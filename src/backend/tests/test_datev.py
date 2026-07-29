"""
Regressionstests für den DATEV-Buchungsstapel-Export (Issue #319).

Bug: Die Umsatz-Spalte enthielt den Netto- statt den Bruttobetrag - DATEV
rechnet die enthaltene Steuer aus diesem Feld selbst heraus (sowohl bei
Automatikkonten als auch bei gesetztem BU-Schlüssel), wodurch alle
steuerbehafteten Buchungen um den USt-Faktor (1,19 bzw. 1,07) zu niedrig
ausfielen - unabhängig von Einnahme/Ausgabe.
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


def _umsatz_und_bu(db, von: date, bis: date) -> tuple[str, str]:
    """Ruft den Export auf und gibt (Umsatz-Feld, BU-Schlüssel-Feld) der ersten Buchungszeile zurück."""
    response = datev_buchungsstapel(von=von, bis=bis, mit_belegen=False, db=db)
    data = asyncio.run(_lese_body(response))
    zeilen = data.decode("utf-8-sig").splitlines()
    felder = zeilen[2].split(";")  # 0=Verwaltungssatz, 1=Spaltenköpfe, 2=erste Buchung
    return felder[0], felder[8]


def test_einnahme_automatikkonto_umsatz_ist_brutto(db):
    """Erlöskonto 8400 (DATEV-Automatikkonto, kein BU-Schlüssel) - Umsatz muss brutto sein,
    sonst rechnet DATEV die Steuer faelschlich aus dem (zu niedrigen) Nettobetrag heraus."""
    _unternehmen(db)
    db.add(Journaleintrag(
        datum=date(2026, 6, 1), belegnr="RE-1", beschreibung="Testrechnung",
        zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("1000.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("190.00"),
        brutto_betrag=Decimal("1190.00"), vorsteuerabzug=False,
        konto_skr03="8400", immutable=True,
    ))
    db.commit()

    umsatz, bu = _umsatz_und_bu(db, date(2026, 6, 1), date(2026, 6, 30))
    assert umsatz == "1190,00"
    assert bu == ""


def test_ausgabe_vorsteuer_umsatz_ist_brutto(db):
    """Aufwandskonto mit Vorsteuerabzug 19% (BU-Schlüssel 9) - Umsatz muss ebenfalls brutto sein."""
    _unternehmen(db)
    db.add(Journaleintrag(
        datum=date(2026, 6, 2), belegnr="AG-1", beschreibung="Testausgabe",
        zahlungsart="Bank", art="Ausgabe",
        netto_betrag=Decimal("1000.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("190.00"),
        brutto_betrag=Decimal("1190.00"), vorsteuerabzug=True,
        konto_skr03="4930", immutable=True,
    ))
    db.commit()

    umsatz, bu = _umsatz_und_bu(db, date(2026, 6, 1), date(2026, 6, 30))
    assert umsatz == "1190,00"
    assert bu == "9"


def test_25a_marge_bleibt_unveraendert(db):
    """§25a Differenzbesteuerung: Umsatz ist die Brutto-Marge, nicht der Bug betroffen -
    marge_25a_brutto hat weiterhin Vorrang vor brutto_betrag."""
    _unternehmen(db)
    db.add(Journaleintrag(
        datum=date(2026, 6, 3), belegnr="RE-2", beschreibung="Gebrauchtartikel §25a",
        zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("500.00"), ust_satz=Decimal("0"), ust_betrag=Decimal("0.00"),
        brutto_betrag=Decimal("500.00"), marge_25a_brutto=Decimal("120.00"),
        vorsteuerabzug=False, konto_skr03="8199", immutable=True,
    ))
    db.commit()

    umsatz, _ = _umsatz_und_bu(db, date(2026, 6, 1), date(2026, 6, 30))
    assert umsatz == "120,00"


def test_ohne_steuer_unveraendert(db):
    """ust_satz=0: brutto_betrag == netto_betrag, der Fix aendert hier nichts am Ergebnis."""
    _unternehmen(db)
    db.add(Journaleintrag(
        datum=date(2026, 6, 4), belegnr="RE-3", beschreibung="Steuerfreie Lieferung",
        zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("300.00"), ust_satz=Decimal("0"), ust_betrag=Decimal("0.00"),
        brutto_betrag=Decimal("300.00"), vorsteuerabzug=False,
        konto_skr03="8125", immutable=True,
    ))
    db.commit()

    umsatz, _ = _umsatz_und_bu(db, date(2026, 6, 1), date(2026, 6, 30))
    assert umsatz == "300,00"
