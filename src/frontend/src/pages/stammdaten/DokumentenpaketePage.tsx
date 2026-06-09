import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getDokumentenPakete, createDokumentenPaket, updateDokumentenPaket, deleteDokumentenPaket,
  uploadPaketDatei, updatePaketDatei, deletePaketDatei, getPaketDateiUrl,
  type DokumentenPaket, type PaketDatei,
} from '../../api/client'
import { openUrl } from '../../api/client'

const inputCls = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-100 dark:placeholder-slate-400"

// ---------------------------------------------------------------------------
// Datei-Zeile innerhalb einer Gruppe
// ---------------------------------------------------------------------------

function DateiZeile({ paket, datei }: { paket: DokumentenPaket; datei: PaketDatei }) {
  const qc = useQueryClient()
  const [editBez, setEditBez] = useState(false)
  const [bez, setBez] = useState(datei.bezeichnung ?? '')

  const updateMut = useMutation({
    mutationFn: () => updatePaketDatei(paket.id, datei.id, { bezeichnung: bez.trim() || undefined }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['dokumentenpakete'] }); setEditBez(false) },
  })

  const deleteMut = useMutation({
    mutationFn: () => deletePaketDatei(paket.id, datei.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dokumentenpakete'] }),
  })

  async function handleOpen() {
    const url = await getPaketDateiUrl(paket.id, datei.id)
    openUrl(url)
  }

  const groesse = datei.dateigroesse
    ? datei.dateigroesse > 1024 * 1024
      ? `${(datei.dateigroesse / 1024 / 1024).toFixed(1)} MB`
      : `${Math.round(datei.dateigroesse / 1024)} KB`
    : null

  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-slate-100 dark:border-slate-700 last:border-0">
      <span className="text-slate-400 text-base flex-shrink-0">
        {datei.mime_type === 'application/pdf' ? '📄' : '🖼️'}
      </span>

      <div className="flex-1 min-w-0">
        {editBez ? (
          <div className="flex gap-2 items-center">
            <input
              type="text"
              value={bez}
              onChange={e => setBez(e.target.value)}
              className="flex-1 rounded border border-slate-300 dark:border-slate-600 px-2 py-1 text-xs dark:bg-slate-700 dark:text-slate-100"
              autoFocus
              onKeyDown={e => { if (e.key === 'Enter') updateMut.mutate(); if (e.key === 'Escape') setEditBez(false) }}
            />
            <button onClick={() => updateMut.mutate()} className="text-xs text-blue-600 hover:underline">OK</button>
            <button onClick={() => setEditBez(false)} className="text-xs text-slate-400 hover:underline">Abbruch</button>
          </div>
        ) : (
          <div className="flex items-baseline gap-2">
            <span className="text-sm font-medium text-slate-800 dark:text-slate-100 truncate">
              {datei.bezeichnung || datei.original_name}
            </span>
            {datei.bezeichnung && (
              <span className="text-xs text-slate-400 dark:text-slate-500 truncate hidden sm:inline">
                {datei.original_name}
              </span>
            )}
            {groesse && <span className="text-xs text-slate-400 flex-shrink-0">{groesse}</span>}
          </div>
        )}
      </div>

      <div className="flex gap-1 flex-shrink-0">
        <button onClick={handleOpen}
          title="Öffnen"
          className="p-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
        </button>
        <button onClick={() => { setBez(datei.bezeichnung ?? ''); setEditBez(true) }}
          title="Umbenennen"
          className="p-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
        </button>
        <button onClick={() => { if (confirm(`„${datei.bezeichnung || datei.original_name}" entfernen?`)) deleteMut.mutate() }}
          title="Entfernen"
          className="p-1.5 text-red-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 rounded">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Dokument-Upload innerhalb einer Gruppe
// ---------------------------------------------------------------------------

function DokumentHinzufuegen({ paket }: { paket: DokumentenPaket }) {
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [bezeichnung, setBezeichnung] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)
  const [offen, setOffen] = useState(false)

  const uploadMut = useMutation({
    mutationFn: ({ file, bez }: { file: File; bez: string }) =>
      uploadPaketDatei(paket.id, file, bez || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['dokumentenpakete'] })
      setBezeichnung('')
      setFehler(null)
      setOffen(false)
      if (fileRef.current) fileRef.current.value = ''
    },
    onError: (e: Error) => setFehler(e.message),
  })

  function handleDatei(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    uploadMut.mutate({ file, bez: bezeichnung })
  }

  if (!offen) {
    return (
      <button
        onClick={() => setOffen(true)}
        className="mt-2 flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
        Dokument hinzufügen
      </button>
    )
  }

  return (
    <div className="mt-3 p-3 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 space-y-3">
      <div className="flex gap-2 items-end flex-wrap">
        <div className="flex-1 min-w-36">
          <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Bezeichnung <span className="text-slate-400">(optional, z.B. AGB)</span></label>
          <input
            type="text"
            value={bezeichnung}
            onChange={e => setBezeichnung(e.target.value)}
            placeholder="z.B. AGB, Datenschutzerklärung"
            className={inputCls}
          />
        </div>
        <div className="flex gap-2">
          <input ref={fileRef} type="file" accept=".pdf,.jpg,.jpeg,.png" className="hidden" onChange={handleDatei} />
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={uploadMut.isPending}
            className="px-3 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50 whitespace-nowrap"
          >
            {uploadMut.isPending ? 'Hochladen…' : 'PDF auswählen'}
          </button>
          <button type="button" onClick={() => setOffen(false)}
            className="px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
            Abbrechen
          </button>
        </div>
      </div>
      {fehler && <p className="text-xs text-red-600">{fehler}</p>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Gruppen-Karte
// ---------------------------------------------------------------------------

function GruppenKarte({ paket }: { paket: DokumentenPaket }) {
  const qc = useQueryClient()
  const [editModus, setEditModus] = useState(false)
  const [name, setName] = useState(paket.name)
  const [beschreibung, setBeschreibung] = useState(paket.beschreibung ?? '')

  const updateMut = useMutation({
    mutationFn: () => updateDokumentenPaket(paket.id, { name: name.trim(), beschreibung: beschreibung.trim() || undefined }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['dokumentenpakete'] }); setEditModus(false) },
  })

  const toggleMut = useMutation({
    mutationFn: () => updateDokumentenPaket(paket.id, { aktiv: !paket.aktiv }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dokumentenpakete'] }),
  })

  const [deleteError, setDeleteError] = useState<string | null>(null)
  const deleteMut = useMutation({
    mutationFn: () => deleteDokumentenPaket(paket.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['dokumentenpakete'] }); setDeleteError(null) },
    onError: (e: Error) => setDeleteError(e.message),
  })

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-2xl border shadow-sm transition-opacity ${
      paket.aktiv ? 'border-slate-200 dark:border-slate-700' : 'border-slate-100 dark:border-slate-800 opacity-60'
    }`}>
      {/* Gruppen-Header */}
      <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700">
        {editModus ? (
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Gruppenname</label>
              <input type="text" value={name} onChange={e => setName(e.target.value)}
                className={inputCls} autoFocus />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Beschreibung</label>
              <input type="text" value={beschreibung} onChange={e => setBeschreibung(e.target.value)}
                placeholder="z.B. Für alle B2B-Geschäftskunden"
                className={inputCls} />
            </div>
            <div className="flex gap-2">
              <button onClick={() => updateMut.mutate()} disabled={!name.trim() || updateMut.isPending}
                className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                Speichern
              </button>
              <button onClick={() => setEditModus(false)}
                className="px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                Abbrechen
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="font-semibold text-slate-800 dark:text-slate-100 text-base">{paket.name}</h3>
                {!paket.aktiv && (
                  <span className="text-[11px] bg-slate-100 dark:bg-slate-700 text-slate-500 rounded px-1.5 py-0.5">Inaktiv</span>
                )}
                <span className="text-xs text-slate-400 dark:text-slate-500">
                  {paket.dateien.length === 0 ? 'Noch keine Dokumente' : `${paket.dateien.length} Dokument${paket.dateien.length !== 1 ? 'e' : ''}`}
                </span>
              </div>
              {paket.beschreibung && (
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{paket.beschreibung}</p>
              )}
            </div>
            <div className="flex gap-1 flex-shrink-0">
              <button onClick={() => setEditModus(true)}
                className="px-2.5 py-1.5 text-xs text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100 border border-slate-200 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700">
                Umbenennen
              </button>
              <button onClick={() => toggleMut.mutate()} disabled={toggleMut.isPending}
                className="px-2.5 py-1.5 text-xs text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100 border border-slate-200 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50">
                {paket.aktiv ? 'Deaktivieren' : 'Aktivieren'}
              </button>
              <button
                onClick={() => { if (confirm(`Gruppe „${paket.name}" und alle Dokumente darin löschen?`)) deleteMut.mutate() }}
                disabled={deleteMut.isPending}
                className="px-2.5 py-1.5 text-xs text-red-500 hover:text-red-700 border border-red-200 dark:border-red-800 rounded-lg hover:bg-red-50 dark:hover:bg-red-950 disabled:opacity-50">
                Löschen
              </button>
            </div>
          </div>
        )}
      </div>

      {deleteError && (
        <div className="px-5 py-2 bg-red-50 dark:bg-red-950 border-b border-red-100 dark:border-red-900 text-sm text-red-600 dark:text-red-400">
          {deleteError}
        </div>
      )}

      {/* Dokumente innerhalb der Gruppe */}
      <div className="px-5 py-3">
        {paket.dateien.length === 0 ? (
          <p className="text-sm text-slate-400 dark:text-slate-500 italic py-1">Noch keine Dokumente in dieser Gruppe.</p>
        ) : (
          <div>
            {paket.dateien.map(d => <DateiZeile key={d.id} paket={paket} datei={d} />)}
          </div>
        )}
        <DokumentHinzufuegen paket={paket} />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Haupt-Seite
