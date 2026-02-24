import { useState } from 'react'
import { downloadGobdExport } from '../api/client'

const AKTUELLES_JAHR = new Date().getFullYear()
const JAHRE = Array.from({ length: 5 }, (_, i) => AKTUELLES_JAHR - i)

export function ExportPage() {
  const [jahr, setJahr] = useState(AKTUELLES_JAHR)
  const [laedt, setLaedt] = useState(false)

  function handleExport() {
    setLaedt(true)
    try {
      downloadGobdExport(jahr)
    } finally {
      setTimeout(() => setLaedt(false), 1500)
    }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Exporte</h1>
        <p className="text-slate-500 mt-1 text-sm">
          Daten für Steuerberater, Betriebsprüfung und Archivierung exportieren.
        </p>
      </div>

      {/* GoBD-Export-Card */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
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
              <label className="text-sm font-medium text-slate-700" htmlFor="export-jahr">
                Wirtschaftsjahr
              </label>
              <select
                id="export-jahr"
                value={jahr}
                onChange={(e) => setJahr(Number(e.target.value))}
                className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
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

          {/* Infobox: enthaltene Dateien */}
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-3">
            <p className="text-sm font-medium text-slate-700">Das ZIP-Archiv enthält:</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {[
                { datei: 'kassenbuch_journal.csv', beschreibung: 'Alle Kassenbucheinträge (IDEA-kompatibel)' },
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
                    <p className="text-xs font-mono font-medium text-slate-800">{datei}</p>
                    <p className="text-xs text-slate-500">{beschreibung}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-2 border-t border-slate-200">
              <p className="text-xs text-slate-500">
                <span className="font-medium">CSV-Format:</span>{' '}
                UTF-8 mit BOM · Semikolon-getrennt · Dezimalkomma · Datum TT.MM.JJJJ
                · kompatibel mit IDEA, Excel und LibreOffice
              </p>
            </div>
          </div>

          {/* GoBD-Hinweis */}
          <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 flex gap-3">
            <span className="text-amber-500 shrink-0">⚠</span>
            <p className="text-xs text-amber-800">
              Alle Kassenbuchdaten sind GoBD-konform unveränderbar gespeichert und durch SHA-256-Signaturen
              gesichert. Der Export enthält eine vollständige Integritätsprüfung. Bei einer Betriebsprüfung
              nach §147 AO ist dieser Export als Z3-Datenträgerüberlassung geeignet.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
