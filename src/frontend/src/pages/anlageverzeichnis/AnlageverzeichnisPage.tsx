import { useState } from 'react'
import { useAnsicht } from '../../hooks/useAnsicht'
import { useSplitterBreite } from '../../hooks/useSplitterBreite'
import { DateInput } from '../../components/DateInput'
import { ExportButtons } from '../../components/ExportButtons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getAnlagegueter, createAnlagegut, updateAnlagegut, deleteAnlagegut,
  getAfaPlan, getAveurPdfUrl, getAveurZusammenfassung, openUrl,
  type Anlagegut, type AnlagegutCreate, type AnlagegutTyp,
} from '../../api/client'

const AKTUELLES_JAHR = new Date().getFullYear()

const TYP_LABEL: Record<AnlagegutTyp, string> = {
  kfz:     'KFZ',
  edv:     'EDV / Software',
  sonstig: 'Sonstiges',
}

const ND_VORSCHLAEGE: Record<AnlagegutTyp, number> = {
  kfz: 6, edv: 3, sonstig: 5,
}

function fmt(iso: string) {
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

// Degressive AfA (§7 Abs. 2 EStG, Investitionsbooster): nur für Anschaffungen 01.07.2025–31.12.2027
function istDegressivMoeglich(kaufdatum: string): boolean {
  if (!kaufdatum) return false
  return kaufdatum >= '2025-07-01' && kaufdatum <= '2027-12-31'
}

function euro(v: number | string) {
  return parseFloat(String(v)).toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'
}

// ---------------------------------------------------------------------------
// Formular
// ---------------------------------------------------------------------------
const LEER: AnlagegutCreate = {
  bezeichnung: '', typ: 'sonstig', kaufdatum: '', kaufpreis_netto: '0',
  nutzungsdauer_jahre: 5, afa_methode: 'linear',
  kennzeichen: null, privat_anteil_prozent: '0',
  verkauft_am: null, notizen: null, aktiv: true,
}

// Nutzungsdauer waehrend der Eingabe auch leer erlauben (sonst springt das Feld beim
// Loeschen auf 1 zurueck, da parseInt("") sonst per Fallback ersetzt werden muesste – Issue #294)
type AnlagegutFormState = Omit<AnlagegutCreate, 'nutzungsdauer_jahre'> & { nutzungsdauer_jahre: number | '' }

function AnlagegutFormular({
  initial, onSave, onAbbrechen,
}: {
  initial?: Anlagegut
  onSave: (d: AnlagegutCreate) => void
  onAbbrechen: () => void
}) {
  const [form, setForm] = useState<AnlagegutFormState>(
    initial
      ? {
          bezeichnung: initial.bezeichnung,
          typ: initial.typ,
          kaufdatum: initial.kaufdatum,
          kaufpreis_netto: initial.kaufpreis_netto,
          nutzungsdauer_jahre: initial.nutzungsdauer_jahre,
          afa_methode: initial.afa_methode,
          kennzeichen: initial.kennzeichen,
          privat_anteil_prozent: initial.privat_anteil_prozent,
          verkauft_am: initial.verkauft_am,
          notizen: initial.notizen,
          aktiv: initial.aktiv,
        }
      : LEER
  )

  function set(key: keyof AnlagegutCreate, val: unknown) {
    setForm(f => {
      const next = { ...f, [key]: val }
      if (key === 'typ') {
        next.nutzungsdauer_jahre = ND_VORSCHLAEGE[val as AnlagegutTyp] ?? 5
        if (val !== 'kfz') { next.kennzeichen = null; next.privat_anteil_prozent = '0' }
      }
      if (key === 'kaufdatum' && next.afa_methode === 'degressiv' && !istDegressivMoeglich(val as string)) {
        next.afa_methode = 'linear'
      }
      return next
    })
  }

  const inputCls = 'w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100'
  const labelCls = 'block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1'

  return (
    <div className="space-y-4">
      <div>
        <label className={labelCls}>Bezeichnung *</label>
        <input className={inputCls} value={form.bezeichnung} onChange={e => set('bezeichnung', e.target.value)} placeholder="z. B. Laptop Dell XPS, Ford Transit" />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelCls}>Typ *</label>
          <select className={inputCls} value={form.typ} onChange={e => set('typ', e.target.value)}>
            <option value="sonstig">Sonstiges Anlagevermögen</option>
            <option value="edv">EDV / Software</option>
            <option value="kfz">Kraftfahrzeug (KFZ)</option>
          </select>
        </div>
        <div>
          <label className={labelCls}>Kaufdatum *</label>
          <DateInput className={inputCls} value={form.kaufdatum} onChange={(v) => set('kaufdatum', v)} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelCls}>Kaufpreis netto (€) *</label>
          <input type="number" min="0" step="0.01" className={inputCls} value={form.kaufpreis_netto} onChange={e => set('kaufpreis_netto', e.target.value)} />
        </div>
        <div>
          <label className={labelCls}>Nutzungsdauer (Jahre) *</label>
          <input type="number" min="1" max="50" className={inputCls} value={form.nutzungsdauer_jahre} onChange={e => {
            const n = parseInt(e.target.value)
            set('nutzungsdauer_jahre', Number.isNaN(n) ? '' : n)
          }} />
          <p className="text-xs text-slate-400 mt-1">AfA-Tabelle BMF: KFZ=6, PC/Laptop=3, Büromöbel=13</p>
        </div>
      </div>

      <div>
        <label className={labelCls}>AfA-Methode</label>
        <select
          className={inputCls}
          value={form.afa_methode}
          disabled={!istDegressivMoeglich(form.kaufdatum) && form.afa_methode !== 'degressiv'}
          onChange={e => set('afa_methode', e.target.value)}
        >
          <option value="linear">Linear</option>
          <option value="degressiv" disabled={!istDegressivMoeglich(form.kaufdatum)}>
            Degressiv (bis zu 30 % vom Restbuchwert)
          </option>
        </select>
        <p className="text-xs text-slate-400 mt-1">
          {istDegressivMoeglich(form.kaufdatum)
            ? 'Investitionsbooster §7 Abs. 2 EStG: wechselt automatisch zu linear, sobald das günstiger ist.'
            : 'Degressive AfA nur für Anschaffungen zwischen 01.07.2025 und 31.12.2027 (Investitionsbooster §7 Abs. 2 EStG).'}
        </p>
      </div>

      {form.typ === 'kfz' && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={labelCls}>Kennzeichen</label>
            <input className={inputCls} value={form.kennzeichen ?? ''} onChange={e => set('kennzeichen', e.target.value || null)} placeholder="z. B. M-AB 1234" />
          </div>
          <div>
            <label className={labelCls}>Privatanteil % <span className="font-normal text-slate-400">(Nettomethode)</span></label>
            <input type="number" min="0" max="100" step="1" className={inputCls} value={form.privat_anteil_prozent} onChange={e => set('privat_anteil_prozent', e.target.value)} />
            <p className="text-xs text-slate-400 mt-1">
              Kürzt die absetzbare AfA um den privaten Anteil (Nettomethode). <strong className="text-slate-500">Nicht</strong> für die 1%-Regelung – bei der 1%-Regelung bleibt dieses Feld 0, die private Nutzung wird stattdessen monatlich als Einnahme im Journal gebucht.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelCls}>Verkauft am</label>
          <DateInput className={inputCls} value={form.verkauft_am ?? ''} onChange={(v) => set('verkauft_am', v || null)} />
        </div>
        <div className="flex items-end pb-1">
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300 cursor-pointer">
            <input type="checkbox" checked={form.aktiv} onChange={e => set('aktiv', e.target.checked)} className="w-4 h-4 rounded" />
            Noch im Bestand (aktiv)
          </label>
        </div>
      </div>

      <div>
        <label className={labelCls}>Notizen</label>
        <textarea className={`${inputCls} resize-none`} rows={2} value={form.notizen ?? ''} onChange={e => set('notizen', e.target.value || null)} />
      </div>

      <div className="flex gap-3 pt-2">
        <button onClick={onAbbrechen} className="flex-1 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-lg py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-700">
          Abbrechen
        </button>
        <button
          onClick={() => {
            const nd = form.nutzungsdauer_jahre
            if (form.bezeichnung && form.kaufdatum && parseFloat(String(form.kaufpreis_netto)) > 0 && nd !== '' && nd >= 1) {
              onSave({ ...form, nutzungsdauer_jahre: nd })
            }
          }}
          disabled={!form.bezeichnung || !form.kaufdatum || parseFloat(String(form.kaufpreis_netto)) <= 0 || form.nutzungsdauer_jahre === '' || form.nutzungsdauer_jahre < 1}
          className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-40"
        >
          {initial ? 'Speichern' : 'Anlegen'}
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// AfA-Plan-Modal
// ---------------------------------------------------------------------------
function AfaPlanModal({ gut, onClose }: { gut: Anlagegut; onClose: () => void }) {
  const { data: plan = [] } = useQuery({
    queryKey: ['afa-plan', gut.id],
    queryFn: () => getAfaPlan(gut.id),
  })

  const privat = parseFloat(gut.privat_anteil_prozent)
  const vollAbgeschrieben = plan.length > 0 && plan[plan.length - 1].restbuchwert_ende === 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 w-full max-w-xl mx-4 flex flex-col max-h-[85vh]">
        <div className="flex items-center justify-between p-5 border-b border-slate-200 dark:border-slate-700">
          <div>
            <h3 className="font-semibold text-slate-800 dark:text-slate-100">{gut.bezeichnung}</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {TYP_LABEL[gut.typ]} · Kaufpreis {euro(gut.kaufpreis_netto)} · {gut.nutzungsdauer_jahre} Jahre ND
              · {gut.afa_methode === 'degressiv' ? 'Degressiv' : 'Linear'}
              {privat > 0 && ` · ${privat.toFixed(0)} % Privatanteil`}
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 text-xl">✕</button>
        </div>

        <div className="overflow-y-auto flex-1">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-700 border-b border-slate-200 dark:border-slate-600">
                <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 dark:text-slate-400">Jahr</th>
                <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 dark:text-slate-400">AfA brutto</th>
                {privat > 0 && <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 dark:text-slate-400">AfA abziehbar</th>}
                <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 dark:text-slate-400">Restwert Ende</th>
              </tr>
            </thead>
            <tbody>
              {plan.map((z, i) => (
                <tr key={z.jahr} className={`border-b border-slate-100 dark:border-slate-700 ${z.jahr === AKTUELLES_JAHR ? 'bg-blue-50 dark:bg-blue-950/30' : i % 2 === 0 ? '' : 'bg-slate-50 dark:bg-slate-800/50'}`}>
                  <td className="px-4 py-2">
                    <span className={z.jahr === AKTUELLES_JAHR ? 'font-bold text-blue-700 dark:text-blue-400' : 'text-slate-700 dark:text-slate-300'}>{z.jahr}</span>
                    {z.jahr === AKTUELLES_JAHR && <span className="ml-1.5 text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-1.5 py-0.5 rounded-full">aktuell</span>}
                    {z.wechsel_zu_linear && (
                      <span
                        className="ml-1.5 text-xs bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 px-1.5 py-0.5 rounded-full"
                        title="Ab hier ist linear günstiger als degressiv – automatischer Wechsel"
                      >
                        ↳ Wechsel zu linear
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-right text-slate-700 dark:text-slate-300">{euro(z.afa_brutto)}</td>
                  {privat > 0 && <td className="px-4 py-2 text-right font-medium text-slate-800 dark:text-slate-200">{euro(z.afa_abziehbar)}</td>}
                  <td className="px-4 py-2 text-right text-slate-500 dark:text-slate-400">{euro(z.restbuchwert_ende)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {vollAbgeschrieben && (
          <div className="px-5 py-3 bg-green-50 dark:bg-green-950/30 border-t border-green-200 dark:border-green-800 text-xs text-green-700 dark:text-green-400">
            ✓ Vollständig abgeschrieben
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Hauptseite
// ---------------------------------------------------------------------------
export function AnlageverzeichnisPage() {
  const qc = useQueryClient()
  const { einstellungen } = useAnsicht()
  const manuell = einstellungen.splitter === 'manuell'
  const [splitterBreite, startSplitterDrag] = useSplitterBreite('anlageverzeichnis', 50)
  const [jahr, setJahr] = useState(AKTUELLES_JAHR)
  const [formModus, setFormModus] = useState<'neu' | 'bearbeiten' | null>(null)
  const [selId, setSelId] = useState<number | null>(null)
  const [planGut, setPlanGut] = useState<Anlagegut | null>(null)

  const { data: gueter = [] } = useQuery({ queryKey: ['anlagegueter'], queryFn: getAnlagegueter })
  const selGut = gueter.find(g => g.id === selId)

  // AfA-Beträge kommen vom Backend (_afa_jahresplan) statt einer eigenen Neuberechnung im
  // Frontend – die frühere lokale Kopie kannte nur lineare AfA und zeigte bei degressiven
  // Wirtschaftsgütern dauerhaft den falschen (linearen) Betrag an (Issue #294).
  const { data: zusammenfassung } = useQuery({
    queryKey: ['aveur-zusammenfassung', jahr],
    queryFn: () => getAveurZusammenfassung(jahr),
  })
  const afaById = new Map((zusammenfassung?.einzel ?? []).map(e => [e.id, e.afa_abziehbar]))
  const gesamtAfa = zusammenfassung?.gesamt_afa ?? 0

  function invalidateAfa() {
    qc.invalidateQueries({ queryKey: ['anlagegueter'] })
    qc.invalidateQueries({ queryKey: ['aveur-zusammenfassung'] })
    qc.invalidateQueries({ queryKey: ['afa-plan'] })
    // AVEÜR-AfA fließt in EÜR Zeile 33 ein – sonst bleibt die EÜR-Seite auf altem Stand,
    // bis dort zufällig ein Requery ausgelöst wird (Issue #294)
    qc.invalidateQueries({ queryKey: ['euer-berechnen'] })
    qc.invalidateQueries({ queryKey: ['euer-kategorien'] })
  }

  const createMut = useMutation({ mutationFn: createAnlagegut, onSuccess: () => { invalidateAfa(); setFormModus(null) } })
  const updateMut = useMutation({ mutationFn: ({ id, data }: { id: number; data: AnlagegutCreate }) => updateAnlagegut(id, data), onSuccess: () => { invalidateAfa(); setFormModus(null) } })
  const deleteMut = useMutation({ mutationFn: deleteAnlagegut, onSuccess: () => { invalidateAfa(); setSelId(null) } })

  async function handlePdf() {
    const url = await getAveurPdfUrl(jahr)
    await openUrl(url)
  }

  const TYP_GRUPPEN: { key: AnlagegutTyp; label: string; icon: string }[] = [
    { key: 'kfz',     label: 'Kraftfahrzeuge',          icon: '🚗' },
    { key: 'edv',     label: 'EDV / Software',           icon: '💻' },
    { key: 'sonstig', label: 'Übrige Wirtschaftsgüter', icon: '🏢' },
  ]

  return (
    <div className="flex h-full overflow-hidden">
      {/* Linke Spalte */}
      <div
        className={`${formModus ? (manuell ? 'shrink-0' : 'w-1/2 min-w-[320px] shrink-0') : 'flex-1'} flex flex-col border-e border-slate-200 dark:border-slate-700 overflow-hidden`}
        style={formModus && manuell ? { width: splitterBreite, minWidth: '280px' } : undefined}
      >

        {/* Kopf */}
        <div className="shrink-0 p-4 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h1 className="text-lg font-bold text-slate-800 dark:text-slate-100">Anlagenverzeichnis</h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">Anlage AVEÜR – Abschreibungsplan</p>
            </div>
            <div className="flex gap-2 items-center">
              <select value={jahr} onChange={e => setJahr(parseInt(e.target.value))}
                className="border border-slate-300 dark:border-slate-600 rounded-lg px-2 py-1.5 text-sm dark:bg-slate-700 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500">
                {Array.from({ length: 6 }, (_, i) => AKTUELLES_JAHR - i).map(y => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
              <ExportButtons formats={['pdf']} onExport={handlePdf} />
              <button onClick={() => { setFormModus('neu'); setSelId(null) }}
                className="bg-blue-600 text-white rounded-lg px-3 py-1.5 text-sm font-medium hover:bg-blue-700">
                + Neu
              </button>
            </div>
          </div>

          {gueter.length > 0 && (
            <div className="flex items-center gap-2 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg px-3 py-2">
              <span className="text-blue-700 dark:text-blue-400 text-sm font-medium">Gesamt-AfA {jahr}</span>
              <span className="ml-auto text-blue-800 dark:text-blue-300 font-bold">{euro(gesamtAfa)}</span>
              <span className="text-xs text-blue-500 dark:text-blue-500">→ EÜR Zeile 33</span>
            </div>
          )}
        </div>

        {/* Liste nach Typ */}
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {gueter.length === 0 && (
            <div className="text-center py-16 text-slate-400 dark:text-slate-500">
              <p className="text-4xl mb-3">🏛️</p>
              <p className="text-sm font-medium mb-1">Noch keine Wirtschaftsgüter erfasst</p>
              <p className="text-xs">Füge KFZ, EDV-Anlagen oder sonstige Wirtschaftsgüter hinzu</p>
            </div>
          )}
          {TYP_GRUPPEN.map(({ key, label, icon }) => {
            const gruppe = gueter.filter(g => g.typ === key)
            if (!gruppe.length) return null
            return (
              <div key={key}>
                <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">{icon} {label}</p>
                <div className="space-y-2">
                  {gruppe.map(g => {
                    const afa = afaById.get(g.id) ?? 0
                    const abgeschrieben = afa === 0 && new Date(g.kaufdatum).getFullYear() < jahr
                    return (
                      <div key={g.id}
                        onClick={() => { setSelId(g.id); setFormModus(null) }}
                        className={`cursor-pointer rounded-xl border p-3 transition-all ${selId === g.id ? 'ring-2 ring-blue-500 border-blue-300 dark:border-blue-700' : 'border-slate-200 dark:border-slate-700'} bg-white dark:bg-slate-800 hover:border-slate-300 dark:hover:border-slate-600`}>
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="font-medium text-sm text-slate-800 dark:text-slate-100 truncate">
                              {g.bezeichnung}
                              {g.kennzeichen && <span className="ml-1.5 text-xs text-slate-400">[{g.kennzeichen}]</span>}
                            </p>
                            <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                              {fmt(g.kaufdatum)} · {euro(g.kaufpreis_netto)} · {g.nutzungsdauer_jahre} Jahre
                              {parseFloat(g.privat_anteil_prozent) > 0 && ` · ${parseFloat(g.privat_anteil_prozent).toFixed(0)} % privat`}
                            </p>
                          </div>
                          <div className="text-right shrink-0">
                            {abgeschrieben ? (
                              <span className="text-xs text-slate-400 dark:text-slate-500">abgeschr.</span>
                            ) : (
                              <>
                                <p className="text-sm font-bold text-slate-800 dark:text-slate-100">{euro(afa)}</p>
                                <p className="text-xs text-slate-400">AfA {jahr}</p>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {formModus && manuell && (
        <div
          className="w-1 shrink-0 bg-slate-200 dark:bg-slate-700 hover:bg-indigo-400 dark:hover:bg-indigo-500 cursor-col-resize transition-colors select-none"
          onMouseDown={startSplitterDrag}
        />
      )}

      {/* Rechte Spalte – Formular */}
      {formModus && (
        <div className="flex-1 overflow-y-auto p-6 border-l border-slate-200 dark:border-slate-700">
          <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100 mb-5">
            {formModus === 'neu' ? 'Wirtschaftsgut anlegen' : 'Wirtschaftsgut bearbeiten'}
          </h2>
          <AnlagegutFormular
            initial={formModus === 'bearbeiten' ? selGut : undefined}
            onSave={d => formModus === 'neu'
              ? createMut.mutate(d)
              : selGut && updateMut.mutate({ id: selGut.id, data: d })}
            onAbbrechen={() => setFormModus(null)}
          />
        </div>
      )}

      {/* Rechte Spalte – Detail */}
      {formModus === null && selGut && (
        <div className="w-[28rem] shrink-0 border-l border-slate-200 dark:border-slate-700 overflow-y-auto p-5">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="font-semibold text-slate-800 dark:text-slate-100 text-sm">{selGut.bezeichnung}</h2>
              <p className="text-xs text-slate-500 mt-0.5">{TYP_LABEL[selGut.typ]}</p>
            </div>
            <button onClick={() => setSelId(null)} className="text-slate-400 hover:text-slate-600">✕</button>
          </div>

          <div className="space-y-2 text-sm mb-5">
            {[
              ['Kaufdatum', fmt(selGut.kaufdatum)],
              ['Kaufpreis netto', euro(selGut.kaufpreis_netto)],
              ['Nutzungsdauer', `${selGut.nutzungsdauer_jahre} Jahre`],
              ['AfA-Methode', selGut.afa_methode === 'degressiv' ? 'Degressiv' : 'Linear'],
              ...(parseFloat(selGut.privat_anteil_prozent) > 0 ? [['Privatanteil', `${parseFloat(selGut.privat_anteil_prozent).toFixed(0)} %`]] : []),
              ...(selGut.kennzeichen ? [['Kennzeichen', selGut.kennzeichen]] : []),
              ...(selGut.verkauft_am ? [['Verkauft am', fmt(selGut.verkauft_am)]] : []),
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">{k}</span>
                <span className="font-medium text-slate-800 dark:text-slate-200">{v}</span>
              </div>
            ))}
          </div>

          {selGut.notizen && (
            <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3 text-xs text-slate-600 dark:text-slate-300 mb-4">
              {selGut.notizen}
            </div>
          )}

          <button
            onClick={() => setPlanGut(selGut)}
            className="w-full mb-2 border border-blue-300 dark:border-blue-700 text-blue-700 dark:text-blue-300 rounded-lg py-2 text-sm hover:bg-blue-50 dark:hover:bg-blue-950/30">
            📅 Abschreibungsplan anzeigen
          </button>
          <button onClick={() => setFormModus('bearbeiten')}
            className="w-full mb-2 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-700">
            Bearbeiten
          </button>
          <button onClick={() => { if (confirm(`„${selGut.bezeichnung}" wirklich löschen?`)) deleteMut.mutate(selGut.id) }}
            className="w-full border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400 rounded-lg py-2 text-sm hover:bg-red-50 dark:hover:bg-red-950/30">
            Löschen
          </button>
        </div>
      )}

      {planGut && <AfaPlanModal gut={planGut} onClose={() => setPlanGut(null)} />}
    </div>
  )
}
