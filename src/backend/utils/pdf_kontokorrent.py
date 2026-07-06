"""
Kontokorrent-Auszug als PDF.
A4 Hochformat – Datum, Typ, Belegnr., Beschreibung, Betrag, Saldo.
"""

from decimal import Decimal
from io import BytesIO
from pathlib import Path

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
        v = Decimal(str(val))
        s = f"{abs(v):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"−{s}" if v < 0 else s
    except Exception:
        return "0,00 €"


def _fmt_datum(iso: str) -> str:
    try:
        y, m, d = iso.split("-")
        return f"{d}.{m}.{y}"
    except Exception:
        return iso


_TYP_LABEL = {
    "rechnung":  "Rechnung",
    "zahlung":   "Zahlung",
    "gutschrift": "Gutschrift",
    "storno":    "Storno",
}

# Spaltenbreiten (Summe = ca. 170 mm bei 20 mm Rand je Seite)
COL_DATUM  = 22
COL_TYP    = 22
COL_BELEG  = 28
COL_BESCHR = 58
COL_BETRAG = 28
COL_SALDO  = 28
ROW_H = 6


class KontokorrentPDF(FPDF):
    def __init__(self, unternehmen: dict, partner_name: str, von: str, bis: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.unt = unternehmen
        self.partner_name = partner_name
        self.von = von
        self.bis = bis
        font_dir = _find_dejavu_dir()
        self.add_font("DejaVu", "",  str(font_dir / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(font_dir / "DejaVuSans-Bold.ttf"))
        self.set_auto_page_break(auto=True, margin=18)
        self.add_page()

    def header(self):
        self.set_font("DejaVu", "B", 11)
        self.cell(0, 7, self.unt.get("firmenname", ""), ln=True)
        self.set_font("DejaVu", "", 9)
        self.cell(0, 5, f"Kontokorrent-Auszug: {self.partner_name}", ln=True)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 4, f"Zeitraum: {_fmt_datum(self.von)} – {_fmt_datum(self.bis)}", ln=True)
        self.set_text_color(0, 0, 0)
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


def _zeile(pdf: FPDF, datum: str, typ: str, belegnr: str, beschreibung: str,
           betrag: str, saldo: str, bold: bool = False, fill: bool = False,
           fill_color: tuple = (240, 240, 240)) -> None:
    style = "B" if bold else ""
    pdf.set_font("DejaVu", style, 8)
    if fill:
        pdf.set_fill_color(*fill_color)
    pdf.cell(COL_DATUM,  ROW_H, datum,        border=0, fill=fill)
    pdf.cell(COL_TYP,    ROW_H, typ,          border=0, fill=fill)
    pdf.cell(COL_BELEG,  ROW_H, belegnr,      border=0, fill=fill)
    pdf.cell(COL_BESCHR, ROW_H, beschreibung, border=0, fill=fill)
    pdf.cell(COL_BETRAG, ROW_H, betrag,       border=0, align="R", fill=fill)
    pdf.cell(COL_SALDO,  ROW_H, saldo,        border=0, align="R", fill=fill, ln=True)


def erstelle_kontokorrent_pdf(
    unternehmen: dict,
    partner_name: str,
    von: str,
    bis: str,
    bewegungen: list[dict],
) -> bytes:
    pdf = KontokorrentPDF(unternehmen, partner_name, von, bis)

    # Kopfzeile
    _zeile(pdf, "Datum", "Typ", "Beleg-Nr.", "Beschreibung", "Betrag", "Saldo",
           bold=True, fill=True, fill_color=(220, 220, 220))
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())

    for i, b in enumerate(bewegungen):
        betrag = Decimal(str(b.get("betrag", 0)))
        saldo  = Decimal(str(b.get("saldo",  0)))
        betrag_str = ("−" if betrag < 0 else "+") + _fmt_euro(abs(betrag))
        saldo_str  = _fmt_euro(saldo)

        fill_col = (248, 248, 248) if i % 2 == 0 else (255, 255, 255)

        _zeile(
            pdf,
            datum=_fmt_datum(b.get("datum", "")),
            typ=_TYP_LABEL.get(b.get("typ", ""), b.get("typ", "")),
            belegnr=(b.get("belegnr", "") or "")[:14],
            beschreibung=(b.get("beschreibung", "") or "")[:34],
            betrag=betrag_str,
            saldo=saldo_str,
            fill=True,
            fill_color=fill_col,
        )

    # Abschlusszeile: offener Saldo
    if bewegungen:
        letzter_saldo = Decimal(str(bewegungen[-1].get("saldo", 0)))
        pdf.set_draw_color(200, 200, 200)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        _zeile(pdf, "", "", "", "Offener Saldo", "", _fmt_euro(letzter_saldo),
               bold=True, fill=True, fill_color=(230, 235, 255))
    else:
        pdf.set_font("DejaVu", "", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 10, "Keine Bewegungen im gewählten Zeitraum.", ln=True)
        pdf.set_text_color(0, 0, 0)

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()
