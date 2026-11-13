// Issue #485/#531: async Nachfrage „Rechnungsdatum auf heute?“ beim Finalisieren
// (Dialog: components/RechnungsdatumDialog.tsx).
import { useCallback, useState, type ReactElement } from 'react'
import { RechnungsdatumDialog, type DatumEntscheidung, type Frage } from '../components/RechnungsdatumDialog'

function heuteIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/**
 * Liefert eine async Frage-Funktion und das zugehörige Dialog-Element (im JSX rendern).
 * Ergebnis: true = auf heute setzen, false = beibehalten, null = Finalisieren abbrechen.
 * Liegt das Datum nicht in der Vergangenheit, wird nicht gefragt (false).
 */
export function useRechnungsdatumFrage(): [
  (datum: string, leistungBis?: string | null) => Promise<DatumEntscheidung>,
  ReactElement | null,
] {
  const [frage, setFrage] = useState<Frage | null>(null)

  const frageDatum = useCallback((datum: string, leistungBis?: string | null) => {
    const heute = heuteIso()
    if (!datum || datum >= heute) return Promise.resolve<DatumEntscheidung>(false)
    return new Promise<DatumEntscheidung>((resolve) => setFrage({ datum, heute, leistungBis, resolve }))
  }, [])

  const element = frage ? (
    <RechnungsdatumDialog frage={frage} onAntwort={(v) => { frage.resolve(v); setFrage(null) }} />
  ) : null

  return [frageDatum, element]
}
