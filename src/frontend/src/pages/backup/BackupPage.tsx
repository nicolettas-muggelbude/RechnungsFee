import { useState } from 'react'
import { downloadBackup } from '../../api/client'

export function BackupPage() {
  const [laedt, setLaedt] = useState(false)

  function handleBackup() {
    setLaedt(true)
    try {
      downloadBackup()
    } finally {
      setTimeout(() => setLaedt(false), 1500)
    }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Backup</h1>
        <p className="text-slate-500 mt-1 text-sm">
          Deine Daten sichern und im Notfall wiederherstellen.
        </p>
      </div>

      {/* Manuelles Backup */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="bg-green-600 px-6 py-4">
          <h2 className="text-white font-bold text-lg">Backup erstellen</h2>
          <p className="text-green-100 text-sm mt-0.5">
            Vollständige Kopie deiner Datenbank als SQLite-Datei herunterladen
          </p>
        </div>

        <div className="p-6 space-y-5">
          <div className="flex items-start gap-4">
            <button
              onClick={handleBackup}
              disabled={laedt}
              className="flex items-center gap-2 bg-green-600 hover:bg-green-700 disabled:bg-green-300 text-white font-medium text-sm px-5 py-2 rounded-lg transition-colors shrink-0"
            >
              {laedt ? (
                <>
                  <span className="animate-spin">⏳</span>
                  Wird erstellt…
                </>
              ) : (
                <>
                  <span>💾</span>
                  Backup erstellen
                </>
              )}
            </button>
            <p className="text-sm text-slate-500 pt-1.5">
              Erstellt eine konsistente Kopie deiner Datenbank und startet den Download.
              Die Datei heißt <span className="font-mono text-slate-700">RechnungsFee-Backup-JJJJ-MM-TT.db</span>.
            </p>
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-2">
            <p className="text-sm font-medium text-slate-700">Was wird gesichert?</p>
            <ul className="text-sm text-slate-600 space-y-1 list-none">
              {[
                'Alle Kassenbucheinträge und Tagesabschlüsse',
                'Rechnungen (Eingang & Ausgang) mit Zahlungen',
                'Kunden und Lieferanten',
                'Unternehmensdaten, Konten, Kategorien',
                'Nummernkreise und alle Einstellungen',
              ].map((item) => (
                <li key={item} className="flex items-center gap-2">
                  <span className="text-green-500 shrink-0">✓</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 flex gap-3">
            <span className="text-blue-500 shrink-0 mt-0.5">ℹ</span>
            <p className="text-xs text-blue-800">
              Das Backup ist eine vollständige SQLite-Datenbank und kann direkt mit dem
              SQLite-Browser oder DB Browser for SQLite geöffnet werden.
              Bewahre Backups an einem sicheren Ort auf – idealerweise auf einem externen
              Laufwerk oder in einem Cloud-Speicher.
            </p>
          </div>
        </div>
      </div>

      {/* Automatische Backups */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6 space-y-3">
        <h2 className="font-semibold text-slate-800">Automatische Backups vor Updates</h2>
        <p className="text-sm text-slate-600">
          RechnungsFee erstellt automatisch ein Backup deiner Datenbank, bevor bei einem
          App-Update Datenbankmigrationen durchgeführt werden. Die letzten 5 Backups werden
          aufbewahrt.
        </p>
        <p className="text-sm text-slate-500 font-mono">
          ~/.local/share/RechnungsFee/backups/
        </p>
      </div>

      {/* Wiederherstellen */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6 space-y-3">
        <h2 className="font-semibold text-slate-800">Backup wiederherstellen</h2>
        <p className="text-sm text-slate-600">
          Eine automatische Wiederherstellungsfunktion ist in Vorbereitung. Bis dahin kannst
          du ein Backup manuell wiederherstellen:
        </p>
        <ol className="text-sm text-slate-600 space-y-1.5 list-none">
          {[
            'RechnungsFee beenden',
            'Aktuelle Datenbank sichern (optional): ~/.local/share/RechnungsFee/rechnungsfee.db umbenennen',
            'Backup-Datei nach ~/.local/share/RechnungsFee/rechnungsfee.db kopieren',
            'RechnungsFee neu starten',
          ].map((step, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="bg-slate-200 text-slate-700 text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center shrink-0 mt-0.5">
                {i + 1}
              </span>
              {step}
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}
