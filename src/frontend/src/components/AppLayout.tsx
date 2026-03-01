import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getTagesabschlussFehltGestern } from '../api/client'
import { TagesabschlussDialog } from '../pages/kassenbuch/TagesabschlussDialog'

const hauptNav = [
  { to: '/', label: 'Dashboard', icon: '📊', end: true },
  { to: '/kassenbuch', label: 'Kassenbuch', icon: '📒' },
  { to: '/rechnungen', label: 'Rechnungen', icon: '🧾' },
  { to: '/tagesabschluesse', label: 'Tagesabschlüsse', icon: '📋' },
  { to: '/exporte', label: 'Exporte', icon: '📦' },
  { to: '/backup', label: 'Backup', icon: '💾' },
]

const stammdatenNav = [
  { to: '/kunden', label: 'Kunden', icon: '👤' },
  { to: '/lieferanten', label: 'Lieferanten', icon: '🏭' },
  { to: '/konten', label: 'Konten', icon: '🏦' },
  { to: '/kategorien', label: 'Kategorien', icon: '🏷️' },
  { to: '/nummernkreise', label: 'Nummernkreise', icon: '🔢' },
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
        ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-600'
        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
    }`

  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-slate-200 flex flex-col">
        <div className="p-4 border-b border-slate-200 flex items-center gap-2">
          <img src="/logo.svg" alt="RechnungsFee" className="w-8 h-8 flex-shrink-0" />
          <div>
            <h1 className="font-bold text-slate-800 text-lg leading-tight">RechnungsFee</h1>
            <p className="text-xs text-slate-400 leading-tight">v{__APP_VERSION__}</p>
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
                  ? 'text-blue-700'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              <span className="flex items-center gap-3">
                <span>🗂️</span>
                <span>Stammdaten</span>
              </span>
              <span className="text-xs">{stammdatenOffen ? '▲' : '▼'}</span>
            </button>

            {stammdatenOffen && (
              <div className="border-l-2 border-slate-100 ml-6">
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

        <div className="p-4 border-t border-slate-200 text-xs text-slate-400 flex flex-col gap-1">
          <a
            href="https://github.com/nicolettas-muggelbude/RechnungsFee/blob/main/docs/ROADMAP.md"
            target="_blank"
            rel="noreferrer"
            className="hover:text-slate-600 transition-colors"
          >
            🗺️ Roadmap
          </a>
          <span>v0.1.0</span>
        </div>
      </aside>

      {/* Hauptinhalt */}
      <main className="flex-1 overflow-auto flex flex-col">
        {/* Erinnerungs-Banner */}
        {zeigeBanner && fehltGestern && (
          <div className="bg-amber-50 border-b border-amber-200 px-4 py-2.5 flex items-center gap-3 shrink-0">
            <span className="text-amber-600 text-base leading-none">⚠</span>
            <p className="text-sm text-amber-800 flex-1">
              Kein Tagesabschluss für{' '}
              <span className="font-semibold">{formatDatum(fehltGestern.datum)}</span> vorhanden.
            </p>
            <button
              onClick={() => setAbschlussDialog(fehltGestern.datum)}
              className="text-sm font-medium text-amber-700 bg-amber-100 hover:bg-amber-200 border border-amber-300 rounded-md px-3 py-1 transition-colors shrink-0"
            >
              Jetzt durchführen
            </button>
            <button
              onClick={() => setBannerDismissed(true)}
              className="text-amber-500 hover:text-amber-700 text-lg leading-none px-1 shrink-0"
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
