"""
Nebenfund Issue #502: Buchungen mit Zahlungsart „Verrechnung“ (Guthaben mit einer Rechnung
verrechnet) haben kein Gegenkonto und werden im DATEV-Export übersprungen - anders als
„Keine“ fehlt dort aber echter Aufwand/Erlös samt Steuer. Bis zum Verrechnungskonto
(Roadmap v0.7.9) meldet der Export sie einzeln mit Belegnummer.
"""
import asyncio
from datetime import date
from decimal import Decimal
from urllib.parse import unquote

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.datev import datev_buchungsstapel
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Unternehmen
from main import app


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(
        firmenname="Testfirma", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort",
        kontenrahmen="SKR03", geschaeftsjahr_beginn=1, datev_konto_bank="1200",
    ))
    kat = Kategorie(name="Bürobedarf", kontenart="Aufwand", konto_skr03="4930", konto_skr04="6815")
    session.add(kat)
    session.flush()

    def eintrag(belegnr: str, zahlungsart: str, betrag: str) -> Journaleintrag:
        return Journaleintrag(
            datum=date(2026, 3, 5), belegnr=belegnr, beschreibung=f"Test {zahlungsart}",
            kategorie_id=kat.id, konto_skr03="4930", konto_skr04="6815", zahlungsart=zahlungsart,
            art="Ausgabe", netto_betrag=Decimal(betrag), ust_satz=Decimal("0"), ust_betrag=Decimal("0"),
            vorsteuer_betrag=Decimal("0"), brutto_betrag=Decimal(betrag),
        )

    session.add_all([
        eintrag("J-1", "Bank", "10.00"),
        eintrag("J-2", "Verrechnung", "20.00"),
        eintrag("J-Ü3", "Verrechnung", "5.00"),
        eintrag("J-4", "Keine", "3.00"),
    ])
    session.commit()
    yield session
    session.close()


def test_export_meldet_verrechnungen_mit_belegnummer(db):
    response = datev_buchungsstapel(von=date(2026, 1, 1), bis=date(2026, 12, 31), mit_belegen=False, db=db)
    asyncio.run(_leeren(response))
    assert response.headers["X-Datev-Eintraege"] == "1"
    assert response.headers["X-Datev-Uebersprungen"] == "3"
    assert response.headers["X-Datev-Verrechnung"] == "2"
    assert unquote(response.headers["X-Datev-Verrechnung-Belege"]).split(",") == ["J-2", "J-Ü3"]


def test_export_ohne_verrechnung_meldet_null(db):
    db.query(Journaleintrag).filter(Journaleintrag.zahlungsart == "Verrechnung").delete()
    db.commit()
    response = datev_buchungsstapel(von=date(2026, 1, 1), bis=date(2026, 12, 31), mit_belegen=False, db=db)
    assert response.headers["X-Datev-Verrechnung"] == "0"
    assert response.headers["X-Datev-Verrechnung-Belege"] == ""


def test_zaehl_header_fuer_frontend_freigegeben():
    """Ohne expose_headers kann die installierte App (anderer Origin) die Header nicht lesen."""
    cors = next(m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware")
    freigegeben = set(cors.kwargs["expose_headers"])
    for header in ("X-Datev-Eintraege", "X-Datev-Uebersprungen", "X-Datev-LeerKonto", "X-Datev-Belege",
                   "X-Datev-Verrechnung", "X-Datev-Verrechnung-Belege"):
        assert header in freigegeben, header


async def _leeren(response) -> None:
    async for _ in response.body_iterator:
        pass
