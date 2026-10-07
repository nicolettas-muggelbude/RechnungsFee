"""
Regressionstests für Issue #419 Phase 2b: Abzugsbasis = tatsächlicher Zahlungseingang statt
Rechnungsbetrag der Abschlagsrechnung - begrenzt auf Unterzahlung.

Deckt ab:
- _bezahlte_betraege_je_satz() liefert den tatsächlich gezahlten Betrag je USt-Satz (nicht den
  Rechnungsbetrag) bei Unterzahlung und komplett unbezahlten Abschlagsrechnungen.
- Eine Überzahlung bleibt bewusst AUSSEN VOR (Nutzer-Vorgabe): der Abzug ist auf den
  Rechnungsbetrag gekappt (= bezahlt_betrag, das die Kappung aus zahlung_bar_erstellen() schon
  mitbringt), die Überzahlungs-Forderung bleibt komplett unabhängig von der Verrechnung - wird
  weder beim Verrechnen geschlossen noch beim Storno/Löschen angefasst.
- GET /offene-abschlaege liefert bezahlt_je_satz korrekt mit.
- Eine komplett unbezahlte, aber verrechnete Abschlagsrechnung erzeugt keinen Abzug.
- Eine verrechnete Abschlagsrechnung erscheint nicht mehr in der Fälligkeitsliste.
- Eine durch Überdeckung negative Schlussrechnung erscheint nicht im Überzahlungs-Widget.
- Eine Bar-Rückzahlung auf eine negative Rechnung prüft den Kassenstand (wie bei Gutschrift).
- Löschen eines Schlussrechnungs-ENTWURFS mit verrechneten Abschlagsrechnungen gibt diese
  vorher frei, statt an der FK-Referenz zu scheitern (PRAGMA foreign_keys=ON).
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import (
    _bezahlte_betraege_je_satz,
    create_rechnung,
    delete_rechnung,
    get_faellige_rechnungen,
    get_ueberzahlungen,
    offene_abschlaege,
    storno_rechnung,
    zahlung_bar_erstellen,
)
from api.schemas import StornoRequest
from api.schemas_rechnungen import BarZahlungCreate, RechnungCreate, RechnungspositionCreate
from database.connection import Base
from database.models import Forderung, Kunde, Rechnung, Unternehmen


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


def _abschlag(db, kunde_id, netto="1000.00", faellig_am=None) -> Rechnung:
    resp = create_rechnung(RechnungCreate(
        typ="ausgang", dokument_typ="Abschlagsrechnung", datum=date(2026, 1, 10), ist_entwurf=False,
        kunde_id=kunde_id, faellig_am=faellig_am,
        positionen=[RechnungspositionCreate(beschreibung="Abschlag", menge=Decimal("1"), netto=Decimal(netto), ust_satz=Decimal("19"))],
    ), db)
    return db.query(Rechnung).filter(Rechnung.id == resp.id).first()


def _schlussrechnung(db, kunde_id, abschlag_id, abzug_netto, gesamt_netto="2000.00", ist_entwurf=False) -> Rechnung:
    positionen = [RechnungspositionCreate(beschreibung="Gesamtleistung", menge=Decimal("1"), netto=Decimal(gesamt_netto), ust_satz=Decimal("19"))]
    if abschlag_id is not None:
        positionen.append(RechnungspositionCreate(
            beschreibung="Abzgl. Abschlag", menge=Decimal("-1") if abzug_netto != "0" else Decimal("0"),
            netto=Decimal(abzug_netto), ust_satz=Decimal("19"), abschlag_rechnung_id=abschlag_id,
        ))
    resp = create_rechnung(RechnungCreate(
        typ="ausgang", dokument_typ="Rechnung", datum=date(2026, 2, 1), ist_entwurf=ist_entwurf,
        kunde_id=kunde_id, positionen=positionen,
    ), db)
    return db.query(Rechnung).filter(Rechnung.id == resp.id).first()


def test_unterzahlung_liefert_nur_gezahlten_teil(db):
    session, kunde_id = db
    abschlag = _abschlag(session, kunde_id, netto="1000.00")  # brutto 1190,00
    zahlung_bar_erstellen(abschlag.id, BarZahlungCreate(datum=date(2026, 1, 15), zahlungsart="Bank", betrag=Decimal("500.00")), session)
    session.refresh(abschlag)

    je_satz = _bezahlte_betraege_je_satz(session, abschlag)

    assert len(je_satz) == 1
    satz, brutto = je_satz[0]
    assert satz == Decimal("19")
    assert brutto == Decimal("500.00")


def test_unbezahlte_abschlagsrechnung_liefert_leere_liste(db):
    session, kunde_id = db
    abschlag = _abschlag(session, kunde_id)

    assert _bezahlte_betraege_je_satz(session, abschlag) == []


def test_ueberzahlung_bleibt_auf_rechnungsbetrag_gekappt(db):
    """Nutzer-Vorgabe: der Abzug darf bei Überzahlung NICHT den vollen gezahlten Betrag
    enthalten - nur den Rechnungsbetrag. Die Überzahlungs-Spitze bleibt eine komplett
    eigenständige, von der Abschlags-Verrechnung unabhängige Kundenguthaben-Forderung."""
    session, kunde_id = db
    abschlag = _abschlag(session, kunde_id, netto="1000.00")  # brutto 1190,00
    zahlung_bar_erstellen(abschlag.id, BarZahlungCreate(datum=date(2026, 1, 15), zahlungsart="Bank", betrag=Decimal("1200.00")), session)
    session.refresh(abschlag)
    # bezahlt_betrag wird beim Buchen bewusst auf brutto_gesamt gekappt
    assert abschlag.bezahlt_betrag == Decimal("1190.00")
    guthaben = session.query(Forderung).filter(Forderung.rechnung_id == abschlag.id).first()
    assert guthaben.betrag == Decimal("10.00")
    assert guthaben.status == "offen"

    je_satz = _bezahlte_betraege_je_satz(session, abschlag)

    assert len(je_satz) == 1
    assert je_satz[0][1] == Decimal("1190.00")  # NICHT 1200.00


def test_offene_abschlaege_liefert_bezahlt_je_satz(db):
    session, kunde_id = db
    abschlag = _abschlag(session, kunde_id, netto="1000.00")
    zahlung_bar_erstellen(abschlag.id, BarZahlungCreate(datum=date(2026, 1, 15), zahlungsart="Bank"), session)

    ergebnis = offene_abschlaege(kunde_id, db=session)

    treffer = next(r for r in ergebnis if r.id == abschlag.id)
    assert len(treffer.bezahlt_je_satz) == 1
    assert treffer.bezahlt_je_satz[0].brutto == Decimal("1190.00")


def test_verrechnen_laesst_ueberzahlungs_forderung_unangetastet(db):
    session, kunde_id = db
    abschlag = _abschlag(session, kunde_id, netto="1000.00")
    zahlung_bar_erstellen(abschlag.id, BarZahlungCreate(datum=date(2026, 1, 15), zahlungsart="Bank", betrag=Decimal("1200.00")), session)
    session.refresh(abschlag)
    guthaben = session.query(Forderung).filter(Forderung.rechnung_id == abschlag.id).first()
    assert guthaben.status == "offen"

    schlussrechnung = _schlussrechnung(session, kunde_id, abschlag.id, abzug_netto="1000.00")

    session.refresh(guthaben)
    assert guthaben.status == "offen"  # unverändert, keine Kopplung
    session.refresh(abschlag)
    assert abschlag.verrechnet_in_rechnung_id == schlussrechnung.id


def test_storno_laesst_ueberzahlungs_forderung_unangetastet(db):
    session, kunde_id = db
    abschlag = _abschlag(session, kunde_id, netto="1000.00")
    zahlung_bar_erstellen(abschlag.id, BarZahlungCreate(datum=date(2026, 1, 15), zahlungsart="Bank", betrag=Decimal("1200.00")), session)
    guthaben = session.query(Forderung).filter(Forderung.rechnung_id == abschlag.id).first()
    schlussrechnung = _schlussrechnung(session, kunde_id, abschlag.id, abzug_netto="1000.00")

    storno_rechnung(schlussrechnung.id, StornoRequest(grund="Test"), session)

    session.refresh(guthaben)
    assert guthaben.status == "offen"  # unverändert
    session.refresh(abschlag)
    assert abschlag.verrechnet_in_rechnung_id is None


def test_vollstaendig_unbezahlte_abschlagsrechnung_bleibt_verrechnet_ohne_abzug(db):
    session, kunde_id = db
    abschlag = _abschlag(session, kunde_id, netto="1000.00")  # nie bezahlt

    schlussrechnung = _schlussrechnung(session, kunde_id, abschlag.id, abzug_netto="0", gesamt_netto="2000.00")

    assert schlussrechnung.netto_gesamt == Decimal("2000.00")  # kein Abzug
    session.refresh(abschlag)
    assert abschlag.verrechnet_in_rechnung_id == schlussrechnung.id


def test_verrechnete_abschlagsrechnung_nicht_mehr_faellig(db):
    session, kunde_id = db
    abschlag = _abschlag(session, kunde_id, netto="1000.00", faellig_am=date.today() - timedelta(days=5))

    vor = get_faellige_rechnungen(tage=7, db=session)
    assert any(r.id == abschlag.id for r in vor)

    _schlussrechnung(session, kunde_id, abschlag.id, abzug_netto="1000.00")

    nach = get_faellige_rechnungen(tage=7, db=session)
    assert not any(r.id == abschlag.id for r in nach)


def test_negative_schlussrechnung_nicht_in_ueberzahlungen(db):
    session, kunde_id = db
    abschlag = _abschlag(session, kunde_id, netto="5000.00")

    schlussrechnung = _schlussrechnung(session, kunde_id, abschlag.id, abzug_netto="1000.00", gesamt_netto="100.00")
    assert schlussrechnung.brutto_gesamt < 0

    ueberzahlungen = get_ueberzahlungen(db=session)
    assert not any(r.id == schlussrechnung.id for r in ueberzahlungen)


def test_bar_rueckzahlung_auf_negative_rechnung_prueft_kassenstand(db):
    session, kunde_id = db
    abschlag = _abschlag(session, kunde_id, netto="5000.00")
    schlussrechnung = _schlussrechnung(session, kunde_id, abschlag.id, abzug_netto="1000.00", gesamt_netto="100.00")
    assert schlussrechnung.brutto_gesamt < 0

    with pytest.raises(HTTPException) as exc:
        zahlung_bar_erstellen(schlussrechnung.id, BarZahlungCreate(datum=date(2026, 2, 2), zahlungsart="Bar", betrag=Decimal("50.00")), session)
    assert exc.value.status_code == 409
    assert "Kassenstand" in exc.value.detail


def test_entwurf_mit_verrechneten_abschlaegen_loeschen_gibt_sie_frei(db):
    """Nutzer-Report: Löschen eines Schlussrechnungs-ENTWURFS mit verrechneten
    Abschlagsrechnungen endete mit Internal Server Error - delete_rechnung() gab die
    Abschlagsrechnungen nicht frei, was die FK-Referenz verrechnet_in_rechnung_id
    (PRAGMA foreign_keys=ON) verletzte."""
    session, kunde_id = db
    abschlag = _abschlag(session, kunde_id, netto="1000.00")
    entwurf = _schlussrechnung(session, kunde_id, abschlag.id, abzug_netto="1000.00", ist_entwurf=True)

    delete_rechnung(entwurf.id, session)

    session.refresh(abschlag)
    assert abschlag.verrechnet_in_rechnung_id is None
    assert session.query(Rechnung).filter(Rechnung.id == entwurf.id).first() is None
