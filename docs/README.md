# 📚 RechnungsFee - Projektdokumentation

**Vollständige Anforderungs- und Konzeptdokumentation**

---

## 📖 Dokumentations-Übersicht

Diese Dokumentation beschreibt alle Anforderungen, Konzepte und Entscheidungen für RechnungsFee.

### 🎯 Grundlagen

| Dokument | Beschreibung | Seiten |
|----------|--------------|--------|
| **[01-projektvision.md](01-projektvision.md)** | Projektvision, Kernmerkmale, UI/UX-Richtlinien | ~125 |

### 📊 Kernfunktionen

| Dokument | Beschreibung | Kategorie |
|----------|--------------|-----------|
| **[02-kassenbuch.md](02-kassenbuch.md)** | Kassenbuch-Führung, Tagesabschluss, GoBD-Konformität | Kategorie 1 |
| **[03-bank-integration.md](03-bank-integration.md)** | Bank-CSV-Import, Zahlungsabgleich, Format-Erkennung | Kategorie 5 |

### 💰 Steuern & Abgaben

| Dokument | Beschreibung | Kategorie |
|----------|--------------|-----------|
| **[04-ustva.md](04-ustva.md)** | Umsatzsteuer-Voranmeldung (UStVA), Kleinunternehmer, EU-Handel | Kategorie 6 |
| **[05-euer.md](05-euer.md)** | Einnahmen-Überschuss-Rechnung (EÜR), AfA, Anlagenverwaltung | Kategorie 7 |
| **[10-steuersaetze.md](10-steuersaetze.md)** | Steuersätze, Buchungslogik, Reverse-Charge | Kategorie 11 |

### 🗂️ Stammdaten & Import

| Dokument | Beschreibung | Kategorie |
|----------|--------------|-----------|
| **[06-stammdaten.md](06-stammdaten.md)** | Unternehmerdaten, Kunden, Lieferanten, Ersteinrichtung | Kategorie 8 |
| **[08-import.md](08-import.md)** | Import aus Fakturama, hellocash, Rechnungsassistent | Kategorie 9 |

### 🔐 Sicherheit & Wartung

| Dokument | Beschreibung | Kategorie |
|----------|--------------|-----------|
| **[07-dsgvo.md](07-dsgvo.md)** | Datenschutzerklärung, DSGVO-Konformität | - |
| **[09-backup-updates.md](09-backup-updates.md)** | Backup-Strategie, Software-Updates, Exit-Backup | Kategorie 10 |
| **[debug-plugin.md](debug-plugin.md)** | Mitgeliefertes Debug-Protokoll: Kategorien, Live-Anzeige und Logdatei | - |

### ❓ Hilfe & Support

| Dokument | Beschreibung | Kategorie |
|----------|--------------|-----------|
| **[12-hilfe-system.md](12-hilfe-system.md)** | Hilfe-System, Tooltips, FAQ, Community-Support | Kategorie 12 |

### 📎 Anhang

| Dokument | Beschreibung |
|----------|--------------|
| **[11-appendix.md](11-appendix.md)** | Bilanzpflichtige Unternehmen, Community-Feedback |

---

## 🗺️ Schnellzugriff nach Thema

### Für Entwickler

- **App lokal bauen (AppImage):** Siehe [build-lokal.md](build-lokal.md)
- **Plugin-Host-API:** [Lesen, Schreiben, Transaktionen und Rechte](plugin-host-api.md)
- **Python-Plugin entwickeln:** [Baubares Beispiel mit Anleitung](../examples/plugins/python-kundenpruefung/README.md)
- **Plugin-System:** Siehe [plugin-system.md](plugin-system.md) (Lastenheft), [plan-plugin-system.md](plan-plugin-system.md) (Umsetzung)
- **Datenbank-Schema:** Siehe [06-stammdaten.md](06-stammdaten.md), [02-kassenbuch.md](02-kassenbuch.md)
- **API-Anforderungen:** Siehe [03-bank-integration.md](03-bank-integration.md), [08-import.md](08-import.md)
- **UI/UX-Richtlinien:** Siehe [01-projektvision.md](01-projektvision.md#-uiux-richtlinien--tonalität)
- **DSGVO-Compliance:** Siehe [07-dsgvo.md](07-dsgvo.md)

### Für Steuerberater / Fachexperten

- **UStVA-Logik:** Siehe [04-ustva.md](04-ustva.md)
- **EÜR-Generierung:** Siehe [05-euer.md](05-euer.md)
- **Steuersätze & Reverse-Charge:** Siehe [10-steuersaetze.md](10-steuersaetze.md)
- **DATEV/AGENDA-Export:** Siehe [04-ustva.md](04-ustva.md), [05-euer.md](05-euer.md)

### Für Produktmanager

- **Projektvision & Features:** Siehe [01-projektvision.md](01-projektvision.md)
- **Ersteinrichtung:** Siehe [06-stammdaten.md](06-stammdaten.md)
- **Backup-Strategie:** Siehe [09-backup-updates.md](09-backup-updates.md)
- **Import-Kompatibilität:** Siehe [08-import.md](08-import.md)
- **Hilfe-System & Support:** Siehe [12-hilfe-system.md](12-hilfe-system.md)

---

## 📊 Dokumentations-Statistik

| Bereich | Dokumente | Geschätzte Zeilen |
|---------|-----------|-------------------|
| **Grundlagen** | 1 | ~125 |
| **Kernfunktionen** | 2 | ~2.000 |
| **Steuern** | 3 | ~4.500 |
| **Stammdaten** | 2 | ~5.500 |
| **Sicherheit** | 2 | ~2.000 |
| **Hilfe & Support** | 1 | ~600 |
| **Anhang** | 1 | ~600 |
| **GESAMT** | **12** | **~15.600 Zeilen** |

---

## 🔄 Ursprüngliche Datei

Die ursprüngliche, monolithische `claude.md` wurde aufgeteilt für bessere Wartbarkeit und Übersichtlichkeit.

**Original:** `../claude.md` (15.358 Zeilen, 572 KB)

---

## 📝 Hinweise zur Nutzung

- **Interne Links:** Alle Dokumente verlinken aufeinander wo sinnvoll
- **Navigation:** Nutze die Übersicht oben für schnellen Zugriff
- **Aktualität:** Letzte Aktualisierung: 2025-12-12
- **Format:** Alle Dokumente sind in Markdown (.md)

---

## 🤝 Mitarbeiten

Verbesserungen an der Dokumentation sind willkommen!

- Tippfehler korrigieren
- Klarstellungen hinzufügen
- Beispiele ergänzen
- Strukturverbesserungen vorschlagen

Siehe [../CONTRIBUTING.md](../CONTRIBUTING.md) für Details.

---

**RechnungsFee** - Open-Source Buchhaltungssoftware
📄 Lizenz: AGPL-3.0 | 🌐 GitHub: [nicolettas-muggelbude/RechnungsFee](https://github.com/nicolettas-muggelbude/RechnungsFee)
