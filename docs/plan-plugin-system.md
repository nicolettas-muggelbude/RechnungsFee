# Ablaufplan: Integration des Wasm-Plugin-Systems

**Grundlage:** [`plugin-system.md`](plugin-system.md) (Lastenheft v1.0.0)
**Status:** Phase 0–5 einschließlich Host-API-Schreibzugriffen umgesetzt, 2026-10-28. Offen: Aufgaben und Rust-SDK (Phase 6), Release (Phase 7)
**Stand:** 2026-10-28

---

## 0. Wichtigster Befund vorab: Lastenheft vs. tatsächliche Architektur

Das Lastenheft geht von einem **Rust-Core mit Data Access Layer** aus, in dem `wasmtime` als Host läuft
und Pre-Hooks synchron *innerhalb der DB-Transaktion* ausgeführt werden.

In RechnungsFee sieht es anders aus:

| Lastenheft | RechnungsFee heute |
|---|---|
| Rust-Core mit DAL | Rust (`src-tauri`) ist nur die Desktop-Hülle: Fenster, Updater, Start des Sidecars. Keine DB-Zugriffe. |
| DB-Transaktionen im Rust-Core | Alle Transaktionen laufen im **Python-Sidecar** (FastAPI + SQLAlchemy 2.0 + SQLite/WAL), `SessionLocal`/`get_db()` in `database/connection.py` |
| Event-Dispatcher | Existiert nicht. Schreibzugriffe sind über viele Endpunkte verteilt (`db.commit()` direkt in `api/*.py`). |
| Entität `task` | Existiert nicht (es gibt `fristen.py`, das berechnet aber nur Steuerfristen, keine Aufgaben-Tabelle). |
| – | Im Browser-Dev-Modus (`npm run dev` + Backend auf 8002) läuft gar kein Rust-Prozess. |

**Konsequenz:** Ein Rust-Host könnte Pre-Hooks nur über einen synchronen IPC-Roundtrip Python → Rust → Wasm → Rust → Python
mitten in einer offenen SQLAlchemy-Transaktion ausführen. Das ist fehleranfällig, macht das 50-ms-Budget schwer
haltbar und funktioniert im Browser-Dev-Modus nicht.

### Empfehlung: Wasm-Host im Python-Backend

| Option | Pro | Contra |
|---|---|---|
| **A – Host im Python-Sidecar (`wasmtime`-PyPI-Paket)** ✅ | Pre-Hooks laufen direkt in der SQLAlchemy-Session, Rollback ist trivial; Host-API nutzt vorhandene Modelle/Pydantic-Schemas; läuft auch im Dev-Modus; ein Prozess weniger an der Kette | Component-Model-Support in wasmtime-py läuft bisher über Code-Generierung (`python -m wasmtime.bindgen`) – muss per Spike verifiziert werden; PyInstaller muss die native Lib mitnehmen |
| B – Host in Rust/Tauri, Python ruft per lokalem IPC | Entspricht dem Lastenheft wörtlich; volle wasmtime-Rust-API | Transaktion über Prozessgrenze; Rust braucht eigene Entitäts-DTOs; im Browser-Dev-Modus nicht verfügbar; doppelte Rechteprüfung |
| C – Eigener Rust-Host-Prozess als zweiter Sidecar | Isolation | Alle Nachteile von B plus ein dritter Prozess |

**→ Weiter mit Option A.** Das Lastenheft wird dazu in Abschnitt 2 (Architektur) angepasst; WIT-Schnittstelle,
Manifest und Hook-Semantik bleiben unverändert, sodass Plugins von der Host-Wahl nichts merken.
Falls der Spike in Phase 0 zeigt, dass wasmtime-py das Component Model nicht tragfähig unterstützt, ist der Fallback
Option B – die Phasen 1, 2, 4 und 5 bleiben dann gleich, nur Phase 3 wandert nach Rust.

---

## Umsetzungsstand Phase 0–2 (2026-10-28)

### Phase 0 – Spike: Ergebnis **Go für Option A** (Host im Python-Backend)

Gemessen mit `wasmtime` 50.0.1 (PyPI), Linux x86_64, Test-Plugin 7,5 KB, Payload 5,9 KB JSON.
Skript: `src/backend/tests/fixtures/plugins/quelle/spike_runtime.py`.

| Messpunkt | Ergebnis |
|---|---|
| Component kompilieren | 13 ms (einmalig pro Plugin-Version, danach Cache) |
| Kompiliertes Artefakt deserialisieren | 0,4 ms (Option für Plattencache) |
| Instanziieren | 0,07 ms |
| Pre-Hook, warme Instanz | Median 0,39 ms, p99 0,61 ms |
| Pre-Hook inkl. frischer Instanz je Aufruf | Median 0,64 ms → **frische Instanz pro Aufruf ist bezahlbar** (volle Isolation zwischen Aufrufen) |
| Host-API-Rundreise (Plugin → Python → Plugin) | 0,58 ms |
| `err(reason)` aus Pre-Hook | kommt als `Variant("err", reason)` an ✔ |
| Endlosschleife, Deadline 50 ms (Epoch-Ticker 1 ms) | abgebrochen nach 56 ms, Fehlertext enthält `wasm trap: interrupt` → von anderen Traps unterscheidbar ✔ |
| Trap im Plugin | `WasmtimeError`, Prozess läuft weiter, neue Instanz sofort nutzbar ✔ |
| Speicherlimit (`store.set_limits`, 16 MB) | greift ✔ |
| 4 Threads parallel mit eigenen Stores | ✔ (Post-Hook-Worker neben Request-Threads möglich) |

