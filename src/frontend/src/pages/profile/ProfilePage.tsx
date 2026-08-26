import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getProfile, createProfil, aktiviereProfil, benenneProfilUm, archiviereProfil,
  stelleProfilWiederHer, loescheArchiviertesProfil, isTauri,
} from '../../api/client'
import { useMxAuto } from '../../hooks/useAnsicht'

const inputCls = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100 dark:placeholder-slate-400"

async function neustart() {
  // Zwingend: nur ein Neustart lädt database/connection.py mit dem neuen Profil-Zeiger
  // neu ein (mehrere Backend-Module binden APP_DATA_DIR-abgeleitete Pfade zur
  // Importzeit, ein Wechsel zur Laufzeit würde zu Datensalat zwischen Profilen führen).
  // Bewusst OHNE kill_backend davor (anders als der Windows-Update-Installer-Pfad in
  // useUpdateCheck.ts) - genau wie beim bestehenden Backup-Wiederherstellen-Neustart
  // (BackupPage.tsx). kill_backend killt nur ein von Tauri selbst gestartetes Sidecar;
  // im lokalen Dev-Workflow (npm run tauri:dev, Backend läuft manuell in einem eigenen
  // Terminal) hat das zu "Connection refused" geführt, weil relaunch() dort die
  // gesamte Dev-Toolchain (Vite) mit beendet statt nur den App-Prozess neu zu starten.
  if (!isTauri()) return
  const { relaunch } = await import('@tauri-apps/plugin-process')
  await relaunch()
}

function NeustartHinweis({ profilName }: { profilName: string }) {
  const [gestartet, setGestartet] = useState(false)
  return (
    <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg p-4 space-y-3">
      <p className="text-sm font-medium text-green-800 dark:text-green-200">
        „{profilName}" ist bereit – RechnungsFee muss neu gestartet werden, damit der Wechsel wirksam wird.
      </p>
      <button
        type="button"
        onClick={() => { setGestartet(true); neustart() }}
        disabled={gestartet}
        className="px-4 py-2 text-sm font-medium bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded-lg transition-colors"
      >
        {gestartet ? 'Wird neu gestartet…' : 'Jetzt neu starten'}
      </button>
    </div>
  )
}

