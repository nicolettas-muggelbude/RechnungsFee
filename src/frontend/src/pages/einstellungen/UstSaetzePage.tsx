import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getUstSaetze, createUstSatz, updateUstSatz, deleteUstSatz,
  type UstSatz,
} from '../../api/client'

function formatSatz(satz: string): string {
  return parseFloat(satz).toLocaleString('de-DE', { minimumFractionDigits: 0, maximumFractionDigits: 2 }) + ' %'
}

export function UstSaetzePage() {
  const qc = useQueryClient()
  const [neuerSatz, setNeuerSatz] = useState('')
  const [neueBez, setNeueBez] = useState('')
  const [fehler, setFehler] = useState('')

  const { data: saetze = [], isLoading } = useQuery({
    queryKey: ['ust-saetze'],
    queryFn: getUstSaetze,
  })

  const createMut = useMutation({
    mutationFn: createUstSatz,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ust-saetze'] })
      setNeuerSatz('')
      setNeueBez('')
      setFehler('')
    },
    onError: (e: Error) => setFehler(e.message),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateUstSatz>[1] }) =>
      updateUstSatz(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ust-saetze'] }),
  })

  const deleteMut = useMutation({
    mutationFn: deleteUstSatz,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ust-saetze'] }),
    onError: (e: Error) => setFehler(e.message),
  })

  function handleAdd() {
    const satzNum = parseFloat(neuerSatz.replace(',', '.'))
    if (isNaN(satzNum) || satzNum < 0 || satzNum > 100) {
      setFehler('Bitte einen gültigen Steuersatz zwischen 0 und 100 eingeben.')
      return
    }
    setFehler('')
    createMut.mutate({ satz: satzNum.toFixed(2), bezeichnung: neueBez || undefined })
  }

  function setDefault(id: number) {
    updateMut.mutate({ id, data: { ist_default: true } })
  }

  function toggleAktiv(s: UstSatz) {
    updateMut.mutate({ id: s.id, data: { ist_aktiv: !s.ist_aktiv } })
  }

  return (
    <div className="max-w-xl mx-auto py-8 px-4 space-y-6">
      <div>
        <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">MwSt.-Sätze</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
          Aktive Sätze erscheinen im Rechnungsformular und Artikelstamm. Der Standard-Satz wird automatisch vorausgefüllt.
        </p>
      </div>

      {isLoading && <p className="text-sm text-slate-400">Lade…</p>}

      <div className="divide-y divide-slate-100 dark:divide-slate-700 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
        {saetze.map((s) => (
          <div
            key={s.id}
            className={`flex items-center gap-3 px-4 py-3 ${s.ist_aktiv ? 'bg-white dark:bg-slate-800' : 'bg-slate-50 dark:bg-slate-900'}`}
          >
            {/* Satz + Bezeichnung */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`font-mono font-semibold ${s.ist_aktiv ? 'text-slate-800 dark:text-slate-100' : 'text-slate-400 dark:text-slate-500'}`}>
                  {formatSatz(s.satz)}
                </span>
                {s.bezeichnung && (
                  <span className="text-xs text-slate-500 dark:text-slate-400">{s.bezeichnung}</span>
                )}
                {s.ist_standard && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400">Standard</span>
                )}
              </div>
            </div>

            {/* Default-Button */}
            <button
              type="button"
              title={s.ist_default ? 'Ist der Standard-Satz' : 'Als Standard festlegen'}
              onClick={() => !s.ist_default && setDefault(s.id)}
              className={`text-sm px-2 py-1 rounded-lg border transition-colors ${
                s.ist_default
                  ? 'bg-blue-100 text-blue-700 border-blue-200 cursor-default dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800'
                  : 'border-slate-200 text-slate-400 hover:border-blue-300 hover:text-blue-600 dark:border-slate-700 dark:text-slate-500 dark:hover:border-blue-700 dark:hover:text-blue-400'
              }`}
            >
              {s.ist_default ? '★ Standard' : '☆ Standard'}
            </button>

            {/* Aktiv-Toggle */}
            <button
              type="button"
              onClick={() => toggleAktiv(s)}
              title={s.ist_aktiv ? 'Deaktivieren' : 'Aktivieren'}
              className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                s.ist_aktiv ? 'bg-blue-600' : 'bg-slate-300'
              }`}
            >
              <span
                className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
                  s.ist_aktiv ? 'translate-x-4' : 'translate-x-0.5'
                }`}
              />
            </button>

            {/* Löschen (nur nicht-Standard) */}
            <button
              type="button"
              onClick={() => {
                if (!window.confirm(`Steuersatz ${formatSatz(s.satz)} wirklich löschen?`)) return
                deleteMut.mutate(s.id)
              }}
              disabled={s.ist_standard}
              title={s.ist_standard ? 'Standard-Sätze können nicht gelöscht werden' : 'Löschen'}
              className="text-slate-300 hover:text-red-500 disabled:opacity-30 disabled:cursor-not-allowed text-lg leading-none"
            >
              ×
            </button>
          </div>
        ))}
      </div>

      {/* Neuen Satz hinzufügen */}
      <div className="border border-slate-200 dark:border-slate-700 rounded-xl p-4 space-y-3 dark:bg-slate-800">
        <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Neuen Steuersatz hinzufügen</p>
        <div className="flex gap-2">
          <div className="relative">
            <input
              type="text"
              inputMode="decimal"
              placeholder="z.B. 5,5"
              value={neuerSatz}
              onChange={(e) => setNeuerSatz(e.target.value)}
              className="w-28 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 pe-6 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100 dark:placeholder-slate-400"
            />
            <span className="absolute end-2 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500 text-sm">%</span>
          </div>
          <input
            type="text"
            placeholder="Bezeichnung (optional)"
            value={neueBez}
            onChange={(e) => setNeueBez(e.target.value)}
            className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100 dark:placeholder-slate-400"
          />
          <button
            type="button"
            onClick={handleAdd}
            disabled={!neuerSatz || createMut.isPending}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {createMut.isPending ? '…' : '+ Hinzufügen'}
          </button>
        </div>
        {fehler && <p className="text-xs text-red-600">{fehler}</p>}
      </div>
    </div>
  )
}
