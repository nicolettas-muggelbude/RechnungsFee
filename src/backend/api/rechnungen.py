"""
Rechnungen-API (Eingang + Ausgang) mit Journal-Verknüpfung.
"""

import difflib
import hashlib
import re
import shutil
import uuid
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from utils.pdfa_konverter import konvertiere_zu_pdfa
from pydantic import BaseModel
from fastapi.responses import FileResponse, Response
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from database.connection import get_db, APP_DATA_DIR
from database.models import (
    Beleg, Kunde, Lieferant, Rechnung, Rechnungsposition, Journaleintrag,
    Kategorie, Unternehmen, Nummernkreis,
)
from utils.signatur import signatur_journaleintrag
from utils.pdf_rechnung import generate_rechnung_pdf
from utils.pdf_rechnung_vorlage1 import generate_rechnung_pdf_vorlage1
from utils.zugferd import generate_zugferd_pdf
from utils.rechnungs_parser import analysiere_datei
from utils.pdf_kopie import speichere_original_pdf, lade_original_mit_kopie_stempel
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
              .replace("JJJJ", year_4)  # dt. Alias
              .replace("YY",   year_2)
              .replace("JJ",   year_2)  # dt. Alias: Jahr
              .replace("MM",   month)
              .replace("TT",   day))

    def _pad(m: _re.Match) -> str:
        return str(nr).zfill(len(m.group()))

    result = _re.sub(r"#+", _pad, result)
    result = _re.sub(r"N+", _pad, result)  # dt. Alias: Nummer
    return result


def _naechste_belegnr_journal(db: Session, datum: date) -> str:
    """Journal-Belegnummer (analog zu journal.py)."""
    nk = db.query(Nummernkreis).filter(Nummernkreis.typ == "journal").first()
    if not nk:
        count = db.query(Journaleintrag).count()
        return f"{str(datum.year)[-2:]}{count + 1:04d}"
    # Jahreswechsel-Reset nur vorwärts (Rückdatierung darf Counter nicht zurücksetzen)
    if nk.reset_jaehrlich and nk.letztes_jahr and datum.year > nk.letztes_jahr:
        nk.naechste_nr = 1
    if not nk.letztes_jahr or datum.year > nk.letztes_jahr:
        nk.letztes_jahr = datum.year
    nr = nk.naechste_nr
    nk.naechste_nr += 1
    candidate = _belegnr_aus_format(nk.format, datum, nr)
    # Kollisions-Schutz: belegnr überspringen wenn durch Rückdatierung bereits vergeben
    while db.query(Journaleintrag).filter(Journaleintrag.belegnr == candidate).first():
        nr = nk.naechste_nr
        nk.naechste_nr += 1
        candidate = _belegnr_aus_format(nk.format, datum, nr)
    return candidate


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


