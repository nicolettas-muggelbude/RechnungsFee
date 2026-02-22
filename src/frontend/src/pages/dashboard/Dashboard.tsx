import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getMonatsUebersicht, getKassenbuch } from '../../api/client'

function formatEuro(val: string | number): string {
  const n = typeof val === 'string' ? parseFloat(val) : val
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n)
}

function aktuellerMonat(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

export function Dashboard() {
  const [monat, setMonat] = useState(aktuellerMonat)

  const { data: stats } = useQuery({
    queryKey: ['monats-uebersicht', monat],
    queryFn: () => getMonatsUebersicht(monat),
  })

  const { data: eintraege } = useQuery({
    queryKey: ['kassenbuch', monat],
    queryFn: () => getKassenbuch({ monat }),
  })

  const letzte5 = (eintraege ?? []).slice(0, 5)

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-slate-800">Dashboard</h2>
        <input
          type="month"
          value={monat}
          onChange={(e) => setMonat(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Kacheln */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-sm text-slate-500 mb-1">Einnahmen</p>
          <p className="text-2xl font-bold text-green-600">
            {stats ? formatEuro(stats.einnahmen) : '—'}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-sm text-slate-500 mb-1">Ausgaben</p>
          <p className="text-2xl font-bold text-red-600">
            {stats ? formatEuro(stats.ausgaben) : '—'}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-sm text-slate-500 mb-1">Saldo</p>
          <p className={`text-2xl font-bold ${stats && parseFloat(stats.saldo) >= 0 ? 'text-blue-600' : 'text-red-700'}`}>
            {stats ? formatEuro(stats.saldo) : '—'}
          </p>
        </div>
      </div>

      {/* Letzte Buchungen */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="px-5 py-3 border-b border-slate-100">
          <h3 className="font-semibold text-slate-700">Letzte Buchungen</h3>
        </div>
        {letzte5.length === 0 ? (
          <p className="text-slate-400 text-sm p-5">Noch keine Buchungen in diesem Monat.</p>
        ) : (
          <table className="w-full text-sm">
            <tbody>
              {letzte5.map((e) => (
                <tr key={e.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                  <td className="px-5 py-3 text-slate-500 w-28">{e.datum}</td>
                  <td className="px-5 py-3 text-slate-400 w-32 font-mono text-xs">{e.belegnr}</td>
                  <td className="px-5 py-3 text-slate-700 flex-1">{e.beschreibung}</td>
                  <td className={`px-5 py-3 text-right font-medium ${e.art === 'Einnahme' ? 'text-green-600' : 'text-red-600'}`}>
                    {e.art === 'Ausgabe' ? '−' : '+'}{formatEuro(e.brutto_betrag)}
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
