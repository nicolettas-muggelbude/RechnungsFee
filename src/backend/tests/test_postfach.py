"""
Issue #451, Stufe 1: Rechnungspostfach per IMAP.

Abruf legt PDF-/XML-Anhänge in die Importliste, verändert das Postfach aber nicht. Erst beim
Übernehmen wandert die Mail nach "RechnungsFee/verarbeitet" (bei mehreren Anhängen, sobald keiner
mehr offen ist); nur verworfene Mails bleiben im Posteingang. Geprüft werden nur Mails seit dem
letzten Abruf. Der IMAP-Server ist hier nachgebaut (keine Netzwerkverbindung).
"""
import hashlib
import re
from email.message import EmailMessage
from email import message_from_bytes

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api.postfach as postfach
from database.connection import Base
from database.models import Beleg, PostfachEingang, Unternehmen

PDF = b"%PDF-1.4\n% Testrechnung\n%%EOF\n"
XML = b"<?xml version='1.0'?><Invoice>Test</Invoice>"
ZIEL = "RechnungsFee/verarbeitet"


def _mail(betreff: str, anhaenge: list[tuple[str, str, bytes]], message_id: str | None = None) -> bytes:
    msg = EmailMessage()
    msg["From"] = "Lieferant <rechnung@lieferant.example>"
    msg["To"] = "rechnungen@firma.example"
    msg["Subject"] = betreff
    msg["Date"] = "Sat, 17 Oct 2026 10:00:00 +0200"
    msg["Message-ID"] = message_id or f"<{abs(hash(betreff))}@lieferant.example>"
    msg.set_content("Anbei die Rechnung.")
    for name, mime, inhalt in anhaenge:
        haupt, unter = mime.split("/")
        msg.add_attachment(inhalt, maintype=haupt, subtype=unter, filename=name)
    return msg.as_bytes()


def _bodystructure(roh: bytes) -> str:
    teile = []
    for teil in message_from_bytes(roh).walk():
        if teil.is_multipart():
            continue
        name = teil.get_filename()
        teile.append(f'("{teil.get_content_maintype().upper()}" "{teil.get_content_subtype().upper()}"'
                     + (f' ("NAME" "{name}")' if name else "") + ")")
    return "(" + " ".join(teile) + ' "MIXED")'


