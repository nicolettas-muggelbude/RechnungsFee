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
