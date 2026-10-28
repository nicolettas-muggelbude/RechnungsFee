"""
Plugin-System Phase 0-2 (docs/plan-plugin-system.md): Manifest, Wasm-Prüfung, Registry/Status,
Installation und Verwaltungs-API.

Die Test-Plugins in tests/fixtures/plugins/ werden mit quelle/build.sh gebaut:
- testplugin.wasm  gültige Component gegen plugins/wit/rechnungsfee.wit
- boese.wasm       importiert zusätzlich eine nicht erlaubte Schnittstelle (Netzwerk)
- modul.wasm       reines Wasm-Modul, keine Component
"""
import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import PluginProtokoll, PluginStatus
from plugins import registry
from plugins.manifest import (
    hook_klartext, parse_manifest, pruefe_manifest, rechte_erweitert, rechte_klartext,
)
from plugins.wasm_pruefung import pruefe_component_bytes

FIXTURES = Path(__file__).parent / "fixtures" / "plugins"
TESTPLUGIN = (FIXTURES / "testplugin.wasm").read_bytes()

MANIFEST_LASTENHEFT = """
[plugin]
id = "org.rechnungsfee.task-automation"
name = "Task Automation & Audit Logger"
version = "0.1.0"
author = "Stefan Lindecke"
description = "Erstellt automatisch Folge-Aufgaben bei Rechnungs-Events und sichert Logdaten."
api_version = "0.1.0"

[permissions]
entities = [
    { type = "invoice", actions = ["read"] },
    { type = "task", actions = ["create", "read", "update"] }
]
hooks = [
    "invoice:create:before",
    "invoice:create:after"
]
"""


def _mit_custom_section(wasm: bytes, inhalt: bytes) -> bytes:
    """Gültige Component mit anderem Hash (angehängte Custom-Section) - simuliert ein Update."""
    name = b"test"
    body = bytes([len(name)]) + name + inhalt
    assert len(body) < 128
    return wasm + bytes([0, len(body)]) + body


@pytest.fixture
def plugin_dir(tmp_path, monkeypatch):
    d = tmp_path / "plugins"
    d.mkdir()
    monkeypatch.setenv("RECHNUNGSFEE_PLUGIN_DIR", str(d))
    monkeypatch.delenv("RECHNUNGSFEE_PLUGINS", raising=False)
    return d


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def lege_plugin_an(basis: Path, ordner: str = "task-automation", manifest: str = MANIFEST_LASTENHEFT,
                   wasm: bytes | None = TESTPLUGIN) -> Path:
    p = basis / ordner
    p.mkdir(exist_ok=True)
    (p / "plugin.toml").write_text(manifest, encoding="utf-8")
    if wasm is not None:
        (p / "plugin.wasm").write_bytes(wasm)
    return p


def zustand(db, plugin_id="org.rechnungsfee.task-automation"):
    return registry.zustand(db, plugin_id)


def aktiviere(db, plugin_id="org.rechnungsfee.task-automation"):
    z = zustand(db, plugin_id)
    return registry.aktivieren(db, plugin_id, z.gefunden.wasm_sha256, z.gefunden.manifest.rechte_snapshot())


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def test_manifest_aus_lastenheft_ist_gueltig(tmp_path):
    (tmp_path / "plugin.toml").write_text(MANIFEST_LASTENHEFT, encoding="utf-8")
    e = parse_manifest(tmp_path / "plugin.toml")
    assert e.fehler == []
    m = e.manifest
    assert m.id == "org.rechnungsfee.task-automation"
    assert m.rechte == {"invoice": ("read",), "task": ("create", "read", "update")}
    assert m.hooks == ("invoice:create:after", "invoice:create:before")


def test_manifest_ohne_api_version_nur_warnung():
    roh = {"plugin": {"id": "de.example.x", "name": "X", "version": "1.0.0", "author": "A", "description": "D"}}
    e = pruefe_manifest(roh)
    assert e.manifest is not None and e.manifest.api_version == "0.1.0"
    assert any("api_version" in w for w in e.warnungen)


