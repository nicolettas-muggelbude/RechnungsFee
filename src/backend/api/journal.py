"""
Journal-API (GoBD-konform, unveränderbar).
Kein PUT/DELETE – nur Storno als Gegenbuchung.
"""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Optional

import csv
import hashlib
import io
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from sqlalchemy import func, extract, or_
from sqlalchemy.orm import Session

from database.connection import get_db, APP_DATA_DIR
from database.models import BankTransaktion, Beleg, Journaleintrag, Kategorie, Tagesabschluss, Unternehmen, Nummernkreis
from utils.signatur import signatur_journaleintrag
from utils.pdfa_konverter import konvertiere_zu_pdfa
from utils.rechnungs_parser import analysiere_datei
from .schemas import (
    JournalEintragCreate,
    JournalEintragResponse,
    StornoRequest,
    SplitBuchungCreate,
    MonatsUebersicht,
)
from .schemas_rechnungen import BelegResponse

BELEG_DIR = APP_DATA_DIR / "uploads" / "belege"
ERLAUBTE_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/tiff"}

router = APIRouter(prefix="/api/journal", tags=["Journal"])


import re as _re


def _belegnr_aus_format(format_str: str, datum: date, nr: int) -> str:
    """Wendet das Format-Template an. Y=Jahrsstelle, MM=Monat, TT=Tag, #=Nummernstelle.
    Gross-/Kleinschreibung der Platzhalter wird nicht unterschieden (Nutzer-Feedback:
    ein von Hand eingetipptes Format wie "RE-tt.mm.yyyy" in Kleinbuchstaben wurde bisher
    gar nicht ersetzt, da die Suche nur exakt YYYY/YY/MM/TT in Grossbuchstaben fand - die
    Rechnungsnummer erschien dann unveraendert als Format-Vorlage statt als echte Nummer).
    Reihenfolge bleibt YYYY vor YY wichtig, sonst wuerde YYYY faelschlich als zwei YY erkannt."""
    year_4 = str(datum.year)
    year_2 = year_4[-2:]
    month  = f"{datum.month:02d}"
    day    = f"{datum.day:02d}"
    result = _re.sub("YYYY", year_4, format_str, flags=_re.IGNORECASE)
    result = _re.sub("YY",   year_2, result,     flags=_re.IGNORECASE)
    result = _re.sub("MM",   month,  result,     flags=_re.IGNORECASE)
    result = _re.sub("TT",   day,    result,     flags=_re.IGNORECASE)

    def _pad(m: _re.Match) -> str:
        return str(nr).zfill(len(m.group()))

    return _re.sub(r"#+", _pad, result)


def _storno_infos(db: Session, eintraege: list[Journaleintrag]) -> dict[int, dict]:
    """Ermittelt fuer eine Liste von Journaleintraegen den Storno-Status in konstant zwei
    Zusatzabfragen (unabhaengig von der Listengroesse) - liefert je Eintrag-id ein Dict mit
    storniert/storno_belegnr (Gegenbuchung existiert) und ist_storno/storno_von_belegnr
    (dieser Eintrag ist selbst eine Gegenbuchung). Nutzt dieselbe Erkennung (Beschreibungs-
    Praefix "STORNO " + gruppe_id-Wurzel) wie die bestehende bereits_storniert-Pruefung beim
    Stornieren selbst - macht sie fuer Lese-Endpunkte nutzbar statt sie clientseitig fragil
    nachzubauen (Issue #321).

    Bekannte Einschraenkung: gruppe_id gruppiert die gesamte Korrekturkette unter der
    Wurzel-id, nicht das einzelne Kettenglied - bei mehr als einer Korrektur derselben
    Buchung (Original -> Storno -> Neu -> erneut storniert -> ...) markiert dieses Ergebnis
    alle Nicht-Storno-Mitglieder der Kette als storniert, sobald irgendein Storno in der
    Kette existiert. Deckt den weit ueberwiegenden Fall (eine Korrektur) exakt ab."""
    wurzel_ids = {e.gruppe_id or e.id for e in eintraege}
    stornos = db.query(Journaleintrag).filter(
        Journaleintrag.beschreibung.like("STORNO %"),
        Journaleintrag.gruppe_id.in_(wurzel_ids),
    ).all() if wurzel_ids else []
    storno_je_wurzel: dict[int, str] = {s.gruppe_id: s.belegnr for s in stornos if s.gruppe_id}

    original_ids = {s.gruppe_id for s in stornos if s.gruppe_id}
    originale = db.query(Journaleintrag.id, Journaleintrag.belegnr).filter(
        Journaleintrag.id.in_(original_ids)
    ).all() if original_ids else []
    belegnr_je_original_id: dict[int, str] = dict(originale)

    ergebnis: dict[int, dict] = {}
    for e in eintraege:
        info = {"storniert": False, "storno_belegnr": None, "ist_storno": False, "storno_von_belegnr": None}
        # gruppe_id kann nicht über JournalEintragCreate gesetzt werden - stammt ausschließlich
        # von der Storno-Erstellung selbst. Beschreibungs-Praefix ALLEIN wuerde faelschlich auch
        # eine eigene Buchung erfassen, deren Text zufaellig mit "STORNO " beginnt (Issue #321).
        ist_storno = e.gruppe_id is not None and e.beschreibung.startswith("STORNO ")
        if ist_storno:
            info["ist_storno"] = True
            info["storno_von_belegnr"] = belegnr_je_original_id.get(e.gruppe_id)
        else:
            wurzel = e.gruppe_id or e.id
            if wurzel in storno_je_wurzel:
                info["storniert"] = True
                info["storno_belegnr"] = storno_je_wurzel[wurzel]
        ergebnis[e.id] = info
    return ergebnis


def _mit_storno_info(response: "JournalEintragResponse", info: dict) -> "JournalEintragResponse":
    response.storniert = info["storniert"]
    response.storno_belegnr = info["storno_belegnr"]
    response.ist_storno = info["ist_storno"]
    response.storno_von_belegnr = info["storno_von_belegnr"]
    return response


def _naechste_belegnr(db: Session, datum: date) -> str:
    """Liest den Journal-Nummernkreis, generiert die nächste Belegnummer
    und speichert den inkrementierten Zähler (atomar im selben Commit)."""
    nk = db.query(Nummernkreis).filter(Nummernkreis.typ == "journal").first()
    if not nk:
        # Fallback falls Seed fehlt
        count = db.query(Journaleintrag).count()
        return f"{str(datum.year)[-2:]}{count + 1:04d}"

    # Jahreswechsel-Reset nur vorwärts (Rückdatierung in älteres Jahr darf Counter nicht zurücksetzen)
    if nk.reset_jaehrlich and nk.letztes_jahr and datum.year > nk.letztes_jahr:
        nk.naechste_nr = 1
    if not nk.letztes_jahr or datum.year > nk.letztes_jahr:
        nk.letztes_jahr = datum.year

    nr = nk.naechste_nr
    nk.naechste_nr += 1
    candidate = _belegnr_aus_format(nk.format, datum, nr)
    # Kollisions-Schutz: belegnr überspringen wenn sie durch Rückdatierung bereits vergeben wurde
    while db.query(Journaleintrag).filter(Journaleintrag.belegnr == candidate).first():
        nr = nk.naechste_nr
        nk.naechste_nr += 1
        candidate = _belegnr_aus_format(nk.format, datum, nr)
    return candidate


