# RechnungsPilot - Claude Projektdokumentation

**Projekt:** RechnungsPilot
**Typ:** Open-Source Buchhaltungssoftware
**Zielgruppe:** Freiberufler, Selbstständige, Kleinunternehmer
**Lizenz:** AGPL-3.0
**Status:** Konzeptphase
**Letzte Aktualisierung:** 2025-12-03

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
  - Datum
  - Belegnr.
  - Beschreibung
  - **Einnahmen** (getrennt nach Zahlungsart):
    - Bar-Einnahmen
    - Karten-Einnahmen
    - Bank-Einnahmen
    - PayPal-Einnahmen
  - **Ausgaben** (getrennt nach Zahlungsart):
    - Bar-Ausgaben
    - Karten-Ausgaben
    - Bank-Ausgaben
    - PayPal-Ausgaben
  - Tagesendsumme Bar
  - Summe alle Einnahmen
  - Summe alle Ausgaben

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

### **Noch zu klären (siehe fragen.md):**

- Kategorie 3: Anlage EKS (Agentur für Arbeit)
- Kategorie 4: DATEV-Export
- Kategorie 5: Bank-Integration
- Kategorie 6: UStVA
- Kategorie 7: EÜR
- Kategorie 8: Stammdaten-Erfassung
- Kategorie 9: Import-Schnittstellen
- Kategorie 10: Backup & Update
- Kategorie 11: Steuersätze
- Kategorie 12: Hilfe-System
- Kategorie 13: Scope & Priorisierung

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

### **2025-12-03 - Projektstart**
- Initiales Projekt-Setup
- projekt.md analysiert
- fragen.md erstellt (Kategorien 2-13)
- claude.md angelegt
- Kategorie 1 (Kassenbuch) vollständig geklärt
- Technologie-Stack grob skizziert

---

## **Notizen**

- **EKS-Export** ist ein Alleinstellungsmerkmal - kaum andere Software bietet das
- **Zwei Versionen** (Desktop + Docker) erhöhen Komplexität, aber auch Reichweite
- **Tauri vs. Electron** - Tauri scheint besser zu passen (Größe, Performance)
- **Import-Schnittstellen** (hellocash, etc.) könnten Nutzerbasis vergrößern
- **Mobile PWA** ist nice-to-have, nicht kritisch für MVP

---

**Fortsetzung folgt nach Klärung der Kategorien 2-13...**
