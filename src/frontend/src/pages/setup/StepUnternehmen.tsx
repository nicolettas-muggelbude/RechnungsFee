import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import type { Unternehmen } from '../../api/client'

// ---------------------------------------------------------------------------
// Berufsgruppen-Konfiguration
// ---------------------------------------------------------------------------

const BERUFSGRUPPEN = [
  { emoji: '💻', label: 'IT / Entwicklung',        wert: 'IT-Freelancer',        kammer: null },
  { emoji: '🎨', label: 'Design / Grafik',          wert: 'Designer/in',          kammer: null },
  { emoji: '✍️', label: 'Text / Journalismus',      wert: 'Journalist/in',        kammer: null },
  { emoji: '📊', label: 'Beratung / Coaching',      wert: 'Berater/in',           kammer: null },
  { emoji: '📣', label: 'Marketing / PR',           wert: 'Marketing-Freelancer', kammer: null },
  { emoji: '🔤', label: 'Übersetzung',              wert: 'Übersetzer/in',        kammer: null },
  { emoji: '⚖️', label: 'Rechtsanwalt/-anwältin',  wert: 'Rechtsanwältin',       kammer: 'Rechtsanwaltskammer' },
  { emoji: '🧮', label: 'Steuerberater/in',         wert: 'Steuerberaterin',      kammer: 'Steuerberaterkammer' },
  { emoji: '🏛️', label: 'Architekt/in',            wert: 'Architektin',          kammer: 'Architektenkammer' },
  { emoji: '🩺', label: 'Arzt / Ärztin',            wert: 'Ärztin',              kammer: 'Ärztekammer' },
  { emoji: '🔧', label: 'Handwerk / Gewerbe',       wert: 'Gewerbetreibende/r',   kammer: null },
  { emoji: '…',  label: 'Sonstiges',                wert: '',                     kammer: null },
] as const

type Berufsgruppe = typeof BERUFSGRUPPEN[number]

// ---------------------------------------------------------------------------

// Erlaubte Zeichen für ZUGFeRD/XRechnung: keine XML-Steuerzeichen (außer Tab, LF, CR)
const xmlSauber = (label: string) =>
  z.string().regex(/^[^\x00-\x08\x0B\x0C\x0E-\x1F\x7F]*$/, `${label} enthält ungültige Zeichen`)

const schema = z.object({
  firmenname:            xmlSauber('Firmenname').max(200, 'Maximal 200 Zeichen').optional().or(z.literal('')),
  vorname:               xmlSauber('Vorname').max(100, 'Maximal 100 Zeichen').optional().or(z.literal('')),
  nachname:              xmlSauber('Nachname').max(100, 'Maximal 100 Zeichen').optional().or(z.literal('')),
  strasse:               xmlSauber('Straße').min(1, 'Straße ist erforderlich').max(200, 'Maximal 200 Zeichen'),
  hausnummer:            z.string().min(1, 'Hausnummer ist erforderlich').max(10, 'Maximal 10 Zeichen'),
  plz:                   z.string()
    .min(4, 'PLZ ist erforderlich')
    .max(10, 'Maximal 10 Zeichen')
    .regex(/^[0-9A-Za-z\s-]+$/, 'PLZ enthält ungültige Zeichen'),
  ort:                   xmlSauber('Ort').min(1, 'Ort ist erforderlich').max(200, 'Maximal 200 Zeichen'),
  email:                 z.string().email('Ungültige E-Mail').optional().or(z.literal('')),
  telefon:               z.string().optional(),
  steuernummer:          z.string().min(1, 'Steuernummer ist erforderlich (§14 UStG – wird für Rechnungen benötigt)'),
  finanzamt:             z.string().optional(),
  berufsbezeichnung:     z.string().optional(),
  kammer_mitgliedschaft: z.string().optional(),
}).superRefine((data, ctx) => {
  const hatFirma = !!(data.firmenname?.trim())
  const hatName  = !!(data.vorname?.trim() || data.nachname?.trim())
  if (!hatFirma && !hatName) {
    ctx.addIssue({ code: 'custom', path: ['firmenname'], message: 'Firmenname oder Vor- und Nachname ist erforderlich' })
  }
})

type FormData = z.infer<typeof schema>

type Props = {
  onNext: (data: Partial<Unternehmen>) => void
  defaultValues?: Partial<Unternehmen>
}

