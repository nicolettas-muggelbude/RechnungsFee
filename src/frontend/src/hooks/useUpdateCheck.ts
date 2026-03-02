import { useState, useEffect, useCallback } from 'react'

// Nur im Tauri-Modus verfügbar
const isTauri = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window

export interface UpdateState {
  checking: boolean
  updateAvailable: boolean
  version: string | null
  downloading: boolean
  progress: number | null
  error: string | null
  readyToRestart: boolean
}

export interface UpdateActions {
  installUpdate: () => Promise<void>
}

export function useUpdateCheck(): UpdateState & UpdateActions {
  const [state, setState] = useState<UpdateState>({
    checking: false,
    updateAvailable: false,
    version: null,
    downloading: false,
    progress: null,
    error: null,
    readyToRestart: false,
  })

  useEffect(() => {
    if (!isTauri) return

    let cancelled = false

    async function checkForUpdate() {
      setState(s => ({ ...s, checking: true, error: null }))
      try {
        const { check } = await import('@tauri-apps/plugin-updater')
        const update = await check()
        if (cancelled) return
        if (update?.available) {
          setState(s => ({
            ...s,
            checking: false,
            updateAvailable: true,
            version: update.version,
          }))
        } else {
          setState(s => ({ ...s, checking: false }))
        }
      } catch (err) {
        if (cancelled) return
        // Fehler im Updater (kein Netz, Platzhalter-Key etc.) – still ignorieren
        setState(s => ({ ...s, checking: false }))
      }
    }

    checkForUpdate()
    return () => { cancelled = true }
  }, [])

  const installUpdate = useCallback(async () => {
    if (!isTauri || !state.updateAvailable) return
    setState(s => ({ ...s, downloading: true, progress: 0 }))
    try {
      const { check } = await import('@tauri-apps/plugin-updater')
      const update = await check()
      if (!update?.available) return

      let total: number | null = null
      let downloaded = 0
      await update.downloadAndInstall(event => {
        if (event.event === 'Started') {
          total = event.data.contentLength ?? null
        } else if (event.event === 'Progress') {
          downloaded += event.data.chunkLength
          const pct = total ? Math.round((downloaded / total) * 100) : null
          setState(s => ({ ...s, progress: pct }))
        }
      })

      // Download abgeschlossen – Nutzer informieren, bevor die App sich schließt.
      // Der NSIS-Installer startet die neue Version NICHT automatisch.
      setState(s => ({ ...s, downloading: false, readyToRestart: true }))

      // 3 Sekunden warten, damit der Nutzer die Meldung lesen kann.
      await new Promise(resolve => setTimeout(resolve, 3000))

      // App beenden, damit der NSIS-Installer die gesperrte Exe ersetzen kann.
      const { exit } = await import('@tauri-apps/plugin-process')
      await exit(0)
    } catch (err) {
      const msg =
        err instanceof Error ? err.message
        : typeof err === 'string' ? err
        : JSON.stringify(err)
      setState(s => ({ ...s, downloading: false, error: msg }))
    }
  }, [state.updateAvailable])

  return { ...state, installUpdate }
}
