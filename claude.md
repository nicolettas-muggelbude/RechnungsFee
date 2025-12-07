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

## **Kategorie 6: Umsatzsteuer-Voranmeldung (UStVA)**

### **6.1 Strategie: Hybrid-Ansatz** ✅

**Entscheidung:** Stufenweise Entwicklung

#### **Version 1.0 (MVP): Zahlen vorbereiten** 📊

**Funktionsweise:**
- Software berechnet alle UStVA-Kennziffern aus Buchungen
- Zeigt Übersicht mit allen Werten
- User trägt Zahlen manuell ins ELSTER-Portal ein
- Kein ELSTER-Zertifikat erforderlich

**Vorteile für MVP:**
- ✅ Schnell entwickelbar (nur Berechnung, kein ELSTER-API)
- ✅ Kein rechtlicher Overhead (User submits selbst)
- ✅ Kein Zertifikats-Management
- ✅ User behält Kontrolle über Übermittlung
- ✅ Weniger Komplexität für Version 1.0

**Ausgabe:**
```
┌─────────────────────────────────────────────────┐
│ Umsatzsteuer-Voranmeldung Dezember 2025        │
├─────────────────────────────────────────────────┤
│                                                 │
│ Zeitraum: Dezember 2025 (monatlich)           │
│ Steuernummer: 12/345/67890                     │
│                                                 │
│ UMSÄTZE                                         │
│ ├─ Kz. 81  Umsätze 19% USt      15.890,00 €   │
│ ├─ Kz. 83  → Umsatzsteuer 19%    3.019,10 €   │
│ ├─ Kz. 86  Umsätze 7% USt        2.140,00 €   │
│ ├─ Kz. 88  → Umsatzsteuer 7%       149,80 €   │
│ └─ Kz. 35  § 13b UStG (Rev.Ch.)        0,00 € │
│                                                 │
│ VORSTEUER                                       │
│ ├─ Kz. 66  Vorsteuer abzugsfähig 1.284,50 €   │
│ └─ Kz. 61  § 13b UStG Vorsteuer        0,00 € │
│                                                 │
│ ─────────────────────────────────────────────── │
│ Umsatzsteuer-Vorauszahlung (Soll):             │
│                                   2.884,40 €   │
│ ─────────────────────────────────────────────── │
│                                                 │
│ [ PDF drucken ]  [ In ELSTER eintragen ]       │
└─────────────────────────────────────────────────┘
```

**User-Workflow:**
```
1. RechnungsPilot öffnen
   → Menü: "UStVA erstellen"

2. Zeitraum wählen
   → Dezember 2025

3. Berechnung prüfen
   → Alle Kennziffern werden automatisch aus Buchungen berechnet
   → Preview zeigt Aufschlüsselung

4. PDF drucken/speichern
   → Zum Nachschlagen/Dokumentation

5. ELSTER-Portal öffnen
   → https://www.elster.de einloggen

6. Zahlen manuell eintragen
   → Kz. 81: 15890,00
   → Kz. 83: 3019,10
   → etc.

7. In ELSTER abschicken
   → User übernimmt Verantwortung
```

---

#### **Version 2.0 (später): ELSTER-Integration** 🤖

**Funktionsweise:**
- Software erstellt ELSTER-XML
- Direkte Übermittlung ans Finanzamt
- ELSTER-Zertifikat erforderlich

**Zusätzliche Features:**
- ✅ Ein-Klick-Übermittlung
- ✅ Automatische XML-Generierung
- ✅ ELSTER-Empfangsbestätigung
- ✅ Status-Tracking (eingereicht, bestätigt, abgelehnt)

**Workflow:**
```
1. RechnungsPilot öffnen
   → UStVA erstellen

2. Zeitraum wählen
   → Dezember 2025

3. Berechnung prüfen
   → Preview

4. [ An ELSTER übermitteln ]  ← Ein Klick!
   → ELSTER-Zertifikat eingeben
   → XML generieren + senden
   → Fertig!
```

**Anforderungen für v2.0:**
- ELSTER-API-Integration (ERiC SDK)
- Zertifikats-Management
- XML-Generierung (ELSTER-Format)
- Fehlerbehandlung (Ablehnung, Nachforderung)

---

### **6.2 Berechnung der Kennziffern**

**Wichtigste UStVA-Kennziffern:**

#### **Umsätze (steuerpflichtig):**

| Kz. | Beschreibung | Quelle | Berechnung |
|-----|--------------|--------|------------|
| **81** | Umsätze 19% USt | Ausgangsrechnungen (Inland) | Summe Netto (USt-Satz 19%) |
| **83** | Umsatzsteuer 19% | Auto-berechnet | Kz. 81 × 0,19 |
| **86** | Umsätze 7% USt | Ausgangsrechnungen (Inland) | Summe Netto (USt-Satz 7%) |
| **88** | Umsatzsteuer 7% | Auto-berechnet | Kz. 86 × 0,07 |
| **41** | Innergemeinschaftliche Lieferungen | Ausgangsrechnungen (EU) | Summe Netto (0% USt, § 4 Nr. 1b UStG) |

#### **Innergemeinschaftlicher Erwerb (EU-Einkäufe):**

| Kz. | Beschreibung | Quelle | Berechnung |
|-----|--------------|--------|------------|
| **89** | Innergemeinschaftlicher Erwerb | Eingangsrechnungen (EU) | Summe Netto (0% von EU-Lieferant) |
| **93** | Umsatzsteuer aus ig. Erwerb | Auto-berechnet | Kz. 89 × 0,19 (Reverse Charge) |
| **61** | Vorsteuer aus ig. Erwerb | Auto-berechnet | = Kz. 93 (abzugsfähig) |

**Wichtig:** Kz. 93 und Kz. 61 gleichen sich aus (zahlen + abziehen) → Netto-Effekt: 0 €

#### **Vorsteuer (abzugsfähig):**

| Kz. | Beschreibung | Quelle | Berechnung |
|-----|--------------|--------|------------|
| **66** | Vorsteuer Inland | Eingangsrechnungen (DE) | Summe USt-Betrag (abzugsfähig) |
| **61** | Vorsteuer aus ig. Erwerb | Eingangsrechnungen (EU) | = Kz. 93 (siehe oben) |

#### **Zahllast/Erstattung:**

| Kz. | Beschreibung | Berechnung |
|-----|--------------|------------|
| **83** | Summe Umsatzsteuer | Kz. 83 + Kz. 88 + ... |
| **66** | Summe Vorsteuer | Kz. 66 + Kz. 61 |
| **Zahllast** | **Vorauszahlung (Soll)** | **Kz. 83 + Kz. 93 - Kz. 66 - Kz. 61** |

---

### **6.2.1 Innergemeinschaftlicher Handel (EU)** 🇪🇺

**Entscheidung:** Im MVP enthalten (wichtig für EU-Geschäft)

---

#### **Was ist innergemeinschaftlicher Handel?**

**Handel zwischen EU-Mitgliedsstaaten**, z.B.:
- Deutschland ↔ Belgien
- Deutschland ↔ Frankreich
- Deutschland ↔ Niederlande
- etc. (alle 27 EU-Länder)

**Besonderheit:** Reverse-Charge-Verfahren (§ 13b UStG, § 4 Nr. 1b UStG)

---

#### **Szenario 1: Einkauf aus EU-Land (Innergemeinschaftlicher Erwerb)**

**Beispiel: Du kaufst Ware aus Belgien (1.000 €)**

```
Belgischer Lieferant               Du (Deutschland)
───────────────────                ────────────────
Rechnung: 1.000 €
+ 0% MwSt (!)                      Du MUSST deutsche USt berechnen:
= 1.000 € Brutto
                                   Kz. 89: 1.000 € (Erwerb)
Lieferant berechnet 0%,            Kz. 93: 190 € (19% USt darauf)
weil du deutsche                   Kz. 61: 190 € (Vorsteuer abziehbar)
USt-IdNr. hast
                                   Netto-Effekt: 0 € (93 - 61 = 0)
```

**Voraussetzungen:**
1. ✅ Du hast gültige **deutsche USt-IdNr.** (DE123456789)
2. ✅ Lieferant hat gültige **belgische USt-IdNr.** (BE0123456789)
3. ✅ Ware wird physisch nach Deutschland geliefert
4. ❌ Du bist **nicht** Kleinunternehmer (§19 UStG)

**Grenzwert:**
- **Unter 12.500 € pro Jahr:** Optional (kannst auch belgische MwSt zahlen)
- **Über 12.500 € pro Jahr:** Pflicht zum Reverse Charge

**UStVA:**
- Kz. 89: 1.000 € (Bemessungsgrundlage)
- Kz. 93: 190 € (Steuer zahlen)
- Kz. 61: 190 € (Vorsteuer abziehen)
- Zahllast: +190 € - 190 € = **0 €** ✅

---

#### **Szenario 2: Verkauf in EU-Land (Innergemeinschaftliche Lieferung)**

**Fall A: B2B - Kunde ist Unternehmer (mit USt-IdNr.)**

**Beispiel: Du verkaufst an belgischen Kunden (1.000 €)**

```
Du (Deutschland)                   Belgischer Kunde (Unternehmer)
────────────────                   ─────────────────────────────
Rechnung: 1.000 €
+ 0% USt (!)                       Kunde MUSS belgische MwSt berechnen:
= 1.000 € Brutto                   → 1.000 € × 21% = 210 € (BE-MwSt)
                                   → Gleichzeitig 210 € Vorsteuer
Steuerfreie Lieferung
§ 4 Nr. 1b UStG                    Netto-Effekt beim Kunden: 0 €
```

**Voraussetzungen (KRITISCH!):**

1. ✅ **Kunde hat gültige belgische USt-IdNr.** (BE0123456789)
2. ✅ **USt-IdNr. validiert** über BZSt-Webservice
3. ✅ **Ware wird physisch nach Belgien geliefert**
4. ✅ **Gelangensbestätigung** vorhanden (Nachweis!)

**OHNE gültige USt-IdNr.:**
- ❌ Keine steuerfreie Lieferung!
- ✅ Deutsche USt berechnen (19%)

**UStVA:**
- Kz. 41: 1.000 € (innergemeinschaftliche Lieferung)
- Keine Umsatzsteuer (0%)

**Grenzwert:**
- ❌ **Kein Grenzwert** für B2B-Verkäufe
- Immer 0% bei gültiger USt-IdNr.

---

**Fall B: B2C - Kunde ist Privatperson (ohne USt-IdNr.)**

```
Du (Deutschland)                   Belgischer Privatkunde
────────────────                   ──────────────────────

Bis 10.000 € Jahresumsatz (EU):
→ Deutsche USt (19%)

Ab 10.000 € Jahresumsatz (EU):
→ Belgische MwSt (21%)             Du musst dich in Belgien
→ Registrierung in BE nötig!       registrieren!
```

**Grenzwerte (B2C):**
- **Unter 10.000 € EU-weit pro Jahr:** Deutsche USt
- **Über 10.000 € EU-weit:** Zielland-MwSt + Registrierung
- **Alternative:** OSS-Verfahren (One-Stop-Shop)

---

#### **Pflichten bei EU-Handel**

**1. USt-IdNr.-Validierung (PFLICHT vor jeder Lieferung!)**

```python
def validate_ust_idnr(ust_idnr, land):
    """
    Validiert USt-IdNr. über BZSt-Webservice

    API: https://evatr.bff-online.de/eVatR/xmlrpc/
    """
    # 1. Format prüfen
    if not re.match(r'^BE[0-9]{10}$', ust_idnr):
        return False, "Ungültiges Format"

    # 2. BZSt-API anfragen
    response = bzst_api.validate(
        ust_idnr=ust_idnr,
        eigene_ust_idnr='DE123456789',
        firmenname='Musterfirma',
        ort='Musterstadt'
    )

    # 3. Ergebnis speichern (Nachweispflicht!)
    save_validation_result(
        ust_idnr=ust_idnr,
        datum=heute(),
        ergebnis=response.gueltig,
        fehlercode=response.fehlercode
    )

    return response.gueltig, response.fehlercode
```

**UI-Workflow:**
```
Ausgangsrechnung erstellen
│
├─ Land: [Belgien ▼]
├─ Kunde: Belgischer Kunde GmbH
├─ USt-IdNr: [BE0123456789]  [ Validieren ]
│                             ↓
│                          ✅ Gültig! (BZSt bestätigt)
│                          → 0% USt wird berechnet
│
└─ Rechnung speichern
```

**WICHTIG:** Validation-Ergebnis **muss gespeichert** werden (Nachweispflicht bei Betriebsprüfung!)

---

**2. Gelangensbestätigung (Nachweis der Lieferung)**

**Was ist das?**
- Nachweis, dass Ware tatsächlich ins EU-Ausland geliefert wurde
- Ohne Nachweis: Finanzamt kann 0% USt ablehnen!

**Mögliche Nachweise:**
1. Spediteur-Bescheinigung (CMR-Frachtbrief)
2. Unterschriebener Lieferschein
3. Tracking-Nummer (DHL, UPS, FedEx)
4. Empfangsbestätigung des Kunden

**RechnungsPilot:**
```
Rechnung bearbeiten
│
├─ Status: Versendet
├─ Lieferdatum: 15.12.2025
├─ Nachweis: [📎 CMR-Frachtbrief.pdf]
│            [📎 Tracking-DHL-123456.pdf]
│
└─ Speichern
```

---

**3. Zusammenfassende Meldung (ZM)**

**Was ist das?**
- Meldung an BZSt (Bundeszentralamt für Steuern)
- Alle innergemeinschaftlichen Lieferungen
- **Pflicht** bei jeder ig. Lieferung!

**Fristen:**
- **Monatlich:** Bei > 50.000 € ig. Lieferungen pro Jahr
- **Quartalsweise:** Bei < 50.000 €
- **Frist:** 25. des Folgemonats

**Inhalt:**

```xml
<!-- ZM Januar 2026 -->
<ZM>
  <Meldezeitraum>2026-01</Meldezeitraum>
  <Lieferungen>
    <Lieferung>
      <Land>BE</Land>
      <UStIdNr>BE0123456789</UStIdNr>
      <Betrag>1000.00</Betrag>  <!-- Netto -->
    </Lieferung>
    <Lieferung>
      <Land>FR</Land>
      <UStIdNr>FR12345678901</UStIdNr>
      <Betrag>2500.00</Betrag>
    </Lieferung>
  </Lieferungen>
</ZM>
```

**RechnungsPilot-Export:**
```python
def export_zm(zeitraum):
    """
    Erstellt Zusammenfassende Meldung (XML)
    """
    lieferungen = get_ig_lieferungen(zeitraum)

    # Nach Land + USt-IdNr gruppieren
    grouped = group_by(lieferungen, ['land', 'ust_idnr'])

    xml = create_zm_xml(
        zeitraum=zeitraum,
        lieferungen=grouped
    )

    return xml  # Hochladen auf ELSTER-Portal
```

**UI:**
```
┌─────────────────────────────────────────┐
│ Zusammenfassende Meldung (ZM)          │
├─────────────────────────────────────────┤
│ Zeitraum: Januar 2026                  │
│                                         │
│ Belgien (BE):                           │
│ └─ BE0123456789: 1.000,00 €            │
│                                         │
│ Frankreich (FR):                        │
│ └─ FR12345678901: 2.500,00 €           │
│                                         │
│ Gesamt: 3.500,00 €                     │
│                                         │
│ [ XML exportieren ]  [ An BZSt ]       │
└─────────────────────────────────────────┘
```

---

#### **Datenbank-Erweiterungen**

```sql
-- Rechnungen (erweitert für EU)
CREATE TABLE rechnungen (
    id INTEGER PRIMARY KEY,
    typ TEXT,  -- 'eingangsrechnung', 'ausgangsrechnung'

    -- NEU: EU-Felder
    land TEXT DEFAULT 'DE',  -- ISO 3166-1 Alpha-2
    ist_eu_lieferung BOOLEAN DEFAULT 0,
    ist_eu_erwerb BOOLEAN DEFAULT 0,
    kunde_ust_idnr TEXT,  -- z.B. BE0123456789

    -- NEU: Validierung
    ust_idnr_validiert BOOLEAN DEFAULT 0,
    ust_idnr_validierung_datum DATE,
    ust_idnr_validierung_ergebnis TEXT,

    -- NEU: Gelangensbestätigung
    gelangensbestaetigung_vorhanden BOOLEAN DEFAULT 0,
    gelangensbestaetigung_datei TEXT,  -- Pfad zu PDF/Scan

    netto_betrag DECIMAL,
    umsatzsteuer_satz DECIMAL,
    umsatzsteuer_betrag DECIMAL,
    brutto_betrag DECIMAL
);

-- ZM-Meldungen
CREATE TABLE zm_meldungen (
    id INTEGER PRIMARY KEY,
    zeitraum TEXT NOT NULL,  -- '2026-01'
    erstellungsdatum TIMESTAMP,
    status TEXT,  -- 'entwurf', 'gesendet', 'bestätigt'
    xml_datei TEXT
);

-- EU-Länder-Stammdaten
CREATE TABLE eu_laender (
    code TEXT PRIMARY KEY,  -- 'BE'
    name TEXT,  -- 'Belgien'
    mwst_satz_standard DECIMAL,  -- 21.0
    mwst_satz_reduziert DECIMAL,  -- 6.0
    ust_idnr_format TEXT  -- '^BE[0-9]{10}$'
);
```

---

#### **Kleinunternehmer (§19 UStG) - Einschränkungen**

**Problem:** Kleinunternehmer haben **keine USt-IdNr.**

**Folgen:**

```
Einkauf aus EU:
❌ Kein Reverse Charge möglich
✅ Lieferant berechnet EU-MwSt (21% BE)
❌ Keine Vorsteuer abziehbar

Verkauf in EU:
❌ Kein 0% USt möglich (keine USt-IdNr.)
✅ Wie Inlandsverkauf (0% nach §19 UStG)
⚠️ Kunde muss ggf. Import-MwSt zahlen
```

**RechnungsPilot-Verhalten:**
- EU-Felder ausgegraut bei Kleinunternehmer
- Warnung: "Als Kleinunternehmer kein Reverse Charge möglich"

---

#### **MVP-Umfang EU-Handel**

**Was im MVP enthalten ist:**

✅ **Rechnungen:**
- Länder-Auswahl (27 EU-Länder)
- USt-IdNr.-Feld für Kunden/Lieferanten
- 0% USt bei ig. Lieferung/Erwerb
- Reverse-Charge-Vermerk auf Rechnung

✅ **USt-IdNr.-Validierung:**
- BZSt-API-Integration
- Validation-Ergebnis speichern
- UI-Feedback (gültig/ungültig)

✅ **UStVA:**
- Kz. 41: Innergemeinschaftliche Lieferungen
- Kz. 89: Innergemeinschaftlicher Erwerb
- Kz. 93: USt aus ig. Erwerb
- Kz. 61: Vorsteuer aus ig. Erwerb

✅ **ZM-Export:**
- XML-Generierung
- Nach Land/USt-IdNr gruppiert
- Export für ELSTER-Portal

✅ **Gelangensbestätigung:**
- Datei-Upload (PDF/Scan)
- Tracking-Nummer speichern

**Nicht im MVP (später):**
- ❌ OSS-Verfahren (B2C > 10.000 €)
- ❌ Automatische ELSTER-Übermittlung (ZM)
- ❌ Drittlands-Handel (Schweiz, UK, etc.)

---

#### **Validierung & Abhängigkeiten** ⚠️ **KRITISCH**

**Problem:** EU-Handel hat viele Voraussetzungen - ohne Validierung → Fehler bei Betriebsprüfung!

---

##### **Abhängigkeiten-Checkliste:**

**1. Voraussetzung: Eigene USt-IdNr. vorhanden**

```
Ohne eigene USt-IdNr.:
❌ Kein EU-Handel möglich
❌ Kein Reverse Charge
❌ Keine innergemeinschaftliche Lieferung

Konsequenz:
→ EU-Funktionen müssen gesperrt sein
→ Setup-Wizard muss abfragen
```

**Validierung:**
```python
def can_use_eu_trade():
    """
    Prüft, ob User EU-Handel nutzen kann
    """
    user = get_user_settings()

    # 1. Hat User eigene USt-IdNr.?
    if not user.ust_idnr:
        return False, "Keine USt-IdNr. hinterlegt"

    # 2. Format validieren (DE + 9 Ziffern)
    if not re.match(r'^DE[0-9]{9}$', user.ust_idnr):
        return False, "USt-IdNr. hat ungültiges Format"

    # 3. Kleinunternehmer?
    if user.ist_kleinunternehmer:
        return False, "Kleinunternehmer können keinen EU-Handel nutzen"

    # 4. USt-IdNr. bei BZSt bestätigt?
    if not user.ust_idnr_bestaetigt:
        return False, "USt-IdNr. noch nicht vom BZSt bestätigt"

    return True, "OK"
```

