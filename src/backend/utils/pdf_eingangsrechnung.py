"""
Issue #591: Erfassungsblatt für Eingangsrechnungen (auch Lieferantengutschriften) ohne
angehängten Originalbeleg.

Eine Eingangsrechnung ist das Dokument des Lieferanten - die Rechnungsvorlagen (Absender =
eigene Firma, Bankdaten/QR-Code, Versand) passen dafür nicht. Dieses Blatt hält nur fest, was
erfasst wurde: Rechnungssteller (Lieferant), Empfänger (eigene Firma), Nummern, Datum,
Positionen, Summen und den Zahlungsstand. Kein Original, keine Archivierung, kein Versand.
Ist ein Originalbeleg angehängt, zeigt die App diesen statt des Blatts.
"""
from datetime import date, datetime
from decimal import Decimal

from fpdf import FPDF

from utils.pdf_rechnung_base import (
    _adresszeilen, _find_dejavu_dir, _fmt_euro, _fmt_ust_satz, _fmt_zahl,
)

L = 20
BREITE = 170
GRAU = (100, 116, 139)
DUNKEL = (30, 41, 59)
LINIE = (203, 213, 225)


class _Blatt(FPDF):
    def footer(self):
        self.set_y(-14)
        self.set_font("DejaVu", "", 7)
        self.set_text_color(*GRAU)
        self.cell(0, 4, f"Internes Erfassungsblatt aus RechnungsFee – kein Originalbeleg  ·  "
                        f"erstellt am {date.today().strftime('%d.%m.%Y')}  ·  Seite {self.page_no()}",
                  align="C")


def _unternehmen_zeilen(unt: dict) -> list[str]:
    class _U:
        pass
    u = _U()
    for k in ("firmenname", "vorname", "nachname", "strasse", "hausnummer", "plz", "ort", "land"):
        setattr(u, k, unt.get(k))
    return _adresszeilen(u)


def _lieferant_zeilen(r) -> list[str]:
    if getattr(r, "lieferant", None) is not None:
        return _adresszeilen(r.lieferant)
    zeilen = [z for z in [(r.partner_freitext or "").strip()] if z]
    strasse = " ".join(filter(None, [getattr(r, "partner_strasse", None), getattr(r, "partner_hausnummer", None)]))
    ort = " ".join(filter(None, [getattr(r, "partner_plz", None), getattr(r, "partner_ort", None)]))
    return zeilen + [z for z in (strasse.strip(), ort.strip()) if z]


