# RechnungsFee - Claude Projektdokumentation

> ⚠️ **HINWEIS:** Diese Datei wurde aufgeteilt in einzelne Themendokumente für bessere Wartbarkeit.
> 📚 **Neue Dokumentation:** Siehe [docs/README.md](docs/README.md) für den strukturierten Zugriff.
> 📄 Diese Datei bleibt als Archiv erhalten, wird aber nicht mehr aktiv gepflegt.

---

**Projekt:** RechnungsFee
**Typ:** Open-Source Buchhaltungssoftware
**Zielgruppe:** Freiberufler, Selbstständige, Kleinunternehmer
**Lizenz:** AGPL-3.0
**Status:** Konzeptphase
**Letzte Aktualisierung:** 2025-12-04

---

## **Projektvision**

RechnungsFee ist eine plattformunabhängige, Open-Source-Lösung für:
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

## **🎨 UI/UX-Richtlinien & Tonalität**

### **Ansprache: "Du" statt "Sie"**

**Entscheidung:** RechnungsFee verwendet durchgängig die **Du-Ansprache**.

**Begründung:**
- 💡 **Finanzen sind trocken** - Persönliche Ansprache macht es zugänglicher
- 👥 **Zielgruppe:** Freiberufler, Selbstständige, Kleinunternehmer - meist jüngere Generation
- 🤝 **Open Source Community** - "Du" ist Standard
- 🚀 **Moderne Software** - "Sie" wirkt altbacken und steif
- 💬 **Lockerer Ton** - Reduziert Hemmschwelle bei komplexen Steuerformularen

**Beispiele:**

| ❌ "Sie"-Formulierung | ✅ "Du"-Formulierung |
|----------------------|---------------------|
| "Bitte warten Sie..." | "Bitte warte..." |
| "Ihre Daten werden gespeichert" | "Deine Daten werden gespeichert" |
| "Wählen Sie ein Backup-Ziel" | "Wähle ein Backup-Ziel" |
| "Möchten Sie fortfahren?" | "Möchtest du fortfahren?" |
| "Ihre Rechnung wurde erstellt" | "Deine Rechnung wurde erstellt" |
| "Sie haben 3 neue Belege" | "Du hast 3 neue Belege" |
| "Bitte überprüfen Sie..." | "Bitte überprüfe..." |
| "Ihre Einstellungen wurden gespeichert" | "Deine Einstellungen wurden gespeichert" |

**Anwendungsbereiche:**
- ✅ Alle UI-Texte (Buttons, Menüs, Dialoge)
- ✅ Fehlermeldungen
- ✅ Hilfetexte und Tooltips
- ✅ Bestätigungsdialoge
- ✅ Onboarding-Screens
- ✅ Dokumentation (User-Handbuch)
- ✅ Changelog/Release Notes (soweit user-facing)

**Ausnahmen (formell bleiben):**
- ❌ Offizielle Dokumente (UStVA, EÜR, DATEV-Export) - hier gelten gesetzliche Vorgaben
- ❌ Externe API-Dokumentation (für Entwickler)
- ❌ Geschäftsbriefe/Rechnungen (sofern vom User erstellt - hier User-Einstellung)

### **Tonalität-Prinzipien**

1. **Freundlich, aber kompetent**
   - ✅ "Das Backup läuft. Dauert nur noch 30 Sekunden!"
   - ❌ "LOL, warte mal kurz! 😂"

2. **Klar und verständlich**
   - ✅ "Verschlüsselung schützt deine Daten bei Diebstahl"
   - ❌ "Encryption is mandatory pursuant to GDPR Art. 32"

3. **Hilfsbereit, nicht bevormundend**
   - ✅ "Tipp: Verschlüsselung ist für Kundendaten empfohlen"
   - ❌ "Du MUSST Verschlüsselung aktivieren!"

4. **Positiv formulieren**
   - ✅ "Backup erfolgreich! Deine Daten sind sicher."
   - ❌ "Fehler vermieden. Keine Probleme aufgetreten."

5. **Fehler menschlich kommunizieren**
   - ✅ "Ups! Die Verbindung zum NAS ist fehlgeschlagen. Prüfe bitte die Zugangsdaten."
   - ❌ "ERROR: SMB connection failed (errno 13)"

### **Emoji-Verwendung**

**Moderat einsetzen** - nur zur Orientierung, nicht übertreiben:

- ✅ **Icons in Dialogen:** 💾 Backup, ⚠️ Warnung, ✅ Erfolg, ❌ Fehler, ℹ️ Info
- ✅ **Kategorien/Menüs:** 📊 Berichte, ⚙️ Einstellungen, 🔐 Sicherheit
- ❌ **Nicht in Fließtext:** "Du hast 3 neue 📄 Belege 🎉🎉🎉"
- ❌ **Nicht in Fehlermeldungen:** "❌😱 Oh nein! ❌"

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

**Ziel von RechnungsFee:** Automatische Generierung der EKS aus vorhandenen Buchhaltungsdaten.

---

#### **Struktur der Anlage EKS**

##### **Tabelle A: Betriebseinnahmen (Einnahmen)**

| Feld | Beschreibung | Quelle in RechnungsFee |
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

| Feld | Beschreibung | Quelle in RechnungsFee |
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

| Feld | Beschreibung | Quelle in RechnungsFee |
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

| Feld | Beschreibung | Quelle in RechnungsFee |
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

| Feld | Beschreibung | Quelle in RechnungsFee |
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
- **Automatisch:** RechnungsFee summiert nach Monat

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
RechnungsFee bietet vordefinierte Kategorien, die direkt zu EKS-Feldern mappen:

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
- User wählt Kategorie → RechnungsFee weiß automatisch, wo es in EKS hingehört
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
2. **User öffnet RechnungsFee** → Menü: "Anlage EKS exportieren"
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

**RechnungsFee verwendet ein einheitliches Kategorisierungssystem:**

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
- Falls fehlend: Fehlermeldung "Bitte trage zuerst die DATEV-Daten ein"

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

**Hinweis:** Da RechnungsFee kein POS-Kassensystem ist (keine TSE), ist DATEV Kassenarchiv nicht verpflichtend. Standard-DATEV-Export reicht für MVP.

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
1. RechnungsFee öffnen
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
1. RechnungsFee öffnen
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

**RechnungsFee:**
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

**RechnungsFee-Export:**
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

**RechnungsFee-Verhalten:**
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
│ Bitte ergänze die USt-IdNr. und        │
│ validiere diese über BZSt.             │
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
│ RechnungsFee - Ersteinrichtung       │
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
│ RechnungsFee - Ersteinrichtung       │
│ Schritt 2/5: EU-Handel                 │
├─────────────────────────────────────────┤
│                                         │
│ Du hast EU-Handel aktiviert.           │
│ Bitte lies folgende Hinweise:          │
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
│ 📋 In welchen Ländern handelst du?     │
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
│ du eine gültige deutsche USt-IdNr.     │
│                                         │
│ Du bist aktuell als Kleinunternehmer   │
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
# EU-Handel: Was du benötigst

## ✅ Voraussetzungen

1. **Eigene USt-IdNr.**
   - Beim Finanzamt beantragen
   - Format: DE + 9 Ziffern (z.B. DE123456789)
   - In RechnungsFee: Einstellungen > Stammdaten

2. **Regelbesteuerung**
   - Kleinunternehmer (§19 UStG) können keinen EU-Handel nutzen
   - Umstellung beim Finanzamt beantragen

3. **Kunden-USt-IdNr.**
   - Für jeden EU-Kunden erforderlich
   - MUSS über BZSt validiert werden
   - In RechnungsFee: Kunde bearbeiten > "Validieren"

4. **Gelangensbestätigung**
   - Nachweis, dass Ware ins EU-Ausland geliefert wurde
   - CMR-Frachtbrief, DHL-Tracking, Lieferschein
   - In RechnungsFee: Rechnung > "Nachweis hochladen"

## ⚠️ Häufige Fehler

❌ "USt-IdNr. nicht validiert"
→ Lösung: Kunde öffnen > USt-IdNr. eingeben > "Validieren" klicken

❌ "0% USt nicht möglich"
→ Lösung: Kunde muss gültige USt-IdNr. haben

❌ "Gelangensbestätigung fehlt"
→ Lösung: CMR/Tracking hochladen (empfohlen, nicht Pflicht)

## 📋 Monatliche Aufgaben

- Zusammenfassende Meldung (ZM) an BZSt senden
- RechnungsFee: Berichte > ZM erstellen > XML exportieren
```

---

##### **⚠️ KRITISCHE KORREKTUR: Export-Zeit-Validierung**

**Problem mit obigem Konzept:**

```
RechnungsFee MVP hat KEINEN Kundenstamm!
────────────────────────────────────────────

User erstellt Rechnungen:
• LibreOffice-Vorlagen
• HTML-Vorlagen
• PDF/XRechnung-Import

→ KEINE Eingabemasken in RechnungsFee
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

   Option A: In RechnungsFee korrigieren
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
│ Behebe die Warnungen vor UStVA-Abgabe,          │
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
- RechnungsFee erkennt: User ist Kleinunternehmer
- UStVA-Menü wird ausgeblendet/deaktiviert
- Hinweis: "Als Kleinunternehmer (§19 UStG) musst du keine UStVA abgeben"

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
| **RechnungsFee** | Alle Ausgangsrechnungen | Nur bezahlte Rechnungen |

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

**RechnungsFee-Verhalten:**

1. **Beim Ersteinrichtung:**
   ```
   Beziehst du Transferleistungen?
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

### **6.6 Bürgergeld-Freibeträge (Einkommensanrechnung)**

**Für erwerbstätige Bürgergeld-Empfänger gibt es Einkommensfreibeträge:**

#### **Grundfreibetrag: 100 € brutto anrechnungsfrei**

**Zusammensetzung des Grundfreibetrags (100 €):**

1. **Versicherungsbeiträge:**
   - Kranken- und Pflegeversicherung (für nicht gesetzlich Versicherte)
   - Altersvorsorge (für Personen ohne Versicherungspflicht in gesetzlicher Rentenversicherung)

2. **Geförderte Altersvorsorge:**
   - Riester-Beiträge nach § 82 EStG
   - Bis Mindesteigenbeitrag nach § 86 EStG

3. **Werbungskosten:**
   - Mit Erzielung des Einkommens verbundene notwendige Ausgaben
   - Fahrtkosten: 0,20 €/km (bei Einkommen > 400 €, wenn Summe > 100 €)

#### **Gestaffelte Anrechnung über 100 €:**

| Bruttoeinkommen | Anrechnung | Anrechnungsfrei | Beispiel (brutto) | Anrechnungsfrei (konkret) |
|-----------------|------------|-----------------|-------------------|---------------------------|
| **0-100 €** | 0% | 100% | 80 € | 80 € |
| **101-520 €** | 80% | **20%** | 500 € | 100 € + (400 € × 20%) = **180 €** |
| **521-1000 €** | 70% | **30%** ⭐ | 800 € | 100 € + (400 € × 20%) + (280 € × 30%) = **264 €** |
| **1001-1200 €** | 90% | **10%** | 1.150 € | 100 € + (400 € × 20%) + (480 € × 30%) + (150 € × 10%) = **339 €** |
| **1001-1500 €** (mit Kind) | 90% | **10%** | 1.400 € | 100 € + (400 € × 20%) + (480 € × 30%) + (400 € × 10%) = **364 €** |
| **Über 1200/1500 €** | 100% | 0% | 1.300 € | 339 € (keine weitere Anrechnung) |

⭐ **NEU seit 2023:** Stufe 521-1000 € mit 30% anrechnungsfrei (vorher 20%)

**Grenzen:**
- **Ohne Kind:** 1.200 € Brutto
- **Mit Kind:** 1.500 € Brutto

#### **Berechnungsbeispiele:**

**Beispiel 1: Einkommen 400 €**
```
Brutto:                400,00 €
- Grundfreibetrag:    -100,00 €
- Anrechnungsfrei 20%:  -60,00 € (300 € × 20%)
= Angerechnet:         240,00 €
→ Bürgergeld wird um 240 € gekürzt
```

**Beispiel 2: Einkommen 750 € (NEU: 30% ab 521 €)**
```
Brutto:                750,00 €
- Grundfreibetrag:    -100,00 €
Verbleibend:           650,00 €

Staffelung:
  101-520 €: 420 € × 20% = 84,00 € anrechnungsfrei
  521-750 €: 230 € × 30% = 69,00 € anrechnungsfrei (NEU!)

Gesamt anrechnungsfrei: 100 + 84 + 69 = 253,00 €
= Angerechnet:                          497,00 €
→ Bürgergeld wird um 497 € gekürzt
```

**Beispiel 3: Einkommen 1.100 € (ohne Kind)**
```
Brutto:                1.100,00 €
- Grundfreibetrag:      -100,00 €
Verbleibend:          1.000,00 €

Staffelung:
  101-520 €: 420 € × 20% =  84,00 € anrechnungsfrei
  521-1000 €: 480 € × 30% = 144,00 € anrechnungsfrei (NEU!)
  1001-1100 €: 100 € × 10% =  10,00 € anrechnungsfrei

Gesamt anrechnungsfrei: 100 + 84 + 144 + 10 = 338,00 €
= Angerechnet:                                762,00 €
→ Bürgergeld wird um 762 € gekürzt
```

#### **RechnungsFee-Implementierung:**

```python
def calculate_buergergeld_anrechnung(brutto_einkommen: Decimal, hat_kind: bool = False) -> dict:
    """
    Berechnet Bürgergeld-Einkommensanrechnung (Stand 2023)

    Returns:
        {
            'brutto': Decimal,
            'grundfreibetrag': Decimal,
            'anrechnungsfrei_gesamt': Decimal,
            'angerechnet': Decimal,
            'staffelung': list  # Details der Berechnung
        }
    """
    grundfreibetrag = Decimal('100.00')

    if brutto_einkommen <= grundfreibetrag:
        return {
            'brutto': brutto_einkommen,
            'grundfreibetrag': brutto_einkommen,
            'anrechnungsfrei_gesamt': brutto_einkommen,
            'angerechnet': Decimal('0.00'),
            'staffelung': []
        }

    verbleibend = brutto_einkommen - grundfreibetrag
    anrechnungsfrei = grundfreibetrag
    staffelung = []

    # Stufe 1: 101-520 € (20% anrechnungsfrei)
    if verbleibend > 0:
        stufe1_max = Decimal('420.00')  # 520 - 100
        stufe1_betrag = min(verbleibend, stufe1_max)
        stufe1_frei = stufe1_betrag * Decimal('0.20')
        anrechnungsfrei += stufe1_frei
        staffelung.append({
            'bereich': '101-520 €',
            'betrag': stufe1_betrag,
            'prozent': 20,
            'anrechnungsfrei': stufe1_frei
        })
        verbleibend -= stufe1_betrag

    # Stufe 2: 521-1000 € (30% anrechnungsfrei) ⭐ NEU!
    if verbleibend > 0:
        stufe2_max = Decimal('480.00')  # 1000 - 520
        stufe2_betrag = min(verbleibend, stufe2_max)
        stufe2_frei = stufe2_betrag * Decimal('0.30')  # NEU: 30% statt 20%
        anrechnungsfrei += stufe2_frei
        staffelung.append({
            'bereich': '521-1000 €',
            'betrag': stufe2_betrag,
            'prozent': 30,
            'anrechnungsfrei': stufe2_frei
        })
        verbleibend -= stufe2_betrag

    # Stufe 3: 1001-1200 € bzw. 1001-1500 € (mit Kind) (10% anrechnungsfrei)
    if verbleibend > 0:
        stufe3_max = Decimal('300.00') if not hat_kind else Decimal('600.00')  # 1500 - 1000 mit Kind
        stufe3_betrag = min(verbleibend, stufe3_max)
        stufe3_frei = stufe3_betrag * Decimal('0.10')
        anrechnungsfrei += stufe3_frei
        staffelung.append({
            'bereich': f'1001-{1200 if not hat_kind else 1500} €',
            'betrag': stufe3_betrag,
            'prozent': 10,
            'anrechnungsfrei': stufe3_frei
        })
        verbleibend -= stufe3_betrag

    # Alles darüber: 100% angerechnet (0% frei)
    if verbleibend > 0:
        staffelung.append({
            'bereich': f'Über {1200 if not hat_kind else 1500} €',
            'betrag': verbleibend,
            'prozent': 0,
            'anrechnungsfrei': Decimal('0.00')
        })

    angerechnet = brutto_einkommen - anrechnungsfrei

    return {
        'brutto': brutto_einkommen,
        'grundfreibetrag': grundfreibetrag,
        'anrechnungsfrei_gesamt': anrechnungsfrei,
        'angerechnet': angerechnet,
        'staffelung': staffelung
    }
```

#### **UI-Ansicht (EKS-Export / Einkommensübersicht):**

```
┌──────────────────────────────────────────────────────────┐
│ Einkommensberechnung für Bürgergeld (Bewilligungszeitraum)│
├──────────────────────────────────────────────────────────┤
│                                                          │
│ Zeitraum: Januar - Juni 2025 (6 Monate)                 │
│                                                          │
│ EINNAHMEN:                                               │
│   Betriebseinnahmen:          4.200,00 € (monatl. Ø 700 €)│
│                                                          │
│ AUSGABEN:                                                │
│   Betriebsausgaben:          -1.800,00 €                 │
│   ────────────────────────────────────────               │
│   Gewinn/Monat (Ø):             400,00 €                 │
│                                                          │
│ ANRECHNUNG (pro Monat):                                  │
│   Bruttoeinkommen:              400,00 €                 │
│   - Grundfreibetrag:          - 100,00 €                 │
│   - Anrechnungsfrei (20%):    -  60,00 € (300 € × 20%)  │
│   ──────────────────────────────────────                 │
│   Angerechnetes Einkommen:      240,00 €                 │
│                                                          │
│ 💡 Ihr Bürgergeld wird um ca. 240 € pro Monat gekürzt   │
│                                                          │
│    [EKS-Formular exportieren]  [Details anzeigen]        │
└──────────────────────────────────────────────────────────┘
```

**Detail-Ansicht:**

```
┌──────────────────────────────────────────┐
│ Staffelung Einkommensanrechnung          │
├──────────────────────────────────────────┤
│                                          │
│ Bruttoeinkommen:      400,00 €           │
│                                          │
│ 1. Grundfreibetrag:                      │
│    0-100 €            100,00 € (100%)    │
│                                          │
│ 2. Staffelung:                           │
│    101-400 €          300,00 €           │
│    Anrechnungsfrei:    60,00 € (20%)     │
│    Angerechnet:       240,00 € (80%)     │
│                                          │
│ ────────────────────────────────────     │
│                                          │
│ Gesamt anrechnungsfrei:  160,00 €        │
│ Gesamt angerechnet:      240,00 €        │
│                                          │
│              [ Schließen ]               │
└──────────────────────────────────────────┘
```

#### **Hinweise für User:**

⚠️ **Wichtig:**
- Anrechnung erfolgt auf **Brutto-Einkommen** (Einnahmen - Ausgaben)
- Werbungskosten sind bereits im Grundfreibetrag (100 €) enthalten
- Fahrtkosten können zusätzlich abgesetzt werden (0,20 €/km bei Einkommen > 400 €)
- Bei schwankendem Einkommen: Durchschnitt des Bewilligungszeitraums

💡 **Tipp:**
- Einkommen unter 100 €/Monat: Keine Anrechnung
- Einkommen 100-520 €: 20% anrechnungsfrei zusätzlich
- Einkommen 521-1000 €: **30% anrechnungsfrei** (NEU seit 2023!)
- Mit Kind: Höhere Grenze (1.500 € statt 1.200 €)

---

**Status:** ✅ Kategorie 6.1-6.6 definiert - Hybrid-Ansatz (MVP: Zahlen vorbereiten, v2.0: ELSTER-Integration), Berechnung, Kleinunternehmer, Ist/Soll-Versteuerung, SGBII-Konformität (Ist-Versteuerung Pflicht bei Transferleistungen).

---

## **🔍 Export-Anforderungen für Steuerberater-Software**

### **AGENDA - Export-Kompatibilität**

**Was AGENDA importieren kann (= was RechnungsFee exportieren muss):**

1. **DATEV-Format**
   - AGENDA kann DATEV-Daten importieren
   - ✅ RechnungsFee hat bereits DATEV-Export (Kategorie 2)

2. **Belegbilder-Export (PDF + XML)**
   - **AGENDA-Anforderung:** PDF und XML müssen denselben Dateinamen haben
   - **Format:** `rechnung-123.pdf` + `rechnung-123.xml`
   - **Bulk-Export:** Gezippte Belegbilder
   - **Workflow:** RechnungsFee erstellt ZIP → AGENDA importiert → Matcht PDF+XML automatisch

**RechnungsFee-Export für AGENDA:**

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

**Antwort: Ja, RechnungsFee bucht automatisch nach Zahlungsdatum (nicht Rechnungsdatum).**

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

**Antwort: Ja, RechnungsFee warnt proaktiv bei Jahresübergang.**

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

**RechnungsFee-Datenquellen:**
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

**RechnungsFee-Datenquellen:**
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

RechnungsFee bietet ein **zweistufiges Kategorien-System**:

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

**User-Kategorien:** Können frei benannt werden, aber RechnungsFee schlägt vor:
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

**RechnungsFee-Implementierung:**
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

#### **Umfang der Anlagenverwaltung in RechnungsFee**

**RechnungsFee bietet vollständige Anlagenverwaltung mit:**

1. ✅ **GWG-Automatik** (Sofortabzug < 800 €, Poolabschreibung 800-1000 €)
2. ✅ **AfA-Rechner** (automatische Abschreibungsberechnung)
3. ✅ **Anlagenverzeichnis** (Übersicht aller Wirtschaftsgüter)
4. ✅ **Monatsgenauer AfA-Berechnung** (anteilig im ersten/letzten Jahr)

---

#### **GWG-Grenzwerte: 800€ vs. 1000€**

**Drei Schwellenwerte:**

| Anschaffungskosten (netto) | Regelung | RechnungsFee-Verhalten |
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

RechnungsFee empfiehlt **Sofortabzug** (wenn User nicht sicher ist), da:
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

RechnungsFee enthält die wichtigsten Einträge der amtlichen AfA-Tabelle:

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

**Entscheidung:** RechnungsFee bietet **vollständige Abschreibungslogik**.

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
- \> 800 €: RechnungsFee **schlägt vor**, Anlagegut anzulegen (kann übersprungen werden)

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

**Wichtig:** User kann überspringen, aber RechnungsFee warnt:

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

**✅ RechnungsFee berechnet:**
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
1. RechnungsFee: "EÜR erstellen" → Zeitraum wählen (2025)
2. RechnungsFee berechnet alle Werte
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
1. RechnungsFee: "EÜR erstellen und senden"
2. RechnungsFee generiert ELSTER-XML
3. RechnungsFee sendet direkt ans Finanzamt
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

RechnungsFee bietet **zwei EÜR-Export-Varianten**:

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

**Arten von Stammdaten in RechnungsFee:**

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
    steuernummer: str  # "12/345/67890" (altes Format) oder "2123450678901" (neues 13-stelliges Format nach Umschlüsselung)
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
│ RechnungsFee - Ersteinrichtung (Schritt 1/4) │
├─────────────────────────────────────────────────┤
│                                                 │
│ FIRMA / FREIBERUFLER                            │
│                                                 │
│  Firmenname:  [___________________________]    │
│  Rechtsform:  [Freiberufler ▼]                 │
│               □ Einzelunternehmer               │
│               □ GbR                             │
│               ● Freiberufler                    │
│                                                 │
│  ℹ️ RechnungsFee unterstützt nur            │
│     EÜR-berechtigte Rechtsformen.              │
│     Bilanzpflichtige Gesellschaften (GmbH,     │
│     UG, OHG, KG) werden nicht unterstützt.     │
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
│ RechnungsFee - Ersteinrichtung (Schritt 2/4) │
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
│ RechnungsFee - Ersteinrichtung (Schritt 3/4) │
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
│ RechnungsFee - Ersteinrichtung (Schritt 4/4) │
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

### **8.2.1 Unterstützte Rechtsformen**

**RechnungsFee unterstützt nur EÜR-berechtigte Rechtsformen:**

✅ **Unterstützt:**
- **Einzelunternehmer** - Gewerbetreibende ohne besondere Rechtsform
- **Freiberufler** - § 18 EStG (Ärzte, Anwälte, IT-Berater, Künstler, etc.)
- **GbR (Gesellschaft bürgerlichen Rechts)** - Personengesellschaft unter Grenzen (Gewinn < 60k€, Umsatz < 600k€)

❌ **NICHT unterstützt (bilanzpflichtig):**
- **GmbH** - Kapitalgesellschaft → Bilanzierung Pflicht nach HGB
- **UG (haftungsbeschränkt)** - Kleine Kapitalgesellschaft → Bilanzierung Pflicht
- **OHG (Offene Handelsgesellschaft)** - Personengesellschaft → Bilanzierung Pflicht
- **KG (Kommanditgesellschaft)** - Personengesellschaft → Bilanzierung Pflicht

**UI-Verhalten:**

```
Rechtsform wählen:

○ Einzelunternehmer
○ Freiberufler
● GbR

──────────────────────────────────────

ℹ️ Hinweis: RechnungsFee unterstützt nur
   EÜR-berechtigte Rechtsformen.

   Bilanzpflichtige Gesellschaften (GmbH,
   UG, OHG, KG) können nicht verwendet
   werden, da sie zur doppelten
   Buchführung verpflichtet sind.
```

**Begründung:**

| Rechtsform | EÜR | Bilanz | RechnungsFee |
|------------|-----|--------|----------------|
| Einzelunternehmer | ✅ | ❌ | ✅ Unterstützt |
| Freiberufler | ✅ | ❌ | ✅ Unterstützt |
| GbR (unter Grenzen) | ✅ | ❌ | ✅ Unterstützt |
| GbR (über Grenzen) | ❌ | ✅ | ❌ Nicht unterstützt |
| GmbH, UG | ❌ | ✅ | ❌ Nicht unterstützt |
| OHG, KG | ❌ | ✅ | ❌ Nicht unterstützt |

**Grenzen für GbR:**
- Gewinn < 60.000 € pro Jahr UND
- Umsatz < 600.000 € pro Jahr

⚠️ **Warnung bei Überschreitung:** RechnungsFee warnt, wenn GbR diese Grenzen überschreitet.

---

### **8.2.2 Steuernummer-Formate**

**Deutschland hat zwei Steuernummer-Formate:**

#### **Altes Format (Bundesland-spezifisch):**

**Format:** `FF/BBB/UUUUP`

- **FF** = Finanzamtsnummer (2-stellig)
- **BBB** = Bezirksnummer (3-stellig)
- **UUUUP** = Persönliche Nummer + Prüfziffer (5-stellig)

**Beispiel:** `12/345/67890`

**Varianten je Bundesland:**
- Bayern: `123/456/78901` (3/3/5)
- NRW: `123/4567/8901` (3/4/4)
- Baden-Württemberg: `12345/67890` (5/5)

#### **Neues Format (Bundeseinheitlich nach Umschlüsselung):**

**Format:** `BBFFUUUUUUUUP` (13-stellig, ohne Schrägstriche)

- **BB** = Bundesland-Kennziffer (2-stellig)
- **FF** = Finanzamtsnummer (2-stellig)
- **UUUUUUUU** = Persönliche Nummer (8-stellig)
- **P** = Prüfziffer (1-stellig)

**Beispiel:** `2123450678901`

**Bundesland-Kennziffern:**
- 21 = Niedersachsen
- 93 = Bayern
- 51 = Nordrhein-Westfalen
- 28 = Baden-Württemberg
- etc.

**RechnungsFee unterstützt beide Formate:**

```python
def validate_steuernummer(stnr: str) -> bool:
    """
    Validiert Steuernummer (altes oder neues Format)
    """
    # Schrägstriche entfernen für Verarbeitung
    stnr_clean = stnr.replace('/', '').replace(' ', '')

    # Neues Format: 13-stellig, nur Ziffern
    if len(stnr_clean) == 13 and stnr_clean.isdigit():
        return validate_bundeseinheitlich(stnr_clean)

    # Altes Format: 10-11 Ziffern (ohne Schrägstriche)
    if len(stnr_clean) >= 10 and len(stnr_clean) <= 11:
        return validate_alt(stnr, stnr_clean)

    return False
```

**UI-Eingabe:**

```
┌──────────────────────────────────────────┐
│ Steuernummer                             │
├──────────────────────────────────────────┤
│                                          │
│  Format: [Auto-Erkennung ▼]              │
│          ● Automatisch erkennen          │
│          ○ Alt (z.B. 12/345/67890)      │
│          ○ Neu (13-stellig)             │
│                                          │
│  Steuernummer: [_________________]       │
│                                          │
│  ✅ Gültig (neues Format erkannt)        │
│     2123450678901                        │
│                                          │
│    [ Abbrechen ]  [ Speichern ]          │
└──────────────────────────────────────────┘
```

**Automatische Erkennung:**
- Eingabe mit Schrägstrichen (`/`) → Altes Format
- Eingabe 13-stellig ohne Schrägstriche → Neues Format
- Validierung nach erkanntem Format

**Speicherung:**
- Intern: Immer normalisiert (ohne Schrägstriche)
- Anzeige: Mit ursprünglicher Formatierung
- Export: Je nach Ziel-System (ELSTER akzeptiert beide)

---

### **8.2.3 Berufsrechtliche Pflichtangaben**

**Bestimmte Berufe haben Pflichtangaben auf Rechnungen:**

#### **Kammerberufe:**

| Beruf | Pflichtangabe | Beispiel |
|-------|--------------|----------|
| **Handwerker** | Handwerkskammer + Handwerksrollennummer | "Eingetragen bei Handwerkskammer Oldenburg, Nr. HWK-123456" |
| **Arzt** | Ärztekammer + Approbationsnummer (optional) | "Mitglied der Ärztekammer Niedersachsen" |
| **Rechtsanwalt** | Rechtsanwaltskammer + Zulassung | "Zugelassen bei Rechtsanwaltskammer Oldenburg" |
| **Steuerberater** | Steuerberaterkammer + Berufsbezeichnung | "Mitglied der Steuerberaterkammer Niedersachsen" |
| **Architekt** | Architektenkammer + Berufsbezeichnung | "Mitglied der Architektenkammer Niedersachsen" |
| **Ingenieur** | Ingenieurkammer (je nach Bundesland) | "Mitglied der Ingenieurkammer Niedersachsen" |

#### **IHK-Mitglieder:**

**Gewerbetreibende (IHK-pflichtig):**
- IHK + Registernummer (optional, aber empfohlen)
- Beispiel: "IHK Oldenburg, Registernummer IHK-789012"

#### **Datenmodell:**

```python
class User:
    # ... (bestehende Felder)

    # Berufsrechtliche Angaben (optional, je nach Beruf)
    kammer_typ: str  # 'handwerk', 'aerzte', 'rechtsanwaelte', 'steuerberater', 'architekten', 'ingenieure', 'ihk', 'keine'
    kammer_name: str  # "Handwerkskammer Oldenburg"
    kammer_nummer: str  # "HWK-123456" oder "IHK-789012"

    # Zusätzliche Angaben (je nach Beruf)
    berufsbezeichnung: str  # "Rechtsanwalt", "Steuerberater", "Architekt"
    approbation: str  # Nur für Ärzte/Apotheker
```

#### **UI-Eingabe im Setup-Wizard:**

```
┌─────────────────────────────────────────────────┐
│ RechnungsFee - Ersteinrichtung (Schritt 1/4) │
├─────────────────────────────────────────────────┤
│                                                 │
│ BERUFSRECHTLICHE ANGABEN                        │
│                                                 │
│ Bist du Mitglied einer Kammer/eines            │
│ Berufsverbandes?                                │
│                                                 │
│ ○ Nein                                          │
│ ● Ja                                            │
│                                                 │
│   Kammer/Verband: [Handwerkskammer ▼]          │
│                   □ Keine                       │
│                   ● Handwerkskammer             │
│                   □ Ärztekammer                 │
│                   □ Rechtsanwaltskammer         │
│                   □ Steuerberaterkammer         │
│                   □ Architektenkammer           │
│                   □ Ingenieurkammer             │
│                   □ IHK                         │
│                                                 │
│   Name:   [Handwerkskammer Oldenburg____]      │
│   Nummer: [HWK-123456___________________]      │
│                                                 │
│   ℹ️ Diese Angaben erscheinen auf Rechnungen   │
│      (gesetzliche Pflicht bei Kammerberufen)   │
│                                                 │
│              [← Zurück]      [Weiter →]         │
└─────────────────────────────────────────────────┘
```

#### **Rechtliche Grundlagen:**

**§ 14 Abs. 4 UStG - Pflichtangaben auf Rechnungen:**

Für Kammerberufe zusätzlich erforderlich:
- Berufsbezeichnung
- Zuständige Kammer
- Kammernummer (je nach Kammer)

**Beispiele auf Rechnung:**

**1. Handwerker:**
```
Max Mustermann
Elektroinstallateur
Musterstraße 42, 26121 Oldenburg

Eingetragen bei der Handwerkskammer Oldenburg
Handwerksrollennummer: HWK-123456
```

**2. Rechtsanwalt:**
```
Dr. Erika Musterfrau
Rechtsanwältin
Musterstraße 42, 26121 Oldenburg

Zugelassen bei der Rechtsanwaltskammer Oldenburg
```

**3. Arzt:**
```
Dr. med. Max Mustermann
Facharzt für Allgemeinmedizin
Musterstraße 42, 26121 Oldenburg

Mitglied der Ärztekammer Niedersachsen
```

**4. IHK-Mitglied:**
```
Musterfirma GmbH
Geschäftsführer: Max Mustermann
Musterstraße 42, 26121 Oldenburg

