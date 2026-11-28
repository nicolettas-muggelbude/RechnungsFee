"""
Unternehmer-Cockpit – Betriebswirtschaftliche Auswertung (BWA light)

Alle Beträge netto (ohne USt/Vorsteuer), Zuflussprinzip (wie EÜR).
Ausgeschlossen: Privatentnahmen/Einlagen (euer_zeile 106/107), Anlage-Buchungen, USt-Buchungen.
Anlage-Käufe zählen stattdessen über die AfA aus dem Anlagenverzeichnis (Issue #607).
"""

import calendar
from datetime import date as dt_date_type
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
# Issue #607: AfA aus dem Anlagenverzeichnis, gleicher Name wie die Journal-Kategorie (Zeile 33)
AFA_KATEGORIE = "Abschreibungen (AfA)"


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
    from api.euer import AUSGABEN_ZEILEN, _euer_haupt_beitrag
    if zeile in AUSGABEN_ZEILEN:
        # Gleicher Beitrag wie in der EÜR (Issue #424 nicht abzugsfähige USt, #459 Reverse
        # Charge, #486 Storno-Spiegel der Vorsteuer)
        return _euer_haupt_beitrag(e)[1]
    return ZERO


def _zaehlt_in_kacheln(kat: Optional[Kategorie]) -> bool:
    """Dashboard-Kacheln (Dashboard.tsx): alles außer Privat und durchlaufenden Posten (Issue #564)."""
    return not kat or kat.kontenart not in ("Privat", "Neutral")


def _ueberleitung_grund(kat: Optional[Kategorie], brutto: Decimal, ein: Decimal, aus: Decimal) -> str:
    """Issue #603: warum der Kachelbetrag (brutto) vom Cockpit (netto, EÜR-relevant) abweicht."""
    if not kat:
        return "Keine Kategorie: zählt weder im Cockpit noch in der EÜR. Buchung prüfen."
    if kat.kontenart == "Privat":
        return "Privatbuchung: zählt nirgends als Betriebseinnahme oder -ausgabe."
    if kat.kontenart == "Neutral":
        return "Durchlaufender Posten: zählt nirgends."
    if kat.kontenart == "Anlage":
        return "Anlagekauf: zählt in der EÜR über die Abschreibung (Anlagenverzeichnis), nicht mit dem Kaufpreis."
    z = kat.euer_zeile
    if z is None:
        return "Kategorie ohne EÜR-Zeile: fällt aus Cockpit und EÜR. Kategorie prüfen."
    if z in (106, 107):
        return "Privatentnahme/-einlage (EÜR-Hinweiszeile): kein Gewinnbestandteil."
    if z in _EINNAHMEN_ZEILEN_SKIP or z in _AUSGABEN_ZEILEN_SKIP:
        return f"Umsatzsteuer/Vorsteuer (EÜR-Zeile {z}): steht in der EÜR, im Cockpit nicht (netto)."
    if ein == ZERO and aus == ZERO:
        return f"EÜR-Zeile {z} passt nicht zur Buchungsrichtung: zählt im Cockpit nicht."
    if abs(ein) + abs(aus) != brutto:
        return "Im Cockpit netto: Umsatzsteuer bzw. abziehbare Vorsteuer herausgerechnet."
    return "Zählt unverändert."


