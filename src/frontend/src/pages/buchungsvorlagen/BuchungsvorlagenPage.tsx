import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getBuchungsvorlagen, createBuchungsvorlage, updateBuchungsvorlage,
  deleteBuchungsvorlage, buchungAusfuehren,
  uploadBuchungsvorlageBeleg, deleteBuchungsvorlageBeleg,
  analysiereRechnung,
  getKategorien, getLieferanten, getKonten,
  type Buchungsvorlage, type BuchungsvorlageCreate, type AnalyseErgebnis,
} from '../../api/client'
import { LieferantErstellenModal } from '../../components/LieferantErstellenModal'

// ---------------------------------------------------------------------------
// Konstanten
// ---------------------------------------------------------------------------

const INTERVALL_LABEL: Record<string, string> = {
  monatlich: 'Monatlich',
  quartalsweise: 'Quartalsweise',
  jaehrlich: 'Jährlich',
}

const INTERVALL_ICON: Record<string, string> = {
  monatlich: '📅',
  quartalsweise: '🗓️',
  jaehrlich: '📆',
}

function heuteIso() {
  return new Date().toISOString().slice(0, 10)
}

function fmt(d: string) {
  const [y, m, t] = d.split('-')
  return `${t}.${m}.${y}`
}

function istFaellig(datum: string) {
  return datum <= heuteIso()
}

// ---------------------------------------------------------------------------
// Formular
// ---------------------------------------------------------------------------

type FormData = {
  bezeichnung: string
  lieferant_id: number | null
  kategorie_id: number | null
  konto_id: number | null
  betrag: string
  ist_brutto: boolean
  ust_satz: string
  intervall: 'monatlich' | 'quartalsweise' | 'jaehrlich'
  naechstes_datum: string
  aktiv: boolean
  modus: 'direkt' | 'beleg'
  notizen: string
}

function leereForm(): FormData {
  return {
    bezeichnung: '',
    lieferant_id: null,
    kategorie_id: null,
    konto_id: null,
    betrag: '',
    ist_brutto: true,
    ust_satz: '0',
    intervall: 'monatlich',
    naechstes_datum: heuteIso(),
    aktiv: true,
    modus: 'direkt',
    notizen: '',
  }
}

function fromVorlage(v: Buchungsvorlage): FormData {
  return {
    bezeichnung: v.bezeichnung,
    lieferant_id: v.lieferant_id,
    kategorie_id: v.kategorie_id,
    konto_id: v.konto_id,
    betrag: v.betrag,
    ist_brutto: v.ist_brutto,
    ust_satz: v.ust_satz,
    intervall: v.intervall,
    naechstes_datum: v.naechstes_datum,
    aktiv: v.aktiv,
    modus: v.modus,
    notizen: v.notizen ?? '',
  }
}

const inputCls = 'w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100'
const selectCls = inputCls

