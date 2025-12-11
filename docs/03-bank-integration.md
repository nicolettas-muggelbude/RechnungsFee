## **Übersicht**

**Ziel:** Bank-Transaktionen automatisch importieren, um Zahlungsabgleich und Einnahmen-/Ausgaben-Erfassung zu vereinfachen.

**Herausforderungen:**
- ❌ **Jede Bank hat eigenes CSV-Format** (Sparkasse ≠ Volksbank ≠ DKB ≠ N26 ≠ PayPal)
- ❌ **Manche Banken bieten mehrere Formate** (MT940, CAMT V2, CAMT V8)
- ❌ **User kennen Formate nicht** - "MT940" sagt normalen Usern nichts
- ❌ **Power-User brauchen Workaround** für noch nicht unterstützte Banken

**Lösung:** Kombination aus **Automatischer Erkennung** + **Template-System**

---

## **5.1 Automatische Format-Erkennung**

### **Wie funktioniert's?**

**Schritt 1: CSV-Datei analysieren**
```python
def detect_bank_format(csv_file):
    # 1. Delimiter erkennen (;, ,, Tab)
    delimiter = detect_delimiter(csv_file)

    # 2. Header-Zeile auslesen
    header = read_first_line(csv_file, delimiter)

    # 3. Mit bekannten Templates matchen
    for template in BANK_TEMPLATES:
        if match_score(header, template.header) > 0.8:
            return template

    # 4. Fallback: "Unbekanntes Format"
    return None
```

**Matching-Kriterien:**
- **Spaltennamen:** `"Auftragskonto"` → Sparkasse/LZO
- **Spaltenanzahl:** 11 Spalten → MT940, 17 Spalten → CAMT, 41 Spalten → PayPal
- **Delimiter:** `;` (Sparkasse), `,` (Volksbank, PayPal)
- **Typische Felder:** `"Buchungstag"`, `"Valutadatum"`, `"Betrag"`

**Beispiel:**
```
CSV Header: "Auftragskonto";"Buchungstag";"Valutadatum";"Buchungstext"...
           ↓
Match: Sparkasse/LZO MT940 (90% Übereinstimmung)
```

---

## **5.2 Template-System** ⭐

### **Warum Template-System?**

✅ **Für Normal-User:** Automatisch → Keine Ahnung von Formaten nötig
✅ **Für Power-User:** Eigenes Template erstellen → Jede Bank unterstützbar
✅ **Community-getrieben:** Templates teilen → Schnell alle Banken abdecken

---

### **Template-Struktur**

**JSON-Format:**
```json
{
  "id": "sparkasse-lzo-mt940",
  "name": "Sparkasse/LZO - MT940 Format",
  "bank": "Sparkasse/LZO",
  "format": "MT940",
  "version": "1.0",
  "author": "RechnungsFee Team",
  "delimiter": ";",
  "encoding": "UTF-8",
  "decimal_separator": ",",
  "date_format": "DD.MM.YY",

  "column_mapping": {
    "datum": "Buchungstag",
    "valuta": "Valutadatum",
    "buchungstext": "Buchungstext",
    "verwendungszweck": "Verwendungszweck",
    "partner": "Beguenstigter/Zahlungspflichtiger",
    "betrag": "Betrag",
    "waehrung": "Währung",
    "iban": "Kontonummer",
    "bic": "BLZ",
    "saldo": "Saldo",
    "info": "Info"
  },

  "field_types": {
    "datum": "date",
    "betrag": "decimal",
    "saldo": "decimal"
  },

  "validation": {
    "required_columns": ["Buchungstag", "Betrag", "Währung"],
    "min_columns": 10,
    "max_columns": 12
  },

  "example_csv": "vorlagen/bank-csv/sparkasse-lzo-mt940.csv"
}
```

**Template-Felder Erklärung:**

| Feld | Bedeutung | Beispiel |
|------|-----------|----------|
| **id** | Eindeutige Template-ID | `sparkasse-lzo-mt940` |
| **name** | Anzeigename für User | `Sparkasse/LZO - MT940 Format` |
| **bank** | Bankname | `Sparkasse/LZO` |
| **format** | Format-Typ (optional) | `MT940`, `CAMT V2`, `Standard` |
| **delimiter** | Trennzeichen | `;`, `,`, `\t` |
| **encoding** | Zeichensatz | `UTF-8`, `ISO-8859-1`, `Windows-1252` |
| **decimal_separator** | Dezimaltrennzeichen | `,` (1.234,56) oder `.` (1,234.56) |
| **date_format** | Datumsformat | `DD.MM.YYYY`, `YYYY-MM-DD` |
| **column_mapping** | CSV-Spalte → RP-Feld | `"Buchungstag"` → `datum` |
| **field_types** | Datentypen | `date`, `decimal`, `string` |
| **validation** | Erkennungs-Regeln | Min/Max Spalten, Pflichtfelder |

