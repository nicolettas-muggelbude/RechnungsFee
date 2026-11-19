# Zugangsdaten im Schlüsselbund (Security-Audit F6)

**Stand:** 2026-11-17
**Status:** umgesetzt (Branch `feature/f6-passwoerter-schluesselbund`)

## Problem

SMTP-, IMAP-, SMB- und Backup-Verschlüsselungspasswort standen im Klartext in der Tabelle
`unternehmen`. Damit lagen sie

- in jeder Antwort von `GET /api/unternehmen` (auch PUT/POST/Logo-Upload),
- in der SQLite-Datei, den lokalen Snapshots unter `backups/` und im Download
  `GET /api/backup/download`,
- im Voll-Backup – wer die Datenbank hatte, konnte also auch die verschlüsselten externen
  Backups (`.zip.enc`) öffnen.

Jede Lese-Lücke (F2–F5, F11) lieferte die Zugangsdaten zu Mailkonto und Netzlaufwerk gleich mit.

## Lösung

### Ablage (`src/backend/utils/geheimnisse.py`)

Die vier Spalten enthalten nur noch einen Marker:

| Spaltenwert | Bedeutung |
|-------------|-----------|
| `NULL` | nicht gesetzt |
| `keyring:v1` | im Schlüsselbund des Betriebssystems (Python-Paket `keyring`: Windows Credential Manager, macOS Keychain, Secret Service/KWallet) |
| `enc:v1:<base64>` | Ersatzweg ohne nutzbaren Schlüsselbund: AES-256-GCM, Schlüssel in `<Profilordner>/geheimnis.key` (0600) |
| alles andere | Alt-Klartext vor F6 → wird beim Start umgezogen |

- Schlüsselbund-Eintrag: Dienst `RechnungsFee`, Benutzer `<profil-id>:<feld>`. Die Profil-ID ist
  eine UUID in `<Profilordner>/geheimnis_id` – nicht der Profilname (umbenennbar) und nicht in der
  Datenbank (ein Backup aus Profil A, in Profil B wiederhergestellt, zeigt nicht auf A).
- `keyrings.alt` (Klartextdatei) sowie fail/null-Backends werden abgelehnt → Ersatzweg.
  `RECHNUNGSFEE_KEIN_SCHLUESSELBUND=1` erzwingt den Ersatzweg.
- Der verschlüsselte Wert ist per AAD an Profil und Feld gebunden.
- `geheimnis.key` liegt außerhalb von `uploads/` und ist damit weder im Backup-Download noch im
  Voll-Backup.

### API

- `UnternehmenResponse` enthält keine Passwörter mehr, nur `smtp_passwort_gesetzt`,
  `imap_passwort_gesetzt`, `backup_extern_passwort_gesetzt`, `backup_smb_passwort_gesetzt`.
- PUT/POST (`GeheimnisEingabe` in `api/schemas.py`): leer oder nicht gesendet = unverändert,
  Wert = ersetzen, `<feld>_entfernen: true` = löschen.
- Gelesen wird nur noch über `geheimnisse.passwort(u, feld)` – `api/mail.py::_smtp_passwort`,
  `api/postfach.py::_imap_passwort`, `main.py::backup_erstellen`. Fehlt der Eintrag (z. B. nach
  Wiederherstellung auf einem anderen Rechner), gibt es eine verständliche Meldung statt eines
  Anmeldefehlers.

### Migration (`main.py::_migrate_geheimnisse`)

Läuft bei jedem Start (idempotent, wie `_migrate_kategorien`), keine eigene Schema-Version:

1. Klartext in der Datenbank → Schlüsselbund, Spalte → Marker. `PRAGMA secure_delete`,
   `VACUUM` und `wal_checkpoint(TRUNCATE)`, damit der alte Wert nicht in freien Seiten oder der
   WAL-Datei bleibt.
2. Snapshots unter `backups/`: gleicher Klartext → gleicher Marker (Wiederherstellen funktioniert
   auf diesem Rechner weiter), abweichender älterer Klartext → `NULL`.

Nicht bereinigen lassen sich bereits heruntergeladene ZIPs und externe `.zip.enc` – dafür der
Hinweis im Changelog, die Passwörter ggf. zu ändern.

### Profile

Beim endgültigen Löschen eines Profils (`api/profile.py::_loesche_profilordner`) werden dessen
Schlüsselbund-Einträge mit entfernt. Archivieren lässt sie stehen.

### Build

`keyring` lädt seine Backends über Entry Points. Der PyInstaller-Sidecar braucht deshalb
`--collect-submodules keyring --copy-metadata keyring` (`scripts/build-sidecar.sh` / `.ps1`) –
sonst fällt er still auf den Ersatzweg zurück. Nach dem ersten Release-Build prüfen: Log-Zeile
`[Geheimnisse] … (Ablage: schluesselbund)` beim Umzug.

## Bekannte Einschränkungen

- **macOS:** Die App ist nicht signiert; nach jedem Update ändert sich die Code-Identität, der
  Schlüsselbund fragt einmal „Zugriff erlauben?“.
- **Wiederherstellung auf anderem Rechner:** Passwörter müssen neu eingegeben werden (gewollt –
  die Datenbank allein reicht nicht mehr).
- **Tests** nutzen einen Schlüsselbund im Speicher (`tests/conftest.py`), nie den echten.