Das 50-ms-Budget aus NFA-3 ist damit um zwei Größenordnungen unterschritten.

**Wichtigste Erkenntnisse**

1. **wasmtime-py ≥ 50 hat eine native Component-API** (`wasmtime.component.Linker/Component`), Code-Generierung
   über `wasmtime.bindgen` ist nicht nötig. Host-Funktionen: `linker.root().add_instance("rechnungsfee:plugin/host-api@0.1.0").add_func(...)`.
   Werte-Mapping: Records als `Record`-Objekte (Feldnamen mit Bindestrich via `setattr`), Enums als `str`,
   `result<string,string>` als `Variant("ok"|"err", …)`, `result<string, api-error>` untagged (`str` bzw. `Variant`).
2. **Die WIT aus dem Lastenheft war nicht übersetzbar:** `list` ist ein WIT-Schlüsselwort → `%list: func(...)`
   (der Funktionsname bleibt `list`); `result<(), api-error>` → `result<_, api-error>`. Korrigierte Fassung:
   `src/backend/plugins/wit/rechnungsfee.wit`.
3. **PyInstaller:** `--collect-all wasmtime` nimmt die native `_libwasmtime.so/.dll/.dylib` **nicht** mit – der
   gefrorene Sidecar bricht dann beim ersten Plugin-Zugriff ab („Failed to load dynlib“). Gelöst über
   `--add-binary` auf den Plattform-Unterordner (`scripts/build-sidecar.sh` + `.ps1`). Kompletter Sidecar-Build
   unter Linux geprüft: startet, prüft und installiert Plugins. Der Sidecar wird ca. 9 MB größer.
   **Noch offen:** Build + Start auf Windows und macOS (arm64/x86_64) im CI-Lauf prüfen.
4. Die Test-Plugins werden in C gebaut (clang wasm32 + `wit-bindgen c` + `wasm-tools component new`), weil das
   Rust-Wasm-Target in der Spike-Umgebung nicht verfügbar war. Echte Plugins: Rust mit `cargo component`.

### Phase 1 – umgesetzt

| Datei | Inhalt |
|---|---|
| `src/backend/plugins/manifest.py` | `plugin.toml` lesen/prüfen, Rechte-Snapshot, `rechte_erweitert()`, Klartexte für die UI |
| `src/backend/plugins/wasm_pruefung.py` | Statische Component-Prüfung ohne Ausführung: Export `event-handler` mit beiden Funktionen, **nur** `host-api`/`types` als Importe (kein WASI) |
| `src/backend/plugins/registry.py` | Ordner-Scan, Statuslogik, Aktivieren/Deaktivieren/Hooks, `.rfplugin`-Installation, Entfernen, `ausfuehrbare_plugins()` als Einstieg für Phase 3 |
| `src/backend/plugins/wit/rechnungsfee.wit` | korrigierte WIT-Schnittstelle |
| `database/models.py` + Migration **175** | `plugin_einstellungen` (Hauptschalter, Singleton – bewusst nicht in `unternehmen`), `plugin_status`, `plugin_protokoll` |

Abweichungen/Ergänzungen zum Plan:
- Hauptschalter **pro Profil** in eigener Tabelle (offene Frage 6 damit vorläufig entschieden).
- Plugin-Ordner per `RECHNUNGSFEE_PLUGIN_DIR` überschreibbar (Tests, Entwicklung).
- Abgesicherter Modus: `RECHNUNGSFEE_PLUGINS=0`.
- Doppelte Plugin-IDs: das erste Vorkommen (alphabetisch nach Ordner) gewinnt, weitere sind „fehlerhaft“.
- Aktivieren bestätigt genau den angezeigten Stand (Hash + Rechte); weicht die Datei inzwischen ab → 409.

### Phase 2 – umgesetzt

- `src/backend/api/plugins.py` – Endpunkte wie geplant, plus `POST /api/plugins/ordner-oeffnen`
  (System-Dateimanager; das Shell-Plugin von Tauri erlaubt nur URLs).
- `src/frontend/src/pages/einstellungen/PluginsPage.tsx` – Einstellungen → Plugins: Hauptschalter, Liste **aller**
  gefundenen Plugins (auch fehlerhafte, mit Grund), Schalter je Plugin, Einzelschalter je Hook, Rechte im Klartext,
  Bestätigungsdialog (mit Differenz bei Rechte-Erweiterung), Installieren (`.rfplugin`/`.zip`), Ordner öffnen,
  Neu einlesen, Protokoll, Entfernen. Schalter als `role="switch"` mit `aria-label` (passt zu v0.8.0).
- Ausgeführt werden Plugins noch **nicht** – die Seite ist als „Experimentell“ markiert.

### Tests

`src/backend/tests/test_plugin_system.py` (49 Tests): Manifest, Wasm-Prüfung (gültig / fremder Import / Modul
statt Component / kein Wasm), alle Statusübergänge, Hauptschalter, abgesicherter Modus, Update mit gleichen,
weniger und mehr Rechten, Installation inkl. Pfad-Traversal und unerlaubter Dateien, Entfernen, API.
Fixtures: `tests/fixtures/plugins/*.wasm`, Quellen + `build.sh` in `tests/fixtures/plugins/quelle/`.

### Phase 3 – umgesetzt

