import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getJournalJahre, getUnternehmen } from '../api/client'

/**
 * Issue #589: Jahresauswahl der Auswertungen - nur Jahre, in denen es Buchungen gibt (wie im
 * Journal), dazu immer das aktuelle Jahr. Bisher fest die letzten 5–6 Jahre, ältere bebuchte
 * Jahre waren nicht wählbar. Bei abweichendem Wirtschaftsjahr gehört eine Buchung am Jahresanfang
 * zum Wirtschaftsjahr des Vorjahres - dann zählt auch dieses Jahr als bebucht.
 */
export function useBuchungsjahre(gewaehlt?: number): number[] {
  const { data: bebucht } = useQuery({ queryKey: ['journal', 'jahre'], queryFn: getJournalJahre, staleTime: 1000 * 60 })
  const { data: unt } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen, staleTime: 1000 * 60 * 10 })
  return useMemo(() => {
    // das gerade gewählte Jahr bleibt immer in der Liste (z. B. Jahres-USt startet mit dem Vorjahr)
    const jahre = new Set<number>([new Date().getFullYear(), ...(bebucht ?? []), ...(gewaehlt ? [gewaehlt] : [])])
    if (unt?.wirtschaftsjahr_abweichend_aktiv) for (const j of bebucht ?? []) jahre.add(j - 1)
    return [...jahre].sort((a, b) => b - a)
  }, [bebucht, unt?.wirtschaftsjahr_abweichend_aktiv, gewaehlt])
}
