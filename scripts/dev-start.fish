#!/usr/bin/env fish
# Dev-Start mit Sitzungstoken (Security-Audit F4 Teil 2) – fish-Variante von dev-start.sh.
#
# Erzeugt ein frisches Token, startet das Backend (Port 8002) und danach das Frontend –
# beide mit demselben RECHNUNGSFEE_TOKEN. Der Vite-Proxy hängt es als
# „Authorization: Bearer …“ an jeden API-Request an (vite.config.ts).
# Beim Beenden (Strg+C) wird das Backend mit beendet.
#
# Aufruf:
#   scripts/dev-start.fish            # Backend + Vite im Browser (http://localhost:5173)
#   scripts/dev-start.fish --tauri    # Backend + Tauri-Desktop-Fenster (npm run tauri:dev)
#   scripts/dev-start.fish --backend  # nur Backend (z. B. für curl-Tests)

set -l repo_root (realpath (dirname (status filename))/..)
set -l backend_dir $repo_root/src/backend
set -l frontend_dir $repo_root/src/frontend
set -l port 8002

set -l modus browser
switch "$argv[1]"
    case '' --browser
        set modus browser
    case --tauri
        set modus tauri
    case --backend
        set modus backend
    case -h --help
        sed -n 2,12p (status filename) | sed 's/^# \{0,1\}//'
        exit 0
    case '*'
        echo "Unbekannte Option: $argv[1] (--browser | --tauri | --backend)" >&2
        exit 1
end

# uvicorn aus der venv, sonst aus dem PATH
set -l uvicorn
if test -x $backend_dir/.venv/bin/uvicorn
    set uvicorn $backend_dir/.venv/bin/uvicorn
else if command -q uvicorn
    set uvicorn (command -s uvicorn)
else
    echo "uvicorn nicht gefunden – erst src/backend/.venv einrichten (pip install -r requirements.txt)." >&2
    exit 1
end

if test $modus != backend; and not test -d $frontend_dir/node_modules
    echo "src/frontend/node_modules fehlt – erst 'cd src/frontend && npm install' ausführen." >&2
    exit 1
end

if command -q lsof; and lsof -nP -iTCP:$port -sTCP:LISTEN >/dev/null 2>&1
    echo "Port $port ist schon belegt (läuft noch ein altes Backend?)." >&2
    exit 1
end

# 32 Zufallsbytes hex – wie in Tauri (src-tauri/src/lib.rs)
if command -q openssl
    set -gx RECHNUNGSFEE_TOKEN (openssl rand -hex 32)
else
    set -gx RECHNUNGSFEE_TOKEN (python3 -c 'import secrets; print(secrets.token_hex(32))')
end

echo "[dev-start] Backend startet auf Port $port (mit Sitzungstoken) …"
pushd $backend_dir
$uvicorn main:app --port $port &
set -g backend_pid $last_pid
popd

function __rf_aufraeumen --on-event fish_exit
    if set -q backend_pid; and kill -0 $backend_pid 2>/dev/null
        echo "[dev-start] Backend wird beendet …"
        kill $backend_pid 2>/dev/null
    end
end
function __rf_signal --on-signal INT --on-signal TERM
    exit 130
end

# Warten bis das Backend antwortet (max. 60 s)
for i in (seq 1 120)
    if curl -s -o /dev/null http://127.0.0.1:$port/health
        break
    end
    if not kill -0 $backend_pid 2>/dev/null
        echo "[dev-start] Backend ist beim Start abgestürzt." >&2
        exit 1
    end
    sleep 0.5
end

echo "[dev-start] Backend bereit. Für curl-Tests in einer anderen Shell:"
echo "            set -x RECHNUNGSFEE_TOKEN $RECHNUNGSFEE_TOKEN"
echo "            curl -H \"Authorization: Bearer \$RECHNUNGSFEE_TOKEN\" http://127.0.0.1:$port/api/setup/status"

switch $modus
    case browser
        cd $frontend_dir; and npm run dev
    case tauri
        cd $repo_root; and npm run tauri:dev
    case backend
        echo "[dev-start] Nur Backend – Strg+C beendet."
        wait $backend_pid
end
