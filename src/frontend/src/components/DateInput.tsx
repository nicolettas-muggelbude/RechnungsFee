import { useState, useEffect, useRef } from 'react'

interface DateInputProps {
  value: string
  onChange: (value: string) => void
  required?: boolean
  className?: string
  min?: string
  max?: string
}

function isoToGerman(iso: string): string {
  if (!iso || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return ''
  return `${iso.slice(8, 10)}.${iso.slice(5, 7)}.${iso.slice(0, 4)}`
}

function germanToIso(s: string): string {
  const m = s.match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/)
  if (!m) return ''
  const dd = m[1].padStart(2, '0')
  const mm = m[2].padStart(2, '0')
  const y = m[3]
  if (parseInt(mm) < 1 || parseInt(mm) > 12) return ''
  if (parseInt(dd) < 1 || parseInt(dd) > 31) return ''
  const iso = `${y}-${mm}-${dd}`
  const dt = new Date(iso + 'T00:00:00')
  if (isNaN(dt.getTime())) return ''
  if (dt.getFullYear() !== parseInt(y) || dt.getMonth() + 1 !== parseInt(mm) || dt.getDate() !== parseInt(dd)) return ''
  return iso
}

export function DateInput({ value, onChange, required, className, min, max }: DateInputProps) {
  const [text, setText] = useState(() => isoToGerman(value))
  const [invalid, setInvalid] = useState(false)
  const prevValue = useRef(value)
  const hiddenRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (value !== prevValue.current) {
      prevValue.current = value
      setText(isoToGerman(value))
      setInvalid(false)
    }
  }, [value])

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const raw = e.target.value
    const adding = raw.length >= text.length

    let s = raw.replace(/[^0-9.]/g, '').replace(/\.{2,}/g, '.')

    if (adding) {
      const digits = s.replace(/\./g, '')
      if (digits.length === 2 && !s.includes('.')) {
        s = s + '.'
      } else if (digits.length === 4 && s.split('.').length === 2 && !s.endsWith('.')) {
        s = s + '.'
      }
    }

    const parts = s.split('.')
    if (parts.length === 3 && parts[2].length > 4) {
      s = `${parts[0]}.${parts[1]}.${parts[2].slice(0, 4)}`
    }

    setText(s)
    setInvalid(false)

    if (!s) {
      prevValue.current = ''
      onChange('')
      return
    }

    const iso = germanToIso(s)
    if (iso && (!min || iso >= min) && (!max || iso <= max)) {
      prevValue.current = iso
      onChange(iso)
    }
  }

  function handleBlur() {
    if (!text) { setInvalid(false); return }
    const iso = germanToIso(text)
    if (iso) {
      setInvalid(false)
      setText(isoToGerman(iso))
    } else {
      setInvalid(true)
    }
  }

  function openPicker() {
    const el = hiddenRef.current
    if (!el) return
    if (typeof (el as HTMLInputElement & { showPicker?: () => void }).showPicker === 'function') {
      (el as HTMLInputElement & { showPicker: () => void }).showPicker()
    } else {
      el.click()
    }
  }

  function handlePickerChange(e: React.ChangeEvent<HTMLInputElement>) {
    const iso = e.target.value
    if (!iso) return
    prevValue.current = iso
    setText(isoToGerman(iso))
    setInvalid(false)
    onChange(iso)
  }

  return (
    <div className="relative">
      <input
        type="text"
        inputMode="numeric"
        value={text}
        onChange={handleChange}
        onBlur={handleBlur}
        required={required}
        placeholder="TT.MM.JJJJ"
        maxLength={10}
        className={`${className ?? ''}${invalid ? ' !border-red-400 dark:!border-red-500' : ''} pr-8`}
      />
      <button
        type="button"
        onClick={openPicker}
        tabIndex={-1}
        title="Kalender öffnen"
        className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 focus:outline-none"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
          <line x1="16" y1="2" x2="16" y2="6"/>
          <line x1="8" y1="2" x2="8" y2="6"/>
          <line x1="3" y1="10" x2="21" y2="10"/>
        </svg>
      </button>
      <input
        ref={hiddenRef}
        type="date"
        value={prevValue.current}
        min={min}
        max={max}
        onChange={handlePickerChange}
        tabIndex={-1}
        className="absolute left-0 top-0 w-0 h-0 opacity-0 pointer-events-none"
      />
    </div>
  )
}
