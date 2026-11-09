#!/usr/bin/env bash
# Dev-Start mit Sitzungstoken (Security-Audit F4 Teil 2).
#
# Erzeugt ein frisches Token, startet das Backend (Port 8002) und danach das Frontend –
# beide mit demselben RECHNUNGSFEE_TOKEN. Der Vite-Proxy hängt es als
# „Authorization: Bearer …“ an jeden API-Request an (vite.config.ts).
# Beim Beenden (Strg+C) wird das Backend mit beendet.
#
# Aufruf:
#   scripts/dev-start.sh            # Backend + Vite im Browser (http://localhost:5173)
#   scripts/dev-start.sh --tauri    # Backend + Tauri-Desktop-Fenster (npm run tauri:dev)
#   scripts/dev-start.sh --backend  # nur Backend (z. B. für curl-Tests)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/src/backend"
FRONTEND_DIR="$REPO_ROOT/src/frontend"
PORT=8002

MODUS="browser"
case "${1:-}" in
    ""|--browser) MODUS="browser" ;;
    --tauri)      MODUS="tauri" ;;
    --backend)    MODUS="backend" ;;
    -h|--help)    sed -n 2,13p "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)            echo "Unbekannte Option: $1 (--browser | --tauri | --backend)" >&2; exit 1 ;;
esac

# uvicorn aus der venv, sonst aus dem PATH
if [ -x "$BACKEND_DIR/.venv/bin/uvicorn" ]; then
    UVICORN="$BACKEND_DIR/.venv/bin/uvicorn"
elif command -v uvicorn >/dev/null 2>&1; then
    UVICORN="$(command -v uvicorn)"
else
    echo "uvicorn nicht gefunden – erst src/backend/.venv einrichten (pip install -r requirements.txt)." >&2
    exit 1
fi

if [ "$MODUS" != "backend" ] && [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "src/frontend/node_modules fehlt – erst 'cd src/frontend && npm install' ausführen." >&2
    exit 1
fi

if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port $PORT ist schon belegt (läuft noch ein altes Backend?)." >&2
    exit 1
fi

# 32 Zufallsbytes hex – wie in Tauri (src-tauri/src/lib.rs)
if command -v openssl >/dev/null 2>&1; then
    RECHNUNGSFEE_TOKEN="$(openssl rand -hex 32)"
else
    RECHNUNGSFEE_TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
fi
export RECHNUNGSFEE_TOKEN

BACKEND_PID=""
aufraeumen() {
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "[dev-start] Backend wird beendet …"
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
}
trap aufraeumen EXIT
trap 'exit 130' INT TERM

echo "[dev-start] Backend startet auf Port $PORT (mit Sitzungstoken) …"
(cd "$BACKEND_DIR" && exec "$UVICORN" main:app --port "$PORT") &
BACKEND_PID=$!

# Warten bis das Backend antwortet (max. 60 s)
for _ in $(seq 1 120); do
    if curl -s -o /dev/null "http://127.0.0.1:$PORT/health"; then
        break
    fi
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "[dev-start] Backend ist beim Start abgestürzt." >&2
        exit 1
    fi
    sleep 0.5
done

echo "[dev-start] Backend bereit. Für curl-Tests in einer anderen Shell:"
echo "            export RECHNUNGSFEE_TOKEN=$RECHNUNGSFEE_TOKEN"
echo "            curl -H \"Authorization: Bearer \$RECHNUNGSFEE_TOKEN\" http://127.0.0.1:$PORT/api/setup/status"

case "$MODUS" in
    browser) (cd "$FRONTEND_DIR" && npm run dev) ;;
    tauri)   (cd "$REPO_ROOT" && npm run tauri:dev) ;;
    backend) echo "[dev-start] Nur Backend – Strg+C beendet."; wait "$BACKEND_PID" ;;
esac
