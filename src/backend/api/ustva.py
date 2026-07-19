"""
UStVA – Umsatzsteuer-Voranmeldung 2026
Berechnet Kennziffern aus dem Journal und exportiert als PDF-Anzeigehilfe.

Zeitraum-Formate:
  Monatlich:       zeitraum=2026-01 … 2026-12
  Vierteljährlich: zeitraum=2026-Q1 … 2026-Q4

KZ-Mapping (konto_ust_skr03/04 → Kennziffer):
  1776 / 3806 → KZ 81      (19% Ausgangsumsatz, Bemessungsgrundlage)
  1771 / 3801 → KZ 86      (7%  Ausgangsumsatz, Bemessungsgrundlage)
  ust_sonderfall="ig_erwerb", je nach ust_satz → KZ 89 (19%) / 93 (7%) / 90 (0%) /
                95+98 (andere Sätze) – jeweils Bemessungsgrundlage, außer 98 (Steuer)
  1583 / 1402 → KZ 61     (Vorsteuer ig. Erwerb, satzunabhängig aggregiert)
  1787        → KZ 84/85  (§13b Abs. 2, Empfänger schuldet)
  1789        → KZ 46/47  (§13b Abs. 1, EU-Dienstleistungen)
  vorsteuer_betrag, art=Ausgabe, andere Konten → KZ 66 (Vorsteuer Inland)

Hinweis: Bei festen Steuersätzen (19%/7%/0%) gibt es laut amtlichem Vordruckmuster
NUR eine Bemessungsgrundlage-Kennzahl – die Steuer wird von ELSTER automatisch daraus
berechnet, nicht separat gemeldet. Nur bei variablen Sätzen (§13b, "andere Steuersätze")
gibt es zusätzlich eine Steuer-Kennzahl. kz_83/kz_88 (Steuer 19%/7% Inland) sind daher
KEINE echten Kennzahlen, sondern nur interne Hilfsgrößen für die Zahllast-Berechnung
(Issue #272).

KZ 41 (EU-Lieferungen steuerfreie Einnahmen) und KZ 87 (Ausfuhr etc.)
können nicht sicher aus dem Journal abgeleitet werden – manuelle Eingabe.
"""

import calendar
import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Journaleintrag, Kategorie, Unternehmen, UstvaExport

router = APIRouter(prefix="/api/ustva", tags=["UStVA"])

ZERO = Decimal("0.00")

# ---------------------------------------------------------------------------
# KZ-Definitionen: Reihenfolge wie im amtlichen Formular USt 1 A 2026
# (abschnitt, kz_nr, bezeichnung, ist_steuer_zeile, auto_berechenbar)
# ist_steuer_zeile: rechte Spalte = USt-Betrag (nicht Bemessungsgrundlage)
# auto_berechenbar: True = aus Journal ableitbar
# ---------------------------------------------------------------------------
KZ_META = [
    ("A. Steuerpflichtige Ausgangsumsätze", "81",
     "Umsätze 19 % – Bemessungsgrundlage", False, True),
    ("", "86", "Umsätze 7 % – Bemessungsgrundlage", False, True),

    ("B. Steuerfreie Umsätze mit Vorsteuerabzug", "41",
     "Innergemeinschaftliche Lieferungen (§4 Nr. 1b) an Abnehmer mit USt-IdNr.", False, False),
    ("", "87",
     "Weitere steuerfreie Umsätze mit Vorsteuerabzug (Ausfuhr, §4 Nr. 2–7 UStG)", False, False),

    ("C. Innergemeinschaftliche Erwerbe", "89",
     "Steuerpflichtige Erwerbe 19 % – Bemessungsgrundlage", False, True),
    ("", "93", "Steuerpflichtige Erwerbe 7 % – Bemessungsgrundlage", False, True),
    ("", "90", "Steuerpflichtige Erwerbe 0 % – Bemessungsgrundlage", False, True),
    ("", "95", "Steuerpflichtige Erwerbe zu anderen Steuersätzen – Bemessungsgrundlage", False, True),
    ("", "98", "Umsatzsteuer zu anderen Steuersätzen (ig. Erwerb)", True, True),

    ("D. Leistungsempfänger als Steuerschuldner (§13b UStG)", "46",
     "Sonstige Leistungen EU-Unternehmer (§13b Abs. 1 UStG)", False, True),
    ("", "47", "Umsatzsteuer §13b Abs. 1", True, True),
    ("", "84",
     "Andere §13b-Leistungen (Abs. 2 Nr. 1, 2, 4–12 UStG)", False, True),
    ("", "85", "Umsatzsteuer §13b Abs. 2", True, True),

    ("F. Abziehbare Vorsteuerbeträge", "66",
     "Vorsteuer aus Rechnungen (§15 Abs. 1 Satz 1 Nr. 1 UStG)", False, True),
    ("", "61",
     "Vorsteuer ig. Erwerb (§15 Abs. 1 Satz 1 Nr. 3 UStG)", False, True),
    ("", "67",
     "Vorsteuer aus §13b-Leistungen (§15 Abs. 1 Satz 1 Nr. 4 UStG)", False, True),
]

# USt-Konto → (Bemessungsgrundlage-KZ, Steuer-KZ) für Einnahmen
_KONTO_EINNAHME: dict[str, tuple[str, str]] = {
    "1776": ("kz_81", "kz_83"), "3806": ("kz_81", "kz_83"),  # 19%
    "1771": ("kz_86", "kz_88"), "3801": ("kz_86", "kz_88"),  # 7%
    "1780": ("kz_89", "kz_93"),                               # ig. Erwerb 19%
    "1787": ("kz_84", "kz_85"),                               # §13b Abs. 2
    "1789": ("kz_46", "kz_47"),                               # §13b Abs. 1 (EU-DL)
}

