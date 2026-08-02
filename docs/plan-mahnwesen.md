# Plan: Mahnwesen / Forderungsmanagement

**Stand:** 2026-08-01
**Status:** Abschnitt A–D implementiert (Schema, Einstellungen/Mahnstufen-CRUD, Fälligkeits-Prüfung,
Vorschau, Mahnung anlegen als Entwurf, PDF-Erzeugung, Frontend-UI inkl. Dashboard-Widget,
Mahnwesen-Seite, Einstellungen-Seite, Rechnungen-Detail „Mahnungen", Kunden-Sperr-Badge) –
Abschnitt E (Kundensperrung-Logik, Inkasso-Paket-ZIP, Bank-Import-Fix) folgt als Nächstes, dann F.

**Wichtige Nachbesserung nach Nutzer-Test (2026-08-01):** `konsolidiert_ab_stufe` (Standard:
Stufe 2) war seit Abschnitt A nur eine gespeicherte Einstellung ohne jede Wirkung - die
Fälligkeits-/Erstellen-Logik behandelte jede Rechnung immer einzeln. Jetzt tatsächlich
implementiert: **Zahlungserinnerung (Stufe 1) bleibt immer 1:1 an einer Rechnung** (Plan-Vorgabe
"noch zu einer Rechnung"); ab `konsolidiert_ab_stufe` zieht `_berechne_mahnung()`
(`api/mahnwesen.py`) automatisch **alle** offenen Rechnungen des Kunden in eine gemeinsame
Mahnung - unabhängig davon, welche rechnung_ids ursprünglich übergeben wurden. Damit wurde auch
die Mahnwesen-Übersichtsseite von "eine Zeile pro Mahnstufe" auf "eine Zeile pro Kunde" umgestellt
(neuer Endpunkt `GET /api/mahnwesen/kunden`) - Details siehe Abschnitt D.

**Neu (2026-08-01): Manuelle Mahnsperre pro Kunde** (Migration 132) - Nutzer-Szenario: Kunde ruft
an, kündigt Zahlung in einer Woche an. `kunden.mahnsperre_bis` (Datum) + `mahnsperre_grund`
(Freitext) - bewusst **getrennt** von `kunden.mahnung_gesperrt`/`mahnung_warnung` (Migration 131/133,
automatische Kundensperrung, siehe Abschnitt E). Wichtige Semantik: die
Sperre **verschiebt keine Fristen**, sie blendet nur so lange jede Aktion (Zahlungserinnerung wie
Mahnung) aus, bis das Datum erreicht ist - `_faellige_naechste_stufe()` bleibt unverändert, nur
`kunden_uebersicht()` unterdrückt das Ergebnis für die Dauer der Sperre; danach läuft alles exakt
auf dem Stand weiter, den es ohne Sperre auch gehabt hätte. `_berechne_mahnung()` (also auch
`/vorschau` und `/erstellen`) lehnt mit 422 ab, solange eine Sperre aktiv ist - zusätzliche
Absicherung falls die Aktion trotzdem über den UI-Zustand hinaus ausgelöst wird.
Endpunkte: `PUT/DELETE /api/mahnwesen/kunden/{kunde_id}/sperre`. Frontend: Banner + Formular im
Kunden-Detail-Panel der Mahnwesen-Seite, Badge „⏸ pausiert bis DD.MM." in der Kundenliste.

**Bugfix (2026-08-01): Konsolidierungs-Stufe konnte zurückfallen.** Szenario (Nutzer-Test):
Rechnung A steht schon bei Stufe 3 ("2. Mahnung"), Rechnung B desselben Kunden erreicht gerade
erst eigenständig Stufe 2 ("1. Mahnung"). Die alte Logik berechnete die Zielstufe der
gemeinsamen Mahnung ausschließlich aus dem individuell ausgelösten Trigger (hier: Stufe 2 von
B) - die gemeinsame Mahnung wäre fälschlich auf Stufe 2 zurückgefallen, obwohl A schon eine
härtere Stufe kannte. Fix in `kunden_uebersicht()` und `_berechne_mahnung()`
(`api/mahnwesen.py`): die Zielstufe ist jetzt immer mindestens der bereits erreichte
Höchststand aller offenen Rechnungen des Kunden (`max(ausgelöste Trigger, kunde_max_mahnstufe)`)
- B "holt auf" zu A's Stand, A wird dabei nicht zusätzlich eskaliert. Echte Weitereskalation
kommt weiterhin nur aus einem tatsächlich ausgelösten höheren Trigger (z.B. A's eigener
Stufe-3→4-Termin). Live verifiziert.

---

## Kontext

RechnungsFee hat bereits:
- Anzeige überfälliger Rechnungen (Dashboard + RechnungenPage)
- Kontokorrent pro Kunde (Forderungen-Tabelle, Migration 108)

Das Mahnwesen baut darauf auf: konfigurierbare Mahnstufen mit Vorlagen, halb-/vollautomatischer Versand per Mail und/oder PDF-Druck, Mahngebühren und Verzugszinsen, Kundensperrung und ein Inkasso-Paket als ZIP am Ende der Mahnkette.

---

## Festgelegte Entscheidungen

| Thema | Entscheidung |
|-------|-------------|
| Terminologie Stufe 1 | „Zahlungserinnerung" als Seed-Vorschlag, Name/Text/Gebühren komplett konfigurierbar |
| Granularität | Stufe 1 pro Rechnung; ab konfigurierbarer Stufe X optional konsolidiert pro Kunde |
| Mahngebühren | Privat/Gewerblich getrennt; Vorschlag: Privat 5 €, Gewerblich 40 € (§288 BGB) |
| Verzugszinsen | Basiszinssatz + Aufschlag getrennt; Vorschlag: +5 Pp Privat / +9 Pp Gewerblich (§288 BGB) |
| Buchungszeitpunkt Mahngebühr | Bei Zahlung der Rechnung → automatische Einnahme-Buchung (Zufluss-Prinzip) |
| Mahngebühr/Zinsen bei Bankabgleich | Überschuss ggü. Rechnungsbetrag erst gegen offene Mahngebühr/Verzugszinsen verrechnen (eigene Einnahme-Buchung), erst der danach verbleibende Rest zählt als Kundenguthaben (`bank_import.py`) – siehe Abschnitt E |
| Mahnungs-PDF | Eigenes schlichtes Layout + Giro-Code QR |
| Automation | Halbautomatik als Standard, Vollautomatik als opt-in |
| Inkasso-Paket | ZIP mit strukturierten PDF-Unterordnern |
| Kundensperrung | Warnung bis harte Sperrung, ab konfigurierbarer Mahnstufe |

---

## Abschnitt A – Datenbankschema (Migration 131 – Nummer im Plan war veraltet, SCHEMA_VERSION war zwischenzeitlich auf 130 gewandert)

**Status: ✅ erledigt (2026-08-01)** – inkl. 4 Standard-Mahnstufen als idempotenter Seed

### Neue Tabellen

```sql
-- Singleton Einstellungen (id=1)
CREATE TABLE mahnwesen_einstellungen (
    id INTEGER PRIMARY KEY DEFAULT 1,
    aktiv BOOLEAN DEFAULT 0,
    automation_modus VARCHAR(10) DEFAULT 'halb',       -- manuell|halb|voll
    versand_mail BOOLEAN DEFAULT 1,
    versand_pdf BOOLEAN DEFAULT 0,
    konsolidiert_ab_stufe INTEGER DEFAULT 2,           -- ab Stufe X: pro Kunde
    kundensperrung_aktiv BOOLEAN DEFAULT 0,
    kundensperrung_ab_stufe INTEGER DEFAULT 3,
    kundensperrung_modus VARCHAR(10) DEFAULT 'warnung',-- warnung|sperrung
    verzugszinsen_aktiv BOOLEAN DEFAULT 0,
    verzugszinsen_ab_stufe INTEGER DEFAULT 2,
    basiszinssatz NUMERIC(5,2) DEFAULT 2.12,           -- Bundesbank, halbjährl. anpassen
    verzugszinsen_aufschlag_privat NUMERIC(5,2) DEFAULT 5.0,
    verzugszinsen_aufschlag_gewerblich NUMERIC(5,2) DEFAULT 9.0
)

-- Konfigurierbare Mahnstufen
CREATE TABLE mahnstufen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stufe INTEGER NOT NULL,
    bezeichnung VARCHAR(100) DEFAULT 'Zahlungserinnerung',
    tage_nach_faelligkeit INTEGER DEFAULT 7,    -- Stufe 1: Tage nach Fälligkeit
    tage_nach_vorheriger INTEGER DEFAULT 14,    -- Stufe 2+: Tage nach letzter Mahnung
    betreff_vorlage TEXT,
    text_vorlage TEXT,
    mahngebuehr_aktiv BOOLEAN DEFAULT 0,
    mahngebuehr_privat NUMERIC(12,2) DEFAULT 5.00,
    mahngebuehr_gewerblich NUMERIC(12,2) DEFAULT 40.00,
    aktiv BOOLEAN DEFAULT 1
)

-- Mahnhistorie
CREATE TABLE mahnungen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mahnnummer VARCHAR(50),                            -- aus Nummernkreis MHN-YY####
    kunde_id INTEGER REFERENCES kunden(id) ON DELETE CASCADE,
    mahnstufe_id INTEGER REFERENCES mahnstufen(id) ON DELETE SET NULL,
    stufe INTEGER NOT NULL,                            -- Snapshot beim Erstellen
    bezeichnung VARCHAR(100),                          -- Snapshot beim Erstellen
    erstellt_am DATETIME DEFAULT CURRENT_TIMESTAMP,
    versendet_am DATETIME,
    versand_mail BOOLEAN DEFAULT 0,
    versand_pdf BOOLEAN DEFAULT 0,
    mahngebuehr NUMERIC(12,2) DEFAULT 0,
    verzugszinsen NUMERIC(12,2) DEFAULT 0,
    offener_betrag_gesamt NUMERIC(12,2),
    journal_id INTEGER REFERENCES journal(id) ON DELETE SET NULL,
    pdf_pfad VARCHAR(500),
    status VARCHAR(20) DEFAULT 'entwurf'               -- entwurf|versendet|storniert
)

-- M:N Mahnung ↔ Rechnung(en) (für konsolidierte Mahnungen)
CREATE TABLE mahnungen_rechnungen (
    mahnung_id INTEGER REFERENCES mahnungen(id) ON DELETE CASCADE,
    rechnung_id INTEGER REFERENCES rechnungen(id) ON DELETE CASCADE,
    offener_betrag NUMERIC(12,2),                      -- Snapshot beim Erstellen
    PRIMARY KEY (mahnung_id, rechnung_id)
)
```

### Neue Felder auf bestehenden Tabellen
```sql
ALTER TABLE kunden ADD COLUMN mahnung_gesperrt BOOLEAN DEFAULT 0
ALTER TABLE rechnungen ADD COLUMN mahnstufe_aktuell INTEGER DEFAULT 0
```

### Nummernkreis-Seed
```python
Nummernkreis(bezeichnung="Mahnungen", typ="mahnung", format="MHN-YY####", naechste_nr=1, reset_jaehrlich=True)
```

### Neue Kategorien (seed.py + _migrate_kategorien)
```python
{"name": "Mahngebühren", "kontenart": "Erlös", "konto_skr03": "2742", "konto_skr04": "4970", "vorsteuer_prozent": 0, "ust_satz_standard": 0}
{"name": "Verzugszinsen (Einnahme)", "kontenart": "Erlös", "konto_skr03": "2650", "konto_skr04": "7100", "vorsteuer_prozent": 0, "ust_satz_standard": 0}
```

> Kontonummern gegen den DATEV-Kontenrahmen (`vorlagen/kategorien/*.pdf`) geprüft, Stand 2026-08-01:
> - **Mahngebühren** → SKR03 2742 / SKR04 4970 „Versicherungsentschädigungen und Schadenersatzleistungen".
>   Passt fachlich besser als eine generische „Sonstige Erträge"-Kategorie: Mahngebühren gelten
>   steuerlich als Schadensersatz (§288 BGB), nicht als reguläre umsatzsteuerpflichtige
>   Betriebseinnahme – daher `vorsteuer_prozent: 0`. Ursprünglich vorgeschlagenes Konto
>   8910/4910 kollidierte mit „Eigenverbrauch von Waren (19%)" (SKR03 8910).
> - **Verzugszinsen** → SKR03 2650 / SKR04 7100 „Sonstige Zinsen und ähnliche Erträge" – eigenes
>   Konto, nicht mit Mahngebühren zusammenlegen. Ebenfalls nicht umsatzsteuerbar.
> - `euer_zeile`: noch offen, siehe TODO unten – vermutlich nicht Zeile 15 (die ist für
>   umsatzsteuerpflichtige Betriebseinnahmen), da beide Kategorien `vorsteuer_prozent: 0` sind.

> ⚠️ **TODO vor Abschluss Abschnitt A:** passende `euer_zeile` für beide Kategorien in der
> Anlage EÜR 2025 ermitteln (voraussichtlich „Sonstige Betriebseinnahmen" nahe Zeile 16/18,
> analog zu „Vorsteuererstattung FA" euer_zeile=18) – noch nicht gegengeprüft.

### Standard-Mahnstufen (seed.py)

| Stufe | Bezeichnung | Tage | Mahngebühr | Mahngebühr aktiv |
|-------|-------------|------|------------|-----------------|
| 1 | Zahlungserinnerung | 7 nach Fälligkeit | 0 € / 0 € | Nein |
| 2 | 1. Mahnung | 14 nach vorheriger | 5,00 € / 40,00 € | Ja |
| 3 | 2. Mahnung | 14 nach vorheriger | 5,00 € / 40,00 € | Ja |
| 4 | Letzte Mahnung vor Klage | 10 nach vorheriger | 5,00 € / 40,00 € | Ja |

### Platzhalter in Vorlagen
`{rechnungsnummer}`, `{faellig_am}`, `{offener_betrag}`, `{mahngebuehr}`, `{verzugszinsen}`, `{gesamtforderung}`, `{bezeichnung}`, `{stufe}`, `{kunde}`, `{firmenname}`, `{datum}`

### Betroffene Dateien (Abschnitt A)
- `src/backend/main.py` – Migration 116 + `SCHEMA_VERSION = 116`
- `src/backend/database/models.py` – 4 neue Modelle, 2 neue Felder
- `src/backend/api/schemas.py` – Pydantic-Schemas
- `src/backend/database/seed.py` – Nummernkreis, Kategorie, 4 Mahnstufen
- `src/backend/api/mahnwesen.py` – NEU, API-Grundgerüst (Einstellungen + Mahnstufen CRUD)
- `src/backend/main.py` – Router registrieren

---

## Abschnitt B – Backend-API (vollständig)

**Status: 🟡 teilweise erledigt (2026-08-01)** – Einstellungen/Mahnstufen-CRUD (Abschnitt A),
`GET /faellig`, `POST /vorschau`, `POST /erstellen`, `GET /rechnungen/{id}/mahnungen`,
`GET /kunden/{id}/mahnungen` implementiert. Noch offen, da sie den PDF-Generator (Abschnitt C)
voraussetzen: `POST /{id}/versenden`, `GET /{id}/pdf`, `POST /inkasso-paket/{kunde_id}`.
Mahnungen bleiben bis zum Versand im Status "entwurf" – `rechnungen.mahnstufe_aktuell` wird
bewusst erst beim tatsächlichen Versand hochgezählt, nicht schon beim Entwurf.

Datei: `src/backend/api/mahnwesen.py`

| Method | Pfad | Beschreibung |
|--------|------|-------------|
| GET | `/api/mahnwesen/einstellungen` | Einstellungen + alle Mahnstufen |
| PUT | `/api/mahnwesen/einstellungen` | Einstellungen speichern |
| POST | `/api/mahnwesen/mahnstufen` | Neue Mahnstufe anlegen |
| PUT | `/api/mahnwesen/mahnstufen/{id}` | Mahnstufe bearbeiten |
| DELETE | `/api/mahnwesen/mahnstufen/{id}` | Mahnstufe löschen |
| GET | `/api/mahnwesen/faellig` | Rechnungen die Mahnung brauchen |
| POST | `/api/mahnwesen/vorschau` | Entwurf berechnen (Gebühren, Zinsen) |
| POST | `/api/mahnwesen/erstellen` | Mahnung(en) erstellen (Status: entwurf) |
| POST | `/api/mahnwesen/{id}/versenden` | Mahnung versenden (Mail + PDF) |
| GET | `/api/mahnwesen/{id}/pdf` | Mahnungs-PDF (inline) |
| GET | `/api/rechnungen/{id}/mahnungen` | Mahnhistorie einer Rechnung |
| GET | `/api/kunden/{id}/mahnungen` | Alle Mahnungen eines Kunden |
| POST | `/api/mahnwesen/inkasso-paket/{kunde_id}` | ZIP-Paket generieren |

### Fälligkeits-Logik
- Keine Mahnung vorhanden → fällig wenn `faellig_am + tage_nach_faelligkeit(niedrigste aktive Stufe) ≤ heute`
- Letzte Mahnung vorhanden → **nächsthöhere aktive Stufe** suchen (`stufe > aktuelle_stufe AND aktiv=1`, sortiert
  aufsteigend, erste Treffer) – nicht stur „aktuelle Stufe + 1", da Nutzer:innen einzelne Stufen deaktivieren/löschen
  können (z. B. nur Stufe 1+2, danach manuell Inkasso). Fällig wenn `versendet_am + tage_nach_vorheriger(gefundene Stufe) ≤ heute`.
- Keine nächsthöhere aktive Stufe gefunden → Rechnung gilt als „ausgereizt", erscheint nicht mehr in
  `GET /faellig`, aber bleibt über „Inkasso-Paket" manuell erreichbar (Abschnitt B)
- Nur Rechnungen mit `zahlungsstatus IN ('offen', 'teilbezahlt')` und `ist_entwurf = 0` und `storniert = 0`

### Mahngebühr bei Zahlung buchen
In `src/backend/api/rechnungen.py` PATCH-Endpoint:  
Bei `zahlungsstatus → 'bezahlt'`, wenn Rechnung Mahnungen mit `mahngebuehr > 0` hat → automatisch Journaleintrag mit Kategorie „Mahngebühren" anlegen.

### Inkasso-Paket ZIP
1. `deckblatt.pdf` – Kundendaten, offener Saldo, Mahnhistorie, Verzugszinsen bis heute
2. `kontokorrent.pdf` – bestehenden `/kontokorrent/pdf`-Endpunkt wiederverwenden
3. `rechnungen/RE-*.pdf` – aus `rechnungen.original_pdf_pfad` oder neu generiert
4. `mahnungen/MHN-*.pdf` – aus `mahnungen.pdf_pfad`

---

## Abschnitt C – Mahnungs-PDF

**Status: ✅ erledigt, nach Nutzer-Test 2026-08-01 nachgebessert** – `utils/pdf_mahnung.py`
(nicht `pdf/mahnung.py`, das Projekt hat keinen `pdf/`-Ordner, alle PDF-Vorlagen liegen unter
`utils/pdf_*.py`). `GET /api/mahnwesen/{id}/pdf` liefert das PDF inline aus.

**Erste Version hatte reale Probleme** (per Live-Test durch Nutzerin gefunden, nicht nur Theorie):
1. `multi_cell()` ohne `new_x="LMARGIN", new_y="NEXT"` → Cursor blieb nach der 1. Zeile fast am
   rechten Rand hängen → **500 Internal Server Error** beim PDF-Abruf sobald der Mahntext mehr
   als eine Zeile hatte. Alle anderen PDF-Generatoren im Projekt setzen diese Parameter konsequent.
2. Kein Briefkopf (kein Logo, keine Absenderadresse), kein DIN-5008-Adressfenster – wirkte nicht
   wie ein Geschäftsbrief. Behoben durch Wiederverwendung der Konstanten/Hilfsfunktionen aus
   `pdf_rechnung_base.py` (Logo, Absenderblock, Fußzeile mit Bankdaten/USt-ID/HR) – die
   Header/Footer-Methoden selbst sind bewusst dupliziert statt geerbt (`RechnungPDFBase` ist eng an
   Rechnungs-Metadaten gekoppelt), nur Konstanten/reine Funktionen werden importiert.
3. Zahlungsreferenz (GiroCode-Verwendungszweck + Überweisungshinweis) nannte die interne
   Mahnnummer statt der Rechnungsnummer(n) – für den Kunden nicht wiederzufinden. Jetzt:
   Rechnungsnummer(n) als Referenz, Mahnnummer nur noch im Meta-Block sichtbar.

Layout (DIN-5008-Geschäftsbrief, analog Rechnungs-PDFs):
- Briefkopf: Logo + Absenderblock rechts oben, Trennlinie (identisch zu Rechnungs-PDFs)
- DIN-5008-Adressfenster links + Meta-Block rechts (Mahnnummer, Datum, Rechnung(en))
- Betreff: `{bezeichnung} – {rechnungsnummer}` / konsolidiert: `{bezeichnung} – Offene Forderungen`
- Mahntext (Vorlage mit aufgelösten Platzhaltern)
- Tabelle: Rechnung(en) | Rechnungsdatum | Fällig am | Offener Betrag
- Summenblock: Offener Betrag + Mahngebühr + Verzugszinsen = **Gesamtforderung**
- Bankdaten + **Giro-Code QR** (Betrag = Gesamtforderung, Referenz = Rechnungsnummer(n))
- Fußzeile: Firmendaten/USt-ID/HR/Bankverbindung/Seitenzahl (wie Rechnungs-PDFs)
- `Content-Disposition: inline`

**Ansehen vs. Versand-Wirkung** (Nutzer-Feedback: "ein geöffneter/gedruckter Entwurf darf nicht
folgenlos löschbar bleiben"): `GET /{id}/pdf?nur_ansehen=true` ändert den Status nicht (reine
Vorschau, analog `rechnungen.py`). Ohne den Parameter (Klick auf "Drucken" oder Mail-Versand)
wechselt eine Mahnung im Status `entwurf` automatisch zu `versendet` + `versendet_am` gesetzt –
danach lehnt `DELETE /{id}` mit 422 ab. Gemeinsamer Helper `mahnung_pdf_bytes()` in
`api/mahnwesen.py`, von `GET /pdf` und `api/mail.py` (`mahnung_id`-Zweig) gleichermaßen genutzt.

**Mail-Versand**: `api/mail.py` → `MailSendenRequest.mahnung_id` (neues optionales Feld neben
`rechnung_id`/`dokumentenpaket_id`), nutzt denselben `mahnung_pdf_bytes()`-Helper für den Anhang.
Frontend: neue Komponente `MahnungMailDialog.tsx` (eigenständig, nicht der bestehende
`MailDialog.tsx` – der ist eng an den `Rechnung`-Typ gekoppelt und wird von Angebot/Proforma/
Auftrag mitgenutzt, die alle als `rechnungen`-Zeilen mit `dokument_typ` existieren; eine Mahnung
ist eine eigene Tabelle mit anderen Feldern).

---

## Abschnitt D – Frontend

**Status: ✅ erledigt, nach Nutzer-Test 2026-08-01 nachgebessert** (siehe auch Abschnitt C:
PDF-Bug, Briefkopf, Ansehen/Versand-Unterscheidung, Mail-Versand hängen eng zusammen).

### Neue Seiten

| Datei | Beschreibung |
|-------|-------------|
| `src/frontend/src/pages/einstellungen/MahnwesenPage.tsx` | Globale Einstellungen + Mahnstufen-Editor |
| `src/frontend/src/pages/mahnwesen/MahnwesenPage.tsx` | Split-Panel Übersicht (wie RechnungenPage) |

### Einstellungsseite
- Toggle: Mahnwesen aktivieren
- Automation: Radio manuell / halb / voll
- Versand: Mail / PDF / beides (Checkboxen)
- Konsolidierung: ab Stufe X pro Kunde (Select)
- Kundensperrung: Toggle + zwei unabhängige, nullbare Schwellen „Warnung ab Stufe" / „Sperrung ab Stufe"
- Verzugszinsen: Toggle + ab Stufe + Basiszinssatz (Info-Link bundesbank.de) + Aufschläge Privat/Gewerblich
- Mahnstufen-Editor: sortierbare Liste, jede Stufe editierbar (Bezeichnung, Tage, Gebühren, Betreff/Text mit Platzhalter-Chips)

### Übersichtsseite `/mahnwesen` (2026-08-01 auf Kunde-Zeilen umgestellt)

**Historie der Entscheidung:** Ursprünglich eine Zeile pro fälliger Mahnstufe (Abschnitt B), dann
eine Zeile pro Rechnung mit Status+Historie im Detail (erster Nutzer-Test: "für jede Stufe ein
Listeneintrag, unübersichtlich"). Beim Design des Rechnung-zentrierten Nachfolgers zeigte sich:
Zahlungserinnerung (Stufe 1) bleibt zwar 1:1 an der Rechnung, aber ab `konsolidiert_ab_stufe`
gehört die Rechnung nicht mehr allein sich selbst – die *Mahnung* gruppiert dann mehrere
Rechnungen eines Kunden. Ergebnis: **eine Zeile pro Kunde** ist die richtige Einheit.

- **Liste** (`GET /api/mahnwesen/kunden`, `MahnwesenKundeUebersicht`): eine Zeile pro Kunde mit
  offenen/überfälligen Rechnungen. Spalten: Kunde | Anzahl Rechnungen | Fällig seit (älteste) |
  Betrag gesamt | Status (`aktionsfaellig` | `entwurf` | `versendet` | `offen`, als Filter-Chips).
  `aktionsfaellig` bedeutet hier bewusst nur „eine echte Mahnstufe (≥ konsolidiert_ab_stufe) ist
  fällig" – eine fällige Zahlungserinnerung einzelner Rechnungen macht den Kunden als Ganzes noch
  nicht aktionsfällig (die bleibt Rechnungssache, siehe Detail).
- **Detail-Panel** (pro Kunde, fest `w-[28rem]`, kein Formular/Splitter – siehe RechnungDetail):
  1. **Offene Rechnungen** (`kunde.rechnungen`, `MahnwesenRechnungMini`) – je mit Badge
     (Zahlungserinnerung fällig / bereits auf Stufe X / offen). Ist eine Zahlungserinnerung
     fällig, klappt ein Klick auf die Zeile eine Mini-Vorschau + „als Entwurf anlegen" auf –
     **immer nur für diese eine Rechnung** (`mahnungErstellen([id], 1)`, nie konsolidiert).
  2. Falls `aktionsfaellig`: Vorschau-Button + „[Stufe] als Entwurf anlegen" für den ganzen
     Kunden – `mahnungErstellen([repräsentative_id], naechste_stufe)`; das Backend zieht wegen
     der Konsolidierungs-Logik automatisch alle offenen Rechnungen mit rein.
  3. **„Mahnungen"** (Historie, `GET /kunden/{id}/mahnungen`, jetzt `MahnungHistorieItem` statt
     `MahnungResponse` – liefert zusätzlich `kunde_email`/`rechnungsnummern` für den Mail-Dialog):
     alle je angelegten Mahnungen dieses Kunden (Stufe 1 **und** höher), mit 👁 Ansehen
     (`nur_ansehen=true`, folgenlos), 🖨️ Drucken/✉️ Mail (setzen Status auf `versendet`),
     🗑️ Löschen nur für `entwurf`. Bei konsolidierten Mahnungen: Hinweis „gemeinsam: RE-X, RE-Y".
  Nach dem Anlegen: grüne Leiste mit direkten Links „→ RE-XXXX ansehen" pro betroffener Rechnung
  (`/rechnungen?open=<id>` – Nutzer-Feedback: kein Weg zurück zur Rechnung nach dem Anlegen).

### Weitere UI-Änderungen

| Bereich | Änderung |
|---------|---------|
| Dashboard | Widget „X Mahnungen fällig" → Liste mit Kunde/Rechnungsnr./Stufe/Betrag (nicht nur eine Zeile – analog `ÜberzahlungWidget`), Klick → `/mahnwesen` |
| Rechnungen Detail-Panel | Abschnitt „Mahnstatus" – **reine Anzeige** (Mahnnummer/Stufe/Status je Mahnung) + Link „Zum Mahnwesen"; PDF-Klick und Löschen wurden hier bewusst entfernt (Nutzer-Feedback: Aktionen gehören zentral ins Mahnwesen, nicht verstreut; ein hier gelöschter, aber schon geöffneter/gedruckter Entwurf hätte eine Lücke in der Mahnkette gerissen) |
| Kunden Detail-Panel | Sperr-Status-Badge im Formular-Header (`🔒 Mahnsperre`), rein anzeigend – kein Toggle, da die Sperr-*Logik* (Setzen von `mahnung_gesperrt`) erst in Abschnitt E entsteht; `mahnung_gesperrt` musste zusätzlich in `KundeResponse` (schemas.py) und im Frontend-`Kunde`-Typ ergänzt werden, da Migration 131 das Feld nur auf DB-Ebene anlegte. Zusätzlich „Mahnstatus"-Badges im Kontokorrent-Tab (informativ, Klick öffnet PDF – hier bewusst nicht auf reine Anzeige reduziert, da nicht explizit bemängelt) |
| Navigation (`AppLayout.tsx`) | Sidebar-Eintrag „Mahnwesen" (sichtbar wenn `aktiv=true`, per eigener Query auf `/mahnwesen/einstellungen` – Modul hat keine `unternehmen.xxx_aktiv`-Spalte wie andere optionale Module) |
| Einstellungsmenü | Neuer Punkt „Mahnwesen" (immer sichtbar, auch wenn Modul deaktiviert) |
| `src/frontend/src/App.tsx` | Routen `/mahnwesen` und `/mahnwesen-einstellungen` |

### Konfigurierbare Dokumentanhänge pro Mahnstufe ✅ (2026-08-02, Nutzer-Feedback Punkt 12 vom 2026-08-01)

„Unter Einstellungen will ich für jede Mahnstufe festlegen können welche Dokumente ich anhängen
möchte. Rechnung, Bisherige Mahnungen, Kontokorrent ab erste gemahnte Rechnung. Vielleicht sogar
ein Datenpaket."

**Scope-Entscheidung:** Nur der **Mail-Versand** wird um Zusatzanhänge erweitert - „anhängen" trifft
das Wort am direktesten, und Drucken/Ansehen bleibt bewusst beim Einzel-PDF (echtes PDF-Merging für
den Druckfall hätte den Umfang deutlich aufgebläht, siehe ursprüngliche Scoping-Notiz). Das
„vielleicht sogar ein Datenpaket" wurde nicht separat gebaut - das bereits existierende
Inkasso-Paket-ZIP deckt diesen Bedarf für den Eskalationsfall ab.

**Migration 137:** `mahnstufen.anhang_rechnung` / `anhang_bisherige_mahnungen` /
`anhang_kontokorrent` (je `BOOLEAN DEFAULT 0`) - alle drei standardmäßig aus, rein opt-in je Stufe
(z. B. bei der Zahlungserinnerung meist unnötig, bei der letzten Mahnung vor Inkasso sinnvoll).

**`sammle_mahnung_anhaenge(db, mahnung)`** (`api/mahnwesen.py`) - liest die Konfiguration der
Mahnstufe der übergebenen Mahnung und baut je aktiviertem Typ zusätzliche `(bytes, dateiname)`-Paare:
- `anhang_rechnung`: PDF jeder verknüpften Rechnung, über den bestehenden `rechnung_als_pdf()`
  (gleiche Wiederverwendung wie beim Inkasso-Paket - Original-Archiv/Kopie-Stempel/GoBD-Snapshot
  greifen automatisch korrekt).
- `anhang_bisherige_mahnungen`: alle **früheren, versendeten** Mahnungen desselben Kunden
  (`erstellt_am < diese Mahnung`, `Mahnung.id != diese Mahnung`), über `mahnung_pdf_bytes(...,
  nur_ansehen=True)` - reiner Nachdruck, keine Statuswirkung.
- `anhang_kontokorrent`: Kontokorrent-PDF über die bestehende `_kontokorrent_bewegungen()` +
  `erstelle_kontokorrent_pdf()`, Zeitraum ab `erstellt_am` der **ältesten versendeten Mahnung**
  dieses Kunden bis heute (Nutzer-Vorgabe „ab erste gemahnte Rechnung").

Jeder Anhang-Typ läuft in einem eigenen `try/except` - ein fehlgeschlagener Zusatzanhang (z. B.
Kontokorrent-Aufbau schlägt fehl) darf den eigentlichen Mahnungs-Versand nie verhindern, nur der
Zusatzanhang fehlt dann.

**Wired in `api/mail.py::mail_senden()`**: direkt nach dem bestehenden Haupt-PDF-Anhang wird
`sammle_mahnung_anhaenge()` angehängt - gilt dadurch automatisch für **beide** Versandwege
(manueller Klick über `MahnungMailDialog.tsx` UND den automatischen `voll`-Versand aus
`automatik_lauf()`, Abschnitt F), da beide über denselben Endpunkt laufen. Kein Duplikat-Code nötig.

**Frontend:** Drei Checkboxen im Mahnstufen-Editor (`einstellungen/MahnwesenPage.tsx`,
`MahnstufeCard`) unter „Zusätzliche Dokumentanhänge beim Mail-Versand".

Live getestet (danach vollständig bereinigt): Flags testweise auf einer aktiven Mahnstufe gesetzt,
Stufe-2-Mahnung für einen Kunden mit vorheriger versendeter Mahnung erstellt und versendet -
`sammle_mahnung_anhaenge()` lieferte korrekt alle 3 Anhänge (Rechnung-PDF, die ältere Mahnung-PDF,
Kontokorrent-PDF mit `von` = Datum der ältesten versendeten Mahnung dieses Kunden). Flags und
Testdaten danach zurückgesetzt.

### Mahnstufen-Editor UX-Fixes ✅ (2026-08-02, Nutzer-Feedback)

Vier zusammengehörige Korrekturen am Mahnstufen-Editor (`einstellungen/MahnwesenPage.tsx` +
`api/mahnwesen.py`), alle aus derselben Test-Session der Nutzerin:

1. **Nur neu hinzugefügte Mahnstufen sind löschbar, Standard-Stufen nur deaktivierbar.**
   Erster Anlauf war ein kompletter Löschverbot (DELETE-Endpunkt entfernt) - die Nutzerin
   korrigierte das direkt danach: neu über „+ Neue Stufe" angelegte Stufen sollen weiterhin
   löschbar bleiben (z. B. um einen Tippfehler bei der Anlage sofort zu korrigieren), nur die vier
   mitgelieferten Standard-Stufen nicht. Migration 138 fügt `mahnstufen.system_stufe` hinzu -
   `seed_mahnstufen()` setzt es für die vier Standard-Stufen auf `True`; `mahnstufe_create()`
   lässt es für alles Neue auf `False`. `_mahnstufe_loeschbar(db, stufe)` liefert `False` sobald
   `system_stufe=True` ist, sonst `True` solange noch keine Mahnung diese Stufe per FK
   (`mahnung.mahnstufe_id`) referenziert (Karteileiche-Schutz bleibt zusätzlich bestehen, auch für
   selbst angelegte Stufen). Response-Feld `MahnstufeResponse.loeschbar` steuert im Frontend, ob
   der ×-Button überhaupt angezeigt wird; der DELETE-Endpunkt lehnt beide geschützten Fälle
   zusätzlich serverseitig mit 422 ab (unterschiedliche Fehlermeldung je nachdem ob Standard-Stufe
   oder bereits verwendete Stufe). Bestandsdatenbanken: die Migration markiert `system_stufe=True`
   für Zeilen deren `bezeichnung` einem der vier Standardnamen entspricht (best effort, wie bei
   früheren Datenfixes in dieser Datei) - alles andere bleibt bewusst löschbar.
   ⚠️ Beim Live-Test dieser Funktion wurde versehentlich die echte Stufe „1. Mahnung" gelöscht
   (zu dem Zeitpunkt existierte noch keine Mahnung, die sie referenzierte) und danach mit
   identischer Konfiguration + `system_stufe=True` wiederhergestellt.
   **Nachtrag (Nutzer-Nachfrage):** zusätzlich blockiert, wenn die Stufen-Nummer aktuell als
   „ab Stufe X"-Schwellenwert (Konsolidierung, Kundensperrung-Warnung/-Sperrung, Verzugszinsen)
   in `MahnwesenEinstellungen` konfiguriert ist - diese Schwellenwerte speichern nur die reine
   `stufe`-Nummer ohne Fremdschlüssel, ein Löschen hätte die Schwelle sonst lautlos ins Leere
   zeigen lassen. `_mahnstufe_loesch_sperrgrund(db, stufe)` liefert `None` wenn löschbar, sonst
   den konkreten Sperrgrund als Fehlertext (Standard-Stufe / bereits verwendet / als Schwellenwert
   konfiguriert) - sowohl für das `loeschbar`-Response-Feld als auch für die 422-Fehlermeldung im
   DELETE-Endpunkt genutzt.
2. **Keine Mahngebühr auf der ersten Stufe.** Eine formlose Zahlungserinnerung ist noch keine
   Mahnung - eine Gebühr darauf wäre rechtlich nicht haltbar. Die Checkbox „Mahngebühr auf dieser
   Stufe berechnen" wird für die Stufe mit der niedrigsten `stufe`-Nummer (Position, nicht
   Aktiv-Status - eine deaktivierte Zahlungserinnerung bleibt trotzdem die „erste Stufe") im
   Frontend gar nicht mehr angezeigt; `mahnstufe_update()` weist zusätzlich serverseitig jeden
   Versuch, `mahngebuehr_aktiv=true` auf dieser Stufe zu setzen, mit 422 zurück (Verteidigung gegen
   direkte API-Aufrufe).
3. **Speichern-Feedback.** `MahnstufeCard` zeigt nach erfolgreichem Speichern für 2,5 Sekunden ein
   grünes „Gespeichert ✓" neben dem Button, bei einem Fehler die Fehlermeldung in Rot - vorher gab
   es überhaupt kein sichtbares Feedback, ob ein Klick auf „Speichern" etwas bewirkt hatte.
4. **Neue Stufen werden immer vor der letzten eingefügt.** `mahnstufe_create()` ignoriert die vom
   Client übergebene `stufe`-Nummer und berechnet sie selbst: die neue Stufe übernimmt die Position
   der bisher letzten Stufe (höchste `stufe`-Nummer, unabhängig von deren Aktiv-Status), die alte
   letzte Stufe rückt eine Position weiter nach hinten. So bleibt z. B. „Letzte Mahnung vor
   Inkasso" strukturell immer die letzte Stufe, und „ab Stufe X"-Schwellenwerte (Konsolidierung,
   Kundensperrung, Verzugszinsen) geraten durch neu angelegte Zwischenstufen nicht durcheinander.

Live getestet: PUT mit `mahngebuehr_aktiv=true` auf Stufe 1 liefert 422 mit der erwarteten
Fehlermeldung; neue Stufe eingefügt bei bestehender Reihenfolge mit einer inaktiven
Zwischenstufe - korrekt vor der bisher letzten Stufe eingefügt, unabhängig von deren Aktiv-Status
(Testdaten danach entfernt); DELETE auf einer System-Stufe liefert 422 mit
„Diese Standard-Mahnstufe kann nicht gelöscht werden"; die von der Nutzerin selbst live über
„+ Neue Stufe" angelegten Stufen zeigen korrekt `loeschbar=true`; eine neu angelegte Testtufe mit
`verzugszinsen_ab_stufe` testweise auf ihre Nummer gesetzt lieferte beim Löschversuch korrekt 422
(„...als Schwellenwert...hinterlegt"), nach Zurücksetzen des Schwellenwerts ließ sie sich löschen
(204). Schwellenwert und Testdaten danach exakt zurückgesetzt.

---

## Abschnitt E – Kundensperrung + Inkasso-Paket + Mahngebühr-Buchung

**Status: 🟡 fast erledigt (2026-08-02)** – Kundensperrung ✅, Inkasso-Paket ✅,
Mahngebühr/Verzugszinsen-Verrechnung (manuell + Bankabgleich + Kontokorrent) ✅. Nur die
Zahlungsverteilung bei konsolidierten Mahnungen bleibt zurückgestellt (siehe unten, eigener
Infrastruktur-Aufwand).

### Kundensperrung ✅ (zweistufig: Warnung + Sperrung unabhängig, Migration 133)

**Redesign 2026-08-02** (Nutzer-Vorgabe: „Wenn ich für eine Mahnstufe erst noch eine Warnung haben
möchte, möchte ich vielleicht bei der nächsten Mahnstufe eine Kundensperre") - ersetzt das
ursprüngliche Einzelfeld-Modell (`kundensperrung_ab_stufe` + `kundensperrung_modus` mit
`warnung`|`sperrung`) durch **zwei unabhängige, jeweils optionale Schwellen**:
`kundensperrung_warnung_ab_stufe` und `kundensperrung_sperrung_ab_stufe`
(`mahnwesen_einstellungen`, beide `INTEGER NULL` - `NULL` = Schwelle deaktiviert). Beide können
gleichzeitig aktiv sein (typisch: Warnung ab Stufe 2, harte Sperre erst ab Stufe 3) oder auch nur
eine von beiden. Migration 133 überführt bestehende Installationen automatisch: alter Modus
`sperrung` → Wert wandert nach `kundensperrung_sperrung_ab_stufe`, alter Modus `warnung` → Wert
wandert nach `kundensperrung_warnung_ab_stufe`. Die alten Spalten `kundensperrung_ab_stufe`/
`kundensperrung_modus` bleiben unbenutzt in der DB stehen (kein `DROP COLUMN` in SQLite,
Risiko/Aufwand-Abwägung).

`kunden` hat entsprechend zwei unabhängige Flags: `mahnung_gesperrt` (hart, blockiert) und
`mahnung_warnung` (weich, nur Hinweis) - beide können gleichzeitig `true` sein.

Beide Flags werden schon beim **Anlegen des Mahnungs-Entwurfs** gesetzt (nicht erst beim Versand -
explizite Nutzer-Vorgabe), sobald `kundensperrung_aktiv` und die erreichte Stufe die jeweilige
Schwelle erreicht/überschreitet (`erstellen()`, `api/mahnwesen.py`). Werden beim Löschen des
auslösenden Entwurfs unabhängig voneinander symmetrisch zurückgesetzt (`mahnung_loeschen()`),
sofern kein anderer Grund mehr besteht - dabei zählt der **kundenweite** Maximalwert von
`rechnungen.mahnstufe_aktuell` über alle Rechnungen des Kunden, nicht nur die der gelöschten
Mahnung zugeordneten (Kundensperrung ist bewusst kundenweit, nicht pro Rechnung). Live getestet:
Lösch-Reihenfolge Stufe 3 → Stufe 2, beide Flags reverten exakt dann, wenn kein verbleibender
Mahnstufen-Wert mehr die jeweilige Schwelle erreicht.

**Wirkung**: `pruefe_kundensperre()` (`api/mahnwesen.py`) prüft nur noch `mahnung_gesperrt` (hartes
Flag, 403) - `mahnung_warnung` blockiert serverseitig nie, das Frontend zeigt dafür lediglich einen
Warnhinweis an (siehe unten). Kein `kundensperrung_modus`-Zweig mehr nötig, da die Unterscheidung
jetzt strukturell über die zwei Flags läuft statt über einen Modus-Wert.

Zeitpunkt-Frage, von der Nutzerin explizit bestätigt (2026-08-02, nach anfänglichem
Missverständnis - die ursprüngliche Frage war zweideutig, deckte ungewollt zwei verschiedene
Zeitpunkte ab):
1. *Wann werden `mahnung_gesperrt`/`mahnung_warnung` gesetzt* (Mahnungs-Seite): schon beim Anlegen
   des Mahnungs-**Entwurfs**, nicht erst beim Versand.
2. *Wann greift die Sperre beim Erstellen eines NEUEN Dokuments* (Rechnung/Angebot/Auftrag-Seite):
   ebenfalls schon beim **Entwurf** des neuen Dokuments, nicht erst beim Finalisieren/Absenden -
   `pruefe_kundensperre()` läuft unconditional vor der `ist_entwurf`-Verzweigung, ein gesperrter
   Kunde kann also nicht mal einen vorbereitenden Entwurf bekommen.

Deckt **alle** Ausgangsdokumente ab, nicht nur Rechnungen (Nutzer-Vorgabe: „Von Angebot, Auftrag,
über Proforma, Lieferschein bis Rechnung"). Technisch reicht das, weil Angebot/Lieferschein/
Proforma/Rechnung alle über `POST /api/rechnungen` laufen (`dokument_typ`-Unterscheidung, Gutschrift
bewusst ausgenommen - mindert eine Forderung statt neue zu schaffen) und Auftrag über die eigene
`POST /api/rechnungen/auftraege`. Die vielen „Dokument X aus Y erstellen"-Konvertierungs-Endpunkte
(Angebot→Rechnung etc.) sind bewusst **nicht** einzeln abgesichert - bei einer bereits vorher
angelegten, freigegebenen Vorstufe schien eine nachträgliche Blockade der Konvertierung eher
störend als schützend; kann bei Bedarf ergänzt werden.

Manuelles Aufheben: `POST /api/mahnwesen/kunden/{kunde_id}/entsperren` (z.B. nach Zahlungseingang
oder individueller Absprache) setzt **beide** Flags zurück - Buttons/Badges getrennt im
Kundenstamm-Formular-Header (`KundenPage.tsx`): `🔒 Kundensperrung` (rot) bei `mahnung_gesperrt`,
`⚠️ Mahnwarnung` (amber) bei `mahnung_warnung`, „Entsperren" erscheint sobald mindestens eins der
beiden Flags gesetzt ist. `RechnungForm` (`RechnungenPage.tsx`) zeigt zwei unabhängige Banner: rot
(blockierend) bei `mahnung_gesperrt`, amber (informativ) bei `mahnung_warnung` - der eigentliche
403-Fehlerfall läuft über die schon vorhandene generische Fehleranzeige (`request()` reicht
`detail` als `Error.message` durch).

Einstellungsseite (`einstellungen/MahnwesenPage.tsx`): zwei getrennte, jeweils nullbare Dropdowns
„Warnung ab Stufe" / „Sperrung ab Stufe" (Option „— keine —"), beide gefiltert auf aktive
Mahnstufen (`aktiveStufenSortiert`, wie auch Konsolidierung und Verzugszinsen-Schwelle - Nutzer-
Vorgabe: „Auch hier nur aktivierte Mahnstufen zur Auswahl anzeigen").

Live end-to-end getestet: Warnung-Schwelle allein auslösen (Sperre bleibt `false`) → zusätzlich
Sperr-Schwelle erreichen (beide Flags gleichzeitig `true`) → Entwürfe absteigend löschen → beide
Flags korrekt und unabhängig voneinander auf `false` zurückgesetzt, sobald kein Rechnung des Kunden
mehr die jeweilige Schwelle erreicht.

### Inkasso-Paket ✅ (2026-08-02)

`GET /api/mahnwesen/kunden/{kunde_id}/inkasso-paket` (`api/mahnwesen.py`, `generate_inkasso_zip()`) -
ZIP-Download mit fertig zusammengestellten Unterlagen für Inkassobüro/Anwalt:

- `00_Deckblatt.pdf` - neu gebaut (`utils/pdf_inkasso_deckblatt.py`, gleicher Stil wie
  `pdf_kontokorrent.py`): Tabelle offene Rechnungen (Nummer/Datum/Fällig/Brutto/Offen/Tage
  überfällig) mit Summenzeile, Mahnhistorie-Tabelle (Mahnnr./Bezeichnung/Stufe/Versendet
  am/Gesamtforderung), Inhaltsverzeichnis aller ZIP-Dateien.
- `01_Kontokorrent.pdf` - volle Wiederverwendung von `_kontokorrent_bewegungen()` +
  `erstelle_kontokorrent_pdf()` (`api/kunden.py`/`utils/pdf_kontokorrent.py`, bereits für den
  Kontokorrent-Tab im Kundenstamm vorhanden), Zeitraum ab ältester offener Rechnung bis heute.
- `rechnungen/<Nummer>.pdf` - je offene Rechnung, erzeugt über direkten In-Prozess-Aufruf von
  `rechnung_als_pdf()` (`api/rechnungen.py`) statt Neuimplementierung - dadurch automatisch
  korrekt: Original-Archiv+Kopie-Stempel falls schon einmal gedruckt, `absender_snapshot` falls
  vorhanden (GoBD), Bezugsdokumente-Kette, ZUGFeRD-Logik etc. Kein `nur_ansehen` - beim allerersten
  Druck greift die normale Erstarchivierung (`original_pdf_pfad` wird gesetzt), das ist im
  Inkasso-Kontext korrekt (das Dokument verlässt hier tatsächlich zum ersten Mal das Haus, falls
  es das nicht schon vorher tat).
- `mahnungen/<Mahnnummer>.pdf` - je versendete Mahnung, `mahnung_pdf_bytes(..., nur_ansehen=True)`
  (bereits vorhanden aus Abschnitt C) - reiner Nachdruck, keine Statusänderung nötig, die
  Mahnungen sind schon `versendet`.

**Voraussetzungen (beide, sonst 404 mit Klartext-Meldung):** mindestens eine offene Rechnung
(`ist_entwurf=false`, `storniert=false`, `zahlungsstatus != bezahlt`, `dokument_typ=Rechnung`) UND
mindestens eine `versendete` Mahnung des Kunden - ein Inkasso-Paket ohne vorherige Mahnung ergibt
keinen Sinn und würde sonst versehentlich zu früh greifen.

**Frontend:** Button „📦 Inkasso-Paket" in `MahnwesenPage.tsx` (`KundeDetail`, neben der
Mahnungen-Historie-Überschrift), sichtbar sobald mindestens eine Mahnung `versendet` ist (Spiegel
der Backend-Bedingung). `downloadInkassoPaket()` (`api/client.ts`) folgt dem bestehenden
ZIP-Download-Muster von `downloadGobdExport()` (fetch → Blob → `_triggerBlobDownload`) statt
`openUrl()`, da die URL keine `.zip`-Endung trägt und `openUrl()`s Download-Erkennung sonst nicht
greifen würde.

Live getestet: Kunde ohne offene Rechnungen → 404, Kunde mit offenen Rechnungen aber ohne
versendete Mahnung → 404 mit eigener Meldung, Kunde mit beidem (Digital Solutions GmbH) → ZIP mit
12 Dateien, Deckblatt-Inhalt via `pdftotext` verifiziert (Tabellen, Summen, Inhaltsverzeichnis
korrekt).

### Mahngebühr/Verzugszinsen-Verrechnung ✅ (2026-08-02, manuell + Bankabgleich + Kontokorrent)

**Design-Entscheidung** (Nutzer-Vorgabe, `AskUserQuestion`): bei manueller Zahlungserfassung mit
Betrag über dem Rechnungsrest wird automatisch mitverrechnet, kein separater Buchen-Schritt -
analog zum bereits bestehenden Verhalten beim Bank-Import. Zweite Klarstellung des Nutzers: "Wenn
keine Mahngebühren und Zinsen offen sind ist es Guthaben des Kunden" - der nach vollständiger
Verrechnung verbleibende Rest wird als `Forderung(typ="kundenguthaben")` erfasst statt die
Buchung zu blockieren.

**Migration 134:** `mahnungen.mahngebuehr_bezahlt` + `mahnungen.verzugszinsen_bezahlt`
(`NUMERIC(12,2) DEFAULT 0`) - **zwei getrennte** Felder statt einem Summenfeld, da Mahngebühr und
Verzugszinsen unterschiedliche Kategorien/SKR-Konten haben und getrennt gebucht werden müssen.

**Neues Modul `utils/mahngebuehr_verrechnung.py`** (von `api/rechnungen.py` UND `api/bank_import.py`
genutzt, da beide eine eigene Journaleintrag-Erzeugung und Belegnummern-Funktion haben - daher
`naechste_belegnr_fn` als Parameter injiziert statt eine dritte Variante einzuführen):
- `offene_mahngebuehr_summe(db, rechnung_id)` - noch offener Anteil aus `mahngebuehr` +
  `verzugszinsen` aller **nicht-konsolidierten** (`anzahl_verknuepfte_rechnungen == 1`),
  `versendeten` Mahnungen dieser Rechnung.
- `verrechne_mahngebuehren(db, rechnung_id, betrag, ...)` - verteilt den Betrag auf offene
  Mahnungen (älteste zuerst, je Mahnung erst Gebühr dann Zinsen), bucht je Kategorie einen
  eigenen Journaleintrag (Einnahme, 0% USt - Mahngebühr = Schadensersatz §288 BGB, Verzugszinsen
  = Zinsertrag, beide nicht umsatzsteuerbar), aktualisiert die `_bezahlt`-Felder. Gibt den nicht
  verrechenbaren Rest zurück (→ Kundenguthaben).

Bewusst nur für **nicht-konsolidierte** Mahnungen (identische Einschränkung wie die zurückgestellte
„Zahlungsverteilung bei konsolidierten Mahnungen" unten) - für eine Mahnung über mehrere
Rechnungen gibt es keine Infrastruktur, einen Betrag aufzuteilen.

**`api/rechnungen.py` (`zahlung_bar_erstellen`, Standard- UND Split-Zweig):** Validierung erweitert
- bei Ausgangsrechnungen wird ein Betrag über dem Restbetrag nicht mehr mit 422 blockiert, sondern:
Rechnungsanteil normal buchen (gedeckelt auf Restbetrag) → Überschuss zuerst gegen
`offene_mahngebuehr_summe()` verrechnen → danach verbleibender Rest als `Forderung`. Eingangsrechnungen
bleiben unverändert strikt begrenzt (kein Mahnwesen für Lieferanten). Gutschrift-Zweig unverändert.

**`api/bank_import.py` (`_buche_pfad_a`):** `verrechne_mahngebuehren()` läuft jetzt vor der
bestehenden Kundenguthaben-Erstellung, reduziert `surplus` entsprechend - der bereits vorhandene
Guthaben-Code direkt danach bekommt dadurch automatisch nur noch den tatsächlichen Rest.

**Kontokorrent-Erweiterung (`api/kunden.py`):** neuer Helper `_mahngebuehr_bewegungen()` liefert
sowohl die **Forderungs-Zeile** (pro versendeter Mahnung mit `mahngebuehr`/`verzugszinsen` > 0,
Datum = Mahnungs-Versand, Typ `mahngebuehr`/`verzugszinsen`) als auch die zugehörige
**Zahlungs-Zeile** (aus den Journaleinträgen von `verrechne_mahngebuehren()`, siehe Bugfix
unten - beide über `kunde_id` + Kategorie geholt, nicht über `rechnung_id`). Ohne die
Forderungs-Zeile wäre der Saldo falsch (Zahlung ohne zugehörige Forderung). Sortier-Tiebreaker
`_TYP_SORT_PRIO` sorgt dafür, dass bei gleichem Datum die Forderung vor ihrem Ausgleich erscheint.
Betrifft `kontokorrent_kunde()` (Kundenstamm-Tab) UND `_kontokorrent_bewegungen()` (PDF-Export,
Mail-Versand, Inkasso-Paket) gleichermaßen - neue Typen `mahngebuehr`/`verzugszinsen` in
`pdf_kontokorrent.py` (`_TYP_LABEL`) und `KundenPage.tsx` (`typLabel`/`typFarbe`, orange) ergänzt.

**Bugfix noch am selben Tag gefunden (Nutzer-Nachfrage "läuft der Mahnstatus weiter?" führte zur
Prüfung):** Die Verrechnungs-Journaleinträge trugen anfangs `rechnung_id` (für die
Kontokorrent-Anzeige gedacht). Problem: `_aktualisiere_zahlungsstatus()` (`api/rechnungen.py`)
summiert bei **jeder** Neuberechnung von `rechnung.bezahlt_betrag` ALLE Journaleinträge mit
passender `rechnung_id`, ohne Kategorie-Filter - eine spätere Neuberechnung (z. B. Korrektur
einer anderen Zahlung derselben Rechnung über `zahlung_korrigieren`) hätte die Mahngebühr
fälschlich als zusätzliche Teilzahlung der Rechnung mitgezählt und `bezahlt_betrag` über
`brutto_gesamt` hinaus aufgebläht (negativer Restbetrag möglich). Fix: `rechnung_id` bei diesen
Buchungen entfernt (nur noch `kunde_id`), Kontokorrent holt sich beide Zeilen jetzt aktiv über
`kunde_id` + Kategorie „Mahngebühren"/„Verzugszinsen (Einnahme)" (s.o.) statt sich auf die
allgemeine `rechnung_id`-Zahlungen-Query zu verlassen. Live verifiziert: `bezahlt_betrag` bleibt
nach der Verrechnung exakt `brutto_gesamt` (nicht mehr), Neuberechnung über
`rechnung.journaleintraege` liefert denselben korrekten Wert, Kontokorrent zeigt beide Zeilen
weiterhin korrekt.

**Lücke geschlossen (2026-08-02, Nutzer-Nachfrage "Wie treibe ich die Mahngebühr ein?"):**
Ursprünglich blockierte `zahlung_bar_erstellen` mit 409, sobald eine Rechnung bereits vollständig
bezahlt war - auch wenn aus einer Mahnung noch Gebühr/Verzugszinsen offen waren, gab es keinen Weg,
das nachträglich separat zu verbuchen. Fix: die Sperre greift jetzt nur noch, wenn **zusätzlich**
`offene_mahngebuehr_summe()` = 0 ist. Ist die Rechnung bezahlt, aber Gebühr/Zinsen offen, bleibt der
Dialog nutzbar und bucht ausschließlich gegen die offene Gebühr (kein Rechnungsanteil mehr, da
Restbetrag ja bereits 0 ist - der normale Rechnungs-Buchungsblock wird in diesem Fall übersprungen,
kein sinnloser 0-€-Journaleintrag).

**Frontend:** `hatZahlungsoption` (`RechnungenPage.tsx`) berücksichtigt jetzt zusätzlich zum
Restbetrag die offene Mahngebühr (`RechnungMahnungenSection`-Query wiederverwendet, gleicher
React-Query-Cache-Key, kein Extra-Request) - der „Zahlung kassieren"-Button bleibt also sichtbar
und heißt dann „Mahngebühr/Zinsen nachbuchen" mit dem offenen Betrag in Klammern.
`ZahlungsDialog` zeigt in diesem Modus einen eigenen Hinweis + befüllt den Betrag automatisch mit
der offenen Gebühr statt mit dem (dann 0-€-)Restbetrag. Zusätzlich zeigt die „Mahnstatus"-Sektion
auf der Rechnung sowie die Mahnwesen-Kundenansicht und der Kundenstamm-Mahnstatus-Badge jetzt
überall „X € Gebühr/Zinsen offen" pro Mahnung an (`mahnung.mahngebuehr_bezahlt`/
`verzugszinsen_bezahlt` neu auf `MahnungResponse`/`MahnungHistorieItem` exponiert).

Live getestet (vier Szenarien, danach vollständig bereinigt): Teilverrechnung (25 von 40 € Gebühr,
kein Kundenguthaben), volle Verrechnung + Kundenguthaben-Rest (40 von 40 € + 10 € Guthaben,
manueller Pfad), volle Verrechnung + Kundenguthaben-Rest über den Bank-Import-Pfad
(`POST /transaktion/{id}/buchen`, 5 von 5 € + 15 € Guthaben), sowie das eigentliche Lücken-Szenario:
Rechnung exakt (ohne Überschuss) bezahlt → Gebühr bleibt bei 0 € bezahlt → separater
Folgezahlung-Aufruf über 40 € bucht die Gebühr vollständig nach (`bezahlt_betrag` der Rechnung
bleibt dabei unverändert) → danach blockt der Endpunkt wieder korrekt mit 409. Jeweils
Journaleintrag-Kategorie/-Betrag, `mahnung.*_bezahlt`, `Forderung` und Kontokorrent-Saldo direkt in
der DB verifiziert.

### Kundenweite Übernahme offener Gebühr/Zinsen + Zinseinfrierung ✅ (2026-08-02)

**Problem (Nutzer-Vorgabe):** "Solange offene Beträge vorhanden sind muss es auch in die nächste
Mahnstufe gehen. Ist beispielsweise noch eine weitere Rechnung offen und bekommt einen neuen
Mahnstatus wird der Betrag dort wieder zusammengefasst. Sonst gibt es keine Übereinstimmung mit
dem Kontokorrent." Bis dahin war Mahngebühr/Verzugszinsen rein an die einzelne Rechnung gebunden -
wurde diese bezahlt, aber eine ANDERE Rechnung desselben Kunden erreichte eine neue Mahnstufe, sah
die neue Mahnung die alte offene Gebühr nicht. Kontokorrent (kundenweit) und Mahnflow liefen
auseinander.

**Migration 135:** `mahnungen.uebertragen_in_mahnung_id` (FK → mahnungen.id, SET NULL) +
`mahnungen.uebernommene_gebuehr_vorperioden` (NUMERIC(12,2)).

**`_offene_gebuehr_vorperioden_kunde(db, kunde_id)`** (`api/mahnwesen.py`): summiert offene
Gebühr/Zinsen aller `versendeten`, noch nicht `uebertragen_in_mahnung_id`-markierten Mahnungen
eines Kunden - unabhängig davon, ob deren ursprüngliche Rechnung inzwischen bezahlt ist. Wird in
**beiden** `erstellen()` UND `vorschau()` aufgerufen (damit die Vorschau exakt zeigt, was beim
tatsächlichen Erstellen passiert) und direkt in die neuen Felder `mahngebuehr`/`verzugszinsen` der
neuen Mahnung eingerechnet (nicht als separates Feld getrackt) - dadurch funktioniert die
bestehende Zahlungsverrechnung (`mahngebuehr_bezahlt`/`verzugszinsen_bezahlt`) unverändert weiter,
ohne einen dritten Zahlungs-Tracking-Satz einzuführen. `uebernommene_gebuehr_vorperioden` ist rein
informativ (PDF/Audit: wie viel des Gesamtbetrags aus einer Vorperiode stammt). Die alten
Mahnungen werden mit `uebertragen_in_mahnung_id = neue_mahnung.id` markiert und dadurch aus
`_offene_1zu1_mahnungen()` (`utils/mahngebuehr_verrechnung.py`) sowie aus allen „X € offen"-Badges
(Mahnwesen-Kundenansicht, Kundenstamm, Rechnungsdetail) ausgeschlossen - sie zeigen stattdessen
„Gebühr/Zinsen in neuere Mahnung übernommen".

**PDF** (`utils/pdf_mahnung.py`, `erstelle_mahnung_pdf()`): neue Zeile „davon aus vorheriger
Mahnung übernommen" zwischen Mahngebühr/Verzugszinsen und Gesamtforderung, sichtbar für den Kunden
(Nutzer-Entscheidung über `AskUserQuestion`: eigene Position statt nur interner Verrechnung -
entspricht üblicher Inkasso-Praxis).

**Zinseinfrierung bei Zahlung** (separater, vorgelagerter Fix - Nutzer-Vorgabe: "Was eingefroren
werden muss ist die Zinsberechnung bis zur Zahlung des Rechnungsbetrages"): Verzugszinsen wurden
bisher nur bis zum Tag der Mahnungs-**Erstellung** berechnet, nicht bis zur tatsächlichen
**Zahlung** - lag dazwischen mehr als ein Tag, gingen diese Tage Zinsertrag schlicht verloren (§288
BGB verlangt Zinsen bis zur tatsächlichen Zahlung). Neue Funktion
`finalisiere_verzugszinsen_bei_zahlung(db, rechnung, zahlungsdatum)` (`api/mahnwesen.py`),
aufgerufen aus `_aktualisiere_zahlungsstatus()` (`api/rechnungen.py`) sobald eine Ausgangsrechnung
vollständig bezahlt ist: berechnet die Verzugszinsen einer offenen, nicht konsolidierten Mahnung
dieser Rechnung neu mit `bis_datum = tatsächliches Zahlungsdatum` statt Mahnungs-Erstellungsdatum,
erhöht `mahnung.verzugszinsen` falls der neue Wert höher ist. Zinsformel aus `_berechne_mahnung()`
in wiederverwendbaren Helper `_verzugszinsen_fuer_betrag()` ausgelagert. Bewusst nur für
nicht-konsolidierte Mahnungen (gleiche Einschränkung wie überall in diesem Abschnitt - Zinsanteil
je Rechnung ist bei einer konsolidierten Mahnung nicht sauber trennbar).

Live getestet (danach vollständig bereinigt):
- **Zinseinfrierung:** Stufe-4-Mahnung erstellt (34 Tage überfällig → 5,55 € Zinsen), Rechnung 8
  Tage später bezahlt (Zahlungsdatum im Request) → `mahnung.verzugszinsen` korrekt auf 6,85 €
  (42 Tage) erhöht.
- **Kundenweite Übernahme:** Rechnung A gemahnt (Stufe 2, 40 € Gebühr, isoliert getestet mit
  temporär deaktivierter Konsolidierung) → exakt bezahlt (Gebühr bleibt bei 0 € verrechnet offen)
  → Rechnung B desselben Kunden erreicht Stufe 2 → `/vorschau` zeigt korrekt
  `mahngebuehr=80,00 (40 eigene + 40 übernommen), gebuehr_vorperioden=40,00,
  gesamtforderung=615,50` → `/erstellen` persistiert identisch → alte Mahnung A trägt
  `uebertragen_in_mahnung_id` auf die neue Mahnung → PDF der neuen Mahnung zeigt „Mahngebühr 80,00 €
  / davon aus vorheriger Mahnung übernommen 40,00 € / Gesamtforderung 615,50 €" →
  `offene_mahngebuehr_summe()` liefert für Rechnung A korrekt 0 (übertragen), für Rechnung B nach
  Versand korrekt 80 € (vorher, im Entwurfsstatus, korrekt 0 - nur versendete Mahnungen zählen als
  verbindliche Forderung).

### Mahnflow ohne offene Rechnung (Kontokorrent-Konsistenz) ✅ (2026-08-02)

**Problem (Nutzer-Vorgabe):** "Das ist wiederum inkonsistent mit dem Kontokorrent. Solange der
Kontokorrent nicht ausgeglichen ist müssen die Mahnungsstufen weiterlaufen." Bis dahin hing der
komplette Mahnflow (Fällig-Liste, Kundenübersicht, `/vorschau`, `/erstellen`) ausschließlich an
`Rechnung.zahlungsstatus IN (offen, teilweise)`. Ein Kunde mit **nur noch offener
Mahngebühr/Verzugszinsen** (Rechnung bereits bezahlt, keine andere Rechnung offen) verschwand
komplett aus dem Mahnwesen - obwohl der Kontokorrent-Saldo ≠ 0 war und `_offene_gebuehr_
vorperioden_kunde()` (siehe oben) diesen Betrag bei der nächsten *fremden* Mahnung zwar
mitgezogen hätte, aber nie von selbst zu einer eigenen Eskalation führte.

**Nutzer-Vorgabe zur Abgrenzung:** "ausgenommen neue Rechnungen die noch nicht im Mahnstatus
sind" - eine druckfrische, noch nie gemahnte Rechnung wird durch diese Erweiterung NICHT vorzeitig
in den Mahnflow gezogen; die neue Eskalation greift ausschließlich für bereits gemahnte, noch
offene Beträge.

**Rechtliche Weichenstellung (`AskUserQuestion`):** Eine neue Mahnstufe, die nur noch eine alte
Gebühr verfolgt (keine Rechnung mehr offen), berechnet **keine neue Mahngebühr** (Gebühr-auf-
Gebühr ist rechtlich riskant) und **keine neuen Verzugszinsen** (Zinsen laufen nur bis zur
Zahlung der Hauptforderung, siehe Zinseinfrierung oben - danach gibt es keine neue Verzugsbasis
mehr). Sie trägt ausschließlich den bereits eingefrorenen Betrag weiter, eskaliert nur die Stufe
(neues PDF, ggf. greift Kundensperrung weiter).

**Neue Bausteine:**
- `_faellige_naechste_stufe_gebuehr_kunde(db, kunde_id, heute)` (`api/mahnwesen.py`) - wie
  `_faellige_naechste_stufe()`, aber für einen Kunden statt eine Rechnung: nutzt die höchste noch
  nicht übertragene, versendete Mahnung mit offenem Rest als Basis für den `tage_nach_vorheriger`-
  Countdown.
- `kunden_uebersicht()` zweite Passe: Kunden ohne offene Rechnung, aber mit offener Gebühr,
  erscheinen zusätzlich mit `nur_offene_gebuehr=true`, `rechnungen=[]`,
  `offener_betrag_gesamt` = offene Gebühr/Zinsen-Summe. Der frühere Early-Return bei „keine
  relevanten Rechnungen" wurde entfernt, damit diese zweite Passe immer läuft.
- `MahnungVorschauRequest`/`MahnungErstellenRequest`: `rechnung_ids` jetzt `= []` erlaubt,
  zusätzliches Feld `kunde_id` für den Rechnung-losen Modus.
- `_berechne_mahnung_gebuehr_only()` / `_erstellen_gebuehr_only()`: erzeugen eine Mahnung mit
  `rechnung_ids=[]` (0 `MahnungRechnung`-Zeilen), `mahngebuehr`/`verzugszinsen` = 1:1 der
  übernommenen Vorperioden-Summe (keine eigene Berechnung).
- **`utils/mahngebuehr_verrechnung.py` komplett auf kundenweit umgestellt** (`_offene_mahnungen_
  kunde()`, `offene_mahngebuehr_summe_kunde()`, `verrechne_mahngebuehren_kunde()`) - die frühere
  Beschränkung auf „genau eine verknüpfte Rechnung" entfällt, da die Journaleinträge ohnehin keine
  `rechnung_id` mehr tragen (siehe Bugfix weiter oben) und eine Zahlung auf irgendeine Rechnung
  eines Kunden jetzt konsequent gegen jede offene Gebühr dieses Kunden verrechnet werden darf -
  auch gegen konsolidierte oder rechnungslose Mahnungen. Die alten `_rechnung_id`-Funktionen
  bleiben als dünne Wrapper für `zahlung_bar_erstellen`/`_buche_pfad_a` erhalten.
- **Neuer Endpunkt `POST /mahnwesen/kunden/{kunde_id}/gebuehr-zahlung`**: kundenweite Zahlung ohne
  Rechnungsbezug (Nutzer-Vorgabe: "Wir müssen das bauen um die Nutzer nicht zu überfordern die von
  Journalbuchungen keinen Plan haben" - normale Nutzer sollen dafür keine freie Journalbuchung
  anlegen müssen). Überschuss über die offene Summe hinaus wird wie bei den anderen Zahlungswegen
  automatisch als `Forderung(typ="kundenguthaben")` erfasst.
- **`generate_inkasso_zip()`** akzeptiert jetzt auch Kunden ohne offene Rechnung (nur noch
  `00_Deckblatt.pdf` + `01_Kontokorrent.pdf` + `mahnungen/*.pdf`, kein `rechnungen/`-Ordner);
  Kontokorrent-Zeitraum fällt in diesem Fall auf die älteste Mahnung zurück (kein Rechnungsdatum
  verfügbar).

**Frontend (`MahnwesenPage.tsx`):** `KundeDetail` zeigt bei `kunde.nur_offene_gebuehr` einen
eigenen Block „Keine Rechnung mehr offen – noch X € Mahngebühr/Verzugszinsen offen" statt der
Rechnungsliste, mit eigenem „Restgebühr bezahlen"-Formular (Betrag/Datum/Zahlungsart, ruft
`bezahleMahngebuehrKunde()`) und eigenen Vorschau/Erstellen-Mutationen
(`mahnungVorschauGebuehr`/`mahnungErstellenGebuehr`, `kunde_id` statt `rechnung_ids`). Filter-Logik
(`kundeHatStatus`) ergänzt, damit solche Kunden nicht aus allen Status-Tabs verschwinden, solange
noch keine Eskalation fällig ist.

Live getestet (durchgehendes Szenario, danach vollständig bereinigt): Rechnung gemahnt (Stufe 2,
40 € Gebühr) → exakt bezahlt (Gebühr bleibt offen) → Kunde erscheint korrekt mit
`nur_offene_gebuehr=true` in der Übersicht → `/vorschau` mit `kunde_id` + Stufe 4 zeigt korrekt
`mahngebuehr=40, gebuehr_vorperioden=40, gesamtforderung=40` (keine neue Gebühr) → `/erstellen`
persistiert identisch, PDF zeigt „Mahngebühr 40,00 € / davon aus vorheriger Mahnung übernommen
40,00 € / Gesamtforderung 40,00 €" → Teilzahlung 25 € über den neuen Endpunkt korrekt verrechnet →
Restzahlung 25 € (15 € verrechnet + 10 € Kundenguthaben) → Kunde verschwindet danach korrekt aus
der Übersicht → Inkasso-Paket für den zwischenzeitlich rechnungslosen Zustand liefert 5 Dateien
(Deckblatt, Kontokorrent, 3 Mahnungs-PDFs, kein Rechnungen-Ordner).

### Zahlungsverteilung bei konsolidierten Mahnungen ✅ (2026-08-02)

**Problem:** Zahlt ein Kunde die Gesamtforderung einer konsolidierten Mahnung (Stufe ≥
`konsolidiert_ab_stufe`, PDF-Zahlungsreferenz = Mahnnummer statt einzelner Rechnungsnummer, siehe
Abschnitt C) in einer Überweisung, deckt dieser eine Betrag mehrere `rechnung_id`s gleichzeitig
ab. Recherche ergab: dafür gab es **keine bestehende Infrastruktur** (Split-Zahlung teilt nur
Kategorien derselben Rechnung auf, `Journaleintrag.rechnung_id` ist ein einzelnes FK-Feld, Bank-
Import matchte strikt 1:1 Betrag↔Rechnung).

**Design-Entscheidungen (Nutzer-Vorgabe 2026-08-02):**
- Verteilung: **älteste fällige Rechnung zuerst voll auffüllen (FIFO)**, nicht anteilig - entspricht
  dem gängigen Buchhaltungsprinzip und ist für die Nutzerin leicht nachvollziehbar.
- Umfang: **beide** ursprünglich zur Wahl gestellten Optionen - manuelle Zahlungserfassung UND
  automatisches Bank-Import-Matching ("Also beides müsste möglich sein. Punkt 1 und 2").

**`verteile_mahnung_zahlung(db, mahnung, betrag, datum, zahlungsart)`** (`api/mahnwesen.py`) - die
zentrale, von beiden Wegen genutzte Funktion:
1. Lädt die verknüpften Rechnungen über `MahnungRechnung`, filtert auf noch offene (>0,004 €) und
   sortiert nach `faellig_am` (älteste zuerst).
2. Bucht je Rechnung über `zahlung_bar_erstellen()` (`api/rechnungen.py`, In-Prozess-Aufruf wie an
   anderen Stellen dieser Datei) **exakt** `min(rest, offen)` - nie mehr, damit dessen eigene
   Überschuss-Logik nicht einspringt und die Aufteilung hier vollständig selbst kontrolliert bleibt.
3. Ein danach verbleibender Rest (oder der komplette Betrag bei einer rechnungslosen Mahnung,
   `nur_offene_gebuehr`) geht über das bereits bestehende `verrechne_mahngebuehren_kunde()` gegen
   offene Mahngebühr/Verzugszinsen des Kunden.
4. Ein danach noch verbleibender Überschuss wird - wie bei allen anderen Zahlungswegen dieser App -
   als `Forderung(typ="kundenguthaben")` erfasst statt die Buchung zu blockieren.
5. Gibt zusätzlich alle erzeugten `journal_ids` zurück, die der Bank-Import braucht, um die
   Transaktion als "gebucht" zu markieren.

**Manueller Weg:** `POST /mahnwesen/{mahnung_id}/zahlung` (`MahnungZahlungRequest` →
`MahnungZahlungResponse`) - dünner Wrapper um `verteile_mahnung_zahlung()`. Frontend: neuer Button
„💶 Zahlung erfassen" in der Mahnungen-Historie (`MahnwesenPage.tsx`), sichtbar nur bei versendeten,
nicht übertragenen Mahnungen mit mehr als einer verknüpften Rechnung (echte Konsolidierung, um
keine Redundanz zur bestehenden Einzel-Rechnungs-Zahlungserfassung zu schaffen); Inline-Formular
Betrag/Datum/Zahlungsart, Ergebnis-Anzeige zeigt die Aufteilung pro Rechnung + Gebühr-Verrechnung +
Kundenguthaben.

**Automatischer Weg (Bank-Import):** `_match_mahnung(db, tx)` (`api/bank_import.py`) sucht bei
eingehenden Transaktionen (`tx.betrag > 0`) im normalisierten Verwendungszweck/Buchungstext nach
der Mahnnummer (Format `MHN-YY####`) einer versendeten Mahnung - läuft in `auto_buchen()` **vor**
der normalen 1:1-Rechnungs-Zuordnung, da eine Mahnung mehrere Rechnungen gleichzeitig abdecken
kann. Bei Treffer: `verteile_mahnung_zahlung()` übernimmt komplett, die erste erzeugte
`journal_id` wird auf `tx.journal_id` gesetzt (markiert die Transaktion als gebucht, analog zum
bestehenden „Gebucht"-Badge-Mechanismus).

Live getestet (zwei vollständig synthetische Test-Kunden inkl. Rechnungen/Mahnung/Konto/Import/
Transaktion, danach lückenlos bereinigt):
- Manueller Weg: konsolidierte Mahnung über 2 Rechnungen (60+90 €, älteste zuerst), erste Zahlung
  150 € → ältere Rechnung voll, jüngere teilweise (`zahlungsstatus=teilweise`); zweite Zahlung
  200 € → jüngere Rechnung voll, 50 € Überschuss korrekt 40 € Mahngebühr + 10 € Kundenguthaben-
  Forderung.
- Bank-Import: Mahnnummer im Verwendungszweck einer echten Transaktion, `auto_buchen()` erkennt sie
  vor der normalen Rechnungs-Zuordnung, verteilt automatisch auf beide Rechnungen + Gebühr +
  Kundenguthaben, markiert die Transaktion korrekt als gebucht.
- Cleanup mit GoBD-Trigger-Falle: `protect_journal_update`/`_delete` blockieren auch das Umsetzen
  von `immutable=1` auf `0` (Trigger prüft `OLD.immutable`, nicht den Zielwert) - Testbuchungen
  konnten nur nach **temporärem `DROP TRIGGER`**, Löschen, dann `_setup_gobd_triggers()` zum
  Wiederherstellen entfernt werden (identisches Muster wie `_migrate_signaturen()` es in `main.py`
  bereits nutzt). Bei einem ersten Cleanup-Versuch blieben die Trigger durch einen Zwischenfehler
  kurzzeitig entfernt - sofort bemerkt, mit einem `try/finally`-geschützten Skript behoben und per
  Update-Selbsttest auf einem echten `immutable=1`-Datensatz verifiziert, dass der Schutz wieder
  aktiv ist.

---

## Abschnitt F – Automatisierung (opt-in) ✅ (2026-08-02)

**Status: ✅ implementiert.** `automatik_lauf()` (`api/mahnwesen.py`) wird beim App-Start aus
`main.py` aufgerufen - exakt analog zum bestehenden Muster für wiederkehrende Rechnungen
(`api.wiederkehrend.pruefen_intern()`, selbe Stelle in `startup()`, selbes try/except-Schema:
blockiert den Start nie, ein Fehler bei einem Kunden bricht die anderen nicht ab).

**Ablauf pro Lauf:**
1. Bei `aktiv=false` oder `automation_modus="manuell"` (Default seit Abschnitt A war real aber
   bereits `"halb"` im Model-Default - siehe Warnhinweis unten): sofortiger No-Op.
2. Nutzt `kunden_uebersicht()` als Datenbasis (identische Logik wie die Übersichtsseite) -
   dadurch automatisch konsistent mit allem, was in diesem Dokument zu Konsolidierung,
   Mahnsperre, Kundensperrung, Vorperioden-Übernahme und dem rechnungslosen Gebühren-Mahnflow
   steht, ohne das getrennt nachzubauen.
3. Zahlungserinnerung (Stufe 1, 1:1 pro Rechnung): für jede `rm.zahlungserinnerung_faellig`
   Rechnung ein `erstellen()`-Aufruf.
4. Echte Mahnstufen (`kunde.aktionsfaellig`): ein `erstellen()`-Aufruf pro Kunde - mit
   `kunde_id` (rechnungslos) bei `nur_offene_gebuehr`, sonst mit der ersten offenen Rechnung
   des Kunden (identisch zum Frontend-Verhalten in `MahnwesenPage.tsx`).
5. Bei `automation_modus="voll"` **und** `versand_mail` aktiv **und** SMTP konfiguriert **und**
   der Kunde eine E-Mail-Adresse hat: sofortiger Mail-Versand über das bestehende
   `api/mail.py::mail_senden()` (identischer Betreff/Text wie der manuelle
   `MahnungMailDialog.tsx`-Standardtext, Platzhalter serverseitig gespiegelt). Jeder andere Fall
   (kein SMTP, keine Mail, `automation_modus="halb"`) lässt den Entwurf einfach liegen - keine
   Fehlermeldung, kein Blockieren.

**⚠️ Wichtiger Warnhinweis (live entdeckt beim Einbau):** `MahnwesenEinstellungen.automation_modus`
hat in `models.py` den Default `"halb"` (nicht `"manuell"`) - jede Installation, die diese
Einstellung nie explizit angefasst hat, läuft also ab sofort automatisch im Halbautomatik-Modus.
Beim Speichern dieser Änderung hat der laufende Dev-Server (uvicorn `--reload`) den Startup-Hook
sofort real ausgeführt und dabei einen echten Zahlungserinnerungs-Entwurf für eine tatsächlich
überfällige Testrechnung erzeugt (kein Mail-Versand, da SMTP in der Dev-Umgebung nicht
konfiguriert war) - sofort bemerkt und bereinigt. In einer Installation mit bereits konfiguriertem
SMTP und `automation_modus="voll"` (wie hier: `versand_mail=true` war zum Zeitpunkt des Einbaus
bereits gesetzt) hätte das bedeutet, dass **beim nächsten App-Start automatisch echte Mahn-Mails an
echte Kunden verschickt worden wären**, ohne vorherige Bestätigung. Vor dem produktiven Einsatz
unbedingt `automation_modus` und `versand_mail` bewusst prüfen/setzen, nicht auf dem
Schema-Default belassen.

Live getestet (direkter Funktionsaufruf, nicht über Server-Neustart, um unkontrollierte
Seiteneffekte zu vermeiden): Zahlungserinnerung-Pfad live über den Server-Neustart-Zufallsfund
bestätigt (siehe Warnhinweis), höhere Mahnstufe (Stufe 1 → 2, inkl. 40 € Mahngebühr) gezielt mit
zurückdatiertem `versendet_am` einer echten Mahnung nachgestellt (danach exakt wiederhergestellt,
keine dauerhafte Datenänderung) - `automatik_lauf()` legt korrekt einen Stufe-2-Entwurf mit Gebühr
an, `versendet: False` da kein SMTP konfiguriert. Alle Testdaten vollständig bereinigt.

### Nachbesserung (2026-08-02, Nutzer-Feedback nach dem Warnhinweis-Fund)

Zwei Korrekturen, direkt durch den oben dokumentierten Vorfall veranlasst:

1. **„voll" kann nur aktiviert werden, wenn SMTP eingerichtet ist.** `einstellungen_put()`
   (`api/mahnwesen.py`) prüft jetzt bei `automation_modus="voll"` explizit
   `Unternehmen.smtp_aktiv` und lehnt mit 422 „Vollautomatik kann erst aktiviert werden, wenn der
   Mail-Versand (SMTP) in den Unternehmenseinstellungen eingerichtet ist." ab, falls SMTP nicht
   aktiv ist. Die Laufzeit-Prüfung in `automatik_lauf()` (`kann_mailen`) bleibt zusätzlich
   bestehen als Absicherung für den Fall, dass SMTP nach dem Aktivieren wieder deaktiviert wird
   (dann läuft die Automatik weiter, versendet aber nichts - kein Fehler).
2. **Bestehende, noch nicht versendete Entwürfe werden bei „voll" nachträglich mitversendet.**
   Nutzer-Vorgabe: "Bestehende Entwürfe sind noch nicht versendet... Bei Umstellung auf 'voll'
   sollen diese jedoch versendet werden. Es darf nur nichts noch mal versendet werden was bereits
   gesendet ist." `automatik_lauf()` wurde umgebaut: Phase 1 legt wie zuvor fällige Entwürfe an
   (unabhängig vom Modus, bei `halb` UND `voll`). Phase 2 (nur bei `voll`) fragt **alle**
   `Mahnung`-Zeilen mit `status == "entwurf"` live aus der DB ab - nicht nur die in diesem Lauf
   neu erzeugten - und versendet jede davon. Das erfasst automatisch auch Entwürfe, die während
   einer früheren `manuell`/`halb`-Phase liegen geblieben sind. Da die Auswahl über
   `status == "entwurf"` läuft (nicht über eine In-Memory-Liste), ist strukturell ausgeschlossen,
   dass eine bereits `versendete` Mahnung dabei erneut angefasst wird.

Live getestet (isolierter Funktionsaufruf mit gemocktem `mail_senden`, um echten SMTP-Versuch zu
vermeiden): `PUT /einstellungen {"automation_modus": "voll"}` ohne SMTP → 422 wie erwartet.
Zwei Test-Mahnungen angelegt - eine bereits `versendet` (vor 10 Tagen), eine bestehender `entwurf`
(nie versendet) - dann `automation_modus="voll"` + SMTP simuliert gesetzt und `automatik_lauf()`
direkt aufgerufen: die bereits versendete Mahnung blieb exakt unverändert (`versendet_am`
identisch, nicht in der Versand-Liste), der bestehende Entwurf wurde korrekt erfasst und auf
`versendet` gesetzt. Alle Testdaten und Einstellungen exakt auf den Ausgangszustand
zurückgesetzt.

Ursprüngliche Spezifikation der drei Modi (unverändert umgesetzt):

- **`manuell`** (heutiges Verhalten): nichts automatisch. Nutzerin geht pro Kunde durch
  `/mahnwesen`, legt Entwürfe manuell an (Button „als Entwurf anlegen") und verschickt sie manuell
  (👁 Ansehen / 🖨️ Drucken / ✉️ Mail in der Mahnungen-Historie).
- **`halb`**: Startup-Hook in `main.py` (nach Migrations-Lauf, analog `voll`) prüft beim App-Start
  automatisch alle Kunden (dieselbe Logik wie `kunden_uebersicht()`: `aktionsfaellig` +
  `zahlungserinnerung_faellig`) und legt für jeden fälligen Fall automatisch einen **Entwurf** an
  (ruft intern `erstellen()` auf - Konsolidierung, Mahngebühr/Verzugszinsen-Berechnung und die
  Mahnsperre-422-Prüfung gelten dabei unverändert). **Kein automatischer Versand** - die Nutzerin
  sieht die neuen Entwürfe in der Mahnungen-Historie und entscheidet weiterhin selbst, wann/ob sie
  tatsächlich rausgehen (Qualitätskontrolle vor Versand: Text prüfen, ggf. doch anrufen statt
  mahnen). Löst das eigentliche Problem von `manuell`: nicht mehr täglich durch jeden Kunden
  klicken müssen, nur um zu sehen wer fällig ist.
- **`voll`**: wie `halb`, zusätzlich wird der neu angelegte Entwurf im selben Durchlauf automatisch
  per Mail versendet (nur wenn `versand_mail` aktiv **und** der Kunde eine E-Mail-Adresse hat -
  sonst bleibt er als Entwurf liegen, kein Blockieren des ganzen Laufs). Protokollierung über
  `mahnungen.status`/`versendet_am` wie beim manuellen Versand. Kein externer Cron nötig.

Kundensperrung (`mahnung_gesperrt`) blockiert bewusst **nicht** das Anlegen neuer Mahnungen selbst
(sonst könnte ein gesperrter Kunde nie weitergemahnt werden) - sie blockiert nur neue
Angebote/Aufträge/Rechnungen (siehe Abschnitt E).

---

## Vollständige Datei-Liste

| Datei | Änderung |
|-------|----------|
| `src/backend/main.py` | ✅ Migration 131-135, SCHEMA_VERSION=135; `startup()` ruft `automatik_lauf()` (Abschnitt F) |
| `src/backend/database/models.py` | ✅ 4 neue Modelle (`MahnwesenEinstellungen`, `Mahnstufe`, `Mahnung`, `MahnungRechnung`), 2 neue Felder (`Kunde.mahnung_gesperrt`, `Rechnung.mahnstufe_aktuell`) |
| `src/backend/api/schemas.py` | ✅ Pydantic-Schemas Mahnung/Mahnstufe/Einstellungen + `mahnung_gesperrt` in `KundeResponse` |
| `src/backend/database/seed.py` | ✅ Nummernkreis mahnung, Kategorien Mahngebühren + Verzugszinsen (Einnahme), 4 Mahnstufen |
| `src/backend/api/mahnwesen.py` | ✅ NEU – alle Endpunkte (Einstellungen, Mahnstufen-CRUD, faellig, vorschau, erstellen, PDF) |
| `src/backend/api/rechnungen.py` | ✅ `zahlung_bar_erstellen`: Überschuss ab Restbetrag=0 verrechnet gegen offene Mahngebühr/Zinsen (kundenweit), Rest als Kundenguthaben; Zinseinfrierung bei Vollzahlung |
| `src/backend/api/bank_import.py` | ✅ `_buche_pfad_a()`: Überschuss erst gegen offene Mahngebühr/Verzugszinsen verrechnet, Rest als Kundenguthaben |
| `src/backend/utils/mahngebuehr_verrechnung.py` | ✅ NEU – kundenweite Verrechnungslogik (Abschnitt E) |
| `src/backend/utils/pdf_inkasso_deckblatt.py` | ✅ NEU – Inkasso-Paket-Deckblatt |
| `src/backend/utils/pdf_mahnung.py` | ✅ NEU – PDF-Generator (nicht `pdf/mahnung.py` – Projekt-Konvention) |
| `src/frontend/src/api/client.ts` | ✅ Neue Typen + API-Calls |
| `src/frontend/src/pages/einstellungen/MahnwesenPage.tsx` | ✅ NEU |
| `src/frontend/src/pages/mahnwesen/MahnwesenPage.tsx` | ✅ NEU |
| `src/frontend/src/pages/dashboard/Dashboard.tsx` | ✅ Widget `mahnwesen_faellig` |
| `src/frontend/src/pages/rechnungen/RechnungenPage.tsx` | ✅ Abschnitt „Mahnungen" (`RechnungMahnungenSection`) |
| `src/frontend/src/pages/kunden/KundenPage.tsx` | ✅ Sperr-/Warn-Badges (getrennt), Mahnstatus mit Gebühr-offen-Hinweis, Entsperren-Button |
| `src/frontend/src/components/AppLayout.tsx` | ✅ Navigation (Fakturierung + Einstellungen) |
| `src/frontend/src/App.tsx` | ✅ Routen `/mahnwesen`, `/mahnwesen-einstellungen` |
| `src/frontend/src/data/changelog.ts` | ⬜ noch nicht befüllt – erfolgt vor Release v0.5.0 |
| `CLAUDE.md` | SCHEMA_VERSION + Migrations-Tabelle |

---

## Implementierungsreihenfolge

| # | Abschnitt | Inhalt | Status |
|---|-----------|--------|--------|
| 1 | A | Migration 131 + Models + Seeds + API-Grundgerüst (Einstellungen + Mahnstufen CRUD) | ✅ |
| 2 | B | Fälligkeits-Prüfung, Vorschau, Mahnung anlegen (Entwurf), `faellig`-Endpunkt | ✅ |
| 3 | C | PDF-Generator (`utils/pdf_mahnung.py`) | ✅ |
| 4 | D | Frontend: Einstellungsseite, Übersicht-Page, Dashboard-Widget, Rechnungen-/Kunden-Detail, Navigation | ✅ |
| 5 | E | Kundensperrung-Logik + Inkasso-Paket-ZIP + Mahngebühr-bei-Zahlung-Buchung + Bank-Import-Fix + Zinseinfrierung + kundenweiter Mahnflow ohne Rechnung | ✅ |
| 5b | E | Zahlungsverteilung bei konsolidierten Mahnungen (manuell + Bank-Import) | ✅ |
| 5c | E | Konfigurierbare Dokumentanhänge pro Mahnstufe (Nutzer-Feedback Punkt 12) | ✅ |
| 6 | F | Vollautomatik Startup-Hook | ✅ |
| 7 | A | Mahnstufen-Editor UX-Fixes (Löschschutz, Speicher-Feedback, Einfügereihenfolge, Gebühr-Verbot 1. Stufe) | ✅ |

---

## Verifikation (nach Implementierung)

1. Einstellungen → Mahnwesen: 4 Standard-Stufen sichtbar, editierbar
2. Überfällige Rechnung anlegen → erscheint in `/mahnwesen`-Übersicht
3. Mahnung erstellen → PDF öffnet inline mit korrekten Beträgen und Giro-Code
4. Mahnung per Mail versenden → Eingang prüfen, Mahnhistorie im Rechnungs-Detail sichtbar
5. Rechnung bezahlen → Mahngebühr-Journaleintrag erscheint automatisch
6. Stufe 4 versendet → Inkasso-ZIP enthält alle PDFs korrekt strukturiert
7. Vollautomatik: App-Neustart mit fälligen Mahnungen → werden versendet
