# RechnungsPilot - Claude Projektdokumentation

**Projekt:** RechnungsPilot
**Typ:** Open-Source Buchhaltungssoftware
**Zielgruppe:** Freiberufler, Selbstständige, Kleinunternehmer
**Lizenz:** AGPL-3.0
**Status:** Konzeptphase
**Letzte Aktualisierung:** 2025-12-04

---

## **Projektvision**

RechnungsPilot ist eine plattformunabhängige, Open-Source-Lösung für:
- Rechnungserfassung (Eingang & Ausgang)
- Kassenbuch-Führung
- Steuerdokumentengenerierung (EAR, EKS, UStVA, EÜR)
- DATEV/AGENDA-Export
- Bank-Integration
- Fokus auf §19 UStG und Regelbesteuerung

**Besonderheit:** Unterstützung für Selbstständige mit Transferleistungen (ALG II/Bürgergeld) durch EKS-Export.

---

## **Kernmerkmale**

### **Zwei Versionen:**
1. **Desktop-App** - Einfach installierbar für Laien (Windows/Mac/Linux)
2. **Docker-Version** - Für Power-User und Server-Betrieb

### **Technologie-Ansatz:**
- **Offline-First** - Volle Funktionalität ohne Internet
- **Plattformunabhängig** - Desktop hat Priorität
- **Mobile PWA** - Für schnelle Erfassung unterwegs
- **Multi-User** - Option für später offen halten

### **Funktionsumfang:**
✅ Eingangsrechnungen verwalten
✅ Ausgangsrechnungen verwalten
✅ Rechnungsschreiben (späteres Modul)
✅ Kassenbuch (EAR-konform, kein POS)
✅ Bank-Integration (CSV-Import, später API)
✅ Automatischer Zahlungsabgleich
✅ Steuerexporte (EAR, EKS, UStVA, EÜR)
✅ DATEV-Schnittstelle
✅ AGENDA-Schnittstelle (CSV)
✅ PDF/ZUGFeRD/XRechnung-Import mit OCR
✅ Kleinunternehmer (§19 UStG) & Regelbesteuerer

---

## **Entscheidungen & Anforderungen**

### **Kassenbuch (Kategorie 1) - ✅ GEKLÄRT**

#### **Erfassung:**
- **Manuelle Eingabe** mit Feldern (siehe `kassenbuchfelder.csv`):
  - **Basis-Daten:**
    - Datum
    - Belegnr. (fortlaufend, eindeutig)
    - Beschreibung
    - Kategorie (z.B. "Bürobedarf", "Warenverkauf")
  - **Zahlungsinformationen:**
    - Zahlungsart (Bar, Karte, Bank, PayPal)
    - Art (Einnahme / Ausgabe)
  - **Beträge (für Vorsteuerabzugsberechtigte):**
    - Netto-Betrag
    - USt-Satz (19%, 7%, 0%)
    - USt-Betrag (automatisch berechnet)
    - Brutto-Betrag
  - **Steuerliche Zuordnung:**
    - Vorsteuerabzug (Ja/Nein - nur bei Ausgaben)
      - "Ja" = Vorsteuer abziehbar (für UStVA)
      - "Nein" = Nicht abziehbar (z.B. Privatnutzung)
  - **Kassenstände:**
    - Tagesendsumme Bar (laufender Kassenstand)

- **Vereinfachung für §19 UStG (Kleinunternehmer):**
  - USt-Satz: Immer 0%
  - USt-Betrag: Immer 0,00 €
  - Vorsteuerabzug: Nicht relevant
  - USt-Felder können in UI ausgeblendet werden
  - Eingabe: Nur Brutto-Beträge

- **Automatische Berechnung:**
  - Bei Eingabe Brutto + USt-Satz → Netto & USt automatisch
  - Bei Eingabe Netto + USt-Satz → USt & Brutto automatisch
  - Umschaltbar: Brutto-/Netto-Eingabemodus

- **Automatisch aus Rechnungsbüchern:**
  - Aus Rechnungseingangsbuch (bei Barzahlung)
  - Aus Rechnungsausgangsbuch (bei Bareinnahme)
  - **Mit manueller Prüfung** (nicht vollautomatisch)

#### **Belege:**
- Belege werden über Rechnungseingangs-/Ausgangsbuch hochgeladen
- Quellen:
  - Scanner
  - Sammelordner (Drag & Drop)
  - Foto (Kamera/Smartphone)

#### **Struktur:**
- **Eine Kasse** (vorerst, kein Multi-Kassen-System)
- **Einmaliger Kassenanfangsbestand** bei Einrichtung
- **Chronologische Liste** aller Bewegungen
- **Unveränderbarkeit (GoBD-Anforderung):**
  - Kassenbucheinträge sind nach Speicherung **unveränderbar**
  - Stornos und Änderungen werden als **neuer Eintrag** angelegt
  - Mit **Begründung protokolliert**
  - Verweis auf ursprünglichen Eintrag (Storno-Kette)

---

#### **Tagesabschluss & Zählprotokoll:**

**GoBD-Anforderung:**
- Nicht verpflichtend bei dieser Art der Kassenführung (kein POS)
- Aber **empfohlen** und wird implementiert
- Täglicher Abschluss mit Soll-Ist-Vergleich dokumentiert Differenzen

**Workflow:**

**1. Tagesabschluss auslösen:**
```
┌─────────────────────────────────────────┐
│ Tagesabschluss für 04.12.2025           │
├─────────────────────────────────────────┤
│ Kassenstand (berechnet):                │
│ • Anfangsbestand:         500,00 €      │
│ • Einnahmen (Bar):      1.450,00 €      │
│ • Ausgaben (Bar):        -320,00 €      │
│ ────────────────────────────────────    │
│ • Soll-Endbestand:      1.630,00 €      │
│                                         │
│ [Abbrechen]  [Zählprotokoll starten]    │
└─────────────────────────────────────────┘
```

**2. Zählprotokoll (Bargeld zählen):**
```
┌─────────────────────────────────────────┐
│ Zählprotokoll - 04.12.2025              │
├─────────────────────────────────────────┤
│ Scheine:                                │
│ • 500 €  [0] Stück    =      0,00 €     │
│ • 200 €  [0] Stück    =      0,00 €     │
│ • 100 €  [5] Stück    =    500,00 €     │
│ • 50 €   [12] Stück   =    600,00 €     │
│ • 20 €   [18] Stück   =    360,00 €     │
│ • 10 €   [8] Stück    =     80,00 €     │
│ • 5 €    [10] Stück   =     50,00 €     │
│                                         │
│ Münzen:                                 │
│ • 2 €    [15] Stück   =     30,00 €     │
│ • 1 €    [8] Stück    =      8,00 €     │
│ • 0,50 € [4] Stück    =      2,00 €     │
│ • 0,20 € [0] Stück    =      0,00 €     │
│ • 0,10 € [0] Stück    =      0,00 €     │
│ • 0,05 € [0] Stück    =      0,00 €     │
│ • 0,02 € [0] Stück    =      0,00 €     │
│ • 0,01 € [0] Stück    =      0,00 €     │
│                                         │
│ ────────────────────────────────────    │
│ Ist-Endbestand:         1.630,00 €      │
│                                         │
│ [Zurück]  [Weiter zum Abgleich]         │
└─────────────────────────────────────────┘
```

**3. Soll-Ist-Vergleich:**
```
┌─────────────────────────────────────────┐
│ Tagesabschluss - Ergebnis               │
├─────────────────────────────────────────┤
│ Soll-Endbestand:        1.630,00 €      │
│ Ist-Endbestand:         1.630,00 €      │
│ ────────────────────────────────────    │
│ Differenz:                  0,00 € ✅    │
│                                         │
│ Status: Kasse stimmt!                   │
│                                         │
│ [Tagesabschluss speichern]              │
└─────────────────────────────────────────┘
```

**4. Bei Differenz - Begründung erfassen:**
```
┌─────────────────────────────────────────┐
│ Tagesabschluss - Differenz erkannt      │
├─────────────────────────────────────────┤
│ Soll-Endbestand:        1.630,00 €      │
│ Ist-Endbestand:         1.625,00 €      │
│ ────────────────────────────────────    │
│ Differenz:                 -5,00 € ⚠️    │
│                                         │
│ ⚠️ Bitte Differenz begründen:           │
│ ┌─────────────────────────────────────┐ │
│ │ Fehlbetrag, vermutlich Wechselgeld  │ │
│ │ falsch herausgegeben                │ │
│ │                                     │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Differenzbuchung:                       │
│ ○ Als Privatentnahme buchen (Manko)     │
│ ○ Als sonstiger Aufwand buchen          │
│ ○ Korrektur ohne Buchung (nur Protokoll)│
│                                         │
│ [Abbrechen]  [Speichern & Abschließen]  │
└─────────────────────────────────────────┘
```

**5. Gespeichertes Zählprotokoll:**

Nach Speicherung wird ein **unveränderliches Zählprotokoll** erstellt:

```json
{
  "datum": "2025-12-04",
  "uhrzeit": "18:30:00",
  "benutzer": "user@example.com",
  "soll_endbestand": 1630.00,
  "ist_endbestand": 1625.00,
  "differenz": -5.00,
  "begründung": "Fehlbetrag, vermutlich Wechselgeld falsch herausgegeben",
  "differenzbuchung": "Privatentnahme",
  "zaehlung": {
    "scheine": {
      "500": 0, "200": 0, "100": 5, "50": 12,
      "20": 18, "10": 8, "5": 10
    },
    "muenzen": {
      "2": 15, "1": 8, "0.5": 4, "0.2": 0,
      "0.1": 0, "0.05": 0, "0.02": 0, "0.01": 0
    }
  },
  "kassenbewegungen_anzahl": 23,
  "einnahmen_bar": 1450.00,
  "ausgaben_bar": 320.00,
  "unveraenderbar": true,
  "signatur": "SHA256:a3f5b8..."
}
```

