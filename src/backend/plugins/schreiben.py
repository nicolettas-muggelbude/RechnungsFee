"""Transaktionale Host-Schreibzugriffe über dieselben CRUD-Helfer wie die HTTP-API."""
from __future__ import annotations

import json
from contextlib import contextmanager

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from . import dto
from .host_api import HostApiFehler, LeseZugriff

MAX_PAYLOAD_BYTES = 1024 * 1024
# Nummern, Abschlusszustände und Import-Abkürzungen gehören ausschließlich dem Core.
GESPERRT = {"kundennummer", "debitor_nr", "rechnungsnummer", "extern_erstellt",
            "netto_gesamt_override", "ust_gesamt_override", "brutto_gesamt_override",
            "ust_idnr_validiert", "ust_idnr_validierung_datum"}


def _id(wert: str) -> int:
    if (not isinstance(wert, str) or len(wert) > 19 or not wert.isascii()
            or not wert.isdecimal() or not 0 < int(wert) <= 2**63 - 1):
        raise HostApiFehler("validation-error", "Die ID muss eine positive Ganzzahl sein")
    return int(wert)


def _dienste(entity, action):
    if entity == "customer":
        from api import kunden
        from api.schemas import KundeCreate, KundeUpdate
        return getattr(kunden, f"_{action}_kunde"), KundeCreate if action == "create" else KundeUpdate
    if entity == "article":
        from api import artikel
        from api.schemas_artikel import ArtikelCreate, ArtikelUpdate
        return getattr(artikel, f"_{action}_artikel"), ArtikelCreate if action == "create" else ArtikelUpdate
    from api import rechnungen
    from api.schemas_rechnungen import RechnungCreate, RechnungUpdate
    return getattr(rechnungen, f"_{action}_rechnung"), RechnungCreate if action == "create" else RechnungUpdate


