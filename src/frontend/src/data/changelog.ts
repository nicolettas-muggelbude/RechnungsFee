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
    version: 'v0.1.29',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'Linux: Weißes Fenster bei KDE Plasma / Wayland behoben – WEBKIT_DISABLE_COMPOSITING_MODE und WEBKIT_DISABLE_DMABUF_RENDERER werden beim App-Start gesetzt' },
      { typ: 'verbesserung', text: 'install-linux.sh prüft jetzt ob libwebkit2gtk-4.1-0 installiert ist (Hinweis für Debian/MX-Linux-Nutzer)' },
      { typ: 'verbesserung', text: 'openUrl-Hilfsfunktion jetzt zentral exportiert – doppelter Code in RechnungenPage entfernt, invoke-Import eliminiert' },
    ],
  },
  {
    version: 'v0.1.28',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'Windows: PDF-Generierung funktioniert jetzt – DejaVu-Schriften werden aus dem Projektverzeichnis (fonts/) geladen und per PyInstaller ins Backend-Bundle gepackt' },
      { typ: 'fix', text: 'PDF öffnet sich jetzt in einem einzigen Browser-Tab statt zwei – Content-Disposition auf inline geändert, alle Downloads (PDF, ZIP, JSON, Backup) nutzen jetzt den Systembrowser statt WebView' },
    ],
  },
  {
    version: 'v0.1.27',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'Windows: App schließt sich jetzt sofort – taskkill wird nicht mehr abgewartet (spawn statt output)' },
    ],
  },
  {
    version: 'v0.1.26',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'Windows: PDF-Generierung funktioniert jetzt – DejaVu-Schriften werden direkt aus dem fpdf2-Paket geladen statt aus Linux-Systempfaden gesucht' },
      { typ: 'fix', text: 'Windows: backend.exe wird beim Schließen der App wieder zuverlässig beendet – Prozess wird jetzt direkt beim Window-Close-Event statt beim App-Exit-Event getötet' },
    ],
  },
  {
    version: 'v0.1.25',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'Linux: Icon und Andocken funktionieren jetzt – StartupWMClass auf de.rechnungsfee.app korrigiert (Tauri 2 nutzt den App-Identifier als GTK App-ID, nicht den Produktnamen)' },
      { typ: 'fix', text: 'Linux: Icon-Cache wird nach der Installation automatisch aktualisiert – kein Ab- und Anmelden mehr nötig' },
    ],
  },
  {
    version: 'v0.1.24',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'PDF öffnen und Drucken funktioniert jetzt auf Linux und Windows – Tauri öffnet PDFs jetzt im Systembrowser statt in einem WebView-Fenster (das keine PDFs rendern kann)' },
      { typ: 'fix', text: 'Linux: Desktop-Integration (install-linux.sh) benötigt kein sudo mehr – Icon wird direkt von GitHub geladen statt aus dem AppImage extrahiert' },
      { typ: 'fix', text: 'Linux: App lässt sich jetzt ans Dock anheften – StartupWMClass war kleingeschrieben und passte nicht zum Fenstertitel' },
    ],
  },
  {
    version: 'v0.1.23',
    datum: 'März 2026',
    eintraege: [
      { typ: 'neu', text: 'Berufsbezeichnung & Kammermitgliedschaft: 12 Berufskarten im Setup-Assistenten, Kammerberufe (Rechtsanwalt, Steuerberater, Architekt, Arzt) werden automatisch vorausgefüllt – erscheinen auf PDF-Rechnungen' },
      { typ: 'fix', text: 'Mail-Versand funktioniert jetzt auf Linux (kein "URL can\'t be shown" mehr) und Windows (PDF wird korrekt erstellt)' },
      { typ: 'fix', text: 'AppImage behält nach einem Update jetzt seinen Dateinamen – kein manuelles Umbenennen mehr nötig' },
      { typ: 'fix', text: 'Linux: RechnungsFee erscheint jetzt mit eigenem Icon im Anwendungsmenü (nach einmaligem Ausführen von install-linux.sh)' },
      { typ: 'fix', text: 'Setup-Assistent: Schrittanzeige ist jetzt auf Windows und Linux korrekt ausgerichtet' },
    ],
  },
  {
    version: 'v0.1.22',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'App lässt sich wieder schließen – onCloseRequested-Handler entfernt, der durch await invoke() blockierte und das Fenster einfrieren ließ' },
    ],
  },
  {
    version: 'v0.1.21',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'App schließt wieder sofort – kein preventDefault mehr im Close-Handler' },
      { typ: 'fix', text: 'Backend-Prozess wird jetzt zuverlässig beendet – taskkill /T läuft jetzt VOR dem child.kill(), damit der Python-Child-Prozess (PyInstaller) nicht als Waise weiterläuft' },
    ],
  },
  {
    version: 'v0.1.19',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'Backend-Sidecar wird beim App-Schließen zuverlässig beendet – PyInstaller --onefile startet auf Windows zwei Prozesse; taskkill /T beendet jetzt den gesamten Prozessbaum' },
    ],
  },
  {
    version: 'v0.1.18',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'Windows-Update: NSIS-ZIP wird jetzt ohne Komprimierung (Stored) erstellt – tauri-plugin-updater unterstützt nur diese Methode' },
    ],
  },
  {
    version: 'v0.1.17',
    datum: 'März 2026',
    eintraege: [
      { typ: 'fix', text: 'Windows-Update: ZIP-Datei wird jetzt mit Standard-Deflate erstellt (statt Deflate64) – behebt "Compression method not supported"' },
    ],
  },
  {
    version: 'v0.1.16',
    datum: 'März 2026',
    eintraege: [
      { typ: 'verbesserung', text: 'Test-Release: Update von v0.1.15 auf v0.1.16 zum Testen des Auto-Updaters' },
    ],
  },
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
