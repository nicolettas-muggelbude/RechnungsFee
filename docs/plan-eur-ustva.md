# Implementierungsplan: Buchungen ohne Geldfluss → EÜR → UStVA

> Stand: 2026-05-30  
> Betrifft: Issue #55 (Buchungen ohne Geldkonto), Issue #61 (Forderungsausfall), v0.4 Auswertungen

---

## Vorarbeit: Vorsteuer-Snapshot im Journal (Schema v39)

### Problem
`vorsteuer_prozent=70` auf der Kategorie „Bewirtungskosten" wird beim Buchen **nicht** auf
`ust_betrag` angewendet – das Journal speichert immer den vollen USt-Betrag.  
EÜR Zeile 47 und UStVA KZ 66 benötigen aber den tatsächlich abziehbaren Anteil.

### Lösung
Neues Feld `journal.vorsteuer_betrag NUMERIC(12,2) DEFAULT 0`

| Kategorie | vorsteuer_prozent | ust_betrag (Beispiel 119 €) | vorsteuer_betrag |
|-----------|-------------------|-----------------------------|------------------|
| Büromaterial | 100 % | 19,00 € | 19,00 € |
| Bewirtungskosten | 70 % | 19,00 € | 13,30 € |
| Bewirtungskosten (nicht abzugsfähig) | 0 % | 0,00 € | 0,00 € |
| Privatentnahme | 0 % | 0,00 € | 0,00 € |

Berechnung beim Buchen: `vorsteuer_betrag = ust_betrag × vorsteuer_prozent / 100`

### Betroffene Dateien
- `src/backend/database/models.py` – Feld `vorsteuer_betrag` in `Journaleintrag`
- `src/backend/main.py` – Migration v39: `ALTER TABLE journal ADD COLUMN vorsteuer_betrag NUMERIC(12,2) DEFAULT 0`
- `src/backend/api/journal.py` – Berechnung in `_berechne_ust()` + Split-Buchung
- `src/backend/api/rechnungen.py` – `_erstelle_skonto_eintrag()`, `_zahlung_buchen()`

---

## Phase 1: Buchungen ohne Geldfluss

### 1a – `zahlungsart='Keine'` im Journal (Issue #55)

`journal.zahlungsart` ist ein String, kein FK → **kein Schema-Change nötig**.

| Datei | Änderung |
|-------|----------|
| `src/backend/api/journal.py` | `zahlungsart: Literal['Bar','Karte','Bank','PayPal','Keine']` im Pydantic-Schema |
| `src/backend/api/journal.py` | Kein Tagesabschluss-Kontostand-Update wenn `zahlungsart='Keine'` |
| Frontend `JournalPage` / Buchungsformular | Toggle „Keine Geldbewegung (z. B. AfA, Sachentnahme, Eigenverbrauch)" → blendet Zahlungsart aus, sendet `zahlungsart='Keine'` |
| Frontend Journal-Liste | Zahlungsart-Spalte zeigt „—" für diese Einträge |

**Typische Anwendungsfälle:**

| Buchung | art | Kategorie | Konto |
|---------|-----|-----------|-------|
| Jahres-AfA Computer | Ausgabe | Abschreibungen (AfA) | — |
| Eigenverbrauch KFZ | Ausgabe | KFZ-Kosten | — |
| Sachentnahme | Ausgabe | Privatentnahme | — |
| Eigenverbrauch Telefon | Ausgabe | Telefon & Internet | — |

### 1b – Forderungsausfall (Issue #61)

**Neue Kategorie** (über `_migrate_kategorien()`):

```python
{"name": "Forderungsausfall", "kontenart": "Aufwand",
 "konto_skr03": "4803", "konto_skr04": "6403",
 "eks_kategorie": None, "euer_zeile": 60,
 "vorsteuer_prozent": 0, "ust_satz_standard": 0}
```

Beschreibung: *„Uneinbringliche Forderungen (Kundeninsolvenz, endgültige Zahlungsverweigerung) – nur für USt-Pflichtige erzeugt dies eine §17-UStG-Korrekturbuchung"*

