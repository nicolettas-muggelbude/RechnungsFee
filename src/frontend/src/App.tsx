import React, { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom'
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
import { AuftraegePage } from './pages/auftraege/AuftraegePage'
import { ProformaPage } from './pages/proforma/ProformaPage'
import { ExportPage } from './pages/ExportPage'
import { EksPage } from './pages/eks/EksPage'
import { UStVAPage } from './pages/ustva/UStVAPage'
import { JahresUStPage } from './pages/ustva/JahresUStPage'
import { ZMPage } from './pages/zm/ZMPage'
import { EUERPage } from './pages/euer/EUERPage'
import { CockpitPage } from './pages/cockpit/CockpitPage'
import { GUVPage } from './pages/guv/GUVPage'
import { AnlageverzeichnisPage } from './pages/anlageverzeichnis/AnlageverzeichnisPage'
import { AnlageSPage } from './pages/anlage-s/AnlageSPage'
import { AnlageGPage } from './pages/anlage-g/AnlageGPage'
import { RechnungenPage } from './pages/rechnungen/RechnungenPage'
import { WiederkehrendePage } from './pages/wiederkehrend/WiederkehrendePage'
import BuchungsvorlagenPage from './pages/buchungsvorlagen/BuchungsvorlagenPage'
import { BackupPage } from './pages/backup/BackupPage'
import { InfoPage } from './pages/info/InfoPage'
import { SpendenPage } from './pages/info/SpendenPage'
import { FristenPage } from './pages/fristen/FristenPage'
import { BankImportPage } from './pages/bank-import/BankImportPage'
import { DatensmigrationsPage } from './pages/datenmigration/DatensmigrationsPage'
import { AnsichtPage } from './pages/einstellungen/AnsichtPage'
import { AnsichtContext, useAnsichtState } from './hooks/useAnsicht'

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
          <Route path="/wiederkehrend" element={<WiederkehrendePage />} />
          <Route path="/buchungsvorlagen" element={<BuchungsvorlagenPage />} />
          <Route path="/lieferscheine" element={<LieferscheineUebersicht />} />
          <Route path="/angebote" element={<AngebotePage />} />
          <Route path="/auftraege" element={<AuftraegePage />} />
          <Route path="/proformas" element={<ProformaPage />} />
          <Route path="/exporte" element={<ExportPage />} />
          <Route path="/eks" element={<EksPage />} />
          <Route path="/ustva" element={<UStVAPage />} />
          <Route path="/jahres-ust" element={<JahresUStPage />} />
          <Route path="/zm" element={<ZMPage />} />
          <Route path="/euer" element={<EUERPage />} />
          <Route path="/cockpit" element={<CockpitPage />} />
          <Route path="/guv" element={<GUVPage />} />
          <Route path="/anlageverzeichnis" element={<AnlageverzeichnisPage />} />
          <Route path="/anlage-s" element={<AnlageSPage />} />
          <Route path="/anlage-g" element={<AnlageGPage />} />
          <Route path="/fristen" element={<FristenPage />} />
          <Route path="/bank-import" element={<BankImportPage />} />
          <Route path="/datenmigration" element={<DatensmigrationsPage />} />
          <Route path="/ansicht" element={<AnsichtPage />} />
          <Route path="/backup" element={<BackupPage />} />
          <Route path="/info" element={<InfoPage />} />
          <Route path="/spenden" element={<SpendenPage />} />
        </Route>
      ) : (
        <Route path="*" element={<Navigate to="/setup" replace />} />
      )}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

type SchliessenPhase = 'backup-laeuft' | 'backup-ok' | 'extern-fehler'

function AnsichtProvider({ children }: { children: React.ReactNode }) {
  const state = useAnsichtState()
  return <AnsichtContext.Provider value={state}>{children}</AnsichtContext.Provider>
}

