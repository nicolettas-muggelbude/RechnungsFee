# Python-Plugin: Kunden prüfen

Ein vollständiges Beispiel für RechnungsFees Plugin-API `0.1.0`: Python-Quelltext
wird mit `componentize-py` in eine **WebAssembly-Component** übersetzt. Die App lädt
kein natives `.py`-Modul. Sie führt das Ergebnis in derselben Sandbox wie andere
Wasm-Plugins aus.

## Was das Beispiel macht

Vor dem Anlegen oder Ändern eines Kunden:

- Fehlen Firmenname und Vor-/Nachname, wird das Speichern mit einer Meldung abgebrochen.
- Leerzeichen am Anfang und Ende der E-Mail-Adresse werden entfernt.
- Alle anderen Felder bleiben erhalten.

Der Post-Hook ist implementiert, tut aber nichts und wird im Manifest nicht abonniert.
Das Plugin braucht keine Host-Leserechte, weil es den Kunden bereits als Hook-Payload
bekommt. Es schreibt keine eigenen Logs; dafür kannst du das mitgelieferte
[Debug-Plugin](../../../docs/debug-plugin.md) einschalten und „Plugin-Aufrufe“ wählen.

## Voraussetzungen

- Python 3.12 für die Buildumgebung (hier geprüft).
- `componentize-py==0.25.0`, separat in `requirements-build.txt` festgehalten.
- Zum Sandbox-Test: installierte Backend-Abhängigkeiten einschließlich wasmtime.
- GNU Make und Bash für die Make-Befehle; die Python-Buildskripte können auch direkt
  aufgerufen werden.

Ein Rust-/C-Compiler ist zum Bauen dieses Beispiels nicht nötig. Die separate
Buildumgebung vermeidet zusätzliche Build-Abhängigkeiten im ausgelieferten Backend.

## Bauen und testen

Im Repository-Hauptverzeichnis:

```bash
make plugins-python-setup             # einmalig; ggf. PYTHON=/pfad/zu/python3.12
make plugins-python-build
make plugins-python-test             # baut erneut, testet Fachlogik und echte Wasm-Sandbox
```

Oder ohne Make:

```bash
cd examples/plugins/python-kundenpruefung
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python build.py
.venv/bin/python -m unittest discover -p test_pruefung.py -v
../../../src/backend/.venv/bin/python smoke_test.py
```

Unter Windows die Python-Datei unter `.venv\Scripts\python.exe` verwenden. Das
Buildskript findet `componentize-py.exe` neben dieser Python-Datei automatisch.
Bei einer anderen Tool-Umgebung ist `build.py --componentize /pfad/zu/componentize-py`
möglich.

Ergebnis:

```text
dist/
├── plugin.wasm
└── python-kundenpruefung.rfplugin
```

Das `.rfplugin` ist ein ZIP mit `plugin.toml` und `plugin.wasm` direkt im Wurzelverzeichnis.
Build-Ausgaben, generierte Bindings und die Build-venv werden nicht versioniert.

## In RechnungsFee ausprobieren

1. Öffne **Einstellungen → Plugins → Plugin installieren…**.
2. Wähle `dist/python-kundenpruefung.rfplugin`.
3. Schalte „Plugins verwenden“ ein und aktiviere „Python-Beispiel: Kundenprüfung“.
4. In den Plugin-Details kannst du einen Testlauf mit folgendem Payload starten:

   ```json
   {
     "_schema": "customer@1",
     "firmenname": "Beispiel GmbH",
     "email": " kontakt@example.org "
   }
   ```

   Ergebnis: geändert, E-Mail ohne Rand-Leerzeichen. Mit leerem Firmennamen und
   ohne Vor-/Nachname wird der Testlauf abgebrochen.
5. Prüfe das Verhalten anschließend beim Anlegen/Ändern eines Kunden in einem Testprofil.
   Der Testlauf selbst speichert keine Kundendaten.

## Fehler beim Installieren

Wähle **`dist/python-kundenpruefung.rfplugin`**, nicht `dist/plugin.wasm`.
Das Wasm enthält den ausführbaren Code; das Paket enthält zusätzlich das Manifest
mit Plugin-ID, API-Version und Rechten. Umbenennen von `.wasm` nach `.rfplugin`
erzeugt kein gültiges Paket.

