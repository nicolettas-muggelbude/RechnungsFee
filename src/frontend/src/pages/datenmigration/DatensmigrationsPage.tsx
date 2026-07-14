import { useState, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  getMusterCsv,
  getSpalten,
  getImportVorschau,
  importDurchfuehren,
  getMappingVorlagen,
  saveMappingVorlage,
  deleteMappingVorlage,
  type ImportVorschauZeile,
  type ImportSpaltenResponse,
  type ImportMappingVorlage,
  type ImportZeileAktion,
} from '../../api/client'
import { useMxAuto } from '../../hooks/useAnsicht'

type ImportTyp = 'kunden' | 'lieferanten' | 'artikel' | 'gemischt'
type Schritt = 1 | 2 | 3 | 4

// Zielfelder je Typ
const ZIELFELDER: Record<ImportTyp, { key: string; label: string }[]> = {
  kunden: [
    { key: 'firmenname', label: 'Firmenname' },
    { key: 'vorname', label: 'Vorname' },
    { key: 'nachname', label: 'Nachname' },
    { key: 'strasse', label: 'Straße' },
    { key: 'hausnummer', label: 'Hausnummer' },
    { key: 'plz', label: 'PLZ' },
    { key: 'ort', label: 'Ort' },
    { key: 'land', label: 'Land' },
    { key: 'email', label: 'E-Mail' },
    { key: 'telefon', label: 'Telefon' },
    { key: 'ust_idnr', label: 'USt-IdNr.' },
    { key: 'kundennummer', label: 'Kundennummer' },
    { key: 'z_hd', label: 'Zu Händen' },
    { key: 'notizen', label: 'Notizen' },
    { key: 'skonto_prozent', label: 'Skonto %' },
    { key: 'skonto_tage', label: 'Skonto Tage' },
  ],
  lieferanten: [
    { key: 'firmenname', label: 'Firmenname' },
    { key: 'vorname', label: 'Vorname' },
    { key: 'nachname', label: 'Nachname' },
    { key: 'strasse', label: 'Straße' },
    { key: 'hausnummer', label: 'Hausnummer' },
    { key: 'plz', label: 'PLZ' },
    { key: 'ort', label: 'Ort' },
    { key: 'land', label: 'Land' },
    { key: 'email', label: 'E-Mail' },
    { key: 'telefon', label: 'Telefon' },
    { key: 'ust_idnr', label: 'USt-IdNr.' },
    { key: 'lieferantennummer', label: 'Lieferantennummer' },
    { key: 'z_hd', label: 'Zu Händen' },
    { key: 'notizen', label: 'Notizen' },
  ],
  artikel: [
    { key: 'typ', label: 'Typ (artikel/dienstleistung/fremdleistung)' },
    { key: 'bezeichnung', label: 'Bezeichnung' },
    { key: 'einheit', label: 'Einheit' },
    { key: 'steuersatz_prozent', label: 'Steuersatz %' },
    { key: 'vk_brutto', label: 'VK Brutto' },
    { key: 'ek_netto', label: 'EK Netto' },
    { key: 'artikelcode', label: 'Artikelcode' },
    { key: 'hersteller', label: 'Hersteller' },
    { key: 'beschreibung', label: 'Beschreibung' },
  ],
  gemischt: [
    { key: 'firmenname', label: 'Firmenname' },
    { key: 'vorname', label: 'Vorname' },
    { key: 'nachname', label: 'Nachname' },
    { key: 'strasse', label: 'Straße' },
    { key: 'hausnummer', label: 'Hausnummer' },
    { key: 'plz', label: 'PLZ' },
    { key: 'ort', label: 'Ort' },
    { key: 'land', label: 'Land' },
    { key: 'email', label: 'E-Mail' },
    { key: 'telefon', label: 'Telefon' },
    { key: 'ust_idnr', label: 'USt-IdNr.' },
    { key: 'kundennummer', label: 'Kunden-/Lieferantennummer' },
    { key: 'z_hd', label: 'Zu Händen' },
    { key: 'notizen', label: 'Notizen' },
  ],
}