def _payload(text, schema, entity, action):
    if len(text.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise HostApiFehler("validation-error", "Der Schreib-Payload ist größer als 1 MB")
    try:
        daten = json.loads(text)
    except (ValueError, RecursionError):
        raise HostApiFehler("validation-error", "Payload ist kein gültiges JSON") from None
    if not isinstance(daten, dict):
        raise HostApiFehler("validation-error", "Payload muss ein JSON-Objekt sein")
    if "_schema" in daten and daten.pop("_schema") != f"{entity}@1":
        raise HostApiFehler("validation-error", "Nicht unterstützte DTO-Version")
    falsch = set(daten) - (set(schema.model_fields) - GESPERRT)
    if falsch:
        raise HostApiFehler("validation-error", "Nicht schreibbare Felder: " + ", ".join(sorted(falsch)))
    if entity == "invoice":
        if "ist_entwurf" in daten and daten["ist_entwurf"] is not True:
            raise HostApiFehler("validation-error", "Plugins dürfen Rechnungen nur als Entwurf speichern")
        if action == "create":
            daten["ist_entwurf"] = True
        if daten.get("positionen") is not None:
            from api.schemas_rechnungen import RechnungspositionCreate
            if not isinstance(daten["positionen"], list):
                raise HostApiFehler("validation-error", "positionen muss eine Liste sein")
            for pos in daten["positionen"]:
                if not isinstance(pos, dict) or set(pos) - set(RechnungspositionCreate.model_fields):
                    raise HostApiFehler("validation-error", "Ungültige oder nicht schreibbare Positionsfelder")
    try:
        return schema.model_validate(daten)
    except ValidationError as exc:
        # Keine Eingabewerte in Fehlern oder Plugin-Protokollen ausgeben.
        meldung = "; ".join(".".join(map(str, e["loc"])) + ": " + e["msg"]
                            for e in exc.errors(include_input=False))
        raise HostApiFehler("validation-error", meldung) from None


def _referenzen_und_felder(db, modell, daten):
    """Auch ohne SQLite-FK-Pragma keine ungültigen Verweise akzeptieren."""
    for feld, wert in daten.items():
        spalte = modell.__table__.columns.get(feld)
        if spalte is None:
            continue
        if isinstance(wert, str) and getattr(spalte.type, "length", None) and len(wert) > spalte.type.length:
            raise HostApiFehler("validation-error", f"{feld} ist länger als {spalte.type.length} Zeichen")
        if wert is not None:
            for fk in spalte.foreign_keys:
                if db.scalar(select(fk.column).where(fk.column == wert)) is None:
                    raise HostApiFehler("not-found", f"Referenz {feld} nicht gefunden")


@contextmanager
def _geschuetzte_aktion(db):
    """Ein einzelner Host-Aufruf ist atomar, die äußere Transaktion bleibt Eigentümer."""
    from . import ereignisse
    vorher = db.info.get(ereignisse._IN_ARBEIT)
    if not vorher:
        db.flush()  # Bereits ausstehende App-Änderungen weiterhin von der ORM-Pipeline erfassen.
    post = db.info.setdefault(ereignisse._POST, [])
    dateien = db.info.setdefault(ereignisse._DATEIEN, [])
    post_vorher, dateien_vorher = list(post), list(dateien)
    db.info[ereignisse._IN_ARBEIT] = True
    try:
        # SQLite im Legacy-Transaktionsmodus muss vor SAVEPOINT ein echtes BEGIN haben;
        # sonst persistiert RELEASE SAVEPOINT bereits die Daten trotz äußerem rollback().
        verbindung = db.connection()
        if verbindung.dialect.name == "sqlite":
            roh = verbindung.connection.driver_connection
            if not roh.in_transaction:
                verbindung.exec_driver_sql("BEGIN")
        with db.begin_nested():
            yield
    except BaseException:
        post[:] = post_vorher
        dateien[:] = dateien_vorher
        raise
    finally:
        if vorher:
            db.info[ereignisse._IN_ARBEIT] = vorher
        else:
            db.info.pop(ereignisse._IN_ARBEIT, None)


class DatenZugriff(LeseZugriff):
    """Pre-Hook: bestehende Session; Post-Hook: eigene Transaktion je Host-Aufruf.

    Rechte werden vor dem Eintritt in diesen Host-Adapter von der Wasm-Laufzeit geprüft.
    Fachliche Sperren, atomare Fehlerbehandlung und Audit gelten unabhängig davon.
    """
    def _schreibe(self, plugin_id, entity, action, id=None, payload_json=None):
        from . import ereignisse, laufzeit
        from database.models import PluginProtokoll
        d = self._definition(entity)
        if entity == "voucher":
            raise HostApiFehler("validation-error", "Belege sind schreibgeschützt; verwende den Belegimport der App")
        if len(laufzeit._kontext.get()) >= laufzeit.MAX_VERSCHACHTELUNG:
            raise HostApiFehler("validation-error", "Maximale Verschachtelung schreibender Plugin-Aufrufe erreicht")
        funktion, schema = _dienste(entity, action)
        schluessel = _id(id) if id is not None else None
        daten = _payload(payload_json, schema, entity, action) if action != "delete" else None
        db = self._session if self._session is not None else self._factory()
        # Auch außerhalb der App-SessionFactory müssen Post-Hooks/Dateiaktionen korrekt warten.
        ereignisse.registrieren_session(db)
        try:
            with _geschuetzte_aktion(db):
                obj = db.get(d.modell, schluessel) if schluessel is not None else None
                if action != "create":
                    if obj is None:
                        raise HostApiFehler("not-found", f"{entity} {schluessel} nicht gefunden")
                    if (entity, schluessel) in db.info.get(ereignisse._ZIELE, set()):
                        raise HostApiFehler("validation-error", "Ein gerade geprüfter Datensatz darf nicht erneut geschrieben werden")
                    darf, grund = dto.ist_aenderbar(obj)
                    if not darf:
                        raise HostApiFehler("validation-error", grund)
                if daten:
                    felder = daten.model_dump(exclude_unset=True)
                    _referenzen_und_felder(db, d.modell, felder)
                    if entity == "invoice" and daten.positionen is not None:
                        for pos in daten.positionen:
                            _referenzen_und_felder(db, dto.Rechnungsposition, pos.model_dump())
                if action == "delete":
                    vorher = dto.als_dto(obj)
                    ereignisse.host_vor_aenderung(db, entity, action, obj, self)
                    dateien = funktion(schluessel, db, commit=False)
                    if entity == "invoice":
                        db.info[ereignisse._DATEIEN].extend(dateien or [])
                    payload = vorher
                else:
                    obj = funktion(daten, db, commit=False) if action == "create" else funktion(schluessel, daten, db, commit=False)
                    ereignisse.host_vor_aenderung(db, entity, action, obj, self)
                    db.flush()
                    payload = dto.als_dto(obj)
                    schluessel = obj.id
                ereignisse.merke_post(db, entity, action, payload)
                db.add(PluginProtokoll(plugin_id=plugin_id, hook=f"host:{entity}:{action}", entitaet=entity,
                                       datensatz_id=schluessel, ergebnis="geschrieben"))
                db.flush()
                antwort = json.dumps(payload, ensure_ascii=False)
            if self._session is None:
                db.commit()
            return antwort
        except HTTPException as exc:
            raise HostApiFehler("not-found" if exc.status_code == 404 else "validation-error", str(exc.detail)) from None
        except IntegrityError:
            raise HostApiFehler("validation-error", "Schreibzugriff verletzt eine Datenbankregel oder verwendet eine bereits vergebene Nummer") from None
        except laufzeit.PluginAbbruch as exc:
            raise HostApiFehler("validation-error", exc.anzeige) from None
        finally:
            if self._session is None:
                db.rollback()
                db.close()

    def create(self, plugin_id: str, entity: str, payload_json: str) -> str:
        return self._schreibe(plugin_id, entity, "create", payload_json=payload_json)

    def update(self, plugin_id: str, entity: str, id: str, payload_json: str) -> str:
        return self._schreibe(plugin_id, entity, "update", id=id, payload_json=payload_json)

    def delete(self, plugin_id: str, entity: str, id: str) -> None:
        self._schreibe(plugin_id, entity, "delete", id=id)
