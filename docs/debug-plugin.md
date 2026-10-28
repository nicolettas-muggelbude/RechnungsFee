# Mitgeliefertes Debug-Plugin

Das System-Plugin `org.rechnungsfee.debug` ist immer Bestandteil von RechnungsFee,
auch im Desktop-/AppImage-Build. Du findest es unter **Einstellungen → Plugins →
Debug-Protokoll**. Es muss weder installiert noch mit einem Wasm-Paket aktualisiert
werden und kann nicht über die Plugin-Verwaltung entfernt werden.

## Verwendung

1. Wähle die gewünschten Kategorien aus.
2. Schalte **Aufzeichnen** ein (bei einem neuen Profil standardmäßig aus).
3. Führe die zu untersuchenden Aktionen in der App aus.
4. Öffne **Protokoll anzeigen**. Du kannst nach Kategorie filtern und die
   Live-Aktualisierung im Abstand von drei Sekunden pausieren.
5. Mit **Logdatei herunterladen** exportierst du die vorhandenen Einträge inklusive
   rotierter Dateien als JSONL-Datei, älteste zuerst.

Die Anzeige zeigt die neuesten 200 passenden Einträge, neueste zuerst. Beim
Ausschalten bleiben bestehende Protokolle erhalten. Kategorien und Hauptschalter
werden sofort profilbezogen gespeichert; ein Neustart ist nicht nötig. Andere
bereits geöffnete Browserfenster übernehmen Einstellungen innerhalb von zehn Sekunden.

| Kategorie | Aufgezeichnete Informationen |
| --- | --- |
| UI-Aktionen | Klick, Feldänderung oder Absenden, Seite, Elementtyp und technische Elementkennung |
| Seitenwechsel | Besuchte App-Seite ohne Suchparameter oder Hash |
| API-Anfragen | Methode, Routenvorlage, HTTP-Status, Dauer und Anfragekennung |
| Plugin-Aufrufe | Plugin-ID, Pre-/Post-Hook oder Host-API-Aufruf, Ergebnis und Dauer, auch bei Erfolg |
| Fehler | Browserfehler bzw. unbehandelte Promises, Backend-Exceptiontyp, HTTP-Fehler ab Status 400 und Python-Logmeldungen ab ERROR als technische Metadaten |

Die UI-Elementkennung kommt aus `data-debug-id`, falls gesetzt, sonst aus der
Position des Elements im DOM. Beschriftungen und Formularwerte werden nicht gelesen.
UI-Ereignisse werden sekundenweise gesammelt übertragen. Fehlertexte, Stacktraces,
Passwörter, Header, Anfrage-/Antwortinhalte, Dateinamen und Belegtexte werden nicht
in dieses Diagnoseprotokoll übernommen. Das vorhandene `backend.log` bleibt separat.
Browserfehler enthalten deshalb nur den Fehlertyp (`javascript`/`promise`).

Die Debug-API und die Bedienung der Protokollkarte werden nicht selbst protokolliert;
dadurch entsteht beim Live-Lesen keine Endlosschleife. Seitenwechsel zur Plugin-Seite
können weiterhin als Navigation erscheinen. Bei nicht erreichbarem Backend werden
UI-Ereignisse nicht nachträglich wiederholt. Aktionen außerhalb der Weboberfläche
(z. B. Betriebssystemdialoge oder Rust-internes Verhalten) sind nicht abgedeckt.

## Dateien und Auslieferung

Alle Dateien liegen im **aktiven Profil** unter `APP_DATA_DIR/logs/`:

- `debug-plugin.json`: gewählte Einstellungen.
- `interaktionen.jsonl`: aktuelles Protokoll, ein JSON-Objekt pro Zeile mit UTC-Zeitstempel.
- `interaktionen.jsonl.1` bis `.3`: automatische Rotation bei jeweils 2 MB,
  insgesamt etwa 8 MB; älteste Einträge werden dabei ersetzt.

Die UI zeigt den konkreten Dateipfad an. Profilwechsel erfordern wie bisher einen
Neustart und trennen sowohl Einstellungen als auch Logdateien. Schreibfehler im Log
verhindern keine fachlichen Aktionen und werden beim erneuten Laden der Einstellungen
in der UI angezeigt.

Das Debug-Plugin ist ein **eingebauter Host-Beobachter**, kein externes Wasm-Plugin:
Die gegenwärtige WIT-Schnittstelle bietet keine Dateizugriffe und keine allgemeinen
UI-/HTTP-Ereignisse. Die Sandbox-Rechte externer Plugins bleiben unverändert.
Der Schalter „Plugins verwenden“ und `RECHNUNGSFEE_PLUGINS=0` betreffen externe
Wasm-Plugins; das Diagnoseprotokoll besitzt seinen eigenen Schalter, damit es auch
bei Problemen mit Fremdplugins verfügbar bleibt.

Beide Sidecar-Buildskripte nehmen die Debug-Module explizit mit. Für einen neuen
Desktop-Build einschließlich Diagnosefunktion genügt `make build:dev`,
`make build:prod` oder unter Linux `make build:appimage`.

## Prüfung

```bash
make test-backend PYTEST_ARGS="-q -k debug_plugin"
```

Die Tests prüfen Kategorieauswahl, Persistenz, Profiltrennung, Rotation,
Fehlerbehandlung, HTTP-/Plugin-Erfassung, Ausschluss vertraulicher Inhalte und
Download. Sie verwenden temporäre Verzeichnisse statt echter Profile.
