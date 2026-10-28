"""
Plugin-Laufzeit (docs/plan-plugin-system.md, Phase 3).

Führt Plugins in der wasmtime-Sandbox aus:

- `vor_aenderung()`  - Pre-Hooks synchron, in fester Reihenfolge (Plugin-ID), mit gemeinsamem
                       Zeitbudget (NFA-3: 50 ms pro Vorgang). Ein Plugin kann den Payload ändern
                       (Plugin 2 sieht die Änderung von Plugin 1) oder mit `PluginAbbruch` abbrechen.
- `nach_aenderung()` - Post-Hooks asynchron im Hintergrund-Thread.
- `testlauf()`       - Ein Hook eines einzelnen Plugins ausprobieren (Einstellungsseite), ohne
                       Datenzugriff und ohne Einfluss auf den Fehlerzähler.

Isolation: jeder Aufruf bekommt eine frische Instanz (eigener Speicher, kein Zustand zwischen
Aufrufen) - laut Spike ~0,6 ms. Kein WASI, nur die Host-API. Laufzeit per Epoch-Interruption
begrenzt, Speicher per Store-Limit.

Fehler (Trap, Timeout, ungültige Antwort) werden protokolliert und gezählt; nach
`FEHLER_BIS_ABSCHALTUNG` Fehlern in Folge wird das Plugin automatisch abgeschaltet. Ein Abbruch mit
eigener Meldung (`err(reason)`) ist kein Fehler, sondern gewolltes Verhalten.

Datenbankzugriffe dieses Moduls (Protokoll, Fehlerzähler) laufen ausschließlich im
Hintergrund-Thread mit eigener Session: der Aufrufer steckt typischerweise mitten in einer
Schreib-Transaktion, ein zweiter Schreiber im selben Thread würde auf dessen SQLite-Lock warten.
"""
from __future__ import annotations

import atexit
import contextvars
import json
import logging
import math
import queue
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .debug_plugin import schreiben as debug_schreiben
from .host_api import HostApi, HostApiFehler, KeinDatenzugriff, pruefe_recht
from .manifest import UNTERSTUETZTE_API_VERSIONEN
from . import registry, wasm_pruefung

log = logging.getLogger("rechnungsfee.plugins")

# --- Grenzwerte -------------------------------------------------------------
PRE_HOOK_BUDGET_MS = 50          # NFA-3: Gesamtzeit aller Pre-Hooks pro Vorgang
POST_HOOK_DEADLINE_MS = 5000     # je Post-Hook-Aufruf
TESTLAUF_DEADLINE_MS = 1000
SPEICHER_LIMIT_BYTES = 64 * 1024 * 1024
MAX_ANTWORT_BYTES = 1024 * 1024  # geänderter Payload aus einem Pre-Hook
MAX_MELDUNG_ZEICHEN = 500
FEHLER_BIS_ABSCHALTUNG = 3
MAX_VERSCHACHTELUNG = 2          # Plugin schreibt per Host-API -> löst wieder Hooks aus
PROTOKOLL_MAX_JE_PLUGIN = 5000

# Offene Frage 3 im Plan: Was passiert, wenn ein Pre-Hook abstürzt oder zu lange braucht?
# True  = Speichern abbrechen (sicher: ein Prüf-Plugin kann nicht unbemerkt übergangen werden)
# False = Plugin überspringen und speichern
BEI_FEHLER_ABBRECHEN = True

_TICK_S = 0.005   # Epoch-Auflösung 5 ms

WIT_PAKET = "rechnungsfee:plugin"


# ---------------------------------------------------------------------------
# Ergebnis-Typen
# ---------------------------------------------------------------------------

@dataclass
class HookErgebnis:
    plugin_id: str
    hook: str
    # ok | geaendert | abgebrochen | fehler | timeout
    ergebnis: str
    payload_json: str | None = None
    meldung: str | None = None
    dauer_ms: float = 0.0


