/**
 * Changelog – wird bei jedem Release manuell gepflegt.
 * Neueste Version steht oben.
 *
 * Eintragstypen:
 *   neu         → neues Feature       (grün)
 *   verbesserung → Verbesserung/Umbau  (blau)
 *   fix          → Bugfix              (amber)
 */

export type EintragTyp = 'neu' | 'verbesserung' | 'fix'

export type ChangelogEintrag = {
  typ: EintragTyp
  text: string
}

export type ChangelogVersion = {
  version: string
  datum: string
  eintraege: ChangelogEintrag[]
}

export const CHANGELOG: ChangelogVersion[] = [
  {
    version: 'v0.1 Beta',
    datum: 'März 2026',
    eintraege: [
      { typ: 'neu', text: 'Kassenbuch mit GoBD-konformen unveränderlichen Einträgen und SHA-256-Signaturen (§146 AO)' },
      { typ: 'neu', text: 'Rechnungen (Eingang & Ausgang) mit Zahlungsverfolgung, Teilzahlungen und PDF nach DIN 5008' },
      { typ: 'neu', text: 'Kunden & Lieferanten mit DSGVO-Funktionen (Auskunft Art. 15, Löschung Art. 17)' },
      { typ: 'neu', text: 'Tagesabschlüsse mit SHA-256-Integritätsprüfung und PDF-Export' },
      { typ: 'neu', text: 'GoBD-Export für Betriebsprüfungen (Z3-Datenträgerüberlassung, 8 Dateien als ZIP)' },
      { typ: 'neu', text: 'Backup-Funktion: manueller Download + automatisches Backup vor DB-Updates' },
      { typ: 'neu', text: 'Kontext-Hilfe mit ℹ-Tooltips für GoBD-Konzepte, Steuerfelder und Rechnungslogik' },
      { typ: 'neu', text: 'Setup-Assistent für den ersten Start (Unternehmen, Konto, Anfangsbestand)' },
      { typ: 'neu', text: 'Nummernkreise frei konfigurierbar (Kassenbuch KB, Rechnung RE, Kunden KD, Lieferanten LI)' },
      { typ: 'neu', text: 'Logo-Upload + Mail-Vorlagen in den Unternehmensstammdaten' },
      { typ: 'neu', text: 'Kleinunternehmer §19 UStG vollständig unterstützt (USt automatisch 0 %, kein Vorsteuerabzug)' },
    ],
  },
]
