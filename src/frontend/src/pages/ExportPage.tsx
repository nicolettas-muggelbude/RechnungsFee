import { useState } from 'react'
import { DateInput } from '../components/DateInput'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useMxAuto } from '../hooks/useAnsicht'
import {
  downloadGobdExport,
  downloadDatevBuchungsstapel,
  downloadBuchhalterCsv,
  getUnternehmen,
  updateUnternehmen,
} from '../api/client'

const AKTUELLES_JAHR = new Date().getFullYear()
const JAHRE = Array.from({ length: 5 }, (_, i) => AKTUELLES_JAHR - i)

type Zeitraum = 'q1' | 'q2' | 'q3' | 'q4' | 'h1' | 'h2' | 'jahr' | 'custom'
type Tab = 'gobd' | 'datev' | 'csv'

function zeitraumZuDaten(z: Zeitraum, jahr: number, vonCustom: string, bisCustom: string) {
  const y = jahr
  const map: Record<Zeitraum, [string, string]> = {
    q1:     [`${y}-01-01`, `${y}-03-31`],
    q2:     [`${y}-04-01`, `${y}-06-30`],
    q3:     [`${y}-07-01`, `${y}-09-30`],
    q4:     [`${y}-10-01`, `${y}-12-31`],
    h1:     [`${y}-01-01`, `${y}-06-30`],
    h2:     [`${y}-07-01`, `${y}-12-31`],
    jahr:   [`${y}-01-01`, `${y}-12-31`],
    custom: [vonCustom, bisCustom],
  }
  return map[z]
}

function ZeitraumAuswahl({
  jahr, setJahr, zeitraum, setZeitraum, vonCustom, setVonCustom, bisCustom, setBisCustom, accent,
}: {
  jahr: number; setJahr: (v: number) => void
  zeitraum: Zeitraum; setZeitraum: (v: Zeitraum) => void
  vonCustom: string; setVonCustom: (v: string) => void
  bisCustom: string; setBisCustom: (v: string) => void
  accent: string
}) {
  const sel = `border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 ${accent} bg-white dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100`
  const inp = `border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100 focus:outline-none focus:ring-2 ${accent}`
  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="space-y-1">
        <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Jahr</label>
        <select value={jahr} onChange={(e) => setJahr(Number(e.target.value))} className={sel}>
          {JAHRE.map((j) => <option key={j} value={j}>{j}</option>)}
        </select>
      </div>
      <div className="space-y-1">
        <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Zeitraum</label>
        <select value={zeitraum} onChange={(e) => setZeitraum(e.target.value as Zeitraum)} className={sel}>
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
            <DateInput value={vonCustom} onChange={setVonCustom} className={inp} />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Bis</label>
            <DateInput value={bisCustom} onChange={setBisCustom} className={inp} />
          </div>
        </>
      )}
    </div>
  )
}

function Erfolg({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg px-4 py-3">
      <span className="text-green-600 dark:text-green-400 shrink-0 mt-0.5">✓</span>
      <div className="text-sm text-green-800 dark:text-green-300">{children}</div>
    </div>
  )
}

function Fehler({ text }: { text: string }) {
  return (
    <div className="flex items-start gap-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3">
      <span className="text-red-600 dark:text-red-400 shrink-0 mt-0.5">✗</span>
      <p className="text-sm text-red-800 dark:text-red-300">{text}</p>
    </div>
  )
}

