/** Issue #562: angezeigte Artikelnummer – die eigene Nummer (Feld „Artikelcode“), sonst die
 *  automatisch vergebene (ART-####). Die automatische bleibt intern bestehen. */
export function artikelNrAnzeige(a: { artikelnummer: string; artikelcode?: string | null }): string {
  return a.artikelcode?.trim() || a.artikelnummer
}
