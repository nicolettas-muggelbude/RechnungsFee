import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  downloadGobdExport,
  downloadDatevBuchungsstapel,
  getUnternehmen,
  updateUnternehmen,
} from '../api/client'

const AKTUELLES_JAHR = new Date().getFullYear()
const JAHRE = Array.from({ length: 5 }, (_, i) => AKTUELLES_JAHR - i)

type Zeitraum = 'q1' | 'q2' | 'q3' | 'q4' | 'h1' | 'h2' | 'jahr' | 'custom'

function zeitraumZuDaten(z: Zeitraum, jahr: number, vonCustom: string, bisCustom: string) {
  const y = jahr
  const map: Record<Zeitraum, [string, string]> = {
    q1:    [`${y}-01-01`, `${y}-03-31`],
    q2:    [`${y}-04-01`, `${y}-06-30`],
    q3:    [`${y}-07-01`, `${y}-09-30`],
    q4:    [`${y}-10-01`, `${y}-12-31`],
    h1:    [`${y}-01-01`, `${y}-06-30`],
    h2:    [`${y}-07-01`, `${y}-12-31`],
    jahr:  [`${y}-01-01`, `${y}-12-31`],
    custom: [vonCustom, bisCustom],
  }
  return map[z]
}

export function ExportPage() {
  // GoBD
  const [gobd_jahr, setGobdJahr] = useState(AKTUELLES_JAHR)
  const [gobdLaedt, setGobdLaedt] = useState(false)
  const [gobdErfolg, setGobdErfolg] = useState<string | null>(null)
  const [gobdFehler, setGobdFehler] = useState<string | null>(null)

  // DATEV
  const [datevJahr, setDatevJahr] = useState(AKTUELLES_JAHR)
  const [zeitraum, setZeitraum] = useState<Zeitraum>('q1')
  const [vonCustom, setVonCustom] = useState('')
  const [bisCustom, setBisCustom] = useState('')
  const [datevLaedt, setDatevLaedt] = useState(false)
  const [datevErgebnis, setDatevErgebnis] = useState<{
    filename: string; eintraege: number; uebersprungen: number
  } | null>(null)
  const [datevFehler, setDatevFehler] = useState<string | null>(null)

  // DATEV-Konfiguration
  const [konfigOffen, setKonfigOffen] = useState(false)
  const [konfigGespeichert, setKonfigGespeichert] = useState(false)
  const queryClient = useQueryClient()

  const { data: unt } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen })

  const [beraternr, setBeraternr] = useState('')
  const [mandantennr, setMandantennr] = useState('')
  const [kontoBar, setKontoBar] = useState('')
  const [kontoBank, setKontoBank] = useState('')
  const [kontoKarte, setKontoKarte] = useState('')
  const [kontoPaypal, setKontoPaypal] = useState('')

  // Felder vorbelegen wenn Unternehmen geladen
  const konfig = unt ? {
    beraternr: unt.datev_beraternummer ?? '',
    mandantennr: unt.datev_mandantennummer ?? '',
    kontoBar: unt.datev_konto_bar ?? '',
    kontoBank: unt.datev_konto_bank ?? '',
    kontoKarte: unt.datev_konto_karte ?? '',
    kontoPaypal: unt.datev_konto_paypal ?? '',
  } : null

  function oeffneKonfig() {
    if (konfig) {
      setBeraternr(konfig.beraternr)
      setMandantennr(konfig.mandantennr)
      setKontoBar(konfig.kontoBar)
      setKontoBank(konfig.kontoBank)
      setKontoKarte(konfig.kontoKarte)
      setKontoPaypal(konfig.kontoPaypal)
    }
    setKonfigOffen(true)
    setKonfigGespeichert(false)
  }

  const speicherMut = useMutation({
    mutationFn: () => updateUnternehmen({
      datev_beraternummer: beraternr || null,
      datev_mandantennummer: mandantennr || null,
      datev_konto_bar: kontoBar || null,
      datev_konto_bank: kontoBank || null,
      datev_konto_karte: kontoKarte || null,
      datev_konto_paypal: kontoPaypal || null,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['unternehmen'] })
      setKonfigGespeichert(true)
      setTimeout(() => setKonfigGespeichert(false), 3000)
    },
  })

  async function handleGobd() {
    setGobdLaedt(true)
    setGobdErfolg(null)
    setGobdFehler(null)
    try {
      const filename = await downloadGobdExport(gobd_jahr)
      setGobdErfolg(filename)
    } catch (e: any) {
      setGobdFehler(e?.message ?? 'Unbekannter Fehler')
    } finally {
      setGobdLaedt(false)
    }
  }

  async function handleDatev() {
    setDatevLaedt(true)
    setDatevErgebnis(null)
    setDatevFehler(null)
    const [von, bis] = zeitraumZuDaten(zeitraum, datevJahr, vonCustom, bisCustom)
    if (!von || !bis) {
      setDatevFehler('Bitte Von- und Bis-Datum angeben')
      setDatevLaedt(false)
      return
    }
    try {
      const result = await downloadDatevBuchungsstapel(von, bis)
      setDatevErgebnis(result)
    } catch (e: any) {
      setDatevFehler(e?.message ?? 'Unbekannter Fehler')
    } finally {
      setDatevLaedt(false)
    }
  }

  const inputCls = 'w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500'
  const labelCls = 'block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1'

  // SKR-Standardwerte als Placeholder
  const skr = unt?.kontenrahmen ?? 'SKR04'
  const phBar    = '1000'
  const phBank   = skr === 'SKR03' ? '1200' : '1800'
  const phKarte  = skr === 'SKR03' ? '1200' : '1800'
  const phPaypal = skr === 'SKR03' ? '1360' : '1460'

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      {/* ── GoBD-Export ─────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Exporte</h1>
      </div>

      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
        <div className="bg-blue-600 px-6 py-4">
          <h2 className="text-white font-bold text-lg">GoBD-Export</h2>
          <p className="text-blue-100 text-sm mt-0.5">
            Journaldaten, Tagesabschlüsse und Stammdaten als ZIP-Archiv exportieren
          </p>
        </div>

        <div className="p-6 space-y-5">
          <div className="flex items-end gap-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700 dark:text-slate-200" htmlFor="export-jahr">
                Wirtschaftsjahr
              </label>
              <select
                id="export-jahr"
                value={gobd_jahr}
                onChange={(e) => setGobdJahr(Number(e.target.value))}
                className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
              >
                {JAHRE.map((j) => <option key={j} value={j}>{j}</option>)}
              </select>
            </div>
            <button
              onClick={handleGobd}
              disabled={gobdLaedt}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium text-sm px-5 py-2 rounded-lg transition-colors"
            >
              {gobdLaedt ? <><span className="animate-spin">⏳</span>Wird erstellt…</> : <><span>📦</span>Export erstellen</>}
            </button>
          </div>

          {gobdErfolg && (
            <div className="flex items-start gap-3 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg px-4 py-3">
              <span className="text-green-600 dark:text-green-400 shrink-0 mt-0.5">✓</span>
              <div className="text-sm text-green-800 dark:text-green-300">
                <p className="font-medium">Export erfolgreich erstellt</p>
                <p className="mt-0.5 font-mono text-xs">{gobdErfolg}</p>
                <p className="mt-1 text-xs opacity-75">Die Datei wurde in deinen Downloads-Ordner gespeichert.</p>
              </div>
            </div>
          )}
          {gobdFehler && (
            <div className="flex items-start gap-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3">
              <span className="text-red-600 dark:text-red-400 shrink-0 mt-0.5">✗</span>
              <p className="text-sm text-red-800 dark:text-red-300">{gobdFehler}</p>
            </div>
          )}

          <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg p-4 space-y-3">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Das ZIP-Archiv enthält:</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {[
                { datei: 'journal.csv',              beschreibung: 'Alle Journaleinträge (IDEA-kompatibel)' },
                { datei: 'tagesabschluesse.csv',     beschreibung: 'Alle Tagesabschlüsse mit Kennzahlen' },
                { datei: 'kategorien.csv',           beschreibung: 'Kategorie-Stammdaten (SKR03/04/49)' },
                { datei: 'kunden.csv',               beschreibung: 'Kunden-Stammdaten' },
                { datei: 'lieferanten.csv',          beschreibung: 'Lieferanten-Stammdaten' },
                { datei: 'integritaetspruefung.csv', beschreibung: 'SHA-256-Signaturprüfung aller Datensätze' },
                { datei: 'index.xml',                beschreibung: 'GDPdU-Beschreibungsdatei (XML)' },
                { datei: 'gobd_pruefbericht.pdf',    beschreibung: 'Zusammenfassender Prüfbericht (PDF)' },
              ].map(({ datei, beschreibung }) => (
                <div key={datei} className="flex items-start gap-2">
                  <span className="text-blue-500 mt-0.5 shrink-0">📄</span>
                  <div>
                    <p className="text-xs font-mono font-medium text-slate-800 dark:text-slate-100">{datei}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{beschreibung}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="pt-2 border-t border-slate-200 dark:border-slate-700">
              <p className="text-xs text-slate-500 dark:text-slate-400">
                <span className="font-medium">CSV-Format:</span>{' '}
                UTF-8 mit BOM · Semikolon-getrennt · Dezimalkomma · Datum TT.MM.JJJJ
                · kompatibel mit IDEA, Excel und LibreOffice
              </p>
            </div>
          </div>

          <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg px-4 py-3 flex gap-3">
            <span className="text-amber-500 dark:text-amber-400 shrink-0">⚠</span>
            <p className="text-xs text-amber-800 dark:text-amber-300">
              Alle Journaldaten sind GoBD-konform unveränderbar gespeichert und durch SHA-256-Signaturen
              gesichert. Der Export enthält eine vollständige Integritätsprüfung. Bei einer Betriebsprüfung
              nach §147 AO ist dieser Export als Z3-Datenträgerüberlassung geeignet.
            </p>
          </div>
        </div>
      </div>

      {/* ── DATEV-Export ─────────────────────────────────────────────────── */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
        <div className="bg-emerald-600 px-6 py-4">
          <h2 className="text-white font-bold text-lg">DATEV-Export</h2>
          <p className="text-emerald-100 text-sm mt-0.5">
            Buchungsstapel im DATEV EXTF-Format für den Steuerberater (Modus A – Zuflussprinzip)
          </p>
        </div>

        <div className="p-6 space-y-5">
          {/* Zeitraumauswahl */}
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Jahr</label>
              <select
                value={datevJahr}
                onChange={(e) => setDatevJahr(Number(e.target.value))}
                className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
              >
                {JAHRE.map((j) => <option key={j} value={j}>{j}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Zeitraum</label>
              <select
                value={zeitraum}
                onChange={(e) => setZeitraum(e.target.value as Zeitraum)}
                className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
              >
                <option value="q1">Q1 (Jan–Mär)</option>
                <option value="q2">Q2 (Apr–Jun)</option>
                <option value="q3">Q3 (Jul–Sep)</option>
                <option value="q4">Q4 (Okt–Dez)</option>
                <option value="h1">Halbjahr 1 (Jan–Jun)</option>
                <option value="h2">Halbjahr 2 (Jul–Dez)</option>
                <option value="jahr">Ganzes Jahr</option>
                <option value="custom">Benutzerdefiniert</option>
              </select>
            </div>
            {zeitraum === 'custom' && (
              <>
                <div className="space-y-1">
                  <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Von</label>
                  <input type="date" value={vonCustom} onChange={(e) => setVonCustom(e.target.value)}
                    className="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500" />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Bis</label>
                  <input type="date" value={bisCustom} onChange={(e) => setBisCustom(e.target.value)}
                    className="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500" />
                </div>
              </>
            )}
            <button
              onClick={handleDatev}
              disabled={datevLaedt}
              className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 text-white font-medium text-sm px-5 py-2 rounded-lg transition-colors"
            >
              {datevLaedt ? <><span className="animate-spin">⏳</span>Wird erstellt…</> : <><span>📊</span>DATEV exportieren</>}
            </button>
          </div>

          {datevErgebnis && (
            <div className="flex items-start gap-3 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg px-4 py-3">
              <span className="text-green-600 dark:text-green-400 shrink-0 mt-0.5">✓</span>
              <div className="text-sm text-green-800 dark:text-green-300">
                <p className="font-medium">Buchungsstapel exportiert</p>
                <p className="mt-0.5 font-mono text-xs">{datevErgebnis.filename}</p>
                <p className="mt-1 text-xs">
                  {datevErgebnis.eintraege} Buchung{datevErgebnis.eintraege !== 1 ? 'en' : ''} exportiert
                  {datevErgebnis.uebersprungen > 0 && (
                    <span className="text-amber-600 dark:text-amber-400 ml-2">
                      · {datevErgebnis.uebersprungen} übersprungen (fehlende Kontonummern)
                    </span>
                  )}
                </p>
              </div>
            </div>
          )}
          {datevFehler && (
            <div className="flex items-start gap-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3">
              <span className="text-red-600 dark:text-red-400 shrink-0 mt-0.5">✗</span>
              <p className="text-sm text-red-800 dark:text-red-300">{datevFehler}</p>
            </div>
          )}

          {/* DATEV-Konfiguration (aufklappbar) */}
          <div className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
            <button
              onClick={() => konfigOffen ? setKonfigOffen(false) : oeffneKonfig()}
              className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            >
              <span>⚙ DATEV-Konfiguration (Berater- / Kontonummern)</span>
              <span className="text-slate-400">{konfigOffen ? '▲' : '▼'}</span>
            </button>

            {konfigOffen && (
              <div className="border-t border-slate-200 dark:border-slate-700 p-4 space-y-4 bg-slate-50 dark:bg-slate-900">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Diese Nummern bekommst du von deinem Steuerberater. Ohne Konfiguration werden
                  SKR-Standardkonten und Beraternr. 1001 / Mandant 1 verwendet.
                </p>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className={labelCls}>Beraternummer</label>
                    <input type="text" value={beraternr} onChange={(e) => setBeraternr(e.target.value)}
                      placeholder="z. B. 12345" className={inputCls} />
                  </div>
                  <div>
                    <label className={labelCls}>Mandantennummer</label>
                    <input type="text" value={mandantennr} onChange={(e) => setMandantennr(e.target.value)}
                      placeholder="z. B. 1" className={inputCls} />
                  </div>
                </div>

                <div>
                  <p className="text-xs font-semibold text-slate-600 dark:text-slate-300 mb-2">
                    Gegenkonto-Nummern (Zahlungsweg → DATEV-Konto)
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className={labelCls}>Bar (Kasse)</label>
                      <input type="text" value={kontoBar} onChange={(e) => setKontoBar(e.target.value)}
                        placeholder={phBar} className={inputCls} />
                    </div>
                    <div>
                      <label className={labelCls}>Bank / Überweisung</label>
                      <input type="text" value={kontoBank} onChange={(e) => setKontoBank(e.target.value)}
                        placeholder={phBank} className={inputCls} />
                    </div>
                    <div>
                      <label className={labelCls}>Karte (EC / Kredit)</label>
                      <input type="text" value={kontoKarte} onChange={(e) => setKontoKarte(e.target.value)}
                        placeholder={phKarte} className={inputCls} />
                    </div>
                    <div>
                      <label className={labelCls}>PayPal</label>
                      <input type="text" value={kontoPaypal} onChange={(e) => setKontoPaypal(e.target.value)}
                        placeholder={phPaypal} className={inputCls} />
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 pt-1">
                  <button
                    onClick={() => speicherMut.mutate()}
                    disabled={speicherMut.isPending}
                    className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 text-white font-medium text-sm px-4 py-2 rounded-lg transition-colors"
                  >
                    {speicherMut.isPending ? 'Speichert…' : 'Speichern'}
                  </button>
                  {konfigGespeichert && (
                    <span className="text-sm text-emerald-600 dark:text-emerald-400">✓ Gespeichert</span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Info */}
          <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-3 space-y-1.5">
            <p className="text-xs font-medium text-slate-700 dark:text-slate-200">Was wird exportiert:</p>
            <ul className="text-xs text-slate-500 dark:text-slate-400 space-y-1 list-disc list-inside">
              <li>Alle Journalbuchungen im gewählten Zeitraum</li>
              <li>BU-Schlüssel für 19 % / 7 % / ig. Erwerb / §13b / §25a Differenzbesteuerung</li>
              <li>Gegenkonto aus Zahlungsart (Bar / Bank / Karte / PayPal)</li>
              <li>Format: DATEV EXTF Buchungsstapel v700/9, UTF-8 mit BOM, Semikolon-getrennt</li>
            </ul>
          </div>

          {/* Beta-Hinweis */}
          <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg px-4 py-3 flex gap-3">
            <span className="text-amber-500 dark:text-amber-400 shrink-0">⚠</span>
            <p className="text-xs text-amber-800 dark:text-amber-300">
              <span className="font-semibold">Beta:</span> Das EXTF-Format wurde nach DATEV-Spezifikation implementiert, konnte mangels DATEV-Lizenz aber nicht gegen die echte Software getestet werden.
              Wir bitten um Rückmeldung – Fehler gerne als{' '}
              <a href="https://github.com/nicolettas-muggelbude/RechnungsFee/issues" target="_blank" rel="noreferrer"
                className="underline">GitHub-Issue</a> melden.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
