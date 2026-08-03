import { useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { createKunde, type Kunde } from '../api/client'
import { LAENDER, istEuLand } from '../utils/laender'

const schema = z.object({
  firmenname: z.string().optional(),
  vorname: z.string().optional(),
  nachname: z.string().optional(),
  strasse: z.string().optional(),
  hausnummer: z.string().optional(),
  plz: z.string().optional(),
  ort: z.string().optional(),
  land: z.string().optional(),
  ust_idnr: z.string().optional(),
  email: z.string().email('Ungültige E-Mail').optional().or(z.literal('')),
  telefon: z.string().optional(),
  kundennummer: z.string().optional(),
  z_hd: z.string().optional(),
  notizen: z.string().optional(),
  ist_verein: z.boolean().optional(),
  ist_gemeinnuetzig: z.boolean().optional(),
  zugferd_aktiv: z.boolean().optional(),
  skonto_prozent: z.number().min(0).max(100).nullable().optional(),
  skonto_tage: z.number().int().min(1).max(365).nullable().optional(),
}).superRefine((data, ctx) => {
  if (!data.zugferd_aktiv) return
  if (!data.firmenname?.trim()) ctx.addIssue({ code: 'custom', path: ['firmenname'], message: 'Pflichtfeld für ZUGFeRD' })
  if (!data.strasse?.trim()) ctx.addIssue({ code: 'custom', path: ['strasse'], message: 'Pflichtfeld für ZUGFeRD' })
  if (!data.plz?.trim()) ctx.addIssue({ code: 'custom', path: ['plz'], message: 'Pflichtfeld für ZUGFeRD' })
  if (!data.ort?.trim()) ctx.addIssue({ code: 'custom', path: ['ort'], message: 'Pflichtfeld für ZUGFeRD' })
})

type FormValues = z.infer<typeof schema>

const EMPTY: FormValues = {
  firmenname: '', vorname: '', nachname: '', strasse: '', hausnummer: '',
  plz: '', ort: '', land: 'DE', ust_idnr: '', email: '', telefon: '',
  kundennummer: '', z_hd: '', notizen: '', ist_verein: false, ist_gemeinnuetzig: false,
  zugferd_aktiv: false, skonto_prozent: null, skonto_tage: null,
}

const inp = 'w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100'
const inpErr = 'w-full border border-red-400 dark:border-red-500 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100'

interface Props {
  onSave: (neuKunde: Kunde) => void
  onClose: () => void
}

export function KundeErstellenModal({ onSave, onClose }: Props) {
  const qc = useQueryClient()
  const { register, handleSubmit, control, setValue, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: EMPTY,
  })

  const watchFirmenname = useWatch({ control, name: 'firmenname' })
  const watchUstIdnr = useWatch({ control, name: 'ust_idnr' })
  const watchZugferd = useWatch({ control, name: 'zugferd_aktiv' })
  const watchLand = useWatch({ control, name: 'land' })
  const zugferdAutoAktiv = !!(watchFirmenname?.trim() && watchUstIdnr?.trim())
  const zugferdOhneUstId = !!(watchZugferd && !watchUstIdnr?.trim())
  // EU-Ausland (nicht DE): ust_idnr fließt unverändert in die Zusammenfassende Meldung (zm.py) -
  // dort MUSS eine syntaktisch gültige EU-USt-IdNr. stehen, keine Steuernummer (Issue #335).
  const istEuAusland = !!watchLand && watchLand !== 'DE' && istEuLand(watchLand)
  const ustIdnrLabel = istEuAusland ? 'USt-IdNr.' : 'USt-IdNr. / Steuernummer'
  const ustIdnrPlaceholder = istEuAusland ? 'z.B. DE123456789' : 'DE123456789 oder 12/345/67890'

  useEffect(() => {
    if (zugferdAutoAktiv) setValue('zugferd_aktiv', true)
  }, [zugferdAutoAktiv, setValue])

  const mut = useMutation({
    mutationFn: (values: FormValues) => {
      const clean = Object.fromEntries(
        Object.entries(values).map(([k, v]) => [k, v === '' ? undefined : v])
      ) as Omit<Kunde, 'id' | 'aktiv' | 'ust_idnr_validiert'>
      return createKunde({
        ...clean,
        land: values.land ?? 'DE',
        ist_verein: values.ist_verein ?? false,
        ist_gemeinnuetzig: values.ist_gemeinnuetzig ?? false,
      })
    },
    onSuccess: (neu) => {
      qc.invalidateQueries({ queryKey: ['kunden'] })
      onSave(neu)
    },
  })

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-4">Neuer Kunde</h3>

        <form onSubmit={(e) => { e.preventDefault(); e.stopPropagation() }} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Firmenname</label>
              <input autoFocus type="text" {...register('firmenname')} className={errors.firmenname ? inpErr : inp} />
              {errors.firmenname && <p className="text-red-500 text-xs mt-0.5">{errors.firmenname.message}</p>}
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Vorname</label>
              <input type="text" {...register('vorname')} className={inp} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Nachname</label>
              <input type="text" {...register('nachname')} className={inp} />
            </div>

            <div className="col-span-2">
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Adresse</label>
              <div className="grid grid-cols-3 gap-2">
                <input type="text" {...register('strasse')} placeholder="Straße" className={`col-span-2 ${errors.strasse ? inpErr : inp}`} />
                <input type="text" {...register('hausnummer')} placeholder="Nr." className={inp} />
                <input type="text" {...register('plz')} placeholder="PLZ" className={errors.plz ? inpErr : inp} />
                <input type="text" {...register('ort')} placeholder="Ort" className={`col-span-2 ${errors.ort ? inpErr : inp}`} />
                <select {...register('land')} className={`col-span-3 ${inp}`}>
                  {LAENDER.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}
                </select>
              </div>
              {(errors.strasse || errors.plz || errors.ort) && (
                <p className="text-red-500 text-xs mt-0.5">Straße, PLZ und Ort sind für ZUGFeRD Pflichtfelder</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">E-Mail</label>
              <input type="email" {...register('email')} className={inp} />
              {errors.email && <p className="text-red-500 text-xs mt-0.5">{errors.email.message}</p>}
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Telefon</label>
              <input type="text" {...register('telefon')} className={inp} />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Kundennummer</label>
              <input type="text" {...register('kundennummer')} placeholder="Wird automatisch vergeben" className={inp} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">{ustIdnrLabel}</label>
              <input type="text" {...register('ust_idnr')} placeholder={ustIdnrPlaceholder} className={inp} />
              {istEuAusland && (
                <p className="text-slate-400 dark:text-slate-500 text-xs mt-0.5">Für ig. Lieferungen/Zusammenfassende Meldung erforderlich – keine Steuernummer.</p>
              )}
            </div>

            <div className="col-span-2">
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">z.Hd. von</label>
              <input type="text" {...register('z_hd')} placeholder="z.B. Max Mustermann oder Buchhaltung" className={inp} />
            </div>

            <div className="col-span-2">
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Skonto (kundenspezifisch)</label>
              <div className="flex items-center gap-2">
                <input type="number" min={0} max={100} step={0.5}
                  {...register('skonto_prozent', { setValueAs: v => v === '' || v == null ? null : parseFloat(v) })}
                  placeholder="z. B. 2"
                  className="w-20 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                <span className="text-xs text-slate-500 dark:text-slate-400">% innerhalb von</span>
                <input type="number" min={1} max={365}
                  {...register('skonto_tage', { setValueAs: v => v === '' || v == null ? null : parseInt(v) })}
                  placeholder="z. B. 10"
                  className="w-20 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                <span className="text-xs text-slate-500 dark:text-slate-400">Tagen</span>
              </div>
            </div>

            <div className="col-span-2">
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Notizen</label>
              <textarea {...register('notizen')} rows={2} className={inp} />
            </div>

            <div className="col-span-2 flex gap-4">
              <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 cursor-pointer">
                <input type="checkbox" {...register('ist_verein')} className="rounded" /> Verein
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 cursor-pointer">
                <input type="checkbox" {...register('ist_gemeinnuetzig')} className="rounded" /> Gemeinnützig
              </label>
            </div>

            <div className="col-span-2">
              <label className={`flex items-start gap-2 text-sm cursor-pointer ${zugferdAutoAktiv ? 'text-slate-400 dark:text-slate-500' : 'text-slate-600 dark:text-slate-300'}`}>
                <input
                  type="checkbox"
                  className="rounded mt-0.5"
                  disabled={zugferdAutoAktiv}
                  checked={zugferdAutoAktiv || undefined}
                  {...(!zugferdAutoAktiv ? register('zugferd_aktiv') : {})}
                  onChange={zugferdAutoAktiv ? undefined : (e) => setValue('zugferd_aktiv', e.target.checked)}
                />
                <span>
                  ZUGFeRD / E-Rechnung
                  {zugferdAutoAktiv
                    ? <span className="ml-1 text-xs text-blue-500 dark:text-blue-400">(automatisch aktiv)</span>
                    : <span className="ml-1 text-xs text-slate-400 dark:text-slate-500">PDF enthält maschinenlesbares XML</span>}
                </span>
              </label>
              {zugferdOhneUstId && (
                <p className="text-amber-600 dark:text-amber-400 text-xs mt-1 ml-6">
                  Hinweis: Ohne USt-IdNr. ist das ZUGFeRD-XML steuerlich unvollständig.
                </p>
              )}
            </div>
          </div>

          {mut.isError && <p className="text-red-600 text-xs">{(mut.error as Error).message}</p>}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-700"
            >
              Abbrechen
            </button>
            <button
              type="button"
              disabled={mut.isPending}
              onClick={() => handleSubmit(v => mut.mutate(v))()}
              className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {mut.isPending ? 'Wird angelegt…' : 'Anlegen'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
