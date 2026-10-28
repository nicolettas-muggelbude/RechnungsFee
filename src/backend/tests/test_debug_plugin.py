"""Diagnose gegen temporäre Profile testen; main.py und echte Nutzerdaten bleiben unberührt."""
import json
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.debug_plugin import router
from plugins import debug_plugin as debug


@pytest.fixture
def plugin(tmp_path, monkeypatch):
    p = debug.DebugPlugin(tmp_path)
    monkeypatch.setattr(debug, "_instanz", p)
    yield p
    p.schliessen()


def aktivieren(p, kategorien=None):
    p.konfigurieren(debug.DebugEinstellungen(aktiviert=True, kategorien=kategorien or list(debug.KATEGORIEN)))


def test_standard_aus_und_auswahl_persistiert(plugin, tmp_path):
    plugin.schreiben("ui", aktion="klick")
    assert not plugin.pfad.exists()
    aktivieren(plugin, ["api"])
    plugin.schreiben("ui", aktion="klick")
    plugin.schreiben("api", methode="GET", route="/api/kunden")
    assert [e["kategorie"] for e in plugin.lesen()] == ["api"]
    neu = debug.DebugPlugin(tmp_path)
    assert neu.einstellungen.aktiviert
    assert neu.einstellungen.kategorien == ["api"]
    plugin.konfigurieren(debug.DebugEinstellungen(aktiviert=False))
    plugin.schreiben("api", methode="POST")
    assert len(plugin.lesen()) == 1


def test_kein_payload_und_keine_profilvermischung(plugin, tmp_path):
    aktivieren(plugin)
    plugin.schreiben("api", methode="POST", route="/api/kunden", passwort="GEHEIM",
                      payload={"name": "Privat"}, headers={"Authorization": "Token"})
    text = plugin.pfad.read_text()
    assert all(wort not in text for wort in ("GEHEIM", "Privat", "Token", "payload"))
    anderes = debug.DebugPlugin(tmp_path / "anderes-profil")
    assert anderes.lesen() == []
    assert not anderes.einstellungen.aktiviert


def test_rotation_limit_filter_und_beschaedigte_zeile(plugin):
    plugin.MAX_BYTES = 400
    aktivieren(plugin)
    for n in range(20):
        plugin.schreiben("api", status=n)
    assert plugin.pfad.with_name(plugin.pfad.name + ".1").exists()
    assert len(list(plugin.verzeichnis.glob("interaktionen.jsonl*"))) <= 4
    assert [e["status"] for e in plugin.lesen(3)] == [19, 18, 17]
    plugin.schreiben("ui", aktion="klick")
    with plugin.pfad.open("a") as f:
        f.write('defekt\n')
    assert [e["aktion"] for e in plugin.lesen(2, "ui")] == ["klick"]


def test_dateifehler_verhindert_keine_aktion(plugin, monkeypatch):
    aktivieren(plugin)
    def fehler(*args, **kwargs):
        raise OSError("voll")
    monkeypatch.setattr(debug.RotatingFileHandler, "_open", fehler)
    plugin.schreiben("api", status=200)
    assert plugin.schreibfehler


def test_fehlerhandler_speichert_keinen_fehlertext(plugin):
    aktivieren(plugin)
    handler = debug.FehlerHandler()
    try:
        raise ValueError("PASSWORT")
    except ValueError:
        import sys
        handler.emit(logging.makeLogRecord({"name": "test", "levelno": 40, "msg": "GEHEIM", "exc_info": sys.exc_info()}))
    e = plugin.lesen()[0]
    assert e["typ"] == "ValueError"
    assert "PASSWORT" not in plugin.pfad.read_text()
    assert "GEHEIM" not in plugin.pfad.read_text()


@pytest.fixture
def client(plugin):
    app = FastAPI()
    app.include_router(router)
    app.add_middleware(debug.DebugMiddleware)

    @app.get('/api/belege/{beleg_id}')
    def belege(beleg_id: str):
        return {"inhalt": "Vertraulich"}

    @app.get('/api/kaputt')
    def kaputt():
        raise RuntimeError("Vertraulich")

    return TestClient(app, raise_server_exceptions=False)


def test_middleware_erfasst_route_statt_query_und_id(client, plugin):
    aktivieren(plugin)
    assert client.get('/api/belege/geheimer-dateiname?token=GEHEIM').status_code == 200
    e = plugin.lesen()[0]
    assert e["route"] == '/api/belege/{beleg_id}'
    assert e["status"] == 200 and e["dauer_ms"] >= 0
    assert "GEHEIM" not in plugin.pfad.read_text()
    assert "geheimer-dateiname" not in plugin.pfad.read_text()
    assert "Vertraulich" not in plugin.pfad.read_text()


