import { useState } from 'react'
import { sendeMailMitAnhang, type MahnungHistorieItem, type Unternehmen, type MailSendenRequest } from '../api/client'

interface Props {
  mahnung: MahnungHistorieItem
  unternehmen: Unternehmen | null | undefined
  onClose: () => void
  onGesendet?: () => void
}

function platzhalterErsetzen(vorlage: string, m: MahnungHistorieItem, unternehmen: Unternehmen | null | undefined): string {
  return vorlage
    .replace(/\{mahnnummer\}/g, m.mahnnummer ?? '—')
    .replace(/\{bezeichnung\}/g, m.bezeichnung ?? 'Mahnung')
    .replace(/\{rechnungsnummer\}/g, m.rechnungsnummern || '—')
    .replace(/\{kunde\}/g, m.kunde_name)
    .replace(/\{firmenname\}/g, unternehmen?.firmenname ?? '')
}

const DEFAULT_BETREFF = '{bezeichnung} – Rechnung {rechnungsnummer}'
const DEFAULT_TEXT =
  'Guten Tag {kunde},\n\nanbei erhalten Sie unser Schreiben „{bezeichnung}" zu Rechnung {rechnungsnummer}.\n\n' +
  'Bitte entnehmen Sie die Details dem beigefügten PDF.\n\nMit freundlichen Grüßen\n{firmenname}'

export function MahnungMailDialog({ mahnung, unternehmen, onClose, onGesendet }: Props) {
  const [an, setAn] = useState(mahnung.kunde_email ?? '')
  const [cc, setCc] = useState('')
  const [betreff, setBetreff] = useState(platzhalterErsetzen(DEFAULT_BETREFF, mahnung, unternehmen))
  const [text, setText] = useState(platzhalterErsetzen(DEFAULT_TEXT, mahnung, unternehmen))
  const [sendet, setSendet] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)
  const [gesendet, setGesendet] = useState(false)

  async function senden() {
    if (!an.trim()) return
    setSendet(true)
    setFehler(null)
    try {
      const req: MailSendenRequest = {
        an: an.trim(),
        cc: cc.trim() || undefined,
        betreff,
        text,
        mahnung_id: mahnung.id,
      }
      await sendeMailMitAnhang(req)
      setGesendet(true)
      onGesendet?.()
      setTimeout(onClose, 1500)
    } catch (e: any) {
      setFehler(e?.message ?? 'Unbekannter Fehler')
    } finally {
      setSendet(false)
    }
  }

  const inputCls = 'w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 dark:bg-slate-700 dark:text-slate-100'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-2xl flex flex-col gap-4 p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">
            ✉️ {mahnung.bezeichnung ?? 'Mahnung'} per Mail senden
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 text-lg leading-none">✕</button>
        </div>

        {gesendet ? (
          <div className="flex items-center gap-2 text-green-600 dark:text-green-400 text-sm font-medium py-4">
            ✓ Mail wurde gesendet
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-xs font-medium text-slate-500 dark:text-slate-400">An *</label>
                <input type="email" value={an} onChange={e => setAn(e.target.value)} className={inputCls} placeholder="empfaenger@beispiel.de" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs font-medium text-slate-500 dark:text-slate-400">CC</label>
                <input type="email" value={cc} onChange={e => setCc(e.target.value)} className={inputCls} placeholder="optional" />
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-slate-500 dark:text-slate-400">Betreff</label>
              <input type="text" value={betreff} onChange={e => setBetreff(e.target.value)} className={inputCls} />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-slate-500 dark:text-slate-400">Text</label>
              <textarea value={text} onChange={e => setText(e.target.value)} rows={8} className={inputCls + ' resize-y'} />
            </div>

            <div className="text-xs text-slate-400 dark:text-slate-500">
              Anhang: <span className="font-medium text-slate-600 dark:text-slate-300">{mahnung.mahnnummer ?? 'Mahnung'}.pdf</span>
              <span className="ml-2 text-amber-600 dark:text-amber-400">Gilt nach dem Versand als zugestellt – kein Entwurf mehr.</span>
            </div>

            {fehler && (
              <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 px-3 py-2 rounded-lg">{fehler}</div>
            )}

            <div className="flex gap-2 justify-end pt-1">
              <button onClick={onClose} className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                Abbrechen
              </button>
              <button onClick={senden} disabled={!an.trim() || sendet} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {sendet ? 'Wird gesendet…' : '✉️ Senden'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
