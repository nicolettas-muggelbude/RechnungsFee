# 🧾 RechnungsFee

**Open-Source Buchhaltungssoftware für Freiberufler, Selbstständige und Kleinunternehmer**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Release](https://img.shields.io/github/v/release/nicolettas-muggelbude/RechnungsFee)](https://github.com/nicolettas-muggelbude/RechnungsFee/releases)
[![GitHub stars](https://img.shields.io/github/stars/nicolettas-muggelbude/RechnungsFee?style=social)](https://github.com/nicolettas-muggelbude/RechnungsFee/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/nicolettas-muggelbude/RechnungsFee)](https://github.com/nicolettas-muggelbude/RechnungsFee/issues)
[![GitHub discussions](https://img.shields.io/github/discussions/nicolettas-muggelbude/RechnungsFee)](https://github.com/nicolettas-muggelbude/RechnungsFee/discussions)

---

## 🎯 Vision

RechnungsFee ist eine plattformunabhängige, offline-first Buchhaltungslösung mit Fokus auf:

- **Einfachheit** – Speziell für Buchhaltungs-Laien entwickelt
- **Datenschutz** – Alle Daten bleiben lokal auf deinem Rechner
- **GoBD-Konformität** – Rechtssicher nach deutschen Steuervorschriften
- **Open Source** – Transparent, erweiterbar, community-driven

**Besonderheit:** Unterstützung für Selbstständige mit Transferleistungen (ALG II / Bürgergeld) durch EKS-Export.

---

## ✅ Aktueller Stand – v0.1 Kassenbuch

[**→ Release-Notes v0.1**](https://github.com/nicolettas-muggelbude/RechnungsFee/releases/tag/v0.1)

- 📒 **GoBD-konformes Kassenbuch** – Einnahmen/Ausgaben erfassen, Storno als Gegenbuchung, keine Manipulation möglich
- 🔢 **Automatische Belegnummern** – Format `KB-YYYYMMDD-NNN`
- 💶 **USt-Berechnung** – Aus Bruttobetrag (ROUND_HALF_UP), §19 UStG automatisch für Kleinunternehmer
- 📅 **Tagesabschluss** – Soll/Ist-Vergleich mit Differenzprotokoll
- 👤 **Kunden & Lieferanten** – Stammdatenverwaltung
- 📊 **Dashboard** – Monatsstatistik (Einnahmen / Ausgaben / Saldo)
- 🗂️ **Kategorien** – 31 vordefinierte Kategorien (SKR03/04/49, EÜR-Zuordnung)

---

## 🗺️ Roadmap

| Version | Inhalt | Status |
|---------|--------|--------|
| **v0.1** | Kassenbuch (GoBD-konform) | ✅ Released Februar 2026 |
| **v0.2** | Bank-CSV Import (Postbank, Sparkasse, Volksbank…) | 🔲 Ziel: Juni 2026 |
| **v0.3** | EÜR, UStVA, DATEV-Export | 🔲 Ziel: August 2026 |
| **v1.0** | Tauri-Installer, Backup, Dokumentation | 🔲 Ziel: Oktober 2026 |
| **v1.1** | Rechnungsmodul, ZUGFeRD | 🔲 Ziel: Dezember 2026 |

Vollständige Roadmap: [docs/ROADMAP.md](docs/ROADMAP.md)

---

## 🛠️ Tech Stack

| Bereich | Technologie |
|---------|-------------|
| Desktop-Shell | [Tauri 2](https://tauri.app) (Rust) |
| Frontend | React 19, Vite, TypeScript, Tailwind CSS v4 |
| State / Forms | React Query, React Hook Form + Zod |
| Backend | FastAPI, Python 3.12 |
| Datenbank | SQLite (WAL-Modus), SQLAlchemy 2.0 |
| Kontenrahmen | SKR03 / SKR04 / SKR49 |

---

## 🚀 Lokale Entwicklung

### Voraussetzungen

- Python 3.12+
- Node.js 20+
- Rust + Cargo (für Tauri)

### Backend starten

```bash
cd src/backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --port 8001 --reload
```

API läuft unter `http://localhost:8001` · Swagger-Docs: `http://localhost:8001/docs`

### Frontend starten

```bash
cd src/frontend
npm install
npm run dev
```

App läuft unter `http://localhost:5173`

### Tauri Desktop-App

```bash
cd src/frontend
npm run tauri dev
```

---

## 🤝 Mitmachen

Dieses Projekt wird offen entwickelt – die Community soll von Anfang an dabei sein!

- 💬 **Feedback & Ideen** → [GitHub Discussions](https://github.com/nicolettas-muggelbude/RechnungsFee/discussions)
- 🐛 **Bugs melden** → [GitHub Issues](https://github.com/nicolettas-muggelbude/RechnungsFee/issues)
- 💻 **Code beitragen** → Pull Requests willkommen, siehe [CONTRIBUTING.md](CONTRIBUTING.md)
- 🏦 **Bank-CSV Format einreichen** → [Anleitung](CONTRIBUTING.md#-bank-csv-format-beitragen)
- ⭐ **Stern geben** → Hilft anderen, das Projekt zu finden

---

## 📚 Dokumentation

| Datei | Inhalt |
|-------|--------|
| [docs/ROADMAP.md](docs/ROADMAP.md) | Versionierte Roadmap mit Meilensteinen |
| [docs/02-kassenbuch.md](docs/02-kassenbuch.md) | Kassenbuch-Konzept & GoBD |
| [docs/03-bank-integration.md](docs/03-bank-integration.md) | Bank-CSV Import |
| [docs/04-ustva.md](docs/04-ustva.md) | UStVA & EÜR |
| [projekt.md](projekt.md) | Projektplan & Feature-Übersicht |

---

## 📄 Lizenz

Lizenziert unter der **GNU Affero General Public License v3.0 (AGPL-3.0)**.

- ✅ Frei nutzbar (privat & kommerziell)
- ✅ Quellcode einsehbar und anpassbar
- ⚠️ Änderungen müssen ebenfalls unter AGPL-3.0 veröffentlicht werden

Siehe [LICENSE](LICENSE) für Details.

---

## ⚠️ Haftungsausschluss

RechnungsFee ist ein Software-Tool und ersetzt keine professionelle Steuerberatung. Bei steuerlichen Fragen wende dich an einen Steuerberater oder das Finanzamt. Die Software wird ohne Gewährleistung für Korrektheit oder Vollständigkeit bereitgestellt.

---

**Entwickelt mit ❤️ für die Freiberufler- und Selbstständigen-Community**
