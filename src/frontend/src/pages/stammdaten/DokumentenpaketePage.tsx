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
// Paket-Formular (erstellen / umbenennen)
// ---------------------------------------------------------------------------

function PaketFormular({
  initial,
  onSpeichern,
  onAbbrechen,
}: {
  initial?: DokumentenPaket
  onSpeichern: (name: string, beschreibung: string) => void
  onAbbrechen: () => void
}) {
  const [name, setName] = useState(initial?.name ?? '')
  const [beschreibung, setBeschreibung] = useState(initial?.beschreibung ?? '')

  function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    onSpeichern(name.trim(), beschreibung.trim())
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Name *</label>
        <input
          type="text"
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="z.B. Standard B2B"
          className={inputCls}
          autoFocus
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Beschreibung</label>
        <textarea
          value={beschreibung}
          onChange={e => setBeschreibung(e.target.value)}
          rows={2}
          placeholder="z.B. AGB, Datenschutzerklärung, Leistungsverzeichnis für B2B-Kunden"
          className={`${inputCls} resize-none`}
        />
      </div>
      <div className="flex gap-2 justify-end">
        <button type="button" onClick={onAbbrechen}
          className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300">
          Abbrechen
        </button>
        <button type="submit" disabled={!name.trim()}
          className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50">
          {initial ? 'Speichern' : 'Paket erstellen'}
        </button>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Datei-Upload-Bereich in einem Paket
// ---------------------------------------------------------------------------

function DateiUploadBereich({ paket }: { paket: DokumentenPaket }) {
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [bezeichnung, setBezeichnung] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)

  const uploadMut = useMutation({
    mutationFn: ({ file, bez }: { file: File; bez: string }) =>
      uploadPaketDatei(paket.id, file, bez || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['dokumentenpakete'] })
      setBezeichnung('')
      setFehler(null)
      if (fileRef.current) fileRef.current.value = ''
    },
    onError: (e: Error) => setFehler(e.message),
  })

  function handleDatei(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    uploadMut.mutate({ file, bez: bezeichnung })
  }

  return (
    <div className="border-t border-slate-100 dark:border-slate-700 pt-4 space-y-3">
      <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Datei hinzufügen</p>
      <div className="flex gap-2 items-end flex-wrap">
        <div className="flex-1 min-w-40">
          <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Bezeichnung (optional)</label>
          <input
            type="text"
            value={bezeichnung}
            onChange={e => setBezeichnung(e.target.value)}
            placeholder="z.B. AGB"
            className={inputCls}
          />
        </div>
        <div>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            className="hidden"
            onChange={handleDatei}
          />
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={uploadMut.isPending}
            className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 disabled:opacity-50 whitespace-nowrap"
          >
            {uploadMut.isPending ? 'Hochladen…' : 'PDF / Bild hochladen'}
          </button>
        </div>
      </div>
      {fehler && <p className="text-xs text-red-600">{fehler}</p>}
      <p className="text-xs text-slate-400 dark:text-slate-500">PDF, JPEG oder PNG · max. Dateigröße abhängig vom System</p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Einzelne Datei in einem Paket
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
    <div className="flex items-center gap-3 py-2 border-b border-slate-50 dark:border-slate-700 last:border-0">
      <span className="text-slate-400 text-lg flex-shrink-0">
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
            <button onClick={() => updateMut.mutate()} disabled={updateMut.isPending}
              className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400">
              OK
            </button>
            <button onClick={() => setEditBez(false)} className="text-xs text-slate-400 hover:text-slate-600">Abbruch</button>
          </div>
        ) : (
          <>
            <p className="text-sm text-slate-800 dark:text-slate-100 truncate">
              {datei.bezeichnung
                ? <><span className="font-medium">{datei.bezeichnung}</span> <span className="text-slate-400 text-xs">– {datei.original_name}</span></>
                : datei.original_name
              }
            </p>
            {groesse && <p className="text-xs text-slate-400">{groesse}</p>}
          </>
        )}
      </div>

      <div className="flex gap-1 flex-shrink-0">
        <button onClick={handleOpen}
          className="px-2 py-1 text-xs text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100 border border-slate-200 dark:border-slate-600 rounded hover:bg-slate-50 dark:hover:bg-slate-700">
          Öffnen
        </button>
        <button onClick={() => { setBez(datei.bezeichnung ?? ''); setEditBez(true) }}
          className="px-2 py-1 text-xs text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100 border border-slate-200 dark:border-slate-600 rounded hover:bg-slate-50 dark:hover:bg-slate-700">
          Umbenennen
        </button>
        <button onClick={() => deleteMut.mutate()} disabled={deleteMut.isPending}
          className="px-2 py-1 text-xs text-red-500 hover:text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800 rounded hover:bg-red-50 dark:hover:bg-red-950 disabled:opacity-50">
          Entfernen
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Paket-Karte
// ---------------------------------------------------------------------------

