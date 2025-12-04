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
- **Tagesabschluss / Z-Bon:**
  - Nicht verpflichtend bei dieser Art der Kassenführung
  - Aber **empfohlen** und wird implementiert
  - Täglicher Abschluss mit Soll-Ist-Vergleich
- **Chronologische Liste** aller Bewegungen
- **Unveränderbarkeit (GoBD-Anforderung):**
  - Kassenbucheinträge sind nach Speicherung **unveränderbar**
  - Stornos und Änderungen werden als **neuer Eintrag** angelegt
  - Mit **Begründung protokolliert**
  - Verweis auf ursprünglichen Eintrag (Storno-Kette)

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

#### **Validierung:**

**Hybrid-System (Option C):**

**1. Validierung gegen offiziellen Standard:**
- XRechnung: Gegen XRechnung-Schema validieren
- ZUGFeRD: Gegen ZUGFeRD-Spezifikation validieren
- Zwei Fehler-Kategorien:
  - **Errors (kritisch):** Import blockiert
    - Korrupte XML-Struktur
    - Pflichtfelder fehlen (Rechnungsnummer, Betrag)
    - Nicht parsebar
  - **Warnings (unkritisch):** Import möglich mit Hinweis
    - Optionale Felder fehlen
    - Format-Abweichungen (aber lesbar)
    - Veraltete Schema-Version

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

### **Noch zu klären (siehe fragen.md):**

- Kategorie 4: DATEV-Export
- Kategorie 5: Bank-Integration
- Kategorie 6: UStVA (Details)
- Kategorie 7: EÜR
- Kategorie 8: Stammdaten-Erfassung
- Kategorie 9: Import-Schnittstellen
- Kategorie 10: Backup & Update
- Kategorie 11: Steuersätze
- Kategorie 12: Hilfe-System
- Kategorie 13: Scope & Priorisierung

---

## **💬 Community-Vorschläge & Feedback**

### **Vorschlag 1: LibreOffice-Rechnungsvorlagen mit ZUGFeRD-Platzhaltern**

**Quelle:** Community-Diskussion auf GitHub
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
  {{RECHNUNGSNUMMER}}
  {{DATUM}}
  {{KUNDE_NAME}}
  {{KUNDE_ADRESSE}}
  {{POSITIONEN}}
  {{NETTO_GESAMT}}
  {{UST_BETRAG}}
  {{BRUTTO_GESAMT}}
  {{ZAHLUNGSZIEL}}
  {{BANKVERBINDUNG}}
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
