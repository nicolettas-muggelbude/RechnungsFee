## **Kategorie 9: Import-Schnittstellen**

### **⚠️ Fundamentale Unterscheidung: Zwei Arten von Import**

**KRITISCH:** Es gibt zwei **völlig unterschiedliche** Arten von Import mit unterschiedlichen rechtlichen und technischen Anforderungen!

---

### **📝 Typ 1: Import zum Weiterarbeiten (editierbar)**

**Zweck:** Migration/Übernahme von Stammdaten aus anderen Systemen

**Eigenschaften:**
- ✅ Daten können nach Import **bearbeitet** werden
- ✅ Daten können **gelöscht** werden
- ✅ Keine GoBD-Anforderungen (keine Buchführung)
- ✅ Validierung kann nachträglich erfolgen
- ✅ User hat **volle Kontrolle**

**Anwendungsfälle:**
1. **Kundenstamm-Import** aus CSV/Excel
2. **Produktstamm-Import** aus CSV/Excel
3. **Lieferantenstamm-Import** aus CSV
4. **Kategorien-Import** aus anderen Buchhaltungsprogrammen
5. **Kontakte-Import** aus CRM-Systemen
6. **Artikel-Import** aus Shop-Systemen (Stammdaten)

**Workflow:**
```
1. CSV/Excel-Datei hochladen
2. Vorschau anzeigen (erste 10 Zeilen)
3. Spalten-Mapping (automatisch + manuell)
   ├─ "Name" → kunde.name
   ├─ "E-Mail" → kunde.email
   └─ "USt-IdNr" → kunde.ust_idnr
4. Duplikat-Erkennung konfigurieren
   ├─ Nach E-Mail
   ├─ Nach Name + PLZ
   └─ Nach Kundennummer
5. Aktion bei Duplikaten wählen:
   ├─ Überspringen
   ├─ Überschreiben
   └─ Zusammenführen
6. Import durchführen
7. ✅ Erfolg: 245 Kunden importiert, 12 Duplikate übersprungen
8. ✅ User kann Daten in RechnungsFee bearbeiten/löschen
```

**Datenbank:**
```sql
CREATE TABLE import_stammdaten (
    id INTEGER PRIMARY KEY,
    typ TEXT NOT NULL, -- 'kunden', 'produkte', 'lieferanten', 'kategorien'
    dateiname TEXT NOT NULL,
    dateityp TEXT, -- 'csv', 'xlsx', 'json'
    importiert_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    benutzer TEXT,

    anzahl_datensaetze INTEGER,
    anzahl_erfolgreich INTEGER,
    anzahl_fehler INTEGER,
    anzahl_duplikate INTEGER,

    spalten_mapping TEXT, -- JSON mit Mapping
    duplikat_strategie TEXT, -- 'skip', 'overwrite', 'merge'

    status TEXT DEFAULT 'erfolgreich', -- 'erfolgreich', 'mit_warnungen', 'fehler'
    fehlerprotokoll TEXT, -- JSON mit Fehlern

    CHECK (typ IN ('kunden', 'produkte', 'lieferanten', 'kategorien'))
);

CREATE INDEX idx_import_stammdaten_typ ON import_stammdaten(typ);
CREATE INDEX idx_import_stammdaten_datum ON import_stammdaten(importiert_am);
```

**UI-Mockup:**
```
┌─────────────────────────────────────────────────────────┐
│ 📥 Kundenstamm importieren                              │
├─────────────────────────────────────────────────────────┤
│ Schritt 1/4: Datei hochladen                            │
│                                                         │
│ ┌─────────────────────────────────────────────────┐     │
│ │ [Datei auswählen] kunden_alt.csv                │     │
│ │                                                 │     │
│ │ Format erkannt: CSV (Komma-getrennt, UTF-8)    │     │
│ │ 247 Zeilen, 8 Spalten                          │     │
│ └─────────────────────────────────────────────────┘     │
│                                                         │
│ Vorschau (erste 5 Zeilen):                             │
│ ┌─────────────────────────────────────────────────┐     │
│ │ Name         │ E-Mail          │ PLZ   │ Ort    │     │
│ │ Müller GmbH  │ info@mueller.de │ 10115 │ Berlin │     │
│ │ Schmidt AG   │ mail@schmidt.de │ 80331 │ München│     │
│ │ ...                                             │     │
│ └─────────────────────────────────────────────────┘     │
│                                                         │
│ [Abbrechen]                    [Weiter zu Mapping →]    │
└─────────────────────────────────────────────────────────┘
```

---

### **📊 Typ 2: Import als Buchführung (unveränderbar)**

