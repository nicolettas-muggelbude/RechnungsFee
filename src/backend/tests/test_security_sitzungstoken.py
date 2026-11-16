"""
Regressionstests Security-Audit F4 Teil 2, Schritt 1 – Sitzungstoken (utils/sitzungstoken.py,
Prüfung in utils/sicherheit_middleware.py).

Vorher: Jeder lokale Prozess und jeder andere Benutzer des Rechners konnte mit einem simplen
`curl http://127.0.0.1:<port>/api/unternehmen` alle Daten samt Zugangsdaten lesen, Buchungen
anlegen oder ein Backup einspielen. Jetzt: ohne gültiges `Authorization: Bearer <token>` 401 –
außer CORS-Preflight und lesenden Abrufen mit gültigem signiertem Kurzzeit-Link (Schritt 2, für
Fenster/iframe/<img>, die keinen Header senden können).
"""
import asyncio
import io
import time

import pytest

import main
from utils import sitzungstoken
from utils.sicherheit_middleware import SicherheitMiddleware

TOKEN = "a" * 32 + "0123456789abcdef0123456789abcdef"


@pytest.fixture
def mit_token():
    vorher = sitzungstoken.aktuelles_token()
    sitzungstoken.setze_token(TOKEN)
    yield
    sitzungstoken.setze_token(vorher)


def _rufe(method="GET", path="/api/unternehmen", authorization=None, query=""):
    aufgerufen = []

    async def app(scope, receive, send):
        aufgerufen.append(True)
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": b"{}"})

    headers = [(b"host", b"127.0.0.1:18765")]
    if authorization is not None:
        headers.append((b"authorization", authorization.encode()))
    scope = {"type": "http", "method": method, "path": path, "headers": headers,
             "query_string": query.encode()}
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


def test_health_braucht_token(mit_token):
    status, aufgerufen = _rufe("GET", "/health")
    assert status == 401 and not aufgerufen


# ── Signierte Kurzzeit-Links (Schritt 2) ───────────────────────────────────────

def _link(pfad, query="", **kw):
    """(Pfad, Query) eines signierten Links, wie ihn der Browser an die Middleware schickt."""
    voll = sitzungstoken.signiere(pfad, query, **kw)
    p, _, q = voll.partition("?")
    return p, q


@pytest.mark.parametrize("pfad,query", [
    ("/api/rechnungen/12/pdf", ""),
    ("/api/rechnungen/12/pdf", "nur_ansehen=true"),
    ("/api/unternehmen/logo", "v=1700000000"),
])
def test_signierter_link_ohne_token(mit_token, pfad, query):
    p, q = _link(pfad, query)
    for method in ("GET", "HEAD"):
        status, aufgerufen = _rufe(method, p, query=q)
        assert status == 200 and aufgerufen


def test_signierter_link_mit_dateiname_segment(mit_token):
    p, q = _link("/api/rechnungen/12/pdf", "nur_ansehen=true")
    status, _ = _rufe("GET", p + "/_datei/Rechnung_RE-1.pdf", query=q)
    assert status == 200


def test_link_abgelaufen(mit_token):
    p, q = _link("/api/rechnungen/12/pdf", gueltig=-1)
    assert _rufe("GET", p, query=q)[0] == 401


def test_link_nicht_uebertragbar(mit_token):
    p, q = _link("/api/rechnungen/12/pdf", "nur_ansehen=true")
    assert _rufe("GET", "/api/rechnungen/13/pdf", query=q)[0] == 401      # anderer Pfad
    assert _rufe("GET", p, query=q.replace("nur_ansehen=true&", ""))[0] == 401  # Query entfernt
    assert _rufe("GET", p, query="nur_ansehen=false&" + q.split("&", 1)[1])[0] == 401
    assert _rufe("POST", p, query=q)[0] == 401                            # nur lesend


def test_link_manipuliert(mit_token):
    p, q = _link("/api/rechnungen/12/pdf")
    exp = int(q.split("&")[0].split("=")[1])
    assert _rufe("GET", p, query=q.replace("exp=%d" % exp, "exp=%d" % (exp + 999)))[0] == 401
    assert _rufe("GET", p, query=q[:-1] + ("0" if q[-1] != "0" else "1"))[0] == 401
    assert _rufe("GET", p, query="exp=%d" % exp)[0] == 401
    assert _rufe("GET", p, query="exp=abc&sig=x")[0] == 401


def test_link_mit_anderem_token_ungueltig(mit_token):
    p, q = _link("/api/rechnungen/12/pdf")
    sitzungstoken.setze_token("b" * 40)
    assert _rufe("GET", p, query=q)[0] == 401


def test_signiere_ohne_token_unveraendert():
    vorher = sitzungstoken.aktuelles_token()
    sitzungstoken.setze_token(None)
    try:
        assert sitzungstoken.signiere("/api/x", "a=1") == "/api/x?a=1"
    finally:
        sitzungstoken.setze_token(vorher)


# ── Endpunkt POST /api/signierte-url ───────────────────────────────────────────

def test_endpunkt_signiert_und_link_funktioniert(mit_token):
    from fastapi.testclient import TestClient
    c = TestClient(main.app, base_url="http://127.0.0.1:18765")
    kopf = {"Authorization": f"Bearer {TOKEN}"}
    url = "http://127.0.0.1:18765/api/rechnungen/12/pdf/_datei/Rechnung%20%C3%9C.pdf?nur_ansehen=true#x"
    assert c.post("/api/signierte-url", json={"url": url}).status_code == 401
    r = c.post("/api/signierte-url", json={"url": url}, headers=kopf)
    assert r.status_code == 200
    signiert = r.json()["url"]
    assert signiert.startswith("http://127.0.0.1:18765/api/rechnungen/12/pdf/_datei/Rechnung%20%C3%9C.pdf?nur_ansehen=true&exp=")
    # Der signierte Link besteht die Prüfung ohne Header (Route selbst darf 404 liefern – kein 401)
    assert c.get(signiert.replace("http://127.0.0.1:18765", "")).status_code != 401
    assert c.get(signiert.replace("/12/", "/13/").replace("http://127.0.0.1:18765", "")).status_code == 401


@pytest.mark.parametrize("url", [
    "http://attacker.example/api/rechnungen/1/pdf",
    "/api/../etc/passwd",
    "/api/signierte-url",
    "/nicht-api/x",
])
def test_endpunkt_lehnt_ab(mit_token, url):
    from fastapi.testclient import TestClient
    c = TestClient(main.app, base_url="http://127.0.0.1:18765")
    r = c.post("/api/signierte-url", json={"url": url}, headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 422


def test_pdf_ansehen_huelle_signiert_iframe(mit_token):
    from api.rechnungen import rechnung_pdf_ansehen_wrapper
    from types import SimpleNamespace
    r = SimpleNamespace(rechnungsnummer="RE-1")
    db = SimpleNamespace(query=lambda *_: SimpleNamespace(filter=lambda *_: SimpleNamespace(first=lambda: r)))
    html = rechnung_pdf_ansehen_wrapper(12, db).body.decode()
    assert "nur_ansehen=true&amp;exp=" in html and "&amp;sig=" in html


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
