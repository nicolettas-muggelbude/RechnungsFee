import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  downloadDebugProtokoll, getDebugEinstellungen, getDebugProtokoll, setDebugEinstellungen,
  type DebugKategorie,
} from '../../api/client'

const kategorien: { id: DebugKategorie; name: string }[] = [
  { id: 'ui', name: 'UI-Aktionen (Klicks, Änderungen, Absenden)' },
  { id: 'navigation', name: 'Seitenwechsel' },
  { id: 'api', name: 'API-Anfragen (Methode, Route, Status, Dauer)' },
  { id: 'plugins', name: 'Plugin-Aufrufe und Ergebnisse' },
  { id: 'fehler', name: 'Backend- und Browserfehler' },
]
const btn = 'px-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-slate-600 disabled:opacity-50'

export function DebugPluginKarte() {
  const qc = useQueryClient()
  const [offen, setOffen] = useState(false)
  const [live, setLive] = useState(true)
  const [filter, setFilter] = useState<DebugKategorie | ''>('')
  const { data, error, isLoading } = useQuery({ queryKey: ['debug-einstellungen'], queryFn: getDebugEinstellungen })
  const speichern = useMutation({
    mutationFn: setDebugEinstellungen,
    onSuccess: d => { qc.setQueryData(['debug-einstellungen'], d) },
  })
  const download = useMutation({ mutationFn: downloadDebugProtokoll })
  const protokoll = useQuery({
    queryKey: ['debug-protokoll', filter], queryFn: () => getDebugProtokoll(filter || undefined),
    enabled: offen, refetchInterval: offen && live ? 3000 : false,
  })
  return (
    <section data-debug-ignore className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 mb-6 text-slate-700 dark:text-slate-200" aria-labelledby="debug-plugin-titel">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 id="debug-plugin-titel" className="font-semibold">Debug-Protokoll <span className="text-xs font-normal text-slate-500 dark:text-slate-400">Mitgeliefertes System-Plugin</span></h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Immer verfügbar, auch wenn externe Plugins ausgeschaltet sind. Du entscheidest, was aufgezeichnet wird.</p>
        </div>
        <label className="flex items-center gap-2 text-sm shrink-0">
          <input type="checkbox" checked={data?.aktiviert ?? false} disabled={!data || speichern.isPending}
            onChange={e => data && speichern.mutate({ aktiviert: e.target.checked, kategorien: data.kategorien })} />
          Aufzeichnen
        </label>
      </div>
      {isLoading && <p className="text-sm mt-3">Lade Debug-Einstellungen…</p>}
      {data && <>
        <fieldset className="mt-4 space-y-2" disabled={speichern.isPending}>
          <legend className="text-sm font-medium mb-2">Diese Interaktionen protokollieren</legend>
          {kategorien.map(k => <label key={k.id} className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={data.kategorien.includes(k.id)} onChange={e => speichern.mutate({
              aktiviert: data.aktiviert,
              kategorien: e.target.checked ? [...data.kategorien, k.id] : data.kategorien.filter(id => id !== k.id),
            })} />{k.name}
          </label>)}
        </fieldset>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-3">Gespeichert werden technische Metadaten ohne Formularwerte, Passwörter, Anfrageinhalte oder Belegtexte. Maximal {(data.max_bytes * (data.sicherungen + 1) / 1024 / 1024).toLocaleString('de-DE')} MB mit automatischer Rotation. Vorhandene Einträge bleiben beim Ausschalten erhalten.</p>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 break-all">Logdatei: <code>{data.logdatei}</code></p>
        {data.schreibfehler && <p role="alert" className="text-sm text-red-600 mt-2">Das Protokoll konnte nicht geschrieben werden. Prüfe freien Speicher und Schreibrechte im Profilordner.</p>}
        <div className="flex flex-wrap gap-2 mt-4">
          <button type="button" className={btn} aria-expanded={offen} aria-controls="debug-protokoll" onClick={() => setOffen(!offen)}>{offen ? 'Protokoll ausblenden' : 'Protokoll anzeigen'}</button>
          <button type="button" className={btn} disabled={download.isPending} onClick={() => download.mutate()}>Logdatei herunterladen</button>
        </div>
      </>}
      {(error || speichern.error || download.error) && <p role="alert" className="text-sm text-red-600 dark:text-red-400 mt-3">{(error || speichern.error || download.error)?.message}</p>}
      {offen && <div id="debug-protokoll" className="mt-4">
        <div className="flex flex-wrap items-center gap-3 mb-3 text-sm">
          <label>Kategorie <select className="ml-2 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 p-1" value={filter} onChange={e => setFilter(e.target.value as DebugKategorie | '')}>
            <option value="">Alle</option>{kategorien.map(k => <option key={k.id} value={k.id}>{k.name}</option>)}
          </select></label>
          <label className="flex items-center gap-2"><input type="checkbox" checked={live} onChange={e => setLive(e.target.checked)} />Live aktualisieren</label>
          <button type="button" className={btn} disabled={protokoll.isFetching} onClick={() => void protokoll.refetch()}>Aktualisieren</button>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">Neueste 200 Einträge, neueste zuerst. Die Bedienung dieser Protokollansicht wird nicht aufgezeichnet.</p>
        {protokoll.error ? <p role="alert" className="text-sm text-red-600">{protokoll.error.message}</p>
          : protokoll.isLoading ? <p className="text-sm">Lade Protokoll…</p>
          : !protokoll.data?.length ? <p className="text-sm text-slate-500">Noch keine passenden Einträge.</p>
          : <ol className="max-h-96 overflow-auto text-xs font-mono divide-y divide-slate-200 dark:divide-slate-700 rounded border border-slate-200 dark:border-slate-700">
            {protokoll.data.map((e, i) => <li key={`${e.zeit}-${i}`} className="p-2 break-words">
              <span className="text-slate-500 dark:text-slate-400">{new Date(e.zeit).toLocaleString('de-DE')}</span>{' '}
              <strong>{e.kategorie}</strong>{' '}
              {Object.entries(e).filter(([k]) => k !== 'zeit' && k !== 'kategorie').map(([k, v]) => `${k}=${v}`).join(' · ')}
            </li>)}
          </ol>}
      </div>}
    </section>
  )
}
