"""
Issue #404: die Gewerbesteuer-Zahlungen-Summe in Anlage G (anlage_g_berechnen) hatte eine
eigenständige, von der EÜR unabhängige Kalenderjahr-Query (extract("year", ...) == jahr). Bei
abweichendem Wirtschaftsjahr muss auch diese Query dem WJ-Zeitraum folgen, sonst bliebe sie
beim Kalenderjahr hängen während der Rest der Anlage G (über _berechne_euer) korrekt umgerechnet
würde.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.anlage_g import anlage_g_berechnen
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


def _unternehmen(db, geschaeftsjahr_beginn: int) -> Unternehmen:
    unt = Unternehmen(
        firmenname="Testbetrieb", strasse="Musterweg", hausnummer="1",
        plz="12345", ort="Musterstadt", geschaeftsjahr_beginn=geschaeftsjahr_beginn,
        taetigkeitsart="gewerbe",
    )
    db.add(unt)
    db.commit()
    return unt


def _gewst_buchung(db, kat_id: int, datum: date) -> None:
    db.add(Journaleintrag(
        datum=datum, belegnr="GEWST1", beschreibung="Gewerbesteuer",
        kategorie_id=kat_id, zahlungsart="Bank", art="Ausgabe",
        netto_betrag=Decimal("500.00"), ust_satz=Decimal("0"), ust_betrag=Decimal("0"),
        vorsteuer_betrag=Decimal("0"), brutto_betrag=Decimal("500.00"),
    ))
    db.commit()


def test_gewerbesteuer_zahlung_folgt_wirtschaftsjahr_nicht_kalenderjahr(db):
    _unternehmen(db, geschaeftsjahr_beginn=7)
    kat = Kategorie(name="Gewerbesteuer", kontenart="Aufwand")
    db.add(kat)
    db.commit()

    # Zahlung am 15.08.2025 gehört zum WJ 2025 (01.07.2025-30.06.2026)
    _gewst_buchung(db, kat.id, date(2025, 8, 15))

    ergebnis_wj_2025 = anlage_g_berechnen(jahr=2025, db=db)
    ergebnis_wj_2024 = anlage_g_berechnen(jahr=2024, db=db)

    assert ergebnis_wj_2025.gewst_gezahlt == Decimal("500.00")
    assert ergebnis_wj_2024.gewst_gezahlt == Decimal("0.00")


def test_gewerbesteuer_zahlung_kalenderjahr_regression(db):
    """Standardfall (geschaeftsjahr_beginn=1) unverändert: Zahlung im Dezember bleibt im
    selben Kalenderjahr."""
    _unternehmen(db, geschaeftsjahr_beginn=1)
    kat = Kategorie(name="Gewerbesteuer", kontenart="Aufwand")
    db.add(kat)
    db.commit()

    _gewst_buchung(db, kat.id, date(2025, 12, 10))

    ergebnis = anlage_g_berechnen(jahr=2025, db=db)
    assert ergebnis.gewst_gezahlt == Decimal("500.00")
