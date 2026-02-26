import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  getKunden, createKunde, updateKunde, deleteKunde,
  anonymisiereKunde, dsgvoExportKunde,
  type Kunde, type AnonymisierungResult,
} from '../../api/client'

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
  notizen: z.string().optional(),
  ist_verein: z.boolean().optional(),
  ist_gemeinnuetzig: z.boolean().optional(),
})

type FormValues = z.infer<typeof schema>

const EMPTY: FormValues = {
  firmenname: '', vorname: '', nachname: '', strasse: '', hausnummer: '',
  plz: '', ort: '', land: 'DE', ust_idnr: '', email: '', telefon: '',
  kundennummer: '', notizen: '', ist_verein: false, ist_gemeinnuetzig: false,
}

export function KundenPage() {
  const qc = useQueryClient()
  const [editKunde, setEditKunde] = useState<Kunde | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [deleteFehlgeschlagen, setDeleteFehlgeschlagen] = useState(false)
  const [showDsgvoBestaetigung, setShowDsgvoBestaetigung] = useState(false)
  const [anonymisierungResult, setAnonymisierungResult] = useState<AnonymisierungResult | null>(null)

  const { data: kunden, isLoading } = useQuery({
    queryKey: ['kunden'],
    queryFn: getKunden,
  })

  const createMutation = useMutation({
    mutationFn: createKunde,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['kunden'] }); closeForm() },
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Kunde> }) => updateKunde(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['kunden'] }); closeForm() },
  })
  const deleteMutation = useMutation({
    mutationFn: (k: Kunde) => deleteKunde(k.id!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['kunden'] }),
    onError: (_err: Error, k: Kunde) => {
      setDeleteFehlgeschlagen(true)
      openEdit(k)
    },
  })

  const anonymisierungMutation = useMutation({
    mutationFn: (id: number) => anonymisiereKunde(id),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ['kunden'] })
      setAnonymisierungResult(result)
      setShowDsgvoBestaetigung(false)
    },
  })

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: EMPTY,
  })

  function openCreate() {
    setEditKunde(null)
    reset(EMPTY)
    setShowForm(true)
  }

  function openEdit(k: Kunde) {
    setEditKunde(k)
    reset({
      firmenname: k.firmenname ?? '', vorname: k.vorname ?? '', nachname: k.nachname ?? '',
      strasse: k.strasse ?? '', hausnummer: k.hausnummer ?? '', plz: k.plz ?? '',
      ort: k.ort ?? '', land: k.land, ust_idnr: k.ust_idnr ?? '',
      email: k.email ?? '', telefon: k.telefon ?? '', kundennummer: k.kundennummer ?? '',
      notizen: k.notizen ?? '', ist_verein: k.ist_verein, ist_gemeinnuetzig: k.ist_gemeinnuetzig,
    })
    setShowForm(true)
  }

  function closeForm() {
    setShowForm(false)
    setEditKunde(null)
    setDeleteFehlgeschlagen(false)
    setShowDsgvoBestaetigung(false)
    setAnonymisierungResult(null)
  }

  function onSubmit(values: FormValues) {
    // Leere Strings → undefined
    const clean = Object.fromEntries(
      Object.entries(values).map(([k, v]) => [k, v === '' ? undefined : v])
    ) as Partial<Kunde>
    if (editKunde?.id) {
      updateMutation.mutate({ id: editKunde.id, data: clean })
    } else {
      createMutation.mutate({
        ...clean,
        ist_verein: values.ist_verein ?? false,
        ist_gemeinnuetzig: values.ist_gemeinnuetzig ?? false,
        land: values.land ?? 'DE',
      })
    }
  }

  function handleDelete(k: Kunde) {
    if (!k.id) return
    if (!window.confirm(`Kunden "${k.firmenname ?? k.nachname}" löschen?`)) return
    deleteMutation.mutate(k)
  }

  const isPending = createMutation.isPending || updateMutation.isPending
  const mutationError = createMutation.error || updateMutation.error

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-slate-800">Kunden</h2>
        <button onClick={openCreate} className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700">
          + Neuer Kunde
        </button>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {isLoading ? (
          <p className="text-slate-400 text-sm p-5">Lade…</p>
        ) : !kunden?.length ? (
          <p className="text-slate-400 text-sm p-5">Noch keine Kunden angelegt.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-left">
                <th className="px-4 py-3 text-xs font-semibold text-slate-500">Name / Firma</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500">Adresse</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500">E-Mail</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500">Kundennr.</th>
                <th className="px-4 py-3 w-20"></th>
              </tr>
            </thead>
            <tbody>
              {kunden.map((k) => (
                <tr key={k.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                  <td className="px-4 py-3 text-slate-700">
                    {k.firmenname || [k.vorname, k.nachname].filter(Boolean).join(' ') || '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-500 text-xs">
                    {[k.strasse && k.hausnummer ? `${k.strasse} ${k.hausnummer}` : k.strasse, k.plz && k.ort ? `${k.plz} ${k.ort}` : k.ort].filter(Boolean).join(', ') || '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-500">{k.email || '—'}</td>
                  <td className="px-4 py-3 text-slate-400 font-mono text-xs">{k.kundennummer || '—'}</td>
                  <td className="px-4 py-3 flex gap-2 justify-end">
                    <button onClick={() => openEdit(k)} className="text-xs text-blue-600 hover:underline">Bearbeiten</button>
                    <button onClick={() => handleDelete(k)} className="text-xs text-red-500 hover:underline">Löschen</button>
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
              {editKunde ? 'Kunde bearbeiten' : 'Neuer Kunde'}
            </h2>
            {deleteFehlgeschlagen && (
              <div className="mb-4 bg-amber-50 border border-amber-300 rounded-lg px-4 py-3 text-sm text-amber-800">
                <p className="font-medium">Löschen nicht möglich</p>
                <p className="mt-0.5">Dieser Kunde hat verknüpfte Buchungen oder Rechnungen und kann nicht direkt gelöscht werden. Verwende unten <strong>„Anonymisieren (Art. 17)"</strong>, um die Daten datenschutzkonform zu entfernen.</p>
              </div>
            )}
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-600 mb-1">Firmenname</label>
                  <input type="text" {...register('firmenname')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Vorname</label>
                  <input type="text" {...register('vorname')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Nachname</label>
                  <input type="text" {...register('nachname')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-600 mb-1">Adresse</label>
                  <div className="grid grid-cols-3 gap-2">
                    <input type="text" {...register('strasse')} placeholder="Straße" className="col-span-2 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    <input type="text" {...register('hausnummer')} placeholder="Nr." className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    <input type="text" {...register('plz')} placeholder="PLZ" className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    <input type="text" {...register('ort')} placeholder="Ort" className="col-span-2 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    <input type="text" {...register('land')} placeholder="Land (z.B. DE)" className="col-span-3 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                  </div>
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
                  <label className="block text-xs font-medium text-slate-600 mb-1">Kundennummer</label>
                  <input type="text" {...register('kundennummer')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">USt-IdNr.</label>
                  <input type="text" {...register('ust_idnr')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-600 mb-1">Notizen</label>
                  <textarea {...register('notizen')} rows={2} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div className="col-span-2 flex gap-4">
                  <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                    <input type="checkbox" {...register('ist_verein')} className="rounded" />
                    Verein
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                    <input type="checkbox" {...register('ist_gemeinnuetzig')} className="rounded" />
                    Gemeinnützig
                  </label>
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

              {/* DSGVO-Aktionen (nur im Bearbeitungs-Modus) */}
              {editKunde?.id && !anonymisierungResult && (
                <div className="border-t border-slate-200 pt-3 space-y-2">
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Datenschutz (DSGVO)</p>
                  {!showDsgvoBestaetigung ? (
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => dsgvoExportKunde(editKunde.id!)}
                        className="flex-1 text-xs border border-slate-300 text-slate-600 rounded-lg py-1.5 hover:bg-slate-50"
                      >
                        📥 Datenauskunft exportieren
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowDsgvoBestaetigung(true)}
                        className="flex-1 text-xs border border-red-200 text-red-600 rounded-lg py-1.5 hover:bg-red-50"
                      >
                        🗑 Anonymisieren (Art. 17)
                      </button>
                    </div>
                  ) : (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3 space-y-2">
                      <p className="text-sm font-medium text-red-800">Kunden wirklich anonymisieren?</p>
                      <ul className="text-xs text-red-700 space-y-0.5 list-disc list-inside">
                        <li>Kundenstammdaten werden dauerhaft gelöscht</li>
                        <li>Verknüpfungen in offenen Buchungen und Rechnungen werden entfernt</li>
                        <li>Immutable Kassenbucheinträge bleiben aus rechtlichen Gründen erhalten (§147 AO)</li>
                      </ul>
                      {anonymisierungMutation.isError && (
                        <p className="text-xs text-red-600">{(anonymisierungMutation.error as Error).message}</p>
                      )}
                      <div className="flex gap-2 pt-1">
                        <button
                          type="button"
                          onClick={() => anonymisierungMutation.mutate(editKunde.id!)}
                          disabled={anonymisierungMutation.isPending}
                          className="flex-1 bg-red-600 text-white rounded-lg py-1.5 text-xs font-medium hover:bg-red-700 disabled:opacity-50"
                        >
                          {anonymisierungMutation.isPending ? '…' : 'Jetzt anonymisieren'}
                        </button>
                        <button
                          type="button"
                          onClick={() => setShowDsgvoBestaetigung(false)}
                          className="flex-1 border border-slate-300 text-slate-600 rounded-lg py-1.5 text-xs hover:bg-slate-50"
                        >
                          Abbrechen
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Ergebnis der Anonymisierung */}
              {anonymisierungResult && (
                <div className="border-t border-slate-200 pt-3">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3 space-y-1">
                    <p className="text-sm font-medium text-green-800">Anonymisierung abgeschlossen</p>
                    <p className="text-xs text-green-700">
                      {anonymisierungResult.anonymisierte_buchungen} Buchung(en) und {anonymisierungResult.anonymisierte_rechnungen} Rechnung(en) anonymisiert.
                    </p>
                    {anonymisierungResult.unveraenderlich_verblieben > 0 && (
                      <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1 mt-1">
                        ⚠ {anonymisierungResult.hinweis}
                      </p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={closeForm}
                    className="w-full mt-2 border border-slate-300 text-slate-600 rounded-lg py-2 text-sm hover:bg-slate-50"
                  >
                    Schließen
                  </button>
                </div>
              )}
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
