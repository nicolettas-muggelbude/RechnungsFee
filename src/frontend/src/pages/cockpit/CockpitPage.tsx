import { useState, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip as RechartsTip,
  Legend, ResponsiveContainer,
} from 'recharts'
import { getCockpit, type CockpitDaten } from '../../api/client'
import { useMxAuto } from '../../hooks/useAnsicht'

// ── Hilfsfunktionen ────────────────────────────────────────────────────────────

const eur = (v: number) =>
  new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(v)

const pct = (v: number) =>
  new Intl.NumberFormat('de-DE', { style: 'decimal', maximumFractionDigits: 1 }).format(v) + ' %'

const DONUT_FARBEN = [
  '#6366f1','#8b5cf6','#ec4899','#f59e0b','#10b981','#3b82f6',
  '#14b8a6','#f97316','#84cc16','#06b6d4','#a855f7','#ef4444',
]

// ── Info-Tooltip ───────────────────────────────────────────────────────────────

function InfoTooltip({ text, direction = 'down' }: { text: string; direction?: 'up' | 'down' }) {
  const box = direction === 'down'
    ? 'top-full left-1/2 -translate-x-1/2 mt-2'
    : 'bottom-full left-1/2 -translate-x-1/2 mb-2'
  const arrow = direction === 'down'
    ? 'absolute bottom-full left-1/2 -translate-x-1/2 border-4 border-transparent border-b-slate-800 dark:border-b-slate-700'
    : 'absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800 dark:border-t-slate-700'
  return (
    <span className="group relative inline-flex items-center ml-1 cursor-help">
      <span className="material-symbols-outlined text-base text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 select-none">
        info
      </span>
      <span className={`
        pointer-events-none absolute ${box} z-50
        w-64 rounded-lg bg-slate-800 dark:bg-slate-700 text-white text-xs px-3 py-2 shadow-xl
        opacity-0 group-hover:opacity-100 transition-opacity duration-150
      `}>
        {text}
        <span className={arrow} />
      </span>
    </span>
  )
}

// ── KPI-Kachel ─────────────────────────────────────────────────────────────────

function KpiCard({
  label, wert, farbe, tooltip, prefix = '',
}: {
  label: string
  wert: string
  farbe: string
  tooltip: string
  prefix?: string
}) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
      <div className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 mb-2">
        {label}
        <InfoTooltip text={tooltip} />
      </div>
      <div className={`text-2xl font-bold tabular-nums ${farbe}`}>
        {prefix}{wert}
      </div>
    </div>
  )
}

// ── Recharts Custom-Tooltip ────────────────────────────────────────────────────

function EurTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg shadow-xl p-3 text-sm">
      <p className="font-semibold text-slate-700 dark:text-slate-200 mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }} className="tabular-nums">
          {p.name}: {eur(p.value)} (netto)
        </p>
      ))}
    </div>
  )
}

// ── Zeitraum-Wahl ──────────────────────────────────────────────────────────────

type Zeitraum = 'monat' | 'quartal' | 'jahr'

function useZeitraum() {
  const jetzt = new Date()
  const aktJahr = jetzt.getFullYear()
  const aktMonat = jetzt.getMonth() + 1

  const [art, setArt] = useState<Zeitraum>('monat')
  const [jahr, setJahr] = useState(aktJahr)
  const [monat, setMonat] = useState(aktMonat)
  const [quartal, setQuartal] = useState(Math.ceil(aktMonat / 3))

  const wert =
    art === 'monat'   ? `${jahr}-${String(monat).padStart(2, '0')}` :
    art === 'quartal' ? `${jahr}-Q${quartal}` :
    String(jahr)

  const jahre = Array.from({ length: 6 }, (_, i) => aktJahr - i)

  return { art, setArt, jahr, setJahr, monat, setMonat, quartal, setQuartal, wert, jahre }
}

const MONATE_DE = ['Jan','Feb','Mär','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez']

// ── Hauptseite ─────────────────────────────────────────────────────────────────

