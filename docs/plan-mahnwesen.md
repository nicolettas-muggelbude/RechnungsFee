# Plan: Mahnwesen / Forderungsmanagement

**Stand:** 2026-07-09  
**Status:** Planung abgeschlossen – Implementierung ausstehend

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
| Mahnungs-PDF | Eigenes schlichtes Layout + Giro-Code QR |
| Automation | Halbautomatik als Standard, Vollautomatik als opt-in |
| Inkasso-Paket | ZIP mit strukturierten PDF-Unterordnern |
| Kundensperrung | Warnung bis harte Sperrung, ab konfigurierbarer Mahnstufe |

---

## Abschnitt A – Datenbankschema (Migration 116)

**Status: ⬜ ausstehend**

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

### Neue Kategorie (seed.py + _migrate_kategorien)
```python
{"name": "Mahngebühren", "kontenart": "Erlös", "konto_skr03": "8910", "konto_skr04": "4910", "euer_zeile": 15}
```

> ⚠️ Hinweis: SKR03 8910 / SKR04 4910 sind bereits von „Zuwendungen von Dritten" belegt (Migration 101).
> Prüfen ob eigenes Konto besser ist (SKR03 8390 „Sonstige betriebliche Erträge" / SKR04 4830).

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

**Status: ⬜ ausstehend**

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
- Keine Mahnung vorhanden → fällig wenn `faellig_am + tage_nach_faelligkeit(Stufe1) ≤ heute`
- Letzte Mahnung vorhanden → fällig wenn `versendet_am + tage_nach_vorheriger(nächste Stufe) ≤ heute`
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

**Status: ⬜ ausstehend**

Datei: `src/backend/pdf/mahnung.py`

Eigenes Layout (briefartig, analog `rechnung.py`):
- Absenderblock (links oben) + Empfängerblock (Adressfenster)
- Betreff: `{bezeichnung} – {rechnungsnummer}` / konsolidiert: `{bezeichnung} – Offene Forderungen`
- Mahntext (Vorlage mit aufgelösten Platzhaltern)
- Tabelle: Rechnung(en) | Rechnungsdatum | Fällig am | Offener Betrag
- Summenblock: Offener Betrag + Mahngebühr + Verzugszinsen = **Gesamtforderung**
- Bankdaten + **Giro-Code QR** (Betrag = Gesamtforderung)
- `Content-Disposition: inline`

---

## Abschnitt D – Frontend

**Status: ⬜ ausstehend**

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
- Kundensperrung: Toggle + ab Stufe + Modus (warnung/sperrung)
- Verzugszinsen: Toggle + ab Stufe + Basiszinssatz (Info-Link bundesbank.de) + Aufschläge Privat/Gewerblich
- Mahnstufen-Editor: sortierbare Liste, jede Stufe editierbar (Bezeichnung, Tage, Gebühren, Betreff/Text mit Platzhalter-Chips)

### Übersichtsseite `/mahnwesen`
- **Links (Liste):** Rechnungen mit fälliger Mahnung  
  Spalten: Kunde | Rechnungsnr. | Fällig seit | Aktuelle Stufe | Empfohlene Stufe
- **Filter:** nach Stufe / Dringlichkeit
- **Halbautomatik:** Checkboxen + „Ausgewählte mahnen"-Button
- **Rechts (Detail):** Mahnhistorie + Vorschau (Gebühren/Zinsen) + Aktionen

### Weitere UI-Änderungen

| Bereich | Änderung |
|---------|---------|
| Dashboard | Widget „X Mahnungen fällig" → Klick `/mahnwesen` |
| Rechnungen Detail-Panel | Tab „Mahnungen" mit Mahnhistorie + Button „Mahnung erstellen" |
| Kunden Detail-Panel | Sperr-Status-Badge + Toggle im Kontokorrent-Tab |
| Navigation (`AppLayout.tsx`) | Sidebar-Eintrag „Mahnwesen" (sichtbar wenn `aktiv=true`) |
| Einstellungsmenü | Neuer Punkt „Mahnwesen" |
| `src/frontend/src/App.tsx` | Route `/mahnwesen` |

---

## Abschnitt E – Kundensperrung + Inkasso-Paket + Mahngebühr-Buchung

**Status: ⬜ ausstehend**

- **Kundensperrung:** Bei Mahnung-Versand prüfen ob `mahnstufe ≥ kundensperrung_ab_stufe` → `kunden.mahnung_gesperrt = true` (Modus `sperrung`) oder Warnung im Frontend (Modus `warnung`)
- **Inkasso-Paket:** ZIP-Download mit Deckblatt, Kontokorrent, Rechnungs-PDFs, Mahnungs-PDFs
- **Mahngebühr-Buchung:** In `api/rechnungen.py` beim Zahlung-PATCH automatisch Journal-Eintrag

---

## Abschnitt F – Vollautomatik (opt-in)

**Status: ⬜ ausstehend**

Startup-Hook in `main.py` (nach Migrations-Lauf):  
Wenn `automation_modus = 'voll'` und `aktiv = true` → alle fälligen Mahnungen berechnen und per Mail versenden. Protokollierung in `mahnungen`. Kein externer Cron nötig.

---

## Vollständige Datei-Liste

| Datei | Änderung |
|-------|----------|
| `src/backend/main.py` | Migration 116, SCHEMA_VERSION=116, Startup-Hook Vollautomatik |
| `src/backend/database/models.py` | 4 neue Modelle, 2 neue Felder |
| `src/backend/api/schemas.py` | Pydantic-Schemas Mahnung/Mahnstufe/Einstellungen |
| `src/backend/database/seed.py` | Nummernkreis mahnung, Kategorie Mahngebühren, 4 Mahnstufen |
| `src/backend/api/mahnwesen.py` | NEU – alle Endpunkte |
| `src/backend/api/rechnungen.py` | Zahlung-PATCH: Mahngebühr-Buchung |
| `src/backend/pdf/mahnung.py` | NEU – PDF-Generator |
| `src/frontend/src/api/client.ts` | Neue Typen + API-Calls |
| `src/frontend/src/pages/einstellungen/MahnwesenPage.tsx` | NEU |
| `src/frontend/src/pages/mahnwesen/MahnwesenPage.tsx` | NEU |
| `src/frontend/src/pages/dashboard/Dashboard.tsx` | Widget |
| `src/frontend/src/pages/rechnungen/RechnungenPage.tsx` | Tab Mahnungen |
| `src/frontend/src/pages/kunden/KundenPage.tsx` | Sperr-Status |
| `src/frontend/src/components/AppLayout.tsx` | Navigation |
| `src/frontend/src/App.tsx` | Route /mahnwesen |
| `src/frontend/src/data/changelog.ts` | v0.4.7 |
| `CLAUDE.md` | SCHEMA_VERSION + Migrations-Tabelle |

---

## Implementierungsreihenfolge

| # | Abschnitt | Inhalt | Status |
|---|-----------|--------|--------|
| 1 | A | Migration 116 + Models + Seeds + API-Grundgerüst (Einstellungen + Mahnstufen CRUD) | ⬜ |
| 2 | B | Einstellungsseite Frontend | ⬜ |
| 3 | C | Übersicht-Page + PDF-Generator + Versand + Dashboard-Widget + Rechnungen-Tab | ⬜ |
| 4 | D | Kundensperrung + Inkasso-Paket + Mahngebühr-bei-Zahlung + `faellig`-Endpunkt | ⬜ |
| 5 | E | Vollautomatik Startup-Hook | ⬜ |

---

## Verifikation (nach Implementierung)

1. Einstellungen → Mahnwesen: 4 Standard-Stufen sichtbar, editierbar
2. Überfällige Rechnung anlegen → erscheint in `/mahnwesen`-Übersicht
3. Mahnung erstellen → PDF öffnet inline mit korrekten Beträgen und Giro-Code
4. Mahnung per Mail versenden → Eingang prüfen, Mahnhistorie im Rechnungs-Detail sichtbar
5. Rechnung bezahlen → Mahngebühr-Journaleintrag erscheint automatisch
6. Stufe 4 versendet → Inkasso-ZIP enthält alle PDFs korrekt strukturiert
7. Vollautomatik: App-Neustart mit fälligen Mahnungen → werden versendet