def test_middleware_erfasst_exceptions_und_http_fehler(client, plugin):
    aktivieren(plugin, ["fehler"])
    assert client.get('/api/kaputt').status_code == 500
    assert client.get('/api/nicht-da').status_code == 404
    assert [(e["status"], e["typ"]) for e in plugin.lesen()] == [(404, "HTTPFehler"), (500, "RuntimeError")]


def test_debug_api_keine_selbstprotokollierung_validierung_export(client, plugin):
    config = {"aktiviert": True, "kategorien": list(debug.KATEGORIEN)}
    assert client.put('/api/debug-plugin/einstellungen', json=config).status_code == 200
    assert client.get('/api/debug-plugin/einstellungen').json()["mitgeliefert"] is True
    assert client.get('/api/debug-plugin/protokoll').json() == []
    assert client.post('/api/debug-plugin/ereignisse', json={"ereignisse": [
        {"kategorie": "ui", "aktion": "klick", "seite": "/kunden", "element": "button"}]}).status_code == 204
    assert len(client.get('/api/debug-plugin/protokoll').json()) == 1
    assert client.post('/api/debug-plugin/ereignisse', json={"ereignisse": [
        {"kategorie": "ui", "aktion": "klick", "seite": "/kunden?token=geheim"}]}).status_code == 422
    assert client.put('/api/debug-plugin/einstellungen', json={"aktiviert": True, "kategorien": ["falsch"]}).status_code == 422
    assert client.get('/api/debug-plugin/protokoll?limit=9999').status_code == 422
    response = client.get('/api/debug-plugin/download')
    assert response.headers['content-disposition'].startswith('attachment;')
    assert json.loads(response.content)['kategorie'] == 'ui'
    assert len(plugin.lesen()) == 1


def test_api_export_mit_archiven(client, plugin):
    plugin.MAX_BYTES = 400
    aktivieren(plugin)
    for n in range(10):
        plugin.schreiben("api", status=n)
    daten = client.get('/api/debug-plugin/download').content.decode().splitlines()
    assert len(daten) == len(plugin.lesen(500))
    assert json.loads(daten[-1])["status"] == 9


def test_defekte_konfiguration_schaltet_aufzeichnung_ab(plugin, tmp_path):
    plugin.verzeichnis.mkdir()
    plugin.einstellungen_pfad.write_text('{defekt')
    assert not debug.DebugPlugin(tmp_path).einstellungen.aktiviert
    with pytest.raises(ValidationError):
        debug.DebugEinstellungen(kategorien=["payloads"])


def test_auch_erfolgreiche_hooks_und_host_api_werden_protokolliert(plugin, monkeypatch):
    from types import SimpleNamespace
    from plugins import laufzeit
    aktivieren(plugin, ["plugins"])
    p = SimpleNamespace(plugin_id="de.test", name="Test")
    monkeypatch.setattr(laufzeit, "_plugins_fuer", lambda hook: [p])
    monkeypatch.setattr(laufzeit, "_als_ausfuehrbar", lambda p: p)
    monkeypatch.setattr(laufzeit, "_component", lambda p: None)
    monkeypatch.setattr(laufzeit, "_erfolg", lambda p: None)
    monkeypatch.setattr(laufzeit, "_ist_abgeschaltet", lambda id: False)
    monkeypatch.setattr(laufzeit, "_rufe_auf", lambda *args: laufzeit.HookErgebnis("de.test", "test", "ok", dauer_ms=1.2))
    monkeypatch.setattr(laufzeit._hintergrund, "auftrag", lambda fn: fn())
    assert laufzeit.vor_aenderung("customer", "create", {"name": "Privat"}) == {"name": "Privat"}
    laufzeit.nach_aenderung("customer", "create", {"name": "Privat"})
    host = SimpleNamespace(get=lambda *args: '{"passwort": "GEHEIM"}')
    token = laufzeit._kontext.set((laufzeit._Kontext("de.test", {"customer": frozenset(["read"])}, host),))
    try:
        laufzeit._host_aufruf("get", "customer", "42")
        laufzeit._host_aufruf("get", "invoice", "42")  # nicht erlaubt
    finally:
        laufzeit._kontext.reset(token)
    e = plugin.lesen()
    assert [z["hook"] for z in reversed(e)] == ["customer:create:before", "customer:create:after", "host:customer:get", "host:invoice:get"]
    assert e[0]["ergebnis"] == "unauthorized"
    assert "Privat" not in plugin.pfad.read_text()
    assert "GEHEIM" not in plugin.pfad.read_text()
