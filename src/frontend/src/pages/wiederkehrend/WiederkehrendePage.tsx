import { useState, useEffect } from 'react'
import { useAnsicht } from '../../hooks/useAnsicht'
import { useSplitterBreite } from '../../hooks/useSplitterBreite'
import { DateInput } from '../../components/DateInput'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSearchParams, useLocation } from 'react-router-dom'
import { useNavigate } from 'react-router-dom'
import {
  getVorlagen, createVorlage, updateVorlage, deleteVorlage, beendenVorlage,
  entwurfJetzt, preiseSynchronisieren, getKunden, getUstSaetze,
  getAuftraege, getUnternehmen, uploadVertragVorlage, deleteVertragVorlage,
  getVorlageRechnungen, pruefenWiederkehrend,
  type Rechnungsvorlage, type VorlageCreate, type EntwurfErgebnis,
  type ArtikelSuche, type Rechnung,
} from '../../api/client'
import { ArtikelAutocomplete } from '../../components/ArtikelAutocomplete'

// ---------------------------------------------------------------------------
// Konstanten & Hilfsfunktionen
// ---------------------------------------------------------------------------

const INTERVALL_LABEL: Record<string, string> = {
  monatlich: 'Monatlich',
  quartalsweise: 'Quartalsweise',
  jaehrlich: 'Jährlich',
}

const INTERVALL_ICON: Record<string, string> = {
  monatlich: '📅',
  quartalsweise: '📆',
  jaehrlich: '🗓️',
}

const inputCls = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100 dark:placeholder-slate-400"
const selectCls = `${inputCls} bg-white dark:bg-slate-700`

type EingabeModus = 'netto' | 'brutto'

