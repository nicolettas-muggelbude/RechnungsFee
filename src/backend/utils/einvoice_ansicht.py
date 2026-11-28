"""Lesbare Ansicht einer E-Rechnung (Issue #598).

XRechnung/ZUGFeRD-XML (CII, auch ZUGFeRD 1.0) und XRechnung UBL (Invoice/CreditNote) werden
ausgelesen und als übersichtliches PDF dargestellt – zum Prüfen der Angaben, ohne fremde
Inhalte als HTML auszuführen (Security-Audit F2): alles landet nur als Text im PDF.

Dazu eine einfache Rechenprüfung (Positionen, Nachlässe, Steuer, Summen). Sie ersetzt keine
Prüfung nach den offiziellen XRechnung-Regeln (KoSIT-Validator).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Optional

NS_CII = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}
NS_UBL = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}

DOKUMENTART = {
    "380": "Rechnung", "381": "Gutschrift / Rechnungskorrektur", "384": "Korrigierte Rechnung",
    "389": "Gutschrift (vom Leistungsempfänger ausgestellt)", "326": "Teilrechnung",
    "386": "Vorauszahlungsrechnung", "875": "Teilrechnung (Bau)", "876": "Teilschlussrechnung (Bau)",
    "877": "Schlussrechnung (Bau)", "751": "Rechnungsinformation",
}
STEUERKATEGORIE = {
    "S": "Umsatzsteuer", "Z": "Nullsatz", "E": "steuerbefreit", "AE": "Reverse Charge",
    "K": "innergemeinschaftliche Lieferung", "G": "Ausfuhrlieferung", "O": "nicht steuerbar",
    "L": "Kanarische Inseln", "M": "Ceuta/Melilla",
}
EINHEIT = {
    "C62": "Stück", "H87": "Stück", "XPP": "Stück", "HUR": "Std.", "MIN": "Min.", "DAY": "Tag",
    "WEE": "Woche", "MON": "Monat", "ANN": "Jahr", "KGM": "kg", "GRM": "g", "TNE": "t", "MTR": "m",
    "KMT": "km", "MTK": "m²", "MTQ": "m³", "LTR": "l", "LS": "pauschal", "SET": "Satz", "P1": "%",
}
ZAHLUNGSART = {
    "10": "Bar", "30": "Überweisung", "31": "Überweisung", "42": "Überweisung", "48": "Karte",
    "49": "Lastschrift", "57": "Dauerauftrag", "58": "SEPA-Überweisung", "59": "SEPA-Lastschrift",
    "68": "Online-Zahlung", "ZZZ": "andere",
}


@dataclass
class Partei:
    name: str = ""
    adresse: list[str] = field(default_factory=list)
    ust_id: str = ""
    steuernr: str = ""
    kontakt: list[str] = field(default_factory=list)
    kennung: str = ""


@dataclass
class EInvoice:
    format: str = ""
    spezifikation: str = ""
    art: str = ""
    nummer: str = ""
    datum: str = ""
    faellig: str = ""
    waehrung: str = "EUR"
    zeitraum: str = ""
    lieferdatum: str = ""
    leitweg: str = ""
    bestellnr: str = ""
    vertrag: str = ""
    vorgaenger: str = ""
    verkaeufer: Partei = field(default_factory=Partei)
    kaeufer: Partei = field(default_factory=Partei)
    lieferort: Optional[Partei] = None
    positionen: list[dict] = field(default_factory=list)
    nachlaesse: list[dict] = field(default_factory=list)
    steuern: list[dict] = field(default_factory=list)
    summen: dict = field(default_factory=dict)
    zahlung: list[tuple[str, str]] = field(default_factory=list)
    bemerkungen: list[str] = field(default_factory=list)
    anhaenge: list[str] = field(default_factory=list)
    hinweise: list[str] = field(default_factory=list)


class KeineEInvoice(ValueError):
    pass


# ── Hilfen ────────────────────────────────────────────────────────────────────

def _t(elem, pfad: str, ns: dict) -> str:
    if elem is None:
        return ""
    r = elem.xpath(pfad, namespaces=ns)
    if not r:
        return ""
    k = r[0]
    wert = k if isinstance(k, str) else (k.text or "")
    return " ".join(str(wert).split())


def _alle(elem, pfad: str, ns: dict) -> list:
    return elem.xpath(pfad, namespaces=ns) if elem is not None else []


def _dez(text: str) -> Optional[Decimal]:
    try:
        return Decimal(text) if text else None
    except InvalidOperation:
        return None


def _datum(text: str) -> str:
    """CII 102 (JJJJMMTT) oder ISO (JJJJ-MM-TT) → TT.MM.JJJJ"""
    t = (text or "").strip()
    if len(t) == 8 and t.isdigit():
        return f"{t[6:8]}.{t[4:6]}.{t[0:4]}"
    if len(t) >= 10 and t[4] == "-" and t[7] == "-":
        return f"{t[8:10]}.{t[5:7]}.{t[0:4]}"
    return t


def _zeitraum(von: str, bis: str) -> str:
    von, bis = _datum(von), _datum(bis)
    if von and bis and von != bis:
        return f"{von} – {bis}"
    return von or bis


def _euro(wert: Optional[Decimal], waehrung: str = "EUR") -> str:
    if wert is None:
        return ""
    text = f"{wert:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{text} {'€' if waehrung == 'EUR' else waehrung}"


def _zahl(wert: Optional[Decimal]) -> str:
    if wert is None:
        return ""
    return format(wert.normalize(), "f").replace(".", ",")  # 10 statt 1E+1, 1,5 statt 1.5000


def _satz(text: str) -> str:
    d = _dez(text)
    return f"{_zahl(d)} %" if d is not None else ""


def _steuerkat(code: str) -> str:
    return STEUERKATEGORIE.get(code, code)


def _parser():
    from utils.rechnungs_parser import _xml_parser
    return _xml_parser()


# ── CII ───────────────────────────────────────────────────────────────────────

def _partei_cii(p) -> Partei:
    ns = NS_CII
    if p is None:
        return Partei()
    adr = p.find("ram:PostalTradeAddress", ns)
    zeilen = [_t(adr, f"ram:{z}", ns) for z in ("LineOne", "LineTwo", "LineThree")]
    ort = " ".join(x for x in (_t(adr, "ram:PostcodeCode", ns), _t(adr, "ram:CityName", ns)) if x)
    land = _t(adr, "ram:CountryID", ns)
    kontakt = []
    for k in _alle(p, "ram:DefinedTradeContact", ns):
        for wert in (_t(k, "ram:PersonName", ns), _t(k, "ram:DepartmentName", ns),
                     _t(k, "ram:TelephoneUniversalCommunication/ram:CompleteNumber", ns),
                     _t(k, "ram:EmailURIUniversalCommunication/ram:URIID", ns)):
            if wert:
                kontakt.append(wert)
    mail = _t(p, "ram:URIUniversalCommunication/ram:URIID", ns)
    if mail and mail not in kontakt:
        kontakt.append(mail)
    kennung = _t(p, "ram:SpecifiedLegalOrganization/ram:ID", ns) or _t(p, "ram:ID", ns) or _t(p, "ram:GlobalID", ns)
    return Partei(
        name=_t(p, "ram:Name", ns) or _t(p, "ram:SpecifiedLegalOrganization/ram:TradingBusinessName", ns),
        adresse=[z for z in zeilen if z] + ([ort] if ort else []) + ([land] if land and land != "DE" else []),
        ust_id=_t(p, "ram:SpecifiedTaxRegistration/ram:ID[@schemeID='VA']", ns),
        steuernr=_t(p, "ram:SpecifiedTaxRegistration/ram:ID[@schemeID='FC']", ns),
        kontakt=kontakt, kennung=kennung,
    )


def _lies_cii(root) -> EInvoice:
    ns = NS_CII
    e = EInvoice(format="CII (ZUGFeRD / Factur-X / XRechnung)")
    e.spezifikation = _t(root, "rsm:ExchangedDocumentContext/ram:GuidelineSpecifiedDocumentContextParameter/ram:ID", ns)
    if "xrechnung" in e.spezifikation.lower():
        e.format = "XRechnung (CII)"
    doc = root.find("rsm:ExchangedDocument", ns)
    e.nummer = _t(doc, "ram:ID", ns)
    code = _t(doc, "ram:TypeCode", ns)
    e.art = DOKUMENTART.get(code, code)
    e.datum = _datum(_t(doc, "ram:IssueDateTime/udt:DateTimeString", ns))
    e.bemerkungen = [_t(n, "ram:Content", ns) for n in _alle(doc, "ram:IncludedNote", ns) if _t(n, "ram:Content", ns)]

    tr = root.find("rsm:SupplyChainTradeTransaction", ns)
    ag = tr.find("ram:ApplicableHeaderTradeAgreement", ns) if tr is not None else None
    de = tr.find("ram:ApplicableHeaderTradeDelivery", ns) if tr is not None else None
    st = tr.find("ram:ApplicableHeaderTradeSettlement", ns) if tr is not None else None

    e.leitweg = _t(ag, "ram:BuyerReference", ns)
    e.bestellnr = _t(ag, "ram:BuyerOrderReferencedDocument/ram:IssuerAssignedID", ns)
    e.vertrag = _t(ag, "ram:ContractReferencedDocument/ram:IssuerAssignedID", ns)
    e.verkaeufer = _partei_cii(ag.find("ram:SellerTradeParty", ns) if ag is not None else None)
    e.kaeufer = _partei_cii(ag.find("ram:BuyerTradeParty", ns) if ag is not None else None)
    for d in _alle(ag, "ram:AdditionalReferencedDocument", ns):
        datei = _t(d, "ram:AttachmentBinaryObject/@filename", ns)
        teile = [x for x in (_t(d, "ram:IssuerAssignedID", ns), _t(d, "ram:Name", ns), datei) if x]
        e.anhaenge.append(" · ".join(teile) or "(ohne Bezeichnung)")

    ship = de.find("ram:ShipToTradeParty", ns) if de is not None else None
    if ship is not None:
        e.lieferort = _partei_cii(ship)
    e.lieferdatum = _datum(_t(de, "ram:ActualDeliverySupplyChainEvent/ram:OccurrenceDateTime/udt:DateTimeString", ns))

    e.waehrung = _t(st, "ram:InvoiceCurrencyCode", ns) or "EUR"
    e.zeitraum = _zeitraum(_t(st, "ram:BillingSpecifiedPeriod/ram:StartDateTime/udt:DateTimeString", ns),
                           _t(st, "ram:BillingSpecifiedPeriod/ram:EndDateTime/udt:DateTimeString", ns))
    e.vorgaenger = _t(st, "ram:InvoiceReferencedDocument/ram:IssuerAssignedID", ns)
    verwendung = _t(st, "ram:PaymentReference", ns)
    for pm in _alle(st, "ram:SpecifiedTradeSettlementPaymentMeans", ns):
        art = _t(pm, "ram:TypeCode", ns)
        e.zahlung.append(("Zahlungsart", ZAHLUNGSART.get(art, art) + (f" – {_t(pm, 'ram:Information', ns)}" if _t(pm, "ram:Information", ns) else "")))
        for label, pfad in (("IBAN", "ram:PayeePartyCreditorFinancialAccount/ram:IBANID"),
                            ("Kontoinhaber", "ram:PayeePartyCreditorFinancialAccount/ram:AccountName"),
                            ("BIC", "ram:PayeeSpecifiedCreditorFinancialInstitution/ram:BICID"),
                            ("Lastschrift von IBAN", "ram:PayerPartyDebtorFinancialAccount/ram:IBANID")):
            if _t(pm, pfad, ns):
                e.zahlung.append((label, _t(pm, pfad, ns)))
    if verwendung:
        e.zahlung.append(("Verwendungszweck", verwendung))
    for pt in _alle(st, "ram:SpecifiedTradePaymentTerms", ns):
        if _t(pt, "ram:Description", ns):
            e.zahlung.append(("Zahlungsbedingungen", _t(pt, "ram:Description", ns)))
        if _t(pt, "ram:DueDateDateTime/udt:DateTimeString", ns) and not e.faellig:
            e.faellig = _datum(_t(pt, "ram:DueDateDateTime/udt:DateTimeString", ns))

    for ac in _alle(st, "ram:SpecifiedTradeAllowanceCharge", ns):
        zuschlag = _t(ac, "ram:ChargeIndicator/udt:Indicator", ns).lower() == "true"
        e.nachlaesse.append({
            "zuschlag": zuschlag, "grund": _t(ac, "ram:Reason", ns) or _t(ac, "ram:ReasonCode", ns),
            "betrag": _dez(_t(ac, "ram:ActualAmount", ns)),
            "satz": _satz(_t(ac, "ram:CategoryTradeTax/ram:RateApplicablePercent", ns)),
            "kategorie": _t(ac, "ram:CategoryTradeTax/ram:CategoryCode", ns),
        })
    for tx in _alle(st, "ram:ApplicableTradeTax", ns):
        e.steuern.append({
            "kategorie": _t(tx, "ram:CategoryCode", ns), "satz_wert": _dez(_t(tx, "ram:RateApplicablePercent", ns)),
            "satz": _satz(_t(tx, "ram:RateApplicablePercent", ns)),
            "basis": _dez(_t(tx, "ram:BasisAmount", ns)), "betrag": _dez(_t(tx, "ram:CalculatedAmount", ns)),
            "grund": _t(tx, "ram:ExemptionReason", ns),
        })
    ms = st.find("ram:SpecifiedTradeSettlementHeaderMonetarySummation", ns) if st is not None else None
    e.summen = {
        "positionen": _dez(_t(ms, "ram:LineTotalAmount", ns)),
        "zuschlaege": _dez(_t(ms, "ram:ChargeTotalAmount", ns)),
        "nachlaesse": _dez(_t(ms, "ram:AllowanceTotalAmount", ns)),
        "netto": _dez(_t(ms, "ram:TaxBasisTotalAmount", ns)),
        "steuer": _dez(_t(ms, "ram:TaxTotalAmount", ns)),
        "brutto": _dez(_t(ms, "ram:GrandTotalAmount", ns)),
        "vorauszahlung": _dez(_t(ms, "ram:TotalPrepaidAmount", ns)),
        "rundung": _dez(_t(ms, "ram:RoundingAmount", ns)),
        "zahlbetrag": _dez(_t(ms, "ram:DuePayableAmount", ns)),
    }

    for li in _alle(tr, "ram:IncludedSupplyChainTradeLineItem", ns):
        menge_el = li.find("ram:SpecifiedLineTradeDelivery/ram:BilledQuantity", ns)
        einheit = menge_el.get("unitCode", "") if menge_el is not None else ""
        ls = li.find("ram:SpecifiedLineTradeSettlement", ns)
        e.positionen.append({
            "nr": _t(li, "ram:AssociatedDocumentLineDocument/ram:LineID", ns),
            "name": _t(li, "ram:SpecifiedTradeProduct/ram:Name", ns),
            "beschreibung": _t(li, "ram:SpecifiedTradeProduct/ram:Description", ns),
            "artnr": _t(li, "ram:SpecifiedTradeProduct/ram:SellerAssignedID", ns),
            "menge": _dez(menge_el.text.strip()) if menge_el is not None and menge_el.text else None,
            "einheit": EINHEIT.get(einheit, einheit),
            "preis": _dez(_t(li, "ram:SpecifiedLineTradeAgreement/ram:NetPriceProductTradePrice/ram:ChargeAmount", ns)),
            "netto": _dez(_t(ls, "ram:SpecifiedTradeSettlementLineMonetarySummation/ram:LineTotalAmount", ns)),
            "satz": _satz(_t(ls, "ram:ApplicableTradeTax/ram:RateApplicablePercent", ns)),
            "kategorie": _t(ls, "ram:ApplicableTradeTax/ram:CategoryCode", ns),
            "zeitraum": _zeitraum(_t(ls, "ram:BillingSpecifiedPeriod/ram:StartDateTime/udt:DateTimeString", ns),
                                  _t(ls, "ram:BillingSpecifiedPeriod/ram:EndDateTime/udt:DateTimeString", ns)),
        })
    return e


# ── UBL ───────────────────────────────────────────────────────────────────────

def _partei_ubl(p) -> Partei:
    ns = NS_UBL
    if p is None:
        return Partei()
    adr = p.find("cac:PostalAddress", ns)
    zeilen = [_t(adr, "cbc:StreetName", ns), _t(adr, "cbc:AdditionalStreetName", ns),
              _t(adr, "cac:AddressLine/cbc:Line", ns)]
    ort = " ".join(x for x in (_t(adr, "cbc:PostalZone", ns), _t(adr, "cbc:CityName", ns)) if x)
    land = _t(adr, "cac:Country/cbc:IdentificationCode", ns)
    ust_id = steuernr = ""
    for ts in _alle(p, "cac:PartyTaxScheme", ns):
        if _t(ts, "cac:TaxScheme/cbc:ID", ns).upper() == "VAT":
            ust_id = _t(ts, "cbc:CompanyID", ns)
        else:
            steuernr = _t(ts, "cbc:CompanyID", ns)
    kontakt = [x for x in (_t(p, "cac:Contact/cbc:Name", ns), _t(p, "cac:Contact/cbc:Telephone", ns),
                           _t(p, "cac:Contact/cbc:ElectronicMail", ns)) if x]
    endpunkt = _t(p, "cbc:EndpointID", ns)
    if endpunkt and endpunkt not in kontakt:
        kontakt.append(endpunkt)
    return Partei(
        name=_t(p, "cac:PartyLegalEntity/cbc:RegistrationName", ns) or _t(p, "cac:PartyName/cbc:Name", ns),
        adresse=[z for z in zeilen if z] + ([ort] if ort else []) + ([land] if land and land != "DE" else []),
        ust_id=ust_id, steuernr=steuernr, kontakt=kontakt,
        kennung=_t(p, "cac:PartyLegalEntity/cbc:CompanyID", ns) or _t(p, "cac:PartyIdentification/cbc:ID", ns),
    )


def _lies_ubl(root) -> EInvoice:
    ns = NS_UBL
    gutschrift = root.tag.endswith("CreditNote")
    e = EInvoice(format="XRechnung (UBL)")
    e.spezifikation = _t(root, "cbc:CustomizationID", ns)
    if "xrechnung" not in e.spezifikation.lower():
        e.format = "UBL"
    e.nummer = _t(root, "cbc:ID", ns)
    code = _t(root, "cbc:CreditNoteTypeCode" if gutschrift else "cbc:InvoiceTypeCode", ns)
    e.art = DOKUMENTART.get(code, code)
    e.datum = _datum(_t(root, "cbc:IssueDate", ns))
    e.faellig = _datum(_t(root, "cbc:DueDate", ns) or _t(root, "cac:PaymentMeans/cbc:PaymentDueDate", ns))
    e.waehrung = _t(root, "cbc:DocumentCurrencyCode", ns) or "EUR"
    e.bemerkungen = [_t(n, ".", ns) for n in _alle(root, "cbc:Note", ns) if _t(n, ".", ns)]
    e.leitweg = _t(root, "cbc:BuyerReference", ns)
    e.bestellnr = _t(root, "cac:OrderReference/cbc:ID", ns)
    e.vertrag = _t(root, "cac:ContractDocumentReference/cbc:ID", ns)
    e.vorgaenger = _t(root, "cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID", ns)
    e.zeitraum = _zeitraum(_t(root, "cac:InvoicePeriod/cbc:StartDate", ns), _t(root, "cac:InvoicePeriod/cbc:EndDate", ns))
    e.verkaeufer = _partei_ubl(root.find("cac:AccountingSupplierParty/cac:Party", ns))
    e.kaeufer = _partei_ubl(root.find("cac:AccountingCustomerParty/cac:Party", ns))
    lief = root.find("cac:Delivery", ns)
    if lief is not None:
        e.lieferdatum = _datum(_t(lief, "cbc:ActualDeliveryDate", ns))
        adr = lief.find("cac:DeliveryLocation/cac:Address", ns)
        if adr is not None:
            ort = " ".join(x for x in (_t(adr, "cbc:PostalZone", ns), _t(adr, "cbc:CityName", ns)) if x)
            e.lieferort = Partei(name=_t(lief, "cac:DeliveryParty/cac:PartyName/cbc:Name", ns),
                                 adresse=[x for x in (_t(adr, "cbc:StreetName", ns), ort) if x])
    for d in _alle(root, "cac:AdditionalDocumentReference", ns):
        teile = [x for x in (_t(d, "cbc:ID", ns), _t(d, "cbc:DocumentDescription", ns),
                             _t(d, "cac:Attachment/cbc:EmbeddedDocumentBinaryObject/@filename", ns)) if x]
        e.anhaenge.append(" · ".join(teile) or "(ohne Bezeichnung)")
    for pm in _alle(root, "cac:PaymentMeans", ns):
        art = _t(pm, "cbc:PaymentMeansCode", ns)
        e.zahlung.append(("Zahlungsart", ZAHLUNGSART.get(art, art)))
        for label, pfad in (("IBAN", "cac:PayeeFinancialAccount/cbc:ID"),
                            ("Kontoinhaber", "cac:PayeeFinancialAccount/cbc:Name"),
                            ("BIC", "cac:PayeeFinancialAccount/cac:FinancialInstitutionBranch/cbc:ID"),
                            ("Verwendungszweck", "cbc:PaymentID")):
            if _t(pm, pfad, ns):
                e.zahlung.append((label, _t(pm, pfad, ns)))
    for pt in _alle(root, "cac:PaymentTerms", ns):
        if _t(pt, "cbc:Note", ns):
            e.zahlung.append(("Zahlungsbedingungen", _t(pt, "cbc:Note", ns)))
    for ac in _alle(root, "cac:AllowanceCharge", ns):
        e.nachlaesse.append({
            "zuschlag": _t(ac, "cbc:ChargeIndicator", ns).lower() == "true",
            "grund": _t(ac, "cbc:AllowanceChargeReason", ns) or _t(ac, "cbc:AllowanceChargeReasonCode", ns),
            "betrag": _dez(_t(ac, "cbc:Amount", ns)),
            "satz": _satz(_t(ac, "cac:TaxCategory/cbc:Percent", ns)),
            "kategorie": _t(ac, "cac:TaxCategory/cbc:ID", ns),
        })
    for sub in _alle(root, "cac:TaxTotal/cac:TaxSubtotal", ns):
        e.steuern.append({
            "kategorie": _t(sub, "cac:TaxCategory/cbc:ID", ns),
            "satz_wert": _dez(_t(sub, "cac:TaxCategory/cbc:Percent", ns)),
            "satz": _satz(_t(sub, "cac:TaxCategory/cbc:Percent", ns)),
            "basis": _dez(_t(sub, "cbc:TaxableAmount", ns)), "betrag": _dez(_t(sub, "cbc:TaxAmount", ns)),
            "grund": _t(sub, "cac:TaxCategory/cbc:TaxExemptionReason", ns),
        })
    lm = root.find("cac:LegalMonetaryTotal", ns)
    netto, brutto = _dez(_t(lm, "cbc:TaxExclusiveAmount", ns)), _dez(_t(lm, "cbc:TaxInclusiveAmount", ns))
    steuer = _dez(_t(root, "cac:TaxTotal/cbc:TaxAmount", ns))
    e.summen = {
        "positionen": _dez(_t(lm, "cbc:LineExtensionAmount", ns)),
        "zuschlaege": _dez(_t(lm, "cbc:ChargeTotalAmount", ns)),
        "nachlaesse": _dez(_t(lm, "cbc:AllowanceTotalAmount", ns)),
        "netto": netto, "steuer": steuer, "brutto": brutto,
        "vorauszahlung": _dez(_t(lm, "cbc:PrepaidAmount", ns)),
        "rundung": _dez(_t(lm, "cbc:PayableRoundingAmount", ns)),
        "zahlbetrag": _dez(_t(lm, "cbc:PayableAmount", ns)),
    }
    zeile = "cac:CreditNoteLine" if gutschrift else "cac:InvoiceLine"
    mengenfeld = "cbc:CreditedQuantity" if gutschrift else "cbc:InvoicedQuantity"
    for li in _alle(root, zeile, ns):
        menge_el = li.find(mengenfeld, ns)
        einheit = menge_el.get("unitCode", "") if menge_el is not None else ""
        e.positionen.append({
            "nr": _t(li, "cbc:ID", ns),
            "name": _t(li, "cac:Item/cbc:Name", ns),
            "beschreibung": _t(li, "cac:Item/cbc:Description", ns),
            "artnr": _t(li, "cac:Item/cac:SellersItemIdentification/cbc:ID", ns),
            "menge": _dez(menge_el.text.strip()) if menge_el is not None and menge_el.text else None,
            "einheit": EINHEIT.get(einheit, einheit),
            "preis": _dez(_t(li, "cac:Price/cbc:PriceAmount", ns)),
            "netto": _dez(_t(li, "cbc:LineExtensionAmount", ns)),
            "satz": _satz(_t(li, "cac:Item/cac:ClassifiedTaxCategory/cbc:Percent", ns)),
            "kategorie": _t(li, "cac:Item/cac:ClassifiedTaxCategory/cbc:ID", ns),
            "zeitraum": _zeitraum(_t(li, "cac:InvoicePeriod/cbc:StartDate", ns), _t(li, "cac:InvoicePeriod/cbc:EndDate", ns)),
        })
    return e


# ── Einlesen + Rechenprüfung ──────────────────────────────────────────────────

def lies_einvoice(daten: bytes) -> EInvoice:
    """XML (CII/UBL) oder PDF mit eingebetteter XML (ZUGFeRD) einlesen."""
    from lxml import etree
    if daten[:4] == b"%PDF":
        try:
            from facturx import get_facturx_xml_from_pdf
            ergebnis = get_facturx_xml_from_pdf(daten)
            daten = ergebnis[1] if isinstance(ergebnis, tuple) else ergebnis
        except Exception:
            daten = None
        if not daten:
            raise KeineEInvoice("Das PDF enthält keine E-Rechnungsdaten (keine ZUGFeRD-/XRechnung-XML).")
    try:
        root = etree.fromstring(daten, parser=_parser())
    except etree.XMLSyntaxError as fehler:
        raise KeineEInvoice(f"Die Datei ist kein gültiges XML ({fehler}).") from fehler
    tag = etree.QName(root).localname
    if tag == "CrossIndustryInvoice":
        e = _lies_cii(root)
    elif tag == "CrossIndustryDocument":  # ZUGFeRD 1.0
        from utils.rechnungs_parser import _zugferd1_zu_cii
        e = _lies_cii(etree.fromstring(_zugferd1_zu_cii(root), parser=_parser()))
        e.format = "ZUGFeRD 1.0"
    elif tag in ("Invoice", "CreditNote"):
        e = _lies_ubl(root)
    else:
        raise KeineEInvoice("Die XML-Datei ist keine E-Rechnung (weder CII noch UBL).")
    e.hinweise = pruefe_rechnung(e)
    return e


def pruefe_rechnung(e: EInvoice) -> list[str]:
    """Einfache Rechenprüfung – Abweichungen ab 1 Cent."""
    s = e.summen
    hinweise: list[str] = []
    cent = Decimal("0.01")

    def abw(a, b) -> bool:
        return a is not None and b is not None and abs(a - b) > cent / 2

    pos_summe = sum((p["netto"] for p in e.positionen if p["netto"] is not None), Decimal("0"))
    if e.positionen and abw(pos_summe, s.get("positionen")):
        hinweise.append(f"Summe der Positionen ({_euro(pos_summe)}) weicht von der angegebenen Positionssumme "
                        f"({_euro(s.get('positionen'))}) ab.")
    nl = sum((n["betrag"] or 0 for n in e.nachlaesse if not n["zuschlag"]), Decimal("0"))
    zs = sum((n["betrag"] or 0 for n in e.nachlaesse if n["zuschlag"]), Decimal("0"))
    if s.get("positionen") is not None and abw(s["positionen"] - nl + zs, s.get("netto")):
        hinweise.append(f"Positionen − Nachlässe + Zuschläge ({_euro(s['positionen'] - nl + zs)}) ergeben nicht "
                        f"den Nettobetrag ({_euro(s.get('netto'))}).")
    st_summe = sum((t["betrag"] for t in e.steuern if t["betrag"] is not None), Decimal("0"))
    if e.steuern and abw(st_summe, s.get("steuer")):
        hinweise.append(f"Summe der Steuerbeträge je Satz ({_euro(st_summe)}) weicht von der Gesamtsteuer "
                        f"({_euro(s.get('steuer'))}) ab.")
    for t in e.steuern:
        if t["kategorie"] == "S" and t["basis"] is not None and t["satz_wert"] is not None and t["betrag"] is not None:
            soll = (t["basis"] * t["satz_wert"] / 100).quantize(cent)
            if abw(soll, t["betrag"]):
                hinweise.append(f"Steuer {t['satz']}: {_euro(t['basis'])} × {t['satz']} = {_euro(soll)}, "
                                f"angegeben sind {_euro(t['betrag'])}.")
    if s.get("netto") is not None and s.get("steuer") is not None and abw(s["netto"] + s["steuer"], s.get("brutto")):
        hinweise.append(f"Netto + Steuer ({_euro(s['netto'] + s['steuer'])}) ergeben nicht den Bruttobetrag "
                        f"({_euro(s.get('brutto'))}).")
    if s.get("brutto") is not None and s.get("zahlbetrag") is not None:
        soll = s["brutto"] - (s.get("vorauszahlung") or 0) + (s.get("rundung") or 0)
        if abw(soll, s["zahlbetrag"]):
            hinweise.append(f"Brutto − Vorauszahlung ({_euro(soll)}) ergibt nicht den Zahlbetrag "
                            f"({_euro(s['zahlbetrag'])}).")
    return hinweise


# ── PDF ───────────────────────────────────────────────────────────────────────

def ansicht_pdf(daten: bytes, quelle: str = "") -> bytes:
    """Lesbare Ansicht als PDF. Wirft KeineEInvoice, wenn die Datei keine E-Rechnung ist."""
    from fpdf import FPDF
    from fpdf.fonts import FontFace
    from utils.pdf_rechnung_base import _find_dejavu_dir

    e = lies_einvoice(daten)
    w = e.waehrung

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=18)
    dv = _find_dejavu_dir()
    pdf.add_font("DejaVu", style="", fname=str(dv / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", style="B", fname=str(dv / "DejaVuSans-Bold.ttf"))
    pdf.set_title(f"E-Rechnung {e.nummer}")

    def fuss():
        pdf.set_y(-12)
        pdf.set_font("DejaVu", "", 7)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 4, "Lesbare Ansicht der E-Rechnungsdaten, erstellt von RechnungsFee. Keine Prüfung nach "
                       f"den offiziellen XRechnung-Regeln. Seite {pdf.page_no()}", align="C")
    pdf.footer = fuss  # type: ignore[method-assign]
    pdf.add_page()
    breite = pdf.epw

    def ueberschrift(text: str):
        pdf.ln(3)
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 6, text, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.set_draw_color(200, 200, 200)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + breite, pdf.get_y())
        pdf.ln(1.5)

    def zeilen(paare: list[tuple[str, str]], label_w: float = 45):
        pdf.set_text_color(30, 30, 30)
        for label, wert in paare:
            if not wert:
                continue
            pdf.set_font("DejaVu", "", 8.5)
            pdf.set_text_color(110, 110, 110)
            pdf.cell(label_w, 5, label)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(breite - label_w, 5, wert, new_x="LMARGIN", new_y="NEXT", align="L")

    # Kopf
    pdf.set_font("DejaVu", "B", 15)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, f"{e.art or 'E-Rechnung'} {e.nummer}".strip(), new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(110, 110, 110)
    pdf.multi_cell(0, 4, " · ".join(x for x in (e.format, e.spezifikation, quelle) if x),
                   new_x="LMARGIN", new_y="NEXT", align="L")

    if e.hinweise:
        pdf.ln(2)
        pdf.set_fill_color(253, 236, 234)
        pdf.set_text_color(160, 30, 20)
        pdf.set_font("DejaVu", "B", 9)
        pdf.cell(0, 6, "Rechenprüfung: Abweichungen gefunden", fill=True, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.set_font("DejaVu", "", 8.5)
        for h in e.hinweise:
            pdf.multi_cell(0, 5, f"• {h}", fill=True, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.set_fill_color(255, 255, 255)  # sonst färben sich die Tabellen danach mit ein
    else:
        pdf.ln(1)
        pdf.set_font("DejaVu", "", 8.5)
        pdf.set_text_color(30, 110, 50)
        pdf.cell(0, 5, "Rechenprüfung: Positionen, Steuer und Summen stimmen überein.", new_x="LMARGIN", new_y="NEXT", align="L")

    ueberschrift("Rechnungsdaten")
    zeilen([
        ("Rechnungsnummer", e.nummer), ("Rechnungsdatum", e.datum), ("Fällig am", e.faellig),
        ("Leistungszeitraum", e.zeitraum), ("Lieferdatum", e.lieferdatum),
        ("Leitweg-ID / Käuferreferenz", e.leitweg), ("Bestellnummer", e.bestellnr), ("Vertrag", e.vertrag),
        ("Bezug auf Rechnung", e.vorgaenger), ("Währung", w if w != "EUR" else ""),
    ])

    # Parteien nebeneinander
    def partei_text(p: Partei) -> str:
        zeilen_ = [p.name] + p.adresse
        if p.ust_id:
            zeilen_.append(f"USt-IdNr.: {p.ust_id}")
        if p.steuernr:
            zeilen_.append(f"Steuernummer: {p.steuernr}")
        if p.kennung:
            zeilen_.append(f"Kennung: {p.kennung}")
        zeilen_ += p.kontakt
        return "\n".join(z for z in zeilen_ if z) or "—"

    parteien = [("Verkäufer", e.verkaeufer), ("Käufer", e.kaeufer)]
    if e.lieferort and (e.lieferort.name or e.lieferort.adresse):
        parteien.append(("Lieferort", e.lieferort))
    pdf.ln(2)
    stil_kopf = FontFace(emphasis="BOLD", fill_color=(240, 240, 240))
    pdf.set_font("DejaVu", "", 8.5)
    pdf.set_text_color(30, 30, 30)
    with pdf.table(headings_style=stil_kopf, line_height=4.5, text_align="LEFT", v_align="TOP",
                   borders_layout="HORIZONTAL_LINES") as t:
        kopf = t.row()
        for titel, _ in parteien:
            kopf.cell(titel)
        zeile = t.row()
        for _, p in parteien:
            zeile.cell(partei_text(p))

    ueberschrift("Positionen")
    pdf.set_font("DejaVu", "", 8)
    with pdf.table(col_widths=(10, 78, 18, 16, 24, 14, 26), headings_style=stil_kopf, line_height=4.2,
                   text_align=("LEFT", "LEFT", "RIGHT", "LEFT", "RIGHT", "RIGHT", "RIGHT"),
                   borders_layout="HORIZONTAL_LINES") as t:
        k = t.row()
        for titel in ("Pos.", "Bezeichnung", "Menge", "Einheit", "Einzelpreis", "USt", "Netto"):
            k.cell(titel)
        for p in e.positionen:
            text = p["name"]
            if p["beschreibung"] and p["beschreibung"] != p["name"]:
                text += f"\n{p['beschreibung']}"
            if p["artnr"]:
                text += f"\nArt.-Nr. {p['artnr']}"
            if p["zeitraum"]:
                text += f"\nLeistung: {p['zeitraum']}"
            satz = p["satz"] if p["kategorie"] in ("S", "") else (p["satz"] + " " + _steuerkat(p["kategorie"])).strip()
            r = t.row()
            for wert in (p["nr"], text, _zahl(p["menge"]), p["einheit"], _euro(p["preis"], w), satz,
                         _euro(p["netto"], w)):
                r.cell(wert or "")

    if e.nachlaesse:
        ueberschrift("Nachlässe und Zuschläge auf die Rechnung")
        zeilen([(("Zuschlag" if n["zuschlag"] else "Nachlass") + (f" ({n['satz']})" if n["satz"] else ""),
                 f"{'+' if n['zuschlag'] else '−'} {_euro(n['betrag'], w)}" + (f" – {n['grund']}" if n["grund"] else ""))
                for n in e.nachlaesse])

    ueberschrift("Steuer")
    pdf.set_font("DejaVu", "", 8.5)
    with pdf.table(col_widths=(60, 25, 40, 40), headings_style=stil_kopf, line_height=4.5,
                   text_align=("LEFT", "RIGHT", "RIGHT", "RIGHT"), borders_layout="HORIZONTAL_LINES") as t:
        k = t.row()
        for titel in ("Kategorie", "Satz", "Bemessungsgrundlage", "Steuerbetrag"):
            k.cell(titel)
        for st in e.steuern:
            r = t.row()
            kat = _steuerkat(st["kategorie"]) + (f"\n{st['grund']}" if st["grund"] else "")
            for wert in (kat, st["satz"], _euro(st["basis"], w), _euro(st["betrag"], w)):
                r.cell(wert or "")

    ueberschrift("Summen")
    s = e.summen
    zeilen([
        ("Summe Positionen", _euro(s.get("positionen"), w)),
        ("Nachlässe", f"− {_euro(s['nachlaesse'], w)}" if s.get("nachlaesse") else ""),
        ("Zuschläge", f"+ {_euro(s['zuschlaege'], w)}" if s.get("zuschlaege") else ""),
        ("Nettobetrag", _euro(s.get("netto"), w)),
        ("Umsatzsteuer", _euro(s.get("steuer"), w)),
        ("Bruttobetrag", _euro(s.get("brutto"), w)),
        ("Bereits gezahlt", f"− {_euro(s['vorauszahlung'], w)}" if s.get("vorauszahlung") else ""),
        ("Rundung", _euro(s.get("rundung"), w) if s.get("rundung") else ""),
    ], label_w=60)
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(60, 6, "Zahlbetrag")
    pdf.cell(0, 6, _euro(s.get("zahlbetrag"), w), new_x="LMARGIN", new_y="NEXT", align="L")

    if e.zahlung:
        ueberschrift("Zahlung")
        zeilen(e.zahlung)
    if e.bemerkungen:
        ueberschrift("Bemerkungen")
        pdf.set_font("DejaVu", "", 8.5)
        for b in e.bemerkungen:
            pdf.multi_cell(0, 5, b, new_x="LMARGIN", new_y="NEXT", align="L")
            pdf.ln(1)
    if e.anhaenge:
        ueberschrift("Eingebettete Anhänge")
        pdf.set_font("DejaVu", "", 8.5)
        for a in e.anhaenge:
            pdf.multi_cell(0, 5, f"• {a}", new_x="LMARGIN", new_y="NEXT", align="L")

    return bytes(pdf.output())
