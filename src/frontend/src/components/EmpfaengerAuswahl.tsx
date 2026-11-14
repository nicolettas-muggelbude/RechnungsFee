import { useEffect, useId } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getLieferadressen } from '../api/client'

/**
 * Issue #495: Auswahl einer weiteren Adresse des Kunden (Filiale, Standort, Lieferadresse aus dem
 * Kundenstamm) für eine Adressrolle des Dokuments:
 *   - Empfänger (Angebot), Rechnungsadresse (Auftrag, Proforma, Rechnung) → empfaenger_adresse_id
 *   - Lieferadresse (Auftrag, Proforma, Lieferschein, Rechnung)          → lieferadresse_id
 * Erscheint nur, wenn der gewählte Kunde weitere Adressen hat.
 *
 * `value`: '' = Stammanschrift des Kunden bzw. keine Lieferadresse, sonst die ID als String.
 */
export function KundenadresseAuswahl({ kundeId, value, onChange, label, leerText, hinweis, className }: {
  kundeId: number | null
  value: string
  onChange: (v: string) => void
  label: string
  leerText: string
  hinweis?: string
  className?: string
}) {
  const id = useId()
  const { data: adressen = [], isSuccess } = useQuery({
    queryKey: ['lieferadressen', kundeId],
    queryFn: () => getLieferadressen(kundeId!),
    enabled: !!kundeId,
  })

  // Adresse gehört nicht (mehr) zum Kunden, z. B. nach einem Kundenwechsel → zurücksetzen
  useEffect(() => {
    if (!value) return
    if (!kundeId || (isSuccess && !adressen.some(a => String(a.id) === value))) onChange('')
  }, [kundeId, isSuccess, adressen, value, onChange])

  if (!kundeId || adressen.length === 0) return null

  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
        {label}
      </label>
      <select id={id} value={value} onChange={e => onChange(e.target.value)} className={className}>
        <option value="">{leerText}</option>
        {adressen.map(a => (
          <option key={a.id} value={String(a.id)}>
            {a.bezeichnung || 'Adresse'}{a.ist_standard ? ' ★' : ''} – {[a.strasse, a.hausnummer, a.plz, a.ort].filter(Boolean).join(' ')}
          </option>
        ))}
      </select>
      {hinweis && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{hinweis}</p>}
    </div>
  )
}

/** Angebot: Empfänger im Adressfeld. */
export function EmpfaengerAuswahl(props: Omit<Parameters<typeof KundenadresseAuswahl>[0], 'label' | 'leerText' | 'hinweis'>) {
  return (
    <KundenadresseAuswahl
      {...props}
      label="Empfänger"
      leerText="Kunde (Stammanschrift)"
      hinweis="Kunde oder eine seiner Filialen. Die Rechnungsadresse lässt sich später in Auftrag oder Rechnung ändern."
    />
  )
}

/** Auftrag, Proforma, Rechnung: Rechnungsadresse im Adressfeld. */
export function RechnungsadresseAuswahl(props: Omit<Parameters<typeof KundenadresseAuswahl>[0], 'label' | 'leerText' | 'hinweis'>) {
  return <KundenadresseAuswahl {...props} label="Rechnungsadresse" leerText="Kunde (Stammanschrift)" />
}

/** Auftrag, Proforma, Lieferschein, Rechnung: Lieferadresse. */
export function LieferadresseAuswahl(props: Omit<Parameters<typeof KundenadresseAuswahl>[0], 'label' | 'leerText' | 'hinweis'> & { leerText?: string }) {
  return <KundenadresseAuswahl {...props} label="Lieferadresse" leerText={props.leerText ?? 'Keine abweichende Lieferadresse'} />
}
