"""
EÜR – Einnahmen-Überschuss-Rechnung (Anlage EÜR 2025)

Berechnet EÜR-Zeilen aus Journalbuchungen nach Ist-Versteuerung (Zuflussprinzip).

Besonderheiten:
  - Zeile 17: vereinnahmte USt = Summe ust_betrag aller Einnahmen
  - Zeile 57: abziehbare Vorsteuer = Summe vorsteuer_betrag aller Ausgaben
  - Alle anderen Zeilen: netto_betrag aus kategorie.euer_zeile
  - Anlage-Buchungen (kontenart=Anlage, euer_zeile=None) → AVEUR-Hinweis
  - km-Pauschale: brutto_betrag enthält bereits km×0,30 €
"""

import calendar
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Journaleintrag, Kategorie, Unternehmen

router = APIRouter(prefix="/api/euer", tags=["EÜR"])

ZERO = Decimal("0.00")

# ---------------------------------------------------------------------------
# EÜR-Zeilen-Definitionen (Anlage EÜR 2025)
# ---------------------------------------------------------------------------

# (bezeichnung, abschnitt)
EUR_ZEILEN_META: dict[int, tuple[str, str]] = {
    12:  ("Betriebseinnahmen als Betriebseinnahmen",                            "A"),
    13:  ("Betriebseinnahmen als Betriebseinnahmen (steuerfrei)",               "A"),
    14:  ("Sonstige steuerfreie Einnahmen",                                     "A"),
    17:  ("Vereinnahmte Umsatzsteuer",                                          "A"),
    18:  ("Vom FA erstattete / verrechnete Umsatzsteuer",                       "A"),
    27:  ("Waren, Rohstoffe, Hilfsstoffe (ohne USt)",                           "B"),
    28:  ("Bezogene Leistungen (ohne USt)",                                     "B"),
    29:  ("Fremdleistungen (ohne USt)",                                         "B"),
    30:  ("Löhne, Gehälter, Sozialversicherung",                               "B"),
    36:  ("Geringwertige Wirtschaftsgüter (GWG)",                               "B"),
    39:  ("Miete / Pacht für Geschäftsräume",                                   "B"),
    41:  ("Nebenkosten für Geschäftsräume",                                     "B"),
    43:  ("Aufwendungen für Telekommunikation",                                 "B"),
    44:  ("Reisekosten (Übernachtung, Nebenkosten)",                            "B"),
    46:  ("Kosten für Buchführung, Steuerberatung, Rechtsberatung",             "B"),
    47:  ("Miet- und Leasingkosten für Wirtschaftsgüter",                       "B"),
    57:  ("Abziehbare Vorsteuerbeträge",                                        "B"),
    49:  ("Versicherungen (betrieblich)",                                        "B"),
    51:  ("Aufwendungen für Bürobedarf, Porto, Fachliteratur",                  "B"),
    52:  ("Aufwendungen für Abfallbeseitigung, Reinigung",                      "B"),
    54:  ("Aufwendungen für Werbung",                                           "B"),
    56:  ("Schuldzinsen",                                                       "B"),
    58:  ("Umsatzsteuer-Vorauszahlungen, sonstige Aufwendungen",               "B"),
    60:  ("Sonstige Betriebsausgaben",                                          "B"),
    63:  ("Aufwendungen für Bewirtung (70 % abzugsfähig)",                      "B"),
    65:  ("Aufwendungen für häusliches Arbeitszimmer",                          "B"),
    68:  ("Leasingkosten für Kraftfahrzeuge",                                   "B"),
    69:  ("KFZ-Steuer, KFZ-Versicherung",                                       "B"),
    70:  ("Übrige KFZ-Kosten, km-Pauschale, Fahrtkosten ÖPNV",                "B"),
    106: ("Entnahmen (Hinweiszeile, kein GuV-Einfluss)",                        "H"),
    107: ("Einlagen (Hinweiszeile, kein GuV-Einfluss)",                         "H"),
}

ABSCHNITT_LABEL = {
    "A": "A – Betriebseinnahmen",
    "B": "B – Betriebsausgaben",
    "H": "Entnahmen / Einlagen (nachrichtlich)",
}

EINNAHMEN_ZEILEN = {z for z, (_, ab) in EUR_ZEILEN_META.items() if ab == "A" and z not in (106, 107)}
AUSGABEN_ZEILEN  = {z for z, (_, ab) in EUR_ZEILEN_META.items() if ab == "B" and z not in (106, 107)}


# ---------------------------------------------------------------------------
# Berechnung
# ---------------------------------------------------------------------------