**Datenbank-Schema:**
```sql
CREATE TABLE tagesabschluesse (
  id INTEGER PRIMARY KEY,
  datum DATE NOT NULL,
  uhrzeit TIME NOT NULL,
  benutzer TEXT,

  -- Soll-Berechnung
  anfangsbestand DECIMAL,
  einnahmen_bar DECIMAL,
  ausgaben_bar DECIMAL,
  soll_endbestand DECIMAL,

  -- Ist-Zählung
  ist_endbestand DECIMAL,
  zaehlung_json TEXT, -- Münzen/Scheine-Details

  -- Differenz
  differenz DECIMAL,
  differenz_begründung TEXT,
  differenz_buchungsart TEXT, -- "Privatentnahme", "Aufwand", "Nur Protokoll"

  -- GoBD
  kassenbewegungen_anzahl INTEGER,
  unveraenderbar BOOLEAN DEFAULT 1,
  signatur TEXT,

  erstellt_am TIMESTAMP,
  UNIQUE(datum) -- Ein Tagesabschluss pro Tag
);
```

**Funktionen:**

**Automatische Erinnerung:**
- Bei Öffnen der Software: "Kein Tagesabschluss für gestern - jetzt durchführen?"
- Optional: Tägliche Push-Benachrichtigung (Mobile PWA)

**PDF-Export des Zählprotokolls:**
- Für Steuerberater/Finanzamt
- Alle Tagesabschlüsse eines Monats/Jahres
- Mit Unterschriftsfeld (optional)

**Statistik:**
- Durchschnittliche Differenzen
- Häufigkeit von Mankos/Überschüssen
- Warnung bei häufigen Differenzen (>5% der Tage)

**GoBD-Konformität:**
- Zählprotokolle sind unveränderbar
- Differenzen müssen begründet werden
- Vollständige Dokumentation aller Kassenabschlüsse
- Export für Betriebsprüfung

#### **Privatentnahmen/-einlagen:**
- Eigene Kategorie für Privatentnahmen und -einlagen
- **Keine Trennung Privat/Gewerbe** bei Freiberuflern/Selbstständigen
  - Einnahmen = Einkommen (für Finanzamt)
  - Zufluss (für Agentur für Arbeit / EKS)
- **Hinweise/Warnungen bei Grenzwertüberschreitung** (z.B. für Transferleistungen)

#### **Verknüpfung Kassenbuch ↔ Rechnungen:**

**Szenario A - Eingangsrechnung bar bezahlt:**
- Automatische Kassenbuchung "Ausgabe" wird vorgeschlagen
- Nutzer muss manuell prüfen und bestätigen
- Verknüpfung zwischen Rechnung und Kassenbuchung sichtbar

**Szenario B - Ausgangsrechnung bar kassiert:**
- Automatische Kassenbuchung "Einnahme" wird vorgeschlagen
- Manuelle Prüfung und Bestätigung
- Verknüpfung sichtbar

**Szenario C - Teilzahlung (bar + Bank):**
- Rechnung 150€, davon 50€ bar, 100€ Überweisung
- Zwei separate Zahlungsbuchungen
- Beide mit Rechnung verknüpft
- Rechnung als "teilweise bezahlt" markiert bis vollständig

---

### **PDF/E-Rechnungs-Import (Kategorie 2) - ✅ GEKLÄRT**

#### **Unterstützte Formate:**
- **ZUGFeRD:** Alle Versionen (1.0, 2.0, 2.1, 2.2)
  - Hybrid-Format: PDF/A-3 + eingebettete XML-Daten
  - Maschinenlesbar + menschenlesbar
  - Meist bereits PDF/A-3 → unveränderbar ✅
- **XRechnung:** Aktuelle Version (3.0.2) + Rückwärtskompatibilität
  - Reine XML-Datei (kein PDF)
  - Rein strukturierte Daten
- **Factur-X:** Ja (französisches ZUGFeRD)
- **PDF/A:** Erkennen und Format beibehalten
  - PDF/A-1, PDF/A-2, PDF/A-3
  - Unveränderbar, GoBD-konform
- **Normales PDF:** Akzeptieren
  - Bei Archivierung → automatisch zu PDF/A-3 konvertieren

#### **Import-Umfang:**
- **Strukturierte Daten** auslesen (XML aus ZUGFeRD/XRechnung)
- **PDF-Rendering** zur Ansicht im Programm (mit pdf.js)
- **Bei Unstimmigkeiten PDF ≠ XML:**
  - **Beide Versionen zum Vergleich anzeigen:**
    - Links: PDF-Darstellung (visuell)
    - Rechts: XML-Daten (strukturiert/tabellarisch)
  - **ZUGFeRD/XRechnung = Primäre Quelle:**
    - In der Regel sind die strukturierten Daten korrekt
    - Diese werden standardmäßig für die Buchhaltung verwendet
  - **Warnung anzeigen:** "Unstimmigkeit zwischen PDF und XML erkannt"
  - **User entscheidet:** Welche Daten übernommen werden (aber Default: XML)

#### **OCR bei normalen PDFs:**

**Standard-Verhalten (Szenario C - Dialog):**
- Bei PDF ohne ZUGFeRD/XRechnung → **Dialog anzeigen:**
  ```
  ┌─────────────────────────────────┐
  │ OCR-Texterkennung starten?      │
  │                                 │
  │ ○ Ja, Daten automatisch         │
  │   ausfüllen (empfohlen)         │
  │                                 │
  │ ○ Nein, manuell eingeben        │
  │                                 │
  │ [☑] Auswahl merken              │
  │                                 │
  │   [Abbrechen]  [Weiter]         │
  └─────────────────────────────────┘
  ```
- User entscheidet pro Rechnung
- Fortschrittsanzeige während OCR-Verarbeitung

**Einstellungen (anpassbar):**
User kann in den Einstellungen das Standard-Verhalten ändern:

1. **"Immer fragen" (Standard)**
   - Dialog wird bei jedem PDF angezeigt
   - Volle Kontrolle

2. **"Immer automatisch OCR starten"**
   - OCR läuft ohne Nachfrage
   - Für User die meist OCR nutzen
   - Schnellerer Workflow

3. **"Nie automatisch OCR"**
   - PDFs werden ohne OCR importiert
   - User kann später manuell OCR starten (Button)
   - Für Power-User die Daten kennen

**Batch-Import (mehrere PDFs):**
- Zusätzliche Option: "Für alle übernehmen"
- User wählt einmal, gilt für alle folgenden PDFs
- Spart Zeit bei vielen Rechnungen

**OCR-Qualität:**
- Preprocessing für bessere Ergebnisse:
  - Kontrast optimieren
  - Deskew (Schräglage korrigieren)
  - Noise Reduction (Rauschen entfernen)
- Tesseract.js + EasyOCR als Fallback

#### **Pflichtfelder für XRechnung und ZUGFeRD:**

**Kritische Pflichtfelder (ohne diese geht nicht):**

| Kategorie | Feld | XRechnung | ZUGFeRD | EN-Code |
|-----------|------|-----------|---------|---------|
| **Rechnungsinfo** | Rechnungsnummer | ✅ Pflicht | ✅ Pflicht | BT-1 |
| | Rechnungsdatum | ✅ Pflicht | ✅ Pflicht | BT-2 |
| | Rechnungstyp (z.B. "380" = Handelsrechnung) | ✅ Pflicht | ✅ Pflicht | BT-3 |
| | Währung (z.B. "EUR") | ✅ Pflicht | ✅ Pflicht | BT-5 |
| **Lieferant** | Name | ✅ Pflicht | ✅ Pflicht | BT-27 |
| | Adresse (Straße, PLZ, Ort, Land) | ✅ Pflicht | ✅ Pflicht | BT-35-38 |
| | Steuernummer ODER USt-ID | ✅ Pflicht (eins) | ✅ Pflicht (eins) | BT-31/32 |
| **Kunde** | Name | ✅ Pflicht | ✅ Pflicht | BT-44 |
| | Adresse (Straße, PLZ, Ort, Land) | ✅ Pflicht | ✅ Pflicht | BT-50-53 |
| | USt-ID | ⚠️ Nur bei ig. Geschäften | ⚠️ Nur bei ig. Geschäften | BT-48 |
| **Leistung** | Beschreibung | ✅ Pflicht | ✅ Pflicht | BT-153 |
| | Menge | ✅ Pflicht | ✅ Pflicht | BT-129 |
| | Einheit (z.B. "C62" = Stück) | ✅ Pflicht | ✅ Pflicht | BT-130 |
| | Einzelpreis (netto) | ✅ Pflicht | ✅ Pflicht | BT-146 |
| | Positionssumme (netto) | ✅ Pflicht | ✅ Pflicht | BT-131 |
| **Steuer** | Steuerkategorie (z.B. "S" = Standard) | ✅ Pflicht | ✅ Pflicht | BT-151 |
| | Steuersatz (z.B. "19") | ✅ Pflicht | ✅ Pflicht | BT-119 |
| **Gesamtbeträge** | Nettosumme | ✅ Pflicht | ✅ Pflicht | BT-106 |
| | Steuerbetrag gesamt | ✅ Pflicht | ✅ Pflicht | BT-110 |
| | Bruttosumme (Zahlbetrag) | ✅ Pflicht | ✅ Pflicht | BT-112 |
| **Zahlung** | IBAN (bei Überweisung) | ✅ Pflicht | ✅ Pflicht | BT-84 |
| | Zahlungsart-Code (z.B. "58" = SEPA) | 🟡 Empfohlen | 🟡 Empfohlen | BT-81 |

**Zusätzliche XRechnung-Pflichtfelder (nur bei öffentlichen Auftraggebern):**

| Feld | Beschreibung | EN-Code |
|------|-------------|---------|
| **Leitweg-ID** | Eindeutige Routing-ID (z.B. "991-12345-67") | BT-13 |
| **Bestellnummer** | Falls vorhanden | BT-13 |

**⚠️ WICHTIG für XRechnung:** Ohne **Leitweg-ID (Buyer Reference)** wird die Rechnung von öffentlichen Verwaltungen abgelehnt!

---

**Optionale, aber empfohlene Felder:**

| Feld | XRechnung | ZUGFeRD | EN-Code |
|------|-----------|---------|---------|
| Fälligkeitsdatum | 🟡 Empfohlen | 🟡 Empfohlen | BT-9 |
| Leistungszeitraum (Von-Bis) | ⚠️ Pflicht wenn ≠ Rechnungsdatum | 🟡 Empfohlen | BT-72/73 |
| Skonto (Betrag, Tage) | 🟡 Empfohlen | 🟡 Empfohlen | BT-92/93 |
| Kontaktdaten (Tel/E-Mail) | 🟡 Empfohlen | 🟡 Empfohlen | BT-41/42 |
| BIC | ❌ Optional (SEPA) | ❌ Optional (SEPA) | BT-86 |
| Kundennummer | 🟡 Empfohlen | 🟡 Empfohlen | - |
| Lieferdatum | 🟡 Empfohlen | 🟡 Empfohlen | BT-72 |

