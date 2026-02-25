import { useState, useEffect } from 'react'
import { useForm, useFieldArray, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createKassenbuchEintrag,
  createSplitBuchung,
  getKategorien,
  getKunden,
  getUnternehmen,
} from '../../api/client'

// ---------------------------------------------------------------------------
// Schemas
// ---------------------------------------------------------------------------

const singleSchema = z.object({
  datum: z.string().min(1, 'Datum erforderlich'),
  beschreibung: z.string().min(1, 'Beschreibung erforderlich'),
  art: z.enum(['Einnahme', 'Ausgabe']),
  brutto_betrag: z
    .string()
    .refine((v) => !isNaN(parseFloat(v)) && parseFloat(v) > 0, 'Betrag muss positiv sein'),
  ust_satz: z.string(),
  zahlungsart: z.enum(['Bar', 'Karte', 'Bank', 'PayPal']),
  kategorie_id: z.string().optional(),
  kunde_id: z.string().optional(),
  vorsteuerabzug: z.boolean().optional(),
  externe_belegnr: z.string().optional(),
})

const positionSchema = z.object({
  beschreibung: z.string().min(1, 'Beschreibung erforderlich'),
  kategorie_id: z.string().optional(),
  brutto_betrag: z
    .string()
    .refine((v) => !isNaN(parseFloat(v)) && parseFloat(v) > 0, 'Betrag muss positiv sein'),
  ust_satz: z.string(),
  vorsteuerabzug: z.boolean(),
})

const splitSchema = z.object({
  datum: z.string().min(1, 'Datum erforderlich'),
  art: z.enum(['Einnahme', 'Ausgabe']),
  zahlungsart: z.enum(['Bar', 'Karte', 'Bank', 'PayPal']),
  externe_belegnr: z.string().optional(),
  kunde_id: z.string().optional(),
  positionen: z.array(positionSchema).min(2, 'Mindestens 2 Positionen erforderlich'),
})

type SingleValues = z.infer<typeof singleSchema>
type SplitValues = z.infer<typeof splitSchema>

interface Props {
  onClose: () => void
  onSuccess: () => void
}

function heute(): string {
  return new Date().toISOString().slice(0, 10)
}

function formatEuro(n: number): string {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n)
}

// ---------------------------------------------------------------------------
// Komponente
// ---------------------------------------------------------------------------

