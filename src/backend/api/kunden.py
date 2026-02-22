"""
API-Endpunkte für Kundenverwaltung.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Kunde
from .schemas import KundeCreate, KundeUpdate, KundeResponse

router = APIRouter(prefix="/api/kunden", tags=["Stammdaten"])


@router.get("", response_model=list[KundeResponse])
def list_kunden(nur_aktive: bool = True, db: Session = Depends(get_db)):
    q = db.query(Kunde)
    if nur_aktive:
        q = q.filter(Kunde.aktiv == True)
    return q.order_by(Kunde.firmenname, Kunde.nachname).all()


@router.post("", response_model=KundeResponse, status_code=201)
def create_kunde(data: KundeCreate, db: Session = Depends(get_db)):
    kunde = Kunde(**data.model_dump())
    db.add(kunde)
    db.commit()
    db.refresh(kunde)
    return kunde


@router.get("/{kunde_id}", response_model=KundeResponse)
def get_kunde(kunde_id: int, db: Session = Depends(get_db)):
    kunde = db.query(Kunde).filter(Kunde.id == kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")
    return kunde


@router.put("/{kunde_id}", response_model=KundeResponse)
def update_kunde(kunde_id: int, data: KundeUpdate, db: Session = Depends(get_db)):
    kunde = db.query(Kunde).filter(Kunde.id == kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(kunde, key, value)
    db.commit()
    db.refresh(kunde)
    return kunde


@router.delete("/{kunde_id}", status_code=204)
def delete_kunde(kunde_id: int, db: Session = Depends(get_db)):
    """Löscht einen Kunden – nur wenn keine Rechnungen verknüpft sind."""
    kunde = db.query(Kunde).filter(Kunde.id == kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")
    if kunde.rechnungen:
        raise HTTPException(
            status_code=409,
            detail="Kunde kann nicht gelöscht werden – es sind Rechnungen verknüpft. "
                   "Bitte den Kunden deaktivieren.",
        )
    db.delete(kunde)
    db.commit()
