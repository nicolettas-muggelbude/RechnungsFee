"""Anlage S – Einkünfte aus selbstständiger Arbeit (§18 EStG).

Anzeigehilfe: Zeigt die relevanten Werte für ELSTER auf Basis der EÜR
und der Unternehmensstammdaten. Keine Steuerberatung, keine Übermittlung.
"""
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.euer import _berechne_euer
from database.connection import get_db
from database.models import Anlagegut, Unternehmen

router = APIRouter(prefix="/api/anlage-s", tags=["Anlage S"])


class AnlageSKfzHinweis(BaseModel):
    bezeichnung: str
    kennzeichen: str
    privat_anteil_prozent: Decimal


class AnlageSErgebnis(BaseModel):
    jahr: int
    vorname: str
    nachname: str
    steuernummer: str
    finanzamt: str
    berufsbezeichnung: str
    gewinn_verlust: Decimal   # positiv = Gewinn, negativ = Verlust
    kfz_hinweise: list[AnlageSKfzHinweis]
    taetigkeitsart: str


@router.get("/berechnen", response_model=AnlageSErgebnis)
def anlage_s_berechnen(
    jahr: int = Query(..., ge=2020, le=2100),
    db: Session = Depends(get_db),
):
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(404, "Unternehmensdaten nicht gefunden.")

    euer = _berechne_euer(jahr, db)

    kfz_list = (
        db.query(Anlagegut)
        .filter(
            Anlagegut.typ == "kfz",
            Anlagegut.aktiv == True,  # noqa: E712
            Anlagegut.privat_anteil_prozent > 0,
            Anlagegut.verkauft_am == None,  # noqa: E711
        )
        .all()
    )

    return AnlageSErgebnis(
        jahr=jahr,
        vorname=unt.vorname or "",
        nachname=unt.nachname or "",
        steuernummer=unt.steuernummer or "",
        finanzamt=unt.finanzamt or "",
        berufsbezeichnung=unt.berufsbezeichnung or "",
        gewinn_verlust=euer["gewinn_verlust"],
        kfz_hinweise=[
            AnlageSKfzHinweis(
                bezeichnung=k.bezeichnung or "",
                kennzeichen=k.kennzeichen or "",
                privat_anteil_prozent=k.privat_anteil_prozent,
            )
            for k in kfz_list
        ],
        taetigkeitsart=unt.taetigkeitsart or "freiberuflich",
    )


# ---------------------------------------------------------------------------
# PDF-Hilfsfunktionen
# ---------------------------------------------------------------------------

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


def _euro(v: Decimal) -> str:
    neg = v < 0
    s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
    return ("− " if neg else "") + s


