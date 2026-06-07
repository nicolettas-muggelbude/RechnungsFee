import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { berechneZM, getUnternehmen, type ZMErgebnis } from '../../api/client'

const MONATE = ['', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']

function euroFmt(v: string | number): string {
  const n = typeof v === 'string' ? parseFloat(v) : v
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n)
}

function datumFmt(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

export function ZMPage() {
  const now = new Date()
  const [modus, setModus] = useState<'quartal' | 'monat'>('quartal')
  const [jahr, setJahr] = useState(now.getFullYear())
  const [quartal, setQuartal] = useState(Math.max(1, Math.ceil((now.getMonth() + 1) / 3) - 1) || 4)
  const [monat, setMonat] = useState(now.getMonth() === 0 ? 12 : now.getMonth())

  const zeitraum = modus === 'quartal'
    ? `${quartal === 4 && modus === 'quartal' && now.getMonth() < 3 ? jahr - 1 : jahr}-Q${quartal}`
    : `${monat === 12 && now.getMonth() < 1 ? jahr - 1 : jahr}-${String(monat).padStart(2, '0')}`

  const { data: unt } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen })

  const { data: ergebnis, isLoading, error, refetch } = useQuery<ZMErgebnis>({
    queryKey: ['zm-berechnen', zeitraum],
    queryFn: () => berechneZM(zeitraum),
    enabled: false,
  })

  const jahre = Array.from({ length: 5 }, (_, i) => now.getFullYear() - i)

  if (unt?.ist_kleinunternehmer) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-4">Zusammenfassende Meldung (ZM)</h1>
        <div className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 text-sm text-slate-600 dark:text-slate-300">
          Als Kleinunternehmer nach §19 UStG bist du von der Zusammenfassenden Meldung befreit.
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">Zusammenfassende Meldung (ZM)</h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        §18a UStG – Meldepflicht für innergemeinschaftliche Lieferungen und Dienstleistungen.
        Einzureichen beim <a href="https://www.bzst.de" target="_blank" rel="noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline">BZSt</a> (über ELSTER).
      </p>

      {/* Zeitraum */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 mb-6">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Typ</label>
            <div className="flex rounded-lg border border-slate-200 dark:border-slate-600 overflow-hidden">
              {(['quartal', 'monat'] as const).map(m => (
                <button key={m} type="button" onClick={() => setModus(m)}
                  className={`px-3 py-1.5 text-sm font-medium transition-colors ${modus === m ? 'bg-blue-600 text-white' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'}`}>
                  {m === 'quartal' ? 'Quartal' : 'Monat'}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Jahr</label>
            <select value={jahr} onChange={e => setJahr(Number(e.target.value))}
              className="border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100">
              {jahre.map(j => <option key={j} value={j}>{j}</option>)}
            </select>
          </div>
          {modus === 'quartal' ? (
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Quartal</label>
              <select value={quartal} onChange={e => setQuartal(Number(e.target.value))}
                className="border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100">
                {[1, 2, 3, 4].map(q => <option key={q} value={q}>Q{q}</option>)}
              </select>
            </div>
          ) : (
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Monat</label>
              <select value={monat} onChange={e => setMonat(Number(e.target.value))}
                className="border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100">
                {MONATE.slice(1).map((m, i) => <option key={i + 1} value={i + 1}>{m}</option>)}
              </select>
            </div>
          )}
          <button onClick={() => refetch()} disabled={isLoading}
            className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors">
            {isLoading ? 'Berechne…' : 'Berechnen'}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl p-4 mb-6 text-sm text-red-700 dark:text-red-300">
          {(error as Error).message}
        </div>
      )}

      {ergebnis && (
        <>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="font-semibold text-slate-700 dark:text-slate-200">{ergebnis.zeitraum_label}</h2>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                Frist: {datumFmt(ergebnis.deadline)}
                {ergebnis.ueber_50k && (
                  <span className="ml-2 text-amber-600 dark:text-amber-400">
                    ⚠ Über 50.000 € – monatliche ZM erforderlich
                  </span>
                )}
              </p>
            </div>
          </div>

          {ergebnis.positionen.length === 0 ? (
            <div className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 text-sm text-slate-500 dark:text-slate-400 text-center">
              Keine innergemeinschaftlichen Lieferungen oder Dienstleistungen im Zeitraum.
            </div>
          ) : (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden mb-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-700/50">
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">USt-IdNr.</th>
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Land</th>
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Kennz.</th>
                    <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Betrag (Netto)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50 dark:divide-slate-700">
                  {ergebnis.positionen.map((p, i) => (
                    <tr key={i}>
                      <td className="px-4 py-3 font-mono text-slate-800 dark:text-slate-100">{p.ust_idnr || '—'}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{p.land || '—'}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center justify-center w-6 h-6 rounded text-xs font-bold text-white ${p.kennzeichen === 'L' ? 'bg-blue-600' : 'bg-purple-600'}`}>
                          {p.kennzeichen}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-medium tabular-nums text-slate-800 dark:text-slate-100">
                        {euroFmt(p.betrag)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-700/50">
                    <td colSpan={3} className="px-4 py-2.5 text-sm font-semibold text-slate-700 dark:text-slate-200">Gesamt</td>
                    <td className="px-4 py-2.5 text-right font-bold tabular-nums text-slate-800 dark:text-slate-100">{euroFmt(ergebnis.gesamt)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          )}

          <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-xl p-4 text-sm text-amber-800 dark:text-amber-200">
            <strong>L</strong> = Innergemeinschaftliche Lieferung · <strong>D</strong> = Dienstleistung §13b Abs. 1<br/>
            Melde die Beträge unter <a href="https://www.elster.de" target="_blank" rel="noreferrer" className="underline">ELSTER → Zusammenfassende Meldung</a> oder über das BZSt-Online-Portal.
          </div>
        </>
      )}
    </div>
  )
}
