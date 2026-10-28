import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  aktivierePlugin,
  deaktivierePlugin,
  entfernePlugin,
  getPluginProtokoll,
  getPlugins,
  installierePlugin,
  oeffnePluginOrdner,
  setPluginHooks,
  setPluginsGlobal,
  testePlugin,
  type PluginEintrag,
  type PluginStatusWert,
  type PluginTestlaufAntwort,
  type PluginUebersicht,
} from '../../api/client'
import { DebugPluginKarte } from './DebugPluginKarte'
import { useMxAuto } from '../../hooks/useAnsicht'

// Einstellungen → Plugins (docs/plan-plugin-system.md, Phase 2): alle gefundenen Plugins
// anzeigen, einzeln an-/ausschalten, Rechte bestätigen, installieren und entfernen.

const STATUS_ANZEIGE: Record<PluginStatusWert, { text: string; cls: string }> = {
  neu: { text: 'Neu', cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300' },
  aktiv: { text: 'Aktiv', cls: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300' },
  aktualisiert: { text: 'Aktualisiert', cls: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300' },
  deaktiviert: { text: 'Aus', cls: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300' },
  rechte_erweitert: { text: 'Neue Rechte angefordert', cls: 'bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-300' },
  fehlerhaft: { text: 'Fehlerhaft', cls: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300' },
  automatisch_deaktiviert: { text: 'Automatisch abgeschaltet', cls: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300' },
  fehlt: { text: 'Dateien fehlen', cls: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300' },
}

const EINGESCHALTET: PluginStatusWert[] = ['aktiv', 'aktualisiert']
const NICHT_SCHALTBAR: PluginStatusWert[] = ['fehlerhaft', 'fehlt']

const btnCls = 'inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50'

function Icon({ name, size = 18 }: { name: string; size?: number }) {
  return <span aria-hidden="true" className="material-symbols-outlined shrink-0" style={{ fontSize: `${size}px` }}>{name}</span>
}

function Schalter({ checked, disabled, onChange, label }: { checked: boolean; disabled?: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-800 disabled:opacity-40 disabled:cursor-not-allowed ${checked ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-600'}`}
    >
      <span className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${checked ? 'translate-x-5' : 'translate-x-0.5'}`} />
    </button>
  )
}

function formatGroesse(bytes: number | null) {
  if (bytes == null) return '–'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function formatZeit(iso: string | null) {
  if (!iso) return '–'
  return new Date(iso).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' })
}

// ---------------------------------------------------------------------------
// Bestätigungsdialog beim Aktivieren
// ---------------------------------------------------------------------------

function AktivierenDialog({ plugin, onAbbrechen, onBestaetigen, laeuft, fehler }: {
  plugin: PluginEintrag
  onAbbrechen: () => void
  onBestaetigen: () => void
  laeuft: boolean
  fehler: string | null
}) {
  const erweitert = plugin.status === 'rechte_erweitert'
  const update = plugin.status === 'aktualisiert'
  const preHooks = plugin.hooks.filter(h => h.vor_dem_speichern)
  const schreibrechte = Object.values(plugin.rechte?.entities ?? {}).some(a => a.some(x => x !== 'read'))
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true" aria-labelledby="plugin-dialog-titel">
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-lg flex flex-col gap-4 p-6 max-h-[90vh] overflow-y-auto">
        <div>
          <h2 id="plugin-dialog-titel" className="text-base font-semibold text-slate-800 dark:text-slate-100">
            {erweitert ? 'Neue Rechte bestätigen' : update ? 'Update bestätigen' : 'Plugin aktivieren'}
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            <span className="font-medium text-slate-700 dark:text-slate-200">{plugin.name}</span> {plugin.version}
            {plugin.author && <> von {plugin.author}</>}
          </p>
        </div>

        {erweitert && (plugin.neue_rechte_klartext.length > 0 || plugin.neue_hooks_klartext.length > 0) && (
          <div className="rounded-lg border border-amber-300 bg-amber-50 dark:bg-amber-900/30 dark:border-amber-700 p-3 text-sm text-amber-900 dark:text-amber-200">
            <p className="font-medium mb-1">Mit diesem Update möchte das Plugin zusätzlich:</p>
            <ul className="list-disc ml-5 space-y-0.5">
              {plugin.neue_rechte_klartext.map(r => <li key={r}>{r}</li>)}
              {plugin.neue_hooks_klartext.map(h => <li key={h}>{h}</li>)}
            </ul>
          </div>
        )}

        <div className="text-sm">
          <p className="font-medium text-slate-700 dark:text-slate-200 mb-1">Das Plugin darf:</p>
          {plugin.rechte_klartext.length === 0 && plugin.hooks.length === 0 ? (
            <p className="text-slate-500 dark:text-slate-400">Nichts – es fordert keine Rechte an.</p>
          ) : (
            <ul className="list-disc ml-5 space-y-0.5 text-slate-600 dark:text-slate-300">
              {plugin.rechte_klartext.map(r => <li key={r}>{r}</li>)}
              {plugin.hooks.map(h => <li key={h.hook}>{h.beschreibung}</li>)}
            </ul>
          )}
        </div>

        {schreibrechte && (
          <p className="text-sm text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
            Mit diesen Rechten kann das Plugin Kunden, Artikel oder Rechnungsentwürfe anlegen, ändern oder löschen.
            Rechnungsabschlüsse und Belege bleiben geschützt. Aufgaben werden noch nicht unterstützt.
          </p>
        )}

        {preHooks.length > 0 && (
          <p className="text-sm text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
            Dieses Plugin läuft <strong>vor dem Speichern</strong>. Es kann Daten vor dem Speichern verändern oder das Speichern
            mit einer Meldung verhindern.
          </p>
        )}

        <p className="text-xs text-slate-400 dark:text-slate-500">
          Plugins laufen abgeschottet: kein Zugriff auf Dateien, Internet oder andere Programme – nur auf die oben genannten Daten.
          Aktiviere nur Plugins, deren Herkunft du vertraust.
        </p>

        {fehler && <p className="text-sm text-red-600 dark:text-red-400" role="alert">{fehler}</p>}

        <div className="flex justify-end gap-2 pt-1">
          <button type="button" onClick={onAbbrechen} className={btnCls}>Abbrechen</button>
          <button
            type="button"
            onClick={onBestaetigen}
            disabled={laeuft}
            className="px-4 py-1.5 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {laeuft ? 'Speichere…' : erweitert || update ? 'Bestätigen' : 'Aktivieren'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Protokoll (nur beim Aufklappen geladen)
// ---------------------------------------------------------------------------

function Protokoll({ pluginId }: { pluginId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['plugin-protokoll', pluginId],
    queryFn: () => getPluginProtokoll(pluginId, 20),
  })
  if (isLoading) return <p className="text-xs text-slate-400">Lade…</p>
  if (!data?.length) return <p className="text-xs text-slate-400 dark:text-slate-500">Noch keine Einträge.</p>
  return (
    <ul className="text-xs space-y-1 text-slate-600 dark:text-slate-300">
      {data.map(e => (
        <li key={e.id} className="flex gap-2">
          <span className="text-slate-400 dark:text-slate-500 tabular-nums shrink-0">{formatZeit(e.erstellt_am)}</span>
          <span className="font-medium shrink-0">{e.ergebnis}</span>
          <span className="truncate" title={e.meldung ?? undefined}>{e.hook !== 'verwaltung' ? e.hook : ''} {e.meldung}</span>
        </li>
      ))}
    </ul>
  )
}

// ---------------------------------------------------------------------------
// Testlauf: einen Hook mit eigenem Payload ausprobieren
// ---------------------------------------------------------------------------

const TESTLAUF_ANZEIGE: Record<PluginTestlaufAntwort['ergebnis'], { text: string; cls: string }> = {
  ok: { text: 'Durchgelassen, ohne Änderung', cls: 'text-green-700 dark:text-green-400' },
  geaendert: { text: 'Durchgelassen, Daten geändert', cls: 'text-green-700 dark:text-green-400' },
  abgebrochen: { text: 'Speichern würde verhindert', cls: 'text-amber-700 dark:text-amber-400' },
  fehler: { text: 'Fehler im Plugin', cls: 'text-red-700 dark:text-red-400' },
  timeout: { text: 'Zeitlimit überschritten', cls: 'text-red-700 dark:text-red-400' },
}

function Testlauf({ plugin }: { plugin: PluginEintrag }) {
  const qc = useQueryClient()
  const [hook, setHook] = useState(plugin.hooks[0]?.hook ?? '')
  const [payload, setPayload] = useState('{\n  \n}')
  const lauf = useMutation({
    mutationFn: () => testePlugin(plugin.plugin_id, hook, payload),
    onSettled: () => qc.invalidateQueries({ queryKey: ['plugin-protokoll', plugin.plugin_id] }),
  })
  const antwort = lauf.data
  const anzeige = antwort ? TESTLAUF_ANZEIGE[antwort.ergebnis] : null
  const idBasis = `testlauf-${plugin.plugin_id}`

  let ausgabe: string | null = null
  if (antwort?.payload_json && antwort.ergebnis === 'geaendert') {
    try { ausgabe = JSON.stringify(JSON.parse(antwort.payload_json), null, 2) } catch { ausgabe = antwort.payload_json }
  }

  return (
    <div>
      <p className="font-medium text-slate-700 dark:text-slate-200 mb-1">Testlauf</p>
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">
        Ruft das Plugin mit Beispieldaten auf – ohne Zugriff auf deine echten Daten und ohne etwas zu speichern.
      </p>
      <div className="space-y-2">
        <div>
          <label htmlFor={`${idBasis}-hook`} className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Wann</label>
          <select
            id={`${idBasis}-hook`}
            value={hook}
            onChange={e => setHook(e.target.value)}
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm dark:bg-slate-700 dark:text-slate-100"
          >
            {plugin.hooks.map(h => <option key={h.hook} value={h.hook}>{h.beschreibung}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor={`${idBasis}-payload`} className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Beispieldaten (JSON)</label>
          <textarea
            id={`${idBasis}-payload`}
            value={payload}
            onChange={e => setPayload(e.target.value)}
            rows={4}
            spellCheck={false}
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-xs font-mono dark:bg-slate-700 dark:text-slate-100"
          />
        </div>
        <button type="button" className={btnCls} disabled={!hook || lauf.isPending} onClick={() => lauf.mutate()}>
          <Icon name="play_arrow" size={16} /> {lauf.isPending ? 'Läuft…' : 'Testen'}
        </button>
        <div aria-live="polite">
          {lauf.error && <p className="text-sm text-red-600 dark:text-red-400">{(lauf.error as Error).message}</p>}
          {antwort && anzeige && (
            <div className="text-sm space-y-1">
              <p>
                <span className={`font-medium ${anzeige.cls}`}>{anzeige.text}</span>
                <span className="text-xs text-slate-400 dark:text-slate-500 ml-2">{antwort.dauer_ms.toLocaleString('de-DE')} ms</span>
              </p>
              {antwort.meldung && <p className="text-slate-600 dark:text-slate-300">Meldung: {antwort.meldung}</p>}
              {ausgabe && (
                <pre className="text-xs font-mono bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700 rounded-lg p-2 overflow-x-auto max-h-48">{ausgabe}</pre>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Eine Plugin-Karte
// ---------------------------------------------------------------------------

function PluginKarte({ plugin, globalAktiv, abgesichert, onAktivieren }: {
  plugin: PluginEintrag
  globalAktiv: boolean
  abgesichert: boolean
  onAktivieren: (p: PluginEintrag) => void
}) {
  const qc = useQueryClient()
  const [offen, setOffen] = useState(false)
  const [loeschenFragen, setLoeschenFragen] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)

  const aktualisieren = () => {
    qc.invalidateQueries({ queryKey: ['plugins'] })
    qc.invalidateQueries({ queryKey: ['plugin-protokoll', plugin.plugin_id] })
  }

  const deaktivieren = useMutation({
    mutationFn: () => deaktivierePlugin(plugin.plugin_id),
    onSuccess: () => { setFehler(null); aktualisieren() },
    onError: (e: Error) => setFehler(e.message),
  })
  const hooks = useMutation({
    mutationFn: (abgeschaltet: string[]) => setPluginHooks(plugin.plugin_id, abgeschaltet),
    onSuccess: () => { setFehler(null); aktualisieren() },
    onError: (e: Error) => setFehler(e.message),
  })
  const entfernen = useMutation({
    mutationFn: () => entfernePlugin(plugin.plugin_id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plugins'] }),
    onError: (e: Error) => { setFehler(e.message); setLoeschenFragen(false) },
  })

  const eingeschaltet = EINGESCHALTET.includes(plugin.status)
  const schaltbar = !NICHT_SCHALTBAR.includes(plugin.status)
  const status = STATUS_ANZEIGE[plugin.status]
  const abgeschaltet = plugin.hooks.filter(h => h.abgeschaltet).map(h => h.hook)

  function hookUmschalten(hook: string, an: boolean) {
    const neu = an ? abgeschaltet.filter(h => h !== hook) : [...abgeschaltet, hook]
    hooks.mutate(neu)
  }

  return (
    <li className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
      <div className="flex items-start gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-medium text-slate-800 dark:text-slate-100">{plugin.name}</h3>
            {plugin.version && <span className="text-xs text-slate-400 dark:text-slate-500">{plugin.version}</span>}
            <span className={`text-xs px-2 py-0.5 rounded-full ${status.cls}`}>{status.text}</span>
          </div>
          {plugin.author && <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">von {plugin.author}</p>}
          {plugin.description && <p className="text-sm text-slate-600 dark:text-slate-300 mt-2">{plugin.description}</p>}
        </div>
        <Schalter
          checked={eingeschaltet}
          disabled={!schaltbar || deaktivieren.isPending}
          label={`${plugin.name} ${eingeschaltet ? 'ausschalten' : 'einschalten'}`}
          onChange={an => (an ? onAktivieren(plugin) : deaktivieren.mutate())}
        />
      </div>

      {/* Hinweise je nach Status */}
      {plugin.status === 'rechte_erweitert' && (
        <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-amber-800 dark:text-amber-300">
          <span>Ein Update fordert zusätzliche Rechte an. Bis du sie bestätigst, ist das Plugin angehalten.</span>
          <button type="button" className={btnCls} onClick={() => onAktivieren(plugin)}>Rechte prüfen</button>
        </div>
      )}
      {plugin.status === 'aktualisiert' && (
        <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-slate-600 dark:text-slate-300">
          <span>Die Plugin-Datei wurde aktualisiert. Die Rechte sind unverändert, das Plugin bleibt aktiv.</span>
          <button type="button" className={btnCls} onClick={() => onAktivieren(plugin)}>Update bestätigen</button>
        </div>
      )}
      {plugin.status === 'automatisch_deaktiviert' && (
        <p className="mt-3 text-sm text-red-700 dark:text-red-400">
          Nach {plugin.fehler_in_folge} Fehlern in Folge automatisch abgeschaltet
          {plugin.letzter_fehler && <>: {plugin.letzter_fehler}</>}. Du kannst es wieder einschalten.
        </p>
      )}
      {eingeschaltet && (!globalAktiv || abgesichert) && (
        <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
          Läuft gerade nicht, weil {abgesichert ? 'RechnungsFee im abgesicherten Modus gestartet wurde' : 'Plugins oben insgesamt ausgeschaltet sind'}.
        </p>
      )}
      {plugin.fehler.length > 0 && (
        <ul className="mt-3 text-sm text-red-700 dark:text-red-400 list-disc ml-5 space-y-0.5">
          {plugin.fehler.map(f => <li key={f}>{f}</li>)}
        </ul>
      )}
      {fehler && <p className="mt-3 text-sm text-red-600 dark:text-red-400" role="alert">{fehler}</p>}

      <button
        type="button"
        onClick={() => setOffen(!offen)}
        aria-expanded={offen}
        className="mt-3 inline-flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:underline"
      >
        <Icon name={offen ? 'expand_less' : 'expand_more'} />
        {offen ? 'Details ausblenden' : 'Details'}
      </button>

      {offen && (
        <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700 space-y-4 text-sm">
          {(plugin.rechte_klartext.length > 0 || plugin.hooks.length > 0) && (
            <div>
              <p className="font-medium text-slate-700 dark:text-slate-200 mb-1">Rechte</p>
              {plugin.rechte_klartext.length > 0 ? (
                <ul className="list-disc ml-5 space-y-0.5 text-slate-600 dark:text-slate-300">
                  {plugin.rechte_klartext.map(r => <li key={r}>{r}</li>)}
                </ul>
              ) : (
                <p className="text-slate-500 dark:text-slate-400">Kein Zugriff auf gespeicherte Daten.</p>
              )}
            </div>
          )}

          {plugin.hooks.length > 0 && (
            <fieldset>
              <legend className="font-medium text-slate-700 dark:text-slate-200 mb-1">Wann das Plugin läuft</legend>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">Einzelne Punkte kannst du abschalten, ohne das ganze Plugin auszuschalten.</p>
              <ul className="space-y-1.5">
                {plugin.hooks.map(h => (
                  <li key={h.hook}>
                    <label className="flex items-center gap-2 text-slate-600 dark:text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        className="rounded"
                        checked={!h.abgeschaltet}
                        disabled={hooks.isPending}
                        onChange={e => hookUmschalten(h.hook, e.target.checked)}
                      />
                      {h.beschreibung}
                      <code className="text-xs text-slate-400 dark:text-slate-500">{h.hook}</code>
                    </label>
                  </li>
                ))}
              </ul>
            </fieldset>
          )}

          {plugin.warnungen.length > 0 && (
            <div>
              <p className="font-medium text-slate-700 dark:text-slate-200 mb-1">Hinweise</p>
              <ul className="list-disc ml-5 space-y-0.5 text-amber-700 dark:text-amber-400">
                {plugin.warnungen.map(w => <li key={w}>{w}</li>)}
              </ul>
            </div>
          )}

          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
            <dt>Plugin-ID</dt><dd className="font-mono break-all">{plugin.plugin_id}</dd>
            {plugin.ordner && <><dt>Ordner</dt><dd className="font-mono break-all">{plugin.ordner}</dd></>}
            {plugin.api_version && <><dt>Schnittstelle</dt><dd>{plugin.api_version}</dd></>}
            <dt>Größe</dt><dd>{formatGroesse(plugin.wasm_bytes)}</dd>
            {plugin.wasm_sha256 && <><dt>SHA-256</dt><dd className="font-mono break-all">{plugin.wasm_sha256}</dd></>}
            {plugin.aktiviert_am && <><dt>Bestätigt am</dt><dd>{formatZeit(plugin.aktiviert_am)}</dd></>}
            {plugin.homepage && <><dt>Webseite</dt><dd><a href={plugin.homepage} target="_blank" rel="noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline break-all">{plugin.homepage}</a></dd></>}
          </dl>

          {schaltbar && plugin.hooks.length > 0 && <Testlauf plugin={plugin} />}

          <div>
            <p className="font-medium text-slate-700 dark:text-slate-200 mb-1">Letzte Ereignisse</p>
            <Protokoll pluginId={plugin.plugin_id} />
          </div>

          <div className="pt-1">
            {loeschenFragen ? (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-slate-600 dark:text-slate-300">
                  {plugin.ordner ? `Ordner „${plugin.ordner}“ löschen und Plugin entfernen?` : 'Eintrag entfernen?'}
                </span>
                <button type="button" className={btnCls} onClick={() => setLoeschenFragen(false)}>Abbrechen</button>
                <button
                  type="button"
                  disabled={entfernen.isPending}
                  onClick={() => entfernen.mutate()}
                  className="px-3 py-1.5 text-sm rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
                >
                  Entfernen
                </button>
              </div>
            ) : (
              <button type="button" className={`${btnCls} text-red-600 dark:text-red-400`} onClick={() => setLoeschenFragen(true)}>
                <Icon name="delete" size={16} /> Plugin entfernen
              </button>
            )}
          </div>
        </div>
      )}
    </li>
  )
}

// ---------------------------------------------------------------------------
// Seite
// ---------------------------------------------------------------------------

export function PluginsPage() {
  const mxAuto = useMxAuto()
  const qc = useQueryClient()
  const dateiInput = useRef<HTMLInputElement>(null)
  const [dialogPlugin, setDialogPlugin] = useState<PluginEintrag | null>(null)
  const [dialogFehler, setDialogFehler] = useState<string | null>(null)
  const [meldung, setMeldung] = useState<{ text: string; fehler: boolean } | null>(null)

  const { data, isLoading, isFetching, refetch, error } = useQuery({ queryKey: ['plugins'], queryFn: getPlugins })

  const global = useMutation({
    mutationFn: setPluginsGlobal,
    onSuccess: (d: PluginUebersicht) => qc.setQueryData(['plugins'], d),
    onError: (e: Error) => setMeldung({ text: e.message, fehler: true }),
  })

  const aktivieren = useMutation({
    mutationFn: aktivierePlugin,
    onSuccess: (p) => {
      setDialogPlugin(null)
      setDialogFehler(null)
      qc.invalidateQueries({ queryKey: ['plugins'] })
      qc.invalidateQueries({ queryKey: ['plugin-protokoll', p.plugin_id] })
    },
    onError: (e: Error) => {
      setDialogFehler(e.message)
      // 409: Plugin hat sich geändert - frische Daten holen, damit der Dialog den neuen Stand zeigt
      qc.invalidateQueries({ queryKey: ['plugins'] })
    },
  })

  const installieren = useMutation({
    mutationFn: installierePlugin,
    onSuccess: (p) => {
      setMeldung({
        text: p.status === 'neu'
          ? `„${p.name}“ wurde installiert. Schalte es ein, um es zu verwenden.`
          : `„${p.name}“ wurde aktualisiert.`,
        fehler: false,
      })
      qc.invalidateQueries({ queryKey: ['plugins'] })
    },
    onError: (e: Error) => setMeldung({ text: e.message, fehler: true }),
  })

  const ordner = useMutation({
    mutationFn: oeffnePluginOrdner,
    onError: (e: Error) => setMeldung({ text: e.message, fehler: true }),
  })

  function dateiGewaehlt(e: React.ChangeEvent<HTMLInputElement>) {
    const datei = e.target.files?.[0]
    e.target.value = ''
    if (datei) {
      setMeldung(null)
      installieren.mutate(datei)
    }
  }

  // Dialog immer mit dem aktuellsten Stand des Plugins anzeigen (nach 409 neu geladen)
  const dialogAktuell = dialogPlugin
    ? data?.plugins.find(p => p.plugin_id === dialogPlugin.plugin_id) ?? dialogPlugin
    : null

  return (
    <div className={`p-6 max-w-3xl ${mxAuto}`}>
      <div className="flex items-center gap-2 mb-1">
        <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Plugins</h2>
        <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-300">Experimentell</span>
      </div>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        Plugins erweitern RechnungsFee um eigene Prüfungen und Automatisierungen. Neue Plugins sind zunächst aus –
        du entscheidest für jedes einzeln, ob es laufen darf und siehst vorher, worauf es zugreifen will.
      </p>

      <DebugPluginKarte />

      {data?.abgesicherter_modus && (
        <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 dark:bg-amber-900/30 dark:border-amber-700 p-3 text-sm text-amber-900 dark:text-amber-200" role="status">
          RechnungsFee wurde im abgesicherten Modus gestartet (<code>RECHNUNGSFEE_PLUGINS=0</code>). Plugins lassen sich verwalten,
          laufen aber nicht, bis du ohne diese Einstellung neu startest.
        </div>
      )}

      {/* Hauptschalter */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 mb-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="font-medium text-slate-800 dark:text-slate-100" id="plugins-global-label">Plugins verwenden</p>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
              Ist dieser Schalter aus, läuft kein externes Plugin – auch keines, das unten eingeschaltet ist. Das mitgelieferte Debug-Protokoll hat einen eigenen Schalter.
            </p>
          </div>
          <Schalter
            checked={!!data?.plugins_aktiv}
            disabled={!data || global.isPending}
            label="Plugins verwenden"
            onChange={v => global.mutate(v)}
          />
        </div>
      </div>

      {/* Werkzeugleiste */}
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <input ref={dateiInput} type="file" accept=".rfplugin,.zip" className="hidden" onChange={dateiGewaehlt} />
        <button type="button" className={btnCls} disabled={installieren.isPending} onClick={() => dateiInput.current?.click()}>
          <Icon name="upload" size={16} /> {installieren.isPending ? 'Installiere…' : 'Plugin installieren…'}
        </button>
        <button type="button" className={btnCls} onClick={() => ordner.mutate()}>
          <Icon name="folder_open" size={16} /> Ordner öffnen
        </button>
        <button type="button" className={btnCls} disabled={isFetching} onClick={() => refetch()}>
          <Icon name="refresh" size={16} /> Neu einlesen
        </button>
      </div>
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">
        Wähle das fertige <code>.rfplugin</code>- oder <code>.zip</code>-Paket mit Manifest, nicht die einzelne <code>plugin.wasm</code>.
      </p>
      {data && (
        <p className="text-xs text-slate-400 dark:text-slate-500 mb-4 break-all">
          Plugin-Ordner: <span className="font-mono">{data.verzeichnis}</span>
        </p>
      )}
      {meldung && (
        <p className={`text-sm mb-4 ${meldung.fehler ? 'text-red-600 dark:text-red-400' : 'text-green-700 dark:text-green-400'}`} role={meldung.fehler ? 'alert' : 'status'}>
          {meldung.text}
        </p>
      )}

      {isLoading ? (
        <p className="text-slate-400 text-sm">Lade…</p>
      ) : error ? (
        <p className="text-red-600 text-sm">{(error as Error).message}</p>
      ) : !data?.plugins.length ? (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-dashed border-slate-300 dark:border-slate-600 p-8 text-center">
          <Icon name="extension" size={32} />
          <p className="font-medium text-slate-700 dark:text-slate-200 mt-2">Noch keine Plugins vorhanden</p>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Installiere ein Plugin-Paket (<code>.rfplugin</code>) oder lege einen Plugin-Ordner mit <code>plugin.toml</code> und{' '}
            <code>plugin.wasm</code> in den Plugin-Ordner und klicke auf „Neu einlesen“.
          </p>
        </div>
      ) : (
        <ul className="space-y-4">
          {data.plugins.map(p => (
            <PluginKarte
              key={p.plugin_id}
              plugin={p}
              globalAktiv={data.plugins_aktiv}
              abgesichert={data.abgesicherter_modus}
              onAktivieren={pl => { setDialogFehler(null); setDialogPlugin(pl) }}
            />
          ))}
        </ul>
      )}

      {dialogAktuell && (
        <AktivierenDialog
          plugin={dialogAktuell}
          laeuft={aktivieren.isPending}
          fehler={dialogFehler}
          onAbbrechen={() => { setDialogPlugin(null); setDialogFehler(null) }}
          onBestaetigen={() => aktivieren.mutate(dialogAktuell)}
        />
      )}
    </div>
  )
}
