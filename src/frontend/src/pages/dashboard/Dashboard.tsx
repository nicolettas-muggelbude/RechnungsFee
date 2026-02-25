import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getKassenbuch, getUnternehmen } from '../../api/client'

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

function heuteIso(): string {
  return new Date().toISOString().slice(0, 10)
}

type FilterModus = 'monat' | 'datum' | 'zeitraum'

// ---------------------------------------------------------------------------
// Zufluss-Monitor für Transferleistungen (Bürgergeld / ALG I)
// ---------------------------------------------------------------------------

// Bürgergeld 2026: § 11b SGB II
const GRUNDFREIBETRAG = 100   // erste 100 € immer anrechnungsfrei
const OBERE_GRENZE   = 520   // bis 520 €: 20 % Freibetrag; darüber volle Anrechnung

function berechneEks(zufluss: number): { freibetrag: number; anrechenbar: number } {
  if (zufluss <= GRUNDFREIBETRAG) {
    return { freibetrag: zufluss, anrechenbar: 0 }
  }
  const freibetragErweiterung = Math.min(zufluss - GRUNDFREIBETRAG, OBERE_GRENZE - GRUNDFREIBETRAG) * 0.2
  const freibetrag = GRUNDFREIBETRAG + freibetragErweiterung
  const anrechenbar = Math.max(0, zufluss - freibetrag)
  return { freibetrag, anrechenbar }
}

