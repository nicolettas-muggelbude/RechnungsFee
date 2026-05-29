"""
Rechnungen-API (Eingang + Ausgang) mit Journal-Verknüpfung.
"""

import difflib
import hashlib
import shutil
import uuid
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from fastapi.responses import FileResponse, Response
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from database.connection import get_db, APP_DATA_DIR
from database.models import (
    Beleg, Lieferant, Rechnung, Rechnungsposition, Journaleintrag,
    Kategorie, Unternehmen, Nummernkreis,
)
from utils.signatur import signatur_journaleintrag
from utils.pdf_rechnung import generate_rechnung_pdf
from utils.pdf_rechnung_vorlage1 import generate_rechnung_pdf_vorlage1
from utils.zugferd import generate_zugferd_pdf
from utils.rechnungs_parser import analysiere_datei
from .schemas_rechnungen import (
    BelegResponse, LieferantVorschlag, RechnungCreate, RechnungUpdate, RechnungResponse,
    BarZahlungCreate, BarZahlungResult, ZahlungKompakt, AnalyseResponse, ZahlungSplitPosition,
)
from .schemas import StornoRequest

BELEG_DIR = APP_DATA_DIR / "uploads" / "belege"
TEMP_DIR = APP_DATA_DIR / "uploads" / "tmp"
ERLAUBTE_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/tiff"}

router = APIRouter(prefix="/api/rechnungen", tags=["Rechnungen"])


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

import re as _re


def _belegnr_aus_format(format_str: str, datum: date, nr: int) -> str:
    year_4 = str(datum.year)
    year_2 = year_4[-2:]
    month  = f"{datum.month:02d}"
    day    = f"{datum.day:02d}"
    result = (format_str
              .replace("YYYY", year_4)
              .replace("YY",   year_2)
              .replace("MM",   month)
              .replace("TT",   day))

    def _pad(m: _re.Match) -> str:
        return str(nr).zfill(len(m.group()))

    return _re.sub(r"#+", _pad, result)


def _naechste_belegnr_journal(db: Session, datum: date) -> str:
    """Journal-Belegnummer (analog zu journal.py)."""
    nk = db.query(Nummernkreis).filter(Nummernkreis.typ == "journal").first()
    if not nk:
        count = db.query(Journaleintrag).count()
        return f"{str(datum.year)[-2:]}{count + 1:04d}"
    if nk.reset_jaehrlich and nk.letztes_jahr and nk.letztes_jahr != datum.year:
        nk.naechste_nr = 1
    nk.letztes_jahr = datum.year
    nr = nk.naechste_nr
    nk.naechste_nr += 1
    return _belegnr_aus_format(nk.format, datum, nr)


def _erloes_kategorie(db: Session, rechnung: "Rechnung") -> tuple[int | None, "Kategorie | None"]:
    """Ermittelt die Erlös-Kategorie für Ausgangsrechnungen anhand des dominanten USt-Satzes."""
    if not rechnung.positionen:
        return None, None
    # Dominanter USt-Satz = Satz mit höchstem Netto-Anteil
    satz_summen: dict[int, Decimal] = {}
    for pos in rechnung.positionen:
        satz = int(pos.ust_satz)
        satz_summen[satz] = satz_summen.get(satz, Decimal("0")) + pos.netto
    dom_satz = max(satz_summen, key=lambda s: satz_summen[s])
    namen = {19: "Betriebseinnahmen", 7: "Betriebseinnahmen (7%)", 0: "Betriebseinnahmen (0%)"}
    name = namen.get(dom_satz, "Betriebseinnahmen")
    kat = db.query(Kategorie).filter(Kategorie.name == name, Kategorie.aktiv == True).first()
    return (kat.id if kat else None, kat)


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


def _skonto_konto(rechnung_typ: str, ust_satz: Decimal) -> tuple[str | None, str | None]:
    """Gibt (konto_skr03, konto_skr04) für die Skonto-Gegenbuchung zurück."""
    satz = int(ust_satz)
    if rechnung_typ == "ausgang":
        # Erlösschmälerungen
        skr03 = {19: "8736", 7: "8727", 0: "8720"}.get(satz)
        skr04 = {19: "4310", 7: "4320", 0: "4300"}.get(satz)
    else:
        # Erhaltene Skonti (Eingangsrechnung)
        skr03 = {19: "2401", 7: "2400", 0: "2400"}.get(satz)
        skr04 = {19: "3401", 7: "3400", 0: "3400"}.get(satz)
    return skr03, skr04


def _berechne_position(pos_data) -> tuple[Decimal, Decimal, Decimal]:
    """Gibt (ust_betrag, brutto, netto_rund) zurück."""
    netto = pos_data.netto.quantize(Decimal("0.01"), ROUND_HALF_UP)
    if pos_data.ust_satz == 0:
        return Decimal("0.00"), netto, netto
    ust_betrag = (netto * pos_data.ust_satz / 100).quantize(Decimal("0.01"))
    brutto = netto + ust_betrag
    return ust_betrag, brutto, netto


def _aktualisiere_zahlungsstatus(rechnung: Rechnung) -> None:
    """Berechnet bezahlt_betrag aus verknüpften Journaleinträgen und setzt zahlungsstatus.
    Unterstützt negative Beträge (Gutschriften): Vergleich über abs()."""
    bezahlt = sum(e.brutto_betrag for e in rechnung.journaleintraege)
    rechnung.bezahlt_betrag = bezahlt.quantize(Decimal("0.01"), ROUND_HALF_UP) if bezahlt else Decimal("0.00")

    abs_bezahlt = abs(rechnung.bezahlt_betrag)
    abs_gesamt  = abs(rechnung.brutto_gesamt)

    if abs_bezahlt >= abs_gesamt:
        rechnung.zahlungsstatus = "bezahlt"
        rechnung.bezahlt = True
        rechnung.zahlungsdatum = date.today()
    elif abs_bezahlt > Decimal("0.004"):
        rechnung.zahlungsstatus = "teilweise"
        rechnung.bezahlt = False
    else:
        rechnung.zahlungsstatus = "offen"
        rechnung.bezahlt = False
        rechnung.zahlungsdatum = None


def _partner_name(rechnung: Rechnung) -> str:
    """Lesbare Bezeichnung des Rechnungspartners."""
    if rechnung.partner_freitext:
        return rechnung.partner_freitext
    if rechnung.typ == "ausgang" and rechnung.kunde:
        parts = [rechnung.kunde.firmenname or "", rechnung.kunde.vorname or "", rechnung.kunde.nachname or ""]
        return " ".join(p for p in parts if p)
    if rechnung.typ == "eingang" and rechnung.lieferant:
        parts = [rechnung.lieferant.firmenname or "", rechnung.lieferant.vorname or "", rechnung.lieferant.nachname or ""]
        return " ".join(p for p in parts if p)
    return "Unbekannt"


# ---------------------------------------------------------------------------
# Endpunkte
# ---------------------------------------------------------------------------

@router.post("/analysieren", response_model=AnalyseResponse)
async def analysiere_rechnung(datei: UploadFile = File(...), db: Session = Depends(get_db)):
    """ZUGFeRD / XRechnung aus PDF oder XML extrahieren (keine DB-Änderung)."""
    inhalt = await datei.read()
    ergebnis = analysiere_datei(datei.filename or "", inhalt)

    temp_url = None
    temp_path = None
    if datei.content_type == "application/pdf":
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        _bereinige_temp_dir()
        token = str(uuid.uuid4())
        temp_file = TEMP_DIR / f"{token}.pdf"
        temp_file.write_bytes(inhalt)
        temp_url = f"/rechnungen/temp/{token}"
        temp_path = str(temp_file.absolute())

    # Lieferanten-Vorschläge per Fuzzy-Matching
    lieferant_vorschlaege: list[LieferantVorschlag] = []
    erkannter_name = ergebnis.felder.get("lieferant_name", "")
    erkannte_ust_id = ergebnis.felder.get("lieferant_ust_id", "")
    if erkannter_name or erkannte_ust_id:
        alle_lieferanten = db.query(Lieferant).filter(Lieferant.aktiv == True).all()
        scored: list[tuple[float, Lieferant]] = []
        for lief in alle_lieferanten:
            score = 0.0
            if erkannte_ust_id and lief.ust_idnr and erkannte_ust_id.replace(" ", "") == lief.ust_idnr.replace(" ", ""):
                score = 1.0
            elif erkannter_name and lief.firmenname:
                score = difflib.SequenceMatcher(None, erkannter_name.lower(), lief.firmenname.lower()).ratio()
            if score > 0.5:
                scored.append((score, lief))
        scored.sort(key=lambda x: x[0], reverse=True)
        lieferant_vorschlaege = [
            LieferantVorschlag(id=lief.id, name=lief.firmenname, score=round(score, 2))
            for score, lief in scored[:3]
        ]

    from .schemas_rechnungen import AnalyseFelder, AnalysePositionResponse
    return AnalyseResponse(
        format=ergebnis.format,
        felder=AnalyseFelder(**ergebnis.felder, konfidenz=ergebnis.konfidenz),
        positionen=[AnalysePositionResponse(**p.__dict__) for p in ergebnis.positionen],
        positionen_modus=ergebnis.positionen_modus,
        warnungen=ergebnis.warnungen,
        temp_url=temp_url,
        temp_path=temp_path,
        lieferant_vorschlaege=lieferant_vorschlaege,
    )


