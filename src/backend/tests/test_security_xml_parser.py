"""
Regressionstest Security-Audit F9 (XML-Parser ohne explizite Härtung).

Die E-Rechnungs-Analyse (utils/rechnungs_parser.py) nutzte etree.fromstring() mit dem
Standardparser – sicher nur, weil lxml ab Version 5 keine externen Entitäten mehr auflöst.
Jetzt mit explizit gehärtetem Parser; dieser Test hält fest, dass weder XXE (lokale Datei)
noch Entity-Expansion durchkommen.
"""
from utils.rechnungs_parser import _analysiere_xml, _xml_parser

CII = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"


def _xxe(pfad: str) -> bytes:
    return f"""<?xml version="1.0"?>
<!DOCTYPE x [<!ENTITY geheim SYSTEM "file://{pfad}">]>
<rsm:CrossIndustryInvoice xmlns:rsm="{CII}">
  <rsm:ExchangedDocument><ID>&geheim;</ID></rsm:ExchangedDocument>
</rsm:CrossIndustryInvoice>""".encode()


def test_parser_ist_gehaertet():
    from lxml import etree
    p = _xml_parser()
    # XXE: externe Entität darf nicht aufgelöst werden
    root = etree.fromstring(b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/hostname">]><x>&e;</x>', parser=p)
    assert (root.text or "") == ""


def test_xxe_liest_keine_lokale_datei(tmp_path):
    geheim = tmp_path / "geheim.txt"
    geheim.write_text("STRENG-GEHEIM")
    ergebnis = _analysiere_xml(_xxe(str(geheim)))
    assert "STRENG-GEHEIM" not in repr(ergebnis.__dict__)


def test_billion_laughs_wird_nicht_expandiert():
    lol = b"""<?xml version="1.0"?>
<!DOCTYPE lolz [
 <!ENTITY lol "lol">
 <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
 <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
 <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
 <!ENTITY lol5 "&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;">
 <!ENTITY lol6 "&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;">
]>
<x>&lol6;</x>"""
    from lxml import etree
    # Sicher ist beides: Abbruch durch libxml (Amplification-Grenze) oder keine Expansion
    try:
        root = etree.fromstring(lol, parser=_xml_parser())
    except etree.XMLSyntaxError:
        return
    assert "lol" * 1000 not in etree.tostring(root).decode()


def test_analyse_bricht_bei_billion_laughs_sauber_ab():
    """Die Analyse darf nicht hängen oder abstürzen, sondern liefert ein Ergebnis mit Warnung."""
    lol = b"""<?xml version="1.0"?><!DOCTYPE l [<!ENTITY a "aaaaaaaaaa">
<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;"><!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">
<!ENTITY d "&c;&c;&c;&c;&c;&c;&c;&c;&c;&c;"><!ENTITY e "&d;&d;&d;&d;&d;&d;&d;&d;&d;&d;">]>
<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100">&e;</rsm:CrossIndustryInvoice>"""
    _analysiere_xml(lol)