> **EKS: `eks_kategorie=None`** – Zuflussprinzip: unbezahlte Rechnungen waren nie in der EKS-Einnahme,
> es gibt nichts zu korrigieren. Die §17-UStG-Korrekturbuchung betrifft nur USt-Pflichtige,
> die in der Regel keine EKS stellen.

**Neuer `zahlungsstatus`-Wert:** `'uneinbringlich'` (String – kein ALTER TABLE nötig)

**Neuer Endpoint:** `POST /api/rechnungen/{id}/forderungsausfall`

```
Voraussetzung: zahlungsstatus IN ('offen', 'teilweise')

→ setzt zahlungsstatus = 'uneinbringlich'

Für USt-Pflichtige (nicht §19):
→ Journal-Korrekturbuchung:
   art        = 'Ausgabe'
   kategorie  = 'Forderungsausfall'
   zahlungsart = 'Keine'
   brutto     = Restbetrag (Rechnungsbetrag − bezahlt_betrag)
   ust_betrag = anteilige USt auf Restbetrag
   beschreibung = "Forderungsausfall RE-XXXXXX (§17 UStG)"

Für §19 Kleinunternehmer:
→ nur Statuswechsel, kein Journal-Eintrag (nie USt vereinnahmt)
```

**Frontend:**
- `RechnungenPage`: Button „Forderung ausbuchen" auf offenen/teilbezahlten Eingangs- **und** Ausgangsrechnungen
- Bestätigungs-Dialog mit Betrag + USt-Hinweis
- Status-Badge „Uneinbringlich" (grau, wie „Storniert")

---

## Phase 2: EÜR

Kein weiteres Schema nötig – alle Daten liegen im Journal.  
**Voraussetzung:** Schema v39 (vorsteuer_betrag) muss vorhanden sein.

### Backend: `src/backend/api/eur.py` (neue Datei)

```
GET  /api/eur/berechnen?jahr=YYYY
POST /api/eur/pdf
```

**Berechnungslogik `GET /api/eur/berechnen`:**

```
Schritt 1 – Betriebseinnahmen
  Für jede euer_zeile WHERE art='Einnahme' AND euer_zeile IS NOT NULL:
    betrag = SUM(brutto_betrag)
  Zeile 16 (vereinnahmte USt):
    SUM(ust_betrag) WHERE art='Einnahme'
  → §19-Flag: Zeile 16 = 0

Schritt 2 – Betriebsausgaben
  Für jede euer_zeile WHERE art='Ausgabe' AND euer_zeile IS NOT NULL:
    betrag = SUM(brutto_betrag)
  Zeile 47 (abziehbare Vorsteuer):
    SUM(vorsteuer_betrag) WHERE art='Ausgabe'   ← aus Schema v39
  → §19-Flag: Zeile 47 = 0

Schritt 3 – Gewinnermittlung
  Gewinn = Summe Betriebseinnahmen − Summe Betriebsausgaben
  (Vorzeichen: positiv = Gewinn, negativ = Verlust)
```

**JSON-Rückgabe (Beispiel):**

```json
{
  "jahr": 2026,
  "ist_kleinunternehmer": false,
  "einnahmen": [
    {"zeile": 11, "bezeichnung": "Betriebseinnahmen (regelbesteuert)", "betrag": "12500.00"},
    {"zeile": 16, "bezeichnung": "Umsatzsteuer (vereinnahmt)", "betrag": "1840.00"}
  ],
  "ausgaben": [
    {"zeile": 27, "bezeichnung": "Wareneinkauf / Fremdleistungen", "betrag": "3200.00"},
    {"zeile": 47, "bezeichnung": "Vorsteuerbeträge", "betrag": "480.00"}
  ],
  "summe_einnahmen": "14340.00",
  "summe_ausgaben": "8620.00",
  "gewinn": "5720.00",
  "hinweis_afa": true   ← true wenn AfA-Buchungen vorhanden
}
```

