import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  berechneJahresUStVA, getJahresUStVAPdfUrl,
  getUnternehmen, openUrl,
} from '../../api/client'

const KZ_META: [string, string, string, boolean][] = [
  ['A. Steuerpflichtige Ausgangsumsätze', '81', 'Umsätze 19 % – Bemessungsgrundlage', false],
  ['', '83', 'Umsatzsteuer 19 %', true],
  ['', '86', 'Umsätze 7 % – Bemessungsgrundlage', false],
  ['', '88', 'Umsatzsteuer 7 %', true],
  ['B. Steuerfreie Umsätze mit Vorsteuerabzug', '41', 'Innergemeinschaftliche Lieferungen (§4 Nr. 1b)', false],
  ['C. Innergemeinschaftliche Erwerbe', '89', 'Steuerpflichtige Erwerbe 19 %', false],
  ['', '93', 'Umsatzsteuer ig. Erwerb 19 %', true],
  ['D. Leistungsempfänger als Steuerschuldner (§13b UStG)', '46', 'Sonstige Leistungen EU-Unternehmer (§13b Abs. 1)', false],
  ['', '47', 'Umsatzsteuer §13b Abs. 1', true],
  ['', '84', 'Andere §13b-Leistungen (Abs. 2 Nr. 1, 2, 4–12)', false],
  ['', '85', 'Umsatzsteuer §13b Abs. 2', true],
  ['F. Abziehbare Vorsteuerbeträge', '66', 'Vorsteuer aus Rechnungen (§15 Abs. 1 Satz 1 Nr. 1 UStG)', false],
  ['', '61', 'Vorsteuer ig. Erwerb (§15 Abs. 1 Satz 1 Nr. 3 UStG)', false],
  ['', '67', 'Vorsteuer aus §13b-Leistungen (§15 Abs. 1 Satz 1 Nr. 4 UStG)', false],
]

function euroFmt(v: string | number): string {
  const n = typeof v === 'string' ? parseFloat(v) : v
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n)
}

