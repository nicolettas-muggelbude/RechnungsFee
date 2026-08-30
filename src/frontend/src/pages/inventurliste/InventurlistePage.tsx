import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { berechneInventurliste, getInventurlisteExportUrl, openUrl, type InventurlisteErgebnis } from '../../api/client'
import { useMxAuto } from '../../hooks/useAnsicht'
import { DateInput } from '../../components/DateInput'
import { ExportButtons } from '../../components/ExportButtons'

function euroFmt(v: string): string {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(parseFloat(v))
}

export function InventurlistePage() {
  const mxAuto = useMxAuto()
  const [stichtag, setStichtag] = useState(new Date().toISOString().slice(0, 10))

  const { data: ergebnis, isLoading, error } = useQuery<InventurlisteErgebnis>({
    queryKey: ['inventurliste-berechnen', stichtag],
    queryFn: () => berechneInventurliste(stichtag),
  })

  async function handleExport(format: 'pdf' | 'csv') {
    const url = await getInventurlisteExportUrl(stichtag, format)
    await openUrl(url)
  }

  return (
    <div className={`max-w-3xl ${mxAuto} px-6 py-8`}>
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">
        Inventurliste
      </h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        Bestand und Wert aller Artikel mit aktiver Lagerführung zum gewählten Stichtag – als Nachweis für die Inventur (§240 HGB).
        Zeigt immer den aktuellen Bestand, keine rückwirkende Bestandshistorie.
      </p>

      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 mb-6">
        <div className="flex flex-wrap gap-3 items-center">
          <label className="text-sm text-slate-600 dark:text-slate-300">Stichtag</label>
          <DateInput
            value={stichtag}
            onChange={setStichtag}
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
          />

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
                <th className="text-left px-4 py-2">Artikelnr.</th>
                <th className="text-left px-4 py-2">Bezeichnung</th>
                <th className="text-right px-4 py-2">Bestand</th>
                <th className="text-right px-4 py-2">EK (netto)</th>
                <th className="text-right px-4 py-2">Wert (netto)</th>
              </tr>
            </thead>
            <tbody>
              {ergebnis.zeilen.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-slate-500 dark:text-slate-400">
                    Keine Artikel mit aktiver Lagerführung.
                  </td>
                </tr>
              )}
              {ergebnis.zeilen.map(z => (
                <tr key={z.artikel_id} className="border-b border-slate-100 dark:border-slate-700 text-slate-700 dark:text-slate-300">
                  <td className="px-4 py-2">{z.artikelnummer}</td>
                  <td className="px-4 py-2">{z.bezeichnung}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{z.bestand} {z.einheit}</td>
                  <td className="px-4 py-2 text-right tabular-nums text-slate-500 dark:text-slate-400">
                    {z.ek_netto !== null ? euroFmt(z.ek_netto) : '–'}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {z.wert !== null ? euroFmt(z.wert) : '–'}
                  </td>
                </tr>
              ))}
            </tbody>
            {ergebnis.zeilen.length > 0 && (
              <tfoot>
                <tr className="bg-slate-50 dark:bg-slate-700/50 font-semibold text-slate-800 dark:text-slate-100">
                  <td className="px-4 py-2.5" colSpan={4}>Gesamtwert</td>
                  <td className="px-4 py-2.5 text-right tabular-nums">
                    {euroFmt(ergebnis.gesamtwert)}
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
