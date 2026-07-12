"""
Unternehmer-Cockpit – Betriebswirtschaftliche Auswertung (BWA light)

Alle Beträge netto (ohne USt/Vorsteuer), Zuflussprinzip (wie EÜR).
Ausgeschlossen: Privatentnahmen/Einlagen (euer_zeile 106/107), Anlage-Buchungen, USt-Buchungen.
"""

import calendar
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Journaleintrag, Kategorie

router = APIRouter(prefix="/api/cockpit", tags=["Cockpit"])

ZERO = Decimal("0.00")
Q2   = Decimal("0.01")

# EÜR-Zeilen Abschnitt A (Einnahmen) ohne Privat/USt-Meta
_EINNAHMEN_ZEILEN_SKIP = {17, 18, 106, 107}
# EÜR-Zeilen Abschnitt B (Ausgaben) ohne Vorsteuer-Summenzeile
_AUSGABEN_ZEILEN_SKIP  = {57}


def _parse_zeitraum(zeitraum: str, wert: str) -> tuple[list[tuple[int, int]], int, str]:
    """
    Gibt zurück: (monatsliste [(jahr, monat), ...], jahr, label)
    """
    if zeitraum == "monat":
        # wert = "2026-06"
        jahr, monat = int(wert[:4]), int(wert[5:7])
        monate_de = ["Jan","Feb","Mär","Apr","Mai","Jun","Jul","Aug","Sep","Okt","Nov","Dez"]
        label = f"{monate_de[monat-1]} {jahr}"
        return [(jahr, monat)], jahr, label

    if zeitraum == "quartal":
        # wert = "2026-Q2"
        jahr = int(wert[:4])
        q = int(wert[6])
        start_monat = (q - 1) * 3 + 1
        monate = [(jahr, m) for m in range(start_monat, start_monat + 3)]
        label = f"Q{q} {jahr}"
        return monate, jahr, label

    # jahr
    jahr = int(wert)
    return [(jahr, m) for m in range(1, 13)], jahr, str(jahr)


def _einnahme_netto(e: Journaleintrag, kat: Optional[Kategorie]) -> Decimal:
    """Netto-Betrag als Einnahme (positiv) oder Storno-Abzug (negativ), 0 wenn nicht relevant."""
    if not kat or kat.kontenart == "Anlage" or kat.kontenart == "Privat":
        return ZERO
    zeile = kat.euer_zeile
    if zeile is None or zeile in _EINNAHMEN_ZEILEN_SKIP:
        return ZERO
    # Abschnitt A der EÜR = Einnahmen-Zeilen (1–99 ohne B-Zeilen)
    # Wir prüfen art: Einnahme addieren, Ausgabe (=Storno) subtrahieren
    if zeile < 100:  # Hinweiszeilen (106/107) bereits oben ausgeschlossen
        from api.euer import EINNAHMEN_ZEILEN
        if zeile in EINNAHMEN_ZEILEN:
            vz = Decimal("1") if e.art == "Einnahme" else Decimal("-1")
            return vz * (e.netto_betrag or ZERO)
    return ZERO


def _ausgabe_netto(e: Journaleintrag, kat: Optional[Kategorie]) -> Decimal:
    """Netto-Betrag als Ausgabe (positiv) oder Storno-Abzug (negativ), 0 wenn nicht relevant."""
    if not kat or kat.kontenart == "Anlage" or kat.kontenart == "Privat":
        return ZERO
    zeile = kat.euer_zeile
    if zeile is None or zeile in _AUSGABEN_ZEILEN_SKIP:
        return ZERO
    from api.euer import AUSGABEN_ZEILEN
    if zeile in AUSGABEN_ZEILEN:
        vz = Decimal("1") if e.art == "Ausgabe" else Decimal("-1")
        return vz * (e.netto_betrag or ZERO)
    return ZERO


