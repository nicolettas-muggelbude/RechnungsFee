import { invoke } from '@tauri-apps/api/core'
export { invoke }

// --- API-Basis-URL ---
// Im Tauri-Produktionsmodus: Backend-Port per IPC-Command holen.
// Im Vite-Dev-Modus: Vite-Proxy leitet /api → http://localhost:8002 weiter.

let _baseUrl: string | null = null

export function isTauri(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window
}

async function getBaseUrl(): Promise<string> {
  if (_baseUrl !== null) return _baseUrl

  if (!isTauri() || import.meta.env.DEV) {
    _baseUrl = '/api'
    return _baseUrl
  }

  // Tauri-Produktionsmodus: Port vom Rust-Backend holen
  const port = await invoke<number>('get_backend_port')
  _baseUrl = `http://127.0.0.1:${port}/api`
  return _baseUrl
}

/** Wartet bis das Backend antwortet (max. 300 × 200 ms = 60 s).
 *  Nach einem Update scannt Windows Defender die neue backend.exe und PyInstaller
 *  extrahiert sich neu – das dauert typisch 20–60 s. */
async function waitForBackend(baseUrl: string): Promise<void> {
  for (let i = 0; i < 300; i++) {
    try {
      const res = await fetch(`${baseUrl}/setup/status`)
      if (res.ok) return
    } catch {
      // Backend noch nicht bereit
    }
    await new Promise((r) => setTimeout(r, 200))
  }
  console.warn('[RechnungsFee] Backend nach 60 s nicht erreichbar')
}

// Promise der resolved wenn das Backend bereit ist – alle request()-Calls warten darauf.
// fire-and-forget war falsch: useQuery startete sofort ohne auf waitForBackend zu warten.
let _backendReady: Promise<void> = Promise.resolve()

// Im Tauri-Modus einmalig warten, damit das UI erst lädt wenn das Backend ready ist
if (isTauri() && !import.meta.env.DEV) {
  _backendReady = getBaseUrl().then((url) => waitForBackend(url))
}

// --- HTTP-Hilfsfunktion ---

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  await _backendReady  // Wartet bis Backend bereit ist (nach Update kann das 30–60 s dauern)
  const base = await getBaseUrl()
  const isFormData = options?.body instanceof FormData
  const res = await fetch(`${base}${path}`, {
    headers: isFormData ? {} : { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    // FastAPI gibt bei 422 ein Array zurück: [{ loc, msg, type }]
    const detail = err.detail
    const message = Array.isArray(detail)
      ? detail.map((e: any) => (e.msg ?? JSON.stringify(e)).replace(/^Value error,\s*/i, '')).join(' · ')
      : String(detail ?? 'Unbekannter Fehler')
    throw new Error(message)
  }
  // 204 No Content
  if (res.status === 204) return undefined as T
  return res.json()
}

/** Liefert die aktuelle Basis-URL für direkte fetch/window.open-Aufrufe. */
export async function getApiBase(): Promise<string> {
  return getBaseUrl()
}

/** Öffnet eine URL (PDF, Export) in einem neuen Tauri-Fenster bzw. Browser-Tab.
 *  CSV/ZIP-URLs werden immer als Datei-Download behandelt (kein WebviewWindow). */
export async function openUrl(url: string) {
  const isDownload = url.includes('format=csv') || /\.(csv|zip)(\?|$)/i.test(url)
  if (isDownload) {
    const res = await fetch(url)
    if (!res.ok) throw new Error(`Download fehlgeschlagen: ${res.status}`)
    const blob = await res.blob()
    const cd = res.headers.get('Content-Disposition') ?? ''
    const match = cd.match(/filename[*]?=(?:UTF-8''|"?)([^";\r\n]+)/i)
    const ext = url.includes('format=csv') ? '.csv' : '.zip'
    _triggerBlobDownload(blob, match?.[1]?.trim() ?? `export${ext}`)
    return
  }
  if (isTauri()) {
    const isLocal = url.startsWith('http://127.0.0.1') || url.startsWith('http://localhost')
      || url.startsWith('blob:')
    if (isLocal) {
      await openInPdfWindow(url)
      return
    }
    try { await invoke('open_url', { url }) } catch { /* ignorieren */ }
  } else {
    window.open(url, '_blank')
  }
}

/** Öffnet ein Dokument in einem neuen Tauri-WebView-Fenster (eigenes OS-Fenster).
 *  Funktioniert für HTTP-URLs und blob:-URLs gleichermaßen. */
export async function openInPdfWindow(url: string, title = 'Dokument') {
  const { WebviewWindow } = await import('@tauri-apps/api/webviewWindow')
  const label = `pdf-${Date.now()}`
  new WebviewWindow(label, {
    url,
    title,
    width: 960,
    height: 800,
    center: true,
    resizable: true,
  })
}

// --- Setup ---
export type SetupStatus = {
  ist_eingerichtet: boolean
  hat_unternehmen: boolean
  hat_konto: boolean
  hat_kategorien: boolean
}
export const getSetupStatus = () => request<SetupStatus>('/setup/status')
export const setKassenbestand = (betrag: string) =>
  request<{ belegnr: string; betrag: string }>('/setup/kassenbestand', {
    method: 'POST',
    body: JSON.stringify({ betrag }),
  })
export const getKleinunternehmerUmsatz = () =>
  request<{ jahr: number; umsatz_netto: number; grenze_kritisch: number; grenze_warnung: number }>('/setup/kleinunternehmer-umsatz')

// --- Unternehmen ---
export type Unternehmen = {
  id?: number
  firmenname: string
  vorname?: string
  nachname?: string
  strasse: string
  hausnummer: string
  plz: string
  ort: string
  land: string
  steuernummer?: string
  ust_idnr?: string
  w_idnr?: string
  finanzamt?: string
  voranmeldungsrhythmus: 'monat' | 'quartal'
  ist_kleinunternehmer: boolean
  bezieht_transferleistungen: boolean
  geburtsdatum?: string | null
  bg_nummer?: string | null
  jobcenter_name?: string | null
  leistungsbescheid_monat?: string | null
  versteuerungsart: 'ist' | 'soll'
  kontenrahmen: 'SKR03' | 'SKR04' | 'SKR49'
  taetigkeitsart: string
  rechtsform: string
  email?: string
  telefon?: string
  webseite?: string
  handelsregister_nr?: string
  handelsregister_gericht?: string
  iban?: string
  bic?: string
  bank_name?: string
  berufsbezeichnung?: string | null
  kammer_mitgliedschaft?: string | null
  zahlungshinweis_aktiv?: boolean
  pdf_vorlage?: number
  logo_pfad?: string | null
  mail_betreff_vorlage?: string | null
  mail_text_vorlage?: string | null
  mail_betreff_angebot?: string | null
  mail_text_angebot?: string | null
  mail_betreff_proforma?: string | null
  mail_text_proforma?: string | null
  mail_betreff_auftrag?: string | null
  mail_text_auftrag?: string | null
  mail_signatur?: string | null
  smtp_aktiv?: boolean
  smtp_host?: string | null
  smtp_port?: number
  smtp_ssl?: boolean
  smtp_user?: string | null
  smtp_passwort?: string | null
  smtp_von_adresse?: string | null
  unterschrift_bild?: string | null
  unterschrift_auf_rechnung?: boolean
  standard_zahlungsziel?: number
  qr_zahlung_aktiv?: boolean
  standard_skonto_prozent?: number | null
  standard_skonto_tage?: number | null
  lieferschein_aktiv?: boolean
  angebote_aktiv?: boolean
  proforma_aktiv?: boolean
  auftraege_aktiv?: boolean
  wiederkehrend_aktiv?: boolean
  buchungsvorlagen_aktiv?: boolean
}
export const getUnternehmen = () => request<Unternehmen | null>('/unternehmen')
export const createUnternehmen = (data: Unternehmen) =>
  request<Unternehmen>('/unternehmen', { method: 'POST', body: JSON.stringify(data) })
