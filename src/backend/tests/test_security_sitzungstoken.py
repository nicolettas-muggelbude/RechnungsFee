"""
Regressionstests Security-Audit F4 Teil 2, Schritt 1 – Sitzungstoken (utils/sitzungstoken.py,
Prüfung in utils/sicherheit_middleware.py).

Vorher: Jeder lokale Prozess und jeder andere Benutzer des Rechners konnte mit einem simplen
`curl http://127.0.0.1:<port>/api/unternehmen` alle Daten samt Zugangsdaten lesen, Buchungen
anlegen oder ein Backup einspielen. Jetzt: ohne gültiges `Authorization: Bearer <token>` 401 –
außer CORS-Preflight und (Übergang bis Schritt 2) lesenden Abrufen der Datei-Endpunkte, die im
eigenen Fenster geöffnet werden.
"""
import asyncio
import io
import re

import pytest

import main
from utils import sitzungstoken
from utils.sicherheit_middleware import SicherheitMiddleware, _FENSTER_PFADE, ohne_token_erlaubt

TOKEN = "a" * 32 + "0123456789abcdef0123456789abcdef"


@pytest.fixture
def mit_token():
    vorher = sitzungstoken.aktuelles_token()
    sitzungstoken.setze_token(TOKEN)
    yield
    sitzungstoken.setze_token(vorher)


def _rufe(method="GET", path="/api/unternehmen", authorization=None):
    aufgerufen = []

    async def app(scope, receive, send):
        aufgerufen.append(True)
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": b"{}"})

    headers = [(b"host", b"127.0.0.1:18765")]
    if authorization is not None:
        headers.append((b"authorization", authorization.encode()))
    scope = {"type": "http", "method": method, "path": path, "headers": headers}
    nachrichten = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(msg):
        nachrichten.append(msg)

    asyncio.run(SicherheitMiddleware(app)(scope, receive, send))
    return nachrichten[0]["status"], bool(aufgerufen)


# ── Prüfung in der Middleware ─────────────────────────────────────────────────

@pytest.mark.parametrize("method,path", [
    ("GET", "/api/unternehmen"),          # enthielt SMTP-/IMAP-Passwörter
    ("POST", "/api/shutdown"),
    ("POST", "/api/backup/wiederherstellen"),
    ("PUT", "/api/unternehmen"),
    ("DELETE", "/api/journal/1/anhang"),
    ("POST", "/api/rechnungen/1/pdf"),    # Fenster-Pfad, aber nicht lesend
])
def test_ohne_token_abgewiesen(mit_token, method, path):
    status, aufgerufen = _rufe(method, path)
    assert status == 401
    assert not aufgerufen


@pytest.mark.parametrize("authorization", [
    "Bearer falsch-falsch-falsch-falsch-falsch-falsch",
    f"Bearer {TOKEN}x",
    f"Basic {TOKEN}",
    TOKEN,
    "Bearer ",
    "",
])
def test_falsches_token_abgewiesen(mit_token, authorization):
    status, aufgerufen = _rufe(authorization=authorization)
    assert status == 401
    assert not aufgerufen


@pytest.mark.parametrize("authorization", [f"Bearer {TOKEN}", f"bearer {TOKEN}", f"  Bearer   {TOKEN} "])
def test_richtiges_token_durchgelassen(mit_token, authorization):
    status, aufgerufen = _rufe("POST", "/api/shutdown", authorization=authorization)
    assert status == 200 and aufgerufen


def test_preflight_ohne_token(mit_token):
    status, aufgerufen = _rufe("OPTIONS", "/api/unternehmen")
    assert status == 200 and aufgerufen


@pytest.mark.parametrize("path", [
    "/api/rechnungen/12/pdf",
    "/api/rechnungen/12/pdf/_datei/Rechnung_RE-260035.pdf",   # Issue #476
    "/api/rechnungen/12/pdf-ansehen",
    "/api/rechnungen/temp/0b6e3c3a-2c55-4c43-9a0f-7d1c1b9a7f10",
    "/api/journal/5/beleg",
    "/api/unternehmen/logo",
    "/api/euer/pdf",
    "/health",
])
def test_fensterpfade_lesend_ohne_token(mit_token, path):
    for method in ("GET", "HEAD"):
        status, aufgerufen = _rufe(method, path)
        assert status == 200 and aufgerufen, (method, path)


@pytest.mark.parametrize("path", [
    "/api/rechnungen/12",
    "/api/rechnungen/12/pdfx",
    "/api/rechnungen/abc/pdf",
    "/api/rechnungen/temp/../../unternehmen",
    "/api/unternehmen/logo/../",
    "/api/kunden",
    "/api/backup/download",
    "/api/export/gobd",
    "/api/euer/pdf/extra",
])
def test_kein_fensterpfad(path):
    assert not ohne_token_erlaubt("GET", path)


def test_ohne_token_im_dev_modus_offen():
    vorher = sitzungstoken.aktuelles_token()
    sitzungstoken.setze_token(None)
    try:
        status, aufgerufen = _rufe("GET", "/api/unternehmen")
        assert status == 200 and aufgerufen
    finally:
        sitzungstoken.setze_token(vorher)


# ── Fenster-Pfade passen zu echten Routen ──────────────────────────────────────

def test_fensterpfade_existieren_als_get_routen():
    """Jede Alternative in _FENSTER_PFADE muss mindestens eine echte GET-Route treffen –
    schützt vor Tippfehlern, durch die ein PDF-Fenster plötzlich 401 zeigt."""
    get_pfade = [p for p, m in main.app.openapi()["paths"].items() if "get" in m]
    beispiele = [re.sub(r"\{token\}", "0b6e3c3a-2c55-4c43-9a0f-7d1c1b9a7f10",
                        re.sub(r"\{[a-z_]*id\}", "1", p)) for p in get_pfade]
    # Jede Zeile des Musters ist eine Alternative und muss mindestens eine Route treffen
    zeilen = [z.strip().lstrip("|").strip() for z in _FENSTER_PFADE.pattern.splitlines()[1:-1]]
    assert len(zeilen) > 10
    for zeile in zeilen:
        teil = re.compile(rf"^/api/(?:{zeile})$")
        assert any(teil.match(b) for b in beispiele), f"keine Route für {zeile!r}"


# ── Token-Übergabe ────────────────────────────────────────────────────────────

def test_token_aus_stdin(monkeypatch):
    vorher = sitzungstoken.aktuelles_token()
    monkeypatch.setattr("sys.stdin", io.StringIO(TOKEN + "\n"))
    try:
        sitzungstoken.aus_stdin(timeout=2)
        assert sitzungstoken.aktuelles_token() == TOKEN
    finally:
        sitzungstoken.setze_token(vorher)


def test_token_aus_umgebung(monkeypatch):
    vorher = sitzungstoken.aktuelles_token()
    monkeypatch.setenv(sitzungstoken.UMGEBUNGSVARIABLE, TOKEN)
    try:
        sitzungstoken.aus_umgebung()
        assert sitzungstoken.aktuelles_token() == TOKEN
    finally:
        sitzungstoken.setze_token(vorher)


@pytest.mark.parametrize("wert", ["kurz", "a" * 31, "a" * 40 + " b", "a" * 40 + "\n", "ä" * 40])
def test_ungueltiges_token_abgelehnt(wert):
    with pytest.raises(ValueError):
        sitzungstoken.setze_token(wert)
