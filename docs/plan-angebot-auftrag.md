# Plan: Angebot · Auftrag · Auftragsbestätigung

Workflow-Erweiterung für B2B-Verkaufsprozesse.

```
Angebot → [akzeptiert] → Auftrag + AB → Lieferschein → Rechnung
                       ↘ Rechnung direkt
```

---

## Stufe 1 – Navigation + Dokumentenpakete

### Navigation umbauen

Neue Sidebar-Struktur mit Gruppen:

```
Dashboard
── Verkauf ──────────────
  Angebote
  Aufträge
  Lieferscheine          ← raus aus Rechnungen-Detail
  Rechnungen
── Einkauf ──────────────
  Journal
  Belege
── Stammdaten ───────────
  Kunden / Lieferanten
  Artikel
  Kategorien / Konten
  Unternehmen
── Auswertung ───────────
  EÜR · UStVA · ZM · EKS
```

Lieferscheine bleiben im Backend an Rechnungen geknüpft, bekommen aber
einen eigenen Menüpunkt mit Übersichtstabelle (analog zur bestehenden
Lieferschein-Übersicht, die bisher nur aus Rechnungs-Detail erreichbar ist).

### Dokumentenpakete (Stammdaten)

Neue Stammdaten-Sektion: **Dokumentenpakete**

Zweck: Wiederverwendbare Anhang-Gruppen für Angebote und Auftragsbestätigungen –
ohne starre B2B/B2C-Unterscheidung, frei konfigurierbar.

Beispiele:
| Paketname | Enthält |
|-----------|---------|
| Standard B2B | AGB-B2B.pdf, Datenschutzerklärung.pdf, Leistungsverzeichnis.pdf |
| Privatkunden | AGB-B2C.pdf, Widerrufsbelehrung.pdf |
| EU-Ausland | AGB-EU.pdf, DSE-EN.pdf |

**Schema:**
- `dokumentenpakete` (id, name, beschreibung, aktiv)
- `dokumentenpaket_belege` (id, paket_id FK, beleg_id FK, sort_order)
- `kunden.dokumentenpaket_id FK` – Standard-Paket pro Kunde (optional)

Belege kommen aus der bestehenden `belege`-Tabelle (Upload-Bereich).
Beim Erstellen eines Angebots/AB wird das Paket des Kunden vorausgewählt,
ist aber pro Dokument überschreibbar.

---

## Stufe 2 – Angebote

### Datenmodell

`rechnungen.dokument_typ = 'Angebot'` – kein neues Table, alle
Infrastruktur (Positionen, PDF, Nummernkreis, E-Mail) funktioniert direkt.

Neue Felder in `rechnungen`:
| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `angebot_status` | VARCHAR(20) | `offen` / `akzeptiert` / `abgelehnt` / `abgelaufen` |
| `gueltig_bis` | DATE | Ablaufdatum des Angebots |
| `dokumentenpaket_id` | FK → dokumentenpakete | Anhänge für dieses Angebot |
| `rechnung_zu_angebot_id` | FK → rechnungen | generierte Rechnung (ausgegraut wenn gesetzt) |
| `auftrag_zu_angebot_id` | FK → rechnungen | generierter Auftrag (ausgegraut wenn gesetzt) |

Nummernkreis: `ANG-JJJJ####`

### Funktionen

- Angebot erstellen (aus Kunden-Detail oder eigenem Menüpunkt)
- PDF-Vorschau + Versand per E-Mail (Dokumentenpaket als Anhänge)
- Status-Badge in Übersicht (offen / akzeptiert / abgelehnt)
- Ablauf-Datum → Status wechselt automatisch auf `abgelaufen`
- **„In Rechnung umwandeln"** – erstellt Rechnung mit übernommenen Positionen
- **„In Auftrag umwandeln"** – erstellt Auftrag (Stufe 3), Angebot-Status → akzeptiert
- Sobald Rechnung/Auftrag erstellt: Button ausgegraut, Link zum Dokument

---

## Stufe 3 – Aufträge + Auftragsbestätigung

### Datenmodell

`rechnungen.dokument_typ = 'Auftrag'` – gleiche Basis wie Angebot.

Neue Felder in `rechnungen`:
| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `auftrag_status` | VARCHAR(20) | `offen` / `in_bearbeitung` / `abgeschlossen` / `storniert` |
| `angebot_id` | FK → rechnungen | Quell-Angebot (optional, wenn aus Angebot erstellt) |
| `auftragsbestaetigung_aktiv` | BOOLEAN | AB per Mail versenden? |
| `auftragsbestaetigung_versendet_am` | DATETIME | Versandzeitpunkt |
| `dokumentenpaket_id` | FK → dokumentenpakete | Anhänge für AB |
| `rechnung_zu_auftrag_id` | FK → rechnungen | generierte Rechnung |
| `lieferschein_zu_auftrag_id` | FK → rechnungen | generierter Lieferschein |

Nummernkreis: `AUF-JJJJ####`

### Auftragsbestätigung (AB)

Optionaler Versand beim Speichern/Erstellen des Auftrags:
- PDF mit Kopfzeile „Auftragsbestätigung" statt „Auftrag"
- Anhänge aus Dokumentenpaket (AGB, DSE, Leistungsverzeichnis)
- Versand per E-Mail (vorhandene Mail-Infrastruktur)
- AB kann auch nachträglich erneut versendet werden

### Funktionen

- Auftrag erstellen (aus Angebot oder direkt aus Kunden-Detail)
- **„Lieferschein erstellen"** → ausgegraut + Link wenn bereits vorhanden
- **„Rechnung erstellen"** → ausgegraut + Link wenn bereits vorhanden
- Status-Tracking (offen → in_bearbeitung → abgeschlossen)
- Spätere Onlineshop-Anbindung: Aufträge per API importieren (Webhook-Endpunkt)

### Workflow-Übersicht (komplett)

```
[Angebot]
    │ akzeptiert
    ▼
[Auftrag] ──→ [Auftragsbestätigung per Mail + Anhänge]
    │
    ├──→ [Lieferschein] ──→ [Rechnung]
    │
    └──→ [Rechnung direkt]
```
