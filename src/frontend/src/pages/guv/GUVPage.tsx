import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { berechneGUV, type GUVErgebnis } from '../../api/client'

function euroFmt(v: string | number): string {
  const n = typeof v === 'string' ? parseFloat(v) : v
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n)
}

export function GUVPage() {
  const now = new Date()
  const [jahr, setJahr] = useState(now.getFullYear() - (now.getMonth() < 3 ? 1 : 0))
  const jahre = Array.from({ length: 6 }, (_, i) => now.getFullYear() - i)

  const { data: ergebnis, isLoading, error } = useQuery<GUVErgebnis>({
    queryKey: ['guv-berechnen', jahr],
    queryFn: () => berechneGUV(jahr),
  })

  const ertraege     = ergebnis?.positionen.filter(p => p.typ === 'ertrag')  ?? []
  const aufwendungen = ergebnis?.positionen.filter(p => p.typ === 'aufwand') ?? []
  const jahresergebnis = ergebnis ? parseFloat(ergebnis.jahresergebnis) : 0

  return (
    <div className="max-w-2xl px-6 py-8">
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">
        GuV – Gewinn- und Verlustrechnung
      </h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        Näherung auf Basis der EÜR-Daten (Ist-Versteuerung). Für eine prüfungsfähige GuV nach §&nbsp;275 HGB ist ein Steuerberater hinzuzuziehen.
      </p>

      {/* Jahresauswahl */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 mb-6 flex items-center gap-4">
        <div>
          <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Wirtschaftsjahr</label>
          <select
            value={jahr}
            onChange={e => setJahr(Number(e.target.value))}
            className="border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100"
          >
            {jahre.map(j => <option key={j} value={j}>{j}</option>)}
          </select>
        </div>
        {isLoading && <span className="text-sm text-slate-500 dark:text-slate-400">Berechne…</span>}
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl p-4 mb-6 text-sm text-red-700 dark:text-red-300">
          {(error as Error).message}
        </div>
      )}

      {ergebnis && (
        <>
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden mb-4">

            {/* ── Erträge ─────────────────────────────────────────────── */}
            <div className="px-4 py-2 bg-slate-50 dark:bg-slate-700/50 border-b border-slate-200 dark:border-slate-700">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Erträge</span>
            </div>
            {ertraege.map(p => (
              <div key={p.nr} className="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 dark:border-slate-700 text-sm text-slate-700 dark:text-slate-300">
                <span className="text-slate-400 dark:text-slate-500 mr-3 tabular-nums w-4 shrink-0">{p.nr}.</span>
                <span className="flex-1">{p.bezeichnung}</span>
                <span className="tabular-nums ml-4">{euroFmt(p.betrag)}</span>
              </div>
            ))}
            <div className="flex items-center justify-between px-4 py-2.5 bg-emerald-50 dark:bg-emerald-950/40 border-t border-emerald-200 dark:border-emerald-800 font-semibold text-sm text-emerald-800 dark:text-emerald-300">
              <span>Summe Erträge</span>
              <span className="tabular-nums">{euroFmt(ergebnis.summe_ertraege)}</span>
            </div>

            {/* ── Aufwendungen ─────────────────────────────────────────── */}
            <div className="px-4 py-2 bg-slate-50 dark:bg-slate-700/50 border-t border-b border-slate-200 dark:border-slate-700">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Aufwendungen</span>
            </div>
            {aufwendungen.map(p => (
              <div key={p.nr} className="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 dark:border-slate-700 text-sm text-slate-700 dark:text-slate-300">
                <span className="text-slate-400 dark:text-slate-500 mr-3 tabular-nums w-4 shrink-0">{p.nr}.</span>
                <span className="flex-1">{p.bezeichnung}</span>
                <span className="tabular-nums ml-4 text-red-600 dark:text-red-400">
                  {parseFloat(p.betrag) > 0 ? '−' : ''}{euroFmt(p.betrag)}
                </span>
              </div>
            ))}
            <div className="flex items-center justify-between px-4 py-2.5 bg-red-50 dark:bg-red-950/40 border-t border-red-200 dark:border-red-800 font-semibold text-sm text-red-800 dark:text-red-300">
              <span>Summe Aufwendungen</span>
              <span className="tabular-nums">
                {parseFloat(ergebnis.summe_aufwendungen) > 0 ? '−' : ''}{euroFmt(ergebnis.summe_aufwendungen)}
              </span>
            </div>

            {/* ── Jahresergebnis ───────────────────────────────────────── */}
            <div className={`flex items-center justify-between px-4 py-3 font-bold text-base ${
              jahresergebnis >= 0
                ? 'bg-slate-800 dark:bg-slate-900 text-white'
                : 'bg-red-700 text-white'
            }`}>
              <span>{jahresergebnis >= 0 ? 'Jahresüberschuss (Gewinn)' : 'Jahresfehlbetrag (Verlust)'}</span>
              <span className="tabular-nums">{euroFmt(ergebnis.jahresergebnis)}</span>
            </div>
          </div>

          {/* Hinweis */}
          <div className="p-4 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-xl text-xs text-blue-700 dark:text-blue-300 leading-relaxed">
            <strong>Hinweis:</strong> Vereinnahmte USt (EÜR Zeile 17) und abziehbare Vorsteuer (Zeile 57)
            sind Steuer-Durchlaufposten und werden in der GuV nicht ausgewiesen. Das Jahresergebnis
            kann daher vom steuerlichen Gewinn der EÜR abweichen.
            Eine prüfungsfähige GuV nach §&nbsp;275 HGB erstellt dein Steuerberater.
          </div>
        </>
      )}
    </div>
  )
}
