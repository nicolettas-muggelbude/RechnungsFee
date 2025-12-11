## **Kategorie 11: Steuersätze & Buchungslogik**

### **📊 Unterstützte Steuersätze**

RechnungsFee unterstützt alle gängigen deutschen Umsatzsteuersätze:

#### **1. Regelsteuersatz: 19%**
- Standard für die meisten Waren und Dienstleistungen
- Gilt seit 01.01.2007

#### **2. Ermäßigter Steuersatz: 7%**
**Anwendungsfälle:**
- Lebensmittel (außer Getränke, Restaurant)
- Bücher, Zeitungen, Zeitschriften
- Personennahverkehr
- Kulturveranstaltungen (Theater, Konzerte, Museen)
- Beherbergung (nur Übernachtung, nicht Frühstück)
- Pflanzen, Schnittblumen
- Künstlerische/schriftstellerische Leistungen (§12 Abs. 2 Nr. 7 UStG)

#### **3. Steuerfrei: 0%**
**Verschiedene Kategorien:**

**a) Kleinunternehmer (§19 UStG):**
- Jahresumsatz < 22.000 € (Vorjahr) und < 50.000 € (laufendes Jahr)
- Keine Umsatzsteuer ausweisen
- Kein Vorsteuerabzug
- Pflichtangabe auf Rechnung: *"Gemäß §19 UStG wird keine Umsatzsteuer berechnet"*

**b) Reverse-Charge (§13b UStG):**
- Bauleistungen
- Gebäudereinigung
- Altmetall, Schrott
- Telekommunikationsdienstleistungen
- Gas, Elektrizität, Wärme, Kälte
- CO2-Zertifikate
- Pflichtangabe: *"Steuerschuldnerschaft des Leistungsempfängers"*

**c) Innergemeinschaftliche Lieferung (§4 Nr. 1b UStG):**
- Warenlieferung in EU-Land
- Mit gültiger USt-IdNr. des Empfängers
- Gelangensbestätigung erforderlich
- Pflichtangabe: *"Steuerfreie innergemeinschaftliche Lieferung"*

**d) Ausfuhrlieferung/Export (§4 Nr. 1a UStG):**
- Lieferung in Drittland (außerhalb EU)
- Ausfuhrnachweis erforderlich (Zollpapiere)
- Pflichtangabe: *"Steuerfreie Ausfuhrlieferung"*

**e) Sonstige steuerfreie Umsätze:**
- Vermietung/Verpachtung (§4 Nr. 12 UStG)
- Versicherungsumsätze
- Bildungsleistungen
- Gesundheitsleistungen (Ärzte, Krankenhäuser)

#### **4. Historische Steuersätze**
**Corona-Sonderregelung (01.07.2020 - 31.12.2020):**
- Regelsteuersatz: 16% (statt 19%)
- Ermäßigter Steuersatz: 5% (statt 7%)

**Wichtig für:**
- Import alter Rechnungen aus dieser Zeit
- Historische Auswertungen
- Steuerprüfungen vergangener Jahre

**RechnungsFee-Verhalten:**
- Historische Sätze werden im System hinterlegt
- Bei Rechnungsdatum 01.07. - 31.12.2020 → Automatische Erkennung
- Manuelle Überschreibung möglich

#### **5. Sondersätze**
**Land- und Forstwirtschaft (§24 UStG):**
- Durchschnittssätze: 10,7% bzw. 5,5%
- Pauschalierung statt Regelbesteuerung
- ⏸️ **Nicht in v1.0** - Spezialfälle für v2.0

---

### **💶 Buchungslogik: Brutto vs. Netto**

#### **Grundprinzip: B2C brutto, B2B netto**

**Einstellung pro Erfassungs-Kontext:**

