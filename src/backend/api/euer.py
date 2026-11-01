"""
EÜR – Einnahmen-Überschuss-Rechnung (Anlage EÜR 2025)

Berechnet EÜR-Zeilen aus Journalbuchungen nach Ist-Versteuerung (Zuflussprinzip).

Besonderheiten:
  - Zeile 17: vereinnahmte USt = Summe ust_betrag aller Einnahmen (inkl. Storno-Abzug)
  - Zeile 57: abziehbare Vorsteuer = Summe vorsteuer_betrag (positiv Ausgaben, negativ Storni)
  - Alle anderen Zeilen: netto_betrag aus kategorie.euer_zeile, vorzeichenkorrigiert nach art
  - Storno-Gegenbuchungen: art wird gespiegelt, netto bleibt positiv →
    Einnahmen-Zeile + art=Ausgabe = subtrahieren; Ausgaben-Zeile + art=Einnahme = subtrahieren
  - Anlage-Buchungen (kontenart=Anlage, euer_zeile=None) → AVEÜR-Hinweis
  - km-Pauschale: brutto_betrag enthält bereits km×0,30 €
"""

import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Anlagegut, Journaleintrag, Kategorie, Unternehmen
from api.journal import _storno_infos
from utils.wirtschaftsjahr import wirtschaftsjahr_zeitraum

router = APIRouter(prefix="/api/euer", tags=["EÜR"])

ZERO = Decimal("0.00")

# ---------------------------------------------------------------------------
# EÜR-Zeilen-Definitionen (Anlage EÜR 2025)
# ---------------------------------------------------------------------------

# (bezeichnung, abschnitt)
EUR_ZEILEN_META: dict[int, tuple[str, str]] = {
    12:  ("Betriebseinnahmen als Kleinunternehmer (§19 Abs. 1 UStG)",           "A"),
    15:  ("Umsatzsteuerpflichtige Betriebseinnahmen (7 % und 19 %)",            "A"),
    16:  ("Steuerfreie / nicht steuerbare Betriebseinnahmen (§4 UStG)",         "A"),
    17:  ("Vereinnahmte Umsatzsteuer",                                          "A"),
    18:  ("Vom FA erstattete / verrechnete Umsatzsteuer",                       "A"),
    20:  ("Private Kfz-Nutzung (1-%-Methode / Fahrtenbuch)",                   "A"),
    21:  ("Sonstige Sach-, Nutzungs- und Leistungsentnahmen (Eigenverbrauch)", "A"),
    27:  ("Waren, Rohstoffe, Hilfsstoffe (ohne USt)",                           "B"),
    29:  ("Bezogene Fremdleistungen (ohne USt)",                                "B"),
    30:  ("Löhne, Gehälter, Sozialversicherung",                               "B"),
    33:  ("AfA für bewegliche Wirtschaftsgüter",                                 "B"),
    36:  ("Geringwertige Wirtschaftsgüter (GWG)",                               "B"),
    39:  ("Miete / Pacht für Geschäftsräume",                                   "B"),
    41:  ("Nebenkosten für Geschäftsräume",                                     "B"),
    43:  ("Aufwendungen für Telekommunikation",                                 "B"),
    44:  ("Reisekosten (Übernachtung, Nebenkosten)",                            "B"),
    45:  ("Fortbildungskosten",                                                  "B"),
    46:  ("Kosten für Buchführung, Steuerberatung, Rechtsberatung",             "B"),
    47:  ("Miet- und Leasingkosten für Wirtschaftsgüter",                       "B"),
    48:  ("Erhaltungsaufwendungen (Instandhaltung, Wartung, Reparatur; ohne Gebäude und Kfz)", "B"),
    57:  ("Abziehbare Vorsteuerbeträge",                                        "B"),
    49:  ("Beiträge, Gebühren, Abgaben und Versicherungen (ohne Gebäude und Kfz)", "B"),
    50:  ("Laufende EDV-Kosten (z. B. Software, Wartung, Beratung)",             "B"),
    51:  ("Arbeitsmittel (z. B. Bürobedarf, Porto, Fachliteratur)",              "B"),
    52:  ("Kosten für Abfallbeseitigung und Entsorgung",                         "B"),
    54:  ("Aufwendungen für Werbung",                                           "B"),
    56:  ("Schuldzinsen",                                                       "B"),
    58:  ("Umsatzsteuer-Vorauszahlungen, sonstige Aufwendungen",               "B"),
    60:  ("Übrige unbeschränkt abziehbare Betriebsausgaben",                     "B"),
    63:  ("Aufwendungen für Bewirtung (70 % abzugsfähig)",                      "B"),
    64:  ("Verpflegungsmehraufwendungen",                                        "B"),
    65:  ("Aufwendungen für häusliches Arbeitszimmer",                          "B"),
    66:  ("Tagespauschale für die Tätigkeit in der häuslichen Wohnung",          "B"),
    68:  ("Leasingkosten für Kraftfahrzeuge",                                   "B"),
    69:  ("KFZ-Steuer, KFZ-Versicherung",                                       "B"),
    70:  ("Sonstige Kfz- und Fahrtkosten (z. B. Reparatur, Treibstoff, ÖPNV)",   "B"),
    # Issue #470: Kz 147 - eigene Zeile für Fahrzeuge außerhalb des Betriebsvermögens (Privat-PKW
    # mit km-Pauschale, anteilige Kosten eines privaten Fahrrads); fehlte bis v0.7.5, Beträge auf
    # einer selbst gesetzten Zeile 71 fielen dadurch aus der Summe der Betriebsausgaben
    71:  ("Fahrtkosten für nicht zum Betriebsvermögen gehörende Fahrzeuge (Nutzungseinlage)", "B"),
    106: ("Entnahmen (Hinweiszeile, kein GuV-Einfluss)",                        "H"),
    107: ("Einlagen (Hinweiszeile, kein GuV-Einfluss)",                         "H"),
}

