"""
CSV-Import für Alt-Rechnungen und Alt-Belege (Issue #445).

Übernimmt die Rechnungs-/Beleghistorie aus anderen Buchhaltungssystemen
(z. B. dem Papierkram-Export `rechnungen.csv` / `belege.csv`) als
Ausgangs- bzw. Eingangsrechnungen.

Wichtig: Der Import legt keine eigenen Datenmodelle an, sondern nutzt die
bestehenden Erstellungs- und Zahlungspfade (`create_rechnung`,
`zahlung_bar_erstellen`). Damit bleiben GoBD-Signaturen, Kontenzuordnung
und Zuflussprinzip identisch zur manuellen Erfassung. Original-
Rechnungsnummern und Original-Daten werden erhalten (vgl. Issue #346).
"""

import csv
import io
import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Kunde, Lieferant, Kategorie, Rechnung

from .rechnungen import _create_rechnung, zahlung_bar_erstellen
from .schemas_rechnungen import BarZahlungCreate, RechnungCreate, RechnungspositionCreate

router = APIRouter(prefix="/api/rechnungen-import", tags=["Rechnungen-Import"])

TYP_RECHNUNGEN = "rechnungen"
TYP_BELEGE = "belege"

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ImportZeileErgebnis(BaseModel):
    zeile: int
    rechnungsnummer: Optional[str] = None
    partner: Optional[str] = None
    status: str  # importiert | uebersprungen | fehler
    begruendung: Optional[str] = None
    rechnung_id: Optional[int] = None
    zahlung_id: Optional[int] = None
    warnungen: list[str] = []


class ImportErgebnis(BaseModel):
    importiert: int
    uebersprungen: int
    fehler: int
    zeilen: list[ImportZeileErgebnis]


class VorschauZeile(BaseModel):
    zeile: int
    rechnungsnummer: Optional[str] = None
    partner: Optional[str] = None
    partner_match: str = "freitext"  # stammdaten | freitext
    datum: Optional[date] = None
    brutto: Optional[Decimal] = None
    bezahlt_betrag: Optional[Decimal] = None
    bezahlt_am: Optional[date] = None
    kategorie: Optional[str] = None
    kategorie_quelle: Optional[str] = None
    kategorie_match: bool = False
    fehler: list[str] = []
    warnungen: list[str] = []


# ---------------------------------------------------------------------------
# Parsing-Helfer (Papierkram-Export: Semikolon, deutsche Beträge, mischte Datumsformate)
# ---------------------------------------------------------------------------

def _detect_delimiter(sample: str) -> str:
    first_line = sample.splitlines()[0] if sample else ""
    counts = {d: first_line.count(d) for d in (";", ",", "\t")}
    best = max(counts, key=lambda d: counts[d])
    return best if counts[best] > 0 else ";"


def _parse_amount(raw: Optional[str]) -> Optional[Decimal]:
    """Deutsche Beträge ('15,00', '-56,99', '1.234,56') und einfache ISO-Beträge."""
    if raw is None:
        return None
    s = raw.strip().replace("€", "").replace("EUR", "").replace(" ", "").strip()
    if not s:
        return None
    # Deutsche Schreibweise: Komma als Dezimaltrenner, Punkt als Tausender
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _parse_date(raw: Optional[str]) -> Optional[date]:
    """Akzeptiert '15.10.2026' (deutsch) und '2026-10-16' (ISO)."""
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


_LAND_KURZ = re.compile(r"^[A-Z]{2}$")

def _land_code(raw: Optional[str]) -> str:
    s = (raw or "").strip()
    mapping = {
        "deutschland": "DE", "österreich": "AT", "schweiz": "CH",
        "liechtenstein": "LI", "luxemburg": "LU", "italien": "IT",
        "frankreich": "FR", "niederlande": "NL", "belgien": "BE",
    }
    if s.lower() in mapping:
        return mapping[s.lower()]
    if _LAND_KURZ.match(s):
        return s.upper()
    return "DE"


