type Props = {
  onNext: (betrag: string) => void
  onBack: () => void
  isLoading?: boolean
}

export function StepKassenbestand({ onNext, onBack, isLoading }: Props) {
  return (
    <div className="space-y-5">
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Falls du bereits Bargeld in deiner Kasse hast, trag hier den aktuellen Bestand ein.
        Dieser Anfangsbestand wird als unveränderlicher Kassenbucheintrag gespeichert.
      </p>
      <div className="rounded-lg bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 px-4 py-3 text-sm text-blue-700 dark:text-blue-300">
        <strong>Kein Bargeld?</strong> Kein Problem – einfach 0 lassen und überspringen.
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
          Bargeld-Anfangsbestand (€)
        </label>
        <input
          id="kassenbestand"
          type="number"
          min="0"
          step="0.01"
          defaultValue="0"
          className="w-full rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
        />
      </div>

      <div className="pt-2 flex justify-between">
        <button
          type="button"
          onClick={onBack}
          className="text-slate-600 dark:text-slate-300 hover:text-slate-800 dark:hover:text-slate-100 font-medium px-4 py-2 rounded-lg transition-colors"
        >
          ← Zurück
        </button>
        <button
          type="button"
          disabled={isLoading}
          onClick={() => {
            const input = document.getElementById('kassenbestand') as HTMLInputElement
            onNext(input.value || '0')
          }}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium px-6 py-2 rounded-lg transition-colors"
        >
          {isLoading ? 'Speichern…' : 'Einrichtung abschließen ✓'}
        </button>
      </div>
    </div>
  )
}
