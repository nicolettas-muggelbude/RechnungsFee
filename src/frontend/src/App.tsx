import { useQuery } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { getSetupStatus } from './api/client'
import { SetupWizard } from './pages/setup/SetupWizard'
import { AppLayout } from './components/AppLayout'
import { Dashboard } from './pages/dashboard/Dashboard'
import { KassenbuchPage } from './pages/kassenbuch/KassenbuchPage'
import { KundenPage } from './pages/kunden/KundenPage'
import { LieferantenPage } from './pages/lieferanten/LieferantenPage'
import { NummernkreisePage } from './pages/einstellungen/NummernkreisePage'
import { KontenPage } from './pages/stammdaten/KontenPage'
import { KategorienPage } from './pages/stammdaten/KategorienPage'
import { UnternehmenPage } from './pages/stammdaten/UnternehmenPage'

function AppRoutes() {
  const { data: status, isLoading } = useQuery({
    queryKey: ['setup-status'],
    queryFn: getSetupStatus,
    retry: false,
  })

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center space-y-3">
          <div className="text-4xl">🧾</div>
          <p className="text-slate-500 text-sm">RechnungsFee wird geladen…</p>
        </div>
      </div>
    )
  }

  if (!status) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-red-50">
        <div className="text-center space-y-2">
          <p className="text-red-600 font-medium">Backend nicht erreichbar</p>
          <p className="text-slate-500 text-sm">Ist der RechnungsFee-Dienst gestartet?</p>
        </div>
      </div>
    )
  }

  return (
    <Routes>
      <Route
        path="/setup"
        element={
          status.ist_eingerichtet
            ? <Navigate to="/" replace />
            : <SetupWizard />
        }
      />
      {status.ist_eingerichtet ? (
        <Route element={<AppLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/kassenbuch" element={<KassenbuchPage />} />
          {/* Stammdaten */}
          <Route path="/kunden" element={<KundenPage />} />
          <Route path="/lieferanten" element={<LieferantenPage />} />
          <Route path="/konten" element={<KontenPage />} />
          <Route path="/kategorien" element={<KategorienPage />} />
          <Route path="/nummernkreise" element={<NummernkreisePage />} />
          <Route path="/unternehmen" element={<UnternehmenPage />} />
        </Route>
      ) : (
        <Route path="*" element={<Navigate to="/setup" replace />} />
      )}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
