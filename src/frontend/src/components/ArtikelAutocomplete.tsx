import { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useQuery } from '@tanstack/react-query'
import { sucheArtikel, type ArtikelSuche } from '../api/client'
import { artikelNrAnzeige } from '../utils/artikelnummer'

interface Props {
  value: string
  onChange: (v: string) => void
  onArtikelWahl: (a: ArtikelSuche) => void
  placeholder?: string
  className?: string
  inputClassName?: string
}

export function ArtikelAutocomplete({ value, onChange, onArtikelWahl, placeholder = 'Beschreibung', className = '', inputClassName }: Props) {
  const [offen, setOffen] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const [dropdownPos, setDropdownPos] = useState<{ top: number; left: number; width: number } | null>(null)

  const { data: treffer } = useQuery({
    queryKey: ['artikel-suche', value],
    queryFn: () => sucheArtikel(value),
    enabled: value.length >= 2,
    staleTime: 1000 * 30,
  })

  // Dropdown-Position anhand des Inputs berechnen
  useEffect(() => {
    if (!offen || !inputRef.current) return
    const rect = inputRef.current.getBoundingClientRect()
    setDropdownPos({
      top: rect.bottom + window.scrollY,
      left: rect.left + window.scrollX,
      width: Math.max(rect.width, 256),
    })
  }, [offen, value])

  // Außerhalb-Klick schließt Dropdown
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        inputRef.current?.contains(e.target as Node) ||
        dropdownRef.current?.contains(e.target as Node)
      ) return
      setOffen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  // Textarea auto-resize
  useEffect(() => {
    const el = inputRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [value])

  const zeigeDropdown = offen && !!treffer?.length && dropdownPos !== null

  return (
    <div className={`relative ${className}`}>
      <textarea
        ref={inputRef}
        rows={1}
        value={value}
        onChange={e => { onChange(e.target.value); setOffen(true) }}
        onFocus={() => value.length >= 2 && setOffen(true)}
        placeholder={placeholder}
        className={`${inputClassName ?? "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100 dark:placeholder-slate-400"} resize-none overflow-hidden leading-snug`}
      />
      {zeigeDropdown && createPortal(
        <div
          ref={dropdownRef}
          style={{ position: 'absolute', top: dropdownPos!.top, left: dropdownPos!.left, width: dropdownPos!.width, zIndex: 9999 }}
          className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg max-h-52 overflow-y-auto mt-0.5"
        >
          {treffer!.map(a => (
            <button
              key={a.id}
              type="button"
              onMouseDown={e => {
                e.preventDefault() // verhindert blur am Input
                onArtikelWahl(a)
                setOffen(false)
              }}
              className="w-full text-left px-3 py-2 text-xs hover:bg-blue-50 dark:hover:bg-blue-950 border-b border-slate-100 dark:border-slate-700 last:border-0"
            >
              <div className="flex items-center gap-1.5">
                <span className="font-medium text-slate-800 dark:text-slate-100">{a.bezeichnung}</span>
                {a.differenzbesteuerung && (
                  <span className="text-[10px] px-1 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300 font-medium">§25a</span>
                )}
              </div>
              <div className="text-slate-400 dark:text-slate-500">
                {artikelNrAnzeige(a)} · {a.einheit} · {parseFloat(String(a.vk_brutto)).toFixed(2).replace('.', ',')} € (brutto)
              </div>
            </button>
          ))}
        </div>,
        document.body
      )}
    </div>
  )
}
