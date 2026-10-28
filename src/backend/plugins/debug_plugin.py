"""Mitgeliefertes Diagnose-Plugin mit profilbezogenem JSONL-Protokoll.

Bewusst im Host: Wasm-Plugins dürfen weder Dateien schreiben noch UI-/HTTP-Ereignisse
abonnieren. Dieser fest eingebaute Beobachter verändert keine fachlichen Daten und
bleibt auch bei abgeschalteten Fremdplugins verfügbar.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Kategorie = Literal["ui", "navigation", "api", "plugins", "fehler"]
KATEGORIEN = ("ui", "navigation", "api", "plugins", "fehler")
PLUGIN_ID = "org.rechnungsfee.debug"
PREFIX = "/api/debug-plugin"


class DebugEinstellungen(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aktiviert: bool = False
    kategorien: list[Kategorie] = Field(default_factory=lambda: list(KATEGORIEN), max_length=5)


# Nur technische Felder zulassen. Keine Meldungen, Payloads, URLs, Header oder Feldwerte.
FELDER = {
    "ui": {"aktion", "seite", "element", "element_id"},
    "navigation": {"aktion", "seite"},
    "api": {"methode", "route", "status", "dauer_ms", "anfrage_id"},
    "plugins": {"plugin_id", "hook", "ergebnis", "dauer_ms"},
    "fehler": {"quelle", "typ", "route", "status", "anfrage_id"},
}


class DebugPlugin:
    MAX_BYTES = 2 * 1024 * 1024
    BACKUPS = 3

    def __init__(self, profil: Path):
        self.verzeichnis = profil / "logs"
        self.pfad = self.verzeichnis / "interaktionen.jsonl"
        self.einstellungen_pfad = self.verzeichnis / "debug-plugin.json"
        self.lock = threading.RLock()
        self.handler: RotatingFileHandler | None = None
        self.schreibfehler = False
        self.einstellungen = DebugEinstellungen()
        try:
            self.einstellungen = DebugEinstellungen.model_validate_json(
                self.einstellungen_pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass  # Fehlende/defekte Konfiguration: Aufzeichnung bleibt aus.

    def konfigurieren(self, daten: DebugEinstellungen) -> None:
        with self.lock:
            self.verzeichnis.mkdir(parents=True, exist_ok=True)
            temp = self.einstellungen_pfad.with_suffix(".tmp")
            temp.write_text(daten.model_dump_json(), encoding="utf-8")
            os.replace(temp, self.einstellungen_pfad)
            self.einstellungen = daten.model_copy(deep=True)

    def schreiben(self, kategorie: Kategorie, **daten) -> None:
        # Diagnose darf den beobachteten Vorgang auch bei voller Platte nicht verhindern.
        with self.lock:
            if not self.einstellungen.aktiviert or kategorie not in self.einstellungen.kategorien:
                return
            try:
                if self.handler is None:
                    self.verzeichnis.mkdir(parents=True, exist_ok=True)
                    self.handler = RotatingFileHandler(
                        self.pfad, maxBytes=self.MAX_BYTES, backupCount=self.BACKUPS,
                        encoding="utf-8", delay=True)
                eintrag = {"zeit": datetime.now(timezone.utc).isoformat(), "kategorie": kategorie}
                for key, value in daten.items():
                    if key in FELDER[kategorie] and value is not None:
                        eintrag[key] = value[:200] if isinstance(value, str) else value
                zeile = json.dumps(eintrag, ensure_ascii=False, separators=(",", ":"))
                # Direkt schreiben: Handler.emit verschluckt I/O-Fehler mit handleError.
                if self.handler.shouldRollover(logging.makeLogRecord({"msg": zeile})):
                    self.handler.doRollover()
                if self.handler.stream is None:
                    self.handler.stream = self.handler._open()
                self.handler.stream.write(zeile + "\n")
                self.handler.flush()
                self.schreibfehler = False
            except (OSError, ValueError):
                self.schreibfehler = True

    def dateien(self) -> list[Path]:
        return [self.pfad] + [self.pfad.with_name(f"{self.pfad.name}.{n}")
                              for n in range(1, self.BACKUPS + 1)]

    def lesen(self, limit: int = 200, kategorie: Kategorie | None = None) -> list[dict]:
        zeilen = []
        with self.lock:
            for pfad in self.dateien():
                try:
                    # Vom Dateiende lesen: auch bei langen Protokollen begrenzter Speicher.
                    with pfad.open("rb") as datei:
                        datei.seek(0, 2)
                        position, rest = datei.tell(), b""
                        while position:
                            groesse = min(position, 65536)
                            position -= groesse
                            datei.seek(position)
                            teile = (datei.read(groesse) + rest).split(b"\n")
                            rest = teile.pop(0) if position else b""
                            for zeile in reversed(teile):
                                try:
                                    e = json.loads(zeile)
                                except (ValueError, UnicodeDecodeError):
                                    continue
                                if not isinstance(e, dict) or (kategorie and e.get("kategorie") != kategorie):
                                    continue
                                zeilen.append(e)
                                if len(zeilen) >= limit:
                                    return zeilen
                except OSError:
                    continue
        return zeilen

    def schliessen(self):
        with self.lock:
            if self.handler:
                self.handler.close()
                self.handler = None


_instanz: DebugPlugin | None = None
_instanz_lock = threading.Lock()


def instanz() -> DebugPlugin:
    global _instanz
    with _instanz_lock:
        if _instanz is None:
            from database.connection import APP_DATA_DIR
            _instanz = DebugPlugin(APP_DATA_DIR)
        return _instanz


def schreiben(kategorie: Kategorie, **daten) -> None:
    instanz().schreiben(kategorie, **daten)


class FehlerHandler(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.ERROR:
            schreiben("fehler", quelle=record.name,
                       typ=record.exc_info[0].__name__ if record.exc_info and record.exc_info[0] else record.levelname)


class DebugMiddleware:
    """Reine ASGI-Middleware: erfasst auch Streaming-Antworten und fehlgeschlagene Requests."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"].startswith(PREFIX):
            await self.app(scope, receive, send)
            return
        import uuid
        anfrage_id = uuid.uuid4().hex
        start, status = time.perf_counter(), 500
        fehler = None

        async def antwort(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, antwort)
        except Exception as exc:
            fehler = type(exc).__name__
            raise
        finally:
            # Die Routenvorlage enthält keine echten IDs, Dateinamen oder Query-Parameter.
            route = getattr(scope.get("route"), "path", "<unbekannt>")
            schreiben("api", methode=scope["method"], route=route, status=status,
                       dauer_ms=round((time.perf_counter() - start) * 1000, 2), anfrage_id=anfrage_id)
            if fehler or status >= 400:
                schreiben("fehler", quelle="backend", typ=fehler or "HTTPFehler", route=route,
                           status=status, anfrage_id=anfrage_id)
