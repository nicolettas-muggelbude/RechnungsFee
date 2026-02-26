"""
API-Endpunkte für Kundenverwaltung.
"""

import json as _json
from datetime import date as _date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response as _Response
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Kunde, Kassenbucheintrag, Rechnung, Nummernkreis
from .kassenbuch import _belegnr_aus_format
from .schemas import KundeCreate, KundeUpdate, KundeResponse


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

router = APIRouter(prefix="/api/kunden", tags=["Stammdaten"])


@router.get("", response_model=list[KundeResponse])
def list_kunden(nur_aktive: bool = True, db: Session = Depends(get_db)):
    q = db.query(Kunde)
    if nur_aktive:
        q = q.filter(Kunde.aktiv == True)
    return q.order_by(Kunde.firmenname, Kunde.nachname).all()


@router.post("", response_model=KundeResponse, status_code=201)
def create_kunde(data: KundeCreate, db: Session = Depends(get_db)):
    kunde_data = data.model_dump()
    if not kunde_data.get("kundennummer"):
        kunde_data["kundennummer"] = _naechste_nummer("kunde", db)
    kunde = Kunde(**kunde_data)
    db.add(kunde)
    db.commit()
    db.refresh(kunde)
    return kunde


@router.get("/{kunde_id}/dsgvo-export")
def dsgvo_export(kunde_id: int, db: Session = Depends(get_db)):
    """DSGVO Art. 15 (Auskunft) + Art. 20 (Datenportabilität):
    Alle gespeicherten Daten zu einem Kunden als JSON-Datei."""
    kunde = db.query(Kunde).filter(Kunde.id == kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")

    eintraege = (
        db.query(Kassenbucheintrag)
        .filter(Kassenbucheintrag.kunde_id == kunde_id)
        .order_by(Kassenbucheintrag.datum)
        .all()
    )
    rechnungen = (
        db.query(Rechnung)
        .filter(Rechnung.kunde_id == kunde_id)
        .order_by(Rechnung.datum)
        .all()
    )

    name_teile = [kunde.firmenname, kunde.vorname, kunde.nachname]
    name = " ".join(t for t in name_teile if t) or f"Kunde-{kunde_id}"

    result = {
        "export_datum": str(_date.today()),
        "grundlage": "DSGVO Art. 15 (Auskunft) + Art. 20 (Datenportabilität)",
        "kundendaten": {
            "id": kunde.id,
            "kundennummer": kunde.kundennummer,
            "firmenname": kunde.firmenname,
            "vorname": kunde.vorname,
            "nachname": kunde.nachname,
            "strasse": kunde.strasse,
            "hausnummer": kunde.hausnummer,
            "plz": kunde.plz,
            "ort": kunde.ort,
            "land": kunde.land,
            "email": kunde.email,
            "telefon": kunde.telefon,
            "ust_idnr": kunde.ust_idnr,
            "ist_verein": kunde.ist_verein,
            "ist_gemeinnuetzig": kunde.ist_gemeinnuetzig,
            "notizen": kunde.notizen,
        },
        "kassenbuch": [
            {
                "id": e.id,
                "datum": str(e.datum),
                "belegnr": e.belegnr,
                "beschreibung": e.beschreibung,
                "art": e.art,
                "brutto_betrag": str(e.brutto_betrag),
                "zahlungsart": e.zahlungsart,
                "immutable": e.immutable,
            }
            for e in eintraege
        ],
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


@router.post("/{kunde_id}/anonymisieren")
def anonymisiere_kunde(kunde_id: int, db: Session = Depends(get_db)):
    """DSGVO Art. 17 (Recht auf Vergessenwerden):
    Löscht den Kundenstammsatz und entfernt die Verknüpfung in allen
    nicht-immutable Buchungen und Rechnungen.

    Immutable Kassenbucheinträge (nach Tagesabschluss) können nicht
    geändert werden (GoBD-Schutz, §147 AO hat Vorrang vor DSGVO Art. 17).
    """
    kunde = db.query(Kunde).filter(Kunde.id == kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")

    name_teile = [kunde.firmenname, kunde.vorname, kunde.nachname]
    kunde_name = " ".join(t for t in name_teile if t) or f"Kunde #{kunde_id}"

    # Mutable Kassenbucheinträge anonymisieren
    mutable = (
        db.query(Kassenbucheintrag)
        .filter(Kassenbucheintrag.kunde_id == kunde_id, Kassenbucheintrag.immutable == False)
        .all()
    )
    for e in mutable:
        e.kunde_id = None

    # Immutable Kassenbucheinträge: GoBD-Trigger blockiert jede Änderung → nur zählen
    immutable_anzahl = (
        db.query(Kassenbucheintrag)
        .filter(Kassenbucheintrag.kunde_id == kunde_id, Kassenbucheintrag.immutable == True)
        .count()
    )

    # Rechnungen: kunde_id entfernen, Name als partner_freitext sichern
    rechnungen = db.query(Rechnung).filter(Rechnung.kunde_id == kunde_id).all()
    for r in rechnungen:
        if not r.partner_freitext:
            r.partner_freitext = kunde_name
        r.kunde_id = None

    db.delete(kunde)
    db.commit()

    return {
        "anonymisierte_buchungen": len(mutable),
        "anonymisierte_rechnungen": len(rechnungen),
        "unveraenderlich_verblieben": immutable_anzahl,
        "hinweis": (
            f"{immutable_anzahl} immutable Kassenbucheinträge konnten nicht anonymisiert werden "
            f"(GoBD-Schutz, Aufbewahrungspflicht §147 AO)."
            if immutable_anzahl else ""
        ),
    }


@router.get("/{kunde_id}", response_model=KundeResponse)
def get_kunde(kunde_id: int, db: Session = Depends(get_db)):
    kunde = db.query(Kunde).filter(Kunde.id == kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")
    return kunde


@router.put("/{kunde_id}", response_model=KundeResponse)
def update_kunde(kunde_id: int, data: KundeUpdate, db: Session = Depends(get_db)):
    kunde = db.query(Kunde).filter(Kunde.id == kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(kunde, key, value)
    db.commit()
    db.refresh(kunde)
    return kunde


@router.delete("/{kunde_id}", status_code=204)
def delete_kunde(kunde_id: int, db: Session = Depends(get_db)):
    """Löscht einen Kunden – nur wenn keine Buchungen oder Rechnungen verknüpft sind.
    Für Kunden mit verknüpften Daten stattdessen /anonymisieren verwenden."""
    kunde = db.query(Kunde).filter(Kunde.id == kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")
    hat_rechnungen = bool(kunde.rechnungen)
    hat_buchungen = (
        db.query(Kassenbucheintrag).filter(Kassenbucheintrag.kunde_id == kunde_id).count() > 0
    )
    if hat_rechnungen or hat_buchungen:
        raise HTTPException(
            status_code=409,
            detail="Kunde hat verknüpfte Buchungen oder Rechnungen. "
                   "Bitte 'Anonymisieren (DSGVO)' verwenden.",
        )
    db.delete(kunde)
    db.commit()
