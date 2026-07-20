# Roadmap – RechnungsFee

> Ziel: GoBD-konformes Buchhaltungsprogramm für Kleinunternehmer, Freiberufler und Vereine.
> Tech-Stack: Tauri + React + FastAPI + SQLite

---

## 📋 Kontokorrent – Kunden & Lieferanten

Laufendes Konto pro Geschäftspartner: alle Vorgänge (Rechnungen, Zahlungen, Gutschriften, Verrechnungen) in chronologischer Reihenfolge mit laufendem Saldo.

- [x] Kontokorrent-Ansicht pro Kunde: alle Ausgangsrechnungen, Zahlungen, Gutschriften als Buchungszeilen mit laufendem Saldo
- [x] Kontokorrent-Ansicht pro Lieferant: alle Eingangsrechnungen, Zahlungen als Buchungszeilen mit laufendem Saldo
- [x] Saldoausweis: offen / ausgeglichen / Guthaben
- [x] PDF-Export des Kontokorrent-Auszugs mit Von/Bis-Filter (Kunden & Lieferanten)
- [x] Kontokorrent-Auszug per Mail versenden (Kunden & Lieferanten)
- [x] Debitor-/Kreditorennummern: automatische Vergabe + manuelle Bearbeitung mit Hinweis auf nächste freie Nummer
- [x] DATEV-Export Spalte 48 (Kreditoren-/Debitorennummer) automatisch befüllt
- [ ] Kontokorrent-Übersicht (alle Partner mit offenem Saldo auf einen Blick)
- [ ] Guthaben-Verrechnungen im Kontokorrent

---

## 📋 v0.5.x – Forderungsmanagement

Vollständige Übersicht und Verwaltung offener Forderungen gegenüber Kunden und Verbindlichkeiten gegenüber Lieferanten – über den bereits vorhandenen Guthaben-Mechanismus hinaus.

### Offene Forderungen (Ausgangsrechnungen)
- [ ] Mahnwesen: Mahnstufen (1. / 2. / 3. Mahnung) mit konfigurierbaren Mahngebühren und Verzugszinsen (§ 288 BGB: 5 % über Basiszinssatz)
- [ ] Mahnschreiben als PDF (eigene Vorlage, Mahngebühr + Zinsen ausgewiesen)
- [ ] Übersicht „Offene Forderungen": alle unbezahlten Ausgangsrechnungen mit Alter (30/60/90 Tage-Ampel)

### Verbindlichkeiten (Eingangsrechnungen)
- [ ] Übersicht „Offene Verbindlichkeiten": alle unbezahlten Eingangsrechnungen mit Fälligkeit und Skonto-Frist
- [ ] Zahlungsvorschlag: welche Eingangsrechnungen sind diese Woche fällig?

### Auswertung
- [ ] Debitorenliste / Kreditorenliste: Summe offener Posten pro Kunde / Lieferant
- [ ] Forderungsspiegel: Altersgliederung (0–30 / 31–60 / 61–90 / > 90 Tage)

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
- **Docker-Version** – containerisiertes Deployment für Selbst-Hoster (Backend + Frontend als Docker-Image)
- **Preiskalkulations-Modul** – Kalkulationsblatt pro Artikel/Leistung: Materialkosten, Stundensatz, Gemeinkosten-Aufschlag, Gewinnmarge → kalkulierter Verkaufspreis; Übernahme direkt in Rechnungsposition
- **Offline-Handbuch** – eingebettetes Handbuch direkt in der App (Tauri-Webview oder lokale HTML-Seiten); kein Internetzugang nötig; synchronisiert mit der installierten Version

- **Vollständige BWA: Betriebswirtschaftliche Auswertung** – Erweiterung des Cockpits um Vorjahresvergleich als zweite Spalte (aktueller Monat / Quartal / Jahr vs. Vorjahresperiode), Exportfunktion als PDF im klassischen BWA-Format; für Nutzer die monatlich mit Steuerberater oder Bank kommunizieren (Issue #232)

- **Sammelposten / Sammelabschreibung (§6 Abs. 2a EStG)** – Wahlrecht für bewegliche Wirtschaftsgüter zwischen 250 € und 1.000 € netto: Pool pro Wirtschaftsjahr, pauschale Auflösung über 5 Jahre à 20 % (Anlage EÜR Zeile 37, Hilfsblatt Zeilen 63–81). Braucht eigene mehrjährige Pool-Verwaltung (ähnlich Anlagenverzeichnis, aber pro Jahrgang statt pro Einzelgut) – deutlich aufwändiger als die übrige EÜR/AVEÜR-Logik. Zurückgestellt bis explizit nachgefragt (Issue #265, Diskussion 2026-07).

- **Mehrere Firmen pro Installation (natürliche Personen, z. B. freiberuflich + gewerblich)** – eigene DB-Datei pro Firma statt einer festen `rechnungsfee.db` ([connection.py:14](../src/backend/database/connection.py#L14)), Firma-Verwaltung (anlegen/umbenennen/löschen/wechseln inkl. Relaunch, ähnlich dem bestehenden Restore-Pattern), Setup-Wizard wiederverwendbar für „neue Firma hinzufügen", eigener Belege-Ordner + Backup pro Firma. EÜR/Anlagenverzeichnis/GoBD bleiben sauber pro Firma getrennt. Bewusst **keine** automatische Zusammenführung von Umsätzen über mehrere Firmen für die §19-Kleinunternehmer-Schwelle/UStVA/§141 AO (die für die Person als Steuersubjekt insgesamt gelten) – wer mehrere Firmen führt, kennt diese Pflicht und prüft/meldet das selbst bzw. mit Steuerberater. Diskussion 2026-07.
