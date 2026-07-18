import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { berechneKontenuebersicht, getKontenuebersichtExportUrl, openUrl, type KontenuebersichtErgebnis } from '../../api/client'
import { useMxAuto } from '../../hooks/useAnsicht'
import { DateInput } from '../../components/DateInput'
import { ExportButtons } from '../../components/ExportButtons'

function euroFmt(v: string): string {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(parseFloat(v))
}

type FilterModus = 'jahr' | 'monat' | 'zeitraum'

function aktuellerMonat(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function letzterTagDesMonats(monat: string): string {
  const [y, m] = monat.split('-').map(Number)
  return `${y}-${String(m).padStart(2, '0')}-${String(new Date(y, m, 0).getDate()).padStart(2, '0')}`
}

export function KontenuebersichtPage() {
  const mxAuto = useMxAuto()
  const now = new Date()
  const [filterModus, setFilterModus] = useState<FilterModus>('jahr')
  const [jahr, setJahr] = useState(now.getFullYear())
  const jahre = Array.from({ length: 6 }, (_, i) => now.getFullYear() - i)
  const [monat, setMonat] = useState(aktuellerMonat())
  const [datumVon, setDatumVon] = useState(`${now.getFullYear()}-01-01`)
  const [datumBis, setDatumBis] = useState(now.toISOString().slice(0, 10))

  const { von, bis } = filterModus === 'monat'
    ? { von: `${monat}-01`, bis: letzterTagDesMonats(monat) }
    : filterModus === 'zeitraum'
      ? { von: datumVon, bis: datumBis }
      : { von: `${jahr}-01-01`, bis: `${jahr}-12-31` }

  const { data: ergebnis, isLoading, error } = useQuery<KontenuebersichtErgebnis>({
    queryKey: ['kontenuebersicht-berechnen', von, bis],
    queryFn: () => berechneKontenuebersicht(von, bis),
  })

  const gesamtsumme = ergebnis?.zeilen.reduce((s, z) => s + parseFloat(z.summe), 0) ?? 0

  async function handleExport(format: 'pdf' | 'csv') {
    const url = await getKontenuebersichtExportUrl(von, bis, format)
    await openUrl(url)
  }

  return (
    <div className={`max-w-3xl ${mxAuto} px-6 py-8`}>
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">
        Kontenübersicht
      </h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        Alle im Zeitraum gebuchten Kategorien mit {ergebnis?.kontenrahmen ?? 'SKR'}-Kontonummer, Anzahl Buchungen und Summe.
        Für das Kontenblatt zu einem einzelnen Konto nutze den Journal-Filter.
      </p>

      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 mb-6">
        <div className="flex flex-wrap gap-3 items-center">
          <div className="flex rounded-lg border border-slate-300 dark:border-slate-600 overflow-hidden text-sm">
            {(['jahr', 'monat', 'zeitraum'] as FilterModus[]).map(m => (
              <button
                key={m}
                onClick={() => setFilterModus(m)}
                className={`px-3 py-1.5 capitalize transition-colors ${
                  filterModus === m
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-slate-600 hover:bg-slate-50 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
                }`}
              >
                {m === 'jahr' ? 'Jahr' : m === 'monat' ? 'Monat' : 'Zeitraum'}
              </button>
            ))}
          </div>

          {filterModus === 'jahr' && (
            <select
              value={jahr}
              onChange={e => setJahr(Number(e.target.value))}
              className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100"
            >
              {jahre.map(j => <option key={j} value={j}>{j}</option>)}
            </select>
          )}
          {filterModus === 'monat' && (
            <input
              type="month"
              value={monat}
              onChange={e => setMonat(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
            />
          )}
          {filterModus === 'zeitraum' && (
            <div className="flex items-center gap-2">
              <DateInput
                value={datumVon}
                onChange={setDatumVon}
                className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
              />
              <span className="text-slate-400 dark:text-slate-500 text-sm">bis</span>
              <DateInput
                value={datumBis}
                min={datumVon}
                onChange={setDatumBis}
                className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
              />
            </div>
          )}

          {isLoading && <span className="text-sm text-slate-500 dark:text-slate-400">Berechne…</span>}

          {ergebnis && ergebnis.zeilen.length > 0 && (
            <div className="ml-auto">
              <ExportButtons onExport={handleExport} />
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl p-4 mb-6 text-sm text-red-700 dark:text-red-300">
          {(error as Error).message}
        </div>
      )}

      {ergebnis && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-700/50 border-b border-slate-200 dark:border-slate-700 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                <th className="text-left px-4 py-2">Kategorie</th>
                <th className="text-left px-4 py-2">Konto</th>
                <th className="text-right px-4 py-2">Buchungen</th>
                <th className="text-right px-4 py-2">Summe</th>
              </tr>
            </thead>
            <tbody>
              {ergebnis.zeilen.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-slate-500 dark:text-slate-400">
                    Keine Buchungen im gewählten Zeitraum.
                  </td>
                </tr>
              )}
              {ergebnis.zeilen.map(z => (
                <tr key={z.kategorie_id} className="border-b border-slate-100 dark:border-slate-700 text-slate-700 dark:text-slate-300">
                  <td className="px-4 py-2">{z.kategorie_name}</td>
                  <td className="px-4 py-2 tabular-nums text-slate-500 dark:text-slate-400">{z.kontonummer ?? '–'}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{z.anzahl}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{euroFmt(z.summe)}</td>
                </tr>
              ))}
            </tbody>
            {ergebnis.zeilen.length > 0 && (
              <tfoot>
                <tr className="bg-slate-50 dark:bg-slate-700/50 font-semibold text-slate-800 dark:text-slate-100">
                  <td className="px-4 py-2.5" colSpan={3}>Gesamtsumme</td>
                  <td className="px-4 py-2.5 text-right tabular-nums">
                    {euroFmt(gesamtsumme.toFixed(2))}
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      )}
    </div>
  )
}