def _berechne_ust(brutto: Decimal, ust_satz: Decimal) -> tuple[Decimal, Decimal]:
    """Gibt (netto, ust_betrag) zurück. ROUND_HALF_UP auf 2 Stellen."""
    if ust_satz == 0:
        return brutto, Decimal("0.00")
    netto = (brutto * 100 / (100 + ust_satz)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    ust_betrag = (brutto - netto).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return netto, ust_betrag


def _berechne_vorsteuer(ust_betrag: Decimal, vorsteuerabzug: bool, kat, ist_reverse_charge: bool = False) -> Decimal:
    """Tatsächlich abziehbarer Vorsteuer-Betrag.
    Berücksichtigt kat.vorsteuer_prozent (z.B. 70% bei nicht vollständig abzugsfähigen Kosten).
    Bei ist_reverse_charge=True (ig. Erwerb/§13b/Einfuhrumsatzsteuer) greift stattdessen §15
    Abs. 1 Nr. 3/4 UStG unabhängig vom Kategorie-Wert: eine Kategorie mit vorsteuer_prozent=0
    trifft nur eine Aussage über den *inländischen Normalfall* (z.B. inländisch steuerfreie
    Bankgebühren, §4 Nr. 8 UStG) - beim Reverse Charge ist die Vorsteuer trotzdem in voller
    Höhe abziehbar, da sie die selbst geschuldete USt exakt spiegelt (Issue #339).
    Storno-Einträge übergeben -ust_betrag damit sich Originalwert und Storno aufheben."""
    if not vorsteuerabzug or ust_betrag == 0:
        return Decimal("0.00")
    if ist_reverse_charge:
        return ust_betrag
    if kat is not None and int(kat.vorsteuer_prozent) < 100:
        return (ust_betrag * kat.vorsteuer_prozent / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return ust_betrag


def _ust_konto(art: str, ust_satz: Decimal) -> tuple[str | None, str | None]:
    """Gibt (konto_skr03, konto_skr04) für den USt-Anteil zurück."""
    satz = int(ust_satz)
    if art == "Einnahme":
        skr03 = {19: "1776", 7: "1771"}.get(satz)
        skr04 = {19: "3806", 7: "3801"}.get(satz)
    else:
        skr03 = {19: "1575", 7: "1570"}.get(satz)
        skr04 = {19: "1406", 7: "1401"}.get(satz)
    return skr03, skr04


def _get_bar_kassenstand(db: Session) -> Decimal:
    """Gibt den aktuellen Kassenstand der Barkasse zurück (nur Bar-Buchungen)."""
    einnahmen = db.query(func.sum(Journaleintrag.brutto_betrag)).filter(
        Journaleintrag.art == "Einnahme",
        Journaleintrag.zahlungsart == "Bar",
    ).scalar() or Decimal("0")
    ausgaben = db.query(func.sum(Journaleintrag.brutto_betrag)).filter(
        Journaleintrag.art == "Ausgabe",
        Journaleintrag.zahlungsart == "Bar",
    ).scalar() or Decimal("0")
    return Decimal(str(einnahmen)) - Decimal(str(ausgaben))


@router.get("/kassenstand")
def get_kassenstand(db: Session = Depends(get_db)):
    """Gibt den aktuellen Kassenstand der Barkasse zurück."""
    return {"kassenstand": str(_get_bar_kassenstand(db))}


@router.get("/naechste-belegnr")
def naechste_belegnr(datum: date = Query(default=None), db: Session = Depends(get_db)):
    """Gibt die nächste freie Belegnummer zurück."""
    d = datum or date.today()
    return {"belegnr": _naechste_belegnr(db, d)}


@router.get("/statistik/monat", response_model=MonatsUebersicht)
def monat_statistik(monat: str = Query(..., description="Format: YYYY-MM"), db: Session = Depends(get_db)):
    """Monatsstatistik: Einnahmen, Ausgaben, Saldo."""
    try:
        jahr, mon = monat.split("-")
        jahr_int, mon_int = int(jahr), int(mon)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail="monat muss im Format YYYY-MM sein")

    # Privateinlagen/-entnahmen (kontenart="Privat") gehören nicht zu den
    # betrieblichen Einnahmen/Ausgaben und werden herausgefiltert.
    betrieb_filter = or_(
        Journaleintrag.kategorie_id.is_(None),
        Kategorie.kontenart != "Privat",
    )
    einnahmen = (
        db.query(func.sum(Journaleintrag.brutto_betrag))
        .outerjoin(Journaleintrag.kategorie)
        .filter(
            extract("year", Journaleintrag.datum) == jahr_int,
            extract("month", Journaleintrag.datum) == mon_int,
            Journaleintrag.art == "Einnahme",
            betrieb_filter,
        )
        .scalar()
        or Decimal("0")
    )
    ausgaben = (
        db.query(func.sum(Journaleintrag.brutto_betrag))
        .outerjoin(Journaleintrag.kategorie)
        .filter(
            extract("year", Journaleintrag.datum) == jahr_int,
            extract("month", Journaleintrag.datum) == mon_int,
            Journaleintrag.art == "Ausgabe",
            betrieb_filter,
        )
        .scalar()
        or Decimal("0")
    )
    anzahl = (
        db.query(func.count(Journaleintrag.id))
        .filter(
            extract("year", Journaleintrag.datum) == jahr_int,
            extract("month", Journaleintrag.datum) == mon_int,
        )
        .scalar()
        or 0
    )
    return MonatsUebersicht(
        monat=monat,
        einnahmen=Decimal(str(einnahmen)),
        ausgaben=Decimal(str(ausgaben)),
        saldo=Decimal(str(einnahmen)) - Decimal(str(ausgaben)),
        anzahl_buchungen=anzahl,
    )


@router.get("", response_model=list[JournalEintragResponse])
def list_eintraege(
    monat: Optional[str] = Query(None, description="Format: YYYY-MM"),
    datum_von: Optional[date] = Query(None, description="Von-Datum (YYYY-MM-DD)"),
    datum_bis: Optional[date] = Query(None, description="Bis-Datum (YYYY-MM-DD)"),
    kategorie_id: Optional[int] = None,
    art: Optional[str] = Query(None, description="Einnahme oder Ausgabe"),
    zahlungsart_typ: Optional[str] = Query(None, description="bar oder unbar"),
    gruppe_id: Optional[int] = Query(None, description="Zeigt nur die Buchungsgruppe (Original+Storno+ggf. Neu) dieser Wurzel-id"),
    db: Session = Depends(get_db),
):
    """Journaleinträge mit optionalen Filtern."""
    q = db.query(Journaleintrag)
    if gruppe_id is not None:
        # Original selbst hat gruppe_id=NULL (GoBD: kein nachtraegliches UPDATE moeglich),
        # daher zusaetzlich nach eigener id filtern.
        q = q.filter((Journaleintrag.id == gruppe_id) | (Journaleintrag.gruppe_id == gruppe_id))
    if monat:
        try:
            jahr, mon = monat.split("-")
            q = q.filter(
                extract("year", Journaleintrag.datum) == int(jahr),
                extract("month", Journaleintrag.datum) == int(mon),
            )
        except (ValueError, AttributeError):
            raise HTTPException(status_code=422, detail="monat muss im Format YYYY-MM sein")
    else:
        if datum_von:
            q = q.filter(Journaleintrag.datum >= datum_von)
        if datum_bis:
            q = q.filter(Journaleintrag.datum <= datum_bis)
    if kategorie_id is not None:
        q = q.filter(Journaleintrag.kategorie_id == kategorie_id)
    if art:
        if art not in ("Einnahme", "Ausgabe"):
            raise HTTPException(status_code=422, detail="art muss Einnahme oder Ausgabe sein")
        q = q.filter(Journaleintrag.art == art)
    if zahlungsart_typ == "bar":
        q = q.filter(Journaleintrag.zahlungsart == "Bar")
    elif zahlungsart_typ == "unbar":
        q = q.filter(Journaleintrag.zahlungsart != "Bar")
    eintraege = q.order_by(Journaleintrag.datum.desc(), Journaleintrag.id.desc()).all()
    storno_infos = _storno_infos(db, eintraege)
    return [
        _mit_storno_info(JournalEintragResponse.from_orm_with_kunde(e), storno_infos[e.id])
        for e in eintraege
    ]


def _felder_aus_data(data: "JournalEintragCreate", db: Session) -> dict:
    """Berechnet alle abgeleiteten Felder für einen Journaleintrag (shared by create + update)."""
    unternehmen = db.query(Unternehmen).first()
    ust_satz = data.ust_satz
    vorsteuerabzug = data.vorsteuerabzug
    steuerbefreiung_grund = None

    if unternehmen and unternehmen.ist_kleinunternehmer:
        ust_satz = Decimal("0")
        steuerbefreiung_grund = "§19 UStG"

    kat = db.query(Kategorie).filter(Kategorie.id == data.kategorie_id).first() if data.kategorie_id else None

    if kat:
        if kat.kontenart == "Privat":
            ust_satz = Decimal("0")
            vorsteuerabzug = False
            if not steuerbefreiung_grund:
                steuerbefreiung_grund = "Privatbuchung"
        if (kat.konto_skr03 == "8125" or kat.konto_skr04 == "3125") and not steuerbefreiung_grund:
            steuerbefreiung_grund = "§4 Nr. 1b UStG"
        if not data.ust_sonderfall and not data.ist_ig_erwerb:
            # WICHTIG: SKR03- und SKR04-Konto je Kategorie GETRENNT prüfen (nicht als
            # gemeinsames Tupel) - Kontonummern sind zwischen den beiden Kontenrahmen nicht
            # eindeutig. Z.B. hat "Innergemeinschaftliche Lieferungen" konto_skr04="3125",
            # während "Drittland-Dienstleistungen (§13b Abs. 1)" konto_skr03="3125" hat - eine
            # gemischte Prüfung "3125" in (skr03, skr04) trifft auf beide Kategorien zu und
            # stufte ig. Lieferungen faelschlich als 13b_abs1 ein (KZ 46 statt KZ 41 in der
            # USt-VA, Issue #326).
            if kat.konto_skr03 == "3425" or kat.konto_skr04 == "5425":
                data = data.model_copy(update={"ust_sonderfall": "ig_erwerb"})
            elif kat.konto_skr03 in ("3123", "3125") or kat.konto_skr04 in ("5923", "5925"):
                data = data.model_copy(update={"ust_sonderfall": "13b_abs1"})
            elif kat.konto_skr03 == "3120" or kat.konto_skr04 == "5920":
                data = data.model_copy(update={"ust_sonderfall": "13b_abs2"})
            elif kat.konto_skr03 == "1588" or kat.konto_skr04 == "1433":
                data = data.model_copy(update={"ust_sonderfall": "einfuhr_ust"})

    ust_sonderfall = data.ust_sonderfall
    if not ust_sonderfall and data.ist_ig_erwerb:
        ust_sonderfall = "ig_erwerb"

    if ust_sonderfall == "einfuhr_ust":
        # Einfuhrumsatzsteuer (DHL/Zoll): der eingegebene Betrag IST bereits die Steuer,
        # kein Nettoanteil (anders als bei ig. Erwerb/§13b, wo der Betrag der Nettopreis ist).
        # ust_satz hat hier keine Bedeutung (kein Satz-basierter Split) - immer auf 0 zwingen,
        # sonst würde unten faelschlich ein USt-Gegenkonto für einen nie berechneten Split gesetzt.
        ust_satz = Decimal("0")
        netto = Decimal("0.00")
        ust_betrag = data.brutto_betrag
        brutto_stored = data.brutto_betrag
        vorsteuerabzug = True
    elif ust_sonderfall and ust_satz > 0:
        netto = data.brutto_betrag
        ust_betrag = (netto * ust_satz / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
        brutto_stored = netto
        vorsteuerabzug = True
    else:
        netto, ust_betrag = _berechne_ust(data.brutto_betrag, ust_satz)
        brutto_stored = data.brutto_betrag

    if ust_satz > 0:
        konto_ust_skr03, konto_ust_skr04 = _ust_konto(data.art, ust_satz)
        satz_i = int(ust_satz)
        if ust_sonderfall == "ig_erwerb":
            konto_ust_skr03 = {19: "1780", 7: "1781"}.get(satz_i, konto_ust_skr03)
            konto_ust_skr04 = {19: "3802", 7: "3803"}.get(satz_i, konto_ust_skr04)
        elif ust_sonderfall in ("13b_abs1", "13b_abs2"):
            konto_ust_skr03 = {19: "1787", 7: "1787"}.get(satz_i, konto_ust_skr03)
            konto_ust_skr04 = {19: "3803", 7: "3803"}.get(satz_i, konto_ust_skr04)
    else:
        konto_ust_skr03, konto_ust_skr04 = None, None

    return dict(
        datum=data.datum,
        beschreibung=data.beschreibung,
        kategorie_id=data.kategorie_id,
        konto_skr03=kat.konto_skr03 if kat else None,
        konto_skr04=kat.konto_skr04 if kat else None,
        konto_ust_skr03=konto_ust_skr03,
        konto_ust_skr04=konto_ust_skr04,
        kunde_id=data.kunde_id,
        zahlungsart=data.zahlungsart,
        art=data.art,
        netto_betrag=netto,
        ust_satz=ust_satz,
        ust_betrag=ust_betrag,
        vorsteuer_betrag=_berechne_vorsteuer(ust_betrag, vorsteuerabzug, kat, bool(ust_sonderfall)),
        brutto_betrag=brutto_stored,
        vorsteuerabzug=vorsteuerabzug,
        steuerbefreiung_grund=steuerbefreiung_grund,
        externe_belegnr=data.externe_belegnr,
        km_anzahl=data.km_anzahl,
        ist_ig_erwerb=(ust_sonderfall == "ig_erwerb"),
        ust_sonderfall=ust_sonderfall,
    )


@router.post("", response_model=JournalEintragResponse, status_code=201)
def create_eintrag(data: JournalEintragCreate, db: Session = Depends(get_db)):
    """Legt einen neuen Journaleintrag an (innerhalb von 5 Min. direkt korrigierbar)."""
    # Barkassen-Prüfung: Bar-Ausgabe darf den Kassenstand nicht übersteigen
    if data.art == "Ausgabe" and data.zahlungsart == "Bar":
        kassenstand = _get_bar_kassenstand(db)
        if data.brutto_betrag > kassenstand:
            raise HTTPException(
                status_code=409,
                detail=f"Kassenstand nicht ausreichend. Aktueller Kassenstand: {kassenstand:.2f} €, Ausgabe: {data.brutto_betrag:.2f} €.",
            )

    felder = _felder_aus_data(data, db)
    belegnr = _naechste_belegnr(db, data.datum)

    journaleintrag = Journaleintrag(belegnr=belegnr, immutable=False, **felder)
    journaleintrag.signatur = signatur_journaleintrag(journaleintrag)
    db.add(journaleintrag)
    db.commit()
    db.refresh(journaleintrag)
    return JournalEintragResponse.from_orm_with_kunde(journaleintrag)


KORREKTUR_FENSTER_SEKUNDEN = 300  # 5 Minuten


@router.put("/{eintrag_id}", response_model=JournalEintragResponse)
def update_eintrag(eintrag_id: int, data: JournalEintragCreate, db: Session = Depends(get_db)):
    """Korrigiert einen Journaleintrag.

    Innerhalb von 5 Minuten nach Erstellung: direkte Korrektur (unsichtbar, GoBD-konform
    da noch keine Festschreibung). Danach: automatische Stornobuchung + korrigierte Neubuchung.
    """
    original = db.query(Journaleintrag).filter(Journaleintrag.id == eintrag_id).first()
    if not original:
        raise HTTPException(404, "Journaleintrag nicht gefunden.")
    if original.beschreibung.startswith("STORNO "):
        raise HTTPException(409, "Storno-Einträge können nicht bearbeitet werden.")
    if original.rechnung_id:
        raise HTTPException(409, "Rechnungsbuchungen können nur über die Rechnung bearbeitet werden.")
    bereits_storniert = db.query(Journaleintrag).filter(
        Journaleintrag.gruppe_id == (original.gruppe_id or original.id),
        Journaleintrag.beschreibung.like("STORNO %"),
    ).first()
    if bereits_storniert:
        raise HTTPException(409, f"Diese Buchung wurde bereits storniert ({bereits_storniert.belegnr}).")

    delta = datetime.utcnow() - original.erstellt_am
    within_window = not original.immutable and delta.total_seconds() < KORREKTUR_FENSTER_SEKUNDEN

    felder = _felder_aus_data(data, db)

    if within_window:
        # Direkte Korrektur: Felder in-place aktualisieren, Signatur neu berechnen
        for k, v in felder.items():
            setattr(original, k, v)
        original.signatur = signatur_journaleintrag(original)
        db.commit()
        db.refresh(original)
        return JournalEintragResponse.from_orm_with_kunde(original)

    # Nach Fristablauf: Original versiegeln (falls noch offen), dann Storno + Neubuchung
    if not original.immutable:
        original.immutable = True
        original.signatur = signatur_journaleintrag(original)

    # Storno-Datum = Datum der Originalbuchung, nicht heute: dieser Pfad korrigiert nur
    # nachtraeglich eine fehlerhafte Erfassung (kein echter Geldfluss heute) - ein Storno im
    # laufenden Jahr wuerde sowohl das Ursprungsjahr unkorrigiert lassen als auch das laufende
    # Jahr um einen wirtschaftlich nicht zugehoerigen Betrag verfaelschen (Issue #320).
    storno_datum = original.datum
    storno_belegnr = _naechste_belegnr(db, storno_datum)
    if original.brutto_betrag >= 0:
        s_art = "Ausgabe" if original.art == "Einnahme" else "Einnahme"
        s_netto, s_ust, s_brutto = original.netto_betrag, original.ust_betrag, original.brutto_betrag
    else:
        s_art = original.art
        s_netto = -original.netto_betrag
        s_ust = -original.ust_betrag
        s_brutto = -original.brutto_betrag

    storno = Journaleintrag(
        datum=storno_datum, belegnr=storno_belegnr,
        beschreibung=f"STORNO {original.belegnr}: Korrektur",
        kategorie_id=original.kategorie_id,
        konto_skr03=original.konto_skr03, konto_skr04=original.konto_skr04,
        konto_ust_skr03=original.konto_ust_skr03, konto_ust_skr04=original.konto_ust_skr04,
        zahlungsart=original.zahlungsart, art=s_art,
        netto_betrag=s_netto, ust_satz=original.ust_satz,
        ust_betrag=s_ust, vorsteuer_betrag=-original.vorsteuer_betrag,
        brutto_betrag=s_brutto, vorsteuerabzug=original.vorsteuerabzug,
        ist_ig_erwerb=original.ist_ig_erwerb, ust_sonderfall=original.ust_sonderfall,
        gruppe_id=original.gruppe_id or original.id,
        immutable=True,
    )
    storno.signatur = signatur_journaleintrag(storno)
    db.add(storno)

    neu_belegnr = _naechste_belegnr(db, felder["datum"])
    neu = Journaleintrag(
        belegnr=neu_belegnr, gruppe_id=original.gruppe_id or original.id, immutable=True,
        beleg_id=original.beleg_id,  # ein evtl. angehängter Beleg wandert mit zur Korrektur-Buchung
        **felder,
    )
    neu.signatur = signatur_journaleintrag(neu)
    db.add(neu)
    db.flush()  # neu.id wird fuer die Bank-Verknuepfung unten benoetigt

    # Bank-Verknuepfung wandert mit auf die Neubuchung (Issue #322) - sonst zeigt
    # BankTransaktion.journal_id dauerhaft auf die stornierte, wirtschaftlich nicht mehr
    # existierende Buchung, waehrend die gueltige Neubuchung ohne Bankbezug bleibt.
    db.query(BankTransaktion).filter(BankTransaktion.journal_id == original.id).update(
        {"journal_id": neu.id}
    )

    db.commit()
    db.refresh(neu)
    return JournalEintragResponse.from_orm_with_kunde(neu)


async def _beleg_datei_speichern(datei: UploadFile, db: Session) -> Beleg:
    """Speichert eine hochgeladene Datei als neuen Beleg-Datensatz (ohne Verknüpfung zu
    einer Buchung) - gemeinsam genutzt von upload_anhang() und upload_anhang_vorab()."""
    mime = datei.content_type or ""
    if mime not in ERLAUBTE_MIME_TYPES:
        raise HTTPException(status_code=422, detail=f"Dateityp '{mime}' nicht erlaubt. Erlaubt: PDF, JPEG, PNG, TIFF.")

    inhalt = await datei.read()
    sha256 = hashlib.sha256(inhalt).hexdigest()

    jetzt = datetime.now()
    ziel_dir = BELEG_DIR / str(jetzt.year) / jetzt.strftime("%m")
    ziel_dir.mkdir(parents=True, exist_ok=True)

    original_name = Path(datei.filename or "beleg")
    stem = original_name.stem[:50]
    suffix = original_name.suffix.lower() or ".bin"
    dateiname_lokal = f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
    rel_pfad = f"belege/{jetzt.year}/{jetzt.strftime('%m')}/{dateiname_lokal}"

    (ziel_dir / dateiname_lokal).write_bytes(inhalt)

    pdfa_pfad_rel: str | None = None
    if mime == "application/pdf":
        try:
            ergebnis = analysiere_datei(datei.filename or "", inhalt)
            if ergebnis.format in ("zugferd", "xrechnung"):
                pdfa_pfad_rel = rel_pfad
        except Exception:
            pass

    beleg = Beleg(
        dateiname=rel_pfad,
        original_name=datei.filename or "beleg",
        mime_type=mime,
        dateigroesse=len(inhalt),
        sha256=sha256,
        beleg_pdfa_pfad=pdfa_pfad_rel,
    )
    db.add(beleg)
    db.flush()
    db.commit()
    db.refresh(beleg)

    if pdfa_pfad_rel is None:
        import threading
        beleg_id = beleg.id
        src_pfad = ziel_dir / dateiname_lokal
        beleg_mime = mime

        def _konvertiere_hintergrund():
            from database.connection import SessionLocal as _Session
            pdfa_path = konvertiere_zu_pdfa(src_pfad, beleg_mime)
            if pdfa_path and pdfa_path.exists():
                pfad_relativ = f"belege/{jetzt.year}/{jetzt.strftime('%m')}/{pdfa_path.name}"
                _db = _Session()
                try:
                    b = _db.query(Beleg).filter(Beleg.id == beleg_id).first()
                    if b:
                        b.beleg_pdfa_pfad = pfad_relativ
                        _db.commit()
                finally:
                    _db.close()

        threading.Thread(target=_konvertiere_hintergrund, daemon=True).start()

    return beleg


@router.post("/{eintrag_id}/anhang", response_model=BelegResponse, status_code=201)
async def upload_anhang(eintrag_id: int, datei: UploadFile = File(...), db: Session = Depends(get_db)):
    """Dateianhang (PDF/Bild) an eine Journalbuchung hängen (Issue #310). Eigene Route
    "/anhang" statt "/beleg" - unter "/beleg" existiert bereits der druckbare HTML-Beleg
    (siehe get_beleg() weiter unten), das waere sonst eine Routenkollision."""
    eintrag = db.query(Journaleintrag).filter(Journaleintrag.id == eintrag_id).first()
    if not eintrag:
        raise HTTPException(status_code=404, detail="Journaleintrag nicht gefunden.")
    if eintrag.immutable:
        # protect_journal_update-Trigger wuerde das UPDATE ohnehin ablehnen (GoBD) -
        # hier vorab mit verstaendlicher Meldung statt rohem DB-Fehler.
        raise HTTPException(
            status_code=409,
            detail="Diese Buchung ist bereits festgeschrieben (GoBD) – ein Beleg kann nachträglich nicht mehr angehängt werden.",
        )

    # Alten Beleg ersetzen wenn vorhanden
    if eintrag.beleg_id:
        alter_beleg = db.query(Beleg).filter(Beleg.id == eintrag.beleg_id).first()
        if alter_beleg:
            alter_pfad = APP_DATA_DIR / "uploads" / alter_beleg.dateiname
            if alter_pfad.exists():
                alter_pfad.unlink()
            db.delete(alter_beleg)
            db.flush()

    beleg = await _beleg_datei_speichern(datei, db)
    eintrag.beleg_id = beleg.id
    db.commit()
    return BelegResponse.from_beleg(beleg)


@router.post("/anhang-vorab", response_model=BelegResponse, status_code=201)
async def upload_anhang_vorab(datei: UploadFile = File(...), db: Session = Depends(get_db)):
    """Beleg VOR dem Anlegen einer Split-Buchung hochladen (Issue #310). Split-Buchungen
    sind ab Erstellung immutable=True (kein 5-Minuten-Korrekturfenster wie bei
    Einzelbuchungen) - ein Beleg muss daher schon beim Anlegen als beleg_id mitgegeben
    werden, ein nachtraeglicher Upload wuerde der GoBD-Trigger ohnehin ablehnen. Gibt
    die Beleg-id zurueck, die dann in SplitBuchungCreate.beleg_id mitgeschickt wird."""
    beleg = await _beleg_datei_speichern(datei, db)
    return BelegResponse.from_beleg(beleg)


@router.get("/{eintrag_id}/anhang")
def download_anhang(
    eintrag_id: int,
    version: str = Query("original", description="'original' oder 'pdfa'"),
    db: Session = Depends(get_db),
):
    """Angehängte Datei einer Journalbuchung herunterladen. Mit ?version=pdfa die PDF/A-Version."""
    eintrag = db.query(Journaleintrag).filter(Journaleintrag.id == eintrag_id).first()
    if not eintrag or not eintrag.beleg_id:
        raise HTTPException(status_code=404, detail="Kein Beleg vorhanden.")
    beleg = db.query(Beleg).filter(Beleg.id == eintrag.beleg_id).first()
    if not beleg:
        raise HTTPException(status_code=404, detail="Beleg-Datensatz nicht gefunden.")

    if version == "pdfa":
        if not beleg.beleg_pdfa_pfad:
            raise HTTPException(status_code=404, detail="Keine PDF/A-Version verfügbar.")
        pfad = APP_DATA_DIR / "uploads" / beleg.beleg_pdfa_pfad
        if not pfad.exists():
            raise HTTPException(status_code=404, detail="PDF/A-Datei nicht gefunden.")
        stem = Path(beleg.original_name).stem
        return FileResponse(
            path=str(pfad),
            media_type="application/pdf",
            filename=f"{stem}_pdfa.pdf",
            content_disposition_type="inline",
        )

    pfad = APP_DATA_DIR / "uploads" / beleg.dateiname
    if not pfad.exists():
        raise HTTPException(status_code=404, detail="Beleg-Datei nicht gefunden.")
    return FileResponse(
        path=str(pfad),
        media_type=beleg.mime_type or "application/octet-stream",
        filename=beleg.original_name,
        content_disposition_type="inline",
    )


@router.delete("/{eintrag_id}/anhang", status_code=204)
def delete_anhang(eintrag_id: int, db: Session = Depends(get_db)):
    """Beleg-Anhang von einer Journalbuchung entfernen und Datei löschen."""
    eintrag = db.query(Journaleintrag).filter(Journaleintrag.id == eintrag_id).first()
    if not eintrag or not eintrag.beleg_id:
        raise HTTPException(status_code=404, detail="Kein Beleg vorhanden.")
    if eintrag.immutable:
        raise HTTPException(
            status_code=409,
            detail="Diese Buchung ist bereits festgeschrieben (GoBD) – der Beleg kann nicht mehr entfernt werden.",
        )
    beleg = db.query(Beleg).filter(Beleg.id == eintrag.beleg_id).first()
    eintrag.beleg_id = None
    if beleg:
        pfad = APP_DATA_DIR / "uploads" / beleg.dateiname
        if pfad.exists():
            pfad.unlink()
        db.delete(beleg)
    db.commit()


@router.post("/split", response_model=list[JournalEintragResponse], status_code=201)
def create_split_buchung(data: SplitBuchungCreate, db: Session = Depends(get_db)):
    """Erstellt mehrere Journaleinträge als atomare Split-Buchung (ein Beleg, mehrere Positionen)."""
    # Barkassen-Prüfung für Split-Ausgaben (nur Bar, Gesamtbetrag aller Positionen)
    if data.art == "Ausgabe" and data.zahlungsart == "Bar":
        gesamt = sum(pos.brutto_betrag for pos in data.positionen)
        kassenstand = _get_bar_kassenstand(db)
        if gesamt > kassenstand:
            raise HTTPException(
                status_code=409,
                detail=f"Kassenstand nicht ausreichend. Aktueller Kassenstand: {kassenstand:.2f} €, Ausgabe gesamt: {gesamt:.2f} €.",
            )

    unternehmen = db.query(Unternehmen).first()
    ergebnisse = []
    for pos in data.positionen:
        ust_satz = pos.ust_satz
        vorsteuerabzug = pos.vorsteuerabzug
        steuerbefreiung_grund = None
        if unternehmen and unternehmen.ist_kleinunternehmer:
            ust_satz = Decimal("0")
            steuerbefreiung_grund = "§19 UStG"
        if pos.kategorie_id:
            kat = db.query(Kategorie).filter(Kategorie.id == pos.kategorie_id).first()
            if kat and kat.kontenart == "Privat":
                ust_satz = Decimal("0")
                vorsteuerabzug = False
                if not steuerbefreiung_grund:
                    steuerbefreiung_grund = "Privatbuchung"
            if kat and kat.konto_skr03 in ("8125", "3125") and not steuerbefreiung_grund:
                steuerbefreiung_grund = "§4 Nr. 1b UStG"
        pos_sf = pos.ust_sonderfall or ("ig_erwerb" if pos.ist_ig_erwerb else None)
        if not pos_sf and pos.kategorie_id:
            _sf_kat = db.query(Kategorie).filter(Kategorie.id == pos.kategorie_id).first()
            if _sf_kat:
                _sf_konten = (_sf_kat.konto_skr03, _sf_kat.konto_skr04)
                if "3425" in _sf_konten or "5425" in _sf_konten:
                    pos_sf = "ig_erwerb"
                elif "3123" in _sf_konten or "5923" in _sf_konten:
                    pos_sf = "13b_abs1"
                elif "3120" in _sf_konten or "5920" in _sf_konten:
                    pos_sf = "13b_abs2"
        split_kat = db.query(Kategorie).filter(Kategorie.id == pos.kategorie_id).first() if pos.kategorie_id else None
        if pos_sf and ust_satz > 0:
            netto = pos.brutto_betrag
            ust_betrag = (netto * ust_satz / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
            brutto_stored = netto
            vorsteuerabzug = True
        else:
            netto, ust_betrag = _berechne_ust(pos.brutto_betrag, ust_satz)
            brutto_stored = pos.brutto_betrag
        belegnr = _naechste_belegnr(db, data.datum)
        if ust_satz > 0:
            konto_ust_skr03, konto_ust_skr04 = _ust_konto(data.art, ust_satz)
            satz_i = int(ust_satz)
            if pos_sf == "ig_erwerb":
                konto_ust_skr03 = {19: "1780", 7: "1781"}.get(satz_i, konto_ust_skr03)
                konto_ust_skr04 = {19: "3802", 7: "3803"}.get(satz_i, konto_ust_skr04)
            elif pos_sf in ("13b_abs1", "13b_abs2"):
                konto_ust_skr03 = {19: "1787", 7: "1787"}.get(satz_i, konto_ust_skr03)
                konto_ust_skr04 = {19: "3803", 7: "3803"}.get(satz_i, konto_ust_skr04)
        else:
            konto_ust_skr03, konto_ust_skr04 = None, None
        journaleintrag = Journaleintrag(
            datum=data.datum,
            belegnr=belegnr,
            beschreibung=pos.beschreibung,
            externe_belegnr=data.externe_belegnr,
            kategorie_id=pos.kategorie_id,
            konto_skr03=split_kat.konto_skr03 if split_kat else None,
            konto_skr04=split_kat.konto_skr04 if split_kat else None,
            konto_ust_skr03=konto_ust_skr03,
            konto_ust_skr04=konto_ust_skr04,
            kunde_id=data.kunde_id,
            zahlungsart=data.zahlungsart,
            art=data.art,
            netto_betrag=netto,
            ust_satz=ust_satz,
            ust_betrag=ust_betrag,
            vorsteuer_betrag=_berechne_vorsteuer(ust_betrag, vorsteuerabzug, split_kat, bool(pos_sf)),
            brutto_betrag=brutto_stored,
            vorsteuerabzug=vorsteuerabzug,
            steuerbefreiung_grund=steuerbefreiung_grund,
            ist_ig_erwerb=(pos_sf == "ig_erwerb"),
            ust_sonderfall=pos_sf,
            beleg_id=data.beleg_id,  # muss beim Anlegen mitgegeben werden, s. SplitBuchungCreate
            immutable=True,
        )
        journaleintrag.signatur = signatur_journaleintrag(journaleintrag)
        db.add(journaleintrag)
        ergebnisse.append(journaleintrag)
    db.commit()
    for e in ergebnisse:
        db.refresh(e)
    return [JournalEintragResponse.from_orm_with_kunde(e) for e in ergebnisse]


# ---------------------------------------------------------------------------
# Kassenbuch-Export (Bar-Buchungen, PDF oder CSV)
# ---------------------------------------------------------------------------

def _kassenbuch_anfangsbestand(db: Session, datum_von: date) -> Decimal:
    letzter = (
        db.query(Tagesabschluss)
        .filter(Tagesabschluss.datum < datum_von)
        .order_by(Tagesabschluss.datum.desc(), Tagesabschluss.id.desc())
        .first()
    )
    if letzter:
        return letzter.ist_endbestand
    einnahmen = db.query(func.coalesce(func.sum(Journaleintrag.brutto_betrag), 0)).filter(
        Journaleintrag.zahlungsart == "Bar",
        Journaleintrag.art == "Einnahme",
        Journaleintrag.datum < datum_von,
    ).scalar()
    ausgaben = db.query(func.coalesce(func.sum(Journaleintrag.brutto_betrag), 0)).filter(
        Journaleintrag.zahlungsart == "Bar",
        Journaleintrag.art == "Ausgabe",
        Journaleintrag.datum < datum_von,
    ).scalar()
    return Decimal(str(einnahmen)) - Decimal(str(ausgaben))


@router.get("/kassenbuch-export")
def kassenbuch_export(
    datum_von: date = Query(...),
    datum_bis: date = Query(...),
    format: str = Query("pdf", description="pdf oder csv"),
    db: Session = Depends(get_db),
):
    eintraege = (
        db.query(Journaleintrag)
        .filter(
            Journaleintrag.zahlungsart == "Bar",
            Journaleintrag.datum >= datum_von,
            Journaleintrag.datum <= datum_bis,
        )
        .order_by(Journaleintrag.datum.asc(), Journaleintrag.id.asc())
        .all()
    )
    anfangsbestand = _kassenbuch_anfangsbestand(db, datum_von)
    kat_map = {k.id: k.name for k in db.query(Kategorie).all()}
    rows = [
        {
            "datum":          str(e.datum),
            "belegnr":        e.belegnr or "",
            "beschreibung":   e.beschreibung or "",
            "kategorie_name": kat_map.get(e.kategorie_id, "") if e.kategorie_id else "",
            "art":            e.art,
            "brutto_betrag":  str(e.brutto_betrag),
        }
        for e in eintraege
    ]
    if format == "csv":
        out = io.StringIO()
        writer = csv.writer(out, delimiter=";")
        writer.writerow(["Datum", "Beleg-Nr.", "Beschreibung", "Kategorie",
                         "Einnahme (EUR)", "Ausgabe (EUR)", "Kassenstand (EUR)"])
        kassenstand = anfangsbestand
        writer.writerow([str(datum_von), "", "Anfangsbestand", "", "", "",
                         f"{kassenstand:.2f}".replace(".", ",")])
        for r in rows:
            betrag = Decimal(r["brutto_betrag"])
            if r["art"] == "Einnahme":
                kassenstand += betrag
                ein, aus_ = f"{betrag:.2f}".replace(".", ","), ""
            else:
                kassenstand -= betrag
                ein, aus_ = "", f"{betrag:.2f}".replace(".", ",")
            writer.writerow([
                r["datum"], r["belegnr"], r["beschreibung"], r["kategorie_name"],
                ein, aus_, f"{kassenstand:.2f}".replace(".", ","),
            ])
        writer.writerow(["", "", "Endbestand", "", "", "",
                         f"{kassenstand:.2f}".replace(".", ",")])
        csv_bytes = ("﻿" + out.getvalue()).encode("utf-8")
        return Response(
            content=csv_bytes,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="Kassenbuch_{datum_von}_{datum_bis}.csv"'},
        )
    unt = db.query(Unternehmen).first()
    unt_dict: dict = {}
    if unt:
        name_teile = [unt.vorname or "", unt.nachname or ""]
        name = " ".join(t for t in name_teile if t) or unt.firmenname
        unt_dict = {
            "firmenname": unt.firmenname,
            "ort": unt.ort or "",
            "unterschrift_name": name,
            "unterschrift_bild": unt.unterschrift_bild or "",
        }
    from utils.pdf_kassenbuch import erstelle_kassenbuch_pdf
    pdf_bytes = erstelle_kassenbuch_pdf(unt_dict, rows, anfangsbestand, str(datum_von), str(datum_bis))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Kassenbuch_{datum_von}_{datum_bis}.pdf"'},
    )


@router.get("/export")
def journal_export(
    monat: Optional[str] = Query(None, description="Format: YYYY-MM"),
    datum_von: Optional[date] = Query(None),
    datum_bis: Optional[date] = Query(None),
    kategorie_id: Optional[int] = None,
    art: Optional[str] = Query(None, description="Einnahme oder Ausgabe"),
    zahlungsart_typ: Optional[str] = Query(None, description="bar oder unbar"),
    format: str = Query("pdf", description="pdf oder csv"),
    db: Session = Depends(get_db),
):
    """Journal-Export als PDF oder CSV mit denselben Filtern wie die Journal-Liste."""
    q = db.query(Journaleintrag)
    if monat:
        try:
            j, m = monat.split("-")
            q = q.filter(
                extract("year", Journaleintrag.datum) == int(j),
                extract("month", Journaleintrag.datum) == int(m),
            )
        except (ValueError, AttributeError):
            raise HTTPException(status_code=422, detail="monat muss im Format YYYY-MM sein")
    else:
        if datum_von:
            q = q.filter(Journaleintrag.datum >= datum_von)
        if datum_bis:
            q = q.filter(Journaleintrag.datum <= datum_bis)
    if kategorie_id is not None:
        q = q.filter(Journaleintrag.kategorie_id == kategorie_id)
    if art:
        if art not in ("Einnahme", "Ausgabe"):
            raise HTTPException(status_code=422, detail="art muss Einnahme oder Ausgabe sein")
        q = q.filter(Journaleintrag.art == art)
    if zahlungsart_typ == "bar":
        q = q.filter(Journaleintrag.zahlungsart == "Bar")
    elif zahlungsart_typ == "unbar":
        q = q.filter(Journaleintrag.zahlungsart != "Bar")
    eintraege = q.order_by(Journaleintrag.datum.asc(), Journaleintrag.id.asc()).all()

    kat_map = {k.id: k.name for k in db.query(Kategorie).all()}
    rows = [
        {
            "datum":          str(e.datum),
            "belegnr":        e.belegnr or "",
            "beschreibung":   e.beschreibung or "",
            "kategorie_name": kat_map.get(e.kategorie_id, "") if e.kategorie_id else "",
            "zahlungsart":    e.zahlungsart or "",
            "art":            e.art,
            "netto_betrag":   str(e.netto_betrag),
            "ust_satz":       str(e.ust_satz),
            "ust_betrag":     str(e.ust_betrag),
            "brutto_betrag":  str(e.brutto_betrag),
        }
        for e in eintraege
    ]

    # Dateinamen aus Zeitraum ableiten
    if monat:
        datei_suffix = monat
    elif datum_von and datum_bis and str(datum_von) == str(datum_bis):
        datei_suffix = str(datum_von)
    elif datum_von and datum_bis:
        datei_suffix = f"{datum_von}_{datum_bis}"
    elif datum_von:
        datei_suffix = f"ab_{datum_von}"
    elif datum_bis:
        datei_suffix = f"bis_{datum_bis}"
    else:
        datei_suffix = "gesamt"

    # Filterzeile für PDF und CSV
    filter_teile = []
    if art:
        filter_teile.append("Nur Einnahmen" if art == "Einnahme" else "Nur Ausgaben")
    if kategorie_id is not None:
        kat_name = kat_map.get(kategorie_id, f"ID {kategorie_id}")
        filter_teile.append(f"Kategorie: {kat_name}")
    if zahlungsart_typ == "bar":
        filter_teile.append("Nur Bar")
    elif zahlungsart_typ == "unbar":
        filter_teile.append("Nur Unbar")
    filter_zeile = " · ".join(filter_teile) if filter_teile else "Alle Buchungen"

    if format == "csv":
        out = io.StringIO()
        writer = csv.writer(out, delimiter=";")
        # Filterinfo als erste Zeile
        writer.writerow(["Filter:", filter_zeile])
        writer.writerow([])
        writer.writerow(["Datum", "Beleg-Nr.", "Beschreibung", "Kategorie",
                         "Zahlungsart", "Art", "Netto (EUR)", "USt %", "USt (EUR)", "Brutto (EUR)"])
        for r in rows:
            def _de(v: str) -> str:
                try:
                    return f"{Decimal(v):.2f}".replace(".", ",")
                except Exception:
                    return v
            writer.writerow([
                r["datum"], r["belegnr"], r["beschreibung"], r["kategorie_name"],
                r["zahlungsart"], r["art"],
                _de(r["netto_betrag"]), r["ust_satz"], _de(r["ust_betrag"]), _de(r["brutto_betrag"]),
            ])
        csv_bytes = ("﻿" + out.getvalue()).encode("utf-8")
        return Response(
            content=csv_bytes,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="Journal_{datei_suffix}.csv"'},
        )

    unt = db.query(Unternehmen).first()
    unt_dict: dict = {}
    if unt:
        unt_dict = {"firmenname": unt.firmenname or ""}

    # Titel für PDF-Header
    monate_de = ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
                 "Juli", "August", "September", "Oktober", "November", "Dezember"]
    if monat:
        try:
            j2, m2 = monat.split("-")
            titel = f"Journal – {monate_de[int(m2)]} {j2}"
        except Exception:
            titel = f"Journal – {monat}"
    elif datum_von and datum_bis:
        titel = f"Journal – {datum_von.strftime('%d.%m.%Y')} bis {datum_bis.strftime('%d.%m.%Y')}"
    elif datum_von:
        titel = f"Journal – ab {datum_von.strftime('%d.%m.%Y')}"
    else:
        titel = "Journal – Alle Buchungen"

    from utils.pdf_journal import erstelle_journal_pdf
    pdf_bytes = erstelle_journal_pdf(unt_dict, rows, titel, filter_zeile)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Journal_{datei_suffix}.pdf"'},
    )


