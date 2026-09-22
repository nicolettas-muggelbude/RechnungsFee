/**
 * Länder für die Land-Dropdowns (Kunden, Lieferanten, eigenes Unternehmen).
 *
 * Enthalten sind die 27 EU-Mitgliedstaaten (2026) plus die Drittländer, die bisher
 * angefragt wurden. Ein weiteres Drittland braucht nur einen Eintrag in LAENDER_QUELLE -
 * die steuerliche Sonderbehandlung (nicht steuerbare Leistung nach §3a Abs. 2 UStG,
 * Ausfuhrlieferung nach §4 Nr. 1a UStG) hängt allein daran, dass sein Code nicht in
 * EU_LAENDER_CODES steht.
 *
 * Reihenfolge im Dropdown: Deutschland, Österreich, Schweiz zuerst (deckt den Großteil
 * der Fälle ab), darunter alle übrigen Länder alphabetisch nach deutschem Namen. Sortiert
 * wird zur Laufzeit - ein neuer Eintrag in LAENDER_QUELLE landet dadurch automatisch an
 * der richtigen Stelle, egal wo er eingefügt wurde.
 */

export type Land = { code: string; name: string }

/** ISO-Codes der 27 EU-Mitgliedstaaten (Stand 2026). Alles was hier nicht steht, gilt als
 * Drittland - diese Liste muss deshalb nur bei einem EU-Beitritt/-Austritt angefasst
 * werden, nicht bei jedem neuen Land im Dropdown. */
export const EU_LAENDER_CODES = new Set([
  'AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GR', 'HR', 'HU',
  'IE', 'IT', 'LT', 'LU', 'LV', 'MT', 'NL', 'PL', 'PT', 'RO', 'SE', 'SI', 'SK',
])

/** Codes, die im Dropdown in dieser Reihenfolge ganz oben stehen (Issue #350: die
 * Länderliste wächst auf Zuruf, der DACH-Raum soll trotzdem sofort greifbar bleiben). */
const BEVORZUGTE_CODES = ['DE', 'AT', 'CH']

const LAENDER_QUELLE: Land[] = [
  { code: 'AE', name: 'Vereinigte Arabische Emirate' },
  { code: 'AT', name: 'Österreich' },
  { code: 'BE', name: 'Belgien' },
  { code: 'BG', name: 'Bulgarien' },
  { code: 'CH', name: 'Schweiz' },
  { code: 'CN', name: 'China' },
  { code: 'CY', name: 'Zypern' },
  { code: 'CZ', name: 'Tschechien' },
  { code: 'DE', name: 'Deutschland' },
  { code: 'DK', name: 'Dänemark' },
  { code: 'EE', name: 'Estland' },
  { code: 'ES', name: 'Spanien' },
  { code: 'FI', name: 'Finnland' },
  { code: 'FR', name: 'Frankreich' },
  { code: 'GB', name: 'Vereinigtes Königreich' },
  { code: 'GR', name: 'Griechenland' },
  { code: 'HR', name: 'Kroatien' },
  { code: 'HU', name: 'Ungarn' },
  { code: 'IE', name: 'Irland' },
  { code: 'IN', name: 'Indien' },
  { code: 'IT', name: 'Italien' },
  { code: 'JP', name: 'Japan' },
  { code: 'LT', name: 'Litauen' },
  { code: 'LU', name: 'Luxemburg' },
  { code: 'LV', name: 'Lettland' },
  { code: 'MT', name: 'Malta' },
  { code: 'NL', name: 'Niederlande' },
  { code: 'NO', name: 'Norwegen' },
  { code: 'PL', name: 'Polen' },
  { code: 'PT', name: 'Portugal' },
  { code: 'RO', name: 'Rumänien' },
  { code: 'RS', name: 'Serbien' },
  { code: 'SE', name: 'Schweden' },
  { code: 'SG', name: 'Singapur' },
  { code: 'SI', name: 'Slowenien' },
  { code: 'SK', name: 'Slowakei' },
  { code: 'TR', name: 'Türkei' },
  { code: 'UA', name: 'Ukraine' },
  { code: 'US', name: 'USA' },
]

export const LAENDER: Land[] = [
  ...BEVORZUGTE_CODES.flatMap((code) => LAENDER_QUELLE.filter((l) => l.code === code)),
  ...LAENDER_QUELLE.filter((l) => !BEVORZUGTE_CODES.includes(l.code)).sort((a, b) =>
    a.name.localeCompare(b.name, 'de')
  ),
]

export function istEuLand(code: string | null | undefined): boolean {
  return !!code && EU_LAENDER_CODES.has(code.toUpperCase())
}

// USt-IdNr-Formatmuster je EU-Land (Issue #358) - Quelle: EU_LAENDER in
// database/seed.py (bewusst dupliziert, wie schon LAENDER selbst - Backend und Frontend
// teilen sich keine gemeinsame Konstanten-Datei). Griechenland nutzt fuer die USt-IdNr
// abweichend das Präfix "EL" statt des ISO-Landescodes "GR".
const UST_IDNR_FORMATE: Record<string, RegExp> = {
  AT: /^ATU[0-9]{8}$/,
  BE: /^BE[0-9]{10}$/,
  BG: /^BG[0-9]{9,10}$/,
  CY: /^CY[0-9]{8}[A-Z]$/,
  CZ: /^CZ[0-9]{8,10}$/,
  DE: /^DE[0-9]{9}$/,
  DK: /^DK[0-9]{8}$/,
  EE: /^EE[0-9]{9}$/,
  ES: /^ES[A-Z0-9][0-9]{7}[A-Z0-9]$/,
  FI: /^FI[0-9]{8}$/,
  FR: /^FR[A-Z0-9]{2}[0-9]{9}$/,
  GR: /^EL[0-9]{9}$/,
  HR: /^HR[0-9]{11}$/,
  HU: /^HU[0-9]{8}$/,
  IE: /^IE[0-9]{7}[A-Z]{1,2}$/,
  IT: /^IT[0-9]{11}$/,
  LT: /^LT([0-9]{9}|[0-9]{12})$/,
  LU: /^LU[0-9]{8}$/,
  LV: /^LV[0-9]{11}$/,
  MT: /^MT[0-9]{8}$/,
  NL: /^NL[0-9]{9}B[0-9]{2}$/,
  PL: /^PL[0-9]{10}$/,
  PT: /^PT[0-9]{9}$/,
  RO: /^RO[0-9]{2,10}$/,
  SE: /^SE[0-9]{12}$/,
  SI: /^SI[0-9]{8}$/,
  SK: /^SK[0-9]{10}$/,
}

/** Formale Prüfung der USt-IdNr für ein EU-Land (Issue #358). Liefert null wenn das Feld
 * leer ist oder für das Land kein Muster hinterlegt ist (z.B. Drittland) - in beiden Fällen
 * gibt es nichts zu warnen. Prüft nur die Form, nicht die tatsächliche Gültigkeit (dafür der
 * Link zur BZSt-eVatR-Abfrage). */
export function pruefeUstIdnrFormat(land: string | null | undefined, ustIdnr: string | null | undefined): boolean | null {
  if (!ustIdnr || !ustIdnr.trim()) return null
  const muster = land ? UST_IDNR_FORMATE[land.toUpperCase()] : undefined
  if (!muster) return null
  return muster.test(ustIdnr.trim().toUpperCase())
}
