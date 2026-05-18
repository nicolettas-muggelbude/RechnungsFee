"""
PDF-Generator: Anlage EKS – vollständiger Nachbau des offiziellen Jobcenter-Formulars (04/2025).
9 Seiten: Seiten 1–3 und 9 Hochformat A4, Seiten 4–8 Querformat A4.
"""

import base64
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any

from fpdf import FPDF


# ─── Font-Erkennung ───────────────────────────────────────────────────────────

def _find_dejavu_dir() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        p = Path(sys._MEIPASS) / "fonts"  # type: ignore[attr-defined]
        if (p / "DejaVuSans.ttf").exists():
            return p
    local = Path(__file__).parent.parent / "fonts"
    if (local / "DejaVuSans.ttf").exists():
        return local
    for p in [
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/dejavu"),
        Path("/usr/share/fonts/dejavu-sans-fonts"),
        Path("/usr/local/share/fonts/dejavu"),
        Path.home() / ".fonts/dejavu",
    ]:
        if (p / "DejaVuSans.ttf").exists():
            return p
    raise FileNotFoundError("DejaVu-Fonts nicht gefunden. Bitte 'fonts-dejavu-core' installieren.")


# ─── Konstanten ───────────────────────────────────────────────────────────────

GRAU_HELL   = (245, 246, 248)
GRAU_RAND   = (210, 210, 214)
GRAU_LINIE  = (180, 180, 185)
BLAU        = (37,  99,  235)
DUNKELGRAU  = (80,  95,  115)
GRUEN       = (22,  163,  74)
ORANGE      = (234,  88,  12)
LILA        = (109,  40, 217)
SCHWARZ     = (30,   30,  30)
ZW_BG       = (255, 237, 213)
BLAU_HELL   = (219, 234, 254)

MONATE_KURZ = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
               "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]

# Hochformat A4: 210×297 mm, Ränder 18 mm → Nutzbreite 174 mm
M_P  = 18.0
W_P  = 174.0
# Querformat A4: 297×210 mm, Ränder 12 mm → Nutzbreite 273 mm
M_L  = 12.0
W_L  = 273.0

# Querformat-Spalten
W_L_CODE  = 14.0
W_L_MONAT = 26.0   # 6 × 26 = 156 mm  (kleiner → mehr Platz für Label-Spalte)
W_L_SUMME = 27.0
# W_L_LABEL = W_L − W_L_CODE − 6×W_L_MONAT − W_L_SUMME = 273-14-156-27 = 76 mm (dynamisch)


# ─── Hilfsfunktionen ─────────────────────────────────────────────────────────

def _fmt_datum(iso: Any) -> str:
    if not iso:
        return ""
    try:
        s = str(iso)
        y, m, d = s.split("-")
        return f"{d}.{m}.{y}"
    except Exception:
        return str(iso)


def _fmt_euro(val: Any, leer_strich: bool = True) -> str:
    try:
        n = float(str(val))
    except (ValueError, TypeError):
        n = 0.0
    if leer_strich and abs(n) < 0.005:
        return "–"
    formatted = f"{abs(n):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"−{formatted}" if n < -0.001 else formatted


def _ist_leer(val: Any) -> bool:
    try:
        return abs(float(str(val))) < 0.005
    except (ValueError, TypeError):
        return True


def _monat_kurz(iso_monat: str) -> str:
    try:
        y, m = iso_monat.split("-")
        return f"{MONATE_KURZ[int(m)-1]} {y[2:]}"
    except Exception:
        return iso_monat


def _code_display(code: str) -> str:
    return code.replace("_", ".")


# ─── PDF-Klasse ───────────────────────────────────────────────────────────────

