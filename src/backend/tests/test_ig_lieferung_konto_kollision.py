"""
Regressionstest für Issue #326.

Bug: journal.py._felder_aus_data() und rechnungen.py._erstelle_eintrag() leiteten
ust_sonderfall aus einem gemeinsamen Tupel (kat.konto_skr03, kat.konto_skr04) ab, statt
SKR03- und SKR04-Konto getrennt zu prüfen. Die Kategorie "Innergemeinschaftliche
Lieferungen" hat konto_skr04="3125" - derselbe Wert ist konto_skr03 der Kategorie
"Drittland-Dienstleistungen (§13b Abs. 1)". Die gemischte Prüfung "3125" in (skr03, skr04)
traf auf beide Kategorien zu, wodurch eine Buchung auf "Innergemeinschaftliche
Lieferungen" fälschlich als ust_sonderfall="13b_abs1" eingestuft wurde - in der USt-VA
landete der Betrag dadurch in KZ 46/47 statt (korrekt) in KZ 41.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.journal import create_eintrag
from api.rechnungen import zahlung_bar_erstellen
from api.schemas import JournalEintragCreate
from api.schemas_rechnungen import BarZahlungCreate
from api.ustva import _berechne_kz
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Rechnung, Rechnungsposition, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _kategorien(db) -> tuple[Kategorie, Kategorie]:
    """Beide an der Kollision beteiligten Kategorien parallel anlegen, wie im echten Seed."""
    ig_lieferung = Kategorie(
        name="Innergemeinschaftliche Lieferungen", kontenart="Erlös",
        konto_skr03="8125", konto_skr04="3125", vorsteuer_prozent=0, ust_satz_standard=0,
    )
    drittland_dl = Kategorie(
        name="Drittland-Dienstleistungen (§13b Abs. 1)", kontenart="Aufwand",
        konto_skr03="3125", konto_skr04="5925", vorsteuer_prozent=100, ust_satz_standard=19,
    )
    db.add_all([ig_lieferung, drittland_dl])
    db.commit()
    db.refresh(ig_lieferung)
    db.refresh(drittland_dl)
    return ig_lieferung, drittland_dl


def test_ig_lieferung_bekommt_keinen_ust_sonderfall_und_kz41(db):
    ig_lieferung, _drittland_dl = _kategorien(db)
    db.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    db.commit()

    data = JournalEintragCreate(
        datum=date(2026, 1, 5), beschreibung="ig. Lieferung Testkunde",
        kategorie_id=ig_lieferung.id, art="Einnahme", brutto_betrag=Decimal("119.00"), zahlungsart="Bank",
    )
    response = create_eintrag(data, db)
    eintrag = db.query(Journaleintrag).filter(Journaleintrag.id == response.id).first()

    assert eintrag.ust_sonderfall is None
    assert eintrag.steuerbefreiung_grund == "§4 Nr. 1b UStG"

    kz = _berechne_kz(date(2026, 1, 1), date(2026, 1, 31), db)
    assert kz["kz_41"] == Decimal("119.00")
    assert kz["kz_46"] == Decimal("0")
    assert kz["kz_47"] == Decimal("0")


def test_drittland_dienstleistung_bekommt_weiterhin_13b_abs1(db):
    """Gegenprobe: die eigentliche Kollisions-Kategorie darf durch den Fix nicht kaputtgehen."""
    _ig_lieferung, drittland_dl = _kategorien(db)
    rechnung = Rechnung(
        typ="eingang", rechnungsnummer="ER-DL-1", datum=date(2026, 1, 1),
        brutto_gesamt=Decimal("119.00"), netto_gesamt=Decimal("100.00"), ist_entwurf=False,
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="US-SaaS Abo",
        menge=Decimal("1"), netto=Decimal("100.00"), ust_satz=Decimal("19"), brutto=Decimal("119.00"),
    ))
    db.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    db.commit()
    db.refresh(rechnung)

    zahlung_bar_erstellen(
        rechnung.id,
        BarZahlungCreate(datum=date(2026, 1, 5), zahlungsart="Bank", kategorie_id=drittland_dl.id),
        db,
    )
    eintrag = db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == rechnung.id).first()
    assert eintrag.ust_sonderfall == "13b_abs1"
