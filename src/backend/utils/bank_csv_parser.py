"""
CSV-Parser für Bank-Kontoauszüge.

Verwendet stdlib csv + charset-normalizer (kein pandas).
Gibt list[dict] zurück – kein SQLAlchemy-Bezug.
"""

import csv
import io
import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

# IBAN-Muster: Länderkürzel + Prüfziffern + volle 4er-Gruppen + optionale Restgruppe (1–4 Zeichen).
# {2,6} volle Gruppen + Restgruppe deckt alle gängigen IBANs (DE 22 Stellen: 4 Gruppen + Rest "78").
_IBAN_RE = re.compile(r'[A-Z]{2}\d{2}(?:\s?[0-9A-Z]{4}){2,6}\s?[0-9A-Z]{1,4}')

from charset_normalizer import from_bytes


# ---------------------------------------------------------------------------
# Encoding & Delimiter
# ---------------------------------------------------------------------------

# Bei sehr wenig Nicht-ASCII-Text (z.B. DATEV-Exporte mit nur vereinzelten Umlauten)
# rät charset_normalizer mangels Signal manchmal auf exotische DOS-Codepages.
# Deutsche Business-Exporte (DATEV, Banken) sind praktisch nie DOS-kodiert,
# sondern cp1252/iso-8859-1 – bei so einem Treffer daher cp1252 bevorzugen (Issue #250).
_UNPLAUSIBLE_DOS_CODEPAGES = {
    "cp437", "cp720", "cp737", "cp775", "cp850", "cp852", "cp855",
    "cp857", "cp858", "cp860", "cp861", "cp862", "cp863", "cp864",
    "cp865", "cp866", "cp869", "cp874",
}


def detect_encoding(raw: bytes) -> str:
    # UTF-8-BOM (z.B. PayPal-Exporte) explizit behandeln – sonst landet "﻿" im
    # ersten Spaltennamen und Template-Erkennung/Mapping schlagen komplett fehl (Issue #248).
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    result = from_bytes(raw).best()
    if result is None:
        return "UTF-8"
    encoding = result.encoding or "UTF-8"
    if encoding.lower() in _UNPLAUSIBLE_DOS_CODEPAGES:
        try:
            raw.decode("cp1252")
            return "cp1252"
        except UnicodeDecodeError:
            pass
    return encoding


def detect_delimiter(text: str) -> str:
    """Zählt Vorkommen typischer Delimiter in der ersten Zeile."""
    first_line = text.split("\n")[0]
    counts = {";": first_line.count(";"), ",": first_line.count(","), "\t": first_line.count("\t")}
    return max(counts, key=lambda k: counts[k])


# ---------------------------------------------------------------------------
# Template-Matching
# ---------------------------------------------------------------------------

def match_score(header: list[str], erkennungs_spalten: list[str]) -> float:
    """Gibt Anteil der Erkennungsspalten zurück die im Header vorkommen (0.0–1.0)."""
    if not erkennungs_spalten:
        return 0.0
    header_clean = [h.strip().strip('"') for h in header]
    treffer = sum(1 for s in erkennungs_spalten if s in header_clean)
    return treffer / len(erkennungs_spalten)


def find_best_template(header: list[str], templates: list) -> Optional[object]:
    """Gibt das Template mit dem höchsten Match-Score zurück (mind. 0.8)."""
    best = None
    best_score = 0.0
    for tpl in templates:
        mapping = json.loads(tpl.column_mapping) if isinstance(tpl.column_mapping, str) else tpl.column_mapping
        erkennungs = mapping.get("__erkennungs__", [])
        score = match_score(header, erkennungs)
        if score > best_score:
            best_score = score
            best = tpl
    if best_score >= 0.8:
        return best
    return None


# ---------------------------------------------------------------------------
# Datums- & Betrags-Konvertierung
# ---------------------------------------------------------------------------

