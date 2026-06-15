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
    _fmt_euro, _iso_zu_de, _adresszeilen, _md,
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

        einleitungstext = (getattr(r, "einleitungstext", None) or
                           self._unt.get("einleitungstext") or "").strip()

        self.ln(5)
        self.set_font("DejaVu", "", 9.5)
        self.set_text_color(*TEXT_DUNKEL)
        self.cell(0, 6, anrede, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        self.set_font("DejaVu", "", 9)
        if einleitungstext:
            self.set_text_color(*TEXT_DUNKEL)
            self.set_x(L_MARGIN)
            self.multi_cell(NUTZ_W, 5, _md(einleitungstext), markdown=True)
        else:
            self.set_text_color(*TEXT_GRAU)
            self.cell(0, 5.5,
                      "Vielen Dank für Dein Vertrauen. Wir stellen hiermit folgende Leistungen in Rechnung:",
                      new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    # -------------------------------------------------------------------------
    # Positionstabelle mit Pos./Datum-Spalten und grünem Design
    # -------------------------------------------------------------------------

    def _render_positionen(self):
        from decimal import Decimal
        r = self._r
        pos_datum_str = _iso_zu_de(str(r.leistung_von or r.datum))
        ist_lieferschein = getattr(r, "dokument_typ", "Rechnung") == "Lieferschein"

        if ist_lieferschein:
            col_w   = [12, 30, 103, 20, 10]
            headers = ["Pos.", "Datum", "Beschreibung", "Menge", "Einheit"]
            aligns  = ["R",   "L",     "L",             "R",     "L"]
        elif self._ist_netto:
            col_w   = [12, 30, 77, 22, 14, 20]
            headers = ["Pos.", "Datum", "Beschreibung", "Einzelpreis", "USt %", "Netto"]
            aligns  = ["R",   "L",     "L",             "R",           "R",     "R"]
        else:
            col_w   = [12, 30, 71, 20, 14, 28]
            headers = ["Pos.", "Datum", "Beschreibung", "Einzelpreis", "USt %", "Brutto"]
            aligns  = ["R",   "L",     "L",             "R",           "R",     "R"]

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
            ist_diff = getattr(pos, "differenzbesteuerung", False)
            ust_label = "§25a" if ist_diff else f"{int(pos.ust_satz)} %"
            pos_rabatt = getattr(pos, "rabatt_prozent", Decimal("0")) or Decimal("0")
            self.cell(col_w[0], 6.5, str(pos.position_nr), align="R")
            self.cell(col_w[1], 6.5, pos_datum_str, align="L")
            if ist_lieferschein:
                einheit = (pos.einheit or "").strip()
                self.cell(col_w[2], 6.5, pos.beschreibung[:80])
                self.cell(col_w[3], 6.5, f"{menge:g}", align="R")
                self.cell(col_w[4], 6.5, einheit, new_x="LMARGIN", new_y="NEXT")
            elif self._ist_netto:
                netto_ges_vor = float(str(pos.netto)) * menge
                netto_ges_eff = (float(str(pos.brutto)) - float(str(pos.ust_betrag))) * menge
                self.cell(col_w[2], 6.5, pos.beschreibung[:60])
                self.cell(col_w[3], 6.5, _fmt_euro(pos.netto), align="R")
                self.cell(col_w[4], 6.5, ust_label, align="R")
                self.cell(col_w[5], 6.5, _fmt_euro(netto_ges_vor), align="R",
                          new_x="LMARGIN", new_y="NEXT")
            else:
                ust_satz = float(str(pos.ust_satz))
                ep_brutto = float(str(pos.netto)) * (1 + ust_satz / 100)
                brutto_ges_vor = ep_brutto * menge
                brutto_ges_eff = float(str(pos.brutto)) * menge
                self.cell(col_w[2], 6.5, pos.beschreibung[:70])
                self.cell(col_w[3], 6.5, _fmt_euro(ep_brutto), align="R")
                self.cell(col_w[4], 6.5, ust_label, align="R")
                self.cell(col_w[5], 6.5, _fmt_euro(brutto_ges_vor), align="R",
                          new_x="LMARGIN", new_y="NEXT")
            # Rabatt-Unterzeile
            if pos_rabatt > 0 and not ist_lieferschein:
                self.set_font("DejaVu", "", 7.5)
                self.set_text_color(*TEXT_GRAU)
                pre_total_w = col_w[0] + col_w[1] + col_w[2] + col_w[3] + col_w[4]
                if self._ist_netto:
                    rabatt_abs = netto_ges_vor - netto_ges_eff
                else:
                    rabatt_abs = brutto_ges_vor - brutto_ges_eff
                self.set_x(L_MARGIN)
                self.cell(pre_total_w, 5, f"  {pos_rabatt:.4g} % Rabatt", align="L")
                self.cell(col_w[-1], 5, f"− {_fmt_euro(rabatt_abs)}", align="R",
                          new_x="LMARGIN", new_y="NEXT")
                self.set_font("DejaVu", "", 8.5)
                self.set_text_color(*TEXT_DUNKEL)

        tbl_bottom  = self.get_y()
        tbl_total_w = sum(col_w)
        self.set_draw_color(*GRUEN_RAND)
        self.rect(tbl_x, tbl_top, tbl_total_w, tbl_bottom - tbl_top)
        x = tbl_x
        for w in col_w[:-1]:
            x += w
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

        # Skonto-Werte vorab berechnen (für Tabellenzeile + QR-Code)
        from datetime import timedelta as _td
        from decimal import Decimal as _D
        _sk_proz = getattr(r, "skonto_prozent", None)
        _sk_tage = getattr(r, "skonto_tage",    None)
        if _sk_proz and _sk_tage and zahlungsstatus not in ("bezahlt", "teilweise"):
            sk_betrag = (r.brutto_gesamt * _D(str(_sk_proz)) / 100).quantize(_D("0.01"))
            sk_frist  = r.datum + _td(days=int(_sk_tage))
            sk_netto  = r.brutto_gesamt - sk_betrag
        else:
            sk_betrag = sk_frist = sk_netto = None

        kopf_titel = "Zahlung erhalten" if zahlungsstatus in ("bezahlt", "teilweise") and zahlungen else "Bank"
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
                "PayPal": "PayPal", "Bank": "Bank",
            }
            ist_gutschrift = getattr(r, "dokument_typ", "Rechnung") == "Gutschrift"
            for z in zahlungen:
                art_label = art_labels.get(
                    str(getattr(z, "zahlungsart", "")),
                    str(getattr(z, "zahlungsart", ""))
                )
                betrag_anzeige = abs(z.brutto_betrag)
                if ist_gutschrift:
                    prefix = (
                        "Betrag zurückerstattet am"
                        if zahlungsstatus == "bezahlt" and len(zahlungen) == 1
                        else "Teilbetrag zurückerstattet am"
                    )
                    _row(f"{prefix} {_iso_zu_de(str(z.datum))} per {art_label}", _fmt_euro(betrag_anzeige), bold_val=True)
                else:
                    prefix = (
                        "Dankend erhalten am"
                        if zahlungsstatus == "bezahlt" and len(zahlungen) == 1
                        else "Teilbetrag erhalten am"
                    )
                    _row(f"{prefix} {_iso_zu_de(str(z.datum))}", _fmt_euro(betrag_anzeige), bold_val=True)
        elif getattr(r, "dokument_typ", "Rechnung") == "Gutschrift":
            # Gutschrift (offen/Entwurf): nur Betrag, kein Zahlungsweg (noch unbekannt)
            _row("Gutschriftsbetrag", _fmt_euro(abs(r.brutto_gesamt)), bold_val=True)
        else:
            if empfaenger:
                _row("Empfänger", empfaenger, bold_val=True)
            _row("Rechnungsbetrag", _fmt_euro(r.brutto_gesamt), bold_val=True)
            _row("Zahlungsziel", faellig)
            if sk_betrag is not None:
                _row("Skonto", f"{_sk_proz:.0f}% bis {_iso_zu_de(str(sk_frist))}: {_fmt_euro(sk_netto)}")
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
            empf = unt.get("firmenname") or " ".join(
                p for p in [unt.get("vorname"), unt.get("nachname")] if p
            )
            qr_voll = epc_qr_bytes(iban, bic, empf, float(r.brutto_gesamt), r.rechnungsnummer or "")
            qr_sk   = (
                epc_qr_bytes(iban, bic, empf, float(sk_netto), r.rechnungsnummer or "")
                if sk_netto is not None else None
            )


            qr_y_top = block_top + 6.5 + 3

            if qr_sk and qr_voll:
                # Zwei QR-Codes (18 mm) nebeneinander im 40-mm-Streifen
                qr_sz  = 18
                qr_gap = 4   # 18 + 4 + 18 = 40 = qr_col_w exakt
                lbl_h  = 3.0
                min_bottom = qr_y_top + qr_sz + 1 + lbl_h + lbl_h + 3
                if block_bottom < min_bottom:
                    block_bottom = min_bottom
                    self.set_y(block_bottom)

                qr_x_sk = x_start + box_w
                qr_x_vo = x_start + box_w + qr_sz + qr_gap
                self.image(BytesIO(qr_sk),   x=qr_x_sk, y=qr_y_top, w=qr_sz, h=qr_sz)
                self.image(BytesIO(qr_voll), x=qr_x_vo, y=qr_y_top, w=qr_sz, h=qr_sz)

                lbl_y = qr_y_top + qr_sz + 1
                self.set_font("DejaVu", "B", 5)
                self.set_text_color(*TEXT_GRAU)
                self.set_xy(qr_x_sk, lbl_y)
                self.cell(qr_sz, lbl_h, "Skonto", align="C", new_x="LMARGIN", new_y="NEXT")
                self.set_font("DejaVu", "", 5)
                self.set_xy(qr_x_sk, lbl_y + lbl_h)
                self.cell(qr_sz, lbl_h, f"bis {_iso_zu_de(str(sk_frist))}: {_fmt_euro(sk_netto)}", align="C")

                self.set_font("DejaVu", "B", 5)
                self.set_xy(qr_x_vo, lbl_y)
                self.cell(qr_sz, lbl_h, "Ohne Skonto", align="C", new_x="LMARGIN", new_y="NEXT")
                self.set_font("DejaVu", "", 5)
                self.set_xy(qr_x_vo, lbl_y + lbl_h)
                self.cell(qr_sz, lbl_h, _fmt_euro(r.brutto_gesamt), align="C")

                self.set_font("DejaVu", "", 8)
                self.set_text_color(*TEXT_DUNKEL)

            elif qr_voll:
                # Einzelner QR-Code (kein Skonto)
                qr_size    = 25
                min_bottom = qr_y_top + qr_size + 5 + 3
                if block_bottom < min_bottom:
                    block_bottom = min_bottom
                    self.set_y(block_bottom)

                qr_x = x_start + box_w + (qr_col_w - qr_size) / 2
                self.image(BytesIO(qr_voll), x=qr_x, y=qr_y_top, w=qr_size, h=qr_size)
                self.set_font("DejaVu", "", 6)
                self.set_text_color(*TEXT_GRAU)
                self.set_xy(x_start + box_w, qr_y_top + qr_size + 1)
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
