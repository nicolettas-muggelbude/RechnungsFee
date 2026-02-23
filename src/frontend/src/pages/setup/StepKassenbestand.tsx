type Props = {
  onNext: (betrag: string) => void
  onBack: () => void
  isLoading?: boolean
}

export function StepKassenbestand({ onNext, onBack, isLoading }: Props) {
  return (
    <div className="space-y-5">
      <p className="text-sm text-slate-600">
        Falls du bereits Bargeld in deiner Kasse hast, trag hier den aktuellen Bestand ein.
        Dieser Anfangsbestand wird als unveränderlicher Kassenbucheintrag gespeichert.
      </p>
      <div className="rounded-lg bg-blue-50 border border-blue-200 px-4 py-3 text-sm text-blue-700">
        <strong>Kein Bargeld?</strong> Kein Problem – einfach 0 lassen und überspringen.
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Bargeld-Anfangsbestand (€)
        </label>
        <input
          id="kassenbestand"
          type="number"
          min="0"
          step="0.01"
          defaultValue="0"
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="pt-2 flex justify-between">
        <button
          type="button"
          onClick={onBack}
          className="text-slate-600 hover:text-slate-800 font-medium px-4 py-2 rounded-lg transition-colors"
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
