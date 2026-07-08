"""
Generiert Test-CSV-Dateien für alle unterstützten Bank-Templates.
Ausführen: python generate_test_csv.py
Die erzeugten .csv-Dateien können direkt im Bank-CSV-Import hochgeladen werden.
"""

from pathlib import Path

OUT = Path(__file__).parent

# ---------------------------------------------------------------------------
# Sparkasse MT940  (ISO-8859-1, Semikolon, Datumsformat %d.%m.%y)
# ---------------------------------------------------------------------------

sparkasse_mt940 = """\
Auftragskonto;Buchungstag;Valutadatum;Buchungstext;Verwendungszweck;Beguenstigter/Zahlungspflichtiger;Kontonummer/IBAN;BLZ/BIC;Betrag;Gläubiger ID;Mandatsreferenz;Kundenreferenz
DE12345678901234567890;01.01.26;01.01.26;Gutschrift;Honorar Januar Webdesign;Muster GmbH;DE98765432109876543210;MARKDEF1XXX;1.500,00;;;
DE12345678901234567890;05.01.26;05.01.26;Lastschrift;Büromiete Januar;Verwaltungs AG;DE11222233334444555566;DEUTDEDB001;-800,00;;;
DE12345678901234567890;10.01.26;10.01.26;Überweisung;Telefonrechnung Jan;Telekom AG;DE55666677778888999900;DTABDE5WXXX;-49,99;;;
DE12345678901234567890;15.01.26;15.01.26;Gutschrift;Rechnung RE-260001;Beispiel UG;DE33444455556666777788;COBADEFFXXX;2.380,00;;;
DE12345678901234567890;20.01.26;20.01.26;Lastschrift;Strom Januar;Stadtwerke GmbH;DE77888899990000111122;SSKMDEMMXXX;-123,50;;;
DE12345678901234567890;25.01.26;25.01.26;Dauerauftrag;Privatentnahme;Eigentümer;DE12345678901234500001;MARKDEF1XXX;-300,00;;;
DE12345678901234567890;28.01.26;28.01.26;Überweisung;Steuerberater Q4;Steuerbüro Müller;DE44555566667777888899;SSKMDEMMXXX;-250,00;;;
DE12345678901234567890;31.01.26;31.01.26;Gutschrift;Honorar Dezember Nachtrag;Klein & Partner;DE66777788889999000011;BELADEBE001;595,00;;;
"""

(OUT / "sparkasse-mt940-test.csv").write_text(sparkasse_mt940, encoding="ISO-8859-1")
print("✓ sparkasse-mt940-test.csv")

# ---------------------------------------------------------------------------
# Sparkasse CAMT  (UTF-8, Semikolon, Datumsformat %d.%m.%y)
# ---------------------------------------------------------------------------

sparkasse_camt = """\
Auftragskonto;Buchungstag;Wertstellung;Buchungstext;Verwendungszweck;Beguenstigter/Zahlungspflichtiger;Kontonummer/IBAN;BIC;Betrag;Glaeubiger ID;Mandatsreferenz
DE12345678901234567890;02.01.26;02.01.26;Gutschrift;Auftrag 2025-047 Beratung;Muster GmbH;DE98765432109876543210;MARKDEF1XXX;2.975,00;;
DE12345678901234567890;07.01.26;07.01.26;Lastschrift;Buchhaltungssoftware Abo;Software House Ltd;DE11222233334444555566;DEUTDEDB001;-39,00;;
DE12345678901234567890;12.01.26;12.01.26;Überweisung;Fahrtkosten Jan Fortbildung;DB Regio AG;DE55666677778888999900;DTABDE5WXXX;-86,00;;
DE12345678901234567890;18.01.26;18.01.26;Gutschrift;Rechnung RE-260003 Webhosting;Hosting AG;DE33444455556666777788;COBADEFFXXX;119,00;;
DE12345678901234567890;22.01.26;22.01.26;Lastschrift;Mobilfunk Geschäft Januar;Telekom AG;DE77888899990000111122;SSKMDEMMXXX;-29,99;;
DE12345678901234567890;29.01.26;29.01.26;Gutschrift;Beratungshonorar Q1 Teilzahlung;Beispiel AG;DE66777788889999000011;BELADEBE001;4.760,00;;
"""

(OUT / "sparkasse-camt-test.csv").write_text(sparkasse_camt, encoding="UTF-8")
print("✓ sparkasse-camt-test.csv")

