"""
Regressionstest für Issue #362.

Bug: EUR_ZEILEN_META fehlten die Einträge für Zeile 45, 48 und 50, obwohl seed.py genau diese
Zeilennummern für echte Kategorien vergibt (u.a. "Fortbildung & Fachliteratur" -> Zeile 45).
EUR_ZEILEN_META.get(zeile, ("", ""))[1] fiel für diese Zeilen auf abschnitt="" zurück - weder
"A" noch "B" - wodurch die Vorzeichen-Korrektur nach journal.art übersprungen wurde (Einnahmen
in einer Aufwands-Kategorie wurden addiert statt gegengerechnet) und die Zeile gleichzeitig aus
EINNAHMEN_ZEILEN/AUSGABEN_ZEILEN herausfiel (Betrag verschwand aus summe_ausgaben).
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.euer import _berechne_euer, EUR_ZEILEN_META
from database.connection import Base
from database.models import Journaleintrag, Kategorie
from database.seed import STANDARD_KATEGORIEN


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


_zaehler = {"n": 0}


def _buchung(db, kategorie_id: int, art: str, netto: str) -> None:
    _zaehler["n"] += 1
    e = Journaleintrag(
        datum=date(2025, 3, 1), belegnr=f"B{_zaehler['n']}", beschreibung="x",
        kategorie_id=kategorie_id, zahlungsart="Bank", art=art,
        netto_betrag=Decimal(netto), ust_satz=Decimal("0"), ust_betrag=Decimal("0"),
        vorsteuer_betrag=Decimal("0"), brutto_betrag=Decimal(netto),
    )
    db.add(e)
    db.commit()


def test_alle_seed_euer_zeilen_haben_eine_bezeichnung():
    """Verhindert, dass dieselbe Bug-Klasse für eine künftige neue Kategorie wieder auftritt."""
    verwendete_zeilen = {k["euer_zeile"] for k in STANDARD_KATEGORIEN if k.get("euer_zeile") is not None}
    fehlende = verwendete_zeilen - set(EUR_ZEILEN_META.keys())
    assert not fehlende, f"EUR_ZEILEN_META fehlt für Zeilen: {sorted(fehlende)}"


def test_zeile_45_hat_abschnitt_b():
    assert EUR_ZEILEN_META[45][1] == "B"
    assert EUR_ZEILEN_META[48][1] == "B"
    assert EUR_ZEILEN_META[50][1] == "B"


def test_fehlbuchung_in_zeile_45_wird_gegengerechnet_nicht_addiert(db):
    """Exaktes Szenario aus Issue #362: eine Einnahme in einer Aufwands-Kategorie muss
    gegengerechnet werden (37 - 37 + 37 = 37), nicht als 111 addiert werden."""
    kat = Kategorie(name="Fortbildung & Fachliteratur", kontenart="Aufwand", euer_zeile=45)
    db.add(kat)
    db.commit()

    _buchung(db, kat.id, "Ausgabe", "37.00")
    _buchung(db, kat.id, "Einnahme", "37.00")  # fehlerhaft in Aufwands-Kategorie gebucht
    _buchung(db, kat.id, "Ausgabe", "37.00")

    erg = _berechne_euer(2025, db)
    assert erg["zeilen"][45] == Decimal("37.00")
    assert erg["summe_ausgaben"] == Decimal("37.00")
    assert erg["summe_einnahmen"] == Decimal("0.00")


def test_zeile_48_reparatur_zaehlt_zu_summe_ausgaben(db):
    kat = Kategorie(name="Reparatur Anlagevermögen", kontenart="Aufwand", euer_zeile=48)
    db.add(kat)
    db.commit()
    _buchung(db, kat.id, "Ausgabe", "100.00")

    erg = _berechne_euer(2025, db)
    assert erg["zeilen"][48] == Decimal("100.00")
    assert erg["summe_ausgaben"] == Decimal("100.00")


def test_zeile_50_software_zaehlt_zu_summe_ausgaben(db):
    kat = Kategorie(name="Software & Abonnements", kontenart="Aufwand", euer_zeile=50)
    db.add(kat)
    db.commit()
    _buchung(db, kat.id, "Ausgabe", "50.00")

    erg = _berechne_euer(2025, db)
    assert erg["zeilen"][50] == Decimal("50.00")
    assert erg["summe_ausgaben"] == Decimal("50.00")
