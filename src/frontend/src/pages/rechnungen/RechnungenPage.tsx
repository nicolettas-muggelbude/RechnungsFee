import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getRechnungen, createRechnung, updateRechnung, deleteRechnung, barZahlungErstellen,
  getKunden, getLieferanten, getKategorien, getUnternehmen,
  type Rechnung, type RechnungCreate, type RechnungspositionCreate, type BarZahlungCreate,
} from '../../api/client'

// ---------------------------------------------------------------------------
// Hilfsfunktionen
// ---------------------------------------------------------------------------

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
// Status-Badge
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: 'offen' | 'teilweise' | 'bezahlt' }) {
  const cfg = {
    offen:     { cls: 'bg-red-50 text-red-700 border-red-200',    label: 'Offen' },
    teilweise: { cls: 'bg-amber-50 text-amber-700 border-amber-200', label: 'Teilweise' },
    bezahlt:   { cls: 'bg-green-50 text-green-700 border-green-200', label: 'Bezahlt' },
  }[status]
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${cfg.cls}`}>
      {cfg.label}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Zahlungs-Dialog
// ---------------------------------------------------------------------------

function ZahlungsDialog({
  rechnung,
  onClose,
  onSuccess,
}: {
  rechnung: Rechnung
  onClose: () => void
  onSuccess: () => void
}) {
  const qc = useQueryClient()
  const restbetrag = parseFloat(rechnung.brutto_gesamt) - parseFloat(rechnung.bezahlt_betrag)
  const [betrag, setBetrag] = useState(restbetrag.toFixed(2).replace('.', ','))
  const [datum, setDatum] = useState(heuteIso())
  const [zahlungsart, setZahlungsart] = useState<'Bar' | 'Karte' | 'PayPal'>('Bar')
  const [beschreibung, setBeschreibung] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: (data: BarZahlungCreate) => barZahlungErstellen(rechnung.id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
      qc.invalidateQueries({ queryKey: ['kassenbuch'] })
      onSuccess()
    },
    onError: (e: Error) => setFehler(e.message),
  })

  const betragDecimal = parseFloat(betrag.replace(',', '.'))
  const artLabel = rechnung.typ === 'ausgang' ? 'Einnahme' : 'Ausgabe'

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (isNaN(betragDecimal) || betragDecimal <= 0) {
      setFehler('Bitte einen gültigen Betrag eingeben.')
      return
    }
    mutation.mutate({
      betrag: betragDecimal.toFixed(2),
      datum,
      zahlungsart,
      beschreibung: beschreibung || undefined,
    })
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">
            {rechnung.typ === 'ausgang' ? 'Bar kassieren' : 'Bar bezahlen'}
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl">×</button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Rechnungsinfo */}
          <div className="bg-slate-50 rounded-xl p-3 text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-500">Rechnung</span>
              <span className="font-medium">{rechnung.rechnungsnummer}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Gesamt</span>
              <span className="font-medium">{formatEuro(rechnung.brutto_gesamt)}</span>
            </div>
            {parseFloat(rechnung.bezahlt_betrag) > 0 && (
              <div className="flex justify-between text-green-700">
                <span>Bereits bezahlt</span>
                <span>{formatEuro(rechnung.bezahlt_betrag)}</span>
              </div>
            )}
            <div className="flex justify-between font-semibold border-t border-slate-200 pt-1 mt-1">
              <span className="text-slate-600">Restbetrag</span>
              <span>{formatEuro(restbetrag)}</span>
            </div>
          </div>

          {/* Betrag */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Betrag (€)</label>
            <input
              type="text"
              value={betrag}
              onChange={(e) => setBetrag(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="0,00"
            />
          </div>

          {/* Datum */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Zahlungsdatum</label>
            <input
              type="date"
              value={datum}
              onChange={(e) => setDatum(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Zahlungsart */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Zahlungsart</label>
            <div className="flex rounded-lg border border-slate-300 overflow-hidden text-sm">
              {(['Bar', 'Karte', 'PayPal'] as const).map((z) => (
                <button
                  key={z}
                  type="button"
                  onClick={() => setZahlungsart(z)}
                  className={`flex-1 py-2 transition-colors ${
                    zahlungsart === z
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {z}
                </button>
              ))}
            </div>
          </div>

          {/* Beschreibung (optional) */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Beschreibung <span className="text-slate-400 font-normal">(optional)</span>
            </label>
            <input
              type="text"
              value={beschreibung}
              onChange={(e) => setBeschreibung(e.target.value)}
              placeholder={`Zahlung ${rechnung.rechnungsnummer ?? ''}`}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Vorschau */}
          {!isNaN(betragDecimal) && betragDecimal > 0 && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 text-sm">
              <p className="text-blue-700 font-medium">Kassenbuchung wird erstellt:</p>
              <p className="text-blue-600 mt-0.5">
                {artLabel} {formatEuro(betragDecimal)} via {zahlungsart}
              </p>
            </div>
          )}

          {fehler && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {fehler}
            </p>
          )}

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50"
            >
              Abbrechen
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
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
}: {
  rechnung: Rechnung
  onClose: () => void
  onEdit: () => void
  onDelete: () => void
}) {
  const [zahlungsDialog, setZahlungsDialog] = useState(false)
  const qc = useQueryClient()

  const restbetrag = parseFloat(rechnung.brutto_gesamt) - parseFloat(rechnung.bezahlt_betrag)
  const fortschritt = parseFloat(rechnung.brutto_gesamt) > 0
    ? Math.min((parseFloat(rechnung.bezahlt_betrag) / parseFloat(rechnung.brutto_gesamt)) * 100, 100)
    : 0

  const hatZahlungsoption = restbetrag > 0.004

  return (
    <div className="border-l border-slate-200 bg-white h-full overflow-auto flex flex-col">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <p className="font-semibold text-slate-800">{rechnung.rechnungsnummer ?? '(keine Nummer)'}</p>
          <p className="text-xs text-slate-400">{rechnung.typ === 'ausgang' ? 'Ausgangsrechnung' : 'Eingangsrechnung'}</p>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl">×</button>
      </div>

      <div className="p-5 space-y-5 flex-1">
        {/* Stammdaten */}
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-500">Partner</span>
            <span className="text-right font-medium text-slate-800">
              {rechnung.typ === 'ausgang'
                ? (rechnung.kunde_name ?? rechnung.partner_freitext ?? '—')
                : (rechnung.lieferant_name ?? rechnung.partner_freitext ?? '—')}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Datum</span>
            <span>{formatDatum(rechnung.datum)}</span>
          </div>
          {rechnung.faellig_am && (
            <div className="flex justify-between">
              <span className="text-slate-500">Fällig am</span>
              <span className={
                rechnung.zahlungsstatus !== 'bezahlt' && rechnung.faellig_am < heuteIso()
                  ? 'text-red-600 font-medium'
                  : ''
              }>{formatDatum(rechnung.faellig_am)}</span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-slate-500">Status</span>
            <StatusBadge status={rechnung.zahlungsstatus} />
          </div>
        </div>

        {/* Positionen */}
        {rechnung.positionen.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Positionen</p>
            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <table className="w-full text-xs">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-slate-500 font-medium">Beschreibung</th>
                    <th className="px-3 py-2 text-right text-slate-500 font-medium">Netto</th>
                    <th className="px-3 py-2 text-right text-slate-500 font-medium">USt</th>
                    <th className="px-3 py-2 text-right text-slate-500 font-medium">Brutto</th>
                  </tr>
                </thead>
                <tbody>
                  {rechnung.positionen.map((pos) => (
                    <tr key={pos.id} className="border-t border-slate-100">
                      <td className="px-3 py-2 text-slate-700">
                        {pos.beschreibung}
                        {parseFloat(pos.menge) !== 1 && (
                          <span className="text-slate-400"> × {pos.menge} {pos.einheit}</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right">{formatEuro(pos.netto)}</td>
                      <td className="px-3 py-2 text-right text-slate-400">{pos.ust_satz}%</td>
                      <td className="px-3 py-2 text-right font-medium">{formatEuro(pos.brutto)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-slate-50 border-t border-slate-200">
                  <tr>
                    <td colSpan={3} className="px-3 py-2 text-right text-slate-500 font-medium">Gesamt</td>
                    <td className="px-3 py-2 text-right font-bold text-slate-800">{formatEuro(rechnung.brutto_gesamt)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}

        {/* Zahlungsstatus */}
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Zahlung</p>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">Bezahlt</span>
              <span className="font-medium">{formatEuro(rechnung.bezahlt_betrag)}</span>
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
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
            <div className="flex justify-between text-xs text-slate-400">
              <span>0 €</span>
              <span>{formatEuro(rechnung.brutto_gesamt)}</span>
            </div>
          </div>
        </div>

        {/* Verknüpfte Zahlungen */}
        {rechnung.zahlungen.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              Verknüpfte Kassenbuchungen
            </p>
            <div className="space-y-1">
              {rechnung.zahlungen.map((z) => (
                <div key={z.id} className="flex items-center justify-between text-sm bg-slate-50 rounded-lg px-3 py-2">
                  <div>
                    <span className="font-mono text-xs text-slate-400 mr-2">{z.belegnr}</span>
                    <span className="text-slate-600">{formatDatum(z.datum)}</span>
                    <span className="ml-1.5 text-xs text-slate-400">{z.zahlungsart}</span>
                  </div>
                  <span className={`font-medium ${z.art === 'Einnahme' ? 'text-green-600' : 'text-red-600'}`}>
                    {z.art === 'Ausgabe' ? '−' : '+'}{formatEuro(z.brutto_betrag)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {rechnung.notizen && (
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Notizen</p>
            <p className="text-sm text-slate-600 bg-slate-50 rounded-lg px-3 py-2">{rechnung.notizen}</p>
          </div>
        )}
      </div>

      {/* Aktionen */}
      <div className="p-5 border-t border-slate-100 space-y-2">
        {hatZahlungsoption && (
          <button
            onClick={() => setZahlungsDialog(true)}
            className="w-full py-2.5 text-sm font-medium bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors"
          >
            {rechnung.typ === 'ausgang' ? 'Bar kassieren' : 'Bar bezahlen'}
            {rechnung.zahlungsstatus === 'teilweise' && ` (Restbetrag ${formatEuro(restbetrag)})`}
          </button>
        )}
        {!rechnung.immutable && (
          <>
            <button
              onClick={onEdit}
              className="w-full py-2 text-sm border border-slate-300 rounded-xl hover:bg-slate-50 transition-colors"
            >
              Bearbeiten
            </button>
            {rechnung.zahlungen.length === 0 && (
              <button
                onClick={onDelete}
                className="w-full py-2 text-sm text-red-600 border border-red-200 rounded-xl hover:bg-red-50 transition-colors"
              >
                Löschen
              </button>
            )}
          </>
        )}
      </div>

      {zahlungsDialog && (
        <ZahlungsDialog
          rechnung={rechnung}
          onClose={() => setZahlungsDialog(false)}
          onSuccess={() => setZahlungsDialog(false)}
        />
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
}

const leerPosition = (defaultUst = '19'): Positionszeile => ({
  beschreibung: '',
  menge: '1',
  einheit: 'Stück',
  netto: '',
  ust_satz: defaultUst,
})

function RechnungForm({
  typ,
  initial,
  onSave,
  onCancel,
}: {
  typ: 'eingang' | 'ausgang'
  initial?: Rechnung
  onSave: (data: RechnungCreate) => void
  onCancel: () => void
}) {
  const { data: kunden } = useQuery({ queryKey: ['kunden'], queryFn: getKunden })
  const { data: lieferanten } = useQuery({ queryKey: ['lieferanten'], queryFn: getLieferanten })
  const { data: kategorien } = useQuery({ queryKey: ['kategorien'], queryFn: getKategorien })
  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen, staleTime: 1000 * 60 * 10 })

  const istKleinunternehmer = unternehmen?.ist_kleinunternehmer ?? false

  const [rechnungsnummer, setRechnungsnummer] = useState(initial?.rechnungsnummer ?? '')
  const [datum, setDatum] = useState(initial?.datum ?? heuteIso())
  const [faelligAm, setFaelligAm] = useState(initial?.faellig_am ?? '')
  const [partnerId, setPartnerId] = useState<string>(
    typ === 'ausgang'
      ? String(initial?.kunde_id ?? '')
      : String(initial?.lieferant_id ?? '')
  )
  const [partnerFreitext, setPartnerFreitext] = useState(initial?.partner_freitext ?? '')
  const [kategorieId, setKategorieId] = useState<string>(String(initial?.kategorie_id ?? ''))
  const [notizen, setNotizen] = useState(initial?.notizen ?? '')
  const [positionen, setPositionen] = useState<Positionszeile[]>(
    initial?.positionen?.map((p) => ({
      beschreibung: p.beschreibung,
      menge: p.menge,
      einheit: p.einheit,
      netto: p.netto,
      ust_satz: p.ust_satz,
    })) ?? [leerPosition()]
  )

  const partnerListe = typ === 'ausgang' ? (kunden ?? []) : (lieferanten ?? [])

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

  // USt-Satz aller Positionen aus gewählter Kategorie ableiten
  useEffect(() => {
    if (!kategorieId || !kategorien) return
    const kat = kategorien.find((k) => String(k.id) === kategorieId)
    if (!kat) return
    const neuerUst = istKleinunternehmer ? '0' : String(kat.ust_satz_standard)
    setPositionen((prev) => prev.map((p) => ({ ...p, ust_satz: neuerUst })))
  }, [kategorieId, kategorien, istKleinunternehmer])

  // Kategorie-Gruppen analog BuchungForm
  const alle = kategorien ?? []
  const erloeseKat = alle.filter(
    (k) =>
      k.kontenart === 'Erlös' &&
      (istKleinunternehmer
        ? k.name === 'Kleinunternehmer-Einnahmen'
        : k.name !== 'Kleinunternehmer-Einnahmen')
  )
  const aufwandKat = alle.filter((k) => k.kontenart === 'Aufwand')
  const anlageKat  = alle.filter((k) => k.kontenart === 'Anlage')

  const kategorieOptionen = typ === 'ausgang' ? (
    <>
      <optgroup label="Erlöse">
        {erloeseKat.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
      </optgroup>
    </>
  ) : (
    <>
      <optgroup label="Betriebsausgaben">
        {aufwandKat.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
      </optgroup>
      {anlageKat.length > 0 && (
        <optgroup label="Investitionen">
          {anlageKat.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
        </optgroup>
      )}
    </>
  )

  // Summenberechnung
  const summen = positionen.reduce(
    (acc, p) => {
      const netto = parseFloat(p.netto.replace(',', '.')) || 0
      const menge = parseFloat(p.menge.replace(',', '.')) || 1
      const ust = parseFloat(p.ust_satz) || 0
      const nettoBrutto = netto * menge
      const ustBetrag = (nettoBrutto * ust) / 100
      return {
        netto: acc.netto + nettoBrutto,
        ust: acc.ust + ustBetrag,
        brutto: acc.brutto + nettoBrutto + ustBetrag,
      }
    },
    { netto: 0, ust: 0, brutto: 0 }
  )

  function updatePosition(i: number, field: keyof Positionszeile, value: string) {
    setPositionen((prev) => prev.map((p, idx) => (idx === i ? { ...p, [field]: value } : p)))
  }

  function addPosition() {
    const kat = (kategorien ?? []).find((k) => String(k.id) === kategorieId)
    const defaultUst = istKleinunternehmer ? '0' : (kat ? String(kat.ust_satz_standard) : '19')
    setPositionen((prev) => [...prev, leerPosition(defaultUst)])
  }

  function removePosition(i: number) {
    if (positionen.length <= 1) return
    setPositionen((prev) => prev.filter((_, idx) => idx !== i))
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const data: RechnungCreate = {
      typ,
      rechnungsnummer: rechnungsnummer || undefined,
      datum,
      faellig_am: faelligAm || undefined,
      ...(typ === 'ausgang' ? { kunde_id: partnerId ? parseInt(partnerId) : undefined } : { lieferant_id: partnerId ? parseInt(partnerId) : undefined }),
      partner_freitext: partnerFreitext || undefined,
      kategorie_id: kategorieId ? parseInt(kategorieId) : undefined,
      notizen: notizen || undefined,
      positionen: positionen.map((p) => ({
        beschreibung: p.beschreibung,
        menge: p.menge || '1',
        einheit: p.einheit || 'Stück',
        netto: (parseFloat(p.netto.replace(',', '.')) || 0).toFixed(2),
        ust_satz: istKleinunternehmer ? '0' : (p.ust_satz || '0'),
      } as RechnungspositionCreate)),
    }
    onSave(data)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Rechnungsnummer <span className="text-slate-400 font-normal">(leer = auto)</span>
          </label>
          <input
            type="text"
            value={rechnungsnummer}
            onChange={(e) => setRechnungsnummer(e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="wird automatisch vergeben"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Datum *</label>
          <input
            type="date"
            required
            value={datum}
            onChange={(e) => setDatum(e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Fällig am</label>
          <input
            type="date"
            value={faelligAm}
            min={datum}
            onChange={(e) => setFaelligAm(e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Kategorie</label>
          <select
            value={kategorieId}
            onChange={(e) => setKategorieId(e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">— keine —</option>
            {kategorieOptionen}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          {typ === 'ausgang' ? 'Kunde' : 'Lieferant'}
        </label>
        <div className="flex gap-2">
          <select
            value={partnerId}
            onChange={(e) => { setPartnerId(e.target.value); if (e.target.value) setPartnerFreitext('') }}
            className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">— Stammdatensatz wählen oder Freitext —</option>
            {partnerListe.map((p: any) => (
              <option key={p.id} value={p.id}>
                {p.firmenname ?? [p.vorname, p.nachname].filter(Boolean).join(' ')}
              </option>
            ))}
          </select>
        </div>
        {!partnerId && (
          <input
            type="text"
            value={partnerFreitext}
            onChange={(e) => setPartnerFreitext(e.target.value)}
            placeholder="oder Name frei eingeben"
            className="mt-2 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        )}
      </div>

      {/* §19-Hinweis */}
      {istKleinunternehmer && (
        <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs text-amber-800">
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
          <label className="text-sm font-medium text-slate-700">Positionen *</label>
          <button
            type="button"
            onClick={addPosition}
            className="text-xs text-blue-600 hover:text-blue-700 font-medium"
          >
            + Position hinzufügen
          </button>
        </div>
        <div className="border border-slate-200 rounded-xl overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-3 py-2 text-left text-slate-500 font-medium">Beschreibung</th>
                <th className="px-3 py-2 text-right text-slate-500 font-medium w-16">Menge</th>
                <th className="px-3 py-2 text-left text-slate-500 font-medium w-20">Einheit</th>
                <th className="px-3 py-2 text-right text-slate-500 font-medium w-24">Netto (€)</th>
                <th className="px-3 py-2 text-right text-slate-500 font-medium w-16">USt %</th>
                <th className="px-3 py-2 w-8"></th>
              </tr>
            </thead>
            <tbody>
              {positionen.map((pos, i) => (
                <tr key={i} className="border-t border-slate-100">
                  <td className="px-2 py-1.5">
                    <input
                      required
                      type="text"
                      value={pos.beschreibung}
                      onChange={(e) => updatePosition(i, 'beschreibung', e.target.value)}
                      className="w-full border-0 outline-none bg-transparent text-slate-700 placeholder-slate-300"
                      placeholder="Beschreibung"
                    />
                  </td>
                  <td className="px-2 py-1.5">
                    <input
                      type="text"
                      value={pos.menge}
                      onChange={(e) => updatePosition(i, 'menge', e.target.value)}
                      className="w-full border-0 outline-none bg-transparent text-right text-slate-700"
                    />
                  </td>
                  <td className="px-2 py-1.5">
                    <input
                      type="text"
                      value={pos.einheit}
                      onChange={(e) => updatePosition(i, 'einheit', e.target.value)}
                      className="w-full border-0 outline-none bg-transparent text-slate-700"
                    />
                  </td>
                  <td className="px-2 py-1.5">
                    <input
                      required
                      type="text"
                      value={pos.netto}
                      onChange={(e) => updatePosition(i, 'netto', e.target.value)}
                      className="w-full border-0 outline-none bg-transparent text-right text-slate-700"
                      placeholder="0,00"
                    />
                  </td>
                  <td className="px-2 py-1.5">
                    <select
                      value={pos.ust_satz}
                      onChange={(e) => updatePosition(i, 'ust_satz', e.target.value)}
                      disabled={istKleinunternehmer}
                      className="w-full border-0 outline-none bg-transparent text-right text-slate-700 disabled:text-slate-400 disabled:cursor-not-allowed"
                    >
                      <option value="0">{istKleinunternehmer ? '0 (§19)' : '0'}</option>
                      {!istKleinunternehmer && <option value="7">7</option>}
                      {!istKleinunternehmer && <option value="19">19</option>}
                    </select>
                  </td>
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
            <tfoot className="bg-slate-50 border-t border-slate-200">
              <tr>
                <td colSpan={4} className="px-3 py-2 text-right text-slate-500 text-xs">Netto</td>
                <td colSpan={2} className="px-3 py-2 text-right font-medium text-slate-700">{formatEuro(summen.netto)}</td>
              </tr>
              <tr>
                <td colSpan={4} className="px-3 py-2 text-right text-slate-500 text-xs">USt</td>
                <td colSpan={2} className="px-3 py-2 text-right text-slate-600">{formatEuro(summen.ust)}</td>
              </tr>
              <tr>
                <td colSpan={4} className="px-3 py-2 text-right font-semibold text-slate-700">Brutto</td>
                <td colSpan={2} className="px-3 py-2 text-right font-bold text-slate-800">{formatEuro(summen.brutto)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Notizen</label>
        <textarea
          value={notizen}
          onChange={(e) => setNotizen(e.target.value)}
          rows={2}
          className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          placeholder="Optionale Bemerkungen"
        />
      </div>

      <div className="flex gap-3">
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 px-4 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50"
        >
          Abbrechen
        </button>
        <button
          type="submit"
          className="flex-1 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          {initial ? 'Speichern' : 'Rechnung anlegen'}
        </button>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Haupt-Seite
// ---------------------------------------------------------------------------

export function RechnungenPage() {
  const qc = useQueryClient()
  const [typ, setTyp] = useState<'eingang' | 'ausgang'>('ausgang')
  const [zahlungsstatus, setZahlungsstatus] = useState('')
  const [monat, setMonat] = useState(aktuellerMonat())
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [formModus, setFormModus] = useState<'neu' | 'bearbeiten' | null>(null)
  const [fehler, setFehler] = useState<string | null>(null)

  const { data: rechnungen, isLoading } = useQuery({
    queryKey: ['rechnungen', typ, zahlungsstatus, monat],
    queryFn: () => getRechnungen({ typ, zahlungsstatus: zahlungsstatus || undefined, monat }),
  })

  const selectedRechnung = rechnungen?.find((r) => r.id === selectedId) ?? null

  const createMutation = useMutation({
    mutationFn: createRechnung,
    onSuccess: (r) => {
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
      setSelectedId(null)
      setFehler(null)
    },
    onError: (e: Error) => setFehler(e.message),
  })

  const liste = rechnungen ?? []

  // Summen
  const gesamt = liste.reduce(
    (acc, r) => ({
      brutto: acc.brutto + parseFloat(r.brutto_gesamt),
      bezahlt: acc.bezahlt + parseFloat(r.bezahlt_betrag),
    }),
    { brutto: 0, bezahlt: 0 }
  )

  return (
    <div className="flex h-full">
      {/* Linke Spalte */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="p-6 pb-4">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <h2 className="text-2xl font-bold text-slate-800">Rechnungen</h2>
            <button
              onClick={() => { setFormModus('neu'); setSelectedId(null) }}
              className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors"
            >
              + Neue Rechnung
            </button>
          </div>

          {/* Tabs + Filter */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Eingang/Ausgang */}
            <div className="flex rounded-lg border border-slate-300 overflow-hidden text-sm">
              {(['ausgang', 'eingang'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => { setTyp(t); setSelectedId(null) }}
                  className={`px-4 py-1.5 transition-colors ${
                    typ === t ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {t === 'ausgang' ? 'Ausgang' : 'Eingang'}
                </button>
              ))}
            </div>

            {/* Zahlungsstatus */}
            <select
              value={zahlungsstatus}
              onChange={(e) => setZahlungsstatus(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Alle Status</option>
              <option value="offen">Offen</option>
              <option value="teilweise">Teilweise bezahlt</option>
              <option value="bezahlt">Bezahlt</option>
            </select>

            {/* Monat */}
            <input
              type="month"
              value={monat}
              onChange={(e) => setMonat(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Fehlermeldung */}
          {fehler && (
            <div className="mt-3 bg-red-50 border border-red-200 rounded-xl px-4 py-2.5 text-sm text-red-700 flex items-center justify-between">
              <span>{fehler}</span>
              <button onClick={() => setFehler(null)} className="text-red-400 hover:text-red-600">×</button>
            </div>
          )}
        </div>

        {/* Kennzahlen */}
        {liste.length > 0 && (
          <div className="px-6 pb-3 grid grid-cols-3 gap-3">
            <div className="bg-white rounded-xl border border-slate-200 p-3">
              <p className="text-xs text-slate-500 mb-0.5">Rechnungen</p>
              <p className="text-lg font-bold text-slate-800">{liste.length}</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-3">
              <p className="text-xs text-slate-500 mb-0.5">Gesamt</p>
              <p className="text-lg font-bold text-slate-800">{formatEuro(gesamt.brutto)}</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-3">
              <p className="text-xs text-slate-500 mb-0.5">Offen</p>
              <p className="text-lg font-bold text-amber-600">{formatEuro(gesamt.brutto - gesamt.bezahlt)}</p>
            </div>
          </div>
        )}

        {/* Tabelle */}
        <div className="flex-1 overflow-auto px-6 pb-6">
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            {isLoading ? (
              <p className="p-5 text-slate-400 text-sm">Lade Rechnungen…</p>
            ) : liste.length === 0 ? (
              <p className="p-5 text-slate-400 text-sm">Keine Rechnungen im gewählten Zeitraum.</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-100">
                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Datum</th>
                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Nummer</th>
                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Partner</th>
                    <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Brutto</th>
                    <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {liste.map((r) => (
                    <tr
                      key={r.id}
                      onClick={() => { setSelectedId(r.id); setFormModus(null) }}
                      className={`border-b border-slate-50 last:border-0 hover:bg-slate-50 cursor-pointer transition-colors ${
                        selectedId === r.id ? 'bg-blue-50/50' : ''
                      }`}
                    >
                      <td className="px-5 py-3 text-slate-500">{formatDatum(r.datum)}</td>
                      <td className="px-5 py-3 font-mono text-xs text-slate-400">
                        {r.rechnungsnummer ?? '—'}
                      </td>
                      <td className="px-5 py-3 text-slate-700">
                        {r.typ === 'ausgang'
                          ? (r.kunde_name ?? r.partner_freitext ?? '—')
                          : (r.lieferant_name ?? r.partner_freitext ?? '—')}
                        {r.faellig_am && r.zahlungsstatus !== 'bezahlt' && r.faellig_am < heuteIso() && (
                          <span className="ml-1.5 text-[10px] text-red-600 bg-red-50 border border-red-200 rounded px-1">
                            Überfällig
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3 text-right font-medium text-slate-800">
                        {formatEuro(r.brutto_gesamt)}
                      </td>
                      <td className="px-5 py-3 text-center">
                        <StatusBadge status={r.zahlungsstatus} />
                      </td>
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
        <div className="w-[480px] shrink-0 border-l border-slate-200 bg-white overflow-auto">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h3 className="font-semibold text-slate-800">
              {formModus === 'neu'
                ? `Neue ${typ === 'ausgang' ? 'Ausgangsrechnung' : 'Eingangsrechnung'}`
                : 'Rechnung bearbeiten'}
            </h3>
            <button onClick={() => setFormModus(null)} className="text-slate-400 hover:text-slate-600 text-xl">×</button>
          </div>
          <div className="p-6">
            <RechnungForm
              typ={formModus === 'bearbeiten' && selectedRechnung ? selectedRechnung.typ : typ}
              initial={formModus === 'bearbeiten' ? selectedRechnung ?? undefined : undefined}
              onSave={(data) => {
                if (formModus === 'bearbeiten' && selectedId) {
                  updateMutation.mutate({ id: selectedId, data })
                } else {
                  createMutation.mutate(data)
                }
              }}
              onCancel={() => setFormModus(null)}
            />
          </div>
        </div>
      )}

      {!formModus && selectedRechnung && (
        <div className="w-96 shrink-0">
          <RechnungDetail
            rechnung={selectedRechnung}
            onClose={() => setSelectedId(null)}
            onEdit={() => setFormModus('bearbeiten')}
            onDelete={() => {
              if (confirm('Rechnung wirklich löschen?')) {
                deleteMutation.mutate(selectedRechnung.id)
              }
            }}
          />
        </div>
      )}
    </div>
  )
}