# Issue #470: Die euer_zeile der Kategorien folgt dem Vordruck der Anlage EÜR 2025 (Basis). Ab dem
# Vordruck 2026 (BMF-Schreiben vom 01.09.2026) ist Zeile 27 "Bildung Rücklage Tierbewertung" (LuF) neu:
# die Waren rücken hinter die Übertragszeile (27 → 29), alle weiteren Ausgaben (29–75) und die
# ergänzenden Angaben ab Zeile 100 (u. a. Entnahmen/Einlagen 106/107) um eins. Die Einnahmen
# (12–23) bleiben gleich. Ein künftiger Vordruck braucht hier nur eine weitere Stufe - die
# Kategorien selbst behalten ihre Basisnummer (keine Datenmigration je Formularjahr).
def formular_zeile(basis: int, jahr: int) -> int:
    """Basis-Zeile (Vordruck 2025) → Zeilennummer im Vordruck des Wirtschaftsjahres."""
    if jahr >= 2026:
        if basis == 27:
            return 29
        if 29 <= basis <= 75 or basis >= 100:
            return basis + 1
    return basis


ZEILE_SUMME_EINNAHMEN = 23   # Basis
ZEILE_SUMME_AUSGABEN = 75    # Basis
ZEILE_AFA_BEWEGLICH = 33     # Basis


ABSCHNITT_LABEL = {
    "A": "A – Betriebseinnahmen",
    "B": "B – Betriebsausgaben",
    "H": "Entnahmen / Einlagen (nachrichtlich)",
}

EINNAHMEN_ZEILEN = {z for z, (_, ab) in EUR_ZEILEN_META.items() if ab == "A" and z not in (106, 107)}
AUSGABEN_ZEILEN  = {z for z, (_, ab) in EUR_ZEILEN_META.items() if ab == "B" and z not in (106, 107)}

# USt-Konten die Ausgangs-USt tragen (kein Vorsteuer-Konto) – für Zeile 17 Storno-Erkennung
_EINNAHME_UST_KONTEN = {"1776", "3806", "1771", "3801", "1780", "1781", "1787", "1789"}


# ---------------------------------------------------------------------------
# Berechnung
# ---------------------------------------------------------------------------