const TYP_LABELS: Record<ImportTyp, string> = {
  kunden: 'Kunden',
  lieferanten: 'Lieferanten',
  artikel: 'Artikel',
  gemischt: 'Gemischt (Kunden + Lieferanten)',
}

function StatusBadge({ status }: { status: ImportVorschauZeile['status'] }) {
  if (status === 'neu') return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">Neu</span>
  if (status === 'duplikat') return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">Duplikat</span>
  return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">Fehler</span>
}

// ---------------------------------------------------------------------------
// Import-Flow (ein Tab)
// ---------------------------------------------------------------------------

function ImportFlow({ typ }: { typ: ImportTyp }) {
  const [schritt, setSchritt] = useState<Schritt>(1)
  const [datei, setDatei] = useState<File | null>(null)
  const [hatHeader, setHatHeader] = useState(true)
  const [typErkennungAktiv, setTypErkennungAktiv] = useState(false)
  const [spaltenInfo, setSpaltenInfo] = useState<ImportSpaltenResponse | null>(null)
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const [vorschauZeilen, setVorschauZeilen] = useState<ImportVorschauZeile[]>([])
  const [aktionen, setAktionen] = useState<Record<number, ImportZeileAktion['aktion']>>({})
  const [ergebnis, setErgebnis] = useState<{ importiert: number; aktualisiert: number; ignoriert: number; fehler: { zeile: number; fehler: string }[] } | null>(null)
  const [mappingName, setMappingName] = useState('')
  const [mappingSpeichernOffen, setMappingSpeichernOffen] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)
  const dateiRef = useRef<HTMLInputElement>(null)

  const { data: mappingVorlagen = [] } = useQuery({
    queryKey: ['mapping-vorlagen'],
    queryFn: getMappingVorlagen,
  })

  const felder = ZIELFELDER[typ]

  // Schritt 1 → 2: Spalten laden
  async function weiterZuMapping() {
    if (!datei) return
    setFehler(null)
    try {
      const info = await getSpalten(datei, hatHeader)
      setSpaltenInfo(info)
      // Standard-Mapping: gleiche Namen soweit möglich
      const autoMapping: Record<string, string> = {}
      info.spaltennamen.forEach(sp => {
        const match = felder.find(f => f.key === sp.toLowerCase() || f.label.toLowerCase() === sp.toLowerCase())
        autoMapping[sp] = match ? match.key : '__ignorieren__'
      })
      setMapping(autoMapping)
      setSchritt(2)
    } catch (e: any) {
      setFehler(e.message)
    }
  }

  // Schritt 2 → 3: Vorschau laden
  async function weiterZuVorschau() {
    if (!datei || !spaltenInfo) return
    setFehler(null)
    try {
      const zeilen = await getImportVorschau(typ, datei, hatHeader, JSON.stringify(mapping), typErkennungAktiv)
      setVorschauZeilen(zeilen)
      // Standard-Aktion: neu → übernehmen, duplikat → ignorieren, fehler → ignorieren
      const std: Record<number, ImportZeileAktion['aktion']> = {}
      zeilen.forEach(z => { std[z.zeile] = z.status === 'neu' ? 'übernehmen' : 'ignorieren' })
      setAktionen(std)
      setSchritt(3)
    } catch (e: any) {
      setFehler(e.message)
    }
  }

  // Schritt 3 → 4: Import
  async function importStarten() {
    setFehler(null)
    try {
      const zeilen: ImportZeileAktion[] = vorschauZeilen.map(z => ({
        zeile: z.zeile,
        daten: z.daten,
        aktion: aktionen[z.zeile] ?? 'ignorieren',
        duplikat_id: z.duplikat_id,
      }))
      const res = await importDurchfuehren(typ, zeilen)
      setErgebnis(res)
      setSchritt(4)
    } catch (e: any) {
      setFehler(e.message)
    }
  }

  async function mappingSpeichern() {
    if (!mappingName.trim()) return
    await saveMappingVorlage({
      name: mappingName.trim(),
      typ,
      hat_header: hatHeader,
      mapping_json: JSON.stringify(mapping),
      typ_erkennung_aktiv: typErkennungAktiv,
    })
    setMappingSpeichernOffen(false)
    setMappingName('')
  }

  function vorlageAnwenden(v: ImportMappingVorlage) {
    try {
      setMapping(JSON.parse(v.mapping_json))
      setHatHeader(v.hat_header)
      setTypErkennungAktiv(v.typ_erkennung_aktiv)
    } catch {}
  }

  async function musterDownload() {
    const blob = await getMusterCsv(typ === 'gemischt' ? 'kunden' : typ)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `muster_${typ === 'gemischt' ? 'kunden' : typ}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  function neuStarten() {
    setSchritt(1); setDatei(null); setSpaltenInfo(null)
    setMapping({}); setVorschauZeilen([]); setAktionen({}); setErgebnis(null); setFehler(null)
  }

  return (
    <div className="space-y-6">
      {/* Fortschrittsanzeige */}
      <div className="flex items-center gap-2 text-sm">
        {(['Datei', 'Feldzuordnung', 'Vorschau', 'Ergebnis'] as const).map((label, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${schritt === i + 1 ? 'bg-blue-600 text-white' : schritt > i + 1 ? 'bg-green-500 text-white' : 'bg-slate-200 dark:bg-slate-700 text-slate-500'}`}>{i + 1}</span>
            <span className={schritt === i + 1 ? 'font-medium text-slate-900 dark:text-slate-100' : 'text-slate-400 dark:text-slate-500'}>{label}</span>
            {i < 3 && <span className="text-slate-300 dark:text-slate-600">›</span>}
          </div>
        ))}
      </div>

      {fehler && (
        <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-sm">{fehler}</div>
      )}

      {/* Schritt 1: Datei */}
      {schritt === 1 && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <button onClick={musterDownload} className="inline-flex items-center gap-2 px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300">
              <span className="material-symbols-outlined text-base">download</span>Muster-CSV herunterladen
            </button>
          </div>

          <div
            onClick={() => dateiRef.current?.click()}
            onDragOver={e => e.preventDefault()}
            onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) setDatei(f) }}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${datei ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20' : 'border-slate-300 dark:border-slate-600 hover:border-blue-400'}`}
          >
            <input ref={dateiRef} type="file" accept=".csv,.txt" className="hidden" onChange={e => setDatei(e.target.files?.[0] ?? null)} />
            <span className="material-symbols-outlined text-4xl text-slate-400 dark:text-slate-500">upload_file</span>
            {datei ? (
              <p className="mt-2 text-sm font-medium text-blue-700 dark:text-blue-300">{datei.name}</p>
            ) : (
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">CSV-Datei hier ablegen oder klicken</p>
            )}
          </div>

          <div className="flex items-center gap-6">
            <label className="flex items-center gap-2 cursor-pointer text-sm text-slate-700 dark:text-slate-300">
              <input type="checkbox" checked={hatHeader} onChange={e => setHatHeader(e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-blue-600" />
              Erste Zeile ist Kopfzeile
            </label>
            {typ === 'gemischt' && (
              <label className="flex items-center gap-2 cursor-pointer text-sm text-slate-700 dark:text-slate-300">
                <input type="checkbox" checked={typErkennungAktiv} onChange={e => setTypErkennungAktiv(e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-blue-600" />
                Typ per Nummer erkennen (10xxx = Kunde, 70xxx = Lieferant)
              </label>
            )}
          </div>

          {mappingVorlagen.filter(v => v.typ === typ || v.typ === 'gemischt').length > 0 && (
            <div className="space-y-1">
              <p className="text-xs text-slate-500 dark:text-slate-400">Gespeichertes Mapping laden:</p>
              <div className="flex flex-wrap gap-2">
                {mappingVorlagen.filter(v => v.typ === typ || v.typ === 'gemischt').map(v => (
                  <button key={v.id} onClick={() => vorlageAnwenden(v)} className="px-3 py-1 text-xs rounded-full border border-slate-300 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300">
                    {v.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          <button
            onClick={weiterZuMapping}
            disabled={!datei}
            className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg disabled:opacity-50"
          >
            Weiter zur Feldzuordnung
          </button>
        </div>
      )}

      {/* Schritt 2: Feldzuordnung */}
      {schritt === 2 && spaltenInfo && (
        <div className="space-y-4">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide border-b border-slate-200 dark:border-slate-700">
                  <th className="pb-2 pr-4">Spalte in CSV</th>
                  <th className="pb-2 pr-4">Beispielwerte</th>
                  <th className="pb-2">Zielfeld</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {spaltenInfo.spaltennamen.map((sp, i) => (
                  <tr key={sp}>
                    <td className="py-2 pr-4 font-medium text-slate-700 dark:text-slate-300">{sp}</td>
                    <td className="py-2 pr-4 text-slate-400 dark:text-slate-500 text-xs">
                      {spaltenInfo.vorschau.slice(0, 3).map(row => row[i]).filter(Boolean).join(' · ')}
                    </td>
                    <td className="py-2">
                      <select
                        value={mapping[sp] ?? '__ignorieren__'}
                        onChange={e => setMapping(m => ({ ...m, [sp]: e.target.value }))}
                        className="text-sm border border-slate-300 dark:border-slate-600 rounded px-2 py-1 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                      >
                        <option value="__ignorieren__">— ignorieren —</option>
                        {felder.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <button onClick={() => setSchritt(1)} className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300">
              Zurück
            </button>
            <button onClick={weiterZuVorschau} className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg">
              Weiter zur Vorschau
            </button>
            <button onClick={() => setMappingSpeichernOffen(true)} className="px-3 py-2 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 underline">
              Mapping speichern
            </button>
          </div>

          {mappingSpeichernOffen && (
            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="Name für dieses Mapping…"
                value={mappingName}
                onChange={e => setMappingName(e.target.value)}
                className="text-sm border border-slate-300 dark:border-slate-600 rounded px-3 py-1.5 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300"
              />
              <button onClick={mappingSpeichern} className="px-3 py-1.5 bg-slate-700 text-white text-sm rounded-lg hover:bg-slate-800">
                Speichern
              </button>
              <button onClick={() => setMappingSpeichernOffen(false)} className="text-sm text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
                Abbrechen
              </button>
            </div>
          )}
        </div>
      )}

      {/* Schritt 3: Vorschau */}
      {schritt === 3 && (
        <div className="space-y-4">
          <div className="flex items-center gap-4 text-sm text-slate-500 dark:text-slate-400">
            <span className="text-green-600 dark:text-green-400 font-medium">{vorschauZeilen.filter(z => z.status === 'neu').length} Neu</span>
            <span className="text-yellow-600 dark:text-yellow-400 font-medium">{vorschauZeilen.filter(z => z.status === 'duplikat').length} Duplikat</span>
            <span className="text-red-600 dark:text-red-400 font-medium">{vorschauZeilen.filter(z => z.status === 'fehler').length} Fehler</span>
          </div>

          <div className="overflow-x-auto max-h-96">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-white dark:bg-slate-900">
                <tr className="text-left font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide border-b border-slate-200 dark:border-slate-700">
                  <th className="pb-2 pr-3">Zeile</th>
                  <th className="pb-2 pr-3">Status</th>
                  <th className="pb-2 pr-3">Aktion</th>
                  <th className="pb-2">Daten</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {vorschauZeilen.map(z => (
                  <tr key={z.zeile}>
                    <td className="py-2 pr-3 text-slate-400">{z.zeile}</td>
                    <td className="py-2 pr-3"><StatusBadge status={z.status} /></td>
                    <td className="py-2 pr-3">
                      {z.status === 'fehler' ? (
                        <span className="text-red-500 dark:text-red-400">{z.fehler}</span>
                      ) : (
                        <select
                          value={aktionen[z.zeile] ?? 'ignorieren'}
                          onChange={e => setAktionen(a => ({ ...a, [z.zeile]: e.target.value as ImportZeileAktion['aktion'] }))}
                          className="border border-slate-300 dark:border-slate-600 rounded px-1.5 py-0.5 text-xs bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                        >
                          <option value="übernehmen">Übernehmen</option>
                          <option value="ignorieren">Ignorieren</option>
                          {z.status === 'duplikat' && <option value="überschreiben">Überschreiben</option>}
                        </select>
                      )}
                    </td>
                    <td className="py-2 text-slate-600 dark:text-slate-400">
                      {Object.entries(z.daten).filter(([k]) => !k.startsWith('__')).slice(0, 4).map(([k, v]) => v ? `${k}: ${v}` : null).filter(Boolean).join(' · ')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center gap-3">
            <button onClick={() => setSchritt(2)} className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300">
              Zurück
            </button>
            <button
              onClick={importStarten}
              disabled={vorschauZeilen.filter(z => aktionen[z.zeile] === 'übernehmen' || aktionen[z.zeile] === 'überschreiben').length === 0}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg disabled:opacity-50"
            >
              {vorschauZeilen.filter(z => aktionen[z.zeile] !== 'ignorieren' && z.status !== 'fehler').length} Datensätze importieren
            </button>
          </div>
        </div>
      )}

      {/* Schritt 4: Ergebnis */}
      {schritt === 4 && ergebnis && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-green-50 dark:bg-green-900/20 space-y-2">
            <p className="font-semibold text-green-800 dark:text-green-300">Import abgeschlossen</p>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div className="text-center">
                <p className="text-2xl font-bold text-green-700 dark:text-green-300">{ergebnis.importiert}</p>
                <p className="text-slate-600 dark:text-slate-400">Importiert</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-blue-700 dark:text-blue-300">{ergebnis.aktualisiert}</p>
                <p className="text-slate-600 dark:text-slate-400">Aktualisiert</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-slate-500">{ergebnis.ignoriert}</p>
                <p className="text-slate-600 dark:text-slate-400">Ignoriert</p>
              </div>
            </div>
          </div>

          {ergebnis.fehler.length > 0 && (
            <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 space-y-1">
              <p className="text-sm font-medium text-red-700 dark:text-red-400">{ergebnis.fehler.length} Fehler:</p>
              {ergebnis.fehler.map(f => (
                <p key={f.zeile} className="text-xs text-red-600 dark:text-red-400">Zeile {f.zeile}: {f.fehler}</p>
              ))}
            </div>
          )}

          <button onClick={neuStarten} className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300">
            Weiteren Import starten
          </button>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Mapping-Vorlagen verwalten
// ---------------------------------------------------------------------------

function MappingVorlagenListe() {
  const { data: vorlagen = [], refetch } = useQuery({
    queryKey: ['mapping-vorlagen'],
    queryFn: getMappingVorlagen,
  })

  if (vorlagen.length === 0) return null

  return (
    <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
      <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">Gespeicherte Mappings</p>
      <div className="space-y-1">
        {vorlagen.map(v => (
          <div key={v.id} className="flex items-center justify-between text-sm">
            <span className="text-slate-700 dark:text-slate-300">{v.name} <span className="text-xs text-slate-400">({TYP_LABELS[v.typ as ImportTyp] ?? v.typ})</span></span>
            <button
              onClick={async () => { await deleteMappingVorlage(v.id); refetch() }}
              className="text-xs text-red-400 hover:text-red-600 dark:hover:text-red-300"
            >
              Löschen
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Hauptseite
// ---------------------------------------------------------------------------

const TABS: { id: ImportTyp; label: string }[] = [
  { id: 'kunden', label: 'Kunden' },
  { id: 'lieferanten', label: 'Lieferanten' },
  { id: 'artikel', label: 'Artikel' },
  { id: 'gemischt', label: 'Gemischt' },
]

export function DatensmigrationsPage() {
  const mxAuto = useMxAuto()
  const [aktuellerTab, setAktuellerTab] = useState<ImportTyp>('kunden')

  return (
    <div className={`p-6 space-y-6 ${mxAuto}`}>
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Datenübernahme</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Kunden, Lieferanten und Artikel per CSV aus anderen Programmen importieren.
          Nach der Übernahme unter Einstellungen → Unternehmen → Artikel deaktivieren.
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200 dark:border-slate-700">
        <nav className="flex gap-1">
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setAktuellerTab(t.id)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                aktuellerTab === t.id
                  ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
        <ImportFlow key={aktuellerTab} typ={aktuellerTab} />
        <MappingVorlagenListe />
      </div>
    </div>
  )
}