@pytest.mark.parametrize("aenderung, erwartet", [
    ({"id": "OhnePunkt"}, "Reverse-DNS"),
    ({"id": "../../etc"}, "Reverse-DNS"),
    ({"version": "eins"}, "SemVer"),
    ({"api_version": "9.0.0"}, "nicht unterstützt"),
])
def test_manifest_ungueltige_plugin_felder(aenderung, erwartet):
    plugin = {"id": "de.example.x", "name": "X", "version": "1.0.0", "author": "A", "description": "D",
              "api_version": "0.1.0", **aenderung}
    e = pruefe_manifest({"plugin": plugin})
    assert e.manifest is None
    assert any(erwartet in f for f in e.fehler), e.fehler


@pytest.mark.parametrize("permissions, erwartet", [
    ({"entities": [{"type": "konto", "actions": ["read"]}]}, "unbekannte Entität"),
    ({"entities": [{"type": "invoice", "actions": ["lesen"]}]}, "unbekannte Aktion"),
    ({"entities": [{"type": "invoice", "actions": []}]}, "nicht-leere Liste"),
    ({"hooks": ["invoice:create"]}, "Format"),
    ({"hooks": ["invoice:read:before"]}, "wird nicht unterstützt"),
    ({"hooks": ["invoice:create:during"]}, "before oder after"),
])
def test_manifest_ungueltige_berechtigungen(permissions, erwartet):
    plugin = {"id": "de.example.x", "name": "X", "version": "1.0.0", "author": "A", "description": "D", "api_version": "0.1.0"}
    e = pruefe_manifest({"plugin": plugin, "permissions": permissions})
    assert e.manifest is None
    assert any(erwartet in f for f in e.fehler), e.fehler


def test_manifest_kaputtes_toml(tmp_path):
    (tmp_path / "plugin.toml").write_text("[plugin\nid=", encoding="utf-8")
    e = parse_manifest(tmp_path / "plugin.toml")
    assert e.manifest is None and "kein gültiges TOML" in e.fehler[0]


def test_rechte_erweitert():
    alt = {"entities": {"invoice": ["read"]}, "hooks": ["invoice:create:after"]}
    assert not rechte_erweitert(alt, alt)
    assert not rechte_erweitert(alt, {"entities": {}, "hooks": []})                       # weniger
    assert rechte_erweitert(alt, {"entities": {"invoice": ["read", "update"]}, "hooks": []})  # neue Aktion
    assert rechte_erweitert(alt, {"entities": {"task": ["read"]}, "hooks": []})           # neue Entität
    assert rechte_erweitert(alt, {"entities": {}, "hooks": ["invoice:create:before"]})   # neuer Hook
    assert rechte_erweitert(None, {"entities": {}, "hooks": []})


def test_klartext():
    assert rechte_klartext({"task": ("create", "read", "update"), "invoice": ("read",)}) == [
        "Darf Rechnungen lesen",
        "Darf Aufgaben lesen, anlegen und ändern",
    ]
    assert hook_klartext("invoice:create:before") == "Prüft oder verändert neue Rechnungen vor dem Speichern"
    assert hook_klartext("customer:update:after") == "Reagiert, nachdem ein Kunde geändert wurde"
    assert hook_klartext("task:delete:before") == "Kann das Löschen von Aufgaben verhindern"


# ---------------------------------------------------------------------------
# Wasm-Prüfung (Phase 0)
# ---------------------------------------------------------------------------

def test_wasm_gueltige_component():
    assert pruefe_component_bytes(TESTPLUGIN) == []


def test_wasm_nicht_erlaubter_import_wird_abgelehnt():
    fehler = pruefe_component_bytes((FIXTURES / "boese.wasm").read_bytes())
    assert len(fehler) == 1 and "rechnungsfee:plugin/netz@0.1.0" in fehler[0]


