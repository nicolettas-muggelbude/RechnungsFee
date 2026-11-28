"""
Issue #577: Zahlungen zu Rechnungen zeigten im aufgeklappten Journal „Kein Kunde verknüpft“ -
die Journalzeile trägt keinen eigenen Kunden/Lieferanten. Die Anzeige nimmt jetzt den Partner der
verknüpften Rechnung (ohne Datenänderung, DATEV unberührt).
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.schemas import JournalEintragResponse
from database.connection import Base
from database.models import Journaleintrag, Kunde, Lieferant, Rechnung


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _zahlung(db, rechnung, art) -> JournalEintragResponse:
    e = Journaleintrag(datum=date(2026, 11, 20), belegnr=f"26{rechnung.id:04d}", beschreibung="Zahlung",
                       zahlungsart="Bank", art=art, netto_betrag=Decimal("10"), brutto_betrag=Decimal("10"),
                       rechnung_id=rechnung.id, immutable=True)
    db.add(e)
    db.commit()
    db.refresh(e)
    return JournalEintragResponse.from_orm_with_kunde(e)


def test_ausgangsrechnung_zeigt_kunden(db):
    k = Kunde(firmenname="Verein e. V.", email="info@verein.example", strasse="S", plz="1", ort="O")
    db.add(k)
    db.flush()
    r = Rechnung(typ="ausgang", datum=date(2026, 11, 1), kunde_id=k.id)
    db.add(r)
    db.commit()
    resp = _zahlung(db, r, "Einnahme")
    assert (resp.kunde_id, resp.kunde_name, resp.kunde_email) == (None, "Verein e. V.", "info@verein.example")


def test_eingangsrechnung_zeigt_lieferanten(db):
    lf = Lieferant(firmenname="Bürobedarf GmbH", strasse="S", plz="1", ort="O")
    db.add(lf)
    db.flush()
    r = Rechnung(typ="eingang", datum=date(2026, 11, 1), lieferant_id=lf.id)
    db.add(r)
    db.commit()
    resp = _zahlung(db, r, "Ausgabe")
    assert (resp.lieferant_name, resp.kunde_name) == ("Bürobedarf GmbH", None)


def test_einmalkunde_aus_freitext(db):
    r = Rechnung(typ="ausgang", datum=date(2026, 11, 1), partner_freitext="Max Muster")
    db.add(r)
    db.commit()
    assert _zahlung(db, r, "Einnahme").kunde_name == "Max Muster"
