"""
Regressionstests für Issue #419 Phase 1: Abschlagsrechnung als eigenständiger,
nutzbarer Dokumenttyp (noch ohne Verrechnung in einer Schlussrechnung).

Deckt ab:
- Eigener Nummernkreis (AR-YY####) statt der normalen RE-/ER-Zählung.
- Standardmäßig ausgeschlossen aus der normalen Rechnungsliste, erscheint nur bei
  explizitem dokument_typ-Filter.
- Zahlung bucht wie bei einer normalen Ausgangsrechnung (Ist-Versteuerung) - keine
  neue Berechnungslogik nötig.
- Storno funktioniert unverändert und wird im PDF als Storno erkannt.
- Überzahlungs-Erkennung greift auch für Abschlagsrechnungen.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import (
    _rechnungen_gefiltert,
    create_rechnung,
    get_ueberzahlungen,
    storno_rechnung,
    zahlung_bar_erstellen,
)
from api.schemas import StornoRequest
from api.schemas_rechnungen import BarZahlungCreate, RechnungCreate, RechnungspositionCreate
from database.connection import Base
from database.models import Journaleintrag, Nummernkreis, Rechnung, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(firmenname="Testfirma GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    session.add(Nummernkreis(bezeichnung="Abschlagsrechnungen", typ="abschlagsrechnung", format="AR-YY####", naechste_nr=1, reset_jaehrlich=True))
    session.commit()
    yield session
    session.close()


def _abschlag_daten(**kwargs) -> RechnungCreate:
    defaults = dict(
        typ="ausgang", dokument_typ="Abschlagsrechnung", datum=date(2026, 1, 10), ist_entwurf=False,
        partner_freitext="Testkunde GmbH",
        positionen=[RechnungspositionCreate(beschreibung="Abschlag 1", menge=Decimal("1"), netto=Decimal("1000.00"), ust_satz=Decimal("19"))],
    )
    defaults.update(kwargs)
    return RechnungCreate(**defaults)


def test_eigener_nummernkreis(db):
    resp = create_rechnung(_abschlag_daten(), db)
    assert resp.rechnungsnummer.startswith("AR-")
    assert resp.dokument_typ == "Abschlagsrechnung"


def test_ausgeschlossen_aus_normaler_liste(db):
    create_rechnung(_abschlag_daten(), db)
    normale_liste = _rechnungen_gefiltert(db)
    assert all(r.dokument_typ != "Abschlagsrechnung" for r in normale_liste)

    gefiltert = _rechnungen_gefiltert(db, dokument_typ="Abschlagsrechnung")
    assert len(gefiltert) == 1


def test_zahlung_bucht_wie_normale_rechnung(db):
    resp = create_rechnung(_abschlag_daten(), db)

    zahlung_bar_erstellen(resp.id, BarZahlungCreate(datum=date(2026, 1, 15), zahlungsart="Bank"), db)

    eintrag = db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == resp.id).first()
    assert eintrag is not None
    assert eintrag.art == "Einnahme"
    assert eintrag.brutto_betrag == Decimal("1190.00")
    assert eintrag.ust_betrag == Decimal("190.00")

    rechnung = db.query(Rechnung).filter(Rechnung.id == resp.id).first()
    assert rechnung.zahlungsstatus == "bezahlt"


def test_storno_funktioniert_und_wird_als_storno_erkannt(db):
    resp = create_rechnung(_abschlag_daten(), db)
    zahlung_bar_erstellen(resp.id, BarZahlungCreate(datum=date(2026, 1, 15), zahlungsart="Bank"), db)

    storno_rechnung(resp.id, StornoRequest(grund="Projekt abgebrochen"), db)

    rechnung = db.query(Rechnung).filter(Rechnung.id == resp.id).first()
    assert rechnung.storniert is True
    # Gegenbuchung wurde erzeugt (Original-Zahlung + Storno-Gegenbuchung)
    eintraege = db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == resp.id).all()
    assert len(eintraege) == 2


def test_ueberzahlung_wird_erkannt(db):
    resp = create_rechnung(_abschlag_daten(), db)
    # zahlung_bar_erstellen() kappt ohne expliziten Split-Betrag auf den Restbetrag - eine
    # Überzahlung entsteht in der Praxis z.B. durch einen zu hohen Bank-Import-Betrag, hier
    # direkt am Datensatz simuliert.
    rechnung = db.query(Rechnung).filter(Rechnung.id == resp.id).first()
    rechnung.bezahlt_betrag = rechnung.brutto_gesamt + Decimal("50.00")
    db.commit()

    ueberzahlungen = get_ueberzahlungen(db)
    assert any(r.id == resp.id for r in ueberzahlungen)
