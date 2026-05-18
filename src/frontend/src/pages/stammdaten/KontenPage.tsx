import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { getKontenAlle, createKonto, updateKonto, deleteKonto, type Konto } from '../../api/client'

const TYPEN: Record<Konto['kontotyp'], { label: string; cls: string }> = {
  geschaeftlich: { label: 'Geschäftlich', cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' },
  mischkonto:    { label: 'Mischkonto',   cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300' },
  privat:        { label: 'Privat',        cls: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300' },
}

const schema = z.object({
  name:         z.string().min(1, 'Name erforderlich'),
  bank:         z.string().min(1, 'Bank erforderlich'),
  iban:         z.string().min(15, 'IBAN zu kurz').max(34, 'IBAN zu lang'),
  bic:          z.string().optional().or(z.literal('')),
  kontotyp:     z.enum(['geschaeftlich', 'mischkonto', 'privat']),
  ist_standard: z.boolean(),
})
type FormValues = z.infer<typeof schema>

const LEER: FormValues = {
  name: '', bank: '', iban: '', bic: '', kontotyp: 'geschaeftlich', ist_standard: false,
}

function formatIban(iban: string) {
  return iban.replace(/(.{4})/g, '$1 ').trim()
}

// ---------------------------------------------------------------------------
// Modal
// ---------------------------------------------------------------------------

function KontoModal({ konto, onClose }: { konto: Konto | null; onClose: () => void }) {
  const qc = useQueryClient()
  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: konto ? {
      name: konto.name,
      bank: konto.bank,
      iban: konto.iban,
      bic: konto.bic ?? '',
      kontotyp: konto.kontotyp,
      ist_standard: konto.ist_standard,
    } : LEER,
  })

  const create = useMutation({
    mutationFn: createKonto,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['konten'] }); onClose() },
  })
  const update = useMutation({
    mutationFn: (data: FormValues) => updateKonto(konto!.id!, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['konten'] }); onClose() },
  })

  const mutation = konto ? update : create
  const serverFehler = (mutation.error as any)?.message ?? null

  function onSubmit(data: FormValues) {
    const payload = { ...data, bic: data.bic || undefined }
    if (konto) update.mutate(payload)
    else create.mutate(payload)
  }

  const inp = 'w-full border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="w-full max-w-md bg-white dark:bg-slate-800 rounded-2xl shadow-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
            {konto ? 'Konto bearbeiten' : 'Neues Konto'}
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xl p-1">✕</button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="px-6 py-5 space-y-4">
          <div>
            <label className="block text-xs text-slate-500 dark:text-slate-400 mb-0.5">Bezeichnung</label>
            <input {...register('name')} placeholder="z.B. Geschäftskonto Sparkasse" className={inp} />
            {errors.name && <p className="text-xs text-red-500 mt-0.5">{errors.name.message}</p>}
          </div>
          <div>
            <label className="block text-xs text-slate-500 dark:text-slate-400 mb-0.5">Bank</label>
            <input {...register('bank')} placeholder="z.B. Sparkasse München" className={inp} />
            {errors.bank && <p className="text-xs text-red-500 mt-0.5">{errors.bank.message}</p>}
          </div>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-xs text-slate-500 dark:text-slate-400 mb-0.5">IBAN</label>
              <input {...register('iban')} placeholder="DE89 3704 0044 …" className={inp} />
              {errors.iban && <p className="text-xs text-red-500 mt-0.5">{errors.iban.message}</p>}
            </div>
            <div className="w-36">
              <label className="block text-xs text-slate-500 dark:text-slate-400 mb-0.5">BIC (optional)</label>
              <input {...register('bic')} placeholder="COBADEFF" className={inp} />
            </div>
          </div>
          <div>
            <label className="block text-xs text-slate-500 dark:text-slate-400 mb-0.5">Kontotyp</label>
            <select {...register('kontotyp')} className={inp}>
              <option value="geschaeftlich">Geschäftlich</option>
              <option value="mischkonto">Mischkonto (privat &amp; geschäftlich)</option>
              <option value="privat">Privat</option>
            </select>
          </div>
          <label className="flex items-center gap-2 cursor-pointer text-sm text-slate-700 dark:text-slate-300">
            <input type="checkbox" {...register('ist_standard')} className="h-4 w-4 rounded border-slate-300 dark:border-slate-600 accent-blue-600" />
            Als Standard-Konto verwenden
          </label>

          {serverFehler && <p className="text-sm text-red-600 dark:text-red-400">{serverFehler}</p>}

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors">
              Abbrechen
            </button>
            <button type="submit" disabled={mutation.isPending} className="px-5 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg transition-colors">
              {mutation.isPending ? 'Speichert…' : 'Speichern'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// KontenPage
// ---------------------------------------------------------------------------

export function KontenPage() {
  const qc = useQueryClient()
  const [modal, setModal] = useState<'neu' | Konto | null>(null)
  const [zuLoeschen, setZuLoeschen] = useState<Konto | null>(null)
  const [loeschFehler, setLoeschFehler] = useState<string | null>(null)

  const { data: konten = [], isLoading } = useQuery({
    queryKey: ['konten'],
    queryFn: getKontenAlle,
  })

  const toggleAktiv = useMutation({
    mutationFn: (k: Konto) => updateKonto(k.id!, { aktiv: !k.aktiv }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['konten'] }),
  })

  const loeschen = useMutation({
    mutationFn: (id: number) => deleteKonto(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['konten'] })
      setZuLoeschen(null)
      setLoeschFehler(null)
    },
    onError: (e: any) => setLoeschFehler(e?.message ?? 'Löschen fehlgeschlagen'),
  })

  return (
    <div className="p-6 max-w-2xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Bankkonten</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Konten für den Bank-Import und automatische Buchungszuordnung
          </p>
        </div>
        <button
          onClick={() => setModal('neu')}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          + Neues Konto
        </button>
      </div>

      {/* Ladelzustand */}
      {isLoading && <p className="text-slate-400 text-sm">Lade…</p>}

      {/* Leer-Zustand */}
      {!isLoading && konten.length === 0 && (
        <div className="text-center py-16 text-slate-400 dark:text-slate-500">
          <p className="text-4xl mb-3">🏦</p>
          <p className="font-medium">Noch keine Konten hinterlegt</p>
          <p className="text-xs mt-1 opacity-70">
            Füge dein Geschäftskonto hinzu – es wird für den Bank-Import benötigt.
          </p>
        </div>
      )}

      {/* Karten */}
      <div className="space-y-3">
        {konten.map(k => (
          <div
            key={k.id}
            className={`bg-white dark:bg-slate-800 border rounded-xl px-5 py-4 flex items-start justify-between gap-4 transition-opacity ${
              k.aktiv
                ? 'border-slate-200 dark:border-slate-700'
                : 'border-slate-100 dark:border-slate-800 opacity-50'
            }`}
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-slate-800 dark:text-slate-100">{k.name}</span>
                {k.ist_standard && (
                  <span className="text-xs bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300 px-2 py-0.5 rounded-full font-medium">
                    Standard
                  </span>
                )}
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${TYPEN[k.kontotyp].cls}`}>
                  {TYPEN[k.kontotyp].label}
                </span>
                {!k.aktiv && (
                  <span className="text-xs bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400 px-2 py-0.5 rounded-full">
                    Inaktiv
                  </span>
                )}
              </div>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{k.bank}</p>
              <p className="font-mono text-sm text-slate-700 dark:text-slate-300 mt-1">{formatIban(k.iban)}</p>
              {k.bic && <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">BIC: {k.bic}</p>}
            </div>
            <div className="flex items-center gap-1 shrink-0 pt-0.5">
              <button
                onClick={() => setModal(k)}
                title="Bearbeiten"
                className="p-1.5 text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >✏️</button>
              <button
                onClick={() => toggleAktiv.mutate(k)}
                title={k.aktiv ? 'Deaktivieren' : 'Aktivieren'}
                className="p-1.5 text-slate-400 hover:text-amber-600 dark:hover:text-amber-400 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >{k.aktiv ? '🔒' : '🔓'}</button>
              <button
                onClick={() => { setZuLoeschen(k); setLoeschFehler(null) }}
                title="Löschen"
                className="p-1.5 text-slate-400 hover:text-red-600 dark:hover:text-red-400 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >🗑️</button>
            </div>
          </div>
        ))}
      </div>

      {/* Neu / Bearbeiten Modal */}
      {modal !== null && (
        <KontoModal
          konto={modal === 'neu' ? null : modal}
          onClose={() => setModal(null)}
        />
      )}

      {/* Löschen-Bestätigung */}
      {zuLoeschen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-sm bg-white dark:bg-slate-800 rounded-2xl shadow-2xl p-6">
            <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-2">Konto löschen?</h3>
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">
              <strong>{zuLoeschen.name}</strong> ({formatIban(zuLoeschen.iban)}) wird unwiderruflich gelöscht.
            </p>
            <p className="text-xs text-slate-400 dark:text-slate-500 mb-4">
              Konten mit verknüpften Transaktionen können nicht gelöscht werden – deaktiviere sie stattdessen.
            </p>
            {loeschFehler && <p className="text-sm text-red-600 dark:text-red-400 mb-3">{loeschFehler}</p>}
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setZuLoeschen(null)}
                className="px-4 py-2 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >Abbrechen</button>
              <button
                onClick={() => loeschen.mutate(zuLoeschen.id!)}
                disabled={loeschen.isPending}
                className="px-4 py-2 text-sm font-medium bg-red-600 hover:bg-red-700 disabled:bg-red-300 text-white rounded-lg transition-colors"
              >{loeschen.isPending ? 'Löscht…' : 'Löschen'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
