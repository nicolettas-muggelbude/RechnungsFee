# Bank-Integration – Implementierungsplan

**Journal-Integration:** Option A (manuell) – User erstellt Journal-Buchung pro Transaktion über vorausgefülltes Formular. Kein bestehender Code wird verändert.

---

## Ist-Stand

| Komponente | Status |
|-----------|--------|
| `Konto` Model + Migration 22/29 + `api/konten.py` CRUD | ✅ vorhanden |
| `BankTemplate`, `BankImport`, `BankTransaktion`, `AutoFilterRegel` in `models.py` | ✅ vorhanden |
| Alle vier Tabellen in DB (via `create_all`, leer) | ✅ vorhanden |
| `api/bank_import.py`, `api/bank_templates.py` | ❌ fehlt |
| Frontend (Seiten, Typen) | ❌ fehlt |
| System-Templates (CSV-Mappings) | ❌ fehlt |
| CSV-Parser | ❌ fehlt |
| Chardet / Encoding-Erkennung | ❌ fehlt |

---

## Risiken

| Risiko | Maßnahme |
|--------|----------|
| `pandas` im Plan (nicht in requirements, ~30 MB) | Ersatz: stdlib `csv` + `charset-normalizer` |
| `kontotyp 'privat'` fehlt im Schema-Validator | Additiv ergänzen (keine Migration, keine Datenmigration) |
| `rechnung_id` FK ohne `ON DELETE SET NULL` | In `journal_id`-Migration (Phase 5) absichern |
| Journal-Integrität: Bank-Tx ≠ Journal-Buchung | Option A: manuell, kein Automatismus |

---

## Phase 1 – Fundament Backend

- [x] **1.1** `charset-normalizer` in `requirements.txt`
- [x] **1.2** `kontotyp` Validator in `schemas.py` um `privat` erweitern
- [x] **1.3** System-Templates als Python-Dicts in `seed.py` + `seed_bank_templates()`
  - Sparkasse MT940, Sparkasse CAMT, DKB, ING, Volksbank, Commerzbank, PayPal
- [x] **1.4** `api/bank_templates.py`
  - `GET /api/bank-templates`
  - `POST /api/bank-templates` (User-Templates)
  - `PUT /api/bank-templates/{id}`
  - `DELETE /api/bank-templates/{id}` (nur User-Templates)
- [x] **1.5** `utils/bank_csv_parser.py`
  - Encoding-Erkennung (charset-normalizer)
  - Delimiter-Erkennung (`;`, `,`, `\t`)
  - Template-Matching (Match-Score gegen Header)
  - Parser gibt `list[dict]` zurück (kein SQLAlchemy-Bezug)

---

## Phase 2 – Import-Backend

- [x] **2.1** `api/bank_import.py`
  - `POST /api/bank-import/vorschau` – CSV hochladen, parsen, zurückgeben (nichts speichern)
  - `POST /api/bank-import/importieren` – nach User-Bestätigung speichern
  - `GET /api/bank-import/{konto_id}` – Transaktionen eines Kontos
  - `PATCH /api/bank-import/transaktion/{id}` – Klassifizierung (Mischkonto)
  - `DELETE /api/bank-import/import/{import_id}` – Import-Batch rückgängig
- [x] **2.2** Duplikat-Erkennung
  - Neue Spalte `dedupe_hash` in `bank_transaktionen` (Migration `version < 104`)
  - `UNIQUE (konto_id, dedupe_hash)` WHERE dedupe_hash IS NOT NULL
  - Hash aus `datum + betrag + partner_iban + verwendungszweck`
- [x] **2.3** Router in `main.py` registrieren

---

## Phase 3 – Auto-Filter & Mischkonto-Logik

- [x] **3.1** `api/auto_filter.py`
  - CRUD für `auto_filter_regeln`
  - `POST /api/auto-filter/vorschlag` – Klassifizierungs-Vorschlag
- [x] **3.2** Vorschlag-Engine (Reihenfolge):
  1. Explizite Keywords (`privatentnahme`, `einlage`)
  2. User-Regeln (SQL LIKE auf partner/verwendungszweck, höchste Priorität zuerst)
  3. Historische Häufigkeit (>5 gleiche user-überschriebene Einträge für denselben Partner)
  4. Heuristiken (GmbH/AG/KG/OHG/e.V./Finanzamt/Krankenkasse → geschäftlich)

---

## Phase 4 – Frontend

- [ ] **4.1** TypeScript-Typen in `client.ts`
  - `BankTemplate`, `BankTransaktion`, `BankImport`
  - API-Funktionen: `getBankTemplates`, `vorschauImport`, `startImport`, `getBankTransaktionen`
- [ ] **4.2** Aktivierung: `unternehmen.bank_import_aktiv` (neues Feld, Migration `version < 105`)
  - Nav-Eintrag erscheint nur wenn aktiv (Pattern: GuV, Angebote etc.)
- [ ] **4.3** Import-Dialog (Stepper, 5 Schritte):
  1. Konto auswählen + CSV hochladen
  2. Erkanntes Template anzeigen / manuell wählen
  3. Vorschau-Tabelle (Datum, Betrag, Partner, Verwendungszweck)
     - Mischkonto: Toggle ✅ geschäftlich / ❌ privat / 💰 Privatentnahme
     - Geschäftskonto: direkt weiter
  4. Zusammenfassung (X importieren, Y ignorieren, Z Duplikate)
  5. Bestätigen → Import
- [ ] **4.4** Transaktionen-Liste `/bank-import`
  - Filter: Zeitraum, Konto, Status (gebucht/offen)
  - Button „Als Buchung übernehmen" → vorausgefülltes Journal-Formular (Option A)

---

## Phase 5 – Journal-Integration (Option A)

- [ ] **5.1** Migration `version < 106`
  - `ALTER TABLE bank_transaktionen ADD COLUMN journal_id INTEGER REFERENCES journal(id) ON DELETE SET NULL`
- [ ] **5.2** Endpoint `POST /api/bank-import/transaktion/{id}/buchen`
  - Erstellt Journal-Eintrag aus Transaktion (Betrag, Datum, Partner vorbelegt)
  - Setzt `bank_transaktionen.journal_id`
  - Guard: `journal_id IS NULL` (kein Doppelbuchen)
- [ ] **5.3** In Transaktionen-Liste: Status-Spalte zeigt „gebucht" wenn `journal_id IS NOT NULL`

---

## Abhängigkeiten

```
Phase 1 → Phase 2 → Phase 4
Phase 3 (unabhängig, kann parallel zu Phase 2)
Phase 5 (benötigt Phase 2 + Phase 4 fertig)
```

## Migrations-Nummern (geplant)

| Version | Inhalt |
|---------|--------|
| 104 | `bank_transaktionen.dedupe_hash` + UNIQUE Index |
| 105 | `unternehmen.bank_import_aktiv BOOLEAN DEFAULT 0` |
| 106 | `bank_transaktionen.journal_id FK → journal(id) ON DELETE SET NULL` |