export default function App() {
  const [zeigSchliessen, setZeigSchliessen] = useState(false)
  const [phase, setPhase] = useState<SchliessenPhase>('backup-laeuft')
  const [externFehler, setExternFehler] = useState<string[]>([])
  const [externKonfiguriert, setExternKonfiguriert] = useState(false)
  const closingRef = useRef(false)
  const abgebrochenRef = useRef(false)

  useEffect(() => {
    if (!isTauri()) return
    let unlisten: (() => void) | undefined
    import('@tauri-apps/api/window').then(({ getCurrentWindow }) => {
      getCurrentWindow().onCloseRequested(async (event) => {
        if (closingRef.current) return  // zweiter Close nach confirm_close – durchlassen
        event.preventDefault()
        abgebrochenRef.current = false
        setExternFehler([])
        setExternKonfiguriert(false)
        setPhase('backup-laeuft')
        setZeigSchliessen(true)
        await führeBackupUndSchliesseDurch()
      }).then(fn => { unlisten = fn })
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

  async function führeBackupUndSchliesseDurch() {
    try {
      const { getApiBase } = await import('./api/client')
      const base = await getApiBase()
      const res = await fetch(`${base}/backup/erstellen`, { method: 'POST' })
      if (res.ok) {
        const json = await res.json().catch(() => ({}))
        setExternKonfiguriert(json.extern_konfiguriert ?? false)
        const fehler: string[] = json.fehler ?? []
        if (fehler.length > 0) {
          if (abgebrochenRef.current) return
          setExternFehler(fehler)
          setPhase('extern-fehler')
          setZeigSchliessen(true)
          return
        }
      }
    } catch {
      // Netzwerkfehler – lokal war OK, einfach schließen
    }
    setPhase('backup-ok')
  }

  function abbrechen() {
    abgebrochenRef.current = true
    setZeigSchliessen(false)
  }

  async function schliessenOhneBackup() {
    setZeigSchliessen(false)
    closingRef.current = true
    const { invoke } = await import('@tauri-apps/api/core')
    await invoke('confirm_close')  // tötet Backend
    const { exit } = await import('@tauri-apps/plugin-process')
    await exit(0)
  }

  return (
    <BrowserRouter>
      <AnsichtProvider>
      <AppRoutes />
      {zeigSchliessen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl p-6 w-96 space-y-4">

            {phase === 'backup-laeuft' && (
              <>
                <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">Backup wird erstellt…</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">Bitte warten – Daten werden gesichert.</p>
              </>
            )}

            {phase === 'backup-ok' && (
              <>
                <h2 className="text-base font-semibold text-emerald-700 dark:text-emerald-400">
                  {externKonfiguriert ? 'Lokales & externes Backup erstellt' : 'Lokales Backup erstellt'}
                </h2>
                {externKonfiguriert ? (
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    Daten wurden lokal und verschlüsselt auf dem externen Ziel gesichert.
                  </p>
                ) : (
                  <div className="rounded-lg bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-700 p-3 space-y-2">
                    <p className="text-sm text-amber-800 dark:text-amber-300 font-medium">
                      Kein externes Backup eingerichtet
                    </p>
                    <p className="text-xs text-amber-700 dark:text-amber-400">
                      Deine Daten liegen nur lokal. Richte ein verschlüsseltes Backup auf NAS oder USB ein – bei Festplattenausfall sind sie sonst verloren.
                    </p>
                    <Link
                      to="/backup"
                      onClick={() => setZeigSchliessen(false)}
                      className="text-xs text-amber-700 dark:text-amber-400 underline hover:text-amber-900 dark:hover:text-amber-200"
                    >
                      Externes Backup einrichten →
                    </Link>
                  </div>
                )}
                <div className="flex justify-between">
                  <button onClick={abbrechen}
                    className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300">
                    Abbrechen
                  </button>
                  <button onClick={schliessenOhneBackup}
                    className="px-4 py-2 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700">
                    App beenden
                  </button>
                </div>
              </>
            )}

            {phase === 'extern-fehler' && (
              <>
                <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">Externes Backup fehlgeschlagen</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Das lokale Backup wurde erstellt. Das externe Backup konnte nicht gespeichert werden:
                </p>
                <ul className="text-xs font-mono bg-slate-50 dark:bg-slate-900 rounded-lg p-3 space-y-1 text-red-600 dark:text-red-400">
                  {externFehler.map((f, i) => <li key={i}>{f}</li>)}
                </ul>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Laufwerk anstecken oder NAS starten und dann erneut versuchen.
                </p>
                <div className="flex gap-2 justify-between">
                  <button onClick={abbrechen}
                    className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300">
                    Abbrechen
                  </button>
                  <div className="flex gap-2">
                    <button onClick={schliessenOhneBackup}
                      className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300">
                      Trotzdem beenden
                    </button>
                    <button onClick={führeBackupUndSchliesseDurch}
                      className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                      Erneut versuchen
                    </button>
                  </div>
                </div>
              </>
            )}

          </div>
        </div>
      )}
      </AnsichtProvider>
    </BrowserRouter>
  )
}