export function ProfilePage() {
  const mxAuto = useMxAuto()
  const qc = useQueryClient()
  const [neuerName, setNeuerName] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)
  const [neustartFuer, setNeustartFuer] = useState<string | null>(null)

  const [umbenennenFuer, setUmbenennenFuer] = useState<string | null>(null)
  const [umbenennenWert, setUmbenennenWert] = useState('')
  const [loeschenFuer, setLoeschenFuer] = useState<string | null>(null)
  const [loeschenEingabe, setLoeschenEingabe] = useState('')

  const { data, isLoading } = useQuery({ queryKey: ['profile'], queryFn: getProfile })

  const createMut = useMutation({
    mutationFn: (name: string) => createProfil(name),
    onSuccess: (_, name) => {
      setFehler(null)
      setNeuerName('')
      setNeustartFuer(name)
      qc.invalidateQueries({ queryKey: ['profile'] })
    },
    onError: (e: Error) => setFehler(e.message),
  })

  const aktivierenMut = useMutation({
    mutationFn: (name: string) => aktiviereProfil(name),
    onSuccess: (_, name) => {
      setFehler(null)
      setNeustartFuer(name)
      qc.invalidateQueries({ queryKey: ['profile'] })
    },
    onError: (e: Error) => setFehler(e.message),
  })

  const umbenennenMut = useMutation({
    mutationFn: ({ alterName, neuerName }: { alterName: string; neuerName: string }) =>
      benenneProfilUm(alterName, neuerName),
    onSuccess: ({ neustart_erforderlich }, { neuerName }) => {
      setFehler(null)
      setUmbenennenFuer(null)
      if (neustart_erforderlich) {
        setNeustartFuer(neuerName)
      } else {
        qc.invalidateQueries({ queryKey: ['profile'] })
      }
    },
    onError: (e: Error) => setFehler(e.message),
  })

  const archivierenMut = useMutation({
    mutationFn: (name: string) => archiviereProfil(name),
    onSuccess: () => {
      setFehler(null)
      qc.invalidateQueries({ queryKey: ['profile'] })
    },
    onError: (e: Error) => setFehler(e.message),
  })

  const wiederherstellenMut = useMutation({
    mutationFn: (name: string) => stelleProfilWiederHer(name),
    onSuccess: () => {
      setFehler(null)
      qc.invalidateQueries({ queryKey: ['profile'] })
    },
    onError: (e: Error) => setFehler(e.message),
  })

  const loeschenMut = useMutation({
    mutationFn: ({ name, eingabe }: { name: string; eingabe: string }) => loescheArchiviertesProfil(name, eingabe),
    onSuccess: () => {
      setFehler(null)
      setLoeschenFuer(null)
      setLoeschenEingabe('')
      qc.invalidateQueries({ queryKey: ['profile'] })
    },
    onError: (e: Error) => setFehler(e.message),
  })

  function anlegen() {
    const name = neuerName.trim()
    if (!name) return
    createMut.mutate(name)
  }

  function umbenennenStarten(name: string) {
    setFehler(null)
    setUmbenennenFuer(name)
    setUmbenennenWert(name)
  }

  function umbenennenSpeichern(alterName: string) {
    const neuerName = umbenennenWert.trim()
    if (!neuerName || neuerName === alterName) { setUmbenennenFuer(null); return }
    umbenennenMut.mutate({ alterName, neuerName })
  }

  function archivieren(name: string) {
    if (!window.confirm(
      `Profil „${name}" archivieren? Es verschwindet aus dieser Liste, Datenbank, Belege und Backups bleiben ` +
      `dabei unverändert erhalten – über „Archivierte Profile" jederzeit wiederherstellbar.`
    )) return
    archivierenMut.mutate(name)
  }

  function loeschenStarten(name: string) {
    setFehler(null)
    setLoeschenFuer(name)
    setLoeschenEingabe('')
  }

  return (
    <div className={`p-6 max-w-2xl ${mxAuto} space-y-6`}>
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Profile</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
          Mehrere Firmen oder Tätigkeiten getrennt in derselben Installation führen – jedes Profil hat eine
          eigene Datenbank, eigene Belege und eigene Backups. Es findet keine automatische Zusammenrechnung
          von Umsätzen über Profile hinweg statt (z. B. für die §19-Kleinunternehmergrenze oder die UStVA) –
          das bleibt in deiner Verantwortung.
        </p>
      </div>

      {neustartFuer && <NeustartHinweis profilName={neustartFuer} />}

      {!neustartFuer && (
        <>
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
            <div className="divide-y divide-slate-100 dark:divide-slate-700">
              {isLoading && <p className="p-4 text-sm text-slate-400">Lade Profile…</p>}
              {data?.profile.map((p) => (
                <div key={p.name} className="flex items-center justify-between px-4 py-3">
                  {umbenennenFuer === p.name ? (
                    <div className="flex items-center gap-2 flex-1">
                      <input
                        type="text"
                        value={umbenennenWert}
                        onChange={(e) => setUmbenennenWert(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') umbenennenSpeichern(p.name)
                          if (e.key === 'Escape') setUmbenennenFuer(null)
                        }}
                        autoFocus
                        className={inputCls}
                      />
                      <button
                        type="button"
                        onClick={() => umbenennenSpeichern(p.name)}
                        disabled={umbenennenMut.isPending || !umbenennenWert.trim()}
                        className="shrink-0 px-3 py-1.5 text-xs font-medium bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg transition-colors"
                      >
                        Speichern
                      </button>
                      <button
                        type="button"
                        onClick={() => setUmbenennenFuer(null)}
                        className="shrink-0 px-3 py-1.5 text-xs border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                      >
                        Abbrechen
                      </button>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-slate-800 dark:text-slate-100">{p.name}</span>
                        {p.aktiv && (
                          <span className="text-[10px] font-medium text-green-700 dark:text-green-300 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded px-1.5 py-0.5">
                            aktiv
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {!p.aktiv && (
                          <button
                            type="button"
                            onClick={() => aktivierenMut.mutate(p.name)}
                            disabled={aktivierenMut.isPending}
                            className="px-3 py-1.5 text-xs border border-blue-300 dark:border-blue-700 text-blue-700 dark:text-blue-300 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-950 disabled:opacity-50 transition-colors"
                          >
                            Aktivieren
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => umbenennenStarten(p.name)}
                          title="Umbenennen"
                          className="px-2 py-1.5 text-xs border border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                        >
                          ✏️
                        </button>
                        {!p.aktiv && (
                          <button
                            type="button"
                            onClick={() => archivieren(p.name)}
                            disabled={archivierenMut.isPending}
                            title="Archivieren (aus der Liste ausblenden, nichts wird gelöscht)"
                            className="px-2 py-1.5 text-xs border border-amber-200 dark:border-amber-800 text-amber-600 dark:text-amber-400 rounded-lg hover:bg-amber-50 dark:hover:bg-amber-950 disabled:opacity-50 transition-colors"
                          >
                            📥
                          </button>
                        )}
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>

          {fehler && (
            <p className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2">
              {fehler}
            </p>
          )}

          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm p-6 space-y-3">
            <h2 className="font-bold text-slate-900 dark:text-slate-100">Neues Profil anlegen</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Startet mit einer komplett leeren Datenbank – nach dem Neustart führt dich der
              Einrichtungs-Assistent durch die Ersteinrichtung, genau wie bei der ersten Installation.
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                value={neuerName}
                onChange={(e) => setNeuerName(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') anlegen() }}
                placeholder="z. B. Freiberuflich"
                className={inputCls}
              />
              <button
                type="button"
                onClick={anlegen}
                disabled={createMut.isPending || !neuerName.trim()}
                className="shrink-0 px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg transition-colors"
              >
                Anlegen
              </button>
            </div>
          </div>

          {!!data?.archiviert.length && (
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-700">
                <h2 className="font-bold text-slate-900 dark:text-slate-100">Archivierte Profile</h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Ausgeblendet, aber vollständig erhalten – Datenbank, Belege und Backups liegen unverändert bereit.
                </p>
              </div>
              <div className="divide-y divide-slate-100 dark:divide-slate-700">
                {data.archiviert.map((name) => (
                  <div key={name}>
                    <div className="flex items-center justify-between px-4 py-3">
                      <span className="text-sm font-medium text-slate-600 dark:text-slate-300">{name}</span>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => wiederherstellenMut.mutate(name)}
                          disabled={wiederherstellenMut.isPending}
                          className="px-3 py-1.5 text-xs border border-blue-300 dark:border-blue-700 text-blue-700 dark:text-blue-300 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-950 disabled:opacity-50 transition-colors"
                        >
                          Wiederherstellen
                        </button>
                        <button
                          type="button"
                          onClick={() => loeschenStarten(name)}
                          title="Endgültig löschen"
                          className="px-2 py-1.5 text-xs border border-red-200 dark:border-red-800 text-red-500 dark:text-red-400 rounded-lg hover:bg-red-50 dark:hover:bg-red-950 transition-colors"
                        >
                          🗑
                        </button>
                      </div>
                    </div>

                    {loeschenFuer === name && (
                      <div className="mx-4 mb-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg p-4 space-y-3">
                        <p className="text-sm font-medium text-red-800 dark:text-red-200">
                          Achtung: Das löscht die komplette Firma „{name}" unwiderruflich – Datenbank, alle
                          Rechnungen und Buchungen, hochgeladene Belege und Backups dieses Profils.
                        </p>
                        <p className="text-xs text-red-700 dark:text-red-300">
                          Für echte Geschäftsvorfälle gilt die 10-jährige GoBD-Aufbewahrungspflicht – lösche
                          nur Test- oder versehentlich angelegte Profile endgültig. Diese Aktion kann nicht
                          rückgängig gemacht werden.
                        </p>
                        <div>
                          <label className="block text-xs font-medium text-red-800 dark:text-red-200 mb-1">
                            Gib zur Bestätigung „{name}" ein:
                          </label>
                          <input
                            type="text"
                            value={loeschenEingabe}
                            onChange={(e) => setLoeschenEingabe(e.target.value)}
                            autoFocus
                            className="w-full rounded-lg border border-red-300 dark:border-red-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500 dark:bg-slate-800 dark:text-slate-100"
                          />
                        </div>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => loeschenMut.mutate({ name, eingabe: loeschenEingabe })}
                            disabled={loeschenMut.isPending || loeschenEingabe !== name}
                            className="px-4 py-2 text-sm font-medium bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-lg transition-colors"
                          >
                            Endgültig löschen
                          </button>
                          <button
                            type="button"
                            onClick={() => setLoeschenFuer(null)}
                            className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                          >
                            Abbrechen
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
