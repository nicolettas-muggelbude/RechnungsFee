# CLAUDE.md – RechnungsFee

GoBD-konformes Kassenbuch für Kleinunternehmer, Freiberufler und Vereine.
**Tech-Stack:** Tauri 2 + React 19 + FastAPI + SQLite

---

## Projektstruktur

```
RechnungsFee/
├── src/
│   ├── backend/                    FastAPI-App
│   │   ├── main.py                 App-Start, Startup-Event (DB-Init + Seeds)
│   │   ├── database/
│   │   │   ├── models.py           SQLAlchemy 2.0 – 16 Tabellen (GoBD-konform)
│   │   │   ├── connection.py       Engine, WAL-Mode, foreign_keys=ON
│   │   │   └── seed.py             31 Kategorien + 27 EU-Länder
│   │   └── api/
│   │       ├── schemas.py          Pydantic-Schemas (alle Request/Response-Typen)
│   │       ├── setup.py            /api/setup/status + /kassenbestand
│   │       ├── kassenbuch.py       /api/kassenbuch (inkl. /split, Storno, Statistik)
│   │       ├── tagesabschluss.py   /api/tagesabschluss + /vorschau
│   │       ├── kunden.py           /api/kunden (CRUD)
│   │       ├── lieferanten.py      /api/lieferanten (CRUD)
│   │       ├── konten.py           /api/konten (CRUD)
│   │       ├── kategorien.py       /api/kategorien (read-only)
│   │       ├── unternehmen.py      /api/unternehmen (GET + POST + PUT)
│   │       └── nummernkreise.py    /api/nummernkreise (Belegnr-Konfiguration)
│   └── frontend/
│       └── src/
│           ├── api/client.ts       Typisierter API-Client (alle Endpunkte)
│           ├── App.tsx             Routing + Setup-Guard
│           ├── components/
│           │   └── AppLayout.tsx   Sidebar-Navigation (ausklappbare Stammdaten-Gruppe)
│           └── pages/
│               ├── setup/          SetupWizard (4 Steps: Daten, Steuern, Konto, Kassenbestand)
│               ├── dashboard/      Dashboard mit Zeitfilter (Monat/Tag/Zeitraum)
│               ├── kassenbuch/     KassenbuchPage, BuchungForm, BuchungDetail, TagesabschlussDialog
│               ├── kunden/         KundenPage
│               ├── lieferanten/    LieferantenPage
│               ├── stammdaten/     UnternehmenPage, KontenPage, KategorienPage
│               └── einstellungen/  NummernkreisePage
├── docs/
│   ├── ROADMAP.md
│   └── 02-kassenbuch.md            Fachliche Spezifikation Kassenbuch
└── src-tauri/                      Tauri-Desktop-Wrapper
```

---

## Entwicklungsumgebung starten

```bash
# Backend (Port 8001)
cd src/backend && .venv/bin/uvicorn main:app --port 8001 --reload

# Frontend (Vite-Proxy /api → localhost:8001)
cd src/frontend && npm run dev

# Build prüfen
cd src/frontend && npm run build
```

---

## Backend-Konventionen

- **GoBD:** Kein PUT/DELETE auf Kassenbucheintrag oder Tagesabschluss — nur Storno als Gegenbuchung
- **Belegnr-Format:** `KB-YYYYMMDD-NNN` (über `_naechste_belegnr(db, datum)` generiert)
- **USt-Berechnung:** `netto = brutto * 100 / (100 + ust_satz)`, ROUND_HALF_UP
- **Kleinunternehmer:** Automatisch `ust_satz=0` + `steuerbefreiung_grund="§19 UStG"`
- **SQLAlchemy 2.0 Gotcha:** `.update({"string_key": value})` — String-Keys, keine Column-Objekte
- **Immutable-Flag:** Kassenanfangsbestand + Tagesabschlüsse sind `immutable=True`
- **Split-Route muss VOR `/{id}` registriert sein** (sonst FastAPI-Path-Param-Konflikt)

## Frontend-Konventionen

- **Zod v4 + @hookform/resolvers v5:** Kein `.default()` in Schemas — Defaults in `useForm({ defaultValues: ... })`
- **Zwei useForm-Hooks:** Immer beide initialisieren (React Rules of Hooks), nicht conditional
- **UI-Sprache:** Du-Ansprache
- **Geldbeträge:** Strings (`"119.00"`) — keine JS-floats, Backend gibt NUMERIC(12,2) zurück
- **FilterModus:** `'monat' | 'datum' | 'zeitraum'` — gleiche Segmented-Control in Dashboard + KassenbuchPage

---

## Implementierter Stand

### v0.1 – Kassenbuch (Released Februar 2026)

**Backend**
- [x] Setup-API: `/status` + `/kassenbestand` (Anfangsbestand als immutable Eintrag)
- [x] Kassenbuch-API: GET/POST + `/split` (atomare Mehrfach-Buchung) + Storno (Gegenbuchung)
- [x] Statistik-Endpunkt: `/kassenbuch/statistik/monat`
- [x] Tagesabschluss: Vorschau + unveränderlicher Abschluss (GoBD)
- [x] Kunden/Lieferanten CRUD
- [x] Nummernkreise: konfigurierbare Belegnr-Präfixe
- [x] USt-Berechnung aus Brutto (ROUND_HALF_UP), Kleinunternehmer §19 automatisch

**Frontend**
- [x] Setup-Wizard (4 Steps: Unternehmen, Steuern, Bankkonto, Kassenbestand)
- [x] AppLayout mit Sidebar (ausklappbare Stammdaten-Gruppe)
- [x] Dashboard: 3 Kacheln (Einnahmen/Ausgaben/Saldo) + letzte 5 Buchungen + Zeitfilter (Monat/Tag/Zeitraum)
- [x] KassenbuchPage: Filter (Monat/Tag/Zeitraum + Art + Kategorie), Tabelle, klickbare Detail-Zeile
- [x] BuchungForm: Einzel- und Split-Buchung in einem Modal, Brutto/Netto-Umschalter (nicht für Kleinunternehmer), Live-USt-Vorschau, Vorsteuerabzug auto nach Kategorie
- [x] BuchungDetail: Inline-Panel mit Storno, Drucken, Kundendaten
- [x] TagesabschlussDialog: Vorschau + Ist-Bestand-Eingabe + Differenz
- [x] Kunden-/Lieferanten-/Konten-/Kategorien-/Stammdaten-/Nummernkreise-Seiten

---

## Nächste Meilensteine (siehe ROADMAP.md)

| Version | Ziel | Inhalt |
|---------|------|--------|
| v0.2 | Juni 2026 | Bank-CSV-Import (Postbank, Sparkasse, …), Auto-Filter-Regeln, Duplikat-Erkennung |
| v0.3 | August 2026 | EÜR, UStVA-Voranmeldung, DATEV-Export, Jahresübersicht, PDF-Export |
| v1.0 | Oktober 2026 | Tauri-Build (.msi/.deb/.dmg), Backup, Einstellungen, Hilfe-System |
| v1.1 | Dezember 2026 | Rechnungseingangsbuch + Rechnungsausgangsbuch (ZUGFeRD/XRechnung/PDF+OCR), Kassenbuch-Vorschlag, Verknüpfung |

---

## Offene Punkte / Tech-Debt

- **Hilfe-Tooltips:** Vorsteuerabzug-Erklärung im BuchungForm (geplant für späteres Milestone)
- **Tauri-Build:** Noch nicht konfiguriert, erst für v1.0
- **DSGVO-Export:** Erst für v1.0
