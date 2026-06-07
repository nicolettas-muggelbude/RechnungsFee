"""
API-Endpunkte für Dokumentenpakete (Anhang-Gruppen für Angebote / Auftragsbestätigungen).
"""

import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db, APP_DATA_DIR
from database.models import Beleg, DokumentenPaket, DokumentenPaketBeleg

router = APIRouter(prefix="/api/dokumentenpakete", tags=["Stammdaten"])

BELEG_DIR = APP_DATA_DIR / "uploads" / "belege"
ERLAUBTE_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PaketDateiResponse(BaseModel):
    id: int
    beleg_id: int
    bezeichnung: Optional[str]
    sort_order: int
    original_name: str
    mime_type: Optional[str]
    dateigroesse: Optional[int]

    model_config = {"from_attributes": True}


class PaketResponse(BaseModel):
    id: int
    name: str
    beschreibung: Optional[str]
    aktiv: bool
    erstellt_am: datetime
    dateien: list[PaketDateiResponse] = []

    model_config = {"from_attributes": True}


class PaketCreate(BaseModel):
    name: str
    beschreibung: Optional[str] = None


class PaketUpdate(BaseModel):
    name: Optional[str] = None
    beschreibung: Optional[str] = None
    aktiv: Optional[bool] = None


class DateiBezeichnungUpdate(BaseModel):
    bezeichnung: Optional[str] = None
    sort_order: Optional[int] = None


# ---------------------------------------------------------------------------
# Hilfsfunktion
# ---------------------------------------------------------------------------

def _paket_response(p: DokumentenPaket) -> PaketResponse:
    return PaketResponse(
        id=p.id,
        name=p.name,
        beschreibung=p.beschreibung,
        aktiv=p.aktiv,
        erstellt_am=p.erstellt_am,
        dateien=[
            PaketDateiResponse(
                id=d.id,
                beleg_id=d.beleg_id,
                bezeichnung=d.bezeichnung,
                sort_order=d.sort_order,
                original_name=d.beleg.original_name,
                mime_type=d.beleg.mime_type,
                dateigroesse=d.beleg.dateigroesse,
            )
            for d in p.dateien
        ],
    )


# ---------------------------------------------------------------------------
# Paket CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=list[PaketResponse])
def list_pakete(db: Session = Depends(get_db)):
    return [_paket_response(p) for p in db.query(DokumentenPaket).order_by(DokumentenPaket.name).all()]


@router.post("", response_model=PaketResponse, status_code=201)
def create_paket(data: PaketCreate, db: Session = Depends(get_db)):
    if not data.name.strip():
        raise HTTPException(status_code=422, detail="Name darf nicht leer sein.")
    p = DokumentenPaket(name=data.name.strip(), beschreibung=data.beschreibung)
    db.add(p)
    db.commit()
    db.refresh(p)
    return _paket_response(p)