| Datei | Inhalt |
|---|---|
| `src/backend/plugins/laufzeit.py` | Laufzeit: `vor_aenderung()` (Pre-Hooks, synchron, Kette in fester Reihenfolge nach Plugin-ID, gemeinsames 50-ms-Budget), `nach_aenderung()` (Post-Hooks im Hintergrund, je 5 s), `testlauf()`, `hat_hooks()` als schnelle Vorprüfung für Phase 5 |
| `src/backend/plugins/host_api.py` | Vertrag `HostApi` für Phase 4, `pruefe_recht()` gegen die **bestätigten** Rechte, `KeinDatenzugriff` als Platzhalter |
| `src/backend/plugins/registry.py` | `laufende_plugins()` (eigene Session, gecacht bis Status- oder Dateiänderung), Datei-Cache für den Ordner-Scan, `status_geaendert()` |
| `src/backend/api/plugins.py` | `POST /api/plugins/{id}/testen` |
| `PluginsPage.tsx` | Bereich „Testlauf“ in den Details: Hook wählen, Beispiel-JSON, Ergebnis + Laufzeit |

Festgelegtes Verhalten:
- **Isolation:** frische Instanz je Aufruf, 64 MB Speicherlimit, kein WASI. Host-API-Aufrufe laufen über einen
  Kontext-Stapel (contextvars) – auch verschachtelt korrekt zugeordnet.
- **Zeitlimit:** Epoch-Interruption mit 5-ms-Ticks; der Ticker-Thread tickt nur, solange ein Plugin läuft (kein
  Dauer-Wakeup im Leerlauf). Kompilieren zählt nicht ins Budget.
- **Fehler:** Trap, Timeout, ungültiges JSON/kein Objekt, Antwort > 1 MB → protokolliert, Fehlerzähler +1; nach 3 Fehlern
  in Folge `automatisch_deaktiviert` (sofort im Speicher, kurz danach in der DB). Ein Erfolg setzt den Zähler zurück.
  `err(reason)` des Plugins ist **kein** Fehler.
- **Pre-Hook-Fehler bricht das Speichern ab** (`BEI_FEHLER_ABBRECHEN = True`, offene Frage 3 – vorläufig wie empfohlen).
- **Python-Exceptions** in der Host-API gelangen nie ins Plugin; es sieht nur „Interner Fehler in RechnungsFee“.
- **Verschachtelung:** Löst ein Plugin über die Host-API weitere Hooks aus, wird es selbst nicht erneut aufgerufen;
  maximal 2 Ebenen.
- **DB-Zugriffe der Laufzeit** (Protokoll, Fehlerzähler) nur im Hintergrund-Thread mit eigener Session – der Aufrufer
  steckt typischerweise in einer offenen Schreib-Transaktion, ein zweiter Schreiber im selben Thread würde auf deren
  SQLite-Lock warten (Deadlock).
- **Protokoll:** reine „ok“-Durchläufe werden nicht protokolliert (sonst eine Zeile pro Speichervorgang), sonst alles;
  max. 5000 Einträge je Plugin.

Messwerte (Linux, warm): Pre-Hook-Kette mit einem Plugin inkl. Registry-Abfrage 1,4 ms; Testlauf im gefrorenen
Sidecar 0,8–1,6 ms, Timeout greift nach ~58 ms. Tests: `tests/test_plugin_laufzeit.py` (22 Tests, 5× hintereinander stabil).

### Phase 4 – umgesetzt (Lesen und Schreiben)

| Datei | Inhalt |
|---|---|
| `src/backend/plugins/dto.py` | Eingefrorene V1-DTOs mit `"_schema": "<entity>@1"`: `customer` (Kunde), `invoice` (Rechnung inkl. Positionen – umfasst alle Zeilen von `rechnungen`, also auch Angebote, Aufträge, Lieferscheine, Proforma, Gutschriften und Eingangsrechnungen; unterscheidbar über `typ`/`dokument_typ`), `article` (Artikel), `voucher` (Beleg) |
| `src/backend/plugins/host_api.py` | `LeseZugriff`: `get`/`list` (Gleichheitsfilter auf DTO-Felder, `limit` ≤ 100, `offset`) |

Schreibzugriffe stehen über `plugins/schreiben.py::DatenZugriff` bereit: Kunden,
Artikel und Rechnungsentwürfe mit gemeinsam genutzten CRUD-Helfern, Savepoints,
Rechteprüfung, Audit und verschachtelten Hooks. Pre-Hook-Schreibzugriffe rollen mit
der äußeren Transaktion zurück; Post-Hooks committen je Host-Aufruf.
Details und Python-Aufrufe: [Host-API für Entwickler](plugin-host-api.md).

- **`voucher` = Beleg** (Entscheidung Stefan): die hochgeladene Belegdatei aus `belege`, nur Metadaten
  (`original_name`, `mime_type`, `dateigroesse`, `sha256`, `hochgeladen_am`) – interne Dateipfade und Inhalt nicht.
  Rechnungen tragen `beleg_id`. Belege sind für Plugins nie änderbar (GoBD).
- **`task`** antwortet „gibt es in dieser Version noch nicht“ (Phase 6).
- **Änderbar durch Pre-Hooks** (alles andere wird ignoriert und protokolliert):
  Kunde: Name/Anrede/Adresse/Kontakt/USt-IdNr./Notizen · Artikel: Bezeichnung, Beschreibung, Einheit, Hersteller,
  Artikelcode (keine Preise) · Rechnung: Einleitungs-/Schlusstext, Notizen, Kunden-Bestellnr., externe Belegnr.,
  Leistungszeitraum – **nur im Entwurf**; finalisierte/stornierte Dokumente sind gesperrt (GoBD).
  Nummern, IDs, Beträge, Positionen, Zahlungsstatus kann kein Plugin ändern. Ungültige Werte (Typ, Länge, Datum) werden verworfen.

### Phase 5 – umgesetzt

`src/backend/plugins/ereignisse.py`, registriert in `main.py` auf `SessionLocal`:

