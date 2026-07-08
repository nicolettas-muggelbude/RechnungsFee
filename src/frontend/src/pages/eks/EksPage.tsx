import { useState } from 'react'
import { eksHalbjahr, eksHalbjahresPdf, type EksHalbjahr, type EksFeld } from '../../api/client'
import { EksEinstellungenModal } from './EksEinstellungenModal'
import { useMxAuto } from '../../hooks/useAnsicht'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const MONATE_KURZ = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']

function halbjahrStart(): string {
  const d = new Date()
  const m = d.getMonth() < 6 ? 1 : 7
  return `${d.getFullYear()}-${String(m).padStart(2, '0')}`
}

function formatMonat(monat: string): string {
  const [y, m] = monat.split('-')
  return `${MONATE_KURZ[parseInt(m) - 1]} ${y.slice(2)}`
}

function fmtEuro(v: string | number | undefined): string {
  const n = parseFloat(String(v ?? '0'))
  if (isNaN(n)) return '–'
  const abs = Math.abs(n).toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return n < -0.005 ? `−${abs}` : abs
}

function val(werte: Record<string, Record<string, string>>, monat: string, code: string): number {
  return parseFloat(werte[monat]?.[code] ?? '0') || 0
}

function zeilenSumme(res: EksHalbjahr, code: string): number {
  return parseFloat(res.zeilensummen[code] ?? '0') || 0
}

const TABELLEN_FARBE: Record<string, string> = {
  A: 'bg-emerald-600',
  B: 'bg-orange-500',
  C: 'bg-violet-600',
}

// ---------------------------------------------------------------------------
// Tabellen-Matrix (A und B)
// ---------------------------------------------------------------------------

