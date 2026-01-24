## 👋 Vielen Dank für deinen Feature-Request!

Das ist ein wichtiger Punkt für die Zukunftssicherheit von RechnungsFee. Ich habe deinen Vorschlag geprüft und möchte ein paar Punkte klarstellen und Rückfragen stellen.

---

## ✅ Gute Nachricht: CSV-Exporte sind bereits umfangreich geplant!

RechnungsFee wird **von Anfang an** umfangreiche Export-Funktionen haben:

### **v1.0 (MVP) - Bereits eingeplant:**
- ✅ **Kassenbuch-Export** → CSV
- ✅ **Eingangsrechnungen** → CSV/PDF
- ✅ **Ausgangsrechnungen** → CSV/PDF
- ✅ **Bank-Transaktionen** → CSV
- ✅ **Kundenstamm** → CSV/Excel
- ✅ **DATEV-Export** → CSV (für Steuerberater)
- ✅ **UStVA/EÜR-Export** → CSV/XML (für ELSTER)
- ✅ **EKS-Export** → CSV/Excel/PDF (für Jobcenter)

**Das heißt:** Du kannst alle Daten bereits **jetzt schon** in Excel/Google Sheets/LibreOffice Calc importieren und weiterverarbeiten! 🎉

### **v1.1 - Geplant:**
- 📋 **AGENDA-Export** - für AGENDA Steuerberatersoftware (Alternative zu DATEV)
- 📋 **Erweiterte Excel-Berichte** mit Diagrammen

---

## ⚠️ Klarstellung zu CAMT & OFX

Du hast **CAMT** und **OFX** als Exportformate vorgeschlagen. Das ist ein häufiges Missverständnis:

### **CAMT & OFX sind IMPORT-Formate (Bank → Software), nicht Export-Formate!**

- **CAMT.053** = ISO 20022 XML-Format für **Kontoauszüge von der Bank**
  - Verwendung: Bank sendet Kontoauszug → RechnungsFee importiert
  - ✅ Bereits als **Import-Format** für Bank-CSVs geplant

- **OFX** = Open Financial Exchange für **Bank-/Kreditkarten-Daten**
  - Verwendung: Bank exportiert → Quicken/GnuCash importiert
  - ✅ Ebenfalls als **Import-Format** geplant

**Diese Formate sind für den Import von Bank-Daten gedacht, NICHT für den Export von Buchhaltungsdaten an andere Programme!**

---

## 🤔 Rückfrage: Welche konkrete Software möchtest du nutzen?

Um deinen Bedarf besser zu verstehen:

**Welche Buchhaltungssoftware hast du im Blick?**
- [ ] **Lexware** (Buchhaltung, Faktura)
- [ ] **WISO** (Mein Büro, Steuer)
- [ ] **sevdesk** (Cloud-Buchhaltung)
- [ ] **MoneyMoney** (Mac Finanzsoftware)
- [ ] **GnuCash** (Open Source)
- [ ] **Andere:** [Bitte angeben]

**Oder geht es dir primär um:**
- [ ] Excel-Auswertungen (bereits gelöst durch CSV-Export)
- [ ] Datenumzug zu anderer Software (teilweise gelöst durch CSV-Export)
- [ ] Tabellenkalkulationen (bereits gelöst)

---

## 💡 Vorschlag: Generisches Export-Template-System (v2.0)

Basierend auf deinem Feedback plane ich ein neues Feature für **v2.0** ein:

### **Export-Template-Editor**

**Funktionsweise:**
1. User wählt Zielsoftware (z.B. "Lexware", "WISO", "sevdesk" oder "Andere")
2. RechnungsFee zeigt Template-Editor
3. Spalten-Mapping: RechnungsFee-Feld → Zielformat
4. Template speichern & wiederverwenden
5. Optional: Template mit Community teilen (GitHub)

**Vordefinierte Templates (Community):**
- Lexware-Import
- WISO-Import
- sevdesk-Import
- MoneyMoney-Import
- GnuCash-Import

**Vorteile:**
- ✅ Kein Vendor-Lock-In - jederzeit umsteigen möglich
- ✅ Benutzerfreundlich - einmal konfigurieren, dann automatisch
- ✅ Community-getrieben - Templates teilen und wiederverwenden
- ✅ Flexibel - jede Software unterstützbar

**Beispiel CSV-Export mit Template:**
```csv
Belegdatum;Belegnummer;Betrag;Konto;Gegenkonto;Buchungstext;USt
01.12.2025;RE-001;1190,00;8400;1200;Dienstleistung;19%
05.12.2025;ER-023;-250,00;4980;1576;Büromaterial;19%
```

---

## 🎯 Fazit & Nächste Schritte

### **Für dich:**
✅ **v1.0 (MVP):** CSV-Exporte decken Tabellenkalkulation bereits ab
📋 **v2.0:** Generisches Template-System für beliebige Buchhaltungssoftware

### **Meine Fragen an dich:**
1. Welche konkrete Buchhaltungssoftware möchtest du nutzen?
2. Reicht dir der CSV-Export für Excel/Google Sheets aus?
3. Oder brauchst du ein spezifisches Format für eine bestimmte Software?

### **Nächste Schritte:**
- Bitte beantworte die Rückfragen oben ☝️
- Basierend auf deinem Feedback plane ich das Feature konkret ein
- Ggf. kann ich bereits für v1.1 ein Template für deine Zielsoftware erstellen

---

## 📊 Priorität

Ich stufe das Feature als **Nice-to-have für v2.0** ein:
- **v1.0:** CSV-Export deckt Basis ab ✅
- **v1.1:** AGENDA-Export für Steuerberater 📋
- **v2.0:** Generisches Template-System für alle anderen 🔮

Falls du eine **konkrete Software** im Blick hast, die bereits für **v1.1** wichtig ist, lass es mich wissen! Dann können wir die Priorität anpassen.

---

## 🙏 Danke für deinen Input!

Dein Feature-Request hilft, RechnungsFee zukunftssicher und flexibel zu machen! 🚀

**Weiter so - jedes Feedback macht das Projekt besser!** 💪

---

**Weitere Infos:**
- [Detaillierte Analyse](./discussion-issue-13-export.md)
- [Dokumentation: Export-Funktionen](./docs/08-import.md)
- [CONTRIBUTING.md](./CONTRIBUTING.md)
