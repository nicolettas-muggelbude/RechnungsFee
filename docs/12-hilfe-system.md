# Hilfe-System

**Kategorie 12: Hilfe & Support**

---

## **Übersicht**

RechnungsFee bietet ein mehrstufiges Hilfe-System, das sowohl Anfänger als auch erfahrene Nutzer optimal unterstützt.

**Grundprinzip:** Progressive Disclosure - von kurzen Quick-Tipps bis zu ausführlichen Erklärungen.

---

## **12.1 Umfang der Hilfe**

### **MVP (Version 1.0)**

#### **1. Tooltips überall** ✅

**Was:**
- An jedem Eingabefeld ein ❓-Icon
- Kurze Erklärung (1-2 Sätze)
- Technische Info: "Was ist dieses Feld?"

**Beispiel:**
```
[Steuernummer] ❓
    ↓ (Klick)
┌─────────────────────────────────┐
│ Deine Steuernummer vom Finanzamt│
│ Format: 12/345/67890            │
└─────────────────────────────────┘
```

**Format:**
- Technisch & prägnant
- Beispiele wo sinnvoll
- Keine Fachbegriff-Erklärungen (dafür: expandierbar)

---

#### **2. Kontextsensitive Hilfe für 3 komplexe Bereiche** ✅

**Wo:**
1. **Ersteinrichtung** (Setup-Assistent)
2. **UStVA erstellen** (Umsatzsteuervoranmeldung)
3. **EÜR erstellen** (Einnahmenüberschussrechnung)

**Format:**
- Sidebar oder Modal mit ausführlichem Text
- Schrittweise Erklärungen
- Screenshots/Diagramme
- Links zu PDF-Handbuch

**Beispiel - UStVA-Hilfe:**
```
┌─────────────────────┬────────────────────────────┐
│ UStVA erstellen     │  ℹ️ Hilfe                   │
│                     │  ─────────────────────────│
│ Zeitraum: [Q1/2025]│  Umsatzsteuervoranmeldung  │
│                     │                           │
│ Kennziffer 81:      │  **Was ist die UStVA?**   │
│ [_________] €       │  Die UStVA ist eine...    │
│                     │                           │
│ Kennziffer 86:      │  **Kennziffer 81:**       │
│ [_________] €       │  Umsätze zu 19%...        │
│                     │                           │
│ [Erstellen]         │  [Mehr im Handbuch →]     │
└─────────────────────┴────────────────────────────┘
```

---

#### **3. PDF-Handbuch** ✅

**Umfang:**
- Vollständige Benutzer-Dokumentation
- Schritt-für-Schritt-Anleitungen
- Screenshots
- FAQ
- Steuer-Grundlagen (EÜR, UStVA, §19 UStG erklärt)

**Zugriff:**
- Menü → Hilfe → Handbuch herunterladen
- Link in Kontexthilfe: "Mehr im Handbuch →"

**Format:** PDF (durchsuchbar)

---

### **Prio 2 (nach MVP)**

#### **Interaktive Touren** ⏳

**Was:**
- Onboarding-Tutorial bei Erstnutzung
- Geführte Tour durch Hauptfunktionen
- Mit "Nicht wieder anzeigen"-Option
- Später in Einstellungen reaktivierbar

**Tool-Vorschlag:** Shepherd.js, Intro.js, oder ähnlich

**Ablauf:**
```
1. Willkommen bei RechnungsFee!
   ↓
2. Hier erfasst du Rechnungen
   ↓
3. Das ist dein Kassenbuch
   ↓
4. Hier erstellst du UStVA
   ↓
5. Fertig! Du kannst jederzeit hier nachschauen: [Hilfe]
```

#### **Kontexthilfe für restliche Bereiche** ⏳

- Kassenbuch
- Rechnungserfassung
- Stammdaten
- Backup-Einstellungen
- etc.

---

### **Später (Version 1.x)**

- 🎥 **Video-Tutorials** (YouTube oder eingebettet)
- 📚 **Markdown Wiki** (z.B. GitHub Wiki)

---

## **12.2 Hilfe-Inhalte: Technisch + Fachlich**

### **Konzept: Progressive Disclosure**

**Stufe 1 - Immer sichtbar (Tooltip):**
```
Kurze technische Info (1-2 Sätze)
```

**Stufe 2 - Expandierbar (bei Bedarf):**
```
[▼ Was bedeutet das genau?]
    ├─ Fachliche Erklärung
    ├─ Vor-/Nachteile
    └─ Beispiele
```

