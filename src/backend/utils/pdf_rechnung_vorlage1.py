"""
PDF-Vorlage 1 – Rechnungsvorlage Kleinunternehmer mit Zahlungsziel.

Community-Vorlage (Issue #33, Einreicher: trinity2701).

Layout:
  ┌─────────────────────────────────────────────────────────┐
  │ Logo (links)       │  Firmenname + Adresse (rechts)     │ 10–43mm
  ├─────────────────────────────────────────────────────────┤  43mm
  │ Absender-Kurzzeile │  Rechnungsnr / Datum / Zahlungsziel│ 45mm
  │ Empfänger-Adresse  │                                     │ 51–90mm
  ├─────────────────────────────────────────────────────────┤
  │ Rechnung RE-XXXX                                         │
  │ Positionstabelle: Datum | Beschreibung | Saldo           │
  │ Bezahldaten-Block (Tabellenstil): Betrag / IBAN / Ziel   │
  ├─────────────────────────────────────────────────────────┤
  │ Vollst. Firmendaten (Tel, E-Mail, Web, IBAN, HRB …)     │ Footer
  └─────────────────────────────────────────────────────────┘

Besonderheiten:
- Kein farbiger Tabellenhintergrund (nur Linie)
- Datum-Spalte: Leistungsdatum der Rechnung (gleiches Datum für alle Positionen)
- Saldo-Spalte: Bruttobetrag der Position (Kleinunternehmer → kein USt-Ausweis)
- Bezahldaten-Block unter den Positionen im Tabellenstil
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from fpdf import FPDF

# Wiederverwendung aus dem Standard-Template
from utils.pdf_rechnung import (
    _find_dejavu_dir,
    _fmt_euro,
    _iso_zu_de,
    _person_bezeichnung,
    _logo_abmessungen,
    _adresszeilen,
    GRAU_HELL,
    GRAU_RAND,
    TEXT_GRAU,
    TEXT_DUNKEL,
    L_MARGIN,
    R_MARGIN,
    PAGE_W,
    NUTZ_W,
    ADRESS_Y,
    HEADER_LINE_Y,
    BLOCK_X,
    BLOCK_W,
    FOOTER_H,
)


class RechnungPDFVorlage1(FPDF):
    """Vorlage 1: Kleinunternehmer mit Zahlungsziel – Tabelle Datum/Beschreibung/Saldo."""

    def __init__(self, unternehmen: dict, rechnung, ist_kopie: bool = False):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(L_MARGIN, 10, R_MARGIN)
        self.set_auto_page_break(auto=True, margin=FOOTER_H + 4)
        dv_dir = _find_dejavu_dir()
        self.add_font("DejaVu", style="",  fname=str(dv_dir / "DejaVuSans.ttf"))
        self.add_font("DejaVu", style="B", fname=str(dv_dir / "DejaVuSans-Bold.ttf"))
        self._unt        = unternehmen
        self._r          = rechnung
        self._ist_kopie  = ist_kopie
        self._druckdatum = datetime.now().strftime("%d.%m.%Y")

    # -------------------------------------------------------------------------
    # Header (identisch mit Standard-Template)
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

    # -------------------------------------------------------------------------
    # Footer (identisch mit Standard-Template)
    # -------------------------------------------------------------------------

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
        hr_nr      = unt.get("handelsregister_nr") or ""
        hr_ger     = unt.get("handelsregister_gericht") or ""
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
        steuer    = f"USt-ID: {ust_id}" if ust_id else (f"StNr: {steuernr}" if steuernr else "")
        hr_zeile  = (f"HRB {hr_nr}" + (f", {hr_ger}" if hr_ger else "")) if hr_nr else ""
        kammer    = unt.get("kammer_mitgliedschaft") or ""
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
    # Inhalt
    # -------------------------------------------------------------------------

    def render(self) -> bytes:
        r   = self._r
        unt = self._unt

        self.add_page()

        # --- Absender-Kurzzeile ---
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

        # --- Empfänger-Adressblock ---
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

        # --- Rechnungsmetadaten (rechts) ---
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
            _meta("Zahlungsziel", _iso_zu_de(str(r.faellig_am)))

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

        if self._ist_kopie:
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
            self.cell(0, 5, "– Kopie –", new_x="LMARGIN", new_y="NEXT")

        self.ln(4)

        # --- Positionstabelle: Datum | Beschreibung | Saldo ---
        # Datum-Spalte: Leistungsdatum der Rechnung (ein Datum für alle Positionen,
        # da Rechnungsposition kein eigenes Datum-Feld hat)
        pos_datum_str = _iso_zu_de(str(r.leistungsdatum or r.datum))

        col_w   = [35, 112, 28]
        headers = ["Datum", "Beschreibung", "Saldo"]
        aligns  = ["L",    "L",             "R"]

        self.set_font("DejaVu", "B", 8)
        self.set_draw_color(*GRAU_RAND)
        self.set_text_color(*TEXT_GRAU)
        # Tabellenheader: nur Unterstrich, kein Hintergrund (lt. Vorlage)
        for i, h in enumerate(headers):
            self.cell(col_w[i], 6.5, h, border="B", align=aligns[i])
        self.ln()

        self.set_font("DejaVu", "", 8.5)
        self.set_text_color(*TEXT_DUNKEL)
        for pos in r.positionen:
            self.cell(col_w[0], 6.5, pos_datum_str, align="L")
            self.cell(col_w[1], 6.5, pos.beschreibung[:90])
            self.cell(col_w[2], 6.5, _fmt_euro(pos.brutto), align="R",
                      new_x="LMARGIN", new_y="NEXT")

        self.ln(6)

        # --- §19-Hinweis ---
        if unt.get("ist_kleinunternehmer"):
            self.set_font("DejaVu", "", 7.5)
            self.set_text_color(*TEXT_GRAU)
            self.cell(0, 5,
                      "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.",
                      new_x="LMARGIN", new_y="NEXT")
            self.ln(3)

        # --- Bezahldaten-Block im Tabellenstil ---
        self._bezahldaten_block(r, unt)

        # --- Notizen ---
        if r.notizen:
            self.ln(4)
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
            self.multi_cell(0, 5, r.notizen)

        self.set_text_color(0, 0, 0)
        return bytes(self.output())

    def _bezahldaten_block(self, r, unt: dict):
        """Bezahldaten-Zusammenfassung unterhalb der Positionen im Tabellenstil."""
        iban   = unt.get("iban") or ""
        bic    = unt.get("bic") or ""
        bank   = unt.get("bank_name") or ""
        faellig = _iso_zu_de(str(r.faellig_am)) if r.faellig_am else "nach Erhalt"

        zahlungsstatus = str(getattr(r, "zahlungsstatus", "offen") or "offen")
        zahlungen = [
            z for z in (getattr(r, "kassenbucheintraege", None) or [])
            if not getattr(z, "storniert", False)
        ]

        lbl_w = 55.0
        val_w = 80.0
        lh    = 6.5
        box_w = lbl_w + val_w

        # Hintergrundblock (helles Grau) für den gesamten Bezahldaten-Block
        block_y = self.get_y()

        def _row(lbl: str, val: str, bold_val: bool = False):
            y = self.get_y()
            # Trennlinie oben
            self.set_draw_color(*GRAU_RAND)
            self.line(L_MARGIN, y, L_MARGIN + box_w, y)
            self.set_xy(L_MARGIN, y)
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
            self.cell(lbl_w, lh, lbl, align="L")
            self.set_font("DejaVu", "B" if bold_val else "", 8)
            self.set_text_color(*TEXT_DUNKEL)
            self.cell(val_w, lh, val, align="L", new_x="LMARGIN", new_y="NEXT")

        if zahlungsstatus in ("bezahlt", "teilweise") and zahlungen:
            # Bezahlte Rechnung: Zahlungsbestätigung im Tabellenstil
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
                    "Dankend erhalten am"
                    if zahlungsstatus == "bezahlt" and len(zahlungen) == 1
                    else "Teilbetrag erhalten am"
                )
                _row(f"{prefix} {_iso_zu_de(str(z.datum))}", _fmt_euro(z.brutto_betrag), bold_val=True)
        else:
            # Offene Rechnung: Zahlungsdaten für Überweisung
            _row("Rechnungsbetrag", _fmt_euro(r.brutto_gesamt), bold_val=True)
            _row("Zahlungsziel", faellig)
            if r.rechnungsnummer:
                _row("Verwendungszweck", r.rechnungsnummer or "")
            if bank:
                _row("Bank", bank)
            if iban:
                _row("IBAN", iban)
            if bic:
                _row("BIC", bic)

        # Abschlusslinie des Blocks
        self.set_draw_color(*GRAU_RAND)
        self.line(L_MARGIN, self.get_y(), L_MARGIN + box_w, self.get_y())


# ---------------------------------------------------------------------------
# Öffentliche Funktion
# ---------------------------------------------------------------------------

def generate_rechnung_pdf_vorlage1(rechnung, unternehmen: dict, ist_kopie: bool = False) -> bytes:
    """
    Erzeugt ein PDF für die übergebene Rechnung nach Vorlage 1
    (Kleinunternehmer mit Zahlungsziel, Issue #33).

    :param rechnung:    SQLAlchemy-Rechnung-Objekt (mit .positionen, .kunde, .lieferant)
    :param unternehmen: dict mit allen Firmendaten
    :param ist_kopie:   True → dezenter „– Kopie –"-Hinweis unter dem Titel
    """
    pdf = RechnungPDFVorlage1(unternehmen, rechnung, ist_kopie=ist_kopie)
    return pdf.render()
