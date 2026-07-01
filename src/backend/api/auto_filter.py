"""
API-Endpunkte für Auto-Filter-Regeln und Klassifizierungs-Vorschläge.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import AutoFilterRegel, BankTransaktion

router = APIRouter(prefix="/api/auto-filter", tags=["Bank-Import"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AutoFilterRegelResponse(BaseModel):
    id: int
    partner_pattern: Optional[str] = None
    verwendungszweck_pattern: Optional[str] = None
    vorschlag: str
    kategorie_id: Optional[int] = None
    prioritaet: int
    aktiv: bool

    model_config = {"from_attributes": True}


class AutoFilterRegelCreate(BaseModel):
    partner_pattern: Optional[str] = None
    verwendungszweck_pattern: Optional[str] = None
    vorschlag: str  # geschaeftlich|privat|privatentnahme|einlage
    kategorie_id: Optional[int] = None
    prioritaet: int = 0
    aktiv: bool = True


class AutoFilterRegelUpdate(BaseModel):
    partner_pattern: Optional[str] = None
    verwendungszweck_pattern: Optional[str] = None
    vorschlag: Optional[str] = None
    kategorie_id: Optional[int] = None
    prioritaet: Optional[int] = None
    aktiv: Optional[bool] = None


class VorschlagRequest(BaseModel):
    partner_name: Optional[str] = None
    verwendungszweck: Optional[str] = None
    betrag: Optional[float] = None  # positiv = Einnahme, negativ = Ausgabe


class VorschlagResponse(BaseModel):
    vorschlag: Optional[str] = None  # geschaeftlich|privat|privatentnahme|einlage|None
    kategorie_id: Optional[int] = None
    quelle: Optional[str] = None    # keyword|regel|verlauf|heuristik


# ---------------------------------------------------------------------------
# Vorschlag-Engine
# ---------------------------------------------------------------------------

_PRIVATENTNAHME_KEYWORDS = {"privatentnahme", "privat entnahme", "private entnahme", "entnahme privat"}
_EINLAGE_KEYWORDS = {"einlage", "privateinlage", "private einlage", "einlage privat"}

_GESCHAEFTLICH_PATTERNS = [
    "gmbh", " ag ", " ag$", "^ag ", " kg ", " ohg ", " gbr ", " e.v.", " ev ",
    "finanzamt", "krankenkasse", "berufsgenossenschaft", "sozialversicherung",
    "steuerberater", "rechtsanwalt", "notar",
]


def _contains(text_val: Optional[str], keywords: set[str]) -> bool:
    if not text_val:
        return False
    lower = text_val.lower()
    return any(kw in lower for kw in keywords)


def _heuristik_geschaeftlich(partner_name: Optional[str]) -> bool:
    if not partner_name:
        return False
    lower = " " + partner_name.lower() + " "
    return any(p in lower for p in _GESCHAEFTLICH_PATTERNS)


def bestimme_vorschlag(
    partner_name: Optional[str],
    verwendungszweck: Optional[str],
    db: Session,
) -> VorschlagResponse:
    """
    Reihenfolge:
    1. Explizite Keywords (privatentnahme / einlage)
    2. User-Regeln (SQL LIKE, höchste Priorität zuerst)
    3. Historische Häufigkeit (>5 gleiche User-Entscheidungen für denselben Partner)
    4. Heuristik (Rechtsform-Kürzel → geschäftlich)
    """

    # 1. Keywords
    combined = " ".join(filter(None, [partner_name, verwendungszweck]))
    if _contains(combined, _PRIVATENTNAHME_KEYWORDS):
        return VorschlagResponse(vorschlag="privatentnahme", quelle="keyword")
    if _contains(combined, _EINLAGE_KEYWORDS):
        return VorschlagResponse(vorschlag="einlage", quelle="keyword")

    # 2. User-Regeln
    regeln = (
        db.query(AutoFilterRegel)
        .filter(AutoFilterRegel.aktiv == True)
        .order_by(AutoFilterRegel.prioritaet.desc())
        .all()
    )
    for regel in regeln:
        treffer = True
        if regel.partner_pattern:
            if not partner_name:
                treffer = False
            else:
                row = db.execute(
                    text("SELECT 1 WHERE :val LIKE :pat"),
                    {"val": partner_name, "pat": regel.partner_pattern},
                ).fetchone()
                treffer = treffer and (row is not None)
        if treffer and regel.verwendungszweck_pattern:
            if not verwendungszweck:
                treffer = False
            else:
                row = db.execute(
                    text("SELECT 1 WHERE :val LIKE :pat"),
                    {"val": verwendungszweck, "pat": regel.verwendungszweck_pattern},
                ).fetchone()
                treffer = treffer and (row is not None)
        if treffer:
            return VorschlagResponse(
                vorschlag=regel.vorschlag,
                kategorie_id=regel.kategorie_id,
                quelle="regel",
            )

    # 3. Historische Häufigkeit (>5 user-überschriebene Einträge für denselben Partner)
    if partner_name:
        row = db.execute(
            text("""
                SELECT
                    CASE
                        WHEN ist_privatentnahme = 1 THEN 'privatentnahme'
                        WHEN ist_einlage = 1        THEN 'einlage'
                        WHEN ist_geschaeftlich = 1  THEN 'geschaeftlich'
                        ELSE 'privat'
                    END AS klasse,
                    COUNT(*) AS cnt
                FROM bank_transaktionen
                WHERE partner_name = :partner AND user_ueberschrieben = 1
                GROUP BY klasse
                ORDER BY cnt DESC
                LIMIT 1
            """),
            {"partner": partner_name},
        ).fetchone()
        if row and row[1] > 5:
            return VorschlagResponse(vorschlag=row[0], quelle="verlauf")

    # 4. Heuristik
    if _heuristik_geschaeftlich(partner_name):
        return VorschlagResponse(vorschlag="geschaeftlich", quelle="heuristik")

    return VorschlagResponse()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[AutoFilterRegelResponse])
def list_regeln(db: Session = Depends(get_db)):
    return db.query(AutoFilterRegel).order_by(AutoFilterRegel.prioritaet.desc()).all()


@router.post("", response_model=AutoFilterRegelResponse, status_code=201)
def create_regel(data: AutoFilterRegelCreate, db: Session = Depends(get_db)):
    if data.vorschlag not in ("geschaeftlich", "privat", "privatentnahme", "einlage"):
        raise HTTPException(status_code=422, detail="Ungültiger Vorschlag-Wert.")
    if not data.partner_pattern and not data.verwendungszweck_pattern:
        raise HTTPException(status_code=422, detail="Mindestens ein Pattern erforderlich.")
    regel = AutoFilterRegel(**data.model_dump())
    db.add(regel)
    db.commit()
    db.refresh(regel)
    return regel


@router.put("/{regel_id}", response_model=AutoFilterRegelResponse)
def update_regel(regel_id: int, data: AutoFilterRegelUpdate, db: Session = Depends(get_db)):
    regel = db.query(AutoFilterRegel).filter(AutoFilterRegel.id == regel_id).first()
    if not regel:
        raise HTTPException(status_code=404, detail="Regel nicht gefunden.")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(regel, key, value)
    db.commit()
    db.refresh(regel)
    return regel


@router.delete("/{regel_id}", status_code=204)
def delete_regel(regel_id: int, db: Session = Depends(get_db)):
    regel = db.query(AutoFilterRegel).filter(AutoFilterRegel.id == regel_id).first()
    if not regel:
        raise HTTPException(status_code=404, detail="Regel nicht gefunden.")
    db.delete(regel)
    db.commit()


@router.post("/vorschlag", response_model=VorschlagResponse)
def vorschlag(data: VorschlagRequest, db: Session = Depends(get_db)):
    """Gibt einen Klassifizierungs-Vorschlag für eine Transaktion zurück."""
    return bestimme_vorschlag(data.partner_name, data.verwendungszweck, db)
