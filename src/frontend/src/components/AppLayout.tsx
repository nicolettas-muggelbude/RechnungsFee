import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'

const hauptNav = [
  { to: '/', label: 'Dashboard', icon: '📊', end: true },
  { to: '/kassenbuch', label: 'Kassenbuch', icon: '📒' },
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

export function AppLayout() {
  const location = useLocation()
  const stammdatenAktiv = stammdatenPfade.some((p) => location.pathname.startsWith(p))
  const [stammdatenOffen, setStammdatenOffen] = useState(stammdatenAktiv)

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
        <div className="p-4 border-b border-slate-200">
          <h1 className="font-bold text-slate-800 text-lg">🧾 RechnungsFee</h1>
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
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