export const updateUnternehmen = (data: Partial<Unternehmen>) =>
  request<Unternehmen>('/unternehmen', { method: 'PUT', body: JSON.stringify(data) })

export async function uploadLogo(file: File): Promise<Unternehmen> {
  const base = await getBaseUrl()
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${base}/unternehmen/logo`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Logo-Upload fehlgeschlagen')
  }
  return res.json()
}

export async function deleteLogo(): Promise<void> {
  const base = await getBaseUrl()
  const res = await fetch(`${base}/unternehmen/logo`, { method: 'DELETE' })
  if (!res.ok && res.status !== 204) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Logo löschen fehlgeschlagen')
  }
}

export async function getLogoUrl(): Promise<string> {
  const base = await getBaseUrl()
  return `${base}/unternehmen/logo`
}

// --- Konten ---
export type Konto = {
  id?: number
  name: string
  anbieter: string
  kontoart: 'bank' | 'zahlungsdienstleister'
  iban?: string
  bic?: string
  kennung?: string
  kontotyp: 'geschaeftlich' | 'mischkonto'
  ist_standard: boolean
  aktiv?: boolean
  erstellt_am?: string
}
export const getKonten = () => request<Konto[]>('/konten')
export const getKontenAlle = () => request<Konto[]>('/konten?nur_aktive=false')
export const createKonto = (data: Omit<Konto, 'id' | 'aktiv' | 'erstellt_am'>) =>
  request<Konto>('/konten', { method: 'POST', body: JSON.stringify(data) })
export const updateKonto = (id: number, data: Partial<Omit<Konto, 'id' | 'erstellt_am'>>) =>
  request<Konto>(`/konten/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteKonto = (id: number) =>
  request<void>(`/konten/${id}`, { method: 'DELETE' })

// --- Kategorien ---
export type Kategorie = {
  id: number
  name: string
  kontenart: string
  konto_skr03?: string
  konto_skr04?: string
  konto_skr49?: string
  konto_skr03_default?: string
  konto_skr04_default?: string
  user_modified_skr03: boolean
  user_modified_skr04: boolean
  eks_kategorie?: string
  euer_zeile?: number
  vorsteuer_prozent: string
  ust_satz_standard: number
  ist_system: boolean
  aktiv: boolean
  beschreibung: string | null
}
export type KategorieCreate = {
  name: string
  kontenart: string
  konto_skr03?: string
  konto_skr04?: string
  euer_zeile?: number
  eks_kategorie?: string
  vorsteuer_prozent?: number
  ust_satz_standard?: number
  beschreibung?: string | null
}
export const getKategorien = (nurAktive = false) =>
  request<Kategorie[]>(`/kategorien${nurAktive ? '?nur_aktive=true' : ''}`)
export const toggleKategorieAktiv = (id: number) =>
  request<Kategorie>(`/kategorien/${id}/aktiv`, { method: 'PATCH' })
export const updateKategorieKonten = (id: number, data: { konto_skr03?: string; konto_skr04?: string }) =>
  request<Kategorie>(`/kategorien/${id}/konten`, { method: 'PATCH', body: JSON.stringify(data) })
export const resetKategorieKonten = (id: number) =>
  request<Kategorie>(`/kategorien/${id}/konten/reset`, { method: 'POST' })
export const updateKategorieBeschreibung = (id: number, beschreibung: string | null) =>
  request<Kategorie>(`/kategorien/${id}/beschreibung`, { method: 'PATCH', body: JSON.stringify({ beschreibung }) })
export const createKategorie = (data: KategorieCreate) =>
  request<Kategorie>(`/kategorien`, { method: 'POST', body: JSON.stringify(data) })
export const updateKategorie = (id: number, data: KategorieCreate) =>
  request<Kategorie>(`/kategorien/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteKategorie = (id: number) =>
  request<void>(`/kategorien/${id}`, { method: 'DELETE' })
export async function downloadKategorienPdf(): Promise<void> {
  const base = await getBaseUrl()
  await openUrl(`${base}/kategorien/export/pdf`)
}

// --- Journal ---
export type JournalEintrag = {
  id: number
  datum: string
  belegnr: string
  beschreibung: string
  kategorie_id: number | null
  kategorie_kontenart: string | null
  kunde_id: number | null
  kunde_name: string | null
  kunde_email: string | null
  kunde_zugferd_aktiv: boolean
  zahlungsart: 'Bar' | 'Karte' | 'Bank' | 'PayPal' | 'Keine'
  art: 'Einnahme' | 'Ausgabe'
  netto_betrag: string
  ust_satz: string
  ust_betrag: string
  brutto_betrag: string
  vorsteuerabzug: boolean
  steuerbefreiung_grund: string | null
  externe_belegnr?: string
  rechnung_id?: number | null
  rechnung_nr?: string | null
  konto_skr03?: string | null
  konto_skr04?: string | null
  konto_ust_skr03?: string | null
  konto_ust_skr04?: string | null
  immutable: boolean
  erstellt_am: string
  km_anzahl?: number | null
  ist_ig_erwerb?: boolean
  ust_sonderfall?: string | null
}

export type JournalEintragCreate = {
  datum: string
  beschreibung: string
  kategorie_id?: number
  kunde_id?: number
  zahlungsart: 'Bar' | 'Karte' | 'Bank' | 'PayPal' | 'Keine'
  art: 'Einnahme' | 'Ausgabe'
  brutto_betrag: string
  ust_satz: string
  vorsteuerabzug?: boolean
  externe_belegnr?: string
  km_anzahl?: number | null
  ist_ig_erwerb?: boolean
  ust_sonderfall?: string | null
}

export type MonatsUebersicht = {
  monat: string
  einnahmen: string
  ausgaben: string
  saldo: string
  anzahl_buchungen: number
}

function toQuery(params: Record<string, string | number | undefined | null>): string {
  const q = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join('&')
  return q ? `?${q}` : ''
}

export const getJournal = (filter?: {
  monat?: string
  datum_von?: string
  datum_bis?: string
  kategorie_id?: number
  art?: string
  zahlungsart_typ?: 'bar' | 'unbar'
}) => request<JournalEintrag[]>(`/journal${toQuery(filter ?? {})}`)
export const createJournaleintrag = (data: JournalEintragCreate) =>
  request<JournalEintrag>('/journal', { method: 'POST', body: JSON.stringify(data) })
export const getJournaleintrag = (id: number) =>
  request<JournalEintrag>(`/journal/${id}`)
export const stornoJournaleintrag = (id: number, grund: string) =>
  request<JournalEintrag>(`/journal/${id}/storno`, {
    method: 'POST',
    body: JSON.stringify({ grund }),
  })

export type SplitPosition = {
  beschreibung: string
  kategorie_id?: number
  brutto_betrag: string
  ust_satz: string
  vorsteuerabzug: boolean
}

export type SplitBuchungCreate = {
  datum: string
  art: 'Einnahme' | 'Ausgabe'
  zahlungsart: 'Bar' | 'Karte' | 'Bank' | 'PayPal' | 'Keine'
  externe_belegnr?: string
  kunde_id?: number
  positionen: SplitPosition[]
}

export const createSplitBuchung = (data: SplitBuchungCreate) =>
  request<JournalEintrag[]>('/journal/split', {
    method: 'POST',
    body: JSON.stringify(data),
  })
export const getMonatsUebersicht = (monat: string) =>
  request<MonatsUebersicht>(`/journal/statistik/monat?monat=${encodeURIComponent(monat)}`)
export const getNaechsteBelegnr = (datum?: string) =>
  request<{ belegnr: string }>(`/journal/naechste-belegnr${datum ? `?datum=${datum}` : ''}`)
export const getKassenstand = () =>
  request<{ kassenstand: string }>('/journal/kassenstand')
export const getJournalBelegUrl = async (id: number, drucken = false, download = false): Promise<string> => {
  const base = await getApiBase()
  const params = new URLSearchParams()
  if (drucken) params.set('drucken', '1')
  if (download) params.set('download', '1')
  const qs = params.toString()
  return `${base}/journal/${id}/beleg${qs ? `?${qs}` : ''}`
}

export const getKassenbuchExportUrl = async (
  datumVon: string, datumBis: string, format: 'pdf' | 'csv'
): Promise<string> => {
  const base = await getApiBase()
  return `${base}/journal/kassenbuch-export?datum_von=${datumVon}&datum_bis=${datumBis}&format=${format}`
}

export const getJournalExportUrl = async (
  params: {
    monat?: string
    datum_von?: string
    datum_bis?: string
    kategorie_id?: number
    art?: string
    zahlungsart_typ?: string
    format: 'pdf' | 'csv'
  }
): Promise<string> => {
  const base = await getApiBase()
  const p = new URLSearchParams()
  if (params.monat) p.set('monat', params.monat)
  if (params.datum_von) p.set('datum_von', params.datum_von)
  if (params.datum_bis) p.set('datum_bis', params.datum_bis)
  if (params.kategorie_id) p.set('kategorie_id', String(params.kategorie_id))
  if (params.art) p.set('art', params.art)
  if (params.zahlungsart_typ) p.set('zahlungsart_typ', params.zahlungsart_typ)
  p.set('format', params.format)
  return `${base}/journal/export?${p.toString()}`
}

// --- Tagesabschluss ---
export type Tagesabschluss = {
  id: number
  datum: string
  uhrzeit: string
  anfangsbestand: string
  einnahmen_bar: string
  ausgaben_bar: string
  soll_endbestand: string
  ist_endbestand: string
  differenz: string
  differenz_begruendung: string | null
  differenz_buchungsart: string | null
  zaehlung_json: string | null
  kassenbewegungen_anzahl: number
  immutable: boolean
  signatur: string | null
  erstellt_am: string
}

export type TagesabschlussVorschau = {
  datum: string
  anfangsbestand: string
  einnahmen_bar: string
  ausgaben_bar: string
  soll_endbestand: string
  kassenbewegungen_anzahl: number
}

export const getTagesabschlussVorschau = (datum: string) =>
  request<TagesabschlussVorschau>(`/tagesabschluss/vorschau/${datum}`)
export const getTagesabschlussFehltGestern = () =>
  request<{ datum: string; fehlt: boolean }>('/tagesabschluss/fehlt-gestern')
export const getTagesabschluesse = () => request<Tagesabschluss[]>('/tagesabschluss')
export const pruefeTagesabschlussSignatur = (id: number) =>
  request<{ id: number; gueltig: boolean; gespeichert: string | null; berechnet: string }>(
    `/tagesabschluss/${id}/pruefen`,
  )
export const createTagesabschluss = (data: {
  datum: string
  ist_endbestand: string
  zaehlung_json?: string
  differenz_begruendung?: string
  differenz_buchungsart?: string
}) => request<Tagesabschluss>('/tagesabschluss', { method: 'POST', body: JSON.stringify(data) })

export async function downloadTagesabschlussPdf(params: {
  zeitraum?: 'monat' | 'jahr' | 'alle' | 'tag'
  wert?: string
}) {
  const { zeitraum = 'alle', wert } = params
  const searchParams = new URLSearchParams({ zeitraum })
  if (wert) searchParams.set('wert', wert)
  const base = await getBaseUrl()
  await openUrl(`${base}/tagesabschluss/export/pdf?${searchParams}`)
}

// --- Kunden ---
export type Kunde = {
  id?: number
  firmenname?: string
  vorname?: string
  nachname?: string
  strasse?: string
  hausnummer?: string
  plz?: string
  ort?: string
  land: string
  ust_idnr?: string
  email?: string
  telefon?: string
  ist_verein: boolean
  ist_gemeinnuetzig: boolean
  kundennummer?: string
  z_hd?: string
  notizen?: string
  zugferd_aktiv?: boolean
  skonto_prozent?: number | null
  skonto_tage?: number | null
  ust_idnr_validiert?: boolean
  aktiv?: boolean
}
export const getKunden = () => request<Kunde[]>('/kunden')
export const createKunde = (data: Omit<Kunde, 'id' | 'aktiv' | 'ust_idnr_validiert'>) =>
  request<Kunde>('/kunden', { method: 'POST', body: JSON.stringify(data) })
export const updateKunde = (id: number, data: Partial<Kunde>) =>
  request<Kunde>(`/kunden/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteKunde = (id: number) =>
  request<void>(`/kunden/${id}`, { method: 'DELETE' })

export type AnonymisierungResult = {
  anonymisierte_buchungen: number
  anonymisierte_rechnungen: number
  unveraenderlich_verblieben: number
  hinweis: string
}
export const anonymisiereKunde = (id: number) =>
  request<AnonymisierungResult>(`/kunden/${id}/anonymisieren`, { method: 'POST' })

export type KundeLieferadresse = {
  id?: number
  kunde_id?: number
  bezeichnung?: string
  z_hd?: string
  strasse?: string
  hausnummer?: string
  plz?: string
  ort?: string
  land: string
  ist_standard: boolean
}
export const getLieferadressen = (kundeId: number) =>
  request<KundeLieferadresse[]>(`/kunden/${kundeId}/lieferadressen`)
export const createLieferadresse = (kundeId: number, data: Omit<KundeLieferadresse, 'id' | 'kunde_id'>) =>
  request<KundeLieferadresse>(`/kunden/${kundeId}/lieferadressen`, { method: 'POST', body: JSON.stringify(data) })
export const updateLieferadresse = (kundeId: number, laId: number, data: Omit<KundeLieferadresse, 'id' | 'kunde_id'>) =>
  request<KundeLieferadresse>(`/kunden/${kundeId}/lieferadressen/${laId}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteLieferadresse = (kundeId: number, laId: number) =>
  request<void>(`/kunden/${kundeId}/lieferadressen/${laId}`, { method: 'DELETE' })

export async function dsgvoExportKunde(id: number) {
  const base = await getBaseUrl()
  await openUrl(`${base}/kunden/${id}/dsgvo-export`)
}
export async function dsgvoExportKundePdf(id: number) {
  const base = await getBaseUrl()
  await openUrl(`${base}/kunden/${id}/dsgvo-export-pdf`)
}

// --- Lieferanten ---
export type Lieferant = {
  id?: number
  firmenname: string
  vorname?: string
  nachname?: string
  strasse?: string
  hausnummer?: string
  plz?: string
  ort?: string
  land: string
  ust_idnr?: string
  email?: string
  telefon?: string
  lieferantennummer?: string
  z_hd?: string
  notizen?: string
  aktiv?: boolean
}
export const getLieferanten = () => request<Lieferant[]>('/lieferanten')
export const createLieferant = (data: Omit<Lieferant, 'id' | 'aktiv'>) =>
  request<Lieferant>('/lieferanten', { method: 'POST', body: JSON.stringify(data) })
export const updateLieferant = (id: number, data: Partial<Lieferant>) =>
  request<Lieferant>(`/lieferanten/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteLieferant = (id: number) =>
  request<void>(`/lieferanten/${id}`, { method: 'DELETE' })
export const anonymisiereLieferant = (id: number) =>
  request<AnonymisierungResult>(`/lieferanten/${id}/anonymisieren`, { method: 'POST' })
export async function dsgvoExportLieferant(id: number) {
  const base = await getBaseUrl()
  await openUrl(`${base}/lieferanten/${id}/dsgvo-export`)
}
export async function dsgvoExportLieferantPdf(id: number) {
  const base = await getBaseUrl()
  await openUrl(`${base}/lieferanten/${id}/dsgvo-export-pdf`)
}

// --- EKS ---
export type EksFeld = {
  tabelle: string
  code: string
  label: string
  negativ?: boolean
  auto: boolean
}

export type EksQuelle = {
  zeitraum_von: string
  zeitraum_bis: string
  anzahl_exporte: number
}

export type EksHalbjahr = {
  monate: string[]                                    // ['2025-01', '2025-02', ...]
  werte: Record<string, Record<string, string>>       // monat → code → betrag
  zeilensummen: Record<string, string>                // code → 6-Monats-Summe
  spaltensummen_a: Record<string, string>             // monat → Summe Tabelle A
  spaltensummen_b: Record<string, string>             // monat → Summe Tabelle B
  spaltensummen_c: Record<string, string>             // monat → Summe Tabelle C
  felder: EksFeld[]
  art: string
  quelle: EksQuelle | null
  bewilligungszeitraum_von: string
  bewilligungszeitraum_bis: string
}

export async function eksHalbjahr(start: string, art: string): Promise<EksHalbjahr> {
  return request<EksHalbjahr>(`/eks/halbjahr?start=${start}&art=${art}`)
}

export async function eksHalbjahresPdf(start: string, art: string): Promise<void> {
  const base = await getBaseUrl()
  await openUrl(`${base}/eks/halbjahr/pdf?start=${start}&art=${art}`)
}

// --- Export ---
export async function downloadGobdExport(jahr: number): Promise<string> {
  const base = await getBaseUrl()
  const res = await fetch(`${base}/export/gobd?jahr=${jahr}`)
  if (!res.ok) throw new Error('Export fehlgeschlagen')
  const blob = await res.blob()
  const filename = `gobd_export_${jahr}.zip`
  _triggerBlobDownload(blob, filename)
  return filename
}

// --- Backup ---
export async function downloadBackup(): Promise<string> {
  const base = await getBaseUrl()
  const res = await fetch(`${base}/backup/download`)
  if (!res.ok) throw new Error('Backup-Download fehlgeschlagen')
  const blob = await res.blob()
  const cd = res.headers.get('Content-Disposition') ?? ''
  const match = cd.match(/filename="?([^"]+)"?/)
  const filename = match?.[1] ?? 'rechnungsfee_backup.db'

  if (isTauri()) {
    const { save } = await import('@tauri-apps/plugin-dialog')
    const { invoke } = await import('@tauri-apps/api/core')
    const savePath = await save({
      defaultPath: filename,
      filters: [{ name: 'SQLite Datenbank', extensions: ['db'] }],
    })
    if (!savePath) return '' // Abgebrochen
    const data = Array.from(new Uint8Array(await blob.arrayBuffer()))
    await invoke('write_bytes_to_path', { path: savePath, data })
    return savePath.split(/[\\/]/).pop() ?? filename
  }

  _triggerBlobDownload(blob, filename)
  return filename
}

function _triggerBlobDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

/** Lädt eine Rechnungs-PDF als Datei herunter (kein Viewer).
 *  Für den Mail-Workflow: User speichert die PDF und hängt sie manuell an. */
export async function downloadPdfForMail(rechnungId: number): Promise<void> {
  const base = await getBaseUrl()
  const res = await fetch(`${base}/rechnungen/${rechnungId}/pdf?download=1`)
  if (!res.ok) throw new Error(`PDF-Download fehlgeschlagen: ${res.status}`)
  const blob = await res.blob()
  const cd = res.headers.get('Content-Disposition') ?? ''
  const match = cd.match(/filename[*]?=(?:UTF-8''|"?)([^";\r\n]+)/i)
  _triggerBlobDownload(blob, match?.[1]?.trim() ?? 'rechnung.pdf')
}

// --- Nummernkreise ---
export type Nummernkreis = {
  id: number
  bezeichnung: string
  typ: string
  format: string
  naechste_nr: number
  reset_jaehrlich: boolean
  letztes_jahr: number | null
  aktiv: boolean
  vorschau: string | null
}
export const getNummernkreise = () => request<Nummernkreis[]>('/nummernkreise')
export const updateNummernkreis = (id: number, data: Partial<Nummernkreis>) =>
  request<Nummernkreis>(`/nummernkreise/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const getNummernkreisVorschau = (id: number, format: string) =>
  request<{ vorschau: string }>(`/nummernkreise/vorschau/${id}?format=${encodeURIComponent(format)}`)

// --- Belege ---
export type Beleg = {
  id: number
  dateiname: string
  original_name: string
  mime_type: string | null
  dateigroesse: number | null
  sha256: string | null
  hochgeladen_am: string
  pdfa_verfuegbar: boolean
}

export async function uploadBeleg(rechnungId: number, datei: File): Promise<Beleg> {
  const base = await getBaseUrl()
  const form = new FormData()
  form.append('datei', datei)
  const res = await fetch(`${base}/rechnungen/${rechnungId}/beleg`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Beleg-Upload fehlgeschlagen')
  }
  return res.json()
}

export async function getBelegUrl(rechnungId: number): Promise<string> {
  const base = await getBaseUrl()
  return `${base}/rechnungen/${rechnungId}/beleg`
}

export async function getBelegPdfaUrl(rechnungId: number): Promise<string> {
  const base = await getBaseUrl()
  return `${base}/rechnungen/${rechnungId}/beleg?version=pdfa`
}

export const deleteBeleg = (rechnungId: number) =>
  request<void>(`/rechnungen/${rechnungId}/beleg`, { method: 'DELETE' })

export type AnalysePosition = {
  beschreibung: string
  menge: string
  einheit: string
  netto: string
  ust_satz: string
  artikel_nr?: string
}

export type AnalyseFelder = {
  externe_belegnr?: string
  datum?: string
  faellig_am?: string
  gesamt_netto?: string
  gesamt_ust?: string
  gesamt_brutto?: string
  ust_satz?: string
  lieferant_name?: string
  lieferant_ust_id?: string
  lieferant_email?: string
  lieferant_strasse?: string
  lieferant_plz?: string
  lieferant_ort?: string
  konfidenz?: Record<string, 'ok' | 'warnung' | 'fehlt'>
}

export type LieferantVorschlag = {
  id: number
  name: string
  score: number
}

export type AnalyseErgebnis = {
  format: 'zugferd' | 'xrechnung' | 'pdf' | 'unbekannt' | string
  felder: AnalyseFelder
  positionen: AnalysePosition[]
  warnungen: string[]
  positionen_modus?: 'netto' | 'brutto'
  temp_url?: string
  temp_path?: string
  lieferant_vorschlaege?: LieferantVorschlag[]
}

export async function analysiereRechnung(datei: File): Promise<AnalyseErgebnis> {
  const base = await getBaseUrl()
  const form = new FormData()
  form.append('datei', datei)
  const res = await fetch(`${base}/rechnungen/analysieren`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Analyse fehlgeschlagen')
  }
  return res.json()
}

export async function analysiereRechnungPfad(pfad: string): Promise<AnalyseErgebnis> {
  const base = await getBaseUrl()
  const res = await fetch(`${base}/rechnungen/analysieren-pfad`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pfad }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Analyse fehlgeschlagen')
  }
  return res.json()
}

// --- Rechnungen ---
export type Rechnungsposition = {
  id: number
  artikel_id: number | null
  artikel_typ: string | null
  kategorie_id: number | null
  position_nr: number
  beschreibung: string
  menge: string
  einheit: string
  netto: string
  ust_satz: string
  ust_betrag: string
  brutto: string
  differenzbesteuerung: boolean
}

export type RechnungspositionCreate = {
  beschreibung: string
  menge?: string
  einheit?: string
  netto: string
  ust_satz: string
  artikel_id?: number
  kategorie_id?: number
  differenzbesteuerung?: boolean
}

export type ZahlungKompakt = {
  id: number
  belegnr: string
  datum: string
  brutto_betrag: string
  art: 'Einnahme' | 'Ausgabe'
  zahlungsart: string
}

export type Rechnung = {
  id: number
  typ: 'eingang' | 'ausgang'
  rechnungsnummer: string | null
  datum: string
  leistung_von: string | null
  leistung_bis: string | null
  faellig_am: string | null
  kunde_id: number | null
  kunde_name: string | null
  kunde_email: string | null
  kunde_zugferd_aktiv: boolean
  lieferant_id: number | null
  lieferant_name: string | null
  lieferant_email: string | null
  partner_freitext: string | null
  kategorie_id: number | null
  netto_gesamt: string
  ust_gesamt: string
  brutto_gesamt: string
  bezahlt: boolean
  bezahlt_betrag: string
  zahlungsstatus: 'offen' | 'teilweise' | 'bezahlt' | 'uneinbringlich'
  zahlungsdatum: string | null
  notizen: string | null
  externe_belegnr: string | null
  positionen: Rechnungsposition[]
  zahlungen: ZahlungKompakt[]
  beleg: Beleg | null
  skonto_prozent: number | null
  skonto_tage: number | null
  ist_entwurf: boolean
  ausgegeben: boolean
  immutable: boolean
  storniert: boolean
  storno_grund: string | null
  dokument_typ: string
  gutschrift_zu_rechnung_id: number | null
  gutschrift_zu_rechnung_nr: string | null
  lieferschein_zu_rechnung_id: number | null
  lieferschein_rechnung_ist_entwurf: boolean | null
  lieferschein_zu_rechnung_nr: string | null
  hat_lieferschein: boolean
  lieferschein_anzahl: number
  linked_lieferschein_id: number | null
  linked_lieferschein_nr: string | null
  lieferadresse_id: number | null
  lieferadresse_text: string | null
  angebot_status: string | null
  gueltig_bis: string | null
  dokumentenpaket_id: number | null
  rechnung_zu_angebot_id: number | null
  rechnung_zu_angebot_nr: string | null
  lieferschein_zu_angebot_id: number | null
  lieferschein_zu_angebot_nr: string | null
  proforma_zu_angebot_id: number | null
  proforma_zu_angebot_nr: string | null
  rechnung_zu_proforma_id: number | null
  rechnung_zu_proforma_nr: string | null
  angebot_zu_proforma_id: number | null
  angebot_zu_proforma_nr: string | null
  // Aufträge
  auftrag_status: string | null
  auftrag_zu_angebot_id: number | null
  auftrag_zu_angebot_nr: string | null
  rechnung_zu_auftrag_id: number | null
  rechnung_zu_auftrag_nr: string | null
  lieferschein_zu_auftrag_id: number | null
  lieferschein_zu_auftrag_nr: string | null
  proforma_zu_auftrag_id: number | null
  proforma_zu_auftrag_nr: string | null
  angebot_zu_auftrag_id: number | null
  angebot_zu_auftrag_nr: string | null
  herkunft_angebot_id: number | null
  herkunft_angebot_nr: string | null
  herkunft_auftrag_id: number | null
  herkunft_auftrag_nr: string | null
  herkunft_proforma_id: number | null
  herkunft_proforma_nr: string | null
  erstellt_am: string
  aktualisiert_am: string
}

export type RechnungCreate = {
  typ: 'eingang' | 'ausgang'
  rechnungsnummer?: string
  datum: string
  leistung_von?: string
  leistung_bis?: string
  faellig_am?: string
  kunde_id?: number
  lieferant_id?: number
  partner_freitext?: string
  kategorie_id?: number
  notizen?: string
  externe_belegnr?: string
  ist_entwurf?: boolean
  skonto_prozent?: number | null
  skonto_tage?: number | null
  dokument_typ?: 'Rechnung' | 'Gutschrift' | 'Lieferschein' | 'Angebot' | 'Proforma' | 'Auftrag'
  gueltig_bis?: string
  dokumentenpaket_id?: number
  lieferadresse_id?: number | null
  positionen: RechnungspositionCreate[]
  netto_gesamt_override?: string
  ust_gesamt_override?: string
  brutto_gesamt_override?: string
}

export type SammelrechnungCreate = {
  lieferschein_ids: number[]
  datum: string
  leistung_von?: string
  leistung_bis?: string
  faellig_am?: string
  notizen?: string
}

export type RechnungUpdate = Partial<RechnungCreate>

export type ZahlungSplitPosition = {
  kategorie_id: number
  betrag: string
  beschreibung: string
}

export type BarZahlungCreate = {
  betrag?: string
  datum: string
  zahlungsart: 'Bar' | 'Karte' | 'PayPal' | 'Bank' | 'Keine'
  beschreibung?: string
  kategorie_id?: number
  split?: ZahlungSplitPosition[]
  skonto_betrag?: string
}

export type BarZahlungResult = {
  journaleintrag_id: number
  journaleintrag_belegnr: string
  rechnung: Rechnung
}

export const getRechnungen = (filter?: {
  typ?: 'eingang' | 'ausgang'
  zahlungsstatus?: string
  monat?: string
  datum_von?: string
  datum_bis?: string
  kunde_id?: number
  lieferant_id?: number
  dokument_typ?: string
}) => request<Rechnung[]>(`/rechnungen${toQuery(filter ?? {})}`)

export const getLieferscheine = (filter?: { kunde_id?: number }) =>
  request<Rechnung[]>(`/rechnungen${toQuery({ dokument_typ: 'Lieferschein', ...filter })}`)

export const getAngebote = () =>
  request<Rechnung[]>('/rechnungen' + toQuery({ dokument_typ: 'Angebot' }))

export const rechnungAusAngebot = (angebotId: number) =>
  request<Rechnung>(`/rechnungen/${angebotId}/rechnung-aus-angebot`, { method: 'POST' })

export const lieferscheinAusAngebot = (angebotId: number) =>
  request<Rechnung>(`/rechnungen/${angebotId}/lieferschein-aus-angebot`, { method: 'POST' })

export const angebotStatusSetzen = (angebotId: number, status: string) =>
  request<Rechnung>(`/rechnungen/${angebotId}/angebot-status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })

// --- Aufträge ---
export const getAuftraege = () =>
  request<Rechnung[]>('/rechnungen/auftraege')

export const auftragErstellen = (data: RechnungCreate) =>
  request<Rechnung>('/rechnungen/auftraege', { method: 'POST', body: JSON.stringify(data) })

export const auftragAusAngebot = (angebotId: number) =>
  request<Rechnung>(`/rechnungen/${angebotId}/auftrag-aus-angebot`, { method: 'POST' })

export const rechnungAusAuftrag = (auftragId: number) =>
  request<Rechnung>(`/rechnungen/${auftragId}/rechnung-aus-auftrag`, { method: 'POST' })

export const lieferscheinAusAuftrag = (auftragId: number) =>
  request<Rechnung>(`/rechnungen/${auftragId}/lieferschein-aus-auftrag`, { method: 'POST' })

export const proformaAusAuftrag = (auftragId: number) =>
  request<Rechnung>(`/rechnungen/${auftragId}/proforma-aus-auftrag`, { method: 'POST' })

export const auftragStatusSetzen = (auftragId: number, status: string) =>
  request<Rechnung>(`/rechnungen/${auftragId}/auftrag-status`, {
    method: 'POST',
    body: JSON.stringify({ status }),
  })

export const getProformas = () =>
  request<Rechnung[]>('/rechnungen' + toQuery({ dokument_typ: 'Proforma' }))

