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
    version: 'v0.1.15',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'Auto-Update: Signatur-Format in latest.json korrigiert (Base64-kodiert statt rohem Text) und Pubkey-Format wiederhergestellt' },
    ],
  },
  {
    version: 'v0.1.14',
    datum: 'März 2026',
    eintraege: [
      { typ: 'verbesserung', text: 'Test-Release: Auto-Update sollte jetzt von v0.1.13 auf v0.1.14 funktionieren' },
    ],
  },
  {
    version: 'v0.1.13',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'Auto-Update funktioniert jetzt auf Windows und Linux – Signatur-Verifikation war durch falsches Pubkey-Format fehlgeschlagen' },
    ],
  },
  {
    version: 'v0.1.12',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'Auto-Update unter Linux funktioniert jetzt – nach dem Download startet die neue Version direkt neu (relaunch statt exit)' },
    ],
  },
  {
    version: 'v0.1.11',
    datum: 'März 2026',
    eintraege: [
      { typ: 'verbesserung', text: 'Nach dem Update-Download erscheint eine Meldung \"Update installiert – bitte App manuell neu starten\", bevor die App sich schließt' },
    ],
  },
  {
    version: 'v0.1.10',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'Fehlermeldung bei Update-Problemen wird jetzt vollständig angezeigt (vorher: \"Update fehlgeschlagen: Update fehlgeschlagen\")' },
    ],
  },
  {
    version: 'v0.1.9',
    datum: 'März 2026',
    eintraege: [
      { typ: 'verbesserung', text: 'Protokoll-Datei wird jetzt geschrieben – unter Windows: %LOCALAPPDATA%\\de.rechnungsfee.app\\logs\\rechnungsfee.log' },
    ],
  },
  {
    version: 'v0.1.8',
    datum: 'März 2026',
    eintraege: [
      { typ: 'verbesserung', text: 'Update-Banner zeigt jetzt Fehlermeldung wenn das Update nicht installiert werden konnte' },
      { typ: 'verbesserung', text: 'Protokoll-Datei wird jetzt geschrieben – unter Windows: %APPDATA%\\RechnungsFee-Logs\\rechnungsfee.log' },
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