**Zweck:** Übernahme von Buchführungsdaten aus externen Systemen (GoBD-relevant!)

**Eigenschaften:**
- ❌ Daten können **NICHT bearbeitet** werden (Unveränderbarkeit §146 AO)
- ❌ Daten können **NICHT gelöscht** werden (nur storniert)
- ✅ **GoBD-Anforderungen gelten** (Unveränderbarkeit, Vollständigkeit, Nachvollziehbarkeit)
- ✅ Import muss **vor** dem Import validiert sein
- ✅ **Import-Protokoll** erforderlich (wer, wann, was)
- ✅ **Zeitstempel** und Versionierung
- ✅ **Originaldatei archivieren** (Hash für Nachweis)

**⚠️ Wichtige Unterscheidung: Typ 2a vs. Typ 2b**

---

#### **Typ 2a: Import Rohdaten (Transaktionen)**

**Charakteristik:** Einfache Transaktionsdaten ohne vollständige Geschäftsvorfälle

**Anwendungsfälle:**
1. **Bank-CSV-Import** (Transaktionen) ⭐
2. **Zahlungsdienste** (PayPal, Stripe, Klarna, etc.)
3. **Kreditkarten-Abrechnungen**

**Eigenschaften:**
- 📝 **Flache Datenstruktur** (eine Zeile = eine Transaktion)
- ❌ **Keine Kategorisierung** (muss nachträglich erfolgen)
- ❌ **Keine Kundendaten** (nur Name/IBAN)
- ❌ **Keine Artikelpositionen**
- ✅ **Einfaches Parsing** (Standard-CSV)

**Format-Beispiel (Bank-CSV):**
```csv
Buchungstag,Wertstellung,Verwendungszweck,Betrag,Währung
01.01.2025,01.01.2025,Überweisung Müller GmbH,1000.00,EUR
02.01.2025,02.01.2025,REWE Einkauf,-45.67,EUR
```

**Workflow:**
1. CSV hochladen
2. Format-Erkennung via Template
3. Transaktionen importieren
4. **User muss Transaktionen kategorisieren** (SKR03/SKR04)

**Status v1.0:** ✅ **JA** - Bereits vollständig spezifiziert (Kategorie 5)

---

#### **Typ 2b: Import Geschäftsvorfälle (vollständig)**

**Charakteristik:** Vollständige Geschäftsvorfälle mit allen relevanten Daten

**Anwendungsfälle:**
1. **Rechnungsprogramme** (Fakturama, Rechnungs-Assistent, Lexware) ⭐
2. **Kassensysteme** (helloCash, AGENDA, orderbird, etc.) ⭐
3. **E-Commerce-Plattformen** (Shopify, WooCommerce - vollständige Bestellungen)
4. **POS-Systeme** (Einzelhandel, Gastronomie)
5. **Warenwirtschaftssysteme** (Eingangsrechnungen mit Artikeln)

**Eigenschaften:**
- 📊 **Verschachtelte Datenstruktur** (Rechnung → Positionen → Artikel)
- ✅ **Bereits kategorisiert** (oder Mapping erforderlich)
- ✅ **Vollständige Kundendaten** (Name, Adresse, USt-IdNr)
- ✅ **Artikelpositionen** mit Menge, Einzelpreis, Steuersatz
- ⚠️ **Komplexes Parsing** (CSV mit Relationen, JSON, XML)

**Format-Beispiel (Fakturama Export):**

**rechnungen.csv:**
```csv
Rechnungsnummer,Datum,Kunde_ID,Kunde_Name,Kunde_Strasse,Kunde_PLZ,Kunde_Ort,Netto,USt,Brutto,Status,Zahlungsziel
RE-2024-001,01.01.2024,K001,Müller GmbH,Musterstr. 1,10115,Berlin,1000.00,190.00,1190.00,Bezahlt,14 Tage
RE-2024-002,05.01.2024,K002,Schmidt AG,Testweg 2,80331,München,500.00,95.00,595.00,Offen,30 Tage
```

**rechnungs_positionen.csv:**
```csv
Rechnungsnummer,Position,Artikel_ID,Artikel_Name,Menge,Einzelpreis,Gesamt,USt_Satz
RE-2024-001,1,ART001,Beratung Stunde,10,100.00,1000.00,19%
RE-2024-002,1,ART002,Softwarelizenz,1,500.00,500.00,19%
```

**Format-Beispiel (helloCash Tagesabschluss):**
```csv
Datum,Umsatz_Netto_19,USt_19,Umsatz_Netto_7,USt_7,Umsatz_Netto_0,Brutto_Gesamt,Zahlungsart_Bar,Zahlungsart_EC,Zahlungsart_Kreditkarte,Trinkgeld
01.01.2024,1034.45,196.55,200.00,14.00,0.00,1445.00,800.00,645.00,0.00,50.00
02.01.2024,890.76,169.24,150.00,10.50,0.00,1220.50,600.00,620.50,0.00,30.00
```

