import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  getProformas, getKunden, getUstSaetze, getUnternehmen,
  createRechnung, updateRechnung, deleteRechnung,
  rechnungAusProforma,
  getApiBase, openUrl, getRechnungPdf, isTauri, openInPdfWindow, downloadPdfForMail,
  type Rechnung, type ArtikelSuche,
} from '../../api/client'
import { ArtikelAutocomplete } from '../../components/ArtikelAutocomplete'
import { MailDialog } from '../../components/MailDialog'

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

  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen, staleTime: 1000 * 60 * 5 })

  const [kundeId, setKundeId] = useState(initial?.kunde_id?.toString() ?? vorKundeId ?? '')
  const [datum, setDatum] = useState(initial?.datum ?? heuteIso())
  const [faelligAm, setFaelligAm] = useState(initial?.faellig_am ?? '')
  const [notizen, setNotizen] = useState(initial?.notizen ?? '')
  const [eingabeModus, setEingabeModus] = useState<EingabeModus>('brutto')

  // Automatisch auf Netto wechseln wenn eine Firma (B2B) gewählt wird
  useEffect(() => {
    if (!kundeId || !kunden) return
    const k = kunden.find(k => String(k.id) === kundeId)
    if (k) setEingabeModus(k.firmenname?.trim() ? 'netto' : 'brutto')
  }, [kundeId, kunden])

  // faellig_am aus Unternehmens-Standard berechnen wenn noch leer
  useEffect(() => {
    if (initial || faelligAm) return
    const tage = unternehmen?.standard_zahlungsziel ?? 14
    const d = new Date(datum)
    d.setDate(d.getDate() + tage)
    setFaelligAm(d.toISOString().slice(0, 10))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unternehmen, datum])

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

  // Sobald UstSätze geladen sind, default-Satz der leeren Positionen korrigieren
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
      idx !== i ? p : { ...p, beschreibung: a.bezeichnung, einheit: a.einheit, einzelpreis: preis, ust_satz, artikel_id: a.id }
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
        faellig_am: faelligAm || undefined,
        kunde_id: parseInt(kundeId),
        notizen: notizen || undefined,
        dokument_typ: 'Proforma' as const,
        ist_entwurf: istEntwurf,
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

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Datum</label>
          <input type="date" value={datum} onChange={e => setDatum(e.target.value)} className={inputCls} />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Zahlungsziel</label>
          <input type="date" value={faelligAm} onChange={e => setFaelligAm(e.target.value)} className={inputCls} />
        </div>
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
  const [finLaedt, setFinLaedt] = useState(false)
  const [pdfLaedt, setPdfLaedt] = useState(false)
  const hatBezug = !!proforma.rechnung_zu_proforma_id
  const [zeigMailEingabe, setZeigMailEingabe] = useState(false)
  const [mailAdresse, setMailAdresse] = useState('')
  const [zeigMailDialog, setZeigMailDialog] = useState(false)
  const [zeigSmtpHinweis, setZeigSmtpHinweis] = useState(false)
  const [zeigZahlungsForm, setZeigZahlungsForm] = useState(false)
  const [zahlungsart, setZahlungsart] = useState('Bank')
  const [bezahltAm, setBezahltAm] = useState(heuteIso())
  const [fehler, setFehler] = useState<string | null>(null)

  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen, staleTime: 1000 * 60 * 5 })

  async function handleFinalisieren() {
    setFinLaedt(true)
    try {
      await updateRechnung(proforma.id, { ist_entwurf: false })
      qc.invalidateQueries({ queryKey: ['proformas'] })
    } catch (e: any) { setFehler(e?.message) }
    finally { setFinLaedt(false) }
  }

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
    if (unternehmen?.smtp_aktiv) { setZeigMailDialog(true); return }
    const email = proforma.kunde_email || mailAdresse.trim()
    if (!email) { setZeigMailEingabe(true); return }

    setPdfLaedt(true)
    try {
      await downloadPdfForMail(proforma.id)
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
    setZeigSmtpHinweis(true)
    setTimeout(() => setZeigSmtpHinweis(false), 6000)
  }

  async function handleRechnungErstellen() {
    if (!zeigZahlungsForm) { setZeigZahlungsForm(true); return }
    setKonvLaedt(true)
    try {
      const re = await rechnungAusProforma(proforma.id, { zahlungsart, bezahlt_am: bezahltAm })
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

        {/* Entwurf-Banner */}
        {proforma.ist_entwurf && (
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
          <button onClick={handleDrucken} disabled={pdfLaedt || !!proforma.ist_entwurf} className={btnNeutral}>
            🖨️ Drucken
          </button>
          <button onClick={handlePdf} disabled={pdfLaedt || !!proforma.ist_entwurf} className={btnNeutral}>
            📄 {pdfLaedt ? 'Lädt…' : 'PDF öffnen'}
          </button>
          <button onClick={() => handleMail()} disabled={pdfLaedt || !!proforma.ist_entwurf} className={btnNeutral}>
            ✉️ Mail senden{!proforma.kunde_email ? ' …' : ''}
          </button>
          <button onClick={onEdit} disabled={hatBezug}
            title={hatBezug ? 'Bereits eine Rechnung vorhanden' : undefined}
            className={btnNeutral}>
            ✏️ Bearbeiten
          </button>
          {!proforma.rechnung_zu_proforma_id ? (
            <button
              onClick={handleRechnungErstellen}
              disabled={konvLaedt || !!proforma.ist_entwurf}
              title={proforma.ist_entwurf ? 'Erst Entwurf finalisieren' : 'Zahlung eingegangen – Rechnung als bezahlt anlegen'}
              className={btnGreen}
            >
              {konvLaedt ? '⏳ Erstelle…' : '✓ Zahlung eingegangen'}
            </button>
          ) : (
            <button onClick={() => navigate(`/rechnungen?id=${proforma.rechnung_zu_proforma_id}`)} className={btnGreen}>
              → {proforma.rechnung_zu_proforma_nr ?? `RE #${proforma.rechnung_zu_proforma_id}`}
            </button>
          )}
          <button onClick={onDelete} disabled={hatBezug}
            title={hatBezug ? 'Kann nicht gelöscht werden – bereits eine Rechnung vorhanden' : undefined}
            className={btnRed}>
            🗑 Löschen
          </button>
        </div>

        {zeigSmtpHinweis && (
          <div className="fixed bottom-6 right-6 z-50 max-w-sm bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-xl p-4 shadow-lg flex gap-3 items-start">
            <span className="text-lg">💡</span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-blue-900 dark:text-blue-100">Tipp: SMTP einrichten</p>
              <p className="text-xs text-blue-700 dark:text-blue-300 mt-0.5">Mit SMTP-Versand werden PDF und Dokumentenpakete automatisch als Anhang beigefügt.</p>
              <button onClick={() => { setZeigSmtpHinweis(false); navigate('/stammdaten/unternehmen') }}
                className="mt-2 text-xs text-blue-600 dark:text-blue-400 underline hover:no-underline">
                Jetzt einrichten →
              </button>
            </div>
            <button onClick={() => setZeigSmtpHinweis(false)} className="text-blue-400 hover:text-blue-600 dark:text-blue-500 dark:hover:text-blue-300 text-sm leading-none">✕</button>
          </div>
        )}

        {zeigMailDialog && (
          <MailDialog
            dokument={proforma}
            dokumentTyp="Proforma"
            unternehmen={unternehmen}
            onClose={() => setZeigMailDialog(false)}
          />
        )}

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

        {/* Zahlungs-Formular */}
        {zeigZahlungsForm && !proforma.rechnung_zu_proforma_id && (
          <div className="border border-green-200 dark:border-green-800 rounded-xl p-4 bg-green-50 dark:bg-green-950/30 space-y-3">
            <p className="text-sm font-medium text-green-800 dark:text-green-300">Zahlungseingang buchen</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Zahlungsart</label>
                <select value={zahlungsart} onChange={e => setZahlungsart(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-1.5 text-sm bg-white dark:bg-slate-700 dark:text-slate-100">
                  <option value="Bank">Bank</option>
                  <option value="PayPal">PayPal</option>
                  <option value="Karte">Karte</option>
                  <option value="Bar">Bar</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Zahlungsdatum</label>
                <input type="date" value={bezahltAm} onChange={e => setBezahltAm(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-1.5 text-sm dark:bg-slate-700 dark:text-slate-100" />
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => setZeigZahlungsForm(false)}
                className="px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                Abbrechen
              </button>
              <button onClick={handleRechnungErstellen} disabled={konvLaedt}
                className="flex-1 px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 font-medium">
                {konvLaedt ? '⏳ Erstelle…' : '✓ Zahlung buchen & Rechnung erstellen'}
              </button>
            </div>
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
          {proforma.faellig_am && (
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Zahlungsziel</span>
              <span className="font-medium text-slate-700 dark:text-slate-200">{formatDatum(proforma.faellig_am)}</span>
            </div>
          )}
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
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [filterId, setFilterId] = useState<number | null>(null)
  const [formModus, setFormModus] = useState<'neu' | 'bearbeiten' | null>(null)
  const [suche, setSuche] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  const { data: proformas, isLoading } = useQuery({
    queryKey: ['proformas'],
    queryFn: getProformas,
  })

  // ?id=X aus Navigation (z.B. von AngebotePage)
  useEffect(() => {
    const id = searchParams.get('id')
    if (id) {
      const n = parseInt(id)
      setSelectedId(n)
      setFilterId(n)
      setSearchParams({}, { replace: true })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const deleteMut = useMutation({
    mutationFn: deleteRechnung,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['proformas'] }); setSelectedId(null) },
  })

  const anzeigeProformas = (proformas ?? []).filter(p => {
    if (filterId && p.id !== filterId) return false
    if (statusFilter) {
      if (statusFilter === 'entwurf' && !p.ist_entwurf) return false
      if (statusFilter === 'abgerechnet' && (p.ist_entwurf || !p.rechnung_zu_proforma_id)) return false
      if (statusFilter === 'offen' && (p.ist_entwurf || !!p.rechnung_zu_proforma_id)) return false
    }
    if (suche) {
      const q = suche.toLowerCase()
      return (
        (p.rechnungsnummer ?? '').toLowerCase().includes(q) ||
        (p.kunde_name ?? p.partner_freitext ?? '').toLowerCase().includes(q)
      )
    }
    return true
  })

  const selected = proformas?.find(p => p.id === selectedId) ?? null

  const listContainerRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase()
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return
      if (formModus) return
      if (!anzeigeProformas.length) return
      e.preventDefault()
      const idx = selectedId != null ? anzeigeProformas.findIndex(p => p.id === selectedId) : -1
      const nextIdx = e.key === 'ArrowDown' ? Math.min(idx + 1, anzeigeProformas.length - 1) : Math.max(idx - 1, 0)
      const next = anzeigeProformas[nextIdx]
      if (!next) return
      setSelectedId(next.id)
      listContainerRef.current?.focus({ preventScroll: true })
      requestAnimationFrame(() => {
        listContainerRef.current?.querySelector(`[data-proforma-id="${next.id}"]`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
      })
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [anzeigeProformas, selectedId, formModus])

  function handleDelete() {
    if (!selected) return
    if (!confirm(`Proforma ${selected.rechnungsnummer} wirklich löschen?`)) return
    deleteMut.mutate(selected.id)
  }

  return (
    <div className="flex h-full">
      {/* Liste */}
      <div className={`${formModus ? 'w-1/3 min-w-[260px] shrink-0' : 'flex-1'} flex flex-col border-e border-slate-200 dark:border-slate-700 min-w-0 min-h-0 transition-all`}>
        {/* Header – bleibt beim Scrollen stehen */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 shrink-0">
          <div className="flex items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Proforma</h1>
              {filterId && (
                <button
                  onClick={() => setFilterId(null)}
                  className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700 hover:bg-blue-200 dark:hover:bg-blue-800"
                >
                  Gefiltert × alle anzeigen
                </button>
              )}
            </div>
            <button
              onClick={() => { setFormModus('neu'); setSelectedId(null) }}
              className="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-xl"
            >
              + Neue Proforma
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            <input
              type="search"
              placeholder="Nummer oder Kunde suchen…"
              value={suche}
              onChange={e => setSuche(e.target.value)}
              className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 flex-1 min-w-[160px]"
            />
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
            >
              <option value="">Alle Status</option>
              <option value="offen">Offen</option>
              <option value="abgerechnet">Abgerechnet</option>
              <option value="entwurf">Entwurf</option>
            </select>
          </div>
        </div>

        {/* Kennzahlen – bleibt beim Scrollen stehen */}
        {(proformas?.length ?? 0) > 0 && (
          <div className="px-6 py-3 grid grid-cols-3 gap-3 border-b border-slate-100 dark:border-slate-800 shrink-0">
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Proformas</p>
              <p className="text-lg font-bold text-slate-800 dark:text-slate-100">{proformas!.length}</p>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Offen</p>
              <p className="text-lg font-bold text-blue-600 dark:text-blue-400">
                {proformas!.filter(p => !p.ist_entwurf && !p.rechnung_zu_proforma_id).length}
              </p>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Abgerechnet</p>
              <p className="text-lg font-bold text-green-600 dark:text-green-400">
                {proformas!.filter(p => !!p.rechnung_zu_proforma_id).length}
              </p>
            </div>
          </div>
        )}

        <div ref={listContainerRef} tabIndex={0} className="flex-1 overflow-y-auto min-h-0 px-6 pb-6 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 dark:focus-visible:ring-blue-500 focus-visible:ring-offset-2 rounded-sm">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          {isLoading ? (
            <div className="p-6 animate-pulse space-y-2">
              {[1, 2, 3].map(i => <div key={i} className="h-12 bg-slate-100 dark:bg-slate-800 rounded" />)}
            </div>
          ) : !proformas?.length ? (
            <div className="p-10 text-center">
              <p className="text-slate-500 dark:text-slate-400">Noch keine Proforma-Rechnungen vorhanden.</p>
              <p className="text-slate-400 dark:text-slate-500 text-sm mt-1">Klicke auf „+ Neue Proforma" oder erstelle eine aus einem Angebot.</p>
            </div>
          ) : !anzeigeProformas.length ? (
            <div className="p-10 text-center">
              <p className="text-slate-500 dark:text-slate-400">Keine Proformas für diese Filter.</p>
              <button onClick={() => { setSuche(''); setStatusFilter('') }} className="mt-2 text-sm text-blue-600 hover:underline">Filter zurücksetzen</button>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-900 border-b border-slate-100 dark:border-slate-700">
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Datum</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Nummer</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Kunde</th>
                  <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Brutto</th>
                  <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Status</th>
                </tr>
              </thead>
              <tbody>
                {anzeigeProformas.map(p => {
                  const tageOffen = p.datum && !p.rechnung_zu_proforma_id
                    ? Math.floor((Date.now() - new Date(p.datum).getTime()) / 86_400_000)
                    : 0
                  const ueberfaellig = tageOffen > 14
                  return (
                  <tr
                    key={p.id}
                    data-proforma-id={p.id}
                    tabIndex={0}
                    onClick={() => { setSelectedId(p.id); setFormModus(null) }}
                    className={`border-b border-slate-50 dark:border-slate-700 last:border-0 cursor-pointer transition-colors focus:outline-none ${
                      selectedId === p.id
                        ? 'bg-blue-100 dark:bg-slate-600 border-l-2 border-l-blue-500'
                        : ueberfaellig
                          ? 'bg-amber-50 dark:bg-amber-950/30 hover:bg-amber-100 dark:hover:bg-amber-950/50'
                          : 'hover:bg-slate-50 dark:hover:bg-slate-700'
                    }`}
                  >
                    <td className="px-5 py-3 text-slate-500 dark:text-slate-400">{formatDatum(p.datum)}</td>
                    <td className="px-5 py-3 font-mono text-xs text-slate-400 dark:text-slate-500">
                      {p.rechnungsnummer}
                      {(p.herkunft_angebot_nr ?? p.herkunft_auftrag_nr) && (
                        <span className="ml-1.5 text-[10px] text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded px-1">
                          aus {p.herkunft_angebot_nr ?? p.herkunft_auftrag_nr}
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-slate-700 dark:text-slate-200">{p.kunde_name ?? p.partner_freitext ?? '—'}</td>
                    <td className="px-5 py-3 text-right text-slate-700 dark:text-slate-200">
                      {(parseFloat(p.brutto_gesamt as any) || 0).toFixed(2).replace('.', ',')} €
                    </td>
                    <td className="px-5 py-3 text-center">
                      {p.rechnung_zu_proforma_id
                        ? <span className="inline-block text-xs font-medium px-2 py-0.5 rounded border bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800">Abgerechnet</span>
                        : ueberfaellig
                          ? <span className="inline-block text-xs font-medium px-2 py-0.5 rounded border bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800">{tageOffen}d offen</span>
                          : <span className="inline-block text-xs font-medium px-2 py-0.5 rounded border bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800">Offen</span>
                      }
                    </td>
                  </tr>
                  )
                })}
              </tbody>
            </table>
          )}
          </div>
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
