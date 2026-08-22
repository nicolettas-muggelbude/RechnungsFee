"""
Verifikationstest für Issue #364, Schritt 6 (kein Blindfix - erst prüfen ob DATEV-Export für
Gutschriften bereits korrekt ist). datev.py leitet das Soll/Haben-Kennzeichen ausschließlich
aus journal.art ab (nicht aus dem tatsächlichen Vorzeichen von brutto_betrag) und exportiert
den Betrag immer als Magnitude (abs()). Dieser Test dokumentiert das aktuelle Verhalten für
beide Gutschrift-Richtungen - identisch zueinander und konsistent mit der bereits produktiv
genutzten Ausgangsrechnungs-Gutschrift, also kein neu eingeführtes Verhalten.
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
    session.add(Unternehmen(
        firmenname="Test GmbH", strasse="Teststr.", hausnummer="1",
        plz="12345", ort="Testort", kontenrahmen="SKR03",
        geschaeftsjahr_beginn=1, datev_beraternummer="1001", datev_mandantennummer="1",
        datev_konto_bank="1200",
    ))
    session.commit()
    yield session
    session.close()


async def _lese_body(response) -> bytes:
    return b"".join([chunk async for chunk in response.body_iterator])


def _erste_buchungszeile(db, von: date, bis: date) -> list[str]:
    response = datev_buchungsstapel(von=von, bis=bis, mit_belegen=False, db=db)
    data = asyncio.run(_lese_body(response))
    zeilen = data.decode("utf-8-sig").splitlines()
    return zeilen[2].split(";")


def test_negative_ausgangs_gutschrift_umsatz_und_sh(db):
    db.add(Journaleintrag(
        datum=date(2026, 6, 1), belegnr="GS-1", beschreibung="Gutschrift RE-1",
        zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("-100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("-19.00"),
        brutto_betrag=Decimal("-119.00"), vorsteuerabzug=False,
        konto_skr03="8400", immutable=True,
    ))
    db.commit()

    felder = _erste_buchungszeile(db, date(2026, 6, 1), date(2026, 6, 30))
    umsatz, sh = felder[0], felder[1]
    # Aktuelles (bestehendes) Verhalten: Betrag als Magnitude, S/H unverändert "H" wie bei
    # jeder anderen Einnahme - identisch zu Eingangs-Gutschrift unten (nur art unterscheidet).
    assert umsatz == "119,00"
    assert sh == "H"


def test_negative_eingangs_gutschrift_umsatz_und_sh(db):
    db.add(Journaleintrag(
        datum=date(2026, 6, 1), belegnr="LGS-1", beschreibung="Lieferantengutschrift ER-1",
        zahlungsart="Bank", art="Ausgabe",
        netto_betrag=Decimal("-100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("-19.00"),
        brutto_betrag=Decimal("-119.00"), vorsteuerabzug=True, vorsteuer_betrag=Decimal("-19.00"),
        konto_skr03="4930", immutable=True,
    ))
    db.commit()

    felder = _erste_buchungszeile(db, date(2026, 6, 1), date(2026, 6, 30))
    umsatz, sh = felder[0], felder[1]
    # Konsistent zur Ausgangs-Gutschrift oben: Magnitude + S/H unverändert "S" wie bei jeder
    # anderen Ausgabe. Beide Richtungen verhalten sich also symmetrisch zueinander - kein durch
    # Issue #364 neu eingeführtes Verhalten, sondern die bereits bestehende Konvention.
    assert umsatz == "119,00"
    assert sh == "S"
