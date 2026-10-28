"""
Plugin-Laufzeit, Phase 3 (docs/plan-plugin-system.md): Pre-/Post-Hooks in der wasmtime-Sandbox,
Zeitbudget, Abbruch, Fehlerzähler/automatische Abschaltung, Rechteprüfung der Host-API,
Verschachtelung, Testlauf.

Das Test-Plugin (tests/fixtures/plugins/testplugin.wasm, Quelle quelle/testplugin.c) reagiert auf
Stichworte im Payload: "abbrechen", "host-get", "endlos", "trap", "speicher"; sonst liefert es
{"geprueft": true, "original": <payload>}. on-after-change ruft host-api.create(task, payload).
"""
import json
import shutil
import time
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import PluginProtokoll, PluginStatus
from plugins import laufzeit, registry
from plugins.host_api import HostApiFehler

FIXTURES = Path(__file__).parent / "fixtures" / "plugins"
ID = "org.rechnungsfee.task-automation"

MANIFEST = """
[plugin]
id = "{id}"
name = "{name}"
version = "0.1.0"
author = "Test"
description = "Test"
api_version = "0.1.0"

[permissions]
entities = [
    {{ type = "invoice", actions = [{invoice}] }},
    {{ type = "task", actions = ["create", "read", "update"] }}
]
hooks = ["invoice:create:before", "invoice:create:after", "invoice:update:before"]
"""


def manifest(plugin_id=ID, name="Task Automation", invoice='"read"'):
    return MANIFEST.format(id=plugin_id, name=name, invoice=invoice)


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()
    monkeypatch.setenv("RECHNUNGSFEE_PLUGIN_DIR", str(plugin_dir))
    monkeypatch.delenv("RECHNUNGSFEE_PLUGINS", raising=False)
    # Datei-DB statt :memory:, weil der Hintergrund-Thread eine eigene Verbindung öffnet
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    laufzeit.konfiguriere(sf)
    registry.status_geaendert()
    yield plugin_dir, sf
    laufzeit.warte_auf_hintergrund()
    laufzeit.konfiguriere(None)
    engine.dispose()


def installiere(plugin_dir: Path, sf, plugin_id=ID, name="Task Automation", invoice='"read"', aktivieren=True):
    ordner = plugin_dir / plugin_id
    ordner.mkdir(exist_ok=True)
    (ordner / "plugin.toml").write_text(manifest(plugin_id, name, invoice), encoding="utf-8")
    shutil.copy(FIXTURES / "testplugin.wasm", ordner / "plugin.wasm")
    db = sf()
    try:
        if aktivieren:
            z = registry.zustand(db, plugin_id)
            registry.aktivieren(db, plugin_id, z.gefunden.wasm_sha256, z.gefunden.manifest.rechte_snapshot())
        registry.global_setzen(db, True)
    finally:
        db.close()


def status(sf, plugin_id=ID) -> PluginStatus:
    laufzeit.warte_auf_hintergrund()
    db = sf()
    try:
        z = db.get(PluginStatus, plugin_id)
        db.expunge(z)
        return z
    finally:
        db.close()


def protokoll(sf, plugin_id=ID) -> list[tuple[str, str]]:
    laufzeit.warte_auf_hintergrund()
    db = sf()
    try:
        return [(p.hook, p.ergebnis) for p in
                db.query(PluginProtokoll).filter_by(plugin_id=plugin_id).order_by(PluginProtokoll.id)
                if p.hook != "verwaltung"]
    finally:
        db.close()


class AufzeichnenderHost:
    def __init__(self, antworten=None):
        self.aufrufe = []
        self.antworten = antworten or {}

    def _merke(self, name, *args):
        self.aufrufe.append((name, *args))
        if name in self.antworten:
            a = self.antworten[name]
            if isinstance(a, Exception):
                raise a
            return a(*args) if callable(a) else a
        return json.dumps({"id": 1})

    def get(self, plugin_id, entity, id):
        return self._merke("get", plugin_id, entity, id)

    def list(self, plugin_id, entity, filter_json):
        return self._merke("list", plugin_id, entity, filter_json)

    def create(self, plugin_id, entity, payload_json):
        return self._merke("create", plugin_id, entity, payload_json)

    def update(self, plugin_id, entity, id, payload_json):
        return self._merke("update", plugin_id, entity, id, payload_json)

    def delete(self, plugin_id, entity, id):
        return self._merke("delete", plugin_id, entity, id)


