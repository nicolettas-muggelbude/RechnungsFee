import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getUnternehmen, updateUnternehmen, uploadLogo, deleteLogo, getLogoUrl, sendeTestMail,
  type Unternehmen,
} from '../../api/client'
import { InfoTooltip } from '../../components/InfoTooltip'
import { DateInput } from '../../components/DateInput'
import { KONTORAHMEN_LS_KEY, type KontorahmenModus } from '../../utils/kontorahmen'

// ---------------------------------------------------------------------------
// Hilfskomponenten
// ---------------------------------------------------------------------------

function Field({ label, children }: { label: React.ReactNode; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">{label}</label>
      {children}
    </div>
  )
}

const inputCls = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100 dark:placeholder-slate-400"
const selectCls = `${inputCls} bg-white dark:bg-slate-700`

// ---------------------------------------------------------------------------
// Tab-Navigation
// ---------------------------------------------------------------------------

type TabId = 'firma' | 'steuer' | 'rechnungen' | 'artikel' | 'email' | 'unterschrift'

const TABS: { id: TabId; label: string }[] = [
  { id: 'firma',        label: 'Firma' },
  { id: 'steuer',       label: 'Steuer & Recht' },
  { id: 'rechnungen',   label: 'Rechnungen' },
  { id: 'artikel',      label: 'Artikel' },
  { id: 'email',        label: 'E-Mail' },
  { id: 'unterschrift', label: 'Unterschrift' },
]

