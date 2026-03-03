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

const schema = z.object({
  firmenname:            z.string().min(1, 'Name ist erforderlich'),
  vorname:               z.string().optional(),
  nachname:              z.string().optional(),
  strasse:               z.string().min(1, 'Straße ist erforderlich'),
  hausnummer:            z.string().min(1, 'Hausnummer ist erforderlich'),
  plz:                   z.string().min(4, 'PLZ ist erforderlich'),
  ort:                   z.string().min(1, 'Ort ist erforderlich'),
  email:                 z.string().email('Ungültige E-Mail').optional().or(z.literal('')),
  telefon:               z.string().optional(),
  steuernummer:          z.string().optional(),
  finanzamt:             z.string().optional(),
  berufsbezeichnung:     z.string().optional(),
  kammer_mitgliedschaft: z.string().optional(),
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

  const inp = 'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'

  return (
    <form onSubmit={handleSubmit(onNext)} className="space-y-5">

      {/* Berufsauswahl */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">
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
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-slate-200 bg-white text-slate-600 hover:border-blue-300 hover:bg-blue-50'}`}
            >
              <span className="text-lg leading-none">{beruf.emoji}</span>
              <span className="text-center leading-tight">{beruf.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Berufsbezeichnung + Kammer (erscheinen nach Auswahl) */}
      {selectedBeruf && (
        <div className="space-y-3 rounded-xl bg-slate-50 border border-slate-200 px-4 py-3">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
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
              <label className="block text-sm font-medium text-slate-700 mb-1">
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
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Firmen- oder Tätigkeitsname <span className="text-red-500">*</span>
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
          <label className="block text-sm font-medium text-slate-700 mb-1">Vorname</label>
          <input {...register('vorname')} placeholder="Maria" className={inp} />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Nachname</label>
          <input {...register('nachname')} placeholder="Muster" className={inp} />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2">
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Straße <span className="text-red-500">*</span>
          </label>
          <input {...register('strasse')} placeholder="Musterstraße" className={inp} />
          {errors.strasse && <p className="text-red-500 text-xs mt-1">{errors.strasse.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Nr. <span className="text-red-500">*</span>
          </label>
          <input {...register('hausnummer')} placeholder="1a" className={inp} />
          {errors.hausnummer && <p className="text-red-500 text-xs mt-1">{errors.hausnummer.message}</p>}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            PLZ <span className="text-red-500">*</span>
          </label>
          <input {...register('plz')} placeholder="12345" className={inp} />
          {errors.plz && <p className="text-red-500 text-xs mt-1">{errors.plz.message}</p>}
        </div>
        <div className="col-span-2">
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Ort <span className="text-red-500">*</span>
          </label>
          <input {...register('ort')} placeholder="Berlin" className={inp} />
          {errors.ort && <p className="text-red-500 text-xs mt-1">{errors.ort.message}</p>}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">E-Mail</label>
          <input {...register('email')} type="email" placeholder="maria@beispiel.de" className={inp} />
          {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Telefon</label>
          <input {...register('telefon')} placeholder="+49 30 12345678" className={inp} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Steuernummer</label>
          <input {...register('steuernummer')} placeholder="12/345/67890" className={inp} />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Finanzamt</label>
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
