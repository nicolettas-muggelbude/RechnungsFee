"""
Regressionstest für Issue #486 (ergänzt zu PR #487).

Die gespiegelte Storno-Gegenbuchung einer Ausgabe (art=Einnahme) übernimmt ust_betrag positiv,
negiert aber vorsteuer_betrag. Ohne Spiegelung ergab die EÜR-Basis die doppelte USt (Storno über
30 € netto / 5,70 € USt minderte Zeile 27 um 41,40 € statt 30 €) und die USt landete zusätzlich
als „vereinnahmt“ in Zeile 17. Hier über den echten Storno-Weg geprüft, inklusive Ausgaben ohne
USt-Konto, „Zahlung korrigieren“ (gleiche art, Beträge negiert) und Cockpit.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.cockpit import _ausgabe_netto
from api.euer import _berechne_euer, _berechne_euer_kategorien, _euer_haupt_beitrag
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


def _ausgabe(db, kat, ust=D("5.70"), vorsteuer=D("5.70"), konto="1576") -> Journaleintrag:
    e = Journaleintrag(
        datum=date(2025, 10, 11), belegnr=f"250003-{konto}-{vorsteuer}", beschreibung="Zahlung ER-250002: Test",
        kategorie_id=kat.id, zahlungsart="PayPal", art="Ausgabe",
        netto_betrag=D("30.00"), ust_satz=D("19"), ust_betrag=ust, konto_ust_skr03=konto,
        vorsteuerabzug=vorsteuer != 0, vorsteuer_betrag=vorsteuer, brutto_betrag=D("30.00") + ust,
        immutable=True,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def _storno(db, original) -> Journaleintrag:
    return db.get(Journaleintrag, storno_eintrag(original.id, StornoRequest(grund="Test"), db).id)


@pytest.mark.parametrize("konto", ["1576", None])
def test_storno_hebt_ausgabe_in_euer_auf(db, kat, konto):
    """Exaktes Szenario aus Issue #486, mit und ohne USt-Konto auf der Ausgabe."""
    _storno(db, _ausgabe(db, kat, konto=konto))

    z = _berechne_euer(2025, db)["zeilen"]
    assert z.get(27, D("0")) == D("0")
    assert z.get(57, D("0")) == D("0")
    assert z.get(17, D("0")) == D("0")    # Storno-USt ist keine vereinnahmte USt
    assert _berechne_euer_kategorien(2025, db).get(17) is None


def test_storno_einzelbetrag_ist_netto(db, kat):
    storno = _storno(db, _ausgabe(db, kat))
    assert _euer_haupt_beitrag(storno) == (27, D("-30.00"))
    assert _ausgabe_netto(storno, kat) == D("-30.00")


def test_storno_ohne_vorsteuerabzug_bleibt_brutto(db, kat):
    """Kleinunternehmer (Issue #424): Original und Storno je mit vollem Bruttobetrag."""
    original = _ausgabe(db, kat, vorsteuer=D("0"))
    storno = _storno(db, original)
    assert _euer_haupt_beitrag(original)[1] == D("35.70")
    assert _euer_haupt_beitrag(storno)[1] == D("-35.70")
    assert _berechne_euer(2025, db)["zeilen"].get(27, D("0")) == D("0")


def test_storno_teilweiser_vorsteuerabzug(db, kat):
    original = _ausgabe(db, kat, vorsteuer=D("3.99"))   # 70 %
    storno = _storno(db, original)
    assert _euer_haupt_beitrag(original)[1] == D("31.71")
    assert _euer_haupt_beitrag(storno)[1] == D("-31.71")
    assert _berechne_euer(2025, db)["zeilen"].get(27, D("0")) == D("0")


def test_zahlung_korrigieren_mindert_vereinnahmte_ust(db):
    """„Zahlung korrigieren“ auf einer Ausgangsrechnung: gleiche art, alle Beträge negiert -
    Zeile 15 und Zeile 17 müssen beide auf 0 zurückgehen."""
    erl = Kategorie(name="Betriebseinnahmen", kontenart="Erlös", euer_zeile=15)
    db.add(erl)
    db.commit()
    zahlung = Journaleintrag(
        datum=date(2025, 3, 1), belegnr="Z1", beschreibung="Zahlung RE-1", kategorie_id=erl.id,
        zahlungsart="Bank", art="Einnahme", netto_betrag=D("1000.00"), ust_satz=D("19"),
        ust_betrag=D("190.00"), brutto_betrag=D("1190.00"),
    )
    db.add(zahlung)
    db.commit()
    db.add(Journaleintrag(
        datum=date(2025, 3, 2), belegnr="Z2", beschreibung="STORNO Z1: Korrektur", kategorie_id=erl.id,
        zahlungsart="Bank", art="Einnahme", netto_betrag=D("-1000.00"), ust_satz=D("19"),
        ust_betrag=D("-190.00"), brutto_betrag=D("-1190.00"), gruppe_id=zahlung.id,
    ))
    db.commit()

    z = _berechne_euer(2025, db)["zeilen"]
    assert z.get(15, D("0")) == D("0")
    assert z.get(17, D("0")) == D("0")


def test_eigene_buchung_mit_storno_text_bleibt_einnahme(db):
    """Ohne gruppe_id ist „STORNO …“ nur Text - die USt zählt normal (Erkennung wie #321)."""
    erl = Kategorie(name="Betriebseinnahmen", kontenart="Erlös", euer_zeile=15)
    db.add(erl)
    db.commit()
    db.add(Journaleintrag(
        datum=date(2025, 3, 1), belegnr="E1", beschreibung="STORNO-Gebühr weiterberechnet",
        kategorie_id=erl.id, zahlungsart="Bank", art="Einnahme", netto_betrag=D("10.00"),
        ust_satz=D("19"), ust_betrag=D("1.90"), brutto_betrag=D("11.90"),
    ))
    db.commit()
    assert _berechne_euer(2025, db)["zeilen"][17] == D("1.90")
