"""
Issue #598: lesbare Ansicht für E-Rechnungen (XRechnung CII/UBL, ZUGFeRD) als PDF.
"""
from datetime import date
from decimal import Decimal

import pytest

from utils.einvoice_ansicht import KeineEInvoice, ansicht_pdf, lies_einvoice

UBL = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
  xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
  xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0</cbc:CustomizationID>
  <cbc:ID>R-2026-17</cbc:ID>
  <cbc:IssueDate>2026-11-20</cbc:IssueDate>
  <cbc:DueDate>2026-12-04</cbc:DueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:Note>Bitte &lt;h:script&gt;alert(1)&lt;/h:script&gt; beachten</cbc:Note>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cbc:BuyerReference>991-12345-67</cbc:BuyerReference>
  <cac:InvoicePeriod><cbc:StartDate>2026-11-01</cbc:StartDate><cbc:EndDate>2026-11-30</cbc:EndDate></cac:InvoicePeriod>
  <cac:AccountingSupplierParty><cac:Party>
    <cbc:EndpointID schemeID="EM">info@lieferant.de</cbc:EndpointID>
    <cac:PostalAddress><cbc:StreetName>Hauptstraße 1</cbc:StreetName><cbc:CityName>Köln</cbc:CityName>
      <cbc:PostalZone>50667</cbc:PostalZone><cac:Country><cbc:IdentificationCode>DE</cbc:IdentificationCode></cac:Country></cac:PostalAddress>
    <cac:PartyTaxScheme><cbc:CompanyID>DE123456789</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
    <cac:PartyLegalEntity><cbc:RegistrationName>Lieferant GmbH</cbc:RegistrationName></cac:PartyLegalEntity>
    <cac:Contact><cbc:Name>Frau Muster</cbc:Name><cbc:Telephone>0221 123</cbc:Telephone></cac:Contact>
  </cac:Party></cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty><cac:Party>
    <cac:PostalAddress><cbc:StreetName>Amtsweg 2</cbc:StreetName><cbc:CityName>Bonn</cbc:CityName>
      <cbc:PostalZone>53111</cbc:PostalZone><cac:Country><cbc:IdentificationCode>DE</cbc:IdentificationCode></cac:Country></cac:PostalAddress>
    <cac:PartyLegalEntity><cbc:RegistrationName>Stadt Bonn</cbc:RegistrationName></cac:PartyLegalEntity>
  </cac:Party></cac:AccountingCustomerParty>
  <cac:PaymentMeans><cbc:PaymentMeansCode>58</cbc:PaymentMeansCode><cbc:PaymentID>R-2026-17</cbc:PaymentID>
    <cac:PayeeFinancialAccount><cbc:ID>DE02120300000000202051</cbc:ID><cbc:Name>Lieferant GmbH</cbc:Name></cac:PayeeFinancialAccount></cac:PaymentMeans>
  <cac:PaymentTerms><cbc:Note>Zahlbar innerhalb 14 Tagen</cbc:Note></cac:PaymentTerms>
  <cac:AllowanceCharge><cbc:ChargeIndicator>false</cbc:ChargeIndicator><cbc:AllowanceChargeReason>Rabatt</cbc:AllowanceChargeReason>
    <cbc:Amount currencyID="EUR">10.00</cbc:Amount><cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>19</cbc:Percent>
    <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory></cac:AllowanceCharge>
  <cac:TaxTotal><cbc:TaxAmount currencyID="EUR">17.10</cbc:TaxAmount>
    <cac:TaxSubtotal><cbc:TaxableAmount currencyID="EUR">90.00</cbc:TaxableAmount><cbc:TaxAmount currencyID="EUR">17.10</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>19</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory></cac:TaxSubtotal></cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">90.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">107.10</cbc:TaxInclusiveAmount>
    <cbc:AllowanceTotalAmount currencyID="EUR">10.00</cbc:AllowanceTotalAmount>
    <cbc:PayableAmount currencyID="EUR">ZAHLBETRAG</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:InvoiceLine><cbc:ID>1</cbc:ID><cbc:InvoicedQuantity unitCode="HUR">2</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
    <cac:Item><cbc:Name>Beratung</cbc:Name><cac:ClassifiedTaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>19</cbc:Percent>
      <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory></cac:Item>
    <cac:Price><cbc:PriceAmount currencyID="EUR">50.00</cbc:PriceAmount></cac:Price></cac:InvoiceLine>
