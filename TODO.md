# TODO – Beta-Vorbereitung

Ziel: Stabiles, sicheres und installierbares Programm als Basis für die Weiterentwicklung.
Zielgruppe Beta: §19-Kleinunternehmer / Freiberufler.

---

## 1. Tooltip-System

Viele GoBD-Konzepte sind für Nutzer ungewohnt (Storno statt Löschen, Tagesabschluss, immutable Einträge).
Kontext-Hilfe direkt im UI ist wertvoller als externe Dokumentation.

- [ ] Wiederverwendbare `<Tooltip>`-Komponente (Info-Icon + Hover/Tap-Popup)
- [ ] Kassenbuch: Tooltips für "Warum kann ich nicht löschen?", Storno, Split-Buchung, Vorsteuerabzug
- [ ] Tagesabschluss: Was ist das, warum ist er unveränderlich
- [ ] Rechnungen: Entwurf vs. finalisiert, KOPIE-Markierung, Zahlungsstatus
- [ ] Kleinunternehmer §19: Hinweis warum keine USt ausgewiesen wird
- [ ] Formulare: Pflichtfelder nach §14 UStG erklären (USt-IdNr, Steuernummer etc.)

---

## 2. Menüpunkt "Info"

Sichtbarer Einstiegspunkt für Hilfe, Beta-Hinweis und Feedback-Link.

- [ ] Info-Seite in der Sidebar ergänzen
- [ ] Inhalt:
  - Versionsnummer (aus `package.json` / Tauri-Config)
  - Beta-Disclaimer ("Programm befindet sich in der Beta-Phase – nicht als alleinige Steuerunterlage verwenden")
  - Link zu GitHub Issues (Feedback / Fehler melden)
  - Lizenz (AGPL-3.0)
  - Kurze Beschreibung Zielgruppe und Scope

---

## 3. DB-Migrationen robust für Updates

Beta-Nutzer akkumulieren echte Daten. Jede neue Version muss sauber migrieren.

- [ ] Migrations-Mechanismus in `main.py` (`_run_migrations()`) auf Vollständigkeit prüfen
- [ ] Alle bisherigen Migrationen dokumentieren und testen (frische DB vs. alte DB)
- [ ] Versionstabelle in DB einführen (`schema_version`) für kontrollierten Migrations-Ablauf
- [ ] Rollback-Strategie festlegen: Backup vor jeder Migration automatisch anlegen
- [ ] Integrations-Test: leere DB → aktuelle Version, alte DB → aktuelle Version

---

## 4. Backup

Vor Datenverlust schützen – besonders kritisch bei Updates und bei Beta-Nutzern ohne IT-Kenntnisse.

- [ ] "Backup erstellen"-Button in Einstellungen / Info-Seite
  - Kopiert `rechnungsfee.db` nach `~/Downloads/RechnungsFee-Backup-YYYY-MM-DD.db`
  - Bestätigungs-Dialog mit Speicherpfad
- [ ] Automatisches Backup vor DB-Migration beim App-Start
  - Speicherort: `~/.local/share/RechnungsFee/backups/` (max. 5 aufbewahren, älteste rotieren)
- [ ] Backup wiederherstellen (manuell: DB-Datei ersetzen, Hinweis in Info-Seite)
- [ ] Backup-Datei als `.db` (SQLite direkt öffenbar) oder `.zip` (mit Metadaten-Datei)?

---

## 5. Tauri-Build

Nutzer brauchen ein installierbares Programm, nicht manuelles `uvicorn` + `npm run dev`.

- [ ] Tauri-Sidecar: FastAPI-Backend als eingebettetes Binary (PyInstaller oder ähnlich)
- [ ] Build-Pipeline:
  - [ ] Windows: `.msi` / `.exe`-Installer
  - [ ] Linux: `.deb` / `.AppImage`
  - [ ] macOS: `.dmg` (optional für Beta)
- [ ] GitHub Actions Workflow für automatische Builds bei Tag-Push (`v*`)
- [ ] App-Icon (alle Plattform-Größen)
- [ ] Erster Start: Auto-Setup wenn keine DB vorhanden (ist bereits implementiert)
- [ ] Backend-Port Konflikt abfangen (8001 belegt → nächsten freien Port wählen)

---

## 6. Updater

Ohne Updater müssen Nutzer manuell neu installieren – nicht akzeptabel nach Beta-Launch.

- [ ] Tauri-Updater aktivieren (`tauri-plugin-updater`)
- [ ] Update-Server: GitHub Releases als Quelle (JSON-Endpoint mit Versionsinfos)
- [ ] Code-Signing einrichten (Pflicht für Tauri-Updater)
  - Windows: Selbstsigniertes Zertifikat für Beta, später ggf. EV-Zertifikat
  - macOS: Apple Developer ID (falls macOS-Support geplant)
  - Linux: kein Signing erforderlich
- [ ] Update-Check beim App-Start (nicht-blockierend, Hinweis-Banner wenn Update verfügbar)
- [ ] Vor Update: automatisches Backup auslösen (→ siehe Punkt 4)
- [ ] Changelog im Update-Dialog anzeigen

---

## Reihenfolge (Empfehlung)

```
DB-Migration robust  →  Backup  →  Tooltip-System + Info-Seite  →  Tauri-Build  →  Updater
```

Begründung: Datensicherheit zuerst, dann UX, dann Deployment.

---

## Post-Beta (nicht Blocker)

- Verschlüsselung (SQLCipher oder Datei-Ebene)
- EÜR / UStVA-Voranmeldung
- E-Rechnung (ZUGFeRD / XRechnung) – B2B-Pflicht ab 2025
- Bank-CSV-Import
- Mahnwesen
