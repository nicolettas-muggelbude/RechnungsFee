// Issue #485/#531: Nachfrage beim Finalisieren eines älteren Entwurfs, ob das Rechnungsdatum
// auf heute gesetzt werden soll. React-Modal statt window.confirm(): native Dialoge erscheinen
// in Tauri/WebView nicht zuverlässig (vgl. Issue #156, #158) - und bei confirm() hieß „OK“
// „auf heute setzen“, wer mit Enter durch die Finalisieren-Dialoge ging, verlor das Datum.
// Vorauswahl ist deshalb „Datum beibehalten“. Aufruf über hooks/useRechnungsdatumFrage.tsx.

/** true = auf heute setzen, false = Datum beibehalten, null = Finalisieren abbrechen */
export type DatumEntscheidung = boolean | null

export interface Frage {
  datum: string
  heute: string
  leistungBis?: string | null
  resolve: (v: DatumEntscheidung) => void
}

const de = (iso: string) => iso.split('-').reverse().join('.')

export function RechnungsdatumDialog({ frage, onAntwort }: { frage: Frage; onAntwort: (v: DatumEntscheidung) => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      role="dialog" aria-modal="true" aria-labelledby="rechnungsdatum-titel"
      onKeyDown={(e) => { if (e.key === 'Escape') onAntwort(null) }}>
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 w-full max-w-md mx-4 p-6">
        <p id="rechnungsdatum-titel" className="font-semibold text-slate-800 dark:text-slate-100 mb-2">
          Rechnungsdatum beim Finalisieren
        </p>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Das Rechnungsdatum ist der <strong>{de(frage.datum)}</strong>. Soll es so bleiben oder auf
          heute ({de(frage.heute)}) gesetzt werden? Beim Wechsel auf heute verschiebt sich die
          Fälligkeit um dieselbe Anzahl Tage.
        </p>
        {frage.leistungBis && frage.leistungBis > frage.datum && (
          <p className="text-sm text-amber-700 dark:text-amber-300 mt-2">
            ⚠️ Der Leistungszeitraum endet erst am {de(frage.leistungBis)}, also nach dem bisherigen Rechnungsdatum.
          </p>
        )}
        <div className="flex flex-wrap justify-end gap-2 mt-5">
          <button type="button" onClick={() => onAntwort(null)}
            className="px-4 py-2 text-sm rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700">
            Abbrechen
          </button>
          <button type="button" onClick={() => onAntwort(true)}
            className="px-4 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700">
            Auf heute setzen
          </button>
          <button type="button" onClick={() => onAntwort(false)} autoFocus
            className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 font-medium">
            {de(frage.datum)} beibehalten
          </button>
        </div>
      </div>
    </div>
  )
}
