"""
ZUGFeRD 2.3 / FacturX EN 16931 (Comfort) – XML-Generierung und PDF-Einbettung.

Ablauf:
  1. generate_zugferd_xml()  → CII-XML als bytes
  2. generate_zugferd_pdf()  → ruft generate_rechnung_pdf() + bettet XML ein → PDF/A-3

Nur für Ausgangsrechnungen (typ='ausgang'), nicht für Entwürfe oder stornierte Rechnungen.
"""

import base64
from decimal import Decimal

from database.connection import APP_DATA_DIR

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


def _d(wert) -> Decimal:
    """Geldbeträge immer als xx.xx – verhindert 1E+2-Notation bei Decimal-Division."""
    return Decimal(str(wert)).quantize(Decimal("0.01"))


def _ust_satz(satz: Decimal) -> Decimal:
    """19.00 → 19, 7.00 → 7, 5.50 → 5.50 – normalize() ist sicher für kleine Prozentwerte."""
    return Decimal(str(satz)).quantize(Decimal("0.01")).normalize()


def _kunde_name(kunde) -> str:
    if kunde.firmenname:
        return kunde.firmenname
    teile = [t for t in [kunde.vorname, kunde.nachname] if t]
    return " ".join(teile) if teile else "Unbekannt"


# Issue #467: Steuerkategorie (UNTDID 5305) und Befreiungsgrund (BT-120/121) je Sonderfall der
# Rechnung. Vorher bekam jede 0-%-Position "Z" (Nullsatz) - formal gültig, inhaltlich falsch.
_SONDERFALL_KATEGORIE = {
    "ist_reverse_charge":     ("AE", "VATEX-EU-AE", "Steuerschuldnerschaft des Leistungsempfängers"),
    "ist_eu_lieferung":       ("K",  "VATEX-EU-IC", "Steuerfreie innergemeinschaftliche Lieferung"),
    "ist_ausfuhrlieferung":   ("G",  "VATEX-EU-G",  "Steuerfreie Ausfuhrlieferung"),
    "ist_drittland_leistung": ("O",  "VATEX-EU-O",  "Nicht im Inland steuerbare Leistung"),
}


def _sonderfall(rechnung) -> tuple[str, str, str] | None:
    """(Kategorie, Befreiungsgrund-Code, Befreiungsgrund-Text) des Rechnungs-Sonderfalls oder None.
    Die Flags schließen sich im Formular gegenseitig aus."""
    for flag, werte in _SONDERFALL_KATEGORIE.items():
        if getattr(rechnung, flag, False):
            return werte
    return None


def _steuerkategorie(ust_satz: Decimal, ist_kleinunternehmer: bool, sonderfall=None) -> str:
    if ust_satz > 0:
        return "S"
    if sonderfall:
        return sonderfall[0]
    return "E" if ist_kleinunternehmer else "Z"


