/**
 * Issue #597: Abschlagsrechnung aus Angebot oder Auftrag erstellen und die zugehörigen
 * Abschläge in der Detailansicht anzeigen. Nur sichtbar, wenn Abschlagsrechnungen unter
 * Einstellungen → Unternehmen → Funktionen eingeschaltet sind (Aufrufer prüft das).
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { abschlagAusDokument, type Rechnung } from '../api/client'

function euro(wert: number | string) {
  const n = typeof wert === 'number' ? wert : parseFloat(wert) || 0
  return n.toLocaleString('de-DE', { style: 'currency', currency: 'EUR' })
}

function datum(iso: string) {
  const [j, m, t] = iso.slice(0, 10).split('-')
  return `${t}.${m}.${j}`
}

function zahl(text: string) {
  // „2.000,50“ und „2000,50“ wie „2000.50“ – Punkt nur als Tausendertrennzeichen, wenn ein Komma folgt
  const t = text.trim()
  return parseFloat(t.includes(',') ? t.replace(/\./g, '').replace(',', '.') : t)
}

/** Summe der nicht stornierten Abschläge und der noch offene Rest des Dokuments */
function abschlagStand(dok: Rechnung) {
  const gesamt = parseFloat(dok.brutto_gesamt as unknown as string) || 0
  const abgerechnet = (dok.abschlaege ?? [])
    .filter(a => !a.storniert)
    .reduce((s, a) => s + (parseFloat(a.brutto_gesamt) || 0), 0)
  return { gesamt, abgerechnet, rest: Math.max(gesamt - abgerechnet, 0) }
}

export function AbschlagErstellenKnopf({ dokument, className, gesperrt, gesperrtTitel }: {
  dokument: Rechnung
  className: string
  gesperrt?: boolean
  gesperrtTitel?: string
}) {
  const [offen, setOffen] = useState(false)
  return (
    <>
      <button onClick={() => setOffen(true)} disabled={gesperrt} title={gesperrt ? gesperrtTitel : undefined}
        className={className}>
        → Abschlagsrechnung
      </button>
      {offen && <AbschlagDialog dokument={dokument} onClose={() => setOffen(false)} />}
    </>
  )
}

