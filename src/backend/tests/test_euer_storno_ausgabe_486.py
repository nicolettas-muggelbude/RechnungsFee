"""
Regressionstest für Issue #486.

Die gespiegelte Storno-Gegenbuchung einer Ausgabe (art=Einnahme) übernimmt ust_betrag positiv,
negiert aber vorsteuer_betrag. Die EÜR-Basis „netto + (ust - vorsteuer)“ (Issue #424) ergab dort
die doppelte USt statt 0: Storno einer Zahlung über 30 € netto / 5,70 € USt minderte Zeile 27
um 41,40 € statt um 30 € - die Ausgaben wurden dadurch zu niedrig, der Gewinn zu hoch.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.cockpit import _ausgabe_netto
from api.euer import _berechne_euer, _berechne_euer_kategorien, ausgabe_basis
from api.journal import storno_eintrag
from api.schemas import StornoRequest
from database.connection import Base
from database.models import Journaleintrag, Kategorie

D = Decimal


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def kat(db):
    k = Kategorie(name="Wareneinkauf", kontenart="Aufwand", euer_zeile=27, vorsteuer_prozent=100)
    db.add(k)
    db.commit()
    return k


def _ausgabe(db, kat, ust=D("5.70"), vorsteuer=D("5.70")) -> Journaleintrag:
    e = Journaleintrag(
        datum=date(2025, 10, 11), belegnr="250003", beschreibung="Zahlung ER-250002: Test",
        kategorie_id=kat.id, zahlungsart="PayPal", art="Ausgabe",
        netto_betrag=D("30.00"), ust_satz=D("19"), ust_betrag=ust,
        vorsteuerabzug=vorsteuer != 0, vorsteuer_betrag=vorsteuer, brutto_betrag=D("30.00") + ust,
        immutable=True,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def test_storno_hebt_ausgabe_in_euer_auf(db, kat):
    """Exaktes Szenario aus Issue #486 über den echten Storno-Weg."""
    original = _ausgabe(db, kat)
    storno = db.get(Journaleintrag, storno_eintrag(original.id, StornoRequest(grund="Test"), db).id)
    assert storno.art == "Einnahme"
    assert storno.vorsteuer_betrag == D("-5.70")

    erg = _berechne_euer(2025, db)
    assert erg["zeilen"].get(27, D("0")) == D("0")
    assert erg["zeilen"].get(57, D("0")) == D("0")
    assert erg["summe_ausgaben"] == D("0")
    assert _berechne_euer_kategorien(2025, db).get(27, {}).get("Wareneinkauf", D("0")) == D("0")


def test_storno_einzelbetrag_ist_netto(db, kat):
    original = _ausgabe(db, kat)
    storno = db.get(Journaleintrag, storno_eintrag(original.id, StornoRequest(grund="Test"), db).id)
    assert ausgabe_basis(storno) == D("30.00")
    assert _ausgabe_netto(storno, kat) == D("-30.00")


def test_storno_ohne_vorsteuerabzug_bleibt_brutto(db, kat):
    """Kleinunternehmer (Issue #424): Original und Storno je mit vollem Bruttobetrag."""
    original = _ausgabe(db, kat, vorsteuer=D("0"))
    storno = db.get(Journaleintrag, storno_eintrag(original.id, StornoRequest(grund="Test"), db).id)
    assert ausgabe_basis(original) == D("35.70")
    assert ausgabe_basis(storno) == D("35.70")
    assert _berechne_euer(2025, db)["zeilen"].get(27, D("0")) == D("0")


def test_storno_teilweiser_vorsteuerabzug(db, kat):
    original = _ausgabe(db, kat, vorsteuer=D("3.99"))   # 70 %
    storno = db.get(Journaleintrag, storno_eintrag(original.id, StornoRequest(grund="Test"), db).id)
    assert ausgabe_basis(original) == D("31.71")
    assert ausgabe_basis(storno) == D("31.71")
    assert _berechne_euer(2025, db)["zeilen"].get(27, D("0")) == D("0")


def test_storno_mit_negierten_betraegen_gleiche_art():
    """Variante aus rechnungen.py (Zahlung korrigieren): gleiche art, alle Beträge negiert."""
    e = Journaleintrag(art="Ausgabe", netto_betrag=D("-30.00"), ust_betrag=D("-5.70"),
                       vorsteuer_betrag=D("-5.70"))
    assert ausgabe_basis(e) == D("-30.00")
    ku = Journaleintrag(art="Ausgabe", netto_betrag=D("-30.00"), ust_betrag=D("-5.70"),
                        vorsteuer_betrag=D("0"))
    assert ausgabe_basis(ku) == D("-35.70")


def test_reverse_charge_nur_netto():
    e = Journaleintrag(art="Einnahme", netto_betrag=D("100.00"), ust_betrag=D("19.00"),
                       vorsteuer_betrag=D("-19.00"), ust_sonderfall="13b_abs1")
    assert ausgabe_basis(e) == D("100.00")
