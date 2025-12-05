# Bank-CSV Template

Diese Vorlage zeigt, wie eine anonymisierte Bank-CSV aussehen sollte.

---

## 📋 Beispiel-CSV (anonymisiert)

**Sparkasse-Format (Beispiel):**
```csv
Buchungstag;Valuta;Auftraggeber/Empfänger;Buchungstext;Verwendungszweck;Betrag;Währung;Saldo
01.12.2025;01.12.2025;Arbeitgeber GmbH;Gehalt;Gehalt Dezember 2025;2500,00;EUR;5430,20
03.12.2025;03.12.2025;Vermieter Name;Überweisung;Miete Wohnung;-850,00;EUR;4580,20
05.12.2025;05.12.2025;Supermarkt XY;Kartenzahlung;Einkauf;-45,20;EUR;4535,00
08.12.2025;08.12.2025;Max Mustermann;Überweisung;Rückzahlung;100,00;EUR;4635,00
10.12.2025;10.12.2025;Versicherung AG;Lastschrift;Kfz-Versicherung;-125,50;EUR;4509,50
```

**Volksbank-Format (Beispiel):**
```csv
Datum,Wertstellung,Buchungstext,Empfänger,IBAN,BIC,Betrag,Währung
01.12.2025,01.12.2025,Gehalt,Arbeitgeber GmbH,DE89370400440532013000,COBADEFFXXX,2500.00,EUR
03.12.2025,03.12.2025,Miete,Vermieter Name,DE89370400440532013001,COBADEFFXXX,-850.00,EUR
05.12.2025,05.12.2025,Kartenzahlung,Supermarkt XY,,,45.20,EUR
```

**DKB-Format (Beispiel):**
```csv
"Buchungstag";"Wertstellung";"Buchungstext";"Auftraggeber / Begünstigter";"Verwendungszweck";"Kontonummer";"BLZ";"Betrag (EUR)";"Gläubiger-ID";"Mandatsreferenz";"Kundenreferenz"
"01.12.2025";"01.12.2025";"Gehalt";"Arbeitgeber GmbH";"Lohn/Gehalt";"DE89370400440532013000";"12345678";"2500,00";"";"";"2025-12-001"
"03.12.2025";"03.12.2025";"Überweisung";"Vermieter Name";"Miete Dezember";"DE89370400440532013001";"12345679";"-850,00";"";"";""
"05.12.2025";"05.12.2025";"Kartenzahlung";"Supermarkt XY";"Einkauf";"";"";"45,20";"";"";""
```

---

## 🗂️ Felder-Mapping

So werden die CSV-Felder auf RechnungsPilot-Felder gemappt:

| Bank-Feld | Bedeutung | RechnungsPilot-Feld | Pflicht |
|-----------|-----------|---------------------|---------|
| Buchungstag / Datum | Transaktionsdatum | `datum` | ✅ Ja |
| Valuta / Wertstellung | Wertstellungsdatum | `valuta` | 🟡 Optional |
| Auftraggeber/Empfänger | Gegenseite | `partner` | ✅ Ja |
| Verwendungszweck | Beschreibung | `verwendungszweck` | ✅ Ja |
| Buchungstext | Transaktionstyp | `buchungstext` | 🟡 Optional |
| Betrag | Betrag (+ = Eingang, - = Ausgang) | `betrag` | ✅ Ja |
| Währung | Währung | `waehrung` | ✅ Ja |
| Saldo | Kontostand nach Buchung | `saldo` | 🟡 Optional |
| IBAN | IBAN der Gegenseite | `iban` | 🟡 Optional |
| BIC | BIC der Gegenseite | `bic` | 🟡 Optional |
| Gläubiger-ID | SEPA-Lastschrift ID | `glaeubigerid` | 🟡 Optional |
| Mandatsreferenz | SEPA-Mandat | `mandatsreferenz` | 🟡 Optional |

---

## ✅ Anonymisierungs-Regeln

### ❌ NICHT teilen (ersetzen):

1. **Kontonummer / IBAN:**
   - `DE12345678901234567890` → `DE89370400440532013000`
   - `AT123456789012345678` → `AT611904300234573201`

2. **Namen:**
   - `Schmidt, Peter` → `Mustermann, Max`
   - `Müller GmbH` → `Firma GmbH`
   - `Vermieter Vorname Nachname` → `Vermieter Name`

3. **Sensible Verwendungszwecke:**
   - `Arztrechnung Dr. Med. XY` → `Arztrechnung`
   - `Spende Organisation ABC` → `Spende`
   - `Kredittilgung Darlehen 123456` → `Kredittilgung`

4. **BIC (optional):**
   - `BYLADEM1001` → `COBADEFFXXX`

5. **Beträge (optional, wenn gewünscht):**
   - `1.234,56` → `1.000,00`
   - `47,23` → `50,00`

### ✅ BEHALTEN (nicht ändern):

1. **Header-Zeile** - Spaltenköpfe müssen original bleiben!
2. **Trennzeichen** - Semikolon, Komma, etc. beibehalten
3. **Anführungszeichen** - `"` oder `'` wie im Original
4. **Datumsformat** - `DD.MM.YYYY` oder `YYYY-MM-DD` beibehalten
5. **Dezimaltrennzeichen** - Komma oder Punkt wie im Original
6. **Währungskürzel** - `EUR`, `USD`, etc.
7. **Anzahl Spalten** - Alle Spalten behalten, auch wenn leer

---

## 🔧 Verwendung

### Für Contributors:
1. Exportiere CSV aus deinem Online-Banking
2. Anonymisiere nach obigen Regeln (10-20 Zeilen reichen)
3. Erstelle GitHub Issue mit [Bank-CSV Template](../../.github/ISSUE_TEMPLATE/bank-csv-format.md)
4. Hänge anonymisierte CSV an

### Für Entwickler:
Diese Templates dienen als:
- Referenz für Parser-Implementierung
- Test-Fixtures für Unit-Tests
- Dokumentation der Bank-spezifischen Formate

---

## 📚 Weitere Informationen

- [CONTRIBUTING.md](../../CONTRIBUTING.md#bank-csv-format-beitragen) - Vollständige Anleitung
- [Issue Template](../../.github/ISSUE_TEMPLATE/bank-csv-format.md) - Bank-CSV einreichen
- [vorlagen/README.md](../README.md) - Übersicht aller Vorlagen
