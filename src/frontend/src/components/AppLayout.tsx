import { useState, useEffect, useRef } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getTagesabschlussFehltGestern, getUnternehmen, pruefZM, pruefenWiederkehrend, getFaelligeBuchungsvorlagen, type EntwurfErgebnis } from '../api/client'
import { TagesabschlussDialog } from '../pages/journal/TagesabschlussDialog'
import { useUpdateCheck } from '../hooks/useUpdateCheck'

// ---------------------------------------------------------------------------
// Navigationsstruktur
// ---------------------------------------------------------------------------

const fakturierungAlleItems = [
  { to: '/angebote',        label: 'Angebote',               icon: '📝', bald: false, zeigen: (u: Unternehmen | undefined) => !!u?.angebote_aktiv },
  { to: '/auftraege',       label: 'Aufträge',               icon: '📋', bald: false, zeigen: (u: Unternehmen | undefined) => !!u?.auftraege_aktiv },
  { to: '/proformas',       label: 'Proforma',               icon: '📋', bald: false, zeigen: (u: Unternehmen | undefined) => !!u?.proforma_aktiv },
  { to: '/lieferscheine',   label: 'Lieferscheine',          icon: '🚚', bald: false, zeigen: (u: Unternehmen | undefined) => !!u?.lieferschein_aktiv },
  { to: '/rechnungen',      label: 'Rechnungen',             icon: '🧾', bald: false, zeigen: (_u: Unternehmen | undefined) => true },
  { to: '/wiederkehrend',   label: 'Wiederkehrend',          icon: '🔁', bald: false, zeigen: (u: Unternehmen | undefined) => !!u?.wiederkehrend_aktiv },
]

const buchhaltungNavBase = [
  { to: '/journal',          label: 'Journal',          icon: '📒' },
  { to: '/tagesabschluesse', label: 'Tagesabschlüsse',  icon: '📋' },
]

import type { Unternehmen, ZMPruefung } from '../api/client'

type NavKontext = { unt: Unternehmen | undefined; zm: ZMPruefung | undefined }
type ZeigenFn = (k: NavKontext) => boolean

const auswertungNavAlle: { to: string; label: string; icon: string; zeigen: ZeigenFn }[] = [
  { to: '/euer',             label: 'EÜR',               icon: '📊', zeigen: () => true },
  { to: '/anlageverzeichnis', label: 'AVEÜR',              icon: '🏛️', zeigen: () => true },
  { to: '/ustva',      label: 'UStVA',         icon: '🏛️', zeigen: ({ unt }) => !unt?.ist_kleinunternehmer },
  { to: '/jahres-ust', label: 'Jahres-USt',   icon: '📅', zeigen: () => true },
  { to: '/zm',         label: 'ZM',            icon: '🌍', zeigen: ({ zm }) => !!zm?.hat_ig_eintraege },
  { to: '/eks',     label: 'EKS',         icon: '📋', zeigen: ({ unt }) => !!unt?.bezieht_transferleistungen },
  { to: '/exporte', label: 'Exporte', icon: '📦', zeigen: () => true },
]

const stammdatenNav = [
  { to: '/kunden',      label: 'Kunden',      icon: '👤' },
  { to: '/lieferanten', label: 'Lieferanten', icon: '🏭' },
  { to: '/artikel',     label: 'Artikel', icon: '📦' },
]

const einstellungenNav = [
  { to: '/dokumentenpakete', label: 'Dokumentenpakete', icon: '📎' },
  { to: '/konten',           label: 'Konten',            icon: '🏦' },
  { to: '/kategorien',       label: 'Kategorien',        icon: '🏷️' },
  { to: '/nummernkreise',    label: 'Nummernkreise',     icon: '🔢' },
  { to: '/ust-saetze',       label: 'Steuersätze',       icon: '%' },
  { to: '/vorlagen',         label: 'Rechnungsvorlagen', icon: '📄' },
  { to: '/unternehmen',      label: 'Unternehmen',       icon: '🏢' },
]

const buchhaltungPfade   = [...buchhaltungNavBase.map(n => n.to), '/buchungsvorlagen']
const auswertungAllePfade = auswertungNavAlle.map(n => n.to)
const stammdatenPfade    = stammdatenNav.map(n => n.to)
const einstellungenPfade = einstellungenNav.map(n => n.to)

