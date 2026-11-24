"""
Issue #578 (Folgemeldung Moog): Die Vorsteuer aus einem Anlagekauf (Kategorie mit kontenart
„Anlage“, z. B. PC über „EDV / Software (Sofortabschreibung)“) fehlte in EÜR-Zeile 57 - die
Anlage-Buchung wurde übersprungen, bevor die Vorsteuer verbucht war. Zusätzlich nennt der
AVEÜR-Hinweis jetzt die Anschaffungskosten (netto + nicht abgezogene Vorsteuer) statt brutto.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.euer import _berechne_euer, _berechne_euer_kategorien
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
    k = Kategorie(name="EDV / Software (Sofortabschreibung)", kontenart="Anlage",
                  euer_zeile=None, vorsteuer_prozent=100)
    db.add(k)
    db.commit()
    return k


def _kauf(db, kat, vorsteuer=D("190.00")) -> Journaleintrag:
    e = Journaleintrag(
        datum=date(2026, 10, 6), belegnr=f"PC-{vorsteuer}", beschreibung="PC",
        kategorie_id=kat.id, zahlungsart="Bank", art="Ausgabe",
        netto_betrag=D("1000.00"), ust_satz=D("19"), ust_betrag=D("190.00"), konto_ust_skr03="1576",
        vorsteuerabzug=vorsteuer != 0, vorsteuer_betrag=vorsteuer, brutto_betrag=D("1190.00"),
        immutable=True,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def test_vorsteuer_aus_anlagekauf_in_zeile_57(db, kat):
    _kauf(db, kat)
    daten = _berechne_euer(2026, db)
    assert daten["zeilen"].get(57) == D("190.00")
    assert daten["zeilen"].get(17) is None
    assert daten["anlage_zugaenge"] == D("1000.00")    # netto, nicht brutto
    assert _berechne_euer_kategorien(2026, db)[57] == {"Vorsteuer": D("190.00")}


def test_storno_hebt_vorsteuer_und_zugang_auf(db, kat):
    original = _kauf(db, kat)
    storno_eintrag(original.id, StornoRequest(grund="Test"), db)
    daten = _berechne_euer(2026, db)
    assert daten["zeilen"].get(57, D("0")) == D("0")
    assert daten["zeilen"].get(17, D("0")) == D("0")
    assert daten["anlage_zugaenge"] == D("0.00")


def test_ohne_vorsteuerabzug_brutto_als_anschaffungskosten(db, kat):
    """Kleinunternehmer: keine Vorsteuer, USt gehört zu den Anschaffungskosten."""
    _kauf(db, kat, vorsteuer=D("0"))
    daten = _berechne_euer(2026, db)
    assert daten["zeilen"].get(57) is None
    assert daten["anlage_zugaenge"] == D("1190.00")
