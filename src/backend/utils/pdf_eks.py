"""
PDF-Generator für Anlage EKS (Einkommenserklärung für Selbstständige).
Erstellt eine A4-Querformat-Zusammenfassung mit 6-Monats-Matrix (Tabellen A, B, C).
"""

from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any


from fpdf import FPDF


# ---------------------------------------------------------------------------
# Font-Erkennung
# ---------------------------------------------------------------------------

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
        "DejaVu-Fonts nicht gefunden. Bitte 'fonts-dejavu-core' installieren."
    )


# ---------------------------------------------------------------------------
# Farben & Layout-Konstanten
# ---------------------------------------------------------------------------

GRAU_HELL  = (245, 246, 248)
GRAU_RAND  = (220, 220, 224)
BLAU       = (37,  99,  235)
DUNKELGRAU = (71,  85,  105)
GRUEN      = (22,  163,  74)
ORANGE     = (234,  88,  12)
LILA       = (109,  40, 217)
SLATE      = (71,   85, 105)
ZW_BG      = (255, 237, 213)   # orange-50 für Zwischensummen

MONATE_KURZ = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
               "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]

# Querformat A4: 297 × 210 mm   Ränder: 12 mm
# Nutzbreite: 297 - 24 = 273 mm
W_TOTAL  = 273.0   # nutzbare Breite
W_CODE   = 13.0
W_MONAT  = 34.0    # pro Monatsspalte (6×34 = 204 mm)
W_SUMME  = 30.0
W_LABEL  = W_TOTAL - W_CODE - 6 * W_MONAT - W_SUMME   # ≈ 26 mm → wird dynamisch berechnet

TABELLEN_FARBE = {"A": GRUEN, "B": ORANGE, "C": LILA}
TABELLEN_TITEL = {
    "A": "Tabelle A – Betriebseinnahmen",
    "B": "Tabelle B – Betriebsausgaben",
    "C": "Tabelle C – Absetzungen vom Einkommen",
}


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _fmt_datum(iso: str | date | None) -> str:
    if not iso:
        return "–"
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
    prefix = "−" if n < -0.001 else ""
    return f"{prefix}{formatted}"


def _ist_leer(val: Any) -> bool:
    try:
        return abs(float(str(val))) < 0.005
    except (ValueError, TypeError):
        return True


def _monat_kurz(iso_monat: str) -> str:
    """'2025-01' → 'Jan 25'"""
    try:
        y, m = iso_monat.split("-")
        return f"{MONATE_KURZ[int(m)-1]} {y[2:]}"
    except Exception:
        return iso_monat


# ---------------------------------------------------------------------------
# PDF-Klasse (A4 Querformat)
# ---------------------------------------------------------------------------