def _berechne_vorsteuer(ust_betrag: Decimal, vorsteuerabzug: bool, kat) -> Decimal:
    """Tatsächlich abziehbarer Vorsteuer-Betrag (berücksichtigt kat.vorsteuer_prozent)."""
    if not vorsteuerabzug or ust_betrag == 0:
        return Decimal("0.00")
    if kat is not None and int(kat.vorsteuer_prozent) < 100:
        return (ust_betrag * kat.vorsteuer_prozent / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return ust_betrag


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
    """Gibt (ust_betrag, brutto, eff_netto) zurück – nach Positionsrabatt.
    Bei Differenzbesteuerung (§25a) wird keine USt separat ausgewiesen –
    brutto = netto = netto-Eingabe (Preis ist der Rechnungspreis).
    """
    netto = pos_data.netto.quantize(Decimal("0.01"), ROUND_HALF_UP)
    rabatt = getattr(pos_data, "rabatt_prozent", Decimal("0")) or Decimal("0")
    if rabatt:
        netto = (netto * (1 - rabatt / 100)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    if getattr(pos_data, "differenzbesteuerung", False) or pos_data.ust_satz == 0:
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
        # Automatisch: verknüpfter Auftrag → abgeschlossen
        # Pfad 1: Rechnung direkt aus Auftrag (rechnung_zu_auftrag_id)
        # Pfad 2: Auftrag → Proforma → Rechnung (proforma_zu_auftrag_id + rechnung_zu_proforma_id)
        # Pfad 3: Auftrag → Lieferschein → Rechnung (lieferschein_zu_auftrag_id + lieferschein_zu_rechnung_id)
        try:
            from sqlalchemy import inspect as _sa_inspect
            _session = _sa_inspect(rechnung).session
            if _session:
                _auftrag = _session.query(rechnung.__class__).filter(
                    rechnung.__class__.rechnung_zu_auftrag_id == rechnung.id,
                    rechnung.__class__.dokument_typ == "Auftrag",
                ).first()
                if not _auftrag:
                    _proforma = _session.query(rechnung.__class__).filter(
                        rechnung.__class__.rechnung_zu_proforma_id == rechnung.id,
                        rechnung.__class__.dokument_typ == "Proforma",
                    ).first()
                    if _proforma:
                        _auftrag = _session.query(rechnung.__class__).filter(
                            rechnung.__class__.proforma_zu_auftrag_id == _proforma.id,
                            rechnung.__class__.dokument_typ == "Auftrag",
                        ).first()
                if not _auftrag:
                    _lieferschein = _session.query(rechnung.__class__).filter(
                        rechnung.__class__.lieferschein_zu_rechnung_id == rechnung.id,
                        rechnung.__class__.dokument_typ == "Lieferschein",
                    ).first()
                    if _lieferschein:
                        _auftrag = _session.query(rechnung.__class__).filter(
                            rechnung.__class__.lieferschein_zu_auftrag_id == _lieferschein.id,
                            rechnung.__class__.dokument_typ == "Auftrag",
                        ).first()
                if _auftrag and _auftrag.auftrag_status not in ("abgeschlossen", "storniert"):
                    _auftrag.auftrag_status = "abgeschlossen"
        except Exception:
            pass
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
        # Rechtsformkürzel entfernen, Trennzeichen normalisieren → besserer Textvergleich
        # "Penny-Markt GmbH" → "penny markt"  |  "PENNY" → "penny"
        _re_rechtsform = re.compile(
            r"\b(?:GmbH|UG|AG|e\.?K\.?|KG|OHG|GbR|e\.?V\.?|Ltd|Inc|Co\.?|SE|GbR)\b",
            re.IGNORECASE,
        )
        def _norm(name: str) -> str:
            n = _re_rechtsform.sub("", name)
            n = re.sub(r"[-_/\\|]", " ", n)
            return re.sub(r"\s+", " ", n).strip().lower()

        norm_erkannt = _norm(erkannter_name)
        for lief in alle_lieferanten:
            score = 0.0
            if erkannte_ust_id and lief.ust_idnr and erkannte_ust_id.replace(" ", "") == lief.ust_idnr.replace(" ", ""):
                score = 1.0
            elif erkannter_name and lief.firmenname:
                norm_lief = _norm(lief.firmenname)
                # Teilstring-Check: "penny" ⊂ "penny markt" → hoher Score
                if len(norm_erkannt) >= 4 and (norm_erkannt in norm_lief or norm_lief in norm_erkannt):
                    score = 0.8
                else:
                    score = difflib.SequenceMatcher(None, norm_erkannt, norm_lief).ratio()
            if score > 0.4:
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
        _re_rechtsform2 = re.compile(
            r"\b(?:GmbH|UG|AG|e\.?K\.?|KG|OHG|GbR|e\.?V\.?|Ltd|Inc|Co\.?|SE|GbR)\b",
            re.IGNORECASE,
        )
        def _norm2(name: str) -> str:
            n = _re_rechtsform2.sub("", name)
            n = re.sub(r"[-_/\\|]", " ", n)
            return re.sub(r"\s+", " ", n).strip().lower()

        norm_erkannt2 = _norm2(erkannter_name)
        for lief in alle_lieferanten:
            score = 0.0
            if erkannte_ust_id and lief.ust_idnr and erkannte_ust_id.replace(" ", "") == lief.ust_idnr.replace(" ", ""):
                score = 1.0
            elif erkannter_name and lief.firmenname:
                norm_lief2 = _norm2(lief.firmenname)
                if len(norm_erkannt2) >= 4 and (norm_erkannt2 in norm_lief2 or norm_lief2 in norm_erkannt2):
                    score = 0.8
                else:
                    score = difflib.SequenceMatcher(None, norm_erkannt2, norm_lief2).ratio()
            if score > 0.4:
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
    dokument_typ: Optional[str] = Query(None, description="Rechnung|Gutschrift|Lieferschein"),
    db: Session = Depends(get_db),
):
    q = db.query(Rechnung)
    if dokument_typ:
        q = q.filter(Rechnung.dokument_typ == dokument_typ)
    else:
        # Lieferscheine, Angebote, Proformas und Aufträge nur auf explizite Anfrage
        q = q.filter(Rechnung.dokument_typ != "Lieferschein")
        q = q.filter(Rechnung.dokument_typ != "Angebot")
        q = q.filter(Rechnung.dokument_typ != "Proforma")
        q = q.filter(Rechnung.dokument_typ != "Auftrag")
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


@router.get("/auftraege", response_model=list[RechnungResponse])
def liste_auftraege(db: Session = Depends(get_db)):
    """Alle Aufträge zurückgeben."""
    auftraege = db.query(Rechnung).filter(
        Rechnung.dokument_typ == "Auftrag"
    ).order_by(Rechnung.datum.desc(), Rechnung.id.desc()).all()
    return [RechnungResponse.from_orm_extended(a) for a in auftraege]


@router.post("/auftraege", response_model=RechnungResponse, status_code=201)
def auftrag_erstellen(data: "RechnungCreate", db: Session = Depends(get_db)):
    """Erstellt einen neuen Auftrag ohne Angebot-Quelle."""
    heute = date.today()
    auftragsnummer = _naechste_auftragsnummer(heute, db)
    auftrag = Rechnung(
        typ="ausgang",
        rechnungsnummer=auftragsnummer,
        datum=data.datum or heute,
        leistung_von=data.leistung_von,
        leistung_bis=data.leistung_bis,
        kunde_id=data.kunde_id,
        partner_freitext=data.partner_freitext,
        notizen=data.notizen,
        ist_entwurf=data.ist_entwurf,
        dokument_typ="Auftrag",
        auftrag_status="offen",
        netto_gesamt=Decimal("0.00"),
        ust_gesamt=Decimal("0.00"),
        brutto_gesamt=Decimal("0.00"),
        skonto_prozent=data.skonto_prozent,
        skonto_tage=data.skonto_tage,
        dokumentenpaket_id=data.dokumentenpaket_id,
    )
    db.add(auftrag)
    db.flush()
    # Positionen
    netto_sum = Decimal("0.00")
    ust_sum = Decimal("0.00")
    for i, pos_data in enumerate(data.positionen or [], start=1):
        netto_ep = Decimal(str(pos_data.netto)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        ust_satz = Decimal(str(pos_data.ust_satz))
        ust_ep = (netto_ep * ust_satz / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
        brutto_ep = (netto_ep + ust_ep).quantize(Decimal("0.01"), ROUND_HALF_UP)
        menge = Decimal(str(pos_data.menge))
        pos = Rechnungsposition(
            rechnung_id=auftrag.id,
            position_nr=i,
            beschreibung=pos_data.beschreibung,
            menge=menge,
            einheit=pos_data.einheit or "Stk.",
            netto=netto_ep,
            ust_satz=ust_satz,
            ust_betrag=ust_ep,
            brutto=brutto_ep,
            artikel_id=pos_data.artikel_id,
            kategorie_id=pos_data.kategorie_id,
        )
        db.add(pos)
        netto_sum += netto_ep * menge
        ust_sum += ust_ep * menge
    Q = Decimal("0.01")
    auftrag.netto_gesamt = netto_sum.quantize(Q, ROUND_HALF_UP)
    auftrag.ust_gesamt = ust_sum.quantize(Q, ROUND_HALF_UP)
    auftrag.brutto_gesamt = (auftrag.netto_gesamt + auftrag.ust_gesamt).quantize(Q, ROUND_HALF_UP)
    db.commit()
    db.refresh(auftrag)
    return RechnungResponse.from_orm_extended(auftrag)


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
        if data.dokument_typ == "Lieferschein":
            nk = db.query(Nummernkreis).filter(Nummernkreis.typ == "lieferschein").first()
            if nk:
                if nk.reset_jaehrlich and nk.letztes_jahr and nk.letztes_jahr != data.datum.year:
                    nk.naechste_nr = 1
                nk.letztes_jahr = data.datum.year
                nr = nk.naechste_nr
                nk.naechste_nr += 1
                rechnungsnummer = _belegnr_aus_format(nk.format, data.datum, nr)
            else:
                count = db.query(Rechnung).filter(Rechnung.dokument_typ == "Lieferschein").count()
                rechnungsnummer = f"LS-{str(data.datum.year)[-2:]}{count + 1:04d}"
        elif data.dokument_typ == "Angebot":
            nk = db.query(Nummernkreis).filter(Nummernkreis.typ == "angebot").first()
            if nk:
                if nk.reset_jaehrlich and nk.letztes_jahr and nk.letztes_jahr != data.datum.year:
                    nk.naechste_nr = 1
                nk.letztes_jahr = data.datum.year
                nr = nk.naechste_nr
                nk.naechste_nr += 1
                rechnungsnummer = _belegnr_aus_format(nk.format, data.datum, nr)
            else:
                count = db.query(Rechnung).filter(Rechnung.dokument_typ == "Angebot").count()
                rechnungsnummer = f"ANG-{str(data.datum.year)[-2:]}{count + 1:04d}"
        elif data.dokument_typ == "Proforma":
            if not data.ist_entwurf:
                rechnungsnummer = _naechste_proformanummer(data.datum, db)
            # else: Entwurf-Proforma ohne Nummer (wie Angebot-Entwurf)
        else:
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

    # Proforma: faellig_am aus Unternehmens-Standard wenn nicht übergeben; kein Skonto
    proforma_faellig_am = data.faellig_am
    if data.dokument_typ == "Proforma" and proforma_faellig_am is None:
        _unt = db.query(Unternehmen).first()
        if _unt:
            from datetime import timedelta as _td
            _zt = int(getattr(_unt, "standard_zahlungsziel", 14) or 14)
            proforma_faellig_am = data.datum + _td(days=_zt)

    rechnung = Rechnung(
        typ=data.typ,
        rechnungsnummer=rechnungsnummer,
        datum=data.datum,
        leistung_von=data.leistung_von, leistung_bis=data.leistung_bis,
        faellig_am=proforma_faellig_am if data.dokument_typ == "Proforma" else data.faellig_am,
        kunde_id=data.kunde_id,
        lieferant_id=data.lieferant_id,
        partner_freitext=data.partner_freitext,
        kategorie_id=data.kategorie_id,
        notizen=data.notizen,
        einleitungstext=data.einleitungstext,
        externe_belegnr=data.externe_belegnr,
        ist_entwurf=data.ist_entwurf,
        skonto_prozent=None if data.dokument_typ == "Proforma" else data.skonto_prozent,
        skonto_tage=None if data.dokument_typ == "Proforma" else data.skonto_tage,
        dokument_typ=data.dokument_typ,
        lieferadresse_id=data.lieferadresse_id if data.dokument_typ == "Lieferschein" else None,
        gueltig_bis=data.gueltig_bis if data.dokument_typ == "Angebot" else None,
        dokumentenpaket_id=data.dokumentenpaket_id if data.dokument_typ == "Angebot" else None,
        angebot_status="offen" if data.dokument_typ == "Angebot" else None,
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
        ist_diff = getattr(pos_data, "differenzbesteuerung", False)
        # §25a: kein USt-Ausweis (ust_satz = 0 auf der Rechnung)
        ust_satz = Decimal("0") if (ist_kleinunternehmer or ist_diff) else pos_data.ust_satz
        ust_betrag, brutto, netto = _berechne_position(pos_data)
        if ist_kleinunternehmer:
            ust_betrag = Decimal("0.00")
            brutto = netto

        # §25a: EK + nominalen USt-Satz zum Buchungszeitpunkt speichern
        ek_netto_25a = None
        ust_satz_25a = pos_data.ust_satz if ist_diff else None  # Original-Satz vor §25a-Override
        if ist_diff:
            a_id = getattr(pos_data, "artikel_id", None)
            if a_id:
                from database.models import Artikel
                art_obj = db.query(Artikel).filter(Artikel.id == a_id).first()
                if art_obj:
                    ek_netto_25a = art_obj.ek_netto

        pos = Rechnungsposition(
            rechnung_id=rechnung.id,
            artikel_id=getattr(pos_data, "artikel_id", None),
            kategorie_id=getattr(pos_data, "kategorie_id", None),
            position_nr=i,
            beschreibung=pos_data.beschreibung,
            menge=pos_data.menge,
            einheit=pos_data.einheit,
            netto=pos_data.netto,          # Original-Einzelpreis (vor Positionsrabatt)
            rabatt_prozent=getattr(pos_data, "rabatt_prozent", Decimal("0")) or Decimal("0"),
            ust_satz=ust_satz,
            ust_betrag=ust_betrag,         # basiert auf rabattiertem Netto
            brutto=brutto,                 # basiert auf rabattiertem Netto
            differenzbesteuerung=ist_diff,
            ek_netto_25a=ek_netto_25a,
            ust_satz_25a=ust_satz_25a,
        )
        db.add(pos)
        netto_sum += netto * pos_data.menge   # netto = eff_netto nach Positionsrabatt
        ust_sum += ust_betrag * pos_data.menge

    Q = Decimal("0.01")
    rechnung.rabatt_prozent = getattr(data, "rabatt_prozent", Decimal("0")) or Decimal("0")
    if data.netto_gesamt_override is not None:
        rechnung.netto_gesamt  = data.netto_gesamt_override.quantize(Q, ROUND_HALF_UP)
        rechnung.ust_gesamt    = (data.ust_gesamt_override or Decimal("0")).quantize(Q, ROUND_HALF_UP)
        rechnung.brutto_gesamt = (data.brutto_gesamt_override or rechnung.netto_gesamt + rechnung.ust_gesamt).quantize(Q, ROUND_HALF_UP)
    else:
        if rechnung.rabatt_prozent:
            faktor = 1 - rechnung.rabatt_prozent / 100
            rechnung.netto_gesamt = (netto_sum * faktor).quantize(Q, ROUND_HALF_UP)
            rechnung.ust_gesamt   = (ust_sum * faktor).quantize(Q, ROUND_HALF_UP)
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
    if not rechnung.ist_entwurf and rechnung.dokument_typ not in ("Angebot", "Auftrag", "Proforma"):
        raise HTTPException(status_code=409, detail="Nur Entwürfe können bearbeitet werden.")
    if rechnung.dokument_typ == "Auftrag" and rechnung.auftrag_status not in ("offen", None):
        raise HTTPException(status_code=409, detail="Nur offene Aufträge können bearbeitet werden.")

    unternehmen = db.query(Unternehmen).first()
    ist_kleinunternehmer = unternehmen.ist_kleinunternehmer if unternehmen else False

    for field in ("rechnungsnummer", "datum", "leistung_von", "leistung_bis", "faellig_am", "kunde_id",
                  "lieferant_id", "partner_freitext", "kategorie_id", "notizen", "externe_belegnr",
                  "skonto_prozent", "skonto_tage", "gueltig_bis", "dokumentenpaket_id"):
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
            ist_diff = getattr(pos_data, "differenzbesteuerung", False)
            ust_satz = Decimal("0") if (ist_kleinunternehmer or ist_diff) else pos_data.ust_satz
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
                netto=pos_data.netto,      # Original-Einzelpreis
                rabatt_prozent=getattr(pos_data, "rabatt_prozent", Decimal("0")) or Decimal("0"),
                ust_satz=ust_satz,
                ust_betrag=ust_betrag,
                brutto=brutto,
                differenzbesteuerung=ist_diff,
            )
            db.add(pos)
            netto_sum += netto * pos_data.menge   # netto = eff_netto nach Positionsrabatt
            ust_sum += ust_betrag * pos_data.menge

        Q2 = Decimal("0.01")
        rechnung.rabatt_prozent = getattr(data, "rabatt_prozent", Decimal("0")) or Decimal("0")
        if rechnung.rabatt_prozent:
            faktor = 1 - rechnung.rabatt_prozent / 100
            rechnung.netto_gesamt = (netto_sum * faktor).quantize(Q2, ROUND_HALF_UP)
            rechnung.ust_gesamt   = (ust_sum * faktor).quantize(Q2, ROUND_HALF_UP)
        else:
            rechnung.netto_gesamt = netto_sum.quantize(Q2, ROUND_HALF_UP)
            rechnung.ust_gesamt = ust_sum.quantize(Q2, ROUND_HALF_UP)
        rechnung.brutto_gesamt = (rechnung.netto_gesamt + rechnung.ust_gesamt).quantize(Q2, ROUND_HALF_UP)

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

    # Auftrag-Status auf rechnung_gestellt setzen sobald Rechnung finalisiert
    if rechnung.dokument_typ == "Rechnung":
        _auftrag = db.query(Rechnung).filter(
            Rechnung.rechnung_zu_auftrag_id == rechnung.id,
            Rechnung.dokument_typ == "Auftrag",
        ).first()
        if _auftrag and _auftrag.auftrag_status not in ("abgeschlossen", "storniert"):
            _auftrag.auftrag_status = "rechnung_gestellt"

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
            "einleitungstext":            unternehmen.einleitungstext or "",
        }

    # Gutschrift: Originalrechnungsnummer am Objekt hinterlegen (für PDF-Titel)
    if rechnung.gutschrift_zu_rechnung_id:
        original = db.query(Rechnung).filter(Rechnung.id == rechnung.gutschrift_zu_rechnung_id).first()
        rechnung._gutschrift_original_nr = original.rechnungsnummer if original else None

    # Bezugsdokumente für PDF-Titel ermitteln
    _dok = getattr(rechnung, "dokument_typ", "Rechnung") or "Rechnung"
    if _dok in ("Rechnung", "Lieferschein", "Proforma"):
        # Quell-Angebot (direkt)
        _angebot_col = {
            "Rechnung":     Rechnung.rechnung_zu_angebot_id,
            "Lieferschein": Rechnung.lieferschein_zu_angebot_id,
            "Proforma":     Rechnung.proforma_zu_angebot_id,
        }[_dok]
        _quell_angebot = db.query(Rechnung).filter(_angebot_col == rechnung_id).first()
        rechnung._quell_angebot_nr = _quell_angebot.rechnungsnummer if _quell_angebot else None

        # Quell-Auftrag (direkt)
        _auftrag_col = {
            "Rechnung":     Rechnung.rechnung_zu_auftrag_id,
            "Lieferschein": Rechnung.lieferschein_zu_auftrag_id,
            "Proforma":     Rechnung.proforma_zu_auftrag_id,
        }[_dok]
        _quell_auftrag = db.query(Rechnung).filter(_auftrag_col == rechnung_id).first()
        rechnung._quell_auftrag_nr = _quell_auftrag.rechnungsnummer if _quell_auftrag else None

        # Wenn Auftrag direkt gefunden: Eltern-Angebot nachschlagen
        # (auftrag_zu_angebot_id steht auf dem Angebot-Dokument, nicht auf dem Auftrag)
        if _quell_auftrag and not rechnung._quell_angebot_nr:
            _angebot_via_auftrag = db.query(Rechnung).filter(
                Rechnung.auftrag_zu_angebot_id == _quell_auftrag.id,
                Rechnung.dokument_typ == "Angebot",
            ).first()
            rechnung._quell_angebot_nr = _angebot_via_auftrag.rechnungsnummer if _angebot_via_auftrag else None

        # Fallback für Rechnung aus Proforma: Auftrag/Angebot über Proforma-Kette
        if _dok == "Rechnung" and not rechnung._quell_auftrag_nr:
            _via_proforma = db.query(Rechnung).filter(
                Rechnung.rechnung_zu_proforma_id == rechnung_id,
                Rechnung.dokument_typ == "Proforma",
            ).first()
            if _via_proforma:
                _auftrag_via = db.query(Rechnung).filter(
                    Rechnung.proforma_zu_auftrag_id == _via_proforma.id,
                    Rechnung.dokument_typ == "Auftrag",
                ).first()
                if _auftrag_via:
                    rechnung._quell_auftrag_nr = _auftrag_via.rechnungsnummer
                    if not rechnung._quell_angebot_nr:
                        # auftrag_zu_angebot_id steht auf dem Angebot (FK → Auftrag), nicht auf dem Auftrag selbst
                        _angebot_via = db.query(Rechnung).filter(
                            Rechnung.auftrag_zu_angebot_id == _auftrag_via.id,
                            Rechnung.dokument_typ == "Angebot",
                        ).first()
                        rechnung._quell_angebot_nr = _angebot_via.rechnungsnummer if _angebot_via else None
                elif not rechnung._quell_angebot_nr and _via_proforma.proforma_zu_angebot_id:
                    _angebot_via = db.query(Rechnung).filter(
                        Rechnung.id == _via_proforma.proforma_zu_angebot_id,
                    ).first()
                    rechnung._quell_angebot_nr = _angebot_via.rechnungsnummer if _angebot_via else None

        # Fallback für Rechnung aus Lieferschein: Auftrag/Angebot über Lieferschein-Kette
        if _dok == "Rechnung" and not rechnung._quell_auftrag_nr:
            _via_ls = db.query(Rechnung).filter(
                Rechnung.lieferschein_zu_rechnung_id == rechnung_id,
                Rechnung.dokument_typ == "Lieferschein",
            ).first()
            if _via_ls:
                _auftrag_via_ls = db.query(Rechnung).filter(
                    Rechnung.lieferschein_zu_auftrag_id == _via_ls.id,
                    Rechnung.dokument_typ == "Auftrag",
                ).first()
                if _auftrag_via_ls:
                    rechnung._quell_auftrag_nr = _auftrag_via_ls.rechnungsnummer
                    if not rechnung._quell_angebot_nr:
                        _angebot_via = db.query(Rechnung).filter(
                            Rechnung.auftrag_zu_angebot_id == _auftrag_via_ls.id,
                            Rechnung.dokument_typ == "Angebot",
                        ).first()
                        rechnung._quell_angebot_nr = _angebot_via.rechnungsnummer if _angebot_via else None
                elif not rechnung._quell_angebot_nr:
                    # Lieferschein direkt aus Angebot (kein Auftrag dazwischen)
                    _angebot_via = db.query(Rechnung).filter(
                        Rechnung.lieferschein_zu_angebot_id == _via_ls.id,
                        Rechnung.dokument_typ == "Angebot",
                    ).first()
                    rechnung._quell_angebot_nr = _angebot_via.rechnungsnummer if _angebot_via else None


    # Auftrag: Eltern-Angebot über Rückwärts-FK suchen
    # (auftrag_zu_angebot_id steht auf dem Angebot, nicht auf dem Auftrag)
    if _dok == "Auftrag":
        _angebot_des_auftrags = db.query(Rechnung).filter(
            Rechnung.auftrag_zu_angebot_id == rechnung_id,
            Rechnung.dokument_typ == "Angebot",
        ).first()
        rechnung._quell_angebot_nr = _angebot_des_auftrags.rechnungsnummer if _angebot_des_auftrags else None

    # Lieferschein: Lieferadresse am Objekt hinterlegen (für PDF + Response)
    if rechnung.lieferadresse_id:
        from database.models import KundeLieferadresse
        rechnung._lieferadresse = db.query(KundeLieferadresse).filter(
            KundeLieferadresse.id == rechnung.lieferadresse_id
        ).first()

    ist_entwurf = rechnung.ist_entwurf
    _dok_typ = getattr(rechnung, "dokument_typ", "Rechnung") or "Rechnung"

    # Dokumente die kein Original-Archiv brauchen (beliebig oft druckbar, kein Kopie-Stempel)
    _kein_archiv = _dok_typ in ("Auftrag", "Angebot", "Proforma")

    # Gutschrift: erst ausgeben wenn Rückerstattung gebucht
    ist_gutschrift_pdf = _dok_typ == "Gutschrift"
    gutschrift_erstattet = ist_gutschrift_pdf and str(getattr(rechnung, "zahlungsstatus", "offen")) == "bezahlt"
    darf_archiviert = (
        not ist_entwurf
        and not _kein_archiv
        and (not ist_gutschrift_pdf or gutschrift_erstattet)
    )

    # Kopie: Original bereits gespeichert → gespeichertes PDF + Wasserzeichen zurückgeben
    if darf_archiviert and rechnung.original_pdf_pfad:
        kopie_bytes = lade_original_mit_kopie_stempel(APP_DATA_DIR, rechnung.original_pdf_pfad)
        if kopie_bytes:
            _dt_datei = _dok_typ
            _prefix = {
                "Gutschrift":   "Gutschrift",
                "Lieferschein": "Lieferschein",
            }.get(_dt_datei, "Rechnung")
            dateiname = f"{_prefix}_{rechnung.rechnungsnummer or rechnung_id}_Kopie.pdf"
            disposition = "attachment" if download else "inline"
            return Response(
                content=kopie_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'{disposition}; filename="{dateiname}"',
                    "Cache-Control": "no-store",
                },
            )
        # Fallback wenn Datei fehlt: frisch generieren (ohne Kopie-Stempel)

    # Netto- oder Bruttorechnung: B2B-Kunden (zugferd_aktiv) → Nettorechnung
    ist_netto = (
        rechnung.typ == "ausgang"
        and rechnung.kunde is not None
        and rechnung.kunde.zugferd_aktiv
    )

    # ZUGFeRD: automatisch wenn Kunde zugferd_aktiv – nur für echte Ausgangsrechnungen
    kunde_zugferd = (
        not ist_entwurf
        and ist_netto
        and _dok_typ == "Rechnung"
        and (unternehmen.steuernummer or unternehmen.ust_idnr)
    )
    if kunde_zugferd:
        try:
            pdf_bytes = generate_zugferd_pdf(rechnung, unt_dict)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("ZUGFeRD-Generierung fehlgeschlagen: %s", e, exc_info=True)
            kunde_zugferd = False
            pdf_bytes = generate_rechnung_pdf(rechnung, unt_dict, ist_kopie=False, ist_entwurf=ist_entwurf, ist_netto=ist_netto)
    else:
        vorlage_nr = vorlage if vorlage >= 0 else (unternehmen.pdf_vorlage if unternehmen else 0)
        if vorlage_nr == 1:
            pdf_bytes = generate_rechnung_pdf_vorlage1(rechnung, unt_dict, ist_kopie=False, ist_entwurf=ist_entwurf, ist_netto=ist_netto)
        else:
            pdf_bytes = generate_rechnung_pdf(rechnung, unt_dict, ist_kopie=False, ist_entwurf=ist_entwurf, ist_netto=ist_netto)

    # Original speichern (erstes echtes Drucken/Mailen)
    if darf_archiviert and not rechnung.original_pdf_pfad:
        rel_pfad = speichere_original_pdf(APP_DATA_DIR, rechnung.id, pdf_bytes)
        rechnung.original_pdf_pfad = rel_pfad
        rechnung.ausgegeben = True
        db.commit()

    _dt_datei = getattr(rechnung, "dokument_typ", "Rechnung") or "Rechnung"
    if kunde_zugferd:
        firma = (unt_dict.get("firmenname") or "").replace("/", "-")
        dateiname = f"{firma}_Invoice {rechnung.rechnungsnummer or rechnung_id}.pdf"
    else:
        _prefix = {
            "Gutschrift":   "Gutschrift",
            "Lieferschein": "Lieferschein",
            "Angebot":      "Angebot",
            "Proforma":     "Proforma",
            "Auftrag":      "Auftrag",
        }.get(_dt_datei, "Rechnung")
        dateiname = f"{_prefix}_{rechnung.rechnungsnummer or rechnung_id}.pdf"
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
    if getattr(rechnung, "dokument_typ", "Rechnung") != "Rechnung":
        raise HTTPException(status_code=400, detail="ZUGFeRD ist nur für Rechnungen verfügbar, nicht für Proforma, Angebote oder Lieferscheine.")
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
        "einleitungstext":         unternehmen.einleitungstext or "",
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
    ist_proforma = rechnung.dokument_typ == "Proforma"
    ist_angebot  = rechnung.dokument_typ == "Angebot"

    if not rechnung.ist_entwurf and not ist_proforma and not ist_angebot:
        raise HTTPException(status_code=409, detail="Nur Entwürfe können gelöscht werden.")

    if ist_proforma and rechnung.rechnung_zu_proforma_id:
        raise HTTPException(status_code=409, detail="Proforma wurde bereits abgerechnet und kann nicht gelöscht werden.")

    if ist_angebot and (
        rechnung.rechnung_zu_angebot_id
        or rechnung.lieferschein_zu_angebot_id
        or rechnung.proforma_zu_angebot_id
        or rechnung.auftrag_zu_angebot_id
    ):
        raise HTTPException(status_code=409, detail="Angebot kann nicht gelöscht werden, da bereits Dokumente daraus erstellt wurden.")
    ist_auftrag = rechnung.dokument_typ == "Auftrag"
    if ist_auftrag and (
        rechnung.rechnung_zu_auftrag_id
        or rechnung.lieferschein_zu_auftrag_id
        or rechnung.proforma_zu_auftrag_id
    ):
        raise HTTPException(status_code=409, detail="Auftrag kann nicht gelöscht werden, da bereits Dokumente daraus erstellt wurden.")
    # FK-Rückverweise zurücksetzen
    db.query(Rechnung).filter(Rechnung.lieferschein_zu_rechnung_id == rechnung_id).update(
        {"lieferschein_zu_rechnung_id": None}
    )
    db.query(Rechnung).filter(Rechnung.proforma_zu_angebot_id == rechnung_id).update(
        {"proforma_zu_angebot_id": None}
    )
    db.query(Rechnung).filter(Rechnung.auftrag_zu_angebot_id == rechnung_id).update(
        {"auftrag_zu_angebot_id": None}
    )
    # Auftrag-Rückverweis bereinigen und Status zurücksetzen wenn keine Dokumente mehr
    _auftrag_ref = db.query(Rechnung).filter(
        Rechnung.proforma_zu_auftrag_id == rechnung_id,
        Rechnung.dokument_typ == "Auftrag",
    ).first()
    def _hat_aktive_vorlage(auftrag_id: int) -> bool:
        from database.models import Rechnungsvorlage as _RV
        return bool(db.query(_RV).filter(
            _RV.auftrag_id == auftrag_id, _RV.aktiv == True  # noqa: E712
        ).first())

    if _auftrag_ref:
        _auftrag_ref.proforma_zu_auftrag_id = None
        if not _auftrag_ref.rechnung_zu_auftrag_id and not _auftrag_ref.lieferschein_zu_auftrag_id:
            _auftrag_ref.auftrag_status = "laufend" if _hat_aktive_vorlage(_auftrag_ref.id) else "offen"
    _auftrag_ref2 = db.query(Rechnung).filter(
        Rechnung.rechnung_zu_auftrag_id == rechnung_id,
        Rechnung.dokument_typ == "Auftrag",
    ).first()
    if _auftrag_ref2:
        _auftrag_ref2.rechnung_zu_auftrag_id = None
        if not _auftrag_ref2.proforma_zu_auftrag_id and not _auftrag_ref2.lieferschein_zu_auftrag_id:
            _auftrag_ref2.auftrag_status = "laufend" if _hat_aktive_vorlage(_auftrag_ref2.id) else "offen"
        elif _auftrag_ref2.auftrag_status == "rechnung_gestellt":
            _auftrag_ref2.auftrag_status = "laufend" if _hat_aktive_vorlage(_auftrag_ref2.id) else "in_bearbeitung"
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
    from database.models import Kategorie as _Kategorie
    skonto_art = "Ausgabe" if rechnung.typ == "ausgang" else "Einnahme"
    sk_netto = (skonto_betrag * 100 / (100 + ust_satz)).quantize(Decimal("0.01"), ROUND_HALF_UP) if ust_satz > 0 else skonto_betrag
    sk_ust = (skonto_betrag - sk_netto).quantize(Decimal("0.01"), ROUND_HALF_UP) if ust_satz > 0 else Decimal("0.00")
    sk_konto_skr03, sk_konto_skr04 = _skonto_konto(rechnung.typ, ust_satz)
    # Ausgangsrechnung-Skonto mindert Umsatzsteuer (1776/3806), nicht Vorsteuer (1575/1406)
    ust_art_konto = "Einnahme" if rechnung.typ == "ausgang" else "Ausgabe"
    sk_ust_skr03, sk_ust_skr04 = _ust_konto(ust_art_konto, ust_satz) if ust_satz > 0 else (None, None)
    kat_name = "Gewährte Skonti" if rechnung.typ == "ausgang" else "Erhaltene Skonti"
    kat = db.query(_Kategorie).filter(_Kategorie.name == kat_name).first()
    sk_vorsteuerabzug = (rechnung.typ == "eingang" and ust_satz > 0)
    sk = Journaleintrag(
        datum=data.datum,
        belegnr=_naechste_belegnr_journal(db, data.datum),
        beschreibung=f"Skonto {rechnung.rechnungsnummer}",
        kategorie_id=kat.id if kat else None,
        konto_skr03=sk_konto_skr03,
        konto_skr04=sk_konto_skr04,
        konto_ust_skr03=sk_ust_skr03,
        konto_ust_skr04=sk_ust_skr04,
        zahlungsart="Skonto",
        art=skonto_art,
        netto_betrag=sk_netto,
        ust_satz=ust_satz,
        ust_betrag=sk_ust,
        vorsteuer_betrag=_berechne_vorsteuer(sk_ust, sk_vorsteuerabzug, kat),
        brutto_betrag=skonto_betrag,
        vorsteuerabzug=sk_vorsteuerabzug,
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
                if pos.differenzbesteuerung:
                    if pos.ust_satz_25a:
                        s = int(pos.ust_satz_25a)
                    else:
                        # Fallback für Positionen ohne ust_satz_25a: aus Artikel ableiten
                        s = 19
                        if pos.artikel_id:
                            from database.models import Artikel as _ArtG
                            _ag = db.query(_ArtG).filter(_ArtG.id == pos.artikel_id).first()
                            if _ag and _ag.vk_netto and _ag.vk_netto > 0 and _ag.vk_brutto:
                                _ratio = _ag.vk_brutto / _ag.vk_netto
                                if abs(_ratio - Decimal("1.07")) < Decimal("0.015"):
                                    s = 7
                else:
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

    # §25a Marge vorberechnen (Brutto-Marge = VK_brutto − EK_netto_gesamt für §25a-Positionen)
    _marge_25a_gesamt = Decimal("0")
    for _pos in rechnung.positionen:
        if _pos.differenzbesteuerung:
            _ek = _pos.ek_netto_25a
            if _ek is None and _pos.artikel_id:
                # Fallback für Positionen vor Schema 50: EK direkt aus Artikel lesen
                from database.models import Artikel as _Artikel
                _art = db.query(_Artikel).filter(_Artikel.id == _pos.artikel_id).first()
                _ek = _art.ek_netto if _art else None
            if _ek is not None:
                _marge_25a_gesamt += (_pos.brutto - _ek) * _pos.menge
    _marge_25a_gesamt = _marge_25a_gesamt.quantize(Decimal("0.01"), ROUND_HALF_UP)

    def _erstelle_eintrag(
        kat_id: int | None, kat: "Kategorie | None", brutto: Decimal, beschr: str,
        g_satz: Decimal | None = None,
        g_ust_skr03: str | None = None,
        g_ust_skr04: str | None = None,
        marge_25a: Decimal | None = None,
    ) -> Journaleintrag:
        satz = g_satz if g_satz is not None else ust_satz
        ust03 = g_ust_skr03 if g_satz is not None else konto_ust_skr03
        ust04 = g_ust_skr04 if g_satz is not None else konto_ust_skr04
        if satz > 0:
            if marge_25a is not None:
                # §25a: USt nur auf Brutto-Marge, nicht auf vollen VK-Preis
                u = (marge_25a * satz / (100 + satz)).quantize(Decimal("0.01"), ROUND_HALF_UP)
                n = (brutto - u).quantize(Decimal("0.01"), ROUND_HALF_UP)
            else:
                n = (brutto * 100 / (100 + satz)).quantize(Decimal("0.01"), ROUND_HALF_UP)
                u = (brutto - n).quantize(Decimal("0.01"), ROUND_HALF_UP)
        else:
            n, u = brutto, Decimal("0.00")
        vst_abzug = (art == "Ausgabe" and satz > 0)
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
            vorsteuer_betrag=_berechne_vorsteuer(u, vst_abzug, kat),
            brutto_betrag=brutto,
            marge_25a_brutto=marge_25a,
            vorsteuerabzug=vst_abzug,
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
            eff_kat_id = kat_id or rechnung.kategorie_id
            kat_obj_g = db.query(Kategorie).filter(Kategorie.id == eff_kat_id).first() if eff_kat_id else None
            e = _erstelle_eintrag(eff_kat_id, kat_obj_g, anteil, beschreibung_gs, satz_d, g_ust03, g_ust04)
            db.add(e)
            if i == 0:
                erster_eintrag_gs = e

        if erster_eintrag_gs is None:
            # Fallback: keine Positionen – Rechnung.kategorie_id verwenden
            fb_kat_id = rechnung.kategorie_id
            fb_kat = db.query(Kategorie).filter(Kategorie.id == fb_kat_id).first() if fb_kat_id else None
            e = _erstelle_eintrag(fb_kat_id, fb_kat, betrag_neg, beschreibung_gs)
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
    marge_25a_arg = _marge_25a_gesamt if _marge_25a_gesamt > 0 else None
    for i, (g_satz, g_betrag, g_ust_skr03, g_ust_skr04) in enumerate(ust_gruppen):
        e = _erstelle_eintrag(kategorie_id, kat_obj, g_betrag, beschreibung, g_satz, g_ust_skr03, g_ust_skr04,
                              marge_25a=marge_25a_arg)
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
        if eintrag.brutto_betrag >= 0:
            storno_art = "Ausgabe" if eintrag.art == "Einnahme" else "Einnahme"
            s_netto  = eintrag.netto_betrag
            s_ust    = eintrag.ust_betrag
            s_brutto = eintrag.brutto_betrag
        else:
            # Negativer Originalbetrag (z. B. Gutschrift-Buchung): gleiche Art, positiver Betrag
            storno_art = eintrag.art
            s_netto  = -eintrag.netto_betrag
            s_ust    = -eintrag.ust_betrag
            s_brutto = -eintrag.brutto_betrag
        belegnr = _naechste_belegnr_journal(db, heute)
        gegenbuchung = Journaleintrag(
            datum=heute,
            belegnr=belegnr,
            beschreibung=f"STORNO {eintrag.belegnr}: {re_nr} – {data.grund.strip()}",
            kategorie_id=eintrag.kategorie_id,
            konto_skr03=eintrag.konto_skr03,
            konto_skr04=eintrag.konto_skr04,
            konto_ust_skr03=eintrag.konto_ust_skr03,
            konto_ust_skr04=eintrag.konto_ust_skr04,
            zahlungsart=eintrag.zahlungsart,
            art=storno_art,
            netto_betrag=s_netto,
            ust_satz=eintrag.ust_satz,
            ust_betrag=s_ust,
            vorsteuer_betrag=-eintrag.vorsteuer_betrag,
            brutto_betrag=s_brutto,
            marge_25a_brutto=eintrag.marge_25a_brutto,
            vorsteuerabzug=False,
            steuerbefreiung_grund=None,
            immutable=True,
        )
        gegenbuchung.signatur = signatur_journaleintrag(gegenbuchung)
        db.add(gegenbuchung)

    rechnung.storniert = True
    rechnung.storno_grund = data.grund.strip()
    rechnung.immutable = True
    # Verknüpfte Lieferscheine wieder auf "Nicht abgerechnet" setzen
    db.query(Rechnung).filter(Rechnung.lieferschein_zu_rechnung_id == rechnung_id).update(
        {"lieferschein_zu_rechnung_id": None}
    )
    db.commit()
    db.refresh(rechnung)
    return RechnungResponse.from_orm_extended(rechnung)


@router.post("/{rechnung_id}/forderungsausfall", response_model=RechnungResponse)
def forderungsausfall_buchen(rechnung_id: int, db: Session = Depends(get_db)):
    """Markiert eine offene/teilweise bezahlte Rechnung als uneinbringlich.
    Für USt-Pflichtige (nicht §19) wird automatisch eine §17-UStG-Korrekturbuchung erstellt."""
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    if rechnung.ist_entwurf:
        raise HTTPException(status_code=409, detail="Entwürfe können nicht ausgebucht werden.")
    if rechnung.storniert:
        raise HTTPException(status_code=409, detail="Stornierte Rechnungen können nicht ausgebucht werden.")
    if rechnung.zahlungsstatus == "bezahlt":
        raise HTTPException(status_code=409, detail="Vollständig bezahlte Rechnungen können nicht ausgebucht werden.")
    if rechnung.zahlungsstatus == "uneinbringlich":
        raise HTTPException(status_code=409, detail="Forderung ist bereits ausgebucht.")

    unternehmen = db.query(Unternehmen).first()
    ist_kleinunternehmer = unternehmen.ist_kleinunternehmer if unternehmen else False

    re_nr = rechnung.rechnungsnummer or f"#{rechnung.id}"
    heute = date.today()
    restbetrag = abs(rechnung.brutto_gesamt - rechnung.bezahlt_betrag)

    if not ist_kleinunternehmer and restbetrag > Decimal("0.004"):
        # USt-Anteil des Restbetrags proportional ermitteln
        Q = Decimal("0.01")
        if rechnung.brutto_gesamt > 0 and rechnung.ust_gesamt > 0:
            ust_anteil = (rechnung.ust_gesamt * restbetrag / rechnung.brutto_gesamt).quantize(Q, ROUND_HALF_UP)
        else:
            ust_anteil = Decimal("0.00")
        netto_anteil = (restbetrag - ust_anteil).quantize(Q, ROUND_HALF_UP)

        # Durchschnittlicher USt-Satz für Kontenzuordnung
        ust_satz_avg = Decimal("0")
        if netto_anteil > 0 and ust_anteil > 0:
            ust_satz_avg = (ust_anteil / netto_anteil * 100).quantize(Decimal("0.01"), ROUND_HALF_UP)

        kat_fa = db.query(Kategorie).filter(Kategorie.name == "Forderungsausfall").first()
        konto_ust_skr03, konto_ust_skr04 = _ust_konto("Einnahme", ust_satz_avg) if ust_satz_avg > 0 else (None, None)

        belegnr = _naechste_belegnr_journal(db, heute)
        eintrag = Journaleintrag(
            datum=heute,
            belegnr=belegnr,
            beschreibung=f"Forderungsausfall {re_nr} (§17 UStG)",
            kategorie_id=kat_fa.id if kat_fa else None,
            konto_skr03=kat_fa.konto_skr03 if kat_fa else None,
            konto_skr04=kat_fa.konto_skr04 if kat_fa else None,
            konto_ust_skr03=konto_ust_skr03,
            konto_ust_skr04=konto_ust_skr04,
            zahlungsart="Keine",
            art="Ausgabe",
            netto_betrag=netto_anteil,
            ust_satz=ust_satz_avg,
            ust_betrag=ust_anteil,
            brutto_betrag=restbetrag,
            vorsteuerabzug=False,
            vorsteuer_betrag=Decimal("0.00"),
            steuerbefreiung_grund=None,
            rechnung_id=rechnung.id,
            immutable=True,
        )
        eintrag.signatur = signatur_journaleintrag(eintrag)
        db.add(eintrag)

    rechnung.zahlungsstatus = "uneinbringlich"
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
        # pos.netto / pos.ust_betrag / pos.brutto sind Einzelpreise (per Unit).
        # Nur menge negieren – Einzelpreise bleiben positiv, damit die PDF-Gesamtspalte
        # (netto * menge) das richtige Vorzeichen trägt und Summen korrekt sind.
        menge_neg = -(pos.menge)

        neue_pos = Rechnungsposition(
            rechnung_id=gutschrift.id,
            artikel_id=pos.artikel_id,
            position_nr=nr_pos,
            beschreibung=pos.beschreibung,
            menge=menge_neg,
            einheit=pos.einheit,
            netto=pos.netto,
            ust_satz=pos.ust_satz,
            ust_betrag=pos.ust_betrag,
            brutto=pos.brutto,
            kategorie_id=pos.kategorie_id or original.kategorie_id,
            differenzbesteuerung=pos.differenzbesteuerung,
        )
        db.add(neue_pos)
        netto_sum += pos.netto * menge_neg
        ust_sum += pos.ust_betrag * menge_neg

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

    # PDF/A-Konvertierung: ZUGFeRD/XRechnung ist bereits PDF/A-3
    pdfa_pfad_rel: str | None = None
    if mime == "application/pdf":
        try:
            ergebnis = analysiere_datei(datei.filename or "", inhalt)
            if ergebnis.format in ("zugferd", "xrechnung"):
                # Eingebettetes XML → bereits normiertes PDF/A-3
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
    rechnung.beleg_id = beleg.id
    db.commit()
    db.refresh(beleg)

    # Konvertierung zu PDF/A (asynchron im Hintergrundthread, blockiert Antwort nicht)
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

    return BelegResponse.from_beleg(beleg)


@router.get("/{rechnung_id}/beleg")
def download_beleg(
    rechnung_id: int,
    version: str = Query("original", description="'original' oder 'pdfa'"),
    db: Session = Depends(get_db),
):
    """Angehängte Datei einer Rechnung herunterladen. Mit ?version=pdfa die PDF/A-Version."""
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung or not rechnung.beleg_id:
        raise HTTPException(status_code=404, detail="Kein Beleg vorhanden.")
    beleg = db.query(Beleg).filter(Beleg.id == rechnung.beleg_id).first()
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


# ---------------------------------------------------------------------------
# Lieferschein → Rechnung
# ---------------------------------------------------------------------------

class SammelrechnungCreate(BaseModel):
    lieferschein_ids: List[int]
    datum: date
    leistung_von: Optional[date] = None
    leistung_bis: Optional[date] = None
    faellig_am: Optional[date] = None
    notizen: Optional[str] = None


def _lieferschein_zu_rechnung_konvertieren(
    lieferscheine: list,
    datum: date,
    rechnungsnummer: str,
    leistung_von: Optional[date],
    leistung_bis: Optional[date],
    faellig_am: Optional[date],
    notizen: Optional[str],
    db: Session,
) -> Rechnung:
    """Erstellt eine Rechnung aus einem oder mehreren Lieferscheinen (Positionen kopieren)."""
    ls_nummern = ", ".join(ls.rechnungsnummer for ls in lieferscheine if ls.rechnungsnummer)
    merged_notizen = notizen or f"Lieferscheine: {ls_nummern}"

    rechnung = Rechnung(
        typ="ausgang",
        rechnungsnummer=rechnungsnummer,
        datum=datum,
        leistung_von=leistung_von,
        leistung_bis=leistung_bis,
        faellig_am=faellig_am,
        kunde_id=lieferscheine[0].kunde_id,
        partner_freitext=lieferscheine[0].partner_freitext,
        notizen=merged_notizen,
        dokument_typ="Rechnung",
        ist_entwurf=True,
        bezahlt=False,
        bezahlt_betrag=Decimal("0.00"),
        zahlungsstatus="offen",
        netto_gesamt=Decimal("0.00"),
        ust_gesamt=Decimal("0.00"),
        brutto_gesamt=Decimal("0.00"),
    )
    db.add(rechnung)
    db.flush()

    netto_sum = Decimal("0.00")
    ust_sum = Decimal("0.00")
    pos_nr = 1
    for ls in lieferscheine:
        for pos in ls.positionen:
            neue_pos = Rechnungsposition(
                rechnung_id=rechnung.id,
                artikel_id=pos.artikel_id,
                kategorie_id=pos.kategorie_id,
                position_nr=pos_nr,
                beschreibung=pos.beschreibung,
                menge=pos.menge,
                einheit=pos.einheit,
                netto=pos.netto,
                ust_satz=pos.ust_satz,
                ust_betrag=pos.ust_betrag,
                brutto=pos.brutto,
                differenzbesteuerung=pos.differenzbesteuerung,
                ek_netto_25a=pos.ek_netto_25a,
                ust_satz_25a=pos.ust_satz_25a,
            )
            db.add(neue_pos)
            netto_sum += pos.netto * pos.menge
            ust_sum += pos.ust_betrag * pos.menge
            pos_nr += 1

    Q = Decimal("0.01")
    rechnung.netto_gesamt = netto_sum.quantize(Q, ROUND_HALF_UP)
    rechnung.ust_gesamt = ust_sum.quantize(Q, ROUND_HALF_UP)
    rechnung.brutto_gesamt = (rechnung.netto_gesamt + rechnung.ust_gesamt).quantize(Q, ROUND_HALF_UP)

    for ls in lieferscheine:
        ls.lieferschein_zu_rechnung_id = rechnung.id

    db.commit()
    db.refresh(rechnung)
    return rechnung


def _naechste_proformanummer(datum: date, db: Session) -> str:
    nk = db.query(Nummernkreis).filter(Nummernkreis.typ == "proforma").first()
    if nk:
        if nk.reset_jaehrlich and nk.letztes_jahr and nk.letztes_jahr != datum.year:
            nk.naechste_nr = 1
        nk.letztes_jahr = datum.year
        nr = nk.naechste_nr
        nk.naechste_nr += 1
        return _belegnr_aus_format(nk.format, datum, nr)
    count = db.query(Rechnung).filter(Rechnung.dokument_typ == "Proforma").count()
    return f"PRF-{str(datum.year)[-2:]}{count + 1:04d}"


def _naechste_lieferscheinnummer(datum: date, db: Session) -> str:
    nk = db.query(Nummernkreis).filter(Nummernkreis.typ == "lieferschein").first()
    if nk:
        if nk.reset_jaehrlich and nk.letztes_jahr and nk.letztes_jahr != datum.year:
            nk.naechste_nr = 1
        nk.letztes_jahr = datum.year
        nr = nk.naechste_nr
        nk.naechste_nr += 1
        return _belegnr_aus_format(nk.format, datum, nr)
    count = db.query(Rechnung).filter(Rechnung.dokument_typ == "Lieferschein").count()
    return f"LS-{str(datum.year)[-2:]}{count + 1:04d}"


def _naechste_rechnungsnummer(datum: date, db: Session) -> str:
    nk = db.query(Nummernkreis).filter(Nummernkreis.typ == "rechnung_ausgang").first()
    if nk:
        if nk.reset_jaehrlich and nk.letztes_jahr and nk.letztes_jahr != datum.year:
            nk.naechste_nr = 1
        nk.letztes_jahr = datum.year
        nr = nk.naechste_nr
        nk.naechste_nr += 1
        return f"RE-{_belegnr_aus_format(nk.format, datum, nr)}"
    count = db.query(Rechnung).filter(Rechnung.typ == "ausgang", Rechnung.dokument_typ == "Rechnung").count()
    return f"RE-{str(datum.year)[-2:]}{count + 1:04d}"


@router.post("/{ls_id}/rechnung-erstellen", response_model=RechnungResponse, status_code=201)
def rechnung_aus_lieferschein(ls_id: int, db: Session = Depends(get_db)):
    """Erstellt eine Rechnung aus einem einzelnen Lieferschein."""
    ls = db.query(Rechnung).filter(Rechnung.id == ls_id, Rechnung.dokument_typ == "Lieferschein").first()
    if not ls:
        raise HTTPException(status_code=404, detail="Lieferschein nicht gefunden.")
    if ls.lieferschein_zu_rechnung_id:
        raise HTTPException(status_code=409, detail="Lieferschein wurde bereits abgerechnet.")
    rechnungsnummer = _naechste_rechnungsnummer(date.today(), db)
    rechnung = _lieferschein_zu_rechnung_konvertieren(
        lieferscheine=[ls],
        datum=date.today(),
        rechnungsnummer=rechnungsnummer,
        leistung_von=ls.leistung_von,
        leistung_bis=ls.leistung_bis,
        faellig_am=None,
        notizen=None,
        db=db,
    )
    return RechnungResponse.from_orm_extended(rechnung)


@router.post("/{rechnung_id}/lieferschein-erstellen", response_model=RechnungResponse, status_code=201)
def lieferschein_aus_rechnung(rechnung_id: int, db: Session = Depends(get_db)):
    """Erstellt einen Lieferschein aus einer bestehenden Ausgangsrechnung (Vorkasse-Workflow)."""
    r = db.query(Rechnung).filter(
        Rechnung.id == rechnung_id,
        Rechnung.typ == "ausgang",
        Rechnung.dokument_typ == "Rechnung",
        Rechnung.storniert == False,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    bereits = db.query(Rechnung).filter(
        Rechnung.lieferschein_zu_rechnung_id == rechnung_id,
        Rechnung.dokument_typ == "Lieferschein",
        Rechnung.storniert == False,
    ).first()
    if bereits:
        raise HTTPException(status_code=409, detail="Zu dieser Rechnung existiert bereits ein Lieferschein.")

    ls_nr = _naechste_lieferscheinnummer(date.today(), db)
    ls = Rechnung(
        typ="ausgang",
        rechnungsnummer=ls_nr,
        datum=date.today(),
        kunde_id=r.kunde_id,
        partner_freitext=r.partner_freitext,
        notizen=f"Zu Rechnung {r.rechnungsnummer}" if r.rechnungsnummer else None,
        dokument_typ="Lieferschein",
        lieferschein_zu_rechnung_id=rechnung_id,
        ist_entwurf=False,
        bezahlt=False,
        bezahlt_betrag=Decimal("0.00"),
        zahlungsstatus="offen",
        netto_gesamt=Decimal("0.00"),
        ust_gesamt=Decimal("0.00"),
        brutto_gesamt=Decimal("0.00"),
    )
    db.add(ls)
    db.flush()

    for nr, pos in enumerate(r.positionen, start=1):
        db.add(Rechnungsposition(
            rechnung_id=ls.id,
            artikel_id=pos.artikel_id,
            position_nr=nr,
            beschreibung=pos.beschreibung,
            menge=pos.menge,
            einheit=pos.einheit,
            netto=Decimal("0.00"),
            ust_satz=Decimal("0.00"),
            ust_betrag=Decimal("0.00"),
            brutto=Decimal("0.00"),
        ))

    db.commit()
    db.refresh(ls)
    return RechnungResponse.from_orm_extended(ls)


# ---------------------------------------------------------------------------
# Angebot → Lieferschein
# ---------------------------------------------------------------------------

@router.post("/{angebot_id}/lieferschein-aus-angebot", response_model=RechnungResponse, status_code=201)
def lieferschein_aus_angebot(angebot_id: int, db: Session = Depends(get_db)):
    """Erstellt einen Lieferschein aus einem Angebot (Positionen ohne Preise übernommen)."""
    angebot = db.query(Rechnung).filter(
        Rechnung.id == angebot_id, Rechnung.dokument_typ == "Angebot"
    ).first()
    if not angebot:
        raise HTTPException(status_code=404, detail="Angebot nicht gefunden.")

    ls_nr = _naechste_lieferscheinnummer(date.today(), db)
    ls = Rechnung(
        typ="ausgang",
        rechnungsnummer=ls_nr,
        datum=date.today(),
        kunde_id=angebot.kunde_id,
        partner_freitext=angebot.partner_freitext,
        notizen=f"Zu Angebot {angebot.rechnungsnummer}" if angebot.rechnungsnummer else None,
        dokument_typ="Lieferschein",
        ist_entwurf=False,
        bezahlt=False,
        bezahlt_betrag=Decimal("0.00"),
        zahlungsstatus="offen",
        netto_gesamt=Decimal("0.00"),
        ust_gesamt=Decimal("0.00"),
        brutto_gesamt=Decimal("0.00"),
    )
    db.add(ls)
    db.flush()

    for nr, pos in enumerate(angebot.positionen, start=1):
        db.add(Rechnungsposition(
            rechnung_id=ls.id,
            artikel_id=pos.artikel_id,
            position_nr=nr,
            beschreibung=pos.beschreibung,
            menge=pos.menge,
            einheit=pos.einheit,
            netto=Decimal("0.00"),
            ust_satz=Decimal("0.00"),
            ust_betrag=Decimal("0.00"),
            brutto=Decimal("0.00"),
        ))

    angebot.lieferschein_zu_angebot_id = ls.id
    db.commit()
    db.refresh(ls)
    return RechnungResponse.from_orm_extended(ls)


# ---------------------------------------------------------------------------
# Angebot → Rechnung
# ---------------------------------------------------------------------------

class AngebotStatusUpdate(BaseModel):
    status: str  # offen | akzeptiert | abgelehnt | abgelaufen


@router.post("/{angebot_id}/rechnung-aus-angebot", response_model=RechnungResponse, status_code=201)
def rechnung_aus_angebot(angebot_id: int, db: Session = Depends(get_db)):
    """Konvertiert ein Angebot in eine Ausgangsrechnung (Positionen werden übernommen)."""
    angebot = db.query(Rechnung).filter(
        Rechnung.id == angebot_id, Rechnung.dokument_typ == "Angebot"
    ).first()
    if not angebot:
        raise HTTPException(status_code=404, detail="Angebot nicht gefunden.")
    if angebot.rechnung_zu_angebot_id:
        raise HTTPException(status_code=409, detail="Aus diesem Angebot wurde bereits eine Rechnung erstellt.")

    heute = date.today()
    rechnungsnummer = _naechste_rechnungsnummer(heute, db)
    unternehmen = db.query(Unternehmen).first()
    zahlungsziel = getattr(unternehmen, "standard_zahlungsziel", 14) or 14
    from datetime import timedelta
    faellig_am = heute + timedelta(days=int(zahlungsziel))

    rechnung = Rechnung(
        typ="ausgang",
        rechnungsnummer=rechnungsnummer,
        datum=heute,
        faellig_am=faellig_am,
        leistung_von=angebot.leistung_von,
        leistung_bis=angebot.leistung_bis,
        kunde_id=angebot.kunde_id,
        partner_freitext=angebot.partner_freitext,
        notizen=angebot.notizen,
        ist_entwurf=True,
        dokument_typ="Rechnung",
        bezahlt=False,
        bezahlt_betrag=Decimal("0.00"),
        zahlungsstatus="offen",
        netto_gesamt=angebot.netto_gesamt,
        ust_gesamt=angebot.ust_gesamt,
        brutto_gesamt=angebot.brutto_gesamt,
    )
    db.add(rechnung)
    db.flush()

    for pos in angebot.positionen:
        neue_pos = Rechnungsposition(
            rechnung_id=rechnung.id,
            position_nr=pos.position_nr,
            beschreibung=pos.beschreibung,
            menge=pos.menge,
            einheit=pos.einheit,
            netto=pos.netto,
            ust_satz=pos.ust_satz,
            ust_betrag=pos.ust_betrag,
            brutto=pos.brutto,
            artikel_id=pos.artikel_id,
            kategorie_id=pos.kategorie_id,
        )
        db.add(neue_pos)

    angebot.rechnung_zu_angebot_id = rechnung.id
    angebot.angebot_status = "akzeptiert"
    db.commit()
    db.refresh(rechnung)
    return RechnungResponse.from_orm_extended(rechnung)


# ---------------------------------------------------------------------------
# Angebot → Proforma
# ---------------------------------------------------------------------------

@router.post("/{angebot_id}/proforma-aus-angebot", response_model=RechnungResponse, status_code=201)
def proforma_aus_angebot(angebot_id: int, db: Session = Depends(get_db)):
    """Erstellt eine Proforma-Rechnung aus einem Angebot (Positionen werden übernommen)."""
    angebot = db.query(Rechnung).filter(
        Rechnung.id == angebot_id, Rechnung.dokument_typ == "Angebot"
    ).first()
    if not angebot:
        raise HTTPException(status_code=404, detail="Angebot nicht gefunden.")
    if angebot.proforma_zu_angebot_id:
        raise HTTPException(status_code=409, detail="Aus diesem Angebot wurde bereits eine Proforma-Rechnung erstellt.")

    heute = date.today()
    proforma_nr = _naechste_proformanummer(heute, db)

    _unt = db.query(Unternehmen).first()
    _zt = int(getattr(_unt, "standard_zahlungsziel", 14) or 14) if _unt else 14
    from datetime import timedelta as _td
    _faellig = heute + _td(days=_zt)

    proforma = Rechnung(
        typ="ausgang",
        rechnungsnummer=proforma_nr,
        datum=heute,
        faellig_am=_faellig,
        leistung_von=angebot.leistung_von,
        leistung_bis=angebot.leistung_bis,
        kunde_id=angebot.kunde_id,
        partner_freitext=angebot.partner_freitext,
        notizen=angebot.notizen,
        ist_entwurf=False,
        dokument_typ="Proforma",
        bezahlt=False,
        bezahlt_betrag=Decimal("0.00"),
        zahlungsstatus="offen",
        netto_gesamt=angebot.netto_gesamt,
        ust_gesamt=angebot.ust_gesamt,
        brutto_gesamt=angebot.brutto_gesamt,
    )
    db.add(proforma)
    db.flush()

    for pos in angebot.positionen:
        db.add(Rechnungsposition(
            rechnung_id=proforma.id,
            position_nr=pos.position_nr,
            beschreibung=pos.beschreibung,
            menge=pos.menge,
            einheit=pos.einheit,
            netto=pos.netto,
            ust_satz=pos.ust_satz,
            ust_betrag=pos.ust_betrag,
            brutto=pos.brutto,
            artikel_id=pos.artikel_id,
            kategorie_id=pos.kategorie_id,
        ))

    angebot.proforma_zu_angebot_id = proforma.id
    db.commit()
    db.refresh(proforma)
    return RechnungResponse.from_orm_extended(proforma)


# ---------------------------------------------------------------------------
# Proforma → Rechnung
# ---------------------------------------------------------------------------

class ZahlungEingegangen(BaseModel):
    zahlungsart: str   # Bar|Karte|Bank|PayPal
    bezahlt_am: date


@router.post("/{proforma_id}/rechnung-aus-proforma", response_model=RechnungResponse, status_code=201)
def rechnung_aus_proforma(proforma_id: int, zahlung: ZahlungEingegangen, db: Session = Depends(get_db)):
    """Konvertiert eine Proforma-Rechnung in eine echte Ausgangsrechnung und bucht den Zahlungseingang."""
    proforma = db.query(Rechnung).filter(
        Rechnung.id == proforma_id, Rechnung.dokument_typ == "Proforma"
    ).first()
    if not proforma:
        raise HTTPException(status_code=404, detail="Proforma-Rechnung nicht gefunden.")
    if proforma.rechnung_zu_proforma_id:
        raise HTTPException(status_code=409, detail="Aus dieser Proforma wurde bereits eine Rechnung erstellt.")

    heute = date.today()
    rechnungsnummer = _naechste_rechnungsnummer(heute, db)

    rechnung = Rechnung(
        typ="ausgang",
        rechnungsnummer=rechnungsnummer,
        datum=heute,
        faellig_am=zahlung.bezahlt_am,
        leistung_von=proforma.leistung_von,
        leistung_bis=proforma.leistung_bis,
        kunde_id=proforma.kunde_id,
        partner_freitext=proforma.partner_freitext,
        notizen=proforma.notizen,
        ist_entwurf=True,
        dokument_typ="Rechnung",
        bezahlt=False,
        bezahlt_betrag=Decimal("0.00"),
        zahlungsstatus="offen",
        netto_gesamt=proforma.netto_gesamt,
        ust_gesamt=proforma.ust_gesamt,
        brutto_gesamt=proforma.brutto_gesamt,
    )
    db.add(rechnung)
    db.flush()

    for pos in proforma.positionen:
        db.add(Rechnungsposition(
            rechnung_id=rechnung.id,
            position_nr=pos.position_nr,
            beschreibung=pos.beschreibung,
            menge=pos.menge,
            einheit=pos.einheit,
            netto=pos.netto,
            ust_satz=pos.ust_satz,
            ust_betrag=pos.ust_betrag,
            brutto=pos.brutto,
            artikel_id=pos.artikel_id,
            kategorie_id=pos.kategorie_id,
        ))
    db.flush()

    # Journaleinträge anlegen (je USt-Gruppe wie beim kassieren-Endpoint)
    unternehmen = db.query(Unternehmen).first()
    ist_kl = bool(unternehmen and unternehmen.ist_kleinunternehmer)
    partner = _partner_name(proforma)
    beschreibung = f"Zahlung {rechnungsnummer}: {partner}"
    steuerbefreiung = "§19 UStG" if ist_kl else None
    brutto = rechnung.brutto_gesamt

    if ist_kl or not rechnung.positionen:
        ust_gruppen: list[tuple[Decimal, Decimal, str | None, str | None]] = [
            (Decimal("0"), brutto, None, None)
        ]
    else:
        gruppen_brutto: dict[int, Decimal] = {}
        for pos in rechnung.positionen:
            s = int(pos.ust_satz)
            gruppen_brutto[s] = gruppen_brutto.get(s, Decimal("0")) + pos.brutto
        gesamt_pos_brutto = sum(gruppen_brutto.values())
        rest_g = brutto
        ust_gruppen = []
        for i, satz in enumerate(sorted(gruppen_brutto.keys())):
            satz_d = Decimal(str(satz))
            g_ust_skr03, g_ust_skr04 = _ust_konto("Einnahme", satz_d) if satz > 0 else (None, None)
            if i == len(gruppen_brutto) - 1:
                g_betrag = rest_g
            else:
                g_betrag = (brutto * gruppen_brutto[satz] / gesamt_pos_brutto).quantize(Decimal("0.01"), ROUND_HALF_UP)
                rest_g -= g_betrag
            ust_gruppen.append((satz_d, g_betrag, g_ust_skr03, g_ust_skr04))

    for satz_d, g_betrag, g_ust_skr03, g_ust_skr04 in ust_gruppen:
        if satz_d > 0:
            n = (g_betrag * 100 / (100 + satz_d)).quantize(Decimal("0.01"), ROUND_HALF_UP)
            u = (g_betrag - n).quantize(Decimal("0.01"), ROUND_HALF_UP)
        else:
            n, u = g_betrag, Decimal("0.00")
        e = Journaleintrag(
            datum=zahlung.bezahlt_am,
            belegnr=_naechste_belegnr_journal(db, zahlung.bezahlt_am),
            beschreibung=beschreibung,
            zahlungsart=zahlung.zahlungsart,
            art="Einnahme",
            netto_betrag=n,
            ust_satz=satz_d,
            ust_betrag=u,
            vorsteuer_betrag=Decimal("0.00"),
            brutto_betrag=g_betrag,
            vorsteuerabzug=False,
            steuerbefreiung_grund=steuerbefreiung,
            rechnung_id=rechnung.id,
            kunde_id=proforma.kunde_id,
            konto_ust_skr03=g_ust_skr03,
            konto_ust_skr04=g_ust_skr04,
            immutable=True,
        )
        e.signatur = signatur_journaleintrag(e)
        db.add(e)
    db.flush()

    proforma.rechnung_zu_proforma_id = rechnung.id
    proforma.zahlungsstatus = "bezahlt"
    db.flush()
    _aktualisiere_zahlungsstatus(rechnung)
    db.commit()
    db.refresh(rechnung)
    return RechnungResponse.from_orm_extended(rechnung)


@router.patch("/{angebot_id}/angebot-status", response_model=RechnungResponse)
def angebot_status_setzen(angebot_id: int, data: AngebotStatusUpdate, db: Session = Depends(get_db)):
    """Ändert den Status eines Angebots."""
    erlaubt = {"offen", "akzeptiert", "abgelehnt", "abgelaufen"}
    if data.status not in erlaubt:
        raise HTTPException(status_code=422, detail=f"Status muss einer von {erlaubt} sein.")
    angebot = db.query(Rechnung).filter(
        Rechnung.id == angebot_id, Rechnung.dokument_typ == "Angebot"
    ).first()
    if not angebot:
        raise HTTPException(status_code=404, detail="Angebot nicht gefunden.")
    angebot.angebot_status = data.status
    db.commit()
    db.refresh(angebot)
    return RechnungResponse.from_orm_extended(angebot)


# ---------------------------------------------------------------------------
# Aufträge
# ---------------------------------------------------------------------------

def _naechste_auftragsnummer(datum: date, db: Session) -> str:
    nk = db.query(Nummernkreis).filter(Nummernkreis.typ == "auftrag").first()
    if nk:
        if nk.reset_jaehrlich and nk.letztes_jahr and nk.letztes_jahr != datum.year:
            nk.naechste_nr = 1
        nk.letztes_jahr = datum.year
        nr = nk.naechste_nr
        nk.naechste_nr += 1
        return _belegnr_aus_format(nk.format, datum, nr)
    count = db.query(Rechnung).filter(Rechnung.dokument_typ == "Auftrag").count()
    return f"AU-{str(datum.year)[-2:]}{count + 1:04d}"


def _kopiere_positionen(quell: "Rechnung", ziel: "Rechnung", db: Session) -> None:
    """Kopiert Positionen von einem Dokument zum anderen."""
    for pos in quell.positionen:
        neue_pos = Rechnungsposition(
            rechnung_id=ziel.id,
            position_nr=pos.position_nr,
            beschreibung=pos.beschreibung,
            menge=pos.menge,
            einheit=pos.einheit,
            netto=pos.netto,
            rabatt_prozent=pos.rabatt_prozent,
            ust_satz=pos.ust_satz,
            ust_betrag=pos.ust_betrag,
            brutto=pos.brutto,
            artikel_id=pos.artikel_id,
            kategorie_id=pos.kategorie_id,
            differenzbesteuerung=pos.differenzbesteuerung,
            ek_netto_25a=pos.ek_netto_25a,
            ust_satz_25a=pos.ust_satz_25a,
        )
        db.add(neue_pos)


@router.post("/{angebot_id}/auftrag-aus-angebot", response_model=RechnungResponse, status_code=201)
def auftrag_aus_angebot(angebot_id: int, db: Session = Depends(get_db)):
    """Erstellt einen Auftrag aus einem Angebot (Positionen werden übernommen)."""
    angebot = db.query(Rechnung).filter(
        Rechnung.id == angebot_id, Rechnung.dokument_typ == "Angebot"
    ).first()
    if not angebot:
        raise HTTPException(status_code=404, detail="Angebot nicht gefunden.")
    if angebot.auftrag_zu_angebot_id:
        _vorh = db.query(Rechnung).filter(Rechnung.id == angebot.auftrag_zu_angebot_id).first()
        if _vorh:
            raise HTTPException(status_code=409, detail="Aus diesem Angebot wurde bereits ein Auftrag erstellt.")
        angebot.auftrag_zu_angebot_id = None  # verwaister FK bereinigen

    heute = date.today()
    auftragsnummer = _naechste_auftragsnummer(heute, db)

    auftrag = Rechnung(
        typ="ausgang",
        rechnungsnummer=auftragsnummer,
        datum=heute,
        leistung_von=angebot.leistung_von,
        leistung_bis=angebot.leistung_bis,
        kunde_id=angebot.kunde_id,
        partner_freitext=angebot.partner_freitext,
        notizen=angebot.notizen,
        ist_entwurf=False,
        dokument_typ="Auftrag",
        auftrag_status="offen",
        netto_gesamt=angebot.netto_gesamt,
        ust_gesamt=angebot.ust_gesamt,
        brutto_gesamt=angebot.brutto_gesamt,
        skonto_prozent=angebot.skonto_prozent,
        skonto_tage=angebot.skonto_tage,
        dokumentenpaket_id=angebot.dokumentenpaket_id,
    )
    db.add(auftrag)
    db.flush()
    _kopiere_positionen(angebot, auftrag, db)
    angebot.auftrag_zu_angebot_id = auftrag.id
    angebot.angebot_status = "akzeptiert"
    db.commit()
    db.refresh(auftrag)
    return RechnungResponse.from_orm_extended(auftrag)


@router.post("/{auftrag_id}/rechnung-aus-auftrag", response_model=RechnungResponse, status_code=201)
def rechnung_aus_auftrag(auftrag_id: int, db: Session = Depends(get_db)):
    """Erstellt eine Ausgangsrechnung aus einem Auftrag."""
    auftrag = db.query(Rechnung).filter(
        Rechnung.id == auftrag_id, Rechnung.dokument_typ == "Auftrag"
    ).first()
    if not auftrag:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden.")
    if auftrag.auftrag_status in ("storniert", "in_bearbeitung", "rechnung_gestellt", "abgeschlossen"):
        raise HTTPException(status_code=409, detail="Dokumente können nur für Aufträge mit Status 'offen' erstellt werden.")
    if auftrag.rechnung_zu_auftrag_id:
        raise HTTPException(status_code=409, detail="Aus diesem Auftrag wurde bereits eine Rechnung erstellt.")

    heute = date.today()
    rechnungsnummer = _naechste_rechnungsnummer(heute, db)
    unternehmen = db.query(Unternehmen).first()
    zahlungsziel = getattr(unternehmen, "standard_zahlungsziel", 14) or 14
    from datetime import timedelta
    faellig_am = heute + timedelta(days=int(zahlungsziel))

    rechnung = Rechnung(
        typ="ausgang",
        rechnungsnummer=rechnungsnummer,
        datum=heute,
        faellig_am=faellig_am,
        leistung_von=auftrag.leistung_von,
        leistung_bis=auftrag.leistung_bis,
        kunde_id=auftrag.kunde_id,
        partner_freitext=auftrag.partner_freitext,
        notizen=auftrag.notizen,
        ist_entwurf=True,
        dokument_typ="Rechnung",
        bezahlt=False,
        bezahlt_betrag=Decimal("0.00"),
        zahlungsstatus="offen",
        netto_gesamt=auftrag.netto_gesamt,
        ust_gesamt=auftrag.ust_gesamt,
        brutto_gesamt=auftrag.brutto_gesamt,
        skonto_prozent=auftrag.skonto_prozent,
        skonto_tage=auftrag.skonto_tage,
    )
    db.add(rechnung)
    db.flush()
    _kopiere_positionen(auftrag, rechnung, db)
    auftrag.rechnung_zu_auftrag_id = rechnung.id
    if auftrag.auftrag_status not in ("abgeschlossen", "storniert"):
        auftrag.auftrag_status = "in_bearbeitung"
    db.commit()
    db.refresh(rechnung)
    return RechnungResponse.from_orm_extended(rechnung)


@router.post("/{auftrag_id}/lieferschein-aus-auftrag", response_model=RechnungResponse, status_code=201)
def lieferschein_aus_auftrag(auftrag_id: int, db: Session = Depends(get_db)):
    """Erstellt einen Lieferschein aus einem Auftrag."""
    auftrag = db.query(Rechnung).filter(
        Rechnung.id == auftrag_id, Rechnung.dokument_typ == "Auftrag"
    ).first()
    if not auftrag:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden.")
    if auftrag.auftrag_status in ("storniert", "in_bearbeitung", "rechnung_gestellt", "abgeschlossen"):
        raise HTTPException(status_code=409, detail="Dokumente können nur für Aufträge mit Status 'offen' erstellt werden.")
    if auftrag.lieferschein_zu_auftrag_id:
        raise HTTPException(status_code=409, detail="Aus diesem Auftrag wurde bereits ein Lieferschein erstellt.")

    heute = date.today()
    nk = db.query(Nummernkreis).filter(Nummernkreis.typ == "lieferschein").first()
    if nk:
        if nk.reset_jaehrlich and nk.letztes_jahr and nk.letztes_jahr != heute.year:
            nk.naechste_nr = 1
        nk.letztes_jahr = heute.year
        nr = nk.naechste_nr
        nk.naechste_nr += 1
        ls_nr = _belegnr_aus_format(nk.format, heute, nr)
    else:
        count = db.query(Rechnung).filter(Rechnung.dokument_typ == "Lieferschein").count()
        ls_nr = f"LS-{str(heute.year)[-2:]}{count + 1:04d}"

    lieferschein = Rechnung(
        typ="ausgang",
        rechnungsnummer=ls_nr,
        datum=heute,
        leistung_von=auftrag.leistung_von,
        leistung_bis=auftrag.leistung_bis,
        kunde_id=auftrag.kunde_id,
        partner_freitext=auftrag.partner_freitext,
        notizen=auftrag.notizen,
        ist_entwurf=False,
        dokument_typ="Lieferschein",
        netto_gesamt=auftrag.netto_gesamt,
        ust_gesamt=auftrag.ust_gesamt,
        brutto_gesamt=auftrag.brutto_gesamt,
    )
    db.add(lieferschein)
    db.flush()
    _kopiere_positionen(auftrag, lieferschein, db)
    auftrag.lieferschein_zu_auftrag_id = lieferschein.id
    if auftrag.auftrag_status == "offen":
        auftrag.auftrag_status = "in_bearbeitung"
    db.commit()
    db.refresh(lieferschein)
    return RechnungResponse.from_orm_extended(lieferschein)


@router.post("/{auftrag_id}/proforma-aus-auftrag", response_model=RechnungResponse, status_code=201)
def proforma_aus_auftrag(auftrag_id: int, db: Session = Depends(get_db)):
    """Erstellt eine Proforma-Rechnung aus einem Auftrag."""
    auftrag = db.query(Rechnung).filter(
        Rechnung.id == auftrag_id, Rechnung.dokument_typ == "Auftrag"
    ).first()
    if not auftrag:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden.")
    if auftrag.auftrag_status in ("storniert", "in_bearbeitung", "rechnung_gestellt", "abgeschlossen"):
        raise HTTPException(status_code=409, detail="Dokumente können nur für Aufträge mit Status 'offen' erstellt werden.")
    if auftrag.proforma_zu_auftrag_id:
        raise HTTPException(status_code=409, detail="Aus diesem Auftrag wurde bereits eine Proforma erstellt.")

    heute = date.today()
    nk = db.query(Nummernkreis).filter(Nummernkreis.typ == "proforma").first()
    if nk:
        if nk.reset_jaehrlich and nk.letztes_jahr and nk.letztes_jahr != heute.year:
            nk.naechste_nr = 1
        nk.letztes_jahr = heute.year
        nr = nk.naechste_nr
        nk.naechste_nr += 1
        prf_nr = _belegnr_aus_format(nk.format, heute, nr)
    else:
        count = db.query(Rechnung).filter(Rechnung.dokument_typ == "Proforma").count()
        prf_nr = f"PRF-{str(heute.year)[-2:]}{count + 1:04d}"

    proforma = Rechnung(
        typ="ausgang",
        rechnungsnummer=prf_nr,
        datum=heute,
        leistung_von=auftrag.leistung_von,
        leistung_bis=auftrag.leistung_bis,
        kunde_id=auftrag.kunde_id,
        partner_freitext=auftrag.partner_freitext,
        notizen=auftrag.notizen,
        ist_entwurf=False,
        dokument_typ="Proforma",
        netto_gesamt=auftrag.netto_gesamt,
        ust_gesamt=auftrag.ust_gesamt,
        brutto_gesamt=auftrag.brutto_gesamt,
    )
    db.add(proforma)
    db.flush()
    _kopiere_positionen(auftrag, proforma, db)
    auftrag.proforma_zu_auftrag_id = proforma.id
    if auftrag.auftrag_status == "offen":
        auftrag.auftrag_status = "in_bearbeitung"
    db.commit()
    db.refresh(proforma)
    return RechnungResponse.from_orm_extended(proforma)


class AuftragStatusUpdate(BaseModel):
    status: str  # offen | in_bearbeitung | abgeschlossen | storniert


@router.post("/{auftrag_id}/auftrag-status", response_model=RechnungResponse)
def auftrag_status_setzen(auftrag_id: int, data: AuftragStatusUpdate, db: Session = Depends(get_db)):
    erlaubt = {"offen", "in_bearbeitung", "laufend", "rechnung_gestellt", "abgeschlossen", "storniert"}
    if data.status not in erlaubt:
        raise HTTPException(status_code=422, detail=f"Status muss einer von {erlaubt} sein.")
    auftrag = db.query(Rechnung).filter(
        Rechnung.id == auftrag_id, Rechnung.dokument_typ == "Auftrag"
    ).first()
    if not auftrag:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden.")
    auftrag.auftrag_status = data.status
    db.commit()
    db.refresh(auftrag)
    return RechnungResponse.from_orm_extended(auftrag)




@router.post("/sammelrechnung", response_model=RechnungResponse, status_code=201)
def sammelrechnung_erstellen(data: SammelrechnungCreate, db: Session = Depends(get_db)):
    """Erstellt eine Sammelrechnung aus mehreren Lieferscheinen."""
    if not data.lieferschein_ids:
        raise HTTPException(status_code=422, detail="Mindestens ein Lieferschein erforderlich.")
    lieferscheine = db.query(Rechnung).filter(
        Rechnung.id.in_(data.lieferschein_ids),
        Rechnung.dokument_typ == "Lieferschein",
    ).all()
    if len(lieferscheine) != len(data.lieferschein_ids):
        raise HTTPException(status_code=404, detail="Mindestens ein Lieferschein nicht gefunden.")
    bereits_abgerechnet = [ls.rechnungsnummer for ls in lieferscheine if ls.lieferschein_zu_rechnung_id]
    if bereits_abgerechnet:
        raise HTTPException(status_code=409, detail=f"Bereits abgerechnet: {', '.join(str(x) for x in bereits_abgerechnet)}")
    kunden = {ls.kunde_id for ls in lieferscheine}
    if len(kunden) > 1:
        raise HTTPException(status_code=422, detail="Sammelrechnung nur für Lieferscheine desselben Kunden möglich.")
    rechnungsnummer = _naechste_rechnungsnummer(data.datum, db)
    rechnung = _lieferschein_zu_rechnung_konvertieren(
        lieferscheine=lieferscheine,
        datum=data.datum,
        rechnungsnummer=rechnungsnummer,
        leistung_von=data.leistung_von,
        leistung_bis=data.leistung_bis,
        faellig_am=data.faellig_am,
        notizen=data.notizen,
        db=db,
    )
    return RechnungResponse.from_orm_extended(rechnung)
