# RechnungsFee lokal bauen (AppImage)

Diese Anleitung beschreibt, wie du die Desktop-App selbst kompilierst und als AppImage testest –
z. B. um eine Änderung vor dem Release auszuprobieren. Für die tägliche Entwicklung reicht der
Dev-Modus (Backend + Vite, siehe [CONTRIBUTING.md](../CONTRIBUTING.md)); bauen musst du nur, wenn
du das fertige Paket testen willst.

Stand: 2026-10-28 · Build nach dieser Anleitung geprüft unter Ubuntu 24.04 (AppImage gebaut, gebündelter
Sidecar inkl. Plugin-System getestet). Die Arch-/CachyOS-Pakete entsprechen den Ubuntu-Paketen, der
Build selbst ist dort nicht separat durchgelaufen.

---

## Was beim Bauen entsteht

```
src/frontend  ── npm run build ──────────────►  src/frontend/dist      (React-Oberfläche)
src/backend   ── scripts/build-sidecar.sh ───►  src-tauri/binaries/backend-<target-triple>
                 (PyInstaller, ein einziges Binary mit Python, FastAPI, wasmtime …)
src-tauri     ── tauri build ────────────────►  src-tauri/target/release/bundle/appimage/
                 (Rust-Hülle, bündelt dist/ + Sidecar)        RechnungsFee_<version>_amd64.AppImage
```

- Das Frontend baut `tauri build` selbst (`beforeBuildCommand` in `src-tauri/tauri.conf.json`).
- Den **Sidecar musst du vorher selbst bauen** – `tauri build` nimmt einfach, was in
  `src-tauri/binaries/` liegt. Ein veralteter Sidecar ist die häufigste Fehlerquelle.
- Die Versionsnummer im lokalen Build ist `0.1.0` (aus `tauri.conf.json`). Die echte Version
  setzt nur die CI aus dem Git-Tag – das ist so gewollt.

---

## Voraussetzungen

| Was | Version | Wofür |
|---|---|---|
| Python | **3.12** (wie CI) | Backend + PyInstaller-Sidecar |
| Node.js + npm | 22 | Frontend, Tauri-CLI |
| Rust (rustup, stable) | ≥ 1.77.2 | Tauri-Hülle (`src-tauri`) |
| Tauri-CLI | 2.x | wird per `npx` geholt, keine Installation nötig |
| Systembibliotheken | siehe unten | WebKitGTK, GTK 3, AppImage-Werkzeuge |
| `fuse2` / `libfuse2` | – | nur zum **Starten** des AppImages |

> **Python-Version:** Die CI baut mit 3.12. Neuere Versionen (3.13/3.14, z. B. aktuelles Arch) sind
> nicht getestet – einzelne Abhängigkeiten liefern dafür evtl. noch keine fertigen Pakete. Am
> einfachsten nimmst du 3.12 über `uv` (siehe unten).

### Arch Linux / CachyOS

```bash
sudo pacman -S --needed base-devel webkit2gtk-4.1 gtk3 librsvg libappindicator-gtk3 \
    patchelf rustup nodejs npm uv fuse2
rustup default stable
uv python install 3.12          # Python 3.12 neben dem System-Python, ohne AUR
```

### Debian / Ubuntu (22.04, 24.04)

Gleiche Pakete wie in `.github/workflows/build.yml`:

```bash
sudo apt-get update
sudo apt-get install -y build-essential curl file \
    libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf libgtk-3-dev \
    libfuse2            # auf 24.04 installiert apt dafür automatisch libfuse2t64
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Node.js 22 und Python 3.12 je nach Distribution aus den Paketquellen, über `nvm`/`uv` o. Ä.
(Ubuntu 24.04 bringt Python 3.12 mit: `sudo apt-get install python3.12-venv`.)

### Windows / macOS

Gleicher Ablauf, Sidecar unter Windows mit `pwsh scripts/build-sidecar.ps1`. Die nötigen
Systemvoraussetzungen beschreibt die [Tauri-Dokumentation](https://tauri.app/start/prerequisites/);
die CI-Schritte je Plattform stehen in `.github/workflows/build.yml`. Diese Anleitung ist für
Windows/macOS nicht separat geprüft.

---

## Einmalig einrichten

Im Projektordner:

```bash
# Python-Umgebung für das Backend - build-sidecar.sh aktiviert src/backend/.venv automatisch
cd src/backend
uv venv --seed --python 3.12 .venv     # oder: python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt pyinstaller
cd ../..

