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

**Stufe 4 – OCR-Fallback** ✅ *v0.2.16*
- [x] `pdfplumber` für maschinenlesbare PDFs (bessere Tabellen-/Spaltenextraktion)
- [x] `pytesseract` + `pymupdf` für Scans/Fotos (graceful fallback wenn tesseract fehlt)
- [x] Regex-/Heuristik-Extraktion für DE/AT/CH-Formate (war bereits vorhanden)

**OCR-Qualitätsverbesserungen** ✅ *v0.2.17–v0.2.19*
- [x] Belegtyp-Erkennung (Kassenbon / Tankquittung / Rechnung) – strukturbasiert, markenunabhängig
- [x] Kassenbons: A/B-Steuerklassen-Voreinstellung (A=19%, B=7%) – robust gegen OCR-Fehllesungen
- [x] Tankquittungen: Produktname, Literanzahl, Brutto-Modus, USt-Inference aus Brutto/Netto-Ratio
- [x] Summenlabels generalisiert: `{*}preis Netto/Brutto` werden nie als Positionen importiert
- [x] Lieferant-Matching: Backend-Vorschlag direkt übernommen, Fuzzy-Match mit Rechtsformbereinigung
- [x] ZUGFeRD/XRechnung: PDF zur Kontrolle automatisch geöffnet

**Stufe 5 – GoBD-Export-Erweiterung + PDF/A-Archivierung** ✅ *v0.2.20*
- [x] `belege.csv` (Manifest mit SHA256) im GoBD-ZIP
- [x] `belege/`-Ordner mit Belegdateien im ZIP (PDF/A bevorzugt, sonst Original)
- [x] PDF/A-3-Konvertierung nach Upload (Hintergrundthread, graceful ohne Ghostscript)
- [x] ZUGFeRD/XRechnung sofort als PDF/A-3 markiert (sind es per Norm)
- [x] „✓ PDF/A-3 (GoBD-Archiv)"-Link in der Beleg-Detailansicht

---

## v0.2.21 – UX-Verbesserungen ✅ *v0.2.21*

