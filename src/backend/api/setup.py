"""
Setup-Status-Endpunkt – wird beim App-Start abgefragt um zu entscheiden,
ob der Einrichtungs-Assistent gezeigt werden soll.
"""

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Unternehmen, Konto, Kategorie, Journaleintrag, Nummernkreis
from utils.signatur import signatur_journaleintrag
from .schemas import SetupStatus
from .journal import _naechste_belegnr

router = APIRouter(prefix="/api/setup", tags=["Setup"])


@router.get("/status", response_model=SetupStatus)
def get_setup_status(db: Session = Depends(get_db)):
    """
    Gibt zurück, ob die App bereits eingerichtet ist.
    Das Frontend zeigt beim ersten Start den Setup-Assistenten.
    """
    hat_unternehmen = db.query(Unternehmen).first() is not None
    hat_konto = db.query(Konto).filter(Konto.aktiv == True).first() is not None
    hat_kategorien = db.query(Kategorie).count() > 0

    return SetupStatus(
        ist_eingerichtet=hat_unternehmen and hat_konto,
        hat_unternehmen=hat_unternehmen,
        hat_konto=hat_konto,
        hat_kategorien=hat_kategorien,
    )


class KassenbestandRequest(BaseModel):
    betrag: Decimal


@router.post("/kassenbestand", status_code=201)
def set_kassenbestand(data: KassenbestandRequest, db: Session = Depends(get_db)):
    """
    Legt den einmaligen Kassenanfangsbestand als unveränderlichen Journaleintrag an.
    Wird nur beim Setup aufgerufen. Bereits vorhandene Einträge werden abgewiesen.
    """
    if data.betrag <= 0:
        return {"detail": "Betrag ist 0 – kein Eintrag angelegt."}

    # Doppelaufruf verhindern
    bereits = db.query(Journaleintrag).filter(
        Journaleintrag.beschreibung == "Kassenanfangsbestand"
    ).first()
    if bereits:
        raise HTTPException(status_code=409, detail="Kassenanfangsbestand wurde bereits gesetzt.")

    # Privateinlage-Kategorie suchen
    kat = db.query(Kategorie).filter(Kategorie.name == "Privateinlage").first()

    heute = date.today()
    belegnr = _naechste_belegnr(db, heute)

    eintrag = Journaleintrag(
        datum=heute,
        belegnr=belegnr,
        beschreibung="Kassenanfangsbestand",
        kategorie_id=kat.id if kat else None,
        zahlungsart="Bar",
        art="Einnahme",
        netto_betrag=data.betrag,
        ust_satz=Decimal("0"),
        ust_betrag=Decimal("0"),
        vorsteuer_betrag=Decimal("0"),
        brutto_betrag=data.betrag,
        vorsteuerabzug=False,
        immutable=True,
    )
    eintrag.signatur = signatur_journaleintrag(eintrag)
    db.add(eintrag)
    db.commit()
    return {"belegnr": belegnr, "betrag": str(data.betrag)}


@router.get("/kleinunternehmer-umsatz")
def kleinunternehmer_umsatz(db: Session = Depends(get_db)):
    """
    Netto-Jahresumsatz aus bezahlten Ausgangsrechnungen im laufenden Kalenderjahr.
    Nur relevant für Kleinunternehmer (§19 UStG).
    """
    from sqlalchemy import func, extract
    from database.models import Rechnung

    jahr = datetime.now().year
    ergebnis = db.query(func.sum(Rechnung.netto_gesamt)).filter(
        Rechnung.typ == "ausgang",
        Rechnung.ist_entwurf == False,
        Rechnung.storniert == False,
        Rechnung.zahlungsstatus.in_(["bezahlt", "teilweise"]),
        extract("year", Rechnung.datum) == jahr,
    ).scalar()

    umsatz = float(ergebnis or 0)
    return {
        "jahr": jahr,
        "umsatz_netto": umsatz,
        "grenze_kritisch": 100000.0,
        "grenze_warnung": 80000.0,
    }
