"""
PDF-Export für Rechnungen (Eingang + Ausgang).

Layout nach DIN 5008 Form B / §14 UStG:

  ┌─────────────────────────────────────────────────────────┐
  │ Logo (links)       │  Firmenname + Adresse (rechts)     │ 10–43mm
  ├─────────────────────────────────────────────────────────┤  43mm
  │ Absender-Kurzzeile │  Rechnungsnr / Datum / Fällig      │ 45mm
  │ Empfänger-Adresse  │                                     │ 51–90mm
  ├─────────────────────────────────────────────────────────┤
  │ Rechnung RE-XXXX                                         │
  │ Positionstabelle                                         │
  │ Summen + Zahlungshinweis                                 │
  ├─────────────────────────────────────────────────────────┤
  │ Vollst. Firmendaten (Tel, E-Mail, Web, IBAN, HRB …)     │ Footer
  └─────────────────────────────────────────────────────────┘

Adressfeld startet IMMER bei Y=45mm (DIN 5008, Fensterumschlag-kompatibel).
Vollständige Firmendaten stehen im Footer (jede Seite).

Fonts: DejaVu (kommt mit fpdf2) für volle Unicode-Unterstützung.
"""

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from fpdf import FPDF
from utils.pdf_shared import build_hr_zeile, embed_unterschrift, epc_qr_bytes


def _find_dejavu_dir() -> Path:
    import sys

    # PyInstaller-Bundle: Fonts werden nach sys._MEIPASS/fonts/ extrahiert
    if getattr(sys, "frozen", False):
        p = Path(sys._MEIPASS) / "fonts"  # type: ignore[attr-defined]
        if (p / "DejaVuSans.ttf").exists():
            return p

    # Entwicklung / direkter Start: Fonts liegen im Projekt unter src/backend/fonts/
    local = Path(__file__).parent.parent / "fonts"
    if (local / "DejaVuSans.ttf").exists():
        return local

    # Fallback: System-Fonts (Linux)
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

L_MARGIN    = 20      # linker Rand mm (DIN 5008)
R_MARGIN    = 15
PAGE_W      = 210
NUTZ_W      = PAGE_W - L_MARGIN - R_MARGIN   # 175 mm

# DIN 5008 Form B: Anschriftfeld beginnt bei 45mm vom oberen Blattrand
ADRESS_Y    = 45.0

# Briefkopf-Separator: fest bei 43mm (2mm Abstand vor Adressfeld)
HEADER_LINE_Y = 43.0

# Unternehmensblock rechts im Header – bündig mit Rechnungsnummer-Spalte (meta_x = L_MARGIN+95)
BLOCK_X     = L_MARGIN + 95                  # 115 mm
BLOCK_W     = PAGE_W - R_MARGIN - BLOCK_X    # 80 mm

# Footer-Höhe: 3-Spalten-Layout (Col1 max 6 Zeilen à 3.8mm + Separator + Puffer)
FOOTER_H    = 28.0


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


def _person_bezeichnung(rechtsform: str) -> str:
    """Korrekte Personenbezeichnung je nach Rechtsform."""
    rf = (rechtsform or "").lower()
    if any(k in rf for k in ("gmbh", "ug", "ag", "se", "kgaa", "eg")):
        return "GF:"       # Geschäftsführer
    if any(k in rf for k in ("gbr", "ohg", "kg", "partg")):
        return "GS:"       # Gesellschafter
    return "Inh.:"         # Einzelunternehmer, Freiberufler


def _logo_abmessungen(pfad: str, max_h: float = 18.0, max_w: float = 55.0) -> tuple[float, float]:
    """Skaliert Logo auf max_h×max_w unter Beibehaltung der Aspect Ratio."""
    try:
        from PIL import Image as PilImage
        with PilImage.open(pfad) as img:
            px_w, px_h = img.size
        h = max_h
        w = h * px_w / px_h
        if w > max_w:
            w = max_w
            h = w * px_h / px_w
        return round(w, 2), round(h, 2)
    except Exception:
        return 0.0, 0.0


