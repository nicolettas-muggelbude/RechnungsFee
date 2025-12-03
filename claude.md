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
- **Manuelle Eingabe** mit Feldern:
  - Datum
  - Zahlungsart (Bank / Bar)
  - Beschreibung
  - Kategorie
  - Einnahme
  - Ausgabe
  - Summe

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
- **Kein Tagesabschluss** (kein POS, nur Mindestanforderung Buchführung)
- **Chronologische Liste** aller Bewegungen

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

### **Noch zu klären (siehe fragen.md):**

- Kategorie 2: PDF/E-Rechnungs-Import
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
