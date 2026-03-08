import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  getArtikel, createArtikel, updateArtikel, getArtikelRechnungen,
  getLieferanten, type Artikel, type ArtikelTyp,
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
  artikel: 'bg-green-100 text-green-700',
  dienstleistung: 'bg-blue-100 text-blue-700',
  fremdleistung: 'bg-purple-100 text-purple-700',
}

function hatEK(typ: ArtikelTyp) { return typ === 'artikel' || typ === 'fremdleistung' }
function hatLieferant(typ: ArtikelTyp) { return typ === 'artikel' || typ === 'dienstleistung' || typ === 'fremdleistung' }
function hatHersteller(typ: ArtikelTyp) { return typ === 'artikel' }

// ---------------------------------------------------------------------------
// Schema
// ---------------------------------------------------------------------------

const schema = z.object({
  typ: z.enum(['artikel', 'dienstleistung', 'fremdleistung']),
  bezeichnung: z.string().min(1, 'Bezeichnung erforderlich'),
  einheit: z.string().min(1, 'Einheit erforderlich'),
  steuersatz: z.enum(['0', '7', '19']),
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
  initial, onClose, onSuccess,
}: {
  initial?: Artikel
  onClose: () => void
  onSuccess: () => void
}) {
  const qc = useQueryClient()
  const { data: lieferanten } = useQuery({ queryKey: ['lieferanten'], queryFn: getLieferanten })

  const { register, handleSubmit, watch, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: initial ? {
      typ: initial.typ,
      bezeichnung: initial.bezeichnung,
      einheit: initial.einheit,
      steuersatz: String(initial.steuersatz) as '0' | '7' | '19',
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
      steuersatz: '19',
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

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6">
        <h2 className="text-lg font-bold text-slate-800 mb-4">
          {initial ? 'Artikel bearbeiten' : 'Neuer Artikel'}
        </h2>

        <form onSubmit={handleSubmit(v => mutation.mutate(v))} className="space-y-4">
          {/* Typ */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Typ</label>
            <div className="flex gap-2">
              {(['artikel', 'dienstleistung', 'fremdleistung'] as ArtikelTyp[]).map(t => (
                <label key={t} className="flex-1 cursor-pointer">
                  <input type="radio" value={t} {...register('typ')} className="sr-only" />
                  <div className={`text-center py-1.5 rounded-lg border-2 text-xs font-medium transition-colors ${
                    typ === t ? TYP_FARBEN[t] + ' border-current' : 'border-slate-200 text-slate-500'
                  }`}>
                    {TYP_LABELS[t]}
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Bezeichnung */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Bezeichnung *</label>
            <input {...register('bezeichnung')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
            {errors.bezeichnung && <p className="text-red-600 text-xs mt-1">{errors.bezeichnung.message}</p>}
          </div>

          {/* Einheit + Steuersatz */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Einheit *</label>
              <input {...register('einheit')} placeholder="Stunden, Stück, Pauschal …" className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
              {errors.einheit && <p className="text-red-600 text-xs mt-1">{errors.einheit.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Steuersatz *</label>
              <select {...register('steuersatz')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
                <option value="19">19 %</option>
                <option value="7">7 %</option>
                <option value="0">0 %</option>
              </select>
            </div>
          </div>

          {/* VK */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">VK brutto *</label>
            <input {...register('vk_brutto')} type="number" step="0.01" min="0.01" placeholder="0,00" className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
            {errors.vk_brutto && <p className="text-red-600 text-xs mt-1">{errors.vk_brutto.message}</p>}
          </div>

          {/* EK (nur bei DL + Fremdleistung) */}
          {hatEK(typ) && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">EK netto</label>
              <input {...register('ek_netto')} type="number" step="0.01" min="0" placeholder="0,00" className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
            </div>
          )}

          {/* Lieferant (nur bei DL + Fremdleistung) */}
          {hatLieferant(typ) && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Lieferant{typ === 'fremdleistung' ? ' *' : ''}
                </label>
                <select {...register('lieferant_id')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
                  <option value="">– kein –</option>
                  {lieferanten?.map(l => (
                    <option key={l.id} value={l.id}>{l.firmenname}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Lieferanten-ArtNr</label>
                <input {...register('lieferanten_artikelnr')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
          )}

          {/* Hersteller/Artikelcode (nur bei Dienstleistung) */}
          {hatHersteller(typ) && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Hersteller</label>
                <input {...register('hersteller')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Artikelcode</label>
                <input {...register('artikelcode')} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
          )}

          {/* Kategorie */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Kategorie</label>
            <input {...register('kategorie')} placeholder="z.B. IT-Hardware, Marketing, Beratung …" className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
          </div>

          {/* Beschreibung */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Beschreibung</label>
            <textarea {...register('beschreibung')} rows={3} placeholder="Ausführlicher Text für Rechnungsposition …" className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm resize-none" />
          </div>

          {mutation.isError && (
            <p className="text-red-600 text-sm">{(mutation.error as Error).message}</p>
          )}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 border border-slate-300 text-slate-600 rounded-lg py-2 text-sm hover:bg-slate-50">
              Abbrechen
            </button>
            <button type="submit" disabled={mutation.isPending} className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
              {mutation.isPending ? 'Speichert…' : initial ? 'Speichern' : 'Anlegen'}
            </button>
          </div>
        </form>
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
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">Inaktiv</span>
            )}
          </div>
          <h3 className="font-bold text-slate-800">{artikel.bezeichnung}</h3>
          <p className="text-xs text-slate-500">{artikel.artikelnummer}</p>
        </div>
        <button onClick={onEdit} className="text-sm text-blue-600 hover:underline">Bearbeiten</button>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm mb-4">
        <div className="text-slate-500">VK brutto</div>
        <div className="font-semibold text-slate-800">{formatEuro(artikel.vk_brutto)}</div>
        <div className="text-slate-500">VK netto</div>
        <div className="text-slate-700">{formatEuro(artikel.vk_netto)}</div>
        {artikel.ek_netto && <>
          <div className="text-slate-500">EK netto</div>
          <div className="text-slate-700">{formatEuro(artikel.ek_netto)}</div>
        </>}
        <div className="text-slate-500">USt-Satz</div>
        <div className="text-slate-700">{artikel.steuersatz} %</div>
        <div className="text-slate-500">Einheit</div>
        <div className="text-slate-700">{artikel.einheit}</div>
        {artikel.kategorie && <>
          <div className="text-slate-500">Kategorie</div>
          <div className="text-slate-700">{artikel.kategorie}</div>
        </>}
        {artikel.lieferant && <>
          <div className="text-slate-500">Lieferant</div>
          <div className="text-slate-700">{artikel.lieferant.firmenname}</div>
        </>}
        {artikel.hersteller && <>
          <div className="text-slate-500">Hersteller</div>
          <div className="text-slate-700">{artikel.hersteller}</div>
        </>}
        {artikel.artikelcode && <>
          <div className="text-slate-500">Artikelcode</div>
          <div className="text-slate-700 font-mono text-xs">{artikel.artikelcode}</div>
        </>}
        {artikel.lieferanten_artikelnr && <>
          <div className="text-slate-500">Lief.-ArtNr</div>
          <div className="text-slate-700 font-mono text-xs">{artikel.lieferanten_artikelnr}</div>
        </>}
      </div>

      {artikel.beschreibung && (
        <div className="text-sm text-slate-600 bg-slate-50 rounded-lg p-3 mb-4 whitespace-pre-wrap">
          {artikel.beschreibung}
        </div>
      )}

      {/* Verknüpfte Rechnungen */}
      <div className="border-t border-slate-100 pt-3 flex-1 min-h-0">
        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
          Verknüpfte Rechnungen ({rechnungen?.length ?? 0})
        </h4>
        {rechnungen && rechnungen.length > 0 ? (
          <div className="space-y-1 overflow-y-auto max-h-48">
            {rechnungen.map((r, i) => (
              <div key={i} className="flex items-center justify-between text-xs bg-slate-50 rounded px-2 py-1.5">
                <div>
                  <span className="font-medium text-slate-700">{r.rechnungsnummer ?? `RE-${r.rechnung_id}`}</span>
                  {r.kunde_name && <span className="text-slate-500 ms-2">· {r.kunde_name}</span>}
                </div>
                <div className="text-slate-500">
                  {r.menge} {r.einheit} · {new Date(r.datum).toLocaleDateString('de-DE')}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-400">Noch in keiner Rechnung verwendet.</p>
        )}
      </div>

      <div className="border-t border-slate-100 pt-3 mt-3">
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
      <div className="flex flex-col w-full max-w-xl border-e border-slate-200">
        {/* Header */}
        <div className="p-4 border-b border-slate-200">
          <div className="flex items-center justify-between mb-3">
            <h1 className="text-xl font-bold text-slate-800">Artikelstamm</h1>
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
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm mb-2"
          />
          <div className="flex gap-2 flex-wrap">
            {/* Typ-Filter */}
            {(['', 'artikel', 'dienstleistung', 'fremdleistung'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTypFilter(t)}
                className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                  typFilter === t
                    ? 'bg-slate-700 text-white border-slate-700'
                    : 'border-slate-300 text-slate-600 hover:border-slate-400'
                }`}
              >
                {t === '' ? 'Alle Typen' : TYP_LABELS[t]}
              </button>
            ))}
            <button
              onClick={() => setAktiv(aktiv === true ? undefined : true)}
              className={`text-xs px-2.5 py-1 rounded-full border transition-colors ms-auto ${
                aktiv === true
                  ? 'bg-green-100 text-green-700 border-green-300'
                  : 'border-slate-300 text-slate-600'
              }`}
            >
              {aktiv === true ? 'Nur aktive' : 'Alle'}
            </button>
          </div>
        </div>

        {/* Liste */}
        <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
          {isLoading ? (
            <div className="p-8 text-center text-slate-400 text-sm">Lädt…</div>
          ) : gefiltert.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-sm">Keine Artikel gefunden.</div>
          ) : (
            gefiltert.map(a => (
              <button
                key={a.id}
                onClick={() => setSelected(a)}
                className={`w-full text-start px-4 py-3 hover:bg-slate-50 transition-colors ${
                  selected?.id === a.id ? 'bg-blue-50 border-e-2 border-blue-500' : ''
                }`}
              >
                <div className="flex items-center justify-between mb-0.5">
                  <span className="font-medium text-sm text-slate-800">{a.bezeichnung}</span>
                  <span className="text-sm font-semibold text-slate-700">{formatEuro(a.vk_brutto)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">{a.artikelnummer}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded-full ${TYP_FARBEN[a.typ]}`}>
                    {TYP_LABELS[a.typ]}
                  </span>
                  {!a.aktiv && <span className="text-xs text-slate-400 italic">inaktiv</span>}
                  {a.lieferant && <span className="text-xs text-slate-400">· {a.lieferant.firmenname}</span>}
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Detail-Panel */}
      <div className="flex-1 p-6 overflow-y-auto">
        {selected ? (
          <ArtikelDetail
            key={selected.id}
            artikel={selected}
            onEdit={() => openEdit(selected)}
          />
        ) : (
          <div className="h-full flex items-center justify-center text-slate-400 text-sm">
            Artikel auswählen
          </div>
        )}
      </div>

      {/* Formular-Modal */}
      {showForm && (
        <ArtikelFormModal
          initial={editArtikel}
          onClose={closeForm}
          onSuccess={() => {
            closeForm()
            if (editArtikel) setSelected(prev => prev?.id === editArtikel.id ? null : prev)
          }}
        />
      )}
    </div>
  )
}
