import { useState } from 'react'
import { sendeMailMitAnhang, type Rechnung, type Unternehmen, type MailSendenRequest } from '../api/client'
import { Modal } from './Modal'

type DokumentTyp = 'Rechnung' | 'Angebot' | 'Proforma' | 'Auftrag'

interface Props {
  dokument: Rechnung
  dokumentTyp: DokumentTyp
  unternehmen: Unternehmen | null | undefined
  onClose: () => void
}

function platzhalterErsetzen(vorlage: string, dok: Rechnung, unternehmen: Unternehmen | null | undefined): string {
  const datum = dok.datum ? dok.datum.split('-').reverse().join('.') : '—'
  const faellig = dok.faellig_am ? dok.faellig_am.split('-').reverse().join('.') : '—'
  const gueltig = (dok as any).gueltig_bis ? (dok as any).gueltig_bis.split('-').reverse().join('.') : '—'
  const brutto = (parseFloat(dok.brutto_gesamt as any) || 0).toFixed(2).replace('.', ',')
  const kunde = dok.kunde_name ?? dok.partner_freitext ?? ''
  const firma = unternehmen?.firmenname ?? ''

  return vorlage
    .replace(/\{rechnungsnummer\}/g, dok.rechnungsnummer ?? '—')
    .replace(/\{datum\}/g, datum)
    .replace(/\{betrag\}/g, brutto)
    .replace(/\{faellig_am\}/g, faellig)
    .replace(/\{gueltig_bis\}/g, gueltig)
    .replace(/\{kunde\}/g, kunde)
    .replace(/\{firmenname\}/g, firma)
}

const DEFAULT_BETREFF: Record<DokumentTyp, string> = {
  Rechnung: 'Rechnung {rechnungsnummer} – {firmenname}',
  Angebot:  'Angebot {rechnungsnummer} – {firmenname}',
  Proforma: 'Proforma-Rechnung {rechnungsnummer} – {firmenname}',
  Auftrag:  'Auftragsbestätigung {rechnungsnummer} – {firmenname}',
}

const DEFAULT_TEXT: Record<DokumentTyp, string> = {
  Rechnung: 'Guten Tag {kunde},\n\nanbei erhalten Sie unsere Rechnung {rechnungsnummer} vom {datum} über {betrag} €.\n\nZahlungsziel: {faellig_am}\n\nMit freundlichen Grüßen\n{firmenname}',
  Angebot:  'Guten Tag {kunde},\n\nanbei finden Sie unser Angebot {rechnungsnummer} vom {datum} über {betrag} €.\n\nGültig bis: {gueltig_bis}\n\nMit freundlichen Grüßen\n{firmenname}',
  Proforma: 'Guten Tag {kunde},\n\nanbei erhalten Sie unsere Proforma-Rechnung {rechnungsnummer} vom {datum} über {betrag} €.\n\nBitte begleichen Sie den Betrag bis zum {faellig_am}.\n\nMit freundlichen Grüßen\n{firmenname}',
  Auftrag:  'Guten Tag {kunde},\n\nvielen Dank für Ihren Auftrag. Anbei finden Sie Ihre Auftragsbestätigung {rechnungsnummer} vom {datum} über {betrag} €.\n\nMit freundlichen Grüßen\n{firmenname}',
}

function getVorlage(typ: DokumentTyp, u: Unternehmen | null | undefined): { betreff: string; text: string } {
  if (!u) return { betreff: DEFAULT_BETREFF[typ], text: DEFAULT_TEXT[typ] }
  const betreff = (
    typ === 'Rechnung'  ? u.mail_betreff_vorlage :
    typ === 'Angebot'   ? u.mail_betreff_angebot :
    typ === 'Proforma'  ? u.mail_betreff_proforma :
                          u.mail_betreff_auftrag
  ) ?? DEFAULT_BETREFF[typ]
  const text = (
    typ === 'Rechnung'  ? u.mail_text_vorlage :
    typ === 'Angebot'   ? u.mail_text_angebot :
    typ === 'Proforma'  ? u.mail_text_proforma :
                          u.mail_text_auftrag
  ) ?? DEFAULT_TEXT[typ]
  return { betreff, text }
}

export function MailDialog({ dokument, dokumentTyp, unternehmen, onClose }: Props) {
  const vorlage = getVorlage(dokumentTyp, unternehmen)
  const [an, setAn] = useState(dokument.kunde_email ?? '')
  const [cc, setCc] = useState('')
  const [betreff, setBetreff] = useState(platzhalterErsetzen(vorlage.betreff, dokument, unternehmen))
  const [text, setText] = useState(platzhalterErsetzen(vorlage.text, dokument, unternehmen))
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
        rechnung_id: dokument.id,
        dokumentenpaket_id: dokument.dokumentenpaket_id ?? undefined,
      }
      await sendeMailMitAnhang(req)
      setGesendet(true)
      setTimeout(onClose, 1500)
    } catch (e: any) {
      setFehler(e?.message ?? 'Unbekannter Fehler')
    } finally {
      setSendet(false)
    }
  }

  const inputCls = 'w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 dark:bg-slate-700 dark:text-slate-100'

  return (
    <Modal
      title={<>✉️ {dokumentTyp} per Mail senden</>}
      onClose={onClose}
      panelClassName="bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-2xl flex flex-col gap-4 p-6 max-h-[90vh] overflow-y-auto"
     
    >
      <div className="flex items-center justify-end">
        <button onClick={onClose} aria-label="Dialog schließen" className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 text-lg leading-none">✕</button>
      </div>

      {gesendet ? (
        <div className="flex items-center gap-2 text-green-600 dark:text-green-400 text-sm font-medium py-4">
          ✓ Mail wurde gesendet
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <label htmlFor="mail-an" className="text-xs font-medium text-slate-500 dark:text-slate-400">An *</label>
              <input id="mail-an" aria-required="true" type="email" value={an} onChange={e => setAn(e.target.value)} className={inputCls} placeholder="empfaenger@beispiel.de" />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="mail-cc" className="text-xs font-medium text-slate-500 dark:text-slate-400">CC</label>
              <input id="mail-cc" type="email" value={cc} onChange={e => setCc(e.target.value)} className={inputCls} placeholder="optional" />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="mail-betreff" className="text-xs font-medium text-slate-500 dark:text-slate-400">Betreff</label>
            <input id="mail-betreff" type="text" value={betreff} onChange={e => setBetreff(e.target.value)} className={inputCls} />
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="mail-text" className="text-xs font-medium text-slate-500 dark:text-slate-400">Text</label>
            <textarea id="mail-text" value={text} onChange={e => setText(e.target.value)} rows={8} className={inputCls + ' resize-y'} />
          </div>

          <div className="text-xs text-slate-400 dark:text-slate-500">
            Anhänge:{' '}
            {/* Issue #530: öffentlicher Auftraggeber – Backend hängt die XRechnung-XML (Original) vorn an */}
            {dokument.kunde_oeffentlich && !dokument.ist_entwurf && !dokument.storniert && (
              <span className="font-medium text-slate-600 dark:text-slate-300">XRechnung_{dokument.rechnungsnummer ?? dokument.id}.xml + </span>
            )}
            <span className="font-medium text-slate-600 dark:text-slate-300">{dokumentTyp}_{dokument.rechnungsnummer ?? dokument.id}.pdf</span>
            {dokument.kunde_oeffentlich && !dokument.ist_entwurf && <span className="ml-1">(Sichtkopie)</span>}
            {dokument.dokumentenpaket_id && <span className="ml-2">+ Dokumentenpaket</span>}
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
    </Modal>
  )
}
