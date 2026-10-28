"""
Statische Prüfung einer plugin.wasm, ohne Plugin-Code auszuführen.

Kompiliert die Datei als WebAssembly-Component und prüft deren Typ gegen die Welt
`rechnungsfee:plugin/plugin-world` (plugins/wit/rechnungsfee.wit):

- exportiert `rechnungsfee:plugin/event-handler@<api>` mit on-before-change + on-after-change
- importiert nichts außer `rechnungsfee:plugin/host-api` und `.../types` - insbesondere kein WASI
  (Dateisystem, Netzwerk, Uhr, Zufall ...). So scheitert ein Plugin, das mehr will als die Sandbox
  erlaubt, schon beim Einlesen mit verständlicher Meldung statt erst beim ersten Aufruf.

Ergebnis wird pro SHA-256 im Speicher gecacht (Kompilieren dauert je nach Größe 10-500 ms).
Phase 0 (docs/plan-plugin-system.md): wasmtime-py >= 50 bringt eine native Component-API mit,
Code-Generierung (wasmtime.bindgen) ist nicht nötig.
"""
from __future__ import annotations

import atexit
import threading
from pathlib import Path

from .manifest import UNTERSTUETZTE_API_VERSIONEN

WIT_PAKET = "rechnungsfee:plugin"
EXPORT_FUNKTIONEN = ("on-before-change", "on-after-change")

_cache: dict[str, list[str]] = {}
_cache_sperre = threading.Lock()
_engine = None
_engine_sperre = threading.Lock()


def engine():
    """Gemeinsame wasmtime-Engine. Epoch-Interruption ist schon hier aktiv, weil eine Component
    nur mit einer Engine gleicher Konfiguration ausgeführt werden kann (Laufzeit, Phase 3)."""
    global _engine
    with _engine_sperre:
        if _engine is None:
            import wasmtime
            cfg = wasmtime.Config()
            cfg.epoch_interruption = True
            cfg.wasm_component_model = True
            _engine = wasmtime.Engine(cfg)
            # Vor dem Interpreter-Shutdown freigeben - sonst räumt __del__ die Engine erst auf,
            # wenn die ctypes-Bindings schon weg sind („NoneType object is not callable“).
            atexit.register(_engine.close)
        return _engine


def _erlaubte_importe(api: str) -> set[str]:
    return {f"{WIT_PAKET}/host-api@{api}", f"{WIT_PAKET}/types@{api}"}


def pruefe_component_bytes(daten: bytes) -> list[str]:
    """Liefert eine Liste von Fehlermeldungen (leer = kompatibel)."""
    try:
        import wasmtime
        from wasmtime.component import Component
    except ImportError:  # pragma: no cover - nur bei kaputter Installation
        return ["Die Plugin-Laufzeit (wasmtime) ist in dieser Installation nicht verfügbar"]

    # Ohne diese Prüfung versucht wasmtime, beliebige Bytes als WAT-Text zu parsen
    # („expected `(`“) - wenig hilfreich für Nutzer.
    if not daten.startswith(b"\0asm"):
        return ["plugin.wasm ist keine WebAssembly-Datei"]

    eng = engine()
    try:
        comp = Component(eng, daten)
    except wasmtime.WasmtimeError as e:
        text = str(e).splitlines()[0] if str(e) else "unbekannter Fehler"
        if "component" in str(e).lower() and "module" in str(e).lower():
            return ["plugin.wasm ist ein Wasm-Modul, aber keine WebAssembly-Component (mit `cargo component build` bauen)"]
        return [f"plugin.wasm kann nicht geladen werden: {text}"]

    try:
        return _pruefe_typ(comp, eng)
    finally:
        comp.close()


def _pruefe_typ(comp, eng) -> list[str]:
    import wasmtime

    typ = comp.type
    importe = set(typ.imports(eng))
    exporte = typ.exports(eng)

    fehler: list[str] = []
    passende_api = None
    for api in UNTERSTUETZTE_API_VERSIONEN:
        if f"{WIT_PAKET}/event-handler@{api}" in exporte:
            passende_api = api
            break
    if passende_api is None:
        andere = sorted(n for n in exporte if n.startswith(f"{WIT_PAKET}/event-handler@"))
        if andere:
            fehler.append(
                f"Das Plugin wurde für eine andere Plugin-Schnittstelle gebaut ({andere[0].split('@')[-1]}); "
                f"unterstützt: {', '.join(UNTERSTUETZTE_API_VERSIONEN)}"
            )
        else:
            fehler.append(f"Das Plugin exportiert die Schnittstelle {WIT_PAKET}/event-handler nicht")
        return fehler

    handler = exporte[f"{WIT_PAKET}/event-handler@{passende_api}"]
    try:
        funktionen = set(handler.ty.exports(eng))
    except (AttributeError, TypeError, wasmtime.WasmtimeError):
        funktionen = set()
    for f in EXPORT_FUNKTIONEN:
        if f not in funktionen:
            fehler.append(f"Das Plugin implementiert {f} nicht")

    fremd = sorted(importe - _erlaubte_importe(passende_api))
    if fremd:
        fehler.append(
            "Das Plugin verlangt Schnittstellen, die RechnungsFee Plugins nicht bereitstellt "
            f"(z. B. Datei- oder Netzwerkzugriff): {', '.join(fremd)}"
        )
    return fehler


def pruefe_component(pfad: Path, sha256: str) -> list[str]:
    with _cache_sperre:
        if sha256 in _cache:
            return list(_cache[sha256])
    ergebnis = pruefe_component_bytes(pfad.read_bytes())
    with _cache_sperre:
        _cache[sha256] = ergebnis
    return list(ergebnis)
