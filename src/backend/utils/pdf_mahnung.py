"""
Mahnungs-PDF - DIN-5008-Geschäftsbrief (docs/plan-mahnwesen.md, Abschnitt C/D).

Briefkopf (Logo + Absenderblock + Trennlinie) und Fußzeile (Bankdaten/Kontakt) sind
bewusst hier dupliziert statt von RechnungPDFBase geerbt: die Rechnungsbasisklasse ist
eng an Rechnungs-spezifische Metadaten (Rechnungsnummer, Positionstabelle, Storno/
Gutschrift-Varianten) gekoppelt, eine Mahnung ist kein Rechnungsdokument. Konstanten
und reine Hilfsfunktionen (Adresszeilen, Logo-Maße, DejaVu-Suche) werden importiert,
damit Briefkopf-Geometrie und -Optik exakt zu den Rechnungs-PDFs passen.
"""

from datetime import datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from fpdf import FPDF

from utils.pdf_rechnung_base import (
    L_MARGIN, R_MARGIN, PAGE_W, ADRESS_Y, HEADER_LINE_Y, BLOCK_X, BLOCK_W, FOOTER_H,
    GRAU_RAND, TEXT_GRAU, TEXT_DUNKEL,
    _find_dejavu_dir, _adresszeilen, _logo_abmessungen, _person_bezeichnung,
)
from utils.pdf_shared import epc_qr_bytes, build_hr_zeile, embed_unterschrift


def _fmt_euro(val) -> str:
    try:
        v = Decimal(str(val))
        s = f"{abs(v):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"−{s}" if v < 0 else s
    except Exception:
        return "0,00 €"


def _fmt_datum(iso) -> str:
    if not iso:
        return ""
    try:
        y, m, d = str(iso)[:10].split("-")
        return f"{d}.{m}.{y}"
    except Exception:
        return str(iso)


COL_RENR   = 32
COL_RDAT   = 28
COL_FAELL  = 28
COL_BETRAG = 30
TAB_W = COL_RENR + COL_RDAT + COL_FAELL + COL_BETRAG
ROW_H = 6


