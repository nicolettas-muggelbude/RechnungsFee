# Vorlagen & Beispieldateien

Dieser Ordner enthält Beispieldateien, Vorlagen und Test-Fixtures für RechnungsPilot.

---

## 📂 Struktur

### **kassenbuch/**
Beispieldateien für die Kassenbuchführung.

- **`kassenbuchfelder.csv`** - Beispiel für Kassenbucheinträge mit allen Feldern
  - Enthält: Datum, Belegnr., Beschreibung, Kategorie, Zahlungsart, Art, Netto, USt-Satz, USt-Betrag, Brutto, Vorsteuerabzug, Tagesendsumme-Bar
  - Dient als Referenz für die Datenstruktur

### **datev/**
Beispieldateien für DATEV-Export.

- **`datev-export.csv`** - DATEV ASCII-Format Buchungsstapel
  - Header mit Beraternummer, Mandantennummer, Kontenrahmen
  - Buchungszeilen im DATEV-Standard-Format
  - Encoding: Windows-1252
  - Dient als Referenz für Export-Implementierung

### **steuern/**
Beispieldateien für Steuerexporte.

- **`anlage-eks.html`** - Anlage EKS (Einkommenserklärung Selbstständige)
  - 9-seitiges Formular der Agentur für Arbeit / Jobcenter
  - Für Selbstständige mit ALG II / Bürgergeld
  - Tabellen A (Betriebseinnahmen), B (Betriebsausgaben), C (Absetzungen)
  - Dient als Referenz für EKS-Export-Implementierung

### **e-rechnung/**
Beispieldateien für elektronische Rechnungen (XRechnung, ZUGFeRD).

*Noch leer - wird später befüllt*

Geplant:
- XRechnung-Beispiel (XML)
- ZUGFeRD-Beispiel (PDF/A-3 mit embedded XML)
- Factur-X-Beispiel

---

## 🔮 Geplante Erweiterungen

### **bank-csv/**
CSV-Beispiele verschiedener Banken für Import-Tests.

Geplant:
- `sparkasse.csv`
- `volksbank.csv`
- `dkb.csv`
- `n26.csv`
- `ing.csv`
- `postbank.csv`

### **libreoffice/**
LibreOffice-Rechnungsvorlagen mit Platzhaltern.

Geplant:
- `rechnung-standard.ott` - Schlichte Standardvorlage
- `rechnung-business.ott` - Professionelle Business-Vorlage
- `rechnung-kreativ.ott` - Kreative Vorlage für Designer

### **steuern/** (Erweiterungen)
Weitere Steuerexport-Beispiele.

Geplant:
- `ustva-beispiel.xml` - Umsatzsteuervoranmeldung
- `euer-beispiel.xml` - Einnahmenüberschussrechnung
- `ear-beispiel.csv` - Einnahmen-Ausgaben-Rechnung

---

## 📝 Verwendung

### Für Entwicklung:
Diese Dateien dienen als:
- **Referenz** für Datenstrukturen und Formate
- **Test-Fixtures** für Unit-Tests und Integration-Tests
- **Beispiele** für die Dokumentation

### Für Dokumentation:
Die Dateien werden in `claude.md` und anderen Dokumenten referenziert, z.B.:
- "Siehe `vorlagen/datev/datev-export.csv` für DATEV-Format"
- "Beispiel-Kassenbuch: `vorlagen/kassenbuch/kassenbuchfelder.csv`"

### Für Testing:
Später können diese Dateien in automatisierten Tests verwendet werden:
```python
# Beispiel
import csv
with open('vorlagen/datev/datev-export.csv') as f:
    reader = csv.reader(f, delimiter=';')
    assert validate_datev_format(reader)
```

---

## ⚠️ Hinweise

- **Keine echten Daten:** Alle Dateien enthalten nur Beispieldaten, keine realen Geschäftsdaten
- **Format-Referenz:** Die Dateien zeigen das korrekte Format, sind aber nicht für Produktivnutzung gedacht
- **Versionskontrolle:** Alle Dateien sind unter Git-Versionskontrolle
- **Erweiterbar:** Neue Beispieldateien können jederzeit hinzugefügt werden

---

## 📚 Weiterführende Dokumentation

Detaillierte Informationen zu den Formaten und ihrer Verwendung:
- [claude.md](../claude.md) - Vollständige Anforderungsdokumentation
- [projekt.md](../projekt.md) - Projektplan und Roadmap
- [fragen.md](../fragen.md) - Offene Fragen zur Anforderungsanalyse
