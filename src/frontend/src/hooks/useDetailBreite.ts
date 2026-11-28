import { useState, useCallback } from 'react'
import type React from 'react'
import { useAnsicht } from './useAnsicht'

// Issue #599: Breite des Detail-Panels rechts neben einer Liste.
// Nur bei Einstellungen → Ansicht → „Manuell verschiebbar“ veränderbar,
// sonst feste Standardbreite (28rem = 448 px) wie bisher.
export const DETAIL_STANDARD_PX = 448
const DETAIL_MIN_PX = 320
const LISTE_MIN_PX = 300

function begrenze(px: number, containerBreite: number): number {
  const max = Math.max(DETAIL_MIN_PX, containerBreite - LISTE_MIN_PX)
  return Math.round(Math.max(DETAIL_MIN_PX, Math.min(max, px)))
}

export interface DetailBreite {
  /** true = Trennlinie anzeigen und Breite aus dem Speicher nutzen */
  manuell: boolean
  /** Style für das Detail-Panel (nur im manuellen Modus gesetzt) */
  style: React.CSSProperties | undefined
  /** Klassen für die Breite des Detail-Panels */
  breiteKlasse: string
  startDrag: (e: React.MouseEvent<HTMLDivElement>) => void
  zuruecksetzen: () => void
}

export function useDetailBreite(seite: string): DetailBreite {
  const { einstellungen } = useAnsicht()
  const manuell = einstellungen.splitter === 'manuell'
  const storageKey = `detailbreite_${seite}`

  const [breite, setBreite] = useState<number>(() => {
    try {
      const wert = Number(localStorage.getItem(storageKey))
      return Number.isFinite(wert) && wert >= DETAIL_MIN_PX ? wert : DETAIL_STANDARD_PX
    } catch {
      return DETAIL_STANDARD_PX
    }
  })

  const speichern = useCallback((px: number) => {
    setBreite(px)
    try { localStorage.setItem(storageKey, String(px)) } catch {}
  }, [storageKey])

  const startDrag = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    e.preventDefault()
    const container = e.currentTarget.parentElement
    if (!container) return
    const rect = container.getBoundingClientRect()

    const onMouseMove = (me: MouseEvent) => {
      speichern(begrenze(rect.right - me.clientX, rect.width))
    }
    const onMouseUp = () => {
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  }, [speichern])

  const zuruecksetzen = useCallback(() => {
    setBreite(DETAIL_STANDARD_PX)
    try { localStorage.removeItem(storageKey) } catch {}
  }, [storageKey])

  return {
    manuell,
    style: manuell ? { width: breite } : undefined,
    breiteKlasse: manuell ? '' : 'w-[28rem]',
    startDrag,
    zuruecksetzen,
  }
}