def _generate_anlage_s_pdf(ergebnis: AnlageSErgebnis) -> bytes:
    from fpdf import FPDF

    BLAU = (37, 99, 235)
    GRAU = (229, 231, 235)
    DUNKEL = (30, 41, 59)
    MITTEL = (100, 116, 139)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    fonts = _fonts()
    pdf.add_font("DejaVu", "",  str(fonts / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(fonts / "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(True, margin=20)

    # Header-Banner
    pdf.set_fill_color(*BLAU)
    pdf.rect(0, 0, 210, 18, "F")
    pdf.set_font("DejaVu", "B", 11)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(20, 5)
    pdf.cell(0, 8, f"Anlage S – Einkünfte aus selbstständiger Arbeit {ergebnis.jahr}", ln=True)
    pdf.set_text_color(*DUNKEL)

    name = f"{ergebnis.nachname}, {ergebnis.vorname}".strip(", ")
    pdf.set_xy(20, 24)
    pdf.set_font("DejaVu", "B", 13)
    pdf.cell(0, 7, name or "—", ln=True)
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(*MITTEL)
    pdf.cell(0, 5, f"Steuernummer: {ergebnis.steuernummer or '—'}  ·  Finanzamt: {ergebnis.finanzamt or '—'}", ln=True)
    pdf.ln(4)

    def section_header(titel: str):
        pdf.set_fill_color(*GRAU)
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_text_color(*DUNKEL)
        pdf.set_x(20)
        pdf.cell(170, 6, f"  {titel.upper()}", fill=True, ln=True)
        pdf.ln(1)

    def zeile_row(zeile: str, bez: str, wert: str):
        y = pdf.get_y()
        h = 6.5
        pdf.set_fill_color(*BLAU)
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(20, y)
        pdf.cell(16, h, f"Z. {zeile}", border=0, fill=True, align="C")
        pdf.set_font("DejaVu", "", 9)
        pdf.set_text_color(*DUNKEL)
        pdf.set_xy(38, y)
        pdf.cell(110, h, bez, border=0, align="L")
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_xy(148, y)
        pdf.cell(42, h, wert, border=0, align="L")
        pdf.ln(h + 1)

    def text_row(bez: str, wert: str):
        y = pdf.get_y()
        h = 6.5
        pdf.set_xy(38, y)
        pdf.set_font("DejaVu", "", 9)
        pdf.set_text_color(*DUNKEL)
        pdf.cell(110, h, bez, border=0, align="L")
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_xy(148, y)
        pdf.cell(42, h, wert or "—", border=0, align="L")
        pdf.ln(h + 1)

    # Persönliche Angaben
    section_header("Persönliche Angaben")
    zeile_row("1", "Name, Vorname", name or "—")
    text_row("Finanzamt", ergebnis.finanzamt or "—")
    zeile_row("3", "Steuernummer", ergebnis.steuernummer or "—")
    zeile_row("4", "Art der Tätigkeit (Berufsbezeichnung)", ergebnis.berufsbezeichnung or "—")
    pdf.ln(2)

    # Laufende Einkünfte
    gv = ergebnis.gewinn_verlust
    ist_gewinn = gv >= 0
    section_header("Laufende Einkünfte (aus EÜR)")
    kz_label = "Gewinn freiberufliche Tätigkeit  (ELSTER KZ 100)" if ist_gewinn else "Verlust freiberufliche Tätigkeit  (ELSTER KZ 100)"
    text_row(kz_label, _euro(gv))
    pdf.ln(2)

    # KFZ
    if ergebnis.kfz_hinweise:
        section_header("KFZ – Privatnutzung (Zeile 18)")
        for k in ergebnis.kfz_hinweise:
            bez = f"{k.bezeichnung}"
            if k.kennzeichen:
                bez += f" ({k.kennzeichen})"
            bez += f" – {int(k.privat_anteil_prozent)} % Privatanteil"
            zeile_row("18", bez, "→ manuell ermitteln")
        pdf.ln(2)

    # Ergebnis-Banner
    pdf.set_fill_color(*DUNKEL)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("DejaVu", "B", 10)
    pdf.set_x(20)
    label = f"Gewinn {ergebnis.jahr} (ELSTER KZ 100)" if ist_gewinn else f"Verlust {ergebnis.jahr} (ELSTER KZ 100)"
    pdf.cell(100, 8, f"  {label}", fill=True, align="L")
    pdf.set_text_color(255, 100, 100) if not ist_gewinn else pdf.set_text_color(255, 255, 255)
    pdf.cell(70, 8, _euro(gv), fill=True, align="L")
    pdf.ln(10)

    # Fußzeile
    pdf.set_font("DejaVu", "", 7)
    pdf.set_text_color(*MITTEL)
    pdf.set_x(20)
    pdf.multi_cell(
        170, 4,
        f"Anzeigehilfe – keine Steuerberatung. Grundlage: EÜR {ergebnis.jahr} (Zuflussprinzip). "
        "Zeilennummern nach Anlage S des jeweiligen Jahres – bitte vor der Übertragung in ELSTER prüfen.",
        align="L",
    )

    return pdf.output()


@router.get("/pdf")
def anlage_s_pdf(
    jahr: int = Query(..., ge=2020, le=2100),
    db: Session = Depends(get_db),
):
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(404, "Unternehmensdaten nicht gefunden.")
    ergebnis = anlage_s_berechnen(jahr=jahr, db=db)
    pdf_bytes = _generate_anlage_s_pdf(ergebnis)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="AnlageS_{jahr}.pdf"'},
    )