IHK Oldenburg, Registernummer: IHK-789012
```

#### **Automatische Angabe auf Rechnungen:**

```python
def generate_rechnung_kopf(user, kunde):
    """
    Generiert Rechnungskopf mit Pflichtangaben
    """
    kopf = f"{user.firmenname or f'{user.vorname} {user.nachname}'}\n"

    # Berufsbezeichnung (wenn vorhanden)
    if user.berufsbezeichnung:
        kopf += f"{user.berufsbezeichnung}\n"

    kopf += f"{user.strasse}, {user.plz} {user.ort}\n\n"

    # Kammer-Angaben (Pflicht bei Kammerberufen)
    if user.kammer_typ != 'keine':
        if user.kammer_typ == 'handwerk':
            kopf += f"Eingetragen bei der {user.kammer_name}\n"
            kopf += f"Handwerksrollennummer: {user.kammer_nummer}\n\n"

        elif user.kammer_typ == 'rechtsanwaelte':
            kopf += f"Zugelassen bei der {user.kammer_name}\n\n"

        elif user.kammer_typ == 'aerzte':
            kopf += f"Mitglied der {user.kammer_name}\n"
            if user.approbation:
                kopf += f"Approbation: {user.approbation}\n"
            kopf += "\n"

        elif user.kammer_typ == 'ihk':
            kopf += f"{user.kammer_name}"
            if user.kammer_nummer:
                kopf += f", Registernummer: {user.kammer_nummer}"
            kopf += "\n\n"

        else:
            # Generisch: Steuerberater, Architekten, Ingenieure
            kopf += f"Mitglied der {user.kammer_name}\n\n"

    return kopf
```

#### **Validierung:**

```python
def validate_kammerangaben(user):
    """
    Prüft ob Kammer-Angaben vollständig sind
    """
    errors = []

    if user.kammer_typ != 'keine':
        if not user.kammer_name:
            errors.append({
                'field': 'kammer_name',
                'message': 'Kammer-Name ist Pflicht bei Kammerberufen'
            })

        # Handwerker: Nummer ist Pflicht
        if user.kammer_typ == 'handwerk' and not user.kammer_nummer:
            errors.append({
                'field': 'kammer_nummer',
                'message': 'Handwerksrollennummer ist Pflicht für Handwerker'
            })

    return errors
```

#### **Hinweis für User:**

⚠️ **Wichtig:**
- Bei Kammerberufen sind diese Angaben **gesetzlich verpflichtend** auf Rechnungen
- Fehlende Angaben können zu Abmahnungen führen
- RechnungsFee fügt diese automatisch in Rechnungsvorlagen ein

💡 **Tipp:**
- Falls unsicher: Auf der Website Ihrer Kammer nachsehen
- Bei IHK: Pflicht zur Mitgliedschaft, Angabe auf Rechnung empfohlen

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
│ Welchen Kontenrahmen nutzt du?         │
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
- Wiederholte Lieferanten (z.B. Vermieter, Telefon, Strom, Material)
- Autocomplete bei Eingangsrechnungen
- Detaillierte Kontaktdaten für Bestellungen

**Datenbank:**
```sql
CREATE TABLE lieferanten (
    id INTEGER PRIMARY KEY,

    -- Stammdaten
    lieferantennummer TEXT UNIQUE,  -- "L-001" (automatisch)
    name TEXT NOT NULL,  -- "Deutsche Telekom AG" (Pflichtfeld) ⭐

    -- Adresse ⭐
    strasse TEXT,
    hausnummer TEXT,
    plz TEXT,
    ort TEXT,
    land TEXT DEFAULT 'DE',

    -- Kontakt (Firma) ⭐
    telefon TEXT,
    email TEXT,
    website TEXT,

    -- Kontaktperson ⭐ NEU
    kontaktperson_name TEXT,  -- z.B. "Max Mustermann"
    kontaktperson_telefon TEXT,
    kontaktperson_email TEXT,

    -- Unternehmensdetails ⭐ NEU
    handelsregisternummer TEXT,  -- z.B. "HRB 12345"
    steuernummer TEXT,

    -- Steuerlich
    ust_idnr TEXT,  -- Bei EU-Lieferanten wichtig (Reverse Charge)

    -- Standard-Kategorie (optional)
    standard_kategorie_id INTEGER,  -- z.B. "Telefon/Internet" für Telekom

    -- Metadaten ⭐
    beschreibung TEXT,  -- Beschreibung / Notizen
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    aktualisiert_am TIMESTAMP,

    -- Statistiken
    anzahl_rechnungen INTEGER DEFAULT 0,
    ausgaben_gesamt DECIMAL(10,2) DEFAULT 0.00,
    letzte_rechnung_datum DATE,

    FOREIGN KEY (standard_kategorie_id) REFERENCES kategorien(id)
);

-- Index für schnelle Suche
CREATE INDEX idx_lieferanten_nummer ON lieferanten(lieferantennummer);
CREATE INDEX idx_lieferanten_name ON lieferanten(name);
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

#### **🖥️ UI: Neuen Lieferanten anlegen** ⭐ NEU

```
┌──────────────────────────────────────────────────┐
│ ➕ Neuer Lieferant                               │
├──────────────────────────────────────────────────┤
│                                                  │
│ Name: * ⭐                                       │
│ [Deutsche Telekom AG_________________]           │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ Adresse ⭐                                 │  │
│ ├────────────────────────────────────────────┤  │
│ │                                            │  │
│ │ Straße:          Hausnr.:                  │  │
│ │ [Musterstraße__] [42__]                    │  │
│ │                                            │  │
│ │ PLZ:       Ort:                            │  │
│ │ [53111__]  [Bonn_______________]           │  │
│ │                                            │  │
│ │ Land:                                      │  │
│ │ [Deutschland ▼]                            │  │
│ │                                            │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ Kontakt (Firma) ⭐                         │  │
│ ├────────────────────────────────────────────┤  │
│ │                                            │  │
│ │ Telefon:                                   │  │
│ │ [📞 0228 181-0___________]                 │  │
│ │                                            │  │
│ │ E-Mail:                                    │  │
│ │ [info@telekom.de_____________]             │  │
│ │                                            │  │
│ │ Website:                                   │  │
│ │ [https://www.telekom.de__]                 │  │
│ │                                            │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ Kontaktperson ⭐ NEU                       │  │
│ ├────────────────────────────────────────────┤  │
│ │                                            │  │
│ │ Name:                                      │  │
│ │ [Max Mustermann______________]             │  │
│ │                                            │  │
│ │ Telefon (direkt):                          │  │
│ │ [📞 0228 181-1234________]                 │  │
│ │                                            │  │
│ │ E-Mail (direkt):                           │  │
│ │ [max.mustermann@telekom.de___]             │  │
│ │                                            │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ Unternehmensdetails ⭐ NEU                 │  │
│ ├────────────────────────────────────────────┤  │
│ │                                            │  │
│ │ Handelsregisternummer:                     │  │
│ │ [HRB 12345_______________]                 │  │
│ │ ℹ️ z.B. "HRB 12345" (Amtsgericht XY)      │  │
│ │                                            │  │
│ │ Steuernummer:                              │  │
│ │ [26/123/12345____________]                 │  │
│ │                                            │  │
│ │ USt-IdNr. (bei EU-Lieferanten):            │  │
│ │ [DE123456789_____]  [Validieren ✓]        │  │
│ │ ℹ️ Wichtig für Reverse Charge             │  │
│ │                                            │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ Standard-Kategorie:                              │
│ [Telefon/Internet ▼]                             │
│ ℹ️ Wird bei Eingangsrechnungen vorgeschlagen    │
│                                                  │
│ Beschreibung / Anmerkungen: ⭐                   │
│ [____________________________________________]   │
│ [Hauptlieferant für Telefonanlage____________]   │
│ [Vertragsnummer: 123456789___________________]   │
│                                                  │
│ [Abbrechen]                    [Speichern]       │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

#### **📋 Templates für Lieferanten** ⭐ NEU (für später)

**Konzept:**
Branchenspezifische Vorlagen für Lieferanten-Felder

**Lieferanten-Templates:**

```python
# templates/lieferanten_templates.py
LIEFERANTEN_TEMPLATES = {
    'standard': {
        'name': 'Standard (Universal)',
        'felder': [
            'lieferantennummer', 'name',
            'strasse', 'plz', 'ort', 'land',
            'telefon', 'email', 'website',
            'kontaktperson_name', 'kontaktperson_telefon', 'kontaktperson_email',
            'handelsregisternummer', 'steuernummer', 'ust_idnr',
            'standard_kategorie_id', 'beschreibung'
        ],
        'pflicht': ['name']
    },

    'handwerk_material': {
        'name': 'Handwerk - Material-Lieferanten',
        'beschreibung': 'Für Handwerker: Baustoff, Werkzeug, Material',
        'felder': [
            'lieferantennummer', 'name',
            'strasse', 'hausnummer', 'plz', 'ort',  # Adresse wichtig (Abholung)
            'telefon', 'email', 'website',
            'kontaktperson_name', 'kontaktperson_telefon',  # Für Bestellungen
            'standard_kategorie_id',  # "Wareneinkauf"
            'beschreibung'  # "Lieferzeit 2-3 Tage", "Rabatt 5%"
        ],
        'pflicht': ['name', 'telefon'],
        'besonderheiten': [
            'Telefon Pflicht (für schnelle Bestellungen)',
            'Adresse wichtig (für Abholung)',
            'Kontaktperson für Bestellabwicklung'
        ]
    },

    'it_software': {
        'name': 'IT/Software - SaaS & Lizenzen',
        'beschreibung': 'Für Software-Abos, Cloud-Dienste, Lizenzen',
        'felder': [
            'lieferantennummer', 'name',
            'email', 'website',  # Nur Online-Kontakt
            'kontaktperson_name', 'kontaktperson_email',  # Support-Kontakt
            'ust_idnr',  # Oft EU-Anbieter
            'standard_kategorie_id',  # "Software/SaaS"
            'beschreibung'  # "Abo-Nr: 123456", "Kündigungsfrist: 3 Monate"
        ],
        'pflicht': ['name', 'email'],
        'besonderheiten': [
            'Adresse optional (nur Online)',
            'E-Mail Pflicht (Hauptkommunikation)',
            'Website wichtig (für Login/Support)',
            'Beschreibung für Abo-Details'
        ]
    },

    'buero_verbrauch': {
        'name': 'Bürobedarf & Verbrauchsmaterial',
        'beschreibung': 'Für Büromaterial, Druckerpatronen, etc.',
        'felder': [
            'lieferantennummer', 'name',
            'telefon', 'email', 'website',
            'kontaktperson_name', 'kontaktperson_telefon', 'kontaktperson_email',
            'standard_kategorie_id',  # "Bürobedarf"
            'beschreibung'  # "Kundennummer: K123456", "Lieferung ab 50€ frei"
        ],
        'pflicht': ['name', 'telefon'],
        'besonderheiten': [
            'Telefon/E-Mail für Bestellungen',
            'Adresse optional (Lieferung)',
            'Kontaktperson für Auftragsabwicklung'
        ]
    },

    'dienstleister_fixkosten': {
        'name': 'Dienstleister - Fixkosten',
        'beschreibung': 'Für Miete, Strom, Telefon, Versicherungen',
        'felder': [
            'lieferantennummer', 'name',
            'strasse', 'plz', 'ort',  # Für Schriftverkehr
            'telefon', 'email', 'website',
            'kontaktperson_name', 'kontaktperson_telefon',  # Ansprechpartner
            'ust_idnr',
            'standard_kategorie_id',  # "Raumkosten", "Telefon", etc.
            'beschreibung'  # "Vertragsnummer: 123456", "Kündigungsfrist: 31.12."
        ],
        'pflicht': ['name', 'standard_kategorie_id'],
        'besonderheiten': [
            'Standard-Kategorie Pflicht (für AutoBooking)',
            'Beschreibung für Vertragsdaten',
            'Kontaktperson für Vertragsanpassungen'
        ]
    },

    'wareneinkauf_grosshandel': {
        'name': 'Wareneinkauf - Großhändler',
        'beschreibung': 'Für Wiederverkäufer, Produzenten, Importeure',
        'felder': [
            'lieferantennummer', 'name',
            'strasse', 'hausnummer', 'plz', 'ort', 'land',
            'telefon', 'email', 'website',
            'kontaktperson_name', 'kontaktperson_telefon', 'kontaktperson_email',
            'handelsregisternummer',  # ⚠️ Wichtig für Verträge
            'steuernummer', 'ust_idnr',  # ⚠️ Wichtig für Vorsteuerabzug
            'standard_kategorie_id',  # "Wareneinkauf"
            'beschreibung'  # "Zahlungsziel: 30 Tage", "Mindestbestellwert: 500€"
        ],
        'pflicht': ['name', 'strasse', 'plz', 'ort', 'steuernummer'],
        'besonderheiten': [
            'Vollständige Adresse Pflicht',
            'Steuernummer Pflicht (für Vorsteuerabzug)',
            'Handelsregisternummer empfohlen',
            'USt-IdNr. bei EU-Lieferanten Pflicht (Reverse Charge)'
        ]
    },

    'freiberufler_subunternehmer': {
        'name': 'Freiberufler - Subunternehmer',
        'beschreibung': 'Für Freie Mitarbeiter, Subunternehmer, Dienstleister',
        'felder': [
            'lieferantennummer', 'name',
            'telefon', 'email',
            'kontaktperson_name',  # = Name (bei Einzelperson)
            'steuernummer',  # ⚠️ Wichtig für § 13b UStG
            'ust_idnr',
            'standard_kategorie_id',
            'beschreibung'  # "Stundensatz: 80€", "Spezialisierung: PHP"
        ],
        'pflicht': ['name', 'telefon', 'email', 'steuernummer'],
        'besonderheiten': [
            'Steuernummer Pflicht (für § 13b UStG - Reverse Charge Bau)',
            'Telefon/E-Mail für Abstimmung',
            'Beschreibung für Stundensatz/Konditionen'
        ]
    }
}


def get_lieferanten_template(branche: str) -> dict:
    """
    Gibt Template für Branche zurück

    Args:
        branche: 'standard', 'handwerk_material', 'it_software', etc.

    Returns:
        Template-Dict mit Feldern, Pflichtfeldern, Besonderheiten
    """
    return LIEFERANTEN_TEMPLATES.get(branche, LIEFERANTEN_TEMPLATES['standard'])
```

**UI - Template-Auswahl (Setup-Wizard):**

```
┌──────────────────────────────────────────────────┐
│ Setup-Wizard: Lieferanten-Arten                  │
├──────────────────────────────────────────────────┤
│                                                  │
│ Welche Art von Lieferanten hast du hauptsächlich?│
│ (Du kannst mehrere wählen)                       │
│                                                  │
│ ☑ Material-Lieferanten (Handwerk)                │
│   Baustoff, Werkzeug, Material                   │
│                                                  │
│ ☑ IT/Software (SaaS & Lizenzen)                  │
│   Software-Abos, Cloud-Dienste                   │
│                                                  │
│ ☐ Bürobedarf & Verbrauchsmaterial                │
│   Büromaterial, Druckerpatronen                  │
│                                                  │
│ ☑ Dienstleister - Fixkosten                      │
│   Miete, Strom, Telefon, Versicherungen          │
│                                                  │
│ ☐ Wareneinkauf - Großhändler                     │
│   Wiederverkäufer, Produzenten                   │
│                                                  │
│ ☐ Freiberufler - Subunternehmer                  │
│   Freie Mitarbeiter, Dienstleister               │
│                                                  │
│ ℹ️ Template passt Felder an deine Anforderungen!│
│                                                  │
│ [Zurück]                         [Weiter]        │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Vorteile:**
- ✅ **Fokussiert**: Nur relevante Felder für Lieferanten-Art
- ✅ **Geführt**: Pflichtfelder an Branche angepasst
- ✅ **Compliance**: § 13b UStG (Reverse Charge) bei Subunternehmern
- ✅ **Flexibel**: Mehrere Templates gleichzeitig nutzbar

**Status:** 🔜 **Für v2.0 geplant** (v1.0 nutzt "Standard"-Template)

---

#### **💻 Python-Modell** ⭐ NEU

```python
# models.py
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

@dataclass
class Lieferant:
    id: Optional[int] = None

    # Stammdaten
    lieferantennummer: Optional[str] = None  # "L-001" (auto)
    name: str = ''  # Pflichtfeld ⭐

    # Adresse
    strasse: Optional[str] = None
    hausnummer: Optional[str] = None
    plz: Optional[str] = None
    ort: Optional[str] = None
    land: str = 'DE'

    # Kontakt (Firma)
    telefon: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None

    # Kontaktperson ⭐ NEU
    kontaktperson_name: Optional[str] = None
    kontaktperson_telefon: Optional[str] = None
    kontaktperson_email: Optional[str] = None

    # Unternehmensdetails ⭐ NEU
    handelsregisternummer: Optional[str] = None
    steuernummer: Optional[str] = None

    # Steuerlich
    ust_idnr: Optional[str] = None

    # Standard-Kategorie
    standard_kategorie_id: Optional[int] = None

    # Metadaten
    beschreibung: Optional[str] = None  # ⭐ NEU
    erstellt_am: Optional[datetime] = None
    aktualisiert_am: Optional[datetime] = None

    # Statistiken
    anzahl_rechnungen: int = 0
    ausgaben_gesamt: Decimal = Decimal('0.00')
    letzte_rechnung_datum: Optional[date] = None

    @property
    def display_name(self) -> str:
        """
        Anzeigename für UI
        """
        if self.kontaktperson_name:
            return f"{self.name} ({self.kontaktperson_name})"
        return self.name

    def validate(self) -> list[str]:
        """
        Validiert Pflichtfelder
        """
        errors = []

        if not self.name:
            errors.append("Name ist Pflichtfeld")

        # USt-IdNr. bei EU-Lieferanten empfohlen (Reverse Charge)
        if self.land != 'DE' and self.land in EU_LAENDER and not self.ust_idnr:
            errors.append("Warnung: USt-IdNr. bei EU-Lieferanten empfohlen (für Reverse Charge)")

        # Steuernummer bei Subunternehmern Pflicht (§ 13b UStG)
        if self.standard_kategorie_id and self._ist_bau_dienstleistung():
            if not self.steuernummer:
                errors.append("Warnung: Steuernummer bei Bau-Dienstleistern Pflicht (§ 13b UStG)")

        return errors

    def _ist_bau_dienstleistung(self) -> bool:
        """
        Prüft ob Kategorie = Bau-Dienstleistung (für § 13b UStG)
        """
        # Implementierung hängt von Kategorien ab
        return False  # Placeholder
```

---

### **8.11 DSGVO-Compliance für Stammdaten** ⚠️ WICHTIG

**Gilt für:** Kundenstamm UND Lieferantenstamm

---

#### **🔐 Rechtsgrundlagen für Speicherung**

**Art. 6 Abs. 1 DSGVO - Rechtmäßigkeit der Verarbeitung:**

```
┌─────────────────────────────────────────────────┐
│ Warum dürfen wir Kundendaten speichern?        │
├─────────────────────────────────────────────────┤
│                                                 │
│ ✅ Art. 6 Abs. 1 lit. b DSGVO                  │
│    "Vertragserfüllung"                          │
│    → Rechnungsstellung erfordert Kundendaten   │
│                                                 │
│ ✅ Art. 6 Abs. 1 lit. c DSGVO                  │
│    "Rechtliche Verpflichtung"                   │
│    → §147 AO: Aufbewahrungspflicht 10 Jahre    │
│    → §257 HGB: Aufbewahrungspflicht 10 Jahre   │
│                                                 │
│ ✅ Art. 6 Abs. 1 lit. f DSGVO                  │
│    "Berechtigtes Interesse"                     │
│    → Kundenverwaltung für Geschäftszwecke      │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Wichtig:**
- **Keine Einwilligung erforderlich** (Art. 6 Abs. 1 lit. a) für Geschäftskunden
- **Aufbewahrungspflicht überwiegt Löschpflicht** während 10 Jahren
- **Danach: Löschpflicht** (Art. 17 DSGVO)

---

#### **⏰ Aufbewahrungsfristen & Löschkonzept**

**§147 AO & §257 HGB:**

```python
# Aufbewahrungsfristen
AUFBEWAHRUNGSFRISTEN = {
    'rechnungen': 10,  # Jahre (§147 Abs. 1 Nr. 1 AO)
    'belege': 10,      # Jahre (§147 Abs. 1 Nr. 4 AO)
    'buchhaltung': 10, # Jahre (§147 Abs. 1 Nr. 1 AO)
}

def berechne_aufbewahrung_bis(letzte_rechnung_datum: date) -> date:
    """
    Berechnet Ende der Aufbewahrungsfrist

    Regel: 10 Jahre ab Ende des Kalenderjahres der letzten Rechnung

    Beispiel:
    - Letzte Rechnung: 15.03.2024
    - Ende Kalenderjahr: 31.12.2024
    - Aufbewahrung bis: 31.12.2034 (10 Jahre später)
    """
    jahr_letzte_rechnung = letzte_rechnung_datum.year
    ende_kalenderjahr = date(jahr_letzte_rechnung, 12, 31)
    aufbewahrung_bis = date(jahr_letzte_rechnung + 10, 12, 31)

    return aufbewahrung_bis
```

**Konflikt: Aufbewahrungspflicht vs. Löschpflicht:**

```
Zeitstrahl:

2024        2025        ...        2034        2035
│           │                      │           │
│           │                      │           │
Rechnung    │                      │           Löschung
erstellt    │                      │           erlaubt!
            │                      │
            │<──── 10 Jahre ──────>│
            Aufbewahrungspflicht
```

**Lösung:**
1. **Während Aufbewahrungsfrist (10 Jahre):**
   - Daten NICHT löschen (§147 AO hat Vorrang)
   - Aber: **Zugriff einschränken** ("Sperrung")
   - Nur für Finanzamt/Prüfung zugänglich

2. **Nach Ablauf (nach 10 Jahren):**
   - **Automatische Löschung** (DSGVO Art. 17)
   - Oder: Anonymisierung

---

#### **📊 Datenbank-Schema mit DSGVO-Feldern**

```sql
-- Erweitert: kunden & lieferanten Tabellen
ALTER TABLE kunden ADD COLUMN gesperrt BOOLEAN DEFAULT 0;
ALTER TABLE kunden ADD COLUMN gesperrt_grund TEXT;  -- "Aufbewahrungspflicht", "Nutzer-Wunsch"
ALTER TABLE kunden ADD COLUMN gesperrt_am DATE;
ALTER TABLE kunden ADD COLUMN loesch_datum DATE;  -- Geplantes Löschdatum
ALTER TABLE kunden ADD COLUMN aufbewahrung_bis DATE;  -- Ende Aufbewahrungsfrist

ALTER TABLE lieferanten ADD COLUMN gesperrt BOOLEAN DEFAULT 0;
ALTER TABLE lieferanten ADD COLUMN gesperrt_grund TEXT;
ALTER TABLE lieferanten ADD COLUMN gesperrt_am DATE;
ALTER TABLE lieferanten ADD COLUMN loesch_datum DATE;
ALTER TABLE lieferanten ADD COLUMN aufbewahrung_bis DATE;

-- Audit-Log für DSGVO-Aktionen
CREATE TABLE dsgvo_log (
    id INTEGER PRIMARY KEY,

    -- Betroffene Person
    tabelle TEXT NOT NULL,  -- 'kunden' oder 'lieferanten'
    datensatz_id INTEGER NOT NULL,
    person_name TEXT,  -- Snapshot für Log

    -- Aktion
    aktion TEXT NOT NULL,  -- 'auskunft', 'berichtigung', 'loeschung', 'sperrung', 'export'
    durchgefuehrt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Details
    details TEXT,  -- JSON mit Details

    -- User (falls Multi-User in Zukunft)
    user_id INTEGER
);
```

---

#### **👤 Betroffenenrechte implementieren**

**Art. 15 DSGVO - Auskunftsrecht:**

```python
def dsgvo_auskunft(kunde_id: int) -> dict:
    """
    Gibt alle gespeicherten Daten über einen Kunden aus

    Returns:
        Dict mit allen Daten + Rechnungen
    """
    kunde = db.get_kunde(kunde_id)
    rechnungen = db.get_rechnungen_by_kunde(kunde_id)

    auskunft = {
        'stammdaten': {
            'kundennummer': kunde.kundennummer,
            'name': f"{kunde.vorname} {kunde.nachname}",
            'adresse': f"{kunde.strasse}, {kunde.plz} {kunde.ort}",
            'email': kunde.email,
            'telefon_mobil': kunde.telefon_mobil,
            'telefon_festnetz': kunde.telefon_festnetz,
            # ... alle Felder
        },
        'rechnungen': [
            {
                'rechnungsnummer': r.rechnungsnummer,
                'datum': r.datum,
                'betrag': r.betrag_brutto,
                'status': r.status
            }
            for r in rechnungen
        ],
        'statistiken': {
            'anzahl_rechnungen': kunde.anzahl_rechnungen,
            'umsatz_gesamt': kunde.umsatz_gesamt,
            'kunde_seit': kunde.erstellt_am,
        },
        'rechtsgrundlage': 'Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung)',
        'speicherdauer': f'Bis {kunde.aufbewahrung_bis} (§147 AO)',
    }

    # Audit-Log
    log_dsgvo_aktion('kunden', kunde_id, 'auskunft', auskunft)

    return auskunft
```

**UI - Auskunft generieren:**

```
┌──────────────────────────────────────────────────┐
│ 📄 DSGVO-Auskunft für Kunde                     │
├──────────────────────────────────────────────────┤
│                                                  │
│ Kunde: [Musterfrau, Erika ▼]                    │
│                                                  │
│ [Auskunft erstellen (PDF)]                      │
│                                                  │
│ ℹ️ Enthält alle gespeicherten Daten gemäß      │
│    Art. 15 DSGVO                                │
│                                                  │
└──────────────────────────────────────────────────┘

[Generiert PDF mit:]
- Stammdaten
- Rechnungen (Liste)
- Speicherzweck
- Rechtsgrundlage
- Speicherdauer
```

---

**Art. 16 DSGVO - Berichtigungsrecht:**

```python
def dsgvo_berichtigung(kunde_id: int, korrekturen: dict):
    """
    Korrigiert Kundendaten auf Wunsch

    Args:
        korrekturen: {'email': 'neu@beispiel.de', 'strasse': 'Neue Str. 1'}
    """
    kunde = db.get_kunde(kunde_id)

    # Alte Daten für Log speichern
    alte_daten = {k: getattr(kunde, k) for k in korrekturen.keys()}

    # Aktualisieren
    for feld, wert in korrekturen.items():
        setattr(kunde, feld, wert)

    kunde.aktualisiert_am = datetime.now()
    db.save(kunde)

    # Audit-Log
    log_dsgvo_aktion('kunden', kunde_id, 'berichtigung', {
        'alt': alte_daten,
        'neu': korrekturen
    })
```

---

**Art. 17 DSGVO - Recht auf Löschung:**

```python
def dsgvo_loeschung(kunde_id: int, grund: str = 'nutzer_wunsch'):
    """
    Löscht Kundendaten (mit Aufbewahrungspflicht-Check)

    Args:
        grund: 'nutzer_wunsch', 'frist_abgelaufen'
    """
    kunde = db.get_kunde(kunde_id)

    # Prüfung: Aufbewahrungspflicht?
    heute = date.today()
    if kunde.aufbewahrung_bis and kunde.aufbewahrung_bis > heute:
        # Noch in Aufbewahrungsfrist → NICHT löschen!
        raise ValueError(
            f"Löschung nicht möglich: Aufbewahrungspflicht bis {kunde.aufbewahrung_bis} "
            f"(§147 AO). Kunde wird stattdessen gesperrt."
        )

    # Löschung durchführen
    if grund == 'nutzer_wunsch':
        # Nutzer will Löschung → Sperrung statt Löschung
        kunde.gesperrt = True
        kunde.gesperrt_grund = 'Nutzer-Wunsch (DSGVO Art. 17)'
        kunde.gesperrt_am = heute
        kunde.loesch_datum = kunde.aufbewahrung_bis  # Löschung nach Frist
        db.save(kunde)

        log_dsgvo_aktion('kunden', kunde_id, 'sperrung', {
            'grund': grund,
            'loesch_datum': kunde.loesch_datum
        })

        return f"Kunde gesperrt. Automatische Löschung am {kunde.loesch_datum}."

    elif grund == 'frist_abgelaufen':
        # Frist abgelaufen → Endgültige Löschung

        # Option 1: Vollständige Löschung
        db.delete_kunde(kunde_id)

        # Option 2: Anonymisierung (besser für Statistiken)
        # kunde.vorname = 'GELÖSCHT'
        # kunde.nachname = 'GELÖSCHT'
        # kunde.email = None
        # kunde.telefon_mobil = None
        # ...
        # db.save(kunde)

        log_dsgvo_aktion('kunden', kunde_id, 'loeschung', {
            'grund': grund
        })

        return "Kunde gelöscht."
```

**UI - Löschung beantragen:**

```
┌──────────────────────────────────────────────────┐
│ 🗑️ Kundendaten löschen                          │
├──────────────────────────────────────────────────┤
│                                                  │
│ Kunde: Erika Musterfrau (K-042)                 │
│                                                  │
│ ⚠️ WARNUNG:                                     │
│ Dieser Kunde hat noch Rechnungen!               │
│                                                  │
│ Letzte Rechnung: 15.03.2024 (RE-2024-123)       │
│ Aufbewahrungspflicht bis: 31.12.2034            │
│                                                  │
│ ❌ Löschung NICHT möglich (§147 AO)             │
│                                                  │
│ ✅ Stattdessen: Kunde sperren                   │
│    → Nicht mehr in Suche/Auswahl sichtbar       │
│    → Automatische Löschung am 31.12.2034        │
│                                                  │
│ [Abbrechen]          [Kunde sperren]            │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

**Art. 20 DSGVO - Datenportabilität:**

```python
def dsgvo_export(kunde_id: int) -> str:
    """
    Exportiert Kundendaten in maschinenlesbarem Format

    Returns:
        JSON-String mit allen Daten
    """
    kunde = db.get_kunde(kunde_id)
    rechnungen = db.get_rechnungen_by_kunde(kunde_id)

    export_data = {
        'stammdaten': {
            'kundennummer': kunde.kundennummer,
            'typ': kunde.typ,
            'vorname': kunde.vorname,
            'nachname': kunde.nachname,
            # ... alle Felder
        },
        'rechnungen': [
            {
                'rechnungsnummer': r.rechnungsnummer,
                'datum': r.datum.isoformat(),
                'betrag_netto': str(r.betrag_netto),
                'betrag_brutto': str(r.betrag_brutto),
                # ... alle Felder
            }
            for r in rechnungen
        ],
        'export_datum': datetime.now().isoformat(),
        'format_version': '1.0'
    }

    json_export = json.dumps(export_data, indent=2, ensure_ascii=False)

    log_dsgvo_aktion('kunden', kunde_id, 'export', {'format': 'JSON'})

    return json_export
```

---

#### **🔗 Löschstrategie für verknüpfte Daten (Rechnungen)** ⚠️ **KRITISCH**

**Problem:**
- Kunde verlangt Löschung seiner Daten (Art. 17 DSGVO)
- ABER: Rechnungen müssen 10 Jahre aufbewahrt werden (§147 AO)
- **Konflikt:** Kundendaten sind in Rechnungen enthalten!

**Frage:** Was passiert mit den Kundendaten in Rechnungen, wenn der Kunde gelöscht wird?

---

##### **Rechtsgrundlage: Ausnahme vom Löschrecht**

**Art. 17 Abs. 3 lit. b DSGVO:**

```
Das Recht auf Löschung besteht NICHT, soweit die Verarbeitung
erforderlich ist zur Erfüllung einer rechtlichen Verpflichtung.
```

**§147 AO & §257 HGB:**
- 10-jährige Aufbewahrungspflicht für Rechnungen
- Rechnung muss **vollständig nachvollziehbar** sein
- Kundendaten (Name, Adresse, etc.) sind **Teil der Rechnung**

**Ergebnis:**
- ✅ **Kundendaten in Rechnungen DÜRFEN gespeichert bleiben** (auch nach Löschantrag)
- ❌ **Kundenstammdaten MÜSSEN gesperrt werden** (bis Frist abläuft)

---

##### **Lösung: Denormalisierung der Kundendaten**

**Strategie:**
1. **Rechnungen enthalten KOPIE der Kundendaten** (nicht Foreign Key)
2. **Kundenstamm wird gesperrt/pseudonymisiert** (bei Löschantrag)
3. **Rechnungen bleiben unverändert** (Aufbewahrungspflicht)

**Datenbank-Design:**

```sql
-- ❌ FALSCH: Foreign Key (führt zu Problemen bei Löschung)
CREATE TABLE rechnungen (
    id INTEGER PRIMARY KEY,
    kunde_id INTEGER,  -- ❌ Foreign Key → Kunde kann nicht gelöscht werden!
    FOREIGN KEY (kunde_id) REFERENCES kunden(id)
);

-- ✅ RICHTIG: Denormalisierte Kundendaten
CREATE TABLE rechnungen (
    id INTEGER PRIMARY KEY,
    rechnungsnummer TEXT UNIQUE,
    datum DATE,

    -- ═══════════════════════════════════════════════════
    -- KUNDENDATEN (KOPIE ZUM ZEITPUNKT DER RECHNUNG)
    -- ═══════════════════════════════════════════════════

    -- Optional: Referenz auf Kundenstamm (für Statistiken)
    -- Wird NULL gesetzt, wenn Kunde gelöscht wird
    kunde_id INTEGER,  -- Optional, kann NULL sein

    -- Kundendaten (denormalisiert, immer gespeichert)
    kunde_typ TEXT,  -- 'privat', 'firma'

    -- Person
    kunde_anrede TEXT,
    kunde_vorname TEXT,
    kunde_nachname TEXT,

    -- Firma
    kunde_firmenname TEXT,
    kunde_rechtsform TEXT,

    -- Adresse (PFLICHT für Rechnung)
    kunde_strasse TEXT NOT NULL,
    kunde_hausnummer TEXT,
    kunde_plz TEXT NOT NULL,
    kunde_ort TEXT NOT NULL,
    kunde_land TEXT DEFAULT 'DE',

    -- Kontakt
    kunde_email TEXT,
    kunde_telefon TEXT,
    kunde_website TEXT,

    -- Steuerlich
    kunde_steuernummer TEXT,
    kunde_ust_idnr TEXT,

    -- ═══════════════════════════════════════════════════
    -- RECHNUNGSDATEN
    -- ═══════════════════════════════════════════════════

    betrag_netto DECIMAL(10,2),
    betrag_brutto DECIMAL(10,2),
    -- ... weitere Felder

    -- Foreign Key (optional, kann NULL sein)
    FOREIGN KEY (kunde_id) REFERENCES kunden(id) ON DELETE SET NULL
    --                                              ^^^^^^^^^^^^^^^^^
    --                                              Bei Löschung: kunde_id → NULL
    --                                              Kundendaten bleiben erhalten!
);
```