# ---------------------------------------------------------------------------
# DKB  (UTF-8, Semikolon, Datumsformat %d.%m.%Y)
# ---------------------------------------------------------------------------

dkb = """\
Buchungsdatum;Wertstellung;Status;Zahlungspflichtige*r;Zahlungsempfänger*in;Verwendungszweck;Glaeubiger-ID;Mandatsreferenz;IBAN;Betrag (€)
03.01.2026;03.01.2026;Gebucht;Muster GmbH;;Honorar Januar Entwicklung;;; DE98765432109876543210;2.500,00
08.01.2026;08.01.2026;Gebucht;;Amazon Business;Büromaterial Bestellung;DE35ZZZ00000314591;AMZN0001;DE11222233334444555566;-67,89
14.01.2026;14.01.2026;Gebucht;Beispiel UG;;Rechnung RE-260002;;;DE33444455556666777788;1.190,00
19.01.2026;19.01.2026;Gebucht;;Adobe Systems;Creative Cloud Abo;DE82ZZZ00000123456;ADBE0001;DE55666677778888999900;-54,99
24.01.2026;24.01.2026;Gebucht;;Finanzamt München;USt-Vorauszahlung Q4 2025;;;DE77888899990000111122;-380,00
30.01.2026;30.01.2026;Gebucht;Klein und Partner GbR;;Nachtragszahlung Projekt;;; DE66777788889999000011;850,00
"""

(OUT / "dkb-test.csv").write_text(dkb, encoding="UTF-8")
print("✓ dkb-test.csv")

# ---------------------------------------------------------------------------
# ING  (ISO-8859-1, Semikolon, skip_rows=13, Datumsformat %d.%m.%Y)
# ---------------------------------------------------------------------------
# 13 Metazeilen, dann die eigentliche CSV-Kopfzeile

ing_meta = """\
Umsatzanzeige;;
;;
Kontonummer:;DE12 3456 7890 1234 5678 90 / Girokonto;
;;
Von:;01.01.2026;
Bis:;31.01.2026;
Kontostand vom 31.01.2026:;5.234,56 EUR;
;;
;;
;;
;;
;;
;;
Buchung;Valuta;Auftraggeber/Empfänger;Buchungstext;Verwendungszweck;Betrag;Glaeubiger ID;Mandats ID;IBAN
04.01.2026;04.01.2026;Muster GmbH;Gutschrift;Honorar Dezember Nachzahlung;1.785,00;;;DE98765432109876543210
09.01.2026;09.01.2026;GitHub Inc;Lastschrift;GitHub Pro Abo;-4,00;;;DE11222233334444555566
16.01.2026;16.01.2026;Beispiel UG;Gutschrift;Rechnung RE-260004;892,50;;;DE33444455556666777788
21.01.2026;21.01.2026;Stadtwerke GmbH;Lastschrift;Stromabschlag Januar;-98,00;;;DE77888899990000111122
26.01.2026;26.01.2026;DATEV eG;Lastschrift;DATEV Unternehmen online;-22,50;;;DE55666677778888999900
"""

(OUT / "ing-test.csv").write_text(ing_meta, encoding="ISO-8859-1")
print("✓ ing-test.csv")

# ---------------------------------------------------------------------------
# Volksbank / Raiffeisenbank  (ISO-8859-1, Semikolon, Datumsformat %d.%m.%Y)
# ---------------------------------------------------------------------------

volksbank = """\
Buchungstag;Valuta;Auftraggeber/Beguenstigter;Verwendungszweck;IBAN;BIC;Betrag;Glaeubiger-ID;Mandatsreferenz;Kundenreferenz
06.01.2026;06.01.2026;Muster GmbH;Honorar Webentwicklung;DE98765432109876543210;MARKDEF1XXX;3.570,00;;;
11.01.2026;11.01.2026;Hosteurope GmbH;Hosting Januar;DE11222233334444555566;DEUTDEDB001;-14,99;;;
17.01.2026;17.01.2026;Finanzamt Stuttgart;Einkommensteuer-Vorauszahlung;DE55666677778888999900;DTABDE5WXXX;-750,00;;;
23.01.2026;23.01.2026;Beispiel UG;Teilzahlung Auftrag AU-260001;DE33444455556666777788;COBADEFFXXX;1.547,50;;;
27.01.2026;27.01.2026;IHK Stuttgart;Mitgliedsbeitrag 2026;DE77888899990000111122;SSKMDEMMXXX;-120,00;;;
"""

