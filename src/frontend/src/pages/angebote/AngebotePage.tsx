import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  getAngebote, getKunden, getUstSaetze, getDokumentenPakete, getUnternehmen,
  createRechnung, updateRechnung, deleteRechnung,
  rechnungAusAngebot, lieferscheinAusAngebot, proformaAusAngebot, auftragAusAngebot, angebotStatusSetzen,
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

function inXTagen(n: number) {
  const d = new Date()
  d.setDate(d.getDate() + n)
  return d.toISOString().slice(0, 10)
}

const inputCls = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100 dark:placeholder-slate-400"
const selectCls = `${inputCls} bg-white dark:bg-slate-700`

const STATUS_LABEL: Record<string, { label: string; cls: string }> = {
  offen:      { label: 'Offen',      cls: 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300 border-blue-200 dark:border-blue-700' },
  akzeptiert: { label: 'Akzeptiert', cls: 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300 border-green-200 dark:border-green-700' },
  abgelehnt:  { label: 'Abgelehnt', cls: 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300 border-red-200 dark:border-red-700' },
  abgelaufen: { label: 'Abgelaufen', cls: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400 border-slate-200 dark:border-slate-700' },
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

function AngebotFormular({
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
  const [gueltigBis, setGueltigBis] = useState(initial?.gueltig_bis ?? inXTagen(30))
  const [notizen, setNotizen] = useState(initial?.notizen ?? '')
  const [paketId, setPaketId] = useState(initial?.dokumentenpaket_id?.toString() ?? '')
  const [eingabeModus, setEingabeModus] = useState<EingabeModus>('brutto')

  // Automatisch auf Netto wechseln wenn eine Firma (B2B) gewählt wird
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
    if (!gueltigBis) { setFehler('Gültig-bis-Datum ist erforderlich.'); return }
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
        gueltig_bis: gueltigBis,
        kunde_id: parseInt(kundeId),
        notizen: notizen || undefined,
        dokument_typ: 'Angebot' as const,
        dokumentenpaket_id: paketId ? parseInt(paketId) : undefined,
        ist_entwurf: istEntwurf,
        positionen: posPayload,
      }

      let result: Rechnung
      if (initial) {
        result = await updateRechnung(initial.id, payload)
      } else {
        result = await createRechnung(payload)
      }
      qc.invalidateQueries({ queryKey: ['angebote'] })
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
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Angebotsdatum</label>
          <input type="date" value={datum} onChange={e => setDatum(e.target.value)} className={inputCls} />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Gültig bis *</label>
          <input type="date" value={gueltigBis} onChange={e => setGueltigBis(e.target.value)} className={inputCls} required />
        </div>
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
          {laedt ? 'Speichern…' : initial ? '✓ Speichern' : '✓ Angebot erstellen'}
        </button>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Detail-Panel
// ---------------------------------------------------------------------------

function AngebotDetail({
  angebot,
  onEdit,
  onClose,
  onDelete,
}: {
  angebot: Rechnung
  onEdit: () => void
  onClose: () => void
  onDelete: () => void
}) {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [statusLaedt, setStatusLaedt] = useState(false)
  const [konvLaedt, setKonvLaedt] = useState(false)
  const [auftragLaedt, setAuftragLaedt] = useState(false)
  const [lsLaedt, setLsLaedt] = useState(false)
  const [pfLaedt, setPfLaedt] = useState(false)
  const hatBezug = !!(angebot.auftrag_zu_angebot_id || angebot.rechnung_zu_angebot_id || angebot.lieferschein_zu_angebot_id || angebot.proforma_zu_angebot_id)
  const [pdfLaedt, setPdfLaedt] = useState(false)
  const [zeigMailEingabe, setZeigMailEingabe] = useState(false)
  const [mailAdresse, setMailAdresse] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)
  const [finLaedt, setFinLaedt] = useState(false)

  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen, staleTime: 1000 * 60 * 5 })

  async function handleFinalisieren() {
    setFinLaedt(true)
    try {
      await updateRechnung(angebot.id, { ist_entwurf: false })
      qc.invalidateQueries({ queryKey: ['angebote'] })
    } catch (e: any) { setFehler(e?.message) }
    finally { setFinLaedt(false) }
  }

  async function fetchPdfBlob(): Promise<string> {
    const blob = await getRechnungPdf(angebot.id)
    return URL.createObjectURL(blob)
  }

  async function handlePdf() {
    setPdfLaedt(true)
    try {
      const blobUrl = await fetchPdfBlob()
      if (isTauri()) {
        openInPdfWindow(blobUrl, `Angebot ${angebot.rechnungsnummer ?? ''}`)
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
        openInPdfWindow(blobUrl, 'Angebot drucken')
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

    // PDF als Download bereitstellen
    setPdfLaedt(true)
    try {
      const base = await getApiBase()
      await openUrl(`${base}/rechnungen/${angebot.id}/pdf?download=1`)
    } finally { setPdfLaedt(false) }

    const datumDe = angebot.datum.split('-').reverse().join('.')
    const gueltigDe = angebot.gueltig_bis ? angebot.gueltig_bis.split('-').reverse().join('.') : '—'
    const kundeName = angebot.kunde_name ?? angebot.partner_freitext ?? ''
    const firmenname = unternehmen?.firmenname ?? [unternehmen?.vorname, unternehmen?.nachname].filter(Boolean).join(' ') ?? 'RechnungsFee'
    const brutto = (parseFloat(angebot.brutto_gesamt as any) || 0).toFixed(2).replace('.', ',')

    const subject = encodeURIComponent(`Angebot ${angebot.rechnungsnummer ?? ''} – ${firmenname}`)
    const body = encodeURIComponent(
      `Guten Tag ${kundeName},\n\nanbei finden Sie unser Angebot ${angebot.rechnungsnummer ?? ''} vom ${datumDe}.\n\nAngebotsbetrag: ${brutto} €\nGültig bis: ${gueltigDe}\n\nBitte fügen Sie die heruntergeladene PDF-Datei als Anhang hinzu.\n\nMit freundlichen Grüßen\n${firmenname}${unternehmen?.mail_signatur ? '\n\n' + unternehmen.mail_signatur : ''}`
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

  async function handleStatusChange(s: string) {
    setStatusLaedt(true)
    try {
      await angebotStatusSetzen(angebot.id, s)
      qc.invalidateQueries({ queryKey: ['angebote'] })
    } catch (e: any) { setFehler(e?.message) }
    finally { setStatusLaedt(false) }
  }

  async function handleAuftragErstellen() {
    setAuftragLaedt(true)
    try {
      const au = await auftragAusAngebot(angebot.id)
      qc.invalidateQueries({ queryKey: ['angebote'] })
      navigate(`/auftraege?id=${au.id}`)
    } catch (e: any) { setFehler(e?.message) }
    finally { setAuftragLaedt(false) }
  }

  async function handleRechnungErstellen() {
    setKonvLaedt(true)
    try {
      const re = await rechnungAusAngebot(angebot.id)
      qc.invalidateQueries({ queryKey: ['angebote'] })
      navigate(`/rechnungen?id=${re.id}`)
    } catch (e: any) { setFehler(e?.message) }
    finally { setKonvLaedt(false) }
  }

  async function handleLieferscheinErstellen() {
    setLsLaedt(true)
    try {
      const ls = await lieferscheinAusAngebot(angebot.id)
      qc.invalidateQueries({ queryKey: ['angebote'] })
      navigate(`/lieferscheine?id=${ls.id}`)
    } catch (e: any) { setFehler(e?.message) }
    finally { setLsLaedt(false) }
  }

  async function handleProformaErstellen() {
    setPfLaedt(true)
    try {
      const pf = await proformaAusAngebot(angebot.id)
      qc.invalidateQueries({ queryKey: ['angebote'] })
      navigate(`/proformas?id=${pf.id}`)
    } catch (e: any) { setFehler(e?.message) }
    finally { setPfLaedt(false) }
  }

  const brutto = parseFloat(angebot.brutto_gesamt as any) || 0

  const btnBase = 'flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
  const btnNeutral = `${btnBase} border-slate-300 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300`
  const btnGreen   = `${btnBase} border-green-300 dark:border-green-700 hover:bg-green-50 dark:hover:bg-green-950 text-green-700 dark:text-green-400 font-medium`
  const btnRed     = `${btnBase} border-red-200 dark:border-red-800 hover:bg-red-50 dark:hover:bg-red-950 text-red-600 dark:text-red-400`

  return (
    <div className="flex flex-col h-full">
      {/* Header – wie RechnungenPage */}
      <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between shrink-0">
        <div>
          <p className="font-semibold text-slate-800 dark:text-slate-100">{angebot.rechnungsnummer ?? '(keine Nummer)'}</p>
          <p className="text-xs text-slate-400 dark:text-slate-500">Angebot</p>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-xl">×</button>
      </div>

      {/* Inhalt */}
      <div className="p-5 space-y-5 flex-1 overflow-y-auto">

        {/* Entwurf-Banner */}
        {angebot.ist_entwurf && (
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

        {/* Aktionsleiste – direkt oben wie bei Rechnungen */}
        <div className="flex flex-wrap gap-2">
          <button onClick={handleDrucken} disabled={pdfLaedt || !!angebot.ist_entwurf} className={btnNeutral}>
            🖨️ Drucken
          </button>
          <button onClick={handlePdf} disabled={pdfLaedt || !!angebot.ist_entwurf} className={btnNeutral}>
            📄 {pdfLaedt ? 'Lädt…' : 'PDF öffnen'}
          </button>
          <button onClick={() => handleMail()} disabled={pdfLaedt || !!angebot.ist_entwurf} className={btnNeutral}>
            ✉️ Mail senden
          </button>
          <button onClick={onEdit} disabled={hatBezug}
            title={hatBezug ? 'Bereits ein Folgedokument vorhanden' : undefined}
            className={btnNeutral}>
            ✏️ Bearbeiten
          </button>
          {unternehmen?.auftraege_aktiv && (
            !angebot.auftrag_zu_angebot_id ? (
              <button
                onClick={handleAuftragErstellen}
                disabled={auftragLaedt || !!angebot.ist_entwurf || angebot.angebot_status !== 'akzeptiert' || hatBezug}
                title={
                  angebot.ist_entwurf ? 'Erst Entwurf finalisieren'
                  : angebot.angebot_status !== 'akzeptiert' ? 'Nur bei Status „Akzeptiert" möglich'
                  : hatBezug ? 'Bereits ein Folgedokument vorhanden'
                  : undefined
                }
                className={btnGreen}
              >
                {auftragLaedt ? '⏳ Erstelle…' : '→ Auftrag'}
              </button>
            ) : (
              <button onClick={() => navigate(`/auftraege?id=${angebot.auftrag_zu_angebot_id}`)} className={btnGreen}>
                → {angebot.auftrag_zu_angebot_nr ?? `AU #${angebot.auftrag_zu_angebot_id}`}
              </button>
            )
          )}
          {!angebot.rechnung_zu_angebot_id ? (
            <button
              onClick={handleRechnungErstellen}
              disabled={konvLaedt || !!angebot.ist_entwurf || hatBezug || angebot.angebot_status !== 'akzeptiert'}
              title={
                angebot.ist_entwurf ? 'Erst Entwurf finalisieren'
                : angebot.angebot_status !== 'akzeptiert' ? 'Nur bei Status „Akzeptiert" möglich'
                : hatBezug ? 'Bereits ein Folgedokument vorhanden'
                : undefined
              }
              className={btnGreen}
            >
              {konvLaedt ? '⏳ Erstelle…' : '→ Rechnung'}
            </button>
          ) : (
            <button onClick={() => navigate(`/rechnungen?id=${angebot.rechnung_zu_angebot_id}`)} className={btnGreen}>
              → {angebot.rechnung_zu_angebot_nr ?? `RE #${angebot.rechnung_zu_angebot_id}`}
            </button>
          )}
          {unternehmen?.lieferschein_aktiv && (
            !angebot.lieferschein_zu_angebot_id ? (
              <button
                onClick={handleLieferscheinErstellen}
                disabled={lsLaedt || !!angebot.ist_entwurf || hatBezug || angebot.angebot_status !== 'akzeptiert'}
                title={
                  angebot.ist_entwurf ? 'Erst Entwurf finalisieren'
                  : angebot.angebot_status !== 'akzeptiert' ? 'Nur bei Status „Akzeptiert" möglich'
                  : hatBezug ? 'Bereits ein Folgedokument vorhanden'
                  : undefined
                }
                className={btnGreen}
              >
                {lsLaedt ? '⏳ Erstelle…' : '→ Lieferschein'}
              </button>
            ) : (
              <button onClick={() => navigate(`/lieferscheine?id=${angebot.lieferschein_zu_angebot_id}`)} className={btnGreen}>
                → {angebot.lieferschein_zu_angebot_nr ?? `LS #${angebot.lieferschein_zu_angebot_id}`}
              </button>
            )
          )}
          {unternehmen?.proforma_aktiv && (
            !angebot.proforma_zu_angebot_id ? (
              <button
                onClick={handleProformaErstellen}
                disabled={pfLaedt || !!angebot.ist_entwurf || hatBezug || angebot.angebot_status !== 'akzeptiert'}
                title={
                  angebot.ist_entwurf ? 'Erst Entwurf finalisieren'
                  : angebot.angebot_status !== 'akzeptiert' ? 'Nur bei Status „Akzeptiert" möglich'
                  : hatBezug ? 'Bereits ein Folgedokument vorhanden'
                  : undefined
                }
                className={btnNeutral}
              >
                {pfLaedt ? '⏳ Erstelle…' : '→ Proforma'}
              </button>
            ) : (
              <button onClick={() => navigate(`/proformas?id=${angebot.proforma_zu_angebot_id}`)} className={btnNeutral}>
                → {angebot.proforma_zu_angebot_nr ?? `PRF #${angebot.proforma_zu_angebot_id}`}
              </button>
            )
          )}
          <button
            onClick={onDelete}
            disabled={!!(angebot.rechnung_zu_angebot_id || angebot.lieferschein_zu_angebot_id || angebot.proforma_zu_angebot_id || angebot.auftrag_zu_angebot_id)}
            title={angebot.rechnung_zu_angebot_id || angebot.lieferschein_zu_angebot_id || angebot.proforma_zu_angebot_id || angebot.auftrag_zu_angebot_id ? 'Nicht löschbar – Dokumente wurden aus diesem Angebot erstellt' : undefined}
            className={btnRed}
          >
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

        {/* Status-Umschalter */}
        {!angebot.rechnung_zu_angebot_id && (
          <div>
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1.5">Status</p>
            <div className="flex gap-1 flex-wrap">
              {(['offen', 'akzeptiert', 'abgelehnt', 'abgelaufen'] as const).map(s => (
                <button key={s} disabled={angebot.angebot_status === s || statusLaedt}
                  onClick={() => handleStatusChange(s)}
                  className={`px-2.5 py-1 text-xs rounded-lg border transition-colors disabled:opacity-50 ${
                    angebot.angebot_status === s
                      ? `${STATUS_LABEL[s].cls} font-medium`
                      : 'border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
                  }`}>
                  {STATUS_LABEL[s].label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Metadaten */}
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-500 dark:text-slate-400">Kunde</span>
            <span className="font-medium text-slate-800 dark:text-slate-100 text-right">{angebot.kunde_name ?? angebot.partner_freitext ?? '—'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500 dark:text-slate-400">Datum</span>
            <span className="text-slate-700 dark:text-slate-200">{formatDatum(angebot.datum)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500 dark:text-slate-400">Gültig bis</span>
            <span className={`font-medium ${angebot.gueltig_bis && angebot.gueltig_bis < heuteIso() && angebot.angebot_status === 'offen' ? 'text-red-600 dark:text-red-400' : 'text-slate-700 dark:text-slate-200'}`}>
              {formatDatum(angebot.gueltig_bis)}
            </span>
          </div>
        </div>

        {/* Positionen */}
        {angebot.positionen && angebot.positionen.length > 0 && (
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
                  {angebot.positionen.map((pos, i) => (
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

        {angebot.notizen && (
          <div>
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Notizen</p>
            <p className="text-sm text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2 whitespace-pre-wrap">{angebot.notizen}</p>
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

export function AngebotePage() {
  const qc = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [formModus, setFormModus] = useState<'neu' | 'bearbeiten' | null>(null)
  const [vorKundeId, setVorKundeId] = useState<string | null>(null)
  const [suche, setSuche] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  // ?kunde_id=X aus KundenPage → Formular direkt öffnen
  useEffect(() => {
    const kid = searchParams.get('kunde_id')
    if (kid) {
      setVorKundeId(kid)
      setFormModus('neu')
      setSearchParams({}, { replace: true })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const { data: angebote, isLoading } = useQuery({
    queryKey: ['angebote'],
    queryFn: getAngebote,
  })

  const deleteMut = useMutation({
    mutationFn: deleteRechnung,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['angebote'] }); setSelectedId(null) },
  })

  const selected = angebote?.find(a => a.id === selectedId) ?? null

  const angeboteGefiltert = (angebote ?? []).filter(a => {
    if (statusFilter) {
      if (statusFilter === 'entwurf' && !a.ist_entwurf) return false
      if (statusFilter !== 'entwurf' && (a.ist_entwurf || a.angebot_status !== statusFilter)) return false
    }
    if (suche) {
      const q = suche.toLowerCase()
      return (
        (a.rechnungsnummer ?? '').toLowerCase().includes(q) ||
        (a.kunde_name ?? a.partner_freitext ?? '').toLowerCase().includes(q)
      )
    }
    return true
  })

  const listContainerRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase()
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return
      if (formModus) return
      if (!angeboteGefiltert.length) return
      e.preventDefault()
      const idx = selectedId != null ? angeboteGefiltert.findIndex(a => a.id === selectedId) : -1
      const nextIdx = e.key === 'ArrowDown' ? Math.min(idx + 1, angeboteGefiltert.length - 1) : Math.max(idx - 1, 0)
      const next = angeboteGefiltert[nextIdx]
      if (!next) return
      setSelectedId(next.id)
      listContainerRef.current?.focus({ preventScroll: true })
      requestAnimationFrame(() => {
        listContainerRef.current?.querySelector(`[data-angebot-id="${next.id}"]`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
      })
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [angeboteGefiltert, selectedId, formModus])

  function handleDelete() {
    if (!selected) return
    if (!confirm(`Angebot ${selected.rechnungsnummer} wirklich löschen?`)) return
    deleteMut.mutate(selected.id)
  }

  return (
    <div className="flex h-full">
      {/* Liste – schrumpft auf 1/3 wenn Formular aktiv */}
      <div className={`${formModus ? 'w-1/3 min-w-[260px] shrink-0' : 'flex-1'} flex flex-col border-e border-slate-200 dark:border-slate-700 min-w-0 min-h-0 transition-all`}>
        {/* Header – bleibt beim Scrollen stehen */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 shrink-0">
          <div className="flex items-center justify-between gap-3 mb-3">
            <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Angebote</h1>
            <button
              onClick={() => { setFormModus('neu'); setSelectedId(null) }}
              className="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-xl"
            >
              + Neues Angebot
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
              <option value="akzeptiert">Akzeptiert</option>
              <option value="abgelehnt">Abgelehnt</option>
              <option value="abgelaufen">Abgelaufen</option>
              <option value="entwurf">Entwurf</option>
            </select>
          </div>
        </div>

        {/* Kennzahlen – bleibt beim Scrollen stehen */}
        {(angebote?.length ?? 0) > 0 && (
          <div className="px-6 py-3 grid grid-cols-3 gap-3 border-b border-slate-100 dark:border-slate-800 shrink-0">
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Angebote</p>
              <p className="text-lg font-bold text-slate-800 dark:text-slate-100">{angebote!.length}</p>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Offen</p>
              <p className="text-lg font-bold text-blue-600 dark:text-blue-400">
                {angebote!.filter(a => !a.ist_entwurf && a.angebot_status === 'offen').length}
              </p>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Akzeptiert</p>
              <p className="text-lg font-bold text-green-600 dark:text-green-400">
                {angebote!.filter(a => !a.ist_entwurf && a.angebot_status === 'akzeptiert').length}
              </p>
            </div>
          </div>
        )}

        {/* Tabelle */}
        <div ref={listContainerRef} tabIndex={0} className="flex-1 overflow-y-auto focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 dark:focus-visible:ring-blue-500 focus-visible:ring-offset-2 rounded-sm">
          {isLoading ? (
            <div className="p-6 animate-pulse space-y-2">
              {[1, 2, 3].map(i => <div key={i} className="h-12 bg-slate-100 dark:bg-slate-800 rounded" />)}
            </div>
          ) : !angebote?.length ? (
            <div className="p-10 text-center">
              <p className="text-slate-500 dark:text-slate-400">Noch keine Angebote vorhanden.</p>
              <p className="text-slate-400 dark:text-slate-500 text-sm mt-1">Klicke auf „+ Neues Angebot" um zu starten.</p>
            </div>
          ) : angeboteGefiltert.length === 0 ? (
            <div className="p-10 text-center">
              <p className="text-slate-500 dark:text-slate-400">Keine Angebote für diese Filter.</p>
              <button onClick={() => { setSuche(''); setStatusFilter('') }} className="mt-2 text-sm text-blue-600 hover:underline">Filter zurücksetzen</button>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800">
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Datum</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Nummer</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Gültig bis</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Kunde</th>
                  <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Brutto</th>
                  <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Status</th>
                </tr>
              </thead>
              <tbody>
                {angeboteGefiltert.map(a => (
                  <tr
                    key={a.id}
                    data-angebot-id={a.id}
                    onClick={() => { setSelectedId(a.id); setFormModus(null) }}
                    className={`border-b border-slate-50 dark:border-slate-700 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-700 cursor-pointer transition-colors ${
                      selectedId === a.id ? 'bg-blue-50 dark:bg-slate-600 border-l-2 border-l-blue-500' : ''
                    }`}
                  >
                    <td className="px-5 py-3 text-slate-500 dark:text-slate-400">{formatDatum(a.datum)}</td>
                    <td className="px-5 py-3 font-mono text-xs text-slate-400 dark:text-slate-500">{a.rechnungsnummer}</td>
                    <td className={`px-5 py-3 font-medium ${a.gueltig_bis && a.gueltig_bis < heuteIso() && a.angebot_status === 'offen' ? 'text-red-600 dark:text-red-400' : 'text-slate-500 dark:text-slate-400'}`}>
                      {formatDatum(a.gueltig_bis)}
                    </td>
                    <td className="px-5 py-3 text-slate-700 dark:text-slate-200">{a.kunde_name ?? a.partner_freitext ?? '—'}</td>
                    <td className="px-5 py-3 text-right text-slate-700 dark:text-slate-200">
                      {(parseFloat(a.brutto_gesamt as any) || 0).toFixed(2).replace('.', ',')} €
                    </td>
                    <td className="px-5 py-3 text-center">
                      {a.ist_entwurf
                        ? <span className="inline-block text-xs font-medium px-2 py-0.5 rounded border bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800">Entwurf</span>
                        : <StatusBadge status={a.angebot_status} />}
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
              {formModus === 'bearbeiten' ? 'Angebot bearbeiten' : 'Neues Angebot'}
            </h3>
            <button type="button" onClick={() => { setFormModus(null); setVorKundeId(null) }}
              className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-xl">×</button>
          </div>
          <div className="p-6">
            <AngebotFormular
              initial={formModus === 'bearbeiten' && selected ? selected : undefined}
              vorKundeId={formModus === 'neu' ? (vorKundeId ?? undefined) : undefined}
              onSpeichern={(id) => { setFormModus(null); setSelectedId(id); setVorKundeId(null) }}
              onAbbrechen={() => { setFormModus(null); setVorKundeId(null) }}
            />
          </div>
        </div>
      )}
      {selected && !formModus && (
        <div className="w-80 shrink-0 border-l border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col">
          <AngebotDetail
            angebot={selected}
            onEdit={() => setFormModus('bearbeiten')}
            onClose={() => setSelectedId(null)}
            onDelete={handleDelete}
          />
        </div>
      )}
    </div>
  )
}
