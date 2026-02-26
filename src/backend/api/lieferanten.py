"""
API-Endpunkte für Lieferantenverwaltung.
"""

import json as _json
from datetime import date as _date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response as _Response
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Lieferant, Rechnung, Nummernkreis
from .kassenbuch import _belegnr_aus_format
from .schemas import LieferantCreate, LieferantUpdate, LieferantResponse


def _naechste_nummer(typ: str, db: Session) -> str | None:
    nk = db.query(Nummernkreis).filter(Nummernkreis.typ == typ).first()
    if not nk:
        return None
    heute = _date.today()
    if nk.reset_jaehrlich and nk.letztes_jahr and nk.letztes_jahr != heute.year:
        nk.naechste_nr = 1
    nk.letztes_jahr = heute.year
    nr = nk.naechste_nr
    nk.naechste_nr += 1
    return _belegnr_aus_format(nk.format, heute, nr)

router = APIRouter(prefix="/api/lieferanten", tags=["Stammdaten"])


@router.get("", response_model=list[LieferantResponse])
def list_lieferanten(nur_aktive: bool = True, db: Session = Depends(get_db)):
    q = db.query(Lieferant)
    if nur_aktive:
        q = q.filter(Lieferant.aktiv == True)
    return q.order_by(Lieferant.firmenname).all()


@router.post("", response_model=LieferantResponse, status_code=201)
def create_lieferant(data: LieferantCreate, db: Session = Depends(get_db)):
    lieferant_data = data.model_dump()
    if not lieferant_data.get("lieferantennummer"):
        lieferant_data["lieferantennummer"] = _naechste_nummer("lieferant", db)
    lieferant = Lieferant(**lieferant_data)
    db.add(lieferant)
    db.commit()
    db.refresh(lieferant)
    return lieferant


@router.get("/{lieferant_id}/dsgvo-export")
def dsgvo_export(lieferant_id: int, db: Session = Depends(get_db)):
    """DSGVO Art. 15 (Auskunft) + Art. 20 (Datenportabilität):
    Alle gespeicherten Daten zu einem Lieferanten als JSON-Datei."""
    lieferant = db.query(Lieferant).filter(Lieferant.id == lieferant_id).first()
    if not lieferant:
        raise HTTPException(status_code=404, detail="Lieferant nicht gefunden.")

    rechnungen = (
        db.query(Rechnung)
        .filter(Rechnung.lieferant_id == lieferant_id)
        .order_by(Rechnung.datum)
        .all()
    )

    name = lieferant.firmenname or " ".join(
        t for t in [lieferant.vorname, lieferant.nachname] if t
    ) or f"Lieferant-{lieferant_id}"

    result = {
        "export_datum": str(_date.today()),
        "grundlage": "DSGVO Art. 15 (Auskunft) + Art. 20 (Datenportabilität)",
        "lieferantendaten": {
            "id": lieferant.id,
            "lieferantennummer": lieferant.lieferantennummer,
            "firmenname": lieferant.firmenname,
            "vorname": lieferant.vorname,
            "nachname": lieferant.nachname,
            "strasse": lieferant.strasse,
            "hausnummer": lieferant.hausnummer,
            "plz": lieferant.plz,
            "ort": lieferant.ort,
            "land": lieferant.land,
            "email": lieferant.email,
            "telefon": lieferant.telefon,
            "ust_idnr": lieferant.ust_idnr,
            "notizen": lieferant.notizen,
        },
        "rechnungen": [
            {
                "id": r.id,
                "rechnungsnummer": r.rechnungsnummer,
                "datum": str(r.datum),
                "leistungsdatum": str(r.leistungsdatum) if r.leistungsdatum else None,
                "brutto_gesamt": str(r.brutto_gesamt),
                "zahlungsstatus": r.zahlungsstatus,
                "storniert": r.storniert,
                "positionen": [
                    {
                        "beschreibung": p.beschreibung,
                        "menge": str(p.menge),
                        "einheit": p.einheit,
                        "netto": str(p.netto),
                        "ust_satz": str(p.ust_satz),
                        "brutto": str(p.brutto),
                    }
                    for p in r.positionen
                ],
            }
            for r in rechnungen
        ],
    }

    content = _json.dumps(result, ensure_ascii=False, indent=2)
    filename = f"dsgvo-{name.replace(' ', '-')}-{_date.today()}.json"
    return _Response(
        content=content.encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{lieferant_id}/anonymisieren")
def anonymisiere_lieferant(lieferant_id: int, db: Session = Depends(get_db)):
    """DSGVO Art. 17 (Recht auf Vergessenwerden):
    Löscht den Lieferantenstammsatz und entfernt die Verknüpfung in allen Rechnungen."""
    lieferant = db.query(Lieferant).filter(Lieferant.id == lieferant_id).first()
    if not lieferant:
        raise HTTPException(status_code=404, detail="Lieferant nicht gefunden.")

    name = lieferant.firmenname or " ".join(
        t for t in [lieferant.vorname, lieferant.nachname] if t
    ) or f"Lieferant #{lieferant_id}"

    rechnungen = db.query(Rechnung).filter(Rechnung.lieferant_id == lieferant_id).all()
    for r in rechnungen:
        if not r.partner_freitext:
            r.partner_freitext = name
        r.lieferant_id = None

    db.delete(lieferant)
    db.commit()

    return {
        "anonymisierte_rechnungen": len(rechnungen),
        "unveraenderlich_verblieben": 0,
        "hinweis": "",
    }


@router.get("/{lieferant_id}", response_model=LieferantResponse)
def get_lieferant(lieferant_id: int, db: Session = Depends(get_db)):
    lieferant = db.query(Lieferant).filter(Lieferant.id == lieferant_id).first()
    if not lieferant:
        raise HTTPException(status_code=404, detail="Lieferant nicht gefunden.")
    return lieferant


@router.put("/{lieferant_id}", response_model=LieferantResponse)
def update_lieferant(lieferant_id: int, data: LieferantUpdate, db: Session = Depends(get_db)):
    lieferant = db.query(Lieferant).filter(Lieferant.id == lieferant_id).first()
    if not lieferant:
        raise HTTPException(status_code=404, detail="Lieferant nicht gefunden.")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(lieferant, key, value)
    db.commit()
    db.refresh(lieferant)
    return lieferant


@router.delete("/{lieferant_id}", status_code=204)
def delete_lieferant(lieferant_id: int, db: Session = Depends(get_db)):
    """Löscht einen Lieferanten – nur wenn keine Rechnungen verknüpft sind.
    Für Lieferanten mit verknüpften Daten stattdessen /anonymisieren verwenden."""
    lieferant = db.query(Lieferant).filter(Lieferant.id == lieferant_id).first()
    if not lieferant:
        raise HTTPException(status_code=404, detail="Lieferant nicht gefunden.")
    if lieferant.rechnungen:
        raise HTTPException(
            status_code=409,
            detail="Lieferant hat verknüpfte Rechnungen. "
                   "Bitte 'Anonymisieren (DSGVO)' verwenden.",
        )
    db.delete(lieferant)
    db.commit()
