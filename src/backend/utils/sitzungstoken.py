"""
Sitzungstoken zwischen Tauri, Frontend und Sidecar (Security-Audit F4 Teil 2, Schritt 1).

Tauri erzeugt bei jedem App-Start 32 Zufallsbytes, übergibt sie dem Sidecar über stdin
(`--token-stdin`) und dem Hauptfenster per IPC (`get_backend_token`). Jeder API-Request
muss das Token als `Authorization: Bearer <token>` mitschicken – sonst 401
(Prüfung in `utils/sicherheit_middleware.py`).

Bewusst kein JWT: es gibt genau einen Aussteller (Tauri) und einen Prüfer (dieses Backend),
keine Benutzer, keine Rollen, keine Claims. Ein reines Zufallstoken, das mit jedem Neustart
ungültig wird, ist einfacher und hat keine Algorithmus-/Bibliotheksfallen.

Übergabe über stdin statt über die Kommandozeile: `argv` ist unter Linux/macOS per `ps`
für alle Benutzer des Rechners sichtbar.

Entwicklungsmodus (`uvicorn main:app --port 8002`, nicht gebündelt): Token optional über
die Umgebungsvariable RECHNUNGSFEE_TOKEN (der Vite-Proxy schickt sie dann als Header mit).
Ohne Token bleibt die Prüfung im Entwicklungsmodus aus. Im ausgelieferten Sidecar
(`sys.frozen`) startet das Backend ohne Token gar nicht erst (siehe main.py).
"""
import hashlib
import hmac
import os
import re
import sys
import threading
import time
from urllib.parse import parse_qs

UMGEBUNGSVARIABLE = "RECHNUNGSFEE_TOKEN"

# 32 Byte hex = 64 Zeichen; etwas Spielraum für eigene Dev-Tokens, aber nichts Triviales.
_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]{32,256}")

_token: str | None = None


def ist_gebuendelt() -> bool:
    return bool(getattr(sys, "frozen", False))


def setze_token(token: str | None) -> None:
    global _token
    if token is not None and not _TOKEN_RE.fullmatch(token):
        raise ValueError("Ungültiges Sitzungstoken (32–256 Zeichen, nur A–Z, a–z, 0–9, _ und -).")
    _token = token


def aktuelles_token() -> str | None:
    return _token


def aus_umgebung() -> None:
    """Dev-Modus: Token aus RECHNUNGSFEE_TOKEN übernehmen, falls gesetzt."""
    wert = os.environ.get(UMGEBUNGSVARIABLE, "").strip()
    if wert:
        setze_token(wert)


def aus_stdin(timeout: float = 30.0) -> None:
    """Sidecar-Modus: eine Zeile von stdin lesen (schreibt Tauri direkt nach dem Start).

    Mit Timeout, damit ein Start ohne Tauri nicht ewig hängt.
    """
    zeilen: list[str] = []

    def _lesen():
        try:
            if sys.stdin is not None:
                zeilen.append(sys.stdin.readline())
        except Exception:
            pass

    t = threading.Thread(target=_lesen, daemon=True)
    t.start()
    t.join(timeout)
    wert = zeilen[0].strip() if zeilen else ""
    if wert:
        setze_token(wert)


def pruefung_aktiv() -> bool:
    return _token is not None


def authorization_gueltig(header: str | None) -> bool:
    """Prüft einen `Authorization`-Header (`Bearer <token>`) zeitkonstant."""
    if _token is None:
        return True
    if not header:
        return False
    art, _, wert = header.strip().partition(" ")
    if art.lower() != "bearer":
        return False
    return hmac.compare_digest(wert.strip().encode("utf-8"), _token.encode("utf-8"))


# ── Signierte Kurzzeit-Links (Security-Audit F4 Teil 2, Schritt 2) ─────────────────────────
# Eigene Fenster (PDF-WebviewWindow), <iframe> und <img> können keinen Authorization-Header
# setzen. Das Frontend holt sich deshalb für jede Datei-URL über POST /api/signierte-url
# (mit Token) eine Variante mit `exp` (Unix-Sekunden) und `sig`. Die Signatur bindet Pfad,
# Query und Ablaufzeit – aus einem Link für Rechnung 5 wird nie Rechnung 6.

LINK_GUELTIG_SEKUNDEN = 3600  # 1 h: unter Linux lädt „Speichern“ im PDF-Fenster die URL neu

_DATEI_MARKER_RE = re.compile(r"^(.+)/_datei/[^/]+$")


def _kanonisch(pfad: str, query: str) -> tuple[str, str]:
    """Pfad ohne kosmetischen `/_datei/<name>`-Anhang (Issue #476), Query ohne exp/sig."""
    m = _DATEI_MARKER_RE.match(pfad)
    if m:
        pfad = m.group(1)
    rest = "&".join(t for t in query.split("&") if t and not t.startswith(("exp=", "sig=")))
    return pfad, rest


def _signatur(pfad: str, query: str, exp: int) -> str:
    schluessel = hmac.new(_token.encode("utf-8"), b"rechnungsfee-link-v1", hashlib.sha256).digest()
    pfad, query = _kanonisch(pfad, query)
    nachricht = f"GET\n{pfad}\n{query}\n{exp}".encode("utf-8")
    return hmac.new(schluessel, nachricht, hashlib.sha256).hexdigest()


def signiere(pfad: str, query: str = "", gueltig: int = LINK_GUELTIG_SEKUNDEN) -> str:
    """Hängt `exp` und `sig` an eine Adresse (Pfad dekodiert, Query roh). Ohne Token unverändert."""
    if _token is None:
        return pfad + ("?" + query if query else "")
    exp = int(time.time()) + gueltig
    extra = f"exp={exp}&sig={_signatur(pfad, query, exp)}"
    return f"{pfad}?{query}&{extra}" if query else f"{pfad}?{extra}"


def link_gueltig(pfad: str, query: str) -> bool:
    """Prüft `exp`/`sig` eines eingehenden GET/HEAD (Query roh, Pfad dekodiert)."""
    if _token is None:
        return True
    q = parse_qs(query, keep_blank_values=True)
    try:
        exp = int(q["exp"][0])
        sig = q["sig"][0]
    except (KeyError, ValueError, IndexError):
        return False
    if exp < time.time():
        return False
    return hmac.compare_digest(sig.encode("utf-8"), _signatur(pfad, query, exp).encode("utf-8"))
