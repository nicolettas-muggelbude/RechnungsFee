"""
Regressionstests für Issue #365: Bei Reverse Charge (§3a Abs. 2, §13b-Hinweis) und
innergemeinschaftlicher Lieferung (§4 Nr. 1b/§6a) verlangt §14a Abs. 1 UStG die Angabe der
USt-IdNr. des Leistungsempfängers auf der Rechnung (anders als beim rein inländischen
§13b Abs. 2/Abs. 5-Fall, wo das nur "sofern vorhanden" gilt). Prüft, dass die Kunden-USt-IdNr.
auf dem PDF erscheint, wenn einer der beiden Fälle aktiv ist - und sonst nicht.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import Kunde, Rechnung, Rechnungsposition
from utils.pdf_rechnung import generate_rechnung_pdf


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


UNT_DICT = {
    "firmenname": "Test GmbH", "vorname": "", "nachname": "",
    "strasse": "Teststr.", "hausnummer": "1", "plz": "12345", "ort": "Testort",
    "land": "DE", "ust_idnr": "DE111111111", "steuernummer": "", "iban": "", "bic": "",
    "telefon": "", "email": "", "webseite": "", "ist_kleinunternehmer": False,
}


def _pdf_text(rechnung) -> str:
    pdf_bytes = generate_rechnung_pdf(rechnung, UNT_DICT)
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() for page in reader.pages)


def _rechnung(db, **kwargs) -> Rechnung:
    kunde = Kunde(firmenname="Kunde EU SARL", strasse="Rue Test", hausnummer="1",
                   plz="75001", ort="Paris", land="FR", ust_idnr="FR12345678901")
    db.add(kunde)
    db.flush()
    rechnung = Rechnung(
        typ="ausgang", rechnungsnummer="RE-2026-1", datum=date(2026, 8, 20),
        kunde_id=kunde.id, netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("0.00"),
        brutto_gesamt=Decimal("100.00"), ist_entwurf=False,
        **kwargs,
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Beratung", menge=Decimal("1"),
        einheit="Stk.", netto=Decimal("100.00"), ust_satz=Decimal("0"), ust_betrag=Decimal("0.00"),
        brutto=Decimal("100.00"),
    ))
    db.commit()
    db.refresh(rechnung)
    return rechnung


def test_reverse_charge_zeigt_kunden_ust_idnr(db):
    rechnung = _rechnung(db, ist_reverse_charge=True)
    text = _pdf_text(rechnung)
    assert "USt-IdNr. Kunde: FR12345678901" in text


def test_ig_lieferung_zeigt_kunden_ust_idnr(db):
    rechnung = _rechnung(db, ist_eu_lieferung=True)
    text = _pdf_text(rechnung)
    assert "USt-IdNr. Kunde: FR12345678901" in text


def test_normale_rechnung_zeigt_keine_kunden_ust_idnr(db):
    rechnung = _rechnung(db)
    text = _pdf_text(rechnung)
    assert "USt-IdNr. Kunde:" not in text


def test_reverse_charge_ohne_kunden_ust_idnr_zeigt_keine_leere_zeile(db):
    kunde = Kunde(firmenname="Kunde ohne IdNr", strasse="Weg", hausnummer="2",
                   plz="1000", ort="Wien", land="AT", ust_idnr=None)
    db.add(kunde)
    db.flush()
    rechnung = Rechnung(
        typ="ausgang", rechnungsnummer="RE-2026-2", datum=date(2026, 8, 20),
        kunde_id=kunde.id, netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("0.00"),
        brutto_gesamt=Decimal("100.00"), ist_entwurf=False, ist_reverse_charge=True,
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Beratung", menge=Decimal("1"),
        einheit="Stk.", netto=Decimal("100.00"), ust_satz=Decimal("0"), ust_betrag=Decimal("0.00"),
        brutto=Decimal("100.00"),
    ))
    db.commit()
    db.refresh(rechnung)

    text = _pdf_text(rechnung)
    assert "USt-IdNr. Kunde:" not in text
