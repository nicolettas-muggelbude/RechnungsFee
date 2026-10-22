"""
Rechnungspostfach per IMAP (Issue #451, Stufe 1).

Abruf: PDF-/XML-Anhänge aus dem eingestellten Ordner landen in der Importliste
(postfach_eingang). Die Mail selbst bleibt dabei unverändert im Postfach (BODY.PEEK - auch der
Gelesen-Status ändert sich nicht). Geprüft werden nur Mails seit dem letzten Abruf
(unternehmen.imap_abruf_stand); vollständig geladen nur solche, deren BODYSTRUCTURE einen
möglichen PDF-/XML-Anhang zeigt.

Übernahme: bewusst KEINE automatische Erfassung - das Frontend holt die Datei und startet damit
den unveränderten Einzelimport (Analyse → Formular → Prüfung → Speichern → Beleg). Danach wird
der Eintrag per /uebernommen als erledigt markiert - erst DANN wird die Mail in den Unterordner
"RechnungsFee/verarbeitet" verschoben (sobald kein Anhang derselben Mail mehr offen ist).
Verworfene Mails bleiben im Posteingang.

Sicherheit: Das Postfach ist von außen beschreibbar - deshalb nur PDF/XML, Größenlimits, nie
automatische Buchungen. Zertifikats-Pinning (Trust on First Use) analog zum SMTP-Versand (#336).
"""
from __future__ import annotations

import email
import email.policy
import hashlib
import imaplib
import json
import re
import socket
import ssl
import uuid
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import APP_DATA_DIR, get_db
from database.models import Beleg, PostfachEingang, Rechnung, Unternehmen

router = APIRouter(prefix="/api/postfach", tags=["Postfach"])

UPLOADS = APP_DATA_DIR / "uploads"
ZIEL_TEILE = ("RechnungsFee", "verarbeitet")
MAX_MAILS_PRO_ABRUF = 50
MAX_MAIL_BYTES = 40 * 1024 * 1024
MAX_ANHANG_BYTES = 25 * 1024 * 1024
_ENDUNGEN = {".pdf": "application/pdf", ".xml": "application/xml"}
_MIME_XML = {"application/xml", "text/xml"}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PostfachEintrag(BaseModel):
    id: int
    original_name: str
    mime_type: str
    dateigroesse: int
    absender: Optional[str] = None
    betreff: Optional[str] = None
    mail_datum: Optional[datetime] = None
    status: str
    rechnung_id: Optional[int] = None
    erstellt_am: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AbrufErgebnis(BaseModel):
    mails_geprueft: int             # neue Mails seit dem letzten Abruf
    neu: int                        # neue Einträge in der Importliste
    dubletten: int                  # Anhänge, die schon in der Liste oder als Beleg vorhanden sind
    uebersprungen: list[str] = []   # Hinweise zu Mails, die nicht verarbeitet werden konnten
    weitere_mails: bool = False     # Limit erreicht - erneut abrufen


class EintragMitHinweis(PostfachEintrag):
    # z. B. "Mail konnte nicht verschoben werden" - die Übernahme selbst ist trotzdem erledigt
    hinweis: Optional[str] = None


class TestErgebnis(BaseModel):
    ok: bool
    ordner: str
    anzahl_mails: int


class UebernommenRequest(BaseModel):
    rechnung_id: Optional[int] = None


# ---------------------------------------------------------------------------
# IMAP-Verbindung
# ---------------------------------------------------------------------------

def _einstellungen(db: Session) -> Unternehmen:
    u = db.query(Unternehmen).first()
    if not u or not u.imap_host or not u.imap_user or not u.imap_passwort:
        raise HTTPException(400, "Rechnungspostfach ist nicht vollständig eingerichtet (Server, Benutzer, Passwort).")
    return u


