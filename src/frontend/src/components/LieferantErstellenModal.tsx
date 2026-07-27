import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { createLieferant, type Lieferant } from '../api/client'
import { LAENDER } from '../utils/laender'

const schema = z.object({
  firmenname: z.string().min(1, 'Firmenname erforderlich'),
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
  lieferantennummer: z.string().optional(),
  z_hd: z.string().optional(),
  notizen: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

const EMPTY: FormValues = {
  firmenname: '', vorname: '', nachname: '', strasse: '', hausnummer: '',
  plz: '', ort: '', land: 'DE', ust_idnr: '', email: '', telefon: '',
  lieferantennummer: '', z_hd: '', notizen: '',
}

const inp = 'w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100'

interface Props {
  onSave: (neuLieferant: Lieferant) => void
  onClose: () => void
}

export function LieferantErstellenModal({ onSave, onClose }: Props) {
  const qc = useQueryClient()
  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: EMPTY,
  })

  const mut = useMutation({
    mutationFn: (values: FormValues) => {
      const clean = Object.fromEntries(
        Object.entries(values).map(([k, v]) => [k, v === '' ? undefined : v])
      ) as Omit<Lieferant, 'id' | 'aktiv'>
      return createLieferant({ ...clean, firmenname: values.firmenname, land: values.land ?? 'DE' })
    },
    onSuccess: (neu) => {
      qc.invalidateQueries({ queryKey: ['lieferanten'] })
      onSave(neu)
    },
  })

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-4">Neuer Lieferant</h3>

        <form onSubmit={(e) => { e.preventDefault(); e.stopPropagation() }} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Firmenname *</label>
              <input autoFocus type="text" {...register('firmenname')} className={inp} />
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
                <input type="text" {...register('strasse')} placeholder="Straße" className={`col-span-2 ${inp}`} />
                <input type="text" {...register('hausnummer')} placeholder="Nr." className={inp} />
                <input type="text" {...register('plz')} placeholder="PLZ" className={inp} />
                <input type="text" {...register('ort')} placeholder="Ort" className={`col-span-2 ${inp}`} />
                <select {...register('land')} className={`col-span-3 ${inp}`}>
                  {LAENDER.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}
                </select>
              </div>
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
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Lieferantennummer</label>
              <input type="text" {...register('lieferantennummer')} placeholder="Wird automatisch vergeben" className={inp} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">USt-IdNr.</label>
              <input type="text" {...register('ust_idnr')} className={inp} />
            </div>

            <div className="col-span-2">
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">z.Hd. von</label>
              <input type="text" {...register('z_hd')} placeholder="z.B. Max Mustermann oder Buchhaltung" className={inp} />
            </div>

            <div className="col-span-2">
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Notizen</label>
              <textarea {...register('notizen')} rows={2} className={inp} />
            </div>
          </div>

          {mut.isError && (
            <p className="text-red-600 text-xs">{(mut.error as Error).message}</p>
          )}

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
