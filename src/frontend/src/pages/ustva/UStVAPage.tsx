import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  berechneUStVA, speichereUStVA, getUStVAHistorie, getUStVAPdfUrl,
  getUnternehmen, openUrl,
  type UStVAErgebnis,
} from '../../api/client'

// ---------------------------------------------------------------------------
// KZ-Metadaten – Reihenfolge wie im amtlichen Formular USt 1 A 2026
// [abschnitt, kz_nr, bezeichnung, ist_steuer, auto_berechenbar]
// ---------------------------------------------------------------------------
type KZMeta = [string, string, string, boolean, boolean]
const KZ_META: KZMeta[] = [
  ['A. Steuerpflichtige Ausgangsumsätze', '81', 'Umsätze 19 % – Bemessungsgrundlage', false, true],
  ['', '83', 'Umsatzsteuer 19 %', true, true],
  ['', '86', 'Umsätze 7 % – Bemessungsgrundlage', false, true],
  ['', '88', 'Umsatzsteuer 7 %', true, true],
  ['B. Steuerfreie Umsätze mit Vorsteuerabzug', '41', 'Innergemeinschaftliche Lieferungen (§4 Nr. 1b) an Abnehmer mit USt-IdNr.', false, false],
  ['', '87', 'Weitere steuerfreie Umsätze mit Vorsteuerabzug (Ausfuhr, §4 Nr. 2–7 UStG)', false, false],
  ['C. Innergemeinschaftliche Erwerbe', '89', 'Steuerpflichtige Erwerbe 19 %', false, true],
  ['', '93', 'Umsatzsteuer ig. Erwerb 19 %', true, true],
  ['D. Leistungsempfänger als Steuerschuldner (§13b UStG)', '46', 'Sonstige Leistungen EU-Unternehmer (§13b Abs. 1)', false, true],
  ['', '47', 'Umsatzsteuer §13b Abs. 1', true, true],
  ['', '84', 'Andere §13b-Leistungen (Abs. 2 Nr. 1, 2, 4–12)', false, true],
  ['', '85', 'Umsatzsteuer §13b Abs. 2', true, true],
  ['F. Abziehbare Vorsteuerbeträge', '66', 'Vorsteuer aus Rechnungen (§15 Abs. 1 Satz 1 Nr. 1 UStG)', false, true],
  ['', '61', 'Vorsteuer ig. Erwerb (§15 Abs. 1 Satz 1 Nr. 3 UStG)', false, true],
  ['', '67', 'Vorsteuer aus §13b-Leistungen (§15 Abs. 1 Satz 1 Nr. 4 UStG)', false, true],
]

// KZs die manuell eingegeben werden müssen (nicht aus Journal ableitbar)
const KZ_MANUELL = new Set(['41', '87'])

const MONATE = ['', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']

function zeitraumLabel(zeitraum: string): string {
  if (zeitraum.includes('-Q')) {
    const [jahr, q] = zeitraum.split('-Q')
    return `Q${q}/${jahr}`
  }
  try {
    const [jahr, mon] = zeitraum.split('-')
    return `${MONATE[parseInt(mon)]} ${jahr}`
  } catch { return zeitraum }
}

function euroFmt(v: string | number): string {
  const n = typeof v === 'string' ? parseFloat(v) : v
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n)
}

