"""Storno-Erkennung innerhalb einer Buchungsgruppe (Issue #601).

Original, Storno und Neubuchung einer Korrektur haengen ueber dieselbe gruppe_id (Wurzel-id)
zusammen - ebenso die Zahlungen einer Ersatzrechnungs-Kette. Die gruppe_id sagt daher nur,
DASS eine Buchung zu einer Kette gehoert, nicht WELCHES Glied ein Storno aufhebt. Das steht im
Text der Gegenbuchung: alle Stellen, die ein Storno anlegen (journal.update_eintrag/
storno_eintrag, rechnungen.zahlung_korrigieren/storno_rechnung), schreiben
"STORNO <Belegnr. der aufgehobenen Buchung>: ...".

Vorher galt jede Buchung der Gruppe als storniert, sobald es irgendein Storno darin gab -
dadurch erschien die korrigierte Neubuchung ebenfalls als storniert und liess sich nicht
erneut korrigieren.
"""
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from database.models import Journaleintrag

PRAEFIX = "STORNO "


def ist_storno(e) -> bool:
    """Gegenbuchung: Praefix plus gesetzte gruppe_id (laesst sich clientseitig nicht setzen,
    eine eigene Buchung mit Text "STORNO ..." zaehlt dadurch nicht, Issue #321)."""
    return e.gruppe_id is not None and (e.beschreibung or "").startswith(PRAEFIX)


def storno_bezug(beschreibung: Optional[str]) -> Optional[str]:
    """Belegnummer der Buchung, die eine Gegenbuchung aufhebt (gleiche Auswertung wie der
    Backfill in Migration 122)."""
    if not beschreibung or not beschreibung.startswith(PRAEFIX):
        return None
    return beschreibung[len(PRAEFIX):].split(":")[0].strip() or None


def stornos_je_glied(stornos: Iterable) -> dict[tuple[int, str], str]:
    """(Wurzel-id, aufgehobene Belegnr.) -> Belegnr. der Gegenbuchung."""
    ergebnis: dict[tuple[int, str], str] = {}
    for s in stornos:
        if not ist_storno(s):
            continue
        bezug = storno_bezug(s.beschreibung)
        if bezug:
            ergebnis.setdefault((s.gruppe_id, bezug), s.belegnr)
    return ergebnis


def storno_zu(db: Session, e: Journaleintrag) -> Optional[Journaleintrag]:
    """Gegenbuchung, die genau diese Buchung aufhebt, sonst None."""
    kandidaten = db.query(Journaleintrag).filter(
        Journaleintrag.gruppe_id == (e.gruppe_id or e.id),
        Journaleintrag.beschreibung.like(PRAEFIX + "%"),
    ).order_by(Journaleintrag.id).all()
    return next((s for s in kandidaten if storno_bezug(s.beschreibung) == e.belegnr), None)