function AbschlagDialog({ dokument, onClose }: { dokument: Rechnung; onClose: () => void }) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [art, setArt] = useState<'prozent' | 'betrag'>('prozent')
  const [eingabe, setEingabe] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)
  const [laedt, setLaedt] = useState(false)
  const { gesamt, abgerechnet, rest } = abschlagStand(dokument)

  const wert = zahl(eingabe)
  const betrag = art === 'prozent' ? (isNaN(wert) ? 0 : gesamt * wert / 100) : (isNaN(wert) ? 0 : wert)
  const ungueltig = !(wert > 0) || (art === 'prozent' && wert > 100) || betrag > rest + 0.005

  async function erstellen() {
    setFehler(null)
    setLaedt(true)
    try {
      const a = await abschlagAusDokument(dokument.id, art === 'prozent' ? { prozent: wert } : { betrag: wert })
      qc.invalidateQueries({ queryKey: ['auftraege'] })
      qc.invalidateQueries({ queryKey: ['angebote'] })
      qc.invalidateQueries({ queryKey: ['rechnungen'] })
      navigate(`/abschlagsrechnungen?id=${a.id}`)
    } catch (e) {
      setFehler(e instanceof Error ? e.message : 'Abschlagsrechnung konnte nicht erstellt werden.')
    } finally {
      setLaedt(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-labelledby="abschlag-titel"
        className="w-full max-w-sm bg-white dark:bg-slate-800 rounded-xl shadow-xl p-5 space-y-4"
        onClick={e => e.stopPropagation()}>
        <h2 id="abschlag-titel" className="font-semibold text-slate-800 dark:text-slate-100">
          Abschlagsrechnung erstellen
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          {dokument.dokument_typ} {dokument.rechnungsnummer ?? ''}: {euro(gesamt)}
          {abgerechnet > 0 && <> · bereits abgerechnet {euro(abgerechnet)} · offen {euro(rest)}</>}
        </p>

        <div className="flex gap-4 text-sm text-slate-700 dark:text-slate-200">
          <label className="flex items-center gap-1.5">
            <input type="radio" checked={art === 'prozent'} onChange={() => { setArt('prozent'); setEingabe('') }} />
            Prozent
          </label>
          <label className="flex items-center gap-1.5">
            <input type="radio" checked={art === 'betrag'} onChange={() => { setArt('betrag'); setEingabe('') }} />
            Betrag (brutto)
          </label>
        </div>

        <div className="flex items-center gap-2">
          <input autoFocus inputMode="decimal" value={eingabe} onChange={e => setEingabe(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !ungueltig && !laedt) erstellen() }}
            placeholder={art === 'prozent' ? 'z. B. 30' : 'z. B. 2000'}
            aria-label={art === 'prozent' ? 'Prozent' : 'Betrag brutto in Euro'}
            className="w-32 px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100" />
          <span className="text-sm text-slate-500 dark:text-slate-400">{art === 'prozent' ? '%' : '€'}</span>
          {art === 'prozent' && betrag > 0 && (
            <span className="text-sm text-slate-600 dark:text-slate-300">= {euro(betrag)}</span>
          )}
        </div>
        {betrag > rest + 0.005 && (
          <p className="text-xs text-red-600 dark:text-red-400">Der Abschlag ist höher als der noch offene Betrag ({euro(rest)}).</p>
        )}
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Es entsteht ein Entwurf, den du vor dem Finalisieren noch anpassen kannst. Hat das Dokument
          mehrere Steuersätze, wird der Abschlag anteilig aufgeteilt.
        </p>
        {fehler && <p className="text-sm text-red-600 dark:text-red-400">{fehler}</p>}

        <div className="flex justify-end gap-2">
          <button onClick={onClose}
            className="px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
            Abbrechen
          </button>
          <button onClick={erstellen} disabled={ungueltig || laedt}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {laedt ? 'Erstelle…' : 'Erstellen'}
          </button>
        </div>
      </div>
    </div>
  )
}

/** Liste der Abschlagsrechnungen in der Detailansicht von Angebot/Auftrag */
export function AbschlagListe({ dokument }: { dokument: Rechnung }) {
  const navigate = useNavigate()
  const abschlaege = dokument.abschlaege ?? []
  if (abschlaege.length === 0) return null
  const { gesamt, abgerechnet, rest } = abschlagStand(dokument)

  function status(a: (typeof abschlaege)[number]) {
    if (a.storniert) return 'storniert'
    if (a.ist_entwurf) return 'Entwurf'
    if (a.verrechnet_in_rechnung_id) return 'verrechnet'
    if (a.zahlungsstatus === 'bezahlt') return 'bezahlt'
    if (a.zahlungsstatus === 'teilbezahlt') return 'teilweise bezahlt'
    return 'offen'
  }

  return (
    <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-sm space-y-2">
      <p className="text-xs text-slate-500 dark:text-slate-400">Abschlagsrechnungen</p>
      <ul className="space-y-1">
        {abschlaege.map(a => (
          <li key={a.id} className="flex items-center justify-between gap-3">
            <button onClick={() => navigate(`/abschlagsrechnungen?id=${a.id}`)}
              className={`text-blue-600 hover:underline font-medium ${a.storniert ? 'line-through opacity-60' : ''}`}>
              {a.rechnungsnummer ?? `Entwurf #${a.id}`}
            </button>
            <span className="text-slate-500 dark:text-slate-400 text-xs">{datum(a.datum)} · {status(a)}</span>
            <span className="tabular-nums text-slate-700 dark:text-slate-200">{euro(a.brutto_gesamt)}</span>
          </li>
        ))}
      </ul>
      <p className="text-xs text-slate-500 dark:text-slate-400 border-t border-slate-200 dark:border-slate-700 pt-2">
        Abgerechnet {euro(abgerechnet)} von {euro(gesamt)} · offen {euro(rest)}.
        Bezahlte Abschläge werden in der Rechnung aus diesem Dokument automatisch abgezogen.
      </p>
    </div>
  )
}
