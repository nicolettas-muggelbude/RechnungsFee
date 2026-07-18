/**
 * Filter-Persistenz für die Session (bis Programmende).
 *
 * Modul-Level-Variablen überleben das Unmount/Remount von React-Komponenten,
 * werden aber bei App-Neustart zurückgesetzt – genau das gewünschte Verhalten.
 *
 * Verwendung in Komponenten:
 *   const [filterModus, _setFilterModus] = useState(() => journalFilter.modus)
 *   const setFilterModus = (m: JournalFilterModus) => { journalFilter.modus = m; _setFilterModus(m) }
 */

function heute(): string { return new Date().toISOString().slice(0, 10) }
function aktuellerMonat(): string { return new Date().toISOString().slice(0, 7) }

// ---------------------------------------------------------------------------
// Journal
// ---------------------------------------------------------------------------

export type JournalFilterModus = 'monat' | 'datum' | 'zeitraum' | 'alle' | 'jahr'

export interface JournalFilterState {
  modus:          JournalFilterModus
  monat:          string
  datum:          string
  datumVon:       string
  datumBis:       string
  art:            '' | 'Einnahme' | 'Ausgabe'
  kategorieId:    string
  zahlungsartTyp: '' | 'bar' | 'unbar'
  nurBebuchte:    boolean
}

export const journalFilter: JournalFilterState = {
  modus:          'monat',
  monat:          aktuellerMonat(),
  datum:          heute(),
  datumVon:       heute(),
  datumBis:       heute(),
  art:            '',
  kategorieId:    '',
  zahlungsartTyp: '',
  nurBebuchte:    false,
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export type DashboardFilterModus = 'monat' | 'datum' | 'zeitraum' | 'alle' | 'jahr'

export interface DashboardFilterState {
  modus:    DashboardFilterModus
  monat:    string
  datum:    string
  datumVon: string
  datumBis: string
}

export const dashboardFilter: DashboardFilterState = {
  modus:    'monat',
  monat:    aktuellerMonat(),
  datum:    heute(),
  datumVon: heute(),
  datumBis: heute(),
}

// ---------------------------------------------------------------------------
// Rechnungen (Ausgangs-/Eingangsrechnungen + Lieferscheine)
// ---------------------------------------------------------------------------

export type RechnungenFilterModus = 'monat' | 'datum' | 'zeitraum' | 'alle' | 'jahr'

export interface RechnungenFilterState {
  modus:    RechnungenFilterModus
  monat:    string
  datum:    string
  datumVon: string
  datumBis: string
}

export const rechnungenFilter: RechnungenFilterState = {
  modus:    'monat',
  monat:    aktuellerMonat(),
  datum:    heute(),
  datumVon: heute(),
  datumBis: heute(),
}

export const lieferscheinFilter: RechnungenFilterState = {
  modus:    'monat',
  monat:    aktuellerMonat(),
  datum:    heute(),
  datumVon: heute(),
  datumBis: heute(),
}

// ---------------------------------------------------------------------------
// Bank-Import
// ---------------------------------------------------------------------------

export type BankImportFilterModus = 'monat' | 'datum' | 'zeitraum' | 'alle' | 'jahr'

export interface BankImportFilterState {
  modus:    BankImportFilterModus
  monat:    string
  datum:    string
  datumVon: string
  datumBis: string
}

// Voreinstellung "alle" – entspricht dem bisherigen Standardverhalten (kein Datumsfilter).
export const bankImportFilter: BankImportFilterState = {
  modus:    'alle',
  monat:    aktuellerMonat(),
  datum:    heute(),
  datumVon: heute(),
  datumBis: heute(),
}
