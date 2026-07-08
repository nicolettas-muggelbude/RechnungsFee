import { useState, useCallback } from 'react'
import type React from 'react'

export function useSplitterBreite(key: string, defaultProzent: number = 33): [string, (e: React.MouseEvent<HTMLDivElement>) => void] {
  const storageKey = `splitter_${key}`

  const [breite, setBreite] = useState<string>(() => {
    try {
      return localStorage.getItem(storageKey) ?? `${defaultProzent}%`
    } catch {
      return `${defaultProzent}%`
    }
  })

  const startDrag = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    e.preventDefault()
    const container = e.currentTarget.parentElement
    if (!container) return

    const containerRect = container.getBoundingClientRect()

    const onMouseMove = (me: MouseEvent) => {
      const neueBreitePx = Math.max(220, Math.min(containerRect.width - 280, me.clientX - containerRect.left))
      const pct = `${(neueBreitePx / containerRect.width * 100).toFixed(1)}%`
      setBreite(pct)
      try { localStorage.setItem(storageKey, pct) } catch {}
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
  }, [storageKey])

  return [breite, startDrag]
}
