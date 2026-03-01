# RechnungsFee – Claude-Entwicklungsnotizen

GoBD-konformes Kassenbuch + Rechnungsprogramm für Kleinunternehmer/Freiberufler.
Stack: FastAPI + SQLAlchemy 2.0 + SQLite | React 19 + TypeScript + Tailwind v4 | Tauri 2.10

## Starten

```bash
# Backend
cd src/backend && .venv/bin/uvicorn main:app --port 8001 --reload

# Frontend
cd src/frontend && npm run dev
```

## Wichtige Konventionen
- UI-Texte: **Du-Ansprache** (nicht Sie)
- Geldbeträge: `NUMERIC(12,2)` – keine floats
- Commits: deutsch, `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`
- Kein `git push` ohne explizite Aufforderung

## SQLAlchemy 2.0 Gotcha
`db.query(Model).update({"feld": wert})` – **String-Keys**, nicht `{Model.feld: wert}`

## Zod v4 + @hookform/resolvers v5 Gotcha
Kein `.default()` in Zod-Schemas → Typ-Konflikt. Defaults in `useForm({ defaultValues })`,
Fallback im Submit-Handler mit `?? wert`.

## Rechnungs-PDF (pdf_rechnung.py)
DIN 5008 Form B, fpdf2 + Pillow:
- Adressfeld fest bei `Y=45mm` (Fensterumschlag-kompatibel)
- Header: Logo links + Firma/Adresse/Tel/Mail/Web rechts (bündig mit Rechnungsnummer-Spalte)
- Footer 3 gleiche Spalten:
  1. Firmenname, Adresse, Tel/E-Mail/Web
  2. Inhaber/GF/GS (rechtsformabhängig via `_person_bezeichnung()`), USt-ID od. StNr, HRB
  3. Bank, IBAN, BIC, Seite · Datum
- Dezentes `– Kopie –` unter Titel statt rotem Banner

## Rechtsform → Personenbezeichnung
`_person_bezeichnung(rechtsform)` in `pdf_rechnung.py`:
- GmbH/UG/AG/SE/eG/KGaA → `GF:` (Geschäftsführer)
- GbR/OHG/KG/PartG → `GS:` (Gesellschafter)
- sonst → `Inh.:` (Inhaber)

## Logo-Upload
`POST/GET/DELETE /api/unternehmen/logo` – gespeichert unter `~/.local/share/RechnungsFee/uploads/`
Max 2 MB, nur PNG/JPEG/WEBP. Pillow berechnet Aspect Ratio für PDF-Einbettung.

## Mail-Vorlagen (Platzhalter)
`{rechnungsnummer}`, `{datum}`, `{betrag}`, `{faellig_am}`, `{kunde}`, `{firmenname}`
Felder: `unternehmen.mail_betreff_vorlage`, `mail_text_vorlage`, `mail_signatur`

## Changelog

### 2026-03-01
- Unternehmen: +`handelsregister_nr`, +`handelsregister_gericht` (DB + Schema + Frontend)
- Unternehmen: +`logo_pfad`, +`mail_betreff_vorlage`, +`mail_text_vorlage`, +`mail_signatur`
- Logo-Upload-Endpunkte (`POST/GET/DELETE /api/unternehmen/logo`)
- UnternehmenPage: vollständige Seite (Firmendaten + Logo + Mail-Vorlage + Signatur)
- RechnungenPage: Mail-Template mit Platzhalter-Ersetzung + Signatur
- BuchungDetail: Mail-Signatur aus Unternehmen
- RechnungResponse: +`kunde_email`, +`lieferant_email` (aus Kundenstamm)
- Entwurfs-Rechnung: Zahlung gesperrt (Backend 409 + Frontend-Guard)
- PDF-Rechnung: DIN 5008 Komplett-Redesign (Adressfeld Y=45mm, 3-Spalten-Footer, Logo, rechtsformabhängige Personenbezeichnung)
- unt_dict in rechnungen.py: alle 22 Felder übergeben (vorher nur 9)
