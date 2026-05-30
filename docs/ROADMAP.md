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

## ✅ Anlage EKS *(Mai 2026)*

Einkommenserklärung für Selbstständige (Jobcenter / Bürgergeld).

**Backend**
- [x] `GET /api/eks/berechnen` – summiert Journalbuchungen nach `eks_kategorie` (abschließend) oder berechnet Halbjahres-Prognose aus Vorjahresdaten (vorläufig)
- [x] `POST /api/eks/pdf` – PDF-Export (fpdf2) mit Tabellen A/B/C, Summen, Ergebniszeile; speichert Export in `eks_exporte`
- [x] Vorläufige EKS: aggregiert monatliche Abschlüsse des Vorjahres-Halbjahres, skaliert auf angeforderten Zeitraum (÷ 6 × N Monate); keine Vorjahresdaten → 0 EUR

**Frontend**
- [x] EksPage (`/eks`): Monats- und Zeitraumauswahl, Vorläufig/Abschließend-Umschalter
- [x] Auto-Felder (aus Journal) vorausgefüllt, manuelle Felder editierbar
- [x] Ergebnis (A − B − C) live berechnet mit farbiger Darstellung
- [x] Quelle-Banner: zeigt Basis der Prognose (Anzahl Vorjahres-Exporte, Skalierung) oder Hinweis bei fehlenden Daten
- [x] DSGVO-Datenauskunft als PDF-Export für Kunden und Lieferanten (`/dsgvo-export-pdf`)

---

## v0.2 – Beleganhang & E-Rechnungs-Import ✅ *v0.2.5*

Eingangsrechnungen mit Beleg belegen, ZUGFeRD/XRechnung automatisch einlesen.

**Stufe 1 – Beleganhang** ✅ *v0.2.1*
- [x] PDF/JPG/PNG an Eingangsrechnung anhängen (Drag & Drop, Datei-Dialog)
- [x] Beleg im eingebetteten Inline-Viewer öffnen
- [x] Beleg löschen
- [x] SHA256-Hash in DB (GoBD-Vorbereitung)

**Stufe 2 – ZUGFeRD/XRechnung-Parsing** ✅ *v0.2.4/v0.2.5*
- [x] `POST /api/rechnungen/analysieren` – liest strukturierte Felder aus E-Rechnung
- [x] `factur-x` + `lxml` als Backend-Abhängigkeiten
- [x] Frontend: „Rechnung importieren"-Workflow mit Vorschau und Vorausfüllung
- [x] Plain PDF: öffnet sich automatisch im systemseitig eingestellten PDF-Viewer
- [x] Originaldatei wird automatisch als Beleganhang gespeichert
- [x] UBL-Format: Lieferantenname aus `PartyLegalEntity/RegistrationName` (Fix v0.2.5)

**Stufe 3 – Validierung & Feld-Mapping** ✅ *v0.2.x*
- [x] Erkannte Felder in Erfassungsformular vorausfüllen
- [x] Niedrige Konfidenz visuell markieren (Konfidenz-Dots, Amber-Ring)
- [x] Abgleich Lieferantenname mit Lieferantenstamm (Fuzzy-Matching, LieferantVorschlagBox)

**Stufe 4 – OCR-Fallback** *(offen)*
- [ ] `pdfplumber` für maschinenlesbare PDFs
- [ ] `pytesseract` für Scans/Fotos
- [ ] Regex-/Heuristik-Extraktion für DE/AT/CH-Formate

**Stufe 5 – GoBD-Export-Erweiterung** *(offen)*
- [ ] `belege.csv` (Manifest mit SHA256) im GoBD-ZIP
- [ ] `belege/`-Ordner mit Original-Dateien im ZIP

---

## v0.2.x – Wiederkehrende Buchungen *(Ziel: offen)*

Monatliche Fixkosten (Miete, Leasing, Abonnements) einmalig als Vorlage anlegen.

