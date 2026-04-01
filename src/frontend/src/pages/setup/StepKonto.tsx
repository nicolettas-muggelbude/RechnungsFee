import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import type { Konto } from '../../api/client'

const schema = z.object({
  name: z.string().min(1, 'Name ist erforderlich'),
  bank: z.string().min(1, 'Bank ist erforderlich'),
  iban: z
    .string()
    .min(1, 'IBAN ist erforderlich')
    .transform((v) => v.replace(/\s/g, '').toUpperCase())
    .refine((v) => v.length >= 15 && v.length <= 34, 'Ungültige IBAN-Länge'),
  bic: z.string().optional(),
  kontotyp: z.enum(['geschaeftlich', 'mischkonto', 'privat']),
})

type FormData = z.infer<typeof schema>

type Props = {
  onNext: (data: Omit<Konto, 'id' | 'aktiv' | 'ist_standard'>) => void
  onBack: () => void
  isLoading?: boolean
}

export function StepKonto({ onNext, onBack, isLoading }: Props) {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { kontotyp: 'geschaeftlich' },
  })

  return (
    <form onSubmit={handleSubmit(onNext)} className="space-y-5">
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Gib dein Geschäftskonto an. Du kannst später weitere Konten hinzufügen.
      </p>

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
          Kontobezeichnung <span className="text-red-500">*</span>
        </label>
        <input {...register('name')} placeholder="z.B. Geschäftskonto"
          className="w-full rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400" />
        {errors.name && <p className="text-red-500 text-xs mt-1">{errors.name.message}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
          Bank <span className="text-red-500">*</span>
        </label>
        <input {...register('bank')} placeholder="z.B. Sparkasse Berlin"
          className="w-full rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400" />
        {errors.bank && <p className="text-red-500 text-xs mt-1">{errors.bank.message}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
          IBAN <span className="text-red-500">*</span>
        </label>
        <input {...register('iban')} placeholder="DE44 2004 0060 0526 0120 00"
          className="w-full rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400" />
        {errors.iban && <p className="text-red-500 text-xs mt-1">{errors.iban.message}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">BIC / SWIFT</label>
        <input {...register('bic')} placeholder="COBADEFFXXX"
          className="w-full rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400" />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Kontotyp</label>
        <div className="space-y-2">
          {[
            { value: 'geschaeftlich', label: 'Rein geschäftlich', desc: 'Alle Buchungen sind Betriebseinnahmen/-ausgaben.' },
            { value: 'mischkonto', label: 'Mischkonto', desc: 'Private und geschäftliche Buchungen werden getrennt klassifiziert.' },
          ].map(({ value, label, desc }) => (
            <label key={value} className="flex items-start gap-3 cursor-pointer">
              <input type="radio" {...register('kontotyp')} value={value}
                className="mt-0.5 h-4 w-4 border-slate-300 text-blue-600" />
              <div>
                <span className="text-sm font-medium text-slate-700 dark:text-slate-200">{label}</span>
                <p className="text-xs text-slate-500 dark:text-slate-400">{desc}</p>
              </div>
            </label>
          ))}
        </div>
      </div>

      <div className="pt-2 flex justify-between">
        <button type="button" onClick={onBack}
          className="text-slate-600 dark:text-slate-300 hover:text-slate-800 dark:hover:text-slate-100 font-medium px-4 py-2 rounded-lg transition-colors">
          ← Zurück
        </button>
        <button type="submit" disabled={isLoading}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium px-6 py-2 rounded-lg transition-colors">
          {isLoading ? 'Speichern…' : 'Einrichtung abschließen ✓'}
        </button>
      </div>
    </form>
  )
}
