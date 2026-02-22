"""
Setup-Status-Endpunkt – wird beim App-Start abgefragt um zu entscheiden,
ob der Einrichtungs-Assistent gezeigt werden soll.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Unternehmen, Konto, Kategorie
from .schemas import SetupStatus

router = APIRouter(prefix="/api/setup", tags=["Setup"])


@router.get("/status", response_model=SetupStatus)
def get_setup_status(db: Session = Depends(get_db)):
    """
    Gibt zurück, ob die App bereits eingerichtet ist.
    Das Frontend zeigt beim ersten Start den Setup-Assistenten.
    """
    hat_unternehmen = db.query(Unternehmen).first() is not None
    hat_konto = db.query(Konto).filter(Konto.aktiv == True).first() is not None
    hat_kategorien = db.query(Kategorie).count() > 0

    return SetupStatus(
        ist_eingerichtet=hat_unternehmen and hat_konto,
        hat_unternehmen=hat_unternehmen,
        hat_konto=hat_konto,
        hat_kategorien=hat_kategorien,
    )