class AnalysierePfadRequest(BaseModel):
    pfad: str

@router.post("/analysieren-pfad", response_model=AnalyseResponse)
def analysiere_rechnung_pfad(body: AnalysierePfadRequest, db: Session = Depends(get_db)):
    """Wie /analysieren, aber liest die Datei vom lokalen Pfad (Tauri Drag-&-Drop auf Windows)."""
    from pathlib import Path as _Path
    pfad = _Path(body.pfad)
    if not pfad.exists() or not pfad.is_file():
        raise HTTPException(status_code=400, detail="Datei nicht gefunden")
    inhalt = pfad.read_bytes()
    dateiname = pfad.name
    ergebnis = analysiere_datei(dateiname, inhalt)

    temp_url = None
    temp_path = None
    if dateiname.lower().endswith(".pdf"):
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        _bereinige_temp_dir()
        token = str(uuid.uuid4())
        temp_file = TEMP_DIR / f"{token}.pdf"
        temp_file.write_bytes(inhalt)
        temp_url = f"/rechnungen/temp/{token}"
        temp_path = str(temp_file.absolute())

    lieferant_vorschlaege: list[LieferantVorschlag] = []
    erkannter_name = ergebnis.felder.get("lieferant_name", "")
    erkannte_ust_id = ergebnis.felder.get("lieferant_ust_id", "")
    if erkannter_name or erkannte_ust_id:
        alle_lieferanten = db.query(Lieferant).filter(Lieferant.aktiv == True).all()
        scored: list[tuple[float, Lieferant]] = []
        for lief in alle_lieferanten:
            score = 0.0
            if erkannte_ust_id and lief.ust_idnr and erkannte_ust_id.replace(" ", "") == lief.ust_idnr.replace(" ", ""):
                score = 1.0
            elif erkannter_name and lief.firmenname:
                score = difflib.SequenceMatcher(None, erkannter_name.lower(), lief.firmenname.lower()).ratio()
            if score > 0.5:
                scored.append((score, lief))
        scored.sort(key=lambda x: x[0], reverse=True)
        lieferant_vorschlaege = [
            LieferantVorschlag(id=lief.id, name=lief.firmenname, score=round(score, 2))
            for score, lief in scored[:3]
        ]

    from .schemas_rechnungen import AnalyseFelder, AnalysePositionResponse
    return AnalyseResponse(
        format=ergebnis.format,
        felder=AnalyseFelder(**ergebnis.felder, konfidenz=ergebnis.konfidenz),
        positionen=[AnalysePositionResponse(**p.__dict__) for p in ergebnis.positionen],
        positionen_modus=ergebnis.positionen_modus,
        warnungen=ergebnis.warnungen,
        temp_url=temp_url,
        temp_path=temp_path,
        lieferant_vorschlaege=lieferant_vorschlaege,
    )


@router.get("/temp/{token}")
def get_temp_pdf(token: str):
    """Temporäre PDF-Vorschau nach Import-Analyse."""
    import re
    if not re.fullmatch(r"[0-9a-f\-]{36}", token):
        raise HTTPException(status_code=404)
    pfad = TEMP_DIR / f"{token}.pdf"
    if not pfad.exists():
        raise HTTPException(status_code=404)
    return FileResponse(pfad, media_type="application/pdf", content_disposition_type="inline")


def _bereinige_temp_dir():
    """Temp-PDFs die älter als 2h sind löschen."""
    import time
    jetzt = time.time()
    if not TEMP_DIR.exists():
        return
    for f in TEMP_DIR.glob("*.pdf"):
        try:
            if jetzt - f.stat().st_mtime > 7200:
                f.unlink()
        except OSError:
            pass


@router.get("/faellig", response_model=list[RechnungResponse])
def get_faellige_rechnungen(tage: int = Query(7, ge=0, le=365), db: Session = Depends(get_db)):
    """Überfällige + in den nächsten N Tagen fällige, unbezahlte Rechnungen."""
    from datetime import date, timedelta
    bis = date.today() + timedelta(days=tage)
    rechnungen = (
        db.query(Rechnung)
        .filter(Rechnung.faellig_am != None)
        .filter(Rechnung.faellig_am <= bis)
        .filter(Rechnung.zahlungsstatus.in_(["offen", "teilweise"]))
        .filter(Rechnung.storniert == False)
        .filter(Rechnung.ist_entwurf == False)
        .order_by(Rechnung.faellig_am.asc())
        .all()
    )
    return [RechnungResponse.from_orm_extended(r) for r in rechnungen]


@router.get("/offene", response_model=list[RechnungResponse])
def get_offene_rechnungen(db: Session = Depends(get_db)):
    """Offene und teilweise bezahlte Rechnungen (für Zahlungs-Vorschläge)."""
    rechnungen = (
        db.query(Rechnung)
        .filter(Rechnung.zahlungsstatus.in_(["offen", "teilweise"]))
        .filter(Rechnung.storniert == False)
        .order_by(Rechnung.datum.desc())
        .all()
    )
    return [RechnungResponse.from_orm_extended(r) for r in rechnungen]


@router.get("", response_model=list[RechnungResponse])
def list_rechnungen(
    typ: Optional[str] = Query(None, description="eingang|ausgang"),
    zahlungsstatus: Optional[str] = Query(None, description="offen|teilweise|bezahlt|entwurf|storniert"),
    monat: Optional[str] = Query(None, description="YYYY-MM"),
    datum_von: Optional[date] = Query(None, description="YYYY-MM-DD"),
    datum_bis: Optional[date] = Query(None, description="YYYY-MM-DD"),
    kunde_id: Optional[int] = Query(None),
    lieferant_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Rechnung)
    if typ:
        if typ not in ("eingang", "ausgang"):
            raise HTTPException(status_code=422, detail="typ muss 'eingang' oder 'ausgang' sein")
        q = q.filter(Rechnung.typ == typ)
    if zahlungsstatus == "entwurf":
        q = q.filter(Rechnung.ist_entwurf == True)
    elif zahlungsstatus == "storniert":
        q = q.filter(Rechnung.storniert == True)
    elif zahlungsstatus:
        q = q.filter(Rechnung.zahlungsstatus == zahlungsstatus)
        q = q.filter(Rechnung.storniert == False)
        q = q.filter(Rechnung.ist_entwurf == False)
    if monat:
        try:
            jahr, mon = monat.split("-")
            q = q.filter(
                extract("year", Rechnung.datum) == int(jahr),
                extract("month", Rechnung.datum) == int(mon),
            )
        except (ValueError, AttributeError):
            raise HTTPException(status_code=422, detail="monat muss im Format YYYY-MM sein")
    if datum_von:
        q = q.filter(Rechnung.datum >= datum_von)
    if datum_bis:
        q = q.filter(Rechnung.datum <= datum_bis)
    if kunde_id is not None:
        q = q.filter(Rechnung.kunde_id == kunde_id)
    if lieferant_id is not None:
        q = q.filter(Rechnung.lieferant_id == lieferant_id)
    rechnungen = q.order_by(Rechnung.datum.desc(), Rechnung.id.desc()).all()
    return [RechnungResponse.from_orm_extended(r) for r in rechnungen]