class FakeImap:
    """Minimaler IMAP-Server mit UIDs, UIDVALIDITY, BODYSTRUCTURE, MOVE/COPY und Namensraum."""

    def __init__(self, mails: dict[str, bytes], move: bool = True, uidplus: bool = True,
                 namespace: bytes | None = None, caps_erst_nach_login: bool = False):
        self.ordner = {"INBOX": dict(mails)}
        self.uidvalidity = {"INBOX": "4711"}
        self._caps_voll = ("IMAP4REV1",) + (("MOVE",) if move else ()) + (("UIDPLUS",) if uidplus else ()) \
            + (("NAMESPACE",) if namespace else ())
        self.capabilities = ("IMAP4REV1",) if caps_erst_nach_login else self._caps_voll
        self._namespace = namespace
        self.aktuell = None
        self.geloescht_markiert: set[str] = set()
        self.voll_geladen: list[str] = []

    def __call__(self, *args, **kwargs):
        return self

    def login(self, user, pw):
        if pw != "geheim":
            raise postfach.imaplib.IMAP4.error(b"[AUTHENTICATIONFAILED] Invalid credentials")

    def capability(self):
        return "OK", [" ".join(self._caps_voll).encode()]

    def namespace(self):
        if self._namespace is None:
            return "BAD", [b"Unknown command"]
        return "OK", [self._namespace]

    def select(self, name, readonly=False):
        name = name.strip('"')
        if name not in self.ordner:
            return "NO", [b"no such folder"]
        self.aktuell = name
        return "OK", [str(len(self.ordner[name])).encode()]

    def response(self, code):
        return code, [self.uidvalidity.get(self.aktuell, "1").encode()]

    def list(self, *a):
        if a == ('""', '""'):
            return "OK", [b'(\\Noselect) "/" ""']
        return "OK", [f'(\\HasNoChildren) "." "{n}"'.encode() for n in self.ordner] + [b'(\\Noselect) "." "Shared"']

    def create(self, name):
        self.ordner.setdefault(name.strip('"'), {})
        return "OK", [b""]

    def subscribe(self, name):
        return "OK", [b""]

    def logout(self):
        pass

    def uid(self, befehl, *args):
        befehl = befehl.upper()
        box = self.ordner[self.aktuell]
        if befehl == "SEARCH":
            if "HEADER" in args:
                gesucht = args[-1].strip('"')
                treffer = [u for u, roh in box.items() if f"Message-ID: {gesucht}".encode() in roh]
                return "OK", [" ".join(treffer).encode()]
            return "OK", [" ".join(sorted(box, key=int)).encode()]
        menge = args[0].decode() if isinstance(args[0], bytes) else args[0]
        if befehl == "FETCH" and "BODYSTRUCTURE" in args[1]:
            start = int(menge.split(":")[0])
            uids = sorted((u for u in box if int(u) >= start), key=int) or sorted(box, key=int)[-1:]
            return "OK", [f"{i} (UID {u} RFC822.SIZE {len(box[u])} BODYSTRUCTURE {_bodystructure(box[u])})".encode()
                          for i, u in enumerate(uids, 1)]
        if befehl == "FETCH":
            self.voll_geladen.append(menge)
            return "OK", [(f"1 (UID {menge} BODY[] {{{len(box[menge])}}}".encode(), box[menge]), b")"]
        if befehl in ("MOVE", "COPY"):
            ziel = args[1].strip('"')
            if ziel not in self.ordner:
                return "NO", [b"[TRYCREATE] Mailbox doesn't exist"]
            self.ordner[ziel][menge] = box[menge]
            if befehl == "MOVE":
                del box[menge]
            return "OK", [b""]
        if befehl == "STORE":
            self.geloescht_markiert.add(menge)
            return "OK", [b""]
        if befehl == "EXPUNGE":
            del box[menge]
            self.geloescht_markiert.discard(menge)
            return "OK", [b""]
        raise AssertionError(f"unerwarteter Befehl {befehl}")


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(postfach, "UPLOADS", tmp_path / "uploads")
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(
        firmenname="Test", strasse="S", hausnummer="1", plz="12345", ort="O",
        postfach_aktiv=True, imap_host="imap.example", imap_user="u", imap_passwort="geheim",
    ))
    session.commit()
    yield session
    session.close()


def _server(monkeypatch, mails, **kw) -> FakeImap:
    fake = FakeImap(mails, **kw)
    monkeypatch.setattr(postfach.imaplib, "IMAP4_SSL", fake)
    return fake


def _eintraege(db):
    return db.query(PostfachEingang).order_by(PostfachEingang.id).all()


def _uebernehmen(db, e):
    return postfach.postfach_uebernommen(e.id, postfach.UebernommenRequest(rechnung_id=None), db)


# ---------------------------------------------------------------------------
# Abruf
# ---------------------------------------------------------------------------

def test_abruf_fuellt_liste_und_laesst_postfach_unveraendert(db, monkeypatch):
    fake = _server(monkeypatch, {
        "1": _mail("Rechnung 1", [("re1.pdf", "application/pdf", PDF)]),
        "2": _mail("E-Rechnung", [("re2.xml", "application/xml", XML)]),
        "3": _mail("Newsletter ohne Anhang", []),
    })

    erg = postfach.postfach_abrufen(db)

    assert (erg.mails_geprueft, erg.neu, erg.dubletten) == (3, 2, 0)
    a, b = _eintraege(db)
    assert (a.original_name, b.original_name) == ("re1.pdf", "re2.xml")
    assert a.betreff == "Rechnung 1" and "lieferant.example" in a.absender
    assert (a.mail_ordner, a.mail_uidvalidity, a.mail_uid) == ("INBOX", "4711", "1")
    assert a.mail_message_id and a.status == "offen"
    assert (postfach.UPLOADS / a.datei_pfad).read_bytes() == PDF
    assert set(fake.ordner["INBOX"]) == {"1", "2", "3"}   # nichts verschoben
    assert ZIEL not in fake.ordner                         # kein Ordner angelegt
    assert "3" not in fake.voll_geladen                    # Mail ohne Anhang gar nicht geladen