def _read_csv_rows(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig", errors="replace")
    delimiter = _detect_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    rows = []
    for row in reader:
        # Papierkram schreibt leere Felder als "" – auf None normalisieren
        cleaned = {
            (k.strip() if k else k): (v.strip() if isinstance(v, str) and v.strip() else None)
            for k, v in row.items()
        }
        if any(v for v in cleaned.values()):  # Leerzeilen überspringen
            rows.append(cleaned)
    return rows


def _get(row: dict, *names: str) -> Optional[str]:
    """Erst spaltenweise, dann case-insensitive nach Namen suchen."""
    for n in names:
        if row.get(n) is not None:
            return row[n]
    lower = {k.lower(): v for k, v in row.items() if k}
    for n in names:
        if lower.get(n.lower()) is not None:
            return lower[n.lower()]
    return None


# ---------------------------------------------------------------------------
# Partner-/Kategorie-Matching
# ---------------------------------------------------------------------------

def _matche_kunde(db: Session, kundennummer: Optional[str], name: Optional[str]) -> Optional[Kunde]:
    if kundennummer:
        kunde = db.query(Kunde).filter(Kunde.kundennummer == kundennummer).first()
        if kunde:
            return kunde
    if name:
        name_l = name.strip().lower()
        for kunde in db.query(Kunde).all():
            firmenname = (kunde.firmenname or "").strip().lower()
            vollname = f"{kunde.vorname or ''} {kunde.nachname or ''}".strip().lower()
            if firmenname == name_l or vollname == name_l:
                return kunde
    return None


def _matche_lieferant(db: Session, name: Optional[str]) -> Optional[Lieferant]:
    if not name:
        return None
    name_l = name.strip().lower()
    for lief in db.query(Lieferant).all():
        firmenname = (lief.firmenname or "").strip().lower()
        vollname = f"{lief.vorname or ''} {lief.nachname or ''}".strip().lower()
        if firmenname == name_l or vollname == name_l:
            return lief
    return None


def _matche_kategorie(db: Session, raw: Optional[str], mapping: Optional[dict[str, str]] = None) -> Optional[Kategorie]:
    """Papierkram-Kategorien können mehrere, kommagetrennte Namen enthalten –
    gematcht wird erst gegen die optionale Zuordnung (Papierkram-Name ->
    RechnungsFee-Name), dann exakt (case-insensitive) gegen den ersten Treffer.
    Kein automatisches 'ähnlich'-Matching: Kategorien steuern Konten und
    Vorsteuerquoten, eine falsche Zuordnung wäre ein Buchungsfehler."""
    if not raw:
        return None
    # Erst die ganze Zeichenkette (Kategorienamen dürfen Kommas enthalten!),
    # erst dann Multiple-Category-Versuch über Komma/Semikolon-Split.
    candidates = [raw.strip()] + [p.strip() for p in re.split(r"[;,]", raw) if p.strip()]
    for part in candidates:
        if not part:
            continue
        ziel = (mapping or {}).get(part) or (mapping or {}).get(part.lower())
        if ziel:
            kat = db.query(Kategorie).filter(Kategorie.name == ziel).first()
            if kat:
                return kat
        kat = db.query(Kategorie).filter(
            sa_func.lower(Kategorie.name) == part.lower()
        ).first()
        if kat:
            return kat
    return None


# ---------------------------------------------------------------------------
# Zeilen-Auswertung (rein – für Vorschau und Import identisch)
# ---------------------------------------------------------------------------

class _AusgewerteteZeile:
    def __init__(self) -> None:
        self.rechnungsnummer: Optional[str] = None
        self.externe_belegnr: Optional[str] = None
        self.beschreibung: Optional[str] = None
        self.partner_name: Optional[str] = None
        self.kunde: Optional[Kunde] = None
        self.lieferant: Optional[Lieferant] = None
        self.kategorie: Optional[Kategorie] = None
        self.datum: Optional[date] = None
        self.faellig_am: Optional[date] = None
        self.netto: Optional[Decimal] = None
        self.ust: Optional[Decimal] = None
        self.brutto: Optional[Decimal] = None
        self.ust_satz: Decimal = Decimal("0")
        self.bezahlt_betrag: Optional[Decimal] = None
        self.bezahlt_am: Optional[date] = None
        self.notizen: Optional[str] = None
        self.land: str = "DE"
        self.fehler: list[str] = []
        self.warnungen: list[str] = []


def _auswerte_zeile(db: Session, typ: str, row: dict, kategorie_mapping: Optional[dict[str, str]] = None) -> _AusgewerteteZeile:
    z = _AusgewerteteZeile()

    if typ == TYP_RECHNUNGEN:
        z.rechnungsnummer = _get(row, "Rechnungsnr.", "Rechnungsnummer", "Rechnungsnr")
        z.beschreibung = _get(row, "Betreff", "Gegenstand") or "Rechnung"
        z.partner_name = _get(row, "Kunde", "Kundenname")
        kundennummer = _get(row, "Kundennummer", "Kunden-Nr.")
        z.land = _land_code(_get(row, "Land", "Land (Post)"))
        z.datum = _parse_date(_get(row, "Datum", "Rechnungsdatum"))
        z.faellig_am = _parse_date(_get(row, "Fälligkeitsdatum", "Faelligkeitsdatum", "Fällig am"))
        status = (_get(row, "Status") or "").strip().lower()
        dokument_typ = (_get(row, "Typ") or "Rechnung").strip()
        z.netto = _parse_amount(_get(row, "Netto", "Netto (Netto)"))
        z.ust = _parse_amount(_get(row, "USt.", "USt", "Umsatzsteuer"))
        z.brutto = _parse_amount(_get(row, "Brutto", "Brutto (Brutto)"))
        z.bezahlt_betrag = _parse_amount(_get(row, "Bezahlt", "Bezahlt (Bezahlt)"))
        z.bezahlt_am = _parse_date(_get(row, "letztes Bezahldatum", "Zahlung am", "Bezahldatum"))
        z.notizen = _get(row, "Notiz", "Notizen")

        if dokument_typ != "Rechnung":
            z.fehler.append(f"Dokumenttyp '{dokument_typ}' wird nicht importiert (nur 'Rechnung').")
        if not z.rechnungsnummer:
            z.fehler.append("Spalte 'Rechnungsnr.' fehlt/leer.")
        elif db.query(Rechnung).filter(Rechnung.rechnungsnummer == z.rechnungsnummer).first():
            z.fehler.append(f"Rechnungsnummer {z.rechnungsnummer} existiert bereits.")
        if not z.datum:
            z.fehler.append("Spalte 'Datum' fehlt oder ist kein gültiges Datum.")
        elif z.datum > date.today():
            z.fehler.append(f"Rechnungsdatum {z.datum.strftime('%d.%m.%Y')} liegt in der Zukunft.")
        if not z.partner_name and not kundennummer:
            z.fehler.append("Weder 'Kunde' noch 'Kundennummer' angegeben.")
        else:
            z.kunde = _matche_kunde(db, kundennummer, z.partner_name)
            if not z.kunde:
                z.warnungen.append("Kein Kunde aus den Stammdaten gefunden – Partner wird als Freitext übernommen.")
        _pruefe_betaege(z)
        zahlungsstatus_abgeschlossen = status in ("bezahlt", "überbezahlt", "ueberbezahlt", "paid")
        if status == "teilweise" or (z.bezahlt_betrag is not None and z.bezahlt_betrag > 0 and not zahlungsstatus_abgeschlossen):
            z.fehler.append(
                "Teilzahlungen/Ratenzahlungen werden beim CSV-Import nicht unterstützt – "
                "bitte manuell erfassen."
            )
        if zahlungsstatus_abgeschlossen and z.brutto is not None:
            if z.bezahlt_betrag is None or z.bezahlt_betrag <= 0:
                z.bezahlt_betrag = z.brutto
            if z.bezahlt_am is None:
                z.bezahlt_am = z.faellig_am or z.datum
                if z.bezahlt_am:
                    z.warnungen.append("Kein Zahlungsdatum in der CSV – Zahlungsdatum der Fälligkeit/des Rechnungsdatums verwendet.")
        elif status in ("unbezahlt", "offen", ""):
            z.bezahlt_betrag = None
        else:
            z.warnungen.append(f"Unbekannter Status '{status}' – ohne Zahlung importiert.")
    else:  # TYP_BELEGE
        herkunftsort = (_get(row, "Herkunftsort") or "").strip().lower()
        if herkunftsort != "domestic":
            z.fehler.append(
                "Herkunftsort ist nicht 'domestic' – EU-/Drittland-Belege (z. B. Reverse-Charge) "
                "bitte vorerst manuell erfassen."
            )
        z.externe_belegnr = _get(row, "Belegnummer", "Beleg-Nr.")
        z.beschreibung = _get(row, "Gegenstand", "Betreff") or "Beleg"
        z.partner_name = _get(row, "Lieferant", "Lieferantenname")
        z.datum = _parse_date(_get(row, "Datum", "Belegdatum"))
        z.faellig_am = _parse_date(_get(row, "Zahlungsfrist", "Fälligkeitsdatum"))
        status = (_get(row, "Status") or "").strip().lower()
        # Papierkram führt Ausgaben negativ – RechnungsFee speichert Eingangsrechnungen positiv
        z.netto = _abs_or_none(_parse_amount(_get(row, "Netto")))
        z.ust = _abs_or_none(_parse_amount(_get(row, "USt.", "USt", "Umsatzsteuer")))
        z.brutto = _abs_or_none(_parse_amount(_get(row, "Brutto")))
        z.bezahlt_betrag = _abs_or_none(_parse_amount(_get(row, "Bezahlt", "Bezahlt (Bezahlt)")))
        z.bezahlt_am = _parse_date(_get(row, "Zahlung am", "letztes Bezahldatum", "Bezahldatum"))
        z.notizen = _get(row, "Notizen", "Notiz")
        kategorie_raw = _get(row, "Kategorien", "Kategorie")
        privatanteil = _parse_amount(_get(row, "Privatanteil"))
        if privatanteil and privatanteil > 0:
            z.warnungen.append(f"Privatanteil {privatanteil} wird nicht getrennt importiert – bitte nachträglich splitten.")

        if not z.datum:
            z.fehler.append("Spalte 'Datum' fehlt oder ist kein gültiges Datum.")
        elif z.datum > date.today():
            z.fehler.append(f"Belegdatum {z.datum.strftime('%d.%m.%Y')} liegt in der Zukunft.")
        if not z.partner_name:
            z.fehler.append("Spalte 'Lieferant' fehlt/leer.")
        else:
            z.lieferant = _matche_lieferant(db, z.partner_name)
            if not z.lieferant:
                z.warnungen.append("Kein Lieferant aus den Stammdaten gefunden – Partner wird als Freitext übernommen.")
        if z.externe_belegnr and db.query(Rechnung).filter(Rechnung.externe_belegnr == z.externe_belegnr).first():
            z.fehler.append(f"Externe Belegnummer {z.externe_belegnr} existiert bereits.")
        _pruefe_betaege(z)
        if status in ("paid", "bezahlt", "überbezahlt", "ueberbezahlt") and z.brutto is not None:
            if z.bezahlt_betrag is None or z.bezahlt_betrag <= 0:
                z.bezahlt_betrag = z.brutto
            if z.bezahlt_am is None:
                z.bezahlt_am = z.faellig_am or z.datum
                if z.bezahlt_am:
                    z.warnungen.append("Kein Zahlungsdatum in der CSV – Zahlungsdatum der Fälligkeit/des Belegdatums verwendet.")
            if z.brutto is not None:
                z.kategorie = _matche_kategorie(db, kategorie_raw, kategorie_mapping)
                if z.kategorie and z.kategorie.kontenart == "Erlös":
                    z.fehler.append(
                        f"Kategorie '{z.kategorie.name}' ist eine Erlöskategorie – "
                        "Eingangsbelege können nicht darauf gebucht werden."
                    )
                    z.kategorie = None
                if not z.kategorie and not z.fehler:
                    z.warnungen.append("Kategorie nicht in den Stammdaten gefunden – Zahlung wird nicht gebucht (bitte manuell kategorisieren).")
        else:
            z.bezahlt_betrag = None

    return z


def _abs_or_none(v: Optional[Decimal]) -> Optional[Decimal]:
    return abs(v) if v is not None else None


def _pruefe_betaege(z: _AusgewerteteZeile) -> None:
    """Netto + USt muss Brutto ergeben (1-Cent-Toleranz); USt-Satz ableiten."""
    if z.netto is None or z.brutto is None:
        z.fehler.append("Netto- oder Bruttobetrag fehlt/ist ungültig.")
        return
    if z.ust is None:
        z.ust = Decimal("0")
    if abs(z.netto + z.ust - z.brutto) > Decimal("0.01"):
        z.fehler.append(f"Beträge inkonsistent: Netto {z.netto} + USt {z.ust} != Brutto {z.brutto}.")
        return
    if z.ust == 0:
        z.ust_satz = Decimal("0")
        return
    if z.netto == 0:
        z.fehler.append("USt-Betrag bei Netto 0 ist ungültig.")
        return
    passende_saetze = (Decimal("7"), Decimal("19"))
    satz = next((rate for rate in passende_saetze if abs(
        z.ust - (z.netto * rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    ) <= Decimal("0.01")), None)
    if satz is None:
        z.fehler.append(
            "Gemischte Steuersätze oder ungültiger USt-Satz erkannt – bitte manuell erfassen. "
            "Unterstützt werden nur 0 %, 7 % und 19 % (mit 1-Cent-Rundungstoleranz)."
        )
        return
    z.ust_satz = satz


# ---------------------------------------------------------------------------
# Endpunkte
# ---------------------------------------------------------------------------

def _csv_lesen(datei: UploadFile) -> list[dict]:
    content = datei.file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Die Datei ist leer.")
    try:
        rows = _read_csv_rows(content)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"CSV konnte nicht gelesen werden: {exc}")
    if not rows:
        raise HTTPException(status_code=422, detail="Die CSV enthält keine Datenzeilen.")
    return rows


def _pruefe_typ(typ: str) -> str:
    if typ not in (TYP_RECHNUNGEN, TYP_BELEGE):
        raise HTTPException(status_code=422, detail=f"typ muss '{TYP_RECHNUNGEN}' oder '{TYP_BELEGE}' sein.")
    return typ


def _parse_mapping(raw: str) -> Optional[dict[str, str]]:
    """Optionales Formularfeld: JSON-Objekt Papierkram-Kategorie -> RechnungsFee-Kategorie."""
    if not raw or not raw.strip():
        return None
    try:
        mapping = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"kategorie_mapping ist kein gültiges JSON: {exc}")
    if not isinstance(mapping, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()):
        raise HTTPException(status_code=422, detail="kategorie_mapping muss ein JSON-Objekt aus Strings sein.")
    return mapping