**Stufe 3 - Deep Dive (optional):**
```
[Ausführlich im Handbuch →]
```

---

### **Beispiel:**

#### **Stufe 1 (Standard):**
```
[§19 UStG (Kleinunternehmer)] ❓
         ↓
┌─────────────────────────────────────────────┐
│ Aktiviere diese Option, wenn dein          │
│ Jahresumsatz unter 25.000€ liegt.          │
│                                             │
│ [▼ Was bedeutet das genau?]                │
└─────────────────────────────────────────────┘
```

#### **Stufe 2 (Expandiert):**
```
┌─────────────────────────────────────────────┐
│ Aktiviere diese Option, wenn dein          │
│ Jahresumsatz unter 25.000€ liegt.          │
│                                             │
│ [▲ Was bedeutet das genau?]                │
│ ─────────────────────────────────────────   │
│ § 19 UStG befreit dich von der Umsatz-     │
│ steuer. Du darfst dann keine USt auf       │
│ Rechnungen ausweisen, kannst aber auch     │
│ keine Vorsteuer geltend machen.            │
│                                             │
│ ✅ Vorteile:                                │
│ • Weniger Bürokratie                       │
│ • Keine UStVA-Pflicht                      │
│                                             │
│ ❌ Nachteile:                               │
│ • Keine Vorsteuer-Erstattung               │
│ • Wirkt weniger professionell              │
│                                             │
│ [Ausführlich im Handbuch →]                │
└─────────────────────────────────────────────┘
```

---

### **Implementierungs-Phasen:**

**Phase 1 (MVP):**
- Nur Stufe 1 (kurze Tooltips)

**Phase 1.5:**
- Expand-Funktion hinzufügen (Stufe 2)

**Phase 2:**
- Links zu PDF-Handbuch (Stufe 3)

---

## **12.3 Steuerberatungs-Disclaimer**

### **Platzierung: Kombination**

#### **1. Bei Ersteinrichtung** ⚠️

**Wann:** Beim allerersten Start der App

**Format:** Modal-Dialog, kann nicht übersprungen werden

```
┌─────────────────────────────────────────┐
│ ⚠️ Wichtiger Hinweis                    │
│ ═════════════════════════════════════   │
│                                         │
│ RechnungsFee ist ein Software-Tool zur │
│ Vereinfachung deiner Buchhaltung.      │
│                                         │
│ ❌ Keine Steuerberatung                │
│ Diese Software ersetzt keine           │
│ professionelle Steuerberatung.          │
│                                         │
│ ⚠️ Bei Unsicherheit                     │
│ Konsultiere bei steuerlichen Fragen    │
│ einen Steuerberater oder das Finanzamt.│
│                                         │
│ 🔒 Haftungsausschluss                   │
│ Wir übernehmen keine Haftung für die   │
│ Korrektheit der generierten Daten.     │
│                                         │
│ [✓] Ich habe verstanden               │
│                                         │
│ [Weiter zur Einrichtung]                │
└─────────────────────────────────────────┘
```

**Speichern:** User-Einstellung (disclaimer_accepted = true)

---

#### **2. Im Footer** 📄

**Wo:** Auf jeder Seite der App, dauerhaft sichtbar

**Format:** Kleine Text-Zeile

```
────────────────────────────────────────────────
ℹ️ Keine Steuerberatung | 📚 Ressourcen | Impressum | Datenschutz
```

**Klick auf "Keine Steuerberatung":**
- Zeigt den ausführlichen Disclaimer nochmal an

---

#### **3. In Exporten** 📑

**Wo:** In allen generierten PDF-Dokumenten

**Formate:**
- EÜR-PDF
- UStVA-Vorschau-PDF
- Berichte

**Format:** Fußnote auf letzter Seite

```
─────────────────────────────────────────────────────
⚠️ Hinweis:
Dieses Dokument wurde mit RechnungsFee (Version 1.0.0) erstellt.
RechnungsFee ist ein Software-Tool und ersetzt keine professionelle
Steuerberatung. Bei steuerlichen Fragen konsultiere bitte einen
Steuerberater oder das Finanzamt.

Keine Haftung für die Korrektheit der Angaben.
─────────────────────────────────────────────────────
```

---

### **Offizielle Quellen: Beides**

#### **1. In Kontexthilfe** 🔗

**Wo:** Direkt bei relevantem Feld/Thema

