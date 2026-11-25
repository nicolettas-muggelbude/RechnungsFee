"""
Issue #596: Dokumentverlauf – Meldungen des Frontends (Drucken/PDF, Übergabe an Thunderbird oder
das Standard-Mailprogramm) und Verlauf je Kunde/Lieferant. SMTP-Versand protokolliert api/mail.py
selbst. Logik in utils/dokument_verlauf.py.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import DokumentVerlauf, Kunde, Lieferant, Mahnung, Rechnung
from api.schemas_rechnungen import VerlaufEintrag
from utils.dokument_verlauf import protokolliere, protokolliere_mahnung

router = APIRouter(prefix="/api/verlauf", tags=["Dokumentverlauf"])

# Was das Frontend melden darf – „mail_gesendet“ (SMTP) nur über api/mail.py
_FRONTEND_ARTEN = {
    "gedruckt": {"druck"},
    "pdf": {"druck"},
    "mail_uebergeben": {"thunderbird", "mailprogramm"},
}
_FRONTEND_MAHNUNG_ARTEN = {
    "mahnung_gedruckt": {"druck"},
    "mahnung_uebergeben": {"thunderbird", "mailprogramm"},
}


class VerlaufMeldung(BaseModel):
    art: str
    kanal: str
    kopie: bool = False
    empfaenger: Optional[str] = None
    betreff: Optional[str] = None


def _pruefe(erlaubt: dict[str, set[str]], data: VerlaufMeldung) -> None:
    if data.kanal not in erlaubt.get(data.art, set()):
        raise HTTPException(status_code=422, detail=f"Unzulässiger Verlaufseintrag: {data.art}/{data.kanal}")


@router.post("/rechnung/{rechnung_id}", response_model=VerlaufEintrag, status_code=201)
def melde_rechnung(rechnung_id: int, data: VerlaufMeldung, db: Session = Depends(get_db)):
    r = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden.")
    if r.ist_entwurf:
        # Entwürfe sind nur Vorschau – nichts zu protokollieren
        raise HTTPException(status_code=409, detail="Entwürfe haben keinen Verlauf.")
    _pruefe(_FRONTEND_ARTEN, data)
    e = protokolliere(db, art=data.art, kanal=data.kanal, rechnung=r, kopie=data.kopie,
                      empfaenger=data.empfaenger, betreff=data.betreff)
    db.commit()
    db.refresh(e)
    return VerlaufEintrag.model_validate(e)


@router.post("/mahnung/{mahnung_id}", response_model=list[VerlaufEintrag], status_code=201)
def melde_mahnung(mahnung_id: int, data: VerlaufMeldung, db: Session = Depends(get_db)):
    m = db.query(Mahnung).filter(Mahnung.id == mahnung_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Mahnung nicht gefunden.")
    _pruefe(_FRONTEND_MAHNUNG_ARTEN, data)
    eintraege = protokolliere_mahnung(db, m, art=data.art, kanal=data.kanal,
                                      empfaenger=data.empfaenger, betreff=data.betreff)
    db.commit()
    return [VerlaufEintrag.model_validate(e) for e in eintraege]


def _partner_verlauf(db: Session, filter_) -> list[VerlaufEintrag]:
    eintraege = (
        db.query(DokumentVerlauf).filter(filter_)
        .order_by(DokumentVerlauf.zeitpunkt.desc(), DokumentVerlauf.id.desc()).all()
    )
    r_ids = {e.rechnung_id for e in eintraege if e.rechnung_id}
    m_ids = {e.mahnung_id for e in eintraege if e.mahnung_id}
    rechnungen = {r.id: r for r in db.query(Rechnung).filter(Rechnung.id.in_(r_ids)).all()} if r_ids else {}
    mahnungen = {m.id: m for m in db.query(Mahnung).filter(Mahnung.id.in_(m_ids)).all()} if m_ids else {}
    ergebnis = []
    for e in eintraege:
        v = VerlaufEintrag.model_validate(e)
        r = rechnungen.get(e.rechnung_id)
        if r:
            v.rechnungsnummer = r.rechnungsnummer
            v.dokument_typ = r.dokument_typ or "Rechnung"
        m = mahnungen.get(e.mahnung_id)
        if m:
            v.mahnnummer = m.mahnnummer
        ergebnis.append(v)
    return ergebnis


@router.get("/kunde/{kunde_id}", response_model=list[VerlaufEintrag])
def kunden_verlauf(kunde_id: int, db: Session = Depends(get_db)):
    if not db.query(Kunde).filter(Kunde.id == kunde_id).first():
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")
    return _partner_verlauf(db, DokumentVerlauf.kunde_id == kunde_id)


@router.get("/lieferant/{lieferant_id}", response_model=list[VerlaufEintrag])
def lieferanten_verlauf(lieferant_id: int, db: Session = Depends(get_db)):
    if not db.query(Lieferant).filter(Lieferant.id == lieferant_id).first():
        raise HTTPException(status_code=404, detail="Lieferant nicht gefunden.")
    return _partner_verlauf(db, DokumentVerlauf.lieferant_id == lieferant_id)
