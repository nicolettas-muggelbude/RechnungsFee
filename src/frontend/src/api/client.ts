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
  iban?: string
  bic?: string
  bank_name?: string
}
export const getUnternehmen = () => request<Unternehmen | null>('/unternehmen')
export const createUnternehmen = (data: Unternehmen) =>
  request<Unternehmen>('/unternehmen', { method: 'POST', body: JSON.stringify(data) })
export const updateUnternehmen = (data: Partial<Unternehmen>) =>
  request<Unternehmen>('/unternehmen', { method: 'PUT', body: JSON.stringify(data) })

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
  zahlungsart: 'Bar' | 'Karte' | 'Bank' | 'PayPal'
  art: 'Einnahme' | 'Ausgabe'
  netto_betrag: string
  ust_satz: string
  ust_betrag: string
  brutto_betrag: string
  vorsteuerabzug: boolean
  steuerbefreiung_grund: string | null
  immutable: boolean
  erstellt_am: string
}

export type KassenbuchEintragCreate = {
  datum: string
  beschreibung: string
  kategorie_id?: number
  zahlungsart: 'Bar' | 'Karte' | 'Bank' | 'PayPal'
  art: 'Einnahme' | 'Ausgabe'
  brutto_betrag: string
  ust_satz: string
  vorsteuerabzug?: boolean
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

export const getKassenbuch = (filter?: { monat?: string; kategorie_id?: number; art?: string }) =>
  request<KassenbuchEintrag[]>(`/kassenbuch${toQuery(filter ?? {})}`)
export const createKassenbuchEintrag = (data: KassenbuchEintragCreate) =>
  request<KassenbuchEintrag>('/kassenbuch', { method: 'POST', body: JSON.stringify(data) })
export const getKassenbuchEintrag = (id: number) =>
  request<KassenbuchEintrag>(`/kassenbuch/${id}`)
export const stornoKassenbuchEintrag = (id: number, grund: string) =>
  request<KassenbuchEintrag>(`/kassenbuch/${id}/storno`, {
    method: 'POST',
    body: JSON.stringify({ grund }),
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
  kassenbewegungen_anzahl: number
  immutable: boolean
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
export const getTagesabschluesse = () => request<Tagesabschluss[]>('/tagesabschluss')
export const createTagesabschluss = (data: {
  datum: string
  ist_endbestand: string
  differenz_begruendung?: string
  differenz_buchungsart?: string
}) => request<Tagesabschluss>('/tagesabschluss', { method: 'POST', body: JSON.stringify(data) })

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