@router.post("/vorschau", response_model=list[VorschauZeile])
async def import_vorschau(
    datei: UploadFile = File(...),
    typ: str = Form(TYP_RECHNUNGEN),
    kategorie_mapping: str = Form(""),
    db: Session = Depends(get_db),
):
    """CSV hochladen und Zeilen validieren – schreibt nichts in die Datenbank."""
    typ = _pruefe_typ(typ)
    mapping = _parse_mapping(kategorie_mapping)
    rows = _csv_lesen(datei)
    seen: set[str] = set()
    ergebnis: list[VorschauZeile] = []
    for idx, row in enumerate(rows, start=2):  # Zeile 1 = Header
        z = _auswerte_zeile(db, typ, row, mapping)
        nr = z.rechnungsnummer or z.externe_belegnr
        if nr:
            if nr in seen:
                z.fehler.append(f"Nummer {nr} kommt in der CSV mehrfach vor.")
            seen.add(nr)
        ergebnis.append(VorschauZeile(
            zeile=idx,
            rechnungsnummer=nr,
            partner=z.partner_name,
            partner_match="stammdaten" if (z.kunde or z.lieferant) else "freitext",
            datum=z.datum,
            brutto=z.brutto,
            bezahlt_betrag=z.bezahlt_betrag,
            bezahlt_am=z.bezahlt_am,
            kategorie=z.kategorie.name if z.kategorie else None,
            kategorie_quelle=(
                _get(row, "Kategorien", "Kategorie")
                if typ == TYP_BELEGE and z.bezahlt_betrag and z.bezahlt_betrag > 0
                else None
            ),
            kategorie_match=z.kategorie is not None,
            fehler=z.fehler,
            warnungen=z.warnungen,
        ))
    return ergebnis