def parse_datum(wert: str, fmt: str) -> Optional[date]:
    wert = wert.strip()
    if not wert:
        return None
    try:
        return datetime.strptime(wert, fmt).date()
    except ValueError:
        pass
    # Nicht-null-gepolsterte Datumsangaben: D.M.YYYY oder D/M/YYYY (z. B. Deutsche Bank)
    m = re.match(r'^(\d{1,2})[./](\d{1,2})[./](\d{2,4})$', wert)
    if m:
        try:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if y < 100:
                y += 2000
            return date(y, mo, d)
        except ValueError:
            pass
    for fallback in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(wert, fallback).date()
        except ValueError:
            continue
    return None


def parse_betrag(wert: str, decimal_sep: str = ",") -> Optional[Decimal]:
    wert = wert.strip().replace(" ", "").replace("\xa0", "")
    if not wert:
        return None
    if decimal_sep == ",":
        wert = wert.replace(".", "").replace(",", ".")
    else:
        wert = wert.replace(",", "")
    try:
        return Decimal(wert)
    except InvalidOperation:
        return None


# ---------------------------------------------------------------------------
# Haupt-Parser
# ---------------------------------------------------------------------------

def parse_csv(
    raw: bytes,
    column_mapping: dict,
    delimiter: Optional[str] = None,
    encoding: Optional[str] = None,
    decimal_separator: str = ",",
    date_format: str = "%d.%m.%Y",
    skip_rows: int = 0,
) -> list[dict]:
    """
    Parst eine Bank-CSV-Datei anhand des column_mapping und gibt eine Liste
    von normalisierten Transaktions-Dicts zurück.

    Jedes Dict enthält die Schlüssel:
        datum, valuta, buchungstext, verwendungszweck,
        partner_name, partner_iban, partner_bic,
        betrag, waehrung, saldo, referenz
    """
    enc = encoding or detect_encoding(raw)
    text = raw.decode(enc, errors="replace")
    delim = delimiter or detect_delimiter(text)

    # Mapping ohne internen Sonderkey
    mapping = {k: v for k, v in column_mapping.items() if not k.startswith("__")}

    lines = text.splitlines()
    lines = lines[skip_rows:]  # Kopfzeilen überspringen (z.B. ING hat 13 Metazeilen)
    reader = csv.DictReader(lines, delimiter=delim, quotechar='"')

    ergebnis = []
    for row in reader:
        tx: dict = {
            "datum": None,
            "valuta": None,
            "buchungstext": None,
            "verwendungszweck": None,
            "partner_name": None,
            "partner_iban": None,
            "partner_bic": None,
            "betrag": None,
            "waehrung": "EUR",
            "saldo": None,
            "referenz": None,
            "roh": dict(row),  # Originaldaten für Debugging
        }

        for csv_spalte, ziel_feld in mapping.items():
            # csv.DictReader füllt zu kurze Zeilen mit None statt "" auf (restval) –
            # row.get(..., "") hilft dort nicht, da der Schlüssel existiert, nur der Wert None ist (Issue #247)
            wert = (row.get(csv_spalte) or "").strip()
            if not wert:
                continue

            if ziel_feld == "datum":
                tx["datum"] = parse_datum(wert, date_format)
            elif ziel_feld == "valuta":
                tx["valuta"] = parse_datum(wert, date_format)
            elif ziel_feld == "betrag":
                tx["betrag"] = parse_betrag(wert, decimal_separator)
            elif ziel_feld == "saldo":
                tx["saldo"] = parse_betrag(wert, decimal_separator)
            elif ziel_feld == "waehrung":
                tx["waehrung"] = wert[:3].upper()
            elif ziel_feld == "partner_name" and not tx["partner_name"]:
                tx["partner_name"] = wert[:200]
            elif ziel_feld == "partner_name_alt" and not tx["partner_name"]:
                # Fallback-Feld (z.B. DKB: Zahlungspflichtiger vs. Zahlungsempfänger)
                tx["partner_name"] = wert[:200]
            elif ziel_feld in tx:
                tx[ziel_feld] = wert

        # Zeile nur übernehmen wenn Datum und Betrag vorhanden
        if tx["datum"] is not None and tx["betrag"] is not None:
            ergebnis.append(tx)

    return ergebnis


