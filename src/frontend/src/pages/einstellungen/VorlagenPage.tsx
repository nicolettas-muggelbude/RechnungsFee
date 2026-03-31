import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getUnternehmen, updateUnternehmen, getPdfVorlagen, openDemoPdf } from '../../api/client'

export function VorlagenPage() {
  const qc = useQueryClient()

  const { data: unt } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen })
  const { data: vorlagen = [] } = useQuery({ queryKey: ['pdf-vorlagen'], queryFn: getPdfVorlagen })

  const mutation = useMutation({
    mutationFn: (id: number) => updateUnternehmen({ pdf_vorlage: id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['unternehmen'] }),
  })

  const aktuelleVorlage = unt?.pdf_vorlage ?? 0

  return (
    <div className="p-6 max-w-3xl">
      <h1 className="text-xl font-semibold text-slate-800 mb-1">Rechnungsvorlagen</h1>
      <p className="text-sm text-slate-500 mb-6">
        Wähle die Vorlage die für alle Ausgangsrechnungen verwendet wird.
      </p>
      <div className="flex flex-col gap-4">
        {vorlagen.map((v) => (
          <div
            key={v.id}
            className={`border rounded-lg p-4 flex items-start gap-4 cursor-pointer transition-colors ${
              aktuelleVorlage === v.id
                ? 'border-blue-500 bg-blue-50'
                : 'border-slate-200 hover:border-slate-300 bg-white'
            }`}
            onClick={() => mutation.mutate(v.id)}
          >
            <input
              type="radio"
              readOnly
              checked={aktuelleVorlage === v.id}
              className="mt-0.5 accent-blue-600"
            />
            <div className="flex-1 min-w-0">
              <div className="font-medium text-slate-800">{v.name}</div>
              <div className="text-sm text-slate-500 mt-0.5">{v.beschreibung}</div>
            </div>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); openDemoPdf(v.id) }}
              className="shrink-0 text-sm px-3 py-1.5 rounded border border-slate-300 bg-white hover:bg-slate-50 text-slate-700"
            >
              Vorschau
            </button>
          </div>
        ))}
      </div>
      {mutation.isSuccess && (
        <p className="mt-4 text-sm text-green-600">Vorlage gespeichert.</p>
      )}
      {mutation.isError && (
        <p className="mt-4 text-sm text-red-600">Fehler beim Speichern.</p>
      )}
    </div>
  )
}
