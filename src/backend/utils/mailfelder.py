"""
Mail-Zugangsdaten bereinigen (Issue #537).

Beim Kopieren aus Webmailern/Hosting-Panels rutschen oft unsichtbare Zeichen mit (geschütztes
Leerzeichen, Zero-Width-Space, BOM). In Host, Benutzer oder Absenderadresse führen sie zu einem
UnicodeEncodeError, weil SMTP/IMAP dort nur ASCII übertragen – vorher als „Failed to fetch“
sichtbar. Passwörter werden bewusst NICHT angefasst (Sonderzeichen sind dort legitim).
"""

_UNSICHTBAR = dict.fromkeys(map(ord, " ​‌‍⁠﻿  "), None)


def bereinige_mailfeld(wert: str | None) -> str | None:
    if wert is None:
        return None
    return wert.translate(_UNSICHTBAR).strip()


def ist_ascii(wert: str | None) -> bool:
    return (wert or "").isascii()


def ascii_rechnername(name: str | None = None) -> str:
    """Name des eigenen Rechners für EHLO und Message-ID, garantiert ASCII (Issue #537).

    smtplib schickt bei der Begrüßung von sich aus socket.getfqdn() und kann nur ASCII senden.
    Heißt der Windows-PC z. B. „Noël-PC“, scheiterte jeder Versand mit UnicodeEncodeError
    (IMAP war nicht betroffen). Umlaute → IDNA-Schreibweise (xn--…), sonst „localhost“."""
    import socket
    name = bereinige_mailfeld(name if name is not None else socket.getfqdn()) or ""
    if name and name.isascii():
        return name
    try:
        kodiert = name.encode("idna").decode("ascii")
        if kodiert:
            return kodiert
    except UnicodeError:
        pass
    return "localhost"