@router.get("/{rechnung_id}", response_model=RechnungResponse)
def get_rechnung(rechnung_id: int, db: Session = Depends(get_db)):
    r = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    return RechnungResponse.from_orm_extended(r)


@router.post("", response_model=RechnungResponse, status_code=201)
def create_rechnung(data: RechnungCreate, db: Session = Depends(get_db)):
    """Rechnung mit Positionen anlegen. Summen werden automatisch berechnet."""
    unternehmen = db.query(Unternehmen).first()
    ist_kleinunternehmer = unternehmen.ist_kleinunternehmer if unternehmen else False

    # Rechnungsnummer: aus Nummernkreis wenn nicht angegeben
    rechnungsnummer = data.rechnungsnummer
    if not rechnungsnummer:
        nk_typ = "rechnung_ausgang" if data.typ == "ausgang" else "rechnung_eingang"
        nk = db.query(Nummernkreis).filter(Nummernkreis.typ == nk_typ).first()
        if nk:
            if nk.reset_jaehrlich and nk.letztes_jahr and nk.letztes_jahr != data.datum.year:
                nk.naechste_nr = 1
            nk.letztes_jahr = data.datum.year
            nr = nk.naechste_nr
            nk.naechste_nr += 1
            prefix = "RE" if data.typ == "ausgang" else "ER"
            rechnungsnummer = f"{prefix}-{_belegnr_aus_format(nk.format, data.datum, nr)}"
        else:
            count = db.query(Rechnung).filter(Rechnung.typ == data.typ).count()
            prefix = "RE" if data.typ == "ausgang" else "ER"
            rechnungsnummer = f"{prefix}-{str(data.datum.year)[-2:]}{count + 1:04d}"

    rechnung = Rechnung(
        typ=data.typ,
        rechnungsnummer=rechnungsnummer,
        datum=data.datum,
        leistung_von=data.leistung_von, leistung_bis=data.leistung_bis,
        faellig_am=data.faellig_am,
        kunde_id=data.kunde_id,
        lieferant_id=data.lieferant_id,
        partner_freitext=data.partner_freitext,
        kategorie_id=data.kategorie_id,
        notizen=data.notizen,
        externe_belegnr=data.externe_belegnr,
        ist_entwurf=data.ist_entwurf,
        skonto_prozent=data.skonto_prozent,
        skonto_tage=data.skonto_tage,
        bezahlt=False,
        bezahlt_betrag=Decimal("0.00"),
        zahlungsstatus="offen",
        netto_gesamt=Decimal("0.00"),
        ust_gesamt=Decimal("0.00"),
        brutto_gesamt=Decimal("0.00"),
    )
    db.add(rechnung)
    db.flush()  # ID erzeugen

    netto_sum = Decimal("0.00")
    ust_sum = Decimal("0.00")

    for i, pos_data in enumerate(data.positionen, start=1):
        ust_satz = Decimal("0") if ist_kleinunternehmer else pos_data.ust_satz
        ust_betrag, brutto, netto = _berechne_position(pos_data)
        if ist_kleinunternehmer:
            ust_betrag = Decimal("0.00")
            brutto = netto

        pos = Rechnungsposition(
            rechnung_id=rechnung.id,
            artikel_id=getattr(pos_data, "artikel_id", None),
            kategorie_id=getattr(pos_data, "kategorie_id", None),
            position_nr=i,
            beschreibung=pos_data.beschreibung,
            menge=pos_data.menge,
            einheit=pos_data.einheit,
            netto=netto,
            ust_satz=ust_satz,
            ust_betrag=ust_betrag,
            brutto=brutto,
        )
        db.add(pos)
        netto_sum += netto * pos_data.menge
        ust_sum += ust_betrag * pos_data.menge

    Q = Decimal("0.01")
    if data.netto_gesamt_override is not None:
        rechnung.netto_gesamt  = data.netto_gesamt_override.quantize(Q, ROUND_HALF_UP)
        rechnung.ust_gesamt    = (data.ust_gesamt_override or Decimal("0")).quantize(Q, ROUND_HALF_UP)
        rechnung.brutto_gesamt = (data.brutto_gesamt_override or rechnung.netto_gesamt + rechnung.ust_gesamt).quantize(Q, ROUND_HALF_UP)
    else:
        rechnung.netto_gesamt  = netto_sum.quantize(Q, ROUND_HALF_UP)
        rechnung.ust_gesamt    = ust_sum.quantize(Q, ROUND_HALF_UP)
        rechnung.brutto_gesamt = (rechnung.netto_gesamt + rechnung.ust_gesamt).quantize(Q, ROUND_HALF_UP)

    db.commit()
    db.refresh(rechnung)
    return RechnungResponse.from_orm_extended(rechnung)


@router.put("/{rechnung_id}", response_model=RechnungResponse)
def update_rechnung(rechnung_id: int, data: RechnungUpdate, db: Session = Depends(get_db)):
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    if not rechnung.ist_entwurf:
        raise HTTPException(status_code=409, detail="Nur Entwürfe können bearbeitet werden.")

    unternehmen = db.query(Unternehmen).first()
    ist_kleinunternehmer = unternehmen.ist_kleinunternehmer if unternehmen else False

    for field in ("rechnungsnummer", "datum", "leistung_von", "leistung_bis", "faellig_am", "kunde_id",
                  "lieferant_id", "partner_freitext", "kategorie_id", "notizen", "externe_belegnr",
                  "skonto_prozent", "skonto_tage"):
        val = getattr(data, field, None)
        if val is not None:
            setattr(rechnung, field, val)

    if data.positionen is not None:
        # Bestehende Positionen löschen und neu anlegen
        for pos in rechnung.positionen:
            db.delete(pos)
        db.flush()

        netto_sum = Decimal("0.00")
        ust_sum = Decimal("0.00")
        for i, pos_data in enumerate(data.positionen, start=1):
            ust_satz = Decimal("0") if ist_kleinunternehmer else pos_data.ust_satz
            ust_betrag, brutto, netto = _berechne_position(pos_data)
            if ist_kleinunternehmer:
                ust_betrag = Decimal("0.00")
                brutto = netto
            pos = Rechnungsposition(
                rechnung_id=rechnung.id,
                position_nr=i,
                artikel_id=getattr(pos_data, "artikel_id", None),
                kategorie_id=getattr(pos_data, "kategorie_id", None),
                beschreibung=pos_data.beschreibung,
                menge=pos_data.menge,
                einheit=pos_data.einheit,
                netto=netto,
                ust_satz=ust_satz,
                ust_betrag=ust_betrag,
                brutto=brutto,
            )
            db.add(pos)
            netto_sum += netto * pos_data.menge
            ust_sum += ust_betrag * pos_data.menge

        rechnung.netto_gesamt = netto_sum.quantize(Decimal("0.01"), ROUND_HALF_UP)
        rechnung.ust_gesamt = ust_sum.quantize(Decimal("0.01"), ROUND_HALF_UP)
        rechnung.brutto_gesamt = (rechnung.netto_gesamt + rechnung.ust_gesamt).quantize(Decimal("0.01"), ROUND_HALF_UP)

        # Gutschrift: Betrag darf den noch verbleibenden Restbetrag nicht überschreiten
        if rechnung.dokument_typ == "Gutschrift" and rechnung.gutschrift_zu_rechnung_id:
            original = db.query(Rechnung).filter(Rechnung.id == rechnung.gutschrift_zu_rechnung_id).first()
            if original:
                restbetrag = _gutschrift_restbetrag(original, db, ausgenommen_id=rechnung.id)
                diese_gs = abs(rechnung.brutto_gesamt)
                if diese_gs > restbetrag + Decimal("0.01"):   # 1 Cent Toleranz für Rundung
                    def _euro(v: Decimal) -> str:
                        return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            f"Gutschrift überschreitet den zulässigen Betrag. "
                            f"Noch gutschreibbar: {_euro(restbetrag)} – "
                            f"diese Gutschrift: {_euro(diese_gs)}."
                        ),
                    )

    if data.ist_entwurf is not None:
        rechnung.ist_entwurf = data.ist_entwurf

    db.commit()
    db.refresh(rechnung)
    return RechnungResponse.from_orm_extended(rechnung)


