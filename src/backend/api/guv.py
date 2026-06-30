"""
GuV – Gewinn- und Verlustrechnung (Näherung auf Basis von EÜR-Daten)

§ 141 AO Buchführungspflicht für Einzelgewerbetreibende:
  - Umsatz > 800.000 € ODER Gewinn > 80.000 € → doppelte Buchführung erforderlich
  - Freiberufler sind von § 141 AO ausgenommen (gilt nur für Gewerbetreibende)

Jahresergebnis der GuV ≠ steuerlicher EÜR-Gewinn:
  EÜR enthält vereinnahmte USt (Zeile 17) als Einnahme und abziehbare Vorsteuer (Zeile 57)
  als Ausgabe. In der GuV sind beide Posten Durchlaufposten und werden ausgeblendet.
"""

import datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Unternehmen

router = APIRouter(prefix="/api/guv", tags=["GuV"])

ZERO = Decimal("0.00")
Q    = Decimal("0.01")

# §141 AO Schwellenwerte
UMSATZ_GRENZE   = Decimal("800000.00")
GEWINN_GRENZE   = Decimal("80000.00")
WARNUNG_PROZENT = Decimal("0.80")

# GuV-Positionen: (nr, bezeichnung, typ, euer_zeilen)
# typ: "ertrag" = Einnahmen-Seite, "aufwand" = Ausgaben-Seite
GUV_POSITIONEN = [
    (1, "Umsatzerlöse",                              "ertrag",  [12, 15, 16]),
    (2, "Sonstige betriebliche Erträge",              "ertrag",  [18, 20, 21]),
    (3, "Materialaufwand",                            "aufwand", [27, 28, 29]),
    (4, "Personalaufwand",                            "aufwand", [30]),
    (5, "Abschreibungen",                             "aufwand", [36]),
    # Zeile 56 (Schuldzinsen) bewusst in sonstige Aufwendungen – kein eigener Finanzaufwand-Ausweis
    (6, "Sonstige betriebliche Aufwendungen",         "aufwand", [39, 41, 43, 44, 46, 47, 49, 51, 52, 54, 56, 58, 60, 63, 65, 68, 69, 70]),
]

# Zeilen 17 (vereinnahmte USt) und 57 (Vorsteuer) sind Steuer-Durchlaufposten →
# in der GuV nicht auszuweisen; Zeilen 106/107 sind Eigenkapitalbewegungen.
_GUV_AUSGESCHLOSSEN = {17, 57, 106, 107}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class GUVPosition(BaseModel):
    nr: int
    bezeichnung: str
    typ: str  # "ertrag" | "aufwand"
    betrag: str


class GUVErgebnis(BaseModel):
    jahr: int
    positionen: list[GUVPosition]
    summe_ertraege: str
    summe_aufwendungen: str
    jahresergebnis: str


class GUVSchwellenwert(BaseModel):
    jahr: int
    umsatz_aktuell: str
    gewinn_aktuell: str
    umsatz_grenze: str
    gewinn_grenze: str
    umsatz_prozent: float
    gewinn_prozent: float
    warnung_aktiv: bool
    grenze_erreicht: bool
    guv_aktiv: bool


# ---------------------------------------------------------------------------
# Endpunkte
# ---------------------------------------------------------------------------

@router.get("/berechnen", response_model=GUVErgebnis)
def berechne_guv(jahr: int = Query(...), db: Session = Depends(get_db)):
    from api.euer import _berechne_euer
    euer = _berechne_euer(jahr, db)
    zeilen: dict[int, Decimal] = euer["zeilen"]

    positionen: list[GUVPosition] = []
    for nr, bezeichnung, typ, euer_zeilen in GUV_POSITIONEN:
        betrag = sum(zeilen.get(z, ZERO) for z in euer_zeilen).quantize(Q, ROUND_HALF_UP)
        positionen.append(GUVPosition(nr=nr, bezeichnung=bezeichnung, typ=typ, betrag=str(betrag)))

    summe_ertraege     = sum(Decimal(p.betrag) for p in positionen if p.typ == "ertrag").quantize(Q, ROUND_HALF_UP)
    summe_aufwendungen = sum(Decimal(p.betrag) for p in positionen if p.typ == "aufwand").quantize(Q, ROUND_HALF_UP)
    jahresergebnis     = (summe_ertraege - summe_aufwendungen).quantize(Q, ROUND_HALF_UP)

    return GUVErgebnis(
        jahr=jahr,
        positionen=positionen,
        summe_ertraege=str(summe_ertraege),
        summe_aufwendungen=str(summe_aufwendungen),
        jahresergebnis=str(jahresergebnis),
    )


@router.get("/schwellenwert", response_model=GUVSchwellenwert)
def guv_schwellenwert(db: Session = Depends(get_db)):
    """§141 AO Schwellenwert-Prüfung für das laufende Kalenderjahr.

    Setzt guv_aktiv automatisch auf True wenn Schwellenwert überschritten und
    taetigkeitsart gewerbe|gemischt. Freiberufler fallen nicht unter §141 AO.
    """
    from api.euer import _berechne_euer

    jahr = datetime.date.today().year
    euer = _berechne_euer(jahr, db)
    zeilen: dict[int, Decimal] = euer["zeilen"]
    gewinn: Decimal = euer["gewinn_verlust"]

    # Netto-Umsatz ohne USt-Durchlaufposten
    umsatz = sum(zeilen.get(z, ZERO) for z in [12, 15, 16]).quantize(Q, ROUND_HALF_UP)

    umsatz_prozent = float(umsatz / UMSATZ_GRENZE) if umsatz > ZERO else 0.0
    gewinn_prozent = float(gewinn / GEWINN_GRENZE)  if gewinn > ZERO else 0.0

    grenze_erreicht = umsatz >= UMSATZ_GRENZE or gewinn >= GEWINN_GRENZE
    warnung_aktiv   = (
        umsatz >= UMSATZ_GRENZE * WARNUNG_PROZENT
        or gewinn >= GEWINN_GRENZE * WARNUNG_PROZENT
    )

    unt = db.query(Unternehmen).filter(Unternehmen.id == 1).first()
    if unt and grenze_erreicht and not unt.guv_aktiv:
        if unt.taetigkeitsart in ("gewerbe", "gemischt"):
            unt.guv_aktiv = True
            db.commit()

    return GUVSchwellenwert(
        jahr=jahr,
        umsatz_aktuell=str(umsatz),
        gewinn_aktuell=str(gewinn),
        umsatz_grenze=str(UMSATZ_GRENZE),
        gewinn_grenze=str(GEWINN_GRENZE),
        umsatz_prozent=round(umsatz_prozent, 4),
        gewinn_prozent=round(gewinn_prozent, 4),
        warnung_aktiv=warnung_aktiv,
        grenze_erreicht=grenze_erreicht,
        guv_aktiv=unt.guv_aktiv if unt else False,
    )
