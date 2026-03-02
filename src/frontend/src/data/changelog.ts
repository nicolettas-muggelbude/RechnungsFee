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
    version: 'v0.1.8',
    datum: 'März 2026',
    eintraege: [
      { typ: 'verbesserung', text: 'Update-Banner zeigt jetzt Fehlermeldung wenn das Update nicht installiert werden konnte' },
    ],
  },
  {
    version: 'v0.1.7',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'Windows-Update: App beendet sich nach dem Download korrekt, damit der Installer die Dateien ersetzen kann' },
    ],
  },
  {
    version: 'v0.1.6',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'App startet nach dem Update unter Windows jetzt automatisch neu – vorher blieb die alte Version geöffnet' },
    ],
  },
  {
    version: 'v0.1.5',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'Mehrere backend.exe-Instanzen im Task-Manager behoben – Hintergrunddienst wird beim Schließen der App jetzt sauber beendet' },
    ],
  },
  {
    version: 'v0.1.4',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'Fehlermeldung "Backend nicht erreichbar" unter Windows behoben – App wartet jetzt bis zu 10 Sekunden auf den Start des Hintergrunddienstes' },
    ],
  },
  {
    version: 'v0.1.3',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'Auto-Updater funktioniert jetzt korrekt – App-Version wird aus dem Git-Tag ermittelt' },
      { typ: 'verbesserung', text: 'Update-Benachrichtigung erscheint direkt beim App-Start (nicht erst beim Öffnen der Info-Seite)' },
    ],
  },
  {
    version: 'v0.1.2',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'Drucken, PDF öffnen und Mail senden funktionieren jetzt unter Windows (Tauri/WebView2-Kompatibilität)' },
      { typ: 'fix', text: 'Zuflussmonitor zählt den Kassenanfangsbestand nicht mehr als Einnahme' },
      { typ: 'fix', text: 'Kein Tagesabschluss-Hinweis mehr für Tage vor der Ersteinrichtung' },
      { typ: 'fix', text: 'Entwurf-Label in Rechnungen vereinfacht' },
    ],
  },
  {
    version: 'v0.1.1',
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
