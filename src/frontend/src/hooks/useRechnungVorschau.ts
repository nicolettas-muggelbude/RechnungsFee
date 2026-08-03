import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { rechnungVorschau, type RechnungVorschauRequest, type RechnungVorschau } from '../api/client'

const DEBOUNCE_MS = 300

/**
 * Fragt die Rechnungssumme beim Backend ab statt sie im Frontend selbst nachzubauen (Issue #332:
 * Formular-Vorschau, Speichern, PDF und Rechnungsdetails müssen dieselbe, einzige Berechnung
 * verwenden - sonst laufen die Rundungen bei Menge>1/Rabatt/gemischten USt-Sätzen leicht
 * auseinander). Debounced, damit nicht bei jedem Tastendruck ein Request rausgeht.
 *
 * `request` auf `null` setzen um die Vorschau zu deaktivieren (z.B. wenn noch keine gültige
 * Position vorhanden ist).
 */
export function useRechnungVorschau(request: RechnungVorschauRequest | null) {
  const [debounced, setDebounced] = useState<RechnungVorschauRequest | null>(request)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(request), DEBOUNCE_MS)
    return () => clearTimeout(timer)
    // Positionen/Rabatt ändern sich als neues Array/Objekt bei jeder Eingabe - Stringify als
    // Vergleichsbasis, damit der Debounce-Timer nicht bei jedem Render neu anläuft.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(request)])

  const { data, isFetching, error } = useQuery({
    queryKey: ['rechnung-vorschau', JSON.stringify(debounced)],
    queryFn: () => rechnungVorschau(debounced!),
    enabled: debounced !== null,
    staleTime: 0,
    placeholderData: (prev) => prev,
  })

  return {
    vorschau: (debounced ? data : undefined) as RechnungVorschau | undefined,
    isLoading: isFetching,
    error: error as Error | null,
  }
}