---

### **User-Workflows**

#### **Workflow A: Normal-User (Automatik)**

```
1. User: "Datei importieren" klicken
   ↓
2. CSV hochladen
   ↓
3. System: Automatische Erkennung
   ✅ "Sparkasse/LZO MT940 erkannt" (90% Match)
   ↓
4. Vorschau anzeigen:
   ┌─────────────────────────────────┐
   │ 10 Transaktionen gefunden       │
   │ 05.12.25  -99,80 €  Amazon      │
   │ 05.12.25  -10,57 €  Domain      │
   │ ...                             │
   └─────────────────────────────────┘
   ↓
5. User: "Importieren" → Fertig! ✅
```

**Kein Wissen über MT940 nötig!** 🎯

---

#### **Workflow B: Power-User (Eigenes Template)**

**Situation:** Bank noch nicht unterstützt (z.B. "Sparda-Bank")

```
1. User: CSV importieren
   ↓
2. System: "❌ Unbekanntes Format - Möchtest du ein Template erstellen?"
   ↓
3. Template-Editor öffnen:

   ┌──────────────────────────────────────────┐
   │ Neues Template erstellen                 │
   ├──────────────────────────────────────────┤
   │ Bankname: [Sparda-Bank            ]     │
   │ Format:   [Standard              ]     │
   │                                          │
   │ CSV-Vorschau (erste 3 Zeilen):          │
   │ Datum;Partner;Verwendung;Betrag;EUR     │
   │ 01.12.25;Amazon;Einkauf;-99,80;EUR      │
   │ 03.12.25;Firma;Rechnung;-10,57;EUR      │
   │                                          │
   │ Spalten-Mapping:                         │
   │ [Datum        ] → Buchungstag     ▼     │
   │ [Partner      ] → Partner          ▼     │
   │ [Verwendung   ] → Verwendungszweck ▼     │
   │ [Betrag       ] → Betrag           ▼     │
   │ [EUR          ] → Währung          ▼     │
   │                                          │
   │ Trennzeichen: [ ; ]   Encoding: [UTF-8]  │
   │ Dezimal:      [ , ]   Datum: [DD.MM.YY]  │
   │                                          │
   │ [ Testen ]  [ Speichern ]  [ Abbrechen ] │
   └──────────────────────────────────────────┘

4. User mapped Spalten per Dropdown
   ↓
5. "Testen" → Vorschau mit Mapping
   ↓
6. "Speichern" → Template gespeichert
   ↓
7. Nächster Import: Automatisch erkannt! ✅
```

---

### **Template-Speicherorte**

**Zwei Ebenen:**

1. **System-Templates** (vorinstalliert):
   ```
   /app/templates/banks/
   ├── sparkasse-lzo-mt940.json
   ├── sparkasse-lzo-camt-v2.json
   ├── sparkasse-lzo-camt-v8.json
   ├── paypal.json
   ├── volksbank.json
   ├── dkb.json
   └── ...
   ```

2. **User-Templates** (selbst erstellt):
   ```
   ~/.rechnungspilot/templates/
   ├── sparda-bank.json
   ├── targobank.json
   └── ...
   ```

**Priorität:** User-Templates > System-Templates

---

### **Template-Sharing (Community)**

**Power-User können Templates mit Community teilen:**

**Workflow:**
```
1. User erstellt Template für "Targobank"
   ↓
2. In App: "Template teilen" → Export als JSON
   ↓
3. GitHub Issue erstellen:
   - Template: "Targobank Standard-Format"
   - JSON-Datei anhängen
   - Beispiel-CSV (anonymisiert) anhängen
   ↓
4. Maintainer prüft & fügt hinzu:
   - Template → /app/templates/banks/targobank.json
   - Beispiel → vorlagen/bank-csv/targobank.csv
   ↓
5. Nächstes Release: Targobank für alle verfügbar! ✅
```

**Benefits:**
- ✅ Community trägt bei → Schnell viele Banken unterstützt
- ✅ Power-User helfen Normal-Usern
- ✅ Keine Programmier-Kenntnisse nötig

---

### **Template-Validierung**