**Workflow:**
1. Export-Datei(en) hochladen
2. Format-Erkennung (komplexes Template)
3. **Relationen auflösen:**
   - Kunde: In Kundenstamm anlegen (falls nicht vorhanden)
   - Artikel: In Produktstamm anlegen (optional)
   - Positionen: Mit Rechnung verknüpfen
4. **Kategorien mappen:**
   - Fakturama "Honorare" → SKR03 Konto 8400 "Erlöse"
   - helloCash "Speisen" → SKR03 Konto 8300 "Umsatzerlöse"
5. Import durchführen (atomare Transaktion)
6. Import-Protokoll + Archivierung

**Technische Herausforderungen:**

**1. Verschachtelte Datenstrukturen:**
```python
# Beispiel: Fakturama-Import
def import_fakturama_rechnungen(rechnungen_csv: Path, positionen_csv: Path):
    # 1. Rechnungen einlesen
    rechnungen = pd.read_csv(rechnungen_csv, delimiter=';', encoding='ISO-8859-1')

    # 2. Positionen einlesen
    positionen = pd.read_csv(positionen_csv, delimiter=';', encoding='ISO-8859-1')

    # 3. Für jede Rechnung:
    for _, rechnung in rechnungen.iterrows():
        # 3a. Kunde anlegen/finden
        kunde = find_or_create_kunde(
            name=rechnung['Kunde_Name'],
            strasse=rechnung['Kunde_Strasse'],
            plz=rechnung['Kunde_PLZ'],
            ort=rechnung['Kunde_Ort']
        )

        # 3b. Rechnung anlegen
        rechnung_id = create_rechnung(
            rechnungsnummer=rechnung['Rechnungsnummer'],
            datum=rechnung['Datum'],
            kunde_id=kunde.id,
            betrag_netto=rechnung['Netto'],
            betrag_brutto=rechnung['Brutto'],
            status=rechnung['Status']
        )

        # 3c. Positionen anlegen
        rechnungs_positionen = positionen[positionen['Rechnungsnummer'] == rechnung['Rechnungsnummer']]
        for _, position in rechnungs_positionen.iterrows():
            create_rechnungsposition(
                rechnung_id=rechnung_id,
                position=position['Position'],
                artikel_name=position['Artikel_Name'],
                menge=position['Menge'],
                einzelpreis=position['Einzelpreis'],
                gesamt=position['Gesamt'],
                ust_satz=parse_ust_satz(position['USt_Satz'])
            )
```

**2. Kundenstamm-Mapping:**

**Problem:** Kunde aus Rechnung evtl. schon im Kundenstamm vorhanden?

**Lösung: Duplikat-Erkennung mit Fuzzy-Matching:**
```python
def find_or_create_kunde(name: str, strasse: str, plz: str, ort: str) -> Kunde:
    # 1. Exakter Match (Name + PLZ)
    kunde = db.query(Kunde).filter(
        Kunde.name == name,
        Kunde.plz == plz
    ).first()

    if kunde:
        return kunde  # Existierender Kunde gefunden

    # 2. Fuzzy-Match (ähnlicher Name + gleiche PLZ)
    aehnliche_kunden = db.query(Kunde).filter(Kunde.plz == plz).all()
    for k in aehnliche_kunden:
        similarity = fuzz.ratio(k.name.lower(), name.lower())
        if similarity > 85:  # 85% Ähnlichkeit
            # User fragen: "Ist 'Müller GmbH' identisch mit 'Mueller GmbH'?"
            if user_confirms_duplicate(k, name):
                return k

    # 3. Neuen Kunden anlegen
    return db.create(Kunde(
        name=name, strasse=strasse, plz=plz, ort=ort,
        quelle='Import Fakturama'
    ))
```

**3. Kategorien-Mapping:**

**Problem:** Fakturama kennt keine SKR03-Kategorien!

