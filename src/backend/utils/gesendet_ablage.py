"""
Issue #596: Kopie per SMTP gesendeter Mails im Ordner „Gesendet“ des Mailkontos ablegen.

SMTP kann nur versenden. Mailprogramme legen die Kopie danach selbst per IMAP ab – das macht
RechnungsFee jetzt auch, wenn unternehmen.gesendet_imap_aktiv gesetzt ist. Benutzer und Passwort
kommen vom Mailversand (bei fast allen Anbietern identisch), nur IMAP-Server und Port sind eigene
Felder. Opt-in, weil Gmail/Outlook per SMTP gesendete Mails ohnehin selbst ablegen (sonst doppelt).

Ein Fehler hier bricht nie ab – die Mail ist zu diesem Zeitpunkt schon verschickt. Stattdessen
kommt ein Hinweistext zurück, den der Versanddialog anzeigt.
"""
import imaplib
import logging
import re
import socket
import ssl
import time
from typing import Optional

from utils.mail_tls import MailTLSConfigurationError, create_mail_tls_context

logger = logging.getLogger(__name__)

# Fallback, wenn der Server den Ordner nicht als \Sent kennzeichnet (RFC 6154)
_NAMEN = ("sent", "gesendet", "gesendete elemente", "gesendete objekte", "sent items", "sent messages", "sent mail")
_LIST_RE = re.compile(rb'^\((?P<flags>[^)]*)\)\s+(?:"(?P<trenner>(?:[^"\\]|\\.)*)"|NIL)\s+(?P<name>.+)$')


def _q(name: str) -> str:
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def gesendet_ordner(m: imaplib.IMAP4) -> Optional[str]:
    """Ordner „Gesendet“: zuerst per Kennzeichnung \\Sent, sonst über gängige Namen."""
    typ, daten = m.list()
    if typ != "OK":
        return None
    eintraege: list[tuple[bytes, str, str]] = []
    for zeile in daten or []:
        if isinstance(zeile, tuple):            # Literal-Form: Name in zweitem Teil
            kopf, name = zeile[0], zeile[1].decode("utf-8", "replace")
            treffer = re.match(rb'^\((?P<flags>[^)]*)\)\s+(?:"(?P<trenner>(?:[^"\\]|\\.)*)"|NIL)', kopf)
            flags = treffer.group("flags") if treffer else b""
            trenner = (treffer.group("trenner") or b"").decode() if treffer else ""
        elif isinstance(zeile, bytes):
            treffer = _LIST_RE.match(zeile.strip())
            if not treffer:
                continue
            flags = treffer.group("flags")
            trenner = (treffer.group("trenner") or b"").decode()
            name = treffer.group("name").decode("utf-8", "replace")
            if name.startswith('"') and name.endswith('"'):
                name = name[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        else:
            continue
        if b"\\Noselect" in flags:
            continue
        eintraege.append((flags, name, trenner))
    for flags, name, _ in eintraege:
        if b"\\Sent" in flags.split():
            return name
    for flags, name, trenner in eintraege:
        letzter = name.rsplit(trenner, 1)[-1] if trenner else name
        if letzter.strip().lower() in _NAMEN:
            return name
    return None


def _verbinde(host: str, port: int) -> imaplib.IMAP4:
    ctx = create_mail_tls_context(public_cas=True)
    if port == 143:
        m = imaplib.IMAP4(host, port, timeout=15)
        m.starttls(ssl_context=ctx)
        return m
    return imaplib.IMAP4_SSL(host, port, ssl_context=ctx, timeout=15)


def lege_gesendet_ab(u, nachricht: bytes, user: str, passwort: str) -> Optional[str]:
    """Kopie ablegen. None = abgelegt, sonst Hinweistext für die Oberfläche."""
    host = (u.gesendet_imap_host or "").strip()
    port = int(u.gesendet_imap_port or 993)
    if not host:
        return "Die Mail wurde gesendet. Für die Kopie im Ordner „Gesendet“ fehlt der IMAP-Server (Einstellungen → Unternehmen → E-Mail)."
    try:
        m = _verbinde(host, port)
        try:
            m.login(user, passwort)
            ordner = gesendet_ordner(m)
            if not ordner:
                return "Die Mail wurde gesendet. Einen Ordner „Gesendet“ hat RechnungsFee im Mailkonto nicht gefunden, deshalb liegt dort keine Kopie."
            typ, daten = m.append(_q(ordner), r"(\Seen)", imaplib.Time2Internaldate(time.time()), nachricht)
            if typ != "OK":
                raise imaplib.IMAP4.error(str(daten))
            return None
        finally:
            try:
                m.logout()
            except Exception:
                pass
    except (imaplib.IMAP4.error, ssl.SSLError, socket.gaierror, TimeoutError, socket.timeout,
            ConnectionRefusedError, OSError, MailTLSConfigurationError) as e:
        logger.warning("Kopie im Ordner Gesendet nicht abgelegt (%s:%s): %s", host, port, e)
        return f"Die Mail wurde gesendet, die Kopie im Ordner „Gesendet“ konnte aber nicht abgelegt werden ({host}:{port}: {e})."
