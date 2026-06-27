import { useState, useEffect, useRef } from 'react'
import { LieferantErstellenModal } from '../../components/LieferantErstellenModal'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  getArtikel, createArtikel, updateArtikel, getArtikelRechnungen,
  getLieferanten, getUstSaetze, type Artikel, type ArtikelTyp,
  getArtikelGruppen, createArtikelGruppe, updateArtikelGruppe,
  toggleArtikelGruppeAktiv, deleteArtikelGruppe, getUnternehmen,
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

const GRUPPE_LABELS: Record<ArtikelTyp, string> = {
  artikel: 'Warengruppe',
  dienstleistung: 'Servicegruppe',
  fremdleistung: 'Fremdleistungsgruppe',
}

function hatEK(typ: ArtikelTyp) { return typ === 'artikel' || typ === 'fremdleistung' }
function hatLieferant(typ: ArtikelTyp) { return typ === 'artikel' || typ === 'dienstleistung' || typ === 'fremdleistung' }
function hatHersteller(typ: ArtikelTyp) { return typ === 'artikel' }

// ---------------------------------------------------------------------------
// Einheit-Auswahl (Dropdown + Freitext-Fallback)
// ---------------------------------------------------------------------------

const EINHEITEN = ['Stück', 'Pack', 'Set', 'Lizenz', 'Stunde', 'Tag', 'Monat', 'Pauschal', 'km', 'm²']

// Für Gewicht/Volumen/Länge Dezimalschritt, für alles andere (Stück, Pack …) ganzzahlig
function stepFuerEinheit(einheit: string | undefined | null): number {
  const e = (einheit ?? '').trim().toLowerCase()
  return /^(kg|g|mg|t|l|ml|dl|cl|m[²³]|m|cm|mm)$/.test(e) ? 0.001 : 1
}

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
// Gruppenverwaltung – Modal
// ---------------------------------------------------------------------------

function GruppenModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient()
  const [aktiverTyp, setAktiverTyp] = useState<ArtikelTyp>('artikel')
  const [neuerName, setNeuerName] = useState('')
  const [editId, setEditId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [fehler, setFehler] = useState('')

  const { data: gruppen = [] } = useQuery({
    queryKey: ['artikel-gruppen'],
    queryFn: () => getArtikelGruppen(),
  })

  const gefiltert = gruppen.filter(g => g.typ === aktiverTyp)

  const createMut = useMutation({
    mutationFn: () => createArtikelGruppe({ typ: aktiverTyp, name: neuerName.trim() }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['artikel-gruppen'] }); setNeuerName(''); setFehler('') },
    onError: (e: Error) => setFehler(e.message),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => updateArtikelGruppe(id, name),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['artikel-gruppen'] }); setEditId(null); setFehler('') },
    onError: (e: Error) => setFehler(e.message),
  })

  const toggleMut = useMutation({
    mutationFn: (id: number) => toggleArtikelGruppeAktiv(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['artikel-gruppen'] }),
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteArtikelGruppe(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['artikel-gruppen'] }),
    onError: (e: Error) => setFehler(e.message),
  })

  function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!neuerName.trim()) return
    createMut.mutate()
  }

  function handleUpdate(e: React.FormEvent) {
    e.preventDefault()
    if (!editId || !editName.trim()) return
    updateMut.mutate({ id: editId, name: editName })
  }

  const TYPEN: ArtikelTyp[] = ['artikel', 'dienstleistung', 'fremdleistung']

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white dark:bg-slate-800 rounded-xl shadow-xl w-full max-w-lg max-h-[85vh] flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between shrink-0">
          <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">Gruppen verwalten</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 text-xl leading-none">×</button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-200 dark:border-slate-700 shrink-0">
          {TYPEN.map(t => (
            <button
              key={t}
              onClick={() => { setAktiverTyp(t); setFehler(''); setEditId(null) }}
              className={`flex-1 py-2 text-sm font-medium transition-colors ${
                aktiverTyp === t
                  ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
              }`}
            >
              {GRUPPE_LABELS[t]}n
            </button>
          ))}
        </div>

        {/* Liste */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-1 min-h-0">
          {gefiltert.length === 0 && (
            <p className="text-sm text-slate-400 dark:text-slate-500 text-center py-4">Noch keine Gruppen angelegt.</p>
          )}
          {gefiltert.map(g => (
            <div
              key={g.id}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
                g.aktiv ? 'bg-slate-50 dark:bg-slate-700/50' : 'bg-slate-100/50 dark:bg-slate-800/50 opacity-60'
              }`}
            >
              {editId === g.id ? (
                <form onSubmit={handleUpdate} className="flex-1 flex gap-2">
                  <input
                    value={editName}
                    onChange={e => setEditName(e.target.value)}
                    autoFocus
                    className="flex-1 border border-slate-300 dark:border-slate-600 rounded px-2 py-1 text-sm dark:bg-slate-700 dark:text-slate-100"
                  />
                  <button type="submit" disabled={updateMut.isPending} className="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
                    OK
                  </button>
                  <button type="button" onClick={() => setEditId(null)} className="text-xs px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700">
                    Abbruch
                  </button>
                </form>
              ) : (
                <>
                  <span className="flex-1 text-sm text-slate-700 dark:text-slate-200">{g.name}</span>
                  <span className="text-xs text-slate-400 dark:text-slate-500">{g.artikel_anzahl} Artikel</span>
                  <button
                    onClick={() => { setEditId(g.id); setEditName(g.name); setFehler('') }}
                    className="text-xs text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 px-1"
                    title="Umbenennen"
                  >✎</button>
                  <button
                    onClick={() => toggleMut.mutate(g.id)}
                    className={`text-xs px-1 ${g.aktiv ? 'text-slate-400 hover:text-amber-600 dark:hover:text-amber-400' : 'text-green-600 dark:text-green-400 hover:text-green-700'}`}
                    title={g.aktiv ? 'Deaktivieren' : 'Aktivieren'}
                  >{g.aktiv ? '⊘' : '✓'}</button>
                  <button
                    onClick={() => { setFehler(''); deleteMut.mutate(g.id) }}
                    disabled={g.artikel_anzahl > 0}
                    className="text-xs text-slate-400 hover:text-red-600 dark:hover:text-red-400 px-1 disabled:opacity-30 disabled:cursor-not-allowed"
                    title={g.artikel_anzahl > 0 ? 'In Verwendung – nicht löschbar' : 'Löschen'}
                  >🗑</button>
                </>
              )}
            </div>
          ))}
        </div>

        {/* Neue Gruppe */}
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 shrink-0">
          {fehler && <p className="text-red-600 dark:text-red-400 text-xs mb-2">{fehler}</p>}
          <form onSubmit={handleCreate} className="flex gap-2">
            <input
              value={neuerName}
              onChange={e => setNeuerName(e.target.value)}
              placeholder={`Neue ${GRUPPE_LABELS[aktiverTyp]} …`}
              className="flex-1 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400"
            />
            <button
              type="submit"
              disabled={!neuerName.trim() || createMut.isPending}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              Anlegen
            </button>
          </form>
        </div>
      </div>
    </div>
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
  gruppe_id: z.string().optional(),
  differenzbesteuerung: z.boolean(),
  // Lagerführung
  lager_aktiv: z.boolean(),
  bestand_aktuell: z.string().optional(),
  mindestbestand: z.string().optional(),
  minusbestand_erlaubt: z.boolean(),
})

type FormValues = z.infer<typeof schema>

function formatEuro(v: string | null | undefined) {
  if (!v) return '–'
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(parseFloat(v))
}

// ---------------------------------------------------------------------------
// Formular
// ---------------------------------------------------------------------------

export function ArtikelFormModal({
  initial, onClose, onSuccess, onSaveArtikel, inline = false,
}: {
  initial?: Artikel
  onClose: () => void
  onSuccess: () => void
  onSaveArtikel?: (a: Artikel) => void
  inline?: boolean
}) {
  const qc = useQueryClient()
  const { data: lieferanten } = useQuery({ queryKey: ['lieferanten'], queryFn: getLieferanten })
  const [showNeuLieferant, setShowNeuLieferant] = useState(false)
  const { data: ustSaetze = [] } = useQuery({ queryKey: ['ust-saetze'], queryFn: getUstSaetze, staleTime: 1000 * 60 * 10 })
  const { data: unt } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen })
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
      gruppe_id: initial.gruppe_id ? String(initial.gruppe_id) : '',
      differenzbesteuerung: initial.differenzbesteuerung ?? false,
      lager_aktiv: initial.lager_aktiv ?? false,
      bestand_aktuell: String(parseFloat(String(initial.bestand_aktuell ?? '0'))),
      mindestbestand: String(parseFloat(String(initial.mindestbestand ?? '0'))),
      minusbestand_erlaubt: initial.minusbestand_erlaubt ?? false,
    } : {
      typ: 'artikel',
      steuersatz: defaultSatz,
      einheit: 'Stück',
      differenzbesteuerung: false,
      lager_aktiv: false,
      bestand_aktuell: '0',
      mindestbestand: '0',
      minusbestand_erlaubt: false,
    },
  })

  const typ = watch('typ') as ArtikelTyp
  const differenzbesteuerung = watch('differenzbesteuerung')
  const steuersatz = differenzbesteuerung ? 0 : parseFloat(watch('steuersatz') || '0')
  const lager_aktiv = watch('lager_aktiv')
  const einheit = watch('einheit')

  const { data: gruppen = [] } = useQuery({
    queryKey: ['artikel-gruppen', typ],
    queryFn: () => getArtikelGruppen(typ, true),
  })

  // Hilfswerte für die jeweils berechnete Seite (nicht im RHF-Schema)
  const [vkNetto, setVkNetto] = useState(
    initial?.vk_netto ? String(parseFloat(initial.vk_netto)) : ''
  )
  const [ekBrutto, setEkBrutto] = useState(
    initial?.ek_brutto ? String(parseFloat(initial.ek_brutto)) : ''
  )
  useEffect(() => {
    setVkNetto(initial?.vk_netto ? String(parseFloat(initial.vk_netto)) : '')
    setEkBrutto(initial?.ek_brutto ? String(parseFloat(initial.ek_brutto)) : '')
  }, [initial?.id])

  // Gruppe zurücksetzen wenn Typ wechselt – nicht beim Mounten (initial?.typ als Startwert)
  const prevTypRef = useRef(initial?.typ ?? 'artikel')
  useEffect(() => {
    if (prevTypRef.current === typ) return
    prevTypRef.current = typ
    setValue('gruppe_id', '')
  }, [typ, setValue])


  function bruttoAusNetto(netto: number) {
    if (differenzbesteuerung) return netto  // §25a: Brutto = Netto (kein USt-Aufschlag)
    return Math.round(netto * (1 + steuersatz / 100) * 100) / 100
  }
  function nettoAusBrutto(brutto: number) {
    if (differenzbesteuerung) return brutto  // §25a: Netto = Brutto
    return Math.round(brutto / (1 + steuersatz / 100) * 100) / 100
  }

  function onVkNettoChange(val: string) {
    setVkNetto(val)
    const n = parseFloat(val)
    if (!isNaN(n) && n > 0) setValue('vk_brutto', String(bruttoAusNetto(n)), { shouldValidate: true })
  }
  function onVkBruttoChange(val: string) {
    setValue('vk_brutto', val, { shouldValidate: true })
    const b = parseFloat(val)
    if (!isNaN(b) && b > 0) setVkNetto(String(nettoAusBrutto(b)))
    else setVkNetto('')
  }
  function onEkBruttoChange(val: string) {
    setEkBrutto(val)
    const b = parseFloat(val)
    if (!isNaN(b) && b >= 0) setValue('ek_netto', String(nettoAusBrutto(b)), { shouldValidate: true })
    else setValue('ek_netto', '')
  }
  function onEkNettoChange(val: string) {
    setValue('ek_netto', val, { shouldValidate: true })
    const n = parseFloat(val)
    if (!isNaN(n) && n >= 0) setEkBrutto(String(bruttoAusNetto(n)))
    else setEkBrutto('')
  }

  const mutation = useMutation({
    mutationFn: (v: FormValues) => {
      const payload = {
        typ: v.typ,
        bezeichnung: v.bezeichnung,
        einheit: v.einheit,
        // §25a: Steuersatz 0 senden, da keine USt ausgewiesen wird
        steuersatz: v.differenzbesteuerung ? '0' : v.steuersatz,
        vk_brutto: v.vk_brutto,
        ek_netto: hatEK(v.typ) && v.ek_netto ? v.ek_netto : undefined,
        lieferant_id: hatLieferant(v.typ) && v.lieferant_id ? Number(v.lieferant_id) : undefined,
        lieferanten_artikelnr: hatLieferant(v.typ) ? v.lieferanten_artikelnr || undefined : undefined,
        hersteller: hatHersteller(v.typ) ? v.hersteller || undefined : undefined,
        artikelcode: hatHersteller(v.typ) ? v.artikelcode || undefined : undefined,
        beschreibung: v.beschreibung || null,
        gruppe_id: v.gruppe_id ? Number(v.gruppe_id) : null,
        differenzbesteuerung: v.differenzbesteuerung,
        lager_aktiv: v.lager_aktiv,
        ...(v.lager_aktiv ? { bestand_aktuell: v.bestand_aktuell || '0' } : {}),
        mindestbestand: v.mindestbestand || '0',
        minusbestand_erlaubt: v.minusbestand_erlaubt,
      }
      return initial ? updateArtikel(initial.id, payload) : createArtikel(payload)
    },
    onSuccess: (gespeichert) => {
      qc.invalidateQueries({ queryKey: ['artikel'] })
      if (onSaveArtikel && !initial) onSaveArtikel(gespeichert)
      onSuccess()
    },
  })

  const formContent = (
    <form onSubmit={(e) => { e.preventDefault(); e.stopPropagation() }} className="space-y-4">
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

          {/* Differenzbesteuerung §25a UStG */}
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              {...register('differenzbesteuerung')}
              className="mt-0.5 w-4 h-4 rounded accent-amber-500"
            />
            <div>
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Differenzbesteuerung §25a UStG</span>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                Gebrauchtgegenstände – USt auf Marge (VK − EK), kein gesonderter USt-Ausweis
              </p>
            </div>
          </label>

          {/* Einheit + Steuersatz */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Einheit *</label>
              <EinheitAuswahl value={watch('einheit') ?? ''} onChange={(v) => setValue('einheit', v, { shouldValidate: true })} />
              {errors.einheit && <p className="text-red-600 dark:text-red-400 text-xs mt-1">{errors.einheit.message}</p>}
            </div>
            {!differenzbesteuerung && (
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
            )}
            {differenzbesteuerung && (
              <div>
                <label className="block text-sm font-medium text-slate-400 dark:text-slate-500 mb-1">Steuersatz</label>
                <div className="w-full border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-400 dark:text-slate-500 bg-slate-50 dark:bg-slate-800">
                  §25a – kein Ausweis
                </div>
              </div>
            )}
          </div>

          {/* VK */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
              Verkaufspreis *
              {differenzbesteuerung && (
                <span className="ms-2 text-xs font-normal text-amber-600 dark:text-amber-400">Rechnungspreis (Brutto = Netto)</span>
              )}
            </label>
            <div className={`grid gap-2 ${differenzbesteuerung ? 'grid-cols-1' : 'grid-cols-2'}`}>
              {!differenzbesteuerung && (
                <div>
                  <span className="text-xs text-slate-400 dark:text-slate-500 mb-1 block">Netto</span>
                  <input
                    type="number" step="0.01" min="0.01" placeholder="0,00"
                    value={vkNetto}
                    onChange={(e) => onVkNettoChange(e.target.value)}
                    className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400"
                  />
                </div>
              )}
              <div>
                <span className="text-xs text-slate-400 dark:text-slate-500 mb-1 block">
                  {differenzbesteuerung ? 'Verkaufspreis (inkl. Margensteuer)' : 'Brutto'}
                </span>
                <input
                  type="number" step="0.01" min="0.01" placeholder="0,00"
                  value={watch('vk_brutto') ?? ''}
                  onChange={(e) => onVkBruttoChange(e.target.value)}
                  className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400"
                />
              </div>
            </div>
            {errors.vk_brutto && <p className="text-red-600 dark:text-red-400 text-xs mt-1">{errors.vk_brutto.message}</p>}
          </div>

          {/* EK (nur bei Artikel + Fremdleistung) */}
          {hatEK(typ) && (
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
                Einkaufspreis
                {differenzbesteuerung && (
                  <span className="ms-2 text-xs font-normal text-amber-600 dark:text-amber-400">Ankaufspreis (von Privatperson, ohne USt)</span>
                )}
              </label>
              <div className={`grid gap-2 ${differenzbesteuerung ? 'grid-cols-1' : 'grid-cols-2'}`}>
                <div>
                  <span className="text-xs text-slate-400 dark:text-slate-500 mb-1 block">
                    {differenzbesteuerung ? 'Ankaufspreis' : 'Netto'}
                  </span>
                  <input
                    type="number" step="0.01" min="0" placeholder="0,00"
                    value={watch('ek_netto') ?? ''}
                    onChange={(e) => onEkNettoChange(e.target.value)}
                    className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400"
                  />
                </div>
                {!differenzbesteuerung && (
                  <div>
                    <span className="text-xs text-slate-400 dark:text-slate-500 mb-1 block">Brutto</span>
                    <input
                      type="number" step="0.01" min="0" placeholder="0,00"
                      value={ekBrutto}
                      onChange={(e) => onEkBruttoChange(e.target.value)}
                      className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400"
                    />
                  </div>
                )}
              </div>
              {/* Margenberechnung bei §25a */}
              {differenzbesteuerung && (() => {
                const vk = parseFloat(watch('vk_brutto') || '0')
                const ek = parseFloat(watch('ek_netto') || '0')
                if (vk > 0 && ek >= 0 && vk > ek) {
                  const marge = vk - ek
                  const ust = Math.round(marge * 19 / 119 * 100) / 100
                  const nettoMarge = Math.round((marge - ust) * 100) / 100
                  return (
                    <div className="mt-2 p-2.5 bg-amber-50 dark:bg-amber-950/30 rounded-lg border border-amber-200 dark:border-amber-800 text-xs text-amber-800 dark:text-amber-300 space-y-0.5">
                      <div className="flex justify-between"><span>Marge (VK − EK):</span><span className="font-medium">{marge.toLocaleString('de-DE', { minimumFractionDigits: 2 })} €</span></div>
                      <div className="flex justify-between"><span>USt auf Marge (19/119):</span><span>{ust.toLocaleString('de-DE', { minimumFractionDigits: 2 })} €</span></div>
                      <div className="flex justify-between border-t border-amber-200 dark:border-amber-700 pt-0.5 font-medium"><span>Netto-Marge:</span><span>{nettoMarge.toLocaleString('de-DE', { minimumFractionDigits: 2 })} €</span></div>
                    </div>
                  )
                }
                return null
              })()}
            </div>
          )}

          {/* Lieferant */}
          {hatLieferant(typ) && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
                  Lieferant{typ === 'fremdleistung' ? ' *' : ''}
                </label>
                <div className="flex gap-1">
                  <select {...register('lieferant_id')} className="flex-1 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-slate-100">
                    <option value="">– kein –</option>
                    {lieferanten?.map(l => (
                      <option key={l.id} value={l.id}>{l.firmenname}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => setShowNeuLieferant(true)}
                    title="Neuen Lieferanten anlegen"
                    className="shrink-0 px-2.5 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 text-base leading-none"
                  >
                    +
                  </button>
                </div>
                {showNeuLieferant && (
                  <LieferantErstellenModal
                    onClose={() => setShowNeuLieferant(false)}
                    onSave={(neu) => { setShowNeuLieferant(false); setValue('lieferant_id', String(neu.id ?? '')) }}
                  />
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Lieferanten-ArtNr</label>
                <input {...register('lieferanten_artikelnr')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-slate-100" />
              </div>
            </div>
          )}

          {/* Hersteller/Artikelcode (nur bei Artikel) */}
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

          {/* Gruppe */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">{GRUPPE_LABELS[typ]}</label>
            <select
              value={watch('gruppe_id') ?? ''}
              onChange={e => setValue('gruppe_id', e.target.value, { shouldDirty: true })}
              className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-slate-100"
            >
              <option value="">– keine –</option>
              {gruppen.map(g => (
                <option key={g.id} value={g.id}>{g.name}</option>
              ))}
            </select>
            {gruppen.length === 0 && (
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                Noch keine {GRUPPE_LABELS[typ]}n angelegt – über „Gruppen verwalten" erstellen.
              </p>
            )}
          </div>

          {/* Lagerführung – nur für physische Artikel und nur wenn global aktiviert */}
          {unt?.lagerführung_aktiv && typ === 'artikel' && (
            <div className="space-y-3 pt-1 border-t border-slate-200 dark:border-slate-700">
              <label className="flex items-start gap-3 cursor-pointer pt-1">
                <input type="checkbox" {...register('lager_aktiv')} className="mt-0.5 w-4 h-4 rounded accent-blue-600" />
                <div>
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Lagerführung aktivieren</span>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Bestand verfolgen, Mindestbestand überwachen</p>
                </div>
              </label>
              {lager_aktiv && (
                <div className="space-y-3 ps-7">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
                      {initial ? 'Lagerbestand' : 'Anfangsbestand'}
                    </label>
                    <input
                      type="number" step={stepFuerEinheit(einheit)} min="0" placeholder="0"
                      {...register('bestand_aktuell')}
                      className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-slate-100"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Mindestbestand</label>
                      <input
                        type="number" step={stepFuerEinheit(einheit)} min="0" placeholder="0"
                        {...register('mindestbestand')}
                        className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm dark:bg-slate-700 dark:text-slate-100"
                      />
                    </div>
                    <div className="flex items-end pb-2">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input type="checkbox" {...register('minusbestand_erlaubt')} className="w-4 h-4 rounded accent-blue-600" />
                        <span className="text-sm text-slate-700 dark:text-slate-200">Minusbestand erlaubt</span>
                      </label>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

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
            <button
              type="button"
              disabled={mutation.isPending}
              onClick={() => handleSubmit(v => mutation.mutate(v))()}
              className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
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
  const { data: unt } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen })

  const toggleAktiv = useMutation({
    mutationFn: () => updateArtikel(artikel.id, { aktiv: !artikel.aktiv }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['artikel'] }),
  })

  const [bestandEdit, setBestandEdit] = useState<string | null>(null)
  const bestandMut = useMutation({
    mutationFn: (wert: string) => updateArtikel(artikel.id, { bestand_aktuell: wert }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['artikel'] }); setBestandEdit(null) },
  })

  const [mindestEdit, setMindestEdit] = useState<string | null>(null)
  const mindestMut = useMutation({
    mutationFn: (wert: string) => updateArtikel(artikel.id, { mindestbestand: wert }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['artikel'] }); setMindestEdit(null) },
  })

  return (
    <div className="h-full flex flex-col">

      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-700 shrink-0 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${TYP_FARBEN[artikel.typ]}`}>
              {TYP_LABELS[artikel.typ]}
            </span>
            {artikel.differenzbesteuerung && (
              <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300">§25a UStG</span>
            )}
            {!artikel.aktiv && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400">Inaktiv</span>
            )}
          </div>
          <h3 className="font-semibold text-slate-800 dark:text-slate-100">{artikel.bezeichnung}</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{artikel.artikelnummer}</p>
        </div>
        <button onClick={onEdit} className="text-sm text-blue-600 dark:text-blue-400 hover:underline shrink-0 mt-0.5">Bearbeiten</button>
      </div>

      {/* Scrollbarer Content */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">

        {/* Preise */}
        <div>
          <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">Preise</p>
          {artikel.differenzbesteuerung ? (
            // §25a: Marge + Steuerberechnung anzeigen
            <div className="space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2">
                  <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Verkaufspreis</p>
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{formatEuro(artikel.vk_brutto)}</p>
                </div>
                {artikel.ek_netto && (
                  <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2">
                    <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Ankaufspreis</p>
                    <p className="text-sm text-slate-700 dark:text-slate-200">{formatEuro(artikel.ek_netto)}</p>
                  </div>
                )}
              </div>
              {artikel.ek_netto && (() => {
                const vk = parseFloat(artikel.vk_brutto)
                const ek = parseFloat(artikel.ek_netto!)
                if (vk > ek) {
                  const marge = vk - ek
                  const ust = Math.round(marge * 19 / 119 * 100) / 100
                  const nettoMarge = Math.round((marge - ust) * 100) / 100
                  return (
                    <div className="p-2.5 bg-amber-50 dark:bg-amber-950/30 rounded-lg border border-amber-200 dark:border-amber-800 text-xs text-amber-800 dark:text-amber-300 space-y-0.5">
                      <p className="font-medium mb-1">Margenberechnung §25a</p>
                      <div className="flex justify-between"><span>Marge (VK − EK):</span><span className="font-medium">{marge.toLocaleString('de-DE', { minimumFractionDigits: 2 })} €</span></div>
                      <div className="flex justify-between"><span>USt auf Marge (19/119):</span><span>{ust.toLocaleString('de-DE', { minimumFractionDigits: 2 })} €</span></div>
                      <div className="flex justify-between border-t border-amber-200 dark:border-amber-700 pt-0.5 font-medium"><span>Netto-Marge:</span><span>{nettoMarge.toLocaleString('de-DE', { minimumFractionDigits: 2 })} €</span></div>
                    </div>
                  )
                }
                return null
              })()}
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2">
                <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">VK brutto</p>
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{formatEuro(artikel.vk_brutto)}</p>
              </div>
              <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2">
                <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">VK netto</p>
                <p className="text-sm text-slate-700 dark:text-slate-200">{formatEuro(artikel.vk_netto)}</p>
              </div>
              {artikel.ek_netto && (
                <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2">
                  <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">EK netto</p>
                  <p className="text-sm text-slate-700 dark:text-slate-200">{formatEuro(artikel.ek_netto)}</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Details */}
        <div>
          <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">Details</p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            <div>
              <p className="text-xs text-slate-400 dark:text-slate-500">USt-Satz</p>
              <p className="text-sm text-slate-700 dark:text-slate-200">{artikel.steuersatz} %</p>
            </div>
            <div>
              <p className="text-xs text-slate-400 dark:text-slate-500">Einheit</p>
              <p className="text-sm text-slate-700 dark:text-slate-200">{artikel.einheit}</p>
            </div>
            {artikel.gruppe_obj && (
              <div>
                <p className="text-xs text-slate-400 dark:text-slate-500">{GRUPPE_LABELS[artikel.typ]}</p>
                <p className="text-sm text-slate-700 dark:text-slate-200">{artikel.gruppe_obj.name}</p>
              </div>
            )}
            {artikel.lieferant && (
              <div>
                <p className="text-xs text-slate-400 dark:text-slate-500">Lieferant</p>
                <p className="text-sm text-slate-700 dark:text-slate-200">{artikel.lieferant.firmenname}</p>
              </div>
            )}
            {artikel.lieferanten_artikelnr && (
              <div>
                <p className="text-xs text-slate-400 dark:text-slate-500">Lief.-ArtNr</p>
                <p className="text-sm text-slate-700 dark:text-slate-200 font-mono">{artikel.lieferanten_artikelnr}</p>
              </div>
            )}
            {artikel.hersteller && (
              <div>
                <p className="text-xs text-slate-400 dark:text-slate-500">Hersteller</p>
                <p className="text-sm text-slate-700 dark:text-slate-200">{artikel.hersteller}</p>
              </div>
            )}
            {artikel.artikelcode && (
              <div>
                <p className="text-xs text-slate-400 dark:text-slate-500">Artikelcode</p>
                <p className="text-sm text-slate-700 dark:text-slate-200 font-mono">{artikel.artikelcode}</p>
              </div>
            )}
          </div>
        </div>

        {/* Lager – sichtbar wenn global aktiv und Artikel tracked */}
        {unt?.lagerführung_aktiv && artikel.lager_aktiv && (() => {
          const bestand = parseFloat(String(artikel.bestand_aktuell))
          const mindest = parseFloat(String(artikel.mindestbestand))
          const unterschritten = bestand <= mindest
          return (
            <div>
              <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">Lager</p>
              <div className="grid grid-cols-3 gap-2">
                {/* Bestand */}
                <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2">
                  <div className="flex items-center justify-between mb-0.5">
                    <p className="text-xs text-slate-500 dark:text-slate-400">Bestand</p>
                    <button onClick={() => setBestandEdit(String(bestand))} className="text-xs text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 leading-none">✎</button>
                  </div>
                  {bestandEdit === null ? (
                    <p className={`text-sm font-semibold ${unterschritten ? 'text-red-600 dark:text-red-400' : 'text-slate-800 dark:text-slate-100'}`}>
                      {bestand.toLocaleString('de-DE', { maximumFractionDigits: 3 })} {artikel.einheit}
                    </p>
                  ) : (
                    <div className="flex items-center gap-1 mt-0.5">
                      <input
                        type="number" step={stepFuerEinheit(artikel.einheit)}
                        value={bestandEdit}
                        onChange={e => setBestandEdit(e.target.value)}
                        autoFocus
                        onKeyDown={e => { if (e.key === 'Enter') bestandMut.mutate(bestandEdit); if (e.key === 'Escape') setBestandEdit(null) }}
                        className="w-full border border-slate-300 dark:border-slate-600 rounded px-1.5 py-0.5 text-xs dark:bg-slate-700 dark:text-slate-100 text-right"
                      />
                      <button onClick={() => bestandMut.mutate(bestandEdit)} disabled={bestandMut.isPending} className="text-xs px-1.5 py-0.5 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">✓</button>
                      <button onClick={() => setBestandEdit(null)} className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">×</button>
                    </div>
                  )}
                </div>

                {/* Schwellwert */}
                <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2">
                  <div className="flex items-center justify-between mb-0.5">
                    <p className="text-xs text-slate-500 dark:text-slate-400">Schwellwert</p>
                    <button onClick={() => setMindestEdit(String(mindest))} className="text-xs text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 leading-none">✎</button>
                  </div>
                  {mindestEdit === null ? (
                    <p className="text-sm text-slate-700 dark:text-slate-200">
                      {mindest.toLocaleString('de-DE', { maximumFractionDigits: 3 })} {artikel.einheit}
                    </p>
                  ) : (
                    <div className="flex items-center gap-1 mt-0.5">
                      <input
                        type="number" step={stepFuerEinheit(artikel.einheit)} min="0"
                        value={mindestEdit}
                        onChange={e => setMindestEdit(e.target.value)}
                        autoFocus
                        onKeyDown={e => { if (e.key === 'Enter') mindestMut.mutate(mindestEdit); if (e.key === 'Escape') setMindestEdit(null) }}
                        className="w-full border border-slate-300 dark:border-slate-600 rounded px-1.5 py-0.5 text-xs dark:bg-slate-700 dark:text-slate-100 text-right"
                      />
                      <button onClick={() => mindestMut.mutate(mindestEdit)} disabled={mindestMut.isPending} className="text-xs px-1.5 py-0.5 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">✓</button>
                      <button onClick={() => setMindestEdit(null)} className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">×</button>
                    </div>
                  )}
                </div>

                {/* Minusbestand */}
                <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2">
                  <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Minusbestand</p>
                  <p className={`text-sm ${artikel.minusbestand_erlaubt ? 'text-slate-700 dark:text-slate-200' : 'text-amber-700 dark:text-amber-400'}`}>
                    {artikel.minusbestand_erlaubt ? 'Erlaubt' : 'Nicht erlaubt'}
                  </p>
                </div>
              </div>

              {unterschritten && (
                <div className="mt-2 p-2 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 text-xs text-amber-700 dark:text-amber-300">
                  Bestand hat den Schwellwert erreicht oder unterschritten.
                </div>
              )}
            </div>
          )
        })()}

        {/* Beschreibung */}
        {artikel.beschreibung && (
          <div>
            <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">Beschreibung</p>
            <p className="text-sm text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-3 whitespace-pre-wrap">{artikel.beschreibung}</p>
          </div>
        )}

        {/* Verknüpfte Rechnungen */}
        <div>
          <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">
            Verknüpfte Rechnungen ({rechnungen?.length ?? 0})
          </p>
          {rechnungen && rechnungen.length > 0 ? (
            <div className="space-y-1.5">
              {rechnungen.map((r, i) => (
                <div key={i} className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 flex items-start justify-between gap-2">
                  <div>
                    <span className="text-xs font-medium text-slate-700 dark:text-slate-200">{r.rechnungsnummer ?? `RE-${r.rechnung_id}`}</span>
                    {r.kunde_name && <span className="text-xs text-slate-500 dark:text-slate-400 ms-2">{r.kunde_name}</span>}
                  </div>
                  <div className="text-xs text-slate-400 dark:text-slate-500 text-right shrink-0">
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
      </div>

      {/* Footer */}
      <div className="shrink-0 border-t border-slate-200 dark:border-slate-700 px-5 py-3">
        <button
          onClick={() => toggleAktiv.mutate()}
          className={`text-xs ${artikel.aktiv ? 'text-slate-400 hover:text-red-500 dark:hover:text-red-400' : 'text-green-600 dark:text-green-400 hover:text-green-700'}`}
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
  const [gruppeFilter, setGruppeFilter] = useState<number | ''>('')
  const [aktiv, setAktiv] = useState<boolean | undefined>(true)
  const [selected, setSelected] = useState<Artikel | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editArtikel, setEditArtikel] = useState<Artikel | undefined>()
  const [showGruppen, setShowGruppen] = useState(false)

  const { data: artikel, isLoading } = useQuery({
    queryKey: ['artikel', aktiv, typFilter],
    queryFn: () => getArtikel({ aktiv, typ: typFilter || undefined }),
  })

  const { data: alleGruppen = [] } = useQuery({
    queryKey: ['artikel-gruppen', typFilter || undefined],
    queryFn: () => getArtikelGruppen(typFilter || undefined, true),
  })

  // selected mit aktuellem Listeneintrag synchronisieren (z. B. nach Toggle-Mutationen)
  useEffect(() => {
    if (!selected || !artikel) return
    const aktuell = artikel.find(a => a.id === selected.id)
    if (aktuell) setSelected(aktuell)
  }, [artikel])

  const gefiltert = (artikel ?? []).filter(a => {
    if (gruppeFilter !== '' && a.gruppe_id !== gruppeFilter) return false
    if (!suche) return true
    const s = suche.toLowerCase()
    return (
      a.bezeichnung.toLowerCase().includes(s) ||
      a.artikelnummer.toLowerCase().includes(s) ||
      (a.lieferant?.firmenname.toLowerCase().includes(s) ?? false) ||
      (a.gruppe_obj?.name.toLowerCase().includes(s) ?? false)
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
      <div className={`${showForm ? 'w-1/3 min-w-[260px] shrink-0' : 'flex-1'} flex flex-col border-e border-slate-200 dark:border-slate-700 min-w-0 transition-all`}>
        {/* Header */}
        <div className="p-6 pb-4 shrink-0">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Artikel</h1>
            <div className="flex gap-2">
              <button
                onClick={() => setShowGruppen(true)}
                className="px-3 py-2 text-sm font-medium border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700"
              >
                Gruppen
              </button>
              <button
                onClick={() => { setEditArtikel(undefined); setShowForm(true) }}
                className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-xl hover:bg-blue-700"
              >
                + Neu
              </button>
            </div>
          </div>
          <input
            data-search-input
            value={suche}
            onChange={e => setSuche(e.target.value)}
            placeholder="Suche nach Bezeichnung, Artikelnummer, Gruppe …"
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm mb-3 dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400"
          />
          <div className="flex gap-2 flex-wrap">
            {(['', 'artikel', 'dienstleistung', 'fremdleistung'] as const).map(t => (
              <button
                key={t}
                onClick={() => { setTypFilter(t); setGruppeFilter('') }}
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
          {alleGruppen.length > 0 && (
            <select
              value={gruppeFilter}
              onChange={e => setGruppeFilter(e.target.value === '' ? '' : Number(e.target.value))}
              className={`mt-2 w-full border rounded-lg px-3 py-1.5 text-xs dark:bg-slate-700 dark:text-slate-100 transition-colors ${
                gruppeFilter !== ''
                  ? 'border-blue-400 dark:border-blue-500 text-slate-800 dark:text-slate-100'
                  : 'border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400'
              }`}
            >
              <option value="">Alle Gruppen</option>
              {alleGruppen.map(g => (
                <option key={g.id} value={g.id}>
                  {typFilter === '' ? `${GRUPPE_LABELS[g.typ]}: ` : ''}{g.name}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Liste */}
        <div className="flex-1 overflow-y-auto min-h-0 px-6 pb-6">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden divide-y divide-slate-100 dark:divide-slate-700">
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
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs text-slate-400 dark:text-slate-500">{a.artikelnummer}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded-full ${TYP_FARBEN[a.typ]}`}>
                    {TYP_LABELS[a.typ]}
                  </span>
                  {a.differenzbesteuerung && (
                    <span className="text-xs px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300">§25a</span>
                  )}
                  {a.gruppe_obj && (
                    <span className="text-xs text-slate-400 dark:text-slate-500">· {a.gruppe_obj.name}</span>
                  )}
                  {!a.aktiv && <span className="text-xs text-slate-400 dark:text-slate-500 italic">inaktiv</span>}
                </div>
              </button>
            ))
          )}
          </div>
        </div>
      </div>

      {/* Detail-Panel */}
      {!showForm && (
        <div className="flex-1 overflow-hidden">
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

      {/* Gruppen-Modal */}
      {showGruppen && <GruppenModal onClose={() => setShowGruppen(false)} />}
    </div>
  )
}
