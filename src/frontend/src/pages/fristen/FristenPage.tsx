import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getFristen, type FristenResponse } from '../../api/client'

const TYP_STYLE: Record<string, string> = {
  UStVA:     'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  'ESt-VZ':  'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  'GewSt-VZ':'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300',
}

function datumDE(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

function tageNoch(iso: string): number {
  const heute = new Date()
  heute.setHours(0, 0, 0, 0)
  const frist = new Date(iso)
  return Math.round((frist.getTime() - heute.getTime()) / 86_400_000)
}

function DringlichkeitBadge({ tage }: { tage: number }) {
  if (tage < 0) return (
    <span className="text-xs text-red-600 dark:text-red-400 font-semibold">abgelaufen</span>
  )
  if (tage === 0) return (
    <span className="text-xs text-red-600 dark:text-red-400 font-bold">heute!</span>
  )
  if (tage <= 7) return (
    <span className="text-xs text-red-500 dark:text-red-400 font-semibold">in {tage} {tage === 1 ? 'Tag' : 'Tagen'}</span>
  )
  if (tage <= 30) return (
    <span className="text-xs text-amber-600 dark:text-amber-400 font-medium">in {tage} Tagen</span>
  )
  return (
    <span className="text-xs text-slate-400">in {tage} Tagen</span>
  )
}

const MONATE_OPTIONS = [
  { value: 3, label: '3 Monate' },
  { value: 6, label: '6 Monate' },
  { value: 12, label: '12 Monate' },
]

export function FristenPage() {
  const [monate, setMonate] = useState(3)

  const { data, isLoading, error } = useQuery<FristenResponse>({
    queryKey: ['fristen', monate],
    queryFn: () => getFristen(monate),
    staleTime: 60_000,
  })

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Steuer-Fristenliste</h1>
          {data?.bundesland_name && (
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
              Bundesland: {data.bundesland_name}
              {data.dauerfristverlaengerung && ' · Dauerfristverlängerung aktiv'}
            </p>
          )}
        </div>
        <select
          value={monate}
          onChange={e => setMonate(Number(e.target.value))}
          className="rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {MONATE_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {!data?.konfiguriert && !isLoading && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-800 p-4 mb-6">
          <p className="text-sm text-amber-800 dark:text-amber-300">
            <strong>Bundesland nicht hinterlegt.</strong> Hinterlege dein Bundesland in{' '}
            <Link to="/unternehmen?tab=steuer" className="underline">Einstellungen → Unternehmen → Steuer &amp; Recht</Link>,
            damit Fristverschiebungen durch Feiertage korrekt berechnet werden.
          </p>
        </div>
      )}

      {data?.ist_kleinunternehmer && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-800 p-4 mb-6">
          <p className="text-sm text-blue-800 dark:text-blue-300">
            Als Kleinunternehmer §19 bist du von der UStVA befreit. Nur ESt- und GewSt-Vorauszahlungen werden angezeigt,
            falls du diese in den Stammdaten aktiviert hast.
          </p>
        </div>
      )}

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-20 rounded-xl bg-slate-100 dark:bg-slate-800 animate-pulse" />
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-900/20 p-4">
          <p className="text-sm text-red-700 dark:text-red-300">Fehler beim Laden der Fristen.</p>
        </div>
      )}

      {data && !isLoading && data.fristen.length === 0 && (
        <div className="text-center py-16 text-slate-400">
          <div className="text-4xl mb-3">📅</div>
          <p className="text-sm">Keine Fristen im gewählten Zeitraum.</p>
          {!data.est_aktiv && !data.gewst_aktiv && !data.ist_kleinunternehmer && (
            <p className="text-xs mt-1 text-slate-400">
              Aktiviere ESt- oder GewSt-Vorauszahlungen in den Stammdaten für mehr Termine.
            </p>
          )}
        </div>
      )}

      {data && !isLoading && data.fristen.length > 0 && (
        <div className="space-y-3">
          {data.fristen.map((f, i) => {
            const tage = tageNoch(f.faellig)
            const verschoben = f.faellig !== f.faellig_original
            const abgelaufen = tage < 0
            return (
              <div
                key={i}
                className={`rounded-xl border p-4 transition-colors ${
                  abgelaufen
                    ? 'border-red-200 bg-red-50/50 dark:border-red-800 dark:bg-red-900/10'
                    : tage <= 7
                    ? 'border-red-200 bg-red-50/30 dark:border-red-800 dark:bg-red-900/10'
                    : tage <= 30
                    ? 'border-amber-200 bg-amber-50/30 dark:border-amber-800 dark:bg-amber-900/10'
                    : 'border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`inline-block text-xs font-semibold px-2 py-0.5 rounded-full ${TYP_STYLE[f.typ] ?? ''}`}>
                        {f.typ}
                      </span>
                      <span className="text-sm font-medium text-slate-800 dark:text-slate-100 truncate">
                        {f.bezeichnung}
                      </span>
                    </div>
                    {f.hinweis && (
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{f.hinweis}</p>
                    )}
                    {verschoben && (
                      <p className="text-xs text-slate-400 mt-0.5">
                        Ursprünglich {datumDE(f.faellig_original)} – auf nächsten Werktag verschoben
                      </p>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                      {datumDE(f.faellig)}
                    </div>
                    <DringlichkeitBadge tage={tage} />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      <p className="text-xs text-slate-400 dark:text-slate-500 mt-8 text-center">
        Alle Angaben ohne Gewähr. Fristen können sich durch individuelle Bescheide oder Dauerfristverlängerung verschieben.
        Kein Ersatz für steuerliche Beratung.
      </p>
    </div>
  )
}
