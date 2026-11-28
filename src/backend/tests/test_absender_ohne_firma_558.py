"""
Issue #558: Ohne Firmennamen (Freiberufler nur mit Vor-/Nachname) begann die Absenderzeile über
dem Adressfeld direkt mit der Straße. Jetzt steht dort der Name - in beiden Rechnungsvorlagen
(Vorlage 1 erbt die Kopfzeile) und in der Mahnung.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import Rechnung, Rechnungsposition
from utils.pdf_rechnung import generate_rechnung_pdf
from utils.pdf_rechnung_base import absender_name
from utils.pdf_rechnung_vorlage1 import generate_rechnung_pdf_vorlage1

UNT = {
    "firmenname": "", "vorname": "Markus", "nachname": "Muster",
    "strasse": "Lindenweg", "hausnummer": "3", "plz": "12345", "ort": "Teststadt",
    "steuernummer": "12/345/67890", "ist_kleinunternehmer": True,
}


def test_absender_name():
    assert absender_name(UNT) == "Markus Muster"
    assert absender_name({**UNT, "firmenname": "Muster Coaching"}) == "Muster Coaching"
    assert absender_name({"firmenname": None, "vorname": None, "nachname": None}) == ""


@pytest.fixture
def rechnung():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    r = Rechnung(typ="ausgang", rechnungsnummer="RE-260001", datum=date(2026, 11, 16), partner_freitext="Kunde",
                 netto_gesamt=Decimal("100"), ust_gesamt=Decimal("0"), brutto_gesamt=Decimal("100"),
                 ist_entwurf=False, eingabemodus="brutto")
    db.add(r)
    db.flush()
    db.add(Rechnungsposition(rechnung_id=r.id, position_nr=1, beschreibung="Beratung", menge=Decimal("1"),
                             netto=Decimal("100"), ust_satz=Decimal("0"), brutto=Decimal("100")))
    db.commit()
    db.refresh(r)
    yield r
    db.close()


@pytest.mark.parametrize("erzeuge", [generate_rechnung_pdf, generate_rechnung_pdf_vorlage1])
def test_absenderzeile_mit_name(rechnung, erzeuge):
    text = PdfReader(BytesIO(erzeuge(rechnung, UNT, ist_netto=False))).pages[0].extract_text()
    assert "Markus Muster  ·  Lindenweg 3" in text