def _gutschrift_restbetrag(original: "Rechnung", db: Session, ausgenommen_id: int | None = None) -> Decimal:
    """Gibt zurück wie viel vom Original noch gutgeschrieben werden darf (positiver Betrag).

    original.brutto_gesamt ist positiv (Ausgangsrechnung).
    Gutschriften haben negatives brutto_gesamt.
    Stornierte und Entwurf-Gutschriften zählen nicht mit.
    ausgenommen_id: ID der aktuellen Gutschrift, die nicht mitgezählt werden soll (beim Finalisieren).
    """
    existing = (
        db.query(Rechnung)
        .filter(
            Rechnung.gutschrift_zu_rechnung_id == original.id,
            Rechnung.dokument_typ == "Gutschrift",
            Rechnung.storniert == False,        # noqa: E712
            Rechnung.ist_entwurf == False,      # noqa: E712
        )
        .all()
    )
    bereits = sum(
        (abs(g.brutto_gesamt) for g in existing if ausgenommen_id is None or g.id != ausgenommen_id),
        Decimal("0.00"),
    )
    return abs(original.brutto_gesamt) - bereits


@router.post("/{rechnung_id}/finalisieren", response_model=RechnungResponse)
def finalisiere_rechnung(rechnung_id: int, db: Session = Depends(get_db)):
    """Entwurf finalisieren – danach nicht mehr bearbeitbar."""
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    if not rechnung.ist_entwurf:
        raise HTTPException(status_code=409, detail="Rechnung ist bereits finalisiert.")

    # Gutschrift: Summen-Check – darf den Original-Bruttobetrag nicht überschreiten
    if rechnung.dokument_typ == "Gutschrift" and rechnung.gutschrift_zu_rechnung_id:
        original = db.query(Rechnung).filter(Rechnung.id == rechnung.gutschrift_zu_rechnung_id).first()
        if original:
            restbetrag = _gutschrift_restbetrag(original, db, ausgenommen_id=rechnung.id)
            diese_gs = abs(rechnung.brutto_gesamt)
            if diese_gs > restbetrag + Decimal("0.01"):   # 1 Cent Toleranz für Rundung
                def _euro(v: Decimal) -> str:
                    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Gutschrift überschreitet den zulässigen Betrag. "
                        f"Noch gutschreibbar: {_euro(restbetrag)} – "
                        f"diese Gutschrift: {_euro(diese_gs)}."
                    ),
                )

    rechnung.ist_entwurf = False
    db.commit()
    db.refresh(rechnung)
    return RechnungResponse.from_orm_extended(rechnung)


@router.post("/{rechnung_id}/ausgegeben", response_model=RechnungResponse)
def markiere_ausgegeben(rechnung_id: int, db: Session = Depends(get_db)):
    """Markiert eine finalisierte Rechnung als ausgegeben (gedruckt/versendet).
    Folgedrucke/-versände werden damit als KOPIE gekennzeichnet."""
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    if rechnung.ist_entwurf:
        raise HTTPException(status_code=409, detail="Entwürfe werden nicht als ausgegeben markiert.")
    rechnung.ausgegeben = True
    db.commit()
    db.refresh(rechnung)
    return RechnungResponse.from_orm_extended(rechnung)


@router.get("/{rechnung_id}/pdf")
def rechnung_als_pdf(rechnung_id: int, vorlage: int = -1, download: bool = False, kopie: bool = False, db: Session = Depends(get_db)):
    """PDF der Rechnung generieren und zurückgeben.
    Beim ersten Abruf wird die Rechnung automatisch als 'ausgegeben' markiert.
    Folge-Abrufe erhalten ein KOPIE-Banner.
    kopie=true: Frontend erzwingt Kopie-Markierung unabhängig vom DB-Zustand."""
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    unternehmen = db.query(Unternehmen).first()
    unt_dict = {}
    if unternehmen:
        unt_dict = {
            "firmenname":              unternehmen.firmenname or "",
            "vorname":                 unternehmen.vorname or "",
            "nachname":                unternehmen.nachname or "",
            "strasse":                 unternehmen.strasse or "",
            "hausnummer":              unternehmen.hausnummer or "",
            "plz":                     unternehmen.plz or "",
            "ort":                     unternehmen.ort or "",
            "land":                    unternehmen.land or "DE",
            "steuernummer":            unternehmen.steuernummer or "",
            "ust_idnr":                unternehmen.ust_idnr or "",
            "finanzamt":               unternehmen.finanzamt or "",
            "handelsregister_nr":      unternehmen.handelsregister_nr or "",
            "handelsregister_gericht": unternehmen.handelsregister_gericht or "",
            "telefon":                 unternehmen.telefon or "",
            "email":                   unternehmen.email or "",
            "webseite":                unternehmen.webseite or "",
            "iban":                    unternehmen.iban or "",
            "bic":                     unternehmen.bic or "",
            "bank_name":               unternehmen.bank_name or "",
            "logo_pfad":               unternehmen.logo_pfad or "",
            "berufsbezeichnung":       unternehmen.berufsbezeichnung or "",
            "kammer_mitgliedschaft":   unternehmen.kammer_mitgliedschaft or "",
            "ist_kleinunternehmer":    unternehmen.ist_kleinunternehmer or False,
            "zahlungshinweis_aktiv":      unternehmen.zahlungshinweis_aktiv,
            "pdf_vorlage":                unternehmen.pdf_vorlage if unternehmen else 0,
            "unterschrift_bild":          unternehmen.unterschrift_bild or "",
            "unterschrift_auf_rechnung":  unternehmen.unterschrift_auf_rechnung or False,
            "qr_zahlung_aktiv":           unternehmen.qr_zahlung_aktiv or False,
        }

    # Gutschrift: Originalrechnungsnummer am Objekt hinterlegen (für PDF-Titel)
    if rechnung.gutschrift_zu_rechnung_id:
        original = db.query(Rechnung).filter(Rechnung.id == rechnung.gutschrift_zu_rechnung_id).first()
        rechnung._gutschrift_original_nr = original.rechnungsnummer if original else None

    ist_entwurf = rechnung.ist_entwurf
    # Entwürfe bekommen kein ausgegeben-Flag und keinen Kopie-Hinweis.
    # kopie=True: Frontend weiß bereits, dass ausgegeben=True → Kopie erzwingen
    ist_kopie = (not ist_entwurf) and (rechnung.ausgegeben or kopie)

    # Netto- oder Bruttorechnung: B2B-Kunden (zugferd_aktiv) → Nettorechnung
    ist_netto = (
        rechnung.typ == "ausgang"
        and rechnung.kunde is not None
        and rechnung.kunde.zugferd_aktiv
    )

    # ZUGFeRD: automatisch wenn Kunde zugferd_aktiv gesetzt hat
    kunde_zugferd = (
        not ist_entwurf
        and ist_netto
        and (unternehmen.steuernummer or unternehmen.ust_idnr)
    )
    if kunde_zugferd:
        try:
            pdf_bytes = generate_zugferd_pdf(rechnung, unt_dict)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("ZUGFeRD-Generierung fehlgeschlagen: %s", e, exc_info=True)
            kunde_zugferd = False
            pdf_bytes = generate_rechnung_pdf(rechnung, unt_dict, ist_kopie=ist_kopie, ist_entwurf=ist_entwurf, ist_netto=ist_netto)
    else:
        vorlage_nr = vorlage if vorlage >= 0 else (unternehmen.pdf_vorlage if unternehmen else 0)
        if vorlage_nr == 1:
            pdf_bytes = generate_rechnung_pdf_vorlage1(rechnung, unt_dict, ist_kopie=ist_kopie, ist_entwurf=ist_entwurf, ist_netto=ist_netto)
        else:
            pdf_bytes = generate_rechnung_pdf(rechnung, unt_dict, ist_kopie=ist_kopie, ist_entwurf=ist_entwurf, ist_netto=ist_netto)

    # ausgegeben beim ersten echten PDF-Öffnen setzen:
    # – normale Rechnung: sofort beim ersten Öffnen
    # – Gutschrift: erst wenn Rückerstattung gebucht (zahlungsstatus == 'bezahlt')
    ist_gutschrift_pdf = getattr(rechnung, "dokument_typ", "Rechnung") == "Gutschrift"
    gutschrift_erstattet = ist_gutschrift_pdf and str(getattr(rechnung, "zahlungsstatus", "offen")) == "bezahlt"
    darf_ausgegeben = not ist_gutschrift_pdf or gutschrift_erstattet
    if not ist_entwurf and not rechnung.ausgegeben and darf_ausgegeben:
        rechnung.ausgegeben = True
        db.commit()

    if kunde_zugferd:
        firma = (unt_dict.get("firmenname") or "").replace("/", "-")
        dateiname = f"{firma}_Invoice {rechnung.rechnungsnummer or rechnung_id}.pdf"
    elif getattr(rechnung, "dokument_typ", "Rechnung") == "Gutschrift":
        dateiname = f"Gutschrift_{rechnung.rechnungsnummer or rechnung_id}.pdf"
    else:
        dateiname = f"Rechnung_{rechnung.rechnungsnummer or rechnung_id}.pdf"
    disposition = "attachment" if download else "inline"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{dateiname}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/{rechnung_id}/zugferd")
