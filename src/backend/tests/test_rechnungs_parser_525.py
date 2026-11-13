"""
Issue #525: PDF-Import erkannte Summen und Positionen mehrerer echter Belege falsch.
Texte nach dem Aufbau der gemeldeten Belege, Namen/Nummern fiktiv.

- "Nettorechnungsbetrag 4,1933" wurde als Brutto gelesen, "Bruttorechnungsbetrag" als Position
- "Gesamtbetrag 38.57 45.90" (exkl./inkl.): der Netto-Betrag landete im Brutto
- "MwSt. 19.00% 7.33": Satz mit Nachkommastellen wurde als USt-Betrag gelesen
- Summenzeile "14,09 2,68 EUR 16,77" unter "Netto MwSt …" wurde zur Position statt zur Summe
- Kassenbon: "Geg. VISA EUR" und OCR-"Gesantbetrag" wurden Positionen
- Menge × Einzelpreis ergab nicht den Zeilenbetrag ("2 kg - Paket 6,19 € 6,19 €" → 12,38)
- Schriften ohne Unicode-Zuordnung ("(cid:20)…") galten als Text, die OCR lief nie
"""
from decimal import Decimal

from utils.rechnungs_parser import (
    KassenbonParser, RechnungParser, _extrahiere_positionen, _ist_unlesbar, _normalisiere_text,
)


def _parse(text: str, parser=RechnungParser):
    return parser().parse(_normalisiere_text(text), [])


TELEKOM_4_STELLEN = """\
RECHNUNG
Musterfon-Team | c/o Muster GmbH | 12345 Musterstadt
Rechnungsnummer: R123
Rechnungsdatum: 28.02.2026
MwSt-Satz Nettobetrag
Allnet-Flat 01.03.2026 - 31.03.2026 19% 16,7983
Ihr Vorteil: Preisreduktion 01.03.2026 - 31.03.2026 19% -12,6050
Nettorechnungsbetrag 4,1933
Umsatzsteuer 19% 0,7967
Bruttorechnungsbetrag EUR 4,99
Der offene Rechnungsbetrag von 4,99 EUR wird ab dem 12.03.2026 eingezogen.
"""


def test_nettorechnungsbetrag_ist_kein_brutto():
    erg = _parse(TELEKOM_4_STELLEN)
    f = erg.felder
    assert (f["gesamt_netto"], f["gesamt_ust"], f["gesamt_brutto"]) == ("4.19", "0.80", "4.99")
    assert not any("rechnungsbetrag" in p.beschreibung.lower() for p in erg.positionen)


SHOP_PUNKT_DEZIMAL = """\
Muster Shop GmbH
Musterstraße 1
12345 Musterstadt
Rechnung 84
Rechnungsdatum 08.08.2026
Beschreibung Artikelnummer Menge MwSt. Preis exkl. Preis inkl. Betrag exkl. Betrag inkl.
Funkmaus schwarz 46537128 1 19.00% 38.57 45.90 38.57 45.90
Gesamtbetrag 38.57 45.90
Gesamtbetrag enthält folgende Mehrwertsteuer:
MwSt. 19.00% 7.33
Rechnungsbetrag 45.90
"""


def test_gesamtbetrag_exkl_inkl_nimmt_brutto():
    f = _parse(SHOP_PUNKT_DEZIMAL).felder
    assert (f["gesamt_netto"], f["gesamt_ust"], f["gesamt_brutto"]) == ("38.57", "7.33", "45.90")
    assert f["ust_satz"] == "19"


BUEROMARKT_SUMMENZEILE = """\
RECHNUNG
Muster Büromarkt AG, Musterstraße 1, 12345 Musterstadt
Rechnung Nr. : 32
Datum : 02.02.2026
Pos Artikel-Nr. Menge ME PE S Einzelpreis Gesamtpreis
Bezeichnung EUR EUR
10 60418b 1 PAK 1 V 11,10 11,10
Packband braun
20 t 1 STK 1 V 2,99 2,99
Versandkosten pro Auftrag
Netto MwSt 19% Netto MwSt 7% Netto MwSt 0% Steuerfrei Gesamtwert
14,09 2,68 EUR 16,77
Die Forderung von 16,77 EUR ziehen wir per Lastschrift ein.
"""


def test_summenzeile_unter_steuerkopf_ist_summe_keine_position():
    erg = _parse(BUEROMARKT_SUMMENZEILE)
    f = erg.felder
    assert (f["gesamt_netto"], f["gesamt_ust"], f["gesamt_brutto"]) == ("14.09", "2.68", "16.77")
    assert sum(Decimal(p.netto) for p in erg.positionen) == Decimal("14.09")
    assert all(p.ust_satz == "19" for p in erg.positionen)


