import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getTagesabschluesse,
  pruefeTagesabschlussSignatur,
  downloadTagesabschlussPdf,
  type Tagesabschluss,
} from '../../api/client'
import { TagesabschlussDialog } from './TagesabschlussDialog'
import { InfoTooltip } from '../../components/InfoTooltip'

// ---------------------------------------------------------------------------
// Hilfsfunktionen
// ---------------------------------------------------------------------------

function formatEuro(val: string | number): string {
  const n = typeof val === 'string' ? parseFloat(val) : val
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n)
}

function formatDatum(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

function formatUhrzeit(hms: string): string {
  return hms.slice(0, 5) + ' Uhr'
}

// ---------------------------------------------------------------------------
// Zählprotokoll aus JSON parsen und darstellen
// ---------------------------------------------------------------------------

const SCHEINE_LABEL: Record<string, string> = {
  '500': '500,00 €', '200': '200,00 €', '100': '100,00 €',
  '50': '50,00 €',   '20': '20,00 €',   '10': '10,00 €',  '5': '5,00 €',
}
const MUENZEN_LABEL: Record<string, string> = {
  '200': '2,00 €',  '100': '1,00 €',  '50': '0,50 €', '20': '0,20 €',
  '10': '0,10 €',   '5': '0,05 €',    '2': '0,02 €',  '1': '0,01 €',
}

function ZaehlprotokollAnzeige({ json }: { json: string }) {
  let parsed: { scheine?: Record<string, number>; muenzen_cent?: Record<string, number> }
  try {
    parsed = JSON.parse(json)
  } catch {
    return <p className="text-xs text-slate-400 italic">Zählprotokoll-Daten ungültig.</p>
  }

  const scheineZeilen = Object.entries(parsed.scheine ?? {})
    .filter(([, anz]) => anz > 0)
    .map(([wert, anz]) => ({
      label: SCHEINE_LABEL[wert] ?? `${wert} €`,
      anzahl: anz,
      betrag: parseInt(wert) * anz,
    }))

  const muenzenZeilen = Object.entries(parsed.muenzen_cent ?? {})
    .filter(([, anz]) => anz > 0)
    .map(([cent, anz]) => ({
      label: MUENZEN_LABEL[cent] ?? `${cent} Ct`,
      anzahl: anz,
      betrag: (parseInt(cent) / 100) * anz,
    }))

  if (scheineZeilen.length === 0 && muenzenZeilen.length === 0) {
    return <p className="text-xs text-slate-400 italic">Alle Positionen waren 0.</p>
  }

  const gesamt =
    scheineZeilen.reduce((s, z) => s + z.betrag, 0) +
    muenzenZeilen.reduce((s, z) => s + z.betrag, 0)

  return (
    <div className="text-xs border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
      {scheineZeilen.length > 0 && (
        <>
          <div className="bg-slate-50 dark:bg-slate-900 px-3 py-1 text-slate-500 dark:text-slate-400 font-medium border-b border-slate-200 dark:border-slate-700">
            Scheine
          </div>
          {scheineZeilen.map((z) => (
            <div key={z.label} className="grid grid-cols-[1fr_40px_80px] px-3 py-1 gap-2 border-b border-slate-100 dark:border-slate-700 dark:bg-slate-800">
              <span className="text-slate-700 dark:text-slate-200">{z.label}</span>
              <span className="text-right text-slate-500 dark:text-slate-400">× {z.anzahl}</span>
              <span className="text-right font-medium dark:text-slate-200">{formatEuro(z.betrag)}</span>
            </div>
          ))}
        </>
      )}
      {muenzenZeilen.length > 0 && (
        <>
          <div className="bg-slate-50 dark:bg-slate-900 px-3 py-1 text-slate-500 dark:text-slate-400 font-medium border-b border-slate-200 dark:border-slate-700">
            Münzen
          </div>
          {muenzenZeilen.map((z) => (
            <div key={z.label} className="grid grid-cols-[1fr_40px_80px] px-3 py-1 gap-2 border-b border-slate-100 dark:border-slate-700 dark:bg-slate-800">
              <span className="text-slate-700 dark:text-slate-200">{z.label}</span>
              <span className="text-right text-slate-500 dark:text-slate-400">× {z.anzahl}</span>
              <span className="text-right font-medium dark:text-slate-200">{formatEuro(z.betrag)}</span>
            </div>
          ))}
        </>
      )}
      <div className="grid grid-cols-[1fr_40px_80px] px-3 py-1.5 gap-2 bg-slate-50 dark:bg-slate-900 font-semibold text-slate-700 dark:text-slate-200">
        <span className="col-span-2">Gesamt</span>
        <span className="text-right">{formatEuro(gesamt)}</span>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Signatur-Block
// ---------------------------------------------------------------------------

type SignaturErgebnis = { gueltig: boolean; gespeichert: string | null; berechnet: string }

function SignaturBlock({ abschluss }: { abschluss: Tagesabschluss }) {
  const [ergebnis, setErgebnis] = useState<SignaturErgebnis | null>(null)
  const [laden, setLaden] = useState(false)

  async function pruefen() {
    setLaden(true)
    try {
      const res = await pruefeTagesabschlussSignatur(abschluss.id)
      setErgebnis(res)
    } finally {
      setLaden(false)
    }
  }

  const hash = abschluss.signatur

  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-semibold text-slate-600 dark:text-slate-300 flex items-center gap-1">
          Integritätsprüfung (SHA-256)
          <InfoTooltip text="Jeder Eintrag wird mit einem SHA-256-Hash digital signiert. Damit kann bei einer Betriebsprüfung bewiesen werden, dass keine nachträglichen Änderungen vorgenommen wurden (GoBD-Konformität nach §146 AO)." />
        </span>
        <button
          onClick={pruefen}
          disabled={laden}
          className="text-xs px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 disabled:opacity-50 transition-colors shrink-0 dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-slate-200 dark:border-slate-600"
        >
          {laden ? 'Prüfe…' : ergebnis ? 'Erneut prüfen' : 'Prüfen'}
        </button>
      </div>

      {hash ? (
        <p className="font-mono text-[11px] text-slate-400 dark:text-slate-500 break-all">{hash}</p>
      ) : (
        <p className="text-xs text-amber-600 dark:text-amber-400 italic">Keine Signatur gespeichert (Altdaten vor GoBD-Update).</p>
      )}

      {ergebnis && (
        <div className={`rounded-md px-3 py-2 text-xs font-medium ${
          ergebnis.gueltig
            ? 'bg-green-50 text-green-700 border border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800'
            : 'bg-red-50 text-red-700 border border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-800'
        }`}>
          {ergebnis.gueltig ? (
            '✓ Signatur gültig – Datensatz wurde seit dem Abschluss nicht verändert.'
          ) : (
            <>
              ✗ Signatur ungültig – mögliche Manipulation!
              <div className="mt-1.5 space-y-0.5 font-normal text-[11px] font-mono">
                <div><span className="text-red-500">Gespeichert:</span> {ergebnis.gespeichert ?? '(leer)'}</div>
                <div><span className="text-red-500">Berechnet:  </span> {ergebnis.berechnet}</div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Detail-Panel eines einzelnen Abschlusses
// ---------------------------------------------------------------------------

function AbschlussDetail({ a }: { a: Tagesabschluss }) {
  const differenz = parseFloat(a.differenz)
  const hatDifferenz = Math.abs(differenz) > 0.005

  function exportEinzel() {
    // Datum als Monat exportieren (einzelner Tag liegt immer in einem Monat)
    const monat = a.datum.slice(0, 7) // YYYY-MM
    downloadTagesabschlussPdf({ zeitraum: 'monat', wert: monat })
  }

  return (
    <div className="px-4 pb-4 pt-3 border-t border-slate-100 dark:border-slate-700 space-y-4 bg-slate-50/50 dark:bg-slate-900/50">
      {/* Kennzahlen */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <div>
          <span className="block text-xs text-slate-400 dark:text-slate-500 mb-0.5">Anfangsbestand</span>
          <span className="font-medium dark:text-slate-200">{formatEuro(a.anfangsbestand)}</span>
        </div>
        <div>
          <span className="block text-xs text-slate-400 dark:text-slate-500 mb-0.5">Einnahmen (Bar)</span>
          <span className="font-medium text-green-600">{formatEuro(a.einnahmen_bar)}</span>
        </div>
        <div>
          <span className="block text-xs text-slate-400 dark:text-slate-500 mb-0.5">Ausgaben (Bar)</span>
          <span className="font-medium text-red-600">{formatEuro(a.ausgaben_bar)}</span>
        </div>
        <div>
          <span className="block text-xs text-slate-400 dark:text-slate-500 mb-0.5">Buchungen gesamt</span>
          <span className="font-medium dark:text-slate-200">{a.kassenbewegungen_anzahl}</span>
        </div>
      </div>

      {/* Differenz-Begründung */}
      {hatDifferenz && (
        <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg px-3 py-2 text-sm">
          <span className="font-medium text-amber-700 dark:text-amber-300">
            Differenz {formatEuro(a.differenz)}
          </span>
          {a.differenz_buchungsart && (
            <span className="ml-2 text-amber-600 dark:text-amber-400 text-xs">· {a.differenz_buchungsart}</span>
          )}
          {a.differenz_begruendung && (
            <p className="text-amber-600 dark:text-amber-400 text-xs mt-0.5">{a.differenz_begruendung}</p>
          )}
        </div>
      )}

      {/* Zählprotokoll */}
      <div>
        <p className="text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1.5">Zählprotokoll</p>
        {a.zaehlung_json ? (
          <ZaehlprotokollAnzeige json={a.zaehlung_json} />
        ) : (
          <p className="text-xs text-slate-400 italic">Kein Zählprotokoll erfasst.</p>
        )}
      </div>

      {/* Signatur */}
      <SignaturBlock abschluss={a} />

      {/* Einzel-Export */}
      <div className="flex justify-end">
        <button
          onClick={exportEinzel}
          className="text-xs px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-colors flex items-center gap-1.5"
        >
          <span>↓</span> PDF exportieren
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Differenz-Statistik
// ---------------------------------------------------------------------------

function DifferenzStatistik({ abschluesse }: { abschluesse: Tagesabschluss[] }) {
  if (abschluesse.length === 0) return null

  const gesamt = abschluesse.length
  const mitDifferenz = abschluesse.filter((a) => Math.abs(parseFloat(a.differenz)) > 0.005)
  const mankos = mitDifferenz.filter((a) => parseFloat(a.differenz) < -0.005)
  const ueberschuesse = mitDifferenz.filter((a) => parseFloat(a.differenz) > 0.005)

  const differenzQuote = mitDifferenz.length / gesamt
  const zeigeWarnung = differenzQuote > 0.05 && gesamt >= 5

  const durchschnittAbsolut =
    mitDifferenz.length > 0
      ? mitDifferenz.reduce((s, a) => s + Math.abs(parseFloat(a.differenz)), 0) /
        mitDifferenz.length
      : 0

  const maxManko = mankos.length > 0
    ? Math.min(...mankos.map((a) => parseFloat(a.differenz)))
    : null
  const maxUeberschuss = ueberschuesse.length > 0
    ? Math.max(...ueberschuesse.map((a) => parseFloat(a.differenz)))
    : null

  return (
    <div className={`mb-5 rounded-xl border overflow-hidden ${
      zeigeWarnung ? 'border-amber-300 dark:border-amber-700' : 'border-slate-200 dark:border-slate-700'
    }`}>
      {/* Header */}
      <div className={`px-4 py-2.5 flex items-center justify-between ${
        zeigeWarnung ? 'bg-amber-50 dark:bg-amber-950' : 'bg-slate-50 dark:bg-slate-800'
      }`}>
        <span className={`text-xs font-semibold ${
          zeigeWarnung ? 'text-amber-700 dark:text-amber-300' : 'text-slate-600 dark:text-slate-300'
        }`}>
          Differenz-Statistik
        </span>
        <span className={`text-xs ${
          zeigeWarnung ? 'text-amber-600 dark:text-amber-400' : 'text-slate-400 dark:text-slate-500'
        }`}>
          {gesamt} {gesamt === 1 ? 'Abschluss' : 'Abschlüsse'}
        </span>
      </div>

      {/* Kennzahlen-Kacheln */}
      <div className="bg-white dark:bg-slate-800 grid grid-cols-2 sm:grid-cols-4 divide-x divide-y sm:divide-y-0 divide-slate-100 dark:divide-slate-700">
        <div className="px-4 py-3">
          <span className="block text-xs text-slate-400 dark:text-slate-500 mb-0.5">Ausgeglichen</span>
          <span className="text-lg font-bold text-green-600">
            {gesamt - mitDifferenz.length}
          </span>
          <span className="text-xs text-slate-400 dark:text-slate-500 ml-1">
            ({Math.round(((gesamt - mitDifferenz.length) / gesamt) * 100)} %)
          </span>
        </div>

        <div className="px-4 py-3">
          <span className="block text-xs text-slate-400 dark:text-slate-500 mb-0.5">Mit Differenz</span>
          <span className={`text-lg font-bold ${mitDifferenz.length > 0 ? 'text-amber-600' : 'text-slate-700 dark:text-slate-200'}`}>
            {mitDifferenz.length}
          </span>
          <span className="text-xs text-slate-400 dark:text-slate-500 ml-1">
            ({Math.round(differenzQuote * 100)} %)
          </span>
        </div>

        <div className="px-4 py-3">
          <span className="block text-xs text-slate-400 dark:text-slate-500 mb-0.5">Mankos</span>
          <span className={`text-lg font-bold ${mankos.length > 0 ? 'text-red-600' : 'text-slate-400 dark:text-slate-500'}`}>
            {mankos.length}
          </span>
          {maxManko !== null && (
            <span className="block text-xs text-red-400 dark:text-red-500">
              bis {formatEuro(maxManko)}
            </span>
          )}
        </div>

        <div className="px-4 py-3">
          <span className="block text-xs text-slate-400 dark:text-slate-500 mb-0.5">Überschüsse</span>
          <span className={`text-lg font-bold ${ueberschuesse.length > 0 ? 'text-blue-600' : 'text-slate-400 dark:text-slate-500'}`}>
            {ueberschuesse.length}
          </span>
          {maxUeberschuss !== null && (
            <span className="block text-xs text-blue-400 dark:text-blue-500">
              bis {formatEuro(maxUeberschuss)}
            </span>
          )}
        </div>
      </div>

      {/* Ø-Differenz */}
      {mitDifferenz.length > 0 && (
        <div className="bg-white dark:bg-slate-800 border-t border-slate-100 dark:border-slate-700 px-4 py-2 flex items-center gap-2">
          <span className="text-xs text-slate-400 dark:text-slate-500">Ø Differenz (absolut):</span>
          <span className="text-xs font-semibold text-slate-700 dark:text-slate-200">
            {formatEuro(durchschnittAbsolut)}
          </span>
        </div>
      )}

      {/* Warnung >5% */}
      {zeigeWarnung && (
        <div className="border-t border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950 px-4 py-2.5 flex items-start gap-2">
          <span className="text-amber-500 dark:text-amber-400 shrink-0 mt-0.5">⚠</span>
          <p className="text-xs text-amber-800 dark:text-amber-300">
            <span className="font-semibold">Häufige Differenzen: </span>
            Bei {mitDifferenz.length} von {gesamt} Abschlüssen (
            {Math.round(differenzQuote * 100)} %) wurde eine Kassendifferenz festgestellt.
            Ab 5 % empfiehlt sich eine Überprüfung der Kassiergewohnheiten.
          </p>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Hauptseite
// ---------------------------------------------------------------------------

export function TagesabschlussPage() {
  const qc = useQueryClient()
  const [offeneId, setOffeneId] = useState<number | null>(null)
  const [dialogOffen, setDialogOffen] = useState(false)

  // Export-Leiste
  const heute = new Date()
  const aktuellerMonat = `${heute.getFullYear()}-${String(heute.getMonth() + 1).padStart(2, '0')}`
  const [exportZeitraum, setExportZeitraum] = useState<'monat' | 'jahr' | 'alle'>('monat')
  const [exportWert, setExportWert] = useState(aktuellerMonat)

  const { data: abschluesse = [], isLoading } = useQuery({
    queryKey: ['tagesabschluss'],
    queryFn: getTagesabschluesse,
  })

  function toggleDetail(id: number) {
    setOffeneId((prev) => (prev === id ? null : id))
  }

  function handleExport() {
    if (exportZeitraum === 'alle') {
      downloadTagesabschlussPdf({ zeitraum: 'alle' })
    } else {
      downloadTagesabschlussPdf({ zeitraum: exportZeitraum, wert: exportWert })
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
            Tagesabschlüsse
            <InfoTooltip text="Der Tagesabschluss dokumentiert den Kassenstand am Tagesende. Er ist nach §146a AO für jeden Tag vorgeschrieben, an dem Bargeschäfte stattfanden, und nach dem Erstellen unveränderlich. Bei einer Betriebsprüfung dient er als lückenloser Nachweis." side="bottom" />
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            {abschluesse.length > 0
              ? `${abschluesse.length} Abschlüsse gespeichert`
              : 'Noch keine Abschlüsse vorhanden'}
          </p>
        </div>
        <button
          onClick={() => setDialogOffen(true)}
          className="bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          + Heute abschließen
        </button>
      </div>

      {/* Export-Leiste */}
      {abschluesse.length > 0 && (
        <div className="mb-5 flex flex-wrap items-center gap-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 mr-1">PDF-Export:</span>

          <select
            value={exportZeitraum}
            onChange={(e) => setExportZeitraum(e.target.value as 'monat' | 'jahr' | 'alle')}
            className="text-sm border border-slate-300 rounded-lg px-2 py-1.5 bg-white text-slate-700 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
          >
            <option value="monat">Monat</option>
            <option value="jahr">Jahr</option>
            <option value="alle">Alle</option>
          </select>

          {exportZeitraum === 'monat' && (
            <input
              type="month"
              value={exportWert}
              onChange={(e) => setExportWert(e.target.value)}
              className="text-sm border border-slate-300 rounded-lg px-2 py-1.5 bg-white text-slate-700 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
            />
          )}

          {exportZeitraum === 'jahr' && (
            <input
              type="number"
              value={exportWert.length === 4 ? exportWert : String(heute.getFullYear())}
              onChange={(e) => setExportWert(e.target.value)}
              min="2000"
              max="2099"
              className="text-sm border border-slate-300 rounded-lg px-2 py-1.5 bg-white text-slate-700 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100 w-24"
            />
          )}

          <button
            onClick={handleExport}
            className="text-sm font-medium px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors flex items-center gap-1.5"
          >
            <span>↓</span> PDF herunterladen
          </button>
        </div>
      )}

      {/* Differenz-Statistik */}
      {!isLoading && <DifferenzStatistik abschluesse={abschluesse} />}

      {/* Liste */}
      {isLoading ? (
        <p className="text-slate-400 text-sm">Lade…</p>
      ) : abschluesse.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <p className="text-4xl mb-3">📋</p>
          <p className="text-sm">Noch kein Tagesabschluss durchgeführt.</p>
        </div>
      ) : (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden divide-y divide-slate-100 dark:divide-slate-700">
          {abschluesse.map((a) => {
            const differenz = parseFloat(a.differenz)
            const hatDifferenz = Math.abs(differenz) > 0.005
            const istOffen = offeneId === a.id

            return (
              <div key={a.id}>
                {/* Zeilen-Header */}
                <button
                  onClick={() => toggleDetail(a.id)}
                  className="w-full text-left px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    {/* Datum + Uhrzeit */}
                    <div className="w-28 shrink-0">
                      <span className="font-semibold text-slate-800 dark:text-slate-100 text-sm">
                        {formatDatum(a.datum)}
                      </span>
                      <span className="block text-xs text-slate-400 dark:text-slate-500">
                        {formatUhrzeit(a.uhrzeit)}
                      </span>
                    </div>

                    {/* Beträge */}
                    <div className="flex-1 grid grid-cols-3 gap-2 text-sm">
                      <div>
                        <span className="block text-xs text-slate-400 dark:text-slate-500">Soll</span>
                        <span className="dark:text-slate-200">{formatEuro(a.soll_endbestand)}</span>
                      </div>
                      <div>
                        <span className="block text-xs text-slate-400 dark:text-slate-500">Ist</span>
                        <span className="font-medium dark:text-slate-200">{formatEuro(a.ist_endbestand)}</span>
                      </div>
                      <div>
                        <span className="block text-xs text-slate-400 dark:text-slate-500">Differenz</span>
                        <span className={hatDifferenz ? 'text-amber-600 font-medium' : 'text-green-600'}>
                          {hatDifferenz ? formatEuro(differenz) : '✓ 0,00 €'}
                        </span>
                      </div>
                    </div>

                    {/* Buchungen + Pfeil */}
                    <div className="shrink-0 flex items-center gap-3">
                      <span className="text-xs text-slate-400 dark:text-slate-500">
                        {a.kassenbewegungen_anzahl} Buchungen
                      </span>
                      {a.signatur ? (
                        <span className="text-xs text-slate-300 dark:text-slate-600" title="Signiert">🔒</span>
                      ) : (
                        <span className="text-xs text-amber-400 dark:text-amber-500" title="Keine Signatur">⚠</span>
                      )}
                      <span className="text-slate-400 dark:text-slate-500 text-xs">{istOffen ? '▲' : '▼'}</span>
                    </div>
                  </div>
                </button>

                {/* Detail */}
                {istOffen && <AbschlussDetail a={a} />}
              </div>
            )
          })}
        </div>
      )}

      {/* Dialog */}
      {dialogOffen && (
        <TagesabschlussDialog
          onClose={() => setDialogOffen(false)}
          onSuccess={() => {
            setDialogOffen(false)
            qc.invalidateQueries({ queryKey: ['tagesabschluss'] })
            qc.invalidateQueries({ queryKey: ['tagesabschluss-fehlt-gestern'] })
          }}
        />
      )}
    </div>
  )
}
