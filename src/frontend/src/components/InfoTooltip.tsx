import { useState } from 'react'

type HAlign = 'left' | 'center' | 'right'

interface Props {
  text: string
  side?: 'top' | 'bottom'
  align?: HAlign
  className?: string
}

export function InfoTooltip({ text, side = 'top', align = 'left', className = '' }: Props) {
  const [visible, setVisible] = useState(false)

  const hPos = align === 'left' ? 'left-0' : align === 'right' ? 'right-0' : 'left-1/2 -translate-x-1/2'
  const arrowH = align === 'left' ? 'left-3.5' : align === 'right' ? 'right-3.5' : 'left-1/2 -translate-x-1/2'

  const popupPos = side === 'top'
    ? `bottom-full ${hPos} mb-2`
    : `top-full ${hPos} mt-2`

  const arrowPos = side === 'top'
    ? `top-full ${arrowH} border-t-slate-700`
    : `bottom-full ${arrowH} border-b-slate-700`

  return (
    <span
      className={`relative inline-flex items-center ${className}`}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      <button
        type="button"
        className="text-slate-400 hover:text-slate-600 transition-colors focus:outline-none leading-none"
        onClick={e => { e.stopPropagation(); setVisible(v => !v) }}
        onFocus={() => setVisible(true)}
        onBlur={() => setVisible(false)}
        aria-label="Mehr Informationen"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
        </svg>
      </button>
      {visible && (
        <span className={`absolute ${popupPos} z-50 w-72 bg-slate-700 text-white text-xs rounded-lg px-3 py-2 shadow-xl leading-relaxed pointer-events-none`}>
          {text}
          <span className={`absolute ${arrowPos} border-[5px] border-transparent`} />
        </span>
      )}
    </span>
  )
}
