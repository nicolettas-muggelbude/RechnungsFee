"""
API-Endpunkte für Buchungskategorien.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Kategorie, Journaleintrag, Rechnungsposition, Rechnung, BankTransaktion, AutoFilterRegel
from fastapi.responses import FileResponse
from .schemas import KategorieResponse, KategorieKontoUpdate, KategorieCreate, KategorieUpdate, KategorieBeschreibungUpdate

router = APIRouter(prefix="/api/kategorien", tags=["Stammdaten"])


@router.get("", response_model=list[KategorieResponse])
def list_kategorien(
    kontenart: str | None = None,
    nur_aktive: bool = False,
    nur_bebuchte: bool = False,
    db: Session = Depends(get_db),
):
    q = db.query(Kategorie)
    if kontenart:
        q = q.filter(Kategorie.kontenart == kontenart)
    if nur_aktive:
        q = q.filter(Kategorie.aktiv == True)
    if nur_bebuchte:
        q = q.filter(
            db.query(Journaleintrag).filter(Journaleintrag.kategorie_id == Kategorie.id).exists()
        )
    return q.order_by(Kategorie.kontenart, Kategorie.name).all()


@router.get("/{kategorie_id}", response_model=KategorieResponse)
def get_kategorie(kategorie_id: int, db: Session = Depends(get_db)):
    kat = db.query(Kategorie).filter(Kategorie.id == kategorie_id).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Kategorie nicht gefunden.")
    return kat


@router.post("", response_model=KategorieResponse, status_code=201)
def create_kategorie(data: KategorieCreate, db: Session = Depends(get_db)):
    if db.query(Kategorie).filter(Kategorie.name == data.name).first():
        raise HTTPException(status_code=409, detail="Eine Kategorie mit diesem Namen existiert bereits.")
    kat = Kategorie(
        name=data.name,
        kontenart=data.kontenart,
        konto_skr03=data.konto_skr03,
        konto_skr04=data.konto_skr04,
        konto_skr03_default=data.konto_skr03,
        konto_skr04_default=data.konto_skr04,
        euer_zeile=data.euer_zeile,
        eks_kategorie=data.eks_kategorie,
        vorsteuer_prozent=data.vorsteuer_prozent,
        ust_satz_standard=data.ust_satz_standard,
        beschreibung=data.beschreibung or None,
        ist_system=False,
        user_modified_skr03=False,
        user_modified_skr04=False,
    )
    db.add(kat)
    db.commit()
    db.refresh(kat)
    return kat


@router.put("/{kategorie_id}", response_model=KategorieResponse)
def update_kategorie(kategorie_id: int, data: KategorieCreate, db: Session = Depends(get_db)):
    kat = db.query(Kategorie).filter(Kategorie.id == kategorie_id).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Kategorie nicht gefunden.")
    if kat.ist_system:
        raise HTTPException(status_code=409, detail="Systemkategorien können nicht bearbeitet werden.")
    konflikt = db.query(Kategorie).filter(Kategorie.name == data.name, Kategorie.id != kategorie_id).first()
    if konflikt:
        raise HTTPException(status_code=409, detail="Eine Kategorie mit diesem Namen existiert bereits.")
    kat.name = data.name
    kat.kontenart = data.kontenart
    kat.konto_skr03 = data.konto_skr03 or None
    kat.konto_skr04 = data.konto_skr04 or None
    kat.konto_skr03_default = data.konto_skr03 or None
    kat.konto_skr04_default = data.konto_skr04 or None
    kat.euer_zeile = data.euer_zeile
    kat.eks_kategorie = data.eks_kategorie or None
    kat.vorsteuer_prozent = data.vorsteuer_prozent
    kat.ust_satz_standard = data.ust_satz_standard
    kat.beschreibung = data.beschreibung or None
    kat.user_modified_skr03 = False
    kat.user_modified_skr04 = False
    db.commit()
    db.refresh(kat)
    return kat


@router.patch("/{kategorie_id}/beschreibung", response_model=KategorieResponse)
def update_beschreibung(kategorie_id: int, data: KategorieBeschreibungUpdate, db: Session = Depends(get_db)):
    """Beschreibung / Beispiele zu einer Kategorie speichern (auch für Systemkategorien)."""
    kat = db.query(Kategorie).filter(Kategorie.id == kategorie_id).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Kategorie nicht gefunden.")
    kat.beschreibung = data.beschreibung.strip() if data.beschreibung else None
    db.commit()
    db.refresh(kat)
    return kat


@router.patch("/{kategorie_id}/aktiv", response_model=KategorieResponse)
def toggle_aktiv(kategorie_id: int, db: Session = Depends(get_db)):
    kat = db.query(Kategorie).filter(Kategorie.id == kategorie_id).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Kategorie nicht gefunden.")
    kat.aktiv = not kat.aktiv
    db.commit()
    db.refresh(kat)
    return kat


@router.patch("/{kategorie_id}/konten", response_model=KategorieResponse)
def update_konten(kategorie_id: int, data: KategorieKontoUpdate, db: Session = Depends(get_db)):
    kat = db.query(Kategorie).filter(Kategorie.id == kategorie_id).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Kategorie nicht gefunden.")
    if data.konto_skr03 is not None:
        kat.konto_skr03 = data.konto_skr03 or None
        kat.user_modified_skr03 = (data.konto_skr03 != kat.konto_skr03_default)
    if data.konto_skr04 is not None:
        kat.konto_skr04 = data.konto_skr04 or None
        kat.user_modified_skr04 = (data.konto_skr04 != kat.konto_skr04_default)
    db.commit()
    db.refresh(kat)
    return kat


@router.post("/{kategorie_id}/konten/reset", response_model=KategorieResponse)
def reset_konten(kategorie_id: int, db: Session = Depends(get_db)):
    kat = db.query(Kategorie).filter(Kategorie.id == kategorie_id).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Kategorie nicht gefunden.")
    kat.konto_skr03 = kat.konto_skr03_default
    kat.konto_skr04 = kat.konto_skr04_default
    kat.user_modified_skr03 = False
    kat.user_modified_skr04 = False
    db.commit()
    db.refresh(kat)
    return kat


@router.get("/export/pdf")
def export_kategorien_pdf(db: Session = Depends(get_db)):
    """PDF-Export aller aktiven Kategorien mit Beschreibung (ohne Kontonummern)."""
    import tempfile
    from utils.pdf_kategorien import generate_kategorien_pdf
    kategorien = db.query(Kategorie).filter(Kategorie.aktiv == True).order_by(Kategorie.kontenart, Kategorie.name).all()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        generate_kategorien_pdf(kategorien, tmp.name)
        return FileResponse(
            tmp.name,
            media_type="application/pdf",
            filename="kategorien.pdf",
            headers={"Content-Disposition": 'inline; filename="kategorien.pdf"'},
        )


@router.delete("/{kategorie_id}", status_code=204)
def delete_kategorie(kategorie_id: int, db: Session = Depends(get_db)):
    kat = db.query(Kategorie).filter(Kategorie.id == kategorie_id).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Kategorie nicht gefunden.")
    if kat.ist_system:
        raise HTTPException(status_code=409, detail="Systemkategorien können nicht gelöscht werden.")
    in_use = (
        db.query(Journaleintrag).filter(Journaleintrag.kategorie_id == kategorie_id).first() or
        db.query(Rechnungsposition).filter(Rechnungsposition.kategorie_id == kategorie_id).first() or
        db.query(Rechnung).filter(Rechnung.kategorie_id == kategorie_id).first() or
        db.query(BankTransaktion).filter(BankTransaktion.kategorie_id == kategorie_id).first() or
        db.query(AutoFilterRegel).filter(AutoFilterRegel.kategorie_id == kategorie_id).first()
    )
    if in_use:
        raise HTTPException(status_code=409, detail="Kategorie wird in Buchungen verwendet und kann nicht gelöscht werden.")
    db.delete(kat)
    db.commit()
