"""
Basis-Klasse für Rechnungs-PDFs (DIN 5008 / §14 UStG).

Unterklassen implementieren:
  _render_positionen()    Positionstabelle; muss self._sum_x/_sum_lbl_w/_sum_val_w setzen
  _render_zahlungsblock() Zahlungshinweis / Bezahldaten-Block

Optional überschreibbar:
  _render_nach_titel()    Inhalte zwischen Titel und Tabelle (z.B. Anrede in Vorlage 1)

Klassenattribute für Vorlage-Anpassungen:
  _faellig_label          Label für Fälligkeitsdatum
  _ln_nach_positionen     Abstand Positionen → Summenblock
  _ln_nach_summen         Abstand Summenblock → §19-Hinweis
  _ln_nach_19             Abstand §19-Hinweis → Zahlungsblock
"""

import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from fpdf import FPDF
from utils.pdf_shared import build_hr_zeile, embed_unterschrift


# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

GRAU_HELL   = (245, 246, 248)
GRAU_RAND   = (210, 213, 220)
TEXT_GRAU   = (110, 115, 125)
TEXT_DUNKEL = (20, 24, 35)

L_MARGIN    = 20
R_MARGIN    = 15
PAGE_W      = 210
NUTZ_W      = PAGE_W - L_MARGIN - R_MARGIN   # 175 mm

ADRESS_Y      = 45.0
HEADER_LINE_Y = 43.0

BLOCK_X = L_MARGIN + 95
BLOCK_W = PAGE_W - R_MARGIN - BLOCK_X

FOOTER_H = 28.0


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _md(text: str) -> str:
    """Konvertiert Standard-Markdown zu fpdf2-Syntax.
    *kursiv* → __kursiv__  (fpdf2 nutzt __ statt *)
    **fett** bleibt unverändert (Lookahead/Lookbehind schützt Doppel-Sternchen).
    """
    return re.sub(r'(?<!\*)\*(?!\*)([^*\n]+?)(?<!\*)\*(?!\*)', r'__\1__', text)


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
    raise FileNotFoundError(
        "DejaVu-Fonts nicht gefunden. Bitte 'fonts-dejavu-core' installieren "
        "(sudo apt install fonts-dejavu-core)."
    )


def _fmt_euro(val: Any) -> str:
    try:
        n = float(str(val))
    except (ValueError, TypeError):
        n = 0.0
    sign = "-" if n < 0 else ""
    formatted = f"{abs(n):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{sign}{formatted} €"


def _iso_zu_de(iso: str) -> str:
    try:
        y, m, d = str(iso)[:10].split("-")
        return f"{d}.{m}.{y}"
    except Exception:
        return str(iso)


def _ust_aufschluesselung(positionen) -> list[tuple[int, float, float]]:
    """Gruppiert Positionen nach USt-Satz. Gibt [(satz_int, netto_sum, ust_sum), ...] zurück."""
    netto_by: dict[int, float] = {}
    ust_by:   dict[int, float] = {}
    for pos in positionen:
        satz  = int(float(str(pos.ust_satz)))
        menge = float(str(pos.menge))
        # pos.brutto − pos.ust_betrag = effektiver Netto-Einzelpreis (nach Positionsrabatt)
        netto_eff = float(str(pos.brutto)) - float(str(pos.ust_betrag))
        netto_by[satz] = netto_by.get(satz, 0.0) + netto_eff              * menge
        ust_by[satz]   = ust_by.get(satz, 0.0)   + float(str(pos.ust_betrag)) * menge
    return sorted([(s, netto_by[s], ust_by[s]) for s in netto_by], key=lambda x: x[0])


def _person_bezeichnung(rechtsform: str) -> str:
    rf = (rechtsform or "").lower()
    if any(k in rf for k in ("gmbh", "ug", "ag", "se", "kgaa", "eg")):
        return "GF:"
    if any(k in rf for k in ("gbr", "ohg", "kg", "partg")):
        return "GS:"
    return "Inh.:"


