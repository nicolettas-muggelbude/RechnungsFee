import { createContext, useContext, useState, useCallback, useEffect } from 'react'

export interface AnsichtEinstellungen {
  ausrichtung: 'links' | 'zentriert'
  splitter: 'auto' | 'manuell'
  farbschema: 'system' | 'hell' | 'dunkel'
}

const STORAGE_KEY = 'ansicht_einstellungen'
const DEFAULTS: AnsichtEinstellungen = { ausrichtung: 'links', splitter: 'auto', farbschema: 'system' }

export function applyTheme(farbschema: 'system' | 'hell' | 'dunkel') {
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const dark = farbschema === 'dunkel' || (farbschema === 'system' && prefersDark)
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
}

function laden(): AnsichtEinstellungen {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) return { ...DEFAULTS, ...JSON.parse(saved) }
  } catch {}
  return { ...DEFAULTS }
}

export const AnsichtContext = createContext<{
  einstellungen: AnsichtEinstellungen
  setEinstellungen: (e: AnsichtEinstellungen) => void
}>({
  einstellungen: DEFAULTS,
  setEinstellungen: () => {},
})

export function useAnsicht() {
  return useContext(AnsichtContext)
}

export function useMxAuto(): string {
  const { einstellungen } = useContext(AnsichtContext)
  return einstellungen.ausrichtung === 'zentriert' ? 'mx-auto' : ''
}

export function useAnsichtState() {
  const [einstellungen, setEinstellungenState] = useState<AnsichtEinstellungen>(() => {
    const e = laden()
    applyTheme(e.farbschema)
    return e
  })

  // Bei "system": Systemthema-Änderungen live übernehmen
  useEffect(() => {
    if (einstellungen.farbschema !== 'system') return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => applyTheme('system')
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [einstellungen.farbschema])

  const setEinstellungen = useCallback((e: AnsichtEinstellungen) => {
    setEinstellungenState(e)
    applyTheme(e.farbschema)
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(e)) } catch {}
  }, [])

  return { einstellungen, setEinstellungen }
}
