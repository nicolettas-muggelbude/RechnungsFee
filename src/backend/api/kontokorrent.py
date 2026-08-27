"""
Kontokorrent-Übersicht: alle Kunden und Lieferanten mit offenem Saldo (Forderung
oder Guthaben) auf einen Blick, statt jeden Partner einzeln öffnen zu müssen.

Nutzt bewusst dieselben Funktionen wie die bestehende Einzelansicht
(kontokorrent_kunde/kontokorrent_lieferant), statt die Saldo-Berechnung ein
zweites Mal nachzubauen - Korrektheit/Konsistenz hat hier Vorrang vor
Performance, die Seite wird manuell geöffnet und ist kein Hot Path.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Kunde, Lieferant
from .kunden import kontokorrent_kunde
from .lieferanten import kontokorrent_lieferant

router = APIRouter(prefix="/api/kontokorrent", tags=["Kontokorrent"])


class PartnerSaldo(BaseModel):
    partner_typ: str  # kunde | lieferant
    partner_id: int
    name: str
    saldo: float
    status: str  # offen | guthaben


def _name(firmenname: str | None, vorname: str | None, nachname: str | None) -> str:
    return firmenname or f"{vorname or ''} {nachname or ''}".strip() or "-"


@router.get("/uebersicht", response_model=list[PartnerSaldo])
def kontokorrent_uebersicht(db: Session = Depends(get_db)):
    ergebnis: list[PartnerSaldo] = []

    for k in db.query(Kunde).all():
        bewegungen = kontokorrent_kunde(k.id, db)
        saldo = bewegungen[-1].saldo if bewegungen else 0.0
        if round(saldo, 2) == 0:
            continue
        ergebnis.append(PartnerSaldo(
            partner_typ="kunde", partner_id=k.id,
            name=_name(k.firmenname, k.vorname, k.nachname),
            saldo=saldo, status="offen" if saldo > 0 else "guthaben",
        ))

    for l in db.query(Lieferant).all():
        bewegungen = kontokorrent_lieferant(l.id, db)
        saldo = bewegungen[-1].saldo if bewegungen else 0.0
        if round(saldo, 2) == 0:
            continue
        ergebnis.append(PartnerSaldo(
            partner_typ="lieferant", partner_id=l.id,
            name=_name(l.firmenname, l.vorname, l.nachname),
            saldo=saldo, status="offen" if saldo > 0 else "guthaben",
        ))

    ergebnis.sort(key=lambda p: abs(p.saldo), reverse=True)
    return ergebnis
