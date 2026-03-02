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

      const isWindows = navigator.userAgent.toLowerCase().includes('win')

      if (isWindows) {
        // NSIS-Installer braucht freie Datei-Sperre.
        // Nutzer informieren, dann App beenden – Installer übernimmt den Rest.
        setState(s => ({ ...s, downloading: false, readyToRestart: true }))
        await new Promise(resolve => setTimeout(resolve, 3000))
        const { exit } = await import('@tauri-apps/plugin-process')
        await exit(0)
      } else {
        // Linux/macOS: AppImage/Bundle wurde bereits ersetzt – direkt neu starten.
        const { relaunch } = await import('@tauri-apps/plugin-process')
        await relaunch()
      }
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
