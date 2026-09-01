interface Props {
  onClose: () => void
}

/** Erscheint wenn der Thunderbird-Versand (Issue #147) keinen der bekannten Aufrufe
 *  (nativ/snap/flatpak/macOS-App-Bundle/Windows-Installationspfad) starten konnte. */
export function ThunderbirdInstallHinweis({ onClose }: Props) {
  return (
    <div className="bg-orange-50 dark:bg-orange-950 border border-orange-200 dark:border-orange-800 rounded-lg px-4 py-3 space-y-2">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-semibold text-orange-700 dark:text-orange-300">
          ✉️ Thunderbird wurde nicht gefunden
        </p>
        <button
          type="button"
          onClick={onClose}
          className="text-orange-400 hover:text-orange-600 dark:hover:text-orange-200 text-sm leading-none shrink-0"
          aria-label="Schließen"
        >
          ✕
        </button>
      </div>
      <p className="text-xs text-orange-600 dark:text-orange-400">
        Der Thunderbird-Versand ist aktiviert (Einstellungen → Unternehmen → E-Mail), aber RechnungsFee konnte Thunderbird auf diesem Rechner nicht starten. Geprüft wurden der normale Programmpfad sowie Snap- und Flatpak-Installationen.
      </p>
      <ul className="text-xs text-orange-600 dark:text-orange-400 list-disc list-inside space-y-0.5">
        <li>Linux: <code className="font-mono">sudo apt install thunderbird</code> (oder das Äquivalent der eigenen Distribution)</li>
        <li>macOS: <code className="font-mono">brew install --cask thunderbird</code> oder von thunderbird.net herunterladen</li>
        <li>Windows: Installer von thunderbird.net herunterladen</li>
      </ul>
      <p className="text-xs text-orange-600 dark:text-orange-400">
        Alternativ: Thunderbird-Versand unter Einstellungen → Unternehmen → E-Mail wieder deaktivieren, dann läuft der Versand wie gewohnt über SMTP oder das Standard-Mailprogramm.
      </p>
    </div>
  )
}
