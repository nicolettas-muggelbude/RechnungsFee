import { RechnungenPage } from '../rechnungen/RechnungenPage'

/**
 * Standalone-Route /lieferscheine – öffnet RechnungenPage direkt im Lieferschein-Modus.
 */
export function LieferscheineUebersicht() {
  return <RechnungenPage initialLieferscheinModus />
}
