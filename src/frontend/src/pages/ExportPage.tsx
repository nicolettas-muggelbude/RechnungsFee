import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { downloadGobdExport, getUnternehmen } from '../api/client'

const AKTUELLES_JAHR = new Date().getFullYear()
const JAHRE = Array.from({ length: 5 }, (_, i) => AKTUELLES_JAHR - i)

export function ExportPage() {
  const [jahr, setJahr] = useState(AKTUELLES_JAHR)
  const [laedt, setLaedt] = useState(false)
  const [erfolg, setErfolg] = useState<string | null>(null)
  const [fehler, setFehler] = useState<string | null>(null)
  const navigate = useNavigate()

  const { data: unternehmen } = useQuery({
    queryKey: ['unternehmen'],
    queryFn: getUnternehmen,
    staleTime: 1000 * 60 * 10,
  })

  async function handleExport() {
    setLaedt(true)
    setErfolg(null)
    setFehler(null)
    try {
      const filename = await downloadGobdExport(jahr)
      setErfolg(filename)
    } catch (e: any) {
      setFehler(e?.message ?? 'Unbekannter Fehler')
    } finally {
      setLaedt(false)
    }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Exporte</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
          Daten für Steuerberater, Betriebsprüfung und Archivierung exportieren.
        </p>
      </div>

      {/* Anlage EKS – nur bei Transferleistungen */}
      {unternehmen?.bezieht_transferleistungen && (
        <button
          onClick={() => navigate('/eks')}
          className="w-full text-left bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden hover:border-blue-400 dark:hover:border-blue-600 transition-colors group"
        >
          <div className="bg-blue-600 px-6 py-4 flex items-center justify-between">
            <div>
              <h2 className="text-white font-bold text-lg">Anlage EKS</h2>
              <p className="text-blue-100 text-sm mt-0.5">
                Einkommenserklärung für Selbstständige (Jobcenter / Bürgergeld)
              </p>
            </div>
            <span className="text-white text-2xl opacity-70 group-hover:opacity-100 transition-opacity">→</span>
          </div>
          <div className="px-6 py-4 flex gap-6 text-sm text-slate-600 dark:text-slate-300">
            <span>📄 Abschließend – monatlich aus Journaldaten</span>
            <span>📊 Vorläufig – Prognose aus Vorjahr</span>
          </div>
        </button>
      )}

      {/* UStVA – nur für Regelbesteuerte */}
      {!unternehmen?.ist_kleinunternehmer && (
        <button
          onClick={() => navigate('/ustva')}
          className="w-full text-left bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden hover:border-blue-400 dark:hover:border-blue-600 transition-colors group"
        >
          <div className="bg-blue-600 px-6 py-4 flex items-center justify-between">
            <div>
              <h2 className="text-white font-bold text-lg">UStVA – Umsatzsteuer-Voranmeldung</h2>
              <p className="text-blue-100 text-sm mt-0.5">
                Kennziffern aus Journalbuchungen berechnen und als Anzeigehilfe für ELSTER ausgeben
              </p>
            </div>
            <span className="text-white text-2xl opacity-70 group-hover:opacity-100 transition-opacity">→</span>
          </div>
          <div className="px-6 py-4 flex gap-6 text-sm text-slate-600 dark:text-slate-300">
            <span>🧮 KZ 81/86 Umsätze · KZ 66 Vorsteuer · Zahllast</span>
            <span>📄 PDF-Anzeigehilfe für ELSTER</span>
          </div>
        </button>
      )}

      {/* ZM – nur für Regelbesteuerte */}
      {!unternehmen?.ist_kleinunternehmer && (
        <button
          onClick={() => navigate('/zm')}
          className="w-full text-left bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden hover:border-blue-400 dark:hover:border-blue-600 transition-colors group"
        >
          <div className="bg-blue-600 px-6 py-4 flex items-center justify-between">
            <div>
              <h2 className="text-white font-bold text-lg">ZM – Zusammenfassende Meldung</h2>
              <p className="text-blue-100 text-sm mt-0.5">
                §18a UStG – Meldepflicht für innergemeinschaftliche Lieferungen &amp; Dienstleistungen
              </p>
            </div>
            <span className="text-white text-2xl opacity-70 group-hover:opacity-100 transition-opacity">→</span>
          </div>
          <div className="px-6 py-4 flex gap-6 text-sm text-slate-600 dark:text-slate-300">
            <span>🇪🇺 ig. Lieferungen (L) · §13b Dienstleistungen (D)</span>
            <span>📋 Quartal / Monat · Frist 25. Folgemonat</span>
          </div>
        </button>
      )}

      {/* GoBD-Export-Card */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
        <div className="bg-blue-600 px-6 py-4">
          <h2 className="text-white font-bold text-lg">GoBD-Export (Betriebsprüfung)</h2>
          <p className="text-blue-100 text-sm mt-0.5">
            Vollständiger Datenexport nach GoBD für die digitale Betriebsprüfung (Z3-Datenträgerüberlassung)
          </p>
        </div>

        <div className="p-6 space-y-5">
          {/* Jahresauswahl + Button */}
          <div className="flex items-end gap-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700 dark:text-slate-200" htmlFor="export-jahr">
                Wirtschaftsjahr
              </label>
              <select
                id="export-jahr"
                value={jahr}
                onChange={(e) => setJahr(Number(e.target.value))}
                className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
              >
                {JAHRE.map((j) => (
                  <option key={j} value={j}>{j}</option>
                ))}
              </select>
            </div>
            <button
              onClick={handleExport}
              disabled={laedt}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium text-sm px-5 py-2 rounded-lg transition-colors"
            >
              {laedt ? (
                <>
                  <span className="animate-spin">⏳</span>
                  Wird erstellt…
                </>
              ) : (
                <>
                  <span>📦</span>
                  Export erstellen
                </>
              )}
            </button>
          </div>

          {/* Erfolgs-/Fehlermeldung */}
          {erfolg && (
            <div className="flex items-start gap-3 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg px-4 py-3">
              <span className="text-green-600 dark:text-green-400 shrink-0 mt-0.5">✓</span>
              <div className="text-sm text-green-800 dark:text-green-300">
                <p className="font-medium">Export erfolgreich erstellt</p>
                <p className="mt-0.5 font-mono text-xs">{erfolg}</p>
                <p className="mt-1 text-xs opacity-75">Die Datei wurde in deinen Downloads-Ordner gespeichert.</p>
              </div>
            </div>
          )}
          {fehler && (
            <div className="flex items-start gap-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3">
              <span className="text-red-600 dark:text-red-400 shrink-0 mt-0.5">✗</span>
              <p className="text-sm text-red-800 dark:text-red-300">{fehler}</p>
            </div>
          )}

          {/* Infobox: enthaltene Dateien */}
          <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg p-4 space-y-3">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Das ZIP-Archiv enthält:</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {[
                { datei: 'journal.csv', beschreibung: 'Alle Journaleinträge (IDEA-kompatibel)' },
                { datei: 'tagesabschluesse.csv',   beschreibung: 'Alle Tagesabschlüsse mit Kennzahlen' },
                { datei: 'kategorien.csv',          beschreibung: 'Kategorie-Stammdaten (SKR03/04/49)' },
                { datei: 'kunden.csv',              beschreibung: 'Kunden-Stammdaten' },
                { datei: 'lieferanten.csv',         beschreibung: 'Lieferanten-Stammdaten' },
                { datei: 'integritaetspruefung.csv',beschreibung: 'SHA-256-Signaturprüfung aller Datensätze' },
                { datei: 'index.xml',               beschreibung: 'GDPdU-Beschreibungsdatei (XML)' },
                { datei: 'gobd_pruefbericht.pdf',   beschreibung: 'Zusammenfassender Prüfbericht (PDF)' },
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

          {/* GoBD-Hinweis */}
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
    </div>
  )
}
