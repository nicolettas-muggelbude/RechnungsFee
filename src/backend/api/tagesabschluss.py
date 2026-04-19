"""
Tagesabschluss-API (GoBD-konform, unveränderbar).
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Tagesabschluss, Kassenbucheintrag, Unternehmen
from .schemas import TagesabschlussCreate, TagesabschlussResponse, TagesabschlussVorschau
from utils.signatur import signatur_tagesabschluss
from utils.pdf_tagesabschluss import generate_tagesabschluss_pdf

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


@router.get("/fehlt-gestern")
def fehlt_gestern(db: Session = Depends(get_db)):
    """Prüft ob für gestern ein Tagesabschluss fehlt.
    Gibt nur fehlt=True zurück wenn gestern tatsächlich Buchungen existieren –
    verhindert Fehlalarm bei Ersteinrichtung."""
    gestern = date.today() - timedelta(days=1)
    hat_buchungen = (
        db.query(func.count(Kassenbucheintrag.id))
        .filter(Kassenbucheintrag.datum == gestern)
        .scalar() or 0
    ) > 0
    if not hat_buchungen:
        return {"datum": str(gestern), "fehlt": False}
    existiert = (
        db.query(Tagesabschluss)
        .filter(Tagesabschluss.datum == gestern)
        .first()
    ) is not None
    return {"datum": str(gestern), "fehlt": not existiert}


@router.get("/vorschau/{datum}", response_model=TagesabschlussVorschau)
def vorschau(datum: date, db: Session = Depends(get_db)):
    """Liefert Vorschau-Daten ohne zu speichern."""
    return _berechne_vorschau(datum, db)


@router.get("/export/pdf")
def export_pdf(
    zeitraum: str = Query("alle", description="monat | jahr | alle"),
    wert: str | None = Query(None, description="2026-02 (Monat) oder 2026 (Jahr)"),
    db: Session = Depends(get_db),
):
    """
    Exportiert Tagesabschlüsse als PDF.
    zeitraum=monat&wert=2026-02  → Februar 2026
    zeitraum=jahr&wert=2026      → ganzes Jahr 2026
    zeitraum=alle                → alle vorhandenen
    """
    q = db.query(Tagesabschluss)
    zeitraum_label = "Alle Abschlüsse"
    dateiname_suffix = "gesamt"

    if zeitraum == "monat" and wert:
        try:
            jahr, monat = wert.split("-")
            q = q.filter(
                extract("year", Tagesabschluss.datum) == int(jahr),
                extract("month", Tagesabschluss.datum) == int(monat),
            )
            monate = ["Januar", "Februar", "März", "April", "Mai", "Juni",
                      "Juli", "August", "September", "Oktober", "November", "Dezember"]
            zeitraum_label = f"{monate[int(monat) - 1]} {jahr}"
            dateiname_suffix = wert  # z.B. 2026-02
        except Exception:
            raise HTTPException(status_code=400, detail="Ungültiger Monatswert (erwartet: YYYY-MM).")
    elif zeitraum == "jahr" and wert:
        try:
            q = q.filter(extract("year", Tagesabschluss.datum) == int(wert))
            zeitraum_label = f"Jahr {wert}"
            dateiname_suffix = wert
        except Exception:
            raise HTTPException(status_code=400, detail="Ungültiger Jahreswert (erwartet: YYYY).")
    elif zeitraum == "tag" and wert:
        try:
            q = q.filter(Tagesabschluss.datum == wert)
            tag_dt = wert.split("-")
            zeitraum_label = f"{tag_dt[2]}.{tag_dt[1]}.{tag_dt[0]}"
            dateiname_suffix = wert
        except Exception:
            raise HTTPException(status_code=400, detail="Ungültiger Tageswert (erwartet: YYYY-MM-DD).")

    abschluesse_db = q.order_by(Tagesabschluss.datum.asc()).all()
    if not abschluesse_db:
        raise HTTPException(status_code=404, detail="Keine Tagesabschlüsse für den gewählten Zeitraum gefunden.")

    # Unternehmensdaten laden
    unt = db.query(Unternehmen).first()
    unt_dict = {}
    if unt:
        unt_dict = {
            "firmenname": unt.firmenname,
            "vorname": unt.vorname or "",
            "nachname": unt.nachname or "",
            "strasse": unt.strasse,
            "hausnummer": unt.hausnummer,
            "plz": unt.plz,
            "ort": unt.ort,
            "steuernummer": unt.steuernummer or "",
            "ust_idnr": unt.ust_idnr or "",
            "unterschrift_bild": unt.unterschrift_bild or "",
        }

    # Abschlüsse als dicts
    abschluss_dicts = [
        {
            "datum": str(a.datum),
            "uhrzeit": str(a.uhrzeit),
            "anfangsbestand": a.anfangsbestand,
            "einnahmen_bar": a.einnahmen_bar,
            "ausgaben_bar": a.ausgaben_bar,
            "soll_endbestand": a.soll_endbestand,
            "ist_endbestand": a.ist_endbestand,
            "differenz": a.differenz,
            "differenz_begruendung": a.differenz_begruendung,
            "differenz_buchungsart": a.differenz_buchungsart,
            "zaehlung_json": a.zaehlung_json,
            "kassenbewegungen_anzahl": a.kassenbewegungen_anzahl,
            "signatur": a.signatur,
        }
        for a in abschluesse_db
    ]

    pdf_bytes = generate_tagesabschluss_pdf(abschluss_dicts, unt_dict, zeitraum_label)
    dateiname = f"Tagesabschluesse_{dateiname_suffix}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{dateiname}"'},
    )


@router.get("/{abschluss_id}/pruefen")
def pruefen_signatur(abschluss_id: int, db: Session = Depends(get_db)):
    """Prüft die SHA-256-Signatur eines Tagesabschlusses auf Integrität."""
    abschluss = db.query(Tagesabschluss).filter(Tagesabschluss.id == abschluss_id).first()
    if not abschluss:
        raise HTTPException(status_code=404, detail="Tagesabschluss nicht gefunden.")
    berechnet = signatur_tagesabschluss(abschluss)
    return {
        "id": abschluss.id,
        "gueltig": abschluss.signatur == berechnet,
        "gespeichert": abschluss.signatur,
        "berechnet": berechnet,
    }


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
        zaehlung_json=data.zaehlung_json,
        kassenbewegungen_anzahl=vorschau_daten["kassenbewegungen_anzahl"],
        immutable=True,
    )
    abschluss.signatur = signatur_tagesabschluss(abschluss)
    db.add(abschluss)
    db.commit()
    db.refresh(abschluss)
    return abschluss