**UI-Verhalten:**
```
Wenn can_use_eu_trade() == False:
┌─────────────────────────────────────────┐
│ Ausgangsrechnung erstellen             │
├─────────────────────────────────────────┤
│ Kunde: [Max Mustermann ▼]             │
│ Land:  [Deutschland ▼]                 │
│        [Belgien] (ausgegraut)          │
│                                         │
│ ⚠️ EU-Länder nicht verfügbar            │
│    Grund: Keine USt-IdNr. hinterlegt   │
│    → Einstellungen > Stammdaten         │
└─────────────────────────────────────────┘
```

---

**2. Voraussetzung: Kunden-USt-IdNr. validiert**

```
Vor jeder ig. Lieferung MUSS geprüft werden:
✅ Kunde hat USt-IdNr. angegeben
✅ Format ist korrekt (z.B. BE0123456789)
✅ BZSt-Bestätigung liegt vor (validiert!)
✅ Nicht älter als 1 Jahr (Empfehlung)
```

**Validierung beim Rechnung-Erstellen:**
```python
def validate_eu_invoice(rechnung):
    """
    Prüft Rechnung vor dem Speichern
    """
    errors = []

    if rechnung.land != 'DE':
        # 1. USt-IdNr. vorhanden?
        if not rechnung.kunde_ust_idnr:
            errors.append(
                "Für EU-Lieferungen ist die USt-IdNr. des Kunden PFLICHT. "
                "Ohne gültige USt-IdNr. muss deutsche USt berechnet werden."
            )

        # 2. USt-IdNr. validiert?
        if rechnung.kunde_ust_idnr and not rechnung.ust_idnr_validiert:
            errors.append(
                "USt-IdNr. muss über BZSt validiert werden. "
                "Klicken Sie auf 'Validieren'."
            )

        # 3. Validation nicht älter als 1 Jahr?
        if rechnung.ust_idnr_validierung_datum:
            age = heute() - rechnung.ust_idnr_validierung_datum
            if age.days > 365:
                errors.append(
                    "USt-IdNr.-Validierung ist älter als 1 Jahr. "
                    "Bitte neu validieren."
                )

        # 4. Wenn 0% USt → Validierung PFLICHT
        if rechnung.umsatzsteuer_satz == 0 and not rechnung.ust_idnr_validiert:
            errors.append(
                "0% USt (steuerfreie ig. Lieferung) nur mit validierter USt-IdNr.!"
            )

    return errors
```

**UI-Blockierung:**
```
[ Rechnung speichern ]
        ↓
      FEHLER!

┌─────────────────────────────────────────┐
│ ❌ Rechnung kann nicht gespeichert      │
│    werden                               │
├─────────────────────────────────────────┤
│ • USt-IdNr. des Kunden fehlt            │
│ • USt-IdNr. nicht validiert             │
│                                         │
│ Bitte ergänzen Sie die USt-IdNr. und   │
│ validieren Sie diese über BZSt.        │
│                                         │
│ [ Stammdaten öffnen ]  [ Abbrechen ]   │
└─────────────────────────────────────────┘
```

---

**3. Voraussetzung: Gelangensbestätigung (empfohlen)**

```
Ohne Gelangensbestätigung:
⚠️ Finanzamt kann 0% USt ablehnen
⚠️ Nachzahlung + Zinsen möglich
```

**Validierung (Warnung, nicht Fehler):**
```python
def warn_missing_gelangensbestaetigung(rechnung):
    """
    Warnt bei fehlender Gelangensbestätigung
    """
    if rechnung.ist_eu_lieferung and not rechnung.gelangensbestaetigung_vorhanden:
        return Warning(
            "Gelangensbestätigung fehlt! "
            "Laden Sie einen Nachweis hoch (CMR, Tracking, Lieferschein). "
            "Ohne Nachweis kann das Finanzamt die steuerfreie Lieferung ablehnen."
        )
```

**UI-Warnung:**
```
[ Rechnung speichern ]
        ↓

┌─────────────────────────────────────────┐
│ ⚠️ Gelangensbestätigung fehlt            │
├─────────────────────────────────────────┤
│ Diese Rechnung ist eine innergemein-    │
│ schaftliche Lieferung (0% USt).         │
│                                         │
│ WICHTIG: Laden Sie einen Nachweis hoch, │
│ dass die Ware nach Belgien geliefert    │
│ wurde (CMR, DHL-Tracking, etc.).        │
│                                         │
│ Ohne Nachweis:                          │
│ → Finanzamt kann 0% USt ablehnen        │
│ → Nachzahlung 19% USt + Zinsen          │
│                                         │
│ [ Jetzt hochladen ]  [ Später ]         │
└─────────────────────────────────────────┘
```

---

##### **Integration im Setup-Wizard** 🧙

**Schritt 1: Grunddaten (erweitert)**

```
┌─────────────────────────────────────────┐
│ RechnungsPilot - Ersteinrichtung       │
│ Schritt 1/5: Grunddaten                │
├─────────────────────────────────────────┤
│                                         │
│ Firmenname:  [Musterfirma GmbH]        │
│ Straße:      [Musterstr. 1]            │
│ PLZ/Ort:     [12345] [Musterstadt]     │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Umsatzsteuer                        │ │
│ ├─────────────────────────────────────┤ │
│ │ ○ Kleinunternehmer (§19 UStG)       │ │
│ │   → Keine USt, kein EU-Handel       │ │
│ │                                     │ │
│ │ ● Regelbesteuert                    │ │
│ │   USt-IdNr: [DE123456789]          │ │
│ │   [ BZSt validieren ] ✅ Gültig     │ │
│ │                                     │ │
│ │   ☑ Ich plane EU-Handel             │ │
│ │     (innergemeinschaftliche         │ │
│ │      Lieferungen/Erwerbe)           │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ [ Zurück ]              [ Weiter ]     │
└─────────────────────────────────────────┘
```

**Logik:**
```python
def setup_wizard_step1_validate(data):
    if data.ist_kleinunternehmer:
        # Kleinunternehmer: EU-Handel deaktivieren
        data.eu_handel_aktiv = False
        return True

    if data.plant_eu_handel:
        # Regelbesteuert + EU-Handel:
        if not data.ust_idnr:
            return Error("Für EU-Handel ist USt-IdNr. Pflicht")

        if not validate_ust_idnr_format(data.ust_idnr):
            return Error("USt-IdNr. hat ungültiges Format (DE + 9 Ziffern)")

        # BZSt-Validierung durchführen
        result = bzst_validate(data.ust_idnr)
        if not result.gueltig:
            return Error(f"USt-IdNr. ungültig: {result.fehler}")

    return True
```

---

**Schritt 2: EU-Handel-Konfiguration (nur wenn aktiviert)**

```
┌─────────────────────────────────────────┐
│ RechnungsPilot - Ersteinrichtung       │
│ Schritt 2/5: EU-Handel                 │
├─────────────────────────────────────────┤
│                                         │
│ Sie haben EU-Handel aktiviert.         │
│ Bitte lesen Sie folgende Hinweise:     │
│                                         │
│ ✅ Voraussetzungen:                     │
│ • Gültige USt-IdNr. (DE123456789) ✅    │
│ • Regelbesteuerung (kein §19) ✅        │
│                                         │
│ ⚠️ Pflichten bei EU-Geschäften:         │
│ • Kunden-USt-IdNr. MUSS validiert sein │
│ • Gelangensbestätigung hochladen       │
│ • Zusammenfassende Meldung (ZM)        │
│   monatlich/quartalsweise an BZSt      │
│                                         │
│ 📋 In welchen Ländern handeln Sie?     │
│ (optional - nur zur Vorbereitung)      │
│                                         │
│ ☑ Belgien                               │
│ ☑ Niederlande                           │
│ ☐ Frankreich                            │
│ ☐ Österreich                            │
│ ☐ Weitere... [27 EU-Länder]            │
│                                         │
│ [ Zurück ]              [ Weiter ]     │
└─────────────────────────────────────────┘
```

---

##### **Integration in Stammdaten (Kategorie 8)** 📋

**Kunden-Stammdaten (erweitert):**

```
Kunde bearbeiten: Belgischer Kunde GmbH
┌─────────────────────────────────────────┐
│ Grunddaten                              │
├─────────────────────────────────────────┤
│ Firmenname: [Belgischer Kunde GmbH]    │
│ Straße:     [Rue de Example 123]       │
│ PLZ/Ort:    [1000] [Brüssel]           │
│                                         │
│ Land:       [Belgien ▼]  🇧🇪             │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Umsatzsteuer-ID (EU)                │ │
│ ├─────────────────────────────────────┤ │
│ │ USt-IdNr: [BE0123456789]            │ │
│ │           [ Validieren ]            │ │
│ │                                     │ │
│ │ Status: ✅ Gültig                    │ │
│ │ Validiert: 05.12.2025 (vor 2 Tagen)│ │
│ │ BZSt-Ergebnis: A (qualifiziert)    │ │
│ │                                     │ │
│ │ ⚠️ Wichtig:                          │ │
│ │ Ohne validierte USt-IdNr. wird      │ │
│ │ deutsche USt (19%) berechnet!       │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ [ Speichern ]  [ Abbrechen ]           │
└─────────────────────────────────────────┘
```

**Validierung beim Speichern:**
```python
def validate_kunde(kunde):
    errors = []

    if kunde.land != 'DE':
        # EU-Land: Prüfen ob USt-IdNr. nötig
        if not kunde.ust_idnr:
            errors.append({
                'feld': 'ust_idnr',
                'typ': 'warning',
                'nachricht':
                    'Für EU-Kunden empfehlen wir die Angabe der USt-IdNr. '
                    'Ohne USt-IdNr. wird deutsche USt (19%) berechnet.'
            })
        elif not kunde.ust_idnr_validiert:
            errors.append({
                'feld': 'ust_idnr',
                'typ': 'error',
                'nachricht':
                    'USt-IdNr. muss validiert werden (BZSt-Abfrage). '
                    'Klicken Sie auf "Validieren".'
            })

    return errors
```

---

##### **Validierungs-Matrix**

**Übersicht: Was muss wann geprüft werden?**

| Zeitpunkt | Prüfung | Fehler-Typ | Aktion |
|-----------|---------|------------|--------|
| **Setup-Wizard** | Eigene USt-IdNr. vorhanden | ❌ Fehler | Weiter blockiert |
| **Setup-Wizard** | USt-IdNr. Format korrekt | ❌ Fehler | Korrektur nötig |
| **Setup-Wizard** | BZSt-Validierung erfolgreich | ❌ Fehler | Eingabe prüfen |
| **Kunde speichern** | Kunden-USt-IdNr. vorhanden | ⚠️ Warnung | Weiter möglich |
| **Kunde speichern** | Kunden-USt-IdNr. validiert | ❌ Fehler | Validierung nötig |
| **Rechnung erstellen** | Kunde hat validierte USt-IdNr. | ❌ Fehler | Stammdaten öffnen |
| **Rechnung erstellen** | Gelangensbestätigung vorhanden | ⚠️ Warnung | Später hochladen |
| **Rechnung speichern** | 0% USt nur mit USt-IdNr. | ❌ Fehler | Speichern blockiert |
| **UStVA erstellen** | Kz. 41: Alle Rechnungen validiert | ⚠️ Warnung | Prüfung empfohlen |
| **ZM erstellen** | Alle Lieferungen haben USt-IdNr. | ❌ Fehler | Export blockiert |

---

##### **Fehlerbehandlung & User-Guidance**

**Szenario 1: User will EU-Rechnung erstellen, aber keine eigene USt-IdNr.**

```
User: Rechnung erstellen > Land: Belgien
       ↓
System: STOP!

┌─────────────────────────────────────────┐
│ ⚠️ EU-Handel nicht möglich               │
├─────────────────────────────────────────┤
│ Für Geschäfte mit EU-Ländern benötigen │
│ Sie eine gültige deutsche USt-IdNr.    │
│                                         │
│ Sie sind aktuell als Kleinunternehmer  │
│ (§19 UStG) registriert.                │
│                                         │
│ Optionen:                               │
│ • Beim Finanzamt USt-IdNr. beantragen   │
│ • Auf Regelbesteuerung umstellen        │
│                                         │
│ [ Stammdaten ändern ]  [ Abbrechen ]   │
└─────────────────────────────────────────┘
```

**Szenario 2: Kunde ohne USt-IdNr., User will 0% USt**

```
User: USt-Satz: 0% (ig. Lieferung)
       ↓
System: STOP!

┌─────────────────────────────────────────┐
│ ❌ 0% USt nicht möglich                  │
├─────────────────────────────────────────┤
│ Für steuerfreie innergemeinschaftliche │
│ Lieferungen (0% USt) ist eine validierte│
│ USt-IdNr. des Kunden PFLICHT.          │
│                                         │
│ Kunde: Belgischer Kunde GmbH           │
│ USt-IdNr: [fehlt]                      │
│                                         │
│ Optionen:                               │
│ 1. USt-IdNr. erfragen und validieren    │
│ 2. Deutsche USt (19%) berechnen         │
│                                         │
│ [ Stammdaten öffnen ]                  │
│ [ 19% USt verwenden ]  [ Abbrechen ]   │
└─────────────────────────────────────────┘
```

---

##### **Dokumentation für User** 📖

**Hilfe-Seite: "EU-Handel - Checkliste"**

```markdown
# EU-Handel: Was Sie benötigen

## ✅ Voraussetzungen

1. **Eigene USt-IdNr.**
   - Beim Finanzamt beantragen
   - Format: DE + 9 Ziffern (z.B. DE123456789)
   - In RechnungsPilot: Einstellungen > Stammdaten

2. **Regelbesteuerung**
   - Kleinunternehmer (§19 UStG) können keinen EU-Handel nutzen
   - Umstellung beim Finanzamt beantragen

3. **Kunden-USt-IdNr.**
   - Für jeden EU-Kunden erforderlich
   - MUSS über BZSt validiert werden
   - In RechnungsPilot: Kunde bearbeiten > "Validieren"

4. **Gelangensbestätigung**
   - Nachweis, dass Ware ins EU-Ausland geliefert wurde
   - CMR-Frachtbrief, DHL-Tracking, Lieferschein
   - In RechnungsPilot: Rechnung > "Nachweis hochladen"

## ⚠️ Häufige Fehler

❌ "USt-IdNr. nicht validiert"
→ Lösung: Kunde öffnen > USt-IdNr. eingeben > "Validieren" klicken

❌ "0% USt nicht möglich"
→ Lösung: Kunde muss gültige USt-IdNr. haben

❌ "Gelangensbestätigung fehlt"
→ Lösung: CMR/Tracking hochladen (empfohlen, nicht Pflicht)

## 📋 Monatliche Aufgaben

- Zusammenfassende Meldung (ZM) an BZSt senden
- RechnungsPilot: Berichte > ZM erstellen > XML exportieren
```

---

##### **⚠️ KRITISCHE KORREKTUR: Export-Zeit-Validierung**

**Problem mit obigem Konzept:**

```
RechnungsPilot MVP hat KEINEN Kundenstamm!
────────────────────────────────────────────

User erstellt Rechnungen:
• LibreOffice-Vorlagen
• HTML-Vorlagen
• PDF/XRechnung-Import

→ KEINE Eingabemasken in RechnungsPilot
→ KEINE Validierung bei Erfassung möglich
→ User könnte fehlerhafte Rechnungen erstellen
```

**Konsequenz:**
- Stammdaten-Validierung (oben) gilt erst für **Version 2.0** (mit Rechnungseditor)
- Setup-Wizard-Validierung bleibt (eigene USt-IdNr. MUSS vorhanden sein)
- **Alle anderen Validierungen müssen beim EXPORT erfolgen!**

---

##### **Export-Zeit-Validierung (MVP-Ansatz)** ✅

**Wann wird validiert?**

1. **Vor UStVA-Erstellung**
2. **Vor ZM-Erstellung**
3. **Vor DATEV-Export**

**Was passiert bei Fehlern?**
- Export wird NICHT blockiert
- Aber: **Validierungs-Report** mit Warnungen
- User muss Fehler bestätigen oder korrigieren

---

**1. UStVA-Validierung**

```python
def validate_ustva_before_export(zeitraum):
    """
    Prüft alle Rechnungen VOR UStVA-Export
    """
    warnings = []
    errors = []

    # Alle Rechnungen mit 0% USt (ig. Lieferung)
    eu_lieferungen = get_ausgangsrechnungen(
        zeitraum=zeitraum,
        umsatzsteuer_satz=0,
        land_not='DE'
    )

    for rechnung in eu_lieferungen:
        # 1. Land ist EU-Mitglied?
        if rechnung.land not in EU_LAENDER:
            errors.append({
                'rechnung': rechnung.nummer,
                'fehler': f"Land '{rechnung.land}' ist kein EU-Mitglied",
                'loesung': "0% USt nur für EU-Länder zulässig. Bitte prüfen."
            })

        # 2. Kunden-USt-IdNr. vorhanden?
        if not rechnung.kunde_ust_idnr:
            warnings.append({
                'rechnung': rechnung.nummer,
                'warnung': "Keine Kunden-USt-IdNr. auf Rechnung",
                'risiko': "Finanzamt könnte 0% USt ablehnen → 19% nachzahlen",
                'loesung': "Rechnung nachträglich korrigieren und USt-IdNr. ergänzen"
            })

        # 3. USt-IdNr.-Format plausibel?
        if rechnung.kunde_ust_idnr:
            if not validate_ust_idnr_format(rechnung.kunde_ust_idnr, rechnung.land):
                warnings.append({
                    'rechnung': rechnung.nummer,
                    'warnung': f"USt-IdNr. '{rechnung.kunde_ust_idnr}' hat ungültiges Format",
                    'format': get_expected_format(rechnung.land),
                    'loesung': "Bitte prüfen und ggf. BZSt-Validierung durchführen"
                })

        # 4. BZSt-Validierung vorhanden?
        if rechnung.kunde_ust_idnr and not rechnung.ust_idnr_validiert:
            warnings.append({
                'rechnung': rechnung.nummer,
                'warnung': "USt-IdNr. nicht über BZSt validiert",
                'risiko': "Bei Betriebsprüfung: Nachweis der Validierung erforderlich",
                'loesung': "Jetzt validieren: [USt-IdNr. prüfen]"
            })

    # Zusammenfassung
    return {
        'errors': errors,  # Kritische Fehler
        'warnings': warnings,  # Warnungen
        'kann_exportieren': len(errors) == 0
    }
```

**UI vor UStVA-Export:**

```
[ UStVA Dezember 2025 erstellen ]
        ↓
    Validierung läuft...
        ↓

┌─────────────────────────────────────────────┐
│ ⚠️ UStVA-Validierung: 5 Warnungen gefunden  │
├─────────────────────────────────────────────┤
│                                             │
│ Rechnung RE-2025-123:                       │
│ └─ ⚠️ Keine Kunden-USt-IdNr.                │
│    Risiko: Finanzamt könnte 0% USt ablehnen│
│    → Nachzahlung 19% + Zinsen              │
│    [ Rechnung korrigieren ]                │
│                                             │
│ Rechnung RE-2025-145:                       │
│ └─ ⚠️ USt-IdNr. nicht validiert             │
│    BE0123456789 (nicht geprüft)            │
│    [ Jetzt validieren ]                    │
│                                             │
│ Rechnung RE-2025-167:                       │
│ └─ ⚠️ Format ungültig                       │
│    "BE012345" (zu kurz, erwartet: 10 Ziff.)│
│    [ Rechnung korrigieren ]                │
│                                             │
│ ───────────────────────────────────────────│
│                                             │
│ ✅ Kritische Fehler: 0                      │
│ ⚠️ Warnungen: 5                             │
│                                             │
│ UStVA kann erstellt werden, aber Warnungen │
│ sollten vor Übermittlung ans Finanzamt     │
│ behoben werden.                            │
│                                             │
│ [ Warnungen ignorieren & fortfahren ]      │
│ [ Alle Rechnungen prüfen ]                 │
│ [ Abbrechen ]                              │
└─────────────────────────────────────────────┘
```

---

**2. ZM-Validierung**