class MahnungPDF(FPDF):
    def __init__(self, unternehmen: dict):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(L_MARGIN, 10, R_MARGIN)
        self.set_auto_page_break(auto=True, margin=FOOTER_H + 4)
        self.unt = unternehmen
        self._druckdatum = datetime.now().strftime("%d.%m.%Y")
        font_dir = _find_dejavu_dir()
        self.add_font("DejaVu", "", str(font_dir / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(font_dir / "DejaVuSans-Bold.ttf"))

    # -------------------------------------------------------------------------
    # Briefkopf / Fußzeile - Geometrie identisch zu RechnungPDFBase, damit alle
    # Geschäftsbriefe der App gleich aussehen (siehe Modul-Docstring).
    # -------------------------------------------------------------------------

    def header(self):
        unt = self.unt
        top = 10.0

        logo_pfad = unt.get("logo_pfad") or ""
        if logo_pfad and Path(logo_pfad).exists():
            try:
                lw, lh = _logo_abmessungen(logo_pfad)
                if lw > 0:
                    self.image(logo_pfad, x=L_MARGIN, y=top, w=lw, h=lh)
            except Exception:
                pass

        firmenname_k = unt.get("firmenname") or ""
        vorname_k    = unt.get("vorname") or ""
        nachname_k   = unt.get("nachname") or ""
        inhaber_k    = " ".join(filter(None, [vorname_k, nachname_k]))
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
        self.cell(BLOCK_W, 5.5, firmenname_k or inhaber_k or "RechnungsFee", align="L")
        y += 5.5
        if firmenname_k and inhaber_k:
            self.set_xy(BLOCK_X, y)
            self.set_font("DejaVu", "", 9)
            self.cell(BLOCK_W, 4.5, inhaber_k, align="L")
            y += 4.5

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
        unt = self.unt
        self.set_y(-FOOTER_H)
        self.set_draw_color(*GRAU_RAND)
        self.line(L_MARGIN, self.get_y(), PAGE_W - R_MARGIN, self.get_y())
        self.ln(1.5)

        self.set_font("DejaVu", "", 7)
        self.set_text_color(*TEXT_GRAU)

        nutz_w  = PAGE_W - L_MARGIN - R_MARGIN
        col_w   = nutz_w / 3
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

        inhaber_f = " ".join(filter(None, [vorname, nachname])) if firmenname else ""

        def _col(x: float, zeilen: list[str], erste_fett: bool = False):
            y = start_y
            for i, z in enumerate(zeilen):
                if z:
                    self.set_xy(x, y)
                    if erste_fett and i == 0:
                        self.set_font("DejaVu", "B", 7.5)
                    self.cell(col_w, lh, z)
                    if erste_fett and i == 0:
                        self.set_font("DejaVu", "", 7)
                    y += lh

        name_zeilen = [firmenname, inhaber_f] if (firmenname and inhaber_f) else [firmenname or inhaber_f]
        _col(L_MARGIN, list(filter(None, name_zeilen + [
            strasse, plz_ort,
            f"Tel: {telefon}" if telefon else "",
            f"E-Mail: {email}" if email else "",
            f"Web: {webseite}" if webseite else "",
        ])), erste_fett=True)

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
    # DIN-5008-Adressfenster + Meta-Block - einmalig auf Seite 1, analog
    # RechnungPDFBase._render_kopf() (dort mit Rechnungs-Metadaten, hier mit
    # Mahnnummer/Datum/Rechnungsbezug).
    # -------------------------------------------------------------------------

    def render_adressfenster(
        self, empfaenger_zeilen: list[str], mahnnummer: str, datum_str: str, rechnungsnummern: str,
    ) -> float:
        unt = self.unt
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

        emp_y = ADRESS_Y + 6.5
        for i, zeile in enumerate(empfaenger_zeilen):
            self.set_xy(L_MARGIN, emp_y + i * 5.5)
            self.set_font("DejaVu", "B" if i == 0 else "", 9.5)
            self.set_text_color(*TEXT_DUNKEL)
            self.cell(90, 5.5, zeile)
        emp_bottom = emp_y + len(empfaenger_zeilen) * 5.5

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

        _meta("Nummer", mahnnummer or "—")
        _meta("Datum", _fmt_datum(datum_str))
        if rechnungsnummern:
            _meta("Rechnung(en)", rechnungsnummern)

        self.set_text_color(0, 0, 0)
        return max(emp_bottom, meta_y)


def erstelle_mahnung_pdf(
    unternehmen: dict,
    kunde,
    mahnnummer: str,
    bezeichnung: str,
    datum: str,
    mahntext: str,
    positionen: list[dict],  # je: rechnungsnummer, rechnungsdatum, faellig_am, offener_betrag
    offener_betrag_gesamt,
    mahngebuehr,
    verzugszinsen,
    gebuehr_vorperioden=None,
) -> bytes:
    empfaenger_zeilen = _adresszeilen(kunde)
    rechnungsnummern = ", ".join(p["rechnungsnummer"] for p in positionen if p.get("rechnungsnummer"))

    pdf = MahnungPDF(unternehmen)
    pdf.add_page()
    kopf_bottom = pdf.render_adressfenster(empfaenger_zeilen, mahnnummer, datum, rechnungsnummern)
    pdf.set_y(max(kopf_bottom, ADRESS_Y + 6.5 + 5 * 5.5) + 8)

    ist_konsolidiert = len(positionen) > 1
    if ist_konsolidiert:
        betreff = f"{bezeichnung} – Offene Forderungen"
    elif positionen:
        betreff = f"{bezeichnung} – {positionen[0].get('rechnungsnummer') or ''}"
    else:
        betreff = bezeichnung
    pdf.set_font("DejaVu", "B", 12)
    pdf.cell(0, 8, betreff, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("DejaVu", "", 10)
    for zeile in (mahntext or "").split("\n"):
        pdf.multi_cell(0, 5, zeile, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Positionstabelle
    pdf.set_font("DejaVu", "B", 8)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(COL_RENR,   ROW_H, "Rechnung",       border=0, fill=True)
    pdf.cell(COL_RDAT,   ROW_H, "Datum",          border=0, fill=True)
    pdf.cell(COL_FAELL,  ROW_H, "Fällig am",      border=0, fill=True)
    pdf.cell(COL_BETRAG, ROW_H, "Offener Betrag", border=0, align="R", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(180, 180, 180)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + TAB_W, pdf.get_y())

    pdf.set_font("DejaVu", "", 8)
    for pos in positionen:
        pdf.cell(COL_RENR,   ROW_H, str(pos.get("rechnungsnummer") or ""), border=0)
        pdf.cell(COL_RDAT,   ROW_H, _fmt_datum(pos.get("rechnungsdatum")), border=0)
        pdf.cell(COL_FAELL,  ROW_H, _fmt_datum(pos.get("faellig_am")), border=0)
        pdf.cell(COL_BETRAG, ROW_H, _fmt_euro(pos.get("offener_betrag")), border=0, align="R",
                 new_x="LMARGIN", new_y="NEXT")

    pdf.ln(2)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + TAB_W, pdf.get_y())
    pdf.ln(2)

    # Summenblock
    def _summenzeile(label: str, betrag, bold: bool = False):
        pdf.set_font("DejaVu", "B" if bold else "", 9)
        pdf.cell(COL_RENR + COL_RDAT + COL_FAELL, ROW_H, label, border=0, align="R")
        pdf.cell(COL_BETRAG, ROW_H, _fmt_euro(betrag), border=0, align="R", new_x="LMARGIN", new_y="NEXT")

    _summenzeile("Offener Betrag", offener_betrag_gesamt)
    if mahngebuehr and Decimal(str(mahngebuehr)) > 0:
        _summenzeile("Mahngebühr", mahngebuehr)
    if verzugszinsen and Decimal(str(verzugszinsen)) > 0:
        _summenzeile("Verzugszinsen", verzugszinsen)
    if gebuehr_vorperioden and Decimal(str(gebuehr_vorperioden)) > 0:
        _summenzeile("davon aus vorheriger Mahnung übernommen", gebuehr_vorperioden)
    gesamt = (
        Decimal(str(offener_betrag_gesamt or 0))
        + Decimal(str(mahngebuehr or 0))
        + Decimal(str(verzugszinsen or 0))
    )
    pdf.ln(1)
    pdf.set_draw_color(0, 0, 0)
    pdf.line(pdf.l_margin + COL_RENR + COL_RDAT, pdf.get_y(), pdf.l_margin + TAB_W, pdf.get_y())
    _summenzeile("Gesamtforderung", gesamt, bold=True)

    # Bankdaten + Giro-Code (Betrag = Gesamtforderung). Verwendungszweck bewusst die
    # Rechnungsnummer(n) statt der internen Mahnnummer - das ist die Referenz, die der
    # Kunde in seiner eigenen Buchhaltung wiederfindet (Issue-Feedback: "neutral").
    pdf.ln(6)
    iban = unternehmen.get("iban") or ""
    if iban:
        bic = unternehmen.get("bic") or ""
        empf = unternehmen.get("firmenname") or " ".join(
            p for p in [unternehmen.get("vorname"), unternehmen.get("nachname")] if p
        )
        # Referenz: bei genau einer Rechnung deren Nummer (das findet der Kunde in seiner
        # eigenen Buchhaltung wieder). Bei mehreren Rechnungen (konsolidierte Mahnung) wäre
        # eine Aufzählung mehrerer Nummern im Verwendungszweck weder praktikabel noch beim
        # Kunden eindeutig zuordenbar - dort stattdessen die Mahnnummer als EINE Referenz.
        if ist_konsolidiert:
            referenz_label = "Mahnnummer"
            verwendungszweck = mahnnummer or rechnungsnummern or ""
        else:
            referenz_label = "Rechnungsnummer"
            verwendungszweck = rechnungsnummern or mahnnummer or ""
        hinweis = f"Bitte überweisen Sie {_fmt_euro(gesamt)} unter Angabe der {referenz_label} {verwendungszweck} auf IBAN {iban}"
        if bic:
            hinweis += f"  ·  BIC {bic}"
        hinweis += "."

        qr_bytes = epc_qr_bytes(iban, bic, empf, float(gesamt), verwendungszweck[:140]) if unternehmen.get("qr_zahlung_aktiv") else None
        if qr_bytes:
            qr_sz = 25
            gap = 4
            text_w = pdf.w - pdf.l_margin - pdf.r_margin - qr_sz - gap
            qr_x = pdf.l_margin + text_w + gap
            y_start = pdf.get_y()
            pdf.multi_cell(text_w, 5, hinweis)
            pdf.image(BytesIO(qr_bytes), x=qr_x, y=y_start, w=qr_sz, h=qr_sz)
            # Label unter dem QR-Code - identisch zu den Rechnungs-Vorlagen (pdf_rechnung.py),
            # damit GiroCode-Optik über alle Dokumenttypen der App konsistent ist.
            pdf.set_font("DejaVu", "", 6)
            pdf.set_text_color(*TEXT_GRAU)
            pdf.set_xy(qr_x, y_start + qr_sz + 1)
            pdf.cell(qr_sz, 4, "Per Banking-App zahlen", align="C")
            pdf.set_font("DejaVu", "", 9)
            pdf.set_text_color(0, 0, 0)
            if pdf.get_y() < y_start + qr_sz + 5:
                pdf.set_y(y_start + qr_sz + 5)
        else:
            pdf.set_font("DejaVu", "", 9)
            pdf.multi_cell(0, 5, hinweis, new_x="LMARGIN", new_y="NEXT")

    # Unterschrift - nur wirksam wenn unternehmen.unterschrift_auf_rechnung UND
    # unterschrift_bild gesetzt sind (Guard steckt in embed_unterschrift selbst),
    # sonst identisch zu den Rechnungs-PDFs (pdf_rechnung_base.py).
    embed_unterschrift(pdf, unternehmen, L_MARGIN)

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()
