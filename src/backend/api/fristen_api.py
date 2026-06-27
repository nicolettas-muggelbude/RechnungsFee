"""Steuerliche Fristen – Endpoint für die Fristenliste."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Unternehmen
from .fristen import fristen_berechnen
from .feiertage import BUNDESLAENDER

router = APIRouter(prefix="/api/fristen", tags=["Fristen"])


@router.get("")
def get_fristen(
    monate: int = Query(default=3, ge=1, le=24),
    db: Session = Depends(get_db),
):
    u = db.query(Unternehmen).first()
    if not u:
        return {"fristen": [], "bundesland": None, "konfiguriert": False}

    bundesland = u.bundesland or "NW"
    rhythmus = getattr(u, "voranmeldungsrhythmus", "quartal") or "quartal"
    dauerfrist = bool(getattr(u, "dauerfristverlaengerung_ust", False))
    est_aktiv = bool(getattr(u, "est_vorauszahlungen_aktiv", False))
    gewst_aktiv = bool(getattr(u, "gewst_vorauszahlungen_aktiv", False))

    # Kleinunternehmer §19: keine UStVA-Pflicht
    ist_kleinunternehmer = bool(getattr(u, "ist_kleinunternehmer", False))
    if ist_kleinunternehmer:
        rhythmus = None

    fristen = fristen_berechnen(
        bundesland=bundesland,
        voranmeldungsrhythmus=rhythmus or "quartal",
        dauerfristverlaengerung=dauerfrist,
        est_aktiv=est_aktiv,
        gewst_aktiv=gewst_aktiv,
        monate=monate,
    ) if (not ist_kleinunternehmer or est_aktiv or gewst_aktiv) else []

    if ist_kleinunternehmer and not est_aktiv and not gewst_aktiv:
        fristen = []

    return {
        "fristen": fristen,
        "bundesland": bundesland,
        "bundesland_name": BUNDESLAENDER.get(bundesland, bundesland),
        "rhythmus": rhythmus,
        "dauerfristverlaengerung": dauerfrist,
        "est_aktiv": est_aktiv,
        "gewst_aktiv": gewst_aktiv,
        "ist_kleinunternehmer": ist_kleinunternehmer,
        "konfiguriert": bool(u.bundesland),
    }


@router.get("/bundeslaender")
def get_bundeslaender():
    return [{"code": k, "name": v} for k, v in sorted(BUNDESLAENDER.items(), key=lambda x: x[1])]
