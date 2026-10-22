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

## 📋 v0.7.0 – Abschlagsrechnungen (Issue #419)

Vorschlag aus der Community: Abschlags- und Teilrechnungen mit korrekter Anrechnung in der
Schlussrechnung. Nicht vorher geplant, kam während der Entwicklung über Issue #419 hinzu.

- [x] Abschlagsrechnung als eigenständiger, optional aktivierbarer Dokumenttyp (Zahlung,
  Mahnwesen, Storno, Kontokorrent, Bank-Import, ZUGFeRD wie bei einer normalen Rechnung)
- [x] Auswahl-Dialog in der Schlussrechnung: offene Abschlagsrechnungen des Kunden
  (eingeschränkt auf überlappenden Leistungszeitraum), automatischer Abzug des tatsächlich
  gezahlten Betrags (Unter- wie Überzahlung), automatische Übernahme der Original-Leistung
- [x] Negative Schlussrechnung bei Überdeckung (Kunde hat ein Guthaben) statt Blockade
- [x] Verrechnete Abschlagsrechnung: eigener Status, keine weitere Zahlung/Storno/Gutschrift,
  fällt aus Mahnwesen/Fälligkeitslisten heraus, Freigabe bei Storno der Schlussrechnung
- [x] Kontokorrent zeigt bei Überzahlung den tatsächlich gezahlten Betrag statt des gekappten
- [ ] ZUGFeRD BT-113 (Vorauszahlungsreferenz) für Abzugszeilen – siehe „Ideen" unten
- [ ] Bank-Import erkennt eine Rückzahlung auf eine negative Schlussrechnung noch nicht
  automatisch (manuelle Buchung funktioniert)

---

## 📋 Eingangsrechnungen aus dem Mailpostfach (Issue #451)

Vorschlag aus der Community (Gerti): PDF-/XML-Anhänge aus einem eigenen Rechnungspostfach
automatisch als **Entwurf** einer Eingangsrechnung samt Beleg übernehmen – nie direkt buchen,
jeder Entwurf wird vom Nutzer geprüft. Gerade seit der E-Rechnungs-Empfangspflicht (2025)
kommen Rechnungen überwiegend per Mail. Zwei Zugangswege mit gemeinsamem Kern
(Anhang → bestehende PDF/XML-Analyse → Entwurf + Beleg, SHA-256-Dublettenschutz):

