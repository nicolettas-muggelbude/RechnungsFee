# 13 – Implementierungsstand & Entwicklungsnotizen

Laufend aktualisiertes Protokoll umgesetzter Features und technischer Entscheidungen.

---

## Tech Stack (umgesetzt)

| Schicht | Technologie |
|---|---|
| Frontend | React 19 + Vite + TypeScript, Tailwind CSS v4, React Query, React Hook Form + Zod, React Router DOM |
| Backend | FastAPI + SQLAlchemy 2.0 + Python 3.12 + SQLite (WAL mode) |
| Desktop | Tauri 2.10.0 (`de.rechnungsfee.app`) |
| PDF | fpdf2 + Pillow (Aspect Ratio für Logos) |
| DB-Pfad | `~/.local/share/RechnungsFee/rechnungsfee.db` |
| Backend-Port | 8001 |

---

## Umgesetzte Features

### Backend
- DB-Schema (16+ Tabellen, GoBD-konform, NUMERIC(12,2))
- Setup-API: `/status` + `/kassenbestand`
- Unternehmen, Konten, Kategorien CRUD
- Kassenbuch: GET/POST + `/split` (atomar) + Storno – kein PUT/DELETE
- Tagesabschluss: Vorschau + unveränderlicher Abschluss (mit PDF)
- Kunden/Lieferanten CRUD + DSGVO (Art. 15 Export, Art. 17 Anonymisieren, DELETE 409)
- Nummernkreise: KB/RE/KD/LI – auto-Vergabe
- USt-Berechnung aus Brutto (ROUND_HALF_UP), §19 automatisch
- GoBD-Export: `GET /api/export/gobd?jahr=YYYY` → ZIP (8 Dateien)
- Rechnungen CRUD + Zahlungen (Bar/Karte/PayPal/Bank) + Storno + Kassenbuch-Gegenbuchungen
- Rechnungs-PDF: `GET /api/rechnungen/{id}/pdf` (DIN 5008, Logo, KOPIE-Flag)
- Logo-Upload: `POST/GET/DELETE /api/unternehmen/logo` → `~/.local/share/RechnungsFee/uploads/`
- Unternehmen: `handelsregister_nr`, `handelsregister_gericht`, `logo_pfad`, `mail_betreff_vorlage`, `mail_text_vorlage`, `mail_signatur`

### Frontend
- Setup-Wizard (4 Steps + Kassenbestand), Auto-Redirect zu /setup
- AppLayout + Sidebar mit ausklappbarer Stammdaten-Gruppe
- Dashboard: 3 Kacheln + letzte 5 Buchungen + Zeitfilter
- KassenbuchPage: Filter, BuchungForm (Einzel + Split, Brutto/Netto-Umschalter)
- TagesabschlussDialog + TagesabschlussPage (PDF-Export, Differenz-Statistik)
- KundenPage + LieferantenPage: DSGVO-Bereich, Löschen-Fehler → amber Banner
- NummernkreisePage, ExportPage
- UnternehmenPage: Firmendaten + Logo-Upload + Mail-Vorlage + Signatur (Live-Vorschau)
- RechnungenPage: Tabs Eingang/Ausgang, Zahlungs-Dialog, KOPIE-Markierung
  - Entwürfe können nicht kassiert werden
  - Mail: Template-Ersetzung (`{rechnungsnummer}`, `{datum}`, `{betrag}`, `{faellig_am}`, `{kunde}`, `{firmenname}`) + Signatur, E-Mail aus Kundenstamm
- BuchungDetail: Mail-Signatur aus Unternehmen

---

## PDF-Rechnung Layout (DIN 5008 Form B)

```
┌──────────────────────────────────────────────────────────┐
│ Logo (links)     │ Firmenname                             │ 10–43mm
│                  │ Adresse, Tel, E-Mail, Web              │
│                  │ (bündig mit Rechnungsnummer-Spalte)    │
├──────────────────────────────────────────────────────────┤ 43mm
│ Absender-Kurzz.  │ Rechnungsnummer  RE-2026-001           │ 45mm
│ Empfänger        │ Rechnungsdatum   01.03.2026            │
│ (DIN-Adressfld.) │ Fällig am        15.03.2026            │
├──────────────────────────────────────────────────────────┤
│ Rechnung RE-XXXX                                         │
│ Positionstabelle                                         │
│ Summen + Zahlungshinweis                                 │
├──────────────────────────────────────────────────────────┤
│ Spalte 1          │ Spalte 2          │ Spalte 3          │ Footer
│ Name + Adresse    │ Inh./GF:/GS:      │ Bank              │
│ Tel/E-Mail/Web    │ USt-ID od. StNr   │ IBAN / BIC        │
│                   │ HRB               │ Seite · Datum     │
└──────────────────────────────────────────────────────────┘
```