**Wichtig:**
- `kunde_id` ist **OPTIONAL** (nur für Statistiken, Verknüpfung mit Kundenstamm)
- `kunde_*` Felder sind **DENORMALISIERT** (immer ausgefüllt, auch wenn `kunde_id` NULL)
- Bei Löschung: `kunde_id` wird `NULL`, aber `kunde_name`, `kunde_adresse` etc. bleiben!

---

##### **Workflow: Kunde will Löschung**

**Szenario:**
1. Kunde "Erika Musterfrau" (ID 42) verlangt Löschung (Art. 17 DSGVO)
2. Letzte Rechnung: 15.03.2024 (RE-2024-123)
3. Aufbewahrungspflicht bis: 31.12.2034

**Schritt 1: Prüfung**

```python
def kunde_loeschen(kunde_id: int):
    kunde = db.get_kunde(kunde_id)
    rechnungen = db.get_rechnungen_by_kunde(kunde_id)

    # Prüfung: Hat Kunde Rechnungen?
    if rechnungen:
        letzte_rechnung = max(rechnungen, key=lambda r: r.datum)
        aufbewahrung_bis = berechne_aufbewahrung_bis(letzte_rechnung.datum)

        if aufbewahrung_bis > date.today():
            # Aufbewahrungspflicht noch aktiv
            raise ValueError(
                f"Löschung nicht möglich: Aufbewahrungspflicht bis {aufbewahrung_bis} (§147 AO)\n"
                f"Kunde wird stattdessen gesperrt."
            )
```

**Schritt 2: Sperrung im Kundenstamm**

```python
    # Kundenstamm sperren
    kunde.gesperrt = True
    kunde.gesperrt_grund = 'DSGVO Art. 17 - Löschantrag vom ' + str(date.today())
    kunde.gesperrt_am = date.today()
    kunde.loesch_datum = aufbewahrung_bis

    # Optional: Pseudonymisierung für zusätzlichen Schutz
    kunde.email = None
    kunde.telefon_mobil = None
    kunde.telefon_festnetz = None
    kunde.website = None
    kunde.notizen = '[GESPERRT - DSGVO]'

    db.save(kunde)

    log_dsgvo_aktion('kunden', kunde_id, 'sperrung', {
        'grund': 'Löschantrag',
        'loesch_datum': aufbewahrung_bis,
        'anzahl_rechnungen': len(rechnungen)
    })
```

**Schritt 3: Rechnungen bleiben unverändert**

```python
    # Rechnungen NICHT ändern!
    # - kunde_id bleibt erhalten (oder wird NULL gesetzt, je nach Design)
    # - kunde_name, kunde_adresse etc. bleiben IMMER erhalten (denormalisiert)

    # Optional: kunde_id auf NULL setzen (Verknüpfung trennen)
    db.execute("""
        UPDATE rechnungen
        SET kunde_id = NULL
        WHERE kunde_id = ?
    """, (kunde_id,))

    # WICHTIG: Kundendaten (kunde_name, kunde_adresse etc.) bleiben!
```

**Ergebnis:**
- ✅ **Kundenstamm**: Gesperrt, nicht mehr sichtbar, optional pseudonymisiert
- ✅ **Rechnungen**: Unverändert, alle Kundendaten erhalten
- ✅ **Compliance**: Aufbewahrungspflicht erfüllt, Löschrecht respektiert

---

##### **Alternative Strategien**

**Strategie 1: Vollständige Denormalisierung (empfohlen)**

```sql
-- Rechnungen enthalten ALLE Kundendaten (keine kunde_id)
CREATE TABLE rechnungen (
    id INTEGER PRIMARY KEY,
    -- Kundendaten (vollständig denormalisiert)
    kunde_typ TEXT,
    kunde_name TEXT,
    kunde_adresse TEXT,
    -- ... alle relevanten Felder
    -- KEIN kunde_id Foreign Key!
);
```

**Vorteile:**
- ✅ Keine Abhängigkeit zum Kundenstamm
- ✅ Kunde kann vollständig gelöscht werden (nach Frist)
- ✅ Rechnung bleibt immer nachvollziehbar

**Nachteile:**
- ❌ Keine Statistiken pro Kunde möglich (nach Löschung)
- ❌ Mehr Speicherplatz

---

**Strategie 2: Foreign Key mit ON DELETE SET NULL (hybrid)**

```sql
CREATE TABLE rechnungen (
    id INTEGER PRIMARY KEY,
    kunde_id INTEGER,  -- Optional (für Statistiken)
    -- Kundendaten (denormalisiert, immer ausgefüllt)
    kunde_name TEXT NOT NULL,
    kunde_adresse TEXT NOT NULL,
    -- ...
    FOREIGN KEY (kunde_id) REFERENCES kunden(id) ON DELETE SET NULL
);
```

**Vorteile:**
- ✅ Statistiken pro Kunde möglich (solange Kunde existiert)
- ✅ Rechnung bleibt nachvollziehbar (auch nach Löschung)
- ✅ kunde_id optional, Kundendaten immer da

**Nachteile:**
- ⚠️ Komplexer (zwei Datenquellen: kunde_id + denormalisierte Felder)

---

**Strategie 3: Pseudonymisierung (NICHT empfohlen für Rechnungen!)**

```python
# ❌ NICHT empfohlen für Rechnungen!
def pseudonymisiere_kunde(kunde_id: int):
    kunde = db.get_kunde(kunde_id)
    kunde.vorname = f"KUNDE-{kunde_id}"
    kunde.nachname = "GELÖSCHT"
    kunde.email = f"geloescht-{kunde_id}@example.com"
    kunde.telefon_mobil = None
    # ...
    db.save(kunde)
```

**Problem:**
- ❌ Rechnung nicht mehr nachvollziehbar (Name geändert)
- ❌ Finanzamt könnte Bedenken haben (Manipulation?)
- ❌ Nicht GoBD-konform (Unveränderbarkeit)

**Nur verwenden für:**
- ✅ Kundenstamm (nach Sperrung)
- ❌ NICHT für Rechnungen!

---

##### **Empfohlene Implementierung**

**Datenbank-Schema:**

```sql
-- Strategie 2: Hybrid (Foreign Key + Denormalisierung)

CREATE TABLE rechnungen (
    id INTEGER PRIMARY KEY,
    rechnungsnummer TEXT UNIQUE,
    datum DATE,

    -- OPTIONAL: Referenz auf Kundenstamm (für Statistiken, kann NULL werden)
    kunde_id INTEGER,

    -- PFLICHT: Denormalisierte Kundendaten (immer ausgefüllt)
    kunde_typ TEXT NOT NULL,
    kunde_anrede TEXT,
    kunde_vorname TEXT,
    kunde_nachname TEXT,
    kunde_firmenname TEXT,
    kunde_strasse TEXT NOT NULL,
    kunde_hausnummer TEXT,
    kunde_plz TEXT NOT NULL,
    kunde_ort TEXT NOT NULL,
    kunde_land TEXT DEFAULT 'DE',
    kunde_email TEXT,
    kunde_telefon TEXT,
    kunde_ust_idnr TEXT,

    -- ... Rechnungsdaten

    FOREIGN KEY (kunde_id) REFERENCES kunden(id) ON DELETE SET NULL
);
```

**Rechnung erstellen:**

```python
def erstelle_rechnung(kunde_id: int, positionen: list):
    kunde = db.get_kunde(kunde_id)

    # Kundendaten KOPIEREN (denormalisieren)
    rechnung = Rechnung(
        kunde_id=kunde_id,  # Optional, für Statistiken

        # Kundendaten zum Zeitpunkt der Rechnungserstellung
        kunde_typ=kunde.typ,
        kunde_anrede=kunde.anrede,
        kunde_vorname=kunde.vorname,
        kunde_nachname=kunde.nachname,
        kunde_firmenname=kunde.firmenname,
        kunde_strasse=kunde.strasse,
        kunde_hausnummer=kunde.hausnummer,
        kunde_plz=kunde.plz,
        kunde_ort=kunde.ort,
        kunde_land=kunde.land,
        kunde_email=kunde.email,
        kunde_telefon=kunde.telefon_mobil or kunde.telefon_festnetz,
        kunde_ust_idnr=kunde.ust_idnr,

        # ... Rechnungspositionen
    )

    db.save(rechnung)
    return rechnung
```

**Kunde löschen (nach Frist):**

```python
def loesche_kunde_nach_frist(kunde_id: int):
    # Prüfung: Frist abgelaufen?
    kunde = db.get_kunde(kunde_id)
    if kunde.aufbewahrung_bis > date.today():
        raise ValueError("Aufbewahrungsfrist noch nicht abgelaufen!")

    # 1. kunde_id in Rechnungen auf NULL setzen
    db.execute("UPDATE rechnungen SET kunde_id = NULL WHERE kunde_id = ?", (kunde_id,))

    # 2. Kundenstamm löschen
    db.delete_kunde(kunde_id)

    # 3. Audit-Log
    log_dsgvo_aktion('kunden', kunde_id, 'loeschung', {
        'grund': 'Aufbewahrungsfrist abgelaufen'
    })

    # WICHTIG: Kundendaten in Rechnungen bleiben erhalten!
    # (kunde_typ, kunde_name, kunde_adresse etc. sind denormalisiert)
```

---

##### **UI: Löschantrag mit Warnung**

```
┌──────────────────────────────────────────────────────────────┐
│ 🗑️ Kundendaten löschen - DSGVO Art. 17                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Kunde: Erika Musterfrau (K-042)                             │
│                                                              │
│ ⚠️ WICHTIG: Dieser Kunde hat Rechnungen!                   │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ 📋 VERKNÜPFTE DATEN                                  │   │
│ ├──────────────────────────────────────────────────────┤   │
│ │ Anzahl Rechnungen: 15                                │   │
│ │ Letzte Rechnung: 15.03.2024 (RE-2024-123)           │   │
│ │ Aufbewahrungspflicht bis: 31.12.2034                │   │
│ │                                                      │   │
│ │ ℹ️ Was passiert mit den Rechnungen?                 │   │
│ │                                                      │   │
│ │ ✅ Rechnungen bleiben erhalten (§147 AO)            │   │
│ │    - Kundendaten in Rechnung: UNVERÄNDERT           │   │
│ │    - Name, Adresse bleiben gespeichert              │   │
│ │                                                      │   │
│ │ ⚠️ Kundenstamm wird gesperrt:                       │   │
│ │    - Nicht mehr in Suche sichtbar                   │   │
│ │    - Kann nicht mehr bearbeitet werden              │   │
│ │    - E-Mail/Telefon werden gelöscht (optional)      │   │
│ │    - Automatische Löschung: 31.12.2034              │   │
│ │                                                      │   │
│ │ 📋 Rechtsgrundlage:                                  │   │
│ │ Art. 17 Abs. 3 lit. b DSGVO - Ausnahme vom          │   │
│ │ Löschrecht bei rechtlicher Aufbewahrungspflicht     │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                              │
│ Optionen:                                                    │
│                                                              │
│ ○ Kundenstamm sperren (empfohlen)                          │
│   Daten werden gesperrt, aber nicht gelöscht.              │
│   Automatische Löschung nach Fristablauf.                  │
│                                                              │
│ ○ Kundenstamm sperren + E-Mail/Telefon löschen             │
│   Zusätzlicher Schutz durch Pseudonymisierung.             │
│   Rechnungen bleiben vollständig erhalten.                 │
│                                                              │
│ ☐ Kunde über Sperrung informieren (E-Mail)                 │
│                                                              │
│ [Abbrechen]                         [Kunde sperren]         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

##### **Zusammenfassung**

**Problem:**
Kunde will Löschung, aber Rechnungen müssen 10 Jahre aufbewahrt werden.

**Lösung:**
1. ✅ **Denormalisierung**: Kundendaten werden in Rechnung kopiert
2. ✅ **Sperrung**: Kundenstamm wird gesperrt (nicht gelöscht)
3. ✅ **Rechtsgrundlage**: Art. 17 Abs. 3 lit. b DSGVO (Ausnahme vom Löschrecht)
4. ✅ **Automatische Löschung**: Nach Ablauf der 10-Jahres-Frist

**Datenbank-Design:**
- `rechnungen.kunde_id` → `ON DELETE SET NULL` (optional, für Statistiken)
- `rechnungen.kunde_*` → Denormalisierte Kundendaten (immer ausgefüllt)

**Compliance:**
- ✅ DSGVO Art. 17 (Löschrecht) → Kundenstamm gesperrt
- ✅ §147 AO (Aufbewahrungspflicht) → Rechnungen bleiben erhalten
- ✅ GoBD (Unveränderbarkeit) → Rechnungen werden nicht geändert

---

#### **🤖 Automatische Löschung (Cron-Job)**

```python
# tasks/dsgvo_cleanup.py
def automatische_loeschung():
    """
    Wird täglich ausgeführt (Cron-Job)

    Löscht Kunden/Lieferanten deren Aufbewahrungsfrist abgelaufen ist
    """
    heute = date.today()

    # Kunden mit abgelaufener Frist finden
    zu_loeschen = db.execute("""
        SELECT id, name FROM kunden
        WHERE loesch_datum IS NOT NULL
        AND loesch_datum <= ?
        AND gesperrt = 1
    """, (heute,)).fetchall()

    for kunde_id, name in zu_loeschen:
        print(f"Lösche Kunde {name} (ID: {kunde_id})...")

        try:
            dsgvo_loeschung(kunde_id, grund='frist_abgelaufen')
            print(f"✅ Gelöscht: {name}")
        except Exception as e:
            print(f"❌ Fehler bei {name}: {e}")

    # Gleiches für Lieferanten
    # ...

    print(f"Automatische Löschung abgeschlossen: {len(zu_loeschen)} Datensätze gelöscht")


# Cron-Eintrag (täglich 02:00 Uhr)
# 0 2 * * * cd /pfad/zu/rechnungspilot && python tasks/dsgvo_cleanup.py
```

---

#### **🔒 Technische & Organisatorische Maßnahmen (TOM)**

**Verschlüsselung:**

```python
# config.py
DATENBANK_VERSCHLUESSELUNG = True  # SQLCipher aktivieren

# Bei SQLite-Verbindung:
import sqlcipher3
conn = sqlcipher3.connect('rechnungspilot.db')
conn.execute(f"PRAGMA key = '{MASTER_PASSWORD}'")
```

**Zugriffskontrolle:**

```python
# Nur gesperrte Kunden für Finanzamt sichtbar
def get_kunden_fuer_anzeige(include_gesperrt: bool = False):
    """
    Gibt Kunden zurück (ohne gesperrte, außer explizit gewünscht)
    """
    query = "SELECT * FROM kunden"
    if not include_gesperrt:
        query += " WHERE gesperrt = 0"

    return db.execute(query).fetchall()


# UI zeigt gesperrte Kunden NICHT in Autocomplete
```

**Audit-Logging:**

```python
def log_dsgvo_aktion(tabelle: str, datensatz_id: int, aktion: str, details: dict):
    """
    Loggt DSGVO-relevante Aktionen
    """
    db.execute("""
        INSERT INTO dsgvo_log (tabelle, datensatz_id, aktion, details)
        VALUES (?, ?, ?, ?)
    """, (tabelle, datensatz_id, aktion, json.dumps(details)))

    db.commit()
```

---

#### **📋 DSGVO-Checkliste für Setup**

```
┌──────────────────────────────────────────────────┐
│ ✅ DSGVO-Checkliste                             │
├──────────────────────────────────────────────────┤
│                                                  │
│ ☑ Datenschutzerklärung erstellt                 │
│   (siehe datenschutz.md)                         │
│                                                  │
│ ☑ Verarbeitungsverzeichnis geführt              │
│   (Art. 30 DSGVO)                                │
│                                                  │
│ ☑ Aufbewahrungsfristen implementiert            │
│   (§147 AO: 10 Jahre)                            │
│                                                  │
│ ☑ Automatische Löschung konfiguriert            │
│   (Cron-Job täglich 02:00 Uhr)                   │
│                                                  │
│ ☑ Datenbank verschlüsselt                       │
│   (SQLCipher aktiviert)                          │
│                                                  │
│ ☑ Backup verschlüsselt                          │
│   (Nextcloud mit Verschlüsselung)                │
│                                                  │
│ ☑ Audit-Logging aktiviert                       │
│   (dsgvo_log Tabelle)                            │
│                                                  │
│ ☐ Datenschutz-Folgenabschätzung (DSFA)          │
│   (Bei > 250 Mitarbeitern oder sensiblen Daten) │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

#### **📄 Datenschutzerklärung (Vorlage)**

```markdown
# Datenschutzerklärung - RechnungsFee

## 1. Verantwortlicher
[Dein Name/Firma]
[Adresse]
[E-Mail]

## 2. Welche Daten speichern wir?

### Kundendaten:
- Name, Adresse, Kontaktdaten
- Rechnungsinformationen
- Zahlungsinformationen

### Lieferantendaten:
- Name, Adresse, Kontaktdaten
- Vertragsinformationen

## 3. Rechtsgrundlage

- **Art. 6 Abs. 1 lit. b DSGVO**: Vertragserfüllung (Rechnungsstellung)
- **Art. 6 Abs. 1 lit. c DSGVO**: Rechtliche Verpflichtung (§147 AO, §257 HGB)

## 4. Speicherdauer

- **Während Geschäftsbeziehung**: Aktive Speicherung
- **Nach letzter Rechnung**: 10 Jahre (§147 AO)
- **Nach 10 Jahren**: Automatische Löschung

## 5. Ihre Rechte (Art. 15-21 DSGVO)

- **Auskunft**: Sie können jederzeit Auskunft über Ihre gespeicherten Daten erhalten
- **Berichtigung**: Fehlerhafte Daten werden korrigiert
- **Löschung**: Nach Ablauf der Aufbewahrungsfrist werden Daten gelöscht
- **Einschränkung**: Sie können die Verarbeitung einschränken lassen
- **Datenportabilität**: Sie erhalten Ihre Daten in maschinenlesbarem Format

**Kontakt für Betroffenenrechte:**
[E-Mail für DSGVO-Anfragen]

## 6. Datensicherheit

- Datenbank verschlüsselt (SQLCipher)
- Backups verschlüsselt
- Zugriffskontrolle
- Audit-Logging

## 7. Keine Weitergabe an Dritte

Ihre Daten werden NICHT an Dritte weitergegeben (außer gesetzlich verpflichtet, z.B. Finanzamt bei Prüfung).
```

---

**Status:** ✅ **DSGVO-Compliance dokumentiert**

**Wichtigste Punkte:**
1. ✅ Aufbewahrungspflicht (10 Jahre) hat Vorrang vor Löschpflicht
2. ✅ Sperrung statt Löschung während Aufbewahrungsfrist
3. ✅ Automatische Löschung nach Ablauf
4. ✅ Betroffenenrechte (Auskunft, Löschung, Export) implementiert
5. ✅ Verschlüsselung & Audit-Logging
6. ✅ Datenschutzerklärung-Vorlage

---

### **8.12 Wiederkehrende Rechnungen** 🔄 (für v2.0 vorgemerkt)

**Status:** 📋 **Für v2.0 geplant** (NICHT in MVP v1.0)

**Zweck:**
- Automatische Verwaltung von wiederkehrenden Ausgaben
- Erinnerungen für fällige Zahlungen
- Historische Nachverfolgung von Abonnements

---

#### **💡 Anwendungsfälle**

**Typische wiederkehrende Rechnungen:**

```
┌─────────────────────────────────────────────────┐
│ 🔄 WIEDERKEHRENDE AUSGABEN                      │
├─────────────────────────────────────────────────┤
│                                                 │
│ 📅 MONATLICH:                                   │
│   - Software-Abos (Adobe, Microsoft 365, etc.) │
│   - SaaS-Tools (Hosting, Cloud-Dienste)        │
│   - Miete (Büro, Lager)                         │
│   - Versicherungen (monatliche Zahlung)        │
│   - Leasingraten                                │
│                                                 │
│ 📅 JÄHRLICH:                                    │
│   - Domain-Renewals (example.com)              │
│   - Software-Lizenzen (jährliche Verlängerung) │
│   - Versicherungen (Jahresprämie)              │
│   - Mitgliedschaften (IHK, Verbände)           │
│   - Zertifikate (SSL, Code Signing)            │
│                                                 │
│ 📅 QUARTALSWEISE:                               │
│   - Steuervorauszahlungen                       │
│   - Quartalsberichte (Abonnements)             │
│                                                 │
│ 📅 WÖCHENTLICH:                                 │
│   - Reinigungsdienst                            │
│   - Wartungsverträge                            │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

#### **🎯 Geplante Features**

**Kernfunktionen:**

1. **Intervalle:**
   - Täglich, Wöchentlich, Monatlich, Quartalsweise, Halbjährlich, Jährlich
   - Benutzerdefinierte Intervalle (z.B. "alle 3 Monate", "alle 2 Jahre")

2. **Automatische Erstellung:**
   - Rechnung wird automatisch importiert/erstellt
   - E-Mail-Benachrichtigung bei Fälligkeit
   - Optional: Automatische Zahlung (z.B. via SEPA-Lastschrift)

3. **Vorlagen:**
   - Wiederkehrende Rechnung basiert auf Vorlage
   - Betrag, Lieferant, Kategorie vordefiniert
   - Automatische Anpassung (z.B. Preiserhöhungen)

4. **Benachrichtigungen:**
   - X Tage vor Fälligkeit (z.B. 7 Tage vorher)
   - Bei überfälligen Rechnungen
   - Bei automatischer Verlängerung

5. **Start-/Enddatum:**
   - Startdatum: Wann beginnt das Abo?
   - Enddatum: Optional (z.B. Vertrag läuft 2 Jahre)
   - Automatische Verlängerung (mit Kündigungsfrist)

6. **Preisverlauf:**
   - Historische Preise tracken
   - Erkennung von Preiserhöhungen
   - Vergleich Jahr-zu-Jahr

---

#### **📊 Datenbank-Schema**

```sql
CREATE TABLE wiederkehrende_rechnungen (
    id INTEGER PRIMARY KEY,

    -- Stammdaten
    bezeichnung TEXT NOT NULL,  -- "Adobe Creative Cloud Abo"
    beschreibung TEXT,

    -- Lieferant (optional, wenn aus Stammdaten)
    lieferant_id INTEGER,
    lieferant_name TEXT,  -- Falls nicht im Stamm

    -- Kategorie
    kategorie_id INTEGER NOT NULL,

    -- Betrag
    betrag_netto DECIMAL(10,2) NOT NULL,
    betrag_brutto DECIMAL(10,2) NOT NULL,
    umsatzsteuer_satz DECIMAL(5,2) DEFAULT 19.0,

    -- Intervall
    intervall_typ TEXT NOT NULL,  -- 'taeglich', 'woechentlich', 'monatlich', 'quartalsweise', 'halbjaehrlich', 'jaehrlich', 'benutzerdefiniert'
    intervall_anzahl INTEGER DEFAULT 1,  -- z.B. 3 für "alle 3 Monate"
    intervall_einheit TEXT,  -- 'tage', 'wochen', 'monate', 'jahre' (bei benutzerdefiniert)

    -- Start-/Enddatum
    start_datum DATE NOT NULL,
    ende_datum DATE,  -- NULL = unbegrenzt
    kuendigungsfrist_tage INTEGER,  -- z.B. 30 Tage

    -- Verlängerung
    automatische_verlaengerung BOOLEAN DEFAULT 1,
    verlaengerung_intervall_monate INTEGER DEFAULT 12,  -- z.B. 12 Monate Verlängerung

    -- Benachrichtigungen
    benachrichtigung_tage_vorher INTEGER DEFAULT 7,  -- 7 Tage vor Fälligkeit
    benachrichtigung_email TEXT,

    -- Status
    ist_aktiv BOOLEAN DEFAULT 1,
    ist_pausiert BOOLEAN DEFAULT 0,

    -- Letzte Erstellung
    letzte_rechnung_datum DATE,
    naechste_rechnung_datum DATE,  -- Berechnet

    -- Metadaten
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    aktualisiert_am TIMESTAMP,

    -- Foreign Keys
    FOREIGN KEY (lieferant_id) REFERENCES lieferanten(id),
    FOREIGN KEY (kategorie_id) REFERENCES kategorien(id),

    -- Constraints
    CHECK (intervall_typ IN ('taeglich', 'woechentlich', 'monatlich', 'quartalsweise', 'halbjaehrlich', 'jaehrlich', 'benutzerdefiniert'))
);

-- Historie der generierten Rechnungen
CREATE TABLE wiederkehrende_rechnungen_historie (
    id INTEGER PRIMARY KEY,
    wiederkehrende_rechnung_id INTEGER NOT NULL,
    rechnung_id INTEGER,  -- Verknüpfung zur eigentlichen Rechnung
    faelligkeit_datum DATE NOT NULL,
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    betrag_netto DECIMAL(10,2),
    betrag_brutto DECIMAL(10,2),
    status TEXT,  -- 'erstellt', 'bezahlt', 'ueberfaellig', 'storniert'

    FOREIGN KEY (wiederkehrende_rechnung_id) REFERENCES wiederkehrende_rechnungen(id),
    FOREIGN KEY (rechnung_id) REFERENCES rechnungen(id)
);

-- Index für schnelle Abfragen
CREATE INDEX idx_wiederkehrend_naechste ON wiederkehrende_rechnungen(naechste_rechnung_datum);
CREATE INDEX idx_wiederkehrend_aktiv ON wiederkehrende_rechnungen(ist_aktiv);
```

---

#### **💻 Code-Implementierung (Konzept)**

```python
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

@dataclass
class WiederkehrendeRechnung:
    id: Optional[int] = None
    bezeichnung: str = ''  # "Adobe Creative Cloud Abo"
    beschreibung: Optional[str] = None

    # Lieferant
    lieferant_id: Optional[int] = None
    lieferant_name: Optional[str] = None

    # Kategorie
    kategorie_id: int = 0

    # Betrag
    betrag_netto: Decimal = Decimal('0.00')
    betrag_brutto: Decimal = Decimal('0.00')
    umsatzsteuer_satz: Decimal = Decimal('19.0')

    # Intervall
    intervall_typ: str = 'monatlich'  # 'taeglich', 'woechentlich', 'monatlich', etc.
    intervall_anzahl: int = 1
    intervall_einheit: Optional[str] = None

    # Start-/Enddatum
    start_datum: date = date.today()
    ende_datum: Optional[date] = None
    kuendigungsfrist_tage: Optional[int] = None

    # Verlängerung
    automatische_verlaengerung: bool = True
    verlaengerung_intervall_monate: int = 12

    # Benachrichtigungen
    benachrichtigung_tage_vorher: int = 7
    benachrichtigung_email: Optional[str] = None

    # Status
    ist_aktiv: bool = True
    ist_pausiert: bool = False

    # Letzte Erstellung
    letzte_rechnung_datum: Optional[date] = None
    naechste_rechnung_datum: Optional[date] = None

    def berechne_naechstes_datum(self) -> date:
        """
        Berechnet nächstes Fälligkeitsdatum

        Returns:
            Nächstes Datum
        """
        if not self.letzte_rechnung_datum:
            # Erste Rechnung
            return self.start_datum

        # Intervall berechnen
        if self.intervall_typ == 'taeglich':
            delta = timedelta(days=self.intervall_anzahl)
        elif self.intervall_typ == 'woechentlich':
            delta = timedelta(weeks=self.intervall_anzahl)
        elif self.intervall_typ == 'monatlich':
            # Monatlich ist komplexer (unterschiedliche Monatslängen)
            naechstes = self.letzte_rechnung_datum
            for _ in range(self.intervall_anzahl):
                naechstes = self._add_month(naechstes)
            return naechstes
        elif self.intervall_typ == 'quartalsweise':
            naechstes = self.letzte_rechnung_datum
            for _ in range(3 * self.intervall_anzahl):
                naechstes = self._add_month(naechstes)
            return naechstes
        elif self.intervall_typ == 'halbjaehrlich':
            naechstes = self.letzte_rechnung_datum
            for _ in range(6 * self.intervall_anzahl):
                naechstes = self._add_month(naechstes)
            return naechstes
        elif self.intervall_typ == 'jaehrlich':
            naechstes = self.letzte_rechnung_datum
            for _ in range(12 * self.intervall_anzahl):
                naechstes = self._add_month(naechstes)
            return naechstes
        elif self.intervall_typ == 'benutzerdefiniert':
            if self.intervall_einheit == 'tage':
                delta = timedelta(days=self.intervall_anzahl)
            elif self.intervall_einheit == 'wochen':
                delta = timedelta(weeks=self.intervall_anzahl)
            elif self.intervall_einheit == 'monate':
                naechstes = self.letzte_rechnung_datum
                for _ in range(self.intervall_anzahl):
                    naechstes = self._add_month(naechstes)
                return naechstes
            elif self.intervall_einheit == 'jahre':
                naechstes = self.letzte_rechnung_datum
                for _ in range(12 * self.intervall_anzahl):
                    naechstes = self._add_month(naechstes)
                return naechstes
        else:
            raise ValueError(f"Ungültiger Intervall-Typ: {self.intervall_typ}")

        return self.letzte_rechnung_datum + delta

    def _add_month(self, datum: date) -> date:
        """
        Fügt einen Monat zu einem Datum hinzu

        Args:
            datum: Ausgangsdatum

        Returns:
            Datum + 1 Monat
        """
        month = datum.month
        year = datum.year

        if month == 12:
            month = 1
            year += 1
        else:
            month += 1

        # Tag anpassen (z.B. 31.01. + 1 Monat = 28./29.02.)
        day = min(datum.day, self._days_in_month(year, month))

        return date(year, month, day)

    def _days_in_month(self, year: int, month: int) -> int:
        """Gibt Anzahl Tage im Monat zurück"""
        if month in [1, 3, 5, 7, 8, 10, 12]:
            return 31
        elif month in [4, 6, 9, 11]:
            return 30
        else:  # Februar
            # Schaltjahr?
            if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
                return 29
            else:
                return 28

    def ist_faellig(self) -> bool:
        """
        Prüft, ob Rechnung fällig ist

        Returns:
            True, wenn heute >= naechste_rechnung_datum
        """
        if not self.ist_aktiv or self.ist_pausiert:
            return False

        if not self.naechste_rechnung_datum:
            self.naechste_rechnung_datum = self.berechne_naechstes_datum()

        return date.today() >= self.naechste_rechnung_datum

    def ist_ende_erreicht(self) -> bool:
        """
        Prüft, ob Enddatum erreicht ist

        Returns:
            True, wenn ende_datum erreicht
        """
        if not self.ende_datum:
            return False  # Unbegrenzt

        return date.today() >= self.ende_datum


