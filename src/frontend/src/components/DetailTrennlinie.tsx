import type { DetailBreite } from '../hooks/useDetailBreite'

// Issue #599: ziehbare Trennlinie links vom Detail-Panel (nur „Manuell verschiebbar“).
// Doppelklick setzt die Standardbreite zurück.
export function DetailTrennlinie({ detail }: { detail: DetailBreite }) {
  if (!detail.manuell) return null
  return (
    <div
      className="w-1 shrink-0 bg-slate-200 dark:bg-slate-700 hover:bg-indigo-400 dark:hover:bg-indigo-500 cursor-col-resize transition-colors select-none"
      onMouseDown={detail.startDrag}
      onDoubleClick={detail.zuruecksetzen}
      title="Ziehen zum Ändern der Breite, Doppelklick setzt sie zurück"
    />
  )
}
