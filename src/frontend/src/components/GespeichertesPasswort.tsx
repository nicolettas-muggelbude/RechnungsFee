/**
 * Security-Audit F6: Das Backend gibt Passwörter nie zurück, nur ob eins hinterlegt ist.
 * Das Eingabefeld bleibt deshalb leer; leer speichern heißt „unverändert“.
 * Diese Zeile unter dem Feld zeigt den Zustand und erlaubt das gezielte Entfernen.
 */
// Platzhalter fürs Eingabefeld: utils/passwortPlatzhalter.ts

interface Props {
  gesetzt: boolean | undefined
  neuEingegeben: boolean
  entfernen: boolean
  onEntfernenChange: (entfernen: boolean) => void
}

export function GespeichertesPasswort({ gesetzt, neuEingegeben, entfernen, onEntfernenChange }: Props) {
  if (!gesetzt) return null
  const linkCls = 'text-blue-600 dark:text-blue-400 hover:underline'
  return (
    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
      {neuEingegeben ? (
        'Das neue Passwort ersetzt beim Speichern das hinterlegte.'
      ) : entfernen ? (
        <>
          Wird beim Speichern entfernt.{' '}
          <button type="button" className={linkCls} onClick={() => onEntfernenChange(false)}>Rückgängig</button>
        </>
      ) : (
        <>
          Ein Passwort ist sicher hinterlegt.{' '}
          <button type="button" className={linkCls} onClick={() => onEntfernenChange(true)}>Passwort entfernen</button>
        </>
      )}
    </p>
  )
}
