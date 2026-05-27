import { useState, useRef } from 'react'
import { createPortal } from 'react-dom'

type HAlign = 'left' | 'center' | 'right'

interface Props {
  text: string
  side?: 'top' | 'bottom'
  align?: HAlign
  className?: string
}

export function InfoTooltip({ text, side = 'top', align = 'left', className = '' }: Props) {
  const [visible, setVisible] = useState(false)
  const [style, setStyle] = useState<React.CSSProperties>({})
  const ref = useRef<HTMLSpanElement>(null)

  function show() {
    if (!ref.current) return
    const r = ref.current.getBoundingClientRect()
    const tooltipW = 288 // w-72
    const rawLeft = align === 'right'
      ? r.right - tooltipW
      : align === 'center'
        ? r.left + r.width / 2 - tooltipW / 2
        : r.left
    const left = Math.max(4, Math.min(rawLeft, window.innerWidth - tooltipW - 4))

    if (side === 'top') {
      setStyle({ position: 'fixed', bottom: window.innerHeight - r.top + 8, left })
    } else {
      setStyle({ position: 'fixed', top: r.bottom + 8, left })
    }
    setVisible(true)
  }

  return (
    <span
      ref={ref}
      className={`relative inline-flex items-center ${className}`}
      onMouseEnter={show}
      onMouseLeave={() => setVisible(false)}
    >
      <button
        type="button"
        className="text-slate-400 hover:text-slate-600 transition-colors focus:outline-none leading-none"
        onClick={e => { e.stopPropagation(); setVisible(v => !v) }}
        onFocus={show}
        onBlur={() => setVisible(false)}
        aria-label="Mehr Informationen"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
        </svg>
      </button>
      {visible && createPortal(
        <span
          className="z-[200] w-72 bg-slate-700 text-white text-xs rounded-lg px-3 py-2 shadow-xl leading-relaxed pointer-events-none"
          style={style}
        >
          {text}
        </span>,
        document.body
      )}
    </span>
  )
}
