import { useEffect, useState } from 'react'
import { getEksEinstellungen, saveEksEinstellungen, type EksEinstellungen } from '../../api/client'

const LEER: EksEinstellungen = {
  taetigkeitsart_text: '',
  taetigkeitsbeginn: '',
  taetigkeitsende: '',
  wohnung_gewerblich: false,
  gewerbliche_raeume: '',
  gewerbliche_flaeche: '',
  produkte_kostenfrei: false,
  personal_beschaeftigt: false,
  anzahl_beschaeftigte: '',
  weiteres_personal: false,
  anzahl_weiteres_personal: '',
  personal_ab: '',
  umsatzsteuerpflichtig: false,
  zuschuss_erhalten: false,
  zuschuss_beantragt: false,
  darlehen: false,
  darlehen_hoehe: '',
  darlehen_eingang: '',
  darlehen_rueckzahlung_ab: '',
  darlehen_tilgung: '',
  darlehen_ausgaben_art: '',
  darlehen_ausgaben_hoehe: '',
  kind_ausserhalb: false,
  unterhalt: false,
  fahrten_betriebsstaette: false,
  km_einfach: '',
  arbeitstage_pro_woche: '',
  mehraufwand_verpflegung: false,
  arbeitstage_verpflegung: '',
}

// ── Hilfselemente ────────────────────────────────────────────────────────────

function Abschnitt({ titel, children }: { titel: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <h3 className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 pb-1">
        {titel}
      </h3>
      {children}
    </div>
  )
}

function Ja({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-start gap-2 cursor-pointer text-sm text-slate-700 dark:text-slate-300">
      <input
        type="checkbox"
        checked={checked}
        onChange={e => onChange(e.target.checked)}
        className="mt-0.5 h-4 w-4 rounded border-slate-300 dark:border-slate-600 accent-blue-600"
      />
      {label}
    </label>
  )
}

function Inp({
  label, value, onChange, placeholder, half,
}: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; half?: boolean
}) {
  return (
    <div className={half ? 'w-1/2' : 'w-full'}>
      <label className="block text-xs text-slate-500 dark:text-slate-400 mb-0.5">{label}</label>
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
  )
}

// ── Hauptkomponente ──────────────────────────────────────────────────────────

