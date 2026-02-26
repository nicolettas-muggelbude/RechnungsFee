"""
PDF-Export für Rechnungen (Eingang + Ausgang).
Erzeugt ein druckbares A4-Dokument mit Firmenkopf, Positionen und Summendarstellung.

Fonts: DejaVu (kommt mit fpdf2 mit) für volle Unicode-Unterstützung
       (Umlaute, Euro-Zeichen, Sonderzeichen).
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from fpdf import FPDF


def _find_dejavu_dir() -> Path:
    """Sucht das DejaVu-Font-Verzeichnis auf gängigen Systemen."""
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


# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

GRAU_HELL = (245, 246, 248)
GRAU_RAND = (220, 220, 224)
BLAU      = (37, 99, 235)
ROT       = (220, 38, 38)
TEXT_GRAU = (90, 90, 100)


def _fmt_euro(val: Any) -> str:
    try:
        n = float(str(val))
    except (ValueError, TypeError):
        n = 0.0
    formatted = f"{abs(n):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted} \u20ac"


def _iso_zu_de(iso: str) -> str:
    try:
        y, m, d = str(iso)[:10].split("-")
        return f"{d}.{m}.{y}"
    except Exception:
        return str(iso)


# ---------------------------------------------------------------------------
# PDF-Klasse
# ---------------------------------------------------------------------------

class RechnungPDF(FPDF):

    def __init__(self, unternehmen: dict, rechnung, ist_kopie: bool = False):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=20)
        dv_dir = _find_dejavu_dir()
        self.add_font("DejaVu",     style="",  fname=str(dv_dir / "DejaVuSans.ttf"))
        self.add_font("DejaVu",     style="B", fname=str(dv_dir / "DejaVuSans-Bold.ttf"))
        self.add_font("DejaVuMono", style="",  fname=str(dv_dir / "DejaVuSansMono.ttf"))
        self._unt       = unternehmen
        self._r         = rechnung
        self._ist_kopie = ist_kopie
        self._druckdatum = datetime.now().strftime("%d.%m.%Y")

    # --- Seitenkopf ---------------------------------------------------------

    def header(self):
        unt = self._unt
        r   = self._r

        # KOPIE-Banner
        if self._ist_kopie:
            self.set_fill_color(*ROT)
            self.set_text_color(255, 255, 255)
            self.set_font("DejaVu", "B", 16)
            self.cell(0, 10, "K O P I E", fill=True, align="C", new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

        # Firmenname (links)
        absender = " ".join(filter(None, [
            unt.get("firmenname"), unt.get("vorname"), unt.get("nachname")
        ])) or "RechnungsFee"
        adresse = (
            f"{unt.get('strasse', '')} {unt.get('hausnummer', '')}, "
            f"{unt.get('plz', '')} {unt.get('ort', '')}"
        ).strip(", ")
        steuernr = unt.get("steuernummer") or ""
        ust_id   = unt.get("ust_idnr") or ""

        start_y = self.get_y()

        # Linke Spalte: Absender
        self.set_x(10)
        self.set_font("DejaVu", "B", 13)
        self.set_text_color(20, 20, 30)
        self.cell(110, 7, absender)

        # Rechte Spalte: Rechnungsmetadaten
        meta_x = 130
        self.set_xy(meta_x, start_y)
        rows = []
        if r.typ == "ausgang":
            rows.append(("Rechnungsnummer", r.rechnungsnummer or "—"))
        else:
            rows.append(("Eingangs-RE-Nr.", r.rechnungsnummer or "—"))
        rows.append(("Datum", _iso_zu_de(str(r.datum))))
        if r.leistungsdatum and str(r.leistungsdatum) != str(r.datum):
            rows.append(("Leistungsdatum", _iso_zu_de(str(r.leistungsdatum))))
        if r.faellig_am:
            rows.append(("Fällig am", _iso_zu_de(str(r.faellig_am))))

        for lbl, val in rows:
            self.set_x(meta_x)
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
            self.cell(35, 5, lbl)
            self.set_font("DejaVu", "B", 8)
            self.set_text_color(20, 20, 30)
            self.cell(0, 5, val, new_x="LMARGIN", new_y="NEXT")

        # Absender-Details (linke Spalte, Fortsetzung)
        self.set_xy(10, start_y + 8)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(*TEXT_GRAU)
        if adresse.strip(", "):
            self.cell(110, 5, adresse, new_x="LMARGIN", new_y="NEXT")
        if steuernr:
            self.set_x(10)
            self.cell(110, 5, f"StNr: {steuernr}", new_x="LMARGIN", new_y="NEXT")
        if ust_id:
            self.set_x(10)
            self.cell(110, 5, f"USt-IdNr: {ust_id}", new_x="LMARGIN", new_y="NEXT")

        # Trennlinie
        self.ln(3)
        self.set_y(max(self.get_y(), start_y + 25))
        self.set_draw_color(*GRAU_RAND)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)

    # --- Fußzeile -----------------------------------------------------------

    def footer(self):
        self.set_y(-12)
        self.set_font("DejaVu", "", 7)
        self.set_text_color(160, 160, 170)
        self.set_draw_color(*GRAU_RAND)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(1)
        self.cell(
            0, 4,
            f"Seite {self.page_no()} \u00b7 {self._druckdatum} \u00b7 Erstellt mit RechnungsFee",
            align="C",
        )
        self.set_text_color(0, 0, 0)

    # --- Inhalt -------------------------------------------------------------

    def render(self) -> bytes:
        r   = self._r
        unt = self._unt

        self.add_page()

        # Empfänger-Zeile
        if r.typ == "ausgang":
            partner = None
            if r.kunde:
                parts = [r.kunde.firmenname or "", r.kunde.vorname or "", r.kunde.nachname or ""]
                partner = " ".join(p for p in parts if p) or None
            partner = partner or r.partner_freitext or "—"
            empf_label = "Rechnungsempfänger"
        else:
            partner = None
            if r.lieferant:
                parts = [r.lieferant.firmenname or "", r.lieferant.vorname or "", r.lieferant.nachname or ""]
                partner = " ".join(p for p in parts if p) or None
            partner = partner or r.partner_freitext or "—"
            empf_label = "Lieferant"

        self.set_font("DejaVu", "", 8.5)
        self.set_text_color(*TEXT_GRAU)
        self.cell(35, 5.5, f"{empf_label}:")
        self.set_font("DejaVu", "B", 8.5)
        self.set_text_color(20, 20, 30)
        self.cell(0, 5.5, partner, new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

        # Rechnungstitel
        titel = "Rechnung" if r.typ == "ausgang" else "Eingangsrechnung"
        self.set_font("DejaVu", "B", 15)
        self.set_text_color(20, 20, 30)
        self.cell(0, 8, titel, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

        # Positionstabelle
        col_w = [82, 16, 16, 28, 16, 28]  # Beschr, Menge, Einh, Netto, USt%, Brutto
        headers = ["Beschreibung", "Menge", "Einheit", "Netto", "USt %", "Brutto"]
        aligns  = ["L",            "R",     "L",       "R",     "R",     "R"]

        self.set_font("DejaVu", "B", 8)
        self.set_fill_color(*GRAU_HELL)
        self.set_draw_color(*GRAU_RAND)
        for i, h in enumerate(headers):
            self.cell(col_w[i], 6, h, border="B", fill=True, align=aligns[i])
        self.ln()

        self.set_font("DejaVu", "", 8.5)
        self.set_text_color(30, 30, 40)
        for pos in r.positionen:
            menge = float(str(pos.menge))
            menge_str = str(int(menge)) if menge == int(menge) else f"{menge:.3f}".rstrip("0")
            self.cell(col_w[0], 6, pos.beschreibung[:60])
            self.cell(col_w[1], 6, menge_str, align="R")
            self.cell(col_w[2], 6, pos.einheit[:10])
            self.cell(col_w[3], 6, _fmt_euro(pos.netto), align="R")
            self.cell(col_w[4], 6, f"{int(pos.ust_satz)} %", align="R")
            self.cell(col_w[5], 6, _fmt_euro(pos.brutto), align="R", new_x="LMARGIN", new_y="NEXT")

        # Summenblock (rechtsbündig)
        self.ln(3)
        sum_x  = 10 + col_w[0] + col_w[1] + col_w[2]
        lbl_w  = col_w[3] + col_w[4]
        val_w  = col_w[5]

        def _sum_row(lbl: str, wert: str, bold: bool = False):
            self.set_x(sum_x)
            self.set_font("DejaVu", "B" if bold else "", 8.5)
            self.set_text_color(*TEXT_GRAU)
            self.cell(lbl_w, 5.5, lbl, align="R")
            self.set_text_color(20, 20, 30)
            self.cell(val_w, 5.5, wert, align="R", new_x="LMARGIN", new_y="NEXT")

        _sum_row("Netto gesamt", _fmt_euro(r.netto_gesamt))
        _sum_row("USt gesamt",   _fmt_euro(r.ust_gesamt))
        # Trennlinie
        self.set_draw_color(*GRAU_RAND)
        self.line(sum_x, self.get_y(), 200, self.get_y())
        _sum_row("Brutto gesamt", _fmt_euro(r.brutto_gesamt), bold=True)

        # §19-Hinweis
        if unt.get("ist_kleinunternehmer"):
            self.ln(4)
            self.set_font("DejaVu", "", 7.5)
            self.set_text_color(*TEXT_GRAU)
            self.cell(0, 5, "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.")
            self.ln()

        # Notizen
        if r.notizen:
            self.ln(4)
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
            self.multi_cell(0, 5, f"Notizen: {r.notizen}")

        self.set_text_color(0, 0, 0)
        return bytes(self.output())


# ---------------------------------------------------------------------------
# Öffentliche Funktion
# ---------------------------------------------------------------------------

def generate_rechnung_pdf(rechnung, unternehmen: dict, ist_kopie: bool = False) -> bytes:
    """
    Erzeugt ein PDF für die übergebene Rechnung und gibt es als Bytes zurück.

    :param rechnung:    SQLAlchemy-Rechnung-Objekt (mit .positionen, .kunde, .lieferant)
    :param unternehmen: dict mit Firmendaten
    :param ist_kopie:   True → rotes KOPIE-Banner
    """
    pdf = RechnungPDF(unternehmen, rechnung, ist_kopie=ist_kopie)
    return pdf.render()