**Beispiel - §19 UStG:**
```
[§19 UStG] ❓
    ↓
┌─────────────────────────────────────┐
│ Kleinunternehmer-Regelung           │
│ ...Erklärung...                     │
│                                     │
│ 🔗 Offizielle Quellen:              │
│ • BMF: Kleinunternehmer-Merkblatt   │
│   (PDF öffnen)                      │
│ • § 19 UStG Gesetzestext            │
│   (gesetze-im-internet.de)          │
└─────────────────────────────────────┘
```

---

#### **2. Menüpunkt "Ressourcen"** 📚

**Navigation:**
```
Menü → Hilfe → Ressourcen & Links
```

**Inhalt:**
```
┌─────────────────────────────────────────┐
│ 📚 Ressourcen & offizielle Links        │
│ ═════════════════════════════════════   │
│                                         │
│ 🏛️ Bundesministerium der Finanzen (BMF)│
│ ├─ Kleinunternehmer-Merkblatt         │
│ ├─ EÜR-Anleitung                      │
│ └─ UStVA-Ausfüllhilfe                 │
│                                         │
│ 🏢 ELSTER                               │
│ ├─ ElsterOnline-Portal                │
│ ├─ Formulare herunterladen            │
│ └─ Hilfe & FAQ                        │
│                                         │
│ 🏛️ Bundesagentur für Arbeit            │
│ ├─ Anlage EKS                         │
│ └─ Hinweise für Selbstständige        │
│                                         │
│ 📖 Gesetzestexte                        │
│ ├─ UStG (Umsatzsteuergesetz)          │
│ ├─ EStG (Einkommensteuergesetz)       │
│ └─ GoBD (Grundsätze ord. Buchführung) │
│                                         │
│ 🔍 Finanzamt-Finder                     │
│ └─ Dein zuständiges Finanzamt finden  │
└─────────────────────────────────────────┘
```

**Alle Links öffnen im Browser** (externe Websites)

---

## **12.4 Community & Support**

### **Support-Struktur**

```
┌─────────────────────────────────────────┐
│ ❓ Hilfe & Support                      │
│ ─────────────────────────────────────   │
│                                         │
│ 📚 FAQ                                  │
│    Häufig gestellte Fragen              │
│    → GitHub Wiki (vorerst)             │
│                                         │
│ 🐛 Bug melden                           │
│    Problem gefunden?                    │
│    → GitHub Issues                      │
│                                         │
│ 💡 Feature vorschlagen                  │
│    Idee für neue Funktion?             │
│    → GitHub Discussions                 │
│                                         │
│ 💬 Community-Forum                      │
│    Austausch mit anderen Nutzern       │
│    → GitHub Discussions                 │
│                                         │
│ ─────────────────────────────────────   │
│ Kritische Anliegen:                     │
│                                         │
│ 🔐 Sicherheitslücke melden              │
│    → security@rechnungsfee.de           │
│                                         │
│ 🛡️ Datenschutz-Anfrage (DSGVO)         │
│    → privacy@rechnungsfee.de            │
│                                         │
└─────────────────────────────────────────┘
```

---

### **1. Community-Forum**

**Plattform:** GitHub Discussions (vorerst)

**Kategorien:**
- 💬 **Allgemein** - Austausch & Smalltalk
- 💡 **Ideen** - Feature Requests
- ❓ **Fragen** - Nutzungsfragen
- 📢 **Ankündigungen** - Updates & Releases
- 🎓 **Tutorials** - Community-Guides

**URL:** `https://github.com/nicolettas-muggelbude/RechnungsFee/discussions`

**Moderation:** Community-driven, minimale Moderation

---

### **2. FAQ-Bereich**

**Phasen:**

**Phase 1 (MVP):**
- GitHub Wiki oder Discussions-Pinned-Post
- 10-15 wichtigste FAQs

**Phase 2:**
- In der App integriert (Menü → Hilfe → FAQ)
- Die 10 wichtigsten FAQs direkt in der App
- Link zu vollständiger FAQ online

**Kategorien:**
- 🔧 Installation & Setup
- 💰 Steuer-Fragen (Disclaimer!)
- 🏦 Bank-Import
- 📊 Berichte & Exporte
- 🔐 Backup & Sicherheit

---

### **3. Bug-Reports**

**Plattform:** GitHub Issues

**Template:** Issue-Template bereitstellen