| Event | Aufgabe |
|---|---|
| `before_flush` | zu löschende Objekte als DTO sichern |
| `after_flush` | neue/geänderte Objekte merken; Positionsänderungen = `invoice:update` |
| `before_commit` | Pre-Hooks mit dem **vollständigen** Stand (Endpunkte flushen oft mehrfach – erst Rechnung, dann Positionen), gemeinsames 50-ms-Budget je Transaktion, erlaubte Änderungen zurückschreiben |
| `after_commit` | Post-Hooks im Hintergrund (eigene Session je Aufruf) |
| `after_rollback` | Gesammeltes verwerfen – kein Post-Hook für Zurückgerolltes |

- `PluginAbbruch` → **HTTP 422** `{"detail": "Plugin „Name“: Meldung", "plugin_id": …}` (Exception-Handler in `main.py`).
  Das Frontend zeigt `detail` ohne Änderung im jeweiligen Formular an (geprüft am Kundenformular).
  Abgebrochene Vorgänge verbrauchen keine Rechnungsnummer (gleiche Transaktion, wird zurückgerollt).
- **Ohne Plugins:** App-Start (`startup()`), Datenübernahme (`api/datenmigration.py::import_durchfuehren`) und
  Rechnungs-CSV-Import (`api/rechnungen_import.py::import_durchfuehren`) über `ohne_plugins()`/`@plugins_aus`.
- **Kosten ohne aktive Plugins:** +0,08 ms pro Commit (gemessen, 400 Commits).
- **Bewusste Lücke:** `query.update()/delete()` und rohes SQL laufen an den ORM-Events vorbei (betrifft Migrationen/Datenfixes).
- Gefundener und behobener Fehler beim Testen: Die Registrierung erkannte „schon registriert“ über `id()` der
  Session-Factory – Python vergibt IDs freigegebener Objekte neu, auch SQLAlchemys `event.contains()` hängt daran.
  Jetzt Markierung direkt am Objekt. (Betraf nur Tests mit vielen Factories, nicht `SessionLocal`.)

Ende-zu-Ende geprüft (uvicorn und gefrorener Sidecar): Kunde anlegen/ändern mit Abbruch → 422, Datensatz
unverändert; erlaubte Feldänderung übernommen; Rechnung anlegen + finalisieren mit aktiven Plugins; Rechnungs-Pre-Hook
bricht ab; Plugin-Änderung am Entwurf übernommen. Einstellungsseite: Hinweis auf nutzbare Schreibrechte und geschützte Entitäten.

Tests: `tests/test_plugin_ereignisse.py` (20 Tests), insgesamt 91 Plugin-Tests, 15× hintereinander stabil.

### Python-Beispiel

Unter [examples/plugins/python-kundenpruefung](../examples/plugins/python-kundenpruefung/README.md)
liegt ein baubares Python-Prüfplugin: `componentize-py` übersetzt den Gast in eine
Wasm-Component ohne WASI-Imports. Enthalten sind Manifest, Paketierung, lokale
Unit-Tests und ein Smoke-Test gegen die unveränderte Sandbox (64 MB / 50 ms).
Damit gibt es eine Python-Einstiegsanleitung; die Rust-SDK-Vorlage und das
Aufgaben-Referenzplugin aus Phase 6 bleiben offen.

### Nächste Schritte

- **Erledigt: Host-API-Schreiben** (`create`/`update`/`delete`) für Kunden, Artikel und Rechnungsentwürfe,
  inklusive gemeinsamer Core-Logik, Transaktions-/Dateisicherheit, Audit und Rekursionsschutz.
- **Phase 6:** Aufgaben-Tabelle (`task`), Referenz-Plugin in Rust, SDK-Vorlage.
- **Offene Frage 3** (Fehler im Pre-Hook → Speichern abbrechen?) steht weiter auf „abbrechen“ (`BEI_FEHLER_ABBRECHEN`).
- Vor einem Release: CI-Build Windows/macOS mit Plugin-Smoke-Test.
---

## 1. Zielbild

```
Frontend (React)                         Python-Backend (FastAPI)
┌──────────────────────┐   REST   ┌─────────────────────────────────────────────────────────┐
│ Einstellungen →      │ ───────► │ api/plugins.py  (Liste, aktivieren, deaktivieren, …)    │
│ Plugins (Liste,      │          │        │                                                │
│ Schalter, Details)   │          │        ▼                                                │
└──────────────────────┘          │ plugins/registry.py  ◄── plugins/manifest.py (TOML)     │
                                  │        │      ▲                                         │
                                  │        │      └── Tabelle plugin_status (pro Profil)    │
                                  │        ▼                                                │
                                  │ plugins/runtime.py  (wasmtime, Fuel/Epoch, Limits)      │
                                  │        ▲                  │ Host-API-Aufrufe            │
                                  │        │ Hooks            ▼                             │
                                  │ plugins/events.py   plugins/host_api.py ─► DTO-Layer    │
                                  │  before_flush ──┐         (Rechte-Guard, GoBD-Regeln)   │
                                  │  after_commit ──┘                                       │
                                  │        ▲                                                │
                                  │ SQLAlchemy-Session (bestehende Endpunkte unverändert)   │
                                  └─────────────────────────────────────────────────────────┘
```

Neues Paket `src/backend/plugins/`:

