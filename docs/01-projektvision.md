# RechnungsFee - Claude Projektdokumentation

**Projekt:** RechnungsFee
**Typ:** Open-Source Buchhaltungssoftware
**Zielgruppe:** Freiberufler, Selbstständige, Kleinunternehmer
**Lizenz:** AGPL-3.0
**Status:** Konzeptphase
**Letzte Aktualisierung:** 2025-12-04

---

## **Projektvision**

RechnungsFee ist eine plattformunabhängige, Open-Source-Lösung für:
- Rechnungserfassung (Eingang & Ausgang)
- Kassenbuch-Führung
- Steuerdokumentengenerierung (EAR, EKS, UStVA, EÜR)
- DATEV/AGENDA-Export
- Bank-Integration
- Fokus auf §19 UStG und Regelbesteuerung

**Besonderheit:** Unterstützung für Selbstständige mit Transferleistungen (ALG II/Bürgergeld) durch EKS-Export.

---

## **Kernmerkmale**

### **Zwei Versionen:**
1. **Desktop-App** - Einfach installierbar für Laien (Windows/Mac/Linux)
2. **Docker-Version** - Für Power-User und Server-Betrieb

### **Technologie-Ansatz:**
- **Offline-First** - Volle Funktionalität ohne Internet
- **Plattformunabhängig** - Desktop hat Priorität
- **Mobile PWA** - Für schnelle Erfassung unterwegs
- **Multi-User** - Option für später offen halten

### **Funktionsumfang:**
✅ Eingangsrechnungen verwalten
✅ Ausgangsrechnungen verwalten
✅ Rechnungsschreiben (späteres Modul)
✅ Kassenbuch (EAR-konform, kein POS)
✅ Bank-Integration (CSV-Import, später API)
✅ Automatischer Zahlungsabgleich
✅ Steuerexporte (EAR, EKS, UStVA, EÜR)
✅ DATEV-Schnittstelle
✅ AGENDA-Schnittstelle (CSV)
✅ PDF/ZUGFeRD/XRechnung-Import mit OCR
✅ Kleinunternehmer (§19 UStG) & Regelbesteuerer

---

## **🎨 UI/UX-Richtlinien & Tonalität**

### **Ansprache: "Du" statt "Sie"**

**Entscheidung:** RechnungsFee verwendet durchgängig die **Du-Ansprache**.

**Begründung:**
- 💡 **Finanzen sind trocken** - Persönliche Ansprache macht es zugänglicher
- 👥 **Zielgruppe:** Freiberufler, Selbstständige, Kleinunternehmer - meist jüngere Generation
- 🤝 **Open Source Community** - "Du" ist Standard
- 🚀 **Moderne Software** - "Sie" wirkt altbacken und steif
- 💬 **Lockerer Ton** - Reduziert Hemmschwelle bei komplexen Steuerformularen

**Beispiele:**

| ❌ "Sie"-Formulierung | ✅ "Du"-Formulierung |
|----------------------|---------------------|
| "Bitte warten Sie..." | "Bitte warte..." |
| "Ihre Daten werden gespeichert" | "Deine Daten werden gespeichert" |
| "Wählen Sie ein Backup-Ziel" | "Wähle ein Backup-Ziel" |
| "Möchten Sie fortfahren?" | "Möchtest du fortfahren?" |
| "Ihre Rechnung wurde erstellt" | "Deine Rechnung wurde erstellt" |
| "Sie haben 3 neue Belege" | "Du hast 3 neue Belege" |
| "Bitte überprüfen Sie..." | "Bitte überprüfe..." |
| "Ihre Einstellungen wurden gespeichert" | "Deine Einstellungen wurden gespeichert" |

**Anwendungsbereiche:**
- ✅ Alle UI-Texte (Buttons, Menüs, Dialoge)
- ✅ Fehlermeldungen
- ✅ Hilfetexte und Tooltips
- ✅ Bestätigungsdialoge
- ✅ Onboarding-Screens
- ✅ Dokumentation (User-Handbuch)
- ✅ Changelog/Release Notes (soweit user-facing)

**Ausnahmen (formell bleiben):**
- ❌ Offizielle Dokumente (UStVA, EÜR, DATEV-Export) - hier gelten gesetzliche Vorgaben
- ❌ Externe API-Dokumentation (für Entwickler)
- ❌ Geschäftsbriefe/Rechnungen (sofern vom User erstellt - hier User-Einstellung)

### **Tonalität-Prinzipien**

1. **Freundlich, aber kompetent**
   - ✅ "Das Backup läuft. Dauert nur noch 30 Sekunden!"
   - ❌ "LOL, warte mal kurz! 😂"

2. **Klar und verständlich**
   - ✅ "Verschlüsselung schützt deine Daten bei Diebstahl"
   - ❌ "Encryption is mandatory pursuant to GDPR Art. 32"

3. **Hilfsbereit, nicht bevormundend**
   - ✅ "Tipp: Verschlüsselung ist für Kundendaten empfohlen"
   - ❌ "Du MUSST Verschlüsselung aktivieren!"

4. **Positiv formulieren**
   - ✅ "Backup erfolgreich! Deine Daten sind sicher."
   - ❌ "Fehler vermieden. Keine Probleme aufgetreten."

5. **Fehler menschlich kommunizieren**
   - ✅ "Ups! Die Verbindung zum NAS ist fehlgeschlagen. Prüfe bitte die Zugangsdaten."
   - ❌ "ERROR: SMB connection failed (errno 13)"

### **Emoji-Verwendung**

**Moderat einsetzen** - nur zur Orientierung, nicht übertreiben:

- ✅ **Icons in Dialogen:** 💾 Backup, ⚠️ Warnung, ✅ Erfolg, ❌ Fehler, ℹ️ Info
- ✅ **Kategorien/Menüs:** 📊 Berichte, ⚙️ Einstellungen, 🔐 Sicherheit
- ❌ **Nicht in Fließtext:** "Du hast 3 neue 📄 Belege 🎉🎉🎉"
- ❌ **Nicht in Fehlermeldungen:** "❌😱 Oh nein! ❌"

---