class PluginAbbruch(Exception):
    """Ein Pre-Hook verhindert das Speichern. `meldung` ist für die Anzeige gedacht."""

    def __init__(self, plugin_id: str, plugin_name: str, meldung: str, ergebnis: str = "abgebrochen"):
        super().__init__(f"Plugin „{plugin_name}“: {meldung}")
        self.plugin_id = plugin_id
        self.plugin_name = plugin_name
        self.meldung = meldung
        self.ergebnis = ergebnis

    @property
    def anzeige(self) -> str:
        return str(self)


@dataclass(frozen=True)
class _Ausfuehrbar:
    """Minimal, was ein Aufruf braucht - aus LaufendesPlugin oder (Testlauf) aus dem Manifest."""
    plugin_id: str
    name: str
    wasm_pfad: Path
    wasm_sha256: str
    rechte: dict


# ---------------------------------------------------------------------------
# Epoch-Ticker: tickt nur, solange mindestens ein Plugin-Aufruf läuft
# ---------------------------------------------------------------------------

class _EpochTicker:
    def __init__(self):
        self._bedingung = threading.Condition()
        self._aktiv = 0
        self._thread: threading.Thread | None = None

    def __enter__(self):
        with self._bedingung:
            self._aktiv += 1
            if self._thread is None:
                self._thread = threading.Thread(target=self._lauf, name="plugin-epoch", daemon=True)
                self._thread.start()
            self._bedingung.notify()
        return self

    def __exit__(self, *_):
        with self._bedingung:
            self._aktiv -= 1

    def _lauf(self):
        eng = wasm_pruefung.engine()
        while True:
            with self._bedingung:
                while self._aktiv == 0:
                    self._bedingung.wait()
            time.sleep(_TICK_S)
            eng.increment_epoch()


_ticker = _EpochTicker()


def _deadline_ticks(ms: float) -> int:
    # +1: der laufende Tick kann schon fast vorbei sein - lieber minimal länger als zu früh
    return max(1, math.ceil(ms / (_TICK_S * 1000))) + 1


# ---------------------------------------------------------------------------
# Hintergrund-Thread (Protokoll, Fehlerzähler, Post-Hooks)
# ---------------------------------------------------------------------------

_session_factory = None


def konfiguriere(session_factory=None) -> None:
    """Für Tests: andere Session-Factory (z. B. Test-DB) verwenden. Setzt Zähler zurück."""
    global _session_factory
    _session_factory = session_factory
    with _zaehler_sperre:
        _fehler_zaehler.clear()
        _abgeschaltet.clear()


def _sessions():
    if _session_factory is not None:
        return _session_factory
    from database.connection import SessionLocal
    return SessionLocal


class _Hintergrund:
    def __init__(self):
        self._warteschlange: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self._sperre = threading.Lock()

    def auftrag(self, fn) -> None:
        with self._sperre:
            if self._thread is None:
                self._thread = threading.Thread(target=self._lauf, name="plugin-hintergrund", daemon=True)
                self._thread.start()
        kontext = contextvars.copy_context()
        self._warteschlange.put(lambda: kontext.run(fn))

    def _lauf(self):
        while True:
            fn = self._warteschlange.get()
            try:
                fn()
            except Exception:  # noqa: BLE001 - Hintergrund darf nie sterben
                log.exception("Plugin-Hintergrundauftrag fehlgeschlagen")
            finally:
                self._warteschlange.task_done()

    def warten(self) -> None:
        """Blockiert, bis alle Aufträge erledigt sind (Tests, geordnetes Herunterfahren).
        Nie aus einer offenen Schreib-Transaktion heraus aufrufen."""
        self._warteschlange.join()


_hintergrund = _Hintergrund()
warte_auf_hintergrund = _hintergrund.warten

_protokoll_seit_aufraeumen = 0