# USt-Konto → Vorsteuer-KZ für Ausgaben
_KONTO_AUSGABE_VST: dict[str, str] = {
    "1583": "kz_61", "1402": "kz_61",   # Vorsteuer ig. Erwerb
    "1787": "kz_67", "1789": "kz_67",   # Vorsteuer §13b
}

# kz_83/kz_88 sind KEINE eigenständig meldepflichtigen Kennzahlen (bei festen Steuersätzen
# berechnet ELSTER die Steuer automatisch aus der Bemessungsgrundlage) – daher nicht in
# KZ_META/Anzeige, aber intern für die Zahllast-Berechnung weiter benötigt.
ALL_KZ_KEYS = [f"kz_{m[1]}" for m in KZ_META] + ["kz_83", "kz_88", "zahllast"]


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _zeitraum_grenzen(zeitraum: str) -> tuple[date, date, str]:
    if "-Q" in zeitraum:
        try:
            jahr_s, q_s = zeitraum.split("-Q")
            jahr, q = int(jahr_s), int(q_s)
            if q not in (1, 2, 3, 4):
                raise ValueError
            von_monat = (q - 1) * 3 + 1
            bis_monat = von_monat + 2
            von = date(jahr, von_monat, 1)
            bis = date(jahr, bis_monat, calendar.monthrange(jahr, bis_monat)[1])
            return von, bis, "quartalsweise"
        except (ValueError, AttributeError):
            raise HTTPException(422, f"Ungültiges Quartal: '{zeitraum}'")
    else:
        try:
            jahr_s, mon_s = zeitraum.split("-")
            jahr, monat = int(jahr_s), int(mon_s)
            if not (1 <= monat <= 12):
                raise ValueError
            von = date(jahr, monat, 1)
            bis = date(jahr, monat, calendar.monthrange(jahr, monat)[1])
            return von, bis, "monatlich"
        except (ValueError, AttributeError):
            raise HTTPException(422, f"Ungültiges Zeitraum-Format: '{zeitraum}'")


