import { Fragment, useState } from 'react'

type ExportFormat = 'pdf' | 'csv'

interface ExportButtonsProps {
  onExport: (format: ExportFormat) => void | Promise<void>
  formats?: ExportFormat[]
  className?: string
}

/** Einheitlicher Export-Button (Pillenbutton), z. B. "📄 PDF | CSV". Issue #259. */
export function ExportButtons({ onExport, formats = ['pdf', 'csv'], className }: ExportButtonsProps) {
  const [laedt, setLaedt] = useState(false)

  async function handle(format: ExportFormat) {
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
            title={`Als ${format.toUpperCase()} exportieren`}
            className="px-3 py-2 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
          >
            {format === 'pdf' ? `${laedt ? '⏳' : '📄'} PDF` : 'CSV'}
          </button>
        </Fragment>
      ))}
    </div>
  )
}
