import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { berechneEUER, berechneEUERDetail, getEUERPdfUrl, openUrl, type EUERErgebnis, type EUERDetailErgebnis } from '../../api/client'
import { useMxAuto } from '../../hooks/useAnsicht'
import { ExportButtons } from '../../components/ExportButtons'

const ABSCHNITT_LABEL: Record<string, string> = {
  A: 'A – Betriebseinnahmen',
  B: 'B – Betriebsausgaben',
  H: 'Entnahmen / Einlagen (nachrichtlich)',
}

function euroFmt(v: string | number): string {
  const n = typeof v === 'string' ? parseFloat(v) : v
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n)
}

function SummenZeile({ label, betrag, hervorgehoben = false }: {
  label: string; betrag: string; hervorgehoben?: boolean
}) {
  const n = parseFloat(betrag)
  return (
    <div className={`flex items-center justify-between px-4 py-2.5 ${
      hervorgehoben
        ? 'bg-slate-800 dark:bg-slate-900 text-white font-bold text-base'
        : 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100 font-semibold text-sm'
    }`}>
      <span>{label}</span>
      <span className={`tabular-nums ${n < 0 ? 'text-red-400' : hervorgehoben ? 'text-white' : ''}`}>
        {euroFmt(betrag)}
      </span>
    </div>
  )
}