def _logo_abmessungen(pfad: str, max_h: float = 18.0, max_w: float = 55.0) -> tuple[float, float]:
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
    if obj is None:
        return []
    zeilen: list[str] = []
    firma    = (getattr(obj, "firmenname", None) or "").strip()
    vorname  = (getattr(obj, "vorname",    None) or "").strip()
    nachname = (getattr(obj, "nachname",   None) or "").strip()
    person   = " ".join(filter(None, [vorname, nachname]))
    if firma:
        zeilen.append(firma)
        if person:
            zeilen.append(person)
    elif person:
        zeilen.append(person)
    z_hd = (getattr(obj, "z_hd", None) or "").strip()
    if z_hd:
        zeilen.append(f"z.Hd. {z_hd}")
    strasse = getattr(obj, "strasse",    None) or ""
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
# Basisklasse
# ---------------------------------------------------------------------------

class RechnungPDFBase(FPDF):

    _faellig_label      = "Fällig am"
    _ln_nach_positionen = 3
    _ln_nach_summen     = 6
    _ln_nach_19         = 2

    def __init__(self, unternehmen: dict, rechnung,
                 ist_kopie: bool = False, ist_entwurf: bool = False, ist_netto: bool = True):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(L_MARGIN, 10, R_MARGIN)
        self.set_auto_page_break(auto=True, margin=FOOTER_H + 4)
        dv_dir = _find_dejavu_dir()
        self.add_font("DejaVu", style="",   fname=str(dv_dir / "DejaVuSans.ttf"))
        self.add_font("DejaVu", style="B",  fname=str(dv_dir / "DejaVuSans-Bold.ttf"))
        if (dv_dir / "DejaVuSans-Oblique.ttf").exists():
            self.add_font("DejaVu", style="I",  fname=str(dv_dir / "DejaVuSans-Oblique.ttf"))
            self.add_font("DejaVu", style="BI", fname=str(dv_dir / "DejaVuSans-BoldOblique.ttf"))
        self._unt         = unternehmen
        self._r           = rechnung
        self._ist_kopie   = ist_kopie
        self._ist_entwurf = ist_entwurf
        self._ist_netto   = ist_netto
        self._druckdatum  = datetime.now().strftime("%d.%m.%Y")
        # Summenblock-Geometrie – wird von _render_positionen() gesetzt
        self._sum_x     = 0.0
        self._sum_lbl_w = 0.0
        self._sum_val_w = 0.0

    # -------------------------------------------------------------------------
    # Header / Footer (identisch in allen Vorlagen)
    # -------------------------------------------------------------------------

    def header(self):
        unt = self._unt
        top = 10.0

        logo_pfad = unt.get("logo_pfad") or ""
        if logo_pfad and Path(logo_pfad).exists():
            try:
                lw, lh = _logo_abmessungen(logo_pfad)
                if lw > 0:
                    self.image(logo_pfad, x=L_MARGIN, y=top, w=lw, h=lh)
            except Exception:
                pass

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

        self.set_draw_color(*GRAU_RAND)
        self.line(L_MARGIN, HEADER_LINE_Y, PAGE_W - R_MARGIN, HEADER_LINE_Y)
        self.set_y(ADRESS_Y)
        self.set_text_color(0, 0, 0)

    def footer(self):
        unt = self._unt
        self.set_y(-FOOTER_H)
        self.set_draw_color(*GRAU_RAND)
        self.line(L_MARGIN, self.get_y(), PAGE_W - R_MARGIN, self.get_y())
        self.ln(1.5)

        self.set_font("DejaVu", "", 7)
        self.set_text_color(*TEXT_GRAU)

        col_w   = NUTZ_W / 3
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

        name = " ".join(filter(None, [firmenname, vorname, nachname]))
        _col(L_MARGIN, list(filter(None, [
            name, strasse, plz_ort,
            f"Tel: {telefon}" if telefon else "",
            f"E-Mail: {email}" if email else "",
            f"Web: {webseite}" if webseite else "",
        ])))

        inhaber      = " ".join(filter(None, [vorname, nachname])) if firmenname else ""
        person_label = _person_bezeichnung(unt.get("rechtsform") or "")
        steuer   = f"USt-ID: {ust_id}" if ust_id else (f"StNr: {steuernr}" if steuernr else "")
        hr_zeile = build_hr_zeile(unt)
        kammer   = unt.get("kammer_mitgliedschaft") or ""
        _col(L_MARGIN + col_w, list(filter(None, [
            f"{person_label} {inhaber}" if inhaber else "",
            steuer, hr_zeile, kammer,
        ])))

        _col(L_MARGIN + 2 * col_w, list(filter(None, [
            bank,
            f"IBAN: {iban}" if iban else "",
            f"BIC: {bic}" if bic else "",
            f"Seite {self.page_no()}  ·  {self._druckdatum}",
        ])))

        self.set_text_color(0, 0, 0)

    # -------------------------------------------------------------------------
    # Gemeinsame Render-Methoden
    # -------------------------------------------------------------------------

    def _render_kopf(self) -> tuple[float, float]:
        """Absender-Kurzzeile, Empfänger-Adresse, Metadaten. Gibt (emp_bottom, meta_y) zurück."""
        r   = self._r
        unt = self._unt

        absender_kurz = "  ·  ".join(filter(None, [
            unt.get("firmenname"),
            f"{unt.get('strasse', '')} {unt.get('hausnummer', '')}".strip(),
            f"{unt.get('plz', '')} {unt.get('ort', '')}".strip(),
        ]))
        self.set_xy(L_MARGIN, ADRESS_Y)
        self.set_font("DejaVu", "", 6.5)
        self.set_text_color(*TEXT_GRAU)
        self.cell(90, 4.5, absender_kurz)
        self.set_draw_color(*GRAU_RAND)
        self.line(L_MARGIN, ADRESS_Y + 5, L_MARGIN + 90, ADRESS_Y + 5)

        partner_obj = r.kunde if r.typ == "ausgang" else r.lieferant
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

        meta_x   = L_MARGIN + 95
        meta_lbl = 42.0
        meta_val = PAGE_W - R_MARGIN - meta_x - meta_lbl
        meta_y   = ADRESS_Y

        def _meta(lbl: str, val: str, dim: bool = False):
            nonlocal meta_y
            self.set_xy(meta_x, meta_y)
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
            self.cell(meta_lbl, 5.5, lbl)
            self.set_font("DejaVu", "" if dim else "B", 8)
            self.set_text_color(*TEXT_GRAU if dim else TEXT_DUNKEL)
            self.cell(meta_val, 5.5, val)
            meta_y += 5.5

        _dok_meta  = getattr(r, "dokument_typ", "Rechnung") or "Rechnung"
        _ist_storno = getattr(r, "storniert", False) and _dok_meta == "Rechnung"
        if _ist_storno:
            _nr_label = "Stornorechnung-Nr."
        else:
            _nr_label = {
                "Angebot":      "Angebotsnr.",
                "Lieferschein": "Lieferscheinnr.",
                "Proforma":     "Proforma-Nr.",
                "Auftrag":      "Auftragsnr.",
                "Gutschrift":   "Gutschriftnr.",
            }.get(_dok_meta, "Rechnungsnummer" if r.typ == "ausgang" else "Eingangsrechn.-Nr.")
        _storno_nr = getattr(r, "storno_rechnungsnummer", None) if _ist_storno else None
        _meta(_nr_label, _storno_nr or r.rechnungsnummer or "—")
        if _ist_storno:
            storno_datum = getattr(r, "storno_datum", None)
            if storno_datum:
                _meta("Stornodatum", _iso_zu_de(str(storno_datum)))
            _meta("Originaldatum", _iso_zu_de(str(r.datum)), dim=True)
        else:
            _meta("Rechnungsdatum", _iso_zu_de(str(r.datum)))
        if r.leistung_von and r.leistung_bis:
            _meta("Leistungszeitraum", f"{_iso_zu_de(str(r.leistung_von))} – {_iso_zu_de(str(r.leistung_bis))}")
        elif r.leistung_von and str(r.leistung_von) != str(r.datum):
            _meta("Leistungsdatum", _iso_zu_de(str(r.leistung_von)))
        dokument_typ_meta = getattr(r, "dokument_typ", "Rechnung") or "Rechnung"
        if dokument_typ_meta == "Angebot":
            gueltig_bis = getattr(r, "gueltig_bis", None)
            if gueltig_bis:
                _meta("Gültig bis", _iso_zu_de(str(gueltig_bis)))
        elif r.faellig_am:
            _meta(self._faellig_label, _iso_zu_de(str(r.faellig_am)))
        la = getattr(r, "_lieferadresse", None)
        if la:
            strasse_nr = " ".join(filter(None, [la.strasse, la.hausnummer]))
            plz_ort = " ".join(filter(None, [la.plz, la.ort]))
            la_label = la.bezeichnung or "Lieferadresse"
            la_zeile = ", ".join(filter(None, [strasse_nr, plz_ort]))
            _meta(la_label, la_zeile)
        quell_angebot_nr = getattr(r, "_quell_angebot_nr", None)
        if quell_angebot_nr:
            _meta("Angebot", quell_angebot_nr, dim=True)
        quell_auftrag_nr = getattr(r, "_quell_auftrag_nr", None)
        if quell_auftrag_nr:
            _meta("Auftrag", quell_auftrag_nr, dim=True)

        return emp_bottom, meta_y

    def _render_titel(self):
        r = self._r
        dokument_typ = getattr(r, "dokument_typ", "Rechnung") or "Rechnung"
        ist_storno = getattr(r, "storniert", False) and dokument_typ == "Rechnung"
        if ist_storno:
            _snr = getattr(r, "storno_rechnungsnummer", None) or r.rechnungsnummer or ""
            titel = f"Stornorechnung {_snr}".strip()
        elif dokument_typ == "Gutschrift":
            titel = f"Gutschrift {r.rechnungsnummer or ''}".strip()
        elif dokument_typ == "Lieferschein":
            titel = f"Lieferschein {r.rechnungsnummer or ''}".strip()
        elif dokument_typ == "Angebot":
            titel = f"Angebot {r.rechnungsnummer or ''}".strip()
        elif dokument_typ == "Proforma":
            titel = f"Proforma-Rechnung {r.rechnungsnummer or ''}".strip()
        elif dokument_typ == "Auftrag":
            titel = f"Auftragsbestätigung {r.rechnungsnummer or ''}".strip()
        elif r.typ == "ausgang":
            titel = f"Rechnung {r.rechnungsnummer or ''}".strip()
        else:
            titel = f"Eingangsrechnung {r.rechnungsnummer or ''}".strip()
        self.set_font("DejaVu", "B", 16)
        self.set_text_color(*TEXT_DUNKEL)
        self.cell(0, 9, titel, new_x="LMARGIN", new_y="NEXT")

        if ist_storno:
            self.set_font("DejaVu", "", 9)
            self.set_text_color(*TEXT_GRAU)
            self.cell(0, 5,
                      f"Stornierung zu Rechnung {r.rechnungsnummer or '–'} vom {_iso_zu_de(str(r.datum))}",
                      new_x="LMARGIN", new_y="NEXT")
            storno_grund = getattr(r, "storno_grund", None)
            if storno_grund:
                self.ln(1)
                self.set_font("DejaVu", "", 8.5)
                self.multi_cell(0, 5,
                                f"Stornobegründung: {storno_grund}",
                                new_x="LMARGIN", new_y="NEXT")
                self.ln(1)
        elif dokument_typ == "Gutschrift":
            gutschrift_nr = getattr(r, "_gutschrift_original_nr", None)
            if gutschrift_nr:
                self.set_font("DejaVu", "", 9)
                self.set_text_color(*TEXT_GRAU)
                self.cell(0, 5, f"Gutschrift zu Rechnung {gutschrift_nr}", new_x="LMARGIN", new_y="NEXT")

        if self._ist_entwurf:
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
            self.cell(0, 5, "– Entwurf –", new_x="LMARGIN", new_y="NEXT")
        elif self._ist_kopie:
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
            self.cell(0, 5, "– Kopie –", new_x="LMARGIN", new_y="NEXT")

    def _render_nach_titel(self):
        """Hook zwischen Titel und Positionen: Einleitungstext, dann Abstand."""
        text = (getattr(self._r, "einleitungstext", None) or
                self._unt.get("einleitungstext") or "").strip()
        if text:
            self.set_font("DejaVu", "", 9)
            self.set_text_color(*TEXT_DUNKEL)
            self.set_x(L_MARGIN)
            self.multi_cell(NUTZ_W, 5, _md(text), markdown=True)
            self.ln(2)
        else:
            self.ln(4)

    def _render_positionen(self):
        """Positionstabelle. Muss self._sum_x, self._sum_lbl_w, self._sum_val_w setzen."""
        raise NotImplementedError

    def _render_summenblock(self):
        r   = self._r
        unt = self._unt
        sum_x   = self._sum_x
        lbl_w   = self._sum_lbl_w
        val_w   = self._sum_val_w

        def _sum_row(lbl: str, wert: str, bold: bool = False, trenn: bool = False, grau: bool = False):
            if trenn:
                self.set_draw_color(*GRAU_RAND)
                self.line(sum_x, self.get_y(), PAGE_W - R_MARGIN, self.get_y())
            self.set_x(sum_x)
            self.set_font("DejaVu", "B" if bold else "", 8.5 if bold else 8)
            self.set_text_color(*TEXT_GRAU)
            self.cell(lbl_w, 5.5, lbl, align="R")
            self.set_text_color(*TEXT_GRAU if grau else TEXT_DUNKEL)
            self.cell(val_w, 5.5, wert, align="R", new_x="LMARGIN", new_y="NEXT")

        ist_storno_sum = getattr(r, "storniert", False) and (getattr(r, "dokument_typ", "Rechnung") or "Rechnung") == "Rechnung"
        _s = Decimal("-1") if ist_storno_sum else Decimal("1")

        aufschluesselung = _ust_aufschluesselung(r.positionen)
        re_rabatt_proz   = getattr(r, "rabatt_prozent", Decimal("0")) or Decimal("0")
        re_rabatt_betrag = getattr(r, "rabatt_betrag", None)
        hat_rabatt = bool(re_rabatt_proz or re_rabatt_betrag)

        # Vor-Rabatt-Summen aus Positionen berechnen (Positions-Ebene bereits eingerechnet)
        if hat_rabatt:
            _Q4 = Decimal("0.0001")
            _Q2 = Decimal("0.01")
            pos_netto_sum = sum(
                (Decimal(str(pos.brutto)) - Decimal(str(pos.ust_betrag))) * Decimal(str(pos.menge))
                for pos in r.positionen
            ).quantize(_Q4)
            pos_ust_sum   = sum(
                Decimal(str(pos.ust_betrag)) * Decimal(str(pos.menge))
                for pos in r.positionen
            ).quantize(_Q4)
            pos_brutto_sum = (pos_netto_sum + pos_ust_sum).quantize(_Q4)
            if re_rabatt_betrag:
                rabatt_brutto = Decimal(str(re_rabatt_betrag)).quantize(_Q2)
                rabatt_netto  = (pos_netto_sum - r.netto_gesamt).quantize(_Q2)
                rabatt_lbl = "Abzug"
            else:
                rabatt_netto  = (pos_netto_sum  * re_rabatt_proz / 100).quantize(_Q2)
                rabatt_brutto = (pos_brutto_sum * re_rabatt_proz / 100).quantize(_Q2)
                rabatt_lbl = f"Rabatt {re_rabatt_proz:.4g} %"

        if self._ist_netto:
            if hat_rabatt:
                _sum_row("Zwischensumme", _fmt_euro(pos_netto_sum * _s))
                _sum_row(rabatt_lbl, f"- {_fmt_euro(rabatt_netto)}", grau=True)
            _sum_row("Nettobetrag", _fmt_euro(r.netto_gesamt * _s))
            if len(aufschluesselung) > 1:
                ust_lbl = "  |  ".join(
                    f"{satz} %: {_fmt_euro(ust_sum * _s)}" for satz, _, ust_sum in aufschluesselung
                )
                _sum_row(f"USt {ust_lbl}", _fmt_euro(r.ust_gesamt * _s))
            else:
                _sum_row("Umsatzsteuer", _fmt_euro(r.ust_gesamt * _s))
            _sum_row("Gesamtbetrag", _fmt_euro(r.brutto_gesamt * _s), bold=True, trenn=True)
        else:
            if hat_rabatt:
                _sum_row("Zwischensumme", _fmt_euro(pos_brutto_sum * _s))
                _sum_row(rabatt_lbl, f"- {_fmt_euro(rabatt_brutto)}", grau=True)
            _sum_row("Gesamtbetrag", _fmt_euro(r.brutto_gesamt * _s), bold=True, trenn=True)
            if not unt.get("ist_kleinunternehmer"):
                saetze_mit_ust = [(satz, ust_sum) for satz, _, ust_sum in aufschluesselung if satz > 0]
                if len(saetze_mit_ust) > 1:
                    ust_lbl = "  |  ".join(
                        f"{satz} %: {_fmt_euro(ust_sum * _s)}" for satz, ust_sum in saetze_mit_ust
                    )
                    _sum_row(f"enthaltene USt {ust_lbl}", _fmt_euro(r.ust_gesamt * _s), grau=True)
                elif saetze_mit_ust:
                    satz, _ = saetze_mit_ust[0]
                    _sum_row(f"enthaltene USt {satz} %", _fmt_euro(r.ust_gesamt * _s), grau=True)

    def _render_19_hinweis(self):
        unt = self._unt
        r = self._r
        self.set_font("DejaVu", "", 7.5)
        self.set_text_color(*TEXT_GRAU)
        if unt.get("ist_kleinunternehmer"):
            self.cell(0, 5, "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.",
                      new_x="LMARGIN", new_y="NEXT")
        # §25a-Hinweis: positionsweise, wenn mindestens eine Differenzbesteuerungs-Position vorhanden
        hat_diff = any(getattr(pos, "differenzbesteuerung", False) for pos in (r.positionen or []))
        if hat_diff:
            self.multi_cell(0, 4.5,
                            "Sonderregelung nach § 25a UStG: Für gekennzeichnete Positionen gilt die "
                            "Differenzbesteuerung (Gebrauchtgegenstände). "
                            "Der Umsatzsteuerbetrag wird nicht gesondert ausgewiesen.",
                            new_x="LMARGIN", new_y="NEXT")
        if unt.get("ist_kleinunternehmer") or hat_diff:
            self.ln(self._ln_nach_19)

    def _render_zahlungsblock(self):
        raise NotImplementedError

    def _render_notizen(self):
        r = self._r
        notizen = r.notizen or ""
        # Alten Autotext "Gutschrift zu ..." herausfiltern (wird im Titel bereits angezeigt)
        if getattr(r, "dokument_typ", "Rechnung") == "Gutschrift" and notizen.startswith("Gutschrift zu "):
            notizen = ""
        if notizen:
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
            self.multi_cell(0, 5, notizen)

    def render(self) -> bytes:
        self.add_page()
        emp_bottom, meta_y = self._render_kopf()
        body_y = max(emp_bottom, meta_y) + 10
        self.set_xy(L_MARGIN, body_y)
        self._render_titel()
        self._render_nach_titel()
        self._render_positionen()
        self.ln(self._ln_nach_positionen)
        _dt = getattr(self._r, "dokument_typ", "Rechnung") or "Rechnung"
        ist_lieferschein = _dt == "Lieferschein"
        ist_angebot      = _dt == "Angebot"
        ist_proforma     = _dt == "Proforma"
        ist_auftrag      = _dt == "Auftrag"
        ist_storno_rnd   = getattr(self._r, "storniert", False) and _dt == "Rechnung"
        if not ist_lieferschein:
            self._render_summenblock()
            self.ln(self._ln_nach_summen)
            self._render_19_hinweis()
            if not ist_angebot and not ist_auftrag and not ist_storno_rnd:
                self._render_zahlungsblock()
        self._render_notizen()
        if ist_lieferschein:
            self._render_empfangsbestaetigung()
        elif not ist_angebot and not ist_proforma and not ist_auftrag and not ist_storno_rnd:
            embed_unterschrift(self, self._unt, L_MARGIN)
        self.set_text_color(0, 0, 0)
        return bytes(self.output())

    def _render_empfangsbestaetigung(self):
        self.ln(12)
        self.set_draw_color(*GRAU_RAND)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(*TEXT_GRAU)
        col = (PAGE_W - L_MARGIN - R_MARGIN) / 2 - 5
        x1 = L_MARGIN
        x2 = L_MARGIN + col + 10
        y = self.get_y()
        self.set_xy(x1, y)
        self.cell(col, 5, "Datum, Ort")
        self.set_xy(x2, y)
        self.cell(col, 5, "Unterschrift Warenempfänger")
        self.ln(7)
        y2 = self.get_y()
        self.line(x1, y2, x1 + col, y2)
        self.line(x2, y2, x2 + col, y2)