# Cron-Job: Täglich ausführen
def erstelle_faellige_rechnungen():
    """
    Erstellt automatisch fällige wiederkehrende Rechnungen

    Wird täglich ausgeführt (z.B. 06:00 Uhr morgens)
    """
    heute = date.today()

    # Alle aktiven wiederkehrenden Rechnungen finden
    wiederkehrend = db.execute("""
        SELECT * FROM wiederkehrende_rechnungen
        WHERE ist_aktiv = 1
          AND ist_pausiert = 0
          AND naechste_rechnung_datum <= ?
          AND (ende_datum IS NULL OR ende_datum >= ?)
    """, (heute, heute)).fetchall()

    for wr in wiederkehrend:
        # Rechnung erstellen
        rechnung = erstelle_rechnung_aus_vorlage(wr)

        # Historie speichern
        db.execute("""
            INSERT INTO wiederkehrende_rechnungen_historie
            (wiederkehrende_rechnung_id, rechnung_id, faelligkeit_datum, betrag_netto, betrag_brutto, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (wr.id, rechnung.id, heute, wr.betrag_netto, wr.betrag_brutto, 'erstellt'))

        # Nächstes Datum berechnen
        wr.letzte_rechnung_datum = heute
        wr.naechste_rechnung_datum = wr.berechne_naechstes_datum()
        db.save(wr)

        # Benachrichtigung senden
        if wr.benachrichtigung_email:
            sende_benachrichtigung(wr, rechnung)

        print(f"✅ Wiederkehrende Rechnung erstellt: {wr.bezeichnung} ({rechnung.rechnungsnummer})")


def sende_erinnerungen():
    """
    Sendet Erinnerungen X Tage vor Fälligkeit

    Wird täglich ausgeführt
    """
    heute = date.today()

    wiederkehrend = db.execute("""
        SELECT * FROM wiederkehrende_rechnungen
        WHERE ist_aktiv = 1
          AND ist_pausiert = 0
          AND benachrichtigung_email IS NOT NULL
    """).fetchall()

    for wr in wiederkehrend:
        tage_bis_faelligkeit = (wr.naechste_rechnung_datum - heute).days

        if tage_bis_faelligkeit == wr.benachrichtigung_tage_vorher:
            # Erinnerung senden
            sende_erinnerungs_email(wr)
            print(f"📧 Erinnerung gesendet: {wr.bezeichnung} (fällig in {tage_bis_faelligkeit} Tagen)")
```

---

#### **🎨 UI-Mockups**

**Übersicht Wiederkehrende Rechnungen:**

```
┌─────────────────────────────────────────────────────────────────────┐
│ Wiederkehrende Rechnungen                                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ [ + Neue wiederkehrende Rechnung ]            [🔍 Suchen: ___]     │
│                                                                     │
│ Filter: [Alle ▼] [Aktiv ▼] [Fällig ▼]                             │
│                                                                     │
│ Bezeichnung              │ Lieferant       │ Intervall │ Nächste  │
│─────────────────────────┼─────────────────┼───────────┼──────────│
│ 📦 Adobe Creative Cloud │ Adobe Systems   │ Monatlich │ 01.01.26 │
│                          │ 52,99 € brutto  │           │ in 7 Tg  │
│─────────────────────────┼─────────────────┼───────────┼──────────│
│ 🌐 Domain example.com   │ STRATO          │ Jährlich  │ 15.03.26 │
│                          │ 12,00 € brutto  │           │ in 3 Mon │
│─────────────────────────┼─────────────────┼───────────┼──────────│
│ 💼 Microsoft 365        │ Microsoft       │ Monatlich │ 05.01.26 │
│                          │ 12,50 € brutto  │           │ ⚠️ in 1 T│
│─────────────────────────┼─────────────────┼───────────┼──────────│
│ 🏢 Büromiete             │ Hausverwaltung  │ Monatlich │ 01.01.26 │
│                          │ 500,00 € brutto │           │ in 7 Tg  │
│                                                                     │
│ Gesamt: 4 Abos │ Monatliche Kosten: ~565,49 € │ ⚠️ 1 fällig       │
└─────────────────────────────────────────────────────────────────────┘
```

**Neue Wiederkehrende Rechnung anlegen:**

```
┌──────────────────────────────────────────────────────────┐
│ Neue wiederkehrende Rechnung                             │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ STAMMDATEN:                                              │
│                                                          │
│ Bezeichnung *:  [Adobe Creative Cloud Abo___________]   │
│ Beschreibung:   [Foto & Video Plan___________________]  │
│                                                          │
│ Lieferant:      [Adobe Systems ▼]                       │
│ Kategorie *:    [Software & Lizenzen ▼]                 │
│                                                          │
│ BETRAG:                                                  │
│                                                          │
│ Netto:          [44,53] €                               │
│ USt-Satz:       [19] %                                  │
│ Brutto:         52,99 € (berechnet)                     │
│                                                          │
│ INTERVALL:                                               │
│                                                          │
│ Typ:            ● Monatlich                             │
│                 ○ Quartalsweise                         │
│                 ○ Halbjährlich                          │
│                 ○ Jährlich                              │
│                 ○ Benutzerdefiniert: [__] [Monate ▼]   │
│                                                          │
│ LAUFZEIT:                                                │
│                                                          │
│ Startdatum *:   [01.01.2024]                            │
│ Enddatum:       [ ] Unbegrenzt                          │
│                 [ ] Bis: [__________]                   │
│                                                          │
│ ☑ Automatische Verlängerung (12 Monate)                │
│ Kündigungsfrist: [30] Tage                              │
│                                                          │
│ BENACHRICHTIGUNGEN:                                      │
│                                                          │
│ ☑ Erinnerung senden [7] Tage vor Fälligkeit            │
│ E-Mail:         [admin@beispiel.de___________________]  │
│                                                          │
│ [Abbrechen]                             [Speichern]     │
└──────────────────────────────────────────────────────────┘
```

**Dashboard-Widget:**

```
┌────────────────────────────────────────┐
│ 🔄 Wiederkehrende Rechnungen           │
├────────────────────────────────────────┤
│                                        │
│ ⚠️ FÄLLIG HEUTE (1):                  │
│ - Microsoft 365 (12,50 €)             │
│   [Rechnung erstellen]                 │
│                                        │
│ 📅 FÄLLIG DIESE WOCHE (2):            │
│ - Adobe Creative Cloud (52,99 €)      │
│ - Büromiete (500,00 €)                │
│                                        │
│ 📊 STATISTIKEN:                        │
│ - Aktive Abos: 4                       │
│ - Monatlich: ~565 €                    │
│ - Jährlich: ~6.785 €                   │
│                                        │
│ [Alle anzeigen →]                      │
└────────────────────────────────────────┘
```

---

#### **📋 Workflow-Beispiele**

**Workflow 1: Domain-Renewal**

```
1. SETUP (einmalig):
   ┌──────────────────────────────────┐
   │ Bezeichnung: Domain example.com  │
   │ Lieferant: STRATO                │
   │ Kategorie: Domains & Hosting     │
   │ Betrag: 12,00 € (brutto)         │
   │ Intervall: Jährlich              │
   │ Start: 15.03.2024                │
   │ Erinnerung: 30 Tage vorher       │
   └──────────────────────────────────┘

2. AUTOMATISCH (14.02.2025):
   📧 E-Mail: "Domain example.com läuft in 30 Tagen ab (15.03.2025)"

3. AUTOMATISCH (15.03.2025):
   ✅ Rechnung automatisch erstellt (RE-2025-042)
   📧 E-Mail: "Rechnung für Domain example.com erstellt"

4. MANUELL (User):
   - Rechnung prüfen
   - Zahlung buchen
   - Fertig!
```

**Workflow 2: Software-Abo mit Preisänderung**

```
1. SETUP (einmalig):
   Bezeichnung: Adobe Creative Cloud
   Betrag: 44,53 € netto (52,99 € brutto)
   Intervall: Monatlich

2. MONAT 1-12:
   ✅ Automatische Rechnungserstellung
   ✅ Betrag: 52,99 €

3. MONAT 13 (Preiserhöhung):
   ⚠️ User erhält Rechnung: 59,99 € (statt 52,99 €)

4. USER-AKTION:
   ┌──────────────────────────────────┐
   │ ⚠️ PREISÄNDERUNG ERKANNT         │
   ├──────────────────────────────────┤
   │ Alt: 52,99 €                     │
   │ Neu: 59,99 €                     │
   │ Änderung: +7,00 € (+13,2%)       │
   │                                  │
   │ Möchtest du die wiederkehrende   │
   │ Rechnung aktualisieren?          │
   │                                  │
   │ [Nein] [Ja, aktualisieren]       │
   └──────────────────────────────────┘
```

---

#### **✅ Vorteile**

1. ✅ **Keine vergessenen Zahlungen**: Automatische Erinnerungen
2. ✅ **Budgetplanung**: Monatliche/jährliche Kosten im Blick
3. ✅ **Historische Daten**: Preisentwicklung nachvollziehbar
4. ✅ **Zeitersparnis**: Keine manuelle Erfassung jedes Mal
5. ✅ **Kündigungsfristen**: Rechtzeitige Erinnerung vor Verlängerung
6. ✅ **Kostenoptimierung**: Erkennung ungenutzter Abos

---

#### **🎯 MVP-Entscheidung**

**NICHT in v1.0:**
- v1.0 fokussiert auf Import & Verwaltung bestehender Rechnungen
- Wiederkehrende Rechnungen erfordern Automatisierung (Cron-Jobs, E-Mail)
- Komplex, aber nicht essentiell für Basis-Buchhaltung

**Für v2.0 geplant:**
- Nach v1.0 Release
- User-Feedback abwarten (Bedarf?)
- Integration mit Benachrichtigungs-System

---

#### **📝 Zusammenfassung**

**Feature:** Wiederkehrende Rechnungen für Abos, Domains, Lizenzen, Miete, etc.

**Kernfunktionen:**
- Intervalle (täglich, monatlich, jährlich, benutzerdefiniert)
- Automatische Erstellung
- Benachrichtigungen (X Tage vorher)
- Start-/Enddatum mit Kündigungsfrist
- Preisverlauf & Historie

**Status:** 🔜 **Für v2.0 vorgemerkt**

**Anwendungsfälle:**
- Software-Abos (Adobe, Microsoft, etc.)
- Domains & Hosting
- Miete & Versicherungen
- Lizenzen & Zertifikate
- Mitgliedschaften

---

### **8.9 Produktstammdaten ✅ GEKLÄRT**

**Status:** ✅ **Entscheidung getroffen**

**Entscheidung:** **Hybrid-Lösung** (wie Kundenstamm) mit Templates für verschiedene Produkttypen

---

#### **🎯 Implementierung: Hybrid-Lösung**

**Wie beim Kundenstamm:**
```
┌─────────────────────────────────────────────────┐
│ ⚙️ Einstellungen > Produktstamm                │
├─────────────────────────────────────────────────┤
│                                                 │
│ Beim Erstellen von Rechnungspositionen:       │
│                                                 │
│ ○ Artikel automatisch speichern               │
│   (Alle neuen Artikel werden ohne Nachfrage    │
│    im Produktstamm gespeichert)                │
│                                                 │
│ ● Auf Nachfrage speichern (Standard) ⭐        │
│   (Du wirst gefragt, ob der Artikel gespeichert│
│    werden soll)                                │
│                                                 │
│ ○ Artikel nicht speichern                      │
│   (Artikel werden nur in der Rechnung erfasst, │
│    kein Produktstamm)                          │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Datenbank-Einstellung:**
```sql
-- In der `user` Tabelle:
ALTER TABLE user ADD COLUMN produktstamm_modus TEXT DEFAULT 'nachfrage';
-- Werte: 'automatisch', 'nachfrage', 'nie'
```

---

#### **📊 Datenbank-Schema**

**Haupttabelle `produkte`:**

```sql
CREATE TABLE produkte (
    id INTEGER PRIMARY KEY,

    -- Stammdaten
    artikelnummer TEXT UNIQUE,  -- "ART-001" (manuell oder automatisch)
    name TEXT NOT NULL,  -- ⭐ PFLICHT: "Beratungsstunde", "Laptop Dell XPS 13"
    beschreibung TEXT,  -- Längerer Text für Rechnung

    -- Typ
    typ TEXT NOT NULL DEFAULT 'produkt',  -- 'produkt', 'dienstleistung'

    -- ═══════════════════════════════════════════════════
    -- STANDARD-FELDER (für beide Typen)
    -- ═══════════════════════════════════════════════════

    -- USt-Satz (PFLICHT)
    umsatzsteuer_satz DECIMAL(5,2) NOT NULL DEFAULT 19.0,  -- ⭐ PFLICHT

    -- Verkaufspreis (PFLICHT)
    verkaufspreis_netto DECIMAL(10,2) NOT NULL,  -- ⭐ PFLICHT
    verkaufspreis_brutto DECIMAL(10,2) GENERATED ALWAYS AS (
        verkaufspreis_netto * (1 + umsatzsteuer_satz / 100.0)
    ) STORED,

    -- ═══════════════════════════════════════════════════
    -- NUR FÜR PRODUKTE (typ='produkt')
    -- ═══════════════════════════════════════════════════

    -- Einkaufspreis (PFLICHT bei Produkten)
    einkaufspreis_netto DECIMAL(10,2),  -- ⭐ PFLICHT (bei typ='produkt')
    einkaufspreis_brutto DECIMAL(10,2) GENERATED ALWAYS AS (
        CASE
            WHEN einkaufspreis_netto IS NOT NULL
            THEN einkaufspreis_netto * (1 + umsatzsteuer_satz / 100.0)
            ELSE NULL
        END
    ) STORED,

    -- Erweiterte Felder (Produkte)
    lieferant_id INTEGER,  -- ⭐ Zuordnung zum Lieferanten
    hersteller TEXT,  -- ⭐ z.B. "Dell", "Bosch", etc.

    -- ⭐⭐ EAN-Code Support (WICHTIG!) ⭐⭐
    ean_code TEXT,  -- ⭐ EAN-13 (13-stellig) oder EAN-8 (8-stellig)
    ean_typ TEXT,  -- 'EAN-13', 'EAN-8', 'UPC', 'ISBN'

    artikelcode TEXT,  -- ⭐ Interner Code / SKU
    einheit TEXT DEFAULT 'Stück',  -- ⭐ 'Stück', 'kg', 'l', 'm', etc.

    -- Lagerbestand (erweitert)
    lagerbestand DECIMAL(10,2) DEFAULT 0.00,  -- ⭐ Aktueller Bestand
    lagerbestand_negativ_erlaubt BOOLEAN DEFAULT 0,  -- ⭐ Negativer Bestand?
    mindestbestand DECIMAL(10,2) DEFAULT 0.00,  -- ⭐ Warnung bei Unterschreitung

    -- ═══════════════════════════════════════════════════
    -- KATEGORIE (evt. später - optional für v1.0)
    -- ═══════════════════════════════════════════════════

    kategorie_id INTEGER,  -- Zuordnung zu Einnahmen-Kategorie (später)

    -- ═══════════════════════════════════════════════════
    -- METADATEN
    -- ═══════════════════════════════════════════════════

    ist_aktiv BOOLEAN DEFAULT 1,
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    aktualisiert_am TIMESTAMP,

    -- Foreign Keys
    FOREIGN KEY (lieferant_id) REFERENCES lieferanten(id),
    FOREIGN KEY (kategorie_id) REFERENCES kategorien(id)  -- Optional für später

    -- Constraints
    CHECK (typ IN ('produkt', 'dienstleistung')),
    CHECK (
        -- Bei Produkten: Einkaufspreis PFLICHT
        (typ = 'produkt' AND einkaufspreis_netto IS NOT NULL) OR
        (typ = 'dienstleistung')
    ),
    CHECK (
        -- Bei Dienstleistungen: Lagerfelder NULL
        (typ = 'produkt') OR
        (typ = 'dienstleistung' AND lagerbestand IS NULL AND mindestbestand IS NULL)
    )
);

-- Index für EAN-Code (WICHTIG für schnelle Suche!)
CREATE INDEX idx_produkte_ean ON produkte(ean_code);
CREATE INDEX idx_produkte_artikelcode ON produkte(artikelcode);
CREATE INDEX idx_produkte_name ON produkte(name);
CREATE INDEX idx_produkte_typ ON produkte(typ);
```

---

#### **🏷️ EAN-Code Support (WICHTIG!)**

**EAN-Code Typen:**

| Typ | Länge | Verwendung | Beispiel |
|-----|-------|------------|----------|
| **EAN-13** | 13 Ziffern | Standard für Retail | `4012345678901` |
| **EAN-8** | 8 Ziffern | Kleine Artikel | `12345670` |
| **UPC** | 12 Ziffern | USA/Kanada | `012345678905` |
| **ISBN** | 13 Ziffern | Bücher (seit 2007) | `978-3-16-148410-0` |

**EAN-Validierung (Prüfziffer):**

```python
def validate_ean13(ean: str) -> bool:
    """
    Validiert EAN-13 Code (Prüfziffer)

    Args:
        ean: 13-stelliger EAN-Code

    Returns:
        True, wenn gültig
    """
    if not ean or len(ean) != 13 or not ean.isdigit():
        return False

    # Prüfziffer berechnen
    checksum = 0
    for i, digit in enumerate(ean[:12]):  # Erste 12 Ziffern
        if i % 2 == 0:
            checksum += int(digit)  # Ungerade Positionen (1, 3, 5, ...) → ×1
        else:
            checksum += int(digit) * 3  # Gerade Positionen (2, 4, 6, ...) → ×3

    # Prüfziffer = (10 - (Summe mod 10)) mod 10
    check_digit = (10 - (checksum % 10)) % 10

    return int(ean[12]) == check_digit


def validate_ean8(ean: str) -> bool:
    """
    Validiert EAN-8 Code (Prüfziffer)
    """
    if not ean or len(ean) != 8 or not ean.isdigit():
        return False

    checksum = 0
    for i, digit in enumerate(ean[:7]):  # Erste 7 Ziffern
        if i % 2 == 0:
            checksum += int(digit) * 3  # Ungerade Positionen → ×3
        else:
            checksum += int(digit)  # Gerade Positionen → ×1

    check_digit = (10 - (checksum % 10)) % 10
    return int(ean[7]) == check_digit


def validate_ean(ean: str, ean_typ: str = None) -> tuple[bool, str]:
    """
    Validiert EAN-Code (auto-detect oder spezifisch)

    Args:
        ean: EAN-Code
        ean_typ: 'EAN-13', 'EAN-8', 'UPC', 'ISBN' (optional)

    Returns:
        (gültig, erkannter_typ)
    """
    if not ean:
        return False, None

    # Nur Ziffern und Bindestriche erlauben
    ean_clean = ean.replace('-', '').replace(' ', '')

    if ean_typ == 'EAN-13' or (ean_typ is None and len(ean_clean) == 13):
        if validate_ean13(ean_clean):
            return True, 'EAN-13'

    if ean_typ == 'EAN-8' or (ean_typ is None and len(ean_clean) == 8):
        if validate_ean8(ean_clean):
            return True, 'EAN-8'

    if ean_typ == 'UPC' or (ean_typ is None and len(ean_clean) == 12):
        # UPC → EAN-13 (Präfix '0' hinzufügen)
        ean13 = '0' + ean_clean
        if validate_ean13(ean13):
            return True, 'UPC'

    if ean_typ == 'ISBN' or (ean_typ is None and (ean_clean.startswith('978') or ean_clean.startswith('979'))):
        # ISBN-13 ist EAN-13
        if len(ean_clean) == 13 and validate_ean13(ean_clean):
            return True, 'ISBN'

    return False, None
```

**EAN-Scanner Integration:**

```python
def import_produkt_from_ean(ean_code: str):
    """
    Importiert Produkt aus externer Datenbank via EAN

    Quellen:
    - OpenEAN (https://openean.kaufland.de) - Kostenlos
    - EAN-Search.org API
    - GS1 API (kostenpflichtig)
    """
    # 1. Validierung
    valid, typ = validate_ean(ean_code)
    if not valid:
        raise ValueError(f"Ungültiger EAN-Code: {ean_code}")

    # 2. Suche in externer Datenbank
    produkt_info = fetch_ean_info(ean_code)  # API-Call

    # 3. Produkt anlegen
    produkt = Produkt(
        ean_code=ean_code,
        ean_typ=typ,
        name=produkt_info.get('name'),
        hersteller=produkt_info.get('brand'),
        beschreibung=produkt_info.get('description'),
        # Preise manuell ergänzen
    )

    return produkt
```

**UI - EAN-Scanner:**

```
┌────────────────────────────────────────────┐
│ Neues Produkt anlegen                      │
├────────────────────────────────────────────┤
│                                            │
│ ┌──────────────────────────────────────┐  │
│ │ 📷 EAN-Scanner                        │  │
│ ├──────────────────────────────────────┤  │
│ │                                      │  │
│ │ EAN-Code: [____________] [Scannen]   │  │
│ │                                      │  │
│ │ ℹ️ Scanne Barcode oder gib EAN ein  │  │
│ └──────────────────────────────────────┘  │
│                                            │
│ ─── ODER MANUELL EINGEBEN ───              │
│                                            │
│ Name *: [_________________________]        │
│ Hersteller: [____________________]         │
│ EAN-Code: [_______________] ✅ Gültig     │
│ Artikelcode: [_______________]             │
│                                            │
│ ...                                        │
│                                            │
│ [Abbrechen]             [Speichern]        │
└────────────────────────────────────────────┘
```

---

#### **📋 Templates für verschiedene Produkttypen**

**Template-System (für v2.0):**

```python
PRODUKT_TEMPLATES = {
    'dienstleistung_beratung': {
        'name': 'Dienstleistung (Beratung)',
        'beschreibung': 'Für Berater, Coaches, Freiberufler',
        'typ': 'dienstleistung',
        'felder': [
            'name',  # z.B. "Beratungsstunde"
            'beschreibung',
            'umsatzsteuer_satz',
            'verkaufspreis_netto',
            'einheit'  # 'Stunde', 'Tag', 'Projekt'
        ],
        'pflicht': ['name', 'umsatzsteuer_satz', 'verkaufspreis_netto'],
        'defaults': {
            'einheit': 'Stunde',
            'umsatzsteuer_satz': 19.0
        },
        'felder_ausblenden': [
            'einkaufspreis_netto',
            'lieferant_id',
            'hersteller',
            'ean_code',
            'lagerbestand',
            'mindestbestand'
        ]
    },

    'dienstleistung_handwerk': {
        'name': 'Dienstleistung (Handwerk)',
        'beschreibung': 'Für Handwerker (Arbeitsstunden)',
        'typ': 'dienstleistung',
        'felder': [
            'name',  # z.B. "Elektriker Arbeitsstunde"
            'beschreibung',
            'umsatzsteuer_satz',
            'verkaufspreis_netto',
            'einheit'
        ],
        'pflicht': ['name', 'umsatzsteuer_satz', 'verkaufspreis_netto'],
        'defaults': {
            'einheit': 'Stunde',
            'umsatzsteuer_satz': 19.0
        },
        'felder_ausblenden': [
            'einkaufspreis_netto',
            'lieferant_id',
            'hersteller',
            'ean_code',
            'lagerbestand',
            'mindestbestand'
        ]
    },

    'produkt_handelsware': {
        'name': 'Produkt (Handelsware)',
        'beschreibung': 'Für Händler (Einkauf & Verkauf)',
        'typ': 'produkt',
        'felder': [
            'name',
            'beschreibung',
            'hersteller',
            'ean_code',  # ⭐ WICHTIG!
            'artikelcode',
            'einheit',
            'umsatzsteuer_satz',
            'einkaufspreis_netto',  # PFLICHT
            'verkaufspreis_netto',  # PFLICHT
            'lieferant_id',
            'lagerbestand',
            'mindestbestand'
        ],
        'pflicht': ['name', 'umsatzsteuer_satz', 'einkaufspreis_netto', 'verkaufspreis_netto'],
        'defaults': {
            'einheit': 'Stück',
            'umsatzsteuer_satz': 19.0,
            'lagerbestand': 0.00,
            'mindestbestand': 5.00
        },
        'besonderheiten': [
            'EAN-Code empfohlen (für Barcode-Scanner)',
            'Lieferant zuordnen für Nachbestellung',
            'Mindestbestand für Warnung bei niedrigem Lagerstand'
        ]
    },

    'produkt_eigenproduktion': {
        'name': 'Produkt (Eigenproduktion)',
        'beschreibung': 'Für selbst hergestellte Produkte',
        'typ': 'produkt',
        'felder': [
            'name',
            'beschreibung',
            'artikelcode',
            'einheit',
            'umsatzsteuer_satz',
            'einkaufspreis_netto',  # Materialkosten
            'verkaufspreis_netto',
            'lagerbestand',
            'mindestbestand'
        ],
        'pflicht': ['name', 'umsatzsteuer_satz', 'einkaufspreis_netto', 'verkaufspreis_netto'],
        'defaults': {
            'einheit': 'Stück',
            'umsatzsteuer_satz': 19.0,
            'lagerbestand': 0.00
        },
        'felder_ausblenden': [
            'ean_code',  # Keine EAN für Eigenproduktion
            'lieferant_id'  # Kein Lieferant
        ],
        'besonderheiten': [
            'Einkaufspreis = Materialkosten',
            '⚠️ Kalkulations-Modul für v2.0 geplant! (Materialkosten + Arbeitszeit)'
        ]
    },

    'produkt_download': {
        'name': 'Digitales Produkt (Download)',
        'beschreibung': 'Für E-Books, Software, etc.',
        'typ': 'produkt',
        'felder': [
            'name',
            'beschreibung',
            'umsatzsteuer_satz',
            'verkaufspreis_netto'
        ],
        'pflicht': ['name', 'umsatzsteuer_satz', 'verkaufspreis_netto'],
        'defaults': {
            'einheit': 'Lizenz',
            'umsatzsteuer_satz': 19.0,
            'einkaufspreis_netto': 0.00  # Keine Materialkosten
        },
        'felder_ausblenden': [
            'ean_code',
            'lieferant_id',
            'hersteller',
            'lagerbestand',  # Kein Lager bei Downloads
            'mindestbestand'
        ]
    },

    'standard': {
        'name': 'Standard (Universal)',
        'beschreibung': 'Alle Felder verfügbar',
        'typ': None,  # User wählt
        'felder': 'alle',
        'pflicht': ['name', 'typ', 'umsatzsteuer_satz', 'verkaufspreis_netto'],
        'defaults': {
            'einheit': 'Stück',
            'umsatzsteuer_satz': 19.0
        }
    }
}
```

---

#### **💰 Kalkulations-Modul (für v2.0 vorgemerkt)**

**Zweck:**
- Automatische Berechnung von Verkaufspreisen
- Berücksichtigung von Materialkosten, Arbeitszeit, Gemeinkosten
- Gewinnmarge-Kalkulation

**Geplante Funktionen:**

```python
# ⚠️ FÜR v2.0 GEPLANT - NICHT IN v1.0!

def berechne_verkaufspreis(
    materialkosten: Decimal,  # Einkaufspreis
    arbeitszeit_stunden: Decimal,
    stundensatz: Decimal,
    gemeinkostenzuschlag: Decimal = Decimal('0.15'),  # 15%
    gewinnmarge: Decimal = Decimal('0.20')  # 20%
) -> Decimal:
    """
    Kalkuliert Verkaufspreis für selbst hergestellte Produkte

    Beispiel:
    - Materialkosten: 50,00 €
    - Arbeitszeit: 2 Stunden
    - Stundensatz: 40,00 €
    - Gemeinkosten: 15%
    - Gewinnmarge: 20%

    Rechnung:
    - Materialkosten: 50,00 €
    - Arbeitskosten: 2h × 40 €/h = 80,00 €
    - Herstellkosten: 130,00 €
    - + Gemeinkosten (15%): 19,50 €
    - Selbstkosten: 149,50 €
    - + Gewinnmarge (20%): 29,90 €
    - = Verkaufspreis (netto): 179,40 €
    """
    arbeitskosten = arbeitszeit_stunden * stundensatz
    herstellkosten = materialkosten + arbeitskosten
    gemeinkosten = herstellkosten * gemeinkostenzuschlag
    selbstkosten = herstellkosten + gemeinkosten
    gewinn = selbstkosten * gewinnmarge
    verkaufspreis = selbstkosten + gewinn

    return verkaufspreis.quantize(Decimal('0.01'))


# Datenbank-Schema-Erweiterung für v2.0:
"""
ALTER TABLE produkte ADD COLUMN kalkulation_aktiv BOOLEAN DEFAULT 0;
ALTER TABLE produkte ADD COLUMN kalkulation_arbeitszeit_stunden DECIMAL(10,2);
ALTER TABLE produkte ADD COLUMN kalkulation_stundensatz DECIMAL(10,2);
ALTER TABLE produkte ADD COLUMN kalkulation_gemeinkostenzuschlag DECIMAL(5,2) DEFAULT 15.0;
ALTER TABLE produkte ADD COLUMN kalkulation_gewinnmarge DECIMAL(5,2) DEFAULT 20.0;
"""
```

**UI - Kalkulations-Assistent (v2.0):**

```
┌───────────────────────────────────────────────┐
│ 🧮 Kalkulations-Assistent                    │
├───────────────────────────────────────────────┤
│                                               │
│ Produkt: Handgemachter Holztisch             │
│                                               │
│ 1️⃣ MATERIALKOSTEN:                           │
│    Holz, Schrauben, Lack: 50,00 €            │
│                                               │
│ 2️⃣ ARBEITSZEIT:                               │
│    Stunden: [__2,0__]                         │
│    Stundensatz: [_40,00_] €/h                │
│    → Arbeitskosten: 80,00 €                   │
│                                               │
│ 3️⃣ GEMEINKOSTEN:                              │
│    Zuschlag: [_15_] %                         │
│    → Gemeinkosten: 19,50 €                    │
│                                               │
│ 4️⃣ GEWINNMARGE:                               │
│    Marge: [_20_] %                            │
│    → Gewinn: 29,90 €                          │
│                                               │
│ ═══════════════════════════════════════       │
│ VERKAUFSPREIS (netto): 179,40 €               │
│ + USt 19%:              34,09 €               │
│ ─────────────────────────────────             │
│ VERKAUFSPREIS (brutto): 213,49 €              │
│ ═══════════════════════════════════════       │
│                                               │
│ [Abbrechen]    [Übernehmen]                   │
└───────────────────────────────────────────────┘
```

**Status:** 🔜 **Für v2.0 geplant**

---

#### **💻 Code-Implementierung**

```python
# models.py
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

@dataclass
class Produkt:
    id: Optional[int] = None

    # Stammdaten
    artikelnummer: Optional[str] = None
    name: str = ''  # PFLICHT
    beschreibung: Optional[str] = None
    typ: str = 'produkt'  # 'produkt' | 'dienstleistung'

    # USt-Satz (PFLICHT)
    umsatzsteuer_satz: Decimal = Decimal('19.0')

    # Verkaufspreis (PFLICHT)
    verkaufspreis_netto: Decimal = Decimal('0.00')

    # Einkaufspreis (PFLICHT bei Produkten)
    einkaufspreis_netto: Optional[Decimal] = None

    # Erweiterte Felder
    lieferant_id: Optional[int] = None
    hersteller: Optional[str] = None

    # EAN-Code
    ean_code: Optional[str] = None
    ean_typ: Optional[str] = None  # 'EAN-13', 'EAN-8', 'UPC', 'ISBN'

    artikelcode: Optional[str] = None
    einheit: str = 'Stück'

    # Lager
    lagerbestand: Decimal = Decimal('0.00')
    lagerbestand_negativ_erlaubt: bool = False
    mindestbestand: Decimal = Decimal('0.00')

    # Kategorie (optional)
    kategorie_id: Optional[int] = None

    # Metadaten
    ist_aktiv: bool = True
    erstellt_am: Optional[datetime] = None
    aktualisiert_am: Optional[datetime] = None

    @property
    def verkaufspreis_brutto(self) -> Decimal:
        """Berechnet Brutto-Verkaufspreis"""
        return (self.verkaufspreis_netto * (1 + self.umsatzsteuer_satz / 100)).quantize(Decimal('0.01'))

    @property
    def einkaufspreis_brutto(self) -> Optional[Decimal]:
        """Berechnet Brutto-Einkaufspreis"""
        if self.einkaufspreis_netto is None:
            return None
        return (self.einkaufspreis_netto * (1 + self.umsatzsteuer_satz / 100)).quantize(Decimal('0.01'))

    @property
    def gewinnmarge_prozent(self) -> Optional[Decimal]:
        """Berechnet Gewinnmarge in Prozent"""
        if self.einkaufspreis_netto is None or self.einkaufspreis_netto == 0:
            return None
        gewinn = self.verkaufspreis_netto - self.einkaufspreis_netto
        marge = (gewinn / self.einkaufspreis_netto) * 100
        return marge.quantize(Decimal('0.01'))

    @property
    def gewinn_pro_stueck(self) -> Optional[Decimal]:
        """Berechnet Gewinn pro Stück (netto)"""
        if self.einkaufspreis_netto is None:
            return None
        return (self.verkaufspreis_netto - self.einkaufspreis_netto).quantize(Decimal('0.01'))

    @property
    def lagerbestand_kritisch(self) -> bool:
        """Prüft, ob Lagerbestand unter Mindestbestand"""
        return self.lagerbestand < self.mindestbestand

    def validate(self) -> list[str]:
        """Validiert Pflichtfelder"""
        errors = []

        if not self.name:
            errors.append("Name ist Pflichtfeld")

        if not self.typ or self.typ not in ['produkt', 'dienstleistung']:
            errors.append("Typ muss 'produkt' oder 'dienstleistung' sein")

        if self.umsatzsteuer_satz is None:
            errors.append("USt-Satz ist Pflichtfeld")

        if self.verkaufspreis_netto is None or self.verkaufspreis_netto <= 0:
            errors.append("Verkaufspreis (netto) ist Pflichtfeld und muss > 0 sein")

        # Bei Produkten: Einkaufspreis PFLICHT
        if self.typ == 'produkt':
            if self.einkaufspreis_netto is None:
                errors.append("Einkaufspreis ist bei Produkten Pflichtfeld")

        # EAN-Validierung
        if self.ean_code:
            valid, detected_typ = validate_ean(self.ean_code, self.ean_typ)
            if not valid:
                errors.append(f"EAN-Code ungültig: {self.ean_code}")
            elif detected_typ != self.ean_typ and self.ean_typ:
                errors.append(f"EAN-Typ stimmt nicht überein: erwartet {self.ean_typ}, erkannt {detected_typ}")

        return errors


# services/produktstamm.py
from models import Produkt

def create_produkt_from_template(template_name: str, **kwargs) -> Produkt:
    """
    Erstellt Produkt aus Template

    Args:
        template_name: 'dienstleistung_beratung', 'produkt_handelsware', etc.
        **kwargs: Überschreibt Template-Defaults

    Returns:
        Produkt-Objekt mit Template-Defaults
    """
    template = PRODUKT_TEMPLATES.get(template_name, PRODUKT_TEMPLATES['standard'])

    produkt_data = {
        'typ': template.get('typ'),
        **template.get('defaults', {}),
        **kwargs
    }

    return Produkt(**produkt_data)
```

---

#### **🎨 UI-Mockups**

**Produktverwaltung (Übersicht):**

```
┌─────────────────────────────────────────────────────────────────────┐
│ Stammdaten → Produkte / Dienstleistungen                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ [ + Neues Produkt ] [ + Neue Dienstleistung ]    [🔍 Suchen: ___] │
│                                                                     │
│ Filter: [Alle ▼] [Aktiv ▼] [Typ ▼]                                │
│                                                                     │
│ Art.-Nr. │ Name                  │ Typ    │ Preis (netto) │ Lager │
│──────────┼───────────────────────┼────────┼───────────────┼───────│
│ DL-001   │ Beratungsstunde       │ DL     │    80,00 €    │   -   │
│ ART-001  │ Laptop Dell XPS 13    │ Prod   │ 1.000,00 €    │  15   │
│ ART-002  │ Schrauben M8 (100St.) │ Prod   │     5,00 €    │ ⚠️ 3  │
│ DL-002   │ Elektriker Arbeit     │ DL     │    50,00 €    │   -   │
│                                                                     │
│ Gesamt: 4 Artikel │ Lagerwert: 15.015,00 € │ ⚠️ 1 Artikel kritisch│
└─────────────────────────────────────────────────────────────────────┘
```

**Neues Produkt anlegen (Template-Auswahl):**

```
┌────────────────────────────────────────────┐
│ Neues Produkt / Dienstleistung anlegen     │
├────────────────────────────────────────────┤
│                                            │
│ Wähle eine Vorlage:                        │
│                                            │
│ ○ Dienstleistung (Beratung)                │
│   Für Berater, Coaches, Freiberufler      │
│                                            │
│ ○ Dienstleistung (Handwerk)                │
│   Für Handwerker (Arbeitsstunden)         │
│                                            │
│ ○ Produkt (Handelsware)                    │
│   Für Händler (Einkauf & Verkauf)         │
│                                            │
│ ○ Produkt (Eigenproduktion)                │
│   Für selbst hergestellte Produkte        │
│                                            │
│ ○ Digitales Produkt (Download)             │
│   Für E-Books, Software, etc.             │
│                                            │
│ ○ Standard (Universal)                     │
│   Alle Felder verfügbar                   │
│                                            │
│ [Abbrechen]                    [Weiter]    │
└────────────────────────────────────────────┘
```

**Produkt bearbeiten (Produkt Handelsware):**

```
┌──────────────────────────────────────────────────────────┐
│ Produkt bearbeiten: Laptop Dell XPS 13                   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ STAMMDATEN:                                              │
│                                                          │
│ Name *:        [Laptop Dell XPS 13___________________]  │
│ Artikelnummer: [ART-001] (automatisch)                  │
│ Hersteller:    [Dell_______________________________]    │
│ Beschreibung:  [13" Ultrabook, 16GB RAM, 512GB SSD]     │
│                [________________________________]         │
│                                                          │
│ EAN-CODE: ⭐                                             │
│ EAN-Code:      [4012345678901] ✅ EAN-13 gültig         │
│ Artikelcode:   [DELL-XPS13-2024__________________]      │
│                                                          │
│ PREISE:                                                  │
│                                                          │
│ USt-Satz *:    [19,0] %                                 │
│                                                          │
│ Einkaufspreis *:                                         │
│   Netto:       [1.000,00] €                             │
│   Brutto:      1.190,00 € (berechnet)                   │
│                                                          │
│ Verkaufspreis *:                                         │
│   Netto:       [1.200,00] €                             │
│   Brutto:      1.428,00 € (berechnet)                   │
│   Gewinnmarge: 20,00 % (200,00 € Gewinn/Stück)         │
│                                                          │
│ LAGER:                                                   │
│                                                          │
│ Einheit:       [Stück ▼]                                │
│ Lagerbestand:  [15,00] Stück                            │
│ Mindestbestand:[5,00] Stück (⚠️ Warnung bei <5)        │
│ ☐ Negativer Lagerbestand erlaubt                        │
│                                                          │
│ ZUORDNUNG:                                               │
│                                                          │
│ Lieferant:     [Tech-Großhandel GmbH ▼]                │
│ Kategorie:     [Computer & Elektronik ▼] (optional)    │
│                                                          │
│ ☑ Artikel ist aktiv                                     │
│                                                          │
│ [Löschen]   [Abbrechen]              [Speichern]        │
└──────────────────────────────────────────────────────────┘
```

**Dienstleistung bearbeiten (Beratung):**

```
┌──────────────────────────────────────────────────────────┐
│ Dienstleistung bearbeiten: Beratungsstunde               │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ STAMMDATEN:                                              │
│                                                          │
│ Name *:        [Beratungsstunde____________________]    │
│ Artikelnummer: [DL-001] (automatisch)                   │
│ Beschreibung:  [Strategieberatung für mittelständische] │
│                [Unternehmen_________________________]   │
│                                                          │
│ PREISE:                                                  │
│                                                          │
│ USt-Satz *:    [19,0] %                                 │
│                                                          │
│ Verkaufspreis *:                                         │
│   Netto:       [80,00] €                                │
│   Brutto:      95,20 € (berechnet)                      │
│                                                          │
│ Einheit:       [Stunde ▼]                               │
│                                                          │
│ ZUORDNUNG:                                               │
│                                                          │
│ Kategorie:     [Beratungsleistungen ▼] (optional)      │
│                                                          │
│ ☑ Dienstleistung ist aktiv                              │
│                                                          │
│ [Löschen]   [Abbrechen]              [Speichern]        │
└──────────────────────────────────────────────────────────┘
```

---

#### **💰 Anschaffungskosten & Anschaffungsnebenkosten** ⚖️ **WICHTIG**

**Problem:**
- Einkaufspreis (netto) vom Lieferanten: z.B. 1.000 €
- + Frachtkosten: 50 €
- + Versicherung: 10 €
- + Mautgebühren: 5 €
- + CO2-Abgabe: 15 €
- **= Was ist der "echte" Netto-EK?**

**Frage:** Gehören Nebenkosten zum Einkaufspreis? Wie steuerlich behandeln?

---

##### **Rechtsgrundlage: §255 HGB - Anschaffungskosten**

**§255 Abs. 1 HGB:**

```
Anschaffungskosten sind die Aufwendungen, die geleistet werden,
um einen Vermögensgegenstand zu erwerben und ihn in einen
betriebsbereiten Zustand zu versetzen, soweit sie dem
Vermögensgegenstand einzeln zugeordnet werden können.

Zu den Anschaffungskosten gehören auch die Nebenkosten sowie
die nachträglichen Anschaffungskosten.

Anschaffungskostenminderungen sind abzusetzen.
```

**Bedeutung:**
- Anschaffungskosten = **Einkaufspreis + Nebenkosten - Minderungen**
- NICHT nur der Preis auf der Lieferantenrechnung!

---

##### **Was gehört zu den Anschaffungskosten?**

**Formel:**

```
┌────────────────────────────────────────────────────────┐
│ ANSCHAFFUNGSKOSTEN (= "echter" Netto-EK)              │
├────────────────────────────────────────────────────────┤
│                                                        │
│ + Anschaffungspreis (netto vom Lieferanten)           │
│   Beispiel: 1.000,00 €                                │
│                                                        │
│ + ANSCHAFFUNGSNEBENKOSTEN:                            │
│   ├─ Frachtkosten / Transportkosten     + 50,00 €    │
│   ├─ Versicherung (während Transport)   + 10,00 €    │
│   ├─ Zölle, Einfuhrabgaben               +  0,00 €    │
│   ├─ Verpackung (nicht rückgabefähig)    +  5,00 €    │
│   ├─ Montagekosten                       +  0,00 €    │
│   ├─ CO2-Abgaben (beim Import)           + 15,00 €    │
│   ├─ Mautgebühren (zuordenbar)           +  5,00 €    │
│   └─ Lagerkosten (bis Inbetriebnahme)    +  0,00 €    │
│                                              ─────────  │
│                                       Summe:  85,00 €  │
│                                                        │
│ - ANSCHAFFUNGSPREISMINDERUNGEN:                       │
│   ├─ Rabatte / Preisnachlässe            -  0,00 €    │
│   ├─ Skonto (z.B. 2% bei Zahlung 10 Tg) - 20,00 €    │
│   └─ Boni / Rückvergütungen              -  0,00 €    │
│                                              ─────────  │
│                                       Summe: -20,00 €  │
│                                                        │
│ ═══════════════════════════════════════════════════    │
│ = ANSCHAFFUNGSKOSTEN (netto):        1.065,00 €       │
│ ═══════════════════════════════════════════════════    │
│                                                        │
│ + Umsatzsteuer (19%):                    202,35 €     │
│ ─────────────────────────────────────────────────      │
│ = ANSCHAFFUNGSKOSTEN (brutto):       1.267,35 €       │
└────────────────────────────────────────────────────────┘
```

---

##### **Welche Nebenkosten gehören DAZU?**

**✅ IMMER Anschaffungsnebenkosten:**

| Nebenkosten | Zuordnung | Beispiel |
|-------------|-----------|----------|
| **Frachtkosten** | ✅ JA | Transport vom Lieferanten zum Lager |
| **Transportversicherung** | ✅ JA | Versicherung während Transport |
| **Zölle, Einfuhrabgaben** | ✅ JA | Import aus Nicht-EU |
| **Verpackung (nicht rückgabefähig)** | ✅ JA | Einwegpaletten, Kisten |
| **Montagekosten** | ✅ JA | Zusammenbau vor Inbetriebnahme |
| **CO2-Abgaben** | ✅ JA | CO2-Steuer beim Import |
| **Prüfkosten** | ✅ JA | Qualitätsprüfung vor Nutzung |

**❌ KEINE Anschaffungsnebenkosten:**

| Nebenkosten | Zuordnung | Begründung |
|-------------|-----------|------------|
| **Lagerkosten (laufend)** | ❌ NEIN | Betriebsausgabe (nicht Anschaffung) |
| **Verwaltungskosten** | ❌ NEIN | Gemeinkosten (nicht zuordenbar) |
| **Finanzierungskosten** | ❌ NEIN | Keine Anschaffungskosten (§255 Abs. 3 HGB) |
| **Mautgebühren (allgemein)** | ⚠️ TEILS | Nur wenn dem Artikel zuordenbar |
| **Verpackung (rückgabefähig)** | ❌ NEIN | Wird zurückgegeben (z.B. Europaletten) |

---

##### **Unterschied: Anlagevermögen vs. Umlaufvermögen**

**Bei ANLAGEVERMÖGEN (Maschinen, Fahrzeuge, etc.):**

```
Beispiel: Maschine kaufen

Anschaffungspreis:       10.000,00 € (netto)
+ Frachtkosten:             500,00 €
+ Montagekosten:          1.000,00 €
─────────────────────────────────────
= Anschaffungskosten:    11.500,00 € (netto)

⚠️ PFLICHT: Nebenkosten MÜSSEN hinzugerechnet werden!

Abschreibung:
AfA linear (10 Jahre) = 11.500 € / 10 = 1.150 € pro Jahr
```

**Warum PFLICHT?**
- §255 HGB zwingt dazu
- Abschreibung erfolgt über **gesamte** Anschaffungskosten
- Finanzamt akzeptiert keine separate Verbuchung

---

**Bei UMLAUFVERMÖGEN (Waren, Material):**

```
Beispiel: Waren kaufen (für Wiederverkauf)

Einkaufspreis:            1.000,00 € (netto)
+ Frachtkosten:              50,00 €
─────────────────────────────────────
= Anschaffungskosten:     1.050,00 € (netto)

⚠️ SOLLTE hinzugerechnet werden (§255 HGB)
✅ ABER: Praktische Vereinfachung möglich!
```

**Praktische Vereinfachung (für Kleinunternehmer):**

```
Variante 1 (KORREKT nach §255 HGB):
- Ware: 1.050,00 € Einkaufspreis (inkl. Fracht)
- Lagerwert: 1.050,00 €
- Bei Verkauf: Wareneinsatz 1.050,00 €

Variante 2 (VEREINFACHT - toleriert vom Finanzamt):
- Ware: 1.000,00 € Einkaufspreis
- Fracht: 50,00 € Betriebsausgabe (separate Kategorie)
- Lagerwert: 1.000,00 €
- Bei Verkauf: Wareneinsatz 1.000,00 € + Fracht 50,00 €
```

**Wann Variante 2 erlaubt?**
- ✅ Bei geringem Warenwert
- ✅ Bei häufigen kleinen Bestellungen
- ✅ Wenn Zuordnung zu einzelnem Artikel schwierig
- ❌ NICHT bei großen Anschaffungen (z.B. Container-Import)

---

##### **Steuerliche Behandlung**

**Umsatzsteuer:**

```
Anschaffungspreis (netto):    1.000,00 €
+ Frachtkosten (netto):          50,00 €
─────────────────────────────────────────
= Anschaffungskosten (netto): 1.050,00 €
+ Umsatzsteuer 19%:             199,50 €
─────────────────────────────────────────
= Anschaffungskosten (brutto):1.249,50 €

Vorsteuerabzug: 199,50 € (wenn berechtigt)
```

**Wichtig:**
- Fracht, Spesen etc. unterliegen der Umsatzsteuer (meist 19%)
- Vorsteuerabzug möglich (wenn nicht Kleinunternehmer §19 UStG)

---

**Einkommensteuer / Körperschaftsteuer:**

**Anlagevermögen:**
- Anschaffungskosten werden über Nutzungsdauer abgeschrieben
- Abschreibung = Betriebsausgabe (steuermindernd)

**Umlaufvermögen:**
- Wareneinsatz = Betriebsausgabe (steuermindernd)
- Berechnung: Anfangsbestand + Einkäufe - Endbestand

---

##### **Implementierung in RechnungsFee**

**Erweiterung Datenbank-Schema (Produktstammdaten):**

```sql
ALTER TABLE produkte ADD COLUMN einkaufspreis_anschaffungskosten DECIMAL(10,2);
ALTER TABLE produkte ADD COLUMN einkaufspreis_nebenkosten DECIMAL(10,2) DEFAULT 0.00;
ALTER TABLE produkte ADD COLUMN einkaufspreis_minderungen DECIMAL(10,2) DEFAULT 0.00;

-- Berechnung der Anschaffungskosten
ALTER TABLE produkte ADD COLUMN einkaufspreis_gesamt DECIMAL(10,2) GENERATED ALWAYS AS (
    einkaufspreis_netto + einkaufspreis_nebenkosten - einkaufspreis_minderungen
) STORED;
```

**Detaillierte Nebenkosten-Erfassung:**

```sql
CREATE TABLE produkt_anschaffungsnebenkosten (
    id INTEGER PRIMARY KEY,
    produkt_id INTEGER NOT NULL,
    typ TEXT NOT NULL,  -- 'fracht', 'versicherung', 'zoll', 'montage', 'co2', 'maut', etc.
    bezeichnung TEXT,
    betrag_netto DECIMAL(10,2) NOT NULL,
    betrag_brutto DECIMAL(10,2),
    datum DATE,
    belegt_durch TEXT,  -- Verweis auf Rechnung/Beleg

    FOREIGN KEY (produkt_id) REFERENCES produkte(id),
    CHECK (typ IN ('fracht', 'versicherung', 'zoll', 'montage', 'co2', 'maut', 'verpackung', 'pruefung', 'sonstige'))
);
```

---

##### **UI-Konzept (erweitert)**

**Produkt bearbeiten - Erweiterte Ansicht:**

```
┌──────────────────────────────────────────────────────────┐
│ Produkt bearbeiten: Laptop Dell XPS 13                   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ PREISE:                                                  │
│                                                          │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ EINKAUFSPREIS (detailliert):                        │ │
│ ├─────────────────────────────────────────────────────┤ │
│ │                                                     │ │
│ │ Anschaffungspreis (netto): [1.000,00] €             │ │
│ │                                                     │ │
│ │ + ANSCHAFFUNGSNEBENKOSTEN:                          │ │
│ │   Frachtkosten:              [  50,00] €            │ │
│ │   Versicherung:              [  10,00] €            │ │
│ │   Zölle:                     [   0,00] €            │ │
│ │   CO2-Abgaben:               [  15,00] €            │ │
│ │   Sonstige:                  [   0,00] €            │ │
│ │                              ─────────               │ │
│ │   Summe Nebenkosten:            75,00 €             │ │
│ │                                                     │ │
│ │ - ANSCHAFFUNGSPREISMINDERUNGEN:                     │ │
│ │   Skonto (2%):               [  20,00] €            │ │
│ │   Rabatt:                    [   0,00] €            │ │
│ │                              ─────────               │ │
│ │   Summe Minderungen:           -20,00 €             │ │
│ │                                                     │ │
│ │ ═══════════════════════════════════════             │ │
│ │ ANSCHAFFUNGSKOSTEN (netto):  1.055,00 €             │ │
│ │ + USt 19%:                     200,45 €             │ │
│ │ ─────────────────────────────────────               │ │
│ │ ANSCHAFFUNGSKOSTEN (brutto): 1.255,45 €             │ │
│ │ ═══════════════════════════════════════             │ │
│ │                                                     │ │
│ │ ℹ️ Gemäß §255 HGB müssen Nebenkosten zu den        │ │
│ │    Anschaffungskosten gerechnet werden.            │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                          │
│ Verkaufspreis (netto):     [1.200,00] €                 │
│ Gewinnmarge:               145,00 € (13,74%)            │
│                                                          │
│ [Abbrechen]                             [Speichern]     │
└──────────────────────────────────────────────────────────┘
```

---

##### **Workflow-Beispiel: Warenimport**

```
SZENARIO: Import von 100 Laptops aus China

1. EINKAUF:
   ┌─────────────────────────────────────────┐
   │ Lieferantenrechnung:                    │
   │ - 100 Laptops × 1.000 € = 100.000 €    │
   │ - Fracht (Container):       2.000 €    │
   │ - Versicherung:               500 €    │
   │ - Zoll (EU-Import):         3.000 €    │
   │ - CO2-Abgabe:                 500 €    │
   │                           ─────────    │
   │ Summe (netto):           106.000 €    │
   │ + USt 19%:                20.140 €    │
   │                           ─────────    │
   │ Summe (brutto):          126.140 €    │
   └─────────────────────────────────────────┘

2. BUCHUNG (§255 HGB - KORREKT):
   ┌─────────────────────────────────────────┐
   │ Ware (100 Laptops):                     │
   │ - Anschaffungskosten: 106.000 € (netto)│
   │ - Pro Laptop: 1.060 € (netto)          │
   │                                         │
   │ Lagerwert: 106.000 €                   │
   │                                         │
   │ Bei Verkauf (1 Laptop):                │
   │ - Wareneinsatz: 1.060 € (nicht 1.000 €)│
   └─────────────────────────────────────────┘

3. VEREINFACHT (toleriert bei Kleinunternehmer):
   ┌─────────────────────────────────────────┐
   │ Ware (100 Laptops): 100.000 € (netto)  │
   │ Fracht: 2.000 € (Betriebsausgabe)      │
   │ Versicherung: 500 € (Betriebsausgabe)  │
   │ Zoll: 3.000 € (Betriebsausgabe)        │
   │ CO2: 500 € (Betriebsausgabe)           │
   │                                         │
   │ Lagerwert: 100.000 €                   │
   │                                         │
   │ Bei Verkauf (1 Laptop):                │
   │ - Wareneinsatz: 1.000 €                │
   │ - Nebenkosten: 60 € (anteilig)         │
   └─────────────────────────────────────────┘
```

---

##### **Best Practices für RechnungsFee**

**Empfehlung:**

1. **Anlagevermögen (Maschinen, Fahrzeuge):**
   - ✅ **IMMER** Nebenkosten zu Anschaffungskosten rechnen
   - ✅ §255 HGB zwingend
   - ✅ Abschreibung über Gesamtkosten

2. **Umlaufvermögen (Waren):**
   - ✅ **Standard**: Nebenkosten zu Anschaffungskosten (§255 HGB)
   - ⚠️ **Vereinfachung**: Separate Verbuchung (bei kleinen Beträgen toleriert)
   - 💡 **RechnungsFee**: Beide Methoden unterstützen, User wählt

3. **Einstellung in RechnungsFee:**
   ```
   ┌──────────────────────────────────────────────┐
   │ ⚙️ Einstellungen > Warenwirtschaft          │
   ├──────────────────────────────────────────────┤
   │                                              │
   │ Anschaffungsnebenkosten behandeln als:      │
   │                                              │
   │ ● Teil der Anschaffungskosten (§255 HGB)    │
   │   Empfohlen, korrekt nach Handelsrecht      │
   │                                              │
   │ ○ Separate Betriebsausgaben                 │
   │   Vereinfachung (nur bei kleinen Beträgen)  │
   └──────────────────────────────────────────────┘
   ```

---

##### **Zusammenfassung: Anschaffungskosten**

**Problem:**
Einkaufspreis ≠ Anschaffungskosten

**Lösung:**
```
Anschaffungskosten = Einkaufspreis + Nebenkosten - Minderungen
```

**Nebenkosten (gehören DAZU):**
- ✅ Fracht, Versicherung, Zölle, CO2, Montage, Verpackung (nicht rückgabefähig)

**Nebenkosten (gehören NICHT dazu):**
- ❌ Lagerkosten (laufend), Verwaltung, Finanzierung

**Steuerlich:**
- **Anlagevermögen**: Nebenkosten PFLICHT hinzurechnen (§255 HGB)
- **Umlaufvermögen**: Sollte hinzugerechnet werden, Vereinfachung toleriert

**RechnungsFee:**
- Datenbank-Erweiterung für detaillierte Nebenkosten
- UI für Erfassung
- Einstellung: §255 HGB vs. Vereinfachung

**Status:** 📋 **Für v2.0 vorgemerkt** (komplexe Warenwirtschaft)

---

#### **📝 Zusammenfassung: Produktstammdaten**

**Entscheidung:**
- ✅ **Hybrid-Lösung** (wie Kundenstamm)
  - Automatisch / Auf Nachfrage (Standard) / Nie
- ✅ **Templates** für verschiedene Produkttypen
  - Dienstleistung (Beratung, Handwerk)
  - Produkt (Handelsware, Eigenproduktion, Digital)
  - Standard (Universal)

**Felder:**

**Für ALLE Typen:**
- Name * (Pflicht)
- USt-Satz * (Pflicht)
- Verkaufspreis * (Netto, Brutto berechnet) (Pflicht)
- Beschreibung
- Kategorie (optional, später)

**Zusätzlich für PRODUKTE:**
- Einkaufspreis * (Netto, Brutto berechnet) (Pflicht)
- Lieferant
- Hersteller
- **EAN-Code** ⭐ (mit Validierung!)
- Artikelcode
- Einheit
- Lagerbestand
- Negativer Lagerbestand (erlaubt/nicht erlaubt)
- Mindestbestand

**Besondere Features:**
- ⭐ **EAN-Code Support** mit Validierung (EAN-13, EAN-8, UPC, ISBN)
- 📊 **Gewinnmarge-Berechnung** (Verkaufspreis - Einkaufspreis)
- ⚠️ **Lagerbestand-Warnung** (bei Unterschreitung Mindestbestand)
- 🧮 **Kalkulations-Modul** (für v2.0 vorgemerkt)
- 💰 **Anschaffungskosten** (§255 HGB) (für v2.0 vorgemerkt)

**Status:** 📋 **Für v2.0 geplant** (NICHT in MVP v1.0)

**Begründung:**
- MVP v1.0: Nur Rechnungen VERWALTEN (nicht erstellen)
- Rechnungsschreiben über LibreOffice/HTML-Vorlagen
- Produktstamm wird erst relevant, wenn internes Rechnungsschreib-Tool kommt

---

### **8.10 Kundenstamm ✅ GEKLÄRT**

**Status:** ✅ **Entscheidung getroffen**

**Entscheidung:** **Hybrid-Lösung (Option C)** mit konfigurierbarem Standard-Verhalten

---

#### **🎯 Implementierung: Hybrid mit Einstellungen**

**User kann in Grundeinstellungen wählen:**

```
┌─────────────────────────────────────────────────┐
│ ⚙️ Einstellungen > Kundenstamm                 │
├─────────────────────────────────────────────────┤
│                                                 │
│ Beim Erstellen von Rechnungen:                 │
│                                                 │
│ ○ Kunden automatisch speichern                 │
│   (Alle neuen Kunden werden ohne Nachfrage     │
│    im Kundenstamm gespeichert)                 │
│                                                 │
│ ● Auf Nachfrage speichern (Standard) ⭐        │
│   (Du wirst gefragt, ob der Kunde gespeichert │
│    werden soll)                                │
│                                                 │
│ ○ Kunden nicht speichern                       │
│   (Kundendaten werden nur in der Rechnung      │
│    erfasst, kein Kundenstamm)                  │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Datenbank-Einstellung:**
```sql
-- In der `user` Tabelle:
ALTER TABLE user ADD COLUMN kundenstamm_modus TEXT DEFAULT 'nachfrage';
-- Werte: 'automatisch', 'nachfrage', 'nie'
```

---

#### **📊 Datenbank-Schema**

```sql
CREATE TABLE kunden (
    id INTEGER PRIMARY KEY,

    -- Stammdaten
    kundennummer TEXT UNIQUE,  -- "K-001" (automatisch generiert)
    typ TEXT,  -- 'privat', 'firma'

    -- Person
    anrede TEXT,  -- 'Herr', 'Frau', 'Divers', NULL
    vorname TEXT,
    nachname TEXT,

    -- Firma (nur wenn typ='firma')
    firmenname TEXT,
    rechtsform TEXT,  -- "GmbH", "AG", "e.K.", etc.
    ansprechpartner TEXT,  -- ⭐ NEU: Kontaktperson bei Firmen

    -- Adresse (Pflichtfelder)
    strasse TEXT NOT NULL,
    hausnummer TEXT,
    plz TEXT NOT NULL,
    ort TEXT NOT NULL,
    land TEXT DEFAULT 'DE' NOT NULL,

    -- Automatisch abgeleitete Kategorisierung
    land_kategorie TEXT GENERATED ALWAYS AS (
        CASE
            WHEN land = 'DE' THEN 'inland'
            WHEN land IN ('AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','GR','HU','IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK','SI','ES','SE') THEN 'eu'
            ELSE 'drittland'
        END
    ) STORED,  -- ⭐ NEU: Automatische Kategorisierung

    -- Kontakt (Optional)
    email TEXT,
    telefon_mobil TEXT,  -- ⭐ NEU: Mobiltelefon (getrennt)
    telefon_festnetz TEXT,  -- ⭐ NEU: Festnetz (getrennt)
    website TEXT,

    -- Persönliche Daten (nur bei typ='privat')
    geburtstag DATE,  -- ⭐ NEU: Für Privatpersonen

    -- Geschäftsbedingungen
    zahlungsziel INTEGER DEFAULT 14,  -- Tage (Standard 14)
    zahlungsziel_individuell BOOLEAN DEFAULT 0,  -- Abweichend vom User-Standard?

    -- Steuerliche Daten
    steuernummer TEXT,  -- ⭐ NEU: Steuernummer (bei Firma validiert)
    steuer_id TEXT,  -- ⭐ NEU: Steueridentifikationsnummer (11-stellig)
    steuer_id_validiert BOOLEAN DEFAULT 0,  -- ⭐ NEU

    -- EU-Handel
    ust_idnr TEXT,  -- z.B. "BE0123456789"
    ust_idnr_validiert BOOLEAN DEFAULT 0,
    ust_idnr_validierung_datum DATE,
    ust_idnr_validierung_ergebnis TEXT,  -- BZSt-API Ergebnis (JSON)

    -- Metadaten
    notizen TEXT,  -- Anmerkungen / Bemerkungen
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    aktualisiert_am TIMESTAMP,

    -- Statistiken (automatisch aktualisiert)
    anzahl_rechnungen INTEGER DEFAULT 0,
    umsatz_gesamt DECIMAL(10,2) DEFAULT 0.00,
    letzte_rechnung_datum DATE
);

-- Index für schnelle Suche
CREATE INDEX idx_kunden_nummer ON kunden(kundennummer);
CREATE INDEX idx_kunden_name ON kunden(nachname, vorname, firmenname);
CREATE INDEX idx_kunden_land_kategorie ON kunden(land_kategorie);
```

---

#### **🖥️ UI: Rechnung erstellen (Modus "nachfrage")**

```
┌──────────────────────────────────────────────────┐
│ 📄 Neue Rechnung erstellen                       │
├──────────────────────────────────────────────────┤
│                                                  │
│ Kunde:                                           │
│ ┌──────────────────────────────────────────────┐ │
│ │ 🔍 Kunde suchen oder neu eingeben...        │ │
│ │ [Bel________________________]               │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ ✓ Belgischer Kunde GmbH (K-042)  ← Aus Stamm   │
│ ✓ Beratung Belgien GmbH (K-015)                │
│ ─────────────────────────────────               │
│ ➕ Neuen Kunden eingeben                        │
│                                                  │
└──────────────────────────────────────────────────┘

[User wählt "Neuen Kunden eingeben"]

┌──────────────────────────────────────────────────┐
│ ➕ Neuer Kunde                                   │
├──────────────────────────────────────────────────┤
│                                                  │
│ Typ:  ● Firma  ○ Privatperson                   │
│                                                  │
│ Firmenname: *                                    │
│ [Neue Firma GmbH_________________]               │
│                                                  │
│ Ansprechpartner:                                 │
│ [Max Mustermann__________________]               │
│                                                  │
│ Straße: *          Hausnr.:                      │
│ [Musterstraße___]  [123__]                       │
│                                                  │
│ PLZ: *      Ort: *                               │
│ [12345___]  [Musterstadt__________]              │
│                                                  │
│ Land: *                      (→ Kategorie: EU)   │
│ [Belgien ▼]                                      │
│                                                  │
│ E-Mail:                                          │
│ [info@neue-firma.be______________]               │
│                                                  │
│ Telefon (Mobil): ⭐ NEU                          │
│ [📱 +49 170 1234567_____]  [📞 Anrufen]         │
│                                                  │
│ Telefon (Festnetz): ⭐ NEU                       │
│ [📞 +49 441 12345___]  [📞 Anrufen]              │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ Steuerliche Daten                          │  │
│ ├────────────────────────────────────────────┤  │
│ │                                            │  │
│ │ Steuernummer (bei Firma): ⭐ NEU          │  │
│ │ [26/123/12345___________]                  │  │
│ │ ⚠️ Empfohlen bei Firmen                   │  │
│ │                                            │  │
│ │ Steuer-ID: ⭐ NEU                          │  │
│ │ [12345678901_____]  [Validieren ✓]        │  │
│ │ ℹ️ 11-stellig (für DE-Kunden)             │  │
│ │                                            │  │
│ │ USt-IdNr. (für EU-Kunden):                 │  │
│ │ [BE0123456789____]  [Validieren ✓]        │  │
│ │ ✅ Gültig (geprüft am 08.12.2025)          │  │
│ │                                            │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ Zahlungsziel:                                    │
│ [14__] Tage  ☑ Abweichend vom Standard (14 T.)  │
│                                                  │
│ Anmerkungen: ⭐ NEU                              │
│ [____________________________________________]   │
│ [____________________________________________]   │
│                                                  │
├──────────────────────────────────────────────────┤
│                                                  │
│ ⚠️ Soll dieser Kunde im Kundenstamm gespeichert │
│    werden?                                       │
│                                                  │
│ ✅ Vorteile:                                     │
│ • Nächste Rechnung: Kunde einfach auswählen     │
│ • USt-IdNr. bereits validiert                   │
│ • Statistiken & Umsatzübersicht möglich         │
│                                                  │
│ [Ja, speichern]  [Nein, nur für diese Rechnung] │
│                                                  │
│ ☑ Immer speichern (Einstellung ändern)          │
│ ☐ Nie mehr fragen (Einstellung ändern)          │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

#### **🖥️ UI: Rechnung erstellen (Modus "automatisch")**

```
[Gleiche Maske wie oben, ABER:]

├──────────────────────────────────────────────────┤
│                                                  │
│ ℹ️ Dieser Kunde wird automatisch im Kundenstamm │
│    gespeichert (Kundennummer: K-089).           │
│                                                  │
│    Einstellung ändern: ⚙️ Einstellungen > Kundenstamm
│                                                  │
└──────────────────────────────────────────────────┘
```

---

#### **🖥️ UI: Rechnung erstellen (Modus "nie")**

```
[Keine Nachfrage, kein Hinweis - Kunde wird NICHT gespeichert]

[Aber: Kundenstamm-Suche trotzdem verfügbar falls manuell angelegt]
```

---

#### **🖥️ UI: Privatperson (mit Geburtstag)** ⭐ NEU

```
┌──────────────────────────────────────────────────┐
│ ➕ Neuer Kunde                                   │
├──────────────────────────────────────────────────┤
│                                                  │
│ Typ:  ○ Firma  ● Privatperson ⭐                │
│                                                  │
│ Anrede:                                          │
│ [Frau ▼]                                         │
│                                                  │
│ Vorname:         Nachname: *                     │
│ [Erika____]      [Musterfrau__________]          │
│                                                  │
│ Geburtstag: ⭐ NEU                               │
│ [01.01.1980__]  📅                               │
│ ℹ️ Optional (z.B. für Glückwünsche)             │
│                                                  │
│ Straße: *          Hausnr.:                      │
│ [Musterstraße___]  [42__]                        │
│                                                  │
│ PLZ: *      Ort: *                               │
│ [26123__]   [Oldenburg____________]              │
│                                                  │
│ Land: *                      (→ Kategorie: Inland)
│ [Deutschland ▼]                                  │
│                                                  │
│ E-Mail:                                          │
│ [erika@beispiel.de_______________]               │
│                                                  │
│ Telefon (Mobil): ⭐                              │
│ [📱 +49 170 9876543_____]  [📞 Anrufen]         │
│                                                  │
│ Telefon (Festnetz): ⭐                           │
│ [📞 0441 987654_____]  [📞 Anrufen]              │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ Steuerliche Daten (optional)               │  │
│ ├────────────────────────────────────────────┤  │
│ │                                            │  │
│ │ Steuer-ID: ⭐                              │  │
│ │ [12345678901_____]                         │  │
│ │ ℹ️ 11-stellig (nur bei Bedarf)            │  │
│ │                                            │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ Zahlungsziel:                                    │
│ [14__] Tage                                      │
│                                                  │
│ Anmerkungen: ⭐                                  │
│ [Stammkundin seit 2020, bevorzugt E-Mail____]   │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

#### **📞 Click-to-Call Funktion** ⭐ NEU

**Linkfeld bei Telefonnummern:**

```python
# ui/kunde_detail.py
def render_telefon_feld(telefon: str, typ: str) -> str:
    """
    Rendert Telefon-Feld mit Click-to-Call Link

    Args:
        telefon: Telefonnummer (z.B. "+49 170 1234567")
        typ: 'mobil' oder 'festnetz'

    Returns:
        HTML mit klickbarem Link für Smartphones
    """
    if not telefon:
        return ""

    icon = "📱" if typ == "mobil" else "📞"

    # Link für Smartphones/Click-to-Call
    # Format: tel:+491701234567 (ohne Leerzeichen)
    tel_link = telefon.replace(' ', '').replace('-', '')

    html = f"""
    <div class="telefon-feld">
        <span class="icon">{icon}</span>
        <a href="tel:{tel_link}" class="telefon-link">
            {telefon}
        </a>
        <button class="btn-call" onclick="call('{tel_link}')">
            📞 Anrufen
        </button>
    </div>
    """

    return html


# JavaScript für Desktop (optional: Integration mit Softphone)
def get_telefon_javascript():
    return """
    <script>
    function call(nummer) {
        // Option 1: Browser-Native (Smartphones)
        window.location.href = 'tel:' + nummer;

        // Option 2: Integration mit Softphone (z.B. 3CX, Asterisk)
        // fetch('/api/softphone/call', {
        //     method: 'POST',
        //     body: JSON.stringify({nummer: nummer})
        // });
    }
    </script>
    """
```

**Verhalten:**
- **Smartphone/Tablet**: Öffnet native Telefon-App
- **Desktop**:
  - Link öffnet Standard-Telefonie-App (Skype, Teams, etc.)
  - Optional: Integration mit Softphone (3CX, Asterisk, sipgate)
- **Button "Anrufen"**: Gleiche Funktion wie Link, aber prominenter

---

#### **📋 Templates für Kundenstamm** ⭐ NEU (für später)

**Konzept:**
Branchenspezifische Vorlagen für Kundenstamm-Felder

**Branchen-Templates:**

```python
# templates/kunden_templates.py
KUNDEN_TEMPLATES = {
    'standard': {
        'name': 'Standard (Universal)',
        'felder': [
            'kundennummer', 'typ', 'firmenname', 'vorname', 'nachname',
            'strasse', 'plz', 'ort', 'land',
            'email', 'telefon_mobil', 'telefon_festnetz',
            'steuernummer', 'steuer_id', 'ust_idnr',
            'zahlungsziel', 'notizen'
        ],
        'pflicht': ['nachname|firmenname', 'strasse', 'plz', 'ort', 'land']
    },

    'handwerk': {
        'name': 'Handwerk (Privatkunden)',
        'beschreibung': 'Für Handwerker mit vielen Privatkunden',
        'felder': [
            'kundennummer', 'typ',
            'anrede', 'vorname', 'nachname',  # Privat im Fokus
            'strasse', 'hausnummer', 'plz', 'ort',  # Hausnummer wichtig!
            'email', 'telefon_mobil', 'telefon_festnetz',  # Beide Nummern
            'geburtstag',  # Für Glückwünsche
            'zahlungsziel',
            'notizen'  # "Wünscht Anruf vorab", "Hat Hund"
        ],
        'pflicht': ['nachname', 'strasse', 'hausnummer', 'plz', 'ort', 'telefon_mobil'],
        'besonderheiten': [
            'Hausnummer Pflichtfeld (für Anfahrt)',
            'Mindestens eine Telefonnummer Pflicht',
            'Geburtstag optional (für Kundenbindung)'
        ]
    },

    'b2b_eu': {
        'name': 'B2B EU-Handel',
        'beschreibung': 'Für Unternehmen mit vielen EU-Geschäftskunden',
        'felder': [
            'kundennummer', 'typ',
            'firmenname', 'rechtsform', 'ansprechpartner',  # Firma im Fokus
            'strasse', 'plz', 'ort', 'land',
            'email', 'telefon_mobil', 'telefon_festnetz',
            'steuernummer', 'ust_idnr',  # USt-IdNr. kritisch!
            'zahlungsziel',
            'notizen'
        ],
        'pflicht': ['firmenname', 'strasse', 'plz', 'ort', 'land', 'ust_idnr'],
        'validierung_scharf': [
            'ust_idnr',  # MUSS validiert werden
            'land'  # MUSS EU-Land sein
        ],
        'besonderheiten': [
            'USt-IdNr. Pflichtfeld (für ig. Lieferung)',
            'Automatische BZSt-Validierung beim Speichern',
            'Warnung bei fehlendem Ansprechpartner'
        ]
    },

    'freiberufler_beratung': {
        'name': 'Freiberufler/Beratung',
        'beschreibung': 'Für Berater, Coaches, Dienstleister',
        'felder': [
            'kundennummer', 'typ',
            'anrede', 'vorname', 'nachname',  # Oft persönliche Beziehung
            'firmenname', 'ansprechpartner',  # Aber auch Firmen
            'strasse', 'plz', 'ort', 'land',
            'email', 'telefon_mobil', 'website',  # Website wichtig
            'zahlungsziel',
            'notizen'  # "Interessiert an Coaching", "Kontakt über LinkedIn"
        ],
        'pflicht': ['nachname|firmenname', 'email'],
        'besonderheiten': [
            'E-Mail Pflichtfeld (Haupt-Kommunikationskanal)',
            'Website optional (für Recherche)',
            'Telefon optional (E-Mail-Kommunikation dominiert)'
        ]
    },

    'einzelhandel': {
        'name': 'Einzelhandel (Laufkundschaft)',
        'beschreibung': 'Für Shops mit vielen Einmalkunden',
        'felder': [
            'kundennummer', 'typ',
            'vorname', 'nachname',
            'email', 'telefon_mobil',
            'geburtstag',  # Für Geburtstags-Rabatte
            'notizen'
        ],
        'pflicht': ['nachname', 'email|telefon_mobil'],  # Minimal!
        'besonderheiten': [
            'Minimales Schema (viele Einmalkunden)',
            'E-Mail ODER Telefon reicht',
            'Adresse optional (Abholung im Shop)',
            'Geburtstag für Marketing'
        ]
    },

    'vermietung': {
        'name': 'Vermietung/Verleih',
        'beschreibung': 'Für Vermieter, Verleiher',
        'felder': [
            'kundennummer', 'typ',
            'anrede', 'vorname', 'nachname',
            'geburtstag',  # Für Altersverifikation
            'strasse', 'hausnummer', 'plz', 'ort',
            'email', 'telefon_mobil', 'telefon_festnetz',
            'steuer_id',  # Für Schufa/Bonität
            'notizen'  # "Kaution hinterlegt", "Vertrag bis 31.12."
        ],
        'pflicht': ['nachname', 'geburtstag', 'strasse', 'plz', 'ort', 'telefon_mobil'],
        'besonderheiten': [
            'Geburtstag Pflicht (Altersverifikation)',
            'Vollständige Adresse Pflicht',
            'Beide Telefonnummern empfohlen (Erreichbarkeit)'
        ]
    }
}


def get_template(branche: str) -> dict:
    """
    Gibt Template für Branche zurück

    Args:
        branche: 'standard', 'handwerk', 'b2b_eu', etc.

    Returns:
        Template-Dict mit Feldern, Pflichtfeldern, Besonderheiten
    """
    return KUNDEN_TEMPLATES.get(branche, KUNDEN_TEMPLATES['standard'])


def apply_template(branche: str):
    """
    Wendet Template an: Passt UI-Formular und Validierung an
    """
    template = get_template(branche)

    # UI nur relevante Felder anzeigen
    # Validierung auf template['pflicht'] anpassen
    # Besonderheiten als Tooltips/Hinweise anzeigen

    pass  # Implementierung später
```

**UI - Template-Auswahl im Setup-Wizard:**

```
┌──────────────────────────────────────────────────┐
│ Setup-Wizard - Schritt 1: Branche               │
├──────────────────────────────────────────────────┤
│                                                  │
│ Welche Branche passt am besten zu dir?          │
│                                                  │
│ ○ Standard (Universal)                           │
│   Für alle Branchen geeignet                     │
│                                                  │
│ ○ Handwerk (Privatkunden)                        │
│   Viele Privatkunden, Anfahrt wichtig            │
│                                                  │
│ ○ B2B EU-Handel                                  │
│   Geschäftskunden, USt-IdNr. wichtig             │
│                                                  │
│ ○ Freiberufler/Beratung                          │
│   Dienstleister, E-Mail-Kommunikation            │
│                                                  │
│ ○ Einzelhandel (Laufkundschaft)                  │
│   Viele Einmalkunden, minimale Daten             │
│                                                  │
│ ○ Vermietung/Verleih                             │
│   Verträge, Altersverifikation wichtig           │
│                                                  │
│ ℹ️ Du kannst die Felder später anpassen!        │
│                                                  │
│ [Zurück]                         [Weiter]        │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Vorteile:**
- ✅ **Fokussiert**: Nur relevante Felder für Branche
- ✅ **Geführt**: Pflichtfelder an Branche angepasst
- ✅ **Lernkurve**: Weniger Verwirrung (weniger Felder)
- ✅ **Flexibel**: Kann später auf "Standard" umstellen

**Status:** 🔜 **Für v2.0 geplant** (v1.0 nutzt "Standard"-Template)

---

#### **💻 Code-Implementierung**

```python
# models.py
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

@dataclass
class Kunde:
    id: Optional[int] = None

    # Stammdaten
    kundennummer: Optional[str] = None  # "K-001" (auto)
    typ: str = 'privat'  # 'privat' | 'firma'

    # Person
    anrede: Optional[str] = None
    vorname: Optional[str] = None
    nachname: Optional[str] = None

    # Firma
    firmenname: Optional[str] = None
    rechtsform: Optional[str] = None
    ansprechpartner: Optional[str] = None  # ⭐ NEU

    # Adresse (Pflicht)
    strasse: str = ''
    hausnummer: Optional[str] = None
    plz: str = ''
    ort: str = ''
    land: str = 'DE'

    # Kontakt
    email: Optional[str] = None
    telefon_mobil: Optional[str] = None  # ⭐ NEU
    telefon_festnetz: Optional[str] = None  # ⭐ NEU
    website: Optional[str] = None

    # Persönliche Daten
    geburtstag: Optional[date] = None  # ⭐ NEU (nur bei typ='privat')

    # Geschäftsbedingungen
    zahlungsziel: int = 14  # Tage
    zahlungsziel_individuell: bool = False

    # Steuerliche Daten
    steuernummer: Optional[str] = None  # ⭐ NEU (bei Firma)
    steuer_id: Optional[str] = None  # ⭐ NEU (11-stellig)
    steuer_id_validiert: bool = False  # ⭐ NEU

    # EU-Handel
    ust_idnr: Optional[str] = None
    ust_idnr_validiert: bool = False
    ust_idnr_validierung_datum: Optional[date] = None
    ust_idnr_validierung_ergebnis: Optional[str] = None

    # Metadaten
    notizen: Optional[str] = None
    erstellt_am: Optional[datetime] = None
    aktualisiert_am: Optional[datetime] = None

    # Statistiken
    anzahl_rechnungen: int = 0
    umsatz_gesamt: Decimal = Decimal('0.00')
    letzte_rechnung_datum: Optional[date] = None

    @property
    def land_kategorie(self) -> str:
        """
        Automatische Kategorisierung: inland / eu / drittland
        """
        if self.land == 'DE':
            return 'inland'
        elif self.land in EU_LAENDER:  # Liste aus Sektion 8.6
            return 'eu'
        else:
            return 'drittland'

    @property
    def display_name(self) -> str:
        """
        Anzeigename für UI
        """
        if self.typ == 'firma' and self.firmenname:
            return self.firmenname
        elif self.vorname and self.nachname:
            return f"{self.vorname} {self.nachname}"
        elif self.nachname:
            return self.nachname
        else:
            return "Unbenannter Kunde"

    def validate(self) -> list[str]:
        """
        Validiert Pflichtfelder
        """
        errors = []

        if self.typ == 'privat':
            if not self.nachname:
                errors.append("Nachname ist Pflichtfeld")
        elif self.typ == 'firma':
            if not self.firmenname:
                errors.append("Firmenname ist Pflichtfeld")

        if not self.strasse:
            errors.append("Straße ist Pflichtfeld")
        if not self.plz:
            errors.append("PLZ ist Pflichtfeld")
        if not self.ort:
            errors.append("Ort ist Pflichtfeld")
        if not self.land:
            errors.append("Land ist Pflichtfeld")

        # Steuerliche Validierungen ⭐ NEU
        if self.typ == 'firma' and self.firmenname:
            # Bei Firma: Steuernummer empfohlen
            if not self.steuernummer:
                errors.append("Warnung: Steuernummer bei Firma empfohlen")

        # Steuer-ID Validierung (wenn gefüllt)
        if self.steuer_id:
            if self.land == 'DE':
                # Deutsche Steuer-ID: 11-stellig
                if not self._validate_steuer_id_de(self.steuer_id):
                    errors.append("Steuer-ID ungültig (muss 11-stellig sein)")
            else:
                # Andere Länder: Steuer-ID sollte validiert werden
                if not self.steuer_id_validiert:
                    errors.append("Warnung: Steuer-ID sollte validiert werden")

        # USt-IdNr. bei EU-Kunden empfohlen
        if self.land_kategorie == 'eu' and not self.ust_idnr:
            errors.append("Warnung: USt-IdNr. bei EU-Kunden empfohlen (für ig. Lieferung)")

        return errors

    def _validate_steuer_id_de(self, steuer_id: str) -> bool:
        """
        Validiert deutsche Steuer-ID (11-stellig)

        Format: XXXXXXXXXXX (11 Ziffern)
        - Ziffer 1-10: Beliebig (aber Prüfziffer-Logik)
        - Ziffer 11: Prüfziffer
        """
        import re

        # Leerzeichen entfernen
        steuer_id_clean = steuer_id.replace(' ', '')

        # Muss 11 Ziffern sein
        if not re.match(r'^\d{11}$', steuer_id_clean):
            return False

        # Erweiterte Validierung (Prüfziffer) hier möglich
        # Für MVP: Nur Längen-Check
        return True


# kunde_service.py
class KundenService:
    def __init__(self, db, user_settings):
        self.db = db
        self.user_settings = user_settings

    def sollte_kunde_speichern(self, kunde: Kunde, user_entscheidung: Optional[bool] = None) -> bool:
        """
        Bestimmt ob Kunde gespeichert werden soll basierend auf Einstellung

        Args:
            kunde: Kundendaten
            user_entscheidung: Explizite User-Entscheidung (überschreibt Einstellung)

        Returns:
            True wenn Kunde gespeichert werden soll
        """
        if user_entscheidung is not None:
            return user_entscheidung

        modus = self.user_settings.kundenstamm_modus

        if modus == 'automatisch':
            return True
        elif modus == 'nie':
            return False
        else:  # 'nachfrage'
            # UI muss Dialog anzeigen
            return None  # Signalisiert: UI-Dialog erforderlich

    def generiere_kundennummer(self) -> str:
        """
        Generiert nächste Kundennummer: K-001, K-002, ...
        """
        cursor = self.db.execute(
            "SELECT MAX(CAST(SUBSTR(kundennummer, 3) AS INTEGER)) FROM kunden WHERE kundennummer LIKE 'K-%'"
        )
        max_nr = cursor.fetchone()[0] or 0
        return f"K-{max_nr + 1:03d}"

    def speichere_kunde(self, kunde: Kunde) -> Kunde:
        """
        Speichert Kunde in Datenbank
        """
        # Validierung
        errors = kunde.validate()
        if errors:
            raise ValueError(f"Validierungsfehler: {', '.join(errors)}")

        # Kundennummer generieren
        if not kunde.kundennummer:
            kunde.kundennummer = self.generiere_kundennummer()

        # Standard-Zahlungsziel vom User übernehmen
        if kunde.zahlungsziel == 14 and not kunde.zahlungsziel_individuell:
            kunde.zahlungsziel = self.user_settings.zahlungsziel_standard or 14

        # USt-IdNr. validieren (falls vorhanden und EU)
        if kunde.ust_idnr and kunde.land_kategorie == 'eu':
            if not kunde.ust_idnr_validiert:
                self.validiere_ust_idnr(kunde)

        # Speichern
        cursor = self.db.execute("""
            INSERT INTO kunden (
                kundennummer, typ,
                anrede, vorname, nachname,
                firmenname, rechtsform, ansprechpartner,
                strasse, hausnummer, plz, ort, land,
                email, telefon, website,
                zahlungsziel, zahlungsziel_individuell,
                ust_idnr, ust_idnr_validiert, ust_idnr_validierung_datum, ust_idnr_validierung_ergebnis,
                notizen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            kunde.kundennummer, kunde.typ,
            kunde.anrede, kunde.vorname, kunde.nachname,
            kunde.firmenname, kunde.rechtsform, kunde.ansprechpartner,
            kunde.strasse, kunde.hausnummer, kunde.plz, kunde.ort, kunde.land,
            kunde.email, kunde.telefon, kunde.website,
            kunde.zahlungsziel, kunde.zahlungsziel_individuell,
            kunde.ust_idnr, kunde.ust_idnr_validiert, kunde.ust_idnr_validierung_datum, kunde.ust_idnr_validierung_ergebnis,
            kunde.notizen
        ))

        kunde.id = cursor.lastrowid
        self.db.commit()

        return kunde

    def suche_kunden(self, suchbegriff: str, limit: int = 10) -> list[Kunde]:
        """
        Sucht Kunden für Autocomplete
        """
        cursor = self.db.execute("""
            SELECT * FROM kunden
            WHERE
                firmenname LIKE ? OR
                nachname LIKE ? OR
                vorname LIKE ? OR
                kundennummer LIKE ?
            ORDER BY
                anzahl_rechnungen DESC,  -- Häufigste zuerst
                letzte_rechnung_datum DESC,
                kundennummer ASC
            LIMIT ?
        """, (f"%{suchbegriff}%",) * 4 + (limit,))

        return [self._row_to_kunde(row) for row in cursor.fetchall()]

    def validiere_ust_idnr(self, kunde: Kunde) -> bool:
        """
        Validiert USt-IdNr. über BZSt-API (siehe Sektion 5.8)
        """
        from ust_idnr_service import UStIdNrService

        service = UStIdNrService(
            eigene_ust_idnr=self.user_settings.ust_idnr,
            firmenname=self.user_settings.firmenname or f"{self.user_settings.vorname} {self.user_settings.nachname}",
            ort=self.user_settings.ort,
            plz=self.user_settings.plz,
            strasse=self.user_settings.strasse
        )

        result = service.qualifizierte_abfrage(
            partner_ust_idnr=kunde.ust_idnr,
            partner_firmenname=kunde.firmenname or f"{kunde.vorname} {kunde.nachname}",
            partner_ort=kunde.ort,
            partner_plz=kunde.plz,
            partner_strasse=kunde.strasse
        )

        kunde.ust_idnr_validiert = result['gueltig']
        kunde.ust_idnr_validierung_datum = date.today()
        kunde.ust_idnr_validierung_ergebnis = json.dumps(result)

        return result['gueltig']
```

---

#### **📝 Workflow-Beispiele**

**Beispiel 1: User mit Modus "nachfrage" (Standard)**

```
1. User klickt "Neue Rechnung"
2. UI zeigt Kundensuche + "Neuen Kunden eingeben"
3. User gibt neuen Kunden ein (z.B. "Belgischer Kunde GmbH")
4. User klickt "Weiter"
5. Dialog erscheint: "Soll dieser Kunde im Kundenstamm gespeichert werden?"
6. User wählt "Ja, speichern"
7. Kunde wird gespeichert (K-089)
8. Rechnung wird erstellt mit kunde_id=89
```

**Beispiel 2: User mit Modus "automatisch"**

```
1. User klickt "Neue Rechnung"
2. UI zeigt Kundensuche + "Neuen Kunden eingeben"
3. User gibt neuen Kunden ein
4. User klickt "Weiter"
5. Hinweis erscheint kurz: "Kunde wurde als K-090 gespeichert"
6. Rechnung wird erstellt mit kunde_id=90
```

**Beispiel 3: User mit Modus "nie"**

```
1. User klickt "Neue Rechnung"
2. UI zeigt Kundensuche (falls manuell angelegte Kunden existieren) + "Neuen Kunden eingeben"
3. User gibt neuen Kunden ein
4. User klickt "Weiter"
5. Kunde wird NICHT gespeichert (kunde_id=NULL in Rechnung)
6. Kundendaten werden in `rechnungen.kunde_json` gespeichert (Fallback)
```

---

#### **✅ Vorteile der Hybrid-Lösung**

1. **Maximale Flexibilität**: User entscheidet selbst (einmalig in Einstellungen)
2. **Kein Overhead bei Einmalkunden**: Modus "nie" spart DSGVO-Aufwand
3. **Komfort bei Stammkunden**: Modus "automatisch" spart Klicks
4. **Lernkurve sanft**: Standard "nachfrage" erklärt Feature beim ersten Mal
5. **Jederzeit änderbar**: User kann Modus später umschalten
6. **Keine Datenverluste**: Auch bei Modus "nie" können Kunden manuell angelegt werden

---

#### **🔍 Zusätzliche Features**

**Kundennummer automatisch generiert:**
- K-001, K-002, K-003, ...
- Fortlaufend, keine Lücken

**Zahlungsziel:**
- Standard: 14 Tage (vom User-Setting übernommen)
- Pro Kunde individuell änderbar (Checkbox "Abweichend vom Standard")

**Ansprechpartner:**
- Für Firmen: Kontaktperson erfassen
- Bei Rechnung wird Ansprechpartner angezeigt: "z.Hd. Max Mustermann"

**Inland/EU/Drittland automatisch:**
- Wird aus `land` abgeleitet (Generated Column in SQLite)
- Keine manuelle Eingabe nötig
- Wichtig für USt-Behandlung in UStVA/ZM

---

**Status:** ✅ **Kategorie 8.10 vollständig geklärt** - Hybrid-Lösung mit konfigurierbarem Modus (automatisch / auf Nachfrage / nie). Alle Felder spezifiziert: Kundennummer (automatisch), Ansprechpartner, Zahlungsziel, Inland/EU/Drittland-Automatik, USt-IdNr.-Validierung (BZSt-API).

---

### **8.10.1 Rechtliche Dokumente (B2B vs. B2C)** ⚖️ WICHTIG

**Problem:** Unterschiedliche Pflichten bei Geschäftskunden (B2B) vs. Privatkunden (B2C)

---

#### **⚠️ RECHTLICHER HINWEIS - BITTE LESEN!**

```
┌──────────────────────────────────────────────────┐
│ ⚠️ WICHTIG: Keine Rechtsberatung!               │
├──────────────────────────────────────────────────┤
│                                                  │
│ Diese Dokumentation stellt KEINE Rechtsberatung │
│ dar!                                             │
│                                                  │
│ Widerrufsfristen können sich ändern!            │
│                                                  │
│ ✅ BITTE VOR EINSATZ PRÜFEN:                    │
│                                                  │
│ 1. Aktuelle Widerrufsfrist in Deutschland:      │
│    → §355 BGB, §312g BGB                        │
│    → Stand dieser Doku: 14 Tage (Januar 2025)  │
│                                                  │
│ 2. Quellen zur Prüfung:                          │
│    → https://www.gesetze-im-internet.de/bgb/    │
│    → Verbraucherzentrale                        │
│    → Rechtsanwalt konsultieren!                 │
│                                                  │
│ 3. Bei Änderung:                                 │
│    → Konstante WIDERRUFSFRIST_TAGE anpassen     │
│    → Siehe config.py                            │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

#### **📋 B2B vs. B2C Anforderungen**

```
┌──────────────────────────────────────────────────┐
│ Rechtliche Dokumente - Übersicht                │
├──────────────────────────────────────────────────┤
│                                                  │
│ B2B (Geschäftskunde):                            │
│ ✅ AGBs MÜSSEN aktiv mitgegeben werden          │
│    (§305 Abs. 2 BGB)                             │
│ ❌ Widerrufsbelehrung NICHT erforderlich        │
│ ℹ️ Datenschutzerklärung auf Anfrage             │
│                                                  │
│ B2C (Privatkunde):                               │
│ ✅ AGBs zur Verfügung stellen                   │
│ ✅ Widerrufsbelehrung bei Fernabsatz (PFLICHT!) │
│    (§312g BGB, BGB-InfoV)                        │
│ ✅ Informationspflichten nach BGB-InfoV         │
│ ✅ Datenschutzerklärung (DSGVO)                 │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Wichtig:**
- **B2B:** AGBs müssen **aktiv einbezogen** werden (z.B. als PDF-Anhang)
- **B2C:** AGBs + Widerrufsbelehrung + Informationspflichten
- **Erkennung:** Über `kunde.typ` ('firma' = B2B, 'privat' = B2C)

---

#### **📄 Welche Dokumente?**

**1. AGBs (Allgemeine Geschäftsbedingungen)**

**B2B:**
- ✅ **PFLICHT:** Aktiv mitgeben (§305 Abs. 2 BGB)
- **Wie:** PDF-Anhang an Rechnung ODER Link in Rechnung
- **Wann:** Bei jeder Rechnung (sofern nicht bereits übermittelt)

**B2C:**
- ✅ **PFLICHT:** Zur Verfügung stellen
- **Wie:** Link in Rechnung oder auf Website
- **Wann:** Vor Vertragsschluss

---

**2. Widerrufsbelehrung**

**B2B:**
- ❌ **NICHT erforderlich** (nur für Verbraucher)

**B2C:**
- ✅ **PFLICHT bei Fernabsatzverträgen** (§312g BGB)
- **Wie:** PDF-Anhang oder in Rechnung integriert
- **Wann:** Bei jeder Rechnung (Fernabsatz)
- **Frist:** **14 Tage** ab Vertragsschluss (§355 BGB) ⚠️ **BITTE PRÜFEN!**
  - Stand: Januar 2025
  - Konfigurierbar in `config.py` → `WIDERRUFSFRIST_TAGE`
  - **Bei Gesetzesänderung:** Konstante anpassen!

**Ausnahmen (keine Widerrufsbelehrung erforderlich):**
- Dienstleistungen vollständig erbracht
- Individuell angefertigte Produkte
- Verderbliche Waren

---

**3. Informationspflichten (BGB-InfoV)**

**B2C:**
- ✅ Identität des Unternehmers
- ✅ Wesentliche Eigenschaften der Ware/Dienstleistung
- ✅ Gesamtpreis inkl. USt
- ✅ Lieferkosten
- ✅ Zahlungsbedingungen
- ✅ Lieferbedingungen

**B2B:**
- ℹ️ Teilweise erforderlich (je nach Vertrag)

---

#### **💻 Implementierung in RechnungsFee**

**Datenbank-Schema:**

```sql
-- Rechtliche Dokumente
CREATE TABLE rechtliche_dokumente (
    id INTEGER PRIMARY KEY,

    -- Art des Dokuments
    typ TEXT NOT NULL,  -- 'agb', 'widerruf', 'datenschutz', 'impressum'

    -- Für wen gilt es?
    gueltig_fuer TEXT NOT NULL,  -- 'b2b', 'b2c', 'beide'

    -- Dokument
    titel TEXT NOT NULL,  -- "AGBs Stand 2024"
    datei_pfad TEXT,  -- "dokumente/agb_2024.pdf"
    datei_hash TEXT,  -- SHA256 für Versionierung

    -- Version
    version TEXT,  -- "1.0", "2.0"
    gueltig_ab DATE NOT NULL,
    gueltig_bis DATE,  -- NULL = aktuell gültig

    -- Metadaten
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    erstellt_von TEXT,

    -- Aktiv?
    aktiv BOOLEAN DEFAULT 1
);

-- Zuordnung: Welche Dokumente wurden mit Rechnung versendet?
CREATE TABLE rechnung_dokumente (
    id INTEGER PRIMARY KEY,

    rechnung_id INTEGER NOT NULL,
    dokument_id INTEGER NOT NULL,

    -- Nachweis
    versendet_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    versand_methode TEXT,  -- 'pdf_anhang', 'link', 'integriert'

    FOREIGN KEY (rechnung_id) REFERENCES rechnungen(id),
    FOREIGN KEY (dokument_id) REFERENCES rechtliche_dokumente(id)
);
```

---

#### **🔄 Workflow: Rechnung erstellen**

```python
def erstelle_rechnung(kunde_id: int, positionen: list) -> Rechnung:
    """
    Erstellt Rechnung mit automatischer Anhängung rechtlicher Dokumente
    """
    kunde = db.get_kunde(kunde_id)
    rechnung = create_rechnung(kunde, positionen)

    # Rechtliche Dokumente bestimmen
    dokumente = []

    if kunde.typ == 'firma':  # B2B
        # AGBs PFLICHT
        agb = get_aktives_dokument('agb', 'b2b')
        if agb:
            dokumente.append(agb)
        else:
            raise ValueError("AGBs für B2B fehlen! Bitte in Einstellungen hochladen.")

    elif kunde.typ == 'privat':  # B2C
        # AGBs + Widerrufsbelehrung
        agb = get_aktives_dokument('agb', 'b2c')
        widerruf = get_aktives_dokument('widerruf', 'b2c')

        if agb:
            dokumente.append(agb)
        if widerruf and ist_fernabsatz(rechnung):
            dokumente.append(widerruf)

    # Dokumente anhängen
    for dok in dokumente:
        haenge_dokument_an(rechnung, dok)

    return rechnung


def haenge_dokument_an(rechnung: Rechnung, dokument: RechtlichesDokument):
    """
    Hängt rechtliches Dokument an Rechnung an
    """
    # Methode 1: PDF-Anhang (Standard)
    if dokument.datei_pfad:
        rechnung.anhaenge.append(dokument.datei_pfad)
        versand_methode = 'pdf_anhang'

    # Methode 2: Link in Rechnung (alternativ)
    else:
        link = f"https://example.com/rechtliches/{dokument.typ}.pdf"
        rechnung.fusszeile += f"\n{dokument.titel}: {link}"
        versand_methode = 'link'

    # Nachweis protokollieren
    db.execute("""
        INSERT INTO rechnung_dokumente (rechnung_id, dokument_id, versand_methode)
        VALUES (?, ?, ?)
    """, (rechnung.id, dokument.id, versand_methode))

    db.commit()


def ist_fernabsatz(rechnung: Rechnung) -> bool:
    """
    Prüft ob Fernabsatzvertrag (Widerrufsbelehrung erforderlich)

    Fernabsatz = Vertrag ohne gleichzeitige Anwesenheit
    (z.B. Online-Shop, E-Mail, Telefon)
    """
    # Vereinfachung: Immer True bei B2C
    # Erweiterte Logik: Prüfung Vertriebsweg
    return True
```

---

#### **🖥️ UI: Rechtliche Dokumente verwalten**

```
┌──────────────────────────────────────────────────┐
│ ⚙️ Einstellungen > Rechtliche Dokumente         │
├──────────────────────────────────────────────────┤
│                                                  │
│ [ + Neues Dokument hochladen ]                   │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ 📄 AGBs (B2B) - Stand 2024               │  │
│ ├────────────────────────────────────────────┤  │
│ │ Typ: AGBs                                  │  │
│ │ Gültig für: B2B (Geschäftskunden)          │  │
│ │ Version: 1.0                               │  │
│ │ Gültig ab: 01.01.2024                      │  │
│ │ Datei: agb_b2b_2024.pdf (142 KB)           │  │
│ │                                            │  │
│ │ ✅ Aktiv (wird automatisch angehängt)     │  │
│ │                                            │  │
│ │ [Bearbeiten] [Deaktivieren] [Löschen]     │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ 📄 AGBs (B2C) - Stand 2024               │  │
│ ├────────────────────────────────────────────┤  │
│ │ Typ: AGBs                                  │  │
│ │ Gültig für: B2C (Privatkunden)             │  │
│ │ Version: 1.0                               │  │
│ │ Gültig ab: 01.01.2024                      │  │
│ │ Datei: agb_b2c_2024.pdf (156 KB)           │  │
│ │                                            │  │
│ │ ✅ Aktiv                                   │  │
│ │                                            │  │
│ │ [Bearbeiten] [Deaktivieren] [Löschen]     │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ 📄 Widerrufsbelehrung (B2C)              │  │
│ ├────────────────────────────────────────────┤  │
│ │ Typ: Widerrufsbelehrung                    │  │
│ │ Gültig für: B2C (Privatkunden)             │  │
│ │ Version: 1.0                               │  │
│ │ Gültig ab: 01.01.2024                      │  │
│ │ Datei: widerruf_2024.pdf (89 KB)           │  │
│ │                                            │  │
│ │ ✅ Aktiv (bei Fernabsatz)                 │  │
│ │                                            │  │
│ │ [Bearbeiten] [Deaktivieren] [Löschen]     │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ ⚠️ Hinweis:                                     │
│ Bei B2B-Kunden werden AGBs automatisch als      │
│ PDF-Anhang mitgesendet (§305 Abs. 2 BGB).       │
│                                                  │
│ Bei B2C-Kunden werden AGBs + Widerrufsbelehrung │
│ mitgesendet (§312g BGB, BGB-InfoV).              │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

#### **📧 E-Mail-Versand mit Anhängen**

```python
def versende_rechnung_email(rechnung_id: int):
    """
    Versendet Rechnung per E-Mail mit rechtlichen Dokumenten
    """
    rechnung = db.get_rechnung(rechnung_id)
    kunde = rechnung.kunde

    # PDF generieren
    rechnung_pdf = generate_rechnung_pdf(rechnung)

    # Anhänge sammeln
    anhaenge = [rechnung_pdf]

    # Rechtliche Dokumente hinzufügen
    dokumente = db.execute("""
        SELECT d.* FROM rechnung_dokumente rd
        JOIN rechtliche_dokumente d ON rd.dokument_id = d.id
        WHERE rd.rechnung_id = ?
        AND rd.versand_methode = 'pdf_anhang'
    """, (rechnung_id,)).fetchall()

    for dok in dokumente:
        anhaenge.append(dok.datei_pfad)

    # E-Mail zusammenstellen
    betreff = f"Rechnung {rechnung.rechnungsnummer}"

    if kunde.typ == 'firma':  # B2B
        text = f"""
        Sehr geehrte Damen und Herren,

        anbei erhalten Sie die Rechnung {rechnung.rechnungsnummer}.

        Im Anhang finden Sie:
        - Rechnung {rechnung.rechnungsnummer}.pdf
        - AGBs.pdf

        Mit freundlichen Grüßen
        """
    else:  # B2C
        text = f"""
        Sehr geehrte/r {kunde.anrede} {kunde.nachname},

        anbei erhalten Sie die Rechnung {rechnung.rechnungsnummer}.

        Im Anhang finden Sie:
        - Rechnung {rechnung.rechnungsnummer}.pdf
        - AGBs.pdf
        - Widerrufsbelehrung.pdf

        Sie haben ein Widerrufsrecht von 14 Tagen ab Erhalt dieser E-Mail.

        Mit freundlichen Grüßen
        """

    # E-Mail versenden
    send_email(
        to=kunde.email,
        betreff=betreff,
        text=text,
        anhaenge=anhaenge
    )
```

---

#### **⚠️ Wichtige Hinweise**

**1. Versionierung:**
- Bei Änderung der AGBs: Neue Version anlegen
- Alte Version bleibt aktiv für bestehende Verträge
- Neue Rechnungen nutzen neue Version

**2. Nachweis:**
- Alle versendeten Dokumente werden in `rechnung_dokumente` protokolliert
- Wichtig bei Streitigkeiten: Nachweis dass AGBs übermittelt wurden

**3. Sprache:**
- Bei ausländischen Kunden: AGBs in Landessprache?
- Mindestens: Deutsche Version

**4. Individueller Vertrag:**
- Wenn individueller Vertrag existiert: AGBs optional
- Aber: Empfohlen für Standard-Klauseln

---

#### **📋 Checkliste: Setup**

```
┌──────────────────────────────────────────────────┐
│ ✅ Rechtliche Dokumente - Checkliste            │
├──────────────────────────────────────────────────┤
│                                                  │
│ ☑ AGBs für B2B erstellt und hochgeladen         │
│   → Pflicht nach §305 Abs. 2 BGB                │
│                                                  │
│ ☑ AGBs für B2C erstellt und hochgeladen         │
│   → Empfohlen                                    │
│                                                  │
│ ☑ Widerrufsbelehrung für B2C erstellt           │
│   → Pflicht bei Fernabsatz (§312g BGB)          │
│                                                  │
│ ☑ Datenschutzerklärung erstellt                 │
│   → DSGVO-Pflicht                                │
│                                                  │
│ ☑ Automatische Anhängung aktiviert              │
│   → In Einstellungen konfiguriert               │
│                                                  │
│ ☑ Test-Rechnung erstellt (B2B)                  │
│   → Prüfen: AGBs angehängt?                     │
│                                                  │
│ ☑ Test-Rechnung erstellt (B2C)                  │
│   → Prüfen: AGBs + Widerruf angehängt?          │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

#### **🎓 Beispiel: Musterdokumente**

**AGBs (B2B) - Kurzversion:**

```
ALLGEMEINE GESCHÄFTSBEDINGUNGEN

1. Geltungsbereich
Diese AGBs gelten für alle Geschäftsbeziehungen mit Unternehmern.

2. Vertragsschluss
Der Vertrag kommt mit Annahme des Angebots zustande.

3. Zahlungsbedingungen
Zahlungsziel: 14 Tage netto.

4. Gewährleistung
Es gelten die gesetzlichen Gewährleistungsrechte.

5. Haftung
[...]
```

**Widerrufsbelehrung (B2C) - Muster:**

```
WIDERRUFSBELEHRUNG

Widerrufsrecht:
Sie haben das Recht, binnen vierzehn Tagen ohne Angabe von Gründen
diesen Vertrag zu widerrufen.

Die Widerrufsfrist beträgt vierzehn Tage ab dem Tag [...]

Um Ihr Widerrufsrecht auszuüben, müssen Sie uns mittels einer
eindeutigen Erklärung (z.B. per Post oder E-Mail) über Ihren
Entschluss informieren.

Kontakt für Widerruf:
[Name]
[Adresse]
[E-Mail]
```

---

**Status:** ✅ **B2B vs. B2C Anforderungen dokumentiert**

**Wichtigste Punkte:**
1. ✅ **B2B:** AGBs PFLICHT als Anhang (§305 Abs. 2 BGB)
2. ✅ **B2C:** AGBs + Widerrufsbelehrung bei Fernabsatz (§312g BGB)
3. ✅ **Automatische Erkennung** über `kunde.typ`
4. ✅ **Nachweis** in `rechnung_dokumente` Tabelle
5. ✅ **Versionierung** für rechtssichere Nachweisbarkeit

---

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

## **Kategorie 10.1: Backup-Strategie**

### **🎯 Anforderungen**

**Kernanforderungen:**
- ✅ **Lokale Backups** (keine Cloud-Abhängigkeit)
- ✅ **Mehrere Backup-Ziele parallel** (3-2-1-Regel)
- ✅ **Automatische & manuelle Backups**
- ✅ **Verschlüsselung optional** (AES-256)
- ✅ **GoBD-konform** (Unveränderbarkeit, Vollständigkeit)
- ⏸️ **Cloud-Backup** (v2.0 - zurückgestellt)

---

### **📂 Backup-Ziele**

#### **1. Lokales Verzeichnis**
```
Beispiel: /backup/rechnungspilot/
         C:\Backups\RechnungsFee\
```
**Eigenschaften:**
- ✅ Einfachste Variante
- ✅ Schnell
- ⚠️ Gleiche Festplatte → bei HDD-Ausfall verloren
- **Use Case:** Schnelle Wiederherstellung, Test-Backups

#### **2. Externe Festplatte / USB-Stick**
```
Beispiel: /media/usb-backup/
         D:\  (Windows - Wechseldatenträger)
```
**Eigenschaften:**
- ✅ Physisch getrennt (Fire/Theft Protection)
- ✅ Offline (Ransomware-Schutz)
- ⚠️ Manuelles Anschließen erforderlich
- **Use Case:** Tägliches Backup vor Feierabend

#### **3. Netzlaufwerk / NAS**
```
SMB/CIFS-Share:
  smb://nas.local/backups/rechnungspilot
  \\NAS\Backups\RechnungsFee

NFS:
  nfs://192.168.1.100/backups
```
**Eigenschaften:**
- ✅ Immer verfügbar (automatische Backups)
- ✅ Zentrale Verwaltung
- ✅ Meist RAID-geschützt
- ✅ Mehrere Geräte können zugreifen
- **Use Case:** Automatische nächtliche Backups

**Gängige NAS-Systeme:**
- Synology DiskStation
- QNAP
- TrueNAS
- Eigener Linux-Server (Samba)

#### **4. Lokale Freigabe (anderer PC im Netzwerk)**
```
Windows-Freigabe:
  \\DESKTOP-PC\Freigaben\Backups

Linux Samba-Share:
  smb://192.168.1.50/shared/backups
```
**Eigenschaften:**
- ✅ Keine zusätzliche Hardware nötig
- ⚠️ Abhängig von anderem PC (muss laufen)
- **Use Case:** Kleine Büros, Heimnetzwerk

---

### **🔄 3-2-1-Backup-Regel**

**Empfehlung für RechnungsFee:**

```
3 Kopien der Daten:
  1. Original (Produktiv-Datenbank)
  2. Lokales Backup (externe HDD)
  3. Netzwerk-Backup (NAS)

2 verschiedene Medien:
  - SSD/HDD (Produktiv)
  - Externe HDD (Backup 1)
  - NAS (anderes Medium - Backup 2)

1 Kopie offsite:
  - Optional: USB-HDD im Bankschließfach
  - Optional: Cloud (v2.0)
```

**Konfiguration in RechnungsFee:**
```
┌─────────────────────────────────────────────────────────┐
│ ⚙️ Backup-Konfiguration                                 │
├─────────────────────────────────────────────────────────┤
│ Backup-Ziel 1 (Primär):                                │
│ ┌─────────────────────────────────────────────────┐     │
│ │ ● Netzlaufwerk (NAS)                            │     │
│ │   Pfad: smb://nas.local/backups/rechnungspilot  │     │
│ │   Benutzer: [backup_user]                       │     │
│ │   Passwort: [***********]                       │     │
│ │   [Verbindung testen] ✅ Verbunden              │     │
│ │                                                 │     │
│ │   Zeitplan:                                     │     │
│ │   ☑ Täglich um 02:00 Uhr                        │     │
│ │   ☑ Verschlüsselung aktiviert (AES-256)        │     │
│ └─────────────────────────────────────────────────┘     │
│                                                         │
│ Backup-Ziel 2 (Sekundär):                              │
│ ┌─────────────────────────────────────────────────┐     │
│ │ ● Externe Festplatte                            │     │
│ │   Pfad: /media/usb-backup/rechnungspilot        │     │
│ │   [Pfad wählen...]                              │     │
│ │                                                 │     │
│ │   Zeitplan:                                     │     │
│ │   ○ Automatisch (wenn angeschlossen)            │     │
│ │   ● Nur manuell                                 │     │
│ │   ☑ Verschlüsselung aktiviert (AES-256)        │     │
│ └─────────────────────────────────────────────────┘     │
│                                                         │
│ Backup-Ziel 3 (Optional):                              │
│ ┌─────────────────────────────────────────────────┐     │
│ │ ○ Deaktiviert                                   │     │
│ │   [+ Weiteres Ziel hinzufügen]                  │     │
│ └─────────────────────────────────────────────────┘     │
│                                                         │
│ [Jetzt Backup durchführen]      [Speichern]            │
└─────────────────────────────────────────────────────────┘
```

---

### **💾 Backup-Strategien**

#### **1. Vollbackup (Full Backup)**

**Beschreibung:** Komplette Kopie aller Daten

**Vorteile:**
- ✅ Einfachste Wiederherstellung (nur ein Backup nötig)
- ✅ Unabhängig von vorherigen Backups

**Nachteile:**
- ❌ Viel Speicherplatz
- ❌ Langsam (bei großen Datenmengen)

**Empfehlung für RechnungsFee:**
- **Wöchentlich:** Vollbackup (z.B. Sonntag Nacht)
- **Aufbewahrung:** 4 Wochen (4 Vollbackups)

**Dateistruktur:**
```
/backup/rechnungspilot/
├── full_2025-12-09_020000.tar.gz.enc
├── full_2025-12-02_020000.tar.gz.enc
├── full_2025-11-25_020000.tar.gz.enc
└── full_2025-11-18_020000.tar.gz.enc
```

#### **2. Inkrementelles Backup**

**Beschreibung:** Nur geänderte Dateien seit dem letzten Backup (egal ob Full oder Inkrementell)

**Vorteile:**
- ✅ Sehr schnell
- ✅ Wenig Speicherplatz

**Nachteile:**
- ❌ Wiederherstellung komplex (braucht Full + alle inkrementellen Backups)
- ❌ Bei Verlust eines inkrementellen Backups → Kette unterbrochen

**Empfehlung für RechnungsFee:**
- **Täglich:** Inkrementelles Backup
- **Aufbewahrung:** 30 Tage

**Dateistruktur:**
```
/backup/rechnungspilot/
├── full_2025-12-09_020000.tar.gz.enc          # Vollbackup (Sonntag)
├── incr_2025-12-10_020000.tar.gz.enc          # +Montag
├── incr_2025-12-11_020000.tar.gz.enc          # +Dienstag
├── incr_2025-12-12_020000.tar.gz.enc          # +Mittwoch
├── incr_2025-12-13_020000.tar.gz.enc          # +Donnerstag
├── incr_2025-12-14_020000.tar.gz.enc          # +Freitag
└── incr_2025-12-15_020000.tar.gz.enc          # +Samstag
```

#### **3. Differentielles Backup**

**Beschreibung:** Nur geänderte Dateien seit dem letzten Vollbackup

**Vorteile:**
- ✅ Schneller als Vollbackup
- ✅ Einfachere Wiederherstellung als inkrementell (nur Full + letztes Diff)

**Nachteile:**
- ⚠️ Wächst im Laufe der Woche (alle Änderungen seit Full)

**Empfehlung für RechnungsFee:**
- Alternative zu inkrementell
- Einfacher für Einsteiger

**Dateistruktur:**
```
/backup/rechnungspilot/
├── full_2025-12-09_020000.tar.gz.enc          # Vollbackup (Sonntag)
├── diff_2025-12-10_020000.tar.gz.enc          # Änderungen seit Sonntag
├── diff_2025-12-11_020000.tar.gz.enc          # Änderungen seit Sonntag
├── diff_2025-12-12_020000.tar.gz.enc          # Änderungen seit Sonntag
└── diff_2025-12-13_020000.tar.gz.enc          # Änderungen seit Sonntag
```

---

### **📦 Backup-Inhalte**

**Was wird gesichert?**

```
rechnungspilot-backup/
├── database/
│   └── rechnungspilot.db              # SQLite-Datenbank (Hauptdaten)
│
├── documents/
│   ├── belege/                        # Eingangsrechnungen (PDFs)
│   ├── rechnungen/                    # Ausgangsrechnungen (PDFs)
│   ├── agb/                           # AGB-Versionen
│   └── widerrufsbelehrung/            # Widerrufsbelehrungen
│
├── imports/
│   ├── 2025/12/09/                    # Import-Archive (Bank-CSV, etc.)
│   │   ├── sparkasse_20251209.csv
│   │   └── paypal_20251209.csv
│   └── ...
│
├── config/
│   ├── settings.json                  # Benutzer-Einstellungen
│   ├── templates/                     # Bank-CSV-Templates (User)
│   └── firma.json                     # Firmenstammdaten
│
└── metadata.json                      # Backup-Metadaten (Timestamp, Version, Hash)
```

**Größenabschätzung:**
```
Startgröße (frische Installation):   ~50 MB
Nach 1 Jahr (100 Rechnungen/Monat):  ~2 GB
  - Datenbank: 100 MB
  - Belege (PDFs): 1,5 GB (avg. 150 KB/PDF × 1200 PDFs)
  - Imports: 200 MB
  - Config: 10 MB
```

---

### **🔐 Verschlüsselung**

**⭐ STANDARDMÄSSIG AKTIVIERT** (Privacy by Default - DSGVO Art. 25)

**Warum Verschlüsselung als Standard?**

1. ✅ **DSGVO Art. 32** fordert Verschlüsselung explizit
2. ✅ **DSGVO Art. 34 Abs. 3 lit. a:** Bei Verschlüsselung **KEINE Meldepflicht** bei Verlust/Diebstahl!
3. ✅ **Schutz vor physischem Zugriff:** USB-Stick verloren? Kein Problem!
4. ✅ **Geschäftsgeheimnisse geschützt:** Umsätze, Preise, Kundenbeziehungen
5. ✅ **Kein Bußgeld-Risiko** bei Datenverlust

**Was passiert OHNE Verschlüsselung bei Verlust?**
```
❌ Meldepflicht an Datenschutzbehörde (72h)
❌ Benachrichtigung ALLER Kunden
❌ Bußgeld bis 20 Mio. € oder 4% Jahresumsatz
❌ Reputationsschaden
```

**Mit Verschlüsselung:**
```
✅ Keine Meldepflicht (Art. 34 Abs. 3 DSGVO)
✅ Keine Kundenbenachrichtigung nötig
✅ Daten bleiben geschützt
✅ Kein Bußgeld-Risiko
```

**Deaktivierung möglich:** User kann Verschlüsselung deaktivieren (opt-out), aber nur mit expliziter Risiko-Warnung.

**Algorithmus:** AES-256 (industry standard)

**Implementierung:**
```python
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

def encrypt_backup(backup_file: str, password: str) -> str:
    """
    Verschlüsselt Backup-Datei mit AES-256.
    """
    # 1. Passwort → Schlüssel (PBKDF2)
    salt = os.urandom(16)
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bit
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = kdf.derive(password.encode())

    # 2. Initialisierungsvektor (IV)
    iv = os.urandom(16)

    # 3. Datei verschlüsseln
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    with open(backup_file, 'rb') as f_in:
        plaintext = f_in.read()

    # Padding (AES benötigt Vielfaches von 16 Bytes)
    padding_length = 16 - (len(plaintext) % 16)
    plaintext += bytes([padding_length]) * padding_length

    ciphertext = encryptor.update(plaintext) + encryptor.finalize()

    # 4. Salt + IV + Ciphertext speichern
    encrypted_file = backup_file + '.enc'
    with open(encrypted_file, 'wb') as f_out:
        f_out.write(salt)       # 16 Bytes
        f_out.write(iv)         # 16 Bytes
        f_out.write(ciphertext) # Rest

    # Original-Datei löschen (sicher)
    os.remove(backup_file)

    return encrypted_file
```

**UI - Standard-Einrichtung:**
```
┌─────────────────────────────────────────────────────────┐
│ 🔐 Backup-Verschlüsselung (DSGVO-konform)               │
├─────────────────────────────────────────────────────────┤
│ ☑ Backups verschlüsseln (empfohlen, DSGVO Art. 32)     │
│                                                         │
│ ℹ️ Warum Verschlüsselung wichtig ist:                   │
│ • Schutz bei Diebstahl/Verlust (Art. 32 DSGVO)         │
│ • Keine Meldepflicht bei Datenverlust (Art. 34 DSGVO)  │
│ • Geschäftsgeheimnisse geschützt                       │
│ • Kundendaten bleiben vertraulich                      │
│                                                         │
│ Verschlüsselungs-Passwort:                              │
│ ┌─────────────────────────────────────────────────┐     │
│ │ [●●●●●●●●●●●●●●●●●●●●]  [Generieren]           │     │
│ └─────────────────────────────────────────────────┘     │
│ Stärke: ████████████████░░░░ Stark                      │
│                                                         │
│ Passwort wiederholen:                                   │
│ ┌─────────────────────────────────────────────────┐     │
│ │ [●●●●●●●●●●●●●●●●●●●●]                          │     │
│ └─────────────────────────────────────────────────┘     │
│                                                         │
│ ☑ Passwort in System-Keychain speichern (empfohlen)    │
│   (Automatische Wiederherstellung ohne Passwort-Eingabe)│
│                                                         │
│ ⚠️ WICHTIG: Passwort zusätzlich sicher aufbewahren!    │
│    (z.B. Passwort-Manager, Notiz im Safe)              │
│    Ohne Passwort ist Backup nicht wiederherstellbar!   │
│                                                         │
│ [Erweiterte Optionen...]                [Speichern]     │
└─────────────────────────────────────────────────────────┘
```

**UI - Erweiterte Optionen (Deaktivierung mit Warnung):**
```
┌─────────────────────────────────────────────────────────┐
│ ⚙️ Erweiterte Backup-Optionen                           │
├─────────────────────────────────────────────────────────┤
│ Verschlüsselung:                                        │
│ ☐ Verschlüsselung deaktivieren (NICHT empfohlen!)      │
│                                                         │
│ ⚠️ WARNUNG - Datenschutzrisiko!                        │
│ ┌─────────────────────────────────────────────────┐     │
│ │ Unverschlüsselte Backups sind ein Risiko:      │     │
│ │                                                 │     │
│ │ Bei Diebstahl/Verlust musst du:                │     │
│ │ • Datenschutzbehörde informieren (Art. 33)     │     │
│ │ • ALLE Kunden benachrichtigen (Art. 34)        │     │
│ │ • Mit Bußgeldern rechnen (bis 20 Mio. €)      │     │
│ │                                                 │     │
│ │ Nur deaktivieren wenn:                          │     │
│ │ • Backup-Medium physisch gesichert (Safe)       │     │
│ │ • Kein Transport (bleibt im verschl. Raum)     │     │
│ │ • Sie das Risiko verstehen und akzeptieren     │     │
│ └─────────────────────────────────────────────────┘     │
│                                                         │
│ ☐ Ich verstehe das Risiko und verzichte auf            │
│   Verschlüsselung (Haftung liegt bei mir)              │
│                                                         │
│ [Abbrechen]                              [Speichern]    │
└─────────────────────────────────────────────────────────┘
```

---

### **⏰ Backup-Zeitplan**

**Automatische Backups:**

```python
# Beispiel: Backup-Schedule
backup_schedule = {
    'vollbackup': {
        'frequenz': 'wöchentlich',
        'wochentag': 'Sonntag',
        'uhrzeit': '02:00',
        'aufbewahrung': 4  # 4 Wochen
    },
    'inkrementell': {
        'frequenz': 'täglich',
        'uhrzeit': '02:00',
        'aufbewahrung': 30  # 30 Tage
    },
    'vor_update': {
        'trigger': 'auto',  # Automatisch vor jedem Update
        'typ': 'vollbackup',
        'aufbewahrung': 'permanent'  # Nicht automatisch löschen
    }
}
```

**UI:**
```
┌─────────────────────────────────────────────────────────┐
│ ⏰ Backup-Zeitplan                                      │
├─────────────────────────────────────────────────────────┤
│ Vollbackup:                                             │
│ ☑ Automatisch                                           │
│   Wöchentlich, jeden [Sonntag ▼] um [02:00]            │
│   Aufbewahrung: [4] Wochen                              │
│                                                         │
│ Inkrementelles Backup:                                  │
│ ☑ Automatisch                                           │
│   Täglich um [02:00]                                    │
│   Aufbewahrung: [30] Tage                               │
│                                                         │
│ Sonder-Backups:                                         │
│ ☑ Vor Software-Updates (automatisch)                   │
│ ☑ Vor DATEV-Export (optional)                          │
│ ☑ Vor Jahresabschluss (Erinnerung)                     │
│                                                         │
│ ⭐ Backup beim Beenden:                                 │
│ ☑ Automatisches Backup beim Beenden (wenn Änderungen)  │
│   (Greift nur, wenn KEIN automatischer Zeitplan aktiv) │
│                                                         │
│ Nächstes geplantes Backup:                             │
│ 📅 Sonntag, 15.12.2025 um 02:00 Uhr (Vollbackup)       │
│                                                         │
│ [Backup jetzt durchführen]              [Speichern]    │
└─────────────────────────────────────────────────────────┘
```

---

### **💾 Backup beim Beenden (Exit-Backup)**

**Problem:** User vergessen oft manuelle Backups!

**Lösung:** Automatisches Backup beim Beenden der Anwendung, wenn:
1. ✅ **KEINE** automatische Zeitplanung aktiv ist (weder täglich noch wöchentlich)
2. ✅ Es **Änderungen** seit dem letzten Backup gab
3. ✅ Die Option aktiviert ist (Standard: AN)

**Vorteil:**
- Backups werden niemals vergessen
- Beenden ist ein natürlicher Zeitpunkt (Arbeitstag abgeschlossen)
- Nur wenn wirklich etwas geändert wurde

#### **Change-Tracking (Änderungserkennung)**

**RechnungsFee trackt automatisch alle Änderungen:**

```sql
-- Change Tracking Tabelle
CREATE TABLE change_log (
    id INTEGER PRIMARY KEY,
    tabelle TEXT NOT NULL,         -- 'rechnungen', 'belege', 'kunden', etc.
    aktion TEXT NOT NULL,           -- 'insert', 'update', 'delete'
    datensatz_id INTEGER,
    geaendert_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger bei jeder Änderung (Beispiel: Rechnungen)
CREATE TRIGGER rechnung_changed
AFTER INSERT ON rechnungen
BEGIN
    INSERT INTO change_log (tabelle, aktion, datensatz_id)
    VALUES ('rechnungen', 'insert', NEW.id);
END;

CREATE TRIGGER rechnung_updated
AFTER UPDATE ON rechnungen
BEGIN
    INSERT INTO change_log (tabelle, aktion, datensatz_id)
    VALUES ('rechnungen', 'update', NEW.id);
END;

-- Funktion: Hat sich was geändert?
CREATE VIEW hat_aenderungen AS
SELECT
    COUNT(*) AS anzahl_aenderungen,
    MAX(geaendert_am) AS letzte_aenderung
FROM change_log
WHERE geaendert_am > (
    SELECT MAX(erstellt_am) FROM backups WHERE status = 'erfolgreich'
);
```

#### **UI: Beenden-Dialog mit Backup**

**Fall 1: Änderungen vorhanden, Exit-Backup aktiv**

```
┌─────────────────────────────────────────────────────────┐
│ 💾 Backup vor dem Beenden                               │
├─────────────────────────────────────────────────────────┤
│ Seit dem letzten Backup hast du einiges geändert:      │
│                                                         │
│ • 3 neue Rechnungen                                     │
│ • 2 neue Belege                                         │
│ • 1 Kunde aktualisiert                                  │
│                                                         │
│ Letzte Änderung: Heute, 17:42 Uhr                      │
│ Letztes Backup:  Gestern, 02:00 Uhr                    │
│                                                         │
│ ☑ Backup jetzt durchführen (empfohlen)                 │
│                                                         │
│ Backup-Ziel: Netzlaufwerk (NAS)                        │
│ Geschätzte Dauer: ~30 Sekunden                         │
│                                                         │
│ [Ohne Backup beenden]          [Backup & Beenden ✅]    │
└─────────────────────────────────────────────────────────┘
```

**Backup läuft:**

```
┌─────────────────────────────────────────────────────────┐
│ 💾 Backup wird erstellt...                              │
├─────────────────────────────────────────────────────────┤
│ ████████████████████░░░░░░ 75%                          │
│                                                         │
│ Verschlüssele Daten...                                  │
│                                                         │
│ Bitte warte, RechnungsFee wird nach dem              │
│ Backup automatisch geschlossen.                        │
│                                                         │
│ [Im Hintergrund beenden] ❌ Nicht empfohlen             │
└─────────────────────────────────────────────────────────┘
```

**Backup erfolgreich:**

```
┌─────────────────────────────────────────────────────────┐
│ ✅ Backup erfolgreich!                                  │
├─────────────────────────────────────────────────────────┤
│ Backup wurde erfolgreich erstellt:                     │
│                                                         │
│ 📁 Datei: full_2025-12-09_174530.tar.gz.enc            │
│ 📊 Größe: 2,3 MB                                        │
│ 🔐 Verschlüsselt: Ja (AES-256)                         │
│ 📍 Ziel: smb://nas.local/backups/rechnungspilot        │
│                                                         │
│ RechnungsFee wird jetzt geschlossen.                 │
│                                                         │
│ [Schließen ✓]                                           │
└─────────────────────────────────────────────────────────┘
```

**Fall 2: KEINE Änderungen → Kein Backup nötig**

```
┌─────────────────────────────────────────────────────────┐
│ 👋 Auf Wiedersehen!                                     │
├─────────────────────────────────────────────────────────┤
│ Seit dem letzten Backup gab es keine Änderungen.       │
│                                                         │
│ Letztes Backup:  Heute, 02:00 Uhr                      │
│                                                         │
│ [Beenden ✓]                                             │
└─────────────────────────────────────────────────────────┘
```

**Fall 3: Automatischer Zeitplan aktiv → Exit-Backup deaktiviert**

```
Beenden ohne Rückfrage, da:
- Automatisches Backup ist konfiguriert (täglich 02:00 Uhr)
- Exit-Backup daher nicht nötig
```

#### **Logik-Flussdiagramm**

```
User klickt "Beenden"
    │
    ├─→ Automatischer Zeitplan aktiv?
    │   ├─→ JA: Sofort beenden (keine Rückfrage)
    │   └─→ NEIN: Weiter
    │
    ├─→ Exit-Backup aktiviert?
    │   ├─→ NEIN: Sofort beenden
    │   └─→ JA: Weiter
    │
    ├─→ Änderungen seit letztem Backup?
    │   ├─→ NEIN: Beenden (kurze Info: "Keine Änderungen")
    │   └─→ JA: Backup-Dialog anzeigen
    │
    └─→ Backup-Dialog
        ├─→ User wählt "Backup & Beenden"
        │   ├─→ Backup durchführen
        │   ├─→ Erfolgsmeldung
        │   └─→ Beenden
        │
        └─→ User wählt "Ohne Backup beenden"
            └─→ Sofort beenden (Risiko auf eigene Verantwortung)
```

#### **Implementierung**

```python
def on_exit():
    """
    Wird beim Beenden der Anwendung aufgerufen.
    """
    # 1. Prüfe: Automatischer Zeitplan aktiv?
    zeitplan_aktiv = db.execute("""
        SELECT COUNT(*) FROM backup_ziele
        WHERE zeitplan_aktiv = 1
    """).fetchone()[0] > 0

    if zeitplan_aktiv:
        # Automatisches Backup läuft → Exit-Backup nicht nötig
        sys.exit(0)

    # 2. Prüfe: Exit-Backup aktiviert?
    exit_backup_aktiv = db.execute("""
        SELECT backup_beim_beenden FROM einstellungen
    """).fetchone()[0]

    if not exit_backup_aktiv:
        # Exit-Backup deaktiviert → Beenden
        sys.exit(0)

    # 3. Prüfe: Änderungen seit letztem Backup?
    letztes_backup = db.execute("""
        SELECT MAX(erstellt_am) FROM backups
        WHERE status = 'erfolgreich'
    """).fetchone()[0]

    aenderungen = db.execute("""
        SELECT COUNT(*) FROM change_log
        WHERE geaendert_am > ?
    """, (letztes_backup,)).fetchone()[0]

    if aenderungen == 0:
        # Keine Änderungen → Beenden (mit kurzer Info)
        show_info_dialog("Keine Änderungen seit letztem Backup.")
        sys.exit(0)

    # 4. Änderungen vorhanden → Backup-Dialog anzeigen
    dialog = ExitBackupDialog(aenderungen_details={
        'anzahl_rechnungen': count_changes('rechnungen'),
        'anzahl_belege': count_changes('belege'),
        'anzahl_kunden': count_changes('kunden'),
        'letzte_aenderung': get_last_change_time(),
        'letztes_backup': letztes_backup
    })

    if dialog.show() == 'BACKUP':
        # User will Backup
        if perform_backup():
            show_success_dialog("Backup erfolgreich!")
            sys.exit(0)
        else:
            show_error_dialog("Backup fehlgeschlagen!")
            # User entscheiden lassen: trotzdem beenden?
            if show_question("Trotzdem beenden?"):
                sys.exit(0)
    else:
        # User will ohne Backup beenden
        sys.exit(0)
```

#### **Einstellungen: Exit-Backup konfigurieren**

```
┌─────────────────────────────────────────────────────────┐
│ ⚙️ Einstellungen → Backup                               │
├─────────────────────────────────────────────────────────┤
│ 💾 Backup beim Beenden                                  │
│                                                         │
│ ☑ Automatisches Backup beim Beenden (wenn Änderungen)  │
│                                                         │
│ ℹ️ Diese Option ist nur aktiv, wenn KEIN automatischer │
│    Zeitplan konfiguriert ist.                          │
│                                                         │
│ Vorteile:                                              │
│ • Sie vergessen nie ein Backup                         │
│ • Backup nur bei echten Änderungen                     │
│ • Beenden ist natürlicher Zeitpunkt                    │
│                                                         │
│ Nachteile:                                             │
│ • Beenden dauert etwas länger (~30 Sekunden)           │
│ • Bei großen Datenmengen kann es nerven                │
│                                                         │
│ Empfehlung:                                            │
│ Aktivieren Sie entweder:                               │
│ • Automatischen Zeitplan (täglich/wöchentlich) ODER    │
│ • Exit-Backup                                          │
│                                                         │
│ [Speichern]                                            │
└─────────────────────────────────────────────────────────┘
```

---

### **🔄 Restore (Wiederherstellung)**

#### **1. Vollständige Wiederherstellung**

**Szenario:** Festplatte defekt, Neuinstallation nötig

**Workflow:**
```
1. RechnungsFee neu installieren
2. Backup auswählen:
   ┌─────────────────────────────────────────────────────────┐
   │ 📥 Backup wiederherstellen                              │
   ├─────────────────────────────────────────────────────────┤
   │ Backup-Quelle:                                          │
   │ ● Externe Festplatte: /media/usb-backup                │
   │ ○ Netzlaufwerk: smb://nas.local/backups                │
   │ ○ Anderer Pfad: [Durchsuchen...]                       │
   │                                                         │
   │ Verfügbare Backups:                                     │
   │ ┌─────────────────────────────────────────────────┐     │
   │ │ ● 15.12.2025 02:00 - Vollbackup (2,3 GB)       │     │
   │ │ ○ 14.12.2025 02:00 - Inkrementell (15 MB)      │     │
   │ │ ○ 13.12.2025 02:00 - Inkrementell (22 MB)      │     │
   │ │ ○ 08.12.2025 02:00 - Vollbackup (2,2 GB)       │     │
   │ └─────────────────────────────────────────────────┘     │
   │                                                         │
   │ ⚠️ Warnung: Alle aktuellen Daten werden überschrieben! │
   │                                                         │
   │ [Abbrechen]                   [Wiederherstellen →]      │
   └─────────────────────────────────────────────────────────┘

3. Bei verschlüsseltem Backup: Passwort eingeben
4. Wiederherstellung (Fortschrittsbalken)
5. Fertig! RechnungsFee neu starten
```

#### **2. Einzelne Datei/Beleg wiederherstellen**

**Szenario:** Versehentlich gelöschtes PDF

**Workflow:**
```
1. Backup durchsuchen:
   ┌─────────────────────────────────────────────────────────┐
   │ 🔍 Backup durchsuchen                                   │
   ├─────────────────────────────────────────────────────────┤
   │ Suche nach:                                             │
   │ [Rechnung RE-2025-001]                    [Suchen]      │
   │                                                         │
   │ Gefunden in Backup vom 08.12.2025:                      │
   │ ┌─────────────────────────────────────────────────┐     │
   │ │ ☑ RE-2025-001.pdf (145 KB)                      │     │
   │ │ ☑ RE-2025-001.xrechnung.xml (12 KB)            │     │
   │ └─────────────────────────────────────────────────┘     │
   │                                                         │
   │ [Abbrechen]          [Exportieren...]  [Wiederherstellen│
   └─────────────────────────────────────────────────────────┘

2. Datei wiederherstellen oder an anderem Ort speichern
```

#### **3. Point-in-Time Recovery**

**Szenario:** "Wie sah meine Datenbank am 01.12. aus?"

**Workflow:**
```
1. Backup vom gewünschten Datum auswählen
2. In temporäres Verzeichnis entpacken
3. Datenbank im Read-Only-Modus öffnen
4. Daten prüfen/exportieren
5. Optional: Bestimmte Datensätze in aktuelle DB kopieren
```

---

### **🗄️ Datenbank-Schema für Backups**

```sql
-- Backup-Historie
CREATE TABLE backups (
    id INTEGER PRIMARY KEY,
    typ TEXT NOT NULL, -- 'full', 'incremental', 'differential'
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ziel TEXT NOT NULL, -- '/media/usb-backup', 'smb://nas.local/backups'
    ziel_typ TEXT NOT NULL, -- 'lokal', 'usb', 'netzwerk'

    -- Backup-Datei
    dateiname TEXT NOT NULL, -- 'full_2025-12-09_020000.tar.gz.enc'
    dateipfad TEXT NOT NULL, -- Vollständiger Pfad
    dateigroesse INTEGER, -- Bytes
    hash_sha256 TEXT, -- Integritätsprüfung

    -- Verschlüsselung (standardmäßig aktiviert!)
    verschluesselt BOOLEAN DEFAULT 1, -- Privacy by Default (DSGVO Art. 25)
    verschluesselungs_algorithmus TEXT DEFAULT 'AES-256-CBC',

    -- Metadaten
    software_version TEXT, -- RechnungsFee-Version
    datenbank_version INTEGER, -- Schema-Version
    anzahl_rechnungen INTEGER,
    anzahl_belege INTEGER,
    anzahl_kunden INTEGER,

    -- Status
    status TEXT DEFAULT 'erfolgreich', -- 'erfolgreich', 'fehler', 'abgebrochen'
    fehlermeldung TEXT,
    dauer_sekunden INTEGER,

    -- Aufbewahrung
    aufbewahren_bis DATE, -- NULL = permanent
    automatisch_geloescht BOOLEAN DEFAULT 0,

    -- Abhängigkeiten (für inkrementelle Backups)
    basiert_auf_backup_id INTEGER, -- NULL bei Vollbackup

    -- Exit-Backup
    exit_backup BOOLEAN DEFAULT 0, -- Wurde beim Beenden erstellt?

    CHECK (typ IN ('full', 'incremental', 'differential')),
    CHECK (ziel_typ IN ('lokal', 'usb', 'netzwerk', 'nas')),
    FOREIGN KEY (basiert_auf_backup_id) REFERENCES backups(id)
);

CREATE INDEX idx_backups_typ ON backups(typ);
CREATE INDEX idx_backups_datum ON backups(erstellt_am);
CREATE INDEX idx_backups_ziel ON backups(ziel_typ);

-- Backup-Ziele (mehrere möglich)
CREATE TABLE backup_ziele (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL, -- 'Primäres NAS', 'USB-Backup', etc.
    typ TEXT NOT NULL, -- 'lokal', 'usb', 'netzwerk', 'nas'
    pfad TEXT NOT NULL, -- '/media/usb-backup' oder 'smb://nas.local/backups'

    -- Authentifizierung (für Netzwerk)
    benutzer TEXT,
    passwort_keychain_id TEXT, -- Referenz zu System-Keychain

    -- Zeitplan
    zeitplan_aktiv BOOLEAN DEFAULT 0,
    zeitplan_typ TEXT, -- 'täglich', 'wöchentlich', 'monatlich'
    zeitplan_uhrzeit TEXT, -- '02:00'
    zeitplan_wochentag INTEGER, -- 0=Sonntag, 1=Montag, etc. (nur bei wöchentlich)

    -- Backup-Typ
    backup_typ TEXT DEFAULT 'full', -- 'full', 'incremental', 'differential'

    -- Verschlüsselung
    verschluesselt BOOLEAN DEFAULT 1,
    passwort_keychain_id_backup TEXT, -- Backup-Verschlüsselungspasswort

    -- Status
    aktiv BOOLEAN DEFAULT 1,
    letztes_backup TIMESTAMP,
    letzter_fehler TEXT,

    CHECK (typ IN ('lokal', 'usb', 'netzwerk', 'nas')),
    CHECK (backup_typ IN ('full', 'incremental', 'differential'))
);

-- Change Tracking (für Exit-Backup)
CREATE TABLE change_log (
    id INTEGER PRIMARY KEY,
    tabelle TEXT NOT NULL, -- 'rechnungen', 'belege', 'kunden', etc.
    aktion TEXT NOT NULL, -- 'insert', 'update', 'delete'
    datensatz_id INTEGER,
    geaendert_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CHECK (aktion IN ('insert', 'update', 'delete'))
);

CREATE INDEX idx_change_log_datum ON change_log(geaendert_am);
CREATE INDEX idx_change_log_tabelle ON change_log(tabelle);

-- View: Änderungen seit letztem Backup
CREATE VIEW hat_aenderungen AS
SELECT
    COUNT(*) AS anzahl_aenderungen,
    MAX(geaendert_am) AS letzte_aenderung
FROM change_log
WHERE geaendert_am > (
    SELECT COALESCE(MAX(erstellt_am), '1970-01-01')
    FROM backups
    WHERE status = 'erfolgreich'
);

-- Einstellungen (Erweiterung)
-- ALTER TABLE einstellungen ADD COLUMN backup_beim_beenden BOOLEAN DEFAULT 1;
-- (Diese Spalte wird zur bestehenden einstellungen-Tabelle hinzugefügt)
```

---

### **📋 MVP-Umfang für Kategorie 10.1 (Backup)**

#### **Phase 1 (v1.0 - MVP):**

**Backup-Ziele:**
- ✅ Lokales Verzeichnis
- ✅ Externe Festplatte / USB
- ✅ Netzlaufwerk (SMB/CIFS)
- ✅ Mehrere Ziele parallel (bis zu 3)

**Backup-Strategien:**
- ✅ Vollbackup
- ⏸️ Inkrementelles Backup - optional (v1.1, wenn Zeit)
- ❌ Differentielles Backup - v1.1

**Features:**
- ✅ Manuelles Backup (On-Demand)
- ✅ Automatisches Backup (Zeitplan)
- ✅ **Exit-Backup** (Backup beim Beenden, wenn Änderungen) ⭐ NEU
- ✅ **Change-Tracking** (automatische Änderungserkennung) ⭐ NEU
- ✅ **Verschlüsselung STANDARD** (AES-256, opt-out mit Warnung) ⭐
- ✅ Passwort in System-Keychain (automatisch)
- ✅ Passwort-Generator (sichere Passwörter)
- ✅ Backup vor Software-Update (automatisch, Pflicht)
- ✅ Vollständige Wiederherstellung
- ⏸️ Einzeldatei-Wiederherstellung - optional (v1.1)

**Cloud-Backup:**
- ❌ **NICHT in v1.0** - zurückgestellt auf v2.0

#### **Phase 2 (v1.1):**
- Inkrementelles/Differentielles Backup
- Einzeldatei-Wiederherstellung (Backup-Browser)
- Backup-Verifizierung (Hash-Check)
- Backup-Rotation automatisch
- Backup-Benachrichtigungen (E-Mail bei Fehler)

#### **Phase 3 (v2.0):**
- Cloud-Backup (S3-kompatibel: AWS, Backblaze B2, Wasabi)
- WebDAV (Nextcloud, ownCloud)
- SFTP/SCP
- Backup-Verschlüsselung mit GPG (zusätzlich zu AES)
- Deduplizierung (nur geänderte Blöcke speichern)

---

### **✅ Status: Kategorie 10.1 - Backup vollständig geklärt**

**Wichtigste Entscheidungen:**

1. ✅ **Lokale Backups für v1.0** (keine Cloud-Abhängigkeit)
2. ✅ **Mehrere Backup-Ziele parallel** (3-2-1-Regel)
3. ✅ **Vollbackup + optional Inkrementell** (v1.0/v1.1)
4. ✅ **Verschlüsselung STANDARDMÄSSIG AKTIVIERT** ⭐
   - AES-256 mit PBKDF2 (100.000 Iterationen)
   - Privacy by Default (DSGVO Art. 25)
   - Deaktivierung möglich (opt-out mit Warnung)
   - Passwort in System-Keychain
5. ✅ **Automatischer Backup-Zeitplan** (täglich/wöchentlich)
6. ✅ **Exit-Backup beim Beenden** (wenn keine Zeitplanung aktiv) ⭐ NEU
   - Nur wenn Änderungen seit letztem Backup
   - Change-Tracking mit automatischen Triggers
   - Benutzerfreundliche Backup-Dialoge
   - Kann deaktiviert werden
7. ✅ **Backup vor Update** (Pflicht, automatisch)
8. ⏸️ **Cloud-Backup** → v2.0

**Backup-Ziele:**
- Lokales Verzeichnis
- Externe Festplatte
- NAS/Netzlaufwerk (SMB/CIFS)
- Lokale Freigaben (anderer PC)

**DSGVO-Konformität:** ⭐
- **Art. 32 DSGVO:** Verschlüsselung als technische Schutzmaßnahme
- **Art. 34 Abs. 3 DSGVO:** Bei Verschlüsselung KEINE Meldepflicht bei Verlust
- **Art. 25 DSGVO:** Privacy by Default (Verschlüsselung standardmäßig aktiv)
- SHA256-Hash für Integrität
- Unveränderbare Backups
- Vollständige Aufzeichnung (Metadaten)

---

## **Kategorie 10.2: Software-Updates**

### **Update-Strategie**

**Grundprinzip:** Sicher, automatisch, mit Backup-Absicherung

### **🔄 Update-Mechanismen**

#### **1. Auto-Update (Standard)**

**Desktop-App (Electron/Tauri):**
- Eingebauter Auto-Updater (z.B. `electron-updater`, `tauri-plugin-updater`)
- Prüft beim Start auf neue Versionen
- Download im Hintergrund
- Installation beim nächsten Neustart

**Workflow:**
```
1. RechnungsFee startet
   ↓
2. Prüft: Neue Version verfügbar?
   ↓ JA
3. 🔔 "Update verfügbar: v1.2.0 → v1.3.0"
   ┌─────────────────────────────────────────┐
   │ 🎉 Update verfügbar!                    │
   ├─────────────────────────────────────────┤
   │ Version 1.3.0 ist verfügbar.           │
   │                                         │
   │ Neue Features:                          │
   │ • Verbesserte UStVA-Prüfung             │
   │ • Schnellerer DATEV-Export              │
   │ • Bugfixes für Kassenbuch               │
   │                                         │
   │ Größe: 45 MB                            │
   │                                         │
   │ ☑ Automatisch beim Beenden installieren│
   │                                         │
   │ [Später]  [Jetzt herunterladen]         │
   └─────────────────────────────────────────┘
   ↓
4. Download im Hintergrund (Progress-Bar)
   ↓
5. User beendet RechnungsFee
   ↓
6. **AUTOMATISCHES BACKUP VOR UPDATE** ⭐
   ┌─────────────────────────────────────────┐
   │ 💾 Backup vor Update (Pflicht)          │
   ├─────────────────────────────────────────┤
   │ Vor dem Update wird automatisch ein    │
   │ Backup erstellt. Dies ist verpflichtend│
   │ und kann nicht übersprungen werden.    │
   │                                         │
   │ ████████████████████░░░░ 80%            │
   │                                         │
   │ Erstelle Backup...                      │
   └─────────────────────────────────────────┘
   ↓
7. Update installieren
   ↓
8. RechnungsFee automatisch neu starten
   ↓
9. ✅ Update erfolgreich!
   "Willkommen bei RechnungsFee v1.3.0!"
```

#### **2. Manuelle Updates**

**Für Power-User / Docker:**
```bash
# Docker
docker pull rechnungspilot/rechnungspilot:latest
docker-compose down
docker-compose up -d

# AppImage
wget https://github.com/rechnungspilot/releases/latest/RechnungsFee.AppImage
chmod +x RechnungsFee.AppImage
./RechnungsFee.AppImage
```

#### **3. Update-Kanäle**

**Verfügbare Kanäle:**

| Kanal | Beschreibung | Zielgruppe | Stabilität |
|-------|--------------|------------|------------|
| **Stable** | Produktiv-Release | Alle User | ⭐⭐⭐⭐⭐ |
| **Beta** | Vorab-Test | Early Adopters | ⭐⭐⭐⭐ |
| **Nightly** | Tägliche Builds | Entwickler | ⭐⭐ |

**Einstellung:**
```
┌─────────────────────────────────────────┐
│ ⚙️ Einstellungen → Updates              │
├─────────────────────────────────────────┤
│ Update-Kanal:                           │
│ ● Stable (empfohlen)                    │
│ ○ Beta (für Early Adopters)             │
│ ○ Nightly (nur für Entwickler)          │
│                                         │
│ ☑ Automatisch nach Updates suchen      │
│ ☑ Updates automatisch herunterladen    │
│ ☑ Backup vor Update (Pflicht) ✅        │
│                                         │
│ Letzte Prüfung: Heute, 10:30 Uhr       │
│ Installierte Version: 1.2.5             │
│                                         │
│ [Jetzt nach Updates suchen]             │
└─────────────────────────────────────────┘
```

### **🛡️ Update-Sicherheit**

#### **1. Backup vor Update (PFLICHT)**

**Siehe Kategorie 10.1 - Backup:**
- Automatisches Backup IMMER vor Update
- Kann NICHT übersprungen werden
- Bei Backup-Fehler → Update wird abgebrochen
- Backup-Typ: Vollbackup (nicht inkrementell)

```python
def perform_update():
    """
    Update-Prozess mit obligatorischem Backup.
    """
    # 1. Backup erzwingen
    backup_erfolg = create_mandatory_backup(typ='vor_update')

    if not backup_erfolg:
        show_error("Update abgebrochen: Backup fehlgeschlagen!")
        return False

    # 2. Datenbank-Migration (falls nötig)
    if needs_migration():
        migrate_database()

    # 3. Update installieren
    install_update()

    # 4. Verifizierung
    if verify_update():
        return True
    else:
        # Rollback auf Backup
        restore_backup(backup_id=last_backup_before_update)
        return False
```

#### **2. Signierte Updates**

**Code Signing:**
- Alle Updates digital signiert
- Verhindert Man-in-the-Middle-Attacks
- Electron Auto-Updater prüft Signatur automatisch

```javascript
// electron-updater Konfiguration
{
  "publish": {
    "provider": "github",
    "owner": "rechnungspilot",
    "repo": "rechnungspilot"
  },
  "verifyUpdateCodeSignature": true  // ✅ Signaturprüfung
}
```

#### **3. Rollback-Funktion**

**Falls Update fehlschlägt:**

```
┌─────────────────────────────────────────┐
│ ⚠️ Update fehlgeschlagen                │
├─────────────────────────────────────────┤
│ Das Update konnte nicht installiert     │
│ werden.                                  │
│                                         │
│ Möchtest du auf die vorherige Version  │
│ zurückkehren? (Backup vom 09.12.2025)  │
│                                         │
│ [Abbrechen]  [Auf v1.2.5 zurückkehren] │
└─────────────────────────────────────────┘
```

### **📋 MVP-Umfang für Kategorie 10.2 (Update)**

#### **Phase 1 (v1.0):**
- ✅ **Auto-Update** (Electron/Tauri built-in)
- ✅ **Backup vor Update** (Pflicht, automatisch) - bereits in 10.1 geklärt
- ✅ **Update-Benachrichtigung** (beim Start)
- ✅ **Signierte Updates** (Code Signing)
- ✅ **Stable-Kanal** (Produktiv-Releases)
- ✅ **Changelog anzeigen** (Was ist neu?)
- ✅ **Manuelle Update-Prüfung** (Button in Einstellungen)

#### **Phase 2 (v1.1):**
- Beta-Kanal (Early Access)
- Rollback-UI (zurück zur vorherigen Version)
- Update-Historie (welche Versionen wurden wann installiert)

#### **Phase 3 (v2.0):**
- Nightly-Kanal (tägliche Builds)
- Delta-Updates (nur Änderungen herunterladen, spart Bandbreite)
- Offline-Updates (Update-Paket manuell importieren)

### **🗄️ Datenbank-Schema für Updates**

```sql
-- Update-Historie
CREATE TABLE update_log (
    id INTEGER PRIMARY KEY,
    version_alt TEXT NOT NULL,        -- '1.2.5'
    version_neu TEXT NOT NULL,        -- '1.3.0'
    update_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Backup-Referenz
    backup_id INTEGER NOT NULL,       -- Backup vor Update

    -- Status
    status TEXT DEFAULT 'erfolgreich', -- 'erfolgreich', 'fehler', 'rollback'
    fehlermeldung TEXT,

    -- Metadaten
    update_kanal TEXT DEFAULT 'stable', -- 'stable', 'beta', 'nightly'
    groesse_mb REAL,
    dauer_sekunden INTEGER,

    CHECK (status IN ('erfolgreich', 'fehler', 'rollback')),
    CHECK (update_kanal IN ('stable', 'beta', 'nightly')),
    FOREIGN KEY (backup_id) REFERENCES backups(id)
);

CREATE INDEX idx_update_log_datum ON update_log(update_am);
```

### **✅ Status: Kategorie 10.2 - Update vollständig geklärt**

**Wichtigste Entscheidungen:**

1. ✅ **Auto-Update als Standard** (Electron/Tauri built-in)
2. ✅ **Backup vor Update PFLICHT** (siehe Kategorie 10.1) ⭐
3. ✅ **Signierte Updates** (Code Signing für Sicherheit)
4. ✅ **Stable-Kanal für v1.0** (Beta/Nightly später)
5. ✅ **Rollback-Funktion** (bei fehlgeschlagenem Update)
6. ✅ **Changelog-Anzeige** (Transparenz über Änderungen)

**Technische Umsetzung:**
- Desktop: `electron-updater` oder `tauri-plugin-updater`
- Docker: Docker Hub / GitHub Container Registry
- AppImage: GitHub Releases mit Auto-Updater

**Sicherheit:**
- Obligatorisches Backup vor jedem Update
- Code Signing (verhindert manipulierte Updates)
- Automatischer Rollback bei Fehler

---

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

## **🏢 Zielgruppe: Bilanzpflichtige Unternehmen (GmbH, UG, AG)**

### **Strategische Überlegung**

**Frage:** Soll RechnungsFee auch für **bilanzpflichtige Unternehmen** (Kapitalgesellschaften wie GmbH, UG, AG) nutzbar sein?

**Kontext:**
- RechnungsFee ist primär für **EÜR-Rechner** konzipiert (Einzelunternehmer, Freiberufler, GbR)
- Bilanzpflichtige Unternehmen sind nach **§238 HGB** zur doppelten Buchführung verpflichtet
- RechnungsFee bietet **keine doppelte Buchführung**
- ABER: RechnungsFee hat **DATEV-Export** und **UStVA-Modul**

### **✅ Use Case: RechnungsFee als Vorerfassungssystem**

**Workflow für GmbH/UG:**

```
┌─────────────────────────────────────────────────────────┐
│ RechnungsFee (Tagesgeschäft)                          │
├─────────────────────────────────────────────────────────┤
│ ✅ Eingangsrechnungen erfassen                          │
│ ✅ Ausgangsrechnungen erstellen                         │
│ ✅ Kassenbuch führen                                    │
│ ✅ Bank-CSV importieren                                 │
│ ✅ Kategorisierung (SKR03/SKR04)                        │
│ ✅ UStVA monatlich/quartalsweise                        │
└─────────────────────────────────────────────────────────┘
                         ↓
                    (Monatlich/Quartalsweise)
                         ↓
┌─────────────────────────────────────────────────────────┐
│ UStVA per ELSTER                                        │
│ (direkt aus RechnungsFee)                             │
└─────────────────────────────────────────────────────────┘
                         ↓
                    (Am Jahresende)
                         ↓
┌─────────────────────────────────────────────────────────┐
│ DATEV-Export an Steuerberater                           │
├─────────────────────────────────────────────────────────┤
│ 📦 Buchungsstapel (alle Belege kategorisiert)           │
│ 📦 Stammdaten (Kunden, Lieferanten, Kontenrahmen)       │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ Steuerberater erstellt in DATEV:                        │
├─────────────────────────────────────────────────────────┤
│ ✅ Doppelte Buchführung (Soll/Haben auf Konten)         │
│ ✅ Bilanz (Aktiva/Passiva nach §266 HGB)                │
│ ✅ GuV (Gewinn- und Verlustrechnung nach §275 HGB)      │
│ ✅ Jahresabschluss                                      │
│ ✅ Körperschaftsteuer-Erklärung                         │
│ ✅ Gewerbesteuer-Erklärung                              │
└─────────────────────────────────────────────────────────┘
```

**Rolle von RechnungsFee:**
- ✅ Belegverwaltungssystem mit Kategorisierung
- ✅ Vorerfassungssystem für Steuerberater
- ✅ UStVA-Modul (selbstständige Abgabe)
- ❌ KEINE doppelte Buchführung
- ❌ KEINE Bilanz-Erstellung
- ❌ KEINE GuV nach §275 HGB

### **📊 Steuerliche Einreichungen: Was ist gleich?**

| Einreichung | EÜR (Einzelunternehmer) | GmbH/UG | In RechnungsFee? |
|-------------|-------------------------|---------|-------------------|
| **UStVA** (monatlich/quartalsweise) | ✅ Pflicht | ✅ Pflicht | ✅ **JA** |
| **ZM** (Zusammenfassende Meldung) | ✅ bei EU-Geschäft | ✅ bei EU-Geschäft | ✅ **JA** (geplant) |
| **USt-Jahreserklärung** | ✅ Pflicht | ✅ Pflicht | ✅ **JA** |
| **Gewinnermittlung** | EÜR (Anlage EÜR) | Bilanz + GuV | ⚠️ **NEIN** (macht Steuerberater) |
| **Einkommensteuer** | ✅ Anlage G/S | ❌ Nicht für GmbH | ⏸️ Nicht relevant |
| **Körperschaftsteuer** | ❌ Nicht für Einzelunternehmer | ✅ Pflicht | ⚠️ **NEIN** (macht Steuerberater) |
| **Gewerbesteuer** | ✅ GewSt-Erklärung | ✅ GewSt-Erklärung | ⚠️ **NEIN** (macht Steuerberater) |
| **Jahresabschluss** | ❌ Nicht für EÜR-Rechner | ✅ Pflicht (§264 HGB) | ❌ **NEIN** (macht Steuerberater) |
| **E-Bilanz** | ❌ Nicht für EÜR-Rechner | ✅ Pflicht (§5b EStG) | ❌ **NEIN** (macht Steuerberater) |

**✅ Fazit:** Alle **laufenden steuerlichen Pflichten** (UStVA, ZM, USt-Jahreserklärung) sind **identisch**!

### **💡 Vorteile für RechnungsFee**

**1. Deutlich größerer Markt:**
- 🏢 **1,2 Millionen GmbHs** in Deutschland (Statistisches Bundesamt 2024)
- 🏢 **600.000 UGs** (Unternehmergesellschaften)
- 👨‍💼 **3,2 Millionen Einzelunternehmer** (ohne GmbH/UG)

→ **Markt verdoppelt sich fast!**

**2. Typisches Szenario:**
- Kleine GmbH/UG (1-5 Mitarbeiter)
- Geschäftsführer erfasst Belege selbst
- Steuerberater kommt 1× jährlich (Jahresabschluss)
- Monatliche UStVA wird selbst gemacht

→ **RechnungsFee spart Steuerberater-Kosten für laufende Buchhaltung!**

**3. Wenig zusätzlicher Entwicklungsaufwand:**
- ✅ DATEV-Export bereits geplant
- ✅ UStVA-Modul bereits geplant
- ✅ Kategorisierung mit SKR03/SKR04 bereits vorhanden
- ❌ KEINE zusätzliche Entwicklung für Bilanz nötig

**4. Klare Abgrenzung:**
- RechnungsFee = Vorerfassungssystem für Steuerberater
- DATEV = Finanzbuchhaltung & Jahresabschluss
- Keine Konkurrenz, sondern **Ergänzung**

### **⚠️ Herausforderungen & Unterschiede**

| Aspekt | EÜR-Rechner | Bilanzpflichtige GmbH | Lösung |
|--------|-------------|----------------------|--------|
| **Kontenrahmen** | SKR03 (bevorzugt) | SKR03 oder SKR04 | ✅ Beide bereits unterstützt |
| **Gewinnermittlung** | EÜR selbst erstellen | Bilanz vom Steuerberater | ✅ RechnungsFee nur Vorerfassung |
| **Anlagevermögen** | Vereinfacht (AfA-Liste) | Detailliert (Anlagenbuchhaltung) | ⚠️ Basis-AfA-Verwaltung reicht |
| **Abschreibungen** | Linear/Sofortabschreibung | Planmäßig/außerplanmäßig | ⚠️ In DATEV detailliert |
| **Kostenstellenrechnung** | Selten | Häufig | ⏸️ v2.0 Feature |
| **Rückstellungen** | Nicht vorhanden | Pflicht (§249 HGB) | ❌ Macht Steuerberater in DATEV |
| **Abgrenzungen** | Nicht vorhanden | Pflicht (§250 HGB) | ❌ Macht Steuerberater in DATEV |
| **Inventur** | Nicht vorhanden | Pflicht (§240 HGB) | ⏸️ v2.0 Feature (optional) |

**✅ Fazit:** Die meisten Unterschiede sind **NICHT relevant**, weil der Steuerberater die Bilanz in DATEV erstellt!

### **🎯 Positionierung**

**Marketing-Botschaft:**

> **RechnungsFee** – Die smarte Belegverwaltung für Einzelunternehmer und kleine GmbH/UG.
>
> ✅ Rechnungen schreiben & erfassen
> ✅ Belege kategorisieren & archivieren
> ✅ UStVA selbst abgeben
> ✅ DATEV-Export für Steuerberater
>
> **Für EÜR-Rechner:** Erstelle deine Einnahmen-Überschuss-Rechnung selbst.
> **Für GmbH/UG:** Exportiere deine Belege an deinen Steuerberater – spart Zeit und Geld!

**Zielgruppen:**
1. **Einzelunternehmer / Freiberufler** (primär)
   - Machen EÜR selbst oder mit Steuerberater
2. **Kleine GmbH/UG** (sekundär)
   - Erfassen Belege selbst, Jahresabschluss macht Steuerberater
3. **GbR** (Personengesellschaften)
   - Ähnlich wie Einzelunternehmer (EÜR-Berechtigt)

### **🛠️ Technische Umsetzung**

**Keine Änderungen nötig!**

Alle Features, die für **EÜR-Rechner** entwickelt werden, funktionieren auch für **GmbH/UG**:

✅ **Rechnungsstellung** – identisch
✅ **Belegerfassung** – identisch
✅ **Kategorisierung** – identisch (SKR03/SKR04)
✅ **UStVA** – identisch
✅ **DATEV-Export** – identisch
✅ **Bank-CSV-Import** – identisch

**Einzige Anpassung:**

Beim **Ersteinrichtungs-Assistenten** eine zusätzliche Frage:

```
┌────────────────────────────────────────────┐
│ Unternehmensform wählen:                   │
├────────────────────────────────────────────┤
│ ○ Einzelunternehmer / Freiberufler (EÜR)  │
│ ○ GbR (EÜR)                                │
│ ● GmbH / UG (Bilanzpflicht) ⭐             │
│ ○ AG / KG / OHG                            │
└────────────────────────────────────────────┘

⚠️ Hinweis bei GmbH/UG:
RechnungsFee erstellt KEINE Bilanz. Am Jahresende
exportierst du deine Belege per DATEV-Export an
deinen Steuerberater, der dann Bilanz und
Jahresabschluss in DATEV erstellt.

[ Weiter ]
```

**Datenbank-Änderung:**

```sql
ALTER TABLE firma ADD COLUMN unternehmensform TEXT DEFAULT 'einzelunternehmer';

-- Mögliche Werte:
-- 'einzelunternehmer', 'freiberufler', 'gbr', 'gmbh', 'ug', 'ag', 'kg', 'ohg'
```

**UI-Anpassung:**

In der **Startseite / Dashboard** für GmbH/UG:

```
┌────────────────────────────────────────┐
│ 📊 RechnungsFee - Dashboard          │
├────────────────────────────────────────┤
│ Unternehmensform: GmbH (Bilanzpflicht) │
│                                        │
│ ℹ️ Hinweis:                            │
│ Am Jahresende: DATEV-Export für       │
│ Steuerberater (Bilanz & Jahresabschluss)│
│                                        │
│ ✅ UStVA 11/2025 - Abgegeben           │
│ ⏸️ Nächste UStVA: 10.12.2025          │
│                                        │
│ [DATEV-Export erstellen]               │
└────────────────────────────────────────┘
```

### **📋 Rechtliche Absicherung**

**Disclaimer in Dokumentation & UI:**

> **Hinweis für bilanzpflichtige Unternehmen (GmbH, UG, AG):**
>
> RechnungsFee ist ein **Belegverwaltungssystem mit DATEV-Export-Funktion**.
> Es ersetzt KEINE professionelle Finanzbuchhaltungs-Software (z.B. DATEV, Lexware Pro).
>
> **Was RechnungsFee KANN:**
> - ✅ Rechnungen erstellen & verwalten
> - ✅ Belege erfassen & kategorisieren
> - ✅ UStVA selbst abgeben
> - ✅ DATEV-Export für Steuerberater
>
> **Was RechnungsFee NICHT KANN:**
> - ❌ Doppelte Buchführung (§238 HGB)
> - ❌ Bilanz erstellen (§266 HGB)
> - ❌ GuV nach §275 HGB
> - ❌ E-Bilanz (§5b EStG)
> - ❌ Jahresabschluss (§264 HGB)
>
> **Empfehlung:**
> Nutzen Sie RechnungsFee für das Tagesgeschäft und übergeben Sie am Jahresende
> per DATEV-Export alle Belege an Ihren Steuerberater, der dann Bilanz und
> Jahresabschluss in einer professionellen Fibu-Software (z.B. DATEV) erstellt.

### **✅ Entscheidung: JA, absolut sinnvoll!**

**Begründung:**

1. ✅ **Markt verdoppelt sich** (1,8 Mio. GmbH/UG zusätzlich)
2. ✅ **Alle steuerlichen Einreichungen sind gleich** (UStVA, ZM, USt-Jahr)
3. ✅ **Wenig Entwicklungsaufwand** (keine neuen Features nötig)
4. ✅ **Klarer Use Case** (Vorerfassungssystem für Steuerberater)
5. ✅ **Keine Konkurrenz zu DATEV** (Ergänzung, kein Ersatz)
6. ✅ **Rechtlich unbedenklich** (mit Disclaimer)

**Implementierung:**

- 🟢 **Phase 1 (MVP):** Bereits vollständig abgedeckt!
- 🟢 **Phase 2 (v1.1):** Unternehmensform-Auswahl + Disclaimer
- 🟢 **Phase 3 (v2.0):** Erweiterte Features (Kostenstellenrechnung, Inventur) optional

**Marketing-Strategie:**

- **Primäre Zielgruppe:** Einzelunternehmer / Freiberufler (EÜR)
- **Sekundäre Zielgruppe:** Kleine GmbH/UG (1-5 Mitarbeiter) mit Steuerberater

→ **Kein Mehraufwand, aber doppelter Markt!** 🚀

---

**Status:** ✅ **Strategische Entscheidung getroffen** - RechnungsFee wird auch für bilanzpflichtige Unternehmen (GmbH, UG, AG) positioniert als **Vorerfassungssystem mit DATEV-Export**. Alle steuerlichen Einreichungen (UStVA, ZM) sind identisch. Bilanz und Jahresabschluss macht der Steuerberater in DATEV.

---

## **💬 Community-Vorschläge & Feedback**

### **Vorschlag 1: LibreOffice-Rechnungsvorlagen mit ZUGFeRD-Platzhaltern**

**Quelle:** Community-Diskussion auf [forum.linuxguides.de](https://forum.linuxguides.de)
**Datum:** 2025-12-03

**Idee:**
- Rechnungsvorlagen für LibreOffice Writer/Calc bereitstellen
- Platzhalter nach ZUGFeRD-Richtlinien
- Integration mit RechnungsFee:
  - Daten aus RechnungsFee in Vorlage einfügen
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
  - RechnungsFee öffnet LibreOffice via CLI
  - Befüllt Platzhalter mit Daten
  - Export als PDF + ZUGFeRD-XML einbetten
  - Speichert in RechnungsFee

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
RechnungsFee/
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

### **2026-01-24 - Issue #13: Export-Funktionen für Nicht-DATEV-Software geprüft**
- Feature-Request analysiert: Export für Programme ohne DATEV-Import-Unterstützung
- Klarstellung: CAMT/OFX sind Bank-IMPORT-Formate, keine Buchhaltungs-EXPORT-Formate
- Feststellung: CSV-Exporte bereits umfangreich geplant (Kassenbuch, Rechnungen, Transaktionen, Stammdaten)
- Neues Feature konzipiert: Generisches Export-Template-System für v2.0
- Template-Editor für beliebige Buchhaltungssoftware (Lexware, WISO, sevdesk, etc.)
- Community-Templates via GitHub für schnelle Unterstützung neuer Software
- Spalten-Mapping-Tool für individuelle Anpassungen
- Dokumentiert in: discussion-issue-13-export.md, issue-13-comment.md
- Rückfragen an User gestellt: Welche konkrete Zielsoftware?

### **2026-01-24 - Postbank CSV-Format hinzugefügt**
- Postbank CSV-Vorlage anonymisiert und integriert
- Format-Spezifikation dokumentiert (18 Spalten, Soll/Haben-Trennung, umfangreiche Metadaten)
- README.md in vorlagen/bank-csv/ aktualisiert: Postbank als unterstützte Bank markiert
- Besonderheiten dokumentiert: Separate Soll/Haben-Spalten, Fremde Gebühren, detaillierte Kartenzahlungen mit Folgenummer und Verfalldatum
- Anonymisierung umfasste: IBANs, Personennamen, Kundennummern, Telefonnummern

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
- Mapping RechnungsFee → EKS definiert
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