---

**NICHT Pflicht (häufige Irrtümer):**

| Feld | Status |
|------|--------|
| Elektronische Signatur | ❌ NICHT Pflicht |
| Aufbewahrungspflicht-Hinweis | ❌ NICHT Pflicht |
| BIC (seit SEPA) | ❌ NICHT Pflicht (nur IBAN) |
| Fälligkeitsdatum | 🟡 Empfohlen, nicht Pflicht |

---

#### **Validierung:**

**Hybrid-System (Option C):**

**1. Validierung gegen offiziellen Standard:**
- XRechnung: Gegen XRechnung-Schema validieren
- ZUGFeRD: Gegen ZUGFeRD-Spezifikation validieren
- **Pflichtfelder prüfen** (siehe Tabelle oben)
- Zwei Fehler-Kategorien:
  - **Errors (kritisch):** Import blockiert
    - Korrupte XML-Struktur
    - **Pflichtfelder fehlen** (Rechnungsnummer, Betrag, Lieferant, Kunde, etc.)
    - **Leitweg-ID fehlt** (nur bei XRechnung für öffentliche Auftraggeber)
    - Nicht parsebar
    - Ungültige Codes (z.B. falscher Rechnungstyp-Code)
  - **Warnings (unkritisch):** Import möglich mit Hinweis
    - Optionale Felder fehlen
    - Format-Abweichungen (aber lesbar)
    - Veraltete Schema-Version
    - Empfohlene Felder fehlen (z.B. Fälligkeitsdatum)

**Validierungs-Beispiele:**

**❌ Error - Import blockiert:**
```
Fehler (3):
• BT-1: Rechnungsnummer fehlt (Pflichtfeld)
• BT-13: Leitweg-ID fehlt (Pflicht bei XRechnung)
• BT-106: Nettosumme fehlt (Pflichtfeld)
```

**⚠️ Warning - Import möglich:**
```
Warnungen (2):
• BT-9: Fälligkeitsdatum fehlt (empfohlen)
• BT-72: Leistungszeitraum fehlt (empfohlen)
```

---

**2. Bei Validierungsfehlern - Dialog mit Editor-Option:**

```
┌─────────────────────────────────────────────────┐
│ ⚠️ Validierungsfehler erkannt                   │
├─────────────────────────────────────────────────┤
│                                                 │
│ Fehler (2):                                     │
│ • Zeile 47: Pflichtfeld "BuyerReference" fehlt  │
│ • Zeile 89: USt-ID ungültiges Format            │
│                                                 │
│ Warnungen (1):                                  │
│ • Zeile 103: Optionales Feld "Projektnr." fehlt │
│                                                 │
│ ─────────────────────────────────────────────   │
│                                                 │
│ Optionen:                                       │
│                                                 │
│ [📝 In Editor öffnen & korrigieren]             │
│ [📋 Validierungsprotokoll anzeigen]             │
│ [⚠️ Trotzdem importieren] (nur bei Warnings)    │
│ [❌ Abbrechen]                                  │
│                                                 │
└─────────────────────────────────────────────────┘
```

**3. Eingebauter XML-Editor:**

Bei Klick auf "In Editor öffnen":

```
┌─────────────────────────────────────────────────┐
│ XRechnung/ZUGFeRD Editor                        │
├──────────────────────┬──────────────────────────┤
│ XML-Code             │ Fehler & Hilfe           │
├──────────────────────┼──────────────────────────┤
│ 45  <Invoice>        │ ❌ Zeile 47:             │
│ 46    <cbc:ID>       │ Pflichtfeld fehlt        │
│ 47    </cbc:ID>  ⚠️  │                          │
│ 48    <cbc:IssueDate>│ Einfügen:                │
│ ...                  │ <cbc:BuyerReference>     │
│                      │   [Wert]                 │
│                      │ </cbc:BuyerReference>    │
│                      │                          │
│ [Syntax-Check] [💾]  │ [Hilfe-Doku]             │
└──────────────────────┴──────────────────────────┘
     [Abbrechen] [Neu validieren] [Speichern & Importieren]
```

**Features des Editors:**
- **Syntax-Highlighting** für XML
- **Zeilen-Nummern** mit Fehler-Markierungen
- **Auto-Vervollständigung** für XML-Tags
- **Echtzeit-Syntax-Check**
- **Hilfe-Panel** mit Fehlererklärungen
- **Vorschläge** für korrekte Werte

**4. Nach Bearbeitung:**
- **Neu validieren** automatisch
- Bei Erfolg → Importieren
- **Beide Versionen speichern:**
  - Original-XML (unveränderbar, GoBD!)
  - Editierte Version (mit Timestamp + User)
  - Flag: `manually_corrected: true`

**5. GoBD-Konformität:**
- **Original-Datei** bleibt unveränderbar archiviert
- **Editierte Version** wird separat gespeichert
- **Änderungsprotokoll:**
  ```json
  {
    "original_file": "rechnung_original.xml",
    "edited_file": "rechnung_edited.xml",
    "edited_at": "2025-12-03T22:45:00Z",
    "edited_by": "user@example.com",
    "reason": "Validierungsfehler korrigiert",
    "changes": [
      {
        "line": 47,
        "field": "BuyerReference",
        "old_value": null,
        "new_value": "PROJECT-2025-001"
      }
    ]
  }
  ```

**6. Validierungs-Strenge (Einstellungen):**

User kann Standard-Verhalten wählen:

- **Strikt:** Auch Warnungen blockieren Import
- **Standard (empfohlen):** Errors blockieren, Warnings OK
- **Flexibel:** Nur informieren, nie blockieren

**7. Technologie:**
- Validierungs-Engine: Standard-konforme Library (z.B. `validationtool` für XRechnung)
- XML-Editor: Monaco Editor (von VS Code) oder CodeMirror
- Diff-View: Zeigt Original vs. Editiert

**Vorteile dieses Ansatzes:**
- ✅ Sofortige Korrektur ohne Lieferanten
- ✅ Volle Kontrolle für User
- ✅ Transparent (Original + Edit gespeichert)
- ✅ GoBD-konform (Original unveränderbar)
- ✅ Rechtssicher (Änderungen dokumentiert)
- ✅ Professionell (wie ein richtiges Tool)

#### **PDF/A-Konvertierung & Archivierung:**
- **Automatisch zu PDF/A-3 konvertieren** (GoBD-konform)
- **Original UND PDF/A speichern:**
  - Original-Datei: Wie vom User hochgeladen
  - PDF/A-Version: Für rechtssichere Archivierung
- Im UI: PDF/A-Version anzeigen (bessere Langzeitarchivierung)
- Bei ZUGFeRD: Bleibt wie es ist (schon PDF/A-3)

#### **Technologie-Stack (geplant):**
**Python (Backend):**
- `pypdf` - PDF lesen
- `ocrmypdf` - PDF/A erstellen + OCR
- `factur-x` - ZUGFeRD lesen/schreiben
- `lxml` - XRechnung XML parsen
- `reportlab` - PDF generieren

**JavaScript (Frontend):**
- `pdf.js` - PDF anzeigen
- `zugferd.js` - ZUGFeRD parsen

#### **Import-Workflow:**
```
1. Datei hochladen
   ↓
2. Format erkennen:
   - Normales PDF?
   - ZUGFeRD? (prüfe ob XML embedded)
   - XRechnung? (prüfe .xml Extension)
   ↓
3. Daten extrahieren:
   - ZUGFeRD → XML parsen
   - XRechnung → XML parsen
   - Normales PDF → OCR (optional)
   ↓
4. Validieren (bei E-Rechnung)
   - Warnungen anzeigen
   ↓
5. Archivieren:
   - Original speichern
   - Falls kein PDF/A → zu PDF/A-3 konvertieren
   ↓
6. In Datenbank speichern
```

**Status:** Vollständig definiert - Alle Formate, OCR-Optionen, Validierung mit XML-Editor, PDF/A-Archivierung geklärt.

---

### **Anlage EKS - Agentur für Arbeit (Kategorie 3) - ✅ GEKLÄRT**

#### **Was ist die Anlage EKS?**

Die **Anlage EKS (Einkommenserklärung für Selbstständige)** ist ein 9-seitiges Formular der Agentur für Arbeit / Jobcenter für:
- Selbstständige mit **ALG II / Bürgergeld**
- Dokumentation von Einnahmen und Ausgaben während des **Bewilligungszeitraums** (meist 6 Monate)
- Zwei Varianten:
  - **Vorläufige EKS:** Vor Beginn des Bewilligungszeitraums (Prognose)
  - **Abschließende EKS:** Nach Ende des Bewilligungszeitraums (tatsächliche Zahlen)

**Ziel von RechnungsPilot:** Automatische Generierung der EKS aus vorhandenen Buchhaltungsdaten.

---

#### **Struktur der Anlage EKS**

##### **Tabelle A: Betriebseinnahmen (Einnahmen)**

| Feld | Beschreibung | Quelle in RechnungsPilot |
|------|--------------|---------------------------|
| **A1** | Betriebseinnahmen aus selbstständiger Tätigkeit | Ausgangsrechnungen + Kassenbuch (Einnahmen) |
| **A2** | Privatentnahmen | Kassenbuch (Kategorie "Privatentnahme") |
| **A3** | Sonstige Einnahmen (privat & betrieblich) | Manuell erfassen (z.B. Steuererstattung) |
| **A4** | Private Geld- oder Sacheinlagen | Kassenbuch (Kategorie "Privateinlage") |
| **A5** | Umsatzsteuer: | |
| **A5.1** | Umsatzsteuer-Ist-Einnahmen (Kennziffer 81) | Aus UStVA-Berechnung |
| **A5.2** | Umsatzsteuer-Erstattung vom Finanzamt | Manuell erfassen (Bank-Eingang) |
| **A5.3** | Summe Umsatzsteuer | A5.1 + A5.2 (automatisch) |

**Summe A:** Automatisch aus A1-A5.3

---

##### **Tabelle B: Betriebsausgaben (Ausgaben)**

**Teil 1 - Allgemeine Ausgaben:**

