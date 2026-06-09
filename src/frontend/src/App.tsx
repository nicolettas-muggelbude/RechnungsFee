import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { getSetupStatus, isTauri } from './api/client'
import { SetupWizard } from './pages/setup/SetupWizard'
import { AppLayout } from './components/AppLayout'
import { Dashboard } from './pages/dashboard/Dashboard'
import { JournalPage } from './pages/journal/JournalPage'
import { TagesabschlussPage } from './pages/journal/TagesabschlussPage'
import { KundenPage } from './pages/kunden/KundenPage'
import { LieferantenPage } from './pages/lieferanten/LieferantenPage'
import { ArtikelPage } from './pages/artikel/ArtikelPage'
import { NummernkreisePage } from './pages/einstellungen/NummernkreisePage'
import { UstSaetzePage } from './pages/einstellungen/UstSaetzePage'
import { VorlagenPage } from './pages/einstellungen/VorlagenPage'
import { KontenPage } from './pages/stammdaten/KontenPage'
import { KategorienPage } from './pages/stammdaten/KategorienPage'
import { UnternehmenPage } from './pages/stammdaten/UnternehmenPage'
import { DokumentenpaketePage } from './pages/stammdaten/DokumentenpaketePage'
import { LieferscheineUebersicht } from './pages/lieferscheine/LieferscheineUebersicht'
import { AngebotePage } from './pages/angebote/AngebotePage'
import { ProformaPage } from './pages/proforma/ProformaPage'
import { ExportPage } from './pages/ExportPage'
import { EksPage } from './pages/eks/EksPage'
import { UStVAPage } from './pages/ustva/UStVAPage'
import { ZMPage } from './pages/zm/ZMPage'
import { EUERPage } from './pages/euer/EUERPage'
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

  // Zeigt nach 8 s einen Hinweis: erster Start nach einem Update dauert länger
  const [longWait, setLongWait] = useState(false)
  useEffect(() => {
    if (!isLoading) return
    const t = setTimeout(() => setLongWait(true), 8000)
    return () => clearTimeout(t)
  }, [isLoading])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center space-y-3">
          <div className="text-4xl">🧾</div>
          <p className="text-slate-500 text-sm">RechnungsFee wird geladen…</p>
          {longWait && (
            <p className="text-slate-400 text-xs">
              Erster Start nach einem Update? Das kann einen Moment dauern…
            </p>
          )}
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
          <Route path="/journal" element={<JournalPage />} />
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
          <Route path="/dokumentenpakete" element={<DokumentenpaketePage />} />
          <Route path="/rechnungen" element={<RechnungenPage />} />
          <Route path="/lieferscheine" element={<LieferscheineUebersicht />} />
          <Route path="/angebote" element={<AngebotePage />} />
          <Route path="/proformas" element={<ProformaPage />} />
          <Route path="/exporte" element={<ExportPage />} />
          <Route path="/eks" element={<EksPage />} />
          <Route path="/ustva" element={<UStVAPage />} />
          <Route path="/zm" element={<ZMPage />} />
          <Route path="/euer" element={<EUERPage />} />
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

  useEffect(() => {
    if (!isTauri()) return
    let unlisten: (() => void) | undefined
    import('@tauri-apps/api/event').then(({ listen }) => {
      listen('confirm-close', () => setZeigSchliessen(true)).then(fn => { unlisten = fn })
    })
    return () => { unlisten?.() }
  }, [])

  // WebKitGTK auf Linux (z.B. Mint Cinnamon) scrollt overflow-Container nicht
  // automatisch per Mausrad. e.target ist auf Cinnamon unzuverlässig –
  // elementFromPoint liefert immer das Element unter dem Cursor.
  useEffect(() => {
    const handler = (e: WheelEvent) => {
      let el = (document.elementFromPoint(e.clientX, e.clientY) ?? e.target) as HTMLElement | null
      while (el && el !== document.documentElement) {
        const oy = window.getComputedStyle(el).overflowY
        if ((oy === 'auto' || oy === 'scroll') && el.scrollHeight > el.clientHeight) {
          el.scrollTop += e.deltaY
          return
        }
        el = el.parentElement
      }
    }
    window.addEventListener('wheel', handler, { passive: true })
    return () => window.removeEventListener('wheel', handler)
  }, [])

  async function handleBestaetigenSchliessen() {
    setZeigSchliessen(false)
    const { invoke } = await import('@tauri-apps/api/core')
    await invoke('confirm_close')
  }

  return (
    <BrowserRouter>
      <AppRoutes />
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