- [x] **Stufe 1 – IMAP direkt** (v0.7.4, `api/postfach.py`; umgesetzt als Importliste statt
  automatischer Entwürfe – „Übernehmen" startet den unveränderten Einzelimport): Postfach in den Einstellungen (Host/Port/SSL/Benutzer/
  Passwort/Ordner), Abruf beim Start und per Knopf „Postfach abrufen“; verarbeitete Mails
  wandern in einen Unterordner „RechnungsFee/verarbeitet“ (sichtbar im Mailprogramm, übersteht
  Neuinstallationen – kein UID-Tracking nötig). Unabhängig vom Mailprogramm (Gerti: Aerion).
  Stdlib `imaplib`, Zertifikats-Pinning wie beim SMTP-Versand (Issue #336) wiederverwenden.
  Nur PDF/XML mit Größenlimit, nur Entwürfe (Postfach ist von außen beschreibbar).
  Einschränkung: Microsoft-Konten (Outlook/M365) verlangen OAuth2 – zunächst nicht unterstützt.
- [ ] **Stufe 2 – Thunderbird-Add-on** (MailExtension): „An RechnungsFee senden“ bzw.
  automatisch für einen Ordner, übergibt Anhänge an das lokale Backend und verschiebt die Mail.
  Thunderbird übernimmt die Anmeldung (auch OAuth bei Microsoft/Google) – deckt damit die
  Lücke aus Stufe 1 ab, RechnungsFee speichert keine Mail-Zugangsdaten. Eigenes Projekt,
  Veröffentlichung über addons.thunderbird.net.
- Bewusst **nicht**: Outlook-Steuerung per COM (nur klassisches Outlook unter Windows, läuft aus),
  direkter Zugriff auf Thunderbird-Profildateien (beschädigt den Index bei laufendem Thunderbird).

---

## 📋 Nach v0.7.4 – vorgemerkt

- [ ] **Rechnungsnummer erst beim Finalisieren** (Issue #465, pasarn) – bisher ziehen Entwürfe von
  Ausgangs-/Eingangs-/Abschlagsrechnungen und Gutschriften ihre Nummer schon beim Anlegen
  (`_create_rechnung()` sowie ~10 Umwandlungswege: Angebot/Auftrag/Lieferschein/Proforma → Rechnung,
  Sammelrechnung, Ersatzrechnung, Gutschrift, wiederkehrende Rechnungen); gelöschte Entwürfe hinterlassen
  Lücken, spät finalisierte Entwürfe brechen die Reihenfolge. Plan: Entwurf ohne Nummer (außer manuell
  eingetragen), Vergabe in `finalisiere_rechnung()` aus dem passenden Kreis (rechnung_ausgang/-eingang,
  abschlagsrechnung, gutschrift, rechnung_wiederkehrend falls aktiv bei `vorlage_id`); direkt finalisiert
  angelegte Rechnungen sofort; Frontend mit fehlender Nummer (Liste, Vorschau-PDF „Entwurf“,
  Mail-Platzhalter, Dateinamen); bestehende Entwürfe behalten ihre Nummer (kein Doppel-Vergeben);
  Angebot/Auftrag/Lieferschein unverändert (Proforma-Entwürfe sind bereits ohne Nummer).
- [ ] **Meldezeitraum ZM / KZ 21 / KZ 41** – siehe Abschnitt ELSTER-Export unten.
- [ ] **E-Rechnung: richtige Steuerkategorie** (Issue #467) – 0-%-Positionen bekommen im ZUGFeRD-XML
  immer „Z“; richtig wären AE (Reverse Charge), K (ig. Lieferung), G (Ausfuhr), O (Drittland) mit
  Befreiungsgrund (BT-120/121).
- [ ] **XRechnung für öffentliche Auftraggeber** (Anfrage Handwerksbetriebe) – Kundenfeld „Leitweg-ID“,
  das statt der Kundennummer in BT-10 (BuyerReference) geschrieben wird; optional Download der reinen
  XRechnung-XML (bisher nur hybrides ZUGFeRD-PDF), da manche Behördenportale nur XML annehmen.
- [ ] **Reverse Charge für Bauleistungen im Inland** (§13b Abs. 2 Nr. 4 / Abs. 5 UStG, Anfrage
  Handwerksbetriebe) – Ausgangsrechnung eines Handwerkers an einen deutschen Bauunternehmer ohne USt mit
  Hinweis „Steuerschuldnerschaft des Leistungsempfängers“; bisher nur für EU-Kunden möglich
  (`kundeEuFaehig`). Eigener Haken nur sichtbar, wenn sinnvoll (keine Überfrachtung des Formulars),
  passende Steuerkategorie AE in der E-Rechnung (siehe #467), UStVA-Kennzahl für eigene §13b-Umsätze prüfen.
- [ ] **Kleinunternehmer: Dienstleistungen an EU-Unternehmer** (Folge aus Issue #464) – das
  Rechnungsformular blendet Reverse Charge/ig. Lieferung/Drittland/Ausfuhr bei §19 komplett aus
  (`kundeEuFaehig` u. a. verlangen `!istKleinunternehmer`). Auch ein Kleinunternehmer erbringt eine
  B2B-Dienstleistung an EU-Unternehmer aber im Empfängerland (§3a Abs. 2 UStG): Hinweis
  „Steuerschuldnerschaft des Leistungsempfängers“ auf der Rechnung, USt-IdNr. nötig, Zusammenfassende
  Meldung (ZM-Menü bisher für §19 gesperrt). Vor Umsetzung fachlich prüfen (u. a. ob eigene USt-IdNr.
  Voraussetzung ist, Zusammenspiel mit §19-Hinweis auf der Rechnung, UStVA bleibt unberührt).

---

## 📋 ELSTER-Export: Umsatzsteuer-Voranmeldung und Zusammenfassende Meldung (Issue #360)

Wunsch von Peter1061, Recherche von herrschmidt (Issue #360): Kennzahlen nicht mehr in ELSTER abtippen.

- [x] **Stufe 1 – Datei für den Upload in Mein ELSTER** (keine Registrierung, kein Zertifikat) – umgesetzt von herrschmidt (PR #460), Kennzahlen-Fehler davor behoben (#456 ZM, #457 KZ 43/87, #458 KZ 41, #459 §13b/Kleinunternehmer):
- [ ] **Meldezeitraum ZM / KZ 21 / KZ 41 gesetzeskonform** (nach v0.7.4, Recherche herrschmidt in PR #460, am Gesetzestext geprüft): bisher nach Zahlungsdatum – unbezahlte EU-Lieferungen fehlen ganz. Laut §18a Abs. 8 und §18b UStG gilt, unabhängig von Ist-Versteuerung:
  - **L / KZ 41** (ig. Lieferung): Monat der Rechnungsausstellung, spätestens Monat nach der Lieferung
  - **S / KZ 21** (sonstige Leistung §3a Abs. 2): Monat der Ausführung (`leistung_bis` → `leistung_von` → Rechnungsdatum)
  - Quelle wird die Rechnung (Netto), nicht die Zahlung; ZM und UStVA weiter aus derselben Quelle
  - Korrekturen nach §17 (§18a Abs. 7, §18b Satz 4) als eigene Minusbeträge im Monat des Ereignisses: Storno, Gutschrift, Skonto, Forderungsausfall (`forderungsausfall_buchen`, #252 – dortige Begründung „nichts zu korrigieren“ gilt dann nicht mehr)
  - Übergang per Stichtag wie beim Vorsteuer-Cutover (#338): Rechnungen ab Stichtag nach neuer Regel, ältere bleiben beim Zahlungsdatum – sonst Doppel- bzw. Fehlmeldungen. Vorschlag: Beginn eines Meldezeitraums (z. B. 01.01.2027)
  - nicht betroffen: KZ 43 (Ausfuhr) und KZ 45 (Drittland) – nicht in §18b
  - UStVA als XML: nur der Nutzdatenteil `Anmeldungssteuern` (Namensraum
    `http://finkonsens.de/elster/elsteranmeldung/ustva/v20xx`, passendes `version`-Attribut je
    Jahresversion – häufigste Fehlerursache beim Import), Zeichensatz ISO-8859-15. Reine Ausgabe der
    bereits berechneten Kennzahlen aus `api/ustva.py` (inkl. ELSTER-Rundung, Issue #428).
  - Zusammenfassende Meldung als CSV-Meldeliste (Versionstabelle, Satzarten, Länderkennzeichen) aus `api/zm.py`.
  - Steuernummer ins 13-stellige bundeseinheitliche ELSTER-Format umrechnen (Regeln je Bundesland,
    `unternehmen.bundesland` vorhanden) – größte Fehlerquelle, gegen offizielle Beispiele prüfen.
  - Abgleich von Struktur und Beispielen mit dem ERiC-Dokumentationspaket (Entwicklerzugang vorhanden);
    herrschmidt hat Unterstützung bei der XML-Struktur angeboten.
  - Absenden bleibt beim Nutzer in Mein ELSTER (eigener Zugang, Prüfung vor dem Senden).
- [ ] **Stufe 2 – Direktversand per ERiC** (zurückgestellt): Hersteller-Registrierung, eigene
  Hersteller-ID, Lizenzvertrag, ERiC-Bibliotheken je Plattform bündeln, Zertifikat/PIN je Nutzer,
  jährliche Pflege (ERiC-Mindestversionen, neue Jahresversionen). Mehrwert: auch Jahreserklärung,
  Dauerfristverlängerung/Sondervorauszahlung – die nimmt Mein ELSTER nicht per Datei an.

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

## ♿ v0.8.0 – Barrierefreiheit & Tastatur (Pflicht vor 1.0)

Die App ist bisher **nicht barrierefrei**: Screenreader-Unterstützung fehlt weitgehend, vieles ist
nur per Maus erreichbar. v0.8.0 wird deshalb ein eigenes Release für Barrierefreiheit und
Tastatursteuerung. Bugfixes laufen parallel als 0.7.x weiter; größere neue Funktionen werden bis
0.8.0 zurückgestellt, damit nicht laufend neue Oberfläche ohne diese Standards entsteht.
Planung und Aufgabenverteilung: [Meilenstein „v0.8.0“](https://github.com/nicolettas-muggelbude/RechnungsFee/milestone/8) + Sammel-Issue #455.

**Ziel:** WCAG 2.1 AA für die Kernabläufe; restliche Bereiche schrittweise in 0.8.x.

### 1. Fundament
- [ ] Alle Dialoge auf die gemeinsame Modal-Basis (`components/Modal.tsx`, PR #452: `role="dialog"`,
  `aria-modal`, `aria-labelledby`, Startfokus, Focus-Trap, Esc, Fokus zurück) – ca. 21 Dialoge
- [ ] Esc in offenen Auswahllisten (Land, Stammdaten, Datum) schließt nur die Liste, nicht den Dialog
- [ ] `aria-live="polite"` für Statusmeldungen (Gespeichert, Fehler, Import-Ergebnisse)
- [ ] Landmarken in `AppLayout.tsx`: `<main>`, `<nav>`, `<header>`
- [ ] Dekorative Icons/Emojis mit `aria-hidden="true"`, Icon-Buttons mit `aria-label`

### 2. Formulare
- [ ] `htmlFor` + `id` in allen Formular-Labels
- [ ] Pflichtfelder mit `aria-required`, Fehlermeldungen per `aria-describedby` am Feld
- [ ] Comboboxen (Land, Stammdaten, Artikel, Kategorie) mit `role="combobox"`, `aria-expanded`,
  `aria-activedescendant`; Pfeiltasten + Enter, kein Mausklick nötig
- [ ] Datumsfelder per Tastatur bedienbar
- [ ] Tabellen mit `<thead>`/`<tbody>`/`scope`

### 3. Kernabläufe komplett per Tastatur
- [ ] Navigation: Seitenleiste per Tab, aktiver Punkt per Enter
- [ ] Listen (Rechnungen, Kunden …) per Pfeiltasten, Enter öffnet das Detail-Panel
- [ ] Rechnung schreiben und finalisieren (inkl. Positionszeilen: Tab durch alle Spalten)
- [ ] Zahlung buchen, Journal-Buchung, Eingangsrechnung importieren (inkl. Dropzone und Postfach)
- [ ] Bestätigungsdialoge (Ja/Nein) per Enter/Leertaste, Esc schließt

### 4. Prüfwerkzeuge & Abnahme
- [ ] `eslint-plugin-jsx-a11y` im Lint
- [ ] axe-Prüfung in den Vitest-Tests der umgestellten Komponenten
- [ ] Kontrast-Check für Hell- und Dunkelmodus
- [ ] Manueller Durchlauf der Kernabläufe mit NVDA (Windows) und Orca (Linux), VoiceOver (macOS)
  wenn möglich – Linux (WebKitGTK) unterstützt Screenreader schwächer, dort nur Bestätigtes zusagen

### Bereits vorhandene Tastaturkürzel

| Kürzel | Aktion | Status |
|--------|--------|--------|
| Strg + F | Suchfeld auf der aktuellen Seite fokussieren | ✅ v0.3.33 |
| Strg + Shift + E | Direkt zu Eingangsrechnungen | ✅ v0.3.26 |
| + / E / A | Journal: neue Buchung, Einnahme/Ausgabe wechseln | ✅ |

### Später (0.8.x, kein Muss für 0.8.0)
- Selten genutzte Bereiche (Anlage EKS, Inventur, DATEV-Details …) schrittweise nachziehen
- Komfort-Kürzel: Strg + N (neues Dokument), Strg + S (speichern), Strg + Enter (finalisieren)

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

- **Mehrere Rechner: neueres Backup beim Start erkennen** (Issue #461, lindesbs) – wer RechnungsFee abwechselnd auf zwei Rechnern nutzt und über die externen Backups abgleicht, soll beim Start erfahren, dass ein anderer Rechner ein neueres Backup geschrieben hat. Skizze: Opt-in-Schalter „Ich nutze RechnungsFee auf mehreren Rechnern“ (Standard aus – gleichzeitiges Arbeiten auf beiden Rechnern würde beim Übernehmen Daten überschreiben); Gerätekennung im Backup-Dateinamen (Rotations-Regex `_EXTERN_BACKUP_RE` anpassen); jeder Rechner merkt sich lokal außerhalb der DB (die mitwandert), welches Backup er zuletzt geschrieben/übernommen hat; Startprüfung der Zielordner (lokal/SMB) nur über Dateinamen, ohne Entschlüsseln; Hinweis „Neueres Backup von <Rechner> – übernehmen?“ über die vorhandene Wiederherstellung mit Neustart und gespeichertem Passwort; Konfliktwarnung, wenn auch lokal seit dem letzten Abgleich gearbeitet wurde (vorher automatisch lokal sichern). Nicht trivial, daher zurückgestellt.

- **§13b-/Reverse-Charge-Kennzeichen für eigene Kategorien** (Issue #459) – die Sonderfall-Behandlung (§13b Abs. 1/2, ig. Erwerb, Einfuhrumsatzsteuer) hängt an `kategorien.ust_sonderfall`, das bisher nur die mitgelieferten Kategorien tragen; selbst angelegte Kategorien (z. B. „Plattformgebühren Airbnb“) werden nur über das SKR-Konto (3123/5923 usw.) erkannt. Auswahlfeld in der Kategorienverwaltung (Schema/API/Formular), Konto-Heuristik bleibt Fallback.

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

- **Abschlagsrechnungen: eigener PDF-Abzugs-Block + ZUGFeRD BT-113** (Folge-Issue nach v0.7.0) –
  aktuell erscheint der Abzug einer verrechneten Abschlagsrechnung als normale (read-only)
  Positionszeile. Denkbar: ein eigener Abzugs-Block zwischen Summenblock und 19-Hinweis (Muster:
  bestehende Rabatt-Zwischensumme). Zusätzlich die Vorauszahlungsreferenz BT-113/
  `PrecedingInvoiceReference` im ZUGFeRD-Export korrekt befüllen, falls XRechnung-pflichtige
  Kunden das brauchen – `utils/zugferd.py` hat dafür aktuell keine Unterstützung.

- **Sammelposten / Sammelabschreibung (§6 Abs. 2a EStG)** – Wahlrecht für bewegliche Wirtschaftsgüter zwischen 250 € und 1.000 € netto: Pool pro Wirtschaftsjahr, pauschale Auflösung über 5 Jahre à 20 % (Anlage EÜR Zeile 37, Hilfsblatt Zeilen 63–81). Braucht eigene mehrjährige Pool-Verwaltung (ähnlich Anlagenverzeichnis, aber pro Jahrgang statt pro Einzelgut) – deutlich aufwändiger als die übrige EÜR/AVEÜR-Logik. Zurückgestellt bis explizit nachgefragt (Issue #265, Diskussion 2026-07).

- **MCP-Server** (Issue #429) – eigener Model-Context-Protocol-Server, der die Backend-API (Rechnung erstellen, Zahlung erfassen, Journal abfragen etc.) als Tools für KI-Assistenten (z. B. Claude) exponiert. Vorschlag bisher sehr knapp, kein konkreter Anwendungsfall genannt – Rückfrage im Issue gestellt, Umfang/Priorität noch unklar.

- **Bestellwesen (Einkauf)** – Spiegelbild zu Angebot/Auftrag auf der Lieferantenseite, als
  Schalter unter Funktionen: Bestellung an Lieferanten als eigener Dokumenttyp (Nummernkreis z. B.
  `BE-YY####`, PDF, Mailversand), Status offen → teilweise geliefert → geliefert; **Wareneingang**
  erhöht den Lagerbestand (bisher wird er nur beim Verkauf fortgeschrieben, Lagerführung #173);
  Eingangsrechnung aus der Bestellung vorbefüllen inkl. Abgleich Bestellung ↔ Rechnung;
  Bestellvorschlag aus Mindestbestand (Dashboard-Lagerwarnung → direkt Bestellung).
  Offen: nur Händler mit Lager oder auch Materialbestellungen von Dienstleistern für Aufträge?

- **Seriennummernverwaltung** – baut auf dem Bestellwesen (Wareneingang) und der Lagerführung auf:
  Artikel „seriennummernpflichtig“; Erfassen beim Wareneingang oder manuell, Bestand = freie
  Seriennummern; beim Verkauf je Position so viele Seriennummern wie Menge zuordnen, auf PDF und
  optional in der E-Rechnung (ZUGFeRD-Produktinstanz); Rückverfolgung per Suche (Einkauf, an
  welchen Kunden, mit welcher Rechnung – Gewährleistung, Garantie, Rückruf); Storno/Gutschrift
  gibt die Seriennummer wieder frei; passt zu §25a (Gebrauchtwarenhandel).
  Offen: nur Rückverfolgung oder auch Garantiefristen mit Ablauf und Erinnerung?

- **Öffentliche REST-API** – das Backend ist intern bereits eine REST-API (FastAPI, ~300 Endpunkte),
  aber unversioniert, ohne Anmeldung und auf zufälligem Port. Für Dritte nötig: stabile, versionierte
  Schnittstelle `/api/v1/…` mit OpenAPI-Doku (entkoppelt von der internen), API-Tokens mit Rechten
  (lesen / schreiben), in den Einstellungen erzeug- und widerrufbar; feste Adresse, standardmäßig
  nur lokal, optional im Netzwerk; Schreibzugriffe über dieselben Wege wie die Oberfläche (GoBD,
  Nummernkreise, Signaturen). Einschränkung Desktop-App: nur erreichbar, solange RechnungsFee läuft.
  **Grundlage für MCP-Server (#429) und hellocash-Anbindung (#13)**, statt dass beide eigene Wege gehen.
  Offen: Hauptzweck (Shop legt Rechnungen an, eigene Skripte/Auswertungen, Anbindung anderer Programme)?