def _berechne_euer(jahr: int, db: Session) -> dict:
    von = __import__("datetime").date(jahr, 1, 1)
    bis = __import__("datetime").date(jahr, 12, 31)

    eintraege = (
        db.query(Journaleintrag)
        .filter(Journaleintrag.datum >= von, Journaleintrag.datum <= bis)
        .all()
    )

    zeilen: dict[int, Decimal] = {}
    anlage_summe = ZERO

    for e in eintraege:
        kat: Optional[Kategorie] = e.kategorie
        euer_zeile = kat.euer_zeile if kat else None

        # Anlage-Buchungen (KFZ-Kauf, EDV etc.) → AVEUR-Hinweis
        if kat and kat.kontenart == "Anlage":
            anlage_summe += (e.brutto_betrag or ZERO)
            continue

        if euer_zeile is not None:
            zeilen[euer_zeile] = zeilen.get(euer_zeile, ZERO) + (e.netto_betrag or ZERO)

        # Zeile 17: vereinnahmte USt aus Einnahmen (Anlage EÜR 2025)
        if e.art == "Einnahme" and e.ust_betrag and e.ust_betrag > 0:
            zeilen[17] = zeilen.get(17, ZERO) + e.ust_betrag

        # Zeile 57: abziehbare Vorsteuer aus Ausgaben (Anlage EÜR 2025)
        if e.art == "Ausgabe" and e.vorsteuer_betrag and e.vorsteuer_betrag > 0:
            zeilen[57] = zeilen.get(57, ZERO) + e.vorsteuer_betrag

    # Runden
    q = Decimal("0.01")
    zeilen = {z: v.quantize(q, ROUND_HALF_UP) for z, v in zeilen.items() if v != ZERO}

    summe_einnahmen = sum(zeilen.get(z, ZERO) for z in EINNAHMEN_ZEILEN)
    summe_ausgaben  = sum(zeilen.get(z, ZERO) for z in AUSGABEN_ZEILEN)
    gewinn_verlust  = (summe_einnahmen - summe_ausgaben).quantize(q, ROUND_HALF_UP)

    return {
        "jahr": jahr,
        "zeilen": zeilen,
        "summe_einnahmen": summe_einnahmen.quantize(q, ROUND_HALF_UP),
        "summe_ausgaben":  summe_ausgaben.quantize(q, ROUND_HALF_UP),
        "gewinn_verlust":  gewinn_verlust,
        "anlage_zugaenge": anlage_summe.quantize(q, ROUND_HALF_UP),
    }


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def _generate_pdf(daten: dict, unt: Unternehmen) -> bytes:
    from fpdf import FPDF

    def _fonts() -> Path:
        import sys
        if getattr(sys, "frozen", False):
            p = Path(sys._MEIPASS) / "fonts"  # type: ignore[attr-defined]
            if (p / "DejaVuSans.ttf").exists():
                return p
        local = Path(__file__).parent.parent / "fonts"
        if (local / "DejaVuSans.ttf").exists():
            return local
        for p in [Path("/usr/share/fonts/truetype/dejavu"), Path("/usr/share/fonts/dejavu")]:
            if (p / "DejaVuSans.ttf").exists():
                return p
        raise FileNotFoundError("DejaVu-Fonts nicht gefunden.")

    BLAU = (37, 99, 235); GRAU = (245, 246, 248); DUNKEL = (30, 41, 59); MITTEL = (100, 116, 139)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    fonts = _fonts()
    pdf.add_font("DejaVu", "",  str(fonts / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(fonts / "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(True, margin=20)

    pdf.set_fill_color(*BLAU)
    pdf.rect(0, 0, 210, 18, "F")
    pdf.set_font("DejaVu", "B", 11)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(20, 5)
    pdf.cell(0, 8, f"Einnahmen-Überschuss-Rechnung {daten['jahr']} – Anzeigehilfe", ln=True)
    pdf.set_text_color(*DUNKEL)

    name = unt.firmenname or f"{unt.vorname or ''} {unt.nachname or ''}".strip()
    pdf.set_xy(20, 24)
    pdf.set_font("DejaVu", "B", 13)
    pdf.cell(0, 7, name, ln=True)
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(*MITTEL)
    pdf.cell(0, 5, f"Steuernummer: {unt.steuernummer or '—'}  ·  Wirtschaftsjahr: {daten['jahr']}", ln=True)
    pdf.ln(4)

    def euro(v: Decimal) -> str:
        neg = v < 0
        s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
        return ("− " if neg else "") + s

    def zeile_row(z: int, bez: str, betrag: Decimal, fett: bool = False):
        y = pdf.get_y()
        h = 6.5
        pdf.set_fill_color(*BLAU)
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(20, y)
        pdf.cell(14, h, f"Z. {z}", border=0, fill=True, align="C")
        pdf.set_font("DejaVu", "B" if fett else "", 9)
        pdf.set_text_color(*DUNKEL)
        pdf.set_xy(36, y)
        pdf.cell(120, h, bez, border=0, align="L")
        color = (220, 38, 38) if betrag < 0 else DUNKEL
        pdf.set_text_color(*color)
        pdf.set_font("DejaVu", "B" if fett else "", 9)
        pdf.set_xy(157, y)
        pdf.cell(33, h, euro(betrag), align="R", border=0)
        pdf.ln(h + 1)

    def section_header(titel: str):
        pdf.set_fill_color(229, 231, 235)
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_text_color(*DUNKEL)
        pdf.set_x(20)
        pdf.cell(170, 6, f"  {titel}", fill=True, ln=True)
        pdf.ln(1)

    def summen_row(label: str, betrag: Decimal):
        pdf.set_fill_color(37, 99, 235)
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_text_color(255, 255, 255)
        pdf.set_x(20)
        pdf.cell(135, 7, f"  {label}", fill=True, align="L")
        pdf.cell(35, 7, euro(betrag), fill=True, align="R")
        pdf.ln(8)

    zeilen = daten["zeilen"]
    aktueller_abschnitt = None

    for z in sorted(EUR_ZEILEN_META.keys()):
        if z not in zeilen:
            continue
        bez, ab = EUR_ZEILEN_META[z]
        if ab != aktueller_abschnitt:
            if aktueller_abschnitt == "A":
                pdf.ln(1)
                summen_row("Summe Betriebseinnahmen (Zeile 23)", daten["summe_einnahmen"])
            aktueller_abschnitt = ab
            section_header(ABSCHNITT_LABEL.get(ab, ab))
        zeile_row(z, bez, zeilen[z])

    if aktueller_abschnitt == "B":
        pdf.ln(1)
        summen_row("Summe Betriebsausgaben (Zeile 75)", daten["summe_ausgaben"])

    pdf.ln(3)
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("DejaVu", "B", 10)
    pdf.set_x(20)
    g = daten["gewinn_verlust"]
    label = "Gewinn (Zeile 75)" if g >= 0 else "Verlust (Zeile 75)"
    pdf.cell(135, 8, f"  {label}", fill=True, align="L")
    pdf.cell(35, 8, euro(g), fill=True, align="R")
    pdf.ln(10)

    if daten["anlage_zugaenge"] > 0:
        pdf.set_fill_color(254, 243, 199)
        pdf.set_x(20)
        pdf.set_font("DejaVu", "", 8)
        pdf.set_text_color(120, 80, 0)
        pdf.multi_cell(170, 5,
            f"Anlagezugänge {daten['jahr']}: {euro(daten['anlage_zugaenge'])} (KFZ, EDV etc.) sind nicht enthalten. "
            "Bitte Anlage AVEUR (Abschreibungsplan) separat ausfüllen.", fill=True)
        pdf.ln(4)

    pdf.set_fill_color(254, 243, 199)
    pdf.set_x(20)
    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(120, 80, 0)
    pdf.multi_cell(170, 5,
        "Hinweis: Anzeigehilfe auf Basis von Journalbuchungen (Ist-Versteuerung / Zuflussprinzip). "
        "Bitte Werte in ELSTER oder mit dem Steuerberater übertragen.", fill=True)

    pdf.set_y(-15)
    pdf.set_font("DejaVu", "", 7)
    pdf.set_text_color(*MITTEL)
    pdf.cell(85, 5, f"Erstellt mit RechnungsFee  ·  {name[:40]}", align="L")
    pdf.cell(85, 5, f"Wirtschaftsjahr {daten['jahr']}", align="R")

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Response-Schemas
# ---------------------------------------------------------------------------

class EUERZeile(BaseModel):
    zeile: int
    bezeichnung: str
    abschnitt: str
    betrag: Decimal

class EUERErgebnis(BaseModel):
    jahr: int
    zeilen: list[EUERZeile]
    summe_einnahmen: Decimal
    summe_ausgaben: Decimal
    gewinn_verlust: Decimal
    anlage_zugaenge: Decimal
    ist_kleinunternehmer: bool


# ---------------------------------------------------------------------------
# Endpunkte
# ---------------------------------------------------------------------------

@router.get("/berechnen", response_model=EUERErgebnis)
def euer_berechnen(
    jahr: int = Query(..., ge=2020, le=2100),
    db: Session = Depends(get_db),
):
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(404, "Unternehmensdaten nicht gefunden.")

    daten = _berechne_euer(jahr, db)

    zeilen_liste = [
        EUERZeile(
            zeile=z,
            bezeichnung=EUR_ZEILEN_META[z][0] if z in EUR_ZEILEN_META else f"Zeile {z}",
            abschnitt=EUR_ZEILEN_META[z][1] if z in EUR_ZEILEN_META else "?",
            betrag=betrag,
        )
        for z, betrag in sorted(daten["zeilen"].items())
    ]

    return EUERErgebnis(
        jahr=daten["jahr"],
        zeilen=zeilen_liste,
        summe_einnahmen=daten["summe_einnahmen"],
        summe_ausgaben=daten["summe_ausgaben"],
        gewinn_verlust=daten["gewinn_verlust"],
        anlage_zugaenge=daten["anlage_zugaenge"],
        ist_kleinunternehmer=bool(unt.ist_kleinunternehmer),
    )


@router.get("/pdf")
def euer_pdf(
    jahr: int = Query(..., ge=2020, le=2100),
    db: Session = Depends(get_db),
):
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(404, "Unternehmensdaten nicht gefunden.")
    daten = _berechne_euer(jahr, db)
    pdf_bytes = _generate_pdf(daten, unt)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="EÜR_{jahr}.pdf"'},
    )
