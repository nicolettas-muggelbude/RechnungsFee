"""
Zusammenfassende Meldung (ZM) – §18a UStG

Pflicht für alle USt-pflichtigen Unternehmer mit innergemeinschaftlichen
Lieferungen oder Dienstleistungen. Kleinunternehmer §19 sind befreit.

Kennzeichen:
  L = Innergemeinschaftliche Lieferung  (konto_skr03=8125)
  D = Innergemeinschaftliche Dienstleistung §13b Abs.1 (ust_sonderfall=13b_abs1)

Rhythmus / Frist:
  < 50.000 € ig. Lieferungen pro Quartal → quartalsweise, bis 25. des Folgemonats
  ≥ 50.000 € ig. Lieferungen pro Quartal → monatlich,    bis 25. des Folgemonats
"""

import calendar
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Journaleintrag, Rechnung, Kunde, Unternehmen

router = APIRouter(prefix="/api/zm", tags=["ZM"])

ZERO = Decimal("0.00")


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _zeitraum_grenzen(zeitraum: str) -> tuple[date, date, str]:
    if "-Q" in zeitraum:
        j, q = zeitraum.split("-Q")
        jahr, q = int(j), int(q)
        vm = (q - 1) * 3 + 1
        bm = vm + 2
        return date(jahr, vm, 1), date(jahr, bm, calendar.monthrange(jahr, bm)[1]), "quartal"
    j, m = zeitraum.split("-")
    jahr, monat = int(j), int(m)
    return date(jahr, monat, 1), date(jahr, monat, calendar.monthrange(jahr, monat)[1]), "monat"


def _deadline(zeitraum: str) -> date:
    if "-Q" in zeitraum:
        j, q = zeitraum.split("-Q")
        bm = int(q) * 3
        if bm == 12:
            return date(int(j) + 1, 1, 25)
        return date(int(j), bm + 1, 25)
    j, m = zeitraum.split("-")
    monat = int(m)
    if monat == 12:
        return date(int(j) + 1, 1, 25)
    return date(int(j), monat + 1, 25)


def _letztes_quartal(heute: date) -> str:
    q = (heute.month - 1) // 3  # laufendes Quartal 0-basiert
    if q == 0:
        return f"{heute.year - 1}-Q4"
    return f"{heute.year}-Q{q}"


def _zeitraum_label(zeitraum: str) -> str:
    MONATE = ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
              "Juli", "August", "September", "Oktober", "November", "Dezember"]
    if "-Q" in zeitraum:
        j, q = zeitraum.split("-Q")
        return f"Q{q}/{j}"
    j, m = zeitraum.split("-")
    return f"{MONATE[int(m)]} {j}"


def _ig_eintraege(von: date, bis: date, db: Session) -> list[Journaleintrag]:
    """Alle Journal-Einträge die in die ZM gehören."""
    return (
        db.query(Journaleintrag)
        .filter(
            Journaleintrag.datum >= von,
            Journaleintrag.datum <= bis,
            Journaleintrag.art == "Einnahme",
        )
        .filter(
            # ig. Lieferungen (KZ 41) ODER §13b Abs.1 Dienstleistungen
            (
                (Journaleintrag.konto_skr03.in_(["8125"])) |
                (Journaleintrag.konto_skr04.in_(["3125"])) |
                (Journaleintrag.ust_sonderfall == "13b_abs1")
            )
        )
        .all()
    )


def _kennzeichen(e: Journaleintrag) -> str:
    if getattr(e, "ust_sonderfall", None) == "13b_abs1":
        return "D"
    return "L"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ZMPosition(BaseModel):
    ust_idnr: str
    land: str
    kennzeichen: str          # L oder D
    betrag: Decimal

class ZMErgebnis(BaseModel):
    zeitraum: str
    zeitraum_label: str
    von: date
    bis: date
    deadline: date
    positionen: list[ZMPosition]
    gesamt: Decimal
    ueber_50k: bool           # → monatliche ZM erforderlich

class ZMPruefung(BaseModel):
    faellig: bool
    zeitraum: str = ""
    zeitraum_label: str = ""
    deadline: str = ""
    grund: str = ""           # "kleinunternehmer" | "keine_lieferungen" | "faellig" | "abgelaufen"


# ---------------------------------------------------------------------------
# Endpunkte
# ---------------------------------------------------------------------------

@router.get("/pruefen", response_model=ZMPruefung)
def zm_pruefen(db: Session = Depends(get_db)):
    """Prüft ob eine ZM fällig ist – für Dashboard-Hinweis."""
    unt = db.query(Unternehmen).first()
    if not unt or unt.ist_kleinunternehmer:
        return ZMPruefung(faellig=False, grund="kleinunternehmer")

    heute = date.today()
    zeitraum = _letztes_quartal(heute)
    deadline = _deadline(zeitraum)

    if heute > deadline:
        return ZMPruefung(faellig=False, grund="abgelaufen",
                          zeitraum=zeitraum, deadline=deadline.isoformat())

    von, bis, _ = _zeitraum_grenzen(zeitraum)
    eintraege = _ig_eintraege(von, bis, db)
    if not eintraege:
        return ZMPruefung(faellig=False, grund="keine_lieferungen", zeitraum=zeitraum)

    return ZMPruefung(
        faellig=True,
        grund="faellig",
        zeitraum=zeitraum,
        zeitraum_label=_zeitraum_label(zeitraum),
        deadline=deadline.isoformat(),
    )


@router.get("/berechnen", response_model=ZMErgebnis)
def zm_berechnen(
    zeitraum: str = Query(..., description="YYYY-QN oder YYYY-MM"),
    db: Session = Depends(get_db),
):
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(404, "Unternehmensdaten nicht gefunden.")
    if unt.ist_kleinunternehmer:
        raise HTTPException(422, "Kleinunternehmer §19 sind von der ZM befreit.")

    try:
        von, bis, _ = _zeitraum_grenzen(zeitraum)
    except Exception:
        raise HTTPException(422, f"Ungültiges Zeitraum-Format: {zeitraum!r}")

    deadline = _deadline(zeitraum)
    eintraege = _ig_eintraege(von, bis, db)

    # Gruppieren nach USt-IdNr. + Kennzeichen
    gruppen: dict[tuple[str, str, str], Decimal] = {}
    for e in eintraege:
        kz = _kennzeichen(e)
        # USt-IdNr. und Land aus verlinktem Kunden holen
        ust_idnr = ""
        land = ""
        if e.rechnung_id:
            rechnung = db.query(Rechnung).filter(Rechnung.id == e.rechnung_id).first()
            if rechnung and rechnung.kunden_id:
                kunde = db.query(Kunde).filter(Kunde.id == rechnung.kunden_id).first()
                if kunde:
                    ust_idnr = kunde.ust_idnr or ""
                    land = kunde.land or ""

        key = (ust_idnr or "unbekannt", land or "?", kz)
        gruppen[key] = gruppen.get(key, ZERO) + (e.netto_betrag or ZERO)

    positionen = [
        ZMPosition(ust_idnr=uid, land=land, kennzeichen=kz,
                   betrag=betrag.quantize(Decimal("0.01")))
        for (uid, land, kz), betrag in sorted(gruppen.items())
    ]
    gesamt = sum(p.betrag for p in positionen)

    return ZMErgebnis(
        zeitraum=zeitraum,
        zeitraum_label=_zeitraum_label(zeitraum),
        von=von, bis=bis, deadline=deadline,
        positionen=positionen,
        gesamt=gesamt,
        ueber_50k=gesamt >= Decimal("50000"),
    )