def test_wasm_modul_statt_component():
    fehler = pruefe_component_bytes((FIXTURES / "modul.wasm").read_bytes())
    assert "keine WebAssembly-Component" in fehler[0]


def test_wasm_keine_wasm_datei():
    assert pruefe_component_bytes(b"PK\x03\x04 kein wasm") == ["plugin.wasm ist keine WebAssembly-Datei"]


# ---------------------------------------------------------------------------
# Registry & Status
# ---------------------------------------------------------------------------

def test_leerer_oder_fehlender_ordner(plugin_dir, db):
    assert registry.alle_zustaende(db) == []
    plugin_dir.rmdir()
    assert registry.alle_zustaende(db) == []


def test_neu_gefundenes_plugin_laeuft_nicht(plugin_dir, db):
    lege_plugin_an(plugin_dir)
    registry.global_setzen(db, True)
    z = zustand(db)
    assert z.status == registry.NEU
    assert z.laeuft is False
    assert registry.ausfuehrbare_plugins(db) == []


@pytest.mark.parametrize("wasm, erwartet", [
    (None, "plugin.wasm fehlt"),
    ((FIXTURES / "boese.wasm").read_bytes(), "nicht bereitstellt"),
    ((FIXTURES / "modul.wasm").read_bytes(), "keine WebAssembly-Component"),
])
def test_fehlerhafte_plugins_werden_mit_grund_angezeigt(plugin_dir, db, wasm, erwartet):
    lege_plugin_an(plugin_dir, wasm=wasm)
    z = zustand(db)
    assert z.status == registry.FEHLERHAFT
    assert any(erwartet in f for f in z.gefunden.fehler), z.gefunden.fehler
    with pytest.raises(registry.PluginFehler) as e:
        registry.aktivieren(db, z.plugin_id, z.gefunden.wasm_sha256 or "", {"entities": {}, "hooks": []})
    assert e.value.status_code == 422


def test_ungueltiges_manifest_erscheint_unter_ordnername(plugin_dir, db):
    lege_plugin_an(plugin_dir, ordner="kaputt", manifest="[plugin]\nname = 'X'\n")
    zustaende = registry.alle_zustaende(db)
    assert [(z.plugin_id, z.status) for z in zustaende] == [("kaputt", registry.FEHLERHAFT)]


def test_aktivieren_und_hauptschalter(plugin_dir, db, monkeypatch):
    lege_plugin_an(plugin_dir)
    z = aktiviere(db)
    assert z.status == registry.AKTIV
    assert z.laeuft is False                        # Hauptschalter standardmäßig aus

    registry.global_setzen(db, True)
    assert zustand(db).laeuft is True
    assert len(registry.ausfuehrbare_plugins(db)) == 1

    monkeypatch.setenv("RECHNUNGSFEE_PLUGINS", "0")  # abgesicherter Modus
    assert zustand(db).laeuft is False
    assert zustand(db).status == registry.AKTIV      # Status bleibt, läuft nur nicht

    zeile = db.get(PluginStatus, "org.rechnungsfee.task-automation")
    assert json.loads(zeile.genehmigte_rechte_json)["entities"]["task"] == ["create", "read", "update"]
    assert db.query(PluginProtokoll).filter_by(ergebnis="aktiviert").count() == 1


def test_aktivieren_lehnt_veralteten_stand_ab(plugin_dir, db):
    """Die Datei wurde ausgetauscht, nachdem die Seite geladen wurde -> nicht das Falsche freigeben."""
    lege_plugin_an(plugin_dir)
    z = zustand(db)
    alter_hash = z.gefunden.wasm_sha256
    rechte = z.gefunden.manifest.rechte_snapshot()
    (plugin_dir / "task-automation" / "plugin.wasm").write_bytes(_mit_custom_section(TESTPLUGIN, b"2"))
    with pytest.raises(registry.PluginFehler) as e:
        registry.aktivieren(db, z.plugin_id, alter_hash, rechte)
    assert e.value.status_code == 409

    weniger = {"entities": {"invoice": ["read"]}, "hooks": []}
    with pytest.raises(registry.PluginFehler):
        registry.aktivieren(db, z.plugin_id, zustand(db).gefunden.wasm_sha256, weniger)


