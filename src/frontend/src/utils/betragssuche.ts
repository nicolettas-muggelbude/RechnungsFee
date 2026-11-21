/**
 * Issue #565: Suche nach Beträgen in Journal und Bank-Import.
 *
 * Die Eingabe wird als deutscher Betrag gelesen ("119", "119,00", "1.190,50", "-49,90 €").
 * Mit Nachkommastellen muss der Betrag genau passen, ohne Nachkommastellen reicht der
 * Euro-Teil (119 findet 119,00 und 119,99). Das Vorzeichen zählt nicht, damit eine
 * Ausgabe auch ohne Minus gefunden wird.
 */
export function suchbetrag(suche: string): { cent: number; mitNachkomma: boolean } | null {
  const s = suche.replace(/€/g, '').replace(/\s/g, '').replace(/^[-+]/, '')
  if (!/^\d{1,3}(\.\d{3})*(,\d{1,2})?$|^\d+(,\d{1,2})?$|^\d+\.\d{1,2}$/.test(s)) return null
  let normal: string
  if (s.includes(',')) normal = s.replace(/\./g, '').replace(',', '.')
  else if (/^\d+\.\d{1,2}$/.test(s)) normal = s            // 119.50 (Punkt als Dezimaltrenner)
  else normal = s.replace(/\./g, '')                       // 1.190 (Tausenderpunkt)
  const wert = Number(normal)
  if (!Number.isFinite(wert)) return null
  return { cent: Math.round(wert * 100), mitNachkomma: /[.,]\d{1,2}$/.test(s) && !/^\d{1,3}(\.\d{3})+$/.test(s) }
}

export function betragPasst(suche: string, betrag: string | number | null | undefined): boolean {
  const b = suchbetrag(suche)
  if (!b || betrag === null || betrag === undefined || betrag === '') return false
  const cent = Math.abs(Math.round(Number(betrag) * 100))
  if (!Number.isFinite(cent)) return false
  return b.mitNachkomma ? cent === b.cent : Math.floor(cent / 100) === Math.floor(b.cent / 100)
}

/**
 * Jahre für die Jahresauswahl: nur Jahre mit Buchungen, dazu immer das aktuelle und das
 * gerade gewählte Jahr (damit die Auswahl nie leer ist bzw. ihren Wert verliert).
 */
export function jahresAuswahl(bebucht: number[] | undefined, gewaehlt: number): number[] {
  const jahre = new Set([...(bebucht ?? []), new Date().getFullYear(), gewaehlt])
  return [...jahre].sort((a, b) => b - a)
}
