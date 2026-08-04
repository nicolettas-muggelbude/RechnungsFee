import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getMahnwesenKundenUebersicht, getMahnwesenEinstellungen, mahnungVorschau, mahnungErstellen,
  mahnungVorschauGebuehr, mahnungErstellenGebuehr, bezahleMahngebuehrKunde, mahnungZahlungErfassen,
  getKundeMahnungen, deleteMahnung, getMahnungPdfUrl, downloadMahnungPdfForMail, openUrl,
  getUnternehmen, getApiBase, isTauri, openInPdfWindow, setMahnsperre, clearMahnsperre, downloadInkassoPaket,
  type MahnwesenKundeUebersicht, type MahnwesenRechnungMini, type MahnungVorschau,
  type MahnungHistorieItem, type Mahnung, type Unternehmen, type MahnungZahlungResult,
} from '../../api/client'
import { MahnungMailDialog } from '../../components/MahnungMailDialog'
import { DateInput } from '../../components/DateInput'

function formatEuro(v: string | number): string {
  const n = typeof v === 'string' ? parseFloat(v) : v
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n)
}

function formatDatum(iso: string | null): string {
  if (!iso) return '–'
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

function tageSeit(iso: string | null): number {
  if (!iso) return 0
  const diff = Date.now() - new Date(iso).getTime()
  return Math.max(Math.floor(diff / 86400000), 0)
}

function heuteIso(): string {
  return new Date().toISOString().slice(0, 10)
}

type StatusKind = 'faellig' | 'entwurf' | 'versendet' | 'offen'
const ALLE_STATUS: StatusKind[] = ['faellig', 'entwurf', 'versendet', 'offen']
const STATUS_LABEL: Record<StatusKind, string> = {
  faellig: 'Fällig', entwurf: 'Entwurf', versendet: 'Versendet', offen: 'Offen',
}
const STATUS_FARBE: Record<string, string> = {
  faellig: 'bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300',
  entwurf: 'bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300',
  versendet: 'bg-green-100 dark:bg-green-950 text-green-700 dark:text-green-300',
  offen: 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400',
  storniert: 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400',
}

function kundeHatStatus(k: MahnwesenKundeUebersicht, s: StatusKind): boolean {
  if (s === 'faellig') return k.aktionsfaellig || k.anzahl_zahlungserinnerung_faellig > 0
  if (s === 'entwurf') return k.anzahl_entwurf > 0
  if (s === 'versendet') return k.anzahl_versendet > 0
  return k.anzahl_offen > 0 || (k.nur_offene_gebuehr && !k.aktionsfaellig)
}
function mahnungStatusLabel(status: string): string {
  return status === 'entwurf' ? 'Entwurf' : status === 'versendet' ? 'Versendet' : status === 'storniert' ? 'Storniert' : status
}

async function mahnungDrucken(mahnungId: number, qc: ReturnType<typeof useQueryClient>) {
  const base = await getApiBase()
  const resp = await fetch(`${base}/mahnwesen/${mahnungId}/pdf`)
  const blob = await resp.blob()
  const blobUrl = URL.createObjectURL(blob)
  qc.invalidateQueries({ queryKey: ['mahnwesen-kunden'] })
  qc.invalidateQueries({ queryKey: ['kunde-mahnungen'] })
  qc.invalidateQueries({ queryKey: ['rechnungen'] })
  if (isTauri()) {
    openInPdfWindow(blobUrl, 'Mahnung drucken')
  } else {
    const win = window.open(blobUrl, '_blank')
    if (win) win.addEventListener('load', () => win.print())
  }
  setTimeout(() => URL.revokeObjectURL(blobUrl), 120_000)
}

/** Mail-Fallback ohne SMTP: PDF herunterladen (zählt als versendet) + Standard-Mailprogramm mit
 *  vorausgefüllter Adresse/Betreff öffnen, analog handleMail() in RechnungenPage.tsx. */
async function mahnungMailFallback(m: MahnungHistorieItem, qc: ReturnType<typeof useQueryClient>, kundeId: number) {
  if (!m.kunde_email) {
    window.alert('Für diesen Kunden ist keine E-Mail-Adresse hinterlegt.')
    return
  }
  await downloadMahnungPdfForMail(m.id)
  qc.invalidateQueries({ queryKey: ['kunde-mahnungen', kundeId] })
  qc.invalidateQueries({ queryKey: ['mahnwesen-kunden'] })
  qc.invalidateQueries({ queryKey: ['rechnungen'] })
  const subject = encodeURIComponent(`${m.bezeichnung ?? 'Mahnung'} – Rechnung ${m.rechnungsnummern}`)
  const body = encodeURIComponent(
    `Guten Tag,\n\nanbei erhalten Sie unser Schreiben „${m.bezeichnung ?? 'Mahnung'}" zu Rechnung ${m.rechnungsnummern}.\n\n` +
    `Bitte die heruntergeladene PDF-Datei als Anhang einfügen.\n\nMit freundlichen Grüßen`
  )
  const mailtoUrl = `mailto:${m.kunde_email}?subject=${subject}&body=${body}`
  if (isTauri()) {
    await openUrl(mailtoUrl)
  } else {
    window.location.href = mailtoUrl
  }
}

// ---------------------------------------------------------------------------
// Detail-Panel für einen ausgewählten Kunden
// ---------------------------------------------------------------------------

function KundeDetail({
  kunde, onClose, onErstellt, unternehmen,
}: {
  kunde: MahnwesenKundeUebersicht
  onClose: () => void
  onErstellt: (ergebnis: Mahnung, rechnungsnummern: Map<number, string>) => void
  unternehmen: Unternehmen | null | undefined
}) {
  const qc = useQueryClient()
  const [zeRechnungId, setZeRechnungId] = useState<number | null>(null)
  const [zeVorschau, setZeVorschau] = useState<MahnungVorschau | null>(null)
  const [vorschau, setVorschau] = useState<MahnungVorschau | null>(null)
  const [mailFuer, setMailFuer] = useState<MahnungHistorieItem | null>(null)
  const [zeigSperreForm, setZeigSperreForm] = useState(false)
  const [sperreBis, setSperreBis] = useState('')
  const [sperreGrund, setSperreGrund] = useState('')

  const sperreSetzenMut = useMutation({
    mutationFn: () => setMahnsperre(kunde.kunde_id, sperreBis, sperreGrund.trim() || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['mahnwesen-kunden'] })
      setZeigSperreForm(false)
      setSperreBis('')
      setSperreGrund('')
    },
  })
  const sperreAufhebenMut = useMutation({
    mutationFn: () => clearMahnsperre(kunde.kunde_id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mahnwesen-kunden'] }),
  })

  const { data: einst } = useQuery({
    queryKey: ['mahnwesen-einstellungen'],
    queryFn: getMahnwesenEinstellungen,
    staleTime: 1000 * 60 * 5,
  })
  const { data: mahnungen = [] } = useQuery({
    queryKey: ['kunde-mahnungen', kunde.kunde_id],
    queryFn: () => getKundeMahnungen(kunde.kunde_id),
  })

  const stufeBezeichnung = (stufe: number): string =>
    einst?.mahnstufen.find((s) => s.stufe === stufe)?.bezeichnung ?? `Stufe ${stufe}`

  const zeVorschauMut = useMutation({
    mutationFn: (rechnungId: number) => mahnungVorschau([rechnungId], 1),
    onSuccess: (v) => setZeVorschau(v),
  })
  const vorschauMut = useMutation({
    mutationFn: () => kunde.nur_offene_gebuehr
      ? mahnungVorschauGebuehr(kunde.kunde_id, kunde.naechste_stufe ?? undefined)
      : mahnungVorschau([kunde.rechnungen[0].rechnung_id], kunde.naechste_stufe ?? undefined),
    onSuccess: (v) => setVorschau(v),
  })
  const erstellenMut = useMutation({
    mutationFn: ({ rechnungId, stufe }: { rechnungId?: number; stufe?: number }) => kunde.nur_offene_gebuehr
      ? mahnungErstellenGebuehr(kunde.kunde_id, stufe)
      : mahnungErstellen([rechnungId!], stufe),
    onSuccess: (ergebnis) => {
      qc.invalidateQueries({ queryKey: ['mahnwesen-kunden'] })
      qc.invalidateQueries({ queryKey: ['kunde-mahnungen', kunde.kunde_id] })
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
      const nrMap = new Map(kunde.rechnungen.map((r) => [r.rechnung_id, r.rechnungsnummer ?? `#${r.rechnung_id}`]))
      onErstellt(ergebnis, nrMap)
      setZeRechnungId(null)
      setZeVorschau(null)
      setVorschau(null)
    },
  })
  const loeschenMut = useMutation({
    mutationFn: (id: number) => deleteMahnung(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kunde-mahnungen', kunde.kunde_id] })
      qc.invalidateQueries({ queryKey: ['mahnwesen-kunden'] })
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
    },
  })

  const [zeigGebuehrZahlung, setZeigGebuehrZahlung] = useState(false)
  const [gebuehrBetrag, setGebuehrBetrag] = useState(kunde.offener_betrag_gesamt.replace('.', ','))
  const [gebuehrDatum, setGebuehrDatum] = useState(heuteIso())
  const [gebuehrZahlungsart, setGebuehrZahlungsart] = useState<'Bar' | 'Karte' | 'PayPal' | 'Bank'>('Bank')
  const gebuehrZahlungMut = useMutation({
    mutationFn: () => bezahleMahngebuehrKunde(kunde.kunde_id, gebuehrBetrag.replace(',', '.'), gebuehrDatum, gebuehrZahlungsart),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['mahnwesen-kunden'] })
      qc.invalidateQueries({ queryKey: ['kunde-mahnungen', kunde.kunde_id] })
      setZeigGebuehrZahlung(false)
    },
  })

  const [zahlungFuerMahnungId, setZahlungFuerMahnungId] = useState<number | null>(null)
  const [zahlungBetrag, setZahlungBetrag] = useState('')
  const [zahlungDatum, setZahlungDatum] = useState(heuteIso())
  const [zahlungZahlungsart, setZahlungZahlungsart] = useState<'Bar' | 'Karte' | 'PayPal' | 'Bank'>('Bank')
  const [zahlungResultat, setZahlungResultat] = useState<{ mahnungId: number; ergebnis: MahnungZahlungResult } | null>(null)
  const zahlungMut = useMutation({
    mutationFn: (mahnungId: number) => mahnungZahlungErfassen(mahnungId, zahlungBetrag.replace(',', '.'), zahlungDatum, zahlungZahlungsart),
    onSuccess: (ergebnis, mahnungId) => {
      qc.invalidateQueries({ queryKey: ['mahnwesen-kunden'] })
      qc.invalidateQueries({ queryKey: ['kunde-mahnungen', kunde.kunde_id] })
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
      setZahlungResultat({ mahnungId, ergebnis })
      setZahlungFuerMahnungId(null)
    },
  })

  function toggleZe(rechnungId: number) {
    if (zeRechnungId === rechnungId) {
      setZeRechnungId(null)
      setZeVorschau(null)
      return
    }
    setZeRechnungId(rechnungId)
    setZeVorschau(null)
    zeVorschauMut.mutate(rechnungId)
  }

  function rechnungStatusBadge(rm: MahnwesenRechnungMini) {
    if (rm.zahlungserinnerung_faellig) {
      return <span className="px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300">Fällig</span>
    }
    if (rm.mahnstufe_aktuell === 0) {
      return <span className="px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">Offen</span>
    }
    const farbe = rm.letzter_mahnung_status === 'versendet'
      ? 'bg-green-100 dark:bg-green-950 text-green-700 dark:text-green-300'
      : 'bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300'
    const suffix = rm.letzter_mahnung_status === 'versendet' ? 'versendet' : 'Entwurf'
    return <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-medium ${farbe}`}>{stufeBezeichnung(rm.mahnstufe_aktuell)} – {suffix}</span>
  }

  return (
    <div className="w-[28rem] shrink-0 border-l border-slate-200 dark:border-slate-700 h-full overflow-auto">
      <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
        <div>
          <p className="font-semibold text-slate-800 dark:text-slate-100">{kunde.kunde_name}</p>
          <p className="text-xs text-slate-400 dark:text-slate-500">
            {kunde.nur_offene_gebuehr
              ? `Nur noch offene Mahngebühr/Zinsen · ${formatEuro(kunde.offener_betrag_gesamt)}`
              : `${kunde.anzahl_offene_rechnungen} offene Rechnung${kunde.anzahl_offene_rechnungen !== 1 ? 'en' : ''} · ${formatEuro(kunde.offener_betrag_gesamt)}`}
          </p>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-xl">×</button>
      </div>

      <div className="p-5 space-y-5">
        {/* Mahnsperre */}
        {kunde.mahnsperre_bis ? (
          <div className="rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/40 px-3 py-2.5">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-sm font-medium text-blue-800 dark:text-blue-200">⏸ Mahnwesen pausiert bis {formatDatum(kunde.mahnsperre_bis)}</p>
                {kunde.mahnsperre_grund && <p className="text-xs text-blue-600 dark:text-blue-400 mt-0.5">{kunde.mahnsperre_grund}</p>}
              </div>
              <button
                type="button"
                onClick={() => sperreAufhebenMut.mutate()}
                disabled={sperreAufhebenMut.isPending}
                className="shrink-0 text-xs text-blue-600 dark:text-blue-400 hover:underline disabled:opacity-50"
              >
                Aufheben
              </button>
            </div>
            <p className="text-[11px] text-blue-500 dark:text-blue-500 mt-1">Fälligkeiten laufen unverändert weiter – danach geht es normal weiter.</p>
          </div>
        ) : zeigSperreForm ? (
          <div className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2.5 space-y-2">
            <p className="text-xs font-medium text-slate-600 dark:text-slate-300">Mahnsperre setzen</p>
            <DateInput value={sperreBis} onChange={setSperreBis} min={heuteIso()} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-2 py-1.5 text-sm dark:bg-slate-700 dark:text-slate-100" />
            <input
              type="text"
              value={sperreGrund}
              onChange={(e) => setSperreGrund(e.target.value)}
              placeholder="Grund (optional, z. B. „Kunde hat angerufen, zahlt in einer Woche“)"
              className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-2 py-1.5 text-xs dark:bg-slate-700 dark:text-slate-100"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => sperreSetzenMut.mutate()}
                disabled={!sperreBis || sperreSetzenMut.isPending}
                className="px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {sperreSetzenMut.isPending ? 'Speichere…' : 'Sperre setzen'}
              </button>
              <button
                type="button"
                onClick={() => { setZeigSperreForm(false); setSperreBis(''); setSperreGrund('') }}
                className="px-3 py-1.5 border border-slate-300 dark:border-slate-600 text-xs rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
              >
                Abbrechen
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setZeigSperreForm(true)}
            className="w-full flex items-center justify-center gap-1.5 px-3 py-2 border border-blue-300 dark:border-blue-700 text-blue-700 dark:text-blue-300 text-sm font-medium rounded-lg hover:bg-blue-50 dark:hover:bg-blue-950"
          >
            ⏸ Mahnsperre setzen
          </button>
        )}

        {/* Nur noch offene Mahngebühr/Zinsen, keine Rechnung mehr offen (Kontokorrent-Konsistenz) */}
        {kunde.nur_offene_gebuehr && (
          <div className="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 px-3 py-3 space-y-2">
            <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
              Keine Rechnung mehr offen – noch {formatEuro(kunde.offener_betrag_gesamt)} Mahngebühr/Verzugszinsen offen
            </p>
            {!zeigGebuehrZahlung ? (
              <button
                type="button"
                onClick={() => { setGebuehrBetrag(kunde.offener_betrag_gesamt.replace('.', ',')); setZeigGebuehrZahlung(true) }}
                className="w-full px-3 py-1.5 bg-amber-600 text-white text-xs font-medium rounded-lg hover:bg-amber-700"
              >
                Restgebühr bezahlen
              </button>
            ) : (
              <div className="space-y-1.5">
                <div className="flex gap-1.5">
                  <input
                    type="text"
                    value={gebuehrBetrag}
                    onChange={(e) => setGebuehrBetrag(e.target.value)}
                    className="w-24 border border-slate-300 dark:border-slate-600 rounded-lg px-2 py-1.5 text-sm dark:bg-slate-700 dark:text-slate-100"
                  />
                  <DateInput value={gebuehrDatum} onChange={setGebuehrDatum} className="flex-1 border border-slate-300 dark:border-slate-600 rounded-lg px-2 py-1.5 text-sm dark:bg-slate-700 dark:text-slate-100" />
                  <select
                    value={gebuehrZahlungsart}
                    onChange={(e) => setGebuehrZahlungsart(e.target.value as typeof gebuehrZahlungsart)}
                    className="border border-slate-300 dark:border-slate-600 rounded-lg px-2 py-1.5 text-sm dark:bg-slate-700 dark:text-slate-100"
                  >
                    <option value="Bank">Bank</option>
                    <option value="Bar">Bar</option>
                    <option value="Karte">Karte</option>
                    <option value="PayPal">PayPal</option>
                  </select>
                </div>
                <div className="flex gap-1.5">
                  <button
                    type="button"
                    onClick={() => gebuehrZahlungMut.mutate()}
                    disabled={gebuehrZahlungMut.isPending}
                    className="flex-1 px-3 py-1.5 bg-amber-600 text-white text-xs font-medium rounded-lg hover:bg-amber-700 disabled:opacity-50"
                  >
                    {gebuehrZahlungMut.isPending ? 'Buche…' : 'Buchen'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setZeigGebuehrZahlung(false)}
                    className="px-3 py-1.5 border border-slate-300 dark:border-slate-600 text-xs rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
                  >
                    Abbrechen
                  </button>
                </div>
                {gebuehrZahlungMut.isError && (
                  <p className="text-xs text-red-600 dark:text-red-400">{(gebuehrZahlungMut.error as Error).message}</p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Offene Rechnungen */}
        <div className={kunde.nur_offene_gebuehr ? 'hidden' : undefined}>
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">Offene Rechnungen</p>
          <div className="space-y-1.5">
            {kunde.rechnungen.map((rm) => (
              <div key={rm.rechnung_id}>
                <div
                  onClick={() => rm.zahlungserinnerung_faellig && toggleZe(rm.rechnung_id)}
                  className={`flex items-center justify-between text-sm rounded-lg px-3 py-2 bg-slate-50 dark:bg-slate-900 ${rm.zahlungserinnerung_faellig ? 'cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800' : ''}`}
                >
                  <div>
                    <span className="font-mono text-xs text-slate-500 dark:text-slate-400 mr-2">{rm.rechnungsnummer ?? '–'}</span>
                    <span className="text-xs text-slate-400 dark:text-slate-500">
                      fällig {formatDatum(rm.faellig_am)} ({tageSeit(rm.faellig_am)}d) · {formatEuro(rm.offener_betrag)}
                    </span>
                  </div>
                  {rechnungStatusBadge(rm)}
                </div>

                {zeRechnungId === rm.rechnung_id && (
                  <div className="mt-1.5 ml-3 pl-3 border-l-2 border-red-200 dark:border-red-800 space-y-2">
                    {zeVorschauMut.isPending && <p className="text-xs text-slate-400">Berechne…</p>}
                    {zeVorschau && (
                      <>
                        <div className="text-xs bg-slate-50 dark:bg-slate-900 rounded-lg p-2.5 space-y-1">
                          <div className="flex justify-between"><span className="text-slate-500 dark:text-slate-400">Offener Betrag</span><span>{formatEuro(zeVorschau.offener_betrag_gesamt)}</span></div>
                          {parseFloat(zeVorschau.mahngebuehr) > 0 && (
                            <div className="flex justify-between"><span className="text-slate-500 dark:text-slate-400">Mahngebühr</span><span>{formatEuro(zeVorschau.mahngebuehr)}</span></div>
                          )}
                          <div className="flex justify-between font-semibold text-slate-800 dark:text-slate-100 pt-1 border-t border-slate-200 dark:border-slate-700">
                            <span>Gesamt</span><span>{formatEuro(zeVorschau.gesamtforderung)}</span>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => erstellenMut.mutate({ rechnungId: rm.rechnung_id, stufe: 1 })}
                          disabled={erstellenMut.isPending}
                          className="w-full px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
                        >
                          {erstellenMut.isPending ? 'Lege an…' : `${zeVorschau.bezeichnung} als Entwurf anlegen`}
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Mahnung (konsolidiert, Stufe >= konsolidiert_ab_stufe) */}
        {kunde.aktionsfaellig && (
          <div>
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
              {kunde.naechste_stufe_bezeichnung} fällig
            </p>
            {!vorschau && !vorschauMut.isPending && (
              <button
                type="button"
                onClick={() => vorschauMut.mutate()}
                className="w-full px-3 py-1.5 border border-slate-300 dark:border-slate-600 text-sm rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
              >
                {kunde.nur_offene_gebuehr ? 'Vorschau berechnen' : `Vorschau berechnen (${kunde.anzahl_offene_rechnungen} Rechnungen zusammen)`}
              </button>
            )}
            {vorschauMut.isPending && <p className="text-xs text-slate-400">Berechne…</p>}
            {vorschau && (
              <div className="space-y-2">
                <div className="text-xs bg-slate-50 dark:bg-slate-900 rounded-lg p-3 space-y-1">
                  {!kunde.nur_offene_gebuehr && (
                    <div className="flex justify-between"><span className="text-slate-500 dark:text-slate-400">Offener Betrag ({vorschau.positionen.length} Rechnungen)</span><span>{formatEuro(vorschau.offener_betrag_gesamt)}</span></div>
                  )}
                  {parseFloat(vorschau.mahngebuehr) > 0 && (
                    <div className="flex justify-between"><span className="text-slate-500 dark:text-slate-400">Mahngebühr</span><span>{formatEuro(vorschau.mahngebuehr)}</span></div>
                  )}
                  {parseFloat(vorschau.verzugszinsen) > 0 && (
                    <div className="flex justify-between"><span className="text-slate-500 dark:text-slate-400">Verzugszinsen</span><span>{formatEuro(vorschau.verzugszinsen)}</span></div>
                  )}
                  <div className="flex justify-between font-semibold text-slate-800 dark:text-slate-100 pt-1 border-t border-slate-200 dark:border-slate-700">
                    <span>Gesamtforderung</span><span>{formatEuro(vorschau.gesamtforderung)}</span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => erstellenMut.mutate(kunde.nur_offene_gebuehr
                    ? { stufe: kunde.naechste_stufe ?? undefined }
                    : { rechnungId: kunde.rechnungen[0].rechnung_id, stufe: kunde.naechste_stufe ?? undefined })}
                  disabled={erstellenMut.isPending}
                  className="w-full px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {erstellenMut.isPending ? 'Lege an…' : `${vorschau.bezeichnung} als Entwurf anlegen`}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Mahnungen-Historie */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Mahnungen</p>
            {mahnungen.some((m) => m.status === 'versendet') && (
              <button
                type="button"
                onClick={() => downloadInkassoPaket(kunde.kunde_id).catch((e: Error) => alert(e.message))}
                title="ZIP mit Deckblatt, Kontokorrent, offenen Rechnungs-PDFs und allen versendeten Mahnungs-PDFs"
                className="text-[11px] px-2 py-1 border border-slate-300 dark:border-slate-600 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
              >
                📦 Inkasso-Paket
              </button>
            )}
          </div>
          {mahnungen.length === 0 ? (
            <p className="text-xs text-slate-400 dark:text-slate-500">Noch keine Mahnung angelegt.</p>
          ) : (
            <div className="space-y-1.5">
              {mahnungen.map((m) => (
                <div key={m.id} className="rounded-lg bg-slate-50 dark:bg-slate-900 px-3 py-2">
                  <div className="flex items-center justify-between text-sm mb-1.5">
                    <div>
                      <span className="font-mono text-xs text-slate-400 dark:text-slate-500 mr-2">{m.mahnnummer ?? '–'}</span>
                      <span className="text-slate-600 dark:text-slate-300">{m.bezeichnung}</span>
                      <span className="ml-1.5 text-xs text-slate-400 dark:text-slate-500">{formatDatum(m.erstellt_am.slice(0, 10))}</span>
                    </div>
                    <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-medium ${STATUS_FARBE[m.status]}`}>{mahnungStatusLabel(m.status)}</span>
                  </div>
                  <p className="text-[11px] text-slate-400 dark:text-slate-500 mb-1.5">
                    {m.rechnung_ids.length > 1 ? `gemeinsam: ${m.rechnungsnummern}` : `Rechnung: ${m.rechnungsnummern || '–'}`}
                  </p>
                  {m.status === 'versendet' && m.uebertragen_in_mahnung_id && (
                    <p className="text-[11px] mb-1.5 text-slate-400 dark:text-slate-500">
                      Gebühr/Zinsen in neuere Mahnung übernommen
                    </p>
                  )}
                  {m.status === 'versendet' && !m.uebertragen_in_mahnung_id && (parseFloat(m.mahngebuehr) > 0 || parseFloat(m.verzugszinsen) > 0) && (() => {
                    const gesamt = parseFloat(m.mahngebuehr) + parseFloat(m.verzugszinsen)
                    const offen = gesamt - parseFloat(m.mahngebuehr_bezahlt) - parseFloat(m.verzugszinsen_bezahlt)
                    const vorperioden = parseFloat(m.uebernommene_gebuehr_vorperioden)
                    return (
                      <p className={`text-[11px] mb-1.5 ${offen > 0.004 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-400 dark:text-slate-500'}`}>
                        Gebühr/Zinsen: {formatEuro(gesamt)}
                        {offen > 0.004 ? ` – davon ${formatEuro(offen)} offen` : ' – bezahlt'}
                        {vorperioden > 0.004 && ` (davon ${formatEuro(vorperioden)} aus Vorperiode)`}
                      </p>
                    )
                  })()}
                  <div className="flex flex-wrap gap-1.5">
                    <button type="button" onClick={async () => { const url = await getMahnungPdfUrl(m.id, true); await openUrl(url) }}
                      className="text-[11px] px-2 py-1 border border-slate-300 dark:border-slate-600 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300">
                      👁 Ansehen
                    </button>
                    <button type="button" onClick={() => mahnungDrucken(m.id, qc)}
                      className="text-[11px] px-2 py-1 border border-slate-300 dark:border-slate-600 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300">
                      🖨️ Drucken
                    </button>
                    <button
                      type="button"
                      onClick={() => unternehmen?.smtp_aktiv ? setMailFuer(m) : mahnungMailFallback(m, qc, kunde.kunde_id)}
                      title={unternehmen?.smtp_aktiv ? undefined : 'Kein SMTP eingerichtet – öffnet dein E-Mail-Programm, PDF wird heruntergeladen'}
                      className="text-[11px] px-2 py-1 border border-slate-300 dark:border-slate-600 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
                    >
                      ✉️ Mail{!unternehmen?.smtp_aktiv ? ' …' : ''}
                    </button>
                    {m.status === 'entwurf' && (
                      <button
                        type="button"
                        onClick={() => { if (window.confirm(`Mahnungs-Entwurf ${m.mahnnummer ?? ''} löschen?`)) loeschenMut.mutate(m.id) }}
                        disabled={loeschenMut.isPending}
                        className="text-[11px] px-2 py-1 border border-red-300 dark:border-red-700 rounded hover:bg-red-50 dark:hover:bg-red-950 text-red-600 dark:text-red-400 disabled:opacity-50"
                      >
                        🗑️ Löschen
                      </button>
                    )}
                    {m.status === 'versendet' && !m.uebertragen_in_mahnung_id && m.rechnung_ids.length > 1 && (
                      <button
                        type="button"
                        onClick={() => {
                          if (zahlungFuerMahnungId === m.id) { setZahlungFuerMahnungId(null); return }
                          setZahlungBetrag('')
                          setZahlungDatum(heuteIso())
                          setZahlungResultat(null)
                          setZahlungFuerMahnungId(m.id)
                        }}
                        title="Verteilt einen Zahlungseingang automatisch auf die zugehörigen Rechnungen (älteste zuerst), Rest gegen offene Mahngebühr/Verzugszinsen"
                        className="text-[11px] px-2 py-1 border border-green-300 dark:border-green-700 rounded hover:bg-green-50 dark:hover:bg-green-950 text-green-700 dark:text-green-400"
                      >
                        💶 Zahlung erfassen
                      </button>
                    )}
                  </div>

                  {zahlungFuerMahnungId === m.id && (
                    <div className="mt-1.5 space-y-1.5 border-t border-slate-200 dark:border-slate-700 pt-1.5">
                      <p className="text-[11px] text-slate-500 dark:text-slate-400">
                        Gesamtbetrag der Zahlung – wird automatisch auf {m.rechnung_ids.length} Rechnungen verteilt (älteste zuerst).
                      </p>
                      <div className="flex gap-1.5">
                        <input
                          type="text"
                          value={zahlungBetrag}
                          onChange={(e) => setZahlungBetrag(e.target.value)}
                          placeholder="Betrag €"
                          className="w-24 border border-slate-300 dark:border-slate-600 rounded-lg px-2 py-1.5 text-sm dark:bg-slate-700 dark:text-slate-100"
                        />
                        <DateInput value={zahlungDatum} onChange={setZahlungDatum} className="flex-1 border border-slate-300 dark:border-slate-600 rounded-lg px-2 py-1.5 text-sm dark:bg-slate-700 dark:text-slate-100" />
                        <select
                          value={zahlungZahlungsart}
                          onChange={(e) => setZahlungZahlungsart(e.target.value as typeof zahlungZahlungsart)}
                          className="border border-slate-300 dark:border-slate-600 rounded-lg px-2 py-1.5 text-sm dark:bg-slate-700 dark:text-slate-100"
                        >
                          <option value="Bank">Bank</option>
                          <option value="Bar">Bar</option>
                          <option value="Karte">Karte</option>
                          <option value="PayPal">PayPal</option>
                        </select>
                      </div>
                      <div className="flex gap-1.5">
                        <button
                          type="button"
                          onClick={() => zahlungMut.mutate(m.id)}
                          disabled={!zahlungBetrag || zahlungMut.isPending}
                          className="flex-1 px-3 py-1.5 bg-green-600 text-white text-xs font-medium rounded-lg hover:bg-green-700 disabled:opacity-50"
                        >
                          {zahlungMut.isPending ? 'Verteile…' : 'Verteilen & buchen'}
                        </button>
                        <button
                          type="button"
                          onClick={() => setZahlungFuerMahnungId(null)}
                          className="px-3 py-1.5 border border-slate-300 dark:border-slate-600 text-xs rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
                        >
                          Abbrechen
                        </button>
                      </div>
                      {zahlungMut.isError && (
                        <p className="text-xs text-red-600 dark:text-red-400">{(zahlungMut.error as Error).message}</p>
                      )}
                    </div>
                  )}

                  {zahlungResultat && zahlungResultat.mahnungId === m.id && (
                    <div className="mt-1.5 text-[11px] text-slate-500 dark:text-slate-400 border-t border-slate-200 dark:border-slate-700 pt-1.5 space-y-0.5">
                      {zahlungResultat.ergebnis.verteilung.map((v) => (
                        <p key={v.rechnung_id}>{v.rechnungsnummer ?? `#${v.rechnung_id}`}: {formatEuro(v.betrag)} verbucht</p>
                      ))}
                      {parseFloat(zahlungResultat.ergebnis.gebuehr_verrechnet) > 0.004 && (
                        <p>{formatEuro(zahlungResultat.ergebnis.gebuehr_verrechnet)} gegen Mahngebühr/Verzugszinsen verrechnet</p>
                      )}
                      {parseFloat(zahlungResultat.ergebnis.kundenguthaben) > 0.004 && (
                        <p>{formatEuro(zahlungResultat.ergebnis.kundenguthaben)} als Kundenguthaben erfasst</p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {mailFuer && (
        <MahnungMailDialog
          mahnung={mailFuer}
          unternehmen={unternehmen}
          onClose={() => setMailFuer(null)}
          onGesendet={() => {
            qc.invalidateQueries({ queryKey: ['kunde-mahnungen', kunde.kunde_id] })
            qc.invalidateQueries({ queryKey: ['rechnungen'] })
          }}
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Übersichtsseite
// ---------------------------------------------------------------------------

export function MahnwesenPage() {
  const navigate = useNavigate()
  const [ausgewaehltKundeId, setAusgewaehltKundeId] = useState<number | null>(null)
  const [statusFilter, setStatusFilter] = useState<Set<StatusKind>>(new Set(ALLE_STATUS))
  const [letzteErgebnisse, setLetzteErgebnisse] = useState<{ ergebnis: Mahnung; nrMap: Map<number, string> }[] | null>(null)

  const { data: kunden = [], isLoading } = useQuery({
    queryKey: ['mahnwesen-kunden'],
    queryFn: getMahnwesenKundenUebersicht,
  })
  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen })

  function toggleStatusFilter(s: StatusKind) {
    setStatusFilter((prev) => {
      const next = new Set(prev)
      if (next.has(s)) next.delete(s)
      else next.add(s)
      return next
    })
  }

  const gefiltert = kunden.filter((k) => ALLE_STATUS.some((s) => statusFilter.has(s) && kundeHatStatus(k, s)))
  const ausgewaehlt = kunden.find((k) => k.kunde_id === ausgewaehltKundeId) ?? null

  // Summe der tatsächlichen Rechnungen/Mahnungen, nicht der Kunden mit diesem Status - sonst
  // zeigt die Kennzahl z.B. "1" obwohl ein einzelner Kunde 5 fällige Mahnungen hat (Nutzer-
  // Feedback 2026-08-04). aktionsfaellig hat keinen eigenen Rechnungs-Zähler (eine konsolidierte
  // Mahnung deckt mehrere Rechnungen als EINE Aktion ab) - zählt deshalb als 1 pro Kunde dazu.
  const anzahl = {
    faellig: kunden.reduce((sum, k) => sum + k.anzahl_zahlungserinnerung_faellig + (k.aktionsfaellig ? 1 : 0), 0),
    entwurf: kunden.reduce((sum, k) => sum + k.anzahl_entwurf, 0),
    versendet: kunden.reduce((sum, k) => sum + k.anzahl_versendet, 0),
  }

  return (
    <div className="flex h-full">
      {/* Linke Spalte */}
      <div className="flex-1 flex flex-col border-e border-slate-200 dark:border-slate-700 min-w-0 min-h-0">
        <div className="p-6 pb-4">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Mahnwesen</h2>
          </div>

          <div className="flex rounded-lg border border-slate-300 dark:border-slate-600 overflow-hidden text-sm w-fit">
            {ALLE_STATUS.map((s) => (
              <button
                key={s}
                onClick={() => toggleStatusFilter(s)}
                title={`„${STATUS_LABEL[s]}" ein-/ausblenden`}
                className={`px-3 py-1.5 transition-colors ${
                  statusFilter.has(s)
                    ? 'bg-blue-600 text-white'
                    : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
                }`}
              >
                {STATUS_LABEL[s]}
              </button>
            ))}
          </div>
        </div>

        {/* Kennzahlen */}
        {kunden.length > 0 && (
          <div className="px-6 pb-3 grid grid-cols-3 gap-3">
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Fällig</p>
              <p className="text-lg font-bold text-red-600 dark:text-red-400">{anzahl.faellig}</p>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Entwürfe</p>
              <p className="text-lg font-bold text-amber-600 dark:text-amber-400">{anzahl.entwurf}</p>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Versendet</p>
              <p className="text-lg font-bold text-green-600 dark:text-green-400">{anzahl.versendet}</p>
            </div>
          </div>
        )}

        {letzteErgebnisse && (
          <div className="mx-6 mb-3 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-xl px-4 py-2.5 text-xs text-green-800 dark:text-green-300">
            <div className="flex items-start justify-between gap-2">
              <span>✓ {letzteErgebnisse.length === 1 ? '1 Mahnung' : `${letzteErgebnisse.length} Mahnungen`} als Entwurf angelegt.</span>
              <button onClick={() => setLetzteErgebnisse(null)} className="text-green-600 dark:text-green-400 hover:text-green-800 dark:hover:text-green-200 leading-none">×</button>
            </div>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5">
              {letzteErgebnisse.flatMap(({ ergebnis, nrMap }) => ergebnis.rechnung_ids.map((rid) => (
                <button
                  key={`${ergebnis.id}-${rid}`}
                  onClick={() => navigate(`/rechnungen?open=${rid}`)}
                  className="underline hover:text-green-900 dark:hover:text-green-100"
                >
                  → {nrMap.get(rid) ?? `Rechnung #${rid}`} ansehen
                </button>
              )))}
            </div>
          </div>
        )}

        {/* Tabelle */}
        <div className="flex-1 overflow-y-auto min-h-0 px-6 pb-6">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            {isLoading ? (
              <p className="p-5 text-slate-400 dark:text-slate-500 text-sm">Lade…</p>
            ) : gefiltert.length === 0 ? (
              <p className="p-5 text-slate-400 dark:text-slate-500 text-sm">
                {kunden.length === 0 ? 'Keine Kunden mit offenen/überfälligen Rechnungen.' : 'Keine Einträge für die gewählten Filter.'}
              </p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 dark:bg-slate-900 border-b border-slate-100 dark:border-slate-700">
                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Kunde</th>
                    <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Rechnungen</th>
                    <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Fällig seit</th>
                    <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Betrag</th>
                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {gefiltert.map((k) => (
                    <tr
                      key={k.kunde_id}
                      onClick={() => setAusgewaehltKundeId(k.kunde_id)}
                      className={`border-b border-slate-50 dark:border-slate-700 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-700 cursor-pointer transition-colors ${
                        ausgewaehlt?.kunde_id === k.kunde_id ? 'bg-blue-100 dark:bg-slate-600 border-l-2 border-l-blue-500' : ''
                      }`}
                    >
                      <td className="px-5 py-3 text-slate-700 dark:text-slate-200">{k.kunde_name}</td>
                      <td className="px-5 py-3 text-center text-slate-600 dark:text-slate-300">{k.nur_offene_gebuehr ? '–' : k.anzahl_offene_rechnungen}</td>
                      <td className="px-5 py-3 text-right text-slate-500 dark:text-slate-400">
                        {k.nur_offene_gebuehr ? 'nur Gebühr offen' : `${formatDatum(k.aeltestes_faellig_am)} (${tageSeit(k.aeltestes_faellig_am)}d)`}
                      </td>
                      <td className="px-5 py-3 text-right font-medium text-slate-800 dark:text-slate-100">{formatEuro(k.offener_betrag_gesamt)}</td>
                      <td className="px-5 py-3">
                        <div className="flex flex-wrap gap-1">
                          {k.mahnsperre_bis && (
                            <span
                              title={k.mahnsperre_grund ?? undefined}
                              className="inline-block px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300"
                            >
                              ⏸ pausiert bis {formatDatum(k.mahnsperre_bis)}
                            </span>
                          )}
                          {k.aktionsfaellig && (
                            <span className={`inline-block px-1.5 py-0.5 rounded-full text-[10px] font-medium ${STATUS_FARBE.faellig}`}>
                              {k.naechste_stufe_bezeichnung} fällig
                            </span>
                          )}
                          {k.anzahl_zahlungserinnerung_faellig > 0 && (
                            <span className={`inline-block px-1.5 py-0.5 rounded-full text-[10px] font-medium ${STATUS_FARBE.faellig}`}>
                              {k.anzahl_zahlungserinnerung_faellig} fällig
                            </span>
                          )}
                          {k.anzahl_entwurf > 0 && (
                            <span className={`inline-block px-1.5 py-0.5 rounded-full text-[10px] font-medium ${STATUS_FARBE.entwurf}`}>
                              {k.anzahl_entwurf} Entwurf
                            </span>
                          )}
                          {k.anzahl_versendet > 0 && (
                            <span className={`inline-block px-1.5 py-0.5 rounded-full text-[10px] font-medium ${STATUS_FARBE.versendet}`}>
                              {k.anzahl_versendet} versendet
                            </span>
                          )}
                          {!k.aktionsfaellig && k.anzahl_zahlungserinnerung_faellig === 0 && k.anzahl_entwurf === 0 && k.anzahl_versendet === 0 && (
                            <span className={`inline-block px-1.5 py-0.5 rounded-full text-[10px] font-medium ${STATUS_FARBE.offen}`}>Offen</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {ausgewaehlt && (
        <KundeDetail
          kunde={ausgewaehlt}
          onClose={() => setAusgewaehltKundeId(null)}
          unternehmen={unternehmen}
          onErstellt={(ergebnis, nrMap) => setLetzteErgebnisse((prev) => [...(prev ?? []), { ergebnis, nrMap }])}
        />
      )}
    </div>
  )
}
