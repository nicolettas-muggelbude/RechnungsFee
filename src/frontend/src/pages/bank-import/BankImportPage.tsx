import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getKonten,
  getBankTemplates,
  getBankTransaktionen,
  vorschauBankImport,
  importiereBankTransaktionen,
  bucheTransaktion,
  abgleichTransaktion,
  autoBuchen,
  ueberzahlungAnerkennen,
  type Konto,
  type BankTemplate,
  type BankVorschauResponse,
  type BankTransaktion,
  type BankAbgleichVorschlag,
} from '../../api/client'
import { BuchungForm } from '../journal/BuchungForm'

// ---------------------------------------------------------------------------
// Hilfsfunktionen
// ---------------------------------------------------------------------------

function euroFmt(v: string | number): string {
  const n = typeof v === 'string' ? parseFloat(v) : v
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n)
}

function datumFmt(iso: string): string {
  return new Date(iso).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function ibanFmt(iban: string): string {
  return iban.replace(/(.{4})/g, '$1 ').trim()
}


// ---------------------------------------------------------------------------
// Import-Dialog (3 Schritte)
// ---------------------------------------------------------------------------

type Schritt = 1 | 2 | 3

type AnalyseStatus =
  | { art: 'idle' }
  | { art: 'laden' }
  | { art: 'iban_match'; iban: string; kontoId: number; kontoName: string }
  | { art: 'iban_kein_konto'; iban: string }
  | { art: 'kein_iban' }

interface ImportDialogProps {
  konten: Konto[]
  templates: BankTemplate[]
  onClose: () => void
  onErfolg: (kontoId: number) => void
}

function ImportDialog({ konten, templates, onClose, onErfolg }: ImportDialogProps) {
  const [schritt, setSchritt] = useState<Schritt>(1)
  const [datei, setDatei] = useState<File | null>(null)
  const [templateId, setTemplateId] = useState<string>('')
  const [manuellKontoId, setManuellKontoId] = useState<number>(konten[0]?.id ?? 0)
  const [analyseStatus, setAnalyseStatus] = useState<AnalyseStatus>({ art: 'idle' })
  const [vorschau, setVorschau] = useState<BankVorschauResponse | null>(null)
  const [auswahl, setAuswahl] = useState<Set<string>>(new Set())
  const [fehler, setFehler] = useState<string | null>(null)

  const geschaeftskonten = konten.filter(k => k.kontotyp !== 'privat')

  // Welches kontoId wird letztendlich für den Import verwendet
  const aktuellesKontoId: number | null =
    analyseStatus.art === 'iban_match' ? analyseStatus.kontoId :
    analyseStatus.art === 'kein_iban' ? manuellKontoId :
    null

  async function analysiere() {
    if (!datei) return
    setFehler(null)
    setAnalyseStatus({ art: 'laden' })
    try {
      const result = await vorschauBankImport(datei, undefined, templateId || undefined)
      if (result.erkanntes_template) setTemplateId(result.erkanntes_template)
      setVorschau(result)
      setAuswahl(new Set(result.transaktionen.filter(t => !t.ist_duplikat).map(t => t.dedupe_hash)))

      if (result.konto_iban && result.erkanntes_konto_id) {
        const konto = geschaeftskonten.find(k => k.id === result.erkanntes_konto_id)
        setAnalyseStatus({
          art: 'iban_match',
          iban: result.konto_iban,
          kontoId: result.erkanntes_konto_id,
          kontoName: konto?.name ?? `Konto #${result.erkanntes_konto_id}`,
        })
      } else if (result.konto_iban && !result.erkanntes_konto_id) {
        setAnalyseStatus({ art: 'iban_kein_konto', iban: result.konto_iban })
      } else {
        setAnalyseStatus({ art: 'kein_iban' })
      }
    } catch (e: unknown) {
      setFehler((e as Error).message)
      setAnalyseStatus({ art: 'idle' })
    }
  }

  // Bei manueller Kontoauswahl: Vorschau mit konto_id neu laden (Duplikat-Check)
  async function ladeVorschauMitKonto(kontoId: number) {
    if (!datei) return
    setFehler(null)
    try {
      const result = await vorschauBankImport(datei, kontoId, templateId || undefined)
      setVorschau(result)
      setAuswahl(new Set(result.transaktionen.filter(t => !t.ist_duplikat).map(t => t.dedupe_hash)))
    } catch (e: unknown) {
      setFehler((e as Error).message)
    }
  }

  const txAuswahl = vorschau?.transaktionen.filter(t => auswahl.has(t.dedupe_hash)) ?? []
  const txDuplikate = vorschau?.transaktionen.filter(t => t.ist_duplikat).length ?? 0

  const autoBuchenMut = useMutation({
    mutationFn: (importId?: number) => autoBuchen(aktuellesKontoId!, importId),
  })

  const importMut = useMutation({
    mutationFn: () =>
      importiereBankTransaktionen({
        konto_id: aktuellesKontoId!,
        template_id: templateId,
        dateiname: datei?.name ?? 'import.csv',
        transaktionen: txAuswahl,
      }),
    onSuccess: (res) => {
      setSchritt(3)
      autoBuchenMut.mutate(res.import_id)
    },
    onError: (e: Error) => setFehler(e.message),
  })

  const toggleAuswahl = (hash: string) => {
    setAuswahl(prev => {
      const next = new Set(prev)
      if (next.has(hash)) next.delete(hash)
      else next.add(hash)
      return next
    })
  }

  const navigate = useNavigate()

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">CSV-Import</h2>
            <div className="flex gap-1">
              {([1, 2, 3] as Schritt[]).map(s => (
                <div key={s} className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-colors ${
                  schritt > s ? 'bg-green-500 border-green-500 text-white' :
                  schritt === s ? 'border-blue-500 text-blue-600 dark:text-blue-400' :
                  'border-slate-200 dark:border-slate-600 text-slate-400'
                }`}>{schritt > s ? '✓' : s}</div>
              ))}
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xl leading-none">×</button>
        </div>

        {/* Inhalt */}
        <div className="flex-1 overflow-y-auto px-6 py-5">

          {fehler && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300">
              {fehler}
            </div>
          )}

          {/* ─── Schritt 1: Datei + Analyse ─── */}
          {schritt === 1 && (
            <div className="space-y-4">

              {/* Datei-Upload */}
              <label
                htmlFor="bank-import-datei"
                className={`block border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                  datei
                    ? 'border-blue-400 bg-blue-50/50 dark:bg-blue-900/10'
                    : 'border-slate-300 dark:border-slate-600 hover:border-blue-400'
                }`}
              >
                {datei ? (
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-slate-700 dark:text-slate-200">📄 {datei.name}</p>
                    <p className="text-xs text-slate-400 dark:text-slate-500">Klicken oder Datei ablegen zum Wechseln</p>
                  </div>
                ) : (
                  <p className="text-sm text-slate-500 dark:text-slate-400">CSV-, XML- oder ZIP-Datei hier ablegen oder klicken</p>
                )}
                <input
                  id="bank-import-datei"
                  type="file" accept=".csv,.txt,.xml,.zip" className="hidden"
                  onChange={e => {
                    setDatei(e.target.files?.[0] ?? null)
                    setAnalyseStatus({ art: 'idle' })
                    setVorschau(null)
                    setFehler(null)
                  }}
                />
              </label>

              {/* Template (immer sichtbar, klein) */}
              <div>
                <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Template</label>
                <select
                  value={templateId}
                  onChange={e => setTemplateId(e.target.value)}
                  className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100"
                >
                  <option value="">– automatisch erkennen –</option>
                  {templates.map(t => (
                    <option key={t.id} value={t.id}>{t.name} ({t.bank})</option>
                  ))}
                </select>
              </div>

              {/* Analyse-Ergebnis */}
              {analyseStatus.art === 'iban_match' && (
                <div className="flex items-start gap-3 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl">
                  <span className="text-green-500 text-lg leading-none mt-0.5">✓</span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-green-800 dark:text-green-200">
                      Konto erkannt: {analyseStatus.kontoName}
                    </p>
                    <p className="text-xs text-green-600 dark:text-green-400 mt-0.5">
                      {ibanFmt(analyseStatus.iban)} · {vorschau?.transaktionen.length} Transaktionen
                      {txDuplikate > 0 && ` · ${txDuplikate} bereits importiert`}
                    </p>
                  </div>
                </div>
              )}

              {analyseStatus.art === 'iban_kein_konto' && (
                <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl space-y-3">
                  <div className="flex items-start gap-2">
                    <span className="text-amber-500 text-lg leading-none mt-0.5">⚠</span>
                    <div>
                      <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
                        Konto nicht konfiguriert
                      </p>
                      <p className="text-xs text-amber-700 dark:text-amber-300 mt-0.5">
                        <span className="font-mono">{ibanFmt(analyseStatus.iban)}</span> ist in RechnungsFee nicht konfiguriert.
                        Möchtest du das Konto anlegen?
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => { navigate(`/konten?iban=${encodeURIComponent(analyseStatus.iban)}`); onClose() }}
                      className="flex-1 px-3 py-2 text-sm font-medium bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors"
                    >
                      Ja, Konto anlegen
                    </button>
                    <button
                      onClick={onClose}
                      className="flex-1 px-3 py-2 text-sm border border-amber-300 dark:border-amber-700 text-amber-700 dark:text-amber-300 rounded-lg hover:bg-amber-50 dark:hover:bg-amber-900/30 transition-colors"
                    >
                      Abbrechen
                    </button>
                  </div>
                </div>
              )}

              {analyseStatus.art === 'kein_iban' && (
                <div className="space-y-2">
                  <div className="flex items-start gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl">
                    <span className="text-blue-500 text-base leading-none mt-0.5">ℹ</span>
                    <p className="text-xs text-blue-700 dark:text-blue-300">
                      Kein Konto in der CSV erkannt. Bitte manuell auswählen.
                    </p>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Konto</label>
                    <select
                      value={manuellKontoId}
                      onChange={e => {
                        const id = Number(e.target.value)
                        setManuellKontoId(id)
                        ladeVorschauMitKonto(id)
                      }}
                      className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100"
                    >
                      {geschaeftskonten.map(k => (
                        <option key={k.id} value={k.id}>
                          {k.name} ({k.anbieter}){k.kontotyp === 'mischkonto' ? ' – Mischkonto' : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                  {vorschau && (
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {vorschau.transaktionen.length} Transaktionen
                      {txDuplikate > 0 && ` · ${txDuplikate} bereits importiert`}
                    </p>
                  )}
                </div>
              )}

            </div>
          )}

          {/* ─── Schritt 2: Vorschau ─── */}
          {schritt === 2 && vorschau && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Template: <span className="font-medium text-slate-700 dark:text-slate-200">{vorschau.template_name}</span>
                  {' · '}{txAuswahl.length} von {vorschau.transaktionen.length} ausgewählt
                  {txDuplikate > 0 && <span className="text-amber-600 dark:text-amber-400"> · {txDuplikate} Duplikat{txDuplikate > 1 ? 'e' : ''}</span>}
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setAuswahl(new Set(vorschau.transaktionen.filter(t => !t.ist_duplikat).map(t => t.dedupe_hash)))}
                    className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                  >Alle</button>
                  <span className="text-slate-300 dark:text-slate-600">|</span>
                  <button onClick={() => setAuswahl(new Set())} className="text-xs text-blue-600 dark:text-blue-400 hover:underline">Keine</button>
                </div>
              </div>

              <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-slate-50 dark:bg-slate-700/50 text-slate-500 dark:text-slate-400">
                      <th className="px-3 py-2 text-left w-8">
                        <input type="checkbox" className="h-3 w-3"
                          checked={auswahl.size === vorschau.transaktionen.filter(t => !t.ist_duplikat).length && auswahl.size > 0}
                          onChange={e => e.target.checked
                            ? setAuswahl(new Set(vorschau.transaktionen.filter(t => !t.ist_duplikat).map(t => t.dedupe_hash)))
                            : setAuswahl(new Set())} />
                      </th>
                      <th className="px-3 py-2 text-left">Datum</th>
                      <th className="px-3 py-2 text-right">Betrag</th>
                      <th className="px-3 py-2 text-left">Partner</th>
                      <th className="px-3 py-2 text-left">Verwendungszweck</th>
                    </tr>
                  </thead>
                  <tbody>
                    {vorschau.transaktionen.map(tx => (
                      <tr key={tx.dedupe_hash}
                        className={`border-t border-slate-100 dark:border-slate-700/50 ${
                          tx.ist_duplikat ? 'opacity-40' : 'hover:bg-slate-50 dark:hover:bg-slate-700/30'
                        }`}
                      >
                        <td className="px-3 py-1.5">
                          {tx.ist_duplikat
                            ? <span className="text-amber-500">↩</span>
                            : <input type="checkbox" className="h-3 w-3"
                                checked={auswahl.has(tx.dedupe_hash)}
                                onChange={() => toggleAuswahl(tx.dedupe_hash)} />
                          }
                        </td>
                        <td className="px-3 py-1.5 whitespace-nowrap text-slate-600 dark:text-slate-300">{datumFmt(tx.datum)}</td>
                        <td className={`px-3 py-1.5 text-right font-mono font-medium whitespace-nowrap ${
                          parseFloat(tx.betrag) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                        }`}>{euroFmt(tx.betrag)}</td>
                        <td className="px-3 py-1.5 text-slate-700 dark:text-slate-200 max-w-[180px] truncate">{tx.partner_name ?? '–'}</td>
                        <td className="px-3 py-1.5 text-slate-500 dark:text-slate-400 max-w-[200px] truncate">{tx.verwendungszweck ?? '–'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ─── Schritt 3: Ergebnis ─── */}
          {schritt === 3 && importMut.data && (
            <div className="space-y-4 py-2">
              <div className="text-center space-y-2">
                <div className="text-4xl">{autoBuchenMut.isPending ? '⏳' : '✅'}</div>
                <h3 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
                  {autoBuchenMut.isPending ? 'Gleiche ab…' : 'Import abgeschlossen'}
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {importMut.data.erfolg} importiert · {importMut.data.duplikate} Duplikate
                  {importMut.data.fehler > 0 && ` · ${importMut.data.fehler} Fehler`}
                </p>
              </div>

              {autoBuchenMut.isPending && (
                <p className="text-sm text-slate-400 dark:text-slate-500 text-center animate-pulse">
                  Transaktionen werden automatisch abgeglichen…
                </p>
              )}

              {autoBuchenMut.data && (
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-4 text-center">
                    <div className="text-2xl font-bold text-green-600 dark:text-green-400">{autoBuchenMut.data.gebucht}</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">Automatisch gebucht</div>
                  </div>
                  <div className={`rounded-xl p-4 text-center border ${
                    autoBuchenMut.data.offen > 0
                      ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800'
                      : 'bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-700'
                  }`}>
                    <div className={`text-2xl font-bold ${autoBuchenMut.data.offen > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-400'}`}>
                      {autoBuchenMut.data.offen}
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">Zuordnung nötig</div>
                  </div>
                  {autoBuchenMut.data.forderungen > 0 && (
                    <div className="col-span-2 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-xl p-3 text-center">
                      <p className="text-xs text-orange-700 dark:text-orange-300">
                        {autoBuchenMut.data.forderungen} Lieferantenguthaben angelegt – im Dashboard sichtbar
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 dark:border-slate-700">

          {schritt === 1 && (
            <>
              <button onClick={onClose} className="text-sm text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200">
                Abbrechen
              </button>
              <div className="flex gap-2">
                {analyseStatus.art === 'idle' || analyseStatus.art === 'laden' ? (
                  <button
                    disabled={!datei || analyseStatus.art === 'laden'}
                    onClick={analysiere}
                    className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-40"
                  >
                    {analyseStatus.art === 'laden' ? 'Analysiere…' : 'Analysieren'}
                  </button>
                ) : analyseStatus.art === 'iban_match' || analyseStatus.art === 'kein_iban' ? (
                  <button
                    disabled={analyseStatus.art === 'kein_iban' && !manuellKontoId}
                    onClick={() => setSchritt(2)}
                    className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-40"
                  >
                    Zur Vorschau →
                  </button>
                ) : null}
              </div>
            </>
          )}

          {schritt === 2 && (
            <>
              <button onClick={() => setSchritt(1)} className="text-sm text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200">
                ← Zurück
              </button>
              <button
                disabled={txAuswahl.length === 0 || importMut.isPending}
                onClick={() => importMut.mutate()}
                className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-40"
              >
                {importMut.isPending ? 'Importiere…' : `${txAuswahl.length} Transaktionen importieren`}
              </button>
            </>
          )}

          {schritt === 3 && (
            <button
              onClick={() => onErfolg(aktuellesKontoId!)}
              className="ml-auto px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              {autoBuchenMut.isPending ? 'Zur Transaktionsliste (läuft noch…)' : 'Zur Transaktionsliste'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Transaktionsliste
// ---------------------------------------------------------------------------

function KlassifizierungBadge({ tx }: { tx: BankTransaktion }) {
  if (tx.ist_privatentnahme) return <span className="text-xs bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 rounded px-1.5 py-0.5">Privatentnahme</span>
  if (tx.ist_einlage)        return <span className="text-xs bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 rounded px-1.5 py-0.5">Einlage</span>
  if (!tx.ist_geschaeftlich) return <span className="text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 rounded px-1.5 py-0.5">Privat</span>
  return <span className="text-xs bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 rounded px-1.5 py-0.5">Geschäftlich</span>
}

// ---------------------------------------------------------------------------
// Abgleich-Dialog
// ---------------------------------------------------------------------------

interface AbgleichDialogProps {
  tx: BankTransaktion
  vorschlaege: BankAbgleichVorschlag[]
  onZuordnen: (rechnungId: number) => void
  onOhneRechnung: () => void
  onClose: () => void
  buchePending: boolean
}

function AbgleichDialog({ tx, vorschlaege, onZuordnen, onOhneRechnung, onClose, buchePending }: AbgleichDialogProps) {
  const hatScore3 = vorschlaege.some(v => v.score === 3)
  const guteMatches = vorschlaege.filter(v => hatScore3 ? v.score === 3 : v.score >= 2)
  const schwacheMatches = hatScore3 ? [] : vorschlaege.filter(v => v.score === 1)

  function Chip({ label, aktiv }: { label: string; aktiv: boolean }) {
    return (
      <span className={`text-[10px] rounded px-1.5 py-0.5 font-medium ${
        aktiv
          ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300'
          : 'bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-500 line-through'
      }`}>{label}</span>
    )
  }

  function VorschlagKarte({ v }: { v: BankAbgleichVorschlag }) {
    return (
      <div className="border border-slate-200 dark:border-slate-600 rounded-xl p-3 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{v.rechnungsnummer}</p>
            {v.externe_belegnr && (
              <p className="text-xs font-mono text-slate-400 dark:text-slate-500">Lief.-Nr. {v.externe_belegnr}</p>
            )}
            <p className="text-xs text-slate-500 dark:text-slate-400">{v.partner} · {datumFmt(v.datum)}</p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-sm font-mono font-bold text-slate-700 dark:text-slate-200">{euroFmt(v.restbetrag)} offen</p>
            <p className="text-[10px] text-slate-400 dark:text-slate-500">von {euroFmt(v.brutto_gesamt)}</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <Chip label="Betrag" aktiv={v.betrag_match} />
          <Chip label="Rechnungsnr." aktiv={v.nummer_match} />
          <Chip label="Name" aktiv={v.name_match} />
        </div>
        <button
          onClick={() => onZuordnen(v.rechnung_id)}
          disabled={buchePending}
          className="w-full mt-1 px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-40 font-medium transition-colors"
        >
          {buchePending ? 'Buche…' : 'Als bezahlt markieren'}
        </button>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <div>
            <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">Zahlungsabgleich</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {euroFmt(tx.betrag)} · {tx.partner_name ?? '–'}
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xl leading-none">×</button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {guteMatches.length === 1 && schwacheMatches.length === 0 && (
            <p className="text-xs text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 rounded-lg px-3 py-2">
              1 eindeutiger Treffer gefunden – bitte bestätigen.
            </p>
          )}
          {guteMatches.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Treffer (≥ 2 Kriterien)</p>
              {guteMatches.map(v => <VorschlagKarte key={v.rechnung_id} v={v} />)}
            </div>
          )}
          {schwacheMatches.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Mögliche Treffer (1 Kriterium)</p>
              {schwacheMatches.map(v => <VorschlagKarte key={v.rechnung_id} v={v} />)}
            </div>
          )}
          {vorschlaege.length === 0 && (
            <p className="text-sm text-slate-500 dark:text-slate-400 text-center py-4">Keine passenden offenen Rechnungen gefunden.</p>
          )}
        </div>
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700">
          <button
            onClick={onOhneRechnung}
            disabled={buchePending}
            className="w-full py-2 text-sm text-slate-600 dark:text-slate-300 border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-40 transition-colors"
          >
            Ohne Rechnungsbezug buchen
          </button>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Überzahlungs-Dialog (Ausgangsrechnung)
// ---------------------------------------------------------------------------

interface UeberzahlungDialogProps {
  rechnungId: number
  rechnungsnummer: string
  partner: string
  ueberzahlung: number
  onGutschrift: () => void
  onSpaeter: () => void
  onKeinHandlungsbedarf: () => void
}

function UeberzahlungDialog({ rechnungsnummer, partner, ueberzahlung, onGutschrift, onSpaeter, onKeinHandlungsbedarf }: UeberzahlungDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md">
        <div className="px-6 py-5 space-y-4">
          <div className="flex items-start gap-3">
            <span className="text-2xl leading-none mt-0.5">⚠️</span>
            <div>
              <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">Überzahlung erkannt</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                <span className="font-medium text-slate-700 dark:text-slate-200">{partner}</span> hat{' '}
                <span className="font-semibold text-amber-600 dark:text-amber-400">
                  {new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(ueberzahlung)}
                </span>{' '}
                mehr gezahlt als Rechnung {rechnungsnummer} ausweist.
              </p>
            </div>
          </div>
          <div className="space-y-2 pt-1">
            <button onClick={onGutschrift} className="w-full px-4 py-2.5 text-sm font-medium bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors text-left">
              Gutschrift erstellen
              <span className="block text-xs font-normal opacity-80 mt-0.5">Öffnet die Rechnung – Gutschrift-Button ist dort verfügbar</span>
            </button>
            <button onClick={onSpaeter} className="w-full px-4 py-2.5 text-sm font-medium border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors text-left">
              Später erinnern
              <span className="block text-xs font-normal text-slate-400 dark:text-slate-500 mt-0.5">Erscheint als offene Aufgabe im Dashboard</span>
            </button>
            <button onClick={onKeinHandlungsbedarf} className="w-full px-4 py-2.5 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors text-left">
              Kein Handlungsbedarf
              <span className="block text-xs text-slate-400 dark:text-slate-500 mt-0.5">Z.B. Trinkgeld – nicht mehr anzeigen</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Buchungs-Zelle
// ---------------------------------------------------------------------------

interface BuchungsCelleProps {
  tx: BankTransaktion
  ladendeTxId: number | null
  buchePending: boolean
  onBuchen: (tx: BankTransaktion) => void
}

function BuchungsCelle({ tx, ladendeTxId, buchePending, onBuchen }: BuchungsCelleProps) {
  if (tx.ist_rueckerstattung) {
    return <span className="text-xs bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 rounded px-1.5 py-0.5">Rückerstattung</span>
  }

  if (tx.journal_id) {
    const info = tx.rechnung_info
    if (info) {
      const gleichBetrag = Math.abs(parseFloat(info.gebuchter_betrag) - parseFloat(info.brutto_gesamt)) < 0.02
      return (
        <div className="space-y-0.5">
          <div className="flex items-center gap-1.5">
            <span className="text-xs bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 rounded px-1.5 py-0.5">Bezahlt</span>
            <span className="text-xs font-medium text-slate-700 dark:text-slate-200">{info.rechnungsnummer}</span>
          </div>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate max-w-[220px]">{info.partner}</p>
          <p className="text-[10px] text-slate-400 dark:text-slate-500">
            Rechnung: {euroFmt(info.brutto_gesamt)}
            {!gleichBetrag && <span className="text-amber-600 dark:text-amber-400"> · gebucht: {euroFmt(info.gebuchter_betrag)}</span>}
          </p>
        </div>
      )
    }
    return <span className="text-xs bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 rounded px-1.5 py-0.5">Gebucht</span>
  }

  if (tx.ist_geschaeftlich && !tx.ist_privatentnahme && !tx.ist_einlage) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-xs bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 rounded px-1.5 py-0.5 shrink-0">
          Zuordnung nötig
        </span>
        <button
          onClick={() => onBuchen(tx)}
          disabled={ladendeTxId === tx.id || buchePending}
          className="text-xs px-2.5 py-1 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-700 rounded hover:bg-blue-100 dark:hover:bg-blue-900/50 disabled:opacity-40 transition-colors whitespace-nowrap"
        >
          {ladendeTxId === tx.id ? 'Suche…' : 'Abgleichen'}
        </button>
      </div>
    )
  }

  return null
}

// ---------------------------------------------------------------------------
// Transaktionsliste
// ---------------------------------------------------------------------------

function Transaktionsliste({ konto }: { konto: Konto }) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [buchungTx, setBuchungTx] = useState<BankTransaktion | null>(null)
  const [abgleichDialog, setAbgleichDialog] = useState<{ tx: BankTransaktion; vorschlaege: BankAbgleichVorschlag[] } | null>(null)
  const [ueberzahlungInfo, setUeberzahlungInfo] = useState<{
    rechnungId: number; rechnungsnummer: string; partner: string; ueberzahlung: number
  } | null>(null)
  const [toast, setToast] = useState<{ text: string; ok: boolean } | null>(null)
  const [suche, setSuche] = useState('')
  const [statusFilter, setStatusFilter] = useState<'alle' | 'offen' | 'gebucht' | 'privat'>('alle')
  const [datumVon, setDatumVon] = useState('')
  const [datumBis, setDatumBis] = useState('')

  const { data: txs = [], isLoading } = useQuery({
    queryKey: ['bank-transaktionen', konto.id],
    queryFn: () => getBankTransaktionen(konto.id!),
    enabled: !!konto.id,
  })

  const anerkenneMut = useMutation({
    mutationFn: (rechnungId: number) => ueberzahlungAnerkennen(rechnungId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['ueberzahlungen'] }); setUeberzahlungInfo(null) },
  })

  const bucheMut = useMutation({
    mutationFn: ({ txId, rechnungId }: { txId: number; rechnungId: number | null }) =>
      bucheTransaktion(txId, rechnungId),
    onSuccess: (tx, { rechnungId }) => {
      qc.invalidateQueries({ queryKey: ['bank-transaktionen', konto.id] })
      qc.invalidateQueries({ queryKey: ['ueberzahlungen'] })
      setAbgleichDialog(null)
      setBuchungTx(null)

      if (tx.forderung_id) {
        qc.invalidateQueries({ queryKey: ['forderungen'] })
        zeigToast('Lieferantenguthaben angelegt – im Dashboard sichtbar', true)
        return
      }

      if (rechnungId && abgleichDialog) {
        const vorschlag = abgleichDialog.vorschlaege.find(v => v.rechnung_id === rechnungId)
        if (vorschlag) {
          const diff = Math.abs(parseFloat(abgleichDialog.tx.betrag)) - parseFloat(vorschlag.restbetrag)
          if (diff > 0.02 && parseFloat(abgleichDialog.tx.betrag) > 0) {
            setUeberzahlungInfo({ rechnungId, rechnungsnummer: vorschlag.rechnungsnummer, partner: vorschlag.partner, ueberzahlung: diff })
            return
          }
        }
      }
      zeigToast(rechnungId ? 'Rechnung als bezahlt markiert' : 'Buchung erstellt', true)
    },
    onError: (e: Error) => zeigToast(e.message || 'Fehler beim Buchen.', false),
  })

  const abgleichMut = useMutation({
    mutationFn: (tx: BankTransaktion) => abgleichTransaktion(tx.id),
    onSuccess: (vorschlaege, tx) => {
      if (vorschlaege.length === 1 && vorschlaege[0].score === 3) {
        bucheMut.mutate({ txId: tx.id, rechnungId: vorschlaege[0].rechnung_id })
        return
      }
      if (vorschlaege.length > 0) setAbgleichDialog({ tx, vorschlaege })
      else proceedOhneAbgleich(tx)
    },
    onError: (_, tx) => proceedOhneAbgleich(tx),
  })

  function proceedOhneAbgleich(tx: BankTransaktion) {
    if (tx.kategorie_id) bucheMut.mutate({ txId: tx.id, rechnungId: null })
    else setBuchungTx(tx)
  }

  function zeigToast(text: string, ok: boolean) {
    setToast({ text, ok })
    setTimeout(() => setToast(null), 3500)
  }

  if (isLoading) return <p className="text-sm text-slate-500 dark:text-slate-400 py-4">Lade Transaktionen…</p>
  if (txs.length === 0) return (
    <div className="py-12 text-center text-slate-400 dark:text-slate-500 text-sm">Noch keine Transaktionen importiert.</div>
  )

  const offene = txs.filter(tx => tx.ist_geschaeftlich && !tx.ist_privatentnahme && !tx.ist_einlage && !tx.journal_id)
  const gebuchte = txs.filter(tx => !!tx.journal_id).length
  const ladendeTxId = abgleichMut.isPending && abgleichMut.variables ? abgleichMut.variables.id : null

  const gefilterteTxs = txs.filter(tx => {
    if (statusFilter === 'offen' && !(tx.ist_geschaeftlich && !tx.ist_privatentnahme && !tx.ist_einlage && !tx.journal_id)) return false
    if (statusFilter === 'gebucht' && !tx.journal_id) return false
    if (statusFilter === 'privat' && (tx.ist_geschaeftlich && !tx.ist_privatentnahme && !tx.ist_einlage)) return false
    if (datumVon && tx.datum < datumVon) return false
    if (datumBis && tx.datum > datumBis) return false
    if (suche) {
      const s = suche.toLowerCase()
      if (!((tx.partner_name ?? '').toLowerCase().includes(s) ||
            (tx.verwendungszweck ?? '').toLowerCase().includes(s) ||
            (tx.buchungstext ?? '').toLowerCase().includes(s))) return false
    }
    return true
  })

  return (
    <>
      <div className="flex flex-col gap-2 mb-3">
        <div className="flex items-center gap-3 flex-wrap">
          <input
            type="search"
            placeholder="Partner, Verwendungszweck…"
            value={suche}
            onChange={e => setSuche(e.target.value)}
            className="flex-1 min-w-[180px] text-sm px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 placeholder:text-slate-400"
          />
          <input
            type="date"
            value={datumVon}
            onChange={e => setDatumVon(e.target.value)}
            className="text-sm px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200"
          />
          <span className="text-xs text-slate-400">–</span>
          <input
            type="date"
            value={datumBis}
            onChange={e => setDatumBis(e.target.value)}
            className="text-sm px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200"
          />
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value as typeof statusFilter)}
            className="text-sm px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200"
          >
            <option value="alle">Alle</option>
            <option value="offen">Offen</option>
            <option value="gebucht">Gebucht</option>
            <option value="privat">Privat</option>
          </select>
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
          <span>{gefilterteTxs.length} von {txs.length} Transaktionen</span>
          {gebuchte > 0 && <span className="text-green-600 dark:text-green-400">{gebuchte} gebucht</span>}
          {offene.length > 0 && <span className="text-amber-600 dark:text-amber-400">{offene.length} offen</span>}
        </div>
      </div>

      {toast && (
        <div className={`mb-3 px-4 py-2.5 rounded-lg text-sm font-medium ${
          toast.ok
            ? 'bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-300'
            : 'bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300'
        }`}>{toast.text}</div>
      )}

      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 dark:bg-slate-700/50 text-slate-500 dark:text-slate-400 text-xs">
              <th className="px-4 py-2.5 text-left">Datum</th>
              <th className="px-4 py-2.5 text-right">Bankbetrag</th>
              <th className="px-4 py-2.5 text-left">Partner / Verwendungszweck</th>
              <th className="px-4 py-2.5 text-left">Art</th>
              <th className="px-4 py-2.5 text-left">Buchung / Zuordnung</th>
            </tr>
          </thead>
          <tbody>
            {gefilterteTxs.map(tx => (
              <tr key={tx.id} className="border-t border-slate-100 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/30">
                <td className="px-4 py-2.5 whitespace-nowrap text-slate-600 dark:text-slate-300 text-xs">{datumFmt(tx.datum)}</td>
                <td className={`px-4 py-2.5 text-right font-mono font-medium whitespace-nowrap text-sm ${
                  parseFloat(tx.betrag) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                }`}>{euroFmt(tx.betrag)}</td>
                <td className="px-4 py-2.5 max-w-[240px]">
                  <p className="text-slate-700 dark:text-slate-200 truncate">{tx.partner_name ?? '–'}</p>
                  <p className="text-xs text-slate-400 dark:text-slate-500 truncate">{tx.verwendungszweck ?? ''}</p>
                </td>
                <td className="px-4 py-2.5"><KlassifizierungBadge tx={tx} /></td>
                <td className="px-4 py-2.5">
                  <BuchungsCelle tx={tx} ladendeTxId={ladendeTxId} buchePending={bucheMut.isPending} onBuchen={t => abgleichMut.mutate(t)} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {abgleichDialog && (
        <AbgleichDialog
          tx={abgleichDialog.tx}
          vorschlaege={abgleichDialog.vorschlaege}
          buchePending={bucheMut.isPending}
          onZuordnen={rechnungId => bucheMut.mutate({ txId: abgleichDialog.tx.id, rechnungId })}
          onOhneRechnung={() => { setAbgleichDialog(null); proceedOhneAbgleich(abgleichDialog.tx) }}
          onClose={() => setAbgleichDialog(null)}
        />
      )}

      {ueberzahlungInfo && (
        <UeberzahlungDialog
          {...ueberzahlungInfo}
          onGutschrift={() => { setUeberzahlungInfo(null); navigate(`/rechnungen/${ueberzahlungInfo.rechnungId}`) }}
          onSpaeter={() => { setUeberzahlungInfo(null); zeigToast('Überzahlung im Dashboard vorgemerkt', true) }}
          onKeinHandlungsbedarf={() => anerkenneMut.mutate(ueberzahlungInfo.rechnungId)}
        />
      )}

      {buchungTx && (
        <BuchungForm
          initialWerte={{
            datum: buchungTx.datum,
            art: parseFloat(buchungTx.betrag) >= 0 ? 'Einnahme' : 'Ausgabe',
            brutto_betrag: String(Math.abs(parseFloat(buchungTx.betrag))),
            zahlungsart: 'Bank',
            beschreibung: [buchungTx.partner_name, buchungTx.verwendungszweck].filter(Boolean).join(' / ').slice(0, 255) || 'Bank-Transaktion',
            kategorie_id: buchungTx.kategorie_id ? String(buchungTx.kategorie_id) : '',
          }}
          onClose={() => setBuchungTx(null)}
          onSuccess={() => {
            setBuchungTx(null)
            qc.invalidateQueries({ queryKey: ['bank-transaktionen', konto.id] })
            zeigToast('Buchung erstellt', true)
          }}
        />
      )}
    </>
  )
}

// ---------------------------------------------------------------------------
// Hauptseite
// ---------------------------------------------------------------------------

export function BankImportPage() {
  const qc = useQueryClient()
  const [dialogOffen, setDialogOffen] = useState(false)
  const [aktivesKontoId, setAktivesKontoId] = useState<number | null>(null)

  const { data: konten = [] } = useQuery({ queryKey: ['konten'], queryFn: getKonten })
  const { data: templates = [] } = useQuery({ queryKey: ['bank-templates'], queryFn: getBankTemplates })

  const geschaeftskonten = konten.filter(k => k.kontotyp !== 'privat' && k.aktiv !== false)
  const aktivesKonto = geschaeftskonten.find(k => k.id === aktivesKontoId) ?? geschaeftskonten[0]

  const handleErfolg = useCallback((kontoId: number) => {
    setDialogOffen(false)
    setAktivesKontoId(kontoId)
    qc.invalidateQueries({ queryKey: ['bank-transaktionen', kontoId] })
    qc.invalidateQueries({ queryKey: ['forderungen'] })
  }, [qc])

  return (
    <div className="max-w-5xl px-6 py-8">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">Bank CSV-Import</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Kontoauszüge importieren und als Journal-Buchungen übernehmen.</p>
        </div>
        <button
          onClick={() => setDialogOffen(true)}
          disabled={geschaeftskonten.length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-40"
        >
          <span>+</span> CSV importieren
        </button>
      </div>

      {geschaeftskonten.length === 0 ? (
        <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-xl p-4 text-sm text-amber-700 dark:text-amber-300">
          Bitte zuerst ein Konto unter <strong>Einstellungen → Konten</strong> anlegen.
        </div>
      ) : (
        <>
          {geschaeftskonten.length > 1 && (
            <div className="flex gap-2 mb-4 flex-wrap">
              {geschaeftskonten.map(k => (
                <button
                  key={k.id}
                  onClick={() => setAktivesKontoId(k.id!)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    aktivesKonto?.id === k.id
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
                  }`}
                >
                  {k.name}
                  {k.kontotyp === 'mischkonto' && <span className="ml-1 text-xs opacity-70">Mischkonto</span>}
                </button>
              ))}
            </div>
          )}
          {aktivesKonto && <Transaktionsliste konto={aktivesKonto} />}
        </>
      )}

      {dialogOffen && (
        <ImportDialog
          konten={geschaeftskonten}
          templates={templates}
          onClose={() => setDialogOffen(false)}
          onErfolg={handleErfolg}
        />
      )}
    </div>
  )
}