def _berechne_kz(von: date, bis: date, db: Session) -> dict[str, Decimal]:
    eintraege = (
        db.query(Journaleintrag)
        .filter(Journaleintrag.datum >= von, Journaleintrag.datum <= bis)
        .all()
    )

    # Lookup-Cache: belegnr → marge_25a_brutto (für Storno-Fallback bei alten Einträgen)
    _marge_cache: dict[str, Decimal | None] = {}

    kz: dict[str, Decimal] = {k: ZERO for k in ALL_KZ_KEYS}
    # Interne Hilfssumme: tatsächliche Steuer aus ig. Erwerb zu festen Sätzen (19%/7%/0%).
    # Keine eigene Kennzahl (die Steuer wird bei festen Sätzen nicht separat gemeldet,
    # siehe KZ_META-Kommentar) – wird nur für die Zahllast-Berechnung gebraucht (Issue #272).
    ige_steuer_feste_saetze = ZERO

    for e in eintraege:
        ust_konto = e.konto_ust_skr03 or e.konto_ust_skr04 or ""

        # Reverse-Charge-Sonderfälle: separat behandeln, nicht in reguläre KZs
        sf = getattr(e, "ust_sonderfall", None) or ("ig_erwerb" if getattr(e, "ist_ig_erwerb", False) else None)
        if sf:
            if sf == "ig_erwerb":
                # Bemessungsgrundlage nach TATSÄCHLICHEM Steuersatz der Buchung einsortieren –
                # nicht mehr pauschal in kz_89 (Issue #272: 7%-Buchungen landeten fälschlich
                # dort, mit dem Steuerbetrag statt der Bemessungsgrundlage).
                satz_i = int(e.ust_satz) if e.ust_satz is not None else None
                if satz_i == 19:
                    kz["kz_89"] += e.netto_betrag
                    ige_steuer_feste_saetze += e.ust_betrag
                elif satz_i == 7:
                    kz["kz_93"] += e.netto_betrag
                    ige_steuer_feste_saetze += e.ust_betrag
                elif satz_i == 0:
                    kz["kz_90"] += e.netto_betrag
                else:
                    # Andere Steuersätze: Bemessungsgrundlage UND Steuer sind laut Formular
                    # getrennt zu melden (KZ 95/98), da der Satz nicht fest vorgegeben ist.
                    kz["kz_95"] += e.netto_betrag
                    kz["kz_98"] += e.ust_betrag
                if e.vorsteuer_betrag:
                    kz["kz_61"] += e.vorsteuer_betrag
            elif sf == "13b_abs1":
                kz["kz_46"] += e.netto_betrag
                kz["kz_47"] += e.ust_betrag
                if e.vorsteuer_betrag:
                    kz["kz_67"] += e.vorsteuer_betrag
            elif sf == "13b_abs2":
                kz["kz_84"] += e.netto_betrag
                kz["kz_85"] += e.ust_betrag
                if e.vorsteuer_betrag:
                    kz["kz_67"] += e.vorsteuer_betrag
            continue  # nicht in reguläre USt/VSt-Erkennung

        if e.art == "Einnahme" and e.ust_betrag and e.ust_betrag != 0:
            mapping = _KONTO_EINNAHME.get(ust_konto)
            if mapping:
                # §25a: Bemessungsgrundlage = Netto-Marge (Brutto-Marge − USt), nicht Netto-VK
                marge = getattr(e, "marge_25a_brutto", None)
                kz[mapping[0]] += (marge - e.ust_betrag) if marge is not None else e.netto_betrag
                kz[mapping[1]] += e.ust_betrag

        # Storno einer Einnahme: art ist "Ausgabe" (umgekehrt), konto_ust_skr ist Einnahme-Konto.
        # Muss Ausgangsumsätze (KZ 81/83 etc.) reduzieren – sonst bleibt der Original-Umsatz
        # stehen und der Storno ist in der UStVA unsichtbar.
        # Skonto-Einträge (zahlungsart == "Skonto") ausschließen: der Zahlungseingang (brutto)
        # enthält bereits den reduzierten Betrag (Zuflussprinzip / Ist-Versteuerung) – eine
        # zusätzliche Kürzung durch den Skonto-Gegeneintrag würde KZ 81/83 doppelt mindern.
        if e.art == "Ausgabe" and e.ust_betrag and e.ust_betrag != 0 and e.zahlungsart != "Skonto":
            mapping = _KONTO_EINNAHME.get(ust_konto)
            if mapping:
                # §25a: Storno muss marge_25a_brutto verwenden (wie Einnahme-Pfad),
                # nicht netto_betrag – sonst wird mehr aus KZ 81 subtrahiert als addiert wurde.
                marge_st = getattr(e, "marge_25a_brutto", None)
                if marge_st is None and e.beschreibung and e.beschreibung.startswith("STORNO "):
                    # Fallback für alte Storno-Einträge ohne marge_25a_brutto:
                    # belegnr des Originals aus "STORNO <belegnr>: ..." parsen
                    try:
                        orig_belegnr = e.beschreibung.split(":")[0].removeprefix("STORNO ").strip()
                        if orig_belegnr not in _marge_cache:
                            orig = db.query(Journaleintrag).filter(
                                Journaleintrag.belegnr == orig_belegnr
                            ).first()
                            _marge_cache[orig_belegnr] = getattr(orig, "marge_25a_brutto", None) if orig else None
                        marge_st = _marge_cache[orig_belegnr]
                    except Exception:
                        pass
                kz[mapping[0]] -= marge_st if marge_st else e.netto_betrag
                kz[mapping[1]] -= e.ust_betrag

        # KZ 41 – ig. Lieferungen: 0% USt, Erkennung via konto_skr03 8125/3125
        if (e.art == "Einnahme"
                and (e.konto_skr03 in ("8125",) or e.konto_skr04 in ("3125",))
                and e.steuerbefreiung_grund == "§4 Nr. 1b UStG"):
            kz["kz_41"] += e.netto_betrag

        # Ausgabe-Vorsteuer → KZ 66/61/67.
        # Storno einer Einnahme hat ebenfalls art=Ausgabe, aber konto_ust ist ein Einnahme-Konto
        # → ausschließen, damit kein falscher Vorsteuer-Eintrag entsteht.
        if e.art == "Ausgabe" and e.vorsteuer_betrag and e.vorsteuer_betrag != 0:
            if not _KONTO_EINNAHME.get(ust_konto):
                vst_kz = _KONTO_AUSGABE_VST.get(ust_konto, "kz_66")
                kz[vst_kz] += e.vorsteuer_betrag

        # Storno einer Ausgabe: art ist "Einnahme" (umgekehrt), vorsteuer_betrag ist negativ.
        # Muss Vorsteuer (KZ 66 etc.) reduzieren – sonst bleibt die Original-Vorsteuer stehen.
        if e.art == "Einnahme" and e.vorsteuer_betrag and e.vorsteuer_betrag < 0:
            vst_kz = _KONTO_AUSGABE_VST.get(ust_konto, "kz_66")
            kz[vst_kz] += e.vorsteuer_betrag  # negativer Wert → reduziert KZ

    q = Decimal("0.01")
    for k in kz:
        if k != "zahllast":
            kz[k] = kz[k].quantize(q, ROUND_HALF_UP)

    # kz_98 (ig. Erwerb andere Sätze) ist eine echte Steuer-Kennzahl, kz_83/kz_88 (Inland
    # 19%/7%) und ige_steuer_feste_saetze (ig. Erwerb 19%/7%/0%) sind interne Hilfsgrößen
    # ohne eigene Kennzahl (siehe KZ_META-Kommentar).
    ust = (kz["kz_83"] + kz["kz_88"] + kz["kz_98"] + kz["kz_47"] + kz["kz_85"]
           + ige_steuer_feste_saetze.quantize(q, ROUND_HALF_UP))
    vst = kz["kz_66"] + kz["kz_61"] + kz["kz_67"]
    kz["zahllast"] = (ust - vst).quantize(q, ROUND_HALF_UP)
    return kz


def _zeitraum_label(zeitraum: str) -> str:
    MONATE = ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
              "Juli", "August", "September", "Oktober", "November", "Dezember"]
    if "-Q" in zeitraum:
        jahr, q = zeitraum.split("-Q")
        return f"Q{q}/{jahr}"
    try:
        jahr, monat = zeitraum.split("-")
        return f"{MONATE[int(monat)]} {jahr}"
    except Exception:
        return zeitraum


# ---------------------------------------------------------------------------
# PDF-Anzeigehilfe
# ---------------------------------------------------------------------------