**Lösung: Mapping-Tabelle:**
```sql
CREATE TABLE import_kategorie_mapping (
    id INTEGER PRIMARY KEY,
    quelle TEXT NOT NULL, -- 'fakturama', 'hellocash', 'agenda'
    quelle_kategorie TEXT NOT NULL, -- 'Honorare', 'Speisen', etc.
    ziel_kategorie_id INTEGER NOT NULL, -- Kategorie in RechnungsFee
    ziel_konto_skr03 TEXT, -- '8400'
    ziel_konto_skr04 TEXT, -- '4400'

    FOREIGN KEY (ziel_kategorie_id) REFERENCES kategorien(id)
);

-- Beispiel-Daten:
INSERT INTO import_kategorie_mapping VALUES
(1, 'fakturama', 'Honorare', 1, '8400', '4400'),
(2, 'fakturama', 'Warenverkauf', 2, '8300', '4300'),
(3, 'hellocash', 'Speisen', 2, '8300', '4300'),
(4, 'hellocash', 'Getränke', 2, '8300', '4300'),
(5, 'agenda', 'Umsatz 19%', 2, '8300', '4300'),
(6, 'agenda', 'Umsatz 7%', 2, '8300', '4300');
```

**UI für Mapping-Konfiguration:**
```
┌─────────────────────────────────────────────────────────┐
│ 📥 Fakturama-Import: Kategorien zuordnen                │
├─────────────────────────────────────────────────────────┤
│ Bitte ordne die Fakturama-Kategorien den                │
│ RechnungsFee-Kategorien zu:                           │
│                                                         │
│ Fakturama-Kategorie          RechnungsFee-Kategorie  │
│ ┌──────────────────────┐     ┌────────────────────┐    │
│ │ Honorare             │ →   │ Erlöse (8400) ▼    │    │
│ │ Warenverkauf         │ →   │ Umsatzerlöse (8300)│    │
│ │ Dienstleistungen     │ →   │ Erlöse (8400) ▼    │    │
│ │ Material             │ →   │ Betriebsausgaben ▼ │    │
│ └──────────────────────┘     └────────────────────┘    │
│                                                         │
│ ✅ Mapping für zukünftige Imports speichern            │
│                                                         │
│ [Abbrechen]                    [Import durchführen →]   │
└─────────────────────────────────────────────────────────┘
```

**4. Format-Vielfalt:**

**Problem:** Jedes Programm hat eigenes Export-Format

**Lösung: Template-System (wie bei Bank-CSV):**

```json
{
  "name": "Fakturama Standard Export",
  "version": "1.0",
  "typ": "rechnungsprogramm",
  "quelle": "fakturama",

  "dateien": {
    "rechnungen": {
      "dateiname_pattern": "*rechnungen*.csv",
      "delimiter": ";",
      "encoding": "ISO-8859-1",
      "decimal": ",",
      "date_format": "DD.MM.YYYY",

      "columns": {
        "rechnungsnummer": "Rechnungsnummer",
        "datum": "Datum",
        "kunde_id": "Kunde_ID",
        "kunde_name": "Kunde_Name",
        "kunde_strasse": "Kunde_Strasse",
        "kunde_plz": "Kunde_PLZ",
        "kunde_ort": "Kunde_Ort",
        "betrag_netto": "Netto",
        "betrag_brutto": "Brutto",
        "ust_betrag": "USt",
        "status": "Status",
        "zahlungsziel": "Zahlungsziel"
      }
    },

    "positionen": {
      "dateiname_pattern": "*positionen*.csv",
      "delimiter": ";",
      "encoding": "ISO-8859-1",

      "columns": {
        "rechnungsnummer": "Rechnungsnummer",
        "position": "Position",
        "artikel_id": "Artikel_ID",
        "artikel_name": "Artikel_Name",
        "menge": "Menge",
        "einzelpreis": "Einzelpreis",
        "gesamt": "Gesamt",
        "ust_satz": "USt_Satz"
      },

      "relation": {
        "parent": "rechnungen",
        "foreign_key": "rechnungsnummer"
      }
    }
  },

  "kategorie_mapping": [
    {"quelle": "Honorare", "ziel_kategorie": "Erlöse", "konto_skr03": "8400"},
    {"quelle": "Warenverkauf", "ziel_kategorie": "Umsatzerlöse", "konto_skr03": "8300"}
  ]
}
```

**Status v1.0:** ❌ **NEIN** - Zu komplex für MVP

**Status v1.1:** ✅ **JA** - Fakturama + helloCash priorisiert

**Begründung für v1.1:**
1. ⏱️ **Hoher Entwicklungsaufwand** (2-3 Wochen pro Format)
2. 🎯 **Nicht kritisch** (Workarounds verfügbar):
   - Kundenstamm separat importieren (v1.0 ✅)
   - Alte Rechnungen als PDF archivieren
   - Wichtige Altrechnungen manuell eingeben
3. 🔧 **Fokus v1.0:** Kernfunktionalität (Bank-Import, Rechnungsstellung, UStVA)

