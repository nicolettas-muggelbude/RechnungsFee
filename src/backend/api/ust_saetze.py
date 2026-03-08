"""USt-Sätze – konfigurierbare Mehrwertsteuersätze."""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import UstSatz

router = APIRouter(prefix="/api/ust-saetze", tags=["UstSaetze"])


class UstSatzResponse(BaseModel):
    id: int
    satz: Decimal
    bezeichnung: Optional[str] = None
    ist_aktiv: bool
    ist_default: bool
    ist_standard: bool

    model_config = {"from_attributes": True}


class UstSatzCreate(BaseModel):
    satz: Decimal
    bezeichnung: Optional[str] = None


class UstSatzUpdate(BaseModel):
    bezeichnung: Optional[str] = None
    ist_aktiv: Optional[bool] = None
    ist_default: Optional[bool] = None


@router.get("", response_model=list[UstSatzResponse])
def list_ust_saetze(db: Session = Depends(get_db)):
    return db.query(UstSatz).order_by(UstSatz.satz).all()


@router.post("", response_model=UstSatzResponse, status_code=201)
def create_ust_satz(data: UstSatzCreate, db: Session = Depends(get_db)):
    existing = db.query(UstSatz).filter(UstSatz.satz == data.satz).first()
    if existing:
        raise HTTPException(status_code=409, detail="Dieser Steuersatz existiert bereits.")
    eintrag = UstSatz(satz=data.satz, bezeichnung=data.bezeichnung)
    db.add(eintrag)
    db.commit()
    db.refresh(eintrag)
    return eintrag


@router.put("/{ust_id}", response_model=UstSatzResponse)
def update_ust_satz(ust_id: int, data: UstSatzUpdate, db: Session = Depends(get_db)):
    eintrag = db.query(UstSatz).filter(UstSatz.id == ust_id).first()
    if not eintrag:
        raise HTTPException(status_code=404, detail="Steuersatz nicht gefunden.")

    if data.bezeichnung is not None:
        eintrag.bezeichnung = data.bezeichnung
    if data.ist_aktiv is not None:
        eintrag.ist_aktiv = data.ist_aktiv
    if data.ist_default is True:
        # Nur einer darf Default sein
        db.query(UstSatz).update({"ist_default": False})
        eintrag.ist_default = True
    elif data.ist_default is False:
        eintrag.ist_default = False

    db.commit()
    db.refresh(eintrag)
    return eintrag


@router.delete("/{ust_id}", status_code=204)
def delete_ust_satz(ust_id: int, db: Session = Depends(get_db)):
    eintrag = db.query(UstSatz).filter(UstSatz.id == ust_id).first()
    if not eintrag:
        raise HTTPException(status_code=404, detail="Steuersatz nicht gefunden.")
    if eintrag.ist_standard:
        raise HTTPException(status_code=409, detail="Standard-Steuersätze können nicht gelöscht werden.")
    db.delete(eintrag)
    db.commit()
