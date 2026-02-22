import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getTagesabschlussVorschau, createTagesabschluss } from '../../api/client'

const schema = z.object({
  ist_endbestand: z.string().refine((v) => !isNaN(parseFloat(v)) && parseFloat(v) >= 0, 'Betrag muss >= 0 sein'),
  differenz_begruendung: z.string().optional(),
  differenz_buchungsart: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

interface Props {
  onClose: () => void
  onSuccess: () => void
}

function heute(): string {
  return new Date().toISOString().slice(0, 10)
}

function formatEuro(val: string | number): string {
  const n = typeof val === 'string' ? parseFloat(val) : val
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n)
}

export function TagesabschlussDialog({ onClose, onSuccess }: Props) {
  const qc = useQueryClient()
  const datum = heute()

  const { data: vorschau, isLoading } = useQuery({
    queryKey: ['tagesabschluss-vorschau', datum],
    queryFn: () => getTagesabschlussVorschau(datum),
  })

  const { register, handleSubmit, watch, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { ist_endbestand: '', differenz_begruendung: '', differenz_buchungsart: '' },
  })

  const istEndbestandStr = watch('ist_endbestand')
  const istEndbestand = parseFloat(istEndbestandStr) || 0
  const sollEndbestand = vorschau ? parseFloat(vorschau.soll_endbestand) : 0
  const differenz = istEndbestand - sollEndbestand
  const hatDifferenz = Math.abs(differenz) > 0.005

  const mutation = useMutation({
    mutationFn: createTagesabschluss,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kassenbuch'] })
      qc.invalidateQueries({ queryKey: ['tagesabschluss'] })
      onSuccess()
    },
  })

  function onSubmit(values: FormValues) {
    mutation.mutate({
      datum,
      ist_endbestand: values.ist_endbestand,
      differenz_begruendung: values.differenz_begruendung || undefined,
      differenz_buchungsart: values.differenz_buchungsart || undefined,
    })
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-bold text-slate-800 mb-1">Tagesabschluss</h2>
        <p className="text-sm text-slate-500 mb-4">{datum}</p>

        {isLoading ? (
          <p className="text-slate-400 text-sm">Lade Vorschau…</p>
        ) : vorschau ? (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Vorschau-Kacheln */}
            <div className="bg-slate-50 rounded-lg p-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="block text-xs text-slate-400 mb-0.5">Anfangsbestand</span>
                <span className="font-medium">{formatEuro(vorschau.anfangsbestand)}</span>
              </div>
              <div>
                <span className="block text-xs text-slate-400 mb-0.5">Buchungen</span>
                <span className="font-medium">{vorschau.kassenbewegungen_anzahl}</span>
              </div>
              <div>
                <span className="block text-xs text-slate-400 mb-0.5">Einnahmen (Bar)</span>
                <span className="font-medium text-green-600">{formatEuro(vorschau.einnahmen_bar)}</span>
              </div>
              <div>
                <span className="block text-xs text-slate-400 mb-0.5">Ausgaben (Bar)</span>
                <span className="font-medium text-red-600">{formatEuro(vorschau.ausgaben_bar)}</span>
              </div>
              <div className="col-span-2 pt-2 border-t border-slate-200">
                <span className="block text-xs text-slate-400 mb-0.5">Soll-Endbestand</span>
                <span className="text-lg font-bold">{formatEuro(vorschau.soll_endbestand)}</span>
              </div>
            </div>

            {/* Ist-Endbestand */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Ist-Endbestand (gezählt) €
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                {...register('ist_endbestand')}
                placeholder="0,00"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {errors.ist_endbestand && (
                <p className="text-red-500 text-xs mt-0.5">{errors.ist_endbestand.message}</p>
              )}
            </div>

            {/* Differenz-Anzeige */}
            {istEndbestandStr && (
              <div className={`rounded-lg p-3 text-sm ${hatDifferenz ? 'bg-amber-50 text-amber-700' : 'bg-green-50 text-green-700'}`}>
                <span className="font-medium">Differenz: {formatEuro(differenz)}</span>
                {!hatDifferenz && <span className="ml-2 text-xs">✓ Kasse stimmt</span>}
              </div>
            )}

            {/* Begründung bei Differenz */}
            {hatDifferenz && (
              <>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Buchungsart der Differenz</label>
                  <select {...register('differenz_buchungsart')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option value="">— wählen —</option>
                    <option value="Privatentnahme">Privatentnahme</option>
                    <option value="Aufwand">Aufwand</option>
                    <option value="Protokoll">Protokoll (Zählfehler)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Begründung</label>
                  <input
                    type="text"
                    {...register('differenz_begruendung')}
                    placeholder="Kurze Erläuterung…"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </>
            )}

            {mutation.isError && (
              <p className="text-red-600 text-sm">{(mutation.error as Error).message}</p>
            )}

            <div className="flex gap-3 pt-2">
              <button type="button" onClick={onClose} className="flex-1 border border-slate-300 text-slate-600 rounded-lg py-2 text-sm hover:bg-slate-50">
                Abbrechen
              </button>
              <button type="submit" disabled={mutation.isPending} className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
                {mutation.isPending ? 'Speichert…' : 'Abschluss buchen'}
              </button>
            </div>
          </form>
        ) : (
          <p className="text-red-500 text-sm">Fehler beim Laden der Vorschau.</p>
        )}
      </div>
    </div>
  )
}
