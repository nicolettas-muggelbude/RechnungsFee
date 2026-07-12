import { useAnsicht, useMxAuto, type AnsichtEinstellungen } from '../../hooks/useAnsicht'

function OptionCard({
  aktiv,
  onClick,
  titel,
  beschreibung,
}: {
  aktiv: boolean
  onClick: () => void
  titel: string
  beschreibung: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full text-left px-4 py-3 rounded-xl border-2 transition-colors ${
        aktiv
          ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950 dark:border-indigo-400'
          : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
      }`}
    >
      <div className="flex items-center gap-3">
        <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0 ${
          aktiv ? 'border-indigo-500 dark:border-indigo-400' : 'border-slate-300 dark:border-slate-600'
        }`}>
          {aktiv && <div className="w-2 h-2 rounded-full bg-indigo-500 dark:bg-indigo-400" />}
        </div>
        <div>
          <p className={`text-sm font-medium ${aktiv ? 'text-indigo-700 dark:text-indigo-300' : 'text-slate-800 dark:text-slate-100'}`}>{titel}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{beschreibung}</p>
        </div>
      </div>
    </button>
  )
}

export function AnsichtPage() {
  const { einstellungen, setEinstellungen } = useAnsicht()
  const mxAuto = useMxAuto()

  function set(patch: Partial<AnsichtEinstellungen>) {
    setEinstellungen({ ...einstellungen, ...patch })
  }

  return (
    <div className={`p-6 max-w-2xl ${mxAuto} space-y-8`}>
      <div>
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">Ansicht</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">Einstellungen werden sofort übernommen und pro Gerät gespeichert.</p>
      </div>

      {/* Farbschema */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide">Farbschema</h2>
        <div className="space-y-2">
          <OptionCard
            aktiv={einstellungen.farbschema === 'system'}
            onClick={() => set({ farbschema: 'system' })}
            titel="Systemeinstellung (Standard)"
            beschreibung="Folgt automatisch der Hell/Dunkel-Einstellung des Betriebssystems."
          />
          <OptionCard
            aktiv={einstellungen.farbschema === 'hell'}
            onClick={() => set({ farbschema: 'hell' })}
            titel="Hell"
            beschreibung="Immer helles Design, unabhängig von der Systemeinstellung."
          />
          <OptionCard
            aktiv={einstellungen.farbschema === 'dunkel'}
            onClick={() => set({ farbschema: 'dunkel' })}
            titel="Dunkel"
            beschreibung="Immer dunkles Design, unabhängig von der Systemeinstellung."
          />
        </div>
      </section>

      {/* Inhaltsausrichtung */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide">Inhaltsausrichtung</h2>
        <div className="space-y-2">
          <OptionCard
            aktiv={einstellungen.ausrichtung === 'links'}
            onClick={() => set({ ausrichtung: 'links' })}
            titel="Linksbündig (Standard)"
            beschreibung="Inhalt beginnt am linken Rand – nutzt die gesamte verfügbare Breite."
          />
          <OptionCard
            aktiv={einstellungen.ausrichtung === 'zentriert'}
            onClick={() => set({ ausrichtung: 'zentriert' })}
            titel="Zentriert"
            beschreibung="Inhalt ist auf max. 1400 px begrenzt und auf breiten Bildschirmen zentriert."
          />
        </div>
      </section>

      {/* Spaltenbreite */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide">Spaltenbreite (Listen mit Detail-Panel)</h2>
        <div className="space-y-2">
          <OptionCard
            aktiv={einstellungen.splitter === 'auto'}
            onClick={() => set({ splitter: 'auto' })}
            titel="Automatisch (Standard)"
            beschreibung="Die Listen-Spalte nimmt 1/3 der Breite ein, das Detail-Panel den Rest."
          />
          <OptionCard
            aktiv={einstellungen.splitter === 'manuell'}
            onClick={() => set({ splitter: 'manuell' })}
            titel="Manuell verschiebbar"
            beschreibung="Die Trennlinie zwischen Liste und Detail lässt sich per Maus ziehen. Die Breite wird pro Seite gespeichert."
          />
        </div>
      </section>
    </div>
  )
}
