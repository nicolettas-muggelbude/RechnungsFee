"""
API-Endpunkte für Lieferantenverwaltung.
"""

import json as _json
from datetime import date as _date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response as _Response, StreamingResponse
from io import BytesIO
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Journaleintrag, Lieferant, Rechnung, Nummernkreis, Unternehmen
from .journal import _belegnr_aus_format
from .schemas import LieferantCreate, LieferantUpdate, LieferantResponse
from utils.pdf_dsgvo import generate_dsgvo_pdf


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
    nr = lieferant_data.get("lieferantennummer")
    if not lieferant_data.get("kreditor_nr"):
        lieferant_data["kreditor_nr"] = _naechste_nummer("kreditor", db)
    if nr and db.query(Lieferant).filter(Lieferant.lieferantennummer == nr).first():
        raise HTTPException(status_code=409, detail=f"Lieferantennummer '{nr}' ist bereits vergeben.")
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
                "leistung_von": str(r.leistung_von) if r.leistung_von else None, "leistung_bis": str(r.leistung_bis) if r.leistung_bis else None,
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


@router.get("/{lieferant_id}/dsgvo-export-pdf")
def dsgvo_export_pdf(lieferant_id: int, db: Session = Depends(get_db)):
    """DSGVO Art. 15: Datenauskunft als lesbare PDF-Datei."""
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

    stammdaten = {
        "id": lieferant.id, "lieferantennummer": lieferant.lieferantennummer,
        "firmenname": lieferant.firmenname, "vorname": lieferant.vorname,
        "nachname": lieferant.nachname, "strasse": lieferant.strasse,
        "hausnummer": lieferant.hausnummer, "plz": lieferant.plz,
        "ort": lieferant.ort, "land": lieferant.land, "email": lieferant.email,
        "telefon": lieferant.telefon, "ust_idnr": lieferant.ust_idnr,
        "notizen": lieferant.notizen,
    }
    rechnungen_dicts = [
        {
            "rechnungsnummer": r.rechnungsnummer, "datum": str(r.datum),
            "leistung_von": str(r.leistung_von) if r.leistung_von else None, "leistung_bis": str(r.leistung_bis) if r.leistung_bis else None,
            "brutto_gesamt": str(r.brutto_gesamt), "zahlungsstatus": r.zahlungsstatus,
            "storniert": r.storniert,
            "positionen": [
                {"beschreibung": p.beschreibung, "menge": str(p.menge),
                 "einheit": p.einheit, "netto": str(p.netto),
                 "ust_satz": str(p.ust_satz), "brutto": str(p.brutto)}
                for p in r.positionen
            ],
        }
        for r in rechnungen
    ]

    pdf_bytes = generate_dsgvo_pdf(stammdaten, rechnungen_dicts, None, "Lieferant")
    filename = f"dsgvo-{name.replace(' ', '-')}-{_date.today()}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
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


class KontokorrentBewegung(BaseModel):
    datum: str
    typ: str          # rechnung | zahlung | gutschrift | storno
    belegnr: str
    beschreibung: str
    betrag: float     # positiv = Verbindlichkeit, negativ = Ausgleich
    saldo: float


@router.get("/{lieferant_id}/kontokorrent", response_model=list[KontokorrentBewegung])
def kontokorrent_lieferant(lieferant_id: int, db: Session = Depends(get_db)):
    lieferant = db.query(Lieferant).filter(Lieferant.id == lieferant_id).first()
    if not lieferant:
        raise HTTPException(status_code=404, detail="Lieferant nicht gefunden.")

    bewegungen: list[dict] = []

    # Eingangsrechnungen dieses Lieferanten
    rechnungen = (
        db.query(Rechnung)
        .filter(
            Rechnung.lieferant_id == lieferant_id,
            Rechnung.typ == "eingang",
            Rechnung.ist_entwurf == False,
        )
        .all()
    )
    rechnung_ids = {r.id for r in rechnungen}

    for r in rechnungen:
        bewegungen.append({
            "datum": str(r.datum),
            "typ": "rechnung",
            "belegnr": r.externe_belegnr or r.rechnungsnummer or str(r.id),
            "beschreibung": f"Eingangsrechnung {r.externe_belegnr or r.rechnungsnummer or '—'}",
            "betrag": float(r.brutto_gesamt),
        })

    # Zahlungsausgänge aus dem Journal
    zahlungen = (
        db.query(Journaleintrag)
        .filter(
            Journaleintrag.rechnung_id.in_(rechnung_ids),
            Journaleintrag.art == "Ausgabe",
        )
        .all()
    )
    for j in zahlungen:
        bewegungen.append({
            "datum": str(j.datum),
            "typ": "zahlung",
            "belegnr": j.belegnr,
            "beschreibung": j.beschreibung,
            "betrag": -float(j.brutto_betrag),
        })

    bewegungen.sort(key=lambda b: b["datum"])

    saldo = 0.0
    ergebnis: list[KontokorrentBewegung] = []
    for b in bewegungen:
        saldo += b["betrag"]
        ergebnis.append(KontokorrentBewegung(saldo=round(saldo, 2), **b))
    return ergebnis