@router.post("/importieren", response_model=ImportErgebnis)
async def import_durchfuehren(
    datei: UploadFile = File(...),
    typ: str = Form(TYP_RECHNUNGEN),
    kategorie_mapping: str = Form(""),
    db: Session = Depends(get_db),
):
    """CSV importieren. Fehlerhafte Zeilen werden übersprungen, gute Zeilen
    über die regulären Erstellungs-/Zahlungspfade gebucht."""
    typ = _pruefe_typ(typ)
    mapping = _parse_mapping(kategorie_mapping)
    rows = _csv_lesen(datei)
    seen: set[str] = set()
    ergebnis: list[ImportZeileErgebnis] = []
    importiert = uebersprungen = fehler = 0

    for idx, row in enumerate(rows, start=2):
        z = _auswerte_zeile(db, typ, row, mapping)
        nr = z.rechnungsnummer or z.externe_belegnr
        if nr:
            if nr in seen:
                z.fehler.append(f"Nummer {nr} kommt in der CSV mehrfach vor.")
            seen.add(nr)

        if z.fehler:
            fehler += 1
            ergebnis.append(ImportZeileErgebnis(
                zeile=idx, rechnungsnummer=nr, partner=z.partner_name,
                status="fehler", begruendung="; ".join(z.fehler),
            ))
            continue

        # Nach Fehlerprüfung sind datum/netto gesetzt – Guard nur für die Typen.
        if z.datum is None or z.netto is None:
            fehler += 1
            ergebnis.append(ImportZeileErgebnis(
                zeile=idx, rechnungsnummer=nr, partner=z.partner_name,
                status="fehler", begruendung="Datum oder Netto nicht auswertbar.",
            ))
            continue

        try:
            create = RechnungCreate(
                typ="ausgang" if typ == TYP_RECHNUNGEN else "eingang",
                rechnungsnummer=z.rechnungsnummer,  # Originalnummer erhalten (bei Belegen: None → Nummernkreis)
                externe_belegnr=z.externe_belegnr,
                datum=z.datum,
                faellig_am=z.faellig_am,
                kunde_id=z.kunde.id if z.kunde else None,
                lieferant_id=z.lieferant.id if z.lieferant else None,
                partner_freitext=None if (z.kunde or z.lieferant) else z.partner_name,
                partner_land=z.land,
                kategorie_id=z.kategorie.id if z.kategorie else None,
                notizen=z.notizen,
                ist_entwurf=False,
                dokument_typ="Rechnung",
                netto_gesamt_override=z.netto,
                ust_gesamt_override=z.ust,
                brutto_gesamt_override=z.brutto,
                positionen=[RechnungspositionCreate(
                    beschreibung=z.beschreibung or (z.rechnungsnummer or z.externe_belegnr or "Rechnung"),
                    menge=Decimal("1"),
                    netto=z.netto,
                    ust_satz=z.ust_satz,
                    kategorie_id=z.kategorie.id if z.kategorie else None,
                )],
            )
            rechnung = _create_rechnung(create, db, import_quelle="papierkram")
        except HTTPException as exc:
            db.rollback()
            fehler += 1
            ergebnis.append(ImportZeileErgebnis(
                zeile=idx, rechnungsnummer=nr, partner=z.partner_name,
                status="fehler", begruendung=f"Anlage fehlgeschlagen: {exc.detail}",
            ))
            continue

        zahlung_id: Optional[int] = None
        warnungen = list(z.warnungen)
        if z.bezahlt_betrag and z.bezahlt_betrag > 0:
            if typ == TYP_BELEGE and not z.kategorie:
                warnungen.append("Beleg ohne Zahlung importiert – Kategorie fehlt (Zahlung manuell erfassen).")
            else:
                try:
                    zahlung = zahlung_bar_erstellen(
                        rechnung.id,
                        BarZahlungCreate(
                            betrag=z.bezahlt_betrag,
                            datum=z.bezahlt_am or z.datum,
                            zahlungsart="Bank",
                            kategorie_id=z.kategorie.id if z.kategorie else None,
                            beschreibung="Import Altbestand",
                        ),
                        db,
                    )
                    zahlung_id = zahlung.journaleintrag_id
                except HTTPException as exc:
                    warnungen.append(f"Rechnung importiert, Zahlung nicht gebucht: {exc.detail}")

        status = "importiert"
        ergebnis.append(ImportZeileErgebnis(
            zeile=idx, rechnungsnummer=rechnung.rechnungsnummer or nr,
            partner=z.partner_name, status=status,
            rechnung_id=rechnung.id, zahlung_id=zahlung_id,
            warnungen=warnungen,
        ))
        importiert += 1

    return ImportErgebnis(
        importiert=importiert, uebersprungen=uebersprungen, fehler=fehler, zeilen=ergebnis,
    )