| Feld | Beschreibung | Quelle in RechnungsPilot |
|------|--------------|---------------------------|
| **B1** | Wareneinkauf (Materialien, Waren) | Eingangsrechnungen (Kategorie "Wareneinkauf") |
| **B2** | Personalkosten: | |
| **B2.1** | Löhne und Gehälter | Eingangsrechnungen / Kassenbuch (Kategorie "Personal") |
| **B2.2** | Sozialabgaben | Eingangsrechnungen (Kategorie "Sozialabgaben") |
| **B2.3** | Vermögenswirksame Leistungen | Kassenbuch (Kategorie "VL") |
| **B2.4** | Sonstige Personalkosten | Eingangsrechnungen / Kassenbuch |
| **B3** | Raumkosten (Miete, Pacht, Nebenkosten) | Eingangsrechnungen (Kategorie "Raumkosten") |
| **B4** | Versicherungen (Betrieb, Haftpflicht, etc.) | Eingangsrechnungen / Bank (Kategorie "Versicherungen") |
| **B5** | Werbekosten (Anzeigen, Marketing) | Eingangsrechnungen (Kategorie "Werbung") |

**Teil 2 - Fahrzeuge, Reisen, Investitionen:**

| Feld | Beschreibung | Quelle in RechnungsPilot |
|------|--------------|---------------------------|
| **B6** | Fahrzeugkosten: | |
| **B6.1** | Laufende Kfz-Kosten (Benzin, Wartung) | Eingangsrechnungen (Kategorie "Kfz") |
| **B6.2** | Kfz-Steuer | Eingangsrechnungen / Bank |
| **B6.3** | Kfz-Versicherung | Eingangsrechnungen / Bank |
| **B6.4** | Leasingraten | Bank (Kategorie "Leasing") |
| **B6.5** | Abschreibungen Fahrzeuge | Manuell / Anlagenverzeichnis (später) |
| **B7** | Reisekosten: | |
| **B7.1** | Fahrtkosten (ÖPNV, Taxi) | Kassenbuch / Eingangsrechnungen |
| **B7.2** | Übernachtung, Verpflegung | Kassenbuch / Eingangsrechnungen (Reisekosten) |
| **B7.3** | Sonstige Reisekosten | Kassenbuch / Eingangsrechnungen |
| **B8** | Investitionen (Anschaffungen über 800€) | Eingangsrechnungen (Kategorie "Investitionen") |

**Teil 3 - Büro, Kommunikation, Sonstiges:**

| Feld | Beschreibung | Quelle in RechnungsPilot |
|------|--------------|---------------------------|
| **B9** | Büro- und Geschäftsbedarf | Eingangsrechnungen / Kassenbuch (Kategorie "Bürobedarf") |
| **B10** | Porto, Telefon, Internet | Eingangsrechnungen (Kategorie "Kommunikation") |
| **B11** | Rechts- und Beratungskosten | Eingangsrechnungen (Kategorie "Beratung") |
| **B12** | Fortbildung | Eingangsrechnungen (Kategorie "Fortbildung") |
| **B13** | Sonstige Betriebsausgaben: | |
| **B13.1** | Instandhaltung / Reparaturen | Eingangsrechnungen (Kategorie "Reparaturen") |
| **B13.2** | Beiträge / Abgaben (IHK, etc.) | Eingangsrechnungen / Bank |
| **B13.3** | Buchhaltung / Steuerberatung | Eingangsrechnungen (Kategorie "Steuerberatung") |
| **B13.4** | Geschenke / Bewirtung | Kassenbuch / Eingangsrechnungen |
| **B13.5** | Übrige Kosten | Kassenbuch / Eingangsrechnungen (Kategorie "Sonstiges") |
| **B14** | Zinsaufwendungen | Bank (Kategorie "Zinsen") |
| **B15** | Kredittilgung | Bank (Kategorie "Tilgung") |
| **B16** | Gezahlte Umsatzsteuer (Kennziffer 83) | Aus UStVA-Berechnung (Vorsteuer) |
| **B17** | Vorsteuererstattung vom Finanzamt | Bank (eingehende Erstattung) |
| **B18** | Sonstige Abzüge | Manuell erfassen (Sonderfälle) |

**Summe B:** Automatisch aus B1-B18

---

##### **Tabelle C: Absetzungen vom Einkommen (Abzüge)**

| Feld | Beschreibung | Quelle in RechnungsPilot |
|------|--------------|---------------------------|
| **C1** | Steuern (Einkommensteuer, Gewerbesteuer) | Bank (Abgänge "Finanzamt") + Manuell |
| **C2** | Pflichtbeiträge Krankenversicherung | Bank (Kategorie "KV") |
| **C3** | Pflichtbeiträge Pflegeversicherung | Bank (Kategorie "PV") |
| **C4** | Rentenversicherung (freiwillig) | Bank (Kategorie "RV") |
| **C5** | Riester-Beiträge | Bank (Kategorie "Riester") |
| **C6** | Sonstige Absetzungen | Manuell erfassen |

**Summe C:** Automatisch

---

#### **Zusätzliche Angaben im Formular:**

**1. Firmendaten:**
- Name, Anschrift, Steuernummer
- **Quelle:** Stammdaten (Unternehmen)

**2. Bewilligungszeitraum:**
- Von-Bis (z.B. 01.01.2026 - 30.06.2026)
- **Eingabe:** Manuell bei Export-Aufruf

**3. Art der EKS:**
- ☐ Vorläufige EKS (Prognose)
- ☐ Abschließende EKS (tatsächliche Zahlen)
- **Auswahl:** Vom User beim Export

**4. Personaldaten:**
- Anzahl Mitarbeiter (Vollzeit/Teilzeit/Geringfügig)
- **Quelle:** Stammdaten (Personal) oder manuell

**5. Fahrzeugnutzung:**
- Anzahl Fahrzeuge
- Betrieblich genutzt in %
- **Quelle:** Stammdaten (Fahrzeuge) oder manuell

**6. Darlehen & Zuschüsse:**
- Erhaltene Fördermittel (z.B. Gründungszuschuss)
- Darlehen (Höhe, Zinssatz)
- **Quelle:** Manuell erfassen (einmalig)

**7. Monatliche Aufschlüsselung:**
- Jede Kategorie (A1-C6) wird **pro Monat** aufgeschlüsselt
- 6 Spalten für 6-Monats-Zeitraum
- **Automatisch:** RechnungsPilot summiert nach Monat

---

#### **Export-Workflow:**

**Schritt 1: User wählt Zeitraum**
```
┌────────────────────────────────────────┐
│ Anlage EKS exportieren                 │
├────────────────────────────────────────┤
│                                        │
│ Bewilligungszeitraum:                  │
│ Von: [01.01.2026] Bis: [30.06.2026]   │
│                                        │
│ Art der EKS:                           │
│ ○ Vorläufig (Prognose)                 │
│ ● Abschließend (tatsächliche Werte)   │
│                                        │
│ [Abbrechen]  [Daten prüfen →]          │
└────────────────────────────────────────┘
```

**Schritt 2: Daten-Vorschau**
```
┌────────────────────────────────────────┐
│ EKS-Vorschau: Jan-Jun 2026             │
├────────────────────────────────────────┤
│ Tabelle A - Betriebseinnahmen          │
│ A1: Betriebseinnahmen      15.450,00 € │
│   └─ Quelle: 42 Rechnungen             │
│ A2: Privatentnahmen         3.200,00 € │
│   └─ Quelle: 6 Kassenbucheinträge      │
│ ...                                    │
│                                        │
│ ⚠️ Fehlende Daten:                     │
│ • B6.5: Kfz-Abschreibung (manuell)     │
│ • C5: Riester-Beiträge (prüfen)        │
│                                        │
│ [Zurück]  [Fehlende Daten ergänzen]    │
│           [Als PDF exportieren]        │
└────────────────────────────────────────┘
```

**Schritt 3: Export-Formate**
- **PDF-Formular:** Vorausgefülltes Anlage-EKS-Formular
- **CSV/Excel:** Tabellen A, B, C zum manuellen Übertragen
- **JSON:** Maschinenlesbar für zukünftige digitale Übermittlung

---

#### **Mapping Kassenbuch → EKS**

**Kategorien im Kassenbuch erweitern:**
RechnungsPilot bietet vordefinierte Kategorien, die direkt zu EKS-Feldern mappen:

**Einnahmen-Kategorien:**
- "Betriebseinnahmen" → A1
- "Privatentnahme" → A2 (negativ)
- "Sonstige Einnahmen" → A3
- "Privateinlage" → A4

**Ausgaben-Kategorien:**
- "Wareneinkauf" → B1
- "Personal" → B2
- "Raumkosten" → B3
- "Versicherungen" → B4
- "Werbung" → B5
- "Kfz" → B6
- "Reisekosten" → B7
- "Investitionen" → B8
- "Bürobedarf" → B9
- "Kommunikation" → B10
- "Beratung" → B11
- "Fortbildung" → B12
- "Sonstiges" → B13.5

**Automatische Zuordnung:**
- User wählt Kategorie → RechnungsPilot weiß automatisch, wo es in EKS hingehört
- Bei Export: Automatische Summierung pro Monat

---

#### **Fehlende Daten (nicht in Kassenbuch/Rechnungen):**

**Manuell zu erfassen:**
- Abschreibungen (B6.5)
- Steuerzahlungen (C1)
- Versicherungsbeiträge (C2-C6)
- Darlehen/Zuschüsse

**Lösung:**
- **Extra-Eingabemaske "EKS-Zusatzdaten":**
  ```
  ┌────────────────────────────────────────┐
  │ EKS-Zusatzdaten für Jan-Jun 2026       │
  ├────────────────────────────────────────┤
  │                                        │
  │ Abschreibungen:                        │
  │ Kfz-Abschreibung (B6.5):   [____] €    │
  │                                        │
  │ Steuern & Versicherungen:              │
  │ Einkommensteuer (C1):      [____] €    │
  │ Krankenversicherung (C2):  [____] €    │
  │ Pflegeversicherung (C3):   [____] €    │
  │ ...                                    │
  │                                        │
  │ [Speichern]  [Abbrechen]               │
  └────────────────────────────────────────┘
  ```
- Daten werden pro Bewilligungszeitraum gespeichert
- Bei erneutem Export: Vorausgefüllt

---

#### **Plausibilitätsprüfung:**

**Automatische Warnungen:**
- ⚠️ "Betriebseinnahmen unter 100 € pro Monat - ist das korrekt?"
- ⚠️ "Keine Ausgaben für Krankenversicherung - vergessen?"
- ⚠️ "Privatentnahmen höher als Einnahmen - Liquiditätsproblem?"
- ⚠️ "Umsatzsteuer-Summe passt nicht zu UStVA - bitte prüfen"