export function BuchungForm({ onClose, onSuccess }: Props) {
  const qc = useQueryClient()
  const [isSplit, setIsSplit] = useState(false)
  const [eingabeModus, setEingabeModus] = useState<'brutto' | 'netto'>('brutto')

  const { data: kategorien } = useQuery({ queryKey: ['kategorien'], queryFn: getKategorien })
  const { data: kunden } = useQuery({ queryKey: ['kunden'], queryFn: getKunden })
  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen })

  const istKleinunternehmer = unternehmen?.ist_kleinunternehmer ?? false

  // --- Einfache Buchung ---
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<SingleValues>({
    resolver: zodResolver(singleSchema),
    defaultValues: {
      datum: heute(),
      art: 'Einnahme',
      zahlungsart: 'Bar',
      ust_satz: '0',
      vorsteuerabzug: true,
    },
  })

  // --- Split-Buchung ---
  const {
    register: registerS,
    handleSubmit: handleSubmitS,
    watch: watchS,
    setValue: setValueS,
    control: controlS,
    formState: { errors: errorsS },
  } = useForm<SplitValues>({
    resolver: zodResolver(splitSchema),
    defaultValues: {
      datum: heute(),
      art: 'Ausgabe',
      zahlungsart: 'Bar',
      positionen: [
        { beschreibung: '', kategorie_id: '', brutto_betrag: '', ust_satz: '19', vorsteuerabzug: true },
        { beschreibung: '', kategorie_id: '', brutto_betrag: '', ust_satz: '19', vorsteuerabzug: true },
      ],
    },
  })

  const { fields, append, remove } = useFieldArray({ control: controlS, name: 'positionen' })

  // Gemeinsame Beobachter
  const art = watch('art')
  const bruttoStr = watch('brutto_betrag')
  const ustSatzStr = watch('ust_satz')
  const kategorie_id = watch('kategorie_id')
  const artSplit = watchS('art')
  const positionenSplit = watchS('positionen')

  // Beim Umschalten: gemeinsame Felder synchronisieren
  function toggleSplit(ein: boolean) {
    if (ein) {
      setValueS('datum', watch('datum'))
      setValueS('art', watch('art') as 'Einnahme' | 'Ausgabe')
      setValueS('zahlungsart', watch('zahlungsart'))
      setValueS('externe_belegnr', watch('externe_belegnr') ?? '')
    } else {
      setValue('datum', watchS('datum'))
      setValue('art', watchS('art'))
      setValue('zahlungsart', watchS('zahlungsart'))
      setValue('externe_belegnr', watchS('externe_belegnr') ?? '')
    }
    setIsSplit(ein)
  }

  // Standardkategorie vorwählen (einfache Buchung)
  useEffect(() => {
    if (!kategorien || isSplit) return
    if (art === 'Einnahme') {
      const defaultName = istKleinunternehmer ? 'Kleinunternehmer-Einnahmen' : 'Betriebseinnahmen'
      const kat = kategorien.find((k) => k.name === defaultName)
      if (kat) setValue('kategorie_id', String(kat.id))
    } else {
      setValue('kategorie_id', '')
    }
  }, [kategorien, art, istKleinunternehmer, isSplit, setValue])

  // USt + Vorsteuer aus Kategorie (einfache Buchung)
  useEffect(() => {
    if (!kategorie_id || !kategorien || isSplit) return
    const kat = kategorien.find((k) => String(k.id) === kategorie_id)
    if (!kat) return
    // Privat-Buchung: immer USt=0, kein Vorsteuerabzug
    if (kat.kontenart === 'Privat') {
      setValue('ust_satz', '0')
      setValue('vorsteuerabzug', false)
      return
    }
    setValue('ust_satz', istKleinunternehmer ? '0' : String(kat.ust_satz_standard))
    if (!istKleinunternehmer) {
      setValue('vorsteuerabzug', parseFloat(kat.vorsteuer_prozent) > 0)
    }
  }, [kategorie_id, kategorien, isSplit, setValue, istKleinunternehmer])

  const gewaehlteKat = (kategorien ?? []).find((k) => String(k.id) === kategorie_id)
  const istPrivatKategorie = gewaehlteKat?.kontenart === 'Privat'

  // USt-Vorschau (einfache Buchung) – je nach Eingabemodus
  const eingabeWert = parseFloat(bruttoStr) || 0
  const ustSatz = parseFloat(ustSatzStr) || 0
  let brutto: number, netto: number, ustBetrag: number
  if (eingabeModus === 'netto') {
    netto = eingabeWert
    ustBetrag = ustSatz > 0 ? netto * ustSatz / 100 : 0
    brutto = netto + ustBetrag
  } else {
    brutto = eingabeWert
    netto = ustSatz > 0 ? (brutto * 100) / (100 + ustSatz) : brutto
    ustBetrag = brutto - netto
  }

  // Umschalten Brutto/Netto mit automatischer Wertkonvertierung
  function toggleEingabeModus() {
    const ust = parseFloat(watch('ust_satz')) || 0
    const val = parseFloat(watch('brutto_betrag')) || 0
    if (eingabeModus === 'brutto') {
      if (val > 0 && ust > 0) setValue('brutto_betrag', ((val * 100) / (100 + ust)).toFixed(2))
      setEingabeModus('netto')
    } else {
      if (val > 0 && ust > 0) setValue('brutto_betrag', (val * (1 + ust / 100)).toFixed(2))
      setEingabeModus('brutto')
    }
  }

  // Gesamtsumme Split (immer als Brutto)
  const gesamtBrutto = positionenSplit.reduce((sum, p) => {
    const val = parseFloat(p.brutto_betrag) || 0
    if (val === 0) return sum
    if (eingabeModus === 'netto') {
      const u = parseFloat(p.ust_satz) || 0
      return sum + val * (1 + u / 100)
    }
    return sum + val
  }, 0)

  // Kategorie-Gruppen
  const alle = kategorien ?? []
  const erloeseKat = alle.filter(
    (k) =>
      k.kontenart === 'Erlös' &&
      (istKleinunternehmer
        ? k.name === 'Kleinunternehmer-Einnahmen'
        : k.name !== 'Kleinunternehmer-Einnahmen')
  )
  const einlageKat = alle.filter((k) => k.kontenart === 'Privat' && k.name === 'Privateinlage')
  const aufwandKat = alle.filter((k) => k.kontenart === 'Aufwand')
  const anlageKat = alle.filter((k) => k.kontenart === 'Anlage')
  const entnahmeKat = alle.filter((k) => k.kontenart === 'Privat' && k.name === 'Privatentnahme')

  function renderKategorieOptgroups(artWert: string) {
    return artWert === 'Einnahme' ? (
      <>
        <optgroup label="Erlöse">
          {erloeseKat.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
        </optgroup>
        {einlageKat.length > 0 && (
          <optgroup label="Sonstiges">
            {einlageKat.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
          </optgroup>
        )}
      </>
    ) : (
      <>
        <optgroup label="Betriebsausgaben">
          {aufwandKat.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
        </optgroup>
        {anlageKat.length > 0 && (
          <optgroup label="Investitionen">
            {anlageKat.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
          </optgroup>
        )}
        {entnahmeKat.length > 0 && (
          <optgroup label="Sonstiges">
            {entnahmeKat.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
          </optgroup>
        )}
      </>
    )
  }

  function handleSplitKategorieChange(index: number, katId: string) {
    setValueS(`positionen.${index}.kategorie_id`, katId)
    if (!katId || istKleinunternehmer) return
    const kat = alle.find((k) => String(k.id) === katId)
    if (!kat) return
    setValueS(`positionen.${index}.ust_satz`, String(kat.ust_satz_standard))
    setValueS(`positionen.${index}.vorsteuerabzug`, parseFloat(kat.vorsteuer_prozent) > 0)
  }

  // Mutations
  const singleMutation = useMutation({
    mutationFn: createKassenbuchEintrag,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kassenbuch'] })
      qc.invalidateQueries({ queryKey: ['monats-uebersicht'] })
      onSuccess()
    },
  })

  const splitMutation = useMutation({
    mutationFn: createSplitBuchung,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kassenbuch'] })
      qc.invalidateQueries({ queryKey: ['monats-uebersicht'] })
      onSuccess()
    },
  })

  function nettoToBrutto(nettoStr: string, ustSatzStr: string): string {
    const n = parseFloat(nettoStr)
    const u = parseFloat(ustSatzStr) || 0
    if (isNaN(n)) return nettoStr
    return (n * (1 + u / 100)).toFixed(2)
  }

  function onSubmitSingle(values: SingleValues) {
    const bruttoFinal =
      eingabeModus === 'netto'
        ? nettoToBrutto(values.brutto_betrag, values.ust_satz)
        : values.brutto_betrag
    singleMutation.mutate({
      datum: values.datum,
      beschreibung: values.beschreibung,
      art: values.art,
      brutto_betrag: bruttoFinal,
      ust_satz: values.ust_satz,
      zahlungsart: values.zahlungsart,
      kategorie_id: values.kategorie_id ? Number(values.kategorie_id) : undefined,
      kunde_id: values.kunde_id ? Number(values.kunde_id) : undefined,
      vorsteuerabzug: values.vorsteuerabzug,
      externe_belegnr: values.externe_belegnr || undefined,
    })
  }

  function onSubmitSplit(values: SplitValues) {
    splitMutation.mutate({
      datum: values.datum,
      art: values.art,
      zahlungsart: values.zahlungsart,
      externe_belegnr: values.externe_belegnr || undefined,
      kunde_id: values.kunde_id ? Number(values.kunde_id) : undefined,
      positionen: values.positionen.map((p) => {
        const ustFinal = istKleinunternehmer ? '0' : p.ust_satz
        const bruttoFinal =
          eingabeModus === 'netto' ? nettoToBrutto(p.brutto_betrag, ustFinal) : p.brutto_betrag
        return {
          beschreibung: p.beschreibung,
          kategorie_id: p.kategorie_id ? Number(p.kategorie_id) : undefined,
          brutto_betrag: bruttoFinal,
          ust_satz: ustFinal,
          vorsteuerabzug: p.vorsteuerabzug,
        }
      }),
    })
  }

  const isPending = singleMutation.isPending || splitMutation.isPending

  // ---------------------------------------------------------------------------
  // Render: geteilter Inhalt je nach Modus
  // ---------------------------------------------------------------------------

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-slate-800">Neue Buchung</h2>
          {isSplit && (
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium">
              Split-Modus
            </span>
          )}
        </div>

        {istKleinunternehmer && (
          <div className="mb-4 flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs text-amber-800">
            <span className="mt-0.5">ℹ️</span>
            <span>
              <strong>Kleinunternehmer §19 UStG</strong> – Keine Umsatzsteuer ausgewiesen. USt-Satz
              ist gesperrt.
            </span>
          </div>
        )}

        {/* ================================================================
            EINFACHE BUCHUNG
        ================================================================ */}
        {!isSplit && (
          <form onSubmit={handleSubmit(onSubmitSingle)} className="space-y-4">
            {/* Art */}
            <div className="flex gap-3">
              {(['Einnahme', 'Ausgabe'] as const).map((a) => (
                <label key={a} className="flex-1 cursor-pointer">
                  <input type="radio" value={a} {...register('art')} className="sr-only" />
                  <div
                    className={`text-center py-2 rounded-lg border-2 font-medium text-sm transition-colors ${
                      art === a
                        ? a === 'Einnahme'
                          ? 'border-green-500 bg-green-50 text-green-700'
                          : 'border-red-500 bg-red-50 text-red-700'
                        : 'border-slate-200 text-slate-500 hover:border-slate-300'
                    }`}
                  >
                    {a}
                  </div>
                </label>
              ))}
            </div>

            {/* Split-Option für Ausgaben */}
            {art === 'Ausgabe' && (
              <button
                type="button"
                onClick={() => toggleSplit(true)}
                className="w-full flex items-center justify-between border border-dashed border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-500 hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
              >
                <span>Mehrere Positionen auf unterschiedliche Kategorien?</span>
                <span className="font-medium">Split-Buchung →</span>
              </button>
            )}

            {/* Datum + Zahlungsart */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Datum</label>
                <input
                  type="date"
                  {...register('datum')}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {errors.datum && (
                  <p className="text-red-500 text-xs mt-0.5">{errors.datum.message}</p>
                )}
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Zahlungsart</label>
                <select
                  {...register('zahlungsart')}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {['Bar', 'Karte', 'Bank', 'PayPal'].map((z) => <option key={z}>{z}</option>)}
                </select>
              </div>
            </div>

            {/* Beschreibung */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Beschreibung</label>
              <input
                type="text"
                {...register('beschreibung')}
                placeholder="z.B. Büromaterial"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {errors.beschreibung && (
                <p className="text-red-500 text-xs mt-0.5">{errors.beschreibung.message}</p>
              )}
            </div>

            {/* Externe Belegnr. */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Externe Belegnr. <span className="text-slate-400 font-normal">(optional)</span>
              </label>
              <input
                type="text"
                {...register('externe_belegnr')}
                placeholder="z.B. RE-2024-00123"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Kategorie */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Kategorie</label>
              <select
                {...register('kategorie_id')}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">— keine —</option>
                {renderKategorieOptgroups(art)}
              </select>
            </div>

            {/* Privat-Hinweis */}
            {istPrivatKategorie && (
              <div className="flex items-start gap-2 bg-purple-50 border border-purple-200 rounded-lg px-3 py-2 text-xs text-purple-800">
                <span className="mt-0.5 shrink-0">🏠</span>
                <span>
                  <strong>Privatbuchung</strong> – kein Betriebsvorgang. Wird nicht in der
                  Betriebseinnahmen/-ausgaben-Auswertung berücksichtigt. USt ist
                  automatisch 0 %.
                </span>
              </div>
            )}

            {/* Kunde (nur Einnahmen) */}
            {art === 'Einnahme' && (
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">
                  Kunde <span className="text-slate-400 font-normal">(optional)</span>
                </label>
                <select
                  {...register('kunde_id')}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">— kein Kunde —</option>
                  {(kunden ?? [])
                    .filter((k) => k.aktiv !== false)
                    .map((k) => {
                      const name = [k.firmenname, k.vorname, k.nachname].filter(Boolean).join(' ')
                      return (
                        <option key={k.id} value={k.id}>
                          {name}
                          {k.kundennummer ? ` (${k.kundennummer})` : ''}
                        </option>
                      )
                    })}
                </select>
              </div>
            )}

            {/* Betrag + USt */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-600">
                    {eingabeModus === 'brutto' ? 'Brutto-Betrag (€)' : 'Netto-Betrag (€)'}
                  </label>
                  {!istKleinunternehmer && (
                    <button
                      type="button"
                      onClick={toggleEingabeModus}
                      className="text-xs text-blue-600 hover:text-blue-700 underline"
                    >
                      {eingabeModus === 'brutto' ? 'Netto eingeben' : 'Brutto eingeben'}
                    </button>
                  )}
                </div>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  {...register('brutto_betrag')}
                  placeholder="0,00"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {errors.brutto_betrag && (
                  <p className="text-red-500 text-xs mt-0.5">{errors.brutto_betrag.message}</p>
                )}
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">
                  USt-Satz (%)
                  {!istKleinunternehmer && unternehmen?.taetigkeitsart === 'freiberuflich' && (
                    <span className="ml-1 text-slate-400 font-normal">
                      (7 % für Autoren/Heilberufe etc.)
                    </span>
                  )}
                </label>
                <select
                  {...register('ust_satz')}
                  disabled={istKleinunternehmer || istPrivatKategorie}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100 disabled:text-slate-400 disabled:cursor-not-allowed"
                >
                  <option value="0">
                    {istKleinunternehmer ? '0 % (§19 UStG)' : istPrivatKategorie ? '0 % (Privat)' : '0 %'}
                  </option>
                  {!istKleinunternehmer && !istPrivatKategorie && <option value="7">7 %</option>}
                  {!istKleinunternehmer && !istPrivatKategorie && <option value="19">19 %</option>}
                </select>
              </div>
            </div>

            {/* USt-Vorschau */}
            {ustSatz > 0 && eingabeWert > 0 && (
              <div className="bg-slate-50 rounded-lg p-3 text-xs text-slate-600 grid grid-cols-3 gap-2">
                <div>
                  <span className="block text-slate-400">Netto</span>
                  {netto.toFixed(2)} €
                </div>
                <div>
                  <span className="block text-slate-400">USt {ustSatz} %</span>
                  {ustBetrag.toFixed(2)} €
                </div>
                <div>
                  <span className={`block ${eingabeModus === 'netto' ? 'text-blue-500 font-medium' : 'text-slate-400'}`}>
                    Brutto {eingabeModus === 'netto' ? '(berechnet)' : ''}
                  </span>
                  {brutto.toFixed(2)} €
                </div>
              </div>
            )}

            {/* Vorsteuerabzug */}
            {art === 'Ausgabe' && !istKleinunternehmer && !istPrivatKategorie && (
              <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                <input type="checkbox" {...register('vorsteuerabzug')} className="rounded" />
                Vorsteuerabzug geltend machen
              </label>
            )}

            {singleMutation.isError && (
              <p className="text-red-600 text-sm">{(singleMutation.error as Error).message}</p>
            )}

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 border border-slate-300 text-slate-600 rounded-lg py-2 text-sm hover:bg-slate-50"
              >
                Abbrechen
              </button>
              <button
                type="submit"
                disabled={isPending}
                className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {isPending ? 'Speichert…' : 'Buchung speichern'}
              </button>
            </div>
          </form>
        )}

        {/* ================================================================
            SPLIT-BUCHUNG
        ================================================================ */}
        {isSplit && (
          <form onSubmit={handleSubmitS(onSubmitSplit)} className="space-y-4">
            {/* Art */}
            <div className="flex gap-3">
              {(['Einnahme', 'Ausgabe'] as const).map((a) => (
                <label key={a} className="flex-1 cursor-pointer">
                  <input type="radio" value={a} {...registerS('art')} className="sr-only" />
                  <div
                    className={`text-center py-2 rounded-lg border-2 font-medium text-sm transition-colors ${
                      artSplit === a
                        ? a === 'Einnahme'
                          ? 'border-green-500 bg-green-50 text-green-700'
                          : 'border-red-500 bg-red-50 text-red-700'
                        : 'border-slate-200 text-slate-500 hover:border-slate-300'
                    }`}
                  >
                    {a}
                  </div>
                </label>
              ))}
            </div>

            {/* Zurück zu einfacher Buchung */}
            <button
              type="button"
              onClick={() => toggleSplit(false)}
              className="w-full flex items-center justify-between border border-dashed border-blue-200 rounded-lg px-3 py-2 text-sm text-blue-500 hover:border-blue-400 hover:bg-blue-50 transition-colors"
            >
              <span>← Zurück zur einfachen Buchung</span>
              <span className="text-xs text-slate-400">eine Position, eine Kategorie</span>
            </button>

            {/* Datum + Zahlungsart */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Datum</label>
                <input
                  type="date"
                  {...registerS('datum')}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {errorsS.datum && (
                  <p className="text-red-500 text-xs mt-0.5">{errorsS.datum.message}</p>
                )}
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Zahlungsart</label>
                <select
                  {...registerS('zahlungsart')}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {['Bar', 'Karte', 'Bank', 'PayPal'].map((z) => <option key={z}>{z}</option>)}
                </select>
              </div>
            </div>

            {/* Externe Belegnr. */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Externe Belegnr. <span className="text-slate-400 font-normal">(optional)</span>
              </label>
              <input
                type="text"
                {...registerS('externe_belegnr')}
                placeholder="z.B. Kassenbon-Nr."
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Kunde (nur Einnahmen) */}
            {artSplit === 'Einnahme' && (
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">
                  Kunde <span className="text-slate-400 font-normal">(optional)</span>
                </label>
                <select
                  {...registerS('kunde_id')}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">— kein Kunde —</option>
                  {(kunden ?? [])
                    .filter((k) => k.aktiv !== false)
                    .map((k) => {
                      const name = [k.firmenname, k.vorname, k.nachname].filter(Boolean).join(' ')
                      return (
                        <option key={k.id} value={k.id}>
                          {name}
                          {k.kundennummer ? ` (${k.kundennummer})` : ''}
                        </option>
                      )
                    })}
                </select>
              </div>
            )}

            {/* Eingabemodus-Umschalter für Split */}
            {!istKleinunternehmer && (
              <div className="flex items-center justify-between bg-slate-50 rounded-lg px-3 py-2 text-sm">
                <span className="text-slate-600">
                  Beträge eingeben als:{' '}
                  <strong>{eingabeModus === 'brutto' ? 'Brutto' : 'Netto'}</strong>
                </span>
                <button
                  type="button"
                  onClick={toggleEingabeModus}
                  className="text-xs text-blue-600 hover:text-blue-700 underline"
                >
                  {eingabeModus === 'brutto' ? 'Netto eingeben' : 'Brutto eingeben'}
                </button>
              </div>
            )}

            {/* Positionen */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  Positionen
                </label>
                <button
                  type="button"
                  onClick={() =>
                    append({
                      beschreibung: '',
                      kategorie_id: '',
                      brutto_betrag: '',
                      ust_satz: istKleinunternehmer ? '0' : '19',
                      vorsteuerabzug: true,
                    })
                  }
                  className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                >
                  + Position hinzufügen
                </button>
              </div>

              <div className="space-y-3">
                {fields.map((field, i) => {
                  const inputVal = parseFloat(positionenSplit[i]?.brutto_betrag) || 0
                  const u = parseFloat(positionenSplit[i]?.ust_satz) || 0
                  let b: number, posNetto: number, posUst: number
                  if (eingabeModus === 'netto') {
                    posNetto = inputVal
                    posUst = u > 0 ? posNetto * u / 100 : 0
                    b = posNetto + posUst
                  } else {
                    b = inputVal
                    posNetto = u > 0 ? (b * 100) / (100 + u) : b
                    posUst = b - posNetto
                  }

                  return (
                    <div
                      key={field.id}
                      className="border border-slate-200 rounded-lg p-3 space-y-2 bg-slate-50"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-500">
                          Position {i + 1}
                        </span>
                        {fields.length > 2 && (
                          <button
                            type="button"
                            onClick={() => remove(i)}
                            className="text-xs text-red-400 hover:text-red-600"
                          >
                            Entfernen
                          </button>
                        )}
                      </div>

                      <input
                        type="text"
                        {...registerS(`positionen.${i}.beschreibung`)}
                        placeholder="Beschreibung *"
                        className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                      {errorsS.positionen?.[i]?.beschreibung && (
                        <p className="text-red-500 text-xs">
                          {errorsS.positionen[i]?.beschreibung?.message}
                        </p>
                      )}

                      <div className="grid grid-cols-2 gap-2">
                        {/* Kategorie */}
                        <Controller
                          control={controlS}
                          name={`positionen.${i}.kategorie_id`}
                          render={({ field: f }) => (
                            <select
                              value={f.value}
                              onChange={(e) => handleSplitKategorieChange(i, e.target.value)}
                              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                              <option value="">— Kategorie —</option>
                              {renderKategorieOptgroups(artSplit)}
                            </select>
                          )}
                        />

                        {/* Brutto */}
                        <div>
                          <input
                            type="number"
                            step="0.01"
                            min="0.01"
                            {...registerS(`positionen.${i}.brutto_betrag`)}
                            placeholder={eingabeModus === 'brutto' ? 'Brutto (€)' : 'Netto (€)'}
                            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                          {errorsS.positionen?.[i]?.brutto_betrag && (
                            <p className="text-red-500 text-xs mt-0.5">
                              {errorsS.positionen[i]?.brutto_betrag?.message}
                            </p>
                          )}
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-2 items-center">
                        <select
                          {...registerS(`positionen.${i}.ust_satz`)}
                          disabled={istKleinunternehmer}
                          className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100 disabled:text-slate-400 disabled:cursor-not-allowed"
                        >
                          <option value="0">
                            {istKleinunternehmer ? '0 % (§19 UStG)' : '0 %'}
                          </option>
                          {!istKleinunternehmer && <option value="7">7 %</option>}
                          {!istKleinunternehmer && <option value="19">19 %</option>}
                        </select>

                        {artSplit === 'Ausgabe' && !istKleinunternehmer ? (
                          <label className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer">
                            <input
                              type="checkbox"
                              {...registerS(`positionen.${i}.vorsteuerabzug`)}
                              className="rounded"
                            />
                            Vorsteuerabzug
                          </label>
                        ) : (
                          <div />
                        )}
                      </div>

                      {u > 0 && inputVal > 0 && (
                        <div className="bg-white rounded p-2 text-xs text-slate-500 grid grid-cols-3 gap-1">
                          <div>
                            <span className="block text-slate-400">Netto</span>
                            {posNetto.toFixed(2)} €
                          </div>
                          <div>
                            <span className="block text-slate-400">USt {u} %</span>
                            {posUst.toFixed(2)} €
                          </div>
                          <div>
                            <span className={`block ${eingabeModus === 'netto' ? 'text-blue-500 font-medium' : 'text-slate-400'}`}>
                              Brutto {eingabeModus === 'netto' ? '→' : ''}
                            </span>
                            {b.toFixed(2)} €
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>

              {gesamtBrutto > 0 && (
                <div className="mt-3 flex justify-between items-center bg-slate-100 rounded-lg px-4 py-2 text-sm font-semibold text-slate-700">
                  <span>Gesamt-Brutto</span>
                  <span>{formatEuro(gesamtBrutto)}</span>
                </div>
              )}
            </div>

            {splitMutation.isError && (
              <p className="text-red-600 text-sm">{(splitMutation.error as Error).message}</p>
            )}

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 border border-slate-300 text-slate-600 rounded-lg py-2 text-sm hover:bg-slate-50"
              >
                Abbrechen
              </button>
              <button
                type="submit"
                disabled={isPending}
                className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {isPending ? 'Speichert…' : `${fields.length} Positionen speichern`}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