**Automatische Tests beim Import:**

```python
def validate_template(template, csv_file):
    checks = []

    # 1. Pflichtfelder vorhanden?
    for required in template.validation.required_columns:
        if required not in csv_header:
            checks.append(f"❌ Pflichtfeld '{required}' fehlt")

    # 2. Spaltenanzahl stimmt?
    if not (template.min_columns <= len(csv_header) <= template.max_columns):
        checks.append(f"❌ Falsche Spaltenanzahl: {len(csv_header)}")

    # 3. Delimiter korrekt?
    if detected_delimiter != template.delimiter:
        checks.append(f"⚠️ Trennzeichen: '{detected_delimiter}' statt '{template.delimiter}'")

    # 4. Datentypen passen?
    if not parse_date(sample_row['datum'], template.date_format):
        checks.append(f"❌ Datumsformat '{template.date_format}' passt nicht")

    return checks
```

**Fehlerbehandlung:**
```
❌ Template-Fehler erkannt:
- Pflichtfeld 'Buchungstag' fehlt
- Datumsformat 'DD.MM.YYYY' passt nicht (Ist: YYYY-MM-DD)

Möchten Sie das Template anpassen?
[ Template editieren ]  [ Abbrechen ]
```

---

### **UI-Konzept**

**Import-Dialog:**

```
┌─────────────────────────────────────────────┐
│ Bank-CSV importieren                        │
├─────────────────────────────────────────────┤
│                                             │
│  [ Datei auswählen ]  sparkasse.csv         │
│                                             │
│  🔍 Format erkannt: Sparkasse/LZO MT940     │
│     (90% Übereinstimmung)                   │
│                                             │
│  ┌────────────────────────────────────────┐ │
│  │ Vorschau (10 Transaktionen):           │ │
│  ├────────────────────────────────────────┤ │
│  │ 05.12.25  -99,80 €  Amazon Payments   │ │
│  │ 05.12.25  -10,57 €  Domain Provider    │ │
│  │ 05.12.25   -5,95 €  LZO Kontoführung  │ │
│  │ 03.12.25  +67,50 €  Eva Schmidt       │ │
│  │ ...                                    │ │
│  └────────────────────────────────────────┘ │
│                                             │
│  ⚙️ Erweiterte Optionen:                    │
│     [ ] Duplikate automatisch erkennen      │
│     [ ] Automatisch kategorisieren          │
│     [ ] Mit Rechnungen abgleichen           │
│                                             │
│  [ Importieren ]  [ Template anpassen ]     │
│                   [ Abbrechen ]             │
└─────────────────────────────────────────────┘
```

**Bei unbekanntem Format:**
```
┌─────────────────────────────────────────────┐
│ Bank-CSV importieren                        │
├─────────────────────────────────────────────┤
│                                             │
│  [ Datei auswählen ]  sparda.csv            │
│                                             │
│  ❌ Format nicht erkannt                    │
│     (Keine Übereinstimmung mit bekannten    │
│      Templates)                             │
│                                             │
│  Möchten Sie ein Template erstellen?        │
│                                             │
│  [ Template-Editor öffnen ]                 │
│  [ Manuelle Zuordnung ]                     │
│  [ Abbrechen ]                              │
└─────────────────────────────────────────────┘
```

---

## **5.3 Private vs. Geschäftliche Transaktionen** ⚠️

### **Grundprinzip: Strikte Trennung**

**Zielgruppe:** Kleinbetriebe, Selbstständige, Freiberufler

**GoBD-Anforderung:** Private Buchungen gehören **NICHT** ins Kassenbuch/in die Buchhaltung!

**Ausnahmen:**
- ✅ **Privatentnahmen** (Geld aus Geschäft → privat)
- ✅ **Einlagen** (Geld aus privat → Geschäft)

---

### **Problem: Mischkonten**

**Realität:** Viele Selbstständige nutzen **ein Konto** für privat + geschäftlich.

**Herausforderung:**
```
Bank-CSV enthält:
- Geschäftliche Transaktionen (gehören in RP)
- Private Transaktionen (gehören NICHT in RP)
- Privatentnahmen/Einlagen (gehören in RP, spezielle Kategorie)
```

**Lösung:** **Filter beim Import** - User markiert, was geschäftlich ist.

---

### **Kontotypen**

**RechnungsFee unterscheidet 3 Kontotypen:**