**Workaround für Migration (v1.0):**
```
Wechsel von Fakturama zu RechnungsFee:

1. Kundenstamm exportieren (CSV)
   → In RechnungsFee importieren ✅ (v1.0)

2. Produktstamm exportieren (CSV)
   → In RechnungsFee importieren ⏸️ (v1.1)

3. Alte Rechnungen (2023, 2024):
   a) Als PDF exportieren und archivieren
   b) Oder: Top 20 wichtigste Rechnungen manuell eingeben

4. Ab 2025: Neue Rechnungen in RechnungsFee erstellen
```

---

**Zusammenfassung Typ 2a vs. 2b:**

| Aspekt | Typ 2a (Rohdaten) | Typ 2b (Geschäftsvorfälle) |
|--------|-------------------|---------------------------|
| **Beispiel** | Bank-CSV, PayPal | Fakturama, helloCash |
| **Struktur** | Flach | Verschachtelt |
| **Kategorisierung** | ❌ Fehlt | ✅ Vorhanden (Mapping) |
| **Kundendaten** | Nur Name | ✅ Vollständig |
| **Artikelpositionen** | ❌ Keine | ✅ Vollständig |
| **Komplexität** | Niedrig | Hoch |
| **v1.0** | ✅ JA | ❌ NEIN |
| **v1.1** | - | ✅ JA (Fakturama, helloCash) |

---

### **Gemeinsame Eigenschaften Typ 2a + 2b:**

**Workflow:**
```
1. CSV/Export-Datei hochladen
2. Format-Erkennung (automatisch + Template-Auswahl)
3. Vorschau anzeigen
4. ⚠️ VALIDIERUNG (KRITISCH!):
   ├─ Pflichtfelder vorhanden?
   ├─ Datumsformat korrekt?
   ├─ Beträge plausibel?
   ├─ Summen-Check (Soll = Haben)
   └─ Duplikate erkennen (Transaktions-ID)
5. Bei Fehler: Import ABBRECHEN (keine teilweisen Imports!)
6. Bei Erfolg: Import durchführen (atomare Transaktion)
7. ✅ Originaldatei archivieren (SHA256-Hash)
8. ✅ Import-Protokoll erstellen (unveränderbar)
9. ✅ Daten sind ab sofort UNVERÄNDERBAR
10. ✅ Nachträgliche Korrekturen nur via Stornobuchung
```

**Datenbank:**
```sql
CREATE TABLE import_buchfuehrung (
    id INTEGER PRIMARY KEY,
    typ TEXT NOT NULL, -- 'bank', 'kasse', 'paypal', 'agenda', 'pos', 'shop'
    quelle TEXT NOT NULL, -- 'Sparkasse', 'PayPal', 'AGENDA Kassensystem', etc.
    dateiname TEXT NOT NULL,
    dateityp TEXT, -- 'csv', 'json', 'xml'

    importiert_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    benutzer TEXT NOT NULL,

    -- Originaldatei-Archivierung (GoBD!)
    originaldatei_hash TEXT NOT NULL, -- SHA256 der Originaldatei
    originaldatei_groesse INTEGER, -- Bytes
    originaldatei_pfad TEXT, -- Pfad im Archiv

    -- Import-Statistik
    anzahl_buchungen INTEGER NOT NULL,
    betrag_summe_soll DECIMAL(12,2),
    betrag_summe_haben DECIMAL(12,2),
    zeitraum_von DATE,
    zeitraum_bis DATE,

    -- Validierung
    validiert BOOLEAN DEFAULT 1,
    validierungsfehler TEXT, -- JSON mit Fehlern (falls vorhanden)

    -- GoBD: Unveränderbarkeit
    veraenderbar BOOLEAN DEFAULT 0 CHECK (veraenderbar = 0), -- IMMER false!

    -- Import-Protokoll (JSON)
    import_protokoll TEXT NOT NULL, -- Detailliertes Protokoll

    status TEXT DEFAULT 'erfolgreich', -- 'erfolgreich', 'fehler'

    CHECK (typ IN ('bank', 'kasse', 'paypal', 'stripe', 'agenda', 'hellocash', 'orderbird', 'pos', 'shopify', 'woocommerce', 'sonstige'))
);

CREATE INDEX idx_import_buchfuehrung_typ ON import_buchfuehrung(typ);
CREATE INDEX idx_import_buchfuehrung_datum ON import_buchfuehrung(importiert_am);
CREATE INDEX idx_import_buchfuehrung_hash ON import_buchfuehrung(originaldatei_hash);

-- Verknüpfung: Welche Buchungen stammen aus welchem Import?
ALTER TABLE bank_transaktionen ADD COLUMN import_id INTEGER;
ALTER TABLE kassenbuch ADD COLUMN import_id INTEGER;

ALTER TABLE bank_transaktionen ADD FOREIGN KEY (import_id) REFERENCES import_buchfuehrung(id);
ALTER TABLE kassenbuch ADD FOREIGN KEY (import_id) REFERENCES import_buchfuehrung(id);
```

