// Issue #590: Zahlungsart in Zahlungs-/Buchungsdialogen merkt sich app-weit die zuletzt
// gebuchte Wahl, statt immer mit „Bar“ zu starten. Ohne Einstellung - wer meist per Bank zahlt,
// stellt einmal um. „Privat bezahlt“ und „Keine“ sind Sonderfälle und werden nicht gemerkt.
export type GemerkteZahlungsart = 'Bar' | 'Bank' | 'Karte' | 'PayPal'

export const ZAHLUNGSART_LS_KEY = 'rechnungsfee.zahlungsart_wahl'

export function letzteZahlungsart(standard: GemerkteZahlungsart = 'Bar'): GemerkteZahlungsart {
  try {
    const v = localStorage.getItem(ZAHLUNGSART_LS_KEY)
    if (v === 'Bar' || v === 'Bank' || v === 'Karte' || v === 'PayPal') return v
  } catch { /* localStorage evtl. nicht verfügbar - Standard verwenden */ }
  return standard
}

export function merkeZahlungsart(z: string) {
  if (z !== 'Bar' && z !== 'Bank' && z !== 'Karte' && z !== 'PayPal') return
  try { localStorage.setItem(ZAHLUNGSART_LS_KEY, z) } catch { /* ignorieren */ }
}
