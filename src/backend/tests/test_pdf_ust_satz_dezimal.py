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
from utils.pdf_rechnung_base import _fmt_ust_satz, _fmt_zahl, _ust_aufschluesselung


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


# --- Menge, Rabatt und Skonto im deutschen Zahlenformat -------------------------------------
# In Angeboten erschien die Menge als "1.5"/"2.5" und der Rechnungsrabatt als "Rabatt 10.00 %",
# während Geldbeträge bereits korrekt deutsch formatiert waren ("1.966,50 €"). Skonto wurde
# über :.0f auf eine ganze Zahl gerundet (1,5 % → "2%"), und _fmt_ust_satz() lieferte für
# glatte Zehner über Decimal.normalize() Exponentenschreibweise (10 % → "1E+1 %").

def _rechnung_mit_mengen(db, mengen, pos_rabatt="0", **rechnung_felder) -> Rechnung:
    kunde = Kunde(firmenname="Webkunde", strasse="Hofweg", hausnummer="1", plz="12345", ort="Testort", land="DE")
    db.add(kunde)
    db.flush()
    einzelpreis = Decimal("80.00")
    zeilen = [(Decimal(m), (einzelpreis * Decimal(m)).quantize(Decimal("0.01"))) for m in mengen]
    netto = sum(n for _, n in zeilen)
    ust = (netto * Decimal("0.19")).quantize(Decimal("0.01"))
    felder = dict(
        typ="ausgang", rechnungsnummer="ANG-260001", datum=date(2026, 9, 24),
        kunde_id=kunde.id, netto_gesamt=netto, ust_gesamt=ust,
        brutto_gesamt=netto + ust, ist_entwurf=False, dokument_typ="Angebot",
    )
    felder.update(rechnung_felder)
    rechnung = Rechnung(**felder)
    db.add(rechnung)
    db.flush()
    for nr, (menge, zeile_netto) in enumerate(zeilen, start=1):
        zeile_ust = (zeile_netto * Decimal("0.19")).quantize(Decimal("0.01"))
        db.add(Rechnungsposition(
            rechnung_id=rechnung.id, position_nr=nr, beschreibung=f"Leistung {nr}", menge=menge,
            einheit="Std.", netto=einzelpreis, ust_satz=Decimal("19"), ust_betrag=zeile_ust,
            brutto=zeile_netto + zeile_ust, rabatt_prozent=Decimal(pos_rabatt),
        ))
    db.commit()
    db.refresh(rechnung)
    return rechnung


GENERATOREN = [generate_rechnung_pdf, generate_rechnung_pdf_vorlage1]


def test_vorlage0_menge_mit_komma(db):
    rechnung = _rechnung_mit_mengen(db, ["1.5", "2.5"])
    text = _pdf_text(generate_rechnung_pdf(rechnung, UNT_DICT))
    assert "1,5" in text and "2,5" in text
    assert "1.5" not in text and "2.5" not in text


def test_vorlage0_storno_menge_mit_komma_und_vorzeichen(db):
    rechnung = _rechnung_mit_mengen(db, ["1.5"], dokument_typ="Rechnung", storniert=True,
                                    storno_datum=date(2026, 9, 25))
    text = _pdf_text(generate_rechnung_pdf(rechnung, UNT_DICT))
    assert "-1,5" in text
    assert "1.5" not in text


def test_vorlage1_lieferschein_menge_mit_komma(db):
    rechnung = _rechnung_mit_mengen(db, ["1.5"], dokument_typ="Lieferschein")
    text = _pdf_text(generate_rechnung_pdf_vorlage1(rechnung, UNT_DICT))
    assert "1,5" in text
    assert "1.5" not in text


@pytest.mark.parametrize("generator", GENERATOREN)
def test_rechnungsrabatt_ohne_ueberfluessige_nullen(db, generator):
    rechnung = _rechnung_mit_mengen(db, ["1.5", "2.5"], rabatt_prozent=Decimal("10.00"))
    text = _pdf_text(generator(rechnung, UNT_DICT))
    assert "Rabatt 10 %" in text
    assert "10.00" not in text


@pytest.mark.parametrize("generator", GENERATOREN)
def test_rechnungsrabatt_mit_nachkommastelle(db, generator):
    rechnung = _rechnung_mit_mengen(db, ["1"], rabatt_prozent=Decimal("12.50"))
    text = _pdf_text(generator(rechnung, UNT_DICT))
    assert "Rabatt 12,5 %" in text


@pytest.mark.parametrize("generator", GENERATOREN)
def test_positionsrabatt_mit_komma(db, generator):
    rechnung = _rechnung_mit_mengen(db, ["1"], pos_rabatt="7.50")
    text = _pdf_text(generator(rechnung, UNT_DICT))
    assert "7,5 % Rabatt" in text
    assert "7.50" not in text


@pytest.mark.parametrize("generator", GENERATOREN)
def test_skonto_mit_nachkommastelle(db, generator):
    unt = {**UNT_DICT, "iban": "DE89370400440532013000", "bic": "COBADEFFXXX"}
    rechnung = _rechnung_mit_mengen(db, ["1"], dokument_typ="Rechnung",
                                    skonto_prozent=Decimal("1.50"), skonto_tage=10)
    text = _pdf_text(generator(rechnung, unt))
    assert "1,5%" in text
    assert "2%" not in text


@pytest.mark.parametrize("satz,erwartet", [("10", "10"), ("20.00", "20"), ("19", "19"), ("7.8", "7,8")])
def test_fmt_ust_satz_ohne_exponentenschreibweise(satz, erwartet):
    assert _fmt_ust_satz(Decimal(satz)) == erwartet


@pytest.mark.parametrize("wert,erwartet", [
    ("1", "1"), ("12.000", "12"), ("1.5", "1,5"), ("0.25", "0,25"), ("2.125", "2,125"),
    ("10.00", "10"), ("1250", "1.250"), ("1250.5", "1.250,5"), ("-1.5", "-1,5"), ("0", "0"),
])
def test_fmt_zahl(wert, erwartet):
    assert _fmt_zahl(Decimal(wert)) == erwartet