class EksPDF(FPDF):
    def __init__(self, zeitraum_von: date, zeitraum_bis: date, art: str):
        super().__init__(orientation="L", format="A4")
        self._zeitraum = f"{_fmt_datum(zeitraum_von)} – {_fmt_datum(zeitraum_bis)}"
        self._art_label = "vorläufig" if art == "vorlaeufig" else "abschließend"
        font_dir = _find_dejavu_dir()
        self.add_font("DejaVu", "",  str(font_dir / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(font_dir / "DejaVuSans-Bold.ttf"))
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(12, 14, 12)

    def header(self):
        self.set_font("DejaVu", "B", 8)
        self.set_text_color(*DUNKELGRAU)
        self.cell(0, 5, f"Anlage EKS – Bewilligungszeitraum: {self._zeitraum}", align="L")
        self.set_font("DejaVu", "", 8)
        self.cell(0, 5, f"Erklärung: {self._art_label}", align="R",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*GRAU_RAND)
        self.set_line_width(0.3)
        self.line(12, self.get_y(), 285, self.get_y())
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("DejaVu", "", 7)
        self.set_text_color(*DUNKELGRAU)
        self.cell(0, 5, f"Seite {self.page_no()}  |  Anlage EKS – {self._zeitraum}", align="C")

    # ------------------------------------------------------------------
    # Matrix-Tabelle (A oder B)
    # ------------------------------------------------------------------

    def matrix_tabelle(
        self,
        tabelle: str,
        felder: list[dict],
        monate: list[str],
        werte: dict,
        zeilensummen: dict,
        spaltensummen: dict,
        abschnitte: list[dict] | None = None,
    ):
        farbe = TABELLEN_FARBE.get(tabelle, BLAU)
        titel = TABELLEN_TITEL.get(tabelle, f"Tabelle {tabelle}")

        w_label = W_TOTAL - W_CODE - len(monate) * W_MONAT - W_SUMME

        # --- Tabellenüberschrift ---
        self.ln(2)
        self.set_fill_color(*farbe)
        self.set_text_color(255, 255, 255)
        self.set_font("DejaVu", "B", 9)
        self.cell(W_TOTAL, 7, f"  {titel}", fill=True, border=0,
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

        # --- Spaltenköpfe ---
        self._matrix_kopf(monate, w_label)

        # --- Zeilen ---
        if abschnitte:
            for ai, abschnitt in enumerate(abschnitte):
                abschnitt_felder = [
                    f for f in felder if f["code"] in abschnitt["codes"]
                ]
                if not abschnitt_felder:
                    continue

                # Teil-Trennzeile
                if abschnitt.get("label"):
                    self._abschnitt_trennzeile(abschnitt["label"], len(monate), w_label)

                for f in abschnitt_felder:
                    self._matrix_zeile(f, monate, werte, zeilensummen, w_label)

                # Zwischensumme (außer letztem Abschnitt)
                if ai < len(abschnitte) - 1:
                    self._zwischensummen_zeile(
                        f"Zwischensumme {abschnitt['label']}",
                        abschnitt_felder, monate, werte, zeilensummen, w_label,
                    )
        else:
            for f in felder:
                self._matrix_zeile(f, monate, werte, zeilensummen, w_label)

        # --- Summenzeile ---
        self._summen_zeile(tabelle, felder, monate, spaltensummen, zeilensummen, w_label, farbe)

    def _matrix_kopf(self, monate: list[str], w_label: float):
        self.set_fill_color(*GRAU_HELL)
        self.set_draw_color(*GRAU_RAND)
        self.set_font("DejaVu", "B", 7.5)
        self.set_text_color(*DUNKELGRAU)
        self.cell(W_CODE,  6, "Code",        fill=True, border=1)
        self.cell(w_label, 6, "Bezeichnung", fill=True, border=1)
        for m in monate:
            self.cell(W_MONAT, 6, _monat_kurz(m), fill=True, border=1, align="C")
        self.cell(W_SUMME, 6, "Summe ✓", fill=True, border=1, align="R",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(30, 30, 30)

    def _matrix_zeile(
        self, f: dict, monate: list[str], werte: dict,
        zeilensummen: dict, w_label: float,
    ):
        if self.get_y() > 182:
            self.add_page()

        code    = f["code"]
        zsum    = zeilensummen.get(code, "0")
        hat_val = not _ist_leer(zsum)

        self.set_font("DejaVu", "B" if hat_val else "", 7.5)
        self.set_text_color(*DUNKELGRAU if not hat_val else (30, 30, 30))
        self.cell(W_CODE, 5.5, code, border=1)

        self.set_font("DejaVu", "", 7.5)
        self.cell(w_label, 5.5, f["label"][:52], border=1)   # kürzen falls zu lang

        for m in monate:
            v = werte.get(m, {}).get(code, "0")
            self.set_font("DejaVu", "", 7.5)
            self.set_text_color(*DUNKELGRAU if _ist_leer(v) else (30, 30, 30))
            self.cell(W_MONAT, 5.5, _fmt_euro(v), border=1, align="R")

        self.set_font("DejaVu", "B" if hat_val else "", 7.5)
        self.set_text_color(*BLAU if hat_val else DUNKELGRAU)
        self.cell(W_SUMME, 5.5, _fmt_euro(zsum), border=1, align="R",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(30, 30, 30)

    def _abschnitt_trennzeile(self, label: str, n_monate: int, w_label: float):
        self.set_fill_color(*GRAU_HELL)
        self.set_draw_color(*GRAU_RAND)
        self.set_font("DejaVu", "B", 7)
        self.set_text_color(*DUNKELGRAU)
        breite = W_CODE + w_label + n_monate * W_MONAT + W_SUMME
        self.cell(breite, 5, f"  {label}", fill=True, border=1,
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(30, 30, 30)

    def _zwischensummen_zeile(
        self, label: str, abschnitt_felder: list[dict],
        monate: list[str], werte: dict, zeilensummen: dict, w_label: float,
    ):
        self.set_fill_color(*ZW_BG)
        self.set_draw_color(*GRAU_RAND)
        self.set_font("DejaVu", "B", 7.5)
        self.set_text_color(*ORANGE)
        self.cell(W_CODE,  5.5, "", border=1, fill=True)
        self.cell(w_label, 5.5, label, border=1, fill=True)
        for m in monate:
            v = sum(
                float(werte.get(m, {}).get(f["code"], "0") or "0")
                for f in abschnitt_felder
            )
            self.cell(W_MONAT, 5.5, _fmt_euro(v), border=1, align="R", fill=True)
        abschnitt_zsum = sum(
            float(zeilensummen.get(f["code"], "0") or "0")
            for f in abschnitt_felder
        )
        self.cell(W_SUMME, 5.5, _fmt_euro(abschnitt_zsum), border=1, align="R",
                  fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(30, 30, 30)

    def _summen_zeile(
        self, tabelle: str, felder: list[dict], monate: list[str],
        spaltensummen: dict, zeilensummen: dict, w_label: float, farbe: tuple,
    ):
        gesamt = sum(float(zeilensummen.get(f["code"], "0") or "0") for f in felder)
        self.set_fill_color(*farbe)
        self.set_draw_color(*farbe)
        self.set_font("DejaVu", "B", 7.5)
        self.set_text_color(255, 255, 255)
        self.cell(W_CODE,  6.5, "", border=0, fill=True)
        label = "Summe Betriebseinnahmen" if tabelle == "A" else "Summe Betriebsausgaben"
        self.cell(w_label, 6.5, label, border=0, fill=True)
        for m in monate:
            self.cell(W_MONAT, 6.5, _fmt_euro(spaltensummen.get(m, "0")),
                      border=0, fill=True, align="R")
        self.cell(W_SUMME, 6.5, _fmt_euro(gesamt),
                  border=0, fill=True, align="R",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(30, 30, 30)
        self.ln(2)

    # ------------------------------------------------------------------
    # Tabelle C (kein monatlicher Aufschluss)
    # ------------------------------------------------------------------

    def tabelle_c(self, felder: list[dict], zeilensummen: dict):
        farbe = TABELLEN_FARBE["C"]
        self.ln(2)
        self.set_fill_color(*farbe)
        self.set_text_color(255, 255, 255)
        self.set_font("DejaVu", "B", 9)
        self.cell(W_TOTAL, 7, f"  {TABELLEN_TITEL['C']}", fill=True, border=0,
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(30, 30, 30)

        # Hinweiszeile
        self.set_font("DejaVu", "", 7.5)
        self.set_text_color(*DUNKELGRAU)
        self.cell(W_TOTAL, 5,
                  "  Keine monatliche Aufgliederung – gilt für den gesamten Bewilligungszeitraum",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(30, 30, 30)
        self.ln(1)

        # Spaltenköpfe
        w_label_c = W_TOTAL - W_CODE - W_SUMME
        self.set_fill_color(*GRAU_HELL)
        self.set_draw_color(*GRAU_RAND)
        self.set_font("DejaVu", "B", 7.5)
        self.set_text_color(*DUNKELGRAU)
        self.cell(W_CODE,    6, "Code",              fill=True, border=1)
        self.cell(w_label_c, 6, "Art der Absetzung", fill=True, border=1)
        self.cell(W_SUMME,   6, "Betrag",             fill=True, border=1, align="R",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(30, 30, 30)

        gesamt_c = 0.0
        for f in felder:
            v = zeilensummen.get(f["code"], "0")
            hat_val = not _ist_leer(v)
            try:
                gesamt_c += float(v or "0")
            except (ValueError, TypeError):
                pass
            self.set_font("DejaVu", "B" if hat_val else "", 7.5)
            if hat_val:
                self.set_text_color(30, 30, 30)
            else:
                self.set_text_color(*DUNKELGRAU)
            self.cell(W_CODE,    5.5, f["code"],  border=1)
            self.set_font("DejaVu", "", 7.5)
            self.cell(w_label_c, 5.5, f["label"][:80], border=1)
            self.set_font("DejaVu", "B" if hat_val else "", 7.5)
            self.set_text_color(*LILA if hat_val else DUNKELGRAU)
            self.cell(W_SUMME,   5.5, _fmt_euro(v), border=1, align="R",
                      new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(30, 30, 30)

        # Summenzeile
        self.set_fill_color(*LILA)
        self.set_font("DejaVu", "B", 7.5)
        self.set_text_color(255, 255, 255)
        self.cell(W_CODE,    6.5, "", fill=True, border=0)
        self.cell(w_label_c, 6.5, "Summe Absetzungen", fill=True, border=0)
        self.cell(W_SUMME,   6.5, _fmt_euro(gesamt_c), fill=True, border=0, align="R",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(30, 30, 30)
        self.ln(2)

    # ------------------------------------------------------------------
    # Ergebnisbox
    # ------------------------------------------------------------------

    def ergebnis_box(self, sum_a: float, sum_b: float, sum_c: float):
        self.ln(3)
        einkommen = sum_a - sum_b - sum_c
        gewinn    = sum_a - sum_b

        self.set_font("DejaVu", "B", 8.5)
        self.set_fill_color(*GRAU_HELL)
        self.set_draw_color(*GRAU_RAND)
        self.set_text_color(*DUNKELGRAU)

        def _zeile(label: str, wert: float, farbe=None, trennlinie=False):
            if trennlinie:
                self.set_draw_color(*GRAU_RAND)
                self.line(12, self.get_y(), 285, self.get_y())
            c = farbe or DUNKELGRAU
            self.set_text_color(*c)
            self.set_font("DejaVu", "B", 8.5)
            self.cell(120, 7, f"  {label}", fill=True, border=1)
            self.set_text_color(*c)
            self.cell(40,  7, _fmt_euro(wert, leer_strich=False), fill=True, border=1, align="R",
                      new_x="LMARGIN", new_y="NEXT")

        _zeile("Betriebseinnahmen (Tabelle A)", sum_a, GRUEN)
        _zeile("− Betriebsausgaben (Tabelle B)", sum_b, ORANGE)
        _zeile("= Gewinn",                        gewinn, BLAU if gewinn >= 0 else (220, 38, 38), trennlinie=False)
        self.ln(1)
        _zeile("− Absetzungen (Tabelle C)", sum_c, LILA)

        # Hauptergebnis
        self.ln(1)
        self.set_fill_color(*BLAU)
        self.set_font("DejaVu", "B", 10)
        self.set_text_color(255, 255, 255)
        self.cell(120, 9, "  = Zu berücksichtigendes Einkommen", fill=True, border=0)
        self.cell(40,  9, _fmt_euro(einkommen, leer_strich=False), fill=True, border=0, align="R",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(30, 30, 30)
        self.ln(4)


# ---------------------------------------------------------------------------
# Öffentliche Funktion (neue Signatur für 6-Monats-Matrix)
# ---------------------------------------------------------------------------

def generate_eks_pdf(
    bewilligungszeitraum_von,
    bewilligungszeitraum_bis,
    art: str,
    monate: list[str],
    werte: dict,
    zeilensummen: dict,
    spaltensummen_a: dict,
    spaltensummen_b: dict,
    spaltensummen_c: dict,
    felder: list[dict],
    unternehmen: dict,
) -> bytes:
    """Erzeugt die EKS-Zusammenfassung als A4-Querformat-PDF.

    monate:          Liste von ISO-Monaten ['2025-01', ..., '2025-06']
    werte:           {monat: {code: betrag_str}}
    zeilensummen:    {code: betrag_str}
    spaltensummen_a: {monat: betrag_str}
    spaltensummen_b: {monat: betrag_str}
    spaltensummen_c: {monat: betrag_str}  (wird ignoriert – C hat keine Monatsspalten)
    felder:          Liste von Dicts {tabelle, code, label, auto}
    unternehmen:     Dict mit firmenname, vorname, nachname, strasse, plz, ort, steuernummer
    """
    pdf = EksPDF(
        zeitraum_von=bewilligungszeitraum_von,
        zeitraum_bis=bewilligungszeitraum_bis,
        art=art,
    )
    pdf.add_page()

    art_label = "vorläufig" if art == "vorlaeufig" else "abschließend"

    # --- Titel ---
    pdf.set_font("DejaVu", "B", 14)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 9, "Anlage EKS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(*DUNKELGRAU)
    pdf.cell(0, 5, "Einkommenserklärung für Selbstständige (Jobcenter / Bürgergeld · Formular 04/2025)",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # --- Personendaten ---
    name = " ".join(t for t in [
        unternehmen.get("firmenname") or "",
        unternehmen.get("vorname") or "",
        unternehmen.get("nachname") or "",
    ] if t)
    adresse = (
        f"{unternehmen.get('strasse', '')}  |  "
        f"{unternehmen.get('plz', '')} {unternehmen.get('ort', '')}"
    ).strip(" |")
    steuernr = unternehmen.get("steuernummer") or "–"

    pdf.set_font("DejaVu", "B", 8.5)
    pdf.set_text_color(30, 30, 30)
    if name:
        pdf.cell(32, 5.5, "Name / Firma:")
        pdf.set_font("DejaVu", "", 8.5)
        pdf.cell(0, 5.5, name, new_x="LMARGIN", new_y="NEXT")
    if adresse.strip("| "):
        pdf.set_font("DejaVu", "B", 8.5)
        pdf.cell(32, 5.5, "Adresse:")
        pdf.set_font("DejaVu", "", 8.5)
        pdf.cell(0, 5.5, adresse, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "B", 8.5)
    pdf.cell(32, 5.5, "Steuernummer:")
    pdf.set_font("DejaVu", "", 8.5)
    pdf.cell(0, 5.5, steuernr, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "B", 8.5)
    pdf.cell(32, 5.5, "Zeitraum:")
    pdf.set_font("DejaVu", "", 8.5)
    pdf.cell(
        0, 5.5,
        f"{_fmt_datum(bewilligungszeitraum_von)} – {_fmt_datum(bewilligungszeitraum_bis)}"
        f"  ({art_label})",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(4)

    # --- Felder gruppieren ---
    felder_a = [f for f in felder if f.get("tabelle") == "A"]
    felder_b = [f for f in felder if f.get("tabelle") == "B"]
    felder_c = [f for f in felder if f.get("tabelle") == "C"]

    b_abschnitte = [
        {
            "label": "Teil 1",
            "codes": ["B1", "B2_1", "B2_2", "B2_3", "B2_4", "B3", "B4", "B5"],
        },
        {
            "label": "Teil 2",
            "codes": ["B6_1", "B6_2", "B6_3", "B6_4", "B6_5",
                      "B7_1", "B7_2", "B7_3", "B8", "B9", "B10"],
        },
        {
            "label": "Teil 3",
            "codes": ["B11", "B12", "B13",
                      "B14_1", "B14_2", "B14_3", "B14_4", "B14_5",
                      "B15", "B16", "B17", "B18"],
        },
    ]

    # --- Tabelle A ---
    if felder_a:
        pdf.matrix_tabelle(
            tabelle="A",
            felder=felder_a,
            monate=monate,
            werte=werte,
            zeilensummen=zeilensummen,
            spaltensummen=spaltensummen_a,
        )

    # --- Tabelle B (neue Seite für Übersichtlichkeit) ---
    if felder_b:
        pdf.add_page()
        pdf.matrix_tabelle(
            tabelle="B",
            felder=felder_b,
            monate=monate,
            werte=werte,
            zeilensummen=zeilensummen,
            spaltensummen=spaltensummen_b,
            abschnitte=b_abschnitte,
        )

    # --- Tabelle C + Ergebnis ---
    pdf.add_page()
    if felder_c:
        pdf.tabelle_c(felder=felder_c, zeilensummen=zeilensummen)

    sum_a = sum(float(zeilensummen.get(f["code"], "0") or "0") for f in felder_a)
    sum_b = sum(float(zeilensummen.get(f["code"], "0") or "0") for f in felder_b)
    sum_c = sum(float(zeilensummen.get(f["code"], "0") or "0") for f in felder_c)
    pdf.ergebnis_box(sum_a, sum_b, sum_c)

    # --- Hinweistext ---
    pdf.set_font("DejaVu", "", 7)
    pdf.set_text_color(*DUNKELGRAU)
    pdf.multi_cell(
        0, 4,
        "Hinweis: Dieses Dokument ist eine Hilfszusammenstellung aus den Buchungsdaten "
        "von RechnungsFee. Es ersetzt nicht die offizielle Anlage EKS des Jobcenters. "
        "Alle Beträge stammen ausschließlich aus den Journalbuchungen. "
        "Das ✓ in der Summen-Spalte zeigt, dass Zeilen- und Spaltensummen übereinstimmen (Kreuzprüfung).",
        align="L",
    )

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()