**GoBD-Hinweise:**
- Alle Belege (Eingangs-/Ausgangsrechnungen, Kassenbuch) müssen archiviert sein
- Hinweis beim Export: "Stelle sicher, dass alle Belege für das Jobcenter vorliegen"

---

#### **Integration mit bestehenden Modulen:**

**1. Kassenbuch:**
- Kategorien müssen EKS-kompatibel sein
- Monatliche Zusammenfassung ermöglichen

**2. Eingangsrechnungen:**
- Automatische Zuordnung zu EKS-Kategorien (B1-B18)

**3. Ausgangsrechnungen:**
- Automatische Summierung für A1

**4. Bank-Integration:**
- Steuerzahlungen erkennen (C1)
- Versicherungsbeiträge erkennen (C2-C6)
- Darlehenstilgung erkennen (B15)

**5. UStVA:**
- A5 (Umsatzsteuer) aus UStVA-Berechnung
- B16 (Vorsteuer) aus UStVA-Berechnung

---

#### **Technische Umsetzung:**

**Datenbank-Schema:**
```sql
CREATE TABLE eks_zusatzdaten (
  id INTEGER PRIMARY KEY,
  zeitraum_von DATE,
  zeitraum_bis DATE,
  kategorie TEXT, -- z.B. "B6.5", "C1"
  monat INTEGER,  -- 1-6 im Bewilligungszeitraum
  betrag DECIMAL,
  beschreibung TEXT,
  erstellt_am TIMESTAMP
);

CREATE TABLE eks_export (
  id INTEGER PRIMARY KEY,
  zeitraum_von DATE,
  zeitraum_bis DATE,
  art TEXT, -- "vorlaeufig" oder "abschliessend"
  exportiert_am TIMESTAMP,
  datei_pfad TEXT,
  daten_json TEXT -- komplette EKS-Daten als JSON
);
```

**Export-Library (Python):**
- Template: Offizielles EKS-PDF-Formular
- Ausfüllen mit `pypdf` oder `reportlab`
- Alternativ: HTML → PDF (Weasyprint, Puppeteer)

**Frontend (React):**
- Komponente `EksExport.tsx`
- Daten-Aggregation via API
- Vorschau mit `react-pdf`

---

#### **Zeitlicher Workflow (User-Sicht):**

**Szenario: Abschließende EKS für Jan-Jun 2026**

1. **Juni 2026 endet** → Bewilligungszeitraum vorbei
2. **User öffnet RechnungsPilot** → Menü: "Anlage EKS exportieren"
3. **Zeitraum wählen:** 01.01.2026 - 30.06.2026
4. **Art wählen:** Abschließend
5. **Automatische Datensammlung:**
   - Alle Ausgangsrechnungen (A1)
   - Alle Eingangsrechnungen (B1-B18)
   - Alle Kassenbucheinträge (A2, A4, B-Kategorien)
   - UStVA-Daten (A5, B16)
   - Bank-Transaktionen (C1-C6)
6. **Fehlende Daten ergänzen:**
   - Abschreibungen manuell eingeben
   - Versicherungsbeiträge prüfen
7. **Vorschau prüfen:**
   - Summen kontrollieren
   - Plausibilität checken
8. **PDF generieren** → Speichern & an Jobcenter senden

**Zeitaufwand:** ~10 Minuten (vs. 2-3 Stunden manuell!)

---

#### **Unique Selling Point (USP):**

**Kein anderes Buchhaltungsprogramm bietet EKS-Export!**

**Vorteile für Zielgruppe:**
- ✅ Riesige Zeitersparnis (2-3 Stunden → 10 Minuten)
- ✅ Weniger Fehler (automatische Berechnung)
- ✅ Rechtssicher (alle Daten aus GoBD-konformen Belegen)
- ✅ Übersichtlich (monatliche Aufschlüsselung)
- ✅ Nachweisbar (alle Belege digital archiviert)

**Marketing-Aspekt:**
- "Die **einzige** Buchhaltungssoftware mit EKS-Export"
- Große Zielgruppe: ~400.000 Selbstständige mit ALG II (Schätzung)
- Community-Reichweite durch einzigartige Funktion

---

#### **MVP-Priorisierung:**

**Phase 1 (MVP):**
- ✅ Kategorie-Mapping definieren
- ✅ Daten-Aggregation (A, B, C)
- ✅ Einfacher CSV/Excel-Export
- ✅ Manuelle Zusatzdaten-Eingabe

**Phase 2 (Post-MVP):**
- PDF-Formular vorausfüllen
- Plausibilitätsprüfung
- Monatliche Vorschau-Reports

**Phase 3 (Later):**
- Vorläufige EKS mit Prognose-Modus
- Automatische Abschreibungsberechnung
- Bank-API-Integration für C1-C6

---

**Status:** Vollständig analysiert - Struktur, Mapping, Export-Workflow, Datenquellen, Technische Umsetzung geklärt.

**Hinweis:** Frage 3.4 (Zusammenarbeit mit Jobcentern / API-Anbindung) wurde an eine **Arbeitslosenselbsthilfe-Beratungsgruppe** zur Rückmeldung gegeben. Expertise aus der Community wird bei weiterer Entwicklung berücksichtigt.

---

### **📊 UStVA-Datenaufbereitung (Verbindung zu Kategorie 6)**

**Wichtige Erkenntnis:** Das Kassenbuch mit USt-Aufschlüsselung bildet die **Datenbasis für die Umsatzsteuervoranmeldung (UStVA)**.

**Datenquellen für UStVA:**
1. **Kassenbuch:**
   - Einnahmen nach Steuersatz (19%, 7%, 0%)
   - Ausgaben mit abziehbarer Vorsteuer
   - Privatentnahmen (nicht steuerbar)

2. **Eingangsrechnungen:**
   - Vorsteuer nach Steuersatz
   - Vorsteuerabzug berechtigt? (Ja/Nein)
   - Innergemeinschaftlicher Erwerb (§13b)
   - Reverse-Charge

3. **Ausgangsrechnungen:**
   - Umsätze nach Steuersatz
   - Steuerfreie Umsätze
   - Innergemeinschaftliche Lieferungen

**Automatische UStVA-Berechnung:**
```
Umsatzsteuer (Kennziffer 81):
= Einnahmen 19% (Kassenbuch) + Ausgangsrechnungen 19%
→ USt-Betrag automatisch summiert

Vorsteuer (Kennziffer 66):
= Ausgaben 19% (Kassenbuch, Vorsteuerabzug=Ja) + Eingangsrechnungen 19%
→ Vorsteuer-Betrag automatisch summiert

Zahllast/Erstattung:
= Umsatzsteuer - Vorsteuer
```

**Implementierung:**
- Monatliche/quartalsweise Auswertung
- Automatische Summierung aus allen Datenquellen
- Prüfung auf Vollständigkeit
- Export für ELSTER (später)

**Status:** Grundkonzept definiert, Details in Kategorie 6.

---

### **DATEV-Export (Kategorie 4) - ✅ GEKLÄRT**

#### **Zentrales Konzept: Buchungstext = Master-Kategorie**

**RechnungsPilot verwendet ein einheitliches Kategorisierungssystem:**

```
User wählt Buchungstext/Kategorie (z.B. "Büromaterial")
         ↓
System ordnet automatisch zu:
  ├─ DATEV-Konto: 4910 (SKR03) / 6815 (SKR04)
  ├─ EKS-Kategorie: B9 (Büro- und Geschäftsbedarf)
  ├─ UStVA: Vorsteuer abziehbar (falls zutreffend)
  └─ Kassenbuch/Rechnungen: Kategorie-Feld
```

**Vorteile:**
- ✅ Einmal kategorisieren → Alle Exporte korrekt
- ✅ Keine Mehrfach-Zuordnung nötig
- ✅ Konsistenz über alle Module (Kassenbuch, Rechnungen, DATEV, EKS)
- ✅ Einfach für Laien (nur Kategorie auswählen)
- ✅ Flexibel (Konten überschreibbar für individuelle Steuerbüros)

---

#### **Kategorien-Master-Tabelle**

Diese zentrale Tabelle definiert alle Zuordnungen:

**Ausgaben (Aufwand):**

| Buchungstext/Kategorie | SKR03 | SKR04 | EKS | Art |
|------------------------|-------|-------|-----|-----|
| Wareneinkauf | 5000 | 7000 | B1 | Aufwand |
| Löhne und Gehälter | 4100 | 6020 | B2.1 | Aufwand |
| Sozialabgaben | 4130 | 6030 | B2.2 | Aufwand |
| Raumkosten | 4210 | 6300 | B3 | Aufwand |
| Versicherungen (Betrieb) | 4360 | 6500 | B4 | Aufwand |
| Werbung | 4600 | 6640 | B5 | Aufwand |
| Kfz-Kosten (laufend) | 4530 | 6520 | B6.1 | Aufwand |
| Kfz-Steuer | 4531 | 6530 | B6.2 | Aufwand |
| Kfz-Versicherung | 4532 | 6535 | B6.3 | Aufwand |
| Leasing | 4850 | 6825 | B6.4 | Aufwand |
| Abschreibungen Kfz | 4832 | 6222 | B6.5 | Aufwand |
| Reisekosten (Fahrt) | 4670 | 6681 | B7.1 | Aufwand |
| Reisekosten (Übernachtung) | 4673 | 6683 | B7.2 | Aufwand |
| Investitionen | - | - | B8 | Anlage |
| Büromaterial | 4910 | 6815 | B9 | Aufwand |
| Kommunikation (Tel/Internet) | 4920 | 6805 | B10 | Aufwand |
| Beratung | 4945 | 6821 | B11 | Aufwand |
| Fortbildung | 4946 | 6824 | B12 | Aufwand |
| Reparaturen | 4800 | 6820 | B13.1 | Aufwand |
| Beiträge/Abgaben | 4930 | 6822 | B13.2 | Aufwand |
| Steuerberatung | 4157 | 6827 | B13.3 | Aufwand |
| Bewirtung | 4650 | 6644 | B13.4 | Aufwand |
| Sonstiges | 4980 | 6855 | B13.5 | Aufwand |
| Zinsen | 2100 | 2100 | B14 | Aufwand |
| Tilgung | - | - | B15 | Privat |

**Einnahmen (Erlöse):**

