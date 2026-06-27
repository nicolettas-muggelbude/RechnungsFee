# Roadmap – RechnungsFee

> Ziel: GoBD-konformes Buchhaltungsprogramm für Kleinunternehmer, Freiberufler und Vereine.
> Tech-Stack: Tauri + React + FastAPI + SQLite

---

## ✅ Abgeschlossen

**Kassenbuch & Journal**
- Einnahmen/Ausgaben erfassen, Kategorisierung, Split-Buchungen
- Tagesabschluss (GoBD: unveränderlich nach Abschluss)
- Buchungen ohne Geldfluss (AfA, Sachentnahmen), Forderungsausfall §17 UStG
- km-Pauschale (Journal-Feld `km_anzahl`, EÜR × 0,30 €, EKS × 0,10 €)
- §25a Differenzbesteuerung (Margensteuer, Ankaufspreis, EK-Preis auf Position)
- Innergemeinschaftlicher Erwerb §1a + §13b Reverse-Charge

**Rechnungen**
- Eingangs- und Ausgangsrechnungen mit Positionen, Zahlungsstatus, Teilzahlungen
- Gutschriften (negativierte Positionen, GoBD-Gegenbuchung, Betragslimit, eigener Nummernkreis GS-YY####)
- Storno mit Pflichtbegründung, GoBD-Gegenbuchung und eigener Stornorechnung-Nummer (STORNO-JJNNNN); Stornorechnung-PDF mit negativen Beträgen, Stornodatum, Bezugszeile; Detail-Panel: Ansehen = Original-Rechnung, Stornorechnung drucken / senden (Issue #178)
- Skonto (Standard, Kunden, Rechnung; Zahlungshinweis + Giro-Code)
- Rechnungsrabatt als Festbetrag (€): Toggle % / € im Formular, immer Bruttobetrag, PDF zeigt „Abzug"
- Artikelcode (SKU/EAN) auf Rechnung: optionale „Art.-Nr."-Spalte im PDF wenn Artikel einen Code haben; Detail-Panel zeigt Code unter Positionsbeschreibung
- Mehrzeilige Positionsbeschreibung: Textarea im Formular wächst automatisch mit; Zeilenumbrüche (Enter) erscheinen im PDF (beide Vorlagen, Lieferschein, Angebot, Auftrag, Proforma)
- Leistungszeitraum Von–Bis
- Original-PDF-Archivierung: erstes Drucken/Mailen speichert das Original; alle weiteren Ausgaben sind Kopien mit rotem KOPIE-Wasserzeichen (Entwurf: nur Vorschau)
- Versand-Zeitstempel (`ausgegeben_am`): Detail-Panel zeigt Datum + Uhrzeit des ersten Versands als Nachweis
- Einmalkunden: Freitext-Modus (kein Stammdatensatz) in allen Dokumenttypen (Rechnung, Angebot, Auftrag, Proforma) mit optionaler Adresse (Straße, Hausnummer, PLZ, Ort, Land) für den PDF-Adressblock; Kundenfeld überall als Combobox mit Autocomplete (Issue #188)

**Lieferscheine**
- Lieferschein-PDF ohne Preise, mit Lieferadresse und Empfangsbestätigung
- Lieferschein aus Rechnung (Vorkasse), Lieferschein → Rechnung, Sammelrechnung
- Lieferadressen im Kundenstamm (separate Tabelle, Standard-Flag)
- Bidirektionale Navigation Lieferschein ↔ Rechnung

**Angebote**
- Angebot erstellen, drucken, per E-Mail versenden
- Entwurf-Modus: Entwurf speichern (ohne Nummer), Finalisieren-Button vergibt Nummer
- Status: offen / akzeptiert / abgelehnt / abgelaufen
- Rechnung, Lieferschein oder Proforma aus Angebot (nur bei Status „Akzeptiert")
- Rückverlinkung: Angebot zeigt erstellten Lieferschein / Rechnung / Proforma als Link
- Dokumentenpakete (Anhänge wie AGB, DSE, LV) als Angebot-Beilage

**Aufträge**
- Auftragsbestätigung-PDF (Nummernkreis `AU-JJNNNN`, kein Kopie-Banner)
- Status-Workflow: offen → in Bearbeitung → Rechnung → abgeschlossen (automatisch: Rechnung finalisiert → „Rechnung"; Rechnung bezahlt → „Abgeschlossen", alle 3 Pfade: direkt / via Proforma / via Lieferschein)
- Auftrag direkt erstellen oder aus akzeptiertem Angebot
- Auftrag → Rechnung / Lieferschein / Proforma
- Bearbeiten ab Status „in Bearbeitung" gesperrt; neue Dokumente bei abgeschlossen/storniert gesperrt
- Bidirektionale Verlinkung Angebot ↔ Auftrag ↔ Folgedokumente

**Proforma-Rechnungen**
- Proforma-Rechnung (Vorkasse-Aufforderung) – direkt erstellen oder aus einem akzeptierten Angebot
- Entwurf-Modus: Entwurf speichern (ohne Nummer), Finalisieren-Button vergibt Nummer
- Zahlungsblock im PDF mit IBAN und Zahlungsziel (aus Unternehmenseinstellungen)
- Kein Skonto, keine Unterschrift (Vorkasse: Zahlung kommt vor Leistung)
- Alterswarnung in der Übersicht: Proformas >14 Tage offen werden amber markiert
- **Zahlung eingegangen:** Zahlungsart + Datum wählen → Journaleintrag wird gebucht, Rechnung automatisch als bezahlt angelegt
- Bidirektionale Verlinkung: Angebot ↔ Proforma ↔ Rechnung
- Proforma-Übersicht aus Angebot heraus automatisch auf das neue Dokument gefiltert
- Angebot sperrt „→ Rechnung" und „→ Lieferschein" sobald eine Proforma existiert

**Belege & Import**
- Beleganhang an Eingangsrechnungen (PDF/JPG/PNG, SHA256, Inline-Viewer)
- ZUGFeRD / XRechnung / UBL-Import mit Auto-Fill + Fuzzy-Matching
- OCR-Fallback (pdfplumber + Tesseract) für Scans, Fotos, Kassenbons, Tankquittungen
- PDF/A-3-Archivierung (GoBD-Stufe 5), GoBD-ZIP mit Belegordner

**Exporte**
- ZUGFeRD-Export für Ausgangsrechnungen (EN 16931, PDF/A-3 mit XML-Einbettung, XRechnung 3.0)
- Kassenbuch-Export (PDF mit Unterschrift + CSV) für Bar-Kasse
- Journal-Export (PDF + CSV) mit allen Filtern – Filtereinstellungen im Dokument dokumentiert

**Auswertungen & Exporte**
- UStVA-Anzeigehilfe (KZ 81/83/86/88/41/89/93/61/35/36, monatl./quartalsweise)
- Zusammenfassende Meldung ZM §18a (ig. Lieferungen + §13b)
- EÜR nach Anlage EÜR 2025 (Zuflussprinzip, Zeilen A+B, Gewinn/Verlust)
- Anlage EKS (abschließend + vorläufige Halbjahresprognose)
- GoBD-Export (ZIP: Journal-CSV, Belegordner, belege.csv mit SHA256)
- DSGVO-Datenauskunft als PDF (Kunden und Lieferanten)

**Stammdaten & Einstellungen**
- Kunden, Lieferanten, Artikel, Artikelgruppen
- Lagerführung-Light: Bestandsführung pro Artikel (global + pro Artikel aktivierbar, Mindestbestand-Schwellwert, automatische Buchung bei Finalisierung/Storno, Inline-Bearbeitung im Detailpanel); Bestandshinweis im Auftragsformular (gelb, nicht blockierend); Angebot ohne Lagerprüfung (Issue #177)
- Kategorien (SKR03/04, EÜR-Zeile, EKS-Kategorie, Beschreibung, editierbar)
- Buchungsanzeige: Kontonummer (SKR03/04) optional in Kategorie-Dropdowns einblenden
- Steuersätze, Konten, Nummernkreise, Unternehmensprofil
- Unterschrift (Zeichnen oder Datei-Upload), Zahlungshinweis, QR-Zahlung
- PDF-Vorlagen (Briefbogen, Schriftart, Fußzeile)
- Setup-Wizard (4 Schritte inkl. Kassenbestand)
- Transferleistungen: Abrechnungszeitraum-Beginn (Monat aus Leistungsbescheid)
- SMTP-Mailversand: PDF + Dokumentenpakete direkt aus der App senden; je Dokumenttyp eigene Betreff-/Text-Vorlage; Markdown-Signatur (HTML-Mail mit plain-text-Fallback); Live-Vorschau + Cheatsheet

**Dashboard**
- Zufluss-Monitor (§11b SGB II): Stufenfreibetrag, anrechenbar; Toggle Monat / Leistungszeitraum (6 Monate rollierend)
- Lagerwarnung-Widget: Artikel am oder unter Mindestbestand (direkt verlinkt zur Artikelseite)

**Infrastruktur**
- Tauri 2 Desktop-App (Windows, Linux AppImage, macOS DMG)
- Automatisches Backup vor jeder Schema-Migration (WAL-sicher, max. 5 Backups)
- GoBD-Trigger-Schutz (unveränderliche Journal-Einträge auf DB-Ebene)
- Tauri-Updater (Signierung, GitHub Releases)

---

## 🚧 v0.3.x – In Arbeit

### Exporte & Auswertungen
- [x] DATEV-Export: Buchungsstapel EXTF v700/9 mit BU-Schlüsseln (19%/7%/ig.Erwerb/§13b/§25a), konfigurierbaren Gegenkonten und Quartal-/Halbjahr-/Jahres-/Freizeitraumauswahl; Fallback-Sachkonto für RE-Zahlungen; Skonto als Bank-Buchung; AM-Konten 8920–8925 ohne BU-Schlüssel (Issues #165, #167); Stornobuchungen übernehmen BU-Schlüssel der Originalbuchung – auch für Stornos vor v0.3.24 (DB-Lookup, Issue #163); Buchungen ohne Sachkonto mit leerem Konto exportiert statt übersprungen (Issue #163)
- [x] Buchhalter-CSV-Export: Journal als Semikolon-CSV (UTF-8 mit BOM) für Excel/LibreOffice und Buchhaltungsprogramme ohne DATEV-Import; Zeitraumauswahl wie DATEV
- [x] Jahresumsatzsteuererklärung (USt 2A / Anlage UR): Anzeigehilfe mit allen KZ-Werten aus den Journalbuchungen des Wirtschaftsjahres; Kleinunternehmer: KZ 48 (§19 Gesamtumsatz); Vorauszahlungsanrechnung aus gespeicherten Voranmeldungen (KZ 76); PDF-Export; Anlage-UR-Hinweis bei ig. Umsätzen
- [x] Anlage S – Einkünfte aus selbstständiger Arbeit: Anzeigehilfe mit Gewinn/Verlust (aus EÜR), Steuernummer, Finanzamt, Berufsbezeichnung und KFZ-Privatanteil; zeigt welche Zeile in ELSTER wohin gehört
- [x] Anlage S – Tätigkeitsart beachten: bei `gewerbe` ausblenden, bei `gemischt` Hinweis anzeigen (Issue #180)
- [x] Anlage G – Einkünfte aus Gewerbebetrieb: Anzeigehilfe für Gewerbetreibende (§15 EStG); Gewinn aus EÜR; §35 EStG Anrechnungsbetrag = Messbetrag × min(4,0; Hebesatz%); Richtwert-Messbetrag aus Jahresgewinn als Vorschlag (Z.51), überschreibbar mit echtem Bescheid-Wert; Hebesatz optional (Issues #180, #182, #183, #187)
- [x] Jahresübersicht: Kategoriensummen mit EÜR-Zuordnung (🔍 Aufschlüsselung-Toggle in der EÜR)
- [x] Anlage AVEÜR – Abschreibungsplan für Anlagegüter (KFZ, EDV)
- [x] GoBD-Export: USt-Spalte im Journal-CSV korrekt je Einnahmen-/Ausgaben-Typ (neue Spalte „Vorsteuer-Betrag")

### Backup & Wiederherstellung
- [x] Backup bei App-Ende (automatisch, WAL-sicher, max. 5 Kopien lokal)
- [x] Backup auf externes Laufwerk/Freigabe bei App-Ende (AES-256-GCM, DSGVO Art. 32, bis zu 2 Ziele, NAS/USB/Netzlaufwerk; Retry-Dialog bei Fehler)
- [x] SMB-Backup: Backup direkt auf SMB-Netzlaufwerk (smb://server/freigabe/pfad) ohne OS-Mount; separate SMB-Zugangsdaten (Issue #176)
- [x] Systemlaufwerk-Sperre: Backup-Pfade auf C:\, /home, /root, /Users etc. werden automatisch übersprungen; Frontend zeigt sofortigen Hinweis
- [x] Wiederherstellung aus Backup: lokale DB-Snapshots direkt auswählen; ZIP-Backup (unverschlüsselt) oder .zip.enc (verschlüsselt) hochladen → Pending-Marker → Neustart stellt DB + Uploads wieder her

### Wiederkehrende Ausgangsrechnungen (Abo)
- [x] Wiederkehrende Ausgangsrechnungen: Vorlage mit Intervall (monatlich, quartalsweise, jährlich) und automatischer Erstellung als Entwurf am Fälligkeitstag; Preisabgleich mit Artikelstamm
- [x] Auftrag verknüpfen: Auftrag wechselt automatisch auf „Laufend" solange Vorlage aktiv; zurück auf „In Bearbeitung" wenn pausiert; „Abgeschlossen" wenn beendet
- [x] Vertragsdokument (PDF/Bild) an Vorlage hinterlegen – Badge auf der Karte, jederzeit ersetzbar
- [x] 3-Zustands-Lifecycle: aktiv (läuft) / pausiert (aktiv=false) / beendet (dauerhaft, Datensatz bleibt erhalten)
- [x] Detail-Panel: Rechnungsliste aller aus der Vorlage generierten Rechnungen mit Gesamtumsatz-Kachel
- [x] Schnellstart von Auftrags-Seite: „🔁 Wiederkehrend"-Button befüllt das Formular mit Auftragsdaten

### Wiederkehrende Buchungen
- [x] Vorlagen für Fixkosten (Miete, Leasing, Abonnements) mit Fälligkeitsintervall (monatlich/quartalsweise/jährlich)
- [x] Fälligkeits-Badge im Menü (oranger Punkt bei überfälligen Vorlagen, alle 5 Minuten aktualisiert)
- [x] Modus „Direkt": Ein-Klick-Buchung → Journal-Eintrag sofort; Datum rückt automatisch vor
- [x] Modus „Warte auf Beleg": PDF hochladen → OCR extrahiert Belegnummer/Betrag/Fälligkeit → Eingangsrechnungsformular vorausgefüllt; Datum rückt nach dem Speichern automatisch vor
- [x] Vertragsdokument (PDF/Bild) an Vorlage hinterlegen
- [x] Lieferant direkt aus dem Vorlagenformular anlegen
- [x] Variabler Betrag (0 = variabel): Beleg-Modus mit OCR statt manuellem Eintrag
- [x] Einnahmen-Vorlagen: Art-Umschalter Ausgabe/Einnahme; Erlös-Kategorien (Eigenverbrauch, Sachentnahmen); korrekte USt-Konten ohne Vorsteuerabzug (Issue #157)

### GoBD & Korrekturen
- [x] 5-Minuten-Korrekturfenster: Journal-Buchungen innerhalb von 5 Min. direkt bearbeitbar (immutable=False); nach Ablauf automatisch Storno + neue Buchung; Bearbeiten-Button immer sichtbar mit „(Storno)"-Hinweis nach Fristablauf (Issue #184)

### UX & Community
- [x] Tagesabschluss-Erinnerung nur bei offenen Bar-Buchungen: Banner erscheint ausschließlich wenn Tage mit Bar-Buchungen ohne Abschluss existieren; ältestes offenes Datum wird angezeigt (Issue #194)
- [x] Spenden-Seite: PayPal-Link, Kostenübersicht, alternative Unterstützungsmöglichkeiten; Impressum + Datenschutz auf GitHub Pages (Issue #174)
- [x] Steuer-Fristenliste (Issue #198): Übersicht fälliger UStVA-, ESt- und GewSt-Vorauszahlungsfristen für 3/6/12 Monate; automatische Verschiebung auf nächsten Werktag je Bundesland; Dauerfristverlängerung-Toggle; Dashboard-Banner für die nächste Frist

---

## 📋 v0.4.x – Bank CSV-Import & Zahlungsabgleich

- [ ] CSV-Kontoauszug-Import (Postbank, Sparkasse, Volksbank, Commerzbank)
- [ ] Vorschau und manuelle Zuordnung vor dem Import
- [ ] Automatischer Zahlungsabgleich: Kontoauszugzeile ↔ offene Rechnung (Betrag + Empfänger)
- [ ] Auto-Filter-Regeln (Empfänger/Verwendungszweck → Kategorie)
- [ ] Duplikat-Erkennung
- [ ] Import-Protokoll (GoBD: Herkunft nachvollziehbar)

---

## ♿ Barrierefreiheit (kein fester Zeitplan, aber Pflicht vor 1.0)

Die App ist aktuell **nicht barrierefrei**. Dark/Light Mode und Keyboard-Navigation (Combobox) sind vorhanden, aber Screenreader-Unterstützung fehlt weitgehend.

### Priorität 1 – Focus-Management in Modalen
- [ ] `role="dialog"` + `aria-modal="true"` + `aria-labelledby` auf alle Modal-Overlays
- [ ] Focus-Trap: Tab bleibt innerhalb des offenen Modals
- [ ] Initial Focus beim Öffnen (erster Input oder Schließen-Button)

### Priorität 2 – Formulare
- [ ] `htmlFor` + `id` in allen Formular-Labels verknüpfen (viele fehlen aktuell)
- [ ] `aria-required="true"` für Pflichtfelder (visuelles `*` reicht nicht für Screenreader)
- [ ] `aria-describedby` für Fehlermeldungen an den jeweiligen Input koppeln

### Priorität 3 – Semantisches Layout
- [ ] `<main>`, `<nav>`, `<header>` in `AppLayout.tsx` ergänzen
- [ ] Dekorative SVG-Icons mit `aria-hidden="true"` versehen
- [ ] Tabellen (`<table>`) mit `<thead>` / `<tbody>` / `scope`-Attributen

### Priorität 4 – ARIA-Architektur
- [ ] `aria-label` / `aria-labelledby` für Icon-only-Buttons (Löschen, Bearbeiten etc.)
- [ ] `aria-expanded` für Akkordeons und aufklappbare Bereiche
- [ ] `aria-live="polite"` für dynamische Statusmeldungen (Speichern, Fehler)

### Ziel: WCAG 2.1 AA

---

## ⌨️ Ziel: Vollständige Tastatursteuerung (kein fester Zeitplan)

**Ziel:** RechnungsFee soll komplett ohne Maus bedienbar sein – von der Navigation bis zum Finalisieren einer Rechnung.

### Globale Kürzel

| Kürzel | Aktion | Status |
|--------|--------|--------|
| Strg + F | Suchfeld auf der aktuellen Seite fokussieren | ✅ v0.3.33 |
| Strg + Shift + E | Direkt zu Eingangsrechnungen | ✅ v0.3.26 |
| Strg + N | Neue Rechnung / Neues Dokument anlegen (kontextabhängig) | [ ] |
| Strg + S | Speichern (im aktiven Formular) | [ ] |
| Strg + Enter | Finalisieren (Entwurf → Rechnung) | [ ] |
| Esc | Dialog / Detail-Panel schließen | [ ] |

### Navigation & Listen

- [ ] Sidebar vollständig per Tab erreichbar; aktiver Menüpunkt per Enter öffnen
- [ ] Listeneinträge (Rechnungen, Kunden usw.) per Pfeiltasten durchblättern; Enter öffnet Detail-Panel
- [ ] Detail-Panel: Tab-Navigation durch alle Aktions-Buttons (Bearbeiten, Drucken, Stornieren …)
- [ ] Tabellen-Header per Tab fokussierbar, Enter sortiert die Spalte

### Formulare

- [ ] Tab / Shift+Tab springt durch alle Felder in logischer Reihenfolge
- [ ] Positionszeilen: Tab springt durch alle Spalten, Enter fügt neue Zeile hinzu
- [ ] Datums-Felder: Pfeiltasten erhöhen/verringern Tag/Monat/Jahr
- [ ] Dropdowns (USt-Satz, Kategorie, Zahlungsart): Pfeiltasten + Enter, kein Mausklick nötig
- [ ] Autocomplete (Artikel, Kunde): Pfeiltasten wählen Vorschlag, Enter übernimmt

### Modals & Dialoge

- [ ] Focus-Trap: Tab bleibt innerhalb des offenen Dialogs
- [ ] Esc schließt alle Dialoge (Mail, Storno, Finalisieren, …)
- [ ] Bestätigungs-Buttons (Ja/Nein) per Enter / Leertaste auslösbar

---

## 💡 Ideen (ohne Zeitplan)

- **Kalenderansicht** (Issue #198, Folge-Feature) – Vollständige Monatsansicht mit Buchungen, Steuerfristen und Feiertagen. Setzt Steuer-Fristenliste voraus. Größerer Scope, kein fester Zeitplan.

- **Artikel-Varianten** – Varianten eines Artikels (z. B. Größe, Farbe) mit eigenem Preis und Bestand; Auswahl direkt in der Rechnungsposition (Issue #171)

- **Rich-Text-Editor für Einleitungstext** – WYSIWYG-Editor (z. B. TipTap oder Quill) statt Markdown-Textarea für den Einleitungstext auf Rechnungen; aktuell: Markdown mit `**fett**`-Unterstützung im PDF

- **Thunderbird-Integration** – `thunderbird -compose` als dritte Mail-Option neben SMTP und mailto; ermöglicht Dateianhänge ohne SMTP-Konfiguration und nutzt Thunderbirds GPG-Integration automatisch (Issue #147)

- **Erweiterbare Kontenpläne** – Built-in-Pakete (SKR03 vollständig) und CSV-Import eigener Kontenpläne
- **LLM-gestützte Felderkennung** – lokales Modell via ollama als Opt-in für bessere OCR-Zuordnung
- **Fahrtenbuch-App (Android/iOS)** – GPS-Erfassung, GoBD-konform, Export an RechnungsFee
- **hellocash-Anbindung** – REST-API (Issue #13)
- **Dashboard konfigurierbar** – Kacheln ein-/ausblenden, Reihenfolge, externer Link Online-Banking
- **Docker-Version** – containerisiertes Deployment für Selbst-Hoster (Backend + Frontend als Docker-Image)