def test_bezeichnung_aus_zeile_unter_codezeile():
    """'10 60418b 1 PAK 1 V 11,10 11,10' - die Bezeichnung steht in der Folgezeile."""
    erg = _parse(BUEROMARKT_SUMMENZEILE)
    assert [(p.beschreibung, p.artikel_nr, p.einheit) for p in erg.positionen] == [
        ("Packband braun", "60418b", "PAK"),
        ("Versandkosten pro Auftrag", "t", "Stück"),
    ]


KASSENBON_OCR = """\
MUSTER-MARKT GMBH
Musterstraße 69
12345 Musterstadt
EUR
 TESAFILM 2,99 A
SUMME ___._ EUR 2,3
Geg. VISA EUR 2,99
Steuer % Netto Steuer Brutto
Az 19,0% 2,51 0,48 2,99
 Gesantbetrag 2,51 0,48 2,99
"""


def test_kassenbon_zahlungs_und_summenzeilen_keine_positionen():
    erg = _parse(KASSENBON_OCR, KassenbonParser)
    assert [p.beschreibung for p in erg.positionen] == ["TESAFILM"]
    assert erg.felder["gesamt_brutto"] == "2.99"


def test_menge_aus_gewicht_verdoppelt_nicht():
    """Einzelpreis = Zeilenbetrag → die Zahl am Anfang war keine Menge."""
    pos = _extrahiere_positionen("Artikelbezeichnung Menge Einzelpreis Gesamtpreis\n2 kg - Paket 6,19 € 6,19 €\n", "0")
    assert len(pos) == 1
    assert Decimal(pos[0].menge) * Decimal(pos[0].netto) == Decimal("6.19")


def test_menge_mit_passendem_einzelpreis():
    pos = _extrahiere_positionen("Bezeichnung Menge Einzelpreis Gesamtpreis\n3 Stk Kabel 2,00 6,00\n", "19")
    assert (Decimal(pos[0].menge), Decimal(pos[0].netto)) == (Decimal("3"), Decimal("2.00"))


def test_menge_ohne_einzelpreis_ergibt_zeilenbetrag():
    pos = _extrahiere_positionen("Bezeichnung Betrag\n4 Std Beratung 360,00\n", "19")
    assert (Decimal(pos[0].menge) * Decimal(pos[0].netto)).quantize(Decimal("0.01")) == Decimal("360.00")


def _summenwarnung(erg) -> bool:
    return any("Positionen ergeben" in w for w in erg.warnungen)


def test_keine_summenwarnung_wenn_positionen_passen():
    assert not _summenwarnung(_parse(BUEROMARKT_SUMMENZEILE))
    assert not _summenwarnung(_parse(KASSENBON_OCR, KassenbonParser))


def test_summenwarnung_wenn_positionen_nicht_passen():
    """Positionen bleiben erhalten (Issue #119), aber die Abweichung wird angezeigt."""
    text = BUEROMARKT_SUMMENZEILE.replace("20 t 1 STK 1 V 2,99 2,99", "20 t 1 STK 1 V 9,99 9,99")
    erg = _parse(text)
    assert len(erg.positionen) == 2
    assert _summenwarnung(erg)


TELKO_KOPF_OHNE_RECHTSFORM = """\
Musterfunk Kundenservice
Datum 17. März 2026
Kundennummer
Rechnungsnummer 1
Seite 11 vvoonn 11
Ihre Rechnung für März 2026
Sie haben gekündigt oder etwas an Ihrem Vertrag geändert? Das ist systembedingt hier vielleicht noch nicht berücksichtigt.
Rechnungsbetrag (netto, ohne 19% MwSt) 16,7984 €
MwSt. (19% = 3,19 €) 3,1917 €
Rechnungsbetrag (brutto, inkl. MwSt) 19,9901 €
Zu zahlender Gesamtbetrag 19,99 €
Der zu zahlende Gesamtbetrag von 19,99 € wird am 20.03.2026 per Lastschrift eingezogen.
""" + "Hinweistext\n" * 25 + """\
Musterfunk GmbH
Hausanschrift Musterplatz 1 D-12345 Musterstadt
Handelsregister Amtsgericht Musterstadt HRB 1 USt-IdNr. DE 123456789
"""


def test_telko_lieferant_aus_fusszeile_und_kein_fliesstext():
    """'e.K.' traf jedes 'ek' ('gekündigt') - Fließtext wurde Lieferant."""
    f = _parse(TELKO_KOPF_OHNE_RECHTSFORM).felder
    assert f["lieferant_name"] == "Musterfunk GmbH"


