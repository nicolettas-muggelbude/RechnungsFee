"""
Host-API: was Plugins über `rechnungsfee:plugin/host-api` aufrufen können.

Gemeinsamer Vertrag und lesender Adapter (docs/plan-plugin-system.md):
- `HostApi` beschreibt, was eine Implementierung liefern muss (Phase 4: echter, GoBD-sicherer
  Datenzugriff über DTOs).
- `pruefe_recht()` setzt die vom Nutzer BESTÄTIGTEN Rechte durch - unabhängig davon, welche
  Implementierung dahinter steckt. Die Laufzeit ruft das vor jeder Weiterleitung auf.
- `KeinDatenzugriff` sperrt echte Daten bei Testläufen aus den Einstellungen.
- `plugins.schreiben.DatenZugriff` ergänzt transaktionale create/update/delete-Aufrufe.

Fehler werden als `HostApiFehler(art, meldung)` geworfen; `art` entspricht den Fällen der WIT-
Variante `api-error`: unauthorized | not-found | validation-error | internal-error.
"""
from __future__ import annotations

from typing import Protocol

FEHLER_ARTEN = ("unauthorized", "not-found", "validation-error", "internal-error")

# Host-Funktion -> benötigte Aktion im Manifest
BENOETIGTE_AKTION = {"get": "read", "list": "read", "create": "create", "update": "update", "delete": "delete"}


class HostApiFehler(Exception):
    def __init__(self, art: str, meldung: str):
        if art not in FEHLER_ARTEN:
            art = "internal-error"
        super().__init__(meldung)
        self.art = art
        self.meldung = meldung


class HostApi(Protocol):
    """Datenzugriff für genau einen Plugin-Aufruf. Alle Werte sind JSON-Texte."""

    def get(self, plugin_id: str, entity: str, id: str) -> str: ...
    def list(self, plugin_id: str, entity: str, filter_json: str | None) -> str: ...
    def create(self, plugin_id: str, entity: str, payload_json: str) -> str: ...
    def update(self, plugin_id: str, entity: str, id: str, payload_json: str) -> str: ...
    def delete(self, plugin_id: str, entity: str, id: str) -> None: ...


def pruefe_recht(rechte: dict[str, frozenset[str]], funktion: str, entity: str) -> None:
    aktion = BENOETIGTE_AKTION[funktion]
    if aktion not in rechte.get(entity, frozenset()):
        raise HostApiFehler(
            "unauthorized",
            f"Das Plugin hat kein bestätigtes Recht „{aktion}“ für „{entity}“",
        )


class KeinDatenzugriff:
    """Antwortet auf alles mit einem Fehler. `grund` erscheint beim Plugin als Fehlermeldung."""

    def __init__(self, grund: str = "Datenzugriff für Plugins ist in dieser Version noch nicht verfügbar"):
        self.grund = grund

    def _nein(self, *_args, **_kw):
        raise HostApiFehler("internal-error", self.grund)

    get = list = create = update = delete = _nein


class LeseZugriff:
    """Host-API mit lesendem Zugriff auf Kunden, Rechnungen, Artikel und Belege (Phase 4).

    `session`: die Session des laufenden Speichervorgangs (Pre-Hooks - das Plugin sieht dann
    auch die noch nicht festgeschriebenen Änderungen dieser Transaktion), oder
    `session_factory`: für Post-Hooks im Hintergrund, eine kurze eigene Session je Aufruf.

    Dieser Adapter bleibt ausdrücklich nur lesend. Die App verwendet den erweiterten
    Adapter `plugins.schreiben.DatenZugriff` für transaktionale Schreibzugriffe.
    """

    def __init__(self, session=None, session_factory=None):
        if (session is None) == (session_factory is None):
            raise ValueError("Genau eines von session oder session_factory angeben")
        self._session = session
        self._factory = session_factory

    def _mit_session(self, fn):
        if self._session is not None:
            return fn(self._session)
        db = self._factory()
        try:
            return fn(db)
        finally:
            db.rollback()
            db.close()

    @staticmethod
    def _definition(entity: str):
        from . import dto
        if entity in dto.NICHT_UNTERSTUETZT:
            raise HostApiFehler("validation-error", dto.NICHT_UNTERSTUETZT[entity])
        d = dto.ENTITAETEN.get(entity)
        if d is None:
            raise HostApiFehler("validation-error", f"Unbekannte Entität „{entity}“")
        return d

    def get(self, plugin_id: str, entity: str, id: str) -> str:
        import json
        from . import dto

        d = self._definition(entity)
        try:
            schluessel = int(id)
        except (TypeError, ValueError):
            raise HostApiFehler("validation-error", f"Ungültige ID „{id}“") from None

        def lesen(db):
            obj = db.get(d.modell, schluessel)
            if obj is None:
                raise HostApiFehler("not-found", f"{entity} {schluessel} nicht gefunden")
            return json.dumps(dto.als_dto(obj), ensure_ascii=False)
        return self._mit_session(lesen)

    def list(self, plugin_id: str, entity: str, filter_json: str | None) -> str:
        import json
        from . import dto

        d = self._definition(entity)

        def lesen(db):
            try:
                query = dto.filter_anwenden(db.query(d.modell), d, filter_json)
            except ValueError as e:
                raise HostApiFehler("validation-error", str(e)) from None
            return json.dumps([dto.als_dto(o) for o in query.all()], ensure_ascii=False)
        return self._mit_session(lesen)

    def _schreiben(self, plugin_id: str, entity: str, *_):
        self._definition(entity)
        raise HostApiFehler(
            "validation-error",
            "Dieser Host-Adapter ist nur lesend; Schreibzugriffe benötigen DatenZugriff",
        )

    create = update = delete = _schreiben