def generate_zugferd_xml(rechnung, unternehmen: dict) -> bytes:
    """Erzeugt das ZUGFeRD 2.3 / FacturX EN 16931 (Comfort) XML als UTF-8-bytes."""
    # Pflichtfelder früh prüfen – gibt sprechenden Fehler statt kryptischem drafthorse-Crash
    _fehlend = []
    _firmenname = (unternehmen.get("firmenname") or "").strip()
    _vorname    = (unternehmen.get("vorname") or "").strip()
    _nachname   = (unternehmen.get("nachname") or "").strip()
    _seller_name = _firmenname or " ".join(filter(None, [_vorname, _nachname]))
    if not _seller_name:
        _fehlend.append("Firmenname oder Vor-/Nachname")
    for label, wert in [("Straße", unternehmen.get("strasse", "")),
                        ("PLZ",    unternehmen.get("plz", "")),
                        ("Ort",    unternehmen.get("ort", ""))]:
        if not str(wert).strip():
            _fehlend.append(label)
    if not unternehmen.get("steuernummer", "").strip() and not unternehmen.get("ust_idnr", "").strip():
        _fehlend.append("Steuernummer oder USt-IdNr.")
    if _fehlend:
        raise ValueError(f"ZUGFeRD-Pflichtfelder in Unternehmensdaten fehlen: {', '.join(_fehlend)}")

    from drafthorse.models.document import Document
    from drafthorse.models.accounting import ApplicableTradeTax
    from drafthorse.models.note import IncludedNote
    from drafthorse.models.trade import LineItem
    from drafthorse.models.party import TaxRegistration
    from drafthorse.models.payment import PaymentMeans, PaymentTerms
    from drafthorse.models.references import AdditionalReferencedDocument

    ist_ku = unternehmen.get("ist_kleinunternehmer", False)
    sonderfall = _sonderfall(rechnung)
    # Kategorie O (nicht steuerbar): die Rechnung darf keine USt-IdNr. von Verkäufer oder Käufer
    # enthalten (BR-O-02) und die Positionen keinen Steuersatz (BR-O-05)
    ist_nicht_steuerbar = bool(sonderfall and sonderfall[0] == "O")

    doc = Document()
    doc.context.business_parameter.id = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"
    doc.context.guideline_parameter.id = "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"
    doc.header.id._text = rechnung.rechnungsnummer or str(rechnung.id)
    doc.header.type_code._text = "380"
    doc.header.issue_date_time._value = rechnung.datum

    # Issue #474: eigene BT-22-Bemerkung hat Vorrang - dann bleiben die Notizen reiner
    # PDF-Fußtext; ohne sie gehen wie bisher die Notizen in BT-22
    bemerkung = (getattr(rechnung, "bemerkung_erechnung", None) or "").strip() or rechnung.notizen
    if bemerkung:
        note = IncludedNote()
        note.subject_code._text = "AAI"
        note.content._text = bemerkung
        doc.header.notes.add(note)

    # ── Verkäufer ─────────────────────────────────────────────────────────────
    seller = doc.trade.agreement.seller
    seller.name = _seller_name
    seller.address.line_one = f"{unternehmen['strasse']} {unternehmen.get('hausnummer') or ''}".strip()
    seller.address.postcode = unternehmen["plz"]
    seller.address.city_name = unternehmen["ort"]
    seller.address.country_id = unternehmen.get("land", "DE")

    if unternehmen.get("ust_idnr") and not ist_nicht_steuerbar:
        reg = TaxRegistration()
        reg.id = ("VA", unternehmen["ust_idnr"])
        seller.tax_registrations.add(reg)
    elif unternehmen.get("steuernummer"):
        reg = TaxRegistration()
        reg.id = ("FC", unternehmen["steuernummer"])
        seller.tax_registrations.add(reg)

    # BR-CO-26: ohne USt-IdNr. (bei Kategorie O verboten) braucht es eine Verkäuferkennung -
    # Handelsregisternummer (BT-30), sonst die Steuernummer als Verkäuferkennung (BT-29) (Issue #467)
    if ist_nicht_steuerbar:
        if unternehmen.get("handelsregister_nr"):
            seller.legal_organization.id = unternehmen["handelsregister_nr"]
        elif unternehmen.get("steuernummer"):
            seller.id = unternehmen["steuernummer"]

    # BT-34: Elektronische Adresse des Verkäufers (XRechnung-Pflichtfeld)
    if unternehmen.get("email"):
        seller.electronic_address.uri_ID = ("EM", unternehmen["email"])

    # BR-DE-2 / BR-DE-5: SELLER CONTACT (BG-6) mit BT-41 (DepartmentName) ist XRechnung-Pflicht
    seller.contact.department_name._text = _seller_name
    if unternehmen.get("telefon"):
        seller.contact.telephone.number = unternehmen["telefon"]
    if unternehmen.get("email"):
        seller.contact.email.address = unternehmen["email"]

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
        # BT-49: Elektronische Adresse des Käufers (empfohlen)
        if hasattr(k, "email") and k.email:
            buyer.electronic_address.uri_ID = ("EM", k.email)
        # BT-48: USt-IdNr. des Käufers - Pflicht bei Reverse Charge und ig. Lieferung (BR-AE-02,
        # BR-IC-02), bei Kategorie O dagegen verboten (BR-O-02) (Issue #467)
        if getattr(k, "ust_idnr", None) and k.ust_idnr.strip() and not ist_nicht_steuerbar:
            reg = TaxRegistration()
            reg.id = ("VA", k.ust_idnr.strip().replace(" ", ""))
            buyer.tax_registrations.add(reg)
    else:
        buyer.name = rechnung.partner_freitext or "Kunde"

    # BT-80: Lieferland - Pflicht bei ig. Lieferung (BR-IC-12); XRechnung verlangt dann die
    # vollständige Lieferanschrift (BR-DE-10/11: Ort, PLZ). Lieferadresse vor Kundenadresse.
    if sonderfall and sonderfall[0] == "K":
        lieferadresse = next(
            (la for la in (rechnung.kunde.lieferadressen if rechnung.kunde else [])
             if la.id == getattr(rechnung, "lieferadresse_id", None)),
            None,
        )
        quelle = lieferadresse or rechnung.kunde
        ship_to = doc.trade.delivery.ship_to
        if quelle is not None:
            ship_to.name = getattr(quelle, "firmenname", None) or buyer.name
            if quelle.strasse:
                ship_to.address.line_one = f"{quelle.strasse} {quelle.hausnummer or ''}".strip()
            if quelle.plz:
                ship_to.address.postcode = quelle.plz
            if quelle.ort:
                ship_to.address.city_name = quelle.ort
            ship_to.address.country_id = quelle.land or "DE"
        elif rechnung.partner_land:
            ship_to.name = buyer.name
            if rechnung.partner_plz:
                ship_to.address.postcode = rechnung.partner_plz
            if rechnung.partner_ort:
                ship_to.address.city_name = rechnung.partner_ort
            ship_to.address.country_id = rechnung.partner_land

    # BuyerReference (XRechnung-Pflichtfeld: Kundennummer oder Rechnungsnummer)
    if rechnung.kunde and rechnung.kunde.kundennummer:
        doc.trade.agreement.buyer_reference = rechnung.kunde.kundennummer
    else:
        doc.trade.agreement.buyer_reference = rechnung.rechnungsnummer or str(rechnung.id)

    # BT-13: Bestellnummer des Kunden - Feld bewusst nur bei tatsächlich vorhandenem Wert
    # setzen, kein Platzhalter wie "keine Referenz" (führt bei Validatoren zu Fehlern, Issue #387).
    if rechnung.kunden_bestellnummer:
        doc.trade.agreement.buyer_order.issuer_assigned_id = rechnung.kunden_bestellnummer

    # ── Lieferdatum (XRechnung BR-13: Pflicht – Fallback auf Rechnungsdatum) ───
    doc.trade.delivery.event.occurrence._value = rechnung.leistung_von or rechnung.datum

    # ── Leistungszeitraum (BT-73/BT-74: Rechnungsperiode Beginn/Ende) ──────────
    # Nur bei echtem Zeitraum (beide Felder gesetzt) - ein einzelnes Leistungsdatum
    # ohne leistung_bis ist bereits oben als Lieferdatum (BT-72) abgebildet, siehe
    # identische Unterscheidung in pdf_rechnung_base.py.
    if rechnung.leistung_von and rechnung.leistung_bis:
        doc.trade.settlement.period.start._value = rechnung.leistung_von
        doc.trade.settlement.period.end._value = rechnung.leistung_bis

    # ── Rechnungsbegleitende Dokumente (Stundennachweis, Vertrag u.ä.) ─────────
    # Werden als AdditionalReferencedDocument mit eingebettetem Base64-Anhang in die
    # PDF/A-3 aufgenommen (Issue #383) - TypeCode 916 ("Referenced document") ist die in
    # ZUGFeRD/Factur-X übliche Kennung für generische Anhänge ohne eigenen Beleg-Typ.
    for anhang in getattr(rechnung, "zugferd_anhaenge", []):
        beleg = anhang.beleg
        pfad = APP_DATA_DIR / "uploads" / beleg.dateiname
        if not pfad.exists():
            continue
        ref_doc = AdditionalReferencedDocument()
        ref_doc.issuer_assigned_id = str(anhang.id)
        ref_doc.type_code._text = "916"
        ref_doc.name = anhang.bezeichnung or beleg.original_name
        inhalt_b64 = base64.b64encode(pfad.read_bytes()).decode("ascii")
        ref_doc.attached_object = (
            beleg.mime_type or "application/octet-stream",
            beleg.original_name,
            inhalt_b64,
        )
        doc.trade.agreement.additional_references.add(ref_doc)

    # ── Fälligkeitsdatum + Zahlungshinweis ───────────────────────────────────
    iban = unternehmen.get("iban") or ""
    bic  = unternehmen.get("bic") or ""
    if rechnung.faellig_am or iban:
        pt = PaymentTerms()
        faellig_str = rechnung.faellig_am.strftime("%d.%m.%Y") if rechnung.faellig_am else "sofort"
        offen = _d(rechnung.brutto_gesamt or 0) - _d(rechnung.bezahlt_betrag or 0)
        betrag_str = f"{offen:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " \u20ac"
        if iban and rechnung.typ == "ausgang":
            hinweis = (
                f"Bitte \u00fcberweisen Sie {betrag_str} bis {faellig_str} "
                f"unter Angabe der Rechnungsnummer {rechnung.rechnungsnummer or ''} "
                f"auf IBAN {iban}"
            )
            if bic:
                hinweis += f"  \u00b7  BIC {bic}"
            hinweis += "."
        else:
            hinweis = f"Zahlbar bis {faellig_str}."
        pt.description._text = hinweis
        if rechnung.faellig_am:
            pt.due._value = rechnung.faellig_am
        doc.trade.settlement.terms.add(pt)

    # ── Zahlungsweise (SEPA-Überweisung) ──────────────────────────────────────
    if unternehmen.get("iban"):
        pm = PaymentMeans()
        pm.type_code._text = "58"
        pm.payee_account.iban = unternehmen["iban"]
        if unternehmen.get("bic"):
            pm.payee_institution.bic = unternehmen["bic"]
        doc.trade.settlement.payment_means.add(pm)

    # ── Verwendungszweck ──────────────────────────────────────────────────────
    doc.trade.settlement.payment_reference = rechnung.rechnungsnummer or str(rechnung.id)

    # ── Währung ───────────────────────────────────────────────────────────────
    doc.trade.settlement.currency_code = "EUR"

    # ── Positionen ────────────────────────────────────────────────────────────
    # rechnungspositionen.netto ist seit Migration 139 (Issue #332) der reine
    # Nettoeinzelpreis (Stückpreis, VOR Menge und Rabatt) - .brutto/.ust_betrag sind
    # dagegen bereits fertige Positionssummen (Menge x Einzelpreis, NACH Rabatt).
    # brutto - ust_betrag ergibt daher die korrekte Netto-Positionssumme, unabhängig
    # vom eingabemodus (netto/brutto) - direkt pos.netto als Zeilensumme zu verwenden
    # ignorierte Menge und Rabatt komplett (Issue #389).
    for pos in sorted(rechnung.positionen, key=lambda p: p.position_nr):
        li = LineItem()
        li.document.line_id._text = str(pos.position_nr)
        li.product.name = pos.beschreibung or "-"

        netto_gesamt = _d(pos.brutto or 0) - _d(pos.ust_betrag or 0)

        # Nettopreis pro Einheit (nach Rabatt) - BT-146
        einheit_code = _einheit_code(pos.einheit)
        netto_pro_einheit = _d(netto_gesamt / pos.menge) if pos.menge else netto_gesamt
        li.agreement.net.amount = netto_pro_einheit
        li.agreement.net.basis_quantity = (Decimal("1"), einheit_code)

        # Menge
        li.delivery.billed_quantity = (_d(pos.menge), einheit_code)

        # Steuer auf Position – nur Kategorie+Satz, kein Betrag (EN16931-Regel)
        li.settlement.trade_tax.type_code = "VAT"
        li.settlement.trade_tax.category_code = _steuerkategorie(pos.ust_satz, ist_ku, sonderfall)
        if not ist_nicht_steuerbar:  # BR-O-05: bei O kein Steuersatz
            li.settlement.trade_tax.rate_applicable_percent = _ust_satz(pos.ust_satz)

        # Zeilensumme (BT-131) – Menge x Einzelpreis, nach Rabatt
        li.settlement.monetary_summation.total_amount = netto_gesamt

        doc.trade.items.add(li)

    # ── Steuer-Zusammenfassung (pro USt-Satz) ─────────────────────────────────
    steuern: dict[str, dict] = {}
    for pos in rechnung.positionen:
        key = str(pos.ust_satz)
        if key not in steuern:
            steuern[key] = {"satz": pos.ust_satz, "basis": Decimal("0"), "betrag": Decimal("0")}
        steuern[key]["basis"] += _d(pos.brutto or 0) - _d(pos.ust_betrag or 0)
        steuern[key]["betrag"] += _d(pos.ust_betrag or 0)

    for eintrag in steuern.values():
        tax = ApplicableTradeTax()
        tax.type_code = "VAT"
        kategorie = _steuerkategorie(eintrag["satz"], ist_ku, sonderfall)
        tax.category_code = kategorie
        # Kopf-Ebene immer mit Satz (XRechnung BR-DE-14, bei O: 0) - nur die Positionen von
        # Kategorie O tragen keinen Satz (BR-O-05)
        tax.rate_applicable_percent = _ust_satz(eintrag["satz"])
        tax.basis_amount = _d(eintrag["basis"])
        tax.calculated_amount = _d(eintrag["betrag"])
        if sonderfall and kategorie == sonderfall[0]:
            tax.exemption_reason_code = sonderfall[1]
            tax.exemption_reason = sonderfall[2]
        elif ist_ku and eintrag["satz"] == 0:
            tax.exemption_reason = "Umsatzsteuerbefreiung gemäß §19 UStG"
        doc.trade.settlement.trade_tax.add(tax)

    # ── Gesamtsummen ──────────────────────────────────────────────────────────
    # BR-CO-10/BR-CO-14: aus Positionen berechnen, nicht DB-Summen verwenden
    line_total = sum(e["basis"]  for e in steuern.values())
    tax_total  = sum(e["betrag"] for e in steuern.values())
    grand_total = line_total + tax_total
    prepaid     = rechnung.bezahlt_betrag or Decimal("0")

    ms = doc.trade.settlement.monetary_summation
    ms.line_total      = _d(line_total)
    ms.charge_total    = Decimal("0.00")
    ms.allowance_total = Decimal("0.00")
    ms.tax_basis_total = _d(line_total)
    ms.tax_total       = (_d(tax_total), "EUR")
    ms.grand_total     = _d(grand_total)
    ms.prepaid_total   = _d(prepaid)
    ms.due_amount      = _d(grand_total - prepaid)

    # EXTENDED-Schema nötig damit DefinedTradeContact (BR-DE-2) serialisiert wird
    xml = doc.serialize(schema="FACTUR-X_EXTENDED")

    # XML-Deklaration: einfache Anführungszeichen → doppelte, utf-8 → UTF-8
    xml = xml.replace(b"<?xml version='1.0' encoding='utf-8'?>",
                      b'<?xml version="1.0" encoding="UTF-8"?>')

    # xmlns:xsi entfernen (unused, stört manche XSLT-Renderer wie hellocash)
    xml = xml.replace(b' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"', b'')

    # Namespace-Reihenfolge im Root-Element korrigieren: rsm, ram, qdt, udt, xs
    # (hellocash zeigt sonst nur rohen XML-Baum statt formatierter eRechnung)
    import re as _re
    _m = _re.search(rb'<rsm:CrossIndustryInvoice([^>]*)>', xml)
    if _m:
        _ns_map: dict[str, str] = {}
        for _nm in _re.finditer(rb'xmlns:(\w+)="([^"]*)"', _m.group(1)):
            _ns_map[_nm.group(1).decode()] = _nm.group(2).decode()
        _order = ["rsm", "ram", "qdt", "udt", "xs"]
        _attrs = [f'xmlns:{p}="{_ns_map[p]}"' for p in _order if p in _ns_map]
        _attrs += [f'xmlns:{p}="{u}"' for p, u in _ns_map.items() if p not in _order]
        _new_tag = ('<rsm:CrossIndustryInvoice ' + ' '.join(_attrs) + '>').encode()
        xml = xml[:_m.start()] + _new_tag + xml[_m.end():]

    return xml


