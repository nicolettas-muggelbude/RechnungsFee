"""
Rechnungsrabatt in der E-Rechnung (ZUGFeRD/XRechnung): fehlte bisher ganz – Positionen und
Summen ohne Rabatt, die XML wich vom PDF und vom gespeicherten Betrag ab. Jetzt als Abschlag
auf Belegebene (BG-20) je Steuersatz, Summen exakt wie in der Rechnung.
"""
import re
from datetime import date
from decimal import Decimal

import pytest
from lxml import etree
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import _berechne_rechnung
from database.connection import Base
from database.models import Rechnung, Rechnungsposition
from utils.zugferd import generate_zugferd_xml

UNTERNEHMEN = {
    "firmenname": "Testfirma GmbH", "strasse": "Teststraße", "hausnummer": "1", "plz": "12345",
    "ort": "Teststadt", "land": "DE", "steuernummer": "12/345/67890", "ust_idnr": "",
    "ist_kleinunternehmer": False,
}
NS = {"ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"}


def _rechnung(positionen, rabatt_prozent=Decimal("0"), rabatt_betrag=None, modus="netto", ku=False,
              drittland=False):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    summen = _berechne_rechnung(positionen, modus, rabatt_prozent, rabatt_betrag, ku, drittland)
    r = Rechnung(
        typ="ausgang", dokument_typ="Rechnung", rechnungsnummer="RE-1", datum=date(2026, 11, 1),
        netto_gesamt=summen.netto_gesamt, ust_gesamt=summen.ust_gesamt, brutto_gesamt=summen.brutto_gesamt,
        rabatt_prozent=rabatt_prozent, rabatt_betrag=rabatt_betrag, eingabemodus=modus,
        ist_drittland_leistung=drittland, ist_entwurf=False,
    )
    db.add(r)
    db.flush()
    for i, (p, erg) in enumerate(zip(positionen, summen.positionen), start=1):
        db.add(Rechnungsposition(
            rechnung_id=r.id, position_nr=i, beschreibung=f"Pos {i}", menge=p.menge, einheit="Stück",
            netto=p.netto, ust_satz=erg.ust_satz, ust_betrag=erg.ust_betrag, brutto=erg.brutto,
            abschlag_rechnung_id=getattr(p, "abschlag_rechnung_id", None),
        ))
    db.commit()
    db.refresh(r)
    return r


def _p(netto, satz="19", menge="1", abschlag=None):
    from types import SimpleNamespace
    return SimpleNamespace(netto=Decimal(netto), menge=Decimal(menge), ust_satz=Decimal(satz),
                           abschlag_rechnung_id=abschlag)


def _wert(xml: bytes, tag: str) -> Decimal:
    baum = etree.fromstring(xml)
    knoten = baum.find(f".//ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:{tag}", NS)
    return Decimal(knoten.text)


def _summen_passen(xml: bytes, r: Rechnung):
    assert _wert(xml, "TaxBasisTotalAmount") == r.netto_gesamt
    assert _wert(xml, "TaxTotalAmount") == r.ust_gesamt
    assert _wert(xml, "GrandTotalAmount") == r.brutto_gesamt
    assert _wert(xml, "LineTotalAmount") - _wert(xml, "AllowanceTotalAmount") == _wert(xml, "TaxBasisTotalAmount")
    # je Steuersatz: Basis = Positionen - Abschlag (BR-S-08)
    baum = etree.fromstring(xml)
    basis = sum(Decimal(e.text) for e in baum.findall(".//ram:ApplicableTradeTax/ram:BasisAmount", NS))
    assert basis == r.netto_gesamt


def test_prozentrabatt_ein_satz():
    r = _rechnung([_p("1000")], rabatt_prozent=Decimal("10"))
    xml = generate_zugferd_xml(r, UNTERNEHMEN)
    assert r.netto_gesamt == Decimal("900.00")
    assert _wert(xml, "LineTotalAmount") == Decimal("1000.00")
    assert _wert(xml, "AllowanceTotalAmount") == Decimal("100.00")
    _summen_passen(xml, r)
    baum = etree.fromstring(xml)
    ac = baum.find(".//ram:SpecifiedTradeAllowanceCharge", NS)
    assert ac.find("ram:ChargeIndicator/*", NS).text == "false"
    assert ac.find("ram:Reason", NS).text == "Rabatt 10 %"
    assert ac.find("ram:CategoryTradeTax/ram:RateApplicablePercent", NS).text == "19"


@pytest.mark.parametrize("modus", ["netto", "brutto"])
def test_prozentrabatt_zwei_saetze(modus):
    r = _rechnung([_p("333.33", "19"), _p("123.45", "7", menge="3")], rabatt_prozent=Decimal("7.5"), modus=modus)
    xml = generate_zugferd_xml(r, UNTERNEHMEN)
    _summen_passen(xml, r)
    assert len(re.findall(r"<ram:SpecifiedTradeAllowanceCharge>", xml.decode())) == 2


def test_festbetrag_rabatt():
    r = _rechnung([_p("1000")], rabatt_betrag=Decimal("119"))
    xml = generate_zugferd_xml(r, UNTERNEHMEN)
    assert r.brutto_gesamt == Decimal("1071.00")
    assert _wert(xml, "AllowanceTotalAmount") == Decimal("100.00")
    _summen_passen(xml, r)


def test_ohne_rabatt_kein_abschlag():
    r = _rechnung([_p("1000")])
    xml = generate_zugferd_xml(r, UNTERNEHMEN).decode()
    assert "SpecifiedTradeAllowanceCharge" not in xml
    assert "<ram:AllowanceTotalAmount>0.00</ram:AllowanceTotalAmount>" in xml


def test_schlussrechnung_mit_rabatt_und_abschlag():
    r = _rechnung([_p("10000"), _p("2700", abschlag=1, menge="-1")], rabatt_prozent=Decimal("10"))
    assert r.netto_gesamt == Decimal("6300.00")
    xml = generate_zugferd_xml(r, UNTERNEHMEN)
    # Leistung 10.000, Rabatt 1.000, Basis 9.000; der Abschlag geht als Vorauszahlung ab
    assert _wert(xml, "LineTotalAmount") == Decimal("10000.00")
    assert _wert(xml, "AllowanceTotalAmount") == Decimal("1000.00")
    assert _wert(xml, "TaxBasisTotalAmount") == Decimal("9000.00")
    assert _wert(xml, "GrandTotalAmount") == Decimal("10710.00")
    assert _wert(xml, "DuePayableAmount") == r.brutto_gesamt


def test_drittland_rabatt_ohne_steuersatz():
    r = _rechnung([_p("1000")], rabatt_prozent=Decimal("10"), drittland=True)
    xml = generate_zugferd_xml(r, UNTERNEHMEN)
    baum = etree.fromstring(xml)
    cat = baum.find(".//ram:SpecifiedTradeAllowanceCharge/ram:CategoryTradeTax", NS)
    assert cat.find("ram:CategoryCode", NS).text == "O"
    assert cat.find("ram:RateApplicablePercent", NS) is None
    _summen_passen(xml, r)