def _pruefe_gepinntes_zertifikat(u: Unternehmen, sock, db: Session) -> None:
    """Trust on First Use wie beim SMTP-Versand (api/mail.py, Issue #336)."""
    fp = hashlib.sha256(sock.getpeercert(binary_form=True)).hexdigest()
    if not u.imap_zertifikat_fingerprint:
        u.imap_zertifikat_fingerprint = fp
        db.commit()
    elif fp != u.imap_zertifikat_fingerprint:
        raise HTTPException(
            400,
            "Das Zertifikat des IMAP-Servers hat sich geändert! Das kann eine legitime "
            "Zertifikatserneuerung sein - oder ein Angriff auf die Verbindung. Zur Sicherheit wurde "
            "abgebrochen, bevor Zugangsdaten gesendet wurden. Bitte in den Postfach-Einstellungen das "
            "gemerkte Zertifikat bewusst zurücksetzen (nur wenn die Änderung erwartet ist).",
        )


def _verbinde(u: Unternehmen, db: Session) -> imaplib.IMAP4:
    ctx = ssl.create_default_context()
    if u.imap_zertifikat_ignorieren:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    port = u.imap_port or (993 if u.imap_ssl else 143)
    try:
        if u.imap_ssl:
            m = imaplib.IMAP4_SSL(u.imap_host, port, ssl_context=ctx, timeout=20)
        else:
            m = imaplib.IMAP4(u.imap_host, port, timeout=20)
            m.starttls(ssl_context=ctx)
        if u.imap_zertifikat_ignorieren:
            _pruefe_gepinntes_zertifikat(u, m.sock, db)
        m.login(u.imap_user, u.imap_passwort)
        # imaplib merkt sich die CAPABILITY-Antwort VOR der Anmeldung - viele Server (z. B. Dovecot)
        # melden MOVE/NAMESPACE/UIDPLUS erst danach. Ohne Neuabfrage würde der Zielordner im
        # falschen Namensraum angelegt ("Mailbox name should probably be prefixed with: INBOX.").
        try:
            typ, daten = m.capability()
            if typ == "OK" and daten:
                m.capabilities = tuple(_text(daten[-1]).upper().split())
        except Exception:
            pass
        return m
    except HTTPException:
        raise
    except imaplib.IMAP4.error as e:
        raise HTTPException(400, f"Anmeldung am Postfach fehlgeschlagen – Benutzer oder Passwort prüfen ({_text(e)}).")
    except ssl.SSLCertVerificationError as e:
        grund = "ein selbstsigniertes" if "self-signed certificate" in str(e) else "ein nicht vertrauenswürdiges"
        raise HTTPException(
            400,
            f'Zertifikatsprüfung fehlgeschlagen: Der IMAP-Server „{u.imap_host}" verwendet {grund} Zertifikat. '
            "Ist der Server vertrauenswürdig (z. B. eigener Mailserver), kannst du in den Einstellungen "
            "„Selbstsigniertes Zertifikat akzeptieren“ aktivieren.",
        )
    except ssl.SSLError as e:
        raise HTTPException(400, f"TLS/SSL-Fehler bei der Verbindung zu {u.imap_host}:{port}: {e}")
    except socket.gaierror:
        raise HTTPException(400, f'IMAP-Server „{u.imap_host}" wurde nicht gefunden – Servername und Internetverbindung prüfen.')
    except (TimeoutError, socket.timeout):
        raise HTTPException(400, f"Zeitüberschreitung bei der Verbindung zu {u.imap_host}:{port} – Servername, Port und Firewall prüfen.")
    except ConnectionRefusedError:
        raise HTTPException(400, f"Verbindung zu {u.imap_host}:{port} abgelehnt – Port und SSL-Einstellung prüfen (993 mit SSL, 143 mit STARTTLS).")
    except OSError as e:
        raise HTTPException(400, f"Netzwerkfehler: {e}")


def _text(wert) -> str:
    if isinstance(wert, bytes):
        return wert.decode("utf-8", "replace")
    if isinstance(wert, (list, tuple)) and wert:
        return _text(wert[0])
    return str(wert)


