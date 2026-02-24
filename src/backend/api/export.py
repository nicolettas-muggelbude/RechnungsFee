"""
GoBD-Export-API.
"""

from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import extract
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Kassenbucheintrag, Tagesabschluss
from utils.gobd_export import generate_gobd_zip

router = APIRouter(prefix="/api/export", tags=["Export"])


@router.get("/gobd")
def gobd_export(
    jahr: int = Query(..., description="Wirtschaftsjahr, z.B. 2026"),
    db: Session = Depends(get_db),
):
    """
    Erstellt einen vollständigen GoBD-Export für das angegebene Jahr als ZIP-Datei.
    Enthält: Kassenbuch-Journal, Tagesabschlüsse, Stammdaten, Integritätsprüfung,
    GDPdU-Index und PDF-Prüfbericht.
    """
    # Prüfen ob Daten für das Jahr vorhanden sind
    anzahl_buchungen = (
        db.query(Kassenbucheintrag)
        .filter(
            Kassenbucheintrag.immutable == True,
            extract("year", Kassenbucheintrag.datum) == jahr,
        )
        .count()
    )
    anzahl_abschluesse = (
        db.query(Tagesabschluss)
        .filter(
            Tagesabschluss.immutable == True,
            extract("year", Tagesabschluss.datum) == jahr,
        )
        .count()
    )

    if anzahl_buchungen == 0 and anzahl_abschluesse == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Keine Daten für das Jahr {jahr} gefunden.",
        )

    zip_bytes = generate_gobd_zip(db, jahr)
    dateiname = f"GoBD_Export_{jahr}.zip"

    return StreamingResponse(
        BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{dateiname}"'},
    )
