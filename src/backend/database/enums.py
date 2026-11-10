"""
Feste Wertemengen für String-Spalten.

Als `StrEnum` umgesetzt: jedes Mitglied *ist* ein `str` und vergleicht sich gleich mit
seinem Wert (`DokumentTyp.ANGEBOT == "Angebot"`). In der Datenbank, im JSON und im
Frontend bleibt dadurch alles unverändert; Code kann schrittweise umgestellt werden.
Die DB-Spalten bleiben bewusst `String` (kein `sqlalchemy.Enum`, keine Migration).

Werte müssen mit den TypeScript-Typen in `src/frontend/src/api/client.ts` übereinstimmen.
"""

from enum import StrEnum


class RechnungTyp(StrEnum):
    """`rechnungen.typ` – Richtung des Belegs."""

    AUSGANG = "ausgang"
    EINGANG = "eingang"


class DokumentTyp(StrEnum):
    """`rechnungen.dokument_typ` – Art des Dokuments (Groß-/Kleinschreibung wie in der DB)."""

    RECHNUNG = "Rechnung"
    ANGEBOT = "Angebot"
    AUFTRAG = "Auftrag"
    PROFORMA = "Proforma"
    LIEFERSCHEIN = "Lieferschein"
    GUTSCHRIFT = "Gutschrift"
    ABSCHLAGSRECHNUNG = "Abschlagsrechnung"
