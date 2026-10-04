"""
Regressionstests für Issue #419 Phase 2: Verrechnung von Abschlagsrechnungen in der
Schlussrechnung.

Deckt ab:
- Abzugsposition (negierte Menge, abschlag_rechnung_id markiert) reduziert brutto_gesamt
  korrekt und setzt verrechnet_in_rechnung_id auf der Abschlagsrechnung.
- GET /offene-abschlaege liefert nur unverrechnete, nicht stornierte, nicht Entwurf-
  Abschlagsrechnungen desselben Kunden.
- Überdeckung (Abzug > erfasste Positionen) wird abgelehnt, keine negative Rechnungssumme.
- Eine bereits verrechnete Abschlagsrechnung kann nicht mehr storniert oder gutgeschrieben werden.
- Storno der Schlussrechnung gibt die verrechneten Abschlagsrechnungen wieder frei.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import (
    create_gutschrift,
    create_rechnung,
    offene_abschlaege,
    storno_rechnung,
    update_rechnung,
)
from api.schemas import StornoRequest
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate, RechnungUpdate
from database.connection import Base
from database.models import Kunde, Rechnung, Unternehmen
from fastapi import HTTPException


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(firmenname="Testfirma GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    kunde = Kunde(firmenname="Testkunde GmbH")
    session.add(kunde)
    session.commit()
    session.refresh(kunde)
    yield session, kunde.id
    session.close()


def _abschlag(db, kunde_id, netto="1000.00", nr="AR-1") -> Rechnung:
    resp = create_rechnung(RechnungCreate(
        typ="ausgang", dokument_typ="Abschlagsrechnung", datum=date(2026, 1, 10), ist_entwurf=False,
        kunde_id=kunde_id,
        positionen=[RechnungspositionCreate(beschreibung="Abschlag", menge=Decimal("1"), netto=Decimal(netto), ust_satz=Decimal("19"))],
    ), db)
    return db.query(Rechnung).filter(Rechnung.id == resp.id).first()


def _schlussrechnung_mit_abzug(db, kunde_id, abschlag: Rechnung, gesamt_netto="2000.00", ist_entwurf=False) -> Rechnung:
    resp = create_rechnung(RechnungCreate(
        typ="ausgang", dokument_typ="Rechnung", datum=date(2026, 2, 1), ist_entwurf=ist_entwurf,
        kunde_id=kunde_id,
        positionen=[
            RechnungspositionCreate(beschreibung="Gesamtleistung", menge=Decimal("1"), netto=Decimal(gesamt_netto), ust_satz=Decimal("19")),
            RechnungspositionCreate(
                beschreibung=f"Abzgl. Abschlagsrechnung {abschlag.rechnungsnummer}",
                menge=Decimal("-1"), netto=Decimal("1000.00"), ust_satz=Decimal("19"),
                abschlag_rechnung_id=abschlag.id,
            ),
        ],
    ), db)
    return db.query(Rechnung).filter(Rechnung.id == resp.id).first()


def test_abzugsposition_reduziert_summe_und_markiert_abschlag(db):
    session, kunde_id = db
    abschlag = _abschlag(session, kunde_id)

    schlussrechnung = _schlussrechnung_mit_abzug(session, kunde_id, abschlag)

    assert schlussrechnung.netto_gesamt == Decimal("1000.00")
    assert schlussrechnung.brutto_gesamt == Decimal("1190.00")
    session.refresh(abschlag)
    assert abschlag.verrechnet_in_rechnung_id == schlussrechnung.id


def test_offene_abschlaege_filtert_korrekt(db):
    session, kunde_id = db
    offen = _abschlag(session, kunde_id, nr="AR-1")
    verrechnet = _abschlag(session, kunde_id, nr="AR-2")
    _schlussrechnung_mit_abzug(session, kunde_id, verrechnet)

    ergebnis = offene_abschlaege(kunde_id, session)

    ids = {r.id for r in ergebnis}
    assert offen.id in ids
    assert verrechnet.id not in ids


def test_ueberdeckung_wird_abgelehnt(db):
    session, kunde_id = db
    abschlag = _abschlag(session, kunde_id, netto="5000.00")

    with pytest.raises(HTTPException) as exc:
        _schlussrechnung_mit_abzug(session, kunde_id, abschlag, gesamt_netto="100.00")
    assert exc.value.status_code == 409
    # In der echten Anwendung schliesst get_db() die Session nach einer unbehandelten
    # Exception ohne commit() - das verwirft den bis hierhin nur geflushten, nie committeten
    # Datensatz automatisch. Im Test wird das explizit nachgebildet.
    session.rollback()

    rechnungen = session.query(Rechnung).filter(Rechnung.dokument_typ == "Rechnung").all()
    assert len(rechnungen) == 0


def test_verrechnete_abschlagsrechnung_kann_nicht_storniert_werden(db):
    session, kunde_id = db
    abschlag = _abschlag(session, kunde_id)
    _schlussrechnung_mit_abzug(session, kunde_id, abschlag)

    with pytest.raises(HTTPException) as exc:
        storno_rechnung(abschlag.id, StornoRequest(grund="Test"), session)
    assert exc.value.status_code == 409


def test_verrechnete_abschlagsrechnung_kann_nicht_gutgeschrieben_werden(db):
    session, kunde_id = db
    abschlag = _abschlag(session, kunde_id)
    _schlussrechnung_mit_abzug(session, kunde_id, abschlag)

    with pytest.raises(HTTPException) as exc:
        create_gutschrift(abschlag.id, session)
    assert exc.value.status_code == 409


def test_storno_der_schlussrechnung_gibt_abschlag_wieder_frei(db):
    session, kunde_id = db
    abschlag = _abschlag(session, kunde_id)
    schlussrechnung = _schlussrechnung_mit_abzug(session, kunde_id, abschlag)

    storno_rechnung(schlussrechnung.id, StornoRequest(grund="Test"), session)

    session.refresh(abschlag)
    assert abschlag.verrechnet_in_rechnung_id is None
    ergebnis = offene_abschlaege(kunde_id, session)
    assert any(r.id == abschlag.id for r in ergebnis)


def test_entfernen_der_abzugsposition_beim_bearbeiten_gibt_abschlag_frei(db):
    session, kunde_id = db
    abschlag = _abschlag(session, kunde_id)
    schlussrechnung = _schlussrechnung_mit_abzug(session, kunde_id, abschlag, ist_entwurf=True)

    update_rechnung(schlussrechnung.id, RechnungUpdate(
        positionen=[RechnungspositionCreate(beschreibung="Gesamtleistung", menge=Decimal("1"), netto=Decimal("2000.00"), ust_satz=Decimal("19"))],
    ), session)

    session.refresh(abschlag)
    assert abschlag.verrechnet_in_rechnung_id is None
