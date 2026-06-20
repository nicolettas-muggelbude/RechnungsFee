import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { berechneAnlageG, getAnlageGPdfUrl, isTauri, openInPdfWindow, openUrl, type AnlageGErgebnis } from '../../api/client'

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
      <span className="shrink-0 inline-flex items-center justify-center w-11 h-6 rounded text-xs font-bold text-white bg-green-600 dark:bg-green-700">
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

function ElsterKz({ kz, label, wert, leer = false }: {
  kz: string; label: string; wert?: string; leer?: boolean
}) {
  return (
    <div className="flex items-center gap-3 py-2">
      <span className="shrink-0 inline-flex items-center justify-center w-11 h-6 rounded text-xs font-bold text-white bg-teal-600 dark:bg-teal-700">
        {kz}
      </span>
      <span className="flex-1 text-sm text-slate-700 dark:text-slate-200">{label}</span>
      <span className={`tabular-nums text-sm font-medium ${leer ? 'text-slate-300 dark:text-slate-600' : 'text-slate-800 dark:text-slate-100'}`}>
        {wert ?? <span className="text-slate-300 dark:text-slate-600">—</span>}
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

export function AnlageGPage() {
  const now = new Date()
  const [jahr, setJahr] = useState(now.getFullYear() - (now.getMonth() < 3 ? 1 : 0))
  const jahre = Array.from({ length: 6 }, (_, i) => now.getFullYear() - i)
  const [hebesatzInput, setHebesatzInput] = useState('')
  const [messbetragInput, setMessbetragInput] = useState('')

  const [pdfLaedt, setPdfLaedt] = useState(false)
  const [pdfFehler, setPdfFehler] = useState<string | null>(null)

  const { data, isLoading, error } = useQuery<AnlageGErgebnis>({
    queryKey: ['anlage-g', jahr],
    queryFn: () => berechneAnlageG(jahr),
  })

  const hebesatz = parseFloat(hebesatzInput.replace(',', '.')) || 0
  const gewstGezahlt = data ? parseFloat(data.gewst_gezahlt) : 0

  // Messbetrag: aus manuellem Input ODER berechnet aus gezahlter GewSt ÷ Hebesatz
  const messbetragBerechnet = (gewstGezahlt > 0 && hebesatz > 0)
    ? gewstGezahlt / (hebesatz / 100)
    : 0
  const messbetrag = messbetragInput
    ? parseFloat(messbetragInput.replace(',', '.')) || 0
    : messbetragBerechnet
  const anrechnungsbetrag = messbetrag * 3.8

  const gv = data ? parseFloat(data.gewinn_verlust) : 0
  const istGewinn = gv >= 0
  const stammdatenUnvollstaendig = data && (!data.steuernummer || !data.finanzamt || !data.art_des_gewerbes)

  async function handlePdf() {
    setPdfLaedt(true); setPdfFehler(null)
    try {
      const url = await getAnlageGPdfUrl(jahr, messbetrag)
      if (isTauri()) {
        const resp = await fetch(url)
        if (!resp.ok) throw new Error(`PDF-Fehler: ${resp.status}`)
        const blob = await resp.blob()
        const blobUrl = URL.createObjectURL(blob)
        await openInPdfWindow(blobUrl, `Anlage G ${jahr}`)
        setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000)
      } else {
        await openUrl(url)
      }
    }
    catch (e: any) { setPdfFehler(e?.message ?? 'PDF-Export fehlgeschlagen') }
    finally { setPdfLaedt(false) }
  }

  return (
    <div className="max-w-2xl px-6 py-8">
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">
        Anlage G – Einkünfte aus Gewerbebetrieb
      </h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
        Anzeigehilfe für die Einkommensteuererklärung (§15 EStG) · Gewinn/Verlust aus der EÜR.
        Übertrage die Werte in{' '}
        <span className="text-blue-600 dark:text-blue-400">ELSTER</span>{' '}
        oder gib sie an deinen Steuerberater.
      </p>
      {data?.taetigkeitsart === 'gemischt' && (
        <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950 px-4 py-3 text-sm text-amber-800 dark:text-amber-300">
          <strong>Hinweis:</strong> Du hast gemischte Tätigkeit angegeben. Die Anlage G gilt nur für den gewerblichen Anteil (§15 EStG). Für freiberufliche Einkünfte ist zusätzlich die <strong>Anlage S</strong> auszufüllen.
        </div>
      )}

      {/* Jahresauswahl + Hebesatz */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 mb-6 flex items-center gap-4 flex-wrap">
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
        {data?.gewst_pflichtig && (
          <div>
            <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
              Hebesatz (%, aus GewSt-Bescheid)
            </label>
            <input
              type="text"
              inputMode="decimal"
              placeholder="z. B. 400"
              value={hebesatzInput}
              onChange={e => setHebesatzInput(e.target.value)}
              className="w-28 border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100"
            />
          </div>
        )}
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
            <ZeileNr zeile="4" label="Art des Gewerbebetriebs" wert={data.art_des_gewerbes || undefined} />
          </Abschnitt>

          {/* Laufende Einkünfte */}
          <Abschnitt titel="Laufende Einkünfte (aus EÜR §4 Abs. 3 EStG)">
            <ElsterKz kz="KZ 10" label="Gewinn 1. Betrieb"
              wert={istGewinn ? euroFmt(gv) : undefined}
              leer={!istGewinn} />
            <ElsterKz kz="KZ 11" label="Verlust 1. Betrieb"
              wert={!istGewinn ? euroFmt(gv) : undefined}
              leer={istGewinn} />
          </Abschnitt>

          {/* KFZ */}
          {data.kfz_hinweise.length > 0 && (
            <Abschnitt titel="KFZ – Privatnutzung">
              {data.kfz_hinweise.map((k, i) => (
                <ZeileNr key={i} zeile="→"
                  label={`${k.bezeichnung}${k.kennzeichen ? ` (${k.kennzeichen})` : ''} – ${parseFloat(k.privat_anteil_prozent).toFixed(0)} % Privatanteil`}
                  wert="→ Betrag manuell ermitteln"
                />
              ))}
            </Abschnitt>
          )}

          {/* Gewerbesteuer §35 EStG */}
          <Abschnitt titel="Gewerbesteuer-Anrechnung §35 EStG">
            <ZeileText label="Freibetrag Einzelunternehmer" wert="24.500,00 €" />
            {data.gewst_pflichtig ? (
              <>
                <ZeileNr zeile="52"
                  label="Tatsächlich zu zahlende Gewerbesteuer (lt. Journal)"
                  wert={gewstGezahlt > 0 ? euroFmt(gewstGezahlt) : undefined}
                />
                <ZeileText
                  label="Richtwert Messbetrag (Schätzung, ohne Hinzurechnungen/Kürzungen)"
                  wert={euroFmt(data.gewst_messbetrag_approx)}
                />
                {/* Z.51 Messbetrag: auto-berechnet oder manuell */}
                <div className="flex items-center gap-3 py-2">
                  <span className="shrink-0 inline-flex items-center justify-center w-11 h-6 rounded text-xs font-bold text-white bg-green-600 dark:bg-green-700">
                    Z. 51
                  </span>
                  <span className="flex-1 text-sm text-slate-700 dark:text-slate-200">
                    Gewerbesteuer-Messbetrag (lt. Bescheid)
                    {messbetragBerechnet > 0 && !messbetragInput && (
                      <span className="ml-2 text-xs text-green-600 dark:text-green-400">
                        berechnet aus Hebesatz
                      </span>
                    )}
                  </span>
                  <input
                    type="text"
                    inputMode="decimal"
                    placeholder={messbetragBerechnet > 0 ? euroFmt(messbetragBerechnet) : '0,00'}
                    value={messbetragInput}
                    onChange={e => setMessbetragInput(e.target.value)}
                    className="w-28 text-right border border-slate-200 dark:border-slate-600 rounded px-2 py-1 text-sm bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100"
                  />
                </div>
                {messbetrag > 0 && (
                  <ZeileText
                    label="Anrechenbarer Betrag (Messbetrag × 3,8, §35 EStG)"
                    wert={euroFmt(anrechnungsbetrag)}
                  />
                )}
              </>
            ) : (
              <ZeileText label="Gewinn unter Freibetrag – voraussichtlich keine Gewerbesteuer" wert="" />
            )}
          </Abschnitt>

          {/* Ergebnis */}
          <SummenZeile
            label={istGewinn ? `Gewinn ${jahr} (ELSTER KZ 10/11)` : `Verlust ${jahr} (ELSTER KZ 10/11)`}
            betrag={gv}
          />

          {/* KFZ-Hinweis */}
          {data.kfz_hinweise.length > 0 && (
            <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-xl px-4 py-3 text-sm text-amber-800 dark:text-amber-200 mt-4">
              <strong>KFZ-Privatnutzung:</strong> Bei der <strong>1 %-Methode</strong> ist der geldwerte Vorteil einzutragen. Bei der <strong>Fahrtenbuchmethode</strong> oder der <strong>km-Pauschale</strong> (Privatfahrzeug) entfällt dieser Eintrag.
            </div>
          )}

          {/* Gewerbesteuer-Hinweis */}
          {data.gewst_pflichtig && (
            <div className="bg-green-50 dark:bg-green-950/40 border border-green-200 dark:border-green-800 rounded-xl px-4 py-3 text-sm text-green-800 dark:text-green-200 mt-4">
              <strong>Gewerbesteuer-Messbetrag:</strong> Den genauen Messbetrag findest du im <strong>Gewerbesteuer-Festsetzungsbescheid</strong> deines Finanzamts. Der Richtwert oben ist eine Schätzung ohne Hinzurechnungen und Kürzungen nach §§ 8, 9 GewStG.
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
            Grundlage: EÜR {jahr} (Ist-Versteuerung / Zuflussprinzip) · Zeilennummern nach Anlage G {jahr}.
            Diese Anzeigehilfe ersetzt keine Steuerberatung.
          </p>
        </div>
      )}
    </div>
  )
}
