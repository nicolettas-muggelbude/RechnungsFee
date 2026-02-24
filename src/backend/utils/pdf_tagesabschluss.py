"""
PDF-Export für Tagesabschlüsse (GoBD-Dokumentation).
Erzeugt ein druckbares A4-Dokument mit Firmenkopf, Kennzahlen,
Zählprotokoll, SHA-256-Hash und Unterschriftsfeld.

Fonts: DejaVu (kommt mit fpdf2 mit) für volle Unicode-Unterstützung
       (Umlaute, Euro-Zeichen, Sonderzeichen).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fpdf import FPDF


def _find_dejavu_dir() -> Path:
    """Sucht das DejaVu-Font-Verzeichnis auf gaengigen Systemen."""
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu"),          # Debian/Ubuntu/WSL
        Path("/usr/share/fonts/dejavu"),                   # Fedora/RHEL
        Path("/usr/share/fonts/dejavu-sans-fonts"),        # weitere RHEL-Variante
        Path("/usr/local/share/fonts/dejavu"),             # macOS (Homebrew)
        Path.home() / ".fonts/dejavu",                    # Nutzerpfad
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

SCHEINE = {500: "500,00 EUR", 200: "200,00 EUR", 100: "100,00 EUR",
           50: "50,00 EUR", 20: "20,00 EUR", 10: "10,00 EUR", 5: "5,00 EUR"}
MUENZEN = {200: "2,00 EUR", 100: "1,00 EUR", 50: "0,50 EUR", 20: "0,20 EUR",
           10: "0,10 EUR", 5: "0,05 EUR", 2: "0,02 EUR", 1: "0,01 EUR"}

GRAU_HELL = (245, 246, 248)
GRAU_RAND = (220, 220, 224)
BLAU = (37, 99, 235)
ROT = (220, 38, 38)
GRUEN = (22, 163, 74)
GELB_BG = (254, 243, 199)
GELB_RAND = (217, 119, 6)


def _fmt_euro(val: Any) -> str:
    try:
        n = float(str(val))
    except (ValueError, TypeError):
        n = 0.0
    # Deutsches Format: Punkt als Tausendertrennzeichen, Komma als Dezimaltrennzeichen
    formatted = f"{abs(n):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    prefix = "-" if n < -0.001 else ""
    return f"{prefix}{formatted} EUR"


def _fmt_datum(iso: str) -> str:
    try:
        y, m, d = iso[:10].split("-")
        return f"{d}.{m}.{y}"
    except Exception:
        return iso


def _parse_zaehlung(json_str: str | None) -> tuple[list, list]:
    """Gibt (schein_zeilen, muenz_zeilen) zurueck - nur Positionen > 0."""
    if not json_str:
        return [], []
    try:
        data = json.loads(json_str)
    except Exception:
        return [], []

    scheine = []
    for wert_str, anzahl in (data.get("scheine") or {}).items():
        wert = int(wert_str)
        if anzahl > 0:
            scheine.append({
                "label": SCHEINE.get(wert, f"{wert} EUR"),
                "anzahl": anzahl,
                "betrag": wert * anzahl,
            })

    muenzen = []
    for cent_str, anzahl in (data.get("muenzen_cent") or {}).items():
        cent = int(cent_str)
        if anzahl > 0:
            muenzen.append({
                "label": MUENZEN.get(cent, f"{cent} Ct"),
                "anzahl": anzahl,
                "betrag": round((cent / 100) * anzahl, 2),
            })

    return scheine, muenzen


# ---------------------------------------------------------------------------
# PDF-Klasse
# ---------------------------------------------------------------------------

class TagesabschlussPDF(FPDF):

    def __init__(self, unternehmen: dict, zeitraum_label: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=18)
        # DejaVu-Fonts fuer volle Unicode-Unterstuetzung
        # Sucht in gaengigen Systempfaden (Linux/WSL); fuer Tauri-Build Fonts bundlen
        dv_dir = _find_dejavu_dir()
        self.add_font("DejaVu", style="", fname=str(dv_dir / "DejaVuSans.ttf"))
        self.add_font("DejaVu", style="B", fname=str(dv_dir / "DejaVuSans-Bold.ttf"))
        self.add_font("DejaVuMono", style="", fname=str(dv_dir / "DejaVuSansMono.ttf"))
        self._unt = unternehmen
        self._zeitraum = zeitraum_label
        self._druckdatum = datetime.now().strftime("%d.%m.%Y %H:%M")

    # --- Kopfzeile ---------------------------------------------------------

    def header(self):
        unt = self._unt
        # Blauer Streifen
        self.set_fill_color(*BLAU)
        self.rect(0, 0, 210, 12, "F")

        # Firmenname links (weiss)
        self.set_y(2)
        self.set_x(10)
        self.set_font("DejaVu", "B", 11)
        self.set_text_color(255, 255, 255)
        self.cell(130, 8, unt.get("firmenname", ""), align="L")

        # Titel rechts (weiss)
        self.set_font("DejaVu", "", 8)
        self.set_x(140)
        self.cell(60, 8, "Kassenabschlussbericht", align="R")

        # Adresszeile
        self.set_y(14)
        self.set_x(10)
        self.set_font("DejaVu", "", 7.5)
        self.set_text_color(100, 100, 110)
        adresse = (
            f"{unt.get('strasse', '')} {unt.get('hausnummer', '')}, "
            f"{unt.get('plz', '')} {unt.get('ort', '')}"
        )
        steuernr = unt.get("steuernummer") or unt.get("ust_idnr") or ""
        if steuernr:
            adresse += f"  |  St.-Nr.: {steuernr}"
        self.cell(190, 4, adresse, align="L")

        # Zeitraum-Label
        self.set_y(19)
        self.set_x(10)
        self.set_font("DejaVu", "B", 9)
        self.set_text_color(37, 99, 235)
        self.cell(190, 5, f"Zeitraum: {self._zeitraum}", align="L")

        self.set_text_color(0, 0, 0)
        self.ln(4)

    # --- Fusszeile ----------------------------------------------------------

    def footer(self):
        self.set_y(-12)
        self.set_font("DejaVu", "", 7)
        self.set_text_color(160, 160, 170)
        self.set_draw_color(*GRAU_RAND)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(1)
        self.cell(0, 4,
            f"Seite {self.page_no()} | Gedruckt: {self._druckdatum} | RechnungsFee",
            align="C")
        self.set_text_color(0, 0, 0)

    # --- Hilfsmethoden -----------------------------------------------------

    def _section_title(self, text: str):
        self.set_font("DejaVu", "B", 9)
        self.set_fill_color(*GRAU_HELL)
        self.set_draw_color(*GRAU_RAND)
        self.cell(0, 6, f"  {text}", border="B", fill=True, ln=True)
        self.ln(1)

    def _kv_row(self, label: str, wert: str,
                bold_wert: bool = False, wert_farbe: tuple | None = None):
        self.set_font("DejaVu", "", 8.5)
        self.set_text_color(80, 80, 90)
        self.cell(75, 5.5, label, align="L")
        self.set_font("DejaVu", "B" if bold_wert else "", 8.5)
        if wert_farbe:
            self.set_text_color(*wert_farbe)
        else:
            self.set_text_color(20, 20, 30)
        self.cell(0, 5.5, wert, align="L", ln=True)
        self.set_text_color(0, 0, 0)

    # --- Hauptblock pro Abschluss ------------------------------------------

    def abschluss_block(self, a: dict):
        """Rendert einen vollstaendigen Abschluss-Block."""
        datum_fmt = _fmt_datum(a.get("datum", ""))
        uhrzeit = (a.get("uhrzeit") or "")[:5] + " Uhr"
        differenz = float(str(a.get("differenz", 0)))
        hat_differenz = abs(differenz) > 0.005

        # Abschluss-Header
        self.set_fill_color(*BLAU)
        self.set_text_color(255, 255, 255)
        self.set_font("DejaVu", "B", 10)
        self.cell(0, 7, f"  Tagesabschluss  {datum_fmt}  /  {uhrzeit}", fill=True, ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

        # Kennzahlen
        self._section_title("Kennzahlen")
        self._kv_row("Anfangsbestand", _fmt_euro(a.get("anfangsbestand", 0)))
        self._kv_row("Einnahmen (Bar)", _fmt_euro(a.get("einnahmen_bar", 0)),
                     wert_farbe=GRUEN)
        self._kv_row("Ausgaben (Bar)", _fmt_euro(a.get("ausgaben_bar", 0)),
                     wert_farbe=ROT)
        self._kv_row("Soll-Endbestand", _fmt_euro(a.get("soll_endbestand", 0)))
        self._kv_row("Ist-Endbestand (gezaehlt)", _fmt_euro(a.get("ist_endbestand", 0)),
                     bold_wert=True)

        if hat_differenz:
            self._kv_row("Differenz", _fmt_euro(differenz),
                         bold_wert=True, wert_farbe=(180, 80, 0))
        else:
            self._kv_row("Differenz", "0,00 EUR (ausgeglichen)", wert_farbe=GRUEN)

        self._kv_row("Kassenbewegungen gesamt", str(a.get("kassenbewegungen_anzahl", 0)))
        self.ln(2)

        # Differenz-Begruendung
        if hat_differenz and (a.get("differenz_begruendung") or a.get("differenz_buchungsart")):
            self.set_fill_color(*GELB_BG)
            self.set_draw_color(*GELB_RAND)
            self.set_font("DejaVu", "B", 8)
            self.set_text_color(120, 60, 0)
            buchungsart = a.get("differenz_buchungsart") or ""
            begruendung = a.get("differenz_begruendung") or ""
            text = f"Differenz-Buchungsart: {buchungsart}"
            if begruendung:
                text += f"  |  Begruendung: {begruendung}"
            self.set_x(10)
            self.multi_cell(0, 5, text, border=1, fill=True)
            self.set_text_color(0, 0, 0)
            self.ln(2)

        # Zaehlprotokoll
        self._section_title("Zaehlprotokoll")
        schein_z, muenz_z = _parse_zaehlung(a.get("zaehlung_json"))

        if not schein_z and not muenz_z:
            self.set_font("DejaVu", "", 8)
            self.set_text_color(150, 150, 160)
            self.cell(0, 5, "  Kein Zaehlprotokoll erfasst.", ln=True)
            self.set_text_color(0, 0, 0)
        else:
            col_w = [60, 30, 40]  # Bezeichnung, Anzahl, Betrag
            self._zaehlung_tabelle("Scheine", schein_z, col_w)
            self._zaehlung_tabelle("Muenzen", muenz_z, col_w)

            gesamt = sum(z["betrag"] for z in schein_z) + sum(z["betrag"] for z in muenz_z)
            self.set_font("DejaVu", "B", 8.5)
            self.set_fill_color(*GRAU_HELL)
            self.cell(col_w[0] + col_w[1], 5.5, "  Gesamt", fill=True, border="B")
            self.cell(col_w[2], 5.5, _fmt_euro(gesamt), align="R", fill=True, border="B", ln=True)

        self.ln(3)

        # SHA-256 Hash
        self._section_title("Integritaetspruefung (SHA-256)")
        signatur = a.get("signatur") or ""
        if signatur:
            self.set_font("DejaVuMono", "", 7.5)
            self.set_text_color(80, 80, 100)
            self.set_x(10)
            self.cell(0, 5, signatur, ln=True)
        else:
            self.set_font("DejaVu", "", 8)
            self.set_text_color(200, 100, 0)
            self.cell(0, 5, "  Keine Signatur vorhanden.", ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(4)

        # Unterschriftsfeld
        self._unterschrift()
        self.ln(6)

    def _zaehlung_tabelle(self, titel: str, zeilen: list, col_w: list):
        if not zeilen:
            return
        self.set_font("DejaVu", "B", 7.5)
        self.set_fill_color(230, 232, 236)
        self.cell(sum(col_w), 4.5, f"  {titel}", fill=True, border="B", ln=True)

        self.set_font("DejaVu", "", 8)
        for z in zeilen:
            self.cell(col_w[0], 5, f"  {z['label']}")
            self.cell(col_w[1], 5, f"x {z['anzahl']}", align="C")
            self.cell(col_w[2], 5, _fmt_euro(z["betrag"]), align="R", ln=True)

    def _unterschrift(self):
        linie_y = self.get_y() + 14
        self.set_draw_color(80, 80, 100)
        self.line(10, linie_y, 100, linie_y)
        self.set_y(linie_y + 1)
        self.set_x(10)
        self.set_font("DejaVu", "", 7)
        self.set_text_color(120, 120, 130)
        self.cell(90, 4, "Datum, Unterschrift Kassenfuehrer/in", align="L")
        self.set_text_color(0, 0, 0)

    # --- Zusammenfassung ---------------------------------------------------

    def zusammenfassung(self, abschluesse: list[dict]):
        """Zusammenfassungsseite bei mehreren Abschluessen."""
        self.add_page()
        self._section_title(f"Zusammenfassung - {len(abschluesse)} Tagesabschluesse")

        gesamt_einnahmen = sum(float(str(a.get("einnahmen_bar", 0))) for a in abschluesse)
        gesamt_ausgaben = sum(float(str(a.get("ausgaben_bar", 0))) for a in abschluesse)
        gesamt_differenz = sum(float(str(a.get("differenz", 0))) for a in abschluesse)
        daten = [a.get("datum", "") for a in abschluesse if a.get("datum")]
        zeitraum_von = min(daten) if daten else "-"
        zeitraum_bis = max(daten) if daten else "-"

        self._kv_row("Anzahl Abschluesse", str(len(abschluesse)))
        self._kv_row("Zeitraum von", _fmt_datum(zeitraum_von))
        self._kv_row("Zeitraum bis", _fmt_datum(zeitraum_bis))
        self._kv_row("Gesamt-Einnahmen (Bar)", _fmt_euro(gesamt_einnahmen), wert_farbe=GRUEN)
        self._kv_row("Gesamt-Ausgaben (Bar)", _fmt_euro(gesamt_ausgaben), wert_farbe=ROT)
        differenz_farbe = (180, 80, 0) if abs(gesamt_differenz) > 0.005 else GRUEN
        self._kv_row("Gesamt-Differenz", _fmt_euro(gesamt_differenz),
                     bold_wert=True, wert_farbe=differenz_farbe)


# ---------------------------------------------------------------------------
# Oeffentliche Funktion
# ---------------------------------------------------------------------------

def generate_tagesabschluss_pdf(
    abschluesse: list[dict],
    unternehmen: dict,
    zeitraum_label: str,
) -> bytes:
    """
    Erzeugt ein PDF aller uebergebenen Tagesabschluesse und gibt es als Bytes zurueck.

    :param abschluesse: Liste von dicts (aus SQLAlchemy-Model konvertiert)
    :param unternehmen: dict mit Firmendaten (firmenname, strasse, ...)
    :param zeitraum_label: Anzeige-Text fuer Kopfzeile, z.B. "Februar 2026"
    """
    pdf = TagesabschlussPDF(unternehmen, zeitraum_label)

    for a in abschluesse:
        pdf.add_page()
        pdf.abschluss_block(a)

    if len(abschluesse) > 1:
        pdf.zusammenfassung(abschluesse)

    return bytes(pdf.output())
