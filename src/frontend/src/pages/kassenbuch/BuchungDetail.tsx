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

function drucken(e: KassenbuchEintrag) {
  const win = window.open('', '_blank', 'width=600,height=700')
  if (!win) return
  const datum = e.datum.split('-').reverse().join('.')
  win.document.write(`
    <!DOCTYPE html><html><head>
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
    <h1>🧾 RechnungsFee – Beleg</h1>
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
    </body></html>
  `)
  win.document.close()
  win.focus()
  win.print()
}

export function BuchungDetail({ eintrag: e, bereitsStorniert, onClose }: Props) {
  const qc = useQueryClient()
  const [stornoGrund, setStornoGrund] = useState('')
  const [zeigStornoEingabe, setZeigStornoEingabe] = useState(false)

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

  return (
    <tr>
      <td colSpan={6} className="bg-slate-50 border-b border-slate-200 px-4 py-4">
        <div className="flex gap-6">

          {/* Linke Spalte: Betragsdetails */}
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
              Belegnr.: {e.belegnr} &nbsp;·&nbsp; {e.zahlungsart} &nbsp;·&nbsp; {new Date(e.erstellt_am).toLocaleString('de-DE')}
            </div>
          </div>

          {/* Mittlere Spalte: Kundendaten */}
          <div className="w-48 text-sm">
            {e.kunde_name ? (
              <div className="space-y-0.5">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Kunde</p>
                <p className="font-medium text-slate-800">{e.kunde_name}</p>
                {e.kunde_email && (
                  <a href={`mailto:${e.kunde_email}`} className="text-blue-600 hover:underline text-xs break-all">
                    {e.kunde_email}
                  </a>
                )}
              </div>
            ) : (
              <p className="text-slate-300 text-xs italic">Kein Kunde verknüpft</p>
            )}
          </div>

          {/* Rechte Spalte: Aktionen */}
          <div className="flex flex-col gap-2 w-40">
            <button
              onClick={() => drucken(e)}
              className="flex items-center gap-2 px-3 py-1.5 text-sm border border-slate-300 rounded-lg hover:bg-white text-slate-600"
            >
              🖨️ Drucken / PDF
            </button>

            {e.kunde_email && !istStorno && (
              <button
                onClick={() => window.open(`mailto:${e.kunde_email}?subject=Beleg ${e.belegnr}&body=Anbei dein Beleg vom ${e.datum.split('-').reverse().join('.')}.`)}
                className="flex items-center gap-2 px-3 py-1.5 text-sm border border-slate-300 rounded-lg hover:bg-white text-slate-600"
              >
                ✉️ Mail senden
              </button>
            )}

            {kannStorniert && !zeigStornoEingabe && (
              <button
                onClick={() => setZeigStornoEingabe(true)}
                className="flex items-center gap-2 px-3 py-1.5 text-sm border border-red-200 rounded-lg hover:bg-red-50 text-red-600"
              >
                ✕ Stornieren
              </button>
            )}

            {bereitsStorniert && (
              <span className="text-xs text-slate-400 italic">Bereits storniert</span>
            )}
          </div>
        </div>

        {/* Storno-Eingabe */}
        {zeigStornoEingabe && (
          <div className="mt-3 flex gap-2 items-center">
            <input
              type="text"
              value={stornoGrund}
              onChange={(e) => setStornoGrund(e.target.value)}
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
          <p className="mt-2 text-red-600 text-xs">{(stornoMutation.error as Error).message}</p>
        )}
      </td>
    </tr>
  )
}