def _protokolliere(plugin_id: str, hook: str, ergebnis: str, meldung: str | None = None,
                   dauer_ms: float | None = None, entitaet: str | None = None) -> None:
    debug_schreiben("plugins", plugin_id=plugin_id, hook=hook, ergebnis=ergebnis, dauer_ms=dauer_ms)

    def schreiben():
        global _protokoll_seit_aufraeumen
        db = _sessions()()
        try:
            registry.protokolliere(db, plugin_id, hook, ergebnis, meldung,
                                   dauer_ms=None if dauer_ms is None else int(round(dauer_ms)),
                                   entitaet=entitaet)
            db.commit()
            _protokoll_seit_aufraeumen += 1
            if _protokoll_seit_aufraeumen >= 200:
                _protokoll_seit_aufraeumen = 0
                _protokoll_kuerzen(db)
        finally:
            db.close()
    _hintergrund.auftrag(schreiben)


def _protokoll_kuerzen(db) -> None:
    from sqlalchemy import text
    db.execute(text("""
        DELETE FROM plugin_protokoll WHERE id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (PARTITION BY plugin_id ORDER BY id DESC) AS nr
                FROM plugin_protokoll
            ) WHERE nr > :max
        )
    """), {"max": PROTOKOLL_MAX_JE_PLUGIN})
    db.commit()


# ---------------------------------------------------------------------------
# Fehlerzähler / automatische Abschaltung
# ---------------------------------------------------------------------------

_zaehler_sperre = threading.Lock()
_fehler_zaehler: dict[str, int] = {}
_abgeschaltet: set[str] = set()
_zaehler_generation = -1


def _synchronisiere_zaehler() -> None:
    """Ändert sich der Registry-Status (z. B. Plugin wieder eingeschaltet), gilt wieder der
    Stand aus der Datenbank."""
    global _zaehler_generation
    if registry._generation != _zaehler_generation:
        _fehler_zaehler.clear()
        _abgeschaltet.clear()
        _zaehler_generation = registry._generation


def _ist_abgeschaltet(plugin_id: str) -> bool:
    with _zaehler_sperre:
        _synchronisiere_zaehler()
        return plugin_id in _abgeschaltet


def _erfolg(p: registry.LaufendesPlugin) -> None:
    with _zaehler_sperre:
        _synchronisiere_zaehler()
        vorher = _fehler_zaehler.get(p.plugin_id, p.fehler_in_folge)
        _fehler_zaehler[p.plugin_id] = 0
    if vorher:
        _schreibe_status(p.plugin_id, 0, None, False)


def _fehlschlag(p: registry.LaufendesPlugin, meldung: str) -> None:
    with _zaehler_sperre:
        _synchronisiere_zaehler()
        anzahl = _fehler_zaehler.get(p.plugin_id, p.fehler_in_folge) + 1
        _fehler_zaehler[p.plugin_id] = anzahl
        abschalten = anzahl >= FEHLER_BIS_ABSCHALTUNG and p.plugin_id not in _abgeschaltet
        if abschalten:
            _abgeschaltet.add(p.plugin_id)
    _schreibe_status(p.plugin_id, anzahl, meldung, abschalten)
    if abschalten:
        log.warning("Plugin %s nach %d Fehlern in Folge automatisch abgeschaltet", p.plugin_id, anzahl)


def _schreibe_status(plugin_id: str, anzahl: int, meldung: str | None, abschalten: bool) -> None:
    from database.models import PluginStatus

    def schreiben():
        db = _sessions()()
        try:
            zeile = db.get(PluginStatus, plugin_id)
            if zeile is None:
                return
            zeile.fehler_in_folge = anzahl
            if meldung:
                zeile.letzter_fehler = meldung
                zeile.letzter_fehler_am = datetime.now()
            if abschalten:
                zeile.automatisch_deaktiviert = True
                registry.protokolliere(db, plugin_id, "verwaltung", "automatisch_deaktiviert",
                                       f"Nach {anzahl} Fehlern in Folge abgeschaltet: {meldung}")
            db.commit()
        finally:
            db.close()
        if abschalten:
            registry.status_geaendert()
    _hintergrund.auftrag(schreiben)