```
┌─────────────────────────────────────────┐
│ ⚙️ Einstellungen → Buchungslogik        │
├─────────────────────────────────────────┤
│ Standard-Eingabemodus:                  │
│                                         │
│ ● Brutto (für B2C-Geschäft)            │
│   Empfohlen für: Endkundenge schäft    │
│   Beispiel: Einzelhandel, Friseur      │
│                                         │
│ ○ Netto (für B2B-Geschäft)             │
│   Empfohlen für: Geschäftskunden       │
│   Beispiel: Beratung, Großhandel       │
│                                         │
│ ☑ In jeder Maske umschaltbar           │
│   (ermöglicht flexibles Arbeiten)      │
│                                         │
│ ☑ Automatische USt-Berechnung          │
│   (berechnet fehlenden Wert)           │
│                                         │
│ [Speichern]                             │
└─────────────────────────────────────────┘
```

#### **Erfassungsmaske mit Umschaltung**

**Beispiel: Eingangsrechnung erfassen**

```
┌─────────────────────────────────────────┐
│ 📄 Eingangsrechnung erfassen            │
├─────────────────────────────────────────┤
│ Lieferant: Bürobedarf Schmidt GmbH     │
│ Rechnungsnr.: RE-2025-001               │
│ Datum: 09.12.2025                       │
│                                         │
│ ─────────────────────────────────────── │
│ BETRÄGE                                 │
│                                         │
│ Eingabemodus: ● Brutto  ○ Netto        │ ← Umschaltbar!
│                                         │
│ Brutto-Betrag:  [119,00] €             │ ← Eingabe
│ USt-Satz:       [19% ▼]                 │ ← Auswahl
│                                         │
│ ─── Automatisch berechnet: ────         │
│ Netto-Betrag:    100,00 €               │
│ USt-Betrag:       19,00 €               │
│ ─────────────────────────────────────── │
│                                         │
│ ☑ Vorsteuerabzug (abzugsfähig)         │
│                                         │
│ [Abbrechen]              [Speichern]    │
└─────────────────────────────────────────┘
```

**Bei Netto-Eingabe:**
```
│ Eingabemodus: ○ Brutto  ● Netto        │
│                                         │
│ Netto-Betrag:   [100,00] €             │ ← Eingabe
│ USt-Satz:       [19% ▼]                 │
│                                         │
│ ─── Automatisch berechnet: ────         │
│ USt-Betrag:       19,00 €               │
│ Brutto-Betrag:   119,00 €               │
│ ─────────────────────────────────────── │
```

#### **Automatische USt-Berechnung**

**Formeln:**

```python
# Brutto → Netto
def brutto_zu_netto(brutto: Decimal, ust_satz: Decimal) -> dict:
    """
    Berechnet Netto und USt aus Brutto-Betrag.
    """
    divisor = 1 + (ust_satz / 100)
    netto = brutto / divisor
    ust = brutto - netto

    return {
        'brutto': brutto,
        'netto': netto.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        'ust': ust.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        'ust_satz': ust_satz
    }

# Netto → Brutto
def netto_zu_brutto(netto: Decimal, ust_satz: Decimal) -> dict:
    """
    Berechnet USt und Brutto aus Netto-Betrag.
    """
    ust = netto * (ust_satz / 100)
    brutto = netto + ust

    return {
        'brutto': brutto.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        'netto': netto,
        'ust': ust.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        'ust_satz': ust_satz
    }

# Beispiel
>>> brutto_zu_netto(Decimal('119.00'), Decimal('19'))
{
    'brutto': Decimal('119.00'),
    'netto': Decimal('100.00'),
    'ust': Decimal('19.00'),
    'ust_satz': Decimal('19')
}
```

---

### **🧾 Mischrechnung (mehrere Steuersätze)**

**Unterstützung für verschiedene Steuersätze pro Position:**

