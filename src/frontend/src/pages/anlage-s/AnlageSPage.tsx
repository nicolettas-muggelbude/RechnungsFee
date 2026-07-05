import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { berechneAnlageS, getAnlageSPdfUrl, openUrl, type AnlageSErgebnis } from '../../api/client'

function euroFmt(v: string | number): string {
  const n = typeof v === 'string' ? parseFloat(v) : v
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(Math.abs(n))
}

function Abschnitt({ titel, children }: { titel: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <div className="bg-slate-100 dark:bg-slate-700 px-3 py-1.5 rounded-t text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">
        {titel}
      </div>
      <div className="bg-white dark:bg-slate-800 rounded-b border border-t-0 border-slate-200 dark:border-slate-700 px-4 divide-y divide-slate-100 dark:divide-slate-700">
        {children}
      </div>
    </div>
  )
}

function ZeileNr({ zeile, label, wert, leer = false }: {
  zeile: string; label: string; wert?: string; leer?: boolean
}) {
  return (
    <div className="flex items-center gap-3 py-2">
      <span className="shrink-0 inline-flex items-center justify-center w-11 h-6 rounded text-xs font-bold text-white bg-blue-600 dark:bg-blue-700">
        Z. {zeile}
      </span>
      <span className="flex-1 text-sm text-slate-700 dark:text-slate-200">{label}</span>
      <span className={`tabular-nums text-sm font-medium ${leer ? 'text-slate-300 dark:text-slate-600' : 'text-slate-800 dark:text-slate-100'}`}>
        {wert ?? <span className="text-slate-300 dark:text-slate-600">—</span>}
      </span>
    </div>
  )
}

function ZeileText({ label, wert }: { label: string; wert?: string }) {
  return (
    <div className="flex items-center gap-3 py-2">
      <span className="shrink-0 w-11" />
      <span className="flex-1 text-sm text-slate-700 dark:text-slate-200">{label}</span>
      <span className={`text-sm font-medium ${wert ? 'text-slate-800 dark:text-slate-100' : 'text-slate-300 dark:text-slate-600'}`}>
        {wert || '—'}
      </span>
    </div>
  )
}

function SummenZeile({ label, betrag }: { label: string; betrag: number }) {
  const negativ = betrag < 0
  return (
    <div className="bg-slate-800 dark:bg-slate-900 text-white font-bold text-base flex items-center justify-between px-4 py-2.5 rounded-xl">
      <span>{label}</span>
      <span className={`tabular-nums ${negativ ? 'text-red-400' : ''}`}>
        {euroFmt(betrag)}
      </span>
    </div>
  )
}