# ---------------------------------------------------------------------------
# Components, Linker, Host-Funktionen
# ---------------------------------------------------------------------------

_components: dict[str, tuple[object, str]] = {}   # sha256 -> (Component, Export-Name event-handler)


def _aufraeumen() -> None:
    """Vor dem Interpreter-Shutdown freigeben (sonst „NoneType object is not callable“ aus
    wasmtime-__del__, weil die ctypes-Bindings dann schon weg sind). Läuft vor dem Schließen der
    Engine, weil später registriert (atexit = LIFO)."""
    global _linker
    with _component_sperre:
        for comp, _ in _components.values():
            comp.close()
        _components.clear()
    if _linker is not None:
        _linker.close()
        _linker = None


_aufraeumen_registriert = False


def _engine_mit_aufraeumen():
    """wasm_pruefung.engine() + einmalig _aufraeumen registrieren - NACH dem Engine-atexit, damit
    es (LIFO) vor dem Schließen der Engine läuft."""
    global _aufraeumen_registriert
    eng = wasm_pruefung.engine()
    if not _aufraeumen_registriert:
        _aufraeumen_registriert = True
        atexit.register(_aufraeumen)
    return eng
_component_sperre = threading.Lock()
_linker = None
_linker_sperre = threading.Lock()


@dataclass
class _Kontext:
    plugin_id: str
    rechte: dict
    host: HostApi


# Stapel statt Einzelwert: ein Plugin kann per Host-API schreiben und damit (Phase 5) im selben
# Thread weitere Hooks auslösen.
_kontext: contextvars.ContextVar[tuple[_Kontext, ...]] = contextvars.ContextVar("plugin_kontext", default=())


def _component(p: _Ausfuehrbar):
    with _component_sperre:
        treffer = _components.get(p.wasm_sha256)
    if treffer:
        return treffer
    from wasmtime.component import Component

    eng = _engine_mit_aufraeumen()
    comp = Component(eng, p.wasm_pfad.read_bytes())
    export = None
    for api in UNTERSTUETZTE_API_VERSIONEN:
        name = f"{WIT_PAKET}/event-handler@{api}"
        if comp.get_export_index(name) is not None:
            export = name
            break
    if export is None:
        raise RuntimeError("Plugin exportiert keine unterstützte event-handler-Schnittstelle")
    with _component_sperre:
        _components[p.wasm_sha256] = (comp, export)
    return comp, export


def _host_aufruf(funktion: str, entity: str, *args):
    from wasmtime.component import Variant

    stapel = _kontext.get()
    if not stapel:
        return Variant("internal-error", "Host-API außerhalb eines Plugin-Aufrufs")
    k = stapel[-1]
    start = time.perf_counter()
    status = "ok"
    try:
        pruefe_recht(k.rechte, funktion, entity)
        ergebnis = getattr(k.host, funktion)(k.plugin_id, entity, *args)
        if funktion == "delete":
            return None
        if not isinstance(ergebnis, str):
            ergebnis = json.dumps(ergebnis, ensure_ascii=False, default=str)
        return ergebnis
    except HostApiFehler as e:
        status = e.art
        return Variant(e.art, e.meldung[:MAX_MELDUNG_ZEICHEN])
    except Exception:  # noqa: BLE001 - nie eine Python-Exception in den Wasm-Stack werfen
        status = "internal-error"
        log.exception("Host-API %s(%s) für Plugin %s fehlgeschlagen", funktion, entity, k.plugin_id)
        return Variant("internal-error", "Interner Fehler in RechnungsFee")
    finally:
        debug_schreiben("plugins", plugin_id=k.plugin_id, hook=f"host:{entity}:{funktion}",
                         ergebnis=status, dauer_ms=round((time.perf_counter() - start) * 1000, 2))


