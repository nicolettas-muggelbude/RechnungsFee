"""Gebautes Python-Plugin mit RechnungsFees echter Sandbox prüfen, ohne Nutzerdaten."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

BEISPIEL = Path(__file__).resolve().parent
REPO = BEISPIEL.parents[2]
sys.path.insert(0, str(REPO / 'src/backend'))


def main():
    from plugins import debug_plugin, laufzeit, registry, wasm_pruefung
    from plugins.host_api import KeinDatenzugriff
    from plugins.manifest import parse_manifest
    paket = BEISPIEL / 'dist/python-kundenpruefung.rfplugin'
    if not paket.exists():
        raise SystemExit('Bitte zuerst make plugins-python-build ausführen.')
    with zipfile.ZipFile(paket) as archiv:
        assert set(archiv.namelist()) == {'plugin.wasm', 'plugin.toml'}
    wasm = BEISPIEL / 'dist/plugin.wasm'
    manifest = parse_manifest(BEISPIEL / 'plugin.toml')
    assert not manifest.fehler, manifest.fehler
    assert not wasm_pruefung.pruefe_component_bytes(wasm.read_bytes()), 'Component inkompatibel'
    assert wasm.stat().st_size <= registry.MAX_WASM_BYTES
    plugin = laufzeit._Ausfuehrbar(
        manifest.manifest.id, manifest.manifest.name, wasm,
        hashlib.sha256(wasm.read_bytes()).hexdigest(), {})
    laufzeit._component(plugin)  # Kompilierung wie in vor_aenderung außerhalb des Hook-Budgets.
    with tempfile.TemporaryDirectory(prefix='rf-python-plugin-') as verzeichnis:
        debug_plugin._instanz = debug_plugin.DebugPlugin(Path(verzeichnis))
        gueltig = {'_schema': 'customer@1', 'firmenname': 'Beispiel', 'email': ' hallo@example.org '}
        for _ in range(10):
            antwort = laufzeit._rufe_auf(plugin, 'before', 'customer', 'create', json.dumps(gueltig),
                                        laufzeit.PRE_HOOK_BUDGET_MS, KeinDatenzugriff())
            assert antwort.ergebnis == 'geaendert', antwort
            assert json.loads(antwort.payload_json)['email'] == 'hallo@example.org'
        antwort = laufzeit._rufe_auf(plugin, 'before', 'customer', 'update',
                                    '{"_schema":"customer@1","firmenname":""}',
                                    laufzeit.PRE_HOOK_BUDGET_MS, KeinDatenzugriff())
        assert antwort.ergebnis == 'abgebrochen', antwort
        assert 'Firmennamen' in antwort.meldung
        antwort = laufzeit._rufe_auf(plugin, 'after', 'customer', 'create', json.dumps(gueltig),
                                    laufzeit.POST_HOOK_DEADLINE_MS, KeinDatenzugriff())
        assert antwort.ergebnis == 'ok', antwort
        debug_plugin._instanz.schliessen()
    print('Wasm-Sandbox: Änderung, Abbruch und Post-Hook erfolgreich (64 MB / 50 ms für Pre-Hooks).')


if __name__ == '__main__':
    main()
