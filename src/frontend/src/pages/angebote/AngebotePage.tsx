import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  getAngebote, getKunden, getUstSaetze, getDokumentenPakete, getUnternehmen,
  createRechnung, updateRechnung, deleteRechnung,
  rechnungAusAngebot, lieferscheinAusAngebot, angebotStatusSetzen,
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
  positionen, onChange, ustSaetze, defaultSatz, onArtikelWahl, eingabeModus, onModusWechsel,
}: {
  positionen: Pos[]
  onChange: (p: Pos[]) => void
  ustSaetze: { satz: string }[]
  defaultSatz: string
  onArtikelWahl: (i: number, a: ArtikelSuche) => void
  eingabeModus: EingabeModus
  onModusWechsel: (m: EingabeModus) => void
}) {
  function update(i: number, field: keyof Pos, val: string) {
    const neu = positionen.map((p, idx) => idx === i ? { ...p, [field]: val } : p)
    onChange(neu)
  }

  const gesamt = positionen.reduce((acc, p) => {
    const { netto, ustBet, brutto } = berechnePos(p, eingabeModus)
    return { netto: acc.netto + netto, ust: acc.ust + ustBet, brutto: acc.brutto + brutto }
  }, { netto: 0, ust: 0, brutto: 0 })

  return (
    <div className="space-y-2">
      {/* Brutto/Netto-Toggle */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-500 dark:text-slate-400">Preiseingabe:</span>
        <div className="flex rounded-lg border border-slate-300 dark:border-slate-600 overflow-hidden text-xs">
          {(['brutto', 'netto'] as EingabeModus[]).map(m => (
            <button key={m} type="button"
              onClick={() => onModusWechsel(m)}
              className={`px-3 py-1 transition-colors ${eingabeModus === m ? 'bg-blue-600 text-white' : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'}`}>
              {m === 'brutto' ? 'Brutto (inkl. USt)' : 'Netto (zzgl. USt)'}
            </button>
          ))}
        </div>
      </div>

      <div className="hidden sm:grid grid-cols-[1fr_80px_80px_110px_80px_32px] gap-2 px-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
        <span>Beschreibung</span><span>Menge</span><span>Einheit</span>
        <span>{eingabeModus === 'brutto' ? 'Bruttopreis' : 'Nettopreis'}</span>
        <span>USt %</span><span />
      </div>

      {positionen.map((pos, i) => (
        <div key={i} className="grid grid-cols-[1fr_80px_80px_110px_80px_32px] gap-2 items-center">
          <ArtikelAutocomplete
            value={pos.beschreibung}
            onChange={v => update(i, 'beschreibung', v)}
            onArtikelWahl={a => onArtikelWahl(i, a)}
            placeholder="Beschreibung oder Artikel suchen"
          />
          <input value={pos.menge} onChange={e => update(i, 'menge', e.target.value)}
            type="number" min="0" step="0.01" className={inputCls} />
          <input value={pos.einheit} onChange={e => update(i, 'einheit', e.target.value)}
            placeholder="Stk." className={inputCls} />
          <input value={pos.einzelpreis} onChange={e => update(i, 'einzelpreis', e.target.value)}
            type="number" step="0.01" min="0" placeholder="0,00" className={inputCls} />
          <select value={pos.ust_satz} onChange={e => update(i, 'ust_satz', e.target.value)}
            className={selectCls}>
            {ustSaetze.map(u => (
              <option key={u.satz} value={u.satz}>{u.satz} %</option>
            ))}
          </select>
          <button type="button" onClick={() => onChange(positionen.filter((_, idx) => idx !== i))}
            disabled={positionen.length === 1}
            className="text-red-400 hover:text-red-600 disabled:opacity-20 text-lg leading-none">×</button>
        </div>
      ))}

      <button type="button" onClick={() => onChange([...positionen, { ...leerePos(), ust_satz: defaultSatz }])}
        className="text-sm text-blue-600 hover:underline dark:text-blue-400">
        + Position hinzufügen
      </button>

      <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700 text-sm space-y-1">
        <div className="flex justify-between text-slate-500 dark:text-slate-400">
          <span>Netto</span><span>{gesamt.netto.toFixed(2).replace('.', ',')} €</span>
        </div>
        <div className="flex justify-between text-slate-500 dark:text-slate-400">
          <span>USt</span><span>{gesamt.ust.toFixed(2).replace('.', ',')} €</span>
        </div>
        <div className="flex justify-between font-semibold text-slate-800 dark:text-slate-100">
          <span>Brutto</span><span>{gesamt.brutto.toFixed(2).replace('.', ',')} €</span>
        </div>
      </div>
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
        einzelpreis: String(p.einzelpreis),
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

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!kundeId) { setFehler('Bitte einen Kunden wählen.'); return }
    if (!gueltigBis) { setFehler('Gültig-bis-Datum ist erforderlich.'); return }
    if (positionen.some(p => !p.beschreibung.trim())) { setFehler('Alle Positionen benötigen eine Beschreibung.'); return }

    setLaedt(true)
    setFehler(null)
    try {
      const posPayload = positionen.map((p, i) => {
        const nettoEinzel = nettoProStueck(p, eingabeModus)
        return {
          beschreibung: p.beschreibung.trim(),
          menge: parseFloat(p.menge) || 1,
          einheit: p.einheit || 'Stk.',
          netto: nettoEinzel,           // Netto pro Einheit – Backend berechnet Gesamt
          ust_satz: parseFloat(p.ust_satz) || 0,
          position: i + 1,
          artikel_id: p.artikel_id,
        }
      })

      const payload = {
        typ: 'ausgang' as const,
        datum,
        gueltig_bis: gueltigBis,
        kunde_id: parseInt(kundeId),
        notizen: notizen || undefined,
        dokument_typ: 'Angebot',
        dokumentenpaket_id: paketId ? parseInt(paketId) : undefined,
        ist_entwurf: false,
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
    <form onSubmit={submit} className="space-y-5 p-6">
      <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
        {initial ? 'Angebot bearbeiten' : 'Neues Angebot'}
      </h2>

      <div className="grid grid-cols-2 gap-4">
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
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Angebotsdatum</label>
          <input type="date" value={datum} onChange={e => setDatum(e.target.value)} className={inputCls} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Gültig bis *</label>
          <input type="date" value={gueltigBis} onChange={e => setGueltigBis(e.target.value)} className={inputCls} required />
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
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">Positionen</label>
        <PositionenTabelle
          positionen={positionen}
          onChange={setPositionen}
          ustSaetze={ustSaetzeListe}
          defaultSatz={defaultSatz}
          onArtikelWahl={fillPositionFromArtikel}
          eingabeModus={eingabeModus}
          onModusWechsel={setEingabeModus}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Notizen</label>
        <textarea value={notizen} onChange={e => setNotizen(e.target.value)}
          rows={3} className={`${inputCls} resize-none`}
          placeholder="Interne Notizen oder Text für die Fußzeile" />
      </div>

      {fehler && <p className="text-sm text-red-600">{fehler}</p>}

      <div className="flex gap-2 pt-1">
        <button type="submit" disabled={laedt}
          className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg disabled:opacity-50">
          {laedt ? 'Speichern…' : initial ? 'Speichern' : 'Angebot erstellen'}
        </button>
        <button type="button" onClick={onAbbrechen}
          className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
          Abbrechen
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
  const [lsLaedt, setLsLaedt] = useState(false)
  const [pdfLaedt, setPdfLaedt] = useState(false)
  const [zeigMailEingabe, setZeigMailEingabe] = useState(false)
  const [mailAdresse, setMailAdresse] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)

  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen, staleTime: 1000 * 60 * 5 })

  const partnerEmail = angebot.kunde_name
    ? undefined  // wird aus Kundenstamm-Daten geladen – hier Fallback auf mailAdresse
    : undefined

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

  async function handleRechnungErstellen() {
    if (!confirm('Rechnung aus diesem Angebot erstellen?')) return
    setKonvLaedt(true)
    try {
      const re = await rechnungAusAngebot(angebot.id)
      qc.invalidateQueries({ queryKey: ['angebote'] })
      navigate(`/rechnungen?id=${re.id}`)
    } catch (e: any) { setFehler(e?.message) }
    finally { setKonvLaedt(false) }
  }

  async function handleLieferscheinErstellen() {
    if (!confirm('Lieferschein aus diesem Angebot erstellen?')) return
    setLsLaedt(true)
    try {
      const ls = await lieferscheinAusAngebot(angebot.id)
      qc.invalidateQueries({ queryKey: ['angebote'] })
      navigate(`/lieferscheine?id=${ls.id}`)
    } catch (e: any) { setFehler(e?.message) }
    finally { setLsLaedt(false) }
  }

  const brutto = parseFloat(angebot.brutto_gesamt as any) || 0

  const btnBase = 'flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg transition-colors'
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

        {/* Aktionsleiste – direkt oben wie bei Rechnungen */}
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
          {!angebot.rechnung_zu_angebot_id ? (
            <button onClick={handleRechnungErstellen} disabled={konvLaedt} className={btnGreen}>
              {konvLaedt ? '⏳ Erstelle…' : '→ Rechnung'}
            </button>
          ) : (
            <button onClick={() => navigate(`/rechnungen?id=${angebot.rechnung_zu_angebot_id}`)} className={btnGreen}>
              → {angebot.rechnung_zu_angebot_nr ?? `RE #${angebot.rechnung_zu_angebot_id}`}
            </button>
          )}
          {unternehmen?.lieferschein_aktiv && (
            <button onClick={handleLieferscheinErstellen} disabled={lsLaedt} className={btnGreen}>
              {lsLaedt ? '⏳ Erstelle…' : '→ Lieferschein'}
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
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-xs text-slate-400 dark:text-slate-500">Kunde</p>
            <p className="font-medium text-slate-700 dark:text-slate-200">{angebot.kunde_name ?? angebot.partner_freitext ?? '—'}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400 dark:text-slate-500">Betrag (Brutto)</p>
            <p className="font-bold text-slate-800 dark:text-slate-100">{brutto.toFixed(2).replace('.', ',')} €</p>
          </div>
          <div>
            <p className="text-xs text-slate-400 dark:text-slate-500">Datum</p>
            <p className="text-slate-700 dark:text-slate-200">{formatDatum(angebot.datum)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400 dark:text-slate-500">Gültig bis</p>
            <p className={`font-medium ${angebot.gueltig_bis && angebot.gueltig_bis < heuteIso() && angebot.angebot_status === 'offen' ? 'text-red-600 dark:text-red-400' : 'text-slate-700 dark:text-slate-200'}`}>
              {formatDatum(angebot.gueltig_bis)}
            </p>
          </div>
        </div>

        {/* Positionen */}
        <div>
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">Positionen</p>
          <div className="space-y-1">
            {angebot.positionen?.map((pos, i) => (
              <div key={i} className="flex justify-between text-sm border-b border-slate-50 dark:border-slate-700 last:border-0 py-1">
                <span className="text-slate-700 dark:text-slate-200 truncate flex-1 mr-2">
                  {pos.menge}× {pos.beschreibung}
                </span>
                <span className="text-slate-500 dark:text-slate-400 shrink-0">
                  {(parseFloat(pos.brutto_gesamt as any) || 0).toFixed(2).replace('.', ',')} €
                </span>
              </div>
            ))}
          </div>
        </div>

        {angebot.notizen && (
          <div>
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Notizen</p>
            <p className="text-sm text-slate-600 dark:text-slate-300 whitespace-pre-wrap">{angebot.notizen}</p>
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

  function handleDelete() {
    if (!selected) return
    if (!confirm(`Angebot ${selected.rechnungsnummer} wirklich löschen?`)) return
    deleteMut.mutate(selected.id)
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* Liste */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between shrink-0">
          <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Angebote</h1>
          <button
            onClick={() => { setFormModus('neu'); setSelectedId(null) }}
            className="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-xl"
          >
            + Neues Angebot
          </button>
        </div>

        {/* Formular */}
        {formModus && (
          <div className="border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-y-auto max-h-[60vh]">
            <AngebotFormular
              initial={formModus === 'bearbeiten' && selected ? selected : undefined}
              vorKundeId={formModus === 'neu' ? (vorKundeId ?? undefined) : undefined}
              onSpeichern={(id) => { setFormModus(null); setSelectedId(id); setVorKundeId(null) }}
              onAbbrechen={() => { setFormModus(null); setVorKundeId(null) }}
            />
          </div>
        )}

        {/* Tabelle */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="p-6 animate-pulse space-y-2">
              {[1, 2, 3].map(i => <div key={i} className="h-12 bg-slate-100 dark:bg-slate-800 rounded" />)}
            </div>
          ) : !angebote?.length ? (
            <div className="p-10 text-center">
              <p className="text-slate-500 dark:text-slate-400">Noch keine Angebote vorhanden.</p>
              <p className="text-slate-400 dark:text-slate-500 text-sm mt-1">Klicke auf „+ Neues Angebot" um zu starten.</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800">
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Nummer</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Datum</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Gültig bis</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Kunde</th>
                  <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Brutto</th>
                  <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Status</th>
                </tr>
              </thead>
              <tbody>
                {angebote.map(a => (
                  <tr
                    key={a.id}
                    onClick={() => { setSelectedId(a.id); setFormModus(null) }}
                    className={`border-b border-slate-50 dark:border-slate-700 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-700 cursor-pointer transition-colors ${
                      selectedId === a.id ? 'bg-blue-50 dark:bg-slate-600 border-l-2 border-l-blue-500' : ''
                    }`}
                  >
                    <td className="px-5 py-3 font-mono text-xs text-slate-400 dark:text-slate-500">{a.rechnungsnummer}</td>
                    <td className="px-5 py-3 text-slate-500 dark:text-slate-400">{formatDatum(a.datum)}</td>
                    <td className={`px-5 py-3 font-medium ${a.gueltig_bis && a.gueltig_bis < heuteIso() && a.angebot_status === 'offen' ? 'text-red-600 dark:text-red-400' : 'text-slate-500 dark:text-slate-400'}`}>
                      {formatDatum(a.gueltig_bis)}
                    </td>
                    <td className="px-5 py-3 text-slate-700 dark:text-slate-200">{a.kunde_name ?? a.partner_freitext ?? '—'}</td>
                    <td className="px-5 py-3 text-right text-slate-700 dark:text-slate-200">
                      {(parseFloat(a.brutto_gesamt as any) || 0).toFixed(2).replace('.', ',')} €
                    </td>
                    <td className="px-5 py-3 text-center"><StatusBadge status={a.angebot_status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Detail-Panel */}
      {selected && !formModus && (
        <div className="w-80 shrink-0 border-l border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-hidden flex flex-col">
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