| Datei | Aufgabe |
|---|---|
| `manifest.py` | `plugin.toml` parsen (`tomllib`, stdlib) und gegen Schema validieren |
| `registry.py` | Plugin-Verzeichnis scannen, Status aus DB mergen, aktive Plugins im Speicher halten, Hot-Reload |
| `runtime.py` | wasmtime-Engine, Component laden, Sandbox-Limits, Aufrufe mit Timeout |
| `host_api.py` | Implementierung von `host-api` (get/list/create/update/delete) mit Rechteprüfung |
| `dto.py` | Stabile JSON-Darstellung je Entität (versioniert), Mapping DTO ↔ ORM |
| `events.py` | SQLAlchemy-Session-Events → Pre-/Post-Hooks, Worker-Queue für Post-Hooks |
| `protokoll.py` | Aufruf- und Fehlerprotokoll schreiben |

---

## 2. Phasen

### Phase 0 – Spike & Grundsatzentscheidungen (Voraussetzung für alles)

1. Minimal-Plugin in Rust mit `cargo component` gegen die `rechnungsfee.wit` aus dem Lastenheft bauen.
2. Mit `wasmtime` (PyPI) laden: `python -m wasmtime.bindgen` erzeugt Python-Bindings; Host-Imports über die generierte Imports-Klasse bereitstellen.
3. Messen: Kaltstart (Laden + Instanziieren), Warmaufruf eines Pre-Hooks mit ~5 KB JSON. Ziel: Warmaufruf deutlich unter 10 ms, damit das 50-ms-Budget auch für mehrere Plugins reicht.
4. Sandbox prüfen: Endlosschleife per **Epoch-Interruption** (`engine.increment_epoch()` aus Timer-Thread + `store.set_epoch_deadline`) oder **Fuel** abbrechen; Speicherlimit über `store.set_limits`; Trap darf den Prozess nicht beenden.
5. PyInstaller-Sidecar bauen (`scripts/build-sidecar.sh` / `.ps1` um `--collect-all wasmtime` ergänzen) und auf **Linux, Windows, macOS (arm64 + x86_64)** starten.
6. Entscheidung dokumentieren: Option A bestätigt oder Fallback auf B.

**Ergebnis:** Go/No-Go, Messwerte, ggf. angepasste Bindgen-Strategie (generierte Bindings pro Plugin vs. generischer Loader).

### Phase 1 – Plugin-Erkennung, Manifest, Status-Speicher

**Verzeichnisse**
- Plugin-Dateien **global** (nicht pro Profil): `BASE_DIR/plugins/<plugin-id>/plugin.toml` + `plugin.wasm`.
  `BASE_DIR` aus `database/connection.py` verwenden, keinen eigenen Pfad hartkodieren (siehe CLAUDE.md, Profilmanager).
- Aktivierungsstatus **pro Profil** in der Profil-DB – Plugins arbeiten auf Profildaten, und ein Plugin, das im
  Geschäftsprofil laufen soll, muss es im Testprofil nicht.

**Manifest-Validierung** (`manifest.py`)
- Pflichtfelder: `id` (Reverse-DNS, eindeutig), `name`, `version` (SemVer), `author`, `description`.
- Ergänzung zum Lastenheft: `api_version = "0.1.0"` (WIT-Paketversion) und optional `min_app_version`.
- `permissions.entities`: nur bekannte Entitäten/Aktionen; `hooks`: Format `entity:action:before|after`.
- Konsistenz: Wer `invoice:create:before` abonniert, braucht keine Host-API-Rechte, aber Hooks auf Entitäten
  ohne passende Leserechte werden als Warnung angezeigt.
- Ungültige Plugins werden **nicht** verworfen, sondern mit Status `fehlerhaft` und Grund gelistet (für die Einstellungsseite).

**Migration** (`main.py`, neuer `if version < N:`-Block, `SCHEMA_VERSION` erhöhen):

