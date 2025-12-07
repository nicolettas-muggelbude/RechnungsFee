# Bank-CSV Formate

Dieser Ordner enthält Beispiel-CSVs verschiedener Banken für die Import-Funktion.

---

## 🏦 Unterstützte Banken & Zahlungsdienste

### Geplant für MVP:

- [ ] **Sparkasse** - Deutschlands größtes Bankennetz
- [ ] **Volksbank / Raiffeisenbank** - Genossenschaftsbanken
- [ ] **Deutsche Bank** - Großbank
- [ ] **Commerzbank** - Großbank
- [ ] **Postbank** - Retail-Bank
- [ ] **DKB (Deutsche Kreditbank)** - Online-Bank
- [ ] **ING (ehem. ING-DiBa)** - Online-Bank
- [ ] **N26** - Mobile Bank
- [ ] **Comdirect** - Online-Bank
- [ ] **Consorsbank** - Online-Broker mit Girokonto
- [ ] **PayPal** - Zahlungsdienstleister (wichtig für Online-Geschäft)

### Später:

- [ ] Targobank
- [ ] Santander
- [ ] HypoVereinsbank
- [ ] Commerzbank
- [ ] PSD Bank
- [ ] Sparda-Bank
- [ ] Tomorrow Bank
- [ ] Revolut
- [ ] C24
- [ ] Trade Republic (mit Girokonto)

---

## 📂 Ordnerstruktur

```
bank-csv/
├── README.md                  # Diese Datei
├── TEMPLATE.md                # Vorlage und Anonymisierungs-Anleitung
├── sparkasse-lzo-mt940.csv    # ✅ Sparkasse/LZO - MT940 Format
├── sparkasse-lzo-camt-v2.csv  # ✅ Sparkasse/LZO - CAMT V2 Format
├── sparkasse-lzo-camt-v8.csv  # ✅ Sparkasse/LZO - CAMT V8 Format
├── paypal.csv                 # ✅ PayPal Aktivitätsbericht
├── commerzbank.csv            # ✅ Commerzbank - Umsatzübersicht
├── volksbank.csv              # (noch nicht vorhanden)
├── dkb.csv                    # (noch nicht vorhanden)
├── ing.csv                    # (noch nicht vorhanden)
├── n26.csv                    # (noch nicht vorhanden)
└── ...
```

**Hinweis:** Manche Banken bieten mehrere Export-Formate an (z.B. MT940, CAMT).
In diesem Fall erstellen wir separate Dateien pro Format.

---

## 🤝 Mitmachen

### Deine Bank fehlt?

**Du kannst helfen!**

1. 📥 **Exportiere** CSV aus deinem Online-Banking
2. 🔒 **Anonymisiere** sensible Daten (siehe [TEMPLATE.md](TEMPLATE.md))
3. 📝 **Erstelle** ein [GitHub Issue](../../.github/ISSUE_TEMPLATE/bank-csv-format.md)
4. 📎 **Hänge** die anonymisierte CSV an
5. ✅ **Fertig!** Wir fügen sie hinzu