class EksPDF(FPDF):

    def __init__(self, bz_von: Any, bz_bis: Any, art: str,
                 unterschrift_bild: str | None = None):
        super().__init__(format="A4")
        self._bz_von    = bz_von
        self._bz_bis    = bz_bis
        self._art       = art
        self._art_label = "vorläufig" if art == "vorlaeufig" else "abschließend"
        self._sig_data: bytes | None = None
        if unterschrift_bild:
            try:
                # base64-PNG aus dem Unternehmensprofil
                raw = unterschrift_bild
                if "," in raw:
                    raw = raw.split(",", 1)[1]
                self._sig_data = base64.b64decode(raw)
            except Exception:
                pass
        font_dir = _find_dejavu_dir()
        self.add_font("DejaVu", "",  str(font_dir / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(font_dir / "DejaVuSans-Bold.ttf"))
        self.set_auto_page_break(auto=True, margin=20)

    # ── Header / Footer ───────────────────────────────────────────────────────

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("DejaVu", "", 8)
        self.set_text_color(*DUNKELGRAU)
        avail = self.w - self.l_margin - self.r_margin
        self.set_x(self.l_margin)
        self.cell(avail, 5, "Jobcenter-EKS - 04/2025", align="R",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*GRAU_RAND)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.get_y(),
                  self.w - self.r_margin, self.get_y())
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(*DUNKELGRAU)
        avail = self.w - self.l_margin - self.r_margin
        self.set_x(self.l_margin)
        self.cell(avail / 2, 5, "Erstellt mit RechnungsFee", align="L")
        self.set_x(self.l_margin + avail / 2)
        self.cell(avail / 2, 5, f"Seite {self.page_no()} von 9", align="R")

    # ── Seitenwechsel ─────────────────────────────────────────────────────────

    def hoch(self):
        self.add_page(orientation="portrait")
        self.set_margins(M_P, M_P, M_P)
        self.set_auto_page_break(True, margin=20)

    def quer(self):
        self.add_page(orientation="landscape")
        self.set_margins(M_L, M_L, M_L)
        self.set_auto_page_break(True, margin=14)

    # ── Hochformat-Helfer ─────────────────────────────────────────────────────

    def abschnitt(self, buchstabe: str, titel: str):
        self.ln(4)
        self.set_font("DejaVu", "B", 14)
        self.set_text_color(*SCHWARZ)
        self.set_x(self.l_margin)
        self.cell(W_P, 8, f"{buchstabe}. {titel}",
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def txt(self, text: str, bold: bool = False, size: float = 9.0,
            farbe: tuple = SCHWARZ, einzug: float = 0.0):
        self.set_font("DejaVu", "B" if bold else "", size)
        self.set_text_color(*farbe)
        self.set_x(self.l_margin + einzug)
        self.multi_cell(W_P - einzug, 4.5, text, align="L")

    def feld_zeile(self, *felder: tuple):
        """Mehrere (nr, label, wert, breite) Felder nebeneinander, dann Zeilenvorschub."""
        lh = 4.5

        max_lh = lh
        for (nr, label, wert, breite) in felder:
            nr_str = f"{nr} " if nr is not None else ""
            self.set_font("DejaVu", "", 8.5)
            n = len(self.multi_cell(breite, lh, nr_str + label, split_only=True))
            h = n * lh
            if h > max_lh:
                max_lh = h

        y0  = self.get_y()
        xc  = self.l_margin
        gap = 4.0
        for (nr, label, wert, breite) in felder:
            nr_str = f"{nr} " if nr is not None else ""
            self.set_xy(xc, y0)
            self.set_font("DejaVu", "", 8.5)
            self.set_text_color(*DUNKELGRAU)
            self.multi_cell(breite, lh, nr_str + label, align="L")
            y_val = y0 + max_lh
            if wert:
                self.set_xy(xc, y_val)
                self.set_font("DejaVu", "B", 9.5)
                self.set_text_color(*BLAU)
                self.multi_cell(breite, 6, str(wert), align="L")
            else:
                self.set_draw_color(*GRAU_LINIE)
                self.set_line_width(0.4)
                self.line(xc, y_val + 5, xc + breite - 2, y_val + 5)
            xc += breite + gap
        self.set_y(y0 + max_lh + 8)

    def feld(self, nr: int | None, label: str, wert: str = "",
             breite: float | None = None, einzug: float = 0.0):
        self.feld_zeile((nr, label, wert, breite or W_P - einzug))

    def checkbox(self, label: str, checked: bool = False, einzug: float = 6.0):
        x = self.l_margin + einzug
        y = self.get_y()
        box = 4.0
        self.set_draw_color(*DUNKELGRAU)
        self.set_line_width(0.5)
        self.rect(x, y + 0.5, box, box)
        if checked:
            self.set_font("DejaVu", "B", 9)
            self.set_text_color(*SCHWARZ)
            self.set_xy(x, y + 0.5)
            self.cell(box, box, "X", align="C")
        self.set_xy(x + box + 2.5, y)
        self.set_font("DejaVu", "", 9)
        self.set_text_color(*SCHWARZ)
        self.cell(W_P - einzug - box - 2.5, 5.5, label,
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(0.5)

    def unterschrift(self, nr_datum: int, nr_sig: int, label_sig: str):
        self.ln(8)
        w_d = 44.0
        w_s = W_P - w_d - 4
        # Label-Zeile
        y0 = self.get_y()
        self.set_xy(self.l_margin, y0)
        self.set_font("DejaVu", "", 8.5)
        self.set_text_color(*DUNKELGRAU)
        self.cell(w_d, 4.5, f"{nr_datum} Datum")
        self.set_xy(self.l_margin + w_d + 4, y0)
        self.cell(w_s, 4.5, f"{nr_sig} {label_sig}")
        self.ln(4.5)
        # Datum: Unterstrich
        self.set_draw_color(*GRAU_LINIE)
        self.set_line_width(0.4)
        self.line(self.l_margin, self.get_y() + 5,
                  self.l_margin + w_d - 2, self.get_y() + 5)
        # Unterschrift: Bild oder Unterstrich
        sig_x = self.l_margin + w_d + 4
        if self._sig_data:
            try:
                buf = BytesIO(self._sig_data)
                self.image(buf, x=sig_x, y=self.get_y() - 2,
                           w=w_s * 0.5, h=14, keep_aspect_ratio=True)
            except Exception:
                self.line(sig_x, self.get_y() + 5,
                          sig_x + w_s - 2, self.get_y() + 5)
        else:
            self.line(sig_x, self.get_y() + 5,
                      sig_x + w_s - 2, self.get_y() + 5)
        self.ln(14)

    def leeres_feld_gross(self, hoehe: float = 20.0):
        """Großes leeres Rechteck für Anmerkungen."""
        self.ln(2)
        self.set_draw_color(*GRAU_RAND)
        self.set_line_width(0.3)
        self.rect(self.l_margin, self.get_y(), W_P, hoehe)
        self.ln(hoehe + 3)

    # ── Querformat-Helfer ─────────────────────────────────────────────────────

    def _wl(self, n: int) -> float:
        """Beschriftungs-Spaltenbreite im Querformat."""
        return W_L - W_L_CODE - n * W_L_MONAT - W_L_SUMME

    def q_abschnitt(self, nr: int | None, titel: str):
        self.ln(2)
        self.set_font("DejaVu", "B", 10)
        self.set_text_color(*SCHWARZ)
        nr_str = f"{nr}  " if nr is not None else ""
        self.set_x(self.l_margin)
        self.cell(W_L, 7, nr_str + titel, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def q_kopf(self, monate: list[str]):
        wl = self._wl(len(monate))
        self.set_fill_color(*GRAU_HELL)
        self.set_draw_color(*GRAU_RAND)
        self.set_font("DejaVu", "B", 7.5)
        self.set_text_color(*DUNKELGRAU)
        self.set_x(self.l_margin)
        self.cell(W_L_CODE, 6, "Pos.",    fill=True, border=1)
        self.cell(wl,       6, "Kalendermonat (gegebenenfalls Teilmonat)",
                  fill=True, border=1)
        for m in monate:
            self.cell(W_L_MONAT, 6, _monat_kurz(m), fill=True, border=1, align="C")
        self.cell(W_L_SUMME, 6, "Summe ✓", fill=True, border=1, align="R",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*SCHWARZ)

    def q_zeile(self, code: str, label: str, monate: list[str],
                werte: dict, zeilensummen: dict, fett: bool = False):
        wl   = self._wl(len(monate))
        zsum = zeilensummen.get(code, "0")
        ok   = not _ist_leer(zsum)

        self.set_font("DejaVu", "B" if fett else "", 7.5)
        n_lines = len(self.multi_cell(wl - 2, 5.0, label, split_only=True))
        row_h   = max(5.5, n_lines * 5.0)

        y0 = self.get_y()
        if y0 + row_h > self.h - self.b_margin:
            return

        self.set_xy(self.l_margin, y0)
        self.set_font("DejaVu", "B" if (ok or fett) else "", 7.5)
        self.set_text_color(*(SCHWARZ if ok else DUNKELGRAU))
        self.cell(W_L_CODE, row_h, _code_display(code), border=1, align="C")

        lx = self.l_margin + W_L_CODE
        self.set_draw_color(*GRAU_RAND)
        self.set_line_width(0.2)
        self.rect(lx, y0, wl, row_h)
        self.set_xy(lx + 1, y0 + 0.5)
        self.set_font("DejaVu", "B" if fett else "", 7.5)
        self.set_text_color(*SCHWARZ)
        self.multi_cell(wl - 1.5, 5.0, label, border=0, align="L")

        mx = lx + wl
        for m in monate:
            v = werte.get(m, {}).get(code, "0")
            self.set_xy(mx, y0)
            self.set_font("DejaVu", "", 7.5)
            self.set_text_color(*(SCHWARZ if not _ist_leer(v) else DUNKELGRAU))
            self.cell(W_L_MONAT, row_h, _fmt_euro(v), border=1, align="R")
            mx += W_L_MONAT

        self.set_xy(mx, y0)
        self.set_font("DejaVu", "B" if ok else "", 7.5)
        self.set_text_color(*(BLAU if ok else DUNKELGRAU))
        self.cell(W_L_SUMME, row_h, _fmt_euro(zsum), border=1, align="R")

        self.set_xy(self.l_margin, y0 + row_h)
        self.set_text_color(*SCHWARZ)

    def q_uebertrag(self, label: str, monat_werte: dict[str, str], monate: list[str]):
        wl = self._wl(len(monate))
        self.set_fill_color(*GRAU_HELL)
        self.set_font("DejaVu", "B", 7.5)
        self.set_text_color(*DUNKELGRAU)
        self.set_x(self.l_margin)
        self.cell(W_L_CODE, 5.5, "",    border=1, fill=True)
        self.cell(wl,       5.5, label, border=1, fill=True)
        for m in monate:
            self.cell(W_L_MONAT, 5.5, _fmt_euro(monat_werte.get(m, "0")),
                      border=1, fill=True, align="R")
        self.cell(W_L_SUMME, 5.5, "", border=1, fill=True,
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*SCHWARZ)

    def q_zwischensumme(self, label: str, felder: list[dict], monate: list[str],
                         werte: dict, zeilensummen: dict, farbe: tuple = ORANGE):
        wl = self._wl(len(monate))
        self.set_fill_color(*farbe)
        self.set_font("DejaVu", "B", 7.5)
        self.set_text_color(255, 255, 255)
        self.set_x(self.l_margin)
        self.cell(W_L_CODE, 6, "", border=0, fill=True)
        self.cell(wl, 6, label, border=0, fill=True)
        for m in monate:
            v = sum(float(werte.get(m, {}).get(f["code"], "0") or "0")
                    for f in felder)
            self.cell(W_L_MONAT, 6, _fmt_euro(v), border=0, fill=True, align="R")
        total = sum(float(zeilensummen.get(f["code"], "0") or "0") for f in felder)
        self.cell(W_L_SUMME, 6, _fmt_euro(total), border=0, fill=True, align="R",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*SCHWARZ)

    def q_endzeile(self, label: str, monate: list[str], spaltensummen: dict,
                   gesamt: float, farbe: tuple):
        wl = self._wl(len(monate))
        self.set_fill_color(*farbe)
        self.set_font("DejaVu", "B", 8)
        self.set_text_color(255, 255, 255)
        self.set_x(self.l_margin)
        self.cell(W_L_CODE, 7, "", border=0, fill=True)
        self.cell(wl, 7, label, border=0, fill=True)
        for m in monate:
            self.cell(W_L_MONAT, 7, _fmt_euro(spaltensummen.get(m, "0")),
                      border=0, fill=True, align="R")
        self.cell(W_L_SUMME, 7, _fmt_euro(gesamt), border=0, fill=True, align="R",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*SCHWARZ)

    def q_anmerkung(self, nr: int):
        self.ln(3)
        self.set_font("DejaVu", "", 8.5)
        self.set_text_color(*SCHWARZ)
        self.set_x(self.l_margin)
        self.cell(W_L, 5,
                  f"{nr} Anmerkungen tragen Sie bitte hier ein. "
                  "Bitte geben Sie die jeweilige Position an.",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*GRAU_RAND)
        self.set_line_width(0.3)
        self.rect(self.l_margin, self.get_y() + 1, W_L, 18)
        self.ln(22)


# ─── Seiten-Inhalt ────────────────────────────────────────────────────────────

def _s1_deckblatt(pdf: EksPDF, art: str, bz_von: Any, bz_bis: Any,
                  unternehmen: dict):
    """Seite 1: Deckblatt + Abschnitt A + B + C"""
    pdf.hoch()

    # ── Titel-Block ──────────────────────────────────────────────────────────
    # Großes "EKS" rechts oben
    pdf.set_font("DejaVu", "B", 52)
    pdf.set_text_color(*SCHWARZ)
    pdf.set_xy(pdf.l_margin + W_P - 50, pdf.t_margin)
    pdf.cell(50, 20, "EKS", align="R")

    # "Anlage" links oben
    pdf.set_xy(pdf.l_margin, pdf.t_margin + 3)
    pdf.set_font("DejaVu", "B", 18)
    pdf.cell(0, 10, "Anlage", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(*DUNKELGRAU)
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 5, "Anlage zum Einkommen aus selbständiger/freiberuflicher Tätigkeit",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 8)
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 4, "Jobcenter-EKS - 04/2025", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # ── Einleitungstext ───────────────────────────────────────────────────────
    pdf.set_draw_color(*GRAU_RAND)
    pdf.set_line_width(0.3)
    pdf.set_fill_color(*GRAU_HELL)
    pdf.rect(pdf.l_margin, pdf.get_y(), W_P, 58, style="F")
    pdf.set_x(pdf.l_margin + 2)
    pdf.set_font("DejaVu", "", 8.5)
    pdf.set_text_color(*SCHWARZ)
    for zeile in [
        "Sie teilen mit diesem Formular die Einkommensverhältnisse aus einer selbständigen/freiberuflichen "
        "Tätigkeit mit. Zu Beginn eines Bewilligungszeitraumes ist es erforderlich, dass Sie die zu "
        "erwartenden Einkünfte angeben (vorläufige Erklärung). Nach Ablauf des Bewilligungszeitraumes "
        "sind die tatsächlichen Einkünfte anzugeben und zu belegen (abschließende Erklärung).",
        "",
        "Füllen Sie dieses Formular bitte jeweils für sich und für alle weiteren selbständigen/"
        "freiberuflichen Personen über 15 Jahren in der Bedarfsgemeinschaft gesondert aus. Das Formular "
        "ist im Abschnitt E von der antragstellenden Person und im Abschnitt H von der selbständigen/"
        "freiberuflichen Person zu unterschreiben.",
        "",
        "Bitte reichen Sie grundsätzlich keine Originalbelege, sondern Nachweise nur in Kopie ein.",
    ]:
        pdf.set_x(pdf.l_margin + 2)
        pdf.multi_cell(W_P - 4, 4, zeile, align="J")

    pdf.ln(2)

    # ── Abschnitt A: Antragstellende Person ──────────────────────────────────
    pdf.abschnitt("A", "Persönliche Daten der antragstellenden Person")
    w2 = (W_P - 4) / 2
    vorname  = unternehmen.get("vorname") or ""
    nachname = unternehmen.get("nachname") or ""
    pdf.feld_zeile((1, "Vorname",  vorname,  w2), (2, "Nachname", nachname, w2))
    pdf.feld_zeile(
        (3, "Geburtsdatum (TT.MM.JJJJ)",
         _fmt_datum(unternehmen.get("geburtsdatum")), w2),
        (4, "Nummer der Bedarfsgemeinschaft (falls vorhanden)",
         unternehmen.get("bg_nummer") or "", w2),
    )

    # ── Abschnitt B: Selbständige Person ─────────────────────────────────────
    pdf.abschnitt("B", "Persönliche Daten der selbständigen/freiberuflich tätigen Person")
    pdf.feld_zeile((5, "Vorname",  vorname,  w2), (6, "Nachname", nachname, w2))
    pdf.feld_zeile(
        (7, "Geburtsdatum (TT.MM.JJJJ)",
         _fmt_datum(unternehmen.get("geburtsdatum")), w2),
        (None, "", "", w2),
    )

    # ── Abschnitt C: Bewilligungszeitraum ────────────────────────────────────
    pdf.abschnitt("C", "Angaben zum Bewilligungszeitraum und zur Art der Erklärung")
    pdf.txt("8 Bitte geben Sie an, ob Sie in diesem Formular vorläufige oder "
            "abschließende Angaben machen.")
    pdf.ln(1)
    vorlaeufig = art == "vorlaeufig"
    pdf.checkbox("vorläufig (für die Zukunft)",          checked=vorlaeufig)
    pdf.checkbox("abschließend (für die Vergangenheit)", checked=not vorlaeufig)
    pdf.ln(2)
    pdf.txt("9 Bitte geben Sie den Bewilligungszeitraum an. Ein Bewilligungszeitraum "
            "beträgt in der Regel 6 Monate.")
    pdf.ln(1)
    pdf.feld_zeile(
        (None, "von (TT.MM.JJJJ)", _fmt_datum(bz_von), w2),
        (None, "bis (TT.MM.JJJJ)", _fmt_datum(bz_bis), w2),
    )


def _s2_allgemein(pdf: EksPDF, unternehmen: dict, e: dict):
    """Seite 2: Abschnitt D + E"""
    pdf.hoch()

    pdf.abschnitt("D", "Allgemeine Daten zur selbständigen/freiberuflichen Tätigkeit")
    pdf.feld(10, "Firmenname", unternehmen.get("firmenname") or "")
    pdf.ln(1)
    pdf.txt("Bitte geben Sie die Anschrift der Betriebsstätte an.", farbe=DUNKELGRAU)
    pdf.ln(1)
    w4 = [W_P * 0.35, W_P * 0.15, W_P * 0.20, W_P * 0.24]
    gap = (W_P - sum(w4)) / 3
    pdf.feld_zeile(
        (11, "Straße",       unternehmen.get("strasse") or "",  w4[0]),
        (12, "Hausnummer",   unternehmen.get("hausnummer") or "", w4[1]),
        (13, "Postleitzahl", unternehmen.get("plz") or "",       w4[2]),
        (14, "Ort",          unternehmen.get("ort") or "",       w4[3]),
    )
    pdf.feld(15, "Gewerbe oder Tätigkeit", e.get("taetigkeitsart_text") or "")
    w2 = (W_P - 4) / 2
    pdf.feld_zeile(
        (16, "Beginn/Aufnahme der Tätigkeit (MM.JJJJ)", e.get("taetigkeitsbeginn") or "", w2),
        (17, "gegebenenfalls Ende der Tätigkeit (MM.JJJJ)", e.get("taetigkeitsende") or "", w2),
    )
    pdf.feld(18, "Rechtsform des Unternehmens (zum Beispiel GmbH, GbR, e.K.)",
             unternehmen.get("rechtsform") or "")

    pdf.abschnitt("E", "Hinweise und Unterschrift der antragstellenden Person")
    pdf.txt("Datenschutzhinweise", bold=True, size=10)
    pdf.ln(1)
    pdf.txt(
        "Ihre Angaben werden aufgrund der §§ 60–65 Erstes Buch Sozialgesetzbuch (SGB I) und der "
        "§§ 67a, b, c Zehntes Buch Sozialgesetzbuch (SGB X) für die Leistungen nach dem SGB II "
        "erhoben und unterliegen dem Sozialgeheimnis. Näheres zum Datenschutz finden Sie im "
        "Internet unter www.arbeitsagentur.de/datenerhebung.",
        farbe=DUNKELGRAU,
    )
    pdf.ln(3)
    pdf.txt("Ich bestätige, dass die Angaben in den Abschnitten A bis D richtig sind.", bold=True)
    pdf.unterschrift(19, 20,
        "Unterschrift antragstellende Person (bei Minderjährigen: "
        "Unterschrift erziehungs- oder sorgeberechtigte Person)")
    pdf.unterschrift(21, 22, "Unterschrift Betreuerin/Betreuer/Vormund")


def _s3_weitere(pdf: EksPDF, e: dict):
    """Seite 3: Abschnitt F – Weitere Angaben"""
    pdf.hoch()
    pdf.abschnitt("F", "Weitere Angaben zur selbständigen/freiberuflichen Tätigkeit")

    def frage(nr: int, text: str):
        pdf.set_font("DejaVu", "", 9)
        pdf.set_text_color(*SCHWARZ)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(W_P, 4.5, f"{nr} {text}", align="L")
        pdf.ln(1)

    frage(23, "Wird oder wurde die Miet-/Eigentumswohnung oder das Eigenheim – teilweise – "
              "für die selbständige/freiberufliche Tätigkeit gewerblich genutzt?")
    pdf.checkbox("Ja", checked=e.get("wohnung_gewerblich", False))
    pdf.checkbox("Nein", checked=not e.get("wohnung_gewerblich", False))
    w2 = (W_P - 4) / 2
    pdf.feld_zeile(
        (24, "Anzahl der gewerblich genutzten Räume",              e.get("gewerbliche_raeume") or "", w2),
        (25, "Gewerblich genutzte Fläche in Quadratmetern (m²)",   e.get("gewerbliche_flaeche") or "", w2),
    )

    frage(26, "Werden oder wurden in Verbindung mit der selbständigen/freiberuflichen Tätigkeit "
              "Produkte kostenfrei und auf Dauer überlassen, zum Beispiel zur Produktplatzierung?")
    pdf.checkbox("Ja (bitte Auflistung und Nachweise über Art und Wert beifügen)", checked=e.get("produkte_kostenfrei", False))
    pdf.checkbox("Nein", checked=not e.get("produkte_kostenfrei", False))

    frage(27, "Wird oder wurde Personal im Zusammenhang mit der selbständigen/"
              "freiberuflichen Tätigkeit beschäftigt?")
    pdf.checkbox("Ja", checked=e.get("personal_beschaeftigt", False))
    pdf.checkbox("Nein", checked=not e.get("personal_beschaeftigt", False))
    pdf.feld_zeile(
        (28, "Anzahl der Gesamtbeschäftigten", e.get("anzahl_beschaeftigte") or "", w2),
        (None, "", "", w2),
    )

    frage(29, "Ist beabsichtigt, weiteres Personal zu beschäftigen?")
    pdf.checkbox("Ja", checked=e.get("weiteres_personal", False))
    pdf.checkbox("Nein", checked=not e.get("weiteres_personal", False))
    pdf.feld_zeile(
        (30, "Anzahl des weiteren Personals", e.get("anzahl_weiteres_personal") or "", w2),
        (31, "Eine Einstellung erfolgt voraussichtlich ab (TT.MM.JJJJ)", e.get("personal_ab") or "", w2),
    )

    frage(32, "Unterliegt die selbständige/freiberufliche Tätigkeit der Umsatzsteuerpflicht?")
    pdf.checkbox("Ja", checked=e.get("umsatzsteuerpflichtig", False))
    pdf.checkbox("Nein (im Abschnitt G entfallen die Angaben zur Umsatzsteuer und zur Vorsteuer)", checked=not e.get("umsatzsteuerpflichtig", False))

    frage(33, "Erhält oder erhielt die selbständige/freiberufliche Person "
              "Zuschüsse/Beihilfen zu ihrer Tätigkeit?")
    pdf.checkbox("Ja (bitte Nachweise zu Leistungsträger, Art, Dauer und Höhe beifügen)", checked=e.get("zuschuss_erhalten", False))
    pdf.checkbox("Nein", checked=not e.get("zuschuss_erhalten", False))

    frage(34, "Hat die selbständige/freiberufliche Person Zuschüsse/Beihilfen beantragt "
              "oder hat sie vor, diese zu beantragen?")
    pdf.checkbox("Ja (bitte soweit möglich Nachweise über die Antragstellung beifügen)", checked=e.get("zuschuss_beantragt", False))
    pdf.checkbox("Nein", checked=not e.get("zuschuss_beantragt", False))

    frage(35, "Hat die selbständige/freiberufliche Person für den Betrieb/das Gewerbe "
              "ein Darlehen aufgenommen?")
    pdf.checkbox("Ja (bitte Nachweise beifügen, z.B. Darlehensbescheid, Kontoauszug)", checked=e.get("darlehen", False))
    pdf.checkbox("Nein", checked=not e.get("darlehen", False))
    pdf.feld_zeile(
        (36, "Höhe des Darlehens in Euro",                         e.get("darlehen_hoehe") or "", w2),
        (37, "Datum des Geldeingangs auf dem Konto (TT.MM.JJJJ)", e.get("darlehen_eingang") or "", w2),
    )
    pdf.feld_zeile(
        (38, "Beginn der Rückzahlung (TT.MM.JJJJ)",  e.get("darlehen_rueckzahlung_ab") or "", w2),
        (39, "Monatliche Tilgungsrate in Euro",        e.get("darlehen_tilgung") or "", w2),
    )
    pdf.feld_zeile(
        (40, "Mit dem Darlehen finanzierte Betriebsausgaben (Art)",          e.get("darlehen_ausgaben_art") or "", w2),
        (41, "Mit dem Darlehen finanzierte Betriebsausgaben (Höhe in Euro)", e.get("darlehen_ausgaben_hoehe") or "", w2),
    )


def _s4_tabelle_a(pdf: EksPDF, felder_a: list[dict], monate: list[str],
                  werte: dict, zeilensummen: dict, spaltensummen_a: dict):
    """Seite 4: Abschnitt G + Tabelle A"""
    pdf.quer()

    pdf.q_abschnitt(None,
        "G. Angaben zum Einkommen aus selbständiger/freiberuflicher Tätigkeit")
    pdf.set_font("DejaVu", "", 8.5)
    pdf.set_text_color(*SCHWARZ)
    pdf.set_x(pdf.l_margin)
    pdf.cell(W_L, 5,
             "42 Bitte geben Sie an, ob die nachfolgenden Angaben vorläufig oder "
             "abschließend sind.",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    pdf.q_abschnitt(43, "Tabelle A: Angaben zu den Betriebseinnahmen")
    pdf.q_kopf(monate)

    for f in felder_a:
        pdf.q_zeile(f["code"], f["label"], monate, werte, zeilensummen)

    gesamt_a = sum(float(zeilensummen.get(f["code"], "0") or "0") for f in felder_a)
    pdf.q_endzeile("Summe der Betriebseinnahmen", monate, spaltensummen_a,
                   gesamt_a, GRUEN)
    pdf.q_anmerkung(44)


def _s5_tabelle_b1(pdf: EksPDF, felder_b1: list[dict], felder_a: list[dict],
                   monate: list[str], werte: dict, zeilensummen: dict,
                   spaltensummen_a: dict):
    """Seite 5: Tabelle B – Teil 1"""
    pdf.quer()
    pdf.q_abschnitt(45, "Tabelle B – Teil 1: Angaben zu den Betriebsausgaben")
    pdf.q_kopf(monate)

    zw_a = {m: str(spaltensummen_a.get(m, "0")) for m in monate}
    pdf.q_uebertrag("Übertrag Summe Betriebseinnahmen (Tabelle A)", zw_a, monate)

    for f in felder_b1:
        pdf.q_zeile(f["code"], f["label"], monate, werte, zeilensummen)
    pdf.q_zwischensumme("Zwischensumme Tabelle B – Teil 1", felder_b1,
                        monate, werte, zeilensummen)
    pdf.q_anmerkung(46)


def _s6_tabelle_b2(pdf: EksPDF, felder_b2: list[dict], felder_b1: list[dict],
                   monate: list[str], werte: dict, zeilensummen: dict):
    """Seite 6: Tabelle B – Teil 2"""
    pdf.quer()

    # KFZ-Hinweis
    pdf.set_font("DejaVu", "B", 9)
    pdf.set_text_color(*SCHWARZ)
    pdf.set_x(pdf.l_margin)
    pdf.cell(W_L, 5, "Angaben zu einem Kraftfahrzeug in Tabelle B – Teil 2",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(*DUNKELGRAU)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(W_L, 4,
        "Bei einem betrieblichen Kraftfahrzeug füllen Sie bitte die Zeilen B6.1 bis B6.4 aus, "
        "bei einem privaten Kraftfahrzeug die Zeile B6.5. Ein Kraftfahrzeug ist ein betriebliches "
        "Kraftfahrzeug, wenn Sie es mindestens zu 50 Prozent betrieblich nutzen. "
        "Bitte fügen Sie als Nachweis ein Fahrtenbuch bei.",
        align="J")
    pdf.ln(2)

    wl = pdf._wl(len(monate))
    pdf.set_font("DejaVu", "", 8.5)
    pdf.set_text_color(*SCHWARZ)
    pdf.set_x(pdf.l_margin)
    pdf.cell(W_L, 5,
             "47 Wie viele Kilometer wird die selbständige/freiberufliche Person "
             "betrieblich und/oder privat fahren?",
             new_x="LMARGIN", new_y="NEXT")
    # Km-Felder
    w2k = W_L / 2 - 2
    y0 = pdf.get_y()
    nr_str_b = "betriebliche Kilometer"
    nr_str_p = "private Kilometer"
    for xi, lbl in [(0, nr_str_b), (W_L / 2 + 2, nr_str_p)]:
        pdf.set_xy(pdf.l_margin + xi, y0)
        pdf.set_font("DejaVu", "", 8.5)
        pdf.set_text_color(*DUNKELGRAU)
        pdf.cell(w2k, 4.5, lbl)
        pdf.set_draw_color(*GRAU_LINIE)
        pdf.set_line_width(0.4)
        pdf.line(pdf.l_margin + xi, y0 + 9.5, pdf.l_margin + xi + w2k - 2, y0 + 9.5)
    pdf.set_y(y0 + 12)
    pdf.ln(1)

    pdf.q_abschnitt(48, "Tabelle B – Teil 2: Angaben zu den Betriebsausgaben")
    pdf.q_kopf(monate)

    # Übertrag aus Teil 1
    zw1 = {m: str(sum(float(werte.get(m, {}).get(f["code"], "0") or "0")
                      for f in felder_b1))
           for m in monate}
    pdf.q_uebertrag("Übertrag Zwischensumme Tabelle B – Teil 1", zw1, monate)

    for f in felder_b2:
        pdf.q_zeile(f["code"], f["label"], monate, werte, zeilensummen)

    pdf.q_zwischensumme("Zwischensumme Tabelle B – Teil 2", felder_b2,
                        monate, werte, zeilensummen)


def _s7_tabelle_b3(pdf: EksPDF, felder_b: list[dict], felder_b1: list[dict],
                   felder_b2: list[dict], felder_b3: list[dict], felder_a: list[dict],
                   monate: list[str], werte: dict, zeilensummen: dict,
                   spaltensummen_b: dict):
    """Seite 7: Tabelle B – Teil 3 + Gewinn"""
    pdf.quer()
    pdf.q_abschnitt(49, "Tabelle B – Teil 3: Angaben zu den Betriebsausgaben und zum Gewinn")
    pdf.q_kopf(monate)

    # Übertrag aus Teil 2
    zw12 = {m: str(sum(float(werte.get(m, {}).get(f["code"], "0") or "0")
                       for f in felder_b1 + felder_b2))
            for m in monate}
    pdf.q_uebertrag("Übertrag Zwischensumme (Tabelle B – Teil 2)", zw12, monate)

    for f in felder_b3:
        pdf.q_zeile(f["code"], f["label"], monate, werte, zeilensummen)

    # Summe Betriebsausgaben (alle B-Felder)
    gesamt_b = sum(float(zeilensummen.get(f["code"], "0") or "0") for f in felder_b)
    pdf.q_endzeile("Summe Betriebsausgaben (Tabelle B Teil 1, 2 und 3)",
                   monate, spaltensummen_b, gesamt_b, ORANGE)

    # Gewinn-Zeile
    gesamt_a = sum(float(zeilensummen.get(f["code"], "0") or "0") for f in felder_a)
    gewinn   = gesamt_a - gesamt_b
    gewinn_m = {m: str(float(werte.get(m, {}).get("A_sum", "0") or "0") -
                       float(spaltensummen_b.get(m, "0") or "0"))
                for m in monate}
    # Spaltensummen A für Gewinn-Berechnung
    spa = {m: sum(float(werte.get(m, {}).get(f["code"], "0") or "0") for f in felder_a)
           for m in monate}
    gewinn_monat = {m: str(spa[m] - float(spaltensummen_b.get(m, "0") or "0"))
                   for m in monate}

    wl = pdf._wl(len(monate))
    farbe_g = GRUEN if gewinn >= 0 else (220, 38, 38)
    pdf.set_fill_color(*farbe_g)
    pdf.set_font("DejaVu", "B", 8)
    pdf.set_text_color(255, 255, 255)
    pdf.set_x(pdf.l_margin)
    pdf.cell(W_L_CODE, 7, "", border=0, fill=True)
    pdf.cell(wl, 7, "Gewinn (Betriebseinnahmen abzüglich Betriebsausgaben)",
             border=0, fill=True)
    for m in monate:
        g = float(gewinn_monat.get(m, "0") or "0")
        pdf.cell(W_L_MONAT, 7, _fmt_euro(g), border=0, fill=True, align="R")
    pdf.cell(W_L_SUMME, 7, _fmt_euro(gewinn), border=0, fill=True, align="R",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*SCHWARZ)

    pdf.q_anmerkung(50)


def _s8_tabelle_c(pdf: EksPDF, felder_c: list[dict], zeilensummen: dict):
    """Seite 8: Tabelle C – Absetzungen vom Einkommen"""
    pdf.quer()
    pdf.set_font("DejaVu", "B", 10)
    pdf.set_text_color(*SCHWARZ)
    pdf.set_x(pdf.l_margin)
    pdf.cell(W_L, 6, "Absetzungen vom Einkommen", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.q_abschnitt(51, "Tabelle C: Absetzungen vom Einkommen")

    # Spaltenbreiten
    w_code = 14.0
    w_art  = W_L * 0.52
    w_betrag = W_L * 0.20
    w_rhyth  = W_L - w_code - w_art - w_betrag

    # Kopfzeile
    pdf.set_fill_color(*GRAU_HELL)
    pdf.set_draw_color(*GRAU_RAND)
    pdf.set_font("DejaVu", "B", 7.5)
    pdf.set_text_color(*DUNKELGRAU)
    pdf.set_x(pdf.l_margin)
    pdf.cell(w_code,   6.5, "Pos.",            fill=True, border=1)
    pdf.cell(w_art,    6.5, "Art der Absetzung", fill=True, border=1)
    pdf.cell(w_betrag, 6.5, "Höhe in Euro",      fill=True, border=1, align="R")
    pdf.cell(w_rhyth,  6.5,
             "Zahlungsrhythmus\n(z.B. monatlich, quartalsweise)",
             fill=True, border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*SCHWARZ)

    gesamt_c = 0.0
    for f in felder_c:
        v = zeilensummen.get(f["code"], "0")
        hat = not _ist_leer(v)
        try:
            gesamt_c += float(v or "0")
        except (ValueError, TypeError):
            pass

        pdf.set_font("DejaVu", "", 7.5)
        n_lines_c = len(pdf.multi_cell(w_art - 1, 5.0, f["label"], split_only=True))
        row_h_c = max(5.5, n_lines_c * 5.0)

        y0_c = pdf.get_y()
        pdf.set_xy(pdf.l_margin, y0_c)
        pdf.set_font("DejaVu", "B" if hat else "", 7.5)
        pdf.set_text_color(*DUNKELGRAU)
        pdf.cell(w_code, row_h_c, _code_display(f["code"]), border=1)

        lx_c = pdf.l_margin + w_code
        pdf.set_draw_color(*GRAU_RAND)
        pdf.set_line_width(0.2)
        pdf.rect(lx_c, y0_c, w_art, row_h_c)
        pdf.set_xy(lx_c + 1, y0_c + 0.5)
        pdf.set_font("DejaVu", "", 7.5)
        pdf.set_text_color(*SCHWARZ)
        pdf.multi_cell(w_art - 1.5, 5.0, f["label"], border=0, align="L")

        pdf.set_xy(lx_c + w_art, y0_c)
        pdf.set_font("DejaVu", "B" if hat else "", 7.5)
        pdf.set_text_color(*LILA if hat else DUNKELGRAU)
        pdf.cell(w_betrag, row_h_c, _fmt_euro(v), border=1, align="R")

        pdf.set_xy(lx_c + w_art + w_betrag, y0_c)
        pdf.set_text_color(*SCHWARZ)
        pdf.set_font("DejaVu", "", 7.5)
        pdf.cell(w_rhyth, row_h_c, "", border=1,
                 new_x="LMARGIN", new_y="NEXT")

    # Summe C
    pdf.set_fill_color(*LILA)
    pdf.set_font("DejaVu", "B", 8)
    pdf.set_text_color(255, 255, 255)
    pdf.set_x(pdf.l_margin)
    pdf.cell(w_code,   7, "", border=0, fill=True)
    pdf.cell(w_art,    7, "Summe Absetzungen", border=0, fill=True)
    pdf.cell(w_betrag, 7, _fmt_euro(gesamt_c), border=0, fill=True, align="R")
    pdf.cell(w_rhyth,  7, "", border=0, fill=True,
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*SCHWARZ)


def _s9_persoenlich(pdf: EksPDF, felder_a: list[dict], felder_b: list[dict],
                    felder_c: list[dict], zeilensummen: dict, unternehmen: dict,
                    e: dict = None):
    """Seite 9: Personenbezogene Ausgaben + Abschnitt H + Ergebnis-Box"""
    pdf.hoch()
    e = e or {}

    pdf.txt("Angaben zu den personenbezogenen Ausgaben", bold=True, size=11)
    pdf.ln(2)

    w2 = (W_P - 4) / 2

    def frage(nr: int, text: str):
        pdf.set_font("DejaVu", "", 9)
        pdf.set_text_color(*SCHWARZ)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(W_P, 4.5, f"{nr} {text}", align="L")
        pdf.ln(1)

    frage(52, "Hat die selbständige/freiberufliche Person mindestens ein Kind unter "
              "18 Jahren, welches nicht bei ihr wohnt?")
    pdf.checkbox("Ja (bitte Nachweis beifügen, z.B. Geburtsurkunde oder Unterhaltstitel)", checked=e.get("kind_ausserhalb", False))
    pdf.checkbox("Nein", checked=not e.get("kind_ausserhalb", False))

    frage(53, "Zahlt die selbständige/freiberufliche Person Unterhalt?")
    pdf.checkbox("Ja (bitte Nachweise zur Höhe der Unterhaltsverpflichtung und Zahlungsnachweis beifügen)", checked=e.get("unterhalt", False))
    pdf.checkbox("Nein", checked=not e.get("unterhalt", False))

    frage(54, "Hat die selbständige/freiberufliche Person Ausgaben für die Fahrten "
              "zur Betriebsstätte mit dem privaten Kraftfahrzeug?")
    pdf.checkbox("Ja", checked=e.get("fahrten_betriebsstaette", False))
    pdf.checkbox("Nein (weiter mit 57)", checked=not e.get("fahrten_betriebsstaette", False))

    pdf.feld(55, "Bitte geben Sie die einfache Strecke zwischen Wohnung und "
                 "Betriebsstätte in Kilometern an.", e.get("km_einfach") or "", breite=w2)
    pdf.feld(56, "An wie vielen Arbeitstagen je Woche fährt die selbständige/"
                 "freiberufliche Person regelmäßig die Strecke?", e.get("arbeitstage_pro_woche") or "", breite=w2)

    frage(57, "Entstehen der selbständigen/freiberuflichen Person Mehraufwendungen "
              "für Verpflegung wegen einer täglichen Abwesenheit von mindestens "
              "12 Stunden von der Wohnung oder dem üblichen Beschäftigungsort?")
    pdf.checkbox("Ja", checked=e.get("mehraufwand_verpflegung", False))
    pdf.checkbox("Nein", checked=not e.get("mehraufwand_verpflegung", False))
    pdf.feld(58, "Bitte geben Sie die Anzahl der Arbeitstage im Monat an, bei denen "
                 "Mehraufwendungen für Verpflegung entstehen.", e.get("arbeitstage_verpflegung") or "", breite=w2)

    # ── Ergebnis-Box ─────────────────────────────────────────────────────────
    sum_a = sum(float(zeilensummen.get(f["code"], "0") or "0") for f in felder_a)
    sum_b = sum(float(zeilensummen.get(f["code"], "0") or "0") for f in felder_b)
    sum_c = sum(float(zeilensummen.get(f["code"], "0") or "0") for f in felder_c)
    gewinn    = sum_a - sum_b
    einkommen = gewinn - sum_c

    pdf.ln(3)
    pdf.set_fill_color(*GRAU_HELL)
    w_l2 = W_P * 0.70
    w_r2 = W_P - w_l2

    def _ebox(label: str, wert: float, farbe: tuple, trenn: bool = False):
        if trenn:
            pdf.set_draw_color(*GRAU_RAND)
            pdf.set_line_width(0.3)
            pdf.line(pdf.l_margin, pdf.get_y(),
                     pdf.l_margin + W_P, pdf.get_y())
            pdf.ln(1)
        y0 = pdf.get_y()
        pdf.set_xy(pdf.l_margin, y0)
        pdf.set_fill_color(*GRAU_HELL)
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_text_color(*DUNKELGRAU)
        pdf.cell(w_l2, 7, "  " + label, fill=True, border=1)
        pdf.set_text_color(*farbe)
        pdf.cell(w_r2, 7, _fmt_euro(wert, leer_strich=False),
                 fill=True, border=1, align="R",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*SCHWARZ)

    _ebox("Betriebseinnahmen (Tabelle A)", sum_a, GRUEN)
    _ebox("− Betriebsausgaben (Tabelle B)", sum_b, ORANGE)
    _ebox("= Gewinn", gewinn, GRUEN if gewinn >= 0 else (220, 38, 38), trenn=True)
    _ebox("− Absetzungen (Tabelle C)", sum_c, LILA)

    pdf.ln(1)
    pdf.set_fill_color(*BLAU)
    pdf.set_font("DejaVu", "B", 10)
    pdf.set_text_color(255, 255, 255)
    pdf.set_x(pdf.l_margin)
    pdf.cell(w_l2, 9, "  = Zu berücksichtigendes Einkommen", fill=True, border=0)
    pdf.cell(w_r2, 9, _fmt_euro(einkommen, leer_strich=False),
             fill=True, border=0, align="R",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*SCHWARZ)

    # ── Abschnitt H ──────────────────────────────────────────────────────────
    pdf.abschnitt("H", "Unterschrift der selbständigen/freiberuflichen Person")
    pdf.txt("Ich bestätige, dass die Angaben in den Abschnitten F bis G richtig sind.",
            bold=True)
    pdf.unterschrift(59, 60, "Unterschrift selbständige/freiberufliche Person")

    # ── Hinweis ───────────────────────────────────────────────────────────────
    pdf.ln(3)
    pdf.set_font("DejaVu", "", 7)
    pdf.set_text_color(*DUNKELGRAU)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(W_P, 3.5,
        "Dieses Dokument wurde mit RechnungsFee erstellt. Alle Beträge stammen "
        "ausschließlich aus den Journalbuchungen. Das ✓ in der Summen-Spalte zeigt, "
        "dass Zeilen- und Spaltensummen übereinstimmen (Kreuzprüfung). "
        "Bitte reichen Sie dieses Formular zusammen mit den erforderlichen Belegen ein.",
        align="J")


# ─── Öffentliche Funktion ─────────────────────────────────────────────────────

def generate_eks_pdf(
    bewilligungszeitraum_von: Any,
    bewilligungszeitraum_bis: Any,
    art: str,
    monate: list[str],
    werte: dict,
    zeilensummen: dict,
    spaltensummen_a: dict,
    spaltensummen_b: dict,
    spaltensummen_c: dict,
    felder: list[dict],
    unternehmen: dict,
    einstellungen: dict | None = None,
) -> bytes:
    """Erzeugt den vollständigen EKS-Nachbau als 9-seitiges PDF."""
    e = einstellungen or {}
    pdf = EksPDF(
        bz_von=bewilligungszeitraum_von,
        bz_bis=bewilligungszeitraum_bis,
        art=art,
        unterschrift_bild=unternehmen.get("unterschrift_bild"),
    )

    felder_a = [f for f in felder if f.get("tabelle") == "A"]
    felder_b = [f for f in felder if f.get("tabelle") == "B"]
    felder_c = [f for f in felder if f.get("tabelle") == "C"]

    b1_codes = {"B1","B2_1","B2_2","B2_3","B2_4","B3","B4","B5"}
    b2_codes = {"B6_1","B6_2","B6_3","B6_4","B6_5","B7_1","B7_2","B7_3","B8","B9","B10"}
    b3_codes = {"B11","B12","B13","B14_1","B14_2","B14_3","B14_4","B14_5",
                "B15","B16","B17","B18"}

    felder_b1 = [f for f in felder_b if f["code"] in b1_codes]
    felder_b2 = [f for f in felder_b if f["code"] in b2_codes]
    felder_b3 = [f for f in felder_b if f["code"] in b3_codes]

    _s1_deckblatt(pdf, art, bewilligungszeitraum_von, bewilligungszeitraum_bis,
                  unternehmen)
    _s2_allgemein(pdf, unternehmen, e)
    _s3_weitere(pdf, e)
    _s4_tabelle_a(pdf, felder_a, monate, werte, zeilensummen, spaltensummen_a)
    _s5_tabelle_b1(pdf, felder_b1, felder_a, monate, werte, zeilensummen,
                   spaltensummen_a)
    _s6_tabelle_b2(pdf, felder_b2, felder_b1, monate, werte, zeilensummen)
    _s7_tabelle_b3(pdf, felder_b, felder_b1, felder_b2, felder_b3, felder_a,
                   monate, werte, zeilensummen, spaltensummen_b)
    _s8_tabelle_c(pdf, felder_c, zeilensummen)
    _s9_persoenlich(pdf, felder_a, felder_b, felder_c, zeilensummen, unternehmen, e)

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()
