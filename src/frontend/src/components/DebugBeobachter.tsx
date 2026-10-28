import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useLocation } from 'react-router-dom'
import { getDebugEinstellungen, sendeDebugEreignisse, type DebugEreignis } from '../api/client'

// App-Routen sind statisch. Unbekannte Pfade, Suchparameter und Hashes nie übertragen.
function seite(pfad: string): string {
  return /^\/[a-z-]*$/.test(pfad) && pfad.length <= 80 ? pfad : '/'
}

export function DebugBeobachter() {
  const location = useLocation()
  const { data } = useQuery({
    queryKey: ['debug-einstellungen'], queryFn: getDebugEinstellungen,
    refetchInterval: 10000, retry: false,
  })
  const navigationAktiv = !!data?.aktiviert && data.kategorien.includes('navigation')

  useEffect(() => {
    if (navigationAktiv) {
      void sendeDebugEreignisse([{ kategorie: 'navigation', aktion: 'seitenwechsel', seite: seite(location.pathname) }]).catch(() => {})
    }
  }, [location.pathname, navigationAktiv])

  useEffect(() => {
    if (!data?.aktiviert) return
    const uiAktiv = data.kategorien.includes('ui')
    const fehlerAktiv = data.kategorien.includes('fehler')
    let stapel: DebugEreignis[] = []
    const senden = () => {
      if (!stapel.length) return
      const ereignisse = stapel
      stapel = []
      // Absichtlich kein Retry und keine Fehlerausgabe: Diagnose erzeugt keine Endlosschleife.
      void sendeDebugEreignisse(ereignisse).catch(() => {})
    }
    window.addEventListener('pagehide', senden)
    const merken = (e: DebugEreignis) => {
      stapel.push(e)
      if (stapel.length >= 50) senden()
    }
    const aktion = (event: Event) => {
      if (!uiAktiv || !(event.target instanceof Element)) return
      // Protokollansicht und ihre Bedienung nicht selbst aufzeichnen.
      if (event.target.closest('[data-debug-ignore]')) return
      const target = event.target.closest('button, a, input, select, textarea, form, [role="button"], [role="switch"]')
      if (!target) return
      const tag = target.tagName.toLowerCase()
      const element = ['button', 'a', 'input', 'select', 'textarea', 'form'].includes(tag)
        ? tag as DebugEreignis['element'] : 'sonstiges'
      // Nur explizite Entwicklerkennungen, keine Beschriftungen, DOM-IDs oder Feldinhalte.
      const kennung = target.getAttribute('data-debug-id')
      const position: string[] = []
      let knoten: Element | null = target
      for (let tiefe = 0; knoten && tiefe < 4; tiefe++, knoten = knoten.parentElement) {
        const geschwister = knoten.parentElement ? Array.from(knoten.parentElement.children) : [knoten]
        position.unshift(`${knoten.tagName.toLowerCase()}:${geschwister.indexOf(knoten) + 1}`)
      }
      merken({
        kategorie: 'ui', aktion: event.type === 'click' ? 'klick' : event.type === 'change' ? 'aenderung' : 'absenden',
        seite: seite(window.location.pathname), element,
        element_id: kennung && /^[a-zA-Z0-9_.:-]{1,80}$/.test(kennung) ? kennung : position.join('.').slice(0, 80),
      })
    }
    const fehler = () => {
      if (fehlerAktiv) merken({ kategorie: 'fehler', aktion: 'javascript', seite: seite(window.location.pathname) })
    }
    const promiseFehler = () => {
      if (fehlerAktiv) merken({ kategorie: 'fehler', aktion: 'promise', seite: seite(window.location.pathname) })
    }
    document.addEventListener('click', aktion, true)
    document.addEventListener('change', aktion, true)
    document.addEventListener('submit', aktion, true)
    window.addEventListener('error', fehler)
    window.addEventListener('unhandledrejection', promiseFehler)
    const timer = window.setInterval(senden, 1000)
    return () => {
      document.removeEventListener('click', aktion, true)
      document.removeEventListener('change', aktion, true)
      document.removeEventListener('submit', aktion, true)
      window.removeEventListener('error', fehler)
      window.removeEventListener('unhandledrejection', promiseFehler)
      window.removeEventListener('pagehide', senden)
      window.clearInterval(timer)
      senden()
    }
  }, [data?.aktiviert, data?.kategorien])
  return null
}
