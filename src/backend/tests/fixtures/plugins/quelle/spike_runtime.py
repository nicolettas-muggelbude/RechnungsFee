"""
Phase-0-Spike: wasmtime-py als Host für RechnungsFee-Plugins (Component Model).

Prüft: Laden, Typ-Introspektion, Host-Imports, Aufrufe (ok/err), Endlosschleife per
Epoch-Interruption, Trap, Speicherlimit, Messwerte. Aufruf: python spike_runtime.py testplugin.wasm
"""
import json
import statistics
import sys
import threading
import time

import wasmtime
from wasmtime.component import Component, Linker, Record, Variant

WASM = sys.argv[1] if len(sys.argv) > 1 else str(__import__("pathlib").Path(__file__).parent.parent / "testplugin.wasm")
API = "0.1.0"

cfg = wasmtime.Config()
cfg.epoch_interruption = True
cfg.wasm_component_model = True
engine = wasmtime.Engine(cfg)

# Epoch-Ticker: 1 Tick pro Millisekunde. Deadline N Ticks ~ N ms Laufzeit.
_stop = threading.Event()


def _ticker():
    while not _stop.is_set():
        time.sleep(0.001)
        engine.increment_epoch()


threading.Thread(target=_ticker, daemon=True).start()

ergebnisse = {}

t0 = time.perf_counter()
daten = open(WASM, "rb").read()
comp = Component(engine, daten)
ergebnisse["kompilieren_ms"] = round((time.perf_counter() - t0) * 1000, 2)

# Serialisierter Cache (spätere Option: kompiliertes Artefakt auf Platte cachen)
t0 = time.perf_counter()
ser = comp.serialize()
comp2 = Component.deserialize(engine, ser)
ergebnisse["deserialisieren_ms"] = round((time.perf_counter() - t0) * 1000, 2)

host_aufrufe = []


def host_get(store, entity, id_):
    host_aufrufe.append(("get", entity, id_))
    if id_ == "42":
        return json.dumps({"id": 42, "entity": entity, "betrag": "119.00"})
    return Variant("not-found", f"{entity} {id_} nicht gefunden")


def host_list(store, entity, filter_json):
    host_aufrufe.append(("list", entity, filter_json))
    return "[]"


def host_create(store, entity, payload):
    host_aufrufe.append(("create", entity, payload))
    return json.dumps({"id": 1})


def host_update(store, entity, id_, payload):
    host_aufrufe.append(("update", entity, id_, payload))
    return Variant("unauthorized", "keine Berechtigung")


def host_delete(store, entity, id_):
    host_aufrufe.append(("delete", entity, id_))
    return Variant("unauthorized", "keine Berechtigung")


linker = Linker(engine)
with linker.root() as root:
    with root.add_instance(f"rechnungsfee:plugin/host-api@{API}") as host:
        host.add_func("get", host_get)
        host.add_func("list", host_list)
        host.add_func("create", host_create)
        host.add_func("update", host_update)
        host.add_func("delete", host_delete)


def instanz(speicher_mb=64):
    store = wasmtime.Store(engine)
    store.set_limits(memory_size=speicher_mb * 1024 * 1024)
    store.set_epoch_deadline(1_000_000)
    inst = linker.instantiate(store, comp)
    idx = comp.get_export_index(f"rechnungsfee:plugin/event-handler@{API}")
    before = inst.get_func(store, comp.get_export_index("on-before-change", idx))
    after = inst.get_func(store, comp.get_export_index("on-after-change", idx))
    return store, before, after


def ctx(action="create"):
    r = Record()
    setattr(r, "event-id", "evt-1")
    setattr(r, "timestamp", "2026-10-28T11:30:00+01:00")
    setattr(r, "entity", "invoice")
    setattr(r, "action", action)
    return r


def aufruf(func, store, *args, deadline_ms=None):
    if deadline_ms is not None:
        store.set_epoch_deadline(deadline_ms)
    t0 = time.perf_counter()
    try:
        r = func(store, *args)
        func.post_return(store)
        return r, (time.perf_counter() - t0) * 1000, None
    except (wasmtime.Trap, wasmtime.WasmtimeError) as e:
        return None, (time.perf_counter() - t0) * 1000, e


# 1) Instanziieren
zeiten = []
for _ in range(20):
    t0 = time.perf_counter()
    instanz()
    zeiten.append((time.perf_counter() - t0) * 1000)
ergebnisse["instanziieren_ms_median"] = round(statistics.median(zeiten), 3)

