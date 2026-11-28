"""
Issue #596 (Punkt 5): Kopie per SMTP gesendeter Mails per IMAP im Ordner „Gesendet“ ablegen.
Opt-in (unternehmen.gesendet_imap_aktiv), Benutzer/Passwort vom Mailversand. Fehler bei der Ablage
brechen den bereits erfolgten Versand nie ab, sondern liefern einen Hinweis.
"""
import email
import imaplib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import main
import api.mail as mail_modul
from api.mail import TestMailRequest as _TestMailRequest
from database.connection import Base
from database.models import Unternehmen
from utils import gesendet_ablage
from utils.gesendet_ablage import gesendet_ordner, lege_gesendet_ab


def _imap(listen):
    m = MagicMock()
    m.list.return_value = ("OK", listen)
    m.append.return_value = ("OK", [b"APPEND completed"])
    return m


@pytest.mark.parametrize("listen,erwartet", [
    ([b'(\\HasNoChildren) "/" INBOX', b'(\\HasNoChildren \\Sent) "/" "Gesendete Elemente"'], "Gesendete Elemente"),
    ([b'(\\HasNoChildren) "." INBOX', b'(\\HasNoChildren) "." INBOX.Sent'], "INBOX.Sent"),
    ([b'(\\HasNoChildren) "/" INBOX', b'(\\HasNoChildren) "/" Gesendet'], "Gesendet"),
    ([b'(\\Noselect \\Sent) "/" Sent', b'(\\HasNoChildren) "/" INBOX'], None),
    ([b'(\\HasNoChildren) "/" INBOX', b'(\\HasNoChildren) "/" Entw&APw-rfe'], None),
])
def test_ordner_gesendet_finden(listen, erwartet):
    assert gesendet_ordner(_imap(listen)) == erwartet


def _u(**kw):
    return SimpleNamespace(gesendet_imap_host=kw.get("host", "imap.example.de"),
                           gesendet_imap_port=kw.get("port", 993))


def test_ablage_haengt_als_gelesen_an():
    m = _imap([b'(\\Sent) "/" Sent'])
    with patch.object(gesendet_ablage, "_verbinde", return_value=m):
        assert lege_gesendet_ab(_u(), b"Subject: x\r\n\r\nHallo", "user@example.de", "geheim") is None
    m.login.assert_called_once_with("user@example.de", "geheim")
    ordner, flags, _datum, nachricht = m.append.call_args.args
    assert ordner == '"Sent"' and flags == r"(\Seen)" and nachricht.endswith(b"Hallo")


def test_ohne_ordner_hinweis_statt_fehler():
    m = _imap([b'() "/" INBOX'])
    with patch.object(gesendet_ablage, "_verbinde", return_value=m):
        hinweis = lege_gesendet_ab(_u(), b"x", "u", "p")
    assert "nicht gefunden" in hinweis
    m.append.assert_not_called()


def test_anmeldung_scheitert_hinweis_statt_fehler():
    m = _imap([])
    m.login.side_effect = imaplib.IMAP4.error("AUTHENTICATIONFAILED")
    with patch.object(gesendet_ablage, "_verbinde", return_value=m):
        hinweis = lege_gesendet_ab(_u(), b"x", "u", "p")
    assert hinweis.startswith("Die Mail wurde gesendet") and "AUTHENTICATIONFAILED" in hinweis


def test_ohne_server_hinweis():
    assert "fehlt der IMAP-Server" in lege_gesendet_ab(_u(host=""), b"x", "u", "p")


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    s.add(Unternehmen(firmenname="Test GmbH", strasse="S", hausnummer="1", plz="12345", ort="O",
                      smtp_aktiv=True, smtp_host="smtp.example.de", smtp_port=587,
                      smtp_user="user@example.de", smtp_passwort="geheim"))
    s.commit()
    yield s
    s.close()


def test_testmail_legt_kopie_mit_datum_ab(db):
    u = db.query(Unternehmen).one()
    u.gesendet_imap_aktiv, u.gesendet_imap_host = True, "imap.example.de"
    db.commit()
    with patch("smtplib.SMTP"), patch("api.mail._smtp_passwort", return_value="geheim"), \
         patch("utils.gesendet_ablage.lege_gesendet_ab", return_value=None) as ablage:
        assert mail_modul.test_mail(_TestMailRequest(an="k@example.com"), db) == {"ok": True, "hinweis": None}
    _u, nachricht, user, passwort = ablage.call_args.args
    kopf = email.message_from_bytes(nachricht)
    assert kopf["Date"] and kopf["Message-ID"].endswith("@example.de>")
    assert (user, passwort) == ("user@example.de", "geheim")


def test_ohne_schalter_keine_ablage(db):
    with patch("smtplib.SMTP"), patch("api.mail._smtp_passwort", return_value="geheim"), \
         patch("utils.gesendet_ablage.lege_gesendet_ab") as ablage:
        assert mail_modul.test_mail(_TestMailRequest(an="k@example.com"), db)["hinweis"] is None
    ablage.assert_not_called()


def test_hinweis_kommt_im_ergebnis_an(db):
    u = db.query(Unternehmen).one()
    u.gesendet_imap_aktiv = True
    db.commit()
    with patch("smtplib.SMTP"), patch("api.mail._smtp_passwort", return_value="geheim"), \
         patch("utils.gesendet_ablage.lege_gesendet_ab", return_value="Kopie fehlt"):
        assert mail_modul.test_mail(_TestMailRequest(an="k@example.com"), db)["hinweis"] == "Kopie fehlt"


def test_migration_201(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.db'}")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as s:
        s.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="1", ort="O"))
        s.commit()
    with engine.begin() as conn:
        for spalte in ("gesendet_imap_aktiv", "gesendet_imap_host", "gesendet_imap_port"):
            conn.execute(text(f"ALTER TABLE unternehmen DROP COLUMN {spalte}"))
        conn.execute(text("PRAGMA user_version = 200"))
    monkeypatch.setattr(main, "engine", engine)
    main._run_migrations()
    with engine.begin() as conn:
        assert tuple(conn.execute(text(
            "SELECT gesendet_imap_aktiv, gesendet_imap_host, gesendet_imap_port FROM unternehmen")).one()) == (0, None, 993)
        conn.execute(text("PRAGMA user_version = 200"))
    main._run_migrations()  # zweiter Lauf ändert nichts
