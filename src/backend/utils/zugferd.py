"""
ZUGFeRD 2.3 / FacturX EN 16931 (Comfort) – XML-Generierung und PDF-Einbettung.

Ablauf:
  1. generate_zugferd_xml()  → CII-XML als bytes
  2. generate_zugferd_pdf()  → ruft generate_rechnung_pdf() + bettet XML ein → PDF/A-3

Nur für Ausgangsrechnungen (typ='ausgang'), nicht für Entwürfe oder stornierte Rechnungen.
"""

from decimal import Decimal

# UN/ECE Rec 20 Einheitencodes
_EINHEIT_CODE: dict[str, str] = {
    "Stück": "C62", "Stk": "C62", "stk": "C62",
    "Std": "HUR", "Stunden": "HUR", "h": "HUR",
    "Min": "MIN", "Minuten": "MIN",
    "Tag": "DAY", "Tage": "DAY",
    "Woche": "WEE", "Wochen": "WEE",
    "Monat": "MON", "Monate": "MON",
    "kg": "KGM", "g": "GRM",
    "l": "LTR", "ml": "MLT",
    "m": "MTR", "m²": "MTK", "m2": "MTK",
    "m³": "MTQ", "m3": "MTQ", "km": "KMT",
    "Pauschal": "LS", "pauschal": "LS", "Pauschale": "LS",
}


def _einheit_code(einheit: str) -> str:
    return _EINHEIT_CODE.get(einheit, "C62")


def _kunde_name(kunde) -> str:
    if kunde.firmenname:
        return kunde.firmenname
    teile = [t for t in [kunde.vorname, kunde.nachname] if t]
    return " ".join(teile) if teile else "Unbekannt"


def _steuerkategorie(ust_satz: Decimal, ist_kleinunternehmer: bool) -> str:
    if ust_satz > 0:
        return "S"
    return "E" if ist_kleinunternehmer else "Z"


