import { invoke } from '@tauri-apps/api/core'

// --- API-Basis-URL ---
// Im Tauri-Produktionsmodus: Backend-Port per IPC-Command holen.
// Im Vite-Dev-Modus: Vite-Proxy leitet /api → http://localhost:8001 weiter.

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

/** Wartet bis das Backend antwortet (max. 50 × 200 ms = 10 s). */
async function waitForBackend(baseUrl: string): Promise<void> {
  for (let i = 0; i < 50; i++) {
    try {
      const res = await fetch(`${baseUrl}/setup/status`)
      if (res.ok) return
    } catch {
      // Backend noch nicht bereit
    }
    await new Promise((r) => setTimeout(r, 200))
  }
  console.warn('[RechnungsFee] Backend nach 10 s nicht erreichbar')
}

// Im Tauri-Modus einmalig warten, damit das UI erst lädt wenn das Backend ready ist
if (isTauri() && !import.meta.env.DEV) {
  getBaseUrl().then((url) => waitForBackend(url))
}

// --- HTTP-Hilfsfunktion ---

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const base = await getBaseUrl()
  const res = await fetch(`${base}${path}`, {
    headers: { 'Content-Type': 'application/json' },
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

/** Öffnet eine URL in Tauri per Shell-Plugin (Systembrowser), im Browser per window.open. */
export async function openUrl(url: string) {
  if (isTauri()) {
    try { await invoke('open_url', { url }) } catch { /* ignorieren */ }
  } else {
    window.open(url, '_blank')
  }
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
  finanzamt?: string
  ist_kleinunternehmer: boolean
  bezieht_transferleistungen: boolean
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
  mail_signatur?: string | null
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
  bank: string
  iban: string
  bic?: string
  kontotyp: 'geschaeftlich' | 'mischkonto' | 'privat'
  ist_standard: boolean
  aktiv?: boolean
}
export const getKonten = () => request<Konto[]>('/konten')
export const createKonto = (data: Omit<Konto, 'id' | 'aktiv'>) =>
  request<Konto>('/konten', { method: 'POST', body: JSON.stringify(data) })

// --- Kategorien ---
export type Kategorie = {
  id: number
  name: string
  kontenart: string
  vorsteuer_prozent: string
  ust_satz_standard: number
  ist_system: boolean
}
export const getKategorien = () => request<Kategorie[]>('/kategorien')

// --- Kassenbuch ---
export type KassenbuchEintrag = {
  id: number
  datum: string
  belegnr: string
  beschreibung: string
  kategorie_id: number | null
  kategorie_kontenart: string | null
  kunde_id: number | null
  kunde_name: string | null
  kunde_email: string | null
  zahlungsart: 'Bar' | 'Karte' | 'Bank' | 'PayPal'
  art: 'Einnahme' | 'Ausgabe'
  netto_betrag: string
  ust_satz: string
  ust_betrag: string
  brutto_betrag: string
  vorsteuerabzug: boolean
  steuerbefreiung_grund: string | null
  externe_belegnr?: string
  rechnung_id?: number | null
  immutable: boolean
  erstellt_am: string
}

export type KassenbuchEintragCreate = {
  datum: string
  beschreibung: string
  kategorie_id?: number
  kunde_id?: number
  zahlungsart: 'Bar' | 'Karte' | 'Bank' | 'PayPal'
  art: 'Einnahme' | 'Ausgabe'
  brutto_betrag: string
  ust_satz: string
  vorsteuerabzug?: boolean
  externe_belegnr?: string
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

export const getKassenbuch = (filter?: {
  monat?: string
  datum_von?: string
  datum_bis?: string
  kategorie_id?: number
  art?: string
}) => request<KassenbuchEintrag[]>(`/kassenbuch${toQuery(filter ?? {})}`)
export const createKassenbuchEintrag = (data: KassenbuchEintragCreate) =>
  request<KassenbuchEintrag>('/kassenbuch', { method: 'POST', body: JSON.stringify(data) })
export const getKassenbuchEintrag = (id: number) =>
  request<KassenbuchEintrag>(`/kassenbuch/${id}`)
export const stornoKassenbuchEintrag = (id: number, grund: string) =>
  request<KassenbuchEintrag>(`/kassenbuch/${id}/storno`, {
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
  zahlungsart: 'Bar' | 'Karte' | 'Bank' | 'PayPal'
  externe_belegnr?: string
  kunde_id?: number
  positionen: SplitPosition[]
}

export const createSplitBuchung = (data: SplitBuchungCreate) =>
  request<KassenbuchEintrag[]>('/kassenbuch/split', {
    method: 'POST',
    body: JSON.stringify(data),
  })
export const getMonatsUebersicht = (monat: string) =>
  request<MonatsUebersicht>(`/kassenbuch/statistik/monat?monat=${encodeURIComponent(monat)}`)
export const getNaechsteBelegnr = (datum?: string) =>
  request<{ belegnr: string }>(`/kassenbuch/naechste-belegnr${datum ? `?datum=${datum}` : ''}`)
export const getKassenstand = () =>
  request<{ kassenstand: string }>('/kassenbuch/kassenstand')
export const getKassenbuchBelegUrl = async (id: number, drucken = false): Promise<string> => {
  const base = await getApiBase()
  return `${base}/kassenbuch/${id}/beleg${drucken ? '?drucken=1' : ''}`
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
  zeitraum?: 'monat' | 'jahr' | 'alle'
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
  notizen?: string
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
export async function dsgvoExportKunde(id: number) {
  const base = await getBaseUrl()
  await openUrl(`${base}/kunden/${id}/dsgvo-export`)
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

// --- Export ---
export async function downloadGobdExport(jahr: number) {
  const base = await getBaseUrl()
  await openUrl(`${base}/export/gobd?jahr=${jahr}`)
}

// --- Backup ---
export async function downloadBackup() {
  const base = await getBaseUrl()
  await openUrl(`${base}/backup/download`)
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
}

export type RechnungspositionCreate = {
  beschreibung: string
  menge?: string
  einheit?: string
  netto: string
  ust_satz: string
  artikel_id?: number
  kategorie_id?: number
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
  leistungsdatum: string | null
  faellig_am: string | null
  kunde_id: number | null
  kunde_name: string | null
  kunde_email: string | null
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
  zahlungsstatus: 'offen' | 'teilweise' | 'bezahlt'
  zahlungsdatum: string | null
  notizen: string | null
  externe_belegnr: string | null
  positionen: Rechnungsposition[]
  zahlungen: ZahlungKompakt[]
  ist_entwurf: boolean
  ausgegeben: boolean
  immutable: boolean
  storniert: boolean
  erstellt_am: string
  aktualisiert_am: string
}

export type RechnungCreate = {
  typ: 'eingang' | 'ausgang'
  rechnungsnummer?: string
  datum: string
  leistungsdatum?: string
  faellig_am?: string
  kunde_id?: number
  lieferant_id?: number
  partner_freitext?: string
  kategorie_id?: number
  notizen?: string
  externe_belegnr?: string
  ist_entwurf?: boolean
  positionen: RechnungspositionCreate[]
}

export type RechnungUpdate = Partial<RechnungCreate>

export type BarZahlungCreate = {
  betrag?: string
  datum: string
  zahlungsart: 'Bar' | 'Karte' | 'PayPal' | 'Bank'
  beschreibung?: string
}

export type BarZahlungResult = {
  kassenbucheintrag_id: number
  kassenbucheintrag_belegnr: string
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
}) => request<Rechnung[]>(`/rechnungen${toQuery(filter ?? {})}`)

export const getOffeneRechnungen = () => request<Rechnung[]>('/rechnungen/offene')

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

export const stornoRechnung = (id: number) =>
  request<Rechnung>(`/rechnungen/${id}/storno`, { method: 'POST' })

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

// --- Artikelstamm ---
export type ArtikelTyp = 'artikel' | 'dienstleistung' | 'fremdleistung'

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
  kategorie: string | null
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
  kategorie?: string
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
