"""
Kryptographische Signatur für GoBD-relevante Datensätze.

SHA-256 über kanonisches JSON der buchungsrelevanten Felder.
Reproduzierbar: gleiche Eingabe → gleicher Hash.
"""

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.models import Kassenbucheintrag, Tagesabschluss


def berechne_signatur(felder: dict) -> str:
    """SHA-256 über kanonisches JSON (sort_keys, kein Whitespace).
    Gleiches dict → gleicher Hash, unabhängig von Einfüge-Reihenfolge."""
    canonical = json.dumps(felder, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def signatur_kassenbucheintrag(e: "Kassenbucheintrag") -> str:
    """Signatur über alle buchungsrelevanten Felder eines Kassenbucheintrags."""
    return berechne_signatur({
        "art": str(e.art),
        "belegnr": str(e.belegnr),
        "beschreibung": str(e.beschreibung),
        "brutto_betrag": str(e.brutto_betrag),
        "datum": str(e.datum),
        "externe_belegnr": e.externe_belegnr or "",
        "kategorie_id": str(e.kategorie_id) if e.kategorie_id is not None else "",
        "kunde_id": str(e.kunde_id) if e.kunde_id is not None else "",
        "netto_betrag": str(e.netto_betrag),
        "steuerbefreiung_grund": e.steuerbefreiung_grund or "",
        "ust_betrag": str(e.ust_betrag),
        "ust_satz": str(e.ust_satz),
        "vorsteuerabzug": bool(e.vorsteuerabzug),
        "zahlungsart": str(e.zahlungsart),
    })


def signatur_tagesabschluss(a: "Tagesabschluss") -> str:
    """Signatur über alle buchungsrelevanten Felder eines Tagesabschlusses."""
    return berechne_signatur({
        "anfangsbestand": str(a.anfangsbestand),
        "ausgaben_bar": str(a.ausgaben_bar),
        "datum": str(a.datum),
        "differenz": str(a.differenz),
        "einnahmen_bar": str(a.einnahmen_bar),
        "ist_endbestand": str(a.ist_endbestand),
        "kassenbewegungen_anzahl": str(a.kassenbewegungen_anzahl),
        "soll_endbestand": str(a.soll_endbestand),
        "uhrzeit": str(a.uhrzeit),
        "zaehlung_json": a.zaehlung_json or "",
    })