@router.get("/{paket_id}", response_model=PaketResponse)
def get_paket(paket_id: int, db: Session = Depends(get_db)):
    p = db.query(DokumentenPaket).filter(DokumentenPaket.id == paket_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Dokumentenpaket nicht gefunden.")
    return _paket_response(p)


@router.put("/{paket_id}", response_model=PaketResponse)
def update_paket(paket_id: int, data: PaketUpdate, db: Session = Depends(get_db)):
    p = db.query(DokumentenPaket).filter(DokumentenPaket.id == paket_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Dokumentenpaket nicht gefunden.")
    if data.name is not None:
        if not data.name.strip():
            raise HTTPException(status_code=422, detail="Name darf nicht leer sein.")
        p.name = data.name.strip()
    if data.beschreibung is not None:
        p.beschreibung = data.beschreibung
    if data.aktiv is not None:
        p.aktiv = data.aktiv
    db.commit()
    db.refresh(p)
    return _paket_response(p)


@router.delete("/{paket_id}", status_code=204)
def delete_paket(paket_id: int, db: Session = Depends(get_db)):
    p = db.query(DokumentenPaket).filter(DokumentenPaket.id == paket_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Dokumentenpaket nicht gefunden.")
    # Belege physisch löschen
    for eintrag in p.dateien:
        pfad = APP_DATA_DIR / "uploads" / eintrag.beleg.dateiname
        if pfad.exists():
            pfad.unlink(missing_ok=True)
        db.delete(eintrag.beleg)
    db.delete(p)
    db.commit()


# ---------------------------------------------------------------------------
# Dateien in einem Paket
# ---------------------------------------------------------------------------

@router.post("/{paket_id}/dateien", response_model=PaketResponse, status_code=201)
async def upload_datei(
    paket_id: int,
    bezeichnung: Optional[str] = None,
    datei: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    p = db.query(DokumentenPaket).filter(DokumentenPaket.id == paket_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Dokumentenpaket nicht gefunden.")

    mime = datei.content_type or ""
    if mime not in ERLAUBTE_MIME_TYPES:
        raise HTTPException(status_code=422, detail=f"Dateityp '{mime}' nicht erlaubt. Erlaubt: PDF, JPEG, PNG.")

    inhalt = await datei.read()
    sha256 = hashlib.sha256(inhalt).hexdigest()

    jetzt = datetime.now()
    ziel_dir = BELEG_DIR / str(jetzt.year) / jetzt.strftime("%m")
    ziel_dir.mkdir(parents=True, exist_ok=True)

    original = Path(datei.filename or "dokument")
    stem = original.stem[:50]
    suffix = original.suffix.lower() or ".bin"
    dateiname_lokal = f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
    rel_pfad = f"belege/{jetzt.year}/{jetzt.strftime('%m')}/{dateiname_lokal}"
    (ziel_dir / dateiname_lokal).write_bytes(inhalt)

    beleg = Beleg(
        dateiname=rel_pfad,
        original_name=datei.filename or "dokument",
        mime_type=mime,
        dateigroesse=len(inhalt),
        sha256=sha256,
    )
    db.add(beleg)
    db.flush()

    sort_order = len(p.dateien)
    eintrag = DokumentenPaketBeleg(
        paket_id=p.id,
        beleg_id=beleg.id,
        bezeichnung=bezeichnung,
        sort_order=sort_order,
    )
    db.add(eintrag)
    db.commit()
    db.refresh(p)
    return _paket_response(p)


@router.put("/{paket_id}/dateien/{eintrag_id}", response_model=PaketResponse)
def update_datei_eintrag(
    paket_id: int,
    eintrag_id: int,
    data: DateiBezeichnungUpdate,
    db: Session = Depends(get_db),
):
    eintrag = db.query(DokumentenPaketBeleg).filter(
        DokumentenPaketBeleg.id == eintrag_id,
        DokumentenPaketBeleg.paket_id == paket_id,
    ).first()
    if not eintrag:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden.")
    if data.bezeichnung is not None:
        eintrag.bezeichnung = data.bezeichnung
    if data.sort_order is not None:
        eintrag.sort_order = data.sort_order
    db.commit()
    p = db.query(DokumentenPaket).filter(DokumentenPaket.id == paket_id).first()
    db.refresh(p)
    return _paket_response(p)


@router.delete("/{paket_id}/dateien/{eintrag_id}", response_model=PaketResponse)
def delete_datei(paket_id: int, eintrag_id: int, db: Session = Depends(get_db)):
    eintrag = db.query(DokumentenPaketBeleg).filter(
        DokumentenPaketBeleg.id == eintrag_id,
        DokumentenPaketBeleg.paket_id == paket_id,
    ).first()
    if not eintrag:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden.")
    beleg = eintrag.beleg
    pfad = APP_DATA_DIR / "uploads" / beleg.dateiname
    if pfad.exists():
        pfad.unlink(missing_ok=True)
    db.delete(eintrag)
    db.delete(beleg)
    db.commit()
    p = db.query(DokumentenPaket).filter(DokumentenPaket.id == paket_id).first()
    db.refresh(p)
    return _paket_response(p)


@router.get("/{paket_id}/dateien/{eintrag_id}/download")
def download_datei(paket_id: int, eintrag_id: int, db: Session = Depends(get_db)):
    eintrag = db.query(DokumentenPaketBeleg).filter(
        DokumentenPaketBeleg.id == eintrag_id,
        DokumentenPaketBeleg.paket_id == paket_id,
    ).first()
    if not eintrag:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden.")
    pfad = APP_DATA_DIR / "uploads" / eintrag.beleg.dateiname
    if not pfad.exists():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden.")
    return FileResponse(
        path=str(pfad),
        media_type=eintrag.beleg.mime_type or "application/octet-stream",
        filename=eintrag.beleg.original_name,
        content_disposition_type="inline",
    )