def test_zweiter_abruf_prueft_nur_neue_mails(db, monkeypatch):
    fake = _server(monkeypatch, {"1": _mail("Rechnung", [("re.pdf", "application/pdf", PDF)])})
    postfach.postfach_abrufen(db)
    fake.ordner["INBOX"]["2"] = _mail("Neue Rechnung", [("neu.pdf", "application/pdf", PDF + b"2")])

    erg = postfach.postfach_abrufen(db)

    assert (erg.mails_geprueft, erg.neu, erg.dubletten) == (1, 1, 0)
    assert fake.voll_geladen == ["1", "2"]   # Mail 1 nicht erneut geladen
    assert len(_eintraege(db)) == 2


def test_gleicher_anhang_in_neuer_mail_ist_dublette(db, monkeypatch):
    fake = _server(monkeypatch, {"1": _mail("Rechnung", [("re.pdf", "application/pdf", PDF)])})
    postfach.postfach_abrufen(db)
    fake.ordner["INBOX"]["2"] = _mail("Zahlungserinnerung", [("re.pdf", "application/pdf", PDF)])
    erg = postfach.postfach_abrufen(db)
    assert (erg.neu, erg.dubletten) == (0, 1)


def test_bereits_als_beleg_vorhanden_ist_dublette(db, monkeypatch):
    db.add(Beleg(dateiname="belege/x.pdf", original_name="x.pdf", sha256=hashlib.sha256(PDF).hexdigest()))
    db.commit()
    _server(monkeypatch, {"1": _mail("Rechnung", [("re.pdf", "application/pdf", PDF)])})
    erg = postfach.postfach_abrufen(db)
    assert (erg.neu, erg.dubletten) == (0, 1)


def test_neue_uidvalidity_liest_neu_ohne_doppelte(db, monkeypatch):
    fake = _server(monkeypatch, {"1": _mail("Rechnung", [("re.pdf", "application/pdf", PDF)], "<a@x>")})
    postfach.postfach_abrufen(db)
    fake.uidvalidity["INBOX"] = "9999"   # Server hat die UIDs neu vergeben
    erg = postfach.postfach_abrufen(db)
    assert (erg.mails_geprueft, erg.neu, erg.dubletten) == (1, 0, 0)   # per Message-ID still übersprungen
    assert len(_eintraege(db)) == 1


def test_andere_anhaenge_werden_ignoriert(db, monkeypatch):
    fake = _server(monkeypatch, {"1": _mail("Bild", [("foto.jpg", "image/jpeg", b"\xff\xd8\xff")])})
    erg = postfach.postfach_abrufen(db)
    assert erg.neu == 0 and fake.voll_geladen == []


# ---------------------------------------------------------------------------
# Übernehmen / Verwerfen → Verschieben
# ---------------------------------------------------------------------------

def test_uebernehmen_verschiebt_mail_und_legt_ordner_an(db, monkeypatch):
    fake = _server(monkeypatch, {"1": _mail("Rechnung", [("re.pdf", "application/pdf", PDF)])})
    postfach.postfach_abrufen(db)
    (e,) = _eintraege(db)
    pfad = postfach.UPLOADS / e.datei_pfad

    erg = _uebernehmen(db, e)

    assert erg.status == "uebernommen" and erg.hinweis is None
    assert not pfad.exists()
    assert "1" not in fake.ordner["INBOX"] and "1" in fake.ordner[ZIEL]
    assert postfach.postfach_eingang("offen", db) == []


def test_verwerfen_laesst_mail_im_posteingang(db, monkeypatch):
    fake = _server(monkeypatch, {"1": _mail("AGB", [("agb.pdf", "application/pdf", PDF)])})
    postfach.postfach_abrufen(db)
    (e,) = _eintraege(db)
    erg = postfach.postfach_verwerfen(e.id, db)
    assert erg.status == "verworfen" and erg.hinweis is None
    assert "1" in fake.ordner["INBOX"] and ZIEL not in fake.ordner


def test_mehrere_anhaenge_erst_verschieben_wenn_keiner_mehr_offen(db, monkeypatch):
    fake = _server(monkeypatch, {"1": _mail("Rechnung + AGB", [
        ("re.pdf", "application/pdf", PDF), ("agb.pdf", "application/pdf", PDF + b"agb")])})
    postfach.postfach_abrufen(db)
    rechnung, agb = _eintraege(db)

    _uebernehmen(db, rechnung)
    assert "1" in fake.ordner["INBOX"]          # AGB noch offen → bleibt
    postfach.postfach_verwerfen(agb.id, db)
    assert "1" in fake.ordner[ZIEL]             # jetzt erledigt → verschoben


