# Plan: Vollständige Länderliste + Suchfeld (Issue #401)

## Context

PR #396 hat acht Drittländer nachgereicht und dabei aufgeworfen, ob die Länderliste in
`src/frontend/src/utils/laender.ts` (aktuell 39 Einträge) weiter auf Zuruf wächst oder einmal
vollständig wird. Issue #401 schlägt vor: einmalig die vollständige ISO-3166-1-Liste (~249
Länder) aus einer zitierbaren Quelle generieren, statisch einchecken, und ein Suchfeld statt
eines langen `<select>` anbieten, da ein Standard-Dropdown mit ~250 Einträgen schlecht bedienbar
wäre. Favoriten/Aktivieren-Einstellungen sind im Issue selbst bewusst zurückgestellt.

## Datenquelle (bereits recherchiert)

Amtliche Quelle: **Auswärtiges Amt – Verzeichnis der Staatennamen für den amtlichen Gebrauch**,
als XLSX verfügbar unter
`https://www.auswaertiges-amt.de/resource/blob/264782/538118f02d2dfaa5f16f7fb356ceb34e/xlsx-data.xlsx`
(Stand laut AA-Seite: 29.07.2026). Genau die im Issue zitierte Quelle.

**Vorgehen bei der Umsetzung** (nicht per LLM-Zusammenfassung, um keine Einträge zu verlieren):
1. XLSX per `curl` herunterladen, mit einem kurzen Python-Einzeiler (`openpyxl`, bei Bedarf
   `pip install`) programmatisch zeilenweise parsen – keine KI-Summarization einer so langen
   Liste, das Risiko stillschweigend fehlender Einträge ist sonst zu hoch.
2. Spalten: 2-stelliger ISO-Code (nicht 3-stellig, passend zu `Land.code: string` im
   bestehenden Format wie `"DE"`) + **Kurzform** des deutschen Namens (nicht die amtliche
   Langform mit Staatsform, z. B. „Vereinigte Arabische Emirate" nicht „Vereinigte Arabische
   Emirate (die)" o. ä.) – konsistent mit den 39 bereits vorhandenen Einträgen.
3. Nach dem Parsen: Anzahl der Zeilen gegenprüfen (~249 erwartet) und stichprobenartig gegen die
   39 bereits vorhandenen Einträge abgleichen (Code + Name müssen exakt übereinstimmen, sonst
   Formatierungs-Inkonsistenz).
4. Quelle + Datum als Kommentar im Datei-Header von `laender.ts` dokumentieren (Issue-Vorgabe).

`EU_LAENDER_CODES` (eigenständiges `Set<string>`, `laender.ts:21-24`), `BEVORZUGTE_CODES`
(DE/AT/CH zuerst), `UST_IDNR_FORMATE` (nur EU) und `database/seed.py::EU_LAENDER` (Backend,
MwSt-Sätze) bleiben alle unverändert – nur `LAENDER_QUELLE` wächst von 39 auf ~249 Einträge.

## Neue Komponente statt Wiederverwendung von `StammdatenCombobox`

Es gibt bereits `src/frontend/src/components/StammdatenCombobox.tsx` (generische
Such-Combobox: Filter, Pfeiltasten, Enter/Escape, Außenklick – aktuell für Kunde/Lieferant in
`RechnungenPage.tsx`, `ProformaPage.tsx`, `AuftraegePage.tsx`, `AngebotePage.tsx`). Interaktionsmuster
ist genau richtig, aber **semantisch nicht passend**: `StammdatenCombobox` erlaubt explizit
Freitext als Fallback („Kein Treffer – wird als Freitext übernommen"), weil Einmalkunden-Namen
offen sind. Ein Land ist dagegen immer einer aus der festen Liste – Freitext-Fallback wäre hier
falsch (ein Tippfehler würde sonst als „gültiges" Land durchgehen).

**Neue, eigenständige Komponente `src/frontend/src/components/LandCombobox.tsx`**, das
Interaktionsmuster von `StammdatenCombobox` übernehmen (Filter, Pfeiltasten, Enter, Escape,
Außenklick-schließt), aber:
- `value: string` (Code) + `onChange: (code: string) => void` – kein Freitext-Zweig
- Filter durchsucht sowohl `name` als auch `code` (z. B. „US" findet „USA")
- Bei Fokus auf leeres Feld: zeigt die Liste ab dem ersten Zeichen wie gehabt, zusätzlich beim
  Fokussieren eines leeren Feldes direkt die ersten Einträge (DACH zuerst) statt komplett leer –
  bei ~249 Einträgen sinnvoller als bei `StammdatenCombobox`s Kundenliste
- Verlässt der Nutzer das Feld ohne gültige Auswahl (Tippfehler o. Ä.), auf den zuletzt gültigen
  Code zurücksetzen statt ungültigen Text stehen zu lassen (kein Freitext-Fallback)
- „Kein Treffer" ohne den Freitext-Hinweistext

`StammdatenCombobox.tsx` selbst bleibt unangetastet – kein Risiko für die vier bestehenden
Einsatzstellen.

## Integration – 6 Fundstellen, gleiches Ersetzungsmuster

Jede Stelle rendert aktuell `<select {...register('land')}>{LAENDER.map(l => <option .../>)}</select>`
(react-hook-form) bzw. einen kontrollierten `<select value=/onChange=>` (Rechnungen). Ersetzen
durch `<LandCombobox value={watch('land')} onChange={v => setValue('land', v)} />` (bzw.
`value={partnerLand} onChange={setPartnerLand}` in `RechnungenPage.tsx`). Betroffen:

- `src/frontend/src/pages/stammdaten/UnternehmenPage.tsx:371`
- `src/frontend/src/components/LieferantErstellenModal.tsx:93`
- `src/frontend/src/components/KundeErstellenModal.tsx:128`
- `src/frontend/src/pages/lieferanten/LieferantenPage.tsx:745`
- `src/frontend/src/pages/kunden/KundenPage.tsx:1347`
- `src/frontend/src/pages/rechnungen/RechnungenPage.tsx:3632` (Einmalkunde/-partner)

## Verifikation

1. `npx tsc -b` sauber nach allen Änderungen.
2. Manueller Test im Browser: Eines der sechs Formulare öffnen, Land-Feld tippen (z. B. „arab"
   → Vereinigte Arabische Emirate; „US" → USA), Pfeiltasten + Enter, Escape, Außenklick,
   ungültiger Text + Blur (muss auf letzten gültigen Code zurückspringen).
3. Stichprobe: EU-Erkennung (`istEuLand()`) für ein paar der neuen Drittländer weiterhin falsch
   negativ prüfen (dürfen nicht versehentlich als EU gelten) – reiner Bestandsschutz, da
   `EU_LAENDER_CODES` unangetastet bleibt.
4. Changelog-Eintrag + ggf. CLAUDE.md-Hinweis folgen im Anschluss über den etablierten Workflow.