```python
def validate_zm_before_export(zeitraum):
    """
    Prüft Zusammenfassende Meldung VOR Export
    """
    errors = []
    warnings = []

    # Alle innergemeinschaftlichen Lieferungen
    ig_lieferungen = get_ig_lieferungen(zeitraum)

    for lieferung in ig_lieferungen:
        # 1. USt-IdNr. MUSS vorhanden sein (ZM-Pflicht!)
        if not lieferung.kunde_ust_idnr:
            errors.append({
                'rechnung': lieferung.nummer,
                'fehler': "Keine USt-IdNr. - ZM-Export nicht möglich",
                'pflicht': "Für ZM ist USt-IdNr. PFLICHT (§18a UStG)",
                'loesung': "Rechnung korrigieren und USt-IdNr. ergänzen"
            })

        # 2. Format-Validierung
        if lieferung.kunde_ust_idnr:
            if not validate_ust_idnr_format(lieferung.kunde_ust_idnr, lieferung.land):
                errors.append({
                    'rechnung': lieferung.nummer,
                    'fehler': f"USt-IdNr. '{lieferung.kunde_ust_idnr}' ungültig",
                    'loesung': "Format prüfen und korrigieren"
                })

        # 3. BZSt-Validierung empfohlen
        if lieferung.kunde_ust_idnr and not lieferung.ust_idnr_validiert:
            warnings.append({
                'rechnung': lieferung.nummer,
                'warnung': "USt-IdNr. nicht validiert",
                'empfehlung': "Vor ZM-Übermittlung validieren"
            })

    return {
        'errors': errors,
        'warnings': warnings,
        'kann_exportieren': len(errors) == 0
    }
```

**UI vor ZM-Export:**

```
[ ZM Januar 2026 erstellen ]
        ↓

┌─────────────────────────────────────────────┐
│ ❌ ZM-Export nicht möglich                   │
├─────────────────────────────────────────────┤
│ 2 kritische Fehler gefunden:                │
│                                             │
│ Rechnung RE-2025-234:                       │
│ └─ ❌ Keine USt-IdNr. vorhanden              │
│    Ohne USt-IdNr. kann diese Lieferung     │
│    nicht in der ZM gemeldet werden.        │
│    → Rechnung aus ZM ausschließen?         │
│    [ Rechnung korrigieren ]                │
│    [ Aus ZM ausschließen ]                 │
│                                             │
│ Rechnung RE-2025-256:                       │
│ └─ ❌ USt-IdNr. ungültig: "BE012"           │
│    Format: BE + 10 Ziffern erwartet        │
│    [ Rechnung korrigieren ]                │
│                                             │
│ ───────────────────────────────────────────│
│                                             │
│ Export BLOCKIERT bis Fehler behoben sind.  │
│                                             │
│ [ Alle Fehler prüfen ]  [ Abbrechen ]      │
└─────────────────────────────────────────────┘
```

---

**3. DATEV-Export-Validierung**

```python
def validate_datev_export(zeitraum):
    """
    Prüft DATEV-Export auf Plausibilität
    """
    warnings = []

    buchungen = get_all_buchungen(zeitraum)

    for buchung in buchungen:
        # 1. Konto 8400 (ig. Lieferung) ohne USt-IdNr.?
        if buchung.konto_skr03 == '8400':  # ig. Lieferung
            if not buchung.kunde_ust_idnr:
                warnings.append({
                    'buchung': buchung.id,
                    'warnung': "Konto 8400 (ig. Lieferung) ohne USt-IdNr.",
                    'risiko': "DATEV-Berater könnte nachfragen",
                    'empfehlung': "Rechnung ergänzen oder Konto korrigieren"
                })

        # 2. 0% USt ohne Begründung?
        if buchung.umsatzsteuer_betrag == 0 and buchung.netto_betrag > 0:
            if not buchung.steuerbefreiung_grund:  # z.B. "§4 Nr. 1b UStG"
                warnings.append({
                    'buchung': buchung.id,
                    'warnung': "0% USt ohne Begründung",
                    'empfehlung': "Steuerbefreiungsgrund angeben"
                })

    return warnings
```

---

##### **Workflow: Nachträgliche Korrektur**

**Szenario: User findet Fehler nach UStVA-Validierung**

```
1. UStVA-Validierung zeigt Warnung
   "Rechnung RE-2025-123: Keine USt-IdNr."

2. User öffnet Rechnung
   → Datei: rechnung-2025-123.xml (XRechnung)
   → Oder: rechnung-2025-123.pdf + metadata.json

3. Zwei Optionen:

   Option A: In RechnungsPilot korrigieren
   ┌────────────────────────────────────┐
   │ Rechnung RE-2025-123 bearbeiten   │
   ├────────────────────────────────────┤
   │ Kunde: Belgischer Kunde GmbH      │
   │ Betrag: 1.000,00 € (Netto)        │
   │ USt: 0% (ig. Lieferung)           │
   │                                    │
   │ ⚠️ USt-IdNr. fehlt!                 │
   │                                    │
   │ Nachträglich ergänzen:             │
   │ USt-IdNr: [BE0123456789]          │
   │           [ Validieren ]           │
   │                                    │
   │ [ Speichern ]                      │
   └────────────────────────────────────┘

   Option B: Original-Rechnung neu erstellen
   → LibreOffice/HTML-Vorlage anpassen
   → Neu hochladen/importieren
   → Alte Version ersetzen

4. Nach Korrektur: UStVA neu erstellen
   → Validierung erneut durchlaufen
   → Diesmal ohne Warnung ✅
```

---

##### **Validierungs-Report (Export-Zusammenfassung)**

**Vor jedem Export: Übersicht aller Probleme**

```
┌───────────────────────────────────────────────────┐
│ Validierungs-Report: Dezember 2025               │
├───────────────────────────────────────────────────┤
│                                                   │
│ ✅ Geprüfte Rechnungen: 47                        │
│ ✅ Ohne Probleme: 42                              │
│ ⚠️ Mit Warnungen: 5                               │
│ ❌ Mit Fehlern: 0                                 │
│                                                   │
│ ───────────────────────────────────────────────── │
│                                                   │
│ Warnungen (sollten behoben werden):              │
│                                                   │
│ 1. RE-2025-123 (Belgien, 1.000 €)                │
│    └─ ⚠️ Keine USt-IdNr.                          │
│       [ Korrigieren ] [ Details ]                │
│                                                   │
│ 2. RE-2025-145 (Frankreich, 2.500 €)             │
│    └─ ⚠️ USt-IdNr. nicht validiert                │
│       [ Validieren ] [ Details ]                 │
│                                                   │
│ 3. RE-2025-167 (Niederlande, 800 €)              │
│    └─ ⚠️ Gelangensbestätigung fehlt               │
│       [ Hochladen ] [ Details ]                  │
│                                                   │
│ 4. RE-2025-189 (Österreich, 450 €)               │
│    └─ ⚠️ USt-IdNr.-Format unklar                  │
│       [ Prüfen ] [ Details ]                     │
│                                                   │
│ 5. RE-2025-201 (Italien, 1.200 €)                │
│    └─ ⚠️ Validierung älter als 1 Jahr             │
│       [ Neu validieren ] [ Details ]             │
│                                                   │
│ ───────────────────────────────────────────────── │
│                                                   │
│ Empfehlung:                                      │
│ Beheben Sie die Warnungen vor UStVA-Abgabe,     │
│ um Probleme bei Betriebsprüfung zu vermeiden.   │
│                                                   │
│ [ Alle korrigieren ]  [ Report drucken ]         │
│ [ Warnungen ignorieren & exportieren ]           │
└───────────────────────────────────────────────────┘
```

---

##### **Unterschied: Fehler vs. Warnung**

| | Fehler ❌ | Warnung ⚠️ |
|---|---|---|
| **Export** | Blockiert | Möglich |
| **Risiko** | Hoch (rechtlich falsch) | Mittel (Betriebsprüfung) |
| **Beispiel** | ZM ohne USt-IdNr. | UStVA mit unvalidierter USt-IdNr. |
| **User-Aktion** | MUSS behoben werden | SOLLTE behoben werden |
| **UI** | Export-Button gesperrt | Export mit Bestätigung |

---

**Status:** ✅ Export-Zeit-Validierung definiert - UStVA, ZM, DATEV mit Validierungs-Report und nachträglicher Korrektur

**Status (alt):** ~~Stammdaten-Validierung~~ → Verschoben auf Version 2.0 (mit Rechnungseditor)

---

### **6.3 Implementierung (MVP)**

**Datenquellen:**

```python
def calculate_ustva(zeitraum):
    """
    Berechnet UStVA-Kennziffern aus Buchungen

    Zeitraum: 'monat' oder 'quartal'
    """
    # 1. Ausgangsrechnungen (Umsätze)
    ausgangsrechnungen = get_ausgangsrechnungen(
        zeitraum=zeitraum,
        status='bezahlt'  # Nur bezahlte (Ist-Versteuerung)
    )

    kz_81 = sum(
        r.netto_betrag for r in ausgangsrechnungen
        if r.umsatzsteuer_satz == 19.0
    )
    kz_83 = kz_81 * 0.19

    kz_86 = sum(
        r.netto_betrag for r in ausgangsrechnungen
        if r.umsatzsteuer_satz == 7.0
    )
    kz_88 = kz_86 * 0.07

    # 2. Eingangsrechnungen (Vorsteuer)
    eingangsrechnungen = get_eingangsrechnungen(
        zeitraum=zeitraum,
        vorsteuer_abzugsfaehig=True
    )

    kz_66 = sum(r.umsatzsteuer_betrag for r in eingangsrechnungen)

    # 3. Kassenbuch-Einnahmen (falls Bar)
    kassenbuch_einnahmen = get_kassenbuch(
        zeitraum=zeitraum,
        art='einnahme'
    )

    kz_81 += sum(
        k.netto_betrag for k in kassenbuch_einnahmen
        if k.ust_satz == 19.0
    )
    # ... analog für 7%

    # 4. Zahllast berechnen
    umsatzsteuer_gesamt = kz_83 + kz_88
    vorsteuer_gesamt = kz_66
    zahllast = umsatzsteuer_gesamt - vorsteuer_gesamt

    return {
        'kz_81': kz_81,
        'kz_83': kz_83,
        'kz_86': kz_86,
        'kz_88': kz_88,
        'kz_66': kz_66,
        'zahllast': zahllast,
        'zeitraum': zeitraum
    }
```

**PDF-Export:**

```python
def export_ustva_pdf(ustva_data):
    """
    Erstellt PDF-Übersicht der UStVA

    Zum Ausdrucken/Dokumentieren
    """
    pdf = create_pdf('UStVA_' + ustva_data['zeitraum'] + '.pdf')

    pdf.add_header("Umsatzsteuer-Voranmeldung")
    pdf.add_text(f"Zeitraum: {ustva_data['zeitraum']}")

    pdf.add_table([
        ['Kz. 81', 'Umsätze 19%', format_currency(ustva_data['kz_81'])],
        ['Kz. 83', 'USt 19%', format_currency(ustva_data['kz_83'])],
        ['Kz. 86', 'Umsätze 7%', format_currency(ustva_data['kz_86'])],
        ['Kz. 88', 'USt 7%', format_currency(ustva_data['kz_88'])],
        ['Kz. 66', 'Vorsteuer', format_currency(ustva_data['kz_66'])],
        ['', 'Zahllast', format_currency(ustva_data['zahllast'])],
    ])

    return pdf
```

---

### **6.4 Kleinunternehmer (§19 UStG)**

**Besonderheit:** Keine UStVA erforderlich!

**Verhalten:**
- RechnungsPilot erkennt: User ist Kleinunternehmer
- UStVA-Menü wird ausgeblendet/deaktiviert
- Hinweis: "Als Kleinunternehmer (§19 UStG) müssen Sie keine UStVA abgeben"

**Optional:**
- Umsatzgrenze-Tracker:
  - Warnung bei 22.000 € Jahresumsatz
  - "Achtung: Nächstes Jahr keine Kleinunternehmerregelung mehr!"

---

### **6.5 Soll- vs. Ist-Versteuerung**

**Unterschied:**

| | Soll-Versteuerung | Ist-Versteuerung |
|---|---|---|
| **Wann USt fällig?** | Bei Rechnungsstellung | Bei Zahlungseingang |
| **Für wen?** | Alle (Standardfall) | Freiberufler, kleine Unternehmen |
| **RechnungsPilot** | Alle Ausgangsrechnungen | Nur bezahlte Rechnungen |

---

#### **⚠️ WICHTIG: Ist-Versteuerung PFLICHT bei Transferleistungen**

**Grund: SGBII-Konformität**

Wenn der User **Transferleistungen** bezieht (ALG II / Bürgergeld), ist **Ist-Versteuerung zwingend erforderlich**!

**Warum?**
- **SGBII § 11:** "Einnahmen = Zufluss" (nur tatsächlich erhaltenes Geld)
- **Soll-Versteuerung** würde Rechnungsdatum zählen → Einnahme "zu früh" gemeldet
- **Ist-Versteuerung** zählt Zahlungseingang → Passt zu SGBII-Definition

**Beispiel:**

```
Szenario:
- Rechnung gestellt: 15.12.2025 (1.000 €)
- Zahlung erhalten: 10.01.2026 (1.000 €)

Soll-Versteuerung (FALSCH bei ALG II):
→ Einnahme in Dezember 2025 (Rechnungsdatum)
→ SGBII rechnet 1.000 € im Dezember an
→ Aber: Kein Geld auf dem Konto!
→ Kürzung der Leistung obwohl kein Geld da ist ❌

Ist-Versteuerung (RICHTIG bei ALG II):
→ Einnahme in Januar 2026 (Zahlungseingang)
→ SGBII rechnet 1.000 € im Januar an
→ Geld ist tatsächlich auf dem Konto
→ Korrekte Anrechnung ✅
```

**RechnungsPilot-Verhalten:**

1. **Beim Ersteinrichtung:**
   ```
   Beziehen Sie Transferleistungen?
   (ALG II, Bürgergeld, Grundsicherung)

   ○ Nein
   ● Ja  ← User wählt "Ja"

   → Automatisch: Ist-Versteuerung wird gesetzt
   → Soll-Versteuerung wird deaktiviert/ausgegraut
   ```

2. **In Einstellungen:**
   ```
   Einstellungen > Steuern
   ┌──────────────────────────────────┐
   │ Versteuerungsart:                │
   │ ○ Soll-Versteuerung (gesperrt)  │
   │ ● Ist-Versteuerung               │
   │                                  │
   │ ⚠️ Ist-Versteuerung ist Pflicht  │
   │    bei Bezug von                 │
   │    Transferleistungen (SGBII)    │
   └──────────────────────────────────┘
   ```

3. **EKS-Export:**
   - EKS nutzt automatisch Ist-Versteuerung
   - Alle Einnahmen/Ausgaben nach Zufluss-Datum
   - Konsistent mit UStVA

**Zusammenhang mit EKS (Kategorie 3):**
- EKS = Einkommensnachweis fürs Jobcenter
- Verwendet "Zufluss-Prinzip" (= Ist-Versteuerung)
- UStVA muss dasselbe Prinzip verwenden!
- Sonst: Widersprüchliche Zahlen zwischen EKS und Steuererklärung

---

#### **Implementierung:**

```python
def get_versteuerungsart():
    """
    Ermittelt die Versteuerungsart unter Berücksichtigung von Transferleistungen
    """
    user_settings = get_user_settings()

    # ZWANG: Transferleistungen → Ist-Versteuerung
    if user_settings.bezieht_transferleistungen:
        return 'ist'  # Keine Wahl!

    # Sonst: User-Einstellung
    return user_settings.versteuerungsart  # 'ist' oder 'soll'


def get_ausgangsrechnungen_fuer_ustva(zeitraum):
    """
    Holt Ausgangsrechnungen je nach Versteuerungsart
    """
    versteuerungsart = get_versteuerungsart()

    if versteuerungsart == 'ist':
        # Ist-Versteuerung: Nur bezahlte Rechnungen
        # WICHTIG bei Transferleistungen (SGBII § 11: Zufluss-Prinzip)
        return get_ausgangsrechnungen(
            zeitraum=zeitraum,
            bezahlt=True,
            zahlungsdatum_in_zeitraum=True  # Nach Zahlungseingang!
        )
    else:
        # Soll-Versteuerung: Alle Rechnungen
        return get_ausgangsrechnungen(
            zeitraum=zeitraum,
            rechnungsdatum_in_zeitraum=True  # Nach Rechnungsdatum
        )


def validate_settings_change(field, new_value):
    """
    Verhindert ungültige Einstellungen
    """
    if field == 'versteuerungsart' and new_value == 'soll':
        user = get_user_settings()

        if user.bezieht_transferleistungen:
            raise ValidationError(
                "Soll-Versteuerung nicht möglich bei Bezug von Transferleistungen. "
                "SGBII § 11 erfordert Ist-Versteuerung (Zufluss-Prinzip)."
            )
```

**User-Einstellung (normal):**
```
Einstellungen > Steuern
┌────────────────────────────┐
│ Versteuerungsart:          │
│ ○ Soll-Versteuerung        │
│ ● Ist-Versteuerung         │
└────────────────────────────┘
```

**User-Einstellung (bei Transferleistungen):**
```
Einstellungen > Steuern
┌──────────────────────────────────────┐
│ Versteuerungsart:                    │
│ ○ Soll-Versteuerung (nicht möglich) │
│ ● Ist-Versteuerung (Pflicht)        │
│                                      │
│ ⚠️ Bei Bezug von Transferleistungen  │
│    ist Ist-Versteuerung              │
│    gesetzlich vorgeschrieben         │
│    (SGBII § 11 Zufluss-Prinzip)      │
└──────────────────────────────────────┘
```

---

**Status:** ✅ Kategorie 6.1-6.5 definiert - Hybrid-Ansatz (MVP: Zahlen vorbereiten, v2.0: ELSTER-Integration), Berechnung, Kleinunternehmer, Ist/Soll-Versteuerung, SGBII-Konformität (Ist-Versteuerung Pflicht bei Transferleistungen).

---

## **🔍 Export-Anforderungen für Steuerberater-Software**

### **AGENDA - Export-Kompatibilität**

**Was AGENDA importieren kann (= was RechnungsPilot exportieren muss):**

1. **DATEV-Format**
   - AGENDA kann DATEV-Daten importieren
   - ✅ RechnungsPilot hat bereits DATEV-Export (Kategorie 2)

2. **Belegbilder-Export (PDF + XML)**
   - **AGENDA-Anforderung:** PDF und XML müssen denselben Dateinamen haben
   - **Format:** `rechnung-123.pdf` + `rechnung-123.xml`
   - **Bulk-Export:** Gezippte Belegbilder
   - **Workflow:** RechnungsPilot erstellt ZIP → AGENDA importiert → Matcht PDF+XML automatisch

**RechnungsPilot-Export für AGENDA:**

```python
def export_belege_fuer_agenda(zeitraum):
    """
    Exportiert alle Belege im AGENDA-kompatiblen Format

    Output:
    belege_2025-Q4.zip
    ├── rechnung-001.pdf  (Beleg-Scan/PDF)
    ├── rechnung-001.xml  (XRechnung-Daten)
    ├── rechnung-002.pdf
    ├── rechnung-002.xml
    └── ...
    """
    rechnungen = get_rechnungen(zeitraum)
    zip_file = create_zip(f"belege_{zeitraum}.zip")

    for rechnung in rechnungen:
        filename_base = f"rechnung-{rechnung.id:03d}"

        # 1. PDF-Beleg
        pdf_path = f"{filename_base}.pdf"
        zip_file.add(rechnung.beleg_pdf, pdf_path)

        # 2. XML-Daten (XRechnung/ZUGFeRD)
        xml_data = generate_xrechnung(rechnung)
        xml_path = f"{filename_base}.xml"
        zip_file.add_text(xml_data, xml_path)

    return zip_file


def export_to_agenda(zeitraum):
    """
    Vollständiger AGENDA-Export
    """
    # 1. DATEV-CSV (Buchungsdaten)
    datev_csv = export_datev(zeitraum)

    # 2. Belegbilder (ZIP mit PDF+XML)
    belege_zip = export_belege_fuer_agenda(zeitraum)

    return {
        'datev': datev_csv,
        'belege': belege_zip
    }
```

**Export-UI:**

```
┌─────────────────────────────────────────┐
│ Export für Steuerberater (AGENDA)      │
├─────────────────────────────────────────┤
│                                         │
│  Zeitraum: [Q4 2025 ▼]                 │
│                                         │
│  ☑ DATEV-Buchungsdaten (CSV)           │
│  ☑ Belegbilder (ZIP mit PDF+XML)       │
│                                         │
│  Dateinamen-Format:                     │
│  ● rechnung-NNN.pdf + .xml              │
│  ○ Rechnungsnummer als Dateiname       │
│                                         │
│  [ Exportieren ]                        │
│                                         │
│  → belege_2025-Q4.zip (12,4 MB)        │
│  → datev_2025-Q4.csv (124 KB)          │
└─────────────────────────────────────────┘
```

**Anforderungen:**
- ✅ **Gleicher Dateiname:** PDF und XML müssen identisch heißen (außer Endung)
- ✅ **ZIP-Format:** Für Massen-Export aller Belege
- ✅ **XRechnung/ZUGFeRD:** XML muss valide sein
- ✅ **DATEV-CSV:** Buchungsdaten parallel exportieren

**Status:** 📋 Für AGENDA-Export-Funktion vorgemerkt (Erweiterung von Kategorie 2: DATEV-Export)