@router.get("")
def get_cockpit(
    zeitraum: str = Query("monat", pattern="^(monat|quartal|jahr)$"),
    wert: str = Query(...),
    db: Session = Depends(get_db),
):
    periode_monate, jahr, label = _parse_zeitraum(zeitraum, wert)
    periode_set = set(periode_monate)

    # Alle Journaleinträge des Jahres laden (für Monatsbalken)
    from datetime import date as dt_date
    von = dt_date(jahr, 1, 1)
    bis = dt_date(jahr, 12, 31)

    eintraege = (
        db.query(Journaleintrag)
        .filter(Journaleintrag.datum >= von, Journaleintrag.datum <= bis)
        .all()
    )

    # --- Monatsbalken (ganzes Jahr) ---
    monats_ein:  dict[int, Decimal] = {m: ZERO for m in range(1, 13)}
    monats_aus:  dict[int, Decimal] = {m: ZERO for m in range(1, 13)}

    # --- KPI-Periode ---
    kpi_ein  = ZERO
    kpi_aus  = ZERO

    # --- Ausgaben nach Kategorie (Periode) ---
    kat_aus:  dict[str, Decimal] = {}

    # --- Einnahmen nach USt-Satz (Periode) ---
    ust_ein: dict[str, Decimal] = {"19": ZERO, "7": ZERO, "0": ZERO}

    for e in eintraege:
        kat: Optional[Kategorie] = e.kategorie
        monat = e.datum.month
        in_periode = (jahr, monat) in periode_set

        ein = _einnahme_netto(e, kat)
        aus = _ausgabe_netto(e, kat)

        monats_ein[monat] += ein
        monats_aus[monat] += aus

        if in_periode:
            kpi_ein += ein
            kpi_aus += aus

            # Ausgaben nach Kategorie
            if aus != ZERO and kat:
                kat_name = kat.name
                kat_aus[kat_name] = kat_aus.get(kat_name, ZERO) + aus

            # Einnahmen nach USt-Satz (auch Stornos mit ein < 0 berücksichtigen)
            if ein != ZERO:
                satz = int(e.ust_satz or 0)
                key = "19" if satz == 19 else "7" if satz == 7 else "0"
                ust_ein[key] = ust_ein.get(key, ZERO) + ein

    # Runden
    def r(v: Decimal) -> float:
        return float(v.quantize(Q2, ROUND_HALF_UP))

    kpi_ein = kpi_ein.quantize(Q2, ROUND_HALF_UP)
    kpi_aus = kpi_aus.quantize(Q2, ROUND_HALF_UP)
    gewinn  = (kpi_ein - kpi_aus).quantize(Q2, ROUND_HALF_UP)
    marge   = float((gewinn / kpi_ein * 100).quantize(Q2, ROUND_HALF_UP)) if kpi_ein else 0.0

    monate_de = ["Jan","Feb","Mär","Apr","Mai","Jun","Jul","Aug","Sep","Okt","Nov","Dez"]
    monatsbalken = [
        {
            "monat": monate_de[m - 1],
            "monat_nr": m,
            "einnahmen": r(monats_ein[m]),
            "ausgaben":  r(monats_aus[m]),
            "gewinn":    r((monats_ein[m] - monats_aus[m]).quantize(Q2, ROUND_HALF_UP)),
            "in_periode": (jahr, m) in periode_set,
        }
        for m in range(1, 13)
    ]

    ausgaben_kategorien = sorted(
        [{"name": k, "betrag": r(v)} for k, v in kat_aus.items() if v > ZERO],
        key=lambda x: x["betrag"],
        reverse=True,
    )

    einnahmen_nach_ust = []
    for satz_key, label_str in [("19", "19 %"), ("7", "7 %"), ("0", "0 % / §19")]:
        v = ust_ein.get(satz_key, ZERO)
        if v:
            einnahmen_nach_ust.append({"satz": label_str, "betrag": r(v)})

    return {
        "zeitraum_label": label,
        "kpis": {
            "einnahmen": r(kpi_ein),
            "ausgaben":  r(kpi_aus),
            "gewinn":    r(gewinn),
            "gewinn_marge_prozent": marge,
        },
        "monatsbalken": monatsbalken,
        "ausgaben_kategorien": ausgaben_kategorien,
        "einnahmen_nach_ust": einnahmen_nach_ust,
    }