function kzKey(nr: string): keyof UStVAErgebnis {
  return `kz_${nr}` as keyof UStVAErgebnis
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

export function UStVAPage() {
  const qc = useQueryClient()
  const now = new Date()
  const [modus, setModus] = useState<'monat' | 'quartal'>('quartal')
  const [jahr, setJahr] = useState(now.getFullYear())
  const [monat, setMonat] = useState(now.getMonth() + 1)
  const [quartal, setQuartal] = useState(Math.ceil((now.getMonth() + 1) / 3))
  const [gespeichertMeldung, setGespeichertMeldung] = useState(false)
  const [pdfLaedt, setPdfLaedt] = useState(false)
  const [pdfFehler, setPdfFehler] = useState<string | null>(null)
  const [pdfExportiert, setPdfExportiert] = useState(false)
  // Manuelle Korrekturen für nicht-auto-berechnete KZs
  const [manuell, setManuell] = useState<Partial<Record<string, string>>>({})

  const zeitraum = modus === 'quartal'
    ? `${jahr}-Q${quartal}`
    : `${jahr}-${String(monat).padStart(2, '0')}`

  const { data: unt } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen })
  const { data: historie } = useQuery({ queryKey: ['ustva-historie'], queryFn: getUStVAHistorie })

  const { data: ergebnis, isLoading, error, refetch } = useQuery({
    queryKey: ['ustva-berechnen', zeitraum],
    queryFn: () => berechneUStVA(zeitraum),
    enabled: false,
  })

  const speichernMut = useMutation({
    mutationFn: speichereUStVA,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ustva-historie'] })
      setGespeichertMeldung(true)
      setTimeout(() => setGespeichertMeldung(false), 3000)
    },
  })

  async function handlePdf() {
    setPdfLaedt(true); setPdfFehler(null); setPdfExportiert(false)
    try {
      await openUrl(await getUStVAPdfUrl(zeitraum))
      setPdfExportiert(true)
    } catch (e: any) {
      setPdfFehler(e?.message ?? 'PDF-Export fehlgeschlagen')
    } finally {
      setPdfLaedt(false) }
  }

  // Wert aus Ergebnis + manuelle Überschreibung
  function kzWert(nr: string): string {
    if (manuell[nr] !== undefined) return manuell[nr]!
    if (!ergebnis) return '0'
    return String(ergebnis[kzKey(nr)] ?? '0')
  }

  // Alle KZ zusammenbauen (auto + manuell) für Speichern
  function alleKZ() {
    const base: Record<string, string> = {}
    for (const [,nr] of KZ_META) base[`kz_${nr}`] = kzWert(nr)
    base['zahllast'] = berechneZahllast()
    return base
  }

  function berechneZahllast(): string {
    const ust = ['83','88','93','47','85'].reduce((s, nr) => s + parseFloat(kzWert(nr) || '0'), 0)
    const vst = ['66','61','67'].reduce((s, nr) => s + parseFloat(kzWert(nr) || '0'), 0)
    return (ust - vst).toFixed(2)
  }

  const jahre = Array.from({ length: 5 }, (_, i) => now.getFullYear() - i)
  const rhythmus = (unt as any)?.voranmeldungsrhythmus ?? 'quartal'

  // Abschnitte mit mindestens einem Nicht-Null-Wert für die Anzeige ermitteln
  function renderKZTabelle() {
    const gruppen: { abschnitt: string; zeilen: KZMeta[] }[] = []
    let aktGruppe: { abschnitt: string; zeilen: KZMeta[] } | null = null

    for (const meta of KZ_META) {
      const [abschnitt, nr] = meta
      const wert = parseFloat(kzWert(nr) || '0')
      if (wert === 0) continue

      const effAbschnitt = abschnitt || aktGruppe?.abschnitt || ''
      if (!aktGruppe || (abschnitt && abschnitt !== aktGruppe.abschnitt)) {
        aktGruppe = { abschnitt: effAbschnitt, zeilen: [] }
        gruppen.push(aktGruppe)
      }
      aktGruppe.zeilen.push(meta)
    }
    return gruppen
  }

  const zahllast = ergebnis ? berechneZahllast() : null
  const gruppen = ergebnis && !ergebnis.ist_kleinunternehmer ? renderKZTabelle() : []
  const hatManuellFelder = KZ_META.some(([,nr,,, auto]) => !auto)

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">UStVA – Anzeigehilfe</h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        Berechnet Kennziffern aus deinen Journalbuchungen (Ist-Versteuerung).
        Trage die Beträge in{' '}
        <button type="button" onClick={() => openUrl('https://www.elster.de')}
          className="text-blue-600 dark:text-blue-400 hover:underline">ELSTER</button>{' '}
        ein oder gib sie an deinen Steuerberater.
      </p>

      {/* Zeitraum-Auswahl */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 mb-6">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Typ</label>
            <div className="flex rounded-lg border border-slate-200 dark:border-slate-600 overflow-hidden">
              {(['quartal', 'monat'] as const).map(m => (
                <button key={m} type="button" onClick={() => setModus(m)}
                  className={`px-3 py-1.5 text-sm font-medium transition-colors ${modus === m ? 'bg-blue-600 text-white' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'}`}>
                  {m === 'quartal' ? 'Vierteljährlich' : 'Monatlich'}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Jahr</label>
            <select value={jahr} onChange={e => setJahr(Number(e.target.value))}
              className="border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100">
              {jahre.map(j => <option key={j} value={j}>{j}</option>)}
            </select>
          </div>
          {modus === 'quartal' ? (
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Quartal</label>
              <select value={quartal} onChange={e => setQuartal(Number(e.target.value))}
                className="border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100">
                {[1,2,3,4].map(q => <option key={q} value={q}>Q{q}</option>)}
              </select>
            </div>
          ) : (
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Monat</label>
              <select value={monat} onChange={e => setMonat(Number(e.target.value))}
                className="border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100">
                {MONATE.slice(1).map((m, i) => <option key={i+1} value={i+1}>{m}</option>)}
              </select>
            </div>
          )}
          <button onClick={() => { setManuell({}); refetch() }} disabled={isLoading}
            className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors">
            {isLoading ? 'Berechne…' : 'Berechnen'}
          </button>
        </div>
        {rhythmus !== modus && (
          <p className="text-xs text-amber-600 dark:text-amber-400 mt-2">
            Hinweis: Einstellung ist <strong>{rhythmus === 'quartal' ? 'Vierteljährlich' : 'Monatlich'}</strong>.
          </p>
        )}
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl p-4 mb-6 text-sm text-red-700 dark:text-red-300">
          {(error as Error).message}
        </div>
      )}

      {ergebnis && (
        <>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-slate-700 dark:text-slate-200">{zeitraumLabel(zeitraum)}</h2>
            <div className="flex items-center gap-2">
              <button onClick={handlePdf} disabled={pdfLaedt}
                className="px-3 py-1.5 text-xs font-medium border border-slate-200 dark:border-slate-600 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors">
                {pdfLaedt ? '…' : '📄 PDF'}
              </button>
              {pdfExportiert && <span className="text-xs text-emerald-600 dark:text-emerald-400">✓ geöffnet</span>}
              {pdfFehler && <span className="text-xs text-red-600 dark:text-red-400">{pdfFehler}</span>}
              <button type="button" onClick={() => speichernMut.mutate(alleKZ() as any)}
                disabled={speichernMut.isPending || ergebnis.ist_kleinunternehmer}
                className="px-3 py-1.5 text-xs font-medium bg-slate-800 dark:bg-slate-600 text-white rounded-lg hover:bg-slate-700 disabled:opacity-40 transition-colors">
                {gespeichertMeldung ? '✓ Gespeichert' : 'Speichern'}
              </button>
            </div>
          </div>

          {ergebnis.hinweis && (
            <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-xl p-4 mb-4 text-sm text-amber-800 dark:text-amber-200">
              {ergebnis.hinweis}
            </div>
          )}

          {!ergebnis.ist_kleinunternehmer && (
            <>
              {/* Auto-berechnete Felder – nur mit Wert */}
              {gruppen.length === 0 ? (
                <p className="text-sm text-slate-400 dark:text-slate-500 mb-4">Keine Buchungen im Zeitraum.</p>
              ) : gruppen.map(({ abschnitt, zeilen }) => (
                <Abschnitt key={abschnitt} titel={abschnitt}>
                  {zeilen.map(([, nr, bezeichnung, istSteuer]) => (
                    <KZZeile key={nr} kz={nr} label={bezeichnung}
                      wert={kzWert(nr)} istSteuer={istSteuer} />
                  ))}
                </Abschnitt>
              ))}

              {/* Manuelle Felder – immer sichtbar wenn EU-Handel möglich */}
              <details className="mb-4">
                <summary className="cursor-pointer text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 mb-2 select-none">
                  Manuelle Felder (EU-Lieferungen, Ausfuhr) ▸
                </summary>
                <div className="mt-2 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 divide-y divide-slate-100 dark:divide-slate-700">
                  {KZ_META.filter(([,,, , auto]) => !auto).map(([, nr, bezeichnung]) => (
                    <div key={nr} className="flex items-center gap-3 px-4 py-2">
                      <span className="shrink-0 inline-flex items-center justify-center w-9 h-6 rounded text-xs font-bold text-white bg-slate-500 dark:bg-slate-600">
                        {nr}
                      </span>
                      <span className="flex-1 text-sm text-slate-600 dark:text-slate-300 text-xs">{bezeichnung}</span>
                      <input
                        type="number" step="0.01" min="0"
                        value={manuell[nr] ?? ''}
                        onChange={e => setManuell(m => ({ ...m, [nr]: e.target.value }))}
                        placeholder="0,00"
                        className="w-28 text-right text-sm border border-slate-200 dark:border-slate-600 rounded px-2 py-1 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100"
                      />
                    </div>
                  ))}
                </div>
              </details>

              {/* Zahllast */}
              {zahllast !== null && (
                <Abschnitt titel="H. Vorauszahlung / Überschuss">
                  <KZZeile kz="—"
                    label={parseFloat(zahllast) < 0 ? 'Verbleibender Überschuss (Erstattung)' : 'Umsatzsteuer-Vorauszahlung'}
                    wert={zahllast} bold />
                </Abschnitt>
              )}

              <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">
                Grundlage: Journalbuchungen {ergebnis.von} bis {ergebnis.bis} (Ist-Versteuerung).
                Felder mit grauem KZ-Chip sind manuell einzutragen.
              </p>
            </>
          )}
        </>
      )}

      {/* Historie */}
      {historie && historie.length > 0 && (
        <div className="mt-8">
          <h2 className="text-sm font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide mb-3">
            Gespeicherte Voranmeldungen
          </h2>
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 divide-y divide-slate-100 dark:divide-slate-700 overflow-hidden">
            {historie.map(e => (
              <div key={e.zeitraum} className="flex items-center justify-between px-4 py-3">
                <div>
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-200">{zeitraumLabel(e.zeitraum)}</span>
                  <span className="text-xs text-slate-400 dark:text-slate-500 ml-2">{e.zeitraum_typ}</span>
                </div>
                <span className={`text-sm font-medium tabular-nums ${e.zahllast < 0 ? 'text-green-600 dark:text-green-400' : 'text-slate-700 dark:text-slate-200'}`}>
                  {euroFmt(e.zahllast)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
