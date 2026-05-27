"""
PDF-Export der Buchungskategorien mit Beschreibung / Verwendungsbeispielen.
Ohne Kontonummern und buchhalterische Referenzen – dient als Nachschlageblatt.

Fonts: DejaVu (kommt mit fpdf2 mit) für volle Unicode-Unterstützung.
"""

from datetime import date
from pathlib import Path
from fpdf import FPDF


KONTENART_LABELS = {
    "Erlös":   "Einnahmen",
    "Aufwand": "Betriebsausgaben",
    "Anlage":  "Anlagevermögen",
    "Privat":  "Privat / Nicht betrieblich",
}

KONTENART_ORDER = ["Erlös", "Aufwand", "Anlage", "Privat"]

# Farben je Kontenart (R, G, B)
KONTENART_FARBEN = {
    "Erlös":   (34,  197, 94),   # grün
    "Aufwand": (239, 68,  68),   # rot
    "Anlage":  (99,  102, 241),  # indigo
    "Privat":  (168, 85,  247),  # lila
}


def _find_dejavu_dir() -> Path:
    """Sucht das DejaVu-Font-Verzeichnis auf gängigen Systemen."""
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
    raise FileNotFoundError(
        "DejaVu-Fonts nicht gefunden. Bitte 'fonts-dejavu-core' installieren "
        "(sudo apt install fonts-dejavu-core)."
    )


class KategorienPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(18, 20, 18)
        dv_dir = _find_dejavu_dir()
        self.add_font("DejaVu",  style="",  fname=str(dv_dir / "DejaVuSans.ttf"))
        self.add_font("DejaVu",  style="B", fname=str(dv_dir / "DejaVuSans-Bold.ttf"))

    def header(self):
        self.set_font("DejaVu", "B", 9)
        self.set_text_color(150, 150, 150)
        self.cell(0, 6, "RechnungsFee – Buchungskategorien", align="L")
        self.set_font("DejaVu", "", 9)
        self.cell(0, 6, date.today().strftime("%d.%m.%Y"), align="R")
        self.ln(4)
        self.set_draw_color(220, 220, 220)
        self.set_line_width(0.3)
        self.line(18, self.get_y(), 192, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-14)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(180, 180, 180)
        self.cell(0, 6, f"Seite {self.page_no()}", align="C")

    def abschnitts_header(self, label: str, farbe: tuple):
        r, g, b = farbe
        self.set_fill_color(r, g, b)
        self.set_text_color(255, 255, 255)
        self.set_font("DejaVu", "B", 10)
        self.cell(0, 7, f"  {label}", fill=True, ln=True)
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def kategorie_zeile(self, name: str, beschreibung: str | None):
        # Name
        self.set_font("DejaVu", "B", 9)
        self.set_text_color(30, 30, 30)
        self.cell(0, 5, name, ln=True)

        # Beschreibung (mehrzeilig wenn nötig)
        if beschreibung:
            self.set_font("DejaVu", "", 8)
            self.set_text_color(80, 80, 80)
            self.multi_cell(0, 4.5, beschreibung)
        else:
            # Leere Zeile als Schreibbereich
            self.set_draw_color(200, 200, 200)
            self.set_line_width(0.2)
            y = self.get_y() + 1
            self.line(18, y, 192, y)
            self.ln(5)

        # Trennlinie
        self.set_draw_color(235, 235, 235)
        self.set_line_width(0.2)
        self.line(18, self.get_y() + 1, 192, self.get_y() + 1)
        self.ln(3)


def generate_kategorien_pdf(kategorien: list, output_path: str) -> None:
    pdf = KategorienPDF()
    pdf.add_page()

    # Titel
    pdf.set_font("DejaVu", "B", 16)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, "Buchungskategorien", ln=True)
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "Nachschlageblatt für die Zuordnung von Belegen und Buchungen", ln=True)
    pdf.ln(4)

    # Nach Kontenart gruppieren
    gruppen: dict[str, list] = {k: [] for k in KONTENART_ORDER}
    for kat in kategorien:
        art = kat.kontenart if kat.kontenart in gruppen else "Aufwand"
        gruppen[art].append(kat)

    for art in KONTENART_ORDER:
        kats = gruppen[art]
        if not kats:
            continue
        label = KONTENART_LABELS.get(art, art)
        farbe = KONTENART_FARBEN.get(art, (100, 100, 100))
        pdf.abschnitts_header(label, farbe)
        for kat in sorted(kats, key=lambda k: k.name):
            pdf.kategorie_zeile(kat.name, kat.beschreibung)
        pdf.ln(3)

    pdf.output(output_path)
