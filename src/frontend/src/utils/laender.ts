/**
 * EU-Mitgliedstaaten (2026, 27 Länder) + Schweiz für Land-Dropdowns.
 * Reihenfolge: Deutschland zuerst, dann alphabetisch nach deutschem Namen.
 */

export const LAENDER: { code: string; name: string }[] = [
  { code: 'DE', name: 'Deutschland' },
  { code: 'AT', name: 'Österreich' },
  { code: 'BE', name: 'Belgien' },
  { code: 'BG', name: 'Bulgarien' },
  { code: 'CH', name: 'Schweiz' },
  { code: 'CY', name: 'Zypern' },
  { code: 'CZ', name: 'Tschechien' },
  { code: 'DK', name: 'Dänemark' },
  { code: 'EE', name: 'Estland' },
  { code: 'ES', name: 'Spanien' },
  { code: 'FI', name: 'Finnland' },
  { code: 'FR', name: 'Frankreich' },
  { code: 'GR', name: 'Griechenland' },
  { code: 'HR', name: 'Kroatien' },
  { code: 'HU', name: 'Ungarn' },
  { code: 'IE', name: 'Irland' },
  { code: 'IT', name: 'Italien' },
  { code: 'LT', name: 'Litauen' },
  { code: 'LU', name: 'Luxemburg' },
  { code: 'LV', name: 'Lettland' },
  { code: 'MT', name: 'Malta' },
  { code: 'NL', name: 'Niederlande' },
  { code: 'PL', name: 'Polen' },
  { code: 'PT', name: 'Portugal' },
  { code: 'RO', name: 'Rumänien' },
  { code: 'SE', name: 'Schweden' },
  { code: 'SI', name: 'Slowenien' },
  { code: 'SK', name: 'Slowakei' },
]

export const EU_LAENDER_CODES = new Set(
  LAENDER.filter((l) => l.code !== 'CH').map((l) => l.code)
)

export function istEuLand(code: string | null | undefined): boolean {
  return !!code && EU_LAENDER_CODES.has(code.toUpperCase())
}