def test_update_ohne_neue_rechte_laeuft_weiter(plugin_dir, db):
    lege_plugin_an(plugin_dir)
    aktiviere(db)
    registry.global_setzen(db, True)
    (plugin_dir / "task-automation" / "plugin.wasm").write_bytes(_mit_custom_section(TESTPLUGIN, b"2"))
    z = zustand(db)
    assert z.status == registry.AKTUALISIERT
    assert z.laeuft is True
    assert aktiviere(db).status == registry.AKTIV   # Update bestätigen


def test_update_mit_neuen_rechten_haelt_an(plugin_dir, db):
    lege_plugin_an(plugin_dir)
    aktiviere(db)
    registry.global_setzen(db, True)
    mehr = MANIFEST_LASTENHEFT.replace('{ type = "invoice", actions = ["read"] }',
                                       '{ type = "invoice", actions = ["read", "update"] }')
    lege_plugin_an(plugin_dir, manifest=mehr)
    z = zustand(db)
    assert z.status == registry.RECHTE_ERWEITERT
    assert z.laeuft is False
    assert aktiviere(db).status == registry.AKTIV


def test_update_mit_weniger_rechten_bleibt_aktiv(plugin_dir, db):
    lege_plugin_an(plugin_dir)
    aktiviere(db)
    weniger = MANIFEST_LASTENHEFT.replace('    "invoice:create:before",\n', "")
    lege_plugin_an(plugin_dir, manifest=weniger)
    assert zustand(db).status == registry.AKTIV


def test_deaktivieren_und_hooks(plugin_dir, db):
    lege_plugin_an(plugin_dir)
    aktiviere(db)
    registry.global_setzen(db, True)

    z = registry.hooks_setzen(db, "org.rechnungsfee.task-automation", ["invoice:create:before"])
    assert registry.deaktivierte_hooks(z.status_zeile) == ["invoice:create:before"]
    assert z.laeuft is True                          # Plugin läuft weiter, nur der Hook ist aus

    with pytest.raises(registry.PluginFehler) as e:
        registry.hooks_setzen(db, "org.rechnungsfee.task-automation", ["customer:delete:before"])
    assert e.value.status_code == 422

    z = registry.deaktivieren(db, "org.rechnungsfee.task-automation")
    assert z.status == registry.DEAKTIVIERT and z.laeuft is False


def test_neues_plugin_deaktivieren_ist_nicht_mehr_neu(plugin_dir, db):
    lege_plugin_an(plugin_dir)
    assert registry.deaktivieren(db, "org.rechnungsfee.task-automation").status == registry.DEAKTIVIERT


def test_automatisch_deaktiviert_und_wieder_einschalten(plugin_dir, db):
    lege_plugin_an(plugin_dir)
    aktiviere(db)
    zeile = db.get(PluginStatus, "org.rechnungsfee.task-automation")
    zeile.automatisch_deaktiviert = True
    zeile.fehler_in_folge = 3
    db.commit()
    assert zustand(db).status == registry.AUTOMATISCH_DEAKTIVIERT
    z = aktiviere(db)
    assert z.status == registry.AKTIV and z.status_zeile.fehler_in_folge == 0


def test_doppelte_plugin_id(plugin_dir, db):
    lege_plugin_an(plugin_dir, ordner="a-original")
    lege_plugin_an(plugin_dir, ordner="b-kopie")
    zustaende = {z.plugin_id: z for z in registry.alle_zustaende(db)}
    assert zustaende["org.rechnungsfee.task-automation"].status == registry.NEU
    kopie = zustaende["org.rechnungsfee.task-automation#b-kopie"]
    assert kopie.status == registry.FEHLERHAFT
    assert "a-original" in kopie.gefunden.fehler[0]


