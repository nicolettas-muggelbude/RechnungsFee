"""
Community-Issue #372: KZ 21 (nicht steuerbare sonstige Leistungen im übrigen
Gemeinschaftsgebiet, §3a Abs. 2 UStG) und KZ 45 (übrige nicht im Inland steuerbare
Umsätze, u. a. Drittland-Dienstleistungen) fehlten in der UStVA-Anzeigehilfe vollständig -
weder automatisch noch manuell. Ausgangsrechnungen lassen sich zwar bereits als
ist_reverse_charge/ist_drittland_leistung kennzeichnen, aber beim Verbuchen der Zahlung
(api/rechnungen.py) wurde das nie an die Buchung weitergegeben. Fix: _berechne_kz() erkennt
diese Rechnungen jetzt direkt über einen Bulk-Lookup der rechnung_id, ohne die
Zahlungsbuchungsfunktion selbst anzufassen.

Die vom Reporter ebenfalls hinterfragten KZ 46/47, 84/85, 67 (§13b) werden hier NICHT erneut
getestet - test_ustva_posten.py::test_sonderfall_13b_erscheint_in_posten deckt das bereits ab
und war schon vor diesem Fix grün (Gegenprüfung: unverändert grün, siehe volle Testsuite).
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import create_rechnung, finalisiere_rechnung, zahlung_bar_erstellen, storno_rechnung
from api.schemas_rechnungen import BarZahlungCreate, RechnungCreate, RechnungspositionCreate
from api.ustva import _berechne_kz
from database.connection import Base
from database.models import Unternehmen


@pytest.fixture
def db(monkeypatch):
    import api.ustva as ustva_api
    monkeypatch.setattr(ustva_api, "CUTOVER_DATUM_VORSTEUER", date(2020, 1, 1))
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    session.commit()
    yield session
    session.close()


def _dl_rechnung(db, *, reverse_charge=False, drittland=False, netto="1000.00") -> int:
    """Ausgangsrechnung mit 0% USt, wie sie das Frontend bei aktivem Reverse-Charge-/
    Drittland-Flag erzeugt (Position bekommt ust_satz=0)."""
    payload = RechnungCreate(
        typ="ausgang", datum=date(2026, 6, 1), partner_freitext="EU-Kunde GmbH",
        ist_reverse_charge=reverse_charge, ist_drittland_leistung=drittland,
        positionen=[RechnungspositionCreate(
            beschreibung="Beratungsleistung", menge=Decimal("1"), einheit="Stk.",
            netto=netto, ust_satz="0",
        )],
    )
    resp = create_rechnung(payload, db)
    finalisiere_rechnung(resp.id, db)
    return resp.id


def test_reverse_charge_dienstleistung_erscheint_in_kz21(db):
    rechnung_id = _dl_rechnung(db, reverse_charge=True)
    zahlung_bar_erstellen(rechnung_id, BarZahlungCreate(datum=date(2026, 6, 15), zahlungsart="Bank"), db)

    kz, posten = _berechne_kz(date(2026, 6, 1), date(2026, 6, 30), db)

    assert kz["kz_21"] == Decimal("1000.00")
    assert kz["kz_45"] == Decimal("0.00")
    assert kz["kz_81"] == Decimal("0.00")  # keine Doppelzählung als normaler Inlandsumsatz
    assert len(posten["kz_21"]) == 1
    assert posten["kz_21"][0]["betrag"] == Decimal("1000.00")
    assert posten["kz_21"][0]["rechnung_id"] == rechnung_id


def test_drittland_dienstleistung_erscheint_in_kz45(db):
    rechnung_id = _dl_rechnung(db, drittland=True, netto="500.00")
    zahlung_bar_erstellen(rechnung_id, BarZahlungCreate(datum=date(2026, 6, 15), zahlungsart="Bank"), db)

    kz, posten = _berechne_kz(date(2026, 6, 1), date(2026, 6, 30), db)

    assert kz["kz_45"] == Decimal("500.00")
    assert kz["kz_21"] == Decimal("0.00")
    assert kz["kz_81"] == Decimal("0.00")
    assert len(posten["kz_45"]) == 1


def test_normale_ausgangsrechnung_bleibt_unveraendert_bei_kz81(db):
    """Gegenprüfung: eine ganz normale (nicht reverse-charge) Ausgangsrechnung darf durch
    den neuen KZ-21/45-Code nicht beeinflusst werden."""
    payload = RechnungCreate(
        typ="ausgang", datum=date(2026, 6, 1), partner_freitext="Inlandskunde",
        positionen=[RechnungspositionCreate(
            beschreibung="Beratung", menge=Decimal("1"), einheit="Stk.",
            netto="100.00", ust_satz="19",
        )],
    )
    resp = create_rechnung(payload, db)
    finalisiere_rechnung(resp.id, db)
    zahlung_bar_erstellen(resp.id, BarZahlungCreate(datum=date(2026, 6, 15), zahlungsart="Bank"), db)

    kz, _ = _berechne_kz(date(2026, 6, 1), date(2026, 6, 30), db)

    assert kz["kz_81"] == Decimal("100.00")
    assert kz["kz_21"] == Decimal("0.00")
    assert kz["kz_45"] == Decimal("0.00")


def test_storno_hebt_kz21_wieder_auf(db):
    rechnung_id = _dl_rechnung(db, reverse_charge=True)
    zahlung_bar_erstellen(rechnung_id, BarZahlungCreate(datum=date(2026, 6, 15), zahlungsart="Bank"), db)
    from api.schemas import StornoRequest
    storno_rechnung(rechnung_id, StornoRequest(grund="Testkorrektur"), db)

    kz, _ = _berechne_kz(date(2026, 6, 1), date(2026, 6, 30), db)

    assert kz["kz_21"] == Decimal("0.00")