(OUT / "volksbank-test.csv").write_text(volksbank, encoding="ISO-8859-1")
print("✓ volksbank-test.csv")

# ---------------------------------------------------------------------------
# Commerzbank  (UTF-8, Semikolon, Datumsformat %d.%m.%Y)
# ---------------------------------------------------------------------------

commerzbank = """\
Buchungstag;Wertstellung;Buchungstext;Auftraggeber / Begünstigter;IBAN;BIC;Betrag;Währung;Verwendungszweck
02.01.2026;02.01.2026;Gutschrift;Muster GmbH;DE98765432109876543210;MARKDEF1XXX;4.165,00;EUR;Projektabrechnung Dez 2025
07.01.2026;07.01.2026;Lastschrift;1&1 Versatel;DE11222233334444555566;DEUTDEDB001;-29,99;EUR;Internetanschluss Jan
13.01.2026;13.01.2026;Überweisung;Finanzamt Köln-Süd;DE55666677778888999900;DTABDE5WXXX;-920,00;EUR;USt Q4 2025
18.01.2026;18.01.2026;Gutschrift;Beispiel UG;DE33444455556666777788;COBADEFFXXX;2.261,00;EUR;Rechnung RE-260005
24.01.2026;24.01.2026;Lastschrift;Steuerberater Frank;DE77888899990000111122;SSKMDEMMXXX;-350,00;EUR;Jahresabschluss 2025
29.01.2026;29.01.2026;Gutschrift;Klein und Partner;DE66777788889999000011;BELADEBE001;714,00;EUR;Resthonorar Auftrag 047
"""

(OUT / "commerzbank-test.csv").write_text(commerzbank, encoding="UTF-8")
print("✓ commerzbank-test.csv")

# ---------------------------------------------------------------------------
# PayPal  (UTF-8, Komma, Datumsformat %d.%m.%Y)
# ---------------------------------------------------------------------------

paypal = """\
Datum,Uhrzeit,Zeitzone,Name,Typ,Status,Währung,Brutto,Entgelt,Netto,Absender-E-Mail-Adresse,Empfänger-E-Mail-Adresse,Transaktionscode,Beschreibung,Betreff,Hinweis,Guthaben,Adressstatus
05.01.2026,09:14:00,Europe/Berlin,Muster GmbH,Zahlung erhalten,Abgeschlossen,EUR,"1.190,00","-34,51","1.155,49",zahlung@muster-gmbh.de,hallo@meinefirma.de,8AB123456CD789012,,"Rechnung RE-260001",,,"Bestätigt"
12.01.2026,14:23:00,Europe/Berlin,Adobe Systems,Express-Checkout-Zahlung,Abgeschlossen,EUR,"-54,99","0,00","-54,99",adobe@adobe.com,hallo@meinefirma.de,9XY987654ZA321098,,Creative Cloud Monatsabo,,,
20.01.2026,11:05:00,Europe/Berlin,GitHub Inc,Automatische Zahlung,Abgeschlossen,EUR,"-10,00","0,00","-10,00",billing@github.com,hallo@meinefirma.de,7PQ456789RS123456,,GitHub Copilot Abo,,,
28.01.2026,16:44:00,Europe/Berlin,Beispiel UG,Zahlung erhalten,Abgeschlossen,EUR,"595,00","-17,86","577,14",info@beispiel-ug.de,hallo@meinefirma.de,3LM234567NO890123,,"Rechnung RE-260006",,,"Nicht bestätigt"
"""

(OUT / "paypal-test.csv").write_text(paypal, encoding="UTF-8")
print("✓ paypal-test.csv")

print()
print("Alle Test-CSVs erstellt in:", OUT)
print()
print("Hinweis Encodings:")
print("  sparkasse-mt940-test.csv → ISO-8859-1")
print("  sparkasse-camt-test.csv  → UTF-8")
print("  dkb-test.csv             → UTF-8")
print("  ing-test.csv             → ISO-8859-1  (enthält 13 Metazeilen)")
print("  volksbank-test.csv       → ISO-8859-1")
print("  commerzbank-test.csv     → UTF-8")
print("  paypal-test.csv          → UTF-8")
