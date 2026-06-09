import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  getProformas, getKunden, getUstSaetze, getUnternehmen,
  createRechnung, updateRechnung, deleteRechnung,
  rechnungAusProforma,
  getApiBase, openUrl, getRechnungPdf, isTauri, openInPdfWindow,
  type Rechnung, type ArtikelSuche,
} from '../../api/client'
import { ArtikelAutocomplete } from '../../components/ArtikelAutocomplete'

// ---------------------------------------------------------------------------
// Hilfsfunktionen
// ---------------------------------------------------------------------------

function formatDatum(iso: string | null | undefined) {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

function heuteIso() {
  return new Date().toISOString().slice(0, 10)
}

const inputCls = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100 dark:placeholder-slate-400"
const selectCls = `${inputCls} bg-white dark:bg-slate-700`

// ---------------------------------------------------------------------------
// Positions-Tabelle (identisch zu Angebote)
// ---------------------------------------------------------------------------

interface Pos {
  beschreibung: string
  menge: string
  einheit: string
  einzelpreis: string
  ust_satz: string
  artikel_id?: number
}

function leerePos(): Pos {
  return { beschreibung: '', menge: '1', einheit: 'Stk.', einzelpreis: '', ust_satz: '19' }
}

type EingabeModus = 'brutto' | 'netto'

function nettoProStueck(pos: Pos, modus: EingabeModus): number {
  const ep  = parseFloat(pos.einzelpreis.replace(',', '.')) || 0
  const ust = parseFloat(pos.ust_satz) || 0
  return modus === 'brutto' ? ep / (1 + ust / 100) : ep
}

function berechnePos(pos: Pos, modus: EingabeModus) {
  const menge = parseFloat(pos.menge) || 0
  const ust   = parseFloat(pos.ust_satz) || 0
  const netto = nettoProStueck(pos, modus) * menge
  const ustBet = (netto * ust) / 100
  return { netto, ustBet, brutto: netto + ustBet }
}

function PositionenTabelle({
  positionen, onChange, ustSaetze, onArtikelWahl, eingabeModus,
}: {
  positionen: Pos[]
  onChange: (p: Pos[]) => void
  ustSaetze: { satz: string }[]
  onArtikelWahl: (i: number, a: ArtikelSuche) => void
  eingabeModus: EingabeModus
}) {
  function update(i: number, field: keyof Pos, val: string) {
    onChange(positionen.map((p, idx) => idx === i ? { ...p, [field]: val } : p))
  }

  const gesamt = positionen.reduce((acc, p) => {
    const { netto, ustBet, brutto } = berechnePos(p, eingabeModus)
    return { netto: acc.netto + netto, ust: acc.ust + ustBet, brutto: acc.brutto + brutto }
  }, { netto: 0, ust: 0, brutto: 0 })

  return (
    <div className="space-y-2">
      {positionen.map((pos, i) => (
        <div key={i} className="border border-slate-200 dark:border-slate-700 rounded-xl p-3 space-y-2">
          <div className="flex gap-2 items-start">
            <div className="flex-1">
              <ArtikelAutocomplete
                value={pos.beschreibung}
                onChange={v => update(i, 'beschreibung', v)}
                onSelect={a => onArtikelWahl(i, a)}
                placeholder="Beschreibung"
                className={inputCls}
              />
            </div>
            {positionen.length > 1 && (
              <button type="button"
                onClick={() => onChange(positionen.filter((_, idx) => idx !== i))}
                className="text-slate-400 hover:text-red-500 dark:hover:text-red-400 text-lg leading-none mt-2">×</button>
            )}
          </div>
          <div className="grid grid-cols-4 gap-2">
            <div>
              <label className="text-xs text-slate-500 dark:text-slate-400">Menge</label>
              <input type="number" value={pos.menge} onChange={e => update(i, 'menge', e.target.value)}
                className={inputCls} min="0.001" step="any" />
            </div>
            <div>
              <label className="text-xs text-slate-500 dark:text-slate-400">Einheit</label>
              <input type="text" value={pos.einheit} onChange={e => update(i, 'einheit', e.target.value)}
                className={inputCls} placeholder="Stk." />
            </div>
            <div>
              <label className="text-xs text-slate-500 dark:text-slate-400">
                {eingabeModus === 'netto' ? 'Einzelpreis (Netto)' : 'Einzelpreis (Brutto)'}
              </label>
              <input type="number" value={pos.einzelpreis} onChange={e => update(i, 'einzelpreis', e.target.value)}
                className={inputCls} min="0" step="0.01" placeholder="0.00" />
            </div>
            <div>
              <label className="text-xs text-slate-500 dark:text-slate-400">USt %</label>
              <select value={pos.ust_satz} onChange={e => update(i, 'ust_satz', e.target.value)} className={selectCls}>
                {ustSaetze.map(u => <option key={u.satz} value={u.satz}>{u.satz} %</option>)}
              </select>
            </div>
          </div>
        </div>
      ))}
      <div className="text-right text-sm text-slate-600 dark:text-slate-300 pr-1">
        <span className="text-slate-400 dark:text-slate-500 mr-2">Gesamt:</span>
        <strong>{gesamt.brutto.toFixed(2).replace('.', ',')} €</strong>
        <span className="text-slate-400 dark:text-slate-500 ml-2 text-xs">
          ({gesamt.netto.toFixed(2).replace('.', ',')} € + {gesamt.ust.toFixed(2).replace('.', ',')} € USt)
        </span>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Formular
// ---------------------------------------------------------------------------

function ProformaFormular({
  initial,
  vorKundeId,
  onSpeichern,
  onAbbrechen,
}: {
  initial?: Rechnung
  vorKundeId?: string
  onSpeichern: (id: number) => void
  onAbbrechen: () => void
}) {
  const qc = useQueryClient()
  const [fehler, setFehler] = useState<string | null>(null)
  const [laedt, setLaedt] = useState(false)

  const { data: kunden } = useQuery({ queryKey: ['kunden'], queryFn: getKunden })
  const { data: ustSaetze } = useQuery({ queryKey: ['ust-saetze'], queryFn: getUstSaetze })

  const [kundeId, setKundeId] = useState(initial?.kunde_id?.toString() ?? vorKundeId ?? '')
  const [datum, setDatum] = useState(initial?.datum ?? heuteIso())
  const [notizen, setNotizen] = useState(initial?.notizen ?? '')
  const [eingabeModus, setEingabeModus] = useState<EingabeModus>('brutto')

  const ustSaetzeListe = ustSaetze?.filter(u => u.ist_aktiv) ?? []
  const defaultSatz = ustSaetze?.find(u => u.ist_default)?.satz
    ?? ustSaetze?.find(u => parseFloat(u.satz) === 19)?.satz
    ?? '19'

  const [positionen, setPositionen] = useState<Pos[]>(() => {
    if (initial?.positionen?.length) {
      return initial.positionen.map(p => ({
        beschreibung: p.beschreibung,
        menge: String(p.menge),
        einheit: p.einheit,
        einzelpreis: String(p.netto),
        ust_satz: String(p.ust_satz),
      }))
    }
    return [leerePos()]
  })

  function fillPositionFromArtikel(i: number, a: ArtikelSuche) {
    const ust_satz = a.differenzbesteuerung ? '0'
      : (ustSaetze?.find(u => parseFloat(u.satz) === parseFloat(a.steuersatz))?.satz ?? a.steuersatz)
    const preis = eingabeModus === 'netto'
      ? parseFloat(a.vk_netto).toFixed(2)
      : parseFloat(a.vk_brutto).toFixed(2)
    setPositionen(prev => prev.map((p, idx) =>
      idx !== i ? p : { ...p, beschreibung: a.bezeichnung, einheit: a.einheit, einzelpreis: preis, ust_satz, artikel_id: a.id }
    ))
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!kundeId) { setFehler('Bitte einen Kunden wählen.'); return }
    if (positionen.some(p => !p.beschreibung.trim())) { setFehler('Alle Positionen benötigen eine Beschreibung.'); return }

    setLaedt(true)
    setFehler(null)
    try {
      const posPayload = positionen.map((p) => {
        const nettoEinzel = nettoProStueck(p, eingabeModus)
        return {
          beschreibung: p.beschreibung.trim(),
          menge: String(parseFloat(p.menge) || 1),
          einheit: p.einheit || 'Stk.',
          netto: String(nettoEinzel),
          ust_satz: String(parseFloat(p.ust_satz) || 0),
          artikel_id: p.artikel_id,
        }
      })

      const payload = {
        typ: 'ausgang' as const,
        datum,
        kunde_id: parseInt(kundeId),
        notizen: notizen || undefined,
        dokument_typ: 'Proforma' as const,
        ist_entwurf: false,
        positionen: posPayload,
      }

      let result: Rechnung
      if (initial) {
        result = await updateRechnung(initial.id, payload)
      } else {
        result = await createRechnung(payload)
      }
      qc.invalidateQueries({ queryKey: ['proformas'] })
      onSpeichern(result.id)
    } catch (e: any) {
      setFehler(e?.message ?? 'Fehler beim Speichern.')
    } finally {
      setLaedt(false)
    }
  }

  return (
    <form onSubmit={(e) => e.preventDefault()} className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Kunde *</label>
        <select value={kundeId} onChange={e => setKundeId(e.target.value)} className={selectCls} required>
          <option value="">— Kunden wählen —</option>
          {kunden?.map(k => (
            <option key={k.id} value={k.id}>
              {k.firmenname || [k.vorname, k.nachname].filter(Boolean).join(' ')}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Datum</label>
        <input type="date" value={datum} onChange={e => setDatum(e.target.value)} className={inputCls} />
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Positionen *</label>
          <div className="flex items-center gap-3">
            <button type="button" onClick={() => setEingabeModus(eingabeModus === 'netto' ? 'brutto' : 'netto')}
              className="text-xs text-blue-600 hover:text-blue-700 underline">
              {eingabeModus === 'netto' ? 'Brutto eingeben' : 'Netto eingeben'}
            </button>
            <button type="button"
              onClick={() => setPositionen(prev => [...prev, { ...leerePos(), ust_satz: defaultSatz }])}
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

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Notizen</label>
        <textarea value={notizen} onChange={e => setNotizen(e.target.value)}
          rows={3} className={`${inputCls} resize-none`}
          placeholder="Erscheint als Fußtext auf dem PDF" />
      </div>

      {fehler && <p className="text-sm text-red-600">{fehler}</p>}

      <div className="flex gap-2">
        <button type="button" onClick={onAbbrechen}
          className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 dark:text-slate-300 transition-colors">
          Abbrechen
        </button>
        <button type="button" disabled={laedt} onClick={submit}
          className="flex-1 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors">
          {laedt ? 'Speichern…' : initial ? '✓ Speichern' : '✓ Proforma erstellen'}
        </button>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Detail-Panel
// ---------------------------------------------------------------------------

function ProformaDetail({
  proforma,
  onEdit,
  onClose,
  onDelete,
}: {
  proforma: Rechnung
  onEdit: () => void
  onClose: () => void
  onDelete: () => void
}) {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [konvLaedt, setKonvLaedt] = useState(false)
  const [pdfLaedt, setPdfLaedt] = useState(false)
  const [zeigMailEingabe, setZeigMailEingabe] = useState(false)
  const [mailAdresse, setMailAdresse] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)

  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen, staleTime: 1000 * 60 * 5 })

  async function fetchPdfBlob(): Promise<string> {
    const blob = await getRechnungPdf(proforma.id)
    return URL.createObjectURL(blob)
  }

  async function handlePdf() {
    setPdfLaedt(true)
    try {
      const blobUrl = await fetchPdfBlob()
      if (isTauri()) {
        openInPdfWindow(blobUrl, `Proforma ${proforma.rechnungsnummer ?? ''}`)
      } else {
        window.open(blobUrl, '_blank')
      }
      setTimeout(() => URL.revokeObjectURL(blobUrl), 120_000)
    } finally { setPdfLaedt(false) }
  }

  async function handleDrucken() {
    setPdfLaedt(true)
    try {
      const blobUrl = await fetchPdfBlob()
      if (isTauri()) {
        openInPdfWindow(blobUrl, 'Proforma drucken')
        setTimeout(() => URL.revokeObjectURL(blobUrl), 120_000)
      } else {
        const win = window.open(blobUrl, '_blank')
        if (win) win.addEventListener('load', () => win.print())
        setTimeout(() => URL.revokeObjectURL(blobUrl), 120_000)
      }
    } finally { setPdfLaedt(false) }
  }

  async function handleMail() {
    const email = mailAdresse.trim()
    if (!email) { setZeigMailEingabe(true); return }

    setPdfLaedt(true)
    try {
      const base = await getApiBase()
      await openUrl(`${base}/rechnungen/${proforma.id}/pdf?download=1`)
    } finally { setPdfLaedt(false) }

    const datumDe = proforma.datum.split('-').reverse().join('.')
    const kundeName = proforma.kunde_name ?? proforma.partner_freitext ?? ''
    const firmenname = unternehmen?.firmenname ?? [unternehmen?.vorname, unternehmen?.nachname].filter(Boolean).join(' ') ?? 'RechnungsFee'
    const brutto = (parseFloat(proforma.brutto_gesamt as any) || 0).toFixed(2).replace('.', ',')

    const subject = encodeURIComponent(`Proforma-Rechnung ${proforma.rechnungsnummer ?? ''} – ${firmenname}`)
    const body = encodeURIComponent(
      `Guten Tag ${kundeName},\n\nanbei findest du unsere Proforma-Rechnung ${proforma.rechnungsnummer ?? ''} vom ${datumDe}.\n\nBetrag: ${brutto} €\n\nBitte füge die heruntergeladene PDF-Datei als Anhang hinzu.\n\nMit freundlichen Grüßen\n${firmenname}${unternehmen?.mail_signatur ? '\n\n' + unternehmen.mail_signatur : ''}`
    )
    const mailtoUrl = `mailto:${email}?subject=${subject}&body=${body}`
    if (isTauri()) {
      await openUrl(mailtoUrl)
    } else {
      window.location.href = mailtoUrl
    }
    setZeigMailEingabe(false)
    setMailAdresse('')
  }

  async function handleRechnungErstellen() {
    setKonvLaedt(true)
    try {
      const re = await rechnungAusProforma(proforma.id)
      qc.invalidateQueries({ queryKey: ['proformas'] })
      navigate(`/rechnungen?id=${re.id}`)
    } catch (e: any) { setFehler(e?.message) }
    finally { setKonvLaedt(false) }
  }

  const brutto = parseFloat(proforma.brutto_gesamt as any) || 0

  const btnBase = 'flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
  const btnNeutral = `${btnBase} border-slate-300 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300`
  const btnGreen   = `${btnBase} border-green-300 dark:border-green-700 hover:bg-green-50 dark:hover:bg-green-950 text-green-700 dark:text-green-400 font-medium`
  const btnRed     = `${btnBase} border-red-200 dark:border-red-800 hover:bg-red-50 dark:hover:bg-red-950 text-red-600 dark:text-red-400`

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between shrink-0">
        <div>
          <p className="font-semibold text-slate-800 dark:text-slate-100">{proforma.rechnungsnummer ?? '(keine Nummer)'}</p>
          <p className="text-xs text-slate-400 dark:text-slate-500">Proforma-Rechnung</p>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-xl">×</button>
      </div>

      {/* Inhalt */}
      <div className="p-5 space-y-5 flex-1 overflow-y-auto">

        {/* Aktionsleiste */}
        <div className="flex flex-wrap gap-2">
          <button onClick={handleDrucken} disabled={pdfLaedt} className={btnNeutral}>
            🖨️ Drucken
          </button>
          <button onClick={handlePdf} disabled={pdfLaedt} className={btnNeutral}>
            📄 {pdfLaedt ? 'Lädt…' : 'PDF öffnen'}
          </button>
          <button onClick={() => handleMail()} disabled={pdfLaedt} className={btnNeutral}>
            ✉️ Mail senden
          </button>
          <button onClick={onEdit} className={btnNeutral}>
            ✏️ Bearbeiten
          </button>
          {!proforma.rechnung_zu_proforma_id ? (
            <button
              onClick={handleRechnungErstellen}
              disabled={konvLaedt}
              className={btnGreen}
            >
              {konvLaedt ? '⏳ Erstelle…' : '→ Rechnung'}
            </button>
          ) : (
            <button onClick={() => navigate(`/rechnungen?id=${proforma.rechnung_zu_proforma_id}`)} className={btnGreen}>
              → {proforma.rechnung_zu_proforma_nr ?? `RE #${proforma.rechnung_zu_proforma_id}`}
            </button>
          )}
          <button onClick={onDelete} className={btnRed}>
            🗑 Löschen
          </button>
        </div>

        {/* Mail-Eingabe */}
        {zeigMailEingabe && (
          <div className="flex gap-2 items-center">
            <input
              type="email"
              value={mailAdresse}
              onChange={e => setMailAdresse(e.target.value)}
              placeholder="E-Mail-Adresse eingeben…"
              className="flex-1 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 dark:bg-slate-700 dark:text-slate-100"
              autoFocus
              onKeyDown={e => e.key === 'Enter' && handleMail()}
            />
            <button onClick={handleMail} disabled={!mailAdresse.trim()}
              className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
              Öffnen
            </button>
            <button onClick={() => { setZeigMailEingabe(false); setMailAdresse('') }}
              className="px-3 py-1.5 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg text-sm hover:bg-slate-50 dark:hover:bg-slate-700">
              Abbrechen
            </button>
          </div>
        )}

        {/* Verlinkungen */}
        {(proforma.angebot_zu_proforma_id || proforma.rechnung_zu_proforma_id) && (
          <div className="space-y-1">
            {proforma.angebot_zu_proforma_id && (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-slate-500 dark:text-slate-400">Aus Angebot:</span>
                <button
                  onClick={() => navigate(`/angebote?id=${proforma.angebot_zu_proforma_id}`)}
                  className="text-blue-600 dark:text-blue-400 hover:underline font-medium"
                >
                  {proforma.angebot_zu_proforma_nr ?? `ANG #${proforma.angebot_zu_proforma_id}`}
                </button>
              </div>
            )}
            {proforma.rechnung_zu_proforma_id && (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-slate-500 dark:text-slate-400">Rechnung erstellt:</span>
                <button
                  onClick={() => navigate(`/rechnungen?id=${proforma.rechnung_zu_proforma_id}`)}
                  className="text-green-600 dark:text-green-400 hover:underline font-medium"
                >
                  {proforma.rechnung_zu_proforma_nr ?? `RE #${proforma.rechnung_zu_proforma_id}`}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Metadaten */}
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-500 dark:text-slate-400">Kunde</span>
            <span className="font-medium text-slate-800 dark:text-slate-100 text-right">{proforma.kunde_name ?? proforma.partner_freitext ?? '—'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500 dark:text-slate-400">Datum</span>
            <span className="text-slate-700 dark:text-slate-200">{formatDatum(proforma.datum)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500 dark:text-slate-400">Betrag</span>
            <span className="font-bold text-slate-800 dark:text-slate-100">
              {brutto.toFixed(2).replace('.', ',')} €
            </span>
          </div>
        </div>

        {/* Positionen */}
        {proforma.positionen && proforma.positionen.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">Positionen</p>
            <div className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
              <table className="w-full text-xs">
                <thead className="bg-slate-50 dark:bg-slate-900">
                  <tr>
                    <th className="px-3 py-2 text-left text-slate-500 dark:text-slate-400 font-medium">Beschreibung</th>
                    <th className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 font-medium">Netto</th>
                    <th className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 font-medium">USt</th>
                    <th className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 font-medium">Brutto</th>
                  </tr>
                </thead>
                <tbody>
                  {proforma.positionen.map((pos, i) => (
                    <tr key={i} className="border-t border-slate-100 dark:border-slate-700">
                      <td className="px-3 py-2 text-slate-700 dark:text-slate-200">
                        {pos.menge !== '1' && <span className="text-slate-400 dark:text-slate-500 mr-1">{pos.menge}×</span>}
                        {pos.beschreibung}
                      </td>
                      <td className="px-3 py-2 text-right text-slate-600 dark:text-slate-300">
                        {(parseFloat(pos.netto as any) || 0).toFixed(2).replace('.', ',')} €
                      </td>
                      <td className="px-3 py-2 text-right text-slate-400 dark:text-slate-500">
                        {pos.ust_satz}%
                      </td>
                      <td className="px-3 py-2 text-right font-medium text-slate-700 dark:text-slate-200">
                        {(parseFloat(pos.brutto as any) || 0).toFixed(2).replace('.', ',')} €
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-700">
                  <tr>
                    <td colSpan={3} className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 font-medium">Gesamt</td>
                    <td className="px-3 py-2 text-right font-bold text-slate-800 dark:text-slate-100">
                      {brutto.toFixed(2).replace('.', ',')} €
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}

        {proforma.notizen && (
          <div>
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Notizen</p>
            <p className="text-sm text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2 whitespace-pre-wrap">{proforma.notizen}</p>
          </div>
        )}

        {fehler && <p className="text-sm text-red-600">{fehler}</p>}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Haupt-Seite
// ---------------------------------------------------------------------------

export function ProformaPage() {
  const qc = useQueryClient()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [formModus, setFormModus] = useState<'neu' | 'bearbeiten' | null>(null)

  const { data: proformas, isLoading } = useQuery({
    queryKey: ['proformas'],
    queryFn: getProformas,
  })

  const deleteMut = useMutation({
    mutationFn: deleteRechnung,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['proformas'] }); setSelectedId(null) },
  })

  const selected = proformas?.find(p => p.id === selectedId) ?? null

  function handleDelete() {
    if (!selected) return
    if (!confirm(`Proforma ${selected.rechnungsnummer} wirklich löschen?`)) return
    deleteMut.mutate(selected.id)
  }

  return (
    <div className="flex h-full">
      {/* Liste */}
      <div className={`${formModus ? 'w-1/3 min-w-[260px] shrink-0' : 'flex-1'} flex flex-col border-e border-slate-200 dark:border-slate-700 min-w-0 min-h-0 transition-all`}>
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between shrink-0">
          <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Proforma</h1>
          <button
            onClick={() => { setFormModus('neu'); setSelectedId(null) }}
            className="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-xl"
          >
            + Neue Proforma
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="p-6 animate-pulse space-y-2">
              {[1, 2, 3].map(i => <div key={i} className="h-12 bg-slate-100 dark:bg-slate-800 rounded" />)}
            </div>
          ) : !proformas?.length ? (
            <div className="p-10 text-center">
              <p className="text-slate-500 dark:text-slate-400">Noch keine Proforma-Rechnungen vorhanden.</p>
              <p className="text-slate-400 dark:text-slate-500 text-sm mt-1">Klicke auf „+ Neue Proforma" oder erstelle eine aus einem Angebot.</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800">
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Nummer</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Datum</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Kunde</th>
                  <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Brutto</th>
                  <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Status</th>
                </tr>
              </thead>
              <tbody>
                {proformas.map(p => (
                  <tr
                    key={p.id}
                    onClick={() => { setSelectedId(p.id); setFormModus(null) }}
                    className={`border-b border-slate-50 dark:border-slate-700 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-700 cursor-pointer transition-colors ${
                      selectedId === p.id ? 'bg-blue-50 dark:bg-slate-600 border-l-2 border-l-blue-500' : ''
                    }`}
                  >
                    <td className="px-5 py-3 font-mono text-xs text-slate-400 dark:text-slate-500">{p.rechnungsnummer}</td>
                    <td className="px-5 py-3 text-slate-500 dark:text-slate-400">{formatDatum(p.datum)}</td>
                    <td className="px-5 py-3 text-slate-700 dark:text-slate-200">{p.kunde_name ?? p.partner_freitext ?? '—'}</td>
                    <td className="px-5 py-3 text-right text-slate-700 dark:text-slate-200">
                      {(parseFloat(p.brutto_gesamt as any) || 0).toFixed(2).replace('.', ',')} €
                    </td>
                    <td className="px-5 py-3 text-center">
                      {p.rechnung_zu_proforma_id
                        ? <span className="inline-block text-xs font-medium px-2 py-0.5 rounded border bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800">Abgerechnet</span>
                        : <span className="inline-block text-xs font-medium px-2 py-0.5 rounded border bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800">Offen</span>
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Rechter Panel: Formular oder Detail */}
      {formModus && (
        <div className="flex-1 border-l border-slate-200 dark:border-slate-700 overflow-auto">
          <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
            <h3 className="font-semibold text-slate-800 dark:text-slate-100">
              {formModus === 'bearbeiten' ? 'Proforma bearbeiten' : 'Neue Proforma-Rechnung'}
            </h3>
            <button type="button" onClick={() => setFormModus(null)}
              className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-xl">×</button>
          </div>
          <div className="p-6">
            <ProformaFormular
              initial={formModus === 'bearbeiten' && selected ? selected : undefined}
              onSpeichern={(id) => { setSelectedId(id); setFormModus(null) }}
              onAbbrechen={() => setFormModus(null)}
            />
          </div>
        </div>
      )}

      {/* Detail-Panel */}
      {!formModus && selected && (
        <div className="w-80 shrink-0 border-l border-slate-200 dark:border-slate-700 overflow-y-auto">
          <ProformaDetail
            proforma={selected}
            onEdit={() => setFormModus('bearbeiten')}
            onClose={() => setSelectedId(null)}
            onDelete={handleDelete}
          />
        </div>
      )}
    </div>
  )
}
