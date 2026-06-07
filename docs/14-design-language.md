# RechnungsFee – Design Language

Dieses Dokument legt die verbindliche Designsprache für alle Features fest.
Neue Seiten, Dialoge und Komponenten müssen diese Muster einhalten.

---

## 1. Farben

### Primärfarbe (Aktionen)
| Verwendung | Klassen |
|---|---|
| Button aktiv | `bg-blue-600 text-white hover:bg-blue-700` |
| Leichter Hintergrund | `bg-blue-50 dark:bg-blue-950` |
| Border | `border-blue-200 dark:border-blue-800` |
| Text | `text-blue-600 dark:text-blue-400` |
| Ausgewählte Zeile | `bg-blue-50 dark:bg-blue-950` |

### Neutrale Basis (Slate)
| Verwendung | Light | Dark |
|---|---|---|
| Seitenhintergrund | `bg-white` / `bg-slate-50` | `dark:bg-slate-900` |
| Karten/Panels | `bg-white` | `dark:bg-slate-800` |
| Sidebar | `bg-white` | `dark:bg-slate-900` |
| Border | `border-slate-200` | `dark:border-slate-700` |
| Border leicht | `border-slate-100` | `dark:border-slate-700` |
| Text primär | `text-slate-800` | `dark:text-slate-100` |
| Text sekundär | `text-slate-600` | `dark:text-slate-300` |
| Text gedimmt | `text-slate-500` | `dark:text-slate-400` |
| Text Platzhalter | `text-slate-400` | `dark:text-slate-500` |

### Statusfarben
Alle Status-Farben folgen demselben Muster: `bg-{farbe}-50 text-{farbe}-700 border-{farbe}-200` / `dark:bg-{farbe}-950 dark:text-{farbe}-300 dark:border-{farbe}-800`

| Status | Farbe | Verwendung |
|---|---|---|
| Erfolg / Bezahlt | Green | Zahlungsstatus, positive Bestätigungen |
| Warnung / Teilzahlung | Amber | Warnhinweise, offene Aktionen |
| Fehler / Unbezahlt | Red | Fehler, Löschaktionen, Fälligkeiten |
| Info / Entwurf | Blue | Hinweise, Info-Boxen |
| Sonstige Tags | Purple | Typ-Tags (Fremdleistung o.ä.) |

---

## 2. Typografie

### Hierarchie
| Ebene | Klassen |
|---|---|
| Seitenüberschrift | `text-2xl font-bold text-slate-800 dark:text-slate-100` |
| Abschnittsüberschrift | `text-lg font-semibold text-slate-800 dark:text-slate-100` |
| Formular-Label | `block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1` |
| Abschnitts-Label | `text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide` |
| Fließtext | `text-sm text-slate-600 dark:text-slate-300` |
| Kleintext / Captions | `text-xs text-slate-400 dark:text-slate-500` |
| Technische Werte | `font-mono` (Belegnummern, IDs, IBAN) |

### Schriftgewichte
- `font-bold` – Seitenüberschriften
- `font-semibold` – Abschnittstitel, Tabellen-Header
- `font-medium` – Labels, Button-Text
- `font-normal` – Fließtext (Default)

---

## 3. Layout

### Seitenstruktur
```
<aside>         w-56, bg-white dark:bg-slate-900, border-r
<main>          flex-1, overflow-hidden
  <header>      p-6 pb-4 shrink-0 — Titel + "+ Neu"-Button + Filter
  <content>     flex-1 overflow-y-auto — Tabelle oder Hauptinhalt
  [<panel>]     w-1/3 min-w-[260px] shrink-0 — Formular/Detail rechts
```

### Sidebar-Navigationsstruktur
```
Logo + Versionsnummer
─────────────────────
Dashboard

FAKTURIERUNG          ← immer sichtbar, kein Toggle
  Angebote            ← Platzhalter (bald)
  Aufträge            ← Platzhalter (bald)
  Lieferscheine       ← eigenständige Seite /lieferscheine
  Rechnungen

BUCHHALTUNG ▼         ← einklappbar
  Journal
  Tagesabschlüsse

AUSWERTUNG ▼          ← einklappbar; Einträge bedingt sichtbar
  EÜR                 ← immer
  UStVA               ← nur wenn !Kleinunternehmer
  ZM                  ← nur wenn ig-Buchungen existieren
  EKS                 ← nur wenn bezieht_transferleistungen
  GoBD-Export

STAMMDATEN ▼          ← einklappbar
  Kunden
  Lieferanten
  Artikelstamm

EINSTELLUNGEN ▼       ← einklappbar
  Dokumentenpakete
  Konten
  Kategorien
  Nummernkreise
  Steuersätze
  Rechnungsvorlagen
  Unternehmen
─────────────────────
Backup
Info & Updates
```