- [ ] Vorlagen-Tabelle: Betrag, Kategorie, Intervall (monatlich/quartalsweise/jährlich), nächstes Fälligkeitsdatum, Modus
- [ ] Beim App-Start: Hinweis auf fällige Buchungen („3 Buchungen bereit")
- [ ] **Modus „Direkt"** (kein Beleg-Import): Eingangsrechnung wird als Entwurf angelegt; Ein-Klick-Bestätigung → unbezahlt; Bank-Import (v0.3) schließt ab
- [ ] **Modus „Warte auf Beleg"**: Vorlage legt nur Platzhalter an; PDF-Import (v0.2 Stufe 2) matcht Lieferant + Betrag + Zeitraum → ersetzt Platzhalter durch echte Rechnung mit Beleg; verhindert Duplikate
- [ ] Vorlagen verwalten (anlegen, pausieren, löschen)

---

## v0.3 – Bank-Import *(Ziel: Juni 2026)*

CSV-Import von Kontoauszügen, automatisches Matching.

- [ ] CSV-Parser (Postbank, Sparkasse, Volksbank, Commerzbank)
- [ ] Vorschau und manuelle Zuordnung vor dem Import
- [ ] Auto-Filter-Regeln (Empfänger/Verwendungszweck → Kategorie)
- [ ] Duplikat-Erkennung
- [ ] Import-Protokoll (GoBD: Herkunft nachvollziehbar)

---

## v0.3.x – Automatische USt-Zuordnung *(teilweise erledigt)*

Jeder Journal-Eintrag speichert `ust_betrag` und `konto_ust_skr03/04` (USt-Gegenkonto).
Die Aufteilung in Netto + USt passiert vollautomatisch beim Buchen.

**Grundlage** ✅ *v0.2.5*
- [x] Journal zeigt Netto- und USt-Zeile getrennt
- [x] USt-Gegenkonto wird automatisch gesetzt (SKR03: 1776/1771/1575/1570; SKR04: 3806/3801/1406/1401)
- [x] Gilt für Rechnungszahlungen und manuelle Buchungen

**Noch offen:**
- [x] EKS: A5_1 / A5_2 automatisch aus `ust_betrag` der A1/A2-Einträge ableiten
- [ ] GoBD-Export CSV: USt-Spalte korrekt je Einnahmen-/Ausgaben-Typ befüllen
- [ ] EÜR: USt-Beträge in die richtigen Zeilen der Anlage EÜR einordnen
- [ ] UStVA (v0.4): Voranmeldungs-Kennziffern direkt aus `ust_betrag` + Kategorie befüllen

**Kategorien `USt auf Eigenverbrauch` und `Umsatzsteuer (vereinnahmt)`** bleiben für
manuelle Korrekturbuchungen erhalten, sind im Normalfall aber nicht mehr nötig.

---

## v0.4 – Auswertungen *(Ziel: August 2026)*

Steuerliche Auswertungen für Finanzamt und Steuerberater.

- [ ] EÜR-Berechnung (Einnahmen-Überschuss-Rechnung)
- [ ] UStVA-Voranmeldung (Monat/Quartal)
- [ ] DATEV-Export (CSV nach DATEV-Format)
- [ ] Jahresübersicht (Kategorien-Summen, grafisch)
- [ ] PDF-Export für alle Auswertungen
- [ ] Dashboard individuell konfigurierbar (Kacheln ein-/ausblenden, Reihenfolge, externer Link z.B. Online-Banking) ([#104](https://github.com/nicolettas-muggelbude/RechnungsFee/issues/104))

---

## v0.5 – Erweiterte Digitalisierung *(Ziel: offen)*

Opt-in LLM-gestützte Felderkennung und Sonderfälle.

- [ ] Lokales LLM (ollama) für bessere Feldzuordnung als Opt-in
- [ ] Unterstützung ausländischer Rechnungsformate (AT/CH/EU)

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

## Ideen & Companion-Apps *(unbewertet)*

Lose Ideen ohne festen Versionsplan.

- [ ] **Fahrtenbuch-App (Android/iOS)** – Fahrten erfassen (Start/Ziel/km/Zweck), GoBD-konformes Fahrtenbuch führen, Export an RechnungsFee (Kategorie KFZ-Kosten, direkt als Buchung oder Eingangsrechnung)
  - km-Erfassung via GPS (kein Zusatz-Hardware, für GoBD ausreichend)
  - Optional: OBD-II-Bluetooth-Dongle (~15–30 €) für exakten Tacho-Kilometerstand
  - CarPlay / Android Auto: UI-Oberfläche zum Starten/Stoppen per Knopf/Sprache möglich, aber kein direkter Tacho-Zugriff (CarPlay/Auto sind reine Display-Protokolle)

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
- [x] **Anlage EKS** (Mai 2026): Einkommenserklärung für Selbstständige – abschließend (monatlich aus Journal) und vorläufig (Halbjahres-Prognose aus Vorjahr)
- [x] **v0.2 Stufe 1** (Mai 2026): Beleganhang für Eingangsrechnungen – Upload, Inline-Viewer, Löschen, SHA256 ([v0.2.1](https://github.com/nicolettas-muggelbude/RechnungsFee/releases/tag/v0.2.1))
- [x] **v0.2 Stufe 2** (Mai 2026): ZUGFeRD/XRechnung-Import – Auto-Fill, plain PDF mit Viewer, Beleganhang automatisch ([v0.2.4](https://github.com/nicolettas-muggelbude/RechnungsFee/releases/tag/v0.2.4))
- [x] **EÜR 2025** (Mai 2026): 44 Zeilennummern auf Anlage EÜR 2025 korrigiert, SKR03/04 auf DATEV-Kontenrahmen 2026 (39 Korrekturen)
- [x] **Kategorien editierbar** (Mai 2026): SKR03/04-Konten pro Kategorie anpassbar, Reset, eigene Kategorien anlegen/löschen
- [x] **v0.2.7** (Mai 2026): PDF Gutschriften/negative Mengen korrekt (Einzelpreis, Netto-Spalte, USt-Vorzeichen); Kategorien löschen: fehlende FK-Prüfungen + Fehlermeldung (Issue #96); Linux Mint Cinnamon Mausrad-Scrollen; PDF-Vorlagen Basisklasse `RechnungPDFBase`; 5 fehlende Kategorien ergänzt (Issue #106)
- [x] **v0.2.8** (Mai 2026): Leistungszeitraum Von–Bis (Issue #107); Kategorie-Zuweisung bei Zahlung + Split; PDF-Import bilinguale Rechnungen (Amazon-Format) + EUR-ohne-Leerzeichen; Cinnamon Wizard-Scroll-Fix
- [x] **v0.2.9** (Mai 2026): Skonto (Issue #73) – Standard/Kunden/Rechnung, ZahlungsDialog-Hinweis, PDF-Zeile, zwei Giro-Codes (Vorlage 0+1); POS-Kassenbeleg-Import komplett überarbeitet; Journal: Rechnungsnummer + Rechnungsbuchungen schreibgeschützt; PDF-Import-Fixes (Fälligkeit, Mehrspalten-Modus)
- [x] **Artikelstamm-Gruppen** (Mai 2026): `artikel.kategorie` umbenannt zu `gruppe`; neue Tabelle `artikel_gruppen` mit Typ-Unterscheidung (Warengruppe / Servicegruppe / Fremdleistungsgruppe); FK-Verknüpfung statt Freitext; Gruppenverwaltungs-Modal direkt auf der Artikelseite (Issue #109 Folgemaßnahme)
- [x] **Info-Seite** (Mai 2026): Handbuch-Link (muggelbude.it), Links und „Über" vor den Changelog verschoben
- [x] **v0.2.10** (Mai 2026): Artikelgruppen-Verwaltung (Warengruppe/Servicegruppe/Fremdleistungsgruppe), Skonto-USt-Konto-Fix (Issue #108), gemischte USt-Sätze bei Zahlung (Issue #109)
- [x] **Storno-Begründung** (Mai 2026): Pflichtfeld mit Schnellauswahl; Begründung in `rechnungen.storno_grund` und Journaleintrag; Schema 34
- [x] **Backend-Start nach Update** (Mai 2026): `_backendReady` Promise korrekt abgewartet, Timeout 10 s → 60 s (Defender-Scan / PyInstaller-Extraktion nach Windows-Update)
- [x] **Kategorie-Beschreibungen** (Mai 2026): `kategorien.beschreibung` – ~65 vorbefüllte Verwendungsbeispiele (migriert), inline editierbar auf KategorienPage, Hinweis im Buchungsformular, PDF-Export als Nachschlageblatt; Schema 35
- [x] **v0.2.11** (Mai 2026): Storno-Begründung (Pflichtfeld, Schnellauswahl, `storno_grund` in DB + Journal, Schema 34); Backend-Start-Timeout 10 s → 60 s (Defender-Scan / PyInstaller nach Windows-Update)
- [x] **v0.2.12 – Gutschriften** (Mai 2026, Issue #103): Schema 37 (`dokument_typ`, `gutschrift_zu_rechnung_id`); `POST /rechnungen/{id}/gutschrift` (Positionen negiert, eigene GS-Nummer, Entwurf); Betragslimit (Summe aller Gutschriften ≤ Originalbrutto); Rückerstattung als negative Einnahme im Journal; PDF-Deckblatt „Gutschrift" + Bezugszeile; Storno einer Gutschrift mit GoBD-Gegenbuchung; Frontend: Button, Badge, Detail-Bereich
- [x] **v0.2.13 – §25a UStG** (Mai 2026): Schema 38 (`artikel.differenzbesteuerung`, `rechnungspositionen.differenzbesteuerung`); Margenberechnung live im Artikelformular (Ankaufspreis, Marge, USt auf Marge); §25a-Badge in Artikelliste + Autocomplete-Dropdown; gemischte Rechnungen (§25a + Regelbesteuerung); PDF-Pflichthinweis nach § 25a UStG (multi_cell, kein Überlauf); Scroll-Layout-Fix (Header + Detailspalte fest, Liste scrollt); Storno-Buchungen: Betrag immer positiv, Art korrekt für Gutschriften