| Buchungstext/Kategorie | SKR03 | SKR04 | EKS | Art |
|------------------------|-------|-------|-----|-----|
| Betriebseinnahmen 19% | 8400 | 4400 | A1 | Erlös |
| Betriebseinnahmen 7% | 8300 | 4300 | A1 | Erlös |
| Betriebseinnahmen 0% (§19) | 8100 | 4120 | A1 | Erlös |
| Privatentnahme | 1890 | 1800 | A2 | Privat |
| Sonstige Einnahmen | 2650 | 2731 | A3 | Erlös |
| Privateinlage | 1880 | 1790 | A4 | Privat |

**Hinweis:** Konten-Nummern sind Standard-Vorschläge. User kann diese in Stammdaten überschreiben (z.B. wenn Steuerbüro abweichende Konten nutzt).

---

#### **4.1 Kontenrahmen: SKR03 und SKR04**

✅ **Beide Kontenrahmen unterstützen**
- SKR03 (Gewerbetreibende)
- SKR04 (Freiberufler)

✅ **Automatische Ableitung aus Stammdaten:**
- Bei Einrichtung: Frage "Freiberuflich oder Gewerbe?"
  - Freiberuflich → SKR04 vorausgewählt
  - Gewerbe → SKR03 vorausgewählt
- User kann manuell überschreiben

✅ **Parallelbetrieb möglich:**
- Bei gemischter Tätigkeit (Gewerbe + Freiberuf):
  - Beide Kontenrahmen verfügbar
  - Pro Buchung auswählbar (Stammdaten: "Welche Tätigkeit?")
  - Separate DATEV-Exporte für jede Tätigkeit

**Technische Umsetzung:**
```sql
CREATE TABLE stammdaten_unternehmen (
  id INTEGER PRIMARY KEY,
  taetigkeitsart TEXT, -- "freiberuflich", "gewerbe", "gemischt"
  kontenrahmen_primaer TEXT, -- "SKR03" oder "SKR04"
  kontenrahmen_sekundaer TEXT -- optional bei "gemischt"
);
```

---

#### **4.2 DATEV ASCII-Format & Stammdaten**

✅ **Format:** DATEV ASCII CSV (Standard-Format, siehe `datev-export.csv`)

✅ **Pflicht-Stammdaten bei DATEV-Export-Aktivierung:**

**1. Beraternummer (7-stellig)**
- Vom Steuerberater erhalten
- Pflichtfeld im DATEV-Header

**2. Mandantennummer (5-stellig)**
- Vom Steuerberater erhalten
- Pflichtfeld im DATEV-Header

**3. Individuelle Konten-Zuordnung (optional, aber empfohlen):**
- **Erlös-Konten** (Steuerbüros weichen oft ab):
  - Erlös 19%: Standard 8400 (SKR03) / 4400 (SKR04)
  - Erlös 7%: Standard 8300 (SKR03) / 4300 (SKR04)
  - Erlös 0% (§19): Standard 8100 (SKR03) / 4120 (SKR04)
- **Steuer-Konten:**
  - Umsatzsteuer 19%: Standard 1776 (SKR03) / 1776 (SKR04)
  - Umsatzsteuer 7%: Standard 1771 (SKR03) / 1771 (SKR04)
  - Vorsteuer 19%: Standard 1576 (SKR03) / 1406 (SKR04)
  - Vorsteuer 7%: Standard 1571 (SKR03) / 1401 (SKR04)

**Eingabemaske "DATEV-Einstellungen":**
```
┌─────────────────────────────────────────┐
│ DATEV-Export aktivieren                 │
├─────────────────────────────────────────┤
│ Beraternummer: [_______]                │
│ Mandantennummer: [_____]                │
│                                         │
│ Kontenrahmen: ● SKR03  ○ SKR04          │
│                                         │
│ Individuelle Konten (optional):         │
│ ┌─────────────────────────────────────┐ │
│ │ Erlös 19%:    [8400] (Standard)     │ │
│ │ Erlös 7%:     [8300] (Standard)     │ │
│ │ Erlös 0%:     [8100] (Standard)     │ │
│ │ USt 19%:      [1776] (Standard)     │ │
│ │ Vorsteuer 19%:[1576] (Standard)     │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ [Standard wiederherstellen]             │
│                                         │
│ [Abbrechen]  [Speichern & Aktivieren]   │
└─────────────────────────────────────────┘
```

**Validierung:**
- Beim Klick auf "Aktivieren": Prüfen ob Beraternr. & Mandantennr. vorhanden
- Falls fehlend: Fehlermeldung "Bitte tragen Sie zuerst die DATEV-Daten ein"

---

#### **4.3 Buchungsstapel-Export**

✅ **Zeitraum-Export:**
- User wählt Zeitraum (z.B. "Januar 2026" oder "01.01.-31.01.2026")
- Alle Belege des Zeitraums werden exportiert:
  - Eingangsrechnungen (mit Zahlungsstatus)
  - Ausgangsrechnungen (mit Zahlungsstatus)
  - Kassenbucheinträge

✅ **Automatische Konten-Zuordnung:**
- Basierend auf **Buchungstext/Kategorie** (siehe Master-Tabelle)
- User wählt z.B. "Büromaterial" → System verwendet Konto 4910 (SKR03)
- **Überschreibbar** in Stammdaten (für Steuerbüro-Abweichungen)

✅ **Detailgrad: Rechnungssummen**
- **Eine Buchungszeile pro Beleg** (nicht pro Rechnungsposition)
- Brutto-Betrag wird gebucht
- Steuersatz in Beleginfo

**Beispiel-Buchung (Eingangsrechnung Büromaterial 119,00 € brutto):**
```csv
119,00;"S";"";"";"";"";"4910";"1600";"";"0101";"RE2025-001";"";"";
"Büromaterial Firma XY";"";"";"";"";"";"";"Steuersatz";"19"
```

✅ **Soll/Haben-Buchungen automatisch generieren:**

**Eingangsrechnungen (Ausgaben):**
```
Soll:  Aufwandskonto (z.B. 4910 Büromaterial)
Haben: Verbindlichkeiten (1600) oder Kasse (1000) oder Bank (1200)
Kennzeichen: "S" (Soll)
```

**Ausgangsrechnungen (Einnahmen):**
```
Soll:  Forderungen (1410) oder Kasse (1000) oder Bank (1200)
Haben: Erlöskonto (z.B. 8400 Erlöse 19%)
Kennzeichen: "H" (Haben)
```

**Kassenbucheinträge:**
- Bei Bareinnahme: Kasse (1000) an Erlöskonto (8400) → "H"
- Bei Barausgabe: Aufwandskonto (4910) an Kasse (1000) → "S"

**Zahlungsstatus berücksichtigen:**
- Rechnung unbezahlt: Gegenkonto = Forderungen (1410) / Verbindlichkeiten (1600)
- Rechnung bezahlt per Bank: Gegenkonto = Bank (1200)
- Rechnung bezahlt bar: Gegenkonto = Kasse (1000)
- Teilzahlung: Mehrere Buchungszeilen

---

#### **4.4 DATEV-Format-Details**

✅ **Format: CSV-DATEV ASCII**
- Basierend auf DATEV-Spezifikation (siehe `datev-export.csv`)
- Header-Zeile mit Metadaten
- Spalten-Überschriften-Zeile
- Buchungszeilen

✅ **Header (Zeile 1):**
```
"EXTF";510;21;"Buchungsstapel";7;[Timestamp];"";[App];"[Firma]";"";
[Beraternr];[Mandantennr];[WJ-Beginn];4;[Von];[Bis];"[Bezeichnung]";
"";1;0;1;"EUR";;;;;"[SKR]";;;"";""
```

**Pflichtfelder im Header:**
- Beraternummer (Stammdaten)
- Mandantennummer (Stammdaten)
- Kontenrahmen ("03" oder "04")
- Wirtschaftsjahr-Beginn
- Zeitraum Von-Bis

✅ **Buchungszeilen - Pflichtfelder:**

| Feld | Beschreibung | Beispiel |
|------|-------------|----------|
| **Umsatz** | Brutto-Betrag | 119,00 |
| **Soll/Haben-Kz** | "S" oder "H" | "S" |
| **Konto** | Aufwands-/Erlöskonto | 4910 |
| **Gegenkonto** | Verbindl./Ford./Kasse | 1600 |
| **Belegdatum** | TTMM-Format | 0101 |
| **Belegfeld 1** | Belegnummer | RE2025-001 |
| **Buchungstext** | Beschreibung | Büromaterial |
| **Beleginfo - Art 1** | "Steuersatz" | Steuersatz |
| **Beleginfo - Inhalt 1** | "19" / "7" / "" | 19 |

✅ **Optionale Felder:**
- BU-Schlüssel (Buchungsschlüssel)
- Kostenstellen (KOST1, KOST2)
- Skonto
- Zahlungsweise
- EU-Land / UStID (bei innergemeinschaftlichen Geschäften)
- Diverse Adressnummer
- Viele weitere (~100+ Felder)

✅ **BU-Schlüssel (Buchungsschlüssel):**
- **Standard: Leer lassen**
  - DATEV berechnet automatisch aus Konto + Steuersatz
- **Ausnahmen:**
  - "20" bei Stornobuchungen
  - Spezielle Schlüssel bei EU-Geschäften (z.B. "40" für innergemeinschaftlichen Erwerb)
- **Power-User:** Können manuell BU-Schlüssel setzen

**Regel:** Wenn unsicher → BU-Schlüssel weglassen, DATEV macht das automatisch richtig.

---

#### **Export-Workflow:**

**Schritt 1: Zeitraum wählen**
```
┌─────────────────────────────────────────┐
│ DATEV-Export                            │
├─────────────────────────────────────────┤
│ Zeitraum:                               │
│ Von: [01.01.2026]  Bis: [31.01.2026]   │
│                                         │
│ Filter:                                 │
│ ☑ Eingangsrechnungen                    │
│ ☑ Ausgangsrechnungen                    │
│ ☑ Kassenbuch                            │
│                                         │
│ [Abbrechen]  [Vorschau →]               │
└─────────────────────────────────────────┘
```