def _euer_haupt_beitrag(e: Journaleintrag) -> tuple[Optional[int], Decimal]:
    """Hauptzeilen-Zuordnung einer Journalbuchung: (euer_zeile, beitrag) - die Summe der
    Beiträge einer Zeile ist deren EÜR-Wert. Zeile None = keine Hauptzeilenzuordnung.

    Gemeinsame Logik von _berechne_euer (Summen) und _euer_kategorien_beitraege
    (Aufschlüsselung) - bisher doppelt gepflegt und auseinandergedriftet.

    Abschnitt A (Einnahmen): Einnahme = +netto, Storno (art=Ausgabe) = −netto.
    Abschnitt B (Ausgaben): Ausgabe = +, Storno (art=Einnahme) = −. Basis = netto +
    nicht abzugsfähiger USt-Anteil (ust_betrag abzüglich tatsächlich abgezogener
    vorsteuer_betrag): fehlt der Vorsteuerabzug ganz (Kleinunternehmer §19, Issue #424)
    oder teilweise (kat.vorsteuer_prozent < 100), ist dieser Anteil ein echter, nicht
    erstattungsfähiger Kostenbestandteil und gehört in die Betriebsausgabe. Bei vollem
    Vorsteuerabzug (vorsteuer_betrag == ust_betrag) ist der Zuschlag 0, Ergebnis bleibt
    netto_betrag. Bei Reverse-Charge (ig_erwerb/§13b) ist brutto_betrag bewusst NICHT
    verwendet (dort ist brutto_betrag == netto_betrag, die additive USt wäre sonst
    fälschlich nochmal abgezogen) - der Zuschlag ist dort ohnehin 0 (voller
    Vorsteuerabzug).

    WICHTIG (Storno-Spiegel): Storno-Gegenbuchungen einer AUSGABE tragen art=Einnahme
    mit positivem netto/ust_betrag, aber NEGATIVEM vorsteuer_betrag
    (vorsteuer_betrag = -original.vorsteuer_betrag, journal.storno / rechnungen.storno) -
    die negative Vorsteuer korrigiert Zeile 57. In der Zeilen-B-Basis muss der tatsächlich
    abgezogene Vorsteueranteil deshalb gespiegelt werden (bei art=Einnahme:
    -vorsteuer_betrag), sonst geht die USt doppelt ein: das Storno einer 30-€-Zahlung
    (netto 30, USt 5,70, Vorsteuer 5,70) wies -41,40 statt -30,00 aus.
    """
    kat: Optional[Kategorie] = e.kategorie
    euer_zeile = kat.euer_zeile if kat else None
    if euer_zeile is None:
        return None, ZERO

    ab = EUR_ZEILEN_META.get(euer_zeile, ("", ""))[1]
    if ab == "A":
        # Einnahmen-Zeile: Einnahme = addieren, Storno (art=Ausgabe) = subtrahieren
        vz = Decimal("1") if e.art == "Einnahme" else Decimal("-1")
        basis = e.netto_betrag or ZERO
    elif ab == "B":
        vz = Decimal("1") if e.art == "Ausgabe" else Decimal("-1")
        # tatsächlich abgezogene Vorsteuer: bei Ausgabe positiv gespeichert, bei der
        # Storno-Gegenbuchung (art=Einnahme) vorzeicheninvertiert (negativ)
        if e.art == "Ausgabe":
            vorsteuer_abgezogen = e.vorsteuer_betrag or ZERO
        else:
            vorsteuer_abgezogen = -(e.vorsteuer_betrag or ZERO)
        basis = (e.netto_betrag or ZERO) + ((e.ust_betrag or ZERO) - vorsteuer_abgezogen)
        if e.ust_sonderfall:
            # Issue #459: bei Reverse Charge fließt die selbst geschuldete USt nicht mit der
            # Zahlung an den Lieferanten, sondern später ans Finanzamt (Zeile 58, Kategorie
            # „Umsatzsteuer-Zahlung FA"). Ohne Vorsteuerabzug (Kleinunternehmer) wäre sie
            # hier sonst ein zweites Mal Betriebsausgabe.
            basis = e.netto_betrag or ZERO
    else:
        vz = Decimal("1")
        basis = e.netto_betrag or ZERO

    return euer_zeile, vz * basis


def _euer_ust_beitraege(e: Journaleintrag) -> list[tuple[int, str, Decimal]]:
    """Unterzeilen-Beiträge einer Journalbuchung: (euer_zeile, kategorie, betrag) für die
    vereinnahmte USt (Zeile 17) und die abziehbare Vorsteuer (Zeile 57). Gemeinsame Logik
    von _berechne_euer (Summen) und _euer_kategorien_beitraege (Aufschlüsselung).

    Zeile 17: reguläre Einnahmen addieren (ohne USt-Konto = Zahlung auf Ausgangsrechnung,
    mit Einnahme-USt-Konto = manuelle Einnahme), Storno einer Einnahme (art=Ausgabe)
    subtrahieren - bei Zahlungen auf Rechnungen ohne USt-Konto nur erkennbar am
    "STORNO "-Präfix; der Abzug muss beide Muster erfassen, sonst bleibt die vereinnahmte
    USt nach einem Zahlungs-Storno zu hoch.
    Storno einer AUSGABE (art=Einnahme, Vorsteuer-Konto vom Original) darf Zeile 17 NICHT
    addieren: diese USt war nie vereinnahmt, die Korrektur läuft ausschließlich über die
    negative Vorsteuer in Zeile 57.
    Skonto-Einträge ausschließen: Zahlung (Zuflussprinzip) enthält bereits reduzierten
    USt-Betrag.

    Zeile 57: Summe aller vorsteuer_betrag-Werte (ohne art-Filter). Storno einer Ausgabe
    hat art=Einnahme mit negativem vorsteuer_betrag → subtrahiert korrekt.
    """
    ist_reverse_charge = bool(e.ust_sonderfall)
    if ist_reverse_charge:
        # Reverse Charge (§13b, i.g. Erwerb): geschuldete Steuer und Vorsteuerabzug entstehen
        # in derselben Voranmeldung und saldieren sich dort - es fließt kein Geld. In der EÜR
        # (Zu-/Abflussprinzip) sind solche Buchungen deshalb neutral und dürfen weder Zeile 17
        # noch Zeile 57 berühren. Ohne diese Ausnahme greift unten die Storno-Heuristik, weil
        # die §13b-Konten 1787/1789 in _EINNAHME_UST_KONTEN stehen (Issue #307).
        return []

    ust_konto = e.konto_ust_skr03 or e.konto_ust_skr04 or ""
    beitraege: list[tuple[int, str, Decimal]] = []

    # Echte Storno-Gegenbuchung: gruppe_id stammt ausschließlich aus der Storno-Erstellung,
    # das Präfix allein könnte auch eine eigene Buchung sein (Erkennung wie _storno_infos, #321)
    ist_storno = e.gruppe_id is not None and (e.beschreibung or "").startswith("STORNO ")

    if e.ust_betrag and e.ust_betrag != 0:
        if e.art == "Einnahme":
            if ist_storno and e.ust_betrag > 0:
                # Gespiegelter Storno einer AUSGABE - auch ohne USt-Konto (Issue #486):
                # diese USt war nie vereinnahmt.
                pass
            elif (e.ust_betrag > 0 or ist_storno) and (not ust_konto or ust_konto in _EINNAHME_UST_KONTEN):
                # negativ nur bei „Zahlung korrigieren“ (rechnungen.py: gleiche art, alle
                # Beträge negiert) - mindert die vereinnahmte USt wie die Hauptzeile (Issue #486)
                beitraege.append((17, "Umsatzsteuer", e.ust_betrag))
        elif e.art == "Ausgabe" and e.ust_betrag > 0 and e.zahlungsart != "Skonto" and (
            ust_konto in _EINNAHME_UST_KONTEN or (not ust_konto and e.beschreibung.startswith("STORNO "))
        ):
            beitraege.append((17, "Umsatzsteuer", -e.ust_betrag))

    if e.vorsteuer_betrag and e.vorsteuer_betrag != 0:
        beitraege.append((57, "Vorsteuer", e.vorsteuer_betrag))

    return beitraege


