import { useQuery } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { getSetupStatus } from './api/client'
import { SetupWizard } from './pages/setup/SetupWizard'
import { Dashboard } from './pages/dashboard/Dashboard'

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
      <Route
        path="/"
        element={
          status.ist_eingerichtet
            ? <Dashboard />
            : <Navigate to="/setup" replace />
        }
      />
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
