"""
Regressionstest für Issue #406 (aus Discussion #381): Eigene USt-Sätze mit Nachkommastelle
(z.B. 7,8 % - Pauschalierung für Land-/Forstwirtschaft, §24 UStG) wurden in der
PDF-Positionszeile auf eine ganze Zahl abgeschnitten (int(pos.ust_satz)) statt die
Nachkommastelle anzuzeigen - "7 %" statt "7,8 %". Berechnung/Speicherung waren davon nicht
betroffen, reiner Anzeigefehler.

Zusätzlich Nebenfund beim Beheben: _ust_aufschluesselung() gruppierte den
USt-Zusammenfassungsblock nach demselben abgeschnittenen Integer als Dictionary-Key - zwei
Sätze, die zufällig auf denselben Integer abschneiden (z.B. 7,8 % und das gesetzliche 7 % auf
derselben Rechnung), hätten ihre Summen unbemerkt in einen gemeinsamen Bucket zusammengerechnet.
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
from utils.pdf_rechnung_vorlage1 import generate_rechnung_pdf_vorlage1
from utils.pdf_rechnung_base import _ust_aufschluesselung


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


def _pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() for page in reader.pages)


def _rechnung_mit_satz(db, satz: str, ust_betrag: str) -> Rechnung:
    kunde = Kunde(firmenname="Achtsamkeitshof", strasse="Hofweg", hausnummer="1", plz="97640", ort="Bad Königshofen", land="DE")
    db.add(kunde)
    db.flush()
    netto = Decimal("1.00")
    ust = Decimal(ust_betrag)
    rechnung = Rechnung(
        typ="ausgang", rechnungsnummer="RE-2026-1", datum=date(2026, 9, 24),
        kunde_id=kunde.id, netto_gesamt=netto, ust_gesamt=ust,
        brutto_gesamt=netto + ust, ist_entwurf=False,
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Getreide", menge=Decimal("1"),
        einheit="Stk.", netto=netto, ust_satz=Decimal(satz), ust_betrag=ust,
        brutto=netto + ust,
    ))
    db.commit()
    db.refresh(rechnung)
    return rechnung


def test_vorlage0_zeigt_nachkommastelle_in_positionszeile(db):
    rechnung = _rechnung_mit_satz(db, "7.8", "0.08")
    text = _pdf_text(generate_rechnung_pdf(rechnung, UNT_DICT))
    assert "7,8 %" in text
    assert "7 %" not in text


def test_vorlage1_zeigt_nachkommastelle_in_positionszeile(db):
    rechnung = _rechnung_mit_satz(db, "7.8", "0.08")
    text = _pdf_text(generate_rechnung_pdf_vorlage1(rechnung, UNT_DICT))
    assert "7,8 %" in text
    assert "7 %" not in text


def test_glatte_saetze_zeigen_weiterhin_keine_nachkommastelle(db):
    """Regression: 19 % / 7 % / 0 % dürfen nicht zu '19,0 %' o.ä. werden."""
    rechnung = _rechnung_mit_satz(db, "19", "0.19")
    text = _pdf_text(generate_rechnung_pdf(rechnung, UNT_DICT))
    assert "19 %" in text
    assert "19,0 %" not in text


def test_ust_aufschluesselung_gruppiert_7_8_prozent_getrennt_von_7_prozent():
    """Nebenfund-Regression: 7,8 % und 7 % dürfen nicht mehr in denselben Bucket fallen."""
    pos_78 = type("Pos", (), {"ust_satz": Decimal("7.8"), "brutto": Decimal("107.80"), "ust_betrag": Decimal("7.80")})()
    pos_7 = type("Pos", (), {"ust_satz": Decimal("7"), "brutto": Decimal("107.00"), "ust_betrag": Decimal("7.00")})()

    ergebnis = _ust_aufschluesselung([pos_78, pos_7])

    saetze = {s for s, _, _ in ergebnis}
    assert saetze == {Decimal("7.8"), Decimal("7")}
    ust_by_satz = {s: ust for s, _, ust in ergebnis}
    assert ust_by_satz[Decimal("7.8")] == Decimal("7.80")
    assert ust_by_satz[Decimal("7")] == Decimal("7.00")
