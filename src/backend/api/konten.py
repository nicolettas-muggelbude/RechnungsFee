"""
API-Endpunkte für Bankkonten-Verwaltung.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Konto, BankTransaktion
from .schemas import KontoCreate, KontoUpdate, KontoResponse

router = APIRouter(prefix="/api/konten", tags=["Stammdaten"])


@router.get("", response_model=list[KontoResponse])
def list_konten(nur_aktive: bool = True, db: Session = Depends(get_db)):
    """Gibt alle Konten zurück (standardmäßig nur aktive)."""
    q = db.query(Konto)
    if nur_aktive:
        q = q.filter(Konto.aktiv == True)
    return q.order_by(Konto.ist_standard.desc(), Konto.name).all()


@router.post("", response_model=KontoResponse, status_code=201)
def create_konto(data: KontoCreate, db: Session = Depends(get_db)):
    """Legt ein neues Bankkonto an."""
    if db.query(Konto).filter(Konto.iban == data.iban).first():
        raise HTTPException(status_code=409, detail=f"IBAN {data.iban} bereits vorhanden.")
    # Erstes Konto wird automatisch Standard
    ist_erstes = db.query(Konto).count() == 0
    konto_data = data.model_dump()
    konto_data["ist_standard"] = data.ist_standard or ist_erstes
    konto = Konto(**konto_data)
    # Wenn dieses Konto Standard wird, alle anderen zurücksetzen
    if konto.ist_standard:
        db.query(Konto).update({"ist_standard": False})
    db.add(konto)
    db.commit()
    db.refresh(konto)
    return konto


@router.get("/{konto_id}", response_model=KontoResponse)
def get_konto(konto_id: int, db: Session = Depends(get_db)):
    konto = db.query(Konto).filter(Konto.id == konto_id).first()
    if not konto:
        raise HTTPException(status_code=404, detail="Konto nicht gefunden.")
    return konto


@router.put("/{konto_id}", response_model=KontoResponse)
def update_konto(konto_id: int, data: KontoUpdate, db: Session = Depends(get_db)):
    """Aktualisiert ein Konto."""
    konto = db.query(Konto).filter(Konto.id == konto_id).first()
    if not konto:
        raise HTTPException(status_code=404, detail="Konto nicht gefunden.")
    # Standard-Konto wechseln
    if data.ist_standard is True:
        db.query(Konto).update({"ist_standard": False})
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(konto, key, value)
    db.commit()
    db.refresh(konto)
    return konto


@router.delete("/{konto_id}", status_code=204)
def delete_konto(konto_id: int, db: Session = Depends(get_db)):
    """Löscht ein Konto – nur wenn keine Transaktionen verknüpft sind."""
    konto = db.query(Konto).filter(Konto.id == konto_id).first()
    if not konto:
        raise HTTPException(status_code=404, detail="Konto nicht gefunden.")
    hat_transaktionen = db.query(BankTransaktion).filter(
        BankTransaktion.konto_id == konto_id
    ).first()
    if hat_transaktionen:
        raise HTTPException(
            status_code=409,
            detail="Konto kann nicht gelöscht werden – es sind Transaktionen verknüpft. "
                   "Bitte das Konto deaktivieren.",
        )
    if konto.ist_standard:
        raise HTTPException(
            status_code=409,
            detail="Das Standard-Konto kann nicht gelöscht werden. "
                   "Bitte zuerst ein anderes Konto als Standard festlegen.",
        )
    db.delete(konto)
    db.commit()
