"""
Wiederkehrende Buchungen – Vorlagen für Fixkosten (Miete, Leasing, Abonnements).

Zwei Modi:
  direkt – Journal-Eintrag direkt aus Vorlage erstellen (Dauerauftrag, SEPA)
  beleg  – Eingangsrechnung aus Vorlage vorausfüllen (monatliche PDF-Rechnung)
"""

import calendar
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import (
    Beleg,
    Buchungsvorlage,
    Journaleintrag,
    Kategorie,
    Konto,
    Lieferant,
    Unternehmen,
)
from api.journal import _naechste_belegnr, _berechne_ust, _berechne_vorsteuer, _ust_konto
from api.rechnungen import APP_DATA_DIR, BELEG_DIR, ERLAUBTE_MIME_TYPES
from utils.signatur import signatur_journaleintrag

router = APIRouter(prefix="/api/buchungsvorlagen", tags=["Buchungsvorlagen"])

Q = Decimal("0.01")
INTERVALLE = {"monatlich", "quartalsweise", "jaehrlich"}
MODI = {"direkt", "beleg"}


# ---------------------------------------------------------------------------
# Pydantic-Schemas
# ---------------------------------------------------------------------------

class BuchungsvorlageCreate(BaseModel):
    bezeichnung: str
    lieferant_id: Optional[int] = None
    kategorie_id: Optional[int] = None
    konto_id: Optional[int] = None
    betrag: Decimal
    ist_brutto: bool = True
    ust_satz: Decimal = Decimal("0")
    intervall: str = "monatlich"
    naechstes_datum: date
    aktiv: bool = True
    modus: str = "direkt"
    notizen: Optional[str] = None


class BuchungsvorlageUpdate(BaseModel):
    bezeichnung: Optional[str] = None
    lieferant_id: Optional[int] = None
    kategorie_id: Optional[int] = None
    konto_id: Optional[int] = None
    betrag: Optional[Decimal] = None
    ist_brutto: Optional[bool] = None
    ust_satz: Optional[Decimal] = None
    intervall: Optional[str] = None
    naechstes_datum: Optional[date] = None
    aktiv: Optional[bool] = None
    modus: Optional[str] = None
    notizen: Optional[str] = None


class BuchungsvorlageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bezeichnung: str
    lieferant_id: Optional[int]
    lieferant_name: Optional[str] = None
    kategorie_id: Optional[int]
    kategorie_name: Optional[str] = None
    konto_id: Optional[int]
    konto_name: Optional[str] = None
    betrag: Decimal
    ist_brutto: bool
    ust_satz: Decimal
    intervall: str
    naechstes_datum: date
    aktiv: bool
    modus: str
    notizen: Optional[str]
    beleg_id: Optional[int]
    beleg_name: Optional[str] = None
    letzte_buchung: Optional[date]
    erstellte_buchungen: int
    erstellt_am: datetime


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _vorruecken(d: date, intervall: str) -> date:
    """Datum um ein Intervall vorrücken."""
    if intervall == "monatlich":
        monat = d.month + 1
        jahr = d.year + (monat - 1) // 12
        monat = ((monat - 1) % 12) + 1
        tag = min(d.day, calendar.monthrange(jahr, monat)[1])
        return date(jahr, monat, tag)
    if intervall == "quartalsweise":
        monat = d.month + 3
        jahr = d.year + (monat - 1) // 12
        monat = ((monat - 1) % 12) + 1
        tag = min(d.day, calendar.monthrange(jahr, monat)[1])
        return date(jahr, monat, tag)
    # jaehrlich
    try:
        return date(d.year + 1, d.month, d.day)
    except ValueError:
        return date(d.year + 1, d.month, 28)


def _to_response(v: Buchungsvorlage) -> BuchungsvorlageResponse:
    return BuchungsvorlageResponse(
        id=v.id,
        bezeichnung=v.bezeichnung,
        lieferant_id=v.lieferant_id,
        lieferant_name=v.lieferant.firmenname if v.lieferant else None,
        kategorie_id=v.kategorie_id,
        kategorie_name=v.kategorie.name if v.kategorie else None,
        konto_id=v.konto_id,
        konto_name=v.konto.name if v.konto else None,
        betrag=v.betrag,
        ist_brutto=bool(v.ist_brutto),
        ust_satz=v.ust_satz,
        intervall=v.intervall,
        naechstes_datum=v.naechstes_datum,
        aktiv=bool(v.aktiv),
        modus=v.modus,
        notizen=v.notizen,
        beleg_id=v.beleg_id,
        beleg_name=v.beleg.original_name if v.beleg else None,
        letzte_buchung=v.letzte_buchung,
        erstellte_buchungen=v.erstellte_buchungen,
        erstellt_am=v.erstellt_am,
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=list[BuchungsvorlageResponse])
def list_vorlagen(db: Session = Depends(get_db)):
    vorlagen = db.query(Buchungsvorlage).order_by(Buchungsvorlage.bezeichnung).all()
    return [_to_response(v) for v in vorlagen]


