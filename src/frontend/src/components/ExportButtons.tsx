import { Fragment, useState } from 'react'

type ExportFormat = 'pdf' | 'csv' | 'xml' | 'elster-csv'

const LABEL: Record<ExportFormat, string> = { pdf: 'PDF', csv: 'CSV', xml: 'ELSTER-XML', 'elster-csv': 'ELSTER-CSV' }

interface ExportButtonsProps<F extends ExportFormat = ExportFormat> {
  onExport: (format: F) => void | Promise<void>
  formats?: F[]
  className?: string
}

/** Einheitlicher Export-Button (Pillenbutton), z. B. "📄 PDF | CSV". Issue #259. */
export function ExportButtons<F extends ExportFormat = ExportFormat>({ onExport, formats = ['pdf', 'csv'] as F[], className }: ExportButtonsProps<F>) {
  const [laedt, setLaedt] = useState(false)

  async function handle(format: F) {
    setLaedt(true)
    try {
      await onExport(format)
    } finally {
      setLaedt(false)
    }
  }

  return (
    <div className={`flex rounded-lg overflow-hidden border border-slate-300 dark:border-slate-600 ${className ?? ''}`}>
      {formats.map((format, i) => (
        <Fragment key={format}>
          {i > 0 && <div className="w-px bg-slate-300 dark:bg-slate-600" />}
          <button
            type="button"
            onClick={() => handle(format)}
            disabled={laedt}
            title={`Als ${LABEL[format]} exportieren`}
            className="px-3 py-2 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
          >
            {format === 'pdf' ? `${laedt ? '⏳' : '📄'} ` : ''}{LABEL[format]}
          </button>
        </Fragment>
      ))}
    </div>
  )
}