function PaketKarte({ paket }: { paket: DokumentenPaket }) {
  const qc = useQueryClient()
  const [editModus, setEditModus] = useState(false)
  const [offen, setOffen] = useState(false)

  const updateMut = useMutation({
    mutationFn: (d: { name: string; beschreibung: string }) =>
      updateDokumentenPaket(paket.id, { name: d.name, beschreibung: d.beschreibung || undefined }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['dokumentenpakete'] }); setEditModus(false) },
  })

  const toggleMut = useMutation({
    mutationFn: () => updateDokumentenPaket(paket.id, { aktiv: !paket.aktiv }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dokumentenpakete'] }),
  })

  const deleteMut = useMutation({
    mutationFn: () => deleteDokumentenPaket(paket.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dokumentenpakete'] }),
    onError: (e: Error) => alert(e.message),
  })

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-2xl border shadow-sm overflow-hidden transition-opacity ${paket.aktiv ? 'border-slate-200 dark:border-slate-700' : 'border-slate-100 dark:border-slate-800 opacity-60'}`}>
      {/* Header */}
      <div className="px-5 py-4 flex items-start gap-3">
        <div className="flex-1 min-w-0">
          {editModus ? (
            <PaketFormular
              initial={paket}
              onSpeichern={(name, beschreibung) => updateMut.mutate({ name, beschreibung })}
              onAbbrechen={() => setEditModus(false)}
            />
          ) : (
            <>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-slate-800 dark:text-slate-100">{paket.name}</h3>
                {!paket.aktiv && (
                  <span className="text-xs bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 rounded px-1.5 py-0.5">Inaktiv</span>
                )}
                <span className="text-xs text-slate-400 dark:text-slate-500">
                  {paket.dateien.length} {paket.dateien.length === 1 ? 'Datei' : 'Dateien'}
                </span>
              </div>
              {paket.beschreibung && (
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{paket.beschreibung}</p>
              )}
            </>
          )}
        </div>

        {!editModus && (
          <div className="flex gap-1 flex-shrink-0">
            <button
              onClick={() => setOffen(o => !o)}
              className="px-3 py-1.5 text-sm text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100 border border-slate-200 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700"
            >
              {offen ? 'Schließen' : 'Dateien'}
            </button>
            <button onClick={() => setEditModus(true)}
              className="px-3 py-1.5 text-sm text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100 border border-slate-200 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700">
              Bearbeiten
            </button>
            <button onClick={() => toggleMut.mutate()} disabled={toggleMut.isPending}
              className="px-3 py-1.5 text-sm text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100 border border-slate-200 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50">
              {paket.aktiv ? 'Deaktivieren' : 'Aktivieren'}
            </button>
            <button
              onClick={() => {
                if (window.confirm(`Paket „${paket.name}" und alle darin enthaltenen Dateien löschen?`))
                  deleteMut.mutate()
              }}
              disabled={deleteMut.isPending}
              className="px-3 py-1.5 text-sm text-red-500 hover:text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800 rounded-lg hover:bg-red-50 dark:hover:bg-red-950 disabled:opacity-50"
            >
              Löschen
            </button>
          </div>
        )}
      </div>

      {/* Dateiliste */}
      {offen && !editModus && (
        <div className="px-5 pb-4 border-t border-slate-100 dark:border-slate-700 pt-3 space-y-0">
          {paket.dateien.length === 0 ? (
            <p className="text-sm text-slate-400 dark:text-slate-500 italic py-2">Noch keine Dateien in diesem Paket.</p>
          ) : (
            paket.dateien.map(d => <DateiZeile key={d.id} paket={paket} datei={d} />)
          )}
          <DateiUploadBereich paket={paket} />
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Haupt-Seite
// ---------------------------------------------------------------------------

export function DokumentenpaketePage() {
  const qc = useQueryClient()
  const [zeigeNeuForm, setZeigeNeuForm] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)

  const { data: pakete, isLoading } = useQuery({
    queryKey: ['dokumentenpakete'],
    queryFn: getDokumentenPakete,
  })

  const createMut = useMutation({
    mutationFn: (d: { name: string; beschreibung?: string }) => createDokumentenPaket(d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['dokumentenpakete'] })
      setZeigeNeuForm(false)
      setFehler(null)
    },
    onError: (e: Error) => setFehler(e.message),
  })

  return (
    <div className="p-6 max-w-4xl space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">Dokumentenpakete</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            Wiederverwendbare Anhang-Gruppen für Angebote und Auftragsbestätigungen – z.B. AGB, Datenschutzerklärung, Leistungsverzeichnis.
          </p>
        </div>
        {!zeigeNeuForm && (
          <button
            onClick={() => setZeigeNeuForm(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg shrink-0"
          >
            + Neues Paket
          </button>
        )}
      </div>

      {zeigeNeuForm && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm p-5">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4">Neues Dokumentenpaket</h2>
          {fehler && <p className="text-sm text-red-600 mb-3">{fehler}</p>}
          <PaketFormular
            onSpeichern={(name, beschreibung) => createMut.mutate({ name, beschreibung: beschreibung || undefined })}
            onAbbrechen={() => { setZeigeNeuForm(false); setFehler(null) }}
          />
        </div>
      )}

      {isLoading ? (
        <div className="animate-pulse space-y-3">
          {[1, 2].map(i => <div key={i} className="h-20 bg-slate-100 dark:bg-slate-800 rounded-2xl" />)}
        </div>
      ) : pakete?.length === 0 ? (
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-10 text-center">
          <p className="text-slate-400 dark:text-slate-500 text-sm">Noch keine Dokumentenpakete angelegt.</p>
          <p className="text-slate-400 dark:text-slate-500 text-xs mt-1">
            Erstelle ein Paket mit AGB, Datenschutzerklärung o.ä. – es wird später an Angebote und Auftragsbestätigungen angehängt.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {pakete?.map(p => <PaketKarte key={p.id} paket={p} />)}
        </div>
      )}
    </div>
  )
}
