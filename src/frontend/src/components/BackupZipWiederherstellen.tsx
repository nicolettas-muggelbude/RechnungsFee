import { useRef, useState } from 'react'
import { isTauri, uploadBackupWiederherstellen } from '../api/client'

const inputCls = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100 dark:placeholder-slate-400"

/**
 * ZIP-Backup hochladen und wiederherstellen (.zip oder verschlüsseltes .zip.enc) – volle
 * Wiederherstellung inkl. Belege. Eigenständige Komponente (Issue #374): wird sowohl in den
 * Backup-Einstellungen als auch im Setup-Assistenten verwendet, damit ein Backup schon vor der
 * Ersteinrichtung eingespielt werden kann, ohne die Konfiguration doppelt einzutippen.
 */
export function BackupZipWiederherstellen() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [datei, setDatei] = useState<File | null>(null)
  const [passwort, setPasswort] = useState('')
  const [zeigPasswort, setZeigPasswort] = useState(false)
  const [status, setStatus] = useState<'idle' | 'uploading' | 'bereit' | 'err'>('idle')
  const [fehler, setFehler] = useState<string | null>(null)

  const istVerschluesselt = datei?.name.endsWith('.zip.enc') ?? false
  const kannWiederherstellen = !!datei && (!istVerschluesselt || !!passwort)
  const neustartBereit = status === 'bereit'

  function waehleDatei() {
    // Bewusst immer der native <input type="file"> – ein fruehrer Versuch, den Tauri-Dialog
    // per fetch("file://…") auszulesen, schlug unter Linux (WebKitGTK) mit "Load failed" fehl.
    fileInputRef.current?.click()
  }

  async function wiederherstellen() {
    if (!datei || !kannWiederherstellen) return
    setStatus('uploading'); setFehler(null)
    try {
      await uploadBackupWiederherstellen(datei, istVerschluesselt ? passwort : undefined)
      setStatus('bereit')
    } catch (e) {
      setFehler(e instanceof Error ? e.message : 'Unbekannter Fehler')
      setStatus('err')
    }
  }

  async function neustart() {
    if (isTauri()) {
      const { relaunch } = await import('@tauri-apps/plugin-process')
      await relaunch()
    }
  }

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700">
        <h2 className="font-semibold text-slate-800 dark:text-slate-100">ZIP-Backup hochladen</h2>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">
          Aus einer Backup-Datei (.zip oder verschlüsselt .zip.enc) – für die vollständige Wiederherstellung
          inkl. Belege, z. B. nach einem Hardware-Wechsel oder Totalverlust.
        </p>
        <button
          type="button"
          onClick={() => import('../api/client').then(m => m.openUrl('https://github.com/nicolettas-muggelbude/RechnungsFee/wiki/Backup#aus-manuellem-zip-backup'))}
          className="inline-block text-blue-600 dark:text-blue-400 text-xs underline mt-1.5 hover:text-blue-800 dark:hover:text-blue-300"
        >
          Mehr dazu im Handbuch →
        </button>
      </div>
      <div className="p-6 space-y-5">
        <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3 flex gap-3">
          <span className="text-red-500 shrink-0 mt-0.5">⚠</span>
          <p className="text-xs text-red-800 dark:text-red-300">
            <strong>Achtung:</strong> Die Wiederherstellung überschreibt alle aktuellen Daten unwiderruflich.
            Vor der Wiederherstellung wird automatisch ein Sicherheits-Backup der aktuellen Daten angelegt.
          </p>
        </div>

        {neustartBereit ? (
          <div className="space-y-4">
            <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg px-4 py-3 text-sm text-green-700 dark:text-green-300">
              ✓ Backup bereit – RechnungsFee stellt die Daten beim Neustart wieder her.
            </div>
            {isTauri() ? (
              <button onClick={neustart}
                className="px-5 py-2 bg-orange-600 hover:bg-orange-700 text-white text-sm font-medium rounded-lg">
                Jetzt neu starten und wiederherstellen
              </button>
            ) : (
              <p className="text-sm text-slate-500 dark:text-slate-400">Bitte starte RechnungsFee neu um die Wiederherstellung abzuschließen.</p>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <input ref={fileInputRef} type="file" accept=".zip,.zip.enc" className="hidden"
              onChange={e => { setDatei(e.target.files?.[0] ?? null); setPasswort('') }} />

            <div className="flex items-center gap-3">
              <button type="button" onClick={waehleDatei}
                className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200">
                Backup-Datei wählen
              </button>
              {datei && (
                <span className="text-sm text-slate-600 dark:text-slate-300 font-mono flex items-center gap-2">
                  {datei.name}
                  {istVerschluesselt && <span className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-1.5 py-0.5 rounded">verschlüsselt</span>}
                </span>
              )}
            </div>

            {istVerschluesselt && (
              <div className="space-y-1">
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-200">
                  Backup-Passwort <span className="text-red-500">*</span>
                </label>
                <div className="relative max-w-sm">
                  <input
                    type={zeigPasswort ? 'text' : 'password'}
                    value={passwort}
                    onChange={e => setPasswort(e.target.value)}
                    placeholder="Passwort das beim Backup gesetzt wurde"
                    className={`${inputCls} pr-24`}
                  />
                  <button type="button" onClick={() => setZeigPasswort(z => !z)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 px-2 py-1">
                    {zeigPasswort ? 'Verbergen' : 'Anzeigen'}
                  </button>
                </div>
              </div>
            )}

            {fehler && <p className="text-sm text-red-600 dark:text-red-400">{fehler}</p>}

            <button onClick={wiederherstellen} disabled={!kannWiederherstellen || status === 'uploading'}
              className="px-5 py-2 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg">
              {status === 'uploading' ? 'Wird verarbeitet…' : 'Backup hochladen und vorbereiten'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