def erstelle_eingangsrechnung_erfassung(r, unt: dict) -> bytes:
    pdf = _Blatt(format="A4")
    font_dir = _find_dejavu_dir()
    pdf.add_font("DejaVu", "", str(font_dir / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(font_dir / "DejaVuSans-Bold.ttf"))
    pdf.set_margins(L, 18, L)
    pdf.set_auto_page_break(True, 20)
    pdf.add_page()

    ist_gutschrift = getattr(r, "dokument_typ", "Rechnung") == "Gutschrift"
    titel = "Lieferantengutschrift – Erfassungsblatt" if ist_gutschrift else "Eingangsrechnung – Erfassungsblatt"
    pdf.set_font("DejaVu", "B", 15)
    pdf.set_text_color(*DUNKEL)
    pdf.cell(0, 8, titel, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 8.5)
    pdf.set_text_color(*GRAU)
    pdf.multi_cell(0, 4.5, "Erfasst in RechnungsFee. Das Original ist die Rechnung des Lieferanten – "
                           "es ist (noch) nicht als Beleg angehängt.", new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.ln(4)

    # Rechnungssteller / Empfänger nebeneinander
    y0 = pdf.get_y()
    for x, ueberschrift, zeilen in (
        (L, "Rechnungssteller (Lieferant)", _lieferant_zeilen(r) or ["—"]),
        (L + 90, "Rechnungsempfänger", _unternehmen_zeilen(unt) or ["—"]),
    ):
        pdf.set_xy(x, y0)
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_text_color(*GRAU)
        pdf.cell(80, 5, ueberschrift, new_x="LEFT", new_y="NEXT")
        pdf.set_font("DejaVu", "", 9.5)
        pdf.set_text_color(*DUNKEL)
        for z in zeilen:
            pdf.set_x(x)
            pdf.cell(80, 5, z, new_x="LEFT", new_y="NEXT")
        y_ende = pdf.get_y()
        if x == L:
            y_links = y_ende
    pdf.set_y(max(y_links, pdf.get_y()) + 4)

    # Eckdaten
    def _wert(v) -> str:
        if v is None or v == "":
            return "—"
        if isinstance(v, (date, datetime)):
            return v.strftime("%d.%m.%Y")
        return str(v)

    leistung = "—"
    if getattr(r, "leistung_von", None):
        leistung = _wert(r.leistung_von)
        if getattr(r, "leistung_bis", None) and r.leistung_bis != r.leistung_von:
            leistung += f" – {_wert(r.leistung_bis)}"
    eckdaten = [
        ("Rechnungsnr. des Lieferanten", _wert(getattr(r, "externe_belegnr", None))),
        ("Interne Nummer", _wert(r.rechnungsnummer) if r.rechnungsnummer else ("Entwurf" if r.ist_entwurf else "—")),
        ("Rechnungsdatum", _wert(r.datum)),
        ("Leistungszeitraum", leistung),
        ("Fällig am", _wert(getattr(r, "faellig_am", None))),
        ("Kategorie", r.kategorie.name if getattr(r, "kategorie", None) else "—"),
    ]
    for lbl, wert in eckdaten:
        pdf.set_font("DejaVu", "", 8.5)
        pdf.set_text_color(*GRAU)
        pdf.cell(55, 5, lbl)
        pdf.set_text_color(*DUNKEL)
        pdf.cell(0, 5, wert, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Positionen
    ist_netto = (getattr(r, "eingabemodus", "netto") or "netto") == "netto"
    breiten = [78, 16, 18, 22, 14, 22]
    koepfe = ["Beschreibung", "Menge", "Einheit", "Einzelpreis", "USt %", "Netto" if ist_netto else "Brutto"]
    ausr = ["L", "R", "L", "R", "R", "R"]
    pdf.set_font("DejaVu", "B", 8)
    pdf.set_text_color(*GRAU)
    pdf.set_draw_color(*LINIE)
    for w, k, a in zip(breiten, koepfe, ausr):
        pdf.cell(w, 6, k, border="B", align=a)
    pdf.ln()
    pdf.set_font("DejaVu", "", 8.5)
    pdf.set_text_color(*DUNKEL)
    for pos in r.positionen:
        betrag = (pos.brutto - pos.ust_betrag) if ist_netto else pos.brutto
        y = pdf.get_y()
        pdf.set_x(L + breiten[0])
        pdf.cell(breiten[1], 5, _fmt_zahl(pos.menge), align="R")
        pdf.cell(breiten[2], 5, (pos.einheit or "")[:10])
        pdf.cell(breiten[3], 5, _fmt_euro(pos.netto), align="R")
        pdf.cell(breiten[4], 5, f"{_fmt_ust_satz(pos.ust_satz)} %", align="R")
        pdf.cell(breiten[5], 5, _fmt_euro(betrag), align="R")
        pdf.set_xy(L, y)
        pdf.multi_cell(breiten[0], 5, pos.beschreibung or "", new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.set_draw_color(*LINIE)
    pdf.line(L, pdf.get_y() + 1, L + BREITE, pdf.get_y() + 1)
    pdf.ln(3)

    # Summen
    def _summe(lbl: str, wert, fett: bool = False):
        pdf.set_font("DejaVu", "B" if fett else "", 9)
        pdf.set_x(L + 100)
        pdf.cell(45, 5.5, lbl)
        pdf.cell(25, 5.5, _fmt_euro(wert), align="R", new_x="LMARGIN", new_y="NEXT")

    _summe("Nettobetrag", r.netto_gesamt)
    _summe("Umsatzsteuer", r.ust_gesamt)
    _summe("Gesamtbetrag", r.brutto_gesamt, fett=True)
    pdf.ln(4)

    # Zahlungsstand
    pdf.set_font("DejaVu", "B", 9)
    pdf.cell(0, 6, "Zahlungsstand", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 8.5)
    bezahlt = r.bezahlt_betrag or Decimal("0")
    offen = (r.brutto_gesamt or Decimal("0")) - bezahlt
    status = {"offen": "offen", "teilweise": "teilweise bezahlt", "bezahlt": "bezahlt",
              "uneinbringlich": "ausgebucht"}.get(r.zahlungsstatus or "", r.zahlungsstatus or "—")
    if r.storniert:
        status = "storniert"
    pdf.cell(0, 5, f"Status: {status}   ·   bezahlt: {_fmt_euro(bezahlt)}   ·   offen: {_fmt_euro(offen)}",
             new_x="LMARGIN", new_y="NEXT")
    for e in sorted(getattr(r, "journaleintraege", []) or [], key=lambda j: (j.datum, j.id)):
        pdf.set_text_color(*GRAU)
        pdf.cell(0, 4.5, f"{e.datum.strftime('%d.%m.%Y')}  {e.belegnr}  {e.zahlungsart}  "
                         f"{_fmt_euro(e.brutto_betrag)}  {e.beschreibung[:60]}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*DUNKEL)

    if (r.notizen or "").strip():
        pdf.ln(3)
        pdf.set_font("DejaVu", "B", 9)
        pdf.cell(0, 6, "Notizen", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("DejaVu", "", 8.5)
        pdf.multi_cell(0, 4.5, r.notizen, new_x="LMARGIN", new_y="NEXT", align="L")

    return bytes(pdf.output())
