import { useState } from 'react'
import { CHANGELOG, type ChangelogVersion, type EintragTyp } from '../../data/changelog'
import { useUpdateCheck } from '../../hooks/useUpdateCheck'

const TYP_CFG: Record<EintragTyp, { label: string; cls: string }> = {
  neu:          { label: 'Neu',          cls: 'bg-green-100 text-green-700' },
  verbesserung: { label: 'Verbessert',   cls: 'bg-blue-100 text-blue-700' },
  fix:          { label: 'Fix',          cls: 'bg-amber-100 text-amber-700' },
}

function VersionsBlock({ v, defaultOffen }: { v: ChangelogVersion; defaultOffen: boolean }) {
  const [offen, setOffen] = useState(defaultOffen)

  return (
    <div className="border border-slate-200 rounded-xl overflow-hidden">
      <button
        type="button"
        onClick={() => setOffen(o => !o)}
        className="w-full flex items-center justify-between px-5 py-4 bg-slate-50 hover:bg-slate-100 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <span className="font-bold text-slate-800">{v.version}</span>
          <span className="text-sm text-slate-500">{v.datum}</span>
          {defaultOffen && (
            <span className="text-xs font-medium bg-blue-600 text-white px-2 py-0.5 rounded-full">
              Aktuell
            </span>
          )}
        </div>
        <span className="text-slate-400 text-sm">{offen ? '▲' : '▼'}</span>
      </button>

      {offen && (
        <ul className="px-5 py-4 space-y-2.5 bg-white">
          {v.eintraege.map((e, i) => {
            const cfg = TYP_CFG[e.typ]
            return (
              <li key={i} className="flex items-start gap-3">
                <span className={`text-[11px] font-semibold px-1.5 py-0.5 rounded shrink-0 mt-0.5 ${cfg.cls}`}>
                  {cfg.label}
                </span>
                <span className="text-sm text-slate-700">{e.text}</span>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

export function InfoPage() {
  const { updateAvailable, version, downloading, progress, installUpdate } = useUpdateCheck()

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center gap-4">
        <img src="/logo.svg" alt="RechnungsFee" className="w-12 h-12 shrink-0" />
        <div>
          <h1 className="text-2xl font-bold text-slate-900">RechnungsFee</h1>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-sm text-slate-500">Version {__APP_VERSION__}</span>
            <span className="text-xs font-medium bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">Beta</span>
          </div>
        </div>
      </div>

      {/* Update-Banner (nur Tauri-Prod, wenn Update verfügbar) */}
      {updateAvailable && (
        <div className="bg-green-50 border border-green-200 rounded-xl px-5 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="text-green-600 text-lg shrink-0">↑</span>
            <div>
              <p className="text-sm font-semibold text-green-800">
                Update verfügbar: Version {version}
              </p>
              {downloading && (
                <div className="mt-1.5 w-48">
                  <div className="h-1.5 bg-green-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-green-500 rounded-full transition-all duration-300"
                      style={{ width: progress !== null ? `${progress}%` : '100%' }}
                    />
                  </div>
                  <p className="text-xs text-green-700 mt-1">
                    {progress !== null ? `${progress} %` : 'Wird heruntergeladen…'}
                  </p>
                </div>
              )}
            </div>
          </div>
          {!downloading && (
            <button
              type="button"
              onClick={installUpdate}
              className="shrink-0 text-sm font-medium bg-green-600 hover:bg-green-700 text-white px-4 py-1.5 rounded-lg transition-colors"
            >
              Jetzt installieren
            </button>
          )}
        </div>
      )}

      {/* Beta-Disclaimer */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl px-5 py-4 flex gap-3">
        <span className="text-amber-500 text-lg shrink-0">⚠</span>
        <div className="space-y-1">
          <p className="text-sm font-semibold text-amber-800">Beta-Version – bitte beachten</p>
          <p className="text-sm text-amber-700">
            RechnungsFee befindet sich in der Beta-Phase. Die Software kann Fehler enthalten und
            sollte nicht als einzige Steuerunterlage verwendet werden. Erstelle regelmäßig{' '}
            <a href="/backup" className="font-medium underline hover:no-underline">Backups</a> deiner Daten.
          </p>
        </div>
      </div>

      {/* Was ist neu */}
      <div className="space-y-3">
        <h2 className="text-lg font-bold text-slate-800">Was ist neu</h2>
        {CHANGELOG.map((v, i) => (
          <VersionsBlock key={v.version} v={v} defaultOffen={i === 0} />
        ))}
      </div>

      {/* Über RechnungsFee */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-2">
        <h2 className="font-bold text-slate-800">Über RechnungsFee</h2>
        <p className="text-sm text-slate-600">
          RechnungsFee ist eine <strong>Open-Source-Buchhaltungssoftware</strong> für
          Freiberufler, Selbstständige und Kleinunternehmer (§19 UStG). Sie unterstützt
          GoBD-konforme Kassenbuchführung, Rechnungsstellung und den gesetzlich
          vorgeschriebenen Datenexport für Betriebsprüfungen.
        </p>
        <p className="text-sm text-slate-500">
          Lizenz: <strong>AGPL-3.0</strong> · Alle Daten bleiben lokal auf deinem Gerät.
        </p>
      </div>

      {/* Links */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
        <h2 className="font-bold text-slate-800">Links</h2>
        <div className="space-y-2">
          <a
            href="https://github.com/nicolettas-muggelbude/RechnungsFee/issues/new"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-3 text-sm text-slate-700 hover:text-blue-600 transition-colors group"
          >
            <span className="w-7 h-7 bg-slate-100 group-hover:bg-blue-50 rounded-lg flex items-center justify-center shrink-0 transition-colors">🐛</span>
            <span>Fehler melden oder Feedback geben (GitHub Issues)</span>
          </a>
          <a
            href="https://github.com/nicolettas-muggelbude/RechnungsFee/blob/main/docs/ROADMAP.md"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-3 text-sm text-slate-700 hover:text-blue-600 transition-colors group"
          >
            <span className="w-7 h-7 bg-slate-100 group-hover:bg-blue-50 rounded-lg flex items-center justify-center shrink-0 transition-colors">🗺️</span>
            <span>Roadmap – geplante Funktionen</span>
          </a>
          <a
            href="https://github.com/nicolettas-muggelbude/RechnungsFee/blob/main/LICENSE"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-3 text-sm text-slate-700 hover:text-blue-600 transition-colors group"
          >
            <span className="w-7 h-7 bg-slate-100 group-hover:bg-blue-50 rounded-lg flex items-center justify-center shrink-0 transition-colors">📄</span>
            <span>Lizenz: GNU AGPL-3.0</span>
          </a>
          <a
            href="https://github.com/nicolettas-muggelbude/RechnungsFee"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-3 text-sm text-slate-700 hover:text-blue-600 transition-colors group"
          >
            <span className="w-7 h-7 bg-slate-100 group-hover:bg-blue-50 rounded-lg flex items-center justify-center shrink-0 transition-colors">⭐</span>
            <span>Quellcode auf GitHub</span>
          </a>
        </div>
      </div>

    </div>
  )
}