def extract_konto_iban(raw: bytes, template) -> Optional[str]:
    """
    Sucht in den übersprungenen Header-Zeilen (skip_rows) nach der eigenen Konto-IBAN.
    Gibt die IBAN ohne Leerzeichen zurück oder None.
    """
    skip_rows = getattr(template, "skip_rows", 0)
    if skip_rows == 0:
        return None
    enc = detect_encoding(raw)
    text = raw.decode(enc, errors="replace")
    header_text = "\n".join(text.splitlines()[:skip_rows])
    match = _IBAN_RE.search(header_text)
    if match:
        iban = match.group(0).replace(" ", "")
        if len(iban) >= 15:
            return iban
    return None


def is_camt(raw: bytes) -> bool:
    """Erkennt CAMT ISO 20022 XML anhand der ersten 500 Bytes."""
    sniff = raw[:500]
    return b'<Document' in sniff and b'camt.' in sniff.lower()


def is_zip(raw: bytes) -> bool:
    return raw[:4] == b'PK\x03\x04'


def extract_xml_from_zip(raw: bytes) -> Optional[bytes]:
    """Gibt den Inhalt der ersten XML-Datei aus einem ZIP zurück (Legacy)."""
    import zipfile, io as _io
    try:
        with zipfile.ZipFile(_io.BytesIO(raw)) as zf:
            xml_names = sorted(n for n in zf.namelist() if n.lower().endswith('.xml'))
            if xml_names:
                return zf.read(xml_names[0])
    except Exception:
        pass
    return None


def parse_camt_from_zip(raw: bytes) -> tuple[Optional[str], list[dict]]:
    """Parst alle CAMT-XMLs aus einem ZIP-Archiv und gibt (konto_iban, transaktionen) zurück.
    Sparkasse und andere Banken liefern ZIP mit einer XML pro Monat.
    """
    import zipfile, io as _io
    try:
        with zipfile.ZipFile(_io.BytesIO(raw)) as zf:
            xml_names = sorted(n for n in zf.namelist() if n.lower().endswith('.xml'))
            if not xml_names:
                return None, []
            konto_iban: Optional[str] = None
            alle: list[dict] = []
            for name in xml_names:
                xml_raw = zf.read(name)
                if konto_iban is None:
                    konto_iban = extract_konto_iban_camt(xml_raw)
                alle.extend(parse_camt(xml_raw))
            return konto_iban, alle
    except Exception:
        pass
    return None, []


