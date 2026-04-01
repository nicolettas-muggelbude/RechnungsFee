import { useForm } from 'react-hook-form'
import type { Unternehmen } from '../../api/client'

type FormData = {
  rechtsform: string
  taetigkeitsart: string
  ist_kleinunternehmer: boolean
  versteuerungsart: 'ist' | 'soll'
  kontenrahmen: 'SKR03' | 'SKR04' | 'SKR49'
  bezieht_transferleistungen: boolean
  ust_idnr: string
}

type Props = {
  onNext: (data: Partial<Unternehmen>) => void
  onBack: () => void
  defaultValues?: Partial<Unternehmen>
}

export function StepSteuern({ onNext, onBack, defaultValues }: Props) {
  const { register, handleSubmit, watch } = useForm<FormData>({
    defaultValues: {
      rechtsform: defaultValues?.rechtsform ?? 'Einzelunternehmer',
      taetigkeitsart: defaultValues?.taetigkeitsart ?? 'freiberuflich',
      ist_kleinunternehmer: defaultValues?.ist_kleinunternehmer ?? false,
      versteuerungsart: defaultValues?.versteuerungsart ?? 'ist',
      kontenrahmen: defaultValues?.kontenrahmen ?? 'SKR03',
      bezieht_transferleistungen: defaultValues?.bezieht_transferleistungen ?? false,
      ust_idnr: defaultValues?.ust_idnr ?? '',
    },
  })

  const istKleinunternehmer = watch('ist_kleinunternehmer')

  return (
    <form onSubmit={handleSubmit(onNext)} className="space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Rechtsform</label>
          <select {...register('rechtsform')}
            className="w-full rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 dark:text-slate-100">
            <option>Einzelunternehmer</option>
            <option>Freiberufler</option>
            <option>GbR</option>
            <option>UG (haftungsbeschränkt)</option>
            <option>GmbH</option>
            <option>AG</option>
            <option>e.K.</option>
            <option>Eingetragener Verein (e.V.)</option>
            <option>Sonstige</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Tätigkeitsart</label>
          <select {...register('taetigkeitsart')}
            className="w-full rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 dark:text-slate-100">
            <option value="freiberuflich">Freiberuflich</option>
            <option value="gewerbe">Gewerblich</option>
            <option value="gemischt">Gemischt</option>
          </select>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-3 dark:bg-slate-800/50">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Umsatzsteuer</h3>

        <label className="flex items-start gap-3 cursor-pointer">
          <input type="checkbox" {...register('ist_kleinunternehmer')}
            className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600" />
          <div>
            <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Ich bin Kleinunternehmer (§19 UStG)</span>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Jahresumsatz &lt; 25.000 € (ab 2025). Keine USt auf Rechnungen, kein Vorsteuerabzug.
            </p>
          </div>
        </label>

        {!istKleinunternehmer && (
          <>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
                Umsatzsteuer-Identifikationsnummer
              </label>
              <input {...register('ust_idnr')} placeholder="DE123456789"
                className="w-full rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400" />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Versteuerungsart</label>
              <div className="space-y-2">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input type="radio" {...register('versteuerungsart')} value="ist"
                    className="mt-0.5 h-4 w-4 border-slate-300 text-blue-600" />
                  <div>
                    <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Ist-Versteuerung</span>
                    <p className="text-xs text-slate-500 dark:text-slate-400">USt wird fällig wenn das Geld eingeht/ausgeht. Empfohlen für Freiberufler.</p>
                  </div>
                </label>
                <label className="flex items-start gap-3 cursor-pointer">
                  <input type="radio" {...register('versteuerungsart')} value="soll"
                    className="mt-0.5 h-4 w-4 border-slate-300 text-blue-600" />
                  <div>
                    <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Soll-Versteuerung</span>
                    <p className="text-xs text-slate-500 dark:text-slate-400">USt wird mit Rechnungsdatum fällig, unabhängig vom Zahlungseingang.</p>
                  </div>
                </label>
              </div>
            </div>
          </>
        )}
      </div>

      <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-3 dark:bg-slate-800/50">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Kontenrahmen</h3>
        <div className="space-y-2">
          {[
            { value: 'SKR03', label: 'SKR03', desc: 'Standard für Freiberufler & Dienstleister' },
            { value: 'SKR04', label: 'SKR04', desc: 'Standard für Handels- & Industrieunternehmen' },
            { value: 'SKR49', label: 'SKR49', desc: 'Für eingetragene Vereine (e.V.)' },
          ].map(({ value, label, desc }) => (
            <label key={value} className="flex items-start gap-3 cursor-pointer">
              <input type="radio" {...register('kontenrahmen')} value={value}
                className="mt-0.5 h-4 w-4 border-slate-300 text-blue-600" />
              <div>
                <span className="text-sm font-medium text-slate-700 dark:text-slate-200">{label}</span>
                <p className="text-xs text-slate-500 dark:text-slate-400">{desc}</p>
              </div>
            </label>
          ))}
        </div>
      </div>

      <label className="flex items-start gap-3 cursor-pointer">
        <input type="checkbox" {...register('bezieht_transferleistungen')}
          className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600" />
        <div>
          <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Ich beziehe Transferleistungen (ALG II / Bürgergeld)</span>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Aktiviert den EKS-Export (Anlage EKS) für das Jobcenter.
          </p>
        </div>
      </label>

      <div className="pt-2 flex justify-between">
        <button type="button" onClick={onBack}
          className="text-slate-600 dark:text-slate-300 hover:text-slate-800 dark:hover:text-slate-100 font-medium px-4 py-2 rounded-lg transition-colors">
          ← Zurück
        </button>
        <button type="submit"
          className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-6 py-2 rounded-lg transition-colors">
          Weiter →
        </button>
      </div>
    </form>
  )
}