def _berechne_euer(jahr: int, db: Session) -> dict:
    unt = db.query(Unternehmen).first()
    von, bis = wirtschaftsjahr_zeitraum(unt, jahr) if unt else (
        __import__("datetime").date(jahr, 1, 1), __import__("datetime").date(jahr, 12, 31)
    )

    eintraege = (
        db.query(Journaleintrag)
        .filter(Journaleintrag.datum >= von, Journaleintrag.datum <= bis)
        .all()
    )

    zeilen: dict[int, Decimal] = {}
    anlage_summe = ZERO
    # Issue #470: Kategorien mit einer Zeile, die RechnungsFee nicht kennt - ihr Betrag fließt in
    # keine Summe ein und muss in der Auswertung deutlich gemeldet werden
    unbekannte_zeilen: dict[int, set[str]] = {}

    for e in eintraege:
        kat: Optional[Kategorie] = e.kategorie
        euer_zeile = kat.euer_zeile if kat else None
        if euer_zeile is not None and euer_zeile not in EUR_ZEILEN_META and kat.kontenart != "Anlage":
            unbekannte_zeilen.setdefault(euer_zeile, set()).add(kat.name)

        # Anlage-Buchungen (KFZ-Kauf, EDV etc.) → AVEÜR-Hinweis
        # Issue #439: Vorzeichen nach art – die Storno-Gegenbuchung eines Kaufs ist eine Einnahme
        # mit positivem Betrag und wurde bisher mitaddiert statt abgezogen (jeder Storno erhöhte
        # die Summe). Stornovariante mit gleicher art und negiertem Betrag hebt sich ebenso auf.
        if kat and kat.kontenart == "Anlage":
            vz = Decimal("1") if e.art == "Ausgabe" else Decimal("-1")
            anlage_summe += vz * (e.brutto_betrag or ZERO)
            continue

        haupt_zeile, haupt_beitrag = _euer_haupt_beitrag(e)
        if haupt_zeile is not None:
            zeilen[haupt_zeile] = zeilen.get(haupt_zeile, ZERO) + haupt_beitrag

        for ust_zeile, _ust_name, ust_beitrag in _euer_ust_beitraege(e):
            zeilen[ust_zeile] = zeilen.get(ust_zeile, ZERO) + ust_beitrag

    # AVEÜR: AfA aus dem Anlagenverzeichnis automatisch in Zeile 33 eintragen
    # (Zeile 33 = AfA bewegliche WG, nicht Zeile 36 = GWG – Issue #265)
    # Bewusst weiterhin `jahr` (Kalenderjahr) statt des oben berechneten WJ-Zeitraums: der
    # Abschreibungsplan (_afa_jahresplan) ist strukturell kalenderjahrbasiert (volle
    # Kalenderjahre nach anteiligem Kaufjahr) - eine Umstellung auf WJ-Zeiträume wäre ein
    # großer, eigenständiger Eingriff in eine steuerlich sensible Kernberechnung. Bei
    # abweichendem Wirtschaftsjahr bleibt die AfA-Zuordnung zu "Jahr X" deshalb vorerst
    # kalenderjahrbasiert (Issue #404, bewusste Scope-Entscheidung).
    from api.anlageverzeichnis import _afa_fuer_jahr
    gueter = db.query(Anlagegut).filter(Anlagegut.aktiv == True).all()
    aveur_afa = sum((_afa_fuer_jahr(g, jahr) for g in gueter), ZERO)
    if aveur_afa:
        zeilen[33] = zeilen.get(33, ZERO) + aveur_afa

    # Runden
    q = Decimal("0.01")
    zeilen = {z: v.quantize(q, ROUND_HALF_UP) for z, v in zeilen.items() if v != ZERO}

    summe_einnahmen = sum(zeilen.get(z, ZERO) for z in EINNAHMEN_ZEILEN)
    summe_ausgaben  = sum(zeilen.get(z, ZERO) for z in AUSGABEN_ZEILEN)
    gewinn_verlust  = (summe_einnahmen - summe_ausgaben).quantize(q, ROUND_HALF_UP)

    return {
        "jahr": jahr,
        "zeilen": zeilen,
        "summe_einnahmen": summe_einnahmen.quantize(q, ROUND_HALF_UP),
        "summe_ausgaben":  summe_ausgaben.quantize(q, ROUND_HALF_UP),
        "gewinn_verlust":  gewinn_verlust,
        "anlage_zugaenge": anlage_summe.quantize(q, ROUND_HALF_UP),
        "aveur_afa":       aveur_afa.quantize(q, ROUND_HALF_UP),
        "nicht_zugeordnet": [
            {"zeile": z, "betrag": zeilen.get(z, ZERO), "kategorien": sorted(namen)}
            for z, namen in sorted(unbekannte_zeilen.items())
            if zeilen.get(z, ZERO) != ZERO
        ],
    }


