"""
API-Endpunkte für Nummernkreise (Belegnummern-Konfiguration).
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Nummernkreis
from .kassenbuch import _belegnr_aus_format
from .schemas import NummernkreisUpdate, NummernkreisResponse

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