export function StepUnternehmen({ onNext, defaultValues }: Props) {
  const [selectedBeruf, setSelectedBeruf] = useState<Berufsgruppe | null>(null)

  const { register, handleSubmit, setValue, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      ...defaultValues,
      berufsbezeichnung:     defaultValues?.berufsbezeichnung ?? '',
      kammer_mitgliedschaft: defaultValues?.kammer_mitgliedschaft ?? '',
    },
  })

  function handleBerufWahl(beruf: Berufsgruppe) {
    setSelectedBeruf(beruf)
    if (beruf.wert) setValue('berufsbezeichnung', beruf.wert)
    if (beruf.kammer) setValue('kammer_mitgliedschaft', beruf.kammer + ' ')
    else setValue('kammer_mitgliedschaft', '')
  }

  const inp = 'w-full rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400'

  return (
    <form onSubmit={handleSubmit(onNext)} className="space-y-5">

      {/* Berufsauswahl */}
      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
          Welche Tätigkeit übst du aus?
        </label>
        <div className="grid grid-cols-3 gap-2">
          {BERUFSGRUPPEN.map((beruf) => (
            <button
              key={beruf.wert + beruf.label}
              type="button"
              onClick={() => handleBerufWahl(beruf)}
              className={`flex flex-col items-center gap-1 rounded-xl border px-2 py-2.5 text-xs font-medium transition-colors
                ${selectedBeruf?.label === beruf.label
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300'
                  : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:border-blue-300 hover:bg-blue-50 dark:hover:bg-slate-700'}`}
            >
              <span className="text-lg leading-none">{beruf.emoji}</span>
              <span className="text-center leading-tight">{beruf.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Berufsbezeichnung + Kammer (erscheinen nach Auswahl) */}
      {selectedBeruf && (
        <div className="space-y-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 px-4 py-3">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
              Berufsbezeichnung <span className="text-slate-400 font-normal">(erscheint auf Rechnungen)</span>
            </label>
            <input
              {...register('berufsbezeichnung')}
              placeholder="z.B. Rechtsanwältin, IT-Berater, Grafikdesignerin"
              className={inp}
            />
          </div>
          {selectedBeruf.kammer && (
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
                Kammermitgliedschaft <span className="text-slate-400 font-normal">(optional, erscheint im Rechnungs-Footer)</span>
              </label>
              <input
                {...register('kammer_mitgliedschaft')}
                placeholder={`${selectedBeruf.kammer} [Stadt], Mitgl.-Nr. …`}
                className={inp}
              />
            </div>
          )}
        </div>
      )}

      {/* Firmendaten */}
      <div className="space-y-3">
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Firmenname <span className="font-medium">oder</span> Vor- und Nachname ist erforderlich – beides zusammen möglich.
        </p>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
            Firmen- oder Tätigkeitsname
          </label>
          <input
            {...register('firmenname')}
            placeholder="z.B. Maria Muster Webdesign"
            className={inp}
          />
          {errors.firmenname && <p className="text-red-500 text-xs mt-1">{errors.firmenname.message}</p>}
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Vorname</label>
            <input {...register('vorname')} placeholder="Maria" className={inp} />
            {errors.vorname && <p className="text-red-500 text-xs mt-1">{errors.vorname.message}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Nachname</label>
            <input {...register('nachname')} placeholder="Muster" className={inp} />
            {errors.nachname && <p className="text-red-500 text-xs mt-1">{errors.nachname.message}</p>}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2">
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
            Straße <span className="text-red-500">*</span>
          </label>
          <input {...register('strasse')} placeholder="Musterstraße" className={inp} />
          {errors.strasse && <p className="text-red-500 text-xs mt-1">{errors.strasse.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
            Nr. <span className="text-red-500">*</span>
          </label>
          <input {...register('hausnummer')} placeholder="1a" className={inp} />
          {errors.hausnummer && <p className="text-red-500 text-xs mt-1">{errors.hausnummer.message}</p>}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
            PLZ <span className="text-red-500">*</span>
          </label>
          <input {...register('plz')} placeholder="12345" className={inp} />
          {errors.plz && <p className="text-red-500 text-xs mt-1">{errors.plz.message}</p>}
        </div>
        <div className="col-span-2">
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
            Ort <span className="text-red-500">*</span>
          </label>
          <input {...register('ort')} placeholder="Berlin" className={inp} />
          {errors.ort && <p className="text-red-500 text-xs mt-1">{errors.ort.message}</p>}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">E-Mail</label>
          <input {...register('email')} type="email" placeholder="maria@beispiel.de" className={inp} />
          {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Telefon</label>
          <input {...register('telefon')} placeholder="+49 30 12345678" className={inp} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
            Steuernummer <span className="text-red-500">*</span>
          </label>
          <input {...register('steuernummer')} placeholder="12/345/67890" className={inp} />
          {errors.steuernummer && <p className="text-red-500 text-xs mt-1">{errors.steuernummer.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Finanzamt</label>
          <input {...register('finanzamt')} placeholder="Finanzamt Berlin-Mitte" className={inp} />
        </div>
      </div>

      <div className="pt-2 flex justify-end">
        <button type="submit"
          className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-6 py-2 rounded-lg transition-colors">
          Weiter →
        </button>
      </div>
    </form>
  )
}
