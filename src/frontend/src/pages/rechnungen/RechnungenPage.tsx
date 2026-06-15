import { useState, useEffect, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { listen } from '@tauri-apps/api/event'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getRechnungen, getRechnung, createRechnung, updateRechnung, deleteRechnung, barZahlungErstellen,
  stornoRechnung, finalisiereRechnung, createGutschrift, forderungsausbuchenRechnung,
  getLieferscheine, rechnungAusLieferschein, sammelrechnungErstellen, lieferscheinAusRechnung,
  getLieferadressen,
  getKunden, getLieferanten, getKategorien, getUnternehmen, getApiBase, isTauri, openUrl, openInPdfWindow, downloadPdfForMail,
  getUstSaetze, getKassenstand,
  uploadBeleg, getBelegUrl, getBelegPdfaUrl, deleteBeleg, analysiereRechnung, analysiereRechnungPfad,
  getBuchungsvorlage, erledigtVorlage,
  type Rechnung, type RechnungCreate, type RechnungspositionCreate, type BarZahlungCreate, type BarZahlungResult,
  type ArtikelSuche, type AnalyseErgebnis, type LieferantVorschlag, type ZahlungSplitPosition,
} from '../../api/client'
import { InfoTooltip } from '../../components/InfoTooltip'
import { KategorieErstellenModal } from '../../components/KategorieErstellenModal'
import { LieferantErstellenModal } from '../../components/LieferantErstellenModal'
import { KundeErstellenModal } from '../../components/KundeErstellenModal'
import { ArtikelFormModal } from '../artikel/ArtikelPage'
import { ArtikelAutocomplete } from '../../components/ArtikelAutocomplete'
import { MailDialog } from '../../components/MailDialog'
import { guardedDateChange } from '../../utils/dateInput'
import { getKontorahmenModus, katLabel, KONTORAHMEN_LS_KEY, type KontorahmenModus } from '../../utils/kontorahmen'

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
// Tesseract-Assistent (OCR einrichten)
// ---------------------------------------------------------------------------

type AssistentSchritt =
  | 'pruefe'          // initiale Prüfung
  | 'bereit'          // Voraussetzungen laden, zeige "Einrichten"-Button
  | 'installiere'     // läuft
  | 'erfolg'          // fertig, Neustart nötig
  | 'fehler_brew'     // macOS, Homebrew fehlt
  | 'fehler_winget'   // Windows, winget fehlt
  | 'fehler_pkexec'   // Linux, pkexec fehlt
  | 'fehler_manager'  // Linux, kein Paketmanager
  | 'fehler_sonstig'  // sonstiger Fehler

function TesseractAssistentModal({ onClose }: { onClose: () => void }) {
  const [schritt, setSchritt] = useState<AssistentSchritt>('pruefe')
  const [vorausset, setVorausset] = useState<import('../../api/client').TesseractVoraussetzungen | null>(null)

  useEffect(() => {
    Promise.all([
      import('../../api/client').then(m => m.pruefeTesseract()),
      import('../../api/client').then(m => m.tesseractVoraussetzungen()),
    ]).then(([status, v]) => {
      if (status.installiert) { onClose(); return }
      setVorausset(v)
      setSchritt('bereit')
    }).catch(() => setSchritt('bereit'))
  }, [])

  async function starten() {
    setSchritt('installiere')
    try {
      const { installiereTesseract } = await import('../../api/client')
      const res = await installiereTesseract()
      if (res.erfolg) {
        setSchritt('erfolg')
      } else {
        const f = res.fehler ?? ''
        if (f === 'BREW_FEHLT')        setSchritt('fehler_brew')
        else if (f === 'WINGET_FEHLT') setSchritt('fehler_winget')
        else if (f === 'PKEXEC_FEHLT') setSchritt('fehler_pkexec')
        else if (f === 'KEIN_PAKETMANAGER') setSchritt('fehler_manager')
        else setSchritt('fehler_sonstig')
      }
    } catch {
      setSchritt('fehler_sonstig')
    }
  }

  const os = vorausset?.os ?? (navigator.userAgent.includes('Win') ? 'Windows' : navigator.userAgent.includes('Mac') ? 'Darwin' : 'Linux')
  const osLabel = os === 'Windows' ? 'Windows' : os === 'Darwin' ? 'macOS' : 'Linux'
  const kannAutoInstall =
    (os === 'Windows' && vorausset?.winget) ||
    (os === 'Darwin'  && vorausset?.brew) ||
    (os === 'Linux'   && vorausset?.pkexec && (vorausset.apt || vorausset.dnf || vorausset.pacman))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md">

        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800 dark:text-slate-100">🔍 Texterkennung einrichten</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 text-xl leading-none">×</button>
        </div>

        <div className="px-6 py-5 space-y-4">

          {/* Prüfen */}
          {schritt === 'pruefe' && (
            <div className="flex items-center gap-3 text-slate-500 dark:text-slate-400">
              <div className="w-5 h-5 border-2 border-slate-300 border-t-blue-500 rounded-full animate-spin" />
              <span className="text-sm">Prüfe Installation…</span>
            </div>
          )}

          {/* Bereit – kann automatisch installieren */}
          {schritt === 'bereit' && kannAutoInstall && (
            <>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Für gescannte Eingangsrechnungen und Kassenbons wird <strong>Tesseract OCR</strong> benötigt.
                RechnungsFee richtet es automatisch ein.
              </p>
              <div className="bg-slate-50 dark:bg-slate-900 rounded-xl p-4 space-y-1 text-sm text-slate-500 dark:text-slate-400">
                <p>✓ {osLabel}-System erkannt</p>
                {os === 'Windows' && <p>✓ Windows-Paketmanager (winget) verfügbar</p>}
                {os === 'Darwin'  && <p>✓ Homebrew verfügbar</p>}
                {os === 'Linux'   && <p>✓ Paketmanager und Rechteverwaltung verfügbar</p>}
                <p className="text-xs pt-1">Dauer: ca. 1–3 Minuten · benötigt Internetverbindung</p>
              </div>
              {os === 'Linux' && (
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  ℹ️ Dein System fragt gleich nach dem Administratorpasswort – das ist normal.
                </p>
              )}
              <button
                onClick={starten}
                className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors"
              >
                Texterkennung einrichten
              </button>
            </>
          )}

          {/* Bereit – KEIN Auto-Install möglich → Anleitung */}
          {schritt === 'bereit' && !kannAutoInstall && (
            <TesseractAnleitung os={os as 'Windows' | 'Darwin' | 'Linux'} vorausset={vorausset} />
          )}

          {/* Läuft */}
          {schritt === 'installiere' && (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-5 h-5 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin shrink-0" />
                <p className="text-sm text-slate-600 dark:text-slate-300">Texterkennung wird eingerichtet…</p>
              </div>
              <p className="text-xs text-slate-400 dark:text-slate-500">
                Das kann 1–3 Minuten dauern. Bitte warten.
              </p>
            </div>
          )}

          {/* Erfolg */}
          {schritt === 'erfolg' && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                <span className="text-xl">✓</span>
                <p className="font-medium text-sm">Texterkennung erfolgreich eingerichtet!</p>
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Bitte starte RechnungsFee neu, damit die Texterkennung aktiv wird.
                Danach einfach den Import erneut starten.
              </p>
              <button
                onClick={onClose}
                className="w-full py-2.5 bg-green-600 hover:bg-green-700 text-white font-medium rounded-xl transition-colors"
              >
                Verstanden
              </button>
            </div>
          )}

          {/* Fehler: Homebrew fehlt (macOS) */}
          {schritt === 'fehler_brew' && (
            <div className="space-y-3">
              <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Homebrew ist nicht installiert</p>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Homebrew ist ein kostenloser Paketmanager für macOS, der für die Installation benötigt wird.
              </p>
              <a
                href="https://brew.sh"
                target="_blank"
                rel="noreferrer"
                onClick={() => import('../../api/client').then(m => m.openUrl('https://brew.sh'))}
                className="block w-full py-2.5 text-center bg-slate-700 hover:bg-slate-800 text-white font-medium rounded-xl transition-colors"
              >
                brew.sh öffnen →
              </a>
              <p className="text-xs text-slate-400 dark:text-slate-500">
                Nach der Homebrew-Installation diesen Assistenten erneut öffnen.
              </p>
            </div>
          )}

          {/* Fehler: winget fehlt (Windows) */}
          {schritt === 'fehler_winget' && (
            <div className="space-y-3">
              <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Automatische Installation nicht möglich</p>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Der Windows-Paketmanager (winget) ist nicht verfügbar. Bitte Tesseract OCR manuell installieren:
              </p>
              <a
                href="https://github.com/UB-Mannheim/tesseract/wiki"
                target="_blank"
                rel="noreferrer"
                onClick={() => import('../../api/client').then(m => m.openUrl('https://github.com/UB-Mannheim/tesseract/wiki'))}
                className="block w-full py-2.5 text-center bg-slate-700 hover:bg-slate-800 text-white font-medium rounded-xl transition-colors"
              >
                Tesseract Installer herunterladen →
              </a>
              <p className="text-xs text-slate-400 dark:text-slate-500">
                Nach der Installation RechnungsFee neu starten.
              </p>
            </div>
          )}

          {/* Fehler: pkexec oder Paketmanager fehlt (Linux) */}
          {(schritt === 'fehler_pkexec' || schritt === 'fehler_manager') && (
            <TesseractAnleitung os="Linux" vorausset={vorausset} />
          )}

          {/* Fehler: sonstiger Fehler */}
          {schritt === 'fehler_sonstig' && (
            <div className="space-y-3">
              <p className="text-sm font-medium text-red-600 dark:text-red-400">Installation fehlgeschlagen</p>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Die automatische Installation konnte nicht abgeschlossen werden. Bitte versuche es erneut oder installiere Tesseract OCR manuell.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => { setSchritt('bereit') }}
                  className="flex-1 py-2 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700 text-sm transition-colors"
                >
                  Erneut versuchen
                </button>
                <button
                  onClick={onClose}
                  className="flex-1 py-2 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700 text-sm transition-colors"
                >
                  Schließen
                </button>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  )
}

/** Manuelle Anleitung wenn kein Auto-Install möglich (Linux ohne pkexec, etc.) */
function TesseractAnleitung({
  os,
  vorausset,
}: {
  os: 'Windows' | 'Darwin' | 'Linux'
  vorausset: import('../../api/client').TesseractVoraussetzungen | null
}) {
  const pkg = vorausset?.dnf ? 'dnf' : vorausset?.pacman ? 'pacman' : 'apt'
  const schritte: { label: string; url?: string; hinweis?: string }[] = os === 'Windows'
    ? [{ label: 'Tesseract Installer herunterladen und ausführen', url: 'https://github.com/UB-Mannheim/tesseract/wiki', hinweis: 'Deutsch-Sprachpaket im Installer auswählen' }]
    : os === 'Darwin'
      ? [
          { label: 'Homebrew installieren (kostenloser macOS-Paketmanager)', url: 'https://brew.sh' },
          { label: 'Diesen Assistenten erneut öffnen – er richtet Tesseract dann automatisch ein' },
        ]
      : pkg === 'apt'
        ? [{ label: 'Terminal öffnen und folgendes eingeben:', hinweis: 'sudo apt install tesseract-ocr tesseract-ocr-deu' }]
        : pkg === 'dnf'
          ? [{ label: 'Terminal öffnen und folgendes eingeben:', hinweis: 'sudo dnf install tesseract tesseract-langpack-deu' }]
          : [{ label: 'Terminal öffnen und folgendes eingeben:', hinweis: 'sudo pacman -S tesseract tesseract-data-deu' }]

  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Für gescannte Eingangsrechnungen und Kassenbons wird <strong>Tesseract OCR</strong> benötigt.
        Bitte einmalig installieren:
      </p>
      <ol className="space-y-2">
        {schritte.map((s, i) => (
          <li key={i} className="text-sm text-slate-600 dark:text-slate-300 flex gap-2">
            <span className="shrink-0 w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 text-xs flex items-center justify-center font-medium">{i + 1}</span>
            <span>
              {s.label}
              {s.url && (
                <button
                  type="button"
                  onClick={() => import('../../api/client').then(m => m.openUrl(s.url!))}
                  className="ml-1 text-blue-600 dark:text-blue-400 underline"
                >
                  {s.url.replace('https://', '')}
                </button>
              )}
              {s.hinweis && <span className="block mt-0.5 text-xs text-slate-400 font-mono">{s.hinweis}</span>}
            </span>
          </li>
        ))}
      </ol>
      <p className="text-xs text-slate-400 dark:text-slate-500">
        Nach der Installation RechnungsFee neu starten.
      </p>
    </div>
  )
}

/** Kleiner Hinweis-Banner der den Assistenten öffnet */
function OcrInstallHinweis() {
  const [zeigAssistent, setZeigAssistent] = useState(false)
  return (
    <>
      <div className="bg-orange-50 dark:bg-orange-950 border border-orange-200 dark:border-orange-800 rounded-lg px-4 py-3 flex items-center justify-between gap-3">
        <div className="space-y-0.5">
          <p className="text-xs font-semibold text-orange-700 dark:text-orange-300">
            🔍 Texterkennung (OCR) nicht verfügbar
          </p>
          <p className="text-xs text-orange-600 dark:text-orange-400">
            Für gescannte Belege und Kassenbons wird Tesseract OCR benötigt.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setZeigAssistent(true)}
          className="shrink-0 px-3 py-1.5 bg-orange-600 hover:bg-orange-700 text-white text-xs font-medium rounded-lg transition-colors"
        >
          Einrichten →
        </button>
      </div>
      {zeigAssistent && <TesseractAssistentModal onClose={() => setZeigAssistent(false)} />}
    </>
  )
}

// ---------------------------------------------------------------------------
// Status-Badge
// ---------------------------------------------------------------------------

function LieferscheinStatusBadge({ r }: { r: { lieferschein_zu_rechnung_id: number | null; lieferschein_rechnung_ist_entwurf: boolean | null } }) {
  if (!r.lieferschein_zu_rechnung_id)
    return <span className="text-xs font-medium px-2 py-0.5 rounded-full border bg-slate-100 text-slate-600 border-slate-300 dark:bg-slate-700 dark:text-slate-300 dark:border-slate-600">Nicht abgerechnet</span>
  if (r.lieferschein_rechnung_ist_entwurf)
    return <span className="text-xs font-medium px-2 py-0.5 rounded-full border bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800">Rechnungsentwurf</span>
  return <span className="text-xs font-medium px-2 py-0.5 rounded-full border bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800">Abgerechnet</span>
}

