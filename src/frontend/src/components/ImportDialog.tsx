import { useState, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  getMusterCsv,
  getSpalten,
  getImportVorschau,
  importDurchfuehren,
  getMappingVorlagen,
  saveMappingVorlage,
  type ImportVorschauZeile,
  type ImportSpaltenResponse,
  type ImportMappingVorlage,
  type ImportZeileAktion,
} from '../api/client'

type ImportTyp = 'kunden' | 'lieferanten' | 'artikel'
type Schritt = 1 | 2 | 3 | 4

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
}

function StatusBadge({ status }: { status: ImportVorschauZeile['status'] }) {
  if (status === 'neu') return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">Neu</span>
  if (status === 'duplikat') return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">Duplikat</span>
  return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">Fehler</span>
}

interface ImportDialogProps {
  typ: ImportTyp
  onClose: () => void
}

export function ImportDialog({ typ, onClose }: ImportDialogProps) {
  const [schritt, setSchritt] = useState<Schritt>(1)
  const [datei, setDatei] = useState<File | null>(null)
  const [hatHeader, setHatHeader] = useState(true)
  const [spaltenInfo, setSpaltenInfo] = useState<ImportSpaltenResponse | null>(null)
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const [vorschauZeilen, setVorschauZeilen] = useState<ImportVorschauZeile[]>([])
  const [aktionen, setAktionen] = useState<Record<number, ImportZeileAktion['aktion']>>({})
  const [ergebnis, setErgebnis] = useState<{ importiert: number; aktualisiert: number; ignoriert: number; fehler: { zeile: number; fehler: string }[] } | null>(null)
  const [mappingName, setMappingName] = useState('')
  const [mappingSpeichernOffen, setMappingSpeichernOffen] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)
  const dateiRef = useRef<HTMLInputElement>(null)

  const felder = ZIELFELDER[typ]

  const { data: mappingVorlagen = [] } = useQuery({
    queryKey: ['mapping-vorlagen'],
    queryFn: getMappingVorlagen,
  })

  async function weiterZuMapping() {
    if (!datei) return
    setFehler(null)
    try {
      const info = await getSpalten(datei, hatHeader)
      setSpaltenInfo(info)
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

  async function weiterZuVorschau() {
    if (!datei || !spaltenInfo) return
    setFehler(null)
    try {
      const zeilen = await getImportVorschau(typ, datei, hatHeader, JSON.stringify(mapping), false)
      setVorschauZeilen(zeilen)
      const std: Record<number, ImportZeileAktion['aktion']> = {}
      zeilen.forEach(z => { std[z.zeile] = z.status === 'neu' ? 'übernehmen' : 'ignorieren' })
      setAktionen(std)
      setSchritt(3)
    } catch (e: any) {
      setFehler(e.message)
    }
  }

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
    await saveMappingVorlage({ name: mappingName.trim(), typ, hat_header: hatHeader, mapping_json: JSON.stringify(mapping), typ_erkennung_aktiv: false })
    setMappingSpeichernOffen(false)
    setMappingName('')
  }

  function vorlageAnwenden(v: ImportMappingVorlage) {
    try { setMapping(JSON.parse(v.mapping_json)); setHatHeader(v.hat_header) } catch {}
  }

  async function musterDownload() {
    const blob = await getMusterCsv(typ)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = `muster_${typ}.csv`; a.click()
    URL.revokeObjectURL(url)
  }

  const schrittLabels = ['Datei', 'Feldzuordnung', 'Vorschau', 'Ergebnis']

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between shrink-0">
          <div>
            <h2 className="font-semibold text-slate-900 dark:text-slate-100">CSV importieren</h2>
            <div className="flex items-center gap-2 mt-1">
              {schrittLabels.map((label, i) => (
                <div key={i} className="flex items-center gap-1.5 text-xs">
                  <span className={`w-5 h-5 rounded-full flex items-center justify-center font-bold ${schritt === i + 1 ? 'bg-blue-600 text-white' : schritt > i + 1 ? 'bg-green-500 text-white' : 'bg-slate-200 dark:bg-slate-700 text-slate-400'}`}>{i + 1}</span>
                  <span className={schritt === i + 1 ? 'text-slate-700 dark:text-slate-200' : 'text-slate-400 dark:text-slate-500'}>{label}</span>
                  {i < 3 && <span className="text-slate-300 dark:text-slate-600">›</span>}
                </div>
              ))}
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-2xl leading-none">×</button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {fehler && <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-sm">{fehler}</div>}

          {/* Schritt 1 */}
          {schritt === 1 && (
            <div className="space-y-4">
              <button onClick={musterDownload} className="inline-flex items-center gap-2 px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300">
                <span className="material-symbols-outlined text-base">download</span>Muster-CSV herunterladen
              </button>
              <div
                onClick={() => dateiRef.current?.click()}
                onDragOver={e => e.preventDefault()}
                onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) setDatei(f) }}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${datei ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20' : 'border-slate-300 dark:border-slate-600 hover:border-blue-400'}`}
              >
                <input ref={dateiRef} type="file" accept=".csv,.txt" className="hidden" onChange={e => setDatei(e.target.files?.[0] ?? null)} />
                <span className="material-symbols-outlined text-3xl text-slate-400">upload_file</span>
                {datei ? <p className="mt-1 text-sm font-medium text-blue-700 dark:text-blue-300">{datei.name}</p>
                       : <p className="mt-1 text-sm text-slate-400">CSV-Datei ablegen oder klicken</p>}
              </div>
              <label className="flex items-center gap-2 cursor-pointer text-sm text-slate-700 dark:text-slate-300">
                <input type="checkbox" checked={hatHeader} onChange={e => setHatHeader(e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-blue-600" />
                Erste Zeile ist Kopfzeile
              </label>
              {mappingVorlagen.filter(v => v.typ === typ).length > 0 && (
                <div className="space-y-1">
                  <p className="text-xs text-slate-500 dark:text-slate-400">Gespeichertes Mapping laden:</p>
                  <div className="flex flex-wrap gap-2">
                    {mappingVorlagen.filter(v => v.typ === typ).map(v => (
                      <button key={v.id} onClick={() => vorlageAnwenden(v)} className="px-3 py-1 text-xs rounded-full border border-slate-300 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300">{v.name}</button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Schritt 2 */}
          {schritt === 2 && spaltenInfo && (
            <div className="space-y-3">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase border-b border-slate-200 dark:border-slate-700">
                    <th className="pb-2 pr-4">Spalte in CSV</th>
                    <th className="pb-2 pr-4">Beispielwerte</th>
                    <th className="pb-2">Zielfeld</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {spaltenInfo.spaltennamen.map((sp, i) => (
                    <tr key={sp}>
                      <td className="py-1.5 pr-4 font-medium text-slate-700 dark:text-slate-300 text-xs">{sp}</td>
                      <td className="py-1.5 pr-4 text-xs text-slate-400 dark:text-slate-500">{spaltenInfo.vorschau.slice(0, 2).map(r => r[i]).filter(Boolean).join(' · ')}</td>
                      <td className="py-1.5">
                        <select value={mapping[sp] ?? '__ignorieren__'} onChange={e => setMapping(m => ({ ...m, [sp]: e.target.value }))}
                          className="text-xs border border-slate-300 dark:border-slate-600 rounded px-1.5 py-0.5 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                          <option value="__ignorieren__">— ignorieren —</option>
                          {felder.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {mappingSpeichernOffen ? (
                <div className="flex items-center gap-2">
                  <input type="text" placeholder="Name für Mapping…" value={mappingName} onChange={e => setMappingName(e.target.value)}
                    className="text-sm border border-slate-300 dark:border-slate-600 rounded px-2 py-1 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300" />
                  <button onClick={mappingSpeichern} className="px-3 py-1 bg-slate-700 text-white text-sm rounded hover:bg-slate-800">Speichern</button>
                  <button onClick={() => setMappingSpeichernOffen(false)} className="text-sm text-slate-400 hover:text-slate-600">Abbrechen</button>
                </div>
              ) : (
                <button onClick={() => setMappingSpeichernOffen(true)} className="text-xs text-slate-500 dark:text-slate-400 underline hover:text-slate-700 dark:hover:text-slate-200">
                  Mapping für spätere Imports speichern
                </button>
              )}
            </div>
          )}

          {/* Schritt 3 */}
          {schritt === 3 && (
            <div className="space-y-3">
              <div className="flex items-center gap-4 text-sm">
                <span className="text-green-600 dark:text-green-400 font-medium">{vorschauZeilen.filter(z => z.status === 'neu').length} Neu</span>
                <span className="text-yellow-600 dark:text-yellow-400 font-medium">{vorschauZeilen.filter(z => z.status === 'duplikat').length} Duplikat</span>
                <span className="text-red-600 dark:text-red-400 font-medium">{vorschauZeilen.filter(z => z.status === 'fehler').length} Fehler</span>
              </div>
              <div className="max-h-64 overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-white dark:bg-slate-900">
                    <tr className="text-left font-semibold text-slate-400 uppercase border-b border-slate-200 dark:border-slate-700">
                      <th className="pb-1.5 pr-3">Z.</th><th className="pb-1.5 pr-3">Status</th><th className="pb-1.5 pr-3">Aktion</th><th className="pb-1.5">Daten</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {vorschauZeilen.map(z => (
                      <tr key={z.zeile}>
                        <td className="py-1.5 pr-3 text-slate-400">{z.zeile}</td>
                        <td className="py-1.5 pr-3"><StatusBadge status={z.status} /></td>
                        <td className="py-1.5 pr-3">
                          {z.status === 'fehler' ? <span className="text-red-500 text-xs">{z.fehler}</span> : (
                            <select value={aktionen[z.zeile] ?? 'ignorieren'} onChange={e => setAktionen(a => ({ ...a, [z.zeile]: e.target.value as ImportZeileAktion['aktion'] }))}
                              className="border border-slate-300 dark:border-slate-600 rounded px-1.5 py-0.5 text-xs bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                              <option value="übernehmen">Übernehmen</option>
                              <option value="ignorieren">Ignorieren</option>
                              {z.status === 'duplikat' && <option value="überschreiben">Überschreiben</option>}
                            </select>
                          )}
                        </td>
                        <td className="py-1.5 text-slate-500 dark:text-slate-400">
                          {Object.entries(z.daten).filter(([k]) => !k.startsWith('__')).slice(0, 3).map(([, v]) => v).filter(Boolean).join(' · ')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Schritt 4 */}
          {schritt === 4 && ergebnis && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-green-50 dark:bg-green-900/20">
                <p className="font-semibold text-green-800 dark:text-green-300 mb-3">Import abgeschlossen</p>
                <div className="grid grid-cols-3 gap-4 text-center text-sm">
                  <div><p className="text-2xl font-bold text-green-700 dark:text-green-300">{ergebnis.importiert}</p><p className="text-slate-500">Importiert</p></div>
                  <div><p className="text-2xl font-bold text-blue-700 dark:text-blue-300">{ergebnis.aktualisiert}</p><p className="text-slate-500">Aktualisiert</p></div>
                  <div><p className="text-2xl font-bold text-slate-500">{ergebnis.ignoriert}</p><p className="text-slate-500">Ignoriert</p></div>
                </div>
              </div>
              {ergebnis.fehler.length > 0 && (
                <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 space-y-1">
                  {ergebnis.fehler.map(f => <p key={f.zeile} className="text-xs text-red-600 dark:text-red-400">Zeile {f.zeile}: {f.fehler}</p>)}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between shrink-0">
          <button onClick={onClose} className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400">
            {schritt === 4 ? 'Schließen' : 'Abbrechen'}
          </button>
          <div className="flex items-center gap-2">
            {schritt === 2 && <button onClick={() => setSchritt(1)} className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400">Zurück</button>}
            {schritt === 3 && <button onClick={() => setSchritt(2)} className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400">Zurück</button>}
            {schritt === 1 && <button onClick={weiterZuMapping} disabled={!datei} className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg disabled:opacity-50">Weiter</button>}
            {schritt === 2 && <button onClick={weiterZuVorschau} className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg">Weiter zur Vorschau</button>}
            {schritt === 3 && (
              <button onClick={importStarten} disabled={vorschauZeilen.filter(z => aktionen[z.zeile] !== 'ignorieren' && z.status !== 'fehler').length === 0}
                className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg disabled:opacity-50">
                {vorschauZeilen.filter(z => aktionen[z.zeile] !== 'ignorieren' && z.status !== 'fehler').length} Datensätze importieren
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
