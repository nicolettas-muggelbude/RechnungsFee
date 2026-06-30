<div align="center">
  <img src="src/frontend/public/logo.svg" alt="RechnungsFee Logo" width="80"/>
  <br/>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/readme-title-dark.svg"/>
    <img src="assets/readme-title.svg" alt="RechnungsFee" height="36"/>
  </picture>
</div>

# 🛠️ Maintainer-Guide

Dieser Guide richtet sich an Projekt-Maintainer und beschreibt interne Prozesse.

---

## 📋 Inhaltsverzeichnis

- [Bank-CSV Beiträge reviewen](#bank-csv-beiträge-reviewen)
- [Anonymisierung prüfen](#anonymisierung-prüfen)
- [CSV ins Repository hinzufügen](#csv-ins-repository-hinzufügen)
- [Issue schließen](#issue-schließen)
- [Häufige Probleme](#häufige-probleme)

---

## 🏦 Bank-CSV Beiträge reviewen

### Workflow-Übersicht

```
GitHub Issue erstellt
    ↓
Review: Template vollständig?
    ↓
Download CSV-Attachment
    ↓
Anonymisierung prüfen ⚠️ WICHTIG!
    ↓
CSV umbenennen & hinzufügen
    ↓
Status-Tracking aktualisieren
    ↓
Commit & Push
    ↓
Issue mit Danke-Kommentar schließen
```

### 1. Issue-Review Checklist

Wenn ein neues Issue mit Label `bank-integration` erstellt wird:

**✅ Vollständigkeit prüfen:**
- [ ] Bankname angegeben (z.B. "Sparkasse Musterstadt", "DKB")
- [ ] CSV-Struktur ausgefüllt (Trennzeichen, Encoding, Datumsformat)
- [ ] Spalten aufgelistet (in Reihenfolge)
- [ ] CSV-Datei angehängt (als Attachment)

**✅ CSV-Attachment herunterladen:**
1. Scrolle zum Attachment-Bereich im Issue
2. Klicke auf die CSV-Datei → Download
3. Speichere in temporärem Ordner (z.B. `~/Downloads/`)

---

## 🔒 Anonymisierung prüfen

**⚠️ KRITISCH: Keine echten Daten ins Repository!**

### Schritt 1: CSV öffnen und prüfen

Öffne die CSV mit einem Text-Editor (NICHT Excel - kann Formatierung ändern):

```bash
cat ~/Downloads/bank-export.csv
# oder
nano ~/Downloads/bank-export.csv
```

### Schritt 2: Anonymisierungs-Checklist

**❌ DARF NICHT enthalten sein:**

| Was | Beispiel FALSCH | Beispiel RICHTIG |
|-----|-----------------|------------------|
| **Echte IBAN** | `DE12345678901234567890` | `DE89370400440532013000` |
| **Echte Namen** | `Schmidt, Peter` | `Mustermann, Max` |
| | `Dr. Med. Müller` | `Arztpraxis` |
| **Echte Firmen** | `Autowerkstatt Meier GmbH` | `Autowerkstatt GmbH` |
| **Sensible Verwendungszwecke** | `Miete Musterstr. 42, 12345 Berlin` | `Miete` |
| | `Arztrechnung Dr. XY, Therapie` | `Arztrechnung` |
| | `Spende Verein ABC e.V.` | `Spende` |
| | `Kredit 123456789` | `Kredittilgung` |
| **Kontonummer (alt)** | `1234567890` | `0000000001` |
| **Echte BIC** (optional) | `BYLADEM1001` | `COBADEFFXXX` |

**✅ MUSS erhalten bleiben:**

- ✅ **Header-Zeile** (Spaltenköpfe) - EXAKT wie im Original!
- ✅ **Trennzeichen** (`;`, `,`, `\t`) - Nicht ändern!
- ✅ **Anführungszeichen** (`"..."`, `'...'`) - Wie im Original!
- ✅ **Datumsformat** (`DD.MM.YYYY`, `YYYY-MM-DD`) - Beibehalten!
- ✅ **Dezimaltrennzeichen** (`,` oder `.`) - Beibehalten!
- ✅ **Spaltenanzahl** - Alle Spalten behalten, auch leere!
- ✅ **Zeilenumbrüche** - Format beibehalten!
- ✅ **Währung** (`EUR`, `USD`) - Beibehalten!

### Schritt 3: Bei mangelhafter Anonymisierung

**Option A: Selbst anonymisieren**
- Öffne CSV in Text-Editor
- Ersetze sensible Daten nach obiger Tabelle
- Speichere als neue Datei

**Option B: Rückfrage an Contributor**

Kommentar im Issue:

```markdown
Vielen Dank für deinen Beitrag! 🙏

Leider enthält die CSV noch sensible Daten, die anonymisiert werden müssen:

- [ ] Zeile 3: Echte IBAN `DE12345...` → Bitte durch Beispiel-IBAN ersetzen
- [ ] Zeile 5: Name "Schmidt, Peter" → Bitte durch "Mustermann, Max" ersetzen
- [ ] Zeile 7: Verwendungszweck "Miete Musterstr. 42" → Bitte nur "Miete"

Bitte lade eine aktualisierte CSV hoch. Die Anleitung findest du hier:
[TEMPLATE.md - Anonymisierungs-Regeln](https://github.com/nicolettas-muggelbude/RechnungsFee/blob/main/vorlagen/bank-csv/TEMPLATE.md#-anonymisierungs-regeln)

Danke! 🚀
```

---

## 📂 CSV ins Repository hinzufügen

### Schritt 1: Bank identifizieren

Finde heraus, welche Bank es ist:

**Hinweise:**
- **BLZ/BIC**: Lookup auf https://www.iban.de/blz-suche oder https://www.theswiftcodes.com/
- **Spaltenköpfe**: Typische Muster erkennen
- **User-Angaben**: Bankname im Issue

**Beispiele:**

| BLZ/BIC | Bank |
|---------|------|
| `SLZODE2XXXX`, `28050100` | Sparkasse/LZO |
| `BYLADEM1XXX`, `70050000` | Bayerische Landesbank / Sparkasse Bayern |
| `COBADEFFXXX` | Commerzbank |
| `DEUTDEFFXXX` | Deutsche Bank |
| `GENODEF1XXX` | Volksbank/Raiffeisenbank |

### Schritt 2: Datei umbenennen

**Namenskonvention:**
```
<bankname>.csv
```

**Beispiele:**
- `sparkasse-lzo.csv`
- `volksbank.csv`
- `dkb.csv`
- `ing.csv`
- `n26.csv`
- `commerzbank.csv`

**Falls mehrere Varianten derselben Bank:**
```
sparkasse-lzo.csv
sparkasse-bayern.csv
sparkasse-koeln-bonn.csv
```

### Schritt 3: Datei hinzufügen

```bash
# Datei ins Repository kopieren
cp ~/Downloads/bank-export.csv vorlagen/bank-csv/sparkasse.csv

# Prüfen, dass keine Zone.Identifier-Dateien mitkommen
ls -la vorlagen/bank-csv/
# Falls vorhanden: rm vorlagen/bank-csv/*.Zone.Identifier

# Datei zu Git hinzufügen
git add vorlagen/bank-csv/sparkasse.csv
```

### Schritt 4: Status-Tracking aktualisieren

**4.1 Datei-Liste in `vorlagen/bank-csv/README.md` aktualisieren:**

Ändere von:
```markdown
├── sparkasse.csv          # (noch nicht vorhanden)
```

zu:
```markdown
├── sparkasse.csv          # ✅ Sparkasse
```

**4.2 Status-Tabelle aktualisieren:**

Ändere von:
```markdown
| Sparkasse | ❌ | ❌ | ❌ |
```

zu:
```markdown
| Sparkasse | ✅ | ❌ | ❌ |
```

**4.3 Git hinzufügen:**
```bash
git add vorlagen/bank-csv/README.md
```

### Schritt 5: Commit & Push

```bash
git commit -m "feat: Bank-CSV für <Bankname> hinzugefügt

Fügt anonymisierte Beispiel-CSV für <Bankname> hinzu:
- <Anzahl> Transaktionsbeispiele
- Alle sensiblen Daten anonymisiert
- Original-Format beibehalten

CSV-Details:
- Trennzeichen: <; oder , oder Tab>
- Encoding: <UTF-8 oder ISO-8859-1 oder Windows-1252>
- Datumsformat: <DD.MM.YYYY oder YYYY-MM-DD>
- Dezimaltrennzeichen: <, oder .>
- Spalten: <Anzahl>

Closes #<Issue-Nummer>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin main
```

**Beispiel:**
```bash
git commit -m "feat: Bank-CSV für Volksbank hinzugefügt

Fügt anonymisierte Beispiel-CSV für Volksbank hinzu:
- 12 Transaktionsbeispiele
- Alle sensiblen Daten anonymisiert
- Original-Format beibehalten

CSV-Details:
- Trennzeichen: Komma (,)
- Encoding: UTF-8
- Datumsformat: YYYY-MM-DD
- Dezimaltrennzeichen: Punkt (.)
- Spalten: 8

Closes #5

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## ✅ Issue schließen

### Template für Danke-Kommentar

**Standard-Dankeschön:**

```markdown
Vielen Dank für deinen Beitrag! 🎉

Die CSV für **<Bankname>** wurde erfolgreich hinzugefügt:
- ✅ Anonymisierung geprüft
- ✅ Format validiert
- ✅ Ins Repository integriert → [vorlagen/bank-csv/<dateiname>.csv](https://github.com/nicolettas-muggelbude/RechnungsFee/blob/main/vorlagen/bank-csv/<dateiname>.csv)

Dank deiner Hilfe unterstützt RechnungsFee jetzt **<Anzahl> Banken**! 🚀

Wenn du weitere Banken nutzt, trag sie gerne auch bei! 💪

Nochmals danke! ❤️
```

**Beispiel:**

```markdown
Vielen Dank für deinen Beitrag! 🎉

Die CSV für **Volksbank** wurde erfolgreich hinzugefügt:
- ✅ Anonymisierung geprüft
- ✅ Format validiert
- ✅ Ins Repository integriert → [vorlagen/bank-csv/volksbank.csv](https://github.com/nicolettas-muggelbude/RechnungsFee/blob/main/vorlagen/bank-csv/volksbank.csv)

Dank deiner Hilfe unterstützt RechnungsFee jetzt **2 Banken** (Sparkasse/LZO, Volksbank)! 🚀

Wenn du weitere Banken nutzt, trag sie gerne auch bei! 💪

Nochmals danke! ❤️
```

**Issue schließen:**
- Label `enhancement` bestätigen
- Ggf. Label `good first contribution` hinzufügen (beim ersten Beitrag des Users)
- Issue als **Closed** markieren

---

## ⚠️ Häufige Probleme

### Problem 1: CSV enthält echte Daten

**Symptome:**
- Echte IBANs erkennbar (nicht `DE89370400440532013000`)
- Echte Namen, Adressen, spezifische Firmen

**Lösung:**
1. **NICHT committen!**
2. CSV selbst anonymisieren oder Rückfrage an User (siehe oben)
3. Niemals echte Daten ins öffentliche Repo pushen

**Falls versehentlich committed:**
```bash
# Git-History bereinigen
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch vorlagen/bank-csv/dateiname.csv" \
  --prune-empty --tag-name-filter cat -- --all

# Force-Push (VORSICHT!)
git push origin --force --all
```

### Problem 2: CSV-Format unbekannt / unklar

**Lösung:**
- Frage im Issue nach: "Welche Bank genau?"
- BLZ/BIC nachschlagen
- Falls unklar: Temporär als `bank-unbekannt-<datum>.csv` speichern
- Issue offen lassen bis geklärt

### Problem 3: Mehrere Banken in einem Issue

**Lösung:**
- Jede Bank separat hinzufügen (separate Commits)
- Im Danke-Kommentar alle erwähnen:
  ```markdown
  Vielen Dank für deinen Beitrag! 🎉

  Wir haben **3 Banken** aus deinem Issue hinzugefügt:
  - ✅ Sparkasse
  - ✅ Volksbank
  - ✅ DKB

  Wow, das sind gleich 3 auf einmal! 🚀
  ```

### Problem 4: Encoding-Probleme (Umlaute falsch)

**Symptome:**
- `Ã¼` statt `ü`
- `Ã¶` statt `ö`
- `ÃŸ` statt `ß`

**Ursache:**
Datei ist ISO-8859-1 oder Windows-1252, wird aber als UTF-8 gelesen

**Lösung:**
```bash
# Encoding konvertieren
iconv -f ISO-8859-1 -t UTF-8 input.csv > output.csv

# oder
iconv -f WINDOWS-1252 -t UTF-8 input.csv > output.csv
```

**Alternative:**
- In Issue dokumentieren: "Diese Bank nutzt ISO-8859-1 Encoding"
- Datei mit originalem Encoding committen
- Im README dokumentieren

### Problem 5: CSV zu groß (viele Zeilen)

**Lösung:**
- Nur 10-20 Beispielzeilen behalten
- Repräsentative Auswahl:
  - Mix aus Lastschrift, Überweisung, Dauerauftrag
  - Positive + negative Beträge
  - Verschiedene Buchungstexte

```bash
# Erste 20 Zeilen (inkl. Header) behalten
head -n 21 input.csv > output.csv
```

### Problem 6: Attachment fehlt

**Lösung:**

Kommentar im Issue:
```markdown
Hallo! 👋

Danke für dein Interesse! Leider fehlt die CSV-Datei als Attachment.

Kannst du sie bitte noch hochladen?
1. Klicke auf "Attach files" unten im Kommentarfeld
2. Ziehe deine anonymisierte CSV hinein
3. Kommentar absenden

Danke! 🙏
```

### Problem 7: Bank bietet mehrere Export-Formate

**Situation:**
Manche Banken bieten verschiedene CSV-Exporte an:
- **MT940** (SWIFT Standard)
- **CAMT V2 / V8** (ISO 20022 Cash Management)
- **Eigenformate** (Bank-spezifische Varianten)

**Beispiel:** Sparkasse/LZO bietet MT940, CAMT V2, CAMT V8

**Lösung:**

**1. Separate Dateien erstellen:**
```bash
sparkasse-lzo-mt940.csv
sparkasse-lzo-camt-v2.csv
sparkasse-lzo-camt-v8.csv
```

**2. Namenskonvention:**
```
<bank>-<format>.csv              # Ein Format
<bank>-<format>-<version>.csv    # Mehrere Versionen
```

**Weitere Beispiele:**
- `volksbank-mt940.csv`
- `dkb-standard.csv` (wenn nur ein Format)
- `commerzbank-camt-v8.csv`

**3. Status-Tabelle erweitern:**
```markdown
| Bank | Format | CSV vorhanden | Parser | Getestet |
|------|--------|---------------|--------|----------|
| Sparkasse/LZO | MT940 | ✅ | ❌ | ❌ |
| Sparkasse/LZO | CAMT V2 | ✅ | ❌ | ❌ |
| Sparkasse/LZO | CAMT V8 | ✅ | ❌ | ❌ |
```

**4. Im Danke-Kommentar erwähnen:**
```markdown
Vielen Dank! 🎉

Die CSV für **Sparkasse/LZO (MT940-Format)** wurde hinzugefügt!

**Hinweis:** Diese Bank bietet auch CAMT V2 und V8 Exporte an.
Falls du diese Formate auch beitragen möchtest, wäre das super! 🚀
```

**Warum mehrere Formate wichtig sind:**
- User können unterschiedliche Formate bevorzugen
- Manche Formate haben mehr/weniger Details
- Parser-Robustheit testen (verschiedene Strukturen)
- Flexibilität für End-User

---

## 📊 Status-Tracking

Nach jedem hinzugefügten CSV:

**Aktualisieren:**
1. `vorlagen/bank-csv/README.md` - Datei-Liste & Status-Tabelle
2. Optional: GitHub Discussion aktualisieren (falls erstellt)
3. Optional: Projekt-README.md (wenn Meilenstein erreicht, z.B. 5/10 Banken)

**Meilensteine feiern:**
- 🎉 **5 Banken** → Announcement in Discussions
- 🎉 **10 Banken** → Update in Haupt-README.md
- 🎉 **20 Banken** → Alle großen deutschen Banken abgedeckt

---

## 🔄 Regelmäßige Aufgaben

### Wöchentlich:
- [ ] Neue Issues mit Label `bank-integration` prüfen
- [ ] Offene Issues ohne Response nachfassen (nach 7 Tagen)

### Monatlich:
- [ ] Status-Übersicht aktualisieren
- [ ] Danke-Nachricht an alle Contributors (z.B. in Discussions)

### Bei Bedarf:
- [ ] Dokumentation verbessern (wenn häufige Rückfragen)
- [ ] Anonymisierungs-Guide erweitern (neue Edge Cases)

---

## 🙏 Danke!

Jeder Maintainer-Einsatz hilft, RechnungsFee besser für alle zu machen! 💪

Wenn du Verbesserungen für diesen Guide hast, ergänze sie gerne direkt! 🚀
