# Issue #13: Export-Funktion für Nicht-DATEV-Programme

**Datum:** 2026-01-24
**Issue:** https://github.com/user/repo/issues/13
**Status:** In Prüfung

---

## 📋 Zusammenfassung

**Feature-Request von @diddi04:**
- Export-Funktion für Programme ohne DATEV-Import-Unterstützung
- Weiterverarbeitung in Tabellenkalkulation
- Umstiegshilfe auf andere Buchhaltungsprogramme
- Vorgeschlagene Formate: CSV, CAMT, OFX

**Priorität (User):** Nice-to-have
**Bereich:** Export/Import

---

## 🔍 Analyse & Bewertung

### **1. Ist-Zustand: Bereits geplante Export-Funktionen**

RechnungsFee hat **bereits umfangreiche Export-Funktionen** geplant:

#### **✅ Steuer-Exporte (v1.0 MVP):**
- **DATEV-Export** - CSV (SKR03/SKR04) für Steuerberater
- **UStVA-Export** - CSV + XML für ELSTER
- **EÜR-Export** - CSV + PDF + ELSTER-XML
- **EKS-Export** - CSV/Excel/PDF für Jobcenter (Alleinstellungsmerkmal!)

#### **✅ Daten-Exporte (v1.0 MVP):**
- **Kassenbuch** - CSV
- **Eingangsrechnungen** - CSV/PDF
- **Ausgangsrechnungen** - CSV/PDF
- **Bank-Transaktionen** - CSV
- **Kundenstamm** - CSV/Excel
- **Belege (Batch)** - PDF/ZIP

#### **📋 Geplante Exporte (v1.1+):**
- **AGENDA-Export** - DATEV-CSV + Belegbilder-ZIP (für AGENDA Steuerberatersoftware)
- **Produktstamm** - CSV/Excel
- **Lieferantenstamm** - CSV/Excel
- **Erweiterte Berichte** - Excel mit Diagrammen

#### **🔮 Zukünftig (v2.0):**
- **Generisches Template-System** - für beliebige Buchhaltungssoftware
- **Community-Templates** - für Lexware, WISO, sevdesk, etc.
- **JSON-Export** - für API-Integrationen

---

### **2. Analyse der vorgeschlagenen Formate**

#### **CSV ✅ Bereits vorhanden/geplant**
- **Status:** Umfangreich geplant für alle Module
- **Zweck:** Tabellenverarbeitung (Excel, Google Sheets, LibreOffice Calc)
- **Struktur:** Datum, Beschreibung, Betrag, Kategorie, Konto, Steuer
- **Verwendung:** Universell importierbar in jede Software

#### **CAMT ❌ Missverständnis**
- **Was ist CAMT?** ISO 20022 XML-Format für **Bank-Kontoauszüge** (camt.053)
- **Zweck:** **IMPORT** von Bank-Daten ins Buchhaltungsprogramm
- **Richtung:** Bank → RechnungsFee (NICHT RechnungsFee → andere Software!)
- **Fazit:** CAMT ist ein **Import-Format**, kein Export-Format für Buchhaltungsdaten

**Klarstellung:**
- CAMT.053 = Kontoauszüge von der Bank (bereits für Import geplant)
- Buchungen exportieren = DATEV/CSV/Excel (anderes Szenario!)

#### **OFX ❌ Ebenfalls Import-Format**
- **Was ist OFX?** Open Financial Exchange - Format für **Finanzdaten von Banken**
- **Zweck:** **IMPORT** von Bank-/Kreditkarten-Transaktionen
- **Richtung:** Bank → Buchhaltungssoftware (NICHT umgekehrt!)
- **Verwendung:** Quicken, GnuCash, MoneyMoney importieren OFX-Dateien
- **Fazit:** OFX ist ebenfalls ein **Bank-Import-Format**

---

### **3. Was der User wahrscheinlich meint**

Basierend auf dem Feature-Request vermute ich folgende **echten Bedürfnisse**:

#### **Szenario 1: Tabellenkalkulation (Excel/Google Sheets)**
✅ **Bereits gelöst durch:**
- CSV-Exporte für alle Bereiche (Kassenbuch, Rechnungen, Transaktionen)
- Excel-Export für Stammdaten (v1.1)

**Beispiel CSV-Export "Kassenbuch":**
```csv
Datum;Beschreibung;Betrag;Kategorie;Konto;USt;Belegnummer
01.12.2025;EDEKA Einkauf;-45,67;Wareneinkauf;1200;7%;KB-001
05.12.2025;Rechnung RE-001;1.190,00;Umsatzerlöse;8400;19%;RE-001
```

#### **Szenario 2: Andere Buchhaltungssoftware (Lexware, WISO, sevdesk, etc.)**
📋 **Teilweise geplant:**
- **v1.1:** AGENDA-Export (DATEV-CSV + Belegbilder)
- **v2.0:** Generisches Template-System für beliebige Software

**Noch NICHT unterstützt:**
- Lexware-spezifisches Format
- WISO-spezifisches Format
- sevdesk/Cloud-Buchhaltungen (außer via generischem CSV)

**Workaround (aktuell):**
1. CSV-Export aus RechnungsFee
2. Manuelles Anpassen der Spalten in Excel
3. Import in Zielsoftware

**Zukünftig (v2.0):**
- Community-Templates für gängige Software
- Spalten-Mapping-Tool

#### **Szenario 3: Datenumzug (RechnungsFee → andere Software)**
✅ **Bereits gelöst durch:**
- Vollständiger CSV-Export aller Daten (Rechnungen, Kunden, Buchungen)
- Backup-Export (SQLite-Datenbank)

