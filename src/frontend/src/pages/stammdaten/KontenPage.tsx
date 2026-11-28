import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { getKontenAlle, createKonto, updateKonto, deleteKonto, getUnternehmen, type Konto } from '../../api/client'
import { useMxAuto } from '../../hooks/useAnsicht'
import { InfoTooltip } from '../../components/InfoTooltip'
import { validiereIban, ladeOpenIbanDaten, OPEN_IBAN_BANK_FALLBACK, OPEN_IBAN_BIC_FALLBACK, openIbanBankdatenFehlgeschlagen, OPEN_IBAN_LAND_TOOLTIP } from '../../utils/iban'

const KONTOARTEN: Record<Konto['kontoart'], { label: string; cls: string }> = {
  bank:                  { label: 'Bankkonto',             cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' },
  zahlungsdienstleister: { label: 'Zahlungsdienstleister', cls: 'bg-violet-100 text-violet-700 dark:bg-violet-900 dark:text-violet-300' },
}

const KONTOTYPEN: Record<Konto['kontotyp'], string> = {
  geschaeftlich: 'Geschäftlich',
  mischkonto:    'Mischkonto',
  privat:        'Privat',
}

const schema = z.discriminatedUnion('kontoart', [
  z.object({
    kontoart:          z.literal('bank'),
    name:              z.string().min(1, 'Name erforderlich'),
    anbieter:          z.string().min(1, 'Bank erforderlich'),
    iban: z
      .string()
      .min(1, 'IBAN erforderlich')
      .transform((v) => v.replace(/\s/g, '').toUpperCase())
      .superRefine((v, ctx) => {
        const fehler = validiereIban(v)
        if (fehler) ctx.addIssue({ code: 'custom', message: fehler })
      }),
    bic:               z.string().optional().or(z.literal('')),
    kennung:           z.string().optional(),
    kontotyp:          z.enum(['geschaeftlich', 'mischkonto', 'privat']),
    ist_standard:      z.boolean(),
    datev_kontonummer: z.string().optional().or(z.literal('')),
    kontoinhaber:      z.string().max(70, 'Höchstens 70 Zeichen (Grenze des QR-Codes)').optional().or(z.literal('')),
  }),
  z.object({
    kontoart:          z.literal('zahlungsdienstleister'),
    name:              z.string().min(1, 'Name erforderlich'),
    anbieter:          z.string().min(1, 'Anbieter erforderlich'),
    iban:              z.string().optional(),
    bic:               z.string().optional(),
    kennung:           z.string().min(1, 'Kennung erforderlich (z.B. E-Mail-Adresse)'),
    kontotyp:          z.enum(['geschaeftlich', 'mischkonto', 'privat']),
    ist_standard:      z.boolean(),
    datev_kontonummer: z.string().optional().or(z.literal('')),
    kontoinhaber:      z.string().optional().or(z.literal('')),
  }),
])
type FormValues = z.infer<typeof schema>

function defaultValues(konto: Konto | null): FormValues {
  if (konto) return {
    kontoart:          konto.kontoart,
    name:              konto.name,
    anbieter:          konto.anbieter,
    iban:              konto.iban ?? '',
    bic:               konto.bic ?? '',
    kennung:           konto.kennung ?? '',
    kontotyp:          konto.kontotyp,
    ist_standard:      konto.ist_standard,
    datev_kontonummer: konto.datev_kontonummer ?? '',
    kontoinhaber:      konto.kontoinhaber ?? '',
  }
  return {
    kontoart: 'bank', name: '', anbieter: '', iban: '', bic: '',
    kennung: '', kontotyp: 'geschaeftlich', ist_standard: false,
    datev_kontonummer: '', kontoinhaber: '',
  }
}

function defaultValuesWithIban(iban: string): FormValues {
  return { kontoart: 'bank', name: '', anbieter: '', iban, bic: '',
    kennung: '', kontotyp: 'geschaeftlich', ist_standard: false, datev_kontonummer: '', kontoinhaber: '' }
}

function formatIban(iban: string) {
  return iban.replace(/(.{4})/g, '$1 ').trim()
}

// ---------------------------------------------------------------------------
// Modal
// ---------------------------------------------------------------------------

function KontoModal({ konto, initialIban, onClose }: { konto: Konto | null; initialIban?: string; onClose: () => void }) {
  const qc = useQueryClient()
  const { register, handleSubmit, control, getValues, setValue, trigger, clearErrors, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: konto ? defaultValues(konto) : initialIban ? defaultValuesWithIban(initialIban) : defaultValues(null),
  })
  const kontoart = useWatch({ control, name: 'kontoart' })
  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen, staleTime: 1000 * 60 * 10 })
  const standardInhaber = (unternehmen?.firmenname ?? '').trim()
    || [unternehmen?.vorname, unternehmen?.nachname].filter(Boolean).join(' ')
  const [bankFehler, setBankFehler] = useState<string | null>(null)
  const [bicFehler, setBicFehler] = useState<string | null>(null)

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
    const payload = {
      ...data,
      bic:               data.bic               || undefined,
      kennung:           data.kennung           || undefined,
      iban:              data.iban              || undefined,
      datev_kontonummer: data.datev_kontonummer || undefined,
      // Issue #604: leer mitsenden, damit „zurück auf Standard“ beim Bearbeiten wirkt
      kontoinhaber:      data.kontoart === 'bank' ? (data.kontoinhaber ?? '').trim() : undefined,
    }
    if (konto) update.mutate(payload as FormValues)
    else create.mutate(payload as FormValues)
  }

  async function handleOpenIbanLookup() {
    const iban = getValues('iban')?.replace(/\s/g, '').toUpperCase()
    if (!iban) return

    setBankFehler(null)
    setBicFehler(null)

    try {
      const data = await ladeOpenIbanDaten(iban)
      if (data.valid) {
        const bic = data.bankData?.bic ?? ''
        const name = data.bankData?.name ?? ''
        if (!bic || !name) {
          const msg = openIbanBankdatenFehlgeschlagen(iban)
          setBankFehler(msg)
          setBicFehler(msg)
        }
        if (bic) setValue('bic', bic, { shouldDirty: true, shouldValidate: true })
        if (name) setValue('anbieter', name, { shouldDirty: true, shouldValidate: true })
        return
      }
    } catch {
      // bewusst still: lokale Validierung bleibt maßgeblich
    }

    setBankFehler(OPEN_IBAN_BANK_FALLBACK)
    setBicFehler(OPEN_IBAN_BIC_FALLBACK)
  }

  const inp = 'w-full border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
  const err = (msg?: string) => msg ? <p className="text-xs text-red-500 mt-0.5">{msg}</p> : null

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

          {/* Kontoart */}
          <div>
            <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Kontoart</label>
            <div className="flex gap-2">
              {(['bank', 'zahlungsdienstleister'] as const).map(art => (
                <label key={art} className="flex-1 cursor-pointer">
                  <input type="radio" value={art} {...register('kontoart')} className="sr-only" />
                  <span className={`block text-center text-sm py-2 rounded-lg border transition-colors ${
                    kontoart === art
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
                  }`}>
                    {art === 'bank' ? '🏦 Bankkonto' : '💳 Zahlungsdienstleister'}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Name */}
          <div>
            <label className="block text-xs text-slate-500 dark:text-slate-400 mb-0.5">Bezeichnung</label>
            <input {...register('name')} placeholder="z.B. Geschäftskonto Sparkasse" className={inp} />
            {err(errors.name?.message)}
          </div>

          {/* Anbieter */}
          <div>
            <label className="block text-xs text-slate-500 dark:text-slate-400 mb-0.5">
              {kontoart === 'bank' ? 'Bank' : 'Anbieter'}
            </label>
            <input
              {...register('anbieter')}
              placeholder={kontoart === 'bank' ? 'z.B. Sparkasse München' : 'z.B. PayPal, Stripe'}
              className={inp}
            />
            {err(errors.anbieter?.message)}
          </div>

          {/* Bankfelder */}
          {kontoart === 'bank' && (
            <>
              {/* Issue #604: Kontoinhaber für QR-Code und E-Rechnung – zwischen Bank und IBAN wie im Onlinebanking */}
              <div>
                <label className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 mb-0.5">
                  Kontoinhaber (optional)
                  <InfoTooltip text="So, wie der Name bei deiner Bank hinterlegt ist. Banken prüfen vor einer Überweisung, ob der Empfängername zum Konto passt. Ist dieses Konto die IBAN auf deinen Rechnungen, steht der Name im Überweisungs-QR-Code, im Zahlungsblock und in der E-Rechnung. Leer lassen: Firmenname bzw. dein Vor- und Nachname aus den Stammdaten." />
                </label>
                <input
                  {...register('kontoinhaber')}
                  placeholder={standardInhaber ? `Standard: ${standardInhaber}` : 'z.B. Max Mustermann'}
                  maxLength={70}
                  className={inp}
                />
                {err((errors as any).kontoinhaber?.message)}
                <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">
                  Nur nötig, wenn das Konto nicht auf deinen Firmennamen läuft, z. B. als Einzelunternehmer mit Konto auf deinen eigenen Namen.
                </p>
              </div>
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="block text-xs text-slate-500 dark:text-slate-400 mb-0.5">IBAN</label>
                  <input
                    {...register('iban', {
                      onChange: (e) => {
                        const el = e.target
                        const ns = el.value.slice(0, el.selectionStart ?? el.value.length).replace(/\s/g, '').length
                        const raw = el.value.replace(/\s/g, '').toUpperCase()
                        const formatted = raw.replace(/(.{4})/g, '$1 ').trimEnd()
                        setValue('iban', formatted)
                        if (raw.length > 0) {
                          trigger('iban')
                        } else {
                          clearErrors('iban')
                        }
                        setBankFehler(null)
                        setBicFehler(null)
                        setTimeout(() => {
                          let p = 0, c = 0
                          for (let i = 0; i <= formatted.length; i++) {
                            if (c === ns) { p = i; break }
                            if (formatted[i] !== ' ') c++
                          }
                          el.setSelectionRange(p, p)
                        }, 0)
                      },
                    })}
                    placeholder="DE89 3704 0044 ..."
                    className={inp}
                  />
                  {err((errors as any).iban?.message)}
                  {bankFehler && <p className="mt-1 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400 inline-flex items-center gap-1">{bankFehler}{bankFehler.startsWith('Für IBANs') && <InfoTooltip text={OPEN_IBAN_LAND_TOOLTIP} />}</p>}
                </div>
            <div className="w-36">
                  <label className="block text-xs text-slate-500 dark:text-slate-400 mb-0.5">BIC (optional)</label>
              <input {...register('bic')} placeholder="COBADEFF" className={inp} />
              {bicFehler && <p className="mt-1 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400 inline-flex items-center gap-1">{bicFehler}{bicFehler.startsWith('Für IBANs') && <InfoTooltip text={OPEN_IBAN_LAND_TOOLTIP} />}</p>}
            </div>
          </div>
              <button
                type="button"
                onClick={handleOpenIbanLookup}
                className="w-full inline-flex items-center justify-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm font-medium text-blue-700 hover:bg-blue-100 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-300 dark:hover:bg-blue-900"
              >
                <span>↗</span>
                <span>Bankname und BIC aus IBAN per Web</span>
              </button>
              <p className="text-xs text-slate-400 dark:text-slate-500 text-center">Sendet deine IBAN an openiban.com (Fremdanbieter) zur Abfrage</p>
            </>
          )}

          {/* Kennung für Zahlungsdienstleister */}
          {kontoart === 'zahlungsdienstleister' && (
            <div>
              <label className="block text-xs text-slate-500 dark:text-slate-400 mb-0.5">
                Kennung (E-Mail, Account-ID o.ä.)
              </label>
              <input {...register('kennung')} placeholder="z.B. meine@email.de" className={inp} />
              {err((errors as any).kennung?.message)}
            </div>
          )}

          {/* Kontotyp */}
          <div>
            <label className="block text-xs text-slate-500 dark:text-slate-400 mb-0.5">Verwendung</label>
            <select {...register('kontotyp')} className={inp}>
              <option value="geschaeftlich">Geschäftlich</option>
              <option value="mischkonto">Mischkonto (privat &amp; geschäftlich)</option>
              <option value="privat">Privat (nicht für Bank-Import verfügbar)</option>
            </select>
          </div>

          {/* DATEV-Kontonummer */}
          <div>
            <label className="block text-xs text-slate-500 dark:text-slate-400 mb-0.5">
              DATEV-Kontonummer (optional)
            </label>
            <input
              {...register('datev_kontonummer')}
              placeholder="z.B. 1200"
              maxLength={8}
              className={inp}
            />
            <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">
              Wird im DATEV-Export als Gegenkonto verwendet (überschreibt den globalen Wert unter Einstellungen → DATEV)
            </p>
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
  const mxAuto = useMxAuto()
  const qc = useQueryClient()
  const [modal, setModal] = useState<'neu' | Konto | null>(null)
  const [initialIban, setInitialIban] = useState<string | undefined>()
  const [zuLoeschen, setZuLoeschen] = useState<Konto | null>(null)
  const [loeschFehler, setLoeschFehler] = useState<string | null>(null)
  const [searchParams] = useSearchParams()

  useEffect(() => {
    const iban = searchParams.get('iban')
    if (iban) { setInitialIban(iban); setModal('neu') }
  }, [])

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
    <div className={`p-6 max-w-2xl ${mxAuto}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Bankkonten</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Bankkonten und Zahlungsdienstleister für den Bank-Import
          </p>
        </div>
        <button
          onClick={() => setModal('neu')}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          + Neues Konto
        </button>
      </div>

      {isLoading && <p className="text-slate-400 text-sm">Lade…</p>}

      {!isLoading && konten.length === 0 && (
        <div className="text-center py-16 text-slate-400 dark:text-slate-500">
          <p className="text-4xl mb-3">🏦</p>
          <p className="font-medium">Noch keine Konten hinterlegt</p>
          <p className="text-xs mt-1 opacity-70">
            Füge dein Geschäftskonto oder einen Zahlungsdienstleister hinzu.
          </p>
        </div>
      )}

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
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${KONTOARTEN[k.kontoart].cls}`}>
                  {KONTOARTEN[k.kontoart].label}
                </span>
                <span className="text-xs text-slate-400 dark:text-slate-500">
                  {KONTOTYPEN[k.kontotyp]}
                </span>
                {!k.aktiv && (
                  <span className="text-xs bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400 px-2 py-0.5 rounded-full">
                    Inaktiv
                  </span>
                )}
              </div>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{k.anbieter}</p>
              {k.iban && (
                <p className="font-mono text-sm text-slate-700 dark:text-slate-300 mt-1">{formatIban(k.iban)}</p>
              )}
              {k.bic && <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">BIC: {k.bic}</p>}
              {k.kennung && (
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-1 font-mono">{k.kennung}</p>
              )}
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
          initialIban={modal === 'neu' ? initialIban : undefined}
          onClose={() => { setModal(null); setInitialIban(undefined) }}
        />
      )}

      {/* Löschen-Bestätigung */}
      {zuLoeschen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-sm bg-white dark:bg-slate-800 rounded-2xl shadow-2xl p-6">
            <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-2">Konto löschen?</h3>
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">
              <strong>{zuLoeschen.name}</strong> wird unwiderruflich gelöscht.
            </p>
            <p className="text-xs text-slate-400 dark:text-slate-500 mb-4">
              Konten mit verknüpften Transaktionen können nicht gelöscht werden – deaktiviere sie stattdessen.
            </p>
            {loeschFehler && <p className="text-sm text-red-600 dark:text-red-400 mb-3">{loeschFehler}</p>}
            <div className="flex justify-end gap-3">
              <button onClick={() => setZuLoeschen(null)} className="px-4 py-2 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors">
                Abbrechen
              </button>
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
