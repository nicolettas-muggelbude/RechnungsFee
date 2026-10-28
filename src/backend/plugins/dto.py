"""
Stabile JSON-Darstellung der Kern-Entitäten für Plugins (docs/plan-plugin-system.md, Phase 4).

Plugins sehen NIE die ORM-Interna, sondern diese eingefrorenen V1-Formen. Eine Schema-Migration
in RechnungsFee darf ein Plugin dadurch nicht brechen: neue Spalten tauchen hier erst auf, wenn
sie bewusst ergänzt werden, umbenannte Spalten werden hier auf den alten Namen gemappt.

Jedes DTO trägt `"_schema": "<entity>@1"`.

Rückschreiben (Pre-Hook liefert geänderten Payload): nur die Felder in `aenderbar`, und bei
Rechnungen nur, solange sie ein Entwurf sind (GoBD: finalisierte Dokumente sind unveränderlich).
Alles andere wird ignoriert und protokolliert - kein Plugin kann Beträge, Nummern, IDs,
Zahlungsstatus o. Ä. verändern.

`voucher` ist der hochgeladene Beleg (Tabelle `belege`, nur Metadaten, nie änderbar).

`invoice` umfasst alle Zeilen der Tabelle `rechnungen`: Ausgangs- und Eingangsrechnungen
(`typ`), dazu Angebote, Aufträge, Lieferscheine, Proforma, Gutschriften usw. (`dokument_typ`).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from database.models import Artikel, Beleg, Kunde, Rechnung, Rechnungsposition

DTO_VERSION = 1


@dataclass(frozen=True)
class EntitaetDef:
    name: str
    modell: type
    felder: tuple[str, ...]
    aenderbar: frozenset[str]


KUNDE = EntitaetDef(
    "customer", Kunde,
    felder=(
        "id", "kundennummer", "debitor_nr", "firmenname", "anrede", "vorname", "nachname", "z_hd",
        "strasse", "hausnummer", "plz", "ort", "land", "email", "telefon", "ust_idnr",
        "steuernummer_ausland", "ist_verein", "ist_gemeinnuetzig", "zugferd_aktiv", "skonto_prozent",
        "skonto_tage", "mahnung_gesperrt", "notizen", "aktiv", "erstellt_am", "aktualisiert_am",
    ),
    aenderbar=frozenset({
        "firmenname", "anrede", "vorname", "nachname", "z_hd", "strasse", "hausnummer", "plz", "ort",
        "land", "email", "telefon", "ust_idnr", "steuernummer_ausland", "notizen",
    }),
)

ARTIKEL = EntitaetDef(
    "article", Artikel,
    felder=(
        "id", "artikelnummer", "typ", "bezeichnung", "beschreibung", "einheit", "steuersatz",
        "vk_netto", "vk_brutto", "vk_eingabe", "ek_netto", "hersteller", "artikelcode", "gruppe_id",
        "lieferant_id", "differenzbesteuerung", "lager_aktiv", "bestand_aktuell", "mindestbestand",
        "aktiv", "erstellt_am", "aktualisiert_am",
    ),
    # Preise bewusst nicht: deren Ableitung (Netto/Brutto, Issue #332/#344) gehört in api/artikel.py
    aenderbar=frozenset({"bezeichnung", "beschreibung", "einheit", "hersteller", "artikelcode"}),
)

RECHNUNG = EntitaetDef(
    "invoice", Rechnung,
    felder=(
        "id", "typ", "dokument_typ", "rechnungsnummer", "datum", "faellig_am", "leistung_von",
        "leistung_bis", "kunde_id", "lieferant_id", "partner_freitext", "partner_strasse",
        "partner_hausnummer", "partner_plz", "partner_ort", "partner_land", "land", "netto_gesamt",
        "ust_gesamt", "brutto_gesamt", "bezahlt", "bezahlt_betrag", "zahlungsstatus", "zahlungsdatum",
        "ist_entwurf", "storniert", "ausgegeben", "externe_belegnr", "kunden_bestellnummer",
        "einleitungstext", "schlusstext", "notizen", "skonto_prozent", "skonto_tage", "beleg_id",
        "ist_reverse_charge", "ist_eu_lieferung", "ist_drittland_leistung", "ist_ausfuhrlieferung",
        "mahnstufe_aktuell", "angebot_status", "auftrag_status", "gueltig_bis", "erstellt_am",
        "aktualisiert_am",
    ),
    aenderbar=frozenset({
        "einleitungstext", "schlusstext", "notizen", "kunden_bestellnummer", "externe_belegnr",
        "leistung_von", "leistung_bis",
    }),
)

# „voucher“ = Beleg (Stefan, 2026-10-28): die hochgeladene Belegdatei (PDF/Bild) als Metadaten.
# Dateipfade bleiben intern, der Dateiinhalt ist für Plugins nicht lesbar. Nichts änderbar - Belege
# sind nach GoBD unveränderlich (sha256 dient genau diesem Nachweis).
BELEG = EntitaetDef(
    "voucher", Beleg,
    felder=("id", "original_name", "mime_type", "dateigroesse", "sha256", "hochgeladen_am"),
    aenderbar=frozenset(),
)

POSITION_FELDER = (
    "position_nr", "artikel_id", "beschreibung", "menge", "einheit", "netto", "rabatt_prozent",
    "ust_satz", "ust_betrag", "brutto",
)

ENTITAETEN: dict[str, EntitaetDef] = {e.name: e for e in (KUNDE, RECHNUNG, ARTIKEL, BELEG)}
NACH_MODELL: dict[type, EntitaetDef] = {e.modell: e for e in ENTITAETEN.values()}

NICHT_UNTERSTUETZT = {
    "task": "Aufgaben („task“) gibt es in dieser RechnungsFee-Version noch nicht",
}


def _wert(v):
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, datetime):
        return v.isoformat(timespec="seconds")
    if isinstance(v, date):
        return v.isoformat()
    return v


def als_dto(obj) -> dict:
    d = NACH_MODELL[type(obj)]
    dto = {"_schema": f"{d.name}@{DTO_VERSION}"}
    for feld in d.felder:
        dto[feld] = _wert(getattr(obj, feld, None))
    if d is RECHNUNG:
        dto["positionen"] = [
            {f: _wert(getattr(p, f, None)) for f in POSITION_FELDER}
            for p in sorted(obj.positionen, key=lambda p: (p.position_nr or 0, p.id or 0))
        ]
    return dto


def ist_aenderbar(obj) -> tuple[bool, str | None]:
    """Darf ein Plugin dieses Objekt überhaupt verändern? (GoBD)"""
    if isinstance(obj, Rechnung) and (not obj.ist_entwurf or obj.immutable or obj.storniert or obj.ausgegeben):
        return False, "finalisierte Dokumente sind unveränderlich (GoBD)"
    if isinstance(obj, Beleg):
        return False, "Belege sind unveränderlich (GoBD)"
    return True, None


def _spalte(modell, feld):
    return modell.__table__.columns[feld]


def _konvertiere(modell, feld: str, wert):
    """Prüft/konvertiert einen vom Plugin gelieferten Wert für ein änderbares Feld.
    Wirft ValueError mit verständlichem Text."""
    spalte = _spalte(modell, feld)
    if wert is None:
        if not spalte.nullable:
            raise ValueError(f"{feld} darf nicht leer sein")
        return None
    typ = spalte.type.python_type
    if typ is date:
        if not isinstance(wert, str):
            raise ValueError(f"{feld} muss ein Datum (JJJJ-MM-TT) sein")
        try:
            return date.fromisoformat(wert)
        except ValueError:
            raise ValueError(f"{feld} muss ein Datum (JJJJ-MM-TT) sein") from None
    if typ is str:
        if not isinstance(wert, str):
            raise ValueError(f"{feld} muss ein Text sein")
        laenge = getattr(spalte.type, "length", None)
        if laenge and len(wert) > laenge:
            raise ValueError(f"{feld} ist länger als {laenge} Zeichen")
        return wert
    raise ValueError(f"{feld} kann nicht geändert werden")


@dataclass
class Rueckschreiben:
    geaendert: list[str]
    ignoriert: list[str]
    ungueltig: list[str]


def uebernehme(obj, vorher: dict, nachher: dict) -> Rueckschreiben:
    """Überträgt die vom Plugin geänderten Felder (nur erlaubte) auf das ORM-Objekt."""
    d = NACH_MODELL[type(obj)]
    erg = Rueckschreiben([], [], [])
    darf, grund = ist_aenderbar(obj)
    for feld in sorted(set(vorher) | set(nachher)):
        if feld == "_schema" or vorher.get(feld) == nachher.get(feld):
            continue
        if not darf or feld not in d.aenderbar or feld not in nachher:
            erg.ignoriert.append(feld)
            continue
        try:
            setattr(obj, feld, _konvertiere(d.modell, feld, nachher[feld]))
            erg.geaendert.append(feld)
        except ValueError as e:
            erg.ungueltig.append(str(e))
    if not darf and erg.ignoriert:
        erg.ignoriert = [f"{f} ({grund})" for f in erg.ignoriert]
    return erg


# ---------------------------------------------------------------------------
# Listen-Filter für host-api.list
# ---------------------------------------------------------------------------

MAX_LIMIT = 100


def filter_anwenden(query, d: EntitaetDef, filter_json: str | None):
    """Einfacher Gleichheitsfilter: {"feld": wert, ..., "limit": 50, "offset": 0}.
    Nur DTO-Felder (ohne Positionen). Wirft ValueError bei ungültigem Filter."""
    import json

    limit, offset = 50, 0
    if filter_json:
        try:
            f = json.loads(filter_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Filter ist kein gültiges JSON: {e.msg}") from None
        if not isinstance(f, dict):
            raise ValueError("Filter muss ein JSON-Objekt sein")
        for schluessel, wert in f.items():
            if schluessel == "limit":
                if not isinstance(wert, int) or not 1 <= wert <= MAX_LIMIT:
                    raise ValueError(f"limit muss zwischen 1 und {MAX_LIMIT} liegen")
                limit = wert
            elif schluessel == "offset":
                if not isinstance(wert, int) or wert < 0:
                    raise ValueError("offset muss eine Zahl ≥ 0 sein")
                offset = wert
            elif schluessel in d.felder:
                spalte = _spalte(d.modell, schluessel)
                typ = spalte.type.python_type
                if wert is None:
                    query = query.filter(spalte.is_(None))
                    continue
                if typ is date and isinstance(wert, str):
                    try:
                        wert = date.fromisoformat(wert)
                    except ValueError:
                        raise ValueError(f"{schluessel}: ungültiges Datum") from None
                elif typ is Decimal and isinstance(wert, (str, int, float)):
                    wert = Decimal(str(wert))
                elif typ is bool and not isinstance(wert, bool):
                    raise ValueError(f"{schluessel} muss true oder false sein")
                query = query.filter(spalte == wert)
            else:
                raise ValueError(f"Unbekanntes Filterfeld „{schluessel}“")
    return query.order_by(d.modell.id).offset(offset).limit(limit)


__all__ = [
    "ENTITAETEN", "NACH_MODELL", "NICHT_UNTERSTUETZT", "als_dto", "uebernehme", "ist_aenderbar",
    "filter_anwenden", "Rueckschreiben", "Rechnungsposition",
]
