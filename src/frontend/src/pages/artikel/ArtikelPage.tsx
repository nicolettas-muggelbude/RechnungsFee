import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  getArtikel, createArtikel, updateArtikel, getArtikelRechnungen,
  getLieferanten, getUstSaetze, type Artikel, type ArtikelTyp,
} from '../../api/client'

// ---------------------------------------------------------------------------
// Typen-Config
// ---------------------------------------------------------------------------

const TYP_LABELS: Record<ArtikelTyp, string> = {
  artikel: 'Artikel',
  dienstleistung: 'Dienstleistung',
  fremdleistung: 'Fremdleistung',
}

const TYP_FARBEN: Record<ArtikelTyp, string> = {
  artikel: 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300',
  dienstleistung: 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
  fremdleistung: 'bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300',
}

function hatEK(typ: ArtikelTyp) { return typ === 'artikel' || typ === 'fremdleistung' }
function hatLieferant(typ: ArtikelTyp) { return typ === 'artikel' || typ === 'dienstleistung' || typ === 'fremdleistung' }
function hatHersteller(typ: ArtikelTyp) { return typ === 'artikel' }

// ---------------------------------------------------------------------------
// Einheit-Auswahl (Dropdown + Freitext-Fallback)
// ---------------------------------------------------------------------------

const EINHEITEN = ['Stück', 'Pack', 'Set', 'Lizenz', 'Stunde', 'Tag', 'Monat', 'Pauschal', 'km', 'm²']