function ZuflussMonitor({ zufluss }: { zufluss: number }) {
  const prozent = Math.min((zufluss / OBERE_GRENZE) * 100, 100)
  const { freibetrag, anrechenbar } = berechneEks(zufluss)

  let stufe: 'ok' | 'warn' | 'kritisch'
  if (zufluss <= GRUNDFREIBETRAG)       stufe = 'ok'
  else if (zufluss < OBERE_GRENZE)      stufe = 'warn'
  else                                   stufe = 'kritisch'

  const farben = {
    ok:       { balken: 'bg-green-500',  text: 'text-green-700',  bg: 'bg-green-50',  border: 'border-green-200' },
    warn:     { balken: 'bg-amber-400',  text: 'text-amber-700',  bg: 'bg-amber-50',  border: 'border-amber-200' },
    kritisch: { balken: 'bg-red-500',    text: 'text-red-700',    bg: 'bg-red-50',    border: 'border-red-200'   },
  }[stufe]

  return (
    <div className={`rounded-xl border ${farben.border} ${farben.bg} p-4 space-y-3`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
            Zufluss-Monitor
          </p>
          <p className="text-xs text-slate-400 mt-0.5">Bürgergeld-Grenzwert (§ 11b SGB II)</p>
        </div>
        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${farben.bg} ${farben.text} border ${farben.border}`}>
          {stufe === 'ok' ? 'Im Freibetrag' : stufe === 'warn' ? 'Achtung' : 'Grenze überschritten'}
        </span>
      </div>

      {/* Fortschrittsbalken */}
      <div>
        <div className="flex justify-between text-xs text-slate-400 mb-1">
          <span>0 €</span>
          <span className="text-slate-500 font-medium">{formatEuro(zufluss)}</span>
          <span>{OBERE_GRENZE} €</span>
        </div>
        <div className="h-3 bg-white rounded-full border border-slate-200 overflow-hidden relative">
          <div
            className={`h-full rounded-full transition-all ${farben.balken}`}
            style={{ width: `${prozent}%` }}
          />
          {/* Grundfreibetrag-Markierung */}
          <div
            className="absolute top-0 bottom-0 w-px bg-slate-400/60"
            style={{ left: `${(GRUNDFREIBETRAG / OBERE_GRENZE) * 100}%` }}
          />
        </div>
        <div className="flex justify-between text-[10px] text-slate-400 mt-0.5">
          <span />
          <span style={{ marginLeft: `${(GRUNDFREIBETRAG / OBERE_GRENZE) * 100 - 8}%` }}>
            100 €
          </span>
          <span />
        </div>
      </div>

      {/* Kennzahlen */}
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div>
          <span className="block text-slate-400">Monatlicher Zufluss</span>
          <span className="font-semibold text-slate-800">{formatEuro(zufluss)}</span>
        </div>
        <div>
          <span className="block text-slate-400">Freibetrag (ca.)</span>
          <span className="font-semibold text-green-700">{formatEuro(freibetrag)}</span>
        </div>
        <div>
          <span className="block text-slate-400">Anrechenbar (ca.)</span>
          <span className={`font-semibold ${anrechenbar > 0 ? farben.text : 'text-slate-400'}`}>
            {formatEuro(anrechenbar)}
          </span>
        </div>
      </div>

      {stufe === 'warn' && (
        <p className="text-xs text-amber-800">
          Dein monatlicher Zufluss liegt über dem Grundfreibetrag von 100 €. Melde deinen
          Gewinn über die EKS-Erklärung bei der Agentur für Arbeit.
        </p>
      )}
      {stufe === 'kritisch' && (
        <p className={`text-xs font-medium ${farben.text}`}>
          Der Zufluss übersteigt 520 €. Oberhalb dieser Grenze wird das Einkommen vollständig
          auf Bürgergeld angerechnet. Stelle sicher, dass deine EKS aktuell ist.
        </p>
      )}

      <p className="text-[10px] text-slate-400">
        Berechnungsgrundlage: § 11b Abs. 2 SGB II (Stand 2026). Privateinlagen sind
        ausgeschlossen. Kein Ersatz für individuelle Rechtsberatung.
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export function Dashboard() {
  const [filterModus, setFilterModus] = useState<FilterModus>('monat')
  const [monat, setMonat] = useState(aktuellerMonat)
  const [datum, setDatum] = useState(heuteIso)
  const [datumVon, setDatumVon] = useState(heuteIso)
  const [datumBis, setDatumBis] = useState(heuteIso)

  const filterParams =
    filterModus === 'monat'
      ? { monat }
      : filterModus === 'datum'
      ? { datum_von: datum, datum_bis: datum }
      : { datum_von: datumVon, datum_bis: datumBis }

  const { data: eintraege } = useQuery({
    queryKey: ['kassenbuch', filterModus, monat, datum, datumVon, datumBis],
    queryFn: () => getKassenbuch(filterParams),
  })

  const { data: unternehmen } = useQuery({
    queryKey: ['unternehmen'],
    queryFn: getUnternehmen,
    staleTime: 1000 * 60 * 10,
  })

  // Aktuellen Monat immer laden für Zufluss-Monitor
  const { data: aktuelleEintraege } = useQuery({
    queryKey: ['kassenbuch-aktuell', aktuellerMonat()],
    queryFn: () => getKassenbuch({ monat: aktuellerMonat() }),
    enabled: unternehmen?.bezieht_transferleistungen === true,
    staleTime: 1000 * 60 * 5,
  })

  const alle = eintraege ?? []

  // Betriebsbuchungen (ohne Privat)
  const betrieb = alle.filter((e) => e.kategorie_kontenart !== 'Privat')
  const privat  = alle.filter((e) => e.kategorie_kontenart === 'Privat')

  const einnahmen = betrieb
    .filter((e) => e.art === 'Einnahme')
    .reduce((s, e) => s + parseFloat(e.brutto_betrag), 0)
  const ausgaben = betrieb
    .filter((e) => e.art === 'Ausgabe')
    .reduce((s, e) => s + parseFloat(e.brutto_betrag), 0)
  const saldo = einnahmen - ausgaben
  const letzte5 = alle.slice(0, 5)

  // Zufluss für Monitor (Einnahmen excl. Privateinlagen, aktueller Monat)
  const zuflussMonat = (aktuelleEintraege ?? [])
    .filter((e) => e.art === 'Einnahme' && e.kategorie_kontenart !== 'Privat')
    .reduce((s, e) => s + parseFloat(e.brutto_betrag), 0)

  const loaded = eintraege !== undefined
  const hatPrivatbuchungen = privat.length > 0
  const zeigeZuflussMonitor = unternehmen?.bezieht_transferleistungen === true

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <h2 className="text-2xl font-bold text-slate-800">Dashboard</h2>

        {/* Zeitfilter */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-lg border border-slate-300 overflow-hidden text-sm">
            {(['monat', 'datum', 'zeitraum'] as FilterModus[]).map((m) => (
              <button
                key={m}
                onClick={() => setFilterModus(m)}
                className={`px-3 py-1.5 transition-colors ${
                  filterModus === m
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-slate-600 hover:bg-slate-50'
                }`}
              >
                {m === 'monat' ? 'Monat' : m === 'datum' ? 'Tag' : 'Zeitraum'}
              </button>
            ))}
          </div>

          {filterModus === 'monat' && (
            <input
              type="month"
              value={monat}
              onChange={(e) => setMonat(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          )}
          {filterModus === 'datum' && (
            <input
              type="date"
              value={datum}
              onChange={(e) => setDatum(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          )}
          {filterModus === 'zeitraum' && (
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={datumVon}
                onChange={(e) => setDatumVon(e.target.value)}
                className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-slate-400 text-sm">bis</span>
              <input
                type="date"
                value={datumBis}
                min={datumVon}
                onChange={(e) => setDatumBis(e.target.value)}
                className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}
        </div>
      </div>

      {/* Zufluss-Monitor */}
      {zeigeZuflussMonitor && (
        <div className="mb-6">
          <ZuflussMonitor zufluss={zuflussMonat} />
        </div>
      )}

      {/* Kacheln (nur Betriebsbuchungen) */}
      <div className="grid grid-cols-3 gap-4 mb-2">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-sm text-slate-500 mb-1">Betriebseinnahmen</p>
          <p className="text-2xl font-bold text-green-600">
            {loaded ? formatEuro(einnahmen) : '—'}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-sm text-slate-500 mb-1">Betriebsausgaben</p>
          <p className="text-2xl font-bold text-red-600">
            {loaded ? formatEuro(ausgaben) : '—'}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-sm text-slate-500 mb-1">Saldo</p>
          <p className={`text-2xl font-bold ${saldo >= 0 ? 'text-blue-600' : 'text-red-700'}`}>
            {loaded ? formatEuro(saldo) : '—'}
          </p>
        </div>
      </div>

      {/* Privat-Hinweis unter den Kacheln */}
      {hatPrivatbuchungen && (
        <p className="text-xs text-slate-400 mb-6 pl-1">
          🏠 {privat.length} Privatbuchung{privat.length !== 1 ? 'en' : ''} (
          {formatEuro(privat.reduce((s, e) => s + parseFloat(e.brutto_betrag), 0))}) im
          gewählten Zeitraum – nicht in den Kacheln enthalten.
        </p>
      )}
      {!hatPrivatbuchungen && <div className="mb-6" />}

      {/* Letzte Buchungen */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="px-5 py-3 border-b border-slate-100">
          <h3 className="font-semibold text-slate-700">Letzte Buchungen</h3>
        </div>
        {letzte5.length === 0 ? (
          <p className="text-slate-400 text-sm p-5">Keine Buchungen im gewählten Zeitraum.</p>
        ) : (
          <table className="w-full text-sm">
            <tbody>
              {letzte5.map((e) => (
                <tr key={e.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                  <td className="px-5 py-3 text-slate-500 w-28">{formatDatum(e.datum)}</td>
                  <td className="px-5 py-3 text-slate-400 w-32 font-mono text-xs">{e.belegnr}</td>
                  <td className="px-5 py-3 text-slate-700">
                    {e.beschreibung}
                    {e.kategorie_kontenart === 'Privat' && (
                      <span className="ml-1.5 text-[10px] text-purple-500 bg-purple-50 border border-purple-200 rounded px-1">
                        Privat
                      </span>
                    )}
                  </td>
                  <td className={`px-5 py-3 text-right font-medium ${
                    e.kategorie_kontenart === 'Privat'
                      ? 'text-slate-400'
                      : e.art === 'Einnahme' ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {e.art === 'Ausgabe' ? '−' : '+'}{formatEuro(e.brutto_betrag)}
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