</Invoice>"""


def _ubl(zahlbetrag="107.10") -> bytes:
    return UBL.replace("ZAHLBETRAG", zahlbetrag).encode()


def test_ubl_wird_gelesen():
    e = lies_einvoice(_ubl())
    assert e.format == "XRechnung (UBL)"
    assert (e.nummer, e.datum, e.faellig, e.art) == ("R-2026-17", "20.11.2026", "04.12.2026", "Rechnung")
    assert e.leitweg == "991-12345-67" and e.zeitraum == "01.11.2026 – 30.11.2026"
    assert e.verkaeufer.name == "Lieferant GmbH" and e.verkaeufer.ust_id == "DE123456789"
    assert "50667 Köln" in e.verkaeufer.adresse and "Frau Muster" in e.verkaeufer.kontakt
    assert e.kaeufer.name == "Stadt Bonn"
    assert e.positionen[0]["einheit"] == "Std." and e.positionen[0]["menge"] == Decimal("2")
    assert e.nachlaesse[0]["betrag"] == Decimal("10.00") and not e.nachlaesse[0]["zuschlag"]
    assert ("IBAN", "DE02120300000000202051") in e.zahlung
    assert e.summen["zahlbetrag"] == Decimal("107.10")
    assert e.hinweise == []


def test_rechenpruefung_findet_abweichung():
    e = lies_einvoice(_ubl("117.10"))
    assert any("Zahlbetrag" in h for h in e.hinweise)


def test_ubl_gutschrift():
    xml = (UBL.replace("<Invoice ", "<CreditNote ").replace("</Invoice>", "</CreditNote>")
           .replace("Invoice-2", "CreditNote-2").replace("InvoiceTypeCode>380", "CreditNoteTypeCode>381")
           .replace("</cbc:InvoiceTypeCode>", "</cbc:CreditNoteTypeCode>")
           .replace("cac:InvoiceLine", "cac:CreditNoteLine").replace("cbc:InvoicedQuantity", "cbc:CreditedQuantity")
           .replace("ZAHLBETRAG", "107.10"))
    e = lies_einvoice(xml.encode())
    assert e.art.startswith("Gutschrift") and len(e.positionen) == 1


def test_pdf_wird_erzeugt_und_skript_nur_als_text():
    pdf = ansicht_pdf(_ubl(), "Test")
    assert pdf[:4] == b"%PDF"
    assert b"/JavaScript" not in pdf and b"/JS" not in pdf


def test_eigene_xml_mit_rabatt_ohne_hinweise():
    from tests.test_zugferd_rechnungsrabatt import UNTERNEHMEN, _p, _rechnung
    from utils.zugferd import generate_zugferd_xml
    r = _rechnung([_p("333.33", "19"), _p("123.45", "7", menge="3")], rabatt_prozent=Decimal("7.5"))
    e = lies_einvoice(generate_zugferd_xml(r, UNTERNEHMEN))
    assert e.format.startswith("XRechnung") or e.format.startswith("CII")
    assert e.nachlaesse and all(n["grund"].startswith("Rabatt") for n in e.nachlaesse)
    assert e.hinweise == []
    assert ansicht_pdf(generate_zugferd_xml(r, UNTERNEHMEN))[:4] == b"%PDF"


@pytest.mark.parametrize("daten", [
    b"<kein>xml",
    b"<?xml version='1.0'?><Bestellung/>",
    b"%PDF-1.4 kein echtes pdf",
])
def test_keine_einvoice(daten):
    with pytest.raises(KeineEInvoice):
        lies_einvoice(daten)


def test_keine_externen_entitaeten(tmp_path):
    geheim = tmp_path / "geheim.txt"
    geheim.write_text("GEHEIM")
    xml = UBL.replace('<?xml version="1.0" encoding="UTF-8"?>',
                      f'<?xml version="1.0"?><!DOCTYPE Invoice [<!ENTITY x SYSTEM "file://{geheim}">]>') \
             .replace("<cbc:ID>R-2026-17</cbc:ID>", "<cbc:ID>&x;</cbc:ID>").replace("ZAHLBETRAG", "107.10")
    try:
        e = lies_einvoice(xml.encode())
    except KeineEInvoice:
        return
    assert "GEHEIM" not in e.nummer


def test_endpunkt_eigene_rechnung_archiviert_nichts(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import api.rechnungen as rmod
    from api.rechnungen import create_rechnung, eigene_einvoice_ansicht
    from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate
    from database.connection import Base
    from database.models import Kunde, Rechnung, Unternehmen

    monkeypatch.setattr(rmod, "APP_DATA_DIR", tmp_path)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    s.add(Unternehmen(firmenname="Testfirma", strasse="S", hausnummer="1", plz="12345", ort="Ort",
                      steuernummer="12/345/67890"))
    k = Kunde(firmenname="Kunde GmbH", strasse="K", hausnummer="2", plz="54321", ort="Stadt")
    s.add(k)
    s.commit()
    resp = create_rechnung(RechnungCreate(
        typ="ausgang", dokument_typ="Rechnung", datum=date(2026, 11, 1), ist_entwurf=False, kunde_id=k.id,
        positionen=[RechnungspositionCreate(beschreibung="Leistung", menge=Decimal("1"), netto=Decimal("100"),
                                            ust_satz=Decimal("19"))],
    ), s)
    antwort = eigene_einvoice_ansicht(resp.id, s)
    assert antwort.media_type == "application/pdf"
    assert antwort.headers["content-disposition"].startswith("inline")
    assert antwort.body[:4] == b"%PDF"
    assert s.get(Rechnung, resp.id).original_xml_pfad is None


def test_endpunkt_import_temp(tmp_path, monkeypatch):
    import uuid
    from fastapi import HTTPException
    import api.rechnungen as rmod
    monkeypatch.setattr(rmod, "TEMP_DIR", tmp_path)
    token = str(uuid.uuid4())
    (tmp_path / f"{token}.xml").write_bytes(_ubl())
    antwort = rmod.temp_einvoice_ansicht(token)
    assert antwort.body[:4] == b"%PDF"
    (tmp_path / f"{token}.xml").write_bytes(b"<?xml version='1.0'?><Bestellung/>")
    with pytest.raises(HTTPException) as e:
        rmod.temp_einvoice_ansicht(token)
    assert e.value.status_code == 422
    with pytest.raises(HTTPException):
        rmod.temp_einvoice_ansicht("../geheim")
