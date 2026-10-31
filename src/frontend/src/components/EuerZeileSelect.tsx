import { useQuery } from '@tanstack/react-query'
import { getEUERZeilen } from '../api/client'

const ABSCHNITT_LABEL: Record<string, string> = {
  A: 'Betriebseinnahmen',
  B: 'Betriebsausgaben',
  H: 'Entnahmen / Einlagen',
}

// Issue #470: Auswahl statt freier Zahl - eine unbekannte Zeile fiele in der EÜR still aus
// der Summe. Nummerierung nach Vordruck 2025 (Basis), die Auswertung rechnet je Jahr um.
export function EuerZeileSelect({
  value,
  onChange,
  className,
  kompakt = false,
}: {
  value: number | null | undefined
  onChange: (v: number | null) => void
  className?: string
  kompakt?: boolean
}) {
  const { data: zeilen = [] } = useQuery({
    queryKey: ['euer-zeilen'],
    queryFn: getEUERZeilen,
    staleTime: Infinity,
  })
  const bekannt = value == null || zeilen.length === 0 || zeilen.some(z => z.zeile === value)
  const gruppen = ['A', 'B', 'H'].map(ab => [ab, zeilen.filter(z => z.abschnitt === ab)] as const)

  return (
    <select
      className={className}
      value={value ?? ''}
      onChange={e => onChange(e.target.value ? Number(e.target.value) : null)}
      aria-label="EÜR-Zeile"
    >
      <option value="">{kompakt ? '—' : 'keine'}</option>
      {!bekannt && <option value={value!}>Zeile {value} (unbekannt)</option>}
      {gruppen.map(([ab, liste]) => liste.length > 0 && (
        <optgroup key={ab} label={ABSCHNITT_LABEL[ab]}>
          {liste.map(z => (
            <option key={z.zeile} value={z.zeile}>
              {z.zeile} – {z.bezeichnung}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  )
}
