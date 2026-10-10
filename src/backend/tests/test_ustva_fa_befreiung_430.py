"""
Regressionstest für Issue #430.

Zusätzlich zur Kleinunternehmer-Befreiung (§19 UStG) kann das Finanzamt auch reguläre
Unternehmer von der Abgabepflicht für Voranmeldungen befreien (§18 Abs. 2 Satz 3 UStG,
Vorjahressteuer ≤ 2.000 €) - abgebildet über voranmeldungsrhythmus="keine". In diesem Fall
muss die Ausfüllhilfe wie beim Kleinunternehmer die volle KZ-Tabelle unterdrücken und einen
erklärenden Hinweis zeigen, ohne fälschlich ist_kleinunternehmer=True zu melden.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.ustva import ustva_berechnen
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


def test_fa_befreiung_unterdrueckt_kz_tabelle_ohne_kleinunternehmer_zu_sein(db):
    db.add(Unternehmen(
        firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort",
        ist_kleinunternehmer=False, voranmeldungsrhythmus="keine",
    ))
    kat = Kategorie(name="Betriebseinnahmen", kontenart="Erlös", euer_zeile=15, konto_skr03="8400")
    db.add(kat)
    db.commit()
    db.add(Journaleintrag(
        datum=date(2026, 1, 15), belegnr="B1", beschreibung="Testumsatz",
        kategorie_id=kat.id, zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        brutto_betrag=Decimal("119.00"), konto_ust_skr03="1776",
    ))
    db.commit()

    ergebnis = ustva_berechnen(zeitraum="2026-01", db=db)

    assert ergebnis.ist_kleinunternehmer is False
    assert ergebnis.befreit is True
    assert "§18 Abs. 2 Satz 3 UStG" in (ergebnis.hinweis or "")
    # Trotz vorhandener Buchung: KZ-Tabelle wird unterdrückt, kein Umsatz hineinberechnet.
    assert ergebnis.kz_81 == Decimal("0.00")


def test_kleinunternehmer_bleibt_eigener_rechtsgrund_trotz_keine_rhythmus(db):
    """Auto-Auswahl (Frontend) setzt bei Kleinunternehmer voranmeldungsrhythmus="keine" -
    ist_kleinunternehmer muss dabei weiterhin korrekt True bleiben, nicht überschrieben werden."""
    db.add(Unternehmen(
        firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort",
        ist_kleinunternehmer=True, voranmeldungsrhythmus="keine",
    ))
    db.commit()

    ergebnis = ustva_berechnen(zeitraum="2026-01", db=db)

    assert ergebnis.ist_kleinunternehmer is True
    assert ergebnis.befreit is True
    assert "§19 UStG" in (ergebnis.hinweis or "")


def test_normaler_rhythmus_bleibt_unveraendert_nicht_befreit(db):
    db.add(Unternehmen(
        firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort",
        ist_kleinunternehmer=False, voranmeldungsrhythmus="quartal",
    ))
    db.commit()

    ergebnis = ustva_berechnen(zeitraum="2026-Q1", db=db)

    assert ergebnis.befreit is False
    assert ergebnis.hinweis is None
