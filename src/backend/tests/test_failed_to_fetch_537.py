"""
Issue #537: SMTP-Testmail/Versand endete mit „Failed to fetch“, ohne Eintrag in backend.log.

Ursache: eine nicht abgefangene Ausnahme (UnicodeEncodeError bei unsichtbaren Zeichen in der
Absenderadresse bzw. Umlaut/€ im Passwort) → 500 ohne CORS-Header, Traceback nur auf stderr.
Nebenfund: Kontokorrent-Mail an Kunden/Lieferanten rief _sende() seit #336 ohne db auf (TypeError).
"""
import asyncio
import base64
import json
import logging
import smtplib

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import api.mail as mail_mod
from api.schemas import UnternehmenBase
from database.models import Unternehmen
from utils.fehler_middleware import FehlerMiddleware
from utils.mailfelder import bereinige_mailfeld


# ── Fehler-Middleware ─────────────────────────────────────────────────────────

def _app():
    app = FastAPI()
    app.add_middleware(FehlerMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=["http://tauri.localhost"],
                       allow_methods=["*"], allow_headers=["*"])

    @app.post("/crash")
    def crash():
        "ä".encode("ascii")

    @app.post("/bekannt")
    def bekannt():
        raise HTTPException(400, "verständlich")

    return app


def _aufruf(app, pfad):
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST",
             "path": pfad, "raw_path": pfad.encode(), "query_string": b"", "root_path": "",
             "headers": [(b"origin", b"http://tauri.localhost"), (b"host", b"127.0.0.1")],
             "client": ("127.0.0.1", 1), "server": ("127.0.0.1", 8002), "scheme": "http"}
    nachrichten = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(m):
        nachrichten.append(m)

    asyncio.run(app(scope, receive, send))
    start = next(m for m in nachrichten if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in nachrichten if m["type"] == "http.response.body")
    return start["status"], dict(start["headers"]), body


def test_unbehandelter_fehler_mit_cors_und_lesbarer_meldung(caplog):
    with caplog.at_level(logging.ERROR, logger="rechnungsfee.fehler"):
        status, header, body = _aufruf(_app(), "/crash")
    assert status == 500
    assert header.get(b"access-control-allow-origin") == b"http://tauri.localhost"
    detail = json.loads(body)["detail"]
    assert "UnicodeEncodeError" in detail and "backend.log" in detail
    # Traceback landet im Root-Logging (→ backend.log)
    assert any(r.exc_info for r in caplog.records)


def test_bekannte_fehler_unveraendert():
    status, header, body = _aufruf(_app(), "/bekannt")
    assert status == 400
    assert json.loads(body)["detail"] == "verständlich"


def test_middleware_liegt_innerhalb_von_cors():
    from main import app
    namen = [m.cls.__name__ for m in app.user_middleware]
    # user_middleware: Index 0 = äußerste Schicht
    assert namen.index("FehlerMiddleware") > namen.index("CORSMiddleware")


# ── Bereinigung der Zugangsdaten ──────────────────────────────────────────────

def test_unsichtbare_zeichen_entfernt():
    assert bereinige_mailfeld("​info@firma.de ") == "info@firma.de"
    assert bereinige_mailfeld(None) is None


def test_schema_bereinigt_smtp_felder_aber_nicht_passwort():
    validator = UnternehmenBase.__pydantic_decorators__.field_validators["bereinige_mailzugang"]
    assert set(validator.info.fields) == {"smtp_host", "smtp_user", "smtp_von_adresse", "imap_host", "imap_user"}
    assert UnternehmenBase.bereinige_mailzugang("info@firma.de ") == "info@firma.de"


def test_build_message_mit_altwert_nbsp_funktioniert():
    u = Unternehmen(firmenname="Noël Testfirma", smtp_von_adresse="info@firma.de ")
    msg = mail_mod._build_message(u, "a@b.de", None, "Test – ä", "Hallo", [])
    assert "info@firma.de" in msg["From"]
    msg.as_string().encode("ascii")


def test_build_message_umlaut_adresse_verstaendlich():
    u = Unternehmen(firmenname="F", smtp_von_adresse="info@müller.de")
    with pytest.raises(HTTPException) as e:
        mail_mod._build_message(u, "a@b.de", None, "T", "x", [])
    assert e.value.status_code == 400 and "Absenderadresse" in e.value.detail


def test_umlaut_im_smtp_benutzer_verstaendlich():
    u = Unternehmen(smtp_host="smtp.firma.de", smtp_user="müller@firma.de", smtp_passwort="x")
    with pytest.raises(HTTPException) as e:
        mail_mod._sende(u, mail_mod._build_message(Unternehmen(smtp_von_adresse="a@b.de"), "a@b.de", None, "T", "x", []),
                        ["a@b.de"], None)
    assert e.value.status_code == 400 and "SMTP-Benutzer" in e.value.detail


# ── Passwort mit Sonderzeichen ────────────────────────────────────────────────

class _FakeSMTP:
    def __init__(self, code=235):
        self.code = code
        self.befehle = []

    def login(self, user, pw):
        f"\0{user}\0{pw}".encode("ascii")  # wie smtplib

    def ehlo_or_helo_if_needed(self):
        pass

    def has_extn(self, name):
        return name == "auth"

    def docmd(self, cmd, arg):
        self.befehle.append((cmd, arg))
        return self.code, b"ok"


def test_passwort_mit_umlaut_per_utf8_auth_plain():
    srv = _FakeSMTP()
    mail_mod._smtp_login(srv, "info@firma.de", "Pässwort€§")
    cmd, arg = srv.befehle[0]
    assert cmd == "AUTH" and arg.startswith("PLAIN ")
    assert base64.b64decode(arg[6:]).decode("utf-8") == "\0info@firma.de\0Pässwort€§"


def test_passwort_ascii_normaler_login_ohne_fallback():
    srv = _FakeSMTP()
    mail_mod._smtp_login(srv, "info@firma.de", "geheim")
    assert srv.befehle == []


def test_utf8_passwort_abgelehnt_wird_auth_fehler():
    with pytest.raises(smtplib.SMTPAuthenticationError):
        mail_mod._smtp_login(_FakeSMTP(code=535), "info@firma.de", "Pässwort")


# ── Nebenfund: Kontokorrent-Mail ──────────────────────────────────────────────

@pytest.mark.parametrize("modul,funktion", [("api.kunden", "kontokorrent_mail"),
                                            ("api.lieferanten", "kontokorrent_mail_lieferant")])
def test_kontokorrent_mail_uebergibt_db(modul, funktion):
    import importlib
    import inspect
    quelle = inspect.getsource(getattr(importlib.import_module(modul), funktion))
    assert "_sende(unt, msg, empfaenger, db)" in quelle