```sql
CREATE TABLE plugin_status (
    plugin_id                 VARCHAR(200) PRIMARY KEY,
    aktiv                     BOOLEAN NOT NULL DEFAULT 0,
    wasm_sha256               VARCHAR(64),      -- Hash zum Zeitpunkt der Freigabe
    genehmigte_rechte_json    TEXT,             -- Snapshot der bestätigten [permissions]
    deaktivierte_hooks_json   TEXT,             -- optional: einzelne Hooks abgeschaltet
    aktiviert_am              DATETIME,
    fehler_in_folge           INTEGER NOT NULL DEFAULT 0,
    letzter_fehler            TEXT,
    letzter_fehler_am         DATETIME
);

CREATE TABLE plugin_protokoll (
    id            INTEGER PRIMARY KEY,
    plugin_id     VARCHAR(200) NOT NULL,
    hook          VARCHAR(50)  NOT NULL,        -- z. B. invoice:create:before / host-api:create
    entitaet      VARCHAR(30),
    datensatz_id  INTEGER,
    ergebnis      VARCHAR(20)  NOT NULL,        -- ok | geaendert | abgebrochen | fehler | timeout
    dauer_ms      INTEGER,
    meldung       TEXT,
    erstellt_am   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

Globaler Hauptschalter „Plugins aktiv“ als Feld in `unternehmen` (5-Stellen-Checkliste aus CLAUDE.md beachten)
oder als Key in einer kleinen Einstellungstabelle – siehe offene Fragen.

**Statuslogik der Registry**

| Status | Bedingung | Läuft? |
|---|---|---|
| `neu` | Im Ordner gefunden, noch kein Eintrag in `plugin_status` | nein |
| `aktiv` | `aktiv = 1`, Hash passt, Rechte unverändert | ja |
| `deaktiviert` | vom Nutzer abgeschaltet | nein |
| `aktualisiert` | Hash geändert, Rechte gleich oder geringer | ja (Hinweis in der UI) |
| `rechte_erweitert` | Hash geändert **und** neue Rechte/Hooks | nein, bis erneut bestätigt |
| `fehlerhaft` | Manifest ungültig, Wasm lädt nicht, WIT-Version inkompatibel | nein |
| `automatisch_deaktiviert` | N Fehler/Timeouts in Folge (Vorschlag: 3) | nein |

Standard für neu gefundene Plugins: **aus** (Opt-in). Ein Plugin, das nur in den Ordner kopiert wird, darf nichts tun,
bevor der Nutzer die Rechte gesehen und bestätigt hat.

### Phase 2 – Einstellungsseite „Plugins“

Kommt bewusst **vor** der Laufzeit: Erkennung, Anzeige und An/Aus sind ohne Wasm-Ausführung testbar, und die Seite
ist ab Phase 3 sofort das Werkzeug zum Debuggen.

**Backend – `api/plugins.py`**

| Methode | Pfad | Zweck |
|---|---|---|
| GET | `/api/plugins` | Alle gefundenen Plugins inkl. Manifest, Status, Rechte, Hooks, Fehler, Kennzahlen; plus globaler Schalter |
| POST | `/api/plugins/neu-einlesen` | Ordner neu scannen |
| POST | `/api/plugins/{id}/aktivieren` | Body: bestätigte Rechte (Hash + Rechte-Snapshot). Lädt das Plugin sofort. |
| POST | `/api/plugins/{id}/deaktivieren` | Wirkt sofort, ohne Neustart (Registry entfernt das Plugin aus der Hook-Tabelle) |
| PUT | `/api/plugins/{id}/hooks` | Optional: einzelne Hooks eines Plugins abschalten |
| PUT | `/api/plugins/einstellungen` | Globaler Hauptschalter |
| GET | `/api/plugins/{id}/protokoll` | Letzte Aufrufe/Fehler (paginiert) |
| POST | `/api/plugins/installieren` | Upload eines `.rfplugin` (ZIP mit `plugin.toml` + `plugin.wasm`) → entpacken nach `BASE_DIR/plugins/<id>/`, Status `neu` |
| DELETE | `/api/plugins/{id}` | Plugin-Ordner entfernen (Status-/Protokolleinträge bleiben für Nachvollziehbarkeit) |

**Frontend**
- Neuer Eintrag in `einstellungenNav` (`AppLayout.tsx`): `{ to: '/plugins', label: 'Plugins', icon: 'extension' }`.
- Route in `App.tsx`, Seite `src/frontend/src/pages/einstellungen/PluginsPage.tsx`, Typen + Calls in `api/client.ts`.
- Aufbau der Seite (Du-Ansprache):
  - **Kopf:** Hauptschalter „Plugins verwenden“, Buttons „Plugin installieren…“ (Tauri-Dateidialog, `tauri-plugin-dialog` ist schon da), „Ordner öffnen“, „Neu einlesen“.
  - **Liste aller verfügbaren Plugins** – auch fehlerhafte und inkompatible, jeweils als Karte:
    Name, Version, Autor, Beschreibung, Status-Badge, **Schalter An/Aus**.
  - **Detailbereich (aufklappbar):** Rechte in Klartext („Darf Rechnungen lesen“, „Darf Aufgaben anlegen und ändern“),
    abonnierte Hooks in Klartext („Prüft Rechnungen vor dem Speichern“, „Reagiert nach dem Anlegen einer Rechnung“),
    optional Einzelschalter je Hook, letzte Fehler, Aufrufzahl und Ø-Laufzeit, Plugin-ID und Hash.
  - **Aktivieren-Dialog:** listet die angeforderten Rechte, Hinweis bei Pre-Hooks („Dieses Plugin kann das Speichern
    von Rechnungen verhindern oder Daten vor dem Speichern verändern“), Bestätigen-Button.
  - Bei `rechte_erweitert`: deutliche Markierung, Diff alt/neu, erneute Bestätigung nötig.
  - Leerer Zustand: kurze Erklärung, was Plugins sind, Link zur Entwickler-Doku.
- Fehlermeldungen aus Pre-Hooks: Backend liefert HTTP 422 mit `detail = "Plugin „<Name>“: <Grund>"`; prüfen, dass die
  bestehende Fehleranzeige in den Formularen `detail` anzeigt.

### Phase 3 – Wasm-Laufzeit & Sandbox

- Eine `wasmtime.Engine` pro Prozess (Epoch-Interruption aktiviert), kompilierte Components werden gecacht
  (Key: SHA-256 der `.wasm`). Instanz pro Aufruf oder gepoolt – nach Messwerten aus Phase 0.
- **Keine WASI-Rechte:** kein Dateisystem, kein Netzwerk, keine Umgebungsvariablen. Nur die `host-api`-Imports.
- Limits pro Aufruf: Speicher (z. B. 64 MB), Pre-Hook-Deadline aus dem 50-ms-Budget, Post-Hook großzügiger (z. B. 5 s).
- Jeder Trap, Timeout oder ungültige Rückgabewert → Eintrag in `plugin_protokoll`, `fehler_in_folge++`;
  bei Erreichen des Grenzwerts → `automatisch_deaktiviert` und Hinweis in der UI (Banner/Badge an „Einstellungen“).
- Ein Plugin-Fehler wird nie als 500 nach außen gereicht, sondern definiert behandelt (siehe Phase 5).
- Notbremse: Umgebungsvariable `RECHNUNGSFEE_PLUGINS=0` startet ohne Plugins (Abgesicherter Modus), falls ein
  Plugin die App unbedienbar macht.

### Phase 4 – DTO-Layer & Host-API

**Entitäts-Mapping** (stabile, versionierte JSON-Form – nicht die ORM-Interna, damit Schema-Migrationen Plugins nicht brechen):

| WIT `entity-type` | RechnungsFee | Anmerkung |
|---|---|---|
| `customer` | `Kunde` | inkl. Lieferadressen read-only |
| `invoice` | `Rechnung` + `Rechnungsposition` | Positionen eingebettet |
| `voucher` | `Beleg` (Tabelle `belege`) | entschieden 2026-10-28, nur lesend (GoBD) |
| `article` | `Artikel` | |
| `task` | neu (`Aufgabe`) | siehe Phase 6 |

Für die DTOs vorhandene Pydantic-Schemas (`api/schemas.py`, `schemas_rechnungen.py`, `schemas_artikel.py`) als
Ausgangspunkt nehmen, aber als eigene `Plugin*V1`-Modelle einfrieren.

**Rechte-Guard** (FA-1.3 umgesetzt als Laufzeitprüfung): jeder Host-API-Aufruf wird gegen den **bestätigten**
Rechte-Snapshot aus `plugin_status` geprüft, nicht gegen das aktuelle Manifest. Ein statischer Abgleich „Manifest vs.
tatsächlich aufgerufene Funktionen“ ist bei Wasm nicht zuverlässig möglich; das Lastenheft sollte FA-1.3 entsprechend
umformulieren.

**GoBD-Regeln – gelten für Plugins genauso wie für die UI, ohne Ausnahme:**
- Finalisierte/ausgegebene Rechnungen: kein `update`, kein `delete` – auch nicht über Pre-Hook-Payload-Änderung.
- `journal`, `tagesabschluesse`, `vorsteuer_ansprueche`: höchstens `read`/`create`, nie `update`/`delete`
  (die SQLite-Trigger aus `_setup_gobd_triggers()` greifen ohnehin; der Guard soll vorher mit verständlicher Meldung abweisen).
- Rechnungsnummern/Nummernkreise vergibt ausschließlich der Core.
- Schreibende Host-API-Aufrufe verwenden dieselbe Logik wie die Endpunkte (Service-Funktionen aus den Routern
  herauslösen, wo nötig) – kein zweiter, abweichender Schreibweg.
- Jede Änderung durch ein Plugin wird in `plugin_protokoll` mit Plugin-ID nachgewiesen (Verfahrensdokumentation).

**Rekursion:** Schreibt ein Plugin per Host-API, lösen die daraus entstehenden Events wieder Hooks aus – aber nicht
beim auslösenden Plugin selbst, und mit maximaler Tiefe (Vorschlag: 2).

**Synergie mit dem MCP-Plan (`plan-mcp-server.md`):** Beide brauchen eine kuratierte, rechtegeprüfte Schnittstelle auf
die Kern-Entitäten. DTO-Layer und Service-Funktionen so schneiden, dass ein späterer MCP-Server sie wiederverwenden kann.

### Phase 5 – Event-Pipeline

Statt jeden Endpunkt anzufassen: zentral über **SQLAlchemy-Session-Events** auf `SessionLocal`.

- **Pre-Hooks (`on-before-change`)** – `before_flush`:
  - Neue/geänderte/gelöschte Objekte der gemappten Klassen aus `session.new` / `session.dirty` / `session.deleted` ermitteln
    → Aktion `create` / `update` / `delete`.
  - Aktive Plugins mit passendem Hook in fester Reihenfolge (nach Plugin-ID oder `priority` im Manifest) aufrufen;
    Payload wird durchgereicht (Plugin 2 sieht die Änderung von Plugin 1).
  - `ok(payload)` → geänderte Felder über Whitelist zurück ins ORM-Objekt schreiben (keine IDs, keine Nummern, keine GoBD-Felder).
  - `err(reason)` → Exception `PluginAbbruch` → bestehende Session wird zurückgerollt; globaler Exception-Handler in
    `main.py` übersetzt in HTTP 422.
  - Gesamtbudget 50 ms pro Flush über alle Plugins; Überschreitung → Verhalten laut offener Frage (fail-closed/-open).
  - Achtung: `before_flush` kann pro Transaktion mehrfach feuern – bereits verarbeitete Objekte in `session.info` merken.
- **Post-Hooks (`on-after-change`)** – Ereignisse in `session.info` sammeln, in `after_commit` an eine
  **einzelne Worker-Queue** (ein Thread) übergeben; bei `after_rollback` verwerfen.
  Ein Worker statt Thread-Pool, weil SQLite nur einen Schreiber gleichzeitig erlaubt; der Worker nutzt eine eigene `SessionLocal()`.
- **Bekannte Lücke:** Raw-SQL (`text(...)`) und Bulk-Updates umgehen ORM-Events. Betroffene Schreibwege für die fünf
  Entitäten inventarisieren und entweder auf ORM umstellen oder explizit `events.emit(...)` aufrufen.
  Migrationen und Seed laufen ohne Plugins (Registry ist beim Start noch nicht aktiv).
- Backup-Wiederherstellung, Datenmigration und Profilwechsel: Hooks während dieser Vorgänge unterdrücken.

### Phase 6 – Aufgaben-Entität, Referenz-Plugin, SDK

- **Aufgaben (`task`):** Das Referenz-Szenario braucht eine Aufgaben-Tabelle, die es heute nicht gibt. Minimal:
  `aufgaben(id, titel, beschreibung, faellig_am, erledigt, bezug_entitaet, bezug_id, quelle_plugin_id, erstellt_am)`,
  plus einfache Liste (z. B. im Cockpit, vgl. `plan-cockpit.md`). Alternativ v1 ohne `task` starten und das
  Referenz-Plugin auf ein Prüf-Plugin (nur Pre-Hook) reduzieren.
- **Referenz-Plugin `org.rechnungsfee.task-automation`** gemäß Lastenheft Abschnitt 7, in eigenem Repo oder unter `plugins-examples/`.
- **SDK/Template:** Rust-Vorlage mit `cargo component`, fertig eingebundener WIT, Beispiel-Tests, Build-Skript für `.rfplugin`.
  WIT-Datei als `src/backend/plugins/wit/rechnungsfee.wit` versioniert ins Repo.

### Phase 7 – Tests, Packaging, Doku, Release

- **Tests (`src/backend/tests/`):** Manifest-Validierung, Statusübergänge (Hash-/Rechteänderung), Rechte-Guard,
  GoBD-Sperren, Pre-Hook-Abbruch → Rollback, Payload-Änderung, Timeout/Trap → Auto-Deaktivierung, Post-Hook nach
  Rollback wird nicht ausgeführt, Rekursionsgrenze. Test-Plugins als vorkompilierte `.wasm` in `tests/fixtures/`.
- **Packaging:** `build-sidecar.sh`/`.ps1` (`--collect-all wasmtime`), CI für alle drei Plattformen,
  `THIRD_PARTY_LICENSES.txt` um wasmtime (Apache-2.0 WITH LLVM-exception) ergänzen.
- **Doku:** Wiki-Seite „Plugins“ für Nutzer, Entwickler-Doku (WIT, Manifest, DTO-Formate, Rechte, GoBD-Grenzen),
  Hilfe-Eintrag (vgl. `12-hilfe-system.md`), CHANGELOG, `13-implementierungsstand.md`, ROADMAP.
- **Release:** zuerst als **experimentell** kennzeichnen (Hinweis auf der Einstellungsseite), Hauptschalter standardmäßig aus.

---

## 3. Reihenfolge & Abhängigkeiten

```
Phase 0 (Spike) ──► Phase 1 (Registry/DB) ──► Phase 2 (Einstellungen-UI)
                                   │
                                   └──► Phase 3 (Runtime) ──► Phase 4 (DTO/Host-API) ──► Phase 5 (Events)
                                                                                              │
                                                       Phase 6 (Aufgaben, Referenz, SDK) ◄────┘
                                                                                              │
                                                                                  Phase 7 (Tests, Release)