- Adressfeld fest bei `Y=45mm` (Fensterumschlag-kompatibel)
- `BLOCK_X = L_MARGIN + 95 = 115mm` – bündig mit Rechnungsnummer-Spalte

### Rechtsform → Personenbezeichnung (`_person_bezeichnung()`)

| Rechtsform | Bezeichnung |
|---|---|
| Einzelunternehmer, Freiberufler | `Inh.:` |
| GmbH, UG, AG, SE, eG, KGaA | `GF:` (Geschäftsführer) |
| GbR, OHG, KG, PartG | `GS:` (Gesellschafter) |

---

## Technische Gotchas

### SQLAlchemy 2.0
```python
# Richtig – String-Keys:
db.query(Konto).update({"ist_standard": False})
# Falsch – führt zu Fehler:
db.query(Konto).update({Konto.ist_standard: False})
```

### Zod v4 + @hookform/resolvers v5
Kein `.default()` in Zod-Schemas → Typ-Konflikt mit `zodResolver`.
Defaults in `useForm({ defaultValues: ... })`, Fallback im Submit-Handler mit `?? wert`.

### mailto-Anhang
`mailto:` unterstützt keine Datei-Anhänge. Workaround: PDF per Browser-Download + mailto öffnen + Hinweis-Banner.

### Kassenbuch-Router
`/split` muss VOR `/{id}` registriert sein (FastAPI matcht sonst `split` als ID).

### FastAPI 422 – Array-Detail
FastAPI gibt bei Validierungsfehlern `detail` als Array zurück: `[{loc, msg, type}]`.
In `client.ts` wird das Array zu einem lesbaren String zusammengeführt, Pydantic-v2-Präfix `"Value error, "` wird entfernt.

### Versionierung
Version kommt aus Git-Tag, **nie manuell** in `package.json` ändern.
`vite.config.ts` liest: `GITHUB_REF_NAME` (CI) → `git describe --tags` (lokal) → `dev-<hash>` (kein Tag).
Neues Release: `git tag v0.x.y && git push --tags`

---

## Changelog

### 2026-03-01
- Unternehmen: +`handelsregister_nr/gericht` (DB-Migration + Schema + Frontend)
- Logo-Upload-Endpunkte (`POST/GET/DELETE /api/unternehmen/logo`)
- UnternehmenPage: vollständige Seite (war Platzhalter)
- Mail-Vorlagen mit Platzhalter-Ersetzung in RechnungenPage + BuchungDetail
- `RechnungResponse`: +`kunde_email`, +`lieferant_email`
- Entwurfs-Rechnung: Zahlung gesperrt (Backend 409 + Frontend-Guard)
- PDF-Rechnung: DIN 5008 Komplett-Redesign
  - `unt_dict` von 9 auf 22 Felder erweitert
  - Adressfeld Y=45mm, 3-Spalten-Footer
  - Rechtsformabhängige Personenbezeichnung (`_person_bezeichnung()`)
  - Dezentes `– Kopie –` statt rotem KOPIE-Banner
  - Zahlungsbestätigung: „Rechnungsbetrag bereits dankend erhalten am TT.MM.JJJJ per Zahlungsart: €"
  - Offene Rechnung: IBAN-Überweisungsaufforderung (unverändert)
- Logo Option B in Sidebar (war Emoji), `src/frontend/public/logo.svg`
- `client.ts`: FastAPI-422-Array-Detail lesbar, Pydantic-v2-Präfix entfernt
- RechnungenPage: Frontend-Validierung vor Submit (Kunde + Positionsbeschreibung)
- Versionsnummer in Sidebar aus Git-Tag (`vite.config.ts` → `__APP_VERSION__`)