@router.get("/ueberleitung")
def get_ueberleitung(
    von: dt_date_type = Query(...),
    bis: dt_date_type = Query(...),
    db: Session = Depends(get_db),
):
    """Issue #603: Überleitung Dashboard-Kacheln (brutto, alle Zahlungen) → Cockpit (netto,
    EÜR-relevant) für denselben Zeitraum, je Kategorie und Kachelseite. Nutzt dieselben
    Regeln wie get_cockpit (_einnahme_netto/_ausgabe_netto) und die Kacheln im Dashboard."""
    eintraege = (
        db.query(Journaleintrag)
        .filter(Journaleintrag.datum >= von, Journaleintrag.datum <= bis)
        .all()
    )

    gruppen: dict[tuple[str, Optional[int]], dict] = {}
    for e in eintraege:
        kat: Optional[Kategorie] = e.kategorie
        ein = _einnahme_netto(e, kat)
        aus = _ausgabe_netto(e, kat)
        in_kacheln = _zaehlt_in_kacheln(kat)
        if in_kacheln:
            seite = "eingaenge" if e.art == "Einnahme" else "ausgaenge"
            brutto = e.brutto_betrag or ZERO
        elif ein != ZERO or aus != ZERO:
            seite, brutto = "nicht_in_kacheln", ZERO
        else:
            continue
        key = (seite, kat.id if kat else None)
        g = gruppen.setdefault(key, {
            "kategorie_id": kat.id if kat else None,
            "kategorie": kat.name if kat else "(ohne Kategorie)",
            "kontenart": kat.kontenart if kat else None,
            "euer_zeile": kat.euer_zeile if kat else None,
            "anzahl": 0, "brutto": ZERO, "cockpit_einnahmen": ZERO, "cockpit_ausgaben": ZERO,
        })
        g["anzahl"] += 1
        g["brutto"] += brutto
        g["cockpit_einnahmen"] += ein
        g["cockpit_ausgaben"] += aus

    def r(v: Decimal) -> float:
        return float(v.quantize(Q2, ROUND_HALF_UP))

    ergebnis: dict[str, list] = {"eingaenge": [], "ausgaenge": [], "nicht_in_kacheln": []}
    kat_cache = {k.id: k for k in db.query(Kategorie).all()}
    for (seite, kat_id), g in gruppen.items():
        kat = kat_cache.get(kat_id) if kat_id else None
        ergebnis[seite].append({
            **g,
            "grund": _ueberleitung_grund(kat, g["brutto"], g["cockpit_einnahmen"], g["cockpit_ausgaben"]),
            "brutto": r(g["brutto"]),
            "cockpit_einnahmen": r(g["cockpit_einnahmen"]),
            "cockpit_ausgaben": r(g["cockpit_ausgaben"]),
        })
    for liste in ergebnis.values():
        liste.sort(key=lambda x: (-abs(x["brutto"]), x["kategorie"]))

    def summe(feld: str, seite: Optional[str] = None) -> float:
        return r(sum((Decimal(str(x[feld])) for s, l in ergebnis.items() if seite in (None, s) for x in l), ZERO))

    return {
        "von": von.isoformat(),
        "bis": bis.isoformat(),
        **ergebnis,
        "summen": {
            "kachel_eingaenge": summe("brutto", "eingaenge"),
            "kachel_ausgaenge": summe("brutto", "ausgaenge"),
            "cockpit_einnahmen": summe("cockpit_einnahmen"),
            "cockpit_ausgaben": summe("cockpit_ausgaben"),
        },
    }


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

    # Issue #607: Anschaffungen auf Anlage-Kategorien zählen nicht mit dem Kaufpreis, sondern
    # über die AfA aus dem Anlagenverzeichnis - wie in der EÜR (Zeile 33), monatsweise verteilt
    from api.anlageverzeichnis import afa_je_monat, offene_anschaffungen
    from database.models import Anlagegut
    for gut in db.query(Anlagegut).filter(Anlagegut.aktiv == True).all():  # noqa: E712
        for monat, afa in afa_je_monat(gut, jahr).items():
            monats_aus[monat] += afa
            if (jahr, monat) in periode_set:
                kpi_aus += afa
                kat_aus[AFA_KATEGORIE] = kat_aus.get(AFA_KATEGORIE, ZERO) + afa

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
        # Issue #607: Anlage-Käufe des Jahres ohne Eintrag im Anlagenverzeichnis (fehlen als Aufwand)
        "offene_anschaffungen": offene_anschaffungen(db, von, bis),
    }
