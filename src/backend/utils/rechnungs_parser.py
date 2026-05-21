"""
ZUGFeRD / XRechnung Parsing für Eingangsrechnungs-Import (Stufe 2).

Unterstützte Formate:
  - PDF mit eingebettetem ZUGFeRD-XML  (factur-x)
  - Standalone XRechnung-XML           (lxml)
  - Normales PDF                        → format='pdf', keine Felder
"""

from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Optional
import re


# ---------------------------------------------------------------------------
# Ergebnis-Datenklassen
# ---------------------------------------------------------------------------

@dataclass
class AnalysePosition:
    beschreibung: str
    menge: str = "1.000"
    einheit: str = "Stück"
    netto: str = "0.00"
    ust_satz: str = "0"


@dataclass
class AnalyseErgebnis:
    format: str                          # zugferd | xrechnung | pdf
    felder: dict = field(default_factory=dict)
    positionen: list[AnalysePosition] = field(default_factory=list)
    warnungen: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _d(text: Optional[str]) -> Optional[str]:
    """XML-Betrag → '1234.56'-String oder None."""
    if not text:
        return None
    try:
        return str(Decimal(text.strip()).quantize(Decimal("0.01")))
    except InvalidOperation:
        return None


def _menge(text: Optional[str]) -> str:
    if not text:
        return "1.000"
    try:
        return str(Decimal(text.strip()).quantize(Decimal("0.001")))
    except InvalidOperation:
        return "1.000"


_EINHEIT_MAP = {
    "C62": "Stück", "HUR": "Std", "DAY": "Tag", "WEE": "Woche",
    "MON": "Monat", "MIN": "Min", "KGM": "kg", "GRM": "g",
    "LTR": "l", "MLT": "ml", "MTR": "m", "MTK": "m²", "MTQ": "m³",
    "KMT": "km", "LS": "Pauschal",
}


def _einheit(code: Optional[str]) -> str:
    return _EINHEIT_MAP.get(code or "", "Stück")


def _ns(root):
    """Gibt das Namespace-Dict für lxml zurück."""
    return root.nsmap


def _x(elem, xpath: str, ns: dict) -> Optional[str]:
    """XPath mit Namespace, gibt ersten Textwert oder None zurück."""
    results = elem.xpath(xpath, namespaces=ns)
    if not results:
        return None
    node = results[0]
    return node.text.strip() if hasattr(node, "text") and node.text else str(node).strip() or None


# ---------------------------------------------------------------------------
# ZUGFeRD / Factur-X / XRechnung – CII-Format (Cross-Industry Invoice)
# ---------------------------------------------------------------------------

