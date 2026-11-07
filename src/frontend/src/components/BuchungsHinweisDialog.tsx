// Hinweis nach dem Buchen (Issue #497: freie ig. Lieferung ab dem Stichtag).
// React-Modal statt window.alert(): native Dialoge erscheinen in Tauri/WebView nicht
// zuverlaessig (vgl. Issue #156, #158). Reiner Hinweis, die Buchung ist bereits gespeichert.

interface Props {
  text: string
  onClose: () => void
}

export function BuchungsHinweisDialog({ text, onClose }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 w-full max-w-md mx-4 p-6">
        <div className="flex items-start gap-3 mb-4">
          <span className="text-2xl shrink-0">⚠️</span>
          <div>
            <p className="font-semibold text-slate-800 dark:text-slate-100 mb-1">Buchung gespeichert – bitte prüfen</p>
            <p className="text-sm text-slate-600 dark:text-slate-300">{text}</p>
          </div>
        </div>
        <div className="flex justify-end">
          <button onClick={onClose} autoFocus
            className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 font-medium">
            OK
          </button>
        </div>
      </div>
    </div>
  )
}
