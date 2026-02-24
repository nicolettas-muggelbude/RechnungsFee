"""
PDF-Prüfbericht für GoBD-Export (Betriebsprüfung).
Erzeugt ein 4-seitiges A4-Dokument:
  Seite 1 – Deckblatt
  Seite 2 – Kennzahlen (Buchungen + USt-Zusammenfassung)
  Seite 3 – Integritätsnachweis (SHA-256-Prüfung)
  Seite 4 – Dateiverzeichnis (Übersicht aller ZIP-Dateien)

Gleiches Design wie pdf_tagesabschluss.py (DejaVu-Fonts, gleiches Farbschema).
"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from fpdf import FPDF


def _find_dejavu_dir() -> Path:
    """Sucht das DejaVu-Font-Verzeichnis auf gaengigen Systemen."""
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


# ---------------------------------------------------------------------------
# Konstanten (identisch zu pdf_tagesabschluss.py)
# ---------------------------------------------------------------------------

GRAU_HELL = (245, 246, 248)
GRAU_RAND = (220, 220, 224)
BLAU = (37, 99, 235)
ROT = (220, 38, 38)
GRUEN = (22, 163, 74)
ORANGE = (180, 80, 0)
GELB_BG = (254, 243, 199)
GELB_RAND = (217, 119, 6)
DUNKELBLAU = (30, 64, 175)


def _fmt_euro(val: Any) -> str:
    try:
        n = float(str(val))
    except (ValueError, TypeError):
        n = 0.0
    formatted = f"{abs(n):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    prefix = "-" if n < -0.001 else ""
    return f"{prefix}{formatted} EUR"


# ---------------------------------------------------------------------------
# PDF-Klasse
# ---------------------------------------------------------------------------

class GobdBerichtPDF(FPDF):

    def __init__(self, unternehmen: dict, jahr: int):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=18)
        dv_dir = _find_dejavu_dir()
        self.add_font("DejaVu", style="",  fname=str(dv_dir / "DejaVuSans.ttf"))
        self.add_font("DejaVu", style="B", fname=str(dv_dir / "DejaVuSans-Bold.ttf"))
        self.add_font("DejaVuMono", style="", fname=str(dv_dir / "DejaVuSansMono.ttf"))
        self._unt = unternehmen
        self._jahr = jahr
        self._druckdatum = datetime.now().strftime("%d.%m.%Y %H:%M")

    # --- Kopfzeile ---------------------------------------------------------

    def header(self):
        unt = self._unt
        self.set_fill_color(*BLAU)
        self.rect(0, 0, 210, 12, "F")

        self.set_y(2)
        self.set_x(10)
        self.set_font("DejaVu", "B", 11)
        self.set_text_color(255, 255, 255)
        self.cell(130, 8, unt.get("firmenname", ""), align="L")

        self.set_font("DejaVu", "", 8)
        self.set_x(140)
        self.cell(60, 8, f"GoBD-Pruefbericht {self._jahr}", align="R")

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

        self.set_y(19)
        self.set_x(10)
        self.set_font("DejaVu", "B", 9)
        self.set_text_color(*BLAU)
        self.cell(190, 5, f"Wirtschaftsjahr {self._jahr}", align="L")

        self.set_text_color(0, 0, 0)
        self.ln(4)

    # --- Fußzeile ----------------------------------------------------------

    def footer(self):
        self.set_y(-12)
        self.set_font("DejaVu", "", 7)
        self.set_text_color(160, 160, 170)
        self.set_draw_color(*GRAU_RAND)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(1)
        self.cell(0, 4,
            f"Seite {self.page_no()} | Erstellt: {self._druckdatum} | RechnungsFee | GoBD-konformer Datenexport",
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
                bold_wert: bool = False, wert_farbe: tuple | None = None,
                label_breite: int = 90):
        self.set_font("DejaVu", "", 8.5)
        self.set_text_color(80, 80, 90)
        self.cell(label_breite, 5.5, label, align="L")
        self.set_font("DejaVu", "B" if bold_wert else "", 8.5)
        if wert_farbe:
            self.set_text_color(*wert_farbe)
        else:
            self.set_text_color(20, 20, 30)
        self.cell(0, 5.5, wert, align="L", ln=True)
        self.set_text_color(0, 0, 0)

    # --- Seite 1: Deckblatt ------------------------------------------------

    def seite_deckblatt(self, exportdatum: str):
        self.add_page()

        # Zentrierung: Großer Titel
        self.ln(8)
        self.set_font("DejaVu", "B", 22)
        self.set_text_color(*DUNKELBLAU)
        self.cell(0, 12, "GoBD-Pruefbericht", align="C", ln=True)
        self.set_font("DejaVu", "B", 14)
        self.set_text_color(*BLAU)
        self.cell(0, 8, f"Wirtschaftsjahr {self._jahr}", align="C", ln=True)
        self.ln(4)

        # Trennlinie
        self.set_draw_color(*BLAU)
        self.set_line_width(0.5)
        self.line(30, self.get_y(), 180, self.get_y())
        self.set_line_width(0.2)
        self.ln(6)

        # Infobox Unternehmen
        unt = self._unt
        self.set_fill_color(*GRAU_HELL)
        self.set_draw_color(*GRAU_RAND)
        self.set_x(30)
        self.set_font("DejaVu", "B", 9)
        self.set_text_color(60, 60, 70)
        self.cell(150, 6, "  Unternehmen", border="TB", fill=True, ln=True)
        self.ln(2)

        def info_zeile(label: str, wert: str):
            self.set_x(30)
            self.set_font("DejaVu", "", 9)
            self.set_text_color(80, 80, 90)
            self.cell(50, 5.5, label)
            self.set_font("DejaVu", "B", 9)
            self.set_text_color(20, 20, 30)
            self.cell(100, 5.5, wert, ln=True)

        info_zeile("Firmenname:", unt.get("firmenname", ""))
        name_teile = []
        if unt.get("vorname"):
            name_teile.append(unt["vorname"])
        if unt.get("nachname"):
            name_teile.append(unt["nachname"])
        if name_teile:
            info_zeile("Inhaber/in:", " ".join(name_teile))
        info_zeile("Adresse:", (
            f"{unt.get('strasse', '')} {unt.get('hausnummer', '')}, "
            f"{unt.get('plz', '')} {unt.get('ort', '')}"
        ).strip(", "))
        steuernr = unt.get("steuernummer") or ""
        ust_id = unt.get("ust_idnr") or ""
        if steuernr:
            info_zeile("Steuernummer:", steuernr)
        if ust_id:
            info_zeile("USt-IdNr.:", ust_id)
        if unt.get("finanzamt"):
            info_zeile("Finanzamt:", unt["finanzamt"])

        self.ln(6)

        # Export-Infos
        self.set_x(30)
        self.set_font("DejaVu", "B", 9)
        self.set_text_color(60, 60, 70)
        self.cell(150, 6, "  Exportinformationen", border="TB", fill=True, ln=True)
        self.ln(2)

        info_zeile("Exportdatum:", exportdatum)
        info_zeile("Exportiert durch:", "RechnungsFee v0.1")
        info_zeile("Erfasster Zeitraum:", f"01.01.{self._jahr} bis 31.12.{self._jahr}")
        info_zeile("Format:", "ZIP-Archiv (CSV + PDF + XML)")
        info_zeile("CSV-Kodierung:", "UTF-8 mit BOM, Semikolon-getrennt")
        info_zeile("Dezimaltrennzeichen:", "Komma (,)")
        info_zeile("Datumsformat:", "TT.MM.JJJJ")

        self.ln(8)

        # Hinweis GoBD
        self.set_fill_color(*GELB_BG)
        self.set_draw_color(*GELB_RAND)
        self.set_x(20)
        self.set_font("DejaVu", "B", 8)
        self.set_text_color(120, 60, 0)
        self.multi_cell(170, 5,
            "Dieser Export wurde gemaess den Grundsaetzen zur ordnungsmaessigen Fuehrung "
            "und Aufbewahrung von Buecher, Aufzeichnungen, Unterlagen und Daten (GoBD) "
            "erstellt. Die enthaltenen Kassenbuchdaten sind unveraenderbar (immutable) "
            "gespeichert und durch SHA-256-Signaturen gesichert.",
            border=1, fill=True)
        self.set_text_color(0, 0, 0)

    # --- Seite 2: Kennzahlen -----------------------------------------------

    def seite_kennzahlen(self, stats: dict):
        self.add_page()
        self.ln(2)

        # Buchungsübersicht
        self._section_title("Buchungsübersicht")
        self._kv_row("Anzahl Buchungen gesamt", str(stats.get("anzahl_buchungen", 0)))
        self._kv_row("davon Stornobuchungen", str(stats.get("stornos", 0)))
        self._kv_row("Einnahmen gesamt (Brutto)",
                     _fmt_euro(stats.get("einnahmen_gesamt", 0)), wert_farbe=GRUEN)
        self._kv_row("Ausgaben gesamt (Brutto)",
                     _fmt_euro(stats.get("ausgaben_gesamt", 0)), wert_farbe=ROT)
        saldo = stats.get("saldo", Decimal("0"))
        saldo_farbe = GRUEN if float(str(saldo)) >= 0 else ROT
        self._kv_row("Saldo (Einnahmen - Ausgaben)",
                     _fmt_euro(saldo), bold_wert=True, wert_farbe=saldo_farbe)
        self.ln(3)

        # Tagesabschlüsse
        self._section_title("Tagesabschlüsse")
        self._kv_row("Anzahl Tagesabschlüsse", str(stats.get("anzahl_abschluesse", 0)))
        self._kv_row("Abschlüsse mit Differenz",
                     str(stats.get("abschluesse_mit_differenz", 0)))
        diff = stats.get("gesamtdifferenz", Decimal("0"))
        diff_farbe = GRUEN if abs(float(str(diff))) < 0.005 else ORANGE
        self._kv_row("Gesamtdifferenz (Kassen-Ist vs. Soll)",
                     _fmt_euro(diff), bold_wert=True, wert_farbe=diff_farbe)
        self.ln(3)

        # Steuerliche Zusammenfassung
        self._section_title("Steuerliche Zusammenfassung (Einnahmen)")
        netto_19 = stats.get("netto_19", Decimal("0"))
        ust_19 = stats.get("ust_19", Decimal("0"))
        netto_7 = stats.get("netto_7", Decimal("0"))
        ust_7 = stats.get("ust_7", Decimal("0"))
        steuerfrei = stats.get("steuerfrei", Decimal("0"))
        vorsteuer = stats.get("vorsteuer", Decimal("0"))

        self._kv_row("Nettoumsätze 19% USt", _fmt_euro(netto_19))
        self._kv_row("Umsatzsteuer 19%", _fmt_euro(ust_19))
        self._kv_row("Nettoumsätze 7% USt", _fmt_euro(netto_7))
        self._kv_row("Umsatzsteuer 7%", _fmt_euro(ust_7))
        self._kv_row("Steuerfreie Einnahmen (0%)", _fmt_euro(steuerfrei))
        self._kv_row("Abziehbare Vorsteuer (Ausgaben)", _fmt_euro(vorsteuer))
        zahllast = (
            Decimal(str(ust_19)) + Decimal(str(ust_7)) - Decimal(str(vorsteuer))
        )
        zahllast_farbe = ROT if float(str(zahllast)) > 0 else GRUEN
        self._kv_row("Rechnerische USt-Zahllast",
                     _fmt_euro(zahllast), bold_wert=True, wert_farbe=zahllast_farbe)
        self.ln(2)
        self.set_font("DejaVu", "", 7.5)
        self.set_text_color(120, 120, 130)
        self.cell(0, 4,
            "  Hinweis: Steuerliche Berechnung ohne Gewähr – massgeblich ist die Steuererklärung.",
            ln=True)
        self.set_text_color(0, 0, 0)

    # --- Seite 3: Integritätsnachweis --------------------------------------

    def seite_integritaet(self, integ_stats: dict):
        self.add_page()
        self.ln(2)

        self._section_title("Integritaetsnachweis (SHA-256-Signaturen)")

        gesamt = integ_stats.get("gesamt", 0)
        gueltig = integ_stats.get("gueltig", 0)
        ungueltig = integ_stats.get("ungueltig", 0)
        ohne = integ_stats.get("ohne_signatur", 0)
        alle_ok = (ungueltig == 0 and ohne == 0 and gesamt > 0)

        self._kv_row("Geprüfte Datensätze gesamt", str(gesamt))
        self._kv_row("Gültige Signaturen", str(gueltig), wert_farbe=GRUEN)
        self._kv_row("Ungültige Signaturen",
                     str(ungueltig),
                     wert_farbe=ROT if ungueltig > 0 else (80, 80, 90))
        self._kv_row("Datensätze ohne Signatur",
                     str(ohne),
                     wert_farbe=ORANGE if ohne > 0 else (80, 80, 90))
        self.ln(3)

        # Ergebnis-Box
        if alle_ok:
            self.set_fill_color(220, 252, 231)  # Grün hell
            self.set_draw_color(*GRUEN)
            ergebnis_text = (
                f"BESTANDEN: Alle {gesamt} Datensaetze haben gueltige SHA-256-Signaturen. "
                "Die Integritaet der Daten ist sichergestellt."
            )
            text_farbe = (20, 83, 45)
        elif ungueltig > 0:
            self.set_fill_color(254, 226, 226)  # Rot hell
            self.set_draw_color(*ROT)
            ergebnis_text = (
                f"NICHT BESTANDEN: {ungueltig} Datensaetze haben ungueltige Signaturen. "
                "Die Daten koennten manipuliert worden sein. Bitte pruefen Sie die betroffenen "
                "Eintraege in der Datei 'integritaetspruefung.csv'."
            )
            text_farbe = (127, 29, 29)
        else:
            self.set_fill_color(*GELB_BG)
            self.set_draw_color(*GELB_RAND)
            ergebnis_text = (
                f"HINWEIS: {ohne} Datensaetze haben keine Signatur. "
                "Dies betrifft moeglicherweise aeltere Eintraege. "
                "Pruefen Sie die Datei 'integritaetspruefung.csv'."
            )
            text_farbe = (120, 60, 0)

        self.set_x(10)
        self.set_font("DejaVu", "B", 8.5)
        self.set_text_color(*text_farbe)
        self.multi_cell(0, 5.5, ergebnis_text, border=1, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(4)

        # Erklärung SHA-256
        self._section_title("Methodik der Signaturprüfung")
        self.set_font("DejaVu", "", 8.5)
        self.set_text_color(60, 60, 70)
        text = (
            "Jeder Kassenbucheintrag und jeder Tagesabschluss wird mit einem SHA-256-Hash "
            "gesichert, der aus den buchungsrelevanten Feldern berechnet wird. "
            "Der Hash wird bei der Erstellung des Datensatzes generiert und unveraenderbar "
            "gespeichert (immutable=1).\n\n"
            "Bei der Pruefung wird der Hash aus den aktuell gespeicherten Feldern neu "
            "berechnet und mit dem gespeicherten Hash verglichen. Eine Abweichung deutet "
            "auf eine nachtraegliche Veraenderung hin, was einen GoBD-Verstoss darstellt.\n\n"
            "Detailergebnisse aller geprueften Datensaetze sind in der Datei "
            "'integritaetspruefung.csv' enthalten."
        )
        self.multi_cell(0, 5.5, text)
        self.set_text_color(0, 0, 0)

    # --- Seite 4: Dateiverzeichnis -----------------------------------------

    def seite_dateiverzeichnis(self, datei_infos: list[dict]):
        self.add_page()
        self.ln(2)

        self._section_title("Dateiverzeichnis des ZIP-Archivs")

        # Tabelle
        col_w = [60, 90, 30]
        self.set_fill_color(210, 217, 232)
        self.set_draw_color(*GRAU_RAND)
        self.set_font("DejaVu", "B", 8.5)
        self.set_text_color(30, 30, 50)
        self.cell(col_w[0], 6, "  Dateiname", border="B", fill=True)
        self.cell(col_w[1], 6, "Beschreibung", border="B", fill=True)
        self.cell(col_w[2], 6, "Datensaetze", border="B", fill=True, align="R", ln=True)

        self.set_font("DejaVu", "", 8.5)
        fill = False
        for info in datei_infos:
            self.set_fill_color(*GRAU_HELL if fill else (255, 255, 255))
            self.set_text_color(20, 20, 30)
            self.cell(col_w[0], 6, f"  {info['name']}", fill=fill)
            self.cell(col_w[1], 6, info["beschreibung"], fill=fill)
            self.cell(col_w[2], 6, str(info["anzahl"]), fill=fill, align="R", ln=True)
            fill = not fill

        # gobd_pruefbericht.pdf
        self.set_fill_color(*GRAU_HELL if fill else (255, 255, 255))
        self.cell(col_w[0], 6, "  gobd_pruefbericht.pdf", fill=fill)
        self.cell(col_w[1], 6, "Dieser Pruefbericht (PDF)", fill=fill)
        self.cell(col_w[2], 6, "1", fill=fill, align="R", ln=True)
        fill = not fill

        # index.xml
        self.set_fill_color(*GRAU_HELL if fill else (255, 255, 255))
        self.cell(col_w[0], 6, "  index.xml", fill=fill)
        self.cell(col_w[1], 6, "GDPdU-Beschreibungsdatei (XML)", fill=fill)
        self.cell(col_w[2], 6, "1", fill=fill, align="R", ln=True)

        self.ln(6)

        # Formatbeschreibung
        self._section_title("CSV-Format-Spezifikation")
        zeilen = [
            ("Zeichenkodierung", "UTF-8 mit Byte Order Mark (BOM)"),
            ("Feldtrennzeichen", "Semikolon (;)"),
            ("Dezimaltrennzeichen", "Komma (,) – kein Tausendertrennzeichen"),
            ("Datumsformat", "TT.MM.JJJJ (z.B. 25.02.2026)"),
            ("Datumszeit-Format", "TT.MM.JJJJ HH:MM:SS"),
            ("Waehrung", "EUR – Betraege ohne Waehrungssymbol"),
            ("Boolesche Werte", "Ja / Nein"),
            ("Erste Zeile", "Spaltenüberschriften"),
            ("Kompatibilitaet", "IDEA, Microsoft Excel, LibreOffice Calc"),
        ]
        for label, wert in zeilen:
            self._kv_row(label, wert, label_breite=70)

        self.ln(4)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(120, 120, 130)
        self.multi_cell(0, 5,
            "Hinweis zur Betriebspruefung: Alle in diesem ZIP-Archiv enthaltenen Daten "
            "wurden unveraendert aus der RechnungsFee-Datenbank exportiert. "
            "Die Signaturdatei 'integritaetspruefung.csv' ermoeglicht die maschinelle "
            "Pruefung der Datenauthentizitaet gemaess GoBD Rz. 108 ff.")
        self.set_text_color(0, 0, 0)


# ---------------------------------------------------------------------------
# Öffentliche Funktion
# ---------------------------------------------------------------------------

def generate_gobd_bericht_pdf(
    unternehmen: dict,
    jahr: int,
    stats: dict,
    datei_infos: list[dict],
) -> bytes:
    """
    Erzeugt den vierseitigen GoBD-Prüfbericht als PDF-Bytes.

    :param unternehmen: dict mit Firmendaten
    :param jahr: Wirtschaftsjahr
    :param stats: aus _sammle_statistiken() + 'integritaet'-Schlüssel
    :param datei_infos: Liste der enthaltenen CSV-Dateien mit Beschreibung + Anzahl
    """
    pdf = GobdBerichtPDF(unternehmen, jahr)

    exportdatum = stats.get("exportdatum", datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
    pdf.seite_deckblatt(exportdatum)
    pdf.seite_kennzahlen(stats)
    pdf.seite_integritaet(stats.get("integritaet", {}))
    pdf.seite_dateiverzeichnis(datei_infos)

    return bytes(pdf.output())
