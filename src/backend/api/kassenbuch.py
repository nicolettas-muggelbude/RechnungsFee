"""
Kassenbuch-API (GoBD-konform, unveränderbar).
Kein PUT/DELETE – nur Storno als Gegenbuchung.
"""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Kassenbucheintrag, Kategorie, Unternehmen, Nummernkreis
from .schemas import (
    KassenbuchEintragCreate,
    KassenbuchEintragResponse,
    StornoRequest,
    MonatsUebersicht,
)

router = APIRouter(prefix="/api/kassenbuch", tags=["Kassenbuch"])


import re as _re


def _belegnr_aus_format(format_str: str, datum: date, nr: int) -> str:
    """Wendet das Format-Template an. Y=Jahrsstelle, #=Nummernstelle."""
    year_4 = str(datum.year)
    year_2 = year_4[-2:]
    result = format_str.replace("YYYY", year_4).replace("YY", year_2)

    def _pad(m: _re.Match) -> str:
        return str(nr).zfill(len(m.group()))

    return _re.sub(r"#+", _pad, result)


def _naechste_belegnr(db: Session, datum: date) -> str:
    """Liest den Kassenbuch-Nummernkreis, generiert die nächste Belegnummer
    und speichert den inkrementierten Zähler (atomar im selben Commit)."""
    nk = db.query(Nummernkreis).filter(Nummernkreis.typ == "kassenbuch").first()
    if not nk:
        # Fallback falls Seed fehlt
        count = db.query(Kassenbucheintrag).count()
        return f"{str(datum.year)[-2:]}{count + 1:04d}"

    # Jahreswechsel-Reset
    if nk.reset_jaehrlich and nk.letztes_jahr and nk.letztes_jahr != datum.year:
        nk.naechste_nr = 1
    nk.letztes_jahr = datum.year

    nr = nk.naechste_nr
    nk.naechste_nr += 1
    # Wird im selben db.commit() des Eintrags gespeichert
    return _belegnr_aus_format(nk.format, datum, nr)