```
┌─────────────────────────────────────────────────────────┐
│ 📄 Eingangsrechnung: Buchladen Müller                  │
├─────────────────────────────────────────────────────────┤
│ Position 1:                                             │
│ Beschreibung: [Fachbuch "Steuerrecht 2025"]            │
│ Netto: 20,00 €  USt-Satz: [7% ▼]  Brutto: 21,40 €     │
│                                                         │
│ Position 2:                                             │
│ Beschreibung: [Beratungsleistung Steueroptimierung]    │
│ Netto: 100,00 € USt-Satz: [19% ▼] Brutto: 119,00 €    │
│                                                         │
│ [+ Position hinzufügen]                                 │
│                                                         │
│ ─────────────────────────────────────────────────────── │
│ SUMMEN (automatisch):                                   │
│                                                         │
│ Netto 7%:     20,00 €  │  USt 7%:    1,40 €            │
│ Netto 19%:   100,00 €  │  USt 19%:  19,00 €            │
│ ───────────────────────┼─────────────────────           │
│ Gesamt Netto: 120,00 € │  Gesamt USt: 20,40 €          │
│                        │  Gesamt Brutto: 140,40 €       │
│ ─────────────────────────────────────────────────────── │
│                                                         │
│ [Speichern]                                             │
└─────────────────────────────────────────────────────────┘
```

**Database-Schema:**

```sql
-- Rechnungspositionen (mehrere pro Rechnung)
CREATE TABLE rechnungspositionen (
    id INTEGER PRIMARY KEY,
    rechnung_id INTEGER NOT NULL,
    position_nr INTEGER NOT NULL,       -- 1, 2, 3, ...

    beschreibung TEXT NOT NULL,
    menge DECIMAL(10,3) DEFAULT 1,
    einheit TEXT DEFAULT 'Stück',       -- 'Stück', 'Stunden', 'Pauschal'

    -- Beträge
    netto DECIMAL(10,2) NOT NULL,
    ust_satz DECIMAL(5,2) NOT NULL,     -- 19.00, 7.00, 0.00
    ust_betrag DECIMAL(10,2) NOT NULL,
    brutto DECIMAL(10,2) NOT NULL,

    FOREIGN KEY (rechnung_id) REFERENCES rechnungen(id) ON DELETE CASCADE
);

-- Trigger: Automatische Summierung
CREATE TRIGGER rechnung_summen_update
AFTER INSERT OR UPDATE OR DELETE ON rechnungspositionen
BEGIN
    -- Gesamtsummen neu berechnen
    UPDATE rechnungen
    SET
        netto_gesamt = (
            SELECT SUM(netto) FROM rechnungspositionen
            WHERE rechnung_id = NEW.rechnung_id
        ),
        ust_gesamt = (
            SELECT SUM(ust_betrag) FROM rechnungspositionen
            WHERE rechnung_id = NEW.rechnung_id
        ),
        brutto_gesamt = (
            SELECT SUM(brutto) FROM rechnungspositionen
            WHERE rechnung_id = NEW.rechnung_id
        )
    WHERE id = NEW.rechnung_id;
END;

-- View: Summierung nach Steuersatz
CREATE VIEW rechnung_summen_nach_steuersatz AS
SELECT
    rechnung_id,
    ust_satz,
    SUM(netto) AS netto_summe,
    SUM(ust_betrag) AS ust_summe,
    SUM(brutto) AS brutto_summe
FROM rechnungspositionen
GROUP BY rechnung_id, ust_satz;
```

---

### **💸 Vorsteuerabzug**

#### **Automatische Berechnung**

**Bei Eingangsrechnungen:**

```
┌─────────────────────────────────────────┐
│ 📄 Eingangsrechnung                     │
├─────────────────────────────────────────┤
│ Brutto: 119,00 €                        │
│ USt 19%: 19,00 €                        │
│                                         │
│ ☑ Vorsteuerabzug berechtigt            │
│   (100% abzugsfähig)                   │
│                                         │
│ → Vorsteuer: 19,00 € ✅                 │
│                                         │
│ Diese 19,00 € werden in UStVA          │
│ Zeile 66 (Abziehbare Vorsteuer)        │
│ berücksichtigt.                         │
└─────────────────────────────────────────┘
```

#### **Nicht abzugsfähige / teilweise abzugsfähige Vorsteuer**

**Bewirtungskosten (§4 Abs. 5 Nr. 2 UStG):**
- Nur 70% der Kosten abzugsfähig
- Vorsteuer nur auf abzugsfähigen Teil

