import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getRechnungen, type Rechnung } from '../../api/client'
import { useMxAuto } from '../../hooks/useAnsicht'

function formatEuro(val: number): string {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(val)
}

function formatDatum(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

function addTage(iso: string, tage: number): string {
  const d = new Date(iso)
  d.setDate(d.getDate() + tage)
  return d.toISOString().slice(0, 10)
}

type Filter = 'alle' | 'ueberfaellig' | 'diese_woche' | 'skonto'

type Zeile = Rechnung & {
  restbetrag: number
  skontoFrist: string | null
  ueberfaellig: boolean
  faelligDieseWoche: boolean
  skontoNochMoeglich: boolean
}

export function VerbindlichkeitenPage() {
  const mxAuto = useMxAuto()
  const navigate = useNavigate()
  const [filter, setFilter] = useState<Filter>('alle')

  const heute = new Date().toISOString().slice(0, 10)
  const inSiebenTagen = addTage(heute, 7)

  const { data = [], isLoading } = useQuery({
    queryKey: ['verbindlichkeiten'],
    queryFn: () => getRechnungen({
      typ: 'eingang', dokument_typ: 'Rechnung', zahlungsstatus: ['offen', 'teilweise'],
    }),
    staleTime: 1000 * 30,
  })

  const zeilen: Zeile[] = data
    .filter(r => !r.ist_entwurf)
    .map(r => {
      const restbetrag = parseFloat(r.brutto_gesamt) - parseFloat(r.bezahlt_betrag)
      const skontoFrist = r.skonto_tage ? addTage(r.datum, r.skonto_tage) : null
      return {
        ...r,
        restbetrag,
        skontoFrist,
        ueberfaellig: !!r.faellig_am && r.faellig_am < heute,
        faelligDieseWoche: !!r.faellig_am && r.faellig_am >= heute && r.faellig_am <= inSiebenTagen,
        skontoNochMoeglich: !!skontoFrist && skontoFrist >= heute,
      }
    })
    .sort((a, b) => (a.faellig_am ?? '9999-99-99').localeCompare(b.faellig_am ?? '9999-99-99'))

  const gefiltert = zeilen.filter(z => {
    if (filter === 'ueberfaellig') return z.ueberfaellig
    if (filter === 'diese_woche') return z.faelligDieseWoche
    if (filter === 'skonto') return z.skontoNochMoeglich
    return true
  })

  const summeGesamt = zeilen.reduce((s, z) => s + z.restbetrag, 0)
  const dieseWoche = zeilen.filter(z => z.faelligDieseWoche)
  const summeDieseWoche = dieseWoche.reduce((s, z) => s + z.restbetrag, 0)

  return (
    <div className={`max-w-4xl ${mxAuto} px-6 py-8`}>
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">
        Offene Verbindlichkeiten
      </h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        Alle unbezahlten Eingangsrechnungen mit Fälligkeit und Skonto-Frist – als Zahlungsvorschlag für die nächsten Tage.
      </p>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
          <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wide">Offene Verbindlichkeiten gesamt</p>
          <p className="text-xl font-bold text-slate-800 dark:text-slate-100 mt-1">{formatEuro(summeGesamt)}</p>
        </div>
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
          <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wide">Diese Woche fällig</p>
          <p className="text-xl font-bold text-amber-600 dark:text-amber-400 mt-1">
            {formatEuro(summeDieseWoche)} <span className="text-sm font-normal text-slate-400">({dieseWoche.length})</span>
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-3">
        {([
          ['alle', 'Alle'],
          ['ueberfaellig', 'Überfällig'],
          ['diese_woche', 'Diese Woche fällig'],
          ['skonto', 'Skonto noch möglich'],
        ] as [Filter, string][]).map(([f, label]) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
              filter === f
                ? 'bg-blue-600 border-blue-600 text-white'
                : 'border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
        {isLoading && <p className="p-4 text-sm text-slate-400">Lade…</p>}
        {!isLoading && gefiltert.length === 0 && (
          <p className="p-4 text-sm text-slate-400 italic">Keine offenen Verbindlichkeiten in dieser Auswahl.</p>
        )}
        {gefiltert.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-900 text-slate-500 dark:text-slate-400 text-[10px] uppercase tracking-wide">
                <th className="text-left px-4 py-2">Lieferant</th>
                <th className="text-left px-4 py-2 hidden sm:table-cell">Rechnungsdatum</th>
                <th className="text-left px-4 py-2">Fällig am</th>
                <th className="text-left px-4 py-2 hidden md:table-cell">Skonto-Frist</th>
                <th className="text-right px-4 py-2">Restbetrag</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
              {gefiltert.map(z => (
                <tr
                  key={z.id}
                  onClick={() => navigate(`/rechnungen?open=${z.id}`)}
                  className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/50"
                >
                  <td className="px-4 py-2.5 text-slate-800 dark:text-slate-100">
                    {z.lieferant_name ?? z.partner_freitext ?? '—'}
                    <span className="block text-[10px] text-slate-400 dark:text-slate-500 font-mono">
                      {z.rechnungsnummer ?? z.externe_belegnr ?? ''}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-slate-500 dark:text-slate-400 hidden sm:table-cell whitespace-nowrap">
                    {formatDatum(z.datum)}
                  </td>
                  <td className={`px-4 py-2.5 whitespace-nowrap ${z.ueberfaellig ? 'text-red-600 dark:text-red-400 font-medium' : 'text-slate-700 dark:text-slate-200'}`}>
                    {z.faellig_am ? formatDatum(z.faellig_am) : '—'}
                  </td>
                  <td className="px-4 py-2.5 hidden md:table-cell whitespace-nowrap">
                    {z.skontoFrist ? (
                      <span className={z.skontoNochMoeglich ? 'text-green-600 dark:text-green-400' : 'text-slate-400 dark:text-slate-500'}>
                        {z.skonto_prozent}% bis {formatDatum(z.skontoFrist)}
                      </span>
                    ) : (
                      <span className="text-slate-300 dark:text-slate-600">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap">
                    {formatEuro(z.restbetrag)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
