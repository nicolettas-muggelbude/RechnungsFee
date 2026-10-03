import { useState, useEffect, useRef } from 'react'
import { LAENDER, type Land } from '../utils/laender'

/**
 * Such-Combobox für die Länderauswahl (Issue #401) - Interaktionsmuster von
 * StammdatenCombobox.tsx übernommen (Filter, Pfeiltasten, Enter/Escape, Außenklick),
 * aber bewusst eine eigenständige Komponente statt Wiederverwendung: Ein Land ist immer
 * eines aus der festen Liste, der dortige Freitext-Fallback ("Kein Treffer - wird als
 * Freitext übernommen", für offene Einmalkunden-Namen gedacht) wäre hier falsch - ein
 * Tippfehler dürfte nie als "gültiges" Land durchgehen.
 */
export function LandCombobox({
  value,
  onChange,
  placeholder = 'Land suchen…',
}: {
  value: string
  onChange: (code: string) => void
  placeholder?: string
}) {
  const aktuellesLand = () => LAENDER.find((l) => l.code === value)
  const [query, setQuery] = useState(() => aktuellesLand()?.name ?? '')
  const [offen, setOffen] = useState(false)
  const [highlightIdx, setHighlightIdx] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Wenn value von außen geändert wird (z.B. Formular-Reset)
  useEffect(() => {
    setQuery(aktuellesLand()?.name ?? '')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])

  // Außen-Klick schließt Dropdown
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOffen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const q = query.trim().toLowerCase()
  const alleTreffer = q === ''
    ? LAENDER
    : LAENDER.filter((l) => l.name.toLowerCase().includes(q) || l.code.toLowerCase().includes(q))
  const gefiltert = alleTreffer.slice(0, q === '' ? 20 : 50)
  const mehrVorhanden = alleTreffer.length > gefiltert.length

  function handleInputChange(v: string) {
    setQuery(v)
    setOffen(true)
    setHighlightIdx(0)
  }

  function handleSelect(land: Land) {
    setQuery(land.name)
    setOffen(false)
    onChange(land.code)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!offen) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        setOffen(true)
        e.preventDefault()
      }
      return
    }
    if (e.key === 'ArrowDown') {
      setHighlightIdx((i) => Math.min(i + 1, gefiltert.length - 1))
      e.preventDefault()
    } else if (e.key === 'ArrowUp') {
      setHighlightIdx((i) => Math.max(i - 1, 0))
      e.preventDefault()
    } else if (e.key === 'Enter') {
      if (gefiltert[highlightIdx]) {
        handleSelect(gefiltert[highlightIdx])
      }
      e.preventDefault()
    } else if (e.key === 'Escape') {
      setOffen(false)
    }
  }

  function handleBlur() {
    setTimeout(() => {
      setOffen(false)
      // Kein Freitext-Fallback: ohne gültige Auswahl auf den zuletzt gültigen Code
      // zurückspringen, damit kein Tippfehler als "Land" stehen bleibt.
      setQuery(aktuellesLand()?.name ?? '')
    }, 150)
  }

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => handleInputChange(e.target.value)}
          onFocus={() => setOffen(true)}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400"
        />
        <button
          type="button"
          tabIndex={-1}
          onClick={() => { setOffen((o) => !o); inputRef.current?.focus() }}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs"
        >
          {offen ? '▲' : '▼'}
        </button>
      </div>

      {offen && (
        <div className="absolute z-50 w-full mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg max-h-64 overflow-y-auto">
          {gefiltert.length === 0 ? (
            <div className="px-3 py-2.5 text-sm text-slate-400 dark:text-slate-500 italic">
              Kein Treffer
            </div>
          ) : (
            <>
              {gefiltert.map((land, idx) => (
                <button
                  key={land.code}
                  type="button"
                  onMouseDown={() => handleSelect(land)}
                  onMouseEnter={() => setHighlightIdx(idx)}
                  className={`w-full text-left px-3 py-2 text-sm transition-colors ${
                    idx === highlightIdx
                      ? 'bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300'
                      : 'text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700'
                  }`}
                >
                  {land.name}
                </button>
              ))}
              {mehrVorhanden && (
                <div className="px-3 py-2 text-xs text-slate-400 dark:text-slate-500 border-t border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
                  Weitere Treffer – Suche verfeinern
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
