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
- [x] Kontokorrent-Übersicht (alle Partner mit offenem Saldo auf einen Blick)
- [x] Guthaben-Verrechnungen im Kontokorrent

---

## 📋 v0.5.x – Forderungsmanagement

Vollständige Übersicht und Verwaltung offener Forderungen gegenüber Kunden und Verbindlichkeiten gegenüber Lieferanten – über den bereits vorhandenen Guthaben-Mechanismus hinaus.

### Offene Forderungen (Ausgangsrechnungen)
- [x] Mahnwesen: frei konfigurierbare Mahnstufen mit Mahngebühren und Verzugszinsen (§288 BGB), Kundensperrung, Halb-/Vollautomatik, Inkasso-Paket, Zahlungsverteilung bei konsolidierten Mahnungen (siehe [docs/plan-mahnwesen.md](plan-mahnwesen.md))
- [x] Mahnschreiben als PDF (eigene Vorlage, Mahngebühr + Zinsen ausgewiesen)
- [x] Übersicht „Offene Forderungen" – Mahnwesen-Seite zeigt alle Kunden mit offenen Rechnungen/Mahngebühr, Filter nach Status

### Verbindlichkeiten (Eingangsrechnungen)
- [x] Übersicht „Offene Verbindlichkeiten": alle unbezahlten Eingangsrechnungen mit Fälligkeit und Skonto-Frist
- [x] Zahlungsvorschlag: welche Eingangsrechnungen sind diese Woche fällig?

### Auswertung
- [ ] Debitorenliste / Kreditorenliste: Summe offener Posten pro Kunde / Lieferant
- [ ] Forderungsspiegel: Altersgliederung (0–30 / 31–60 / 61–90 / > 90 Tage)

---

## 📦 Weitere Linux-Paketformate (Debian, Snap) – vor v1.0.0 testen

**Anlass:** Über AppImage/NSIS/DMG hinaus wurden Debian und Snap als mögliche weitere
Paketformate geprüft – beide haben grundlegend unterschiedliche Hürden.

