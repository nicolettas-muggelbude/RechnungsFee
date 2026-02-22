import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { createUnternehmen, createKonto, type Unternehmen, type Konto } from '../../api/client'
import { StepUnternehmen } from './StepUnternehmen'
import { StepSteuern } from './StepSteuern'
import { StepKonto } from './StepKonto'

const STEPS = [
  { label: 'Meine Daten', desc: 'Name & Adresse' },
  { label: 'Steuerliches', desc: 'USt & Kontenrahmen' },
  { label: 'Bankkonto', desc: 'Erstes Konto' },
]

export function SetupWizard() {
  const [step, setStep] = useState(0)
  const [formData, setFormData] = useState<Partial<Unternehmen>>({})
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const saveMutation = useMutation({
    mutationFn: async (kontoData: Omit<Konto, 'id' | 'aktiv' | 'ist_standard'>) => {
      await createUnternehmen({
        ...formData,
        land: 'DE',
        ist_kleinunternehmer: formData.ist_kleinunternehmer ?? false,
        bezieht_transferleistungen: formData.bezieht_transferleistungen ?? false,
        versteuerungsart: formData.versteuerungsart ?? 'ist',
        kontenrahmen: formData.kontenrahmen ?? 'SKR03',
        taetigkeitsart: formData.taetigkeitsart ?? 'freiberuflich',
        rechtsform: formData.rechtsform ?? 'Einzelunternehmer',
      } as Unternehmen)
      await createKonto({ ...kontoData, ist_standard: true })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['setup-status'] })
      navigate('/', { replace: true })
    },
    onError: (err: Error) => setError(err.message),
  })

  const handleStep0 = (data: Partial<Unternehmen>) => {
    setFormData((prev) => ({ ...prev, ...data }))
    setStep(1)
  }

  const handleStep1 = (data: Partial<Unternehmen>) => {
    setFormData((prev) => ({ ...prev, ...data }))
    setStep(2)
  }

  const handleStep2 = (data: Omit<Konto, 'id' | 'aktiv' | 'ist_standard'>) => {
    setError(null)
    saveMutation.mutate(data)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-slate-800">🧾 RechnungsFee</h1>
          <p className="text-slate-500 mt-1">Einrichtung in 3 Schritten</p>
        </div>

        {/* Fortschrittsanzeige */}
        <div className="flex items-center mb-8">
          {STEPS.map((s, i) => (
            <div key={i} className="flex-1 flex items-center">
              <div className="flex flex-col items-center">
                <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold transition-colors ${
                  i < step ? 'bg-green-500 text-white' :
                  i === step ? 'bg-blue-600 text-white' :
                  'bg-slate-200 text-slate-500'
                }`}>
                  {i < step ? '✓' : i + 1}
                </div>
                <div className="text-center mt-1">
                  <p className={`text-xs font-medium ${i === step ? 'text-blue-700' : 'text-slate-500'}`}>{s.label}</p>
                  <p className="text-xs text-slate-400 hidden sm:block">{s.desc}</p>
                </div>
              </div>
              {i < STEPS.length - 1 && (
                <div className={`flex-1 h-0.5 mx-2 mb-5 ${i < step ? 'bg-green-400' : 'bg-slate-200'}`} />
              )}
            </div>
          ))}
        </div>

        {/* Formular-Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-1">{STEPS[step].label}</h2>
          <p className="text-sm text-slate-500 mb-5">{STEPS[step].desc}</p>

          {error && (
            <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              ⚠️ {error}
            </div>
          )}

          {step === 0 && <StepUnternehmen onNext={handleStep0} defaultValues={formData} />}
          {step === 1 && <StepSteuern onNext={handleStep1} onBack={() => setStep(0)} defaultValues={formData} />}
          {step === 2 && <StepKonto onNext={handleStep2} onBack={() => setStep(1)} isLoading={saveMutation.isPending} />}
        </div>

        <p className="text-center text-xs text-slate-400 mt-6">
          Du kannst alle Angaben später unter Einstellungen ändern.
        </p>
      </div>
    </div>
  )
}
