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
// Detail-Panel
// ---------------------------------------------------------------------------

function KundeDetail({
  kunde,
  onEdit,
  onDelete,
}: {
  kunde: Kunde
  onEdit: () => void
  onDelete: () => void
}) {
  const [offeneRechnung, setOffeneRechnung] = useState<number | null>(null)

  const { data: rechnungen, isLoading } = useQuery({
    queryKey: ['kunden-rechnungen', kunde.id],
    queryFn: () => getRechnungen({ typ: 'ausgang', kunde_id: kunde.id }),
    staleTime: 1000 * 60,
  })

  const adresse = [
    kunde.strasse && kunde.hausnummer ? `${kunde.strasse} ${kunde.hausnummer}` : kunde.strasse,
    kunde.plz && kunde.ort ? `${kunde.plz} ${kunde.ort}` : kunde.ort,
    kunde.land !== 'DE' ? kunde.land : undefined,
  ].filter(Boolean).join(', ')

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-100 shrink-0">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              {kunde.ist_verein && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">Verein</span>
              )}
              {kunde.ist_gemeinnuetzig && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">Gemeinnützig</span>
              )}
            </div>
            <h3 className="font-bold text-slate-800 text-base">{kundeName(kunde)}</h3>
            {kunde.kundennummer && (
              <p className="text-xs text-slate-400 font-mono">{kunde.kundennummer}</p>
            )}
          </div>
          <div className="flex gap-2 shrink-0">
            <button onClick={onEdit} className="text-xs text-blue-600 hover:underline">Bearbeiten</button>
            <button onClick={onDelete} className="text-xs text-red-500 hover:underline">Löschen</button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5">
        {/* Kontaktdaten */}
        <div className="grid grid-cols-2 gap-3">
          {adresse && (
            <div className="bg-slate-50 rounded-lg px-3 py-2 col-span-2">
              <p className="text-xs text-slate-500 mb-0.5">Adresse</p>
              <p className="text-sm text-slate-700">{adresse}</p>
            </div>
          )}
          {kunde.email && (
            <div className="bg-slate-50 rounded-lg px-3 py-2">
              <p className="text-xs text-slate-500 mb-0.5">E-Mail</p>
              <p className="text-sm text-slate-700">{kunde.email}</p>
            </div>
          )}
          {kunde.telefon && (
            <div className="bg-slate-50 rounded-lg px-3 py-2">
              <p className="text-xs text-slate-500 mb-0.5">Telefon</p>
              <p className="text-sm text-slate-700">{kunde.telefon}</p>
            </div>
          )}
          {kunde.ust_idnr && (
            <div className="bg-slate-50 rounded-lg px-3 py-2">
              <p className="text-xs text-slate-500 mb-0.5">USt-IdNr.</p>
              <p className="text-sm text-slate-700 font-mono">{kunde.ust_idnr}</p>
            </div>
          )}
        </div>

        {kunde.notizen && (
          <div className="text-sm text-slate-600 bg-slate-50 rounded-lg p-3 whitespace-pre-wrap">
            {kunde.notizen}
          </div>
        )}

        {/* Rechnungen */}
        <div>
          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
            Rechnungen ({rechnungen?.length ?? '…'})
          </h4>
          {isLoading && <p className="text-xs text-slate-400">Lade…</p>}
          {!isLoading && !rechnungen?.length && (
            <p className="text-xs text-slate-400">Noch keine Ausgangsrechnungen.</p>
          )}
          <div className="space-y-1.5">
            {rechnungen?.map((r: Rechnung) => (
              <div key={r.id} className="border border-slate-200 rounded-lg overflow-hidden">
                <button
                  type="button"
                  onClick={() => setOffeneRechnung(offeneRechnung === r.id ? null : r.id)}
                  className="w-full flex items-center justify-between px-3 py-2 text-xs hover:bg-slate-50 text-left"
                >
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-slate-400">{r.rechnungsnummer ?? '—'}</span>
                    <span className="font-semibold text-slate-700">{formatEuro(r.brutto_gesamt)}</span>
                    <span className="text-slate-400">{formatDatum(r.datum)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded-full border ${
                      r.zahlungsstatus === 'bezahlt' ? 'bg-green-50 text-green-700 border-green-200'
                      : r.zahlungsstatus === 'teilweise' ? 'bg-amber-50 text-amber-700 border-amber-200'
                      : 'bg-red-50 text-red-700 border-red-200'
                    }`}>
                      {r.zahlungsstatus === 'bezahlt' ? 'Bezahlt' : r.zahlungsstatus === 'teilweise' ? 'Teilweise' : 'Offen'}
                    </span>
                    <span className="text-slate-400">{offeneRechnung === r.id ? '▲' : '▼'}</span>
                  </div>
                </button>

                {offeneRechnung === r.id && r.positionen.length > 0 && (
                  <div className="border-t border-slate-100 bg-slate-50 px-3 py-2">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-slate-400 border-b border-slate-200">
                          <th className="py-1 text-left font-medium">Artikel / Beschreibung</th>
                          <th className="py-1 text-right font-medium">Menge</th>
                          <th className="py-1 text-right font-medium">Brutto</th>
                        </tr>
                      </thead>
                      <tbody>
                        {r.positionen.map((p) => (
                          <tr key={p.id} className="border-t border-slate-100">
                            <td className="py-1.5 text-slate-700">
                              {p.beschreibung}
                              {p.artikel_id && (
                                <span className="ms-1.5 text-slate-400 bg-slate-200 rounded px-1 py-0.5 text-[10px]">Artikel</span>
                              )}
                            </td>
                            <td className="py-1.5 text-right text-slate-500">{p.menge} {p.einheit}</td>
                            <td className="py-1.5 text-right text-slate-700">{formatEuro(p.brutto)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
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
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: ['kunden'] })
      setSelected(updated)
      closeForm()
    },
  })
  const deleteMutation = useMutation({
    mutationFn: (k: Kunde) => deleteKunde(k.id!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kunden'] })
      setSelected(null)
    },
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
    if (!window.confirm(`Kunden "${kundeName(k)}" löschen?`)) return
    deleteMutation.mutate(k)
  }

  const isPending = createMutation.isPending || updateMutation.isPending
  const mutationError = createMutation.error || updateMutation.error

  return (
    <div className="flex h-full">
      {/* Linke Spalte – Kundenliste */}
      <div className="w-72 border-e border-slate-200 bg-white flex flex-col shrink-0">
        <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
          <h2 className="font-semibold text-slate-800">Kunden</h2>
          <button
            onClick={openCreate}
            className="bg-blue-600 text-white rounded-lg px-3 py-1.5 text-xs font-medium hover:bg-blue-700"
          >
            + Neu
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {isLoading && <p className="text-slate-400 text-sm p-4">Lade…</p>}
          {!isLoading && !kunden?.length && (
            <p className="text-slate-400 text-sm p-4">Noch keine Kunden.</p>
          )}
          {kunden?.map((k) => (
            <button
              key={k.id}
              onClick={() => setSelected(k)}
              className={`w-full text-left px-4 py-3 border-b border-slate-100 last:border-0 transition-colors ${
                selected?.id === k.id
                  ? 'bg-blue-50 border-e-2 border-e-blue-600'
                  : 'hover:bg-slate-50'
              }`}
            >
              <p className={`text-sm font-medium truncate ${selected?.id === k.id ? 'text-blue-700' : 'text-slate-800'}`}>
                {kundeName(k)}
              </p>
              {k.kundennummer && (
                <p className="text-xs text-slate-400 font-mono">{k.kundennummer}</p>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Rechte Spalte – Detail */}
      <div className="flex-1 overflow-hidden">
        {selected ? (
          <KundeDetail
            key={selected.id}
            kunde={selected}
            onEdit={() => openEdit(selected)}
            onDelete={() => handleDelete(selected)}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-slate-400 text-sm">
            Kunden auswählen
          </div>
        )}
      </div>

      {/* Bearbeiten-Modal */}
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
                  <input type="text" {...register('kundennummer')} placeholder="Wird automatisch vergeben" className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
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

              {/* DSGVO-Aktionen */}
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
