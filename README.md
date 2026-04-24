<div align="center">
  <img src="src/frontend/public/logo.svg" alt="RechnungsFee Logo" width="120"/>

  # RechnungsFee

  **Open-Source Buchhaltungssoftware für Freiberufler, Selbstständige und Kleinunternehmer**

  [![Release](https://img.shields.io/github/v/release/nicolettas-muggelbude/RechnungsFee)](https://github.com/nicolettas-muggelbude/RechnungsFee/releases/latest)
  [![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
  [![GitHub stars](https://img.shields.io/github/stars/nicolettas-muggelbude/RechnungsFee?style=social)](https://github.com/nicolettas-muggelbude/RechnungsFee/stargazers)
  [![GitHub issues](https://img.shields.io/github/issues/nicolettas-muggelbude/RechnungsFee)](https://github.com/nicolettas-muggelbude/RechnungsFee/issues)
  [![GitHub discussions](https://img.shields.io/github/discussions/nicolettas-muggelbude/RechnungsFee)](https://github.com/nicolettas-muggelbude/RechnungsFee/discussions)

</div>

---

## ⬇️ Download

| Betriebssystem | Download | Hinweis |
|---|---|---|
| **Windows 10/11** | [→ Releases-Seite](https://github.com/nicolettas-muggelbude/RechnungsFee/releases/latest) → `…x64-setup.exe` | NSIS-Installer, einfach ausführen |
| **Linux (x86_64)** | [→ Releases-Seite](https://github.com/nicolettas-muggelbude/RechnungsFee/releases/latest) → `…amd64.AppImage` | Ausführbar machen + starten |

```bash
# Linux: AppImage ausführbar machen
chmod +x RechnungsFee_*.AppImage
./RechnungsFee_*.AppImage
```

Installierte Apps aktualisieren sich automatisch – beim nächsten Start erscheint ein Update-Banner.

---

## ✨ Was kann RechnungsFee?

### 📒 Kassenbuch (GoBD-konform)
- Einnahmen & Ausgaben erfassen – Bar, Karte, Bank, PayPal
- **Unveränderliche Einträge** nach §146 AO – Storno erzeugt Gegenbuchung, kein Löschen
- **SHA-256-Signaturen** für jeden Eintrag und Tagesabschluss
- Split-Buchungen für gemischte Zahlungen
- Automatische **Belegnummern** (Nummernkreise frei konfigurierbar)

### 🧾 Rechnungen
- Ausgangsrechnungen & Eingangsrechnungen
- **PDF nach DIN 5008** – mit Logo, Unternehmensblock, Fensterumschlag-Adressfeld
- Zahlungsverfolgung mit Teilzahlungen und Fortschrittsbalken
- Bar-, Karte-, PayPal- und Banküberweisungserfassung
- Entwurfsmodus & Finalisierung, Storno mit automatischer Kassenbuchgegenbuchung
- Suche nach Rechnungsnummer und Partnername, kombinierbar mit Status-Filter

### 📦 Artikelstamm
- Artikel, Dienstleistungen und Fremdleistungen verwalten
- VK und EK – Eingabe wahlweise als Netto oder Brutto, automatische Gegenrechnung
- Verknüpfung mit Lieferanten, Rechnungshistorie je Artikel
- Autocomplete beim Erstellen von Rechnungspositionen

### 📋 Tagesabschlüsse
- Soll/Ist-Vergleich mit Differenzprotokoll
- Unveränderlicher Abschluss mit **SHA-256-Integritätsprüfung**
- PDF-Export für die Buchhaltungsablage

### 👥 Kunden & Lieferanten
- Vollständige Stammdatenverwaltung
- **DSGVO-konform**: Auskunft Art. 15 (JSON-Export) · Löschung Art. 17 (Anonymisierung)

### 📦 GoBD-Export
- Export für Betriebsprüfungen nach **Z3-Datenträgerüberlassung**
- 8 CSV-Dateien + PDF-Prüfbericht als ZIP

### 🏢 Unternehmensstammdaten
- Logo-Upload, Steuernummer, USt-IdNr., IBAN, Rechtsform
- Mail-Vorlagen mit Platzhaltern für Rechnungsversand
- **Kleinunternehmer §19 UStG** vollständig unterstützt (USt automatisch 0 %)
- **Umsatzwarnung** – Dashboard-Hinweis wenn die Jahresumsatzgrenze (100.000 €) in Sicht ist oder überschritten wurde

### 🔧 Weitere Funktionen
- **Setup-Assistent** für den ersten Start
- **Manuelles Backup** als Download + automatisches Backup vor DB-Updates
- **Kontext-Hilfe** mit ℹ-Tooltips für GoBD-Konzepte, Steuerfelder und Rechnungslogik
- **Auto-Updater** – neue Versionen werden direkt in der App angeboten
- **Offline-first** – alle Daten bleiben lokal auf deinem Rechner

---

## 🗺️ Roadmap

| Version | Inhalt | Status |
|---------|--------|--------|
| **v0.1.x** | Kassenbuch, Rechnungen, GoBD, GiroCode, Dark Mode, Tauri-App, Auto-Updater | ✅ Aktuell |
| **v0.2** | Bank-CSV-Import (Postbank, Sparkasse, Volksbank …), Auto-Filter-Regeln, Duplikat-Erkennung | 🔲 Ziel: Juni 2026 |
| **v0.3** | EÜR, UStVA-Voranmeldung, DATEV-Export, Jahresübersicht | 🔲 Ziel: August 2026 |
| **v0.4** | Eingangsrechnungen digitalisieren – PDF/Foto-Upload mit OCR-gestützter Felderkennung | 🔲 Ziel: Oktober 2026 |
| **v1.0** | Mehrsprachigkeit (DE/EN/TR/AR/UK/FA), Einstellungen, Flatpak/Flathub | 🔲 Ziel: Dezember 2026 |
| **v1.1** | ZUGFeRD/XRechnung, Rechnungs-PDF-Vorschau im App | 🔲 Ziel: Februar 2027 |

---

## 🛠️ Tech Stack

| Bereich | Technologie |
|---------|-------------|
| Desktop-Shell | [Tauri 2](https://tauri.app) (Rust) |
| Frontend | React 19, Vite, TypeScript, Tailwind CSS v4 |
| State / Forms | TanStack Query, React Hook Form + Zod |
| Backend | FastAPI, Python 3.12 |
| Datenbank | SQLite (WAL-Modus), SQLAlchemy 2.0 |
| PDF | fpdf2 (DIN 5008) |
| Pakete | AppImage (Linux), NSIS-Installer (Windows) |

---

## 🚀 Lokale Entwicklung

### Voraussetzungen

- Python 3.12+
- Node.js 22+
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

### Tauri Desktop-App (Entwicklungsmodus)

```bash
# Sidecar-Binary zuerst bauen
bash scripts/build-sidecar.sh      # Linux
# pwsh scripts/build-sidecar.ps1  # Windows

cd src/frontend
npm run tauri dev
```

---

## 🤝 Mitmachen

Dieses Projekt wird offen entwickelt – die Community soll von Anfang an dabei sein!

- 💬 **Feedback & Ideen** → [GitHub Discussions](https://github.com/nicolettas-muggelbude/RechnungsFee/discussions)
- 🐛 **Bugs melden** → [GitHub Issues](https://github.com/nicolettas-muggelbude/RechnungsFee/issues)
- 💻 **Code beitragen** → Pull Requests sind willkommen
- ⭐ **Stern geben** → Hilft anderen, das Projekt zu finden

---

## 🌟 Mitwirkende

Danke an alle, die RechnungsFee besser machen – durch Code, Tests, Ideen, Design und Feedback!

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Adler-real"><img src="https://avatars.githubusercontent.com/u/166315348?v=4?s=100" width="100px;" alt="Adlerreal"/><br /><sub><b>Adlerreal</b></sub></a><br /><a href="#design-Adler-real" title="Design">🎨</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Peter1061"><img src="https://avatars.githubusercontent.com/u/267404634?v=4?s=100" width="100px;" alt="Peter1061"/><br /><sub><b>Peter1061</b></sub></a><br /><a href="#userTesting-Peter1061" title="User Testing">📓</a> <a href="https://github.com/nicolettas-muggelbude/RechnungsFee/issues?q=author%3APeter1061" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/pengu1981"><img src="https://avatars.githubusercontent.com/pengu1981?s=100" width="100px;" alt="pengu1981"/><br /><sub><b>pengu1981</b></sub></a><br /><a href="#userTesting-pengu1981" title="User Testing">📓</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

🎨 Design &nbsp;·&nbsp; 💻 Code &nbsp;·&nbsp; 📓 Testen &nbsp;·&nbsp; 🐛 Bugs gemeldet &nbsp;·&nbsp; 🤔 Ideen &nbsp;·&nbsp; 📖 Dokumentation

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

<div align="center">
  <strong>Entwickelt mit ❤️ für die Freiberufler- und Selbstständigen-Community</strong>
</div>