Die Meldung „Die Datei ist kein gültiges Plugin-Paket (.rfplugin/.zip)“ bedeutet,
dass der Upload nicht als ZIP gelesen werden konnte. Falls du bereits das richtige
Paket gewählt hast, prüfe es im Repository-Hauptverzeichnis:

```bash
python3 -m zipfile -t examples/plugins/python-kundenpruefung/dist/python-kundenpruefung.rfplugin
```

Bei einem defekten Paket erneut `make plugins-python-build` ausführen und den
Build vollständig abwarten, bevor du es auswählst.

## Aufbau und Erweiterung

| Datei | Zweck |
| --- | --- |
| `pruefung.py` | Fachlogik ohne Toolchain-Abhängigkeiten |
| `app.py` | WIT-Adapter: `EventHandler`, Ergebnis zurückgeben bzw. `Err(...)` werfen |
| `plugin.toml` | ID, Version, API-Version und abonnierte Hooks |
| `build.py` | Wasm bauen und ZIP-Paket erzeugen |
| `test_pruefung.py` | Lokale Unit-Tests |
| `smoke_test.py` | Aufrufe in der echten RechnungsFee-Laufzeit mit deren normalen Limits |

Die Bindings entstehen beim Build aus der zentralen
[WIT-Datei](../../../src/backend/plugins/wit/rechnungsfee.wit). Für IDE-Unterstützung
kannst du sie optional im Beispielordner erzeugen:

```bash
.venv/bin/componentize-py \
  -d ../../../src/backend/plugins/wit/rechnungsfee.wit \
  -w plugin-world bindings .
```

`app.EventHandler` implementiert das generierte Protokoll `wit_world.exports.EventHandler`.
`on_before_change(ctx, payload_json)` erhält den Ereigniskontext und das DTO als JSON-Text.
Die Rückgabe ist der vollständige DTO-JSON-Text. `raise componentize_py_types.Err(meldung)`
entspricht dem WIT-Fehlerresultat und bricht die Transaktion ab. Eine gewöhnliche,
unbehandelte Python-Exception gilt dagegen als Plugin-Fehler.

Die tatsächlich verfügbaren Felder und Änderungsrechte stehen in
[`plugins/dto.py`](../../../src/backend/plugins/dto.py). `customer@1` ist die DTO-Version;
`api_version = "0.1.0"` bezeichnet die davon getrennte WIT-API-Version.
Nicht erlaubte Feldänderungen werden vom Host verworfen und protokolliert.

## Grenzen

- `--stub-wasi` ist zwingend: Die erzeugte Python-Runtime darf keine WASI-Imports
  verlangen. Datei-, Netzwerk-, Zeit- und andere WASI-Zugriffe stehen nicht zur Verfügung.
- Keine Dateizugriffe, `print()`-Ausgaben oder Laufzeitimporte voraussetzen.
  Alle benötigten Module am Modulanfang importieren; hier wird `json` beim Build eingebunden.
- Python-Runtime und Standardbibliothek sind im Wasm enthalten. Das Beispiel erzeugt
  hier etwa **18,4 MB** Wasm und liegt damit unter dem **20-MB-Limit**. Zusätzliche
  Bibliotheken können dieses Limit oder das Speicherlimit überschreiten.
- Das Beispiel wurde mit **64 MB Speicherlimit** und dem unveränderten
  **50-ms-Pre-Hook-Budget** getestet. Dieses Budget teilen sich alle Pre-Hooks einer
  Transaktion; auf anderen Rechnern und mit mehreren Plugins erneut testen.
- Host-API-Schreibzugriffe für Kunden, Artikel und Rechnungsentwürfe sind mit bestätigten
  Rechten verfügbar: siehe [Host-API-Anleitung](../../../docs/plugin-host-api.md). Dieses
  Prüfplugin benötigt sie nicht. Aufgaben (`task`) sind weiterhin nicht implementiert.
- Es gibt keine persistenten Python-Globals zwischen Aufrufen: jeder Hook erhält eine
  neue Wasm-Instanz.

Tool-Dokumentation: [Bytecode Alliance – componentize-py](https://github.com/bytecodealliance/componentize-py/tree/v0.25.0).
