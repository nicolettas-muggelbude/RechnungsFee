import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  getLieferanten, createLieferant, updateLieferant, deleteLieferant,
  anonymisiereLieferant, dsgvoExportLieferant,
  type Lieferant, type AnonymisierungResult,
} from '../../api/client'

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

// ---------------------------------------------------------------------------
// Detail-Panel (rechts)
// ---------------------------------------------------------------------------

function LieferantDetail({ lieferant }: { lieferant: Lieferant }) {
  return (
    <div className="h-full flex flex-col">

      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-700 shrink-0">
        <h3 className="font-semibold text-slate-800 dark:text-slate-100">{lieferant.firmenname}</h3>
        {(lieferant.vorname || lieferant.nachname) && (
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{[lieferant.vorname, lieferant.nachname].filter(Boolean).join(' ')}</p>
        )}
        {lieferant.lieferantennummer && (
          <p className="text-xs text-slate-400 dark:text-slate-500 font-mono mt-0.5">{lieferant.lieferantennummer}</p>
        )}
      </div>

      {/* Scrollbarer Content */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">

        {/* Adresse */}
        {(lieferant.strasse || lieferant.ort) && (
          <div>
            <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">Adresse</p>
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 space-y-0.5">
              {lieferant.strasse && (
                <p className="text-sm text-slate-700 dark:text-slate-200">{lieferant.strasse} {lieferant.hausnummer}</p>
              )}
              {lieferant.ort && (
                <p className="text-sm text-slate-700 dark:text-slate-200">{lieferant.plz} {lieferant.ort}</p>
              )}
              {lieferant.land && lieferant.land !== 'DE' && (
                <p className="text-xs text-slate-500 dark:text-slate-400">{lieferant.land}</p>
              )}
            </div>
          </div>
        )}

        {/* Kontakt */}
        {(lieferant.email || lieferant.telefon) && (
          <div>
            <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">Kontakt</p>
            <div className="grid grid-cols-1 gap-2">
              {lieferant.email && (
                <div>
                  <p className="text-xs text-slate-400 dark:text-slate-500">E-Mail</p>
                  <p className="text-sm text-slate-700 dark:text-slate-200 break-all">{lieferant.email}</p>
                </div>
              )}
              {lieferant.telefon && (
                <div>
                  <p className="text-xs text-slate-400 dark:text-slate-500">Telefon</p>
                  <p className="text-sm text-slate-700 dark:text-slate-200">{lieferant.telefon}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Steuer / Nummern */}
        {lieferant.ust_idnr && (
          <div>
            <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">Steuer</p>
            <div>
              <p className="text-xs text-slate-400 dark:text-slate-500">USt-IdNr.</p>
              <p className="text-sm text-slate-700 dark:text-slate-200 font-mono">{lieferant.ust_idnr}</p>
            </div>
          </div>
        )}

        {/* Notizen */}
        {lieferant.notizen && (
          <div>
            <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">Notizen</p>
            <p className="text-sm text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-3 whitespace-pre-wrap">{lieferant.notizen}</p>
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Hauptseite
// ---------------------------------------------------------------------------

export function LieferantenPage() {
  const qc = useQueryClient()
  const [selected, setSelected] = useState<Lieferant | null>(null)
  const [suche, setSuche] = useState('')
  const [editLieferant, setEditLieferant] = useState<Lieferant | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [deleteFehlgeschlagen, setDeleteFehlgeschlagen] = useState(false)
  const [showDsgvoBestaetigung, setShowDsgvoBestaetigung] = useState(false)
  const [anonymisierungResult, setAnonymisierungResult] = useState<AnonymisierungResult | null>(null)

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
    mutationFn: (l: Lieferant) => deleteLieferant(l.id!),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['lieferanten'] }); setSelected(null) },
    onError: (_err: Error, l: Lieferant) => {
      setDeleteFehlgeschlagen(true)
      openEdit(l)
    },
  })
  const anonymisierungMutation = useMutation({
    mutationFn: (id: number) => anonymisiereLieferant(id),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ['lieferanten'] })
      setAnonymisierungResult(result)
      setShowDsgvoBestaetigung(false)
    },
  })

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: EMPTY,
  })

  function openCreate() {
    setEditLieferant(null)
    setDeleteFehlgeschlagen(false)
    setShowDsgvoBestaetigung(false)
    setAnonymisierungResult(null)
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

  function closeForm() {
    setShowForm(false)
    setEditLieferant(null)
    setDeleteFehlgeschlagen(false)
    setShowDsgvoBestaetigung(false)
    setAnonymisierungResult(null)
  }

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
    deleteMutation.mutate(l)
  }

  const isPending = createMutation.isPending || updateMutation.isPending
  const mutationError = createMutation.error || updateMutation.error

  const s = suche.toLowerCase()
  const gefiltert = (lieferanten ?? []).filter((l) =>
    !s || l.firmenname.toLowerCase().includes(s) ||
    (l.email ?? '').toLowerCase().includes(s) ||
    (l.lieferantennummer ?? '').toLowerCase().includes(s) ||
    (l.ort ?? '').toLowerCase().includes(s)
  )

  return (
    <div className="flex h-full">

      {/* ── Linke Spalte ─────────────────────────────────────────────── */}
      <div className={`${showForm ? 'w-1/3 min-w-[260px] shrink-0' : 'flex-1'} flex flex-col border-e border-slate-200 dark:border-slate-700 min-w-0 transition-all`}>

        {/* Header */}
        <div className="p-6 pb-4 shrink-0">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Lieferanten</h2>
            <button onClick={openCreate} className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-xl hover:bg-blue-700">
              + Neu
            </button>
          </div>
          <input
            type="text"
            placeholder="Suchen…"
            value={suche}
            onChange={(e) => setSuche(e.target.value)}
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
          />
        </div>

        {/* Tabelle */}
        <div className="flex-1 overflow-y-auto min-h-0 px-6 pb-6">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          {isLoading ? (
            <p className="text-slate-400 dark:text-slate-500 text-sm p-5">Lade…</p>
          ) : !gefiltert.length ? (
            <p className="text-slate-400 dark:text-slate-500 text-sm p-5">{suche ? 'Keine Treffer.' : 'Noch keine Lieferanten angelegt.'}</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                <tr className="text-left">
                  <th className="px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400">Firmenname</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400">Adresse</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400">E-Mail</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400">Lieferantennr.</th>
                  <th className="px-4 py-2.5 w-28"></th>
                </tr>
              </thead>
              <tbody>
                {gefiltert.map((l) => (
                  <tr
                    key={l.id}
                    onClick={() => setSelected(selected?.id === l.id ? null : l)}
                    className={`border-b border-slate-100 dark:border-slate-700 last:border-0 cursor-pointer transition-colors ${
                      selected?.id === l.id ? 'bg-blue-50 dark:bg-blue-950' : 'hover:bg-slate-50 dark:hover:bg-slate-700'
                    }`}
                  >
                    <td className={`px-4 py-2.5 font-medium truncate max-w-[120px] ${selected?.id === l.id ? 'text-blue-700 dark:text-blue-300' : 'text-slate-800 dark:text-slate-100'}`}>
                      {l.firmenname}
                    </td>
                    <td className="px-4 py-2.5 text-slate-500 dark:text-slate-400 text-xs">
                      {[l.strasse && l.hausnummer ? `${l.strasse} ${l.hausnummer}` : l.strasse, l.plz && l.ort ? `${l.plz} ${l.ort}` : l.ort].filter(Boolean).join(', ') || '—'}
                    </td>
                    <td className="px-4 py-2.5 text-slate-500 dark:text-slate-400">{l.email || '—'}</td>
                    <td className="px-4 py-2.5 text-slate-400 dark:text-slate-500 font-mono text-xs">{l.lieferantennummer || '—'}</td>
                    <td className="px-4 py-2.5">
                      <div className="flex gap-2 justify-end" onClick={(e) => e.stopPropagation()}>
                        <button onClick={() => openEdit(l)} className="text-xs text-blue-600 dark:text-blue-400 hover:underline">Bearbeiten</button>
                        <button onClick={() => handleDelete(l)} className="text-xs text-red-500 dark:text-red-400 hover:underline">Löschen</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          </div>
        </div>

        {/* Stammdaten-Karte des ausgewählten Lieferanten */}
        {selected && (
          <div className="shrink-0 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 px-4 py-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">{selected.firmenname}</span>
              <button onClick={() => setSelected(null)} className="text-slate-400 hover:text-slate-600 text-sm leading-none">×</button>
            </div>
            <div className="grid grid-cols-4 gap-2 text-xs">
              {selected.telefon && (
                <div><span className="text-slate-400 dark:text-slate-500 block">Telefon</span><span className="text-slate-700 dark:text-slate-200">{selected.telefon}</span></div>
              )}
              {selected.ust_idnr && (
                <div><span className="text-slate-400 dark:text-slate-500 block">USt-IdNr.</span><span className="text-slate-700 dark:text-slate-200 font-mono">{selected.ust_idnr}</span></div>
              )}
              {selected.email && (
                <div><span className="text-slate-400 dark:text-slate-500 block">E-Mail</span><span className="text-slate-700 dark:text-slate-200">{selected.email}</span></div>
              )}
              {selected.lieferantennummer && (
                <div><span className="text-slate-400 dark:text-slate-500 block">Lieferantennr.</span><span className="text-slate-700 dark:text-slate-200 font-mono">{selected.lieferantennummer}</span></div>
              )}
            </div>
            {selected.notizen && (
              <p className="mt-2 text-xs text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-700 px-2 py-1.5 whitespace-pre-wrap">{selected.notizen}</p>
            )}
          </div>
        )}
      </div>

      {/* ── Rechte Spalte (Detail oder Formular) ─────────────────────── */}
      {!showForm && (
        <div className="w-80 shrink-0">
          {selected ? (
            <LieferantDetail key={selected.id} lieferant={selected} />
          ) : (
            <div className="flex items-center justify-center h-full text-slate-400 dark:text-slate-500 text-sm">
              Lieferant auswählen
            </div>
          )}
        </div>
      )}

      {/* ── Formular-Panel ───────────────────────────────────────────── */}
      {showForm && (
        <div className="flex-1 border-l border-slate-200 dark:border-slate-700 overflow-y-auto">
          <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between shrink-0">
            <h3 className="font-semibold text-slate-800 dark:text-slate-100">
              {editLieferant ? 'Lieferant bearbeiten' : 'Neuer Lieferant'}
            </h3>
            <button onClick={closeForm} className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-xl leading-none">×</button>
          </div>
          <div className="p-6 max-w-lg">
            {deleteFehlgeschlagen && (
              <div className="mb-4 bg-amber-50 dark:bg-amber-950 border border-amber-300 dark:border-amber-800 rounded-lg px-4 py-3 text-sm text-amber-800 dark:text-amber-300">
                <p className="font-medium">Löschen nicht möglich</p>
                <p className="mt-0.5">Dieser Lieferant hat verknüpfte Rechnungen und kann nicht direkt gelöscht werden. Verwende unten <strong>„Anonymisieren (Art. 17)"</strong>, um die Daten datenschutzkonform zu entfernen.</p>
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Firmenname *</label>
                  <input type="text" {...register('firmenname')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                  {errors.firmenname && <p className="text-red-500 text-xs mt-0.5">{errors.firmenname.message}</p>}
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Vorname</label>
                  <input type="text" {...register('vorname')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Nachname</label>
                  <input type="text" {...register('nachname')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Adresse</label>
                  <div className="grid grid-cols-3 gap-2">
                    <input type="text" {...register('strasse')} placeholder="Straße" className="col-span-2 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                    <input type="text" {...register('hausnummer')} placeholder="Nr." className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                    <input type="text" {...register('plz')} placeholder="PLZ" className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                    <input type="text" {...register('ort')} placeholder="Ort" className="col-span-2 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                    <input type="text" {...register('land')} placeholder="Land (z.B. DE)" className="col-span-3 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">E-Mail</label>
                  <input type="email" {...register('email')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                  {errors.email && <p className="text-red-500 text-xs mt-0.5">{errors.email.message}</p>}
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Telefon</label>
                  <input type="text" {...register('telefon')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Lieferantennummer</label>
                  <input type="text" {...register('lieferantennummer')} placeholder="Wird automatisch vergeben" className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">USt-IdNr.</label>
                  <input type="text" {...register('ust_idnr')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Notizen</label>
                  <textarea {...register('notizen')} rows={2} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                </div>
              </div>

              {mutationError && (
                <p className="text-red-600 text-sm">{(mutationError as Error).message}</p>
              )}

              <div className="flex gap-3 pt-2">
                <button type="button" onClick={closeForm} className="flex-1 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-700">
                  Abbrechen
                </button>
                <button type="submit" disabled={isPending} className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
                  {isPending ? 'Speichert…' : 'Speichern'}
                </button>
              </div>

              {/* DSGVO-Aktionen (nur im Bearbeitungs-Modus) */}
              {editLieferant?.id && !anonymisierungResult && (
                <div className="border-t border-slate-200 dark:border-slate-700 pt-3 space-y-2">
                  <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide">Datenschutz (DSGVO)</p>
                  {!showDsgvoBestaetigung ? (
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => dsgvoExportLieferant(editLieferant.id!)}
                        className="flex-1 text-xs border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg py-1.5 hover:bg-slate-50 dark:hover:bg-slate-700"
                      >
                        📥 Datenauskunft exportieren
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowDsgvoBestaetigung(true)}
                        className="flex-1 text-xs border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 rounded-lg py-1.5 hover:bg-red-50 dark:hover:bg-red-950"
                      >
                        🗑 Anonymisieren (Art. 17)
                      </button>
                    </div>
                  ) : (
                    <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg p-3 space-y-2">
                      <p className="text-sm font-medium text-red-800 dark:text-red-300">Lieferant wirklich anonymisieren?</p>
                      <ul className="text-xs text-red-700 dark:text-red-400 space-y-0.5 list-disc list-inside">
                        <li>Lieferantenstammdaten werden dauerhaft gelöscht</li>
                        <li>Verknüpfungen in Rechnungen werden entfernt</li>
                        <li>Der Lieferantenname bleibt in den Rechnungen als Freitext erhalten</li>
                      </ul>
                      {anonymisierungMutation.isError && (
                        <p className="text-xs text-red-600 dark:text-red-400">{(anonymisierungMutation.error as Error).message}</p>
                      )}
                      <div className="flex gap-2 pt-1">
                        <button
                          type="button"
                          onClick={() => anonymisierungMutation.mutate(editLieferant.id!)}
                          disabled={anonymisierungMutation.isPending}
                          className="flex-1 bg-red-600 text-white rounded-lg py-1.5 text-xs font-medium hover:bg-red-700 disabled:opacity-50"
                        >
                          {anonymisierungMutation.isPending ? '…' : 'Jetzt anonymisieren'}
                        </button>
                        <button
                          type="button"
                          onClick={() => setShowDsgvoBestaetigung(false)}
                          className="flex-1 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg py-1.5 text-xs hover:bg-slate-50 dark:hover:bg-slate-700"
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
                <div className="border-t border-slate-200 dark:border-slate-700 pt-3">
                  <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg p-3 space-y-1">
                    <p className="text-sm font-medium text-green-800 dark:text-green-300">Anonymisierung abgeschlossen</p>
                    <p className="text-xs text-green-700 dark:text-green-400">
                      {anonymisierungResult.anonymisierte_rechnungen} Rechnung(en) anonymisiert.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={closeForm}
                    className="w-full mt-2 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-700"
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
