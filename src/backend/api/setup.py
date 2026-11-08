"""
Setup-Status-Endpunkt – wird beim App-Start abgefragt um zu entscheiden,
ob der Einrichtungs-Assistent gezeigt werden soll.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

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


KU_GRENZE_VORJAHR = Decimal("25000")
KU_GRENZE_LAUFEND = Decimal("100000")
KU_GRENZE_GRUENDUNGSJAHR = Decimal("25000")
KU_WARNSCHWELLE = Decimal("0.8")


def _umsatz_extern(unt: Optional[Unternehmen], jahr: int) -> Decimal:
    """Umsatz vor RechnungsFee (Stammdaten) für ein Kalenderjahr - nur Startjahr und Vorjahr."""
    if not unt or not unt.umsatz_extern_jahr:
        return Decimal("0")
    if jahr == unt.umsatz_extern_jahr:
        return Decimal(unt.umsatz_extern_startjahr or 0)
    if jahr == unt.umsatz_extern_jahr - 1:
        return Decimal(unt.umsatz_extern_vorjahr or 0)
    return Decimal("0")


@router.get("/kleinunternehmer-umsatz")
def kleinunternehmer_umsatz(db: Session = Depends(get_db), heute: Optional[date] = None):
    """Kleinunternehmergrenze nach § 19 UStG (seit 2025) für die Dashboard-Warnung (Issue #491).

    Gesamtumsatz nach vereinnahmten Entgelten aus der EÜR-Zuordnung (inkl. Journal-Einnahmen,
    ohne nicht steuerbare und § 4-steuerfreie Umsätze, ohne Anlagevermögen) zuzüglich des in
    den Stammdaten eingetragenen Umsatzes vor RechnungsFee.
    - Gründungsjahr (Beginn der Tätigkeit im laufenden Jahr): 25.000 €, keine Hochrechnung
    - sonst laufendes Jahr: 100.000 €; Vorjahr über 25.000 € → § 19 gilt im laufenden Jahr nicht
    Wer die Grenze im laufenden Jahr überschreitet, ist ab diesem Umsatz regelbesteuert.
    `heute` nur für Tests."""
    from .euer import kleinunternehmer_gesamtumsatz

    jahr = (heute or date.today()).year
    unt = db.query(Unternehmen).first()
    beginn = unt.taetigkeit_beginn if unt else None
    ist_gruendungsjahr = bool(beginn and beginn.year == jahr)

    umsatz = kleinunternehmer_gesamtumsatz(jahr, db) + _umsatz_extern(unt, jahr)
    grenze = KU_GRENZE_GRUENDUNGSJAHR if ist_gruendungsjahr else KU_GRENZE_LAUFEND

    # Vorjahr nur prüfen, wenn es eines gab (nicht im Gründungsjahr, nicht vor dem Beginn)
    vorjahr_relevant = not ist_gruendungsjahr and not (beginn and beginn.year > jahr - 1)
    umsatz_vorjahr = (
        kleinunternehmer_gesamtumsatz(jahr - 1, db) + _umsatz_extern(unt, jahr - 1)
        if vorjahr_relevant else Decimal("0")
    )

    return {
        "jahr": jahr,
        "umsatz_netto": float(umsatz),
        "grenze_kritisch": float(grenze),
        "grenze_warnung": float(grenze * KU_WARNSCHWELLE),
        "ist_gruendungsjahr": ist_gruendungsjahr,
        "umsatz_extern": float(_umsatz_extern(unt, jahr)),
        "vorjahr": jahr - 1,
        "umsatz_vorjahr": float(umsatz_vorjahr),
        "grenze_vorjahr": float(KU_GRENZE_VORJAHR),
        "vorjahr_ueberschritten": vorjahr_relevant and umsatz_vorjahr > KU_GRENZE_VORJAHR,
    }
