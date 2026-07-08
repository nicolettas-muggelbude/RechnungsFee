import { createContext, useContext, useState, useCallback } from 'react'

export interface AnsichtEinstellungen {
  ausrichtung: 'links' | 'zentriert'
  splitter: 'auto' | 'manuell'
}

const STORAGE_KEY = 'ansicht_einstellungen'

function laden(): AnsichtEinstellungen {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) return { ausrichtung: 'links', splitter: 'auto', ...JSON.parse(saved) }
  } catch {}
  return { ausrichtung: 'links', splitter: 'auto' }
}

export const AnsichtContext = createContext<{
  einstellungen: AnsichtEinstellungen
  setEinstellungen: (e: AnsichtEinstellungen) => void
}>({
  einstellungen: { ausrichtung: 'links', splitter: 'auto' },
  setEinstellungen: () => {},
})

export function useAnsicht() {
  return useContext(AnsichtContext)
}

export function useAnsichtState() {
  const [einstellungen, setEinstellungenState] = useState<AnsichtEinstellungen>(laden)

  const setEinstellungen = useCallback((e: AnsichtEinstellungen) => {
    setEinstellungenState(e)
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(e)) } catch {}
  }, [])

  return { einstellungen, setEinstellungen }
}