| Typ | Beschreibung | Import-Verhalten |
|-----|--------------|------------------|
| **Geschäftskonto** | Nur geschäftliche Transaktionen | ✅ Alles importieren (außer explizit markiert) |
| **Privatkonto** | Nur private Transaktionen | ❌ Nicht importierbar |
| **Mischkonto** | Privat + Geschäftlich gemischt | ⚠️ User filtert beim Import |

**Einstellung pro Konto:**
```
Konto: DE89370400440532013000 (Sparkasse)
Typ: [ ] Geschäftskonto
     [x] Mischkonto  ← User wählt beim ersten Import
     [ ] Privatkonto
```

---

### **Import-Workflow: Mischkonto**

**Erweiterte Vorschau mit Filterung:**

```
┌──────────────────────────────────────────────────┐
│ Bank-CSV importieren - Sparkasse (Mischkonto)   │
├──────────────────────────────────────────────────┤
│                                                  │
│  🔍 Format erkannt: Sparkasse/LZO MT940          │
│                                                  │
│  ⚠️ Dies ist ein Mischkonto (privat + geschäftl)│
│     Bitte markieren Sie geschäftliche Buchungen: │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │ Datum     Betrag    Partner        Status │  │
│  ├────────────────────────────────────────────┤  │
│  │ 05.12.25  -99,80 €  Amazon         [x] ✅ │ ← Geschäftlich
│  │ 05.12.25 -850,00 €  Vermieter      [ ] ❌ │ ← Privat (Miete)
│  │ 05.12.25  -10,57 €  Domain         [x] ✅ │ ← Geschäftlich
│  │ 03.12.25  +67,50 €  Eva Schmidt    [ ] ❌ │ ← Privat
│  │ 03.12.25 +119,00 €  Kunde GmbH     [x] ✅ │ ← Geschäftlich
│  │ 01.12.25-1000,00 €  Privatentnahme [P] 💰 │ ← Privatentnahme
│  └────────────────────────────────────────────┘  │
│                                                  │
│  Legende:                                        │
│  [x] ✅ Geschäftlich (wird importiert)          │
│  [ ] ❌ Privat (wird ignoriert)                 │
│  [P] 💰 Privatentnahme/Einlage (wird importiert)│
│                                                  │
│  ⚙️ Auto-Vorschläge:                            │
│     [x] Bekannte Partner automatisch markieren  │
│     [x] Entscheidungen für zukünftige Imports   │
│         merken                                   │
│                                                  │
│  📊 Statistik:                                   │
│     Gesamt: 6 Transaktionen                     │
│     Geschäftlich: 3 (werden importiert)         │
│     Privat: 2 (werden ignoriert)                │
│     Privatentnahme: 1 (wird importiert)         │
│                                                  │
│  [ Alle als geschäftlich ]  [ Importieren ]     │
│  [ Alle als privat ]        [ Abbrechen ]       │
└──────────────────────────────────────────────────┘
```

---

### **Automatische Vorschläge (Smart Filter)**

**System lernt aus bisherigen Entscheidungen:**

```python
# Beispiel: Amazon wurde schon 10x als "geschäftlich" markiert
if partner == "Amazon" and previous_decisions["Amazon"] >= 10:
    suggest_as_business = True

# Beispiel: "Miete" im Verwendungszweck → meist privat
if "miete" in verwendungszweck.lower() and not is_office_rent():
    suggest_as_private = True
```

**User-spezifische Regeln:**
```
Partner "Edeka" → Privat (Lebensmittel)
Partner "Edeka" + Verwendungszweck "Büro" → Geschäftlich (Bürokaffee)
Partner "Telekom" → Geschäftlich (Geschäftstelefon)
```

**Konfigurierbares Regelwerk:**
```
┌────────────────────────────────────────┐
│ Auto-Filter Regeln                     │
├────────────────────────────────────────┤
│ Partner enthält "GmbH" → Geschäftlich  │
│ Partner "Vermieter" → Privat           │
│ Verwendung "Privatentnahme" → [P]      │
│ Verwendung "Einlage" → [P]             │
│                                        │
│ [ Neue Regel hinzufügen ]              │
└────────────────────────────────────────┘
```

---

### **Privatentnahmen & Einlagen**

**Spezialbehandlung:**

**Privatentnahme:**
```
Datum: 01.12.2025
Betrag: -1.000,00 €
Partner: (leer)
Verwendungszweck: "Privatentnahme Dezember"
→ Kategorie: "Privatentnahme" (SKR03: 1800, SKR04: 1200)
→ Wird in EÜR erfasst
→ Reduziert Geschäftsguthaben
```

