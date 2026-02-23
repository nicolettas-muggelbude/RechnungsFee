# Roadmap – RechnungsFee

> Ziel: GoBD-konformes Kassenbuch für Kleinunternehmer, Freiberufler und Vereine.
> Tech-Stack: Tauri + React + FastAPI + SQLite

---

## ✅ v0.1 – Kassenbuch *(Released: Februar 2026)*

Kern-Funktion: Einnahmen und Ausgaben manuell erfassen.

**Backend**
- [x] Kassenbuch-API (Einnahmen/Ausgaben, Kategorisierung, Storno als Gegenbuchung)
- [x] Kunden- und Lieferanten-API
- [x] Tagesabschluss (GoBD: unveränderlich nach Abschluss, Soll/Ist-Differenz)
- [x] USt-Berechnung aus Bruttobetrag (ROUND_HALF_UP), Kleinunternehmer §19 automatisch

**Frontend**
- [x] Kassenbuch-Ansicht (Liste, Filter nach Monat/Kategorie/Art)
- [x] Buchung erfassen (Formular mit Live-USt-Vorschau, Belegnummer KB-YYYYMMDD-NNN)
- [x] Kunden-/Lieferantenverwaltung
- [x] Tagesabschluss-Dialog (Vorschau, Ist-Bestand, Differenz-Begründung)
- [x] Dashboard mit Monatsübersicht (Einnahmen / Ausgaben / Saldo)
- [x] AppLayout mit Sidebar-Navigation

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

## v1.1 – Rechnungsbücher & Import *(Ziel: Dezember 2026)*

Eingangs- und Ausgangsrechnungen verwalten, elektronische Rechnungsformate importieren.

**Rechnungseingangsbuch**
- [ ] Eingangsrechnungen erfassen und verwalten (Lieferant, Betrag, Fälligkeit, Zahlungsstatus)
- [ ] ZUGFeRD / XRechnung / PDF importieren (inkl. OCR-Texterkennung bei normalen PDFs)
- [ ] Automatische Kassenbuchung vorschlagen (bei Barzahlung)
- [ ] Verknüpfung Eingangsrechnung ↔ Kassenbucheintrag sichtbar

**Rechnungsausgangsbuch**
- [ ] Ausgangsrechnungen erfassen und verwalten (Kunde, Betrag, Fälligkeit, Zahlungsstatus)
- [ ] ZUGFeRD-Export (elektronische Rechnung)
- [ ] LibreOffice-ODT-Rechnungsvorlage (generiert aus Stammdaten + Buchung)
- [ ] Automatische Kassenbuchung vorschlagen (bei Bareinnahme)
- [ ] Verknüpfung Ausgangsrechnung ↔ Kassenbucheintrag sichtbar

**Sonstiges**
- [ ] Vollständige Kundenverwaltung (inkl. Vereins-Felder, Issue #14)
- [ ] hellocash REST-API Anbindung (Issue #13)

---

## Bereits erledigt

- [x] Projektvision und Dokumentation (`docs/`)
- [x] Datenbankschema (SQLAlchemy 2.0, GoBD-konform, 16 Tabellen)
- [x] Backend-API: Setup, Unternehmen, Konten, Kategorien
- [x] Frontend: Setup-Assistent (3-stufiger Wizard)
- [x] 31 Standard-Kategorien (SKR03/04/49, EÜR-Zuordnung)
- [x] 27 EU-Länder mit USt-Sätzen (Seed-Daten)
- [x] **v0.1 Kassenbuch** – Released Februar 2026 ([Release-Notes](https://github.com/nicolettas-muggelbude/RechnungsFee/releases/tag/v0.1))
