"""
PDF-Export für Rechnungen (Eingang + Ausgang).
Layout nach DIN 5008 / §14 UStG:
  - Briefkopf mit Logo + Absender oben
  - Empfänger-Adressblock (vollständige Anschrift, Pflicht §14 IV Nr. 1)
  - Rechnungsmetadaten rechts
  - Positionstabelle
  - Summen + Bankdaten + Pflichthinweise

Fonts: DejaVu (kommt mit fpdf2) für volle Unicode-Unterstützung.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from fpdf import FPDF


def _find_dejavu_dir() -> Path:
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

GRAU_HELL  = (245, 246, 248)
GRAU_RAND  = (210, 213, 220)
BLAU       = (37, 99, 235)
TEXT_GRAU  = (100, 105, 115)
TEXT_DUNKEL = (20, 24, 35)

L_MARGIN = 15   # linker Rand mm
R_MARGIN = 15   # rechter Rand mm
PAGE_W   = 210  # A4-Breite mm
NUTZ_W   = PAGE_W - L_MARGIN - R_MARGIN  # nutzbarer Bereich: 180mm


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


def _adresszeilen(obj) -> list[str]:
    """Vollständige Adresszeilen aus Kunden- oder Lieferanten-Objekt."""
    if obj is None:
        return []
    zeilen = []
    # Firmen- oder Personenname
    name_teile = [
        getattr(obj, "firmenname", None) or "",
        getattr(obj, "vorname", None) or "",
        getattr(obj, "nachname", None) or "",
    ]
    name = " ".join(t for t in name_teile if t).strip()
    if name:
        zeilen.append(name)
    # Straße
    strasse = getattr(obj, "strasse", None) or ""
    hausnr  = getattr(obj, "hausnummer", None) or ""
    if strasse:
        zeilen.append(f"{strasse} {hausnr}".strip())
    # PLZ Ort
    plz = getattr(obj, "plz", None) or ""
    ort = getattr(obj, "ort", None) or ""
    if plz or ort:
        zeilen.append(f"{plz} {ort}".strip())
    # Land (nur wenn nicht DE)
    land = getattr(obj, "land", "DE") or "DE"
    if land and land.upper() != "DE":
        zeilen.append(land.upper())
    return zeilen


# ---------------------------------------------------------------------------
# PDF-Klasse
# ---------------------------------------------------------------------------

LOGO_H     = 16   # Logo-Höhe in mm
HEADER_MIN = 32   # Mindesthöhe Briefkopf-Block in mm


class RechnungPDF(FPDF):

    def __init__(self, unternehmen: dict, rechnung, ist_kopie: bool = False):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(L_MARGIN, 12, R_MARGIN)
        self.set_auto_page_break(auto=True, margin=22)
        dv_dir = _find_dejavu_dir()
        self.add_font("DejaVu",     style="",  fname=str(dv_dir / "DejaVuSans.ttf"))
        self.add_font("DejaVu",     style="B", fname=str(dv_dir / "DejaVuSans-Bold.ttf"))
        self.add_font("DejaVuMono", style="",  fname=str(dv_dir / "DejaVuSansMono.ttf"))
        self._unt        = unternehmen
        self._r          = rechnung
        self._ist_kopie  = ist_kopie
        self._druckdatum = datetime.now().strftime("%d.%m.%Y")

    # -------------------------------------------------------------------------
    # Briefkopf (jede Seite)
    # -------------------------------------------------------------------------

    def header(self):
        unt     = self._unt
        start_y = 10.0

        absender = " ".join(filter(None, [
            unt.get("firmenname"), unt.get("vorname"), unt.get("nachname")
        ])) or "RechnungsFee"
        adresse  = f"{unt.get('strasse', '')} {unt.get('hausnummer', '')}".strip()
        plz_ort  = f"{unt.get('plz', '')} {unt.get('ort', '')}".strip()
        steuernr = unt.get("steuernummer") or ""
        ust_id   = unt.get("ust_idnr") or ""
        email    = unt.get("email") or ""
        telefon  = unt.get("telefon") or ""

        # --- Logo (links oben) ---
        logo_pfad = unt.get("logo_pfad")
        logo_w    = 0.0
        if logo_pfad and Path(logo_pfad).exists():
            try:
                self.image(logo_pfad, x=L_MARGIN, y=start_y, h=LOGO_H)
                # Breite des platzierten Logos ermitteln (Aspect Ratio)
                from PIL import Image as PilImage
                with PilImage.open(logo_pfad) as img:
                    iw, ih = img.size
                logo_w = LOGO_H * iw / ih + 3  # +3mm Abstand
            except Exception:
                logo_w = 0.0

        # --- Absender-Text (rechts neben Logo oder linksbündig) ---
        text_x = L_MARGIN + logo_w
        text_w = PAGE_W - R_MARGIN - text_x

        self.set_xy(text_x, start_y)
        self.set_font("DejaVu", "B", 12)
        self.set_text_color(*TEXT_DUNKEL)
        self.cell(text_w, 6, absender, new_x="LMARGIN", new_y="NEXT")

        self.set_x(text_x)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(*TEXT_GRAU)

        for zeile in filter(None, [adresse, plz_ort]):
            self.set_x(text_x)
            self.cell(text_w, 4.5, zeile, new_x="LMARGIN", new_y="NEXT")

        kontakt_parts = []
        if telefon: kontakt_parts.append(f"Tel: {telefon}")
        if email:   kontakt_parts.append(email)
        if kontakt_parts:
            self.set_x(text_x)
            self.cell(text_w, 4.5, "  ·  ".join(kontakt_parts), new_x="LMARGIN", new_y="NEXT")

        steuer_parts = []
        if steuernr: steuer_parts.append(f"StNr: {steuernr}")
        if ust_id:   steuer_parts.append(f"USt-IdNr: {ust_id}")
        if steuer_parts:
            self.set_x(text_x)
            self.cell(text_w, 4.5, "  ·  ".join(steuer_parts), new_x="LMARGIN", new_y="NEXT")

        # Trennlinie
        line_y = max(self.get_y(), start_y + HEADER_MIN) + 3
        self.set_draw_color(*GRAU_RAND)
        self.line(L_MARGIN, line_y, PAGE_W - R_MARGIN, line_y)
        self.set_y(line_y + 4)
        self.set_text_color(0, 0, 0)

    # -------------------------------------------------------------------------
    # Fußzeile (jede Seite)
    # -------------------------------------------------------------------------

    def footer(self):
        unt  = self._unt
        iban = unt.get("iban") or ""
        bic  = unt.get("bic") or ""
        bank = unt.get("bank_name") or ""

        self.set_y(-18)
        self.set_draw_color(*GRAU_RAND)
        self.line(L_MARGIN, self.get_y(), PAGE_W - R_MARGIN, self.get_y())
        self.ln(1.5)

        self.set_font("DejaVu", "", 7)
        self.set_text_color(*TEXT_GRAU)

        # Bankdaten links, Seitenzahl rechts
        bank_info = "  ·  ".join(filter(None, [
            f"IBAN: {iban}" if iban else "",
            f"BIC: {bic}" if bic else "",
            bank,
        ]))
        col_w = NUTZ_W / 2

        self.set_x(L_MARGIN)
        self.cell(col_w, 4, bank_info)
        self.cell(col_w, 4,
                  f"Seite {self.page_no()}  ·  {self._druckdatum}  ·  RechnungsFee",
                  align="R")
        self.set_text_color(0, 0, 0)

    # -------------------------------------------------------------------------
    # Inhalt (erste Seite)
    # -------------------------------------------------------------------------

    def render(self) -> bytes:
        r   = self._r
        unt = self._unt

        self.add_page()
        y0 = self.get_y()

        # --- Empfänger-Adressblock (links, DIN 5008) ---
        emp_x = L_MARGIN
        emp_w = 95.0   # mm

        # Absender-Kurzzeile (Fensterumschlag, §14: Absender erkennbar)
        absender_kurz = ", ".join(filter(None, [
            unt.get("firmenname"),
            f"{unt.get('strasse', '')} {unt.get('hausnummer', '')}".strip(),
            f"{unt.get('plz', '')} {unt.get('ort', '')}".strip(),
        ]))
        self.set_xy(emp_x, y0)
        self.set_font("DejaVu", "", 6.5)
        self.set_text_color(*TEXT_GRAU)
        self.cell(emp_w, 4, absender_kurz)
        self.set_draw_color(*GRAU_RAND)
        self.line(emp_x, self.get_y() + 4, emp_x + emp_w, self.get_y() + 4)

        # Empfänger-Adresse
        if r.typ == "ausgang":
            partner_obj  = r.kunde
            freitext     = r.partner_freitext
        else:
            partner_obj  = r.lieferant
            freitext     = r.partner_freitext

        adresszeilen = _adresszeilen(partner_obj)
        if not adresszeilen and freitext:
            adresszeilen = [freitext]

        emp_y = y0 + 6
        self.set_font("DejaVu", "", 9.5)
        self.set_text_color(*TEXT_DUNKEL)
        for i, zeile in enumerate(adresszeilen):
            self.set_xy(emp_x, emp_y + i * 5.5)
            font_style = "B" if i == 0 else ""
            self.set_font("DejaVu", font_style, 9.5)
            self.cell(emp_w, 5.5, zeile)

        emp_bottom = emp_y + max(len(adresszeilen), 1) * 5.5

        # --- Metadaten-Block (rechts) ---
        meta_x = L_MARGIN + emp_w + 5
        meta_w = NUTZ_W - emp_w - 5

        self.set_xy(meta_x, y0)
        meta_rows = []
        if r.typ == "ausgang":
            meta_rows.append(("Rechnungsnummer", r.rechnungsnummer or "—"))
        else:
            meta_rows.append(("Eingangsrechn.-Nr.", r.rechnungsnummer or "—"))
        meta_rows.append(("Rechnungsdatum", _iso_zu_de(str(r.datum))))
        if r.leistungsdatum and str(r.leistungsdatum) != str(r.datum):
            meta_rows.append(("Leistungsdatum", _iso_zu_de(str(r.leistungsdatum))))
        if r.faellig_am:
            meta_rows.append(("Fällig am", _iso_zu_de(str(r.faellig_am))))

        lbl_w = 38.0
        val_w = meta_w - lbl_w
        meta_y = y0
        for lbl, val in meta_rows:
            self.set_xy(meta_x, meta_y)
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
            self.cell(lbl_w, 5.5, lbl)
            self.set_font("DejaVu", "B", 8)
            self.set_text_color(*TEXT_DUNKEL)
            self.cell(val_w, 5.5, val)
            meta_y += 5.5

        # --- Rechnungstitel ---
        body_y = max(emp_bottom, meta_y) + 10
        self.set_xy(L_MARGIN, body_y)

        if r.typ == "ausgang":
            titel = f"Rechnung {r.rechnungsnummer or ''}".strip()
        else:
            titel = f"Eingangsrechnung {r.rechnungsnummer or ''}".strip()

        self.set_font("DejaVu", "B", 16)
        self.set_text_color(*TEXT_DUNKEL)
        self.cell(0, 9, titel, new_x="LMARGIN", new_y="NEXT")

        # Kopie-Hinweis (dezent, kein roter Banner)
        if self._ist_kopie:
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
            self.cell(0, 5, "– Kopie –", new_x="LMARGIN", new_y="NEXT")

        self.ln(4)

        # --- Positionstabelle ---
        # Spaltenbreiten: Beschr, Menge, Einheit, Netto, USt%, Brutto
        col_w = [82, 16, 17, 27, 14, 24]
        headers = ["Beschreibung", "Menge", "Einheit", "Netto", "USt %", "Brutto"]
        aligns  = ["L",            "R",     "L",       "R",     "R",     "R"]

        self.set_font("DejaVu", "B", 8)
        self.set_fill_color(*GRAU_HELL)
        self.set_draw_color(*GRAU_RAND)
        self.set_text_color(*TEXT_GRAU)
        for i, h in enumerate(headers):
            self.cell(col_w[i], 6.5, h, border="B", fill=True, align=aligns[i])
        self.ln()

        self.set_font("DejaVu", "", 8.5)
        self.set_text_color(*TEXT_DUNKEL)
        for pos in r.positionen:
            menge = float(str(pos.menge))
            menge_str = str(int(menge)) if menge == int(menge) else f"{menge:.3f}".rstrip("0")
            self.cell(col_w[0], 6, pos.beschreibung[:70])
            self.cell(col_w[1], 6, menge_str,             align="R")
            self.cell(col_w[2], 6, pos.einheit[:12])
            self.cell(col_w[3], 6, _fmt_euro(pos.netto),  align="R")
            self.cell(col_w[4], 6, f"{int(pos.ust_satz)} %", align="R")
            self.cell(col_w[5], 6, _fmt_euro(pos.brutto), align="R",
                      new_x="LMARGIN", new_y="NEXT")

        # --- Summenblock ---
        self.ln(3)
        sum_x = L_MARGIN + col_w[0] + col_w[1] + col_w[2]
        lbl_w = col_w[3] + col_w[4]
        val_w = col_w[5]

        def _sum_row(lbl: str, wert: str, bold: bool = False, trennlinie: bool = False):
            if trennlinie:
                self.set_draw_color(*GRAU_RAND)
                self.line(sum_x, self.get_y(), PAGE_W - R_MARGIN, self.get_y())
            self.set_x(sum_x)
            self.set_font("DejaVu", "B" if bold else "", 8.5)
            self.set_text_color(*TEXT_GRAU)
            self.cell(lbl_w, 5.5, lbl, align="R")
            self.set_text_color(*TEXT_DUNKEL)
            self.cell(val_w, 5.5, wert, align="R", new_x="LMARGIN", new_y="NEXT")

        _sum_row("Nettobetrag",   _fmt_euro(r.netto_gesamt))
        _sum_row("Umsatzsteuer",  _fmt_euro(r.ust_gesamt))
        _sum_row("Gesamtbetrag",  _fmt_euro(r.brutto_gesamt), bold=True, trennlinie=True)

        self.ln(5)

        # --- §19-Hinweis ---
        if unt.get("ist_kleinunternehmer"):
            self.set_font("DejaVu", "", 7.5)
            self.set_text_color(*TEXT_GRAU)
            self.cell(0, 5,
                      "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.",
                      new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

        # --- Zahlungshinweis (wenn IBAN vorhanden) ---
        iban = unt.get("iban") or ""
        if iban and r.typ == "ausgang":
            bic  = unt.get("bic") or ""
            bank = unt.get("bank_name") or ""
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
            betrag_str = _fmt_euro(r.brutto_gesamt)
            faellig_str = _iso_zu_de(str(r.faellig_am)) if r.faellig_am else "sofort"
            hinweis = (
                f"Bitte überweisen Sie {betrag_str} bis {faellig_str} "
                f"unter Angabe der Rechnungsnummer {r.rechnungsnummer or ''} "
                f"auf IBAN {iban}"
            )
            if bic:  hinweis += f"  ·  BIC {bic}"
            if bank: hinweis += f"  ({bank})"
            hinweis += "."
            self.multi_cell(0, 5, hinweis)
            self.ln(2)

        # --- Notizen ---
        if r.notizen:
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
            self.multi_cell(0, 5, r.notizen)

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
    :param ist_kopie:   True → dezenter Kopie-Hinweis unter dem Titel
    """
    pdf = RechnungPDF(unternehmen, rechnung, ist_kopie=ist_kopie)
    return pdf.render()
