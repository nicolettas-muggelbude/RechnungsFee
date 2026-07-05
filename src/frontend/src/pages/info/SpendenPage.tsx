import { openUrl } from '../../api/client'

const PAYPAL_URL = 'https://www.paypal.com/ncp/payment/UYJ73YNEZ3KHL'
const GITHUB_URL = 'https://github.com/nicolettas-muggelbude/RechnungsFee'
const IMPRESSUM_URL = 'https://rechnungsfee.app/impressum'
const DATENSCHUTZ_URL = 'https://rechnungsfee.app/datenschutz'

export function SpendenPage() {
  return (
    <div className="max-w-2xl mx-auto px-6 py-10 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-2">RechnungsFee unterstützen</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm">
          RechnungsFee ist kostenlos, Open Source (AGPLv3) und wird in der Freizeit entwickelt.
          Jede Unterstützung hilft dabei, das Projekt weiterzuführen und neue Features umzusetzen.
        </p>
      </div>

      {/* Kosten */}
      <div className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-3">Laufende Kosten</h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between text-slate-700 dark:text-slate-200">
              <span>GitHub (Hosting, Actions, Releases)</span>
              <span className="font-medium">kostenlos</span>
            </div>
            <div className="flex justify-between text-slate-700 dark:text-slate-200">
              <span>Entwicklungszeit (Freizeit)</span>
              <span className="font-medium">unbezahlt</span>
            </div>
          </div>
        </div>
        <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
          <h2 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-3">Einmalige &amp; anlassbezogene Kosten</h2>
          <div className="space-y-2 text-sm text-slate-700 dark:text-slate-200">
            <div className="flex items-start gap-2">
              <span className="material-symbols-outlined text-[#4F46E5] shrink-0" style={{ fontSize: '1.25rem' }}>computer</span>
              <span>Infrastruktur – Hardware, Tools und Lizenzen für die Entwicklung</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="material-symbols-outlined text-[#4F46E5] shrink-0" style={{ fontSize: '1.25rem' }}>mic</span>
              <span>Raummiete für kostenfreie Vorträge und Workshops rund um RechnungsFee</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="material-symbols-outlined text-[#4F46E5] shrink-0" style={{ fontSize: '1.25rem' }}>checkroom</span>
              <span>Merchandise – Aufkleber, Shirts und Materialien für die Community</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="material-symbols-outlined text-[#4F46E5] shrink-0" style={{ fontSize: '1.25rem' }}>celebration</span>
              <span>Event-Teilnahmen – Anreise, Unterkunft und Standgebühren</span>
            </div>
          </div>
        </div>
      </div>

      {/* Spenden */}
      <div className="bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 rounded-xl p-6 space-y-5">
        <p className="text-slate-700 dark:text-slate-200 text-sm text-center">
          Wenn RechnungsFee dir Arbeit spart oder dich in deiner Selbstständigkeit unterstützt –
          freue ich mich über jede Spende, egal wie klein.
        </p>

        {/* PayPal */}
        <div className="flex flex-col items-center gap-2">
          <button
            onClick={() => openUrl(PAYPAL_URL)}
            className="inline-flex items-center gap-2 px-6 py-3 bg-[#0070ba] hover:bg-[#005ea6] text-white font-semibold rounded-xl text-sm transition-colors shadow-sm"
          >
            <span className="material-symbols-outlined leading-none" style={{ fontSize: '1.25rem' }}>favorite</span>
            <span>Via PayPal spenden</span>
          </button>
          <p className="text-xs text-slate-400 dark:text-slate-500">
            PayPal zieht Transaktionsgebühren ab (~1,5 % + 0,35 €)
          </p>
        </div>

        {/* Überweisung */}
        <div className="border-t border-blue-200 dark:border-blue-800 pt-4">
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-3 text-center">
            Oder gebührenfrei per Banküberweisung
          </p>
          <div className="bg-white dark:bg-slate-800 rounded-lg p-4 space-y-1 text-sm font-mono">
            <div className="flex justify-between gap-4">
              <span className="text-slate-400 dark:text-slate-500 font-sans shrink-0">Kontoinhaber</span>
              <span className="text-slate-700 dark:text-slate-200 text-right">PC-Wittfoot UG</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-400 dark:text-slate-500 font-sans shrink-0">IBAN</span>
              <span className="text-slate-700 dark:text-slate-200 tracking-wider">DE43 2805 0100 0093 3624 57</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-400 dark:text-slate-500 font-sans shrink-0">BIC</span>
              <span className="text-slate-700 dark:text-slate-200">SLZODE22XXX</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-400 dark:text-slate-500 font-sans shrink-0">Verwendungszweck</span>
              <span className="text-slate-700 dark:text-slate-200">Spende RechnungsFee</span>
            </div>
          </div>
        </div>

        <p className="text-xs text-slate-500 dark:text-slate-400 text-center pt-1">
          Spenden werden treuhänderisch von der <strong className="font-medium">PC-Wittfoot UG</strong> verwaltet
          (Spendenverwalter, nicht Entwickler).
          Die Entwicklung von RechnungsFee erfolgt durch die Community als Open-Source-Projekt.
        </p>
      </div>

      {/* Alternativ */}
      <div className="border border-slate-200 dark:border-slate-700 rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Andere Wege zu helfen</h2>
        <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
          <li className="flex items-start gap-2">
            <span className="material-symbols-outlined text-[#4F46E5] mt-0.5 shrink-0" style={{ fontSize: '1.25rem' }}>star</span>
            <span>
              Das Projekt auf{' '}
              <button
                onClick={() => openUrl(GITHUB_URL)}
                className="text-blue-600 dark:text-blue-400 hover:underline"
              >
                GitHub mit einem Stern markieren
              </button>{' '}
              – macht das Projekt sichtbarer
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="material-symbols-outlined text-[#4F46E5] mt-0.5 shrink-0" style={{ fontSize: '1.25rem' }}>bug_report</span>
            <span>Bugs melden und Feature-Wünsche als GitHub Issue eintragen</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="material-symbols-outlined text-[#4F46E5] mt-0.5 shrink-0" style={{ fontSize: '1.25rem' }}>campaign</span>
            <span>RechnungsFee anderen Freiberuflern und Kleinunternehmern empfehlen</span>
          </li>
        </ul>
      </div>

      <p className="text-xs text-slate-400 dark:text-slate-500 text-center">
        Danke, dass du RechnungsFee nutzt. ♥
      </p>

      <div className="flex justify-center gap-4 text-xs text-slate-400 dark:text-slate-500">
        <button onClick={() => openUrl(IMPRESSUM_URL)} className="hover:underline hover:text-slate-600 dark:hover:text-slate-300">
          Impressum
        </button>
        <span>·</span>
        <button onClick={() => openUrl(DATENSCHUTZ_URL)} className="hover:underline hover:text-slate-600 dark:hover:text-slate-300">
          Datenschutz
        </button>
      </div>
    </div>
  )
}
