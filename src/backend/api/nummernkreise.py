"""
API-Endpunkte für Nummernkreise (Belegnummern-Konfiguration).
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError as _IntegrityError
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Nummernkreis, Rechnung
from utils.belegnummer import belegnr_aus_format as _belegnr_aus_format
from .schemas import NummernkreisUpdate, NummernkreisResponse


def naechste_nummer(typ: str, db: Session, datum: date | None = None) -> str | None:
    """Generiert die nächste Nummer für den angegebenen Nummernkreis-Typ.
    Inkrementiert naechste_nr in-memory; der Aufrufer muss committen.

    datum: Bezugsdatum für den Jahres-Rollover-Reset und die YYYY/YY/MM/TT-Platzhalter -
    Default heute. Für rückdatierte Belege (z.B. eine Eingangsrechnung vom Vormonat) muss
    das tatsächliche Belegdatum übergeben werden, sonst würde ein Jahreswechsel anhand des
    falschen Datums erkannt (Issue #399-Konsolidierung: vorher hatte jeder Aufrufer sein
    eigenes, dupliziertes Increment/Reset/Format hier hin- statt herzuzuschreiben)."""
    nk = db.query(Nummernkreis).filter(Nummernkreis.typ == typ).first()
    if not nk:
        return None
    bezug = datum or date.today()
    # Jahreswechsel-Reset nur vorwärts (Issue #426): eine Eingangsrechnung wird oft nicht
    # chronologisch nach Rechnungsdatum erfasst, sondern wie der Beleg zur Hand ist. Wird
    # danach eine ÄLTERE Rechnung (z.B. aus dem Vorjahr) nacherfasst, darf das nicht als
    # Jahreswechsel missverstanden werden - sonst setzt sich der Zähler auf 1 zurück und
    # vergibt eine bereits verwendete Nummer doppelt (reproduziert: ER-260001 erscheint an
    # zwei verschiedenen Eingangsrechnungen, sobald zwischen 2026- und 2025-Belegen
    # gewechselt wird).
    if nk.reset_jaehrlich and nk.letztes_jahr and bezug.year > nk.letztes_jahr:
        nk.naechste_nr = 1
    if not nk.letztes_jahr or bezug.year > nk.letztes_jahr:
        nk.letztes_jahr = bezug.year
    nr = nk.naechste_nr
    nk.naechste_nr += 1
    candidate = _belegnr_aus_format(nk.format, bezug, nr)
    # Kollisions-Schutz (analog zu journal.py::_naechste_belegnr_journal()): Nummer
    # überspringen falls durch eine frühere Rückdatierung bereits vergeben.
    while db.query(Rechnung).filter(Rechnung.rechnungsnummer == candidate).first():
        nr = nk.naechste_nr
        nk.naechste_nr += 1
        candidate = _belegnr_aus_format(nk.format, bezug, nr)
    return candidate

router = APIRouter(prefix="/api/nummernkreise", tags=["Stammdaten"])


def _mit_vorschau(nk: Nummernkreis) -> NummernkreisResponse:
    resp = NummernkreisResponse.model_validate(nk)
    try:
        resp.vorschau = _belegnr_aus_format(nk.format, date.today(), nk.naechste_nr)
    except Exception:
        resp.vorschau = None
    return resp


@router.get("", response_model=list[NummernkreisResponse])
def list_nummernkreise(db: Session = Depends(get_db)):
    return [_mit_vorschau(nk) for nk in db.query(Nummernkreis).order_by(Nummernkreis.id).all()]


@router.get("/{nk_id}", response_model=NummernkreisResponse)
def get_nummernkreis(nk_id: int, db: Session = Depends(get_db)):
    nk = db.query(Nummernkreis).filter(Nummernkreis.id == nk_id).first()
    if not nk:
        raise HTTPException(status_code=404, detail="Nummernkreis nicht gefunden.")
    return _mit_vorschau(nk)


@router.put("/{nk_id}", response_model=NummernkreisResponse)
def update_nummernkreis(nk_id: int, data: NummernkreisUpdate, db: Session = Depends(get_db)):
    nk = db.query(Nummernkreis).filter(Nummernkreis.id == nk_id).first()
    if not nk:
        raise HTTPException(status_code=404, detail="Nummernkreis nicht gefunden.")
    if data.naechste_nr is not None and data.naechste_nr < nk.naechste_nr:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Die nächste Nummer darf nicht verringert werden (aktuell: {nk.naechste_nr}). "
                "Eine Verringerung würde bereits vergebene Nummern erneut ausgeben."
            ),
        )
    # Issue #399 Wunsch 2: der eigene Nummernkreis für wiederkehrende Rechnungen lässt sich
    # nur deaktivieren, solange er noch nie eine Nummer vergeben hat (naechste_nr == 1) - ein
    # Zurückschalten auf den gemeinsamen rechnung_ausgang-Kreis würde sonst später zu doppelt
    # vergebenen Rechnungsnummern führen können, sobald beide Kreise irgendwann dieselbe
    # laufende Nummer erreichen. Einschalten bleibt jederzeit möglich.
    if (
        nk.typ == "rechnung_wiederkehrend"
        and data.aktiv is False
        and nk.aktiv
        and nk.naechste_nr > 1
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Kann nicht deaktiviert werden: Es wurden bereits {nk.naechste_nr - 1} Rechnung(en) "
                "mit diesem eigenen Nummernkreis erstellt. Ein Zurückschalten auf den gemeinsamen "
                "Nummernkreis der Ausgangsrechnungen würde später doppelt vergebene Rechnungsnummern "
                "riskieren."
            ),
        )
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(nk, key, value)
    db.commit()
    db.refresh(nk)
    return _mit_vorschau(nk)


@router.get("/vorschau/{nk_id}")
def vorschau_nummernkreis(nk_id: int, format: str, db: Session = Depends(get_db)):
    """Liefert eine Vorschau der nächsten Belegnummer für ein gegebenes Format."""
    nk = db.query(Nummernkreis).filter(Nummernkreis.id == nk_id).first()
    if not nk:
        raise HTTPException(status_code=404, detail="Nummernkreis nicht gefunden.")
    try:
        vorschau = _belegnr_aus_format(format, date.today(), nk.naechste_nr)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Ungültiges Format: {e}")
    return {"vorschau": vorschau}