# ---------------------------------------------------------------------------
# Pre-Hooks
# ---------------------------------------------------------------------------

def test_pre_hook_aendert_payload(umgebung):
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf)
    assert laufzeit.vor_aenderung("invoice", "create", {"betrag": "119.00"}) == {
        "geprueft": True, "original": {"betrag": "119.00"},
    }
    assert protokoll(sf) == [("invoice:create:before", "geaendert")]


def test_ohne_passenden_hook_kein_aufruf(umgebung):
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf)
    payload = {"name": "Muster"}
    assert laufzeit.vor_aenderung("customer", "create", payload) is payload
    assert laufzeit.vor_aenderung("invoice", "delete", payload) is payload
    assert laufzeit.hat_hooks("invoice", "create", "before") is True
    assert laufzeit.hat_hooks("customer", "create", "before") is False
    assert protokoll(sf) == []


def test_laeuft_nicht_wenn_aus(umgebung, monkeypatch):
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf, aktivieren=False)                  # nie bestätigt
    assert laufzeit.vor_aenderung("invoice", "create", {"a": 1}) == {"a": 1}

    installiere(plugin_dir, sf)                                    # bestätigt ...
    db = sf()
    registry.global_setzen(db, False)                              # ... aber Hauptschalter aus
    db.close()
    assert laufzeit.vor_aenderung("invoice", "create", {"a": 1}) == {"a": 1}

    db = sf()
    registry.global_setzen(db, True)
    db.close()
    monkeypatch.setenv("RECHNUNGSFEE_PLUGINS", "0")                # abgesicherter Modus
    assert laufzeit.vor_aenderung("invoice", "create", {"a": 1}) == {"a": 1}


def test_einzeln_abgeschalteter_hook(umgebung):
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf)
    db = sf()
    registry.hooks_setzen(db, ID, ["invoice:create:before"])
    db.close()
    assert laufzeit.vor_aenderung("invoice", "create", {"a": 1}) == {"a": 1}
    assert laufzeit.vor_aenderung("invoice", "update", {"a": 1})["geprueft"] is True


def test_abbruch_durch_plugin_ist_kein_fehler(umgebung):
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf)
    with pytest.raises(laufzeit.PluginAbbruch) as e:
        laufzeit.vor_aenderung("invoice", "create", {"abbrechen": True})
    assert e.value.meldung == "Pflichtfeld fehlt"
    assert e.value.anzeige == "Plugin „Task Automation“: Pflichtfeld fehlt"
    assert status(sf).fehler_in_folge == 0
    assert protokoll(sf) == [("invoice:create:before", "abgebrochen")]


def test_endlosschleife_wird_nach_budget_abgebrochen(umgebung):
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf)
    laufzeit.vor_aenderung("invoice", "create", {})   # kompilieren
    start = time.perf_counter()
    with pytest.raises(laufzeit.PluginAbbruch) as e:
        laufzeit.vor_aenderung("invoice", "create", {"endlos": 1})
    dauer = (time.perf_counter() - start) * 1000
    assert e.value.ergebnis == "timeout"
    assert dauer < 250, dauer
    s = status(sf)
    assert s.fehler_in_folge == 1 and s.letzter_fehler == "Zeitlimit überschritten"


@pytest.mark.parametrize("stichwort, meldung", [("trap", "Absturz im Plugin"), ("speicher", "Absturz im Plugin")])
def test_absturz_und_speicherlimit(umgebung, stichwort, meldung):
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf)
    with pytest.raises(laufzeit.PluginAbbruch) as e:
        laufzeit.vor_aenderung("invoice", "create", {stichwort: 1})
    assert e.value.ergebnis == "fehler"
    assert meldung in e.value.meldung
    # danach sofort wieder nutzbar (frische Instanz je Aufruf)
    assert laufzeit.vor_aenderung("invoice", "create", {"x": 1})["geprueft"] is True