```
┌─────────────────────────────────────────┐
│ 📄 Eingangsrechnung: Restaurant         │
├─────────────────────────────────────────┤
│ Kategorie: [Bewirtungskosten ▼]        │
│                                         │
│ Brutto: 119,00 €                        │
│ USt 19%: 19,00 €                        │
│ Netto: 100,00 €                         │
│                                         │
│ ⚠️ Bewirtungskosten-Regelung:           │
│ Nur 70% abzugsfähig (§4 Abs. 5 Nr. 2)  │
│                                         │
│ Abzugsfähig: 70,00 € (70%)              │
│ Nicht abzugsfähig: 30,00 € (30%)        │
│                                         │
│ → Vorsteuer: 13,30 € (70% von 19,00 €) │
│   (automatisch berechnet)               │
└─────────────────────────────────────────┘
```

**PKW-Nutzung (gemischt privat/geschäftlich):**

```
┌─────────────────────────────────────────┐
│ 📄 Eingangsrechnung: KFZ-Werkstatt      │
├─────────────────────────────────────────┤
│ Kategorie: [KFZ-Kosten ▼]              │
│                                         │
│ Brutto: 595,00 €                        │
│ USt 19%: 95,00 €                        │
│ Netto: 500,00 €                         │
│                                         │
│ Geschäftliche Nutzung: [60] %          │ ← Eingabe
│ Private Nutzung: 40%                    │
│                                         │
│ → Vorsteuer: 57,00 € (60% von 95,00 €) │
│   (automatisch berechnet)               │
│                                         │
│ ℹ️ Hinweis: Fahrtenbuch erforderlich!   │
└─────────────────────────────────────────┘
```

**Database-Schema:**

```sql
-- Vorsteuer-Einschränkungen
ALTER TABLE rechnungen ADD COLUMN vorsteuer_prozent DECIMAL(5,2) DEFAULT 100.00;
ALTER TABLE rechnungen ADD COLUMN vorsteuer_abzugsfaehig DECIMAL(10,2);

-- Trigger: Vorsteuer automatisch berechnen
CREATE TRIGGER vorsteuer_berechnen
AFTER INSERT OR UPDATE ON rechnungen
BEGIN
    UPDATE rechnungen
    SET vorsteuer_abzugsfaehig = (ust_gesamt * vorsteuer_prozent / 100)
    WHERE id = NEW.id;
END;

-- Kategorien mit Vorsteuer-Einschränkung
CREATE TABLE kategorie_vorsteuer_regeln (
    kategorie_id INTEGER PRIMARY KEY,
    vorsteuer_prozent DECIMAL(5,2) NOT NULL,  -- 100.00, 70.00, 0.00
    beschreibung TEXT,

    FOREIGN KEY (kategorie_id) REFERENCES kategorien(id)
);

-- Beispiel-Daten
INSERT INTO kategorie_vorsteuer_regeln VALUES
    (1, 100.00, 'Voll abzugsfähig'),
    (2, 70.00, 'Bewirtungskosten (nur 70%)'),
    (3, 0.00, 'Nicht abzugsfähig (Privatnutzung)');
```

---

### **📋 MVP-Umfang für Kategorie 11 (Steuersätze)**

#### **Phase 1 (v1.0):**

**Steuersätze:**
- ✅ 19% (Regelsteuersatz)
- ✅ 7% (ermäßigt)
- ✅ 0% (mit Unterkategorien: §19, §13b, innergemeinschaftlich, Export)
- ✅ Historische Sätze (16%/5% Corona 2020)
- ❌ Sondersätze Land-/Forstwirtschaft → v2.0

**Buchungslogik:**
- ✅ B2C brutto / B2B netto (einstellbar)
- ✅ Umschaltung in jeder Maske
- ✅ Automatische USt-Berechnung
- ✅ Rundung auf 2 Nachkommastellen (kaufmännisch)

**Mischrechnung:**
- ✅ Mehrere Positionen mit verschiedenen Steuersätzen
- ✅ Automatische Summierung nach Steuersatz
- ✅ Gesamtsummen automatisch

