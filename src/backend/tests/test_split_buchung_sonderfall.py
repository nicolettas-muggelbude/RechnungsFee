"""
Regressionstests für Issue #384 Punkt 3+7 (Split-Buchung):

- Eine Split-Position auf "Drittland-Dienstleistungen (§13b Abs. 2)" (Konto 3125/5925)
  bekam bisher GAR KEINEN ust_sonderfall (weder 46/47 noch 84/85) - die Buchung fiel
  komplett aus der UStVA heraus.
- Dieselbe Kategorie bekam zusätzlich fälschlich steuerbefreiung_grund="§4 Nr. 1b UStG"
  (das ist die Befreiung für ausgehende ig. Lieferungen, hier auf einer Eingangsleistung),
  weil kat.konto_skr03 gegen ein gemischtes SKR03/SKR04-Tupel statt getrennt geprüft wurde
  - identisches Muster wie Issue #326 in _felder_aus_data(), hier aber in
  create_split_buchung() nie mitkorrigiert.
- Eine Split-Position mit Kategorie "Einfuhrumsatzsteuer (Zoll/DHL)" wurde als normaler
  Prozentsatz-Split behandelt statt als vollstaendiger Steuerbetrag ohne Netto-Anteil.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.journal import create_split_buchung
from api.schemas import SplitBuchungCreate, SplitPosition
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _setup(db):
    ig_lieferung = Kategorie(
        name="Innergemeinschaftliche Lieferungen", kontenart="Erlös",
        konto_skr03="8125", konto_skr04="3125", vorsteuer_prozent=0, ust_satz_standard=0,
    )
    drittland_dl = Kategorie(
        name="Drittland-Dienstleistungen (§13b Abs. 2)", kontenart="Aufwand",
        konto_skr03="3125", konto_skr04="5925", vorsteuer_prozent=100, ust_satz_standard=19,
    )
    buero = Kategorie(
        name="Bürobedarf", kontenart="Aufwand",
        konto_skr03="4930", konto_skr04="6815", vorsteuer_prozent=100, ust_satz_standard=19,
    )
    einfuhr = Kategorie(
        name="Einfuhrumsatzsteuer (Zoll/DHL)", kontenart="Aufwand",
        konto_skr03="1588", konto_skr04="1433", vorsteuer_prozent=100, ust_satz_standard=0,
    )
    db.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    db.add_all([ig_lieferung, drittland_dl, buero, einfuhr])
    db.commit()
    for k in (ig_lieferung, drittland_dl, buero, einfuhr):
        db.refresh(k)
    return ig_lieferung, drittland_dl, buero, einfuhr


def test_split_position_drittland_abs2_bekommt_sonderfall_und_keine_falsche_befreiung(db):
    _ig, drittland_dl, buero, _einfuhr = _setup(db)

    data = SplitBuchungCreate(
        datum=date(2026, 1, 5), art="Ausgabe", zahlungsart="Bank",
        positionen=[
            SplitPosition(beschreibung="US-SaaS Abo", kategorie_id=drittland_dl.id,
                          brutto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), vorsteuerabzug=True),
            SplitPosition(beschreibung="Bürobedarf", kategorie_id=buero.id,
                          brutto_betrag=Decimal("59.50"), ust_satz=Decimal("19"), vorsteuerabzug=True),
        ],
    )
    ergebnisse = create_split_buchung(data, db)
    e_dl = db.query(Journaleintrag).filter(Journaleintrag.id == ergebnisse[0].id).first()

    assert e_dl.ust_sonderfall == "13b_abs2"
    assert e_dl.steuerbefreiung_grund is None
    assert e_dl.netto_betrag == Decimal("100.00")
    assert e_dl.ust_betrag == Decimal("19.00")
    assert e_dl.vorsteuer_betrag == Decimal("19.00")


def test_split_position_ig_lieferung_bekommt_weiterhin_korrekte_befreiung(db):
    """Gegenprobe: die eigentliche Kollisions-Kategorie darf durch den Fix nicht kaputtgehen."""
    ig_lieferung, _drittland, buero, _einfuhr = _setup(db)

    data = SplitBuchungCreate(
        datum=date(2026, 1, 5), art="Einnahme", zahlungsart="Bank",
        positionen=[
            SplitPosition(beschreibung="ig. Lieferung Testkunde", kategorie_id=ig_lieferung.id,
                          brutto_betrag=Decimal("119.00"), ust_satz=Decimal("0")),
            SplitPosition(beschreibung="Sonstige Einnahme", kategorie_id=buero.id,
                          brutto_betrag=Decimal("10.00"), ust_satz=Decimal("19")),
        ],
    )
    ergebnisse = create_split_buchung(data, db)
    e = db.query(Journaleintrag).filter(Journaleintrag.id == ergebnisse[0].id).first()

    assert e.ust_sonderfall is None
    assert e.steuerbefreiung_grund == "§4 Nr. 1b UStG"


def test_split_position_einfuhrumsatzsteuer_ohne_netto_anteil(db):
    _ig, _drittland, buero, einfuhr = _setup(db)

    data = SplitBuchungCreate(
        datum=date(2026, 1, 5), art="Ausgabe", zahlungsart="Bank",
        positionen=[
            SplitPosition(beschreibung="Einfuhr-USt Zoll", kategorie_id=einfuhr.id,
                          brutto_betrag=Decimal("50.00"), ust_satz=Decimal("0")),
            SplitPosition(beschreibung="Bürobedarf", kategorie_id=buero.id,
                          brutto_betrag=Decimal("59.50"), ust_satz=Decimal("19"), vorsteuerabzug=True),
        ],
    )
    ergebnisse = create_split_buchung(data, db)
    e = db.query(Journaleintrag).filter(Journaleintrag.id == ergebnisse[0].id).first()

    assert e.ust_sonderfall == "einfuhr_ust"
    assert e.netto_betrag == Decimal("0.00")
    assert e.ust_betrag == Decimal("50.00")
    assert e.brutto_betrag == Decimal("50.00")
