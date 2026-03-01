const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Unbekannter Fehler')
  }
  // 204 No Content
  if (res.status === 204) return undefined as T
  return res.json()
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
  iban?: string
  bic?: string
  bank_name?: string
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
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/unternehmen/logo`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Logo-Upload fehlgeschlagen')
  }
  return res.json()
}

export async function deleteLogo(): Promise<void> {
  const res = await fetch(`${BASE}/unternehmen/logo`, { method: 'DELETE' })
  if (!res.ok && res.status !== 204) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Logo löschen fehlgeschlagen')
  }
}

export function getLogoUrl(): string {
  return `${BASE}/unternehmen/logo`
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

export function downloadTagesabschlussPdf(params: {
  zeitraum?: 'monat' | 'jahr' | 'alle'
  wert?: string
}) {
  const { zeitraum = 'alle', wert } = params
  const searchParams = new URLSearchParams({ zeitraum })
  if (wert) searchParams.set('wert', wert)
  window.open(`/api/tagesabschluss/export/pdf?${searchParams}`, '_blank')
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
export function dsgvoExportKunde(id: number) {
  window.open(`/api/kunden/${id}/dsgvo-export`, '_blank')
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
export function dsgvoExportLieferant(id: number) {
  window.open(`/api/lieferanten/${id}/dsgvo-export`, '_blank')
}

// --- Export ---
export function downloadGobdExport(jahr: number) {
  window.open(`/api/export/gobd?jahr=${jahr}`, '_blank')
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
  const res = await fetch(`${BASE}/rechnungen/${id}/pdf`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'PDF-Export fehlgeschlagen')
  }
  return res.blob()
}
