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
