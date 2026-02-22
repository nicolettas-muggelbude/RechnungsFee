# Roadmap – RechnungsFee

> Ziel: GoBD-konformes Kassenbuch für Kleinunternehmer, Freiberufler und Vereine.
> Tech-Stack: Tauri + React + FastAPI + SQLite

---

## v0.1 – Kassenbuch *(Ziel: April 2026)*

Kern-Funktion: Einnahmen und Ausgaben manuell erfassen.

**Backend**
- [ ] Kassenbuch-API (CRUD: Einnahmen/Ausgaben, Kategorisierung)
- [ ] Kunden- und Lieferanten-API
- [ ] Tagesabschluss (GoBD: unveränderlich nach Abschluss)
- [ ] USt-Berechnung bei Buchungserstellung

**Frontend**
- [ ] Kassenbuch-Ansicht (Liste, Filter nach Monat/Kategorie)
- [ ] Buchung erfassen (Formular mit Kategorie, Belegnummer, Betrag, USt)
- [ ] Kunden-/Lieferantenverwaltung (einfach)
- [ ] Tagesabschluss-Dialog
- [ ] Dashboard mit Monatsübersicht (Einnahmen / Ausgaben / Saldo)

---

## v0.2 – Bank-Import *(Ziel: Juni 2026)*

CSV-Import von Kontoauszügen, automatisches Matching.

- [ ] CSV-Parser (Postbank, Sparkasse, Volksbank, Commerzbank)
- [ ] Vorschau und manuelle Zuordnung vor dem Import
- [ ] Auto-Filter-Regeln (Empfänger/Verwendungszweck → Kategorie)
- [ ] Duplikat-Erkennung
- [ ] Import-Protokoll (GoBD: Herkunft nachvollziehbar)

---

## v0.3 – Auswertungen *(Ziel: August 2026)*

Steuerliche Auswertungen für Finanzamt und Steuerberater.

- [ ] EÜR-Berechnung (Einnahmen-Überschuss-Rechnung)
- [ ] UStVA-Voranmeldung (Monat/Quartal)
- [ ] DATEV-Export (CSV nach DATEV-Format)
- [ ] Jahresübersicht (Kategorien-Summen, grafisch)
- [ ] PDF-Export für alle Auswertungen

---

## v1.0 – Release *(Ziel: Oktober 2026)*

Produktionsreife Desktop-App für Windows, Linux und macOS.

- [ ] Tauri-Build (Windows `.msi`, Linux `.deb`/`.AppImage`, macOS `.dmg`)
- [ ] Automatisches Backup (täglich, konfigurierbarer Pfad)
- [ ] Datenwiederherstellung aus Backup
- [ ] Einstellungen-Seite (Unternehmen, Konten, Kategorien)
- [ ] Hilfe-System / Onboarding-Tooltips
- [ ] DSGVO: Datenexport und -löschung

---

## v1.1 – Rechnungen *(Ziel: Dezember 2026)*

Rechnungen erstellen und externe Programme anbinden.

- [ ] LibreOffice-ODT-Rechnungsvorlage (generiert aus Kassenbuch-Daten)
- [ ] Vollständige Kundenverwaltung (inkl. Vereins-Felder, Issue #14)
- [ ] ZUGFeRD-Export (elektronische Rechnung)
- [ ] hellocash REST-API Anbindung (Issue #13)

---

## Bereits erledigt

- [x] Projektvision und Dokumentation (`docs/`)
- [x] Datenbankschema (SQLAlchemy 2.0, GoBD-konform, 16 Tabellen)
- [x] Backend-API: Setup, Unternehmen, Konten, Kategorien
- [x] Frontend: Setup-Assistent (3-stufiger Wizard)
- [x] 31 Standard-Kategorien (SKR03/04/49, EÜR-Zuordnung)
- [x] 27 EU-Länder mit USt-Sätzen (Seed-Daten)
