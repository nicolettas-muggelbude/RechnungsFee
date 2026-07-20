import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { downloadBackup, getUnternehmen, updateUnternehmen, uploadBackupWiederherstellen, getBackupListe, wiederherstellenLokal, isTauri } from '../../api/client'
import type { BackupEintrag } from '../../api/client'
import { useMxAuto } from '../../hooks/useAnsicht'

type TabId = 'backup' | 'wiederherstellung'

const inputCls = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100 dark:placeholder-slate-400"

function istSystemlaufwerk(pfad: string): boolean {
  if (!pfad || pfad.startsWith('smb://')) return false
  const p = pfad.replace(/\\/g, '/').toLowerCase().replace(/\/+$/, '')
  if (p === 'c:' || p.startsWith('c:/')) return true
  if (p.startsWith('/')) {
    const erlaubt = ['/mnt/', '/media/', '/run/media/', '/volumes/']
    return !erlaubt.some(e => p.startsWith(e))
  }
  return false
}

// ---------------------------------------------------------------------------
// Tab-Navigation
// ---------------------------------------------------------------------------

function TabNav({ active, onChange }: { active: TabId; onChange: (t: TabId) => void }) {
  const tabs: { id: TabId; label: string }[] = [
    { id: 'backup',          label: 'Backup' },
    { id: 'wiederherstellung', label: 'Wiederherstellung' },
  ]
  return (
    <div className="flex gap-0 border-b border-slate-200 dark:border-slate-700">
      {tabs.map(t => (
        <button key={t.id} type="button" onClick={() => onChange(t.id)}
          className={`px-5 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
            active === t.id
              ? 'border-blue-600 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
          }`}>
          {t.label}
        </button>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Backup-Tab
// ---------------------------------------------------------------------------

function ExterneBackupEinstellungen() {
  const queryClient = useQueryClient()
  const { data } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen })

  const [pfad1, setPfad1] = useState<string>('')
  const [pfad2, setPfad2] = useState<string>('')
  const [passwort, setPasswort] = useState<string>('')
  const [zeigPasswort, setZeigPasswort] = useState(false)
  const [smbBenutzer, setSmbBenutzer] = useState<string>('')
  const [smbPasswort, setSmbPasswort] = useState<string>('')
  const [zeigSmbPasswort, setZeigSmbPasswort] = useState(false)
  const [status, setStatus] = useState<'idle' | 'saving' | 'ok' | 'err'>('idle')

  useEffect(() => {
    if (!data) return
    setPfad1(data.backup_extern_pfad_1 ?? '')
    setPfad2(data.backup_extern_pfad_2 ?? '')
    setPasswort(data.backup_extern_passwort ?? '')
    setSmbBenutzer(data.backup_smb_benutzer ?? '')
    setSmbPasswort(data.backup_smb_passwort ?? '')
  }, [data])

  const mutation = useMutation({
    mutationFn: (payload: typeof data) => updateUnternehmen(payload!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['unternehmen'] })
      setStatus('ok')
      setTimeout(() => setStatus('idle'), 2000)
    },
    onError: () => setStatus('err'),
  })

  async function waehlePfad(setter: (v: string) => void) {
    if (!isTauri()) return
    try {
      const { open } = await import('@tauri-apps/plugin-dialog')
      const selected = await open({ directory: true, title: 'Backup-Zielordner wählen' })
      if (typeof selected === 'string' && selected) setter(selected)
    } catch { /* Im Browser nicht verfügbar */ }
  }

  const hatZiel = !!(pfad1 || pfad2)
  const passwortFehlt = hatZiel && !passwort
  const kannSpeichern = !passwortFehlt && !!data && status !== 'saving'

  function speichern() {
    if (!kannSpeichern) return
    setStatus('saving')
    mutation.mutate({ ...data!, backup_extern_pfad_1: pfad1 || null, backup_extern_pfad_2: pfad2 || null, backup_extern_passwort: passwort || null, backup_smb_benutzer: smbBenutzer || null, backup_smb_passwort: smbPasswort || null })
  }

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
      <div className="bg-blue-600 px-6 py-4">
        <h2 className="text-white font-bold text-lg">Automatisches Backup beim Beenden</h2>
        <p className="text-blue-100 text-sm mt-0.5">
          Beim Schließen der App auf NAS, USB oder Netzlaufwerk sichern – immer AES-256-verschlüsselt (DSGVO Art. 32)
        </p>
      </div>
      <div className="p-6 space-y-5">
        <div className="space-y-4">
          <div className="space-y-1">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200">Ziel 1</label>
            <div className="flex gap-2">
              <input type="text" value={pfad1} onChange={e => setPfad1(e.target.value)}
                placeholder="z.B. /mnt/nas/backup, \\NAS\backup oder smb://server/freigabe/backup"
                className={`${inputCls} flex-1`} />
              {isTauri() && (
                <button type="button" onClick={() => waehlePfad(setPfad1)}
                  className="px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 whitespace-nowrap">
                  Ordner wählen
                </button>
              )}
            </div>
            {istSystemlaufwerk(pfad1) && (
              <p className="text-xs text-amber-700 dark:text-amber-400">
                Systemlaufwerk – Backup wird beim Beenden übersprungen. Bitte ein externes Laufwerk, NAS oder SMB-Pfad verwenden.
              </p>
            )}
          </div>
          <div className="space-y-1">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200">
              Ziel 2 <span className="font-normal text-slate-400">(optional)</span>
            </label>
            <div className="flex gap-2">
              <input type="text" value={pfad2} onChange={e => setPfad2(e.target.value)}
                placeholder="z.B. /media/usb/backup"
                className={`${inputCls} flex-1`} />
              {isTauri() && (
                <button type="button" onClick={() => waehlePfad(setPfad2)}
                  className="px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 whitespace-nowrap">
                  Ordner wählen
                </button>
              )}
            </div>
            {istSystemlaufwerk(pfad2) && (
              <p className="text-xs text-amber-700 dark:text-amber-400">
                Systemlaufwerk – Backup wird beim Beenden übersprungen. Bitte ein externes Laufwerk, NAS oder SMB-Pfad verwenden.
              </p>
            )}
          </div>
        </div>

        {/* SMB-Zugangsdaten – erscheinen nur wenn mindestens ein smb://-Pfad eingetragen ist */}
        {(pfad1.startsWith('smb://') || pfad2.startsWith('smb://')) && (
          <>
            <hr className="border-slate-100 dark:border-slate-700" />
            <div className="space-y-3">
              <p className="text-sm font-medium text-slate-700 dark:text-slate-200">SMB-Zugangsdaten</p>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="block text-xs text-slate-500 dark:text-slate-400">Benutzername</label>
                  <input type="text" value={smbBenutzer} onChange={e => setSmbBenutzer(e.target.value)}
                    placeholder="z.B. backup-user"
                    className={inputCls} />
                </div>
                <div className="space-y-1">
                  <label className="block text-xs text-slate-500 dark:text-slate-400">Passwort</label>
                  <div className="relative">
                    <input type={zeigSmbPasswort ? 'text' : 'password'} value={smbPasswort} onChange={e => setSmbPasswort(e.target.value)}
                      placeholder="SMB-Passwort"
                      className={`${inputCls} pr-20`} />
                    <button type="button" onClick={() => setZeigSmbPasswort(z => !z)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 px-2 py-1">
                      {zeigSmbPasswort ? 'Verbergen' : 'Anzeigen'}
                    </button>
                  </div>
                </div>
              </div>
              <p className="text-xs text-slate-400 dark:text-slate-500">
                Wird nur für smb://-Pfade verwendet. Leer lassen wenn die Freigabe ohne Passwort erreichbar ist.
              </p>
            </div>
          </>
        )}

        <hr className="border-slate-100 dark:border-slate-700" />

        <div className="space-y-2">
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200">
            Verschlüsselungs-Passwort{hatZiel && <span className="ml-1 text-red-500">*</span>}
          </label>
          <div className="relative">
            <input type={zeigPasswort ? 'text' : 'password'} value={passwort} onChange={e => setPasswort(e.target.value)}
              placeholder={hatZiel ? 'Pflichtfeld – externes Backup ist immer verschlüsselt' : 'Wird benötigt sobald ein Ziel konfiguriert ist'}
              className={`${inputCls} pr-24 ${passwortFehlt ? 'border-red-400 focus:ring-red-400' : ''}`} />
            <button type="button" onClick={() => setZeigPasswort(z => !z)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 px-2 py-1">
              {zeigPasswort ? 'Verbergen' : 'Anzeigen'}
            </button>
          </div>
          {passwortFehlt && (
            <p className="text-xs text-red-600 dark:text-red-400">
              Externes Backup erfordert ein Passwort – Kundendaten müssen gemäß DSGVO Art. 32 verschlüsselt gespeichert werden.
            </p>
          )}
          {passwort && (
            <p className="text-xs text-slate-400 dark:text-slate-500">
              Datei wird als <code className="font-mono">.zip.enc</code> gespeichert. Dieses Passwort wird zur Wiederherstellung benötigt – sicher aufbewahren.
            </p>
          )}
        </div>

        <div className="flex items-center gap-3">
          <button type="button" onClick={speichern} disabled={!kannSpeichern}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">
            {status === 'saving' ? 'Wird gespeichert…' : 'Einstellungen speichern'}
          </button>
          {status === 'ok' && <span className="text-sm text-green-600 dark:text-green-400">Gespeichert</span>}
          {status === 'err' && <span className="text-sm text-red-600 dark:text-red-400">Fehler beim Speichern</span>}
        </div>
      </div>
    </div>
  )
}

function BackupTab() {
  const [laedt, setLaedt] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)
  const [erfolg, setErfolg] = useState<string | null>(null)

  async function handleBackup() {
    setLaedt(true); setFehler(null); setErfolg(null)
    try {
      const name = await downloadBackup()
      if (name) setErfolg(`Backup gespeichert: ${name}`)
    } catch (e) {
      setFehler(e instanceof Error ? e.message : 'Unbekannter Fehler')
    } finally {
      setLaedt(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Manuelles Backup */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
        <div className="bg-green-600 px-6 py-4">
          <h2 className="text-white font-bold text-lg">Manuelles Backup</h2>
          <p className="text-green-100 text-sm mt-0.5">ZIP-Archiv (Datenbank + Belege) herunterladen</p>
        </div>
        <div className="p-6 space-y-5">
          {fehler && <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3 text-sm text-red-700 dark:text-red-300">Fehler: {fehler}</div>}
          {erfolg && <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg px-4 py-3 text-sm text-green-700 dark:text-green-300">✓ {erfolg}</div>}

          <div className="flex items-start gap-4">
            <button onClick={handleBackup} disabled={laedt}
              className="flex items-center gap-2 bg-green-600 hover:bg-green-700 disabled:bg-green-300 text-white font-medium text-sm px-5 py-2 rounded-lg transition-colors shrink-0">
              {laedt ? <><span className="animate-spin">⏳</span>Wird erstellt…</> : <>💾 Backup herunterladen</>}
            </button>
            <p className="text-sm text-slate-500 dark:text-slate-400 pt-1.5">
              Dateiname: <span className="font-mono text-slate-700 dark:text-slate-200">RechnungsFee-Backup-JJJJ-MM-TT.zip</span>
            </p>
          </div>

          <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg px-4 py-3 flex gap-3">
            <span className="text-amber-500 shrink-0 mt-0.5">⚠</span>
            <p className="text-xs text-amber-800 dark:text-amber-300">
              Der Download ist <strong>unverschlüsselt</strong> – die ZIP-Datei enthält alle Kundendaten und Rechnungen im Klartext.
              Nur an sicheren, zugangsbeschränkten Orten aufbewahren.
            </p>
          </div>

          <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg p-4 space-y-2">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Was wird gesichert?</p>
            <ul className="text-sm text-slate-600 dark:text-slate-300 space-y-1">
              {['Alle Journaleinträge und Tagesabschlüsse', 'Rechnungen (Eingang & Ausgang) mit Zahlungen',
                'Kunden und Lieferanten', 'Unternehmensdaten, Konten, Kategorien',
                'Nummernkreise und alle Einstellungen', 'Hochgeladene Belege und Eingangsrechnungen (PDF, Scans)',
              ].map(item => (
                <li key={item} className="flex items-center gap-2 list-none">
                  <span className="text-green-500 shrink-0">✓</span>{item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Externe Backup-Ziele */}
      <ExterneBackupEinstellungen />

      {/* Automatische Backups – Info */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm p-6 space-y-3">
        <h2 className="font-semibold text-slate-800 dark:text-slate-100">Lokale automatische Backups</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Beim Beenden der App und vor Datenbankmigrationen wird automatisch ein lokales DB-Backup erstellt (max. 5 Kopien).
        </p>
        <div className="space-y-1.5">
          {[
            { os: 'Linux',   pfad: '~/.local/share/RechnungsFee/backups/' },
            { os: 'Windows', pfad: '%APPDATA%\\RechnungsFee\\backups\\' },
            { os: 'macOS',   pfad: '~/Library/Application Support/RechnungsFee/backups/' },
          ].map(({ os, pfad }) => (
            <div key={os} className="flex items-center gap-2 text-sm">
              <span className="text-xs bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 px-1.5 py-0.5 rounded font-medium w-16 text-center shrink-0">{os}</span>
              <code className="text-slate-600 dark:text-slate-300 font-mono text-xs">{pfad}</code>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Hilfsfunktionen
// ---------------------------------------------------------------------------

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('de-DE', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    })
  } catch {
    return iso
  }
}

// ---------------------------------------------------------------------------
// Lokale Backup-Liste
// ---------------------------------------------------------------------------

function LokaleBackupListe({ onErfolg }: { onErfolg: () => void }) {
  const { data: liste, isLoading, error } = useQuery({
    queryKey: ['backup-liste'],
    queryFn: getBackupListe,
    refetchOnWindowFocus: false,
  })
  const [selected, setSelected] = useState<BackupEintrag | null>(null)
  const [status, setStatus] = useState<'idle' | 'loading' | 'err'>('idle')
  const [fehler, setFehler] = useState<string | null>(null)

  async function wiederherstellen(eintrag: BackupEintrag) {
    setStatus('loading'); setFehler(null)
    try {
      await wiederherstellenLokal(eintrag.dateiname)
      onErfolg()
    } catch (e) {
      setFehler(e instanceof Error ? e.message : 'Unbekannter Fehler')
      setStatus('err')
    }
  }

  if (isLoading) {
    return <p className="text-sm text-slate-400 py-2">Lade Backup-Liste…</p>
  }
  if (error) {
    return <p className="text-sm text-red-500 py-2">Fehler beim Laden der Backups</p>
  }
  if (!liste || liste.length === 0) {
    return (
      <p className="text-sm text-slate-500 dark:text-slate-400 py-2">
        Noch keine lokalen Backups vorhanden. Backups werden automatisch beim Beenden der App erstellt.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <div className="divide-y divide-slate-100 dark:divide-slate-700 border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
        {liste.map(eintrag => (
          <div key={eintrag.dateiname}
            className={`flex items-center justify-between px-4 py-3 text-sm transition-colors ${
              selected?.dateiname === eintrag.dateiname
                ? 'bg-orange-50 dark:bg-orange-950'
                : 'bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-750'
            }`}>
            <div className="space-y-0.5 min-w-0">
              <p className="font-medium text-slate-800 dark:text-slate-100 truncate">
                {formatTimestamp(eintrag.timestamp)}
              </p>
              <p className="text-xs text-slate-400 font-mono">{eintrag.dateiname} · {formatBytes(eintrag.groesse)}</p>
            </div>
            <button
              type="button"
              onClick={() => setSelected(selected?.dateiname === eintrag.dateiname ? null : eintrag)}
              className="ml-3 shrink-0 px-3 py-1.5 text-xs border border-orange-300 dark:border-orange-700 text-orange-700 dark:text-orange-300 rounded-lg hover:bg-orange-50 dark:hover:bg-orange-950 transition-colors">
              Auswählen
            </button>
          </div>
        ))}
      </div>

      {selected && (
        <div className="bg-orange-50 dark:bg-orange-950 border border-orange-200 dark:border-orange-800 rounded-lg p-4 space-y-3">
          <p className="text-sm font-medium text-orange-800 dark:text-orange-200">
            Backup vom {formatTimestamp(selected.timestamp)} wiederherstellen?
          </p>
          <p className="text-xs text-orange-700 dark:text-orange-300">
            Nur die Datenbank wird wiederhergestellt – hochgeladene Belege bleiben unverändert.
            Die aktuellen Daten werden vor der Wiederherstellung automatisch gesichert.
          </p>
          {fehler && <p className="text-xs text-red-600 dark:text-red-400">{fehler}</p>}
          <div className="flex gap-2">
            <button type="button" onClick={() => { setSelected(null); setFehler(null); setStatus('idle') }}
              className="px-3 py-1.5 text-xs border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300">
              Abbrechen
            </button>
            <button type="button" onClick={() => wiederherstellen(selected)} disabled={status === 'loading'}
              className="px-3 py-1.5 text-xs bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white rounded-lg">
              {status === 'loading' ? 'Wird vorbereitet…' : 'Ja, wiederherstellen'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Wiederherstellung-Tab
// ---------------------------------------------------------------------------

function WiederherstellungTab() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [datei, setDatei] = useState<File | null>(null)
  const [passwort, setPasswort] = useState('')
  const [zeigPasswort, setZeigPasswort] = useState(false)
  const [status, setStatus] = useState<'idle' | 'uploading' | 'bereit' | 'err'>('idle')
  const [fehler, setFehler] = useState<string | null>(null)

  const istVerschluesselt = datei?.name.endsWith('.zip.enc') ?? false
  const kannWiederherstellen = !!datei && (!istVerschluesselt || !!passwort)

  function waehleDatei() {
    // Bewusst immer der native <input type="file"> – ein fruehrer Versuch, den Tauri-Dialog
    // per fetch("file://…") auszulesen, schlug unter Linux (WebKitGTK) mit "Load failed" fehl.
    fileInputRef.current?.click()
  }

  async function wiederherstellen() {
    if (!datei || !kannWiederherstellen) return
    setStatus('uploading'); setFehler(null)
    try {
      await uploadBackupWiederherstellen(datei, istVerschluesselt ? passwort : undefined)
      setStatus('bereit')
    } catch (e) {
      setFehler(e instanceof Error ? e.message : 'Unbekannter Fehler')
      setStatus('err')
    }
  }

  async function neustart() {
    if (isTauri()) {
      const { relaunch } = await import('@tauri-apps/plugin-process')
      await relaunch()
    }
  }

  const neustartBereit = status === 'bereit'

  return (
    <div className="space-y-6">

      {/* Lokale Backups */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
        <div className="bg-orange-600 px-6 py-4">
          <h2 className="text-white font-bold text-lg">Lokales Backup wiederherstellen</h2>
          <p className="text-orange-100 text-sm mt-0.5">
            Automatisch erstellte DB-Snapshots – direkt auswählen und einspielen
          </p>
        </div>
        <div className="p-6 space-y-4">
          {neustartBereit ? (
            <div className="space-y-4">
              <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg px-4 py-3 text-sm text-green-700 dark:text-green-300">
                ✓ Backup bereit – RechnungsFee stellt die Daten beim Neustart wieder her.
              </div>
              {isTauri() ? (
                <button onClick={neustart}
                  className="px-5 py-2 bg-orange-600 hover:bg-orange-700 text-white text-sm font-medium rounded-lg">
                  Jetzt neu starten und wiederherstellen
                </button>
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">Bitte starte RechnungsFee neu um die Wiederherstellung abzuschließen.</p>
              )}
            </div>
          ) : (
            <LokaleBackupListe onErfolg={() => setStatus('bereit')} />
          )}
          <p className="text-xs text-slate-400 dark:text-slate-500">
            Hinweis: Lokale Backups enthalten nur die Datenbank – hochgeladene Belege bleiben beim Wiederherstellen unverändert.
          </p>
        </div>
      </div>

      {/* Manuelles ZIP-Backup hochladen */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700">
          <h2 className="font-semibold text-slate-800 dark:text-slate-100">ZIP-Backup hochladen</h2>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">
            Manuelles Backup (.zip) oder verschlüsseltes externes Backup (.zip.enc) einspielen
          </p>
        </div>
        <div className="p-6 space-y-5">
          <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3 flex gap-3">
            <span className="text-red-500 shrink-0 mt-0.5">⚠</span>
            <p className="text-xs text-red-800 dark:text-red-300">
              <strong>Achtung:</strong> Die Wiederherstellung überschreibt alle aktuellen Daten unwiderruflich.
              Vor der Wiederherstellung wird automatisch ein Sicherheits-Backup der aktuellen Daten angelegt.
            </p>
          </div>

          {neustartBereit ? (
            <div className="space-y-4">
              <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg px-4 py-3 text-sm text-green-700 dark:text-green-300">
                ✓ Backup bereit – RechnungsFee stellt die Daten beim Neustart wieder her.
              </div>
              {isTauri() ? (
                <button onClick={neustart}
                  className="px-5 py-2 bg-orange-600 hover:bg-orange-700 text-white text-sm font-medium rounded-lg">
                  Jetzt neu starten und wiederherstellen
                </button>
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">Bitte starte RechnungsFee neu um die Wiederherstellung abzuschließen.</p>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <input ref={fileInputRef} type="file" accept=".zip,.zip.enc" className="hidden"
                onChange={e => { setDatei(e.target.files?.[0] ?? null); setPasswort('') }} />

              <div className="flex items-center gap-3">
                <button type="button" onClick={waehleDatei}
                  className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200">
                  Backup-Datei wählen
                </button>
                {datei && (
                  <span className="text-sm text-slate-600 dark:text-slate-300 font-mono flex items-center gap-2">
                    {datei.name}
                    {istVerschluesselt && <span className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-1.5 py-0.5 rounded">verschlüsselt</span>}
                  </span>
                )}
              </div>

              {istVerschluesselt && (
                <div className="space-y-1">
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-200">
                    Backup-Passwort <span className="text-red-500">*</span>
                  </label>
                  <div className="relative max-w-sm">
                    <input
                      type={zeigPasswort ? 'text' : 'password'}
                      value={passwort}
                      onChange={e => setPasswort(e.target.value)}
                      placeholder="Passwort das beim Backup gesetzt wurde"
                      className={`${inputCls} pr-24`}
                    />
                    <button type="button" onClick={() => setZeigPasswort(z => !z)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 px-2 py-1">
                      {zeigPasswort ? 'Verbergen' : 'Anzeigen'}
                    </button>
                  </div>
                </div>
              )}

              {fehler && <p className="text-sm text-red-600 dark:text-red-400">{fehler}</p>}

              <button onClick={wiederherstellen} disabled={!kannWiederherstellen || status === 'uploading'}
                className="px-5 py-2 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg">
                {status === 'uploading' ? 'Wird verarbeitet…' : 'Backup hochladen und vorbereiten'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Manuelle Anleitung als Fallback */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm p-6 space-y-3">
        <h2 className="font-semibold text-slate-800 dark:text-slate-100">Manuelle Wiederherstellung</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">Alternativ kannst du ein Backup manuell einspielen:</p>
        <ol className="text-sm text-slate-600 dark:text-slate-300 space-y-2 list-none">
          {[
            'RechnungsFee beenden',
            'ZIP entpacken',
            'rechnungsfee.db in den Datenpfad kopieren (vorherige DB ersetzen)',
            'uploads/-Ordner in den Datenpfad kopieren',
            'RechnungsFee neu starten',
          ].map((schritt, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center shrink-0 mt-0.5">{i + 1}</span>
              {schritt}
            </li>
          ))}
        </ol>
        <div className="space-y-1.5 pt-1">
          {[
            { os: 'Linux',   pfad: '~/.local/share/RechnungsFee/' },
            { os: 'Windows', pfad: '%APPDATA%\\RechnungsFee\\' },
            { os: 'macOS',   pfad: '~/Library/Application Support/RechnungsFee/' },
          ].map(({ os, pfad }) => (
            <div key={os} className="flex items-center gap-2 text-sm">
              <span className="text-xs bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 px-1.5 py-0.5 rounded font-medium w-16 text-center shrink-0">{os}</span>
              <code className="text-slate-600 dark:text-slate-300 font-mono text-xs">{pfad}</code>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Haupt-Seite
// ---------------------------------------------------------------------------

export function BackupPage() {
  const mxAuto = useMxAuto()
  const [activeTab, setActiveTab] = useState<TabId>('backup')

  return (
    <div className={`p-6 max-w-4xl ${mxAuto} space-y-6`}>
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Backup & Wiederherstellung</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">Deine Daten sichern und im Notfall wiederherstellen.</p>
      </div>

      <TabNav active={activeTab} onChange={setActiveTab} />

      {activeTab === 'backup'          && <BackupTab />}
      {activeTab === 'wiederherstellung' && <WiederherstellungTab />}
    </div>
  )
}
