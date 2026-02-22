# RechnungsFee – Projektplan & Roadmap

**Ziel:** Open-Source Buchhaltungssoftware für Freiberufler, Selbstständige und Kleinunternehmer
**Lizenz:** AGPL-3.0 · **Stack:** Tauri 2 · React 19 · FastAPI · SQLite (WAL)

---

## Status

| Version | Inhalt | Status |
|---------|--------|--------|
| **v0.1** | Kassenbuch (GoBD-konform) | ✅ Released 2026-02-22 |
| **v0.2** | Bank-CSV Import | 🔲 Geplant |
| **v0.3** | Rechnungsmodul | 🔲 Geplant |
| **v0.4** | EÜR / UStVA Export | 🔲 Geplant |
| **v1.0** | Erstes stabiles Release | 🔲 Geplant |

---

## v0.1 – Kassenbuch ✅

- GoBD-konformes Kassenbuch (keine Änderung/Löschung, Storno als Gegenbuchung)
- Belegnummer-Generierung: `KB-YYYYMMDD-NNN`
- USt-Berechnung aus Bruttobetrag (ROUND_HALF_UP)
- Kleinunternehmer-Automatik (§19 UStG)
- Tagesabschluss mit Soll/Ist-Vergleich und Differenzprotokoll
- Kunden- & Lieferantenverwaltung
- Dashboard: Monatsstatistik (Einnahmen / Ausgaben / Saldo)
- Sidebar-Navigation im App-Layout

---

## v0.2 – Bank-CSV Import

**Ziel:** Kontoauszüge importieren und Buchungen halbautomatisch zuordnen.

- CSV-Import für gängige Bankformate (Postbank, Sparkasse, DKB, ING)
- Vorlagen-System (`bank_templates` – bereits in DB vorhanden)
- Automatische Kategorie-Vorschläge per Regelwerk (`auto_filter_regeln`)
- Mischkonto-Klassifizierung: geschäftlich / privat / Privatentnahme
- Import-Protokoll mit Duplikat-Erkennung
- Frontend: Import-Wizard + manuelle Nachbearbeitung

---

## v0.3 – Rechnungsmodul

**Ziel:** Eingangs- und Ausgangsrechnungen erfassen und verwalten.

- Ausgangsrechnungen schreiben (PDF-Generierung)
- Eingangsrechnungen erfassen (manuell oder per PDF-Upload)
- Zuordnung zu Kunden / Lieferanten
- Zahlungsstatus & Fälligkeitsverfolgung
- Vorsteuerabzug für Eingangsrechnungen
- Rechnungspositionen mit verschiedenen USt-Sätzen
- Verknüpfung mit Kassenbuch / Bankkonto

---

## v0.4 – EÜR / UStVA Export

**Ziel:** Steuerrelevante Auswertungen und Exporte.

- Einnahmen-Überschuss-Rechnung (EÜR) – Jahresauswertung
- Umsatzsteuer-Voranmeldung (UStVA) – monatlich / quartalsweise
- Anlage EKS (für Transferleistungsbezieher)
- DATEV-Export (CSV)
- §19-Umsatzgrenze-Warnung (aktuelle Grenze: 25.000 € ab 2025)

---

## v1.0 – Erstes stabiles Release

**Ziel:** Produktionsreif, dokumentiert, updatefähig.

- Tauri-Installer (Windows / macOS / Linux)
- Auto-Update via GitHub Releases
- Backup-Funktion (lokale ZIP-Sicherung)
- Benutzerhandbuch (MkDocs)
- Vollständige Testabdeckung Backend (pytest)

---

## Spätere Versionen (Backlog)

| Feature | Prio |
|---------|------|
| AfA-Berechnung (Anlagevermögen) | Mittel |
| OCR-Erkennung für PDF-Rechnungen | Mittel |
| XRechnung / ZUGFeRD Import | Niedrig |
| Docker-Version | Niedrig |
| Mobile PWA | Niedrig |
| ELSTER-Direktübertragung | Niedrig |
| Mehrsprachigkeit (i18n) | Niedrig |

---

## Tech Stack

| Bereich | Technologie |
|---------|-------------|
| Desktop-Shell | Tauri 2.10 (Rust) |
| Frontend | React 19, Vite, TypeScript, Tailwind CSS v4 |
| State / API | React Query, React Hook Form + Zod |
| Backend | FastAPI, Python 3.12 |
| Datenbank | SQLite (WAL-Modus), SQLAlchemy 2.0 |
| DB-Pfad | `~/.local/share/RechnungsFee/rechnungsfee.db` |
| Kontenrahmen | SKR03 / SKR04 / SKR49 |