def _adresszeilen(obj) -> list[str]:
    """Vollständige Adresszeilen aus Kunden- oder Lieferanten-Objekt (§14 UStG)."""
    if obj is None:
        return []
    zeilen: list[str] = []
    firma   = (getattr(obj, "firmenname", None) or "").strip()
    vorname = (getattr(obj, "vorname",    None) or "").strip()
    nachname= (getattr(obj, "nachname",   None) or "").strip()
    person  = " ".join(filter(None, [vorname, nachname]))
    if firma:
        zeilen.append(firma)
        if person:
            zeilen.append(person)
    elif person:
        zeilen.append(person)
    z_hd = (getattr(obj, "z_hd", None) or "").strip()
    if z_hd:
        zeilen.append(f"z.Hd. {z_hd}")
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

    def __init__(self, unternehmen: dict, rechnung, ist_kopie: bool = False, ist_entwurf: bool = False):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(L_MARGIN, 10, R_MARGIN)
        self.set_auto_page_break(auto=True, margin=FOOTER_H + 4)
        dv_dir = _find_dejavu_dir()
        self.add_font("DejaVu", style="",  fname=str(dv_dir / "DejaVuSans.ttf"))
        self.add_font("DejaVu", style="B", fname=str(dv_dir / "DejaVuSans-Bold.ttf"))
        self._unt        = unternehmen
        self._r          = rechnung
        self._ist_kopie  = ist_kopie
        self._ist_entwurf = ist_entwurf
        self._druckdatum = datetime.now().strftime("%d.%m.%Y")

    # -------------------------------------------------------------------------
    # Briefkopf (jede Seite) – kompakt, endet bei HEADER_LINE_Y=43mm
    # -------------------------------------------------------------------------

    def header(self):
        unt = self._unt
        top = 10.0

        # --- Logo links oben ---
        logo_pfad = unt.get("logo_pfad") or ""
        if logo_pfad and Path(logo_pfad).exists():
            try:
                lw, lh = _logo_abmessungen(logo_pfad)
                if lw > 0:
                    self.image(logo_pfad, x=L_MARGIN, y=top, w=lw, h=lh)
            except Exception:
                pass

        # --- Firmenname + Adresse + Kontakt rechts (bündig mit Rechnungsnummer) ---
        absender = " ".join(filter(None, [
            unt.get("firmenname"), unt.get("vorname"), unt.get("nachname")
        ])) or "RechnungsFee"
        strasse  = f"{unt.get('strasse', '')} {unt.get('hausnummer', '')}".strip()
        plz_ort  = f"{unt.get('plz', '')} {unt.get('ort', '')}".strip()
        telefon  = unt.get("telefon") or ""
        email    = unt.get("email") or ""
        webseite = unt.get("webseite") or ""

        berufsbezeichnung = unt.get("berufsbezeichnung") or ""

        y = top
        self.set_xy(BLOCK_X, y)
        self.set_font("DejaVu", "B", 10)
        self.set_text_color(*TEXT_DUNKEL)
        self.cell(BLOCK_W, 5.5, absender, align="L")
        y += 5.5

        self.set_font("DejaVu", "", 8)
        self.set_text_color(*TEXT_GRAU)
        if berufsbezeichnung:
            self.set_xy(BLOCK_X, y)
            self.cell(BLOCK_W, 4.0, berufsbezeichnung, align="L")
            y += 4.0
        for zeile in filter(None, [strasse, plz_ort]):
            self.set_xy(BLOCK_X, y)
            self.cell(BLOCK_W, 4.0, zeile, align="L")
            y += 4.0

        for zeile in filter(None, [
            f"Tel: {telefon}" if telefon else "",
            f"E-Mail: {email}" if email else "",
            f"Web: {webseite}" if webseite else "",
        ]):
            self.set_xy(BLOCK_X, y)
            self.cell(BLOCK_W, 4.0, zeile, align="L")
            y += 4.0

        # --- Separator-Linie (fest bei 43mm) ---
        self.set_draw_color(*GRAU_RAND)
        self.line(L_MARGIN, HEADER_LINE_Y, PAGE_W - R_MARGIN, HEADER_LINE_Y)

        # Cursor auf Adressfeld-Start setzen
        self.set_y(ADRESS_Y)
        self.set_text_color(0, 0, 0)

    # -------------------------------------------------------------------------
    # Fußzeile (jede Seite) – vollständige Firmendaten
    # -------------------------------------------------------------------------

    def footer(self):
        unt = self._unt

        self.set_y(-FOOTER_H)

        # Separator
        self.set_draw_color(*GRAU_RAND)
        self.line(L_MARGIN, self.get_y(), PAGE_W - R_MARGIN, self.get_y())
        self.ln(1.5)

        self.set_font("DejaVu", "", 7)
        self.set_text_color(*TEXT_GRAU)

        col_w   = NUTZ_W / 3      # ≈ 58 mm je Spalte
        lh      = 3.8
        start_y = self.get_y()

        firmenname = unt.get("firmenname") or ""
        vorname    = unt.get("vorname") or ""
        nachname   = unt.get("nachname") or ""
        strasse    = f"{unt.get('strasse', '')} {unt.get('hausnummer', '')}".strip()
        plz_ort    = f"{unt.get('plz', '')} {unt.get('ort', '')}".strip()
        telefon    = unt.get("telefon") or ""
        email      = unt.get("email") or ""
        webseite   = unt.get("webseite") or ""
        ust_id     = unt.get("ust_idnr") or ""
        steuernr   = unt.get("steuernummer") or ""
        iban       = unt.get("iban") or ""
        bic        = unt.get("bic") or ""
        bank       = unt.get("bank_name") or ""

        def _col(x: float, zeilen: list[str]):
            y = start_y
            for z in zeilen:
                if z:
                    self.set_xy(x, y)
                    self.cell(col_w, lh, z)
                    y += lh

        # ── Spalte 1: Name · Adresse · Kontakt ───────────────────────────────
        name = " ".join(filter(None, [firmenname, vorname, nachname]))
        _col(L_MARGIN, list(filter(None, [
            name,
            strasse,
            plz_ort,
            f"Tel: {telefon}" if telefon else "",
            f"E-Mail: {email}" if email else "",
            f"Web: {webseite}" if webseite else "",
        ])))

        # ── Spalte 2: Inhaber · USt-ID (bevorzugt) oder StNr · HRB ──────────
        # Personen-Label je nach Rechtsform; nur wenn Firmenname + Vor-/Nachname vorhanden
        inhaber      = " ".join(filter(None, [vorname, nachname])) if firmenname else ""
        person_label = _person_bezeichnung(unt.get("rechtsform") or "")
        steuer    = f"USt-ID: {ust_id}" if ust_id else (f"StNr: {steuernr}" if steuernr else "")
        hr_zeile  = build_hr_zeile(unt)
        kammer    = unt.get("kammer_mitgliedschaft") or ""
        _col(L_MARGIN + col_w, list(filter(None, [
            f"{person_label} {inhaber}" if inhaber else "",
            steuer,
            hr_zeile,
            kammer,
        ])))

        # ── Spalte 3: Bankdaten · Seite ──────────────────────────────────────
        _col(L_MARGIN + 2 * col_w, list(filter(None, [
            bank,
            f"IBAN: {iban}" if iban else "",
            f"BIC: {bic}" if bic else "",
            f"Seite {self.page_no()}  ·  {self._druckdatum}",
        ])))

        self.set_text_color(0, 0, 0)

    # -------------------------------------------------------------------------
    # Inhalt
    # -------------------------------------------------------------------------

    def render(self) -> bytes:
        r   = self._r
        unt = self._unt

        self.add_page()
        # header() hat den Cursor bereits auf ADRESS_Y=45mm gesetzt

        # --- Absender-Kurzzeile (DIN 5008: erste 5mm des Anschriftfeldes) ---
        absender_kurz = "  ·  ".join(filter(None, [
            unt.get("firmenname"),
            f"{unt.get('strasse', '')} {unt.get('hausnummer', '')}".strip(),
            f"{unt.get('plz', '')} {unt.get('ort', '')}".strip(),
        ]))
        self.set_xy(L_MARGIN, ADRESS_Y)
        self.set_font("DejaVu", "", 6.5)
        self.set_text_color(*TEXT_GRAU)
        self.cell(90, 4.5, absender_kurz)
        # Trennlinie unter Kurzzeile
        self.set_draw_color(*GRAU_RAND)
        self.line(L_MARGIN, ADRESS_Y + 5, L_MARGIN + 90, ADRESS_Y + 5)

        # --- Empfänger-Adressblock (DIN 5008: ab ~50mm, max 6 Zeilen à 5.5mm = 33mm) ---
        if r.typ == "ausgang":
            partner_obj = r.kunde
            freitext    = r.partner_freitext
        else:
            partner_obj = r.lieferant
            freitext    = r.partner_freitext

        adresszeilen = _adresszeilen(partner_obj)
        if not adresszeilen and freitext:
            adresszeilen = [freitext]

        emp_y = ADRESS_Y + 6.5
        for i, zeile in enumerate(adresszeilen):
            self.set_xy(L_MARGIN, emp_y + i * 5.5)
            self.set_font("DejaVu", "B" if i == 0 else "", 9.5)
            self.set_text_color(*TEXT_DUNKEL)
            self.cell(90, 5.5, zeile)

        emp_bottom = emp_y + len(adresszeilen) * 5.5

        # --- Rechnungsmetadaten (rechts neben Empfänger, ab ADRESS_Y) ---
        meta_x   = L_MARGIN + 95
        meta_lbl = 42.0
        meta_val = PAGE_W - R_MARGIN - meta_x - meta_lbl
        meta_y   = ADRESS_Y

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

        titel = (
            f"Rechnung {r.rechnungsnummer or ''}".strip()
            if r.typ == "ausgang"
            else f"Eingangsrechnung {r.rechnungsnummer or ''}".strip()
        )
        self.set_font("DejaVu", "B", 16)
        self.set_text_color(*TEXT_DUNKEL)
        self.cell(0, 9, titel, new_x="LMARGIN", new_y="NEXT")

        if self._ist_entwurf:
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
            self.cell(0, 5, "– Entwurf –", new_x="LMARGIN", new_y="NEXT")
        elif self._ist_kopie:
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
            self.cell(0, 5, "– Kopie –", new_x="LMARGIN", new_y="NEXT")

        self.ln(4)

        # --- Positionstabelle ---
        col_w   = [82, 16, 17, 27, 14, 24]
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
            row_y = self.get_y()
            # Rechte Zellen zuerst – einzeilig, an row_y ausgerichtet
            self.set_x(L_MARGIN + col_w[0])
            self.cell(col_w[1], 6, menge_str,             align="R")
            self.cell(col_w[2], 6, pos.einheit[:12])
            self.cell(col_w[3], 6, _fmt_euro(pos.netto),  align="R")
            self.cell(col_w[4], 6, f"{int(pos.ust_satz)} %", align="R")
            self.cell(col_w[5], 6, _fmt_euro(pos.brutto), align="R")
            # Beschreibung als multi_cell – unterstützt Zeilenumbrüche und \n
            self.set_xy(L_MARGIN, row_y)
            self.multi_cell(col_w[0], 6, pos.beschreibung or "",
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

        # --- Zahlungshinweis / Zahlungsbestätigung ---
        zahlungsstatus = str(getattr(r, "zahlungsstatus", "offen") or "offen")
        zahlungen = [
            z for z in (getattr(r, "kassenbucheintraege", None) or [])
            if not getattr(z, "storniert", False)
        ]

        self.set_font("DejaVu", "", 8)
        self.set_text_color(*TEXT_GRAU)

        if zahlungsstatus in ("bezahlt", "teilweise") and zahlungen:
            # Bezahlte / teilweise bezahlte Rechnung – Zahlungsbestätigung
            art_labels = {
                "Bar": "Barzahlung", "Karte": "Kartenzahlung",
                "PayPal": "PayPal", "Bank": "Überweisung",
            }
            for z in zahlungen:
                art_label = art_labels.get(
                    str(getattr(z, "zahlungsart", "")),
                    str(getattr(z, "zahlungsart", ""))
                )
                prefix = (
                    "Rechnungsbetrag bereits dankend erhalten"
                    if zahlungsstatus == "bezahlt" and len(zahlungen) == 1
                    else "Teilbetrag dankend erhalten"
                )
                zeile = (
                    f"{prefix} am {_iso_zu_de(str(z.datum))} "
                    f"per {art_label}: {_fmt_euro(z.brutto_betrag)}"
                )
                self.cell(0, 5, zeile, new_x="LMARGIN", new_y="NEXT")
        else:
            # Offene Rechnung – Überweisungsaufforderung (nur wenn aktiv)
            if unt.get("zahlungshinweis_aktiv", True):
                iban = unt.get("iban") or ""
                if iban and r.typ == "ausgang":
                    bic     = unt.get("bic") or ""
                    faellig = _iso_zu_de(str(r.faellig_am)) if r.faellig_am else "sofort"
                    hinweis = (
                        f"Bitte überweisen Sie {_fmt_euro(r.brutto_gesamt)} bis {faellig} "
                        f"unter Angabe der Rechnungsnummer {r.rechnungsnummer or ''} "
                        f"auf IBAN {iban}"
                    )
                    if bic: hinweis += f"  ·  BIC {bic}"
                    hinweis += "."

                    qr_aktiv = unt.get("qr_zahlung_aktiv", False)
                    if qr_aktiv:
                        qr_size  = 25
                        gap      = 4
                        text_w   = NUTZ_W - qr_size - gap
                        y_start  = self.get_y()
                        qr_x     = L_MARGIN + text_w + gap
                        self.multi_cell(text_w, 5, hinweis)
                        empf = unt.get("firmenname") or " ".join(
                            p for p in [unt.get("vorname"), unt.get("nachname")] if p
                        )
                        qr_data = epc_qr_bytes(iban, bic, empf, float(r.brutto_gesamt), r.rechnungsnummer or "")
                        if qr_data:
                            self.image(BytesIO(qr_data), x=qr_x, y=y_start, w=qr_size, h=qr_size)
                            # Label unterhalb des QR
                            self.set_font("DejaVu", "", 6)
                            self.set_text_color(*TEXT_GRAU)
                            self.set_xy(qr_x, y_start + qr_size + 1)
                            self.cell(qr_size, 4, "Per Banking-App zahlen", align="C")
                            self.set_font("DejaVu", "", 8)
                            if self.get_y() < y_start + qr_size + 5:
                                self.set_y(y_start + qr_size + 5)
                    else:
                        self.multi_cell(0, 5, hinweis)
        self.ln(2)

        # --- Notizen ---
        if r.notizen:
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
            self.multi_cell(0, 5, r.notizen)

        # --- Digitale Unterschrift ---
        embed_unterschrift(self, unt, L_MARGIN)

        self.set_text_color(0, 0, 0)
        return bytes(self.output())


# ---------------------------------------------------------------------------
# Öffentliche Funktion
# ---------------------------------------------------------------------------

def generate_rechnung_pdf(
    rechnung, unternehmen: dict,
    ist_kopie: bool = False,
    ist_entwurf: bool = False,
    mit_output_intent: bool = False,
) -> bytes:
    """
    Erzeugt ein PDF für die übergebene Rechnung.

    :param rechnung:            SQLAlchemy-Rechnung-Objekt (mit .positionen, .kunde, .lieferant)
    :param unternehmen:         dict mit allen Firmendaten
    :param ist_kopie:           True → dezenter „– Kopie –"-Hinweis unter dem Titel
    :param ist_entwurf:         True → „– Entwurf –"-Hinweis, kein ausgegeben-Flag
    :param mit_output_intent:   True → sRGB-OutputIntent für PDF/A-3 (ZUGFeRD)
    """
    pdf = RechnungPDF(unternehmen, rechnung, ist_kopie=ist_kopie, ist_entwurf=ist_entwurf)
    if mit_output_intent:
        from fpdf.enums import OutputIntentSubType
        from fpdf.output import PDFICCProfile
        from fpdf.util import builtin_srgb2014_bytes
        pdf.add_output_intent(
            OutputIntentSubType.PDFA,
            output_condition_identifier="sRGB",
            output_condition="IEC 61966-2-1:1999",
            registry_name="http://www.color.org",
            dest_output_profile=PDFICCProfile(
                contents=builtin_srgb2014_bytes(),
                n=3,
                alternate="DeviceRGB",
            ),
            info="sRGB2014 (v2)",
        )
    return pdf.render()