def generate_zugferd_pdf(rechnung, unternehmen: dict) -> bytes:
    """Erzeugt ein ZUGFeRD PDF/A-3 – normales PDF + eingebettetes XRechnung-XML."""
    # saxonche ist Top-Level-Import in facturx aber wird nur für XSD/Schematron-Validierung
    # gebraucht – wir nutzen check_xsd=False, check_schematron=False. Falls saxonche im
    # PyInstaller-Build nicht korrekt gebündelt ist, Stub eintragen damit der Import nicht fehlschlägt.
    import sys, types
    if "saxonche" not in sys.modules:
        try:
            import saxonche  # noqa: F401
        except (ImportError, OSError):
            sys.modules["saxonche"] = types.ModuleType("saxonche")

    import facturx
    import facturx.facturx as _fx
    from utils.pdf_rechnung import generate_rechnung_pdf

    # sRGB-OutputIntent für PDF/A-3-Konformität
    pdf_bytes = generate_rechnung_pdf(rechnung, unternehmen, ist_kopie=False, ist_entwurf=False,
                                      mit_output_intent=True)
    xml_bytes = generate_zugferd_xml(rechnung, unternehmen)

    # XRechnung-Profil in facturx registrieren (einmalig; idempotent)
    if "xrechnung" not in _fx.FACTURX_LEVEL2xsd:
        _fx.FACTURX_LEVEL2xsd["xrechnung"] = _fx.FACTURX_LEVEL2xsd["en16931"]
    if "xrechnung" not in _fx.FACTURX_LEVEL2xmp:
        _fx.FACTURX_LEVEL2xmp["xrechnung"] = "XRECHNUNG"

    # Pflicht-Dateiname für XRechnung laut ZUGFeRD 2.3.2 §6.2
    _orig_fname = _fx.FACTURX_FILENAME
    _fx.FACTURX_FILENAME = "xrechnung.xml"

    # generate_from_binary nutzt NamedTemporaryFile ohne delete=False – auf Windows
    # kann die Temp-Datei nicht von einem zweiten Handle geöffnet werden (PermissionError).
    # Workaround: Temp-Datei selbst anlegen, generate_from_file aufrufen, dann einlesen.
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(prefix="facturx-", suffix=".pdf", delete=False)
    try:
        tmp.write(pdf_bytes)
        tmp.flush()
        tmp.close()  # explizit schließen damit generate_from_file es öffnen kann (Windows)
        _fx.generate_from_file(
            tmp.name,
            xml_bytes,
            flavor="factur-x",
            level="xrechnung",
            check_xsd=False,
            check_schematron=False,
            xmp_compression=False,
            afrelationship="alternative",
        )
        with open(tmp.name, "rb") as f:
            result = f.read()
    finally:
        _fx.FACTURX_FILENAME = _orig_fname
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    return result