**Einlage:**
```
Datum: 15.01.2025
Betrag: +5.000,00 €
Partner: (leer)
Verwendungszweck: "Einlage Startkapital"
→ Kategorie: "Einlage" (SKR03: 1800, SKR04: 1200)
→ Wird in EÜR erfasst
→ Erhöht Geschäftsguthaben
```

**UI-Unterstützung:**
```
Transaktion markieren als:
[ ] Geschäftlich
[x] Privatentnahme
[ ] Einlage
[ ] Privat (ignorieren)
```

---

### **Kontenübergreifender Cashflow** 💰

**Problem:** User hat mehrere Konten:
- Geschäftskonto (Sparkasse): 10.000 €
- Mischkonto (PayPal): 2.000 € (davon 1.500 € geschäftlich)

**Frage:** Wie viel **Geschäftsgeld** habe ich insgesamt?

**Lösung: Business-Cashflow Dashboard**

```
┌────────────────────────────────────────────┐
│ Geschäftlicher Cashflow (Alle Konten)     │
├────────────────────────────────────────────┤
│                                            │
│  Sparkasse Geschäftskonto:    10.000,00 € │
│  PayPal (nur geschäftlich):    1.500,00 € │
│  ─────────────────────────────────────────│
│  Gesamt verfügbar:            11.500,00 € │
│                                            │
│  📊 Details:                               │
│  ├─ Forderungen offen:        +2.300,00 € │
│  ├─ Verbindlichkeiten:        -  800,00 € │
│  └─ Erwarteter Cashflow:      13.000,00 € │
│                                            │
│  🧾 Vorsteuer-Übersicht:                   │
│  ├─ Vorsteuer lfd. Monat:     +  427,13 € │
│  ├─ Vorsteuer Quartal (Q4):   +1.284,50 € │
│  └─ Nächste UStVA: 10.01.2026              │
│                                            │
│  [ Konten verwalten ]  [ UStVA ]  [ Export ]│
└────────────────────────────────────────────┘
```

**Nur geschäftliche Transaktionen** aus allen Konten werden summiert!

**Vorsteuer-Berechnung:**
- Zeigt erwartete Vorsteuer (Rückforderung vom Finanzamt)
- Berechnet aus allen geschäftlichen Ausgaben mit Vorsteuer
- Hilft bei Cashflow-Planung (wann kommt Geld vom FA zurück)

---

### **Datenbank-Erweiterung**

```sql
-- Konten-Definition
CREATE TABLE konten (
    id INTEGER PRIMARY KEY,
    bank TEXT NOT NULL,
    iban TEXT UNIQUE NOT NULL,
    kontotyp TEXT NOT NULL,  -- 'geschaeftlich', 'mischkonto', 'privat'
    name TEXT,  -- z.B. "Hauptgeschäftskonto", "PayPal Business"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bank-Transaktionen (erweitert)
CREATE TABLE bank_transaktionen (
    id INTEGER PRIMARY KEY,
    konto_id INTEGER NOT NULL,  -- Verknüpfung zu Konto
    import_id INTEGER,
    datum DATE NOT NULL,
    betrag DECIMAL NOT NULL,
    partner TEXT,
    verwendungszweck TEXT,

    -- NEU: Geschäftlich-Markierung
    ist_geschaeftlich BOOLEAN DEFAULT 1,  -- 1 = geschäftlich, 0 = privat
    ist_privatentnahme BOOLEAN DEFAULT 0,
    ist_einlage BOOLEAN DEFAULT 0,

    -- Auto-Filter
    auto_vorschlag TEXT,  -- 'geschaeftlich', 'privat', 'privatentnahme'
    user_ueberschrieben BOOLEAN DEFAULT 0,  -- User hat Vorschlag geändert

    kategorie_id INTEGER,
    rechnung_id INTEGER,

    FOREIGN KEY (konto_id) REFERENCES konten(id),
    FOREIGN KEY (import_id) REFERENCES bank_imports(id)
);

-- Auto-Filter-Regeln (User-spezifisch)
CREATE TABLE auto_filter_regeln (
    id INTEGER PRIMARY KEY,
    partner_pattern TEXT,  -- z.B. "%GmbH%", "Amazon"
    verwendungszweck_pattern TEXT,
    vorschlag TEXT,  -- 'geschaeftlich', 'privat', 'privatentnahme'
    prioritaet INTEGER DEFAULT 0,
    aktiv BOOLEAN DEFAULT 1
);

-- Kategorien (für Vorsteuer-Berechnung erweitert)
CREATE TABLE kategorien (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,  -- z.B. "Büromaterial"
    konto_skr03 TEXT,    -- "4910"
    konto_skr04 TEXT,    -- "6815"
    vorsteuer_abzugsfaehig BOOLEAN DEFAULT 1,  -- ← NEU: Für Vorsteuer-Berechnung
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rechnungen (Eingangs- und Ausgangsrechnungen)
CREATE TABLE rechnungen (
    id INTEGER PRIMARY KEY,
    typ TEXT NOT NULL,  -- 'eingangsrechnung', 'ausgangsrechnung'
    rechnungsnummer TEXT,
    datum DATE NOT NULL,
    partner TEXT,

    netto_betrag DECIMAL,
    umsatzsteuer_satz DECIMAL,       -- z.B. 19.00, 7.00, 0.00
    umsatzsteuer_betrag DECIMAL,     -- ← Wichtig für Vorsteuer!
    brutto_betrag DECIMAL,

    kategorie_id INTEGER,
    bezahlt BOOLEAN DEFAULT 0,

    FOREIGN KEY (kategorie_id) REFERENCES kategorien(id)
);
```