- **Debian:** Größter Brocken vermutlich das npm-Frontend (Debian verbietet minifizierte Bundles
  als „Quellcode", jede transitive npm-Abhängigkeit müsste einzeln als `node-*`-Paket vorliegen)
  und der Rust-/Tauri-Crate-Baum (kein Vendoring erlaubt, jede Crate braucht ein
  `librust-*-dev`-Paket via debcargo) – aber ein etabliertes Debian-Rust-Team mit Tooling
  existiert dafür. `saxonche` (nur für optionale ZUGFeRD-XSD-Validierung) ist MPL-2.0/frei, aber
  nur als Wheel verfügbar – prüfen ob aus Quellcode baubar. PyMuPDF/`fitz`, `ocrmypdf`,
  `tesseract-ocr` sind bereits fertig in Debian gepflegt. Tauri-Updater müsste für einen
  Debian-Build deaktiviert werden (Debian-Policy: Updates ausschließlich über apt).
- **Snap:** Umgekehrtes Problem-Profil – Snapcraft erlaubt Vendoring (kein Debian-Blocker), dafür
  zwei eigene Risiken: (1) Bei Tauri-Apps kann die empfohlene GNOME-Extension-Einbindung von
  webkit2gtk die Paketgröße drastisch aufblähen (dokumentierter Fall: 17 MB App → 3 GB Snap) –
  vor Veröffentlichung unbedingt selbst nachbauen und Größe prüfen. (2) Strict Confinement
  blockiert das externe Backup auf NAS/USB (`backup_extern_pfad_1/2`) ohne manuell verbundenes
  `removable-media`-Interface – wird für Desktop-Apps nicht automatisch gewährt. Würde von uns
  selbst gebaut und im Snap Store veröffentlicht (eigenes CI-Target, kein externer Maintainer).

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

## 🌿 Release-Strategie nach 1.0 – Stable/Beta-Trennung

**Anlass:** Nach dem 1.0-Release soll die Weiterentwicklung (Beta/2.x) strikt von der stabilen 1.x-Linie getrennt werden. In der Vergangenheit gab es Testversionen (Branches `testing/backend-shutdown`, `testing/qr-code-debug`), bei denen Änderungen versehentlich im `main` landeten – das darf mit dem 1.x-Stable-Branch nicht mehr passieren, reine Disziplin/Worktree-Trennung reicht nicht (siehe auch die frühere `web`-Branch-Worktree-Verwechslung).

**Entscheidung: Branch-per-Stable-Linie + technische Sperre, nicht nur Konvention.**

- Bei 1.0-Release: `1.x`-Branch am Tag abzweigen. `main` wird der aktive Beta/Next-Pfad, dort läuft die freie Weiterentwicklung ohne Einschränkung.
- **GitHub Branch-Protection auf `1.x`**: direkte Pushes serverseitig sperren, Änderungen nur per Pull Request gegen `1.x`. Das macht es technisch unmöglich, dass ein Fehlgriff (falscher Branch, falscher Worktree, KI-/Mensch-Fehler) unbemerkt in der stabilen Linie landet – im Gegensatz zu reiner Branch-Disziplin, die genau das beim `web`-Branch nicht verhindert hat.
- **Wichtiger Fund (2026-07-21):** `main` hat bereits eine klassische Branch-Protection (Pflicht-Review + Status-Check „test (ubuntu-latest)") – aber `enforce_admins` steht auf `false`. Beim Release v0.4.20 wurde die Regel dadurch beim Push als Repo-Owner stillschweigend umgangen („Bypassed rule violations"). **Für `1.x` muss `enforce_admins: true` gesetzt werden**, sonst greift die geplante Sperre nicht einmal für die eigene Solo-Maintainerin – die ganze Garantie wäre wirkungslos.
- `main` bleibt bewusst ohne diese Sperre.

**Praktischer Ablauf für 1.x-Bugfixes:**
1. Fix-Branch von `1.x` abzweigen (z. B. `hotfix/1.x-issue-123`)
2. Fix committen, pushen, PR gegen `1.x` öffnen (auch als Solo-Maintainerin – die Sperre erzwingt den PR-Umweg)
3. PR mergen → einziger Weg wie etwas auf `1.x` landet
4. Patch-Tag von `1.x` aus setzen (`v1.0.1`, `v1.0.2`, …) – eigenes Tag-Schema getrennt von Beta-Tags (`v2.0.0-beta.N`)
5. Falls relevant für Beta: Commit per Cherry-Pick nach `main` nachziehen

Restrisiko ist nur noch Schritt 5 (vergessener Forward-Port) – harmlose Kategorie (Fix fehlt vorübergehend in Beta, auffällig) statt der vorherigen Gefahr (Test-Code landet unbemerkt in Stable).

**Feature-Übernahme von Beta nach 1.x (umgekehrte Richtung):**
Wenn eine Beta-Funktion sich bei der Testgruppe bewährt hat, wird **nicht der ganze Beta-Branch übernommen**, sondern nur der geprüfte Feature-Commit per Cherry-Pick von `main` (Beta) nach `1.x` gezogen – andere, noch unfertige Beta-Features bleiben außen vor. `1.x` wächst so gezielt um genau das, was sich bewährt hat.

**Schema-Versionsregel (kritisch, verhindert Kollisionen bei der Feature-Übernahme):**
`SCHEMA_VERSION` muss über beide Branches hinweg eine einzige, fortlaufende Kette bleiben. Deshalb: jeder 1.x-Bugfix, der eine Migration braucht, wird **sofort** (nicht irgendwann gesammelt) per Cherry-Pick auch nach Beta vorgezogen – nicht nur "bei Gelegenheit". Nur so bleibt Betas `SCHEMA_VERSION` immer ≥ der von 1.x, und eine spätere Feature-Übernahme aus Beta kollidiert nicht mit einer inzwischen unabhängig auf 1.x vergebenen Versionsnummer.

**Weitere Punkte, die bei Umsetzung zu klären sind:**
- Tauri-Updater: eigene Update-Channels (stable/beta) nutzen, damit Beta-Releases nicht automatisch an 1.x-Nutzer verteilt werden; Beta-Releases auf GitHub als "Pre-release" markieren.
- `build.yml`-Tag-Trigger muss Beta-Tag-Schema (`v2.0.0-beta.N`) von echten Releases unterscheiden können.
- Downloadseite (`web`-Branch) darf Beta nicht über den stabilen Download-Link schreiben; eigener, klar getrennter Download-Bereich für die Testgruppe.

**Einordnung:** Entspricht dem Branchüblichen (Release-Branch pro stabiler Linie, z. B. Node.js LTS, Kubernetes `release-1.XX`, PostgreSQL `REL_XX_STABLE`) – kein Sonderweg. Alternative Modelle (Git Flow, Release-Trains wie Firefox/Chrome, Trunk-based+Feature-Flags) wurden verglichen und als zu schwergewichtig bzw. nicht passend für Solo-/Kleinprojekt mit unregelmäßigem Patch-Rhythmus verworfen. Diskussion 2026-07.

---

## 💡 Ideen (ohne Zeitplan)

- **Kalenderansicht** (Issue #198, Folge-Feature) – Vollständige Monatsansicht mit Buchungen, Steuerfristen und Feiertagen. Setzt Steuer-Fristenliste voraus. Größerer Scope, kein fester Zeitplan.

- **Artikel-Varianten** – Varianten eines Artikels (z. B. Größe, Farbe) mit eigenem Preis und Bestand; Auswahl direkt in der Rechnungsposition (Issue #171)

- **Rich-Text-Editor für Einleitungstext** – WYSIWYG-Editor (z. B. TipTap oder Quill) statt Markdown-Textarea für den Einleitungstext auf Rechnungen; aktuell: Markdown mit `**fett**`-Unterstützung im PDF

- **Thunderbird-Versand auf weitere Dokumenttypen ausweiten** – bisher nur für Rechnungen umgesetzt (Issue #147); Angebote, Proforma, Aufträge, Mahnungen und Belege laufen weiterhin ausschließlich über SMTP/mailto. Gleiches Muster (`sendeUeberThunderbird()` in `utils/thunderbirdVersand.ts`), nur die jeweilige `handleMail()`-Stelle ergänzen.

- **Erweiterbare Kontenpläne** – Built-in-Pakete (SKR03 vollständig) und CSV-Import eigener Kontenpläne
- **LLM-gestützte Felderkennung** – lokales Modell via ollama als Opt-in für bessere OCR-Zuordnung
- **Fahrtenbuch-App (Android/iOS)** – GPS-Erfassung, GoBD-konform, Export an RechnungsFee
- **hellocash-Anbindung** – REST-API (Issue #13)
- **Docker-Version** – containerisiertes Deployment für Selbst-Hoster (Backend + Frontend als Docker-Image)
- **Preiskalkulations-Modul** – Kalkulationsblatt pro Artikel/Leistung: Materialkosten, Stundensatz, Gemeinkosten-Aufschlag, Gewinnmarge → kalkulierter Verkaufspreis; Übernahme direkt in Rechnungsposition
- **Offline-Handbuch** – eingebettetes Handbuch direkt in der App (Tauri-Webview oder lokale HTML-Seiten); kein Internetzugang nötig; synchronisiert mit der installierten Version
- **Eigene PDF-Rechnungsvorlagen hochladen** (Issue #383) – setzt einen Umbau der PDF-Erzeugung von imperativem fpdf2-Zeichnen auf eine echte Template-Engine (z. B. HTML/CSS + Jinja + WeasyPrint) voraus; erst danach ist ein Upload-Feature mit Variablenliste sinnvoll möglich. Bis dahin: Wunschvorlagen werden auf Zuruf einzeln in der bestehenden fpdf2-Struktur nachgebaut.

- **Vollständige BWA: Betriebswirtschaftliche Auswertung** – Erweiterung des Cockpits um Vorjahresvergleich als zweite Spalte (aktueller Monat / Quartal / Jahr vs. Vorjahresperiode), Exportfunktion als PDF im klassischen BWA-Format; für Nutzer die monatlich mit Steuerberater oder Bank kommunizieren (Issue #232)

- **Konfigurierbarer Speicherort für archivierte Original-PDFs** (Issue #390) – Dateiname nach Rechnungsnummer statt interner DB-ID (z. B. `RE-260103_42.pdf`) ist seit v0.6.12 erledigt. Offen bleibt: selbst wählbarer Speicherort statt fest `uploads/rechnungen/` im Profil-Datenordner. Setzt eine Lösung für bereits archivierte Bestandsdateien voraus (alte Pfade bleiben in `rechnung.original_pdf_pfad` referenziert).

- **Zeiterfassungssystem** (Issue #395) – optional aktivierbares Zeiterfassungs-Modul mit eigenem Dashboard: Start/Stopp-Zeiterfassung, Zuordnung zu Kunde (idealerweise Projekt), Notizen/Tätigkeitsbeschreibung pro Eintrag; am Periodenende unberechnete Zeiten pro Kunde auswerten und direkt in eine Rechnung mit Stunden-/Projekt-Aufschlüsselung überführen. Größerer Scope (eigenes Datenmodell für Zeiteinträge/Projekte, neue Seite, Rechnungs-Workflow-Integration), kein fester Zeitplan.

- **GbR / Personengesellschaften: Gesellschafter + Gewinnverteilung** (Issue #402) – Stammdatenbereich je Gesellschafter (Name, Beteiligungsquote, Gewinn-/Verlustverteilungsquote getrennt geführt, Gültigkeit je Wirtschaftsjahr, Zuordnung von Privateinlagen/-entnahmen); darauf aufbauend eine Jahresauswertung (EÜR-Gewinn der Gesellschaft, Gewinn-/Verlustanteil je Gesellschafter, Privateinlagen/-entnahmen je Gesellschafter, steuerlicher Ergebnisanteil) als Vorarbeit für die gesonderte und einheitliche Feststellung – keine ELSTER-Übermittlung nötig, reine Berechnung/Auswertung reicht laut Melder. Kein kleines Formularfeld: Buchhaltung/Rechnungen/EÜR laufen unternehmens- bzw. tätigkeitsbezogen und damit unabhängig von der Rechtsform – eine GbR kann RechnungsFee für den Gesamtbetrieb also schon heute nutzen. Es fehlt aber die Ebene darunter: die Aufteilung des bereits ermittelten Gesamtgewinns auf mehrere Personen. `unternehmen` ist als Singleton angelegt und Privatentnahme/-einlage laufen rein kategorienbasiert ohne Personenbezug (Anlage EKS ist zudem ein reines Einzelpersonen-Zusatzformular für Transferleistungsempfänger, damit für GbRs ohnehin irrelevant) – „Gesellschafter" wäre eine neue Dimension quer durch Stammdaten und Auswertung. Später denkbar: Sonderbetriebseinnahmen/-ausgaben, Sonderbetriebsvermögen, Ergänzungsrechnungen. Zurückgestellt bis sich zeigt, wie groß die Nachfrage über den einen Melder hinaus ist.

- **Sammelposten / Sammelabschreibung (§6 Abs. 2a EStG)** – Wahlrecht für bewegliche Wirtschaftsgüter zwischen 250 € und 1.000 € netto: Pool pro Wirtschaftsjahr, pauschale Auflösung über 5 Jahre à 20 % (Anlage EÜR Zeile 37, Hilfsblatt Zeilen 63–81). Braucht eigene mehrjährige Pool-Verwaltung (ähnlich Anlagenverzeichnis, aber pro Jahrgang statt pro Einzelgut) – deutlich aufwändiger als die übrige EÜR/AVEÜR-Logik. Zurückgestellt bis explizit nachgefragt (Issue #265, Diskussion 2026-07).
