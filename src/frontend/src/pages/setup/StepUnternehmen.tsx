import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import type { Unternehmen } from '../../api/client'

const schema = z.object({
  firmenname: z.string().min(1, 'Name ist erforderlich'),
  vorname: z.string().optional(),
  nachname: z.string().optional(),
  strasse: z.string().min(1, 'Straße ist erforderlich'),
  hausnummer: z.string().min(1, 'Hausnummer ist erforderlich'),
  plz: z.string().min(4, 'PLZ ist erforderlich'),
  ort: z.string().min(1, 'Ort ist erforderlich'),
  email: z.string().email('Ungültige E-Mail').optional().or(z.literal('')),
  telefon: z.string().optional(),
  steuernummer: z.string().optional(),
  finanzamt: z.string().optional(),
})

type FormData = z.infer<typeof schema>

type Props = {
  onNext: (data: Partial<Unternehmen>) => void
  defaultValues?: Partial<Unternehmen>
}

export function StepUnternehmen({ onNext, defaultValues }: Props) {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: defaultValues ?? {},
  })

  return (
    <form onSubmit={handleSubmit(onNext)} className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Firmen- oder Tätigkeitsname <span className="text-red-500">*</span>
        </label>
        <input
          {...register('firmenname')}
          placeholder="z.B. Maria Muster Webdesign"
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {errors.firmenname && <p className="text-red-500 text-xs mt-1">{errors.firmenname.message}</p>}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Vorname</label>
          <input {...register('vorname')} placeholder="Maria"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Nachname</label>
          <input {...register('nachname')} placeholder="Muster"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2">
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Straße <span className="text-red-500">*</span>
          </label>
          <input {...register('strasse')} placeholder="Musterstraße"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          {errors.strasse && <p className="text-red-500 text-xs mt-1">{errors.strasse.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Nr. <span className="text-red-500">*</span>
          </label>
          <input {...register('hausnummer')} placeholder="1a"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          {errors.hausnummer && <p className="text-red-500 text-xs mt-1">{errors.hausnummer.message}</p>}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            PLZ <span className="text-red-500">*</span>
          </label>
          <input {...register('plz')} placeholder="12345"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          {errors.plz && <p className="text-red-500 text-xs mt-1">{errors.plz.message}</p>}
        </div>
        <div className="col-span-2">
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Ort <span className="text-red-500">*</span>
          </label>
          <input {...register('ort')} placeholder="Berlin"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          {errors.ort && <p className="text-red-500 text-xs mt-1">{errors.ort.message}</p>}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">E-Mail</label>
          <input {...register('email')} type="email" placeholder="maria@beispiel.de"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Telefon</label>
          <input {...register('telefon')} placeholder="+49 30 12345678"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Steuernummer</label>
          <input {...register('steuernummer')} placeholder="12/345/67890"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Finanzamt</label>
          <input {...register('finanzamt')} placeholder="Finanzamt Berlin-Mitte"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
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