@router.get("/{eintrag_id}/beleg", response_class=HTMLResponse)
def get_beleg(eintrag_id: int, drucken: bool = Query(False), download: bool = Query(False), db: Session = Depends(get_db)):
    """Gibt einen druckbaren HTML-Beleg für einen Journaleintrag zurück."""
    eintrag = db.query(Journaleintrag).filter(Journaleintrag.id == eintrag_id).first()
    if not eintrag:
        raise HTTPException(status_code=404, detail="Journaleintrag nicht gefunden.")

    datum = eintrag.datum.strftime("%d.%m.%Y")
    ust_satz = float(eintrag.ust_satz)
    print_script = "<script>window.addEventListener('load', () => { window.print() })</script>" if drucken else ""

    html = f"""<!DOCTYPE html><html><head>
    <meta charset="utf-8">
    <title>Beleg {eintrag.belegnr}</title>
    {print_script}
    <style>
      body {{ font-family: Arial, sans-serif; margin: 40px; color: #1e293b; }}
      h1 {{ font-size: 18px; margin-bottom: 4px; }}
      .meta {{ color: #64748b; font-size: 13px; margin-bottom: 24px; }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
      td {{ padding: 8px 0; border-bottom: 1px solid #e2e8f0; font-size: 14px; }}
      td:last-child {{ text-align: right; }}
      .label {{ color: #64748b; }}
      .total {{ font-weight: bold; font-size: 16px; }}
      .footer {{ margin-top: 40px; font-size: 12px; color: #94a3b8; }}
    </style>
    </head><body>
    <h1>RechnungsFee – Beleg</h1>
    <div class="meta">{eintrag.belegnr} &nbsp;·&nbsp; {datum} &nbsp;·&nbsp; {eintrag.art}</div>
    <table>
      <tr><td class="label">Beschreibung</td><td>{eintrag.beschreibung}</td></tr>
      <tr><td class="label">Zahlungsart</td><td>{eintrag.zahlungsart}</td></tr>
      <tr><td class="label">Netto</td><td>{float(eintrag.netto_betrag):.2f} €</td></tr>
      <tr><td class="label">USt ({ust_satz:.0f} %)</td><td>{float(eintrag.ust_betrag):.2f} €</td></tr>
      {"" if not eintrag.steuerbefreiung_grund else f'<tr><td class="label">Steuerbefreiung</td><td>{eintrag.steuerbefreiung_grund}</td></tr>'}
      <tr class="total"><td>Brutto</td><td>{float(eintrag.brutto_betrag):.2f} €</td></tr>
    </table>
    <div class="footer">Erstellt mit RechnungsFee &nbsp;·&nbsp; {datetime.now().strftime("%d.%m.%Y")}</div>
    </body></html>"""

    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="Beleg_{eintrag.belegnr}.html"'
    return HTMLResponse(content=html, headers=headers)


