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
- Status: offen / bestätigt / abgelehnt / abgelaufen
- Rechnung oder Lieferschein aus Angebot (nur bei Status „Bestätigt")
- Rückverlinkung: Angebot zeigt erstellten Lieferschein / Rechnung als Link
- Dokumentenpakete (Anhänge wie AGB, DSE, LV) als Angebot-Beilage

**Belege & Import**
- Beleganhang an Eingangsrechnungen (PDF/JPG/PNG, SHA256, Inline-Viewer)
- ZUGFeRD / XRechnung / UBL-Import mit Auto-Fill + Fuzzy-Matching
- OCR-Fallback (pdfplumber + Tesseract) für Scans, Fotos, Kassenbons, Tankquittungen
- PDF/A-3-Archivierung (GoBD-Stufe 5), GoBD-ZIP mit Belegordner

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
- Steuersätze, Konten, Nummernkreise, Unternehmensprofil
- Unterschrift (Zeichnen oder Datei-Upload), Zahlungshinweis, QR-Zahlung
- PDF-Vorlagen (Briefbogen, Schriftart, Fußzeile)
- Setup-Wizard (4 Schritte inkl. Kassenbestand)

**Infrastruktur**
- Tauri 2 Desktop-App (Windows, Linux AppImage, macOS DMG)
- Automatisches Backup vor jeder Schema-Migration (WAL-sicher, max. 5 Backups)
- GoBD-Trigger-Schutz (unveränderliche Journal-Einträge auf DB-Ebene)
- Tauri-Updater (Signierung, GitHub Releases)

---

## 🚧 v0.3.x – In Arbeit

### Aufträge
- [ ] `dokument_typ = 'Auftrag'`, Nummernkreis `AUF-JJJJ####`
- [ ] Auftragsbestätigung-PDF mit Dokumentenpaket-Anhängen
- [ ] Auftrag → Lieferschein oder Rechnung
- [ ] Status-Tracking (offen / bestätigt / abgeschlossen)

### Exporte & Auswertungen
- [ ] ZUGFeRD-Export für Ausgangsrechnungen (EN 16931, PDF/A-3 mit XML-Einbettung)
- [ ] DATEV-Export (CSV nach DATEV-Format für Steuerberater)
- [ ] Jahresübersicht: Kategoriensummen mit EÜR-Zuordnung
- [ ] Anlage AVEUR – Abschreibungsplan für Anlagegüter (KFZ, EDV)
- [ ] GoBD-Export: USt-Spalte im Journal-CSV korrekt je Einnahmen-/Ausgaben-Typ

### Wiederkehrende Buchungen
- [ ] Vorlagen für Fixkosten (Miete, Leasing, Abonnements) mit Fälligkeitsintervall
- [ ] Hinweis auf fällige Buchungen beim App-Start
- [ ] Modus „Direkt": Entwurf anlegen, Ein-Klick-Bestätigung
- [ ] Modus „Warte auf Beleg": PDF-Import matcht Lieferant + Betrag → ersetzt Platzhalter

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

- **Erweiterbare Kontenpläne** – Built-in-Pakete (SKR03 vollständig) und CSV-Import eigener Kontenpläne
- **LLM-gestützte Felderkennung** – lokales Modell via ollama als Opt-in für bessere OCR-Zuordnung
- **Fahrtenbuch-App (Android/iOS)** – GPS-Erfassung, GoBD-konform, Export an RechnungsFee
- **hellocash-Anbindung** – REST-API (Issue #13)
- **Dashboard konfigurierbar** – Kacheln ein-/ausblenden, Reihenfolge, externer Link Online-Banking
- **Docker-Version** – containerisiertes Deployment für Selbst-Hoster (Backend + Frontend als Docker-Image)
