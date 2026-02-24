import { useEffect, useState } from 'react'
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

// Scheine in Euro, Münzen in Cent
const SCHEINE = [500, 200, 100, 50, 20, 10, 5]
const MUENZEN_CENT = [200, 100, 50, 20, 10, 5, 2, 1]

function berechneSumme(scheine: Record<number, number>, muenzen: Record<number, number>): number {
  const s = SCHEINE.reduce((acc, wert) => acc + wert * (scheine[wert] || 0), 0)
  const m = MUENZEN_CENT.reduce((acc, cent) => acc + cent * (muenzen[cent] || 0), 0)
  return s + m / 100
}

interface Props {
  onClose: () => void
  onSuccess: () => void
  datum?: string
}

function heute(): string {
  return new Date().toISOString().slice(0, 10)
}

function formatEuro(val: string | number): string {
  const n = typeof val === 'string' ? parseFloat(val) : val
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n)
}

function muenzLabel(cent: number): string {
  return formatEuro(cent / 100)
}

export function TagesabschlussDialog({ onClose, onSuccess, datum: datumProp }: Props) {
  const qc = useQueryClient()
  const datum = datumProp ?? heute()

  const [scheine, setScheine] = useState<Record<number, number>>(
    Object.fromEntries(SCHEINE.map((s) => [s, 0])) as Record<number, number>,
  )
  const [muenzen, setMuenzen] = useState<Record<number, number>>(
    Object.fromEntries(MUENZEN_CENT.map((m) => [m, 0])) as Record<number, number>,
  )

  const zaehlsumme = berechneSumme(scheine, muenzen)
  const hatZaehlung = zaehlsumme > 0

  const { data: vorschau, isLoading } = useQuery({
    queryKey: ['tagesabschluss-vorschau', datum],
    queryFn: () => getTagesabschlussVorschau(datum),
  })

  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { ist_endbestand: '', differenz_begruendung: '', differenz_buchungsart: '' },
  })

  // Zählsumme automatisch in ist_endbestand übernehmen
  useEffect(() => {
    if (hatZaehlung) {
      setValue('ist_endbestand', zaehlsumme.toFixed(2))
    }
  }, [zaehlsumme, hatZaehlung, setValue])

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
    const zaehlungJson = hatZaehlung
      ? JSON.stringify({ scheine, muenzen_cent: muenzen })
      : undefined
    mutation.mutate({
      datum,
      ist_endbestand: values.ist_endbestand,
      zaehlung_json: zaehlungJson,
      differenz_begruendung: values.differenz_begruendung || undefined,
      differenz_buchungsart: values.differenz_buchungsart || undefined,
    })
  }

  function setSchein(wert: number, anzahl: number) {
    setScheine((prev) => ({ ...prev, [wert]: Math.max(0, anzahl) }))
  }

  function setMuenze(cent: number, anzahl: number) {
    setMuenzen((prev) => ({ ...prev, [cent]: Math.max(0, anzahl) }))
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] flex flex-col">

        {/* Header */}
        <div className="px-6 pt-6 pb-4 shrink-0">
          <h2 className="text-lg font-bold text-slate-800 mb-0.5">Tagesabschluss</h2>
          <p className="text-sm text-slate-500">{datum.split('-').reverse().join('.')}</p>
        </div>

        {/* Scrollbarer Inhalt */}
        <div className="overflow-y-auto flex-1 px-6">
          {isLoading ? (
            <p className="text-slate-400 text-sm pb-4">Lade Vorschau…</p>
          ) : vorschau ? (
            <form id="tagesabschluss-form" onSubmit={handleSubmit(onSubmit)} className="space-y-5 pb-4">

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

              {/* Zählprotokoll */}
              <div>
                <h3 className="text-sm font-semibold text-slate-700 mb-2">Zählprotokoll</h3>
                <div className="border border-slate-200 rounded-lg overflow-hidden text-sm">

                  {/* Spalten-Header */}
                  <div className="grid grid-cols-[1fr_72px_88px] px-3 py-1.5 bg-slate-100 text-xs font-medium text-slate-500 border-b border-slate-200">
                    <span>Denomination</span>
                    <span className="text-right">Anzahl</span>
                    <span className="text-right">Betrag</span>
                  </div>

                  {/* Scheine */}
                  <div className="px-3 py-1 bg-slate-50 text-xs font-medium text-slate-400 border-b border-slate-100">
                    Scheine
                  </div>
                  <div className="divide-y divide-slate-100">
                    {SCHEINE.map((wert) => {
                      const betrag = wert * (scheine[wert] || 0)
                      return (
                        <div key={wert} className="grid grid-cols-[1fr_72px_88px] items-center px-3 py-1.5 gap-2">
                          <span className="text-slate-700">{wert},00 €</span>
                          <input
                            type="number"
                            min="0"
                            value={scheine[wert] || ''}
                            onChange={(e) => setSchein(wert, parseInt(e.target.value) || 0)}
                            placeholder="0"
                            className="border border-slate-300 rounded px-2 py-1 text-xs text-right w-full focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                          <span className="text-right text-xs text-slate-500">
                            {betrag > 0 ? formatEuro(betrag) : '—'}
                          </span>
                        </div>
                      )
                    })}
                  </div>

                  {/* Münzen */}
                  <div className="px-3 py-1 bg-slate-50 text-xs font-medium text-slate-400 border-y border-slate-100">
                    Münzen
                  </div>
                  <div className="divide-y divide-slate-100">
                    {MUENZEN_CENT.map((cent) => {
                      const betrag = (cent / 100) * (muenzen[cent] || 0)
                      return (
                        <div key={cent} className="grid grid-cols-[1fr_72px_88px] items-center px-3 py-1.5 gap-2">
                          <span className="text-slate-700">{muenzLabel(cent)}</span>
                          <input
                            type="number"
                            min="0"
                            value={muenzen[cent] || ''}
                            onChange={(e) => setMuenze(cent, parseInt(e.target.value) || 0)}
                            placeholder="0"
                            className="border border-slate-300 rounded px-2 py-1 text-xs text-right w-full focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                          <span className="text-right text-xs text-slate-500">
                            {betrag > 0 ? formatEuro(betrag) : '—'}
                          </span>
                        </div>
                      )
                    })}
                  </div>

                  {/* Gesamt-Zeile */}
                  <div className="grid grid-cols-[1fr_72px_88px] items-center px-3 py-2 gap-2 bg-slate-50 border-t border-slate-200">
                    <span className="text-xs font-semibold text-slate-600 col-span-2">Summe Zählung</span>
                    <span className={`text-right text-sm font-bold ${hatZaehlung ? 'text-blue-700' : 'text-slate-300'}`}>
                      {formatEuro(zaehlsumme)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Ist-Endbestand */}
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">
                  Ist-Endbestand (gezählt) €
                  {hatZaehlung && (
                    <span className="ml-1.5 text-blue-500 font-normal">— aus Zählprotokoll übernommen</span>
                  )}
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

              {/* Differenz */}
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
                    <select
                      {...register('differenz_buchungsart')}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
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
            </form>
          ) : (
            <p className="text-red-500 text-sm pb-4">Fehler beim Laden der Vorschau.</p>
          )}
        </div>

        {/* Footer */}
        {vorschau && (
          <div className="px-6 py-4 shrink-0 border-t border-slate-100 flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-slate-300 text-slate-600 rounded-lg py-2 text-sm hover:bg-slate-50"
            >
              Abbrechen
            </button>
            <button
              type="submit"
              form="tagesabschluss-form"
              disabled={mutation.isPending}
              className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {mutation.isPending ? 'Speichert…' : 'Abschluss buchen'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
