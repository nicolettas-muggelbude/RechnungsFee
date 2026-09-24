"""
Zeitraumberechnung für das Wirtschaftsjahr (Issue #404).

unternehmen.geschaeftsjahr_beginn (Monat 1-12) ist die einzige Quelle der Wahrheit für den
Zeitraum - unternehmen.wirtschaftsjahr_abweichend_aktiv steuert nur, ob das Feld in der UI
sichtbar/editierbar ist (siehe schemas.py::erzwinge_kalenderjahr_wenn_inaktiv, das
geschaeftsjahr_beginn serverseitig auf 1 zwingt sobald der Schalter aus ist). Diese Funktion
kennt den Schalter deshalb bewusst nicht - sie muss ihn auch nicht kennen, ein Aufrufer mit
geschaeftsjahr_beginn=1 bekommt ohnehin exakt das alte Kalenderjahr-Verhalten zurück.
"""

from datetime import date, timedelta

from database.models import Unternehmen


def wirtschaftsjahr_zeitraum(unternehmen: Unternehmen, jahr: int) -> tuple[date, date]:
    """Liefert (von, bis) für das Wirtschaftsjahr, das im Kalenderjahr `jahr` beginnt.
    Bei geschaeftsjahr_beginn=1 (Standard) identisch zu date(jahr,1,1)/date(jahr,12,31)."""
    monat = unternehmen.geschaeftsjahr_beginn or 1
    von = date(jahr, monat, 1)
    if monat == 1:
        bis = date(jahr, 12, 31)
    else:
        bis = date(jahr + 1, monat, 1) - timedelta(days=1)
    return von, bis