def test_geloeschte_dateien_erscheinen_als_fehlt(plugin_dir, db):
    ordner = lege_plugin_an(plugin_dir)
    aktiviere(db)
    for f in ordner.iterdir():
        f.unlink()
    ordner.rmdir()
    z = zustand(db)
    assert z.status == registry.FEHLT and z.laeuft is False


def test_interne_punktordner_werden_ignoriert(plugin_dir, db):
    lege_plugin_an(plugin_dir, ordner=".install-abc")
    assert registry.alle_zustaende(db) == []


# ---------------------------------------------------------------------------
# Installation / Entfernen
# ---------------------------------------------------------------------------

def _zip(dateien: dict[str, bytes]) -> bytes:
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w") as zf:
        for name, inhalt in dateien.items():
            zf.writestr(name, inhalt)
    return puffer.getvalue()


def test_installieren_mit_oberordner(plugin_dir, db):
    paket = _zip({
        "mein-plugin/plugin.toml": MANIFEST_LASTENHEFT.encode(),
        "mein-plugin/plugin.wasm": TESTPLUGIN,
        "mein-plugin/README.md": b"# Hallo",
    })
    g = registry.installiere_paket(paket)
    assert g.verzeichnis == plugin_dir / "org.rechnungsfee.task-automation"
    assert sorted(p.name for p in g.verzeichnis.iterdir()) == ["README.md", "plugin.toml", "plugin.wasm"]
    assert zustand(db).status == registry.NEU
    assert [p.name for p in plugin_dir.iterdir()] == ["org.rechnungsfee.task-automation"]  # keine Reste


def test_installieren_als_update(plugin_dir, db):
    registry.installiere_paket(_zip({"plugin.toml": MANIFEST_LASTENHEFT.encode(), "plugin.wasm": TESTPLUGIN}))
    aktiviere(db)
    registry.installiere_paket(_zip({
        "plugin.toml": MANIFEST_LASTENHEFT.encode(), "plugin.wasm": _mit_custom_section(TESTPLUGIN, b"2"),
    }))
    assert zustand(db).status == registry.AKTUALISIERT


@pytest.mark.parametrize("dateien, erwartet", [
    ({"plugin.toml": b"x"}, "muss plugin.toml und plugin.wasm enthalten"),
    ({"../plugin.toml": b"x", "plugin.wasm": b"x"}, "ungültige Pfade"),
    ({"plugin.toml": b"x", "plugin.wasm": b"x", "lib/so.so": b"x"}, "Unterordner"),
    ({"plugin.toml": b"x", "plugin.wasm": b"x", "start.sh": b"x"}, "Unerwartete Datei"),
    ({"plugin.toml": b"[plugin]\nid='x'", "plugin.wasm": TESTPLUGIN}, "Manifest des Plugins ist ungültig"),
])
def test_installieren_lehnt_ungueltige_pakete_ab(plugin_dir, dateien, erwartet):
    with pytest.raises(registry.PluginFehler) as e:
        registry.installiere_paket(_zip(dateien))
    text = e.value.meldung + " " + " ".join(e.value.details)
    assert erwartet in text, text
    assert list(plugin_dir.iterdir()) == []


def test_installieren_lehnt_inkompatible_wasm_ab(plugin_dir):
    with pytest.raises(registry.PluginFehler) as e:
        registry.installiere_paket(_zip({
            "plugin.toml": MANIFEST_LASTENHEFT.encode(), "plugin.wasm": (FIXTURES / "boese.wasm").read_bytes(),
        }))
    assert e.value.status_code == 422 and "netz" in e.value.details[0]


