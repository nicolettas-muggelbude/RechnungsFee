"""
PDF-Export für das Journal (mit Filter-Unterstützung).
Erzeugt ein A4-Querformat-Dokument aller gefilterten Buchungen.
"""

from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any

import base64

from fpdf import FPDF


def _find_dejavu_dir() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        p = Path(sys._MEIPASS) / "fonts"  # type: ignore[attr-defined]
        if (p / "DejaVuSans.ttf").exists():
            return p
    local = Path(__file__).parent.parent / "fonts"
    if (local / "DejaVuSans.ttf").exists():
        return local
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/dejavu"),
        Path("/usr/share/fonts/dejavu-sans-fonts"),
        Path("/usr/local/share/fonts/dejavu"),
        Path.home() / ".fonts/dejavu",
    ]
    for p in candidates:
        if (p / "DejaVuSans.ttf").exists():
            return p
    raise FileNotFoundError("DejaVu-Fonts nicht gefunden.")


def _fmt_euro(val) -> str:
    try:
        return f"{Decimal(str(val)):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00 €"


def _fmt_datum(iso: str) -> str:
    try:
        y, m, d = iso.split("-")
        return f"{d}.{m}.{y}"
    except Exception:
        return iso


COL = {
    "datum":        22,
    "belegnr":      28,
    "beschreibung": 68,
    "kategorie":    38,
    "zahlung":      18,
    "netto":        26,
    "ust_satz":     12,
    "ust":          22,
    "brutto":       26,
}
ROW_H = 6


class JournalPDF(FPDF):
    def __init__(self, unternehmen: dict, titel: str):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.unt = unternehmen
        self.titel = titel
        font_dir = _find_dejavu_dir()
        self.add_font("DejaVu", "", str(font_dir / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(font_dir / "DejaVuSans-Bold.ttf"))
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()

    def header(self):
        self.set_font("DejaVu", "B", 11)
        self.cell(0, 7, self.unt.get("firmenname", ""), ln=True)
        self.set_font("DejaVu", "", 9)
        self.cell(0, 5, self.titel, ln=True)
        self.ln(2)
        self.set_draw_color(180, 180, 180)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, f"Seite {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)


def _row(pdf: FPDF, cols: dict, bold: bool = False, fill: bool = False,
         fill_color: tuple = (240, 240, 240)):
    style = "B" if bold else ""
    pdf.set_font("DejaVu", style, 8)
    if fill:
        pdf.set_fill_color(*fill_color)
    pdf.cell(COL["datum"],        ROW_H, cols.get("datum", ""),        border=0, fill=fill)
    pdf.cell(COL["belegnr"],      ROW_H, cols.get("belegnr", ""),      border=0, fill=fill)
    pdf.cell(COL["beschreibung"], ROW_H, cols.get("beschreibung", ""), border=0, fill=fill)
    pdf.cell(COL["kategorie"],    ROW_H, cols.get("kategorie", ""),    border=0, fill=fill)
    pdf.cell(COL["zahlung"],      ROW_H, cols.get("zahlung", ""),      border=0, fill=fill)
    pdf.cell(COL["netto"],        ROW_H, cols.get("netto", ""),        border=0, align="R", fill=fill)
    pdf.cell(COL["ust_satz"],     ROW_H, cols.get("ust_satz", ""),     border=0, align="R", fill=fill)
    pdf.cell(COL["ust"],          ROW_H, cols.get("ust", ""),          border=0, align="R", fill=fill)
    pdf.cell(COL["brutto"],       ROW_H, cols.get("brutto", ""),       border=0, align="R", fill=fill, ln=True)


def erstelle_journal_pdf(
    unternehmen: dict,
    eintraege: list[dict],
    titel: str,
) -> bytes:
    pdf = JournalPDF(unternehmen, titel)

    # Kopfzeile
    _row(pdf, {
        "datum": "Datum", "belegnr": "Beleg-Nr.", "beschreibung": "Beschreibung",
        "kategorie": "Kategorie", "zahlung": "Zahlung",
        "netto": "Netto", "ust_satz": "USt %", "ust": "USt", "brutto": "Brutto",
    }, bold=True, fill=True, fill_color=(220, 220, 220))
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())

    sum_ein = Decimal("0")
    sum_aus = Decimal("0")

    for i, e in enumerate(eintraege):
        art = e.get("art", "")
        brutto = Decimal(str(e.get("brutto_betrag", 0)))
        netto  = Decimal(str(e.get("netto_betrag",  0)))
        ust    = Decimal(str(e.get("ust_betrag",    0)))
        ust_satz = e.get("ust_satz", "0")
        try:
            ust_satz_str = f'{Decimal(str(ust_satz)):.0f} %'
        except Exception:
            ust_satz_str = ""

        if art == "Einnahme":
            sum_ein += brutto
            brutto_str = _fmt_euro(brutto)
            netto_str  = _fmt_euro(netto)
            ust_str    = _fmt_euro(ust) if ust else ""
        else:
            sum_aus += brutto
            brutto_str = f"−{_fmt_euro(brutto)}"
            netto_str  = f"−{_fmt_euro(netto)}"
            ust_str    = f"−{_fmt_euro(ust)}" if ust else ""

        is_storno = (e.get("beschreibung", "") or "").startswith("STORNO ")
        fill = i % 2 == 0
        fill_col = (248, 248, 248) if not is_storno else (245, 242, 242)

        _row(pdf, {
            "datum":        _fmt_datum(e.get("datum", "")),
            "belegnr":      (e.get("belegnr", "") or "")[:14],
            "beschreibung": (e.get("beschreibung", "") or "")[:40],
            "kategorie":    (e.get("kategorie_name", "") or "")[:22],
            "zahlung":      (e.get("zahlungsart", "") or "")[:10],
            "netto":        netto_str,
            "ust_satz":     ust_satz_str if ust else "",
            "ust":          ust_str,
            "brutto":       brutto_str,
        }, fill=fill, fill_color=fill_col)

    # Summenzeile – drei gleichbreite Zellen über die volle Tabellenbreite
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    saldo = sum_ein - sum_aus
    saldo_str = _fmt_euro(saldo) if saldo >= 0 else f"−{_fmt_euro(-saldo)}"
    total_w = sum(COL.values())
    third = total_w / 3
    pdf.set_font("DejaVu", "B", 8)
    pdf.set_fill_color(235, 245, 255)
    pdf.cell(third, ROW_H, f"  Einnahmen: {_fmt_euro(sum_ein)}", border=0, fill=True)
    pdf.cell(third, ROW_H, f"Ausgaben: {_fmt_euro(sum_aus)}", border=0, fill=True)
    pdf.cell(third, ROW_H, f"Saldo: {saldo_str}", border=0, align="R", fill=True, ln=True)

    return bytes(pdf.output())
