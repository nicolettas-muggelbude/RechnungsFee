"""
Deckblatt für das Inkasso-Paket (Abschnitt E Mahnwesen).
Zusammenfassung: offene Rechnungen, Mahnhistorie, Inhaltsverzeichnis des ZIP-Archivs.
Gleiches Design wie pdf_kontokorrent.py (DejaVu-Fonts, gleiches Farbschema).
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


def _fmt_datum(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        y, m, d = str(iso)[:10].split("-")
        return f"{d}.{m}.{y}"
    except Exception:
        return str(iso)


class InkassoDeckblattPDF(FPDF):
    def __init__(self, unternehmen: dict, kunde_name: str, erstellt_am: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.unt = unternehmen
        self.kunde_name = kunde_name
        self.erstellt_am = erstellt_am
        font_dir = _find_dejavu_dir()
        self.add_font("DejaVu", "",  str(font_dir / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(font_dir / "DejaVuSans-Bold.ttf"))
        self.set_auto_page_break(auto=True, margin=18)
        self.add_page()

    def header(self):
        self.set_font("DejaVu", "B", 13)
        self.cell(0, 8, "Inkasso-Unterlagen", ln=True)
        self.set_font("DejaVu", "", 9)
        self.set_text_color(80, 80, 80)
        self.cell(0, 5, self.unt.get("firmenname", ""), ln=True)
        self.cell(0, 5, f"Schuldner: {self.kunde_name}", ln=True)
        self.cell(0, 5, f"Erstellt am: {self.erstellt_am}", ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)
        self.set_draw_color(180, 180, 180)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, f"Seite {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)

    def abschnitt_titel(self, text: str) -> None:
        self.set_font("DejaVu", "B", 10)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 7, f"  {text}", ln=True, fill=True)
        self.ln(1)


# Spaltenbreiten Rechnungen (Summe = 175 mm)
RE_COL_NR      = 35
RE_COL_DATUM   = 25
RE_COL_FAELLIG = 25
RE_COL_BRUTTO  = 30
RE_COL_OFFEN   = 30
RE_COL_TAGE    = 30

# Spaltenbreiten Mahnungen (Summe = 175 mm)
MH_COL_NR      = 35
MH_COL_BEZ     = 45
MH_COL_STUFE   = 15
MH_COL_VERSAND = 30
MH_COL_FORDER  = 50


def erstelle_inkasso_deckblatt_pdf(
    unternehmen: dict,
    kunde_name: str,
    erstellt_am: str,
    offene_rechnungen: list[dict],
    mahnungen: list[dict],
    dateiliste: list[str],
) -> bytes:
    """
    offene_rechnungen: [{rechnungsnummer, datum, faellig_am, brutto_gesamt, offener_betrag, tage_ueberfaellig}]
    mahnungen: [{mahnnummer, bezeichnung, stufe, versendet_am, gesamtforderung}]
    dateiliste: Dateinamen im ZIP (für das Inhaltsverzeichnis), in Aufnahme-Reihenfolge.
    """
    pdf = InkassoDeckblattPDF(unternehmen, kunde_name, erstellt_am)

    # --- Offene Rechnungen --------------------------------------------------
    pdf.abschnitt_titel("Offene Rechnungen")
    pdf.set_font("DejaVu", "B", 8)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(RE_COL_NR,      6, "Rechnungsnr.", fill=True)
    pdf.cell(RE_COL_DATUM,   6, "Datum",        fill=True)
    pdf.cell(RE_COL_FAELLIG, 6, "Fällig bis",   fill=True)
    pdf.cell(RE_COL_BRUTTO,  6, "Brutto",       fill=True, align="R")
    pdf.cell(RE_COL_OFFEN,   6, "Offen",        fill=True, align="R")
    pdf.cell(RE_COL_TAGE,    6, "Tage überf.",  fill=True, align="R", ln=True)

    gesamt_offen = Decimal("0")
    for i, r in enumerate(offene_rechnungen):
        offen = Decimal(str(r.get("offener_betrag", 0)))
        gesamt_offen += offen
        fill = (248, 248, 248) if i % 2 == 0 else (255, 255, 255)
        pdf.set_font("DejaVu", "", 8)
        pdf.set_fill_color(*fill)
        pdf.cell(RE_COL_NR,      6, str(r.get("rechnungsnummer") or "—"), fill=True)
        pdf.cell(RE_COL_DATUM,   6, _fmt_datum(r.get("datum")), fill=True)
        pdf.cell(RE_COL_FAELLIG, 6, _fmt_datum(r.get("faellig_am")), fill=True)
        pdf.cell(RE_COL_BRUTTO,  6, _fmt_euro(r.get("brutto_gesamt", 0)), fill=True, align="R")
        pdf.cell(RE_COL_OFFEN,   6, _fmt_euro(offen), fill=True, align="R")
        pdf.cell(RE_COL_TAGE,    6, str(r.get("tage_ueberfaellig", "—")), fill=True, align="R", ln=True)

    pdf.set_draw_color(180, 180, 180)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.set_font("DejaVu", "B", 9)
    pdf.cell(RE_COL_NR + RE_COL_DATUM + RE_COL_FAELLIG + RE_COL_BRUTTO, 7, "Summe offene Hauptforderung", align="R")
    pdf.cell(RE_COL_OFFEN, 7, _fmt_euro(gesamt_offen), align="R")
    pdf.cell(RE_COL_TAGE, 7, "", ln=True)
    pdf.ln(4)

    # --- Mahnhistorie --------------------------------------------------------
    pdf.abschnitt_titel("Mahnhistorie")
    if mahnungen:
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(MH_COL_NR,      6, "Mahnnr.",      fill=True)
        pdf.cell(MH_COL_BEZ,     6, "Bezeichnung",  fill=True)
        pdf.cell(MH_COL_STUFE,   6, "Stufe",        fill=True, align="R")
        pdf.cell(MH_COL_VERSAND, 6, "Versendet am", fill=True)
        pdf.cell(MH_COL_FORDER,  6, "Gesamtforderung", fill=True, align="R", ln=True)

        for i, m in enumerate(mahnungen):
            fill = (248, 248, 248) if i % 2 == 0 else (255, 255, 255)
            pdf.set_font("DejaVu", "", 8)
            pdf.set_fill_color(*fill)
            pdf.cell(MH_COL_NR,      6, str(m.get("mahnnummer") or "—"), fill=True)
            pdf.cell(MH_COL_BEZ,     6, str(m.get("bezeichnung") or "")[:26], fill=True)
            pdf.cell(MH_COL_STUFE,   6, str(m.get("stufe", "")), fill=True, align="R")
            pdf.cell(MH_COL_VERSAND, 6, _fmt_datum(m.get("versendet_am")), fill=True)
            pdf.cell(MH_COL_FORDER,  6, _fmt_euro(m.get("gesamtforderung", 0)), fill=True, align="R", ln=True)
        pdf.ln(2)
        pdf.set_font("DejaVu", "", 7.5)
        pdf.set_text_color(110, 110, 110)
        pdf.multi_cell(0, 4, "Hinweis: Mahngebühren und Verzugszinsen sind bereits geleisteten Zahlungen "
                              "gegenzurechnen - die tagesaktuelle Zusammensetzung der Gesamtforderung je "
                              "Mahnung ist dem jeweiligen Mahnungs-PDF zu entnehmen.")
        pdf.set_text_color(0, 0, 0)
    else:
        pdf.set_font("DejaVu", "", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 8, "Keine versendeten Mahnungen vorhanden.", ln=True)
        pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # --- Inhaltsverzeichnis ----------------------------------------------------
    pdf.abschnitt_titel("Enthaltene Dokumente")
    pdf.set_font("DejaVu", "", 8)
    for name in dateiliste:
        pdf.cell(6, 5.5, "-")
        pdf.cell(0, 5.5, name, ln=True)

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()
