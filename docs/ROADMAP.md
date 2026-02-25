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

## ✅ Post-v0.1 – Erweiterungen *(Februar 2026)*

Features, die nach dem v0.1-Release umgesetzt wurden.

**Backend**
- [x] Split-Buchung (atomare Mehrfach-Buchung, min. 2 Positionen, `/kassenbuch/split`)
- [x] Nummernkreise: konfigurierbare Belegnr-Präfixe (KB-YYYYMMDD-NNN, RE-YY####, ER-YY####)
- [x] GoBD-Export: `GET /api/export/gobd?jahr=YYYY` → ZIP mit 8 Dateien (CSV + PDF-Prüfbericht)
- [x] Rechnungen-API: Eingangs- und Ausgangsrechnungen CRUD mit Positionen, automatische Summenberechnung
- [x] Verknüpfung Rechnung ↔ Kassenbucheintrag (`POST /{id}/zahlung-bar`, Bar/Karte/PayPal)
- [x] Teilzahlungs-Tracking: `bezahlt_betrag`, `zahlungsstatus` (offen / teilweise / bezahlt)

**Frontend**
- [x] Split-Buchung im BuchungForm (eigener Modus im selben Modal)
- [x] Brutto/Netto-Umschalter im Kassenbuch-Buchungsformular (nicht für §19)
- [x] Dashboard-Zeitfilter (Monat / Tag / Zeitraum)
- [x] Externe Belegnr. im Buchungsformular
- [x] Vorsteuerabzug automatisch nach Kategorie
- [x] TagesabschlussPage: Liste aller Abschlüsse, PDF-Export, Differenz-Statistik
- [x] ExportPage (`/exporte`): GoBD-Export mit Jahresauswahl
- [x] RechnungenPage (`/rechnungen`): Tabs Eingang/Ausgang, Positionsformular mit Brutto/Netto-Umschalter, Detail-Panel, Zahlungs-Dialog, Fortschrittsbalken, Link zu Kassenbuch-Einträgen

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

## v1.1 – Rechnungen – Ausgabe & Import *(Ziel: Dezember 2026)*

Rechnungs-PDF ausgeben und elektronische Rechnungsformate importieren.

**Bereits umgesetzt (vorgezogen)**
- [x] Eingangs- und Ausgangsrechnungen erfassen (Positionen, Fälligkeit, Zahlungsstatus)
- [x] Kassenbuchung bei Bar-/Kartenzahlung direkt aus der Rechnung erstellen
- [x] Verknüpfung Rechnung ↔ Kassenbucheintrag in beiden Richtungen sichtbar

**Noch offen**
- [ ] Rechnungs-PDF ausgeben (Ausgangsrechnung als druckfertiges PDF)
- [ ] ZUGFeRD-Export (elektronische Rechnung nach EN 16931)
- [ ] ZUGFeRD / XRechnung / PDF importieren (inkl. OCR-Texterkennung)
- [ ] Vollständige Kundenverwaltung (inkl. Vereins-Felder, Issue #14)
- [ ] hellocash REST-API Anbindung (Issue #13)

---

## Bereits erledigt

- [x] Projektvision und Dokumentation (`docs/`)
- [x] Datenbankschema (SQLAlchemy 2.0, GoBD-konform, 16 Tabellen)
- [x] Backend-API: Setup, Unternehmen, Konten, Kategorien
- [x] Frontend: Setup-Assistent (4-stufiger Wizard inkl. Kassenbestand)
- [x] 31 Standard-Kategorien (SKR03/04/49, EÜR-Zuordnung)
- [x] 27 EU-Länder mit USt-Sätzen (Seed-Daten)
- [x] **v0.1 Kassenbuch** – Released Februar 2026 ([Release-Notes](https://github.com/nicolettas-muggelbude/RechnungsFee/releases/tag/v0.1))
- [x] **Post-v0.1**: Split-Buchung, GoBD-Export, Rechnungen (Eingang/Ausgang) mit Kassenbuch-Verknüpfung