**Schritt 2: Vorschau & Prüfung**
```
┌─────────────────────────────────────────┐
│ DATEV-Export Vorschau: Januar 2026      │
├─────────────────────────────────────────┤
│ 📊 Zusammenfassung:                     │
│ • 42 Buchungen (15 ER / 23 AR / 4 KB)   │
│ • Summe Einnahmen: 15.430,00 €          │
│ • Summe Ausgaben: 4.290,00 €            │
│                                         │
│ ⚠️ Warnungen:                           │
│ • 3 Rechnungen ohne Kategorie           │
│   → Bitte nachträglich kategorisieren   │
│                                         │
│ ✅ Bereit für Export                    │
│                                         │
│ [Zurück]  [Fehlende Daten ergänzen]     │
│           [Als CSV exportieren]         │
└─────────────────────────────────────────┘
```

**Schritt 3: Export**
- CSV-Datei generieren: `DATEV_2026-01_Buchungen.csv`
- Encoding: Windows-1252 (DATEV-Standard)
- Speicherort: User wählt
- Hinweis: "Datei kann jetzt in DATEV importiert werden"

---

#### **Technische Umsetzung:**

**Datenbank-Schema:**
```sql
CREATE TABLE datev_einstellungen (
  id INTEGER PRIMARY KEY,
  beraternummer TEXT,
  mandantennummer TEXT,
  kontenrahmen TEXT, -- "SKR03" oder "SKR04"
  individuell_konten JSON -- {"8400": "8405", ...}
);

CREATE TABLE kategorien_mapping (
  id INTEGER PRIMARY KEY,
  kategorie TEXT, -- "Büromaterial"
  konto_skr03 TEXT, -- "4910"
  konto_skr04 TEXT, -- "6815"
  eks_kategorie TEXT, -- "B9"
  kontenart TEXT -- "Aufwand", "Erlös", "Privat", "Anlage"
);

CREATE TABLE datev_export_log (
  id INTEGER PRIMARY KEY,
  zeitraum_von DATE,
  zeitraum_bis DATE,
  anzahl_buchungen INTEGER,
  exportiert_am TIMESTAMP,
  datei_pfad TEXT
);
```

**Export-Library (Python):**
```python
# datev_export.py
import csv
from datetime import datetime

def export_datev(zeitraum_von, zeitraum_bis, kontenrahmen):
    # 1. Header generieren
    header = generate_datev_header(kontenrahmen)

    # 2. Buchungen sammeln
    buchungen = []
    buchungen += get_eingangsrechnungen(zeitraum_von, zeitraum_bis)
    buchungen += get_ausgangsrechnungen(zeitraum_von, zeitraum_bis)
    buchungen += get_kassenbuch(zeitraum_von, zeitraum_bis)

    # 3. Soll/Haben generieren
    buchungszeilen = [create_buchungszeile(b, kontenrahmen) for b in buchungen]

    # 4. CSV schreiben
    write_datev_csv(header, buchungszeilen, filename)
```

**Frontend (React):**
```typescript
// DatevExport.tsx
import { useState } from 'react';

function DatevExport() {
  const [zeitraum, setZeitraum] = useState({ von: '', bis: '' });
  const [vorschau, setVorschau] = useState(null);

  const generatePreview = async () => {
    const data = await api.datev.preview(zeitraum);
    setVorschau(data);
  };

  const exportCSV = async () => {
    await api.datev.export(zeitraum);
  };

  return (/* UI siehe oben */);
}
```

---

#### **Validierung & Fehlervermeidung:**

**Vor Export prüfen:**
- ✅ Alle Belege haben Kategorie zugeordnet
- ✅ Alle Konten existieren im gewählten Kontenrahmen
- ✅ Beraternummer & Mandantennummer vorhanden
- ✅ Belegdaten plausibel (nicht in der Zukunft)
- ✅ Keine negativen Beträge (außer Storno)

**Warnungen:**
- ⚠️ "3 Belege ohne Kategorie - Export unvollständig"
- ⚠️ "Kassenendstand stimmt nicht mit Berechnungen überein"
- ⚠️ "Einige Konten weichen von Standard ab - bitte prüfen"

---

#### **DATEV Kassenarchiv Online:**

**Status:** Keine offizielle Dokumentation gefunden

**Empfehlung:**
- MVP: Standard-DATEV-Export (wie oben) ✅
- Post-MVP: DATEV Kassenarchiv separat recherchieren
- Eventuell bei DATEV anfragen oder Reverse Engineering

**Hinweis:** Da RechnungsPilot kein POS-Kassensystem ist (keine TSE), ist DATEV Kassenarchiv nicht verpflichtend. Standard-DATEV-Export reicht für MVP.

---

**Status:** Vollständig geklärt - Kontenrahmen, Format, Buchungsstapel, Kategorisierungssystem, Export-Workflow, Technische Umsetzung definiert.

---

# Kategorie 5: Bank-Integration (CSV-Import)

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
  "author": "RechnungsPilot Team",
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
2. System: "❌ Unbekanntes Format - Möchten Sie ein Template erstellen?"
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

**RechnungsPilot unterscheidet 3 Kontotypen:**

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

## **🔍 Marktbeobachtung & Competitor Research**

### **AGENDA (Lexware)**

**Import-Funktionen:**

1. **DATEV-Import**
   - Kann DATEV-Daten importieren
   - Kompatibilität mit DATEV-Schnittstelle

2. **Beleg-Import (PDF + XML)**
   - **Voraussetzung:** PDF und XML müssen denselben Dateinamen haben
   - **Format:** `rechnung-123.pdf` + `rechnung-123.xml`
   - **Bulk-Import:** Unterstützt gezippte Belegbilder
   - **Workflow:** ZIP hochladen → AGENDA entpackt → Matcht PDF+XML → Importiert

**Relevanz für RechnungsPilot:**
- ✅ **PDF+XML-Pairing:** Sollten wir auch unterstützen (Standard bei ZUGFeRD)
- ✅ **ZIP-Import:** Praktisch für Massen-Upload von gescannten Belegen
- ✅ **Dateinamen-Matching:** Konvention übernehmen (benutzerfreundlich)

**Implementierungs-Idee:**
```python
def import_beleg_zip(zip_file):
    """
    Importiert ZIP mit gepaarten PDF+XML-Belegen

    Struktur:
    belege.zip
    ├── rechnung-001.pdf
    ├── rechnung-001.xml
    ├── rechnung-002.pdf
    └── rechnung-002.xml
    """
    files = extract_zip(zip_file)

    # PDFs und XMLs matchen
    pairs = match_pdf_xml_by_filename(files)

    for pdf, xml in pairs:
        # ZUGFeRD/XRechnung parsen
        rechnung_data = parse_xrechnung(xml)

        # PDF als Beleg anhängen
        rechnung_data['beleg_pdf'] = pdf

        # In Rechnungseingangs-/Ausgangsbuch eintragen
        create_rechnung(rechnung_data)
```

**Status:** 📋 Für Kategorie 9 (Import-Schnittstellen) vorgemerkt

---

### **Noch zu klären (siehe fragen.md):**

- Kategorie 6: UStVA (Details)
- Kategorie 7: EÜR
- Kategorie 8: Stammdaten-Erfassung
- Kategorie 9: Import-Schnittstellen (inkl. AGENDA-kompatibel)
- Kategorie 10: Backup & Update
- Kategorie 11: Steuersätze
- Kategorie 12: Hilfe-System
- Kategorie 13: Scope & Priorisierung

---

## **💬 Community-Vorschläge & Feedback**

### **Vorschlag 1: LibreOffice-Rechnungsvorlagen mit ZUGFeRD-Platzhaltern**

