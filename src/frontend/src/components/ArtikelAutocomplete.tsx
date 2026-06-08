import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { sucheArtikel, type ArtikelSuche } from '../api/client'

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
  const ref = useRef<HTMLDivElement>(null)

  const { data: treffer } = useQuery({
    queryKey: ['artikel-suche', value],
    queryFn: () => sucheArtikel(value),
    enabled: value.length >= 2,
    staleTime: 1000 * 30,
  })

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOffen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const zeigeDropdown = offen && !!treffer?.length

  return (
    <div ref={ref} className={`relative ${className}`}>
      <input
        type="text"
        value={value}
        onChange={e => { onChange(e.target.value); setOffen(true) }}
        onFocus={() => value.length >= 2 && setOffen(true)}
        placeholder={placeholder}
        className={inputClassName ?? "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100 dark:placeholder-slate-400"}
      />
      {zeigeDropdown && (
        <div className="absolute top-full left-0 z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg min-w-64 max-h-52 overflow-y-auto mt-0.5">
          {treffer!.map(a => (
            <button
              key={a.id}
              type="button"
              onClick={() => { onArtikelWahl(a); setOffen(false) }}
              className="w-full text-left px-3 py-2 text-xs hover:bg-blue-50 dark:hover:bg-blue-950 border-b border-slate-100 dark:border-slate-700 last:border-0"
            >
              <div className="flex items-center gap-1.5">
                <span className="font-medium text-slate-800 dark:text-slate-100">{a.bezeichnung}</span>
                {a.differenzbesteuerung && (
                  <span className="text-[10px] px-1 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300 font-medium">§25a</span>
                )}
              </div>
              <div className="text-slate-400 dark:text-slate-500">
                {a.artikelnummer} · {a.einheit} · {parseFloat(a.vk_brutto).toFixed(2).replace('.', ',')} € (brutto)
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