function StatusBadge({ status }: { status: 'offen' | 'teilweise' | 'bezahlt' | 'uneinbringlich' }) {
  const cfg = {
    offen:           { cls: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-800',             label: 'Offen' },
    teilweise:       { cls: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800', label: 'Teilweise' },
    bezahlt:         { cls: 'bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800', label: 'Bezahlt' },
    uneinbringlich:  { cls: 'bg-slate-100 text-slate-500 border-slate-300 dark:bg-slate-700 dark:text-slate-400 dark:border-slate-600', label: 'Uneinbringlich' },
  }[status] ?? { cls: 'bg-slate-100 text-slate-500 border-slate-300', label: status }
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${cfg.cls}`}>
      {cfg.label}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Zahlungs-Dialog
// ---------------------------------------------------------------------------

type SplitZeile = { beschreibung: string; betrag: string; kategorie_id: string }

function ZahlungsDialog({
  rechnung,
  onClose,
  onSuccess,
}: {
  rechnung: Rechnung
  onClose: () => void
  onSuccess: (result: BarZahlungResult) => void
}) {
  const qc = useQueryClient()
  const istGutschrift = rechnung.dokument_typ === 'Gutschrift'
  const restbetrag = parseFloat(rechnung.brutto_gesamt) - parseFloat(rechnung.bezahlt_betrag)
  const [katModus, setKatModus] = useState<KontorahmenModus>(getKontorahmenModus)
  useEffect(() => {
    const h = (e: StorageEvent) => { if (e.key === KONTORAHMEN_LS_KEY) setKatModus((e.newValue ?? '') as KontorahmenModus) }
    window.addEventListener('storage', h)
    return () => window.removeEventListener('storage', h)
  }, [])
  const [betrag, setBetrag] = useState(Math.abs(restbetrag).toFixed(2).replace('.', ','))
  const [datum, setDatum] = useState(heuteIso())
  const [zahlungsart, setZahlungsart] = useState<'Bar' | 'Karte' | 'PayPal' | 'Bank'>('Bar')
  const [beschreibung, setBeschreibung] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)

  // Skonto
  const skontoFrist: string | null = (rechnung.skonto_prozent != null && rechnung.skonto_tage != null)
    ? (() => {
        const d = new Date(rechnung.datum)
        d.setDate(d.getDate() + rechnung.skonto_tage!)
        return d.toISOString().slice(0, 10)
      })()
    : null
  const skontoVerfuegbar = !istGutschrift && rechnung.typ === 'ausgang' && skontoFrist !== null && datum <= skontoFrist
  const berechneterSkontoBetrag = skontoVerfuegbar
    ? Math.round(parseFloat(rechnung.brutto_gesamt) * rechnung.skonto_prozent! / 100 * 100) / 100
    : 0
  const [skontoAktiv, setSkontoAktiv] = useState(false)

  // Eingangsrechnung: Kategorie bei Zahlung (Schritt 6+7)
  // rechnung.kategorie_id ist nach erster Teilzahlung gesetzt → Vorausfüllung (Schritt 7)
  const alleKategorienGesetzt = rechnung.positionen.every(p => p.kategorie_id != null)
  const irgendwelcheKategorienGesetzt = rechnung.positionen.some(p => p.kategorie_id != null)
  const [kategorieId, setKategorieId] = useState<string>(() => {
    if (rechnung.kategorie_id) return String(rechnung.kategorie_id)
    if (rechnung.positionen.length === 1 && rechnung.positionen[0].kategorie_id != null)
      return String(rechnung.positionen[0].kategorie_id)
    return ''
  })
  const [showNeuKategorie, setShowNeuKategorie] = useState(false)
  const [splitModus, setSplitModus] = useState(
    rechnung.positionen.length > 1 && irgendwelcheKategorienGesetzt
  )
  const [splitZeilen, setSplitZeilen] = useState<SplitZeile[]>(() =>
    rechnung.positionen.map((pos) => ({
      beschreibung: pos.beschreibung,
      betrag: (parseFloat(pos.brutto) * parseFloat(pos.menge)).toFixed(2).replace('.', ','),
      kategorie_id: String(pos.kategorie_id ?? ''),
    }))
  )

  const { data: kategorien } = useQuery({ queryKey: ['kategorien', 'aktiv'], queryFn: () => getKategorien(true) })
  const { data: kassenstandData } = useQuery({ queryKey: ['kassenstand'], queryFn: getKassenstand })
  const kassenstand = parseFloat(kassenstandData?.kassenstand ?? '0')
  const istBarAusgabe = rechnung.typ === 'eingang' && zahlungsart === 'Bar'
  const aufwandKat = (kategorien ?? []).filter((k) => k.kontenart === 'Aufwand')
  const anlageKat  = (kategorien ?? []).filter((k) => k.kontenart === 'Anlage')

  const mutation = useMutation({
    mutationFn: (data: BarZahlungCreate) => barZahlungErstellen(rechnung.id, data),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
      qc.invalidateQueries({ queryKey: ['journal'] })
      qc.invalidateQueries({ queryKey: ['auftraege'] })
      qc.invalidateQueries({ queryKey: ['vorlage-rechnungen'] })
      onSuccess(result)
    },
    onError: (e: Error) => setFehler(e.message),
  })

  const betragDecimal = parseFloat(betrag.replace(',', '.'))
  const kassenstandUeberschritten = istBarAusgabe && !isNaN(betragDecimal) && betragDecimal > kassenstand
  const artLabel = rechnung.typ === 'ausgang' ? 'Einnahme' : 'Ausgabe'
  const splitSumme = splitZeilen.reduce((s, z) => s + (parseFloat(z.betrag.replace(',', '.')) || 0), 0)
  const splitSummeOK = !isNaN(betragDecimal) && Math.abs(splitSumme - betragDecimal) < 0.005

  function updateSplitZeile(i: number, field: keyof SplitZeile, val: string) {
    setSplitZeilen((prev) => prev.map((z, idx) => idx === i ? { ...z, [field]: val } : z))
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (isNaN(betragDecimal) || betragDecimal <= 0) {
      setFehler('Bitte einen gültigen Betrag eingeben.')
      return
    }
    // Gutschrift: Frontend schickt positiven Betrag, Backend negiert intern

    if (datum > new Date().toISOString().slice(0, 10)) {
      setFehler('Das Zahlungsdatum darf nicht in der Zukunft liegen.')
      return
    }

    const payload: BarZahlungCreate = {
      betrag: betragDecimal.toFixed(2),
      datum,
      zahlungsart,
      beschreibung: beschreibung || undefined,
      ...(skontoAktiv && berechneterSkontoBetrag > 0 ? { skonto_betrag: berechneterSkontoBetrag.toFixed(2) } : {}),
    }

    if (rechnung.typ === 'eingang') {
      if (splitModus) {
        if (!splitSummeOK) {
          setFehler(`Split-Summe (${splitSumme.toFixed(2)} €) stimmt nicht mit Zahlungsbetrag (${betragDecimal.toFixed(2)} €) überein.`)
          return
        }
        const ohneKategorie = splitZeilen.map((z, i) => (!z.kategorie_id ? rechnung.positionen[i]?.beschreibung || `Position ${i + 1}` : null)).filter(Boolean)
        if (ohneKategorie.length > 0) {
          setFehler(`Fehlende Kategorie bei: ${ohneKategorie.join(', ')}`)
          return
        }
        payload.split = splitZeilen.map((z): ZahlungSplitPosition => ({
          kategorie_id: parseInt(z.kategorie_id),
          betrag: parseFloat(z.betrag.replace(',', '.')).toFixed(2),
          beschreibung: z.beschreibung,
        }))
      } else {
        if (!kategorieId) {
          setFehler('Bitte eine Kategorie wählen.')
          return
        }
        payload.kategorie_id = parseInt(kategorieId)
      }
    }

    mutation.mutate(payload)
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md">
        <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800 dark:text-slate-100">
            {istGutschrift ? 'Rückerstattung buchen' : rechnung.typ === 'ausgang' ? 'Zahlung kassieren' : 'Zahlung buchen'}
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

          {/* Skonto-Hinweis */}
          {skontoVerfuegbar && (
            <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-xl p-3 text-sm">
              <p className="text-green-800 dark:text-green-200 font-medium">
                {rechnung.skonto_prozent}% Skonto verfügbar (bis {skontoFrist!.split('-').reverse().join('.')})
              </p>
              <p className="text-green-700 dark:text-green-300 mt-0.5">
                Netto: <strong>{formatEuro(parseFloat(rechnung.brutto_gesamt) - berechneterSkontoBetrag)}</strong>{' '}
                statt {formatEuro(parseFloat(rechnung.brutto_gesamt))} — Nachlass: {formatEuro(berechneterSkontoBetrag)}
              </p>
              <div className="flex gap-2 mt-2">
                <button
                  type="button"
                  onClick={() => {
                    setSkontoAktiv(true)
                    setBetrag((restbetrag - berechneterSkontoBetrag).toFixed(2).replace('.', ','))
                  }}
                  className={`flex-1 py-1.5 text-xs rounded-lg border transition-colors ${
                    skontoAktiv
                      ? 'bg-green-600 text-white border-green-600'
                      : 'bg-white dark:bg-slate-800 text-green-700 dark:text-green-300 border-green-300 dark:border-green-700 hover:bg-green-50 dark:hover:bg-green-900'
                  }`}
                >
                  Skonto anwenden
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSkontoAktiv(false)
                    setBetrag(restbetrag.toFixed(2).replace('.', ','))
                  }}
                  className={`flex-1 py-1.5 text-xs rounded-lg border transition-colors ${
                    !skontoAktiv
                      ? 'bg-slate-600 text-white border-slate-600'
                      : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-300 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-700'
                  }`}
                >
                  Ohne Skonto
                </button>
              </div>
            </div>
          )}

          {/* Datum */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Zahlungsdatum</label>
            <input
              type="date"
              value={datum}
              max={new Date().toISOString().slice(0, 10)}
              onChange={guardedDateChange(setDatum)}
              className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
            />
          </div>

          {/* Zahlungsart */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Zahlungsart</label>
            <div className="flex rounded-lg border border-slate-300 dark:border-slate-600 overflow-hidden text-sm">
              {([['Bar', 'Bar'], ['Karte', 'Karte'], ['PayPal', 'PayPal'], ['Bank', 'Bank']] as const).map(([val, label]) => (
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

          {/* Kategorie / Split – nur Eingangsrechnungen */}
          {rechnung.typ === 'eingang' && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-200">
                  Kategorie *
                </label>
                {rechnung.positionen.length > 1 && (
                  <button
                    type="button"
                    onClick={() => setSplitModus((v) => !v)}
                    className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    {splitModus ? '← Einfach buchen' : 'Splitbuchung →'}
                  </button>
                )}
              </div>
              {/* Alle Kategorien aus Positionen gesetzt: Warnung bei fehlendem Split */}
              {!splitModus && !alleKategorienGesetzt && irgendwelcheKategorienGesetzt && rechnung.positionen.length > 1 && (
                <div className="flex items-start gap-2 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg px-3 py-2 text-xs text-amber-800 dark:text-amber-300">
                  <span className="shrink-0">⚠</span>
                  <span>Einzelne Positionen haben bereits eine Kategorie. Wechsle zu Splitbuchung um alle zu übernehmen.</span>
                </div>
              )}

              {splitModus ? (
                <div className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
                  <table className="w-full text-xs">
                    <thead className="bg-slate-50 dark:bg-slate-900">
                      <tr>
                        <th className="px-3 py-2 text-left font-medium text-slate-500 dark:text-slate-400">Position</th>
                        <th className="px-3 py-2 text-right font-medium text-slate-500 dark:text-slate-400 w-24">Betrag (€)</th>
                        <th className="px-3 py-2 text-left font-medium text-slate-500 dark:text-slate-400 w-36">Kategorie</th>
                      </tr>
                    </thead>
                    <tbody>
                      {splitZeilen.map((z, i) => (
                        <tr key={i} className={`border-t border-slate-100 dark:border-slate-700 ${!z.kategorie_id ? 'bg-amber-50 dark:bg-amber-950/50' : ''}`}>
                          <td className="px-3 py-1.5 text-slate-700 dark:text-slate-200">{z.beschreibung}</td>
                          <td className="px-2 py-1.5">
                            <input
                              type="text"
                              value={z.betrag}
                              onChange={(e) => updateSplitZeile(i, 'betrag', e.target.value)}
                              className="w-full border-0 outline-none bg-transparent text-right text-slate-700 dark:text-slate-200"
                            />
                          </td>
                          <td className="px-2 py-1.5">
                            <select
                              value={z.kategorie_id}
                              onChange={(e) => updateSplitZeile(i, 'kategorie_id', e.target.value)}
                              className="w-full border-0 outline-none bg-transparent text-xs text-slate-700 dark:text-slate-200"
                            >
                              <option value="">— wählen —</option>
                              <optgroup label="Betriebsausgaben">
                                {aufwandKat.map((k) => <option key={k.id} value={String(k.id)}>{katLabel(k, katModus)}</option>)}
                              </optgroup>
                              {anlageKat.length > 0 && (
                                <optgroup label="Investitionen">
                                  {anlageKat.map((k) => <option key={k.id} value={String(k.id)}>{katLabel(k, katModus)}</option>)}
                                </optgroup>
                              )}
                            </select>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
                      <tr>
                        <td className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300">Summe</td>
                        <td className={`px-3 py-1.5 text-right text-xs font-semibold ${splitSummeOK ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                          {formatEuro(splitSumme)}
                        </td>
                        <td className="px-3 py-1.5 text-xs text-slate-400 dark:text-slate-500">
                          {splitSummeOK ? '✓ passt' : `≠ ${formatEuro(betragDecimal)}`}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              ) : rechnung.positionen.length === 1 && alleKategorienGesetzt ? (
                <div className="flex items-center gap-2 bg-emerald-50 dark:bg-emerald-950 border border-emerald-200 dark:border-emerald-800 rounded-lg px-3 py-2 text-sm text-emerald-800 dark:text-emerald-300">
                  <span className="shrink-0">✓</span>
                  <span>
                    Aus Rechnung: <strong>{(kategorien ?? []).find(k => String(k.id) === kategorieId)?.name ?? '–'}</strong>
                  </span>
                </div>
              ) : (
                <div className="flex gap-1">
                  <select
                    value={kategorieId}
                    onChange={(e) => setKategorieId(e.target.value)}
                    className="flex-1 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
                  >
                    <option value="">— Kategorie wählen —</option>
                    <optgroup label="Betriebsausgaben">
                      {aufwandKat.map((k) => <option key={k.id} value={String(k.id)}>{k.name}</option>)}
                    </optgroup>
                    {anlageKat.length > 0 && (
                      <optgroup label="Investitionen">
                        {anlageKat.map((k) => <option key={k.id} value={String(k.id)}>{k.name}</option>)}
                      </optgroup>
                    )}
                  </select>
                  <button
                    type="button"
                    onClick={() => setShowNeuKategorie(true)}
                    title="Neue Kategorie anlegen"
                    className="shrink-0 px-2.5 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 text-base leading-none"
                  >
                    +
                  </button>
                </div>
              )}
              {showNeuKategorie && (
                <KategorieErstellenModal
                  kontenPflicht
                  onClose={() => setShowNeuKategorie(false)}
                  onSave={(neu) => { setShowNeuKategorie(false); setKategorieId(String(neu.id)) }}
                />
              )}
            </div>
          )}

          {/* Vorschau */}
          {!isNaN(betragDecimal) && betragDecimal > 0 && (
            <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-xl p-3 text-sm">
              <p className="text-blue-700 dark:text-blue-300 font-medium">Journalbuchung wird erstellt:</p>
              <p className="text-blue-600 dark:text-blue-400 mt-0.5">
                {artLabel} {formatEuro(betragDecimal)} via {zahlungsart}
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
  onGutschriftCreated,
  onRechnungAusLs,
  onSelectId,
  onLieferscheinAusRechnung,
  onFinalisiert,
  onZahlungErfasst,
}: {
  rechnung: Rechnung
  onClose: () => void
  onEdit: () => void
  onDelete: () => void
  onGutschriftCreated?: (gs: Rechnung) => void
  onRechnungAusLs?: (id: number) => void
  onSelectId?: (id: number, isLieferschein?: boolean, filterRechnungId?: number) => void
  onLieferscheinAusRechnung?: (id: number) => void
  onFinalisiert?: (r: Rechnung) => void
  onZahlungErfasst?: (r: Rechnung) => void
}) {
  const navigate = useNavigate()
  const [zahlungsDialog, setZahlungsDialog] = useState(false)
  const [zeigStornoEingabe, setZeigStornoEingabe] = useState(false)
  const [stornoGrund, setStornoGrund] = useState<string | null>(null)
  const [stornoSonstiges, setStornoSonstiges] = useState('')
  const [zeigForderungsausfall, setZeigForderungsausfall] = useState(false)
  const [zeigMailEingabe, setZeigMailEingabe] = useState(false)
  const [mailAdresse, setMailAdresse] = useState('')
  const [zeigMailDialog, setZeigMailDialog] = useState(false)
  const [zeigSmtpHinweis, setZeigSmtpHinweis] = useState(false)
  const [pdfLaeuft, setPdfLaeuft] = useState(false)
  const [pdfHinweis, setPdfHinweis] = useState(false)
  const [belegFehler, setBelegFehler] = useState<string | null>(null)
  // Ref statt State: _fetchPdfBlob liest immer den aktuellen Wert,
  // unabhängig vom Closure-Zeitpunkt des letzten Renders.
  const ausgegebenRef = useRef(rechnung.ausgegeben)
  // State nur für Button-Text / InfoTooltip (braucht Re-Render)
  const [lokalAusgegeben, setLokalAusgegeben] = useState(rechnung.ausgegeben)
  const qc = useQueryClient()

  const belegUploadMutation = useMutation({
    mutationFn: (datei: File) => uploadBeleg(rechnung.id, datei),
    onSuccess: () => {
      setBelegFehler(null)
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
    },
    onError: (e: Error) => setBelegFehler(e.message),
  })

  const belegDeleteMutation = useMutation({
    mutationFn: () => deleteBeleg(rechnung.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rechnungen'] }),
    onError: (e: Error) => setBelegFehler(e.message),
  })

  async function _openBeleg() {
    const url = await getBelegUrl(rechnung.id)
    await openUrl(url)
  }
  async function _openBelegPdfa() {
    const url = await getBelegPdfaUrl(rechnung.id)
    await openUrl(url)
  }
  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen, staleTime: 1000 * 60 * 10 })

  const restbetrag = parseFloat(rechnung.brutto_gesamt) - parseFloat(rechnung.bezahlt_betrag)
  const fortschritt = Math.abs(parseFloat(rechnung.brutto_gesamt)) > 0.004
    ? Math.min((Math.abs(parseFloat(rechnung.bezahlt_betrag)) / Math.abs(parseFloat(rechnung.brutto_gesamt))) * 100, 100)
    : 0

  const hatZahlungsoption = Math.abs(restbetrag) > 0.004 && !rechnung.storniert && !rechnung.ist_entwurf
    && rechnung.zahlungsstatus !== 'uneinbringlich'
    && rechnung.dokument_typ !== 'Lieferschein'

  const partnerEmail = rechnung.typ === 'ausgang'
    ? rechnung.kunde_email
    : rechnung.lieferant_email

  const STORNO_GRUENDE = ['Doppelt ausgestellt', 'Falsche Adresse', 'Kundenwiderspruch', 'Sonstiges…']

  const stornoMutation = useMutation({
    mutationFn: (grund: string) => stornoRechnung(rechnung.id, grund),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
      qc.invalidateQueries({ queryKey: ['vorlage-rechnungen'] })
      setZeigStornoEingabe(false)
      setStornoGrund(null)
      setStornoSonstiges('')
    },
  })

  function handleStornoSubmit() {
    const grund = stornoGrund === 'Sonstiges…' ? stornoSonstiges.trim() : stornoGrund
    if (!grund) return
    stornoMutation.mutate(grund)
  }

  const finalisiereMutation = useMutation({
    mutationFn: () => finalisiereRechnung(rechnung.id),
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
      qc.invalidateQueries({ queryKey: ['auftraege'] })
      qc.invalidateQueries({ queryKey: ['vorlage-rechnungen'] })
      onFinalisiert?.(updated)
    },
    onError: (e: Error) => alert(e.message),
  })

  const gutschriftMutation = useMutation({
    mutationFn: () => createGutschrift(rechnung.id),
    onSuccess: (gs) => {
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
      onGutschriftCreated?.(gs)
    },
    onError: (e: Error) => alert(e.message),
  })

  const forderungsausfallMutation = useMutation({
    mutationFn: () => forderungsausbuchenRechnung(rechnung.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
      qc.invalidateQueries({ queryKey: ['vorlage-rechnungen'] })
      setZeigForderungsausfall(false)
    },
    onError: (e: Error) => alert(e.message),
  })

  /** Lädt das PDF als Blob. Liest ausgegebenRef.current (immer aktuell, kein Closure-Problem)
   *  um kopie=true zu senden wenn das Dokument bereits ausgegeben wurde. */
  async function _fetchPdfBlob(): Promise<string> {
    const base = await getApiBase()
    const params = ausgegebenRef.current ? '?kopie=true' : ''
    const resp = await fetch(`${base}/rechnungen/${rechnung.id}/pdf${params}`)
    const blob = await resp.blob()
    if (!ausgegebenRef.current) {
      ausgegebenRef.current = true      // sofort für nächsten Aufruf
      setLokalAusgegeben(true)          // Re-Render für Button-Text
    }
    return URL.createObjectURL(blob)
  }

  function _zeigeBlob(blobUrl: string) {
    if (isTauri()) {
      openInPdfWindow(blobUrl, 'Rechnung')
    } else {
      window.open(blobUrl, '_blank')
    }
    setTimeout(() => URL.revokeObjectURL(blobUrl), 120_000)
  }

  async function handleDrucken() {
    const blobUrl = await _fetchPdfBlob()
    qc.invalidateQueries({ queryKey: ['rechnungen'] })
    if (isTauri()) {
      openInPdfWindow(blobUrl, 'Rechnung drucken')
      setTimeout(() => URL.revokeObjectURL(blobUrl), 120_000)
    } else {
      const win = window.open(blobUrl, '_blank')
      if (win) win.addEventListener('load', () => win.print())
      setTimeout(() => URL.revokeObjectURL(blobUrl), 120_000)
    }
  }

  async function handlePdfOeffnen() {
    const blobUrl = await _fetchPdfBlob()
    qc.invalidateQueries({ queryKey: ['rechnungen'] })
    _zeigeBlob(blobUrl)
  }

  async function handleMail() {
    if (unternehmen?.smtp_aktiv) { setZeigMailDialog(true); return }
    const email = partnerEmail || mailAdresse.trim()
    if (!email) { setZeigMailEingabe(true); return }

    setPdfLaeuft(true)
    setPdfHinweis(false)
    try {
      await downloadPdfForMail(rechnung.id)
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
    setZeigSmtpHinweis(true)
    setTimeout(() => setZeigSmtpHinweis(false), 6000)
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
          {rechnung.ist_entwurf || (rechnung.dokument_typ === 'Gutschrift' && rechnung.zahlungsstatus !== 'bezahlt') ? (
            <button
              onClick={handlePdfOeffnen}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400"
            >
              📄 Vorschau
            </button>
          ) : (
            <>
              <button
                onClick={handleDrucken}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
              >
                🖨️ {lokalAusgegeben ? 'Kopie drucken' : 'Drucken'}
              </button>
              <button
                onClick={handlePdfOeffnen}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
              >
                📄 {lokalAusgegeben ? 'Kopie öffnen' : 'PDF öffnen'}
              </button>
              {lokalAusgegeben && (
                <InfoTooltip text="Diese Rechnung wurde bereits ausgegeben (gedruckt, als PDF geöffnet oder per Mail versandt). Alle weiteren Ausgaben werden automatisch als Kopie markiert, damit Doppelsendungen erkennbar sind." side="bottom" align="right" />
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
            </>
          )}
          {rechnung.dokument_typ === 'Lieferschein' && !rechnung.lieferschein_zu_rechnung_id && onRechnungAusLs && (
            <button
              onClick={() => onRechnungAusLs(rechnung.id)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-green-300 dark:border-green-700 rounded-lg hover:bg-green-50 dark:hover:bg-green-950 text-green-700 dark:text-green-400 font-medium"
            >
              → Rechnung erstellen
            </button>
          )}
          {rechnung.dokument_typ === 'Lieferschein' && rechnung.lieferschein_zu_rechnung_id && (
            <button
              onClick={() => onSelectId?.(rechnung.lieferschein_zu_rechnung_id!)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg font-mono ${
                rechnung.lieferschein_rechnung_ist_entwurf
                  ? 'border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-950'
                  : 'border-green-300 dark:border-green-700 text-green-700 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-950'
              }`}
            >
              → {rechnung.lieferschein_zu_rechnung_nr ?? `Rechnung #${rechnung.lieferschein_zu_rechnung_id}`}
              {rechnung.lieferschein_rechnung_ist_entwurf && <span className="font-sans text-xs opacity-70">(Entwurf)</span>}
            </button>
          )}
          {!rechnung.ist_entwurf && !rechnung.storniert && rechnung.typ === 'ausgang' && rechnung.dokument_typ !== 'Gutschrift' && rechnung.dokument_typ !== 'Lieferschein' && !zeigStornoEingabe && onLieferscheinAusRechnung && (
            rechnung.hat_lieferschein ? (
              <button
                onClick={() => onSelectId?.(rechnung.id, true, rechnung.id)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-teal-200 dark:border-teal-800 rounded-lg hover:bg-teal-50 dark:hover:bg-teal-950 text-teal-700 dark:text-teal-400"
              >
                → {rechnung.lieferschein_anzahl === 1 && rechnung.linked_lieferschein_nr
                  ? rechnung.linked_lieferschein_nr
                  : `${rechnung.lieferschein_anzahl} Lieferschein${rechnung.lieferschein_anzahl !== 1 ? 'e' : ''}`}
              </button>
            ) : (
              <button
                onClick={() => onLieferscheinAusRechnung(rechnung.id)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-teal-200 dark:border-teal-800 rounded-lg hover:bg-teal-50 dark:hover:bg-teal-950 text-teal-700 dark:text-teal-400"
              >
                → Lieferschein erstellen
              </button>
            )
          )}
          {!rechnung.ist_entwurf && !rechnung.storniert && rechnung.typ === 'ausgang' && rechnung.dokument_typ !== 'Gutschrift' && rechnung.dokument_typ !== 'Lieferschein' && !zeigStornoEingabe && (
            <button
              onClick={() => gutschriftMutation.mutate()}
              disabled={gutschriftMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-amber-200 dark:border-amber-800 rounded-lg hover:bg-amber-50 dark:hover:bg-amber-950 text-amber-700 dark:text-amber-400 disabled:opacity-50"
            >
              {gutschriftMutation.isPending ? '…' : '↩ Gutschrift'}
            </button>
          )}
          {!rechnung.ist_entwurf && !rechnung.storniert && !zeigStornoEingabe && !zeigForderungsausfall
            && rechnung.dokument_typ !== 'Lieferschein' && (
            <button
              onClick={() => setZeigStornoEingabe(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-red-200 dark:border-red-800 rounded-lg hover:bg-red-50 dark:hover:bg-red-950 text-red-600 dark:text-red-400"
            >
              ✕ Stornieren
            </button>
          )}
          {!rechnung.ist_entwurf && !rechnung.storniert && !zeigStornoEingabe && !zeigForderungsausfall
            && rechnung.dokument_typ !== 'Lieferschein'
            && (rechnung.zahlungsstatus === 'offen' || rechnung.zahlungsstatus === 'teilweise') && (
            <button
              onClick={() => setZeigForderungsausfall(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400"
            >
              ⚠ Uneinbringlich
            </button>
          )}
          {rechnung.zahlungsstatus === 'uneinbringlich' && rechnung.dokument_typ !== 'Lieferschein' && (
            <span className="self-center text-xs text-slate-400 dark:text-slate-500 italic">Uneinbringlich ausgebucht</span>
          )}
          {rechnung.storniert && (
            <span className="self-center text-xs text-slate-400 italic">Storniert</span>
          )}
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
            dokument={rechnung}
            dokumentTyp={rechnung.dokument_typ === 'Gutschrift' ? 'Rechnung' : (rechnung.dokument_typ as any) ?? 'Rechnung'}
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

        {/* Storno-Dialog */}
        {zeigStornoEingabe && (
          <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl px-3 py-3 space-y-2">
            <p className="text-sm font-medium text-red-800 dark:text-red-200">
              Warum wird diese Rechnung storniert?
            </p>
            {rechnung.zahlungen.length > 0 && (
              <p className="text-xs text-red-600 dark:text-red-400">
                Es werden {rechnung.zahlungen.length} Gegenbuchung{rechnung.zahlungen.length !== 1 ? 'en' : ''} im Journal erstellt.
              </p>
            )}
            <div className="flex flex-wrap gap-1.5">
              {STORNO_GRUENDE.map(g => (
                <button
                  key={g}
                  type="button"
                  onClick={() => { setStornoGrund(g); setStornoSonstiges('') }}
                  className={`px-2.5 py-1 rounded-lg text-xs border transition-colors ${
                    stornoGrund === g
                      ? 'bg-red-600 text-white border-red-600'
                      : 'border-red-300 dark:border-red-700 text-red-700 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-900'
                  }`}
                >
                  {g}
                </button>
              ))}
            </div>
            {stornoGrund === 'Sonstiges…' && (
              <input
                type="text"
                autoFocus
                placeholder="Begründung eingeben…"
                value={stornoSonstiges}
                onChange={e => setStornoSonstiges(e.target.value)}
                className="w-full text-sm border border-red-300 dark:border-red-700 rounded-lg px-3 py-1.5 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-red-400"
              />
            )}
            <div className="flex gap-2 pt-0.5">
              <button
                onClick={handleStornoSubmit}
                disabled={stornoMutation.isPending || !stornoGrund || (stornoGrund === 'Sonstiges…' && !stornoSonstiges.trim())}
                className="px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {stornoMutation.isPending ? '…' : 'Stornieren'}
              </button>
              <button
                onClick={() => { setZeigStornoEingabe(false); setStornoGrund(null); setStornoSonstiges('') }}
                className="px-3 py-1.5 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg text-sm hover:bg-slate-50 dark:hover:bg-slate-700"
              >
                Abbrechen
              </button>
            </div>
          </div>
        )}
        {stornoMutation.isError && (
          <p className="text-red-600 text-xs">{(stornoMutation.error as Error).message}</p>
        )}

        {/* Forderungsausfall-Dialog */}
        {zeigForderungsausfall && (
          <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-3 space-y-2">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
              Forderung als uneinbringlich ausbuchen?
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Restbetrag: <strong>{formatEuro(Math.abs(parseFloat(rechnung.brutto_gesamt) - parseFloat(rechnung.bezahlt_betrag)))}</strong>
              {!(unternehmen?.ist_kleinunternehmer) && ' · USt-Korrekturbuchung nach §17 UStG wird automatisch erstellt (zahlungsart=Keine)'}
            </p>
            <div className="flex gap-2 pt-0.5">
              <button
                onClick={() => forderungsausfallMutation.mutate()}
                disabled={forderungsausfallMutation.isPending}
                className="px-3 py-1.5 bg-slate-600 dark:bg-slate-500 text-white rounded-lg text-sm hover:bg-slate-700 dark:hover:bg-slate-400 disabled:opacity-40"
              >
                {forderungsausfallMutation.isPending ? '…' : 'Ausbuchen bestätigen'}
              </button>
              <button
                onClick={() => setZeigForderungsausfall(false)}
                className="px-3 py-1.5 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg text-sm hover:bg-slate-50 dark:hover:bg-slate-700"
              >
                Abbrechen
              </button>
            </div>
          </div>
        )}
        {forderungsausfallMutation.isError && (
          <p className="text-slate-600 text-xs">{(forderungsausfallMutation.error as Error).message}</p>
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
          {rechnung.dokument_typ !== 'Lieferschein' && (
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Rechnungsdatum</span>
              <span className="dark:text-slate-200">{formatDatum(rechnung.datum)}</span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-slate-500 dark:text-slate-400">
              {rechnung.leistung_bis ? 'Leistungszeitraum' : 'Leistungsdatum'}
            </span>
            <span className="dark:text-slate-200">
              {rechnung.leistung_bis
                ? `${formatDatum(rechnung.leistung_von ?? rechnung.datum)} – ${formatDatum(rechnung.leistung_bis)}`
                : formatDatum(rechnung.leistung_von ?? rechnung.datum)}
            </span>
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
                : rechnung.dokument_typ === 'Lieferschein'
                  ? <LieferscheinStatusBadge r={rechnung} />
                  : <StatusBadge status={rechnung.zahlungsstatus as 'offen' | 'teilweise' | 'bezahlt' | 'uneinbringlich'} />}
          </div>
          {rechnung.typ === 'ausgang' && rechnung.kunde_zugferd_aktiv && !rechnung.ist_entwurf && (
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">E-Rechnung</span>
              <span className="text-xs px-2 py-0.5 rounded border bg-violet-50 text-violet-700 border-violet-200 dark:bg-violet-950 dark:text-violet-300 dark:border-violet-800">ZUGFeRD ✓</span>
            </div>
          )}
          {rechnung.storniert && rechnung.storno_grund && (
            <div className="flex justify-between gap-2">
              <span className="text-slate-500 dark:text-slate-400 shrink-0">Storno-Grund</span>
              <span className="text-slate-600 dark:text-slate-300 text-right text-xs">{rechnung.storno_grund}</span>
            </div>
          )}
          {rechnung.gutschrift_zu_rechnung_nr && (
            <div className="flex justify-between gap-2">
              <span className="text-slate-500 dark:text-slate-400 shrink-0">Gutschrift zur Rechnung</span>
              <span className="text-amber-700 dark:text-amber-400 text-xs font-medium">{rechnung.gutschrift_zu_rechnung_nr}</span>
            </div>
          )}
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
                    {rechnung.dokument_typ === 'Lieferschein' ? <>
                      <th className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 font-medium">Menge</th>
                      <th className="px-3 py-2 text-left text-slate-500 dark:text-slate-400 font-medium">Einheit</th>
                    </> : <>
                      <th className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 font-medium">Menge</th>
                      <th className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 font-medium">Einzelpreis</th>
                      <th className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 font-medium">USt</th>
                      <th className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 font-medium">Gesamt</th>
                    </>}
                  </tr>
                </thead>
                <tbody>
                  {rechnung.positionen.map((pos) => {
                    const posRabatt = parseFloat(pos.rabatt_prozent ?? '0') || 0
                    const menge = parseFloat(pos.menge)
                    const nettoEP = parseFloat(pos.netto)            // Stückpreis original (netto)
                    const gesamtVorRabatt = nettoEP * menge           // Gesamtpreis vor Rabatt
                    const rabattAbsNetto = posRabatt > 0
                      ? (nettoEP - (parseFloat(pos.brutto) - parseFloat(pos.ust_betrag))) * menge
                      : 0
                    return (
                    <>
                    <tr key={pos.id} className="border-t border-slate-100 dark:border-slate-700">
                      <td className="px-3 py-2 text-slate-700 dark:text-slate-200">{pos.beschreibung}</td>
                      {rechnung.dokument_typ === 'Lieferschein' ? <>
                        <td className="px-3 py-2 text-right dark:text-slate-200">{formatMenge(pos.menge)}</td>
                        <td className="px-3 py-2 text-slate-400 dark:text-slate-500">{pos.einheit}</td>
                      </> : <>
                        <td className="px-3 py-2 text-right text-slate-500 dark:text-slate-400">
                          {formatMenge(pos.menge)}{pos.einheit ? ` ${pos.einheit}` : ''}
                        </td>
                        <td className="px-3 py-2 text-right dark:text-slate-200">
                          {formatEuro(nettoEP.toFixed(2))}
                        </td>
                        <td className="px-3 py-2 text-right text-slate-400 dark:text-slate-500">
                          {pos.differenzbesteuerung
                            ? <span className="text-xs font-medium text-amber-600 dark:text-amber-400">§25a</span>
                            : `${pos.ust_satz}%`
                          }
                        </td>
                        <td className="px-3 py-2 text-right font-medium dark:text-slate-200">
                          {formatEuro(gesamtVorRabatt.toFixed(2))}
                        </td>
                      </>}
                    </tr>
                    {posRabatt > 0 && rechnung.dokument_typ !== 'Lieferschein' && (
                      <tr key={`${pos.id}-rabatt`} className="bg-slate-50 dark:bg-slate-900/50">
                        <td colSpan={2} className="px-3 pb-1.5 pt-0 text-xs text-slate-400 dark:text-slate-500 italic pl-5">
                          {posRabatt} % Rabatt
                        </td>
                        <td className="px-3 pb-1.5 pt-0 text-right text-xs text-slate-400 dark:text-slate-500 italic" colSpan={2}></td>
                        <td className="px-3 pb-1.5 pt-0 text-right text-xs text-slate-400 dark:text-slate-500 italic">
                          − {formatEuro(rabattAbsNetto.toFixed(2))}
                        </td>
                      </tr>
                    )}
                    </>
                    )
                  })}
                </tbody>
                {rechnung.dokument_typ !== 'Lieferschein' && (() => {
                  const reRabatt = parseFloat(String(rechnung.rabatt_prozent ?? '0')) || 0
                  const posSumNetto = rechnung.positionen.reduce((s, p) => s + parseFloat(p.netto) * parseFloat(p.menge), 0)
                  const rabattNetto = posSumNetto * reRabatt / 100
                  const ustGesamt = parseFloat(rechnung.ust_gesamt)
                  return (
                  <tfoot className="bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-700">
                    {reRabatt > 0 && (
                      <tr>
                        <td colSpan={4} className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 text-xs">Zwischensumme Netto</td>
                        <td className="px-3 py-2 text-right text-slate-600 dark:text-slate-300">{formatEuro(posSumNetto.toFixed(2))}</td>
                      </tr>
                    )}
                    {reRabatt > 0 && (
                      <tr>
                        <td colSpan={4} className="px-3 py-2 text-right text-slate-400 dark:text-slate-500 text-xs">Rabatt {reRabatt} %</td>
                        <td className="px-3 py-2 text-right text-slate-400 dark:text-slate-500 text-xs">− {formatEuro(rabattNetto.toFixed(2))}</td>
                      </tr>
                    )}
                    <tr>
                      <td colSpan={4} className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 text-xs">Netto</td>
                      <td className="px-3 py-2 text-right text-slate-600 dark:text-slate-300">{formatEuro(rechnung.netto_gesamt)}</td>
                    </tr>
                    {ustGesamt !== 0 && (
                      <tr>
                        <td colSpan={4} className="px-3 py-2 text-right text-slate-400 dark:text-slate-500 text-xs">USt</td>
                        <td className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 text-xs">{formatEuro(rechnung.ust_gesamt)}</td>
                      </tr>
                    )}
                    <tr>
                      <td colSpan={4} className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 font-medium">Gesamt</td>
                      <td className="px-3 py-2 text-right font-bold text-slate-800 dark:text-slate-100">{formatEuro(rechnung.brutto_gesamt)}</td>
                    </tr>
                  </tfoot>
                  )
                })()}
              </table>
            </div>
          </div>
        )}

        {/* Zahlungsstatus */}
        {rechnung.dokument_typ !== 'Lieferschein' && <div>
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2 flex items-center gap-1">
            Zahlung
            <InfoTooltip text="Offen: noch keine Zahlung eingegangen. Teilweise: mindestens eine Teilzahlung verbucht. Bezahlt: Rechnungsbetrag vollständig beglichen. Zahlungen werden automatisch als Journaleinträge gespeichert." />
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
        </div>}

        {/* Verknüpfte Zahlungen */}
        {rechnung.zahlungen.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
              Verknüpfte Journalbuchungen
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

        {rechnung.einleitungstext && (
          <div>
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Einleitungstext</p>
            <p className="text-sm text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2 whitespace-pre-wrap">{rechnung.einleitungstext}</p>
          </div>
        )}

        {rechnung.notizen && (
          <div>
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Notizen</p>
            <p className="text-sm text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2">{rechnung.notizen}</p>
          </div>
        )}

        {/* Beleg-Anhang – nur für Eingangsrechnungen */}
        {rechnung.typ === 'eingang' && <div>
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">Beleg</p>
          {rechnung.beleg ? (
            <div className="bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2.5 space-y-1.5">
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <button
                    onClick={_openBeleg}
                    className="text-sm text-blue-600 dark:text-blue-400 hover:underline truncate block text-left"
                    title={rechnung.beleg.original_name}
                  >
                    📄 {rechnung.beleg.original_name}
                  </button>
                  <span className="text-xs text-slate-400 dark:text-slate-500">
                    {rechnung.beleg.dateigroesse ? `${Math.round(rechnung.beleg.dateigroesse / 1024)} KB · ` : ''}
                    {rechnung.beleg.hochgeladen_am.slice(0, 10)}
                  </span>
                </div>
                <button
                  onClick={() => belegDeleteMutation.mutate()}
                  disabled={belegDeleteMutation.isPending}
                  className="shrink-0 text-xs text-red-500 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300"
                  title="Beleg entfernen"
                >
                  🗑
                </button>
              </div>
              {rechnung.beleg.pdfa_verfuegbar && (
                <button
                  onClick={_openBelegPdfa}
                  className="text-xs text-emerald-600 dark:text-emerald-400 hover:underline"
                  title="GoBD-konforme PDF/A-3-Version öffnen"
                >
                  ✓ PDF/A-3 (GoBD-Archiv)
                </button>
              )}
            </div>
          ) : (
            <label className="flex items-center gap-2 cursor-pointer text-sm text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2.5 border border-dashed border-slate-300 dark:border-slate-600 hover:border-blue-400 dark:hover:border-blue-500 transition-colors">
              <span>📎</span>
              <span>{belegUploadMutation.isPending ? 'Wird hochgeladen…' : 'PDF oder Bild anhängen'}</span>
              <input
                type="file"
                accept="application/pdf,image/jpeg,image/png,image/tiff"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (f) belegUploadMutation.mutate(f)
                  e.target.value = ''
                }}
                disabled={belegUploadMutation.isPending}
              />
            </label>
          )}
          {belegFehler && (
            <p className="text-xs text-red-600 dark:text-red-400 mt-1">{belegFehler}</p>
          )}
        </div>}
      </div>

      {/* Aktionen */}
      <div className="p-5 border-t border-slate-100 dark:border-slate-700 space-y-2">
        {hatZahlungsoption && (
          <button
            onClick={() => setZahlungsDialog(true)}
            className="w-full py-2.5 text-sm font-medium bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors"
          >
            {rechnung.dokument_typ === 'Gutschrift' ? 'Rückerstattung buchen' : rechnung.typ === 'ausgang' ? 'Zahlung kassieren' : 'Zahlung buchen'}
            {rechnung.zahlungsstatus === 'teilweise' && ` (Restbetrag ${formatEuro(Math.abs(restbetrag))})`}
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
          onSuccess={(result) => { setZahlungsDialog(false); onZahlungErfasst?.(result.rechnung) }}
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
// Rechnungs-Formular
// ---------------------------------------------------------------------------

type Positionszeile = {
  beschreibung: string
  menge: string
  einheit: string
  netto: string
  ust_satz: string
  rabatt_prozent?: string
  artikel_id?: number
  kategorie_id?: string  // nur Eingang, per-Position-Kategorie
  differenzbesteuerung?: boolean
}

const leerPosition = (defaultUst = '19'): Positionszeile => ({
  beschreibung: '',
  menge: '1',
  einheit: '',
  netto: '',
  ust_satz: defaultUst,
  rabatt_prozent: '',
  artikel_id: undefined,
  kategorie_id: undefined,
  differenzbesteuerung: false,
})

function RechnungForm({
  typ,
  initial,
  prefillFromAnalyse,
  initialDokumentTyp,
  onSave,
  onCancel,
}: {
  typ: 'eingang' | 'ausgang'
  initial?: Rechnung
  prefillFromAnalyse?: AnalyseErgebnis
  initialDokumentTyp?: 'Lieferschein'
  onSave: (data: RechnungCreate) => void
  onCancel: () => void
}) {
  const pf = prefillFromAnalyse?.felder
  const pfRing = (key: string) => pf?.konfidenz?.[key] === 'warnung' ? 'ring-2 ring-amber-400 rounded-lg' : ''
  const formatLabel: Record<string, string> = {
    zugferd: 'ZUGFeRD', xrechnung: 'XRechnung', pdf: 'PDF', unbekannt: 'Unbekannt', xml: 'XML',
  }
  const { data: kunden } = useQuery({ queryKey: ['kunden'], queryFn: getKunden })
  const { data: lieferanten } = useQuery({ queryKey: ['lieferanten'], queryFn: getLieferanten })
  const { data: kategorien } = useQuery({ queryKey: ['kategorien', 'aktiv'], queryFn: () => getKategorien(true) })
  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen, staleTime: 1000 * 60 * 10 })
  const { data: ustSaetze = [] } = useQuery({ queryKey: ['ust-saetze'], queryFn: getUstSaetze, staleTime: 1000 * 60 * 10 })
  const [katModus, setKatModus] = useState<KontorahmenModus>(getKontorahmenModus)
  useEffect(() => {
    const h = (e: StorageEvent) => { if (e.key === KONTORAHMEN_LS_KEY) setKatModus((e.newValue ?? '') as KontorahmenModus) }
    window.addEventListener('storage', h)
    return () => window.removeEventListener('storage', h)
  }, [])

  const istKleinunternehmer = unternehmen?.ist_kleinunternehmer ?? false
  const aktiveSaetze = ustSaetze.filter((s) => s.ist_aktiv)
  const defaultUstGlobal = istKleinunternehmer
    ? '0'
    : (ustSaetze.find((s) => s.ist_default)?.satz
        ? String(parseFloat(ustSaetze.find((s) => s.ist_default)!.satz))
        : '19')

  const [rechnungsnummer, setRechnungsnummer] = useState(initial?.rechnungsnummer ?? '')
  const [datum, setDatum] = useState(pf?.datum ?? initial?.datum ?? heuteIso())
  const [leistungVon, setLeistungVon] = useState(initial?.leistung_von ?? initial?.datum ?? pf?.datum ?? heuteIso())
  const [leistungBis, setLeistungBis] = useState(initial?.leistung_bis ?? '')
  const [leistungManuell, setLeistungManuell] = useState(
    !!(initial?.leistung_von && initial.leistung_von !== initial.datum)
  )
  const [leistungZeitraum, setLeistungZeitraum] = useState(!!(initial?.leistung_bis))
  const zahlungsziel = unternehmen?.standard_zahlungsziel ?? 14
  const [skontoProzent, setSkontoProzent] = useState<string>(
    initial?.skonto_prozent != null ? String(initial.skonto_prozent) : ''
  )
  const [skontoTage, setSkontoTage] = useState<string>(
    initial?.skonto_tage != null ? String(initial.skonto_tage) : ''
  )
  const [rechnungRabatt, setRechnungRabatt] = useState<string>(
    initial?.rabatt_prozent && parseFloat(String(initial.rabatt_prozent)) > 0 ? String(parseFloat(String(initial.rabatt_prozent))) : ''
  )
  const [faelligAm, setFaelligAm] = useState(() => {
    if (pf?.faellig_am) return pf.faellig_am
    if (initial?.faellig_am) return initial.faellig_am
    if (initial) return ''
    if (prefillFromAnalyse) return ''  // Import ohne Fälligkeit → leer lassen
    const d = new Date(heuteIso())
    d.setDate(d.getDate() + (unternehmen?.standard_zahlungsziel ?? 14))
    return d.toISOString().slice(0, 10)
  })
  const [partnerId, setPartnerId] = useState<string>(
    typ === 'ausgang'
      ? String(initial?.kunde_id ?? '')
      : String(initial?.lieferant_id ?? '')
  )
  const [partnerFreitext, setPartnerFreitext] = useState(
    pf?.lieferant_name ?? initial?.partner_freitext ?? ''
  )
  const [kategorieId, setKategorieId] = useState<string>(String(initial?.kategorie_id ?? ''))
  const [showNeuKategorieForm, setShowNeuKategorieForm] = useState(false)
  const [showNeuLieferant, setShowNeuLieferant] = useState(false)
  const [showNeuKunde, setShowNeuKunde] = useState(false)
  const [showNeuArtikel, setShowNeuArtikel] = useState(false)
  const [notizen, setNotizen] = useState(initial?.notizen ?? '')
  const [einleitungstext, setEinleitungstext] = useState(initial?.einleitungstext ?? '')
  const [externeBelegnr, setExterneBelegnr] = useState(pf?.externe_belegnr ?? initial?.externe_belegnr ?? '')
  const [positionen, setPositionen] = useState<Positionszeile[]>(() => {
    if (prefillFromAnalyse?.positionen?.length) {
      return prefillFromAnalyse.positionen.map((p) => ({
        beschreibung: p.artikel_nr ? `${p.artikel_nr} ${p.beschreibung}` : p.beschreibung,
        menge: String(parseFloat(p.menge)),
        einheit: p.einheit || 'Stück',
        netto: p.netto,
        ust_satz: p.ust_satz,
      }))
    }
    if (initial?.positionen?.length) {
      return initial.positionen.map((p) => ({
        beschreibung: p.beschreibung,
        menge: String(parseFloat(p.menge)),
        einheit: p.einheit,
        netto: Math.abs(parseFloat(p.netto)).toFixed(2).replace('.', ','),  // pos.netto = Original-Einzelpreis (vor Rabatt); abs() für alte Gutschrift-Einträge
        ust_satz: String(parseFloat(p.ust_satz)),
        rabatt_prozent: p.rabatt_prozent && parseFloat(p.rabatt_prozent) > 0 ? String(parseFloat(p.rabatt_prozent)) : '',
        artikel_id: p.artikel_id ?? undefined,
        kategorie_id: p.kategorie_id != null ? String(p.kategorie_id) : undefined,
        differenzbesteuerung: p.differenzbesteuerung ?? false,
      }))
    }
    // Plain-PDF-Prefill: Brutto/Netto-Betrag und USt-Satz aus Texterkennung vorfüllen
    const pos = leerPosition(pf?.ust_satz ?? defaultUstGlobal)
    if (pf?.gesamt_brutto) pos.netto = pf.gesamt_brutto
    else if (pf?.gesamt_netto) pos.netto = pf.gesamt_netto
    return [pos]
  })
  const [eingabeModus, setEingabeModus] = useState<'netto' | 'brutto'>(
    prefillFromAnalyse?.positionen_modus === 'brutto'
      ? 'brutto'
      : prefillFromAnalyse?.positionen?.length
        ? 'netto'
        : pf?.gesamt_netto && !pf?.gesamt_brutto ? 'netto' : 'brutto'
  )
  const dokumentTyp: 'Rechnung' | 'Lieferschein' =
    (initial?.dokument_typ === 'Lieferschein' ? 'Lieferschein' : initialDokumentTyp) ?? 'Rechnung'
  const [lieferadresseId, setLieferadresseId] = useState<string>(
    initial?.lieferadresse_id ? String(initial.lieferadresse_id) : ''
  )
const kundeIdNum = partnerId ? parseInt(partnerId) : null
  const { data: lieferadressen = [] } = useQuery({
    queryKey: ['lieferadressen', kundeIdNum],
    queryFn: () => getLieferadressen(kundeIdNum!),
    enabled: dokumentTyp === 'Lieferschein' && !!kundeIdNum,
  })

  // Standard-Lieferadresse vorauswählen, wenn nicht bereits explizit gesetzt
  useEffect(() => {
    if (initial?.lieferadresse_id || lieferadresseId) return
    const standard = lieferadressen.find(la => la.ist_standard)
    if (standard) setLieferadresseId(String(standard.id))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lieferadressen])

  // Netto-Modus automatisch aktivieren wenn Firmenkunde gewählt wird (B2B)
  useEffect(() => {
    if (typ !== 'ausgang' || !!initial || !partnerId) return
    const kunde = kunden?.find(k => k.id === parseInt(partnerId))
    if (!kunde?.firmenname?.trim()) return
    const preiseNochLeer = positionen.every(p => !p.netto.trim())
    if (preiseNochLeer) setEingabeModus('netto')
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [partnerId, kunden])

  // Schnellmodus: einfache Betragseingabe für Eingangsrechnungen
  // Standard ist aufgeschlüsselter Modus – Schnellmodus nur bei Bearbeitung bestehender 1-Positions-Rechnungen
  const [schnellmodus, setSchnellmodus] = useState(
    typ === 'eingang' &&
    !!initial && initial.positionen.length <= 1 &&
    (prefillFromAnalyse?.positionen?.length ?? 0) <= 1
  )

  const partnerListe = typ === 'ausgang' ? (kunden ?? []) : (lieferanten ?? [])

  // Lieferant aus Analyse-Prefill setzen:
  // 1. Backend-Vorschlag (lieferant_vorschlaege[0]) hat Vorrang – das Backend normalisiert
  //    OCR-Artefakte (z.B. "GimbH" → GmbH) bereits korrekt per Fuzzy-Matching.
  // 2. Fallback: einfacher includes()-Vergleich über den erkannten Namen.
  useEffect(() => {
    if (!prefillFromAnalyse || !lieferanten?.length) return

    // Backend-Vorschlag direkt übernehmen (beste Qualität)
    const vorschlagId = prefillFromAnalyse.lieferant_vorschlaege?.[0]?.id
    if (vorschlagId) {
      const found = lieferanten.find((l) => l.id === vorschlagId)
      if (found) {
        setPartnerId(String(found.id))
        setPartnerFreitext('')
        return
      }
    }

    // Fallback: einfacher Namensvergleich
    if (!pf?.lieferant_name) return
    const name = pf.lieferant_name.toLowerCase()
    const match = lieferanten.find(
      (l) => (l.firmenname || `${l.vorname ?? ''} ${l.nachname ?? ''}`).toLowerCase().includes(name)
        || name.includes((l.firmenname || '').toLowerCase())
    )
    if (match?.id) {
      setPartnerId(String(match.id))
      setPartnerFreitext('')
    }
  }, [lieferanten])

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

  // Skonto aus Kunde/Unternehmen vorbelegen (nur neue Ausgangsrechnungen)
  useEffect(() => {
    if (initial || typ !== 'ausgang') return
    if (partnerId && kunden) {
      const k = kunden.find((c: any) => String(c.id) === partnerId)
      if (k && (k as any).skonto_prozent != null) {
        setSkontoProzent(String((k as any).skonto_prozent))
        setSkontoTage(String((k as any).skonto_tage ?? ''))
        return
      }
    }
    if (unternehmen?.standard_skonto_prozent != null) {
      setSkontoProzent(String(unternehmen.standard_skonto_prozent))
      setSkontoTage(String(unternehmen.standard_skonto_tage ?? ''))
    } else {
      setSkontoProzent('')
      setSkontoTage('')
    }
  }, [partnerId, kunden, unternehmen, initial, typ])

  // Leistungsdatum synchron mit Rechnungsdatum halten (solange nicht manuell geändert)
  useEffect(() => {
    if (!leistungManuell) setLeistungVon(datum)
  }, [datum, leistungManuell])

  // Fälligkeitsdatum = Rechnungsdatum + Zahlungsziel (nur neue Rechnungen, nicht bei Prefill aus Analyse)
  useEffect(() => {
    if (initial) return
    if (prefillFromAnalyse) return  // Import ohne Fälligkeit → nicht berechnen
    const d = new Date(datum)
    d.setDate(d.getDate() + zahlungsziel)
    setFaelligAm(d.toISOString().slice(0, 10))
  }, [datum, zahlungsziel, initial, prefillFromAnalyse])


  // Kategorie-Gruppen analog BuchungForm
  const alle = kategorien ?? []
  const aufwandKat = alle.filter((k) => k.kontenart === 'Aufwand')
  const anlageKat  = alle.filter((k) => k.kontenart === 'Anlage')

  // Summenberechnung — reagiert auf eingabeModus und Positionsrabatt
  const summen = positionen.reduce(
    (acc, p) => {
      const eingabe = parseFloat(p.netto.replace(',', '.')) || 0
      const menge = parseFloat(p.menge.replace(',', '.')) || 1
      const ust = parseFloat(p.ust_satz) || 0
      const posRabatt = parseFloat((p.rabatt_prozent ?? '').replace(',', '.')) || 0
      let netto: number, ustBetrag: number, brutto: number
      if (eingabeModus === 'brutto') {
        const nettoEinzel = ust > 0 ? (eingabe * 100) / (100 + ust) : eingabe
        const nettoNachRabatt = nettoEinzel * (1 - posRabatt / 100)
        netto = nettoNachRabatt * menge
        ustBetrag = netto * ust / 100
        brutto = netto + ustBetrag
      } else {
        const nettoNachRabatt = eingabe * (1 - posRabatt / 100)
        netto = nettoNachRabatt * menge
        ustBetrag = (netto * ust) / 100
        brutto = netto + ustBetrag
      }
      return { netto: acc.netto + netto, ust: acc.ust + ustBetrag, brutto: acc.brutto + brutto }
    },
    { netto: 0, ust: 0, brutto: 0 }
  )
  // Rechnungsrabatt anwenden
  const rechnungRabattNum = parseFloat(rechnungRabatt.replace(',', '.')) || 0
  const summenNachRabatt = rechnungRabattNum > 0
    ? {
        netto: summen.netto * (1 - rechnungRabattNum / 100),
        ust: summen.ust * (1 - rechnungRabattNum / 100),
        brutto: summen.brutto * (1 - rechnungRabattNum / 100),
      }
    : summen

  // Im Import-Modus: Gesamtbeträge aus dem XML nur anzeigen solange Positionen unverändert.
  // Hat der Nutzer Positionen korrigiert (Abweichung > 1 Cent), live aus Positionen rechnen.
  const pfN = prefillFromAnalyse?.felder?.gesamt_netto
  const pfU = prefillFromAnalyse?.felder?.gesamt_ust
  const pfB = prefillFromAnalyse?.felder?.gesamt_brutto
  const overridePasst = pfB != null && Math.abs(summenNachRabatt.brutto - Number(pfB)) <= 0.01
  const anzeigeSummen = (pfN && pfU && pfB && overridePasst)
    ? { netto: parseFloat(String(pfN)), ust: parseFloat(String(pfU)), brutto: parseFloat(String(pfB)) }
    : summenNachRabatt

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

  function zusammenfassenNachSteuersatz() {
    const gruppen: Record<string, number> = {}
    for (const p of positionen) {
      const satz = String(parseFloat(p.ust_satz) || 0)
      const betrag = (parseFloat(p.netto.replace(',', '.')) || 0) * (parseFloat(p.menge) || 1)
      gruppen[satz] = (gruppen[satz] ?? 0) + betrag
    }
    const labels: Record<string, string> = { '0': 'Waren (0%)', '7': 'Waren (7%)', '19': 'Waren (19%)' }
    setPositionen(
      Object.entries(gruppen)
        .sort(([a], [b]) => parseFloat(a) - parseFloat(b))
        .map(([satz, summe]) => ({
          ...leerPosition(satz),
          beschreibung: labels[satz] ?? `Waren (${satz}%)`,
          netto: summe.toFixed(2).replace('.', ','),
          menge: '1',
        }))
    )
    // eingabeModus bleibt erhalten – war Brutto, bleibt Brutto
  }

  function addPosition() {
    const letztePos = positionen[positionen.length - 1]
    const defaultUst = istKleinunternehmer
      ? '0'
      : typ === 'ausgang'
        ? defaultUstGlobal
        : String((kategorien ?? []).find((k) => String(k.id) === (letztePos?.kategorie_id ?? ''))?.ust_satz_standard ?? defaultUstGlobal)
    setPositionen((prev) => [...prev, { ...leerPosition(defaultUst), kategorie_id: letztePos?.kategorie_id }])
  }

  function removePosition(i: number) {
    if (positionen.length <= 1) return
    setPositionen((prev) => prev.filter((_, idx) => idx !== i))
  }

  function fillPositionFromArtikel(i: number, a: ArtikelSuche) {
    // §25a: kein USt-Ausweis, VK brutto = VK netto
    const istDiff = a.differenzbesteuerung
    const ust_satz = (istKleinunternehmer || istDiff) ? '0' : String(parseInt(a.steuersatz))
    const preis = istDiff ? a.vk_brutto : (eingabeModus === 'netto' ? a.vk_netto : a.vk_brutto)
    setPositionen((prev) => prev.map((p, idx) =>
      idx === i
        ? { ...p, beschreibung: a.bezeichnung, einheit: a.einheit, ust_satz, netto: preis.replace('.', ','), artikel_id: a.id, differenzbesteuerung: istDiff }
        : p
    ))
  }

  function buildData(istEntwurf: boolean): RechnungCreate {
    return {
      typ,
      rechnungsnummer: rechnungsnummer || undefined,
      datum,
      leistung_von: leistungVon !== datum ? leistungVon : undefined,
      leistung_bis: leistungBis || undefined,
      faellig_am: dokumentTyp === 'Lieferschein' ? undefined : (faelligAm || undefined),
      kunde_id: typ === 'ausgang' ? (partnerId ? parseInt(partnerId) : undefined) : undefined,
      lieferant_id: typ === 'eingang' ? (partnerId ? parseInt(partnerId) : undefined) : undefined,
      partner_freitext: partnerFreitext || undefined,
      kategorie_id: kategorieId ? parseInt(kategorieId) : undefined,
      notizen: notizen || undefined,
      einleitungstext: einleitungstext || undefined,
      externe_belegnr: typ === 'eingang' ? (externeBelegnr || undefined) : undefined,
      ist_entwurf: istEntwurf,
      skonto_prozent: dokumentTyp === 'Lieferschein' ? undefined : (skontoProzent ? parseFloat(skontoProzent) : undefined),
      skonto_tage: dokumentTyp === 'Lieferschein' ? undefined : (skontoTage ? parseInt(skontoTage) : undefined),
      dokument_typ: dokumentTyp !== 'Rechnung' ? dokumentTyp : undefined,
      lieferadresse_id: dokumentTyp === 'Lieferschein' && lieferadresseId ? parseInt(lieferadresseId) : undefined,
      // XML-Import: Gesamtbeträge direkt aus der Rechnung übernehmen –
      // aber nur wenn die Positionen noch mit dem OCR/XML-Wert übereinstimmen.
      // Hat der Nutzer Positionen manuell korrigiert (z.B. via Zusammenfassen + USt-Änderung),
      // weicht die berechnete Summe ab → Override verwerfen, Positionen sind maßgeblich.
      ...(() => {
        const pfN = prefillFromAnalyse?.felder?.gesamt_netto
        const pfU = prefillFromAnalyse?.felder?.gesamt_ust
        const pfB = prefillFromAnalyse?.felder?.gesamt_brutto
        if (!pfN || !pfU || !pfB) return {}
        const calcBrutto = positionen.reduce((sum, p) => {
          const eingabe = parseFloat(p.netto.replace(',', '.')) || 0
          const ust = parseFloat(p.ust_satz) || 0
          const netto = (eingabeModus === 'brutto' && ust > 0) ? (eingabe * 100) / (100 + ust) : eingabe
          return sum + (netto + netto * ust / 100) * (parseFloat(p.menge) || 1)
        }, 0)
        if (Math.abs(calcBrutto - Number(pfB)) > 0.01) return {}
        return { netto_gesamt_override: pfN, ust_gesamt_override: pfU, brutto_gesamt_override: pfB }
      })(),
      positionen: positionen.map((p) => {
        const eingabe = parseFloat(p.netto.replace(',', '.')) || 0
        const ust = parseFloat(p.ust_satz) || 0
        const istDiff = p.differenzbesteuerung ?? false
        // §25a: kein USt-Ausweis; Eingabewert = Rechnungspreis → direkt als netto senden
        const ust_satz = (istKleinunternehmer || istDiff) ? '0' : (p.ust_satz || '0')
        const netto = (!istDiff && eingabeModus === 'brutto' && ust > 0) ? (eingabe * 100) / (100 + ust) : eingabe
        const rabatt = parseFloat((p.rabatt_prozent ?? '').replace(',', '.')) || 0
        return {
          beschreibung: p.beschreibung,
          menge: p.menge || '1',
          einheit: p.einheit || 'Stück',
          netto: netto.toFixed(2),
          ust_satz,
          artikel_id: p.artikel_id,
          kategorie_id: p.kategorie_id ? parseInt(p.kategorie_id) : undefined,
          differenzbesteuerung: istDiff,
          rabatt_prozent: rabatt > 0 ? rabatt : undefined,
        } as RechnungspositionCreate
      }),
      rabatt_prozent: rechnungRabattNum > 0 ? rechnungRabattNum : undefined,
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
      {/* Import-Warnungen */}
      {prefillFromAnalyse && prefillFromAnalyse.warnungen.some(w => w === 'TESSERACT_FEHLT') && (
        <OcrInstallHinweis />
      )}
      {prefillFromAnalyse && prefillFromAnalyse.warnungen.filter(w => w !== 'TESSERACT_FEHLT').length > 0 && (
        <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg px-4 py-3 space-y-1">
          <p className="text-xs font-semibold text-amber-700 dark:text-amber-300 mb-1">
            Hinweise aus dem Import ({formatLabel[prefillFromAnalyse.format] ?? prefillFromAnalyse.format}):
          </p>
          {prefillFromAnalyse.warnungen.filter(w => w !== 'TESSERACT_FEHLT').map((w, i) => (
            <p key={i} className="text-xs text-amber-700 dark:text-amber-300">⚠️ {w}</p>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
            {dokumentTyp === 'Lieferschein' ? 'Lieferscheinnummer' : 'Rechnungsnummer'} <span className="text-slate-400 dark:text-slate-500 font-normal">(leer = auto)</span>
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
          <div className={pfRing('datum')}>
            <input
              type="date"
              required
              value={datum}
              onChange={guardedDateChange(setDatum)}
              className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className={leistungZeitraum ? 'col-span-2' : ''}>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200">
              {leistungZeitraum ? 'Leistungszeitraum' : 'Leistungsdatum'}
              {!leistungManuell && !leistungZeitraum && <span className="text-slate-400 dark:text-slate-500 font-normal ml-1">(= Rechnungsdatum)</span>}
            </label>
            <button
              type="button"
              onClick={() => {
                setLeistungZeitraum((v) => !v)
                if (leistungZeitraum) setLeistungBis('')
              }}
              className="text-xs text-blue-500 hover:text-blue-700 dark:text-blue-400"
            >
              {leistungZeitraum ? '← Einzeldatum' : 'Zeitraum →'}
            </button>
          </div>
          {leistungZeitraum ? (
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={leistungVon}
                onChange={(e) => {
                  if (e.target.value) { setLeistungVon(e.target.value); setLeistungManuell(true) }
                }}
                className="flex-1 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
              />
              <span className="text-slate-400 dark:text-slate-500 text-sm">–</span>
              <input
                type="date"
                value={leistungBis}
                min={leistungVon}
                onChange={guardedDateChange(setLeistungBis)}
                className="flex-1 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
              />
            </div>
          ) : (
            <input
              type="date"
              value={leistungVon}
              onChange={(e) => {
                if (e.target.value) {
                  setLeistungVon(e.target.value)
                  setLeistungManuell(e.target.value !== datum)
                }
              }}
              className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
            />
          )}
        </div>
        {!leistungZeitraum && <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Fällig am</label>
          <div className={pfRing('faellig_am')}>
            <input
              type="date"
              value={faelligAm}
              min={datum}
              onChange={guardedDateChange(setFaelligAm)}
              className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
            />
          </div>
        </div>}
      </div>
      {leistungZeitraum && (
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Fällig am</label>
          <div className={pfRing('faellig_am')}>
            <input
              type="date"
              value={faelligAm}
              min={datum}
              onChange={guardedDateChange(setFaelligAm)}
              className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
            />
          </div>
        </div>
      )}

      {/* Rechnungsrabatt */}
      {dokumentTyp !== 'Lieferschein' && (
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
            Rechnungsrabatt %{' '}<span className="text-slate-400 dark:text-slate-500 font-normal">(optional, auf Gesamtbetrag)</span>
          </label>
          <input
            type="number"
            min="0"
            max="100"
            step="0.5"
            value={rechnungRabatt}
            onChange={(e) => setRechnungRabatt(e.target.value)}
            placeholder="z. B. 5"
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
          />
        </div>
      )}

      {/* Skonto – nur Ausgangsrechnungen */}
      {typ === 'ausgang' && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
              Skonto %{' '}<span className="text-slate-400 dark:text-slate-500 font-normal">(optional)</span>
            </label>
            <input
              type="number"
              min="0"
              max="100"
              step="0.5"
              value={skontoProzent}
              onChange={(e) => setSkontoProzent(e.target.value)}
              placeholder="z. B. 2"
              className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
              Skonto-Frist{' '}<span className="text-slate-400 dark:text-slate-500 font-normal">(Tage)</span>
            </label>
            <input
              type="number"
              min="1"
              max="365"
              step="1"
              value={skontoTage}
              onChange={(e) => setSkontoTage(e.target.value)}
              placeholder="z. B. 7"
              className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
            />
          </div>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
          {typ === 'ausgang' ? 'Kunde' : 'Lieferant'}
        </label>
        <div className="flex gap-1">
          <div className={`flex-1 ${pfRing('lieferant_name')}`}>
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
          {typ === 'eingang' && (
            <button
              type="button"
              onClick={() => setShowNeuLieferant(true)}
              title="Neuen Lieferanten anlegen"
              className="shrink-0 px-2.5 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 text-base leading-none"
            >
              +
            </button>
          )}
          {typ === 'ausgang' && (
            <button
              type="button"
              onClick={() => setShowNeuKunde(true)}
              title="Neuen Kunden anlegen"
              className="shrink-0 px-2.5 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 text-base leading-none"
            >
              +
            </button>
          )}
        </div>
        {showNeuLieferant && (
          <LieferantErstellenModal
            onClose={() => setShowNeuLieferant(false)}
            onSave={(neu) => {
              setShowNeuLieferant(false)
              setPartnerId(String(neu.id ?? ''))
              setPartnerFreitext(neu.firmenname)
            }}
          />
        )}
        {showNeuKunde && (
          <KundeErstellenModal
            onClose={() => setShowNeuKunde(false)}
            onSave={(neu) => {
              setShowNeuKunde(false)
              setPartnerId(String(neu.id ?? ''))
              setPartnerFreitext(neu.firmenname ?? [neu.vorname, neu.nachname].filter(Boolean).join(' '))
            }}
          />
        )}
      </div>

      {/* Lieferadresse – nur bei Lieferschein mit ausgewähltem Kunden */}
      {dokumentTyp === 'Lieferschein' && kundeIdNum && lieferadressen.length > 0 && (
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Lieferadresse</label>
          <select
            value={lieferadresseId}
            onChange={e => setLieferadresseId(e.target.value)}
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
          >
            <option value="">Rechnungsadresse (Standard)</option>
            {lieferadressen.map(la => (
              <option key={la.id} value={String(la.id)}>
                {la.bezeichnung || 'Lieferadresse'}{la.ist_standard ? ' ★' : ''} – {[la.strasse, la.hausnummer, la.plz, la.ort].filter(Boolean).join(' ')}
              </option>
            ))}
          </select>
        </div>
      )}

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
            {!schnellmodus && typ === 'eingang' && positionen.length > 1 && (
              <button
                type="button"
                onClick={zusammenfassenNachSteuersatz}
                className="text-xs text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 underline"
                title="Alle Positionen nach Steuersatz summieren (z.B. alle 7%-Positionen → eine Zeile)"
              >
                ∑ Nach Steuersatz zusammenfassen
              </button>
            )}
            {typ === 'eingang' && (
              <button
                type="button"
                onClick={() => setSchnellmodus((v) => !v)}
                className="text-xs text-blue-600 hover:text-blue-700 underline"
              >
                {schnellmodus ? 'Positionen aufschlüsseln →' : '← Einfache Eingabe'}
              </button>
            )}
            {(!schnellmodus || typ === 'ausgang') && !istKleinunternehmer && dokumentTyp !== 'Lieferschein' && (
              <button
                type="button"
                onClick={toggleEingabeModus}
                className="text-xs text-blue-600 hover:text-blue-700 underline"
              >
                {eingabeModus === 'netto' ? 'Brutto eingeben' : 'Netto eingeben'}
              </button>
            )}
            {!schnellmodus && typ === 'ausgang' && (
              <button
                type="button"
                onClick={() => setShowNeuArtikel(true)}
                className="text-xs text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400"
              >
                + Neuer Artikel
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
            {/* Kategorie */}
            <div>
              <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Kategorie</label>
              <div className="flex gap-1">
                <select
                  value={positionen[0]?.kategorie_id ?? ''}
                  onChange={(e) => updatePosition(0, 'kategorie_id', e.target.value)}
                  className="flex-1 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
                >
                  <option value="">— keine Kategorie —</option>
                  <optgroup label="Betriebsausgaben">
                    {aufwandKat.map((k) => <option key={k.id} value={String(k.id)}>{k.name}</option>)}
                  </optgroup>
                  {anlageKat.length > 0 && (
                    <optgroup label="Investitionen">
                      {anlageKat.map((k) => <option key={k.id} value={String(k.id)}>{k.name}</option>)}
                    </optgroup>
                  )}
                </select>
                <button
                  type="button"
                  onClick={() => setShowNeuKategorieForm(true)}
                  title="Neue Kategorie anlegen"
                  className="shrink-0 px-2.5 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 text-base leading-none"
                >
                  +
                </button>
              </div>
              {showNeuKategorieForm && (
                <KategorieErstellenModal
                  kontenPflicht
                  onClose={() => setShowNeuKategorieForm(false)}
                  onSave={(neu) => { setShowNeuKategorieForm(false); updatePosition(0, 'kategorie_id', String(neu.id)) }}
                />
              )}
            </div>

            {/* Summenanzeige */}
            {parseFloat((positionen[0]?.netto ?? '').replace(',', '.')) !== 0 && (
              <div className="text-xs text-right text-slate-500 dark:text-slate-400 space-y-0.5 pt-1 border-t border-slate-100 dark:border-slate-700">
                <div>Netto{eingabeModus === 'brutto' && ' (berechnet)'}: <span className="font-medium text-slate-700 dark:text-slate-200">{formatEuro(anzeigeSummen.netto)}</span></div>
                {anzeigeSummen.ust !== 0 && <div>USt: <span className="text-slate-600 dark:text-slate-300">{formatEuro(anzeigeSummen.ust)}</span></div>}
                <div className="font-semibold text-slate-800 dark:text-slate-100">Brutto{eingabeModus === 'netto' && ' (berechnet)'}: {formatEuro(anzeigeSummen.brutto)}</div>
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
                {dokumentTyp !== 'Lieferschein' && <>
                  <th className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 font-medium w-24">
                    {eingabeModus === 'netto' ? 'Netto (€)' : 'Brutto (€)'}
                  </th>
                  <th className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 font-medium w-16">Rabatt %</th>
                  <th className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 font-medium w-16">USt %</th>
                  {typ === 'eingang' && (
                    <th className="px-3 py-2 text-left text-slate-500 dark:text-slate-400 font-medium w-28">Konto</th>
                  )}
                </>}
                <th className="px-3 py-2 w-8"></th>
              </tr>
            </thead>
            <tbody>
              {positionen.map((pos, i) => (
                <tr key={i} className="border-t border-slate-100 dark:border-slate-700">
                  <td className="px-2 py-1.5">
                    <ArtikelAutocomplete
                      value={pos.beschreibung}
                      onChange={(v) => updatePosition(i, 'beschreibung', v)}
                      onArtikelWahl={(a) => fillPositionFromArtikel(i, a)}
                      placeholder="Beschreibung"
                      inputClassName="w-full border-0 outline-none bg-transparent text-slate-700 dark:text-slate-200 placeholder-slate-300 dark:placeholder-slate-500 text-xs"
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
                  {dokumentTyp !== 'Lieferschein' && <>
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
                      <input
                        type="text"
                        value={pos.rabatt_prozent ?? ''}
                        onChange={(e) => updatePosition(i, 'rabatt_prozent', e.target.value)}
                        className="w-full border-0 outline-none bg-transparent text-right text-slate-700 dark:text-slate-200 placeholder-slate-300 dark:placeholder-slate-600"
                        placeholder="0"
                      />
                    </td>
                    <td className="px-2 py-1.5">
                      {pos.differenzbesteuerung ? (
                        <div className="text-right text-xs font-medium text-amber-600 dark:text-amber-400 px-1">§25a</div>
                      ) : (
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
                      )}
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
                            <option key={k.id} value={String(k.id)}>{katLabel(k, katModus)}</option>
                          ))}
                        </select>
                      </td>
                    )}
                  </>}
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
            {dokumentTyp !== 'Lieferschein' && (
            <tfoot className="bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-700">
              <tr>
                <td colSpan={typ === 'eingang' ? 6 : 5} className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 text-xs">
                  Netto{eingabeModus === 'brutto' && <span className="text-slate-400 dark:text-slate-500"> (berechnet)</span>}
                </td>
                <td colSpan={2} className="px-3 py-2 text-right font-medium text-slate-700 dark:text-slate-200">{formatEuro(anzeigeSummen.netto)}</td>
              </tr>
              <tr>
                <td colSpan={typ === 'eingang' ? 6 : 5} className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 text-xs">USt</td>
                <td colSpan={2} className="px-3 py-2 text-right text-slate-600 dark:text-slate-300">{formatEuro(anzeigeSummen.ust)}</td>
              </tr>
              {rechnungRabattNum > 0 && (
                <tr>
                  <td colSpan={typ === 'eingang' ? 6 : 5} className="px-3 py-2 text-right text-slate-500 dark:text-slate-400 text-xs">
                    Zwischensumme Brutto
                  </td>
                  <td colSpan={2} className="px-3 py-2 text-right text-slate-600 dark:text-slate-300">{formatEuro(summen.brutto)}</td>
                </tr>
              )}
              {rechnungRabattNum > 0 && (
                <tr>
                  <td colSpan={typ === 'eingang' ? 6 : 5} className="px-3 py-2 text-right text-slate-400 dark:text-slate-500 text-xs">
                    Rabatt {rechnungRabattNum} %
                  </td>
                  <td colSpan={2} className="px-3 py-2 text-right text-slate-400 dark:text-slate-500 text-xs">
                    − {formatEuro((summen.brutto * rechnungRabattNum / 100).toFixed(2))}
                  </td>
                </tr>
              )}
              <tr>
                <td colSpan={typ === 'eingang' ? 6 : 5} className="px-3 py-2 text-right font-semibold text-slate-700 dark:text-slate-200">
                  Brutto{eingabeModus === 'netto' && <span className="text-slate-400 dark:text-slate-500 font-normal"> (berechnet)</span>}
                </td>
                <td colSpan={2} className="px-3 py-2 text-right font-bold text-slate-800 dark:text-slate-100">{formatEuro(anzeigeSummen.brutto)}</td>
              </tr>
            </tfoot>
            )}
          </table>
        </div>
        )}
      </div>

      {showNeuArtikel && (
        <ArtikelFormModal
          onClose={() => setShowNeuArtikel(false)}
          onSuccess={() => setShowNeuArtikel(false)}
          onSaveArtikel={(neu) => {
            setShowNeuArtikel(false)
            const istDiff = neu.differenzbesteuerung
            const ust_satz = (istKleinunternehmer || istDiff) ? '0' : String(parseInt(neu.steuersatz))
            const preis = istDiff ? neu.vk_brutto : (eingabeModus === 'netto' ? neu.vk_netto : neu.vk_brutto)
            setPositionen(prev => {
              const letzteIdx = prev.length - 1
              if (letzteIdx >= 0 && !prev[letzteIdx].beschreibung) {
                return prev.map((p, idx) => idx === letzteIdx
                  ? { ...p, beschreibung: neu.bezeichnung, einheit: neu.einheit, ust_satz, netto: preis.replace('.', ','), artikel_id: neu.id, differenzbesteuerung: istDiff }
                  : p)
              }
              return [...prev, { beschreibung: neu.bezeichnung, menge: '1', einheit: neu.einheit, ust_satz, netto: preis.replace('.', ','), artikel_id: neu.id, differenzbesteuerung: istDiff }]
            })
          }}
        />
      )}

      {typ === 'ausgang' && dokumentTyp !== 'Lieferschein' && (
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Einleitungstext</label>
          <textarea
            value={einleitungstext}
            onChange={(e) => setEinleitungstext(e.target.value)}
            rows={3}
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400"
            placeholder="Erscheint vor der Positionstabelle. Leer = globaler Standard aus Einstellungen."
          />
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
            Markdown: <code className="bg-slate-100 dark:bg-slate-800 px-1 rounded text-slate-600 dark:text-slate-300">**fett**</code> <code className="bg-slate-100 dark:bg-slate-800 px-1 rounded text-slate-600 dark:text-slate-300">*kursiv*</code> · Zeilenumbruch mit Enter
          </p>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Notizen</label>
        <textarea
          value={notizen}
          onChange={(e) => setNotizen(e.target.value)}
          rows={2}
          className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400"
          placeholder="Erscheint als Fußtext auf dem PDF"
        />
      </div>

      {typ === 'eingang' && (
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
            Belegnr. des Lieferanten
            <span className="text-slate-400 dark:text-slate-500 font-normal ml-1">(optional)</span>
          </label>
          <div className={pfRing('externe_belegnr')}>
            <input
              type="text"
              value={externeBelegnr}
              onChange={(e) => setExterneBelegnr(e.target.value)}
              className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400"
              placeholder="z. B. RE-2025-0042"
            />
          </div>
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
// Konfidenz-Indikator
// ---------------------------------------------------------------------------

function KonfidenzDot({ level }: { level?: string }) {
  if (!level || level === 'ok') return null
  if (level === 'fehlt') return (
    <span title="Feld nicht erkannt" className="inline-block w-2 h-2 rounded-full bg-red-500 flex-shrink-0" />
  )
  return (
    <span title="Plausibilität prüfen" className="inline-block w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" />
  )
}

function LieferantVorschlagBox({ vorschlaege }: { vorschlaege: LieferantVorschlag[] }) {
  if (vorschlaege.length === 0) return null
  return (
    <div className="ml-0 mt-0.5 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg px-3 py-2 text-xs space-y-1">
      <p className="text-blue-600 dark:text-blue-400 font-medium">Möglicher Treffer im Lieferantenstamm:</p>
      {vorschlaege.map(v => (
        <div key={v.id} className="flex justify-between text-slate-700 dark:text-slate-300">
          <span>{v.name}</span>
          <span className="text-slate-400 dark:text-slate-500">{Math.round(v.score * 100)} %</span>
        </div>
      ))}
    </div>
  )
}


// ---------------------------------------------------------------------------
// Import-Dialog (Stufe 2 – ZUGFeRD/XRechnung)
// ---------------------------------------------------------------------------

function ImportDialog({
  onClose,
  onWeiter,
}: {
  onClose: () => void
  onWeiter: (ergebnis: AnalyseErgebnis, datei: File) => void
}) {
  const [schritt, setSchritt] = useState<'upload' | 'ergebnis'>('upload')
  const [ergebnis, setErgebnis] = useState<AnalyseErgebnis | null>(null)
  const [ladeFehler, setLadeFehler] = useState<string | null>(null)
  const [laedt, setLaedt] = useState(false)
  const [datei, setDatei] = useState<File | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleDatei(f: File) {
    setDatei(f)
    setLaedt(true)
    setLadeFehler(null)
    try {
      const res = await analysiereRechnung(f)
      setErgebnis(res)
      setSchritt('ergebnis')
    } catch (e: any) {
      setLadeFehler(e.message)
    } finally {
      setLaedt(false)
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    const f = e.dataTransfer.files[0]
    if (f) handleDatei(f)
  }

  // Tauri auf Windows: HTML5-Drop feuert nicht – stattdessen tauri://drag-drop hören
  useEffect(() => {
    if (!isTauri() || schritt !== 'upload') return
    let unlisten: (() => void) | undefined
    listen<{ paths: string[] }>('tauri://drag-drop', async (event) => {
      const paths = event.payload?.paths ?? (event.payload as any) ?? []
      const erlaubte = (Array.isArray(paths) ? paths : [])
        .filter((p: string) => /\.(pdf|xml)$/i.test(p))
      if (erlaubte.length === 0) return
      const pfad = erlaubte[0]
      const name = pfad.replace(/\\/g, '/').split('/').pop() ?? 'rechnung'
      setLaedt(true)
      setLadeFehler(null)
      try {
        const res = await analysiereRechnungPfad(pfad)
        // Datei für Beleganhang: temp-Datei vom Backend holen
        if (res.temp_url) {
          const base = await getApiBase()
          const blob = await fetch(`${base}${res.temp_url}`).then(r => r.blob())
          setDatei(new File([blob], name, { type: 'application/pdf' }))
        }
        setErgebnis(res)
        setSchritt('ergebnis')
      } catch (e: any) {
        setLadeFehler(e.message)
      } finally {
        setLaedt(false)
      }
    }).then((fn) => { unlisten = fn })
    return () => { unlisten?.() }
  }, [schritt])

  async function handlePdfOeffnen() {
    if (!ergebnis?.temp_url) return
    // HTTP-Endpunkt statt file://-Pfad – funktioniert plattformübergreifend (auch WSL).
    const base = import.meta.env.DEV
      ? `${window.location.protocol}//${window.location.host}/api`
      : await getApiBase()
    await openUrl(`${base}${ergebnis.temp_url}`)
  }

  const formatLabel: Record<string, string> = {
    zugferd: 'ZUGFeRD',
    xrechnung: 'XRechnung',
    pdf: 'PDF (kein XML)',
    unbekannt: 'Unbekannt',
    xml: 'XML',
  }

  const felder = ergebnis?.felder

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg">
        <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800 dark:text-slate-100">Rechnung importieren</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-xl">×</button>
        </div>

        <div className="p-6">
          {schritt === 'upload' && (
            <>
              <div
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
                onClick={() => inputRef.current?.click()}
                className="border-2 border-dashed border-slate-300 dark:border-slate-600 rounded-xl p-10 flex flex-col items-center justify-center gap-3 cursor-pointer hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/30 transition-colors"
              >
                <span className="text-4xl">{laedt ? '⏳' : '📄'}</span>
                <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
                  {laedt ? 'Analysiere…' : 'PDF oder XML hier ablegen'}
                </p>
                <p className="text-xs text-slate-400 dark:text-slate-500">oder klicken zum Auswählen</p>
                <p className="text-xs text-slate-400 dark:text-slate-500">ZUGFeRD · XRechnung · normales PDF</p>
                <input
                  ref={inputRef}
                  type="file"
                  accept=".pdf,.xml"
                  className="hidden"
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) handleDatei(f) }}
                />
              </div>
              {ladeFehler && (
                <p className="mt-3 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2">
                  {ladeFehler}
                </p>
              )}
            </>
          )}

          {schritt === 'ergebnis' && ergebnis && (
            <div className="space-y-4">

              {/* Format-Badge */}
              <div className="flex items-center gap-2">
                <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${
                  ergebnis.format === 'zugferd' || ergebnis.format === 'xrechnung'
                    ? 'bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800'
                    : 'bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:border-slate-600'
                }`}>
                  {formatLabel[ergebnis.format] ?? ergebnis.format}
                </span>
                <span className="text-sm text-slate-500 dark:text-slate-400">
                  {ergebnis.format === 'zugferd' || ergebnis.format === 'xrechnung'
                    ? 'Strukturierte Daten erkannt'
                    : felder && Object.keys(felder).some(k => k !== 'konfidenz' && (felder as any)[k])
                      ? 'Felder aus PDF-Text extrahiert – bitte prüfen'
                      : 'Keine Daten erkannt – bitte manuell ausfüllen'}
                </span>
              </div>

              {/* Warnungen */}
              {ergebnis.warnungen.some(w => w === 'TESSERACT_FEHLT') && (
                <OcrInstallHinweis />
              )}
              {ergebnis.warnungen.filter(w => w !== 'TESSERACT_FEHLT').length > 0 && (
                <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg px-4 py-3 space-y-1">
                  {ergebnis.warnungen.filter(w => w !== 'TESSERACT_FEHLT').map((w, i) => (
                    <p key={i} className="text-xs text-amber-700 dark:text-amber-300">⚠️ {w}</p>
                  ))}
                </div>
              )}

              {/* Erkannte Felder */}
              {felder && Object.keys(felder).some(k => k !== 'konfidenz' && (felder as any)[k]) && (
                <div className="bg-slate-50 dark:bg-slate-900 rounded-xl p-4 space-y-2 text-sm">
                  {felder.lieferant_name && (
                    <div className="space-y-1">
                      <div className="flex justify-between items-center">
                        <span className="text-slate-500 dark:text-slate-400">Lieferant</span>
                        <div className="flex items-center gap-1.5">
                          <KonfidenzDot level={felder.konfidenz?.lieferant_name} />
                          <span className="font-medium dark:text-slate-200">{felder.lieferant_name}</span>
                        </div>
                      </div>
                      {ergebnis?.lieferant_vorschlaege && ergebnis.lieferant_vorschlaege.length > 0 && (
                        <LieferantVorschlagBox vorschlaege={ergebnis.lieferant_vorschlaege} />
                      )}
                    </div>
                  )}
                  {felder.externe_belegnr && (
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500 dark:text-slate-400">Rechnungsnr.</span>
                      <div className="flex items-center gap-1.5">
                        <KonfidenzDot level={felder.konfidenz?.externe_belegnr} />
                        <span className="font-medium dark:text-slate-200">{felder.externe_belegnr}</span>
                      </div>
                    </div>
                  )}
                  {felder.datum && (
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500 dark:text-slate-400">Datum</span>
                      <div className="flex items-center gap-1.5">
                        <KonfidenzDot level={felder.konfidenz?.datum} />
                        <span className="font-medium dark:text-slate-200">{formatDatum(felder.datum)}</span>
                      </div>
                    </div>
                  )}
                  {felder.faellig_am && (
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500 dark:text-slate-400">Fällig am</span>
                      <div className="flex items-center gap-1.5">
                        <KonfidenzDot level={felder.konfidenz?.faellig_am} />
                        <span className="font-medium dark:text-slate-200">{formatDatum(felder.faellig_am)}</span>
                      </div>
                    </div>
                  )}
                  {felder.gesamt_brutto && (
                    <div className="flex justify-between items-center border-t border-slate-200 dark:border-slate-700 pt-2 mt-2 font-semibold">
                      <span className="text-slate-600 dark:text-slate-300">Brutto</span>
                      <div className="flex items-center gap-1.5">
                        <KonfidenzDot level={felder.konfidenz?.gesamt_brutto} />
                        <span className="dark:text-slate-100">{formatEuro(felder.gesamt_brutto)}</span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {ergebnis.positionen.length > 0 && (
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {ergebnis.positionen.length} Position{ergebnis.positionen.length !== 1 ? 'en' : ''} erkannt
                </p>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => { setSchritt('upload'); setErgebnis(null); setDatei(null) }}
                  className="flex-1 px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 dark:text-slate-300"
                >
                  Andere Datei
                </button>
                <button
                  onClick={() => {
                    handlePdfOeffnen()   // öffnet PDF zur Kontrolle – kein-op wenn kein temp_url
                    if (datei) onWeiter(ergebnis, datei)
                  }}
                  className="flex-1 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Rechnung erstellen →
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}


// ---------------------------------------------------------------------------
// Haupt-Seite
// ---------------------------------------------------------------------------

type FilterModus = 'monat' | 'datum' | 'zeitraum' | 'jahr' | 'alle'

export function RechnungenPage({ modus = 'rechnungen' }: { modus?: 'rechnungen' | 'lieferscheine' } = {}) {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [typ, setTyp] = useState<'eingang' | 'ausgang'>('ausgang')
  const istLieferscheinSeite = modus === 'lieferscheine'
  const lieferscheinModus = istLieferscheinSeite
  const [zahlungsstatus, setZahlungsstatus] = useState('')
  const [lsAbrechnungFilter, setLsAbrechnungFilter] = useState<'' | 'offen' | 'entwurf' | 'abgerechnet'>('')
  const [suche, setSuche] = useState('')
  const [filterModus, setFilterModus] = useState<FilterModus>('monat')
  const [monat, setMonat] = useState(aktuellerMonat())
  const [datum, setDatum] = useState(heuteIso())
  const [datumVon, setDatumVon] = useState(heuteIso())
  const [datumBis, setDatumBis] = useState(heuteIso())
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [pendingEditRechnung, setPendingEditRechnung] = useState<Rechnung | null>(null)
  const [detailVersion, setDetailVersion] = useState(0)

  // ?open=ID oder ?id=ID: direkt zu einem Dokument springen
  useEffect(() => {
    const openId = searchParams.get('open') ?? searchParams.get('id')
    if (openId) {
      const id = parseInt(openId, 10)
      if (!isNaN(id)) {
        getRechnung(id)
          .then((r) => {
            setTyp(r.typ)
            setFilterModus('alle')
            setSelectedId(r.id)
            setPendingEditRechnung(r)
            setSuche(r.rechnungsnummer ?? '')
            setSearchParams({}, { replace: true })
          })
          .catch(() => setSearchParams({}, { replace: true }))
        return
      }
    }
    // ?typ=eingang|ausgang: direkt zum Typ springen (z.B. per Tastaturkürzel)
    const typParam = searchParams.get('typ')
    if (typParam === 'eingang' || typParam === 'ausgang') {
      setTyp(typParam)
      // ?vorlage=ID: Eingangsrechnung aus Buchungsvorlage vorausfüllen (Warte-auf-Beleg)
      const vorlageParam = searchParams.get('vorlage')
      if (typParam === 'eingang' && vorlageParam) {
        const vorlageId = parseInt(vorlageParam, 10)
        if (!isNaN(vorlageId)) {
          setActiveVorlageId(vorlageId)
          // OCR-Daten aus BuchungsvorlagenPage (Upload-Schritt) nutzen wenn vorhanden
          const ocrKey = `vorlage_ocr_${vorlageId}`
          const stored = sessionStorage.getItem(ocrKey)
          if (stored) {
            sessionStorage.removeItem(ocrKey)
            try {
              const ocrData: AnalyseErgebnis = JSON.parse(stored)
              setImportPrefill(ocrData)
              setImportKey(k => k + 1)
              setFormModus('neu')
            } catch {
              setFormModus('neu')
            }
          } else {
            // Fallback: Vorlage-Daten manuell vorausfüllen (kein PDF hochgeladen)
            getBuchungsvorlage(vorlageId).then(v => {
              const ustSatz = parseFloat(v.ust_satz)
              const betrag = parseFloat(v.betrag)
              const netto = v.ist_brutto && ustSatz > 0
                ? (betrag / (1 + ustSatz / 100)).toFixed(2).replace('.', ',')
                : betrag.toFixed(2).replace('.', ',')
              const prefill: AnalyseErgebnis = {
                format: 'vorlage',
                felder: {},
                positionen: [{
                  beschreibung: v.bezeichnung,
                  menge: '1',
                  einheit: 'Monat',
                  netto,
                  ust_satz: String(ustSatz),
                }],
                warnungen: [],
                positionen_modus: 'netto',
                lieferant_vorschlaege: v.lieferant_id
                  ? [{ id: v.lieferant_id, name: v.lieferant_name ?? '', score: 1 }]
                  : [],
              }
              setImportPrefill(prefill)
              setImportKey(k => k + 1)
              setFormModus('neu')
            }).catch(() => setFormModus('neu'))
          }
        }
      }
      setSearchParams({}, { replace: true })
      return
    }
    // ?filterRechnungId=ID: Lieferscheine einer bestimmten Rechnung anzeigen
    const filterRId = searchParams.get('filterRechnungId')
    if (filterRId) {
      const id = parseInt(filterRId, 10)
      if (!isNaN(id)) {
        setLsFilterRechnungId(id)
        setLsFilterLabel(`Rechnung #${id}`)
        setSearchParams({}, { replace: true })
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  const [formModus, setFormModus] = useState<'neu' | 'bearbeiten' | null>(null)
  const [fehler, setFehler] = useState<string | null>(null)
  const [sortFaellig, setSortFaellig] = useState<'asc' | 'desc' | null>(null)
  const listContainerRef = useRef<HTMLDivElement>(null)
  const [zeigImport, setZeigImport] = useState(false)
  const [importPrefill, setImportPrefill] = useState<AnalyseErgebnis | null>(null)
  const [importDatei, setImportDatei] = useState<File | null>(null)
  const [importKey, setImportKey] = useState(0)
  const [activeVorlageId, setActiveVorlageId] = useState<number | null>(null)
  const [selectedLsIds, setSelectedLsIds] = useState<Set<number>>(new Set())
  const [zeigSammelrechnung, setZeigSammelrechnung] = useState(false)
  const [srDatum, setSrDatum] = useState(heuteIso())
  const [srLeistungVon, setSrLeistungVon] = useState('')
  const [srLeistungBis, setSrLeistungBis] = useState('')
  const [lsFilterRechnungId, setLsFilterRechnungId] = useState<number | null>(null)
  const [lsFilterLabel, setLsFilterLabel] = useState<string>('')

  const aktivesJahr = new Date().getFullYear()
  const filterParams =
    filterModus === 'monat'
      ? { monat }
      : filterModus === 'datum'
        ? { datum_von: datum, datum_bis: datum }
        : filterModus === 'zeitraum'
          ? { datum_von: datumVon, datum_bis: datumBis }
          : filterModus === 'alle'
            ? {}  // kein Datumsfilter – alle Rechnungen
            : { datum_von: `${aktivesJahr}-01-01`, datum_bis: `${aktivesJahr}-12-31` }

  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen })
  const lieferscheinAktiv = !!unternehmen?.lieferschein_aktiv

  const { data: rechnungen, isLoading } = useQuery({
    queryKey: ['rechnungen', typ, zahlungsstatus, filterModus, monat, datum, datumVon, datumBis, lieferscheinModus],
    queryFn: () => lieferscheinModus
      ? getLieferscheine()
      : getRechnungen({ typ, zahlungsstatus: zahlungsstatus || undefined, ...filterParams }),
  })

  const _fromQuery = rechnungen?.find((r) => r.id === selectedId) ?? null
  const _fromPending = (pendingEditRechnung?.id === selectedId ? pendingEditRechnung : null)
  // Query-Version bevorzugen wenn bezahlt_betrag höher (Zahlung wurde gebucht)
  const selectedRechnung = (() => {
    if (!_fromQuery && !_fromPending) return null
    if (!_fromQuery) return _fromPending
    if (!_fromPending) return _fromQuery
    const qBez = parseFloat(_fromQuery.bezahlt_betrag ?? '0')
    const pBez = parseFloat(_fromPending.bezahlt_betrag ?? '0')
    return qBez >= pBez ? _fromQuery : _fromPending
  })()

  const createMutation = useMutation({
    mutationFn: createRechnung,
    onSuccess: async (r) => {
      if (importDatei) {
        try { await uploadBeleg(r.id, importDatei) } catch {}
        setImportDatei(null)
      }
      if (activeVorlageId) {
        try { await erledigtVorlage(activeVorlageId) } catch {}
        setActiveVorlageId(null)
        qc.invalidateQueries({ queryKey: ['buchungsvorlagen'] })
      }
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
      qc.invalidateQueries({ queryKey: ['auftraege'] })
      setSelectedId(null)
      setFehler(null)
    },
    onError: (e: Error) => setFehler(e.message),
  })

  const lieferscheinAusRechnungMutation = useMutation({
    mutationFn: lieferscheinAusRechnung,
    onSuccess: (ls) => {
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
      // Auf Lieferscheine-Seite navigieren statt Modus intern wechseln
      navigate(`/lieferscheine?id=${ls.id}`)
    },
    onError: (e: Error) => alert((e as Error).message),
  })

  const rechnungAusLsMutation = useMutation({
    mutationFn: rechnungAusLieferschein,
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
      setSelectedLsIds(new Set())
      setZeigSammelrechnung(false)
      setFehler(null)
      // Auf Rechnungen-Seite navigieren statt Modus intern wechseln
      navigate(`/rechnungen?id=${r.id}`)
    },
    onError: (e: Error) => setFehler(e.message),
  })

  const sammelrechnungMutation = useMutation({
    mutationFn: sammelrechnungErstellen,
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
      setZeigSammelrechnung(false)
      setSelectedLsIds(new Set())
      // Auf Rechnungen-Seite navigieren
      navigate(`/rechnungen?id=${r.id}`)
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
          (r.externe_belegnr ?? '').toLowerCase().includes(q) ||
          (r.lieferschein_zu_rechnung_nr ?? '').toLowerCase().includes(q)
        )
      })
    : alleRechnungen

  const listeGefiltert = (() => {
    let result = lsFilterRechnungId != null && lieferscheinModus
      ? liste.filter(r => r.lieferschein_zu_rechnung_id === lsFilterRechnungId)
      : liste
    if (lieferscheinModus && lsAbrechnungFilter) {
      result = result.filter(r => {
        if (lsAbrechnungFilter === 'offen') return !r.lieferschein_zu_rechnung_id
        if (lsAbrechnungFilter === 'entwurf') return r.lieferschein_zu_rechnung_id != null && !!r.lieferschein_rechnung_ist_entwurf
        if (lsAbrechnungFilter === 'abgerechnet') return r.lieferschein_zu_rechnung_id != null && !r.lieferschein_rechnung_ist_entwurf
        return true
      })
    }
    return result
  })()

  const listeSortiert = sortFaellig
    ? [...listeGefiltert].sort((a, b) => {
        const fa = a.faellig_am ?? ''
        const fb = b.faellig_am ?? ''
        return sortFaellig === 'asc' ? fa.localeCompare(fb) : fb.localeCompare(fa)
      })
    : listeGefiltert

  // Keyboard-Navigation: globaler Listener damit der Focus-Zustand
  // des Detail-Panels oder anderer Elemente nicht stört.
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
      // Nicht aktiv wenn der Nutzer in ein Feld tippt oder ein Formular offen ist
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase()
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return
      if (formModus) return
      if (!listeSortiert.length) return
      e.preventDefault()
      const idx = selectedId != null ? listeSortiert.findIndex(r => r.id === selectedId) : -1
      const nextIdx = e.key === 'ArrowDown'
        ? Math.min(idx + 1, listeSortiert.length - 1)
        : Math.max(idx - 1, 0)
      const next = listeSortiert[nextIdx]
      if (!next) return
      setSelectedId(next.id)
      // Fokus auf den Listen-Container (outline-none) damit kein Browser-Fokus-Ring
      // auf dem Detail-Panel oder zuletzt geklickten Element sichtbar bleibt
      listContainerRef.current?.focus({ preventScroll: true })
      requestAnimationFrame(() => {
        const row = listContainerRef.current?.querySelector(`[data-rechnung-id="${next.id}"]`)
        row?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
      })
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [listeSortiert, selectedId, formModus])

  // Summen (Entwürfe + Stornierte werden aus dem offenen Saldo ausgeschlossen)
  const gesamt = liste.reduce(
    (acc, r) => ({
      brutto: acc.brutto + (r.ist_entwurf || r.storniert ? 0 : parseFloat(r.brutto_gesamt)),
      offen: acc.offen + (r.ist_entwurf || r.storniert || r.zahlungsstatus === 'uneinbringlich'
        ? 0
        : Math.max(0, parseFloat(r.brutto_gesamt) - parseFloat(r.bezahlt_betrag))),
    }),
    { brutto: 0, offen: 0 }
  )

  return (
    <div className="flex h-full">
      {zeigImport && (
        <ImportDialog
          onClose={() => setZeigImport(false)}
          onWeiter={(ergebnis, datei) => {
            setZeigImport(false)
            setImportPrefill(ergebnis)
            setImportDatei(datei)
            setTyp('eingang')
            setFormModus('neu')
            setSelectedId(null)
            setImportKey(k => k + 1)
          }}
        />
      )}
      {/* Linke Spalte */}
      <div className={`${formModus ? 'w-1/3 min-w-[260px] shrink-0' : 'flex-1'} flex flex-col border-e border-slate-200 dark:border-slate-700 min-w-0 min-h-0 transition-all`}>
        <div className="p-6 pb-4">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">{lieferscheinModus ? 'Lieferscheine' : 'Rechnungen'}</h2>
            <div className="flex gap-2">
              {typ === 'eingang' && (
                <button
                  onClick={() => setZeigImport(true)}
                  className="px-4 py-2 text-sm font-medium border border-blue-300 dark:border-blue-700 text-blue-700 dark:text-blue-300 rounded-xl hover:bg-blue-50 dark:hover:bg-blue-950 transition-colors"
                >
                  ↑ Importieren
                </button>
              )}
              <button
                onClick={() => { setFormModus('neu'); setSelectedId(null); setImportPrefill(null) }}
                className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors"
              >
                {lieferscheinModus ? '+ Neuer Lieferschein' : '+ Neue Rechnung'}
              </button>
            </div>
          </div>

          {/* Tabs + Filter */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Eingang/Ausgang – nur auf Rechnungen-Seite */}
            {!istLieferscheinSeite && (
              <div className="flex rounded-lg border border-slate-300 dark:border-slate-600 overflow-hidden text-sm">
                {(['ausgang', 'eingang'] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => { setTyp(t); setSelectedId(null); setSelectedLsIds(new Set()); setLsFilterRechnungId(null) }}
                    className={`px-4 py-1.5 transition-colors ${
                      typ === t ? 'bg-blue-600 text-white' : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
                    }`}
                  >
                    {t === 'ausgang' ? 'Ausgang' : 'Eingang'}
                  </button>
                ))}
              </div>
            )}

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
                onChange={guardedDateChange(setDatum)}
                className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
              />
            )}
            {filterModus === 'zeitraum' && (
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={datumVon}
                  onChange={guardedDateChange(setDatumVon)}
                  className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
                />
                <span className="text-slate-400 dark:text-slate-500 text-sm">bis</span>
                <input
                  type="date"
                  value={datumBis}
                  min={datumVon}
                  onChange={guardedDateChange(setDatumBis)}
                  className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
                />
              </div>
            )}

            {/* Suche */}
            <input
              type="search"
              placeholder={lieferscheinModus ? 'Nummer, Partner oder Rechnung suchen…' : 'Nummer oder Partner suchen…'}
              value={suche}
              onChange={(e) => setSuche(e.target.value)}
              className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 w-56"
            />

            {/* Status-Filter */}
            {lieferscheinModus ? (
              <select
                value={lsAbrechnungFilter}
                onChange={(e) => setLsAbrechnungFilter(e.target.value as typeof lsAbrechnungFilter)}
                className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
              >
                <option value="">Alle Status</option>
                <option value="offen">Nicht abgerechnet</option>
                <option value="entwurf">Rechnungsentwurf</option>
                <option value="abgerechnet">Abgerechnet</option>
              </select>
            ) : (
              <select
                value={zahlungsstatus}
                onChange={(e) => setZahlungsstatus(e.target.value)}
                className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
              >
                <option value="">Alle Status</option>
                <option value="offen">Offen</option>
                <option value="teilweise">Teilweise bezahlt</option>
                <option value="bezahlt">Bezahlt</option>
                <option value="uneinbringlich">Uneinbringlich</option>
                <option value="entwurf">Entwurf</option>
                <option value="storniert">Storniert</option>
              </select>
            )}
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
            {lieferscheinModus ? (
              <>
                <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
                  <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Lieferscheine</p>
                  <p className="text-lg font-bold text-slate-800 dark:text-slate-100">{liste.length}</p>
                </div>
                <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
                  <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Nicht abgerechnet</p>
                  <p className="text-lg font-bold text-amber-600 dark:text-amber-400">
                    {liste.filter(r => !r.lieferschein_zu_rechnung_id).length}
                  </p>
                </div>
                <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
                  <p className="text-xs text-slate-500 dark:text-slate-400 mb-0.5">Abgerechnet</p>
                  <p className="text-lg font-bold text-green-600 dark:text-green-400">
                    {liste.filter(r => r.lieferschein_zu_rechnung_id != null && !r.lieferschein_rechnung_ist_entwurf).length}
                  </p>
                </div>
              </>
            ) : (
              <>
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
              </>
            )}
          </div>
        )}

        {/* Tabelle */}
        <div ref={listContainerRef} tabIndex={0} className="flex-1 overflow-y-auto min-h-0 px-6 pb-6 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 dark:focus-visible:ring-blue-500 focus-visible:ring-offset-2 rounded-sm">
          {lieferscheinModus && lsFilterRechnungId != null && (
            <div className="mb-3 flex items-center gap-3 bg-teal-50 dark:bg-teal-950 border border-teal-200 dark:border-teal-800 rounded-xl px-4 py-2.5">
              <span className="text-sm text-teal-700 dark:text-teal-300 flex-1">
                Filter: Lieferscheine zu <span className="font-mono font-semibold">{lsFilterLabel}</span>
              </span>
              <button type="button" onClick={() => setLsFilterRechnungId(null)}
                className="text-xs text-teal-600 dark:text-teal-400 hover:text-teal-800">
                Filter aufheben ×
              </button>
            </div>
          )}
          {lieferscheinModus && selectedLsIds.size > 0 && (
            <div className="mb-3 flex items-center gap-3 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-xl px-4 py-2.5">
              <span className="text-sm text-blue-700 dark:text-blue-300 font-medium flex-1">
                {selectedLsIds.size} Lieferschein{selectedLsIds.size !== 1 ? 'e' : ''} ausgewählt
              </span>
              <button type="button" onClick={() => setSelectedLsIds(new Set())}
                className="text-xs text-blue-500 dark:text-blue-400 hover:text-blue-700">
                Auswahl aufheben
              </button>
              <button type="button"
                onClick={() => {
                  const selectedLs = (rechnungen ?? []).filter(r => selectedLsIds.has(r.id))
                  const dates = selectedLs.map(r => r.datum).sort()
                  setSrDatum(heuteIso())
                  setSrLeistungVon(dates[0] ?? '')
                  setSrLeistungBis(dates[dates.length - 1] ?? '')
                  setZeigSammelrechnung(true)
                }}
                className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 font-medium">
                Sammelrechnung erstellen →
              </button>
            </div>
          )}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            {isLoading ? (
              <p className="p-5 text-slate-400 dark:text-slate-500 text-sm">Lade Rechnungen…</p>
            ) : listeSortiert.length === 0 ? (
              <p className="p-5 text-slate-400 dark:text-slate-500 text-sm">Keine Rechnungen im gewählten Zeitraum.</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 dark:bg-slate-900 border-b border-slate-100 dark:border-slate-700">
                    {lieferscheinModus && (
                      <th className="pl-4 py-3 w-8">
                        <input type="checkbox" className="h-3.5 w-3.5 rounded border-slate-300 text-blue-600"
                          checked={listeSortiert.filter(r => !r.lieferschein_zu_rechnung_id).length > 0
                            && listeSortiert.filter(r => !r.lieferschein_zu_rechnung_id).every(r => selectedLsIds.has(r.id))}
                          onChange={(e) => {
                            const ids = listeSortiert.filter(r => !r.lieferschein_zu_rechnung_id).map(r => r.id)
                            setSelectedLsIds(e.target.checked ? new Set(ids) : new Set())
                          }}
                        />
                      </th>
                    )}
                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Datum</th>
                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Nummer</th>
                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Partner</th>
                    {lieferscheinModus ? (
                      <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Rechnung</th>
                    ) : (
                      <>
                        <th
                          className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide cursor-pointer select-none hover:text-slate-700 dark:hover:text-slate-200"
                          onClick={() => setSortFaellig(s => s === 'asc' ? 'desc' : s === 'desc' ? null : 'asc')}
                        >
                          Fällig am {sortFaellig === 'asc' ? '↑' : sortFaellig === 'desc' ? '↓' : ''}
                        </th>
                        <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Brutto</th>
                      </>
                    )}
                    <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Status</th>
                    {typ !== 'ausgang' && (
                      <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide w-8" title="Beleg angehängt">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5 mx-auto">
                          <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/>
                        </svg>
                      </th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {listeSortiert.map((r) => (
                    <tr
                      key={r.id}
                      data-rechnung-id={r.id}
                      tabIndex={0}
                      onClick={() => { setSelectedId(r.id); setFormModus(null) }}
                      className={`border-b border-slate-50 dark:border-slate-700 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-700 focus:outline-none cursor-pointer transition-colors ${
                        selectedId === r.id ? 'bg-blue-100 dark:bg-slate-600 border-l-2 border-l-blue-500' : ''
                      } ${selectedLsIds.has(r.id) ? 'bg-blue-50 dark:bg-blue-950' : ''} ${r.storniert ? 'opacity-50' : ''}`}
                    >
                      {lieferscheinModus && (
                        <td className="pl-4 py-3 w-8" onClick={e => e.stopPropagation()}>
                          {!r.lieferschein_zu_rechnung_id && (
                            <input type="checkbox" className="h-3.5 w-3.5 rounded border-slate-300 text-blue-600"
                              checked={selectedLsIds.has(r.id)}
                              onChange={e => setSelectedLsIds(prev => {
                                const next = new Set(prev)
                                e.target.checked ? next.add(r.id) : next.delete(r.id)
                                return next
                              })}
                            />
                          )}
                        </td>
                      )}
                      <td className="px-5 py-3 text-slate-500 dark:text-slate-400">{formatDatum(r.datum)}</td>
                      <td className="px-5 py-3 font-mono text-xs text-slate-400 dark:text-slate-500">
                        {r.rechnungsnummer ?? '—'}
                        {r.dokument_typ === 'Gutschrift' && <span className="ml-1.5 text-[10px] text-purple-700 dark:text-purple-300 bg-purple-50 dark:bg-purple-950 border border-purple-200 dark:border-purple-800 rounded px-1">Gutschrift</span>}
                        {r.dokument_typ === 'Lieferschein' && (
                          lieferscheinModus
                            ? (r.herkunft_angebot_nr ?? r.herkunft_auftrag_nr)
                              ? <span className="ml-1.5 text-[10px] text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded px-1">
                                  aus {r.herkunft_angebot_nr ?? r.herkunft_auftrag_nr}
                                </span>
                              : null
                            : <span className="ml-1.5 text-[10px] text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-950 border border-teal-200 dark:border-teal-800 rounded px-1">
                                {!r.lieferschein_zu_rechnung_id ? 'Lieferschein' : r.lieferschein_rechnung_ist_entwurf ? 'Entwurf' : '✓ abgerechnet'}
                              </span>
                        )}
                        {!lieferscheinModus && r.dokument_typ !== 'Lieferschein' && r.dokument_typ !== 'Gutschrift' && (r.herkunft_auftrag_nr ?? r.herkunft_proforma_nr) && (
                          <span className="ml-1.5 text-[10px] text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded px-1">
                            aus {r.herkunft_auftrag_nr ?? r.herkunft_proforma_nr}
                          </span>
                        )}
                        {r.ist_entwurf && <span className="ml-1.5 text-[10px] text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded px-1">Entwurf</span>}
                        {r.storniert && <span className="ml-1.5 text-[10px] text-slate-400 dark:text-slate-500 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded px-1">Storniert</span>}
                      </td>
                      <td className="px-5 py-3 text-slate-700 dark:text-slate-200">
                        {r.typ === 'ausgang'
                          ? (r.kunde_name ?? r.partner_freitext ?? '—')
                          : (r.lieferant_name ?? r.partner_freitext ?? '—')}
                      </td>
                      {lieferscheinModus ? (
                        <td className="px-5 py-3 font-mono text-xs text-slate-500 dark:text-slate-400">
                          {r.lieferschein_zu_rechnung_nr
                            ? <span className={r.lieferschein_rechnung_ist_entwurf ? 'text-amber-600 dark:text-amber-400' : 'text-teal-700 dark:text-teal-400'}>{r.lieferschein_zu_rechnung_nr}</span>
                            : <span className="text-slate-300 dark:text-slate-600">—</span>}
                        </td>
                      ) : (
                        <>
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
                        </>
                      )}
                      <td className="px-5 py-3 text-center">
                        {r.storniert
                          ? <span className="text-xs px-2 py-0.5 rounded border bg-slate-100 text-slate-500 border-slate-200 dark:bg-slate-700 dark:text-slate-400 dark:border-slate-600">Storniert</span>
                          : r.ist_entwurf
                            ? <span className="text-xs px-2 py-0.5 rounded border bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800">Entwurf</span>
                            : r.dokument_typ === 'Lieferschein'
                              ? <LieferscheinStatusBadge r={r} />
                              : <StatusBadge status={r.zahlungsstatus as 'offen' | 'teilweise' | 'bezahlt' | 'uneinbringlich'} />}
                      </td>
                      {typ !== 'ausgang' && (
                        <td className="px-3 py-3 text-center">
                          {r.typ === 'eingang' && r.beleg && (
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5 mx-auto text-slate-400 dark:text-slate-500">
                              <title>{r.beleg.original_name}</title>
                              <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/>
                            </svg>
                          )}
                        </td>
                      )}
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
                ? lieferscheinModus
                  ? 'Neuer Lieferschein'
                  : `Neue ${typ === 'ausgang' ? 'Ausgangsrechnung' : 'Eingangsrechnung'}`
                : selectedRechnung?.dokument_typ === 'Gutschrift'
                  ? 'Gutschrift bearbeiten'
                  : selectedRechnung?.dokument_typ === 'Lieferschein'
                    ? 'Lieferschein bearbeiten'
                    : 'Rechnung bearbeiten'}
            </h3>
            <button onClick={() => setFormModus(null)} className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-xl">×</button>
          </div>
          <div className="p-6">
            <RechnungForm
              key={importPrefill ? `import-${importKey}` : `manual-${formModus}-${selectedId ?? 'neu'}`}
              typ={formModus === 'bearbeiten' && selectedRechnung ? selectedRechnung.typ : typ}
              initial={formModus === 'bearbeiten' ? selectedRechnung ?? undefined : undefined}
              prefillFromAnalyse={formModus === 'neu' ? importPrefill ?? undefined : undefined}
              initialDokumentTyp={lieferscheinModus && formModus === 'neu' ? 'Lieferschein' : undefined}
              onSave={(data) => {
                setPendingEditRechnung(null)
                if (formModus === 'bearbeiten' && selectedId) {
                  updateMutation.mutate({ id: selectedId, data })
                } else {
                  createMutation.mutate(data)
                }
              }}
              onCancel={() => { setPendingEditRechnung(null); setFormModus(null) }}
            />
          </div>
        </div>
      )}

      {!formModus && (
        <div className="w-[28rem] shrink-0 h-full overflow-hidden">
          {selectedRechnung ? (
            <RechnungDetail
              key={`${selectedId ?? 0}-${detailVersion}`}
              rechnung={selectedRechnung}
              onClose={() => setSelectedId(null)}
              onEdit={() => setFormModus('bearbeiten')}
              onDelete={() => {
                if (confirm('Rechnung wirklich löschen?')) {
                  deleteMutation.mutate(selectedRechnung.id)
                }
              }}
              onFinalisiert={(r) => setPendingEditRechnung(r)}
              onZahlungErfasst={(r) => { setPendingEditRechnung(r); setDetailVersion(v => v + 1) }}
              onGutschriftCreated={(gs) => { setPendingEditRechnung(gs); setSelectedId(gs.id); setFormModus('bearbeiten') }}
              onRechnungAusLs={(id) => rechnungAusLsMutation.mutate(id)}
              onSelectId={(id, isLieferschein, filterRechnungId) => {
                // Seitenwechsel wenn Ziel auf anderer Seite liegt
                if (isLieferschein && !istLieferscheinSeite) {
                  navigate(filterRechnungId !== undefined
                    ? `/lieferscheine?filterRechnungId=${filterRechnungId}`
                    : `/lieferscheine?id=${id}`)
                  return
                }
                if (!isLieferschein && istLieferscheinSeite) {
                  navigate(`/rechnungen?id=${id}`)
                  return
                }
                setTyp('ausgang')
                if (filterRechnungId !== undefined) {
                  setLsFilterRechnungId(filterRechnungId)
                  const r = (rechnungen ?? []).find(r => r.id === filterRechnungId)
                  setLsFilterLabel(r?.rechnungsnummer ?? `Rechnung #${filterRechnungId}`)
                  setSelectedId(null)
                } else {
                  setLsFilterRechnungId(null)
                  setSelectedId(id)
                }
              }}
              onLieferscheinAusRechnung={lieferscheinAktiv ? (id) => lieferscheinAusRechnungMutation.mutate(id) : undefined}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-slate-400 dark:text-slate-500 text-sm">
              Rechnung auswählen
            </div>
          )}
        </div>
      )}

      {/* Sammelrechnung-Dialog – fixed, daher position innerhalb des flex-Containers kein Problem */}
      {zeigSammelrechnung && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-800 dark:text-slate-100">Sammelrechnung erstellen</h3>
              <button onClick={() => setZeigSammelrechnung(false)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 text-xl">×</button>
            </div>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Aus {selectedLsIds.size} Lieferschein{selectedLsIds.size !== 1 ? 'en' : ''} wird eine Sammelrechnung (Entwurf) erstellt.
            </p>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Rechnungsdatum *</label>
                <input type="date" value={srDatum} onChange={e => setSrDatum(e.target.value)} required
                  className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Leistung von</label>
                  <input type="date" value={srLeistungVon} onChange={e => setSrLeistungVon(e.target.value)}
                    className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Leistung bis</label>
                  <input type="date" value={srLeistungBis} onChange={e => setSrLeistungBis(e.target.value)}
                    className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                </div>
              </div>
            </div>
            {sammelrechnungMutation.isError && (
              <p className="text-sm text-red-600 dark:text-red-400">{(sammelrechnungMutation.error as Error).message}</p>
            )}
            <div className="flex gap-2 pt-1">
              <button
                onClick={() => sammelrechnungMutation.mutate({
                  lieferschein_ids: Array.from(selectedLsIds),
                  datum: srDatum,
                  leistung_von: srLeistungVon || undefined,
                  leistung_bis: srLeistungBis || undefined,
                })}
                disabled={!srDatum || sammelrechnungMutation.isPending}
                className="flex-1 py-2 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 disabled:opacity-50"
              >
                {sammelrechnungMutation.isPending ? '…' : 'Sammelrechnung erstellen'}
              </button>
              <button onClick={() => setZeigSammelrechnung(false)}
                className="px-4 py-2 border border-slate-300 dark:border-slate-600 text-sm rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                Abbrechen
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
