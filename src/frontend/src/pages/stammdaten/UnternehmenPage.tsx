import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getUnternehmen, updateUnternehmen, uploadLogo, deleteLogo, getLogoUrl,
  type Unternehmen,
} from '../../api/client'

// ---------------------------------------------------------------------------
// Hilfskomponenten
// ---------------------------------------------------------------------------

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      {children}
    </div>
  )
}

const inputCls = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
const selectCls = `${inputCls} bg-white`

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
      <div className="w-28 h-20 rounded-xl border-2 border-dashed border-slate-300 flex items-center justify-center overflow-hidden bg-slate-50 flex-shrink-0">
        {logoVorhanden ? (
          <img
            src={`${getLogoUrl()}?v=${cacheBust}`}
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
          className="px-4 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50 text-slate-700 disabled:opacity-50"
        >
          {uploadMut.isPending ? 'Lädt…' : logoVorhanden ? 'Logo ändern' : 'Logo hochladen'}
        </button>
        {logoVorhanden && (
          <button
            type="button"
            onClick={() => deleteMut.mutate()}
            disabled={deleteMut.isPending}
            className="px-4 py-2 text-sm border border-red-200 rounded-lg hover:bg-red-50 text-red-600 disabled:opacity-50"
          >
            {deleteMut.isPending ? '…' : 'Entfernen'}
          </button>
        )}
        <p className="text-xs text-slate-400">PNG, JPEG oder WEBP · max. 2 MB</p>
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

  function set(key: keyof Unternehmen, value: string | boolean) {
    setForm(f => ({ ...f, [key]: value }))
  }

  function handleSpeichern(e: React.FormEvent) {
    e.preventDefault()
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
        <h3 className="text-sm font-semibold text-slate-600 uppercase tracking-wide">Firmendaten</h3>
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
        <h3 className="text-sm font-semibold text-slate-600 uppercase tracking-wide">Steuer</h3>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Steuernummer">{inp('steuernummer', '12/345/67890')}</Field>
          <Field label="Finanzamt">{inp('finanzamt', 'Finanzamt Berlin-Mitte')}</Field>
        </div>
        <Field label="USt-IdNr.">{inp('ust_idnr', 'DE123456789')}</Field>

        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={!!form.ist_kleinunternehmer}
            onChange={ev => set('ist_kleinunternehmer', ev.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600"
          />
          <div>
            <span className="text-sm font-medium text-slate-700">Kleinunternehmer (§19 UStG)</span>
            <p className="text-xs text-slate-500 mt-0.5">Keine USt auf Rechnungen, kein Vorsteuerabzug.</p>
          </div>
        </label>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Versteuerungsart">
            <select
              value={form.versteuerungsart ?? 'ist'}
              onChange={ev => set('versteuerungsart', ev.target.value)}
              className={selectCls}
            >
              <option value="ist">Ist-Versteuerung</option>
              <option value="soll">Soll-Versteuerung</option>
            </select>
          </Field>
          <Field label="Kontenrahmen">
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

      {/* Handelsregister */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-600 uppercase tracking-wide">Handelsregister</h3>
        <p className="text-xs text-slate-400">Nur für GmbH, UG, AG etc. – Einzelunternehmer und Freiberufler leer lassen.</p>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Register-Nr.">{inp('handelsregister_nr', 'HRB 215517')}</Field>
          <Field label="Registergericht">{inp('handelsregister_gericht', 'Oldenburg')}</Field>
        </div>
      </div>

      <hr className="border-slate-100" />

      {/* Bank */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-600 uppercase tracking-wide">Bankverbindung</h3>
        <Field label="IBAN">{inp('iban', 'DE89 3704 0044 0532 0130 00')}</Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="BIC">{inp('bic', 'COBADEFFXXX')}</Field>
          <Field label="Bank">{inp('bank_name', 'Deutsche Bank')}</Field>
        </div>
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
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
        <p className="text-sm font-medium text-blue-800 mb-2">Verfügbare Platzhalter</p>
        <div className="grid grid-cols-2 gap-x-6 gap-y-1">
          {PLATZHALTER.map(p => (
            <div key={p.key} className="flex gap-2 text-xs">
              <code className="text-blue-700 font-mono whitespace-nowrap">{p.key}</code>
              <span className="text-blue-600">{p.desc}</span>
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
          className="px-4 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50 text-slate-600"
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
          <p className="text-sm font-medium text-slate-700">Vorschau</p>
          <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 min-h-32">
            <pre className="text-xs text-slate-600 whitespace-pre-wrap font-sans">{signatur || <span className="text-slate-300 italic">Noch kein Text eingegeben</span>}</pre>
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
          className="px-4 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50 text-slate-600"
        >
          Zurücksetzen
        </button>
        {gespeichert && <span className="text-sm text-green-600">✓ Gespeichert</span>}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Haupt-Seite
// ---------------------------------------------------------------------------

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100">
        <h2 className="font-semibold text-slate-800">{title}</h2>
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
        <h1 className="text-2xl font-bold text-slate-800 mb-1">Unternehmen</h1>
        <p className="text-slate-500 text-sm">Firmendaten, Logo und Mail-Vorlagen verwalten</p>
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
    </div>
  )
}