def rechnung_als_zugferd(rechnung_id: int, db: Session = Depends(get_db)):
    """ZUGFeRD 2.3 / FacturX EN 16931 (Comfort) – PDF/A-3 mit eingebettetem XML.
    Nur für finalisierte Ausgangsrechnungen."""
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    if rechnung.typ != "ausgang":
        raise HTTPException(status_code=400, detail="ZUGFeRD ist nur für Ausgangsrechnungen verfügbar.")
    if rechnung.ist_entwurf:
        raise HTTPException(status_code=400, detail="Entwürfe können nicht als ZUGFeRD exportiert werden.")
    if rechnung.storniert:
        raise HTTPException(status_code=400, detail="Stornierte Rechnungen können nicht als ZUGFeRD exportiert werden.")

    unternehmen = db.query(Unternehmen).first()
    if not unternehmen:
        raise HTTPException(status_code=400, detail="Unternehmensdaten nicht gefunden.")
    if not unternehmen.steuernummer and not unternehmen.ust_idnr:
        raise HTTPException(status_code=400, detail="Für ZUGFeRD wird eine Steuernummer oder USt-IdNr. benötigt.")

    unt_dict = {
        "firmenname":              unternehmen.firmenname or "",
        "vorname":                 unternehmen.vorname or "",
        "nachname":                unternehmen.nachname or "",
        "strasse":                 unternehmen.strasse or "",
        "hausnummer":              unternehmen.hausnummer or "",
        "plz":                     unternehmen.plz or "",
        "ort":                     unternehmen.ort or "",
        "land":                    unternehmen.land or "DE",
        "steuernummer":            unternehmen.steuernummer or "",
        "ust_idnr":                unternehmen.ust_idnr or "",
        "finanzamt":               unternehmen.finanzamt or "",
        "handelsregister_nr":      unternehmen.handelsregister_nr or "",
        "handelsregister_gericht": unternehmen.handelsregister_gericht or "",
        "telefon":                 unternehmen.telefon or "",
        "email":                   unternehmen.email or "",
        "webseite":                unternehmen.webseite or "",
        "iban":                    unternehmen.iban or "",
        "bic":                     unternehmen.bic or "",
        "bank_name":               unternehmen.bank_name or "",
        "logo_pfad":               unternehmen.logo_pfad or "",
        "berufsbezeichnung":       unternehmen.berufsbezeichnung or "",
        "kammer_mitgliedschaft":   unternehmen.kammer_mitgliedschaft or "",
        "ist_kleinunternehmer":    unternehmen.ist_kleinunternehmer or False,
        "zahlungshinweis_aktiv":   unternehmen.zahlungshinweis_aktiv,
        "pdf_vorlage":             unternehmen.pdf_vorlage if unternehmen else 0,
        "unterschrift_bild":       unternehmen.unterschrift_bild or "",
        "unterschrift_auf_rechnung": unternehmen.unterschrift_auf_rechnung or False,
        "qr_zahlung_aktiv":        unternehmen.qr_zahlung_aktiv or False,
    }

    try:
        pdf_bytes = generate_zugferd_pdf(rechnung, unt_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ZUGFeRD-Generierung fehlgeschlagen: {e}")

    firma = (unternehmen.firmenname or "").replace("/", "-")
    dateiname = f"{firma}_Invoice {rechnung.rechnungsnummer or rechnung_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{dateiname}"'},
    )


@router.delete("/{rechnung_id}", status_code=204)
def delete_rechnung(rechnung_id: int, db: Session = Depends(get_db)):
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    if not rechnung.ist_entwurf:
        raise HTTPException(status_code=409, detail="Nur Entwürfe können gelöscht werden.")
    db.delete(rechnung)
    db.commit()


# ---------------------------------------------------------------------------
# Zahlungs-Endpunkte
# ---------------------------------------------------------------------------

def _erstelle_skonto_eintrag(
    db: Session,
    rechnung: "Rechnung",
    rechnung_id: int,
    data: "BarZahlungCreate",
    skonto_betrag: Decimal,
    ust_satz: Decimal,
    steuerbefreiung_grund: str | None,
    zahlung_art: str,
) -> None:
    """Erzeugt den Skonto-Journaleintrag (Erlösschmälerung / erhaltener Skonto)."""
    skonto_art = "Ausgabe" if rechnung.typ == "ausgang" else "Einnahme"
    sk_netto = (skonto_betrag * 100 / (100 + ust_satz)).quantize(Decimal("0.01"), ROUND_HALF_UP) if ust_satz > 0 else skonto_betrag
    sk_ust = (skonto_betrag - sk_netto).quantize(Decimal("0.01"), ROUND_HALF_UP) if ust_satz > 0 else Decimal("0.00")
    sk_konto_skr03, sk_konto_skr04 = _skonto_konto(rechnung.typ, ust_satz)
    # Ausgangsrechnung-Skonto mindert Umsatzsteuer (1776/3806), nicht Vorsteuer (1575/1406)
    ust_art_konto = "Einnahme" if rechnung.typ == "ausgang" else "Ausgabe"
    sk_ust_skr03, sk_ust_skr04 = _ust_konto(ust_art_konto, ust_satz) if ust_satz > 0 else (None, None)
    sk = Journaleintrag(
        datum=data.datum,
        belegnr=_naechste_belegnr_journal(db, data.datum),
        beschreibung=f"Skonto {rechnung.rechnungsnummer}",
        kategorie_id=None,
        konto_skr03=sk_konto_skr03,
        konto_skr04=sk_konto_skr04,
        konto_ust_skr03=sk_ust_skr03,
        konto_ust_skr04=sk_ust_skr04,
        zahlungsart="Skonto",
        art=skonto_art,
        netto_betrag=sk_netto,
        ust_satz=ust_satz,
        ust_betrag=sk_ust,
        brutto_betrag=skonto_betrag,
        vorsteuerabzug=(rechnung.typ == "eingang" and ust_satz > 0),
        steuerbefreiung_grund=steuerbefreiung_grund,
        rechnung_id=rechnung_id,
        immutable=True,
    )
    sk.signatur = signatur_journaleintrag(sk)
    db.add(sk)


