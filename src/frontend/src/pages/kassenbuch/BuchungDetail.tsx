import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { stornoKassenbuchEintrag, getUnternehmen, getKassenbuchBelegUrl, openUrl, type KassenbuchEintrag } from '../../api/client'
import { InfoTooltip } from '../../components/InfoTooltip'

interface Props {
  eintrag: KassenbuchEintrag
  bereitsStorniert: boolean
  onClose: () => void
}

function formatEuro(val: string): string {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(parseFloat(val))
}

async function oeffneBelegFenster(id: number, drucken: boolean) {
  const url = await getKassenbuchBelegUrl(id, drucken)
  await openUrl(url)
}

export function BuchungDetail({ eintrag: e, bereitsStorniert, onClose }: Props) {
  const qc = useQueryClient()
  const [stornoGrund, setStornoGrund] = useState('')
  const [zeigStornoEingabe, setZeigStornoEingabe] = useState(false)
  const [zeigMailEingabe, setZeigMailEingabe] = useState(false)
  const [mailAdresse, setMailAdresse] = useState('')
  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen, staleTime: 1000 * 60 * 10 })

  const stornoMutation = useMutation({
    mutationFn: () => stornoKassenbuchEintrag(e.id, stornoGrund),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kassenbuch'] })
      qc.invalidateQueries({ queryKey: ['monats-uebersicht'] })
      onClose()
    },
  })

  const istStorno = e.beschreibung.startsWith('STORNO ')
  const kannStorniert = !istStorno && !bereitsStorniert
  const datum = e.datum.split('-').reverse().join('.')

  function handleMail() {
    const email = e.kunde_email || mailAdresse.trim()
    if (!email) {
      setZeigMailEingabe(true)
      return
    }
    const subject = encodeURIComponent(`Beleg ${e.belegnr}`)
    let bodyText = `Anbei dein Beleg vom ${datum}.\n\nBeleg-Nr.: ${e.belegnr}\nBetrag: ${formatEuro(e.brutto_betrag)}`
    if (unternehmen?.mail_signatur) {
      bodyText += `\n\n${unternehmen.mail_signatur}`
    }
    const body = encodeURIComponent(bodyText)
    window.location.href = `mailto:${email}?subject=${subject}&body=${body}`
    setZeigMailEingabe(false)
    setMailAdresse('')
  }

  return (
    <tr>
      <td colSpan={6} className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 px-4 py-4">

        {/* Aktionsleiste – waagerecht als erste Zeile */}
        <div className="flex flex-wrap gap-2 mb-4">
          <button
            onClick={() => oeffneBelegFenster(e.id, true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-white dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
          >
            🖨️ Drucken
          </button>
          <button
            onClick={() => oeffneBelegFenster(e.id, false)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-white dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
          >
            📄 PDF öffnen
          </button>
          {!istStorno && (
            <button
              onClick={handleMail}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-white dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
            >
              ✉️ Mail senden{!e.kunde_email ? ' …' : ''}
            </button>
          )}
          {kannStorniert && !zeigStornoEingabe && (
            <div className="flex items-center gap-1">
              <button
                onClick={() => setZeigStornoEingabe(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-red-200 rounded-lg hover:bg-red-50 text-red-600"
              >
                ✕ Stornieren
              </button>
              <InfoTooltip text="Kassenbucheinträge sind nach GoBD §146 unveränderbar – löschen ist nicht erlaubt. Eine Stornierung erzeugt einen Gegeneintrag mit negativem Betrag. Beide Buchungen bleiben sichtbar und bilden gemeinsam die korrekte Buchungshistorie." side="bottom" />
            </div>
          )}
          {bereitsStorniert && (
            <span className="self-center text-xs text-slate-400 dark:text-slate-500 italic">Bereits storniert</span>
          )}
        </div>

        {/* Mail-Eingabe (wenn kein Kunde oder keine E-Mail hinterlegt) */}
        {zeigMailEingabe && (
          <div className="mb-3 flex gap-2 items-center">
            <input
              type="email"
              value={mailAdresse}
              onChange={(ev) => setMailAdresse(ev.target.value)}
              placeholder="E-Mail-Adresse eingeben…"
              className="flex-1 border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100 dark:placeholder-slate-400"
              autoFocus
              onKeyDown={(ev) => ev.key === 'Enter' && handleMail()}
            />
            <button
              onClick={handleMail}
              disabled={!mailAdresse.trim()}
              className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              Öffnen
            </button>
            <button
              onClick={() => { setZeigMailEingabe(false); setMailAdresse('') }}
              className="px-3 py-1.5 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg text-sm hover:bg-slate-50 dark:hover:bg-slate-700"
            >
              Abbrechen
            </button>
          </div>
        )}

        {/* Storno-Eingabe */}
        {zeigStornoEingabe && (
          <div className="mb-3 flex gap-2 items-center">
            <input
              type="text"
              value={stornoGrund}
              onChange={(ev) => setStornoGrund(ev.target.value)}
              placeholder="Storno-Grund eingeben…"
              className="flex-1 border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-400 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100 dark:placeholder-slate-400"
              autoFocus
            />
            <button
              onClick={() => stornoMutation.mutate()}
              disabled={!stornoGrund.trim() || stornoMutation.isPending}
              className="px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700 disabled:opacity-50"
            >
              {stornoMutation.isPending ? '…' : 'Bestätigen'}
            </button>
            <button
              onClick={() => { setZeigStornoEingabe(false); setStornoGrund('') }}
              className="px-3 py-1.5 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg text-sm hover:bg-slate-50 dark:hover:bg-slate-700"
            >
              Abbrechen
            </button>
          </div>
        )}
        {stornoMutation.isError && (
          <p className="mb-3 text-red-600 text-xs">{(stornoMutation.error as Error).message}</p>
        )}

        {/* Betragsdetails + Kundendaten */}
        <div className="flex gap-6">
          <div className="flex-1 text-sm space-y-1">
            <div className="flex justify-between text-slate-500 dark:text-slate-400">
              <span>Netto</span>
              <span>{formatEuro(e.netto_betrag)}</span>
            </div>
            <div className="flex justify-between text-slate-500 dark:text-slate-400">
              <span>USt {e.ust_satz} %</span>
              <span>{formatEuro(e.ust_betrag)}</span>
            </div>
            {e.steuerbefreiung_grund && (
              <div className="text-xs text-slate-400 dark:text-slate-500">{e.steuerbefreiung_grund}</div>
            )}
            <div className="flex justify-between font-semibold text-slate-800 dark:text-slate-100 border-t border-slate-200 dark:border-slate-700 pt-1">
              <span>Brutto</span>
              <span>{formatEuro(e.brutto_betrag)}</span>
            </div>
            <div className="text-xs text-slate-400 dark:text-slate-500 pt-1">
              {e.externe_belegnr && <span>Ext. Belegnr.: {e.externe_belegnr} &nbsp;·&nbsp;</span>}
              {e.zahlungsart} &nbsp;·&nbsp; {new Date(e.erstellt_am).toLocaleString('de-DE')}
            </div>
          </div>

          <div className="w-52 text-sm">
            {e.kunde_name ? (
              <div className="space-y-0.5">
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Kunde</p>
                <p className="font-medium text-slate-800 dark:text-slate-100">{e.kunde_name}</p>
                {e.kunde_email ? (
                  <a href={`mailto:${e.kunde_email}`} className="text-blue-600 dark:text-blue-400 hover:underline text-xs break-all">
                    {e.kunde_email}
                  </a>
                ) : (
                  <p className="text-xs text-slate-400 dark:text-slate-500 italic">Keine E-Mail hinterlegt</p>
                )}
              </div>
            ) : (
              <p className="text-slate-300 dark:text-slate-600 text-xs italic">Kein Kunde verknüpft</p>
            )}
          </div>
        </div>

      </td>
    </tr>
  )
}
