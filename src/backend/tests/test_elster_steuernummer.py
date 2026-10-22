"""Tests für die Umrechnung der Steuernummer ins 13-stellige ELSTER-Bundesschema.

Testvektoren aus der kanonischen Bundesland-Tabelle (de.wikipedia.org/wiki/Steuernummer,
"Standardschema der Länder" → "Vereinheitlichtes Bundesschema zur elektronischen
Übermittlung"). Zielschema: \d{4}0\d{8} (BUFA-Nr. + "0" + Bezirk + Unterscheidungsnr + Prüfziffer).
"""
import pytest

from utils.elster import ElsterExportFehler, steuernummer_elster13


# (bundesland, landesformat, erwartete 13-stellige ELSTER-Steuernummer)
WIKIPEDIA_VEKTOREN = [
    ("BW", "93/815/08152", "2893081508152"),
    ("BY", "181/815/08155", "9181081508155"),
    ("BE", "21/815/08150", "1121081508150"),
    ("BB", "048/815/08155", "3048081508155"),
    ("HB", "75/815/08152", "2475081508152"),
    ("HH", "02/815/08156", "2202081508156"),
    ("HE", "013/815/08153", "2613081508153"),
    ("MV", "079/815/08151", "4079081508151"),
    ("NI", "24/815/08151", "2324081508151"),
    ("NW", "133/8150/8159", "5133081508159"),
    ("RP", "22/815/08154", "2722081508154"),
    ("SL", "10/815/08182", "1010081508182"),
    ("SN", "201/123/12340", "3201012312340"),
    ("ST", "101/815/08154", "3101081508154"),
    ("SH", "29/815/08158", "2129081508158"),
    ("TH", "151/815/08156", "4151081508156"),
]


@pytest.mark.parametrize("bundesland,lokal,erwartet", WIKIPEDIA_VEKTOREN)
def test_wikipedia_vektoren(bundesland, lokal, erwartet):
    assert steuernummer_elster13(lokal, bundesland) == erwartet


@pytest.mark.parametrize("trenner", ["/", "-", " ", "."])
def test_trennzeichen_werden_ignoriert(trenner):
    assert steuernummer_elster13(f"93{trenner}815{trenner}08152", "BW") == "2893081508152"


def test_gemischte_trennzeichen_und_leerzeichen():
    assert steuernummer_elster13(" 93/815 - 08152 ", "BW") == "2893081508152"


def test_hessen_ohne_fuehrende_null():
    # Landesformat "013/815/08153", Nutzer könnte die führende 0 weglassen
    assert steuernummer_elster13("13/815/08153", "HE") == "2613081508153"


def test_th_laesst_vorangestellte_laenderziffer_weg_und_direkt():
    # 11-stellig mit Landesziffer ODER bereits 10-stellig eingegeben
    assert steuernummer_elster13("15181508156", "TH") == "4151081508156"
    assert steuernummer_elster13("151/815/08156", "TH") == "4151081508156"


def test_13stelliges_ergebnis_wird_akzeptiert_und_passt_durch():
    # Wer bereits die bundeseinheitliche 13-stellige Nummer hat, bekommt sie zurück
    assert steuernummer_elster13("2893081508152", "BW") == "2893081508152"


def test_ust_idnr_wird_abgelehnt():
    with pytest.raises(ElsterExportFehler, match="USt-IdNr"):
        steuernummer_elster13("DE811907980", "BY")


def test_buchstaben_werden_abgelehnt():
    with pytest.raises(ElsterExportFehler):
        steuernummer_elster13("93/815/0815A", "BW")


def test_falsche_laenge_wird_abgelehnt():
    with pytest.raises(ElsterExportFehler):
        steuernummer_elster13("93815081", "BW")          # zu kurz
    with pytest.raises(ElsterExportFehler):
        steuernummer_elster13("12345678901234", "NW")    # 14 Ziffern


def test_bundesland_erforderlich():
    with pytest.raises(ElsterExportFehler, match="undesland"):
        steuernummer_elster13("93/815/08152", None)
    with pytest.raises(ElsterExportFehler, match="undesland"):
        steuernummer_elster13("93/815/08152", "")


def test_unbekanntes_bundesland():
    with pytest.raises(ElsterExportFehler):
        steuernummer_elster13("93/815/08152", "XX")


def test_bundesland_lowercase_akzeptiert():
    assert steuernummer_elster13("93/815/08152", "bw") == "2893081508152"