**Import-Protokoll (JSON-Beispiel):**
```json
{
  "import_id": 42,
  "typ": "bank",
  "quelle": "Sparkasse LZO - MT940 Format",
  "dateiname": "umsaetze_2025-01.csv",
  "importiert_am": "2025-12-09T14:32:18Z",
  "benutzer": "max.mustermann@example.com",

  "originaldatei": {
    "hash": "a3d5f7b9c2e1d4a6...",
    "groesse": 245678,
    "pfad": "imports/2025/12/09/umsaetze_2025-01_a3d5f7b9.csv"
  },

  "validierung": {
    "erfolgreich": true,
    "pruefungen": [
      {"name": "Pflichtfelder", "status": "OK"},
      {"name": "Datumsformat", "status": "OK"},
      {"name": "Betragsformat", "status": "OK"},
      {"name": "Duplikate", "status": "OK", "gefunden": 0},
      {"name": "Summen-Check", "status": "OK", "soll": 12345.67, "haben": 12345.67}
    ]
  },

  "import": {
    "anzahl_buchungen": 187,
    "betrag_summe_soll": 8234.56,
    "betrag_summe_haben": 4111.11,
    "zeitraum_von": "2025-01-01",
    "zeitraum_bis": "2025-01-31"
  },

  "status": "erfolgreich"
}
```

**UI-Mockup:**
```
┌─────────────────────────────────────────────────────────┐
│ 📥 Bank-CSV importieren                                 │
├─────────────────────────────────────────────────────────┤
│ ⚠️ WICHTIG: Import als Buchführung (unveränderbar!)    │
│                                                         │
│ Schritt 3/4: Validierung                               │
│                                                         │
│ ✅ Format erkannt: Sparkasse MT940                     │
│ ✅ Zeitraum: 01.01.2025 - 31.01.2025                   │
│ ✅ 187 Transaktionen erkannt                           │
│ ✅ Summe Soll:   8.234,56 €                            │
│ ✅ Summe Haben:  4.111,11 €                            │
│ ✅ Saldo:        4.123,45 € ✅                          │
│                                                         │
│ Validierung:                                            │
│ ✅ Pflichtfelder vorhanden                             │
│ ✅ Datumsformat korrekt                                │
│ ✅ Betragsformat korrekt                               │
│ ✅ Keine Duplikate gefunden                            │
│                                                         │
│ ⚠️ Nach Import können die Daten NICHT mehr            │
│    bearbeitet werden (GoBD-konform)!                   │
│                                                         │
│ ✅ Originaldatei wird archiviert (SHA256-Hash)         │
│ ✅ Import-Protokoll wird erstellt                      │
│                                                         │
│ [Abbrechen]                    [Import durchführen →]   │
└─────────────────────────────────────────────────────────┘
```

**Nach erfolgreichem Import:**
```
┌─────────────────────────────────────────────────────────┐
│ ✅ Import erfolgreich abgeschlossen                     │
├─────────────────────────────────────────────────────────┤
│ Import-ID: #42                                          │
│ Datum: 09.12.2025, 14:32:18 Uhr                        │
│                                                         │
│ 📊 Zusammenfassung:                                     │
│ • 187 Transaktionen importiert                         │
│ • Zeitraum: 01.01.2025 - 31.01.2025                    │
│ • Summe Soll:   8.234,56 €                             │
│ • Summe Haben:  4.111,11 €                             │
│ • Saldo:        4.123,45 €                              │
│                                                         │
│ 🔒 Die importierten Daten sind unveränderbar           │
│    (GoBD-konform nach §146 AO).                        │
│                                                         │
│ 📄 Originaldatei archiviert:                            │
│    Hash: a3d5f7b9c2e1d4a6...                            │
│                                                         │
│ [Transaktionen anzeigen]  [Import-Protokoll anzeigen]   │
└─────────────────────────────────────────────────────────┘
```

---

### **🔄 Vergleichstabelle**