def _q(name: str) -> str:
    """Ordnernamen für IMAP-Befehle quoten (Leerzeichen, Sonderzeichen)."""
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _trennzeichen(m: imaplib.IMAP4) -> str:
    typ, daten = m.list('""', '""')
    if typ == "OK" and daten and daten[0]:
        treffer = re.search(rb'\(.*?\)\s+"(.)"', daten[0] if isinstance(daten[0], bytes) else b"")
        if treffer:
            return treffer.group(1).decode()
    return "/"


_LIST_ZEILE_RE = re.compile(rb'^\((?P<flags>[^)]*)\)\s+(?:"(?:[^"\\]|\\.)*"|NIL)\s+(?P<name>.+)$')


def _ordnerliste(m: imaplib.IMAP4) -> list[str]:
    """Alle auswählbaren Ordnernamen in der Schreibweise des Servers (inkl. Trennzeichen)."""
    typ, daten = m.list()
    namen: list[str] = []
    for zeile in (daten or []) if typ == "OK" else []:
        if isinstance(zeile, tuple):    # Literal-Form {n}\r\nname
            kopf, name_roh = zeile[0], zeile[1]
            if b"\\Noselect" in kopf:
                continue
            namen.append(name_roh.decode("utf-8", "replace"))
            continue
        if not isinstance(zeile, bytes):
            continue
        treffer = _LIST_ZEILE_RE.match(zeile.strip())
        if not treffer or b"\\Noselect" in treffer.group("flags"):
            continue
        name = treffer.group("name").decode("utf-8", "replace")
        if name.startswith('"') and name.endswith('"'):
            name = name[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        namen.append(name)
    return sorted(namen, key=str.lower)


def _ordner_auswaehlen(m: imaplib.IMAP4, ordner: str, readonly: bool = False):
    typ, daten = m.select(_q(ordner), readonly=readonly)
    if typ == "OK":
        return daten
    vorhanden = [n for n in _ordnerliste(m) if ZIEL_TEILE[0] not in n]   # eigenen Zielordner nicht anbieten
    hinweis = (" Vorhandene Ordner: " + ", ".join(f"„{n}“" for n in vorhanden[:30])
               + (" …" if len(vorhanden) > 30 else "") + ".") if vorhanden else ""
    raise HTTPException(
        400,
        f'Ordner „{ordner}" nicht gefunden. Unterordner werden je nach Mailserver mit „/" oder „." '
        f'getrennt (z. B. „INBOX/Rechnungen" oder „INBOX.Rechnungen").{hinweis}',
    )


def _namensraum(m: imaplib.IMAP4) -> tuple[str, Optional[str]]:
    """(Präfix, Trennzeichen) des persönlichen Namensraums (RFC 2342). Manche Server (Courier,
    einige Dovecot-Setups) erlauben eigene Ordner nur unterhalb von "INBOX." - ein Zielordner
    auf oberster Ebene ließe sich dort nicht anlegen."""
    # Bewusst auch ohne gemeldete NAMESPACE-Fähigkeit versuchen - ein Server ohne Unterstützung
    # antwortet mit BAD/NO, dann bleibt es beim Zielordner auf oberster Ebene.
    try:
        typ, daten = m.namespace()
    except Exception:
        return "", None
    roh = daten[0] if typ == "OK" and daten and isinstance(daten[0], bytes) else b""
    treffer = re.match(rb'\(\("((?:[^"\\]|\\.)*)"\s+(?:"((?:[^"\\]|\\.)*)"|NIL)\)', roh)
    if not treffer:
        return "", None
    praefix = treffer.group(1).decode("utf-8", "replace")
    trenner = treffer.group(2).decode("utf-8", "replace") if treffer.group(2) is not None else None
    return praefix, trenner


def _zielordner_anlegen(m: imaplib.IMAP4) -> str:
    praefix, ns_trenner = _namensraum(m)
    trenner = ns_trenner or _trennzeichen(m)
    pfad = praefix.rstrip(trenner) if praefix else ""
    for teil in ZIEL_TEILE:
        pfad = f"{pfad}{trenner}{teil}" if pfad else teil
        m.create(_q(pfad))       # existiert er schon, antwortet der Server mit NO - unkritisch
        m.subscribe(_q(pfad))    # im Mailprogramm sichtbar machen
    return pfad


def _hat_faehigkeit(m: imaplib.IMAP4, name: str) -> bool:
    return name.upper() in {c.upper() for c in (m.capabilities or ())}


def _verschiebe(m: imaplib.IMAP4, uid: bytes, ziel: str) -> None:
    if _hat_faehigkeit(m, "MOVE"):
        typ, daten = m.uid("MOVE", uid, _q(ziel))
        if typ != "OK":
            raise RuntimeError(_text(daten))
        return
    typ, daten = m.uid("COPY", uid, _q(ziel))
    if typ != "OK":
        raise RuntimeError(_text(daten))
    m.uid("STORE", uid, "+FLAGS", r"(\Deleted)")
    # Nur die eigene Mail endgültig entfernen - ein ordnerweites EXPUNGE würde auch Mails löschen,
    # die der Nutzer selbst nur als gelöscht markiert hat. Ohne UIDPLUS bleibt sie markiert liegen.
    if _hat_faehigkeit(m, "UIDPLUS"):
        m.uid("EXPUNGE", uid)


# ---------------------------------------------------------------------------
# Mail-Auswertung
# ---------------------------------------------------------------------------

def _anhaenge(msg) -> list[tuple[str, str, bytes]]:
    """(Dateiname, MIME-Typ, Inhalt) aller PDF-/XML-Anhänge."""
    ergebnis = []
    for teil in msg.walk():
        if teil.is_multipart():
            continue
        name = teil.get_filename() or ""
        mime = (teil.get_content_type() or "").lower()
        endung = Path(name).suffix.lower()
        if endung in _ENDUNGEN:
            mime = _ENDUNGEN[endung]
        elif mime == "application/pdf":
            name = name or "rechnung.pdf"
        elif mime in _MIME_XML and teil.get_content_disposition() == "attachment":
            name, mime = name or "rechnung.xml", "application/xml"
        else:
            continue
        inhalt = teil.get_payload(decode=True) or b""
        if not inhalt:
            continue
        ergebnis.append((name, mime, inhalt))
    return ergebnis


def _dateiname_sicher(name: str) -> str:
    stamm = re.sub(r"[^\w.\-]+", "_", Path(name).stem)[:60] or "anhang"
    return f"{stamm}_{uuid.uuid4().hex[:8]}{Path(name).suffix.lower()}"


@router.post("/test", response_model=TestErgebnis)
def postfach_testen(db: Session = Depends(get_db)):
    """Verbindung, Anmeldung und Ordner prüfen - ändert nichts im Postfach."""
    u = _einstellungen(db)
    m = _verbinde(u, db)
    try:
        daten = _ordner_auswaehlen(m, u.imap_ordner or "INBOX", readonly=True)
        return TestErgebnis(ok=True, ordner=u.imap_ordner or "INBOX", anzahl_mails=int(_text(daten) or 0))
    finally:
        try:
            m.logout()
        except Exception:
            pass


# Möglicher Rechnungsanhang laut BODYSTRUCTURE - großzügig (octet-stream, Dateiendung), damit
# nichts übersehen wird; die eigentliche Prüfung macht _anhaenge() nach dem Laden der Mail.
_KANDIDAT_RE = re.compile(
    rb'"APPLICATION"\s+"(?:PDF|X-PDF|XML|OCTET-STREAM)"|"TEXT"\s+"XML"|\.(?:PDF|XML)"', re.IGNORECASE,
)
_SATZ_START_RE = re.compile(rb"^\d+ \(")


def _fetch_datensaetze(daten) -> list[bytes]:
    """imaplib-FETCH-Antwort (gemischte bytes/tuple-Teile bei Literalen) pro Mail zusammenfügen."""
    saetze: list[bytes] = []
    for teil in daten or []:
        if isinstance(teil, tuple):
            stueck = b"".join(x for x in teil if isinstance(x, bytes))
            kopf = teil[0] if teil and isinstance(teil[0], bytes) else b""
        elif isinstance(teil, bytes):
            stueck = kopf = teil
        else:
            continue
        if _SATZ_START_RE.match(kopf) or not saetze:
            saetze.append(stueck)
        else:
            saetze[-1] += stueck
    return saetze


def _neue_mails(m: imaplib.IMAP4, ab_uid: int) -> list[tuple[int, int, bool]]:
    """(UID, Größe, möglicher Rechnungsanhang) aller Mails mit UID > ab_uid, aufsteigend."""
    typ, daten = m.uid("FETCH", f"{ab_uid + 1}:*", "(UID RFC822.SIZE BODYSTRUCTURE)")
    if typ != "OK":
        return []
    mails = []
    for satz in _fetch_datensaetze(daten):
        uid = re.search(rb"UID (\d+)", satz)
        if not uid or int(uid.group(1)) <= ab_uid:   # "N:*" liefert bei N > max die letzte Mail
            continue
        groesse = re.search(rb"RFC822\.SIZE (\d+)", satz)
        mails.append((int(uid.group(1)), int(groesse.group(1)) if groesse else 0, bool(_KANDIDAT_RE.search(satz))))
    return sorted(mails)


def _uidvalidity(m: imaplib.IMAP4) -> Optional[str]:
    typ, daten = m.response("UIDVALIDITY")
    return _text(daten) if daten and daten[0] else None


def _lese_stand(u: Unternehmen, ordner: str, uidvalidity: Optional[str]) -> int:
    try:
        stand = json.loads(u.imap_abruf_stand or "{}")
    except ValueError:
        return 0
    if stand.get("ordner") != ordner or stand.get("uidvalidity") != uidvalidity:
        return 0   # anderer Ordner oder Server hat die UIDs neu vergeben → von vorn (Message-ID schützt vor Doppelten)
    return int(stand.get("uid") or 0)


@router.post("/abrufen", response_model=AbrufErgebnis)
def postfach_abrufen(db: Session = Depends(get_db)):
    u = _einstellungen(db)
    m = _verbinde(u, db)
    ergebnis = AbrufErgebnis(mails_geprueft=0, neu=0, dubletten=0)
    ordner = u.imap_ordner or "INBOX"
    try:
        _ordner_auswaehlen(m, ordner, readonly=True)   # readonly: der Abruf verändert nichts im Postfach
        uidvalidity = _uidvalidity(m)
        stand = _lese_stand(u, ordner, uidvalidity)
        geladen = 0

        for uid, groesse, kandidat in _neue_mails(m, stand):
            if kandidat and geladen >= MAX_MAILS_PRO_ABRUF:
                ergebnis.weitere_mails = True
                break
            ergebnis.mails_geprueft += 1
            stand = uid
            if not kandidat:
                continue   # kein Rechnungsanhang - Mail bleibt unberührt
            if groesse > MAX_MAIL_BYTES:
                ergebnis.uebersprungen.append(f"Eine Mail ist größer als {MAX_MAIL_BYTES // 1024 // 1024} MB – übersprungen.")
                continue
            geladen += 1
            typ, roh = m.uid("FETCH", str(uid), "(BODY.PEEK[])")
            mail_bytes = next((t[1] for t in (roh or []) if isinstance(t, tuple) and len(t) > 1), None)
            if typ != "OK" or not mail_bytes:
                continue
            msg = email.message_from_bytes(mail_bytes, policy=email.policy.default)
            message_id = (str(msg.get("Message-ID", "")).strip() or None)
            if message_id and db.query(PostfachEingang.id).filter(PostfachEingang.mail_message_id == message_id).first():
                continue   # schon in der Liste (z. B. nach geändertem Abrufstand)
            anhaenge = _anhaenge(msg)
            if not anhaenge:
                continue

            absender = str(msg.get("From", ""))[:300] or None
            betreff = str(msg.get("Subject", ""))[:500] or None
            try:
                mail_datum = parsedate_to_datetime(msg.get("Date")) if msg.get("Date") else None
                if mail_datum and mail_datum.tzinfo:
                    mail_datum = mail_datum.astimezone().replace(tzinfo=None)
            except (TypeError, ValueError):
                mail_datum = None

            for name, mime, inhalt in anhaenge:
                if len(inhalt) > MAX_ANHANG_BYTES:
                    ergebnis.uebersprungen.append(f'Anhang „{name}" ({betreff or "ohne Betreff"}) ist zu groß – übersprungen.')
                    continue
                sha = hashlib.sha256(inhalt).hexdigest()
                if (db.query(PostfachEingang.id).filter(PostfachEingang.sha256 == sha).first()
                        or db.query(Beleg.id).filter(Beleg.sha256 == sha).first()):
                    ergebnis.dubletten += 1
                    continue
                jetzt = datetime.now()
                rel = Path("postfach") / str(jetzt.year) / jetzt.strftime("%m") / _dateiname_sicher(name)
                (UPLOADS / rel).parent.mkdir(parents=True, exist_ok=True)
                (UPLOADS / rel).write_bytes(inhalt)
                db.add(PostfachEingang(
                    sha256=sha, datei_pfad=rel.as_posix(), original_name=name[:255], mime_type=mime,
                    dateigroesse=len(inhalt), absender=absender, betreff=betreff, mail_datum=mail_datum,
                    mail_ordner=ordner, mail_uidvalidity=uidvalidity, mail_uid=str(uid),
                    mail_message_id=message_id[:500] if message_id else None,
                ))
                db.commit()
                ergebnis.neu += 1

        u.imap_abruf_stand = json.dumps({"ordner": ordner, "uidvalidity": uidvalidity, "uid": stand})
        db.commit()
        return ergebnis
    finally:
        try:
            m.logout()
        except Exception:
            pass


def _gleiche_mail(e: PostfachEingang):
    if e.mail_message_id:
        return PostfachEingang.mail_message_id == e.mail_message_id
    return ((PostfachEingang.mail_ordner == e.mail_ordner)
            & (PostfachEingang.mail_uidvalidity == e.mail_uidvalidity)
            & (PostfachEingang.mail_uid == e.mail_uid))


def _mail_abschliessen(e: PostfachEingang, db: Session) -> Optional[str]:
    """Verschiebt die Mail nach "RechnungsFee/verarbeitet", sobald kein Anhang derselben Mail mehr
    offen ist und mindestens einer übernommen wurde. Nur verworfene Mails bleiben im Posteingang.
    Gibt bei einem Problem einen Hinweis zurück - die Übernahme selbst ist davon nicht betroffen."""
    if not e.mail_ordner:
        return None
    geschwister = db.query(PostfachEingang).filter(_gleiche_mail(e)).all()
    if any(g.status == "offen" for g in geschwister) or not any(g.status == "uebernommen" for g in geschwister):
        return None
    ziel_anzeige = "/".join(ZIEL_TEILE)
    try:
        u = _einstellungen(db)
        m = _verbinde(u, db)
    except HTTPException as ex:
        return f"Die Mail wurde nicht nach „{ziel_anzeige}“ verschoben: {ex.detail}"
    try:
        typ, _ = m.select(_q(e.mail_ordner))
        if typ != "OK":
            return f"Die Mail wurde nicht verschoben: Ordner „{e.mail_ordner}“ nicht gefunden."
        uid: Optional[str] = None
        if e.mail_uid and _uidvalidity(m) == e.mail_uidvalidity:
            uid = e.mail_uid
        elif e.mail_message_id:
            typ, daten = m.uid("SEARCH", None, "HEADER", "Message-ID", _q(e.mail_message_id))
            treffer = (daten[0] or b"").split() if typ == "OK" and daten else []
            uid = _text(treffer[-1]) if treffer else None
        if uid is None:
            return "Die Mail wurde im Postfach nicht mehr gefunden und deshalb nicht verschoben."
        _verschiebe(m, uid, _zielordner_anlegen(m))
        return None
    except Exception as ex:
        return f"Die Mail konnte nicht nach „{ziel_anzeige}“ verschoben werden: {_text(ex)}"
    finally:
        try:
            m.logout()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Importliste
# ---------------------------------------------------------------------------

def _eintrag(eintrag_id: int, db: Session) -> PostfachEingang:
    e = db.query(PostfachEingang).filter(PostfachEingang.id == eintrag_id).first()
    if not e:
        raise HTTPException(404, "Eintrag nicht gefunden.")
    return e


@router.get("/eingang", response_model=list[PostfachEintrag])
def postfach_eingang(status: str = "offen", db: Session = Depends(get_db)):
    q = db.query(PostfachEingang)
    if status != "alle":
        q = q.filter(PostfachEingang.status == status)
    return q.order_by(PostfachEingang.mail_datum.desc(), PostfachEingang.id.desc()).all()


@router.get("/eingang/{eintrag_id}/datei")
def postfach_datei(eintrag_id: int, db: Session = Depends(get_db)):
    e = _eintrag(eintrag_id, db)
    if not e.datei_pfad or not (UPLOADS / e.datei_pfad).exists():
        raise HTTPException(404, "Datei nicht mehr vorhanden.")
    # inline: PDFs werden per openUrl() im WebviewWindow angezeigt (CLAUDE.md)
    return FileResponse(
        UPLOADS / e.datei_pfad, media_type=e.mime_type,
        headers={"Content-Disposition": f'inline; filename="{Path(e.datei_pfad).name}"'},
    )


@router.post("/eingang/{eintrag_id}/uebernommen", response_model=EintragMitHinweis)
def postfach_uebernommen(eintrag_id: int, body: UebernommenRequest, db: Session = Depends(get_db)):
    """Nach erfolgreichem Einzelimport: Eintrag erledigt (die Datei hängt dann als Beleg an der
    Rechnung) und die Mail wandert nach "RechnungsFee/verarbeitet"."""
    e = _eintrag(eintrag_id, db)
    if body.rechnung_id is not None and not db.query(Rechnung.id).filter(Rechnung.id == body.rechnung_id).first():
        raise HTTPException(404, "Rechnung nicht gefunden.")
    e.status = "uebernommen"
    e.rechnung_id = body.rechnung_id
    _datei_entfernen(e)
    db.commit()
    hinweis = _mail_abschliessen(e, db)
    db.refresh(e)
    return EintragMitHinweis.model_validate(e).model_copy(update={"hinweis": hinweis})


@router.post("/eingang/{eintrag_id}/verwerfen", response_model=EintragMitHinweis)
def postfach_verwerfen(eintrag_id: int, db: Session = Depends(get_db)):
    """Kein Rechnungsbeleg (z. B. AGB, Werbung). Zeile bleibt als Dublettenschutz bestehen, die
    Mail bleibt im Posteingang - außer ein anderer Anhang derselben Mail wurde übernommen."""
    e = _eintrag(eintrag_id, db)
    e.status = "verworfen"
    _datei_entfernen(e)
    db.commit()
    hinweis = _mail_abschliessen(e, db)
    db.refresh(e)
    return EintragMitHinweis.model_validate(e).model_copy(update={"hinweis": hinweis})


def _datei_entfernen(e: PostfachEingang) -> None:
    if e.datei_pfad:
        pfad = UPLOADS / e.datei_pfad
        if pfad.exists():
            pfad.unlink()
        e.datei_pfad = None