def test_fehler_ueberspringen_wenn_so_eingestellt(umgebung, monkeypatch):
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf)
    monkeypatch.setattr(laufzeit, "BEI_FEHLER_ABBRECHEN", False)
    assert laufzeit.vor_aenderung("invoice", "create", {"trap": 1}) == {"trap": 1}
    assert status(sf).fehler_in_folge == 1


def test_automatische_abschaltung_und_wiedereinschalten(umgebung):
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf)
    for _ in range(laufzeit.FEHLER_BIS_ABSCHALTUNG):
        with pytest.raises(laufzeit.PluginAbbruch):
            laufzeit.vor_aenderung("invoice", "create", {"trap": 1})
    s = status(sf)
    assert s.automatisch_deaktiviert is True and s.fehler_in_folge == 3
    # läuft nicht mehr - Speichern geht wieder durch
    assert laufzeit.vor_aenderung("invoice", "create", {"trap": 1}) == {"trap": 1}
    db = sf()
    assert registry.zustand(db, ID).status == registry.AUTOMATISCH_DEAKTIVIERT
    db.close()

    installiere(plugin_dir, sf)   # Nutzer schaltet wieder ein
    assert status(sf).fehler_in_folge == 0
    assert laufzeit.vor_aenderung("invoice", "create", {"x": 1})["geprueft"] is True


def test_erfolg_setzt_fehlerzaehler_zurueck(umgebung):
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf)
    for _ in range(2):
        with pytest.raises(laufzeit.PluginAbbruch):
            laufzeit.vor_aenderung("invoice", "create", {"trap": 1})
    assert status(sf).fehler_in_folge == 2
    laufzeit.vor_aenderung("invoice", "create", {"x": 1})
    assert status(sf).fehler_in_folge == 0
    with pytest.raises(laufzeit.PluginAbbruch):
        laufzeit.vor_aenderung("invoice", "create", {"trap": 1})
    assert status(sf).automatisch_deaktiviert is False


def test_kette_mehrerer_plugins_in_fester_reihenfolge(umgebung):
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf, plugin_id="de.b.zweites", name="Zweites")
    installiere(plugin_dir, sf, plugin_id="de.a.erstes", name="Erstes")
    ergebnis = laufzeit.vor_aenderung("invoice", "create", {"betrag": "1"})
    # „de.a.erstes“ läuft zuerst, „de.b.zweites“ bekommt dessen Ergebnis
    assert ergebnis == {"geprueft": True, "original": {"geprueft": True, "original": {"betrag": "1"}}}


def test_abbruch_stoppt_die_kette(umgebung):
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf, plugin_id="de.a.erstes", name="Erstes")
    installiere(plugin_dir, sf, plugin_id="de.b.zweites", name="Zweites")
    with pytest.raises(laufzeit.PluginAbbruch) as e:
        laufzeit.vor_aenderung("invoice", "create", {"abbrechen": 1})
    assert e.value.plugin_id == "de.a.erstes"
    assert protokoll(sf, "de.b.zweites") == []


# ---------------------------------------------------------------------------
# Host-API: Rechteprüfung und Weiterleitung
# ---------------------------------------------------------------------------

def test_host_api_mit_recht(umgebung):
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf)
    host = AufzeichnenderHost({"get": json.dumps({"id": 42, "betrag": "119.00"})})
    assert laufzeit.vor_aenderung("invoice", "create", {"host-get": 1}, host=host) == {"id": 42, "betrag": "119.00"}
    assert host.aufrufe == [("get", ID, "invoice", "42")]


def test_host_api_ohne_bestaetigtes_recht(umgebung):
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf, invoice='"create"')   # kein "read" auf invoice
    host = AufzeichnenderHost()
    with pytest.raises(laufzeit.PluginAbbruch) as e:
        laufzeit.vor_aenderung("invoice", "create", {"host-get": 1}, host=host)
    assert "kein bestätigtes Recht „read“ für „invoice“" in e.value.meldung
    assert host.aufrufe == []                         # Implementierung nie erreicht


def test_host_api_fehler_wird_weitergereicht(umgebung):
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf)
    host = AufzeichnenderHost({"get": HostApiFehler("not-found", "Rechnung 42 gibt es nicht")})
    with pytest.raises(laufzeit.PluginAbbruch) as e:
        laufzeit.vor_aenderung("invoice", "create", {"host-get": 1}, host=host)
    assert "Rechnung 42 gibt es nicht" in e.value.meldung