export function EUERPage() {
  const mxAuto = useMxAuto()
  const now = new Date()
  const [jahr, setJahr] = useState(now.getFullYear() - (now.getMonth() < 3 ? 1 : 0))
  const [pdfFehler, setPdfFehler] = useState<string | null>(null)
  const [detailansicht, setDetailansicht] = useState(false)
  const jahre = Array.from({ length: 6 }, (_, i) => now.getFullYear() - i)

  const { data: ergebnis, isLoading, error } = useQuery<EUERErgebnis>({
    queryKey: ['euer-berechnen', jahr],
    queryFn: () => berechneEUER(jahr),
  })

  const { data: detail } = useQuery<EUERDetailErgebnis>({
    queryKey: ['euer-kategorien', jahr],
    queryFn: () => berechneEUERDetail(jahr),
    enabled: detailansicht,
  })

  async function handlePdf() {
    setPdfFehler(null)
    try { await openUrl(await getEUERPdfUrl(jahr)) }
    catch (e: any) { setPdfFehler(e?.message ?? 'PDF-Export fehlgeschlagen') }
  }

  // Zeilen nach Abschnitt gruppieren
  const abschnitte = ergebnis
    ? Object.entries(
        ergebnis.zeilen.reduce<Record<string, typeof ergebnis.zeilen>>((acc, z) => {
          ;(acc[z.abschnitt] ??= []).push(z)
          return acc
        }, {})
      ).sort(([a], [b]) => a.localeCompare(b))
    : []

  // Detail-Index für schnellen Zugriff per Zeilen-Nr.
  const detailByZeile = detail
    ? Object.fromEntries(detail.zeilen.map(z => [z.zeile, z]))
    : {}

  return (
    <div className={`max-w-2xl ${mxAuto} px-6 py-8`}>
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">
        EÜR – Einnahmen-Überschuss-Rechnung
      </h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        Berechnet aus Journalbuchungen nach Ist-Versteuerung (Zuflussprinzip). Anzeigehilfe für ELSTER oder Steuerberater.
      </p>

      {/* Jahresauswahl + PDF */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 mb-6 flex items-center gap-4">
        <div>
          <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Wirtschaftsjahr</label>
          <select value={jahr} onChange={e => setJahr(Number(e.target.value))}
            className="border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100">
            {jahre.map(j => <option key={j} value={j}>{j}</option>)}
          </select>
        </div>
        {isLoading && <span className="text-sm text-slate-500 dark:text-slate-400">Berechne…</span>}
        {ergebnis && (
          <div className="flex items-center gap-2 ml-auto">
            <button
              onClick={() => setDetailansicht(v => !v)}
              className={`px-3 py-1.5 text-xs font-medium border rounded-lg transition-colors ${
                detailansicht
                  ? 'bg-blue-600 border-blue-600 text-white hover:bg-blue-700'
                  : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
              }`}>
              🔍 Aufschlüsselung
            </button>
            <ExportButtons formats={['pdf']} onExport={handlePdf} />
            {pdfFehler && <span className="text-xs text-red-600 dark:text-red-400">{pdfFehler}</span>}
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl p-4 mb-6 text-sm text-red-700 dark:text-red-300">
          {(error as Error).message}
        </div>
      )}

      {ergebnis && (
        <div className="space-y-4">
          {ergebnis.ist_kleinunternehmer && (
            <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-xl p-4 text-sm text-amber-800 dark:text-amber-200">
              Kleinunternehmer §19 UStG – Umsatzsteuer-Zeilen (15, 48) sind 0.
            </div>
          )}

          {abschnitte.map(([abschnitt, zeilen]) => (
            <div key={abschnitt} className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
              <div className="bg-slate-100 dark:bg-slate-700 px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">
                {ABSCHNITT_LABEL[abschnitt] ?? abschnitt}
              </div>
              <div className="divide-y divide-slate-50 dark:divide-slate-700">
                {zeilen.map(z => {
                  const d = detailByZeile[z.zeile]
                  return (
                    <div key={z.zeile}>
                      <div className="flex items-center gap-3 px-4 py-2.5">
                        <span className="shrink-0 inline-flex items-center justify-center w-11 h-6 rounded text-xs font-bold text-white bg-blue-600 dark:bg-blue-700">
                          Z. {z.zeile}
                        </span>
                        <span className="flex-1 text-sm text-slate-700 dark:text-slate-200">{z.bezeichnung}</span>
                        <span className={`tabular-nums text-sm font-medium ${parseFloat(z.betrag) < 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-800 dark:text-slate-100'}`}>
                          {euroFmt(z.betrag)}
                        </span>
                      </div>
                      {detailansicht && d && d.kategorien.length > 0 && (
                        <div className="bg-slate-50 dark:bg-slate-900/40 divide-y divide-slate-100 dark:divide-slate-800">
                          {d.kategorien.map(k => (
                            <div key={k.name} className="flex items-center gap-3 pl-10 pr-4 py-1.5">
                              <span className="text-slate-400 dark:text-slate-600 text-xs shrink-0">└</span>
                              <span className="flex-1 text-xs text-slate-500 dark:text-slate-400">{k.name}</span>
                              <span className={`tabular-nums text-xs ${parseFloat(k.betrag) < 0 ? 'text-red-500 dark:text-red-400' : 'text-slate-500 dark:text-slate-400'}`}>
                                {euroFmt(k.betrag)}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
              {abschnitt === 'A' && (
                <SummenZeile label="Summe Betriebseinnahmen (Z. 22)" betrag={ergebnis.summe_einnahmen} />
              )}
              {abschnitt === 'B' && (
                <SummenZeile label="Summe Betriebsausgaben (Z. 74)" betrag={ergebnis.summe_ausgaben} />
              )}
            </div>
          ))}

          {/* Gewinn / Verlust */}
          <div className="rounded-xl overflow-hidden">
            <SummenZeile
              label={parseFloat(ergebnis.gewinn_verlust) >= 0 ? 'Gewinn (Zeile 75)' : 'Verlust (Zeile 75)'}
              betrag={ergebnis.gewinn_verlust}
              hervorgehoben
            />
          </div>

          {/* Anlage AVEÜR – AfA automatisch oder Hinweis */}
          {parseFloat(ergebnis.aveur_afa) > 0 ? (
            <div className="bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 rounded-xl p-4 text-sm text-blue-800 dark:text-blue-200">
              <strong>Anlage AVEÜR:</strong> AfA {ergebnis.jahr} ({euroFmt(ergebnis.aveur_afa)}) wurde automatisch aus dem Anlagenverzeichnis in Zeile 33 eingetragen.
              {parseFloat(ergebnis.anlage_zugaenge) > 0 && (
                <span className="ml-1">Anlagezugänge {ergebnis.jahr}: {euroFmt(ergebnis.anlage_zugaenge)}.</span>
              )}
            </div>
          ) : parseFloat(ergebnis.anlage_zugaenge) > 0 ? (
            <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-xl p-4 text-sm text-amber-800 dark:text-amber-200">
              <strong>Anlagezugänge {ergebnis.jahr}:</strong> {euroFmt(ergebnis.anlage_zugaenge)} (KFZ, EDV o.ä.) – erfasse die Wirtschaftsgüter unter <strong>Auswertung → Anlage AVEÜR</strong>, damit die AfA automatisch in Zeile 33 einfließt.
            </div>
          ) : null}

          <p className="text-xs text-slate-400 dark:text-slate-500">
            Grundlage: Journalbuchungen {ergebnis.jahr} · Ist-Versteuerung (Zahlungsdatum).
          </p>
        </div>
      )}

      {ergebnis && ergebnis.zeilen.length === 0 && (
        <div className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 text-sm text-slate-500 dark:text-slate-400 text-center">
          Keine Buchungen für {jahr} gefunden.
        </div>
      )}
    </div>
  )
}
