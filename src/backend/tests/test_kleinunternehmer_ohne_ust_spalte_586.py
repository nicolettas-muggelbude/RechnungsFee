"""
Issue #586: Rechnungen von Kleinunternehmern (§ 19 UStG) zeigen keine Spalte „USt %“ (0 % stünde für
steuerfreie Umsätze) - nur den § 19-Hinweis. Die Betragsspalte heißt „Betrag“ statt Netto/Brutto.
Regelbesteuerte und Eingangsrechnungen behalten die Spalte. Beide Vorlagen, mit und ohne
Positionsnummer/Artikelnummer.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import Artikel, Rechnung, Rechnungsposition
from utils.pdf_rechnung import generate_rechnung_pdf
from utils.pdf_rechnung_vorlage1 import generate_rechnung_pdf_vorlage1

UNT = {"firmenname": "T", "strasse": "S", "hausnummer": "1", "plz": "12345", "ort": "O",
       "steuernummer": "12/345/67890"}


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _rechnung(db, typ="ausgang", ust="0"):
    a = Artikel(artikelnummer=f"ART-{typ}-{ust}", typ="artikel", bezeichnung="Leiste", einheit="Stück",
                steuersatz=Decimal(ust), vk_brutto=Decimal("10"), vk_netto=Decimal("10"), artikelcode="PR-1")
    db.add(a)
    db.flush()
    r = Rechnung(typ=typ, rechnungsnummer="RE-1", datum=date(2026, 11, 1), partner_freitext="Kunde",
                 netto_gesamt=Decimal("10"), ust_gesamt=Decimal("0"), brutto_gesamt=Decimal("10"),
                 ist_entwurf=False, eingabemodus="brutto")
    db.add(r)
    db.flush()
    db.add(Rechnungsposition(rechnung_id=r.id, position_nr=1, beschreibung="Leiste", menge=Decimal("1"),
                             netto=Decimal("10"), ust_satz=Decimal(ust), brutto=Decimal("10"), artikel_id=a.id))
    db.commit()
    db.refresh(r)
    return r


def _text(r, unt, erzeuge, ist_netto):
    pdf = erzeuge(r, unt, ist_netto=ist_netto)
    return "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)


VARIANTEN = [
    {}, {"pdf_positionsnummern": True}, {"pdf_artikelnummer": True},
    {"pdf_positionsnummern": True, "pdf_artikelnummer": True},
]


@pytest.mark.parametrize("erzeuge", [generate_rechnung_pdf, generate_rechnung_pdf_vorlage1])
@pytest.mark.parametrize("ist_netto", [True, False])
@pytest.mark.parametrize("extra", VARIANTEN)
def test_kleinunternehmer_ohne_ust_spalte(db, erzeuge, ist_netto, extra):
    text_ = _text(_rechnung(db), {**UNT, "ist_kleinunternehmer": True, **extra}, erzeuge, ist_netto)
    assert "USt %" not in text_ and "0 %" not in text_
    assert "Betrag" in text_ and "Leiste" in text_ and "10,00" in text_
    assert "§ 19 UStG" in text_


@pytest.mark.parametrize("erzeuge", [generate_rechnung_pdf, generate_rechnung_pdf_vorlage1])
def test_regelbesteuert_und_eingang_behalten_spalte(db, erzeuge):
    assert "USt %" in _text(_rechnung(db, ust="19"), {**UNT, "ist_kleinunternehmer": False}, erzeuge, True)
    assert "USt %" in _text(_rechnung(db, typ="eingang"), {**UNT, "ist_kleinunternehmer": True}, erzeuge, True)