---

## **Kategorie 7: Einnahmen-Überschuss-Rechnung (EÜR)**

### **7.1 Was ist die EÜR?**

Die **Einnahmen-Überschuss-Rechnung (EÜR)** ist eine vereinfachte Form der Gewinnermittlung:

**Grundformel:**
```
Gewinn = Betriebseinnahmen - Betriebsausgaben
```

**Rechtliche Grundlage:**
- § 4 Abs. 3 EStG (Einkommensteuergesetz)
- **Anlage EÜR** zur Einkommensteuererklärung
- Nur für nicht-buchführungspflichtige Unternehmen

**Wer muss EÜR erstellen?**

✅ **Pflicht für:**
- Freiberufler (§ 18 EStG) - Ärzte, Anwälte, Künstler, IT-Berater, etc.
- Kleingewerbetreibende mit:
  - Gewinn < 60.000 € pro Jahr UND
  - Umsatz < 600.000 € pro Jahr
- Land- und Forstwirte (unter bestimmten Grenzen)

❌ **NICHT für:**
- Kapitalgesellschaften (GmbH, AG, UG) → Bilanzierung Pflicht
- Personengesellschaften über Grenzen (OHG, KG) → Bilanzierung Pflicht
- Kleinunternehmer (§ 19 UStG) → EÜR optional, aber empfohlen

**Abgabefrist:**
- Mit Einkommensteuererklärung
- Ohne Steuerberater: 31. Juli des Folgejahres (für 2025 → 31.07.2026)
- Mit Steuerberater: 28. Februar übernächstes Jahr (für 2025 → 28.02.2027)

---

### **7.2 Zufluss-/Abfluss-Prinzip**

**Entscheidend ist WANN das Geld geflossen ist, nicht das Rechnungsdatum!**

#### **Beispiel Einnahmen:**

| Rechnung geschrieben | Zahlung erhalten | EÜR-Jahr |
|---------------------|------------------|----------|
| 15.12.2025 | 10.01.2026 | **2026** (Zufluss) |
| 20.11.2025 | 28.12.2025 | **2025** (Zufluss) |

#### **Beispiel Ausgaben:**

| Rechnung erhalten | Zahlung geleistet | EÜR-Jahr |
|-------------------|-------------------|----------|
| 05.12.2025 | 15.01.2026 | **2026** (Abfluss) |
| 10.12.2025 | 20.12.2025 | **2025** (Abfluss) |

**Wichtig:**
- ✅ Zufluss-/Abfluss-Prinzip = **Ist-Versteuerung** (identisch!)
- ✅ SGBII-konform (siehe Kategorie 6.5)
- ✅ Einfacher für Einsteiger (nur bezahlte Rechnungen zählen)

**Ausnahmen:**
- **Regelmäßige Zahlungen** (z.B. Miete, Versicherungen) → 10-Tage-Regel:
  - Zahlung zwischen 22.12.-10.01. → User wählt Jahr
- **Abschreibungen (AfA):** Nicht nach Zahlung, sondern nach Nutzungsdauer

---

### **7.2.1 Automatische Zuordnung & Warnungen (Frage 7.4)**

#### **Automatische Buchung nach Zahlungsdatum**

**Antwort: Ja, RechnungsPilot bucht automatisch nach Zahlungsdatum (nicht Rechnungsdatum).**

**Technische Umsetzung:**

```python
def calculate_euer_jahr(rechnung):
    """
    Bestimmt EÜR-Jahr basierend auf Zahlungsdatum (Zufluss-/Abfluss-Prinzip)
    """
    if rechnung.zahlungsdatum:
        # Zufluss-/Abfluss-Prinzip: Zahlungsdatum zählt
        return rechnung.zahlungsdatum.year
    else:
        # Rechnung noch nicht bezahlt → Kein EÜR-Jahr
        return None


# Beispiel:
rechnung = Rechnung(
    rechnungsdatum='2025-12-15',
    zahlungsdatum='2026-01-10',  # Zahlung im neuen Jahr
    betrag=1000.00
)

euer_jahr = calculate_euer_jahr(rechnung)  # → 2026 (nicht 2025!)
```

**UI-Verhalten:**

```
┌──────────────────────────────────────────┐
│ Ausgangsrechnung                         │
├──────────────────────────────────────────┤
│                                          │
│ Rechnungsdatum: [15.12.2025]            │
│ Zahlungsdatum:  [10.01.2026]            │
│                                          │
│ ℹ️ EÜR-Jahr: 2026                        │
│    (Zufluss-Prinzip: Zahlungsdatum zählt)│
│                                          │
│ Betrag: 1.000,00 €                       │
│                                          │
│    [ Speichern ]                         │
└──────────────────────────────────────────┘
```

**Filter in EÜR-Berechnung:**

```python
def get_ausgangsrechnungen_fuer_euer(jahr):
    """
    Holt Ausgangsrechnungen für EÜR (nach Zahlungsdatum!)
    """
    return db.query(Ausgangsrechnung).filter(
        Ausgangsrechnung.zahlungsdatum >= f'{jahr}-01-01',
        Ausgangsrechnung.zahlungsdatum <= f'{jahr}-12-31',
        Ausgangsrechnung.status == 'bezahlt'  # Nur bezahlte!
    ).all()

# NICHT nach Rechnungsdatum filtern!
# ❌ FALSCH: Ausgangsrechnung.rechnungsdatum
# ✅ RICHTIG: Ausgangsrechnung.zahlungsdatum
```

---

#### **Hinweise bei Jahresübergang (Rechnung & Zahlung in verschiedenen Jahren)**

**Antwort: Ja, RechnungsPilot warnt proaktiv bei Jahresübergang.**

**Wann wird gewarnt?**

| Rechnungsdatum | Zahlungsdatum | Warnung? | Grund |
|----------------|---------------|----------|-------|
| 15.11.2025 | 28.11.2025 | ❌ Nein | Beide im selben Jahr |
| 15.12.2025 | 10.01.2026 | ✅ Ja | Jahresübergang → EÜR-Jahr ändert sich |
| 20.12.2025 | 28.12.2025 | ⚠️ Optional | Jahresende-Warnung (siehe unten) |

**Warnung bei Jahresübergang:**

```
┌──────────────────────────────────────────┐
│ ⚠️ Jahresübergang: EÜR-Jahr beachten!    │
├──────────────────────────────────────────┤
│                                          │
│ Ausgangsrechnung: RE-2025-042            │
│ Rechnungsdatum: 15.12.2025               │
│ Zahlungsdatum:  10.01.2026               │
│                                          │
│ ⚠️ Rechnung wurde 2025 geschrieben,      │
│    aber Zahlung erfolgt 2026.            │
│                                          │
│ Zufluss-Prinzip (EÜR):                   │
│ → Einnahme zählt für EÜR 2026 (nicht 2025)│
│                                          │
│ Das ist steuerlich korrekt!              │
│ Nur zur Info, falls unerwartet.          │
│                                          │
│              [ Verstanden ]              │
└──────────────────────────────────────────┘
```

**Warnung direkt beim Zahlungseingabe:**

```
┌──────────────────────────────────────────┐
│ Zahlung erfassen                         │
├──────────────────────────────────────────┤
│                                          │
│ Rechnung: RE-2025-042                    │
│ Rechnungsdatum: 15.12.2025               │
│                                          │
│ Zahlungsdatum: [10.01.2026____]          │
│                                          │
│ ⚠️ Achtung: Zahlung im neuen Jahr!       │
│    → EÜR-Jahr: 2026 (nicht 2025)        │
│                                          │
│ Betrag: [1.000,00___] €                  │
│                                          │
│    [Abbrechen]  [ Speichern ]            │
└──────────────────────────────────────────┘
```

---

#### **Jahresende-Warnung (Dezember-Zahlungen)**

**Problem:** User könnte vergessen, Dezember-Zahlungen rechtzeitig zu erfassen.

**Lösung:** Automatische Erinnerung im Januar.

```
┌──────────────────────────────────────────┐
│ ℹ️ Jahresabschluss 2025: Offene Rechnungen│
├──────────────────────────────────────────┤
│                                          │
│ Es gibt 3 unbezahlte Rechnungen aus 2025:│
│                                          │
│ • RE-2025-038 (15.11.25) - 500 €        │
│ • RE-2025-040 (01.12.25) - 750 €        │
│ • RE-2025-042 (15.12.25) - 1.000 €      │
│                                          │
│ Fragen:                                  │
│ 1. Wurden diese in 2025 bezahlt?         │
│    → Zahlungsdatum nachtragen            │
│                                          │
│ 2. Wurden diese in 2026 bezahlt?         │
│    → EÜR 2026 (Zufluss-Prinzip)         │
│                                          │
│ 💡 Tipp: Prüfe Kontoauszüge Dez 2025!    │
│                                          │
│    [Später]  [ Rechnungen prüfen ]       │
└──────────────────────────────────────────┘
```

**Zeitpunkt der Warnung:**

- ✅ Anfang Januar (z.B. ab 05.01.2026)
- ✅ Vor EÜR-Export für Vorjahr
- ✅ Bei EÜR-Berechnung für Vorjahr

---

#### **10-Tage-Regel für regelmäßige Zahlungen**

**Rechtslage:** Regelmäßige Zahlungen (Miete, Versicherung, Abos) zwischen 22.12. und 10.01. können dem alten oder neuen Jahr zugeordnet werden.

**UI-Dialog:**

```
┌──────────────────────────────────────────┐
│ 10-Tage-Regel: Jahr wählen               │
├──────────────────────────────────────────┤
│                                          │
│ Eingangsrechnung: Büromiete Januar 2026  │
│ Zahlungsdatum: 28.12.2025                │
│ Betrag: 500,00 €                         │
│                                          │
│ ℹ️ Regelmäßige Zahlung im Zeitraum       │
│    22.12. - 10.01. → Wahlrecht           │
│                                          │
│ EÜR-Jahr:                                │
│ ○ 2025 (Zahlung vor Jahreswechsel)      │
│ ● 2026 (wirtschaftlich zu Januar gehörig)│
│                                          │
│ 💡 Empfehlung: 2026 (Miete für Januar)   │
│                                          │
│    [Abbrechen]  [ Speichern ]            │
└──────────────────────────────────────────┘
```

**Automatische Erkennung:**

```python
def ist_10_tage_regel_anwendbar(rechnung):
    """
    Prüft ob 10-Tage-Regel anwendbar (22.12. - 10.01.)
    """
    # 1. Regelmäßige Zahlung? (Miete, Versicherung, Abo)
    ist_regelmaessig = rechnung.kategorie in [
        'Raumkosten (Miete)',
        'Versicherungen (betr.)',
        'Telefon, Internet',
        'Software, Lizenzen'  # Wenn monatlich
    ]

    if not ist_regelmaessig:
        return False

    # 2. Zahlungsdatum zwischen 22.12. und 10.01.?
    datum = rechnung.zahlungsdatum
    jahr = datum.year

    # 22.12. - 31.12. (altes Jahr)
    if datum >= date(jahr, 12, 22) and datum <= date(jahr, 12, 31):
        return True

    # 01.01. - 10.01. (neues Jahr)
    if datum >= date(jahr, 1, 1) and datum <= date(jahr, 1, 10):
        return True

    return False
```

---

#### **Übersicht: EÜR-Jahr vs. Rechnungsjahr**

**Dashboard-Widget:**

```
┌──────────────────────────────────────────┐
│ EÜR-Jahresübergang (2025 → 2026)        │
├──────────────────────────────────────────┤
│                                          │
│ Rechnungen 2025, bezahlt in 2026:       │
│   3 Rechnungen, 2.500 € → EÜR 2026      │
│                                          │
│ Rechnungen 2026, bezahlt in 2025:       │
│   0 Rechnungen, 0 € → Keine             │
│                                          │
│ ℹ️ EÜR 2025 niedriger als erwartet?      │
│    Prüfe, ob Dezember-Rechnungen in 2026 │
│    bezahlt wurden.                       │
│                                          │
│    [ Details anzeigen ]                  │
└──────────────────────────────────────────┘
```

**Detail-Ansicht:**

```
┌─────────────────────────────────────────────────────────────┐
│ Jahresübergang: Rechnungen mit abweichendem EÜR-Jahr       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Filter: [2025 ▼]  Typ: [Alle ▼]                             │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Rechnung        │ Rechnungsdatum │ Zahlungsdatum │ EÜR │
│ ├─────────────────┼────────────────┼───────────────┼─────┤
│ │ RE-2025-038     │ 15.11.2025     │ 05.01.2026    │ 2026│
│ │ RE-2025-040     │ 01.12.2025     │ 08.01.2026    │ 2026│
│ │ RE-2025-042     │ 15.12.2025     │ 10.01.2026    │ 2026│
│ └─────────────────┴────────────────┴───────────────┴─────┘   │
│                                                             │
│ 💡 Diese Rechnungen wurden 2025 geschrieben, aber zählen   │
│    für EÜR 2026 (Zufluss-Prinzip).                         │
│                                                             │
│    [CSV exportieren]  [PDF drucken]                         │
└─────────────────────────────────────────────────────────────┘
```

---

#### **Zusammenfassung Frage 7.4**

| Aspekt | Antwort |
|--------|---------|
| **Automatisch nach Zahlungsdatum buchen?** | ✅ Ja, EÜR-Jahr = Zahlungsjahr (nicht Rechnungsjahr) |
| **Hinweise bei Jahresübergang?** | ✅ Ja, proaktive Warnungen bei Zahlungseingabe und Jahresabschluss |
| **10-Tage-Regel?** | ✅ Ja, automatische Erkennung + Wahlrecht für regelmäßige Zahlungen |
| **Dashboard-Widget?** | ✅ Ja, Übersicht Jahresübergang mit abweichenden EÜR-Jahren |

---

### **7.3 Betriebseinnahmen**

**Was gehört rein?**

✅ **Alle betrieblichen Einnahmen:**
- Umsätze aus Verkauf (Waren, Dienstleistungen)
- Honorare, Provisionen
- Erstattungen (z.B. von Versicherung)
- Skonti, Rabatte (erhalten)
- Private Kfz-Nutzung (bei Betriebsfahrzeug)
- Entnahmen (z.B. Waren für Eigenverbrauch)

❌ **NICHT:**
- Privatentnahmen (Geld vom Geschäftskonto auf privat)
- Darlehen/Kredite (keine Einnahmen, nur Fremdkapital)
- Umsatzsteuer (wird separat erfasst)

**EÜR-Zeilen (Anlage EÜR):**
- **Zeile 11:** Umsätze 19% USt
- **Zeile 12:** Umsätze 7% USt
- **Zeile 13:** Steuerfreie Umsätze (§ 4 Nr. 1-28 UStG)
- **Zeile 14:** Umsätze Kleinunternehmer (§ 19 UStG)
- **Zeile 15:** Innergemeinschaftliche Lieferungen (0% USt, EU)
- **Zeile 21:** Vereinnahmte Umsatzsteuer

**RechnungsPilot-Datenquellen:**
```python
def calculate_betriebseinnahmen(jahr):
    """
    Berechnet Betriebseinnahmen für EÜR
    """
    # 1. Ausgangsrechnungen (bezahlt!)
    ausgangsrechnungen = get_ausgangsrechnungen(
        jahr=jahr,
        status='bezahlt',  # Nur bezahlte (Zufluss-Prinzip!)
        zahlungsdatum_jahr=jahr  # Zahlung im Jahr (nicht Rechnungsdatum!)
    )

    # Aufschlüsselung nach USt-Satz
    umsatz_19 = sum(
        r.netto_betrag for r in ausgangsrechnungen
        if r.umsatzsteuer_satz == 19.0
    )

    umsatz_7 = sum(
        r.netto_betrag for r in ausgangsrechnungen
        if r.umsatzsteuer_satz == 7.0
    )

    umsatz_0_eu = sum(
        r.netto_betrag for r in ausgangsrechnungen
        if r.umsatzsteuer_satz == 0.0 and r.ist_eu_lieferung
    )

    umsatz_kleinunternehmer = sum(
        r.brutto_betrag for r in ausgangsrechnungen
        if user.ist_kleinunternehmer
    )

    # 2. Bareinnahmen (Kassenbuch)
    bareinnahmen = get_kassenbuch_einnahmen(
        jahr=jahr,
        art='Einnahme'
    )

    bar_umsatz_19 = sum(
        e.netto_betrag for e in bareinnahmen
        if e.ust_satz == 19.0
    )

    bar_umsatz_7 = sum(
        e.netto_betrag for e in bareinnahmen
        if e.ust_satz == 7.0
    )

    # SUMMEN
    return {
        'zeile_11_umsatz_19': umsatz_19 + bar_umsatz_19,
        'zeile_12_umsatz_7': umsatz_7 + bar_umsatz_7,
        'zeile_15_eu_lieferungen': umsatz_0_eu,
        'zeile_14_kleinunternehmer': umsatz_kleinunternehmer,
        'zeile_21_ust_gesamt': (umsatz_19 + bar_umsatz_19) * 0.19 + (umsatz_7 + bar_umsatz_7) * 0.07
    }
```

---

### **7.4 Betriebsausgaben**

**Was gehört rein?**

✅ **Alle betrieblichen Ausgaben:**
- Wareneinkauf, Material
- Bürobedarf, Software
- Miete (Büro, Lager)
- Versicherungen (betrieblich)
- Telefon, Internet
- Fahrtkosten, Reisekosten
- Fortbildungen
- Steuerberatungskosten
- Abschreibungen (AfA)
- Zinsen für Betriebskredite

❌ **NICHT:**
- Private Ausgaben
- Einkommensteuer, Lohnsteuer (nicht abzugsfähig)
- Geldstrafen, Bußgelder
- Repräsentationsaufwand (nur teilweise)

**EÜR-Zeilen (Anlage EÜR):**
- **Zeile 25:** Wareneinkauf
- **Zeile 26:** Löhne, Gehälter
- **Zeile 28:** Raumkosten (Miete, Nebenkosten)
- **Zeile 32:** Fahrtkosten (Kfz)
- **Zeile 34:** Werbekosten
- **Zeile 36:** Bürobedarf
- **Zeile 40:** Fortbildungskosten
- **Zeile 41:** Versicherungen
- **Zeile 43:** Sonstige unbeschränkt abziehbare Betriebsausgaben
- **Zeile 45:** Abschreibungen (AfA)
- **Zeile 60:** Vorsteuer (abziehbar)

**RechnungsPilot-Datenquellen:**
```python
def calculate_betriebsausgaben(jahr):
    """
    Berechnet Betriebsausgaben für EÜR
    """
    # 1. Eingangsrechnungen (bezahlt!)
    eingangsrechnungen = get_eingangsrechnungen(
        jahr=jahr,
        status='bezahlt',  # Nur bezahlte (Abfluss-Prinzip!)
        zahlungsdatum_jahr=jahr
    )

    # Kategorisierung nach EÜR-Zeilen
    ausgaben_kategorisiert = {}

    for kategorie in EÜR_KATEGORIEN:
        ausgaben_kategorisiert[kategorie.zeile] = sum(
            r.netto_betrag for r in eingangsrechnungen
            if r.kategorie == kategorie.name
        )

    # 2. Barausgaben (Kassenbuch)
    barausgaben = get_kassenbuch_ausgaben(
        jahr=jahr,
        art='Ausgabe'
    )

    for kategorie in EÜR_KATEGORIEN:
        ausgaben_kategorisiert[kategorie.zeile] += sum(
            a.netto_betrag for a in barausgaben
            if a.kategorie == kategorie.name
        )

    # 3. Vorsteuer (abziehbar)
    vorsteuer = sum(
        r.umsatzsteuer_betrag for r in eingangsrechnungen
        if r.vorsteuerabzug  # Nur wenn abziehbar!
    )

    vorsteuer += sum(
        a.ust_betrag for a in barausgaben
        if a.vorsteuerabzug
    )

    return {
        **ausgaben_kategorisiert,
        'zeile_60_vorsteuer': vorsteuer
    }
```

**Kategorie-Mapping (Beispiel):**
```python
EÜR_KATEGORIEN = [
    {'zeile': 25, 'name': 'Wareneinkauf'},
    {'zeile': 26, 'name': 'Löhne & Gehälter'},  # Auch für Einzelunternehmer mit Mitarbeitern!
    {'zeile': 28, 'name': 'Raumkosten'},
    {'zeile': 32, 'name': 'Fahrtkosten'},
    {'zeile': 34, 'name': 'Werbekosten'},
    {'zeile': 36, 'name': 'Bürobedarf'},
    {'zeile': 40, 'name': 'Fortbildung'},
    {'zeile': 41, 'name': 'Versicherungen'},
    {'zeile': 43, 'name': 'Sonstige'},
]
```

---

### **7.4.1 Betriebsausgaben-Kategorien (Frage 7.2)**

