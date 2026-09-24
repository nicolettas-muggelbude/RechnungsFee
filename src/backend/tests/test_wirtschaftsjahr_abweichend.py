"""
Issue #404: abweichendes Wirtschaftsjahr (z.B. 01.07.-30.06. für Landwirtschaft).

unternehmen.geschaeftsjahr_beginn existierte bereits seit dem allerersten Schema-Commit, wurde
aber von der EÜR-Berechnung (_berechne_euer/_berechne_euer_kategorien in euer.py) komplett
ignoriert - fest 01.01.-31.12. Diese Tests prüfen, dass Buchungen jetzt korrekt dem
Wirtschaftsjahr statt dem Kalenderjahr zugeordnet werden, dass der Standardfall
(geschaeftsjahr_beginn=1, oder gar kein Unternehmen-Datensatz) unverändert bleibt, und dass der
serverseitige Validator geschaeftsjahr_beginn zurücksetzt sobald der Opt-in-Schalter aus ist.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.euer import _berechne_euer
from api.schemas import UnternehmenCreate
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Unternehmen
from utils.wirtschaftsjahr import wirtschaftsjahr_zeitraum


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _unternehmen(db, geschaeftsjahr_beginn: int = 1) -> Unternehmen:
    unt = Unternehmen(
        firmenname="Testbetrieb", strasse="Musterweg", hausnummer="1",
        plz="12345", ort="Musterstadt", geschaeftsjahr_beginn=geschaeftsjahr_beginn,
    )
    db.add(unt)
    db.commit()
    return unt


_zaehler = {"n": 0}


def _buchung(db, kategorie_id: int, datum: date, netto: str = "100.00") -> None:
    _zaehler["n"] += 1
    e = Journaleintrag(
        datum=datum, belegnr=f"B{_zaehler['n']}", beschreibung="x",
        kategorie_id=kategorie_id, zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal(netto), ust_satz=Decimal("0"), ust_betrag=Decimal("0"),
        vorsteuer_betrag=Decimal("0"), brutto_betrag=Decimal(netto),
    )
    db.add(e)
    db.commit()


def test_wirtschaftsjahr_zeitraum_kalenderjahr():
    unt = Unternehmen(firmenname="x", strasse="x", hausnummer="1", plz="1", ort="x", geschaeftsjahr_beginn=1)
    von, bis = wirtschaftsjahr_zeitraum(unt, 2025)
    assert (von, bis) == (date(2025, 1, 1), date(2025, 12, 31))


def test_wirtschaftsjahr_zeitraum_abweichend_juli():
    unt = Unternehmen(firmenname="x", strasse="x", hausnummer="1", plz="1", ort="x", geschaeftsjahr_beginn=7)
    von, bis = wirtschaftsjahr_zeitraum(unt, 2025)
    assert (von, bis) == (date(2025, 7, 1), date(2026, 6, 30))


def test_buchung_landet_im_richtigen_wirtschaftsjahr_nicht_kalenderjahr(db):
    """Kernszenario aus Issue #404: WJ 01.07.-30.06. Eine Buchung vom 15.08.2025 gehört zum WJ
    2025 (01.07.2025-30.06.2026), nicht mehr zum Kalenderjahr 2025 wie vorher."""
    _unternehmen(db, geschaeftsjahr_beginn=7)
    kat = Kategorie(name="Betriebseinnahmen", kontenart="Ertrag", euer_zeile=15)
    db.add(kat)
    db.commit()

    _buchung(db, kat.id, date(2025, 8, 15))

    ergebnis_wj_2025 = _berechne_euer(2025, db)
    ergebnis_wj_2024 = _berechne_euer(2024, db)
    assert ergebnis_wj_2025["zeilen"].get(15) is not None
    assert 15 not in {z for z in ergebnis_wj_2024["zeilen"]}


def test_grenzfall_30_juni_gehoert_noch_zum_alten_wirtschaftsjahr(db):
    _unternehmen(db, geschaeftsjahr_beginn=7)
    kat = Kategorie(name="Betriebseinnahmen", kontenart="Ertrag", euer_zeile=15)
    db.add(kat)
    db.commit()

    _buchung(db, kat.id, date(2025, 6, 30))

    ergebnis_wj_2024 = _berechne_euer(2024, db)  # WJ 01.07.2024-30.06.2025
    ergebnis_wj_2025 = _berechne_euer(2025, db)  # WJ 01.07.2025-30.06.2026
    assert ergebnis_wj_2024["zeilen"].get(15) is not None
    assert 15 not in {z for z in ergebnis_wj_2025["zeilen"]}


def test_grenzfall_1_juli_gehoert_zum_neuen_wirtschaftsjahr(db):
    _unternehmen(db, geschaeftsjahr_beginn=7)
    kat = Kategorie(name="Betriebseinnahmen", kontenart="Ertrag", euer_zeile=15)
    db.add(kat)
    db.commit()

    _buchung(db, kat.id, date(2025, 7, 1))

    ergebnis_wj_2025 = _berechne_euer(2025, db)
    assert ergebnis_wj_2025["zeilen"].get(15) is not None


def test_kalenderjahr_bleibt_unveraendert_wenn_geschaeftsjahr_beginn_1(db):
    """Regressionstest: Standardfall (geschaeftsjahr_beginn=1) verhält sich exakt wie vor
    Issue #404 - eine Dezember-Buchung bleibt im selben Kalenderjahr."""
    _unternehmen(db, geschaeftsjahr_beginn=1)
    kat = Kategorie(name="Betriebseinnahmen", kontenart="Ertrag", euer_zeile=15)
    db.add(kat)
    db.commit()

    _buchung(db, kat.id, date(2025, 12, 15))

    ergebnis = _berechne_euer(2025, db)
    assert ergebnis["zeilen"].get(15) is not None


def test_ohne_unternehmen_datensatz_faellt_auf_kalenderjahr_zurueck(db):
    """Regressionstest für bestehende Tests/Szenarien ohne Unternehmen-Zeile in der DB
    (z.B. test_euer_zeile_45_48_50.py) - _berechne_euer darf nicht crashen."""
    kat = Kategorie(name="Betriebseinnahmen", kontenart="Ertrag", euer_zeile=15)
    db.add(kat)
    db.commit()

    _buchung(db, kat.id, date(2025, 12, 15))

    ergebnis = _berechne_euer(2025, db)
    assert ergebnis["zeilen"].get(15) is not None


def test_validator_erzwingt_kalenderjahr_wenn_schalter_aus():
    """schemas.py::erzwinge_kalenderjahr_wenn_inaktiv - geschaeftsjahr_beginn ist die einzige
    Quelle der Wahrheit, der Opt-in-Schalter steuert nur die UI. Ein Request mit
    abweichend_aktiv=False aber geschaeftsjahr_beginn=7 darf keinen inkonsistenten Zustand
    speichern können."""
    daten = UnternehmenCreate(
        firmenname="x", strasse="x", hausnummer="1", plz="12345", ort="x",
        wirtschaftsjahr_abweichend_aktiv=False, geschaeftsjahr_beginn=7,
    )
    assert daten.geschaeftsjahr_beginn == 1


def test_validator_laesst_wert_wenn_schalter_an():
    daten = UnternehmenCreate(
        firmenname="x", strasse="x", hausnummer="1", plz="12345", ort="x",
        wirtschaftsjahr_abweichend_aktiv=True, geschaeftsjahr_beginn=7,
    )
    assert daten.geschaeftsjahr_beginn == 7
