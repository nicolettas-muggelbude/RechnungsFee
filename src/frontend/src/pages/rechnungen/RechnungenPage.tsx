import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getRechnungen, createRechnung, updateRechnung, deleteRechnung, barZahlungErstellen,
  stornoRechnung, finalisiereRechnung,
  getKunden, getLieferanten, getKategorien, getUnternehmen, getApiBase, isTauri, openUrl,
  sucheArtikel, getUstSaetze, getKassenstand,
  type Rechnung, type RechnungCreate, type RechnungspositionCreate, type BarZahlungCreate,
  type ArtikelSuche,
} from '../../api/client'
import { InfoTooltip } from '../../components/InfoTooltip'

// ---------------------------------------------------------------------------
// Hilfsfunktionen
// ---------------------------------------------------------------------------

function formatMenge(v: string | number): string {
  const n = parseFloat(String(v).replace(',', '.'))
  if (isNaN(n)) return String(v)
  return new Intl.NumberFormat('de-DE', { maximumFractionDigits: 3 }).format(n)
}

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
// Status-Badge
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: 'offen' | 'teilweise' | 'bezahlt' }) {
  const cfg = {
    offen:     { cls: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-800',    label: 'Offen' },
    teilweise: { cls: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800', label: 'Teilweise' },
    bezahlt:   { cls: 'bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800', label: 'Bezahlt' },
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

  const { data: kassenstandData } = useQuery({ queryKey: ['kassenstand'], queryFn: getKassenstand })
  const kassenstand = parseFloat(kassenstandData?.kassenstand ?? '0')
  const istBarAusgabe = rechnung.typ === 'eingang' && zahlungsart === 'Bar'

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
  const kassenstandUeberschritten = istBarAusgabe && !isNaN(betragDecimal) && betragDecimal > kassenstand
  const artLabel = rechnung.typ === 'ausgang' ? 'Einnahme' : 'Ausgabe'

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (isNaN(betragDecimal) || betragDecimal <= 0) {
      setFehler('Bitte einen gültigen Betrag eingeben.')
      return
    }
    if (datum > new Date().toISOString().slice(0, 10)) {
      setFehler('Das Zahlungsdatum darf nicht in der Zukunft liegen.')
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
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md">
        <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800 dark:text-slate-100">
            {rechnung.typ === 'ausgang' ? 'Zahlung kassieren' : 'Zahlung buchen'}
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-xl">×</button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Rechnungsinfo */}
          <div className="bg-slate-50 dark:bg-slate-900 rounded-xl p-3 text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Rechnung</span>
              <span className="font-medium dark:text-slate-200">{rechnung.rechnungsnummer}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Gesamt</span>
              <span className="font-medium dark:text-slate-200">{formatEuro(rechnung.brutto_gesamt)}</span>
            </div>
            {parseFloat(rechnung.bezahlt_betrag) > 0 && (
              <div className="flex justify-between text-green-700 dark:text-green-400">
                <span>Bereits bezahlt</span>
                <span>{formatEuro(rechnung.bezahlt_betrag)}</span>
              </div>
            )}
            <div className="flex justify-between font-semibold border-t border-slate-200 dark:border-slate-700 pt-1 mt-1">
              <span className="text-slate-600 dark:text-slate-300">Restbetrag</span>
              <span className="dark:text-slate-100">{formatEuro(restbetrag)}</span>
            </div>
          </div>

          {/* Betrag */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Betrag (€)</label>
            <input
              type="text"
              value={betrag}
              onChange={(e) => setBetrag(e.target.value)}
              className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
              placeholder="0,00"
            />
          </div>

          {/* Datum */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Zahlungsdatum</label>
            <input
              type="date"
              value={datum}
              max={new Date().toISOString().slice(0, 10)}
              onChange={(e) => setDatum(e.target.value)}
              className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
            />
          </div>

          {/* Zahlungsart */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Zahlungsart</label>
            <div className="flex rounded-lg border border-slate-300 dark:border-slate-600 overflow-hidden text-sm">
              {([['Bar', 'Bar'], ['Karte', 'Karte'], ['PayPal', 'PayPal'], ['Bank', 'Überw.']] as const).map(([val, label]) => (
                <button
                  key={val}
                  type="button"
                  onClick={() => setZahlungsart(val)}
                  className={`flex-1 py-2 transition-colors ${
                    zahlungsart === val
                      ? 'bg-blue-600 text-white'
                      : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Beschreibung (optional) */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
              Beschreibung <span className="text-slate-400 dark:text-slate-500 font-normal">(optional)</span>
            </label>
            <input
              type="text"
              value={beschreibung}
              onChange={(e) => setBeschreibung(e.target.value)}
              placeholder={`Zahlung ${rechnung.rechnungsnummer ?? ''}`}
              className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400"
            />
          </div>

          {/* Vorschau */}
          {!isNaN(betragDecimal) && betragDecimal > 0 && (
            <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-xl p-3 text-sm">
              <p className="text-blue-700 dark:text-blue-300 font-medium">Kassenbuchung wird erstellt:</p>
              <p className="text-blue-600 dark:text-blue-400 mt-0.5">
                {artLabel} {formatEuro(betragDecimal)} via {zahlungsart === 'Bank' ? 'Überweisung' : zahlungsart}
              </p>
            </div>
          )}

          {kassenstandUeberschritten && (
            <div className="flex items-start gap-2 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2 text-xs text-red-800 dark:text-red-300">
              <span className="mt-0.5 shrink-0">⛔</span>
              <span>
                <strong>Kassenstand nicht ausreichend.</strong> Aktueller Kassenstand:{' '}
                {formatEuro(kassenstand)} – Ausgabe: {formatEuro(betragDecimal)}
              </span>
            </div>
          )}

          {fehler && (
            <p className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2">
              {fehler}
            </p>
          )}

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 dark:text-slate-300"
            >
              Abbrechen
            </button>
            <button
              type="submit"
              disabled={mutation.isPending || kassenstandUeberschritten}
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

  async function _openPdf() {
    const base = await getApiBase()
    await openUrl(`${base}/rechnungen/${rechnung.id}/pdf`)
  }

  async function handleDrucken() {
    if (isTauri()) {
      await _openPdf()
    } else {
      const base = await getApiBase()
      const win = window.open(`${base}/rechnungen/${rechnung.id}/pdf`, '_blank')
      if (win) win.addEventListener('load', () => win.print())
    }
    qc.invalidateQueries({ queryKey: ['rechnungen'] })
  }

  async function handlePdfOeffnen() {
    await _openPdf()
    qc.invalidateQueries({ queryKey: ['rechnungen'] })
  }

  async function handleMail() {
    const email = partnerEmail || mailAdresse.trim()
    if (!email) { setZeigMailEingabe(true); return }

    // PDF als Download speichern damit es manuell als Anhang hinzugefügt werden kann
    setPdfLaeuft(true)
    setPdfHinweis(false)
    try {
      const base = await getApiBase()
      await openUrl(`${base}/rechnungen/${rechnung.id}/pdf?download=1`)
      setPdfHinweis(true)
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
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

    const subject = encodeURIComponent(subjectText)
    const body    = encodeURIComponent(bodyText)
    const mailtoUrl = `mailto:${email}?subject=${subject}&body=${body}`
    if (isTauri()) {
      await openUrl(mailtoUrl)
    } else {
      window.location.href = mailtoUrl
    }
    setZeigMailEingabe(false)
    setMailAdresse('')
  }

  return (
    <div className="border-l border-slate-200 dark:border-slate-700 h-full overflow-auto flex flex-col">
      <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
        <div>
          <p className="font-semibold text-slate-800 dark:text-slate-100">{rechnung.rechnungsnummer ?? '(keine Nummer)'}</p>
          <p className="text-xs text-slate-400 dark:text-slate-500">{rechnung.typ === 'ausgang' ? 'Ausgangsrechnung' : 'Eingangsrechnung'}</p>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-xl">×</button>
      </div>

      <div className="p-5 space-y-5 flex-1">

        {/* Aktionsleiste */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleDrucken}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
          >
            🖨️ {!rechnung.ist_entwurf && rechnung.ausgegeben ? 'Kopie drucken' : 'Drucken'}
          </button>
          <button
            onClick={handlePdfOeffnen}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
          >
            📄 {!rechnung.ist_entwurf && rechnung.ausgegeben ? 'Kopie öffnen' : 'PDF öffnen'}
          </button>
          {!rechnung.ist_entwurf && rechnung.ausgegeben && (
            <InfoTooltip text="Diese Rechnung wurde bereits ausgegeben (gedruckt, als PDF geöffnet oder per Mail versandt). Alle weiteren Ausgaben werden automatisch als Kopie markiert, damit Doppelsendungen erkennbar sind." side="bottom" />
          )}
          {!rechnung.storniert && (
            <button
              onClick={handleMail}
              disabled={pdfLaeuft}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 disabled:opacity-50"
            >
              {pdfLaeuft ? '⏳ PDF…' : `✉️ Mail senden${!partnerEmail ? ' …' : ''}`}
            </button>
          )}
          {!rechnung.ist_entwurf && !rechnung.storniert && !zeigStornoEingabe && (
            <button
              onClick={() => setZeigStornoEingabe(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-red-200 dark:border-red-800 rounded-lg hover:bg-red-50 dark:hover:bg-red-950 text-red-600 dark:text-red-400"
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
              className="flex-1 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400"
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
              className="px-3 py-1.5 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg text-sm hover:bg-slate-50 dark:hover:bg-slate-700"
            >
              Abbrechen
            </button>
          </div>
        )}

        {/* PDF-Hinweis nach Mail-Versand */}
        {pdfHinweis && (
          <div className="flex items-start gap-2 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-xl px-3 py-2 text-sm text-blue-800 dark:text-blue-300">
            <span className="mt-0.5 shrink-0">📎</span>
            <span className="flex-1">
              PDF wurde gespeichert. Bitte die Datei als Anhang in dein E-Mail-Programm einfügen.
            </span>
            <button onClick={() => setPdfHinweis(false)} className="text-blue-400 hover:text-blue-600 dark:text-blue-500 dark:hover:text-blue-300 shrink-0">×</button>
          </div>
        )}

        {/* Storno-Bestätigung */}
        {zeigStornoEingabe && (
          <div className="flex gap-2 items-center bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl px-3 py-2">
            <span className="text-sm text-red-700 dark:text-red-300 flex-1">
              Rechnung wirklich stornieren? Dies ist nicht rückgängig zu machen.
              {rechnung.zahlungen.length > 0 && (
                <span className="block mt-0.5 text-xs text-red-600 dark:text-red-400">
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
              className="px-3 py-1.5 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg text-sm hover:bg-slate-50 dark:hover:bg-slate-700"
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
          <div className="flex items-center justify-between gap-2 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-xl px-3 py-2">
            <span className="text-sm text-amber-800 dark:text-amber-300 flex items-center gap-1">
              📝 <strong>Entwurf</strong>
              <InfoTooltip text="Entwürfe sind noch nicht rechtsverbindlich und können bearbeitet oder gelöscht werden. Erst nach dem Finalisieren erhält die Rechnung ihre offizielle Nummer – danach ist keine Bearbeitung mehr möglich. Entwürfe können nicht kassiert werden." />
            </span>
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
            <span className="text-slate-500 dark:text-slate-400">Partner</span>
            <span className="text-right font-medium text-slate-800 dark:text-slate-100">
              {rechnung.typ === 'ausgang'
                ? (rechnung.kunde_name ?? rechnung.partner_freitext ?? '—')
                : (rechnung.lieferant_name ?? rechnung.partner_freitext ?? '—')}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500 dark:text-slate-400">Rechnungsdatum</span>
            <span className="dark:text-slate-200">{formatDatum(rechnung.datum)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500 dark:text-slate-400">Leistungsdatum</span>
            <span className="dark:text-slate-200">{rechnung.leistungsdatum ? formatDatum(rechnung.leistungsdatum) : formatDatum(rechnung.datum)}</span>
          </div>
          {rechnung.faellig_am && (
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Fällig am</span>
              <span className={
                rechnung.zahlungsstatus !== 'bezahlt' && rechnung.faellig_am < heuteIso()
                  ? 'text-red-600 font-medium'
                  : ''
              }>{formatDatum(rechnung.faellig_am)}</span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-slate-500 dark:text-slate-400">Status</span>
            {rechnung.storniert
              ? <span className="text-xs px-2 py-0.5 rounded border bg-slate-100 text-slate-500 border-slate-200 dark:bg-slate-700 dark:text-slate-400 dark:border-slate-600">Storniert</span>
              : rechnung.ist_entwurf
                ? <span className="text-xs px-2 py-0.5 rounded border bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800">Entwurf</span>
                : <StatusBadge status={rechnung.zahlungsstatus} />}
          </div>
        </div>

        {/* Positionen */}
        {rechnung.positionen.length > 0 && (
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
                  {rechnung.positionen.map((pos) => (
                    <tr key={pos.id} className="border-t border-slate-100 dark:border-slate-700">
                      <td className="px-3 py-2 text-slate-700 dark:text-slate-200">
                        {pos.beschreibung}
                        {parseFloat(pos.menge) !== 1 && (
                          <span className="text-slate-400 dark:text-slate-500"> × {formatMenge(pos.menge)} {pos.einheit}</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right dark:text-slate-200">{formatEuro(pos.netto)}</td>
                      <td className="px-3 py-2 text-right text-slate-400 dark:text-slate-500">{pos.ust_satz}%</td>
                      <td className="px-3 py-2 text-right font-medium dark:text-slate-200">{formatEuro(pos.brutto)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-700">
                  <tr>
                    <td colSpan={3} className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 font-medium">Gesamt</td>
                    <td className="px-3 py-2 text-right font-bold text-slate-800 dark:text-slate-100">{formatEuro(rechnung.brutto_gesamt)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}

        {/* Zahlungsstatus */}
        <div>
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2 flex items-center gap-1">
            Zahlung
            <InfoTooltip text="Offen: noch keine Zahlung eingegangen. Teilweise: mindestens eine Teilzahlung verbucht. Bezahlt: Rechnungsbetrag vollständig beglichen. Zahlungen werden automatisch als Kassenbucheinträge gespeichert." />
          </p>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-slate-500 dark:text-slate-400">Bezahlt</span>
              <span className="font-medium dark:text-slate-200">{formatEuro(rechnung.bezahlt_betrag)}</span>
            </div>
            <div className="h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
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
            <div className="flex justify-between text-xs text-slate-400 dark:text-slate-500">
              <span>0 €</span>
              <span>{formatEuro(rechnung.brutto_gesamt)}</span>
            </div>
          </div>
        </div>

        {/* Verknüpfte Zahlungen */}
        {rechnung.zahlungen.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
              Verknüpfte Kassenbuchungen
            </p>
            <div className="space-y-1">
              {rechnung.zahlungen.map((z) => (
                <div key={z.id} className="flex items-center justify-between text-sm bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2">
                  <div>
                    <span className="font-mono text-xs text-slate-400 dark:text-slate-500 mr-2">{z.belegnr}</span>
                    <span className="text-slate-600 dark:text-slate-300">{formatDatum(z.datum)}</span>
                    <span className="ml-1.5 text-xs text-slate-400 dark:text-slate-500">{z.zahlungsart}</span>
                  </div>
                  <span className={`font-medium ${z.art === 'Einnahme' ? 'text-green-600' : 'text-red-600'}`}>
                    {z.art === 'Ausgabe' ? '−' : '+'}{formatEuro(z.brutto_betrag)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {rechnung.typ === 'eingang' && rechnung.externe_belegnr && (
          <div>
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Belegnr. Lieferant</p>
            <p className="text-sm text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2">{rechnung.externe_belegnr}</p>
          </div>
        )}

        {rechnung.notizen && (
          <div>
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Notizen</p>
            <p className="text-sm text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2">{rechnung.notizen}</p>
          </div>
        )}
      </div>

      {/* Aktionen */}
      <div className="p-5 border-t border-slate-100 dark:border-slate-700 space-y-2">
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
              className="w-full py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700 dark:text-slate-300 transition-colors"
            >
              Bearbeiten
            </button>
            <button
              onClick={onDelete}
              className="w-full py-2 text-sm text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800 rounded-xl hover:bg-red-50 dark:hover:bg-red-950 transition-colors"
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
          className="w-full border-0 outline-none bg-transparent text-slate-700 dark:text-slate-200 min-w-0"
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
      className="w-full border-0 outline-none bg-transparent text-slate-700 dark:text-slate-200 cursor-pointer"
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
          className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 pr-20 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400"
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
        <div className="absolute z-50 w-full mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg max-h-64 overflow-y-auto">
          {gefiltert.length === 0 ? (
            <div className="px-3 py-2.5 text-sm text-slate-400 dark:text-slate-500 italic">
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
                      ? 'bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300'
                      : 'text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700'
                  }`}
                >
                  {item.label}
                </button>
              ))}
              {mehrVorhanden && (
                <div className="px-3 py-2 text-xs text-slate-400 dark:text-slate-500 border-t border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
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
// Artikel-Autocomplete für Positionsbeschreibung
// ---------------------------------------------------------------------------

function BeschreibungAutocomplete({
  value,
  onChange,
  onArtikelWahl,
}: {
  value: string
  onChange: (v: string) => void
  onArtikelWahl: (a: ArtikelSuche) => void
}) {
  const [offen, setOffen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const { data: treffer } = useQuery({
    queryKey: ['artikel-suche', value],
    queryFn: () => sucheArtikel(value),
    enabled: value.length >= 3,
    staleTime: 1000 * 30,
  })

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOffen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const zeigeDropdown = offen && !!treffer && treffer.length > 0

  return (
    <div ref={ref} className="relative w-full">
      <input
        required
        type="text"
        value={value}
        onChange={(e) => { onChange(e.target.value); setOffen(true) }}
        onFocus={() => value.length >= 3 && setOffen(true)}
        className="w-full border-0 outline-none bg-transparent text-slate-700 dark:text-slate-200 placeholder-slate-300 dark:placeholder-slate-500"
        placeholder="Beschreibung"
      />
      {zeigeDropdown && (
        <div className="absolute top-full left-0 z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg min-w-64 max-h-52 overflow-y-auto">
          {treffer!.map((a) => (
            <button
              key={a.id}
              type="button"
              onClick={() => { onArtikelWahl(a); setOffen(false) }}
              className="w-full text-left px-3 py-2 text-xs hover:bg-blue-50 dark:hover:bg-blue-950 border-b border-slate-100 dark:border-slate-700 last:border-0"
            >
              <div className="font-medium text-slate-800 dark:text-slate-100">{a.bezeichnung}</div>
              <div className="text-slate-400 dark:text-slate-500">{a.artikelnummer} · {a.einheit} · {formatEuro(a.vk_brutto)}</div>
            </button>
          ))}
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
  artikel_id?: number
  kategorie_id?: string  // nur Eingang, per-Position-Kategorie
}

const leerPosition = (defaultUst = '19'): Positionszeile => ({
  beschreibung: '',
  menge: '1',
  einheit: '',
  netto: '',
  ust_satz: defaultUst,
  artikel_id: undefined,
  kategorie_id: undefined,
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
  const { data: ustSaetze = [] } = useQuery({ queryKey: ['ust-saetze'], queryFn: getUstSaetze, staleTime: 1000 * 60 * 10 })

  const istKleinunternehmer = unternehmen?.ist_kleinunternehmer ?? false
  const aktiveSaetze = ustSaetze.filter((s) => s.ist_aktiv)
  const defaultUstGlobal = istKleinunternehmer
    ? '0'
    : (ustSaetze.find((s) => s.ist_default)?.satz
        ? String(parseFloat(ustSaetze.find((s) => s.ist_default)!.satz))
        : '19')

  const [rechnungsnummer, setRechnungsnummer] = useState(initial?.rechnungsnummer ?? '')
  const [datum, setDatum] = useState(initial?.datum ?? heuteIso())
  const [leistungsdatum, setLeistungsdatum] = useState(initial?.leistungsdatum ?? initial?.datum ?? heuteIso())
  const [leistungsdatumManuell, setLeistungsdatumManuell] = useState(
    !!(initial?.leistungsdatum && initial.leistungsdatum !== initial.datum)
  )
  const zahlungsziel = unternehmen?.standard_zahlungsziel ?? 14
  const [faelligAm, setFaelligAm] = useState(() => {
    if (initial?.faellig_am) return initial.faellig_am
    if (initial) return ''  // Bearbeiten ohne Fälligkeitsdatum → leer lassen
    const d = new Date(heuteIso())
    d.setDate(d.getDate() + (unternehmen?.standard_zahlungsziel ?? 14))
    return d.toISOString().slice(0, 10)
  })
  const [partnerId, setPartnerId] = useState<string>(
    typ === 'ausgang'
      ? String(initial?.kunde_id ?? '')
      : String(initial?.lieferant_id ?? '')
  )
  const [partnerFreitext, setPartnerFreitext] = useState(initial?.partner_freitext ?? '')
  const [kategorieId, setKategorieId] = useState<string>(String(initial?.kategorie_id ?? ''))
  const [notizen, setNotizen] = useState(initial?.notizen ?? '')
  const [externeBelegnr, setExterneBelegnr] = useState(initial?.externe_belegnr ?? '')
  const [positionen, setPositionen] = useState<Positionszeile[]>(
    initial?.positionen?.map((p) => ({
      beschreibung: p.beschreibung,
      menge: String(parseFloat(p.menge)),  // Decimal-Trailing-Zeros entfernen (z.B. "10.000" → "10")
      einheit: p.einheit,
      netto: p.brutto,  // eingabeModus startet als 'brutto' → Bruttowert vorbefüllen
      ust_satz: String(parseFloat(p.ust_satz)),
      artikel_id: p.artikel_id ?? undefined,
      kategorie_id: p.kategorie_id != null ? String(p.kategorie_id) : undefined,
    })) ?? [leerPosition(defaultUstGlobal)]
  )
  const [eingabeModus, setEingabeModus] = useState<'netto' | 'brutto'>('brutto')
  // Schnellmodus: einfache Betragseingabe für Eingangsrechnungen (default für neue + 1-Positions-Rechnungen)
  const [schnellmodus, setSchnellmodus] = useState(
    typ === 'eingang' && (!initial || initial.positionen.length <= 1)
  )

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

  // Fälligkeitsdatum = Rechnungsdatum + Zahlungsziel (nur neue Rechnungen, nur wenn unternehmen geladen)
  useEffect(() => {
    if (initial) return
    const d = new Date(datum)
    d.setDate(d.getDate() + zahlungsziel)
    setFaelligAm(d.toISOString().slice(0, 10))
  }, [datum, zahlungsziel, initial])

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
    const defaultUst = istKleinunternehmer ? '0' : (kat ? String(kat.ust_satz_standard) : defaultUstGlobal)
    setPositionen((prev) => [...prev, leerPosition(defaultUst)])
  }

  function removePosition(i: number) {
    if (positionen.length <= 1) return
    setPositionen((prev) => prev.filter((_, idx) => idx !== i))
  }

  function fillPositionFromArtikel(i: number, a: ArtikelSuche) {
    const ust_satz = istKleinunternehmer ? '0' : String(parseInt(a.steuersatz))
    const preis = eingabeModus === 'netto' ? a.vk_netto : a.vk_brutto
    setPositionen((prev) => prev.map((p, idx) =>
      idx === i
        ? { ...p, beschreibung: a.bezeichnung, einheit: a.einheit, ust_satz, netto: preis.replace('.', ','), artikel_id: a.id }
        : p
    ))
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
      externe_belegnr: typ === 'eingang' ? (externeBelegnr || undefined) : undefined,
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
          artikel_id: p.artikel_id,
          kategorie_id: p.kategorie_id ? parseInt(p.kategorie_id) : undefined,
        } as RechnungspositionCreate
      }),
    }
  }

  function handleSubmit(e: React.FormEvent, istEntwurf: boolean) {
    e.preventDefault()
    if (typ === 'ausgang' && !partnerId && !partnerFreitext.trim()) {
      alert('Bitte einen Kunden auswählen oder einen Namen im Kundenfeld eingeben.')
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
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
            Rechnungsnummer <span className="text-slate-400 dark:text-slate-500 font-normal">(leer = auto)</span>
          </label>
          <input
            type="text"
            value={rechnungsnummer}
            onChange={(e) => setRechnungsnummer(e.target.value)}
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400"
            placeholder="wird automatisch vergeben"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Rechnungsdatum *</label>
          <input
            type="date"
            required
            value={datum}
            onChange={(e) => setDatum(e.target.value)}
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
            Leistungsdatum
            {!leistungsdatumManuell && <span className="text-slate-400 dark:text-slate-500 font-normal ml-1">(= Rechnungsdatum)</span>}
          </label>
          <input
            type="date"
            value={leistungsdatum}
            onChange={(e) => {
              setLeistungsdatum(e.target.value)
              setLeistungsdatumManuell(e.target.value !== datum)
            }}
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Fällig am</label>
          <input
            type="date"
            value={faelligAm}
            min={datum}
            onChange={(e) => setFaelligAm(e.target.value)}
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Kategorie</label>
        <select
          value={kategorieId}
          onChange={(e) => setKategorieId(e.target.value)}
          className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
        >
          <option value="">— keine —</option>
          {kategorieOptionen}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
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
        <div className="flex items-start gap-2 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg px-3 py-2 text-xs text-amber-800 dark:text-amber-300">
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
          <label className="text-sm font-medium text-slate-700 dark:text-slate-200">
            {typ === 'eingang' && schnellmodus ? 'Rechnungsbetrag *' : 'Positionen *'}
          </label>
          <div className="flex items-center gap-3">
            {typ === 'eingang' && (
              <button
                type="button"
                onClick={() => setSchnellmodus((v) => !v)}
                className="text-xs text-blue-600 hover:text-blue-700 underline"
              >
                {schnellmodus ? 'Positionen aufschlüsseln →' : '← Einfache Eingabe'}
              </button>
            )}
            {(!schnellmodus || typ === 'ausgang') && !istKleinunternehmer && (
              <button
                type="button"
                onClick={toggleEingabeModus}
                className="text-xs text-blue-600 hover:text-blue-700 underline"
              >
                {eingabeModus === 'netto' ? 'Brutto eingeben' : 'Netto eingeben'}
              </button>
            )}
            {!schnellmodus && (
              <button
                type="button"
                onClick={addPosition}
                className="text-xs text-blue-600 hover:text-blue-700 font-medium"
              >
                + Position hinzufügen
              </button>
            )}
          </div>
        </div>

        {/* Schnellmodus (nur Eingang) */}
        {typ === 'eingang' && schnellmodus ? (
          <div className="border border-slate-200 dark:border-slate-700 rounded-xl p-4 space-y-3">
            <div>
              <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Beschreibung / Verwendungszweck</label>
              <input
                type="text"
                value={positionen[0]?.beschreibung ?? ''}
                onChange={(e) => updatePosition(0, 'beschreibung', e.target.value)}
                className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400"
                placeholder="z. B. Lieferantenrechnung Bürobedarf"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">
                  {eingabeModus === 'netto' ? 'Nettobetrag (€)' : 'Bruttobetrag (€)'}
                </label>
                <div className="flex gap-2">
                  <input
                    required
                    type="text"
                    value={positionen[0]?.netto ?? ''}
                    onChange={(e) => updatePosition(0, 'netto', e.target.value)}
                    className="flex-1 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
                    placeholder="0,00"
                  />
                  {!istKleinunternehmer && (
                    <button
                      type="button"
                      onClick={toggleEingabeModus}
                      className="px-2 py-1 text-xs border border-slate-300 dark:border-slate-600 rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 whitespace-nowrap"
                    >
                      {eingabeModus === 'netto' ? '→ Brutto' : '→ Netto'}
                    </button>
                  )}
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">USt-Satz</label>
                <select
                  value={positionen[0]?.ust_satz ?? defaultUstGlobal}
                  onChange={(e) => updatePosition(0, 'ust_satz', e.target.value)}
                  disabled={istKleinunternehmer}
                  className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 disabled:text-slate-400 disabled:cursor-not-allowed"
                >
                  {istKleinunternehmer ? (
                    <option value="0">0 % (§19)</option>
                  ) : (
                    aktiveSaetze.map((s) => {
                      const val = String(parseFloat(s.satz))
                      return <option key={s.id} value={val}>{val} %</option>
                    })
                  )}
                </select>
              </div>
            </div>
            {/* Summenanzeige */}
            {parseFloat((positionen[0]?.netto ?? '').replace(',', '.')) !== 0 && (
              <div className="text-xs text-right text-slate-500 dark:text-slate-400 space-y-0.5 pt-1 border-t border-slate-100 dark:border-slate-700">
                <div>Netto{eingabeModus === 'brutto' && ' (berechnet)'}: <span className="font-medium text-slate-700 dark:text-slate-200">{formatEuro(summen.netto)}</span></div>
                {summen.ust !== 0 && <div>USt: <span className="text-slate-600 dark:text-slate-300">{formatEuro(summen.ust)}</span></div>}
                <div className="font-semibold text-slate-800 dark:text-slate-100">Brutto{eingabeModus === 'netto' && ' (berechnet)'}: {formatEuro(summen.brutto)}</div>
              </div>
            )}
          </div>
        ) : (
        /* Positionstabelle */
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
                {typ === 'eingang' && (
                  <th className="px-3 py-2 text-left text-slate-500 dark:text-slate-400 font-medium w-28">Konto</th>
                )}
                <th className="px-3 py-2 w-8"></th>
              </tr>
            </thead>
            <tbody>
              {positionen.map((pos, i) => (
                <tr key={i} className="border-t border-slate-100 dark:border-slate-700">
                  <td className="px-2 py-1.5">
                    <BeschreibungAutocomplete
                      value={pos.beschreibung}
                      onChange={(v) => updatePosition(i, 'beschreibung', v)}
                      onArtikelWahl={(a) => fillPositionFromArtikel(i, a)}
                    />
                  </td>
                  <td className="px-2 py-1.5">
                    <input
                      type="text"
                      value={pos.menge}
                      onChange={(e) => updatePosition(i, 'menge', e.target.value)}
                      className="w-full border-0 outline-none bg-transparent text-right text-slate-700 dark:text-slate-200"
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
                      className="w-full border-0 outline-none bg-transparent text-right text-slate-700 dark:text-slate-200"
                      placeholder="0,00"
                    />
                  </td>
                  <td className="px-2 py-1.5">
                    <select
                      value={pos.ust_satz}
                      onChange={(e) => updatePosition(i, 'ust_satz', e.target.value)}
                      disabled={istKleinunternehmer}
                      className="w-full border-0 outline-none bg-transparent text-right text-slate-700 dark:text-slate-200 disabled:text-slate-400 dark:disabled:text-slate-500 disabled:cursor-not-allowed"
                    >
                      {istKleinunternehmer ? (
                        <option value="0">0 (§19)</option>
                      ) : (
                        aktiveSaetze.map((s) => {
                          const val = String(parseFloat(s.satz))
                          return (
                            <option key={s.id} value={val}>{val} %</option>
                          )
                        })
                      )}
                    </select>
                  </td>
                  {typ === 'eingang' && (
                    <td className="px-2 py-1.5">
                      <select
                        value={pos.kategorie_id ?? ''}
                        onChange={(e) => updatePosition(i, 'kategorie_id', e.target.value)}
                        className="w-full border-0 outline-none bg-transparent text-slate-700 dark:text-slate-200 text-xs"
                      >
                        <option value="">— Hauptkategorie —</option>
                        {(kategorien ?? []).filter((k) => k.kontenart === 'Aufwand' || k.kontenart === 'Anlage').map((k) => (
                          <option key={k.id} value={String(k.id)}>{k.name}</option>
                        ))}
                      </select>
                    </td>
                  )}
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
            <tfoot className="bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-700">
              <tr>
                <td colSpan={typ === 'eingang' ? 5 : 4} className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 text-xs">
                  Netto{eingabeModus === 'brutto' && <span className="text-slate-400 dark:text-slate-500"> (berechnet)</span>}
                </td>
                <td colSpan={2} className="px-3 py-2 text-right font-medium text-slate-700 dark:text-slate-200">{formatEuro(summen.netto)}</td>
              </tr>
              <tr>
                <td colSpan={typ === 'eingang' ? 5 : 4} className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 text-xs">USt</td>
                <td colSpan={2} className="px-3 py-2 text-right text-slate-600 dark:text-slate-300">{formatEuro(summen.ust)}</td>
              </tr>
              <tr>
                <td colSpan={typ === 'eingang' ? 5 : 4} className="px-3 py-2 text-right font-semibold text-slate-700 dark:text-slate-200">
                  Brutto{eingabeModus === 'netto' && <span className="text-slate-400 dark:text-slate-500 font-normal"> (berechnet)</span>}
                </td>
                <td colSpan={2} className="px-3 py-2 text-right font-bold text-slate-800 dark:text-slate-100">{formatEuro(summen.brutto)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Notizen</label>
        <textarea
          value={notizen}
          onChange={(e) => setNotizen(e.target.value)}
          rows={2}
          className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400"
          placeholder="Optionale Bemerkungen"
        />
      </div>

      {typ === 'eingang' && (
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
            Belegnr. des Lieferanten
            <span className="text-slate-400 dark:text-slate-500 font-normal ml-1">(optional)</span>
          </label>
          <input
            type="text"
            value={externeBelegnr}
            onChange={(e) => setExterneBelegnr(e.target.value)}
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400"
            placeholder="z. B. RE-2025-0042"
          />
        </div>
      )}

      <div className="flex gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 dark:text-slate-300"
        >
          Abbrechen
        </button>
        <button
          type="button"
          onClick={(e) => handleSubmit(e, true)}
          className="flex-1 px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700"
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

type FilterModus = 'monat' | 'datum' | 'zeitraum' | 'jahr'

export function RechnungenPage() {
  const qc = useQueryClient()
  const [typ, setTyp] = useState<'eingang' | 'ausgang'>('ausgang')
  const [zahlungsstatus, setZahlungsstatus] = useState('')
  const [suche, setSuche] = useState('')
  const [filterModus, setFilterModus] = useState<FilterModus>('monat')
  const [monat, setMonat] = useState(aktuellerMonat())
  const [datum, setDatum] = useState(heuteIso())
  const [datumVon, setDatumVon] = useState(heuteIso())
  const [datumBis, setDatumBis] = useState(heuteIso())
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [formModus, setFormModus] = useState<'neu' | 'bearbeiten' | null>(null)
  const [fehler, setFehler] = useState<string | null>(null)
  const [sortFaellig, setSortFaellig] = useState<'asc' | 'desc' | null>(null)

  const aktivesJahr = new Date().getFullYear()
  const filterParams =
    filterModus === 'monat'
      ? { monat }
      : filterModus === 'datum'
        ? { datum_von: datum, datum_bis: datum }
        : filterModus === 'zeitraum'
          ? { datum_von: datumVon, datum_bis: datumBis }
          : { datum_von: `${aktivesJahr}-01-01`, datum_bis: `${aktivesJahr}-12-31` }

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

  const alleRechnungen = rechnungen ?? []
  const liste = suche.trim()
    ? alleRechnungen.filter(r => {
        const q = suche.trim().toLowerCase()
        return (
          (r.rechnungsnummer ?? '').toLowerCase().includes(q) ||
          (r.kunde_name ?? '').toLowerCase().includes(q) ||
          (r.lieferant_name ?? '').toLowerCase().includes(q) ||
          (r.externe_belegnr ?? '').toLowerCase().includes(q)
        )
      })
    : alleRechnungen

  const listeSortiert = sortFaellig
    ? [...liste].sort((a, b) => {
        const fa = a.faellig_am ?? ''
        const fb = b.faellig_am ?? ''
        return sortFaellig === 'asc' ? fa.localeCompare(fb) : fb.localeCompare(fa)
      })
    : liste

  // Summen (Entwürfe + Stornierte werden aus dem offenen Saldo ausgeschlossen)
  const gesamt = liste.reduce(
    (acc, r) => ({
      brutto: acc.brutto + (r.ist_entwurf || r.storniert ? 0 : parseFloat(r.brutto_gesamt)),
      offen: acc.offen + (r.ist_entwurf || r.storniert
        ? 0
        : Math.max(0, parseFloat(r.brutto_gesamt) - parseFloat(r.bezahlt_betrag))),
    }),
    { brutto: 0, offen: 0 }
  )

  return (
    <div className="flex h-full">
      {/* Linke Spalte */}
      <div className={`${formModus ? 'w-1/3 min-w-[260px] shrink-0' : 'flex-1'} flex flex-col border-e border-slate-200 dark:border-slate-700 min-w-0 transition-all`}>
        <div className="p-6 pb-4">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Rechnungen</h2>
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
            <div className="flex rounded-lg border border-slate-300 dark:border-slate-600 overflow-hidden text-sm">
              {(['ausgang', 'eingang'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => { setTyp(t); setSelectedId(null) }}
                  className={`px-4 py-1.5 transition-colors ${
                    typ === t ? 'bg-blue-600 text-white' : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
                  }`}
                >
                  {t === 'ausgang' ? 'Ausgang' : 'Eingang'}
                </button>
              ))}
            </div>

            {/* Zeitraum-Modus */}
            <div className="flex rounded-lg border border-slate-300 dark:border-slate-600 overflow-hidden text-sm">
              {(['monat', 'datum', 'zeitraum', 'alle'] as FilterModus[]).map((m) => (
                <button
                  key={m}
                  onClick={() => setFilterModus(m)}
                  className={`px-3 py-1.5 transition-colors ${
                    filterModus === m
                      ? 'bg-blue-600 text-white'
                      : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
                  }`}
                >
                  {m === 'monat' ? 'Monat' : m === 'datum' ? 'Tag' : m === 'zeitraum' ? 'Zeitraum' : 'Jahr'}
                </button>
              ))}
            </div>

            {/* Datums-Eingabe je nach Modus */}
            {filterModus === 'monat' && (
              <input
                type="month"
                value={monat}
                onChange={(e) => setMonat(e.target.value)}
                className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
              />
            )}
            {filterModus === 'datum' && (
              <input
                type="date"
                value={datum}
                onChange={(e) => setDatum(e.target.value)}
                className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
              />
            )}
            {filterModus === 'zeitraum' && (
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={datumVon}
                  onChange={(e) => setDatumVon(e.target.value)}
                  className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
                />
                <span className="text-slate-400 dark:text-slate-500 text-sm">bis</span>
                <input
                  type="date"
                  value={datumBis}
                  min={datumVon}
                  onChange={(e) => setDatumBis(e.target.value)}
                  className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
                />
              </div>
            )}

            {/* Suche */}
            <input
              type="search"
              placeholder="Nummer oder Partner suchen…"
              value={suche}
              onChange={(e) => setSuche(e.target.value)}
              className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 w-56"
            />

            {/* Zahlungsstatus */}
            <select
              value={zahlungsstatus}
              onChange={(e) => setZahlungsstatus(e.target.value)}
              className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
            >
              <option value="">Alle Status</option>
              <option value="offen">Offen</option>
              <option value="teilweise">Teilweise bezahlt</option>
              <option value="bezahlt">Bezahlt</option>
              <option value="entwurf">Entwurf</option>
              <option value="storniert">Storniert</option>
            </select>
          </div>

          {/* Fehlermeldung */}
          {fehler && (
            <div className="mt-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl px-4 py-2.5 text-sm text-red-700 dark:text-red-300 flex items-center justify-between">
              <span>{fehler}</span>
              <button onClick={() => setFehler(null)} className="text-red-400 hover:text-red-600 dark:text-red-500 dark:hover:text-red-300">×</button>
            </div>
          )}
        </div>

        {/* Kennzahlen */}
        {liste.length > 0 && (
          <div className="px-6 pb-3 grid grid-cols-3 gap-3">
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Rechnungen</p>
              <p className="text-lg font-bold text-slate-800 dark:text-slate-100">{liste.length}</p>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Gesamt</p>
              <p className="text-lg font-bold text-slate-800 dark:text-slate-100">{formatEuro(gesamt.brutto)}</p>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Offen</p>
              <p className="text-lg font-bold text-amber-600 dark:text-amber-400">{formatEuro(gesamt.offen)}</p>
            </div>
          </div>
        )}

        {/* Tabelle */}
        <div className="flex-1 overflow-auto px-6 pb-6">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            {isLoading ? (
              <p className="p-5 text-slate-400 dark:text-slate-500 text-sm">Lade Rechnungen…</p>
            ) : listeSortiert.length === 0 ? (
              <p className="p-5 text-slate-400 dark:text-slate-500 text-sm">Keine Rechnungen im gewählten Zeitraum.</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 dark:bg-slate-900 border-b border-slate-100 dark:border-slate-700">
                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Datum</th>
                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Nummer</th>
                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Partner</th>
                    <th
                      className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide cursor-pointer select-none hover:text-slate-700 dark:hover:text-slate-200"
                      onClick={() => setSortFaellig(s => s === 'asc' ? 'desc' : s === 'desc' ? null : 'asc')}
                    >
                      Fällig am {sortFaellig === 'asc' ? '↑' : sortFaellig === 'desc' ? '↓' : ''}
                    </th>
                    <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Brutto</th>
                    <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {listeSortiert.map((r) => (
                    <tr
                      key={r.id}
                      onClick={() => { setSelectedId(r.id); setFormModus(null) }}
                      className={`border-b border-slate-50 dark:border-slate-700 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-700 cursor-pointer transition-colors ${
                        selectedId === r.id ? 'bg-blue-50/50 dark:bg-blue-950/30' : ''
                      } ${r.storniert ? 'opacity-50' : ''}`}
                    >
                      <td className="px-5 py-3 text-slate-500 dark:text-slate-400">{formatDatum(r.datum)}</td>
                      <td className="px-5 py-3 font-mono text-xs text-slate-400 dark:text-slate-500">
                        {r.rechnungsnummer ?? '—'}
                        {r.ist_entwurf && <span className="ml-1.5 text-[10px] text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded px-1">Entwurf</span>}
                        {r.storniert && <span className="ml-1.5 text-[10px] text-slate-400 dark:text-slate-500 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded px-1">Storniert</span>}
                      </td>
                      <td className="px-5 py-3 text-slate-700 dark:text-slate-200">
                        {r.typ === 'ausgang'
                          ? (r.kunde_name ?? r.partner_freitext ?? '—')
                          : (r.lieferant_name ?? r.partner_freitext ?? '—')}
                      </td>
                      <td className="px-5 py-3 whitespace-nowrap">
                        {r.faellig_am ? (
                          <span className={`text-sm font-medium ${
                            r.zahlungsstatus !== 'bezahlt' && !r.storniert && r.faellig_am < heuteIso()
                              ? 'text-red-600 dark:text-red-400'
                              : 'text-slate-500 dark:text-slate-400'
                          }`}>
                            {formatDatum(r.faellig_am)}
                            {r.zahlungsstatus !== 'bezahlt' && !r.storniert && r.faellig_am < heuteIso() && (
                              <span className="ml-1.5 text-[10px] bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded px-1">Überfällig</span>
                            )}
                          </span>
                        ) : <span className="text-slate-300 dark:text-slate-600">—</span>}
                      </td>
                      <td className="px-5 py-3 text-right font-medium text-slate-800 dark:text-slate-100">
                        {formatEuro(r.brutto_gesamt)}
                      </td>
                      <td className="px-5 py-3 text-center">
                        {r.storniert
                          ? <span className="text-xs px-2 py-0.5 rounded border bg-slate-100 text-slate-500 border-slate-200 dark:bg-slate-700 dark:text-slate-400 dark:border-slate-600">Storniert</span>
                          : r.ist_entwurf
                            ? <span className="text-xs px-2 py-0.5 rounded border bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800">Entwurf</span>
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
        <div className="flex-1 border-l border-slate-200 dark:border-slate-700 overflow-auto">
          <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
            <h3 className="font-semibold text-slate-800 dark:text-slate-100">
              {formModus === 'neu'
                ? `Neue ${typ === 'ausgang' ? 'Ausgangsrechnung' : 'Eingangsrechnung'}`
                : 'Rechnung bearbeiten'}
            </h3>
            <button onClick={() => setFormModus(null)} className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-xl">×</button>
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

      {!formModus && (
        <div className="w-96 shrink-0">
          {selectedRechnung ? (
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
          ) : (
            <div className="flex items-center justify-center h-full text-slate-400 dark:text-slate-500 text-sm">
              Rechnung auswählen
            </div>
          )}
        </div>
      )}
    </div>
  )
}
