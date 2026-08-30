"""PDF-Export für die Inventurliste (Bestandsliste zum Stichtag, §240 HGB)."""

from datetime import date
from decimal import Decimal

from fpdf import FPDF


def _find_dejavu_dir():
    from pathlib import Path
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


def _fmt_menge(val) -> str:
    d = Decimal(str(val)).normalize()
    return f"{d:f}".replace(".", ",")


COL = {"artikelnr": 28, "bezeichnung": 62, "bestand": 30, "ek": 30, "wert": 30}
ROW_H = 6.5


class InventurlistePDF(FPDF):
    def __init__(self, unternehmen: dict, titel: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.unt = unternehmen
        self.titel = titel
        font_dir = _find_dejavu_dir()
        self.add_font("DejaVu", "", str(font_dir / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(font_dir / "DejaVuSans-Bold.ttf"))
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()

    def header(self):
        name = self.unt.get("firmenname") or " ".join(
            t for t in [self.unt.get("vorname", ""), self.unt.get("nachname", "")] if t
        )
        adresse = f"{self.unt.get('strasse', '')} {self.unt.get('hausnummer', '')}".strip()
        plz_ort = f"{self.unt.get('plz', '')} {self.unt.get('ort', '')}".strip()
        steuernummer = self.unt.get("steuernummer") or "—"

        self.set_font("DejaVu", "B", 12)
        self.cell(0, 6.5, name, ln=True)
        self.set_font("DejaVu", "", 9)
        self.set_text_color(100, 116, 139)
        if adresse or plz_ort:
            self.cell(0, 5, " · ".join(t for t in [adresse, plz_ort] if t), ln=True)
        self.cell(0, 5, f"Steuernummer: {steuernummer}", ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(1)
        self.set_font("DejaVu", "B", 10)
        self.cell(0, 6, self.titel, ln=True)
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


def _row(pdf: FPDF, artikelnr: str, bezeichnung: str, bestand: str, ek: str, wert: str,
         bold: bool = False, fill: bool = False, fill_color: tuple = (240, 240, 240)):
    style = "B" if bold else ""
    pdf.set_font("DejaVu", style, 9)
    if fill:
        pdf.set_fill_color(*fill_color)
    pdf.cell(COL["artikelnr"],    ROW_H, artikelnr,   border=0, fill=fill)
    pdf.cell(COL["bezeichnung"],  ROW_H, bezeichnung, border=0, fill=fill)
    pdf.cell(COL["bestand"],      ROW_H, bestand,     border=0, align="R", fill=fill)
    pdf.cell(COL["ek"],           ROW_H, ek,          border=0, align="R", fill=fill)
    pdf.cell(COL["wert"],         ROW_H, wert,        border=0, align="R", fill=fill, ln=True)


def erstelle_inventurliste_pdf(unternehmen: dict, zeilen: list[dict], stichtag: date) -> bytes:
    pdf = InventurlistePDF(unternehmen, f"Inventurliste zum {stichtag.strftime('%d.%m.%Y')}")

    _row(pdf, "Artikelnr.", "Bezeichnung", "Bestand", "EK (netto)", "Wert (netto)",
         bold=True, fill=True, fill_color=(220, 220, 220))
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())

    gesamt = Decimal("0")
    for i, z in enumerate(zeilen):
        wert = Decimal(z["wert"]) if z["wert"] is not None else None
        if wert is not None:
            gesamt += wert
        fill = i % 2 == 0
        _row(
            pdf,
            z["artikelnummer"],
            (z["bezeichnung"] or "")[:40],
            f"{_fmt_menge(z['bestand'])} {z['einheit']}",
            _fmt_euro(z["ek_netto"]) if z["ek_netto"] is not None else "–",
            _fmt_euro(wert) if wert is not None else "–",
            fill=fill,
            fill_color=(248, 248, 248),
        )

    if not zeilen:
        pdf.set_font("DejaVu", "", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 8, "Keine Artikel mit aktiver Lagerführung.", ln=True)
        pdf.set_text_color(0, 0, 0)

    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.set_font("DejaVu", "B", 9)
    pdf.set_fill_color(235, 245, 255)
    pdf.cell(COL["artikelnr"] + COL["bezeichnung"] + COL["bestand"] + COL["ek"], ROW_H, "  Gesamtwert", border=0, fill=True)
    pdf.cell(COL["wert"], ROW_H, _fmt_euro(gesamt), border=0, align="R", fill=True, ln=True)

    return bytes(pdf.output())
