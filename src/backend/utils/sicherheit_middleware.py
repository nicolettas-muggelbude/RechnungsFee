"""
Sicherheits-Middleware für die lokale API (Security-Audit lindesbs, 2026-11-07).

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

F4 Teil 2, Schritt 1 – Sitzungstoken: jeder Request braucht „Authorization: Bearer <token>“
  (pro App-Start von Tauri erzeugt, siehe utils/sitzungstoken.py), sonst 401. Ausnahmen:
  CORS-Preflight (OPTIONS trägt keinen Header) und – als Übergang bis zu den signierten
  Kurzzeit-Links (Schritt 2) – lesende Abrufe der Datei-Endpunkte, die das Frontend in einem
  eigenen Fenster, iframe oder <img> öffnet (`_FENSTER_PFADE`). Dort kann kein Header gesetzt
  werden. Alle JSON-Endpunkte und alle schreibenden Requests sind geschützt.

Reine ASGI-Middleware (kein BaseHTTPMiddleware), damit Streaming-Antworten unverändert
durchlaufen.
"""
import re
from urllib.parse import urlsplit

from utils import sitzungstoken

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


# Übergang bis Schritt 2 (signierte Links): GET/HEAD-Pfade, die ohne eigenen Header geladen
# werden (WebviewWindow per openUrl()/openInPdfWindow(), iframe in pdf-ansehen, <img> fürs Logo).
# Neue Datei-Endpunkte, die im Fenster geöffnet werden, hier ergänzen – sonst 401 im Fenster.
_FENSTER_PFADE = re.compile(r"""^/api/(?:
      rechnungen/\d+/(?:pdf|pdf-ansehen|beleg|zugferd)
    | rechnungen/temp/[0-9a-f\-]{36}
    | rechnungen/export
    | mahnwesen/\d+/pdf
    | (?:kunden|lieferanten)/\d+/(?:kontokorrent/pdf|dsgvo-export|dsgvo-export-pdf)
    | kunden/\d+/belege/\d+/download
    | dokumentenpakete/\d+/(?:vorschau|dateien/\d+/download)
    | journal/\d+/(?:beleg|anhang)
    | journal/(?:export|kassenbuch-export)
    | (?:inventurliste|kontenuebersicht)/export
    | (?:kategorien|tagesabschluss)/export/pdf
    | (?:anlage-g|anlage-s|anlageverzeichnis|euer|ustva|eks)/pdf
    | ustva/jahreserklarung/pdf
    | eks/halbjahr/pdf
    | pdf-vorlagen/demo
    | postfach/eingang/\d+/datei
    | unternehmen/logo
)$""", re.X)

# Angehängter Dateiname (Issue #476, PdfDateinameMiddleware läuft erst danach).
_DATEI_MARKER_RE = re.compile(r"^(.+)/_datei/[^/]+$")

_OHNE_TOKEN = {"/health"}


def ohne_token_erlaubt(methode: str, pfad: str) -> bool:
    """True, wenn der Request (Übergangsregel) auch ohne Sitzungstoken durch darf."""
    if methode == "OPTIONS":
        return True
    if methode not in ("GET", "HEAD"):
        return False
    m = _DATEI_MARKER_RE.match(pfad)
    if m:
        pfad = m.group(1)
    return pfad in _OHNE_TOKEN or bool(_FENSTER_PFADE.match(pfad))


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

        if (
            sitzungstoken.pruefung_aktiv()
            and not ohne_token_erlaubt(scope.get("method", "GET"), scope.get("path", ""))
            and not sitzungstoken.authorization_gueltig(headers.get("authorization"))
        ):
            await _abweisen(send, 401, "Sitzungstoken fehlt oder ist ungültig.")
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