@router.post("/{rechnung_id}/zahlung-bar", response_model=BarZahlungResult, status_code=201)
def zahlung_bar_erstellen(rechnung_id: int, data: BarZahlungCreate, db: Session = Depends(get_db)):
    """
    Erstellt eine Journalbuchung für eine Bar-/Kartenzahlung und verknüpft sie mit der Rechnung.
    Bei Eingangsrechnung → Ausgabe, bei Ausgangsrechnung → Einnahme.
    """
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    if rechnung.ist_entwurf:
        raise HTTPException(status_code=409, detail="Entwürfe können nicht kassiert werden. Bitte zuerst finalisieren.")

    ist_gutschrift = getattr(rechnung, "dokument_typ", "Rechnung") == "Gutschrift"
    restbetrag = rechnung.brutto_gesamt - rechnung.bezahlt_betrag

    if abs(restbetrag) <= Decimal("0.004"):
        raise HTTPException(status_code=409, detail="Rechnung ist bereits vollständig bezahlt/verbucht.")

    # -----------------------------------------------------------------------
    # Betrag-Validierung (getrennt je Pfad)
    # -----------------------------------------------------------------------
    betrag_neg: Decimal = Decimal("0")  # nur für Gutschrift-Pfad
    betrag: Decimal = Decimal("0")      # nur für Normal-Pfad

    if ist_gutschrift:
        # Frontend schickt positiven Betrag → Backend negiert für EÜR-korrekte Erlösminderung
        betrag_abs = (data.betrag if data.betrag is not None else abs(restbetrag)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        if betrag_abs > abs(restbetrag) + Decimal("0.01"):
            raise HTTPException(status_code=422,
                detail=f"Betrag ({betrag_abs}) übersteigt den Restbetrag ({abs(restbetrag)}).")
        betrag_neg = -betrag_abs

        # Barkassen-Prüfung: Gutschrift per Bar reduziert Kassenstand
        if data.zahlungsart == "Bar":
            ein_bar = db.query(func.sum(Journaleintrag.brutto_betrag)).filter(
                Journaleintrag.art == "Einnahme", Journaleintrag.zahlungsart == "Bar").scalar() or Decimal("0")
            aus_bar = db.query(func.sum(Journaleintrag.brutto_betrag)).filter(
                Journaleintrag.art == "Ausgabe", Journaleintrag.zahlungsart == "Bar").scalar() or Decimal("0")
            ks_bar = Decimal(str(ein_bar)) - Decimal(str(aus_bar))
            if betrag_abs > ks_bar:
                raise HTTPException(status_code=409,
                    detail=f"Kassenstand nicht ausreichend ({ks_bar:.2f} €) für Rückerstattung ({betrag_abs:.2f} €).")
    else:
        betrag = data.betrag if data.betrag is not None else (
            restbetrag - data.skonto_betrag if data.skonto_betrag else restbetrag
        )
        if betrag > restbetrag:
            raise HTTPException(status_code=422,
                detail=f"Betrag ({betrag}) übersteigt den Restbetrag ({restbetrag}).")
        if data.skonto_betrag and data.skonto_betrag > 0:
            total = (betrag + data.skonto_betrag).quantize(Decimal("0.01"), ROUND_HALF_UP)
            if total > restbetrag.quantize(Decimal("0.01"), ROUND_HALF_UP) + Decimal("0.01"):
                raise HTTPException(status_code=422,
                    detail=f"Betrag + Skonto ({total}) übersteigt den Restbetrag ({restbetrag}).")

    # art: Gutschrift = "Einnahme" mit negativem Betrag (Erlösminderung in EÜR)
    art = "Einnahme" if rechnung.typ == "ausgang" else "Ausgabe"

    # Barkassen-Prüfung Normal-Pfad (Eingangsrechnung per Bar)
    if not ist_gutschrift and art == "Ausgabe" and data.zahlungsart == "Bar":
        einnahmen = db.query(func.sum(Journaleintrag.brutto_betrag)).filter(
            Journaleintrag.art == "Einnahme", Journaleintrag.zahlungsart == "Bar").scalar() or Decimal("0")
        ausgaben = db.query(func.sum(Journaleintrag.brutto_betrag)).filter(
            Journaleintrag.art == "Ausgabe", Journaleintrag.zahlungsart == "Bar").scalar() or Decimal("0")
        kassenstand = Decimal(str(einnahmen)) - Decimal(str(ausgaben))
        if betrag > kassenstand:
            raise HTTPException(status_code=409,
                detail=f"Kassenstand nicht ausreichend. Aktueller Kassenstand: {kassenstand:.2f} €, Ausgabe: {betrag:.2f} €.")

    partner = _partner_name(rechnung)
    beschreibung = data.beschreibung or f"Zahlung {rechnung.rechnungsnummer}: {partner}"

    unternehmen = db.query(Unternehmen).first()
    steuerbefreiung_grund = "§19 UStG" if (unternehmen and unternehmen.ist_kleinunternehmer) else None
    ust_satz = Decimal("0")
    ust_gruppen: list[tuple[Decimal, Decimal, str | None, str | None]] = []
    konto_ust_skr03: str | None = None
    konto_ust_skr04: str | None = None

    if not ist_gutschrift:
        if unternehmen and unternehmen.ist_kleinunternehmer:
            ust_gruppen = [(Decimal("0"), betrag, None, None)]
        elif rechnung.positionen:
            gruppen_brutto: dict[int, Decimal] = {}
            for pos in rechnung.positionen:
                s = int(pos.ust_satz)
                gruppen_brutto[s] = gruppen_brutto.get(s, Decimal("0")) + pos.brutto
            dom_satz = max(gruppen_brutto, key=lambda s: gruppen_brutto[s])
            ust_satz = Decimal(str(dom_satz))
            gesamt_pos_brutto = sum(gruppen_brutto.values())
            rest_g = betrag
            for i, satz in enumerate(sorted(gruppen_brutto.keys())):
                satz_d = Decimal(str(satz))
                g_ust_skr03, g_ust_skr04 = _ust_konto(art, satz_d) if satz > 0 else (None, None)
                if i == len(gruppen_brutto) - 1:
                    g_betrag = rest_g
                else:
                    g_betrag = (betrag * gruppen_brutto[satz] / gesamt_pos_brutto).quantize(Decimal("0.01"), ROUND_HALF_UP)
                    rest_g -= g_betrag
                ust_gruppen.append((satz_d, g_betrag, g_ust_skr03, g_ust_skr04))
        else:
            ust_gruppen = [(Decimal("0"), betrag, None, None)]
        konto_ust_skr03, konto_ust_skr04 = _ust_konto(art, ust_satz) if ust_satz > 0 else (None, None)

    def _erstelle_eintrag(
        kat_id: int | None, kat: "Kategorie | None", brutto: Decimal, beschr: str,
        g_satz: Decimal | None = None,
        g_ust_skr03: str | None = None,
        g_ust_skr04: str | None = None,
    ) -> Journaleintrag:
        satz = g_satz if g_satz is not None else ust_satz
        ust03 = g_ust_skr03 if g_satz is not None else konto_ust_skr03
        ust04 = g_ust_skr04 if g_satz is not None else konto_ust_skr04
        if satz > 0:
            n = (brutto * 100 / (100 + satz)).quantize(Decimal("0.01"), ROUND_HALF_UP)
            u = (brutto - n).quantize(Decimal("0.01"), ROUND_HALF_UP)
        else:
            n, u = brutto, Decimal("0.00")
        e = Journaleintrag(
            datum=data.datum,
            belegnr=_naechste_belegnr_journal(db, data.datum),
            beschreibung=beschr,
            kategorie_id=kat_id,
            konto_skr03=kat.konto_skr03 if kat else None,
            konto_skr04=kat.konto_skr04 if kat else None,
            konto_ust_skr03=ust03,
            konto_ust_skr04=ust04,
            zahlungsart=data.zahlungsart,
            art=art,
            netto_betrag=n,
            ust_satz=satz,
            ust_betrag=u,
            brutto_betrag=brutto,
            vorsteuerabzug=(art == "Ausgabe" and satz > 0),
            steuerbefreiung_grund=steuerbefreiung_grund,
            rechnung_id=rechnung_id,
            immutable=True,
        )
        e.signatur = signatur_journaleintrag(e)
        return e

    # -----------------------------------------------------------------------
    # Gutschrift-Buchung: positionsweise, gleiche Kategorien + USt, negative Einnahme
    # Artikel-IDs bleiben in den Positionen erhalten → Warenbestand-Hook für spätere Warenwirtschaft
    # -----------------------------------------------------------------------
    if ist_gutschrift:
        from collections import defaultdict
        beschreibung_gs = data.beschreibung or f"Gutschrift {rechnung.rechnungsnummer}: {partner}"
        pos_gruppen: dict[tuple, Decimal] = defaultdict(Decimal)
        for pos in rechnung.positionen:
            key = (pos.kategorie_id, int(pos.ust_satz))
            pos_gruppen[key] += pos.brutto  # Gutschrift-Positionen haben bereits negative brutto-Beträge
        gesamt_pos = sum(pos_gruppen.values()) or Decimal("1")  # Division-by-zero Guard

        erster_eintrag_gs = None
        rest_neg = betrag_neg
        gruppen_liste = list(pos_gruppen.items())
        for i, ((kat_id, satz_int), g_brutto_pos) in enumerate(gruppen_liste):
            if i < len(gruppen_liste) - 1:
                anteil = (betrag_neg * g_brutto_pos / gesamt_pos).quantize(Decimal("0.01"), ROUND_HALF_UP)
                rest_neg -= anteil
            else:
                anteil = rest_neg  # letzter Eintrag = Rundungsausgleich

            satz_d = Decimal(str(satz_int)) if not steuerbefreiung_grund else Decimal("0")
            g_ust03, g_ust04 = (_ust_konto(art, satz_d) if satz_int > 0 and not steuerbefreiung_grund else (None, None))
            kat_obj_g = db.query(Kategorie).filter(Kategorie.id == kat_id).first() if kat_id else None
            e = _erstelle_eintrag(kat_id, kat_obj_g, anteil, beschreibung_gs, satz_d, g_ust03, g_ust04)
            db.add(e)
            if i == 0:
                erster_eintrag_gs = e

        if erster_eintrag_gs is None:
            # Fallback: keine Positionen vorhanden
            e = _erstelle_eintrag(None, None, betrag_neg, beschreibung_gs)
            db.add(e)
            erster_eintrag_gs = e

        db.flush()
        _aktualisiere_zahlungsstatus(rechnung)
        # ausgegeben wird NICHT hier gesetzt – das passiert beim ersten PDF-Öffnen nach Erstattung
        db.commit()
        db.refresh(rechnung)
        db.refresh(erster_eintrag_gs)
        return BarZahlungResult(
            journaleintrag_id=erster_eintrag_gs.id,
            journaleintrag_belegnr=erster_eintrag_gs.belegnr,
            rechnung=RechnungResponse.from_orm_extended(rechnung),
        )

    if data.split:
        # Split-Zahlung: Summe der Split-Beträge muss dem Zahlungsbetrag entsprechen
        split_summe = sum(p.betrag for p in data.split).quantize(Decimal("0.01"), ROUND_HALF_UP)
        if split_summe != betrag.quantize(Decimal("0.01"), ROUND_HALF_UP):
            raise HTTPException(
                status_code=422,
                detail=f"Split-Summe ({split_summe} €) stimmt nicht mit Zahlungsbetrag ({betrag} €) überein.",
            )
        erster_eintrag = None
        for i, sp in enumerate(data.split):
            sp_kat = db.query(Kategorie).filter(Kategorie.id == sp.kategorie_id).first()
            if not sp_kat:
                raise HTTPException(status_code=404, detail=f"Kategorie {sp.kategorie_id} nicht gefunden.")
            e = _erstelle_eintrag(sp.kategorie_id, sp_kat, sp.betrag, sp.beschreibung)
            db.add(e)
            if i == 0:
                erster_eintrag = e
                # Erste Split-Kategorie an Rechnung zurückschreiben
                if rechnung.kategorie_id is None:
                    rechnung.kategorie_id = sp.kategorie_id
        db.flush()
        _aktualisiere_zahlungsstatus(rechnung)
        db.commit()
        db.refresh(rechnung)
        db.refresh(erster_eintrag)
        return BarZahlungResult(
            journaleintrag_id=erster_eintrag.id,
            journaleintrag_belegnr=erster_eintrag.belegnr,
            rechnung=RechnungResponse.from_orm_extended(rechnung),
        )

    # Einfache Zahlung (kein Split)
    if rechnung.typ == "ausgang":
        kategorie_id, kat_obj = _erloes_kategorie(db, rechnung)
    else:
        if data.kategorie_id is None and rechnung.kategorie_id is None:
            raise HTTPException(status_code=422, detail="Bitte eine Kategorie für die Buchung auswählen.")
        if data.kategorie_id is not None:
            kat_obj = db.query(Kategorie).filter(Kategorie.id == data.kategorie_id).first()
            if not kat_obj:
                raise HTTPException(status_code=404, detail="Kategorie nicht gefunden.")
            kategorie_id = data.kategorie_id
            if rechnung.kategorie_id is None:
                rechnung.kategorie_id = kategorie_id
        else:
            kategorie_id = rechnung.kategorie_id
            kat_obj = rechnung.kategorie

    erster_eintrag = None
    for i, (g_satz, g_betrag, g_ust_skr03, g_ust_skr04) in enumerate(ust_gruppen):
        e = _erstelle_eintrag(kategorie_id, kat_obj, g_betrag, beschreibung, g_satz, g_ust_skr03, g_ust_skr04)
        db.add(e)
        if i == 0:
            erster_eintrag = e
    eintrag = erster_eintrag

    if data.skonto_betrag and data.skonto_betrag > 0:
        _erstelle_skonto_eintrag(db, rechnung, rechnung_id, data, data.skonto_betrag, ust_satz,
                                 steuerbefreiung_grund, art)

    db.flush()
    _aktualisiere_zahlungsstatus(rechnung)
    db.commit()
    db.refresh(rechnung)
    db.refresh(eintrag)

    return BarZahlungResult(
        journaleintrag_id=eintrag.id,
        journaleintrag_belegnr=eintrag.belegnr,
        rechnung=RechnungResponse.from_orm_extended(rechnung),
    )


@router.post("/{rechnung_id}/storno", response_model=RechnungResponse)
def storno_rechnung(rechnung_id: int, data: StornoRequest, db: Session = Depends(get_db)):
    """Rechnung stornieren (irreversibel). Hat die Rechnung verknüpfte Journal-
    Zahlungen, werden automatisch GoBD-konforme Gegenbuchungen erstellt."""
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    if rechnung.ist_entwurf:
        raise HTTPException(status_code=409, detail="Entwürfe können nicht storniert werden. Bitte den Entwurf löschen.")
    if rechnung.storniert:
        raise HTTPException(status_code=409, detail="Rechnung ist bereits storniert.")
    if not data.grund or not data.grund.strip():
        raise HTTPException(status_code=422, detail="Storno-Begründung darf nicht leer sein.")

    re_nr = rechnung.rechnungsnummer or f"#{rechnung.id}"
    heute = date.today()

    # Für jede verknüpfte Zahlung: Gegenbuchung erstellen (wie Journal-Storno)
    for eintrag in list(rechnung.journaleintraege):
        # Nicht doppelt stornieren
        bereits = db.query(Journaleintrag).filter(
            Journaleintrag.beschreibung.like(f"STORNO {eintrag.belegnr}:%")
        ).first()
        if bereits:
            continue
        storno_art = "Ausgabe" if eintrag.art == "Einnahme" else "Einnahme"
        belegnr = _naechste_belegnr_journal(db, heute)
        gegenbuchung = Journaleintrag(
            datum=heute,
            belegnr=belegnr,
            beschreibung=f"STORNO {eintrag.belegnr}: {re_nr} – {data.grund.strip()}",
            kategorie_id=eintrag.kategorie_id,
            konto_skr03=eintrag.konto_skr03,
            konto_skr04=eintrag.konto_skr04,
            zahlungsart=eintrag.zahlungsart,
            art=storno_art,
            netto_betrag=eintrag.netto_betrag,
            ust_satz=eintrag.ust_satz,
            ust_betrag=eintrag.ust_betrag,
            brutto_betrag=eintrag.brutto_betrag,
            vorsteuerabzug=False,
            steuerbefreiung_grund=None,
            immutable=True,
        )
        gegenbuchung.signatur = signatur_journaleintrag(gegenbuchung)
        db.add(gegenbuchung)

    rechnung.storniert = True
    rechnung.storno_grund = data.grund.strip()
    rechnung.immutable = True
    db.commit()
    db.refresh(rechnung)
    return RechnungResponse.from_orm_extended(rechnung)


@router.post("/{rechnung_id}/gutschrift", response_model=RechnungResponse, status_code=201)
def create_gutschrift(rechnung_id: int, db: Session = Depends(get_db)):
    """Erstellt eine Gutschrift aus einer bestehenden Ausgangsrechnung.
    Alle Positionen werden übernommen (Mengen negiert), eigene RE-Nummer, Entwurf."""
    original = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    if original.typ != "ausgang":
        raise HTTPException(status_code=409, detail="Gutschriften können nur für Ausgangsrechnungen erstellt werden.")
    if original.dokument_typ == "Gutschrift":
        raise HTTPException(status_code=409, detail="Aus einer Gutschrift kann keine weitere Gutschrift erstellt werden.")
    if original.storniert:
        raise HTTPException(status_code=409, detail="Stornierte Rechnungen können nicht als Vorlage für eine Gutschrift dienen.")

    # Prüfen ob bereits der volle Betrag durch finalisierte Gutschriften abgedeckt ist
    restbetrag = _gutschrift_restbetrag(original, db)
    if restbetrag <= Decimal("0.01"):   # 1 Cent Toleranz
        def _euro(v: Decimal) -> str:
            return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
        raise HTTPException(
            status_code=409,
            detail=(
                f"Der Rechnungsbetrag ({_euro(abs(original.brutto_gesamt))}) ist bereits vollständig "
                f"durch bestehende Gutschriften abgedeckt. Storniere eine Gutschrift, um eine neue erstellen zu können."
            ),
        )

    heute = date.today()

    # Rechnungsnummer aus Nummernkreis
    nk = db.query(Nummernkreis).filter(Nummernkreis.typ == "rechnung_ausgang").first()
    if nk:
        if nk.reset_jaehrlich and nk.letztes_jahr and nk.letztes_jahr != heute.year:
            nk.naechste_nr = 1
        nk.letztes_jahr = heute.year
        nr = nk.naechste_nr
        nk.naechste_nr += 1
        rechnungsnummer = f"GS-{_belegnr_aus_format(nk.format, heute, nr)}"
    else:
        count = db.query(Rechnung).filter(Rechnung.typ == "ausgang").count()
        rechnungsnummer = f"GS-{str(heute.year)[-2:]}{count + 1:04d}"

    orig_nr = original.rechnungsnummer or f"#{original.id}"

    gutschrift = Rechnung(
        typ="ausgang",
        dokument_typ="Gutschrift",
        gutschrift_zu_rechnung_id=original.id,
        rechnungsnummer=rechnungsnummer,
        datum=heute,
        faellig_am=None,
        kunde_id=original.kunde_id,
        partner_freitext=original.partner_freitext,
        kategorie_id=original.kategorie_id,
        notizen=None,
        skonto_prozent=None,
        skonto_tage=None,
        ist_entwurf=True,
        bezahlt=False,
        bezahlt_betrag=Decimal("0.00"),
        zahlungsstatus="offen",
        netto_gesamt=Decimal("0.00"),
        ust_gesamt=Decimal("0.00"),
        brutto_gesamt=Decimal("0.00"),
    )
    db.add(gutschrift)
    db.flush()

    netto_sum = Decimal("0.00")
    ust_sum = Decimal("0.00")

    for nr_pos, pos in enumerate(
        sorted(original.positionen, key=lambda p: p.position_nr), start=1
    ):
        menge_neg = -(pos.menge)
        netto_pos = (pos.netto * menge_neg / pos.menge).quantize(Decimal("0.01"), ROUND_HALF_UP)
        ust_betrag = (netto_pos * pos.ust_satz / 100).quantize(Decimal("0.01"), ROUND_HALF_UP) if pos.ust_satz else Decimal("0.00")
        brutto_pos = netto_pos + ust_betrag

        neue_pos = Rechnungsposition(
            rechnung_id=gutschrift.id,
            artikel_id=pos.artikel_id,
            position_nr=nr_pos,
            beschreibung=pos.beschreibung,
            menge=menge_neg,
            einheit=pos.einheit,
            netto=netto_pos,
            ust_satz=pos.ust_satz,
            ust_betrag=ust_betrag,
            brutto=brutto_pos,
            kategorie_id=pos.kategorie_id,
        )
        db.add(neue_pos)
        netto_sum += netto_pos
        ust_sum += ust_betrag

    gutschrift.netto_gesamt = netto_sum.quantize(Decimal("0.01"), ROUND_HALF_UP)
    gutschrift.ust_gesamt = ust_sum.quantize(Decimal("0.01"), ROUND_HALF_UP)
    gutschrift.brutto_gesamt = (netto_sum + ust_sum).quantize(Decimal("0.01"), ROUND_HALF_UP)

    db.commit()
    db.refresh(gutschrift)
    resp = RechnungResponse.from_orm_extended(gutschrift)
    resp.gutschrift_zu_rechnung_nr = orig_nr
    return resp


@router.get("/{rechnung_id}/zahlungen", response_model=list[ZahlungKompakt])
def get_rechnung_zahlungen(rechnung_id: int, db: Session = Depends(get_db)):
    """Alle verknüpften Journaleinträge für eine Rechnung."""
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    return [
        ZahlungKompakt(
            id=e.id,
            belegnr=e.belegnr,
            datum=e.datum,
            brutto_betrag=e.brutto_betrag,
            art=e.art,
            zahlungsart=e.zahlungsart,
        )
        for e in rechnung.journaleintraege
    ]


# ---------------------------------------------------------------------------
# Beleg-Upload / Download / Löschen
# ---------------------------------------------------------------------------

@router.post("/{rechnung_id}/beleg", response_model=BelegResponse, status_code=201)
async def upload_beleg(rechnung_id: int, datei: UploadFile = File(...), db: Session = Depends(get_db)):
    """Dateianhang (PDF/Bild) an eine Rechnung hängen."""
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")

    mime = datei.content_type or ""
    if mime not in ERLAUBTE_MIME_TYPES:
        raise HTTPException(status_code=422, detail=f"Dateityp '{mime}' nicht erlaubt. Erlaubt: PDF, JPEG, PNG, TIFF.")

    inhalt = await datei.read()
    sha256 = hashlib.sha256(inhalt).hexdigest()

    jetzt = datetime.now()
    ziel_dir = BELEG_DIR / str(jetzt.year) / jetzt.strftime("%m")
    ziel_dir.mkdir(parents=True, exist_ok=True)

    original = Path(datei.filename or "beleg")
    stem = original.stem[:50]
    suffix = original.suffix.lower() or ".bin"
    dateiname_lokal = f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
    rel_pfad = f"belege/{jetzt.year}/{jetzt.strftime('%m')}/{dateiname_lokal}"

    (ziel_dir / dateiname_lokal).write_bytes(inhalt)

    # Alten Beleg ersetzen wenn vorhanden
    if rechnung.beleg_id:
        alter_beleg = db.query(Beleg).filter(Beleg.id == rechnung.beleg_id).first()
        if alter_beleg:
            alter_pfad = APP_DATA_DIR / "uploads" / alter_beleg.dateiname
            if alter_pfad.exists():
                alter_pfad.unlink()
            db.delete(alter_beleg)

    beleg = Beleg(
        dateiname=rel_pfad,
        original_name=datei.filename or "beleg",
        mime_type=mime,
        dateigroesse=len(inhalt),
        sha256=sha256,
    )
    db.add(beleg)
    db.flush()
    rechnung.beleg_id = beleg.id
    db.commit()
    db.refresh(beleg)
    return beleg


@router.get("/{rechnung_id}/beleg")
def download_beleg(rechnung_id: int, db: Session = Depends(get_db)):
    """Angehängte Datei einer Rechnung herunterladen."""
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung or not rechnung.beleg_id:
        raise HTTPException(status_code=404, detail="Kein Beleg vorhanden.")
    beleg = db.query(Beleg).filter(Beleg.id == rechnung.beleg_id).first()
    if not beleg:
        raise HTTPException(status_code=404, detail="Beleg-Datensatz nicht gefunden.")
    pfad = APP_DATA_DIR / "uploads" / beleg.dateiname
    if not pfad.exists():
        raise HTTPException(status_code=404, detail="Beleg-Datei nicht gefunden.")
    return FileResponse(
        path=str(pfad),
        media_type=beleg.mime_type or "application/octet-stream",
        filename=beleg.original_name,
        content_disposition_type="inline",
    )


@router.delete("/{rechnung_id}/beleg", status_code=204)
def delete_beleg(rechnung_id: int, db: Session = Depends(get_db)):
    """Beleg von einer Rechnung entfernen und Datei löschen."""
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung or not rechnung.beleg_id:
        raise HTTPException(status_code=404, detail="Kein Beleg vorhanden.")
    beleg = db.query(Beleg).filter(Beleg.id == rechnung.beleg_id).first()
    rechnung.beleg_id = None
    if beleg:
        pfad = APP_DATA_DIR / "uploads" / beleg.dateiname
        if pfad.exists():
            pfad.unlink()
        db.delete(beleg)
    db.commit()