**Konzept:**

RechnungsPilot bietet ein **zweistufiges Kategorien-System**:

1. **Vordefinierte Standard-Kategorien** (nach Anlage EÜR)
2. **Frei erweiterbare User-Kategorien** (optional)

---

#### **Standard-Kategorien**

**Anzahl:** 15 vordefinierte Ausgaben-Kategorien

**Basis:** Anlage EÜR Zeilen 25-60 + DATEV-Kontenrahmen

**Vollständige Liste:**

```python
AUSGABEN_KATEGORIEN = [
    # ID | Name                    | EÜR-Zeile | DATEV SKR03 | DATEV SKR04

    # Zeile 25: Wareneinkauf
    {'id': 10, 'name': 'Wareneinkauf', 'euer_zeile': 25, 'skr03': 3400, 'skr04': 5400},

    # Zeile 26: Löhne & Gehälter (auch für Einzelunternehmer mit Mitarbeitern!)
    {'id': 11, 'name': 'Löhne & Gehälter', 'euer_zeile': 26, 'skr03': 4120, 'skr04': 6020},

    # Zeile 28: Raumkosten
    {'id': 12, 'name': 'Raumkosten (Miete)', 'euer_zeile': 28, 'skr03': 4210, 'skr04': 6300},
    {'id': 13, 'name': 'Strom, Gas, Wasser', 'euer_zeile': 28, 'skr03': 4240, 'skr04': 6325},
    {'id': 14, 'name': 'Telefon, Internet', 'euer_zeile': 28, 'skr03': 4910, 'skr04': 6805},

    # Zeile 32: Fahrtkosten
    {'id': 15, 'name': 'KFZ-Kosten (Benzin)', 'euer_zeile': 32, 'skr03': 4530, 'skr04': 6530},
    {'id': 16, 'name': 'KFZ-Versicherung', 'euer_zeile': 32, 'skr03': 4570, 'skr04': 6560},
    {'id': 17, 'name': 'Fahrtkosten (ÖPNV)', 'euer_zeile': 32, 'skr03': 4670, 'skr04': 6670},

    # Zeile 34: Werbekosten
    {'id': 18, 'name': 'Werbekosten', 'euer_zeile': 34, 'skr03': 4600, 'skr04': 6600},

    # Zeile 36: Bürobedarf
    {'id': 19, 'name': 'Bürobedarf', 'euer_zeile': 36, 'skr03': 4910, 'skr04': 6815},
    {'id': 20, 'name': 'Software, Lizenzen', 'euer_zeile': 36, 'skr03': 4940, 'skr04': 6825},

    # Zeile 40: Fortbildung
    {'id': 21, 'name': 'Fortbildung', 'euer_zeile': 40, 'skr03': 4945, 'skr04': 6820},

    # Zeile 41: Versicherungen
    {'id': 22, 'name': 'Versicherungen (betr.)', 'euer_zeile': 41, 'skr03': 4360, 'skr04': 6540},

    # Zeile 43: Sonstige unbeschränkt abziehbare Betriebsausgaben
    {'id': 23, 'name': 'Steuerberatung', 'euer_zeile': 43, 'skr03': 4970, 'skr04': 6837},
    {'id': 24, 'name': 'Sonstige Ausgaben', 'euer_zeile': 43, 'skr03': 4980, 'skr04': 6855},
]
```

**Vorteile:**
- ✅ Sofort einsatzbereit (kein Setup nötig)
- ✅ Korrekte EÜR-Zuordnung garantiert
- ✅ DATEV-Export funktioniert automatisch
- ✅ Für 90% der Einzelunternehmer ausreichend

---

#### **Benutzerdefinierte Kategorien**

**User kann eigene Kategorien hinzufügen:**

```python
class BenutzerKategorie:
    """
    Benutzerdefinierte Ausgaben-Kategorie
    """
    id: int  # 100+ (User-Kategorien starten bei ID 100)
    name: str  # z.B. "Hosting & Domain-Kosten"
    euer_zeile: int  # User wählt aus Dropdown: 25, 28, 32, 34, 36, 40, 41, 43
    datev_konto_skr03: int  # Optional: User kann DATEV-Konto angeben
    datev_konto_skr04: int  # Optional
    parent_kategorie_id: int  # Optional: Verknüpfung zu Standard-Kategorie
```

**UI zum Anlegen:**

```
┌──────────────────────────────────────────┐
│ Neue Kategorie erstellen                 │
├──────────────────────────────────────────┤
│                                          │
│  Name:  [Hosting & Domain-Kosten___]    │
│                                          │
│  Zuordnung:                              │
│  ● Basierend auf Standard-Kategorie:    │
│    [Bürobedarf ▼]                        │
│    → EÜR-Zeile 36                        │
│    → DATEV SKR03: 4910                   │
│                                          │
│  ○ Manuelle Zuordnung:                   │
│    EÜR-Zeile: [Zeile 36 ▼]              │
│    DATEV SKR03: [4910_______]           │
│    DATEV SKR04: [6815_______]           │
│                                          │
│    [Abbrechen]  [ Speichern ]            │
└──────────────────────────────────────────┘
```

**Beispiel-Workflow:**

1. User benötigt Kategorie "Hosting & Domain-Kosten"
2. Wählt Basis-Kategorie "Bürobedarf" (Zeile 36, DATEV 4910)
3. Neue Unterkategorie wird erstellt
4. Bei Eingangsrechnung: User wählt "Hosting & Domain-Kosten"
5. EÜR: Wird automatisch zu Zeile 36 addiert
6. DATEV-Export: Wird mit Konto 4910 exportiert

**Vorteile:**
- ✅ Flexibel für spezielle Branchen (z.B. Fotografen: "Model-Honorare")
- ✅ Detailliertere Auswertungen möglich
- ✅ EÜR-Konformität bleibt erhalten (durch Basis-Kategorie)
- ✅ DATEV-Export funktioniert (durch geerbtes Konto)

---

#### **DATEV-Kontenrahmen: SKR03 vs. SKR04**

**Warum zwei Kontenrahmen?**

| Kontenrahmen | Zielgruppe | Struktur |
|--------------|-----------|----------|
| **SKR03** | Gewerbetreibende, Handwerker, Handel | Prozessgliederung (Umsatzprozess) |
| **SKR04** | Freiberufler, Dienstleister | Abschlussgliederung (GuV-Schema) |

**User wählt bei Ersteinrichtung (Kategorie 8.6):**

```
Kontenrahmen wählen:

○ SKR03 - Gewerbetreibende
  Für: Handel, Handwerk, Produktion

● SKR04 - Freiberufler
  Für: IT-Berater, Ärzte, Anwälte, Kreative
```

**Automatisches Mapping:**

```python
def get_datev_konto(kategorie, kontenrahmen):
    """
    Gibt DATEV-Konto je nach Kontenrahmen zurück
    """
    if kontenrahmen == 'SKR03':
        return kategorie.skr03
    else:
        return kategorie.skr04

# Beispiel:
kategorie = AUSGABEN_KATEGORIEN[0]  # Wareneinkauf
get_datev_konto(kategorie, 'SKR03')  # → 3400
get_datev_konto(kategorie, 'SKR04')  # → 5400
```

**Kontenrahmen wechseln:**

⚠️ **Hinweis:** Wechsel nur möglich, wenn:
- Noch keine Buchungen vorhanden ODER
- User akzeptiert Neu-Mapping aller Buchungen

```
┌──────────────────────────────────────────┐
│ ⚠️ Kontenrahmen wechseln?                │
├──────────────────────────────────────────┤
│                                          │
│ Aktuell:  SKR03 (Gewerbetreibende)      │
│ Neu:      SKR04 (Freiberufler)          │
│                                          │
│ Auswirkungen:                            │
│ • 234 Buchungen werden neu zugeordnet   │
│ • DATEV-Export ändert sich              │
│ • Bisherige Exporte bleiben unverändert │
│                                          │
│ ⚠️ Dieser Vorgang kann nicht rückgängig │
│    gemacht werden!                       │
│                                          │
│    [Abbrechen]  [ Kontenrahmen wechseln ]│
└──────────────────────────────────────────┘
```

---

#### **Namenskonventionen**

**Regeln für Kategorienamen:**

1. **Kurz & prägnant:** Max. 30 Zeichen
2. **Selbsterklärend:** "Bürobedarf" statt "BB" oder "Diverses"
3. **Eindeutig:** "Telefon, Internet" statt nur "Telefon"
4. **Hierarchie optional:** "KFZ-Kosten (Benzin)" vs. einfach "Benzin"

**Beispiele:**

| ✅ Gut | ❌ Schlecht |
|-------|-----------|
| Wareneinkauf | Waren |
| Löhne & Gehälter | Löhne |
| Strom, Gas, Wasser | Energie |
| Telefon, Internet | Telekommunikation (zu lang) |
| KFZ-Kosten (Benzin) | Sprit |
| Software, Lizenzen | SW |

**User-Kategorien:** Können frei benannt werden, aber RechnungsPilot schlägt vor:
- "Hosting & Domain-Kosten" (Unterkategorie von "Bürobedarf")
- "Model-Honorare" (Unterkategorie von "Löhne & Gehälter")
- "Werbe-Flyer" (Unterkategorie von "Werbekosten")

---

#### **Standard-Kategorien bearbeiten/löschen?**

**Nein!** Standard-Kategorien sind **schreibgeschützt**.

**Begründung:**
- ✅ Garantiert korrekte EÜR-Zuordnung
- ✅ Verhindert Fehler (z.B. "Wareneinkauf" versehentlich gelöscht)
- ✅ DATEV-Export bleibt kompatibel

**Workaround:**
- User kann Standard-Kategorie **ausblenden** (wenn ungenutzt)
- User kann **eigene Kategorie** mit anderem Namen erstellen

---

#### **Zusammenfassung Frage 7.2**

| Aspekt | Antwort |
|--------|---------|
| **Vordefinierte Liste nach Anlage EÜR?** | ✅ Ja, 15 Standard-Kategorien |
| **Frei konfigurierbar/erweiterbar?** | ✅ Ja, User-Kategorien mit EÜR-Zuordnung |
| **Anlehnung an DATEV-Konten?** | ✅ Beide: Eigene Namen + DATEV-Mapping (SKR03/SKR04) |
| **Wie viele Standard-Kategorien?** | **15 Ausgaben** + 5 Einnahmen |

---

### **7.5 Abschreibungen (AfA)**

**Was ist AfA?**
- **AfA** = Absetzung für Abnutzung
- Verteilung der Anschaffungskosten über die Nutzungsdauer
- Beispiel: Laptop 1.200 € → 3 Jahre Nutzung → 400 €/Jahr AfA

**Wann muss abgeschrieben werden?**

| Anschaffungskosten (netto) | Behandlung |
|----------------------------|------------|
| **< 800 €** | Sofortabzug (volle Kosten im Jahr der Anschaffung) |
| **800 € - 1.000 €** | Poolabschreibung (5 Jahre, je 20%) oder Sofortabzug |
| **> 1.000 €** | Abschreibung über Nutzungsdauer (AfA-Tabelle) |

**AfA-Tabelle (Beispiele):**

| Anlagegut | Nutzungsdauer | AfA/Jahr |
|-----------|---------------|----------|
| Computer, Laptop | 3 Jahre | 33,33% |
| Drucker | 3 Jahre | 33,33% |
| Büromöbel | 13 Jahre | 7,69% |
| Pkw | 6 Jahre | 16,67% |
| Software | 3 Jahre | 33,33% |
| Gebäude | 33-50 Jahre | 2-3% |

**Berechnung:**
```
AfA linear = Anschaffungskosten / Nutzungsdauer
```

**Beispiel:**
```
Laptop gekauft: 15.03.2025, 1.200 € (netto)
Nutzungsdauer: 3 Jahre
AfA/Jahr: 1.200 € / 3 = 400 €
AfA 2025 (März-Dez): 400 € × 10/12 = 333,33 € (monatsgenau!)
AfA 2026-2027: je 400 €
AfA 2028 (Jan-Feb): 400 € × 2/12 = 66,67 €
```

**RechnungsPilot-Implementierung:**
```python
class Anlagegut:
    """
    Anlagegut mit Abschreibung
    """
    id: int
    bezeichnung: str  # "Laptop Dell XPS 13"
    anschaffungsdatum: date  # 15.03.2025
    anschaffungskosten: Decimal  # 1200.00 (netto)
    nutzungsdauer_jahre: int  # 3
    afa_methode: str  # 'linear', 'degressiv', 'pool'
    restbuchwert: Decimal  # 1200.00 → 800.00 → 400.00 → 0.00
    rechnung_id: int  # Verknüpfung zur Eingangsrechnung


def calculate_afa(anlagegut, jahr):
    """
    Berechnet AfA für ein Jahr
    """
    # 1. Volle AfA pro Jahr
    afa_pro_jahr = anlagegut.anschaffungskosten / anlagegut.nutzungsdauer_jahre

    # 2. Monatsgenau (nur im ersten und letzten Jahr)
    start_jahr = anlagegut.anschaffungsdatum.year
    ende_jahr = start_jahr + anlagegut.nutzungsdauer_jahre

    if jahr == start_jahr:
        # Erstes Jahr: Nur Monate ab Anschaffung
        monate = 13 - anlagegut.anschaffungsdatum.month  # März → 10 Monate
        return afa_pro_jahr * (monate / 12)

    elif jahr >= start_jahr and jahr < ende_jahr:
        # Volle Jahre dazwischen
        return afa_pro_jahr

    elif jahr == ende_jahr:
        # Letztes Jahr: Nur Monate bis Jahresende
        monate = anlagegut.anschaffungsdatum.month - 1  # März → 2 Monate
        return afa_pro_jahr * (monate / 12)

    else:
        # Außerhalb Nutzungsdauer
        return 0


def get_afa_for_euer(jahr):
    """
    Summiert alle AfA für EÜR Zeile 45
    """
    anlagegueter = get_anlagegueter()

    afa_gesamt = sum(
        calculate_afa(a, jahr) for a in anlagegueter
    )

    return {
        'zeile_45_afa': afa_gesamt
    }
```

**Geringwertige Wirtschaftsgüter (GWG):**
```python
def handle_gwg(rechnung):
    """
    Prüft ob GWG-Regelung anwendbar
    """
    netto = rechnung.netto_betrag

    if netto < 800:
        # Sofortabzug
        return {
            'typ': 'sofortabzug',
            'zeile_43': netto,  # Sonstige Ausgaben
            'afa_notwendig': False
        }

    elif netto >= 800 and netto <= 1000:
        # User wählt: Sofortabzug oder Pool
        return {
            'typ': 'wahlrecht',
            'optionen': ['sofortabzug', 'pool_5_jahre']
        }

    else:
        # Abschreibung Pflicht
        return {
            'typ': 'afa_pflicht',
            'afa_notwendig': True
        }
```

---

### **7.5.1 Anlagenverwaltung (Frage 7.3)**

#### **Umfang der Anlagenverwaltung in RechnungsPilot**

**RechnungsPilot bietet vollständige Anlagenverwaltung mit:**

1. ✅ **GWG-Automatik** (Sofortabzug < 800 €, Poolabschreibung 800-1000 €)
2. ✅ **AfA-Rechner** (automatische Abschreibungsberechnung)
3. ✅ **Anlagenverzeichnis** (Übersicht aller Wirtschaftsgüter)
4. ✅ **Monatsgenauer AfA-Berechnung** (anteilig im ersten/letzten Jahr)

---

#### **GWG-Grenzwerte: 800€ vs. 1000€**

**Drei Schwellenwerte:**

| Anschaffungskosten (netto) | Regelung | RechnungsPilot-Verhalten |
|----------------------------|----------|--------------------------|
| **< 800 €** | Sofortabzug Pflicht | Automatisch zu Zeile 43 (Sonstige Ausgaben) |
| **800 € - 1.000 €** | Wahlrecht: Sofortabzug ODER Poolabschreibung | User wird gefragt (siehe Dialog unten) |
| **> 1.000 €** | AfA-Pflicht | Anlage wird erstellt, AfA über Nutzungsdauer |

**UI-Dialog bei 800-1000€:**

```
┌──────────────────────────────────────────┐
│ GWG-Behandlung wählen                    │
├──────────────────────────────────────────┤
│                                          │
│ Eingangsrechnung: Laptop HP ProBook     │
│ Netto: 899,00 €                          │
│                                          │
│ Anschaffungskosten zwischen 800-1000 €   │
│ → Wahlrecht nach § 6 Abs. 2a EStG       │
│                                          │
│ Optionen:                                │
│                                          │
│ ● Sofortabzug (empfohlen)                │
│   Volle 899 € im Jahr 2025 abziehbar    │
│   → EÜR Zeile 43                         │
│                                          │
│ ○ Poolabschreibung (5 Jahre)            │
│   179,80 € pro Jahr (2025-2029)         │
│   → EÜR Zeile 45 (AfA)                   │
│                                          │
│ 💡 Sofortabzug maximiert Steuerersparnis│
│    in 2025. Poolabschreibung verteilt   │
│    über 5 Jahre.                         │
│                                          │
│    [Abbrechen]  [ Auswählen ]            │
└──────────────────────────────────────────┘
```

**Empfehlung:**

RechnungsPilot empfiehlt **Sofortabzug** (wenn User nicht sicher ist), da:
- ✅ Steuerersparnis früher (im Jahr der Anschaffung)
- ✅ Weniger Verwaltungsaufwand (keine 5-Jahres-Buchführung)
- ✅ Einfacher zu verstehen

---

#### **AfA-Rechner**

**Funktionen:**

1. **Automatische Nutzungsdauer-Vorschläge** (basierend auf amtlicher AfA-Tabelle)
2. **Monatsgenauer AfA-Berechnung** (anteilig im ersten/letzten Jahr)
3. **Restbuchwert-Tracking** (für Verkauf/Entnahme)

**UI beim Anlagegut anlegen:**

```
┌──────────────────────────────────────────┐
│ Anlagegut erfassen                       │
├──────────────────────────────────────────┤
│                                          │
│ Bezeichnung: [Laptop Dell XPS 13_____]  │
│                                          │
│ Anschaffung:                             │
│   Datum:   [15.03.2025]                  │
│   Kosten:  [1.200,00] € (netto)         │
│                                          │
│ Abschreibung:                            │
│   Kategorie: [Computer/Laptop ▼]         │
│   Nutzungsdauer: [3] Jahre               │
│              💡 Vorschlag aus AfA-Tabelle│
│                                          │
│ AfA-Berechnung (Vorschau):               │
│   2025 (Mär-Dez): 333,33 € (10/12)      │
│   2026-2027:      400,00 € (je Jahr)     │
│   2028 (Jan-Feb):  66,67 € (2/12)       │
│   ────────────────────────────────       │
│   Gesamt:       1.200,00 €               │
│                                          │
│ Verknüpfung:                             │
│   Eingangsrechnung: [RE-2025-001 ▼]     │
│                                          │
│    [Abbrechen]  [ Speichern ]            │
└──────────────────────────────────────────┘
```

**AfA-Tabelle (integriert):**

RechnungsPilot enthält die wichtigsten Einträge der amtlichen AfA-Tabelle:

```python
AFA_TABELLE = {
    'Computer/Laptop': 3,
    'Drucker': 3,
    'Monitor': 3,
    'Smartphone': 5,
    'Software': 3,
    'Büromöbel': 13,
    'PKW': 6,
    'Kamera (professionell)': 7,
    'Werkzeuge': 10,
    'Maschinen (allgemein)': 10,
    'Gebäude (Büro)': 33,
}
```

**User kann abweichen:**

- ⚠️ Warnung wenn Nutzungsdauer < AfA-Tabelle
- ℹ️ Hinweis: "Finanzamt erkennt ggf. nicht an"

---

#### **Anlagenverzeichnis**

**Übersicht aller Anlagegüter:**

```
┌─────────────────────────────────────────────────────────────┐
│ Anlagenverzeichnis                           [+ Neu]        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Filter: [Alle ▼]  Suche: [____________]                     │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Bezeichnung            │ Anschaffung │ Restbuchwert  │   │
│ ├────────────────────────┼─────────────┼───────────────┤   │
│ │ Laptop Dell XPS 13     │ 15.03.2025  │   800,00 €   │   │
│ │   1.200,00 € (3 Jahre) │ AfA 2025: 333,33 €         │   │
│ ├────────────────────────┼─────────────┼───────────────┤   │
│ │ Drucker HP LaserJet    │ 02.01.2024  │   199,80 €   │   │
│ │   Pool (5 Jahre)       │ AfA 2025: 99,90 €          │   │
│ ├────────────────────────┼─────────────┼───────────────┤   │
│ │ Bürostuhl Herman M.    │ 12.05.2023  │   384,62 €   │   │
│ │   500,00 € (13 Jahre)  │ AfA 2025: 38,46 €          │   │
│ └────────────────────────┴─────────────┴───────────────┘   │
│                                                             │
│ AfA 2025 gesamt: 471,69 € → EÜR Zeile 45                   │
│                                                             │
│ Aktionen: [AfA-Plan drucken]  [CSV exportieren]             │
└─────────────────────────────────────────────────────────────┘
```