// ---------------------------------------------------------------------------

export function DokumentenpaketePage() {
  const qc = useQueryClient()
  const [zeigeNeuForm, setZeigeNeuForm] = useState(false)
  const [neuName, setNeuName] = useState('')
  const [neuBeschreibung, setNeuBeschreibung] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)

  const { data: pakete, isLoading } = useQuery({
    queryKey: ['dokumentenpakete'],
    queryFn: getDokumentenPakete,
  })

  const createMut = useMutation({
    mutationFn: () => createDokumentenPaket({ name: neuName.trim(), beschreibung: neuBeschreibung.trim() || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['dokumentenpakete'] })
      setZeigeNeuForm(false)
      setNeuName('')
      setNeuBeschreibung('')
      setFehler(null)
    },
    onError: (e: Error) => setFehler(e.message),
  })

  return (
    <div className="p-6 max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">Dokumentenpakete</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm">
          Gruppen von Anhängen für Angebote und Auftragsbestätigungen – z.B. Gruppe „B2B" mit AGB, Datenschutzerklärung und Leistungsverzeichnis.
        </p>
      </div>

      {/* Neue Gruppe anlegen */}
      {zeigeNeuForm ? (
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-blue-200 dark:border-blue-800 shadow-sm p-5 space-y-4">
          <h2 className="font-semibold text-slate-800 dark:text-slate-100">Neue Gruppe anlegen</h2>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Gruppenname *</label>
            <input
              type="text"
              value={neuName}
              onChange={e => setNeuName(e.target.value)}
              placeholder="z.B. B2B-Kunden, Privatkunden, EU-Ausland"
              className={inputCls}
              autoFocus
              onKeyDown={e => { if (e.key === 'Enter' && neuName.trim()) createMut.mutate() }}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Beschreibung</label>
            <input
              type="text"
              value={neuBeschreibung}
              onChange={e => setNeuBeschreibung(e.target.value)}
              placeholder="z.B. Für alle B2B-Geschäftskunden mit vollständigem Vertragswerk"
              className={inputCls}
            />
          </div>
          {fehler && <p className="text-sm text-red-600">{fehler}</p>}
          <div className="flex gap-2">
            <button
              onClick={() => createMut.mutate()}
              disabled={!neuName.trim() || createMut.isPending}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg disabled:opacity-50"
            >
              {createMut.isPending ? 'Anlegen…' : 'Gruppe anlegen'}
            </button>
            <button onClick={() => { setZeigeNeuForm(false); setFehler(null) }}
              className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
              Abbrechen
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setZeigeNeuForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
          Neue Gruppe anlegen
        </button>
      )}

      {/* Gruppen-Liste */}
      {isLoading ? (
        <div className="animate-pulse space-y-3">
          {[1, 2].map(i => <div key={i} className="h-32 bg-slate-100 dark:bg-slate-800 rounded-2xl" />)}
        </div>
      ) : pakete?.length === 0 ? (
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-10 text-center space-y-2">
          <p className="text-slate-600 dark:text-slate-300 font-medium">Noch keine Gruppen angelegt</p>
          <p className="text-slate-400 dark:text-slate-500 text-sm">
            Lege z.B. eine Gruppe „B2B" an und füge AGB, Datenschutzerklärung und Leistungsverzeichnis hinzu.
            Diese Gruppe kannst du später bei Angeboten und Auftragsbestätigungen auswählen.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {pakete?.map(p => <GruppenKarte key={p.id} paket={p} />)}
        </div>
      )}
    </div>
  )
}
