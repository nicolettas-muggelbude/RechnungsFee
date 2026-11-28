import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getCockpitUeberleitung, type UeberleitungZeile } from '../api/client'

// Issue #603 Stufe 3: Woher kommt der Unterschied zwischen den Dashboard-Kacheln (brutto,
// alle Zahlungen) und dem Cockpit (netto, nur EÜR-relevant)? Gleicher Zeitraum wie die Kacheln.

const euro = (v: number) => new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(v)

function CockpitWert({ z, seite }: { z: UeberleitungZeile; seite: 'eingaenge' | 'ausgaenge' }) {
  const eigen = seite === 'eingaenge' ? z.cockpit_einnahmen : z.cockpit_ausgaben
  const fremd = seite === 'eingaenge' ? z.cockpit_ausgaben : z.cockpit_einnahmen
  const fremdLabel = seite === 'eingaenge' ? 'bei Ausgaben' : 'bei Einnahmen'
  if (eigen === 0 && fremd === 0) return <span className="text-slate-400 dark:text-slate-500">–</span>
  return (
    <span className="tabular-nums">
      {eigen !== 0 && euro(eigen)}
      {fremd !== 0 && (
        <span className="block text-xs text-slate-500 dark:text-slate-400">{euro(fremd)} {fremdLabel}</span>
      )}
    </span>
  )
}

function Tabelle({ titel, zeilen, seite, onKategorie }: {
  titel: string
  zeilen: UeberleitungZeile[]
  seite: 'eingaenge' | 'ausgaenge'
  onKategorie: (z: UeberleitungZeile, seite: 'eingaenge' | 'ausgaenge') => void
}) {
  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">{titel}</h3>
      {zeilen.length === 0 ? (
        <p className="text-sm text-slate-400 dark:text-slate-500">Keine Buchungen im Zeitraum.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">
              <th scope="col" className="py-1.5 pr-3 font-semibold">Kategorie</th>
              <th scope="col" className="py-1.5 pr-3 font-semibold text-right">Kachel (brutto)</th>
              <th scope="col" className="py-1.5 pr-3 font-semibold text-right">Cockpit (netto)</th>
              <th scope="col" className="py-1.5 font-semibold">Warum</th>
            </tr>
          </thead>
          <tbody>
            {zeilen.map((z) => {
              const unveraendert = z.grund === 'Zählt unverändert.'
              return (
                <tr key={`${z.kategorie_id}`} className="border-b border-slate-100 dark:border-slate-700/60 align-top">
                  <td className="py-1.5 pr-3">
                    {z.kategorie_id !== null ? (
                      <button
                        type="button"
                        onClick={() => onKategorie(z, seite)}
                        className="text-left text-blue-600 dark:text-blue-400 hover:underline"
                        title="Buchungen dieser Kategorie im Journal anzeigen"
                      >
                        {z.kategorie}
                      </button>
                    ) : z.kategorie}
                    <span className="block text-xs text-slate-400 dark:text-slate-500">
                      {z.anzahl} Buchung{z.anzahl !== 1 ? 'en' : ''}{z.euer_zeile ? ` · EÜR-Zeile ${z.euer_zeile}` : ''}
                    </span>
                  </td>
                  <td className="py-1.5 pr-3 text-right tabular-nums">{euro(z.brutto)}</td>
                  <td className="py-1.5 pr-3 text-right"><CockpitWert z={z} seite={seite} /></td>
                  <td className={`py-1.5 text-xs ${unveraendert ? 'text-slate-400 dark:text-slate-500' : 'text-slate-600 dark:text-slate-300'}`}>{z.grund}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </section>
  )
}

export function UeberleitungDialog({ von, bis, zeitraumLabel, onClose, onKategorie }: {
  von: string
  bis: string
  zeitraumLabel: string
  onClose: () => void
  onKategorie: (z: UeberleitungZeile, seite: 'eingaenge' | 'ausgaenge') => void
}) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['cockpit-ueberleitung', von, bis],
    queryFn: () => getCockpitUeberleitung(von, bis),
  })

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const s = data?.summen

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="ueberleitung-titel"
        className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-start justify-between gap-4">
          <div>
            <h2 id="ueberleitung-titel" className="font-semibold text-slate-800 dark:text-slate-100">Woher kommt der Unterschied?</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {zeitraumLabel}: Kacheln (brutto, alle Zahlungen) im Vergleich zum Cockpit (netto, nur was für den Gewinn zählt)
            </p>
          </div>
          <button onClick={onClose} aria-label="Schließen" className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 text-xl leading-none">×</button>
        </div>

        <div className="overflow-y-auto px-6 py-4 space-y-6">
          {isLoading && <p className="text-sm text-slate-400">Lade…</p>}
          {isError && <p className="text-sm text-red-600">Die Aufschlüsselung konnte nicht geladen werden.</p>}
          {data && s && (
            <>
              <div className="grid grid-cols-2 gap-4 text-sm">
                {([
                  ['Eingänge', s.kachel_eingaenge, 'Einnahmen', s.cockpit_einnahmen],
                  ['Ausgänge', s.kachel_ausgaenge, 'Ausgaben', s.cockpit_ausgaben],
                ] as const).map(([kLabel, kWert, cLabel, cWert]) => (
                  <div key={kLabel} className="rounded-xl border border-slate-200 dark:border-slate-700 p-4 space-y-1">
                    <div className="flex justify-between"><span className="text-slate-500 dark:text-slate-400">Kachel Zahlungs{kLabel.toLowerCase()} (brutto)</span><span className="tabular-nums font-medium">{euro(kWert)}</span></div>
                    <div className="flex justify-between"><span className="text-slate-500 dark:text-slate-400">Cockpit {cLabel} (netto)</span><span className="tabular-nums font-medium">{euro(cWert)}</span></div>
                    <div className="flex justify-between border-t border-slate-100 dark:border-slate-700 pt-1"><span className="text-slate-500 dark:text-slate-400">Unterschied</span><span className="tabular-nums font-semibold">{euro(kWert - cWert)}</span></div>
                  </div>
                ))}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Die Tabellen zeigen je Kategorie, was in der Kachel steht und was davon im Cockpit zählt. Ein Storno steht bei der Gegenrichtung (das Storno einer Ausgabe ist ein Zahlungseingang) und mindert im Cockpit die ursprüngliche Seite. Ein Klick auf eine Kategorie öffnet ihre Buchungen im Journal. Das Cockpit-Widget auf dem Dashboard zeigt immer den laufenden Monat, diese Aufschlüsselung dagegen den Zeitraum der Kacheln.
              </p>
              <Tabelle titel="Zahlungseingänge" zeilen={data.eingaenge} seite="eingaenge" onKategorie={onKategorie} />
              <Tabelle titel="Zahlungsausgänge" zeilen={data.ausgaenge} seite="ausgaenge" onKategorie={onKategorie} />
              {data.nicht_in_kacheln.length > 0 && (
                <Tabelle titel="Nur im Cockpit (nicht in den Kacheln)" zeilen={data.nicht_in_kacheln} seite="eingaenge" onKategorie={onKategorie} />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