def _linker_holen():
    global _linker
    with _linker_sperre:
        if _linker is not None:
            return _linker
        from wasmtime.component import Linker

        linker = Linker(_engine_mit_aufraeumen())
        with linker.root() as root:
            for api in UNTERSTUETZTE_API_VERSIONEN:
                with root.add_instance(f"{WIT_PAKET}/host-api@{api}") as host:
                    host.add_func("get", lambda _s, entity, id_: _host_aufruf("get", entity, id_))
                    host.add_func("list", lambda _s, entity, f: _host_aufruf("list", entity, f))
                    host.add_func("create", lambda _s, entity, p: _host_aufruf("create", entity, p))
                    host.add_func("update", lambda _s, entity, id_, p: _host_aufruf("update", entity, id_, p))
                    host.add_func("delete", lambda _s, entity, id_: _host_aufruf("delete", entity, id_))
        _linker = linker
        return _linker


def _event_kontext(entity: str, action: str):
    from wasmtime.component import Record

    r = Record()
    setattr(r, "event-id", uuid.uuid4().hex)
    setattr(r, "timestamp", datetime.now().astimezone().isoformat(timespec="milliseconds"))
    setattr(r, "entity", entity)
    setattr(r, "action", action)
    return r


def _fehlertext(e: Exception) -> tuple[str, str]:
    """(ergebnis, meldung) aus einem wasmtime-Fehler. Die Ursache steht nach „Caused by:“."""
    text = str(e)
    if "wasm trap: interrupt" in text:
        return "timeout", "Zeitlimit überschritten"
    ursache = text.split("Caused by:")[-1].strip().splitlines()
    zeile = ursache[0].strip() if ursache else text.splitlines()[0]
    zeile = zeile.replace("wasm trap: ", "")
    if "unreachable" in zeile:
        zeile = "Absturz im Plugin"
    return "fehler", zeile[:MAX_MELDUNG_ZEICHEN]


def _rufe_auf(p: _Ausfuehrbar, phase: str, entity: str, action: str, payload_json: str,
              deadline_ms: float, host: HostApi) -> HookErgebnis:
    """Ein einzelner Aufruf in frischer Instanz. Wirft nie (außer bei Programmierfehlern hier)."""
    import wasmtime
    from wasmtime.component import Variant

    hook = f"{entity}:{action}:{phase}"
    start = time.perf_counter()

    def ergebnis(art, payload=None, meldung=None):
        return HookErgebnis(p.plugin_id, hook, art, payload, meldung, (time.perf_counter() - start) * 1000)

    try:
        comp, export = _component(p)
    except (OSError, RuntimeError, wasmtime.WasmtimeError) as e:
        return ergebnis("fehler", meldung=f"Plugin kann nicht geladen werden: {str(e).splitlines()[0]}")

    funktion = "on-before-change" if phase == "before" else "on-after-change"
    store = wasmtime.Store(wasm_pruefung.engine())
    store.set_limits(memory_size=SPEICHER_LIMIT_BYTES)
    token = _kontext.set(_kontext.get() + (_Kontext(p.plugin_id, p.rechte, host),))
    try:
        with _ticker:
            store.set_epoch_deadline(_deadline_ticks(deadline_ms))
            try:
                instanz = _linker_holen().instantiate(store, comp)
                handler = comp.get_export_index(export)
                func = instanz.get_func(store, comp.get_export_index(funktion, handler))
                antwort = func(store, _event_kontext(entity, action), payload_json)
                func.post_return(store)
            except (wasmtime.WasmtimeError, wasmtime.Trap) as e:
                art, meldung = _fehlertext(e)
                return ergebnis(art, meldung=meldung)
    finally:
        _kontext.reset(token)
        store.close()

    if phase == "after":
        return ergebnis("ok")

    if not isinstance(antwort, Variant) or antwort.tag not in ("ok", "err") or not isinstance(antwort.payload, str):
        return ergebnis("fehler", meldung="Ungültige Antwort des Plugins")
    if antwort.tag == "err":
        meldung = antwort.payload.strip()[:MAX_MELDUNG_ZEICHEN] or "Speichern vom Plugin abgelehnt"
        return ergebnis("abgebrochen", meldung=meldung)

    neu = antwort.payload
    if len(neu.encode("utf-8")) > MAX_ANTWORT_BYTES:
        return ergebnis("fehler", meldung="Antwort des Plugins ist zu groß")
    try:
        objekt = json.loads(neu)
    except json.JSONDecodeError:
        return ergebnis("fehler", meldung="Plugin hat kein gültiges JSON zurückgegeben")
    if not isinstance(objekt, dict):
        return ergebnis("fehler", meldung="Plugin muss ein JSON-Objekt zurückgeben")
    if neu == payload_json or objekt == json.loads(payload_json):
        return ergebnis("ok", payload_json)
    return ergebnis("geaendert", neu)


