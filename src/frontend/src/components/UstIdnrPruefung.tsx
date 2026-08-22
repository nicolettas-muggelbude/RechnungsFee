import { pruefeUstIdnrFormat } from '../utils/laender'

const BZST_URL = 'https://www.bzst.de/DE/Unternehmen/Identifikationsnummern/Umsatzsteuer-Identifikationsnummer/eVatR/eVatR_node.html'

function formatDatumKurz(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

/** Formatwarnung + BZSt-eVatR-Link + "über BZSt bestätigt"-Checkbox für ein USt-IdNr.-Feld
 * (Issue #358). `aktiv` steuert ob die Prüfung überhaupt greift - beim Kunden ist das Feld für
 * Deutschland/Drittland auch als normale Steuernummer nutzbar (Issue #335), dort würde ein
 * Formatcheck gegen das USt-IdNr.-Muster falsche Warnungen erzeugen. */
export function UstIdnrPruefung({
  aktiv, land, ustIdnr, validiert, validierungDatum, onValidiertChange,
}: {
  aktiv: boolean
  land: string
  ustIdnr: string
  validiert: boolean
  validierungDatum?: string | null
  onValidiertChange: (validiert: boolean) => void
}) {
  if (!aktiv || !ustIdnr?.trim()) return null
  const formatOk = pruefeUstIdnrFormat(land, ustIdnr)

  return (
    <div className="mt-1.5 space-y-1.5">
      {formatOk === false && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          ⚠ Format entspricht nicht dem für {land} üblichen Muster – bitte prüfen.
        </p>
      )}
      <div className="flex items-center gap-3 flex-wrap">
        <button
          type="button"
          onClick={() => import('../api/client').then((m) => m.openUrl(BZST_URL))}
          className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
        >
          🔍 Bei BZSt online prüfen (eVatR) ↗
        </button>
        <label className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 cursor-pointer">
          <input
            type="checkbox"
            checked={validiert}
            onChange={(e) => onValidiertChange(e.target.checked)}
            className="rounded border-slate-300 dark:border-slate-600"
          />
          Über BZSt bestätigt
          {validiert && validierungDatum && (
            <span className="text-slate-400 dark:text-slate-500">({formatDatumKurz(validierungDatum)})</span>
          )}
        </label>
      </div>
    </div>
  )
}
