"""
Regressionstests für das Storno-Datum bei Journalbuchungen (Issue #320).

Bug: Die Storno-Gegenbuchung erhielt immer das heutige Datum statt das Datum
der Originalbuchung. Bei der EÜR (Zuflussprinzip) zählt ausschließlich das
Buchungsjahr - ein Storno im laufenden Jahr ließ das Ursprungsjahr
unkorrigiert und verfälschte zusätzlich das laufende Jahr.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.journal import storno_eintrag
from api.schemas import StornoRequest
from database.connection import Base
from database.models import Journaleintrag


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _alte_ausgabe(db) -> Journaleintrag:
    eintrag = Journaleintrag(
        datum=date(2021, 5, 3), belegnr="J-2021-1", beschreibung="Alte Ausgabe",
        zahlungsart="Bank", art="Ausgabe",
        netto_betrag=Decimal("1000.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("190.00"),
        brutto_betrag=Decimal("1190.00"), vorsteuerabzug=True, immutable=True,
    )
    db.add(eintrag)
    db.commit()
    db.refresh(eintrag)
    return eintrag


def test_storno_ohne_datum_uebernimmt_datum_der_originalbuchung(db):
    original = _alte_ausgabe(db)

    ergebnis = storno_eintrag(original.id, StornoRequest(grund="falsche Kategorie"), db)

    assert ergebnis.datum == date(2021, 5, 3)
    assert ergebnis.art == "Einnahme"
    assert ergebnis.brutto_betrag == Decimal("1190.00")


def test_storno_mit_explizitem_datum_uebernimmt_dieses(db):
    """Echte Rückabwicklung mit tatsächlichem Geldfluss heute - Ausnahme vom Default."""
    original = _alte_ausgabe(db)

    ergebnis = storno_eintrag(
        original.id, StornoRequest(grund="Rückzahlung an Kunde", datum=date(2026, 7, 29)), db
    )

    assert ergebnis.datum == date(2026, 7, 29)


def test_storno_kopiert_ust_sonderfall(db):
    """ust_sonderfall/ist_ig_erwerb muessen auf die Gegenbuchung uebernommen werden,
    sonst faellt ein storniertes ig-Erwerb/§13b-Original bei der Auswertung falsch aus."""
    original = Journaleintrag(
        datum=date(2024, 3, 1), belegnr="J-2024-1", beschreibung="EU-Dienstleistung eingekauft",
        zahlungsart="Bank", art="Ausgabe",
        netto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        brutto_betrag=Decimal("100.00"), vorsteuerabzug=True,
        ust_sonderfall="13b_abs1", immutable=True,
    )
    db.add(original)
    db.commit()
    db.refresh(original)

    ergebnis = storno_eintrag(original.id, StornoRequest(grund="Testkorrektur"), db)

    assert ergebnis.ust_sonderfall == "13b_abs1"