**Vorsteuerabzug:**
- ✅ Automatische Berechnung
- ✅ Teilweise abzugsfähig (Bewirtung 70%)
- ✅ Gemischte Nutzung (PKW mit %-Angabe)
- ✅ Kategorie-basierte Regeln

#### **Phase 2 (v1.1):**
- Vorlagen für Standard-Steuersätze nach Branche
- Erweiterte Vorsteuer-Aufteilung (mehrere Nutzungsarten)
- Import historischer Rechnungen mit automatischer Steuersatz-Erkennung

#### **Phase 3 (v2.0):**
- Sondersätze Land-/Forstwirtschaft (§24 UStG)
- Differenzbesteuerung (§25a UStG - Gebrauchtwarenhändler)
- Margenbesteuerung (Reisebüros)

---

### **✅ Status: Kategorie 11 - Steuersätze vollständig geklärt**

**Wichtigste Entscheidungen:**

1. ✅ **Alle Standard-Steuersätze** (19%, 7%, 0% mit Unterkategorien)
2. ✅ **Historische Sätze** (16%/5% Corona 2020)
3. ✅ **B2C brutto / B2B netto** (einstellbar, umschaltbar) ⭐
4. ✅ **Automatische USt-Berechnung** (beide Richtungen)
5. ✅ **Mischrechnung** (mehrere Steuersätze pro Beleg)
6. ✅ **Vorsteuerabzug automatisch** (inkl. Teilabzug)
7. ✅ **Kategorie-basierte Vorsteuer-Regeln**

**B2C/B2B-Logik:**
- Standard-Eingabemodus konfigurierbar
- In jeder Maske umschaltbar (Flexibilität)
- Automatische Berechnung des jeweils anderen Wertes
- Kaufmännische Rundung (2 Dezimalstellen)

**Vorsteuer-Intelligenz:**
- Bewirtungskosten: automatisch 70%
- PKW gemischt: prozentuale Eingabe
- Kategorie-Vorlagen

---

### **Noch zu klären (siehe fragen.md):**

- ✅ ~~Kategorie 6: UStVA~~ - **Geklärt** (Hybrid-Ansatz, MVP nur Zahlen)
- ✅ ~~Kategorie 7: EÜR~~ - **Geklärt** (Hybrid-Ansatz, AfA-Verwaltung, Zufluss-/Abfluss-Prinzip)
- ✅ ~~Kategorie 8: Stammdaten-Erfassung~~ - **Geklärt** (User/Firma, Kategorien, EU-Länder, Bankkonten, Kontenrahmen, Geschäftsjahr, Kundenstamm mit Hybrid-Lösung, Lieferantenstamm, Produktstamm v2.0)
- ✅ ~~Kategorie 9: Import-Schnittstellen~~ - **Geklärt** (Typ 1: Stammdaten editierbar, Typ 2a: Rohdaten unveränderbar, Typ 2b: Geschäftsvorfälle unveränderbar; Fakturama/helloCash in v1.1, AGENDA in v1.1/v2.0)
- ✅ ~~Kategorie 10.1: Backup~~ - **Geklärt** (Lokale Backups: Verzeichnis/USB/NAS, mehrere Ziele parallel, 3-2-1-Regel, Vollbackup/Inkrementell, AES-256-Verschlüsselung, automatischer Zeitplan, **Exit-Backup beim Beenden** ⭐, Change-Tracking, Cloud-Backup v2.0)
- ✅ ~~Kategorie 10.2: Update~~ - **Geklärt** (Auto-Update Standard, Backup vor Update PFLICHT, Code Signing, Stable/Beta/Nightly-Kanäle, Rollback-Funktion, Changelog-Anzeige)
- ✅ ~~Kategorie 11: Steuersätze~~ - **Geklärt** (Alle Standard-Steuersätze 19%/7%/0%, historische Sätze, **B2C brutto / B2B netto** ⭐, automatische USt-Berechnung, Mischrechnung, Vorsteuerabzug mit Teilabzug, Kategorie-basierte Regeln)
- Kategorie 12: Hilfe-System
- Kategorie 13: Scope & Priorisierung

---

