"""
Issue #467: Steuerkategorie in der E-Rechnung (ZUGFeRD/XRechnung-XML).

Vorher bekam jede 0-%-Position die Kategorie "Z" (Nullsatz). Richtig sind AE (Reverse Charge),
K (ig. Lieferung), G (Ausfuhr) und O (nicht steuerbar) mit Befreiungsgrund, dazu die
kategoriespezifischen Pflichtangaben. Alle Varianten wurden zusätzlich mit dem KoSIT-Validator
(XRechnung 3.0.2) geprüft - die Tests hier sichern die dabei geprüften Eigenschaften ab.
"""
import re
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import create_rechnung, finalisiere_rechnung
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate
from database.connection import Base
from database.models import Kunde, Rechnung, Unternehmen
from utils.zugferd import generate_zugferd_xml

UNT = {
    "firmenname": "Test GmbH", "strasse": "Teststraße", "hausnummer": "1", "plz": "12345", "ort": "Testort",
    "land": "DE", "ust_idnr": "DE123456789", "steuernummer": "12/345/67890", "email": "info@test.example",
    "telefon": "0123 456789", "iban": "DE89370400440532013000", "bic": "COBADEFFXXX",
    "ist_kleinunternehmer": False,
}


def _xml(flags: dict, land: str, ust_idnr: str | None, satz: str = "0", unt: dict | None = None) -> str:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(Unternehmen(firmenname="Test GmbH", strasse="Teststraße", hausnummer="1", plz="12345", ort="Testort",
                       ist_kleinunternehmer=False))
    kunde = Kunde(firmenname="Kunde Ltd", strasse="Main Street", hausnummer="5", plz="1000", ort="Stadt",
                  land=land, ust_idnr=ust_idnr, kundennummer="K-00001")
    db.add(kunde)
    db.commit()
    r = create_rechnung(RechnungCreate(
        typ="ausgang", datum=date(2026, 10, 20), kunde_id=kunde.id,
        positionen=[RechnungspositionCreate(beschreibung="Leistung", netto=Decimal("100"), ust_satz=Decimal(satz))],
        **flags,
    ), db)
    finalisiere_rechnung(r.id, db)
    return generate_zugferd_xml(db.query(Rechnung).filter(Rechnung.id == r.id).one(), unt or UNT).decode("utf-8")


def _kategorien(xml: str) -> set[str]:
    return set(re.findall(r"<ram:CategoryCode>([A-Z]+)<", xml))


@pytest.mark.parametrize("flags,land,ust_idnr,kategorie,grund", [
    ({"ist_reverse_charge": True}, "FR", "FR40303265045", "AE", "VATEX-EU-AE"),
    ({"ist_eu_lieferung": True}, "AT", "ATU12345678", "K", "VATEX-EU-IC"),
    ({"ist_ausfuhrlieferung": True}, "CH", None, "G", "VATEX-EU-G"),
    ({"ist_drittland_leistung": True}, "US", None, "O", "VATEX-EU-O"),
])
def test_kategorie_und_befreiungsgrund(flags, land, ust_idnr, kategorie, grund):
    xml = _xml(flags, land, ust_idnr)
    assert _kategorien(xml) == {kategorie}
    assert f"<ram:ExemptionReasonCode>{grund}<" in xml


@pytest.mark.parametrize("flags,land,ust_idnr", [
    ({"ist_reverse_charge": True}, "FR", "FR40303265045"),
    ({"ist_eu_lieferung": True}, "AT", "ATU12345678"),
])
def test_ust_idnr_beider_seiten_bei_ae_und_k(flags, land, ust_idnr):
    """BR-AE-02/03, BR-IC-02: USt-IdNr. von Verkäufer UND Käufer."""
    xml = _xml(flags, land, ust_idnr)
    assert 'schemeID="VA">DE123456789<' in xml
    assert f'schemeID="VA">{ust_idnr}<' in xml


def test_ig_lieferung_mit_lieferanschrift():
    """BR-IC-12 (Lieferland) und XRechnung BR-DE-10/11 (Ort, PLZ der Lieferanschrift)."""
    xml = _xml({"ist_eu_lieferung": True}, "AT", "ATU12345678")
    ship_to = re.search(r"<ram:ShipToTradeParty>.*?</ram:ShipToTradeParty>", xml, re.S).group(0)
    assert "<ram:CountryID>AT<" in ship_to
    assert "<ram:CityName>Stadt<" in ship_to and "<ram:PostcodeCode>1000<" in ship_to


def test_nicht_steuerbar_ohne_ustidnr_und_ohne_positionssatz():
    """BR-O-02: keine USt-IdNr.; BR-O-05: kein Satz an der Position; BR-CO-26: trotzdem
    Verkäuferkennung; XRechnung BR-DE-14: Satz 0 im Steuerblock der Rechnung."""
    xml = _xml({"ist_drittland_leistung": True}, "US", None)
    assert 'schemeID="VA"' not in xml
    position = re.search(r"<ram:IncludedSupplyChainTradeLineItem>.*?</ram:IncludedSupplyChainTradeLineItem>", xml, re.S).group(0)
    assert "RateApplicablePercent" not in position
    kopf = re.search(r"<ram:ApplicableHeaderTradeSettlement>.*</ram:ApplicableHeaderTradeSettlement>", xml, re.S).group(0)
    assert "<ram:RateApplicablePercent>0<" in kopf
    seller = re.search(r"<ram:SellerTradeParty>.*?</ram:SellerTradeParty>", xml, re.S).group(0)
    assert "<ram:ID>12/345/67890<" in seller  # Steuernummer als Verkäuferkennung (BT-29)


def test_normalfall_und_kleinunternehmer_unveraendert():
    assert _kategorien(_xml({}, "DE", None, satz="19")) == {"S"}
    xml_ku = _xml({}, "DE", None, unt=dict(UNT, ist_kleinunternehmer=True))
    assert _kategorien(xml_ku) == {"E"}
    assert "ExemptionReasonCode" not in xml_ku