function KZZeile({ kz, label, wert, istSteuer = false, bold = false }:
  { kz: string; label: string; wert: string; istSteuer?: boolean; bold?: boolean }) {
  const n = parseFloat(wert)
  const negativ = n < 0
  return (
    <div className={`flex items-center gap-3 py-2 ${bold ? 'border-t border-slate-200 dark:border-slate-600 mt-1 pt-3' : ''}`}>
      <span className={`shrink-0 inline-flex items-center justify-center w-9 h-6 rounded text-xs font-bold text-white ${bold ? 'bg-slate-700 dark:bg-slate-500' : 'bg-blue-600 dark:bg-blue-700'}`}>
        {kz}
      </span>
      <span className={`flex-1 text-sm ${istSteuer ? 'text-slate-500 dark:text-slate-400 text-xs' : bold ? 'font-semibold text-slate-800 dark:text-slate-100' : 'text-slate-700 dark:text-slate-200'}`}>
        {label}
      </span>
      <span className={`tabular-nums text-sm font-medium ${negativ ? 'text-green-600 dark:text-green-400' : bold ? 'text-slate-800 dark:text-slate-100' : 'text-slate-700 dark:text-slate-200'}`}>
        {n === 0 ? <span className="text-slate-300 dark:text-slate-600">—</span> : euroFmt(wert)}
      </span>
    </div>
  )
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

export function JahresUStPage() {
  const now = new Date()
  const jahre = Array.from({ length: 5 }, (_, i) => now.getFullYear() - i)
  const [jahr, setJahr] = useState(now.getFullYear() - 1)
  const [pdfLaedt, setPdfLaedt] = useState(false)
  const [pdfFehler, setPdfFehler] = useState<string | null>(null)
  const [pdfOk, setPdfOk] = useState(false)

  const { data: unt } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen })

  const { data, isLoading, error } = useQuery({
    queryKey: ['jahres-ustva', jahr],
    queryFn: () => berechneJahresUStVA(jahr),
    enabled: !!unt,
  })

  async function handlePdf() {
    setPdfLaedt(true); setPdfFehler(null); setPdfOk(false)
    try {
      await openUrl(await getJahresUStVAPdfUrl(jahr))
      setPdfOk(true)
    } catch (e: any) {
      setPdfFehler(e?.message ?? 'PDF-Export fehlgeschlagen')
    } finally { setPdfLaedt(false) }
  }

  // KZ-Tabelle nur Zeilen ≠ 0, nach Abschnitt gruppiert
  const gruppen = data && !data.ist_kleinunternehmer ? (() => {
    const result: { abschnitt: string; zeilen: typeof KZ_META }[] = []
    let aktGruppe: { abschnitt: string; zeilen: typeof KZ_META } | null = null
    for (const meta of KZ_META) {
      const [abschnitt, nr] = meta
      const wert = parseFloat(String((data as any)[`kz_${nr}`] ?? '0'))
      if (wert === 0) continue
      const eff = abschnitt || aktGruppe?.abschnitt || ''
      if (!aktGruppe || (abschnitt && abschnitt !== aktGruppe.abschnitt)) {
        aktGruppe = { abschnitt: eff, zeilen: [] }
        result.push(aktGruppe)
      }
      aktGruppe.zeilen.push(meta)
    }
    return result
  })() : []

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">Jahresumsatzsteuererklärung</h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        Anzeigehilfe für die USt 2A – berechnet aus allen Journalbuchungen des Wirtschaftsjahres (Ist-Versteuerung).
        Übertrage die Kennziffern in{' '}
        <button type="button" onClick={() => openUrl('https://www.elster.de')}
          className="text-blue-600 dark:text-blue-400 hover:underline">ELSTER</button>{' '}
        oder gib sie an deinen Steuerberater.
      </p>

      {/* Jahresauswahl + PDF */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 mb-6">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Wirtschaftsjahr</label>
            <select value={jahr} onChange={e => setJahr(Number(e.target.value))}
              className="border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100">
              {jahre.map(j => <option key={j} value={j}>{j}</option>)}
            </select>
          </div>
          {data && (
            <div className="flex items-center gap-2">
              <button onClick={handlePdf} disabled={pdfLaedt}
                className="px-3 py-1.5 text-xs font-medium border border-slate-200 dark:border-slate-600 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors">
                {pdfLaedt ? '…' : '📄 PDF'}
              </button>
              {pdfOk && <span className="text-xs text-emerald-600 dark:text-emerald-400">✓ geöffnet</span>}
              {pdfFehler && <span className="text-xs text-red-600 dark:text-red-400">{pdfFehler}</span>}
            </div>
          )}
          {isLoading && <span className="text-sm text-slate-400 dark:text-slate-500">Berechne…</span>}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl p-4 mb-6 text-sm text-red-700 dark:text-red-300">
          {(error as Error).message}
        </div>
      )}

      {data && (
        <>
          {/* Kleinunternehmer §19 */}
          {data.ist_kleinunternehmer && (
            <div className="space-y-3 mb-6">
              <Abschnitt titel="Kleinunternehmer §19 UStG – Zeile 23">
                <KZZeile kz="48"
                  label="Umsätze, für die als KU keine USt geschuldet wird (§19 Abs. 1 UStG)"
                  wert={data.kz_48} bold />
              </Abschnitt>
              <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-xl px-4 py-3 text-sm text-blue-800 dark:text-blue-200">
                Als Kleinunternehmer §19 UStG schuldest du keine Umsatzsteuer.
                Trage den Gesamtumsatz ({euroFmt(data.kz_48)}) in ELSTER ein (USt 2A, Zeile 23 / KZ 48) –
                das Finanzamt prüft damit, ob du die §19-Grenze eingehalten hast.
              </div>
            </div>
          )}

          {/* Reguläre Steuerpflichtige */}
          {!data.ist_kleinunternehmer && (
            <>
              {gruppen.length === 0 ? (
                <p className="text-sm text-slate-400 dark:text-slate-500 mb-6">Keine Buchungen im Wirtschaftsjahr {jahr}.</p>
              ) : gruppen.map(({ abschnitt, zeilen }) => (
                <Abschnitt key={abschnitt} titel={abschnitt}>
                  {zeilen.map(([, nr, bezeichnung, istSteuer]) => (
                    <KZZeile key={nr} kz={nr} label={bezeichnung}
                      wert={String((data as any)[`kz_${nr}`] ?? '0')} istSteuer={istSteuer} />
                  ))}
                </Abschnitt>
              ))}

              {/* Jahressteuer */}
              <Abschnitt titel="H. Jahressteuer">
                <KZZeile kz="—"
                  label={parseFloat(data.zahllast) < 0 ? 'Verbleibender Überschuss (Erstattung)' : 'Jahresumsatzsteuer'}
                  wert={data.zahllast} bold />
              </Abschnitt>

              {/* Vorauszahlungsanrechnung */}
              {data.gespeicherte_perioden > 0 ? (
                <Abschnitt titel={`Vorauszahlungsanrechnung (${data.gespeicherte_perioden} Voranmeldungen gespeichert)`}>
                  <KZZeile kz="76" label="Summe geleistete Vorauszahlungen (aus gespeicherten Voranmeldungen)"
                    wert={data.summe_vorauszahlungen} />
                  <KZZeile kz="—"
                    label={parseFloat(data.restschuld) < 0 ? 'Verbleibender Überschuss (Erstattung)' : 'Verbleibende Zahllast'}
                    wert={data.restschuld} bold />
                </Abschnitt>
              ) : (
                <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-xs text-slate-500 dark:text-slate-400 mb-4">
                  Keine Voranmeldungen für {jahr} gespeichert – trage geleistete Vorauszahlungen manuell in ELSTER ein (KZ 76).
                </div>
              )}

              {/* Anlage UR */}
              {data.hat_ig_transaktionen && (
                <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl px-4 py-3 text-sm text-red-800 dark:text-red-200 mb-4">
                  <span className="font-semibold">Anlage UR erforderlich:</span> Im Journal existieren
                  innergemeinschaftliche Umsätze (KZ 41/89/93) oder §13b-Leistungen (KZ 46/84).
                  Die Anlage UR ist separat in ELSTER auszufüllen (Aufschlüsselung nach EU-Ländern).
                </div>
              )}

              <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">
                Grundlage: Journalbuchungen {data.von} bis {data.bis} (Ist-Versteuerung / Zuflussprinzip).
                Nicht abgedeckt: KZ 62 (Einfuhrumsatzsteuer), KZ 50 (unterjähriger §19-Wechsel), Reiseleistungen §25.
              </p>
            </>
          )}
        </>
      )}
    </div>
  )
}