**Funktionen:**

- ✅ Sortieren nach: Bezeichnung, Anschaffungsdatum, Restbuchwert
- ✅ Filtern nach: Aktiv, Vollständig abgeschrieben, Verkauft
- ✅ Suche nach Bezeichnung
- ✅ Detailansicht (mit AfA-Plan für alle Jahre)
- ✅ Export: CSV, PDF

**Detailansicht (Klick auf Anlagegut):**

```
┌──────────────────────────────────────────┐
│ Anlagegut: Laptop Dell XPS 13            │
├──────────────────────────────────────────┤
│                                          │
│ STAMMDATEN:                              │
│   Anschaffung:  15.03.2025               │
│   Kosten:       1.200,00 € (netto)      │
│   Nutzungsdauer: 3 Jahre (Computer)      │
│   Verknüpfung:  RE-2025-001              │
│                                          │
│ ABSCHREIBUNGSPLAN:                       │
│ ┌──────────────────────────────────┐     │
│ │ Jahr │ AfA      │ Restbuchwert  │     │
│ ├──────┼──────────┼───────────────┤     │
│ │ 2025 │  333,33  │   866,67 €   │     │
│ │ 2026 │  400,00  │   466,67 €   │     │
│ │ 2027 │  400,00  │    66,67 €   │     │
│ │ 2028 │   66,67  │     0,00 €   │     │
│ └──────┴──────────┴───────────────┘     │
│                                          │
│ AKTIONEN:                                │
│ [ Bearbeiten ]  [ Verkaufen/Entnahme ]   │
│ [ AfA-Plan drucken ]  [ Löschen ]        │
└──────────────────────────────────────────┘
```

---

#### **Verkauf/Entnahme von Anlagegütern**

**Was passiert beim Verkauf?**

```
┌──────────────────────────────────────────┐
│ Anlagegut verkaufen/entnehmen            │
├──────────────────────────────────────────┤
│                                          │
│ Anlagegut: Laptop Dell XPS 13            │
│ Restbuchwert: 466,67 € (Stand 31.12.2026)│
│                                          │
│ Verkaufsdatum: [15.06.2027__]            │
│ Verkaufspreis: [300,00___] € (netto)    │
│                                          │
│ Berechnung:                              │
│   AfA 2027 (Jan-Mai):  166,67 € (5/12)  │
│   Restbuchwert danach: 300,00 €          │
│   Verkaufspreis:       300,00 €          │
│   ────────────────────────────────       │
│   Gewinn/Verlust:        0,00 €          │
│                                          │
│ ℹ️ Kein Buchgewinn/-verlust              │
│                                          │
│    [Abbrechen]  [ Verkauf buchen ]       │
└──────────────────────────────────────────┘
```

**Buchhaltung:**

- ✅ AfA wird anteilig bis Verkaufsdatum berechnet
- ✅ Buchgewinn/-verlust wird berechnet (Verkaufspreis - Restbuchwert)
- ✅ Buchgewinn → EÜR Zeile 11 (Betriebseinnahmen)
- ✅ Buchverlust → EÜR Zeile 43 (Sonstige Ausgaben)

---

#### **Einfache Erfassung vs. vollständige Abschreibungslogik**

**Entscheidung:** RechnungsPilot bietet **vollständige Abschreibungslogik**.

**Begründung:**

| Aspekt | Einfache Erfassung | Vollständige AfA-Logik | Entscheidung |
|--------|-------------------|------------------------|--------------|
| **Aufwand für User** | Niedrig (nur Betrag eingeben) | Mittel (Anlagegut anlegen) | ✅ Mittel akzeptabel |
| **Korrektheit EÜR** | Manuell fehleranfällig | Garantiert korrekt | ✅ Wichtig! |
| **Mehrjahresplanung** | Nicht möglich | Automatisch | ✅ Sehr hilfreich |
| **Verkauf/Entnahme** | Kompliziert manuell | Automatisch berechnet | ✅ Wichtig! |
| **Steuerprüfung** | Anlagenverzeichnis fehlt | Vorhanden | ✅ Pflicht ab 60k € Gewinn |

**Kompromiss:** Automatische GWG-Erkennung

- < 800 €: Sofortabzug (User muss kein Anlagegut anlegen)
- \> 800 €: RechnungsPilot **schlägt vor**, Anlagegut anzulegen (kann übersprungen werden)

**Workflow:**

```
Eingangsrechnung erfasst: Laptop 1.200 €

┌──────────────────────────────────────────┐
│ ℹ️ Anlagegut anlegen?                    │
├──────────────────────────────────────────┤
│                                          │
│ Die Rechnung "Laptop Dell XPS 13" ist    │
│ über 800 € und könnte ein Anlagegut sein.│
│                                          │
│ Empfehlung: Als Anlagegut anlegen        │
│ → AfA über 3 Jahre (Computer)            │
│                                          │
│ ○ Als Anlagegut anlegen (empfohlen)     │
│   → AfA-Rechner öffnen                   │
│                                          │
│ ○ Als Betriebsausgabe buchen             │
│   → Sofortabzug (nicht korrekt!)        │
│                                          │
│ [Überspringen]  [ Auswählen ]            │
└──────────────────────────────────────────┘
```

**Wichtig:** User kann überspringen, aber RechnungsPilot warnt:

⚠️ "Achtung: Anschaffungskosten > 1.000 € müssen lt. EStG abgeschrieben werden. Sofortabzug kann vom Finanzamt abgelehnt werden."

---

#### **Zusammenfassung Frage 7.3**

| Aspekt | Antwort |
|--------|---------|
| **GWG bis 800€/1000€?** | ✅ Ja, automatische Erkennung + Wahlrecht 800-1000€ |
| **AfA-Rechner?** | ✅ Ja, vollständiger AfA-Rechner mit Nutzungsdauer-Vorschlägen |
| **Einfache Erfassung oder Abschreibungslogik?** | ✅ **Vollständige Abschreibungslogik** (mit GWG-Automatik < 800 €) |
| **Anlagenverzeichnis?** | ✅ Ja, mit AfA-Plan, Restbuchwert, Verkauf/Entnahme |

---

### **7.6 MVP-Implementierung (Hybrid-Ansatz)**

Analog zu UStVA (Kategorie 6.1) nutzen wir einen **Hybrid-Ansatz:**

#### **Version 1.0 (MVP):**

**✅ RechnungsPilot berechnet:**
- Betriebseinnahmen (nach EÜR-Zeilen sortiert)
- Betriebsausgaben (nach EÜR-Zeilen sortiert)
- AfA für Anlagegüter
- Gewinn = Einnahmen - Ausgaben

**✅ Export-Formate:**
- **CSV/Excel** - Für manuelle Übertragung in ELSTER
- **PDF-Report** - Übersichtliche Darstellung

**❌ NICHT in MVP:**
- ELSTER-XML-Generierung
- Direkte Übermittlung ans Finanzamt

**User-Workflow:**
```
1. RechnungsPilot: "EÜR erstellen" → Zeitraum wählen (2025)
2. RechnungsPilot berechnet alle Werte
3. Export als CSV/Excel/PDF
4. User öffnet ELSTER-Portal
5. User trägt Werte MANUELL aus CSV in Anlage EÜR ein
6. User sendet über ELSTER
```

#### **Version 2.0 (Zukunft):**

**✅ Vollautomatisch:**
- ELSTER-XML-Generierung (Anlage EÜR)
- Validierung gegen ELSTER-Schema
- Direkte Übermittlung mit ELSTER-Zertifikat

**User-Workflow:**
```
1. RechnungsPilot: "EÜR erstellen und senden"
2. RechnungsPilot generiert ELSTER-XML
3. RechnungsPilot sendet direkt ans Finanzamt
4. Bestätigung erhalten → Fertig!
```

---

### **7.7 EÜR-Berechnung (Implementierung)**

**Hauptfunktion:**
```python
def calculate_euer(jahr):
    """
    Berechnet vollständige EÜR für ein Jahr
    """
    # 1. Betriebseinnahmen
    einnahmen = calculate_betriebseinnahmen(jahr)

    # 2. Betriebsausgaben
    ausgaben = calculate_betriebsausgaben(jahr)

    # 3. AfA
    afa = get_afa_for_euer(jahr)

    # 4. Gewinn
    gewinn = (
        einnahmen['zeile_11_umsatz_19'] +
        einnahmen['zeile_12_umsatz_7'] +
        einnahmen['zeile_13_steuerfrei'] +
        einnahmen['zeile_14_kleinunternehmer'] +
        einnahmen['zeile_15_eu_lieferungen']
        -
        sum(ausgaben.values())
        -
        afa['zeile_45_afa']
    )

    return {
        'jahr': jahr,
        'einnahmen': einnahmen,
        'ausgaben': ausgaben,
        'afa': afa,
        'gewinn': gewinn,
        'erstellt_am': datetime.now()
    }
```

**Export-Varianten:**

RechnungsPilot bietet **zwei EÜR-Export-Varianten**:

1. **Amtliche Anlage EÜR** - Für ELSTER/Finanzamt (alle Zeilen, zu denen Daten verfügbar sind)
2. **Vereinfachte EÜR** - Für User/Jobcenter (übersichtlich, nur Einnahmen - Ausgaben = Gewinn)

**Export 1: Amtliche Anlage EÜR (vollständig)**
```python
def export_euer_amtlich(euer_data):
    """
    Exportiert vollständige Anlage EÜR für ELSTER

    Befüllt ALLE Zeilen, zu denen Daten verfügbar sind
    """
    csv_data = [
        ['Anlage EÜR', euer_data['jahr']],
        ['', ''],
        ['BETRIEBSEINNAHMEN', ''],
        ['Zeile 11: Umsätze 19% USt', format_euro(euer_data['einnahmen']['zeile_11_umsatz_19'])],
        ['Zeile 12: Umsätze 7% USt', format_euro(euer_data['einnahmen']['zeile_12_umsatz_7'])],
        ['Zeile 14: Kleinunternehmer (§19 UStG)', format_euro(euer_data['einnahmen']['zeile_14_kleinunternehmer'])],
        ['Zeile 15: Innergemeinschaftl. Lieferungen', format_euro(euer_data['einnahmen']['zeile_15_eu_lieferungen'])],
        ['Zeile 21: Vereinnahmte USt', format_euro(euer_data['einnahmen']['zeile_21_ust_gesamt'])],
        ['', ''],
        ['BETRIEBSAUSGABEN', ''],
        ['Zeile 25: Wareneinkauf', format_euro(euer_data['ausgaben'].get(25, 0))],
        ['Zeile 26: Löhne & Gehälter', format_euro(euer_data['ausgaben'].get(26, 0))],  # Neu!
        ['Zeile 28: Raumkosten', format_euro(euer_data['ausgaben'].get(28, 0))],
        ['Zeile 32: Fahrtkosten', format_euro(euer_data['ausgaben'].get(32, 0))],
        ['Zeile 34: Werbekosten', format_euro(euer_data['ausgaben'].get(34, 0))],
        ['Zeile 36: Bürobedarf', format_euro(euer_data['ausgaben'].get(36, 0))],
        ['Zeile 40: Fortbildung', format_euro(euer_data['ausgaben'].get(40, 0))],
        ['Zeile 41: Versicherungen', format_euro(euer_data['ausgaben'].get(41, 0))],
        ['Zeile 43: Sonstige Ausgaben', format_euro(euer_data['ausgaben'].get(43, 0))],
        ['Zeile 45: AfA', format_euro(euer_data['afa']['zeile_45_afa'])],
        ['Zeile 60: Vorsteuer', format_euro(euer_data['ausgaben'].get(60, 0))],
        ['', ''],
        ['GEWINN', format_euro(euer_data['gewinn'])],
    ]

    return csv_data


def export_euer_vereinfacht(euer_data):
    """
    Exportiert vereinfachte EÜR für User/Jobcenter

    Übersichtlich: Nur Einnahmen - Ausgaben = Gewinn
    Keine detaillierte Zeilen-Aufschlüsselung
    """
    # Summen berechnen
    einnahmen_gesamt = sum(euer_data['einnahmen'].values())
    ausgaben_gesamt = sum(euer_data['ausgaben'].values()) + euer_data['afa']['zeile_45_afa']

    csv_data = [
        ['Einnahmen-Überschuss-Rechnung (vereinfacht)', euer_data['jahr']],
        ['', ''],
        ['EINNAHMEN', ''],
        ['Betriebseinnahmen gesamt', format_euro(einnahmen_gesamt)],
        ['', ''],
        ['AUSGABEN', ''],
        ['Betriebsausgaben gesamt', format_euro(ausgaben_gesamt)],
        ['  davon: Wareneinkauf', format_euro(euer_data['ausgaben'].get(25, 0))],
        ['  davon: Löhne & Gehälter', format_euro(euer_data['ausgaben'].get(26, 0))],
        ['  davon: Raumkosten', format_euro(euer_data['ausgaben'].get(28, 0))],
        ['  davon: Fahrtkosten', format_euro(euer_data['ausgaben'].get(32, 0))],
        ['  davon: Sonstige', format_euro(sum(euer_data['ausgaben'].values()) - euer_data['ausgaben'].get(25, 0) - euer_data['ausgaben'].get(26, 0) - euer_data['ausgaben'].get(28, 0) - euer_data['ausgaben'].get(32, 0))],
        ['  davon: AfA (Abschreibungen)', format_euro(euer_data['afa']['zeile_45_afa'])],
        ['', ''],
        ['════════════════════════════════════════', ''],
        ['GEWINN', format_euro(euer_data['gewinn'])],
        ['════════════════════════════════════════', ''],
    ]

    return csv_data
```

---

### **7.8 UI/UX**

**Navigation:**
```
Dashboard → Steuern → EÜR erstellen
```

**Formular:**
```
┌──────────────────────────────────────────────┐
│ Einnahmen-Überschuss-Rechnung (EÜR)         │
├──────────────────────────────────────────────┤
│                                              │
│  Jahr: [2025 ▼]                              │
│                                              │
│  ☑ Alle bezahlten Rechnungen einbeziehen    │
│  ☑ Kassenbuch-Einträge einbeziehen           │
│  ☑ AfA automatisch berechnen                 │
│                                              │
│  [ Berechnen ]                               │
│                                              │
├──────────────────────────────────────────────┤
│ ERGEBNIS:                                    │
│                                              │
│  Betriebseinnahmen:      45.890,00 €        │
│  Betriebsausgaben:      -23.450,00 €        │
│  AfA:                      -400,00 €        │
│  ────────────────────────────────────        │
│  GEWINN:                 22.040,00 €        │
│                                              │
│  EXPORT:                                     │
│  [ Amtliche EÜR (ELSTER) ]                   │
│  [ Vereinfachte EÜR (Jobcenter) ]            │
│  [ Detailansicht ]                           │
└──────────────────────────────────────────────┘
```

**Export-Dialog:**
```
┌──────────────────────────────────────────┐
│ EÜR exportieren                          │
├──────────────────────────────────────────┤
│                                          │
│ Variante:                                │
│ ● Amtliche Anlage EÜR                   │
│   Für: ELSTER / Finanzamt                │
│   Enthält: Alle EÜR-Zeilen mit Daten     │
│                                          │
│ ○ Vereinfachte EÜR                      │
│   Für: Eigene Übersicht / Jobcenter      │
│   Enthält: Einnahmen - Ausgaben = Gewinn │
│                                          │
│ Format:                                  │
│ ● CSV  ○ PDF  ○ Excel                    │
│                                          │
│    [Abbrechen]  [ Exportieren ]          │
└──────────────────────────────────────────┘
```

**Detailansicht:**
```
┌──────────────────────────────────────────────┐
│ EÜR 2025 - Detailansicht                     │
├──────────────────────────────────────────────┤
│                                              │
│ BETRIEBSEINNAHMEN                            │
│ ├─ Zeile 11: Umsätze 19% USt    38.500,00 € │
│ ├─ Zeile 12: Umsätze 7% USt      7.390,00 € │
│ └─ SUMME                         45.890,00 € │
│                                              │
│ BETRIEBSAUSGABEN                             │
│ ├─ Zeile 25: Wareneinkauf       12.300,00 € │
│ ├─ Zeile 28: Raumkosten          4.800,00 € │
│ ├─ Zeile 32: Fahrtkosten         2.150,00 € │
│ ├─ Zeile 36: Bürobedarf            890,00 € │
│ ├─ Zeile 40: Fortbildung           450,00 € │
│ ├─ Zeile 41: Versicherungen      1.260,00 € │
│ ├─ Zeile 43: Sonstige            1.600,00 € │
│ └─ SUMME                         23.450,00 € │
│                                              │
│ ABSCHREIBUNGEN (AfA)                         │
│ └─ Zeile 45: AfA                   400,00 € │
│    ├─ Laptop Dell XPS (03/2025)   400,00 € │
│                                              │
│ VORSTEUER                                    │
│ └─ Zeile 60: Vorsteuer           4.455,50 € │
│                                              │
│ ════════════════════════════════════════════ │
│ GEWINN                           22.040,00 € │
└──────────────────────────────────────────────┘
```

---

### **7.9 Validierung & Plausibilitätsprüfung**

**Vor Export:**
```python
def validate_euer(euer_data):
    """
    Prüft EÜR auf Plausibilität
    """
    warnings = []
    errors = []

    # 1. Gewinn plausibel?
    if euer_data['gewinn'] < 0:
        warnings.append({
            'typ': 'negativer_gewinn',
            'message': 'Verlust im Jahr - bitte prüfen',
            'betrag': euer_data['gewinn']
        })

    # 2. Alle Rechnungen bezahlt?
    unbezahlte = get_unbezahlte_rechnungen(euer_data['jahr'])
    if unbezahlte:
        warnings.append({
            'typ': 'unbezahlte_rechnungen',
            'message': f'{len(unbezahlte)} unbezahlte Rechnungen gefunden',
            'hinweis': 'Diese werden in der EÜR NICHT berücksichtigt (Zufluss-Prinzip)'
        })

    # 3. AfA vollständig?
    anlagegueter_ohne_afa = get_anlagegueter(
        jahr=euer_data['jahr'],
        anschaffungskosten__gt=1000,
        afa_angelegt=False
    )
    if anlagegueter_ohne_afa:
        errors.append({
            'typ': 'fehlende_afa',
            'message': f'{len(anlagegueter_ohne_afa)} Anlagegüter ohne AfA-Berechnung',
            'anlagegueter': [a.bezeichnung for a in anlagegueter_ohne_afa]
        })

    # 4. Kleinunternehmer: Keine Vorsteuer
    if user.ist_kleinunternehmer and euer_data['ausgaben'].get(60, 0) > 0:
        errors.append({
            'typ': 'kleinunternehmer_vorsteuer',
            'message': 'Kleinunternehmer können keine Vorsteuer abziehen',
            'betrag': euer_data['ausgaben'][60]
        })

    # 5. Umsatz > 600.000 € → Bilanzierungspflicht
    umsatz_gesamt = sum(euer_data['einnahmen'].values())
    if umsatz_gesamt > 600000:
        warnings.append({
            'typ': 'bilanzierungspflicht',
            'message': 'Umsatz > 600.000 € → Bilanzierungspflicht ab nächstem Jahr!',
            'umsatz': umsatz_gesamt
        })

    return {
        'errors': errors,
        'warnings': warnings,
        'kann_exportieren': len(errors) == 0
    }
```

---

### **7.10 Datenbank-Schema (Erweiterung)**

**Neue Tabelle: Anlagegüter**
```sql
CREATE TABLE anlagegueter (
    id INTEGER PRIMARY KEY,

    -- Stammdaten
    bezeichnung TEXT NOT NULL,  -- "Laptop Dell XPS 13"
    anschaffungsdatum DATE NOT NULL,
    anschaffungskosten DECIMAL(10,2) NOT NULL,  -- Netto

    -- AfA
    nutzungsdauer_jahre INTEGER NOT NULL,
    afa_methode TEXT DEFAULT 'linear',  -- 'linear', 'degressiv', 'pool'
    restbuchwert DECIMAL(10,2),

    -- Verknüpfung
    rechnung_id INTEGER,  -- Verknüpfung zur Eingangsrechnung

    -- Metadaten
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (rechnung_id) REFERENCES eingangsrechnungen(id)
);
```

