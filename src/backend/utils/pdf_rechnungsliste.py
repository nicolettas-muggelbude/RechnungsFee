"""PDF-Export für die (gefilterte) Rechnungsliste – z.B. Offene-Posten-Liste (Issue #258)."""

from decimal import Decimal
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
        return f"{Decimal(str(val)):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00 €"


def _fmt_datum(d) -> str:
    if not d:
        return ""
    return d.strftime("%d.%m.%Y")


COL = {"nr": 26, "datum": 20, "faellig": 20, "partner_nr": 24, "partner": 54, "status": 22, "betrag": 24, "offen": 24}
ROW_H = 6


class RechnungslistePDF(FPDF):
    def __init__(self, unternehmen: dict, filter_zeile: str):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.unt = unternehmen
        self.filter_zeile = filter_zeile
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
        self.cell(0, 6, "Rechnungsliste", ln=True)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 4, f"Filter: {self.filter_zeile}", ln=True)
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


def _row(pdf: FPDF, nr, datum, faellig, partner_nr, partner, status, betrag, offen,
         bold: bool = False, fill: bool = False, fill_color: tuple = (240, 240, 240)):
    style = "B" if bold else ""
    pdf.set_font("DejaVu", style, 8)
    if fill:
        pdf.set_fill_color(*fill_color)
    pdf.cell(COL["nr"],        ROW_H, nr,        border=0, fill=fill)
    pdf.cell(COL["datum"],     ROW_H, datum,     border=0, fill=fill)
    pdf.cell(COL["faellig"],   ROW_H, faellig,   border=0, fill=fill)
    pdf.cell(COL["partner_nr"], ROW_H, partner_nr, border=0, fill=fill)
    pdf.cell(COL["partner"],   ROW_H, partner,   border=0, fill=fill)
    pdf.cell(COL["status"],    ROW_H, status,    border=0, fill=fill)
    pdf.cell(COL["betrag"],    ROW_H, betrag,    border=0, align="R", fill=fill)
    pdf.cell(COL["offen"],     ROW_H, offen,     border=0, align="R", fill=fill, ln=True)


def erstelle_rechnungsliste_pdf(unternehmen: dict, zeilen: list, filter_zeile: str) -> bytes:
    pdf = RechnungslistePDF(unternehmen, filter_zeile)

    _row(pdf, "Rechnungsnr.", "Datum", "Fällig", "Deb./Kred.-Nr.", "Partner", "Status", "Betrag", "Offen",
         bold=True, fill=True, fill_color=(220, 220, 220))
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())

    summe_betrag = Decimal("0")
    summe_offen = Decimal("0")

    for i, z in enumerate(zeilen):
        r = z["resp"]
        partner = r.kunde_name or r.lieferant_name or r.partner_freitext or "—"
        betrag = Decimal(str(r.brutto_gesamt))
        offen = z["offen_betrag"]
        summe_betrag += betrag
        summe_offen += offen
        fill = i % 2 == 0
        _row(
            pdf,
            (r.rechnungsnummer or "—")[:14],
            _fmt_datum(r.datum),
            _fmt_datum(r.faellig_am),
            z["partner_nr"][:12],
            partner[:32],
            z["status_anzeige"],
            _fmt_euro(betrag),
            _fmt_euro(offen) if offen else "",
            fill=fill,
            fill_color=(248, 248, 248),
        )

    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.set_font("DejaVu", "B", 8)
    pdf.set_fill_color(235, 245, 255)
    vorspalten_breite = COL["nr"] + COL["datum"] + COL["faellig"] + COL["partner_nr"] + COL["partner"] + COL["status"]
    pdf.cell(vorspalten_breite, ROW_H, "  Summe", border=0, fill=True)
    pdf.cell(COL["betrag"], ROW_H, _fmt_euro(summe_betrag), border=0, align="R", fill=True)
    pdf.cell(COL["offen"], ROW_H, _fmt_euro(summe_offen), border=0, align="R", fill=True, ln=True)

    return bytes(pdf.output())
