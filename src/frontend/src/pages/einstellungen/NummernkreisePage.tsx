import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getNummernkreise, updateNummernkreis, getNummernkreisVorschau, type Nummernkreis } from '../../api/client'

const FORMAT_BEISPIELE = [
  { label: 'YY#### (z.B. 260001)', value: 'YY####' },
  { label: 'YYYY-#### (z.B. 2026-0001)', value: 'YYYY-####' },
  { label: 'YYYY/#### (z.B. 2026/0001)', value: 'YYYY/####' },
  { label: 'YYYY-MM-#### (z.B. 2026-04-0001)', value: 'YYYY-MM-####' },
  { label: 'YYYY-MM-TT-#### (z.B. 2026-04-25-001)', value: 'YYYY-MM-TT-####' },
  { label: '########## (nur Nummer, z.B. 000001)', value: '######' },
]

interface EditState {
  bezeichnung: string
  format: string
  naechste_nr: number
  reset_jaehrlich: boolean
}

export function NummernkreisePage() {
  const qc = useQueryClient()
  const [editId, setEditId] = useState<number | null>(null)
  const [editState, setEditState] = useState<EditState | null>(null)


  const { data: nummernkreise, isLoading } = useQuery({
    queryKey: ['nummernkreise'],
    queryFn: getNummernkreise,
  })

  const mutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Nummernkreis> }) =>
      updateNummernkreis(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['nummernkreise'] })
      setEditId(null)
      setEditState(null)
    },
  })

  const vorschauQuery = useQuery({
    queryKey: ['nummernkreis-vorschau', editId, editState?.format],
    queryFn: () => getNummernkreisVorschau(editId!, editState!.format),
    enabled: !!editId && !!editState?.format && editState.format.includes('#'),
  })

  function openEdit(nk: Nummernkreis) {
    setEditId(nk.id)
    setEditState({
      bezeichnung: nk.bezeichnung,
      format: nk.format,
      naechste_nr: nk.naechste_nr,
      reset_jaehrlich: nk.reset_jaehrlich,
    })
  }

  function handleSave() {
    if (!editId || !editState) return
    mutation.mutate({ id: editId, data: editState })
  }

  const liveVorschau = vorschauQuery.data?.vorschau ?? ''

  return (
    <div className="p-6 max-w-2xl">
      <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">Nummernkreise</h2>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        Lege fest, wie Belegnummern aufgebaut werden.
        <span className="ml-1 font-mono bg-slate-100 dark:bg-slate-700 dark:text-slate-300 px-1 rounded text-xs">YY</span> = Jahreszahl 2-stellig,
        <span className="ml-1 font-mono bg-slate-100 dark:bg-slate-700 dark:text-slate-300 px-1 rounded text-xs">YYYY</span> = 4-stellig,
        <span className="ml-1 font-mono bg-slate-100 dark:bg-slate-700 dark:text-slate-300 px-1 rounded text-xs">MM</span> = Monat,
        <span className="ml-1 font-mono bg-slate-100 dark:bg-slate-700 dark:text-slate-300 px-1 rounded text-xs">TT</span> = Tag,
        <span className="ml-1 font-mono bg-slate-100 dark:bg-slate-700 dark:text-slate-300 px-1 rounded text-xs">#</span> = Nummernstelle (Anzahl bestimmt Stellen)
      </p>

      {isLoading ? (
        <p className="text-slate-400 text-sm">Lade…</p>
      ) : (
        <div className="space-y-4">
          {(nummernkreise ?? []).map((nk) => (
            <div key={nk.id} className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
              {editId === nk.id && editState ? (
                /* Bearbeitungs-Modus */
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Bezeichnung</label>
                    <input
                      type="text"
                      value={editState.bezeichnung}
                      onChange={(e) => setEditState({ ...editState, bezeichnung: e.target.value })}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Format</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={editState.format}
                        onChange={(e) => setEditState({ ...editState, format: e.target.value })}
                        className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
                        placeholder="z.B. YY####"
                      />
                      <select
                        onChange={(e) => e.target.value && setEditState({ ...editState, format: e.target.value })}
                        className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
                        value=""
                      >
                        <option value="">Vorlage…</option>
                        {FORMAT_BEISPIELE.map((b) => (
                          <option key={b.value} value={b.value}>{b.label}</option>
                        ))}
                      </select>
                    </div>
                    {liveVorschau && (
                      <p className="mt-1.5 text-xs text-slate-500">
                        Vorschau nächste Nummer:
                        <span className="ml-1.5 font-mono font-semibold text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-950 px-1.5 py-0.5 rounded">
                          {liveVorschau}
                        </span>
                      </p>
                    )}
                    {editState.format && !editState.format.includes('#') && (
                      <p className="mt-1 text-xs text-red-500">Format muss mindestens ein '#' enthalten</p>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Nächste Nummer</label>
                      <input
                        type="number"
                        min={1}
                        value={editState.naechste_nr}
                        onChange={(e) => setEditState({ ...editState, naechste_nr: parseInt(e.target.value) || 1 })}
                        className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
                      />
                    </div>
                    <div className="flex items-end pb-2">
                      <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={editState.reset_jaehrlich}
                          onChange={(e) => setEditState({ ...editState, reset_jaehrlich: e.target.checked })}
                          className="rounded"
                        />
                        Jährlich zurücksetzen
                      </label>
                    </div>
                  </div>

                  {mutation.isError && (
                    <p className="text-red-600 text-sm">{(mutation.error as Error).message}</p>
                  )}

                  <div className="flex gap-3 pt-1">
                    <button
                      onClick={() => { setEditId(null); setEditState(null) }}
                      className="flex-1 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-700"
                    >
                      Abbrechen
                    </button>
                    <button
                      onClick={handleSave}
                      disabled={mutation.isPending || !editState.format.includes('#')}
                      className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                    >
                      {mutation.isPending ? 'Speichert…' : 'Speichern'}
                    </button>
                  </div>
                </div>
              ) : (
                /* Anzeige-Modus */
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-slate-800 dark:text-slate-100">{nk.bezeichnung}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="font-mono text-sm text-slate-500 dark:text-slate-400">{nk.format}</span>
                      {nk.vorschau && (
                        <span className="text-xs text-slate-400 dark:text-slate-500">
                          → nächste: <span className="font-mono font-semibold text-slate-600 dark:text-slate-300">{nk.vorschau}</span>
                        </span>
                      )}
                      {nk.reset_jaehrlich && (
                        <span className="text-xs text-slate-400 dark:text-slate-500 bg-slate-100 dark:bg-slate-700 px-1.5 py-0.5 rounded">jährlicher Reset</span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => openEdit(nk)}
                    className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    Bearbeiten
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
