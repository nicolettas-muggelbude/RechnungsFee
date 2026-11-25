/** Issue #596: Druck-/Versandverlauf eines Dokuments bzw. eines Kunden/Lieferanten. */
import { useQuery } from '@tanstack/react-query'
import { getPartnerVerlauf, type VerlaufEintrag } from '../api/client'

function zeit(iso: string): string {
  return new Date(iso).toLocaleString('de-DE', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function symbol(e: VerlaufEintrag): string {
  if (e.art.startsWith('mahnung')) return '⚠️'
  if (e.kanal === 'druck') return '🖨️'
  if (e.kanal === 'smtp') return '✉️'
  if (e.kanal === 'thunderbird' || e.kanal === 'mailprogramm') return '📤'
  return '✔️'
}

export function verlaufText(e: VerlaufEintrag): string {
  const an = e.empfaenger ? ` an ${e.empfaenger}` : ''
  const kopie = e.kopie ? ' (Kopie)' : ''
  const mahnung = e.mahnnummer ? `Mahnung ${e.mahnnummer}` : 'Mahnung'
  switch (e.art) {
    case 'ausgegeben': return 'Ausgegeben (Weg nicht erfasst)'
    case 'gedruckt': return `Zum Drucken geöffnet${kopie}`
    case 'pdf': return `PDF geöffnet${kopie}`
    case 'mail_gesendet': return `Per Mail gesendet${an}${kopie}`
    case 'mail_uebergeben':
      return `${e.kanal === 'thunderbird' ? 'An Thunderbird' : 'An das Mailprogramm'} übergeben${an}${kopie}`
    case 'mahnung_gesendet': return e.kanal === 'unbekannt' ? `${mahnung} versendet` : `${mahnung} per Mail gesendet${an}`
    case 'mahnung_uebergeben':
      return `${mahnung} ${e.kanal === 'thunderbird' ? 'an Thunderbird' : 'an das Mailprogramm'} übergeben${an}`
    case 'mahnung_gedruckt': return `${mahnung} zum Drucken geöffnet`
    default: return e.art
  }
}

/** Spalte „Versand“ in der Rechnungsliste: Symbol des letzten Versands, Details als Tooltip. */
export function VersandSymbol({ eintrag }: { eintrag?: VerlaufEintrag | null }) {
  if (!eintrag) return <span className="text-slate-300 dark:text-slate-600" title="Noch nicht gedruckt oder versendet">–</span>
  const text = `${verlaufText(eintrag)} · ${zeit(eintrag.zeitpunkt)}`
  return <span title={text} aria-label={text}>{symbol(eintrag)}</span>
}

const DOKUMENT_KURZ: Record<string, string> = {
  Rechnung: 'Rechnung', Gutschrift: 'Gutschrift', Lieferschein: 'Lieferschein', Angebot: 'Angebot',
  Auftrag: 'Auftrag', Proforma: 'Proforma', Abschlagsrechnung: 'Abschlagsrechnung',
}

/** Reiter „Verlauf“ im Kunden-/Lieferantenstamm: alle Ereignisse zu dessen Dokumenten, neueste zuerst. */
export function PartnerVerlauf({ art, id }: { art: 'kunde' | 'lieferant'; id: number }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['partner-verlauf', art, id],
    queryFn: () => getPartnerVerlauf(art, id),
  })
  if (isLoading) return <p className="text-xs text-slate-400 dark:text-slate-500 p-1">Lade…</p>
  if (error) return <p className="text-xs text-red-600 dark:text-red-400 p-1">{(error as Error).message}</p>
  return (
    <div className="p-1">
      <VerlaufListe
        eintraege={data ?? []}
        mitDokument
        leerText="Noch keine Dokumente gedruckt oder versendet."
      />
    </div>
  )
}

/** Zeitleiste. mitDokument: im Kunden-/Lieferantenstamm zusätzlich Dokument und Nummer zeigen. */
export function VerlaufListe({ eintraege, mitDokument = false, leerText }: {
  eintraege: VerlaufEintrag[]
  mitDokument?: boolean
  leerText?: string
}) {
  if (!eintraege.length) {
    return <p className="text-xs text-slate-400 dark:text-slate-500">{leerText ?? 'Noch nicht gedruckt oder versendet.'}</p>
  }
  return (
    <ol className="space-y-1.5">
      {eintraege.map((e) => (
        <li key={e.id} className="flex gap-2 text-xs">
          <span className="shrink-0" aria-hidden="true">{symbol(e)}</span>
          <div className="min-w-0">
            <p className="text-slate-700 dark:text-slate-200">
              {mitDokument && e.rechnungsnummer && (
                <span className="font-medium">{DOKUMENT_KURZ[e.dokument_typ ?? ''] ?? 'Dokument'} {e.rechnungsnummer}: </span>
              )}
              {verlaufText(e)}
            </p>
            <p className="text-slate-400 dark:text-slate-500">
              {zeit(e.zeitpunkt)}
              {e.betreff ? ` · „${e.betreff}"` : ''}
            </p>
          </div>
        </li>
      ))}
    </ol>
  )
}