# 2) OK-Pfad mit ~5 KB Payload, warm (gleiche Instanz) - Achtung: Bump-Allocator des
#    Testplugins gibt nie frei, daher pro Messreihe frische Instanz
payload = json.dumps({"kunde": "Muster GmbH", "positionen": [{"text": "x" * 40, "betrag": "10.00"}] * 80})
ergebnisse["payload_bytes"] = len(payload)
store, before, after = instanz()
r, _, err = aufruf(before, store, ctx(), payload)
assert err is None, err
assert isinstance(r, Variant) and r.tag == "ok", r
assert json.loads(r.payload)["original"] == json.loads(payload)
warm = []
for _ in range(200):
    r, ms, err = aufruf(before, store, ctx(), payload)
    warm.append(ms)
ergebnisse["pre_hook_warm_ms_median"] = round(statistics.median(warm), 3)
ergebnisse["pre_hook_warm_ms_p99"] = round(sorted(warm)[int(len(warm) * 0.99) - 1], 3)

# 3) Frische Instanz pro Aufruf (Isolation zwischen Aufrufen)
kalt = []
for _ in range(50):
    t0 = time.perf_counter()
    store, before, after = instanz()
    aufruf(before, store, ctx(), payload)
    kalt.append((time.perf_counter() - t0) * 1000)
ergebnisse["pre_hook_frische_instanz_ms_median"] = round(statistics.median(kalt), 3)

# 4) err -> Abbruch
store, before, after = instanz()
r, _, err = aufruf(before, store, ctx(), '{"abbrechen": true}')
assert r == Variant("err", "Pflichtfeld fehlt"), r
ergebnisse["abbruch"] = "ok: err('Pflichtfeld fehlt')"

# 5) Host-Aufruf aus dem Pre-Hook
host_aufrufe.clear()
r, ms, err = aufruf(before, store, ctx(), '{"host-get": 1}')
assert err is None and r.tag == "ok" and json.loads(r.payload)["id"] == 42, (r, err)
assert host_aufrufe == [("get", "invoice", "42")], host_aufrufe
ergebnisse["host_get_roundtrip_ms"] = round(ms, 3)

# 6) Post-Hook ruft host-api.create(task, ...)
host_aufrufe.clear()
r, ms, err = aufruf(after, store, ctx(), '{"rechnung": 42}')
assert err is None and r is None
assert host_aufrufe == [("create", "task", '{"rechnung": 42}')], host_aufrufe
ergebnisse["post_hook_host_create"] = "ok"

# 7) Endlosschleife -> Epoch-Deadline 50 ms
store, before, after = instanz()
r, ms, err = aufruf(before, store, ctx(), '{"endlos": 1}', deadline_ms=50)
assert err is not None, "Endlosschleife wurde nicht abgebrochen"
ergebnisse["endlosschleife_abgebrochen_nach_ms"] = round(ms, 1)
ergebnisse["endlosschleife_fehler"] = type(err).__name__ + ": " + str(err).splitlines()[0]

# 8) Trap -> Exception, Prozess lebt weiter; Instanz danach unbrauchbar, neue Instanz geht
store, before, after = instanz()
r, ms, err = aufruf(before, store, ctx(), '{"trap": 1}')
assert err is not None
ergebnisse["trap_fehler"] = type(err).__name__ + ": " + str(err).splitlines()[0]
store, before, after = instanz()
r, _, err = aufruf(before, store, ctx(), "{}")
assert err is None and r.tag == "ok"
ergebnisse["nach_trap_neue_instanz"] = "ok"

# 9) Speicherlimit 16 MB
store, before, after = instanz(speicher_mb=16)
r, ms, err = aufruf(before, store, ctx(), '{"speicher": 1}')
assert err is not None
ergebnisse["speicherlimit_fehler"] = type(err).__name__ + ": " + str(err).splitlines()[0]

# 10) Mehrere Threads parallel (Post-Hook-Worker + Request-Thread)
fehler_threads = []


def thread_lauf():
    try:
        s, b, a = instanz()
        for _ in range(50):
            r, _, e = aufruf(b, s, ctx(), "{}")
            assert e is None and r.tag == "ok"
    except Exception as e:  # noqa
        fehler_threads.append(e)


ts = [threading.Thread(target=thread_lauf) for _ in range(4)]
[t.start() for t in ts]
[t.join() for t in ts]
ergebnisse["parallel_4_threads"] = "ok" if not fehler_threads else repr(fehler_threads[0])

_stop.set()
ergebnisse["wasmtime_version"] = wasmtime.__version__ if hasattr(wasmtime, "__version__") else "?"
print(json.dumps(ergebnisse, indent=2, ensure_ascii=False))