def _als_ausfuehrbar(p: registry.LaufendesPlugin) -> _Ausfuehrbar:
    return _Ausfuehrbar(p.plugin_id, p.name, p.wasm_pfad, p.wasm_sha256, p.rechte)


def _plugins_fuer(hook: str) -> list[registry.LaufendesPlugin]:
    aktiv_im_stapel = {k.plugin_id for k in _kontext.get()}
    return [
        p for p in registry.laufende_plugins(_sessions())
        if hook in p.hooks and not _ist_abgeschaltet(p.plugin_id) and p.plugin_id not in aktiv_im_stapel
    ]


# ---------------------------------------------------------------------------
# Öffentliche Schnittstelle
# ---------------------------------------------------------------------------

def irgendein_plugin() -> bool:
    """Läuft überhaupt ein Plugin? Billigster Vorab-Check für die Event-Pipeline."""
    return bool(registry.laufende_plugins(_sessions()))


def hat_hooks(entity: str, action: str, phase: str) -> bool:
    """Schnelle Vorprüfung für Phase 5: lohnt es sich überhaupt, einen Payload zu bauen?"""
    if len(_kontext.get()) >= MAX_VERSCHACHTELUNG:
        return False
    return bool(_plugins_fuer(f"{entity}:{action}:{phase}"))


def vor_aenderung(entity: str, action: str, payload: dict, host: HostApi | None = None,
                  budget_ms: float = PRE_HOOK_BUDGET_MS) -> dict:
    """Führt alle Pre-Hooks für (entity, action) aus und liefert den ggf. geänderten Payload.

    Wirft `PluginAbbruch`, wenn ein Plugin das Speichern ablehnt - oder (bei
    BEI_FEHLER_ABBRECHEN) abstürzt bzw. das Zeitbudget sprengt."""
    if len(_kontext.get()) >= MAX_VERSCHACHTELUNG:
        return payload
    hook = f"{entity}:{action}:before"
    plugins = _plugins_fuer(hook)
    if not plugins:
        return payload
    host = host or KeinDatenzugriff()
    for p in plugins:   # Kompilieren zählt nicht ins Laufzeitbudget
        try:
            _component(_als_ausfuehrbar(p))
        except Exception:  # noqa: BLE001 - Fehler meldet _rufe_auf gleich ordentlich
            pass

    payload_json = json.dumps(payload, ensure_ascii=False, default=str)
    start = time.perf_counter()
    for p in plugins:
        rest = budget_ms - (time.perf_counter() - start) * 1000
        if rest <= 0:
            e = HookErgebnis(p.plugin_id, hook, "timeout", meldung="Zeitbudget aller Plugins aufgebraucht")
        else:
            e = _rufe_auf(_als_ausfuehrbar(p), "before", entity, action, payload_json, rest, host)

        if e.ergebnis in ("ok", "geaendert"):
            _erfolg(p)
            if e.ergebnis == "ok":
                debug_schreiben("plugins", plugin_id=p.plugin_id, hook=hook,
                                 ergebnis=e.ergebnis, dauer_ms=e.dauer_ms)
            if e.ergebnis == "geaendert":
                _protokolliere(p.plugin_id, hook, "geaendert", None, e.dauer_ms, entity)
                payload_json = e.payload_json
            continue
        if e.ergebnis == "abgebrochen":
            _erfolg(p)
            _protokolliere(p.plugin_id, hook, "abgebrochen", e.meldung, e.dauer_ms, entity)
            raise PluginAbbruch(p.plugin_id, p.name, e.meldung)

        # fehler / timeout
        _protokolliere(p.plugin_id, hook, e.ergebnis, e.meldung, e.dauer_ms, entity)
        _fehlschlag(p, e.meldung or e.ergebnis)
        if BEI_FEHLER_ABBRECHEN:
            text = ("hat zu lange gebraucht" if e.ergebnis == "timeout" else "ist auf einen Fehler gestoßen")
            raise PluginAbbruch(p.plugin_id, p.name,
                                f"{text} ({e.meldung}). Das Speichern wurde zur Sicherheit abgebrochen.",
                                ergebnis=e.ergebnis)
    return json.loads(payload_json)


