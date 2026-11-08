"""
Sicherheits-Middleware für die lokale API (Security-Audit Stefan Lindecke, 2026-11-07).

F4 Teil 1 – Host-Prüfung gegen DNS-Rebinding: Eine Angreifer-Domain, die per DNS plötzlich
  auf 127.0.0.1 zeigt, gilt im Browser als „gleicher Ursprung“ und könnte alle Antworten
  lesen – CORS greift dann nicht. Der Host-Header verrät sie aber: nur 127.0.0.1/localhost.
F7 Teil 1 – Origin-Prüfung: Formular-, text/plain- und Multipart-POSTs fremder Webseiten
  laufen ohne CORS-Preflight bis zum Endpunkt durch (CORS verhindert nur das Lesen der
  Antwort). Schreibende Requests mit fremdem Origin werden deshalb abgewiesen. Requests ganz
  ohne Origin (eigene Fenster per GET, Skripte, Tests) bleiben erlaubt.
F2 – Datei-Antworten: „X-Content-Type-Options: nosniff“ überall; Antworten, die weder JSON,
  HTML noch PDF sind (XML, Bilder, Office-Dateien, CSV …), zusätzlich mit
  „Content-Security-Policy: sandbox“ – fremde Inhalte dürfen im API-Ursprung kein Skript
  ausführen. PDF bewusst ohne sandbox (blockiert in manchen Engines den PDF-Viewer),
  HTML setzt seine CSP selbst (Journal-Beleg) bzw. ist eigener Code (PDF-Ansichtshülle).

Reine ASGI-Middleware (kein BaseHTTPMiddleware), damit Streaming-Antworten unverändert
durchlaufen.
"""
from urllib.parse import urlsplit

ERLAUBTE_HOSTS = {"127.0.0.1", "localhost", "[::1]"}

# Eigene Oberflächen: Tauri (macOS/Linux), Tauri unter Windows (WebView2), Vite-Dev-Server
# sowie Seiten, die die API selbst ausliefert (PDF-Ansicht) – jeweils nur auf localhost.
_ERLAUBTE_ORIGINS = {"tauri://localhost", "http://tauri.localhost", "https://tauri.localhost"}

_LESEND = {"GET", "HEAD", "OPTIONS"}

_OHNE_SANDBOX = ("application/json", "text/html", "application/pdf")

# F10: Größenlimit per Content-Length (Uploads werden per await datei.read() komplett in den
# Speicher gelesen). Großzügig, damit echte Belege/Backups nie scheitern.
MAX_UPLOAD = 500 * 1024 ** 2                    # 500 MB
MAX_UPLOAD_BACKUP = 10 * 1024 ** 3              # 10 GB – wie das Entpack-Limit beim Restore
_BACKUP_PFADE = ("/api/backup/wiederherstellen",)


def _hostname(host_header: str) -> str:
    """Hostname ohne Port; IPv6-Literal behält die Klammern."""
    host = host_header.strip().lower()
    if host.startswith("["):
        return host.split("]", 1)[0] + "]"
    return host.rsplit(":", 1)[0] if ":" in host else host


def origin_erlaubt(origin: str) -> bool:
    origin = origin.strip().lower()
    if origin in _ERLAUBTE_ORIGINS:
        return True
    try:
        teile = urlsplit(origin)
    except ValueError:
        return False
    if teile.scheme not in ("http", "https"):
        return False
    host = teile.hostname or ""
    return host in ("127.0.0.1", "localhost", "::1")


async def _abweisen(send, status: int, text: str) -> None:
    body = text.encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            (b"content-type", b"text/plain; charset=utf-8"),
            (b"content-length", str(len(body)).encode()),
            (b"x-content-type-options", b"nosniff"),
        ],
    })
    await send({"type": "http.response.body", "body": body})


class SicherheitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}

        if _hostname(headers.get("host", "")) not in ERLAUBTE_HOSTS:
            await _abweisen(send, 421, "Unzulässiger Host-Header.")
            return

        origin = headers.get("origin")
        if scope.get("method", "GET") not in _LESEND and origin is not None and not origin_erlaubt(origin):
            await _abweisen(send, 403, "Anfrage von fremder Herkunft abgelehnt.")
            return

        laenge = headers.get("content-length", "")
        if laenge.isdigit():
            grenze = MAX_UPLOAD_BACKUP if scope.get("path", "").startswith(_BACKUP_PFADE) else MAX_UPLOAD
            if int(laenge) > grenze:
                await _abweisen(send, 413, "Datei zu groß.")
                return

        async def send_mit_headern(message):
            if message["type"] == "http.response.start":
                vorhanden = {k.lower() for k, _ in message.get("headers", [])}
                neu = list(message.get("headers", []))
                if b"x-content-type-options" not in vorhanden:
                    neu.append((b"x-content-type-options", b"nosniff"))
                content_type = next(
                    (v.decode("latin-1").lower() for k, v in neu if k.lower() == b"content-type"), ""
                )
                if (
                    content_type
                    and not content_type.startswith(_OHNE_SANDBOX)
                    and b"content-security-policy" not in vorhanden
                ):
                    neu.append((b"content-security-policy", b"sandbox"))
                message = dict(message, headers=neu)
            await send(message)

        await self.app(scope, receive, send_mit_headern)
