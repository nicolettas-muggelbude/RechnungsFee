"""
Kryptographische Signatur für GoBD-relevante Datensätze.

SHA-256 über kanonisches JSON der buchungsrelevanten Felder.
Reproduzierbar: gleiche Eingabe → gleicher Hash.
"""

import hashlib
import json
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from database.models import Journaleintrag, Tagesabschluss, VorsteuerAnspruch


def berechne_signatur(felder: dict) -> str:
    """SHA-256 über kanonisches JSON (sort_keys, kein Whitespace).
    Gleiches dict → gleicher Hash, unabhängig von Einfüge-Reihenfolge."""
    canonical = json.dumps(felder, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _dec(wert: Optional[Decimal], skala: str) -> str:
    """Normalisiert einen Decimal-Betrag auf die deklarierte Spalten-Skala (z.B. Numeric(12,2)
    -> "0.01") bevor er in die Signatur einfliesst.

    Ohne das lieferte str() unterschiedliche Strings fuer denselben Wert je nachdem ob das
    Objekt frisch im Speicher stand (Decimal("19"), direkt aus dem Request geparst) oder
    bereits einmal aus SQLite geladen wurde (Decimal("19.00"), durch den Numeric-Skalen der
    Spalte) - identische Buchung, unterschiedlicher Hash, je nach Zeitpunkt der Signierung
    (Issue #384: Neubuchungen instabil, aus der DB kopierte Storno-Buchungen stabil).
    """
    if wert is None:
        return ""
    return str(Decimal(str(wert)).quantize(Decimal(skala)))


def signatur_journaleintrag(e: "Journaleintrag") -> str:
    """Signatur über alle buchungsrelevanten Felder eines Journaleintrags."""
    return berechne_signatur({
        "art": str(e.art),
        "belegnr": str(e.belegnr),
        "beschreibung": str(e.beschreibung),
        "brutto_betrag": _dec(e.brutto_betrag, "0.01"),
        "datum": str(e.datum),
        "externe_belegnr": e.externe_belegnr or "",
        "kategorie_id": str(e.kategorie_id) if e.kategorie_id is not None else "",
        "kunde_id": str(e.kunde_id) if e.kunde_id is not None else "",
        "netto_betrag": _dec(e.netto_betrag, "0.01"),
        "steuerbefreiung_grund": e.steuerbefreiung_grund or "",
        "ust_betrag": _dec(e.ust_betrag, "0.01"),
        "ust_satz": _dec(e.ust_satz, "0.01"),
        "vorsteuerabzug": bool(e.vorsteuerabzug),
        "zahlungsart": str(e.zahlungsart),
        "km_anzahl": _dec(e.km_anzahl, "0.1"),
    })


def signatur_vorsteueranspruch(v: "VorsteuerAnspruch") -> str:
    """Signatur über alle buchungsrelevanten Felder eines Vorsteuer-Anspruchs."""
    return berechne_signatur({
        "rechnung_id": str(v.rechnung_id),
        "datum": str(v.datum),
        "kategorie_id": str(v.kategorie_id) if v.kategorie_id is not None else "",
        "netto_betrag": _dec(v.netto_betrag, "0.01"),
        "ust_satz": _dec(v.ust_satz, "0.01"),
        "ust_betrag": _dec(v.ust_betrag, "0.01"),
        "vorsteuer_betrag": _dec(v.vorsteuer_betrag, "0.01"),
        "ust_sonderfall": v.ust_sonderfall or "",
        "typ": str(v.typ),
        "bezug_id": str(v.bezug_id) if v.bezug_id is not None else "",
        "korrektur_grund": v.korrektur_grund or "",
    })


def signatur_tagesabschluss(a: "Tagesabschluss") -> str:
    """Signatur über alle buchungsrelevanten Felder eines Tagesabschlusses."""
    return berechne_signatur({
        "anfangsbestand": _dec(a.anfangsbestand, "0.01"),
        "ausgaben_bar": _dec(a.ausgaben_bar, "0.01"),
        "datum": str(a.datum),
        "differenz": _dec(a.differenz, "0.01"),
        "einnahmen_bar": _dec(a.einnahmen_bar, "0.01"),
        "ist_endbestand": _dec(a.ist_endbestand, "0.01"),
        "kassenbewegungen_anzahl": str(a.kassenbewegungen_anzahl),
        "soll_endbestand": _dec(a.soll_endbestand, "0.01"),
        "uhrzeit": str(a.uhrzeit),
        "zaehlung_json": a.zaehlung_json or "",
    })
