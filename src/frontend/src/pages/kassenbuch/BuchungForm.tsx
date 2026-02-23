import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createKassenbuchEintrag, getKategorien, getKunden, getUnternehmen } from '../../api/client'

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
  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen })

  const istKleinunternehmer = unternehmen?.ist_kleinunternehmer ?? false

  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      datum: heute(),
      art: 'Einnahme',
      zahlungsart: 'Bar',
      ust_satz: '0',
      vorsteuerabzug: true,
    },
  })

  const art = watch('art')
  const bruttoStr = watch('brutto_betrag')
  const ustSatzStr = watch('ust_satz')
  const kategorie_id = watch('kategorie_id')

  // Standardkategorie vorwählen sobald Kategorien geladen oder Art / Unternehmensstatus wechselt
  useEffect(() => {
    if (!kategorien) return
    if (art === 'Einnahme') {
      const defaultName = istKleinunternehmer ? 'Kleinunternehmer-Einnahmen' : 'Betriebseinnahmen'
      const kat = kategorien.find((k) => k.name === defaultName)
      if (kat) setValue('kategorie_id', String(kat.id))
    } else {
      setValue('kategorie_id', '')
    }
  }, [kategorien, art, istKleinunternehmer, setValue])

  // USt-Satz und Vorsteuerabzug aus Kategorie vorbelegen
  useEffect(() => {
    if (!kategorie_id || !kategorien) return
    const kat = kategorien.find((k) => String(k.id) === kategorie_id)
    if (!kat) return
    setValue('ust_satz', istKleinunternehmer ? '0' : String(kat.ust_satz_standard))
    if (!istKleinunternehmer) {
      setValue('vorsteuerabzug', parseFloat(kat.vorsteuer_prozent) > 0)
    }
  }, [kategorie_id, kategorien, setValue, istKleinunternehmer])

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

  const alle = kategorien ?? []
  // Einnahmen: Kleinunternehmer sieht nur "Kleinunternehmer-Einnahmen", sonst alles außer dieser
  const erloeseKat = alle.filter((k) =>
    k.kontenart === 'Erlös' &&
    (istKleinunternehmer ? k.name === 'Kleinunternehmer-Einnahmen' : k.name !== 'Kleinunternehmer-Einnahmen')
  )
  const einlageKat  = alle.filter((k) => k.kontenart === 'Privat' && k.name === 'Privateinlage')
  // Ausgaben
  const aufwandKat  = alle.filter((k) => k.kontenart === 'Aufwand')
  const anlageKat   = alle.filter((k) => k.kontenart === 'Anlage')
  const entnahmeKat = alle.filter((k) => k.kontenart === 'Privat' && k.name === 'Privatentnahme')

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
        <h2 className="text-lg font-bold text-slate-800 mb-4">Neue Buchung</h2>

        {/* Kleinunternehmer-Hinweis */}
        {istKleinunternehmer && (
          <div className="mb-4 flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs text-amber-800">
            <span className="mt-0.5">ℹ️</span>
            <span><strong>Kleinunternehmer §19 UStG</strong> – Keine Umsatzsteuer ausgewiesen. USt-Satz ist gesperrt.</span>
          </div>
        )}

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
              {art === 'Einnahme' ? (
                <>
                  <optgroup label="Erlöse">
                    {erloeseKat.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
                  </optgroup>
                  {einlageKat.length > 0 && (
                    <optgroup label="Sonstiges">
                      {einlageKat.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
                    </optgroup>
                  )}
                </>
              ) : (
                <>
                  <optgroup label="Betriebsausgaben">
                    {aufwandKat.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
                  </optgroup>
                  {anlageKat.length > 0 && (
                    <optgroup label="Investitionen">
                      {anlageKat.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
                    </optgroup>
                  )}
                  {entnahmeKat.length > 0 && (
                    <optgroup label="Sonstiges">
                      {entnahmeKat.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
                    </optgroup>
                  )}
                </>
              )}
            </select>
          </div>

          {/* Kunde (optional, nur bei Einnahmen) */}
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
              <label className="block text-xs font-medium text-slate-600 mb-1">
                USt-Satz (%)
                {!istKleinunternehmer && unternehmen?.taetigkeitsart === 'freiberuflich' && (
                  <span className="ml-1 text-slate-400 font-normal">(7 % für Autoren/Heilberufe etc.)</span>
                )}
              </label>
              <select
                {...register('ust_satz')}
                disabled={istKleinunternehmer}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100 disabled:text-slate-400 disabled:cursor-not-allowed"
              >
                <option value="0">{istKleinunternehmer ? '0 % (§19 UStG)' : '0 %'}</option>
                {!istKleinunternehmer && <option value="7">7 %</option>}
                {!istKleinunternehmer && <option value="19">19 %</option>}
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

          {/* Vorsteuerabzug – nur für Ausgaben von Nicht-Kleinunternehmern */}
          {art === 'Ausgabe' && !istKleinunternehmer && (
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
