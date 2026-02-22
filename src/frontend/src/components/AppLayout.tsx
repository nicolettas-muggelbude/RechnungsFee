import { NavLink, Outlet } from 'react-router-dom'

const navItems = [
  { to: '/', label: 'Dashboard', icon: '📊', end: true },
  { to: '/kassenbuch', label: 'Kassenbuch', icon: '📒' },
  { to: '/kunden', label: 'Kunden', icon: '👤' },
  { to: '/lieferanten', label: 'Lieferanten', icon: '🏭' },
]

export function AppLayout() {
  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-slate-200 flex flex-col">
        <div className="p-4 border-b border-slate-200">
          <h1 className="font-bold text-slate-800 text-lg">🧾 RechnungsFee</h1>
        </div>
        <nav className="flex-1 py-3">
          {navItems.map(({ to, label, icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-600'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`
              }
            >
              <span>{icon}</span>
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-slate-200 text-xs text-slate-400">
          v0.1.0
        </div>
      </aside>

      {/* Hauptinhalt */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
