/**
 * Leitweg-ID öffentlicher Auftraggeber (Issue #530) – Gegenstück zu utils/leitweg_id.py im Backend:
 * Grobadressierung (2–12 Ziffern) – optional Feinadressierung (bis 30 Zeichen A–Z/0–9) –
 * Prüfziffer (2 Ziffern, Modulo 97-10; Buchstaben A=10 … Z=35). Beispiel: 991-33333TEST-33.
 */
const MUSTER = /^(\d{2,12})(?:-([A-Z0-9]{1,30}))?-(\d{2})$/

export function normalisiereLeitwegId(wert: string | null | undefined): string {
  return (wert ?? '').trim().toUpperCase().replace(/\s+/g, '')
}

/** null wenn gültig, sonst Fehlermeldung */
export function leitwegIdFehler(wert: string | null | undefined): string | null {
  const lid = normalisiereLeitwegId(wert)
  if (!lid) return 'Pflichtfeld für öffentliche Auftraggeber'
  const m = MUSTER.exec(lid)
  if (!m) return 'Ungültiges Format – z. B. 991-33333TEST-33'
  const ziffern = [...(m[1] + (m[2] ?? ''))].map(c => parseInt(c, 36).toString()).join('') + m[3]
  // Modulo 97 stückweise – die Zahl ist für Number zu groß
  let rest = 0
  for (const z of ziffern) rest = (rest * 10 + Number(z)) % 97
  return rest === 1 ? null : 'Prüfziffer stimmt nicht – bitte auf Tippfehler prüfen'
}
