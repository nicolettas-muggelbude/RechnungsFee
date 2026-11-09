# Sitzungstoken zwischen Tauri, Frontend und Backend

**Stand:** 2026-11-09
**Status:** Schritt 1 umgesetzt (Branch `feature/f4-sitzungstoken`), Security-Audit F4 Teil 2.
Schritt 2 (signierte Kurzzeit-Links für Datei-URLs) folgt.

## Problem

Das Backend (Sidecar) lauscht auf `127.0.0.1:<zufälliger Port>`. Bis v0.7.10 gab es keine
Authentifizierung: Die Host-, Origin- und CORS-Prüfung schützte nur vor Angriffen aus dem
Browser. Jeder lokale Prozess und jeder andere Benutzer desselben Rechners konnte mit einem
einfachen `curl` alle Daten lesen (auch SMTP-/IMAP-Passwörter), Buchungen anlegen, ein Backup
einspielen oder das Backend beenden.

## Lösung: ein Zufallstoken pro App-Start

```
Tauri (Rust)                       Sidecar (Python)                Frontend (Hauptfenster)
─────────────                      ────────────────                ───────────────────────
32 Zufallsbytes (getrandom) ─────► stdin, 1. Zeile                 invoke('get_backend_token')
                                    (--token-stdin)          ◄──── Authorization: Bearer <token>
Shutdown per TCP mit Token ───────► POST /api/shutdown
```

- **Erzeugung:** `src-tauri/src/lib.rs` → `neues_sitzungstoken()`, 32 Byte aus dem
  Zufallsgenerator des Betriebssystems, hex-kodiert (64 Zeichen). Bei jedem Start neu, dadurch
  ist ein altes Token nach dem Beenden wertlos.
- **Übergabe an den Sidecar über stdin**, nicht über die Kommandozeile. Unter Linux/macOS ist
  `argv` per `ps` für alle Benutzer sichtbar. Der Sidecar liest das Token mit 30 s Timeout ein,
  bevor uvicorn startet (`utils/sitzungstoken.py::aus_stdin()`). Der gebündelte Sidecar
  (`sys.frozen`) startet ohne Token nicht.
- **Übergabe an das Frontend per IPC** (`get_backend_token`). Nur das Fenster `main` hat
  IPC-Rechte (`capabilities/default.json`), PDF-Fenster bekommen das Token nicht.
- **Prüfung** in `utils/sicherheit_middleware.py` (äußerste ASGI-Schicht, nach Host-/Origin-
  Prüfung): fehlt der Header oder stimmt er nicht, kommt 401. Verglichen wird zeitkonstant mit
  `hmac.compare_digest`.
- **Frontend:** Alle Aufrufe ans Backend laufen über `apiFetch()` in `api/client.ts`, das den
  Header ergänzt. **Neue direkte `fetch()`-Aufrufe ans Backend immer über `apiFetch()`**,
  sonst 401.
- **Beenden:** Rust schickt `POST /api/shutdown` direkt per TCP mit Token
  (`sende_shutdown()`) statt per `curl`. Sonst stünde das Token in der Kommandozeile eines
  Hilfsprozesses.

### Warum kein JWT

JWT ist für getrennte Aussteller und Prüfer mit Claims (Benutzer, Rollen, Ablauf) gedacht. Hier
gibt es einen Aussteller (Tauri), einen Prüfer (Backend), einen Benutzer und keine Rollen. JWT
brächte nur zusätzliche Fehlerquellen (Algorithmus-Verwechslung, `alg: none`, Bibliotheken,
Refresh-Logik) ohne Nutzen. Verschlüsselung (TLS auf Loopback) wurde ebenfalls verworfen: Der
Verkehr verlässt den Rechner nicht, und wer Loopback mitlesen kann, kann auch die Datenbank lesen.

## Ausnahmen ohne Token

| Was | Warum |
|-----|-------|
| `OPTIONS` | CORS-Preflight trägt keinen `Authorization`-Header |
| `GET /health` | reine Erreichbarkeitsprüfung, keine Daten |
| GET/HEAD auf Datei-Endpunkte (`_FENSTER_PFADE`) | **Übergang bis Schritt 2:** PDFs, Belege, Logo usw. werden in einem eigenen `WebviewWindow`, `<iframe>` oder `<img>` geladen, und dort lässt sich kein Header setzen |

**Wichtig für neue Datei-Endpunkte:** Wird ein neuer GET-Endpunkt im eigenen Fenster geöffnet
(`openUrl()`, `openInPdfWindow()`, `<img src>`), muss sein Pfad in `_FENSTER_PFADE` ergänzt
werden, sonst zeigt das Fenster „Sitzungstoken fehlt oder ist ungültig.“. Der Test
`test_fensterpfade_existieren_als_get_routen` prüft, dass jeder Eintrag zu einer echten Route
passt.

Alle JSON-Endpunkte und alle schreibenden Requests brauchen das Token.

## Entwicklungsmodus

- `uvicorn main:app --port 8002` ohne `RECHNUNGSFEE_TOKEN`: keine Token-Prüfung (wie bisher).
- Mit Token, wie im Release: `scripts/dev-start.sh` bzw. `scripts/dev-start.fish`. Die Skripte
  erzeugen ein Token, starten Backend und Frontend mit demselben `RECHNUNGSFEE_TOKEN` und
  beenden das Backend bei Strg+C mit. Der Vite-Proxy hängt den Header an (`vite.config.ts`).
  Optionen: ohne = Browser, `--tauri` = Desktop-Fenster, `--backend` = nur Backend (gibt das
  Token für curl-Tests aus).

## Was das Token nicht leistet

Schadsoftware, die als **derselbe Benutzer** läuft, kann die SQLite-Datei direkt lesen oder das
Token aus dem Prozess holen. Das Token schützt gegen andere Benutzer des Rechners, gegen
Webseiten (auch über andere localhost-Dienste) und gegen Programme, die nur Netzwerkzugriff auf
Loopback haben.

## Tests

`src/backend/tests/test_security_sitzungstoken.py`: ohne, mit falschem und mit richtigem Token,
Preflight, Fensterpfade inkl. `/_datei/`-Segment (Issue #476), Abgleich der Fensterpfade mit den
echten Routen, Übergabe über stdin und Umgebungsvariable, ungültige Token-Formate.

## Nächste Schritte

1. **Signierte Kurzzeit-Links** für alle Datei-URLs (`?exp=…&sig=HMAC-SHA256(…)`, Schlüssel vom
   Token abgeleitet, 10–15 Minuten gültig), dann `_FENSTER_PFADE` entfernen.
2. Passwörter write-only (`GET /api/unternehmen` liefert nur „gesetzt ja/nein“).
3. Im Release `http://localhost:5173` aus CORS entfernen; die Origin-Ausnahme für beliebige
   localhost-Ports streichen.
4. Archivierung beim ersten PDF-Abruf von GET auf POST verlagern.
5. Tauri: CSP für das Hauptfenster setzen, `write_bytes_to_path` und `open_url` einschränken.