**Neue Tabelle: EÜR-Export-Historie**
```sql
CREATE TABLE euer_exporte (
    id INTEGER PRIMARY KEY,
    jahr INTEGER NOT NULL,

    -- Berechnete Werte
    einnahmen_gesamt DECIMAL(10,2),
    ausgaben_gesamt DECIMAL(10,2),
    afa_gesamt DECIMAL(10,2),
    gewinn DECIMAL(10,2),

    -- Export
    export_format TEXT,  -- 'csv', 'pdf', 'elster_xml'
    export_datei TEXT,

    -- Metadaten
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### **7.11 Zusammenhang mit anderen Kategorien**

**Kategorie 1 (Kassenbuch):**
- Bareinnahmen/-ausgaben fließen in EÜR ein
- Zufluss-/Abfluss-Prinzip identisch

**Kategorie 2 (Rechnungen):**
- Ausgangsrechnungen (bezahlt!) → Betriebseinnahmen
- Eingangsrechnungen (bezahlt!) → Betriebsausgaben

**Kategorie 5 (Bank-Integration):**
- Zahlungsdaten → Zuordnung Rechnungen (bezahlt/unbezahlt)
- Automatischer Zahlungsabgleich essentiell für EÜR

**Kategorie 6 (UStVA):**
- **Gleiche Datengrundlage** (Ist-Versteuerung = Zufluss-Prinzip)
- Vorsteuer aus UStVA → EÜR Zeile 60

**Kategorie 4 (DATEV-Export):**
- EÜR-Daten können als DATEV-CSV exportiert werden
- Steuerberater nutzt für Jahresabschluss

---

**Status:** ✅ Kategorie 7 definiert - EÜR-Berechnung (Hybrid-Ansatz: MVP berechnet Werte, Export als CSV/PDF für manuelle ELSTER-Eingabe; v2.0: ELSTER-XML mit direkter Übermittlung), Zufluss-/Abfluss-Prinzip, Betriebseinnahmen/-ausgaben, AfA-Verwaltung, GWG-Regelung, Validierung, Datenbank-Schema.

---

## **Kategorie 8: Stammdaten-Erfassung**

### **8.1 Übersicht**

Stammdaten sind **grundlegende Informationen**, die wiederholt verwendet werden:

**Arten von Stammdaten in RechnungsPilot:**

1. **User-/Firmen-Stammdaten** (Pflicht)
   - Eigene Firma/Freiberufler-Daten
   - Finanzamt, Steuernummer, USt-IdNr.
   - Bank-Verbindungen

2. **Kategorien** (Pflicht)
   - Einnahmen-Kategorien
   - Ausgaben-Kategorien
   - EÜR-Zuordnung

3. **EU-Länder** (für EU-Handel)
   - Ländercodes, MwSt-Sätze
   - USt-IdNr.-Formate

4. **Bankkonten** (für Bank-Integration)
   - IBAN, BIC, Bankname
   - CSV-Format-Zuordnung

5. **Kundenstamm** (📋 **OFFEN** - Community-Entscheidung)
   - Siehe `discussion-kundenstamm.md`
   - Option A: Mit Kundenstamm (v1.0)
   - Option B: Ohne Kundenstamm (v1.0)
   - Option C: Hybrid (optional)

---

### **8.2 User-/Firmen-Stammdaten**

**Zweck:**
- Identifikation der Firma/Freiberufler
- Für Rechnungsvorlagen (Absender)
- Für DATEV/AGENDA-Export
- Für UStVA/EÜR (eigene USt-IdNr., Finanzamt)

**Felder:**

#### **Basis-Informationen:**
```python
class UserStammdaten:
    # Firma/Person
    firmenname: str  # "Musterfirma GmbH" oder "Max Mustermann"
    rechtsform: str  # "Einzelunternehmen", "GbR", "GmbH", "Freiberufler"
    inhaber_name: str  # Bei Einzelunternehmen/Freiberufler

    # Adresse
    strasse: str
    hausnummer: str
    plz: str
    ort: str
    land: str  # ISO 3166-1 Alpha-2, default 'DE'

    # Kontakt
    telefon: str
    email: str
    website: str

    # Steuerliche Daten
    steuernummer: str  # "12/345/67890"
    ust_idnr: str  # "DE123456789"
    finanzamt_name: str  # "Finanzamt Oldenburg"
    finanzamt_nummer: str  # "2360"

    # Bank
    iban: str
    bic: str
    bankname: str

    # Steuerliche Einordnung
    ist_kleinunternehmer: bool  # § 19 UStG
    versteuerungsart: str  # 'ist' oder 'soll'
    bezieht_transferleistungen: bool  # ALG II/Bürgergeld → Ist-Versteuerung Pflicht!

    # E-Rechnung
    leitweg_id: str  # Für Rechnungen an öffentliche Auftraggeber (optional)
```

**Validierung:**

```python
def validate_user_stammdaten():
    """
    Prüft Pflichtfelder und Plausibilität
    """
    errors = []

    # 1. Pflichtfelder
    required = ['firmenname', 'strasse', 'plz', 'ort', 'email']
    for field in required:
        if not getattr(user, field):
            errors.append({
                'field': field,
                'message': f'{field} ist Pflichtfeld'
            })

    # 2. Steuernummer oder USt-IdNr. (mindestens eines)
    if not user.steuernummer and not user.ust_idnr:
        errors.append({
            'field': 'steuernummer',
            'message': 'Steuernummer ODER USt-IdNr. erforderlich'
        })

    # 3. USt-IdNr.-Format (wenn vorhanden)
    if user.ust_idnr:
        if not re.match(r'^DE[0-9]{9}$', user.ust_idnr):
            errors.append({
                'field': 'ust_idnr',
                'message': 'USt-IdNr. muss Format "DE123456789" haben'
            })

    # 4. Kleinunternehmer: Keine USt-IdNr. nötig
    if user.ist_kleinunternehmer and user.ust_idnr:
        # Warnung, kein Fehler (kann beides haben)
        warnings.append({
            'field': 'ist_kleinunternehmer',
            'message': 'Kleinunternehmer haben meist keine USt-IdNr.'
        })

    # 5. Transferleistungen → Ist-Versteuerung Pflicht
    if user.bezieht_transferleistungen and user.versteuerungsart == 'soll':
        errors.append({
            'field': 'versteuerungsart',
            'message': 'Bei Bezug von Transferleistungen ist Ist-Versteuerung Pflicht (SGBII § 11)'
        })

    # 6. IBAN-Format (wenn vorhanden)
    if user.iban:
        if not validate_iban(user.iban):
            errors.append({
                'field': 'iban',
                'message': 'IBAN hat ungültiges Format'
            })

    return {
        'errors': errors,
        'valid': len(errors) == 0
    }
```

**UI - Einrichtungs-Assistent (Setup-Wizard):**

```
┌─────────────────────────────────────────────────┐
│ RechnungsPilot - Ersteinrichtung (Schritt 1/4) │
├─────────────────────────────────────────────────┤
│                                                 │
│ FIRMA / FREIBERUFLER                            │
│                                                 │
│  Firmenname:  [___________________________]    │
│  Rechtsform:  [Freiberufler ▼]                 │
│               □ Einzelunternehmen               │
│               □ GbR                             │
│               ● Freiberufler                    │
│               □ GmbH                            │
│                                                 │
│  Inhaber:     [Max Mustermann____________]     │
│                                                 │
│ ADRESSE                                         │
│                                                 │
│  Straße:      [Musterstraße______________]     │
│  Hausnummer:  [42__]                            │
│  PLZ:         [26121]  Ort: [Oldenburg____]    │
│  Land:        [Deutschland ▼]                   │
│                                                 │
│ KONTAKT                                         │
│                                                 │
│  E-Mail:      [max@example.com___________]     │
│  Telefon:     [0441 12345678_____________]     │
│  Website:     [www.example.com___________]     │
│                                                 │
│              [Zurück]        [Weiter →]         │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ RechnungsPilot - Ersteinrichtung (Schritt 2/4) │
├─────────────────────────────────────────────────┤
│                                                 │
│ STEUERLICHE DATEN                               │
│                                                 │
│  Steuernummer:    [12/345/67890__________]     │
│  USt-IdNr.:       [DE123456789___________]     │
│                   [ Validieren ]  ✅ Gültig     │
│                                                 │
│  Finanzamt:       [Finanzamt Oldenburg___]     │
│  FA-Nummer:       [2360]                        │
│                                                 │
│ STEUERLICHE EINORDNUNG                          │
│                                                 │
│  ☑ Kleinunternehmer (§ 19 UStG)                │
│    → Keine Umsatzsteuer auf Rechnungen         │
│    → Kein Vorsteuerabzug                        │
│                                                 │
│  Versteuerungsart:                              │
│    ● Ist-Versteuerung (Zufluss-Prinzip)        │
│    ○ Soll-Versteuerung (Rechnungsdatum)        │
│                                                 │
│  ⚠️  WICHTIG:                                   │
│  ☑ Ich beziehe Transferleistungen (ALG II)     │
│    → Ist-Versteuerung ist PFLICHT (SGBII § 11) │
│                                                 │
│ EU-HANDEL                                       │
│                                                 │
│  ☑ Ich plane EU-Geschäft                       │
│    → USt-IdNr. erforderlich                     │
│    → Siehe Kategorie 6.2 (EU-Handel)           │
│                                                 │
│              [← Zurück]      [Weiter →]         │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ RechnungsPilot - Ersteinrichtung (Schritt 3/4) │
├─────────────────────────────────────────────────┤
│                                                 │
│ BANKVERBINDUNG                                  │
│                                                 │
│  IBAN:      [DE89370400440532013000______]     │
│             ✅ Gültig                           │
│  BIC:       [COBADEFFXXX_________________]     │
│  Bankname:  [Commerzbank_________________]     │
│                                                 │
│  💡 Diese Daten erscheinen auf Rechnungen      │
│                                                 │
│              [← Zurück]      [Weiter →]         │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ RechnungsPilot - Ersteinrichtung (Schritt 4/4) │
├─────────────────────────────────────────────────┤
│                                                 │
│ ZUSAMMENFASSUNG                                 │
│                                                 │
│ ✅ Firma:        Max Mustermann (Freiberufler) │
│ ✅ Adresse:      Musterstraße 42, 26121 OL     │
│ ✅ Steuernr.:    12/345/67890                   │
│ ✅ USt-IdNr.:    DE123456789 (validiert)        │
│ ✅ Finanzamt:    Finanzamt Oldenburg (2360)     │
│ ✅ Bank:         DE89...3000 (Commerzbank)      │
│                                                 │
│ EINSTELLUNGEN:                                  │
│ ✅ Kleinunternehmer (§ 19 UStG)                │
│ ✅ Ist-Versteuerung (Pflicht wegen ALG II)     │
│ ✅ EU-Geschäft geplant                         │
│                                                 │
│              [← Zurück]    [Abschließen]        │
└─────────────────────────────────────────────────┘
```

---

### **8.3 Kategorien (Einnahmen/Ausgaben)**

**Zweck:**
- Einnahmen/Ausgaben kategorisieren
- Automatische EÜR-Zeilen-Zuordnung
- DATEV-Konten-Mapping
- Auswertungen (Kostenstellen)

**Standardkategorien (vordefiniert):**

#### **Einnahmen-Kategorien:**
```python
EINNAHMEN_KATEGORIEN = [
    {'id': 1, 'name': 'Warenverkauf', 'euer_zeile': 11, 'datev_konto': 8400},
    {'id': 2, 'name': 'Dienstleistungen', 'euer_zeile': 11, 'datev_konto': 8400},
    {'id': 3, 'name': 'Provisionen', 'euer_zeile': 11, 'datev_konto': 8500},
    {'id': 4, 'name': 'Erstattungen', 'euer_zeile': 11, 'datev_konto': 8900},
    {'id': 5, 'name': 'Sonstige Einnahmen', 'euer_zeile': 11, 'datev_konto': 8900},
]
```

#### **Ausgaben-Kategorien:**
```python
AUSGABEN_KATEGORIEN = [
    {'id': 10, 'name': 'Wareneinkauf', 'euer_zeile': 25, 'datev_konto': 3400},
    {'id': 11, 'name': 'Löhne & Gehälter', 'euer_zeile': 26, 'datev_konto': 4120},  # Auch für Einzelunternehmer!
    {'id': 12, 'name': 'Raumkosten (Miete)', 'euer_zeile': 28, 'datev_konto': 4210},
    {'id': 13, 'name': 'Strom, Gas, Wasser', 'euer_zeile': 28, 'datev_konto': 4240},
    {'id': 14, 'name': 'Telefon, Internet', 'euer_zeile': 28, 'datev_konto': 4910},
    {'id': 15, 'name': 'KFZ-Kosten (Benzin)', 'euer_zeile': 32, 'datev_konto': 4530},
    {'id': 16, 'name': 'KFZ-Versicherung', 'euer_zeile': 32, 'datev_konto': 4570},
    {'id': 17, 'name': 'Fahrtkosten (ÖPNV)', 'euer_zeile': 32, 'datev_konto': 4670},
    {'id': 18, 'name': 'Werbekosten', 'euer_zeile': 34, 'datev_konto': 4600},
    {'id': 19, 'name': 'Bürobedarf', 'euer_zeile': 36, 'datev_konto': 4910},
    {'id': 20, 'name': 'Software, Lizenzen', 'euer_zeile': 36, 'datev_konto': 4940},
    {'id': 21, 'name': 'Fortbildung', 'euer_zeile': 40, 'datev_konto': 4945},
    {'id': 22, 'name': 'Versicherungen (betr.)', 'euer_zeile': 41, 'datev_konto': 4360},
    {'id': 23, 'name': 'Steuerberatung', 'euer_zeile': 43, 'datev_konto': 4970},
    {'id': 24, 'name': 'Sonstige Ausgaben', 'euer_zeile': 43, 'datev_konto': 4980},
]
```

**User kann eigene Kategorien hinzufügen:**

```python
class Kategorie:
    id: int
    name: str  # "Marketing-Flyer"
    typ: str  # 'einnahme' oder 'ausgabe'
    euer_zeile: int  # 34 (Werbekosten)
    datev_konto: int  # 4600 (Werbekosten)
    ist_standard: bool  # False (custom)
    erstellt_am: datetime
```

**UI - Kategorien verwalten:**

```
┌──────────────────────────────────────────────┐
│ Einstellungen → Kategorien                   │
├──────────────────────────────────────────────┤
│                                              │
│ EINNAHMEN-KATEGORIEN                         │
│                                              │
│ ID │ Name                 │ EÜR │ DATEV     │
│────┼──────────────────────┼─────┼──────────│
│  1 │ Warenverkauf         │  11 │ 8400  🔒 │
│  2 │ Dienstleistungen     │  11 │ 8400  🔒 │
│  3 │ Provisionen          │  11 │ 8500  🔒 │
│  4 │ Erstattungen         │  11 │ 8900  🔒 │
│  5 │ Sonstige Einnahmen   │  11 │ 8900  🔒 │
│────┼──────────────────────┼─────┼──────────│
│  6 │ Online-Kurse         │  11 │ 8400  ✏️ │
│                                              │
│ [ + Neue Kategorie ]                         │
│                                              │
│ AUSGABEN-KATEGORIEN                          │
│                                              │
│ ID │ Name                 │ EÜR │ DATEV     │
│────┼──────────────────────┼─────┼──────────│
│ 10 │ Wareneinkauf         │  25 │ 3400  🔒 │
│ 11 │ Raumkosten (Miete)   │  28 │ 4210  🔒 │
│ 12 │ Strom, Gas, Wasser   │  28 │ 4240  🔒 │
│ ...│ ...                  │ ... │ ...   🔒 │
│ 23 │ Sonstige Ausgaben    │  43 │ 4980  🔒 │
│────┼──────────────────────┼─────┼──────────│
│ 30 │ Hosting-Kosten       │  43 │ 4980  ✏️ │
│ 31 │ Bücher (Fachliteratur)│ 40 │ 4945  ✏️ │
│                                              │
│ [ + Neue Kategorie ]                         │
│                                              │
│ 🔒 = Standard (nicht editierbar)             │
│ ✏️  = Custom (editierbar/löschbar)           │
└──────────────────────────────────────────────┘
```

---

### **8.4 EU-Länder-Stammdaten**

**Zweck:**
- EU-Handel (Kategorie 6.2)
- Validierung USt-IdNr.-Format
- MwSt-Sätze für Reverse Charge

**Datenbank:**
```sql
CREATE TABLE eu_laender (
    code TEXT PRIMARY KEY,  -- 'BE' (ISO 3166-1 Alpha-2)
    name_de TEXT,  -- 'Belgien'
    name_en TEXT,  -- 'Belgium'

    -- MwSt-Sätze
    mwst_satz_standard DECIMAL(5,2),  -- 21.0
    mwst_satz_reduziert DECIMAL(5,2),  -- 6.0

    -- USt-IdNr.-Format
    ust_idnr_prefix TEXT,  -- 'BE'
    ust_idnr_regex TEXT,  -- '^BE[0-9]{10}$'
    ust_idnr_beispiel TEXT,  -- 'BE0123456789'

    -- EU-Mitglied seit
    eu_beitritt_jahr INTEGER,  -- 1957

    -- Aktiv
    ist_eu_mitglied BOOLEAN DEFAULT 1,  -- True (falls Land austritt)

    -- Metadaten
    aktualisiert_am TIMESTAMP
);
```

**Vorbefüllung (Beispiel):**
```python
EU_LAENDER_INITIAL = [
    {
        'code': 'AT', 'name_de': 'Österreich', 'name_en': 'Austria',
        'mwst_satz_standard': 20.0, 'mwst_satz_reduziert': 10.0,
        'ust_idnr_prefix': 'AT', 'ust_idnr_regex': r'^ATU[0-9]{8}$',
        'ust_idnr_beispiel': 'ATU12345678', 'eu_beitritt_jahr': 1995
    },
    {
        'code': 'BE', 'name_de': 'Belgien', 'name_en': 'Belgium',
        'mwst_satz_standard': 21.0, 'mwst_satz_reduziert': 6.0,
        'ust_idnr_prefix': 'BE', 'ust_idnr_regex': r'^BE[0-9]{10}$',
        'ust_idnr_beispiel': 'BE0123456789', 'eu_beitritt_jahr': 1957
    },
    {
        'code': 'FR', 'name_de': 'Frankreich', 'name_en': 'France',
        'mwst_satz_standard': 20.0, 'mwst_satz_reduziert': 5.5,
        'ust_idnr_prefix': 'FR', 'ust_idnr_regex': r'^FR[0-9A-Z]{2}[0-9]{9}$',
        'ust_idnr_beispiel': 'FR12345678901', 'eu_beitritt_jahr': 1957
    },
    # ... weitere 24 EU-Länder
]
```

**Verwendung:**
```python
def validate_ust_idnr_format(ust_idnr, land_code):
    """
    Prüft USt-IdNr. gegen Länder-Format
    """
    land = get_eu_land(land_code)

    if not land:
        return False, f"Land {land_code} nicht in EU-Stammdaten"

    if not re.match(land.ust_idnr_regex, ust_idnr):
        return False, f"Format ungültig. Erwartet: {land.ust_idnr_beispiel}"

    return True, "Format OK"


def get_reverse_charge_mwst(land_code):
    """
    Holt MwSt-Satz des Lieferlands für Reverse Charge
    """
    land = get_eu_land(land_code)
    return land.mwst_satz_standard  # Z.B. 21% für Belgien
