"""Schnell-Test: prüft ob der CSV-Parser alle Testdateien korrekt einliest."""
import sys
sys.path.insert(0, '/home/nicole/projekte/RechnungsFee/src/backend')
from utils.bank_csv_parser import parse_csv

BASE = '/home/nicole/projekte/RechnungsFee/docs/testdaten/'

tests = [
    ("sparkasse-mt940-test.csv", {
        "Buchungstag": "datum", "Valutadatum": "valuta", "Buchungstext": "buchungstext",
        "Verwendungszweck": "verwendungszweck", "Beguenstigter/Zahlungspflichtiger": "partner_name",
        "Kontonummer/IBAN": "partner_iban", "Betrag": "betrag",
    }, ";", "ISO-8859-1", ",", "%d.%m.%y", 0),

    ("sparkasse-camt-test.csv", {
        "Buchungstag": "datum", "Wertstellung": "valuta", "Buchungstext": "buchungstext",
        "Verwendungszweck": "verwendungszweck", "Beguenstigter/Zahlungspflichtiger": "partner_name",
        "Kontonummer/IBAN": "partner_iban", "Betrag": "betrag",
    }, ";", "UTF-8", ",", "%d.%m.%y", 0),

    ("dkb-test.csv", {
        "Buchungsdatum": "datum", "Wertstellung": "valuta", "Status": "buchungstext",
        "Zahlungspflichtige*r": "partner_name", "Verwendungszweck": "verwendungszweck",
        "IBAN": "partner_iban", "Betrag (€)": "betrag",
    }, ";", "UTF-8", ",", "%d.%m.%Y", 0),

    ("ing-test.csv", {
        "Buchung": "datum", "Valuta": "valuta",
        "Auftraggeber/Empf\xe4nger": "partner_name",
        "Buchungstext": "buchungstext", "Verwendungszweck": "verwendungszweck", "Betrag": "betrag",
    }, ";", "ISO-8859-1", ",", "%d.%m.%Y", 13),

    ("volksbank-test.csv", {
        "Buchungstag": "datum", "Valuta": "valuta",
        "Auftraggeber/Beguenstigter": "partner_name",
        "Verwendungszweck": "verwendungszweck", "IBAN": "partner_iban", "Betrag": "betrag",
    }, ";", "ISO-8859-1", ",", "%d.%m.%Y", 0),

    ("commerzbank-test.csv", {
        "Buchungstag": "datum", "Wertstellung": "valuta", "Buchungstext": "buchungstext",
        "Auftraggeber / Beg\xfcnstigter": "partner_name",
        "IBAN": "partner_iban", "Betrag": "betrag",
        "W\xe4hrung": "waehrung", "Verwendungszweck": "verwendungszweck",
    }, ";", "UTF-8", ",", "%d.%m.%Y", 0),

    ("paypal-test.csv", {
        "Datum": "datum", "Name": "partner_name", "Typ": "buchungstext",
        "Betreff": "verwendungszweck", "Brutto": "betrag",
        "W\xe4hrung": "waehrung", "Transaktionscode": "referenz",
    }, ",", "UTF-8", ",", "%d.%m.%Y", 0),
]

print()
alle_ok = True
for fname, mapping, delim, enc, dsep, dfmt, skip in tests:
    raw = open(BASE + fname, "rb").read()
    rows = parse_csv(raw, mapping, delim, enc, dsep, dfmt, skip)
    ok = len(rows) > 0
    if not ok:
        alle_ok = False
    symbol = "✓" if ok else "✗"
    print(f"  {symbol} {fname:<35} {len(rows)} Transaktionen")
    if ok and rows:
        r = rows[0]
        print(f"      Datum: {r['datum']}  Betrag: {r['betrag']}  Partner: {r['partner_name']}")

print()
print("Alle OK" if alle_ok else "FEHLER bei mindestens einer Datei")