**Quelle:** Community-Diskussion auf [forum.linuxguides.de](https://forum.linuxguides.de)
**Datum:** 2025-12-03

**Idee:**
- Rechnungsvorlagen für LibreOffice Writer/Calc bereitstellen
- Platzhalter nach ZUGFeRD-Richtlinien
- Integration mit RechnungsPilot:
  - Daten aus RechnungsPilot in Vorlage einfügen
  - Automatisches Befüllen aller Pflichtfelder
  - Export als ZUGFeRD-PDF

**Vorteile:**
- ✅ User können individuelles Design gestalten
- ✅ LibreOffice = Open Source (passt zur Philosophie)
- ✅ Plattformunabhängig
- ✅ ZUGFeRD-konform (E-Rechnungspflicht ab 2025)
- ✅ Keine PDF-Generierung in Code nötig

**Technische Umsetzung:**
- **Vorlagen-Repository:** Sammlung von LO-Templates
  - Standard-Vorlage (schlicht)
  - Business-Vorlage (professionell)
  - Kreativ-Vorlage (für Designer/Kreative)
- **Platzhalter-System:**
  ```
  # Rechnungsinformationen
  {{RECHNUNGSNUMMER}}
  {{DATUM}}
  {{RECHNUNGSTYP}}  # z.B. "Rechnung", "Gutschrift", "Stornorechnung"
  {{ZAHLUNGSZIEL}}
  {{FAELLIGKEITSDATUM}}

  # Lieferant (Absender) - Strukturierte Adresse
  {{ABSENDER_VORNAME}}
  {{ABSENDER_NACHNAME}}
  {{ABSENDER_FIRMA}}  # Optional, falls vorhanden
  {{ABSENDER_STRASSE}}
  {{ABSENDER_HAUSNUMMER}}  # Optional separat
  {{ABSENDER_PLZ}}
  {{ABSENDER_ORT}}
  {{ABSENDER_LAND}}
  {{ABSENDER_TELEFON}}
  {{ABSENDER_EMAIL}}
  {{ABSENDER_WEBSITE}}
  {{ABSENDER_STEUERNUMMER}}
  {{ABSENDER_USTID}}
  {{ABSENDER_BANKNAME}}
  {{ABSENDER_IBAN}}
  {{ABSENDER_BIC}}

  # Kunde (Empfänger) - Strukturierte Adresse
  {{KUNDE_VORNAME}}
  {{KUNDE_NACHNAME}}
  {{KUNDE_FIRMA}}  # Optional, falls vorhanden
  {{KUNDE_STRASSE}}
  {{KUNDE_HAUSNUMMER}}  # Optional separat
  {{KUNDE_PLZ}}
  {{KUNDE_ORT}}
  {{KUNDE_LAND}}
  {{KUNDE_KUNDENNUMMER}}
  {{KUNDE_USTID}}  # Falls B2B

  # Rechnungspositionen
  {{POSITIONEN}}  # Tabelle mit Spalten: Pos, Beschreibung, Menge, Einheit, Einzelpreis, Gesamt

  # Beträge
  {{NETTO_GESAMT}}
  {{UST_SATZ}}  # z.B. "19%"
  {{UST_BETRAG}}
  {{BRUTTO_GESAMT}}

  # Optional: Skonto
  {{SKONTO_PROZENT}}
  {{SKONTO_BETRAG}}
  {{SKONTO_TAGE}}

  # Optional: Zusatzinfos
  {{LEISTUNGSZEITRAUM_VON}}
  {{LEISTUNGSZEITRAUM_BIS}}
  {{BESTELLNUMMER}}
  {{LIEFERDATUM}}
  {{BEMERKUNG}}
  ```
- **Integration:**
  - RechnungsPilot öffnet LibreOffice via CLI
  - Befüllt Platzhalter mit Daten
  - Export als PDF + ZUGFeRD-XML einbetten
  - Speichert in RechnungsPilot

**Implementierung (später):**
- Phase: Rechnungsschreiben-Modul (nach MVP)
- Prio: Mittel (nice-to-have, nicht MVP)
- Abhängigkeiten: LibreOffice installiert, Python-UNO-Bridge

**Alternative (wenn LO nicht installiert):**
- HTML-Templates mit ähnlichen Platzhaltern
- Rendering im Browser
- Export via Headless-Chrome/Puppeteer

**Status:** Vorgemerkt für spätere Umsetzung, sehr guter Community-Input! 👍

---

## **Technologie-Stack (Vorschlag - noch zu diskutieren)**

### **Desktop-App:**
- **Tauri** (empfohlen) - Klein, schnell, sicher
  - Alternative: Electron (etabliert, größer)
- **Frontend:** React + Vite + TypeScript
- **UI-Framework:** TBD (Tailwind, MUI, shadcn/ui?)
- **State Management:** TanStack Query + Zustand

### **Backend (Embedded):**
- **FastAPI** (Python) in Tauri-Backend integriert
- **Datenbank:** SQLite mit SQLCipher (verschlüsselt)
- **ORM:** SQLAlchemy oder Prisma

### **Mobile (PWA):**
- React PWA mit Service Worker
- Optional später: Capacitor für Native Apps

### **Docker-Version:**
- FastAPI (Container)
- PostgreSQL oder SQLite (Volume)
- Nginx (Frontend)
- docker-compose.yml

### **Zusätzliche Tools:**
- **OCR:** Tesseract.js (Frontend) + EasyOCR (Backend, optional)
- **PDF:** pdf.js (Viewer), PyPDF2 (Manipulation)
- **ZUGFeRD/XRechnung:** factur-x (Python), zugferd.js
- **CSV-Parsing:** PapaParse (Frontend), pandas (Backend)
- **Backup:** Nextcloud API

---

## **Projektstruktur (Vorschlag)**

```
RechnungsPilot/
├── docs/                     # Dokumentation
│   ├── projekt.md           # Projektplan (vorhanden)
│   ├── fragen.md            # Offene Fragen (vorhanden)
│   └── claude.md            # Diese Datei
│
├── packages/                # Monorepo
│   ├── shared/              # Gemeinsame Types, Utils
│   ├── frontend/            # React App
│   ├── backend/             # FastAPI
│   └── desktop/             # Tauri Wrapper
│
├── docker/                  # Docker-Version
│   ├── frontend/
│   ├── backend/
│   └── docker-compose.yml
│
├── scripts/                 # Build-Scripts, Installer
├── tests/                   # E2E & Unit Tests
└── README.md
```

---

## **Nächste Schritte**

1. ✅ Kategorie 1 (Kassenbuch) geklärt
2. ⏳ Kategorien 2-13 klären (siehe fragen.md)
3. ⏳ Technologie-Stack finalisieren
4. ⏳ Datenbank-Schema entwerfen
5. ⏳ API-Spezifikation erstellen
6. ⏳ UI/UX-Konzept skizzieren
7. ⏳ Projekt-Setup (Repo, CI/CD)
8. ⏳ MVP-Entwicklung starten

---

## **Offene Risiken & Herausforderungen**

### **Rechtlich:**
- **GoBD-Konformität** - Unveränderbarkeit, Vollständigkeit, Nachvollziehbarkeit
- **DSGVO** - Datenschutz, Auskunftsrecht, Löschpflicht
- **Haftungsausschluss** - Keine Steuerberatung, keine Garantie
- **E-Rechnungspflicht ab 2025** - B2B muss ZUGFeRD/XRechnung können

### **Technisch:**
- **OCR-Genauigkeit** - Preprocessing notwendig
- **DATEV-Format** - Komplexe Spezifikation, evt. kostenpflichtige Doku
- **Bank-CSV-Formate** - Jede Bank anders, hoher Wartungsaufwand
- **Offline-Sync** - Konflikte bei Multi-Device-Nutzung
- **Auto-Update** - Sicher ohne Datenverlust

### **Organisatorisch:**
- **Solo-Entwicklung** - Längere Entwicklungszeit
- **Steuerberater-Review** - Braucht Partner für fachliche Prüfung
- **Beta-Tester** - Mindestens 5-10 echte Nutzer finden

---

## **Design-Prinzipien**

1. **Einfachheit vor Features** - Lieber weniger, dafür gut
2. **Laien-freundlich** - Tooltips, Wizards, klare Sprache
3. **Offline-First** - Muss ohne Internet funktionieren
4. **Datenschutz** - Lokale Daten, verschlüsselte Backups
5. **GoBD-konform** - Unveränderbar, vollständig, nachvollziehbar
6. **Open Source** - Transparent, erweiterbar, community-driven
7. **Performance** - Schneller Start (<3 Sekunden), flüssige UI
8. **Wartbarkeit** - Sauberer Code, Tests, Dokumentation

---

## **Changelog**

### **2025-12-04 - XRechnung/ZUGFeRD Pflichtfelder präzisiert**
- Vollständige Pflichtfelder-Tabelle mit EN-Codes (BT-Nummern)
- Kritische Pflichtfelder: Rechnungsinfo, Lieferant, Kunde, Leistung, Steuer, Gesamtbeträge
- Leitweg-ID (BT-13) für XRechnung bei öffentlichen Auftraggebern hervorgehoben
- Unterschiede XRechnung vs. ZUGFeRD klargestellt
- Optionale vs. empfohlene Felder dokumentiert
- Häufige Irrtümer aufgeklärt (keine Signatur-Pflicht, kein BIC nötig)
- Validierungs-Beispiele (Errors vs. Warnings) hinzugefügt

### **2025-12-05 - Kategorie 5 (Bank-Integration) geklärt**
- Template-System für CSV-Import konzipiert (JSON-basiert)
- Automatische Format-Erkennung definiert (Header-Matching, 80%+ Threshold)
- User-Workflows dokumentiert: Normal-User (Automatik) vs Power-User (Template-Editor)
- Template-Struktur spezifiziert: Column-Mapping, Validation, Encoding, Delimiter
- Template-Speicherorte: System-Templates + User-Templates
- Template-Sharing via GitHub für Community-Beiträge
- UI-Konzepte: Import-Dialog, Template-Editor, Vorschau
- Datenbank-Schema: bank_templates, bank_transaktionen, bank_imports
- Parser-Architektur (Python + pandas) skizziert
- MVP-Umfang: 6 System-Templates (Sparkasse MT940/CAMT V2/V8, PayPal, Volksbank, DKB, ING, N26)
- CSV-Beispiele gesammelt: Sparkasse/LZO (3 Formate), PayPal (anonymisiert)
- Bank-CSV Community-Contribution-Mechanismus etabliert (Issue Template, MAINTAINER.md)

### **2025-12-04 - Kategorie 4 (DATEV-Export) geklärt**
- Zentrales Kategorisierungssystem dokumentiert: Buchungstext = Master-Kategorie
- Kategorien-Master-Tabelle mit SKR03/SKR04/EKS-Mapping erstellt (28 Kategorien)
- Kontenrahmen-Unterstützung: SKR03 + SKR04, automatische Ableitung, Parallelbetrieb
- DATEV ASCII-Format vollständig analysiert (datev-export.csv)
- Pflicht-Stammdaten definiert: Beraternummer, Mandantennummer, individuelle Konten
- Buchungsstapel-Export: Zeitraum, Auto-Konten, Soll/Haben-Automatik
- DATEV-Format-Details: Pflichtfelder, optionale Felder, BU-Schlüssel-Regeln
- Export-Workflow mit Vorschau und Validierung konzipiert
- Datenbank-Schema für DATEV-Modul entworfen
- Technische Umsetzung (Python + React) skizziert

### **2025-12-04 - Kategorie 3 (Anlage EKS) geklärt**
- Anlage EKS (9-seitiges Jobcenter-Formular) vollständig analysiert
- Tabelle A (Betriebseinnahmen): 7 Kategorien dokumentiert
- Tabelle B (Betriebsausgaben): 28 Kategorien dokumentiert
- Tabelle C (Absetzungen): 6 Kategorien dokumentiert
- Mapping RechnungsPilot → EKS definiert
- Export-Workflow (CSV/Excel/PDF) konzipiert
- EKS-Zusatzdaten-Eingabemaske geplant
- Plausibilitätsprüfung definiert
- Integration mit Kassenbuch, Rechnungen, Bank, UStVA geklärt
- Datenbank-Schema für EKS-Modul entworfen
- MVP-Priorisierung in 3 Phasen aufgeteilt
- USP herausgearbeitet: Einzige Software mit EKS-Export

### **2025-12-03 - Projektstart**
- Initiales Projekt-Setup
- projekt.md analysiert
- fragen.md erstellt (Kategorien 2-13)
- claude.md angelegt
- Kategorie 1 (Kassenbuch) vollständig geklärt
- Kategorie 2 (PDF/E-Rechnungs-Import) vollständig geklärt
- Kassenbuch um USt-Aufschlüsselung erweitert
- UStVA-Datenaufbereitung konzipiert
- Technologie-Stack grob skizziert
- GitHub-Repository erstellt und konfiguriert
- Community-Ankündigungen vorbereitet

---

## **Notizen**

- **EKS-Export** ist ein Alleinstellungsmerkmal - kaum andere Software bietet das
- **Zwei Versionen** (Desktop + Docker) erhöhen Komplexität, aber auch Reichweite
- **Tauri vs. Electron** - Tauri scheint besser zu passen (Größe, Performance)
- **Import-Schnittstellen** (hellocash, etc.) könnten Nutzerbasis vergrößern
- **Mobile PWA** ist nice-to-have, nicht kritisch für MVP

---

**Fortsetzung folgt nach Klärung der Kategorien 2-13...**