def _generate_pdf(zeitraum: str, kz: dict, unt: Unternehmen) -> bytes:
    from fpdf import FPDF

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
        ]:
            if (p / "DejaVuSans.ttf").exists():
                return p
        raise FileNotFoundError("DejaVu-Fonts nicht gefunden.")

    BLAU   = (37, 99, 235)
    GRAU   = (245, 246, 248)
    DUNKEL = (30, 41, 59)
    MITTEL = (100, 116, 139)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    fonts = _find_dejavu_dir()
    pdf.add_font("DejaVu", "",  str(fonts / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(fonts / "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(True, margin=20)

    # Kopfzeile
    pdf.set_fill_color(*BLAU)
    pdf.rect(0, 0, 210, 18, "F")
    pdf.set_font("DejaVu", "B", 11)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(20, 5)
    pdf.cell(0, 8, "Umsatzsteuer-Voranmeldung 2026 – Anzeigehilfe", ln=True, align="L")
    pdf.set_text_color(*DUNKEL)

    pdf.set_xy(20, 24)
    pdf.set_font("DejaVu", "B", 14)
    pdf.cell(0, 8, _zeitraum_label(zeitraum), ln=True, align="L")

    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(*MITTEL)
    name = unt.firmenname or f"{unt.vorname or ''} {unt.nachname or ''}".strip()
    pdf.cell(0, 5,
        f"{name}  ·  Steuernummer: {unt.steuernummer or '—'}  ·  Finanzamt: {unt.finanzamt or '—'}",
        ln=True, align="L")
    if unt.w_idnr:
        pdf.cell(0, 5, f"Wirtschafts-IdNr. (Zeile 1): {unt.w_idnr}", ln=True, align="L")
    pdf.ln(4)

    def euro(v: Decimal) -> str:
        neg = v < 0
        s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
        return f"− {s}" if neg else s

    def kz_row(kz_nr: str, bezeichnung: str, wert: Decimal, ist_steuer: bool = False, bold: bool = False):
        y = pdf.get_y()
        h = 7
        pdf.set_fill_color(*BLAU)
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(20, y)
        pdf.cell(12, h, kz_nr, border=0, fill=True, align="C")

        font_size = 8 if ist_steuer else 9
        pdf.set_font("DejaVu", "B" if bold else "", font_size)
        pdf.set_text_color(MITTEL if ist_steuer else DUNKEL)
        pdf.set_xy(34, y)
        pdf.cell(120, h, bezeichnung, border=0, align="L")

        color = (220, 38, 38) if wert < 0 else DUNKEL
        pdf.set_text_color(*color)
        pdf.set_font("DejaVu", "B" if bold else "", 9)
        pdf.set_xy(155, y)
        pdf.cell(35, h, euro(wert), align="R", border=0)
        pdf.ln(h + 1)

    def section(titel: str):
        pdf.set_fill_color(229, 231, 235)
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_text_color(*DUNKEL)
        pdf.set_x(20)
        pdf.cell(170, 6, f"  {titel}", fill=True, ln=True, align="L")
        pdf.ln(1)

    # Nur Zeilen mit Wert ≠ 0 rendern, Abschnitte bei Bedarf
    letzter_abschnitt = None
    for (abschnitt, kz_nr, bezeichnung, ist_steuer, _auto) in KZ_META:
        key = f"kz_{kz_nr}"
        wert = kz.get(key, ZERO)
        if wert == ZERO:
            continue
        eff_abschnitt = abschnitt if abschnitt else letzter_abschnitt
        if eff_abschnitt != letzter_abschnitt:
            if letzter_abschnitt is not None:
                pdf.ln(2)
            section(eff_abschnitt)
            letzter_abschnitt = eff_abschnitt
        kz_row(kz_nr, bezeichnung, wert, ist_steuer=ist_steuer)

    # Zahllast immer anzeigen
    pdf.ln(2)
    section("H. Vorauszahlung / Überschuss")
    zahllast = kz.get("zahllast", ZERO)
    label = "Verbleibender Überschuss (Erstattung)" if zahllast < 0 else "Umsatzsteuer-Vorauszahlung"
    kz_row("—", label, zahllast, bold=True)
    pdf.ln(4)

    # Hinweis
    pdf.set_fill_color(254, 243, 199)
    pdf.set_x(20)
    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(120, 80, 0)
    pdf.multi_cell(170, 5,
        "Hinweis: Dieses Dokument ist eine Anzeigehilfe und kein amtliches Formular. "
        "Bitte übertrage die Kennziffern in ELSTER (www.elster.de) oder übergib sie "
        "deinem Steuerberater. Grundlage: Journalbuchungen nach Ist-Versteuerung "
        "(Zahlungsdatum). Bei Soll-Versteuerung ggf. abweichend. "
        "Nicht automatisch berechnete Felder (z.B. EU-Lieferungen KZ 41) müssen "
        "manuell eingetragen werden.",
        fill=True, align="L"
    )

    # Fußzeile
    pdf.set_y(-15)
    pdf.set_font("DejaVu", "", 7)
    pdf.set_text_color(*MITTEL)
    name_kurz = (unt.firmenname or f"{unt.vorname or ''} {unt.nachname or ''}".strip())[:40]
    pdf.cell(85, 5, f"Erstellt mit RechnungsFee  ·  {name_kurz}", align="L")
    pdf.cell(85, 5, _zeitraum_label(zeitraum), align="R")

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Response-Schema
# ---------------------------------------------------------------------------

class UStVAErgebnis(BaseModel):
    zeitraum: str
    zeitraum_typ: str
    von: date
    bis: date
    # A – Ausgangsumsätze
    kz_81: Decimal = ZERO
    kz_83: Decimal = ZERO
    kz_86: Decimal = ZERO
    kz_88: Decimal = ZERO
    # B – Steuerfreie Umsätze (manuell)
    kz_41: Decimal = ZERO
    kz_87: Decimal = ZERO
    # C – ig. Erwerb
    kz_89: Decimal = ZERO
    kz_93: Decimal = ZERO
    kz_90: Decimal = ZERO
    kz_95: Decimal = ZERO
    kz_98: Decimal = ZERO
    # D – §13b
    kz_46: Decimal = ZERO
    kz_47: Decimal = ZERO
    kz_84: Decimal = ZERO
    kz_85: Decimal = ZERO
    # F – Vorsteuer
    kz_66: Decimal = ZERO
    kz_61: Decimal = ZERO
    kz_67: Decimal = ZERO
    zahllast: Decimal = ZERO
    ist_kleinunternehmer: bool = False
    hinweis: Optional[str] = None


class UStVASpeichernRequest(BaseModel):
    zeitraum: str
    kz_81: Decimal = ZERO
    kz_83: Decimal = ZERO
    kz_86: Decimal = ZERO
    kz_88: Decimal = ZERO
    kz_41: Decimal = ZERO
    kz_87: Decimal = ZERO
    kz_89: Decimal = ZERO
    kz_93: Decimal = ZERO
    kz_90: Decimal = ZERO
    kz_95: Decimal = ZERO
    kz_98: Decimal = ZERO
    kz_46: Decimal = ZERO
    kz_47: Decimal = ZERO
    kz_84: Decimal = ZERO
    kz_85: Decimal = ZERO
    kz_66: Decimal = ZERO
    kz_61: Decimal = ZERO
    kz_67: Decimal = ZERO
    zahllast: Decimal = ZERO


# ---------------------------------------------------------------------------
# Endpunkte
# ---------------------------------------------------------------------------

@router.get("/berechnen", response_model=UStVAErgebnis)
def ustva_berechnen(
    zeitraum: str = Query(..., description="YYYY-MM oder YYYY-QN"),
    db: Session = Depends(get_db),
):
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(404, "Unternehmensdaten nicht gefunden.")

    von, bis, typ = _zeitraum_grenzen(zeitraum)
    ist_ku = bool(unt.ist_kleinunternehmer)

    if ist_ku:
        kz: dict = {k: ZERO for k in ALL_KZ_KEYS}
        hinweis = ("Als Kleinunternehmer nach §19 UStG bist du von der UStVA befreit. "
                   "Umsätze werden in Zeile 23 (KZ 48) als steuerfreie Umsätze ohne "
                   "Vorsteuerabzug eingetragen – nur einmal jährlich in der Jahressteuererklärung.")
    else:
        kz = _berechne_kz(von, bis, db)
        hinweis = None

    return UStVAErgebnis(
        zeitraum=zeitraum, zeitraum_typ=typ, von=von, bis=bis,
        ist_kleinunternehmer=ist_ku, hinweis=hinweis,
        **{k: v for k, v in kz.items() if k != "zahllast"},
        zahllast=kz["zahllast"],
    )


@router.post("/speichern")
def ustva_speichern(req: UStVASpeichernRequest, db: Session = Depends(get_db)):
    _zeitraum_grenzen(req.zeitraum)
    eintrag = db.query(UstvaExport).filter(UstvaExport.zeitraum == req.zeitraum).first()
    if not eintrag:
        eintrag = UstvaExport(zeitraum=req.zeitraum)
        db.add(eintrag)
    _, _, typ = _zeitraum_grenzen(req.zeitraum)
    eintrag.zeitraum_typ = typ
    eintrag.kz_81 = req.kz_81; eintrag.kz_83 = req.kz_83
    eintrag.kz_86 = req.kz_86; eintrag.kz_88 = req.kz_88
    eintrag.kz_66 = req.kz_66; eintrag.kz_41 = req.kz_41
    eintrag.zahllast = req.zahllast
    eintrag.daten_json = json.dumps({k: str(v) for k, v in req.model_dump().items()})
    db.commit()
    return {"ok": True, "zeitraum": req.zeitraum}


@router.get("/historie")
def ustva_historie(db: Session = Depends(get_db)):
    eintraege = db.query(UstvaExport).order_by(UstvaExport.zeitraum.desc()).all()
    return [
        {"zeitraum": e.zeitraum, "zeitraum_typ": e.zeitraum_typ,
         "zahllast": float(e.zahllast), "erstellt_am": e.erstellt_am.isoformat()}
        for e in eintraege
    ]


@router.get("/pdf")
def ustva_pdf(
    zeitraum: str = Query(...),
    db: Session = Depends(get_db),
):
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(404, "Unternehmensdaten nicht gefunden.")
    von, bis, _ = _zeitraum_grenzen(zeitraum)
    kz = _berechne_kz(von, bis, db)
    pdf_bytes = _generate_pdf(zeitraum, kz, unt)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="UStVA_{zeitraum}.pdf"'},
    )


# ===========================================================================
# Jahresumsatzsteuererklärung (USt 2A / Anlage UR)
# ===========================================================================

class JahresUStVAErgebnis(BaseModel):
    jahr: int
    von: date
    bis: date
    ist_kleinunternehmer: bool
    # Reguläre KZs – identisch mit den Voranmeldungs-KZs, Jahressumme aus Journal
    kz_81: Decimal = ZERO; kz_83: Decimal = ZERO
    kz_86: Decimal = ZERO; kz_88: Decimal = ZERO
    kz_41: Decimal = ZERO; kz_87: Decimal = ZERO
    kz_89: Decimal = ZERO; kz_93: Decimal = ZERO
    kz_90: Decimal = ZERO; kz_95: Decimal = ZERO; kz_98: Decimal = ZERO
    kz_46: Decimal = ZERO; kz_47: Decimal = ZERO
    kz_84: Decimal = ZERO; kz_85: Decimal = ZERO
    kz_66: Decimal = ZERO; kz_61: Decimal = ZERO; kz_67: Decimal = ZERO
    zahllast: Decimal = ZERO
    # §19 Kleinunternehmer: Brutto-Umsätze ohne USt-Ausweis (Zeile 23)
    kz_48: Decimal = ZERO
    # Vorauszahlungsanrechnung (aus gespeicherten Voranmeldungen)
    summe_vorauszahlungen: Decimal = ZERO
    restschuld: Decimal = ZERO          # positiv = Nachzahlung, negativ = Erstattung
    gespeicherte_perioden: int = 0
    hat_ig_transaktionen: bool = False  # → Anlage UR erforderlich


def _berechne_ku_kz48(von: date, bis: date, db: Session) -> Decimal:
    """KZ 48: §19-Umsätze (Kleinunternehmer). Brutto-Einnahmen ohne Privateinlagen (euer_zeile=107)."""
    eintraege = (
        db.query(Journaleintrag)
        .outerjoin(Kategorie, Journaleintrag.kategorie_id == Kategorie.id)
        .filter(
            Journaleintrag.datum >= von,
            Journaleintrag.datum <= bis,
            Journaleintrag.art == "Einnahme",
            Journaleintrag.zahlungsart != "Skonto",
            # Privateinlagen (euer_zeile=107) ausschließen
            or_(
                Journaleintrag.kategorie_id.is_(None),
                Kategorie.euer_zeile.is_(None),
                Kategorie.euer_zeile != 107,
            ),
        )
        .all()
    )
    total = sum(Decimal(str(e.brutto_betrag or 0)) for e in eintraege)
    return total.quantize(Decimal("0.01"), ROUND_HALF_UP)


def _generate_pdf_jahres(jahr: int, ergebnis: JahresUStVAErgebnis, unt: Unternehmen) -> bytes:
    from fpdf import FPDF

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
        ]:
            if (p / "DejaVuSans.ttf").exists():
                return p
        raise FileNotFoundError("DejaVu-Fonts nicht gefunden.")

    BLAU   = (37, 99, 235)
    DUNKEL = (30, 41, 59)
    MITTEL = (100, 116, 139)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    fonts = _find_dejavu_dir()
    pdf.add_font("DejaVu", "",  str(fonts / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(fonts / "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(True, margin=20)

    # Kopfzeile
    pdf.set_fill_color(*BLAU)
    pdf.rect(0, 0, 210, 18, "F")
    pdf.set_font("DejaVu", "B", 11)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(20, 5)
    pdf.cell(0, 8, f"Jahresumsatzsteuererklärung {jahr} – Anzeigehilfe (USt 2A)", ln=True, align="L")
    pdf.set_text_color(*DUNKEL)

    pdf.set_xy(20, 24)
    pdf.set_font("DejaVu", "B", 14)
    pdf.cell(0, 8, f"Wirtschaftsjahr {jahr}", ln=True, align="L")

    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(*MITTEL)
    name = unt.firmenname or f"{unt.vorname or ''} {unt.nachname or ''}".strip()
    pdf.cell(0, 5,
        f"{name}  ·  Steuernummer: {unt.steuernummer or '—'}  ·  Finanzamt: {unt.finanzamt or '—'}",
        ln=True, align="L")
    if unt.w_idnr:
        pdf.cell(0, 5, f"Wirtschafts-IdNr. (Zeile 1): {unt.w_idnr}", ln=True, align="L")
    pdf.ln(4)

    def euro(v: Decimal) -> str:
        neg = v < 0
        s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
        return f"− {s}" if neg else s

    def kz_row(kz_nr: str, bezeichnung: str, wert: Decimal, ist_steuer: bool = False, bold: bool = False):
        y = pdf.get_y()
        h = 7
        chip_color = (71, 85, 105) if bold else BLAU
        pdf.set_fill_color(*chip_color)
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(20, y)
        pdf.cell(12, h, kz_nr, border=0, fill=True, align="C")
        font_size = 8 if ist_steuer else 9
        pdf.set_font("DejaVu", "B" if bold else "", font_size)
        pdf.set_text_color(MITTEL if ist_steuer else DUNKEL)
        pdf.set_xy(34, y)
        pdf.cell(120, h, bezeichnung, border=0, align="L")
        color = (220, 38, 38) if wert < 0 else DUNKEL
        pdf.set_text_color(*color)
        pdf.set_font("DejaVu", "B" if bold else "", 9)
        pdf.set_xy(155, y)
        pdf.cell(35, h, euro(wert), align="R", border=0)
        pdf.ln(h + 1)

    def section(titel: str):
        pdf.set_fill_color(229, 231, 235)
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_text_color(*DUNKEL)
        pdf.set_x(20)
        pdf.cell(170, 6, f"  {titel}", fill=True, ln=True, align="L")
        pdf.ln(1)

    if ergebnis.ist_kleinunternehmer:
        section("Kleinunternehmer §19 UStG")
        kz_row("48", "Umsätze, für die als KU keine USt geschuldet wird (§19 Abs. 1 UStG)", ergebnis.kz_48, bold=True)
        pdf.ln(2)
        pdf.set_fill_color(219, 234, 254)
        pdf.set_x(20)
        pdf.set_font("DejaVu", "", 8)
        pdf.set_text_color(30, 64, 175)
        pdf.multi_cell(170, 5,
            f"Dein Gesamtumsatz {jahr}: {euro(ergebnis.kz_48)}. "
            "Als Kleinunternehmer §19 UStG schulde ich keine Umsatzsteuer. "
            "Der Umsatz ist in der Jahressteuererklärung (USt 2A, Zeile 23 / KZ 48) anzugeben, "
            "damit das Finanzamt prüfen kann ob die §19-Grenze eingehalten wurde.",
            fill=True, align="L")
        pdf.ln(4)
    else:
        # Reguläre KZ-Tabelle (nur Zeilen ≠ 0)
        letzter_abschnitt = None
        for (abschnitt, kz_nr, bezeichnung, ist_steuer, _auto) in KZ_META:
            key = f"kz_{kz_nr}"
            wert: Decimal = getattr(ergebnis, key, ZERO)
            if wert == ZERO:
                continue
            eff = abschnitt if abschnitt else letzter_abschnitt
            if eff != letzter_abschnitt:
                if letzter_abschnitt is not None:
                    pdf.ln(2)
                section(eff)
                letzter_abschnitt = eff
            kz_row(kz_nr, bezeichnung, wert, ist_steuer=ist_steuer)

        # Jahressteuer
        pdf.ln(2)
        section("H. Jahressteuer")
        label = "Verbleibender Überschuss (Erstattung)" if ergebnis.zahllast < 0 else "Jahresumsatzsteuer"
        kz_row("—", label, ergebnis.zahllast, bold=True)

        # Vorauszahlungsanrechnung
        if ergebnis.gespeicherte_perioden > 0:
            pdf.ln(2)
            section(f"Vorauszahlungsanrechnung ({ergebnis.gespeicherte_perioden} Voranmeldungen gespeichert)")
            kz_row("76", "Summe der Vorauszahlungen (aus UStVA-Voranmeldungen)", ergebnis.summe_vorauszahlungen)
            restlabel = "Verbleibender Überschuss (Erstattung)" if ergebnis.restschuld < 0 else "Verbleibende Zahllast"
            kz_row("—", restlabel, ergebnis.restschuld, bold=True)
            pdf.ln(2)
            pdf.set_fill_color(254, 243, 199)
            pdf.set_x(20)
            pdf.set_font("DejaVu", "", 8)
            pdf.set_text_color(120, 80, 0)
            pdf.multi_cell(170, 5,
                "Hinweis Vorauszahlungen: Die Summe ergibt sich aus den in RechnungsFee gespeicherten "
                "Voranmeldungen. Wurden nicht alle Zeiträume gespeichert, weicht die Summe ab. "
                "Eine Dauerfristverlängerungs-Sondervorauszahlung muss ggf. manuell ergänzt werden.",
                fill=True, align="L")
        elif not ergebnis.ist_kleinunternehmer:
            pdf.ln(2)
            pdf.set_fill_color(243, 244, 246)
            pdf.set_x(20)
            pdf.set_font("DejaVu", "", 8)
            pdf.set_text_color(*MITTEL)
            pdf.multi_cell(170, 5,
                "Vorauszahlungen: Keine Voranmeldungen in RechnungsFee gespeichert. "
                "Trage deine geleisteten Vorauszahlungen manuell in ELSTER ein (KZ 76).",
                fill=True, align="L")

        # Anlage-UR-Hinweis
        if ergebnis.hat_ig_transaktionen:
            pdf.ln(3)
            pdf.set_fill_color(254, 226, 226)
            pdf.set_x(20)
            pdf.set_font("DejaVu", "B", 8)
            pdf.set_text_color(185, 28, 28)
            pdf.multi_cell(170, 5,
                "Anlage UR erforderlich: Im Journal existieren innergemeinschaftliche Umsätze "
                "(KZ 41/89/93) oder §13b-Leistungen (KZ 46/84). "
                "Die Anlage UR ist separat in ELSTER auszufüllen (Aufschlüsselung nach EU-Ländern).",
                fill=True, align="L")

    pdf.ln(4)
    # Allgemeiner Hinweis
    pdf.set_fill_color(254, 243, 199)
    pdf.set_x(20)
    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(120, 80, 0)
    pdf.multi_cell(170, 5,
        "Dieses Dokument ist eine Anzeigehilfe und kein amtliches Formular. "
        "Übertrage die Kennziffern in ELSTER (www.elster.de) oder übergib sie deinem Steuerberater. "
        "Grundlage: Journalbuchungen nach Ist-Versteuerung (Zahlungsdatum). "
        "Nicht abgedeckt: KZ 62 (Einfuhrumsatzsteuer), KZ 50 (unterjähriger KU-Wechsel), "
        "Reiseleistungen §25 UStG, Durchschnittssatz §23/23a UStG.",
        fill=True, align="L")

    # Fußzeile
    pdf.set_y(-15)
    pdf.set_font("DejaVu", "", 7)
    pdf.set_text_color(*MITTEL)
    name_kurz = name[:40]
    pdf.cell(85, 5, f"Erstellt mit RechnungsFee  ·  {name_kurz}", align="L")
    pdf.cell(85, 5, f"Jahresumsatzsteuererklärung {jahr}", align="R")

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()


@router.get("/jahreserklarung", response_model=JahresUStVAErgebnis)
def jahresumsatzsteuer(
    jahr: int = Query(..., description="Wirtschaftsjahr (z. B. 2026)"),
    db: Session = Depends(get_db),
):
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(404, "Unternehmensdaten nicht gefunden.")

    von = date(jahr, 1, 1)
    bis = date(jahr, 12, 31)
    ist_ku = bool(unt.ist_kleinunternehmer)

    kz_48 = ZERO
    if ist_ku:
        kz: dict[str, Decimal] = {k: ZERO for k in ALL_KZ_KEYS}
        kz_48 = _berechne_ku_kz48(von, bis, db)
    else:
        kz = _berechne_kz(von, bis, db)

    # Gespeicherte Voranmeldungen für Vorauszahlungsanrechnung
    voranmeldungen = (
        db.query(UstvaExport)
        .filter(UstvaExport.zeitraum.like(f"{jahr}-%"))
        .all()
    )
    q = Decimal("0.01")
    summe_voa = sum((Decimal(str(v.zahllast)) for v in voranmeldungen), Decimal("0")).quantize(q, ROUND_HALF_UP)
    jahressteuer = kz["zahllast"]
    restschuld = (jahressteuer - summe_voa).quantize(q, ROUND_HALF_UP)

    hat_ig = any(
        kz.get(k, ZERO) != ZERO
        for k in ["kz_41", "kz_89", "kz_93", "kz_90", "kz_95", "kz_98", "kz_46", "kz_47", "kz_84", "kz_85"]
    )

    return JahresUStVAErgebnis(
        jahr=jahr, von=von, bis=bis, ist_kleinunternehmer=ist_ku,
        kz_81=kz.get("kz_81", ZERO), kz_83=kz.get("kz_83", ZERO),
        kz_86=kz.get("kz_86", ZERO), kz_88=kz.get("kz_88", ZERO),
        kz_41=kz.get("kz_41", ZERO), kz_87=kz.get("kz_87", ZERO),
        kz_89=kz.get("kz_89", ZERO), kz_93=kz.get("kz_93", ZERO),
        kz_90=kz.get("kz_90", ZERO), kz_95=kz.get("kz_95", ZERO), kz_98=kz.get("kz_98", ZERO),
        kz_46=kz.get("kz_46", ZERO), kz_47=kz.get("kz_47", ZERO),
        kz_84=kz.get("kz_84", ZERO), kz_85=kz.get("kz_85", ZERO),
        kz_66=kz.get("kz_66", ZERO), kz_61=kz.get("kz_61", ZERO),
        kz_67=kz.get("kz_67", ZERO),
        zahllast=jahressteuer,
        kz_48=kz_48,
        summe_vorauszahlungen=summe_voa,
        restschuld=restschuld,
        gespeicherte_perioden=len(voranmeldungen),
        hat_ig_transaktionen=hat_ig,
    )


@router.get("/jahreserklarung/pdf")
def jahresumsatzsteuer_pdf(
    jahr: int = Query(...),
    db: Session = Depends(get_db),
):
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(404, "Unternehmensdaten nicht gefunden.")

    von = date(jahr, 1, 1)
    bis = date(jahr, 12, 31)
    ist_ku = bool(unt.ist_kleinunternehmer)

    kz_48 = ZERO
    if ist_ku:
        kz: dict[str, Decimal] = {k: ZERO for k in ALL_KZ_KEYS}
        kz_48 = _berechne_ku_kz48(von, bis, db)
    else:
        kz = _berechne_kz(von, bis, db)

    voranmeldungen = (
        db.query(UstvaExport)
        .filter(UstvaExport.zeitraum.like(f"{jahr}-%"))
        .all()
    )
    q = Decimal("0.01")
    summe_voa = sum((Decimal(str(v.zahllast)) for v in voranmeldungen), Decimal("0")).quantize(q, ROUND_HALF_UP)
    jahressteuer = kz["zahllast"]

    hat_ig = any(
        kz.get(k, ZERO) != ZERO
        for k in ["kz_41", "kz_89", "kz_93", "kz_90", "kz_95", "kz_98", "kz_46", "kz_47", "kz_84", "kz_85"]
    )

    ergebnis = JahresUStVAErgebnis(
        jahr=jahr, von=von, bis=bis, ist_kleinunternehmer=ist_ku,
        kz_81=kz.get("kz_81", ZERO), kz_83=kz.get("kz_83", ZERO),
        kz_86=kz.get("kz_86", ZERO), kz_88=kz.get("kz_88", ZERO),
        kz_41=kz.get("kz_41", ZERO), kz_87=kz.get("kz_87", ZERO),
        kz_89=kz.get("kz_89", ZERO), kz_93=kz.get("kz_93", ZERO),
        kz_90=kz.get("kz_90", ZERO), kz_95=kz.get("kz_95", ZERO), kz_98=kz.get("kz_98", ZERO),
        kz_46=kz.get("kz_46", ZERO), kz_47=kz.get("kz_47", ZERO),
        kz_84=kz.get("kz_84", ZERO), kz_85=kz.get("kz_85", ZERO),
        kz_66=kz.get("kz_66", ZERO), kz_61=kz.get("kz_61", ZERO),
        kz_67=kz.get("kz_67", ZERO),
        zahllast=jahressteuer, kz_48=kz_48,
        summe_vorauszahlungen=summe_voa,
        restschuld=(jahressteuer - summe_voa).quantize(q, ROUND_HALF_UP),
        gespeicherte_perioden=len(voranmeldungen),
        hat_ig_transaktionen=hat_ig,
    )
    pdf_bytes = _generate_pdf_jahres(jahr, ergebnis, unt)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="JahresUSt_{jahr}.pdf"'},
    )
