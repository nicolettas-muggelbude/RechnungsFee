"""
Tagesabschluss-API (GoBD-konform, unveränderbar).
"""

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Tagesabschluss, Kassenbucheintrag
from .schemas import TagesabschlussCreate, TagesabschlussResponse, TagesabschlussVorschau

router = APIRouter(prefix="/api/tagesabschluss", tags=["Kassenbuch"])


def _berechne_vorschau(datum: date, db: Session) -> dict:
    """Berechnet Anfangsbestand und Bargeldbewegungen für ein Datum."""
    # Letzter Tagesabschluss vor dem Datum
    letzter = (
        db.query(Tagesabschluss)
        .filter(Tagesabschluss.datum < datum)
        .order_by(Tagesabschluss.datum.desc())
        .first()
    )
    anfangsbestand = letzter.ist_endbestand if letzter else Decimal("0")

    # Nur Barbuchungen des Tages
    einnahmen = (
        db.query(func.sum(Kassenbucheintrag.brutto_betrag))
        .filter(
            Kassenbucheintrag.datum == datum,
            Kassenbucheintrag.art == "Einnahme",
            Kassenbucheintrag.zahlungsart == "Bar",
        )
        .scalar()
        or Decimal("0")
    )
    ausgaben = (
        db.query(func.sum(Kassenbucheintrag.brutto_betrag))
        .filter(
            Kassenbucheintrag.datum == datum,
            Kassenbucheintrag.art == "Ausgabe",
            Kassenbucheintrag.zahlungsart == "Bar",
        )
        .scalar()
        or Decimal("0")
    )
    anzahl = (
        db.query(func.count(Kassenbucheintrag.id))
        .filter(Kassenbucheintrag.datum == datum)
        .scalar()
        or 0
    )
    soll_endbestand = (
        Decimal(str(anfangsbestand))
        + Decimal(str(einnahmen))
        - Decimal(str(ausgaben))
    )
    return {
        "datum": datum,
        "anfangsbestand": Decimal(str(anfangsbestand)),
        "einnahmen_bar": Decimal(str(einnahmen)),
        "ausgaben_bar": Decimal(str(ausgaben)),
        "soll_endbestand": soll_endbestand,
        "kassenbewegungen_anzahl": anzahl,
    }


@router.get("/vorschau/{datum}", response_model=TagesabschlussVorschau)
def vorschau(datum: date, db: Session = Depends(get_db)):
    """Liefert Vorschau-Daten ohne zu speichern."""
    return _berechne_vorschau(datum, db)


@router.get("", response_model=list[TagesabschlussResponse])
def list_tagesabschluesse(db: Session = Depends(get_db)):
    return (
        db.query(Tagesabschluss)
        .order_by(Tagesabschluss.datum.desc())
        .all()
    )


@router.post("", response_model=TagesabschlussResponse, status_code=201)
def create_tagesabschluss(data: TagesabschlussCreate, db: Session = Depends(get_db)):
    """Erstellt einen unveränderlichen Tagesabschluss."""
    if db.query(Tagesabschluss).filter(Tagesabschluss.datum == data.datum).first():
        raise HTTPException(
            status_code=409,
            detail=f"Für den {data.datum} existiert bereits ein Tagesabschluss.",
        )

    vorschau_daten = _berechne_vorschau(data.datum, db)
    differenz = data.ist_endbestand - vorschau_daten["soll_endbestand"]

    abschluss = Tagesabschluss(
        datum=data.datum,
        uhrzeit=datetime.now().strftime("%H:%M:%S"),
        anfangsbestand=vorschau_daten["anfangsbestand"],
        einnahmen_bar=vorschau_daten["einnahmen_bar"],
        ausgaben_bar=vorschau_daten["ausgaben_bar"],
        soll_endbestand=vorschau_daten["soll_endbestand"],
        ist_endbestand=data.ist_endbestand,
        differenz=differenz,
        differenz_begruendung=data.differenz_begruendung,
        differenz_buchungsart=data.differenz_buchungsart,
        kassenbewegungen_anzahl=vorschau_daten["kassenbewegungen_anzahl"],
        immutable=True,
    )
    db.add(abschluss)
    db.commit()
    db.refresh(abschluss)
    return abschluss
