"""
Inventurliste – Bestandsliste zum Stichtag für alle Artikel mit aktiver Lagerführung
(§240 HGB, "schlanke Variante": reine Dokumentation von Menge und Wert, kein
Soll-/Ist-Zählworkflow mit Korrekturbuchung - Abweichungen werden weiterhin über eine
normale manuelle Bestandskorrektur erfasst).

stichtag ist rein für die Beschriftung des Dokuments gedacht - bestand_aktuell ist immer
der aktuelle Bestand (keine Bestandshistorie), das Feld dokumentiert also "Bestand zum
Zeitpunkt des Exports", nicht rückwirkend einen früheren Bestand.
"""

import csv
import io
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Artikel, Unternehmen

router = APIRouter(prefix="/api/inventurliste", tags=["Inventurliste"])

Q = Decimal("0.01")


class InventurZeile(BaseModel):
    artikel_id: int
    artikelnummer: str
    bezeichnung: str
    einheit: str
    bestand: str
    ek_netto: str | None
    wert: str | None


class InventurlisteErgebnis(BaseModel):
    stichtag: date
    zeilen: list[InventurZeile]
    gesamtwert: str


def _inventur_zeilen(db: Session) -> list[InventurZeile]:
    artikel = (
        db.query(Artikel)
        .filter(Artikel.lager_aktiv == True, Artikel.aktiv == True)  # noqa: E712
        .order_by(Artikel.artikelnummer)
        .all()
    )
    zeilen = []
    for a in artikel:
        wert = (a.bestand_aktuell * a.ek_netto).quantize(Q, ROUND_HALF_UP) if a.ek_netto is not None else None
        zeilen.append(InventurZeile(
            artikel_id=a.id,
            artikelnummer=a.artikelnummer,
            bezeichnung=a.bezeichnung,
            einheit=a.einheit,
            bestand=str(a.bestand_aktuell),
            ek_netto=str(a.ek_netto.quantize(Q, ROUND_HALF_UP)) if a.ek_netto is not None else None,
            wert=str(wert) if wert is not None else None,
        ))
    return zeilen


@router.get("/berechnen", response_model=InventurlisteErgebnis)
def berechne_inventurliste(stichtag: date = Query(default_factory=date.today), db: Session = Depends(get_db)):
    zeilen = _inventur_zeilen(db)
    gesamtwert = sum((Decimal(z.wert) for z in zeilen if z.wert is not None), Decimal("0"))
    return InventurlisteErgebnis(stichtag=stichtag, zeilen=zeilen, gesamtwert=str(gesamtwert.quantize(Q, ROUND_HALF_UP)))


@router.get("/export")
def inventurliste_export(
    stichtag: date = Query(default_factory=date.today),
    format: str = Query("pdf", description="pdf oder csv"),
    db: Session = Depends(get_db),
):
    zeilen = _inventur_zeilen(db)

    if format == "csv":
        out = io.StringIO()
        writer = csv.writer(out, delimiter=";")
        writer.writerow(["Artikelnr.", "Bezeichnung", "Bestand", "Einheit", "EK-Preis (netto)", "Wert (netto)"])
        for z in zeilen:
            writer.writerow([
                z.artikelnummer, z.bezeichnung, z.bestand, z.einheit,
                f"{Decimal(z.ek_netto):.2f}".replace(".", ",") if z.ek_netto is not None else "",
                f"{Decimal(z.wert):.2f}".replace(".", ",") if z.wert is not None else "",
            ])
        csv_bytes = ("﻿" + out.getvalue()).encode("utf-8")
        return Response(
            content=csv_bytes,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="Inventurliste_{stichtag}.csv"'},
        )

    unt = db.query(Unternehmen).filter(Unternehmen.id == 1).first()
    unt_dict = {
        "firmenname": unt.firmenname if unt else "",
        "vorname": unt.vorname if unt else "",
        "nachname": unt.nachname if unt else "",
        "strasse": unt.strasse if unt else "",
        "hausnummer": unt.hausnummer if unt else "",
        "plz": unt.plz if unt else "",
        "ort": unt.ort if unt else "",
        "steuernummer": unt.steuernummer if unt else "",
    }

    from utils.pdf_inventurliste import erstelle_inventurliste_pdf
    pdf_bytes = erstelle_inventurliste_pdf(unt_dict, [z.model_dump() for z in zeilen], stichtag)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Inventurliste_{stichtag}.pdf"'},
    )