def generate_zugferd_xml(rechnung, unternehmen: dict) -> bytes:
    """Erzeugt das ZUGFeRD 2.3 / FacturX EN 16931 (Comfort) XML als UTF-8-bytes."""
    from drafthorse.models.document import Document
    from drafthorse.models.accounting import ApplicableTradeTax
    from drafthorse.models.note import IncludedNote
    from drafthorse.models.trade import LineItem
    from drafthorse.models.party import TaxRegistration
    from drafthorse.models.payment import PaymentMeans, PaymentTerms

    ist_ku = unternehmen.get("ist_kleinunternehmer", False)

    doc = Document()
    doc.context.business_parameter.id = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"
    doc.context.guideline_parameter.id = "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended"
    doc.header.id._text = rechnung.rechnungsnummer or str(rechnung.id)
    doc.header.type_code._text = "380"
    doc.header.issue_date_time._value = rechnung.datum

    if rechnung.notizen:
        note = IncludedNote()
        note.content._text = rechnung.notizen
        doc.header.notes.add(note)

    # ── Verkäufer ─────────────────────────────────────────────────────────────
    seller = doc.trade.agreement.seller
    seller.name = unternehmen["firmenname"]
    seller.address.line_one = f"{unternehmen['strasse']} {unternehmen['hausnummer']}"
    seller.address.postcode = unternehmen["plz"]
    seller.address.city_name = unternehmen["ort"]
    seller.address.country_id = unternehmen.get("land", "DE")

    if unternehmen.get("ust_idnr"):
        reg = TaxRegistration()
        reg.id = ("VA", unternehmen["ust_idnr"])
        seller.tax_registrations.add(reg)
    elif unternehmen.get("steuernummer"):
        reg = TaxRegistration()
        reg.id = ("FC", unternehmen["steuernummer"])
        seller.tax_registrations.add(reg)

    # ── Käufer ────────────────────────────────────────────────────────────────
    buyer = doc.trade.agreement.buyer
    if rechnung.kunde:
        k = rechnung.kunde
        buyer.name = _kunde_name(k)
        if k.strasse:
            buyer.address.line_one = f"{k.strasse} {k.hausnummer or ''}".strip()
        if k.plz:
            buyer.address.postcode = k.plz
        if k.ort:
            buyer.address.city_name = k.ort
        buyer.address.country_id = k.land or "DE"
    else:
        buyer.name = rechnung.partner_freitext or "Kunde"

    # ── Lieferdatum ───────────────────────────────────────────────────────────
    if rechnung.leistungsdatum:
        doc.trade.delivery.event.occurrence._value = rechnung.leistungsdatum

    # ── Fälligkeitsdatum ──────────────────────────────────────────────────────
    if rechnung.faellig_am:
        pt = PaymentTerms()
        pt.due._value = rechnung.faellig_am
        doc.trade.settlement.terms.add(pt)

    # ── Zahlungsweise (SEPA-Überweisung) ──────────────────────────────────────
    if unternehmen.get("iban"):
        pm = PaymentMeans()
        pm.type_code._text = "58"
        pm.payee_account.iban = unternehmen["iban"]
        doc.trade.settlement.payment_means.add(pm)

    # ── Währung ───────────────────────────────────────────────────────────────
    doc.trade.settlement.currency_code = "EUR"

    # ── Positionen ────────────────────────────────────────────────────────────
    for pos in sorted(rechnung.positionen, key=lambda p: p.position_nr):
        li = LineItem()
        li.document.line_id._text = str(pos.position_nr)
        li.product.name = pos.beschreibung

        # Brutto- und Nettopreis pro Einheit (Extended: beide Felder erforderlich)
        einheit_code = _einheit_code(pos.einheit)
        netto_pro_einheit = (pos.netto / pos.menge) if pos.menge else pos.netto
        from drafthorse.models.tradelines import AllowanceCharge
        li.agreement.gross.amount = netto_pro_einheit
        li.agreement.gross.basis_quantity = (Decimal("1"), einheit_code)
        discount = AllowanceCharge()
        discount.indicator = False
        discount.actual_amount = Decimal("0.00")
        li.agreement.gross.charge.add(discount)
        li.agreement.net.amount = netto_pro_einheit
        li.agreement.net.basis_quantity = (Decimal("1"), einheit_code)

        # Menge
        li.delivery.billed_quantity = (pos.menge, einheit_code)

        # Steuer auf Position – nur Kategorie+Satz, kein Betrag (EN16931-Regel)
        li.settlement.trade_tax.type_code = "VAT"
        li.settlement.trade_tax.category_code = _steuerkategorie(pos.ust_satz, ist_ku)
        li.settlement.trade_tax.rate_applicable_percent = pos.ust_satz

        # Zeilensumme
        li.settlement.monetary_summation.total_amount = pos.netto

        doc.trade.items.add(li)

    # ── Steuer-Zusammenfassung (pro USt-Satz) ─────────────────────────────────
    steuern: dict[str, dict] = {}
    for pos in rechnung.positionen:
        key = str(pos.ust_satz)
        if key not in steuern:
            steuern[key] = {"satz": pos.ust_satz, "basis": Decimal("0"), "betrag": Decimal("0")}
        steuern[key]["basis"] += pos.netto
        steuern[key]["betrag"] += pos.ust_betrag

    for eintrag in steuern.values():
        tax = ApplicableTradeTax()
        tax.type_code = "VAT"
        tax.category_code = _steuerkategorie(eintrag["satz"], ist_ku)
        tax.rate_applicable_percent = eintrag["satz"]
        tax.basis_amount = eintrag["basis"]
        tax.calculated_amount = eintrag["betrag"]
        if ist_ku and eintrag["satz"] == 0:
            tax.exemption_reason = "Umsatzsteuerbefreiung gemäß §19 UStG"
        doc.trade.settlement.trade_tax.add(tax)

    # ── Gesamtsummen ──────────────────────────────────────────────────────────
    ms = doc.trade.settlement.monetary_summation
    ms.line_total = rechnung.netto_gesamt
    ms.tax_basis_total = rechnung.netto_gesamt        # kein currencyID (EN16931)
    ms.tax_total = (rechnung.ust_gesamt, "EUR")       # currencyID required
    ms.grand_total = rechnung.brutto_gesamt           # kein currencyID (EN16931)
    ms.due_amount = rechnung.brutto_gesamt - rechnung.bezahlt_betrag

    return doc.serialize(schema="FACTUR-X_EXTENDED")


def generate_zugferd_pdf(rechnung, unternehmen: dict) -> bytes:
    """Erzeugt ein ZUGFeRD PDF/A-3 – normales PDF + eingebettetes FacturX-XML."""
    import facturx
    from utils.pdf_rechnung import generate_rechnung_pdf

    pdf_bytes = generate_rechnung_pdf(rechnung, unternehmen, ist_kopie=False, ist_entwurf=False)
    xml_bytes = generate_zugferd_xml(rechnung, unternehmen)

    return facturx.generate_from_binary(
        pdf_bytes,
        xml_bytes,
        flavor="factur-x",
        level="extended",
        check_xsd=False,
        check_schematron=False,
        xmp_compression=False,
        afrelationship="alternative",
    )
