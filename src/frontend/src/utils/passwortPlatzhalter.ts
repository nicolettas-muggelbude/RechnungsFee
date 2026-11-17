/** Security-Audit F6: Platzhalter für Passwortfelder, deren Wert das Backend nie zurückgibt. */
export const PASSWORT_GESPEICHERT_PLATZHALTER = 'Gespeichert – leer lassen, um es beizubehalten'

export function passwortPlatzhalter(gesetzt: boolean | undefined, entfernen: boolean, standard: string) {
  return gesetzt && !entfernen ? PASSWORT_GESPEICHERT_PLATZHALTER : standard
}