```

---

### **8.5 Bankkonten-Stammdaten**

**Zweck:**
- Bank-CSV-Import (Kategorie 5)
- Zuordnung CSV-Format → Parser
- Mehrere Konten verwalten

**Datenbank:**
```sql
CREATE TABLE bankkonten (
    id INTEGER PRIMARY KEY,

    -- Kontodaten
    kontoname TEXT NOT NULL,  -- "Geschäftskonto Commerzbank"
    iban TEXT NOT NULL UNIQUE,
    bic TEXT,
    bankname TEXT,

    -- CSV-Import
    bank_typ TEXT,  -- 'commerzbank', 'sparkasse', 'dkb', 'paypal'
    csv_format TEXT,  -- 'mt940', 'camt_v8', 'standard'
    csv_delimiter TEXT DEFAULT ';',  -- ';', ',', '\t'
    csv_encoding TEXT DEFAULT 'ISO-8859-1',  -- 'UTF-8', 'ISO-8859-1'

    -- Status
    ist_hauptkonto BOOLEAN DEFAULT 0,
    ist_aktiv BOOLEAN DEFAULT 1,

    -- Saldo
    aktueller_saldo DECIMAL(10,2),
    saldo_datum DATE,

    -- Metadaten
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**UI - Bankkonten verwalten:**

```
┌─────────────────────────────────────────────────┐
│ Einstellungen → Bankkonten                      │
├─────────────────────────────────────────────────┤
│                                                 │
│ GESCHÄFTSKONTEN                                 │
│                                                 │
│ ┌─────────────────────────────────────────────┐ │
│ │ ⭐ Hauptkonto: Commerzbank                   │ │
│ │                                             │ │
│ │ IBAN:     DE89 3704 0044 0532 0130 00      │ │
│ │ BIC:      COBADEFFXXX                       │ │
│ │ Bank:     Commerzbank                       │ │
│ │                                             │ │
│ │ CSV-Import:                                 │ │
│ │ - Format:    Commerzbank Standard           │ │
│ │ - Delimiter: ; (Semikolon)                  │ │
│ │ - Encoding:  ISO-8859-1                     │ │
│ │                                             │ │
│ │ Saldo:       8.450,23 € (Stand: 06.12.25)  │ │
│ │                                             │ │
│ │ [ Bearbeiten ]  [ CSV importieren ]         │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ ┌─────────────────────────────────────────────┐ │
│ │ PayPal Geschäftskonto                       │ │
│ │                                             │ │
│ │ E-Mail:   fibu@musterfirma.de               │ │
│ │ Typ:      PayPal                            │ │
│ │                                             │ │
│ │ CSV-Import:                                 │ │
│ │ - Format:    PayPal Aktivitätsbericht       │ │
│ │ - Delimiter: , (Komma)                      │ │
│ │ - Encoding:  UTF-8                          │ │
│ │                                             │ │
│ │ Saldo:       234,56 € (Stand: 06.12.25)    │ │
│ │                                             │ │
│ │ [ Bearbeiten ]  [ CSV importieren ]         │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ [ + Bankkonto hinzufügen ]                      │
└─────────────────────────────────────────────────┘
```

**Hinzufügen-Dialog:**

```
┌─────────────────────────────────────────┐
│ Neues Bankkonto hinzufügen              │
├─────────────────────────────────────────┤
│                                         │
│ Kontoname:  [Geschäftskonto_________]  │
│                                         │
│ IBAN:       [DE89________________]     │
│             [ Validieren ] ✅ Gültig   │
│ BIC:        [COBADEFFXXX_________]     │
│ Bankname:   [Commerzbank_________]     │
│                                         │
│ CSV-IMPORT-EINSTELLUNGEN                │
│                                         │
│ Bank/Typ:   [Commerzbank ▼]            │
│             - Commerzbank               │
│             - Sparkasse (MT940)         │
│             - Sparkasse (CAMT V8)       │
│             - DKB                       │
│             - PayPal                    │
│             - Andere...                 │
│                                         │
│ Format:     [Standard ▼]               │
│ Delimiter:  [; (Semikolon) ▼]          │
│ Encoding:   [ISO-8859-1 ▼]             │
│                                         │
│ ☑ Als Hauptkonto festlegen             │
│                                         │
│        [Abbrechen]  [ Speichern ]      │
└─────────────────────────────────────────┘
```

---

### **8.6 Kontenrahmen (SKR03 / SKR04)**

**Zweck:**
- DATEV-Export korrekt zuordnen
- Buchungskonten für Einnahmen/Ausgaben
- Unterschied zwischen Gewerbetreibenden und Freiberuflern

**Was ist der Kontenrahmen?**
- Standardisierte Nummernstruktur für Buchhaltungskonten
- In Deutschland: SKR03 oder SKR04 (DATEV-Standard)

**Unterschied:**

| Aspekt | SKR03 | SKR04 |
|--------|-------|-------|
| **Zielgruppe** | Gewerbetreibende, Handwerk, Handel | Freiberufler, Dienstleister |
| **Struktur** | Prozessgliederung (nach Ablauf) | Abschlussgliederung (nach Bilanz) |
| **Beispiel** | Konto 8400: Erlöse 19% USt | Konto 4400: Erlöse 19% USt |
| **Verbreitung** | Häufiger | Seltener |

**Auswahl im Setup-Wizard:**

```
┌─────────────────────────────────────────┐
│ Kontenrahmen auswählen                  │
├─────────────────────────────────────────┤
│                                         │
│ Welchen Kontenrahmen nutzen Sie?       │
│                                         │
│ ● SKR03 (Prozessgliederung)            │
│   Empfohlen für:                        │
│   - Gewerbetreibende                    │
│   - Handel, Handwerk                    │
│   - Produktion                          │
│                                         │
│ ○ SKR04 (Abschlussgliederung)          │
│   Empfohlen für:                        │
│   - Freiberufler                        │
│   - Dienstleister                       │
│   - Beratung, IT, Kreative              │
│                                         │
│ 💡 Diese Einstellung kann später        │
│    geändert werden.                     │
│                                         │
│          [Zurück]  [Weiter →]           │
└─────────────────────────────────────────┘
```

**Datenbank:**
```sql
ALTER TABLE user_settings ADD COLUMN kontenrahmen TEXT DEFAULT 'SKR03';
-- 'SKR03' oder 'SKR04'
```

**Implementierung:**
```python
def get_datev_konto(kategorie_name, kontenrahmen='SKR03'):
    """
    Gibt DATEV-Konto für Kategorie zurück
    """
    mapping = {
        'Warenverkauf': {
            'SKR03': 8400,
            'SKR04': 4400
        },
        'Bürobedarf': {
            'SKR03': 4910,
            'SKR04': 6815
        },
        # ... weitere Kategorien
    }

    return mapping[kategorie_name][kontenrahmen]
```

**Wechsel später möglich:**
```python
def switch_kontenrahmen(alt, neu):
    """
    Wechselt Kontenrahmen für alle Kategorien
    """
    kategorien = get_all_kategorien()

    for kat in kategorien:
        kat.datev_konto = get_datev_konto(kat.name, neu)
        kat.save()

    user_settings.kontenrahmen = neu
    user_settings.save()

    return f"Kontenrahmen gewechselt: {alt} → {neu}"
```

---

### **8.7 Geschäftsjahr**

**Zweck:**
- Zeiträume für EÜR, UStVA, Auswertungen
- Standard: Kalenderjahr (01.01. - 31.12.)
- Abweichendes Wirtschaftsjahr möglich (z.B. Landwirtschaft)

**Standard: Kalenderjahr**
```python
class UserSettings:
    geschaeftsjahr_start: str = '01-01'  # MM-DD
    geschaeftsjahr_ende: str = '12-31'   # MM-DD
```

**Abweichendes Wirtschaftsjahr (Beispiel):**
```
Landwirtschaft: 01.07. - 30.06.
→ geschaeftsjahr_start = '07-01'
→ geschaeftsjahr_ende = '06-30'
```

**UI - Setup-Wizard:**
```
┌─────────────────────────────────────────┐
│ Geschäftsjahr festlegen                 │
├─────────────────────────────────────────┤
│                                         │
│ ● Kalenderjahr (01.01. - 31.12.)       │
│   Standard für die meisten Unternehmen │
│                                         │
│ ○ Abweichendes Wirtschaftsjahr         │
│   Beginn: [01] . [07] (TT.MM)          │
│   Ende:   [30] . [06] (TT.MM)          │
│                                         │
│   Beispiel: Landwirtschaft (01.07.-30.06.)│
│                                         │
│ 💡 Wichtig für EÜR und Jahresabschluss │
│                                         │
│          [Zurück]  [Weiter →]           │
└─────────────────────────────────────────┘
```

**Verwendung:**
```python
def get_geschaeftsjahr(jahr):
    """
    Gibt Start- und End-Datum des Geschäftsjahres zurück
    """
    user = get_user_settings()

    if user.geschaeftsjahr_start == '01-01':
        # Kalenderjahr
        return (
            date(jahr, 1, 1),
            date(jahr, 12, 31)
        )
    else:
        # Abweichendes Wirtschaftsjahr
        start_month, start_day = user.geschaeftsjahr_start.split('-')
        ende_month, ende_day = user.geschaeftsjahr_ende.split('-')

        start = date(jahr, int(start_month), int(start_day))

        # Ende kann im Folgejahr sein
        if int(ende_month) < int(start_month):
            ende = date(jahr + 1, int(ende_month), int(ende_day))
        else:
            ende = date(jahr, int(ende_month), int(ende_day))

        return (start, ende)


def calculate_euer(jahr):
    """
    Berechnet EÜR für Geschäftsjahr
    """
    start, ende = get_geschaeftsjahr(jahr)

    rechnungen = get_rechnungen(
        zahlungsdatum__gte=start,
        zahlungsdatum__lte=ende
    )
    # ... Berechnung
```

---

### **8.8 Lieferantenstammdaten**

**Zweck:**
- Wiederholte Lieferanten (z.B. Vermieter, Telefon, Strom)
- Autocomplete bei Eingangsrechnungen
- Ähnlich wie Kundenstamm, aber minimalistischer

**Datenbank:**
```sql
CREATE TABLE lieferanten (
    id INTEGER PRIMARY KEY,

    -- Stammdaten
    lieferantennummer TEXT UNIQUE,  -- "L-001" (automatisch)
    name TEXT NOT NULL,  -- "Deutsche Telekom AG"

    -- Adresse
    strasse TEXT,
    hausnummer TEXT,
    plz TEXT,
    ort TEXT,
    land TEXT DEFAULT 'DE',

    -- Kontakt
    email TEXT,
    telefon TEXT,
    website TEXT,

    -- Steuerlich
    ust_idnr TEXT,  -- Bei EU-Lieferanten wichtig (Reverse Charge)

    -- Standard-Kategorie (optional)
    standard_kategorie_id INTEGER,  -- z.B. "Telefon/Internet" für Telekom

    -- Metadaten
    notizen TEXT,
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Statistiken
    anzahl_rechnungen INTEGER DEFAULT 0,
    ausgaben_gesamt DECIMAL(10,2) DEFAULT 0.00,

    FOREIGN KEY (standard_kategorie_id) REFERENCES kategorien(id)
);
```

**UI - Lieferanten verwalten:**
```
┌────────────────────────────────────────────┐
│ Stammdaten → Lieferanten                   │
├────────────────────────────────────────────┤
│                                            │
│ [ + Neuer Lieferant ]        [🔍 Suchen]  │
│                                            │
│ Nr.  │ Name                │ Kategorie     │
│──────┼─────────────────────┼──────────────│
│ L-001│ Vermieter Müller    │ Raumkosten   │
│ L-002│ Deutsche Telekom AG │ Telefon      │
│ L-003│ Amazon Business     │ Bürobedarf   │
│ L-004│ Shell Tankstelle    │ Fahrtkosten  │
│ L-005│ Lieferant BE GmbH   │ Wareneinkauf │
│      │ (BE0123456789)      │ [EU]         │
│                                            │
│ Gesamt: 5 Lieferanten                      │
└────────────────────────────────────────────┘
```

**Verknüpfung mit Eingangsrechnungen:**
```python
class Eingangsrechnung:
    id: int
    lieferant_id: int  # OPTIONAL - Verknüpfung zu Lieferant
    lieferant_name: str  # Immer ausgefüllt (auch ohne Stammdaten)
    # ... andere Felder
```

**Autocomplete beim Erfassen:**
```
┌────────────────────────────────────────┐
│ Eingangsrechnung erfassen              │
├────────────────────────────────────────┤
│                                        │
│ Lieferant: [Deut____________]         │
│            ┌──────────────────────┐   │
│            │ Deutsche Telekom AG  │   │
│            │ (L-002)              │   │
│            │ Kategorie: Telefon   │   │
│            └──────────────────────┘   │
│                                        │
│ [✓] = Enter drücken übernimmt          │
└────────────────────────────────────────┘
```

**Hybrid-Ansatz (wie Kundenstamm):**
- Optional: Lieferant aus Stamm wählen
- Oder: Manuell Name eingeben
- Bei wiederholtem Lieferanten: "Als Lieferant speichern?" anbieten

---

### **8.9 Produktstammdaten (für Rechnungsschreib-Modul)**

**Zweck:**
- Für späteres Modul "Ausgangsrechnungen erstellen"
- Wiederverwendbare Produkte/Dienstleistungen
- Schnelles Erstellen von Rechnungen

**Status:** 📋 **Für v2.0 geplant** (NICHT in MVP v1.0)

**Begründung:**
- MVP v1.0: Nur Rechnungen VERWALTEN (nicht erstellen)
- Rechnungsschreiben über LibreOffice/HTML-Vorlagen
- Produktstamm wird erst relevant, wenn internes Rechnungsschreib-Tool kommt

**Vorbereitung - Datenbank-Schema:**
```sql
CREATE TABLE produkte (
    id INTEGER PRIMARY KEY,

    -- Stammdaten
    artikelnummer TEXT UNIQUE,  -- "ART-001" (manuell oder automatisch)
    bezeichnung TEXT NOT NULL,  -- "Beratungsstunde"
    beschreibung TEXT,  -- Längerer Text für Rechnung

    -- Typ
    typ TEXT,  -- 'dienstleistung', 'ware', 'pauschale'

    -- Preis
    einzelpreis_netto DECIMAL(10,2),
    umsatzsteuer_satz DECIMAL(5,2) DEFAULT 19.0,
    einzelpreis_brutto DECIMAL(10,2),

    -- Einheit
    einheit TEXT DEFAULT 'Stück',  -- 'Stunde', 'Stück', 'Pauschal', 'kg', etc.

    -- Kategorie
    kategorie_id INTEGER,  -- Zuordnung zu Einnahmen-Kategorie

    -- Aktiv
    ist_aktiv BOOLEAN DEFAULT 1,

    -- Metadaten
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (kategorie_id) REFERENCES kategorien(id)
);
```

**Beispiel-Produkte:**
```python
PRODUKTE_BEISPIELE = [
    {
        'artikelnummer': 'DL-001',
        'bezeichnung': 'Beratungsstunde',
        'typ': 'dienstleistung',
        'einzelpreis_netto': 80.00,
        'umsatzsteuer_satz': 19.0,
        'einzelpreis_brutto': 95.20,
        'einheit': 'Stunde'
    },
    {
        'artikelnummer': 'ART-001',
        'bezeichnung': 'Laptop Dell XPS 13',
        'typ': 'ware',
        'einzelpreis_netto': 1000.00,
        'umsatzsteuer_satz': 19.0,
        'einzelpreis_brutto': 1190.00,
        'einheit': 'Stück'
    },
    {
        'artikelnummer': 'PAUS-001',
        'bezeichnung': 'Website-Erstellung Pauschal',
        'typ': 'pauschale',
        'einzelpreis_netto': 2500.00,
        'umsatzsteuer_satz': 19.0,
        'einzelpreis_brutto': 2975.00,
        'einheit': 'Pauschal'
    }
]
```

**UI-Konzept (für v2.0):**
```
┌────────────────────────────────────────────┐
│ Stammdaten → Produkte / Dienstleistungen   │
├────────────────────────────────────────────┤
│                                            │
│ [ + Neues Produkt ]          [🔍 Suchen]  │
│                                            │
│ Art.-Nr. │ Bezeichnung       │ Preis      │
│──────────┼───────────────────┼───────────│
│ DL-001   │ Beratungsstunde   │ 95,20 €   │
│ ART-001  │ Laptop Dell XPS   │ 1.190,00 €│
│ PAUS-001 │ Website-Erstellung│ 2.975,00 €│
│                                            │
│ Gesamt: 3 Produkte                         │
└────────────────────────────────────────────┘
```

**Verwendung in v2.0 (Ausgangsrechnung erstellen):**
```
┌────────────────────────────────────────┐
│ Ausgangsrechnung erstellen             │
├────────────────────────────────────────┤
│                                        │
│ Kunde: [Belgischer Kunde ▼]           │
│                                        │
│ POSITIONEN:                            │
│                                        │
│ Pos │ Artikel        │ Anz │ Preis    │
│─────┼────────────────┼─────┼─────────│
│  1  │ [Beratung▼]    │ 10  │ 952,00 €│
│     │ Beratungsstunde│     │          │
│                                        │
│ [ + Position hinzufügen ]              │
│                                        │
│ Gesamt netto:     800,00 €             │
│ USt 19%:          152,00 €             │
│ ─────────────────────────────          │
│ Gesamt brutto:    952,00 €             │
│                                        │
│      [Abbrechen]  [ Speichern ]        │
└────────────────────────────────────────┘
```

**Entscheidung für v1.0:**
- ❌ NICHT in Setup-Wizard
- ❌ NICHT in Stammdaten-Erfassung
- ✅ Datenbank-Schema vorbereitet (Tabelle existiert, aber leer)
- ✅ UI/Funktionalität für v2.0

---

### **8.10 Kundenstamm (OFFEN - Community-Entscheidung)**

**Status:** 📋 **Ausstehende Entscheidung**

**Siehe:** `discussion-kundenstamm.md`

**Optionen:**

#### **Option A: MIT Kundenstamm (v1.0)**

**Datenbank:**
```sql
CREATE TABLE kunden (
    id INTEGER PRIMARY KEY,

    -- Stammdaten
    kundennummer TEXT UNIQUE,  -- "K-001" (automatisch)
    typ TEXT,  -- 'privat', 'firma'

    -- Person
    anrede TEXT,  -- 'Herr', 'Frau', 'Divers'
    vorname TEXT,
    nachname TEXT,

    -- Firma (nur wenn typ='firma')
    firmenname TEXT,
    rechtsform TEXT,  -- "GmbH", "AG", etc.

    -- Adresse
    strasse TEXT,
    hausnummer TEXT,
    plz TEXT,
    ort TEXT,
    land TEXT DEFAULT 'DE',

    -- Kontakt
    email TEXT,
    telefon TEXT,
    website TEXT,

    -- EU-Handel
    ust_idnr TEXT,  -- z.B. "BE0123456789"
    ust_idnr_validiert BOOLEAN DEFAULT 0,
    ust_idnr_validierung_datum DATE,
    ust_idnr_validierung_ergebnis TEXT,  -- BZSt-API Ergebnis

    -- Metadaten
    notizen TEXT,
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    aktualisiert_am TIMESTAMP,

    -- Statistiken
    anzahl_rechnungen INTEGER DEFAULT 0,
    umsatz_gesamt DECIMAL(10,2) DEFAULT 0.00
);
```

**Vorteile:**
- ✅ Weniger Tipparbeit (Kunde 1× anlegen)
- ✅ Autocomplete
- ✅ USt-IdNr. VORHER validiert
- ✅ Statistiken möglich

**Nachteile:**
- ❌ +2-3 Wochen Entwicklung
- ❌ Mehr Lernkurve
- ❌ DSGVO-Komplex

---

#### **Option B: OHNE Kundenstamm (v1.0)**

**Workflow:**
- Kundendaten werden direkt in Rechnung eingegeben (LibreOffice/HTML-Template)
- RechnungsPilot importiert PDF/XRechnung
- Validierung erst beim Export (UStVA, ZM)

**Vorteile:**
- ✅ Schnellerer Release (2-3 Wochen gespart)
- ✅ Einfacherer Scope
- ✅ DSGVO einfacher

**Nachteile:**
- ❌ Wiederholte Eingabe
- ❌ Tippfehler-Gefahr
- ❌ Validierung erst beim Export

---

#### **Option C: Hybrid (Kompromiss)**

**Workflow:**
```
Rechnung erstellen:
┌────────────────────────────┐
│ Kunde:                     │
│ ○ Aus Kundenstamm:        │
│   [Belgischer Kunde ▼]    │
│                            │
│ ● Manuell eingeben:       │
│   Name: [_____________]    │
│   Land: [Belgien ▼]       │
│   USt-IdNr: [_________]   │
│   ☑ Als Kunde speichern   │ ← Optional!
└────────────────────────────┘
```

**Vorteile:**
- ✅ Flexibel (User entscheidet)
- ✅ Moderater Aufwand (+1 Woche)

**Nachteile:**
- ⚠️ Zwei Wege (könnte verwirren)

---

**Community-Umfrage läuft:** `discussion-kundenstamm.md`

**Fragen:**
1. Wie viele wiederkehrende Kunden? (< 5, 5-20, > 20)
2. Priorität: Schneller Release vs. Komfort?
3. EU-Geschäft-Häufigkeit?

**Entscheidung ausstehend.**

---

**Status:** ✅ Kategorie 8 definiert (weitgehend) - User-/Firmen-Stammdaten, Kategorien, EU-Länder, Bankkonten, Kontenrahmen (SKR03/SKR04), Geschäftsjahr, Lieferantenstamm, Produktstamm (v2.0) dokumentiert. **Kundenstamm-Entscheidung ausstehend** (siehe `discussion-kundenstamm.md`).

---

### **Noch zu klären (siehe fragen.md):**

- ✅ ~~Kategorie 6: UStVA~~ - **Geklärt** (Hybrid-Ansatz, MVP nur Zahlen)
- ✅ ~~Kategorie 7: EÜR~~ - **Geklärt** (Hybrid-Ansatz, AfA-Verwaltung, Zufluss-/Abfluss-Prinzip)
- ⏸️ **Kategorie 8: Stammdaten-Erfassung** - **Teilweise geklärt** (User/Firma, Kategorien, EU-Länder, Bankkonten dokumentiert; **Kundenstamm: Community-Entscheidung ausstehend**)
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