```

Phase 2 und 3 können parallel laufen. Sinnvoller erster Meilenstein: **Phasen 0–2** – Plugins werden erkannt,
in den Einstellungen gelistet und lassen sich an-/abschalten, auch wenn sie noch nichts ausführen.
Zweiter Meilenstein: **Phasen 3–5 nur mit Pre-Hooks und Leserechten** (kein Schreiben per Host-API) – das ist der
risikoärmste Weg, echte Plugins (z. B. Rechnungsprüfungen) zu ermöglichen.

---

## 4. Vorgeschlagene Anpassungen am Lastenheft

1. **Abschnitt 2:** Host im Python-Backend statt „RechnungsFee Core (Rust)“ (siehe Abschnitt 0).
2. **FA-1.1:** Pfad konkretisieren – `BASE_DIR/plugins/<id>/`, global; Aktivierung pro Profil.
3. **FA-1.3:** „validiert … gegen die tatsächlich ausgeführten Host-API-Aufrufe“ → Laufzeit-Durchsetzung gegen den vom Nutzer bestätigten Rechte-Snapshot.
4. **Neu FA-1.4:** Plugins sind nach dem Fund standardmäßig deaktiviert; Aktivierung erfordert Bestätigung der Rechte; Rechte-Erweiterung bei Update erfordert erneute Bestätigung.
5. **Neu FA-1.5:** Nutzer sieht alle verfügbaren Plugins in den Einstellungen und kann jedes einzeln (optional je Hook) deaktivieren; wirkt ohne Neustart.
6. **Neu NFA-4 (GoBD):** Plugins unterliegen denselben Unveränderbarkeitsregeln wie die UI; alle Plugin-Änderungen werden protokolliert.
7. **Manifest:** `api_version`, optional `min_app_version`, optional `priority`.
8. **WIT:** `list` → `%list` und `result<(), …>` → `result<_, …>` (sonst nicht übersetzbar, Phase 0); `crud-action::read` als Hook-Auslöser streichen oder bewusst nicht unterstützen (Lese-Hooks würden jede Liste verlangsamen);
   optional Host-Import `log(level, message)` für Plugin-Diagnose im Protokoll.

---

## 5. Offene Fragen

1. ~~**Option A bestätigen?**~~ – Spike positiv, siehe Umsetzungsstand.
2. ~~**`voucher`**~~ – entschieden: Beleg (Tabelle `belege`), siehe Phase 4.
3. **Pre-Hook-Timeout/Absturz:** Speichern abbrechen (fail-closed, sicherer für Prüf-Plugins) oder Plugin überspringen und
   speichern (fail-open, nutzerfreundlicher)? Vorschlag: fail-closed mit verständlicher Meldung + Auto-Deaktivierung nach 3 Fehlern.
4. **Granularität des Abschaltens:** reicht An/Aus pro Plugin, oder auch einzelne Hooks?
5. **Aufgaben-Entität** in v1 mitbauen oder Referenz-Szenario auf Prüf-Plugin reduzieren?
6. **Hauptschalter:** pro Profil (Feld in `unternehmen`) oder global für alle Profile? *Vorläufig: pro Profil, eigene Tabelle `plugin_einstellungen`.*
7. **Verteilung:** nur manuelle Installation (`.rfplugin`), oder später Signaturen/Plugin-Verzeichnis? Für v1 Vorschlag: nur lokal, keine Signaturpflicht, aber Hash-Anzeige.