**Schritt-für-Schritt-Anleitung:** [CONTRIBUTING.md](../../CONTRIBUTING.md#bank-csv-format-beitragen)

---

## 🔍 Format-Unterschiede

Jede Bank hat ihr eigenes CSV-Format. Typische Unterschiede:

| Aspekt | Varianten |
|--------|-----------|
| **Trennzeichen** | `;` (Semikolon), `,` (Komma), `\t` (Tab) |
| **Encoding** | UTF-8, ISO-8859-1, Windows-1252 |
| **Dezimaltrennzeichen** | `,` (1.234,56) oder `.` (1,234.56) |
| **Datumsformat** | DD.MM.YYYY, YYYY-MM-DD, MM/DD/YYYY |
| **Anführungszeichen** | `"..."`, `'...'`, keine |
| **Header-Zeilen** | 0, 1, oder mehrere |
| **Fußzeilen** | Summen, Saldo, Metadaten |
| **Spaltenanzahl** | 5-15+ Spalten |
| **Besonderheiten** | Mehrzeilig, HTML, Sonderzeichen |

**RechnungsPilot wird alle gängigen Formate unterstützen!**

---

## 🔄 Mehrere Formate pro Bank

Manche Banken bieten verschiedene Export-Formate an:

### **MT940 (SWIFT Message Type 940)**
- Standard-Format für elektronische Kontoauszüge
- Ursprünglich für SWIFT-Nachrichten entwickelt
- Viele Sparkassen und Banken bieten CSV-Export im MT940-Format
- **Beispiel:** `sparkasse-lzo-mt940.csv`

### **CAMT (Cash Management - ISO 20022)**
- Moderner Standard für Zahlungsverkehr
- ISO 20022 XML-basiert, aber einige Banken bieten CSV-Varianten
- **Versionen:** V2, V8 (unterschiedliche Schema-Versionen)
- **Beispiel:** `sparkasse-lzo-camt-v2.csv`, `sparkasse-lzo-camt-v8.csv`

### **Andere Formate**
- **Eigenformate** - Bank-spezifische CSV-Strukturen
- **SEPA PAIN** - Payment Initiation (selten als CSV)
- **Umsatzliste** - Vereinfachte Formate für Privatkunden

**Namenskonvention bei mehreren Formaten:**
```
<bank>-<format>.csv         # Bei einem Format
<bank>-<format>-<version>.csv  # Bei mehreren Versionen
```

**Beispiele:**
- `sparkasse-lzo-mt940.csv`
- `sparkasse-lzo-camt-v2.csv`
- `dkb-standard.csv` (wenn nur ein Format)
- `volksbank-mt940.csv`

---

## 🛠️ Für Entwickler

### Import-Parser-Implementierung:

```python
# Beispiel: Sparkasse-Parser
class SparkasseCSVParser:
    delimiter = ';'
    encoding = 'ISO-8859-1'
    date_format = '%d.%m.%Y'
    decimal_sep = ','

    column_mapping = {
        'Buchungstag': 'datum',
        'Auftraggeber/Empfänger': 'partner',
        'Verwendungszweck': 'verwendungszweck',
        'Betrag': 'betrag',
        'Währung': 'waehrung',
    }
```

### Test-Fixtures:

```python
# tests/test_bank_import.py
import pytest
from bank_import import parse_bank_csv

def test_sparkasse_import():
    result = parse_bank_csv('vorlagen/bank-csv/sparkasse.csv', 'sparkasse')
    assert len(result) > 0
    assert result[0]['betrag'] is not None
```

---

## 📊 Status-Übersicht

| Bank/Dienst | Format | CSV vorhanden | Parser implementiert | Getestet |
|-------------|--------|---------------|----------------------|----------|
| Sparkasse/LZO | MT940 | ✅ | ❌ | ❌ |
| Sparkasse/LZO | CAMT V2 | ✅ | ❌ | ❌ |
| Sparkasse/LZO | CAMT V8 | ✅ | ❌ | ❌ |
| PayPal | Aktivitätsbericht | ✅ | ❌ | ❌ |
| Commerzbank | Umsatzübersicht | ✅ | ❌ | ❌ |
| Volksbank | - | ❌ | ❌ | ❌ |
| DKB | - | ❌ | ❌ | ❌ |
| ING | - | ❌ | ❌ | ❌ |
| N26 | - | ❌ | ❌ | ❌ |

**Legende:**
- ✅ Vorhanden
- ⏳ Geplant
- ❌ Noch offen

**Hilf mit, diese Tabelle mit ✅ zu füllen!**

---

## 🔐 Datenschutz

**WICHTIG:** Alle CSV-Dateien in diesem Ordner enthalten **nur anonymisierte Beispieldaten**!

- ❌ Keine echten Kontonummern / IBANs
- ❌ Keine echten Namen
- ❌ Keine sensiblen Verwendungszwecke
- ✅ Nur Format-Beispiele zur Entwicklung

**Falls versehentlich echte Daten committed wurden:**
1. Sofort Issue erstellen
2. History bereinigen (git filter-branch / BFG Repo-Cleaner)
3. Force-Push auf allen Branches

---

## 📚 Weitere Ressourcen

- [TEMPLATE.md](TEMPLATE.md) - Anonymisierungs-Vorlage
- [Issue Template](../../.github/ISSUE_TEMPLATE/bank-csv-format.md) - Bank-CSV einreichen
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Contribution Guidelines
- [claude.md](../../claude.md) - Kategorie 5: Bank-Integration (Details)
