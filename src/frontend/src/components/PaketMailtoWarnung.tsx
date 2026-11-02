/** Issue #477: Hinweis an Angebot/Auftrag mit Dokumentenpaket, wenn weder SMTP noch
 *  Thunderbird eingerichtet ist - über mailto: lassen sich keine Anhänge übergeben, das Paket
 *  käme beim Kunden also nicht an. Sichtbar schon vor dem Klick auf „Mail senden“. */
export function PaketMailtoWarnung({ onEinrichten }: { onEinrichten: () => void }) {
  return (
    <div className="flex gap-2 items-start rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950 px-3 py-2 text-xs text-amber-800 dark:text-amber-200">
      <span aria-hidden="true">⚠️</span>
      <p>
        Das Dokumentenpaket wird nur beim Versand per SMTP oder Thunderbird mitgeschickt. Über dein
        Standard-Mailprogramm geht nur das PDF raus, und auch das musst du selbst anhängen.{' '}
        <button type="button" onClick={onEinrichten} className="underline hover:no-underline font-medium">
          Mailversand einrichten →
        </button>
      </p>
    </div>
  )
}
