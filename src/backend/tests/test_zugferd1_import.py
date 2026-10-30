"""
Issue #479: Eingangsrechnungen im alten Format ZUGFeRD 1.0 (rsm:CrossIndustryDocument, 2014)
einlesen - bisher endete der Import mit „Unbekanntes XML-Root-Element“.
Aufbau angelehnt an das COMFORT-Beispiel der ZUGFeRD-1.0-Spezifikation.
"""
from utils.rechnungs_parser import analysiere_datei

ZUGFERD1 = """<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryDocument xmlns:rsm="urn:ferd:CrossIndustryDocument:invoice:1p0"
    xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:12"
    xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:15">
  <rsm:SpecifiedExchangedDocumentContext>
    <ram:GuidelineSpecifiedDocumentContextParameter>
      <ram:ID>urn:ferd:CrossIndustryDocument:invoice:1p0:comfort</ram:ID>
    </ram:GuidelineSpecifiedDocumentContextParameter>
  </rsm:SpecifiedExchangedDocumentContext>
  <rsm:HeaderExchangedDocument>
    <ram:ID>471102</ram:ID>
    <ram:Name>RECHNUNG</ram:Name>
    <ram:TypeCode>380</ram:TypeCode>
    <ram:IssueDateTime><udt:DateTimeString format="102">20261028</udt:DateTimeString></ram:IssueDateTime>
  </rsm:HeaderExchangedDocument>
  <rsm:SpecifiedSupplyChainTradeTransaction>
    <ram:ApplicableSupplyChainTradeAgreement>
      <ram:SellerTradeParty>
        <ram:Name>Lieferant GmbH</ram:Name>
        <ram:PostalTradeAddress>
          <ram:PostcodeCode>80333</ram:PostcodeCode>
          <ram:LineOne>Lieferantenstraße 20</ram:LineOne>
          <ram:CityName>München</ram:CityName>
          <ram:CountryID>DE</ram:CountryID>
        </ram:PostalTradeAddress>
        <ram:SpecifiedTaxRegistration><ram:ID schemeID="VA">DE123456789</ram:ID></ram:SpecifiedTaxRegistration>
      </ram:SellerTradeParty>
      <ram:BuyerTradeParty><ram:Name>Kunden AG</ram:Name></ram:BuyerTradeParty>
    </ram:ApplicableSupplyChainTradeAgreement>
    <ram:ApplicableSupplyChainTradeDelivery>
      <ram:ActualDeliverySupplyChainEvent>
        <ram:OccurrenceDateTime><udt:DateTimeString format="102">20261025</udt:DateTimeString></ram:OccurrenceDateTime>
      </ram:ActualDeliverySupplyChainEvent>
    </ram:ApplicableSupplyChainTradeDelivery>
    <ram:ApplicableSupplyChainTradeSettlement>
      <ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>
      <ram:ApplicableTradeTax>
        <ram:CalculatedAmount currencyID="EUR">38.00</ram:CalculatedAmount>
        <ram:TypeCode>VAT</ram:TypeCode>
        <ram:BasisAmount currencyID="EUR">200.00</ram:BasisAmount>
        <ram:CategoryCode>S</ram:CategoryCode>
        <ram:ApplicablePercent>19.00</ram:ApplicablePercent>
      </ram:ApplicableTradeTax>
      <ram:SpecifiedTradePaymentTerms>
        <ram:DueDateDateTime><udt:DateTimeString format="102">20261127</udt:DateTimeString></ram:DueDateDateTime>
      </ram:SpecifiedTradePaymentTerms>
      <ram:SpecifiedTradeSettlementMonetarySummation>
        <ram:LineTotalAmount currencyID="EUR">200.00</ram:LineTotalAmount>
        <ram:TaxBasisTotalAmount currencyID="EUR">200.00</ram:TaxBasisTotalAmount>
        <ram:TaxTotalAmount currencyID="EUR">38.00</ram:TaxTotalAmount>
        <ram:GrandTotalAmount currencyID="EUR">238.00</ram:GrandTotalAmount>
        <ram:DuePayableAmount currencyID="EUR">238.00</ram:DuePayableAmount>
      </ram:SpecifiedTradeSettlementMonetarySummation>
    </ram:ApplicableSupplyChainTradeSettlement>
    <ram:IncludedSupplyChainTradeLineItem>
      <ram:AssociatedDocumentLineDocument><ram:LineID>1</ram:LineID></ram:AssociatedDocumentLineDocument>
      <ram:SpecifiedSupplyChainTradeAgreement>
        <ram:NetPriceProductTradePrice><ram:ChargeAmount currencyID="EUR">50.00</ram:ChargeAmount></ram:NetPriceProductTradePrice>
      </ram:SpecifiedSupplyChainTradeAgreement>
      <ram:SpecifiedSupplyChainTradeDelivery>
        <ram:BilledQuantity unitCode="C62">4.0000</ram:BilledQuantity>
      </ram:SpecifiedSupplyChainTradeDelivery>
      <ram:SpecifiedSupplyChainTradeSettlement>
        <ram:ApplicableTradeTax>
          <ram:TypeCode>VAT</ram:TypeCode>
          <ram:CategoryCode>S</ram:CategoryCode>
          <ram:ApplicablePercent>19.00</ram:ApplicablePercent>
        </ram:ApplicableTradeTax>
        <ram:SpecifiedTradeSettlementMonetarySummation>
          <ram:LineTotalAmount currencyID="EUR">200.00</ram:LineTotalAmount>
        </ram:SpecifiedTradeSettlementMonetarySummation>
      </ram:SpecifiedSupplyChainTradeSettlement>
      <ram:SpecifiedTradeProduct><ram:Name>Trennblätter A4</ram:Name></ram:SpecifiedTradeProduct>
    </ram:IncludedSupplyChainTradeLineItem>
  </rsm:SpecifiedSupplyChainTradeTransaction>
</rsm:CrossIndustryDocument>
""".encode("utf-8")


def test_zugferd1_wird_erkannt_und_gelesen():
    erg = analysiere_datei("ZUGFeRD-invoice.xml", ZUGFERD1)
    assert erg.format == "zugferd"
    assert not any("Unbekanntes XML-Root-Element" in w for w in erg.warnungen)
    f = erg.felder
    assert f["externe_belegnr"] == "471102"
    assert f["datum"] == "2026-10-28"
    assert f["faellig_am"] == "2026-11-27"
    assert f["lieferant_name"] == "Lieferant GmbH"
    assert f["lieferant_ust_id"] == "DE123456789"
    assert f["lieferant_plz"] == "80333"
    assert f["lieferant_ort"] == "München"
    assert str(f["gesamt_netto"]) in ("200.00", "200")
    assert str(f["gesamt_ust"]) in ("38.00", "38")
    assert str(f["gesamt_brutto"]) in ("238.00", "238")
    assert str(f["ust_satz"]).startswith("19")


def test_zugferd1_positionen():
    pos = analysiere_datei("rechnung.xml", ZUGFERD1).positionen
    assert len(pos) == 1
    assert "Trennblätter A4" in pos[0].beschreibung
    assert "4" in pos[0].beschreibung  # Menge wandert in die Beschreibung (wie bei 2.x)
    assert str(pos[0].netto) in ("200.00", "200")
    assert str(pos[0].ust_satz).startswith("19")
