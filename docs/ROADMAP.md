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
- Gutschriften (negativierte Positionen, GoBD-Gegenbuchung, Betragslimit)
- Storno mit Pflichtbegründung und GoBD-Gegenbuchung
- Skonto (Standard, Kunden, Rechnung; Zahlungshinweis + Giro-Code)
- Leistungszeitraum Von–Bis

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

**Infrastruktur**
- Tauri 2 Desktop-App (Windows, Linux AppImage, macOS DMG)
- Automatisches Backup vor jeder Schema-Migration (WAL-sicher, max. 5 Backups)
- GoBD-Trigger-Schutz (unveränderliche Journal-Einträge auf DB-Ebene)
- Tauri-Updater (Signierung, GitHub Releases)

---

## 🚧 v0.3.x – In Arbeit

### Exporte & Auswertungen
- [ ] DATEV-Export (CSV nach DATEV-Format für Steuerberater)
- [x] Jahresübersicht: Kategoriensummen mit EÜR-Zuordnung (🔍 Aufschlüsselung-Toggle in der EÜR)
- [ ] Anlage AVEUR – Abschreibungsplan für Anlagegüter (KFZ, EDV)
- [x] GoBD-Export: USt-Spalte im Journal-CSV korrekt je Einnahmen-/Ausgaben-Typ (neue Spalte „Vorsteuer-Betrag")

### Backup & Wiederherstellung
- [ ] Automatische Wiederherstellung aus Backup (Datei-Auswahl → App ersetzt DB und startet neu)

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

---

## 📋 v0.4.x – Bank CSV-Import & Zahlungsabgleich

- [ ] CSV-Kontoauszug-Import (Postbank, Sparkasse, Volksbank, Commerzbank)
- [ ] Vorschau und manuelle Zuordnung vor dem Import
- [ ] Automatischer Zahlungsabgleich: Kontoauszugzeile ↔ offene Rechnung (Betrag + Empfänger)
- [ ] Auto-Filter-Regeln (Empfänger/Verwendungszweck → Kategorie)
- [ ] Duplikat-Erkennung
- [ ] Import-Protokoll (GoBD: Herkunft nachvollziehbar)

---

## 💡 Ideen (ohne Zeitplan)

- **Thunderbird-Integration** – `thunderbird -compose` als dritte Mail-Option neben SMTP und mailto; ermöglicht Dateianhänge ohne SMTP-Konfiguration und nutzt Thunderbirds GPG-Integration automatisch (Issue #147)

- **Erweiterbare Kontenpläne** – Built-in-Pakete (SKR03 vollständig) und CSV-Import eigener Kontenpläne
- **LLM-gestützte Felderkennung** – lokales Modell via ollama als Opt-in für bessere OCR-Zuordnung
- **Fahrtenbuch-App (Android/iOS)** – GPS-Erfassung, GoBD-konform, Export an RechnungsFee
- **hellocash-Anbindung** – REST-API (Issue #13)
- **Dashboard konfigurierbar** – Kacheln ein-/ausblenden, Reihenfolge, externer Link Online-Banking
- **Docker-Version** – containerisiertes Deployment für Selbst-Hoster (Backend + Frontend als Docker-Image)
