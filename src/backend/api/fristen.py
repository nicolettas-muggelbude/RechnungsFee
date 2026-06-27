"""
Steuerliche Fristen für Freiberufler/Kleinunternehmer.
Berechnet UStVA, ESt- und GewSt-Vorauszahlungsfristen für die nächsten N Monate.
"""
from datetime import date
from typing import Optional

from .feiertage import naechster_werktag


def _add_months(d: date, months: int, keep_day: bool = False) -> date:
    """Addiert N Monate zu einem date-Objekt (stdlib-only).
    keep_day=True: behält den Tag bei (z. B. 27. → max. letzter Tag des Zielmonats).
    keep_day=False (Standard): gibt immer den 1. des Zielmonats zurück.
    """
    import calendar
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    if not keep_day:
        return date(year, month, 1)
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def fristen_berechnen(
    bundesland: str,
    voranmeldungsrhythmus: str,      # 'monat' oder 'quartal'
    dauerfristverlaengerung: bool,   # +1 Monat bei UStVA
    est_aktiv: bool,
    gewst_aktiv: bool,
    ab_datum: Optional[date] = None,
    monate: int = 3,
) -> list[dict]:
    """
    Gibt eine nach Fälligkeitsdatum sortierte Liste aller Steuerfristen zurück.

    Jedes Element:
    {
        "typ": "UStVA" | "ESt-VZ" | "GewSt-VZ",
        "bezeichnung": "UStVA Q1/2026",
        "zeitraum": "Januar 2026",
        "faellig_original": "2026-02-10",   # ISO-Datum
        "faellig": "2026-02-10",             # nach Feiertag-Verschiebung
        "hinweis": "..."                     # optional (z.B. Dauerfristverlängerung)
    }
    """
    if ab_datum is None:
        ab_datum = date.today()

    bis_datum = _add_months(ab_datum, monate, keep_day=True)
    result = []

    # --- UStVA ---
    if voranmeldungsrhythmus in ("monat", "quartal"):
        if voranmeldungsrhythmus == "monat":
            perioden = _monatliche_perioden(ab_datum, bis_datum)
        else:
            perioden = _quartals_perioden(ab_datum, bis_datum)

        for p_label, p_year, p_month_end in perioden:
            # Frist: 10. des Folgemonats
            if dauerfristverlaengerung:
                frist_ref = _add_months(date(p_year, p_month_end, 1), 2)
            else:
                frist_ref = _add_months(date(p_year, p_month_end, 1), 1)
            faellig_original = date(frist_ref.year, frist_ref.month, 10)
            faellig = naechster_werktag(faellig_original, bundesland)

            if faellig < ab_datum:
                continue

            hinweis = "Dauerfristverlängerung aktiv (+1 Monat)" if dauerfristverlaengerung else None
            result.append({
                "typ": "UStVA",
                "bezeichnung": f"UStVA {p_label}",
                "zeitraum": p_label,
                "faellig_original": faellig_original.isoformat(),
                "faellig": faellig.isoformat(),
                "hinweis": hinweis,
            })

    # --- ESt-Vorauszahlungen (10.03 / 10.06 / 10.09 / 10.12) ---
    if est_aktiv:
        est_monate = [(3, "Q1"), (6, "Q2"), (9, "Q3"), (12, "Q4")]
        for year in range(ab_datum.year, bis_datum.year + 1):
            for month, label in est_monate:
                faellig_original = date(year, month, 10)
                faellig = naechster_werktag(faellig_original, bundesland)
                if faellig < ab_datum or faellig > bis_datum:
                    continue
                result.append({
                    "typ": "ESt-VZ",
                    "bezeichnung": f"ESt-Vorauszahlung {label}/{year}",
                    "zeitraum": f"{label}/{year}",
                    "faellig_original": faellig_original.isoformat(),
                    "faellig": faellig.isoformat(),
                    "hinweis": None,
                })

    # --- GewSt-Vorauszahlungen (15.02 / 15.05 / 15.08 / 15.11) ---
    if gewst_aktiv:
        gewst_monate = [(2, "Q1"), (5, "Q2"), (8, "Q3"), (11, "Q4")]
        for year in range(ab_datum.year, bis_datum.year + 1):
            for month, label in gewst_monate:
                faellig_original = date(year, month, 15)
                faellig = naechster_werktag(faellig_original, bundesland)
                if faellig < ab_datum or faellig > bis_datum:
                    continue
                result.append({
                    "typ": "GewSt-VZ",
                    "bezeichnung": f"GewSt-Vorauszahlung {label}/{year}",
                    "zeitraum": f"{label}/{year}",
                    "faellig_original": faellig_original.isoformat(),
                    "faellig": faellig.isoformat(),
                    "hinweis": None,
                })

    result.sort(key=lambda x: x["faellig"])
    return result


def _monatliche_perioden(ab: date, bis: date) -> list[tuple[str, int, int]]:
    """Alle Monate von 2 Monate vor `ab` bis `bis` (wegen Nachfrist)."""
    MONATE = [
        "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember"
    ]
    result = []
    cur = _add_months(date(ab.year, ab.month, 1), -2)
    ende = date(bis.year, bis.month, 1)
    while cur <= ende:
        result.append((f"{MONATE[cur.month - 1]} {cur.year}", cur.year, cur.month))
        cur = _add_months(cur, 1)
    return result


def _quartals_perioden(ab: date, bis: date) -> list[tuple[str, int, int]]:
    """Alle Quartale von 2 Quartale vor `ab` bis `bis`."""
    result = []
    cur = _add_months(date(ab.year, ab.month, 1), -6)
    # Quartalsbeginn (1, 4, 7, 10) abrunden
    cur = date(cur.year, ((cur.month - 1) // 3) * 3 + 1, 1)
    ende = date(bis.year, bis.month, 1)
    while cur <= ende:
        q = (cur.month - 1) // 3 + 1
        q_end_month = q * 3
        result.append((f"Q{q}/{cur.year}", cur.year, q_end_month))
        cur = _add_months(cur, 3)
    # Deduplizieren (falls Überlapp)
    seen = set()
    deduped = []
    for item in result:
        key = (item[1], item[2])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped
