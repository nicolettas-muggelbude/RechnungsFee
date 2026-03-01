import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getRechnungen, createRechnung, updateRechnung, deleteRechnung, barZahlungErstellen,
  stornoRechnung, finalisiereRechnung, markiereRechnungAusgegeben, getRechnungPdf,
  getKunden, getLieferanten, getKategorien, getUnternehmen,
  type Rechnung, type RechnungCreate, type RechnungspositionCreate, type BarZahlungCreate,
  type Unternehmen,
} from '../../api/client'

// ---------------------------------------------------------------------------
// Hilfsfunktionen
// ---------------------------------------------------------------------------

function formatEuro(val: string | number): string {
  const n = typeof val === 'string' ? parseFloat(val) : val
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n)
}

function formatDatum(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

function heuteIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function aktuellerMonat(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

// ---------------------------------------------------------------------------
// Druck-/PDF-Logik
// ---------------------------------------------------------------------------

function rechnungHtml(r: Rechnung, u: Unternehmen | null | undefined, istKopie = false): string {
  const isoZuDe = (iso: string) => iso.split('-').reverse().join('.')
  const partner = r.typ === 'ausgang'
    ? (r.kunde_name ?? r.partner_freitext ?? '—')
    : (r.lieferant_name ?? r.partner_freitext ?? '—')

  const absenderName = u
    ? [u.firmenname, u.vorname, u.nachname].filter(Boolean).join(' ')
    : 'RechnungsFee'
  const absenderAdresse = u
    ? `${u.strasse} ${u.hausnummer}, ${u.plz} ${u.ort}`
    : ''
  const steuernrZeile = u?.steuernummer ? `StNr: ${u.steuernummer}` : ''
  const ustIdZeile = u?.ust_idnr ? `USt-IdNr: ${u.ust_idnr}` : ''

  const leistungsDatum = r.leistungsdatum && r.leistungsdatum !== r.datum
    ? `<tr><td class="lbl">Leistungsdatum</td><td>${isoZuDe(r.leistungsdatum)}</td></tr>`
    : ''
  const faelligZeile = r.faellig_am
    ? `<tr><td class="lbl">Fällig am</td><td>${isoZuDe(r.faellig_am)}</td></tr>`
    : ''
  const steuerHinweis = u?.ist_kleinunternehmer
    ? '<p style="margin-top:12px;font-size:12px;color:#64748b">Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.</p>'
    : ''

  const posZeilen = r.positionen.map((p) => {
    const mengeStr = parseFloat(p.menge) !== 1 ? ` × ${p.menge} ${p.einheit}` : ''
    return `<tr>
      <td>${p.beschreibung}${mengeStr}</td>
      <td class="r">${formatEuro(p.netto)}</td>
      <td class="r">${p.ust_satz} %</td>
      <td class="r bold">${formatEuro(p.brutto)}</td>
    </tr>`
  }).join('')

  const kopiBanner = istKopie
    ? `<div style="background:#dc2626;color:#fff;text-align:center;padding:10px;font-size:20px;font-weight:bold;letter-spacing:8px;margin-bottom:24px;border-radius:4px;">KOPIE</div>`
    : ''

  return `<!DOCTYPE html><html><head>
  <meta charset="utf-8">
  <title>${istKopie ? 'KOPIE – ' : ''}${r.rechnungsnummer ?? 'Rechnung'}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 40px; color: #1e293b; font-size: 14px; }
    .header { display: flex; justify-content: space-between; margin-bottom: 32px; }
    .absender { font-size: 13px; line-height: 1.6; }
    .absender strong { font-size: 15px; }
    .metatable { font-size: 13px; border-collapse: collapse; }
    .metatable td { padding: 2px 8px 2px 0; }
    .metatable td.lbl { color: #64748b; }
    h1 { font-size: 20px; margin: 24px 0 4px; }
    .empfaenger { font-size: 13px; margin-bottom: 24px; color: #475569; }
    table.pos { width: 100%; border-collapse: collapse; margin-top: 8px; }
    th { background: #f8fafc; text-align: left; padding: 8px; font-size: 13px; color: #64748b; border-bottom: 1px solid #e2e8f0; }
    th.r, td.r { text-align: right; }
    td { padding: 8px; border-bottom: 1px solid #f1f5f9; }
    .bold { font-weight: bold; }
    .total td { border-top: 2px solid #e2e8f0; font-weight: bold; font-size: 15px; padding-top: 10px; }
    .footer { margin-top: 48px; font-size: 11px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 8px; }
  </style>
  </head><body>
  ${kopiBanner}
  <div class="header">
    <div class="absender">
      <strong>${absenderName}</strong><br>
      ${absenderAdresse ? absenderAdresse + '<br>' : ''}
      ${steuernrZeile ? steuernrZeile + '<br>' : ''}
      ${ustIdZeile || ''}
    </div>
    <table class="metatable">
      <tr><td class="lbl">${r.typ === 'ausgang' ? 'Rechnungsnummer' : 'Eingangsrechnung'}</td><td>${r.rechnungsnummer ?? '—'}</td></tr>
      <tr><td class="lbl">Rechnungsdatum</td><td>${isoZuDe(r.datum)}</td></tr>
      ${leistungsDatum}
      ${faelligZeile}
    </table>
  </div>
  <div class="empfaenger"><strong>${r.typ === 'ausgang' ? 'Rechnungsempfänger' : 'Lieferant'}:</strong> ${partner}</div>
  <h1>${r.typ === 'ausgang' ? 'Rechnung' : 'Eingangsrechnung'}</h1>
  <table class="pos">
    <thead><tr>
      <th>Beschreibung</th>
      <th class="r">Netto</th>
      <th class="r">USt</th>
      <th class="r">Brutto</th>
    </tr></thead>
    <tbody>${posZeilen}</tbody>
    <tfoot>
      <tr class="total">
        <td colspan="3">Gesamtbetrag</td>
        <td class="r">${formatEuro(r.brutto_gesamt)}</td>
      </tr>
    </tfoot>
  </table>
  ${steuerHinweis}
  ${r.notizen ? `<p style="margin-top:16px;font-size:13px;color:#64748b">Notizen: ${r.notizen}</p>` : ''}
  <div class="footer">Erstellt mit RechnungsFee &nbsp;·&nbsp; ${new Date().toLocaleDateString('de-DE')}</div>
  </body></html>`
}

function oeffneRechnungFenster(r: Rechnung, drucken: boolean, u?: Unternehmen | null, istKopie = false) {
  const win = window.open('', '_blank', 'width=720,height=900')
  if (!win) return
  win.document.write(rechnungHtml(r, u, istKopie))
  win.document.close()
  win.focus()
  if (drucken) win.print()
}

// ---------------------------------------------------------------------------
// Status-Badge
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: 'offen' | 'teilweise' | 'bezahlt' }) {
  const cfg = {
    offen:     { cls: 'bg-red-50 text-red-700 border-red-200',    label: 'Offen' },
    teilweise: { cls: 'bg-amber-50 text-amber-700 border-amber-200', label: 'Teilweise' },
    bezahlt:   { cls: 'bg-green-50 text-green-700 border-green-200', label: 'Bezahlt' },
  }[status]
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${cfg.cls}`}>
      {cfg.label}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Zahlungs-Dialog
// ---------------------------------------------------------------------------

function ZahlungsDialog({
  rechnung,
  onClose,
  onSuccess,
}: {
  rechnung: Rechnung
  onClose: () => void
  onSuccess: () => void
}) {
  const qc = useQueryClient()
  const restbetrag = parseFloat(rechnung.brutto_gesamt) - parseFloat(rechnung.bezahlt_betrag)
  const [betrag, setBetrag] = useState(restbetrag.toFixed(2).replace('.', ','))
  const [datum, setDatum] = useState(heuteIso())
  const [zahlungsart, setZahlungsart] = useState<'Bar' | 'Karte' | 'PayPal' | 'Bank'>('Bar')
  const [beschreibung, setBeschreibung] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: (data: BarZahlungCreate) => barZahlungErstellen(rechnung.id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
      qc.invalidateQueries({ queryKey: ['kassenbuch'] })
      onSuccess()
    },
    onError: (e: Error) => setFehler(e.message),
  })

  const betragDecimal = parseFloat(betrag.replace(',', '.'))
  const artLabel = rechnung.typ === 'ausgang' ? 'Einnahme' : 'Ausgabe'

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (isNaN(betragDecimal) || betragDecimal <= 0) {
      setFehler('Bitte einen gültigen Betrag eingeben.')
      return
    }
    mutation.mutate({
      betrag: betragDecimal.toFixed(2),
      datum,
      zahlungsart,
      beschreibung: beschreibung || undefined,
    })
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">
            {rechnung.typ === 'ausgang' ? 'Zahlung kassieren' : 'Zahlung buchen'}
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl">×</button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Rechnungsinfo */}
          <div className="bg-slate-50 rounded-xl p-3 text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-500">Rechnung</span>
              <span className="font-medium">{rechnung.rechnungsnummer}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Gesamt</span>
              <span className="font-medium">{formatEuro(rechnung.brutto_gesamt)}</span>
            </div>
            {parseFloat(rechnung.bezahlt_betrag) > 0 && (
              <div className="flex justify-between text-green-700">
                <span>Bereits bezahlt</span>
                <span>{formatEuro(rechnung.bezahlt_betrag)}</span>
              </div>
            )}
            <div className="flex justify-between font-semibold border-t border-slate-200 pt-1 mt-1">
              <span className="text-slate-600">Restbetrag</span>
              <span>{formatEuro(restbetrag)}</span>
            </div>
          </div>

          {/* Betrag */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Betrag (€)</label>
            <input
              type="text"
              value={betrag}
              onChange={(e) => setBetrag(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="0,00"
            />
          </div>

          {/* Datum */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Zahlungsdatum</label>
            <input
              type="date"
              value={datum}
              onChange={(e) => setDatum(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Zahlungsart */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Zahlungsart</label>
            <div className="flex rounded-lg border border-slate-300 overflow-hidden text-sm">
              {([['Bar', 'Bar'], ['Karte', 'Karte'], ['PayPal', 'PayPal'], ['Bank', 'Überw.']] as const).map(([val, label]) => (
                <button
                  key={val}
                  type="button"
                  onClick={() => setZahlungsart(val)}
                  className={`flex-1 py-2 transition-colors ${
                    zahlungsart === val
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Beschreibung (optional) */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Beschreibung <span className="text-slate-400 font-normal">(optional)</span>
            </label>
            <input
              type="text"
              value={beschreibung}
              onChange={(e) => setBeschreibung(e.target.value)}
              placeholder={`Zahlung ${rechnung.rechnungsnummer ?? ''}`}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Vorschau */}
          {!isNaN(betragDecimal) && betragDecimal > 0 && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 text-sm">
              <p className="text-blue-700 font-medium">Kassenbuchung wird erstellt:</p>
              <p className="text-blue-600 mt-0.5">
                {artLabel} {formatEuro(betragDecimal)} via {zahlungsart === 'Bank' ? 'Überweisung' : zahlungsart}
              </p>
            </div>
          )}

          {fehler && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {fehler}
            </p>
          )}

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50"
            >
              Abbrechen
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="flex-1 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {mutation.isPending ? 'Wird gebucht…' : 'Bestätigen'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Rechnungs-Detail
// ---------------------------------------------------------------------------

function RechnungDetail({
  rechnung,
  onClose,
  onEdit,
  onDelete,
}: {
  rechnung: Rechnung
  onClose: () => void
  onEdit: () => void
  onDelete: () => void
}) {
  const [zahlungsDialog, setZahlungsDialog] = useState(false)
  const [zeigStornoEingabe, setZeigStornoEingabe] = useState(false)
  const [zeigMailEingabe, setZeigMailEingabe] = useState(false)
  const [mailAdresse, setMailAdresse] = useState('')
  const [pdfLaeuft, setPdfLaeuft] = useState(false)
  const [pdfHinweis, setPdfHinweis] = useState(false)
  const qc = useQueryClient()
  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen, staleTime: 1000 * 60 * 10 })

  const restbetrag = parseFloat(rechnung.brutto_gesamt) - parseFloat(rechnung.bezahlt_betrag)
  const fortschritt = parseFloat(rechnung.brutto_gesamt) > 0
    ? Math.min((parseFloat(rechnung.bezahlt_betrag) / parseFloat(rechnung.brutto_gesamt)) * 100, 100)
    : 0

  const hatZahlungsoption = restbetrag > 0.004 && !rechnung.storniert && !rechnung.ist_entwurf

  const partnerEmail = rechnung.typ === 'ausgang'
    ? rechnung.kunde_email
    : rechnung.lieferant_email

  const stornoMutation = useMutation({
    mutationFn: () => stornoRechnung(rechnung.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
      setZeigStornoEingabe(false)
    },
  })

  const finalisiereMutation = useMutation({
    mutationFn: () => finalisiereRechnung(rechnung.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rechnungen'] }),
  })

  const markiereAusgegebenMutation = useMutation({
    mutationFn: () => markiereRechnungAusgegeben(rechnung.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rechnungen'] }),
  })

  // Beim ersten Druck/Öffnen/Mail: Rechnung als "ausgegeben" markieren
  function _markiereWennNoetig() {
    if (!rechnung.ist_entwurf && !rechnung.ausgegeben) {
      markiereAusgegebenMutation.mutate()
    }
  }

  function handleDrucken() {
    const istKopie = !rechnung.ist_entwurf && rechnung.ausgegeben
    oeffneRechnungFenster(rechnung, true, unternehmen, istKopie)
    _markiereWennNoetig()
  }

  function handlePdfOeffnen() {
    const istKopie = !rechnung.ist_entwurf && rechnung.ausgegeben
    oeffneRechnungFenster(rechnung, false, unternehmen, istKopie)
    _markiereWennNoetig()
  }

  async function handleMail() {
    const email = partnerEmail || mailAdresse.trim()
    if (!email) { setZeigMailEingabe(true); return }

    // PDF vom Backend laden und herunterladen
    setPdfLaeuft(true)
    setPdfHinweis(false)
    try {
      const blob = await getRechnungPdf(rechnung.id)
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = `Rechnung_${rechnung.rechnungsnummer ?? rechnung.id}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      setPdfHinweis(true)
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
    } catch {
      // PDF-Fehler: trotzdem mailto öffnen
    } finally {
      setPdfLaeuft(false)
    }

    // Platzhalter-Werte bestimmen
    const datumDe = rechnung.datum.split('-').reverse().join('.')
    const faelligDe = rechnung.faellig_am ? rechnung.faellig_am.split('-').reverse().join('.') : '—'
    const kundeName = rechnung.kunde_name ?? rechnung.lieferant_name ?? rechnung.partner_freitext ?? ''
    const firmenname = unternehmen?.firmenname ?? 'RechnungsFee'

    function ersetze(vorlage: string): string {
      return vorlage
        .replace(/\{rechnungsnummer\}/g, rechnung.rechnungsnummer ?? '—')
        .replace(/\{datum\}/g, datumDe)
        .replace(/\{betrag\}/g, formatEuro(rechnung.brutto_gesamt))
        .replace(/\{faellig_am\}/g, faelligDe)
        .replace(/\{kunde\}/g, kundeName)
        .replace(/\{firmenname\}/g, firmenname)
    }

    // Betreff aus Vorlage oder Fallback
    const betreffVorlage = unternehmen?.mail_betreff_vorlage ?? 'Rechnung {rechnungsnummer}'
    const subjectText = ersetze(betreffVorlage)

    // Text aus Vorlage oder Fallback
    const standardText = `Anbei die Rechnung vom ${datumDe}.\n\nRechnungsnr.: ${rechnung.rechnungsnummer ?? '—'}\nBetrag: ${formatEuro(rechnung.brutto_gesamt)}\n\nBitte die beigefügte PDF-Datei als Anhang einfügen.`
    const textVorlage = unternehmen?.mail_text_vorlage ?? standardText
    let bodyText = ersetze(textVorlage)

    // Signatur anhängen
    if (unternehmen?.mail_signatur) {
      bodyText += `\n\n${unternehmen.mail_signatur}`
    }

    // mailto öffnen (PDF-Anhang muss manuell hinzugefügt werden)
    const subject = encodeURIComponent(subjectText)
    const body    = encodeURIComponent(bodyText)
    window.open(`mailto:${email}?subject=${subject}&body=${body}`)
    setZeigMailEingabe(false)
    setMailAdresse('')
  }

  return (
    <div className="border-l border-slate-200 bg-white h-full overflow-auto flex flex-col">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <p className="font-semibold text-slate-800">{rechnung.rechnungsnummer ?? '(keine Nummer)'}</p>
          <p className="text-xs text-slate-400">{rechnung.typ === 'ausgang' ? 'Ausgangsrechnung' : 'Eingangsrechnung'}</p>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl">×</button>
      </div>

      <div className="p-5 space-y-5 flex-1">

        {/* Aktionsleiste */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleDrucken}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 rounded-lg hover:bg-slate-50 text-slate-600"
          >
            🖨️ {!rechnung.ist_entwurf && rechnung.ausgegeben ? 'Kopie drucken' : 'Drucken'}
          </button>
          <button
            onClick={handlePdfOeffnen}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 rounded-lg hover:bg-slate-50 text-slate-600"
          >
            📄 {!rechnung.ist_entwurf && rechnung.ausgegeben ? 'Kopie öffnen' : 'PDF öffnen'}
          </button>
          {!rechnung.storniert && (
            <button
              onClick={handleMail}
              disabled={pdfLaeuft}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 rounded-lg hover:bg-slate-50 text-slate-600 disabled:opacity-50"
            >
              {pdfLaeuft ? '⏳ PDF…' : `✉️ Mail senden${!partnerEmail ? ' …' : ''}`}
            </button>
          )}
          {!rechnung.ist_entwurf && !rechnung.storniert && !zeigStornoEingabe && (
            <button
              onClick={() => setZeigStornoEingabe(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-red-200 rounded-lg hover:bg-red-50 text-red-600"
            >
              ✕ Stornieren
            </button>
          )}
          {rechnung.storniert && (
            <span className="self-center text-xs text-slate-400 italic">Storniert</span>
          )}
        </div>

        {/* Mail-Eingabe */}
        {zeigMailEingabe && (
          <div className="flex gap-2 items-center">
            <input
              type="email"
              value={mailAdresse}
              onChange={(e) => setMailAdresse(e.target.value)}
              placeholder="E-Mail-Adresse eingeben…"
              className="flex-1 border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              autoFocus
              onKeyDown={(e) => e.key === 'Enter' && handleMail()}
            />
            <button
              onClick={handleMail}
              disabled={!mailAdresse.trim()}
              className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              Öffnen
            </button>
            <button
              onClick={() => { setZeigMailEingabe(false); setMailAdresse('') }}
              className="px-3 py-1.5 border border-slate-300 text-slate-600 rounded-lg text-sm hover:bg-slate-50"
            >
              Abbrechen
            </button>
          </div>
        )}

        {/* PDF-Hinweis nach Mail-Versand */}
        {pdfHinweis && (
          <div className="flex items-start gap-2 bg-blue-50 border border-blue-200 rounded-xl px-3 py-2 text-sm text-blue-800">
            <span className="mt-0.5 shrink-0">📎</span>
            <span className="flex-1">
              PDF wurde gespeichert. Bitte die Datei als Anhang in dein E-Mail-Programm einfügen.
            </span>
            <button onClick={() => setPdfHinweis(false)} className="text-blue-400 hover:text-blue-600 shrink-0">×</button>
          </div>
        )}

        {/* Storno-Bestätigung */}
        {zeigStornoEingabe && (
          <div className="flex gap-2 items-center bg-red-50 border border-red-200 rounded-xl px-3 py-2">
            <span className="text-sm text-red-700 flex-1">
              Rechnung wirklich stornieren? Dies ist nicht rückgängig zu machen.
              {rechnung.zahlungen.length > 0 && (
                <span className="block mt-0.5 text-xs text-red-600">
                  Es werden {rechnung.zahlungen.length} Gegenbuchung{rechnung.zahlungen.length !== 1 ? 'en' : ''} im Kassenbuch erstellt.
                </span>
              )}
            </span>
            <button
              onClick={() => stornoMutation.mutate()}
              disabled={stornoMutation.isPending}
              className="px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700 disabled:opacity-50"
            >
              {stornoMutation.isPending ? '…' : 'Bestätigen'}
            </button>
            <button
              onClick={() => setZeigStornoEingabe(false)}
              className="px-3 py-1.5 border border-slate-300 text-slate-600 rounded-lg text-sm hover:bg-slate-50"
            >
              Abbrechen
            </button>
          </div>
        )}
        {stornoMutation.isError && (
          <p className="text-red-600 text-xs">{(stornoMutation.error as Error).message}</p>
        )}

        {/* Entwurf-Banner */}
        {rechnung.ist_entwurf && (
          <div className="flex items-center justify-between gap-2 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2">
            <span className="text-sm text-amber-800">📝 <strong>Entwurf</strong> – noch nicht finalisiert</span>
            <button
              onClick={() => finalisiereMutation.mutate()}
              disabled={finalisiereMutation.isPending}
              className="px-3 py-1 text-xs font-medium bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 shrink-0"
            >
              {finalisiereMutation.isPending ? '…' : 'Finalisieren'}
            </button>
          </div>
        )}

        {/* Stammdaten */}
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-500">Partner</span>
            <span className="text-right font-medium text-slate-800">
              {rechnung.typ === 'ausgang'
                ? (rechnung.kunde_name ?? rechnung.partner_freitext ?? '—')
                : (rechnung.lieferant_name ?? rechnung.partner_freitext ?? '—')}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Rechnungsdatum</span>
            <span>{formatDatum(rechnung.datum)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Leistungsdatum</span>
            <span>{rechnung.leistungsdatum ? formatDatum(rechnung.leistungsdatum) : formatDatum(rechnung.datum)}</span>
          </div>
          {rechnung.faellig_am && (
            <div className="flex justify-between">
              <span className="text-slate-500">Fällig am</span>
              <span className={
                rechnung.zahlungsstatus !== 'bezahlt' && rechnung.faellig_am < heuteIso()
                  ? 'text-red-600 font-medium'
                  : ''
              }>{formatDatum(rechnung.faellig_am)}</span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-slate-500">Status</span>
            <StatusBadge status={rechnung.zahlungsstatus} />
          </div>
        </div>

        {/* Positionen */}
        {rechnung.positionen.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Positionen</p>
            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <table className="w-full text-xs">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-slate-500 font-medium">Beschreibung</th>
                    <th className="px-3 py-2 text-right text-slate-500 font-medium">Netto</th>
                    <th className="px-3 py-2 text-right text-slate-500 font-medium">USt</th>
                    <th className="px-3 py-2 text-right text-slate-500 font-medium">Brutto</th>
                  </tr>
                </thead>
                <tbody>
                  {rechnung.positionen.map((pos) => (
                    <tr key={pos.id} className="border-t border-slate-100">
                      <td className="px-3 py-2 text-slate-700">
                        {pos.beschreibung}
                        {parseFloat(pos.menge) !== 1 && (
                          <span className="text-slate-400"> × {pos.menge} {pos.einheit}</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right">{formatEuro(pos.netto)}</td>
                      <td className="px-3 py-2 text-right text-slate-400">{pos.ust_satz}%</td>
                      <td className="px-3 py-2 text-right font-medium">{formatEuro(pos.brutto)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-slate-50 border-t border-slate-200">
                  <tr>
                    <td colSpan={3} className="px-3 py-2 text-right text-slate-500 font-medium">Gesamt</td>
                    <td className="px-3 py-2 text-right font-bold text-slate-800">{formatEuro(rechnung.brutto_gesamt)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}

        {/* Zahlungsstatus */}
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Zahlung</p>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">Bezahlt</span>
              <span className="font-medium">{formatEuro(rechnung.bezahlt_betrag)}</span>
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  rechnung.zahlungsstatus === 'bezahlt'
                    ? 'bg-green-500'
                    : rechnung.zahlungsstatus === 'teilweise'
                    ? 'bg-amber-400'
                    : 'bg-slate-300'
                }`}
                style={{ width: `${fortschritt}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-slate-400">
              <span>0 €</span>
              <span>{formatEuro(rechnung.brutto_gesamt)}</span>
            </div>
          </div>
        </div>

        {/* Verknüpfte Zahlungen */}
        {rechnung.zahlungen.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              Verknüpfte Kassenbuchungen
            </p>
            <div className="space-y-1">
              {rechnung.zahlungen.map((z) => (
                <div key={z.id} className="flex items-center justify-between text-sm bg-slate-50 rounded-lg px-3 py-2">
                  <div>
                    <span className="font-mono text-xs text-slate-400 mr-2">{z.belegnr}</span>
                    <span className="text-slate-600">{formatDatum(z.datum)}</span>
                    <span className="ml-1.5 text-xs text-slate-400">{z.zahlungsart}</span>
                  </div>
                  <span className={`font-medium ${z.art === 'Einnahme' ? 'text-green-600' : 'text-red-600'}`}>
                    {z.art === 'Ausgabe' ? '−' : '+'}{formatEuro(z.brutto_betrag)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {rechnung.notizen && (
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Notizen</p>
            <p className="text-sm text-slate-600 bg-slate-50 rounded-lg px-3 py-2">{rechnung.notizen}</p>
          </div>
        )}
      </div>

      {/* Aktionen */}
      <div className="p-5 border-t border-slate-100 space-y-2">
        {hatZahlungsoption && (
          <button
            onClick={() => setZahlungsDialog(true)}
            className="w-full py-2.5 text-sm font-medium bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors"
          >
            {rechnung.typ === 'ausgang' ? 'Zahlung kassieren' : 'Zahlung buchen'}
            {rechnung.zahlungsstatus === 'teilweise' && ` (Restbetrag ${formatEuro(restbetrag)})`}
          </button>
        )}
        {rechnung.ist_entwurf && (
          <>
            <button
              onClick={onEdit}
              className="w-full py-2 text-sm border border-slate-300 rounded-xl hover:bg-slate-50 transition-colors"
            >
              Bearbeiten
            </button>
            <button
              onClick={onDelete}
              className="w-full py-2 text-sm text-red-600 border border-red-200 rounded-xl hover:bg-red-50 transition-colors"
            >
              Entwurf löschen
            </button>
          </>
        )}
      </div>

      {zahlungsDialog && (
        <ZahlungsDialog
          rechnung={rechnung}
          onClose={() => setZahlungsDialog(false)}
          onSuccess={() => setZahlungsDialog(false)}
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Einheit-Combo (Select + Freitext-Fallback)
// ---------------------------------------------------------------------------

const EINHEITEN = ['Stück', 'Pack', 'Set', 'Lizenz', 'Stunde', 'Tag', 'Monat', 'Pauschal', 'km', 'm²']

function EinheitZelle({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const istBekannt = EINHEITEN.includes(value)
  const [freitext, setFreitext] = useState(!istBekannt)

  // Wenn der Wert von außen auf einen bekannten zurückgesetzt wird (z.B. Formular-Reset)
  useEffect(() => {
    if (EINHEITEN.includes(value)) setFreitext(false)
  }, [value])

  if (freitext) {
    return (
      <div className="flex items-center gap-0.5">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full border-0 outline-none bg-transparent text-slate-700 min-w-0"
          placeholder="Einheit"
        />
        <button
          type="button"
          title="Zur Liste zurück"
          onClick={() => { setFreitext(false); onChange('Stück') }}
          className="text-slate-300 hover:text-slate-500 shrink-0 leading-none"
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
        if (e.target.value === '__freitext__') {
          setFreitext(true)
          onChange('')
        } else {
          onChange(e.target.value)
        }
      }}
      className="w-full border-0 outline-none bg-transparent text-slate-700 cursor-pointer"
    >
      {EINHEITEN.map((e) => <option key={e} value={e}>{e}</option>)}
      <option value="__freitext__">Freitext…</option>
    </select>
  )
}


// ---------------------------------------------------------------------------
// Stammdaten-Combobox (Autocomplete mit Freitext-Fallback)
// ---------------------------------------------------------------------------

function StammdatenCombobox({
  items,
  selectedId,
  freitext,
  onChange,
  placeholder = 'Suchen oder frei eingeben…',
}: {
  items: { id: number; label: string }[]
  selectedId: number | null
  freitext: string
  onChange: (id: number | null, freitext: string) => void
  placeholder?: string
}) {
  const [query, setQuery] = useState(() => {
    if (selectedId != null) {
      return items.find((i) => i.id === selectedId)?.label ?? ''
    }
    return freitext
  })
  const [offen, setOffen] = useState(false)
  const [highlightIdx, setHighlightIdx] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Wenn selectedId / freitext von außen geändert wird (z.B. Formular-Reset)
  useEffect(() => {
    if (selectedId != null) {
      const label = items.find((i) => i.id === selectedId)?.label ?? ''
      setQuery(label)
    } else {
      setQuery(freitext)
    }
  }, [selectedId, freitext, items])

  // Außen-Klick schließt Dropdown
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOffen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const q = query.trim()
  const gefiltert = q === ''
    ? []
    : items.filter((i) => i.label.toLowerCase().includes(q.toLowerCase())).slice(0, 50)

  const mehrVorhanden = q !== '' &&
    items.filter((i) => i.label.toLowerCase().includes(q.toLowerCase())).length > 50

  function handleInputChange(v: string) {
    setQuery(v)
    setOffen(v.trim() !== '')
    setHighlightIdx(0)
    // Freitext-Modus: kein Stammdatensatz ausgewählt
    onChange(null, v)
  }

  function handleSelect(item: { id: number; label: string }) {
    setQuery(item.label)
    setOffen(false)
    onChange(item.id, '')
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!offen) {
      if ((e.key === 'ArrowDown' || e.key === 'Enter') && query.trim()) {
        setOffen(true)
        e.preventDefault()
      }
      return
    }
    if (e.key === 'ArrowDown') {
      setHighlightIdx((i) => Math.min(i + 1, gefiltert.length - 1))
      e.preventDefault()
    } else if (e.key === 'ArrowUp') {
      setHighlightIdx((i) => Math.max(i - 1, 0))
      e.preventDefault()
    } else if (e.key === 'Enter') {
      if (gefiltert[highlightIdx]) {
        handleSelect(gefiltert[highlightIdx])
      }
      e.preventDefault()
    } else if (e.key === 'Escape') {
      setOffen(false)
    }
  }

  function handleBlur() {
    // Kleines Delay damit onClick im Dropdown noch feuert
    setTimeout(() => setOffen(false), 150)
  }

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => handleInputChange(e.target.value)}
          onFocus={() => { if (query.trim()) setOffen(true) }}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full border border-slate-300 rounded-lg px-3 py-2 pr-20 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {selectedId != null && (
          <span className="absolute right-8 top-1/2 -translate-y-1/2 text-xs text-green-600 font-medium whitespace-nowrap">
            ✓ Stammdaten
          </span>
        )}
        {query.trim() && (
          <button
            type="button"
            tabIndex={-1}
            onClick={() => { setOffen((o) => !o); inputRef.current?.focus() }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs"
          >
            {offen ? '▲' : '▼'}
          </button>
        )}
      </div>

      {offen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-slate-200 rounded-xl shadow-lg max-h-64 overflow-y-auto">
          {gefiltert.length === 0 ? (
            <div className="px-3 py-2.5 text-sm text-slate-400 italic">
              Kein Treffer – wird als Freitext übernommen
            </div>
          ) : (
            <>
              {gefiltert.map((item, idx) => (
                <button
                  key={item.id}
                  type="button"
                  onMouseDown={() => handleSelect(item)}
                  onMouseEnter={() => setHighlightIdx(idx)}
                  className={`w-full text-left px-3 py-2 text-sm transition-colors ${
                    idx === highlightIdx
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  {item.label}
                </button>
              ))}
              {mehrVorhanden && (
                <div className="px-3 py-2 text-xs text-slate-400 border-t border-slate-100 bg-slate-50">
                  Weitere Treffer – Suche verfeinern
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}


// ---------------------------------------------------------------------------
// Rechnungs-Formular
// ---------------------------------------------------------------------------

type Positionszeile = {
  beschreibung: string
  menge: string
  einheit: string
  netto: string
  ust_satz: string
}

const leerPosition = (defaultUst = '19'): Positionszeile => ({
  beschreibung: '',
  menge: '1',
  einheit: '',
  netto: '',
  ust_satz: defaultUst,
})

function RechnungForm({
  typ,
  initial,
  onSave,
  onCancel,
}: {
  typ: 'eingang' | 'ausgang'
  initial?: Rechnung
  onSave: (data: RechnungCreate) => void
  onCancel: () => void
}) {
  const { data: kunden } = useQuery({ queryKey: ['kunden'], queryFn: getKunden })
  const { data: lieferanten } = useQuery({ queryKey: ['lieferanten'], queryFn: getLieferanten })
  const { data: kategorien } = useQuery({ queryKey: ['kategorien'], queryFn: getKategorien })
  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen, staleTime: 1000 * 60 * 10 })

  const istKleinunternehmer = unternehmen?.ist_kleinunternehmer ?? false

  const [rechnungsnummer, setRechnungsnummer] = useState(initial?.rechnungsnummer ?? '')
  const [datum, setDatum] = useState(initial?.datum ?? heuteIso())
  const [leistungsdatum, setLeistungsdatum] = useState(initial?.leistungsdatum ?? initial?.datum ?? heuteIso())
  const [leistungsdatumManuell, setLeistungsdatumManuell] = useState(
    !!(initial?.leistungsdatum && initial.leistungsdatum !== initial.datum)
  )
  const [faelligAm, setFaelligAm] = useState(initial?.faellig_am ?? '')
  const [partnerId, setPartnerId] = useState<string>(
    typ === 'ausgang'
      ? String(initial?.kunde_id ?? '')
      : String(initial?.lieferant_id ?? '')
  )
  const [partnerFreitext, setPartnerFreitext] = useState(initial?.partner_freitext ?? '')
  const [kategorieId, setKategorieId] = useState<string>(String(initial?.kategorie_id ?? ''))
  const [notizen, setNotizen] = useState(initial?.notizen ?? '')
  const [positionen, setPositionen] = useState<Positionszeile[]>(
    initial?.positionen?.map((p) => ({
      beschreibung: p.beschreibung,
      menge: p.menge,
      einheit: p.einheit,
      netto: p.netto,
      ust_satz: p.ust_satz,
    })) ?? [leerPosition()]
  )
  const [eingabeModus, setEingabeModus] = useState<'netto' | 'brutto'>('brutto')

  const partnerListe = typ === 'ausgang' ? (kunden ?? []) : (lieferanten ?? [])

  // Default-Kategorie vorwählen (nur neue Rechnung, nicht beim Bearbeiten)
  useEffect(() => {
    if (!kategorien || initial) return
    if (typ === 'ausgang') {
      const defaultName = istKleinunternehmer ? 'Kleinunternehmer-Einnahmen' : 'Betriebseinnahmen'
      const kat = kategorien.find((k) => k.name === defaultName)
      if (kat) setKategorieId(String(kat.id))
    }
    // Eingang: keine Default-Kategorie (zu vielfältig)
  }, [kategorien, istKleinunternehmer, typ, initial])

  // Leistungsdatum synchron mit Rechnungsdatum halten (solange nicht manuell geändert)
  useEffect(() => {
    if (!leistungsdatumManuell) setLeistungsdatum(datum)
  }, [datum, leistungsdatumManuell])

  // USt-Satz aller Positionen aus gewählter Kategorie ableiten
  useEffect(() => {
    if (!kategorieId || !kategorien) return
    const kat = kategorien.find((k) => String(k.id) === kategorieId)
    if (!kat) return
    const neuerUst = istKleinunternehmer ? '0' : String(kat.ust_satz_standard)
    setPositionen((prev) => prev.map((p) => ({ ...p, ust_satz: neuerUst })))
  }, [kategorieId, kategorien, istKleinunternehmer])

  // Kategorie-Gruppen analog BuchungForm
  const alle = kategorien ?? []
  const erloeseKat = alle.filter(
    (k) =>
      k.kontenart === 'Erlös' &&
      (istKleinunternehmer
        ? k.name === 'Kleinunternehmer-Einnahmen'
        : k.name !== 'Kleinunternehmer-Einnahmen')
  )
  const aufwandKat = alle.filter((k) => k.kontenart === 'Aufwand')
  const anlageKat  = alle.filter((k) => k.kontenart === 'Anlage')

  const kategorieOptionen = typ === 'ausgang' ? (
    <>
      <optgroup label="Erlöse">
        {erloeseKat.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
      </optgroup>
    </>
  ) : (
    <>
      <optgroup label="Betriebsausgaben">
        {aufwandKat.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
      </optgroup>
      {anlageKat.length > 0 && (
        <optgroup label="Investitionen">
          {anlageKat.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
        </optgroup>
      )}
    </>
  )

  // Summenberechnung — reagiert auf eingabeModus
  const summen = positionen.reduce(
    (acc, p) => {
      const eingabe = parseFloat(p.netto.replace(',', '.')) || 0
      const menge = parseFloat(p.menge.replace(',', '.')) || 1
      const ust = parseFloat(p.ust_satz) || 0
      let netto: number, ustBetrag: number, brutto: number
      if (eingabeModus === 'brutto') {
        brutto = eingabe * menge
        netto = ust > 0 ? (brutto * 100) / (100 + ust) : brutto
        ustBetrag = brutto - netto
      } else {
        netto = eingabe * menge
        ustBetrag = (netto * ust) / 100
        brutto = netto + ustBetrag
      }
      return { netto: acc.netto + netto, ust: acc.ust + ustBetrag, brutto: acc.brutto + brutto }
    },
    { netto: 0, ust: 0, brutto: 0 }
  )

  function toggleEingabeModus() {
    setEingabeModus((prev) => {
      const naechster = prev === 'netto' ? 'brutto' : 'netto'
      setPositionen((ps) =>
        ps.map((p) => {
          const val = parseFloat(p.netto.replace(',', '.'))
          if (isNaN(val) || val === 0) return { ...p }
          const ust = parseFloat(p.ust_satz) || 0
          if (prev === 'netto') {
            // netto → brutto
            const neuerWert = ust > 0 ? val * (1 + ust / 100) : val
            return { ...p, netto: neuerWert.toFixed(2) }
          } else {
            // brutto → netto
            const neuerWert = ust > 0 ? (val * 100) / (100 + ust) : val
            return { ...p, netto: neuerWert.toFixed(2) }
          }
        })
      )
      return naechster
    })
  }

  function updatePosition(i: number, field: keyof Positionszeile, value: string) {
    setPositionen((prev) => prev.map((p, idx) => (idx === i ? { ...p, [field]: value } : p)))
  }

  function addPosition() {
    const kat = (kategorien ?? []).find((k) => String(k.id) === kategorieId)
    const defaultUst = istKleinunternehmer ? '0' : (kat ? String(kat.ust_satz_standard) : '19')
    setPositionen((prev) => [...prev, leerPosition(defaultUst)])
  }

  function removePosition(i: number) {
    if (positionen.length <= 1) return
    setPositionen((prev) => prev.filter((_, idx) => idx !== i))
  }

  function buildData(istEntwurf: boolean): RechnungCreate {
    return {
      typ,
      rechnungsnummer: rechnungsnummer || undefined,
      datum,
      leistungsdatum: leistungsdatum !== datum ? leistungsdatum : undefined,
      faellig_am: faelligAm || undefined,
      ...(typ === 'ausgang' ? { kunde_id: partnerId ? parseInt(partnerId) : undefined } : { lieferant_id: partnerId ? parseInt(partnerId) : undefined }),
      partner_freitext: partnerFreitext || undefined,
      kategorie_id: kategorieId ? parseInt(kategorieId) : undefined,
      notizen: notizen || undefined,
      ist_entwurf: istEntwurf,
      positionen: positionen.map((p) => {
        const eingabe = parseFloat(p.netto.replace(',', '.')) || 0
        const ust = parseFloat(p.ust_satz) || 0
        const ust_satz = istKleinunternehmer ? '0' : (p.ust_satz || '0')
        const netto = eingabeModus === 'brutto' && ust > 0 ? (eingabe * 100) / (100 + ust) : eingabe
        return {
          beschreibung: p.beschreibung,
          menge: p.menge || '1',
          einheit: p.einheit || 'Stück',
          netto: netto.toFixed(2),
          ust_satz,
        } as RechnungspositionCreate
      }),
    }
  }

  function handleSubmit(e: React.FormEvent, istEntwurf: boolean) {
    e.preventDefault()
    if (typ === 'ausgang' && !partnerId && !partnerFreitext.trim()) {
      alert('Bitte einen Kunden auswählen oder einen Namen im Freitext-Feld eingeben.')
      return
    }
    if (positionen.every((p) => !p.beschreibung.trim())) {
      alert('Bitte mindestens eine Position mit Beschreibung eingeben.')
      return
    }
    onSave(buildData(istEntwurf))
  }

  return (
    <form onSubmit={(e) => e.preventDefault()} className="space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Rechnungsnummer <span className="text-slate-400 font-normal">(leer = auto)</span>
          </label>
          <input
            type="text"
            value={rechnungsnummer}
            onChange={(e) => setRechnungsnummer(e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="wird automatisch vergeben"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Rechnungsdatum *</label>
          <input
            type="date"
            required
            value={datum}
            onChange={(e) => setDatum(e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Leistungsdatum
            {!leistungsdatumManuell && <span className="text-slate-400 font-normal ml-1">(= Rechnungsdatum)</span>}
          </label>
          <input
            type="date"
            value={leistungsdatum}
            onChange={(e) => {
              setLeistungsdatum(e.target.value)
              setLeistungsdatumManuell(e.target.value !== datum)
            }}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Fällig am</label>
          <input
            type="date"
            value={faelligAm}
            min={datum}
            onChange={(e) => setFaelligAm(e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Kategorie</label>
        <select
          value={kategorieId}
          onChange={(e) => setKategorieId(e.target.value)}
          className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">— keine —</option>
          {kategorieOptionen}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          {typ === 'ausgang' ? 'Kunde' : 'Lieferant'}
        </label>
        <StammdatenCombobox
          items={partnerListe.map((p: any) => ({
            id: p.id as number,
            label: p.firmenname ?? [p.vorname, p.nachname].filter(Boolean).join(' '),
          }))}
          selectedId={partnerId ? parseInt(partnerId) : null}
          freitext={partnerFreitext}
          onChange={(id, text) => {
            setPartnerId(id != null ? String(id) : '')
            setPartnerFreitext(text)
          }}
          placeholder={
            typ === 'ausgang'
              ? 'Kunde suchen oder frei eingeben…'
              : 'Lieferant suchen oder frei eingeben…'
          }
        />
      </div>

      {/* §19-Hinweis */}
      {istKleinunternehmer && (
        <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs text-amber-800">
          <span className="mt-0.5">ℹ️</span>
          <span>
            <strong>Kleinunternehmer §19 UStG</strong> – Keine Umsatzsteuer ausgewiesen.
            USt-Satz ist gesperrt.
          </span>
        </div>
      )}

      {/* Positionen */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-slate-700">Positionen *</label>
          <div className="flex items-center gap-3">
            {!istKleinunternehmer && (
              <button
                type="button"
                onClick={toggleEingabeModus}
                className="text-xs text-blue-600 hover:text-blue-700 underline"
              >
                {eingabeModus === 'netto' ? 'Brutto eingeben' : 'Netto eingeben'}
              </button>
            )}
            <button
              type="button"
              onClick={addPosition}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium"
            >
              + Position hinzufügen
            </button>
          </div>
        </div>
        <div className="border border-slate-200 rounded-xl overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-3 py-2 text-left text-slate-500 font-medium">Beschreibung</th>
                <th className="px-3 py-2 text-right text-slate-500 font-medium w-16">Menge</th>
                <th className="px-3 py-2 text-left text-slate-500 font-medium w-20">Einheit</th>
                <th className="px-3 py-2 text-right text-slate-500 font-medium w-24">
                  {eingabeModus === 'netto' ? 'Netto (€)' : 'Brutto (€)'}
                </th>
                <th className="px-3 py-2 text-right text-slate-500 font-medium w-16">USt %</th>
                <th className="px-3 py-2 w-8"></th>
              </tr>
            </thead>
            <tbody>
              {positionen.map((pos, i) => (
                <tr key={i} className="border-t border-slate-100">
                  <td className="px-2 py-1.5">
                    <input
                      required
                      type="text"
                      value={pos.beschreibung}
                      onChange={(e) => updatePosition(i, 'beschreibung', e.target.value)}
                      className="w-full border-0 outline-none bg-transparent text-slate-700 placeholder-slate-300"
                      placeholder="Beschreibung"
                    />
                  </td>
                  <td className="px-2 py-1.5">
                    <input
                      type="text"
                      value={pos.menge}
                      onChange={(e) => updatePosition(i, 'menge', e.target.value)}
                      className="w-full border-0 outline-none bg-transparent text-right text-slate-700"
                    />
                  </td>
                  <td className="px-2 py-1.5">
                    <EinheitZelle
                      value={pos.einheit}
                      onChange={(v) => updatePosition(i, 'einheit', v)}
                    />
                  </td>
                  <td className="px-2 py-1.5">
                    <input
                      required
                      type="text"
                      value={pos.netto}
                      onChange={(e) => updatePosition(i, 'netto', e.target.value)}
                      className="w-full border-0 outline-none bg-transparent text-right text-slate-700"
                      placeholder="0,00"
                    />
                  </td>
                  <td className="px-2 py-1.5">
                    <select
                      value={pos.ust_satz}
                      onChange={(e) => updatePosition(i, 'ust_satz', e.target.value)}
                      disabled={istKleinunternehmer}
                      className="w-full border-0 outline-none bg-transparent text-right text-slate-700 disabled:text-slate-400 disabled:cursor-not-allowed"
                    >
                      <option value="0">{istKleinunternehmer ? '0 (§19)' : '0'}</option>
                      {!istKleinunternehmer && <option value="7">7</option>}
                      {!istKleinunternehmer && <option value="19">19</option>}
                    </select>
                  </td>
                  <td className="px-2 py-1.5 text-center">
                    {positionen.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removePosition(i)}
                        className="text-slate-300 hover:text-red-500 text-base leading-none"
                      >
                        ×
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-slate-50 border-t border-slate-200">
              <tr>
                <td colSpan={4} className="px-3 py-2 text-right text-slate-500 text-xs">
                  Netto{eingabeModus === 'brutto' && <span className="text-slate-400"> (berechnet)</span>}
                </td>
                <td colSpan={2} className="px-3 py-2 text-right font-medium text-slate-700">{formatEuro(summen.netto)}</td>
              </tr>
              <tr>
                <td colSpan={4} className="px-3 py-2 text-right text-slate-500 text-xs">USt</td>
                <td colSpan={2} className="px-3 py-2 text-right text-slate-600">{formatEuro(summen.ust)}</td>
              </tr>
              <tr>
                <td colSpan={4} className="px-3 py-2 text-right font-semibold text-slate-700">
                  Brutto{eingabeModus === 'netto' && <span className="text-slate-400 font-normal"> (berechnet)</span>}
                </td>
                <td colSpan={2} className="px-3 py-2 text-right font-bold text-slate-800">{formatEuro(summen.brutto)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Notizen</label>
        <textarea
          value={notizen}
          onChange={(e) => setNotizen(e.target.value)}
          rows={2}
          className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          placeholder="Optionale Bemerkungen"
        />
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50"
        >
          Abbrechen
        </button>
        <button
          type="button"
          onClick={(e) => handleSubmit(e, true)}
          className="flex-1 px-4 py-2 text-sm border border-slate-300 bg-white text-slate-700 rounded-lg hover:bg-slate-50"
        >
          📝 Entwurf speichern
        </button>
        <button
          type="button"
          onClick={(e) => handleSubmit(e, false)}
          className="flex-1 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          ✓ {initial ? 'Speichern & Finalisieren' : 'Finalisieren'}
        </button>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Haupt-Seite
// ---------------------------------------------------------------------------

type FilterModus = 'monat' | 'datum' | 'zeitraum'

export function RechnungenPage() {
  const qc = useQueryClient()
  const [typ, setTyp] = useState<'eingang' | 'ausgang'>('ausgang')
  const [zahlungsstatus, setZahlungsstatus] = useState('')
  const [filterModus, setFilterModus] = useState<FilterModus>('monat')
  const [monat, setMonat] = useState(aktuellerMonat())
  const [datum, setDatum] = useState(heuteIso())
  const [datumVon, setDatumVon] = useState(heuteIso())
  const [datumBis, setDatumBis] = useState(heuteIso())
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [formModus, setFormModus] = useState<'neu' | 'bearbeiten' | null>(null)
  const [fehler, setFehler] = useState<string | null>(null)

  const filterParams =
    filterModus === 'monat'
      ? { monat }
      : filterModus === 'datum'
        ? { datum_von: datum, datum_bis: datum }
        : { datum_von: datumVon, datum_bis: datumBis }

  const { data: rechnungen, isLoading } = useQuery({
    queryKey: ['rechnungen', typ, zahlungsstatus, filterModus, monat, datum, datumVon, datumBis],
    queryFn: () => getRechnungen({ typ, zahlungsstatus: zahlungsstatus || undefined, ...filterParams }),
  })

  const selectedRechnung = rechnungen?.find((r) => r.id === selectedId) ?? null

  const createMutation = useMutation({
    mutationFn: createRechnung,
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
      setFormModus(null)
      setSelectedId(r.id)
      setFehler(null)
    },
    onError: (e: Error) => setFehler(e.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => updateRechnung(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
      setFormModus(null)
      setFehler(null)
    },
    onError: (e: Error) => setFehler(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteRechnung,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
      setSelectedId(null)
      setFehler(null)
    },
    onError: (e: Error) => setFehler(e.message),
  })

  const liste = rechnungen ?? []

  // Summen
  const gesamt = liste.reduce(
    (acc, r) => ({
      brutto: acc.brutto + parseFloat(r.brutto_gesamt),
      bezahlt: acc.bezahlt + parseFloat(r.bezahlt_betrag),
    }),
    { brutto: 0, bezahlt: 0 }
  )

  return (
    <div className="flex h-full">
      {/* Linke Spalte */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="p-6 pb-4">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <h2 className="text-2xl font-bold text-slate-800">Rechnungen</h2>
            <button
              onClick={() => { setFormModus('neu'); setSelectedId(null) }}
              className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors"
            >
              + Neue Rechnung
            </button>
          </div>

          {/* Tabs + Filter */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Eingang/Ausgang */}
            <div className="flex rounded-lg border border-slate-300 overflow-hidden text-sm">
              {(['ausgang', 'eingang'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => { setTyp(t); setSelectedId(null) }}
                  className={`px-4 py-1.5 transition-colors ${
                    typ === t ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {t === 'ausgang' ? 'Ausgang' : 'Eingang'}
                </button>
              ))}
            </div>

            {/* Zeitraum-Modus */}
            <div className="flex rounded-lg border border-slate-300 overflow-hidden text-sm">
              {(['monat', 'datum', 'zeitraum'] as FilterModus[]).map((m) => (
                <button
                  key={m}
                  onClick={() => setFilterModus(m)}
                  className={`px-3 py-1.5 transition-colors ${
                    filterModus === m
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {m === 'monat' ? 'Monat' : m === 'datum' ? 'Tag' : 'Zeitraum'}
                </button>
              ))}
            </div>

            {/* Datums-Eingabe je nach Modus */}
            {filterModus === 'monat' && (
              <input
                type="month"
                value={monat}
                onChange={(e) => setMonat(e.target.value)}
                className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            )}
            {filterModus === 'datum' && (
              <input
                type="date"
                value={datum}
                onChange={(e) => setDatum(e.target.value)}
                className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            )}
            {filterModus === 'zeitraum' && (
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={datumVon}
                  onChange={(e) => setDatumVon(e.target.value)}
                  className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-slate-400 text-sm">bis</span>
                <input
                  type="date"
                  value={datumBis}
                  min={datumVon}
                  onChange={(e) => setDatumBis(e.target.value)}
                  className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            )}

            {/* Zahlungsstatus */}
            <select
              value={zahlungsstatus}
              onChange={(e) => setZahlungsstatus(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Alle Status</option>
              <option value="offen">Offen</option>
              <option value="teilweise">Teilweise bezahlt</option>
              <option value="bezahlt">Bezahlt</option>
            </select>
          </div>

          {/* Fehlermeldung */}
          {fehler && (
            <div className="mt-3 bg-red-50 border border-red-200 rounded-xl px-4 py-2.5 text-sm text-red-700 flex items-center justify-between">
              <span>{fehler}</span>
              <button onClick={() => setFehler(null)} className="text-red-400 hover:text-red-600">×</button>
            </div>
          )}
        </div>

        {/* Kennzahlen */}
        {liste.length > 0 && (
          <div className="px-6 pb-3 grid grid-cols-3 gap-3">
            <div className="bg-white rounded-xl border border-slate-200 p-3">
              <p className="text-xs text-slate-500 mb-0.5">Rechnungen</p>
              <p className="text-lg font-bold text-slate-800">{liste.length}</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-3">
              <p className="text-xs text-slate-500 mb-0.5">Gesamt</p>
              <p className="text-lg font-bold text-slate-800">{formatEuro(gesamt.brutto)}</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-3">
              <p className="text-xs text-slate-500 mb-0.5">Offen</p>
              <p className="text-lg font-bold text-amber-600">{formatEuro(gesamt.brutto - gesamt.bezahlt)}</p>
            </div>
          </div>
        )}

        {/* Tabelle */}
        <div className="flex-1 overflow-auto px-6 pb-6">
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            {isLoading ? (
              <p className="p-5 text-slate-400 text-sm">Lade Rechnungen…</p>
            ) : liste.length === 0 ? (
              <p className="p-5 text-slate-400 text-sm">Keine Rechnungen im gewählten Zeitraum.</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-100">
                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Datum</th>
                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Nummer</th>
                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Partner</th>
                    <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Brutto</th>
                    <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {liste.map((r) => (
                    <tr
                      key={r.id}
                      onClick={() => { setSelectedId(r.id); setFormModus(null) }}
                      className={`border-b border-slate-50 last:border-0 hover:bg-slate-50 cursor-pointer transition-colors ${
                        selectedId === r.id ? 'bg-blue-50/50' : ''
                      } ${r.storniert ? 'opacity-50' : ''}`}
                    >
                      <td className="px-5 py-3 text-slate-500">{formatDatum(r.datum)}</td>
                      <td className="px-5 py-3 font-mono text-xs text-slate-400">
                        {r.rechnungsnummer ?? '—'}
                        {r.ist_entwurf && <span className="ml-1.5 text-[10px] text-amber-700 bg-amber-50 border border-amber-200 rounded px-1">Entwurf</span>}
                        {r.storniert && <span className="ml-1.5 text-[10px] text-slate-400 bg-slate-100 border border-slate-200 rounded px-1">Storniert</span>}
                      </td>
                      <td className="px-5 py-3 text-slate-700">
                        {r.typ === 'ausgang'
                          ? (r.kunde_name ?? r.partner_freitext ?? '—')
                          : (r.lieferant_name ?? r.partner_freitext ?? '—')}
                        {r.faellig_am && r.zahlungsstatus !== 'bezahlt' && !r.storniert && r.faellig_am < heuteIso() && (
                          <span className="ml-1.5 text-[10px] text-red-600 bg-red-50 border border-red-200 rounded px-1">
                            Überfällig
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3 text-right font-medium text-slate-800">
                        {formatEuro(r.brutto_gesamt)}
                      </td>
                      <td className="px-5 py-3 text-center">
                        {r.storniert
                          ? <span className="text-xs text-slate-400 italic">—</span>
                          : <StatusBadge status={r.zahlungsstatus} />}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {/* Rechte Spalte: Detail oder Formular */}
      {formModus && (
        <div className="w-[480px] shrink-0 border-l border-slate-200 bg-white overflow-auto">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h3 className="font-semibold text-slate-800">
              {formModus === 'neu'
                ? `Neue ${typ === 'ausgang' ? 'Ausgangsrechnung' : 'Eingangsrechnung'}`
                : 'Rechnung bearbeiten'}
            </h3>
            <button onClick={() => setFormModus(null)} className="text-slate-400 hover:text-slate-600 text-xl">×</button>
          </div>
          <div className="p-6">
            <RechnungForm
              typ={formModus === 'bearbeiten' && selectedRechnung ? selectedRechnung.typ : typ}
              initial={formModus === 'bearbeiten' ? selectedRechnung ?? undefined : undefined}
              onSave={(data) => {
                if (formModus === 'bearbeiten' && selectedId) {
                  updateMutation.mutate({ id: selectedId, data })
                } else {
                  createMutation.mutate(data)
                }
              }}
              onCancel={() => setFormModus(null)}
            />
          </div>
        </div>
      )}

      {!formModus && selectedRechnung && (
        <div className="w-96 shrink-0">
          <RechnungDetail
            rechnung={selectedRechnung}
            onClose={() => setSelectedId(null)}
            onEdit={() => setFormModus('bearbeiten')}
            onDelete={() => {
              if (confirm('Rechnung wirklich löschen?')) {
                deleteMutation.mutate(selectedRechnung.id)
              }
            }}
          />
        </div>
      )}
    </div>
  )
}
