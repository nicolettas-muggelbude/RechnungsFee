"""
Regressionstest für Issue #383: Leistungszeitraum (leistung_von/leistung_bis) als
BT-73/BT-74 (BillingSpecifiedPeriod) im ZUGFeRD-XML.

Manuell gegen die echte facturx-Pipeline verifiziert (PDF/A-Generierung + Extraktion
des eingebetteten XML für Rechnungen mit und ohne Leistungszeitraum) - dieser Test
deckt die reine XML-Erzeugung ab, ohne die PDF/A-Einbettung erneut auszuführen.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import Rechnung, Rechnungsposition
from utils.zugferd import generate_zugferd_xml

UNTERNEHMEN = {
    "firmenname": "Testfirma GmbH",
    "strasse": "Teststraße", "hausnummer": "1", "plz": "12345", "ort": "Teststadt",
    "land": "DE", "steuernummer": "12/345/67890", "ust_idnr": "",
    "ist_kleinunternehmer": False,
}


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _rechnung(db, **kwargs) -> Rechnung:
    defaults = dict(
        typ="ausgang", rechnungsnummer="RE-1", datum=date(2026, 7, 1),
        netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("19.00"), brutto_gesamt=Decimal("119.00"),
        ist_entwurf=False,
    )
    defaults.update(kwargs)
    r = Rechnung(**defaults)
    db.add(r)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=r.id, position_nr=1, beschreibung="Beratung", menge=Decimal("1"),
        einheit="Stück", netto=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        brutto=Decimal("119.00"),
    ))
    db.commit()
    db.refresh(r)
    return r


def test_leistungszeitraum_wird_als_billing_specified_period_abgebildet():
    db = _db()
    rechnung = _rechnung(db, leistung_von=date(2026, 6, 1), leistung_bis=date(2026, 6, 30))

    xml = generate_zugferd_xml(rechnung, UNTERNEHMEN).decode("utf-8")

    assert "<ram:BillingSpecifiedPeriod>" in xml
    assert "<udt:DateTimeString format=\"102\">20260601</udt:DateTimeString>" in xml
    assert "<udt:DateTimeString format=\"102\">20260630</udt:DateTimeString>" in xml


def test_einzelnes_leistungsdatum_ohne_bis_erzeugt_keine_period():
    """leistung_von ohne leistung_bis ist ein einzelnes Leistungsdatum (BT-72, Lieferdatum),
    kein Zeitraum - siehe identische Unterscheidung in pdf_rechnung_base.py."""
    db = _db()
    rechnung = _rechnung(db, leistung_von=date(2026, 6, 15), leistung_bis=None)

    xml = generate_zugferd_xml(rechnung, UNTERNEHMEN).decode("utf-8")

    assert "<ram:BillingSpecifiedPeriod>" not in xml


def test_ohne_leistungszeitraum_keine_period():
    db = _db()
    rechnung = _rechnung(db)

    xml = generate_zugferd_xml(rechnung, UNTERNEHMEN).decode("utf-8")

    assert "<ram:BillingSpecifiedPeriod>" not in xml
