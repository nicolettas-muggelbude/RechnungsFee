<div align="center">
  <img src="src/frontend/public/logo.svg" alt="RechnungsFee Logo" width="80"/>
  <br/>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/readme-title-dark.svg"/>
    <img src="assets/readme-title.svg" alt="RechnungsFee" height="36"/>
  </picture>
</div>

# 🤝 Beitragen zu RechnungsFee

Vielen Dank für dein Interesse an RechnungsFee! Wir freuen uns über jeden Beitrag aus der Community.

---

## 📋 Inhaltsverzeichnis

- [Code of Conduct](#code-of-conduct)
- [Wie kann ich beitragen?](#wie-kann-ich-beitragen)
  - [Feedback & Ideen](#-feedback--ideen)
  - [Bugs melden](#-bugs-melden)
  - [Feature Requests](#-feature-requests)
  - [Code beitragen](#-code-beitragen)
  - [Dokumentation verbessern](#-dokumentation-verbessern)
  - [Bank-CSV Format beitragen](#-bank-csv-format-beitragen)
- [Entwicklungsumgebung einrichten](#-entwicklungsumgebung-einrichten)
- [Pull Requests](#pull-requests)
- [Coding Standards](#coding-standards)
- [Design Language](#design-language)
- [Commit-Nachrichten](#commit-nachrichten)
- [Fragen & Support](#fragen--support)

---

## 📜 Code of Conduct

Wir verpflichten uns zu einem offenen und einladenden Umfeld für alle, unabhängig von:
- Erfahrungslevel
- Geschlecht, Geschlechtsidentität und -ausdruck
- Sexueller Orientierung
- Behinderung
- Aussehen, Körpergröße, Ethnizität
- Alter, Religion

### Erwartetes Verhalten

✅ Respektvoll und konstruktiv kommunizieren
✅ Unterschiedliche Meinungen akzeptieren
✅ Konstruktive Kritik geben und annehmen
✅ Fokus auf das Beste für die Community

### Unerwünschtes Verhalten

❌ Belästigung, Diskriminierung oder Beleidigungen
❌ Trolling, beleidigende Kommentare
❌ Persönliche oder politische Angriffe
❌ Veröffentlichung privater Informationen ohne Erlaubnis

---

## 🚀 Wie kann ich beitragen?

### 💬 Feedback & Ideen

- Öffne eine [Discussion](https://github.com/nicolettas-muggelbude/RechnungsFee/discussions) für neue Ideen
- Kommentiere zu bestehenden Features in Issues
- Teile deine Erfahrungen als Freiberufler/Selbstständiger

### 🐛 Bugs melden

Wenn du einen Bug findest:

1. **Prüfe** ob der Bug bereits gemeldet wurde (Issues durchsuchen)
2. **Öffne** ein neues Issue mit:
   - Beschreibung des Problems
   - Schritte zur Reproduktion
   - Erwartetes vs. tatsächliches Verhalten
   - Screenshots (wenn hilfreich)
   - System-Info (OS, Browser, Version)

### ✨ Feature Requests

Feature-Wünsche sind willkommen! Bitte:

1. Prüfe ob das Feature bereits vorgeschlagen wurde
2. Öffne ein Issue mit Label `enhancement`
3. Beschreibe:
   - **Was** soll das Feature tun?
   - **Warum** ist es nützlich?
   - **Wie** könnte es umgesetzt werden? (optional)

### 💻 Code beitragen

1. **Fork** das Repository
2. **Clone** deinen Fork: `git clone https://github.com/DEIN-NAME/RechnungsFee.git`
3. **Branch** erstellen: `git checkout -b feature/dein-feature-name`
4. **Entwickeln** und testen
5. **Commit** mit aussagekräftiger Nachricht
6. **Push** zu deinem Fork: `git push origin feature/dein-feature-name`
7. **Pull Request** öffnen

### 📖 Dokumentation verbessern

Doku-Verbesserungen sind genauso wichtig wie Code!

- Tippfehler korrigieren
- Erklärungen verbessern
- Beispiele hinzufügen
- Übersetzungen (später)

### 🏦 Bank-CSV Format beitragen

Deine Bank wird noch nicht unterstützt? **Du kannst helfen!**

RechnungsFee wird Bank-CSVs verschiedener Banken importieren können. Jede Bank hat ihr eigenes Format - um alle zu unterstützen, brauchen wir anonymisierte Beispiel-CSVs.

#### Schritt 1: CSV exportieren

1. Logge dich in dein **Online-Banking** ein
2. Gehe zu **Kontoumsätze** oder **Transaktionen**
3. Wähle **Export** → **CSV** (oder ähnlich)
4. Wähle einen Zeitraum (z.B. **1 Monat** mit 10-20 Transaktionen)
5. **Speichere** die CSV-Datei

#### Schritt 2: Anonymisieren (WICHTIG!)

**⚠️ Teile NIE echte Bank-Daten!**

Ersetze sensible Informationen:

**❌ NICHT teilen:**
- **Kontonummer / IBAN** → Ersetze durch `DE89370400440532013000`
- **Namen** (Auftraggeber/Empfänger) → Ersetze durch `Max Mustermann`, `Firma GmbH`
- **Sensible Verwendungszwecke** → Ersetze durch allgemeine Beschreibungen
  - `Arztrechnung Dr. Med. XY` → `Arztrechnung`
  - `Miete Musterstraße 123` → `Miete`
  - `Kredit 123456` → `Kredittilgung`
- **BIC** (optional) → Ersetze durch `COBADEFFXXX`

**Optional anonymisieren:**
- **Beträge** → Runde auf runde Zahlen (`1.234,56` → `1.000,00`)

**✅ BEHALTEN (nicht ändern!):**
- **Header-Zeile** (Spaltenköpfe) - Muss original bleiben!
- **Trennzeichen** (Semikolon, Komma, etc.)
- **Anführungszeichen** (`"` oder `'`)
- **Datumsformat** (`DD.MM.YYYY`, `YYYY-MM-DD`, etc.)
- **Dezimaltrennzeichen** (Komma oder Punkt)
- **Währungskürzel** (`EUR`, `USD`, etc.)
- **CSV-Struktur** (Anzahl Spalten, Zeilenumbrüche)

**Beispiel - Vorher (NICHT TEILEN!):**
```csv
Datum;Partner;Verwendungszweck;Betrag
01.12.2025;Schmidt, Peter;Miete Musterstr. 42;-850,00
05.12.2025;Dr. Med. Müller;Arztrechnung 2025-001;-120,00
```

**Beispiel - Nachher (OK zum Teilen):**
```csv
Datum;Partner;Verwendungszweck;Betrag
01.12.2025;Mustermann, Max;Miete;-850,00
05.12.2025;Arztpraxis;Arztrechnung;-120,00
```

#### Schritt 3: Einreichen

1. **Erstelle** ein [GitHub Issue](https://github.com/nicolettas-muggelbude/RechnungsFee/issues/new?template=bank-csv-format.md) (verwende Template "Bank-CSV Format einreichen")
2. **Fülle** die Felder aus:
   - Bankname (z.B. "Sparkasse Musterstadt")
   - CSV-Format-Details (Trennzeichen, Encoding, Datumsformat)
   - Spaltenköpfe (in Reihenfolge)
3. **Hänge** die anonymisierte CSV-Datei an
4. **Fertig!** Wir prüfen und fügen sie zu `vorlagen/bank-csv/` hinzu

**Checkliste vor dem Einreichen:**
- [ ] CSV ist vollständig anonymisiert (keine echten IBANs, Namen, etc.)
- [ ] Header-Zeile ist unverändert (original Spaltenköpfe)
- [ ] CSV-Struktur ist unverändert (Trennzeichen, Format)
- [ ] 10-20 Beispielzeilen vorhanden (nicht zu wenige, nicht zu viele)
- [ ] GitHub Issue mit [Template](https://github.com/nicolettas-muggelbude/RechnungsFee/issues/new?template=bank-csv-format.md) erstellt

**Weitere Infos:**
- [vorlagen/bank-csv/TEMPLATE.md](vorlagen/bank-csv/TEMPLATE.md) - Detaillierte Anonymisierungs-Anleitung
- [vorlagen/bank-csv/README.md](vorlagen/bank-csv/README.md) - Übersicht unterstützter Banken

**🙏 Danke für deinen Beitrag!** Jede Bank-CSV hilft RechnungsFee für alle besser zu machen!

---

## 🛠️ Entwicklungsumgebung einrichten

### Voraussetzungen

- **Python 3.12+**
- **Node.js 22+**
- **Rust + Cargo** (nur für Tauri-Build, nicht für Web-Entwicklung nötig)
- **Git**

### Setup

```bash
# Repository klonen
git clone https://github.com/nicolettas-muggelbude/RechnungsFee.git
cd RechnungsFee
```

**Terminal 1 – Backend:**

```bash
cd src/backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --port 8002 --reload
```

**Terminal 2 – Frontend:**

```bash
cd src/frontend
npm install
npm run dev
```

Dann Browser öffnen: **http://localhost:5173**

### Ports

| Dienst | URL |
|--------|-----|
| Frontend (Vite) | http://localhost:5173 |
| Backend (FastAPI) | http://localhost:8002 |
| API-Docs (Swagger) | http://localhost:8002/docs |

### Datenpfade (Linux)

Seit v0.6.0 (Profilmanager) liegen die Daten pro Profil eine Ebene tiefer (`<Name>` = aktives
Profil, standardmäßig `Standard`; macOS: `~/Library/Application Support/RechnungsFee/`,
Windows: `%APPDATA%\RechnungsFee\`):

```
~/.local/share/RechnungsFee/profile/<Name>/rechnungsfee.db   ← Datenbank
~/.local/share/RechnungsFee/profile/<Name>/uploads/          ← Belegdateien
~/.local/share/RechnungsFee/profile/<Name>/backups/          ← automatische Backups
~/.local/share/RechnungsFee/plugins/                         ← Plugins (für alle Profile)
```

### Tauri-App bauen (optional)

Kurzfassung (Linux, im Projektordner):

```bash
bash scripts/build-sidecar.sh
NO_STRIP=true npx --yes @tauri-apps/cli@^2 build --bundles appimage
```

Voraussetzungen, Einrichtung, Testen und Fehlerbehebung: **[docs/build-lokal.md](docs/build-lokal.md)**.

---

## ⚖️ Lizenz-Hinweis für Beiträge

By submitting a pull request you agree that your contribution may be used under both the AGPL-3.0 license and a future commercial license by the project maintainer.

---

## 🔀 Pull Requests

### Checkliste vor dem PR

- [ ] Code läuft lokal ohne Fehler
- [ ] Tests geschrieben (falls zutreffend)
- [ ] Dokumentation aktualisiert
- [ ] UI-Änderungen halten sich an die [Design Language](docs/14-design-language.md)
- [ ] Commit-Nachrichten sind aussagekräftig
- [ ] Branch ist aktuell mit `main`

### PR-Beschreibung

Bitte beschreibe:

- **Was** ändert der PR?
- **Warum** ist die Änderung nötig?
- **Wie** wurde getestet?
- **Verknüpfung** zu Issues (z.B. "Fixes #123")

### Review-Prozess

1. Mindestens ein Maintainer reviewt deinen PR
2. Feedback wird konstruktiv gegeben
3. Du kannst Änderungen vornehmen (push zum selben Branch)
4. Nach Approval wird gemerged

---

## 📏 Coding Standards

### Allgemein

- **Lesbarkeit** vor Cleverness
- **Kommentare** für komplexe Logik
- **Keine Magic Numbers** - nutze Konstanten
- **DRY** (Don't Repeat Yourself)

### Python (Backend)

```python
# PEP 8 Style Guide befolgen
# Type Hints nutzen
def calculate_tax(amount: float, rate: float) -> float:
    """Berechnet Steuerbetrag."""
    return amount * rate

# Black als Formatter
# Ruff als Linter
```

### TypeScript/React (Frontend)

```typescript
// ESLint + Prettier
// Functional Components + Hooks
interface InvoiceProps {
  id: string;
  amount: number;
}

export function Invoice({ id, amount }: InvoiceProps) {
  // ...
}
```

### Benennung

- **Variablen**: `snake_case` (Python), `camelCase` (TypeScript)
- **Funktionen**: Verben (z.B. `calculateTotal`, `fetchInvoices`)
- **Klassen**: PascalCase (z.B. `InvoiceManager`)
- **Konstanten**: `UPPER_SNAKE_CASE`

---

## 🎨 Design Language

Alle UI-Beiträge müssen die festgelegte Designsprache einhalten.

➡️ **[docs/14-design-language.md](docs/14-design-language.md)**

Dort sind verbindlich definiert:
- Farben (Primär, Status, Dark Mode)
- Typografie-Hierarchie
- Seiten-Layout-Muster
- Tabellen, Buttons, Formulare, Modals
- Badges, Info-Boxen, Tooltips
- Dos & Don'ts

Neue Komponenten und Seiten dürfen keine eigenen Farben oder Abstände erfinden, sondern nutzen ausschließlich die dort beschriebenen Muster.

---

## 📝 Commit-Nachrichten

Wir nutzen **Conventional Commits**:

```
<type>: <subject>

<body (optional)>

<footer (optional)>
```

### Types

- `feat:` Neues Feature
- `fix:` Bug-Fix
- `docs:` Dokumentation
- `style:` Formatierung (kein Code-Change)
- `refactor:` Code-Refactoring
- `test:` Tests hinzufügen/ändern
- `chore:` Build-Prozess, Dependencies

### Beispiele

```bash
feat: Kassenbuch-Modul hinzugefügt

Implementiert Grundfunktionen für Kassenbuch:
- Einnahmen/Ausgaben erfassen
- Privatentnahmen kennzeichnen
- Automatische Verknüpfung mit Rechnungen

Closes #42
```

```bash
fix: OCR erkennt Beträge mit Komma korrekt

Behebt Problem bei Beträgen wie "1.234,56"

Fixes #78
```

```bash
docs: README um Installation erweitert
```

---

## ❓ Fragen & Support

### Vor der Frage

- 📖 Dokumentation lesen (README, Wiki)
- 🔍 Issues durchsuchen
- 💬 Discussions durchsuchen

### Hilfe bekommen

- **Allgemeine Fragen**: [GitHub Discussions](https://github.com/nicolettas-muggelbude/RechnungsFee/discussions)
- **Bug Reports**: [GitHub Issues](https://github.com/nicolettas-muggelbude/RechnungsFee/issues)
- **Entwickler-Fragen**: Discussions mit Label `question`

---

## 🙏 Danke!

Jeder Beitrag - egal wie klein - hilft RechnungsFee besser zu machen.

**Besonderer Dank an:**
- Alle Contributors
- Beta-Tester
- Issue-Reporter
- Dokumentations-Helfer

Gemeinsam bauen wir die beste Open-Source-Buchhaltung für Selbstständige! 🚀
