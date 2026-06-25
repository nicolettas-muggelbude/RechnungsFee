# RechnungsFee – Website / Landingpage

Produktwebsite für RechnungsFee mit Custom Domain, gebaut mit Astro + Tailwind,
deployed via GitHub Actions auf GitHub Pages.

## Status

- [x] Domain beschaffen (rechnungsfee.app)
- [x] `web`-Branch anlegen + Astro-Projekt einrichten
- [x] GitHub Actions Workflow (Build + Deploy)
- [x] Domain in GitHub Pages konfigurieren (CNAME)
- [ ] Layout + Navigation bauen
- [ ] Startseite (Hero, Features, Screenshots, Download, Spenden)
- [ ] Funktionsübersicht (/funktionen)
- [ ] Spenden-Seite (/spenden)
- [ ] Impressum + Datenschutz (/impressum, /datenschutz)
- [ ] Changelog (/changelog aus changelog.ts)
- [ ] Handbuch (/handbuch/... aus Wiki)
- [ ] Wiki-Sync einrichten
- [ ] Jekyll-Dateien aus `docs/` in `main` entfernen

---

## Tech-Stack

| Was | Womit |
|-----|-------|
| Framework | Astro |
| CSS | Tailwind v4 (wie Frontend) |
| Deployment | GitHub Actions → GitHub Pages |
| Branch | `web` (Quellcode) → `gh-pages` (Build-Output) |
| Domain | rechnungsfee.app (Registrar: resellerinterface.de) |

---

## Seitenstruktur

| Route | Inhalt | Quelle |
|-------|--------|--------|
| `/` | Startseite: Hero, Top-Features, Screenshots, Download-Button, Spenden-Link | statisch + GitHub Releases API |
| `/funktionen` | Vollständige Funktionsübersicht nach Kategorien | statisch gepflegt |
| `/handbuch/...` | Wiki-Inhalte als Handbuch | geklontes Wiki-Repo zur Build-Zeit |
| `/changelog` | Versionshistorie | `src/frontend/src/data/changelog.ts` |
| `/spenden` | PayPal + IBAN + (später Wero) | statisch |
| `/impressum` | Impressum PC-Wittfoot UG | von `docs/impressum.md` übernommen |
| `/datenschutz` | Datenschutzerklärung | von `docs/datenschutz.md` übernommen |

---

## Startseite (`/`) – Aufbau

1. **Hero** – Headline, Subline, Download-Button (OS-erkannt, aktuelle Version aus GitHub Releases API), Screenshot
2. **Top-Features** – 6–8 Kacheln mit Icon + 1 Satz (Auswahl aus Funktionsübersicht)
3. **Screenshots** – 2–3 App-Ansichten
4. **Letzter Release** – Version + Datum, automatisch aktuell
5. **Spenden-Block** – kurzer Aufruf mit PayPal + IBAN
6. **Footer** – GitHub, Handbuch, Impressum, Datenschutz

---

## Funktionsübersicht (`/funktionen`) – Kategorien

- **Rechnungsstellung** – Angebot → Auftrag → Lieferschein → Rechnung → Proforma → Gutschrift → Storno; Wiederkehrende Rechnungen; Einleitungstext; Rabatt; Skonto; §25a Differenzbesteuerung
- **Journal & Kassenbuch** – Einnahmen/Ausgaben buchen; Bar/Karte/Überweisung; Tagesabschluss; GoBD-Signatur; km-Pauschale
- **EÜR & Steuer** – EÜR Anlage 2025; UStVA; Anlage G/S; DATEV-Export (EXTF); §13b, innergemeinschaftlicher Erwerb
- **Belege & GoBD** – Upload & Vorschau; OCR (Tesseract); PDF/A-Archivierung; unveränderliche Belege; Dokumentenpakete
- **Stammdaten** – Kunden (inkl. Lieferadressen, Dokumente); Lieferanten; Artikel + Lagerführung; Kategorien (SKR03/04)
- **Anlageverzeichnis** – AfA-Plan; Anlage AVEÜR; KFZ, EDV, sonstige Wirtschaftsgüter
- **Datensicherheit** – Lokal & offline; kein Cloud-Zwang; AES-256-Backup (NAS/USB/SMB); DSGVO-konform
- **Kommunikation** – E-Mail-Versand (SMTP); PDF-Vorlagen; Unterschrift; ZUGFeRD/XRechnung

---

## Handbuch (`/handbuch`) – Wiki-Sync

- GitHub Action klont `RechnungsFee.wiki.git` zur Build-Zeit
- Markdown-Dateien → `src/content/handbuch/`
- Sidebar aus `_Sidebar.md` generieren
- Build-Trigger: Push auf `main` (manuell oder Cron nächtlich)

---

## Download-Button – OS-Erkennung (clientseitig)

`navigator.userAgentData.platform` bzw. `navigator.userAgent` als Fallback.

| Erkanntes OS | Primärer Button | Datei |
|--------------|-----------------|-------|
| Windows | ⬇ Für Windows herunterladen | `RechnungsFee_X.X.X_x64-setup.exe` |
| Linux | ⬇ Für Linux herunterladen | `RechnungsFee_X.X.X_amd64.AppImage` |
| macOS | ⬇ Für macOS herunterladen | `RechnungsFee_X.X.X_aarch64.dmg` (Apple Silicon, Intel-Link darunter) |
| Unbekannt | Alle Plattformen anzeigen | – |

Unter dem Primär-Button: kleine Links „Andere Plattformen" → klappt alle Optionen auf.
Downloadzähler (summiert aus GitHub Releases API `download_count`) neben oder unter dem Button.

---

## Dynamische Inhalte (Build-Zeit)

| Inhalt | Quelle | Wie |
|--------|--------|-----|
| Aktuelle Version + Download-Links | GitHub Releases API | `fetch` in Astro `.astro`-Seite |
| GitHub Sterne | GitHub API | `fetch` |
| Changelog | `changelog.ts` | direkter Import (TypeScript-nativ in Astro) |
| Handbuch-Seiten | Wiki-Repo | `git clone` im Action-Step |

---

## Zahlungsoptionen (`/spenden`)

| Methode | Status | Gebühren |
|---------|--------|----------|
| PayPal | ✅ aktiv | ~1,5 % + 0,35 € |
| Banküberweisung (IBAN) | ✅ aktiv | kostenlos |
| Wero | 🔜 geplant | – |

IBAN: DE43 2805 0100 0093 3624 57 · BIC: SLZODE22XXX · Kontoinhaber: PC-Wittfoot UG

---

## Design-Referenz

Grob angelehnt an rustdesk.com, aber mit besserem Weißraum und Typographie.
Farbpalette: RechnungsFee-Blau (`#0070ba`) + Slate (wie App-Frontend).
