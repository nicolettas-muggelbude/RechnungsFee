"""
Issue #440: anpassbare Anrede in den Rechnungs-PDFs.
Reihenfolge eigene Kundenanrede > globaler Satz > Standard "Hallo {vorname} {nachname},",
Ersatzanrede bei leeren Platzhaltern, Vorlage 0 nur wenn konfiguriert, alte Snapshots unverändert.
"""
from types import SimpleNamespace

from utils.pdf_rechnung_base import anrede_zeile


def _r(kunde=None, partner_freitext=None):
    return SimpleNamespace(typ="ausgang", kunde=kunde, lieferant=None, partner_freitext=partner_freitext)


def _kunde(**kw):
    basis = dict(vorname="Sandra", nachname="Grün", firmenname=None, anrede=None, anrede_individuell=None)
    basis.update(kw)
    return SimpleNamespace(**basis)


UNT_LEER = {"anrede_text": "", "anrede_fallback": ""}


def test_standard_vor_und_nachname():
    assert anrede_zeile(_r(_kunde()), UNT_LEER) == "Hallo Sandra Grün,"


def test_standard_ohne_nachname_kein_doppeltes_leerzeichen():
    assert anrede_zeile(_r(_kunde(nachname=None)), UNT_LEER) == "Hallo Sandra,"


def test_standard_ohne_namen_fallback():
    assert anrede_zeile(_r(_kunde(vorname=None, nachname=None)), UNT_LEER) == "Hallo,"
    assert anrede_zeile(_r(None, partner_freitext="Einmalkunde"), UNT_LEER) == "Hallo,"


def test_sehr_geehrte_je_anrede():
    unt = {"anrede_text": "{sehr_geehrte} {nachname},", "anrede_fallback": ""}
    assert anrede_zeile(_r(_kunde(anrede="frau")), unt) == "Sehr geehrte Frau Grün,"
    assert anrede_zeile(_r(_kunde(anrede="herr", vorname="Max", nachname="Muster")), unt) == "Sehr geehrter Herr Muster,"
    # divers/ohne Angabe: geschlechtsneutral mit Vorname
    assert anrede_zeile(_r(_kunde(anrede="divers")), unt) == "Guten Tag Sandra Grün,"
    assert anrede_zeile(_r(_kunde()), unt) == "Guten Tag Sandra Grün,"


def test_anrede_platzhalter_ohne_herr_frau_nimmt_fallback():
    unt = {"anrede_text": "Hallo {anrede} {nachname},", "anrede_fallback": "Sehr geehrte Damen und Herren,"}
    assert anrede_zeile(_r(_kunde(anrede="frau")), unt) == "Hallo Frau Grün,"
    assert anrede_zeile(_r(_kunde(anrede="divers")), unt) == "Sehr geehrte Damen und Herren,"


def test_eigene_kundenanrede_hat_vorrang():
    unt = {"anrede_text": "{sehr_geehrte} {nachname},", "anrede_fallback": ""}
    k = _kunde(anrede="frau", anrede_individuell="Liebe {vorname},")
    assert anrede_zeile(_r(k), unt) == "Liebe Sandra,"


def test_firma_platzhalter():
    unt = {"anrede_text": "Hallo Team {firma},", "anrede_fallback": ""}
    assert anrede_zeile(_r(_kunde(firmenname="Grün GmbH")), unt) == "Hallo Team Grün GmbH,"
    assert anrede_zeile(_r(_kunde()), unt) == "Hallo,"


def test_unbekannter_platzhalter_bleibt_stehen():
    unt = {"anrede_text": "Hallo {spitzname},", "anrede_fallback": ""}
    assert anrede_zeile(_r(_kunde()), unt) == "Hallo {spitzname},"


def test_vorlage0_nur_wenn_konfiguriert():
    assert anrede_zeile(_r(_kunde()), UNT_LEER, nur_wenn_konfiguriert=True) == ""
    unt = {"anrede_text": "Hallo {vorname},", "anrede_fallback": ""}
    assert anrede_zeile(_r(_kunde()), unt, nur_wenn_konfiguriert=True) == "Hallo Sandra,"
    k = _kunde(anrede_individuell="Moin {vorname},")
    assert anrede_zeile(_r(k), UNT_LEER, nur_wenn_konfiguriert=True) == "Moin Sandra,"


def test_alter_snapshot_ohne_schluessel_behaelt_alte_anrede():
    # Finalisiert vor #440: Snapshot kennt anrede_text nicht -> bisheriges "Hallo {vorname},"
    alt = {"firmenname": "X"}
    k = _kunde(anrede_individuell="Liebe {vorname},")
    assert anrede_zeile(_r(k), alt) == "Hallo Sandra,"
    assert anrede_zeile(_r(_kunde(vorname=None)), alt) == "Hallo,"
    assert anrede_zeile(_r(k), alt, nur_wenn_konfiguriert=True) == ""


# Ersatzanrede mit eigenen Platzhaltern (Nutzer-Feedback 2026-11-09: „Moin {firma}“ wurde bei
# einem Firmenkunden ohne Ansprechpartner wörtlich mit „{firma}“ gedruckt)

UNT_MOIN = {"anrede_text": "Moin {vorname} {nachname}", "anrede_fallback": "Moin {firma}"}


def test_ersatzanrede_ersetzt_firma():
    k = _kunde(vorname=None, nachname=None, firmenname="Onx GmbH")
    assert anrede_zeile(_r(k), UNT_MOIN) == "Moin Onx GmbH"


def test_ersatzanrede_einmalkunde_freitext():
    assert anrede_zeile(_r(None, partner_freitext="Bäckerei Krume"), UNT_MOIN) == "Moin Bäckerei Krume"


def test_ersatzanrede_ohne_wert_nimmt_standard():
    k = _kunde(vorname=None, nachname=None, firmenname=None)
    assert anrede_zeile(_r(k), UNT_MOIN) == "Hallo,"


def test_ersatzanrede_ohne_platzhalter_unveraendert():
    k = _kunde(vorname=None, nachname=None, firmenname="Onx GmbH")
    unt = {"anrede_text": "Moin {vorname},", "anrede_fallback": "Sehr geehrte Damen und Herren,"}
    assert anrede_zeile(_r(k), unt) == "Sehr geehrte Damen und Herren,"
