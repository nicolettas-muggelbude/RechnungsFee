import { useNavigate } from 'react-router-dom'
import type { OffeneAnschaffung } from '../api/client'

function euro(v: number) {
  return v.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'
}

function datumDe(iso: string) {
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

/** Issue #607: Käufe auf Anlage-Kategorien (z. B. Software, Laptop, KFZ) zählen nicht mit dem
 *  Kaufpreis, sondern über die AfA aus dem Anlagenverzeichnis. Fehlt dort der Eintrag, fehlt der
 *  Aufwand in Cockpit und EÜR - der Hinweis zeigt diese Käufe mit direktem Weg zum Eintragen. */
export function OffeneAnschaffungenHinweis({ liste }: { liste?: OffeneAnschaffung[] }) {
  const navigate = useNavigate()
  if (!liste?.length) return null
  const einzahl = liste.length === 1
  return (
    <div role="status" className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-xl p-4 text-sm text-amber-900 dark:text-amber-100">
      <p className="mb-2">
        <strong>{einzahl ? '1 Anschaffung ist' : `${liste.length} Anschaffungen sind`} noch nicht im Anlagenverzeichnis eingetragen</strong>{' '}
        und {einzahl ? 'fehlt' : 'fehlen'} deshalb als Ausgabe. Anschaffungen wie Software, Computer oder Fahrzeuge
        zählen über die Abschreibung (AfA). Beim Eintragen sind die Angaben aus der Buchung schon ausgefüllt.
      </p>
      <ul className="divide-y divide-amber-200 dark:divide-amber-800">
        {liste.map((o) => (
          <li key={o.journal_id} className="flex items-center gap-3 py-1.5">
            <span className="tabular-nums text-amber-700 dark:text-amber-300 shrink-0">{datumDe(o.datum)}</span>
            <span className="min-w-0 truncate" title={o.beschreibung}>{o.beschreibung}</span>
            <span className="ml-auto tabular-nums font-medium shrink-0">{euro(o.betrag)}</span>
            <button
              type="button"
              onClick={() => navigate(`/anlageverzeichnis?aus_journal=${o.journal_id}`)}
              className="shrink-0 px-2.5 py-1 rounded-lg bg-amber-600 text-white text-xs font-medium hover:bg-amber-700"
            >
              Jetzt eintragen
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
