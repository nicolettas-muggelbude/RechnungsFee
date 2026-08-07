"""
Regressionstest für Issue #343 (DATEV-Export mit Skonto).

Bug: Der Skonto-Journaleintrag wurde im DATEV-Export mit Gegenkonto=Bank exportiert,
obwohl beim Skonto kein zusätzlicher Zahlungsfluss stattfindet - die tatsächliche
Zahlung (bereits netto nach Skonto) steckt vollständig in der Hauptbuchung. Dadurch
kam beim Erlöskonto nur der geminderte Betrag an (116,62 statt 119,00 bei einer
119,00-€-Rechnung mit 2% Skonto), und die Bank wurde durch die zweite Buchung
zusätzlich um den Skonto-Betrag reduziert - das Skonto wurde faktisch doppelt
abgezogen. Gegenkonto der Skonto-Zeile muss stattdessen das Erlöskonto der
zugehörigen Hauptbuchung sein.
"""
import asyncio
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.datev import datev_buchungsstapel
from database.connection import Base
from database.models import Journaleintrag, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _unternehmen(db) -> Unternehmen:
    unt = Unternehmen(
        firmenname="Test GmbH", strasse="Teststr.", hausnummer="1",
        plz="12345", ort="Testort", kontenrahmen="SKR03",
        geschaeftsjahr_beginn=1, datev_beraternummer="1001", datev_mandantennummer="1",
        datev_konto_bank="1200",
    )
    db.add(unt)
    db.commit()
    return unt


async def _lese_body(response) -> bytes:
    return b"".join([chunk async for chunk in response.body_iterator])


def _buchungszeilen(db, von: date, bis: date) -> list[list[str]]:
    response = datev_buchungsstapel(von=von, bis=bis, mit_belegen=False, db=db)
    data = asyncio.run(_lese_body(response))
    zeilen = data.decode("utf-8-sig").splitlines()
    return [z.split(";") for z in zeilen[2:] if z]


def test_skonto_gegenkonto_ist_erloeskonto_nicht_bank(db):
    """Exakter Repro-Fall aus Issue #343: 119,00-€-Rechnung, 2% Skonto, bezahlt 116,62 €."""
    _unternehmen(db)
    db.add(Journaleintrag(
        datum=date(2026, 6, 1), belegnr="RE-1", beschreibung="Zahlung Rechnung RE-2026-001",
        zahlungsart="Bank", art="Einnahme", rechnung_id=42,
        netto_betrag=Decimal("98.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("18.62"),
        brutto_betrag=Decimal("116.62"), vorsteuerabzug=False,
        konto_skr03="8400", immutable=True,
    ))
    db.add(Journaleintrag(
        datum=date(2026, 6, 1), belegnr="RE-2", beschreibung="Skonto RE-2026-001",
        zahlungsart="Skonto", art="Ausgabe", rechnung_id=42,
        netto_betrag=Decimal("2.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("0.38"),
        brutto_betrag=Decimal("2.38"), vorsteuerabzug=False,
        konto_skr03="8736", immutable=True,
    ))
    db.commit()

    zeilen = _buchungszeilen(db, date(2026, 6, 1), date(2026, 6, 30))
    assert len(zeilen) == 2

    haupt = next(z for z in zeilen if z[6] == "8400")
    skonto = next(z for z in zeilen if z[6] == "8736")

    assert haupt[0] == "116,62"
    assert haupt[1] == "H"
    assert haupt[7] == "1200"  # Gegenkonto Bank - unveraendert

    assert skonto[0] == "2,38"
    assert skonto[1] == "S"
    # Der eigentliche Fix: Gegenkonto ist das Erloeskonto der Hauptbuchung, nicht die Bank
    assert skonto[7] == "8400"

    # Kombinierter Effekt: Erloeskonto (Haben) summiert sich auf den vollen Rechnungsbetrag
    erloes_haben = Decimal(haupt[0].replace(",", ".")) + Decimal(skonto[0].replace(",", "."))
    assert erloes_haben == Decimal("119.00")


def test_erhaltene_skonti_eingangsrechnung_gegenkonto_ist_aufwandskonto(db):
    """Gegenrichtung: Eingangsrechnung mit "Erhaltene Skonti" (art-Richtung invertiert
    gegenüber der Ausgangsrechnung) - Gegenkonto muss das Aufwandskonto der Hauptbuchung sein."""
    _unternehmen(db)
    db.add(Journaleintrag(
        datum=date(2026, 6, 5), belegnr="AG-1", beschreibung="Zahlung Eingangsrechnung",
        zahlungsart="Bank", art="Ausgabe", rechnung_id=7,
        netto_betrag=Decimal("98.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("18.62"),
        brutto_betrag=Decimal("116.62"), vorsteuerabzug=True,
        konto_skr03="4930", immutable=True,
    ))
    db.add(Journaleintrag(
        datum=date(2026, 6, 5), belegnr="AG-2", beschreibung="Erhaltene Skonti",
        zahlungsart="Skonto", art="Einnahme", rechnung_id=7,
        netto_betrag=Decimal("2.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("0.38"),
        brutto_betrag=Decimal("2.38"), vorsteuerabzug=False,
        konto_skr03="2401", immutable=True,
    ))
    db.commit()

    zeilen = _buchungszeilen(db, date(2026, 6, 1), date(2026, 6, 30))
    skonto = next(z for z in zeilen if z[6] == "2401")
    assert skonto[7] == "4930"


def test_skonto_ohne_passende_hauptbuchung_faellt_auf_bank_zurueck(db):
    """Kein Sibling-Journaleintrag zur selben rechnung_id/ust_satz gefunden - alter Fallback
    (Bank) bleibt erhalten statt eines Fehlers oder eines leeren Gegenkontos."""
    _unternehmen(db)
    db.add(Journaleintrag(
        datum=date(2026, 6, 1), belegnr="RE-3", beschreibung="Skonto ohne Hauptbuchung",
        zahlungsart="Skonto", art="Ausgabe", rechnung_id=99,
        netto_betrag=Decimal("2.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("0.38"),
        brutto_betrag=Decimal("2.38"), vorsteuerabzug=False,
        konto_skr03="8736", immutable=True,
    ))
    db.commit()

    zeilen = _buchungszeilen(db, date(2026, 6, 1), date(2026, 6, 30))
    assert len(zeilen) == 1
    assert zeilen[0][7] == "1200"
