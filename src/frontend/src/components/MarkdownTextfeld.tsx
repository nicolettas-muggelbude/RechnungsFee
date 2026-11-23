import { useRef, type ReactNode, type TextareaHTMLAttributes } from 'react'

/**
 * Issue #583: Textfeld mit Formatierleiste statt reinem Markdown-Hinweis.
 * Knöpfe/Kürzel setzen die Markdown-Zeichen um die Auswahl (bzw. an die Schreibmarke) oder
 * entfernen sie wieder. Gespeichert wird weiter Markdown - PDF und Mail bleiben unverändert.
 * Optional eine kleine Vorschau (fett/kursiv/Zeilenumbruch, ohne HTML - kein innerHTML).
 */
type Props = Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'value' | 'onChange'> & {
  value: string
  onChange: (wert: string) => void
  /** Knopf für Links ([Text](URL)) - nur wo die Ausgabe Links kann (Mail-Signatur) */
  links?: boolean
  /** Vorschau unter dem Feld (fett, kursiv, Zeilenumbrüche) */
  vorschau?: boolean
}

const KNOPF = 'min-w-7 h-7 px-1.5 text-xs rounded border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500'

export default function MarkdownTextfeld({ value, onChange, links = false, vorschau = false, onKeyDown, ...rest }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null)

  function setzeAuswahl(start: number, ende: number) {
    requestAnimationFrame(() => {
      const ta = ref.current
      if (!ta) return
      ta.focus()
      ta.setSelectionRange(start, ende)
    })
  }

  /** Umschließt die Auswahl mit `zeichen`; ist sie schon umschlossen, wird es entfernt. */
  function umschliessen(zeichen: string, platzhalter: string) {
    const ta = ref.current
    if (!ta) return
    const { selectionStart: s, selectionEnd: e } = ta
    const n = zeichen.length
    const davor = value.slice(s - n, s)
    const danach = value.slice(e, e + n)
    // bei * nicht in ein ** hinein greifen (fett ≠ kursiv)
    const echt = zeichen !== '*' || (value[s - n - 1] !== '*' && value[e + n] !== '*')
    if (davor === zeichen && danach === zeichen && echt) {
      onChange(value.slice(0, s - n) + value.slice(s, e) + value.slice(e + n))
      setzeAuswahl(s - n, e - n)
      return
    }
    const text = value.slice(s, e) || platzhalter
    onChange(value.slice(0, s) + zeichen + text + zeichen + value.slice(e))
    setzeAuswahl(s + n, s + n + text.length)
  }

  function link() {
    const ta = ref.current
    if (!ta) return
    const { selectionStart: s, selectionEnd: e } = ta
    const text = value.slice(s, e) || 'Linktext'
    const neu = `[${text}](https://)`
    onChange(value.slice(0, s) + neu + value.slice(e))
    const urlStart = s + text.length + 3
    setzeAuswahl(urlStart, urlStart + 8)
  }

  function tasten(ev: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((ev.ctrlKey || ev.metaKey) && !ev.altKey && !ev.shiftKey) {
      const k = ev.key.toLowerCase()
      if (k === 'b') { ev.preventDefault(); umschliessen('**', 'fett') }
      else if (k === 'i') { ev.preventDefault(); umschliessen('*', 'kursiv') }
      else if (k === 'k' && links) { ev.preventDefault(); link() }
    }
    onKeyDown?.(ev)
  }

  return (
    <div>
      <div role="toolbar" aria-label="Formatierung" className="flex items-center gap-1 mb-1">
        <button type="button" className={`${KNOPF} font-bold`} title="Fett (Strg+B)" aria-label="Fett"
          onMouseDown={e => e.preventDefault()} onClick={() => umschliessen('**', 'fett')}>F</button>
        <button type="button" className={`${KNOPF} italic font-serif`} title="Kursiv (Strg+I)" aria-label="Kursiv"
          onMouseDown={e => e.preventDefault()} onClick={() => umschliessen('*', 'kursiv')}>K</button>
        {links && (
          <button type="button" className={KNOPF} title="Link (Strg+K)" aria-label="Link"
            onMouseDown={e => e.preventDefault()} onClick={link}>🔗</button>
        )}
        <span className="ml-1 text-[11px] text-slate-400 dark:text-slate-500">Text markieren, dann Knopf oder Strg+B / Strg+I · Zeilenumbruch mit Enter</span>
      </div>
      <textarea ref={ref} value={value} onChange={e => onChange(e.target.value)} onKeyDown={tasten} {...rest} />
      {vorschau && value.trim() && (
        <div className="mt-1 rounded-lg border border-dashed border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs text-slate-600 dark:text-slate-300" aria-label="Vorschau">
          <span className="text-[10px] uppercase tracking-wide text-slate-400 dark:text-slate-500 mr-2">Vorschau</span>
          {markdownVorschau(value)}
        </div>
      )}
    </div>
  )
}

/** fett/kursiv/Zeilenumbruch als React-Elemente - gleiche Regeln wie im PDF (`_md()` im Backend). */
export function markdownVorschau(text: string): ReactNode[] {
  const zeilen = text.split('\n')
  return zeilen.flatMap((zeile, zi) => {
    const teile: ReactNode[] = []
    // ohne Lookbehind - ältere WebKitGTK-Versionen (Linux) brechen sonst beim Laden ab
    const re = /\*\*(.+?)\*\*|\*([^*\n]+?)\*/g
    let rest = 0
    let m: RegExpExecArray | null
    while ((m = re.exec(zeile))) {
      if (m.index > rest) teile.push(zeile.slice(rest, m.index))
      teile.push(m[1] !== undefined
        ? <strong key={`${zi}-${m.index}`}>{m[1]}</strong>
        : <em key={`${zi}-${m.index}`}>{m[2]}</em>)
      rest = m.index + m[0].length
    }
    if (rest < zeile.length) teile.push(zeile.slice(rest))
    return zi < zeilen.length - 1 ? [...teile, <br key={`br-${zi}`} />] : teile
  })
}
