"""
Rechnungs-PDF Vorlage 0 – Standard (DIN 5008 Form B).

Layout:
  Spalten: Beschreibung | Menge | Einheit | Einzelpreis | USt % | Netto/Brutto
  Zahlungshinweis als Fließtext, optionaler EPC-QR-Code.
"""

from decimal import Decimal
from io import BytesIO

from utils.pdf_rechnung_base import (
    RechnungPDFBase,
    _fmt_euro, _iso_zu_de, _ust_aufschluesselung,
    GRAU_HELL, GRAU_RAND, TEXT_GRAU, TEXT_DUNKEL,
    L_MARGIN, R_MARGIN, PAGE_W, NUTZ_W,
    ADRESS_Y, HEADER_LINE_Y, BLOCK_X, BLOCK_W, FOOTER_H,
    _find_dejavu_dir, _person_bezeichnung, _logo_abmessungen, _adresszeilen,
)
from utils.pdf_shared import epc_qr_bytes


class RechnungPDF(RechnungPDFBase):
    """Vorlage 0: DIN 5008, graue Tabelle, Zahlungshinweis als Fließtext."""

    def _render_positionen(self):
        r = self._r

        if self._ist_netto:
            col_w   = [82, 16, 17, 27, 14, 24]
            headers = ["Beschreibung", "Menge", "Einheit", "Einzelpreis", "USt %", "Netto"]
            aligns  = ["L",            "R",     "L",       "R",           "R",     "R"]
        else:
            col_w   = [82, 16, 17, 16, 49]
            headers = ["Beschreibung", "Menge", "Einheit", "USt %", "Brutto"]
            aligns  = ["L",            "R",     "L",       "R",     "R"]

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
            ist_diff = getattr(pos, "differenzbesteuerung", False)
            ust_label = "§25a" if ist_diff else f"{int(pos.ust_satz)} %"
            row_y = self.get_y()
            self.set_x(L_MARGIN + col_w[0])
            self.cell(col_w[1], 6, menge_str, align="R")
            self.cell(col_w[2], 6, pos.einheit[:12])
            if self._ist_netto:
                self.cell(col_w[3], 6, _fmt_euro(pos.netto),             align="R")
                self.cell(col_w[4], 6, ust_label,                        align="R")
                self.cell(col_w[5], 6, _fmt_euro(float(str(pos.netto)) * menge), align="R")
            else:
                self.cell(col_w[3], 6, ust_label,              align="R")
                self.cell(col_w[4], 6, _fmt_euro(pos.brutto),  align="R")
            self.set_xy(L_MARGIN, row_y)
            self.multi_cell(col_w[0], 6, pos.beschreibung or "",
                            new_x="LMARGIN", new_y="NEXT")

        # Summenblock-Geometrie: rechtsbündig ab Ende der ersten drei Spalten
        self._sum_x     = L_MARGIN + col_w[0] + col_w[1] + col_w[2]
        self._sum_lbl_w = 41.0
        self._sum_val_w = 24.0

    def _render_zahlungsblock(self):
        r   = self._r
        unt = self._unt

        zahlungsstatus = str(getattr(r, "zahlungsstatus", "offen") or "offen")
        zahlungen = [
            z for z in (getattr(r, "journaleintraege", None) or [])
            if not getattr(z, "storniert", False)
        ]

        self.set_font("DejaVu", "", 8)
        self.set_text_color(*TEXT_GRAU)

        if zahlungsstatus in ("bezahlt", "teilweise") and zahlungen:
            art_labels = {
                "Bar": "Barzahlung", "Karte": "Kartenzahlung",
                "PayPal": "PayPal", "Bank": "Überweisung",
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
                        "Betrag wurde zurückerstattet"
                        if zahlungsstatus == "bezahlt" and len(zahlungen) == 1
                        else "Teilbetrag zurückerstattet"
                    )
                else:
                    prefix = (
                        "Rechnungsbetrag bereits dankend erhalten"
                        if zahlungsstatus == "bezahlt" and len(zahlungen) == 1
                        else "Teilbetrag dankend erhalten"
                    )
                zeile = (
                    f"{prefix} am {_iso_zu_de(str(z.datum))} "
                    f"per {art_label}: {_fmt_euro(betrag_anzeige)}"
                )
                self.cell(0, 5, zeile, new_x="LMARGIN", new_y="NEXT")
        else:
            ist_gutschrift_offen = getattr(r, "dokument_typ", "Rechnung") == "Gutschrift"

            # Gutschrift (offen/Entwurf): Rückerstattungshinweis statt Zahlungsaufforderung
            if ist_gutschrift_offen:
                betrag_gs = abs(r.brutto_gesamt)
                self.set_font("DejaVu", "", 8)
                self.set_text_color(*TEXT_GRAU)
                self.cell(0, 5, f"Wir erstatten Ihnen den Betrag von {_fmt_euro(betrag_gs)}.", new_x="LMARGIN", new_y="NEXT")
                return

            # Skonto-Hinweis (nur bei offener Ausgangsrechnung mit Skonto-Bedingungen)
            if (r.typ == "ausgang"
                    and getattr(r, "skonto_prozent", None)
                    and getattr(r, "skonto_tage", None)):
                from datetime import timedelta
                skonto_frist = r.datum + timedelta(days=int(r.skonto_tage))
                skonto_betrag = (r.brutto_gesamt * Decimal(str(r.skonto_prozent)) / 100).quantize(Decimal("0.01"))
                skonto_text = (
                    f"{r.skonto_prozent:.0f}% Skonto bei Zahlung bis {_iso_zu_de(str(skonto_frist))}: "
                    f"{_fmt_euro(r.brutto_gesamt - skonto_betrag)}"
                )
                self.set_font("DejaVu", "", 8)
                self.set_text_color(*TEXT_GRAU)
                self.cell(0, 5, skonto_text, new_x="LMARGIN", new_y="NEXT")

            if unt.get("zahlungshinweis_aktiv", True):
                iban = unt.get("iban") or ""
                if iban and r.typ == "ausgang":
                    bic    = unt.get("bic") or ""
                    faellig = _iso_zu_de(str(r.faellig_am)) if r.faellig_am else "sofort"
                    hinweis = (
                        f"Bitte überweisen Sie {_fmt_euro(r.brutto_gesamt)} bis {faellig} "
                        f"unter Angabe der Rechnungsnummer {r.rechnungsnummer or ''} "
                        f"auf IBAN {iban}"
                    )
                    if bic:
                        hinweis += f"  ·  BIC {bic}"
                    hinweis += "."

                    qr_aktiv = unt.get("qr_zahlung_aktiv", False)
                    if qr_aktiv:
                        empf = unt.get("firmenname") or " ".join(
                            p for p in [unt.get("vorname"), unt.get("nachname")] if p
                        )
                        # Skonto-QR bestimmen
                        sk_proz = getattr(r, "skonto_prozent", None)
                        sk_tage = getattr(r, "skonto_tage",    None)
                        if sk_proz and sk_tage:
                            from datetime import timedelta as _td
                            sk_betrag = (r.brutto_gesamt * Decimal(str(sk_proz)) / 100).quantize(Decimal("0.01"))
                            sk_netto  = r.brutto_gesamt - sk_betrag
                            sk_frist  = r.datum + _td(days=int(sk_tage))
                            qr_sk = epc_qr_bytes(iban, bic, empf, float(sk_netto), r.rechnungsnummer or "")
                        else:
                            qr_sk = sk_netto = sk_frist = None

                        qr_voll = epc_qr_bytes(iban, bic, empf, float(r.brutto_gesamt), r.rechnungsnummer or "")

                        if qr_sk and qr_voll:
                            # Zwei QR-Codes: Text links, Skonto-QR + Voll-QR rechts
                            qr_sz   = 18
                            qr_gap  = 4   # 18 + 4 + 18 = 40 mm
                            lbl_h   = 3.0
                            col_w   = qr_sz + qr_gap + qr_sz  # 40 mm
                            text_w  = NUTZ_W - col_w - 4
                            y_start = self.get_y()
                            qr_x_sk = L_MARGIN + text_w + 4
                            qr_x_vo = qr_x_sk + qr_sz + qr_gap
                            self.multi_cell(text_w, 5, hinweis)
                            self.image(BytesIO(qr_sk),   x=qr_x_sk, y=y_start, w=qr_sz, h=qr_sz)
                            self.image(BytesIO(qr_voll), x=qr_x_vo, y=y_start, w=qr_sz, h=qr_sz)
                            lbl_y = y_start + qr_sz + 1
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
                            self.set_text_color(*TEXT_GRAU)
                            if self.get_y() < y_start + qr_sz + lbl_h + lbl_h + 2:
                                self.set_y(y_start + qr_sz + lbl_h + lbl_h + 2)
                        elif qr_voll:
                            # Einzelner QR-Code (kein Skonto)
                            qr_size = 25
                            gap     = 4
                            text_w  = NUTZ_W - qr_size - gap
                            y_start = self.get_y()
                            qr_x    = L_MARGIN + text_w + gap
                            self.multi_cell(text_w, 5, hinweis)
                            self.image(BytesIO(qr_voll), x=qr_x, y=y_start, w=qr_size, h=qr_size)
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


# ---------------------------------------------------------------------------
# Öffentliche Funktion
# ---------------------------------------------------------------------------

def generate_rechnung_pdf(
    rechnung, unternehmen: dict,
    ist_kopie: bool = False,
    ist_entwurf: bool = False,
    mit_output_intent: bool = False,
    ist_netto: bool = True,
) -> bytes:
    pdf = RechnungPDF(unternehmen, rechnung,
                      ist_kopie=ist_kopie, ist_entwurf=ist_entwurf, ist_netto=ist_netto)
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
