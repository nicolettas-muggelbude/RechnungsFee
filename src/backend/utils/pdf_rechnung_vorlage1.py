"""
Rechnungs-PDF Vorlage 1 – Grün / Kleinunternehmer mit Zahlungsziel.

Community-Vorlage (Issue #33, Einreicher: trinity2701).

Layout:
  Spalten: Pos. | Datum | Beschreibung | Einzelpreis | USt % | Netto/Saldo
  Anrede + Einleitung vor der Tabelle.
  Bezahldaten-Block im Tabellenstil unterhalb der Summen.
"""

from io import BytesIO

from utils.pdf_rechnung_base import (
    RechnungPDFBase,
    _fmt_euro, _iso_zu_de, _adresszeilen,
    TEXT_GRAU, TEXT_DUNKEL,
    L_MARGIN, R_MARGIN, PAGE_W, NUTZ_W, FOOTER_H,
)
from utils.pdf_shared import epc_qr_bytes

# Vorlage-Farben: Grüntöne passend zu #eff4ef
GRUEN_HELL = (239, 244, 239)
GRUEN_RAND = (180, 210, 180)
GRAU_RAND  = (210, 213, 220)


class RechnungPDFVorlage1(RechnungPDFBase):
    """Vorlage 1: Grünes Design, Pos./Datum-Spalten, Bezahldaten-Block."""

    _faellig_label      = "Zahlungsziel"
    _ln_nach_positionen = 6
    _ln_nach_summen     = 4
    _ln_nach_19         = 3

    def __init__(self, unternehmen: dict, rechnung,
                 ist_kopie: bool = False, ist_entwurf: bool = False, ist_netto: bool = False):
        super().__init__(unternehmen, rechnung,
                         ist_kopie=ist_kopie, ist_entwurf=ist_entwurf, ist_netto=ist_netto)

    # -------------------------------------------------------------------------
    # Anrede zwischen Titel und Tabelle
    # -------------------------------------------------------------------------

    def _render_nach_titel(self):
        r = self._r
        partner_obj = r.kunde if r.typ == "ausgang" else r.lieferant
        vorname_kunde = getattr(partner_obj, "vorname", None) or ""
        anrede = f"Hallo {vorname_kunde}," if vorname_kunde else "Hallo,"

        self.ln(5)
        self.set_font("DejaVu", "", 9.5)
        self.set_text_color(*TEXT_DUNKEL)
        self.cell(0, 6, anrede, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        self.set_font("DejaVu", "", 9)
        self.set_text_color(*TEXT_GRAU)
        self.cell(0, 5.5,
                  "Vielen Dank für Dein Vertrauen. Wir stellen hiermit folgende Leistungen in Rechnung:",
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    # -------------------------------------------------------------------------
    # Positionstabelle mit Pos./Datum-Spalten und grünem Design
    # -------------------------------------------------------------------------

    def _render_positionen(self):
        r = self._r
        pos_datum_str = _iso_zu_de(str(r.leistung_von or r.datum))

        if self._ist_netto:
            col_w   = [12, 30, 77, 22, 14, 20]
            headers = ["Pos.", "Datum", "Beschreibung", "Einzelpreis", "USt %", "Netto"]
            aligns  = ["R",   "L",     "L",             "R",           "R",     "R"]
        else:
            col_w   = [12, 30, 91, 14, 28]
            headers = ["Pos.", "Datum", "Beschreibung", "USt %", "Saldo"]
            aligns  = ["R",   "L",     "L",             "R",     "R"]

        tbl_x   = L_MARGIN
        tbl_top = self.get_y()

        self.set_font("DejaVu", "B", 8)
        self.set_fill_color(*GRUEN_HELL)
        self.set_draw_color(*GRUEN_RAND)
        self.set_text_color(*TEXT_DUNKEL)
        for i, h in enumerate(headers):
            self.cell(col_w[i], 6.5, h, border="B", fill=True, align=aligns[i])
        self.ln()

        self.set_font("DejaVu", "", 8.5)
        self.set_text_color(*TEXT_DUNKEL)
        for pos in r.positionen:
            menge = float(str(pos.menge))
            self.cell(col_w[0], 6.5, str(pos.position_nr), align="R")
            self.cell(col_w[1], 6.5, pos_datum_str, align="L")
            if self._ist_netto:
                self.cell(col_w[2], 6.5, pos.beschreibung[:60])
                self.cell(col_w[3], 6.5, _fmt_euro(pos.netto),                   align="R")
                self.cell(col_w[4], 6.5, f"{int(pos.ust_satz)} %",               align="R")
                self.cell(col_w[5], 6.5, _fmt_euro(float(str(pos.netto)) * menge), align="R",
                          new_x="LMARGIN", new_y="NEXT")
            else:
                self.cell(col_w[2], 6.5, pos.beschreibung[:70])
                self.cell(col_w[3], 6.5, f"{int(pos.ust_satz)} %", align="R")
                self.cell(col_w[4], 6.5, _fmt_euro(pos.brutto), align="R",
                          new_x="LMARGIN", new_y="NEXT")

        tbl_bottom  = self.get_y()
        tbl_total_w = sum(col_w)
        self.set_draw_color(*GRUEN_RAND)
        self.rect(tbl_x, tbl_top, tbl_total_w, tbl_bottom - tbl_top)
        x = tbl_x + col_w[0]
        self.line(x, tbl_top, x, tbl_bottom); x += col_w[1]
        self.line(x, tbl_top, x, tbl_bottom); x += col_w[2]
        self.line(x, tbl_top, x, tbl_bottom); x += col_w[3]
        self.line(x, tbl_top, x, tbl_bottom)
        if self._ist_netto:
            x += col_w[4]
            self.line(x, tbl_top, x, tbl_bottom)

        # Summenblock-Geometrie: mittig rechts
        self._sum_x     = L_MARGIN + NUTZ_W * 0.5
        self._sum_lbl_w = NUTZ_W * 0.3
        self._sum_val_w = NUTZ_W * 0.2

    # -------------------------------------------------------------------------
    # Bezahldaten-Block im Tabellenstil
    # -------------------------------------------------------------------------

    def _render_zahlungsblock(self):
        self._bezahldaten_block(self._r, self._unt)

    def _render_notizen(self):
        r = self._r
        if r.notizen:
            self.ln(4)
            super()._render_notizen()

    def _bezahldaten_block(self, r, unt: dict):
        iban    = unt.get("iban") or ""
        bic     = unt.get("bic") or ""
        bank    = unt.get("bank_name") or ""
        faellig = _iso_zu_de(str(r.faellig_am)) if r.faellig_am else "nach Erhalt"

        empfaenger = unt.get("firmenname") or " ".join(filter(None, [
            unt.get("vorname"), unt.get("nachname")
        ]))

        zahlungsstatus = str(getattr(r, "zahlungsstatus", "offen") or "offen")
        zahlungen = [
            z for z in (getattr(r, "journaleintraege", None) or [])
            if not getattr(z, "storniert", False)
        ]

        lbl_w = 55.0
        val_w = 80.0
        lh    = 6.5
        box_w = lbl_w + val_w

        qr_aktiv = (
            unt.get("qr_zahlung_aktiv", False)
            and iban
            and r.typ == "ausgang"
            and zahlungsstatus not in ("bezahlt", "teilweise")
        )
        qr_col_w = NUTZ_W - box_w  # 40 mm

        x_start   = float(L_MARGIN) if qr_aktiv else L_MARGIN + (NUTZ_W - box_w) / 2
        block_top = self.get_y()

        kopf_titel = "Zahlung erhalten" if zahlungsstatus in ("bezahlt", "teilweise") and zahlungen else "Überweisung"
        kopf_w = box_w + qr_col_w if qr_aktiv else box_w
        self.set_font("DejaVu", "B", 8)
        self.set_fill_color(*GRUEN_HELL)
        self.set_draw_color(*GRUEN_RAND)
        self.set_text_color(*TEXT_DUNKEL)
        self.set_xy(x_start, block_top)
        self.cell(kopf_w, 6.5, kopf_titel, border="B", fill=True, align="L",
                  new_x="LMARGIN", new_y="NEXT")

        def _row(lbl: str, val: str, bold_val: bool = False):
            y = self.get_y()
            self.set_draw_color(*GRUEN_RAND)
            self.line(x_start, y, x_start + box_w, y)
            self.set_xy(x_start, y)
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*TEXT_GRAU)
            self.cell(lbl_w, lh, lbl, align="L")
            self.set_font("DejaVu", "B" if bold_val else "", 8)
            self.set_text_color(*TEXT_DUNKEL)
            self.cell(val_w, lh, val, align="L", new_x="LMARGIN", new_y="NEXT")

        if zahlungsstatus in ("bezahlt", "teilweise") and zahlungen:
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
            if empfaenger:
                _row("Empfänger", empfaenger, bold_val=True)
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

        block_bottom = self.get_y()

        if qr_aktiv:
            qr_size    = 25
            label_h    = 5
            min_bottom = block_top + 6.5 + 3 + qr_size + label_h + 3
            if block_bottom < min_bottom:
                block_bottom = min_bottom
                self.set_y(block_bottom)

            empf = unt.get("firmenname") or " ".join(
                p for p in [unt.get("vorname"), unt.get("nachname")] if p
            )
            qr_data = epc_qr_bytes(iban, bic, empf, float(r.brutto_gesamt), r.rechnungsnummer or "")
            if qr_data:
                qr_x = x_start + box_w + (qr_col_w - qr_size) / 2
                qr_y = block_top + 6.5 + 3
                self.image(BytesIO(qr_data), x=qr_x, y=qr_y, w=qr_size, h=qr_size)
                self.set_font("DejaVu", "", 6)
                self.set_text_color(*TEXT_GRAU)
                self.set_xy(x_start + box_w, qr_y + qr_size + 1)
                self.cell(qr_col_w, 4, "Per Banking-App zahlen", align="C")
                self.set_font("DejaVu", "", 8)
                self.set_text_color(*TEXT_DUNKEL)

            total_w = box_w + qr_col_w
        else:
            total_w = box_w

        self.set_draw_color(*GRUEN_RAND)
        self.rect(x_start, block_top, total_w, block_bottom - block_top)
        self.line(x_start + lbl_w, block_top, x_start + lbl_w, block_bottom)
        if qr_aktiv:
            self.line(x_start + box_w, block_top, x_start + box_w, block_bottom)

        self.set_y(block_bottom)


# ---------------------------------------------------------------------------
# Öffentliche Funktion
# ---------------------------------------------------------------------------

def generate_rechnung_pdf_vorlage1(
    rechnung, unternehmen: dict,
    ist_kopie: bool = False,
    ist_entwurf: bool = False,
    ist_netto: bool = False,
) -> bytes:
    pdf = RechnungPDFVorlage1(unternehmen, rechnung,
                               ist_kopie=ist_kopie, ist_entwurf=ist_entwurf, ist_netto=ist_netto)
    return pdf.render()
