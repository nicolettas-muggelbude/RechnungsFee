"""
ZUGFeRD / XRechnung Parsing für Eingangsrechnungs-Import (Stufe 2).

Unterstützte Formate:
  - PDF mit eingebettetem ZUGFeRD-XML  (factur-x)
  - Standalone XRechnung-XML           (lxml)
  - Normales PDF                        → format='pdf', keine Felder
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional
import re


# ---------------------------------------------------------------------------
# Ergebnis-Datenklassen
# ---------------------------------------------------------------------------

@dataclass
class AnalysePosition:
    beschreibung: str
    menge: str = "1.000"
    einheit: str = "Stück"
    netto: str = "0.00"
    ust_satz: str = "0"
    artikel_nr: Optional[str] = None


@dataclass
class AnalyseErgebnis:
    format: str                          # zugferd | xrechnung | pdf
    felder: dict = field(default_factory=dict)
    positionen: list[AnalysePosition] = field(default_factory=list)
    warnungen: list[str] = field(default_factory=list)
    konfidenz: dict = field(default_factory=dict)  # Feld → "ok"|"warnung"|"fehlt"
    positionen_modus: str = "netto"      # "netto" | "brutto" – Eingabemodus für Positionen


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _d(text: Optional[str]) -> Optional[str]:
    """XML-Betrag → '1234.56'-String oder None."""
    if not text:
        return None
    try:
        return str(Decimal(text.strip()).quantize(Decimal("0.01")))
    except InvalidOperation:
        return None


def _menge(text: Optional[str]) -> str:
    if not text:
        return "1.000"
    try:
        return str(Decimal(text.strip()).quantize(Decimal("0.001")))
    except InvalidOperation:
        return "1.000"


_EINHEIT_MAP = {
    "C62": "Stück", "HUR": "Std", "DAY": "Tag", "WEE": "Woche",
    "MON": "Monat", "MIN": "Min", "KGM": "kg", "GRM": "g",
    "LTR": "l", "MLT": "ml", "MTR": "m", "MTK": "m²", "MTQ": "m³",
    "KMT": "km", "LS": "Pauschal",
}


def _einheit(code: Optional[str]) -> str:
    return _EINHEIT_MAP.get(code or "", "Stück")


def _ns(root):
    """Gibt das Namespace-Dict für lxml zurück."""
    return root.nsmap


def _build_konfidenz(felder: dict) -> dict:
    """
    Bewertet je Feld die Extraktionsqualität.
    ok      = vorhanden und plausibel
    warnung = vorhanden, aber verdächtig
    fehlt   = nicht extrahiert
    """
    K: dict[str, str] = {}
    today = date.today()

    def _bewerte(schluessel: str, check_fn=None) -> None:
        val = felder.get(schluessel)
        if not val:
            K[schluessel] = "fehlt"
            return
        if check_fn:
            K[schluessel] = check_fn(val)
        else:
            K[schluessel] = "ok"

    def _datum_check(val: str) -> str:
        try:
            d = datetime.strptime(val, "%Y-%m-%d").date()
        except ValueError:
            return "warnung"
        if d > today:
            return "warnung"
        if (today - d).days > 5 * 365:
            return "warnung"
        return "ok"

    def _betrag_check(val: str) -> str:
        try:
            Decimal(val)
            return "ok"
        except InvalidOperation:
            return "warnung"

    def _name_check(val: str) -> str:
        return "ok" if len(val.strip()) >= 3 else "warnung"

    _bewerte("externe_belegnr")
    _bewerte("datum", _datum_check)
    _bewerte("faellig_am", _datum_check)
    _bewerte("gesamt_brutto", _betrag_check)
    _bewerte("gesamt_netto", _betrag_check)
    _bewerte("gesamt_ust", _betrag_check)
    _bewerte("lieferant_name", _name_check)

    # Plausibilität: netto + ust ≈ brutto (Toleranz 0.02 €)
    netto = felder.get("gesamt_netto")
    ust = felder.get("gesamt_ust")
    brutto = felder.get("gesamt_brutto")
    if netto and ust and brutto:
        try:
            diff = abs(Decimal(netto) + Decimal(ust) - Decimal(brutto))
            if diff > Decimal("0.02"):
                K["gesamt_brutto"] = "warnung"
        except InvalidOperation:
            pass

    return K


def _datum_de_zu_iso(text: str) -> Optional[str]:
    """DD.MM.YYYY oder D.M.YY → ISO-String, sonst None."""
    m = re.match(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})", text.strip())
    if not m:
        return None
    day, month, year = m.group(1), m.group(2), m.group(3)
    if len(year) == 2:
        year = f"20{year}"
    try:
        return date(int(year), int(month), int(day)).isoformat()
    except ValueError:
        return None


def _betrag_de(text: str) -> Optional[str]:
    """Deutschen Betrag (1.234,56 / 1234,56 / 1234.56) → Decimal-String oder None."""
    text = text.strip().replace("€", "").replace("EUR", "").strip()
    try:
        if re.match(r"^\d{1,3}(?:\.\d{3})*,\d{2}$", text):
            return str(Decimal(text.replace(".", "").replace(",", ".")))
        if re.match(r"^\d+,\d{2}$", text):
            return str(Decimal(text.replace(",", ".")))
        return str(Decimal(text.replace(",", ".")))
    except InvalidOperation:
        return None


_GUELTIGE_UST = {0, 7, 9, 16, 19}  # in DE vorkommende Sätze


def _faellig_aus_zahlungsziel(datum_iso: Optional[str], ziel_text: str) -> Optional[str]:
    """Berechnet Fälligkeitsdatum aus Datum + 'X Tage'-Text (wie Plain-PDF-Fallback)."""
    if not datum_iso or not ziel_text:
        return None
    m = re.search(
        r"Rechnungsdatum\s*\+\s*(\d+)\s*(?:Werk)?[Tt]age?"
        r"|(?:Zahlungsziel|Zahlbar\s+innerhalb|netto\s+(?:sofort\s+)?innerhalb|innerhalb)\s*[:\s]*(\d+)\s*(?:Werk)?[Tt]age?"
        r"|(\d+)\s*(?:Werk)?[Tt]age?\s*(?:Zahlungsziel|netto|Zahlung|ab\s+Rechnung)?"
        r"|Zahlung\s+(?:innerhalb|binnen)\s*(\d+)\s*(?:Werk)?[Tt]age?"
        r"|netto\s+(\d+)\s*[Tt]age?",
        ziel_text, re.IGNORECASE,
    )
    if not m:
        return None
    try:
        from datetime import timedelta
        tage = int(next(g for g in m.groups() if g is not None))
        return (date.fromisoformat(datum_iso) + timedelta(days=tage)).isoformat()
    except (ValueError, TypeError, StopIteration):
        return None


def _normalize_ust_satz(val: Optional[str]) -> Optional[str]:
    """'19.00' → '19', '7.0' → '7', None/'' → None."""
    if not val:
        return None
    try:
        return str(int(Decimal(val)))
    except (InvalidOperation, ValueError):
        return val


def _ust_satz_aus_betraegen(netto_str: Optional[str], ust_str: Optional[str]) -> Optional[str]:
    """Leitet USt-Satz (%) aus Netto- und USt-Betrag ab, gerundet auf DE-Standardsatz."""
    if not netto_str or not ust_str:
        return None
    try:
        netto = Decimal(netto_str)
        ust = Decimal(ust_str)
        if netto <= 0:
            return None
        rate = int((ust / netto * 100).quantize(Decimal("1")))
        closest = min(_GUELTIGE_UST, key=lambda s: abs(s - rate))
        return str(closest)
    except (InvalidOperation, ValueError, ZeroDivisionError):
        return None


def _berechne_fehlende_summen(felder: dict) -> None:
    """Berechnet fehlendes Brutto/Netto/USt wenn zwei der drei Werte bekannt sind."""
    try:
        n = Decimal(felder["gesamt_netto"]) if felder.get("gesamt_netto") else None
        u = Decimal(felder["gesamt_ust"]) if felder.get("gesamt_ust") else None
        b = Decimal(felder["gesamt_brutto"]) if felder.get("gesamt_brutto") else None
        q = Decimal("0.01")
        if n and u and not b:
            felder["gesamt_brutto"] = str((n + u).quantize(q))
        elif n and b and not u:
            felder["gesamt_ust"] = str((b - n).quantize(q))
        elif u and b and not n:
            felder["gesamt_netto"] = str((b - u).quantize(q))
    except (InvalidOperation, KeyError):
        pass


def _extrahiere_positionen(text: str, ust_satz_default: Optional[str]) -> list["AnalysePosition"]:
    """
    Versucht Einzelpositionen aus PDF-Freitext zu extrahieren.
    Gibt leere Liste zurück wenn kein verwertbares Ergebnis erkennbar ist.
    """
    # Betrag am Zeilenende, optional gefolgt von "19 %" (trailing USt)
    _BETRAG_END = re.compile(
        r"\s+(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})\s*(?:€|EUR)?\s*(?:(\d+)\s*%)?\s*$",
        re.IGNORECASE,
    )
    _SUMMENLABEL = re.compile(
        r"^(?:netto(?:betrag|summe|preis)?|brutto(?:betrag|summe)?|"
        r"gesamt(?:betrag|summe)?|zwischensumme|rechnungsbetrag|"
        r"zu\s+zahlen(?:\w+)?|summe(?:betrag)?(?:\s+netto)?|"
        r"(?:ust|mwst|umsatzsteuer)\.?\s*\d*\s*%?|"
        r"\d+\s*%\s*(?:ust|mwst|umsatzsteuer)|"
        r"rabatt|skonto|aufschlag|mindermenge)\s*(?:[:\s]|$)",
        re.IGNORECASE,
    )
    _HEADER = re.compile(
        r"(?:beschreibung|bezeichnung|artikel|leistung).{0,40}(?:betrag|preis|ep|gp)",
        re.IGNORECASE,
    )
    _EINHEIT = re.compile(
        r"^(Stk\.?|Stück|Std\.?|[Hh](?:r(?:s|[.])?)?\.?|[Tt]ag(?:e|en)?\.?|"
        r"[Ww]ochen?\.?|[Mm]onate?n?\.?|[Kk][Gg]\.?|[Gg](?:ram)?\.?|"
        r"[Ll](?:iter)?\.?|m[l]?\.?|[Mm]eter?\.?|[Kk][Mm]\.?|"
        r"[Pp](?:auschal(?:e)?|sch\.?))\s+",
        re.IGNORECASE,
    )
    _EINHEIT_MAP = {
        "stk": "Stück", "stück": "Stück",
        "std": "Std", "h": "Std", "hr": "Std", "hrs": "Std",
        "tag": "Tag", "tage": "Tag", "tagen": "Tag",
        "woche": "Woche", "wochen": "Woche",
        "monat": "Monat", "monate": "Monat",
        "kg": "kg", "g": "g", "gram": "g",
        "l": "l", "liter": "l", "ml": "ml",
        "m": "m", "meter": "m", "km": "km",
        "pauschal": "Pauschal", "pauschale": "Pauschal", "psch": "Pauschal",
    }

    alle_zeilen = text.split("\n")
    positionen: list[AnalysePosition] = []

    start, end = 0, len(alle_zeilen)
    for i, z in enumerate(alle_zeilen):
        s = z.strip()
        if _HEADER.search(s):
            start = i + 1
        if i > start and _SUMMENLABEL.match(s) and _BETRAG_END.search(s):
            end = i
            break

    for z in alle_zeilen[start:end]:
        s = z.strip()
        if not s:
            continue
        # USt-Aufschlüsselungszeile überspringen: "A 19 10,08 1,92 12,00"
        if re.match(r"^[A-Z]\s+\d{1,2}\s+\d+,\d{2}\s+\d+,\d{2}\s+\d+,\d{2}\s*$", s):
            continue
        m = _BETRAG_END.search(s)
        if not m:
            continue
        betrag = _betrag_de(m.group(1))
        if not betrag:
            continue
        try:
            if Decimal(betrag) < Decimal("0.01"):
                continue
        except InvalidOperation:
            continue

        vor = s[:m.start()].strip()
        if not vor or _SUMMENLABEL.match(vor):
            continue

        # USt aus trailing-% (Gruppe 2) oder aus Inline-% in vor bestimmen
        ust_pos = ust_satz_default or "0"
        if m.group(2) and int(m.group(2)) in _GUELTIGE_UST:
            ust_pos = m.group(2)
        else:
            m_ust = re.search(r"(\d+)\s*%\s*$", vor)
            if m_ust and int(m_ust.group(1)) in _GUELTIGE_UST:
                ust_pos = m_ust.group(1)
                vor = vor[:m_ust.start()].strip()
            else:
                # % irgendwo in der Zeile vor dem Betrag (z.B. "19 % MwSt")
                m_ust2 = re.search(r"\b(\d+)\s*%", vor)
                if m_ust2 and int(m_ust2.group(1)) in _GUELTIGE_UST:
                    ust_pos = m_ust2.group(1)

        # Zweiten Betrag (Einzelpreis) in vor abschneiden
        m2 = _BETRAG_END.search(vor)
        if m2:
            vor = vor[:m2.start()].strip()

        # Nackter USt-Satz (ohne %) am Zeilenende → aus Beschreibung entfernen
        m_naked = re.search(r"(?<!\d)(\d{1,2})\s*$", vor)
        if m_naked and int(m_naked.group(1)) in _GUELTIGE_UST:
            if ust_pos == (ust_satz_default or "0"):
                ust_pos = m_naked.group(1)
            vor = vor[:m_naked.start()].strip()

        # Artikelnummer am Anfang: Ziffernfolge (≥4) oder alphanumerischer Code mit Trennzeichen
        artikel_nr: Optional[str] = None
        m_artnr = re.match(
            r"^(\d{4,}|[A-Z]{1,5}[-./]\d{2,}|[A-Z]{2,}\d{2,})\s+(?=[A-Za-zÀ-ž])",
            vor, re.IGNORECASE,
        )
        if m_artnr and len(vor) - len(m_artnr.group(0)) >= 3:
            artikel_nr = m_artnr.group(1)
            vor = vor[m_artnr.end():].strip()

        # Menge am Anfang: "2x", "4 Std", "1,5 kg" …
        menge, einheit = "1.000", "Stück"
        # Format "[TypCode] [Qty] Beschreibung" (z.B. "A 1 TLD Domain"): einzelner Buchstabe + Zahl
        m_typ_q = re.match(r"^[A-Z]\s+(\d+(?:[,.]\d+)?)\s+(?=[A-Za-zÀ-ž])", vor, re.IGNORECASE)
        if m_typ_q:
            try:
                menge = f"{float(m_typ_q.group(1).replace(',', '.')):.3f}"
            except ValueError:
                pass
            vor = vor[m_typ_q.end():].strip()
        m_menge = re.match(r"^(\d+(?:[,.]\d+)?)\s*", vor)
        if m_menge:
            nach_zahl = vor[m_menge.end():]
            m_x = re.match(r"^([xX×])\s*", nach_zahl)
            m_ein = _EINHEIT.match(nach_zahl)
            if m_x or m_ein:
                try:
                    menge = f"{float(m_menge.group(1).replace(',', '.')):.3f}"
                except ValueError:
                    pass
                if m_ein:
                    roh = m_ein.group(1).rstrip(". ").lower()
                    einheit = _EINHEIT_MAP.get(roh, m_ein.group(1).rstrip("."))
                    vor = nach_zahl[m_ein.end():].strip()
                else:
                    vor = nach_zahl[m_x.end():].strip()

        if len(vor) < 2 or re.match(r"^\d+$", vor):
            continue

        positionen.append(AnalysePosition(
            beschreibung=vor,
            menge=menge,
            einheit=einheit,
            netto=betrag,
            ust_satz=ust_pos,
            artikel_nr=artikel_nr,
        ))

    if len(positionen) == 1 and len(positionen[0].beschreibung) < 5:
        return []
    return positionen


def _extrahiere_pdf_text(pdf_bytes: bytes) -> "AnalyseErgebnis":
    """Fallback: Text aus PDF lesen und per Regex Rechnungsfelder suchen."""
    warnungen: list[str] = []
    try:
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        return AnalyseErgebnis(
            format="pdf",
            warnungen=["Kein eingebettetes XML – Textextraktion fehlgeschlagen.", str(exc)],
        )

    if not text.strip():
        return AnalyseErgebnis(
            format="pdf",
            warnungen=["Kein eingebettetes XML – kein extrahierbarer Text (gescanntes Dokument?)."],
        )

    felder: dict = {}

    # Datum – zuerst suchen, damit spätere Felder darauf aufbauen können
    _datum_pattern = r"\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}"
    m = re.search(
        r"(?:Rechnungs(?:datum)?|Ausstellungsdatum|Ausgestellt(?:\s+am)?|Datum)\s*:?\s*(" + _datum_pattern + r")",
        text, re.IGNORECASE,
    )
    if m:
        iso = _datum_de_zu_iso(m.group(1))
        if iso:
            felder["datum"] = iso
    else:
        # Fallback: alle Datumstreffer sammeln, neuestes plausibles nehmen
        alle_daten = re.findall(_datum_pattern, text)
        for treffer in alle_daten:
            iso = _datum_de_zu_iso(treffer)
            if iso:
                felder["datum"] = iso
                break

    # Rechnungsnummer – gängige deutsche Label (Wert in derselben Zeile)
    _belegnr_label = (
        r"(?:Rechnungs(?:nummer|[-\s]?Nr\.?|nr\.?|snr\.?)"
        r"|Rechnung(?!s?[\s]*(?:datum|sDatum))\s*(?:[-]?\s*Nr\.?|#|:|\s)"
        r"|RE[-.\s]?Nr\.?|RE(?=[\s:]+[A-Z0-9\-])"
        r"|Beleg(?:nummer|[-\s]?Nr\.?|nr\.?)|Beleg(?=[\s:]+\d)"
        r"|Faktura[-\s]?(?:Nr\.?|nummer)?"
        r"|Invoice\s*(?:No\.?|Nr\.?|#))"
    )
    def _belegnr_filter(kandidat: str) -> bool:
        return (bool(re.search(r"\d", kandidat))
                and not re.match(r"^\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}$", kandidat))

    m = re.search(_belegnr_label + r"[\s:]*([A-Z0-9][A-Z0-9/\-_.]{1,29})", text, re.IGNORECASE)
    if m:
        kandidat = m.group(1).strip()
        if _belegnr_filter(kandidat):
            felder["externe_belegnr"] = kandidat

    # Fallback: Label als Tabellen-Header, Wert steht auf der nächsten Zeile
    if not felder.get("externe_belegnr"):
        m2 = re.search(
            _belegnr_label + r"[^\n]*\n\s*([A-Z0-9][A-Z0-9/\-_.]{1,29})",
            text, re.IGNORECASE,
        )
        if m2:
            kandidat = m2.group(1).strip()
            if _belegnr_filter(kandidat):
                felder["externe_belegnr"] = kandidat

    # Fälligkeitsdatum – explizites Datum ODER "X Tage Zahlungsziel"
    m_faellig = re.search(
        r"(?:F[äa]llig(?:keit(?:s?datum)?)?|zahlbar\s+bis|zu\s+zahlen\s+bis)\s*:?\s*(" + _datum_pattern + r")",
        text, re.IGNORECASE,
    )
    if m_faellig:
        iso = _datum_de_zu_iso(m_faellig.group(1))
        if iso:
            felder["faellig_am"] = iso
    else:
        # "14 Tage", "14 Werktage", "Zahlungsziel 14 Tage", "netto 14 Tage" usw.
        m_ziel = re.search(
            r"Rechnungsdatum\s*\+\s*(\d+)\s*(?:Werk)?[Tt]age?"
            r"|(?:Zahlungsziel|Zahlbar\s+innerhalb|netto\s+(?:sofort\s+)?innerhalb|innerhalb)\s*[:\s]*(\d+)\s*(?:Werk)?[Tt]age?"
            r"|(\d+)\s*(?:Werk)?[Tt]age?\s*(?:Zahlungsziel|netto|Zahlung|ab\s+Rechnung)"
            r"|Zahlung\s+(?:innerhalb|binnen)\s*(\d+)\s*(?:Werk)?[Tt]age?"
            r"|netto\s+(\d+)\s*[Tt]age?",
            text, re.IGNORECASE,
        )
        if m_ziel and felder.get("datum"):
            try:
                from datetime import timedelta
                tage = int(next(g for g in m_ziel.groups() if g is not None))
                felder["faellig_am"] = (date.fromisoformat(felder["datum"]) + timedelta(days=tage)).isoformat()
            except (ValueError, TypeError):
                pass

    # USt-Aufschlüsselung Tabellenformat: "[A-Z] 19 10,08 1,92 12,00" → Netto/USt/Brutto
    m_ust_tab = re.search(
        r"^[A-Z]\s+(\d{1,2})\s+(\d+,\d{2})\s+(\d+,\d{2})\s+(\d+,\d{2})\s*$",
        text, re.IGNORECASE | re.MULTILINE,
    )
    if m_ust_tab:
        if not felder.get("ust_satz"):
            felder["ust_satz"] = m_ust_tab.group(1)
        if not felder.get("gesamt_netto"):
            felder["gesamt_netto"] = _betrag_de(m_ust_tab.group(2))
        if not felder.get("gesamt_ust"):
            felder["gesamt_ust"] = _betrag_de(m_ust_tab.group(3))
        if not felder.get("gesamt_brutto"):
            felder["gesamt_brutto"] = _betrag_de(m_ust_tab.group(4))

    # USt-Satz + USt-Betrag (kombiniert, mit %-Zeichen)
    if not felder.get("ust_satz") or not felder.get("gesamt_ust"):
        m = re.search(
            r"(\d{1,2})\s*%\s*(?:MwSt\.?|USt\.?|Umsatzsteuer)\s*[:\s]+([\d.,]+)",
            text, re.IGNORECASE,
        )
        if m:
            felder["ust_satz"] = m.group(1)
            v = _betrag_de(m.group(2))
            if v:
                felder["gesamt_ust"] = v
        else:
            m = re.search(
                r"(?:MwSt\.?|USt\.?|Umsatzsteuer)\s*(?:\d+\s*%\s*)?:?\s*([\d.,]+)",
                text, re.IGNORECASE,
            )
            if m:
                v = _betrag_de(m.group(1))
                if v:
                    felder["gesamt_ust"] = v

    # Brutto-Gesamtbetrag
    m = re.search(
        r"(?:Gesamtbetrag|Rechnungsbetrag|Zu\s+zahlen(?:der\s+Betrag)?|"
        r"Brutto(?:summe|betrag)?|Gesamt(?:summe)?|Summe)\s*[:\s]*([\d.,]+)\s*(?:€|EUR)?",
        text, re.IGNORECASE,
    )
    if m:
        v = _betrag_de(m.group(1))
        if v:
            felder["gesamt_brutto"] = v

    # Netto-Betrag
    m = re.search(
        r"(?:Netto(?:betrag|summe)?|Zwischensumme(?:\s+netto)?)\s*[:\s]+([\d.,]+)\s*(?:€|EUR)?",
        text, re.IGNORECASE,
    )
    if m:
        v = _betrag_de(m.group(1))
        if v:
            felder["gesamt_netto"] = v

    # USt-ID
    m = re.search(r"(?:USt\.?-?IdNr\.?|UStIdNr|UID)\s*:?\s*(DE\d{9})", text, re.IGNORECASE)
    if m:
        felder["lieferant_ust_id"] = m.group(1).strip()

    # Lieferanten-Name: erste Zeile mit Unternehmensform-Marker
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines[:25]:
        if re.search(r"\b(GmbH|UG|AG|e\.?K\.?|KG|OHG|GbR|e\.?V\.?|Ltd|Inc|Co\.)\b", line, re.IGNORECASE):
            felder["lieferant_name"] = line
            break

    felder = {k: v for k, v in felder.items() if v is not None}
    _berechne_fehlende_summen(felder)

    if felder:
        warnungen.append("Kein eingebettetes XML – Felder aus PDF-Text extrahiert, bitte prüfen.")
    else:
        warnungen.append("Kein eingebettetes XML – keine Felder erkannt, bitte manuell ausfüllen.")


    konfidenz = _build_konfidenz(felder)
    # Alle per Regex extrahierten Felder mindestens auf "warnung" setzen
    for k in list(konfidenz):
        if konfidenz[k] == "ok":
            konfidenz[k] = "warnung"
    for k in ("externe_belegnr", "datum", "gesamt_brutto", "lieferant_name"):
        if k not in felder:
            konfidenz[k] = "fehlt"

    positionen = _extrahiere_positionen(text, felder.get("ust_satz"))

    # Brutto/Netto-Modus: Summe der Positionen mit bekannten Gesamtbeträgen vergleichen
    positionen_modus = "netto"
    if positionen and (felder.get("gesamt_netto") or felder.get("gesamt_brutto")):
        try:
            pos_summe = sum(Decimal(p.netto) for p in positionen)
            toleranz = Decimal("0.15")
            netto_total = Decimal(felder.get("gesamt_netto") or "0")
            brutto_total = Decimal(felder.get("gesamt_brutto") or "0")
            diff_netto = abs(pos_summe - netto_total) if netto_total else Decimal("9999")
            diff_brutto = abs(pos_summe - brutto_total) if brutto_total else Decimal("9999")
            if diff_brutto <= toleranz and diff_brutto < diff_netto:
                positionen_modus = "brutto"
        except (InvalidOperation, Exception):
            pass

    return AnalyseErgebnis(
        format="pdf", felder=felder, positionen=positionen,
        positionen_modus=positionen_modus, warnungen=warnungen, konfidenz=konfidenz,
    )


def _x(elem, xpath: str, ns: dict) -> Optional[str]:
    """XPath mit Namespace, gibt ersten Textwert oder None zurück."""
    results = elem.xpath(xpath, namespaces=ns)
    if not results:
        return None
    node = results[0]
    return node.text.strip() if hasattr(node, "text") and node.text else str(node).strip() or None


# ---------------------------------------------------------------------------
# ZUGFeRD / Factur-X / XRechnung – CII-Format (Cross-Industry Invoice)
# ---------------------------------------------------------------------------

def _parse_cii_xml(xml_bytes: bytes) -> AnalyseErgebnis:
    from lxml import etree

    root = etree.fromstring(xml_bytes)
    ns = {
        "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
        "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
        "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    }

    warnungen: list[str] = []
    felder: dict = {}
    positionen: list[AnalysePosition] = []

    # Format-Typ aus GuidelineSpecifiedDocumentContextParameter
    profil = _x(root, "//ram:GuidelineSpecifiedDocumentContextParameter/ram:ID", ns) or ""
    if "xrechnung" in profil.lower():
        fmt = "xrechnung"
    else:
        fmt = "zugferd"

    # Rechnungsnummer (BT-1)
    nr = _x(root, "//rsm:ExchangedDocument/ram:ID", ns)
    if nr:
        felder["externe_belegnr"] = nr
    else:
        warnungen.append("BT-1: Rechnungsnummer fehlt")

    # Datum (BT-2)
    datum_raw = _x(root, "//rsm:ExchangedDocument/ram:IssueDateTime/udt:DateTimeString", ns)
    if datum_raw and len(datum_raw) == 8:
        felder["datum"] = f"{datum_raw[:4]}-{datum_raw[4:6]}-{datum_raw[6:8]}"

    # Fälligkeitsdatum (BT-9) – Zahlungsbedingungstext hat Vorrang vor DueDateDateTime
    ziel_text = _x(root, "//ram:SpecifiedTradePaymentTerms/ram:Description", ns) or ""
    iso = _faellig_aus_zahlungsziel(felder.get("datum"), ziel_text)
    if iso:
        felder["faellig_am"] = iso
    else:
        faellig_raw = _x(root, "//ram:SpecifiedTradePaymentTerms/ram:DueDateDateTime/udt:DateTimeString", ns)
        if faellig_raw and len(faellig_raw) == 8:
            felder["faellig_am"] = f"{faellig_raw[:4]}-{faellig_raw[4:6]}-{faellig_raw[6:8]}"
        else:
            warnungen.append("BT-9: Fälligkeitsdatum fehlt")

    # Lieferant (BT-27)
    lieferant_name = _x(root, "//ram:SellerTradeParty/ram:Name", ns)
    if lieferant_name:
        felder["lieferant_name"] = lieferant_name
    else:
        warnungen.append("BT-27: Lieferantenname fehlt")

    felder["lieferant_ust_id"] = _x(root, "//ram:SellerTradeParty/ram:SpecifiedTaxRegistration/ram:ID", ns)
    felder["lieferant_email"] = _x(root, "//ram:SellerTradeParty/ram:URIUniversalCommunication/ram:URIID", ns)

    # Adresse Lieferant
    felder["lieferant_strasse"] = _x(root, "//ram:SellerTradeParty/ram:PostalTradeAddress/ram:LineOne", ns)
    felder["lieferant_plz"] = _x(root, "//ram:SellerTradeParty/ram:PostalTradeAddress/ram:PostcodeCode", ns)
    felder["lieferant_ort"] = _x(root, "//ram:SellerTradeParty/ram:PostalTradeAddress/ram:CityName", ns)

    # Gesamtbeträge (BT-109 / BT-110 / BT-112)
    netto = _d(_x(root, "//ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:TaxBasisTotalAmount", ns))
    ust   = _d(_x(root, "//ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:TaxTotalAmount", ns))
    brutto = _d(_x(root, "//ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:GrandTotalAmount", ns))

    if netto:  felder["gesamt_netto"]  = netto
    if ust:    felder["gesamt_ust"]    = ust
    if brutto: felder["gesamt_brutto"] = brutto
    _berechne_fehlende_summen(felder)
    if not felder.get("gesamt_brutto"):
        warnungen.append("BT-112: Gesamtbetrag (brutto) fehlt")

    # Steuersatz (explizit oder aus Beträgen abgeleitet)
    ust_satz = _normalize_ust_satz(_x(root, "//ram:ApplicableTradeTax/ram:RateApplicablePercent", ns))
    if not ust_satz:
        ust_satz = _ust_satz_aus_betraegen(felder.get("gesamt_netto"), felder.get("gesamt_ust"))
    if ust_satz:
        felder["ust_satz"] = ust_satz

    # Positionen
    for item in root.xpath("//ram:IncludedSupplyChainTradeLineItem", namespaces=ns):
        beschr = _x(item, "ram:SpecifiedTradeProduct/ram:Name", ns) or "Position"
        menge_raw = _x(item, "ram:SpecifiedLineTradeDelivery/ram:BilledQuantity", ns)
        einheit_code = None
        menge_elems = item.xpath("ram:SpecifiedLineTradeDelivery/ram:BilledQuantity", namespaces=ns)
        if menge_elems:
            einheit_code = menge_elems[0].get("unitCode")

        netto_pos = _d(_x(item, "ram:SpecifiedLineTradeSettlement/ram:SpecifiedTradeSettlementLineMonetarySummation/ram:LineTotalAmount", ns))
        ust_pos = _normalize_ust_satz(
            _x(item, "ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax/ram:RateApplicablePercent", ns)
            or _x(item, ".//ram:RateApplicablePercent", ns)
        )

        positionen.append(AnalysePosition(
            beschreibung=beschr,
            menge=_menge(menge_raw),
            einheit=_einheit(einheit_code),
            netto=netto_pos or "0.00",
            ust_satz=ust_pos or ust_satz or "0",
        ))

    # Fallback: eine Position aus Gesamtbetrag wenn keine Positionen
    if not positionen and netto:
        positionen.append(AnalysePosition(
            beschreibung=lieferant_name or "Import",
            netto=netto,
            ust_satz=ust_satz or "0",
        ))

    # None-Werte entfernen
    felder = {k: v for k, v in felder.items() if v is not None}

    return AnalyseErgebnis(
        format=fmt, felder=felder, positionen=positionen,
        warnungen=warnungen, konfidenz=_build_konfidenz(felder),
    )


# ---------------------------------------------------------------------------
# UBL-Format (manche XRechnungen nutzen UBL statt CII)
# ---------------------------------------------------------------------------

def _parse_ubl_xml(xml_bytes: bytes) -> AnalyseErgebnis:
    from lxml import etree

    root = etree.fromstring(xml_bytes)
    ns = {
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    }

    warnungen: list[str] = []
    felder: dict = {}
    positionen: list[AnalysePosition] = []

    nr = _x(root, "//cbc:ID", ns)
    if nr:
        felder["externe_belegnr"] = nr

    datum = _x(root, "//cbc:IssueDate", ns)
    if datum:
        felder["datum"] = datum

    # Zahlungsbedingungstext hat Vorrang vor explizitem DueDate
    ziel_text = _x(root, "//cac:PaymentTerms/cbc:Note", ns) or ""
    iso = _faellig_aus_zahlungsziel(felder.get("datum"), ziel_text)
    if iso:
        felder["faellig_am"] = iso
    else:
        faellig = (
            _x(root, "//cbc:DueDate", ns)
            or _x(root, "//cac:PaymentMeans/cbc:PaymentDueDate", ns)
            or _x(root, "//cac:PaymentTerms/cbc:PaymentDueDate", ns)
        )
        if faellig:
            felder["faellig_am"] = faellig

    lieferant_name = (
        _x(root, "//cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name", ns)
        or _x(root, "//cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName", ns)
    )
    if lieferant_name:
        felder["lieferant_name"] = lieferant_name
    else:
        warnungen.append("BT-27: Lieferantenname fehlt")

    felder["lieferant_ust_id"] = _x(root, "//cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID", ns)
    felder["lieferant_email"] = _x(root, "//cac:AccountingSupplierParty/cac:Party/cac:Contact/cbc:ElectronicMail", ns)
    felder["lieferant_strasse"] = _x(root, "//cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:StreetName", ns)
    felder["lieferant_plz"] = _x(root, "//cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:PostalZone", ns)
    felder["lieferant_ort"] = _x(root, "//cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:CityName", ns)

    brutto = _d(_x(root, "//cac:LegalMonetaryTotal/cbc:PayableAmount", ns))
    netto  = _d(_x(root, "//cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount", ns))
    ust    = _d(_x(root, "//cac:TaxTotal/cbc:TaxAmount", ns))
    ust_satz = _x(root, "//cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:Percent", ns)

    if netto:  felder["gesamt_netto"]  = netto
    if ust:    felder["gesamt_ust"]    = ust
    if brutto: felder["gesamt_brutto"] = brutto
    _berechne_fehlende_summen(felder)
    if not felder.get("gesamt_brutto"):
        warnungen.append("BT-112: Gesamtbetrag (brutto) fehlt")
    # Steuersatz (explizit oder aus Beträgen abgeleitet)
    ust_satz = _normalize_ust_satz(ust_satz)
    if not ust_satz:
        ust_satz = _ust_satz_aus_betraegen(felder.get("gesamt_netto"), felder.get("gesamt_ust"))
    if ust_satz: felder["ust_satz"] = ust_satz

    for item in root.xpath("//cac:InvoiceLine", namespaces=ns):
        beschr = _x(item, "cac:Item/cbc:Name", ns) or "Position"
        menge_raw = _x(item, "cbc:InvoicedQuantity", ns)
        einheit_code = None
        menge_elems = item.xpath("cbc:InvoicedQuantity", namespaces=ns)
        if menge_elems:
            einheit_code = menge_elems[0].get("unitCode")
        netto_pos = _d(_x(item, "cbc:LineExtensionAmount", ns))
        ust_pos = _normalize_ust_satz(
            _x(item, "cac:Item/cac:ClassifiedTaxCategory/cbc:Percent", ns)
            or _x(item, "cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:Percent", ns)
            or _x(item, ".//cac:TaxCategory/cbc:Percent", ns)
        )

        positionen.append(AnalysePosition(
            beschreibung=beschr,
            menge=_menge(menge_raw),
            einheit=_einheit(einheit_code),
            netto=netto_pos or "0.00",
            ust_satz=ust_pos or ust_satz or "0",
        ))

    if not positionen and netto:
        positionen.append(AnalysePosition(
            beschreibung=lieferant_name or "Import",
            netto=netto,
            ust_satz=ust_satz or "0",
        ))

    felder = {k: v for k, v in felder.items() if v is not None}
    return AnalyseErgebnis(
        format="xrechnung", felder=felder, positionen=positionen,
        warnungen=warnungen, konfidenz=_build_konfidenz(felder),
    )


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------

def analysiere_datei(dateiname: str, inhalt: bytes) -> AnalyseErgebnis:
    """
    Erkennt das Format und gibt das Analyse-Ergebnis zurück.
    Wirft keine Exception – Fehler landen in warnungen.
    """
    lower = dateiname.lower()

    # 1. Standalone XML
    if lower.endswith(".xml"):
        return _analysiere_xml(inhalt)

    # 2. PDF – ZUGFeRD-XML extrahieren
    if lower.endswith(".pdf") or inhalt[:4] == b"%PDF":
        try:
            from facturx import get_facturx_xml_from_pdf
            result = get_facturx_xml_from_pdf(inhalt)
            # factur-x gibt (dateiname, xml_bytes) zurück
            xml_bytes = result[1] if isinstance(result, tuple) else result
            if xml_bytes:
                ergebnis = _analysiere_xml(xml_bytes)
                if ergebnis.format == "xrechnung":
                    ergebnis.format = "xrechnung"
                else:
                    ergebnis.format = "zugferd"
                return ergebnis
        except Exception:
            pass
        return _extrahiere_pdf_text(inhalt)

    return AnalyseErgebnis(format="unbekannt", warnungen=["Dateiformat nicht unterstützt."])


def _analysiere_xml(xml_bytes: bytes) -> AnalyseErgebnis:
    """Erkennt CII vs. UBL anhand des Root-Elements."""
    try:
        from lxml import etree
        root = etree.fromstring(xml_bytes)
        tag = root.tag or ""
        if "CrossIndustryInvoice" in tag:
            return _parse_cii_xml(xml_bytes)
        elif "Invoice" in tag:
            return _parse_ubl_xml(xml_bytes)
        else:
            return AnalyseErgebnis(format="xml", warnungen=[f"Unbekanntes XML-Root-Element: {tag}"])
    except Exception as e:
        return AnalyseErgebnis(format="xml", warnungen=[f"XML-Parsing fehlgeschlagen: {e}"])
