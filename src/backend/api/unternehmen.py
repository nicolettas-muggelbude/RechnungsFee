"""
API-Endpunkte für Unternehmensstammdaten.
Es gibt immer genau einen Datensatz (id=1).
"""

import imghdr
import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Unternehmen
from .schemas import UnternehmenCreate, UnternehmenUpdate, UnternehmenResponse

router = APIRouter(prefix="/api/unternehmen", tags=["Stammdaten"])

UPLOAD_DIR = Path.home() / ".local" / "share" / "RechnungsFee" / "uploads"
ERLAUBTE_TYPEN = {"image/png", "image/jpeg", "image/webp"}
MAX_LOGO_BYTES = 2 * 1024 * 1024  # 2 MB


def _upload_dir() -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


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
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(unternehmen, key, value)
    db.commit()
    db.refresh(unternehmen)
    return unternehmen


# ---------------------------------------------------------------------------
# Logo-Endpunkte
# ---------------------------------------------------------------------------

@router.post("/logo", response_model=UnternehmenResponse)
async def upload_logo(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Lädt ein Firmenlogo hoch (PNG/JPEG/WEBP, max 2 MB)."""
    unternehmen = db.query(Unternehmen).first()
    if not unternehmen:
        raise HTTPException(status_code=404, detail="Unternehmensdaten noch nicht angelegt.")

    inhalt = await file.read()
    if len(inhalt) > MAX_LOGO_BYTES:
        raise HTTPException(status_code=400, detail="Logo darf maximal 2 MB groß sein.")

    # Content-Type aus Dateiinhalt ermitteln (Fallback wenn Browser keinen/falschen Typ sendet)
    erkannt = imghdr.what(None, h=inhalt)
    typ_map = {"png": "image/png", "jpeg": "image/jpeg", "webp": "image/webp"}
    content_type = typ_map.get(erkannt or "", file.content_type or "")
    if content_type not in ERLAUBTE_TYPEN:
        raise HTTPException(status_code=400, detail="Nur PNG, JPEG und WEBP sind erlaubt.")

    # Dateierweiterung bestimmen
    ext_map = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
    ext = ext_map[content_type]
    ziel = _upload_dir() / f"logo.{ext}"

    # Altes Logo löschen (andere Erweiterung)
    if unternehmen.logo_pfad and unternehmen.logo_pfad != str(ziel):
        try:
            os.unlink(unternehmen.logo_pfad)
        except FileNotFoundError:
            pass

    with open(ziel, "wb") as f:
        f.write(inhalt)

    unternehmen.logo_pfad = str(ziel)
    db.commit()
    db.refresh(unternehmen)
    return unternehmen


@router.get("/logo")
def get_logo(db: Session = Depends(get_db)):
    """Liefert das gespeicherte Firmenlogo als Datei aus."""
    unternehmen = db.query(Unternehmen).first()
    if not unternehmen or not unternehmen.logo_pfad:
        raise HTTPException(status_code=404, detail="Kein Logo hinterlegt.")
    pfad = Path(unternehmen.logo_pfad)
    if not pfad.exists():
        raise HTTPException(status_code=404, detail="Logo-Datei nicht gefunden.")
    return FileResponse(str(pfad))


@router.delete("/logo", status_code=204)
def delete_logo(db: Session = Depends(get_db)):
    """Löscht das Firmenlogo."""
    unternehmen = db.query(Unternehmen).first()
    if not unternehmen:
        raise HTTPException(status_code=404, detail="Unternehmensdaten noch nicht angelegt.")
    if unternehmen.logo_pfad:
        try:
            os.unlink(unternehmen.logo_pfad)
        except FileNotFoundError:
            pass
        unternehmen.logo_pfad = None
        db.commit()