def test_host_api_python_exception_bleibt_drinnen(umgebung):
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf)
    host = AufzeichnenderHost({"get": RuntimeError("geheimes Detail")})
    with pytest.raises(laufzeit.PluginAbbruch) as e:
        laufzeit.vor_aenderung("invoice", "create", {"host-get": 1}, host=host)
    assert "Interner Fehler in RechnungsFee" in e.value.meldung
    assert "geheimes Detail" not in e.value.meldung


def test_verschachtelung_ruft_dasselbe_plugin_nicht_erneut(umgebung):
    """Ein Plugin liest per Host-API, die Implementierung löst dabei wieder einen Pre-Hook
    aus (Phase 5: Schreiben über die ORM). Das aufrufende Plugin darf nicht rekursiv laufen."""
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf)
    innen = []

    def get(_plugin_id, _entity, _id):
        innen.append(laufzeit.vor_aenderung("invoice", "create", {"innen": 1}))
        return json.dumps({"id": 42})

    host = AufzeichnenderHost({"get": get})
    assert laufzeit.vor_aenderung("invoice", "create", {"host-get": 1}, host=host) == {"id": 42}
    assert innen == [{"innen": 1}]   # unverändert durchgereicht, Plugin nicht erneut aufgerufen


# ---------------------------------------------------------------------------
# Post-Hooks
# ---------------------------------------------------------------------------

def test_post_hook_laeuft_im_hintergrund(umgebung):
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf)
    host = AufzeichnenderHost()
    laufzeit.nach_aenderung("invoice", "create", {"id": 7}, host_factory=lambda: host)
    laufzeit.warte_auf_hintergrund()
    assert host.aufrufe == [("create", ID, "task", '{"id": 7}')]


def test_post_hook_ohne_recht_scheitert_still(umgebung):
    plugin_dir, sf = umgebung
    ordner = plugin_dir / ID
    ordner.mkdir()
    (ordner / "plugin.toml").write_text(
        manifest().replace('{ type = "task", actions = ["create", "read", "update"] }', '{ type = "task", actions = ["read"] }'),
        encoding="utf-8")
    shutil.copy(FIXTURES / "testplugin.wasm", ordner / "plugin.wasm")
    db = sf()
    z = registry.zustand(db, ID)
    registry.aktivieren(db, ID, z.gefunden.wasm_sha256, z.gefunden.manifest.rechte_snapshot())
    registry.global_setzen(db, True)
    db.close()
    host = AufzeichnenderHost()
    laufzeit.nach_aenderung("invoice", "create", {"id": 7}, host_factory=lambda: host)
    laufzeit.warte_auf_hintergrund()
    assert host.aufrufe == []   # create(task) ohne Recht -> abgewiesen, das Plugin ignoriert den Fehler


# ---------------------------------------------------------------------------
# Testlauf
# ---------------------------------------------------------------------------

def test_testlauf_auch_ohne_aktivierung(umgebung):
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf, aktivieren=False)
    db = sf()
    g = registry.zustand(db, ID).gefunden
    db.close()

    e = laufzeit.testlauf(g, "invoice:create:before", '{"betrag": "1"}')
    assert e.ergebnis == "geaendert"
    assert json.loads(e.payload_json) == {"geprueft": True, "original": {"betrag": "1"}}

    e = laufzeit.testlauf(g, "invoice:create:before", '{"host-get": 1}')
    assert e.ergebnis == "abgebrochen" and "kein Zugriff auf echte Daten" in e.meldung

    e = laufzeit.testlauf(g, "invoice:create:before", '{"endlos": 1}')
    assert e.ergebnis == "timeout"

    assert [h for h, _ in protokoll(sf)] == ["test invoice:create:before"] * 3


def test_testlauf_zaehlt_nicht_als_fehler(umgebung):
    plugin_dir, sf = umgebung
    installiere(plugin_dir, sf)
    db = sf()
    g = registry.zustand(db, ID).gefunden
    db.close()
    for _ in range(4):
        assert laufzeit.testlauf(g, "invoice:create:before", '{"trap": 1}').ergebnis == "fehler"
    s = status(sf)
    assert s.fehler_in_folge == 0 and s.automatisch_deaktiviert is False