export const proformaAusAngebot = (angebotId: number) =>
  request<Rechnung>(`/rechnungen/${angebotId}/proforma-aus-angebot`, { method: 'POST' })

export const rechnungAusProforma = (proformaId: number, zahlung: { zahlungsart: string; bezahlt_am: string }) =>
  request<Rechnung>(`/rechnungen/${proformaId}/rechnung-aus-proforma`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(zahlung),
  })

export const rechnungAusLieferschein = (lsId: number) =>
  request<Rechnung>(`/rechnungen/${lsId}/rechnung-erstellen`, { method: 'POST' })

export const sammelrechnungErstellen = (data: SammelrechnungCreate) =>
  request<Rechnung>('/rechnungen/sammelrechnung', { method: 'POST', body: JSON.stringify(data) })

export const lieferscheinAusRechnung = (rechnungId: number) =>
  request<Rechnung>(`/rechnungen/${rechnungId}/lieferschein-erstellen`, { method: 'POST' })

export const getOffeneRechnungen = () => request<Rechnung[]>('/rechnungen/offene')
export const getFaelligeRechnungen = (tage = 7) => request<Rechnung[]>(`/rechnungen/faellig?tage=${tage}`)

// ---------------------------------------------------------------------------
// Dokumentenpakete
// ---------------------------------------------------------------------------

export interface PaketDatei {
  id: number
  beleg_id: number
  bezeichnung: string | null
  sort_order: number
  original_name: string
  mime_type: string | null
  dateigroesse: number | null
}

export interface DokumentenPaket {
  id: number
  name: string
  beschreibung: string | null
  aktiv: boolean
  erstellt_am: string
  dateien: PaketDatei[]
}

export const getDokumentenPakete = () =>
  request<DokumentenPaket[]>('/dokumentenpakete')

export const getDokumentenPaket = (id: number) =>
  request<DokumentenPaket>(`/dokumentenpakete/${id}`)

export const createDokumentenPaket = (data: { name: string; beschreibung?: string }) =>
  request<DokumentenPaket>('/dokumentenpakete', { method: 'POST', body: JSON.stringify(data) })

export const updateDokumentenPaket = (id: number, data: { name?: string; beschreibung?: string; aktiv?: boolean }) =>
  request<DokumentenPaket>(`/dokumentenpakete/${id}`, { method: 'PUT', body: JSON.stringify(data) })

export const deleteDokumentenPaket = (id: number) =>
  request<void>(`/dokumentenpakete/${id}`, { method: 'DELETE' })

export const uploadPaketDatei = (paketId: number, datei: File, bezeichnung?: string) => {
  const fd = new FormData()
  fd.append('datei', datei)
  if (bezeichnung) fd.append('bezeichnung', bezeichnung)
  return request<DokumentenPaket>(`/dokumentenpakete/${paketId}/dateien`, { method: 'POST', body: fd })
}