---

### **Import-Logik (Pseudocode)**

```python
def import_bank_csv(csv_file, konto_id):
    konto = get_konto(konto_id)
    template = detect_template(csv_file)
    df = parse_csv(csv_file, template)

    # Schritt 1: Auto-Vorschläge generieren
    for row in df:
        row['auto_vorschlag'] = suggest_transaction_type(
            partner=row['partner'],
            verwendungszweck=row['verwendungszweck'],
            konto_typ=konto.kontotyp
        )

    # Schritt 2: Bei Mischkonto → User-Review
    if konto.kontotyp == 'mischkonto':
        df = user_review_transactions(df)  # UI-Dialog

    # Schritt 3: Nur geschäftliche Transaktionen importieren
    df_business = df[
        (df['ist_geschaeftlich'] == True) |
        (df['ist_privatentnahme'] == True) |
        (df['ist_einlage'] == True)
    ]

    # Schritt 4: Import
    for row in df_business:
        save_transaction(row)

    # Schritt 5: Regeln aktualisieren (Lernen)
    update_auto_filter_rules(df)

def suggest_transaction_type(partner, verwendungszweck, konto_typ):
    # Geschäftskonto: Alles ist geschäftlich (default)
    if konto_typ == 'geschaeftlich':
        return 'geschaeftlich'

    # Mischkonto: Intelligente Vorschläge
    if konto_typ == 'mischkonto':
        # 1. Explizite Keywords
        if 'privatentnahme' in verwendungszweck.lower():
            return 'privatentnahme'
        if 'einlage' in verwendungszweck.lower():
            return 'einlage'

        # 2. User-Regeln prüfen
        for regel in get_auto_filter_regeln():
            if matches_pattern(partner, regel.partner_pattern):
                return regel.vorschlag

        # 3. Historische Entscheidungen
        history = get_partner_history(partner)
        if history.count('geschaeftlich') > 5:
            return 'geschaeftlich'
        if history.count('privat') > 5:
            return 'privat'

        # 4. Heuristiken
        if 'GmbH' in partner or 'AG' in partner:
            return 'geschaeftlich'
        if partner in ['Vermieter', 'Edeka', 'Rewe']:
            return 'privat'

    # Default: Unsicher → User muss entscheiden
    return None
```

---

### **Cashflow-Berechnung**

```python
def calculate_business_cashflow():
    """
    Summiert alle geschäftlichen Salden über alle Konten
    """
    cashflow = 0

    for konto in get_all_konten():
        if konto.kontotyp == 'privat':
            continue  # Privatkonten ignorieren

        # Letzte Transaktion mit Saldo holen
        last_tx = get_last_transaction(konto.id)

        if konto.kontotyp == 'geschaeftlich':
            # Geschäftskonto: Gesamtsaldo
            cashflow += last_tx.saldo

        elif konto.kontotyp == 'mischkonto':
            # Mischkonto: Nur geschäftliche Transaktionen summieren
            business_txs = get_transactions(
                konto_id=konto.id,
                ist_geschaeftlich=True
            )
            cashflow += sum(tx.betrag for tx in business_txs)

    return cashflow
```

**Vorsteuer-Berechnung:**

