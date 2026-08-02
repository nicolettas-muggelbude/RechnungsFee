import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getMahnwesenEinstellungen, updateMahnwesenEinstellungen, getUnternehmen,
  createMahnstufe, updateMahnstufe, deleteMahnstufe,
  type Mahnstufe, type MahnwesenEinstellungenUpdate,
} from '../../api/client'
import { useMxAuto } from '../../hooks/useAnsicht'

const inputCls = 'w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100'
const labelCls = 'block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1'

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors shrink-0 ${checked ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-600'}`}
    >
      <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${checked ? 'translate-x-4' : 'translate-x-0.5'}`} />
    </button>
  )
}

function MahnstufeCard({ stufe, istErsteStufe, istErsteAktiveStufe, onSaved }: { stufe: Mahnstufe; istErsteStufe: boolean; istErsteAktiveStufe: boolean; onSaved: () => void }) {
  const [form, setForm] = useState(stufe)
  const [offen, setOffen] = useState(false)
  const [gespeichert, setGespeichert] = useState(false)
  const qc = useQueryClient()

  useEffect(() => setForm(stufe), [stufe])

  const saveMut = useMutation({
    mutationFn: (data: Partial<Mahnstufe>) => updateMahnstufe(stufe.id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['mahnwesen-einstellungen'] })
      onSaved()
      setGespeichert(true)
      setTimeout(() => setGespeichert(false), 2500)
    },
  })
  const saveFehler = saveMut.isError ? (saveMut.error as Error).message : null
  const deleteMut = useMutation({
    mutationFn: () => deleteMahnstufe(stufe.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mahnwesen-einstellungen'] }),
  })

  function speichern() {
    setGespeichert(false)
    saveMut.mutate({
      bezeichnung: form.bezeichnung,
      tage_nach_faelligkeit: form.tage_nach_faelligkeit,
      tage_nach_vorheriger: form.tage_nach_vorheriger,
      betreff_vorlage: form.betreff_vorlage,
      text_vorlage: form.text_vorlage,
      mahngebuehr_aktiv: istErsteStufe ? false : form.mahngebuehr_aktiv,
      mahngebuehr_privat: form.mahngebuehr_privat,
      mahngebuehr_gewerblich: form.mahngebuehr_gewerblich,
      anhang_rechnung: form.anhang_rechnung,
      anhang_bisherige_mahnungen: form.anhang_bisherige_mahnungen,
      anhang_kontokorrent: form.anhang_kontokorrent,
    })
  }

  return (
    <div className={`border rounded-xl overflow-hidden ${stufe.aktiv ? 'border-slate-200 dark:border-slate-700' : 'border-slate-100 dark:border-slate-800 opacity-60'}`}>
      <div className="flex items-center gap-3 px-4 py-3 bg-slate-50 dark:bg-slate-900">
        <span className="text-xs font-bold text-slate-400 dark:text-slate-500 w-6">#{stufe.stufe}</span>
        <span className="flex-1 font-medium text-sm text-slate-800 dark:text-slate-100">{stufe.bezeichnung}</span>
        <Toggle checked={stufe.aktiv} onChange={(v) => updateMahnstufe(stufe.id, { aktiv: v }).then(() => qc.invalidateQueries({ queryKey: ['mahnwesen-einstellungen'] }))} />
        <button type="button" onClick={() => setOffen((o) => !o)} className="text-xs text-blue-600 hover:underline">
          {offen ? 'Schließen' : 'Bearbeiten'}
        </button>
        {stufe.loeschbar && (
          <button
            type="button"
            onClick={() => { if (window.confirm(`Mahnstufe "${stufe.bezeichnung}" wirklich löschen?`)) deleteMut.mutate() }}
            className="text-slate-300 hover:text-red-500 text-lg leading-none"
            title="Löschen (noch nie verwendet)"
          >
            ×
          </button>
        )}
      </div>
      {offen && (
        <div className="p-4 space-y-3 bg-white dark:bg-slate-800">
          <div>
            <label className={labelCls}>Bezeichnung</label>
            <input className={inputCls} value={form.bezeichnung} onChange={(e) => setForm({ ...form, bezeichnung: e.target.value })} />
          </div>
          {istErsteAktiveStufe ? (
            <div>
              <label className={labelCls}>Tage nach Fälligkeit der Rechnung</label>
              <input type="number" min={0} className={inputCls} value={form.tage_nach_faelligkeit}
                onChange={(e) => setForm({ ...form, tage_nach_faelligkeit: parseInt(e.target.value) || 0 })} />
              <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-1">
                Diese Stufe ist aktuell die erste aktive Mahnstufe – sie greift ab der Fälligkeit der Rechnung, nicht nach einer vorherigen Mahnung.
              </p>
            </div>
          ) : (
            <div>
              <label className={labelCls}>Tage nach vorheriger Mahnung</label>
              <input type="number" min={0} className={inputCls} value={form.tage_nach_vorheriger}
                onChange={(e) => setForm({ ...form, tage_nach_vorheriger: parseInt(e.target.value) || 0 })} />
            </div>
          )}
          {istErsteStufe ? (
            <p className="text-[11px] text-slate-400 dark:text-slate-500">
              Auf der ersten Stufe (Zahlungserinnerung) wird keine Mahngebühr berechnet – eine
              formlose Erinnerung ist noch keine Mahnung.
            </p>
          ) : (
            <>
              <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 cursor-pointer">
                <input type="checkbox" checked={form.mahngebuehr_aktiv} onChange={(e) => setForm({ ...form, mahngebuehr_aktiv: e.target.checked })} className="rounded" />
                Mahngebühr auf dieser Stufe berechnen
              </label>
              {form.mahngebuehr_aktiv && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className={labelCls}>Mahngebühr privat (€)</label>
                    <input className={inputCls} value={form.mahngebuehr_privat} onChange={(e) => setForm({ ...form, mahngebuehr_privat: e.target.value })} />
                  </div>
                  <div>
                    <label className={labelCls}>Mahngebühr gewerblich (€)</label>
                    <input className={inputCls} value={form.mahngebuehr_gewerblich} onChange={(e) => setForm({ ...form, mahngebuehr_gewerblich: e.target.value })} />
                  </div>
                </div>
              )}
            </>
          )}
          <div>
            <label className={labelCls}>Zusätzliche Dokumentanhänge beim Mail-Versand</label>
            <div className="space-y-1.5 mt-1">
              <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 cursor-pointer">
                <input type="checkbox" checked={form.anhang_rechnung} onChange={(e) => setForm({ ...form, anhang_rechnung: e.target.checked })} className="rounded" />
                Rechnung(en) anhängen
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 cursor-pointer">
                <input type="checkbox" checked={form.anhang_bisherige_mahnungen} onChange={(e) => setForm({ ...form, anhang_bisherige_mahnungen: e.target.checked })} className="rounded" />
                Bisherige Mahnungen anhängen
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 cursor-pointer">
                <input type="checkbox" checked={form.anhang_kontokorrent} onChange={(e) => setForm({ ...form, anhang_kontokorrent: e.target.checked })} className="rounded" />
                Kontokorrent anhängen (ab erster gemahnter Rechnung)
              </label>
            </div>
          </div>
          <div>
            <label className={labelCls}>Betreff-Vorlage (optional)</label>
            <input className={inputCls} value={form.betreff_vorlage ?? ''} onChange={(e) => setForm({ ...form, betreff_vorlage: e.target.value })} placeholder="{bezeichnung} – {rechnungsnummer}" />
          </div>
          <div>
            <label className={labelCls}>
              Text-Vorlage (optional – leer = Standardtext)
            </label>
            <textarea
              className={`${inputCls} font-mono text-xs`}
              rows={5}
              value={form.text_vorlage ?? ''}
              onChange={(e) => setForm({ ...form, text_vorlage: e.target.value })}
              placeholder="Sehr geehrte Damen und Herren,..."
            />
            <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-1">
              Platzhalter: {'{rechnungsnummer} {offener_betrag} {mahngebuehr} {verzugszinsen} {gesamtforderung} {bezeichnung} {stufe} {kunde} {firmenname} {datum}'}
            </p>
          </div>
          <div className="flex justify-end items-center gap-3">
            {saveFehler && <span className="text-xs text-red-600 dark:text-red-400">{saveFehler}</span>}
            {gespeichert && !saveMut.isPending && (
              <span className="text-xs text-green-600 dark:text-green-400">Gespeichert ✓</span>
            )}
            <button
              type="button"
              onClick={speichern}
              disabled={saveMut.isPending}
              className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {saveMut.isPending ? 'Speichert…' : 'Speichern'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export function MahnwesenEinstellungenPage() {
  const mxAuto = useMxAuto()
  const qc = useQueryClient()

  const { data: einst, isLoading } = useQuery({
    queryKey: ['mahnwesen-einstellungen'],
    queryFn: getMahnwesenEinstellungen,
  })
  const { data: unternehmen } = useQuery({
    queryKey: ['unternehmen'],
    queryFn: getUnternehmen,
    staleTime: 1000 * 60 * 5,
  })
  const smtpAktiv = !!unternehmen?.smtp_aktiv

  const patchMut = useMutation({
    mutationFn: (data: MahnwesenEinstellungenUpdate) => updateMahnwesenEinstellungen(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mahnwesen-einstellungen'] }),
  })
  const patchFehler = patchMut.isError ? (patchMut.error as Error).message : null

  const neueStufeMut = useMutation({
    // stufe wird vom Backend überschrieben - neue Stufen werden immer vor der bisher letzten
    // Stufe eingefügt (unabhängig davon ob diese aktiv ist), siehe mahnstufe_create().
    mutationFn: () => createMahnstufe({
      stufe: 0,
      bezeichnung: 'Neue Mahnstufe',
      tage_nach_faelligkeit: 7,
      tage_nach_vorheriger: 14,
      betreff_vorlage: null,
      text_vorlage: null,
      mahngebuehr_aktiv: false,
      mahngebuehr_privat: '5.00',
      mahngebuehr_gewerblich: '40.00',
      aktiv: true,
      anhang_rechnung: false,
      anhang_bisherige_mahnungen: false,
      anhang_kontokorrent: false,
    }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mahnwesen-einstellungen'] }),
  })

  if (isLoading || !einst) {
    return <div className={`max-w-2xl ${mxAuto} p-6`}><p className="text-sm text-slate-400">Lade…</p></div>
  }

  const stufenSortiert = [...einst.mahnstufen].sort((a, b) => a.stufe - b.stufe)
  // Für "ab Stufe X"-Schwellenwerte (Konsolidierung/Kundensperrung/Verzugszinsen) nur aktive
  // Stufen anbieten - eine deaktivierte Stufe wird nie erreicht (_naechste_aktive_stufe
  // überspringt sie), als Schwelle wäre sie irreführend. Der Mahnstufen-Editor selbst zeigt
  // weiterhin alle Stufen (dort werden sie ja gerade an-/abgeschaltet).
  const aktiveStufenSortiert = stufenSortiert.filter((s) => s.aktiv)

  return (
    <div className={`max-w-2xl ${mxAuto} p-6 space-y-6`}>
      <div>
        <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">Mahnwesen</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
          Konfigurierbare Mahnstufen mit Vorlagen, Mahngebühren und Verzugszinsen. Bleibt für
          Nutzer:innen die z. B. nur auf Vorkasse arbeiten komplett ausgeblendet, solange deaktiviert.
        </p>
      </div>

      <div className="flex items-center justify-between border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3">
        <div>
          <p className="text-sm font-medium text-slate-800 dark:text-slate-100">Mahnwesen aktivieren</p>
          <p className="text-xs text-slate-500 dark:text-slate-400">Blendet den Menüpunkt „Mahnwesen" und alle zugehörigen Funktionen ein.</p>
        </div>
        <Toggle checked={einst.aktiv} onChange={(v) => patchMut.mutate({ aktiv: v })} />
      </div>

      {einst.aktiv && (
        <>
          <div className="border border-slate-200 dark:border-slate-700 rounded-xl p-4 space-y-4">
            <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">Automatisierung & Versand</p>
            <div>
              <label className={labelCls}>Automation</label>
              <div className="flex gap-4 text-sm text-slate-600 dark:text-slate-300">
                {(['manuell', 'halb', 'voll'] as const).map((m) => {
                  const gesperrt = m === 'voll' && !smtpAktiv
                  return (
                    <label
                      key={m}
                      className={`flex items-center gap-1.5 ${gesperrt ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
                      title={gesperrt ? 'Erst verfügbar, wenn unter Einstellungen → E-Mail/SMTP der Mail-Versand aktiviert ist.' : undefined}
                    >
                      <input
                        type="radio"
                        checked={einst.automation_modus === m}
                        disabled={gesperrt}
                        onChange={() => patchMut.mutate({ automation_modus: m })}
                      />
                      {m === 'manuell' ? 'Manuell' : m === 'halb' ? 'Halbautomatik' : 'Vollautomatik'}
                    </label>
                  )
                })}
              </div>
              {!smtpAktiv && (
                <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-1">
                  Vollautomatik ist erst wählbar, wenn unter Einstellungen → E-Mail/SMTP der Mail-Versand eingerichtet und aktiviert ist.
                </p>
              )}
              {patchFehler && (
                <p className="text-xs text-red-600 dark:text-red-400 mt-1">{patchFehler}</p>
              )}
            </div>
            <div className="flex gap-4 text-sm text-slate-600 dark:text-slate-300">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input type="checkbox" checked={einst.versand_mail} onChange={(e) => patchMut.mutate({ versand_mail: e.target.checked })} className="rounded" />
                Per Mail versenden
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input type="checkbox" checked={einst.versand_pdf} onChange={(e) => patchMut.mutate({ versand_pdf: e.target.checked })} className="rounded" />
                PDF zusätzlich ablegen
              </label>
            </div>
            <div>
              <label className={labelCls}>Konsolidierung: mehrere offene Rechnungen ab Stufe zusammenfassen</label>
              <select
                className={inputCls}
                value={einst.konsolidiert_ab_stufe}
                onChange={(e) => patchMut.mutate({ konsolidiert_ab_stufe: parseInt(e.target.value) })}
              >
                {aktiveStufenSortiert.map((s) => <option key={s.id} value={s.stufe}>ab Stufe {s.stufe} ({s.bezeichnung})</option>)}
              </select>
            </div>
          </div>

          <div className="border border-slate-200 dark:border-slate-700 rounded-xl p-4 space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">Kundensperrung</p>
              <Toggle checked={einst.kundensperrung_aktiv} onChange={(v) => patchMut.mutate({ kundensperrung_aktiv: v })} />
            </div>
            {einst.kundensperrung_aktiv && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelCls}>Warnung ab Stufe</label>
                  <select
                    className={inputCls}
                    value={einst.kundensperrung_warnung_ab_stufe ?? ''}
                    onChange={(e) => patchMut.mutate({ kundensperrung_warnung_ab_stufe: e.target.value === '' ? null : parseInt(e.target.value) })}
                  >
                    <option value="">— keine —</option>
                    {aktiveStufenSortiert.map((s) => <option key={s.id} value={s.stufe}>Stufe {s.stufe} ({s.bezeichnung})</option>)}
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Sperrung ab Stufe</label>
                  <select
                    className={inputCls}
                    value={einst.kundensperrung_sperrung_ab_stufe ?? ''}
                    onChange={(e) => patchMut.mutate({ kundensperrung_sperrung_ab_stufe: e.target.value === '' ? null : parseInt(e.target.value) })}
                  >
                    <option value="">— keine —</option>
                    {aktiveStufenSortiert.map((s) => <option key={s.id} value={s.stufe}>Stufe {s.stufe} ({s.bezeichnung})</option>)}
                  </select>
                </div>
              </div>
            )}
          </div>

          <div className="border border-slate-200 dark:border-slate-700 rounded-xl p-4 space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">Verzugszinsen (§288 BGB)</p>
              <Toggle checked={einst.verzugszinsen_aktiv} onChange={(v) => patchMut.mutate({ verzugszinsen_aktiv: v })} />
            </div>
            {einst.verzugszinsen_aktiv && (
              <>
                <div>
                  <label className={labelCls}>Ab Stufe</label>
                  <select className={inputCls} value={einst.verzugszinsen_ab_stufe} onChange={(e) => patchMut.mutate({ verzugszinsen_ab_stufe: parseInt(e.target.value) })}>
                    {aktiveStufenSortiert.map((s) => <option key={s.id} value={s.stufe}>Stufe {s.stufe} ({s.bezeichnung})</option>)}
                  </select>
                </div>
                <div>
                  <label className={labelCls}>
                    Basiszinssatz (%) – <a href="https://www.bundesbank.de/de/aufgaben/geldpolitik/zinssaetze/basiszinssatz-607820" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">aktueller Wert bei der Bundesbank</a>
                  </label>
                  <input className={`${inputCls} w-32`} value={einst.basiszinssatz} onChange={(e) => patchMut.mutate({ basiszinssatz: e.target.value })} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className={labelCls}>Aufschlag privat (Prozentpunkte)</label>
                    <input className={inputCls} value={einst.verzugszinsen_aufschlag_privat} onChange={(e) => patchMut.mutate({ verzugszinsen_aufschlag_privat: e.target.value })} />
                  </div>
                  <div>
                    <label className={labelCls}>Aufschlag gewerblich (Prozentpunkte)</label>
                    <input className={inputCls} value={einst.verzugszinsen_aufschlag_gewerblich} onChange={(e) => patchMut.mutate({ verzugszinsen_aufschlag_gewerblich: e.target.value })} />
                  </div>
                </div>
              </>
            )}
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">Mahnstufen</p>
              <button type="button" onClick={() => neueStufeMut.mutate()} className="text-xs text-blue-600 hover:underline">
                + Neue Stufe
              </button>
            </div>
            <div className="space-y-2">
              {stufenSortiert.map((s) => (
                <MahnstufeCard
                  key={s.id}
                  stufe={s}
                  istErsteStufe={stufenSortiert[0]?.id === s.id}
                  istErsteAktiveStufe={aktiveStufenSortiert[0]?.id === s.id}
                  onSaved={() => qc.invalidateQueries({ queryKey: ['mahnwesen-einstellungen'] })}
                />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
