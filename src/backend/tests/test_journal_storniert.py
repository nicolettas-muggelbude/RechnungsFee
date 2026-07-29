"""
Regressionstests für den Storno-Status auf Lese-Endpunkten (Issue #321).

Bug: GET /api/journal und GET /api/journal/{id} lieferten für stornierte
Buchungen kein Signal - Konsumenten mussten die Beschreibung auf den
Präfix "STORNO " prüfen, was u.a. eine eigene Buchung mit zufällig
gleichem Textanfang fälschlich als Gegenbuchung wertet.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.journal import get_eintrag, list_eintraege, storno_eintrag
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


def _eintrag(db, **kwargs) -> Journaleintrag:
    defaults = dict(
        datum=date(2026, 1, 10), beschreibung="Testbuchung",
        zahlungsart="Bank", art="Ausgabe",
        netto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        brutto_betrag=Decimal("119.00"), vorsteuerabzug=True, immutable=True,
    )
    defaults.update(kwargs)
    e = Journaleintrag(**defaults)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def test_original_zeigt_storniert_nach_storno(db):
    original = _eintrag(db, belegnr="J-1")
    gegenbuchung = storno_eintrag(original.id, StornoRequest(grund="Testkorrektur"), db)

    ergebnis = get_eintrag(original.id, db)

    assert ergebnis.storniert is True
    assert ergebnis.storno_belegnr == gegenbuchung.belegnr
    assert ergebnis.ist_storno is False


def test_gegenbuchung_zeigt_ist_storno(db):
    original = _eintrag(db, belegnr="J-2")
    gegenbuchung = storno_eintrag(original.id, StornoRequest(grund="Testkorrektur"), db)

    ergebnis = get_eintrag(gegenbuchung.id, db)

    assert ergebnis.ist_storno is True
    assert ergebnis.storno_von_belegnr == original.belegnr
    assert ergebnis.storniert is False


def test_unbeteiligte_buchung_mit_storno_praefix_wird_nicht_faelschlich_erkannt(db):
    """Eine eigene Buchung, deren Text zufaellig mit 'STORNO ' beginnt, hat kein gruppe_id
    (das laesst sich ueber die API nicht setzen) und darf nicht als Gegenbuchung gelten."""
    fremd = _eintrag(db, belegnr="J-3", beschreibung="STORNO meines Urlaubskontos, nichts mit Buchhaltung zu tun")

    ergebnis = get_eintrag(fremd.id, db)

    assert ergebnis.ist_storno is False
    assert ergebnis.storniert is False


def test_liste_liefert_storno_status_fuer_alle_eintraege(db):
    original = _eintrag(db, belegnr="J-4")
    gegenbuchung = storno_eintrag(original.id, StornoRequest(grund="Testkorrektur"), db)
    unbeteiligt = _eintrag(db, belegnr="J-5")

    ergebnisse = {
        r.id: r for r in list_eintraege(
            monat=None, datum_von=None, datum_bis=None, kategorie_id=None,
            art=None, zahlungsart_typ=None, gruppe_id=None, db=db,
        )
    }

    assert ergebnisse[original.id].storniert is True
    assert ergebnisse[original.id].storno_belegnr == gegenbuchung.belegnr
    assert ergebnisse[gegenbuchung.id].ist_storno is True
    assert ergebnisse[gegenbuchung.id].storno_von_belegnr == original.belegnr
    assert ergebnisse[unbeteiligt.id].storniert is False
    assert ergebnisse[unbeteiligt.id].ist_storno is False