def _kontokorrent_bewegungen_lieferant(
    lieferant_id: int, von: _date, bis: _date, db: Session
) -> tuple[list[dict], str]:
    """Gibt (bewegungen_dicts, partner_name) zurück, gefiltert nach Zeitraum."""
    lieferant = db.query(Lieferant).filter(Lieferant.id == lieferant_id).first()
    if not lieferant:
        raise HTTPException(status_code=404, detail="Lieferant nicht gefunden.")
    partner_name = (
        lieferant.firmenname
        or " ".join(t for t in [lieferant.vorname, lieferant.nachname] if t)
        or f"Lieferant #{lieferant_id}"
    )

    rechnungen = (
        db.query(Rechnung)
        .filter(
            Rechnung.lieferant_id == lieferant_id,
            Rechnung.typ == "eingang",
            Rechnung.ist_entwurf == False,
        )
        .all()
    )
    rechnung_ids = {r.id for r in rechnungen}

    raw: list[dict] = []
    for r in rechnungen:
        datum = r.datum
        if not (von <= datum <= bis):
            continue
        raw.append({
            "datum": str(datum), "typ": "rechnung",
            "belegnr": r.externe_belegnr or r.rechnungsnummer or str(r.id),
            "beschreibung": f"Eingangsrechnung {r.externe_belegnr or r.rechnungsnummer or '—'}",
            "betrag": float(r.brutto_gesamt),
        })

    zahlungen = (
        db.query(Journaleintrag)
        .filter(
            Journaleintrag.rechnung_id.in_(rechnung_ids),
            Journaleintrag.art == "Ausgabe",
            Journaleintrag.datum >= von,
            Journaleintrag.datum <= bis,
        )
        .all()
    )
    for j in zahlungen:
        raw.append({
            "datum": str(j.datum), "typ": "zahlung",
            "belegnr": j.belegnr, "beschreibung": j.beschreibung,
            "betrag": -float(j.brutto_betrag),
        })

    raw.sort(key=lambda b: b["datum"])
    saldo = 0.0
    bewegungen: list[dict] = []
    for b in raw:
        saldo += b["betrag"]
        bewegungen.append({**b, "saldo": round(saldo, 2)})
    return bewegungen, partner_name


@router.get("/{lieferant_id}/kontokorrent/pdf")
def kontokorrent_pdf_lieferant(
    lieferant_id: int,
    von: _date = None,
    bis: _date = None,
    db: Session = Depends(get_db),
):
    from utils.pdf_kontokorrent import erstelle_kontokorrent_pdf
    if not von:
        von = _date(_date.today().year, 1, 1)
    if not bis:
        bis = _date.today()
    bewegungen, partner_name = _kontokorrent_bewegungen_lieferant(lieferant_id, von, bis, db)
    unt = db.query(Unternehmen).first()
    unt_dict = {c.name: getattr(unt, c.name) for c in unt.__table__.columns} if unt else {}

    pdf_bytes = erstelle_kontokorrent_pdf(
        unternehmen=unt_dict,
        partner_name=partner_name,
        von=str(von),
        bis=str(bis),
        bewegungen=bewegungen,
    )
    dateiname = f"Kontokorrent_{partner_name.replace(' ', '_')}_{von}_{bis}.pdf"
    return _Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{dateiname}"'},
    )


class KontokorrentMailRequestLieferant(BaseModel):
    an: str
    cc: Optional[str] = None
    betreff: str
    text: str
    von: Optional[_date] = None
    bis: Optional[_date] = None


@router.post("/{lieferant_id}/kontokorrent/mail")
def kontokorrent_mail_lieferant(
    lieferant_id: int,
    data: KontokorrentMailRequestLieferant,
    db: Session = Depends(get_db),
):
    from utils.pdf_kontokorrent import erstelle_kontokorrent_pdf
    from api.mail import _build_message, _smtp_einstellungen, _sende
    von = data.von or _date(_date.today().year, 1, 1)
    bis = data.bis or _date.today()
    bewegungen, partner_name = _kontokorrent_bewegungen_lieferant(lieferant_id, von, bis, db)
    unt = _smtp_einstellungen(db)
    unt_dict = {c.name: getattr(unt, c.name) for c in unt.__table__.columns}

    pdf_bytes = erstelle_kontokorrent_pdf(
        unternehmen=unt_dict,
        partner_name=partner_name,
        von=str(von),
        bis=str(bis),
        bewegungen=bewegungen,
    )
    dateiname = f"Kontokorrent_{partner_name.replace(' ', '_')}_{von}_{bis}.pdf"
    empfaenger = [data.an]
    if data.cc:
        empfaenger.append(data.cc)
    msg = _build_message(unt, data.an, data.cc, data.betreff, data.text,
                         attachments=[(pdf_bytes, dateiname)])
    _sende(unt, msg, empfaenger)
    return {"ok": True}


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
    dump = data.model_dump(exclude_none=True)
    neue_nr = dump.get("lieferantennummer")
    if neue_nr and neue_nr != lieferant.lieferantennummer:
        if db.query(Lieferant).filter(Lieferant.lieferantennummer == neue_nr, Lieferant.id != lieferant_id).first():
            raise HTTPException(status_code=409, detail=f"Lieferantennummer '{neue_nr}' ist bereits vergeben.")
    neue_kreditor = dump.get("kreditor_nr")
    if neue_kreditor and neue_kreditor != lieferant.kreditor_nr:
        if db.query(Lieferant).filter(Lieferant.kreditor_nr == neue_kreditor, Lieferant.id != lieferant_id).first():
            raise HTTPException(status_code=409, detail=f"Kreditorennummer '{neue_kreditor}' ist bereits vergeben.")
    for key, value in dump.items():
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