function VorlageFormular({
  initial,
  onSave,
  onAbbrechen,
  kategorien,
  lieferanten,
  konten,
}: {
  initial?: Buchungsvorlage
  onSave: (d: BuchungsvorlageCreate) => void
  onAbbrechen: () => void
  kategorien: { id: number; name: string; kontenart: string }[]
  lieferanten: { id: number; name: string }[]
  konten: { id: number; bezeichnung: string; kontoart: string }[]
}) {
  const qc = useQueryClient()
  const [form, setForm] = useState<FormData>(initial ? fromVorlage(initial) : leereForm())
  const [showNeuLieferant, setShowNeuLieferant] = useState(false)

  const set = (k: keyof FormData, v: unknown) => setForm(f => ({ ...f, [k]: v }))

  const aufwandKategorien = kategorien.filter(k => k.kontenart === 'Aufwand')

  function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.bezeichnung.trim()) return
    onSave({
      bezeichnung: form.bezeichnung.trim(),
      lieferant_id: form.lieferant_id,
      kategorie_id: form.kategorie_id,
      konto_id: form.konto_id,
      betrag: form.betrag,
      ist_brutto: form.ist_brutto,
      ust_satz: form.ust_satz,
      intervall: form.intervall,
      naechstes_datum: form.naechstes_datum,
      aktiv: form.aktiv,
      modus: form.modus,
      notizen: form.notizen || null,
    } as BuchungsvorlageCreate)
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Bezeichnung *</label>
        <input value={form.bezeichnung} onChange={e => set('bezeichnung', e.target.value)}
          placeholder="z. B. Büromiete, Telefonrechnung" required className={inputCls} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Modus *</label>
          <select value={form.modus} onChange={e => set('modus', e.target.value as 'direkt' | 'beleg')} className={selectCls}>
            <option value="direkt">Direkt buchen (Dauerauftrag/SEPA)</option>
            <option value="beleg">Warte auf Beleg (monatl. Rechnung)</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Intervall *</label>
          <select value={form.intervall} onChange={e => set('intervall', e.target.value as 'monatlich' | 'quartalsweise' | 'jaehrlich')} className={selectCls}>
            <option value="monatlich">Monatlich</option>
            <option value="quartalsweise">Quartalsweise</option>
            <option value="jaehrlich">Jährlich</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Nächste Fälligkeit *</label>
          <input type="date" value={form.naechstes_datum} onChange={e => set('naechstes_datum', e.target.value)} required className={inputCls} />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Lieferant</label>
          <div className="flex gap-1">
            <select value={form.lieferant_id ?? ''} onChange={e => set('lieferant_id', e.target.value ? Number(e.target.value) : null)} className={selectCls + ' flex-1'}>
              <option value="">– kein Lieferant –</option>
              {lieferanten.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
            <button type="button" onClick={() => setShowNeuLieferant(true)}
              title="Neuen Lieferanten anlegen"
              className="shrink-0 px-2.5 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 text-base leading-none">
              +
            </button>
          </div>
          {showNeuLieferant && (
            <LieferantErstellenModal
              onClose={() => setShowNeuLieferant(false)}
              onSave={(neu) => {
                setShowNeuLieferant(false)
                set('lieferant_id', neu.id)
                qc.invalidateQueries({ queryKey: ['lieferanten'] })
              }}
            />
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
            {form.ist_brutto ? 'Brutto-Betrag *' : 'Netto-Betrag *'}
          </label>
          <input type="number" step="0.01" min="0" value={form.betrag}
            onChange={e => set('betrag', e.target.value)} placeholder="0,00 (variabel)" className={inputCls} />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">USt-Satz (%)</label>
          <select value={form.ust_satz} onChange={e => set('ust_satz', e.target.value)} className={selectCls}>
            <option value="0">0 %</option>
            <option value="7">7 %</option>
            <option value="19">19 %</option>
          </select>
        </div>
        <div className="flex items-end pb-1">
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200 cursor-pointer">
            <input type="checkbox" checked={form.ist_brutto} onChange={e => set('ist_brutto', e.target.checked)}
              className="rounded border-slate-300 text-blue-600" />
            Brutto-Eingabe
          </label>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Kategorie (Aufwand)</label>
          <select value={form.kategorie_id ?? ''} onChange={e => set('kategorie_id', e.target.value ? Number(e.target.value) : null)} className={selectCls}>
            <option value="">– keine Kategorie –</option>
            {aufwandKategorien.map(k => <option key={k.id} value={k.id}>{k.name}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Konto</label>
          <select value={form.konto_id ?? ''} onChange={e => set('konto_id', e.target.value ? Number(e.target.value) : null)} className={selectCls}>
            <option value="">– kein Konto –</option>
            {konten.map(k => <option key={k.id} value={k.id}>{k.bezeichnung ?? ''}</option>)}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Notizen</label>
        <textarea value={form.notizen} onChange={e => set('notizen', e.target.value)}
          rows={2} placeholder="z. B. Vertragsnummer, Kostenstelle…" className={inputCls} />
      </div>

      <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200 cursor-pointer">
        <input type="checkbox" checked={form.aktiv} onChange={e => set('aktiv', e.target.checked)}
          className="rounded border-slate-300 text-blue-600" />
        Vorlage aktiv
      </label>

      <div className="flex gap-2 pt-2">
        <button type="submit"
          className="flex-1 px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          {initial ? 'Speichern' : 'Vorlage erstellen'}
        </button>
        <button type="button" onClick={onAbbrechen}
          className="px-4 py-2 text-sm font-medium border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-colors">
          Abbrechen
        </button>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Karte
// ---------------------------------------------------------------------------

function VorlageKarte({ vorlage, onBuchen, onEingangsrechnung }: {
  vorlage: Buchungsvorlage
  onBuchen: () => void
  onEingangsrechnung: () => void
}) {
  const faellig = istFaellig(vorlage.naechstes_datum) && vorlage.aktiv
  const betragNum = parseFloat(vorlage.betrag)

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-xl border ${
      vorlage.aktiv ? 'border-slate-200 dark:border-slate-700' : 'border-slate-100 dark:border-slate-800 opacity-60'
    } p-5 space-y-3`}>

      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-lg">{INTERVALL_ICON[vorlage.intervall] ?? '📒'}</span>
          <div className="min-w-0">
            <h3 className="font-semibold text-slate-800 dark:text-slate-100 truncate">{vorlage.bezeichnung}</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {INTERVALL_LABEL[vorlage.intervall]} · {vorlage.lieferant_name ?? vorlage.kategorie_name ?? 'Keine Kategorie'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {!vorlage.aktiv && (
            <span className="text-xs bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 px-2 py-0.5 rounded-full">Pausiert</span>
          )}
          {faellig && (
            <span className="text-xs bg-orange-100 dark:bg-orange-950 text-orange-700 dark:text-orange-300 px-2 py-0.5 rounded-full font-medium">Fällig</span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 text-sm">
        <div>
          <p className="text-xs text-slate-400 dark:text-slate-500 mb-0.5">Nächste Fälligkeit</p>
          <p className={`font-medium ${faellig ? 'text-orange-600 dark:text-orange-400' : 'text-slate-700 dark:text-slate-200'}`}>
            {fmt(vorlage.naechstes_datum)}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-400 dark:text-slate-500 mb-0.5">Betrag ({vorlage.ist_brutto ? 'brutto' : 'netto'})</p>
          <p className="font-medium text-slate-700 dark:text-slate-200">
            {betragNum === 0
              ? <span className="text-slate-400 dark:text-slate-500 font-normal italic">variabel</span>
              : `${betragNum.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-400 dark:text-slate-500 mb-0.5">Erstellt</p>
          <p className="font-medium text-slate-700 dark:text-slate-200">
            {vorlage.erstellte_buchungen}×{vorlage.letzte_buchung ? ` · ${fmt(vorlage.letzte_buchung)}` : ''}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border ${
          vorlage.modus === 'direkt'
            ? 'bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-700'
            : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-600'
        }`}>
          {vorlage.modus === 'direkt' ? '⚡ Dauerauftrag/SEPA' : '📄 Warte auf Beleg'}
        </span>
        {vorlage.beleg_name && (
          <span className="inline-flex items-center gap-1 text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-600 rounded-full px-2 py-0.5">
            📎 Vertrag hinterlegt
          </span>
        )}
      </div>

      <div className="flex gap-2 pt-1">
        {vorlage.modus === 'direkt' ? (
          <button
            onClick={e => { e.stopPropagation(); onBuchen() }}
            disabled={betragNum === 0}
            className="flex-1 px-3 py-1.5 text-xs font-medium bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
            📒 Jetzt buchen
          </button>
        ) : (
          <button
            onClick={e => { e.stopPropagation(); onEingangsrechnung() }}
            className="flex-1 px-3 py-1.5 text-xs font-medium bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors">
            📥 Eingangsrechnung erfassen
          </button>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Detail-Panel
// ---------------------------------------------------------------------------

function VorlageDetail({
  vorlage,
  onBearbeiten,
  onLoeschen,
  onBuchen,
  onBelegUpload,
  onBelegLoeschen,
}: {
  vorlage: Buchungsvorlage
  onBearbeiten: () => void
  onLoeschen: () => void
  onBuchen: () => void
  onBelegUpload: (f: File) => void
  onBelegLoeschen: () => void
}) {
  const navigate = useNavigate()
  const [ocrLaed, setOcrLaed] = useState(false)
  const faellig = istFaellig(vorlage.naechstes_datum) && vorlage.aktiv
  const betragNum = parseFloat(vorlage.betrag)

  async function handleRechnungsUpload(file: File) {
    setOcrLaed(true)
    try {
      const ergebnis = await analysiereRechnung(file)
      const kombiniert: AnalyseErgebnis = {
        ...ergebnis,
        format: 'vorlage',
        lieferant_vorschlaege: vorlage.lieferant_id
          ? [{ id: vorlage.lieferant_id, name: vorlage.lieferant_name ?? '', score: 1 }]
          : (ergebnis.lieferant_vorschlaege ?? []),
        positionen: ergebnis.positionen?.length
          ? ergebnis.positionen
          : betragNum > 0
            ? [{ beschreibung: vorlage.bezeichnung, menge: '1', einheit: 'Monat', netto: String(betragNum), ust_satz: vorlage.ust_satz }]
            : [],
      }
      sessionStorage.setItem(`vorlage_ocr_${vorlage.id}`, JSON.stringify(kombiniert))
    } catch {
      // OCR fehlgeschlagen – navigieren ohne Vorausfüllung
    }
    navigate(`/rechnungen?typ=eingang&vorlage=${vorlage.id}`)
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-slate-800 dark:text-slate-100 text-base truncate">{vorlage.bezeichnung}</h2>
        <div className="flex gap-2 shrink-0">
          <button onClick={onBearbeiten}
            className="px-3 py-1.5 text-xs font-medium border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-colors">
            ✏️ Bearbeiten
          </button>
          {vorlage.erstellte_buchungen === 0 && (
            <button onClick={onLoeschen}
              className="px-3 py-1.5 text-xs font-medium border border-red-200 dark:border-red-800 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500 dark:text-red-400 transition-colors">
              Löschen
            </button>
          )}
        </div>
      </div>

      {/* Metadaten */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        {[
          ['Modus', vorlage.modus === 'direkt' ? '⚡ Direkt buchen' : '📄 Warte auf Beleg'],
          ['Intervall', INTERVALL_LABEL[vorlage.intervall]],
          ['Nächste Fälligkeit', fmt(vorlage.naechstes_datum)],
          ['Betrag', betragNum === 0 ? 'variabel' : `${betragNum.toLocaleString('de-DE', { minimumFractionDigits: 2 })} € (${vorlage.ist_brutto ? 'brutto' : 'netto'})`],
          ['USt-Satz', `${vorlage.ust_satz} %`],
          ['Buchungen erstellt', `${vorlage.erstellte_buchungen}×`],
          ...(vorlage.letzte_buchung ? [['Letzte Buchung', fmt(vorlage.letzte_buchung)]] : []),
          ...(vorlage.lieferant_name ? [['Lieferant', vorlage.lieferant_name]] : []),
          ...(vorlage.kategorie_name ? [['Kategorie', vorlage.kategorie_name]] : []),
          ...(vorlage.konto_name ? [['Konto', vorlage.konto_name]] : []),
        ].map(([label, value]) => (
          <div key={label}>
            <p className="text-xs text-slate-400 dark:text-slate-500">{label}</p>
            <p className="font-medium text-slate-700 dark:text-slate-200 text-sm">{value}</p>
          </div>
        ))}
      </div>

      {vorlage.notizen && (
        <div className="p-3 bg-slate-50 dark:bg-slate-700 rounded-lg text-sm text-slate-600 dark:text-slate-300">
          {vorlage.notizen}
        </div>
      )}

      {/* Direkt buchen */}
      {vorlage.modus === 'direkt' && (
        <div className={`p-4 rounded-xl border ${faellig ? 'bg-orange-50 dark:bg-orange-950/30 border-orange-200 dark:border-orange-800' : 'bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-600'}`}>
          <p className="text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
            {faellig ? '⚠️ Fällig – jetzt buchen' : '📒 Journal-Eintrag erstellen'}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
            {betragNum === 0
              ? 'Betrag ist variabel – bitte zuerst den Betrag in der Vorlage eintragen.'
              : `Erstellt einen Journal-Eintrag über ${betragNum.toLocaleString('de-DE', { minimumFractionDigits: 2 })} € und rückt das Datum um ein Intervall vor.`}
          </p>
          <button onClick={onBuchen} disabled={betragNum === 0}
            className="w-full px-3 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
            📒 Jetzt buchen
          </button>
        </div>
      )}

      {/* Warte auf Beleg – Upload + OCR */}
      {vorlage.modus === 'beleg' && (
        <div className={`p-4 rounded-xl border ${faellig ? 'bg-orange-50 dark:bg-orange-950/30 border-orange-200 dark:border-orange-800' : 'bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-600'}`}>
          <p className="text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
            {faellig ? '⚠️ Fällig – Eingangsrechnung erfassen' : '📄 Eingangsrechnung erfassen'}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
            PDF hochladen → OCR füllt Belegnummer und Betrag automatisch aus.
          </p>
          <label className={`flex flex-col items-center gap-1.5 cursor-pointer w-full px-3 py-4 border-2 border-dashed rounded-lg transition-colors mb-2 ${
            ocrLaed
              ? 'border-blue-300 bg-blue-50 dark:bg-blue-950/30 cursor-wait'
              : 'border-slate-300 dark:border-slate-600 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-950/20'
          }`}>
            {ocrLaed ? (
              <span className="text-sm text-blue-600 dark:text-blue-400">⏳ Analysiere Rechnung…</span>
            ) : (
              <>
                <span className="text-sm text-slate-600 dark:text-slate-300">📎 Rechnung hochladen (PDF / Bild)</span>
                <span className="text-xs text-slate-400 dark:text-slate-500">OCR extrahiert alle Felder automatisch</span>
              </>
            )}
            <input type="file" accept=".pdf,.jpg,.jpeg,.png" className="hidden" disabled={ocrLaed}
              onChange={e => { if (e.target.files?.[0]) handleRechnungsUpload(e.target.files[0]) }} />
          </label>
          <button
            onClick={() => navigate(`/rechnungen?typ=eingang&vorlage=${vorlage.id}`)}
            className="w-full text-xs text-slate-400 dark:text-slate-500 hover:text-blue-600 dark:hover:text-blue-400 transition-colors py-1"
          >
            Ohne Beleg manuell eingeben →
          </button>
        </div>
      )}

      {/* Vertragsdokument */}
      <div className="border-t border-slate-100 dark:border-slate-700 pt-4">
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2">Vertragsdokument</p>
        {vorlage.beleg_id ? (
          <div className="flex items-center justify-between p-2 bg-slate-50 dark:bg-slate-700 rounded-lg">
            <span className="text-sm text-slate-700 dark:text-slate-200 truncate">📄 {vorlage.beleg_name}</span>
            <button onClick={onBelegLoeschen}
              className="text-xs text-red-500 hover:text-red-700 dark:text-red-400 ml-2 shrink-0">Entfernen</button>
          </div>
        ) : (
          <label className="flex items-center gap-2 cursor-pointer p-2 border border-dashed border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
            <span className="text-sm text-slate-500 dark:text-slate-400">📎 Vertrag hochladen (PDF/JPG/PNG)</span>
            <input type="file" accept=".pdf,.jpg,.jpeg,.png" className="hidden"
              onChange={e => { if (e.target.files?.[0]) onBelegUpload(e.target.files[0]) }} />
          </label>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Hauptseite
// ---------------------------------------------------------------------------

export default function BuchungsvorlagenPage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [selId, setSelId] = useState<number | null>(null)
  const [formModus, setFormModus] = useState<'neu' | 'bearbeiten' | null>(null)
  const [suche, setSuche] = useState('')
  const [aktivFilter, setAktivFilter] = useState<'alle' | 'aktiv' | 'inaktiv'>('aktiv')
  const [modusFilter, setModusFilter] = useState<'' | 'direkt' | 'beleg'>('')

  const { data: vorlagen = [] } = useQuery({ queryKey: ['buchungsvorlagen'], queryFn: getBuchungsvorlagen })
  const { data: kategorien = [] } = useQuery({ queryKey: ['kategorien'], queryFn: getKategorien })
  const { data: lieferanten = [] } = useQuery({ queryKey: ['lieferanten'], queryFn: getLieferanten })
  const { data: konten = [] } = useQuery({ queryKey: ['konten'], queryFn: getKonten })
  const bankKonten = konten.filter(k => k.kontoart === 'bank')

  const selVorlage = vorlagen.find(v => v.id === selId)

  const gefiltert = vorlagen.filter(v => {
    if (suche && !v.bezeichnung.toLowerCase().includes(suche.toLowerCase()) &&
      !v.lieferant_name?.toLowerCase().includes(suche.toLowerCase())) return false
    if (aktivFilter === 'aktiv' && !v.aktiv) return false
    if (aktivFilter === 'inaktiv' && v.aktiv) return false
    if (modusFilter && v.modus !== modusFilter) return false
    return true
  })

  const faelligCount = vorlagen.filter(v => v.aktiv && istFaellig(v.naechstes_datum)).length

  function invalidieren() {
    qc.invalidateQueries({ queryKey: ['buchungsvorlagen'] })
    qc.invalidateQueries({ queryKey: ['journal'] })
  }

  const createMut = useMutation({
    mutationFn: createBuchungsvorlage,
    onSuccess: () => { invalidieren(); setFormModus(null) },
  })
  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<BuchungsvorlageCreate> }) => updateBuchungsvorlage(id, data),
    onSuccess: () => { invalidieren(); setFormModus(null) },
  })
  const deleteMut = useMutation({
    mutationFn: deleteBuchungsvorlage,
    onSuccess: () => { invalidieren(); setSelId(null) },
  })
  const buchenMut = useMutation({
    mutationFn: buchungAusfuehren,
    onSuccess: () => invalidieren(),
  })
  const belegUploadMut = useMutation({
    mutationFn: ({ id, datei }: { id: number; datei: File }) => uploadBuchungsvorlageBeleg(id, datei),
    onSuccess: () => invalidieren(),
  })
  const belegLoeschenMut = useMutation({
    mutationFn: deleteBuchungsvorlageBeleg,
    onSuccess: () => invalidieren(),
  })

  function handleLoeschen(id: number, name: string) {
    if (!confirm(`Vorlage „${name}" wirklich löschen?`)) return
    deleteMut.mutate(id)
  }

  function handleBuchen(id: number) {
    if (!confirm('Jetzt einen Journal-Eintrag erstellen und Datum vorrücken?')) return
    buchenMut.mutate(id)
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* Linke Spalte – Liste */}
      <div className={`${formModus ? 'w-1/3 min-w-[260px] shrink-0' : 'flex-1'} flex flex-col border-e border-slate-200 dark:border-slate-700 min-w-0 overflow-hidden`}>

        {/* Kopfzeile */}
        <div className="p-4 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h1 className="text-lg font-bold text-slate-800 dark:text-slate-100">Buchungsvorlagen</h1>
              {faelligCount > 0 && (
                <p className="text-xs text-orange-600 dark:text-orange-400 font-medium mt-0.5">
                  ⚠️ {faelligCount} Vorlage{faelligCount > 1 ? 'n' : ''} fällig
                </p>
              )}
            </div>
            <button onClick={() => { setFormModus('neu'); setSelId(null) }}
              className="px-3 py-1.5 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shrink-0">
              + Neue Vorlage
            </button>
          </div>

          <input value={suche} onChange={e => setSuche(e.target.value)}
            placeholder="Suche…" className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 mb-2" />

          <div className="flex gap-2">
            <select value={aktivFilter} onChange={e => setAktivFilter(e.target.value as 'alle' | 'aktiv' | 'inaktiv')}
              className="flex-1 border border-slate-300 dark:border-slate-600 rounded-lg px-2 py-1.5 text-xs focus:outline-none dark:bg-slate-700 dark:text-slate-100">
              <option value="aktiv">Nur aktive</option>
              <option value="alle">Alle</option>
              <option value="inaktiv">Nur inaktive</option>
            </select>
            <select value={modusFilter} onChange={e => setModusFilter(e.target.value as '' | 'direkt' | 'beleg')}
              className="flex-1 border border-slate-300 dark:border-slate-600 rounded-lg px-2 py-1.5 text-xs focus:outline-none dark:bg-slate-700 dark:text-slate-100">
              <option value="">Alle Modi</option>
              <option value="direkt">⚡ Direkt</option>
              <option value="beleg">📄 Beleg</option>
            </select>
          </div>
        </div>

        {/* Liste */}
        <div className={`flex-1 overflow-y-auto p-4 grid gap-4 content-start ${formModus ? 'grid-cols-1' : 'grid-cols-1 sm:grid-cols-2'}`}>
          {gefiltert.length === 0 && (
            <div className="col-span-full text-center py-12 text-slate-400 dark:text-slate-500">
              <p className="text-3xl mb-2">📒</p>
              <p className="text-sm">{vorlagen.length === 0 ? 'Noch keine Buchungsvorlagen angelegt' : 'Keine Vorlagen gefunden'}</p>
            </div>
          )}
          {gefiltert.map(v => (
            <div key={v.id}
              onClick={() => { setSelId(v.id); setFormModus(null) }}
              className={`cursor-pointer rounded-xl transition-all ${selId === v.id ? 'ring-2 ring-blue-500' : ''}`}>
              <VorlageKarte
                vorlage={v}
                onBuchen={() => handleBuchen(v.id)}
                onEingangsrechnung={() => navigate(`/rechnungen?typ=eingang&vorlage=${v.id}`)}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Rechte Spalte – Formular */}
      {formModus && (
        <div className="flex-1 border-l border-slate-200 dark:border-slate-700 overflow-y-auto p-6">
          {formModus === 'neu' && (
            <>
              <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100 mb-5">Neue Vorlage</h2>
              <VorlageFormular
                kategorien={kategorien as { id: number; name: string; kontenart: string }[]}
                lieferanten={lieferanten.map(l => ({ id: l.id!, name: l.firmenname }))}
                konten={bankKonten.map(k => ({ id: k.id!, bezeichnung: k.name, kontoart: k.kontoart }))}
                onSave={d => createMut.mutate(d)}
                onAbbrechen={() => setFormModus(null)}
              />
            </>
          )}
          {formModus === 'bearbeiten' && selVorlage && (
            <>
              <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100 mb-5">Vorlage bearbeiten</h2>
              <VorlageFormular
                initial={selVorlage}
                kategorien={kategorien as { id: number; name: string; kontenart: string }[]}
                lieferanten={lieferanten.map(l => ({ id: l.id!, name: l.firmenname }))}
                konten={bankKonten.map(k => ({ id: k.id!, bezeichnung: k.name, kontoart: k.kontoart }))}
                onSave={d => updateMut.mutate({ id: selVorlage.id, data: d })}
                onAbbrechen={() => setFormModus(null)}
              />
            </>
          )}
        </div>
      )}

      {/* Rechte Spalte – Detail (schmal) */}
      {formModus === null && selVorlage && (
        <div className="w-96 shrink-0 border-l border-slate-200 dark:border-slate-700 overflow-y-auto p-6">
          <VorlageDetail
            vorlage={selVorlage}
            onBearbeiten={() => setFormModus('bearbeiten')}
            onLoeschen={() => handleLoeschen(selVorlage.id, selVorlage.bezeichnung)}
            onBuchen={() => handleBuchen(selVorlage.id)}
            onBelegUpload={f => belegUploadMut.mutate({ id: selVorlage.id, datei: f })}
            onBelegLoeschen={() => belegLoeschenMut.mutate(selVorlage.id)}
          />
        </div>
      )}
    </div>
  )
}
