# 📊 RechnungsPilot

**Open-Source Buchhaltungssoftware für Freiberufler, Selbstständige und Kleinunternehmer**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Status](https://img.shields.io/badge/Status-In_Development-yellow)](https://github.com/nicoletta/RechnungsPilot)

---

## 🎯 Vision

RechnungsPilot ist eine plattformunabhängige, offline-first Buchhaltungslösung mit Fokus auf:

- **Einfachheit** - Speziell für Buchhaltungs-Laien entwickelt
- **Datenschutz** - Alle Daten bleiben lokal, verschlüsselte Backups
- **GoBD-Konformität** - Rechtssicher nach deutschen Steuervorschriften
- **Open Source** - Transparent, erweiterbar, community-driven

### Besonderheiten

✅ **Unterstützung für Transferleistungen** - EKS-Export für Selbstständige mit ALG II/Bürgergeld
✅ **Offline-First** - Volle Funktionalität ohne Internet
✅ **Zwei Versionen** - Desktop-App (einfach) & Docker (Power-User)
✅ **Mobile PWA** - Rechnungen unterwegs erfassen

---

## 🚀 Geplante Features

### Version 1.0 (MVP)

- 📥 **Eingangsrechnungen** verwalten (manuell, PDF-Import, OCR, ZUGFeRD/XRechnung)
- 📤 **Ausgangsrechnungen** verwalten (Rechnungsschreiben in späterem Modul)
- 💰 **Kassenbuch** führen (EAR-konform, kein POS)
- 🏦 **Bank-Integration** (CSV-Import, automatischer Zahlungsabgleich)
- 📊 **Steuerexporte**:
  - EAR (Einnahmen-Ausgaben-Rechnung)
  - EKS (Anlage für Agentur für Arbeit)
  - UStVA (Umsatzsteuervoranmeldung)
  - EÜR (Einnahmenüberschussrechnung)
- 🔗 **Schnittstellen**: DATEV, AGENDA
- 👤 **Stammdaten**: Kunden, Lieferanten, Unternehmen
- 💾 **Backup**: Automatisch & manuell (Nextcloud-Integration)
- 🔐 **Verschlüsselung**: SQLCipher (AES-256)

### Später (Version 1.x)

- Rechnungen schreiben (Ausgangsrechnungen erstellen)
- POS-Kassenbuch mit TSE
- ELSTER-Direktanbindung
- Bank-API (Live-Anbindung)
- Import aus hellocash, Rechnungsassistent, Fakturama
- Multi-User / Mandantenfähigkeit
- Mehrsprachigkeit

---

## 🛠️ Technologie-Stack (geplant)

| Bereich | Technologie | Begründung |
|---------|-------------|------------|
| **Desktop** | Tauri / Electron | Klein, schnell, plattformunabhängig |
| **Frontend** | React + TypeScript | Modern, große Community |
| **Backend** | FastAPI (Python) | Schnell, einfach, gute Doku |
| **Datenbank** | SQLite + SQLCipher | Lokal, verschlüsselt, keine Server |
| **OCR** | Tesseract.js / EasyOCR | Open Source, lokal |
| **Mobile** | PWA + Service Worker | Offline-fähig, keine App Stores |

---

## 📋 Projektstatus

**Phase:** 🟡 Konzeption & Planung

- [x] Projektvision definiert
- [x] Anforderungen erfasst (siehe [projekt.md](projekt.md))
- [x] Offene Fragen dokumentiert (siehe [fragen.md](fragen.md))
- [ ] Technologie-Stack finalisieren
- [ ] Datenbank-Schema entwerfen
- [ ] UI/UX-Konzept erstellen
- [ ] Projekt-Setup (Monorepo)
- [ ] MVP-Entwicklung

---

## 🤝 Mitmachen

Dieses Projekt wird offen entwickelt - die Community soll von Anfang an dabei sein!

### Wie kannst du helfen?

- 💬 **Feedback geben** - Teile deine Ideen und Anforderungen
- 🐛 **Bugs melden** - Öffne Issues wenn etwas nicht funktioniert
- 💻 **Code beitragen** - Pull Requests sind willkommen (siehe [CONTRIBUTING.md](CONTRIBUTING.md))
- 📖 **Dokumentation** - Hilf die Docs zu verbessern
- 🧪 **Testen** - Werde Beta-Tester
- ⭐ **Stern geben** - Zeig deine Unterstützung

### Community

- 📣 **Diskussionen**: [GitHub Discussions](https://github.com/nicoletta/RechnungsPilot/discussions) *(coming soon)*
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/nicoletta/RechnungsPilot/issues)
- 📧 **Kontakt**: *(coming soon)*

---

## 📄 Lizenz

Dieses Projekt ist lizenziert unter der **GNU Affero General Public License v3.0 (AGPL-3.0)**.

Das bedeutet:
- ✅ Frei nutzbar (privat & kommerziell)
- ✅ Quellcode einsehbar
- ✅ Anpassbar & erweiterbar
- ⚠️ Änderungen müssen ebenfalls AGPL-3.0 sein
- ⚠️ Bei Netzwerknutzung: Quellcode bereitstellen

Siehe [LICENSE](LICENSE) für Details.

---

## ⚠️ Haftungsausschluss

**Keine Steuerberatung:** RechnungsPilot ist ein Software-Tool, ersetzt aber keine professionelle Steuerberatung. Bei steuerlichen Fragen konsultiere einen Steuerberater oder das Finanzamt.

**Keine Garantie:** Die Software wird "wie besehen" bereitgestellt, ohne Gewährleistung für Korrektheit oder Vollständigkeit.

---

## 🗺️ Roadmap

### Q1 2025
- Anforderungsanalyse abschließen
- Technologie-Stack finalisieren
- Datenbank-Schema entwerfen
- Projekt-Setup & CI/CD

### Q2 2025
- MVP-Entwicklung starten
- Kernfunktionen implementieren
- Erste Beta-Version

### Q3 2025
- Beta-Testing mit echten Nutzern
- Feedback einarbeiten
- Dokumentation erstellen

### Q4 2025
- Version 1.0 Release
- Desktop-Installer für Windows/Mac/Linux
- Öffentliche Ankündigung

*(Zeitplan ist flexibel und wird nach Community-Feedback angepasst)*

---

## 📚 Dokumentation

- [projekt.md](projekt.md) - Detaillierter Projektplan
- [fragen.md](fragen.md) - Offene Fragen zur Anforderungsanalyse
- [claude.md](claude.md) - Entwicklungs-Tagebuch

---

**Entwickelt mit ❤️ für die Freiberufler- und Selbstständigen-Community**