function TabNav({ active, onChange }: { active: TabId; onChange: (t: TabId) => void }) {
  return (
    <div className="flex gap-0 border-b border-slate-200 dark:border-slate-700 overflow-x-auto">
      {TABS.map(t => (
        <button
          key={t.id}
          type="button"
          onClick={() => onChange(t.id)}
          className={`px-5 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
            active === t.id
              ? 'border-blue-600 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Logo-Sektion
// ---------------------------------------------------------------------------

function LogoSektion({
  logoVorhanden,
  onUploaded,
  onDeleted,
}: {
  logoVorhanden: boolean
  onUploaded: (u: Unternehmen) => void
  onDeleted: () => void
}) {
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [fehler, setFehler] = useState<string | null>(null)
  const [cacheBust, setCacheBust] = useState(Date.now())
  const [logoSrc, setLogoSrc] = useState<string>('')
  useEffect(() => {
    getLogoUrl().then((url) => setLogoSrc(`${url}?v=${cacheBust}`))
  }, [cacheBust])

  const uploadMut = useMutation({
    mutationFn: (file: File) => uploadLogo(file),
    onSuccess: (u) => {
      setFehler(null)
      setCacheBust(Date.now())
      qc.invalidateQueries({ queryKey: ['unternehmen'] })
      onUploaded(u)
    },
    onError: (e: Error) => setFehler(e.message),
  })

  const deleteMut = useMutation({
    mutationFn: () => deleteLogo(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['unternehmen'] })
      onDeleted()
    },
    onError: (e: Error) => setFehler(e.message),
  })

  function handleDatei(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    uploadMut.mutate(file)
    e.target.value = ''
  }

  return (
    <div className="flex items-start gap-6">
      <div className="w-28 h-20 rounded-xl border-2 border-dashed border-slate-300 dark:border-slate-600 flex items-center justify-center overflow-hidden bg-slate-50 dark:bg-slate-900 flex-shrink-0">
        {logoVorhanden ? (
          <img
            src={logoSrc}
            alt="Firmenlogo"
            className="max-w-full max-h-full object-contain"
            onError={() => setCacheBust(Date.now())}
          />
        ) : (
          <span className="text-slate-300 text-3xl">🏢</span>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <input
          ref={fileRef}
          type="file"
          accept="image/png,image/jpeg,image/webp,image/svg+xml"
          className="hidden"
          onChange={handleDatei}
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={uploadMut.isPending}
          className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 disabled:opacity-50"
        >
          {uploadMut.isPending ? 'Lädt…' : logoVorhanden ? 'Logo ändern' : 'Logo hochladen'}
        </button>
        {logoVorhanden && (
          <button
            type="button"
            onClick={() => deleteMut.mutate()}
            disabled={deleteMut.isPending}
            className="px-4 py-2 text-sm border border-red-200 dark:border-red-800 rounded-lg hover:bg-red-50 dark:hover:bg-red-950 text-red-600 dark:text-red-400 disabled:opacity-50"
          >
            {deleteMut.isPending ? '…' : 'Entfernen'}
          </button>
        )}
        <p className="text-xs text-slate-400 dark:text-slate-500">PNG, JPEG, WEBP oder SVG · max. 2 MB</p>
        {fehler && <p className="text-xs text-red-600 dark:text-red-400">{fehler}</p>}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Firmendaten-Sektion (Firma + Steuer + Rechnungen – geteilt via activeTab)
// ---------------------------------------------------------------------------

function FirmendatenSektion({ data, activeTab }: { data: Unternehmen; activeTab: TabId }) {
  const qc = useQueryClient()
  const [form, setForm] = useState<Partial<Unternehmen>>(() => {
    const { logo_pfad: _logo, ...rest } = data
    return rest
  })
  const [gespeichert, setGespeichert] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)
  const [kontorahmenModus, setKontorahmenModus] = useState<KontorahmenModus>(
    () => (localStorage.getItem(KONTORAHMEN_LS_KEY) ?? '') as KontorahmenModus
  )

  function handleKontorahmenChange(modus: KontorahmenModus) {
    setKontorahmenModus(modus)
    if (modus) localStorage.setItem(KONTORAHMEN_LS_KEY, modus)
    else localStorage.removeItem(KONTORAHMEN_LS_KEY)
    window.dispatchEvent(new StorageEvent('storage', { key: KONTORAHMEN_LS_KEY, newValue: modus || null }))
  }

  const mut = useMutation({
    mutationFn: (d: Partial<Unternehmen>) => updateUnternehmen(d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['unternehmen'] })
      setGespeichert(true)
      setFehler(null)
      setTimeout(() => setGespeichert(false), 2500)
    },
    onError: (e: Error) => setFehler(e.message),
  })

  function set(key: keyof Unternehmen, value: string | boolean | number | null) {
    setForm(f => ({ ...f, [key]: value }))
  }

  function handleSpeichern(e: React.FormEvent) {
    e.preventDefault()

    const steuerzeichen = /[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/

    const hatFirma = !!(form.firmenname?.trim())
    const hatName  = !!(form.vorname?.trim() || form.nachname?.trim())
    if (!hatFirma && !hatName) { setFehler('Firmenname oder Vor- und Nachname ist erforderlich.'); return }
    if (hatFirma && steuerzeichen.test(form.firmenname!)) { setFehler('Firmenname enthält ungültige Zeichen.'); return }
    if ((form.firmenname ?? '').length > 200) { setFehler('Firmenname: maximal 200 Zeichen.'); return }

    if (!form.strasse?.trim()) { setFehler('Straße ist erforderlich.'); return }
    if (steuerzeichen.test(form.strasse)) { setFehler('Straße enthält ungültige Zeichen.'); return }
    if ((form.strasse ?? '').length > 200) { setFehler('Straße: maximal 200 Zeichen.'); return }

    if (!form.hausnummer?.trim()) { setFehler('Hausnummer ist erforderlich.'); return }
    if ((form.hausnummer ?? '').length > 10) { setFehler('Hausnummer: maximal 10 Zeichen.'); return }

    if (!form.plz?.trim()) { setFehler('PLZ ist erforderlich.'); return }
    const land = (form.land ?? 'DE').toUpperCase()
    const plzRegeln: Record<string, { re: RegExp; hint: string }> = {
      DE: { re: /^[0-9]{5}$/,              hint: '5 Ziffern (z.B. 10115)' },
      AT: { re: /^[0-9]{4}$/,              hint: '4 Ziffern (z.B. 1010)' },
      CH: { re: /^[0-9]{4}$/,              hint: '4 Ziffern (z.B. 8001)' },
      LI: { re: /^[0-9]{4}$/,              hint: '4 Ziffern (z.B. 9490)' },
      NL: { re: /^[0-9]{4}\s?[A-Z]{2}$/i, hint: '4 Ziffern + 2 Buchstaben (z.B. 1234 AB)' },
    }
    const plzRegel = plzRegeln[land]
    if (plzRegel && !plzRegel.re.test(form.plz.trim())) {
      setFehler(`PLZ für ${land} hat ein ungültiges Format – erwartet: ${plzRegel.hint}.`); return
    }
    if (!plzRegel && !/^[0-9A-Za-z\s-]{4,10}$/.test(form.plz.trim())) {
      setFehler('PLZ hat ein ungültiges Format (4–10 alphanumerische Zeichen).'); return
    }

    if (!form.ort?.trim()) { setFehler('Ort ist erforderlich.'); return }
    if (steuerzeichen.test(form.ort)) { setFehler('Ort enthält ungültige Zeichen.'); return }
    if ((form.ort ?? '').length > 200) { setFehler('Ort: maximal 200 Zeichen.'); return }

    const stNr = (form.steuernummer ?? '').trim()
    const ustId = (form.ust_idnr ?? '').trim()
    if (!stNr && !ustId) {
      setFehler('Steuernummer oder USt-IdNr. ist erforderlich (§14 UStG).'); return
    }
    if (ustId) {
      if (!/^[A-Z]{2}[A-Z0-9+*]{2,13}$/i.test(ustId)) {
        setFehler('USt-IdNr. hat ein ungültiges Format (z.B. DE123456789).'); return
      }
      if (ustId.toUpperCase().startsWith('DE') && !/^DE[0-9]{9}$/i.test(ustId)) {
        setFehler('Deutsche USt-IdNr. muss das Format DE + 9 Ziffern haben (z.B. DE123456789).'); return
      }
    }

    const iban = (form.iban ?? '').replace(/\s/g, '').toUpperCase()
    if (!iban) { setFehler('IBAN ist erforderlich.'); return }
    if (iban.length < 15 || iban.length > 34 || !/^[A-Z]{2}[0-9A-Z]+$/.test(iban)) {
      setFehler('IBAN hat ein ungültiges Format (z.B. DE89 3704 0044 0532 0130 00).'); return
    }

    setFehler(null)
    mut.mutate(form)
  }

  const inp = (key: keyof Unternehmen, placeholder = '') => (
    <input
      type="text"
      value={(form[key] as string) ?? ''}
      onChange={ev => set(key, ev.target.value)}
      placeholder={placeholder}
      className={inputCls}
    />
  )

  const isFirmTab       = activeTab === 'firma'
  const isSteuerTab     = activeTab === 'steuer'
  const isRechnungTab   = activeTab === 'rechnungen'
  const isArtikelTab    = activeTab === 'artikel'
  const isFormTab       = isFirmTab || isSteuerTab || isRechnungTab || isArtikelTab

  return (
    <form onSubmit={handleSpeichern} className="space-y-6">

      {/* ── Tab: Firma ────────────────────────────────────────────────── */}
      <div className={isFirmTab ? 'space-y-6' : 'hidden'}>

        <LogoSektion
          logoVorhanden={!!data.logo_pfad}
          onUploaded={() => {}}
          onDeleted={() => {}}
        />

        <hr className="border-slate-100 dark:border-slate-700" />

        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">Firmendaten</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">Firmenname <span className="font-medium">oder</span> Vor- und Nachname ist erforderlich.</p>
          <Field label="Firmen- oder Tätigkeitsname">{inp('firmenname', 'z.B. Maria Muster Webdesign')}</Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Vorname">{inp('vorname', 'Maria')}</Field>
            <Field label="Nachname">{inp('nachname', 'Muster')}</Field>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2">
              <Field label="Straße *">{inp('strasse', 'Musterstraße')}</Field>
            </div>
            <Field label="Nr. *">{inp('hausnummer', '1a')}</Field>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Field label="PLZ *">{inp('plz', '12345')}</Field>
            <div className="col-span-2">
              <Field label="Ort *">{inp('ort', 'Berlin')}</Field>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="E-Mail">
              <input
                type="email"
                value={(form.email as string) ?? ''}
                onChange={ev => set('email', ev.target.value)}
                placeholder="maria@beispiel.de"
                className={inputCls}
              />
            </Field>
            <Field label="Telefon">{inp('telefon', '+49 30 12345678')}</Field>
          </div>
          <Field label="Webseite">{inp('webseite', 'https://maria-muster.de')}</Field>
          {(form.taetigkeitsart === 'gewerbe' || form.taetigkeitsart === 'gemischt') && (
            <Field label="Bezeichnung des Gewerbes">{inp('bezeichnung_des_gewerbes', 'z.B. Tischlerei, Buchhandlung, IT-Dienstleistungen')}</Field>
          )}
        </div>

        <hr className="border-slate-100 dark:border-slate-700" />

        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">Beruf & Kammermitgliedschaft</h3>
          <p className="text-xs text-slate-400 dark:text-slate-500">
            Optional – erscheint auf Rechnungen. Relevant für Anwälte, Steuerberater, Architekten und andere Kammerberufe.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Berufsbezeichnung">{inp('berufsbezeichnung', 'z.B. Rechtsanwältin')}</Field>
            <Field label="Kammermitgliedschaft">{inp('kammer_mitgliedschaft', 'z.B. Rechtsanwaltskammer Berlin')}</Field>
          </div>
        </div>

        <hr className="border-slate-100 dark:border-slate-700" />

        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">Handelsregister</h3>
          <p className="text-xs text-slate-400 dark:text-slate-500">Wenn dein Unternehmen im Handelsregister eingetragen ist, ergänze Register-Nr. und Registergericht. Nicht eingetragene Einzelunternehmer und Freiberufler lassen diese Felder leer.</p>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Register-Nr.">{inp('handelsregister_nr', 'z.B. HRA 12345 oder HRB 215517')}</Field>
            <Field label="Registergericht">{inp('handelsregister_gericht', 'Oldenburg')}</Field>
          </div>
        </div>
      </div>

      {/* ── Tab: Steuer & Recht ───────────────────────────────────────── */}
      <div className={isSteuerTab ? 'space-y-4' : 'hidden'}>
        <div className="grid grid-cols-2 gap-4">
          <Field label={<>Steuernummer * <InfoTooltip text="Deine Steuernummer vom Finanzamt (z.B. 12/345/67890). Mindestens Steuernummer oder USt-IdNr. ist Pflicht (§14 UStG / ZUGFeRD)." /></>}>{inp('steuernummer', '12/345/67890')}</Field>
          <Field label="Finanzamt">{inp('finanzamt', 'Finanzamt Berlin-Mitte')}</Field>
        </div>
        <Field label={<>USt-IdNr. <InfoTooltip text="Umsatzsteuer-Identifikationsnummer (z.B. DE123456789) – benötigt für EU-Geschäfte. Bei rein inländischen Geschäften genügt die Steuernummer." /></>}>{inp('ust_idnr', 'DE123456789')}</Field>
        <Field label={<>W-IdNr. <InfoTooltip text="Wirtschafts-Identifikationsnummer – seit November 2024 vom Bundeszentralamt für Steuern zugeteilt. Nicht zu verwechseln mit der USt-IdNr." /></>}>{inp('w_idnr', 'DE123456789')}</Field>

        <hr className="border-slate-100 dark:border-slate-700" />

        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={!!form.ist_kleinunternehmer}
            onChange={ev => set('ist_kleinunternehmer', ev.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600"
          />
          <div>
            <span className="text-sm font-medium text-slate-700 dark:text-slate-200 flex items-center gap-1">
              Kleinunternehmer (§19 UStG)
              <InfoTooltip text="Als Kleinunternehmer weist du keine Umsatzsteuer auf Rechnungen aus und kannst keine Vorsteuer abziehen. Voraussetzungen (ab 2025): Netto-Gesamtumsatz im Vorjahr ≤ 25.000 € und im laufenden Jahr unter 100.000 € netto." side="bottom" />
            </span>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Keine USt auf Rechnungen, kein Vorsteuerabzug.</p>
          </div>
        </label>

        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={!!form.bezieht_transferleistungen}
            onChange={ev => set('bezieht_transferleistungen', ev.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600"
          />
          <div>
            <span className="text-sm font-medium text-slate-700 dark:text-slate-200 flex items-center gap-1">
              Transferleistungen (ALG II / Bürgergeld)
              <InfoTooltip text="Aktiviere diese Option wenn du Bürgergeld oder ALG II beziehst. RechnungsFee berücksichtigt dann den Grundfreibetrag nach §11b SGB II." side="bottom" />
            </span>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Freibetrag nach §11b SGB II wird berücksichtigt.</p>
          </div>
        </label>

        {form.bezieht_transferleistungen && (
          <div className="rounded-xl border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950 p-4 space-y-4">
            <p className="text-xs font-semibold text-blue-700 dark:text-blue-300 uppercase tracking-wide">
              Angaben für Anlage EKS (Jobcenter-Formular)
            </p>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Geburtsdatum">
                <DateInput
                  value={form.geburtsdatum ?? ''}
                  onChange={(v) => set('geburtsdatum', v)}
                  className={inputCls}
                />
              </Field>
              <Field label={<>BG-Nummer <InfoTooltip text="Nummer der Bedarfsgemeinschaft aus deinem Bewilligungsbescheid des Jobcenters." /></>}>
                {inp('bg_nummer', 'z.B. 12345678')}
              </Field>
            </div>
            <Field label="Jobcenter">
              {inp('jobcenter_name', 'z.B. Jobcenter Berlin-Mitte')}
            </Field>
            <Field label={<>Abrechnungszeitraum Beginn <InfoTooltip text="Startmonat deines 6-Monats-Abrechnungszeitraums aus dem Leistungsbescheid. RechnungsFee berechnet den aktuellen Zeitraum daraus automatisch." /></>}>
              <select
                value={form.leistungsbescheid_monat?.match(/^\d{4}-(\d{2})$/) ? form.leistungsbescheid_monat.split('-')[1] : ''}
                onChange={e => {
                  const y = new Date().getFullYear()
                  set('leistungsbescheid_monat', e.target.value ? `${y}-${e.target.value}` : null)
                }}
                className={inputCls}
              >
                <option value="">– nicht gesetzt –</option>
                {['Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember'].map((m, i) => (
                  <option key={i} value={String(i + 1).padStart(2, '0')}>{m}</option>
                ))}
              </select>
            </Field>
          </div>
        )}

        <hr className="border-slate-100 dark:border-slate-700" />

        <Field label={<>Voranmeldungsrhythmus <InfoTooltip text="Monatlich: wenn deine Jahres-USt-Zahllast im Vorjahr über 7.500 € lag. Vierteljährlich: bei Zahllast ≤ 7.500 €. Kleinunternehmer §19 sind von der UStVA befreit." /></>}>
          <select
            value={form.voranmeldungsrhythmus ?? 'quartal'}
            onChange={ev => set('voranmeldungsrhythmus', ev.target.value)}
            className={selectCls}
          >
            <option value="quartal">Vierteljährlich</option>
            <option value="monat">Monatlich</option>
          </select>
        </Field>

        <hr className="border-slate-100 dark:border-slate-700" />

        <div className="flex items-center gap-2">
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Steuer-Fristenliste</p>
          {form.bundesland
            ? <span className="text-xs px-1.5 py-0.5 rounded bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400">aktiv</span>
            : <span className="text-xs px-1.5 py-0.5 rounded bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">inaktiv – Bundesland wählen</span>
          }
        </div>

        <Field label={<>Bundesland <InfoTooltip text="Aktiviert die Steuer-Fristenliste. Solange kein Bundesland gesetzt ist, werden keine Fristen berechnet und der Dashboard-Banner bleibt ausgeblendet. Bundesländer haben unterschiedliche Feiertage, die Abgabefristen verschieben können." /></>}>
          <select
            value={form.bundesland ?? ''}
            onChange={ev => set('bundesland', ev.target.value || null)}
            className={selectCls}
          >
            <option value="">– bitte wählen –</option>
            <option value="BB">Brandenburg</option>
            <option value="BE">Berlin</option>
            <option value="BW">Baden-Württemberg</option>
            <option value="BY">Bayern</option>
            <option value="HB">Bremen</option>
            <option value="HE">Hessen</option>
            <option value="HH">Hamburg</option>
            <option value="MV">Mecklenburg-Vorpommern</option>
            <option value="NI">Niedersachsen</option>
            <option value="NW">Nordrhein-Westfalen</option>
            <option value="RP">Rheinland-Pfalz</option>
            <option value="SH">Schleswig-Holstein</option>
            <option value="SL">Saarland</option>
            <option value="SN">Sachsen</option>
            <option value="ST">Sachsen-Anhalt</option>
            <option value="TH">Thüringen</option>
          </select>
        </Field>

        <div className="flex items-center gap-3">
          <input
            id="dauerfrist"
            type="checkbox"
            checked={form.dauerfristverlaengerung_ust ?? false}
            onChange={ev => set('dauerfristverlaengerung_ust', ev.target.checked)}
            className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
          />
          <label htmlFor="dauerfrist" className="text-sm text-slate-700 dark:text-slate-200">
            Dauerfristverlängerung (UStVA) <span className="text-slate-400 text-xs">– Frist verschiebt sich um +1 Monat</span>
          </label>
        </div>

        <div className="flex items-center gap-3">
          <input
            id="est_vz"
            type="checkbox"
            checked={form.est_vorauszahlungen_aktiv ?? false}
            onChange={ev => set('est_vorauszahlungen_aktiv', ev.target.checked)}
            className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
          />
          <label htmlFor="est_vz" className="text-sm text-slate-700 dark:text-slate-200">
            Einkommensteuer-Vorauszahlungen <span className="text-slate-400 text-xs">– Termine 10.03 / 10.06 / 10.09 / 10.12</span>
          </label>
        </div>

        <div className="flex items-center gap-3">
          <input
            id="gewst_vz"
            type="checkbox"
            checked={form.gewst_vorauszahlungen_aktiv ?? false}
            onChange={ev => set('gewst_vorauszahlungen_aktiv', ev.target.checked)}
            className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
          />
          <label htmlFor="gewst_vz" className="text-sm text-slate-700 dark:text-slate-200">
            Gewerbesteuer-Vorauszahlungen <span className="text-slate-400 text-xs">– Termine 15.02 / 15.05 / 15.08 / 15.11</span>
          </label>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label={<>Kontenrahmen <InfoTooltip text="SKR03: Standard für Dienstleister und Freiberufler. SKR04: Standard für Handel und produzierende Betriebe. SKR49: Für Vereine und Non-Profits." /></>}>
            <select
              value={form.kontenrahmen ?? 'SKR03'}
              onChange={ev => set('kontenrahmen', ev.target.value)}
              className={selectCls}
            >
              <option value="SKR03">SKR03 – Freiberufler</option>
              <option value="SKR04">SKR04 – Handel/Industrie</option>
              <option value="SKR49">SKR49 – Vereine</option>
            </select>
          </Field>
          <Field label="Rechtsform">
            <select
              value={form.rechtsform ?? 'Einzelunternehmer'}
              onChange={ev => set('rechtsform', ev.target.value)}
              className={selectCls}
            >
              <option>Einzelunternehmer</option>
              <option>Freiberufler</option>
              <option>GbR</option>
              <option>UG (haftungsbeschränkt)</option>
              <option>GmbH</option>
              <option>AG</option>
              <option>e.K.</option>
              <option>Eingetragener Verein (e.V.)</option>
              <option>Sonstige</option>
            </select>
          </Field>
        </div>

        <Field label="Tätigkeitsart">
          <select
            value={form.taetigkeitsart ?? 'freiberuflich'}
            onChange={ev => set('taetigkeitsart', ev.target.value)}
            className={selectCls}
          >
            <option value="freiberuflich">Freiberuflich</option>
            <option value="gewerbe">Gewerblich</option>
            <option value="gemischt">Gemischt</option>
          </select>
        </Field>
      </div>

      {/* ── Tab: Rechnungen ───────────────────────────────────────────── */}
      <div className={isRechnungTab ? 'space-y-6' : 'hidden'}>

        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">Bankverbindung</h3>
          <Field label="IBAN *">{inp('iban', 'DE89 3704 0044 0532 0130 00')}</Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="BIC">{inp('bic', 'COBADEFFXXX')}</Field>
            <Field label="Bank">{inp('bank_name', 'Deutsche Bank')}</Field>
          </div>
        </div>

        <hr className="border-slate-100 dark:border-slate-700" />

        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">Rechnungs-PDF</h3>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={form.zahlungshinweis_aktiv !== false}
              onChange={ev => set('zahlungshinweis_aktiv', ev.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600"
            />
            <div>
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Standard-Zahlungshinweis anzeigen</span>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Fügt automatisch „Bitte überweisen Sie … auf IBAN …" unter dem Rechnungsbetrag ein.
                Deaktivieren wenn du einen eigenen Text im Notizfeld der Rechnung hinterlegen möchtest.
              </p>
            </div>
          </label>

          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200 whitespace-nowrap">Standard-Zahlungsziel</label>
            <input
              type="number"
              min={0}
              max={365}
              value={form.standard_zahlungsziel ?? 14}
              onChange={ev => set('standard_zahlungsziel', parseInt(ev.target.value) || 0)}
              className="w-20 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
            />
            <span className="text-sm text-slate-500 dark:text-slate-400">Tage nach Rechnungsdatum</span>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200 whitespace-nowrap">Standard-Skonto</label>
            <input
              type="number"
              min={0}
              max={100}
              step={0.5}
              value={form.standard_skonto_prozent ?? ''}
              onChange={ev => set('standard_skonto_prozent', ev.target.value === '' ? null : parseFloat(ev.target.value))}
              placeholder="z. B. 2"
              className="w-20 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
            />
            <span className="text-sm text-slate-500 dark:text-slate-400">%</span>
            <span className="text-sm text-slate-400 dark:text-slate-500">bei Zahlung innerhalb von</span>
            <input
              type="number"
              min={1}
              max={365}
              value={form.standard_skonto_tage ?? ''}
              onChange={ev => set('standard_skonto_tage', ev.target.value === '' ? null : parseInt(ev.target.value))}
              placeholder="z. B. 10"
              className="w-20 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
            />
            <span className="text-sm text-slate-500 dark:text-slate-400">Tagen (leer = kein Skonto)</span>
          </div>

          <label className={`flex items-start gap-3 ${form.iban?.trim() ? 'cursor-pointer' : 'cursor-not-allowed'}`}>
            <input
              type="checkbox"
              checked={!!form.qr_zahlung_aktiv}
              onChange={ev => set('qr_zahlung_aktiv', ev.target.checked)}
              disabled={!form.iban?.trim()}
              className={`mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600 disabled:cursor-not-allowed${form.iban?.trim() ? '' : ' opacity-50'}`}
            />
            <div className={form.iban?.trim() ? '' : 'opacity-50'}>
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                GiroCode (QR) auf Rechnung
              </span>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Fügt einen EPC-QR-Code (GiroCode) neben den Zahlungshinweis ein.
                Kunden können damit per Banking-App direkt überweisen – mit vorausgefüllten Daten.
              </p>
            </div>
            {!form.iban?.trim() && (
              <InfoTooltip text="Bitte zuerst eine IBAN unter Bankverbindung hinterlegen." align="right" />
            )}
          </label>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={!!form.lieferschein_aktiv}
              onChange={ev => set('lieferschein_aktiv', ev.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600"
            />
            <div>
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                Lieferscheine aktivieren
              </span>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Lieferscheine können direkt in Rechnungen oder Sammelrechnungen umgewandelt werden.
              </p>
            </div>
          </label>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={!!form.angebote_aktiv}
              onChange={ev => set('angebote_aktiv', ev.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600"
            />
            <div>
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                Angebote aktivieren
              </span>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Angebote mit Gültigkeitsdatum erstellen und direkt in Rechnungen umwandeln.
              </p>
            </div>
          </label>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={!!form.proforma_aktiv}
              onChange={ev => set('proforma_aktiv', ev.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600"
            />
            <div>
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                Proforma-Rechnungen aktivieren
              </span>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Proforma-Rechnungen erstellen (z. B. als Zahlungsaufforderung vor Lieferung) und in echte Rechnungen umwandeln.
              </p>
            </div>
          </label>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={!!form.auftraege_aktiv}
              onChange={ev => set('auftraege_aktiv', ev.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600"
            />
            <div>
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                Aufträge aktivieren
              </span>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Aufträge erstellen (aus Angeboten oder eigenständig) und daraus Rechnungen, Lieferscheine oder Proforma-Rechnungen generieren.
              </p>
            </div>
          </label>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={!!form.wiederkehrend_aktiv}
              onChange={ev => set('wiederkehrend_aktiv', ev.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600"
            />
            <div>
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                Wiederkehrende Rechnungen aktivieren
              </span>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Vorlagen mit Intervall (monatlich, quartalsweise, jährlich) – Entwürfe werden automatisch beim App-Start erstellt.
              </p>
            </div>
          </label>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={!!form.buchungsvorlagen_aktiv}
              onChange={ev => set('buchungsvorlagen_aktiv', ev.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600"
            />
            <div>
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                Wiederkehrende Buchungen aktivieren
              </span>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Vorlagen für Fixkosten (Miete, Leasing, Abonnements) – Modus „Direkt" bucht sofort ins Journal, Modus „Warte auf Beleg" füllt das Eingangsrechnungs-Formular vor.
              </p>
            </div>
          </label>

          <div className="space-y-2 pt-2">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200 block">
              Einleitungstext auf Rechnungen
            </label>
            <textarea
              value={form.einleitungstext ?? ''}
              onChange={ev => set('einleitungstext', ev.target.value || null)}
              rows={4}
              placeholder="Dieser Text erscheint auf allen Rechnungen vor der Positionstabelle. Er kann pro Rechnung individuell überschrieben werden."
              className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 resize-y"
            />
            <p className="text-xs text-slate-400 dark:text-slate-500">
              Leer lassen wenn kein Standardtext gewünscht. Pro Rechnung überschreibbar.
              Markdown: <code className="bg-slate-100 dark:bg-slate-800 px-1 rounded">**fett**</code> <code className="bg-slate-100 dark:bg-slate-800 px-1 rounded">*kursiv*</code> · Zeilenumbruch mit Enter
            </p>
          </div>
        </div>

        <hr className="border-slate-100 dark:border-slate-700" />

        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">Buchungsanzeige</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Kontonummer hinter der Kategorie-Bezeichnung anzeigen – beim Buchen im Journal und beim Rechnungsschreiben.
          </p>
          <div className="flex flex-wrap gap-3">
            {([
              { value: '' as KontorahmenModus, label: 'Nur Bezeichnung' },
              { value: 'skr03' as KontorahmenModus, label: 'Bezeichnung + SKR03' },
              { value: 'skr04' as KontorahmenModus, label: 'Bezeichnung + SKR04' },
            ] as const).map(opt => (
              <label key={opt.value} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="kontorahmen_anzeige"
                  value={opt.value}
                  checked={kontorahmenModus === opt.value}
                  onChange={() => handleKontorahmenChange(opt.value)}
                  className="h-4 w-4 text-blue-600 border-slate-300"
                />
                <span className="text-sm text-slate-700 dark:text-slate-200">{opt.label}</span>
              </label>
            ))}
          </div>
          <p className="text-xs text-slate-400 dark:text-slate-500">
            Beispiel SKR03: Betriebseinnahmen [8400] · Büromaterial [4930]
          </p>
        </div>
      </div>

      {/* ── Tab: Artikel ──────────────────────────────────────────────── */}
      <div className={isArtikelTab ? 'space-y-6' : 'hidden'}>
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">Lagerführung</h3>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={!!form.lagerführung_aktiv}
              onChange={ev => set('lagerführung_aktiv', ev.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600"
            />
            <div>
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                Lagerführung aktivieren
              </span>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Bestand pro Artikel verwalten. Bei Finalisierung einer Rechnung sinkt der Bestand automatisch, bei Storno wird er zurückgebucht. Pro Artikel konfigurierbar: Anfangsbestand, Mindestbestand (Warngrenze) und ob Minusbestand erlaubt ist.
              </p>
            </div>
          </label>
        </div>
      </div>

      {/* Fehler + Speichern-Button (nur für Firma/Steuer/Rechnungen/Artikel-Tabs) */}
      {isFormTab && (
        <>
          {fehler && <p className="text-sm text-red-600 dark:text-red-400">{fehler}</p>}
          <div className="flex items-center gap-3 pt-1">
            <button
              type="submit"
              disabled={mut.isPending}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors"
            >
              {mut.isPending ? 'Speichern…' : 'Speichern'}
            </button>
            {gespeichert && <span className="text-sm text-green-600 dark:text-green-400">✓ Gespeichert</span>}
          </div>
        </>
      )}
    </form>
  )
}

// ---------------------------------------------------------------------------
// Mail-Vorlage-Sektion (alle Dokumenttypen)
// ---------------------------------------------------------------------------

const PLATZHALTER = [
  { key: '{rechnungsnummer}', desc: 'Dokumentnummer' },
  { key: '{datum}',           desc: 'Datum (TT.MM.JJJJ)' },
  { key: '{betrag}',          desc: 'Bruttobetrag' },
  { key: '{faellig_am}',      desc: 'Fälligkeitsdatum' },
  { key: '{gueltig_bis}',     desc: 'Gültig bis (Angebot)' },
  { key: '{kunde}',           desc: 'Name des Empfängers' },
  { key: '{firmenname}',      desc: 'Dein Firmenname' },
]

type VorlagenTyp = 'Rechnung' | 'Angebot' | 'Proforma' | 'Auftrag'

const VORLAGEN_DEFAULT: Record<VorlagenTyp, { betreff: string; text: string }> = {
  Rechnung: {
    betreff: 'Rechnung {rechnungsnummer}',
    text: 'Hallo {kunde},\n\nanbei findest du die Rechnung {rechnungsnummer} vom {datum}.\n\nBetrag: {betrag}\nFällig am: {faellig_am}\n\nBitte überweise den Betrag auf das angegebene Konto.\n\nViele Grüße\n{firmenname}',
  },
  Angebot: {
    betreff: 'Angebot {rechnungsnummer}',
    text: 'Hallo {kunde},\n\nanbei findest du unser Angebot {rechnungsnummer} vom {datum}.\n\nAngebotsbetrag: {betrag}\nGültig bis: {gueltig_bis}\n\nBei Fragen stehe ich gerne zur Verfügung.\n\nViele Grüße\n{firmenname}',
  },
  Proforma: {
    betreff: 'Proforma-Rechnung {rechnungsnummer}',
    text: 'Hallo {kunde},\n\nanbei findest du unsere Proforma-Rechnung {rechnungsnummer} vom {datum}.\n\nBetrag: {betrag}\nZahlungsziel: {faellig_am}\n\nNach Zahlungseingang erstellst du die Rechnung automatisch.\n\nViele Grüße\n{firmenname}',
  },
  Auftrag: {
    betreff: 'Auftragsbestätigung {rechnungsnummer}',
    text: 'Hallo {kunde},\n\nvielen Dank für deinen Auftrag! Anbei findest du die Auftragsbestätigung {rechnungsnummer} vom {datum}.\n\nAuftragswert: {betrag}\n\nViele Grüße\n{firmenname}',
  },
}

function betreffFeld(typ: VorlagenTyp): keyof Unternehmen {
  return typ === 'Rechnung' ? 'mail_betreff_vorlage' : typ === 'Angebot' ? 'mail_betreff_angebot' : typ === 'Proforma' ? 'mail_betreff_proforma' : 'mail_betreff_auftrag'
}
function textFeld(typ: VorlagenTyp): keyof Unternehmen {
  return typ === 'Rechnung' ? 'mail_text_vorlage' : typ === 'Angebot' ? 'mail_text_angebot' : typ === 'Proforma' ? 'mail_text_proforma' : 'mail_text_auftrag'
}

function MailVorlageSektion({ data }: { data: Unternehmen }) {
  const qc = useQueryClient()
  const [aktTyp, setAktTyp] = useState<VorlagenTyp>('Rechnung')
  const def = VORLAGEN_DEFAULT[aktTyp]
  const [betreff, setBetreff] = useState(data[betreffFeld(aktTyp)] as string ?? def.betreff)
  const [text, setText] = useState(data[textFeld(aktTyp)] as string ?? def.text)
  const [gespeichert, setGespeichert] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)

  function ladeTyp(typ: VorlagenTyp) {
    setAktTyp(typ)
    setBetreff(data[betreffFeld(typ)] as string ?? VORLAGEN_DEFAULT[typ].betreff)
    setText(data[textFeld(typ)] as string ?? VORLAGEN_DEFAULT[typ].text)
    setGespeichert(false)
  }

  const mut = useMutation({
    mutationFn: () => updateUnternehmen({ [betreffFeld(aktTyp)]: betreff, [textFeld(aktTyp)]: text }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['unternehmen'] })
      setGespeichert(true)
      setFehler(null)
      setTimeout(() => setGespeichert(false), 2500)
    },
    onError: (e: Error) => setFehler(e.message),
  })

  const typen: VorlagenTyp[] = ['Rechnung', 'Angebot', 'Proforma', 'Auftrag']

  return (
    <div className="space-y-5">
      <div className="flex gap-1">
        {typen.map(t => (
          <button key={t} onClick={() => ladeTyp(t)}
            className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${aktTyp === t ? 'bg-blue-600 text-white border-blue-600' : 'border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'}`}>
            {t}
          </button>
        ))}
      </div>

      <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-xl p-4">
        <p className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-2">Verfügbare Platzhalter</p>
        <div className="grid grid-cols-2 gap-x-6 gap-y-1">
          {PLATZHALTER.map(p => (
            <div key={p.key} className="flex gap-2 text-xs">
              <code className="text-blue-700 dark:text-blue-300 font-mono whitespace-nowrap">{p.key}</code>
              <span className="text-blue-600 dark:text-blue-400">{p.desc}</span>
            </div>
          ))}
        </div>
      </div>

      <Field label="Betreff">
        <input type="text" value={betreff} onChange={ev => setBetreff(ev.target.value)} className={inputCls} />
      </Field>

      <Field label="Text">
        <textarea value={text} onChange={ev => setText(ev.target.value)} rows={10} className={`${inputCls} resize-y font-mono text-xs`} />
      </Field>

      {fehler && <p className="text-sm text-red-600 dark:text-red-400">{fehler}</p>}

      <div className="flex items-center gap-3">
        <button type="button" onClick={() => mut.mutate()} disabled={mut.isPending}
          className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors">
          {mut.isPending ? 'Speichern…' : 'Vorlage speichern'}
        </button>
        <button type="button" onClick={() => { setBetreff(def.betreff); setText(def.text) }}
          className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300">
          Zurücksetzen
        </button>
        {gespeichert && <span className="text-sm text-green-600 dark:text-green-400">✓ Gespeichert</span>}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// SMTP-Sektion
// ---------------------------------------------------------------------------

function SmtpSektion({ data }: { data: Unternehmen }) {
  const qc = useQueryClient()
  const [aktiv, setAktiv] = useState(data.smtp_aktiv ?? false)
  const [host, setHost] = useState(data.smtp_host ?? '')
  const [port, setPort] = useState(String(data.smtp_port ?? 587))
  const [ssl, setSsl] = useState(data.smtp_ssl ?? false)
  const [user, setUser] = useState(data.smtp_user ?? '')
  const [passwort, setPasswort] = useState(data.smtp_passwort ?? '')
  const [von, setVon] = useState(data.smtp_von_adresse ?? '')
  const [testMail, setTestMail] = useState('')
  const [gespeichert, setGespeichert] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)
  const [testStatus, setTestStatus] = useState<'idle' | 'sending' | 'ok' | 'error'>('idle')
  const [testFehler, setTestFehler] = useState<string | null>(null)

  const mut = useMutation({
    mutationFn: () => updateUnternehmen({
      smtp_aktiv: aktiv,
      smtp_host: host || null,
      smtp_port: parseInt(port) || 587,
      smtp_ssl: ssl,
      smtp_user: user || null,
      smtp_passwort: passwort || null,
      smtp_von_adresse: von || null,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['unternehmen'] })
      setGespeichert(true)
      setFehler(null)
      setTimeout(() => setGespeichert(false), 2500)
    },
    onError: (e: Error) => setFehler(e.message),
  })

  async function handleTest() {
    if (!testMail.trim()) return
    setTestStatus('sending')
    setTestFehler(null)
    try {
      await sendeTestMail(testMail.trim())
      setTestStatus('ok')
      setTimeout(() => setTestStatus('idle'), 3000)
    } catch (e: any) {
      setTestStatus('error')
      setTestFehler(e?.message ?? 'Unbekannter Fehler')
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <label className="relative inline-flex items-center cursor-pointer">
          <input type="checkbox" checked={aktiv} onChange={e => setAktiv(e.target.checked)} className="sr-only peer" />
          <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:bg-blue-600 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all" />
        </label>
        <span className="text-sm font-medium text-slate-700 dark:text-slate-200">SMTP-Versand aktivieren</span>
      </div>

      {aktiv && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <Field label="SMTP-Server (Host)">
                <input type="text" value={host} onChange={e => setHost(e.target.value)} placeholder="smtp.gmail.com" className={inputCls} />
              </Field>
            </div>
            <Field label="Port">
              <input type="number" value={port} onChange={e => setPort(e.target.value)} placeholder="587" className={inputCls} />
            </Field>
          </div>

          <div className="flex items-center gap-3">
            <input type="checkbox" id="smtp-ssl" checked={ssl} onChange={e => setSsl(e.target.checked)} className="rounded" />
            <label htmlFor="smtp-ssl" className="text-sm text-slate-600 dark:text-slate-300">SSL (Port 465) statt STARTTLS (Port 587)</label>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Benutzername / E-Mail">
              <input type="email" value={user} onChange={e => setUser(e.target.value)} placeholder="deine@email.de" className={inputCls} />
            </Field>
            <Field label="Passwort / App-Passwort">
              <input type="password" value={passwort} onChange={e => setPasswort(e.target.value)} placeholder="••••••••" className={inputCls} />
            </Field>
          </div>

          <Field label={<>Absender-Adresse <span className="text-xs text-slate-400 font-normal">(optional, Standard: Benutzername)</span></>}>
            <input type="email" value={von} onChange={e => setVon(e.target.value)} placeholder="rechnungen@firma.de" className={inputCls} />
          </Field>

          <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-xl p-3 text-xs text-amber-700 dark:text-amber-300">
            <strong>Gmail:</strong> Nutze ein App-Passwort (Google-Konto → Sicherheit → 2-FA → App-Passwörter). Host: smtp.gmail.com, Port: 587 (STARTTLS).
          </div>

        </div>
      )}

      {fehler && <p className="text-sm text-red-600 dark:text-red-400">{fehler}</p>}

      <div className="flex items-center gap-3">
        <button type="button" onClick={() => mut.mutate()} disabled={mut.isPending}
          className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors">
          {mut.isPending ? 'Speichern…' : 'SMTP speichern'}
        </button>
        {gespeichert && <span className="text-sm text-green-600 dark:text-green-400">✓ Gespeichert</span>}
      </div>

      {aktiv && (
        <>
          <hr className="border-slate-100 dark:border-slate-700" />
          <p className="text-xs text-slate-500 dark:text-slate-400">Testmail erst nach dem Speichern senden.</p>
          <div className="flex gap-2 items-center">
            <input type="email" value={testMail} onChange={e => setTestMail(e.target.value)}
              placeholder="Test-Empfänger eingeben…" className={`${inputCls} flex-1`} />
            <button type="button" onClick={handleTest} disabled={!testMail.trim() || testStatus === 'sending'}
              className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 disabled:opacity-50 whitespace-nowrap">
              {testStatus === 'sending' ? 'Sende…' : '✉️ Testmail'}
            </button>
          </div>
          {testStatus === 'ok' && <p className="text-sm text-green-600 dark:text-green-400">✓ Testmail gesendet</p>}
          {testStatus === 'error' && <p className="text-sm text-red-600 dark:text-red-400">{testFehler}</p>}
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Mail-Signatur-Sektion
// ---------------------------------------------------------------------------

const DEFAULT_SIGNATUR = (firmenname: string) =>
  `--\n${firmenname}`

function mdToHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code style="background:#f1f5f9;padding:1px 4px;border-radius:3px;font-size:0.9em">$1</code>')
    .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" style="max-width:200px;vertical-align:middle">')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" style="color:#2563eb">$1</a>')
    .replace(/\n/g, '<br>')
}

const MD_CHEATSHEET = [
  { syntax: '**fett**',         ergebnis: 'fett' },
  { syntax: '*kursiv*',         ergebnis: 'kursiv' },
  { syntax: '`code`',           ergebnis: 'code' },
  { syntax: '[Text](URL)',       ergebnis: 'Link' },
  { syntax: '![alt](bild-url)', ergebnis: 'Bild' },
]

function SignaturSektion({ data }: { data: Unternehmen }) {
  const qc = useQueryClient()
  const [signatur, setSignatur] = useState(
    data.mail_signatur ?? DEFAULT_SIGNATUR(data.firmenname)
  )
  const [gespeichert, setGespeichert] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)
  const [zeigHilfe, setZeigHilfe] = useState(false)

  const mut = useMutation({
    mutationFn: () => updateUnternehmen({ mail_signatur: signatur }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['unternehmen'] })
      setGespeichert(true)
      setFehler(null)
      setTimeout(() => setGespeichert(false), 2500)
    },
    onError: (e: Error) => setFehler(e.message),
  })

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200">Signatur-Text</label>
            <button
              type="button"
              onClick={() => setZeigHilfe(v => !v)}
              className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
            >
              {zeigHilfe ? 'Hilfe ausblenden' : 'Markdown-Hilfe'}
            </button>
          </div>
          {zeigHilfe && (
            <div className="rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 p-3">
              <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2">Markdown-Syntax</p>
              <table className="w-full text-xs">
                <tbody>
                  {MD_CHEATSHEET.map(r => (
                    <tr key={r.syntax} className="border-t border-slate-100 dark:border-slate-800 first:border-0">
                      <td className="py-1 pr-3 font-mono text-slate-600 dark:text-slate-300">{r.syntax}</td>
                      <td className="py-1 text-slate-400 dark:text-slate-500">→ {r.ergebnis}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">HTML-Tags wie <code className="font-mono">&lt;pre&gt;</code> werden ebenfalls unterstützt.</p>
            </div>
          )}
          <textarea
            value={signatur}
            onChange={ev => setSignatur(ev.target.value)}
            rows={8}
            className={`${inputCls} resize-y font-mono text-xs`}
            placeholder={DEFAULT_SIGNATUR(data.firmenname)}
          />
        </div>

        <div className="space-y-2">
          <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Vorschau (HTML-Mail)</p>
          <div className="rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 p-4 min-h-32 text-xs text-slate-700 dark:text-slate-300">
            {signatur
              ? <div dangerouslySetInnerHTML={{ __html: mdToHtml(signatur) }} />
              : <span className="text-slate-300 dark:text-slate-600 italic">Noch kein Text eingegeben</span>
            }
          </div>
        </div>
      </div>

      {fehler && <p className="text-sm text-red-600 dark:text-red-400">{fehler}</p>}

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => mut.mutate()}
          disabled={mut.isPending}
          className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors"
        >
          {mut.isPending ? 'Speichern…' : 'Signatur speichern'}
        </button>
        <button
          type="button"
          onClick={() => setSignatur(DEFAULT_SIGNATUR(data.firmenname))}
          className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
        >
          Zurücksetzen
        </button>
        {gespeichert && <span className="text-sm text-green-600 dark:text-green-400">✓ Gespeichert</span>}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// E-Mail-Tab (Vorlage + Signatur kombiniert)
// ---------------------------------------------------------------------------

function EmailSektion({ data }: { data: Unternehmen }) {
  return (
    <div className="space-y-8">
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">SMTP-Versand</h3>
        <p className="text-xs text-slate-400 dark:text-slate-500">Direkt aus RechnungsFee versenden – mit PDF-Anhang und Dokumentenpaketen.</p>
      </div>
      <SmtpSektion data={data} />

      <hr className="border-slate-100 dark:border-slate-700" />

      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">Mail-Vorlagen</h3>
        <p className="text-xs text-slate-400 dark:text-slate-500">Betreff und Text für jeden Dokumenttyp separat konfigurierbar.</p>
      </div>
      <MailVorlageSektion data={data} />

      <hr className="border-slate-100 dark:border-slate-700" />

      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">Mail-Signatur</h3>
        <p className="text-xs text-slate-400 dark:text-slate-500">Wird automatisch unter jede ausgehende E-Mail gesetzt (Markdown wird als HTML gerendert).</p>
      </div>
      <SignaturSektion data={data} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Digitale Unterschrift
// ---------------------------------------------------------------------------

function UnterschriftModal({ onSpeichern, onAbbrechen }: {
  onSpeichern: (bild: string) => void
  onAbbrechen: () => void
}) {
  const [modus, setModus] = useState<'zeichnen' | 'hochladen'>('zeichnen')

  const canvasRef = useRef<HTMLCanvasElement>(null)
  const letzterPunkt = useRef<{ x: number; y: number } | null>(null)
  const [zeichnen, setZeichnen] = useState(false)
  const [hatInhalt, setHatInhalt] = useState(false)

  useEffect(() => {
    if (modus !== 'zeichnen') return
    const canvas = canvasRef.current
    if (!canvas) return
    const dpr = window.devicePixelRatio || 1
    const size = canvas.offsetWidth
    canvas.width = size * dpr
    canvas.height = Math.round(size * 0.55 * dpr)
    const ctx = canvas.getContext('2d')!
    ctx.scale(dpr, dpr)
    ctx.lineWidth = 3
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.strokeStyle = '#1e293b'
  }, [modus])

  function getPos(e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current!
    const rect = canvas.getBoundingClientRect()
    if ('touches' in e) {
      return { x: e.touches[0].clientX - rect.left, y: e.touches[0].clientY - rect.top }
    }
    return { x: e.clientX - rect.left, y: e.clientY - rect.top }
  }

  function startZeichnen(e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) {
    e.preventDefault()
    const pos = getPos(e)
    letzterPunkt.current = pos
    const ctx = canvasRef.current!.getContext('2d')!
    ctx.beginPath()
    ctx.moveTo(pos.x, pos.y)
    setZeichnen(true)
  }

  function weiterZeichnen(e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) {
    e.preventDefault()
    if (!zeichnen || !letzterPunkt.current) return
    const ctx = canvasRef.current!.getContext('2d')!
    const curr = getPos(e)
    const prev = letzterPunkt.current
    const mid = { x: (prev.x + curr.x) / 2, y: (prev.y + curr.y) / 2 }
    ctx.quadraticCurveTo(prev.x, prev.y, mid.x, mid.y)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(mid.x, mid.y)
    letzterPunkt.current = curr
    setHatInhalt(true)
  }

  function stopZeichnen() { setZeichnen(false); letzterPunkt.current = null }

  function leeren() {
    const canvas = canvasRef.current!
    const dpr = window.devicePixelRatio || 1
    canvas.getContext('2d')!.clearRect(0, 0, canvas.width / dpr, canvas.height / dpr)
    setHatInhalt(false)
  }

  function uebernehmenZeichnen() {
    const canvas = canvasRef.current!
    const out = document.createElement('canvas')
    out.width = canvas.width; out.height = canvas.height
    const ctx = out.getContext('2d')!
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, out.width, out.height)
    ctx.drawImage(canvas, 0, 0)
    onSpeichern(out.toDataURL('image/png'))
  }

  const fileRef = useRef<HTMLInputElement>(null)
  const [uploadVorschau, setUploadVorschau] = useState<string | null>(null)
  const [uploadFehler, setUploadFehler] = useState<string | null>(null)

  function handleDatei(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.match(/^image\/(jpeg|png|webp)$/)) {
      setUploadFehler('Nur JPG, PNG oder WebP erlaubt.')
      return
    }
    const reader = new FileReader()
    reader.onload = (ev) => { setUploadVorschau(ev.target?.result as string); setUploadFehler(null) }
    reader.readAsDataURL(file)
    e.target.value = ''
  }

  const tabCls = (aktiv: boolean) =>
    `px-4 py-2 text-sm font-medium rounded-lg transition-colors ${aktiv
      ? 'bg-blue-600 text-white'
      : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'}`

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-lg space-y-4 p-6">
        <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">Digitale Unterschrift</h2>

        <div className="flex gap-2 p-1 bg-slate-100 dark:bg-slate-700 rounded-lg w-fit">
          <button type="button" className={tabCls(modus === 'zeichnen')} onClick={() => setModus('zeichnen')}>Zeichnen</button>
          <button type="button" className={tabCls(modus === 'hochladen')} onClick={() => setModus('hochladen')}>Datei hochladen</button>
        </div>

        {modus === 'zeichnen' ? (
          <>
            <p className="text-sm text-slate-500 dark:text-slate-400">Unterschrift im Feld unten einzeichnen (Maus oder Touchscreen).</p>
            <canvas
              ref={canvasRef}
              style={{ height: '220px' }}
              className="w-full border-2 border-slate-300 dark:border-slate-600 rounded-xl bg-white cursor-crosshair touch-none"
              onMouseDown={startZeichnen}
              onMouseMove={weiterZeichnen}
              onMouseUp={stopZeichnen}
              onMouseLeave={stopZeichnen}
              onTouchStart={startZeichnen}
              onTouchMove={weiterZeichnen}
              onTouchEnd={stopZeichnen}
            />
            <div className="flex gap-2 justify-between">
              <button type="button" onClick={leeren}
                className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300">
                Leeren
              </button>
              <div className="flex gap-2">
                <button type="button" onClick={onAbbrechen}
                  className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300">
                  Abbrechen
                </button>
                <button type="button" disabled={!hatInhalt} onClick={uebernehmenZeichnen}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg disabled:opacity-50">
                  Übernehmen
                </button>
              </div>
            </div>
          </>
        ) : (
          <>
            <p className="text-sm text-slate-500 dark:text-slate-400">JPG oder PNG hochladen (z.B. eingescannte Unterschrift).</p>
            <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={handleDatei} />
            <div
              onClick={() => fileRef.current?.click()}
              className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-slate-300 dark:border-slate-600 rounded-xl h-40 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            >
              {uploadVorschau
                ? <img src={uploadVorschau} alt="Vorschau" className="max-h-36 max-w-full object-contain rounded" />
                : <><span className="text-3xl">📁</span><span className="text-sm text-slate-500 dark:text-slate-400">Klicken zum Auswählen</span></>
              }
            </div>
            {uploadFehler && <p className="text-sm text-red-600 dark:text-red-400">{uploadFehler}</p>}
            <div className="flex gap-2 justify-end">
              <button type="button" onClick={onAbbrechen}
                className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300">
                Abbrechen
              </button>
              <button type="button" disabled={!uploadVorschau} onClick={() => uploadVorschau && onSpeichern(uploadVorschau)}
                className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg disabled:opacity-50">
                Übernehmen
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function UnterschriftSektion({ data }: { data: Unternehmen }) {
  const qc = useQueryClient()
  const [zeigModal, setZeigModal] = useState(false)
  const [vorschau, setVorschau] = useState<string>(data.unterschrift_bild ?? '')
  const [aufRechnung, setAufRechnung] = useState(!!data.unterschrift_auf_rechnung)
  const [gespeichert, setGespeichert] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)

  const toggleMut = useMutation({
    mutationFn: (val: boolean) => updateUnternehmen({ unterschrift_auf_rechnung: val }),
    onSuccess: (_, val) => {
      setAufRechnung(val)
      qc.invalidateQueries({ queryKey: ['unternehmen'] })
    },
  })

  const mut = useMutation({
    mutationFn: (bild: string | null) => updateUnternehmen({ unterschrift_bild: bild }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['unternehmen'] })
      setGespeichert(true)
      setFehler(null)
      setTimeout(() => setGespeichert(false), 2500)
    },
    onError: (e: Error) => setFehler(e.message),
  })

  function handleSpeichern(bild: string) {
    setVorschau(bild)
    setZeigModal(false)
    mut.mutate(bild)
  }

  function handleEntfernen() {
    setVorschau('')
    mut.mutate(null)
  }

  return (
    <div className="space-y-4">
      {zeigModal && (
        <UnterschriftModal
          onSpeichern={handleSpeichern}
          onAbbrechen={() => setZeigModal(false)}
        />
      )}
      <p className="text-sm text-slate-500 dark:text-slate-400">
        Einmal hinterlegen – wird automatisch in Tagesabschluss-PDFs eingebettet.
      </p>
      <label className="flex items-center gap-2 cursor-pointer w-fit">
        <input
          type="checkbox"
          checked={aufRechnung}
          onChange={e => toggleMut.mutate(e.target.checked)}
          className="w-4 h-4 rounded accent-blue-600"
        />
        <span className="text-sm text-slate-700 dark:text-slate-200">Unterschrift auf Rechnungen anzeigen</span>
      </label>
      <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white p-4 min-h-[100px] flex items-center justify-center">
        {vorschau
          ? <img src={vorschau} alt="Unterschrift" className="max-h-24 max-w-full" />
          : <span className="text-sm text-slate-300 dark:text-slate-600 italic">Noch keine Unterschrift hinterlegt</span>
        }
      </div>
      <div className="flex gap-2 items-center">
        <button type="button" onClick={() => setZeigModal(true)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg">
          {vorschau ? 'Unterschrift ändern' : 'Unterschrift zeichnen'}
        </button>
        {vorschau && (
          <>
            <a
              href={vorschau}
              download="unterschrift.png"
              className="px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
            >
              Speichern
            </a>
            <button type="button" onClick={handleEntfernen}
              className="px-3 py-2 text-sm border border-red-200 rounded-lg hover:bg-red-50 text-red-600">
              Entfernen
            </button>
          </>
        )}
        {gespeichert && <span className="text-sm text-green-600 dark:text-green-400">✓ Gespeichert</span>}
        {fehler && <p className="text-sm text-red-600 dark:text-red-400">{fehler}</p>}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Haupt-Seite
// ---------------------------------------------------------------------------

export function UnternehmenPage() {
  const [activeTab, setActiveTab] = useState<TabId>('firma')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['unternehmen'],
    queryFn: getUnternehmen,
  })

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-slate-200 rounded w-48" />
          <div className="h-10 bg-slate-100 rounded-xl" />
          <div className="h-64 bg-slate-100 rounded-2xl" />
        </div>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="p-6">
        <p className="text-red-600 dark:text-red-400 text-sm">Unternehmensdaten konnten nicht geladen werden.</p>
      </div>
    )
  }

  const isFormTab = activeTab === 'firma' || activeTab === 'steuer' || activeTab === 'rechnungen' || activeTab === 'artikel'

  return (
    <div className="p-6 max-w-4xl space-y-0">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">Unternehmen</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm">Stammdaten, Steuer, Rechnungseinstellungen und Kommunikation</p>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <TabNav active={activeTab} onChange={setActiveTab} />

        <div className="p-6">
          {/* Firma / Steuer / Rechnungen teilen sich FirmendatenSektion – immer gemountet damit State erhalten bleibt */}
          <div className={isFormTab ? '' : 'hidden'}>
            <FirmendatenSektion data={data} activeTab={activeTab} />
          </div>

          {activeTab === 'email' && <EmailSektion data={data} />}
          {activeTab === 'unterschrift' && <UnterschriftSektion data={data} />}
        </div>
      </div>
    </div>
  )
}
