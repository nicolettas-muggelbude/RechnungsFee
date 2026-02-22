"""
API-Endpunkte für Buchungskategorien.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Kategorie
from .schemas import KategorieResponse

router = APIRouter(prefix="/api/kategorien", tags=["Stammdaten"])


@router.get("", response_model=list[KategorieResponse])
def list_kategorien(kontenart: str | None = None, db: Session = Depends(get_db)):
    """Gibt alle Kategorien zurück, optional gefiltert nach Kontenart."""
    q = db.query(Kategorie)
    if kontenart:
        q = q.filter(Kategorie.kontenart == kontenart)
    return q.order_by(Kategorie.kontenart, Kategorie.name).all()


@router.get("/{kategorie_id}", response_model=KategorieResponse)
def get_kategorie(kategorie_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    kat = db.query(Kategorie).filter(Kategorie.id == kategorie_id).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Kategorie nicht gefunden.")
    return kat