**Hinweis:** Rückmigration ist IMMER aufwendig, da jede Software andere Datenmodelle hat!

---

## 💡 Empfehlung

### **Für v1.0 (MVP): ✅ Bereits ausreichend**

Die **geplanten CSV-Exporte** decken die beschriebenen Use-Cases bereits ab:

| Use-Case | Lösung |
|----------|--------|
| **Excel-Auswertung** | CSV-Export (Kassenbuch, Rechnungen, etc.) |
| **Datensicherung** | Backup-Export (SQLite) + CSV-Exporte |
| **Steuerberater** | DATEV-Export (CSV) |
| **Jobcenter** | EKS-Export (CSV/Excel/PDF) |
| **ELSTER** | UStVA/EÜR-Export (XML/CSV) |

### **Für v1.1: 📋 AGENDA-Export bereits geplant**

Erste Alternative zu DATEV:
- AGENDA Steuerberatersoftware
- Format: DATEV-CSV + Belegbilder-ZIP
- XRechnung/ZUGFeRD-konform

### **Für v2.0: 🔮 Generisches Export-System**

**Neues Feature:** Export-Template-Editor

**Funktionsweise:**
1. User wählt Zielsoftware (Dropdown oder "Andere")
2. RechnungsFee zeigt Template-Editor
3. Spalten-Mapping: RechnungsFee-Feld → Zielformat
4. Template speichern & wiederverwenden
5. Optional: Template an Community teilen (GitHub)

**Beispiel-Templates (Community):**
- Lexware-Import
- WISO-Import
- sevdesk-Import
- MoneyMoney-Import
- GnuCash-Import

**Technische Umsetzung:**
```json
{
  "name": "Lexware Buchhaltung",
  "version": "2025",
  "delimiter": ";",
  "encoding": "ISO-8859-1",
  "column_mapping": {
    "datum": "Belegdatum",
    "belegnummer": "Belegnummer",
    "betrag": "Betrag",
    "konto": "Konto",
    "gegenkonto": "Gegenkonto",
    "buchungstext": "Buchungstext"
  }
}
```

---

## 🎯 Konkrete Vorschläge für Issue #13

### **Vorschlag 1: Nice-to-have in v2.0 einplanen ✅**

**Feature:** Generisches Export-Template-System

**Funktionen:**
- Export-Wizard mit Spalten-Mapping
- Vordefinierte Templates für gängige Software (Lexware, WISO, sevdesk)
- Community-Templates über GitHub
- Template-Import/Export (JSON)

**Priorität:** Medium (v2.0)
**Aufwand:** Mittel (2-3 Wochen Entwicklung)
**Nutzen:** Hoch (Vendor-Lock-In-Vermeidung, Umstiegshilfe)

### **Vorschlag 2: Klarstellung im Issue ✅**

**Kommentar an @diddi04:**
- CAMT/OFX sind **Import-Formate** (Bank → Software), nicht Export
- CSV-Exporte sind bereits **umfangreich geplant**
- Generisches Template-System für v2.0 vormerken

**Frage an User:**
> Welche konkrete Buchhaltungssoftware möchtest du nutzen?
> - Lexware?
> - WISO?
> - sevdesk?
> - Andere?

**Damit können wir:**
- Priorität besser einschätzen
- Spezifisches Format recherchieren
- Ggf. als Community-Template umsetzen

---

## 📊 Zusammenfassung

| Aspekt | Bewertung |
|--------|-----------|
| **Problem valide?** | ✅ Ja - Export für Nicht-DATEV-Software sinnvoll |
| **Bereits gelöst?** | ⚠️ Teilweise - CSV-Export deckt Basis ab |
| **CAMT/OFX relevant?** | ❌ Nein - sind Bank-Import-Formate, kein Buchhaltungs-Export |
| **Feature nötig?** | 📋 Nice-to-have für v2.0 |
| **Aufwand** | ⚖️ Mittel (Template-System) |
| **Nutzen** | 📈 Hoch (Vendor-Lock-In vermeiden) |
| **Priorität** | 🟡 Medium (v2.0, nach MVP) |

---

## ✅ Nächste Schritte

1. **Kommentar im Issue posten** - Klarstellung + Rückfragen
2. **User-Feedback einholen** - Welche konkrete Software?
3. **v2.0 Roadmap** - Generisches Export-Template-System einplanen
4. **Community-Templates** - Repository für Templates erstellen
5. **Dokumentation** - Export-Formate in Docs detaillieren

---

## 📎 Anhang: Format-Übersicht

### **Import-Formate (Bank → RechnungsFee):**
- ✅ CSV (diverse Banken)
- ✅ MT940 (SWIFT-Kontoauszüge)
- ✅ CAMT.053 (ISO 20022 Kontoauszüge)
- ✅ OFX (Quicken-Format)
- ✅ PayPal CSV

### **Export-Formate (RechnungsFee → andere Software):**
- ✅ CSV (universell)
- ✅ DATEV ASCII-CSV (Steuerberater)
- ✅ ELSTER XML (Finanzamt)
- ✅ Excel (XLSX)
- ✅ PDF (Berichte, Formulare)
- ✅ ZUGFeRD/XRechnung (E-Rechnungen)
- 📋 AGENDA-Format (v1.1)
- 🔮 Generische Templates (v2.0)

---

**Erstellt:** 2026-01-24
**Autor:** Claude (AI-Assistent)
**Review:** Offen
