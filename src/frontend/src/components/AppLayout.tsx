import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getTagesabschlussFehltGestern } from '../api/client'
import { TagesabschlussDialog } from '../pages/kassenbuch/TagesabschlussDialog'
import { useUpdateCheck } from '../hooks/useUpdateCheck'

const hauptNav = [
  { to: '/', label: 'Dashboard', icon: '📊', end: true },
  { to: '/kassenbuch', label: 'Kassenbuch', icon: '📒' },
  { to: '/rechnungen', label: 'Rechnungen', icon: '🧾' },
  { to: '/tagesabschluesse', label: 'Tagesabschlüsse', icon: '📋' },
  { to: '/exporte', label: 'Exporte', icon: '📦' },
  { to: '/backup', label: 'Backup', icon: '💾' },
  { to: '/info', label: 'Info & Updates', icon: 'ℹ️' },
]

const stammdatenNav = [
  { to: '/kunden', label: 'Kunden', icon: '👤' },
  { to: '/lieferanten', label: 'Lieferanten', icon: '🏭' },
  { to: '/artikel', label: 'Artikelstamm', icon: '📦' },
  { to: '/konten', label: 'Konten', icon: '🏦' },
  { to: '/kategorien', label: 'Kategorien', icon: '🏷️' },
  { to: '/nummernkreise', label: 'Nummernkreise', icon: '🔢' },
  { to: '/ust-saetze', label: 'MwSt.-Sätze', icon: '%' },
  { to: '/vorlagen', label: 'Rechnungsvorlagen', icon: '📄' },
  { to: '/unternehmen', label: 'Unternehmen', icon: '🏢' },
]

const stammdatenPfade = stammdatenNav.map((n) => n.to)

