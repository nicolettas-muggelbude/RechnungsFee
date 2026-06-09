import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  getAuftraege, getRechnung, getKunden, getUstSaetze, getDokumentenPakete, getUnternehmen,
  auftragErstellen, updateRechnung, deleteRechnung,
  rechnungAusAuftrag, lieferscheinAusAuftrag, proformaAusAuftrag, auftragStatusSetzen,
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

const STATUS_LABEL: Record<string, { label: string; cls: string }> = {
  offen:          { label: 'Offen',          cls: 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300 border-blue-200 dark:border-blue-700' },
  in_bearbeitung: { label: 'In Bearbeitung', cls: 'bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300 border-amber-200 dark:border-amber-700' },
  abgeschlossen:  { label: 'Abgeschlossen',  cls: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700' },
  storniert:      { label: 'Storniert',      cls: 'bg-red-50 text-red-600 dark:bg-red-950 dark:text-red-400 border-red-200 dark:border-red-700' },
}

function StatusBadge({ status }: { status: string | null }) {
  const s = status ?? 'offen'
  const info = STATUS_LABEL[s] ?? STATUS_LABEL.offen
  return (
    <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded border ${info.cls}`}>
      {info.label}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Positions-Tabelle
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
                <input value={pos.menge} onChange={e => update(i, 'menge', e.target.value)}
                  type="text" className={`${cellInput} text-right`} />
              </td>
              <td className="px-2 py-1.5">
                <input value={pos.einheit} onChange={e => update(i, 'einheit', e.target.value)}
                  placeholder="Stk." className={cellInput} />
              </td>
              <td className="px-2 py-1.5">
                <input value={pos.einzelpreis} onChange={e => update(i, 'einzelpreis', e.target.value)}
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

function AuftragFormular({
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
  const { data: pakete } = useQuery({ queryKey: ['dokumentenpakete'], queryFn: getDokumentenPakete })

  const [kundeId, setKundeId] = useState(initial?.kunde_id?.toString() ?? vorKundeId ?? '')
  const [datum, setDatum] = useState(initial?.datum ?? heuteIso())
  const [notizen, setNotizen] = useState(initial?.notizen ?? '')
  const [paketId, setPaketId] = useState(initial?.dokumentenpaket_id?.toString() ?? '')
  const [eingabeModus, setEingabeModus] = useState<EingabeModus>('brutto')

  useEffect(() => {
    if (!kundeId || !kunden) return
    const k = kunden.find(k => String(k.id) === kundeId)
    if (k) setEingabeModus(k.firmenname?.trim() ? 'netto' : 'brutto')
  }, [kundeId, kunden])

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

  useEffect(() => {
    if (!ustSaetze?.length || initial) return
    setPositionen(prev => prev.map(p =>
      p.einzelpreis === '' ? { ...p, ust_satz: defaultSatz } : p
    ))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ustSaetze])

  function fillPositionFromArtikel(i: number, a: ArtikelSuche) {
    const ust_satz = a.differenzbesteuerung ? '0'
      : (ustSaetze?.find(u => parseFloat(u.satz) === parseFloat(a.steuersatz))?.satz ?? a.steuersatz)
    const preis = eingabeModus === 'netto'
      ? parseFloat(a.vk_netto).toFixed(2)
      : parseFloat(a.vk_brutto).toFixed(2)
    setPositionen(prev => prev.map((p, idx) =>
      idx !== i ? p : {
        ...p,
        beschreibung: a.bezeichnung,
        einheit: a.einheit,
        einzelpreis: preis,
        ust_satz,
        artikel_id: a.id,
      }
    ))
  }

  async function submit(e: React.FormEvent, istEntwurf: boolean) {
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
        dokument_typ: 'Auftrag' as const,
        dokumentenpaket_id: paketId ? parseInt(paketId) : undefined,
        ist_entwurf: istEntwurf,
        positionen: posPayload,
      }

      let result: Rechnung
      if (initial) {
        result = await updateRechnung(initial.id, payload)
      } else {
        result = await auftragErstellen(payload)
      }
      qc.invalidateQueries({ queryKey: ['auftraege'] })
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
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Auftragsdatum</label>
        <input type="date" value={datum} onChange={e => setDatum(e.target.value)} className={inputCls} />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Dokumentenpaket</label>
        <select value={paketId} onChange={e => setPaketId(e.target.value)} className={selectCls}>
          <option value="">— Kein Paket —</option>
          {pakete?.filter(p => p.aktiv).map(p => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
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
        <button type="button" disabled={laedt} onClick={(e) => submit(e, true)}
          className="flex-1 px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors">
          📝 Entwurf speichern
        </button>
        <button type="button" disabled={laedt} onClick={(e) => submit(e, false)}
          className="flex-1 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors">
          {laedt ? 'Speichern…' : initial ? '✓ Speichern' : '✓ Auftrag erstellen'}
        </button>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Detail-Panel
// ---------------------------------------------------------------------------

function AuftragDetail({
  auftrag,
  onEdit,
  onClose,
  onDelete,
}: {
  auftrag: Rechnung
  onEdit: () => void
  onClose: () => void
  onDelete: () => void
}) {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [statusLaedt, setStatusLaedt] = useState(false)
  const [finLaedt, setFinLaedt] = useState(false)
  const [reLaedt, setReLaedt] = useState(false)
  const [lsLaedt, setLsLaedt] = useState(false)
  const [pfLaedt, setPfLaedt] = useState(false)
  const [pdfLaedt, setPdfLaedt] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)

  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen, staleTime: 1000 * 60 * 5 })

  async function handleFinalisieren() {
    setFinLaedt(true)
    try {
      await updateRechnung(auftrag.id, { ist_entwurf: false })
      qc.invalidateQueries({ queryKey: ['auftraege'] })
    } catch (e: any) { setFehler(e?.message) }
    finally { setFinLaedt(false) }
  }

  async function fetchPdfBlob(): Promise<string> {
    const blob = await getRechnungPdf(auftrag.id)
    return URL.createObjectURL(blob)
  }

  async function handlePdf() {
    setPdfLaedt(true)
    try {
      const blobUrl = await fetchPdfBlob()
      if (isTauri()) {
        openInPdfWindow(blobUrl, `Auftrag ${auftrag.rechnungsnummer ?? ''}`)
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
        openInPdfWindow(blobUrl, 'Auftrag drucken')
        setTimeout(() => URL.revokeObjectURL(blobUrl), 120_000)
      } else {
        const win = window.open(blobUrl, '_blank')
        if (win) win.addEventListener('load', () => win.print())
        setTimeout(() => URL.revokeObjectURL(blobUrl), 120_000)
      }
    } finally { setPdfLaedt(false) }
  }

  async function handleMail() {
    setPdfLaedt(true)
    try {
      const base = await getApiBase()
      await openUrl(`${base}/rechnungen/${auftrag.id}/pdf?download=1`)
    } finally { setPdfLaedt(false) }

    const datumDe = auftrag.datum.split('-').reverse().join('.')
    const kundeName = auftrag.kunde_name ?? auftrag.partner_freitext ?? ''
    const firmenname = unternehmen?.firmenname ?? [unternehmen?.vorname, unternehmen?.nachname].filter(Boolean).join(' ') ?? 'RechnungsFee'
    const brutto = (parseFloat(auftrag.brutto_gesamt as any) || 0).toFixed(2).replace('.', ',')

    const subject = encodeURIComponent(`Auftragsbestätigung ${auftrag.rechnungsnummer ?? ''} – ${firmenname}`)
    const body = encodeURIComponent(
      `Guten Tag ${kundeName},\n\nvielen Dank für Ihren Auftrag. Anbei finden Sie die Auftragsbestätigung ${auftrag.rechnungsnummer ?? ''} vom ${datumDe}.\n\nAuftragswert: ${brutto} €\n\nBitte fügen Sie die heruntergeladene PDF-Datei als Anhang hinzu.\n\nMit freundlichen Grüßen\n${firmenname}${unternehmen?.mail_signatur ? '\n\n' + unternehmen.mail_signatur : ''}`
    )
    const mailtoUrl = `mailto:?subject=${subject}&body=${body}`
    if (isTauri()) {
      await openUrl(mailtoUrl)
    } else {
      window.location.href = mailtoUrl
    }
  }

  async function handleStatusChange(s: string) {
    setStatusLaedt(true)
    try {
      await auftragStatusSetzen(auftrag.id, s)
      qc.invalidateQueries({ queryKey: ['auftraege'] })
    } catch (e: any) { setFehler(e?.message) }
    finally { setStatusLaedt(false) }
  }

  async function handleRechnungErstellen() {
    setReLaedt(true)
    try {
      const re = await rechnungAusAuftrag(auftrag.id)
      qc.invalidateQueries({ queryKey: ['auftraege'] })
      navigate(`/rechnungen?id=${re.id}`)
    } catch (e: any) { setFehler(e?.message) }
    finally { setReLaedt(false) }
  }

  async function handleLieferscheinErstellen() {
    setLsLaedt(true)
    try {
      const ls = await lieferscheinAusAuftrag(auftrag.id)
      qc.invalidateQueries({ queryKey: ['auftraege'] })
      navigate(`/lieferscheine?id=${ls.id}`)
    } catch (e: any) { setFehler(e?.message) }
    finally { setLsLaedt(false) }
  }

  async function handleProformaErstellen() {
    setPfLaedt(true)
    try {
      const pf = await proformaAusAuftrag(auftrag.id)
      qc.invalidateQueries({ queryKey: ['auftraege'] })
      navigate(`/proformas?id=${pf.id}`)
    } catch (e: any) { setFehler(e?.message) }
    finally { setPfLaedt(false) }
  }

  const brutto = parseFloat(auftrag.brutto_gesamt as any) || 0

  const btnBase = 'flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
  const btnNeutral = `${btnBase} border-slate-300 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300`
  const btnGreen   = `${btnBase} border-green-300 dark:border-green-700 hover:bg-green-50 dark:hover:bg-green-950 text-green-700 dark:text-green-400 font-medium`
  const btnRed     = `${btnBase} border-red-200 dark:border-red-800 hover:bg-red-50 dark:hover:bg-red-950 text-red-600 dark:text-red-400`

  return (
    <div className="flex flex-col h-full">
      <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between shrink-0">
        <div>
          <p className="font-semibold text-slate-800 dark:text-slate-100">{auftrag.rechnungsnummer ?? '(keine Nummer)'}</p>
          <p className="text-xs text-slate-400 dark:text-slate-500">Auftrag</p>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-xl">×</button>
      </div>

      <div className="p-5 space-y-5 flex-1 overflow-y-auto">

        {fehler && (
          <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl px-3 py-2 text-sm text-red-700 dark:text-red-300">
            {fehler}
          </div>
        )}

        {/* Entwurf-Banner */}
        {auftrag.ist_entwurf && (
          <div className="flex items-center justify-between gap-2 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-xl px-3 py-2">
            <span className="text-sm text-amber-800 dark:text-amber-300">
              📝 <strong>Entwurf</strong> – noch nicht versendbar
            </span>
            <button onClick={handleFinalisieren} disabled={finLaedt}
              className="px-3 py-1 text-xs font-medium bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 shrink-0">
              {finLaedt ? '…' : 'Finalisieren'}
            </button>
          </div>
        )}

        {/* Aktionsleiste */}
        <div className="flex flex-wrap gap-2">
          <button onClick={handleDrucken} disabled={pdfLaedt || !!auftrag.ist_entwurf} className={btnNeutral}>🖨️ Drucken</button>
          <button onClick={handlePdf} disabled={pdfLaedt || !!auftrag.ist_entwurf} className={btnNeutral}>
            📄 {pdfLaedt ? 'Lädt…' : 'PDF öffnen'}
          </button>
          <button onClick={handleMail} disabled={pdfLaedt || !!auftrag.ist_entwurf} className={btnNeutral}>✉️ Mail senden</button>
          <button
            onClick={onEdit}
            disabled={auftrag.auftrag_status === 'in_bearbeitung' || auftrag.auftrag_status === 'abgeschlossen' || auftrag.auftrag_status === 'storniert'}
            title={auftrag.auftrag_status !== 'offen' ? 'Nur offene Aufträge können bearbeitet werden' : undefined}
            className={btnNeutral}
          >✏️ Bearbeiten</button>

          {/* → Rechnung */}
          {!auftrag.rechnung_zu_auftrag_id ? (
            <button
              onClick={handleRechnungErstellen}
              disabled={reLaedt || !!auftrag.ist_entwurf || auftrag.auftrag_status === 'storniert' || auftrag.auftrag_status === 'in_bearbeitung' || auftrag.auftrag_status === 'abgeschlossen'}
              title={auftrag.auftrag_status === 'in_bearbeitung' || auftrag.auftrag_status === 'abgeschlossen' ? 'Auftrag ist bereits in Bearbeitung' : undefined}
              className={btnGreen}
            >
              {reLaedt ? '⏳ Erstelle…' : '→ Rechnung'}
            </button>
          ) : (
            <button onClick={() => navigate(`/rechnungen?id=${auftrag.rechnung_zu_auftrag_id}`)} className={btnGreen}>
              → {auftrag.rechnung_zu_auftrag_nr ?? `RE #${auftrag.rechnung_zu_auftrag_id}`}
            </button>
          )}

          {/* → Lieferschein */}
          {unternehmen?.lieferschein_aktiv && (
            !auftrag.lieferschein_zu_auftrag_id ? (
              <button
                onClick={handleLieferscheinErstellen}
                disabled={lsLaedt || !!auftrag.ist_entwurf || auftrag.auftrag_status === 'storniert' || auftrag.auftrag_status === 'in_bearbeitung' || auftrag.auftrag_status === 'abgeschlossen'}
                title={auftrag.auftrag_status === 'in_bearbeitung' || auftrag.auftrag_status === 'abgeschlossen' ? 'Auftrag ist bereits in Bearbeitung' : undefined}
                className={btnGreen}
              >
                {lsLaedt ? '⏳ Erstelle…' : '→ Lieferschein'}
              </button>
            ) : (
              <button onClick={() => navigate(`/lieferscheine?id=${auftrag.lieferschein_zu_auftrag_id}`)} className={btnGreen}>
                → {auftrag.lieferschein_zu_auftrag_nr ?? `LS #${auftrag.lieferschein_zu_auftrag_id}`}
              </button>
            )
          )}

          {/* → Proforma */}
          {unternehmen?.proforma_aktiv && (
            !auftrag.proforma_zu_auftrag_id ? (
              <button
                onClick={handleProformaErstellen}
                disabled={pfLaedt || !!auftrag.ist_entwurf || auftrag.auftrag_status === 'storniert' || auftrag.auftrag_status === 'in_bearbeitung' || auftrag.auftrag_status === 'abgeschlossen'}
                title={auftrag.auftrag_status === 'in_bearbeitung' || auftrag.auftrag_status === 'abgeschlossen' ? 'Auftrag ist bereits in Bearbeitung' : undefined}
                className={btnGreen}
              >
                {pfLaedt ? '⏳ Erstelle…' : '→ Proforma'}
              </button>
            ) : (
              <button onClick={() => navigate(`/proformas?id=${auftrag.proforma_zu_auftrag_id}`)} className={btnGreen}>
                → {auftrag.proforma_zu_auftrag_nr ?? `PRF #${auftrag.proforma_zu_auftrag_id}`}
              </button>
            )
          )}

          <button onClick={onDelete} disabled={
            !!(auftrag.rechnung_zu_auftrag_id || auftrag.lieferschein_zu_auftrag_id || auftrag.proforma_zu_auftrag_id)
          } title={
            auftrag.rechnung_zu_auftrag_id || auftrag.lieferschein_zu_auftrag_id || auftrag.proforma_zu_auftrag_id
              ? 'Kann nicht gelöscht werden – es wurden bereits Dokumente erstellt'
              : undefined
          } className={btnRed}>🗑️ Löschen</button>
        </div>

        {/* Rückverlinkung zum Angebot */}
        {auftrag.angebot_zu_auftrag_id && (
          <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-sm">
            <span className="text-slate-500 dark:text-slate-400">Erstellt aus Angebot </span>
            <button onClick={() => navigate(`/angebote?id=${auftrag.angebot_zu_auftrag_id}`)}
              className="text-blue-600 hover:underline font-medium">
              {auftrag.angebot_zu_auftrag_nr ?? `#${auftrag.angebot_zu_auftrag_id}`}
            </button>
          </div>
        )}

        {/* Status */}
        <div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">Status</p>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(STATUS_LABEL).map(([s, info]) => (
              <button
                key={s}
                disabled={statusLaedt}
                onClick={() => handleStatusChange(s)}
                className={`text-xs px-2.5 py-1 rounded-lg border font-medium transition-colors disabled:opacity-50 ${
                  auftrag.auftrag_status === s
                    ? info.cls
                    : 'border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700'
                }`}
              >
                {info.label}
              </button>
            ))}
          </div>
        </div>

        {/* Metadaten */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-sm">
            <span className="text-slate-500 dark:text-slate-400">Kunde</span>
            <span className="font-medium text-slate-800 dark:text-slate-100">{auftrag.kunde_name ?? auftrag.partner_freitext ?? '—'}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-slate-500 dark:text-slate-400">Datum</span>
            <span className="text-slate-700 dark:text-slate-200">{formatDatum(auftrag.datum)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-slate-500 dark:text-slate-400">Brutto</span>
            <span className="font-semibold text-slate-800 dark:text-slate-100">
              {brutto.toFixed(2).replace('.', ',')} €
            </span>
          </div>
          {auftrag.notizen && (
            <div className="pt-1 border-t border-slate-100 dark:border-slate-700 text-xs text-slate-500 dark:text-slate-400 whitespace-pre-wrap">
              {auftrag.notizen}
            </div>
          )}
        </div>

        {/* Positionen */}
        {auftrag.positionen?.length > 0 && (
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
                  {auftrag.positionen.map((pos, i) => (
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
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Haupt-Seite
// ---------------------------------------------------------------------------

export function AuftraegePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const qc = useQueryClient()

  const { data: auftraege, isLoading } = useQuery({ queryKey: ['auftraege'], queryFn: getAuftraege })
  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen, staleTime: 1000 * 60 * 5 })

  const [selId, setSelId] = useState<number | null>(null)
  const [zeigFormular, setZeigFormular] = useState(false)
  const [editAuftrag, setEditAuftrag] = useState<Rechnung | undefined>()

  const selAuftrag = auftraege?.find(a => a.id === selId) ?? null

  // ?id=X beim ersten Mount: Auftrag direkt vom Server laden (wie RechnungenPage)
  useEffect(() => {
    const openId = searchParams.get('id')
    if (openId) {
      const id = parseInt(openId, 10)
      if (!isNaN(id)) {
        getRechnung(id)
          .then((r) => {
            setSelId(r.id)
            qc.invalidateQueries({ queryKey: ['auftraege'] })
            setSearchParams({}, { replace: true })
          })
          .catch(() => setSearchParams({}, { replace: true }))
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteRechnung(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['auftraege'] })
      setSelId(null)
    },
  })

  function handleNeu() {
    setEditAuftrag(undefined)
    setZeigFormular(true)
    setSelId(null)
  }

  function handleEdit(a: Rechnung) {
    setEditAuftrag(a)
    setZeigFormular(true)
  }

  function handleSpeichern(id: number) {
    setZeigFormular(false)
    setEditAuftrag(undefined)
    setSelId(id)
  }

  function handleDelete(id: number) {
    if (!confirm('Auftrag löschen?')) return
    deleteMut.mutate(id)
  }

  if (!unternehmen?.auftraege_aktiv) {
    return (
      <div className="p-8 max-w-lg mx-auto text-center space-y-4">
        <p className="text-4xl">📋</p>
        <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Aufträge nicht aktiviert</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm">
          Aktiviere Aufträge unter <strong>Einstellungen → Unternehmensdaten → Rechnungen</strong>.
        </p>
      </div>
    )
  }

  return (
    <div className="flex h-full">
      {/* Liste – schrumpft auf 1/3 wenn Formular aktiv */}
      <div className={`${zeigFormular ? 'w-1/3 min-w-[260px] shrink-0' : 'flex-1'} flex flex-col border-e border-slate-200 dark:border-slate-700 min-w-0 min-h-0 transition-all`}>
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between shrink-0">
          <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Aufträge</h1>
          <button onClick={handleNeu}
            className="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-xl">
            + Neuer Auftrag
          </button>
        </div>

        {/* Einträge */}
        <div className="flex-1 overflow-y-auto">
          {isLoading && (
            <div className="p-6 animate-pulse space-y-2">
              {[1, 2, 3].map(i => <div key={i} className="h-12 bg-slate-100 dark:bg-slate-800 rounded" />)}
            </div>
          )}
          {!isLoading && (!auftraege || auftraege.length === 0) && (
            <div className="p-10 text-center">
              <p className="text-slate-500 dark:text-slate-400">Noch keine Aufträge vorhanden.</p>
              <p className="text-slate-400 dark:text-slate-500 text-sm mt-1">Klicke auf „+ Neuer Auftrag" um zu starten.</p>
            </div>
          )}
          {auftraege && auftraege.length > 0 && (
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
                {auftraege.map(a => (
                  <tr
                    key={a.id}
                    onClick={() => { setSelId(a.id); setZeigFormular(false) }}
                    className={`border-b border-slate-50 dark:border-slate-700 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-700 cursor-pointer transition-colors ${
                      selId === a.id ? 'bg-blue-50 dark:bg-slate-600 border-l-2 border-l-blue-500' : ''
                    }`}
                  >
                    <td className="px-5 py-3 font-mono text-xs text-slate-400 dark:text-slate-500">{a.rechnungsnummer}</td>
                    <td className="px-5 py-3 text-slate-500 dark:text-slate-400">{formatDatum(a.datum)}</td>
                    <td className="px-5 py-3 text-slate-700 dark:text-slate-200">{a.kunde_name ?? a.partner_freitext ?? '—'}</td>
                    <td className="px-5 py-3 text-right text-slate-700 dark:text-slate-200">
                      {(parseFloat(a.brutto_gesamt as any) || 0).toFixed(2).replace('.', ',')} €
                    </td>
                    <td className="px-5 py-3 text-center">
                      {a.ist_entwurf
                        ? <span className="inline-block text-xs font-medium px-2 py-0.5 rounded border bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800">Entwurf</span>
                        : <StatusBadge status={a.auftrag_status} />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Rechter Panel: Formular oder Detail */}
      {zeigFormular && (
        <div className="flex-1 border-l border-slate-200 dark:border-slate-700 overflow-auto">
          <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
            <h3 className="font-semibold text-slate-800 dark:text-slate-100">
              {editAuftrag ? 'Auftrag bearbeiten' : 'Neuer Auftrag'}
            </h3>
            <button type="button" onClick={() => { setZeigFormular(false); setEditAuftrag(undefined) }}
              className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-xl">×</button>
          </div>
          <div className="p-6">
            <AuftragFormular
              initial={editAuftrag}
              onSpeichern={handleSpeichern}
              onAbbrechen={() => { setZeigFormular(false); setEditAuftrag(undefined) }}
            />
          </div>
        </div>
      )}

      {selAuftrag && !zeigFormular && (
        <div className="w-80 shrink-0 border-l border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col">
          <AuftragDetail
            auftrag={selAuftrag}
            onEdit={() => handleEdit(selAuftrag)}
            onClose={() => setSelId(null)}
            onDelete={() => handleDelete(selAuftrag.id)}
          />
        </div>
      )}
    </div>
  )
}