def nach_aenderung(entity: str, action: str, payload: dict, host_factory=None) -> None:
    """Stellt alle Post-Hooks für (entity, action) in den Hintergrund. Kehrt sofort zurück.
    `host_factory()` liefert pro Aufruf eine HostApi (Phase 4: mit eigener Session)."""
    if len(_kontext.get()) >= MAX_VERSCHACHTELUNG:
        return
    hook = f"{entity}:{action}:after"
    plugins = _plugins_fuer(hook)
    if not plugins:
        return
    payload_json = json.dumps(payload, ensure_ascii=False, default=str)
    host_factory = host_factory or KeinDatenzugriff

    def ausfuehren():
        for p in plugins:
            if _ist_abgeschaltet(p.plugin_id):
                continue
            e = _rufe_auf(_als_ausfuehrbar(p), "after", entity, action, payload_json,
                          POST_HOOK_DEADLINE_MS, host_factory())
            if e.ergebnis == "ok":
                _erfolg(p)
                debug_schreiben("plugins", plugin_id=p.plugin_id, hook=hook,
                                 ergebnis=e.ergebnis, dauer_ms=e.dauer_ms)
            else:
                _protokolliere(p.plugin_id, hook, e.ergebnis, e.meldung, e.dauer_ms, entity)
                _fehlschlag(p, e.meldung or e.ergebnis)
    _hintergrund.auftrag(ausfuehren)


def testlauf(g: registry.GefundenesPlugin, hook: str, payload_json: str) -> HookErgebnis:
    """Ruft einen Hook eines einzelnen Plugins zur Probe auf - auch wenn es (noch) nicht aktiv
    ist. Kein Datenzugriff (Host-API antwortet mit Fehler, Rechteprüfung gegen das Manifest),
    kein Einfluss auf den Fehlerzähler. Wird protokolliert."""
    entity, action, phase = hook.split(":")
    p = _Ausfuehrbar(
        g.plugin_id, g.manifest.name, g.verzeichnis / "plugin.wasm", g.wasm_sha256,
        {e: frozenset(a) for e, a in g.manifest.rechte.items()},
    )
    deadline = PRE_HOOK_BUDGET_MS if phase == "before" else TESTLAUF_DEADLINE_MS
    try:
        _component(p)   # Kompilieren nicht ins Zeitlimit rechnen
    except Exception:  # noqa: BLE001
        pass
    e = _rufe_auf(p, phase, entity, action, payload_json, deadline,
                  KeinDatenzugriff("Testlauf: kein Zugriff auf echte Daten"))
    _protokolliere(p.plugin_id, f"test {hook}", e.ergebnis, e.meldung, e.dauer_ms, entity)
    return e
