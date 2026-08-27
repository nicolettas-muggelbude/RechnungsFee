import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getKontokorrentUebersicht, type PartnerSaldo } from '../../api/client'
import { useMxAuto } from '../../hooks/useAnsicht'

function formatEuro(val: number): string {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(val)
}

type Filter = 'alle' | 'offen' | 'guthaben'

export function KontokorrentUebersichtPage() {
  const mxAuto = useMxAuto()
  const navigate = useNavigate()
  const [filter, setFilter] = useState<Filter>('alle')

  const { data = [], isLoading } = useQuery({
    queryKey: ['kontokorrent-uebersicht'],
    queryFn: getKontokorrentUebersicht,
    staleTime: 1000 * 30,
  })

  const gefiltert = filter === 'alle' ? data : data.filter(p => p.status === filter)

  const summeOffen = data.filter(p => p.status === 'offen').reduce((s, p) => s + p.saldo, 0)
  const summeGuthaben = data.filter(p => p.status === 'guthaben').reduce((s, p) => s + Math.abs(p.saldo), 0)

  function oeffnen(p: PartnerSaldo) {
    const pfad = p.partner_typ === 'kunde' ? '/kunden' : '/lieferanten'
    navigate(`${pfad}?open=${p.partner_id}&tab=kontokorrent`)
  }

  return (
    <div className={`max-w-3xl ${mxAuto} px-6 py-8`}>
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">
        Kontokorrent-Übersicht
      </h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        Alle Kunden und Lieferanten mit offenem Saldo auf einen Blick, statt jeden Partner einzeln zu öffnen.
      </p>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
          <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wide">Offene Salden gesamt</p>
          <p className="text-xl font-bold text-slate-800 dark:text-slate-100 mt-1">{formatEuro(summeOffen)}</p>
        </div>
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
          <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wide">Guthaben gesamt</p>
          <p className="text-xl font-bold text-green-600 dark:text-green-400 mt-1">{formatEuro(summeGuthaben)}</p>
        </div>
      </div>

      <div className="flex gap-2 mb-3">
        {(['alle', 'offen', 'guthaben'] as Filter[]).map(f => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
              filter === f
                ? 'bg-blue-600 border-blue-600 text-white'
                : 'border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
            }`}
          >
            {f === 'alle' ? 'Alle' : f === 'offen' ? 'Offen' : 'Guthaben'}
          </button>
        ))}
      </div>

      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
        {isLoading && <p className="p-4 text-sm text-slate-400">Lade…</p>}
        {!isLoading && gefiltert.length === 0 && (
          <p className="p-4 text-sm text-slate-400 italic">Keine Partner mit offenem Saldo.</p>
        )}
        {gefiltert.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-900 text-slate-500 dark:text-slate-400 text-[10px] uppercase tracking-wide">
                <th className="text-left px-4 py-2">Partner</th>
                <th className="text-left px-4 py-2">Typ</th>
                <th className="text-right px-4 py-2">Saldo</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
              {gefiltert.map(p => (
                <tr
                  key={`${p.partner_typ}-${p.partner_id}`}
                  onClick={() => oeffnen(p)}
                  className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/50"
                >
                  <td className="px-4 py-2.5 text-slate-800 dark:text-slate-100">{p.name}</td>
                  <td className="px-4 py-2.5">
                    <span className="text-[10px] px-1.5 py-0.5 rounded border border-slate-200 dark:border-slate-600 text-slate-500 dark:text-slate-400">
                      {p.partner_typ === 'kunde' ? 'Kunde' : 'Lieferant'}
                    </span>
                  </td>
                  <td className={`px-4 py-2.5 text-right font-mono font-semibold ${
                    p.status === 'guthaben' ? 'text-green-600 dark:text-green-400' : 'text-slate-700 dark:text-slate-200'
                  }`}>
                    {formatEuro(p.saldo)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