export const updatePaketDatei = (paketId: number, eintragId: number, data: { bezeichnung?: string; sort_order?: number }) =>
  request<DokumentenPaket>(`/dokumentenpakete/${paketId}/dateien/${eintragId}`, { method: 'PUT', body: JSON.stringify(data) })

export const deletePaketDatei = (paketId: number, eintragId: number) =>
  request<DokumentenPaket>(`/dokumentenpakete/${paketId}/dateien/${eintragId}`, { method: 'DELETE' })

export const getPaketDateiUrl = async (paketId: number, eintragId: number): Promise<string> => {
  const base = await getApiBase()
  return `${base}/dokumentenpakete/${paketId}/dateien/${eintragId}/download`
}

export const getRechnung = (id: number) => request<Rechnung>(`/rechnungen/${id}`)

export const createRechnung = (data: RechnungCreate) =>
  request<Rechnung>('/rechnungen', { method: 'POST', body: JSON.stringify(data) })

export const updateRechnung = (id: number, data: RechnungUpdate) =>
  request<Rechnung>(`/rechnungen/${id}`, { method: 'PUT', body: JSON.stringify(data) })

export const deleteRechnung = (id: number) =>
  request<void>(`/rechnungen/${id}`, { method: 'DELETE' })

export const barZahlungErstellen = (id: number, data: BarZahlungCreate) =>
  request<BarZahlungResult>(`/rechnungen/${id}/zahlung-bar`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const getRechnungZahlungen = (id: number) =>
  request<ZahlungKompakt[]>(`/rechnungen/${id}/zahlungen`)

export const stornoRechnung = (id: number, grund: string) =>
  request<Rechnung>(`/rechnungen/${id}/storno`, { method: 'POST', body: JSON.stringify({ grund }) })

export const forderungsausbuchenRechnung = (id: number) =>
  request<Rechnung>(`/rechnungen/${id}/forderungsausfall`, { method: 'POST' })

export const createGutschrift = (id: number) =>
  request<Rechnung>(`/rechnungen/${id}/gutschrift`, { method: 'POST' })

export const finalisiereRechnung = (id: number) =>
  request<Rechnung>(`/rechnungen/${id}/finalisieren`, { method: 'POST' })

export const markiereRechnungAusgegeben = (id: number) =>
  request<Rechnung>(`/rechnungen/${id}/ausgegeben`, { method: 'POST' })

export async function getRechnungPdf(id: number): Promise<Blob> {
  const base = await getBaseUrl()
  const res = await fetch(`${base}/rechnungen/${id}/pdf`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'PDF-Export fehlgeschlagen')
  }
  return res.blob()
}

export async function getRechnungZugferd(id: number): Promise<Blob> {
  const base = await getBaseUrl()
  const res = await fetch(`${base}/rechnungen/${id}/zugferd`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'ZUGFeRD-Export fehlgeschlagen')
  }
  return res.blob()
}

// --- Artikelstamm ---
export type ArtikelTyp = 'artikel' | 'dienstleistung' | 'fremdleistung'

export type ArtikelGruppe = {
  id: number
  typ: ArtikelTyp
  name: string
  aktiv: boolean
  artikel_anzahl: number
}

export type Artikel = {
  id: number
  artikelnummer: string
  typ: ArtikelTyp
  bezeichnung: string
  einheit: string
  steuersatz: string
  vk_brutto: string
  vk_netto: string
  ek_netto: string | null
  ek_brutto: string | null
  lieferant_id: number | null
  lieferant: { id: number; firmenname: string; lieferantennummer: string | null } | null
  lieferanten_artikelnr: string | null
  hersteller: string | null
  artikelcode: string | null
  beschreibung: string | null
  gruppe_id: number | null
  gruppe_obj: { id: number; name: string } | null
  differenzbesteuerung: boolean
  aktiv: boolean
  erstellt_am: string
  aktualisiert_am: string
}

export type ArtikelSuche = {
  id: number
  artikelnummer: string
  typ: ArtikelTyp
  bezeichnung: string
  einheit: string
  steuersatz: string
  vk_brutto: string
  vk_netto: string
  ek_brutto: string | null
  differenzbesteuerung: boolean
  lieferant_name: string | null
}

export type ArtikelRechnungKurz = {
  rechnung_id: number
  rechnungsnummer: string | null
  datum: string
  menge: string
  einheit: string
  vk_brutto: string
  kunde_id: number | null
  kunde_name: string | null
}

export type ArtikelCreate = {
  typ: ArtikelTyp
  bezeichnung: string
  einheit: string
  steuersatz: string
  vk_brutto: string
  ek_netto?: string
  lieferant_id?: number
  lieferanten_artikelnr?: string
  hersteller?: string
  artikelcode?: string
  beschreibung?: string
  gruppe_id?: number
  differenzbesteuerung?: boolean
}

export type ArtikelUpdate = Partial<ArtikelCreate> & { aktiv?: boolean }

export const getArtikel = (params?: { aktiv?: boolean; typ?: string }) => {
  const q: Record<string, string | number | undefined> = {}
  if (params?.aktiv !== undefined) q.aktiv = String(params.aktiv)
  if (params?.typ !== undefined) q.typ = params.typ
  return request<Artikel[]>(`/artikel${toQuery(q)}`)
}
export const sucheArtikel = (q: string) =>
  request<ArtikelSuche[]>(`/artikel/suche?q=${encodeURIComponent(q)}`)
export const createArtikel = (data: ArtikelCreate) =>
  request<Artikel>('/artikel', { method: 'POST', body: JSON.stringify(data) })
export const updateArtikel = (id: number, data: ArtikelUpdate) =>
  request<Artikel>(`/artikel/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const getArtikelRechnungen = (id: number) =>
  request<ArtikelRechnungKurz[]>(`/artikel/${id}/rechnungen`)

export const getArtikelGruppen = (typ?: ArtikelTyp, nurAktive = false) =>
  request<ArtikelGruppe[]>(`/artikel-gruppen${toQuery({ typ, nur_aktive: nurAktive ? 'true' : undefined })}`)
export const createArtikelGruppe = (data: { typ: ArtikelTyp; name: string }) =>
  request<ArtikelGruppe>('/artikel-gruppen', { method: 'POST', body: JSON.stringify(data) })
export const updateArtikelGruppe = (id: number, name: string) =>
  request<ArtikelGruppe>(`/artikel-gruppen/${id}`, { method: 'PUT', body: JSON.stringify({ name }) })
export const toggleArtikelGruppeAktiv = (id: number) =>
  request<ArtikelGruppe>(`/artikel-gruppen/${id}/aktiv`, { method: 'PATCH' })
export const deleteArtikelGruppe = (id: number) =>
  request<void>(`/artikel-gruppen/${id}`, { method: 'DELETE' })

// --- USt-Sätze ---
export type UstSatz = {
  id: number
  satz: string
  bezeichnung: string | null
  ist_aktiv: boolean
  ist_default: boolean
  ist_standard: boolean
}
export const getUstSaetze = () => request<UstSatz[]>('/ust-saetze')
export const createUstSatz = (data: { satz: string; bezeichnung?: string }) =>
  request<UstSatz>('/ust-saetze', { method: 'POST', body: JSON.stringify(data) })
export const updateUstSatz = (id: number, data: { bezeichnung?: string; ist_aktiv?: boolean; ist_default?: boolean }) =>
  request<UstSatz>(`/ust-saetze/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteUstSatz = (id: number) =>
  request<void>(`/ust-saetze/${id}`, { method: 'DELETE' })

// --- PDF-Vorlagen ---
export type PdfVorlage = {
  id: number
  name: string
  beschreibung: string
}
export const getPdfVorlagen = () => request<PdfVorlage[]>('/pdf-vorlagen')

export async function openDemoPdf(vorlage: number): Promise<void> {
  const base = await getApiBase()
  await openUrl(`${base}/pdf-vorlagen/demo?vorlage=${vorlage}`)
}

// --- EKS-Einstellungen ---
export type EksEinstellungen = {
  id?: number
  taetigkeitsart_text?: string | null
  taetigkeitsbeginn?: string | null
  taetigkeitsende?: string | null
  wohnung_gewerblich: boolean
  gewerbliche_raeume?: string | null
  gewerbliche_flaeche?: string | null
  produkte_kostenfrei: boolean
  personal_beschaeftigt: boolean
  anzahl_beschaeftigte?: string | null
  weiteres_personal: boolean
  anzahl_weiteres_personal?: string | null
  personal_ab?: string | null
  umsatzsteuerpflichtig: boolean
  zuschuss_erhalten: boolean
  zuschuss_beantragt: boolean
  darlehen: boolean
  darlehen_hoehe?: string | null
  darlehen_eingang?: string | null
  darlehen_rueckzahlung_ab?: string | null
  darlehen_tilgung?: string | null
  darlehen_ausgaben_art?: string | null
  darlehen_ausgaben_hoehe?: string | null
  kind_ausserhalb: boolean
  unterhalt: boolean
  fahrten_betriebsstaette: boolean
  km_einfach?: string | null
  arbeitstage_pro_woche?: string | null
  mehraufwand_verpflegung: boolean
  arbeitstage_verpflegung?: string | null
}

export const getEksEinstellungen = () =>
  request<EksEinstellungen>('/eks/einstellungen')

export const saveEksEinstellungen = (data: EksEinstellungen) =>
  request<EksEinstellungen>('/eks/einstellungen', {
    method: 'PUT',
    body: JSON.stringify(data),
  })


// ---------------------------------------------------------------------------
// System – Tesseract OCR
// ---------------------------------------------------------------------------

export type TesseractVoraussetzungen = {
  os: 'Windows' | 'Darwin' | 'Linux'
  winget: boolean
  brew: boolean
  apt: boolean
  dnf: boolean
  pacman: boolean
  pkexec: boolean
}

export const pruefeTesseract = () =>
  request<{ installiert: boolean }>('/system/tesseract')

export const tesseractVoraussetzungen = () =>
  request<TesseractVoraussetzungen>('/system/tesseract/voraussetzungen')

export const installiereTesseract = () =>
  request<{ erfolg: boolean; fehler?: string }>('/system/tesseract/installieren', {
    method: 'POST',
  })

// ---------------------------------------------------------------------------
// UStVA
// ---------------------------------------------------------------------------

export type UStVAErgebnis = {
  zeitraum: string
  zeitraum_typ: string
  von: string
  bis: string
  // A – Ausgangsumsätze
  kz_81: string; kz_83: string
  kz_86: string; kz_88: string
  // B – steuerfreie Umsätze (manuell)
  kz_41: string; kz_87: string
  // C – ig. Erwerb
  kz_89: string; kz_93: string
  // D – §13b
  kz_46: string; kz_47: string
  kz_84: string; kz_85: string
  // F – Vorsteuer
  kz_66: string; kz_61: string; kz_67: string
  zahllast: string
  ist_kleinunternehmer: boolean
  hinweis?: string | null
}

export type UStVAHistorieEintrag = {
  zeitraum: string
  zeitraum_typ: string
  zahllast: number
  erstellt_am: string
}

export const berechneUStVA = (zeitraum: string) =>
  request<UStVAErgebnis>(`/ustva/berechnen?zeitraum=${encodeURIComponent(zeitraum)}`)

export const speichereUStVA = (data: Omit<UStVAErgebnis, 'zeitraum_typ' | 'von' | 'bis' | 'ist_kleinunternehmer' | 'hinweis'>) =>
  request<{ ok: boolean; zeitraum: string }>('/ustva/speichern', { method: 'POST', body: JSON.stringify(data) })

export const getUStVAHistorie = () =>
  request<UStVAHistorieEintrag[]>('/ustva/historie')

export const getUStVAPdfUrl = async (zeitraum: string): Promise<string> => {
  const base = await getBaseUrl()
  return `${base}/ustva/pdf?zeitraum=${encodeURIComponent(zeitraum)}`
}

// --- Zusammenfassende Meldung (ZM) ---

export type ZMPosition = {
  ust_idnr: string
  land: string
  kennzeichen: string
  betrag: string
}

export type ZMErgebnis = {
  zeitraum: string
  zeitraum_label: string
  von: string
  bis: string
  deadline: string
  positionen: ZMPosition[]
  gesamt: string
  ueber_50k: boolean
}

export type ZMPruefung = {
  faellig: boolean
  hat_ig_eintraege: boolean
  zeitraum: string
  zeitraum_label: string
  deadline: string
  grund: string
}

export const pruefZM = () =>
  request<ZMPruefung>('/zm/pruefen')

export const berechneZM = (zeitraum: string) =>
  request<ZMErgebnis>(`/zm/berechnen?zeitraum=${encodeURIComponent(zeitraum)}`)

// --- EÜR ---

export type EUERZeile = {
  zeile: number
  bezeichnung: string
  abschnitt: string
  betrag: string
}

export type EUERErgebnis = {
  jahr: number
  zeilen: EUERZeile[]
  summe_einnahmen: string
  summe_ausgaben: string
  gewinn_verlust: string
  anlage_zugaenge: string
  ist_kleinunternehmer: boolean
}

export const berechneEUER = (jahr: number) =>
  request<EUERErgebnis>(`/euer/berechnen?jahr=${jahr}`)

export const getEUERPdfUrl = async (jahr: number): Promise<string> => {
  const base = await getBaseUrl()
  return `${base}/euer/pdf?jahr=${jahr}`
}

export type EUERKatSumme = {
  name: string
  betrag: string
}

export type EUERZeileDetail = {
  zeile: number
  bezeichnung: string
  abschnitt: string
  betrag_gesamt: string
  kategorien: EUERKatSumme[]
}

export type EUERDetailErgebnis = {
  jahr: number
  zeilen: EUERZeileDetail[]
}

export const berechneEUERDetail = (jahr: number) =>
  request<EUERDetailErgebnis>(`/euer/kategorien?jahr=${jahr}`)


// ---------------------------------------------------------------------------
// Mail – SMTP-Versand
// ---------------------------------------------------------------------------

export type MailSendenRequest = {
  an: string
  cc?: string
  betreff: string
  text: string
  rechnung_id?: number
  dokumentenpaket_id?: number
}

export const sendeMailMitAnhang = (data: MailSendenRequest) =>
  request<{ ok: boolean }>('/mail/senden', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const sendeTestMail = (an: string) =>
  request<{ ok: boolean }>('/mail/test', {
    method: 'POST',
    body: JSON.stringify({ an }),
  })

// ---------------------------------------------------------------------------
// Wiederkehrende Ausgangsrechnungen
// ---------------------------------------------------------------------------

export type VorlagePosition = {
  beschreibung: string
  menge: string
  einheit: string
  netto: string
  ust_satz: string
  artikel_id?: number | null
  kategorie_id?: number | null
}

export type Preisaenderung = {
  beschreibung: string
  artikel_id: number
  preis_vorlage: string
  preis_aktuell: string
}

export type EntwurfErgebnis = {
  vorlage_id: number
  vorlage_bezeichnung: string
  rechnung_id: number
  rechnungsnummer: string
  preisaenderungen: Preisaenderung[]
}

export type Rechnungsvorlage = {
  id: number
  bezeichnung: string
  intervall: 'monatlich' | 'quartalsweise' | 'jaehrlich'
  naechstes_datum: string
  aktiv: boolean
  beendet: boolean
  kunde_id: number | null
  kunde_name: string | null
  zahlungsziel_tage: number | null
  notizen: string | null
  positionen: VorlagePosition[]
  letzte_erstellung: string | null
  erstellte_rechnungen: number
  erstellt_am: string
  auftrag_id: number | null
  auftrag_nr: string | null
  beleg_id: number | null
  beleg_name: string | null
}

export type VorlageCreate = Omit<Rechnungsvorlage, 'id' | 'kunde_name' | 'auftrag_nr' | 'beleg_id' | 'beleg_name' | 'letzte_erstellung' | 'erstellte_rechnungen' | 'erstellt_am' | 'beendet'>
export type VorlageUpdate = Partial<VorlageCreate>

export const getVorlagen = () => request<Rechnungsvorlage[]>('/wiederkehrend')
export const createVorlage = (data: VorlageCreate) =>
  request<Rechnungsvorlage>('/wiederkehrend', { method: 'POST', body: JSON.stringify(data) })
export const updateVorlage = (id: number, data: VorlageUpdate) =>
  request<Rechnungsvorlage>(`/wiederkehrend/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteVorlage = (id: number) =>
  request<void>(`/wiederkehrend/${id}`, { method: 'DELETE' })
export const pruefenWiederkehrend = () =>
  request<EntwurfErgebnis[]>('/wiederkehrend/pruefen', { method: 'POST' })
export const entwurfJetzt = (id: number) =>
  request<EntwurfErgebnis>(`/wiederkehrend/${id}/jetzt`, { method: 'POST' })
export const preiseSynchronisieren = (id: number) =>
  request<Rechnungsvorlage>(`/wiederkehrend/${id}/preise-sync`, { method: 'POST' })
export type VorlageRechnungKompakt = {
  id: number
  rechnungsnummer: string | null
  datum: string
  brutto_gesamt: string
  zahlungsstatus: string | null
  ist_entwurf: boolean
  kunde_name: string | null
}

export const getVorlageRechnungen = (id: number) =>
  request<VorlageRechnungKompakt[]>(`/wiederkehrend/${id}/rechnungen`)

export const uploadVertragVorlage = (id: number, datei: File) => {
  const form = new FormData()
  form.append('datei', datei)
  return request<Rechnungsvorlage>(`/wiederkehrend/${id}/vertrag`, { method: 'POST', body: form })
}
export const deleteVertragVorlage = (id: number) =>
  request<Rechnungsvorlage>(`/wiederkehrend/${id}/vertrag`, { method: 'DELETE' })
export const beendenVorlage = (id: number) =>
  request<Rechnungsvorlage>(`/wiederkehrend/${id}/beenden`, { method: 'POST' })

// ---------------------------------------------------------------------------
// Buchungsvorlagen (Wiederkehrende Buchungen)
// ---------------------------------------------------------------------------

export type Buchungsvorlage = {
  id: number
  bezeichnung: string
  lieferant_id: number | null
  lieferant_name: string | null
  kategorie_id: number | null
  kategorie_name: string | null
  konto_id: number | null
  konto_name: string | null
  betrag: string
  ist_brutto: boolean
  ust_satz: string
  intervall: 'monatlich' | 'quartalsweise' | 'jaehrlich'
  naechstes_datum: string
  aktiv: boolean
  modus: 'direkt' | 'beleg'
  notizen: string | null
  beleg_id: number | null
  beleg_name: string | null
  letzte_buchung: string | null
  erstellte_buchungen: number
  erstellt_am: string
}

export type BuchungsvorlageCreate = Omit<Buchungsvorlage,
  'id' | 'lieferant_name' | 'kategorie_name' | 'konto_name' |
  'beleg_id' | 'beleg_name' | 'letzte_buchung' | 'erstellte_buchungen' | 'erstellt_am'>

export const getBuchungsvorlagen = () =>
  request<Buchungsvorlage[]>('/buchungsvorlagen')
export const getBuchungsvorlage = (id: number) =>
  request<Buchungsvorlage>(`/buchungsvorlagen/${id}`)
export const getFaelligeBuchungsvorlagen = () =>
  request<Buchungsvorlage[]>('/buchungsvorlagen/faellige')
export const createBuchungsvorlage = (data: BuchungsvorlageCreate) =>
  request<Buchungsvorlage>('/buchungsvorlagen', { method: 'POST', body: JSON.stringify(data) })
export const updateBuchungsvorlage = (id: number, data: Partial<BuchungsvorlageCreate>) =>
  request<Buchungsvorlage>(`/buchungsvorlagen/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteBuchungsvorlage = (id: number) =>
  request<void>(`/buchungsvorlagen/${id}`, { method: 'DELETE' })
export const buchungAusfuehren = (id: number) =>
  request<unknown>(`/buchungsvorlagen/${id}/buchen`, { method: 'POST' })
export const uploadBuchungsvorlageBeleg = (id: number, datei: File) => {
  const form = new FormData()
  form.append('datei', datei)
  return request<{ id: number; original_name: string }>(`/buchungsvorlagen/${id}/beleg`, { method: 'POST', body: form })
}
export const deleteBuchungsvorlageBeleg = (id: number) =>
  request<void>(`/buchungsvorlagen/${id}/beleg`, { method: 'DELETE' })
export const erledigtVorlage = (id: number) =>
  request<unknown>(`/buchungsvorlagen/${id}/erledigt`, { method: 'POST' })

