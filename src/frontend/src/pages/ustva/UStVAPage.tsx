import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  berechneUStVA, speichereUStVA, getUStVAHistorie, getUStVAPdfUrl,
  getUnternehmen, openUrl,
  type UStVAErgebnis,
} from '../../api/client'

const MONATE = [
  '', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
]

function aktuellesQuartal(): string {
  const now = new Date()
  const q = Math.ceil((now.getMonth() + 1) / 3)
  return `${now.getFullYear()}-Q${q}`
}

function zeitraumLabel(zeitraum: string): string {
  if (zeitraum.includes('-Q')) {
    const [jahr, q] = zeitraum.split('-Q')
    return `Q${q}/${jahr}`
  }
  try {
    const [jahr, mon] = zeitraum.split('-')
    return `${MONATE[parseInt(mon)]} ${jahr}`
  } catch {
    return zeitraum
  }
}

function euroFmt(v: string | number): string {
  const n = typeof v === 'string' ? parseFloat(v) : v
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n)
}

function KZZeile({
  kz, label, wert, sub = false, bold = false,
}: { kz: string; label: string; wert: string; sub?: boolean; bold?: boolean }) {
  const n = parseFloat(wert)
  const negativ = n < 0
  return (
    <div className={`flex items-center gap-3 py-2 ${sub ? 'pl-6' : ''} ${bold ? 'border-t border-slate-200 dark:border-slate-600 mt-1 pt-3' : ''}`}>
      <span className={`shrink-0 inline-flex items-center justify-center w-9 h-6 rounded text-xs font-bold text-white ${bold ? 'bg-slate-700 dark:bg-slate-500' : 'bg-blue-600 dark:bg-blue-700'}`}>
        {kz}
      </span>
      <span className={`flex-1 text-sm ${bold ? 'font-semibold text-slate-800 dark:text-slate-100' : 'text-slate-700 dark:text-slate-200'} ${sub ? 'text-slate-500 dark:text-slate-400' : ''}`}>
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

  const zeitraum = modus === 'quartal'
    ? `${jahr}-Q${quartal}`
    : `${jahr}-${String(monat).padStart(2, '0')}`

  const { data: unt } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen })
  const { data: historie } = useQuery({ queryKey: ['ustva-historie'], queryFn: getUStVAHistorie })

  const {
    data: ergebnis, isLoading, error, refetch,
  } = useQuery({
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

  const jahre = Array.from({ length: 5 }, (_, i) => now.getFullYear() - i)

  const rhythmus = (unt as any)?.voranmeldungsrhythmus ?? 'quartal'

  async function handlePdf() {
    setPdfLaedt(true)
    setPdfFehler(null)
    setPdfExportiert(false)
    try {
      await openUrl(getUStVAPdfUrl(zeitraum))
      setPdfExportiert(true)
    } catch (e: any) {
      setPdfFehler(e?.message ?? 'PDF-Export fehlgeschlagen')
    } finally {
      setPdfLaedt(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">
        UStVA – Anzeigehilfe
      </h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        Berechnet Kennziffern aus deinen Journalbuchungen (Ist-Versteuerung).
        Trage die Beträge manuell in{' '}
        <button
          type="button"
          onClick={() => openUrl('https://www.elster.de')}
          className="text-blue-600 dark:text-blue-400 hover:underline"
        >
          ELSTER
        </button>{' '}
        ein oder gib sie an deinen Steuerberater.
      </p>

      {/* Zeitraum-Auswahl */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 mb-6">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Typ</label>
            <div className="flex rounded-lg border border-slate-200 dark:border-slate-600 overflow-hidden">
              {(['quartal', 'monat'] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setModus(m)}
                  className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                    modus === m
                      ? 'bg-blue-600 text-white'
                      : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
                  }`}
                >
                  {m === 'quartal' ? 'Vierteljährlich' : 'Monatlich'}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Jahr</label>
            <select
              value={jahr}
              onChange={e => setJahr(Number(e.target.value))}
              className="border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100"
            >
              {jahre.map(j => <option key={j} value={j}>{j}</option>)}
            </select>
          </div>

          {modus === 'quartal' ? (
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Quartal</label>
              <select
                value={quartal}
                onChange={e => setQuartal(Number(e.target.value))}
                className="border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100"
              >
                {[1, 2, 3, 4].map(q => <option key={q} value={q}>Q{q}</option>)}
              </select>
            </div>
          ) : (
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Monat</label>
              <select
                value={monat}
                onChange={e => setMonat(Number(e.target.value))}
                className="border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100"
              >
                {MONATE.slice(1).map((m, i) => <option key={i + 1} value={i + 1}>{m}</option>)}
              </select>
            </div>
          )}

          <button
            onClick={() => refetch()}
            disabled={isLoading}
            className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {isLoading ? 'Berechne…' : 'Berechnen'}
          </button>
        </div>

        {rhythmus !== modus && (
          <p className="text-xs text-amber-600 dark:text-amber-400 mt-2">
            Hinweis: In den Einstellungen ist dein Voranmeldungsrhythmus auf{' '}
            <strong>{rhythmus === 'quartal' ? 'Vierteljährlich' : 'Monatlich'}</strong> eingestellt.
          </p>
        )}
      </div>

      {/* Fehler */}
      {error && (
        <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl p-4 mb-6 text-sm text-red-700 dark:text-red-300">
          {(error as Error).message}
        </div>
      )}

      {/* Ergebnis */}
      {ergebnis && (
        <>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-slate-700 dark:text-slate-200">
              {zeitraumLabel(zeitraum)}
            </h2>
            <div className="flex gap-2">
              <button
                onClick={handlePdf}
                disabled={pdfLaedt}
                className="px-3 py-1.5 text-xs font-medium border border-slate-200 dark:border-slate-600 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors"
              >
                {pdfLaedt ? '…' : '📄 PDF'}
              </button>
              {pdfExportiert && <span className="text-xs text-emerald-600 dark:text-emerald-400">✓ geöffnet</span>}
              {pdfFehler && <span className="text-xs text-red-600 dark:text-red-400">{pdfFehler}</span>}
              <button
                type="button"
                onClick={() => speichernMut.mutate({
                  zeitraum,
                  kz_81: ergebnis.kz_81,
                  kz_83: ergebnis.kz_83,
                  kz_86: ergebnis.kz_86,
                  kz_88: ergebnis.kz_88,
                  kz_66: ergebnis.kz_66,
                  kz_41: ergebnis.kz_41,
                  zahllast: ergebnis.zahllast,
                })}
                disabled={speichernMut.isPending || ergebnis.ist_kleinunternehmer}
                className="px-3 py-1.5 text-xs font-medium bg-slate-800 dark:bg-slate-600 text-white rounded-lg hover:bg-slate-700 disabled:opacity-40 transition-colors"
              >
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
              <Abschnitt titel="A. Steuerpflichtige Ausgangsumsätze">
                <KZZeile kz="81" label="Umsätze zum Steuersatz 19 % – Bemessungsgrundlage" wert={ergebnis.kz_81} />
                <KZZeile kz="83" label="Umsatzsteuer 19 %" wert={ergebnis.kz_83} sub />
                <KZZeile kz="86" label="Umsätze zum Steuersatz 7 % – Bemessungsgrundlage" wert={ergebnis.kz_86} />
                <KZZeile kz="88" label="Umsatzsteuer 7 %" wert={ergebnis.kz_88} sub />
              </Abschnitt>

              <Abschnitt titel="F. Abziehbare Vorsteuerbeträge">
                <KZZeile kz="66" label="Vorsteuer aus Eingangsrechnungen (§ 15 Abs. 1 Nr. 1 UStG)" wert={ergebnis.kz_66} />
              </Abschnitt>

              <Abschnitt titel="H. Vorauszahlung / Überschuss">
                <KZZeile
                  kz="—"
                  label={parseFloat(ergebnis.zahllast) < 0 ? 'Verbleibender Überschuss (Erstattung)' : 'Umsatzsteuer-Vorauszahlung'}
                  wert={ergebnis.zahllast}
                  bold
                />
              </Abschnitt>

              <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">
                Grundlage: Journalbuchungen {ergebnis.von} bis {ergebnis.bis} (Ist-Versteuerung / Zahlungsdatum).
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
            {historie.map((e) => (
              <div key={e.zeitraum} className="flex items-center justify-between px-4 py-3">
                <div>
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                    {zeitraumLabel(e.zeitraum)}
                  </span>
                  <span className="text-xs text-slate-400 dark:text-slate-500 ml-2">
                    {e.zeitraum_typ}
                  </span>
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