@router.get("/muster-csv/{typ}")
def muster_csv(typ: str):
    """Muster-CSV im erwarteten Format (analog `datenmigration/muster-csv`)."""
    typ = _pruefe_typ(typ)
    if typ == TYP_RECHNUNGEN:
        content = (
            "Rechnungsnr.;Betreff;Kunde;Land;Projekt;Kundennummer;Datum;Fälligkeitsdatum;"
            "Status;Typ;Netto;USt.;Brutto;Skonto;Bezahlt;letztes Bezahldatum;Notiz;Mahnungsdatum;"
            "Waren & Dienstleistungen\n"
            "R-00001;Rechnung Mai 2026;Beispiel Kunde;Deutschland;;K-00010;15.05.2026;29.05.2026;"
            "Bezahlt;Rechnung;45,00;0,00;45,00;0,00;45,00;2026-05-20;;;\n"
            "R-00002;Rechnung Juni 2026;Beispiel Kunde;Deutschland;;K-00010;15.06.2026;29.06.2026;"
            "Unbezahlt;Rechnung;60,00;0,00;60,00;0,00;0,00;;;;\n"
        )
    else:
        content = (
            "Belegnummer;Gegenstand;Lieferant;Datum;Zahlungsfrist;Zahlung am;Status;Netto;USt.;"
            "Brutto;Privatanteil;Herkunftsort;Kategorien;Projekte;Projektkunden;Projektkunden-Nr;"
            "Zusatz;Notizen\n"
            "B-00001;Bürobedarf;Beispiel Lieferant GmbH;03.08.2026;03.08.2026;2026-07-19;paid;"
            "-56,99;0,00;-56,99;0;domestic;Bürobedarf;;;;;;\n"
        )
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content, media_type="text/csv; charset=utf-8")