```markdown
---
name: Bug Report
about: Melde einen Fehler
---

## Beschreibung
[Was ist passiert?]

## Schritte zum Reproduzieren
1.
2.
3.

## Erwartetes Verhalten
[Was sollte passieren?]

## Screenshots
[Falls hilfreich]

## System
- OS: [z.B. Windows 11, macOS 14]
- RechnungsFee Version: [z.B. 1.0.2]
- Browser (falls Web): [z.B. Chrome 120]
```

---

### **4. E-Mail-Support (nur kritisch)**

#### **security@rechnungsfee.de** 🔐

**Zweck:** Sicherheitslücken melden (Responsible Disclosure)

**Antwortzeit:** < 48 Stunden

**Security Policy:** `.github/SECURITY.md` anlegen

```markdown
# Security Policy

## Reporting a Vulnerability

Wenn du eine Sicherheitslücke in RechnungsFee entdeckst,
melde sie bitte an:

📧 **security@rechnungsfee.de**

⚠️ Bitte KEINE öffentlichen GitHub Issues für Sicherheitsprobleme!

Wir antworten innerhalb von 48 Stunden und arbeiten mit dir
zusammen, um das Problem zeitnah zu beheben.

## Unterstützte Versionen

| Version | Unterstützt         |
| ------- | ------------------- |
| 1.x.x   | ✅                  |
| < 1.0   | ❌                  |
```

---

#### **privacy@rechnungsfee.de** 🛡️

**Zweck:** DSGVO-Anfragen (Art. 15-21)

- Auskunft über gespeicherte Daten
- Löschung von Daten
- Berichtigung von Daten
- Datenexport

**Antwortzeit:** < 30 Tage (gesetzlich)

**Format:** Standardisiertes Formular bereitstellen

---

#### **Optional später: contact@rechnungsfee.de**

**Zweck:** Alles andere
- Presse-Anfragen
- Kooperationen
- Rechtliches (außer Sicherheit/Datenschutz)

---

## **12.5 Sprache**

### **MVP (Version 1.0)**

**Nur Deutsch** 🇩🇪

**Begründung:**
- Fokus auf deutschen Markt
- Deutsche Steuervorschriften
- Schnellerer MVP
- Einfachere Wartung

**Umfang:**
- Komplette UI auf Deutsch
- Tooltips & Hilfen auf Deutsch
- PDF-Handbuch auf Deutsch
- Dokumentation auf Deutsch

---

### **Später (Version 1.1+)**

**Englisch hinzufügen** 🇬🇧

**Vorbereitung schon im MVP:**
- I18n-Framework einbauen (z.B. react-i18next)
- Alle Texte als Keys speichern (nicht hardcoded)
- Sprachauswahl-Mechanismus vorbereiten

**Herausforderung:**
- Steuerlogik bleibt deutsch-spezifisch
- Englische UI kann verwirren ("Why is this using German tax law?")

**Lösung:**
- Disclaimer in englischer Version:
  "This software is designed for German tax law only"

---

### **Weitere Sprachen (später)**

**Potenzial:**
- 🇫🇷 Französisch (Frankreich hat ähnliche Selbstständigen-Kultur)
- 🇪🇸 Spanisch
- 🇮🇹 Italienisch

**Aber:** Erfordert länderspezifische Steuerlogik!

---

## **Zusammenfassung**

| Bereich | MVP | Prio 2 | Später |
|---------|-----|--------|--------|
| **Tooltips** | ✅ Überall | - | - |
| **Kontexthilfe** | ✅ 3 Bereiche | ⏳ Alle | - |
| **PDF-Handbuch** | ✅ | - | - |
| **Interaktive Touren** | - | ⏳ | - |
| **Video-Tutorials** | - | - | 🔮 |
| **Wiki** | - | - | 🔮 |
| **Progressive Disclosure** | ⏳ Stufe 1 | ✅ Stufen 2+3 | - |
| **Disclaimer** | ✅ | - | - |
| **Offizielle Links** | ✅ | - | - |
| **Community** | ✅ GitHub | - | 🔮 Forum? |
| **FAQ** | ✅ GitHub | ⏳ In App | - |
| **E-Mail Security** | ✅ | - | - |
| **E-Mail Privacy** | ✅ | - | - |
| **Sprache DE** | ✅ | - | - |
| **Sprache EN** | - | - | 🔮 v1.1+ |

---

**Letzte Aktualisierung:** 2025-12-12
**Status:** ✅ Vollständig geklärt