### Header-Muster (jede Seite)
```tsx
<div className="p-6 pb-4 shrink-0">
  <div className="flex items-center justify-between mb-4">
    <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Titel</h2>
    <button className="bg-blue-600 ...">+ Neu</button>
  </div>
  {/* Filter-Zeile */}
</div>
```

### Zweispalten-Split
```tsx
<div className="flex flex-1 overflow-hidden">
  <div className="flex-1 overflow-y-auto">   {/* Liste */}
  <div className="w-1/3 min-w-[260px] shrink-0 border-l ...">  {/* Panel */}
</div>
```

### Abstände
| Kontext | Klassen |
|---|---|
| Seiten-Padding | `p-6` |
| Panel-Padding | `px-6 py-4` |
| Tabellenzellen | `px-4 py-2.5` |
| Formularfelder Abstand | `space-y-3` |
| Abschnitte | `space-y-4` |
| Zwischen Elementen | `gap-2` / `gap-3` |

---

## 4. Tabellen

### Grundstruktur
```tsx
<table className="w-full text-sm">
  <thead className="sticky top-0 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
    <tr>
      <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 dark:text-slate-400">
        Spalte
      </th>
    </tr>
  </thead>
  <tbody>
    <tr className="border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors cursor-pointer">
      <td className="px-4 py-2.5">Inhalt</td>
    </tr>
  </tbody>
</table>
```

### Zeilen-Zustände
| Zustand | Klassen |
|---|---|
| Normal | `border-b border-slate-100 dark:border-slate-700` |
| Hover | `hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors` |
| Ausgewählt | `bg-blue-50 dark:bg-blue-950` |
| Ausgewählt Text | `text-blue-700 dark:text-blue-300` |

### Aufklapp-Zeile (Accordion)
Nach der ausgewählten `<tr>` folgt eine Detail-`<tr>`:
```tsx
{isSelected && (
  <tr className="bg-blue-50 dark:bg-blue-950 border-b border-slate-200 dark:border-slate-700">
    <td colSpan={N} className="px-6 py-4">
      <div className="grid grid-cols-2 gap-x-8 gap-y-3 text-xs">
        {/* Felder */}
      </div>
    </td>
  </tr>
)}
```
Chevron-Indikator im ersten `<td>`: `▼` / `▶` als Text, Klasse `mr-1 text-slate-400`

---

## 5. Buttons

### Primär
```
bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50
```

### Sekundär
```
border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg px-4 py-2 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-700
```

### Gefahr (Löschen)
```
bg-red-600 text-white rounded-lg px-3 py-1.5 text-xs font-medium hover:bg-red-700 disabled:opacity-50
```
Variante mit Border (weniger aggressiv):
```
border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 rounded-lg px-3 py-1.5 text-xs hover:bg-red-50 dark:hover:bg-red-950
```

### Link-Button (inline)
```
text-xs text-blue-600 dark:text-blue-400 hover:underline
```

### Button-Gruppe (Formular-Footer)
```tsx
<div className="flex gap-3 pt-2">
  <button className="flex-1 border ...">Abbrechen</button>
  <button className="flex-1 bg-blue-600 ...">Speichern</button>
</div>
```

---

## 6. Formulare

### Eingabefeld
```
w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm
focus:outline-none focus:ring-2 focus:ring-blue-500
dark:bg-slate-700 dark:text-slate-100
```
Fehler-Zustand: `border-red-400 dark:border-red-500`

### Label
```
block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1
```

### Fehlermeldung
```
text-red-500 dark:text-red-400 text-xs mt-0.5
```

### Select
Identische Klassen wie Eingabefeld.

### Checkbox
```tsx
<label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 cursor-pointer">
  <input type="checkbox" className="rounded" />
  Text
</label>
```

### Mehrspaltig
```tsx
<div className="grid grid-cols-2 gap-3">...</div>
```

