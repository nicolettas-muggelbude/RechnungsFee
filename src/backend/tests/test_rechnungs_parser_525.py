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


def test_cid_text_gilt_als_unlesbar():
    assert _ist_unlesbar("(cid:20)(cid:24)(cid:23)(cid:26)\n(cid:23)(cid:48) (cid:62)")
    assert _ist_unlesbar("\x14\x18\x17\x1a\x1d\x1d\x19 \x14\x18\x17")
    assert not _ist_unlesbar("Rechnung Nr. 4711 vom 01.02.2026 (cid:3)")