```python
def calculate_vorsteuer(zeitraum='monat', quartal=None):
    """
    Berechnet die erwartete Vorsteuer aus geschäftlichen Ausgaben.

    Vorsteuer = Eingangsumsatzsteuer (gezahlte MwSt bei Einkäufen)
    → Kann vom Finanzamt zurückgefordert werden
    """
    from datetime import datetime

    # Zeitraum bestimmen
    if zeitraum == 'monat':
        start_date = datetime.now().replace(day=1)
    elif zeitraum == 'quartal':
        start_date = get_quarter_start(quartal)

    # Alle geschäftlichen Ausgaben mit Vorsteuer holen
    ausgaben = get_transactions(
        datum_von=start_date,
        ist_geschaeftlich=True,
        betrag_lt=0  # Nur Ausgaben (negativ)
    )

    vorsteuer_gesamt = 0

    for tx in ausgaben:
        # Vorsteuer nur aus zugeordneten Eingangsrechnungen
        if tx.rechnung_id:
            rechnung = get_rechnung(tx.rechnung_id)

            # Rechnung muss Vorsteuer enthalten
            if rechnung.umsatzsteuer_betrag and rechnung.umsatzsteuer_betrag > 0:
                vorsteuer_gesamt += rechnung.umsatzsteuer_betrag

        # Alternative: Aus Transaktions-Kategorie schätzen (falls keine Rechnung)
        elif tx.kategorie_id:
            kategorie = get_kategorie(tx.kategorie_id)

            # Nur wenn Kategorie "vorsteuerabzugsberechtigt" ist
            if kategorie.vorsteuer_abzugsfaehig:
                # Standard-Steuersatz 19% rückrechnen
                brutto = abs(tx.betrag)
                netto = brutto / 1.19
                vorsteuer_gesamt += (brutto - netto)

    return vorsteuer_gesamt


def get_vorsteuer_overview():
    """
    Dashboard-Daten für Vorsteuer-Übersicht
    """
    aktueller_monat = calculate_vorsteuer(zeitraum='monat')
    aktuelles_quartal = calculate_vorsteuer(
        zeitraum='quartal',
        quartal=get_current_quarter()
    )
    naechste_ustva = get_next_ustva_deadline()

    return {
        'monat': aktueller_monat,
        'quartal': aktuelles_quartal,
        'deadline': naechste_ustva,
        'status': 'ausstehend' if naechste_ustva else 'eingereicht'
    }
```

**Hinweise zur Vorsteuer-Berechnung:**

1. **Nur bei Eingangsrechnungen:** Vorsteuer kann nur von Rechnungen mit ausgewiesener MwSt abgezogen werden
2. **Kleinunternehmer:** Bei Kleinunternehmerregelung (§19 UStG) → keine Vorsteuer
3. **Reverse-Charge:** Bei innergemeinschaftlichem Erwerb → separate Behandlung
4. **Nicht abzugsfähig:**
   - Private Ausgaben (bereits gefiltert durch ist_geschaeftlich=True)
   - Kleinbetragsrechnungen ohne MwSt-Ausweis
   - Ausländische Rechnungen ohne deutsche MwSt

**Integration im Dashboard:**
```python
def get_cashflow_dashboard():
    cashflow = calculate_business_cashflow()
    vorsteuer = get_vorsteuer_overview()

    return {
        'konten': get_konten_uebersicht(),
        'cashflow': cashflow,
        'forderungen': get_offene_forderungen(),
        'verbindlichkeiten': get_offene_verbindlichkeiten(),
        'vorsteuer': vorsteuer  # ← NEU
    }
```

---

### **GoBD-Konformität**

**Wichtig:** Private Transaktionen dürfen **nicht** in Export-Dateien auftauchen!

**DATEV-Export:**
```python
def export_datev(zeitraum):
    # Nur geschäftliche Transaktionen exportieren
    transaktionen = get_transactions(
        zeitraum=zeitraum,
        ist_geschaeftlich=True  # ← Kritisch!
    )
    # Privatentnahmen/Einlagen WERDEN exportiert (Konto 1800)
    return generate_datev_csv(transaktionen)
```

**EÜR-Export:**
```python
def export_euer(jahr):
    einnahmen = sum(
        betrag for tx in get_transactions(jahr)
        if tx.ist_geschaeftlich and tx.betrag > 0
    )
    ausgaben = sum(
        betrag for tx in get_transactions(jahr)
        if tx.ist_geschaeftlich and tx.betrag < 0
    )
    privatentnahmen = sum(
        betrag for tx in get_transactions(jahr)
        if tx.ist_privatentnahme
    )
    # Private Transaktionen werden NICHT berücksichtigt
    return einnahmen - ausgaben - privatentnahmen
```

