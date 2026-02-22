"""
API-Endpunkte für Unternehmensstammdaten.
Es gibt immer genau einen Datensatz (id=1).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Unternehmen
from .schemas import UnternehmenCreate, UnternehmenUpdate, UnternehmenResponse

router = APIRouter(prefix="/api/unternehmen", tags=["Stammdaten"])


@router.get("", response_model=UnternehmenResponse | None)
def get_unternehmen(db: Session = Depends(get_db)):
    """Gibt die Unternehmensdaten zurück, oder null wenn noch nicht eingerichtet."""
    return db.query(Unternehmen).first()


@router.post("", response_model=UnternehmenResponse, status_code=201)
def create_unternehmen(data: UnternehmenCreate, db: Session = Depends(get_db)):
    """Erstellt die Unternehmensdaten (nur beim ersten Setup)."""
    if db.query(Unternehmen).first():
        raise HTTPException(
            status_code=409,
            detail="Unternehmensdaten bereits vorhanden. Bitte PUT verwenden.",
        )
    unternehmen = Unternehmen(**data.model_dump())
    db.add(unternehmen)
    db.commit()
    db.refresh(unternehmen)
    return unternehmen


@router.put("", response_model=UnternehmenResponse)
def update_unternehmen(data: UnternehmenUpdate, db: Session = Depends(get_db)):
    """Aktualisiert die Unternehmensdaten."""
    unternehmen = db.query(Unternehmen).first()
    if not unternehmen:
        raise HTTPException(status_code=404, detail="Unternehmensdaten noch nicht angelegt.")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(unternehmen, key, value)
    db.commit()
    db.refresh(unternehmen)
    return unternehmen
