---
name: Bank-CSV Format einreichen
about: Hilf mit, deine Bank zu unterstützen
title: 'Bank-CSV: [Bankname]'
labels: 'enhancement, bank-integration'
assignees: ''
---

## 🏦 Bank-Informationen

**Bankname:** [z.B. Sparkasse Musterstadt, Volksbank eG, DKB]
**Export-Typ:** [z.B. "Umsätze CSV", "Kontoauszug", "Tagesumsätze"]
**Online-Banking URL:** [Optional, z.B. sparkasse.de]

---

## 📋 CSV-Struktur

**Trennzeichen:** [z.B. Semikolon (;), Komma (,), Tabulator]
**Encoding:** [z.B. UTF-8, ISO-8859-1, Windows-1252]
**Dezimaltrennzeichen:** [z.B. Komma (1.234,56) oder Punkt (1,234.56)]
**Datumsformat:** [z.B. DD.MM.YYYY, YYYY-MM-DD]

**Spalten (in Reihenfolge):**
1. [z.B. Buchungstag]
2. [z.B. Valuta]
3. [z.B. Auftraggeber/Empfänger]
4. [z.B. Verwendungszweck]
5. [z.B. Betrag]
6. [...]

---

## 📎 Beispieldaten

Bitte hänge eine **anonymisierte** CSV-Datei an.

### ⚠️ Anonymisierungs-Checkliste:

- [ ] Kontonummer / IBAN entfernt oder ersetzt (z.B. durch `DE89370400440532013000`)
- [ ] Echte Namen ersetzt durch Beispielnamen (`Max Mustermann`, `Firma GmbH`)
- [ ] Sensible Verwendungszwecke anonymisiert (`Gehalt`, `Miete`, `Einkauf Supermarkt`)
- [ ] Optional: Beträge anonymisiert (z.B. gerundet auf runde Zahlen)
- [ ] Header-Zeile (Spaltenköpfe) **NICHT** verändert
- [ ] CSV-Struktur (Trennzeichen, Format) **NICHT** verändert

**Tipp:** Siehe [Anleitung zur Anonymisierung](../../CONTRIBUTING.md#bank-csv-format-beitragen)

---

## 📊 Zusatzinformationen

**Besonderheiten:**
- [z.B. Header-Zeilen mit Metadaten, Fußzeilen mit Summen, Sonderzeichen]
- [z.B. Mehrzeilige Verwendungszwecke, HTML-Tags, etc.]

**Export-Häufigkeit:**
- [ ] Täglich verfügbar
- [ ] Wöchentlich
- [ ] Monatlich
- [ ] Nur auf Anfrage

**Export-Umfang:**
- [ ] Einzelnes Konto
- [ ] Alle Konten
- [ ] Mit Saldo/Kontostand
- [ ] Ohne Saldo

---

## 🙏 Danke für deinen Beitrag!

Deine Hilfe macht RechnungsPilot besser für alle! 🚀
