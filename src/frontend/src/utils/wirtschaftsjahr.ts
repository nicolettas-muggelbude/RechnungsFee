/**
 * Gemeinsame Formatierung für das Wirtschaftsjahr-Label (Issue #404).
 * Bei Kalenderjahr (beginnMonat 1 oder nicht gesetzt) nur die Jahreszahl, bei abweichendem
 * Wirtschaftsjahr "2025/2026" (Jahr, in dem das WJ beginnt, / Jahr in dem es endet).
 */
export function formatWirtschaftsjahrLabel(jahr: number, beginnMonat?: number): string {
  if (!beginnMonat || beginnMonat === 1) return String(jahr)
  return `${jahr}/${jahr + 1}`
}
