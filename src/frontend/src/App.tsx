import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { getSetupStatus, isTauri } from './api/client'
import { SetupWizard } from './pages/setup/SetupWizard'
import { AppLayout } from './components/AppLayout'
import { Dashboard } from './pages/dashboard/Dashboard'
import { KassenbuchPage } from './pages/kassenbuch/KassenbuchPage'
import { TagesabschlussPage } from './pages/kassenbuch/TagesabschlussPage'
import { KundenPage } from './pages/kunden/KundenPage'
import { LieferantenPage } from './pages/lieferanten/LieferantenPage'
import { ArtikelPage } from './pages/artikel/ArtikelPage'
import { NummernkreisePage } from './pages/einstellungen/NummernkreisePage'
import { UstSaetzePage } from './pages/einstellungen/UstSaetzePage'
import { VorlagenPage } from './pages/einstellungen/VorlagenPage'
import { KontenPage } from './pages/stammdaten/KontenPage'
import { KategorienPage } from './pages/stammdaten/KategorienPage'
import { UnternehmenPage } from './pages/stammdaten/UnternehmenPage'
import { ExportPage } from './pages/ExportPage'
import { RechnungenPage } from './pages/rechnungen/RechnungenPage'
import { BackupPage } from './pages/backup/BackupPage'
import { InfoPage } from './pages/info/InfoPage'

function AppRoutes() {
  const { data: status, isLoading } = useQuery({
    queryKey: ['setup-status'],
    queryFn: getSetupStatus,
    retry: 20,
    retryDelay: 500,
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
          <Route path="/tagesabschluesse" element={<TagesabschlussPage />} />
          {/* Stammdaten */}
          <Route path="/kunden" element={<KundenPage />} />
          <Route path="/lieferanten" element={<LieferantenPage />} />
          <Route path="/artikel" element={<ArtikelPage />} />
          <Route path="/konten" element={<KontenPage />} />
          <Route path="/kategorien" element={<KategorienPage />} />
          <Route path="/nummernkreise" element={<NummernkreisePage />} />
          <Route path="/ust-saetze" element={<UstSaetzePage />} />
          <Route path="/vorlagen" element={<VorlagenPage />} />
          <Route path="/unternehmen" element={<UnternehmenPage />} />
          <Route path="/rechnungen" element={<RechnungenPage />} />
          <Route path="/exporte" element={<ExportPage />} />
          <Route path="/backup" element={<BackupPage />} />
          <Route path="/info" element={<InfoPage />} />
        </Route>
      ) : (
        <Route path="*" element={<Navigate to="/setup" replace />} />
      )}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  const [zeigSchliessen, setZeigSchliessen] = useState(false)
  const [inlineViewerUrl, setInlineViewerUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!isTauri()) return
    let unlisten: (() => void) | undefined
    import('@tauri-apps/api/event').then(({ listen }) => {
      listen('confirm-close', () => setZeigSchliessen(true)).then(fn => { unlisten = fn })
    })
    return () => { unlisten?.() }
  }, [])

  useEffect(() => {
    const handler = (e: Event) => setInlineViewerUrl((e as CustomEvent).detail.url)
    window.addEventListener('rechnungsfee:inline-viewer', handler)
    return () => window.removeEventListener('rechnungsfee:inline-viewer', handler)
  }, [])

  async function handleBestaetigenSchliessen() {
    setZeigSchliessen(false)
    const { invoke } = await import('@tauri-apps/api/core')
    await invoke('confirm_close')
  }

  return (
    <BrowserRouter>
      <AppRoutes />
      {inlineViewerUrl && (
        <div className="fixed inset-0 z-50 flex flex-col bg-black/80">
          <div className="flex items-center justify-between px-4 py-2 bg-slate-800 text-white text-sm">
            <span className="text-slate-300 truncate">{inlineViewerUrl.split('/').slice(-2).join('/')}</span>
            <button
              onClick={() => setInlineViewerUrl(null)}
              className="ml-4 px-3 py-1 rounded-lg bg-slate-600 hover:bg-slate-500 text-white text-xs font-medium"
            >
              ✕ Schließen
            </button>
          </div>
          <iframe
            src={inlineViewerUrl}
            className="flex-1 w-full border-0 bg-white"
            title="Dokument"
          />
        </div>
      )}
      {zeigSchliessen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl p-6 w-80 space-y-4">
            <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">RechnungsFee beenden?</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">Möchtest du RechnungsFee wirklich schließen?</p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setZeigSchliessen(false)}
                className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
              >
                Abbrechen
              </button>
              <button
                onClick={handleBestaetigenSchliessen}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Ja, beenden
              </button>
            </div>
          </div>
        </div>
      )}
    </BrowserRouter>
  )
}
