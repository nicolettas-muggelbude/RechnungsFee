import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createKassenbuchEintrag, getKategorien, getKunden } from '../../api/client'

const schema = z.object({
  datum: z.string().min(1, 'Datum erforderlich'),
  beschreibung: z.string().min(1, 'Beschreibung erforderlich'),
  art: z.enum(['Einnahme', 'Ausgabe']),
  brutto_betrag: z.string().refine((v) => !isNaN(parseFloat(v)) && parseFloat(v) > 0, 'Betrag muss positiv sein'),
  ust_satz: z.string(),
  zahlungsart: z.enum(['Bar', 'Karte', 'Bank', 'PayPal']),
  kategorie_id: z.string().optional(),
  kunde_id: z.string().optional(),
  vorsteuerabzug: z.boolean().optional(),
})

type FormValues = z.infer<typeof schema>

interface Props {
  onClose: () => void
  onSuccess: () => void
}

function heute(): string {
  return new Date().toISOString().slice(0, 10)
}

export function BuchungForm({ onClose, onSuccess }: Props) {
  const qc = useQueryClient()
  const { data: kategorien } = useQuery({ queryKey: ['kategorien'], queryFn: getKategorien })
  const { data: kunden } = useQuery({ queryKey: ['kunden'], queryFn: getKunden })

  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      datum: heute(),
      art: 'Einnahme',
      zahlungsart: 'Bar',
      ust_satz: '0',
      vorsteuerabzug: false,
    },
  })

  const art = watch('art')
  const bruttoStr = watch('brutto_betrag')
  const ustSatzStr = watch('ust_satz')
  const kategorie_id = watch('kategorie_id')

  // USt-Satz aus Kategorie vorbelegen
  useEffect(() => {
    if (!kategorie_id || !kategorien) return
    const kat = kategorien.find((k) => String(k.id) === kategorie_id)
    if (kat) {
      // vorsteuer_prozent ist 100 = kein USt, 19 = 19% USt
      const satz = parseFloat(kat.vorsteuer_prozent) === 100 ? '19' : '0'
      setValue('ust_satz', satz)
    }
  }, [kategorie_id, kategorien, setValue])

  // Live USt-Berechnung
  const brutto = parseFloat(bruttoStr) || 0
  const ustSatz = parseFloat(ustSatzStr) || 0
  const netto = ustSatz > 0 ? (brutto * 100) / (100 + ustSatz) : brutto
  const ustBetrag = brutto - netto

  const mutation = useMutation({
    mutationFn: createKassenbuchEintrag,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kassenbuch'] })
      qc.invalidateQueries({ queryKey: ['monats-uebersicht'] })
      onSuccess()
    },
  })

  function onSubmit(values: FormValues) {
    mutation.mutate({
      datum: values.datum,
      beschreibung: values.beschreibung,
      art: values.art,
      brutto_betrag: values.brutto_betrag,
      ust_satz: values.ust_satz,
      zahlungsart: values.zahlungsart,
      kategorie_id: values.kategorie_id ? Number(values.kategorie_id) : undefined,
      kunde_id: values.kunde_id ? Number(values.kunde_id) : undefined,
      vorsteuerabzug: values.vorsteuerabzug,
    })
  }

  const kategorienGefiltert = (kategorien ?? []).filter((k) =>
    art === 'Einnahme' ? k.kontenart === 'Erlös' : k.kontenart === 'Aufwand'
  )

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
        <h2 className="text-lg font-bold text-slate-800 mb-4">Neue Buchung</h2>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Art */}
          <div className="flex gap-3">
            {(['Einnahme', 'Ausgabe'] as const).map((a) => (
              <label key={a} className="flex-1 cursor-pointer">
                <input type="radio" value={a} {...register('art')} className="sr-only" />
                <div className={`text-center py-2 rounded-lg border-2 font-medium text-sm transition-colors ${
                  art === a
                    ? a === 'Einnahme' ? 'border-green-500 bg-green-50 text-green-700' : 'border-red-500 bg-red-50 text-red-700'
                    : 'border-slate-200 text-slate-500 hover:border-slate-300'
                }`}>{a}</div>
              </label>
            ))}
          </div>

          {/* Datum + Zahlungsart */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Datum</label>
              <input type="date" {...register('datum')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              {errors.datum && <p className="text-red-500 text-xs mt-0.5">{errors.datum.message}</p>}
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Zahlungsart</label>
              <select {...register('zahlungsart')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                {['Bar', 'Karte', 'Bank', 'PayPal'].map((z) => <option key={z}>{z}</option>)}
              </select>
            </div>
          </div>

          {/* Beschreibung */}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Beschreibung</label>
            <input type="text" {...register('beschreibung')} placeholder="z.B. Büromaterial" className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            {errors.beschreibung && <p className="text-red-500 text-xs mt-0.5">{errors.beschreibung.message}</p>}
          </div>

          {/* Kategorie */}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Kategorie</label>
            <select {...register('kategorie_id')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="">— keine —</option>
              {kategorienGefiltert.map((k) => (
                <option key={k.id} value={k.id}>{k.name}</option>
              ))}
            </select>
          </div>

          {/* Kunde (optional) */}
          {art === 'Einnahme' && (
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Kunde <span className="text-slate-400 font-normal">(optional)</span></label>
              <select {...register('kunde_id')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="">— kein Kunde —</option>
                {(kunden ?? []).filter((k) => k.aktiv !== false).map((k) => {
                  const name = [k.firmenname, k.vorname, k.nachname].filter(Boolean).join(' ')
                  return <option key={k.id} value={k.id}>{name}{k.kundennummer ? ` (${k.kundennummer})` : ''}</option>
                })}
              </select>
            </div>
          )}

          {/* Betrag + USt */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Brutto-Betrag (€)</label>
              <input type="number" step="0.01" min="0.01" {...register('brutto_betrag')} placeholder="0,00" className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              {errors.brutto_betrag && <p className="text-red-500 text-xs mt-0.5">{errors.brutto_betrag.message}</p>}
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">USt-Satz (%)</label>
              <select {...register('ust_satz')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="0">0 %</option>
                <option value="7">7 %</option>
                <option value="19">19 %</option>
              </select>
            </div>
          </div>

          {/* USt-Vorschau */}
          {ustSatz > 0 && brutto > 0 && (
            <div className="bg-slate-50 rounded-lg p-3 text-xs text-slate-600 grid grid-cols-3 gap-2">
              <div><span className="block text-slate-400">Netto</span>{netto.toFixed(2)} €</div>
              <div><span className="block text-slate-400">USt {ustSatz} %</span>{ustBetrag.toFixed(2)} €</div>
              <div><span className="block text-slate-400">Brutto</span>{brutto.toFixed(2)} €</div>
            </div>
          )}

          {/* Vorsteuerabzug */}
          {art === 'Ausgabe' && (
            <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
              <input type="checkbox" {...register('vorsteuerabzug')} className="rounded" />
              Vorsteuerabzug geltend machen
            </label>
          )}

          {mutation.isError && (
            <p className="text-red-600 text-sm">{(mutation.error as Error).message}</p>
          )}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 border border-slate-300 text-slate-600 rounded-lg py-2 text-sm hover:bg-slate-50">
              Abbrechen
            </button>
            <button type="submit" disabled={mutation.isPending} className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
              {mutation.isPending ? 'Speichert…' : 'Buchung speichern'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
