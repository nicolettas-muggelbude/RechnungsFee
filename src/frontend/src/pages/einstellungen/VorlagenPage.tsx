import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getUnternehmen, updateUnternehmen, getPdfVorlagen, openDemoPdf } from '../../api/client'
import { useMxAuto } from '../../hooks/useAnsicht'

export function VorlagenPage() {
  const mxAuto = useMxAuto()
  const qc = useQueryClient()

  const { data: unt } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen })
  const { data: vorlagen = [] } = useQuery({ queryKey: ['pdf-vorlagen'], queryFn: getPdfVorlagen })

  const mutation = useMutation({
    mutationFn: (id: number) => updateUnternehmen({ pdf_vorlage: id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['unternehmen'] }),
  })

  const posMutation = useMutation({
    mutationFn: (an: boolean) => updateUnternehmen({ pdf_positionsnummern: an }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['unternehmen'] }),
  })

  // Issue #562: Spalte „Art.-Nr.“ – gilt für beide Vorlagen
  const artNrMutation = useMutation({
    mutationFn: (an: boolean) => updateUnternehmen({ pdf_artikelnummer: an }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['unternehmen'] }),
  })

  // Issue #594: Spalte „Datum“ und Datumsfeld je Position – gilt für beide Vorlagen
  const datumMutation = useMutation({
    mutationFn: (an: boolean) => updateUnternehmen({ pdf_positionsdatum: an }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['unternehmen'] }),
  })

  const aktuelleVorlage = unt?.pdf_vorlage ?? 0

  return (
    <div className={`p-6 max-w-3xl ${mxAuto}`}>
      <h1 className="text-xl font-semibold text-slate-800 dark:text-slate-100 mb-1">Rechnungsvorlagen</h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        Wähle die Vorlage die für alle Ausgangsrechnungen verwendet wird.
      </p>
      <div className="flex flex-col gap-4">
        {vorlagen.map((v) => (
          <div
            key={v.id}
            className={`border rounded-lg p-4 flex items-start gap-4 cursor-pointer transition-colors ${
              aktuelleVorlage === v.id
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-950 dark:border-blue-700'
                : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 bg-white dark:bg-slate-800'
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
              <div className="font-medium text-slate-800 dark:text-slate-100">{v.name}</div>
              <div className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{v.beschreibung}</div>
            </div>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); openDemoPdf(v.id) }}
              className="shrink-0 text-sm px-3 py-1.5 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 hover:bg-slate-50 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200"
            >
              Vorschau
            </button>
          </div>
        ))}
      </div>
      {/* Issue #594: alle Spalten-Schalter gelten für beide Vorlagen */}
      <label className="mt-6 flex items-start gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={!!unt?.pdf_positionsnummern}
          onChange={(e) => posMutation.mutate(e.target.checked)}
          className="mt-0.5 accent-blue-600"
        />
        <span>
          <span className="block text-sm font-medium text-slate-800 dark:text-slate-100">Positionsnummern anzeigen</span>
          <span className="block text-sm text-slate-500 dark:text-slate-400">
            Zusätzliche Spalte „Pos.“ (1, 2, 3 …) in Rechnungen, Angeboten, Aufträgen, Proforma-Rechnungen,
            Lieferscheinen und Gutschriften. Gilt für neu finalisierte Dokumente, bereits finalisierte bleiben unverändert.
          </span>
        </span>
      </label>
      <label className="mt-4 flex items-start gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={!!unt?.pdf_positionsdatum}
          onChange={(e) => datumMutation.mutate(e.target.checked)}
          className="mt-0.5 accent-blue-600"
        />
        <span>
          <span className="block text-sm font-medium text-slate-800 dark:text-slate-100">Leistungsdatum je Position</span>
          <span className="block text-sm text-slate-500 dark:text-slate-400">
            Im Formular bekommt jede Position ein eigenes Datumsfeld, im Dokument erscheint die Spalte „Datum“ –
            praktisch für Sammelrechnungen. Ohne eigenes Datum steht dort der Leistungsbeginn bzw. das Rechnungsdatum.
            Ist kein Leistungszeitraum eingetragen, wird er aus dem frühesten und spätesten Positionsdatum gebildet.
            Gilt für neu finalisierte Dokumente, bereits finalisierte bleiben unverändert.
          </span>
        </span>
      </label>
      <label className="mt-4 flex items-start gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={!!unt?.pdf_artikelnummer}
          onChange={(e) => artNrMutation.mutate(e.target.checked)}
          className="mt-0.5 accent-blue-600"
        />
        <span>
          <span className="block text-sm font-medium text-slate-800 dark:text-slate-100">Artikelnummern anzeigen</span>
          <span className="block text-sm text-slate-500 dark:text-slate-400">
            Zusätzliche Spalte „Art.-Nr.“ bei Positionen mit Artikel. Steht beim Artikel etwas im Feld
            „Artikelcode“, erscheint dieser Eintrag, sonst die automatisch vergebene Nummer (z. B. ART-0005).
            Gilt für neu finalisierte Dokumente, bereits finalisierte bleiben unverändert.
          </span>
        </span>
      </label>
      {mutation.isSuccess && (
        <p className="mt-4 text-sm text-green-600">Vorlage gespeichert.</p>
      )}
      {mutation.isError && (
        <p className="mt-4 text-sm text-red-600">Fehler beim Speichern.</p>
      )}
    </div>
  )
}
