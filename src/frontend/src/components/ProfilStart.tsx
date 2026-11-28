import { useState } from 'react'
import { meldeProfilAn, isTauri, type ProfilStart as ProfilStartDaten } from '../api/client'
import { neustart } from '../pages/profile/ProfilePage'

/** Issue #593: Startbildschirm vor der App. Erscheint, wenn das aktive Profil ein Passwort hat
 *  (Backend sperrt bis zur Anmeldung) oder die Profilauswahl beim Start eingeschaltet ist.
 *  Anderes Profil gewählt → Backend stellt um, App startet neu (Profil lädt nur beim Start). */
export function ProfilStart({ start, onFertig }: { start: ProfilStartDaten; onFertig: () => void }) {
  const aktiv = start.profile.find((p) => p.aktiv)?.name ?? start.profile[0]?.name ?? ''
  const [gewaehlt, setGewaehlt] = useState(aktiv)
  const [passwort, setPasswort] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)
  const [laeuft, setLaeuft] = useState(false)
  const [neustartNoetig, setNeustartNoetig] = useState(false)

  const profil = start.profile.find((p) => p.name === gewaehlt)
  const mitAuswahl = start.auswahl_anzeigen

  async function oeffnen() {
    if (!gewaehlt) return
    setLaeuft(true)
    setFehler(null)
    try {
      const { neustart_erforderlich } = await meldeProfilAn(gewaehlt, passwort)
      if (!neustart_erforderlich) { onFertig(); return }
      setNeustartNoetig(true)
      await neustart()
    } catch (err) {
      setFehler((err as Error).message)
      setPasswort('')
    } finally {
      setLaeuft(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 px-4">
      <form
        onSubmit={(e) => { e.preventDefault(); void oeffnen() }}
        className="w-full max-w-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm p-6 space-y-4"
      >
        <div className="text-center space-y-1">
          <div className="text-4xl" aria-hidden="true">🧾</div>
          <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">RechnungsFee</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {mitAuswahl ? 'Wähle dein Profil.' : `Profil „${gewaehlt}“ ist mit einem Passwort geschützt.`}
          </p>
        </div>

        {mitAuswahl && (
          <div>
            <label htmlFor="profil-start-auswahl" className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
              Profil
            </label>
            <select
              id="profil-start-auswahl"
              value={gewaehlt}
              onChange={(e) => { setGewaehlt(e.target.value); setPasswort(''); setFehler(null) }}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
            >
              {start.profile.map((p) => (
                <option key={p.name} value={p.name}>{p.name}{p.passwort ? ' 🔒' : ''}</option>
              ))}
            </select>
          </div>
        )}

        {profil?.passwort && (
          <div>
            <label htmlFor="profil-start-passwort" className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
              Passwort
            </label>
            <input
              id="profil-start-passwort"
              type="password"
              value={passwort}
              onChange={(e) => setPasswort(e.target.value)}
              autoFocus
              autoComplete="current-password"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
            />
          </div>
        )}

        {fehler && (
          <p role="alert" className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2">
            {fehler}
          </p>
        )}

        {neustartNoetig && !isTauri() && (
          <p className="text-sm text-amber-700 dark:text-amber-300">
            Profil umgestellt – starte das Backend neu und lade die Seite danach neu.
          </p>
        )}

        <button
          type="submit"
          disabled={laeuft || neustartNoetig || !gewaehlt || (!!profil?.passwort && !passwort)}
          className="w-full px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg transition-colors"
        >
          {neustartNoetig ? 'Wird neu gestartet…' : laeuft ? 'Wird geöffnet…' : gewaehlt !== aktiv ? 'Öffnen (Neustart)' : 'Öffnen'}
        </button>
      </form>
    </div>
  )
}
