import { useEffect, useId } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getLieferadressen } from '../api/client'

/**
 * Issue #495: Empfänger im Adressfeld von Angebot, Auftrag, Proforma und Lieferschein –
 * der Kunde selbst oder einer seiner Standorte (Lieferadressen aus dem Kundenstamm).
 * Erscheint nur, wenn der gewählte Kunde Lieferadressen hat. Die Rechnung geht immer an
 * den Kunden.
 *
 * `value`: '' = Kunde selbst, sonst die ID der Lieferadresse als String.
 */
export function EmpfaengerAuswahl({ kundeId, value, onChange, className }: {
  kundeId: number | null
  value: string
  onChange: (v: string) => void
  className?: string
}) {
  const id = useId()
  const { data: adressen = [], isSuccess } = useQuery({
    queryKey: ['lieferadressen', kundeId],
    queryFn: () => getLieferadressen(kundeId!),
    enabled: !!kundeId,
  })

  // Standort gehört nicht (mehr) zum Kunden, z. B. nach einem Kundenwechsel → zurück auf den Kunden
  useEffect(() => {
    if (!value) return
    if (!kundeId || (isSuccess && !adressen.some(a => String(a.id) === value))) onChange('')
  }, [kundeId, isSuccess, adressen, value, onChange])

  if (!kundeId || adressen.length === 0) return null

  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
        Empfänger (Adressfeld)
      </label>
      <select id={id} value={value} onChange={e => onChange(e.target.value)} className={className}>
        <option value="">Kunde (Rechnungsanschrift)</option>
        {adressen.map(a => (
          <option key={a.id} value={String(a.id)}>
            {a.bezeichnung || 'Lieferadresse'} – {[a.strasse, a.hausnummer, a.plz, a.ort].filter(Boolean).join(' ')}
          </option>
        ))}
      </select>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        Ein Standort aus den Lieferadressen des Kunden. Die Rechnung geht weiterhin an den Kunden.
      </p>
    </div>
  )
}
