import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { getLieferanten, createLieferant, updateLieferant, deleteLieferant, type Lieferant } from '../../api/client'

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
  notizen: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

const EMPTY: FormValues = {
  firmenname: '', vorname: '', nachname: '', strasse: '', hausnummer: '',
  plz: '', ort: '', land: 'DE', ust_idnr: '', email: '', telefon: '',
  lieferantennummer: '', notizen: '',
}

export function LieferantenPage() {
  const qc = useQueryClient()
  const [editLieferant, setEditLieferant] = useState<Lieferant | null>(null)
  const [showForm, setShowForm] = useState(false)

  const { data: lieferanten, isLoading } = useQuery({
    queryKey: ['lieferanten'],
    queryFn: getLieferanten,
  })

  const createMutation = useMutation({
    mutationFn: createLieferant,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['lieferanten'] }); closeForm() },
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Lieferant> }) => updateLieferant(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['lieferanten'] }); closeForm() },
  })
  const deleteMutation = useMutation({
    mutationFn: deleteLieferant,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['lieferanten'] }),
  })

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: EMPTY,
  })

  function openCreate() {
    setEditLieferant(null)
    reset(EMPTY)
    setShowForm(true)
  }

  function openEdit(l: Lieferant) {
    setEditLieferant(l)
    reset({
      firmenname: l.firmenname, vorname: l.vorname ?? '', nachname: l.nachname ?? '',
      strasse: l.strasse ?? '', hausnummer: l.hausnummer ?? '', plz: l.plz ?? '',
      ort: l.ort ?? '', land: l.land, ust_idnr: l.ust_idnr ?? '',
      email: l.email ?? '', telefon: l.telefon ?? '',
      lieferantennummer: l.lieferantennummer ?? '', notizen: l.notizen ?? '',
    })
    setShowForm(true)
  }

  function closeForm() { setShowForm(false); setEditLieferant(null) }

  function onSubmit(values: FormValues) {
    const clean = Object.fromEntries(
      Object.entries(values).map(([k, v]) => [k, v === '' ? undefined : v])
    ) as Partial<Lieferant>
    if (editLieferant?.id) {
      updateMutation.mutate({ id: editLieferant.id, data: clean })
    } else {
      createMutation.mutate({ ...clean, firmenname: values.firmenname, land: values.land ?? 'DE' })
    }
  }

  function handleDelete(l: Lieferant) {
    if (!l.id) return
    if (!window.confirm(`Lieferant "${l.firmenname}" löschen?`)) return
    deleteMutation.mutate(l.id)
  }

  const isPending = createMutation.isPending || updateMutation.isPending
  const mutationError = createMutation.error || updateMutation.error

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-slate-800">Lieferanten</h2>
        <button onClick={openCreate} className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700">
          + Neuer Lieferant
        </button>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {isLoading ? (
          <p className="text-slate-400 text-sm p-5">Lade…</p>
        ) : !lieferanten?.length ? (
          <p className="text-slate-400 text-sm p-5">Noch keine Lieferanten angelegt.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-left">
                <th className="px-4 py-3 text-xs font-semibold text-slate-500">Firmenname</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500">E-Mail</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500">Lieferantennr.</th>
                <th className="px-4 py-3 w-20"></th>
              </tr>
            </thead>
            <tbody>
              {lieferanten.map((l) => (
                <tr key={l.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                  <td className="px-4 py-3 text-slate-700">{l.firmenname}</td>
                  <td className="px-4 py-3 text-slate-500">{l.email || '—'}</td>
                  <td className="px-4 py-3 text-slate-400 font-mono text-xs">{l.lieferantennummer || '—'}</td>
                  <td className="px-4 py-3 flex gap-2 justify-end">
                    <button onClick={() => openEdit(l)} className="text-xs text-blue-600 hover:underline">Bearbeiten</button>
                    <button onClick={() => handleDelete(l)} className="text-xs text-red-500 hover:underline">Löschen</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-bold text-slate-800 mb-4">
              {editLieferant ? 'Lieferant bearbeiten' : 'Neuer Lieferant'}
            </h2>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-600 mb-1">Firmenname *</label>
                  <input type="text" {...register('firmenname')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                  {errors.firmenname && <p className="text-red-500 text-xs mt-0.5">{errors.firmenname.message}</p>}
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Vorname</label>
                  <input type="text" {...register('vorname')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Nachname</label>
                  <input type="text" {...register('nachname')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">E-Mail</label>
                  <input type="email" {...register('email')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                  {errors.email && <p className="text-red-500 text-xs mt-0.5">{errors.email.message}</p>}
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Telefon</label>
                  <input type="text" {...register('telefon')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Lieferantennummer</label>
                  <input type="text" {...register('lieferantennummer')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">USt-IdNr.</label>
                  <input type="text" {...register('ust_idnr')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-600 mb-1">Notizen</label>
                  <textarea {...register('notizen')} rows={2} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              </div>

              {mutationError && (
                <p className="text-red-600 text-sm">{(mutationError as Error).message}</p>
              )}

              <div className="flex gap-3 pt-2">
                <button type="button" onClick={closeForm} className="flex-1 border border-slate-300 text-slate-600 rounded-lg py-2 text-sm hover:bg-slate-50">
                  Abbrechen
                </button>
                <button type="submit" disabled={isPending} className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
                  {isPending ? 'Speichert…' : 'Speichern'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