export function CockpitPage() {
  const mxAuto = useMxAuto()
  const zr = useZeitraum()

  const { data, isLoading, error } = useQuery<CockpitDaten>({
    queryKey: ['cockpit', zr.art, zr.wert],
    queryFn: () => getCockpit(zr.art, zr.wert),
    staleTime: 60_000,
  })

  return (
    <div className={`p-6 max-w-6xl ${mxAuto}`}>

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
            Unternehmer-Cockpit
          </h1>
          <div className="flex items-center gap-1 text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Alle Beträge netto (ohne Umsatzsteuer)
            <InfoTooltip text="Netto bedeutet: ohne Umsatzsteuer. Die USt, die du auf Rechnungen ausweist, gehört dem Finanzamt – sie ist kein Gewinn. Hier siehst du deinen tatsächlichen Umsatz und Gewinn." />
          </div>
        </div>

        {/* Zeitraum-Wahl */}
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={zr.art}
            onChange={e => zr.setArt(e.target.value as Zeitraum)}
            className="text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-1.5 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200"
          >
            <option value="monat">Monat</option>
            <option value="quartal">Quartal</option>
            <option value="jahr">Jahr</option>
          </select>

          {zr.art === 'monat' && (
            <select
              value={zr.monat}
              onChange={e => zr.setMonat(Number(e.target.value))}
              className="text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-1.5 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200"
            >
              {MONATE_DE.map((m, i) => (
                <option key={i + 1} value={i + 1}>{m}</option>
              ))}
            </select>
          )}

          {zr.art === 'quartal' && (
            <select
              value={zr.quartal}
              onChange={e => zr.setQuartal(Number(e.target.value))}
              className="text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-1.5 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200"
            >
              <option value={1}>Q1 (Jan–Mär)</option>
              <option value={2}>Q2 (Apr–Jun)</option>
              <option value={3}>Q3 (Jul–Sep)</option>
              <option value={4}>Q4 (Okt–Dez)</option>
            </select>
          )}

          <select
            value={zr.jahr}
            onChange={e => zr.setJahr(Number(e.target.value))}
            className="text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-1.5 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200"
          >
            {zr.jahre.map(j => <option key={j} value={j}>{j}</option>)}
          </select>
        </div>
      </div>

      {isLoading && (
        <div className="text-center text-slate-400 py-16">Lade Auswertung…</div>
      )}
      {error && (
        <div className="text-center text-red-500 py-16">Fehler beim Laden der Daten</div>
      )}

      {data && (
        <div className="space-y-6">

          {/* KPI-Kacheln */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard
              label="Einnahmen"
              wert={eur(data.kpis.einnahmen)}
              farbe="text-emerald-600 dark:text-emerald-400"
              tooltip="Summe aller Zahlungseingänge ohne Umsatzsteuer im gewählten Zeitraum."
            />
            <KpiCard
              label="Ausgaben"
              wert={eur(data.kpis.ausgaben)}
              farbe="text-red-500 dark:text-red-400"
              tooltip="Summe aller Betriebsausgaben ohne abzugsfähige Vorsteuer im gewählten Zeitraum."
            />
            <KpiCard
              label="Gewinn"
              wert={eur(data.kpis.gewinn)}
              farbe={data.kpis.gewinn >= 0 ? 'text-blue-600 dark:text-blue-400' : 'text-red-600 dark:text-red-400'}
              tooltip="Einnahmen minus Ausgaben (netto). Entspricht dem Überschuss in deiner EÜR für den gewählten Zeitraum."
            />
            <KpiCard
              label="Gewinnmarge"
              wert={pct(data.kpis.gewinn_marge_prozent)}
              farbe={data.kpis.gewinn_marge_prozent >= 0 ? 'text-violet-600 dark:text-violet-400' : 'text-red-600 dark:text-red-400'}
              tooltip="Anteil des Gewinns an den Einnahmen in Prozent. Je höher, desto effizienter wirtschaftest du."
            />
          </div>

          {/* Monatsbalken – Jahresverlauf */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
            <h2 className="text-sm font-semibold text-slate-600 dark:text-slate-300 mb-4">
              Einnahmen & Ausgaben – Jahresverlauf {zr.jahr}
            </h2>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={data.monatsbalken} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="monat"
                  tick={{ fontSize: 12, fill: '#94a3b8' }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tickFormatter={v => v === 0 ? '0' : `${(v / 1000).toFixed(0)}k`}
                  tick={{ fontSize: 11, fill: '#94a3b8' }}
                  axisLine={false}
                  tickLine={false}
                  width={40}
                />
                <RechartsTip content={<EurTooltip />} />
                <Legend
                  formatter={(v) => <span className="text-xs text-slate-600 dark:text-slate-300">{v}</span>}
                />
                <Bar dataKey="einnahmen" name="Einnahmen" fill="#10b981" radius={[3,3,0,0]}>
                  {data.monatsbalken.map((entry, i) => (
                    <Cell
                      key={i}
                      fill={entry.in_periode ? '#10b981' : '#d1fae5'}
                    />
                  ))}
                </Bar>
                <Bar dataKey="ausgaben" name="Ausgaben" fill="#f87171" radius={[3,3,0,0]}>
                  {data.monatsbalken.map((entry, i) => (
                    <Cell
                      key={i}
                      fill={entry.in_periode ? '#f87171' : '#fee2e2'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Gewinnverlauf + Donut */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

            {/* Gewinnverlauf */}
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
              <h2 className="text-sm font-semibold text-slate-600 dark:text-slate-300 mb-4">
                Gewinnverlauf {zr.jahr}
              </h2>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={data.monatsbalken} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="monat"
                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tickFormatter={v => v === 0 ? '0' : `${(v / 1000).toFixed(0)}k`}
                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                    axisLine={false}
                    tickLine={false}
                    width={40}
                  />
                  <RechartsTip content={<EurTooltip />} />
                  <Line
                    type="monotone"
                    dataKey="gewinn"
                    name="Gewinn"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={{ r: 3, fill: '#3b82f6' }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Ausgaben nach Kategorie */}
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
              <h2 className="text-sm font-semibold text-slate-600 dark:text-slate-300 mb-4">
                Ausgaben nach Kategorie
              </h2>
              {data.ausgaben_kategorien.length === 0 ? (
                <div className="flex items-center justify-center h-48 text-sm text-slate-400">
                  Keine Ausgaben im gewählten Zeitraum
                </div>
              ) : (
                <div className="flex items-center gap-4">
                  <ResponsiveContainer width={160} height={160}>
                    <PieChart>
                      <Pie
                        data={data.ausgaben_kategorien}
                        dataKey="betrag"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={45}
                        outerRadius={72}
                        strokeWidth={0}
                      >
                        {data.ausgaben_kategorien.map((_, i) => (
                          <Cell key={i} fill={DONUT_FARBEN[i % DONUT_FARBEN.length]} />
                        ))}
                      </Pie>
                      <RechartsTip
                        formatter={((v: number, name: string) => [eur(v) + ' (netto)', name]) as any}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="flex-1 space-y-1.5 overflow-hidden">
                    {data.ausgaben_kategorien.slice(0, 8).map((k, i) => (
                      <div key={k.name} className="flex items-center gap-2 text-xs">
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ background: DONUT_FARBEN[i % DONUT_FARBEN.length] }}
                        />
                        <span className="text-slate-600 dark:text-slate-300 truncate flex-1">{k.name}</span>
                        <span className="tabular-nums text-slate-500 dark:text-slate-400 shrink-0">{eur(k.betrag)}</span>
                      </div>
                    ))}
                    {data.ausgaben_kategorien.length > 8 && (
                      <p className="text-xs text-slate-400 pl-4">
                        + {data.ausgaben_kategorien.length - 8} weitere
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Einnahmen nach USt-Satz */}
          {data.einnahmen_nach_ust.length > 0 && (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
              <h2 className="text-sm font-semibold text-slate-600 dark:text-slate-300 mb-4">
                Einnahmen nach Umsatzsteuersatz
                <InfoTooltip text="Zeigt welcher Anteil deiner Einnahmen mit welchem USt-Satz versteuert wird. Relevant für die UStVA." />
              </h2>
              <div className="flex flex-wrap gap-6">
                {data.einnahmen_nach_ust.map(u => (
                  <div key={u.satz} className="flex flex-col">
                    <span className="text-xs text-slate-500 dark:text-slate-400">{u.satz}</span>
                    <span className="text-lg font-semibold tabular-nums text-emerald-600 dark:text-emerald-400">
                      {eur(u.betrag)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Detailtabelle */}
          <KategorienTabelle
            einnahmen={data.einnahmen_nach_ust.reduce((s, u) => s + u.betrag, 0)}
            ausgaben_kategorien={data.ausgaben_kategorien}
            zeitraum_label={data.zeitraum_label}
          />

        </div>
      )}
    </div>
  )
}

// ── Detailtabelle ──────────────────────────────────────────────────────────────

function KategorienTabelle({
  einnahmen,
  ausgaben_kategorien,
  zeitraum_label,
}: {
  einnahmen: number
  ausgaben_kategorien: { name: string; betrag: number }[]
  zeitraum_label: string
}) {
  const [offen, setOffen] = useState(false)
  const contentRef = useRef<HTMLDivElement>(null)

  const ausgaben_gesamt = ausgaben_kategorien.reduce((s, k) => s + k.betrag, 0)
  const gewinn = einnahmen - ausgaben_gesamt

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
      <button
        onClick={() => setOffen(v => !v)}
        className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors rounded-xl"
      >
        <h2 className="text-sm font-semibold text-slate-600 dark:text-slate-300">
          Detailansicht – {zeitraum_label}
        </h2>
        <span className={`material-symbols-outlined text-slate-400 transition-transform duration-200 ${offen ? 'rotate-180' : ''}`}>
          expand_more
        </span>
      </button>

      <div
        ref={contentRef}
        className="overflow-hidden transition-all duration-200"
        style={{ maxHeight: offen ? (contentRef.current?.scrollHeight ?? 2000) + 'px' : '0px' }}
      >
        <div className="px-5 pb-5">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-700">
                <th className="text-left py-2 text-xs font-medium text-slate-500 dark:text-slate-400">Kategorie</th>
                <th className="text-right py-2 text-xs font-medium text-slate-500 dark:text-slate-400" title="ohne MwSt">Betrag (netto)</th>
                <th className="text-right py-2 text-xs font-medium text-slate-500 dark:text-slate-400">Anteil</th>
              </tr>
            </thead>
            <tbody>
              {/* Einnahmen-Zeile */}
              <tr className="border-b border-slate-100 dark:border-slate-700">
                <td colSpan={3} className="py-2 text-xs font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wide">
                  Einnahmen
                </td>
              </tr>
              <tr className="border-b border-slate-100 dark:border-slate-700">
                <td className="py-2 text-slate-700 dark:text-slate-200 pl-3">Betriebseinnahmen gesamt</td>
                <td className="py-2 text-right tabular-nums text-emerald-600 dark:text-emerald-400 font-medium">
                  {eur(einnahmen)}
                </td>
                <td className="py-2 text-right tabular-nums text-slate-400">100 %</td>
              </tr>

              {/* Ausgaben */}
              <tr className="border-b border-slate-100 dark:border-slate-700">
                <td colSpan={3} className="py-2 text-xs font-semibold text-red-500 dark:text-red-400 uppercase tracking-wide">
                  Ausgaben
                </td>
              </tr>
              {ausgaben_kategorien.map(k => (
                <tr key={k.name} className="border-b border-slate-50 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors">
                  <td className="py-1.5 text-slate-600 dark:text-slate-300 pl-3">{k.name}</td>
                  <td className="py-1.5 text-right tabular-nums text-slate-700 dark:text-slate-200">
                    {eur(k.betrag)}
                  </td>
                  <td className="py-1.5 text-right tabular-nums text-slate-400">
                    {einnahmen > 0 ? ((k.betrag / einnahmen) * 100).toFixed(1) + ' %' : '—'}
                  </td>
                </tr>
              ))}
              {ausgaben_kategorien.length === 0 && (
                <tr>
                  <td colSpan={3} className="py-3 text-center text-slate-400 text-xs pl-3">
                    Keine Ausgaben im gewählten Zeitraum
                  </td>
                </tr>
              )}

              {/* Summenzeilen */}
              <tr className="border-t-2 border-slate-200 dark:border-slate-600">
                <td className="py-2 text-slate-500 dark:text-slate-400 text-xs">Ausgaben gesamt</td>
                <td className="py-2 text-right tabular-nums text-red-500 dark:text-red-400 font-medium">
                  {eur(ausgaben_gesamt)}
                </td>
                <td className="py-2 text-right tabular-nums text-slate-400">
                  {einnahmen > 0 ? ((ausgaben_gesamt / einnahmen) * 100).toFixed(1) + ' %' : '—'}
                </td>
              </tr>
              <tr className="bg-slate-50 dark:bg-slate-700/50 rounded">
                <td className="py-2.5 font-bold text-slate-700 dark:text-slate-100 pl-1">Gewinn / Verlust</td>
                <td className={`py-2.5 text-right tabular-nums font-bold ${gewinn >= 0 ? 'text-blue-600 dark:text-blue-400' : 'text-red-600 dark:text-red-400'}`}>
                  {eur(gewinn)}
                </td>
                <td className={`py-2.5 text-right tabular-nums font-bold ${gewinn >= 0 ? 'text-blue-600 dark:text-blue-400' : 'text-red-600 dark:text-red-400'}`}>
                  {einnahmen > 0 ? ((gewinn / einnahmen) * 100).toFixed(1) + ' %' : '—'}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
