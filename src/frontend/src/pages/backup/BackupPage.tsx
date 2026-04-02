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
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Backup</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
          Deine Daten sichern und im Notfall wiederherstellen.
        </p>
      </div>

      {/* Manuelles Backup */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
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
            <p className="text-sm text-slate-500 dark:text-slate-400 pt-1.5">
              Erstellt eine konsistente Kopie deiner Datenbank und startet den Download.
              Die Datei heißt <span className="font-mono text-slate-700 dark:text-slate-200">RechnungsFee-Backup-JJJJ-MM-TT.db</span>.
            </p>
          </div>

          <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg p-4 space-y-2">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Was wird gesichert?</p>
            <ul className="text-sm text-slate-600 dark:text-slate-300 space-y-1 list-none">
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

          <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg px-4 py-3 flex gap-3">
            <span className="text-blue-500 dark:text-blue-400 shrink-0 mt-0.5">ℹ</span>
            <p className="text-xs text-blue-800 dark:text-blue-300">
              Das Backup ist eine vollständige SQLite-Datenbank und kann direkt mit dem
              SQLite-Browser oder DB Browser for SQLite geöffnet werden.
              Bewahre Backups an einem sicheren Ort auf – idealerweise auf einem externen
              Laufwerk oder in einem Cloud-Speicher.
            </p>
          </div>
        </div>
      </div>

      {/* Automatische Backups */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm p-6 space-y-3">
        <h2 className="font-semibold text-slate-800 dark:text-slate-100">Automatische Backups vor Updates</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          RechnungsFee erstellt automatisch ein Backup deiner Datenbank, bevor bei einem
          App-Update Datenbankmigrationen durchgeführt werden. Die letzten 5 Backups werden
          aufbewahrt.
        </p>
        <div className="space-y-1.5">
          {[
            { os: 'Linux', pfad: '~/.local/share/RechnungsFee/backups/' },
            { os: 'Windows', pfad: '%APPDATA%\\RechnungsFee\\backups\\' },
            { os: 'macOS', pfad: '~/Library/Application Support/RechnungsFee/backups/' },
          ].map(({ os, pfad }) => (
            <div key={os} className="flex items-center gap-2 text-sm">
              <span className="text-xs bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 px-1.5 py-0.5 rounded font-medium w-16 text-center shrink-0">{os}</span>
              <code className="text-slate-600 dark:text-slate-300 font-mono text-xs">{pfad}</code>
            </div>
          ))}
        </div>
      </div>

      {/* Wiederherstellen */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm p-6 space-y-3">
        <h2 className="font-semibold text-slate-800 dark:text-slate-100">Backup wiederherstellen</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Eine automatische Wiederherstellungsfunktion ist in Vorbereitung. Bis dahin kannst
          du ein Backup manuell wiederherstellen:
        </p>
        <ol className="text-sm text-slate-600 dark:text-slate-300 space-y-2 list-none">
          <li className="flex items-start gap-2">
            <span className="bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center shrink-0 mt-0.5">1</span>
            RechnungsFee beenden
          </li>
          <li className="flex items-start gap-2">
            <span className="bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center shrink-0 mt-0.5">2</span>
            <span>Aktuelle Datenbank sichern (optional) – Datei umbenennen:
              <div className="mt-1 space-y-0.5">
                {[
                  { os: 'Linux', pfad: '~/.local/share/RechnungsFee/rechnungsfee.db' },
                  { os: 'Windows', pfad: '%APPDATA%\\RechnungsFee\\rechnungsfee.db' },
                  { os: 'macOS', pfad: '~/Library/Application Support/RechnungsFee/rechnungsfee.db' },
                ].map(({ os, pfad }) => (
                  <div key={os} className="flex items-center gap-2">
                    <span className="text-xs bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 px-1.5 py-0.5 rounded font-medium w-16 text-center shrink-0">{os}</span>
                    <code className="font-mono text-xs text-slate-500 dark:text-slate-400">{pfad}</code>
                  </div>
                ))}
              </div>
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center shrink-0 mt-0.5">3</span>
            Backup-Datei in den jeweiligen Ordner kopieren und in <code className="font-mono text-xs">rechnungsfee.db</code> umbenennen
          </li>
          <li className="flex items-start gap-2">
            <span className="bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center shrink-0 mt-0.5">4</span>
            RechnungsFee neu starten
          </li>
        </ol>
      </div>
    </div>
  )
}