| Aspekt | Import Stammdaten (editierbar) | Import Buchführung (unveränderbar) |
|--------|-------------------------------|-----------------------------------|
| **Zweck** | Migration, Übernahme | Buchführungsdaten übernehmen |
| **Editierbar** | ✅ Ja, volle Kontrolle | ❌ Nein, unveränderbar |
| **Löschbar** | ✅ Ja | ❌ Nein (nur Storno) |
| **GoBD-relevant** | ❌ Nein | ✅ Ja, §146 AO |
| **Validierung** | Optional, nachträglich | Pflicht, VOR Import |
| **Import-Protokoll** | Optional | ✅ Pflicht |
| **Originaldatei archivieren** | Optional | ✅ Pflicht (mit Hash) |
| **Duplikat-Erkennung** | Konfigurierbar | Automatisch, Pflicht |
| **Fehlerbehandlung** | Warnung, Import fortsetzbar | Fehler → Import ABBRUCH |
| **Nachträgliche Korrektur** | ✅ Direkt editieren | ❌ Nur via Stornobuchung |
| **Beispiele** | Kunden, Produkte, Lieferanten | Bank-CSV, Kasse, PayPal |

---

### **📋 MVP-Umfang für Kategorie 9**

#### **Phase 1 (v1.0 - MVP):**

**Typ 1: Import Stammdaten (editierbar)**
- ✅ Kundenstamm-Import (CSV) ⭐
  - Spalten-Mapping (automatisch + manuell)
  - Duplikat-Erkennung (konfigurierbar)
  - Vorschau + Fehlerprotokoll
- ⏸️ Produktstamm-Import (CSV) - optional, wenn Zeit
- ⏸️ Lieferantenstamm-Import (CSV) - v1.1

**Typ 2a: Import Buchführung Rohdaten (unveränderbar)**
- ✅ Bank-CSV-Import ⭐ (bereits in Kategorie 5 spezifiziert)
  - Template-System für verschiedene Banken
  - Format-Erkennung via Templates
  - Validierung (Pflichtfelder, Datumsformat, Beträge)
  - Import-Protokoll + Archivierung (SHA256-Hash)
- 🟡 PayPal-Import - optional (Template bereits vorhanden, niedriger Aufwand)

**Typ 2b: Import Buchführung Geschäftsvorfälle (unveränderbar)**
- ❌ **NICHT in v1.0** (zu komplex, siehe Workaround unten)

#### **Phase 2 (v1.1):**

**Typ 1: Stammdaten**
- ✅ Produktstamm-Import (CSV)
- ✅ Lieferantenstamm-Import (CSV)

**Typ 2a: Rohdaten**
- ✅ PayPal-Import (falls nicht in v1.0)
- ✅ Stripe/Klarna (Zahlungsdienstleister)

**Typ 2b: Geschäftsvorfälle** ⭐
- ✅ **Fakturama-Import** (Rechnungsprogramm, Open Source)
  - Verschachtelte Strukturen (Rechnungen + Positionen)
  - Kundenstamm-Mapping mit Fuzzy-Matching
  - Kategorien-Mapping (Fakturama → SKR03)
  - Template-System für Relationen
- ✅ **helloCash-Import** (Kassensystem für Gastronomie)
  - Tagesabschluss-Import
  - USt-Aufschlüsselung (19%, 7%, 0%)
  - Zahlungsarten (Bar, EC, Kreditkarte)
- ⏸️ AGENDA-kompatibel (Kassensystem) - evtl. v1.1, sonst v2.0
- ⏸️ Rechnungs-Assistent - v2.0

#### **Phase 3 (v2.0):**

**Typ 2b: Erweiterte Formate**
- E-Commerce-Plattformen (Shopify, WooCommerce - vollständige Bestellungen)
- POS-Systeme (orderbird, lightspeed, etc.)
- Warenwirtschaftssysteme (Lexware, WISO)
- Excel-Import (komplexe Strukturen)
- JSON/XML-Import (API-Daten)
- Generisches Template-System (User kann eigene Formate definieren)

---

### **🛡️ Sicherheitsmaßnahmen bei Buchführungs-Import**

**1. Unveränderbarkeit erzwingen:**
```sql
-- CHECK Constraint verhindert veraenderbar = true
CREATE TABLE import_buchfuehrung (
    veraenderbar BOOLEAN DEFAULT 0 CHECK (veraenderbar = 0)
);

-- Trigger verhindert UPDATE/DELETE auf importierte Buchungen
CREATE TRIGGER prevent_edit_imported_transactions
BEFORE UPDATE ON bank_transaktionen
FOR EACH ROW
WHEN OLD.import_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'Importierte Buchungen dürfen nicht bearbeitet werden (GoBD)!');
END;

CREATE TRIGGER prevent_delete_imported_transactions
BEFORE DELETE ON bank_transaktionen
FOR EACH ROW
WHEN OLD.import_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'Importierte Buchungen dürfen nicht gelöscht werden (GoBD)!');
END;
```

