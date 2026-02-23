import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getKassenbuch, getKategorien, stornoKassenbuchEintrag } from '../../api/client'
import { BuchungForm } from './BuchungForm'
import { TagesabschlussDialog } from './TagesabschlussDialog'

function formatEuro(val: string | number): string {
  const n = typeof val === 'string' ? parseFloat(val) : val
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n)
}

function formatDatum(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

function aktuellerMonat(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

export function KassenbuchPage() {
  const qc = useQueryClient()
  const [monat, setMonat] = useState(aktuellerMonat)
  const [art, setArt] = useState<'' | 'Einnahme' | 'Ausgabe'>('')
  const [kategorieId, setKategorieId] = useState<string>('')
  const [showBuchung, setShowBuchung] = useState(false)
  const [showAbschluss, setShowAbschluss] = useState(false)

  const { data: eintraege, isLoading } = useQuery({
    queryKey: ['kassenbuch', monat, art, kategorieId],
    queryFn: () => getKassenbuch({
      monat,
      art: art || undefined,
      kategorie_id: kategorieId ? Number(kategorieId) : undefined,
    }),
  })

  const { data: kategorien } = useQuery({
    queryKey: ['kategorien'],
    queryFn: getKategorien,
  })

  // Belegnummern die bereits storniert wurden (aus der geladenen Liste ableiten)
  const bereitsStornieterteBelegnrn = new Set(
    (eintraege ?? [])
      .filter((e) => e.beschreibung.startsWith('STORNO '))
      .map((e) => e.beschreibung.split(':')[0].replace('STORNO ', '').trim())
  )

  const stornoMutation = useMutation({
    mutationFn: ({ id, grund }: { id: number; grund: string }) =>
      stornoKassenbuchEintrag(id, grund),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kassenbuch'] })
      qc.invalidateQueries({ queryKey: ['monats-uebersicht'] })
    },
  })

  function handleStorno(id: number, belegnr: string) {
    const grund = window.prompt(`Storno-Grund für ${belegnr}:`)
    if (!grund) return
    stornoMutation.mutate({ id, grund })
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-slate-800">Kassenbuch</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setShowAbschluss(true)}
            className="border border-slate-300 text-slate-600 rounded-lg px-4 py-2 text-sm hover:bg-slate-50"
          >
            Tagesabschluss
          </button>
          <button
            onClick={() => setShowBuchung(true)}
            className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700"
          >
            + Neue Buchung
          </button>
        </div>
      </div>

      {/* Filter */}
      <div className="flex gap-3 mb-4">
        <input
          type="month"
          value={monat}
          onChange={(e) => setMonat(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <select
          value={art}
          onChange={(e) => setArt(e.target.value as '' | 'Einnahme' | 'Ausgabe')}
          className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Alle Arten</option>
          <option value="Einnahme">Einnahmen</option>
          <option value="Ausgabe">Ausgaben</option>
        </select>
        <select
          value={kategorieId}
          onChange={(e) => setKategorieId(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Alle Kategorien</option>
          {(kategorien ?? []).map((k) => (
            <option key={k.id} value={k.id}>{k.name}</option>
          ))}
        </select>
      </div>

      {/* Tabelle */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {isLoading ? (
          <p className="text-slate-400 text-sm p-5">Lade…</p>
        ) : !eintraege?.length ? (
          <p className="text-slate-400 text-sm p-5">Keine Buchungen gefunden.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-left">
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 w-28">Datum</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 w-36">Belegnr.</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500">Beschreibung</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 w-24">Zahlung</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 text-right w-28">Einnahme</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 text-right w-28">Ausgabe</th>
                <th className="px-4 py-3 w-16"></th>
              </tr>
            </thead>
            <tbody>
              {eintraege.map((e) => (
                <tr key={e.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                  <td className="px-4 py-3 text-slate-500">{formatDatum(e.datum)}</td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-400">{e.belegnr}</td>
                  <td className="px-4 py-3 text-slate-700">
                    {e.beschreibung}
                    {e.steuerbefreiung_grund && (
                      <span className="ml-2 text-xs text-slate-400">({e.steuerbefreiung_grund})</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-500">{e.zahlungsart}</td>
                  <td className="px-4 py-3 text-right font-medium text-green-600">
                    {e.art === 'Einnahme' ? formatEuro(e.brutto_betrag) : ''}
                  </td>
                  <td className="px-4 py-3 text-right font-medium text-red-600">
                    {e.art === 'Ausgabe' ? formatEuro(e.brutto_betrag) : ''}
                  </td>
                  <td className="px-4 py-3">
                    {!e.beschreibung.startsWith('STORNO ') && !bereitsStornieterteBelegnrn.has(e.belegnr) && (
                      <button
                        onClick={() => handleStorno(e.id, e.belegnr)}
                        className="text-xs text-slate-400 hover:text-red-600"
                        title="Stornieren"
                      >
                        ✕
                      </button>
                    )}
                    {bereitsStornieterteBelegnrn.has(e.belegnr) && (
                      <span className="text-xs text-slate-300" title="Bereits storniert">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showBuchung && (
        <BuchungForm
          onClose={() => setShowBuchung(false)}
          onSuccess={() => setShowBuchung(false)}
        />
      )}
      {showAbschluss && (
        <TagesabschlussDialog
          onClose={() => setShowAbschluss(false)}
          onSuccess={() => setShowAbschluss(false)}
        />
      )}
    </div>
  )
}