def test_uidvalidity_geaendert_sucht_per_message_id(db, monkeypatch):
    fake = _server(monkeypatch, {"1": _mail("Rechnung", [("re.pdf", "application/pdf", PDF)], "<abc@x>")})
    postfach.postfach_abrufen(db)
    (e,) = _eintraege(db)
    # Server vergibt neue UIDs: dieselbe Mail heißt jetzt 77
    fake.ordner["INBOX"] = {"77": fake.ordner["INBOX"]["1"]}
    fake.uidvalidity["INBOX"] = "5000"
    erg = _uebernehmen(db, e)
    assert erg.hinweis is None and "77" in fake.ordner[ZIEL]


def test_mail_nicht_mehr_da_gibt_hinweis(db, monkeypatch):
    fake = _server(monkeypatch, {"1": _mail("Rechnung", [("re.pdf", "application/pdf", PDF)], "<weg@x>")})
    postfach.postfach_abrufen(db)
    (e,) = _eintraege(db)
    fake.ordner["INBOX"] = {}
    fake.uidvalidity["INBOX"] = "1"
    erg = _uebernehmen(db, e)
    assert erg.status == "uebernommen" and "nicht mehr gefunden" in erg.hinweis


def test_zielordner_unter_inbox_namensraum_dovecot(db, monkeypatch):
    # Realer Fall: Fähigkeiten erst nach Login, eigene Ordner nur unterhalb von "INBOX."
    fake = _server(monkeypatch, {"1": _mail("Rechnung", [("re.pdf", "application/pdf", PDF)])},
                   namespace=b'(("INBOX." ".")) NIL NIL', caps_erst_nach_login=True)
    postfach.postfach_abrufen(db)
    erg = _uebernehmen(db, _eintraege(db)[0])
    assert erg.hinweis is None
    assert "1" in fake.ordner["INBOX.RechnungsFee.verarbeitet"] and "1" not in fake.ordner["INBOX"]
    assert ZIEL not in fake.ordner


def test_ohne_move_kopieren_und_nur_eigene_mail_entfernen(db, monkeypatch):
    fake = _server(monkeypatch, {"1": _mail("Rechnung", [("re.pdf", "application/pdf", PDF)])}, move=False)
    postfach.postfach_abrufen(db)
    _uebernehmen(db, _eintraege(db)[0])
    assert "1" not in fake.ordner["INBOX"] and "1" in fake.ordner[ZIEL]


def test_ohne_move_und_uidplus_bleibt_mail_nur_markiert(db, monkeypatch):
    fake = _server(monkeypatch, {"1": _mail("Rechnung", [("re.pdf", "application/pdf", PDF)])},
                   move=False, uidplus=False)
    postfach.postfach_abrufen(db)
    _uebernehmen(db, _eintraege(db)[0])
    assert "1" in fake.ordner["INBOX"] and "1" in fake.geloescht_markiert and "1" in fake.ordner[ZIEL]


# ---------------------------------------------------------------------------
# Fehlerfälle
# ---------------------------------------------------------------------------

def test_falsches_passwort_gibt_verstaendliche_meldung(db, monkeypatch):
    _server(monkeypatch, {})
    db.query(Unternehmen).first().imap_passwort = "falsch"
    db.commit()
    with pytest.raises(HTTPException) as exc:
        postfach.postfach_abrufen(db)
    assert "Anmeldung am Postfach fehlgeschlagen" in exc.value.detail


def test_falscher_ordner_nennt_vorhandene_ordner(db, monkeypatch):
    fake = _server(monkeypatch, {})
    fake.ordner["INBOX.TEST"] = {}
    db.query(Unternehmen).first().imap_ordner = "INBOX/TEST"
    db.commit()
    with pytest.raises(HTTPException) as exc:
        postfach.postfach_testen(db)
    assert "„INBOX/TEST\" nicht gefunden" in exc.value.detail
    assert "„INBOX.TEST“" in exc.value.detail and "„INBOX“" in exc.value.detail
    assert "Shared" not in exc.value.detail


def test_nicht_eingerichtet(db):
    db.query(Unternehmen).first().imap_host = None
    db.commit()
    with pytest.raises(HTTPException) as exc:
        postfach.postfach_abrufen(db)
    assert "nicht vollständig eingerichtet" in exc.value.detail
