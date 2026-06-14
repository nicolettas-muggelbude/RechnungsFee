import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getJournal, getKategorien, getKassenbuchExportUrl, getJournalExportUrl, openUrl } from '../../api/client'
import { BuchungForm } from './BuchungForm'
import { TagesabschlussDialog } from './TagesabschlussDialog'
import { BuchungDetail } from './BuchungDetail'
import { guardedDateChange } from '../../utils/dateInput'
import { journalFilter } from '../../store/filterStore'

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

type FilterModus = 'monat' | 'datum' | 'zeitraum' | 'alle' | 'jahr'

function heuteIso(): string {
  return new Date().toISOString().slice(0, 10)
}

export function JournalPage() {
  const navigate = useNavigate()

  // Filter: Lazy-Init aus Store → bleibt beim Navigieren erhalten bis Programmende
  const [filterModus, _setFilterModus] = useState<FilterModus>(() => journalFilter.modus)
  const setFilterModus = (m: FilterModus) => { journalFilter.modus = m; _setFilterModus(m) }

  const [monat, _setMonat] = useState<string>(() => journalFilter.monat)
  const setMonat = (m: string) => { journalFilter.monat = m; _setMonat(m) }

  const [datum, _setDatum] = useState<string>(() => journalFilter.datum)
  const setDatum = (d: string) => { journalFilter.datum = d; _setDatum(d) }

  const [datumVon, _setDatumVon] = useState<string>(() => journalFilter.datumVon)
  const setDatumVon = (d: string) => { journalFilter.datumVon = d; _setDatumVon(d) }

  const [datumBis, _setDatumBis] = useState<string>(() => journalFilter.datumBis)
  const setDatumBis = (d: string) => { journalFilter.datumBis = d; _setDatumBis(d) }

  const [art, _setArt] = useState<'' | 'Einnahme' | 'Ausgabe'>(() => journalFilter.art)
  const setArt = (a: '' | 'Einnahme' | 'Ausgabe') => { journalFilter.art = a; _setArt(a) }

  const [kategorieId, _setKategorieId] = useState<string>(() => journalFilter.kategorieId)
  const setKategorieId = (k: string) => { journalFilter.kategorieId = k; _setKategorieId(k) }

  const [zahlungsartTyp, _setZahlungsartTyp] = useState<'' | 'bar' | 'unbar'>(() => journalFilter.zahlungsartTyp)
  const setZahlungsartTyp = (z: '' | 'bar' | 'unbar') => { journalFilter.zahlungsartTyp = z; _setZahlungsartTyp(z) }

  const [nurBebuchte, _setNurBebuchte] = useState<boolean>(() => journalFilter.nurBebuchte)
  const setNurBebuchte = (v: boolean) => { journalFilter.nurBebuchte = v; _setNurBebuchte(v) }
  const [showBuchung, setShowBuchung] = useState(false)
  const [showAbschluss, setShowAbschluss] = useState(false)
  const [aktiverEintragId, setAktiverEintragId] = useState<number | null>(null)
  const [kassenbuchLaedt, setKassenbuchLaedt] = useState(false)
  const [exportLaedt, setExportLaedt] = useState(false)
  const [csvErfolg, setCsvErfolg] = useState<string | null>(null)

  const aktivesJahr = new Date().getFullYear()
  const filterParams = filterModus === 'monat'
    ? { monat }
    : filterModus === 'datum'
      ? { datum_von: datum, datum_bis: datum }
      : filterModus === 'zeitraum'
        ? { datum_von: datumVon, datum_bis: datumBis }
        : { datum_von: `${aktivesJahr}-01-01`, datum_bis: `${aktivesJahr}-12-31` }

  function kassenbuchDatumsbereich(): { von: string; bis: string } {
    if (filterModus === 'monat') {
      const [y, m] = monat.split('-').map(Number)
      const von = `${y}-${String(m).padStart(2, '0')}-01`
      const letzterTag = new Date(y, m, 0).getDate()
      const bis = `${y}-${String(m).padStart(2, '0')}-${String(letzterTag).padStart(2, '0')}`
      return { von, bis }
    }
    if (filterModus === 'datum') return { von: datum, bis: datum }
    if (filterModus === 'zeitraum') return { von: datumVon, bis: datumBis }
    return { von: `${aktivesJahr}-01-01`, bis: `${aktivesJahr}-12-31` }
  }

  async function handleKassenbuchExport(format: 'pdf' | 'csv') {
    setKassenbuchLaedt(true)
    setCsvErfolg(null)
    try {
      const { von, bis } = kassenbuchDatumsbereich()
      const url = await getKassenbuchExportUrl(von, bis, format)
      await openUrl(url)
      if (format === 'csv') setCsvErfolg('Kassenbuch als CSV exportiert und in deinen Downloads gespeichert.')
    } finally {
      setKassenbuchLaedt(false)
    }
  }

  async function handleJournalExport(format: 'pdf' | 'csv') {
    setExportLaedt(true)
    setCsvErfolg(null)
    try {
      const p: Parameters<typeof getJournalExportUrl>[0] = { format }
      if (filterModus === 'monat') {
        p.monat = monat
      } else if (filterModus === 'datum') {
        p.datum_von = datum
        p.datum_bis = datum
      } else if (filterModus === 'zeitraum') {
        p.datum_von = datumVon
        p.datum_bis = datumBis
      } else {
        p.datum_von = `${aktivesJahr}-01-01`
        p.datum_bis = `${aktivesJahr}-12-31`
      }
      if (art) p.art = art
      if (kategorieId) p.kategorie_id = Number(kategorieId)
      if (zahlungsartTyp) p.zahlungsart_typ = zahlungsartTyp
      const url = await getJournalExportUrl(p)
      await openUrl(url)
      if (format === 'csv') setCsvErfolg('Journal als CSV exportiert und in deinen Downloads gespeichert.')
    } finally {
      setExportLaedt(false)
    }
  }

  const { data: eintraege, isLoading } = useQuery({
    queryKey: ['journal', filterModus, monat, datum, datumVon, datumBis, art, kategorieId, zahlungsartTyp],
    queryFn: () => getJournal({
      ...filterParams,
      art: art || undefined,
      kategorie_id: kategorieId ? Number(kategorieId) : undefined,
      zahlungsart_typ: zahlungsartTyp || undefined,
    }),
  })

  const { data: kategorien } = useQuery({
    queryKey: ['kategorien', nurBebuchte],
    queryFn: () => getKategorien(false, nurBebuchte),
  })

  const hatAktiveFilter = art !== '' || kategorieId !== '' || zahlungsartTyp !== '' || filterModus !== 'monat' || nurBebuchte

  function resetFilter() {
    setArt('')
    setKategorieId('')
    setZahlungsartTyp('')
    setNurBebuchte(false)
    setFilterModus('monat')
    setMonat(aktuellerMonat())
    setDatum(heuteIso())
    setDatumVon(heuteIso())
    setDatumBis(heuteIso())
  }

  // Belegnummern die bereits storniert wurden (aus der geladenen Liste ableiten)
  const bereitsStornieterteBelegnrn = new Set(
    (eintraege ?? [])
      .filter((e) => e.beschreibung.startsWith('STORNO '))
      .map((e) => e.beschreibung.split(':')[0].replace('STORNO ', '').trim())
  )

  function toggleEintrag(id: number) {
    setAktiverEintragId((prev) => (prev === id ? null : id))
  }

  const sumEinnahmen = (eintraege ?? []).reduce(
    (s, e) => e.art === 'Einnahme' ? s + parseFloat(e.brutto_betrag) : s, 0)
  const sumAusgaben = (eintraege ?? []).reduce(
    (s, e) => e.art === 'Ausgabe' ? s + parseFloat(e.brutto_betrag) : s, 0)
  const saldo = sumEinnahmen - sumAusgaben

  return (
    <div className="h-full flex flex-col">
      {/* Kopf + Filter – bleibt stehen */}
      <div className="shrink-0 px-6 pt-6 pb-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Journal</h2>
        <div className="flex gap-2">
          {/* Journal-Export immer sichtbar */}
          <div className="flex rounded-lg overflow-hidden border border-slate-300 dark:border-slate-600">
            <button
              onClick={() => handleJournalExport('pdf')}
              disabled={exportLaedt}
              title="Journal als PDF exportieren"
              className="px-3 py-2 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
            >
              {exportLaedt ? '⏳' : '📄'} PDF
            </button>
            <div className="w-px bg-slate-300 dark:bg-slate-600" />
            <button
              onClick={() => handleJournalExport('csv')}
              disabled={exportLaedt}
              title="Journal als CSV exportieren"
              className="px-3 py-2 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
            >
              CSV
            </button>
          </div>
          {zahlungsartTyp === 'bar' && (
            <div className="flex rounded-lg overflow-hidden border border-slate-300 dark:border-slate-600">
              <button
                onClick={() => handleKassenbuchExport('pdf')}
                disabled={kassenbuchLaedt}
                title="Kassenbuch als PDF exportieren"
                className="px-3 py-2 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
              >
                {kassenbuchLaedt ? '⏳' : '📒'} Kassenbuch PDF
              </button>
              <div className="w-px bg-slate-300 dark:bg-slate-600" />
              <button
                onClick={() => handleKassenbuchExport('csv')}
                disabled={kassenbuchLaedt}
                title="Kassenbuch als CSV exportieren"
                className="px-3 py-2 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
              >
                CSV
              </button>
            </div>
          )}
          <button
            onClick={() => setShowAbschluss(true)}
            className="border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg px-4 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-800"
          >
            Tagesabschluss
          </button>
          <button
            onClick={() => setShowBuchung(true)}
            className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700"
          >
            + Neue Buchung
          </button>
        </div>
      </div>

      {/* Filter */}
      <div className="flex flex-wrap gap-3 mb-4 items-center">
        {/* Modus-Umschalter */}
        <div className="flex rounded-lg border border-slate-300 dark:border-slate-600 overflow-hidden text-sm">
          {(['monat', 'datum', 'zeitraum', 'alle'] as FilterModus[]).map((m) => (
            <button
              key={m}
              onClick={() => setFilterModus(m)}
              className={`px-3 py-1.5 capitalize transition-colors ${
                filterModus === m
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-slate-600 hover:bg-slate-50 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
              }`}
            >
              {m === 'monat' ? 'Monat' : m === 'datum' ? 'Tag' : m === 'zeitraum' ? 'Zeitraum' : 'Jahr'}
            </button>
          ))}
        </div>

        {/* Datums-Eingabe je nach Modus */}
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

        {/* Art */}
        <select
          value={art}
          onChange={(e) => setArt(e.target.value as '' | 'Einnahme' | 'Ausgabe')}
          className={`rounded-lg px-3 py-1.5 text-sm focus:outline-none border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 transition-shadow ${
            art === 'Einnahme'
              ? 'ring-2 ring-green-500'
              : art === 'Ausgabe'
              ? 'ring-2 ring-red-500'
              : 'focus:ring-2 focus:ring-blue-500'
          }`}
        >
          <option value="">Alle Arten</option>
          <option value="Einnahme">Einnahmen</option>
          <option value="Ausgabe">Ausgaben</option>
        </select>

        {/* Kategorie */}
        <select
          value={kategorieId}
          onChange={(e) => setKategorieId(e.target.value)}
          className={`rounded-lg px-3 py-1.5 text-sm focus:outline-none border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 transition-shadow ${
            kategorieId !== ''
              ? 'ring-2 ring-blue-500'
              : 'focus:ring-2 focus:ring-blue-500'
          }`}
        >
          <option value="">Alle Kategorien</option>
          {(kategorien ?? []).map((k) => (
            <option key={k.id} value={k.id}>{k.name}</option>
          ))}
        </select>

        {/* Nur bebuchte Kategorien */}
        <button
          onClick={() => { setNurBebuchte(!nurBebuchte); setKategorieId('') }}
          title="Nur Kategorien anzeigen, die mindestens eine Buchung haben"
          className={`rounded-lg px-3 py-1.5 text-sm border transition-colors ${
            nurBebuchte
              ? 'bg-blue-600 text-white border-blue-600'
              : 'border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
          }`}
        >
          Nur bebuchte
        </button>

        {/* Zahlungsart */}
        <select
          value={zahlungsartTyp}
          onChange={(e) => setZahlungsartTyp(e.target.value as '' | 'bar' | 'unbar')}
          className={`rounded-lg px-3 py-1.5 text-sm focus:outline-none border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 transition-shadow ${
            zahlungsartTyp !== ''
              ? 'ring-2 ring-blue-500'
              : 'focus:ring-2 focus:ring-blue-500'
          }`}
        >
          <option value="">Bar &amp; Unbar</option>
          <option value="bar">Nur Bar</option>
          <option value="unbar">Nur Unbar</option>
        </select>

        {/* Reset */}
        {hatAktiveFilter && (
          <button
            onClick={resetFilter}
            title="Filter zurücksetzen"
            className="border border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 rounded-lg px-2.5 py-1.5 text-sm hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
          >
            ✕
          </button>
        )}

        {/* Summen: Saldo links, dann Zugänge/Abgänge über den jeweiligen Spalten */}
        {!!eintraege?.length && (
          <div className="ml-auto flex items-center text-sm">
            <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide mr-1.5">Saldo</span>
            <span className={`font-bold mr-4 ${saldo >= 0 ? 'text-green-700 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
              {formatEuro(saldo)}
            </span>
            <div className="w-28 px-4 text-right font-medium text-green-600 dark:text-green-400">
              ↑ {formatEuro(sumEinnahmen)}
            </div>
            <div className="w-28 px-4 text-right font-medium text-red-600 dark:text-red-400">
              ↓ {formatEuro(sumAusgaben)}
            </div>
          </div>
        )}
      </div>
      </div>{/* Ende Kopf+Filter */}

      {csvErfolg && (
        <div className="shrink-0 px-6 pb-3">
          <div className="flex items-center gap-3 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg px-4 py-2.5 text-sm text-green-800 dark:text-green-300">
            <span className="shrink-0">✓</span>
            <span>{csvErfolg}</span>
            <button onClick={() => setCsvErfolg(null)} className="ml-auto text-green-600 dark:text-green-400 hover:text-green-800 dark:hover:text-green-200">✕</button>
          </div>
        </div>
      )}

      {/* Tabelle – scrollbar */}
      <div className="flex-1 overflow-y-auto min-h-0 px-6 pb-6">
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        {isLoading ? (
          <p className="text-slate-400 dark:text-slate-500 text-sm p-5">Lade…</p>
        ) : !eintraege?.length ? (
          <p className="text-slate-400 dark:text-slate-500 text-sm p-5">Keine Buchungen gefunden.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 text-left">
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 w-28">Datum</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 w-36">Belegnr.</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400">Beschreibung</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 w-24">Zahlung</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 text-right w-28">Einnahme</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 text-right w-28">Ausgabe</th>
              </tr>
            </thead>
            <tbody>
              {eintraege.map((e) => {
                const istAktiv = aktiverEintragId === e.id
                const bereitsStorniert = bereitsStornieterteBelegnrn.has(e.belegnr)
                const istStorno = e.beschreibung.startsWith('STORNO ')
                const hatUst = parseFloat(e.ust_betrag) > 0
                const rowClass = `border-b border-slate-100 dark:border-slate-700 cursor-pointer select-none transition-colors ${
                  istAktiv ? 'bg-blue-50 dark:bg-blue-950' : istStorno ? 'hover:bg-slate-50 dark:hover:bg-slate-700 opacity-60' : 'hover:bg-slate-50 dark:hover:bg-slate-700'
                }`
                return (
                  <>
                    {/* Netto-Zeile */}
                    <tr key={e.id} onClick={() => toggleEintrag(e.id)} className={rowClass}>
                      <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{formatDatum(e.datum)}</td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-400 dark:text-slate-500 flex items-center gap-1">
                        <span className={`inline-block w-3 text-slate-300 dark:text-slate-600 transition-transform ${istAktiv ? 'rotate-90' : ''}`}>▶</span>
                        {e.belegnr}
                      </td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-200">
                        {e.beschreibung}
                        {e.rechnung_nr && e.rechnung_id && (
                          <button
                            type="button"
                            title="Zur Rechnung springen"
                            onClick={(ev) => { ev.stopPropagation(); navigate(`/rechnungen?open=${e.rechnung_id}`) }}
                            className="ml-2 text-xs bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400 rounded px-1.5 py-0.5 hover:bg-blue-100 dark:hover:bg-blue-900 transition-colors"
                          >
                            🧾 {e.rechnung_nr} ↗
                          </button>
                        )}
                        {e.steuerbefreiung_grund && (
                          <span className="ml-2 text-xs text-slate-400 dark:text-slate-500">({e.steuerbefreiung_grund})</span>
                        )}
                        {bereitsStorniert && (
                          <span className="ml-2 text-xs bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-500 rounded px-1">storniert</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{e.zahlungsart}</td>
                      <td className="px-4 py-3 text-right font-medium text-green-600">
                        {e.art === 'Einnahme' ? formatEuro(hatUst ? e.netto_betrag : e.brutto_betrag) : ''}
                      </td>
                      <td className="px-4 py-3 text-right font-medium text-red-600">
                        {e.art === 'Ausgabe' ? formatEuro(hatUst ? e.netto_betrag : e.brutto_betrag) : ''}
                      </td>
                    </tr>
                    {/* USt-Zeile */}
                    {hatUst && (
                      <tr key={`${e.id}-ust`} onClick={() => toggleEintrag(e.id)} className={rowClass}>
                        <td className="px-4 py-2 text-slate-400 dark:text-slate-500 text-xs"></td>
                        <td className="px-4 py-2 font-mono text-xs text-slate-300 dark:text-slate-600">
                          {e.konto_ust_skr03 ?? ''}
                        </td>
                        <td className="px-4 py-2 text-xs text-slate-400 dark:text-slate-500 italic">
                          {/* 1776/1771 = Umsatzsteuer-Konto (auch bei Forderungsausfall art='Ausgabe', Issue #113) */}
                          {(e.art === 'Einnahme' || e.konto_ust_skr03 === '1776' || e.konto_ust_skr03 === '1771')
                            ? `Umsatzsteuer ${e.ust_satz} %`
                            : `Vorsteuer ${e.ust_satz} %`}
                        </td>
                        <td className="px-4 py-2"></td>
                        <td className="px-4 py-2 text-right text-xs font-medium text-green-500 dark:text-green-700">
                          {e.art === 'Einnahme' ? formatEuro(e.ust_betrag) : ''}
                        </td>
                        <td className="px-4 py-2 text-right text-xs font-medium text-red-500 dark:text-red-700">
                          {e.art === 'Ausgabe' ? formatEuro(e.ust_betrag) : ''}
                        </td>
                      </tr>
                    )}
                    {istAktiv && (
                      <BuchungDetail
                        key={`detail-${e.id}`}
                        eintrag={e}
                        bereitsStorniert={bereitsStorniert}
                        onClose={() => setAktiverEintragId(null)}
                      />
                    )}
                  </>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
      </div>{/* Ende Tabellen-Wrapper */}

      {showBuchung && (
        <BuchungForm
          onClose={() => setShowBuchung(false)}
          onSuccess={() => setShowBuchung(false)}
        />
      )}
      {showAbschluss && (
        <TagesabschlussDialog
          onClose={() => setShowAbschluss(false)}
          onSuccess={() => setShowAbschluss(false)}
        />
      )}
    </div>
  )
}