function formatDatum(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

// ---------------------------------------------------------------------------
// Hilfskomponenten
// ---------------------------------------------------------------------------

function SectionLabel({ label }: { label: string }) {
  return (
    <p className="px-4 pt-3 pb-0.5 text-[10px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500 select-none">
      {label}
    </p>
  )
}

function CollapsibleSection({
  label,
  icon,
  aktiv,
  items,
  badge,
}: {
  label: string
  icon: string
  aktiv: boolean
  items: { to: string; label: string; icon: string; badge?: boolean }[]
  badge?: boolean
}) {
  const [offen, setOffen] = useState(aktiv)
  const prevLen = useRef(items.length)
  useEffect(() => {
    if (aktiv) setOffen(true)
  }, [aktiv])
  useEffect(() => {
    if (items.length > prevLen.current) setOffen(true)
    prevLen.current = items.length
  }, [items.length])

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-4 py-2 text-sm font-medium transition-colors ${
      isActive
        ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-600 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-700'
        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100'
    }`

  return (
    <div className="mt-1">
      <button
        onClick={() => setOffen(o => !o)}
        className={`w-full flex items-center justify-between px-4 py-2 text-sm font-medium transition-colors ${
          aktiv
            ? 'text-blue-700 dark:text-blue-300'
            : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100'
        }`}
      >
        <span className="flex items-center gap-3">
          <span>{icon}</span>
          <span>{label}</span>
          {badge && <span className="w-2 h-2 rounded-full bg-orange-500 inline-block" />}
        </span>
        <span className="text-xs text-slate-400 dark:text-slate-500">{offen ? '▲' : '▼'}</span>
      </button>

      {offen && (
        <div className="border-l-2 border-slate-100 dark:border-slate-800 ml-6">
          {items.map(({ to, label: l, icon: ic, badge: itemBadge }) => (
            <NavLink key={to} to={to} className={navLinkClass}>
              <span>{ic}</span><span className="flex-1">{l}</span>
              {itemBadge && <span className="w-2 h-2 rounded-full bg-orange-500 shrink-0" />}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// AppLayout
// ---------------------------------------------------------------------------

export function AppLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [bannerDismissed, setBannerDismissed] = useState(false)

  // Ctrl+Shift+E (Strg+Shift+E) → Eingangsrechnungen
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && !e.metaKey && !e.altKey && e.key.toLowerCase() === 'e') {
        e.preventDefault()
        navigate('/rechnungen?typ=eingang')
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [navigate])
  const [abschlussDialog, setAbschlussDialog] = useState<string | null>(null)
  const [updateDismissed, setUpdateDismissed] = useState(false)
  const [wiederErgebnisse, setWiederErgebnisse] = useState<EntwurfErgebnis[]>([])

  // Beim Start: fällige Vorlagen prüfen, Entwürfe anlegen
  useEffect(() => {
    pruefenWiederkehrend().then(ergebnisse => {
      if (ergebnisse.length > 0) setWiederErgebnisse(ergebnisse)
    }).catch(() => {/* ignorieren, Startup soll nie blockieren */})
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const { updateAvailable, version: updateVersion, downloading, progress, error: updateError, readyToRestart, installUpdate } = useUpdateCheck()

  const { data: fehltGestern } = useQuery({
    queryKey: ['tagesabschluss-fehlt-gestern'],
    queryFn: getTagesabschlussFehltGestern,
    staleTime: 1000 * 60 * 5,
    refetchOnWindowFocus: false,
  })

  const { data: unt } = useQuery({
    queryKey: ['unternehmen'],
    queryFn: getUnternehmen,
    staleTime: 1000 * 60 * 5,
  })

  const { data: zmPruefung } = useQuery({
    queryKey: ['zm-pruefen'],
    queryFn: pruefZM,
    staleTime: 1000 * 60 * 10,
    enabled: !unt?.ist_kleinunternehmer,
  })

  const untDef = unt ?? undefined
  const navKontext: NavKontext = { unt: untDef, zm: zmPruefung }
  const auswertungNav = auswertungNavAlle.filter(n => n.zeigen(navKontext))
  const fakturierungNav = fakturierungAlleItems.filter(n => n.zeigen(untDef))
  const buchhaltungNav = [
    ...buchhaltungNavBase,
    ...(untDef?.buchungsvorlagen_aktiv ? [{ to: '/buchungsvorlagen', label: 'Buchungsvorlagen', icon: '🔄' }] : []),
  ]

  const { data: faelligeBuchungen = [] } = useQuery({
    queryKey: ['buchungsvorlagen-faellig'],
    queryFn: getFaelligeBuchungsvorlagen,
    enabled: !!untDef?.buchungsvorlagen_aktiv,
    refetchInterval: 5 * 60 * 1000,
  })
  const faelligBadge = faelligeBuchungen.length > 0

  const zeigeBanner = fehltGestern?.fehlt === true && !bannerDismissed

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-4 py-2 text-sm font-medium transition-colors ${
      isActive
        ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-600 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-700'
        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100'
    }`

  const buchhaltungAktiv  = buchhaltungPfade.some(p => location.pathname.startsWith(p))
  const auswertungAktiv   = auswertungAllePfade.some(p => location.pathname.startsWith(p))
  const stammdatenAktiv   = stammdatenPfade.some(p => location.pathname.startsWith(p))
  const einstellungenAktiv = einstellungenPfade.some(p => location.pathname.startsWith(p))

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-slate-900 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-700 flex flex-col shrink-0">
        <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex items-center gap-2">
          <img src="/logo.svg" alt="RechnungsFee" className="w-8 h-8 flex-shrink-0" />
          <div>
            <h1 className="font-bold text-slate-800 dark:text-slate-100 text-lg leading-tight">RechnungsFee</h1>
            <p className="text-xs text-slate-400 dark:text-slate-500 leading-tight">v{__APP_VERSION__}</p>
          </div>
        </div>

        <nav className="flex-1 py-2 overflow-y-auto">

          {/* Dashboard */}
          <NavLink to="/" end className={navLinkClass}>
            <span>📊</span><span>Dashboard</span>
          </NavLink>

          {/* Fakturierung – immer sichtbar */}
          <SectionLabel label="Fakturierung" />
          {fakturierungNav.map(({ to, label, icon, bald }) =>
            bald ? (
              <div key={to} className="flex items-center gap-3 px-4 py-2 text-sm text-slate-300 dark:text-slate-600 cursor-not-allowed select-none">
                <span className="opacity-40">{icon}</span>
                <span>{label}</span>
                <span className="ml-auto text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500 rounded px-1.5 py-0.5">bald</span>
              </div>
            ) : (
              <NavLink key={to} to={to} className={navLinkClass}>
                <span>{icon}</span><span>{label}</span>
              </NavLink>
            )
          )}

          {/* Buchhaltung */}
          <CollapsibleSection
            label="Buchhaltung"
            icon="📒"
            aktiv={buchhaltungAktiv}
            badge={faelligBadge}
            items={buchhaltungNav.map(n => ({
              ...n,
              badge: n.to === '/buchungsvorlagen' && faelligBadge,
            }))}
          />

          {/* Auswertung */}
          <CollapsibleSection
            label="Auswertung"
            icon="📈"
            aktiv={auswertungAktiv}
            items={auswertungNav}
          />

          {/* Stammdaten */}
          <CollapsibleSection
            label="Stammdaten"
            icon="👥"
            aktiv={stammdatenAktiv}
            items={stammdatenNav}
          />

          {/* Einstellungen */}
          <CollapsibleSection
            label="Einstellungen"
            icon="⚙️"
            aktiv={einstellungenAktiv}
            items={einstellungenNav}
          />

          {/* Trennlinie */}
          <div className="border-t border-slate-100 dark:border-slate-800 mt-3 mb-1" />

          <NavLink to="/backup" className={navLinkClass}>
            <span>💾</span><span>Backup</span>
          </NavLink>
          <NavLink to="/info" className={navLinkClass}>
            <span>ℹ️</span><span>Info & Updates</span>
          </NavLink>

        </nav>
      </aside>

      {/* Hauptinhalt */}
      <main className="flex-1 overflow-auto flex flex-col">
        {/* Update-Banner */}
        {updateAvailable && !updateDismissed && (
          <div className={`border-b px-4 py-2.5 flex items-center gap-3 shrink-0 ${
            readyToRestart ? 'bg-blue-50 border-blue-200 dark:bg-blue-950 dark:border-blue-800'
            : updateError ? 'bg-red-50 border-red-200 dark:bg-red-950 dark:border-red-800'
            : 'bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800'
          }`}>
            <span className={`text-base leading-none ${
              readyToRestart ? 'text-blue-500 dark:text-blue-400'
              : updateError ? 'text-red-500 dark:text-red-400'
              : 'text-green-600 dark:text-green-400'
            }`}>
              {readyToRestart ? '↻' : updateError ? '!' : '↑'}
            </span>
            <p className={`text-sm flex-1 ${
              readyToRestart ? 'text-blue-800 dark:text-blue-200'
              : updateError ? 'text-red-800 dark:text-red-200'
              : 'text-green-800 dark:text-green-200'
            }`}>
              {readyToRestart ? (
                <><span className="font-semibold">Update installiert!</span> Die App startet gleich automatisch neu.</>
              ) : updateError ? (
                <><span className="font-semibold">Update fehlgeschlagen:</span> {updateError}</>
              ) : (
                <>Update verfügbar: <span className="font-semibold">Version {updateVersion}</span></>
              )}
            </p>
            {!readyToRestart && (
              downloading ? (
                <div className="w-32 h-1.5 bg-green-200 dark:bg-green-800 rounded-full overflow-hidden shrink-0">
                  <div
                    className="h-full bg-green-500 rounded-full transition-all duration-300"
                    style={{ width: progress !== null ? `${progress}%` : '60%' }}
                  />
                </div>
              ) : (
                <button
                  onClick={installUpdate}
                  className={`text-sm font-medium rounded-md px-3 py-1 transition-colors shrink-0 border ${
                    updateError
                      ? 'text-red-700 bg-red-100 hover:bg-red-200 border-red-300 dark:text-red-300 dark:bg-red-900 dark:hover:bg-red-800 dark:border-red-700'
                      : 'text-green-700 bg-green-100 hover:bg-green-200 border-green-300 dark:text-green-300 dark:bg-green-900 dark:hover:bg-green-800 dark:border-green-700'
                  }`}
                >
                  {updateError ? 'Erneut versuchen' : 'Jetzt installieren'}
                </button>
              )
            )}
            {!readyToRestart && (
              <button
                onClick={() => setUpdateDismissed(true)}
                className={`text-lg leading-none px-1 shrink-0 ${updateError ? 'text-red-400 hover:text-red-600 dark:text-red-500 dark:hover:text-red-300' : 'text-green-500 hover:text-green-700 dark:text-green-400 dark:hover:text-green-200'}`}
                title="Schließen"
              >
                ×
              </button>
            )}
          </div>
        )}

        {/* Wiederkehrende Rechnungen – Entwürfe erstellt */}
        {wiederErgebnisse.length > 0 && (
          <div className="bg-blue-50 dark:bg-blue-950 border-b border-blue-200 dark:border-blue-800 px-4 py-2.5 flex items-center gap-3 shrink-0">
            <span className="text-blue-600 dark:text-blue-400 text-base leading-none">🔁</span>
            <p className="text-sm text-blue-800 dark:text-blue-300 flex-1">
              {wiederErgebnisse.length === 1
                ? <>Entwurf <span className="font-semibold">{wiederErgebnisse[0].rechnungsnummer}</span> aus Vorlage „{wiederErgebnisse[0].vorlage_bezeichnung}" erstellt.</>
                : <>{wiederErgebnisse.length} Rechnungs-Entwürfe aus wiederkehrenden Vorlagen erstellt.</>
              }
              {wiederErgebnisse.some(e => e.preisaenderungen.length > 0) && (
                <span className="ml-2 text-amber-700 dark:text-amber-400 font-medium">⚠ Preisänderungen erkannt – Vorlagen prüfen.</span>
              )}
            </p>
            <button
              onClick={() => navigate('/wiederkehrend')}
              className="text-sm font-medium text-blue-700 bg-blue-100 hover:bg-blue-200 border border-blue-300 rounded-md px-3 py-1 transition-colors shrink-0 dark:text-blue-300 dark:bg-blue-900 dark:hover:bg-blue-800 dark:border-blue-700"
            >
              Vorlagen
            </button>
            <button
              onClick={() => setWiederErgebnisse([])}
              className="text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-200 text-lg leading-none px-1 shrink-0"
              title="Schließen"
            >
              ×
            </button>
          </div>
        )}

        {/* Erinnerungs-Banner */}
        {zeigeBanner && fehltGestern && (
          <div className="bg-amber-50 dark:bg-amber-950 border-b border-amber-200 dark:border-amber-800 px-4 py-2.5 flex items-center gap-3 shrink-0">
            <span className="text-amber-600 dark:text-amber-400 text-base leading-none">⚠</span>
            <p className="text-sm text-amber-800 dark:text-amber-300 flex-1">
              Kein Tagesabschluss für{' '}
              <span className="font-semibold">{formatDatum(fehltGestern.datum)}</span> vorhanden.
            </p>
            <button
              onClick={() => setAbschlussDialog(fehltGestern.datum)}
              className="text-sm font-medium text-amber-700 bg-amber-100 hover:bg-amber-200 border border-amber-300 rounded-md px-3 py-1 transition-colors shrink-0 dark:text-amber-300 dark:bg-amber-900 dark:hover:bg-amber-800 dark:border-amber-700"
            >
              Jetzt durchführen
            </button>
            <button
              onClick={() => setBannerDismissed(true)}
              className="text-amber-500 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-200 text-lg leading-none px-1 shrink-0"
              title="Schließen"
            >
              ×
            </button>
          </div>
        )}

        <div className="flex-1 min-h-0 overflow-y-auto">
          <Outlet />
        </div>
      </main>

      {/* Tagesabschluss-Dialog */}
      {abschlussDialog && (
        <TagesabschlussDialog
          datum={abschlussDialog}
          onClose={() => setAbschlussDialog(null)}
          onSuccess={() => {
            setAbschlussDialog(null)
            setBannerDismissed(true)
            qc.invalidateQueries({ queryKey: ['tagesabschluss-fehlt-gestern'] })
          }}
        />
      )}
    </div>
  )
}
