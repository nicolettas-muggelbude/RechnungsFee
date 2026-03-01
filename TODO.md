# TODO – Beta-Vorbereitung

Ziel: Stabiles, sicheres und installierbares Programm als Basis für die Weiterentwicklung.
Zielgruppe Beta: §19-Kleinunternehmer / Freiberufler.

---

## 1. Tooltip-System ✅

Viele GoBD-Konzepte sind für Nutzer ungewohnt (Storno statt Löschen, Tagesabschluss, immutable Einträge).
Kontext-Hilfe direkt im UI ist wertvoller als externe Dokumentation.

- [x] Wiederverwendbare `<InfoTooltip>`-Komponente (`components/InfoTooltip.tsx`, ℹ-Icon + Hover/Tap-Popup, side=top|bottom)
- [x] Kassenbuch: Storno (GoBD §146, Gegeneintrag), Split-Buchung, Vorsteuerabzug (einfach + Split)
- [x] Tagesabschluss: Seitentitel (§146a AO, unveränderlich), SHA-256-Integritätsprüfung
- [x] Rechnungen: Entwurf-Banner, KOPIE-Markierung, Zahlungsstatus-Label
- [x] Kleinunternehmer §19 (UnternehmenPage: Checkbox)
- [x] Formulare: Steuernummer, USt-IdNr., Versteuerungsart, Kontenrahmen

---

## 2. Menüpunkt "Info" ✅

Sichtbarer Einstiegspunkt für Hilfe, Beta-Hinweis und Feedback-Link.

- [x] Info-Seite in der Sidebar ergänzen (ℹ️ Info & Updates)
- [x] Versionsnummer aus Git-Tag (`__APP_VERSION__`)
- [x] Beta-Disclaimer (amber Box mit Backup-Link)
- [x] "Was ist neu" – statisches Changelog (`src/frontend/src/data/changelog.ts`), aufklappbar pro Version, Typ-Badges (Neu/Verbessert/Fix)
- [x] Links: GitHub Issues, Roadmap, Lizenz AGPL-3.0, Quellcode
- [x] Kurzbeschreibung Zielgruppe und Scope

---

## 3. DB-Migrationen robust für Updates ✅

Beta-Nutzer akkumulieren echte Daten. Jede neue Version muss sauber migrieren.

- [x] Migrations-Mechanismus in `main.py` (`_run_migrations()`) auf Vollständigkeit prüfen
- [x] Alle bisherigen Migrationen dokumentieren (CLAUDE.md – Versionsverlauf)
- [x] `PRAGMA user_version` als Versionstabelle – `SCHEMA_VERSION = 2`, kontrollierte Versionssprünge
- [x] Backup vor jeder Migration automatisch anlegen (`_backup_datenbank()`, max. 5, WAL-sicher)
- [x] Early-Return wenn DB aktuell (kein PRAGMA-Overhead beim normalen Start)
- [x] Integrations-Test: leere DB → aktuelle Version, alte DB → aktuelle Version (`src/backend/tests/test_migrations.py`, 6 Tests)

---

## 4. Backup ✅

Vor Datenverlust schützen – besonders kritisch bei Updates und bei Beta-Nutzern ohne IT-Kenntnisse.

- [x] "Backup erstellen"-Button (`GET /api/backup/download`, `BackupPage.tsx`, Sidebar-Eintrag 💾)
- [x] Automatisches Backup vor DB-Migration beim App-Start (TODO 3, `_backup_datenbank()`, max. 5, Rotation)
- [x] Backup wiederherstellen – Schritt-für-Schritt-Anleitung in BackupPage.tsx
- [x] Format: `.db` (SQLite direkt öffenbar, konsistent mit Auto-Backups)

---

## 5. Tauri-Build + Paketformate ✅

Nutzer brauchen ein installierbares Programm, nicht manuelles `uvicorn` + `npm run dev`.

### Beschlossene Paketierungs-Strategie

| Phase | Format | Plattform | Updater |
|---|---|---|---|
| **Beta** | `.AppImage` | Linux (alle Distros) | Tauri in-app ✅ |
| **Beta** | `.msi` | Windows | Tauri in-app ✅ |
| **Post-Beta** | Flatpak (Flathub) | Linux | flatpak update ⚙️ |
| **Post-Beta** | `.dmg` | macOS | Tauri in-app ✅ |
| **On Demand** | Snap | Ubuntu | snapd automatisch ⚙️ |

> `.deb` / `.rpm` werden nicht als primäre Formate gepflegt –
> AppImage (Beta) und Flatpak (Post-Beta) decken Linux vollständig ab.

### Aufgaben

- [x] Tauri-Sidecar: FastAPI-Backend als eingebettetes Binary (PyInstaller)
- [x] GitHub Actions Workflow für automatische Builds bei Tag-Push (`v*`)
  - [x] Matrix: `[windows-latest, ubuntu-latest]` für Beta
  - [x] Outputs: `.msi` + `.AppImage`
- [x] App-Icon aus Logo ableiten (alle Plattform-Größen: 16–512px, `.ico`, `.icns`, `.png`)
- [x] Erster Start: Auto-Setup wenn keine DB vorhanden (bereits implementiert)
- [x] Backend-Port Konflikt abfangen (8001 belegt → nächsten freien Port wählen)
- [ ] Code Signing Windows: selbstsigniertes Zertifikat für Beta (Hinweis im Installer)
- [ ] Flatpak-Manifest (`org.rechnungsfee.App.yaml`) + Flathub-Einreichung nach Beta

---

## 6. Updater ✅

Ohne Updater müssen Nutzer manuell neu installieren – nicht akzeptabel nach Beta-Launch.

> Gilt für AppImage und MSI. Flatpak/Snap nutzen ihr eigenes Update-System und rufen
> den Tauri-Updater nicht auf – das ist gewollt.

- [x] Tauri-Updater aktivieren (`tauri-plugin-updater`)
- [x] Update-Server: GitHub Releases als Quelle
  - JSON-Endpoint `latest.json` wird von GitHub Actions automatisch bei jedem Release erzeugt
- [x] Code-Signing: Signing-Key generiert, Public Key in `tauri.conf.json`, Private Key als GitHub Secret
- [x] Update-Check beim App-Start (nicht-blockierend, grünes Hinweis-Banner in InfoPage)
- [ ] Vor Update: automatisches Backup auslösen (→ siehe Punkt 4)
- [ ] Changelog im Update-Dialog anzeigen

---

## Reihenfolge (Empfehlung)

```
DB-Migration robust  →  Backup  →  Tooltip-System + Info-Seite  →  Tauri-Build  →  Updater
```

Alle Beta-Blocker erledigt. Erstes Release: **v0.1.1** (02.03.2026)

Begründung: Datensicherheit zuerst, dann UX, dann Deployment.

---

## Post-Beta (nicht Blocker)

- Verschlüsselung (SQLCipher oder Datei-Ebene)
- EÜR / UStVA-Voranmeldung
- E-Rechnung (ZUGFeRD / XRechnung) – B2B-Pflicht ab 2025
- Bank-CSV-Import
- Mahnwesen