**2. Originaldatei-Archivierung:**
```python
import hashlib
import shutil
from pathlib import Path

def archiviere_originaldatei(upload_datei: Path) -> dict:
    """
    Archiviert Originaldatei und erstellt Hash für GoBD-Nachweis.
    """
    # SHA256-Hash berechnen
    sha256 = hashlib.sha256()
    with open(upload_datei, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)

    datei_hash = sha256.hexdigest()

    # Archiv-Pfad erstellen (Jahr/Monat/Tag)
    heute = datetime.now()
    archiv_pfad = Path('imports') / str(heute.year) / f'{heute.month:02d}' / f'{heute.day:02d}'
    archiv_pfad.mkdir(parents=True, exist_ok=True)

    # Datei mit Hash-Präfix kopieren
    archiv_datei = archiv_pfad / f'{upload_datei.stem}_{datei_hash[:8]}{upload_datei.suffix}'
    shutil.copy2(upload_datei, archiv_datei)

    return {
        'hash': datei_hash,
        'groesse': upload_datei.stat().st_size,
        'pfad': str(archiv_datei)
    }
```

**3. Atomare Transaktionen:**
```python
def import_bank_csv(datei: Path, template_id: int) -> ImportErgebnis:
    """
    Importiert Bank-CSV als unveränderbare Buchungen.
    ALLES-ODER-NICHTS Prinzip!
    """
    conn = db.get_connection()
    try:
        conn.execute('BEGIN TRANSACTION')

        # 1. Validierung
        fehler = validiere_bank_csv(datei, template_id)
        if fehler:
            raise ValidationError(fehler)

        # 2. Originaldatei archivieren
        archiv = archiviere_originaldatei(datei)

        # 3. Import-Eintrag erstellen
        import_id = conn.execute('''
            INSERT INTO import_buchfuehrung
            (typ, dateiname, originaldatei_hash, anzahl_buchungen, ...)
            VALUES (?, ?, ?, ?, ...)
        ''', ...).lastrowid

        # 4. Transaktionen importieren
        for transaktion in parse_csv(datei):
            conn.execute('''
                INSERT INTO bank_transaktionen
                (import_id, datum, betrag, verwendungszweck, ...)
                VALUES (?, ?, ?, ?, ...)
            ''', import_id, ...)

        # 5. Import-Protokoll erstellen
        protokoll = erstelle_import_protokoll(import_id, archiv, ...)
        conn.execute('UPDATE import_buchfuehrung SET import_protokoll = ? WHERE id = ?',
                     json.dumps(protokoll), import_id)

        conn.execute('COMMIT')
        return ImportErgebnis(erfolg=True, import_id=import_id)

    except Exception as e:
        conn.execute('ROLLBACK')
        return ImportErgebnis(erfolg=False, fehler=str(e))
```

---

### **✅ Status: Kategorie 9 - Vollständig geklärt**

**Wichtigste Erkenntnisse:**

1. ✅ **Drei fundamental unterschiedliche Import-Typen:**
   - **Typ 1: Stammdaten** (editierbar) - Kunden, Produkte, Lieferanten
   - **Typ 2a: Buchführung Rohdaten** (unveränderbar) - Bank-CSV, PayPal
   - **Typ 2b: Buchführung Geschäftsvorfälle** (unveränderbar) - Fakturama, helloCash

2. ✅ **Typ 2a vs. 2b Unterscheidung:**
   - **2a:** Flache Transaktionen, keine Kategorisierung, einfaches Parsing
   - **2b:** Verschachtelte Strukturen (Rechnung→Positionen), bereits kategorisiert, komplexes Parsing

3. ✅ **Buchführungs-Import (kritisch):**
   - Validierung VOR Import (Pflicht!)
   - Originaldatei archivieren (SHA256-Hash)
   - Import-Protokoll erstellen
   - Unveränderbarkeit via DB-Constraints + Trigger
   - Atomare Transaktionen (alles oder nichts)

4. ✅ **MVP-Umfang präzisiert:**
   - **v1.0:** Stammdaten (Kunden) + Typ 2a (Bank-CSV)
   - **v1.1:** Stammdaten (Produkte, Lieferanten) + Typ 2b (Fakturama, helloCash)
   - **v2.0:** Erweiterte Formate (E-Commerce, POS)

5. ✅ **Technische Herausforderungen Typ 2b:**
   - Verschachtelte Datenstrukturen (Rechnung→Positionen)
   - Kundenstamm-Mapping mit Fuzzy-Matching
   - Kategorien-Mapping (Fakturama → SKR03)
   - Template-System für verschiedene Formate

6. ✅ **Workaround für v1.0:**
   - Kundenstamm separat importieren
   - Alte Rechnungen als PDF archivieren
   - Wichtige Altrechnungen manuell eingeben

---

