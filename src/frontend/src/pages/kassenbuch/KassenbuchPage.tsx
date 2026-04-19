import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getKassenbuch, getKategorien } from '../../api/client'
import { BuchungForm } from './BuchungForm'
import { TagesabschlussDialog } from './TagesabschlussDialog'
import { BuchungDetail } from './BuchungDetail'

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

type FilterModus = 'monat' | 'datum' | 'zeitraum' | 'jahr'

function heuteIso(): string {
  return new Date().toISOString().slice(0, 10)
}

export function KassenbuchPage() {
  const [filterModus, setFilterModus] = useState<FilterModus>('monat')
  const [monat, setMonat] = useState(aktuellerMonat)
  const [datum, setDatum] = useState(heuteIso)
  const [datumVon, setDatumVon] = useState(heuteIso)
  const [datumBis, setDatumBis] = useState(heuteIso)
  const [art, setArt] = useState<'' | 'Einnahme' | 'Ausgabe'>('')
  const [kategorieId, setKategorieId] = useState<string>('')
  const [showBuchung, setShowBuchung] = useState(false)
  const [showAbschluss, setShowAbschluss] = useState(false)
  const [aktiverEintragId, setAktiverEintragId] = useState<number | null>(null)

  const aktivesJahr = new Date().getFullYear()
  const filterParams = filterModus === 'monat'
    ? { monat }
    : filterModus === 'datum'
      ? { datum_von: datum, datum_bis: datum }
      : filterModus === 'zeitraum'
        ? { datum_von: datumVon, datum_bis: datumBis }
        : { datum_von: `${aktivesJahr}-01-01`, datum_bis: `${aktivesJahr}-12-31` }

  const { data: eintraege, isLoading } = useQuery({
    queryKey: ['kassenbuch', filterModus, monat, datum, datumVon, datumBis, art, kategorieId],
    queryFn: () => getKassenbuch({
      ...filterParams,
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

  function toggleEintrag(id: number) {
    setAktiverEintragId((prev) => (prev === id ? null : id))
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Kassenbuch</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setShowAbschluss(true)}
            className="border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg px-4 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-800"
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
      <div className="flex flex-wrap gap-3 mb-4 items-center">
        {/* Modus-Umschalter */}
        <div className="flex rounded-lg border border-slate-300 dark:border-slate-600 overflow-hidden text-sm">
          {(['monat', 'datum', 'zeitraum', 'alle'] as FilterModus[]).map((m) => (
            <button
              key={m}
              onClick={() => setFilterModus(m)}
              className={`px-3 py-1.5 capitalize transition-colors ${
                filterModus === m
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-slate-600 hover:bg-slate-50 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
              }`}
            >
              {m === 'monat' ? 'Monat' : m === 'datum' ? 'Tag' : m === 'zeitraum' ? 'Zeitraum' : 'Jahr'}
            </button>
          ))}
        </div>

        {/* Datums-Eingabe je nach Modus */}
        {filterModus === 'monat' && (
          <input
            type="month"
            value={monat}
            onChange={(e) => setMonat(e.target.value)}
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
          />
        )}
        {filterModus === 'datum' && (
          <input
            type="date"
            value={datum}
            onChange={(e) => setDatum(e.target.value)}
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
          />
        )}
        {filterModus === 'zeitraum' && (
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={datumVon}
              onChange={(e) => setDatumVon(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
            />
            <span className="text-slate-400 dark:text-slate-500 text-sm">bis</span>
            <input
              type="date"
              value={datumBis}
              min={datumVon}
              onChange={(e) => setDatumBis(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
            />
          </div>
        )}

        {/* Art + Kategorie */}
        <select
          value={art}
          onChange={(e) => setArt(e.target.value as '' | 'Einnahme' | 'Ausgabe')}
          className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
        >
          <option value="">Alle Arten</option>
          <option value="Einnahme">Einnahmen</option>
          <option value="Ausgabe">Ausgaben</option>
        </select>
        <select
          value={kategorieId}
          onChange={(e) => setKategorieId(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
        >
          <option value="">Alle Kategorien</option>
          {(kategorien ?? []).map((k) => (
            <option key={k.id} value={k.id}>{k.name}</option>
          ))}
        </select>
      </div>

      {/* Tabelle */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        {isLoading ? (
          <p className="text-slate-400 dark:text-slate-500 text-sm p-5">Lade…</p>
        ) : !eintraege?.length ? (
          <p className="text-slate-400 dark:text-slate-500 text-sm p-5">Keine Buchungen gefunden.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 text-left">
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 w-28">Datum</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 w-36">Belegnr.</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400">Beschreibung</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 w-24">Zahlung</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 text-right w-28">Einnahme</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 text-right w-28">Ausgabe</th>
              </tr>
            </thead>
            <tbody>
              {eintraege.map((e) => {
                const istAktiv = aktiverEintragId === e.id
                const bereitsStorniert = bereitsStornieterteBelegnrn.has(e.belegnr)
                const istStorno = e.beschreibung.startsWith('STORNO ')
                return (
                  <>
                    <tr
                      key={e.id}
                      onClick={() => toggleEintrag(e.id)}
                      className={`border-b border-slate-100 dark:border-slate-700 cursor-pointer select-none transition-colors ${
                        istAktiv ? 'bg-blue-50 dark:bg-blue-950' : istStorno ? 'hover:bg-slate-50 dark:hover:bg-slate-700 opacity-60' : 'hover:bg-slate-50 dark:hover:bg-slate-700'
                      }`}
                    >
                      <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{formatDatum(e.datum)}</td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-400 dark:text-slate-500 flex items-center gap-1">
                        <span className={`inline-block w-3 text-slate-300 dark:text-slate-600 transition-transform ${istAktiv ? 'rotate-90' : ''}`}>▶</span>
                        {e.belegnr}
                      </td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-200">
                        {e.beschreibung}
                        {e.steuerbefreiung_grund && (
                          <span className="ml-2 text-xs text-slate-400 dark:text-slate-500">({e.steuerbefreiung_grund})</span>
                        )}
                        {bereitsStorniert && (
                          <span className="ml-2 text-xs bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-500 rounded px-1">storniert</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{e.zahlungsart}</td>
                      <td className="px-4 py-3 text-right font-medium text-green-600">
                        {e.art === 'Einnahme' ? formatEuro(e.brutto_betrag) : ''}
                      </td>
                      <td className="px-4 py-3 text-right font-medium text-red-600">
                        {e.art === 'Ausgabe' ? formatEuro(e.brutto_betrag) : ''}
                      </td>
                    </tr>
                    {istAktiv && (
                      <BuchungDetail
                        key={`detail-${e.id}`}
                        eintrag={e}
                        bereitsStorniert={bereitsStorniert}
                        onClose={() => setAktiverEintragId(null)}
                      />
                    )}
                  </>
                )
              })}
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
