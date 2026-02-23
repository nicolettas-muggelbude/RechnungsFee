import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { stornoKassenbuchEintrag, type KassenbuchEintrag } from '../../api/client'

interface Props {
  eintrag: KassenbuchEintrag
  bereitsStorniert: boolean
  onClose: () => void
}

function formatEuro(val: string): string {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(parseFloat(val))
}

function belegHtml(e: KassenbuchEintrag): string {
  const datum = e.datum.split('-').reverse().join('.')
  return `<!DOCTYPE html><html><head>
    <meta charset="utf-8">
    <title>Beleg ${e.belegnr}</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 40px; color: #1e293b; }
      h1 { font-size: 18px; margin-bottom: 4px; }
      .meta { color: #64748b; font-size: 13px; margin-bottom: 24px; }
      table { width: 100%; border-collapse: collapse; margin-top: 16px; }
      td { padding: 8px 0; border-bottom: 1px solid #e2e8f0; font-size: 14px; }
      td:last-child { text-align: right; }
      .label { color: #64748b; }
      .total { font-weight: bold; font-size: 16px; }
      .footer { margin-top: 40px; font-size: 12px; color: #94a3b8; }
    </style>
    </head><body>
    <h1>RechnungsFee – Beleg</h1>
    <div class="meta">${e.belegnr} &nbsp;·&nbsp; ${datum} &nbsp;·&nbsp; ${e.art}</div>
    ${e.kunde_name ? `<p><strong>Kunde:</strong> ${e.kunde_name}${e.kunde_email ? ' &lt;' + e.kunde_email + '&gt;' : ''}</p>` : ''}
    <table>
      <tr><td class="label">Beschreibung</td><td>${e.beschreibung}</td></tr>
      <tr><td class="label">Zahlungsart</td><td>${e.zahlungsart}</td></tr>
      <tr><td class="label">Netto</td><td>${formatEuro(e.netto_betrag)}</td></tr>
      <tr><td class="label">USt (${e.ust_satz} %)</td><td>${formatEuro(e.ust_betrag)}</td></tr>
      ${e.steuerbefreiung_grund ? `<tr><td class="label">Steuerbefreiung</td><td>${e.steuerbefreiung_grund}</td></tr>` : ''}
      <tr class="total"><td>Brutto</td><td>${formatEuro(e.brutto_betrag)}</td></tr>
    </table>
    <div class="footer">Erstellt mit RechnungsFee &nbsp;·&nbsp; ${new Date().toLocaleDateString('de-DE')}</div>
    </body></html>`
}

function oeffneBelegFenster(e: KassenbuchEintrag, drucken: boolean) {
  const win = window.open('', '_blank', 'width=640,height=750')
  if (!win) return
  win.document.write(belegHtml(e))
  win.document.close()
  win.focus()
  if (drucken) win.print()
}

export function BuchungDetail({ eintrag: e, bereitsStorniert, onClose }: Props) {
  const qc = useQueryClient()
  const [stornoGrund, setStornoGrund] = useState('')
  const [zeigStornoEingabe, setZeigStornoEingabe] = useState(false)
  const [zeigMailEingabe, setZeigMailEingabe] = useState(false)
  const [mailAdresse, setMailAdresse] = useState('')

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
    const body = encodeURIComponent(
      `Anbei dein Beleg vom ${datum}.\n\nBeleg-Nr.: ${e.belegnr}\nBetrag: ${formatEuro(e.brutto_betrag)}`
    )
    window.open(`mailto:${email}?subject=${subject}&body=${body}`)
    setZeigMailEingabe(false)
    setMailAdresse('')
  }

  return (
    <tr>
      <td colSpan={6} className="bg-slate-50 border-b border-slate-200 px-4 py-4">

        {/* Aktionsleiste – waagerecht als erste Zeile */}
        <div className="flex flex-wrap gap-2 mb-4">
          <button
            onClick={() => oeffneBelegFenster(e, true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 rounded-lg hover:bg-white text-slate-600"
          >
            🖨️ Drucken
          </button>
          <button
            onClick={() => oeffneBelegFenster(e, false)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 rounded-lg hover:bg-white text-slate-600"
          >
            📄 PDF öffnen
          </button>
          {!istStorno && (
            <button
              onClick={handleMail}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 rounded-lg hover:bg-white text-slate-600"
            >
              ✉️ Mail senden{!e.kunde_email ? ' …' : ''}
            </button>
          )}
          {kannStorniert && !zeigStornoEingabe && (
            <button
              onClick={() => setZeigStornoEingabe(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-red-200 rounded-lg hover:bg-red-50 text-red-600"
            >
              ✕ Stornieren
            </button>
          )}
          {bereitsStorniert && (
            <span className="self-center text-xs text-slate-400 italic">Bereits storniert</span>
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
              className="flex-1 border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
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
              className="px-3 py-1.5 border border-slate-300 text-slate-600 rounded-lg text-sm hover:bg-slate-50"
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
              className="flex-1 border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
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
              className="px-3 py-1.5 border border-slate-300 text-slate-600 rounded-lg text-sm hover:bg-slate-50"
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
            <div className="flex justify-between text-slate-500">
              <span>Netto</span>
              <span>{formatEuro(e.netto_betrag)}</span>
            </div>
            <div className="flex justify-between text-slate-500">
              <span>USt {e.ust_satz} %</span>
              <span>{formatEuro(e.ust_betrag)}</span>
            </div>
            {e.steuerbefreiung_grund && (
              <div className="text-xs text-slate-400">{e.steuerbefreiung_grund}</div>
            )}
            <div className="flex justify-between font-semibold text-slate-800 border-t border-slate-200 pt-1">
              <span>Brutto</span>
              <span>{formatEuro(e.brutto_betrag)}</span>
            </div>
            <div className="text-xs text-slate-400 pt-1">
              {e.zahlungsart} &nbsp;·&nbsp; {new Date(e.erstellt_am).toLocaleString('de-DE')}
            </div>
          </div>

          <div className="w-52 text-sm">
            {e.kunde_name ? (
              <div className="space-y-0.5">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Kunde</p>
                <p className="font-medium text-slate-800">{e.kunde_name}</p>
                {e.kunde_email ? (
                  <a href={`mailto:${e.kunde_email}`} className="text-blue-600 hover:underline text-xs break-all">
                    {e.kunde_email}
                  </a>
                ) : (
                  <p className="text-xs text-slate-400 italic">Keine E-Mail hinterlegt</p>
                )}
              </div>
            ) : (
              <p className="text-slate-300 text-xs italic">Kein Kunde verknüpft</p>
            )}
          </div>
        </div>

      </td>
    </tr>
  )
}
