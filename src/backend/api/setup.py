"""
Setup-Status-Endpunkt – wird beim App-Start abgefragt um zu entscheiden,
ob der Einrichtungs-Assistent gezeigt werden soll.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Unternehmen, Konto, Kategorie, Kassenbucheintrag, Nummernkreis
from .schemas import SetupStatus
from .kassenbuch import _naechste_belegnr

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


class KassenbestandRequest(BaseModel):
    betrag: Decimal


@router.post("/kassenbestand", status_code=201)
def set_kassenbestand(data: KassenbestandRequest, db: Session = Depends(get_db)):
    """
    Legt den einmaligen Kassenanfangsbestand als unveränderlichen Kassenbucheintrag an.
    Wird nur beim Setup aufgerufen. Bereits vorhandene Einträge werden abgewiesen.
    """
    if data.betrag <= 0:
        return {"detail": "Betrag ist 0 – kein Eintrag angelegt."}

    # Doppelaufruf verhindern
    bereits = db.query(Kassenbucheintrag).filter(
        Kassenbucheintrag.beschreibung == "Kassenanfangsbestand"
    ).first()
    if bereits:
        raise HTTPException(status_code=409, detail="Kassenanfangsbestand wurde bereits gesetzt.")

    # Privateinlage-Kategorie suchen
    kat = db.query(Kategorie).filter(Kategorie.name == "Privateinlage").first()

    heute = date.today()
    belegnr = _naechste_belegnr(db, heute)

    eintrag = Kassenbucheintrag(
        datum=heute,
        belegnr=belegnr,
        beschreibung="Kassenanfangsbestand",
        kategorie_id=kat.id if kat else None,
        zahlungsart="Bar",
        art="Einnahme",
        netto_betrag=data.betrag,
        ust_satz=Decimal("0"),
        ust_betrag=Decimal("0"),
        brutto_betrag=data.betrag,
        vorsteuerabzug=False,
        immutable=True,
    )
    db.add(eintrag)
    db.commit()
    return {"belegnr": belegnr, "betrag": str(data.betrag)}
