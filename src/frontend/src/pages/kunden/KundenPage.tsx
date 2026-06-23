import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import {
  getKunden, createKunde, updateKunde, deleteKunde,
  anonymisiereKunde, dsgvoExportKunde, dsgvoExportKundePdf, getRechnungen, getAngebote, getUnternehmen,
  getLieferadressen, createLieferadresse, updateLieferadresse, deleteLieferadresse,
  getKundeBelege, uploadKundeBeleg, deleteKundeBeleg, updateKundeBeleg, getKundeBelegDownloadUrl,
  type Kunde, type AnonymisierungResult, type Rechnung, type KundeLieferadresse, type KundeBeleg,
} from '../../api/client'

function formatEuro(val: string | number): string {
  const n = typeof val === 'string' ? parseFloat(val) : val
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n)
}

function formatDatum(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

function kundeName(k: Kunde): string {
  return k.firmenname || [k.vorname, k.nachname].filter(Boolean).join(' ') || '—'
}

// ---------------------------------------------------------------------------
// Lieferadressen-Sektion im Kundenformular
// ---------------------------------------------------------------------------

function KundeLieferadressen({ kundeId }: { kundeId: number }) {
  const qc = useQueryClient()
  const [editId, setEditId] = useState<number | 'neu' | null>(null)
  const [form, setForm] = useState<Omit<KundeLieferadresse, 'id' | 'kunde_id'>>({
    bezeichnung: '', z_hd: '', strasse: '', hausnummer: '', plz: '', ort: '', land: 'DE', ist_standard: false,
  })

  const { data: adressen = [] } = useQuery({
    queryKey: ['lieferadressen', kundeId],
    queryFn: () => getLieferadressen(kundeId),
  })

  const saveMut = useMutation({
    mutationFn: () => editId === 'neu'
      ? createLieferadresse(kundeId, form)
      : updateLieferadresse(kundeId, editId as number, form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['lieferadressen', kundeId] }); setEditId(null) },
  })

  const delMut = useMutation({
    mutationFn: (id: number) => deleteLieferadresse(kundeId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['lieferadressen', kundeId] }),
  })

  function startEdit(la: KundeLieferadresse) {
    setEditId(la.id!)
    setForm({ bezeichnung: la.bezeichnung ?? '', z_hd: la.z_hd ?? '', strasse: la.strasse ?? '',
      hausnummer: la.hausnummer ?? '', plz: la.plz ?? '', ort: la.ort ?? '', land: la.land, ist_standard: la.ist_standard })
  }

  const inp = 'border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500'

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Lieferadressen</span>
        <button type="button" onClick={() => { setEditId('neu'); setForm({ bezeichnung: '', z_hd: '', strasse: '', hausnummer: '', plz: '', ort: '', land: 'DE', ist_standard: false }) }}
          className="text-xs text-blue-600 hover:text-blue-700 font-medium">+ Hinzufügen</button>
      </div>

      {adressen.map(la => (
        <div key={la.id} className="border border-slate-200 dark:border-slate-700 rounded-lg p-3 text-sm">
          {editId === la.id ? (
            <div className="space-y-2">
              <input placeholder="Bezeichnung (z.B. Lager Nord)" value={form.bezeichnung ?? ''} onChange={e => setForm(f => ({ ...f, bezeichnung: e.target.value }))} className={`${inp} w-full`} />
              <input placeholder="z.Hd." value={form.z_hd ?? ''} onChange={e => setForm(f => ({ ...f, z_hd: e.target.value }))} className={`${inp} w-full`} />
              <div className="grid grid-cols-3 gap-2">
                <input placeholder="Straße" value={form.strasse ?? ''} onChange={e => setForm(f => ({ ...f, strasse: e.target.value }))} className={`${inp} col-span-2`} />
                <input placeholder="Nr." value={form.hausnummer ?? ''} onChange={e => setForm(f => ({ ...f, hausnummer: e.target.value }))} className={inp} />
              </div>
              <div className="grid grid-cols-3 gap-2">
                <input placeholder="PLZ" value={form.plz ?? ''} onChange={e => setForm(f => ({ ...f, plz: e.target.value }))} className={inp} />
                <input placeholder="Ort" value={form.ort ?? ''} onChange={e => setForm(f => ({ ...f, ort: e.target.value }))} className={`${inp} col-span-2`} />
              </div>
              <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300 cursor-pointer">
                <input type="checkbox" checked={form.ist_standard} onChange={e => setForm(f => ({ ...f, ist_standard: e.target.checked }))} />
                Standard-Lieferadresse
              </label>
              <div className="flex gap-2">
                <button type="button" onClick={() => saveMut.mutate()} disabled={saveMut.isPending}
                  className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50">Speichern</button>
                <button type="button" onClick={() => setEditId(null)} className="px-3 py-1 border border-slate-300 dark:border-slate-600 text-xs rounded text-slate-600 dark:text-slate-300">Abbrechen</button>
              </div>
            </div>
          ) : (
            <div className="flex items-start justify-between gap-2">
              <div>
                {la.ist_standard && <span className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded px-1 mr-1">Standard</span>}
                <span className="font-medium text-slate-800 dark:text-slate-100">{la.bezeichnung || 'Lieferadresse'}</span>
                {la.z_hd && <div className="text-slate-500 dark:text-slate-400 text-xs">z.Hd. {la.z_hd}</div>}
                <div className="text-slate-600 dark:text-slate-300 text-xs">{[la.strasse, la.hausnummer].filter(Boolean).join(' ')}</div>
                <div className="text-slate-600 dark:text-slate-300 text-xs">{[la.plz, la.ort].filter(Boolean).join(' ')}</div>
              </div>
              <div className="flex gap-1 shrink-0">
                <button type="button" onClick={() => startEdit(la)} className="text-xs text-blue-600 hover:text-blue-700">Bearb.</button>
                <button type="button" onClick={() => delMut.mutate(la.id!)} className="text-xs text-red-500 hover:text-red-600">Löschen</button>
              </div>
            </div>
          )}
        </div>
      ))}

      {editId === 'neu' && (
        <div className="border border-blue-300 dark:border-blue-700 rounded-lg p-3 space-y-2">
          <input placeholder="Bezeichnung (z.B. Lager Nord)" value={form.bezeichnung ?? ''} onChange={e => setForm(f => ({ ...f, bezeichnung: e.target.value }))} className={`${inp} w-full`} />
          <input placeholder="z.Hd." value={form.z_hd ?? ''} onChange={e => setForm(f => ({ ...f, z_hd: e.target.value }))} className={`${inp} w-full`} />
          <div className="grid grid-cols-3 gap-2">
            <input placeholder="Straße" value={form.strasse ?? ''} onChange={e => setForm(f => ({ ...f, strasse: e.target.value }))} className={`${inp} col-span-2`} />
            <input placeholder="Nr." value={form.hausnummer ?? ''} onChange={e => setForm(f => ({ ...f, hausnummer: e.target.value }))} className={inp} />
          </div>
          <div className="grid grid-cols-3 gap-2">
            <input placeholder="PLZ" value={form.plz ?? ''} onChange={e => setForm(f => ({ ...f, plz: e.target.value }))} className={inp} />
            <input placeholder="Ort" value={form.ort ?? ''} onChange={e => setForm(f => ({ ...f, ort: e.target.value }))} className={`${inp} col-span-2`} />
          </div>
          <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300 cursor-pointer">
            <input type="checkbox" checked={form.ist_standard} onChange={e => setForm(f => ({ ...f, ist_standard: e.target.checked }))} />
            Standard-Lieferadresse
          </label>
          <div className="flex gap-2">
            <button type="button" onClick={() => saveMut.mutate()} disabled={saveMut.isPending}
              className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50">Speichern</button>
            <button type="button" onClick={() => setEditId(null)} className="px-3 py-1 border border-slate-300 dark:border-slate-600 text-xs rounded text-slate-600 dark:text-slate-300">Abbrechen</button>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Dokumente im Kundenstamm
// ---------------------------------------------------------------------------

function KundeDokumente({ kundeId }: { kundeId: number }) {
  const qc = useQueryClient()
  const [editId, setEditId] = useState<number | null>(null)
  const [editLabel, setEditLabel] = useState('')
  const [editLoeschdatum, setEditLoeschdatum] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadLabel, setUploadLabel] = useState('')
  const [uploadLoeschdatum, setUploadLoeschdatum] = useState('')

  const { data: docs = [] } = useQuery({
    queryKey: ['kunde-belege', kundeId],
    queryFn: () => getKundeBelege(kundeId),
  })

  const delMut = useMutation({
    mutationFn: (kbId: number) => deleteKundeBeleg(kundeId, kbId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['kunde-belege', kundeId] }),
  })

  const updateMut = useMutation({
    mutationFn: ({ kbId, label, ld }: { kbId: number; label: string; ld: string }) =>
      updateKundeBeleg(kundeId, kbId, {
        bezeichnung: label,
        loeschdatum: ld || undefined,
        loeschdatum_loeschen: ld === '',
      }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['kunde-belege', kundeId] }); setEditId(null) },
  })

  async function handleUpload(e: { target: HTMLInputElement }) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      await uploadKundeBeleg(kundeId, file, uploadLabel, uploadLoeschdatum || undefined)
      qc.invalidateQueries({ queryKey: ['kunde-belege', kundeId] })
      setUploadLabel('')
      setUploadLoeschdatum('')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  async function handleOpen(kb: KundeBeleg) {
    const url = await getKundeBelegDownloadUrl(kundeId, kb.id)
    window.open(url, '_blank')
  }

  function fileIcon(mime?: string) {
    if (!mime) return '📎'
    if (mime === 'application/pdf') return '📄'
    if (mime.startsWith('image/')) return '🖼'
    if (mime.includes('word')) return '📝'
    return '📎'
  }

  function fmtSize(bytes?: number) {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  }

  function loeschdatumBadge(ld?: string) {
    if (!ld) return null
    const heute = new Date().toISOString().slice(0, 10)
    const tage = Math.ceil((new Date(ld).getTime() - new Date(heute).getTime()) / 86400000)
    if (tage < 0)
      return <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 font-medium">Löschen überfällig ({formatDatum(ld)})</span>
    if (tage <= 30)
      return <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 font-medium">Löschen bis {formatDatum(ld)}</span>
    return <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400">Löschen bis {formatDatum(ld)}</span>
  }

  const inp = 'border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500'

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Dokumente</span>
      </div>

      {docs.map(kb => (
        <div key={kb.id} className={`border rounded-lg p-3 text-sm ${kb.loeschdatum && kb.loeschdatum < new Date().toISOString().slice(0,10) ? 'border-red-300 dark:border-red-700' : 'border-slate-200 dark:border-slate-700'}`}>
          {editId === kb.id ? (
            <div className="space-y-2">
              <input value={editLabel} onChange={e => setEditLabel(e.target.value)}
                className={`${inp} w-full`} placeholder="Bezeichnung" autoFocus />
              <div>
                <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Löschdatum (DSGVO)</label>
                <input type="date" value={editLoeschdatum} onChange={e => setEditLoeschdatum(e.target.value)}
                  className={`${inp} w-full`} />
                {editLoeschdatum && <button type="button" onClick={() => setEditLoeschdatum('')}
                  className="text-xs text-slate-400 hover:text-slate-600 mt-1">× Kein Löschdatum</button>}
              </div>
              <div className="flex gap-2">
                <button type="button"
                  onClick={() => updateMut.mutate({ kbId: kb.id, label: editLabel, ld: editLoeschdatum })}
                  className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700">Speichern</button>
                <button type="button" onClick={() => setEditId(null)}
                  className="px-3 py-1 border border-slate-300 dark:border-slate-600 text-xs rounded text-slate-600 dark:text-slate-300">Abbruch</button>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-2">
              <span className="text-base shrink-0 mt-0.5">{fileIcon(kb.beleg.mime_type)}</span>
              <div className="flex-1 min-w-0">
                <button type="button" onClick={() => handleOpen(kb)}
                  className="text-blue-600 dark:text-blue-400 hover:underline text-left truncate block max-w-full font-medium">
                  {kb.bezeichnung || kb.beleg.original_name}
                </button>
                {kb.bezeichnung && <div className="text-xs text-slate-400 truncate">{kb.beleg.original_name}</div>}
                <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                  <span className="text-xs text-slate-400">{fmtSize(kb.beleg.dateigroesse)}</span>
                  {loeschdatumBadge(kb.loeschdatum)}
                </div>
              </div>
              <div className="flex gap-1 shrink-0">
                <button type="button"
                  onClick={() => { setEditId(kb.id); setEditLabel(kb.bezeichnung ?? ''); setEditLoeschdatum(kb.loeschdatum ?? '') }}
                  className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300">Bearb.</button>
                <button type="button"
                  onClick={() => { if (confirm('Dokument löschen?')) delMut.mutate(kb.id) }}
                  className="text-xs text-red-500 hover:text-red-600">Löschen</button>
              </div>
            </div>
          )}
        </div>
      ))}

      <div className="border border-dashed border-slate-300 dark:border-slate-600 rounded-lg p-3 space-y-2">
        <input type="text" value={uploadLabel} onChange={e => setUploadLabel(e.target.value)}
          placeholder="Bezeichnung (optional)" className={`${inp} w-full`} />
        <div>
          <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Löschdatum (DSGVO, optional)</label>
          <input type="date" value={uploadLoeschdatum} onChange={e => setUploadLoeschdatum(e.target.value)}
            className={`${inp} w-full`} />
        </div>
        <label className={`flex items-center justify-center gap-2 px-3 py-2 text-xs rounded-lg cursor-pointer
          ${uploading
            ? 'bg-slate-100 dark:bg-slate-700 text-slate-400 cursor-not-allowed'
            : 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/50 border border-blue-200 dark:border-blue-700'}`}>
          {uploading ? 'Wird hochgeladen …' : '+ Dokument hochladen'}
          <input type="file" className="hidden" disabled={uploading}
            accept=".pdf,.jpg,.jpeg,.png,.tiff,.doc,.docx"
            onChange={handleUpload} />
        </label>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Rechts: Rechnungspanel