# Frontend-Abhängigkeiten
(cd src/frontend && npm ci)
```

Wichtig bei `uv`: **`--seed`** nicht weglassen. Ohne legt `uv venv` kein `pip` in die Umgebung,
`build-sidecar.sh` greift dann auf das System-`pip` zurück – und das bricht auf Arch/neueren
Ubuntu-Versionen mit „externally-managed-environment“ ab.

Nach jeder Änderung an `src/backend/requirements.txt` den `pip install`-Schritt wiederholen.

---

## Bauen

```bash
# 1. Backend-Sidecar (PyInstaller) - nach JEDER Backend-Änderung neu bauen
bash scripts/build-sidecar.sh

# 2. Tauri-App + AppImage (baut das Frontend dabei mit)
NO_STRIP=true npx --yes @tauri-apps/cli@^2 build --bundles appimage
```

- `--bundles appimage` baut nur das AppImage (die Konfiguration enthält auch NSIS/DMG für andere
  Plattformen).
- `NO_STRIP=true` verhindert, dass das AppImage-Werkzeug (linuxdeploy) Bibliotheken mit seinem
  eingebauten, älteren `strip` bearbeitet – das bricht auf neueren Distributionen (Arch, Fedora …)
  sonst oft mit „failed to run linuxdeploy“ ab. Unter Ubuntu schadet es nicht.
- Alternativ in einem Schritt: `npm run tauri:build` (Sidecar + `tauri build`, alle Pakete) –
  setzt aber eine global installierte Tauri-CLI voraus (`npm install -g @tauri-apps/cli@^2`).

**Dauer** (gemessen auf einer schwachen Maschine mit 2 Kernen – ein Desktop-Rechner ist deutlich
schneller): Sidecar ca. 1,5 Min., erster `tauri build` ca. 9 Min. (davon Rust ca. 7 Min.), danach
schneller (Rust-Cache in `src-tauri/target/`). Das AppImage ist ca.
200 MB groß.

**Ergebnis:**

```
src-tauri/target/release/bundle/appimage/RechnungsFee_0.1.0_amd64.AppImage
```

---

## Testen

Am besten mit eigenem Datenordner, damit deine echten Daten unberührt bleiben – ein neuer Build
kann Datenbank-Migrationen enthalten, die sich nicht zurückdrehen lassen:

```bash
mkdir -p ~/rf-test
HOME=~/rf-test ./src-tauri/target/release/bundle/appimage/RechnungsFee_0.1.0_amd64.AppImage
```

Daten, Profile und Plugins liegen dann unter `~/rf-test/.local/share/RechnungsFee/`.
Zum Aufräumen einfach `~/rf-test` löschen.

Ohne FUSE (z. B. in Containern) startet das AppImage auch so:
`./RechnungsFee_0.1.0_amd64.AppImage --appimage-extract-and-run`

### Plugin-System testen (optional)

Ein Test-Plugin liegt in `src/backend/tests/fixtures/plugins/testplugin.wasm`. Als installierbares
Paket:

```bash
cd src/backend/tests/fixtures/plugins
python3 - <<'EOF'
import zipfile
with zipfile.ZipFile('/tmp/kundenpruefung.rfplugin', 'w') as z:
    z.write('testplugin.wasm', 'plugin.wasm')
    z.writestr('plugin.toml', '''[plugin]
id = "de.test.kundenpruefung"
name = "Kundenprüfung"
version = "1.0.0"
author = "Test"
description = "Prüft Kunden vor dem Speichern."
api_version = "0.1.0"

[permissions]
entities = [ { type = "customer", actions = ["read"] } ]
hooks = [ "customer:create:before", "customer:update:before" ]
''')
EOF
```

In der App: Einstellungen → Plugins → „Plugin installieren…“ → `/tmp/kundenpruefung.rfplugin`,
Plugin und Hauptschalter einschalten. Ein Kunde mit „abbrechen“ in den Notizen wird abgelehnt,
mit „plugin-notiz“ ersetzt das Plugin die Notiz. Details: [plan-plugin-system.md](plan-plugin-system.md).

---

## Unterschied zum Release-AppImage

Die CI (`build.yml`) packt das AppImage nach dem Bauen neu und **entfernt die mitgebündelten
Bibliotheken** (`usr/lib/`) – sonst kollidieren das WebKitGTK/GStreamer aus Ubuntu 22.04 mit neueren
Systemen (Fedora, Bazzite …). Das Release-AppImage nutzt deshalb die Systembibliotheken, die
`install-linux.sh` prüft.

Für einen Test auf **demselben Rechner**, auf dem du gebaut hast, ist das egal. Willst du dein
lokales AppImage auf einem anderen System testen, wiederhole den CI-Schritt
„AppImage Bibliotheken entbündeln“ aus `.github/workflows/build.yml` (AppImage mit
`--appimage-extract` entpacken, `squashfs-root/usr/lib/` löschen, mit `appimagetool` neu packen).

---

## Fehlerbehebung

| Symptom | Ursache / Lösung |
|---|---|
| `failed to run linuxdeploy` beim Bauen | `NO_STRIP=true` setzen (siehe oben) |
| App startet, bleibt aber leer / „Backend nicht erreichbar“ | Sidecar veraltet oder fehlt → `bash scripts/build-sidecar.sh`, danach neu bauen. Der Sidecar lässt sich auch allein testen: `src-tauri/binaries/backend-x86_64-unknown-linux-gnu --port 8123`, dann `curl localhost:8123/health` |
| Sidecar: `ModuleNotFoundError: … __mypyc` | alter Sidecar, gebaut vor dem `charset-normalizer`-Fix → `pip install -r requirements.txt` wiederholen, Sidecar neu bauen |
| Sidecar: `Failed to load dynlib … _libwasmtime` | Sidecar mit altem Build-Skript gebaut (native wasmtime-Bibliothek fehlt) → aktuelles `scripts/build-sidecar.sh` verwenden |
| `Native wasmtime-Bibliothek nicht gefunden` beim Sidecar-Build | wasmtime fehlt in der venv → `pip install -r requirements.txt` |
| AppImage startet nicht: `dlopen(): error loading libfuse.so.2` | `fuse2` (Arch) bzw. `libfuse2`/`libfuse2t64` (Ubuntu) installieren oder `--appimage-extract-and-run` |
| App bricht sofort ab: `panicked … Kein freier Port gefunden` | Die App sucht einen freien Port mit `portpicker` 0.1, das einen Port nur als frei wertet, wenn er **auch unter IPv6** belegbar ist. Bei abgeschaltetem IPv6 (`ipv6.disable=1`, manche Container) findet sie deshalb nie einen. Workaround: IPv6 aktivieren. (Bekannte Einschränkung, beim Test dieser Anleitung in einem Container ohne IPv6 aufgefallen – sollte im Code behoben werden, z. B. Port per Bind auf `127.0.0.1:0` ermitteln.) |
| `pip install` scheitert an einzelnen Paketen | Python-Version prüfen (`.venv/bin/python --version` → 3.12) |
| `tauri dev` meldet Sidecar-Fehler | harmlos, solange du parallel `uvicorn` auf Port 8002 laufen hast – siehe „Dev-Start“ in `CLAUDE.md` |
