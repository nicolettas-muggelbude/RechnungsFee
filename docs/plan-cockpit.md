# Plan: Unternehmer-Cockpit (BWA light)

**Issue:** #232  
**Ziel:** Verständliche betriebswirtschaftliche Auswertung mit Grafiken – kein Klon der Steuerberater-BWA sondern ein visuelles Cockpit für Freiberufler/Kleinunternehmer.

---

## Kernprinzip

Steuerberater-BWA: dichte Tabelle mit Fachbegriffen → niemand versteht sie  
Unser Cockpit: Grafiken zuerst, Zahlen dahinter – auf einen Blick lesbar, ohne Vorkenntnisse

---

## Entscheidungen

| Thema | Entscheidung |
|-------|-------------|
| Chart-Bibliothek | **Recharts** (leichtgewichtig, TypeScript-first, React 19 kompatibel) |
| Zeitraum-Wahl | Monat / Quartal / Jahr + Jahresauswahl (kein „von-bis" – zu komplex) |
| Navigation | Neuer Eintrag „Cockpit" ganz oben in `auswertungNavAlle` (immer sichtbar) |
| Route | `/cockpit` |
| PDF-Export | Phase 2 (nach Grundfunktion) |
| Vorjahresvergleich | Phase 2 |

---

## Abschnitt A – Backend (`src/backend/api/cockpit.py`)

### Endpunkt

```
GET /api/cockpit?zeitraum=monat&wert=2026-06
GET /api/cockpit?zeitraum=quartal&wert=2026-Q2
GET /api/cockpit?zeitraum=jahr&wert=2026
```

### Response-Struktur

```json
{
  "zeitraum_label": "Juni 2026",
  "kpis": {
    "einnahmen": 4200.00,
    "ausgaben": 1850.00,
    "gewinn": 2350.00,
    "gewinn_marge_prozent": 55.95
  },
  "monatsbalken": [
    { "monat": "Jan", "einnahmen": 3100, "ausgaben": 1400, "gewinn": 1700 },
    ...bis aktueller Monat (oder gewähltes Jahr)
  ],
  "ausgaben_kategorien": [
    { "name": "Büro & Verwaltung", "betrag": 420.00 },
    { "name": "Fahrtkosten", "betrag": 180.00 },
    ...
  ],
  "einnahmen_nach_ust": [
    { "satz": "19%", "betrag": 3500.00 },
    { "satz": "7%", "betrag": 500.00 },
    { "satz": "0% / §19", "betrag": 200.00 }
  ]
}
```

### Datenquelle
Ausschließlich `journal`-Tabelle (Zuflussprinzip, wie EÜR).  
Ausgaben-Kategorien werden nach `kategorien.kontenart` gruppiert:
- Einnahmen: `kontenart = 'Erlös'`
- Ausgaben: alle anderen buchbaren Kategorien

### Datei
`src/backend/api/cockpit.py` – neues Router-Modul, in `main.py` eingebunden

---

## Abschnitt B – Frontend (`src/frontend/src/pages/cockpit/CockpitPage.tsx`)

### Layout

```
┌─────────────────────────────────────────────────────┐
│  Cockpit          [Monat ▼] [Juni 2026 ▼]           │
├──────────┬──────────┬──────────┬────────────────────┤
│ Einnahmen│ Ausgaben │  Gewinn  │  Gewinnmarge        │
│ 4.200 €  │ 1.850 €  │ 2.350 €  │  55,9 %             │
├──────────┴──────────┴──────────┴────────────────────┤
│                                                     │
│  Einnahmen vs. Ausgaben – Jahresverlauf             │
│  [Balkendiagramm: Jan–Dez, grün/rot]                │
│                                                     │
├──────────────────────┬──────────────────────────────┤
│  Gewinnverlauf       │  Ausgaben nach Kategorie     │
│  [Liniendiagramm]    │  [Donut-Chart]               │
│                      │                              │
├──────────────────────┴──────────────────────────────┤
│  Einnahmen nach USt-Satz   Detailtabelle (Kategorien│
│  [kleine Balken 19%/7%/0%] aufklappbar)             │
└─────────────────────────────────────────────────────┘
```

### Komponenten

| Datei | Inhalt |
|-------|--------|
| `CockpitPage.tsx` | Hauptseite, Zeitraum-State, API-Call |
| `KpiCard.tsx` | Einzelne KPI-Kachel (Wert + Label + Trend-Pfeil) |
| `MonatsbalkenChart.tsx` | Recharts `BarChart` – Einnahmen/Ausgaben/Gewinn |
| `GewinnverlaufChart.tsx` | Recharts `LineChart` – Gewinn pro Monat |
| `KategorienDonut.tsx` | Recharts `PieChart` – Ausgaben nach Kategorie |
| `EinnahmenUStBalken.tsx` | Recharts `BarChart` horizontal – USt-Satz-Aufschlüsselung |
| `KategorienTabelle.tsx` | Aufklappbare Detailtabelle unter den Charts |

### Zeitraum-Wahl
- Dropdown: Monat / Quartal / Jahr
- Bei Monat: zweites Dropdown mit Monaten des gewählten Jahres
- Bei Quartal: Q1–Q4 des gewählten Jahres
- Bei Jahr: nur Jahresauswahl
- Vorauswahl: aktueller Monat

### Farben
- Einnahmen: grün (`text-emerald-600`, `fill-emerald-500`)
- Ausgaben: rot (`text-red-500`, `fill-red-400`)
- Gewinn: blau (`text-blue-600`, `fill-blue-500`)
- Donut: Tailwind-Palette (slate/blue/indigo/violet/purple…)

---

## Abschnitt C – Integration

| Was | Wo |
|-----|----|
| Route `/cockpit` | `src/frontend/src/App.tsx` |
| Nav-Eintrag „Cockpit" | `AppLayout.tsx` → `auswertungNavAlle` ganz oben |
| Icon | `dashboard` (Material Symbols) |
| Recharts installieren | `npm install recharts` in `src/frontend` |
| API-Client | `src/frontend/src/api/client.ts` → `getCockpit(params)` |
| Changelog | `changelog.ts` → v0.4.8 oder neuer Block |

---

## Betroffene Dateien

| Datei | Änderung |
|-------|----------|
| `src/backend/api/cockpit.py` | Neu |
| `src/backend/main.py` | Router einbinden |
| `src/frontend/src/pages/cockpit/CockpitPage.tsx` | Neu |
| `src/frontend/src/pages/cockpit/KpiCard.tsx` | Neu |
| `src/frontend/src/pages/cockpit/MonatsbalkenChart.tsx` | Neu |
| `src/frontend/src/pages/cockpit/GewinnverlaufChart.tsx` | Neu |
| `src/frontend/src/pages/cockpit/KategorienDonut.tsx` | Neu |
| `src/frontend/src/pages/cockpit/EinnahmenUStBalken.tsx` | Neu |
| `src/frontend/src/pages/cockpit/KategorienTabelle.tsx` | Neu |
| `src/frontend/src/api/client.ts` | `getCockpit()` + Typen |
| `src/frontend/src/App.tsx` | Route `/cockpit` |
| `src/frontend/src/components/AppLayout.tsx` | Nav-Eintrag |
| `src/frontend/package.json` | recharts dependency |
| `src/frontend/src/data/changelog.ts` | Changelog-Eintrag |

---

## Implementierungsreihenfolge

1. **A** – Backend: `cockpit.py` + Router-Einbindung
2. **B** – Frontend: Seite mit KPI-Kacheln + Zeitraum-Wahl (ohne Charts)
3. **C** – Charts schrittweise einbauen: Monatsbalken → Gewinnverlauf → Donut → USt-Balken
4. **D** – Detailtabelle + Nav-Eintrag + Route

---

## Verifikation

1. Monat wählen → KPIs korrekt, Balkendiagramm zeigt Jan–aktueller Monat
2. Quartal wählen → Balkendiagramm zeigt 3 Monate des Quartals
3. Jahr wählen → alle 12 Monate (fehlende Monate = 0)
4. Donut zeigt Ausgaben-Kategorien korrekt aufgeschlüsselt
5. USt-Balken korrekt: 19%/7%/0% aus Journal
6. Leerer Zeitraum (keine Buchungen) → kein Crash, 0-Werte anzeigen