@router.get("/{eintrag_id}", response_model=JournalEintragResponse)
def get_eintrag(eintrag_id: int, db: Session = Depends(get_db)):
    journaleintrag = db.query(Journaleintrag).filter(Journaleintrag.id == eintrag_id).first()
    if not journaleintrag:
        raise HTTPException(status_code=404, detail="Journaleintrag nicht gefunden.")
    info = _storno_infos(db, [journaleintrag])[journaleintrag.id]
    return _mit_storno_info(JournalEintragResponse.from_orm_with_kunde(journaleintrag), info)


@router.post("/{eintrag_id}/storno", response_model=JournalEintragResponse, status_code=201)
def storno_eintrag(eintrag_id: int, data: StornoRequest, db: Session = Depends(get_db)):
    """Storniert einen Eintrag durch eine Gegenbuchung (GoBD-konform)."""
    original = db.query(Journaleintrag).filter(Journaleintrag.id == eintrag_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Journaleintrag nicht gefunden.")
    # Storno eines Stornos verhindern
    if original.beschreibung.startswith("STORNO "):
        raise HTTPException(status_code=409, detail="Ein Storno-Eintrag kann nicht erneut storniert werden.")
    # Bereits stornierte Buchung erkennen
    bereits_storniert = db.query(Journaleintrag).filter(
        Journaleintrag.gruppe_id == (original.gruppe_id or original.id),
        Journaleintrag.beschreibung.like("STORNO %"),
    ).first()
    if bereits_storniert:
        raise HTTPException(
            status_code=409,
            detail=f"Diese Buchung wurde bereits storniert (Gegenbuchung: {bereits_storniert.belegnr}).",
        )
    # Gegenbuchung: Betrag immer positiv.
    # Hatte das Original einen positiven Betrag (Normalfall): entgegengesetzte Art, gleicher Betrag.
    # Hatte das Original einen negativen Betrag (z. B. Gutschrift = Einnahme −x):
    #   → gleiche Art, negativer Betrag (= positive Zahl) → Gutschrift-Storno erscheint als Einnahme +x.
    # Storno-Datum: Vorgabe ist das Datum der Originalbuchung, nicht heute - bei der EÜR
    # (Zuflussprinzip) zaehlt ausschliesslich das Buchungsjahr; ein Storno im laufenden Jahr
    # verfaelscht sowohl das Ursprungsjahr (bleibt unkorrigiert) als auch das laufende Jahr
    # (bekommt einen wirtschaftlich nicht zugehoerigen Betrag) (Issue #320). Ausnahme: eine
    # tatsaechliche Rueckabwicklung mit echtem Geldfluss heute kann explizit data.datum setzen.
    storno_datum = data.datum or original.datum
    belegnr = _naechste_belegnr(db, storno_datum)
    if original.brutto_betrag >= 0:
        storno_art = "Ausgabe" if original.art == "Einnahme" else "Einnahme"
        s_netto  = original.netto_betrag
        s_ust    = original.ust_betrag
        s_brutto = original.brutto_betrag
    else:
        storno_art = original.art
        s_netto  = -original.netto_betrag
        s_ust    = -original.ust_betrag
        s_brutto = -original.brutto_betrag

    storno = Journaleintrag(
        datum=storno_datum,
        belegnr=belegnr,
        beschreibung=f"STORNO {original.belegnr}: {data.grund}",
        kategorie_id=original.kategorie_id,
        konto_skr03=original.konto_skr03,
        konto_skr04=original.konto_skr04,
        konto_ust_skr03=original.konto_ust_skr03,
        konto_ust_skr04=original.konto_ust_skr04,
        zahlungsart=original.zahlungsart,
        art=storno_art,
        netto_betrag=s_netto,
        ust_satz=original.ust_satz,
        ust_betrag=s_ust,
        vorsteuer_betrag=-original.vorsteuer_betrag,
        brutto_betrag=s_brutto,
        marge_25a_brutto=original.marge_25a_brutto,
        vorsteuerabzug=original.vorsteuerabzug,
        steuerbefreiung_grund=None,
        ist_ig_erwerb=original.ist_ig_erwerb,
        ust_sonderfall=original.ust_sonderfall,
        gruppe_id=original.gruppe_id or original.id,
        immutable=True,
    )
    storno.signatur = signatur_journaleintrag(storno)
    db.add(storno)
    db.commit()
    db.refresh(storno)
    return JournalEintragResponse.from_orm_with_kunde(storno)