function fmt(iso: string) {
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

function heuteIso() {
  return new Date().toISOString().slice(0, 10)
}

// ---------------------------------------------------------------------------
// Positions-Typen & Berechnungen
// ---------------------------------------------------------------------------

interface PositionEntwurf {
  beschreibung: string
  menge: string
  einheit: string
  einzelpreis: string
  ust_satz: string
  artikel_id: number | null
}

function leerPosition(defaultSatz = '19'): PositionEntwurf {
  return { beschreibung: '', menge: '1', einheit: 'Stk.', einzelpreis: '', ust_satz: defaultSatz, artikel_id: null }
}

function nettoProStueck(pos: PositionEntwurf, modus: EingabeModus): number {
  const ep = parseFloat(pos.einzelpreis.replace(',', '.')) || 0
  const ust = parseFloat(pos.ust_satz) || 0
  return modus === 'brutto' ? ep / (1 + ust / 100) : ep
}

function stepFuerEinheit(einheit: string | undefined | null): number {
  const e = (einheit ?? '').trim().toLowerCase()
  return /^(kg|g|mg|t|l|ml|dl|cl|m[²³]|m|cm|mm)$/.test(e) ? 0.001 : 1
}

function adjustMenge(current: string, step: number): string {
  const n = parseFloat(current.replace(',', '.')) || 0
  const r = Math.max(0, Math.round((n + step) * 1000) / 1000)
  return r % 1 === 0 ? String(r) : String(r).replace('.', ',')
}

function berechneGesamt(positionen: PositionEntwurf[], modus: EingabeModus) {
  return positionen.reduce((acc, p) => {
    const menge = parseFloat(p.menge) || 0
    const netto = nettoProStueck(p, modus) * menge
    const ust = (netto * (parseFloat(p.ust_satz) || 0)) / 100
    return { netto: acc.netto + netto, ust: acc.ust + ust, brutto: acc.brutto + netto + ust }
  }, { netto: 0, ust: 0, brutto: 0 })
}

// ---------------------------------------------------------------------------
// Positionen-Tabelle
// ---------------------------------------------------------------------------

function PositionenTabelle({
  positionen, onChange, ustSaetze, onArtikelWahl, eingabeModus,
}: {
  positionen: PositionEntwurf[]
  onChange: (p: PositionEntwurf[]) => void
  ustSaetze: { satz: string }[]
  onArtikelWahl: (i: number, a: ArtikelSuche) => void
  eingabeModus: EingabeModus
}) {
  function update(i: number, field: keyof PositionEntwurf, val: string | number | null) {
    onChange(positionen.map((p, idx) => idx === i ? { ...p, [field]: val } : p))
  }

  const gesamt = berechneGesamt(positionen, eingabeModus)
  const cellInput = "w-full border-0 outline-none bg-transparent text-slate-700 dark:text-slate-200 text-xs"

  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
      <table className="w-full text-xs">
        <thead className="bg-slate-50 dark:bg-slate-900">
          <tr>
            <th className="px-3 py-2 text-left text-slate-500 dark:text-slate-400 font-medium">Beschreibung</th>
            <th className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 font-medium w-16">Menge</th>
            <th className="px-3 py-2 text-left text-slate-500 dark:text-slate-400 font-medium w-20">Einheit</th>
            <th className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 font-medium w-24">
              {eingabeModus === 'netto' ? 'Netto (€)' : 'Brutto (€)'}
            </th>
            <th className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 font-medium w-16">USt %</th>
            <th className="px-3 py-2 w-8" />
          </tr>
        </thead>
        <tbody>
          {positionen.map((pos, i) => (
            <tr key={i} className="border-t border-slate-100 dark:border-slate-700">
              <td className="px-2 py-1.5">
                <ArtikelAutocomplete
                  value={pos.beschreibung}
                  onChange={v => update(i, 'beschreibung', v)}
                  onArtikelWahl={a => onArtikelWahl(i, a)}
                  placeholder="Beschreibung oder Artikel suchen"
                  inputClassName="w-full border-0 outline-none bg-transparent text-slate-700 dark:text-slate-200 text-xs placeholder-slate-400 dark:placeholder-slate-500"
                />
              </td>
              <td className="px-2 py-1.5">
                <div className="flex items-center gap-0.5 justify-end">
                  <button type="button" tabIndex={-1}
                    onClick={() => update(i, 'menge', adjustMenge(pos.menge, -stepFuerEinheit(pos.einheit)))}
                    className="text-slate-300 hover:text-blue-500 dark:text-slate-600 dark:hover:text-blue-400 leading-none shrink-0 text-base">−</button>
                  <input value={pos.menge} onChange={e => update(i, 'menge', e.target.value)}
                    type="text" className="w-8 border-0 outline-none bg-transparent text-center text-slate-700 dark:text-slate-200 text-xs" />
                  <button type="button" tabIndex={-1}
                    onClick={() => update(i, 'menge', adjustMenge(pos.menge, +stepFuerEinheit(pos.einheit)))}
                    className="text-slate-300 hover:text-blue-500 dark:text-slate-600 dark:hover:text-blue-400 leading-none shrink-0 text-base">+</button>
                </div>
              </td>
              <td className="px-2 py-1.5">
                <input value={pos.einheit} onChange={e => update(i, 'einheit', e.target.value)}
                  placeholder="Stk." className={cellInput} />
              </td>
              <td className="px-2 py-1.5">
                <input value={pos.einzelpreis} onChange={e => { update(i, 'einzelpreis', e.target.value); update(i, 'artikel_id', null) }}
                  type="text" placeholder="0,00" className={`${cellInput} text-right`} />
              </td>
              <td className="px-2 py-1.5">
                <select value={pos.ust_satz} onChange={e => update(i, 'ust_satz', e.target.value)}
                  className={`${cellInput} text-right`}>
                  {ustSaetze.map(u => (
                    <option key={u.satz} value={u.satz}>{u.satz} %</option>
                  ))}
                </select>
              </td>
              <td className="px-2 py-1.5 text-center">
                {positionen.length > 1 && (
                  <button type="button" onClick={() => onChange(positionen.filter((_, idx) => idx !== i))}
                    className="text-slate-300 hover:text-red-500 text-base leading-none">×</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot className="bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-700">
          <tr>
            <td colSpan={3} className="px-3 py-2 text-right text-slate-500 dark:text-slate-400">
              Netto{eingabeModus === 'brutto' && <span className="text-slate-400 dark:text-slate-500"> (berechnet)</span>}
            </td>
            <td colSpan={3} className="px-3 py-2 text-right font-medium text-slate-700 dark:text-slate-200">
              {gesamt.netto.toFixed(2).replace('.', ',')} €
            </td>
          </tr>
          <tr className="border-t border-slate-100 dark:border-slate-700">
            <td colSpan={3} className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 text-xs">USt</td>
            <td colSpan={3} className="px-3 py-2 text-right text-slate-600 dark:text-slate-300">
              {gesamt.ust.toFixed(2).replace('.', ',')} €
            </td>
          </tr>
          <tr className="border-t border-slate-100 dark:border-slate-700">
            <td colSpan={3} className="px-3 py-2 text-right font-semibold text-slate-700 dark:text-slate-200">Brutto</td>
            <td colSpan={3} className="px-3 py-2 text-right font-semibold text-slate-800 dark:text-slate-100">
              {gesamt.brutto.toFixed(2).replace('.', ',')} €
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Formular
// ---------------------------------------------------------------------------

function VorlageFormular({
  initial,
  isSaving,
  onSpeichern,
  onAbbrechen,
  auftraegeAktiv = false,
  auftraege = [],
  defaultAuftragId,
  defaultAuftrag,
  onVertragUpload,
  onVertragDelete,
  isVertragUploading = false,
}: {
  initial?: Rechnungsvorlage
  isSaving: boolean
  onSpeichern: (data: VorlageCreate) => void
  onAbbrechen: () => void
  auftraegeAktiv?: boolean
  auftraege?: Rechnung[]
  defaultAuftragId?: number
  defaultAuftrag?: Rechnung
  onVertragUpload?: (file: File) => void
  onVertragDelete?: () => void
  isVertragUploading?: boolean
}) {
  const { data: kunden } = useQuery({ queryKey: ['kunden'], queryFn: getKunden })
  const { data: ustSaetze } = useQuery({ queryKey: ['ust-saetze'], queryFn: getUstSaetze })

  const ustSaetzeListe = ustSaetze?.filter(u => u.ist_aktiv) ?? []
  const defaultSatz = ustSaetze?.find(u => u.ist_default)?.satz
    ?? ustSaetze?.find(u => parseFloat(u.satz) === 19)?.satz
    ?? '19'

  const [bezeichnung, setBezeichnung] = useState(() => {
    if (initial?.bezeichnung) return initial.bezeichnung
    if (defaultAuftrag) return `${defaultAuftrag.rechnungsnummer ?? ''} – Wiederkehrend`.trimStart()
    return ''
  })
  const [intervall, setIntervall] = useState(initial?.intervall ?? 'monatlich')
  const [naechstesDatum, setNaechstesDatum] = useState(initial?.naechstes_datum ?? heuteIso())
  const [aktiv, setAktiv] = useState(initial?.aktiv ?? true)
  const [kundeId, setKundeId] = useState(() => {
    if (initial?.kunde_id) return String(initial.kunde_id)
    if (defaultAuftrag?.kunde_id) return String(defaultAuftrag.kunde_id)
    return ''
  })
  const [zahlungsziel, setZahlungsziel] = useState(initial?.zahlungsziel_tage ? String(initial.zahlungsziel_tage) : '')
  const [notizen, setNotizen] = useState(initial?.notizen ?? '')
  const [auftragId, setAuftragId] = useState(() => {
    if (initial?.auftrag_id) return String(initial.auftrag_id)
    if (defaultAuftragId) return String(defaultAuftragId)
    if (defaultAuftrag?.id) return String(defaultAuftrag.id)
    return ''
  })
  const [eingabeModus, setEingabeModus] = useState<EingabeModus>('netto')
  const [fehler, setFehler] = useState<string | null>(null)

  const [positionen, setPositionen] = useState<PositionEntwurf[]>(() => {
    if (initial?.positionen?.length) {
      return initial.positionen.map(p => ({
        beschreibung: p.beschreibung,
        menge: String(p.menge),
        einheit: p.einheit,
        einzelpreis: String(p.netto),
        ust_satz: String(p.ust_satz),
        artikel_id: p.artikel_id ?? null,
      }))
    }
    if (defaultAuftrag?.positionen?.length) {
      return defaultAuftrag.positionen.map(p => ({
        beschreibung: p.beschreibung,
        menge: String(p.menge),
        einheit: p.einheit,
        einzelpreis: String(p.netto),
        ust_satz: String(p.ust_satz),
        artikel_id: p.artikel_id ?? null,
      }))
    }
    return [leerPosition()]
  })

  // Gewerbekunde → Netto, Privatkunde → Brutto
  useEffect(() => {
    if (!kundeId || !kunden) return
    const k = kunden.find(k => String(k.id) === kundeId)
    if (k) setEingabeModus(k.firmenname?.trim() ? 'netto' : 'brutto')
  }, [kundeId, kunden])

  // Default-USt setzen sobald Sätze geladen sind
  useEffect(() => {
    if (!ustSaetze?.length || initial) return
    setPositionen(prev => prev.map(p =>
      p.einzelpreis === '' ? { ...p, ust_satz: defaultSatz } : p
    ))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ustSaetze])

  function fillPositionFromArtikel(i: number, a: ArtikelSuche) {
    const ust_satz = ustSaetze?.find(u => parseFloat(u.satz) === parseFloat(a.steuersatz))?.satz ?? a.steuersatz
    const preis = eingabeModus === 'netto'
      ? parseFloat(a.vk_netto).toFixed(2)
      : parseFloat(a.vk_brutto).toFixed(2)
    setPositionen(prev => prev.map((p, idx) =>
      idx !== i ? p : { ...p, beschreibung: a.bezeichnung, einheit: a.einheit, einzelpreis: preis, ust_satz, artikel_id: a.id }
    ))
  }

  function handleSpeichern() {
    if (!bezeichnung.trim()) { setFehler('Bezeichnung ist erforderlich.'); return }
    if (!naechstesDatum) { setFehler('Datum ist erforderlich.'); return }
    setFehler(null)

    onSpeichern({
      bezeichnung: bezeichnung.trim(),
      intervall: intervall as VorlageCreate['intervall'],
      naechstes_datum: naechstesDatum,
      aktiv,
      kunde_id: kundeId ? parseInt(kundeId) : null,
      auftrag_id: auftragId ? parseInt(auftragId) : null,
      zahlungsziel_tage: zahlungsziel ? parseInt(zahlungsziel) : null,
      notizen: notizen.trim() || null,
      positionen: positionen
        .filter(p => p.beschreibung.trim())
        .map(p => ({
          beschreibung: p.beschreibung.trim(),
          menge: String(parseFloat(p.menge) || 1),
          einheit: p.einheit || 'Stk.',
          netto: String(nettoProStueck(p, eingabeModus)),
          ust_satz: String(parseFloat(p.ust_satz) || 0),
          artikel_id: p.artikel_id ?? null,
          kategorie_id: null,
        })),
    })
  }

  return (
    <form onSubmit={e => e.preventDefault()} className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Bezeichnung *</label>
        <input
          value={bezeichnung}
          onChange={e => setBezeichnung(e.target.value)}
          placeholder="z. B. Webhosting Muster GmbH"
          className={inputCls}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Intervall *</label>
          <select value={intervall} onChange={e => setIntervall(e.target.value as 'monatlich' | 'quartalsweise' | 'jaehrlich')} className={selectCls}>
            <option value="monatlich">Monatlich</option>
            <option value="quartalsweise">Quartalsweise</option>
            <option value="jaehrlich">Jährlich</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Erster / nächster Entwurf *</label>
          <DateInput
            value={naechstesDatum}
            onChange={setNaechstesDatum}
            className={inputCls}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Kunde</label>
          <select value={kundeId} onChange={e => setKundeId(e.target.value)} className={selectCls}>
            <option value="">— Kein Kunde —</option>
            {kunden?.map(k => (
              <option key={k.id} value={k.id}>
                {k.firmenname || [k.vorname, k.nachname].filter(Boolean).join(' ')}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Zahlungsziel (Tage)</label>
          <input
            type="number"
            value={zahlungsziel}
            onChange={e => setZahlungsziel(e.target.value)}
            placeholder="Unternehmens-Standard"
            className={inputCls}
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Notizen</label>
        <textarea
          value={notizen}
          onChange={e => setNotizen(e.target.value)}
          rows={2}
          className={`${inputCls} resize-none`}
          placeholder="Erscheint als Fußtext auf der Rechnung"
        />
      </div>

      {auftraegeAktiv && (
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Auftrag verknüpfen</label>
          <select value={auftragId} onChange={e => setAuftragId(e.target.value)} className={selectCls}>
            <option value="">— Kein Auftrag —</option>
            {auftraege.map(a => (
              <option key={a.id} value={a.id}>
                {a.rechnungsnummer} · {a.kunde_name ?? ''}
              </option>
            ))}
          </select>
          {auftragId && (
            <p className="text-xs text-teal-600 dark:text-teal-400 mt-1">
              Der Auftrag wird auf „Laufend" gesetzt, solange diese Vorlage aktiv ist.
            </p>
          )}
        </div>
      )}

      {initial && (
        <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
            Vertragsdokument (PDF)
          </label>
          {initial.beleg_name ? (
            <div className="flex items-center gap-2 bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2">
              <span className="text-slate-400 dark:text-slate-500 text-lg">📄</span>
              <span className="text-sm text-slate-700 dark:text-slate-200 flex-1 truncate">{initial.beleg_name}</span>
              <button type="button" onClick={onVertragDelete}
                disabled={isVertragUploading}
                className="text-xs text-red-500 hover:text-red-700 dark:text-red-400 disabled:opacity-50 shrink-0">
                Entfernen
              </button>
            </div>
          ) : (
            <label className={`flex items-center gap-3 cursor-pointer rounded-lg border border-dashed border-slate-300 dark:border-slate-600 px-4 py-3 hover:border-blue-400 dark:hover:border-blue-600 transition-colors${isVertragUploading ? ' opacity-50 pointer-events-none' : ''}`}>
              <span className="text-2xl">📎</span>
              <div>
                <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
                  {isVertragUploading ? 'Wird hochgeladen…' : 'Vertragsdokument hochladen'}
                </p>
                <p className="text-xs text-slate-400 dark:text-slate-500">PDF, JPG, PNG – max. 20 MB</p>
              </div>
              <input
                type="file"
                accept=".pdf,image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={e => { const f = e.target.files?.[0]; if (f) onVertragUpload?.(f) }}
              />
            </label>
          )}
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Positionen</label>
          <div className="flex items-center gap-3">
            <button type="button"
              onClick={() => setEingabeModus(eingabeModus === 'netto' ? 'brutto' : 'netto')}
              className="text-xs text-blue-600 hover:text-blue-700 underline">
              {eingabeModus === 'netto' ? 'Brutto eingeben' : 'Netto eingeben'}
            </button>
            <button type="button"
              onClick={() => setPositionen(prev => [...prev, leerPosition(defaultSatz)])}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium">
              + Position hinzufügen
            </button>
          </div>
        </div>
        <PositionenTabelle
          positionen={positionen}
          onChange={setPositionen}
          ustSaetze={ustSaetzeListe}
          onArtikelWahl={fillPositionFromArtikel}
          eingabeModus={eingabeModus}
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="vorlage-aktiv"
          checked={aktiv}
          onChange={e => setAktiv(e.target.checked)}
          className="h-4 w-4 rounded border-slate-300 text-blue-600"
        />
        <label htmlFor="vorlage-aktiv" className="text-sm text-slate-700 dark:text-slate-200 cursor-pointer">
          Vorlage aktiv (automatisch Entwürfe erstellen)
        </label>
      </div>

      {fehler && <p className="text-sm text-red-600">{fehler}</p>}

      <div className="flex gap-2">
        <button type="button" onClick={onAbbrechen}
          className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 dark:text-slate-300 transition-colors">
          Abbrechen
        </button>
        <button type="button" onClick={handleSpeichern} disabled={isSaving}
          className="flex-1 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors">
          {isSaving ? 'Speichern…' : initial ? '✓ Speichern' : '✓ Vorlage erstellen'}
        </button>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Vorlage-Karte
// ---------------------------------------------------------------------------

function VorlageKarte({
  vorlage, onEntwurfJetzt, onPreisSync,
}: {
  vorlage: Rechnungsvorlage
  onEntwurfJetzt: () => void
  onPreisSync: () => void
}) {
  const brutto = vorlage.positionen.reduce((s, p) => {
    const n = parseFloat(p.netto || '0')
    const u = parseFloat(p.ust_satz || '0')
    return s + parseFloat(p.menge || '1') * n * (1 + u / 100)
  }, 0)

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-xl border ${vorlage.aktiv ? 'border-slate-200 dark:border-slate-700' : 'border-slate-100 dark:border-slate-800 opacity-60'} p-5 space-y-3`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-lg">{INTERVALL_ICON[vorlage.intervall] ?? '📄'}</span>
          <div className="min-w-0">
            <h3 className="font-semibold text-slate-800 dark:text-slate-100 truncate">{vorlage.bezeichnung}</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {INTERVALL_LABEL[vorlage.intervall]} · {vorlage.kunde_name ?? 'Kein Kunde'}
            </p>
          </div>
        </div>
        {vorlage.beendet && (
          <span className="shrink-0 text-xs bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 px-2 py-0.5 rounded-full">Beendet</span>
        )}
        {!vorlage.aktiv && !vorlage.beendet && (
          <span className="shrink-0 text-xs bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 px-2 py-0.5 rounded-full">Pausiert</span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3 text-sm">
        <div>
          <p className="text-xs text-slate-400 dark:text-slate-500 mb-0.5">Nächster Entwurf</p>
          <p className="font-medium text-slate-700 dark:text-slate-200">{fmt(vorlage.naechstes_datum)}</p>
        </div>
        <div>
          <p className="text-xs text-slate-400 dark:text-slate-500 mb-0.5">Betrag (ca. brutto)</p>
          <p className="font-medium text-slate-700 dark:text-slate-200">
            {brutto.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-400 dark:text-slate-500 mb-0.5">Erstellt</p>
          <p className="font-medium text-slate-700 dark:text-slate-200">
            {vorlage.erstellte_rechnungen}× {vorlage.letzte_erstellung ? `· ${fmt(vorlage.letzte_erstellung)}` : ''}
          </p>
        </div>
      </div>

      {(vorlage.auftrag_nr || vorlage.beleg_name) && (
        <div className="flex flex-wrap gap-2">
          {vorlage.auftrag_nr && (
            <span className="inline-flex items-center gap-1 text-xs bg-teal-50 dark:bg-teal-950 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-700 rounded-full px-2 py-0.5">
              📋 {vorlage.auftrag_nr}
            </span>
          )}
          {vorlage.beleg_name && (
            <span className="inline-flex items-center gap-1 text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-full px-2 py-0.5">
              📄 Vertrag hinterlegt
            </span>
          )}
        </div>
      )}

      {vorlage.positionen.length > 0 && (
        <div className="border-t border-slate-100 dark:border-slate-700 pt-2">
          {vorlage.positionen.slice(0, 3).map((p, i) => (
            <div key={i} className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 py-0.5">
              <span className="truncate">{p.beschreibung}</span>
              <span className="shrink-0 ml-2">
                {parseFloat(p.netto || '0').toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €
              </span>
            </div>
          ))}
          {vorlage.positionen.length > 3 && (
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">+{vorlage.positionen.length - 3} weitere…</p>
          )}
        </div>
      )}

      <div className="flex gap-2 pt-1">
        <button onClick={e => { e.stopPropagation(); onEntwurfJetzt() }}
          disabled={vorlage.beendet}
          className="flex-1 px-3 py-1.5 text-xs font-medium bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
          RE-Entwurf jetzt erstellen
        </button>
        <button onClick={e => { e.stopPropagation(); onPreisSync() }} title="Artikel-Preise auf aktuellen Stand bringen"
          className="px-3 py-1.5 text-xs font-medium bg-slate-50 dark:bg-slate-700 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-600 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors">
          Preise sync
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Detail-Panel – generierte Rechnungen
// ---------------------------------------------------------------------------

const ZS_LABEL: Record<string, { label: string; cls: string }> = {
  offen:      { label: 'Offen',      cls: 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300 border-blue-200 dark:border-blue-700' },
  bezahlt:    { label: 'Bezahlt',    cls: 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300 border-green-200 dark:border-green-700' },
  teilbezahlt:{ label: 'Teilbezahlt',cls: 'bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300 border-amber-200 dark:border-amber-700' },
  ueberfaellig:{ label: 'Überfällig',cls: 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300 border-red-200 dark:border-red-700' },
}

function VorlageDetail({
  vorlage,
  onClose,
  onBearbeiten,
  onBeenden,
  onLoeschen,
}: {
  vorlage: Rechnungsvorlage
  onClose: () => void
  onBearbeiten: () => void
  onBeenden: () => void
  onLoeschen: () => void
}) {
  const navigate = useNavigate()
  const { data: rechnungen = [], isLoading } = useQuery({
    queryKey: ['vorlage-rechnungen', vorlage.id],
    queryFn: () => getVorlageRechnungen(vorlage.id),
  })

  const gesamt = rechnungen.reduce((s, r) => s + parseFloat(r.brutto_gesamt || '0'), 0)
  const kannLoeschen = (vorlage.erstellte_rechnungen === 0) && !vorlage.auftrag_id && !vorlage.beleg_id

  return (
    <div className="flex flex-col h-full">
      <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between shrink-0">
        <div>
          <p className="font-semibold text-slate-800 dark:text-slate-100 truncate max-w-[200px]">{vorlage.bezeichnung}</p>
          <p className="text-xs text-slate-400 dark:text-slate-500">{INTERVALL_LABEL[vorlage.intervall]} · {vorlage.kunde_name ?? 'Kein Kunde'}</p>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-xl shrink-0">×</button>
      </div>

      <div className="p-5 space-y-4 flex-1 overflow-y-auto">
        {/* Schnellaktionen */}
        <div className="flex gap-2 flex-wrap">
          {!vorlage.beendet && (
            <button onClick={onBearbeiten}
              className="px-3 py-1.5 text-xs border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 transition-colors">
              ✏️ Bearbeiten
            </button>
          )}
          {!vorlage.beendet && (
            <button onClick={onBeenden}
              className="px-3 py-1.5 text-xs border border-amber-300 dark:border-amber-700 rounded-lg hover:bg-amber-50 dark:hover:bg-amber-900/20 text-amber-700 dark:text-amber-400 transition-colors">
              ⏹ Beenden
            </button>
          )}
          {kannLoeschen && (
            <button onClick={onLoeschen}
              className="px-3 py-1.5 text-xs border border-red-200 dark:border-red-800 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500 dark:text-red-400 transition-colors">
              Löschen
            </button>
          )}
        </div>

        {/* Statistik */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-slate-50 dark:bg-slate-900 rounded-xl p-3">
            <p className="text-xs text-slate-400 dark:text-slate-500 mb-0.5">Erstellt</p>
            <p className="text-lg font-bold text-slate-800 dark:text-slate-100">{vorlage.erstellte_rechnungen}×</p>
          </div>
          <div className="bg-slate-50 dark:bg-slate-900 rounded-xl p-3">
            <p className="text-xs text-slate-400 dark:text-slate-500 mb-0.5">Gesamtumsatz</p>
            <p className="text-lg font-bold text-slate-800 dark:text-slate-100">
              {gesamt.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €
            </p>
          </div>
        </div>

        {/* Rechnungsliste */}
        <div>
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
            Generierte Rechnungen
          </p>
          {isLoading && <p className="text-sm text-slate-400 dark:text-slate-500 py-4 text-center">Lade…</p>}
          {!isLoading && rechnungen.length === 0 && (
            <p className="text-sm text-slate-400 dark:text-slate-500 py-4 text-center">
              Noch keine Rechnungen erstellt.
            </p>
          )}
          {rechnungen.length > 0 && (
            <div className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
              <table className="w-full text-xs">
                <thead className="bg-slate-50 dark:bg-slate-900">
                  <tr>
                    <th className="px-3 py-2 text-left text-slate-500 dark:text-slate-400 font-medium">Datum</th>
                    <th className="px-3 py-2 text-left text-slate-500 dark:text-slate-400 font-medium">Nummer</th>
                    <th className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 font-medium">Brutto</th>
                    <th className="px-3 py-2 text-center text-slate-500 dark:text-slate-400 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rechnungen.map(r => {
                    const zs = ZS_LABEL[r.zahlungsstatus ?? 'offen'] ?? ZS_LABEL.offen
                    return (
                      <tr key={r.id}
                        onClick={() => navigate(`/rechnungen?id=${r.id}`)}
                        className="border-t border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 cursor-pointer transition-colors">
                        <td className="px-3 py-2 text-slate-500 dark:text-slate-400">{fmt(r.datum)}</td>
                        <td className="px-3 py-2 font-mono text-slate-600 dark:text-slate-300">{r.rechnungsnummer ?? '—'}</td>
                        <td className="px-3 py-2 text-right font-medium text-slate-700 dark:text-slate-200">
                          {parseFloat(r.brutto_gesamt || '0').toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €
                        </td>
                        <td className="px-3 py-2 text-center">
                          {r.ist_entwurf
                            ? <span className="inline-block text-xs font-medium px-1.5 py-0.5 rounded border bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800">Entwurf</span>
                            : <span className={`inline-block text-xs font-medium px-1.5 py-0.5 rounded border ${zs.cls}`}>{zs.label}</span>
                          }
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Hauptseite
// ---------------------------------------------------------------------------

export function WiederkehrendePage() {
  const qc = useQueryClient()
  const { einstellungen } = useAnsicht()
  const manuell = einstellungen.splitter === 'manuell'
  const [splitterBreite, startSplitterDrag] = useSplitterBreite('wiederkehrend', 33)
  const [searchParams, setSearchParams] = useSearchParams()
  const location = useLocation()
  const [formModus, setFormModus] = useState<'neu' | number | null>(null)
  const [selId, setSelId] = useState<number | null>(null)
  const [defaultAuftragId, setDefaultAuftragId] = useState<number | undefined>()
  const [defaultAuftrag, setDefaultAuftrag] = useState<Rechnung | undefined>()
  const [letzterEntwurf, setLetzterEntwurf] = useState<EntwurfErgebnis | null>(null)
  const [suche, setSuche] = useState('')
  const [intervallFilter, setIntervallFilter] = useState('')
  const [aktivFilter, setAktivFilter] = useState('')

  // Navigation von AuftraegePage: Auftrag-Daten vorausfüllen
  useEffect(() => {
    const stateAuftrag = (location.state as any)?.auftrag as Rechnung | undefined
    if (stateAuftrag) {
      setDefaultAuftrag(stateAuftrag)
      setDefaultAuftragId(stateAuftrag.id)
      setFormModus('neu')
      return
    }
    // Fallback: ?auftrag_id=X per URL-Param
    const aid = searchParams.get('auftrag_id')
    if (aid) {
      const id = parseInt(aid, 10)
      if (!isNaN(id)) { setDefaultAuftragId(id); setFormModus('neu') }
      setSearchParams({}, { replace: true })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const { data: vorlagen = [], isLoading } = useQuery({
    queryKey: ['wiederkehrend'],
    queryFn: getVorlagen,
  })

  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen })
  const { data: auftraege = [] } = useQuery({
    queryKey: ['auftraege'],
    queryFn: getAuftraege,
    enabled: !!unternehmen?.auftraege_aktiv,
  })

  const vorlagenGefiltert = vorlagen.filter(v => {
    if (intervallFilter && v.intervall !== intervallFilter) return false
    if (aktivFilter === 'aktiv' && (!v.aktiv || v.beendet)) return false
    if (aktivFilter === 'pausiert' && (v.aktiv || v.beendet)) return false
    if (aktivFilter === 'beendet' && !v.beendet) return false
    if (aktivFilter === '' && v.beendet) return false  // beendet standardmäßig ausblenden
    if (suche) {
      const q = suche.toLowerCase()
      return v.bezeichnung.toLowerCase().includes(q) || (v.kunde_name ?? '').toLowerCase().includes(q)
    }
    return true
  })

  const createMut = useMutation({
    mutationFn: createVorlage,
    onSuccess: (vorlage) => {
      qc.invalidateQueries({ queryKey: ['wiederkehrend'] })
      setFormModus(null)
      // Sofort prüfen ob ein Entwurf fällig ist (naechstes_datum <= heute)
      if (vorlage.aktiv) {
        pruefenWiederkehrend().then(ergebnisse => {
          if (ergebnisse.length > 0) {
            setLetzterEntwurf(ergebnisse[ergebnisse.length - 1])
            qc.invalidateQueries({ queryKey: ['wiederkehrend'] })
            qc.invalidateQueries({ queryKey: ['rechnungen'] })
          }
        }).catch(() => {})
      }
    },
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: VorlageCreate }) => updateVorlage(id, data),
    onSuccess: (vorlage) => {
      qc.invalidateQueries({ queryKey: ['wiederkehrend'] })
      setFormModus(null)
      if (vorlage.aktiv) {
        pruefenWiederkehrend().then(ergebnisse => {
          if (ergebnisse.length > 0) {
            setLetzterEntwurf(ergebnisse[ergebnisse.length - 1])
            qc.invalidateQueries({ queryKey: ['wiederkehrend'] })
            qc.invalidateQueries({ queryKey: ['rechnungen'] })
          }
        }).catch(() => {})
      }
    },
  })

  const deleteMut = useMutation({
    mutationFn: deleteVorlage,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['wiederkehrend'] }); setSelId(null) },
  })

  const beendenMut = useMutation({
    mutationFn: beendenVorlage,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['wiederkehrend'] })
      qc.invalidateQueries({ queryKey: ['auftraege'] })
      setSelId(null)
    },
  })

  const entwurfMut = useMutation({
    mutationFn: entwurfJetzt,
    onSuccess: (ergebnis) => {
      qc.invalidateQueries({ queryKey: ['wiederkehrend'] })
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
      setLetzterEntwurf(ergebnis)
    },
  })

  const syncMut = useMutation({
    mutationFn: preiseSynchronisieren,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['wiederkehrend'] }),
  })

  const vertragUploadMut = useMutation({
    mutationFn: ({ id, datei }: { id: number; datei: File }) => uploadVertragVorlage(id, datei),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['wiederkehrend'] })
      qc.invalidateQueries({ queryKey: ['auftraege'] })
    },
  })

  const vertragDeleteMut = useMutation({
    mutationFn: (id: number) => deleteVertragVorlage(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['wiederkehrend'] }),
  })

  function handleSave(data: VorlageCreate) {
    if (formModus === 'neu') createMut.mutate(data)
    else if (typeof formModus === 'number') updateMut.mutate({ id: formModus, data })
  }

  function handleLoeschen(id: number, bezeichnung: string) {
    if (confirm(`Vorlage „${bezeichnung}" wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.`))
      deleteMut.mutate(id)
  }

  function handleBeenden(id: number, bezeichnung: string) {
    if (confirm(`Vorlage „${bezeichnung}" dauerhaft beenden? Sie wird nicht mehr automatisch ausgeführt. Alle bisherigen Rechnungen bleiben erhalten.`))
      beendenMut.mutate(id)
  }

  const editVorlage = typeof formModus === 'number' ? vorlagen.find(v => v.id === formModus) : undefined

  const selVorlage = selId != null ? vorlagen.find(v => v.id === selId) ?? null : null

  return (
    <div className="flex h-full">

      {/* Linke Seite – Liste (schrumpft wenn rechts etwas geöffnet ist) */}
      <div
        className={`${formModus !== null ? (manuell ? 'shrink-0' : 'w-1/3 min-w-[280px] shrink-0') : selVorlage ? 'flex-1' : 'flex-1'} flex flex-col border-e border-slate-200 dark:border-slate-700 min-w-0 overflow-hidden`}
        style={formModus !== null && manuell ? { width: splitterBreite, minWidth: '220px' } : undefined}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 shrink-0">
          <div className="flex items-center justify-between gap-3 mb-3">
            <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Wiederkehrende Rechnungen</h1>
            <button
              onClick={() => { setFormModus('neu'); setSelId(null) }}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors shrink-0">
              + Neue Vorlage
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            <input type="search" data-search-input placeholder="Bezeichnung oder Kunde suchen…"
              value={suche} onChange={e => setSuche(e.target.value)}
              className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 flex-1 min-w-[140px]"
            />
            <select value={intervallFilter} onChange={e => setIntervallFilter(e.target.value)}
              className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 bg-white dark:bg-slate-700">
              <option value="">Alle Intervalle</option>
              <option value="monatlich">Monatlich</option>
              <option value="quartalsweise">Quartalsweise</option>
              <option value="jaehrlich">Jährlich</option>
            </select>
            <select value={aktivFilter} onChange={e => setAktivFilter(e.target.value)}
              className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 bg-white dark:bg-slate-700">
              <option value="">Aktiv &amp; Pausiert</option>
              <option value="aktiv">Nur aktive</option>
              <option value="pausiert">Nur pausierte</option>
              <option value="beendet">Beendete</option>
            </select>
          </div>
        </div>

        {/* Liste – scrollbar */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {/* Entwurf-Banner */}
          {letzterEntwurf && (
            <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-xl p-4 flex items-start gap-3">
              <span className="text-green-600 dark:text-green-400 text-xl">✓</span>
              <div className="flex-1 space-y-1">
                <p className="text-sm font-medium text-green-800 dark:text-green-300">
                  RE-Entwurf <span className="font-bold">{letzterEntwurf.rechnungsnummer}</span> erstellt aus „{letzterEntwurf.vorlage_bezeichnung}"
                </p>
                {letzterEntwurf.preisaenderungen.length > 0 && (
                  <div>
                    <p className="text-xs text-amber-700 dark:text-amber-400 font-medium mt-1">⚠ Preisänderungen im Entwurf übernommen:</p>
                    {letzterEntwurf.preisaenderungen.map((pa, i) => (
                      <p key={i} className="text-xs text-amber-700 dark:text-amber-400 ml-3">
                        · {pa.beschreibung}: {parseFloat(pa.preis_vorlage).toFixed(2)} € → {parseFloat(pa.preis_aktuell).toFixed(2)} €
                      </p>
                    ))}
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                      Klicke „Preise sync" um die Vorlage auf die neuen Preise zu aktualisieren.
                    </p>
                  </div>
                )}
              </div>
              <button onClick={() => setLetzterEntwurf(null)} className="text-green-400 hover:text-green-600 text-lg leading-none">×</button>
            </div>
          )}

          {isLoading ? (
            <p className="text-sm text-slate-400 dark:text-slate-500">Lade Vorlagen…</p>
          ) : vorlagen.length === 0 ? (
            <div className="text-center py-16 text-slate-400 dark:text-slate-500 space-y-2">
              <p className="text-4xl">🔁</p>
              <p className="text-sm">Noch keine Vorlagen angelegt.</p>
              <p className="text-xs">Erstelle eine Vorlage für regelmäßige Leistungen wie Hosting, Wartung oder Miete.</p>
            </div>
          ) : vorlagenGefiltert.length === 0 ? (
            <p className="text-sm text-slate-400 dark:text-slate-500 text-center py-8">Keine Vorlagen entsprechen dem Filter.</p>
          ) : (
            <div className={`grid gap-4 ${formModus !== null ? 'grid-cols-1' : 'grid-cols-1 sm:grid-cols-2'}`}>
              {vorlagenGefiltert.map(v => (
                <div key={v.id} onClick={() => { setSelId(v.id); setFormModus(null) }}
                  className={`cursor-pointer rounded-xl transition-all ${selId === v.id ? 'ring-2 ring-blue-500' : ''}`}>
                  <VorlageKarte
                    vorlage={v}
                    onEntwurfJetzt={() => entwurfMut.mutate(v.id)}
                    onPreisSync={() => syncMut.mutate(v.id)}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {formModus !== null && manuell && (
        <div
          className="w-1 shrink-0 bg-slate-200 dark:bg-slate-700 hover:bg-indigo-400 dark:hover:bg-indigo-500 cursor-col-resize transition-colors select-none"
          onMouseDown={startSplitterDrag}
        />
      )}

      {/* Rechts: Formular */}
      {formModus !== null && (
        <div className="flex-1 border-l border-slate-200 dark:border-slate-700 overflow-auto">
          <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
            <h3 className="font-semibold text-slate-800 dark:text-slate-100">
              {formModus === 'neu' ? 'Neue Vorlage' : 'Vorlage bearbeiten'}
            </h3>
            <button onClick={() => setFormModus(null)}
              className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-xl">×</button>
          </div>
          <div className="p-6">
            <VorlageFormular
              key={typeof formModus === 'number' ? formModus : 'neu'}
              initial={editVorlage}
              isSaving={createMut.isPending || updateMut.isPending}
              onSpeichern={handleSave}
              onAbbrechen={() => setFormModus(null)}
              auftraegeAktiv={!!unternehmen?.auftraege_aktiv}
              auftraege={auftraege}
              defaultAuftragId={formModus === 'neu' ? defaultAuftragId : undefined}
              defaultAuftrag={formModus === 'neu' ? defaultAuftrag : undefined}
              onVertragUpload={typeof formModus === 'number' ? (datei) => vertragUploadMut.mutate({ id: formModus, datei }) : undefined}
              onVertragDelete={typeof formModus === 'number' ? () => vertragDeleteMut.mutate(formModus) : undefined}
              isVertragUploading={vertragUploadMut.isPending || vertragDeleteMut.isPending}
            />
          </div>
        </div>
      )}

      {/* Rechts: Detail-Panel */}
      {selVorlage && formModus === null && (
        <div className="w-[28rem] shrink-0 border-l border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col">
          <VorlageDetail
            vorlage={selVorlage}
            onClose={() => setSelId(null)}
            onBearbeiten={() => { setFormModus(selVorlage.id); setSelId(null) }}
            onBeenden={() => handleBeenden(selVorlage.id, selVorlage.bezeichnung)}
            onLoeschen={() => handleLoeschen(selVorlage.id, selVorlage.bezeichnung)}
          />
        </div>
      )}
    </div>
  )
}
