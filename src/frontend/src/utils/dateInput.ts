import type { ChangeEvent } from 'react'

/**
 * Schutz-Handler für <input type="date"> gegen WebView2-Black-Screen-Bug.
 *
 * WebView2 (Tauri/Windows) feuert onChange mit value="" sobald ein Datum
 * während der Eingabe kurzzeitig ungültig ist (z.B. Tag=0 beim Tippen oder
 * beim Löschen von Ziffern). Wird dieser leere Wert in den React-State
 * übernommen und das Controlled-Input mit value="" neu gerendert,
 * zeigt WebView2 einen Black Screen / leere Seite.
 *
 * Lösung: Leere Werte werden in onChange ignoriert – der State bleibt beim
 * letzten gültigen Datum. Explizites Löschen per programmatischem setState('')
 * (z.B. über einen ×-Button oder Toggle-Logik) funktioniert weiterhin.
 *
 * Linux/macOS-Verhalten: Kein Absturz, aber gleiche Absicherung für
 * konsistentes Verhalten über alle Plattformen hinweg.
 *
 * @param setter - React-setState-Funktion für den Datums-String-State
 *
 * @example
 * // Einfaches Datum:
 * <input type="date" value={datum} onChange={guardedDateChange(setDatum)} />
 *
 * // Compound-Handler (mehrere State-Updates):
 * <input type="date" value={leistungVon}
 *   onChange={(e) => {
 *     if (e.target.value) {
 *       setLeistungVon(e.target.value)
 *       setLeistungManuell(true)
 *     }
 *   }}
 * />
 */
export function guardedDateChange(
  setter: (value: string) => void
): (e: ChangeEvent<HTMLInputElement>) => void {
  return (e) => {
    if (e.target.value) setter(e.target.value)
  }
}