def euer_zeilen_auswahl() -> list[dict]:
    """Gültige EÜR-Zeilen (Basis Vordruck 2025) für die Auswahl im Kategorie-Formular."""
    return [
        {"zeile": z, "bezeichnung": bez, "abschnitt": ab}
        for z, (bez, ab) in sorted(EUR_ZEILEN_META.items())
    ]


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def _generate_pdf(daten: dict, unt: Unternehmen) -> bytes:
    from fpdf import FPDF

    def _fonts() -> Path:
        import sys
        if getattr(sys, "frozen", False):
            p = Path(sys._MEIPASS) / "fonts"  # type: ignore[attr-defined]
            if (p / "DejaVuSans.ttf").exists():
                return p
        local = Path(__file__).parent.parent / "fonts"
        if (local / "DejaVuSans.ttf").exists():
            return local
        for p in [Path("/usr/share/fonts/truetype/dejavu"), Path("/usr/share/fonts/dejavu")]:
            if (p / "DejaVuSans.ttf").exists():
                return p
        raise FileNotFoundError("DejaVu-Fonts nicht gefunden.")

    BLAU = (37, 99, 235); GRAU = (245, 246, 248); DUNKEL = (30, 41, 59); MITTEL = (100, 116, 139)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    fonts = _fonts()
    pdf.add_font("DejaVu", "",  str(fonts / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(fonts / "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(True, margin=20)

    pdf.set_fill_color(*BLAU)
    pdf.rect(0, 0, 210, 18, "F")
    pdf.set_font("DejaVu", "B", 11)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(20, 5)
    pdf.cell(0, 8, f"Einnahmen-Überschuss-Rechnung {daten['jahr']} – Anzeigehilfe", ln=True)
    pdf.set_text_color(*DUNKEL)

    name = unt.firmenname or f"{unt.vorname or ''} {unt.nachname or ''}".strip()
    pdf.set_xy(20, 24)
    pdf.set_font("DejaVu", "B", 13)
    pdf.cell(0, 7, name, ln=True)
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(*MITTEL)
    pdf.cell(0, 5, f"Steuernummer: {unt.steuernummer or '—'}  ·  Wirtschaftsjahr: {daten['jahr']}", ln=True)
    pdf.ln(4)

    def euro(v: Decimal) -> str:
        neg = v < 0
        s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
        return ("− " if neg else "") + s

    def zeile_row(z: int, bez: str, betrag: Decimal, fett: bool = False):
        y = pdf.get_y()
        h = 6.5
        pdf.set_fill_color(*BLAU)
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(20, y)
        pdf.cell(14, h, f"Z. {z}", border=0, fill=True, align="C")
        pdf.set_font("DejaVu", "B" if fett else "", 9)
        pdf.set_text_color(*DUNKEL)
        pdf.set_xy(36, y)
        pdf.cell(120, h, bez, border=0, align="L")
        color = (220, 38, 38) if betrag < 0 else DUNKEL
        pdf.set_text_color(*color)
        pdf.set_font("DejaVu", "B" if fett else "", 9)
        pdf.set_xy(157, y)
        pdf.cell(33, h, euro(betrag), align="R", border=0)
        pdf.ln(h + 1)

    def section_header(titel: str):
        pdf.set_fill_color(229, 231, 235)
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_text_color(*DUNKEL)
        pdf.set_x(20)
        pdf.cell(170, 6, f"  {titel}", fill=True, ln=True)
        pdf.ln(1)

    def summen_row(label: str, betrag: Decimal):
        pdf.set_fill_color(37, 99, 235)
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_text_color(255, 255, 255)
        pdf.set_x(20)
        pdf.cell(135, 7, f"  {label}", fill=True, align="L")
        pdf.cell(35, 7, euro(betrag), fill=True, align="R")
        pdf.ln(8)

    zeilen = daten["zeilen"]
    aktueller_abschnitt = None

    for z in sorted(EUR_ZEILEN_META.keys()):
        if z not in zeilen:
            continue
        bez, ab = EUR_ZEILEN_META[z]
        if ab != aktueller_abschnitt:
            if aktueller_abschnitt == "A":
                pdf.ln(1)
                summen_row(f"Summe Betriebseinnahmen (Zeile {formular_zeile(ZEILE_SUMME_EINNAHMEN, daten['jahr'])})", daten["summe_einnahmen"])
            aktueller_abschnitt = ab
            section_header(ABSCHNITT_LABEL.get(ab, ab))
        zeile_row(formular_zeile(z, daten["jahr"]), bez, zeilen[z])

    if aktueller_abschnitt == "B":
        pdf.ln(1)
        summen_row(f"Summe Betriebsausgaben (Zeile {formular_zeile(ZEILE_SUMME_AUSGABEN, daten['jahr'])})", daten["summe_ausgaben"])

    for nz in daten.get("nicht_zugeordnet", []):
        pdf.ln(2)
        pdf.set_fill_color(254, 226, 226)
        pdf.set_x(20)
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_text_color(153, 27, 27)
        pdf.multi_cell(170, 5,
            f"Achtung: {euro(nz['betrag'])} auf der unbekannten EÜR-Zeile {nz['zeile']} "
            f"(Kategorie {', '.join(nz['kategorien'])}) sind in keiner Summe enthalten. "
            "Bitte der Kategorie eine gültige EÜR-Zeile zuordnen.", fill=True, align="L")

    pdf.ln(3)
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("DejaVu", "B", 10)
    pdf.set_x(20)
    g = daten["gewinn_verlust"]
    label = "Gewinn" if g >= 0 else "Verlust"
    pdf.cell(135, 8, f"  {label}", fill=True, align="L")
    pdf.cell(35, 8, euro(g), fill=True, align="R")
    pdf.ln(10)

    if daten["anlage_zugaenge"] > 0:
        pdf.set_fill_color(254, 243, 199)
        pdf.set_x(20)
        pdf.set_font("DejaVu", "", 8)
        pdf.set_text_color(120, 80, 0)
        pdf.multi_cell(170, 5,
            f"Anlagezugänge {daten['jahr']}: {euro(daten['anlage_zugaenge'])} (KFZ, EDV etc.) sind nicht enthalten. "
            "Bitte Anlage AVEÜR (Abschreibungsplan) separat ausfüllen.", fill=True, align="L")
        pdf.ln(4)

    pdf.set_fill_color(254, 243, 199)
    pdf.set_x(20)
    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(120, 80, 0)
    pdf.multi_cell(170, 5,
        "Hinweis: Anzeigehilfe auf Basis von Journalbuchungen (Ist-Versteuerung / Zuflussprinzip). "
        "Bitte Werte in ELSTER oder mit dem Steuerberater übertragen.", fill=True, align="L")

    pdf.set_y(-15)
    pdf.set_font("DejaVu", "", 7)
    pdf.set_text_color(*MITTEL)
    pdf.cell(85, 5, f"Erstellt mit RechnungsFee  ·  {name[:40]}", align="L")
    pdf.cell(85, 5, f"Wirtschaftsjahr {daten['jahr']}", align="R")

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Kategorie-Aufschlüsselung
# ---------------------------------------------------------------------------

def _euer_kategorien_beitraege(
    jahr: int, db: Session
) -> dict[int, dict[str, list[tuple[Decimal, Journaleintrag]]]]:
    """Gleiche Logik wie _berechne_euer, aber gruppiert nach (euer_zeile, kategorie_name) mit
    den einzelnen Beiträgen (Beitrag, Journaleintrag). Basis für die Kategorie-Summen
    (_berechne_euer_kategorien) und die Einzelposten der Aufschlüsselung (Rechnungs- und
    Zahlungsnummer mit Link)."""
    unt = db.query(Unternehmen).first()
    von, bis = wirtschaftsjahr_zeitraum(unt, jahr) if unt else (date(jahr, 1, 1), date(jahr, 12, 31))

    eintraege = (
        db.query(Journaleintrag)
        .filter(Journaleintrag.datum >= von, Journaleintrag.datum <= bis)
        .all()
    )

    zeilen: dict[int, dict[str, list[tuple[Decimal, Journaleintrag]]]] = {}

    def add(zeile: int, kat_name: str, beitrag: Decimal, e: Journaleintrag) -> None:
        zeilen.setdefault(zeile, {})
        zeilen[zeile].setdefault(kat_name, [])
        zeilen[zeile][kat_name].append((beitrag, e))

    for e in eintraege:
        kat: Optional[Kategorie] = e.kategorie
        kat_name = kat.name if kat else "Unbekannt"

        if kat and kat.kontenart == "Anlage":
            continue

        haupt_zeile, haupt_beitrag = _euer_haupt_beitrag(e)
        if haupt_zeile is not None:
            add(haupt_zeile, kat_name, haupt_beitrag, e)

        for ust_zeile, ust_kat_name, ust_beitrag in _euer_ust_beitraege(e):
            add(ust_zeile, ust_kat_name, ust_beitrag, e)

    return zeilen


def _berechne_euer_kategorien(jahr: int, db: Session) -> dict[int, dict[str, Decimal]]:
    """Summen je (euer_zeile, kategorie_name) - gleiche Logik wie _berechne_euer."""
    beitraege = _euer_kategorien_beitraege(jahr, db)

    q = Decimal("0.01")
    summen = {
        z: {k: sum((b for b, _ in liste), ZERO).quantize(q, ROUND_HALF_UP) for k, liste in kats.items()}
        for z, kats in beitraege.items()
    }
    return {
        z: {k: v for k, v in kats.items() if v != ZERO}
        for z, kats in summen.items()
        if any(v != ZERO for v in kats.values())
    }


# ---------------------------------------------------------------------------
# Response-Schemas
# ---------------------------------------------------------------------------

class EUERZeile(BaseModel):
    zeile: int
    bezeichnung: str
    abschnitt: str
    betrag: Decimal

class EUERNichtZugeordnet(BaseModel):
    zeile: int
    betrag: Decimal
    kategorien: list[str]

class EUERZeileAuswahl(BaseModel):
    zeile: int
    bezeichnung: str
    abschnitt: str

class EUERErgebnis(BaseModel):
    jahr: int
    zeilen: list[EUERZeile]
    # Issue #470: Beträge auf unbekannten Zeilen (nicht in den Summen enthalten)
    nicht_zugeordnet: list[EUERNichtZugeordnet] = []
    summe_einnahmen: Decimal
    summe_ausgaben: Decimal
    gewinn_verlust: Decimal
    anlage_zugaenge: Decimal
    aveur_afa: Decimal
    ist_kleinunternehmer: bool
    # Issue #470: Zeilennummern im Vordruck des Wirtschaftsjahres (für Summen-/AfA-Hinweise)
    zeile_summe_einnahmen: int = 23
    zeile_summe_ausgaben: int = 75
    zeile_afa: int = 33

class EUERKatBuchung(BaseModel):
    """Einzelposten einer Kategorie in der Aufschlüsselung - Journalbuchung mit
    Rechnungs- und Zahlungsnummer (als Link-Ziel für die Oberfläche)."""
    id: int                       # Journaleintrag-ID (Zahlungsbeleg /journal/{id}/beleg)
    datum: date
    belegnr: str                  # Zahlungs-/Belegnummer der Journalbuchung
    beschreibung: str
    betrag: Decimal               # Beitrag an dieser EÜR-Zeile (vorzeichenkorrigiert)
    rechnung_id: int | None = None
    rechnungsnummer: str | None = None
    # Storno-Bündelung: Original wird mit seiner Gegenbuchung als Paar angezeigt
    storniert: bool = False       # dieses Original hat eine Storno-Gegenbuchung
    storno_belegnr: str | None = None
    ist_storno: bool = False      # dieser Eintrag IST die Storno-Gegenbuchung
    storno_von_belegnr: str | None = None

class EUERKatSumme(BaseModel):
    name: str
    betrag: Decimal
    buchungen: list[EUERKatBuchung] = []

class EUERZeileDetail(BaseModel):
    zeile: int
    bezeichnung: str
    abschnitt: str
    betrag_gesamt: Decimal
    kategorien: list[EUERKatSumme]

class EUERDetailErgebnis(BaseModel):
    jahr: int
    zeilen: list[EUERZeileDetail]


# ---------------------------------------------------------------------------
# Endpunkte
# ---------------------------------------------------------------------------

@router.get("/zeilen", response_model=list[EUERZeileAuswahl])
def euer_zeilen():
    return euer_zeilen_auswahl()


@router.get("/berechnen", response_model=EUERErgebnis)
def euer_berechnen(
    jahr: int = Query(..., ge=2020, le=2100),
    db: Session = Depends(get_db),
):
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(404, "Unternehmensdaten nicht gefunden.")

    daten = _berechne_euer(jahr, db)

    zeilen_liste = [
        EUERZeile(
            zeile=formular_zeile(z, daten["jahr"]),
            bezeichnung=EUR_ZEILEN_META[z][0] if z in EUR_ZEILEN_META else f"Zeile {z}",
            abschnitt=EUR_ZEILEN_META[z][1] if z in EUR_ZEILEN_META else "?",
            betrag=betrag,
        )
        # unbekannte Zeilen stehen gesondert in nicht_zugeordnet (Issue #470)
        for z, betrag in sorted(daten["zeilen"].items()) if z in EUR_ZEILEN_META
    ]

    return EUERErgebnis(
        jahr=daten["jahr"],
        zeilen=zeilen_liste,
        nicht_zugeordnet=daten["nicht_zugeordnet"],
        summe_einnahmen=daten["summe_einnahmen"],
        summe_ausgaben=daten["summe_ausgaben"],
        gewinn_verlust=daten["gewinn_verlust"],
        anlage_zugaenge=daten["anlage_zugaenge"],
        aveur_afa=daten["aveur_afa"],
        ist_kleinunternehmer=bool(unt.ist_kleinunternehmer),
        zeile_summe_einnahmen=formular_zeile(ZEILE_SUMME_EINNAHMEN, daten["jahr"]),
        zeile_summe_ausgaben=formular_zeile(ZEILE_SUMME_AUSGABEN, daten["jahr"]),
        zeile_afa=formular_zeile(ZEILE_AFA_BEWEGLICH, daten["jahr"]),
    )


@router.get("/kategorien", response_model=EUERDetailErgebnis)
def euer_kategorien(
    jahr: int = Query(..., ge=2020, le=2100),
    db: Session = Depends(get_db),
):
    beitraege = _euer_kategorien_beitraege(jahr, db)
    kat_daten = _berechne_euer_kategorien(jahr, db)
    euer_daten = _berechne_euer(jahr, db)

    q = Decimal("0.01")

    def buchungen_fuer(zeile: int, kat_name: str) -> list[EUERKatBuchung]:
        """Einzelposten einer Kategorie, chronologisch mit Belegnummer. Storno-Paarung
        über dieselbe Erkennung wie im Journal (STORNO-Präfix + gruppe_id-Wurzel)."""
        liste = beitraege.get(zeile, {}).get(kat_name, [])
        storno_infos = _storno_infos(db, [e for _, e in liste])
        return [
            EUERKatBuchung(
                id=e.id,
                datum=e.datum,
                belegnr=e.belegnr,
                beschreibung=e.beschreibung,
                betrag=b.quantize(q, ROUND_HALF_UP),
                rechnung_id=e.rechnung_id,
                rechnungsnummer=e.rechnung.rechnungsnummer if e.rechnung else None,
                storniert=storno_infos[e.id]["storniert"],
                storno_belegnr=storno_infos[e.id]["storno_belegnr"],
                ist_storno=storno_infos[e.id]["ist_storno"],
                storno_von_belegnr=storno_infos[e.id]["storno_von_belegnr"],
            )
            for b, e in sorted(liste, key=lambda t: (t[1].datum, t[1].belegnr))
            if b != ZERO
        ]

    zeilen_liste = []
    for z, kats in sorted(kat_daten.items()):
        betrag_gesamt = euer_daten["zeilen"].get(z, ZERO)
        zeilen_liste.append(EUERZeileDetail(
            zeile=formular_zeile(z, jahr),
            bezeichnung=EUR_ZEILEN_META[z][0] if z in EUR_ZEILEN_META else f"Zeile {z}",
            abschnitt=EUR_ZEILEN_META[z][1] if z in EUR_ZEILEN_META else "?",
            betrag_gesamt=betrag_gesamt,
            kategorien=[
                EUERKatSumme(name=k, betrag=v, buchungen=buchungen_fuer(z, k))
                for k, v in sorted(kats.items(), key=lambda x: abs(x[1]), reverse=True)
            ],
        ))

    return EUERDetailErgebnis(jahr=jahr, zeilen=zeilen_liste)


@router.get("/pdf")
def euer_pdf(
    jahr: int = Query(..., ge=2020, le=2100),
    db: Session = Depends(get_db),
):
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(404, "Unternehmensdaten nicht gefunden.")
    daten = _berechne_euer(jahr, db)
    pdf_bytes = _generate_pdf(daten, unt)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="EÜR_{jahr}.pdf"'},
    )