function formatDatum(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

export function AppLayout() {
  const location = useLocation()
  const qc = useQueryClient()
  const stammdatenAktiv = stammdatenPfade.some((p) => location.pathname.startsWith(p))
  const [stammdatenOffen, setStammdatenOffen] = useState(stammdatenAktiv)
  const [bannerDismissed, setBannerDismissed] = useState(false)
  const [abschlussDialog, setAbschlussDialog] = useState<string | null>(null)
  const [updateDismissed, setUpdateDismissed] = useState(false)

  const { updateAvailable, version: updateVersion, downloading, progress, error: updateError, readyToRestart, installUpdate } = useUpdateCheck()

  const { data: fehltGestern } = useQuery({
    queryKey: ['tagesabschluss-fehlt-gestern'],
    queryFn: getTagesabschlussFehltGestern,
    staleTime: 1000 * 60 * 5,
    refetchOnWindowFocus: false,
  })

  const zeigeBanner = fehltGestern?.fehlt === true && !bannerDismissed

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-4 py-2 text-sm font-medium transition-colors ${
      isActive
        ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-600 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-700'
        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100'
    }`

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Sidebar */}
      <aside className="w-56 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-700 flex flex-col">
        <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex items-center gap-2">
          <img src="/logo.svg" alt="RechnungsFee" className="w-8 h-8 flex-shrink-0" />
          <div>
            <h1 className="font-bold text-slate-800 dark:text-slate-100 text-lg leading-tight">RechnungsFee</h1>
            <p className="text-xs text-slate-400 dark:text-slate-500 leading-tight">v{__APP_VERSION__}</p>
          </div>
        </div>

        <nav className="flex-1 py-3">
          {/* Hauptnavigation */}
          {hauptNav.map(({ to, label, icon, end }) => (
            <NavLink key={to} to={to} end={end} className={navLinkClass}>
              <span>{icon}</span>
              <span>{label}</span>
            </NavLink>
          ))}

          {/* Stammdaten – ausklappbar */}
          <div className="mt-2">
            <button
              onClick={() => setStammdatenOffen((o) => !o)}
              className={`w-full flex items-center justify-between px-4 py-2 text-sm font-medium transition-colors ${
                stammdatenAktiv
                  ? 'text-blue-700 dark:text-blue-300'
                  : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100'
              }`}
            >
              <span className="flex items-center gap-3">
                <span>🗂️</span>
                <span>Stammdaten</span>
              </span>
              <span className="text-xs">{stammdatenOffen ? '▲' : '▼'}</span>
            </button>

            {stammdatenOffen && (
              <div className="border-l-2 border-slate-100 dark:border-slate-800 ml-6">
                {stammdatenNav.map(({ to, label, icon }) => (
                  <NavLink key={to} to={to} className={navLinkClass}>
                    <span>{icon}</span>
                    <span>{label}</span>
                  </NavLink>
                ))}
              </div>
            )}
          </div>
        </nav>

      </aside>

      {/* Hauptinhalt */}
      <main className="flex-1 overflow-auto flex flex-col">
        {/* Update-Banner */}
        {updateAvailable && !updateDismissed && (
          <div className={`border-b px-4 py-2.5 flex items-center gap-3 shrink-0 ${
            readyToRestart ? 'bg-blue-50 border-blue-200 dark:bg-blue-950 dark:border-blue-800'
            : updateError ? 'bg-red-50 border-red-200 dark:bg-red-950 dark:border-red-800'
            : 'bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800'
          }`}>
            <span className={`text-base leading-none ${
              readyToRestart ? 'text-blue-500 dark:text-blue-400'
              : updateError ? 'text-red-500 dark:text-red-400'
              : 'text-green-600 dark:text-green-400'
            }`}>
              {readyToRestart ? '↻' : updateError ? '!' : '↑'}
            </span>
            <p className={`text-sm flex-1 ${
              readyToRestart ? 'text-blue-800 dark:text-blue-200'
              : updateError ? 'text-red-800 dark:text-red-200'
              : 'text-green-800 dark:text-green-200'
            }`}>
              {readyToRestart ? (
                <><span className="font-semibold">Update installiert!</span> Die App schließt sich gleich – bitte danach manuell neu starten.</>
              ) : updateError ? (
                <><span className="font-semibold">Update fehlgeschlagen:</span> {updateError}</>
              ) : (
                <>Update verfügbar: <span className="font-semibold">Version {updateVersion}</span></>
              )}
            </p>
            {!readyToRestart && (
              downloading ? (
                <div className="w-32 h-1.5 bg-green-200 dark:bg-green-800 rounded-full overflow-hidden shrink-0">
                  <div
                    className="h-full bg-green-500 rounded-full transition-all duration-300"
                    style={{ width: progress !== null ? `${progress}%` : '60%' }}
                  />
                </div>
              ) : (
                <button
                  onClick={installUpdate}
                  className={`text-sm font-medium rounded-md px-3 py-1 transition-colors shrink-0 border ${
                    updateError
                      ? 'text-red-700 bg-red-100 hover:bg-red-200 border-red-300 dark:text-red-300 dark:bg-red-900 dark:hover:bg-red-800 dark:border-red-700'
                      : 'text-green-700 bg-green-100 hover:bg-green-200 border-green-300 dark:text-green-300 dark:bg-green-900 dark:hover:bg-green-800 dark:border-green-700'
                  }`}
                >
                  {updateError ? 'Erneut versuchen' : 'Jetzt installieren'}
                </button>
              )
            )}
            {!readyToRestart && (
              <button
                onClick={() => setUpdateDismissed(true)}
                className={`text-lg leading-none px-1 shrink-0 ${updateError ? 'text-red-400 hover:text-red-600 dark:text-red-500 dark:hover:text-red-300' : 'text-green-500 hover:text-green-700 dark:text-green-400 dark:hover:text-green-200'}`}
                title="Schließen"
              >
                ×
              </button>
            )}
          </div>
        )}

        {/* Erinnerungs-Banner */}
        {zeigeBanner && fehltGestern && (
          <div className="bg-amber-50 dark:bg-amber-950 border-b border-amber-200 dark:border-amber-800 px-4 py-2.5 flex items-center gap-3 shrink-0">
            <span className="text-amber-600 dark:text-amber-400 text-base leading-none">⚠</span>
            <p className="text-sm text-amber-800 dark:text-amber-300 flex-1">
              Kein Tagesabschluss für{' '}
              <span className="font-semibold">{formatDatum(fehltGestern.datum)}</span> vorhanden.
            </p>
            <button
              onClick={() => setAbschlussDialog(fehltGestern.datum)}
              className="text-sm font-medium text-amber-700 bg-amber-100 hover:bg-amber-200 border border-amber-300 rounded-md px-3 py-1 transition-colors shrink-0 dark:text-amber-300 dark:bg-amber-900 dark:hover:bg-amber-800 dark:border-amber-700"
            >
              Jetzt durchführen
            </button>
            <button
              onClick={() => setBannerDismissed(true)}
              className="text-amber-500 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-200 text-lg leading-none px-1 shrink-0"
              title="Schließen"
            >
              ×
            </button>
          </div>
        )}

        <div className="flex-1">
          <Outlet />
        </div>
      </main>

      {/* Tagesabschluss-Dialog (aus Banner heraus) */}
      {abschlussDialog && (
        <TagesabschlussDialog
          datum={abschlussDialog}
          onClose={() => setAbschlussDialog(null)}
          onSuccess={() => {
            setAbschlussDialog(null)
            setBannerDismissed(true)
            qc.invalidateQueries({ queryKey: ['tagesabschluss-fehlt-gestern'] })
          }}
        />
      )}
    </div>
  )
}