@router.post("", response_model=BuchungsvorlageResponse, status_code=201)
def erstelle_vorlage(data: BuchungsvorlageCreate, db: Session = Depends(get_db)):
    if data.intervall not in INTERVALLE:
        raise HTTPException(422, f"intervall muss einer von {INTERVALLE} sein")
    if data.modus not in MODI:
        raise HTTPException(422, f"modus muss 'direkt' oder 'beleg' sein")
    v = Buchungsvorlage(**data.model_dump())
    db.add(v)
    db.commit()
    db.refresh(v)
    return _to_response(v)


@router.get("/faellige", response_model=list[BuchungsvorlageResponse])
def faellige_vorlagen(db: Session = Depends(get_db)):
    """Aktive Vorlagen, deren naechstes_datum heute oder früher liegt."""
    heute = date.today()
    vorlagen = (
        db.query(Buchungsvorlage)
        .filter(Buchungsvorlage.aktiv == True, Buchungsvorlage.naechstes_datum <= heute)
        .order_by(Buchungsvorlage.naechstes_datum)
        .all()
    )
    return [_to_response(v) for v in vorlagen]


@router.get("/{vorlage_id}", response_model=BuchungsvorlageResponse)
def get_vorlage(vorlage_id: int, db: Session = Depends(get_db)):
    v = db.query(Buchungsvorlage).filter(Buchungsvorlage.id == vorlage_id).first()
    if not v:
        raise HTTPException(404, "Vorlage nicht gefunden")
    return _to_response(v)


@router.put("/{vorlage_id}", response_model=BuchungsvorlageResponse)
def aktualisiere_vorlage(vorlage_id: int, data: BuchungsvorlageUpdate, db: Session = Depends(get_db)):
    v = db.query(Buchungsvorlage).filter(Buchungsvorlage.id == vorlage_id).first()
    if not v:
        raise HTTPException(404, "Vorlage nicht gefunden")
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(v, field, val)
    if data.intervall and data.intervall not in INTERVALLE:
        raise HTTPException(422, f"intervall muss einer von {INTERVALLE} sein")
    if data.modus and data.modus not in MODI:
        raise HTTPException(422, f"modus muss 'direkt' oder 'beleg' sein")
    db.commit()
    db.refresh(v)
    return _to_response(v)


@router.delete("/{vorlage_id}", status_code=204)
def loesche_vorlage(vorlage_id: int, db: Session = Depends(get_db)):
    v = db.query(Buchungsvorlage).filter(Buchungsvorlage.id == vorlage_id).first()
    if not v:
        raise HTTPException(404, "Vorlage nicht gefunden")
    if v.erstellte_buchungen and v.erstellte_buchungen > 0:
        raise HTTPException(409, "Vorlage hat bereits Buchungen – Löschen nicht möglich.")
    db.delete(v)
    db.commit()


# ---------------------------------------------------------------------------
# Direkt-Buchen: Journal-Eintrag aus Vorlage erstellen
# ---------------------------------------------------------------------------

