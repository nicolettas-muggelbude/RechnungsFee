"""
Nutzer-Folgefund nach Issue #371: Ein von Hand eingetipptes Nummernkreis-Format in
Kleinbuchstaben (z.B. "RE-tt.mm.yyyy") wurde nicht ersetzt - _belegnr_aus_format() suchte
bisher nur exakt YYYY/YY/MM/TT in Grossbuchstaben. Die erzeugte "Rechnungsnummer" war dann
buchstäblich die unveränderte Format-Vorlage statt einer echten Nummer. Fix: Platzhalter
werden jetzt unabhängig von Gross-/Kleinschreibung erkannt.
"""
from datetime import date

from api.journal import _belegnr_aus_format


def test_grossbuchstaben_platzhalter_unveraendert():
    assert _belegnr_aus_format("RE-YYYY-####", date(2026, 8, 28), 7) == "RE-2026-0007"


def test_kleinbuchstaben_platzhalter_werden_jetzt_ersetzt():
    assert _belegnr_aus_format("RE-tt.mm.yyyy-####", date(2026, 8, 28), 7) == "RE-28.08.2026-0007"


def test_gemischte_schreibweise():
    assert _belegnr_aus_format("Re-Yyyy/mm/Tt-##", date(2026, 1, 5), 3) == "Re-2026/01/05-03"


def test_yyyy_geht_vor_yy_auch_bei_kleinbuchstaben():
    """yyyy darf nicht faelschlich als zwei "yy" (2026 -> 2626) interpretiert werden."""
    assert _belegnr_aus_format("yyyy", date(2026, 8, 28), 1) == "2026"