// ---------------------------------------------------------------------------

function KundeRechnungen({ kunde }: { kunde: Kunde }) {
  const navigate = useNavigate()
  const [offeneRechnung, setOffeneRechnung] = useState<number | null>(null)
  const [tab, setTab] = useState<'rechnungen' | 'angebote' | 'dokumente'>('rechnungen')

  const { data: unternehmen } = useQuery({ queryKey: ['unternehmen'], queryFn: getUnternehmen, staleTime: 1000 * 60 * 5 })
  const angeboteAktiv = !!unternehmen?.angebote_aktiv
  const auftraegeAktiv = !!unternehmen?.auftraege_aktiv
  const proformaAktiv = !!unternehmen?.proforma_aktiv
  const lieferscheinAktiv = !!unternehmen?.lieferschein_aktiv

  const { data: rechnungen, isLoading: laegtRechnungen } = useQuery({
    queryKey: ['kunden-rechnungen', kunde.id],
    queryFn: () => getRechnungen({ typ: 'ausgang', kunde_id: kunde.id }),
    staleTime: 1000 * 60,
  })

  const { data: angebote, isLoading: laegtAngebote } = useQuery({
    queryKey: ['kunden-angebote', kunde.id],
    queryFn: () => getAngebote(),
    select: (data: Rechnung[]) => data.filter(a => a.kunde_id === kunde.id),
    enabled: angeboteAktiv,
    staleTime: 1000 * 60,
  })

  const isLoading = tab === 'rechnungen' ? laegtRechnungen : laegtAngebote
  const liste = tab === 'rechnungen' ? (rechnungen ?? []) : (angebote ?? [])

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 shrink-0 space-y-2">
        {/* Tabs */}
        <div className="flex gap-1">
          <button onClick={() => setTab('rechnungen')}
            className={`flex-1 text-xs py-1 rounded border transition-colors ${tab === 'rechnungen' ? 'bg-blue-600 text-white border-blue-600' : 'border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700'}`}>
            Rechnungen ({rechnungen?.length ?? '…'})
          </button>
          {angeboteAktiv && (
            <button onClick={() => setTab('angebote')}
              className={`flex-1 text-xs py-1 rounded border transition-colors ${tab === 'angebote' ? 'bg-blue-600 text-white border-blue-600' : 'border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700'}`}>
              Angebote ({angebote?.length ?? '…'})
            </button>
          )}
          <button onClick={() => setTab('dokumente')}
            className={`flex-1 text-xs py-1 rounded border transition-colors ${tab === 'dokumente' ? 'bg-blue-600 text-white border-blue-600' : 'border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700'}`}>
            Dokumente
          </button>
        </div>
        {/* Aktions-Buttons – nur bei Rechnungen/Angebote-Tab */}
        {tab !== 'dokumente' && (
          <div className="flex flex-wrap gap-1">
            <button
              onClick={() => navigate(`/rechnungen?neue_aus_kunde=${kunde.id}`)}
              className="text-[11px] py-1 px-2 border border-slate-300 dark:border-slate-600 rounded text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
              + Neue Rechnung
            </button>
            {angeboteAktiv && (
              <button
                onClick={() => navigate(`/angebote?kunde_id=${kunde.id}`)}
                className="text-[11px] py-1 px-2 border border-slate-300 dark:border-slate-600 rounded text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                + Neues Angebot
              </button>
            )}
            {auftraegeAktiv && (
              <button
                onClick={() => navigate(`/auftraege?neue_aus_kunde=${kunde.id}`)}
                className="text-[11px] py-1 px-2 border border-slate-300 dark:border-slate-600 rounded text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                + Neuer Auftrag
              </button>
            )}
            {proformaAktiv && (
              <button
                onClick={() => navigate(`/proformas?neue_aus_kunde=${kunde.id}`)}
                className="text-[11px] py-1 px-2 border border-slate-300 dark:border-slate-600 rounded text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                + Neue Proforma
              </button>
            )}
            {lieferscheinAktiv && (
              <button
                onClick={() => navigate(`/lieferscheine?neue_aus_kunde=${kunde.id}`)}
                className="text-[11px] py-1 px-2 border border-slate-300 dark:border-slate-600 rounded text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                + Neuer Lieferschein
              </button>
            )}
          </div>
        )}
      </div>
      <div className="flex-1 overflow-y-auto px-3 py-3">
        {tab === 'dokumente' ? (
          <KundeDokumente kundeId={kunde.id!} />
        ) : (<div className="space-y-1.5">
        {isLoading && <p className="text-xs text-slate-400 dark:text-slate-500 p-1">Lade…</p>}
        {!isLoading && !liste.length && (
          <p className="text-xs text-slate-400 dark:text-slate-500 p-1">
            {tab === 'rechnungen' ? 'Noch keine Ausgangsrechnungen.' : 'Noch keine Angebote.'}
          </p>
        )}
        {liste.map((r: Rechnung) => (
          <div key={r.id} className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
            <button
              type="button"
              onClick={() => setOffeneRechnung(offeneRechnung === r.id ? null : r.id)}
              className="w-full flex items-center justify-between px-3 py-2 text-xs hover:bg-slate-50 dark:hover:bg-slate-700 text-left gap-2 dark:bg-slate-800"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="font-mono text-slate-400 dark:text-slate-500 shrink-0">{r.rechnungsnummer ?? '—'}</span>
                  <span className="font-semibold text-slate-700 dark:text-slate-200">{formatEuro(r.brutto_gesamt)}</span>
                </div>
                <div className="text-slate-400 dark:text-slate-500">{formatDatum(r.datum)}</div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                {tab === 'angebote' ? (
                  <span className={`px-1.5 py-0.5 rounded-full border text-[10px] ${
                    r.angebot_status === 'akzeptiert' ? 'bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800'
                    : r.angebot_status === 'abgelehnt' ? 'bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-800'
                    : r.angebot_status === 'abgelaufen' ? 'bg-slate-100 text-slate-500 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700'
                    : 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800'
                  }`}>
                    {r.angebot_status === 'akzeptiert' ? 'Akzeptiert' : r.angebot_status === 'abgelehnt' ? 'Abgelehnt' : r.angebot_status === 'abgelaufen' ? 'Abgelaufen' : 'Offen'}
                  </span>
                ) : (
                  <span className={`px-1.5 py-0.5 rounded-full border text-[10px] ${
                    r.zahlungsstatus === 'bezahlt' ? 'bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800'
                    : r.zahlungsstatus === 'teilweise' ? 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800'
                    : 'bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-800'
                  }`}>
                    {r.zahlungsstatus === 'bezahlt' ? 'Bezahlt' : r.zahlungsstatus === 'teilweise' ? 'Teil' : 'Offen'}
                  </span>
                )}
                <span className="text-slate-400 dark:text-slate-500">{offeneRechnung === r.id ? '▲' : '▼'}</span>
              </div>
            </button>
            {offeneRechnung === r.id && r.positionen.length > 0 && (
              <div className="border-t border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 px-3 py-2">
                {r.positionen.map((p) => (
                  <div key={p.id} className="flex items-start justify-between gap-2 py-1 border-b border-slate-100 dark:border-slate-700 last:border-0 text-xs">
                    <span className="text-slate-700 dark:text-slate-200 min-w-0">
                      {p.beschreibung}
                      {p.artikel_typ && (
                        <span className="ms-1 text-slate-400 dark:text-slate-500 bg-slate-200 dark:bg-slate-700 rounded px-1 py-0.5 text-[10px]">
                          {p.artikel_typ === 'artikel' ? 'Artikel' : p.artikel_typ === 'dienstleistung' ? 'Dienstl.' : 'Fremdl.'}
                        </span>
                      )}
                    </span>
                    <span className="text-slate-500 dark:text-slate-400 shrink-0">{formatEuro(p.brutto)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        </div>)}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Formular-Schema
// ---------------------------------------------------------------------------

const schema = z.object({
  firmenname: z.string().optional(),
  vorname: z.string().optional(),
  nachname: z.string().optional(),
  strasse: z.string().optional(),
  hausnummer: z.string().optional(),
  plz: z.string().optional(),
  ort: z.string().optional(),
  land: z.string().optional(),
  ust_idnr: z.string().optional(),
  email: z.string().email('Ungültige E-Mail').optional().or(z.literal('')),
  telefon: z.string().optional(),
  kundennummer: z.string().optional(),
  z_hd: z.string().optional(),
  notizen: z.string().optional(),
  ist_verein: z.boolean().optional(),
  ist_gemeinnuetzig: z.boolean().optional(),
  zugferd_aktiv: z.boolean().optional(),
  skonto_prozent: z.number().min(0).max(100).nullable().optional(),
  skonto_tage: z.number().int().min(1).max(365).nullable().optional(),
}).superRefine((data, ctx) => {
  if (!data.zugferd_aktiv) return
  if (!data.firmenname?.trim()) ctx.addIssue({ code: 'custom', path: ['firmenname'], message: 'Pflichtfeld für ZUGFeRD' })
  if (!data.strasse?.trim()) ctx.addIssue({ code: 'custom', path: ['strasse'], message: 'Pflichtfeld für ZUGFeRD' })
  if (!data.plz?.trim()) ctx.addIssue({ code: 'custom', path: ['plz'], message: 'Pflichtfeld für ZUGFeRD' })
  if (!data.ort?.trim()) ctx.addIssue({ code: 'custom', path: ['ort'], message: 'Pflichtfeld für ZUGFeRD' })
})

type FormValues = z.infer<typeof schema>

const EMPTY: FormValues = {
  firmenname: '', vorname: '', nachname: '', strasse: '', hausnummer: '',
  plz: '', ort: '', land: 'DE', ust_idnr: '', email: '', telefon: '',
  kundennummer: '', z_hd: '', notizen: '', ist_verein: false, ist_gemeinnuetzig: false, zugferd_aktiv: false,
  skonto_prozent: null, skonto_tage: null,
}

// ---------------------------------------------------------------------------
// Hauptseite
// ---------------------------------------------------------------------------

export function KundenPage() {
  const qc = useQueryClient()
  const [selected, setSelected] = useState<Kunde | null>(null)
  const [suche, setSuche] = useState('')
  const [editKunde, setEditKunde] = useState<Kunde | null>(null)
  const [showForm, setShowForm] = useState(false)

  const [deleteFehlgeschlagen, setDeleteFehlgeschlagen] = useState(false)
  const [showDsgvoBestaetigung, setShowDsgvoBestaetigung] = useState(false)
  const [anonymisierungResult, setAnonymisierungResult] = useState<AnonymisierungResult | null>(null)

  const { data: kunden, isLoading } = useQuery({ queryKey: ['kunden'], queryFn: getKunden })

  const createMutation = useMutation({
    mutationFn: createKunde,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['kunden'] }); closeForm() },
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Kunde> }) => updateKunde(id, data),
    onSuccess: (updated) => { qc.invalidateQueries({ queryKey: ['kunden'] }); setSelected(updated); closeForm() },
  })
  const deleteMutation = useMutation({
    mutationFn: (k: Kunde) => deleteKunde(k.id!),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['kunden'] }); setSelected(null) },
    onError: (_err: Error, k: Kunde) => { setDeleteFehlgeschlagen(true); openEdit(k) },
  })
  const anonymisierungMutation = useMutation({
    mutationFn: (id: number) => anonymisiereKunde(id),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ['kunden'] })
      setAnonymisierungResult(result)
      setShowDsgvoBestaetigung(false)
    },
  })

  const { register, handleSubmit, reset, control, setValue, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: EMPTY,
  })
  const watchFirmenname = useWatch({ control, name: 'firmenname' })
  const watchUstIdnr = useWatch({ control, name: 'ust_idnr' })
  const watchZugferd = useWatch({ control, name: 'zugferd_aktiv' })
  const zugferdAutoAktiv = !!(watchFirmenname?.trim() && watchUstIdnr?.trim())
  const zugferdOhneUstId = !!(watchZugferd && !watchUstIdnr?.trim())

  useEffect(() => {
    if (zugferdAutoAktiv) setValue('zugferd_aktiv', true)
  }, [zugferdAutoAktiv, setValue])

  function openCreate() { setEditKunde(null); reset(EMPTY); setShowForm(true) }

  function openEdit(k: Kunde) {
    setEditKunde(k)
    reset({
      firmenname: k.firmenname ?? '', vorname: k.vorname ?? '', nachname: k.nachname ?? '',
      strasse: k.strasse ?? '', hausnummer: k.hausnummer ?? '', plz: k.plz ?? '',
      ort: k.ort ?? '', land: k.land, ust_idnr: k.ust_idnr ?? '',
      email: k.email ?? '', telefon: k.telefon ?? '', kundennummer: k.kundennummer ?? '',
      z_hd: k.z_hd ?? '', notizen: k.notizen ?? '', ist_verein: k.ist_verein, ist_gemeinnuetzig: k.ist_gemeinnuetzig,
      zugferd_aktiv: k.zugferd_aktiv ?? false,
      skonto_prozent: (k as any).skonto_prozent ?? null,
      skonto_tage: (k as any).skonto_tage ?? null,
    })
    setShowForm(true)
  }

  function closeForm() {
    setShowForm(false); setEditKunde(null)
    setDeleteFehlgeschlagen(false); setShowDsgvoBestaetigung(false); setAnonymisierungResult(null)
  }

  function onSubmit(values: FormValues) {
    const clean = Object.fromEntries(
      Object.entries(values).map(([k, v]) => [k, v === '' ? undefined : v])
    ) as Partial<Kunde>
    if (editKunde?.id) {
      updateMutation.mutate({ id: editKunde.id, data: clean })
    } else {
      createMutation.mutate({ ...clean, ist_verein: values.ist_verein ?? false, ist_gemeinnuetzig: values.ist_gemeinnuetzig ?? false, land: values.land ?? 'DE' })
    }
  }

  function handleDelete(k: Kunde) {
    if (!k.id) return
    if (!window.confirm(`Kunden "${kundeName(k)}" löschen?`)) return
    deleteMutation.mutate(k)
  }

  const s = suche.toLowerCase()
  const gefiltert = (kunden ?? []).filter((k) =>
    !s || kundeName(k).toLowerCase().includes(s) ||
    (k.email ?? '').toLowerCase().includes(s) ||
    (k.kundennummer ?? '').toLowerCase().includes(s) ||
    (k.ort ?? '').toLowerCase().includes(s)
  )

  const isPending = createMutation.isPending || updateMutation.isPending
  const mutationError = createMutation.error || updateMutation.error

  return (
    <div className="flex h-full">

      {/* ── Linke Spalte (breit) ─────────────────────────────────────── */}
      <div className={`${showForm ? 'w-1/3 min-w-[260px] shrink-0' : 'flex-1'} flex flex-col border-e border-slate-200 dark:border-slate-700 min-w-0 transition-all`}>

        {/* Header */}
        <div className="p-6 pb-4 shrink-0">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Kunden</h2>
            <button onClick={openCreate} className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-xl hover:bg-blue-700">
              + Neu
            </button>
          </div>
          <input
            type="text"
            placeholder="Suchen…"
            value={suche}
            onChange={(e) => setSuche(e.target.value)}
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100"
          />
        </div>

        {/* Tabelle */}
        <div className="flex-1 overflow-y-auto min-h-0 px-6 pb-6">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          {isLoading ? (
            <p className="text-slate-400 dark:text-slate-500 text-sm p-5">Lade…</p>
          ) : !gefiltert.length ? (
            <p className="text-slate-400 dark:text-slate-500 text-sm p-5">{suche ? 'Keine Treffer.' : 'Noch keine Kunden.'}</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                <tr className="text-left">
                  <th className="px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400">Name / Firma</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400">Adresse</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400">E-Mail</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400">Kundennr.</th>
                  <th className="px-4 py-2.5 w-28"></th>
                </tr>
              </thead>
              <tbody>
                {gefiltert.map((k) => {
                  const isSelected = selected?.id === k.id
                  return (
                    <>
                      <tr
                        key={k.id}
                        onClick={() => setSelected(isSelected ? null : k)}
                        className={`border-b border-slate-100 dark:border-slate-700 cursor-pointer transition-colors ${
                          isSelected ? 'bg-blue-50 dark:bg-blue-950' : 'hover:bg-slate-50 dark:hover:bg-slate-700'
                        }`}
                      >
                        <td className={`px-4 py-2.5 font-medium ${isSelected ? 'text-blue-700 dark:text-blue-300' : 'text-slate-800 dark:text-slate-100'}`}>
                          <span className="mr-1 text-slate-400">{isSelected ? '▼' : '▶'}</span>
                          {kundeName(k)}
                        </td>
                        <td className="px-4 py-2.5 text-slate-500 dark:text-slate-400 text-xs">
                          {[k.strasse && k.hausnummer ? `${k.strasse} ${k.hausnummer}` : k.strasse, k.plz && k.ort ? `${k.plz} ${k.ort}` : k.ort].filter(Boolean).join(', ') || '—'}
                        </td>
                        <td className="px-4 py-2.5 text-slate-500 dark:text-slate-400">{k.email || '—'}</td>
                        <td className="px-4 py-2.5 text-slate-400 dark:text-slate-500 font-mono text-xs">{k.kundennummer || '—'}</td>
                        <td className="px-4 py-2.5">
                          <div className="flex gap-2 justify-end" onClick={(e) => e.stopPropagation()}>
                            <button onClick={() => openEdit(k)} className="text-xs text-blue-600 dark:text-blue-400 hover:underline">Bearbeiten</button>
                            <button onClick={() => handleDelete(k)} className="text-xs text-red-500 dark:text-red-400 hover:underline">Löschen</button>
                          </div>
                        </td>
                      </tr>
                      {isSelected && (
                        <tr key={`${k.id}-detail`} className="bg-blue-50 dark:bg-blue-950 border-b border-slate-200 dark:border-slate-700">
                          <td colSpan={5} className="px-6 py-4">
                            <div className="grid grid-cols-2 gap-x-8 gap-y-3 text-xs">
                              {(k.vorname || k.nachname) && (
                                <div>
                                  <span className="font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wide block mb-1">Name</span>
                                  <span className="text-slate-700 dark:text-slate-200">{[k.vorname, k.nachname].filter(Boolean).join(' ')}</span>
                                </div>
                              )}
                              {(k.strasse || k.ort) && (
                                <div>
                                  <span className="font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wide block mb-1">Adresse</span>
                                  <span className="text-slate-700 dark:text-slate-200">
                                    {[k.strasse, k.hausnummer].filter(Boolean).join(' ')}
                                    {(k.plz || k.ort) && <>, {[k.plz, k.ort].filter(Boolean).join(' ')}</>}
                                    {k.land && k.land !== 'DE' && <>, {k.land}</>}
                                  </span>
                                </div>
                              )}
                              {k.email && (
                                <div>
                                  <span className="font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wide block mb-1">E-Mail</span>
                                  <a href={`mailto:${k.email}`} className="text-blue-600 dark:text-blue-400 hover:underline break-all">{k.email}</a>
                                </div>
                              )}
                              {k.telefon && (
                                <div>
                                  <span className="font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wide block mb-1">Telefon</span>
                                  <a href={`tel:${k.telefon}`} className="text-blue-600 dark:text-blue-400 hover:underline">{k.telefon}</a>
                                </div>
                              )}
                              {k.ust_idnr && (
                                <div>
                                  <span className="font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wide block mb-1">USt-IdNr.</span>
                                  <span className="text-slate-700 dark:text-slate-200 font-mono">{k.ust_idnr}</span>
                                </div>
                              )}
                              {k.kundennummer && (
                                <div>
                                  <span className="font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wide block mb-1">Kundennr.</span>
                                  <span className="text-slate-700 dark:text-slate-200 font-mono">{k.kundennummer}</span>
                                </div>
                              )}
                              {k.z_hd && (
                                <div>
                                  <span className="font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wide block mb-1">z.Hd. von</span>
                                  <span className="text-slate-700 dark:text-slate-200">{k.z_hd}</span>
                                </div>
                              )}
                              {(k.ist_verein || k.ist_gemeinnuetzig || k.zugferd_aktiv) && (
                                <div>
                                  <span className="font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wide block mb-1">Eigenschaften</span>
                                  <div className="flex gap-1.5 flex-wrap">
                                    {k.ist_verein && <span className="px-1.5 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300">Verein</span>}
                                    {k.ist_gemeinnuetzig && <span className="px-1.5 py-0.5 rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300">Gemeinnützig</span>}
                                    {k.zugferd_aktiv && <span className="px-1.5 py-0.5 rounded-full bg-violet-100 dark:bg-violet-900 text-violet-700 dark:text-violet-300">ZUGFeRD</span>}
                                  </div>
                                </div>
                              )}
                              {k.notizen && (
                                <div className="col-span-2">
                                  <span className="font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wide block mb-1">Notizen</span>
                                  <p className="text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-700 px-2 py-1.5 whitespace-pre-wrap">{k.notizen}</p>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  )
                })}
              </tbody>
            </table>
          )}
          </div>
        </div>

      </div>

      {/* ── Rechte Spalte (Rechnungen oder Formular) ─────────────────── */}
      {!showForm && (
        <div className="w-96 shrink-0">
          {selected ? (
            <KundeRechnungen key={selected.id} kunde={selected} />
          ) : (
            <div className="flex items-center justify-center h-full text-slate-400 dark:text-slate-500 text-sm">
              Kunden auswählen
            </div>
          )}
        </div>
      )}

      {/* ── Formular-Panel ───────────────────────────────────────────── */}
      {showForm && (
        <div className="flex-1 border-l border-slate-200 dark:border-slate-700 overflow-y-auto">
          <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between shrink-0">
            <h3 className="font-semibold text-slate-800 dark:text-slate-100">
              {editKunde ? 'Kunde bearbeiten' : 'Neuer Kunde'}
            </h3>
            <button onClick={closeForm} className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-xl leading-none">×</button>
          </div>
          <div className="p-6 max-w-lg">
            {deleteFehlgeschlagen && (
              <div className="mb-4 bg-amber-50 dark:bg-amber-950 border border-amber-300 dark:border-amber-800 rounded-lg px-4 py-3 text-sm text-amber-800 dark:text-amber-300">
                <p className="font-medium">Löschen nicht möglich</p>
                <p className="mt-0.5">Dieser Kunde hat verknüpfte Buchungen oder Rechnungen. Verwende <strong>„Anonymisieren (Art. 17)"</strong>.</p>
              </div>
            )}
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Firmenname</label>
                  <input type="text" {...register('firmenname')} className={`w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 ${errors.firmenname ? 'border-red-400 dark:border-red-500' : 'border-slate-300 dark:border-slate-600'}`} />
                  {errors.firmenname && <p className="text-red-500 text-xs mt-0.5">{errors.firmenname.message}</p>}
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Vorname</label>
                  <input type="text" {...register('vorname')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Nachname</label>
                  <input type="text" {...register('nachname')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Adresse</label>
                  <div className="grid grid-cols-3 gap-2">
                    <input type="text" {...register('strasse')} placeholder="Straße" className={`col-span-2 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 ${errors.strasse ? 'border-red-400 dark:border-red-500' : 'border-slate-300 dark:border-slate-600'}`} />
                    <input type="text" {...register('hausnummer')} placeholder="Nr." className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                    <input type="text" {...register('plz')} placeholder="PLZ" className={`border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 ${errors.plz ? 'border-red-400 dark:border-red-500' : 'border-slate-300 dark:border-slate-600'}`} />
                    <input type="text" {...register('ort')} placeholder="Ort" className={`col-span-2 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100 ${errors.ort ? 'border-red-400 dark:border-red-500' : 'border-slate-300 dark:border-slate-600'}`} />
                    <input type="text" {...register('land')} placeholder="Land (z.B. DE)" className="col-span-3 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                  </div>
                  {(errors.strasse || errors.plz || errors.ort) && (
                    <p className="text-red-500 text-xs mt-0.5">Straße, PLZ und Ort sind für ZUGFeRD Pflichtfelder</p>
                  )}
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">E-Mail</label>
                  <input type="email" {...register('email')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                  {errors.email && <p className="text-red-500 text-xs mt-0.5">{errors.email.message}</p>}
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Telefon</label>
                  <input type="text" {...register('telefon')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Kundennummer</label>
                  <input type="text" {...register('kundennummer')} placeholder="Wird automatisch vergeben" className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">USt-IdNr.</label>
                  <input type="text" {...register('ust_idnr')} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">z.Hd. von</label>
                  <input type="text" {...register('z_hd')} placeholder="z.B. Max Mustermann oder Buchhaltung" className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Notizen</label>
                  <textarea {...register('notizen')} rows={2} className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Skonto (kundenspezifisch)</label>
                  <div className="flex items-center gap-2">
                    <input type="number" min={0} max={100} step={0.5} {...register('skonto_prozent', { setValueAs: v => v === '' || v == null ? null : parseFloat(v) })} placeholder="z. B. 2" className="w-20 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                    <span className="text-sm text-slate-500 dark:text-slate-400">%  bei Zahlung innerhalb von</span>
                    <input type="number" min={1} max={365} {...register('skonto_tage', { setValueAs: v => v === '' || v == null ? null : parseInt(v) })} placeholder="z. B. 10" className="w-20 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:text-slate-100" />
                    <span className="text-sm text-slate-500 dark:text-slate-400">Tagen  (leer = Standard aus Unternehmen)</span>
                  </div>
                </div>
                <div className="col-span-2 flex gap-4">
                  <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 cursor-pointer">
                    <input type="checkbox" {...register('ist_verein')} className="rounded" /> Verein
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 cursor-pointer">
                    <input type="checkbox" {...register('ist_gemeinnuetzig')} className="rounded" /> Gemeinnützig
                  </label>
                </div>
                <div className="col-span-2">
                  <label className={`flex items-start gap-2 text-sm cursor-pointer ${zugferdAutoAktiv ? 'text-slate-400 dark:text-slate-500' : 'text-slate-600 dark:text-slate-300'}`}>
                    <input
                      type="checkbox"
                      className="rounded mt-0.5"
                      disabled={zugferdAutoAktiv}
                      checked={zugferdAutoAktiv || undefined}
                      {...(!zugferdAutoAktiv ? register('zugferd_aktiv') : {})}
                      onChange={zugferdAutoAktiv ? undefined : (e) => setValue('zugferd_aktiv', e.target.checked)}
                    />
                    <span>
                      ZUGFeRD / E-Rechnung
                      {zugferdAutoAktiv
                        ? <span className="ml-1 text-xs text-blue-500 dark:text-blue-400">(automatisch aktiv – Firma + USt-IdNr. vorhanden)</span>
                        : <span className="ml-1 text-xs text-slate-400 dark:text-slate-500">PDF enthält maschinenlesbares XML für B2B-Empfänger</span>
                      }
                    </span>
                  </label>
                  {zugferdOhneUstId && (
                    <p className="text-amber-600 dark:text-amber-400 text-xs mt-1 ml-6">
                      Hinweis: Ohne USt-IdNr. oder Steuernummer ist das ZUGFeRD-XML steuerlich unvollständig.
                    </p>
                  )}
                </div>
              </div>

              {mutationError && <p className="text-red-600 text-sm">{(mutationError as Error).message}</p>}

              {/* Lieferadressen – nur bei bestehendem Kunden */}
              {editKunde?.id && (
                <div className="border-t border-slate-200 dark:border-slate-700 pt-3">
                  <KundeLieferadressen kundeId={editKunde.id} />
                </div>
              )}


              <div className="flex gap-3 pt-2">
                <button type="button" onClick={closeForm} className="flex-1 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-700">Abbrechen</button>
                <button type="submit" disabled={isPending} className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
                  {isPending ? 'Speichert…' : 'Speichern'}
                </button>
              </div>

              {editKunde?.id && !anonymisierungResult && (
                <div className="border-t border-slate-200 dark:border-slate-700 pt-3 space-y-2">
                  <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide">Datenschutz (DSGVO)</p>
                  {!showDsgvoBestaetigung ? (
                    <div className="flex gap-2">
                      <button type="button" onClick={() => dsgvoExportKundePdf(editKunde.id!)}
                        className="flex-1 text-xs border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg py-1.5 hover:bg-slate-50 dark:hover:bg-slate-700">
                        📄 Datenauskunft (PDF)
                      </button>
                      <button type="button" onClick={() => dsgvoExportKunde(editKunde.id!)}
                        className="flex-1 text-xs border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg py-1.5 hover:bg-slate-50 dark:hover:bg-slate-700">
                        📥 Datenauskunft (JSON)
                      </button>
                      <button type="button" onClick={() => setShowDsgvoBestaetigung(true)}
                        className="flex-1 text-xs border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 rounded-lg py-1.5 hover:bg-red-50 dark:hover:bg-red-950">
                        🗑 Anonymisieren (Art. 17)
                      </button>
                    </div>
                  ) : (
                    <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg p-3 space-y-2">
                      <p className="text-sm font-medium text-red-800 dark:text-red-300">Kunden wirklich anonymisieren?</p>
                      <ul className="text-xs text-red-700 dark:text-red-400 space-y-0.5 list-disc list-inside">
                        <li>Kundenstammdaten werden dauerhaft gelöscht</li>
                        <li>Verknüpfungen in Buchungen und Rechnungen werden entfernt</li>
                        <li>Immutable Journaleinträge bleiben erhalten (§147 AO)</li>
                      </ul>
                      {anonymisierungMutation.isError && (
                        <p className="text-xs text-red-600 dark:text-red-400">{(anonymisierungMutation.error as Error).message}</p>
                      )}
                      <div className="flex gap-2 pt-1">
                        <button type="button" onClick={() => anonymisierungMutation.mutate(editKunde.id!)}
                          disabled={anonymisierungMutation.isPending}
                          className="flex-1 bg-red-600 text-white rounded-lg py-1.5 text-xs font-medium hover:bg-red-700 disabled:opacity-50">
                          {anonymisierungMutation.isPending ? '…' : 'Jetzt anonymisieren'}
                        </button>
                        <button type="button" onClick={() => setShowDsgvoBestaetigung(false)}
                          className="flex-1 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg py-1.5 text-xs hover:bg-slate-50 dark:hover:bg-slate-700">
                          Abbrechen
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {anonymisierungResult && (
                <div className="border-t border-slate-200 dark:border-slate-700 pt-3">
                  <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg p-3 space-y-1">
                    <p className="text-sm font-medium text-green-800 dark:text-green-300">Anonymisierung abgeschlossen</p>
                    <p className="text-xs text-green-700 dark:text-green-400">
                      {anonymisierungResult.anonymisierte_buchungen} Buchung(en) und {anonymisierungResult.anonymisierte_rechnungen} Rechnung(en) anonymisiert.
                    </p>
                    {anonymisierungResult.unveraenderlich_verblieben > 0 && (
                      <p className="text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded px-2 py-1 mt-1">
                        ⚠ {anonymisierungResult.hinweis}
                      </p>
                    )}
                  </div>
                  <button type="button" onClick={closeForm}
                    className="w-full mt-2 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-700">
                    Schließen
                  </button>
                </div>
              )}
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
