"""
PDF-Export für Rechnungen (Eingang + Ausgang).
Layout nach DIN 5008 / §14 UStG:
  - Logo links oben
  - Unternehmensblock rechts (Name, Adresse, Steuer, Kontakt, Bank)
  - Empfänger-Adressblock links (§14 IV Nr. 1 Pflichtangabe)
  - Rechnungsmetadaten rechts daneben
  - Positionstabelle + Summen + Zahlungshinweis

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

GRAU_HELL   = (245, 246, 248)
GRAU_RAND   = (210, 213, 220)
TEXT_GRAU   = (110, 115, 125)
TEXT_DUNKEL = (20, 24, 35)

L_MARGIN = 15
R_MARGIN = 15
PAGE_W   = 210
NUTZ_W   = PAGE_W - L_MARGIN - R_MARGIN  # 180 mm

# Unternehmensblock: rechte Spalte
BLOCK_X = 110.0   # Startpunkt links des Unternehmensblocks
BLOCK_W = PAGE_W - R_MARGIN - BLOCK_X  # ≈ 85 mm

LOGO_MAX_H = 20.0  # maximale Logo-Höhe mm
LOGO_MAX_W = 60.0  # maximale Logo-Breite mm


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


def _logo_abmessungen(pfad: str) -> tuple[float, float]:
    """Gibt (breite_mm, hoehe_mm) zurück, skaliert auf LOGO_MAX_H/LOGO_MAX_W."""
    try:
        from PIL import Image as PilImage
        with PilImage.open(pfad) as img:
            px_w, px_h = img.size
        # skalieren: primär auf Höhe, dann auf Breite kappen
        h = LOGO_MAX_H
        w = h * px_w / px_h
        if w > LOGO_MAX_W:
            w = LOGO_MAX_W
            h = w * px_h / px_w
        return w, h
    except Exception:
        return 0.0, 0.0


def _adresszeilen(obj) -> list[str]:
    """Vollständige Adresszeilen aus Kunden- oder Lieferanten-Objekt."""
    if obj is None:
        return []
    zeilen = []
    name = " ".join(filter(None, [
        getattr(obj, "firmenname", None) or "",
        getattr(obj, "vorname", None) or "",
        getattr(obj, "nachname", None) or "",
    ])).strip()
    if name:
        zeilen.append(name)
    strasse = getattr(obj, "strasse", None) or ""
    hausnr  = getattr(obj, "hausnummer", None) or ""
    if strasse:
        zeilen.append(f"{strasse} {hausnr}".strip())
    plz = getattr(obj, "plz", None) or ""
    ort = getattr(obj, "ort", None) or ""
    if plz or ort:
        zeilen.append(f"{plz} {ort}".strip())
    land = (getattr(obj, "land", None) or "DE").upper()
    if land != "DE":
        zeilen.append(land)
    return zeilen


# ---------------------------------------------------------------------------
# PDF-Klasse
# ---------------------------------------------------------------------------

class RechnungPDF(FPDF):

    def __init__(self, unternehmen: dict, rechnung, ist_kopie: bool = False):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(L_MARGIN, 10, R_MARGIN)
        self.set_auto_page_break(auto=True, margin=22)
        dv_dir = _find_dejavu_dir()
        self.add_font("DejaVu",  style="",  fname=str(dv_dir / "DejaVuSans.ttf"))
        self.add_font("DejaVu",  style="B", fname=str(dv_dir / "DejaVuSans-Bold.ttf"))
        self._unt        = unternehmen
        self._r          = rechnung
        self._ist_kopie  = ist_kopie
        self._druckdatum = datetime.now().strftime("%d.%m.%Y")
        # Header-Höhe vorberechnen damit body_y auf jeder Seite stimmt
        self._header_h   = self._calc_header_h()

    # -------------------------------------------------------------------------
    # Hilfsmethode: Höhe des Unternehmensblocks schätzen
    # -------------------------------------------------------------------------

    def _calc_header_h(self) -> float:
        """Schätzt die Gesamthöhe des Briefkopfs in mm."""
        unt = self._unt
        zeilen = 0
        # Firmenname
        zeilen += 1
        # Adresse
        for f in ["strasse", "plz", "land"]:
            if unt.get(f):
                zeilen += 1
        # Leerzeile Trenngruppe
        steuer_da = any(unt.get(k) for k in ["steuernummer", "ust_idnr", "handelsregister_nr"])
        kontakt_da = any(unt.get(k) for k in ["telefon", "email", "webseite"])
        bank_da = unt.get("iban")
        if steuer_da:
            zeilen += sum(1 for k in ["steuernummer", "ust_idnr", "handelsregister_nr"] if unt.get(k))
            zeilen += 1  # Leerzeile
        if kontakt_da:
            zeilen += sum(1 for k in ["telefon", "email", "webseite"] if unt.get(k))
            zeilen += 1
        if bank_da:
            zeilen += 1 + (1 if unt.get("bic") else 0)

        block_h = 10 + zeilen * 4.5  # Start 10mm + Zeilen
        # Logo-Höhe berücksichtigen
        logo_pfad = unt.get("logo_pfad")
        if logo_pfad and Path(logo_pfad).exists():
            _, lh = _logo_abmessungen(logo_pfad)
            block_h = max(block_h, lh + 6)

        return max(block_h, 35.0) + 6  # +6mm für Linie + Abstand

    # -------------------------------------------------------------------------
    # Briefkopf (jede Seite)
    # -------------------------------------------------------------------------

    def header(self):
        unt = self._unt
        top = 10.0

        # === Logo links ===
        logo_pfad = unt.get("logo_pfad")
        if logo_pfad and Path(logo_pfad).exists():
            try:
                lw, lh = _logo_abmessungen(logo_pfad)
                if lw > 0:
                    self.image(logo_pfad, x=L_MARGIN, y=top, w=lw, h=lh)
            except Exception:
                pass

        # === Unternehmensblock rechts ===
        y = top

        def _zeile(text: str, bold: bool = False, size: float = 8.5, color=TEXT_DUNKEL):
            nonlocal y
            self.set_xy(BLOCK_X, y)
            self.set_font("DejaVu", "B" if bold else "", size)
            self.set_text_color(*color)
            self.cell(BLOCK_W, 4.5, text, new_x="LMARGIN", new_y="NEXT")
            y += 4.5

        def _leer():
            nonlocal y
            y += 2.5

        # Firmenname
        absender = " ".join(filter(None, [
            unt.get("firmenname"), unt.get("vorname"), unt.get("nachname")
        ])) or "RechnungsFee"
        _zeile(absender, bold=True, size=9.0)

        # Adresse
        strasse = f"{unt.get('strasse', '')} {unt.get('hausnummer', '')}".strip()
        plz_ort = f"{unt.get('plz', '')} {unt.get('ort', '')}".strip()
        land    = (unt.get("land") or "DE").upper()
        if strasse: _zeile(strasse, color=TEXT_GRAU)
        if plz_ort: _zeile(plz_ort, color=TEXT_GRAU)
        if land and land != "DE": _zeile(land, color=TEXT_GRAU)

        # Steuer / Rechtsangaben
        steuernr   = unt.get("steuernummer") or ""
        ust_id     = unt.get("ust_idnr") or ""
        hr_nr      = unt.get("handelsregister_nr") or ""
        hr_gericht = unt.get("handelsregister_gericht") or ""
        steuer_zeilen = []
        if ust_id:   steuer_zeilen.append(f"USt-ID: {ust_id}")
        if steuernr: steuer_zeilen.append(f"Steuernr.: {steuernr}")
        if hr_nr:
            hr_text = f"Handelsregister: {hr_nr}"
            if hr_gericht: hr_text += f" ({hr_gericht})"
            steuer_zeilen.append(hr_text)
        if steuer_zeilen:
            _leer()
            for z in steuer_zeilen:
                _zeile(z, color=TEXT_GRAU)

        # Kontakt
        telefon = unt.get("telefon") or ""
        email   = unt.get("email") or ""
        webseite = unt.get("webseite") or ""
        kontakt_zeilen = []
        if telefon:  kontakt_zeilen.append(f"Telefon: {telefon}")
        if email:    kontakt_zeilen.append(f"E-Mail: {email}")
        if webseite: kontakt_zeilen.append(f"Webseite: {webseite}")
        if kontakt_zeilen:
            _leer()
            for z in kontakt_zeilen:
                _zeile(z, color=TEXT_GRAU)

        # Bankverbindung
        iban = unt.get("iban") or ""
        bic  = unt.get("bic") or ""
        if iban:
            _leer()
            _zeile(f"IBAN: {iban}", color=TEXT_GRAU)
            if bic: _zeile(f"BIC: {bic}", color=TEXT_GRAU)

        # Trennlinie
        line_y = max(y, self._header_h - 4)
        self.set_draw_color(*GRAU_RAND)
        self.line(L_MARGIN, line_y, PAGE_W - R_MARGIN, line_y)
        self.set_y(line_y + 4)
        self.set_text_color(0, 0, 0)

    # -------------------------------------------------------------------------
    # Fußzeile (jede Seite)
    # -------------------------------------------------------------------------

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(*GRAU_RAND)
        self.line(L_MARGIN, self.get_y(), PAGE_W - R_MARGIN, self.get_y())
        self.ln(1.5)
        self.set_font("DejaVu", "", 7)
        self.set_text_color(*TEXT_GRAU)
        self.cell(
            0, 4,
            f"Seite {self.page_no()}  ·  {self._druckdatum}  ·  RechnungsFee",
            align="C",
        )
        self.set_text_color(0, 0, 0)

    # -------------------------------------------------------------------------
    # Inhalt
    # -------------------------------------------------------------------------

    def render(self) -> bytes:
        r   = self._r
        unt = self._unt

        self.add_page()
        y0 = self.get_y()

        # --- Absender-Kurzzeile (für Fensterumschlag) ---
        absender_kurz = ", ".join(filter(None, [
            unt.get("firmenname"),
            f"{unt.get('strasse', '')} {unt.get('hausnummer', '')}".strip(),
            f"{unt.get('plz', '')} {unt.get('ort', '')}".strip(),
        ]))
        self.set_xy(L_MARGIN, y0)
        self.set_font("DejaVu", "", 6.5)
        self.set_text_color(*TEXT_GRAU)
        self.cell(90, 4, absender_kurz)
        # Trennlinie unter Kurzzeile
        self.set_draw_color(*GRAU_RAND)
        self.line(L_MARGIN, y0 + 4.5, L_MARGIN + 90, y0 + 4.5)

        # --- Empfänger-Adressblock (links) ---
        if r.typ == "ausgang":
            partner_obj = r.kunde
            freitext    = r.partner_freitext
        else:
            partner_obj = r.lieferant
            freitext    = r.partner_freitext

        adresszeilen = _adresszeilen(partner_obj)
        if not adresszeilen and freitext:
            adresszeilen = [freitext]

        emp_y = y0 + 6
        for i, zeile in enumerate(adresszeilen):
            self.set_xy(L_MARGIN, emp_y + i * 5.5)
            self.set_font("DejaVu", "B" if i == 0 else "", 9.5)
            self.set_text_color(*TEXT_DUNKEL)
            self.cell(90, 5.5, zeile)

        emp_bottom = emp_y + max(len(adresszeilen), 1) * 5.5

        # --- Rechnungsmetadaten (rechts, neben Empfänger) ---
        meta_x  = L_MARGIN + 95
        meta_lbl = 40.0
        meta_val = PAGE_W - R_MARGIN - meta_x - meta_lbl
        meta_y  = y0

        def _meta(lbl: str, val: str):
            nonlocal meta_y
            self.set_xy(meta_x, meta_y)
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
            self.cell(meta_lbl, 5.5, lbl)
            self.set_font("DejaVu", "B", 8)
            self.set_text_color(*TEXT_DUNKEL)
            self.cell(meta_val, 5.5, val)
            meta_y += 5.5

        if r.typ == "ausgang":
            _meta("Rechnungsnummer", r.rechnungsnummer or "—")
        else:
            _meta("Eingangsrechn.-Nr.", r.rechnungsnummer or "—")
        _meta("Rechnungsdatum", _iso_zu_de(str(r.datum)))
        if r.leistungsdatum and str(r.leistungsdatum) != str(r.datum):
            _meta("Leistungsdatum", _iso_zu_de(str(r.leistungsdatum)))
        if r.faellig_am:
            _meta("Fällig am", _iso_zu_de(str(r.faellig_am)))

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

        if self._ist_kopie:
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
            self.cell(0, 5, "– Kopie –", new_x="LMARGIN", new_y="NEXT")

        self.ln(4)

        # --- Positionstabelle ---
        col_w  = [82, 16, 17, 27, 14, 24]
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
            menge     = float(str(pos.menge))
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

        def _sum_row(lbl: str, wert: str, bold: bool = False, trenn: bool = False):
            if trenn:
                self.set_draw_color(*GRAU_RAND)
                self.line(sum_x, self.get_y(), PAGE_W - R_MARGIN, self.get_y())
            self.set_x(sum_x)
            self.set_font("DejaVu", "B" if bold else "", 8.5)
            self.set_text_color(*TEXT_GRAU)
            self.cell(lbl_w, 5.5, lbl, align="R")
            self.set_text_color(*TEXT_DUNKEL)
            self.cell(val_w, 5.5, wert, align="R", new_x="LMARGIN", new_y="NEXT")

        _sum_row("Nettobetrag",  _fmt_euro(r.netto_gesamt))
        _sum_row("Umsatzsteuer", _fmt_euro(r.ust_gesamt))
        _sum_row("Gesamtbetrag", _fmt_euro(r.brutto_gesamt), bold=True, trenn=True)

        self.ln(6)

        # --- §19-Hinweis ---
        if unt.get("ist_kleinunternehmer"):
            self.set_font("DejaVu", "", 7.5)
            self.set_text_color(*TEXT_GRAU)
            self.cell(0, 5,
                      "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.",
                      new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

        # --- Zahlungshinweis ---
        iban = unt.get("iban") or ""
        if iban and r.typ == "ausgang":
            bic       = unt.get("bic") or ""
            bank      = unt.get("bank_name") or ""
            faellig   = _iso_zu_de(str(r.faellig_am)) if r.faellig_am else "sofort"
            hinweis   = (
                f"Bitte überweisen Sie {_fmt_euro(r.brutto_gesamt)} bis {faellig} "
                f"unter Angabe der Rechnungsnummer {r.rechnungsnummer or ''} "
                f"auf IBAN {iban}"
            )
            if bic:  hinweis += f"  ·  BIC {bic}"
            if bank: hinweis += f"  ({bank})"
            hinweis += "."
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
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
    Erzeugt ein PDF für die übergebene Rechnung.

    :param rechnung:    SQLAlchemy-Rechnung-Objekt (mit .positionen, .kunde, .lieferant)
    :param unternehmen: dict mit Firmendaten
    :param ist_kopie:   True → dezenter „– Kopie –"-Hinweis unter dem Titel
    """
    pdf = RechnungPDF(unternehmen, rechnung, ist_kopie=ist_kopie)
    return pdf.render()