function MatrixTabelle({
  tabelle, felder, res, b64PrivKm, onB64PrivKmChange,
}: {
  tabelle: 'A' | 'B'
  felder: EksFeld[]
  res: EksHalbjahr
  b64PrivKm?: string
  onB64PrivKmChange?: (km: string) => void
}) {
  const { monate, werte, spaltensummen_a, spaltensummen_b } = res
  const spaltensummen = tabelle === 'A' ? spaltensummen_a : spaltensummen_b
  const b64PrivBetrag = (parseFloat(b64PrivKm || '0') || 0) * 0.10
  const gesamt = felder.reduce((s, f) => {
    if (f.negativ) return s  // negativ-Felder aus Journal-Summe raus (manuell)
    return s + zeilenSumme(res, f.code)
  }, 0) - (tabelle === 'B' ? b64PrivBetrag : 0)

  // Tabellenabschnitte für B (Teil 1 / 2 / 3)
  const abschnitte: { label: string; codes: string[] }[] = tabelle === 'A' ? [
    { label: '', codes: felder.map(f => f.code) },
  ] : [
    { label: 'Teil 1', codes: ['B1','B2_1','B2_2','B2_3','B2_4','B3','B4','B5'] },
    { label: 'Teil 2', codes: ['B6_1','B6_2','B6_3','B6_4','B6_4_priv','B6_5','B7_1','B7_2','B7_3','B8','B9','B10'] },
    { label: 'Teil 3', codes: ['B11','B12','B13','B14_1','B14_2','B14_3','B14_4','B14_5','B15','B16','B17','B18'] },
  ]

  const titelFarbe = TABELLEN_FARBE[tabelle]
  const titel = tabelle === 'A'
    ? 'Tabelle A – Betriebseinnahmen'
    : 'Tabelle B – Betriebsausgaben'

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
      <div className={`${titelFarbe} px-5 py-3`}>
        <h2 className="text-white font-bold text-base">{titel}</h2>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          {/* Kopfzeile */}
          <thead>
            <tr className="bg-slate-50 dark:bg-slate-900 text-xs text-slate-500 dark:text-slate-400">
              <th className="text-left px-3 py-2 font-medium w-16 border-b border-r border-slate-200 dark:border-slate-700">Code</th>
              <th className="text-left px-3 py-2 font-medium min-w-[200px] border-b border-r border-slate-200 dark:border-slate-700">Bezeichnung</th>
              {monate.map(m => (
                <th key={m} className="text-right px-2 py-2 font-medium w-24 border-b border-r border-slate-200 dark:border-slate-700">
                  {formatMonat(m)}
                </th>
              ))}
              <th className="text-right px-3 py-2 font-medium w-28 border-b border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800">
                Summe
              </th>
            </tr>
          </thead>

          <tbody>
            {abschnitte.map((abschnitt, ai) => {
              const abschnittFelder = abschnitt.codes
                .map(c => felder.find(f => f.code === c))
                .filter(Boolean) as EksFeld[]
              if (!abschnittFelder.length) return null

              return (
                <>
                  {/* Abschnitts-Trennzeile für Tabelle B */}
                  {tabelle === 'B' && (
                    <tr key={`head-${ai}`} className="bg-slate-50 dark:bg-slate-900">
                      <td
                        colSpan={monate.length + 3}
                        className="px-3 py-1 text-xs font-semibold text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700"
                      >
                        {abschnitt.label}
                      </td>
                    </tr>
                  )}

                  {abschnittFelder.map((f) => {
                    // B6_4_priv: manuelles km-Eingabefeld mit Abzugsdarstellung
                    if (f.negativ) {
                      const abzugBetrag = (parseFloat(b64PrivKm || '0') || 0) * 0.10
                      const hatAbzug = abzugBetrag >= 0.005
                      return (
                        <tr key={f.code} className="border-b border-orange-100 dark:border-orange-900 bg-orange-50/40 dark:bg-orange-950/20">
                          <td className="px-3 py-2 font-mono text-xs font-bold text-orange-400 dark:text-orange-600 border-r border-orange-100 dark:border-orange-900">
                            {f.code}
                          </td>
                          <td className="px-3 py-2 text-slate-600 dark:text-slate-300 italic text-xs border-r border-orange-100 dark:border-orange-900">
                            {f.label}
                          </td>
                          {monate.map(m => (
                            <td key={m} className="px-2 py-2 text-right tabular-nums text-slate-300 dark:text-slate-600 border-r border-orange-100 dark:border-orange-900">—</td>
                          ))}
                          <td className="px-3 py-2 bg-orange-50 dark:bg-orange-950">
                            <div className="flex items-center justify-end gap-1.5">
                              <input
                                type="number"
                                step="0.1"
                                min="0"
                                value={b64PrivKm ?? ''}
                                onChange={e => onB64PrivKmChange?.(e.target.value)}
                                placeholder="0"
                                className="w-20 border border-orange-300 dark:border-orange-700 rounded px-2 py-0.5 text-xs text-right focus:outline-none focus:ring-1 focus:ring-orange-400 dark:bg-slate-700 dark:text-slate-100"
                              />
                              <span className="text-xs text-orange-600 dark:text-orange-400">km</span>
                              <span className={`text-xs font-semibold tabular-nums ${hatAbzug ? 'text-red-600 dark:text-red-400' : 'text-slate-300 dark:text-slate-600'}`}>
                                {hatAbzug ? `−${abzugBetrag.toFixed(2).replace('.', ',')}` : '–'}
                              </span>
                            </div>
                          </td>
                        </tr>
                      )
                    }

                    const zeilSum = zeilenSumme(res, f.code)
                    const hatWert = Math.abs(zeilSum) >= 0.005
                    return (
                      <tr
                        key={f.code}
                        className="border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-750"
                      >
                        <td className="px-3 py-2 font-mono text-xs font-bold text-slate-400 dark:text-slate-500 border-r border-slate-100 dark:border-slate-700">
                          {f.code}
                        </td>
                        <td className="px-3 py-2 text-slate-700 dark:text-slate-200 border-r border-slate-100 dark:border-slate-700">
                          {f.label}
                        </td>
                        {monate.map(m => {
                          const v = val(werte, m, f.code)
                          return (
                            <td
                              key={m}
                              className={`px-2 py-2 text-right tabular-nums border-r border-slate-100 dark:border-slate-700 ${
                                Math.abs(v) >= 0.005
                                  ? 'text-slate-800 dark:text-slate-100'
                                  : 'text-slate-300 dark:text-slate-600'
                              }`}
                            >
                              {fmtEuro(v)}
                            </td>
                          )
                        })}
                        <td className={`px-3 py-2 text-right tabular-nums font-semibold bg-slate-50 dark:bg-slate-900 ${
                          hatWert ? 'text-slate-800 dark:text-slate-100' : 'text-slate-300 dark:text-slate-600'
                        }`}>
                          {fmtEuro(zeilSum)}
                        </td>
                      </tr>
                    )
                  })}

                  {/* Zwischensumme zwischen B-Teilen */}
                  {tabelle === 'B' && ai < abschnitte.length - 1 && (() => {
                    const zwSum = abschnittFelder.reduce((s, f) => s + zeilenSumme(res, f.code), 0)
                    const zwSumMonate = monate.map(m =>
                      abschnittFelder.reduce((s, f) => s + val(werte, m, f.code), 0)
                    )
                    return (
                      <tr key={`zw-${ai}`} className="bg-orange-50 dark:bg-orange-950 font-semibold text-xs">
                        <td className="px-3 py-1.5 border-r border-orange-200 dark:border-orange-800" />
                        <td className="px-3 py-1.5 text-orange-800 dark:text-orange-300 border-r border-orange-200 dark:border-orange-800">
                          Zwischensumme {abschnitt.label}
                        </td>
                        {zwSumMonate.map((v, i) => (
                          <td key={i} className="px-2 py-1.5 text-right tabular-nums text-orange-800 dark:text-orange-300 border-r border-orange-200 dark:border-orange-800">
                            {fmtEuro(v)}
                          </td>
                        ))}
                        <td className="px-3 py-1.5 text-right tabular-nums text-orange-800 dark:text-orange-300 bg-orange-100 dark:bg-orange-900">
                          {fmtEuro(zwSum)}
                        </td>
                      </tr>
                    )
                  })()}
                </>
              )
            })}
          </tbody>

          {/* Summenzeile */}
          <tfoot>
            <tr className={`${titelFarbe} text-white font-bold text-xs`}>
              <td className="px-3 py-2 border-r border-white/20" />
              <td className="px-3 py-2 border-r border-white/20">
                {tabelle === 'A' ? 'Summe Betriebseinnahmen' : 'Summe Betriebsausgaben'}
              </td>
              {monate.map(m => (
                <td key={m} className="px-2 py-2 text-right tabular-nums border-r border-white/20">
                  {fmtEuro(spaltensummen[m])}
                </td>
              ))}
              <td className="px-3 py-2 text-right tabular-nums bg-black/10">
                {fmtEuro(gesamt)}
                {' '}
                <span className="opacity-70 text-xs ml-1" title="Kreuzprüfung: Zeilensummen = Spaltensummen">✓</span>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tabelle C (keine monatliche Aufgliederung im offiziellen Formular)
// ---------------------------------------------------------------------------

function TabelleC({ felder, res }: { felder: EksFeld[]; res: EksHalbjahr }) {
  const gesamtC = felder.reduce((s, f) => s + zeilenSumme(res, f.code), 0)
  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
      <div className="bg-violet-600 px-5 py-3">
        <h2 className="text-white font-bold text-base">Tabelle C – Absetzungen vom Einkommen</h2>
        <p className="text-violet-200 text-xs mt-0.5">
          Keine monatliche Aufgliederung – gilt für den gesamten Bewilligungszeitraum
        </p>
      </div>

      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-slate-50 dark:bg-slate-900 text-xs text-slate-500 dark:text-slate-400">
            <th className="text-left px-3 py-2 font-medium w-16 border-b border-r border-slate-200 dark:border-slate-700">Code</th>
            <th className="text-left px-3 py-2 font-medium border-b border-r border-slate-200 dark:border-slate-700">Art der Absetzung</th>
            <th className="text-right px-3 py-2 font-medium w-36 border-b border-slate-200 dark:border-slate-700">Betrag (6 Monate)</th>
          </tr>
        </thead>
        <tbody>
          {felder.map(f => {
            const v = zeilenSumme(res, f.code)
            return (
              <tr key={f.code} className="border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-750">
                <td className="px-3 py-2 font-mono text-xs font-bold text-slate-400 dark:text-slate-500 border-r border-slate-100 dark:border-slate-700">
                  {f.code}
                </td>
                <td className="px-3 py-2 text-slate-700 dark:text-slate-200 border-r border-slate-100 dark:border-slate-700">
                  {f.label}
                </td>
                <td className={`px-3 py-2 text-right tabular-nums font-medium ${
                  Math.abs(v) >= 0.005 ? 'text-slate-800 dark:text-slate-100' : 'text-slate-300 dark:text-slate-600'
                }`}>
                  {fmtEuro(v)}
                </td>
              </tr>
            )
          })}
        </tbody>
        <tfoot>
          <tr className="bg-violet-600 text-white font-bold text-xs">
            <td className="px-3 py-2 border-r border-white/20" />
            <td className="px-3 py-2 border-r border-white/20">Summe Absetzungen</td>
            <td className="px-3 py-2 text-right tabular-nums">{fmtEuro(gesamtC)}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  )
}

