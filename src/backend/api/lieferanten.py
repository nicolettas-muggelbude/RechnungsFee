"""
API-Endpunkte für Lieferantenverwaltung.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Lieferant
from .schemas import LieferantCreate, LieferantUpdate, LieferantResponse

router = APIRouter(prefix="/api/lieferanten", tags=["Stammdaten"])


@router.get("", response_model=list[LieferantResponse])
def list_lieferanten(nur_aktive: bool = True, db: Session = Depends(get_db)):
    q = db.query(Lieferant)
    if nur_aktive:
        q = q.filter(Lieferant.aktiv == True)
    return q.order_by(Lieferant.firmenname).all()


@router.post("", response_model=LieferantResponse, status_code=201)
def create_lieferant(data: LieferantCreate, db: Session = Depends(get_db)):
    lieferant = Lieferant(**data.model_dump())
    db.add(lieferant)
    db.commit()
    db.refresh(lieferant)
    return lieferant


@router.get("/{lieferant_id}", response_model=LieferantResponse)
def get_lieferant(lieferant_id: int, db: Session = Depends(get_db)):
    lieferant = db.query(Lieferant).filter(Lieferant.id == lieferant_id).first()
    if not lieferant:
        raise HTTPException(status_code=404, detail="Lieferant nicht gefunden.")
    return lieferant


@router.put("/{lieferant_id}", response_model=LieferantResponse)
def update_lieferant(lieferant_id: int, data: LieferantUpdate, db: Session = Depends(get_db)):
    lieferant = db.query(Lieferant).filter(Lieferant.id == lieferant_id).first()
    if not lieferant:
        raise HTTPException(status_code=404, detail="Lieferant nicht gefunden.")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(lieferant, key, value)
    db.commit()
    db.refresh(lieferant)
    return lieferant


@router.delete("/{lieferant_id}", status_code=204)
def delete_lieferant(lieferant_id: int, db: Session = Depends(get_db)):
    """Löscht einen Lieferanten – nur wenn keine Rechnungen verknüpft sind."""
    lieferant = db.query(Lieferant).filter(Lieferant.id == lieferant_id).first()
    if not lieferant:
        raise HTTPException(status_code=404, detail="Lieferant nicht gefunden.")
    if lieferant.rechnungen:
        raise HTTPException(
            status_code=409,
            detail="Lieferant kann nicht gelöscht werden – es sind Rechnungen verknüpft. "
                   "Bitte den Lieferanten deaktivieren.",
        )
    db.delete(lieferant)
    db.commit()
