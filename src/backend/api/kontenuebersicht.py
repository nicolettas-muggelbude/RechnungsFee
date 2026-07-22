"""
Kontenübersicht – Summenliste aller gebuchten Kategorien mit Kontonummer (Issue #255)

Zeigt, im Unterschied zum Journal-Filter (Kontenblatt zu EINEM Konto), alle
Kategorien auf einen Blick mit der aktuell hinterlegten Kontonummer, Anzahl
Buchungen und Summe im gewählten Zeitraum.

Die Kontonummern-Spalte wird über unternehmen.kontenrahmen dynamisch gewählt
(aktuell SKR03/SKR04, konto_skr49 ist als Spalte reserviert für einen künftigen
weiteren Kontenplan – noch nicht produktiv befüllt).
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
from database.models import Journaleintrag, Kategorie, Unternehmen

router = APIRouter(prefix="/api/kontenuebersicht", tags=["Kontenübersicht"])

Q = Decimal("0.01")

_KONTO_SPALTEN = {
    "SKR03": Kategorie.konto_skr03,
    "SKR04": Kategorie.konto_skr04,
    "SKR49": Kategorie.konto_skr49,
}


class KontenuebersichtZeile(BaseModel):
    kategorie_id: int
    kategorie_name: str
    kontonummer: str | None
    anzahl: int
    summe: str


class KontenuebersichtErgebnis(BaseModel):
    kontenrahmen: str
    von: date
    bis: date
    zeilen: list[KontenuebersichtZeile]


def _kontenuebersicht_zeilen(von: date, bis: date, db: Session) -> tuple[str, list[KontenuebersichtZeile]]:
    unt = db.query(Unternehmen).filter(Unternehmen.id == 1).first()
    skr = (unt.kontenrahmen if unt else None) or "SKR04"
    konto_spalte_attr = "konto_skr03" if skr == "SKR03" else "konto_skr49" if skr == "SKR49" else "konto_skr04"

    eintraege = (
        db.query(Journaleintrag)
        .filter(Journaleintrag.datum >= von, Journaleintrag.datum <= bis, Journaleintrag.kategorie_id.isnot(None))
        .all()
    )

    # Ein Storno behält dieselbe Kategorie und denselben (positiven) Betrag, nur die Art
    # dreht sich um (s. journal.py update_eintrag). Bei einer naiven Summe ohne Art-Filter
    # würde eine stornierte Buchung doppelt statt netto null zählen – daher werden Storno-
    # Gegenbuchungen UND die dadurch stornierten Original-Buchungen ausgeschlossen.
    gruppen_ids = {e.gruppe_id for e in eintraege if e.gruppe_id is not None}
    aktive = [
        e for e in eintraege
        if not e.beschreibung.startswith("STORNO ") and e.id not in gruppen_ids
    ]

    gruppen: dict[int, dict] = {}
    for e in aktive:
        kat: Kategorie | None = e.kategorie
        if not kat:
            continue
        g = gruppen.setdefault(kat.id, {
            "name": kat.name,
            "kontonummer": getattr(kat, konto_spalte_attr),
            "anzahl": 0,
            "summe": Decimal("0"),
        })
        g["anzahl"] += 1
        g["summe"] += e.brutto_betrag

    zeilen = [
        KontenuebersichtZeile(
            kategorie_id=kat_id,
            kategorie_name=g["name"],
            kontonummer=g["kontonummer"],
            anzahl=g["anzahl"],
            summe=str(g["summe"].quantize(Q, ROUND_HALF_UP)),
        )
        for kat_id, g in gruppen.items()
    ]
    zeilen.sort(key=lambda z: (z.kontonummer is None, z.kontonummer or "", z.kategorie_name))
    return skr, zeilen


@router.get("/berechnen", response_model=KontenuebersichtErgebnis)
def berechne_kontenuebersicht(von: date = Query(...), bis: date = Query(...), db: Session = Depends(get_db)):
    skr, zeilen = _kontenuebersicht_zeilen(von, bis, db)
    return KontenuebersichtErgebnis(kontenrahmen=skr, von=von, bis=bis, zeilen=zeilen)


@router.get("/export")
def kontenuebersicht_export(
    von: date = Query(...),
    bis: date = Query(...),
    format: str = Query("pdf", description="pdf oder csv"),
    db: Session = Depends(get_db),
):
    skr, zeilen = _kontenuebersicht_zeilen(von, bis, db)
    jahr = von.year if von.year == bis.year else None
    datei_suffix = str(jahr) if jahr else f"{von}_{bis}"

    if format == "csv":
        out = io.StringIO()
        writer = csv.writer(out, delimiter=";")
        writer.writerow(["Kategorie", "Konto", "Buchungen", "Summe (EUR)"])
        for z in zeilen:
            writer.writerow([
                z.kategorie_name, z.kontonummer or "",
                z.anzahl, f"{Decimal(z.summe):.2f}".replace(".", ","),
            ])
        csv_bytes = ("﻿" + out.getvalue()).encode("utf-8")
        return Response(
            content=csv_bytes,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="Kontenuebersicht_{datei_suffix}.csv"'},
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

    from utils.pdf_kontenuebersicht import erstelle_kontenuebersicht_pdf
    pdf_bytes = erstelle_kontenuebersicht_pdf(
        unt_dict, [z.model_dump() for z in zeilen], jahr or von.year, skr,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Kontenuebersicht_{datei_suffix}.pdf"'},
    )