function EinheitAuswahl({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const istBekannt = EINHEITEN.includes(value)
  const [freitext, setFreitext] = useState(!istBekannt)

  useEffect(() => {
    if (EINHEITEN.includes(value)) setFreitext(false)
  }, [value])

  if (freitext) {
    return (
      <div className="flex items-center gap-1 w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 border-0 outline-none bg-transparent text-slate-700 dark:text-slate-100 min-w-0"
          placeholder="Einheit eingeben"
        />
        <button
          type="button"
          title="Zur Liste zurück"
          onClick={() => { setFreitext(false); onChange('Stück') }}
          className="text-slate-300 hover:text-slate-500 dark:text-slate-500 dark:hover:text-slate-300 shrink-0 leading-none"
        >
          ↩
        </button>
      </div>
    )
  }

  return (
    <select
      value={value}
      onChange={(e) => {
        if (e.target.value === '__freitext__') { setFreitext(true); onChange('') }
        else onChange(e.target.value)
      }}
      className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
    >
      {EINHEITEN.map((e) => <option key={e} value={e}>{e}</option>)}
      <option value="__freitext__">Freitext…</option>
    </select>
  )
}


// ---------------------------------------------------------------------------
// Schema
// ---------------------------------------------------------------------------

const schema = z.object({
  typ: z.enum(['artikel', 'dienstleistung', 'fremdleistung']),
  bezeichnung: z.string().min(1, 'Bezeichnung erforderlich'),
  einheit: z.string().min(1, 'Einheit erforderlich'),
  steuersatz: z.string().min(1, 'Steuersatz erforderlich'),
  vk_brutto: z.string().refine(v => parseFloat(v) > 0, 'VK muss positiv sein'),
  ek_netto: z.string().optional(),
  lieferant_id: z.string().optional(),
  lieferanten_artikelnr: z.string().optional(),
  hersteller: z.string().optional(),
  artikelcode: z.string().optional(),
  beschreibung: z.string().optional(),
  kategorie: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

function formatEuro(v: string | null | undefined) {
  if (!v) return '–'
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(parseFloat(v))
}

// ---------------------------------------------------------------------------
// Formular
// ---------------------------------------------------------------------------

function ArtikelFormModal({
  initial, onClose, onSuccess, inline = false,
}: {
  initial?: Artikel
  onClose: () => void
  onSuccess: () => void
  inline?: boolean
}) {
  const qc = useQueryClient()
  const { data: lieferanten } = useQuery({ queryKey: ['lieferanten'], queryFn: getLieferanten })
  const { data: ustSaetze = [] } = useQuery({ queryKey: ['ust-saetze'], queryFn: getUstSaetze, staleTime: 1000 * 60 * 10 })
  const aktiveSaetze = ustSaetze.filter((s) => s.ist_aktiv)
  const defaultSatz = ustSaetze.find((s) => s.ist_default)?.satz
    ? String(parseFloat(ustSaetze.find((s) => s.ist_default)!.satz))
    : '19'

  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: initial ? {
      typ: initial.typ,
      bezeichnung: initial.bezeichnung,
      einheit: initial.einheit,
      steuersatz: String(parseFloat(String(initial.steuersatz))),
      vk_brutto: initial.vk_brutto,
      ek_netto: initial.ek_netto ?? '',
      lieferant_id: initial.lieferant_id ? String(initial.lieferant_id) : '',
      lieferanten_artikelnr: initial.lieferanten_artikelnr ?? '',
      hersteller: initial.hersteller ?? '',
      artikelcode: initial.artikelcode ?? '',
      beschreibung: initial.beschreibung ?? '',
      kategorie: initial.kategorie ?? '',
    } : {
      typ: 'artikel',
      steuersatz: defaultSatz,
      einheit: 'Stück',
    },
  })

  const typ = watch('typ') as ArtikelTyp

  const mutation = useMutation({
    mutationFn: (v: FormValues) => {
      const payload = {
        typ: v.typ,
        bezeichnung: v.bezeichnung,
        einheit: v.einheit,
        steuersatz: v.steuersatz,
        vk_brutto: v.vk_brutto,
        ek_netto: hatEK(v.typ) && v.ek_netto ? v.ek_netto : undefined,
        lieferant_id: hatLieferant(v.typ) && v.lieferant_id ? Number(v.lieferant_id) : undefined,
        lieferanten_artikelnr: hatLieferant(v.typ) ? v.lieferanten_artikelnr || undefined : undefined,
        hersteller: hatHersteller(v.typ) ? v.hersteller || undefined : undefined,
        artikelcode: hatHersteller(v.typ) ? v.artikelcode || undefined : undefined,
        beschreibung: v.beschreibung || undefined,
        kategorie: v.kategorie || undefined,
      }
      return initial ? updateArtikel(initial.id, payload) : createArtikel(payload)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['artikel'] })
      onSuccess()
    },
  })

  const formContent = (
    <form onSubmit={handleSubmit(v => mutation.mutate(v))} className="space-y-4">
          {/* Typ */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Typ</label>
            <div className="flex gap-2">
              {(['artikel', 'dienstleistung', 'fremdleistung'] as ArtikelTyp[]).map(t => (
                <label key={t} className="flex-1 cursor-pointer">
                  <input type="radio" value={t} {...register('typ')} className="sr-only" />
                  <div className={`text-center py-1.5 rounded-lg border-2 text-xs font-medium transition-colors ${
                    typ === t ? TYP_FARBEN[t] + ' border-current' : 'border-slate-200 dark:border-slate-600 text-slate-500 dark:text-slate-400'
                  }`}>
                    {TYP_LABELS[t]}
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Bezeichnung */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Bezeichnung *</label>
            <input {...register('bezeichnung')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-slate-100" />
            {errors.bezeichnung && <p className="text-red-600 dark:text-red-400 text-xs mt-1">{errors.bezeichnung.message}</p>}
          </div>

          {/* Einheit + Steuersatz */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Einheit *</label>
              <EinheitAuswahl value={watch('einheit') ?? ''} onChange={(v) => setValue('einheit', v, { shouldValidate: true })} />
              {errors.einheit && <p className="text-red-600 dark:text-red-400 text-xs mt-1">{errors.einheit.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Steuersatz *</label>
              <select {...register('steuersatz')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-slate-100">
                {aktiveSaetze.map((s) => {
                  const val = String(parseFloat(s.satz))
                  return (
                    <option key={s.id} value={val}>
                      {val} %{s.bezeichnung ? ` – ${s.bezeichnung}` : ''}
                    </option>
                  )
                })}
              </select>
            </div>
          </div>

          {/* VK */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">VK brutto *</label>
            <input {...register('vk_brutto')} type="number" step="0.01" min="0.01" placeholder="0,00" className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400" />
            {errors.vk_brutto && <p className="text-red-600 dark:text-red-400 text-xs mt-1">{errors.vk_brutto.message}</p>}
          </div>

          {/* EK (nur bei DL + Fremdleistung) */}
          {hatEK(typ) && (
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">EK netto</label>
              <input {...register('ek_netto')} type="number" step="0.01" min="0" placeholder="0,00" className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400" />
            </div>
          )}

          {/* Lieferant (nur bei DL + Fremdleistung) */}
          {hatLieferant(typ) && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
                  Lieferant{typ === 'fremdleistung' ? ' *' : ''}
                </label>
                <select {...register('lieferant_id')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-slate-100">
                  <option value="">– kein –</option>
                  {lieferanten?.map(l => (
                    <option key={l.id} value={l.id}>{l.firmenname}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Lieferanten-ArtNr</label>
                <input {...register('lieferanten_artikelnr')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-slate-100" />
              </div>
            </div>
          )}

          {/* Hersteller/Artikelcode (nur bei Dienstleistung) */}
          {hatHersteller(typ) && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Hersteller</label>
                <input {...register('hersteller')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-slate-100" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Artikelcode</label>
                <input {...register('artikelcode')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-slate-100" />
              </div>
            </div>
          )}

          {/* Kategorie */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Kategorie</label>
            <input {...register('kategorie')} placeholder="z.B. IT-Hardware, Marketing, Beratung …" className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400" />
          </div>

          {/* Beschreibung */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Beschreibung</label>
            <textarea {...register('beschreibung')} rows={3} placeholder="Ausführlicher Text für Rechnungsposition …" className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm resize-none dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400" />
          </div>

          {mutation.isError && (
            <p className="text-red-600 dark:text-red-400 text-sm">{(mutation.error as Error).message}</p>
          )}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-700">
              Abbrechen
            </button>
            <button type="submit" disabled={mutation.isPending} className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
              {mutation.isPending ? 'Speichert…' : initial ? 'Speichern' : 'Anlegen'}
            </button>
          </div>
        </form>
  )

  return inline ? formContent : (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6">
        <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-4">
          {initial ? 'Artikel bearbeiten' : 'Neuer Artikel'}
        </h2>
        {formContent}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Detail-Panel
// ---------------------------------------------------------------------------

function ArtikelDetail({ artikel, onEdit }: { artikel: Artikel; onEdit: () => void }) {
  const qc = useQueryClient()
  const { data: rechnungen } = useQuery({
    queryKey: ['artikel-rechnungen', artikel.id],
    queryFn: () => getArtikelRechnungen(artikel.id),
  })

  const toggleAktiv = useMutation({
    mutationFn: () => updateArtikel(artikel.id, { aktiv: !artikel.aktiv }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['artikel'] }),
  })

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${TYP_FARBEN[artikel.typ]}`}>
              {TYP_LABELS[artikel.typ]}
            </span>
            {!artikel.aktiv && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400">Inaktiv</span>
            )}
          </div>
          <h3 className="font-bold text-slate-800 dark:text-slate-100">{artikel.bezeichnung}</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">{artikel.artikelnummer}</p>
        </div>
        <button onClick={onEdit} className="text-sm text-blue-600 dark:text-blue-400 hover:underline">Bearbeiten</button>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2">
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">VK brutto</p>
          <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{formatEuro(artikel.vk_brutto)}</p>
        </div>
        <div className="bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2">
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">VK netto</p>
          <p className="text-sm text-slate-700 dark:text-slate-200">{formatEuro(artikel.vk_netto)}</p>
        </div>
        {artikel.ek_netto ? (
          <div className="bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2">
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">EK netto</p>
            <p className="text-sm text-slate-700 dark:text-slate-200">{formatEuro(artikel.ek_netto)}</p>
          </div>
        ) : <div />}
        <div className="bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2">
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">USt-Satz</p>
          <p className="text-sm text-slate-700 dark:text-slate-200">{artikel.steuersatz} %</p>
        </div>
        <div className="bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2">
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Einheit</p>
          <p className="text-sm text-slate-700 dark:text-slate-200">{artikel.einheit}</p>
        </div>
        {artikel.kategorie && (
          <div className="bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2">
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Kategorie</p>
            <p className="text-sm text-slate-700 dark:text-slate-200">{artikel.kategorie}</p>
          </div>
        )}
        {artikel.lieferant && (
          <div className="bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2">
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Lieferant</p>
            <p className="text-sm text-slate-700 dark:text-slate-200">{artikel.lieferant.firmenname}</p>
          </div>
        )}
        {artikel.lieferanten_artikelnr && (
          <div className="bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2">
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Lief.-ArtNr</p>
            <p className="text-sm text-slate-700 dark:text-slate-200 font-mono">{artikel.lieferanten_artikelnr}</p>
          </div>
        )}
        {artikel.hersteller && (
          <div className="bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2">
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Hersteller</p>
            <p className="text-sm text-slate-700 dark:text-slate-200">{artikel.hersteller}</p>
          </div>
        )}
        {artikel.artikelcode && (
          <div className="bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2">
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Artikelcode</p>
            <p className="text-sm text-slate-700 dark:text-slate-200 font-mono">{artikel.artikelcode}</p>
          </div>
        )}
      </div>

      {artikel.beschreibung && (
        <div className="text-sm text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900 rounded-lg p-3 mb-4 whitespace-pre-wrap">
          {artikel.beschreibung}
        </div>
      )}

      {/* Verknüpfte Rechnungen */}
      <div className="border-t border-slate-100 dark:border-slate-700 pt-3 flex-1 min-h-0">
        <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
          Verknüpfte Rechnungen ({rechnungen?.length ?? 0})
        </h4>
        {rechnungen && rechnungen.length > 0 ? (
          <div className="space-y-1 overflow-y-auto max-h-48">
            {rechnungen.map((r, i) => (
              <div key={i} className="text-xs bg-slate-50 dark:bg-slate-900 rounded px-2 py-1.5 flex items-start justify-between gap-2">
                <div>
                  <span className="font-medium text-slate-700 dark:text-slate-200">{r.rechnungsnummer ?? `RE-${r.rechnung_id}`}</span>
                  {r.kunde_name && <span className="text-slate-500 dark:text-slate-400 ms-2">{r.kunde_name}</span>}
                </div>
                <div className="text-slate-400 dark:text-slate-500 text-right shrink-0">
                  <div>{r.menge} {r.einheit}</div>
                  <div>{new Date(r.datum).toLocaleDateString('de-DE')}</div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-400 dark:text-slate-500">Noch in keiner Rechnung verwendet.</p>
        )}
      </div>

      <div className="border-t border-slate-100 dark:border-slate-700 pt-3 mt-3">
        <button
          onClick={() => toggleAktiv.mutate()}
          className={`text-xs ${artikel.aktiv ? 'text-slate-400 hover:text-red-500' : 'text-green-600 hover:text-green-700'}`}
        >
          {artikel.aktiv ? 'Als inaktiv markieren' : 'Wieder aktivieren'}
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Hauptseite
// ---------------------------------------------------------------------------

export function ArtikelPage() {
  const [suche, setSuche] = useState('')
  const [typFilter, setTypFilter] = useState<ArtikelTyp | ''>('')
  const [aktiv, setAktiv] = useState<boolean | undefined>(true)
  const [selected, setSelected] = useState<Artikel | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editArtikel, setEditArtikel] = useState<Artikel | undefined>()

  const { data: artikel, isLoading } = useQuery({
    queryKey: ['artikel', aktiv, typFilter],
    queryFn: () => getArtikel({ aktiv, typ: typFilter || undefined }),
  })

  const gefiltert = (artikel ?? []).filter(a => {
    if (!suche) return true
    const s = suche.toLowerCase()
    return (
      a.bezeichnung.toLowerCase().includes(s) ||
      a.artikelnummer.toLowerCase().includes(s) ||
      (a.lieferant?.firmenname.toLowerCase().includes(s) ?? false)
    )
  })

  function openEdit(a: Artikel) {
    setEditArtikel(a)
    setShowForm(true)
  }

  function closeForm() {
    setShowForm(false)
    setEditArtikel(undefined)
  }

  return (
    <div className="flex h-full gap-0">
      {/* Liste */}
      <div className={`${showForm ? 'w-1/4 min-w-[200px] shrink-0' : 'w-full max-w-xl'} flex flex-col border-e border-slate-200 dark:border-slate-700 transition-all`}>
        {/* Header */}
        <div className="p-4 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between mb-3">
            <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Artikelstamm</h1>
            <button
              onClick={() => { setEditArtikel(undefined); setShowForm(true) }}
              className="bg-blue-600 text-white text-sm px-3 py-1.5 rounded-lg hover:bg-blue-700"
            >
              + Neu
            </button>
          </div>
          <input
            value={suche}
            onChange={e => setSuche(e.target.value)}
            placeholder="Suche nach Bezeichnung, Artikelnummer, Lieferant …"
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm mb-2 dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400"
          />
          <div className="flex gap-2 flex-wrap">
            {/* Typ-Filter */}
            {(['', 'artikel', 'dienstleistung', 'fremdleistung'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTypFilter(t)}
                className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                  typFilter === t
                    ? 'bg-slate-700 dark:bg-slate-500 text-white border-slate-700 dark:border-slate-500'
                    : 'border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:border-slate-400 dark:hover:border-slate-500'
                }`}
              >
                {t === '' ? 'Alle Typen' : TYP_LABELS[t]}
              </button>
            ))}
            <button
              onClick={() => setAktiv(aktiv === true ? undefined : true)}
              className={`text-xs px-2.5 py-1 rounded-full border transition-colors ms-auto ${
                aktiv === true
                  ? 'bg-green-100 dark:bg-green-950 text-green-700 dark:text-green-300 border-green-300 dark:border-green-700'
                  : 'border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300'
              }`}
            >
              {aktiv === true ? 'Nur aktive' : 'Alle'}
            </button>
          </div>
        </div>

        {/* Liste */}
        <div className="flex-1 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-700">
          {isLoading ? (
            <div className="p-8 text-center text-slate-400 dark:text-slate-500 text-sm">Lädt…</div>
          ) : gefiltert.length === 0 ? (
            <div className="p-8 text-center text-slate-400 dark:text-slate-500 text-sm">Keine Artikel gefunden.</div>
          ) : (
            gefiltert.map(a => (
              <button
                key={a.id}
                onClick={() => setSelected(a)}
                className={`w-full text-start px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors ${
                  selected?.id === a.id ? 'bg-blue-50 dark:bg-blue-950/30 border-e-2 border-blue-500' : ''
                }`}
              >
                <div className="flex items-center justify-between mb-0.5">
                  <span className="font-medium text-sm text-slate-800 dark:text-slate-100">{a.bezeichnung}</span>
                  <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">{formatEuro(a.vk_brutto)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400 dark:text-slate-500">{a.artikelnummer}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded-full ${TYP_FARBEN[a.typ]}`}>
                    {TYP_LABELS[a.typ]}
                  </span>
                  {!a.aktiv && <span className="text-xs text-slate-400 dark:text-slate-500 italic">inaktiv</span>}
                  {a.lieferant && <span className="text-xs text-slate-400 dark:text-slate-500">· {a.lieferant.firmenname}</span>}
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Detail-Panel */}
      {!showForm && (
        <div className="flex-1 p-6 overflow-y-auto">
          {selected ? (
            <ArtikelDetail
              key={selected.id}
              artikel={selected}
              onEdit={() => openEdit(selected)}
            />
          ) : (
            <div className="h-full flex items-center justify-center text-slate-400 dark:text-slate-500 text-sm">
              Artikel auswählen
            </div>
          )}
        </div>
      )}

      {/* Formular-Panel */}
      {showForm && (
        <div className="flex-1 border-l border-slate-200 dark:border-slate-700 overflow-y-auto">
          <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between shrink-0">
            <h3 className="font-semibold text-slate-800 dark:text-slate-100">
              {editArtikel ? 'Artikel bearbeiten' : 'Neuer Artikel'}
            </h3>
            <button onClick={closeForm} className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-xl leading-none">×</button>
          </div>
          <div className="p-6">
            <ArtikelFormModal
              initial={editArtikel}
              onClose={closeForm}
              onSuccess={() => {
                closeForm()
                if (editArtikel) setSelected(prev => prev?.id === editArtikel.id ? null : prev)
              }}
              inline
            />
          </div>
        </div>
      )}
    </div>
  )
}
