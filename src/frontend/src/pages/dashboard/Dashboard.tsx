import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getJournal, getUnternehmen, getKleinunternehmerUmsatz, getFaelligeRechnungen, pruefZM, getLagerwarnungListe, type Rechnung } from '../../api/client'
import { guardedDateChange } from '../../utils/dateInput'
import { dashboardFilter } from '../../store/filterStore'

function formatEuro(val: string | number): string {
  const n = typeof val === 'string' ? parseFloat(val) : val
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n)
}

function formatDatum(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

function aktuellerMonat(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function heuteIso(): string {
  return new Date().toISOString().slice(0, 10)
}

type FilterModus = 'monat' | 'datum' | 'zeitraum' | 'jahr'

// ---------------------------------------------------------------------------
// Zufluss-Monitor für Transferleistungen (Bürgergeld / ALG I)
// ---------------------------------------------------------------------------

// Bürgergeld 2026: § 11b SGB II – dreistufige Freibetragsberechnung
// Stufe 1:    0–100 €:   vollständig anrechnungsfrei (Grundfreibetrag)
// Stufe 2: 100–1000 €:   20 % Freibetrag auf diesen Anteil (max. 180 €)
// Stufe 3: 1000–1200 €:  10 % Freibetrag auf diesen Anteil (max. 20 €)
// Über 1200 €:           kein weiterer Freibetrag, vollständige Anrechnung
const GRUNDFREIBETRAG = 100
const GRENZE_20 = 1000
const OBERE_GRENZE = 1200   // ab hier: volle Anrechnung des Überschusses

function berechneEks(zufluss: number): { freibetrag: number; anrechenbar: number } {
  if (zufluss <= GRUNDFREIBETRAG) return { freibetrag: zufluss, anrechenbar: 0 }
  const stufe2 = Math.min(zufluss - GRUNDFREIBETRAG, GRENZE_20 - GRUNDFREIBETRAG) * 0.2
  const stufe3 = Math.min(Math.max(zufluss - GRENZE_20, 0), OBERE_GRENZE - GRENZE_20) * 0.1
  const freibetrag = GRUNDFREIBETRAG + stufe2 + stufe3
  return { freibetrag, anrechenbar: Math.max(0, zufluss - freibetrag) }
}

const DE_MONATE = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']

function getAbrechnungszeitraum(startMonat: string): { von: string; bis: string; label: string } | null {
  if (!/^\d{4}-\d{2}$/.test(startMonat)) return null
  const [sy, sm] = startMonat.split('-').map(Number)
  const now = new Date()
  const totalMonths = (now.getFullYear() - sy) * 12 + (now.getMonth() + 1 - sm)
  const idx = Math.max(0, Math.floor(totalMonths / 6))

  const vonMonatsIdx = sm - 1 + idx * 6  // 0-indexed, may exceed 11
  const vonJahr = sy + Math.floor(vonMonatsIdx / 12)
  const vonMonat = (vonMonatsIdx % 12) + 1

  const bisMonatsIdx = vonMonatsIdx + 5
  const bisJahr = sy + Math.floor(bisMonatsIdx / 12)
  const bisMonat = (bisMonatsIdx % 12) + 1
  const bisTag = new Date(bisJahr, bisMonat, 0).getDate()

  const von = `${vonJahr}-${String(vonMonat).padStart(2, '0')}-01`
  const bis = `${bisJahr}-${String(bisMonat).padStart(2, '0')}-${String(bisTag).padStart(2, '0')}`
  const label = vonJahr === bisJahr
    ? `${DE_MONATE[vonMonat - 1]}–${DE_MONATE[bisMonat - 1]} ${vonJahr}`
    : `${DE_MONATE[vonMonat - 1]} ${vonJahr} – ${DE_MONATE[bisMonat - 1]} ${bisJahr}`

  return { von, bis, label }
}

type ZuflussAnsicht = 'monat' | 'zeitraum'

function ZuflussMonitor({
  zufluss,
  zeitraumLabel,
  ansicht,
  onAnsichtWechsel,
  hatZeitraum,
  laedt = false,
}: {
  zufluss: number
  zeitraumLabel: string
  ansicht: ZuflussAnsicht
  onAnsichtWechsel: (a: ZuflussAnsicht) => void
  hatZeitraum: boolean
  laedt?: boolean
}) {
  const prozent = Math.min((zufluss / OBERE_GRENZE) * 100, 100)
  const { freibetrag, anrechenbar } = berechneEks(zufluss)

  let stufe: 'ok' | 'warn' | 'kritisch'
  if (zufluss <= GRUNDFREIBETRAG) stufe = 'ok'
  else if (zufluss < OBERE_GRENZE) stufe = 'warn'
  else stufe = 'kritisch'

  const farben = {
    ok:       { balken: 'bg-green-500', text: 'text-green-700 dark:text-green-300', bg: 'bg-green-50 dark:bg-green-950', border: 'border-green-200 dark:border-green-800' },
    warn:     { balken: 'bg-amber-400', text: 'text-amber-700 dark:text-amber-300', bg: 'bg-amber-50 dark:bg-amber-950', border: 'border-amber-200 dark:border-amber-800' },
    kritisch: { balken: 'bg-red-500',   text: 'text-red-700 dark:text-red-300',    bg: 'bg-red-50 dark:bg-red-950',    border: 'border-red-200 dark:border-red-800'   },
  }[stufe]

  const pct100  = (GRUNDFREIBETRAG / OBERE_GRENZE) * 100
  const pct1000 = (GRENZE_20 / OBERE_GRENZE) * 100

  return (
    <div className={`rounded-xl border ${farben.border} ${farben.bg} p-4 space-y-3`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide flex items-center gap-1.5">
            Zufluss-Monitor
            {laedt && <span className="inline-block w-3 h-3 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />}
          </p>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Stufenfreibetrag (§ 11b SGB II)</p>
        </div>
        <div className="flex items-center gap-2">
          {hatZeitraum && (
            <div className="flex rounded-md border border-slate-300 dark:border-slate-600 overflow-hidden text-xs">
              <button
                type="button"
                onClick={() => onAnsichtWechsel('monat')}
                className={`px-2 py-1 transition-colors ${ansicht === 'monat' ? 'bg-blue-600 text-white' : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'}`}
              >
                Monat
              </button>
              <button
                type="button"
                onClick={() => onAnsichtWechsel('zeitraum')}
                className={`px-2 py-1 transition-colors ${ansicht === 'zeitraum' ? 'bg-blue-600 text-white' : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'}`}
              >
                Leistungszeitraum
              </button>
            </div>
          )}
          <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${farben.bg} ${farben.text} border ${farben.border}`}>
            {stufe === 'ok' ? 'Im Freibetrag' : stufe === 'warn' ? 'Achtung' : 'Grenze überschritten'}
          </span>
        </div>
      </div>

      {/* Fortschrittsbalken */}
      <div>
        <div className="flex justify-between text-xs text-slate-400 dark:text-slate-500 mb-1">
          <span>0 €</span>
          <span className="text-slate-500 dark:text-slate-400 font-medium">{formatEuro(zufluss)}</span>
          <span>1.200 €</span>
        </div>
        <div className="h-3 bg-white dark:bg-slate-800 rounded-full border border-slate-200 dark:border-slate-700 overflow-hidden relative">
          <div
            className={`h-full rounded-full transition-all ${farben.balken}`}
            style={{ width: `${prozent}%` }}
          />
          <div className="absolute top-0 bottom-0 w-px bg-slate-400/60" style={{ left: `${pct100}%` }} />
          <div className="absolute top-0 bottom-0 w-px bg-slate-400/60" style={{ left: `${pct1000}%` }} />
        </div>
        <div className="relative text-[10px] text-slate-400 dark:text-slate-500 mt-0.5 h-3">
          <span className="absolute" style={{ left: `${pct100}%`, transform: 'translateX(-50%)' }}>100 €</span>
          <span className="absolute" style={{ left: `${pct1000}%`, transform: 'translateX(-50%)' }}>1.000 €</span>
        </div>
      </div>

      {/* Kennzahlen */}
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div>
          <span className="block text-slate-400 dark:text-slate-500">{zeitraumLabel}</span>
          <span className="font-semibold text-slate-800 dark:text-slate-100">{formatEuro(zufluss)}</span>
        </div>
        <div>
          <span className="block text-slate-400 dark:text-slate-500">Freibetrag (ca.)</span>
          <span className="font-semibold text-green-700 dark:text-green-300">{formatEuro(freibetrag)}</span>
        </div>
        <div>
          <span className="block text-slate-400 dark:text-slate-500">Anrechenbar (ca.)</span>
          <span className={`font-semibold ${anrechenbar > 0 ? farben.text : 'text-slate-400'}`}>
            {formatEuro(anrechenbar)}
          </span>
        </div>
      </div>

      {stufe === 'warn' && zufluss <= GRENZE_20 && (
        <p className="text-xs text-amber-800 dark:text-amber-300">
          Dein Zufluss liegt über dem Grundfreibetrag. Auf den Anteil zwischen 100 € und 1.000 €
          werden 20 % anrechnungsfrei gestellt. Melde deinen Gewinn über die EKS-Erklärung.
        </p>
      )}
      {stufe === 'warn' && zufluss > GRENZE_20 && (
        <p className="text-xs text-amber-800 dark:text-amber-300">
          Zwischen 1.000 € und 1.200 € gilt noch ein Freibetrag von 10 %. Darüber hinaus wird
          der Überschuss vollständig angerechnet. EKS aktuell halten.
        </p>
      )}
      {stufe === 'kritisch' && (
        <p className={`text-xs font-medium ${farben.text}`}>
          Der Zufluss übersteigt 1.200 €. Der Überschuss über dem Gesamtfreibetrag von 300 €
          wird vollständig auf das Bürgergeld angerechnet. Stelle sicher, dass deine EKS aktuell ist.
        </p>
      )}

      <p className="text-[10px] text-slate-400 dark:text-slate-500">
        § 11b Abs. 2 SGB II: 0–100 € frei · 100–1.000 € → 20 % Freibetrag · 1.000–1.200 € → 10 % Freibetrag · darüber volle Anrechnung. Kein Ersatz für Rechtsberatung.
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Kleinunternehmer-Umsatzwarnung (§19 UStG)
// ---------------------------------------------------------------------------

function LagerwarnungWidget() {
  const navigate = useNavigate()
  const { data: unt } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen })
  const { data: artikel } = useQuery({
    queryKey: ['lagerwarnung'],
    queryFn: getLagerwarnungListe,
    staleTime: 1000 * 60 * 5,
    enabled: !!unt?.lagerführung_aktiv,
  })

  if (!unt?.lagerführung_aktiv || !artikel || artikel.length === 0) return null

  return (
    <div className="rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">
          Lager: {artikel.length} Artikel unter Mindestbestand
        </p>
        <button
          onClick={() => navigate('/artikel')}
          className="text-xs text-amber-700 dark:text-amber-400 hover:underline"
        >
          Zum Artikelstamm →
        </button>
      </div>
      <div className="space-y-1">
        {artikel.map(a => {
          const bestand = parseFloat(a.bestand_aktuell)
          const mindest = parseFloat(a.mindestbestand)
          return (
            <div key={a.id} className="flex items-center justify-between text-xs">
              <span className="text-amber-800 dark:text-amber-300 truncate max-w-[60%]">{a.bezeichnung}</span>
              <span className={`font-medium tabular-nums ${bestand < 0 ? 'text-red-600 dark:text-red-400' : 'text-amber-700 dark:text-amber-400'}`}>
                {bestand.toLocaleString('de-DE', { maximumFractionDigits: 3 })} / {mindest.toLocaleString('de-DE', { maximumFractionDigits: 3 })} {a.einheit}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------

function KleinunternehmerWarnung() {
  const { data: unt } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen })
  const { data: ku } = useQuery({
    queryKey: ['kleinunternehmer-umsatz'],
    queryFn: getKleinunternehmerUmsatz,
    enabled: !!unt?.ist_kleinunternehmer,
    staleTime: 1000 * 60 * 5,
  })

  if (!unt?.ist_kleinunternehmer || !ku) return null

  const prozent = Math.min((ku.umsatz_netto / ku.grenze_kritisch) * 100, 100)
  const ueberschritten = ku.umsatz_netto >= ku.grenze_kritisch
  const kritisch = ku.umsatz_netto >= ku.grenze_warnung

  if (!kritisch) return null

  return (
    <div className={`rounded-lg border p-4 mb-4 ${
      ueberschritten
        ? 'bg-red-50 border-red-300 dark:bg-red-950 dark:border-red-800'
        : 'bg-amber-50 border-amber-300 dark:bg-amber-950 dark:border-amber-800'
    }`}>
      <div className="flex items-start gap-3">
        <span className="text-xl">{ueberschritten ? '🚨' : '⚠️'}</span>
        <div className="flex-1">
          <p className={`font-semibold text-sm ${ueberschritten ? 'text-red-800 dark:text-red-300' : 'text-amber-800 dark:text-amber-300'}`}>
            {ueberschritten
              ? 'Kleinunternehmergrenze überschritten!'
              : 'Achtung: Kleinunternehmergrenze in Sicht'}
          </p>
          <p className={`text-sm mt-0.5 ${ueberschritten ? 'text-red-700 dark:text-red-400' : 'text-amber-700 dark:text-amber-400'}`}>
            {ueberschritten
              ? `Dein Netto-Jahresumsatz ${ku.jahr} beträgt ${formatEuro(ku.umsatz_netto)} und hat die 100.000 €-Grenze überschritten. Ab diesem Zeitpunkt bist du regelbesteuert – stelle ab sofort Rechnungen mit Umsatzsteuer aus und informiere dein Finanzamt.`
              : `Dein Netto-Jahresumsatz ${ku.jahr} beträgt ${formatEuro(ku.umsatz_netto)} (${prozent.toFixed(1)} % der 100.000 €-Grenze). Bei Überschreitung wechselst du sofort zur Regelbesteuerung.`
            }
          </p>
          <div className="mt-2 h-1.5 rounded-full bg-amber-200 dark:bg-amber-900 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${ueberschritten ? 'bg-red-500' : 'bg-amber-500'}`}
              style={{ width: `${prozent}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

function FaelligeKachel({ rechnungen }: { rechnungen: Rechnung[] }) {
  const heute = heuteIso()
  const sortiert = [...rechnungen].sort((a, b) => (a.faellig_am ?? '') < (b.faellig_am ?? '') ? -1 : 1)

  const gesamt = rechnungen.length
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-amber-200 dark:border-amber-800 mb-6">
      <div className="px-5 py-3 border-b border-amber-100 dark:border-amber-800 flex items-center gap-2">
        <span className="text-amber-500">⚠️</span>
        <h3 className="font-semibold text-slate-700 dark:text-slate-200">Fällige Rechnungen</h3>
        <span className="ml-auto text-xs text-slate-400 dark:text-slate-500">nächste 7 Tage + überfällig · {gesamt} Einträge</span>
      </div>
      <div className="overflow-y-auto resize-y px-5 py-4" style={{ height: '240px', minHeight: '96px' }}>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-700 text-xs text-slate-400 dark:text-slate-500">
              <th className="pb-1.5 text-left font-medium">Fällig am</th>
              <th className="pb-1.5 text-left font-medium">Typ</th>
              <th className="pb-1.5 text-left font-medium">Partner</th>
              <th className="pb-1.5 text-left font-medium">Rg.-Nr.</th>
              <th className="pb-1.5 text-right font-medium">Betrag</th>
            </tr>
          </thead>
          <tbody>
            {sortiert.map(r => {
              const ueberfaellig = r.faellig_am && r.faellig_am < heute
              return (
                <tr key={r.id} className="border-b border-slate-50 dark:border-slate-700 last:border-0">
                  <td className={`py-2 pr-4 whitespace-nowrap font-medium ${ueberfaellig ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-400'}`}>
                    {r.faellig_am ? formatDatum(r.faellig_am) : '—'}
                    {ueberfaellig && <span className="ml-1.5 text-[10px] bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded px-1">Überfällig</span>}
                  </td>
                  <td className="py-2 pr-4">
                    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${r.typ === 'eingang' ? 'bg-orange-50 dark:bg-orange-950 text-orange-600 dark:text-orange-400' : 'bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400'}`}>
                      {r.typ === 'eingang' ? 'Eingang' : 'Ausgang'}
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-slate-700 dark:text-slate-200 truncate max-w-[140px]">
                    {r.typ === 'ausgang' ? (r.kunde_name ?? r.partner_freitext ?? '—') : (r.lieferant_name ?? r.partner_freitext ?? '—')}
                  </td>
                  <td className="py-2 pr-4 font-mono text-xs text-slate-400 dark:text-slate-500">{r.rechnungsnummer ?? '—'}</td>
                  <td className="py-2 text-right font-medium text-slate-800 dark:text-slate-100 whitespace-nowrap">{formatEuro(r.brutto_gesamt)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function Dashboard() {
  const navigate = useNavigate()
  // Filter: Lazy-Init aus Store → bleibt beim Navigieren erhalten bis Programmende
  const [filterModus, _setFilterModus] = useState<FilterModus>(() => (dashboardFilter.modus as FilterModus) ?? 'monat')
  const setFilterModus = (m: FilterModus) => { dashboardFilter.modus = m; _setFilterModus(m) }

  const [monat, _setMonat] = useState<string>(() => dashboardFilter.monat)
  const setMonat = (m: string) => { dashboardFilter.monat = m; _setMonat(m) }

  const [datum, _setDatum] = useState<string>(() => dashboardFilter.datum)
  const setDatum = (d: string) => { dashboardFilter.datum = d; _setDatum(d) }

  const [datumVon, _setDatumVon] = useState<string>(() => dashboardFilter.datumVon)
  const setDatumVon = (d: string) => { dashboardFilter.datumVon = d; _setDatumVon(d) }

  const [datumBis, _setDatumBis] = useState<string>(() => dashboardFilter.datumBis)
  const setDatumBis = (d: string) => { dashboardFilter.datumBis = d; _setDatumBis(d) }

  const aktivesJahr = new Date().getFullYear()
  const filterParams =
    filterModus === 'monat'
      ? { monat }
      : filterModus === 'datum'
      ? { datum_von: datum, datum_bis: datum }
      : filterModus === 'zeitraum'
      ? { datum_von: datumVon, datum_bis: datumBis }
      : { datum_von: `${aktivesJahr}-01-01`, datum_bis: `${aktivesJahr}-12-31` }

  const { data: eintraege } = useQuery({
    queryKey: ['journal', filterModus, monat, datum, datumVon, datumBis],
    queryFn: () => getJournal(filterParams),
  })

  const { data: unternehmen } = useQuery({
    queryKey: ['unternehmen'],
    queryFn: getUnternehmen,
    staleTime: 1000 * 60 * 10,
  })

  const [zuflussAnsicht, setZuflussAnsicht] = useState<ZuflussAnsicht>('monat')

  const zeitraum = unternehmen?.leistungsbescheid_monat
    ? getAbrechnungszeitraum(unternehmen.leistungsbescheid_monat)
    : null

  // Aktuellen Monat für Zufluss-Monitor (Monat-Ansicht)
  const { data: aktuelleEintraege } = useQuery({
    queryKey: ['journal-aktuell', aktuellerMonat()],
    queryFn: () => getJournal({ monat: aktuellerMonat() }),
    enabled: unternehmen?.bezieht_transferleistungen === true,
    staleTime: 1000 * 60 * 5,
  })

  // Abrechnungszeitraum (6 Monate) – wird vorgeladen sobald leistungsbescheid_monat gesetzt ist
  const { data: zeitraumEintraege, isFetching: zeitraumLaedt } = useQuery({
    queryKey: ['journal-zeitraum', zeitraum?.von, zeitraum?.bis],
    queryFn: () => getJournal({ datum_von: zeitraum!.von, datum_bis: zeitraum!.bis }),
    enabled: unternehmen?.bezieht_transferleistungen === true && !!zeitraum,
    staleTime: 1000 * 60 * 5,
  })

  const { data: faellige } = useQuery({
    queryKey: ['rechnungen', 'faellig'],
    queryFn: () => getFaelligeRechnungen(7),
    staleTime: 1000 * 60 * 5,
  })

  const { data: zmPruefung } = useQuery({
    queryKey: ['zm-pruefen'],
    queryFn: pruefZM,
    staleTime: 1000 * 60 * 60,
    enabled: !unternehmen?.ist_kleinunternehmer,
  })

  const alle = eintraege ?? []

  // Betriebsbuchungen (ohne Privat)
  const betrieb = alle.filter((e) => e.kategorie_kontenart !== 'Privat')
  const privat  = alle.filter((e) => e.kategorie_kontenart === 'Privat')

  const einnahmen = betrieb
    .filter((e) => e.art === 'Einnahme')
    .reduce((s, e) => s + parseFloat(e.brutto_betrag), 0)
  const ausgaben = betrieb
    .filter((e) => e.art === 'Ausgabe')
    .reduce((s, e) => s + parseFloat(e.brutto_betrag), 0)
  const saldo = einnahmen - ausgaben
  const letzteEintraege = alle

  // §11b SGB II Zuflussprinzip: Einnahmen und Ausgaben brutto (tatsächlich geflossene Beträge)
  // Stornos heben sich korrekt auf (brutto +X − brutto X = 0)
  // Verlust = 0 (negatives Einkommen gibt es bei §11b nicht)
  function calcZufluss(entries: typeof aktuelleEintraege) {
    const list = (entries ?? []).filter(
      (e) => e.kategorie_kontenart !== 'Privat' && e.beschreibung !== 'Kassenanfangsbestand'
    )
    const ein = list.filter((e) => e.art === 'Einnahme').reduce((s, e) => s + parseFloat(e.brutto_betrag), 0)
    const aus = list.filter((e) => e.art === 'Ausgabe').reduce((s, e) => s + parseFloat(e.brutto_betrag), 0)
    return Math.max(0, ein - aus)
  }

  const hatZeitraum = !!zeitraum
  const zeitraumAktiv = zuflussAnsicht === 'zeitraum' && hatZeitraum
  // Zeige Periodendaten wenn vorhanden, sonst Monatsdaten als Fallback während des Ladens
  const zufluss = zeitraumAktiv && zeitraumEintraege !== undefined
    ? calcZufluss(zeitraumEintraege)
    : calcZufluss(aktuelleEintraege)

  const jetzt = new Date()
  const monatLabel = `${DE_MONATE[jetzt.getMonth()]} ${jetzt.getFullYear()}`
  // Label wechselt sofort beim Toggle – auch während die Daten noch laden
  const zuflussLabel = zeitraumAktiv ? zeitraum!.label : monatLabel

  const loaded = eintraege !== undefined
  const hatPrivatbuchungen = privat.length > 0
  const zeigeZuflussMonitor = unternehmen?.bezieht_transferleistungen === true

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <KleinunternehmerWarnung />
      <LagerwarnungWidget />
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Dashboard</h2>

        {/* Zeitfilter */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-lg border border-slate-300 dark:border-slate-600 overflow-hidden text-sm">
            {(['monat', 'datum', 'zeitraum', 'alle'] as FilterModus[]).map((m) => (
              <button
                key={m}
                onClick={() => setFilterModus(m)}
                className={`px-3 py-1.5 transition-colors ${
                  filterModus === m
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-slate-600 hover:bg-slate-50 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
                }`}
              >
                {m === 'monat' ? 'Monat' : m === 'datum' ? 'Tag' : m === 'zeitraum' ? 'Zeitraum' : 'Jahr'}
              </button>
            ))}
          </div>

          {filterModus === 'monat' && (
            <input
              type="month"
              value={monat}
              onChange={(e) => setMonat(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
            />
          )}
          {filterModus === 'datum' && (
            <input
              type="date"
              value={datum}
              onChange={guardedDateChange(setDatum)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
            />
          )}
          {filterModus === 'zeitraum' && (
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={datumVon}
                onChange={guardedDateChange(setDatumVon)}
                className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
              />
              <span className="text-slate-400 dark:text-slate-500 text-sm">bis</span>
              <input
                type="date"
                value={datumBis}
                min={datumVon}
                onChange={guardedDateChange(setDatumBis)}
                className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100"
              />
            </div>
          )}
        </div>
      </div>

      {/* Zufluss-Monitor */}
      {zeigeZuflussMonitor && (
        <div className="mb-6">
          <ZuflussMonitor
            zufluss={zufluss}
            zeitraumLabel={zuflussLabel}
            ansicht={zuflussAnsicht}
            onAnsichtWechsel={setZuflussAnsicht}
            hatZeitraum={hatZeitraum}
            laedt={zeitraumLaedt && zuflussAnsicht === 'zeitraum'}
          />
        </div>
      )}

      {/* Kacheln (nur Betriebsbuchungen) */}
      <div className="grid grid-cols-3 gap-4 mb-2">
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">Betriebseinnahmen</p>
          <p className="text-2xl font-bold text-green-600">
            {loaded ? formatEuro(einnahmen) : '—'}
          </p>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">Betriebsausgaben</p>
          <p className="text-2xl font-bold text-red-600">
            {loaded ? formatEuro(ausgaben) : '—'}
          </p>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">Saldo</p>
          <p className={`text-2xl font-bold ${saldo >= 0 ? 'text-blue-600' : 'text-red-700'}`}>
            {loaded ? formatEuro(saldo) : '—'}
          </p>
        </div>
      </div>

      {/* Privat-Hinweis unter den Kacheln */}
      {hatPrivatbuchungen && (
        <p className="text-xs text-slate-400 dark:text-slate-500 mb-6 pl-1">
          🏠 {privat.length} Privatbuchung{privat.length !== 1 ? 'en' : ''} (
          {formatEuro(privat.reduce((s, e) => s + parseFloat(e.brutto_betrag), 0))}) im
          gewählten Zeitraum – nicht in den Kacheln enthalten.
        </p>
      )}
      {!hatPrivatbuchungen && <div className="mb-6" />}

      {/* ZM-Hinweis */}
      {zmPruefung?.faellig && (
        <div
          onClick={() => navigate('/zm')}
          className="flex items-center gap-3 bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-700 rounded-xl px-5 py-3 mb-4 cursor-pointer hover:bg-amber-100 dark:hover:bg-amber-950/60 transition-colors"
        >
          <span className="text-2xl">🇪🇺</span>
          <div className="flex-1">
            <p className="text-sm font-semibold text-amber-800 dark:text-amber-200">
              Zusammenfassende Meldung fällig – {zmPruefung.zeitraum_label}
            </p>
            <p className="text-xs text-amber-700 dark:text-amber-300">
              Frist: {zmPruefung.deadline.split('-').reverse().join('.')} · Einzureichen beim BZSt über ELSTER
            </p>
          </div>
          <span className="text-amber-600 dark:text-amber-400 text-sm">→</span>
        </div>
      )}

      {/* Fällige Rechnungen */}
      {faellige && faellige.length > 0 && (
        <FaelligeKachel rechnungen={faellige} />
      )}

      {/* Letzte Buchungen */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
        <div className="px-5 py-3 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
          <h3 className="font-semibold text-slate-700 dark:text-slate-200">Letzte Buchungen</h3>
          {letzteEintraege.length > 0 && (
            <span className="text-xs text-slate-400 dark:text-slate-500">{letzteEintraege.length} Einträge</span>
          )}
        </div>
        {letzteEintraege.length === 0 ? (
          <p className="text-slate-400 dark:text-slate-500 text-sm p-5">Keine Buchungen im gewählten Zeitraum.</p>
        ) : (
          <div className="overflow-y-auto resize-y" style={{ height: '240px', minHeight: '96px' }}>
            <table className="w-full text-sm">
              <tbody>
                {letzteEintraege.map((e) => (
                  <tr key={e.id} className="border-b border-slate-50 dark:border-slate-700 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-700">
                    <td className="px-5 py-3 text-slate-500 dark:text-slate-400 w-28">{formatDatum(e.datum)}</td>
                    <td className="px-5 py-3 text-slate-400 dark:text-slate-500 w-32 font-mono text-xs">{e.belegnr}</td>
                    <td className="px-5 py-3 text-slate-700 dark:text-slate-200">
                      {e.beschreibung}
                      {e.kategorie_kontenart === 'Privat' && (
                        <span className="ml-1.5 text-[10px] text-purple-500 bg-purple-50 border border-purple-200 rounded px-1 dark:bg-purple-950 dark:border-purple-800">
                          Privat
                        </span>
                      )}
                    </td>
                    <td className={`px-5 py-3 text-right font-medium ${
                      e.kategorie_kontenart === 'Privat'
                        ? 'text-slate-400'
                        : e.art === 'Einnahme' ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {e.art === 'Ausgabe' ? '−' : '+'}{formatEuro(e.brutto_betrag)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
