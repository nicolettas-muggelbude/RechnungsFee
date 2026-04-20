import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getUnternehmen, updateUnternehmen, uploadLogo, deleteLogo, getLogoUrl,
  type Unternehmen,
} from '../../api/client'
import { InfoTooltip } from '../../components/InfoTooltip'

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
      {/* Vorschau */}
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

      {/* Aktionen */}
      <div className="flex flex-col gap-2">
        <input
          ref={fileRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
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
        <p className="text-xs text-slate-400 dark:text-slate-500">PNG, JPEG oder WEBP · max. 2 MB</p>
        {fehler && <p className="text-xs text-red-600">{fehler}</p>}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Firmendaten-Sektion
// ---------------------------------------------------------------------------

function FirmendatenSektion({ data }: { data: Unternehmen }) {
  const qc = useQueryClient()
  const [form, setForm] = useState<Partial<Unternehmen>>({ ...data })
  const [gespeichert, setGespeichert] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)

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

  function set(key: keyof Unternehmen, value: string | boolean | number) {
    setForm(f => ({ ...f, [key]: value }))
  }

  function handleSpeichern(e: React.FormEvent) {
    e.preventDefault()
    const ustId = (form.ust_idnr ?? '').trim()
    if (ustId) {
      // Basis-Formatprüfung: 2 Buchstaben Ländercode + mind. 2 Zeichen, max. 15
      if (!/^[A-Z]{2}[A-Z0-9+*]{2,13}$/i.test(ustId)) {
        setFehler('USt-IdNr. hat ein ungültiges Format (z.B. DE123456789).')
        return
      }
      // Deutschland: DE + genau 9 Ziffern
      if (ustId.toUpperCase().startsWith('DE') && !/^DE[0-9]{9}$/i.test(ustId)) {
        setFehler('Deutsche USt-IdNr. muss das Format DE + 9 Ziffern haben (z.B. DE123456789).')
        return
      }
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

  return (
    <form onSubmit={handleSpeichern} className="space-y-6">
      {/* Logo */}
      <LogoSektion
        logoVorhanden={!!data.logo_pfad}
        onUploaded={() => { /* Cache wird im Logo-Comp bereits invalidiert */ }}
        onDeleted={() => { /* dto */ }}
      />

      <hr className="border-slate-100" />

      {/* Kontaktdaten */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">Firmendaten</h3>
        <Field label="Firmen- oder Tätigkeitsname *">{inp('firmenname', 'z.B. Maria Muster Webdesign')}</Field>
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
      </div>

      <hr className="border-slate-100" />

      {/* Steuer */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">Steuer</h3>
        <div className="grid grid-cols-2 gap-4">
          <Field label={<>Steuernummer <InfoTooltip text="Deine Steuernummer vom Finanzamt (z.B. 12/345/67890). Muss auf Rechnungen nach §14 UStG angegeben werden, wenn keine USt-IdNr. vorhanden ist." /></>}>{inp('steuernummer', '12/345/67890')}</Field>
          <Field label="Finanzamt">{inp('finanzamt', 'Finanzamt Berlin-Mitte')}</Field>
        </div>
        <Field label={<>USt-IdNr. <InfoTooltip text="Umsatzsteuer-Identifikationsnummer (z.B. DE123456789) – benötigt für EU-Geschäfte (innergemeinschaftliche Lieferungen und Leistungen). Bei rein inländischen Geschäften genügt die Steuernummer." /></>}>{inp('ust_idnr', 'DE123456789')}</Field>

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
              <InfoTooltip text="Als Kleinunternehmer nach §19 UStG weist du keine Umsatzsteuer auf Rechnungen aus und kannst keine Vorsteuer abziehen. Voraussetzungen (ab 2025): Netto-Gesamtumsatz im Vorjahr ≤ 25.000 € und im laufenden Jahr unter 100.000 € netto. Wird die 100.000 €-Grenze unterjährig überschritten, endet die Kleinunternehmerregelung sofort mit diesem Umsatz." side="bottom" />
            </span>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Keine USt auf Rechnungen, kein Vorsteuerabzug.</p>
          </div>
        </label>

        <div className="grid grid-cols-2 gap-4">
          <Field label={<>Versteuerungsart <InfoTooltip text="Ist-Versteuerung: USt wird fällig wenn der Kunde zahlt. Soll-Versteuerung: USt ist bereits bei Rechnungsstellung fällig. Für die meisten Freiberufler und Kleinunternehmer gilt die Ist-Versteuerung – sie muss einmalig beim Finanzamt beantragt werden." /></>}>
            <select
              value={form.versteuerungsart ?? 'ist'}
              onChange={ev => set('versteuerungsart', ev.target.value)}
              className={selectCls}
            >
              <option value="ist">Ist-Versteuerung</option>
              <option value="soll">Soll-Versteuerung</option>
            </select>
          </Field>
          <Field label={<>Kontenrahmen <InfoTooltip text="SKR03: Standard für Dienstleister und Freiberufler. SKR04: Standard für Handel und produzierende Betriebe. SKR49: Für Vereine und Non-Profits. Beeinflusst Kontenzuordnung im GoBD-Export." /></>}>
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
        </div>

        <div className="grid grid-cols-2 gap-4">
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
      </div>

      <hr className="border-slate-100" />

      {/* Beruf & Kammer */}
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

      <hr className="border-slate-100" />

      {/* Handelsregister */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">Handelsregister</h3>
        <p className="text-xs text-slate-400 dark:text-slate-500">Wenn dein Unternehmen im Handelsregister eingetragen ist, ergänze Register-Nr. und Registergericht. Abteilung A (HRA) gilt für Einzelkaufleute und Personengesellschaften, Abteilung B (HRB) für Kapitalgesellschaften (GmbH, UG, AG). Nicht eingetragene Einzelunternehmer und Freiberufler lassen diese Felder leer.</p>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Register-Nr.">{inp('handelsregister_nr', 'z.B. HRA 12345 oder HRB 215517')}</Field>
          <Field label="Registergericht">{inp('handelsregister_gericht', 'Oldenburg')}</Field>
        </div>
      </div>

      <hr className="border-slate-100" />

      {/* Bank */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">Bankverbindung</h3>
        <Field label="IBAN">{inp('iban', 'DE89 3704 0044 0532 0130 00')}</Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="BIC">{inp('bic', 'COBADEFFXXX')}</Field>
          <Field label="Bank">{inp('bank_name', 'Deutsche Bank')}</Field>
        </div>
      </div>

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

        <label className={`flex items-start gap-3 ${form.iban?.trim() ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'}`}>
          <input
            type="checkbox"
            checked={!!form.qr_zahlung_aktiv}
            onChange={ev => set('qr_zahlung_aktiv', ev.target.checked)}
            disabled={!form.iban?.trim()}
            className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600 disabled:cursor-not-allowed"
          />
          <div>
            <span className="text-sm font-medium text-slate-700 dark:text-slate-200 flex items-center gap-1">
              GiroCode (QR) auf Rechnung
              {!form.iban?.trim() && (
                <InfoTooltip text="Bitte zuerst eine IBAN unter Bankverbindung hinterlegen – der QR-Code benötigt die Kontonummer für den EPC-Standard." />
              )}
            </span>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Fügt einen EPC-QR-Code (GiroCode) neben den Zahlungshinweis ein.
              Kunden können damit per Banking-App direkt überweisen – mit vorausgefüllten Daten.
              Nur auf Ausgangsrechnungen mit hinterlegter IBAN.
            </p>
          </div>
        </label>
      </div>

      {fehler && <p className="text-sm text-red-600">{fehler}</p>}

      <div className="flex items-center gap-3 pt-1">
        <button
          type="submit"
          disabled={mut.isPending}
          className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors"
        >
          {mut.isPending ? 'Speichern…' : 'Speichern'}
        </button>
        {gespeichert && <span className="text-sm text-green-600">✓ Gespeichert</span>}
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Mail-Vorlage-Sektion
// ---------------------------------------------------------------------------

const PLATZHALTER = [
  { key: '{rechnungsnummer}', desc: 'Rechnungsnummer' },
  { key: '{datum}',           desc: 'Rechnungsdatum (TT.MM.JJJJ)' },
  { key: '{betrag}',          desc: 'Bruttobetrag (z.B. 119,00 €)' },
  { key: '{faellig_am}',      desc: 'Fälligkeitsdatum' },
  { key: '{kunde}',           desc: 'Name des Empfängers' },
  { key: '{firmenname}',      desc: 'Dein Firmenname' },
]

const DEFAULT_BETREFF = 'Rechnung {rechnungsnummer}'
const DEFAULT_TEXT = `Hallo {kunde},

anbei findest du die Rechnung {rechnungsnummer} vom {datum}.

Betrag: {betrag}
Fällig am: {faellig_am}

Bitte überweise den Betrag auf das angegebene Konto.

Viele Grüße
{firmenname}`

function MailVorlageSektion({ data }: { data: Unternehmen }) {
  const qc = useQueryClient()
  const [betreff, setBetreff] = useState(data.mail_betreff_vorlage ?? DEFAULT_BETREFF)
  const [text, setText] = useState(data.mail_text_vorlage ?? DEFAULT_TEXT)
  const [gespeichert, setGespeichert] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)

  const mut = useMutation({
    mutationFn: () => updateUnternehmen({
      mail_betreff_vorlage: betreff,
      mail_text_vorlage: text,
    }),
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
      {/* Platzhalter-Legende */}
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

      <Field label="Betreff-Vorlage">
        <input
          type="text"
          value={betreff}
          onChange={ev => setBetreff(ev.target.value)}
          placeholder={DEFAULT_BETREFF}
          className={inputCls}
        />
      </Field>

      <Field label="Text-Vorlage">
        <textarea
          value={text}
          onChange={ev => setText(ev.target.value)}
          rows={10}
          placeholder={DEFAULT_TEXT}
          className={`${inputCls} resize-y font-mono text-xs`}
        />
      </Field>

      {fehler && <p className="text-sm text-red-600">{fehler}</p>}

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => mut.mutate()}
          disabled={mut.isPending}
          className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors"
        >
          {mut.isPending ? 'Speichern…' : 'Vorlage speichern'}
        </button>
        <button
          type="button"
          onClick={() => { setBetreff(DEFAULT_BETREFF); setText(DEFAULT_TEXT) }}
          className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
        >
          Zurücksetzen
        </button>
        {gespeichert && <span className="text-sm text-green-600">✓ Gespeichert</span>}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Mail-Signatur-Sektion
// ---------------------------------------------------------------------------

const DEFAULT_SIGNATUR = (firmenname: string) =>
  `--\n${firmenname}`

function SignaturSektion({ data }: { data: Unternehmen }) {
  const qc = useQueryClient()
  const [signatur, setSignatur] = useState(
    data.mail_signatur ?? DEFAULT_SIGNATUR(data.firmenname)
  )
  const [gespeichert, setGespeichert] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)

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
        {/* Bearbeitung */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-slate-700">Signatur-Text</label>
          <textarea
            value={signatur}
            onChange={ev => setSignatur(ev.target.value)}
            rows={8}
            className={`${inputCls} resize-y font-mono text-xs`}
            placeholder={DEFAULT_SIGNATUR(data.firmenname)}
          />
        </div>

        {/* Vorschau */}
        <div className="space-y-2">
          <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Vorschau</p>
          <div className="rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 p-4 min-h-32">
            <pre className="text-xs text-slate-600 dark:text-slate-300 whitespace-pre-wrap font-sans">{signatur || <span className="text-slate-300 dark:text-slate-600 italic">Noch kein Text eingegeben</span>}</pre>
          </div>
        </div>
      </div>

      {fehler && <p className="text-sm text-red-600">{fehler}</p>}

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
        {gespeichert && <span className="text-sm text-green-600">✓ Gespeichert</span>}
      </div>
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
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const letzterPunkt = useRef<{ x: number; y: number } | null>(null)
  const [zeichnen, setZeichnen] = useState(false)
  const [hatInhalt, setHatInhalt] = useState(false)

  // HiDPI: Canvas-Interne Auflösung = CSS-Größe × devicePixelRatio
  useEffect(() => {
    const canvas = canvasRef.current!
    const dpr = window.devicePixelRatio || 1
    const size = canvas.offsetWidth
    canvas.width = size * dpr
    canvas.height = size * dpr
    const ctx = canvas.getContext('2d')!
    ctx.scale(dpr, dpr)
    ctx.lineWidth = 4
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.strokeStyle = '#1e293b'
  }, [])

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
    // Glatte Kurve durch Mittelpunkt zwischen letztem und aktuellem Punkt
    const mid = { x: (prev.x + curr.x) / 2, y: (prev.y + curr.y) / 2 }
    ctx.quadraticCurveTo(prev.x, prev.y, mid.x, mid.y)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(mid.x, mid.y)
    letzterPunkt.current = curr
    setHatInhalt(true)
  }

  function stopZeichnen() {
    setZeichnen(false)
    letzterPunkt.current = null
  }

  function leeren() {
    const canvas = canvasRef.current!
    const dpr = window.devicePixelRatio || 1
    canvas.getContext('2d')!.clearRect(0, 0, canvas.width / dpr, canvas.height / dpr)
    setHatInhalt(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-2xl space-y-4 p-6">
        <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">Unterschrift zeichnen</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400">Zeichne deine Unterschrift im weißen Feld.</p>
        <canvas
          ref={canvasRef}
          className="w-full aspect-square border-2 border-slate-300 dark:border-slate-600 rounded-xl bg-white cursor-crosshair touch-none"
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
            <button type="button" disabled={!hatInhalt}
              onClick={() => {
                const canvas = canvasRef.current!
                const out = document.createElement('canvas')
                out.width = canvas.width
                out.height = canvas.height
                const ctx = out.getContext('2d')!
                ctx.fillStyle = '#ffffff'
                ctx.fillRect(0, 0, out.width, out.height)
                ctx.drawImage(canvas, 0, 0)
                onSpeichern(out.toDataURL('image/png'))
              }}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg disabled:opacity-50">
              Übernehmen
            </button>
          </div>
        </div>
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
          <button type="button" onClick={handleEntfernen}
            className="px-3 py-2 text-sm border border-red-200 rounded-lg hover:bg-red-50 text-red-600">
            Entfernen
          </button>
        )}
        {gespeichert && <span className="text-sm text-green-600">✓ Gespeichert</span>}
        {fehler && <p className="text-sm text-red-600">{fehler}</p>}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Haupt-Seite
// ---------------------------------------------------------------------------

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700">
        <h2 className="font-semibold text-slate-800 dark:text-slate-100">{title}</h2>
      </div>
      <div className="p-6">{children}</div>
    </div>
  )
}

export function UnternehmenPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['unternehmen'],
    queryFn: getUnternehmen,
  })

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-slate-200 rounded w-48" />
          <div className="h-64 bg-slate-100 rounded-2xl" />
        </div>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="p-6">
        <p className="text-red-600 text-sm">Unternehmensdaten konnten nicht geladen werden.</p>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">Unternehmen</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm">Firmendaten, Logo und Mail-Vorlagen verwalten</p>
      </div>

      <Card title="Firmendaten & Logo">
        <FirmendatenSektion data={data} />
      </Card>

      <Card title="Mail-Vorlage">
        <MailVorlageSektion data={data} />
      </Card>

      <Card title="Mail-Signatur">
        <SignaturSektion data={data} />
      </Card>

      <Card title="Digitale Unterschrift">
        <UnterschriftSektion data={data} />
      </Card>
    </div>
  )
}