- [x] Rechnungsliste: Büroklammer-Icon wenn Eingangsrechnung einen Beleg hat (#123)
- [x] Rechnungsliste: Keyboard-Navigation – Pfeiltasten + Tab mit focus-visible Ring (#125)
- [x] Journal: Summenzeile (Einnahmen / Ausgaben / Saldo) (#122)
- [x] Formulare: Kategorie, Lieferant, Kunde, Artikel direkt anlegen ohne Seitenwechsel (#120)
- [x] Beleg-Anhang nur für Eingangsrechnungen (Ausgangsrechnungen: App generiert PDF selbst)
- [x] OCR: Vodafone/Telekommunikationsrechnungen (#119)
- [x] GoBD-Export: Belege-Fallback via rechnung.beleg_id (#124)

---

## v0.2.x – Wiederkehrende Buchungen *(Ziel: offen)*

Monatliche Fixkosten (Miete, Leasing, Abonnements) einmalig als Vorlage anlegen.

- [ ] Vorlagen-Tabelle: Betrag, Kategorie, Intervall (monatlich/quartalsweise/jährlich), nächstes Fälligkeitsdatum, Modus
- [ ] Beim App-Start: Hinweis auf fällige Buchungen („3 Buchungen bereit")
- [ ] **Modus „Direkt"** (kein Beleg-Import): Eingangsrechnung wird als Entwurf angelegt; Ein-Klick-Bestätigung → unbezahlt; Bank-Import (v0.3) schließt ab
- [ ] **Modus „Warte auf Beleg"**: Vorlage legt nur Platzhalter an; PDF-Import (v0.2 Stufe 2) matcht Lieferant + Betrag + Zeitraum → ersetzt Platzhalter durch echte Rechnung mit Beleg; verhindert Duplikate
- [ ] Vorlagen verwalten (anlegen, pausieren, löschen)

---

## v0.4 – Angebot & Auftrag (geplant)

Vollständiger B2B-Workflow: Angebot → Auftragsbestätigung → Lieferschein → Rechnung.
Details: [docs/plan-angebot-auftrag.md](plan-angebot-auftrag.md)

### Stufe 1 – Navigation + Dokumentenpakete ✅ *Juni 2026*

- [x] Navigation umgebaut: Sektionen Verkauf / Einkauf / Auswertung / Stammdaten
- [x] Lieferscheine als eigener Sidebar-Menüpunkt (`/lieferscheine`)
- [x] Platzhalter für Angebote & Aufträge (ausgegraut, „bald")
- [x] Auswertung (EÜR, UStVA, ZM, EKS, Exporte) als ausklappbare Sektion sichtbar
- [x] Dokumentenpakete (Schema 54): wiederverwendbare Anhang-Gruppen für Angebote/AB
  - Tabellen `dokumentenpakete` + `dokumentenpaket_belege`
  - CRUD-API + Stammdaten-Seite
  - Upload PDF/Bild direkt ins Paket

### Stufe 2 – Angebote *(geplant)*

- [ ] `dokument_typ = 'Angebot'`, Nummernkreis `ANG-JJJJ####`
- [ ] Angebot → Rechnung oder Auftrag umwandeln
- [ ] E-Mail-Versand mit Dokumentenpaket-Anhängen
- [ ] Status: offen / akzeptiert / abgelehnt / abgelaufen

### Stufe 3 – Aufträge + Auftragsbestätigung *(geplant)*

- [ ] `dokument_typ = 'Auftrag'`, Nummernkreis `AUF-JJJJ####`
- [ ] Auftragsbestätigung-PDF mit Anhängen aus Dokumentenpaket
- [ ] Auftrag → Lieferschein oder Rechnung
- [ ] Status-Tracking + optionaler Onlineshop-Webhook

---

## v0.3.3 – Lieferadressen & Lieferscheine ✅ *v0.3.3 – Juni 2026*

- [x] Lieferadressen im Kundenstamm (Schema 51): eigene Tabelle `kunden_lieferadressen`; Tab im Kunden-Detail; Standard-Adresse-Flag; Dropdown beim Lieferschein
- [x] Lieferscheine aktivieren/deaktivieren (Einstellungen → Unternehmen) – Schema 52
- [x] Lieferschein-PDF: Positionen mit Menge/Einheit, kein Preis; Lieferadresse im Kopf; Empfangsbestätigung-Block (Datum/Ort + Unterschrift Warenempfänger)
- [x] Nummernkreis `LS-YY####` (Seed); im Nummernkreise-Tab versteckt wenn Funktion inaktiv
- [x] Lieferschein → Einzelrechnung (Entwurf mit allen Positionen, Preise ergänzen)
- [x] Sammelrechnung: mehrere Lieferscheine eines Kunden zusammenfassen; Leistungszeitraum-Vorausfüllung; Dialog schließt nach Erstellen automatisch
- [x] Lieferschein aus Rechnung (Vorkasse): finalisierte RE → Lieferschein; Positionen ohne Preis; max. 1 LS pro RE (409 + ausgegrauter Button)
- [x] Schema 53: `rechnungen.lieferadresse_id` FK
- [x] Bidirektionale Navigation: LS-Detail → RE-Button; RE-Detail → LS-Button mit Filter in Lieferschein-Übersicht
- [x] Lieferschein-Übersicht: „Fällig am" + „Brutto" entfernt; neue Spalte „Rechnung"; Suche um Rechnungsnummer erweitert

---

## v0.3.1 – Fixes & ZM ✅ *v0.3.1 – Juni 2026*

- [x] §25a Differenzbesteuerung: Margensteuer korrekt im Journal (USt nur auf Brutto-Marge, Schema 50)
- [x] §25a: Kategorie „Wareneinkauf §25a (privat)" – 0% USt, kein Vorsteuerabzug
- [x] ZM – Zusammenfassende Meldung §18a UStG: Dashboard-Hinweis, Exporte-Kachel bei Fälligkeit, ZM-Seite mit ig. Lieferungen (L) + §13b Abs.1 (D) gruppiert nach USt-IdNr.
- [x] Unterschrift (#129): Upload-Tab (JPG/PNG/WebP) + Download als PNG (Backup Neuinstallation)
- [x] Steuersätze (#128): 0%/7%/19% jetzt als Seed (Neuinstallation), Umbenennung MwSt-Sätze → Steuersätze
- [x] Rechnungsliste (#125): Tastaturfokus – ausgewählte Zeile bg-blue-100/slate-600 + blauer Balken links

---

## v0.3 – Buchhalterische Vollständigkeit ✅ *v0.3.0 – Juni 2026*

### Phase 1 – Korrekturbuchungen ✅ *v0.2.15*

- [x] Buchungen ohne Geldfluss (`zahlungsart='Keine'`) – für AfA, Sachentnahmen, Eigenverbrauch (Issue #55)
- [x] Forderungsausfall mit §17-UStG-Korrekturbuchung und Status „Uneinbringlich" (Issue #61)
- [x] `vorsteuer_betrag`-Snapshot im Journal (tatsächlich abziehbarer Vorsteueranteil je Kategorie)
- [x] Neue Kategorien: Forderungsausfall (SKR03 4803/SKR04 6403), KFZ (Kauf) (SKR03 0320/SKR04 0540), Bewirtungskosten (nicht abzugsfähig)
- [x] EDV/Software (Sofortabschreibung): Kontenart Aufwand → Anlage (SKR03 0650), korrekte Buchungslogik (zweistufig: Kauf + AfA) nach BMF 2021 (Issue #111)
- [x] Einkommensteuer-Vorauszahlung: Fälligkeitsmonate korrigiert (März/Jun/Sep/Dez)

### Phase 2 – EÜR ✅ *v0.3.2*

- [x] EÜR-Berechnung aus Journalbuchungen nach Anlage EÜR 2025 (Zuflussprinzip)
- [x] EÜR-Summen je Zeilennummer: netto_betrag je euer_zeile, Zeile 15 aus ust_betrag, Zeile 48 aus vorsteuer_betrag
- [x] PDF-Export Anlage EÜR (strukturierter Bericht mit Zeilennummern, Anzeigehilfe)
- [x] Hinweis auf Anlage AVEUR wenn Anlagezugänge vorhanden
- [ ] Jahresübersicht: Kategorien-Summen mit EÜR-Zuordnung (noch offen)
- [ ] Anlage AVEUR – Abschreibungsplan für Anlagegüter (spätere Version)

---

## v0.3.x – Automatische USt-Zuordnung ✅ *v0.3*

Jeder Journal-Eintrag speichert `ust_betrag` und `konto_ust_skr03/04` (USt-Gegenkonto).
Die Aufteilung in Netto + USt passiert vollautomatisch beim Buchen.

**Grundlage** ✅ *v0.2.5*
- [x] Journal zeigt Netto- und USt-Zeile getrennt
- [x] USt-Gegenkonto wird automatisch gesetzt (SKR03: 1776/1771/1575/1570; SKR04: 3806/3801/1406/1401)
- [x] Gilt für Rechnungszahlungen und manuelle Buchungen

**UStVA-Anzeigehilfe** ✅ *v0.3*
- [x] UStVA-Backend: KZ-Berechnung aus Journal (`ust_betrag`, `ust_sonderfall`, `marge_25a_brutto`)
- [x] KZ 81/83 (19%), KZ 86/88 (7%), KZ 41 (ig. Lieferungen), KZ 89/93/61 (ig. Erwerb)
- [x] KZ 35/36 (§13b Bauleistungen / EU-Dienstleistungen)
- [x] §25a Differenzbesteuerung: `marge_25a_brutto` im Journal; USt auf Brutto-Marge, nicht auf VK-Preis
- [x] UStVA-PDF: Anzeigehilfe zum manuellen Eintragen in ELSTER
- [x] Voranmeldungsrhythmus (monatlich / quartalsweise) in Stammdaten
- [x] EKS: A5_1 / A5_2 automatisch aus `ust_betrag` der A1/A2-Einträge ableiten

**Noch offen:**
- [ ] GoBD-Export CSV: USt-Spalte korrekt je Einnahmen-/Ausgaben-Typ befüllen
- [ ] EÜR: USt-Beträge in die richtigen Zeilen der Anlage EÜR einordnen

**Kategorien `USt auf Eigenverbrauch` und `Umsatzsteuer (vereinnahmt)`** bleiben für
manuelle Korrekturbuchungen erhalten, sind im Normalfall aber nicht mehr nötig.

---

## v0.4 – Bank-Import *(Ziel: Sommer 2026)*

CSV-Import von Kontoauszügen, automatisches Matching.

- [ ] CSV-Parser (Postbank, Sparkasse, Volksbank, Commerzbank)
- [ ] Vorschau und manuelle Zuordnung vor dem Import
- [ ] Auto-Filter-Regeln (Empfänger/Verwendungszweck → Kategorie)
- [ ] Duplikat-Erkennung
- [ ] Import-Protokoll (GoBD: Herkunft nachvollziehbar)

---

## v0.5 – Erweiterte Auswertungen *(Ziel: Herbst 2026)*

Steuerliche Auswertungen für Finanzamt und Steuerberater.

- [ ] UStVA-Voranmeldung (Monat/Quartal)
- [ ] DATEV-Export (CSV nach DATEV-Format)
- [ ] Jahresübersicht (Kategorien-Summen, grafisch)
- [ ] PDF-Export für alle Auswertungen
- [ ] Dashboard individuell konfigurierbar (Kacheln ein-/ausblenden, Reihenfolge, externer Link z.B. Online-Banking) ([#104](https://github.com/nicolettas-muggelbude/RechnungsFee/issues/104))

---

## v0.x – Erweiterbare Kontenpläne *(Ziel: offen)*

Optionale DATEV-Kontenpläne und nutzereigene Pläne per CSV.

**Konzept:**
- Die bestehenden ~65 Standardkategorien (SKR03/04) bleiben die Basis – immer aktiv, nicht ersetzbar
- Zusätzliche Kontenpläne kommen optional obendrauf, ohne Duplikate

**Zwei Quellen für erweiterte Pläne:**

1. **Built-in-Pakete** – von RechnungsFee bereitgestellt, aus den Einstellungen heraus installierbar (ein Klick, kein Datei-Upload):
   - z.B. „SKR03 vollständig (800+ Konten)" oder branchenspezifische Pakete
   - Werden als Seed-Datei im App-Bundle mitgeliefert
   - Aktivierung speichert die neuen Kategorien in der lokalen DB

2. **CSV-Import durch den User** – eigene Kontenpläne hochladen und aktivieren:
   - Format: `name, kontenart, konto_skr03, konto_skr04, ust_satz_standard, vorsteuer_prozent, euer_zeile, eks_kategorie`
   - Vorschau vor dem Import (Duplikat-Erkennung anhand Name + Kontonummer)
   - Aktivieren / Deaktivieren einzelner importierter Kategorien
   - Export der aktuellen Kategorien als CSV (Backup / Weitergabe)

**Technische Umsetzung (Idee):**
- `kategorien.quelle VARCHAR(20)` – `system` | `built-in-paket` | `user-csv`
- `kategorien.paket_name VARCHAR(100)` – z.B. „SKR03-vollständig"
- Pakete können vollständig deinstalliert werden (nur `quelle ≠ system`-Einträge ohne Buchungen)
- Konflikt-Strategie: gleicher Name → überspringen; gleiches Konto, anderer Name → beide behalten

---

## v0.6 – Erweiterte Digitalisierung *(Ziel: offen)*

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
- [x] **v0.2.14 – Korrekturbuchungen Phase 1** (Mai 2026): Buchungen ohne Geldfluss `zahlungsart='Keine'` (Issue #55); Forderungsausfall §17 UStG mit Status „Uneinbringlich" (Issue #61); `vorsteuer_betrag`-Snapshot; Kategorien Forderungsausfall + KFZ (Kauf) + Bewirtungskosten (nicht abzugsfähig); EDV/Software Aufwand→Anlage nach BMF 2021 (Issue #111); Schema 42
- [x] **v0.2.15 – km-Pauschale EKS** (Mai 2026): `journal.km_anzahl` (Schema 43); BuchungForm km-Eingabe bei B6_5 (EÜR km×0,30, EKS-Vorschau km×0,10); EKS B6_5 auto-Berechnung km×0,10; EKS B6_4_priv (privat gefahrene km Betriebs-KFZ, Abzugsposten); GoBD-Hash erweitert
- [x] **v0.2.16 – OCR für gescannte Belege** (Juni 2026): pdfplumber + pytesseract + pymupdf (Stufe 4); Tesseract-Installation per NSIS-Installer (Windows) und install-linux.sh; OcrInstallHinweis-Banner wenn Tesseract fehlt; PDFs in eigenem OS-Fenster; Journal→Rechnung-Link
- [x] **v0.2.17 – Tesseract-Assistent** (Juni 2026): TesseractAssistentModal mit State-Machine (Ein-Klick-Install via winget/pkexec/apt/dnf/pacman ohne Terminal); NSIS-Installer fragt per Dialog statt still zu installieren; Tesseract-Pfaderkennung auch wenn PATH noch nicht aktualisiert (Issue #115)
- [x] **v0.2.18 – OCR-Parser-Fixes Tankquittung** (Juni 2026): Produktname + Menge (Super 95 / 32,69 l) aus Tankquittungen extrahiert (Einzeiler + Mehrzeiler); Sternchen-Bereinigung; „SUMME EUR 30,85" als Rechnungsbetrag erkannt
- [x] **v0.2.19 – OCR-Parser-Fixes Kassenbons** (Juni 2026): Tesseract-Artefakt „25, 95" (Leerzeichen nach Komma) vor Auswertung bereinigt; USt-Aufschlüsselungs-Tabellenzeilen mit Dezimalrate (z.B. „fz 19,0% 4,12 6,78 4,90") werden nicht mehr als Positionen importiert
- [x] **v0.2.20 – GoBD-Belege + PDF/A-Archivierung** (Juni 2026): GoBD-ZIP enthält jetzt belege.csv + belege/-Ordner; PDF/A-3-Konvertierung via ocrmypdf (Hintergrundthread, graceful ohne Ghostscript); ZUGFeRD/XRechnung sofort als PDF/A-3 markiert; PDF/A-Link in Beleg-Detailansicht; install-linux.sh Ghostscript-Check
- [x] **v0.3.3 – Lieferadressen & Lieferscheine** (Juni 2026, Issue #25): Lieferadressen im Kundenstamm (Schema 51); Lieferschein-PDF ohne Preise + Lieferadresse + Empfangsbestätigung (Schema 52); LS→Rechnung, LS→Sammelrechnung, RE→Lieferschein (Vorkasse); bidirektionale Navigation + Filter; Lieferschein-Übersicht Rechnungsnummer-Spalte + Suche; Nummernkreis-Tab ausgeblendet wenn inaktiv; Schema 53