export function ExportPage() {
  const mxAuto = useMxAuto()
  const [aktTab, setAktTab] = useState<Tab>('gobd')

  // GoBD
  const [gobdJahr, setGobdJahr] = useState(AKTUELLES_JAHR)
  const [gobdLaedt, setGobdLaedt] = useState(false)
  const [gobdErfolg, setGobdErfolg] = useState<string | null>(null)
  const [gobdFehler, setGobdFehler] = useState<string | null>(null)

  // DATEV
  const [datevJahr, setDatevJahr] = useState(AKTUELLES_JAHR)
  const [datevZeitraum, setDatevZeitraum] = useState<Zeitraum>('q1')
  const [datevVon, setDatevVon] = useState('')
  const [datevBis, setDatevBis] = useState('')
  const [datevLaedt, setDatevLaedt] = useState(false)
  const [datevMitBelegen, setDatevMitBelegen] = useState(true)
  const [datevErgebnis, setDatevErgebnis] = useState<{ filename: string; eintraege: number; uebersprungen: number; leer_konto: number; belege: number | null } | null>(null)
  const [datevFehler, setDatevFehler] = useState<string | null>(null)
  const [konfigOffen, setKonfigOffen] = useState(false)
  const [konfigGespeichert, setKonfigGespeichert] = useState(false)
  const [beraternr, setBeraternr] = useState('')
  const [mandantennr, setMandantennr] = useState('')
  const [kontoBar, setKontoBar] = useState('')
  const [kontoBank, setKontoBank] = useState('')
  const [kontoKarte, setKontoKarte] = useState('')
  const [kontoPaypal, setKontoPaypal] = useState('')

  // CSV
  const [csvJahr, setCsvJahr] = useState(AKTUELLES_JAHR)
  const [csvZeitraum, setCsvZeitraum] = useState<Zeitraum>('jahr')
  const [csvVon, setCsvVon] = useState('')
  const [csvBis, setCsvBis] = useState('')
  const [csvLaedt, setCsvLaedt] = useState(false)
  const [csvErgebnis, setCsvErgebnis] = useState<{ filename: string; eintraege: number } | null>(null)
  const [csvFehler, setCsvFehler] = useState<string | null>(null)

  const queryClient = useQueryClient()
  const { data: unt } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen })
  const skr = unt?.kontenrahmen ?? 'SKR04'

  function oeffneKonfig() {
    setBeraternr(unt?.datev_beraternummer ?? '')
    setMandantennr(unt?.datev_mandantennummer ?? '')
    setKontoBar(unt?.datev_konto_bar ?? '')
    setKontoBank(unt?.datev_konto_bank ?? '')
    setKontoKarte(unt?.datev_konto_karte ?? '')
    setKontoPaypal(unt?.datev_konto_paypal ?? '')
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
    setGobdLaedt(true); setGobdErfolg(null); setGobdFehler(null)
    try { setGobdErfolg(await downloadGobdExport(gobdJahr)) }
    catch (e: any) { setGobdFehler(e?.message ?? 'Unbekannter Fehler') }
    finally { setGobdLaedt(false) }
  }

  async function handleDatev() {
    setDatevLaedt(true); setDatevErgebnis(null); setDatevFehler(null)
    const [von, bis] = zeitraumZuDaten(datevZeitraum, datevJahr, datevVon, datevBis)
    if (!von || !bis) { setDatevFehler('Bitte Von- und Bis-Datum angeben'); setDatevLaedt(false); return }
    try { setDatevErgebnis(await downloadDatevBuchungsstapel(von, bis, datevMitBelegen)) }
    catch (e: any) { setDatevFehler(e?.message ?? 'Unbekannter Fehler') }
    finally { setDatevLaedt(false) }
  }

  async function handleCsv() {
    setCsvLaedt(true); setCsvErgebnis(null); setCsvFehler(null)
    const [von, bis] = zeitraumZuDaten(csvZeitraum, csvJahr, csvVon, csvBis)
    if (!von || !bis) { setCsvFehler('Bitte Von- und Bis-Datum angeben'); setCsvLaedt(false); return }
    try { setCsvErgebnis(await downloadBuchhalterCsv(von, bis)) }
    catch (e: any) { setCsvFehler(e?.message ?? 'Unbekannter Fehler') }
    finally { setCsvLaedt(false) }
  }

  const inputCls = 'w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500'
  const labelCls = 'block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1'

  const TABS: { id: Tab; label: string; icon: string; color: string }[] = [
    { id: 'gobd',  label: 'GoBD-Export',    icon: '📦', color: 'blue'   },
    { id: 'datev', label: 'DATEV-Export',    icon: '📊', color: 'emerald'},
    { id: 'csv',   label: 'Buchhalter-CSV',  icon: '📋', color: 'violet' },
  ]

  const tabActive = (color: string) =>
    color === 'blue'    ? 'border-blue-600 text-blue-600 dark:text-blue-400' :
    color === 'emerald' ? 'border-emerald-600 text-emerald-600 dark:text-emerald-400' :
                          'border-violet-600 text-violet-600 dark:text-violet-400'

  const btnColor = (color: string) =>
    color === 'blue'    ? 'bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300' :
    color === 'emerald' ? 'bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300' :
                          'bg-violet-600 hover:bg-violet-700 disabled:bg-violet-300'

  return (
    <div className={`p-6 max-w-4xl ${mxAuto} space-y-4`}>
      <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Exporte</h1>

      {/* Tab-Leiste */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
        <div className="flex border-b border-slate-200 dark:border-slate-700">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setAktTab(t.id)}
              className={`flex items-center gap-2 px-5 py-3.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                aktTab === t.id
                  ? tabActive(t.color)
                  : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
              }`}
            >
              <span>{t.icon}</span>
              {t.label}
            </button>
          ))}
        </div>

        {/* ── GoBD ──────────────────────────────────────────────────────── */}
        {aktTab === 'gobd' && (
          <div className="p-6 space-y-5">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Vollständiger Datenexport nach GoBD für Betriebsprüfung und Archivierung (Z3-Datenträgerüberlassung).
            </p>

            <div className="flex items-end gap-4">
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Wirtschaftsjahr</label>
                <select value={gobdJahr} onChange={(e) => setGobdJahr(Number(e.target.value))}
                  className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100">
                  {JAHRE.map((j) => <option key={j} value={j}>{j}</option>)}
                </select>
              </div>
              <button onClick={handleGobd} disabled={gobdLaedt}
                className={`flex items-center gap-2 ${btnColor('blue')} text-white font-medium text-sm px-5 py-2 rounded-lg transition-colors`}>
                {gobdLaedt ? <><span className="animate-spin">⏳</span>Wird erstellt…</> : <><span>📦</span>Export erstellen</>}
              </button>
            </div>

            {gobdErfolg && <Erfolg><p className="font-medium">Export erstellt</p><p className="mt-0.5 font-mono text-xs">{gobdErfolg}</p></Erfolg>}
            {gobdFehler && <Fehler text={gobdFehler} />}

            <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg p-4 space-y-3">
              <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Das ZIP-Archiv enthält:</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {[
                  { datei: 'journal.csv',               beschreibung: 'Alle Journaleinträge (IDEA-kompatibel)' },
                  { datei: 'tagesabschluesse.csv',       beschreibung: 'Alle Tagesabschlüsse mit Kennzahlen' },
                  { datei: 'kategorien.csv',             beschreibung: 'Kategorie-Stammdaten (SKR03/04/49)' },
                  { datei: 'kunden.csv',                 beschreibung: 'Kunden-Stammdaten' },
                  { datei: 'lieferanten.csv',            beschreibung: 'Lieferanten-Stammdaten' },
                  { datei: 'integritaetspruefung.csv',   beschreibung: 'SHA-256-Signaturprüfung aller Datensätze' },
                  { datei: 'index.xml',                  beschreibung: 'GDPdU-Beschreibungsdatei (XML)' },
                  { datei: 'gobd_pruefbericht.pdf',      beschreibung: 'Zusammenfassender Prüfbericht (PDF)' },
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
                  UTF-8 mit BOM · Semikolon-getrennt · Dezimalkomma · Datum TT.MM.JJJJ · kompatibel mit IDEA, Excel und LibreOffice
                </p>
              </div>
            </div>

            <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg px-4 py-3 flex gap-3">
              <span className="text-amber-500 dark:text-amber-400 shrink-0">⚠</span>
              <p className="text-xs text-amber-800 dark:text-amber-300">
                Alle Journaldaten sind GoBD-konform unveränderbar gespeichert und durch SHA-256-Signaturen gesichert.
                Bei einer Betriebsprüfung nach §147 AO ist dieser Export als Z3-Datenträgerüberlassung geeignet.
              </p>
            </div>
          </div>
        )}

        {/* ── DATEV ─────────────────────────────────────────────────────── */}
        {aktTab === 'datev' && (
          <div className="p-6 space-y-5">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Buchungsstapel im DATEV EXTF-Format (v700/9) für den Steuerberater – Modus A (Zuflussprinzip).
            </p>

            <ZeitraumAuswahl
              jahr={datevJahr} setJahr={setDatevJahr}
              zeitraum={datevZeitraum} setZeitraum={setDatevZeitraum}
              vonCustom={datevVon} setVonCustom={setDatevVon}
              bisCustom={datevBis} setBisCustom={setDatevBis}
              accent="focus:ring-emerald-500"
            />

            <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 cursor-pointer">
              <input type="checkbox" checked={datevMitBelegen} onChange={(e) => setDatevMitBelegen(e.target.checked)}
                className="rounded border-slate-300 dark:border-slate-600 text-emerald-600 focus:ring-emerald-500" />
              Belege mitexportieren (ZIP mit Belege/-Ordner, benannt nach Belegnummer)
            </label>

            <button onClick={handleDatev} disabled={datevLaedt}
              className={`flex items-center gap-2 ${btnColor('emerald')} text-white font-medium text-sm px-5 py-2 rounded-lg transition-colors`}>
              {datevLaedt ? <><span className="animate-spin">⏳</span>Wird erstellt…</> : <><span>📊</span>DATEV exportieren</>}
            </button>

            {datevErgebnis && (
              <Erfolg>
                <p className="font-medium">Buchungsstapel exportiert</p>
                <p className="mt-0.5 font-mono text-xs">{datevErgebnis.filename}</p>
                <p className="mt-1 text-xs">
                  {datevErgebnis.eintraege} Buchung{datevErgebnis.eintraege !== 1 ? 'en' : ''} exportiert
                  {datevErgebnis.belege !== null && (
                    <span className="ml-2">· {datevErgebnis.belege} Beleg{datevErgebnis.belege !== 1 ? 'e' : ''} mitexportiert</span>
                  )}
                  {datevErgebnis.uebersprungen > 0 && (
                    <span className="text-red-600 dark:text-red-400 ml-2">
                      · {datevErgebnis.uebersprungen} übersprungen (kein Zahlungskonto)
                    </span>
                  )}
                  {datevErgebnis.leer_konto > 0 && (
                    <span className="text-amber-600 dark:text-amber-400 ml-2">
                      · {datevErgebnis.leer_konto} ohne Sachkonto (DATEV meldet Importfehler – im Programm ergänzen)
                    </span>
                  )}
                </p>
                <p className="mt-0.5 text-xs opacity-70">Datei gespeichert im Downloads-Ordner</p>
              </Erfolg>
            )}
            {datevFehler && <Fehler text={datevFehler} />}

            {/* Konfiguration */}
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
                    Diese Nummern bekommst du von deinem Steuerberater. Ohne Konfiguration werden SKR-Standardkonten und Beraternr. 1001 / Mandant 1 verwendet.
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <div><label className={labelCls}>Beraternummer</label>
                      <input type="text" value={beraternr} onChange={(e) => setBeraternr(e.target.value)} placeholder="z. B. 12345" className={inputCls} /></div>
                    <div><label className={labelCls}>Mandantennummer</label>
                      <input type="text" value={mandantennr} onChange={(e) => setMandantennr(e.target.value)} placeholder="z. B. 1" className={inputCls} /></div>
                  </div>
                  <p className="text-xs font-semibold text-slate-600 dark:text-slate-300">Gegenkonto-Nummern (Zahlungsweg → DATEV-Konto)</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div><label className={labelCls}>Bar (Kasse)</label>
                      <input type="text" value={kontoBar} onChange={(e) => setKontoBar(e.target.value)} placeholder={skr === 'SKR03' ? '1000' : '1600'} className={inputCls} /></div>
                    <div><label className={labelCls}>Bank / Überweisung</label>
                      <input type="text" value={kontoBank} onChange={(e) => setKontoBank(e.target.value)} placeholder={skr === 'SKR03' ? '1200' : '1800'} className={inputCls} /></div>
                    <div><label className={labelCls}>Karte (EC / Kredit)</label>
                      <input type="text" value={kontoKarte} onChange={(e) => setKontoKarte(e.target.value)} placeholder={skr === 'SKR03' ? '1200' : '1800'} className={inputCls} /></div>
                    <div><label className={labelCls}>PayPal</label>
                      <input type="text" value={kontoPaypal} onChange={(e) => setKontoPaypal(e.target.value)} placeholder={skr === 'SKR03' ? '1361' : '1460'} className={inputCls} /></div>
                  </div>
                  <div className="flex items-center gap-3 pt-1">
                    <button onClick={() => speicherMut.mutate()} disabled={speicherMut.isPending}
                      className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 text-white font-medium text-sm px-4 py-2 rounded-lg transition-colors">
                      {speicherMut.isPending ? 'Speichert…' : 'Speichern'}
                    </button>
                    {konfigGespeichert && <span className="text-sm text-emerald-600 dark:text-emerald-400">✓ Gespeichert</span>}
                  </div>
                </div>
              )}
            </div>

            <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-3 space-y-1.5">
              <p className="text-xs font-medium text-slate-700 dark:text-slate-200">BU-Schlüssel werden automatisch gesetzt:</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                leer = steuerfrei / §19 · <strong>2</strong> = 7 % · <strong>9</strong> = 19 % · <strong>89/93</strong> = ig. Erwerb · <strong>94</strong> = §13b · <strong>57</strong> = §25a Marge
              </p>
            </div>

            <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg px-4 py-3 flex gap-3">
              <span className="text-amber-500 dark:text-amber-400 shrink-0">⚠</span>
              <p className="text-xs text-amber-800 dark:text-amber-300">
                <span className="font-semibold">Beta:</span> Das EXTF-Format wurde nach DATEV-Spezifikation implementiert, konnte mangels DATEV-Lizenz aber nicht gegen die echte Software getestet werden.
                Wir bitten um Rückmeldung – Fehler gerne als{' '}
                <a href="https://github.com/nicolettas-muggelbude/RechnungsFee/issues" target="_blank" rel="noreferrer" className="underline">GitHub-Issue</a> melden.
              </p>
            </div>
          </div>
        )}

        {/* ── Buchhalter-CSV ────────────────────────────────────────────── */}
        {aktTab === 'csv' && (
          <div className="p-6 space-y-5">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Einfaches Journal-CSV für Excel, LibreOffice oder andere Buchhaltungsprogramme ohne DATEV-Import.
            </p>

            <ZeitraumAuswahl
              jahr={csvJahr} setJahr={setCsvJahr}
              zeitraum={csvZeitraum} setZeitraum={setCsvZeitraum}
              vonCustom={csvVon} setVonCustom={setCsvVon}
              bisCustom={csvBis} setBisCustom={setCsvBis}
              accent="focus:ring-violet-500"
            />

            <button onClick={handleCsv} disabled={csvLaedt}
              className={`flex items-center gap-2 ${btnColor('violet')} text-white font-medium text-sm px-5 py-2 rounded-lg transition-colors`}>
              {csvLaedt ? <><span className="animate-spin">⏳</span>Wird erstellt…</> : <><span>📋</span>CSV exportieren</>}
            </button>

            {csvErgebnis && (
              <Erfolg>
                <p className="font-medium">CSV exportiert</p>
                <p className="mt-0.5 font-mono text-xs">{csvErgebnis.filename}</p>
                <p className="mt-1 text-xs">{csvErgebnis.eintraege} Buchung{csvErgebnis.eintraege !== 1 ? 'en' : ''}</p>
                <p className="mt-0.5 text-xs opacity-70">Datei gespeichert im Downloads-Ordner</p>
              </Erfolg>
            )}
            {csvFehler && <Fehler text={csvFehler} />}

            <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-3 space-y-1.5">
              <p className="text-xs font-medium text-slate-700 dark:text-slate-200">Spalten:</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                Datum · Belegnr · Externe Belegnr · Beschreibung · Kategorie · Zahlungsart · Art · Netto · USt-Satz % · USt-Betrag · Brutto
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                UTF-8 mit BOM · Semikolon-getrennt · Dezimalkomma · Datum TT.MM.JJJJ · direkt in Excel / LibreOffice öffenbar
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