def extract_konto_iban_camt(raw: bytes) -> Optional[str]:
    """Extrahiert die eigene Konto-IBAN aus einem CAMT.053/054-XML."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(raw)
        ns_match = re.match(r'\{([^}]+)\}', root.tag)
        p = f'{{{ns_match.group(1)}}}' if ns_match else ''
        for path in [
            f'.//{p}Stmt/{p}Acct/{p}Id/{p}IBAN',
            f'.//{p}Ntfctn/{p}Acct/{p}Id/{p}IBAN',
            f'.//{p}Acct/{p}Id/{p}IBAN',
        ]:
            el = root.find(path)
            if el is not None and el.text:
                return el.text.strip().replace(' ', '')
    except Exception:
        pass
    return None


def parse_camt(raw: bytes) -> list[dict]:
    """Parst CAMT.053/054 ISO 20022 XML und gibt normalisierte Transaktionsdicts zurück."""
    import xml.etree.ElementTree as ET
    from decimal import InvalidOperation as _IE

    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []

    ns_match = re.match(r'\{([^}]+)\}', root.tag)
    p = f'{{{ns_match.group(1)}}}' if ns_match else ''

    ergebnis = []
    for ntry in root.iter(f'{p}Ntry'):
        tx: dict = {
            'datum': None, 'valuta': None, 'buchungstext': None,
            'verwendungszweck': None, 'partner_name': None, 'partner_iban': None,
            'partner_bic': None, 'betrag': None, 'waehrung': 'EUR',
            'saldo': None, 'referenz': None,
        }

        # Betrag + Vorzeichen
        amt_el = ntry.find(f'{p}Amt')
        if amt_el is None or not (amt_el.text or '').strip():
            continue
        try:
            betrag = Decimal(amt_el.text.strip())
        except (InvalidOperation, AttributeError):
            continue
        tx['waehrung'] = amt_el.get('Ccy', 'EUR')
        ind = ntry.find(f'{p}CdtDbtInd')
        if ind is not None and (ind.text or '').strip() == 'DBIT':
            betrag = -betrag
        tx['betrag'] = betrag

        # Buchungsdatum
        for date_tag in (f'{p}BookgDt/{p}Dt', f'{p}ValDt/{p}Dt'):
            el = ntry.find(date_tag)
            if el is not None and (el.text or '').strip():
                try:
                    tx['datum'] = datetime.strptime(el.text.strip(), '%Y-%m-%d').date()
                    break
                except ValueError:
                    pass
        if tx['datum'] is None:
            continue

        # Valutadatum
        val_el = ntry.find(f'{p}ValDt/{p}Dt')
        if val_el is not None and (val_el.text or '').strip():
            try:
                tx['valuta'] = datetime.strptime(val_el.text.strip(), '%Y-%m-%d').date()
            except ValueError:
                pass

        # Buchungstext
        addtl = ntry.find(f'{p}AddtlNtryInf')
        if addtl is not None and addtl.text:
            tx['buchungstext'] = addtl.text.strip()[:255]

        # Transaktionsdetails
        for td in ntry.iter(f'{p}TxDtls'):
            if not tx['verwendungszweck']:
                el = td.find(f'{p}RmtInf/{p}Ustrd')
                if el is not None and el.text:
                    tx['verwendungszweck'] = el.text.strip()[:500]

            if not tx['partner_name']:
                for nm_path in (
                    f'{p}RltdPties/{p}Cdtr/{p}Nm',
                    f'{p}RltdPties/{p}Dbtr/{p}Nm',
                ):
                    el = td.find(nm_path)
                    if el is not None and el.text:
                        tx['partner_name'] = el.text.strip()[:200]
                        break

            if not tx['partner_iban']:
                for iban_path in (
                    f'{p}RltdPties/{p}CdtrAcct/{p}Id/{p}IBAN',
                    f'{p}RltdPties/{p}DbtrAcct/{p}Id/{p}IBAN',
                ):
                    el = td.find(iban_path)
                    if el is not None and el.text:
                        tx['partner_iban'] = el.text.strip().replace(' ', '')
                        break

            if not tx['partner_bic']:
                for bic_path in (
                    f'{p}RltdAgts/{p}CdtrAgt/{p}FinInstnId/{p}BICFI',
                    f'{p}RltdAgts/{p}DbtrAgt/{p}FinInstnId/{p}BICFI',
                ):
                    el = td.find(bic_path)
                    if el is not None and el.text:
                        tx['partner_bic'] = el.text.strip()
                        break

            if not tx['referenz']:
                el = td.find(f'{p}Refs/{p}EndToEndId')
                if el is not None and el.text:
                    tx['referenz'] = el.text.strip()[:100]

        ergebnis.append(tx)
    return ergebnis


def parse_csv_mit_template(raw: bytes, template) -> tuple[list[dict], str]:
    """
    Parst raw-Bytes mit einem BankTemplate-Objekt.
    Gibt (transaktionen, erkannte_encoding) zurück.
    """
    mapping = json.loads(template.column_mapping) if isinstance(template.column_mapping, str) else template.column_mapping
    enc = detect_encoding(raw)

    transaktionen = parse_csv(
        raw=raw,
        column_mapping=mapping,
        delimiter=template.delimiter,
        encoding=template.encoding or enc,
        decimal_separator=template.decimal_separator,
        date_format=template.date_format,
        skip_rows=template.skip_rows,
    )
    return transaktionen, enc
