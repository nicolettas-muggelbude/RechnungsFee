/**
 * Datenauskunft nach Art. 15 DSGVO per Mail senden (Issue #526) – für Kunden und Lieferanten.
 * Gleiche drei Versandwege wie bei Rechnungen: Thunderbird (falls aktiviert), SMTP-Dialog,
 * sonst PDF speichern + Standard-Mailprogramm öffnen. Abgeschickt wird immer von Hand:
 * Vor einer Auskunft muss geprüft werden, ob die Anfrage wirklich von der Person stammt
 * (Art. 12 Abs. 6 DSGVO) – ein vollautomatischer Versand würde das übergehen.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  getApiBase, getUnternehmen, isTauri, openUrl, sendeMailMitAnhang, speichereBlob,
  type MailSendenRequest, type Unternehmen,
} from '../api/client'
import { sendeUeberThunderbird, ThunderbirdNichtGefundenError } from '../utils/thunderbirdVersand'

type Art = 'kunde' | 'lieferant'

interface Props {
  art: Art
  id: number
  name: string
  email: string | null | undefined
}

const IDENTITAET_HINWEIS =
  'Bitte vorher prüfen, ob die Anfrage wirklich von dieser Person stammt (Art. 12 Abs. 6 DSGVO) – sonst gehen die Daten im Zweifel an die Falschen.'

function vorlage(name: string, firma: string) {
  return {
    betreff: `Auskunft über Ihre gespeicherten Daten (Art. 15 DSGVO)${firma ? ` – ${firma}` : ''}`,
    text:
      `Guten Tag${name ? ` ${name}` : ''},\n\n` +
      'wie gewünscht erhalten Sie im Anhang eine Übersicht der Daten, die wir zu Ihrer Person gespeichert haben (Auskunft nach Art. 15 DSGVO).\n\n' +
      'Wir verarbeiten diese Daten zur Abwicklung unserer Geschäftsbeziehung und zur Erfüllung gesetzlicher Aufbewahrungspflichten (§ 147 AO, § 257 HGB).\n\n' +
      'Bei Fragen oder wenn Sie eine Berichtigung oder Löschung wünschen, melden Sie sich gern.\n\n' +
      `Mit freundlichen Grüßen\n${firma}`,
  }
}

function dateiname(name: string): string {
  const heute = new Date().toLocaleDateString('sv-SE')
  return `dsgvo-${(name || 'auskunft').replace(/[^\p{L}\p{N}._-]+/gu, '-')}-${heute}.pdf`
}

async function pdfUrl(art: Art, id: number): Promise<string> {
  const base = await getApiBase()
  return `${base}/${art === 'kunde' ? 'kunden' : 'lieferanten'}/${id}/dsgvo-export-pdf`
}

export function DsgvoMailButton({ art, id, name, email }: Props) {
  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen, staleTime: 1000 * 60 * 5 })
  const [zeigDialog, setZeigDialog] = useState(false)
  const [laeuft, setLaeuft] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)
  const [hinweis, setHinweis] = useState<string | null>(null)

  async function klick() {
    setFehler(null)
    setHinweis(null)
    if (unternehmen?.smtp_aktiv && !unternehmen?.thunderbird_aktiv) { setZeigDialog(true); return }
    if (!window.confirm(`Datenauskunft an ${name || 'diese Person'} senden?\n\n${IDENTITAET_HINWEIS}`)) return

    const { betreff, text } = vorlage(name, unternehmen?.firmenname ?? '')
    setLaeuft(true)
    try {
      if (unternehmen?.thunderbird_aktiv) {
        await sendeUeberThunderbird({
          an: email ?? '',
          betreff,
          text,
          anhaenge: [{ url: await pdfUrl(art, id), dateiname: dateiname(name) }],
        })
        return
      }
      // Kein SMTP/Thunderbird: PDF speichern, Mailprogramm öffnen – Anhang von Hand einfügen
      const res = await fetch(await pdfUrl(art, id))
      if (!res.ok) throw new Error(`PDF konnte nicht erzeugt werden (${res.status})`)
      await speichereBlob(await res.blob(), dateiname(name))
      const mailto = `mailto:${email ?? ''}?subject=${encodeURIComponent(betreff)}&body=${encodeURIComponent(text)}`
      if (isTauri()) await openUrl(mailto)
      else window.location.href = mailto
      setHinweis('Die PDF wurde gespeichert – bitte in deinem Mailprogramm als Anhang einfügen.')
    } catch (e) {
      setFehler(
        e instanceof ThunderbirdNichtGefundenError
          ? 'Thunderbird wurde nicht gefunden. Prüfe die Einstellung unter Einstellungen → Unternehmen → E-Mail.'
          : e instanceof Error ? e.message : 'Unbekannter Fehler',
      )
    } finally {
      setLaeuft(false)
    }
  }

  return (
    <>
      <button type="button" onClick={klick} disabled={laeuft}
        title={`Datenauskunft (PDF) per Mail senden. ${IDENTITAET_HINWEIS}`}
        className="flex-1 text-xs border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg py-1.5 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50">
        {laeuft ? '…' : '✉️ Auskunft per Mail'}
      </button>
      {(fehler || hinweis) && (
        <p className={`basis-full text-xs ${fehler ? 'text-red-600 dark:text-red-400' : 'text-slate-500 dark:text-slate-400'}`}>
          {fehler ?? hinweis}
        </p>
      )}
      {zeigDialog && (
        <DsgvoMailDialog art={art} id={id} name={name} email={email} unternehmen={unternehmen}
          onClose={() => setZeigDialog(false)} />
      )}
    </>
  )
}

function DsgvoMailDialog({ art, id, name, email, unternehmen, onClose }: Props & {
  unternehmen: Unternehmen | null | undefined
  onClose: () => void
}) {
  const start = vorlage(name, unternehmen?.firmenname ?? '')
  const [an, setAn] = useState(email ?? '')
  const [cc, setCc] = useState('')
  const [betreff, setBetreff] = useState(start.betreff)
  const [text, setText] = useState(start.text)
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
        ...(art === 'kunde' ? { dsgvo_kunde_id: id } : { dsgvo_lieferant_id: id }),
      }
      await sendeMailMitAnhang(req)
      setGesendet(true)
      setTimeout(onClose, 1500)
    } catch (e) {
      setFehler(e instanceof Error ? e.message : 'Unbekannter Fehler')
    } finally {
      setSendet(false)
    }
  }

  const inputCls = 'w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 dark:bg-slate-700 dark:text-slate-100'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div role="dialog" aria-modal="true" aria-labelledby="dsgvo-mail-titel"
        className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-2xl flex flex-col gap-4 p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h2 id="dsgvo-mail-titel" className="text-base font-semibold text-slate-800 dark:text-slate-100">
            ✉️ Datenauskunft per Mail senden
          </h2>
          <button onClick={onClose} aria-label="Schließen" className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 text-lg leading-none">✕</button>
        </div>

        {gesendet ? (
          <div className="flex items-center gap-2 text-green-600 dark:text-green-400 text-sm font-medium py-4">
            ✓ Mail wurde gesendet
          </div>
        ) : (
          <>
            <p className="text-xs text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 px-3 py-2 rounded-lg">
              {IDENTITAET_HINWEIS}
            </p>
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
              <textarea value={text} onChange={e => setText(e.target.value)} rows={10} className={inputCls + ' resize-y'} />
            </div>
            <div className="text-xs text-slate-400 dark:text-slate-500">
              Anhang: <span className="font-medium text-slate-600 dark:text-slate-300">{dateiname(name)}</span>
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