@router.post("/{vorlage_id}/buchen", status_code=201)
def buche_vorlage(vorlage_id: int, db: Session = Depends(get_db)):
    """Legt einen Journal-Eintrag aus der Vorlage an und rückt das Datum vor."""
    v = db.query(Buchungsvorlage).filter(Buchungsvorlage.id == vorlage_id).first()
    if not v:
        raise HTTPException(404, "Vorlage nicht gefunden")
    if v.modus != "direkt":
        raise HTTPException(422, "Nur Direkt-Vorlagen können direkt gebucht werden")

    heute = date.today()
    kat = db.query(Kategorie).filter(Kategorie.id == v.kategorie_id).first() if v.kategorie_id else None

    # Betrag: brutto oder netto → immer als brutto speichern
    brutto = v.betrag if v.ist_brutto else (v.betrag * (1 + v.ust_satz / 100)).quantize(Q, ROUND_HALF_UP)
    netto, ust_betrag = _berechne_ust(brutto, v.ust_satz)
    ist_privat = kat.kontenart == "Privat" if kat else False
    vorsteuerabzug_flag = bool(v.ust_satz > 0 and not ist_privat)
    vorsteuer = _berechne_vorsteuer(ust_betrag, vorsteuerabzug_flag, kat)
    konto_skr03 = kat.konto_skr03 if kat else None
    konto_skr04 = kat.konto_skr04 if kat else None
    konto_ust_skr03, konto_ust_skr04 = _ust_konto("Ausgabe", v.ust_satz)

    belegnr = _naechste_belegnr(db, heute)
    eintrag = Journaleintrag(
        datum=heute,
        belegnr=belegnr,
        beschreibung=v.bezeichnung + (f" ({v.notizen})" if v.notizen else ""),
        kategorie_id=v.kategorie_id,
        zahlungsart="Bank",
        art="Ausgabe",
        brutto_betrag=brutto,
        netto_betrag=netto,
        ust_satz=v.ust_satz,
        ust_betrag=ust_betrag,
        vorsteuer_betrag=vorsteuer,
        vorsteuerabzug=vorsteuerabzug_flag,
        konto_skr03=konto_skr03,
        konto_skr04=konto_skr04,
        konto_ust_skr03=konto_ust_skr03 if v.ust_satz > 0 else None,
        konto_ust_skr04=konto_ust_skr04 if v.ust_satz > 0 else None,
        buchungsvorlage_id=v.id,
        immutable=True,
    )
    eintrag.signatur = signatur_journaleintrag(eintrag)
    db.add(eintrag)

    v.letzte_buchung = heute
    v.erstellte_buchungen = (v.erstellte_buchungen or 0) + 1
    v.naechstes_datum = _vorruecken(v.naechstes_datum, v.intervall)

    db.commit()
    db.refresh(eintrag)
    from api.schemas import JournalEintragResponse
    return JournalEintragResponse.model_validate(eintrag)


# ---------------------------------------------------------------------------
# Vertragsdokument (Beleg) an Vorlage hängen
# ---------------------------------------------------------------------------

@router.post("/{vorlage_id}/beleg", status_code=201)
async def upload_beleg(vorlage_id: int, datei: UploadFile = File(...), db: Session = Depends(get_db)):
    import hashlib, uuid as _uuid
    v = db.query(Buchungsvorlage).filter(Buchungsvorlage.id == vorlage_id).first()
    if not v:
        raise HTTPException(404, "Vorlage nicht gefunden")
    if datei.content_type not in ERLAUBTE_MIME_TYPES:
        raise HTTPException(422, "Nur PDF, JPG und PNG erlaubt")

    inhalt = await datei.read()
    sha = hashlib.sha256(inhalt).hexdigest()
    ext = Path(datei.filename).suffix.lower() if datei.filename else ".pdf"
    dateiname = f"{_uuid.uuid4().hex}{ext}"
    BELEG_DIR.mkdir(parents=True, exist_ok=True)
    (BELEG_DIR / dateiname).write_bytes(inhalt)

    if v.beleg_id:
        alter = db.query(Beleg).filter(Beleg.id == v.beleg_id).first()
        if alter:
            try:
                (BELEG_DIR / alter.dateiname).unlink(missing_ok=True)
            except Exception:
                pass
            db.delete(alter)
            db.flush()

    beleg = Beleg(
        dateiname=dateiname,
        original_name=datei.filename or dateiname,
        mime_type=datei.content_type,
        dateigroesse=len(inhalt),
        sha256=sha,
    )
    db.add(beleg)
    db.flush()
    v.beleg_id = beleg.id
    db.commit()
    return {"id": beleg.id, "original_name": beleg.original_name}


@router.post("/{vorlage_id}/erledigt", response_model=BuchungsvorlageResponse)
def vorlage_erledigt(vorlage_id: int, db: Session = Depends(get_db)):
    """Rückt naechstes_datum vor – beleg-Modus: Eingangsrechnung wurde verarbeitet."""
    v = db.query(Buchungsvorlage).filter(Buchungsvorlage.id == vorlage_id).first()
    if not v:
        raise HTTPException(404, "Vorlage nicht gefunden")
    v.letzte_buchung = date.today()
    v.erstellte_buchungen = (v.erstellte_buchungen or 0) + 1
    v.naechstes_datum = _vorruecken(v.naechstes_datum, v.intervall)
    db.commit()
    db.refresh(v)
    return _to_response(v)


@router.delete("/{vorlage_id}/beleg", status_code=204)
def loesche_beleg(vorlage_id: int, db: Session = Depends(get_db)):
    v = db.query(Buchungsvorlage).filter(Buchungsvorlage.id == vorlage_id).first()
    if not v or not v.beleg_id:
        raise HTTPException(404, "Kein Beleg vorhanden")
    beleg = db.query(Beleg).filter(Beleg.id == v.beleg_id).first()
    if beleg:
        try:
            (BELEG_DIR / beleg.dateiname).unlink(missing_ok=True)
        except Exception:
            pass
        v.beleg_id = None
        db.delete(beleg)
    db.commit()