def _parse_cii_xml(xml_bytes: bytes) -> AnalyseErgebnis:
    from lxml import etree

    root = etree.fromstring(xml_bytes)
    ns = {
        "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
        "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
        "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    }

    warnungen: list[str] = []
    felder: dict = {}
    positionen: list[AnalysePosition] = []

    # Format-Typ aus GuidelineSpecifiedDocumentContextParameter
    profil = _x(root, "//ram:GuidelineSpecifiedDocumentContextParameter/ram:ID", ns) or ""
    if "xrechnung" in profil.lower():
        fmt = "xrechnung"
    else:
        fmt = "zugferd"

    # Rechnungsnummer (BT-1)
    nr = _x(root, "//rsm:ExchangedDocument/ram:ID", ns)
    if nr:
        felder["externe_belegnr"] = nr
    else:
        warnungen.append("BT-1: Rechnungsnummer fehlt")

    # Datum (BT-2)
    datum_raw = _x(root, "//rsm:ExchangedDocument/ram:IssueDateTime/udt:DateTimeString", ns)
    if datum_raw and len(datum_raw) == 8:
        felder["datum"] = f"{datum_raw[:4]}-{datum_raw[4:6]}-{datum_raw[6:8]}"

    # Fälligkeitsdatum (BT-9)
    faellig_raw = _x(root, "//ram:SpecifiedTradePaymentTerms/ram:DueDateDateTime/udt:DateTimeString", ns)
    if faellig_raw and len(faellig_raw) == 8:
        felder["faellig_am"] = f"{faellig_raw[:4]}-{faellig_raw[4:6]}-{faellig_raw[6:8]}"
    else:
        warnungen.append("BT-9: Fälligkeitsdatum fehlt")

    # Lieferant (BT-27)
    lieferant_name = _x(root, "//ram:SellerTradeParty/ram:Name", ns)
    if lieferant_name:
        felder["lieferant_name"] = lieferant_name
    else:
        warnungen.append("BT-27: Lieferantenname fehlt")

    felder["lieferant_ust_id"] = _x(root, "//ram:SellerTradeParty/ram:SpecifiedTaxRegistration/ram:ID", ns)
    felder["lieferant_email"] = _x(root, "//ram:SellerTradeParty/ram:URIUniversalCommunication/ram:URIID", ns)

    # Adresse Lieferant
    felder["lieferant_strasse"] = _x(root, "//ram:SellerTradeParty/ram:PostalTradeAddress/ram:LineOne", ns)
    felder["lieferant_plz"] = _x(root, "//ram:SellerTradeParty/ram:PostalTradeAddress/ram:PostcodeCode", ns)
    felder["lieferant_ort"] = _x(root, "//ram:SellerTradeParty/ram:PostalTradeAddress/ram:CityName", ns)

    # Gesamtbeträge (BT-109 / BT-110 / BT-112)
    netto = _d(_x(root, "//ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:TaxBasisTotalAmount", ns))
    ust   = _d(_x(root, "//ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:TaxTotalAmount", ns))
    brutto = _d(_x(root, "//ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:GrandTotalAmount", ns))

    if netto:  felder["gesamt_netto"]  = netto
    if ust:    felder["gesamt_ust"]    = ust
    if brutto: felder["gesamt_brutto"] = brutto
    if not brutto:
        warnungen.append("BT-112: Gesamtbetrag (brutto) fehlt")

    # Steuersatz (erster gefundener)
    ust_satz = _x(root, "//ram:ApplicableTradeTax/ram:RateApplicablePercent", ns)
    if ust_satz:
        felder["ust_satz"] = ust_satz

    # Positionen
    for item in root.xpath("//ram:IncludedSupplyChainTradeLineItem", namespaces=ns):
        beschr = _x(item, "ram:SpecifiedTradeProduct/ram:Name", ns) or "Position"
        menge_raw = _x(item, "ram:SpecifiedLineTradeDelivery/ram:BilledQuantity", ns)
        einheit_code = None
        menge_elems = item.xpath("ram:SpecifiedLineTradeDelivery/ram:BilledQuantity", namespaces=ns)
        if menge_elems:
            einheit_code = menge_elems[0].get("unitCode")

        netto_pos = _d(_x(item, "ram:SpecifiedLineTradeSettlement/ram:SpecifiedTradeSettlementLineMonetarySummation/ram:LineTotalAmount", ns))
        ust_pos   = _x(item, "ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax/ram:RateApplicablePercent", ns)

        positionen.append(AnalysePosition(
            beschreibung=beschr,
            menge=_menge(menge_raw),
            einheit=_einheit(einheit_code),
            netto=netto_pos or "0.00",
            ust_satz=ust_pos or ust_satz or "0",
        ))

    # Fallback: eine Position aus Gesamtbetrag wenn keine Positionen
    if not positionen and netto:
        positionen.append(AnalysePosition(
            beschreibung=lieferant_name or "Import",
            netto=netto,
            ust_satz=ust_satz or "0",
        ))

    # None-Werte entfernen
    felder = {k: v for k, v in felder.items() if v is not None}

    return AnalyseErgebnis(format=fmt, felder=felder, positionen=positionen, warnungen=warnungen)


# ---------------------------------------------------------------------------
# UBL-Format (manche XRechnungen nutzen UBL statt CII)
# ---------------------------------------------------------------------------

def _parse_ubl_xml(xml_bytes: bytes) -> AnalyseErgebnis:
    from lxml import etree

    root = etree.fromstring(xml_bytes)
    ns = {
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    }

    warnungen: list[str] = []
    felder: dict = {}
    positionen: list[AnalysePosition] = []

    nr = _x(root, "//cbc:ID", ns)
    if nr:
        felder["externe_belegnr"] = nr

    datum = _x(root, "//cbc:IssueDate", ns)
    if datum:
        felder["datum"] = datum

    faellig = _x(root, "//cac:PaymentMeans/cbc:PaymentDueDate", ns)
    if faellig:
        felder["faellig_am"] = faellig
    else:
        warnungen.append("BT-9: Fälligkeitsdatum fehlt")

    lieferant_name = _x(root, "//cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name", ns)
    if lieferant_name:
        felder["lieferant_name"] = lieferant_name
    else:
        warnungen.append("BT-27: Lieferantenname fehlt")

    felder["lieferant_ust_id"] = _x(root, "//cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID", ns)
    felder["lieferant_email"] = _x(root, "//cac:AccountingSupplierParty/cac:Party/cac:Contact/cbc:ElectronicMail", ns)
    felder["lieferant_strasse"] = _x(root, "//cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:StreetName", ns)
    felder["lieferant_plz"] = _x(root, "//cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:PostalZone", ns)
    felder["lieferant_ort"] = _x(root, "//cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cbc:CityName", ns)

    brutto = _d(_x(root, "//cac:LegalMonetaryTotal/cbc:PayableAmount", ns))
    netto  = _d(_x(root, "//cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount", ns))
    ust    = _d(_x(root, "//cac:TaxTotal/cbc:TaxAmount", ns))
    ust_satz = _x(root, "//cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:Percent", ns)

    if netto:  felder["gesamt_netto"]  = netto
    if ust:    felder["gesamt_ust"]    = ust
    if brutto: felder["gesamt_brutto"] = brutto
    if ust_satz: felder["ust_satz"]   = ust_satz
    if not brutto:
        warnungen.append("BT-112: Gesamtbetrag (brutto) fehlt")

    for item in root.xpath("//cac:InvoiceLine", namespaces=ns):
        beschr = _x(item, "cac:Item/cbc:Name", ns) or "Position"
        menge_raw = _x(item, "cbc:InvoicedQuantity", ns)
        einheit_code = None
        menge_elems = item.xpath("cbc:InvoicedQuantity", namespaces=ns)
        if menge_elems:
            einheit_code = menge_elems[0].get("unitCode")
        netto_pos = _d(_x(item, "cbc:LineExtensionAmount", ns))
        ust_pos   = _x(item, "cac:Item/cac:ClassifiedTaxCategory/cbc:Percent", ns)

        positionen.append(AnalysePosition(
            beschreibung=beschr,
            menge=_menge(menge_raw),
            einheit=_einheit(einheit_code),
            netto=netto_pos or "0.00",
            ust_satz=ust_pos or ust_satz or "0",
        ))

    if not positionen and netto:
        positionen.append(AnalysePosition(
            beschreibung=lieferant_name or "Import",
            netto=netto,
            ust_satz=ust_satz or "0",
        ))

    felder = {k: v for k, v in felder.items() if v is not None}
    return AnalyseErgebnis(format="xrechnung", felder=felder, positionen=positionen, warnungen=warnungen)


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------

def analysiere_datei(dateiname: str, inhalt: bytes) -> AnalyseErgebnis:
    """
    Erkennt das Format und gibt das Analyse-Ergebnis zurück.
    Wirft keine Exception – Fehler landen in warnungen.
    """
    lower = dateiname.lower()

    # 1. Standalone XML
    if lower.endswith(".xml"):
        return _analysiere_xml(inhalt)

    # 2. PDF – ZUGFeRD-XML extrahieren
    if lower.endswith(".pdf") or inhalt[:4] == b"%PDF":
        try:
            from facturx import get_facturx_xml_from_pdf
            result = get_facturx_xml_from_pdf(inhalt)
            # factur-x gibt (dateiname, xml_bytes) zurück
            xml_bytes = result[1] if isinstance(result, tuple) else result
            if xml_bytes:
                ergebnis = _analysiere_xml(xml_bytes)
                if ergebnis.format == "xrechnung":
                    ergebnis.format = "xrechnung"
                else:
                    ergebnis.format = "zugferd"
                return ergebnis
        except Exception:
            pass
        return AnalyseErgebnis(format="pdf", warnungen=["Kein eingebettetes XML gefunden – bitte Felder manuell ausfüllen."])

    return AnalyseErgebnis(format="unbekannt", warnungen=["Dateiformat nicht unterstützt."])


def _analysiere_xml(xml_bytes: bytes) -> AnalyseErgebnis:
    """Erkennt CII vs. UBL anhand des Root-Elements."""
    try:
        from lxml import etree
        root = etree.fromstring(xml_bytes)
        tag = root.tag or ""
        if "CrossIndustryInvoice" in tag:
            return _parse_cii_xml(xml_bytes)
        elif "Invoice" in tag:
            return _parse_ubl_xml(xml_bytes)
        else:
            return AnalyseErgebnis(format="xml", warnungen=[f"Unbekanntes XML-Root-Element: {tag}"])
    except Exception as e:
        return AnalyseErgebnis(format="xml", warnungen=[f"XML-Parsing fehlgeschlagen: {e}"])