**PDF-Struktur** (`POST /api/eur/pdf`, fpdf2, analog EKS-Export):

```
┌─────────────────────────────────────────────────────┐
│  Anlage EÜR – Steuerjahr 2026                       │
│  Mustermann Consulting · USt-ID DE123456789         │
│  Erstellt: 30.05.2026                               │
├─────────────────────────────────────────────────────┤
│  A  Betriebseinnahmen                               │
│  ─────────────────────────────────────────────────  │
│  Z11  Betriebseinnahmen (regelbesteuert)  12.500,00 │
│  Z16  Umsatzsteuer (vereinnahmt)           1.840,00 │
│       Summe Einnahmen                     14.340,00 │
├─────────────────────────────────────────────────────┤
│  B  Betriebsausgaben                                │
│  ─────────────────────────────────────────────────  │
│  Z27  Wareneinkauf / Fremdleistungen       3.200,00 │
│  Z47  Vorsteuerbeträge                       480,00 │
│       ...                                           │
│       Summe Ausgaben                       8.620,00 │
├─────────────────────────────────────────────────────┤
│  Gewinn                                    5.720,00 │
└─────────────────────────────────────────────────────┘
  ⚠ AfA-Buchungen sind nur enthalten soweit sie
    manuell im Journal erfasst wurden. Ohne AfA-
    Buchungen weicht dieser Wert vom steuerlichen
    Gewinn ab. Bitte mit Steuerberater abstimmen.
```

### Frontend: `src/frontend/src/pages/auswertungen/EuerPage.tsx`

- Jahresauswahl (Dropdown, default: aktuelles Jahr)
- Abschnitt A (Einnahmen) + Abschnitt B (Ausgaben) als Sektionen
- Zeilen mit Betrag 0,00 € ausgegraut aber sichtbar
- Gewinn/Verlust-Banner (grün = Gewinn, rot = Verlust)
- Button „PDF exportieren"
- §19-Nutzer: Info-Banner „Als Kleinunternehmer weist du keine USt aus – Zeilen 16 und 47 entfallen"
- AfA-Hinweis-Banner wenn `hinweis_afa=true`

**Navigation:** Neuer Menüpunkt „Auswertungen" mit Unterseiten EÜR und UStVA.

---

## Phase 3: UStVA

Technisch unabhängig von Phase 1/2, logisch danach.  
**Voraussetzung:** Schema v39 (vorsteuer_betrag für KZ 66).

### Backend: `src/backend/api/ustva.py` (neue Datei)

```
GET  /api/ustva/berechnen?jahr=YYYY&zeitraum=M01|M02|...|Q1|Q2|Q3|Q4
POST /api/ustva/pdf
```

**Kennzahlen-Mapping:**

| ELSTER KZ | Bezeichnung | Quelle im Journal |
|-----------|-------------|-------------------|
| KZ 81 | Umsätze 19 % | `SUM(netto_betrag)` WHERE art='Einnahme' AND ust_satz=19 |
| KZ 86 | Umsätze 7 % | `SUM(netto_betrag)` WHERE art='Einnahme' AND ust_satz=7 |
| KZ 35 | Steuerfreie Umsätze | `SUM(brutto_betrag)` WHERE art='Einnahme' AND ust_satz=0 AND NOT §19 |
| KZ 41 | §19-Umsätze | `SUM(brutto_betrag)` WHERE art='Einnahme', wenn ist_kleinunternehmer |
| KZ 66 | Vorsteuer aus Eingangsrechnungen | `SUM(vorsteuer_betrag)` WHERE art='Ausgabe' |
| — | **Zahllast** | (KZ81×0,19 + KZ86×0,07) − KZ66 |

**Zeiträume:** Monat M01–M12, Quartale Q1 (Jan–Mrz), Q2 (Apr–Jun), Q3 (Jul–Sep), Q4 (Okt–Dez).

**PDF:** Tabelle mit Kennzahlen + Beträgen, Zahllast-Box,  
Hinweis: *„Diese Aufstellung dient zur Vorbereitung der ELSTER-Voranmeldung und ersetzt diese nicht."*

