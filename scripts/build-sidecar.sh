#!/usr/bin/env bash
# Baut das Python-Backend als PyInstaller-Sidecar für Tauri.
# Ausgabe: src-tauri/binaries/backend-{triple}
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$REPO_ROOT/src/backend"
BINARIES_DIR="$REPO_ROOT/src-tauri/binaries"

# Rust-Target-Triple ermitteln
if command -v rustc &>/dev/null; then
    TRIPLE="$(rustc -vV | sed -n 's/host: //p')"
else
    TRIPLE="x86_64-unknown-linux-gnu"
fi

echo "[Sidecar] Target-Triple: $TRIPLE"
echo "[Sidecar] Backend-Verzeichnis: $BACKEND_DIR"

# Virtuelle Umgebung aktivieren (falls vorhanden)
if [ -f "$BACKEND_DIR/.venv/bin/activate" ]; then
    # shellcheck disable=SC1090
    source "$BACKEND_DIR/.venv/bin/activate"
fi

# PyInstaller sicherstellen
pip install --quiet pyinstaller

mkdir -p "$BINARIES_DIR"

# Binary bauen
cd "$BACKEND_DIR"
pyinstaller \
    --onefile \
    --name backend \
    --distpath "$BINARIES_DIR" \
    --workpath /tmp/pyinstaller_build \
    --specpath /tmp/pyinstaller_spec \
    --hidden-import uvicorn.logging \
    --hidden-import uvicorn.loops \
    --hidden-import uvicorn.loops.auto \
    --hidden-import uvicorn.protocols \
    --hidden-import uvicorn.protocols.http \
    --hidden-import uvicorn.protocols.http.auto \
    --hidden-import uvicorn.protocols.websockets \
    --hidden-import uvicorn.protocols.websockets.auto \
    --hidden-import uvicorn.lifespan \
    --hidden-import uvicorn.lifespan.on \
    --hidden-import api.unternehmen \
    --hidden-import api.konten \
    --hidden-import api.kategorien \
    --hidden-import api.setup \
    --hidden-import api.kassenbuch \
    --hidden-import api.kunden \
    --hidden-import api.lieferanten \
    --hidden-import api.tagesabschluss \
    --hidden-import api.nummernkreise \
    --hidden-import api.export \
    --hidden-import api.rechnungen \
    --hidden-import api.backup \
    --hidden-import api.pdf_vorlagen \
    --hidden-import database.models \
    --hidden-import database.connection \
    --hidden-import database.seed \
    --hidden-import utils.gobd_export \
    --hidden-import utils.pdf_gobd_bericht \
    --hidden-import utils.pdf_tagesabschluss \
    --hidden-import utils.pdf_rechnung \
    --hidden-import utils.pdf_rechnung_vorlage1 \
    --hidden-import utils.pdf_shared \
    --hidden-import utils.signatur \
    --hidden-import utils.zugferd \
    --collect-all segno \
    --collect-all fpdf \
    --collect-all drafthorse \
    --collect-all facturx \
    --collect-all saxonche \
    --add-binary "$BACKEND_DIR/.venv/lib/python3.12/site-packages/saxonche.cpython-312-x86_64-linux-gnu.so:." \
    --add-data "$BACKEND_DIR/.venv/lib/python3.12/site-packages/saxonche.libs:saxonche.libs" \
    --add-data "$BACKEND_DIR/fonts:fonts" \
    main.py

# Binary umbenennen: backend → backend-{triple}
BINARY_SRC="$BINARIES_DIR/backend"
BINARY_DST="$BINARIES_DIR/backend-$TRIPLE"

if [ -f "$BINARY_SRC" ]; then
    mv "$BINARY_SRC" "$BINARY_DST"
    chmod +x "$BINARY_DST"
    echo "[Sidecar] Fertig: $BINARY_DST"
else
    echo "[Sidecar] Fehler: Binary nicht gefunden in $BINARIES_DIR" >&2
    exit 1
fi
