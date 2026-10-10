// Issue #423: Schnellauswahl-Knöpfe für ein Zahlungsdatum ("Heute"/"Rechnungsdatum"/
// "Leistungsdatum") - merkt sich app-weit die zuletzt genutzte Quelle, damit beim nächsten
// Zahlungsdialog bereits der naheliegende Vorschlag vorausgewählt ist (Issue-Kommentar).
export type ZahlungsdatumWahl = 'heute' | 'rechnungsdatum' | 'leistungsdatum'

export const ZAHLUNGSDATUM_WAHL_LS_KEY = 'rechnungsfee.zahlungsdatum_wahl'

export function letzteZahlungsdatumWahl(): ZahlungsdatumWahl {
  try {
    const v = localStorage.getItem(ZAHLUNGSDATUM_WAHL_LS_KEY)
    if (v === 'heute' || v === 'rechnungsdatum' || v === 'leistungsdatum') return v
  } catch { /* localStorage evtl. nicht verfügbar - Standard verwenden */ }
  return 'heute'
}

export function merkeZahlungsdatumWahl(wahl: ZahlungsdatumWahl) {
  try { localStorage.setItem(ZAHLUNGSDATUM_WAHL_LS_KEY, wahl) } catch { /* ignorieren */ }
}