### Frontend: `src/frontend/src/pages/auswertungen/UstvaPage.tsx`

- Tabs: Monat / Quartal
- Kennzahlen-Tabelle (ELSTER-Nummerierung)
- Zahllast-Box (grün wenn Erstattung, rot wenn Zahlung)
- §19-Nutzer: vereinfachte Ansicht (nur KZ 41, keine Zahllast, Hinweis auf Befreiung)
- Warnhinweis wenn Tagesabschlüsse im Zeitraum fehlen

---

## Sequenz und Abhängigkeiten

```
Schema v39
├── journal.vorsteuer_betrag          ← Voraussetzung für EÜR Z47 + UStVA KZ66
└── (rechnungen.zahlungsstatus 'uneinbringlich' – kein ALTER nötig)

Phase 1 – Buchungen ohne Geldfluss
├── zahlungsart='Keine' (kein Schema-Change)
├── Kategorie „Forderungsausfall" (seed + _migrate_kategorien)
├── POST /rechnungen/{id}/forderungsausfall
└── Frontend: Toggle + Ausbuchen-Button

Phase 2 – EÜR
├── Aufbaut auf Schema v39 (vorsteuer_betrag)
├── Profitiert von Phase 1 (AfA jetzt buchbar → EÜR vollständiger)
└── api/eur.py + EuerPage.tsx

Phase 3 – UStVA
├── Aufbaut auf Schema v39 (vorsteuer_betrag für KZ 66)
└── api/ustva.py + UstvaPage.tsx
```

---

## EKS-Auswirkungen

| Bereich | Verhalten | Begründung |
|---------|-----------|------------|
| AfA-Buchungen (Phase 1) | fließen **nicht** in EKS | EKS-Formular hat kein AfA-Feld; Anlagevermögen geht vollständig in B8 „Investitionen" im Kaufjahr |
| Eigenverbrauch/Sachentnahmen (Phase 1) | fließen **automatisch** in EKS | Nutzen bestehende Kategorien mit korrekten `eks_kategorie`-Werten (z. B. B6_3, B11) |
| Forderungsausfall (Phase 1b) | `eks_kategorie=None` | Zuflussprinzip: unbezahlte Rechnungen waren nie EKS-Einnahme; nichts zu korrigieren |
| `vorsteuer_betrag` (Schema v39) | **Bonus: B17 auto-berechnen** | EKS-Zeile B17 „Gezahlte Vorsteuer" könnte aus `SUM(vorsteuer_betrag)` der Ausgaben befüllt werden – B17 ist aktuell deaktiviert, optional nach Phase 2 aktivierbar |
| A5_1 / A5_2 (Roadmap-Punkt) | bereits implementiert ✅ | Wird automatisch aus `ust_betrag` der A1/A3/A4-Einnahmen berechnet; Roadmap-Eintrag ist veraltet |

---

## Bewusste Vereinfachungen / offene Punkte

| Thema | Entscheidung |
|-------|--------------|
| ELSTER-XML-Export | Erstversion: PDF zur manuellen Übertragung; ELSTER-XML als späteres Feature (erfordert Zertifikat-Handling) |
| AfA-Assistent | Kein AfA-Modul – manuelle Buchung über Phase 1; Steuerberater liefert AfA-Betrag |
| §25a in EÜR | Korrekt automatisch: Umsatz als normale Einnahme, kein separater USt-Ausweis, `euer_zeile` der Kategorie greift |
| Bewirtungskosten 70/30 | Zwei Kategorien → zwei EÜR-Zeilen; keine Extra-Logik nötig |
| EKS B17 Vorsteuer | Optional nach Schema v39: `SUM(vorsteuer_betrag)` → B17; erst aktivieren wenn Bedarf besteht |
| CSV-Import Kontenplan | Separates Feature (aus Issue #111), unabhängig von EÜR/UStVA |
| Wiederholende Buchungen | Eigenes Feature (Roadmap v0.2.x), kein Blocker für EÜR |
