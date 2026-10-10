"""
Regressionstest (Nutzer-Report während Issue #419-Regressionstest, aber unabhängig davon):
eine Rechnung mit zwei unterschiedlichen USt-Sätzen (z.B. 19 % und 7 %) erzeugt bei EINER
Zahlung zwei Journaleinträge (einen je Satz-Gruppe, siehe zahlung_bar_erstellen()). Das PDF
zeigte dafür fälschlich zweimal "Teilbetrag erhalten", obwohl die Rechnung mit einer einzigen
Zahlung vollständig bezahlt wurde - die Wortwahl ("Teilbetrag" vs. voller Betrag) hing bisher
an der Anzahl der Journaleintrag-ZEILEN statt an der Anzahl tatsächlicher Zahlungs-EREIGNISSE
(gruppiert nach Datum + Zahlungsart).
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import Journaleintrag, Kunde, Rechnung, Rechnungsposition
from utils.pdf_rechnung import generate_rechnung_pdf
from utils.pdf_rechnung_vorlage1 import generate_rechnung_pdf_vorlage1


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


def _voll_bezahlte_rechnung_mit_zwei_saetzen(db) -> Rechnung:
    kunde = Kunde(firmenname="Testkunde GmbH", strasse="Hofweg", hausnummer="1", plz="12345", ort="Testort", land="DE")
    db.add(kunde)
    db.flush()
    rechnung = Rechnung(
        typ="ausgang", rechnungsnummer="RE-2026-1", datum=date(2026, 10, 1),
        kunde_id=kunde.id, netto_gesamt=Decimal("1.77"), ust_gesamt=Decimal("0.23"),
        brutto_gesamt=Decimal("2.00"), ist_entwurf=False, zahlungsstatus="bezahlt",
        bezahlt_betrag=Decimal("2.00"),
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Dienstleistung1", menge=Decimal("1"),
        einheit="Stunde", netto=Decimal("0.8403"), ust_satz=Decimal("19"), ust_betrag=Decimal("0.16"),
        brutto=Decimal("1.00"),
    ))
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=2, beschreibung="Dienstleistung2", menge=Decimal("1"),
        einheit="Stunde", netto=Decimal("0.9346"), ust_satz=Decimal("7"), ust_betrag=Decimal("0.07"),
        brutto=Decimal("1.00"),
    ))
    # Eine einzige Zahlung (gleiches Datum, gleiche Zahlungsart) wird beim Buchen auf zwei
    # Journaleintraege aufgeteilt - eine je USt-Satz-Gruppe.
    db.add(Journaleintrag(
        datum=date(2026, 10, 10), belegnr="B1", beschreibung="Zahlung RE-2026-1",
        zahlungsart="Bank", art="Einnahme", netto_betrag=Decimal("0.84"), ust_satz=Decimal("19"),
        ust_betrag=Decimal("0.16"), brutto_betrag=Decimal("1.00"), rechnung_id=rechnung.id,
    ))
    db.add(Journaleintrag(
        datum=date(2026, 10, 10), belegnr="B2", beschreibung="Zahlung RE-2026-1",
        zahlungsart="Bank", art="Einnahme", netto_betrag=Decimal("0.93"), ust_satz=Decimal("7"),
        ust_betrag=Decimal("0.07"), brutto_betrag=Decimal("1.00"), rechnung_id=rechnung.id,
    ))
    db.commit()
    db.refresh(rechnung)
    return rechnung


def test_vorlage0_zeigt_vollen_betrag_nicht_teilbetrag(db):
    rechnung = _voll_bezahlte_rechnung_mit_zwei_saetzen(db)
    text = _pdf_text(generate_rechnung_pdf(rechnung, UNT_DICT))
    assert "Teilbetrag" not in text
    assert "Rechnungsbetrag bereits dankend erhalten" in text
    assert "2,00" in text  # voller Betrag, nicht zweimal 1,00


def test_vorlage1_zeigt_vollen_betrag_nicht_teilbetrag(db):
    rechnung = _voll_bezahlte_rechnung_mit_zwei_saetzen(db)
    text = _pdf_text(generate_rechnung_pdf_vorlage1(rechnung, UNT_DICT))
    assert "Teilbetrag" not in text
    assert "Dankend erhalten am" in text
    assert "2,00" in text