export function AnlageSPage() {
  const now = new Date()
  const [jahr, setJahr] = useState(now.getFullYear() - (now.getMonth() < 3 ? 1 : 0))
  const jahre = Array.from({ length: 6 }, (_, i) => now.getFullYear() - i)

  const [pdfLaedt, setPdfLaedt] = useState(false)
  const [pdfFehler, setPdfFehler] = useState<string | null>(null)

  async function handlePdf() {
    setPdfLaedt(true); setPdfFehler(null)
    try { await openUrl(await getAnlageSPdfUrl(jahr)) }
    catch (e: any) { setPdfFehler(e?.message ?? 'PDF-Export fehlgeschlagen') }
    finally { setPdfLaedt(false) }
  }

  const { data, isLoading, error } = useQuery<AnlageSErgebnis>({
    queryKey: ['anlage-s', jahr],
    queryFn: () => berechneAnlageS(jahr),
  })

  const gv = data ? parseFloat(data.gewinn_verlust) : 0
  const istGewinn = gv >= 0
  const stammdatenUnvollstaendig = data && (!data.steuernummer || !data.finanzamt || !data.berufsbezeichnung)

  return (
    <div className="max-w-2xl px-6 py-8">
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">
        Anlage S – Einkünfte aus selbstständiger Arbeit
      </h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
        Anzeigehilfe für die Einkommensteuererklärung (§18 EStG) · Gewinn/Verlust aus der EÜR.
        Übertrage die Werte in{' '}
        <span className="text-blue-600 dark:text-blue-400">ELSTER</span>{' '}
        oder gib sie an deinen Steuerberater.
      </p>
      {data?.taetigkeitsart === 'gemischt' && (
        <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950 px-4 py-3 text-sm text-amber-800 dark:text-amber-300">
          <strong>Hinweis:</strong> Du hast gemischte Tätigkeit (freiberuflich + gewerblich) angegeben. Die Anlage S gilt nur für den freiberuflichen Anteil (§18 EStG). Für gewerbliche Einkünfte ist zusätzlich die <strong>Anlage G</strong> auszufüllen.
        </div>
      )}

      {/* Jahresauswahl */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 mb-6 flex items-center gap-4">
        <div>
          <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Wirtschaftsjahr</label>
          <select
            value={jahr}
            onChange={e => setJahr(Number(e.target.value))}
            className="border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100"
          >
            {jahre.map(j => <option key={j} value={j}>{j}</option>)}
          </select>
        </div>
        {isLoading && <span className="text-sm text-slate-500 dark:text-slate-400">Berechne…</span>}
        {data && !isLoading && (
          <div className="ml-auto flex items-center gap-2">
            <button onClick={handlePdf} disabled={pdfLaedt}
              className="px-3 py-1.5 text-xs font-medium border border-slate-200 dark:border-slate-600 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors">
              {pdfLaedt ? '…' : '📄 PDF'}
            </button>
            {pdfFehler && <span className="text-xs text-red-600 dark:text-red-400">{pdfFehler}</span>}
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl p-4 mb-6 text-sm text-red-700 dark:text-red-300">
          {(error as Error).message}
        </div>
      )}

      {data && (
        <div className="space-y-0">

          {/* Persönliche Angaben */}
          <Abschnitt titel="Persönliche Angaben">
            <ZeileNr zeile="1" label="Name, Vorname"
              wert={[data.nachname, data.vorname].filter(Boolean).join(', ') || undefined} />
            <ZeileText label="Finanzamt" wert={data.finanzamt || undefined} />
            <ZeileNr zeile="3" label="Steuernummer" wert={data.steuernummer || undefined} />
            <ZeileNr zeile="4" label="Art der Tätigkeit (Berufsbezeichnung)" wert={data.berufsbezeichnung || undefined} />
          </Abschnitt>

          {/* Laufende Einkünfte */}
          <Abschnitt titel="Laufende Einkünfte (aus EÜR)">
            <div className="flex items-center gap-3 py-2">
              <span className="shrink-0 inline-flex items-center justify-center w-11 h-6 rounded text-xs font-bold text-white bg-teal-600 dark:bg-teal-700">
                KZ 100
              </span>
              <span className="flex-1 text-sm text-slate-700 dark:text-slate-200">
                {istGewinn ? 'Gewinn aus freiberuflicher Tätigkeit' : 'Verlust aus freiberuflicher Tätigkeit'}
              </span>
              <span className={`tabular-nums text-sm font-medium ${!istGewinn ? 'text-red-600 dark:text-red-400' : 'text-slate-800 dark:text-slate-100'}`}>
                {!istGewinn && '− '}{euroFmt(gv)}
              </span>
            </div>
          </Abschnitt>

          {/* KFZ */}
          {data.kfz_hinweise.length > 0 && (
            <Abschnitt titel="KFZ – Privatnutzung">
              {data.kfz_hinweise.map((k, i) => (
                <ZeileNr key={i} zeile="18"
                  label={`${k.bezeichnung}${k.kennzeichen ? ` (${k.kennzeichen})` : ''} – ${parseFloat(k.privat_anteil_prozent).toFixed(0)} % Privatanteil`}
                  wert="→ Betrag manuell ermitteln"
                />
              ))}
            </Abschnitt>
          )}

          {/* Ergebnis */}
          <SummenZeile
            label={istGewinn ? `Gewinn ${jahr} (ELSTER KZ 100)` : `Verlust ${jahr} (ELSTER KZ 100)`}
            betrag={gv}
          />

          {/* KFZ-Hinweis */}
          {data.kfz_hinweise.length > 0 && (
            <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-xl px-4 py-3 text-sm text-amber-800 dark:text-amber-200 mt-4">
              <strong>Zeile 18 – KFZ-Privatnutzung:</strong> Bei der <strong>1 %-Methode</strong> ist der geldwerte Vorteil in Zeile 18 einzutragen. Bei der <strong>Fahrtenbuchmethode</strong> oder der <strong>km-Pauschale</strong> (Privatfahrzeug) entfällt Zeile 18.
            </div>
          )}

          {/* Fehlende Stammdaten */}
          {stammdatenUnvollstaendig && (
            <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-xl px-4 py-3 text-sm text-blue-800 dark:text-blue-300 mt-4">
              Einige Felder sind leer.{' '}
              <a href="/unternehmen" className="underline font-medium">Einstellungen → Unternehmen</a>{' '}
              → Steuernummer, Finanzamt und Berufsbezeichnung hinterlegen.
            </div>
          )}

          <p className="text-xs text-slate-400 dark:text-slate-500 mt-4">
            Grundlage: EÜR {jahr} (Ist-Versteuerung / Zuflussprinzip) · Zeilen- und KZ-Nummern nach Anlage S {jahr}.
            Diese Anzeigehilfe ersetzt keine Steuerberatung.
          </p>
        </div>
      )}
    </div>
  )
}