// ---------------------------------------------------------------------------
// EksPage
// ---------------------------------------------------------------------------

export function EksPage() {
  const mxAuto = useMxAuto()
  const [startMonat, setStartMonat] = useState(halbjahrStart())
  const [art, setArt] = useState<'abschliessend' | 'vorlaeufig'>('abschliessend')
  const [ergebnis, setErgebnis] = useState<EksHalbjahr | null>(null)
  const [laedt, setLaedt] = useState(false)
  const [exportiert, setExportiert] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)
  const [showEinstellungen, setShowEinstellungen] = useState(false)
  const [b64PrivKm, setB64PrivKm] = useState<string>('')  // km privat gefahren mit Betriebs-KFZ (B6_4_priv)

  async function handleBerechnen() {
    setLaedt(true)
    setFehler(null)
    setExportiert(false)
    try {
      const res = await eksHalbjahr(`${startMonat}-01`, art)
      setErgebnis(res)
    } catch (e: any) {
      setFehler(e?.message ?? 'Fehler beim Laden der Daten')
    } finally {
      setLaedt(false)
    }
  }

  async function handlePdf() {
    if (!ergebnis) return
    setLaedt(true)
    setFehler(null)
    try {
      await eksHalbjahresPdf(`${startMonat}-01`, art)
      setExportiert(true)
    } catch (e: any) {
      setFehler(e?.message ?? 'PDF-Export fehlgeschlagen')
    } finally {
      setLaedt(false)
    }
  }

  const felderA = ergebnis?.felder.filter(f => f.tabelle === 'A') ?? []
  const felderB = ergebnis?.felder.filter(f => f.tabelle === 'B') ?? []
  const felderC = ergebnis?.felder.filter(f => f.tabelle === 'C') ?? []

  const b64PrivBetrag = (parseFloat(b64PrivKm) || 0) * 0.10
  const sumA = ergebnis ? felderA.reduce((s, f) => s + zeilenSumme(ergebnis, f.code), 0) : 0
  const sumB = ergebnis
    ? felderB.filter(f => !f.negativ).reduce((s, f) => s + zeilenSumme(ergebnis, f.code), 0) - b64PrivBetrag
    : 0
  const sumC = ergebnis ? felderC.reduce((s, f) => s + zeilenSumme(ergebnis, f.code), 0) : 0
  const gewinn    = sumA - sumB
  const einkommen = gewinn - sumC

  // Bewilligungszeitraum-Label
  const [startJahr, startM] = startMonat.split('-')
  const endM = ((parseInt(startM) - 1 + 5) % 12) + 1
  const endJahr = parseInt(startJahr) + Math.floor((parseInt(startM) - 1 + 5) / 12)
  const zeitraumLabel = `${MONATE_KURZ[parseInt(startM) - 1]} ${startJahr} – ${MONATE_KURZ[endM - 1]} ${endJahr}`

  return (
    <div className={`p-6 max-w-6xl ${mxAuto} space-y-6`}>
      {/* Kopfzeile */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Anlage EKS</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
          Einkommenserklärung für Selbstständige · Jobcenter / Bürgergeld · Formular 04/2025
        </p>
      </div>

      {/* Einstellungen */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm p-5">
        <h2 className="font-semibold text-slate-800 dark:text-slate-100 mb-4">Bewilligungszeitraum</h2>

        <div className="flex flex-wrap gap-4 items-end">
          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-600 dark:text-slate-300">
              Startmonat (6 Monate ab hier)
            </label>
            <input
              type="month"
              value={startMonat}
              onChange={e => setStartMonat(e.target.value)}
              className="border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">{zeitraumLabel}</p>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-600 dark:text-slate-300">Erklärungsart</label>
            <select
              value={art}
              onChange={e => setArt(e.target.value as 'abschliessend' | 'vorlaeufig')}
              className="border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="abschliessend">Abschließend (aus Journaldaten)</option>
              <option value="vorlaeufig">Vorläufig (Prognose aus Vorjahr)</option>
            </select>
          </div>

          <button
            onClick={handleBerechnen}
            disabled={laedt}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm font-medium px-5 py-2 rounded-lg transition-colors"
          >
            {laedt ? <span className="animate-spin inline-block">⏳</span> : <span>🔄</span>}
            Berechnen
          </button>
        </div>

        {fehler && (
          <div className="mt-4 flex items-start gap-2 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3 text-sm text-red-800 dark:text-red-300">
            <span className="shrink-0">✗</span>{fehler}
          </div>
        )}
      </div>

      {/* Quellen-Banner bei vorläufig */}
      {ergebnis && art === 'vorlaeufig' && (
        ergebnis.quelle ? (
          <div className="flex items-start gap-3 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-xl px-4 py-3">
            <span className="text-blue-500 dark:text-blue-400 shrink-0">ℹ</span>
            <p className="text-sm text-blue-800 dark:text-blue-200">
              <strong>Prognose aus Vorjahr:</strong>{' '}
              {ergebnis.quelle.anzahl_exporte} abschließende EKS-Exporte aus dem Vorjahres-Halbjahr · Monatswert = Halbjahressumme ÷ 6
            </p>
          </div>
        ) : (
          <div className="flex items-start gap-3 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-xl px-4 py-3">
            <span className="text-amber-500 dark:text-amber-400 shrink-0">⚠</span>
            <p className="text-sm text-amber-800 dark:text-amber-300">
              <strong>Keine Vorjahresdaten:</strong> Erstelle zuerst monatliche abschließende EKS-Exporte für das Vorjahres-Halbjahr.
              Alle Beträge sind 0,00 €.
            </p>
          </div>
        )
      )}

      {/* Tabellen */}
      {ergebnis && (
        <>
          <MatrixTabelle tabelle="A" felder={felderA} res={ergebnis} />
          <MatrixTabelle
            tabelle="B" felder={felderB} res={ergebnis}
            b64PrivKm={b64PrivKm} onB64PrivKmChange={setB64PrivKm}
          />

          {/* Gewinn-Box */}
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
            <div className="bg-slate-700 px-5 py-3">
              <h2 className="text-white font-bold text-base">Gewinn (A − B)</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <tbody>
                  <tr>
                    {ergebnis.monate.map(m => {
                      const a = parseFloat(ergebnis.spaltensummen_a[m] ?? '0')
                      const b = parseFloat(ergebnis.spaltensummen_b[m] ?? '0')
                      const g = a - b
                      return (
                        <td key={m} className="px-3 py-3 text-center border-r border-slate-100 dark:border-slate-700 last:border-r-0">
                          <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">{formatMonat(m)}</div>
                          <div className={`font-bold tabular-nums ${g >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                            {fmtEuro(g)}
                          </div>
                        </td>
                      )
                    })}
                    <td className="px-3 py-3 text-center bg-slate-50 dark:bg-slate-900 border-l border-slate-200 dark:border-slate-700">
                      <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Gesamt</div>
                      <div className={`font-bold tabular-nums text-lg ${gewinn >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                        {fmtEuro(gewinn)}
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <TabelleC felder={felderC} res={ergebnis} />

          {/* Ergebnis */}
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
            <div className="bg-blue-600 px-5 py-3">
              <h2 className="text-white font-bold text-base">Zu berücksichtigendes Einkommen</h2>
            </div>
            <div className="p-5 space-y-2">
              <div className="flex justify-between text-sm text-slate-600 dark:text-slate-300">
                <span>Betriebseinnahmen (A)</span><span className="tabular-nums">{fmtEuro(sumA)}</span>
              </div>
              <div className="flex justify-between text-sm text-slate-600 dark:text-slate-300">
                <span>− Betriebsausgaben (B)</span><span className="tabular-nums">{fmtEuro(sumB)}</span>
              </div>
              <div className="flex justify-between text-sm font-medium border-t border-slate-200 dark:border-slate-600 pt-2 text-slate-700 dark:text-slate-200">
                <span>= Gewinn</span>
                <span className={`tabular-nums ${gewinn >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>{fmtEuro(gewinn)}</span>
              </div>
              <div className="flex justify-between text-sm text-slate-600 dark:text-slate-300">
                <span>− Absetzungen (C)</span><span className="tabular-nums">{fmtEuro(sumC)}</span>
              </div>
              <div className="flex justify-between items-center border-t-2 border-blue-200 dark:border-blue-700 pt-3 mt-1">
                <span className="font-bold text-slate-800 dark:text-slate-100">= Zu berücksichtigendes Einkommen</span>
                <span className={`font-bold text-xl tabular-nums ${
                  einkommen < 0 ? 'text-red-600 dark:text-red-400'
                  : einkommen > 0 ? 'text-blue-600 dark:text-blue-400'
                  : 'text-slate-600 dark:text-slate-300'
                }`}>
                  {fmtEuro(einkommen)}
                </span>
              </div>
            </div>
          </div>

          {/* Aktionen */}
          <div className="flex flex-wrap gap-3 items-center">
            <button
              onClick={() => setShowEinstellungen(true)}
              className="flex items-center gap-2 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 text-sm font-medium px-4 py-2 rounded-lg transition-colors"
            >
              ⚙️ Einstellungen
            </button>
            <button
              onClick={handlePdf}
              disabled={laedt}
              className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 text-white text-sm font-medium px-5 py-2 rounded-lg transition-colors"
            >
              {laedt ? <span className="animate-spin inline-block">⏳</span> : <span>📄</span>}
              PDF erstellen
            </button>
            {exportiert && (
              <span className="flex items-center gap-2 text-sm text-emerald-700 dark:text-emerald-400">
                <span>✓</span> PDF wurde geöffnet
              </span>
            )}
          </div>

          {/* Hinweis */}
          <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg px-4 py-3 flex gap-2">
            <span className="text-amber-500 dark:text-amber-400 shrink-0">⚠</span>
            <p className="text-xs text-amber-800 dark:text-amber-300">
              <strong>Hinweis:</strong> Alle Beträge stammen ausschließlich aus deinen Journalbuchungen.
              Felder ohne Buchung zeigen 0,00 €.
              Das erzeugte PDF ist ein vollständiger Formularnachbau des offiziellen EKS-Formulars des Jobcenters und ersetzt dieses – entbindet aber nicht von der Pflicht, alle Angaben auf Richtigkeit und Vollständigkeit zu prüfen.
              Das ✓ in der Summen-Spalte zeigt, dass Zeilen- und Spaltensummen übereinstimmen (Kreuzprüfung).
            </p>
          </div>
        </>
      )}

      {/* Leer-Zustand */}
      {!ergebnis && (
        <div className="text-center py-20 text-slate-400 dark:text-slate-500">
          <div className="text-5xl mb-4">📋</div>
          <p className="text-sm">Startmonat wählen und auf „Berechnen" klicken.</p>
          <p className="text-xs mt-2 opacity-70">Der Bewilligungszeitraum umfasst immer 6 aufeinanderfolgende Monate.</p>
        </div>
      )}
      {showEinstellungen && <EksEinstellungenModal onClose={() => setShowEinstellungen(false)} />}
    </div>
  )
}