def test_telko_datum_belegnr_netto_ust():
    f = _parse(TELKO_KOPF_OHNE_RECHTSFORM).felder
    assert f["datum"] == "2026-03-17"
    assert f["externe_belegnr"] == "1"
    assert (f["gesamt_netto"], f["gesamt_ust"], f["gesamt_brutto"]) == ("16.80", "3.19", "19.99")
    assert f["ust_satz"] == "19"


def test_absenderzeile_mit_marke_co_und_spaltenrest():
    f = _parse("Musterfon-Team | c/o Muster GmbH | 12345 Musterstadt Sie erreichen uns täglich\n"
               "Rechnungsnummer R123\nSumme 5,00 €\n").felder
    assert f["lieferant_name"] == "Muster GmbH"


def test_lieferant_ohne_webadresse_und_ocr_reste():
    assert _parse("Muster Versand GmbH www.muster.de\nMusterweg 1\n12345 Musterstadt\nSumme 5,00 €\n").felder[
        "lieferant_name"] == "Muster Versand GmbH"
    assert _parse("«K MUSTER-MARKT GMBH xx\nMusterweg 1\n12345 Musterstadt\nSumme 5,00 €\n").felder[
        "lieferant_name"] == "MUSTER-MARKT GMBH"


def _pos(erg):
    return [(p.beschreibung, Decimal(p.menge), Decimal(p.netto), p.ust_satz) for p in erg.positionen]


def test_telko_positionen_satz_vor_netto():
    """otelo: '… 19% 16,7983' - 4 Nachkommastellen, Nullposition entfällt."""
    text = TELEKOM_4_STELLEN.replace(
        "Ihr Vorteil", "Nutzungskosten (s. Einzelverbindungsnachweis) 19% 0,0000\nIhr Vorteil")
    erg = _parse(text)
    assert _pos(erg) == [
        ("Allnet-Flat 01.03.2026 - 31.03.2026", 1, Decimal("16.7983"), "19"),
        ("Ihr Vorteil: Preisreduktion 01.03.2026 - 31.03.2026", 1, Decimal("-12.6050"), "19"),
    ]
    assert not _summenwarnung(erg)


def test_telko_positionen_spalten_ohne_kundenanschrift_und_wiederholung():
    """Vodafone: Zeitraum Menge Netto Satz Brutto; Anschrift rutscht vorn in die Zeile,
    die Vertragsübersicht wiederholt die Position ohne Bezeichnung."""
    text = TELKO_KOPF_OHNE_RECHTSFORM.replace("Hinweistext\n", (
        "Produkt Zeitraum Menge Nettopreis (€) MwSt. Bruttopreis (€)\n"
        "1 Paket Option 01.03.26-31.03.26 1 0,0000 19 % 0,00\n"
        "Musterstr. 4 Kabel 50 01.03.26-31.03.26 1 16,7984 19 % 19,99\n"
        "01.03.26-31.03.26 1 16,7984 19 % 19,99\n"
        "Zwischensumme: 16,7984 19,99\n"), 1)
    erg = _parse(text)
    assert _pos(erg) == [("Kabel 50", 1, Decimal("16.7984"), "19")]
    assert not _summenwarnung(erg)


def test_artikelzeile_mit_exkl_inkl_spalten():
    """Galaxus: Zeile mit Satz% und vier Beträgen ist keine USt-Aufschlüsselung."""
    erg = _parse(SHOP_PUNKT_DEZIMAL)
    assert _pos(erg) == [("Funkmaus schwarz", 1, Decimal("38.57"), "19")]
    assert erg.positionen[0].artikel_nr == "46537128"
    assert erg.positionen_modus == "netto"


def test_seite_und_absenderzeile_sind_keine_belegnr():
    text = "Rechnung\n\nMuster Post AG - 12345 Musterstadt\nRechnungsnummer\nSeite 1 von 2\nSumme 5,00 €\n"
    assert "externe_belegnr" not in _parse(text).felder


def test_rechtsform_ek_ev_nur_als_kuerzel():
    assert _parse("Blumen Muster e.K.\nMusterweg 1\n12345 Musterstadt\nSumme 5,00 €\n").felder[
        "lieferant_name"] == "Blumen Muster e.K."


def test_cid_text_gilt_als_unlesbar():
    assert _ist_unlesbar("(cid:20)(cid:24)(cid:23)(cid:26)\n(cid:23)(cid:48) (cid:62)")
    assert _ist_unlesbar("\x14\x18\x17\x1a\x1d\x1d\x19 \x14\x18\x17")
    assert not _ist_unlesbar("Rechnung Nr. 4711 vom 01.02.2026 (cid:3)")
