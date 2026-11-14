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
