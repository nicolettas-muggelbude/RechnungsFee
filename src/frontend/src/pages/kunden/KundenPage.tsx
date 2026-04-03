import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  getKunden, createKunde, updateKunde, deleteKunde,
  anonymisiereKunde, dsgvoExportKunde, getRechnungen,
  type Kunde, type AnonymisierungResult, type Rechnung,
} from '../../api/client'

function formatEuro(val: string | number): string {
  const n = typeof val === 'string' ? parseFloat(val) : val
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n)
}

function formatDatum(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

function kundeName(k: Kunde): string {
  return k.firmenname || [k.vorname, k.nachname].filter(Boolean).join(' ') || '—'
}

// ---------------------------------------------------------------------------
// Rechts: Rechnungspanel
// ---------------------------------------------------------------------------

function KundeRechnungen({ kunde }: { kunde: Kunde }) {
  const [offeneRechnung, setOffeneRechnung] = useState<number | null>(null)

  const { data: rechnungen, isLoading } = useQuery({
    queryKey: ['kunden-rechnungen', kunde.id],
    queryFn: () => getRechnungen({ typ: 'ausgang', kunde_id: kunde.id }),
    staleTime: 1000 * 60,
  })

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 shrink-0">
        <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
          Rechnungen ({rechnungen?.length ?? '…'})
        </p>
      </div>
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1.5">
        {isLoading && <p className="text-xs text-slate-400 dark:text-slate-500 p-1">Lade…</p>}
        {!isLoading && !rechnungen?.length && (
          <p className="text-xs text-slate-400 dark:text-slate-500 p-1">Noch keine Ausgangsrechnungen.</p>
        )}
        {rechnungen?.map((r: Rechnung) => (
          <div key={r.id} className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
            <button
              type="button"
              onClick={() => setOffeneRechnung(offeneRechnung === r.id ? null : r.id)}
              className="w-full flex items-center justify-between px-3 py-2 text-xs hover:bg-slate-50 dark:hover:bg-slate-700 text-left gap-2 dark:bg-slate-800"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="font-mono text-slate-400 dark:text-slate-500 shrink-0">{r.rechnungsnummer ?? '—'}</span>
                  <span className="font-semibold text-slate-700 dark:text-slate-200">{formatEuro(r.brutto_gesamt)}</span>
                </div>
                <div className="text-slate-400 dark:text-slate-500">{formatDatum(r.datum)}</div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <span className={`px-1.5 py-0.5 rounded-full border text-[10px] ${
                  r.zahlungsstatus === 'bezahlt' ? 'bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800'
                  : r.zahlungsstatus === 'teilweise' ? 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800'
                  : 'bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-800'
                }`}>
                  {r.zahlungsstatus === 'bezahlt' ? 'Bezahlt' : r.zahlungsstatus === 'teilweise' ? 'Teil' : 'Offen'}
                </span>
                <span className="text-slate-400 dark:text-slate-500">{offeneRechnung === r.id ? '▲' : '▼'}</span>
              </div>
            </button>
            {offeneRechnung === r.id && r.positionen.length > 0 && (
              <div className="border-t border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 px-3 py-2">
                {r.positionen.map((p) => (
                  <div key={p.id} className="flex items-start justify-between gap-2 py-1 border-b border-slate-100 dark:border-slate-700 last:border-0 text-xs">
                    <span className="text-slate-700 dark:text-slate-200 min-w-0">
                      {p.beschreibung}
                      {p.artikel_typ && (
                        <span className="ms-1 text-slate-400 dark:text-slate-500 bg-slate-200 dark:bg-slate-700 rounded px-1 py-0.5 text-[10px]">
                          {p.artikel_typ === 'artikel' ? 'Artikel' : p.artikel_typ === 'dienstleistung' ? 'Dienstl.' : 'Fremdl.'}
                        </span>
                      )}
                    </span>
                    <span className="text-slate-500 dark:text-slate-400 shrink-0">{formatEuro(p.brutto)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Formular-Schema
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Hauptseite
// ---------------------------------------------------------------------------

export function KundenPage() {
  const qc = useQueryClient()
  const [selected, setSelected] = useState<Kunde | null>(null)
  const [suche, setSuche] = useState('')
  const [editKunde, setEditKunde] = useState<Kunde | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [deleteFehlgeschlagen, setDeleteFehlgeschlagen] = useState(false)
  const [showDsgvoBestaetigung, setShowDsgvoBestaetigung] = useState(false)
  const [anonymisierungResult, setAnonymisierungResult] = useState<AnonymisierungResult | null>(null)

  const { data: kunden, isLoading } = useQuery({ queryKey: ['kunden'], queryFn: getKunden })

  const createMutation = useMutation({
    mutationFn: createKunde,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['kunden'] }); closeForm() },
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Kunde> }) => updateKunde(id, data),
    onSuccess: (updated) => { qc.invalidateQueries({ queryKey: ['kunden'] }); setSelected(updated); closeForm() },
  })
  const deleteMutation = useMutation({
    mutationFn: (k: Kunde) => deleteKunde(k.id!),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['kunden'] }); setSelected(null) },
    onError: (_err: Error, k: Kunde) => { setDeleteFehlgeschlagen(true); openEdit(k) },
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

  function openCreate() { setEditKunde(null); reset(EMPTY); setShowForm(true) }

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
    setShowForm(false); setEditKunde(null)
    setDeleteFehlgeschlagen(false); setShowDsgvoBestaetigung(false); setAnonymisierungResult(null)
  }

  function onSubmit(values: FormValues) {
    const clean = Object.fromEntries(
      Object.entries(values).map(([k, v]) => [k, v === '' ? undefined : v])
    ) as Partial<Kunde>
    if (editKunde?.id) {
      updateMutation.mutate({ id: editKunde.id, data: clean })
    } else {
      createMutation.mutate({ ...clean, ist_verein: values.ist_verein ?? false, ist_gemeinnuetzig: values.ist_gemeinnuetzig ?? false, land: values.land ?? 'DE' })
    }
  }

  function handleDelete(k: Kunde) {
    if (!k.id) return
    if (!window.confirm(`Kunden "${kundeName(k)}" löschen?`)) return
    deleteMutation.mutate(k)
  }

  const s = suche.toLowerCase()
  const gefiltert = (kunden ?? []).filter((k) =>
    !s || kundeName(k).toLowerCase().includes(s) ||
    (k.email ?? '').toLowerCase().includes(s) ||
    (k.kundennummer ?? '').toLowerCase().includes(s) ||
    (k.ort ?? '').toLowerCase().includes(s)
  )

  const isPending = createMutation.isPending || updateMutation.isPending
  const mutationError = createMutation.error || updateMutation.error

  return (
    <div className="flex h-full">

      {/* ── Linke Spalte (breit) ─────────────────────────────────────── */}
      <div className={`${showForm ? 'w-1/4 min-w-[200px] shrink-0' : 'flex-1'} flex flex-col border-e border-slate-200 dark:border-slate-700 min-w-0 transition-all`}>

        {/* Header */}
        <div className="p-6 pb-4 shrink-0">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Kunden</h2>
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
            <p className="text-slate-400 dark:text-slate-500 text-sm p-5">{suche ? 'Keine Treffer.' : 'Noch keine Kunden.'}</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                <tr className="text-left">
                  <th className="px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400">Name / Firma</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400">Adresse</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400">E-Mail</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400">Kundennr.</th>
                  <th className="px-4 py-2.5 w-28"></th>
                </tr>
              </thead>
              <tbody>
                {gefiltert.map((k) => (
                  <tr
                    key={k.id}
                    onClick={() => setSelected(selected?.id === k.id ? null : k)}
                    className={`border-b border-slate-100 dark:border-slate-700 last:border-0 cursor-pointer transition-colors ${
                      selected?.id === k.id ? 'bg-blue-50 dark:bg-blue-950' : 'hover:bg-slate-50 dark:hover:bg-slate-700'
                    }`}
                  >
                    <td className={`px-4 py-2.5 font-medium ${selected?.id === k.id ? 'text-blue-700 dark:text-blue-300' : 'text-slate-800 dark:text-slate-100'}`}>
                      {kundeName(k)}
                    </td>
                    <td className="px-4 py-2.5 text-slate-500 dark:text-slate-400 text-xs">
                      {[k.strasse && k.hausnummer ? `${k.strasse} ${k.hausnummer}` : k.strasse, k.plz && k.ort ? `${k.plz} ${k.ort}` : k.ort].filter(Boolean).join(', ') || '—'}
                    </td>
                    <td className="px-4 py-2.5 text-slate-500 dark:text-slate-400">{k.email || '—'}</td>
                    <td className="px-4 py-2.5 text-slate-400 dark:text-slate-500 font-mono text-xs">{k.kundennummer || '—'}</td>
                    <td className="px-4 py-2.5">
                      <div className="flex gap-2 justify-end" onClick={(e) => e.stopPropagation()}>
                        <button onClick={() => openEdit(k)} className="text-xs text-blue-600 dark:text-blue-400 hover:underline">Bearbeiten</button>
                        <button onClick={() => handleDelete(k)} className="text-xs text-red-500 dark:text-red-400 hover:underline">Löschen</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          </div>
        </div>

        {/* Stammdaten-Karte des ausgewählten Kunden */}
        {selected && (
          <div className="shrink-0 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 px-4 py-3">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">{kundeName(selected)}</span>
                {selected.ist_verein && <span className="text-xs px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700">Verein</span>}
                {selected.ist_gemeinnuetzig && <span className="text-xs px-1.5 py-0.5 rounded-full bg-green-100 text-green-700">Gemeinnützig</span>}
              </div>
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
              {selected.kundennummer && (
                <div><span className="text-slate-400 dark:text-slate-500 block">Kundennr.</span><span className="text-slate-700 dark:text-slate-200 font-mono">{selected.kundennummer}</span></div>
              )}
            </div>
            {selected.notizen && (
              <p className="mt-2 text-xs text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-700 px-2 py-1.5 whitespace-pre-wrap">{selected.notizen}</p>
            )}
          </div>
        )}
      </div>

      {/* ── Rechte Spalte (Rechnungen oder Formular) ─────────────────── */}
      {!showForm && (
        <div className="w-80 shrink-0">
          {selected ? (
            <KundeRechnungen key={selected.id} kunde={selected} />
          ) : (
            <div className="flex items-center justify-center h-full text-slate-400 dark:text-slate-500 text-sm">
              Kunden auswählen
            </div>
          )}
        </div>
      )}

      {/* ── Formular-Panel ───────────────────────────────────────────── */}
      {showForm && (
        <div className="flex-1 border-l border-slate-200 dark:border-slate-700 overflow-y-auto">
          <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between shrink-0">
            <h3 className="font-semibold text-slate-800 dark:text-slate-100">
              {editKunde ? 'Kunde bearbeiten' : 'Neuer Kunde'}
            </h3>
            <button onClick={closeForm} className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-xl leading-none">×</button>
          </div>
          <div className="p-6 max-w-lg">
            {deleteFehlgeschlagen && (
              <div className="mb-4 bg-amber-50 dark:bg-amber-950 border border-amber-300 dark:border-amber-800 rounded-lg px-4 py-3 text-sm text-amber-800 dark:text-amber-300">
                <p className="font-medium">Löschen nicht möglich</p>
                <p className="mt-0.5">Dieser Kunde hat verknüpfte Buchungen oder Rechnungen. Verwende <strong>„Anonymisieren (Art. 17)"</strong>.</p>
              </div>
            )}
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Firmenname</label>
                  <input type="text" {...register('firmenname')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
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
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Kundennummer</label>
                  <input type="text" {...register('kundennummer')} placeholder="Wird automatisch vergeben" className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">USt-IdNr.</label>
                  <input type="text" {...register('ust_idnr')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Notizen</label>
                  <textarea {...register('notizen')} rows={2} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                </div>
                <div className="col-span-2 flex gap-4">
                  <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 cursor-pointer">
                    <input type="checkbox" {...register('ist_verein')} className="rounded" /> Verein
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 cursor-pointer">
                    <input type="checkbox" {...register('ist_gemeinnuetzig')} className="rounded" /> Gemeinnützig
                  </label>
                </div>
              </div>

              {mutationError && <p className="text-red-600 text-sm">{(mutationError as Error).message}</p>}

              <div className="flex gap-3 pt-2">
                <button type="button" onClick={closeForm} className="flex-1 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-700">Abbrechen</button>
                <button type="submit" disabled={isPending} className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
                  {isPending ? 'Speichert…' : 'Speichern'}
                </button>
              </div>

              {editKunde?.id && !anonymisierungResult && (
                <div className="border-t border-slate-200 dark:border-slate-700 pt-3 space-y-2">
                  <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide">Datenschutz (DSGVO)</p>
                  {!showDsgvoBestaetigung ? (
                    <div className="flex gap-2">
                      <button type="button" onClick={() => dsgvoExportKunde(editKunde.id!)}
                        className="flex-1 text-xs border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg py-1.5 hover:bg-slate-50 dark:hover:bg-slate-700">
                        📥 Datenauskunft exportieren
                      </button>
                      <button type="button" onClick={() => setShowDsgvoBestaetigung(true)}
                        className="flex-1 text-xs border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 rounded-lg py-1.5 hover:bg-red-50 dark:hover:bg-red-950">
                        🗑 Anonymisieren (Art. 17)
                      </button>
                    </div>
                  ) : (
                    <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg p-3 space-y-2">
                      <p className="text-sm font-medium text-red-800 dark:text-red-300">Kunden wirklich anonymisieren?</p>
                      <ul className="text-xs text-red-700 dark:text-red-400 space-y-0.5 list-disc list-inside">
                        <li>Kundenstammdaten werden dauerhaft gelöscht</li>
                        <li>Verknüpfungen in Buchungen und Rechnungen werden entfernt</li>
                        <li>Immutable Kassenbucheinträge bleiben erhalten (§147 AO)</li>
                      </ul>
                      {anonymisierungMutation.isError && (
                        <p className="text-xs text-red-600 dark:text-red-400">{(anonymisierungMutation.error as Error).message}</p>
                      )}
                      <div className="flex gap-2 pt-1">
                        <button type="button" onClick={() => anonymisierungMutation.mutate(editKunde.id!)}
                          disabled={anonymisierungMutation.isPending}
                          className="flex-1 bg-red-600 text-white rounded-lg py-1.5 text-xs font-medium hover:bg-red-700 disabled:opacity-50">
                          {anonymisierungMutation.isPending ? '…' : 'Jetzt anonymisieren'}
                        </button>
                        <button type="button" onClick={() => setShowDsgvoBestaetigung(false)}
                          className="flex-1 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg py-1.5 text-xs hover:bg-slate-50 dark:hover:bg-slate-700">
                          Abbrechen
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {anonymisierungResult && (
                <div className="border-t border-slate-200 dark:border-slate-700 pt-3">
                  <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg p-3 space-y-1">
                    <p className="text-sm font-medium text-green-800 dark:text-green-300">Anonymisierung abgeschlossen</p>
                    <p className="text-xs text-green-700 dark:text-green-400">
                      {anonymisierungResult.anonymisierte_buchungen} Buchung(en) und {anonymisierungResult.anonymisierte_rechnungen} Rechnung(en) anonymisiert.
                    </p>
                    {anonymisierungResult.unveraenderlich_verblieben > 0 && (
                      <p className="text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded px-2 py-1 mt-1">
                        ⚠ {anonymisierungResult.hinweis}
                      </p>
                    )}
                  </div>
                  <button type="button" onClick={closeForm}
                    className="w-full mt-2 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-700">
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