### Abschnitts-Trenner im Formular
```tsx
<div className="border-t border-slate-200 dark:border-slate-700 pt-3 space-y-2">
  <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide">
    Abschnitt
  </p>
  {/* Felder */}
</div>
```

---

## 7. Modals / Dialoge

### Overlay
```
fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4
```

### Container
```
bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-md
```
Größen: `max-w-md` (klein) · `max-w-lg` (mittel) · `max-w-2xl` (groß)

### Header
```tsx
<div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
  <h3 className="font-semibold text-slate-800 dark:text-slate-100">Titel</h3>
  <button className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-xl">×</button>
</div>
```

### Body
```
p-6 space-y-4
```

---

## 8. Status-Badges / Pills

### Grundform
```
text-xs font-medium px-2 py-0.5 rounded-full border
```

### Zahlungsstatus
```tsx
// Bezahlt
"bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800"

// Teilzahlung
"bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800"

// Offen
"bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-800"

// Entwurf
"bg-slate-100 text-slate-500 border-slate-200 dark:bg-slate-700 dark:text-slate-400 dark:border-slate-600"
```

### Typ-Tags (kompakter)
```
px-1.5 py-0.5 rounded-full font-medium text-xs
```

---

## 9. Info-Boxen / Banner

### Inline Info-Box (in Panels/Formularen)
```tsx
<div className="rounded-xl p-3 border bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300 text-xs">
  Hinweis
</div>
```
Varianten: Blue (Info) · Amber (Warnung) · Red (Fehler)

### Seiten-Banner (oben, unter Header)
```tsx
<div className="border-b px-4 py-2.5 flex items-center gap-3 bg-amber-50 border-amber-200 dark:bg-amber-950 dark:border-amber-800 text-amber-800 dark:text-amber-300 text-sm">
  Nachricht
</div>
```

---

## 10. Fortschrittsbalken

```tsx
<div className="h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
  <div
    className="h-full bg-green-500 rounded-full transition-all"
    style={{ width: `${prozent}%` }}
  />
</div>
```

---

## 11. Tooltip (InfoTooltip)

Komponente: `src/frontend/src/components/InfoTooltip.tsx`

```tsx
<InfoTooltip text="Erklärungstext" side="top" align="left" />
```
- `side`: `"top"` | `"bottom"`
- `align`: `"left"` | `"center"` | `"right"` (right = Popup öffnet sich nach links, verhindert Rand-Abschneiden)

---

## 12. Border-Radius

| Verwendung | Klasse |
|---|---|
| Standard (Inputs, Buttons, Karten) | `rounded-lg` |
| Modals, Hervorgehobene Karten | `rounded-xl` |
| Badges, Pills | `rounded-full` |

---

## 13. Dark Mode

Vollständig implementiert via `dark:`-Prefix (Tailwind class-Strategie).

**Regel:** Jede Farbe die in Light Mode gesetzt wird, braucht ein `dark:`-Gegenstück.

Standardpaare:
```
bg-white             → dark:bg-slate-800 (Karte) / dark:bg-slate-900 (Seite)
border-slate-200     → dark:border-slate-700
text-slate-800       → dark:text-slate-100
text-slate-600       → dark:text-slate-300
text-slate-500       → dark:text-slate-400
bg-slate-50          → dark:bg-slate-700 (Hover)
bg-blue-50           → dark:bg-blue-950
bg-green-50          → dark:bg-green-950
bg-amber-50          → dark:bg-amber-950
bg-red-50            → dark:bg-red-950
```

---

## 14. Dos & Don'ts

**Do:**
- Immer `text-sm` als Standard-Schriftgröße in Tabellen und Formularen
- Immer `transition-colors` bei Hover-Zuständen
- Immer `disabled:opacity-50` bei Buttons
- Immer `focus:outline-none focus:ring-2 focus:ring-blue-500` bei Inputs
- Jede Farbe mit Dark-Mode-Variante versehen
- `font-mono` für technische Werte (IBAN, Belegnummern)

**Don't:**
- Keine anderen Farbfamilien einführen ohne Absprache (kein Teal, Cyan, Orange als neue Akzentfarbe)
- Keine Inline-Styles für Farben oder Abstände
- Keine hardcodierten Pixelwerte (keine `style={{ width: '300px' }}` für Layouts)
- Kein `text-base` oder `text-lg` in Tabellen/Formularen
- Kein `rounded` (ohne Suffix) — immer `rounded-lg` oder spezifischer
