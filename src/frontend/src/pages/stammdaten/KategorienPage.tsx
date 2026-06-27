import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getKategorien, toggleKategorieAktiv,
  updateKategorieKonten, resetKategorieKonten, createKategorie, updateKategorie, deleteKategorie,
  updateKategorieBeschreibung, downloadKategorienPdf, getUnternehmen,
  type Kategorie, type KategorieCreate,
} from '../../api/client'
import { InfoTooltip } from '../../components/InfoTooltip'

const KONTENART_META: Record<string, { label: string; cls: string; beschreibung: string }> = {
  Erlös:   { label: 'Erlöse',   cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300', beschreibung: 'Betriebseinnahmen' },
  Aufwand: { label: 'Aufwand',  cls: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',                 beschreibung: 'Betriebsausgaben' },
  Anlage:  { label: 'Anlage',   cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',             beschreibung: 'Anlagevermögen' },
  Privat:  { label: 'Privat',   cls: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',         beschreibung: 'Private Entnahmen/Einlagen' },
}

const REIHENFOLGE = ['Erlös', 'Aufwand', 'Anlage', 'Privat']

function UstBadge({ satz }: { satz: number }) {
  if (satz === 0)  return <span className="text-xs text-slate-400 dark:text-slate-500">§19 / 0 %</span>
  if (satz === 7)  return <span className="text-xs text-amber-600 dark:text-amber-400">7 %</span>
  if (satz === 19) return <span className="text-xs text-blue-600 dark:text-blue-400">19 %</span>
  return <span className="text-xs text-slate-400">{satz} %</span>
}

// ---------------------------------------------------------------------------
// Beschreibungs-Inline-Editor
// ---------------------------------------------------------------------------

function BeschreibungEditor({
  kategorie,
  onSave,
  onClose,
}: {
  kategorie: Kategorie
  onSave: (text: string | null) => void
  onClose: () => void
}) {
  const [text, setText] = useState(kategorie.beschreibung ?? '')

  function handleBlurOrSave() {
    const val = text.trim() || null
    if (val !== (kategorie.beschreibung ?? null)) {
      onSave(val)
    }
  }

  return (
    <tr className="bg-sky-50 dark:bg-sky-950/40">
      <td colSpan={8} className="px-4 py-3">
        <div className="space-y-2">
          <p className="text-xs font-medium text-sky-700 dark:text-sky-300">
            💬 Verwendungsbeispiele / Notizen zu „{kategorie.name}"
          </p>
          <textarea
            rows={3}
            autoFocus
            value={text}
            onChange={e => setText(e.target.value)}
            onFocus={e => { const l = e.currentTarget.value.length; e.currentTarget.setSelectionRange(l, l) }}
            placeholder="z. B. Büromaterial – Stifte, Papier, Druckerpatronen, Ordner …"
            className="w-full text-sm border border-sky-300 dark:border-sky-700 rounded-lg px-3 py-2 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-sky-400 resize-y"
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => { handleBlurOrSave(); onClose() }}
              className="px-3 py-1.5 text-xs bg-sky-600 text-white rounded-lg hover:bg-sky-700"
            >
              Speichern
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-xs border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700"
            >
              Schließen
            </button>
            {kategorie.beschreibung && (
              <button
                type="button"
                onClick={() => { onSave(null); onClose() }}
                className="px-3 py-1.5 text-xs text-red-400 hover:text-red-600 dark:hover:text-red-300 ml-auto"
              >
                Löschen
              </button>
            )}
          </div>
        </div>
      </td>
    </tr>
  )
}

// ---------------------------------------------------------------------------
// Neues-Kategorie-Dialog
// ---------------------------------------------------------------------------

const LEER: KategorieCreate = {
  name: '', kontenart: 'Aufwand', konto_skr03: '', konto_skr04: '',
  euer_zeile: undefined, eks_kategorie: '', vorsteuer_prozent: 100, ust_satz_standard: 19,
  beschreibung: '',
}

function NeuDialog({ onClose, bearbeiten, hatEks }: { onClose: () => void; bearbeiten?: Kategorie; hatEks: boolean }) {
  const [form, setForm] = useState<KategorieCreate>(bearbeiten ? {
    name: bearbeiten.name,
    kontenart: bearbeiten.kontenart,
    konto_skr03: bearbeiten.konto_skr03 ?? '',
    konto_skr04: bearbeiten.konto_skr04 ?? '',
    euer_zeile: bearbeiten.euer_zeile ?? undefined,
    eks_kategorie: bearbeiten.eks_kategorie ?? '',
    vorsteuer_prozent: Number(bearbeiten.vorsteuer_prozent),
    ust_satz_standard: bearbeiten.ust_satz_standard,
    beschreibung: bearbeiten.beschreibung ?? '',
  } : LEER)
  const [err, setErr] = useState('')
  const qc = useQueryClient()
  const mut = useMutation({
    mutationFn: bearbeiten
      ? (data: KategorieCreate) => updateKategorie(bearbeiten.id, data)
      : createKategorie,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['kategorien'] }); onClose() },
    onError: (e: Error) => setErr(e.message),
  })

  const set = (k: keyof KategorieCreate, v: string | number | undefined) =>
    setForm(f => ({ ...f, [k]: v }))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4"
        onClick={e => e.stopPropagation()}
      >
        <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">{bearbeiten ? 'Kategorie bearbeiten' : 'Neue Kategorie'}</h3>

        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="text-xs font-medium text-slate-500 dark:text-slate-400">Bezeichnung *</label>
            <input
              className="mt-1 w-full border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 rounded-lg px-3 py-2 text-sm"
              value={form.name}
              onChange={e => set('name', e.target.value)}
              placeholder="z.B. Fachzeitschriften"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-slate-500 dark:text-slate-400">Kontenart *</label>
            <select
              className="mt-1 w-full border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 rounded-lg px-3 py-2 text-sm"
              value={form.kontenart}
              onChange={e => set('kontenart', e.target.value)}
            >
              <option>Aufwand</option>
              <option>Erlös</option>
              <option>Anlage</option>
              <option>Privat</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-500 dark:text-slate-400">USt-Satz Standard</label>
            <select
              className="mt-1 w-full border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 rounded-lg px-3 py-2 text-sm"
              value={form.ust_satz_standard}
              onChange={e => set('ust_satz_standard', Number(e.target.value))}
            >
              <option value={0}>0 % (§19 / steuerfrei)</option>
              <option value={7}>7 %</option>
              <option value={19}>19 %</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-500 dark:text-slate-400">SKR03-Konto</label>
            <input
              className="mt-1 w-full border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 rounded-lg px-3 py-2 text-sm font-mono"
              value={form.konto_skr03 ?? ''}
              onChange={e => set('konto_skr03', e.target.value)}
              placeholder="z.B. 4945"
              maxLength={10}
            />
          </div>

          <div>
            <label className="text-xs font-medium text-slate-500 dark:text-slate-400">SKR04-Konto</label>
            <input
              className="mt-1 w-full border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 rounded-lg px-3 py-2 text-sm font-mono"
              value={form.konto_skr04 ?? ''}
              onChange={e => set('konto_skr04', e.target.value)}
              placeholder="z.B. 6821"
              maxLength={10}
            />
          </div>

          <div>
            <label className="text-xs font-medium text-slate-500 dark:text-slate-400">EÜR-Zeile</label>
            <input
              type="number"
              className="mt-1 w-full border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 rounded-lg px-3 py-2 text-sm"
              value={form.euer_zeile ?? ''}
              onChange={e => set('euer_zeile', e.target.value ? Number(e.target.value) : undefined)}
              placeholder="optional"
            />
          </div>

          {hatEks && (
            <div>
              <label className="text-xs font-medium text-slate-500 dark:text-slate-400">EKS-Feld</label>
              <input
                className="mt-1 w-full border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 rounded-lg px-3 py-2 text-sm font-mono"
                value={form.eks_kategorie ?? ''}
                onChange={e => set('eks_kategorie', e.target.value)}
                placeholder="z.B. B13 (optional)"
              />
            </div>
          )}

          <div>
            <label className="text-xs font-medium text-slate-500 dark:text-slate-400">Vorsteuer %</label>
            <input
              type="number"
              min={0} max={100}
              className="mt-1 w-full border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 rounded-lg px-3 py-2 text-sm"
              value={form.vorsteuer_prozent ?? 100}
              onChange={e => set('vorsteuer_prozent', Number(e.target.value))}
            />
          </div>

          <div className="col-span-2">
            <label className="text-xs font-medium text-slate-500 dark:text-slate-400">Verwendungsbeispiele (optional)</label>
            <textarea
              rows={2}
              className="mt-1 w-full border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 rounded-lg px-3 py-2 text-sm resize-none"
              value={form.beschreibung ?? ''}
              onChange={e => set('beschreibung', e.target.value)}
              placeholder="z. B. was gehört in diese Kategorie, was nicht …"
            />
          </div>
        </div>

        {err && <p className="text-xs text-red-500">{err}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700"
          >
            Abbrechen
          </button>
          <button
            type="button"
            disabled={!form.name || mut.isPending}
            onClick={() => mut.mutate(form)}
            className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {bearbeiten ? 'Speichern' : 'Anlegen'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// KontoCellEdit – Inline-Eingabefeld für SKR-Konto
// ---------------------------------------------------------------------------

function KontoCellEdit({
  value, defaultValue, isModified, onSave, onReset,
}: {
  value: string | undefined
  defaultValue: string | undefined
  isModified: boolean
  onSave: (v: string) => void
  onReset: () => void
}) {
  const [local, setLocal] = useState(value ?? '')

  return (
    <div className="flex items-center gap-1">
      <input
        className={`w-16 font-mono text-xs border rounded px-1.5 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 ${
          isModified
            ? 'border-amber-400 dark:border-amber-500'
            : 'border-slate-300 dark:border-slate-600'
        }`}
        value={local}
        maxLength={10}
        onChange={e => setLocal(e.target.value)}
        onBlur={() => { if (local !== (value ?? '')) onSave(local) }}
        onKeyDown={e => { if (e.key === 'Enter') { e.currentTarget.blur() } }}
      />
      {isModified && (
        <button
          type="button"
          title={`Zurück auf Standard (${defaultValue ?? '—'})`}
          onClick={onReset}
          className="text-amber-500 hover:text-amber-700 dark:hover:text-amber-300 text-xs"
        >
          ↩
        </button>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// EuerZeileEdit – Inline-Eingabe für EÜR-Zeile
// ---------------------------------------------------------------------------

function EuerZeileEdit({
  value,
  onSave,
}: {
  value: number | undefined
  onSave: (v: number | null) => void
}) {
  const [local, setLocal] = useState(value != null ? String(value) : '')

  return (
    <input
      type="number"
      min={1}
      max={200}
      className="w-16 text-xs border border-slate-300 dark:border-slate-600 rounded px-1.5 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
      value={local}
      placeholder="—"
      onChange={e => setLocal(e.target.value)}
      onBlur={() => {
        const n = local.trim() ? Number(local) : null
        if (n !== (value ?? null)) onSave(n)
      }}
      onKeyDown={e => { if (e.key === 'Enter') e.currentTarget.blur() }}
    />
  )
}

// ---------------------------------------------------------------------------
// KategorienPage
// ---------------------------------------------------------------------------

export function KategorienPage() {
  const [filter, setFilter] = useState('')
  const [nurAktive, setNurAktive] = useState(false)
  const [editModus, setEditModus] = useState(false)
  const [neuDialog, setNeuDialog] = useState(false)
  const [bearbeitenKat, setBearbeitenKat] = useState<Kategorie | null>(null)
  const [loeschenId, setLoeschenId] = useState<number | null>(null)
  const [loeschFehler, setLoeschFehler] = useState<{ id: number; msg: string } | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const qc = useQueryClient()

  const { data: kategorien = [], isLoading } = useQuery({
    queryKey: ['kategorien'],
    queryFn: () => getKategorien(false),
  })

  const { data: unternehmen } = useQuery({
    queryKey: ['unternehmen'],
    queryFn: getUnternehmen,
    staleTime: 1000 * 60 * 10,
  })
  const hatEks = unternehmen?.bezieht_transferleistungen ?? false

  const toggleMutation = useMutation({
    mutationFn: (id: number) => toggleKategorieAktiv(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['kategorien'] }),
  })

  const kontenMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { konto_skr03?: string; konto_skr04?: string; euer_zeile?: number | null; euer_zeile_loeschen?: boolean } }) =>
      updateKategorieKonten(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['kategorien'] }),
  })

  const resetMutation = useMutation({
    mutationFn: (id: number) => resetKategorieKonten(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['kategorien'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteKategorie(id),
    onSuccess: () => { setLoeschFehler(null); qc.invalidateQueries({ queryKey: ['kategorien'] }) },
    onError: (e: Error, id: number) => setLoeschFehler({ id, msg: e.message }),
  })

  const beschreibungMutation = useMutation({
    mutationFn: ({ id, text }: { id: number; text: string | null }) =>
      updateKategorieBeschreibung(id, text),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['kategorien'] }),
  })

  const suchtext = filter.toLowerCase()
  const gefiltert = kategorien.filter(k =>
    (nurAktive ? k.aktiv : true) &&
    (k.name.toLowerCase().includes(suchtext) ||
    (k.konto_skr03 ?? '').includes(suchtext) ||
    (k.konto_skr04 ?? '').includes(suchtext) ||
    (k.eks_kategorie ?? '').toLowerCase().includes(suchtext) ||
    (k.beschreibung ?? '').toLowerCase().includes(suchtext))
  )

  const gruppen = REIHENFOLGE
    .map(art => ({ art, liste: gefiltert.filter(k => k.kontenart === art) }))
    .filter(g => g.liste.length > 0)

  return (
    <div className="p-6 max-w-4xl">
      {neuDialog && <NeuDialog onClose={() => setNeuDialog(false)} hatEks={hatEks} />}
      {bearbeitenKat && <NeuDialog onClose={() => setBearbeitenKat(null)} bearbeiten={bearbeitenKat} hatEks={hatEks} />}

      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Kategorien</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
          {kategorien.length} Buchungskategorien mit SKR03/04-Konten und EÜR-Zuordnung
        </p>
      </div>

      {/* Toolbar */}
      <div className="mb-5 flex items-center gap-3 flex-wrap">
        <input
          type="search"
          data-search-input
          value={filter}
          onChange={e => setFilter(e.target.value)}
          placeholder={`Name, SKR-Konto${hatEks ? ', EKS' : ''} oder Beschreibung suchen …`}
          className="w-full max-w-sm border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="button"
          onClick={() => setNurAktive(v => !v)}
          className={`shrink-0 text-sm px-3 py-2 rounded-lg border transition-colors ${
            nurAktive
              ? 'bg-blue-600 text-white border-blue-600'
              : 'border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
          }`}
        >
          {nurAktive ? 'Nur aktive' : 'Alle'}
        </button>
        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            onClick={() => downloadKategorienPdf()}
            className="text-sm px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700"
            title="Alle Kategorien als PDF exportieren (ohne Kontonummern)"
          >
            📄 PDF
          </button>
          <button
            type="button"
            onClick={() => { setEditModus(v => !v); setExpandedId(null) }}
            className={`text-sm px-3 py-2 rounded-lg border transition-colors ${
              editModus
                ? 'bg-amber-50 border-amber-400 text-amber-700 dark:bg-amber-900/30 dark:border-amber-500 dark:text-amber-300'
                : 'border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
            }`}
          >
            {editModus ? '✏️ Bearbeiten – aktiv' : 'Bearbeiten'}
          </button>
          <button
            type="button"
            onClick={() => setNeuDialog(true)}
            className="text-sm px-3 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700"
          >
            + Neue Kategorie
          </button>
        </div>
      </div>

      {editModus && (
        <div className="mb-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-xl px-4 py-3 text-xs text-amber-700 dark:text-amber-300">
          Bearbeitungsmodus aktiv – SKR03/SKR04-Kontonummern, EÜR-Zeile und Verwendungsbeispiele können bearbeitet werden.
          Geänderte Konten sind <span className="font-semibold">orange</span> markiert. Mit ↩ zurück auf den Standardwert.
        </div>
      )}

      {isLoading && <p className="text-slate-400 text-sm">Lade…</p>}

      {/* Gruppen */}
      <div className="space-y-8">
        {gruppen.map(({ art, liste }) => {
          const meta = KONTENART_META[art] ?? { label: art, cls: 'bg-slate-100 text-slate-600', beschreibung: '' }
          return (
            <div key={art}>
              <div className="flex items-center gap-2 mb-3">
                <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${meta.cls}`}>
                  {meta.label}
                </span>
                <span className="text-xs text-slate-400 dark:text-slate-500">{meta.beschreibung}</span>
                <span className="text-xs text-slate-300 dark:text-slate-600 ml-auto">{liste.length} Kategorien</span>
              </div>

              <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-slate-50 dark:bg-slate-900 text-xs text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">
                      <th className="text-left px-4 py-2.5 font-medium sticky left-0 bg-slate-50 dark:bg-slate-900 z-10">Bezeichnung</th>
                      <th className="text-left px-3 py-2.5 font-medium w-28">SKR03</th>
                      <th className="text-left px-3 py-2.5 font-medium w-28">SKR04</th>
                      <th className="text-left px-3 py-2.5 font-medium w-24">EÜR-Zeile</th>
                      {hatEks && <th className="text-left px-3 py-2.5 font-medium w-20">EKS</th>}
                      <th className="text-left px-3 py-2.5 font-medium w-24">USt-Satz</th>
                      <th className="text-left px-3 py-2.5 font-medium w-16">VSt %</th>
                      <th className="px-3 py-2.5 w-28 text-right" />
                    </tr>
                  </thead>
                  <tbody>
                    {liste.map((k, i) => (
                      <>
                        <tr
                          key={k.id}
                          className={`border-b border-slate-100 dark:border-slate-700 last:border-0 transition-opacity ${
                            !k.aktiv ? 'opacity-40' : ''
                          } ${i % 2 === 0 ? '' : 'bg-slate-50/50 dark:bg-slate-900/30'}`}
                        >
                          <td className="px-4 py-2 sticky left-0 bg-white dark:bg-slate-800 z-10">
                            <div className="flex items-center gap-2">
                              {editModus && (
                                <button
                                  type="button"
                                  title={k.beschreibung ? 'Verwendungsbeispiel bearbeiten' : 'Verwendungsbeispiel hinzufügen'}
                                  onClick={() => setExpandedId(expandedId === k.id ? null : k.id)}
                                  className={`shrink-0 text-sm leading-none transition-colors ${
                                    expandedId === k.id
                                      ? 'text-sky-500 dark:text-sky-400'
                                      : k.beschreibung
                                        ? 'text-sky-400 dark:text-sky-500 hover:text-sky-600'
                                        : 'text-slate-300 dark:text-slate-600 hover:text-slate-400 dark:hover:text-slate-400'
                                  }`}
                                >
                                  💬
                                </button>
                              )}
                              <span className="text-slate-800 dark:text-slate-100">{k.name}</span>
                              {k.beschreibung && expandedId !== k.id && (
                                <InfoTooltip text={k.beschreibung} side="top" align="left" />
                              )}
                              {!k.ist_system && (
                                <span className="text-xs bg-violet-100 text-violet-600 dark:bg-violet-900 dark:text-violet-300 px-1.5 py-0.5 rounded font-medium">
                                  Eigene
                                </span>
                              )}
                              {!k.aktiv && (
                                <span className="text-xs bg-slate-100 text-slate-400 dark:bg-slate-700 dark:text-slate-500 px-1.5 py-0.5 rounded font-medium">
                                  Inaktiv
                                </span>
                              )}
                            </div>
                          </td>

                          {/* SKR03 */}
                          <td className="px-3 py-2">
                            {editModus ? (
                              <KontoCellEdit
                                key={`${k.id}-skr03-${k.konto_skr03 ?? ''}`}
                                value={k.konto_skr03}
                                defaultValue={k.konto_skr03_default}
                                isModified={k.user_modified_skr03}
                                onSave={v => kontenMutation.mutate({ id: k.id, data: { konto_skr03: v } })}
                                onReset={() => resetMutation.mutate(k.id)}
                              />
                            ) : (
                              <span className={`font-mono text-xs ${k.user_modified_skr03 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-600 dark:text-slate-300'}`}>
                                {k.konto_skr03 ?? <span className="text-slate-300 dark:text-slate-600">—</span>}
                              </span>
                            )}
                          </td>

                          {/* SKR04 */}
                          <td className="px-3 py-2">
                            {editModus ? (
                              <KontoCellEdit
                                key={`${k.id}-skr04-${k.konto_skr04 ?? ''}`}
                                value={k.konto_skr04}
                                defaultValue={k.konto_skr04_default}
                                isModified={k.user_modified_skr04}
                                onSave={v => kontenMutation.mutate({ id: k.id, data: { konto_skr04: v } })}
                                onReset={() => resetMutation.mutate(k.id)}
                              />
                            ) : (
                              <span className={`font-mono text-xs ${k.user_modified_skr04 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-600 dark:text-slate-300'}`}>
                                {k.konto_skr04 ?? <span className="text-slate-300 dark:text-slate-600">—</span>}
                              </span>
                            )}
                          </td>

                          <td className="px-3 py-2 text-slate-500 dark:text-slate-400 text-xs">
                            {editModus ? (
                              <EuerZeileEdit
                                key={`${k.id}-euer-${k.euer_zeile ?? 'null'}`}
                                value={k.euer_zeile}
                                onSave={v => kontenMutation.mutate({
                                  id: k.id,
                                  data: v != null ? { euer_zeile: v } : { euer_zeile_loeschen: true },
                                })}
                              />
                            ) : (
                              k.euer_zeile
                                ? <span>Zeile {k.euer_zeile}</span>
                                : <span className="text-slate-300 dark:text-slate-600">—</span>
                            )}
                          </td>
                          {hatEks && (
                            <td className="px-3 py-2 font-mono text-xs">
                              {k.eks_kategorie
                                ? <span className="text-slate-700 dark:text-slate-300">{k.eks_kategorie}</span>
                                : <span className="text-slate-300 dark:text-slate-600">—</span>
                              }
                            </td>
                          )}
                          <td className="px-3 py-2">
                            <UstBadge satz={k.ust_satz_standard} />
                          </td>
                          <td className="px-3 py-2 text-xs text-slate-500 dark:text-slate-400">
                            {Number(k.vorsteuer_prozent) === 100
                              ? '100 %'
                              : <span className="text-amber-600 dark:text-amber-400">{k.vorsteuer_prozent} %</span>
                            }
                          </td>
                          <td className="px-3 py-2 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              {editModus && (k.user_modified_skr03 || k.user_modified_skr04) && (
                                <button
                                  type="button"
                                  title="Kontonummern auf Standardwerte zurücksetzen"
                                  onClick={() => resetMutation.mutate(k.id)}
                                  className="text-xs px-2 py-1 rounded border border-amber-300 text-amber-600 hover:bg-amber-50 dark:border-amber-600 dark:text-amber-400 dark:hover:bg-amber-950"
                                >
                                  Reset
                                </button>
                              )}
                              {editModus && !k.ist_system && loeschenId !== k.id && (
                                <button
                                  type="button"
                                  onClick={() => setBearbeitenKat(k)}
                                  className="text-xs px-2 py-1 rounded border border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:border-blue-400 hover:text-blue-600 dark:hover:text-blue-400"
                                >
                                  Bearbeiten
                                </button>
                              )}
                              {editModus && !k.ist_system && (
                                loeschenId === k.id ? (
                                  <div className="flex items-center gap-1">
                                    <span className="text-xs text-red-500 dark:text-red-400">Löschen?</span>
                                    <button
                                      type="button"
                                      onClick={() => { deleteMutation.mutate(k.id); setLoeschenId(null) }}
                                      className="text-xs px-2 py-1 rounded border border-red-400 bg-red-50 text-red-600 hover:bg-red-100 dark:border-red-600 dark:bg-red-950 dark:text-red-400"
                                    >
                                      Ja
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => { setLoeschenId(null); setLoeschFehler(null) }}
                                      className="text-xs px-2 py-1 rounded border border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700"
                                    >
                                      Nein
                                    </button>
                                  </div>
                                ) : loeschFehler?.id === k.id ? (
                                  <div className="flex items-center gap-1.5">
                                    <span className="text-xs text-red-600 dark:text-red-400 max-w-xs">{loeschFehler.msg}</span>
                                    <button
                                      type="button"
                                      onClick={() => setLoeschFehler(null)}
                                      className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                                      title="Schließen"
                                    >✕</button>
                                  </div>
                                ) : (
                                  <button
                                    type="button"
                                    onClick={() => { setLoeschenId(k.id); setLoeschFehler(null) }}
                                    className="text-xs px-2 py-1 rounded border border-red-200 text-red-400 hover:border-red-400 hover:text-red-600 dark:border-red-800 dark:text-red-500 dark:hover:text-red-400"
                                  >
                                    Löschen
                                  </button>
                                )
                              )}
                              {!editModus && (
                                <button
                                  type="button"
                                  title={k.aktiv ? 'Deaktivieren' : 'Aktivieren'}
                                  onClick={() => toggleMutation.mutate(k.id)}
                                  className={`text-xs px-2 py-1 rounded border transition-colors ${
                                    k.aktiv
                                      ? 'border-slate-200 dark:border-slate-600 text-slate-400 hover:border-red-300 hover:text-red-500 dark:hover:text-red-400'
                                      : 'border-green-300 text-green-600 hover:bg-green-50 dark:border-green-700 dark:text-green-400 dark:hover:bg-green-950'
                                  }`}
                                >
                                  {k.aktiv ? 'Aus' : 'Ein'}
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>

                        {/* Beschreibungs-Editor (aufgeklappt) */}
                        {expandedId === k.id && (
                          <BeschreibungEditor
                            key={`desc-${k.id}`}
                            kategorie={k}
                            onSave={text => beschreibungMutation.mutate({ id: k.id, text })}
                            onClose={() => setExpandedId(null)}
                          />
                        )}
                      </>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )
        })}
      </div>

      {/* Legende */}
      {!isLoading && kategorien.length > 0 && (
        <div className="mt-8 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-5 py-4 text-xs text-slate-500 dark:text-slate-400 space-y-1">
          <p className="font-semibold text-slate-600 dark:text-slate-300 mb-2">Legende</p>
          <p><span className="font-mono">ℹ</span> – Mouseover auf das Info-Icon zeigt Verwendungsbeispiele. Im Bearbeitungsmodus: 💬-Button zum Anpassen.</p>
          <p><span className="font-mono">📄 PDF</span> – Alle Kategorien mit Beschreibungen als Nachschlageblatt exportieren (ohne Kontonummern).</p>
          <p><span className="font-mono">SKR03/04</span> – DATEV-Kontonummern (Standardkontenrahmen). Geänderte Werte erscheinen orange.</p>
          <p><span className="font-mono">EÜR-Zeile</span> – Zeile in der Einnahmen-Überschuss-Rechnung (Anlage EÜR)</p>
          <p><span className="font-mono">EKS</span> – Tabellenfeld in der Anlage EKS (Jobcenter-Einkommenserklärung)</p>
          <p><span className="font-mono">VSt %</span> – Anteil der Vorsteuer der abgezogen wird (100 % = voller Abzug)</p>
        </div>
      )}
    </div>
  )
}