def _berechne_ust(brutto: Decimal, ust_satz: Decimal) -> tuple[Decimal, Decimal]:
    """Gibt (netto, ust_betrag) zurück. ROUND_HALF_UP auf 2 Stellen."""
    if ust_satz == 0:
        return brutto, Decimal("0.00")
    netto = (brutto * 100 / (100 + ust_satz)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    ust_betrag = (brutto - netto).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return netto, ust_betrag


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

    einnahmen = (
        db.query(func.sum(Kassenbucheintrag.brutto_betrag))
        .filter(
            extract("year", Kassenbucheintrag.datum) == jahr_int,
            extract("month", Kassenbucheintrag.datum) == mon_int,
            Kassenbucheintrag.art == "Einnahme",
        )
        .scalar()
        or Decimal("0")
    )
    ausgaben = (
        db.query(func.sum(Kassenbucheintrag.brutto_betrag))
        .filter(
            extract("year", Kassenbucheintrag.datum) == jahr_int,
            extract("month", Kassenbucheintrag.datum) == mon_int,
            Kassenbucheintrag.art == "Ausgabe",
        )
        .scalar()
        or Decimal("0")
    )
    anzahl = (
        db.query(func.count(Kassenbucheintrag.id))
        .filter(
            extract("year", Kassenbucheintrag.datum) == jahr_int,
            extract("month", Kassenbucheintrag.datum) == mon_int,
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


@router.get("", response_model=list[KassenbuchEintragResponse])
def list_eintraege(
    monat: Optional[str] = Query(None, description="Format: YYYY-MM"),
    datum_von: Optional[date] = Query(None, description="Von-Datum (YYYY-MM-DD)"),
    datum_bis: Optional[date] = Query(None, description="Bis-Datum (YYYY-MM-DD)"),
    kategorie_id: Optional[int] = None,
    art: Optional[str] = Query(None, description="Einnahme oder Ausgabe"),
    db: Session = Depends(get_db),
):
    """Kassenbucheinträge mit optionalen Filtern."""
    q = db.query(Kassenbucheintrag)
    if monat:
        try:
            jahr, mon = monat.split("-")
            q = q.filter(
                extract("year", Kassenbucheintrag.datum) == int(jahr),
                extract("month", Kassenbucheintrag.datum) == int(mon),
            )
        except (ValueError, AttributeError):
            raise HTTPException(status_code=422, detail="monat muss im Format YYYY-MM sein")
    else:
        if datum_von:
            q = q.filter(Kassenbucheintrag.datum >= datum_von)
        if datum_bis:
            q = q.filter(Kassenbucheintrag.datum <= datum_bis)
    if kategorie_id is not None:
        q = q.filter(Kassenbucheintrag.kategorie_id == kategorie_id)
    if art:
        if art not in ("Einnahme", "Ausgabe"):
            raise HTTPException(status_code=422, detail="art muss Einnahme oder Ausgabe sein")
        q = q.filter(Kassenbucheintrag.art == art)
    eintraege = q.order_by(Kassenbucheintrag.datum.desc(), Kassenbucheintrag.id.desc()).all()
    return [KassenbuchEintragResponse.from_orm_with_kunde(e) for e in eintraege]


@router.post("", response_model=KassenbuchEintragResponse, status_code=201)
def create_eintrag(data: KassenbuchEintragCreate, db: Session = Depends(get_db)):
    """Legt einen neuen unveränderlichen Kassenbucheintrag an."""
    # Kleinunternehmer-Check
    unternehmen = db.query(Unternehmen).first()
    ust_satz = data.ust_satz
    steuerbefreiung_grund = None
    if unternehmen and unternehmen.ist_kleinunternehmer:
        ust_satz = Decimal("0")
        steuerbefreiung_grund = "§19 UStG"

    netto, ust_betrag = _berechne_ust(data.brutto_betrag, ust_satz)
    belegnr = _naechste_belegnr(db, data.datum)

    eintrag = Kassenbucheintrag(
        datum=data.datum,
        belegnr=belegnr,
        beschreibung=data.beschreibung,
        kategorie_id=data.kategorie_id,
        kunde_id=data.kunde_id,
        zahlungsart=data.zahlungsart,
        art=data.art,
        netto_betrag=netto,
        ust_satz=ust_satz,
        ust_betrag=ust_betrag,
        brutto_betrag=data.brutto_betrag,
        vorsteuerabzug=data.vorsteuerabzug,
        steuerbefreiung_grund=steuerbefreiung_grund,
        immutable=True,
    )
    db.add(eintrag)
    db.commit()
    db.refresh(eintrag)
    return KassenbuchEintragResponse.from_orm_with_kunde(eintrag)


@router.get("/{eintrag_id}", response_model=KassenbuchEintragResponse)
def get_eintrag(eintrag_id: int, db: Session = Depends(get_db)):
    eintrag = db.query(Kassenbucheintrag).filter(Kassenbucheintrag.id == eintrag_id).first()
    if not eintrag:
        raise HTTPException(status_code=404, detail="Kassenbucheintrag nicht gefunden.")
    return KassenbuchEintragResponse.from_orm_with_kunde(eintrag)


@router.post("/{eintrag_id}/storno", response_model=KassenbuchEintragResponse, status_code=201)
def storno_eintrag(eintrag_id: int, data: StornoRequest, db: Session = Depends(get_db)):
    """Storniert einen Eintrag durch eine Gegenbuchung (GoBD-konform)."""
    original = db.query(Kassenbucheintrag).filter(Kassenbucheintrag.id == eintrag_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Kassenbucheintrag nicht gefunden.")
    # Storno eines Stornos verhindern
    if original.beschreibung.startswith("STORNO "):
        raise HTTPException(status_code=409, detail="Ein Storno-Eintrag kann nicht erneut storniert werden.")
    # Bereits stornierte Buchung erkennen
    bereits_storniert = db.query(Kassenbucheintrag).filter(
        Kassenbucheintrag.beschreibung.like(f"STORNO {original.belegnr}:%")
    ).first()
    if bereits_storniert:
        raise HTTPException(
            status_code=409,
            detail=f"Diese Buchung wurde bereits storniert (Gegenbuchung: {bereits_storniert.belegnr}).",
        )
    # Gegenbuchung: umgekehrte Art
    storno_art = "Ausgabe" if original.art == "Einnahme" else "Einnahme"
    storno_datum = date.today()
    belegnr = _naechste_belegnr(db, storno_datum)

    storno = Kassenbucheintrag(
        datum=storno_datum,
        belegnr=belegnr,
        beschreibung=f"STORNO {original.belegnr}: {data.grund}",
        kategorie_id=original.kategorie_id,
        zahlungsart=original.zahlungsart,
        art=storno_art,
        netto_betrag=original.netto_betrag,
        ust_satz=original.ust_satz,
        ust_betrag=original.ust_betrag,
        brutto_betrag=original.brutto_betrag,
        vorsteuerabzug=False,
        steuerbefreiung_grund=None,
        immutable=True,
    )
    db.add(storno)
    db.commit()
    db.refresh(storno)
    return KassenbuchEintragResponse.from_orm_with_kunde(storno)