export function EksEinstellungenModal({ onClose }: { onClose: () => void }) {
  const [form, setForm] = useState<EksEinstellungen>(LEER)
  const [laedt, setLaedt] = useState(true)
  const [speichert, setSpeichert] = useState(false)
  const [gespeichert, setGespeichert] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)

  useEffect(() => {
    getEksEinstellungen()
      .then(d => setForm({ ...LEER, ...d }))
      .catch(() => {})
      .finally(() => setLaedt(false))
  }, [])

  function set<K extends keyof EksEinstellungen>(k: K, v: EksEinstellungen[K]) {
    setForm(f => ({ ...f, [k]: v }))
    setGespeichert(false)
  }

  async function handleSpeichern() {
    setSpeichert(true)
    setFehler(null)
    try {
      await saveEksEinstellungen(form)
      setGespeichert(true)
    } catch (e: any) {
      setFehler(e?.message ?? 'Speichern fehlgeschlagen')
    } finally {
      setSpeichert(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 overflow-y-auto py-8 px-4">
      <div className="relative w-full max-w-2xl bg-white dark:bg-slate-800 rounded-2xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">EKS-Einstellungen</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Felder für Abschnitt D, F und Seite 9 des Formulars
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xl leading-none p-1"
          >
            ✕
          </button>
        </div>

        {laedt ? (
          <div className="p-8 text-center text-slate-400">Lade Einstellungen…</div>
        ) : (
          <div className="px-6 py-5 space-y-6 max-h-[70vh] overflow-y-auto">

            {/* ── Abschnitt D ─────────────────────────────────────────── */}
            <Abschnitt titel="D – Tätigkeit">
              <Inp
                label="15 Gewerbe oder Tätigkeit"
                value={form.taetigkeitsart_text ?? ''}
                onChange={v => set('taetigkeitsart_text', v)}
                placeholder="z.B. Softwareentwicklung, Grafikdesign …"
              />
              <div className="flex gap-3">
                <Inp
                  label="16 Beginn der Tätigkeit (MM.JJJJ)"
                  value={form.taetigkeitsbeginn ?? ''}
                  onChange={v => set('taetigkeitsbeginn', v)}
                  placeholder="01.2020"
                  half
                />
                <Inp
                  label="17 Ende der Tätigkeit (MM.JJJJ, falls zutreffend)"
                  value={form.taetigkeitsende ?? ''}
                  onChange={v => set('taetigkeitsende', v)}
                  placeholder="leer lassen wenn noch aktiv"
                  half
                />
              </div>
            </Abschnitt>

            {/* ── Abschnitt F ─────────────────────────────────────────── */}
            <Abschnitt titel="F – Weitere Angaben">

              <div className="space-y-1">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  23 Wohnung gewerblich genutzt?
                </p>
                <Ja label="Ja" checked={form.wohnung_gewerblich} onChange={v => set('wohnung_gewerblich', v)} />
                {form.wohnung_gewerblich && (
                  <div className="flex gap-3 mt-2 ml-6">
                    <Inp label="24 Anzahl Räume" value={form.gewerbliche_raeume ?? ''} onChange={v => set('gewerbliche_raeume', v)} half />
                    <Inp label="25 Fläche (m²)" value={form.gewerbliche_flaeche ?? ''} onChange={v => set('gewerbliche_flaeche', v)} half />
                  </div>
                )}
              </div>

              <div className="space-y-1">
                <p className="text-xs text-slate-500 dark:text-slate-400">26 Produkte kostenfrei überlassen?</p>
                <Ja label="Ja (Auflistung + Nachweise beifügen)" checked={form.produkte_kostenfrei} onChange={v => set('produkte_kostenfrei', v)} />
              </div>

              <div className="space-y-1">
                <p className="text-xs text-slate-500 dark:text-slate-400">27 Personal beschäftigt?</p>
                <Ja label="Ja" checked={form.personal_beschaeftigt} onChange={v => set('personal_beschaeftigt', v)} />
                {form.personal_beschaeftigt && (
                  <div className="ml-6">
                    <Inp label="28 Anzahl Beschäftigte" value={form.anzahl_beschaeftigte ?? ''} onChange={v => set('anzahl_beschaeftigte', v)} half />
                  </div>
                )}
              </div>

              <div className="space-y-1">
                <p className="text-xs text-slate-500 dark:text-slate-400">29 Weiteres Personal geplant?</p>
                <Ja label="Ja" checked={form.weiteres_personal} onChange={v => set('weiteres_personal', v)} />
                {form.weiteres_personal && (
                  <div className="flex gap-3 mt-2 ml-6">
                    <Inp label="30 Anzahl" value={form.anzahl_weiteres_personal ?? ''} onChange={v => set('anzahl_weiteres_personal', v)} half />
                    <Inp label="31 Einstellung ab (TT.MM.JJJJ)" value={form.personal_ab ?? ''} onChange={v => set('personal_ab', v)} half />
                  </div>
                )}
              </div>

              <div className="space-y-1">
                <p className="text-xs text-slate-500 dark:text-slate-400">32 Umsatzsteuerpflichtig?</p>
                <Ja label="Ja" checked={form.umsatzsteuerpflichtig} onChange={v => set('umsatzsteuerpflichtig', v)} />
              </div>

              <div className="space-y-1">
                <p className="text-xs text-slate-500 dark:text-slate-400">33/34 Zuschüsse / Beihilfen?</p>
                <Ja label="33 Zuschüsse erhalten (Nachweise beifügen)" checked={form.zuschuss_erhalten} onChange={v => set('zuschuss_erhalten', v)} />
                <Ja label="34 Zuschüsse beantragt oder geplant" checked={form.zuschuss_beantragt} onChange={v => set('zuschuss_beantragt', v)} />
              </div>

              <div className="space-y-1">
                <p className="text-xs text-slate-500 dark:text-slate-400">35 Betriebliches Darlehen aufgenommen?</p>
                <Ja label="Ja (Nachweise beifügen)" checked={form.darlehen} onChange={v => set('darlehen', v)} />
                {form.darlehen && (
                  <div className="space-y-3 mt-2 ml-6">
                    <div className="flex gap-3">
                      <Inp label="36 Höhe (€)" value={form.darlehen_hoehe ?? ''} onChange={v => set('darlehen_hoehe', v)} half />
                      <Inp label="37 Eingang auf Konto (TT.MM.JJJJ)" value={form.darlehen_eingang ?? ''} onChange={v => set('darlehen_eingang', v)} half />
                    </div>
                    <div className="flex gap-3">
                      <Inp label="38 Rückzahlung ab (TT.MM.JJJJ)" value={form.darlehen_rueckzahlung_ab ?? ''} onChange={v => set('darlehen_rueckzahlung_ab', v)} half />
                      <Inp label="39 Monatliche Tilgung (€)" value={form.darlehen_tilgung ?? ''} onChange={v => set('darlehen_tilgung', v)} half />
                    </div>
                    <div className="flex gap-3">
                      <Inp label="40 Finanzierte Ausgaben (Art)" value={form.darlehen_ausgaben_art ?? ''} onChange={v => set('darlehen_ausgaben_art', v)} half />
                      <Inp label="41 Finanzierte Ausgaben (€)" value={form.darlehen_ausgaben_hoehe ?? ''} onChange={v => set('darlehen_ausgaben_hoehe', v)} half />
                    </div>
                  </div>
                )}
              </div>
            </Abschnitt>

            {/* ── Seite 9 ──────────────────────────────────────────────── */}
            <Abschnitt titel="Seite 9 – Personenbezogene Ausgaben">

              <div className="space-y-1">
                <p className="text-xs text-slate-500 dark:text-slate-400">52 Kind unter 18 nicht im Haushalt?</p>
                <Ja label="Ja (Nachweis beifügen)" checked={form.kind_ausserhalb} onChange={v => set('kind_ausserhalb', v)} />
              </div>

              <div className="space-y-1">
                <p className="text-xs text-slate-500 dark:text-slate-400">53 Unterhalt gezahlt?</p>
                <Ja label="Ja (Nachweise beifügen)" checked={form.unterhalt} onChange={v => set('unterhalt', v)} />
              </div>

              <div className="space-y-1">
                <p className="text-xs text-slate-500 dark:text-slate-400">54 Fahrten zur Betriebsstätte mit privatem PKW?</p>
                <Ja label="Ja" checked={form.fahrten_betriebsstaette} onChange={v => set('fahrten_betriebsstaette', v)} />
                {form.fahrten_betriebsstaette && (
                  <div className="flex gap-3 mt-2 ml-6">
                    <Inp label="55 Einfache Strecke (km)" value={form.km_einfach ?? ''} onChange={v => set('km_einfach', v)} half />
                    <Inp label="56 Arbeitstage/Woche" value={form.arbeitstage_pro_woche ?? ''} onChange={v => set('arbeitstage_pro_woche', v)} half />
                  </div>
                )}
              </div>

              <div className="space-y-1">
                <p className="text-xs text-slate-500 dark:text-slate-400">57 Mehraufwand für Verpflegung (≥12 h abwesend)?</p>
                <Ja label="Ja" checked={form.mehraufwand_verpflegung} onChange={v => set('mehraufwand_verpflegung', v)} />
                {form.mehraufwand_verpflegung && (
                  <div className="ml-6 mt-2">
                    <Inp label="58 Arbeitstage/Monat mit Mehraufwand" value={form.arbeitstage_verpflegung ?? ''} onChange={v => set('arbeitstage_verpflegung', v)} half />
                  </div>
                )}
              </div>
            </Abschnitt>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 dark:border-slate-700 gap-3">
          {fehler && (
            <p className="text-sm text-red-600 dark:text-red-400">{fehler}</p>
          )}
          {gespeichert && !fehler && (
            <p className="text-sm text-emerald-600 dark:text-emerald-400">Gespeichert</p>
          )}
          {!fehler && !gespeichert && <span />}
          <div className="flex gap-3 ml-auto">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              Schließen
            </button>
            <button
              onClick={handleSpeichern}
              disabled={speichert || laedt}
              className="px-5 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg transition-colors"
            >
              {speichert ? 'Speichert…' : 'Speichern'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