def test_installieren_einzelne_wasm_erklaert_paketauswahl(plugin_dir):
    with pytest.raises(registry.PluginFehler) as e:
        registry.installiere_paket(TESTPLUGIN)
    assert e.value.status_code == 422
    assert "einzelne Wasm-Datei" in e.value.meldung
    assert "python-kundenpruefung.rfplugin" in e.value.meldung
    assert not list(plugin_dir.iterdir())


def test_installieren_kein_zip(plugin_dir):
    with pytest.raises(registry.PluginFehler) as e:
        registry.installiere_paket(b"kein zip")
    assert e.value.status_code == 422


def test_entfernen(plugin_dir, db):
    lege_plugin_an(plugin_dir)
    aktiviere(db)
    registry.entfernen(db, "org.rechnungsfee.task-automation")
    assert list(plugin_dir.iterdir()) == []
    assert db.get(PluginStatus, "org.rechnungsfee.task-automation") is None
    # Protokoll bleibt erhalten (Nachvollziehbarkeit)
    ergebnisse = [p.ergebnis for p in db.query(PluginProtokoll).order_by(PluginProtokoll.id)]
    assert ergebnisse == ["aktiviert", "entfernt"]
    # Neuinstallation gilt wieder als neu
    lege_plugin_an(plugin_dir)
    assert zustand(db).status == registry.NEU


# ---------------------------------------------------------------------------
# API (Endpunktfunktionen direkt, Stil wie test_profile_api.py)
# ---------------------------------------------------------------------------

def test_api_liste_und_aktivieren(plugin_dir, db):
    from api import plugins as api

    lege_plugin_an(plugin_dir)
    uebersicht = api.liste(db)
    assert uebersicht.plugins_aktiv is False and uebersicht.abgesicherter_modus is False
    assert uebersicht.verzeichnis == str(plugin_dir)
    p = uebersicht.plugins[0]
    assert p.status == "neu" and p.laeuft is False
    assert p.rechte_klartext == ["Darf Rechnungen lesen", "Darf Aufgaben lesen, anlegen und ändern"]
    assert [h.vor_dem_speichern for h in p.hooks] == [False, True]

    with pytest.raises(HTTPException) as e:
        api.aktivieren(p.plugin_id, api.AktivierenRequest(wasm_sha256="0" * 64, rechte=p.rechte), db)
    assert e.value.status_code == 409

    eintrag = api.aktivieren(p.plugin_id, api.AktivierenRequest(wasm_sha256=p.wasm_sha256, rechte=p.rechte), db)
    assert eintrag.status == "aktiv" and eintrag.laeuft is False

    assert api.global_setzen(api.GlobalRequest(plugins_aktiv=True), db).plugins[0].laeuft is True

    protokoll = api.protokoll(p.plugin_id, limit=10, offset=0, db=db)
    assert [e.ergebnis for e in protokoll] == ["aktiviert"]


def test_api_rechte_erweitert_zeigt_differenz(plugin_dir, db):
    from api import plugins as api

    lege_plugin_an(plugin_dir)
    aktiviere(db)
    mehr = MANIFEST_LASTENHEFT.replace('{ type = "invoice", actions = ["read"] }',
                                       '{ type = "invoice", actions = ["read", "update"] }, { type = "customer", actions = ["read"] }')
    mehr = mehr.replace('"invoice:create:after"', '"invoice:create:after", "invoice:delete:before"')
    lege_plugin_an(plugin_dir, manifest=mehr)
    p = api.liste(db).plugins[0]
    assert p.status == "rechte_erweitert"
    assert p.neue_rechte_klartext == ["Darf Kunden lesen", "Darf Rechnungen ändern"]
    assert p.neue_hooks_klartext == ["Kann das Löschen von Rechnungen verhindern"]


def test_api_unbekanntes_plugin(plugin_dir, db):
    from api import plugins as api

    with pytest.raises(HTTPException) as e:
        api.deaktivieren("de.gibt.es-nicht", db)
    assert e.value.status_code == 404
