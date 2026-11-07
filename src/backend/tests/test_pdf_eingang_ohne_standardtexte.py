"""
Issue #504: Eingangsrechnungen bekamen im PDF die eigenen Standard-Einleitungs-/Schlusstexte
der Ausgangsrechnung, Vorlage 1 zusätzlich die Anrede („Hallo …“ an den Lieferanten) und ihren
eingebauten Satz „Vielen Dank für Dein Vertrauen …“. Eine Eingangsrechnung bildet das Dokument
des Lieferanten ab - die Standardtexte entfallen dort. Ausgangsrechnungen bleiben unverändert.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import Kunde, Lieferant, Rechnung, Rechnungsposition
from utils.pdf_rechnung import generate_rechnung_pdf
from utils.pdf_rechnung_vorlage1 import generate_rechnung_pdf_vorlage1

UNT_DICT = {
    "firmenname": "Test GmbH", "vorname": "", "nachname": "",
    "strasse": "Teststr.", "hausnummer": "1", "plz": "12345", "ort": "Testort",
    "land": "DE", "ust_idnr": "DE111111111", "steuernummer": "", "iban": "", "bic": "",
    "telefon": "", "email": "", "webseite": "", "ist_kleinunternehmer": False,
    "einleitungstext": "STANDARD-EINLEITUNG",
    "schlusstext": "STANDARD-SCHLUSS",
    "anrede_text": "Sehr geehrte Damen und Herren,",
}


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _pdf_text(pdf_bytes: bytes) -> str:
    return "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf_bytes)).pages)


def _rechnung(db, typ: str, **felder) -> Rechnung:
    partner = Kunde(firmenname="Kunde AG") if typ == "ausgang" else Lieferant(firmenname="Lieferant AG")
    db.add(partner)
    db.flush()
    rechnung = Rechnung(
        typ=typ, rechnungsnummer=f"{typ}-1", datum=date(2026, 9, 24),
        kunde_id=partner.id if typ == "ausgang" else None,
        lieferant_id=partner.id if typ == "eingang" else None,
        netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("19.00"), brutto_gesamt=Decimal("119.00"),
        ist_entwurf=False, **felder,
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Leistung", menge=Decimal("1"),
        einheit="Stk.", netto=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        brutto=Decimal("119.00"),
    ))
    db.commit()
    db.refresh(rechnung)
    return rechnung


@pytest.mark.parametrize("erzeuge", [generate_rechnung_pdf, generate_rechnung_pdf_vorlage1])
def test_eingangsrechnung_ohne_standardtexte_und_anrede(db, erzeuge):
    text = _pdf_text(erzeuge(_rechnung(db, "eingang"), UNT_DICT))
    assert "STANDARD-EINLEITUNG" not in text
    assert "STANDARD-SCHLUSS" not in text
    assert "Sehr geehrte Damen und Herren" not in text
    assert "Vielen Dank für Dein Vertrauen" not in text


@pytest.mark.parametrize("erzeuge", [generate_rechnung_pdf, generate_rechnung_pdf_vorlage1])
def test_ausgangsrechnung_behaelt_standardtexte_und_anrede(db, erzeuge):
    text = _pdf_text(erzeuge(_rechnung(db, "ausgang"), UNT_DICT))
    assert "STANDARD-EINLEITUNG" in text
    assert "STANDARD-SCHLUSS" in text
    assert "Sehr geehrte Damen und Herren" in text


def test_vorlage1_ausgang_ohne_text_behaelt_eingebauten_satz(db):
    unt = {**UNT_DICT, "einleitungstext": ""}
    text = _pdf_text(generate_rechnung_pdf_vorlage1(_rechnung(db, "ausgang"), unt))
    assert "Vielen Dank für Dein Vertrauen" in text


def test_eigener_text_an_eingangsrechnung_bleibt(db):
    """Steht ausdrücklich ein Text an der Eingangsrechnung, wird er weiter gedruckt."""
    rechnung = _rechnung(db, "eingang", einleitungstext="EIGENER-TEXT")
    text = _pdf_text(generate_rechnung_pdf(rechnung, UNT_DICT))
    assert "EIGENER-TEXT" in text