---

**Status:** ✅ Private/Geschäftliche Trennung definiert - Kontotypen, Import-Filter, Auto-Vorschläge, Cashflow, Vorsteuer-Übersicht, GoBD-Konformität.

---

## **5.4 Technische Umsetzung**

### **Datenbank-Schema**

```sql
-- Bank-Templates
CREATE TABLE bank_templates (
    id TEXT PRIMARY KEY,  -- z.B. "sparkasse-lzo-mt940"
    name TEXT NOT NULL,
    bank TEXT NOT NULL,
    format TEXT,
    version TEXT,
    author TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_system_template BOOLEAN DEFAULT 0,  -- 0 = User, 1 = System
    config_json TEXT NOT NULL  -- Vollständige Template-Config als JSON
);

-- Importierte Transaktionen
CREATE TABLE bank_transaktionen (
    id INTEGER PRIMARY KEY,
    import_id INTEGER,  -- Verknüpfung zu Import-Batch
    datum DATE NOT NULL,
    valuta DATE,
    buchungstext TEXT,
    verwendungszweck TEXT,
    partner TEXT,
    betrag DECIMAL NOT NULL,
    waehrung TEXT DEFAULT 'EUR',
    iban TEXT,
    bic TEXT,
    saldo DECIMAL,
    info TEXT,
    kategorie_id INTEGER,  -- Automatische Kategorisierung
    rechnung_id INTEGER,  -- Automatischer Zahlungsabgleich
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (import_id) REFERENCES bank_imports(id),
    FOREIGN KEY (kategorie_id) REFERENCES kategorien(id),
    FOREIGN KEY (rechnung_id) REFERENCES rechnungen(id)
);

-- Import-Batches (Tracking)
CREATE TABLE bank_imports (
    id INTEGER PRIMARY KEY,
    template_id TEXT NOT NULL,
    dateiname TEXT,
    anzahl_zeilen INTEGER,
    erfolg INTEGER,
    fehler INTEGER,
    duplikate INTEGER,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (template_id) REFERENCES bank_templates(id)
);
```

---

### **Parser-Architektur**

```python
class BankCSVParser:
    def __init__(self, csv_file, template=None):
        self.csv_file = csv_file
        self.template = template or self.detect_template()

    def detect_template(self):
        """Automatische Format-Erkennung"""
        header = self.read_header()

        for template in load_all_templates():
            if self.match_template(header, template) > 0.8:
                return template

        return None

    def match_template(self, header, template):
        """Berechne Match-Score (0.0 - 1.0)"""
        required_cols = template.validation.required_columns
        found = sum(1 for col in required_cols if col in header)
        return found / len(required_cols)

    def parse(self):
        """Parse CSV mit Template"""
        df = pd.read_csv(
            self.csv_file,
            sep=self.template.delimiter,
            encoding=self.template.encoding,
            decimal=self.template.decimal_separator
        )

        # Column-Mapping anwenden
        df.rename(columns=self.template.column_mapping, inplace=True)

        # Datentypen konvertieren
        df['datum'] = pd.to_datetime(df['datum'], format=self.template.date_format)
        df['betrag'] = df['betrag'].astype(float)

        return df

    def validate(self, df):
        """Validierung nach Import"""
        errors = []

        # Duplikate erkennen
        duplicates = self.find_duplicates(df)
        if duplicates:
            errors.append(f"{len(duplicates)} Duplikate gefunden")

        # Fehlende Pflichtfelder
        for required in ['datum', 'betrag']:
            if df[required].isna().any():
                errors.append(f"Pflichtfeld '{required}' hat leere Werte")

        return errors
```

---

## **5.5 MVP-Umfang**

**Für Version 1.0:**

✅ **System-Templates:**
- Sparkasse/LZO (MT940, CAMT V2, CAMT V8)
- PayPal
- Volksbank
- DKB
- ING
- N26

✅ **Features:**
- Automatische Format-Erkennung
- Template-Editor für Power-User
- CSV-Vorschau vor Import
- Duplikat-Erkennung
- Automatischer Zahlungsabgleich (mit Rechnungen)

⏳ **Post-MVP:**
- Template-Sharing via GitHub
- Automatische Kategorisierung (ML)
- Multi-File-Import (mehrere CSVs auf einmal)
- Bank-API-Integration (Live-Anbindung)

---

**Status:** ✅ Vollständig geklärt - Template-System, Automatische Erkennung, User-Workflows, Technische Umsetzung definiert.

---

