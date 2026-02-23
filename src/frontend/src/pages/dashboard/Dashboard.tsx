import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getKassenbuch } from '../../api/client'

function formatEuro(val: string | number): string {
  const n = typeof val === 'string' ? parseFloat(val) : val
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n)
}

function formatDatum(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

function aktuellerMonat(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function heuteIso(): string {
  return new Date().toISOString().slice(0, 10)
}

type FilterModus = 'monat' | 'datum' | 'zeitraum'

export function Dashboard() {
  const [filterModus, setFilterModus] = useState<FilterModus>('monat')
  const [monat, setMonat] = useState(aktuellerMonat)
  const [datum, setDatum] = useState(heuteIso)
  const [datumVon, setDatumVon] = useState(heuteIso)
  const [datumBis, setDatumBis] = useState(heuteIso)

  const filterParams =
    filterModus === 'monat'
      ? { monat }
      : filterModus === 'datum'
      ? { datum_von: datum, datum_bis: datum }
      : { datum_von: datumVon, datum_bis: datumBis }

  const { data: eintraege } = useQuery({
    queryKey: ['kassenbuch', filterModus, monat, datum, datumVon, datumBis],
    queryFn: () => getKassenbuch(filterParams),
  })

  const alle = eintraege ?? []
  const einnahmen = alle
    .filter((e) => e.art === 'Einnahme')
    .reduce((s, e) => s + parseFloat(e.brutto_betrag), 0)
  const ausgaben = alle
    .filter((e) => e.art === 'Ausgabe')
    .reduce((s, e) => s + parseFloat(e.brutto_betrag), 0)
  const saldo = einnahmen - ausgaben
  const letzte5 = alle.slice(0, 5)

  const loaded = eintraege !== undefined

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <h2 className="text-2xl font-bold text-slate-800">Dashboard</h2>

        {/* Zeitfilter */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-lg border border-slate-300 overflow-hidden text-sm">
            {(['monat', 'datum', 'zeitraum'] as FilterModus[]).map((m) => (
              <button
                key={m}
                onClick={() => setFilterModus(m)}
                className={`px-3 py-1.5 transition-colors ${
                  filterModus === m
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-slate-600 hover:bg-slate-50'
                }`}
              >
                {m === 'monat' ? 'Monat' : m === 'datum' ? 'Tag' : 'Zeitraum'}
              </button>
            ))}
          </div>

          {filterModus === 'monat' && (
            <input
              type="month"
              value={monat}
              onChange={(e) => setMonat(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          )}
          {filterModus === 'datum' && (
            <input
              type="date"
              value={datum}
              onChange={(e) => setDatum(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          )}
          {filterModus === 'zeitraum' && (
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={datumVon}
                onChange={(e) => setDatumVon(e.target.value)}
                className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-slate-400 text-sm">bis</span>
              <input
                type="date"
                value={datumBis}
                min={datumVon}
                onChange={(e) => setDatumBis(e.target.value)}
                className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}
        </div>
      </div>

      {/* Kacheln */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-sm text-slate-500 mb-1">Einnahmen</p>
          <p className="text-2xl font-bold text-green-600">
            {loaded ? formatEuro(einnahmen) : '—'}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-sm text-slate-500 mb-1">Ausgaben</p>
          <p className="text-2xl font-bold text-red-600">
            {loaded ? formatEuro(ausgaben) : '—'}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-sm text-slate-500 mb-1">Saldo</p>
          <p className={`text-2xl font-bold ${saldo >= 0 ? 'text-blue-600' : 'text-red-700'}`}>
            {loaded ? formatEuro(saldo) : '—'}
          </p>
        </div>
      </div>

      {/* Letzte Buchungen */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="px-5 py-3 border-b border-slate-100">
          <h3 className="font-semibold text-slate-700">Letzte Buchungen</h3>
        </div>
        {letzte5.length === 0 ? (
          <p className="text-slate-400 text-sm p-5">Keine Buchungen im gewählten Zeitraum.</p>
        ) : (
          <table className="w-full text-sm">
            <tbody>
              {letzte5.map((e) => (
                <tr key={e.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                  <td className="px-5 py-3 text-slate-500 w-28">{formatDatum(e.datum)}</td>
                  <td className="px-5 py-3 text-slate-400 w-32 font-mono text-xs">{e.belegnr}</td>
                  <td className="px-5 py-3 text-slate-700">{e.beschreibung}</td>
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
