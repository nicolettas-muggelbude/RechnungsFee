"""
API-Endpunkte für Kundenverwaltung.
"""

import hashlib
import json as _json
import uuid
from datetime import date as _date, datetime as _datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Body, UploadFile
from fastapi.responses import FileResponse as _FileResponse, Response as _Response, StreamingResponse
from io import BytesIO
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db, APP_DATA_DIR
from database.models import Beleg, Kunde, KundeBeleg, KundeLieferadresse, Journaleintrag, Rechnung, Nummernkreis, Unternehmen
from .journal import _belegnr_aus_format
from .schemas import KundeCreate, KundeUpdate, KundeResponse
from .schemas_rechnungen import BelegResponse
from utils.pdf_dsgvo import generate_dsgvo_pdf
from utils.pdf_kontokorrent import erstelle_kontokorrent_pdf

_BELEG_DIR = APP_DATA_DIR / "uploads" / "belege"
_ERLAUBTE_MIME = {"application/pdf", "image/jpeg", "image/png", "image/tiff", "image/webp",
                  "application/msword",
                  "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


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
    nr = kunde_data.get("kundennummer")
    if not kunde_data.get("debitor_nr"):
        kunde_data["debitor_nr"] = _naechste_nummer("debitor", db)
    if nr and db.query(Kunde).filter(Kunde.kundennummer == nr).first():
        raise HTTPException(status_code=409, detail=f"Kundennummer '{nr}' ist bereits vergeben.")
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
        db.query(Journaleintrag)
        .filter(Journaleintrag.kunde_id == kunde_id)
        .order_by(Journaleintrag.datum)
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
        "journal": [
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


@router.get("/{kunde_id}/dsgvo-export-pdf")
def dsgvo_export_pdf(kunde_id: int, db: Session = Depends(get_db)):
    """DSGVO Art. 15: Datenauskunft als lesbare PDF-Datei."""
    kunde = db.query(Kunde).filter(Kunde.id == kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")

    eintraege = (
        db.query(Journaleintrag)
        .filter(Journaleintrag.kunde_id == kunde_id)
        .order_by(Journaleintrag.datum)
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

    stammdaten = {
        "id": kunde.id, "kundennummer": kunde.kundennummer,
        "firmenname": kunde.firmenname, "vorname": kunde.vorname,
        "nachname": kunde.nachname, "strasse": kunde.strasse,
        "hausnummer": kunde.hausnummer, "plz": kunde.plz,
        "ort": kunde.ort, "land": kunde.land, "email": kunde.email,
        "telefon": kunde.telefon, "ust_idnr": kunde.ust_idnr,
        "notizen": kunde.notizen,
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
    journal_dicts = [
        {"datum": str(e.datum), "belegnr": e.belegnr, "beschreibung": e.beschreibung,
         "art": e.art, "brutto_betrag": str(e.brutto_betrag), "zahlungsart": e.zahlungsart}
        for e in eintraege
    ]

    pdf_bytes = generate_dsgvo_pdf(stammdaten, rechnungen_dicts, journal_dicts, "Kunde")
    filename = f"dsgvo-{name.replace(' ', '-')}-{_date.today()}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/{kunde_id}/anonymisieren")
def anonymisiere_kunde(kunde_id: int, db: Session = Depends(get_db)):
    """DSGVO Art. 17 (Recht auf Vergessenwerden):
    Löscht den Kundenstammsatz und entfernt die Verknüpfung in allen
    nicht-immutable Buchungen und Rechnungen.

    Immutable Journaleinträge (nach Tagesabschluss) können nicht
    geändert werden (GoBD-Schutz, §147 AO hat Vorrang vor DSGVO Art. 17).
    """
    kunde = db.query(Kunde).filter(Kunde.id == kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")

    name_teile = [kunde.firmenname, kunde.vorname, kunde.nachname]
    kunde_name = " ".join(t for t in name_teile if t) or f"Kunde #{kunde_id}"

    # Mutable Journaleinträge anonymisieren
    mutable = (
        db.query(Journaleintrag)
        .filter(Journaleintrag.kunde_id == kunde_id, Journaleintrag.immutable == False)
        .all()
    )
    for e in mutable:
        e.kunde_id = None

    # Immutable Journaleinträge: GoBD-Trigger blockiert jede Änderung → nur zählen
    immutable_anzahl = (
        db.query(Journaleintrag)
        .filter(Journaleintrag.kunde_id == kunde_id, Journaleintrag.immutable == True)
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


# ---------------------------------------------------------------------------
# Lieferadressen
# ---------------------------------------------------------------------------

class LieferadresseCreate(BaseModel):
    bezeichnung: Optional[str] = None
    z_hd: Optional[str] = None
    strasse: Optional[str] = None
    hausnummer: Optional[str] = None
    plz: Optional[str] = None
    ort: Optional[str] = None
    land: str = "DE"
    ist_standard: bool = False

class LieferadresseResponse(BaseModel):
    id: int
    kunde_id: int
    bezeichnung: Optional[str] = None
    z_hd: Optional[str] = None
    strasse: Optional[str] = None
    hausnummer: Optional[str] = None
    plz: Optional[str] = None
    ort: Optional[str] = None
    land: str
    ist_standard: bool
    model_config = {"from_attributes": True}


@router.get("/{kunde_id}/lieferadressen", response_model=list[LieferadresseResponse])
def list_lieferadressen(kunde_id: int, db: Session = Depends(get_db)):
    if not db.query(Kunde).filter(Kunde.id == kunde_id).first():
        raise HTTPException(404, "Kunde nicht gefunden.")
    return db.query(KundeLieferadresse).filter(KundeLieferadresse.kunde_id == kunde_id).all()


@router.post("/{kunde_id}/lieferadressen", response_model=LieferadresseResponse, status_code=201)
def create_lieferadresse(kunde_id: int, data: LieferadresseCreate, db: Session = Depends(get_db)):
    if not db.query(Kunde).filter(Kunde.id == kunde_id).first():
        raise HTTPException(404, "Kunde nicht gefunden.")
    if data.ist_standard:
        db.query(KundeLieferadresse).filter(KundeLieferadresse.kunde_id == kunde_id).update({"ist_standard": False})
    la = KundeLieferadresse(kunde_id=kunde_id, **data.model_dump())
    db.add(la)
    db.commit()
    db.refresh(la)
    return la


@router.put("/{kunde_id}/lieferadressen/{la_id}", response_model=LieferadresseResponse)
def update_lieferadresse(kunde_id: int, la_id: int, data: LieferadresseCreate, db: Session = Depends(get_db)):
    la = db.query(KundeLieferadresse).filter(
        KundeLieferadresse.id == la_id, KundeLieferadresse.kunde_id == kunde_id
    ).first()
    if not la:
        raise HTTPException(404, "Lieferadresse nicht gefunden.")
    if data.ist_standard:
        db.query(KundeLieferadresse).filter(
            KundeLieferadresse.kunde_id == kunde_id, KundeLieferadresse.id != la_id
        ).update({"ist_standard": False})
    for k, v in data.model_dump().items():
        setattr(la, k, v)
    db.commit()
    db.refresh(la)
    return la


@router.delete("/{kunde_id}/lieferadressen/{la_id}", status_code=204)
def delete_lieferadresse(kunde_id: int, la_id: int, db: Session = Depends(get_db)):
    la = db.query(KundeLieferadresse).filter(
        KundeLieferadresse.id == la_id, KundeLieferadresse.kunde_id == kunde_id
    ).first()
    if not la:
        raise HTTPException(404, "Lieferadresse nicht gefunden.")
    db.delete(la)
    db.commit()

    return {
        "anonymisierte_buchungen": len(mutable),
        "anonymisierte_rechnungen": len(rechnungen),
        "unveraenderlich_verblieben": immutable_anzahl,
        "hinweis": (
            f"{immutable_anzahl} immutable Journaleinträge konnten nicht anonymisiert werden "
            f"(GoBD-Schutz, Aufbewahrungspflicht §147 AO)."
            if immutable_anzahl else ""
        ),
    }


# ---------------------------------------------------------------------------
# Dokumente im Kundenstamm
# ---------------------------------------------------------------------------

class KundeBelegResponse(BaseModel):
    id: int
    bezeichnung: Optional[str]
    loeschdatum: Optional[_date]
    erstellt_am: _datetime
    beleg: BelegResponse
    model_config = {"from_attributes": True}


@router.get("/{kunde_id}/belege", response_model=list[KundeBelegResponse])
def list_kunde_belege(kunde_id: int, db: Session = Depends(get_db)):
    if not db.query(Kunde).filter(Kunde.id == kunde_id).first():
        raise HTTPException(404, "Kunde nicht gefunden.")
    return db.query(KundeBeleg).filter(KundeBeleg.kunde_id == kunde_id).order_by(KundeBeleg.id).all()


@router.post("/{kunde_id}/belege", response_model=KundeBelegResponse, status_code=201)
async def upload_kunde_beleg(
    kunde_id: int,
    datei: UploadFile = File(...),
    bezeichnung: str = Form(""),
    loeschdatum: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    if not db.query(Kunde).filter(Kunde.id == kunde_id).first():
        raise HTTPException(404, "Kunde nicht gefunden.")
    mime = datei.content_type or ""
    if mime not in _ERLAUBTE_MIME:
        raise HTTPException(422, f"Dateityp '{mime}' nicht erlaubt.")

    inhalt = await datei.read()
    sha256 = hashlib.sha256(inhalt).hexdigest()
    jetzt = _datetime.now()
    ziel_dir = _BELEG_DIR / str(jetzt.year) / jetzt.strftime("%m")
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

    from datetime import date as _date_cls
    ld = None
    if loeschdatum:
        try:
            ld = _date_cls.fromisoformat(loeschdatum)
        except ValueError:
            pass

    kb = KundeBeleg(
        kunde_id=kunde_id,
        beleg_id=beleg.id,
        bezeichnung=bezeichnung.strip() or None,
        loeschdatum=ld,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


class KundeBelegUpdate(BaseModel):
    bezeichnung: Optional[str] = None
    loeschdatum: Optional[_date] = None
    loeschdatum_loeschen: bool = False

@router.patch("/{kunde_id}/belege/{kb_id}", response_model=KundeBelegResponse)
def update_kunde_beleg(
    kunde_id: int, kb_id: int,
    data: KundeBelegUpdate,
    db: Session = Depends(get_db),
):
    kb = db.query(KundeBeleg).filter(KundeBeleg.id == kb_id, KundeBeleg.kunde_id == kunde_id).first()
    if not kb:
        raise HTTPException(404, "Dokument nicht gefunden.")
    if data.bezeichnung is not None:
        kb.bezeichnung = data.bezeichnung.strip() or None
    if data.loeschdatum_loeschen:
        kb.loeschdatum = None
    elif data.loeschdatum is not None:
        kb.loeschdatum = data.loeschdatum
    db.commit()
    db.refresh(kb)
    return kb


@router.get("/{kunde_id}/belege/{kb_id}/download")
def download_kunde_beleg(kunde_id: int, kb_id: int, db: Session = Depends(get_db)):
    kb = db.query(KundeBeleg).filter(KundeBeleg.id == kb_id, KundeBeleg.kunde_id == kunde_id).first()
    if not kb:
        raise HTTPException(404, "Dokument nicht gefunden.")
    beleg = kb.beleg
    pfad = APP_DATA_DIR / "uploads" / beleg.dateiname
    if not pfad.exists():
        raise HTTPException(404, "Datei nicht gefunden.")
    return _FileResponse(
        path=str(pfad),
        media_type=beleg.mime_type or "application/octet-stream",
        filename=beleg.original_name,
        content_disposition_type="inline",
    )


@router.delete("/{kunde_id}/belege/{kb_id}", status_code=204)
def delete_kunde_beleg(kunde_id: int, kb_id: int, db: Session = Depends(get_db)):
    kb = db.query(KundeBeleg).filter(KundeBeleg.id == kb_id, KundeBeleg.kunde_id == kunde_id).first()
    if not kb:
        raise HTTPException(404, "Dokument nicht gefunden.")
    beleg = kb.beleg
    pfad = APP_DATA_DIR / "uploads" / beleg.dateiname
    if pfad.exists():
        pfad.unlink()
    db.delete(kb)
    db.delete(beleg)
    db.commit()


class KontokorrentBewegung(BaseModel):
    datum: str
    typ: str          # rechnung | zahlung | gutschrift | storno
    belegnr: str
    beschreibung: str
    betrag: float     # positiv = Forderung, negativ = Ausgleich
    saldo: float


@router.get("/{kunde_id}/kontokorrent", response_model=list[KontokorrentBewegung])
def kontokorrent_kunde(kunde_id: int, db: Session = Depends(get_db)):
    kunde = db.query(Kunde).filter(Kunde.id == kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")

    bewegungen: list[dict] = []

    # Ausgangsrechnungen, Gutschriften, Stornorechnungen dieses Kunden
    rechnungen = (
        db.query(Rechnung)
        .filter(
            Rechnung.kunde_id == kunde_id,
            Rechnung.typ == "ausgang",
            Rechnung.ist_entwurf == False,
            Rechnung.dokument_typ.in_(["Rechnung", "Gutschrift", "Stornorechnung"]),
        )
        .all()
    )
    rechnung_ids = {r.id for r in rechnungen}

    for r in rechnungen:
        if r.dokument_typ == "Rechnung":
            typ = "rechnung"
            betrag = float(r.brutto_gesamt)
        elif r.dokument_typ == "Gutschrift":
            typ = "gutschrift"
            betrag = -float(r.brutto_gesamt)
        else:  # Stornorechnung
            typ = "storno"
            betrag = -float(r.brutto_gesamt)
        datum = r.ausgegeben_am.date() if r.ausgegeben_am else r.datum
        bewegungen.append({
            "datum": str(datum),
            "typ": typ,
            "belegnr": r.rechnungsnummer or str(r.id),
            "beschreibung": f"{r.dokument_typ} {r.rechnungsnummer or '—'}",
            "betrag": betrag,
        })

    # Zahlungseingänge aus dem Journal
    zahlungen = (
        db.query(Journaleintrag)
        .filter(
            Journaleintrag.rechnung_id.in_(rechnung_ids),
            Journaleintrag.art == "Einnahme",
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


def _kontokorrent_bewegungen(
    kunde_id: int, von: _date, bis: _date, db: Session
) -> tuple[list[dict], str]:
    """Gibt (bewegungen_dicts, partner_name) zurück, gefiltert nach Zeitraum."""
    kunde = db.query(Kunde).filter(Kunde.id == kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")
    partner_name = (
        kunde.firmenname
        or " ".join(t for t in [kunde.vorname, kunde.nachname] if t)
        or f"Kunde #{kunde_id}"
    )

    rechnungen = (
        db.query(Rechnung)
        .filter(
            Rechnung.kunde_id == kunde_id,
            Rechnung.typ == "ausgang",
            Rechnung.ist_entwurf == False,
            Rechnung.dokument_typ.in_(["Rechnung", "Gutschrift", "Stornorechnung"]),
        )
        .all()
    )
    rechnung_ids = {r.id for r in rechnungen}

    raw: list[dict] = []
    for r in rechnungen:
        if r.dokument_typ == "Rechnung":
            typ, betrag = "rechnung", float(r.brutto_gesamt)
        elif r.dokument_typ == "Gutschrift":
            typ, betrag = "gutschrift", -float(r.brutto_gesamt)
        else:
            typ, betrag = "storno", -float(r.brutto_gesamt)
        datum = (r.ausgegeben_am.date() if r.ausgegeben_am else r.datum)
        if not (von <= datum <= bis):
            continue
        raw.append({
            "datum": str(datum), "typ": typ,
            "belegnr": r.rechnungsnummer or str(r.id),
            "beschreibung": f"{r.dokument_typ} {r.rechnungsnummer or '—'}",
            "betrag": betrag,
        })

    zahlungen = (
        db.query(Journaleintrag)
        .filter(
            Journaleintrag.rechnung_id.in_(rechnung_ids),
            Journaleintrag.art == "Einnahme",
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


@router.get("/{kunde_id}/kontokorrent/pdf")
def kontokorrent_pdf(
    kunde_id: int,
    von: _date = None,
    bis: _date = None,
    db: Session = Depends(get_db),
):
    if not von:
        von = _date((_date.today().year), 1, 1)
    if not bis:
        bis = _date.today()
    bewegungen, partner_name = _kontokorrent_bewegungen(kunde_id, von, bis, db)
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


class KontokorrentMailRequest(BaseModel):
    an: str
    cc: Optional[str] = None
    betreff: str
    text: str
    von: Optional[_date] = None
    bis: Optional[_date] = None


@router.post("/{kunde_id}/kontokorrent/mail")
def kontokorrent_mail(
    kunde_id: int,
    data: KontokorrentMailRequest,
    db: Session = Depends(get_db),
):
    from .mail import _build_message, _smtp_einstellungen, _sende
    von = data.von or _date(_date.today().year, 1, 1)
    bis = data.bis or _date.today()
    bewegungen, partner_name = _kontokorrent_bewegungen(kunde_id, von, bis, db)
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
    dump = data.model_dump(exclude_none=True)
    neue_nr = dump.get("kundennummer")
    if neue_nr and neue_nr != kunde.kundennummer:
        if db.query(Kunde).filter(Kunde.kundennummer == neue_nr, Kunde.id != kunde_id).first():
            raise HTTPException(status_code=409, detail=f"Kundennummer '{neue_nr}' ist bereits vergeben.")
    neue_debitor = dump.get("debitor_nr")
    if neue_debitor and neue_debitor != kunde.debitor_nr:
        if db.query(Kunde).filter(Kunde.debitor_nr == neue_debitor, Kunde.id != kunde_id).first():
            raise HTTPException(status_code=409, detail=f"Debitorennummer '{neue_debitor}' ist bereits vergeben.")
    for key, value in dump.items():
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
        db.query(Journaleintrag).filter(Journaleintrag.kunde_id == kunde_id).count() > 0
    )
    if hat_rechnungen or hat_buchungen:
        raise HTTPException(
            status_code=409,
            detail="Kunde hat verknüpfte Rechnungen oder Journaleinträge. "
                   "Bitte 'Anonymisieren (DSGVO)' verwenden.",
        )
    db.delete(kunde)
    db.commit()
