# Offene Fragen zu RechnungsFee

## Status:
- ✅ Kategorie 1 (Kassenbuch) geklärt
- ✅ Kategorie 2 (PDF/E-Rechnungs-Import) geklärt
- ✅ Kategorie 3 (Anlage EKS) geklärt
- ✅ Kategorie 4 (DATEV-Export) geklärt
- ✅ Kategorie 5 (Bank-Integration) vollständig geklärt - 10 Banken, Auto-Erkennung, Matching
- ✅ Kategorie 6 (UStVA) vollständig geklärt - CSV/XML-Export, Kleinunternehmer, Zeiträume
- ✅ Kategorie 7 (EÜR) vollständig geklärt - Master-Kategorien, AfA-Rechner, Anlagenverwaltung
- ✅ Kategorie 8.1 (Unternehmerdaten) geklärt - 13 Pflichtfelder, 6 optional
- ✅ Kategorie 8.2 (Steuerliche Einstellungen) geklärt - USt-Status, Ist-Default, Dauerfrist, änderbar
- ✅ Kategorie 8.3 (Kontenrahmen) geklärt - Auto-Auswahl nach Rechtsform, nachträglich änderbar
- ✅ Kategorie 8.4 (Geschäftsjahr) geklärt - Standard Kalenderjahr, abweichendes optional, änderbar
- ✅ Kategorie 8.5 (Bank-/Konteneinrichtung) geklärt - Min. 1 Konto Pflicht, 4 Pflichtfelder, 3 Typen
- ✅ Kategorie 8.6 (Kundenstammdaten) vollständig geklärt - 9 Punkte inkl. VIES-API, Inland/EU/Drittland
- ✅ Kategorie 8.7 (Lieferantenstammdaten) geklärt - Ähnlich Kunden, einfacher, VIES-API
- ✅ Kategorie 8.8 (Artikel & Dienstleistungen) geklärt - Gemeinsamer Stamm, 3 Typen, EAN auch bei DL
- ✅ Kategorie 8.9 (Vereins-Buchhaltung) geklärt - 4 Sphären, SKR49, ermäßigter Steuersatz (v1.1+)
- ✅ Kategorie 10 (Backup & Update) vollständig geklärt - Frist-System, kein manueller Rollback
- ✅ Kategorie 12 (Hilfe-System) geklärt
- ✅ Kategorie 9 (Import-Schnittstellen) geklärt - v1.0 durch Kat. 2+5 abgedeckt, direkte APIs ab v1.1; Rechnungsmodul v1.0=LibreOffice-ODT-Vorlage, v1.1=eigenes Modul
- ✅ Kategorie 11 (Steuersätze) vollständig geklärt - 19%/7%/0%, historische Sätze, B2C brutto/B2B netto, Mischrechnung, Vorsteuer mit Teilabzug
- ✅ Kategorie 13 (Scope & Priorisierung) vollständig geklärt - Komfortables MVP, 9 Phasen
- ✅ GitHub Issue #14 (Rechnung AN Verein, §4 Nr. 21 UStG) analysiert - Steuer-Assistent v1.2, Bescheinigung im Kundenstamm v1.1

---

## **📋 Kategorie 2: PDF/E-Rechnungs-Import (ZUGFeRD, XRechnung)** ✅ GEKLÄRT

### **Formate:**

**Frage 2.1: Welche Versionen/Formate genau?**
- ZUGFeRD: Version 1.0, 2.0, 2.1, 2.2? Alle oder nur die aktuellste?
- XRechnung: Welche Version? (aktuell 3.0.2) Rückwärtskompatibilität?
- Factur-X (französisches ZUGFeRD) auch unterstützen?

**Frage 2.2: Import-Umfang:**
- Nur strukturierte Daten auslesen (XML aus PDF)?
- Oder auch PDF-Rendering zur Ansicht im Programm?
- Was wenn ZUGFeRD-Daten und PDF-Darstellung nicht übereinstimmen? Warnung? Welche Quelle ist "Wahrheit"?

**Frage 2.3: OCR bei normalen PDFs:**
- Wenn ein normales PDF (kein ZUGFeRD/XRechnung) importiert wird:
  - Automatisch OCR starten?
  - Oder nur manuell auf Wunsch?
  - Oder Vorschlag "OCR starten?" nach Import?

**Frage 2.4: Validierung:**
- Soll geprüft werden ob XRechnung/ZUGFeRD nach Standard valide ist?
- Was bei Fehlern/Warnungen: Abbruch oder trotzdem importieren mit Hinweis?
- Validierungsprotokoll anzeigen?

---

## **📋 Kategorie 3: Anlage EKS (Agentur für Arbeit)** ✅ GEKLÄRT

**Frage 3.1: EKS-Struktur:**
- Welche Kategorien müssen genau erfasst werden? (Hast du die aktuelle Liste?)
- Gibt es eine offizielle Vorlage/Spezifikation der Agentur für Arbeit?
- Meldungszeitraum: Monatlich, quartalsweise oder jährlich?

**Frage 3.2: Datenquellen:**
- Werden Ausgaben aus Eingangsrechnungen automatisch EKS-Kategorien vorgeschlagen?
- Oder manuelle Zuordnung pro Rechnung?
- Sollen Kostenstellen/Projekte dabei helfen?
- Einnahmen vs. Ausgaben: Beide in EKS oder nur Ausgaben?

**Frage 3.3: Export-Format:**
- Welches Format erwartet die Agentur für Arbeit?
  - PDF-Formular zum Ausdrucken?
  - CSV/Excel zum Hochladen?
  - Online-Formular (dann nur als Vorbereitung)?
  - ELSTER-ähnliche Integration?

**Frage 3.4: Besonderheiten:**
- Gibt es spezielle Kategorien die oft vergessen werden?
- Welche Fehler passieren häufig bei der EKS?
- Grenzwerte/Freibeträge die beachtet werden müssen?
- Zusammenhang mit Einkommensanrechnung bei ALG II/Bürgergeld?

---

## **📋 Kategorie 4: DATEV-Export** ✅ GEKLÄRT

### **Kontenrahmen:**

**Frage 4.1: SKR03 oder SKR04 oder beide?**
- Standardmäßig SKR03 (für Gewerbetreibende)?
- SKR04 (für Freiberufler)?
- Soll der Nutzer bei Einrichtung wählen können?
- Beide parallel möglich (falls jemand mehrere Firmen hat)?

**Frage 4.2: DATEV Kassenarchiv Online:**
- Hast du Dokumentation zu den Anforderungen?
- Welches Format: CSV, XML, oder proprietär?
- Braucht es spezielle Felder (Z-Bons, TSE-Daten) auch ohne POS?
- Ist das Prio 1 oder kann das später kommen?

**Frage 4.3: Buchungsstapel:**
- Sollen alle Belege eines Zeitraums exportiert werden?
- Automatische Konten-Zuordnung (z.B. Büromaterial → Konto 4910) oder muss der Nutzer Konten wählen?
- Wie detailliert: Pro Rechnungsposition oder nur Rechnungssummen?
- Soll/Haben-Buchungen automatisch generieren?

**Frage 4.4: DATEV-Format-Details:**
- CSV-DATEV oder anderes Format?
- Welche Felder sind Pflicht, welche optional?
- Buchungsschlüssel (BU-Schlüssel) automatisch setzen oder manuell?

---

## **📋 Kategorie 5: Bank-Integration (CSV-Import)** ✅ GEKLÄRT

### **CSV-Formate:**

**Frage 5.1: Welche Banken sind primär relevant?** ✅ GEKLÄRT

**Entscheidung: Alle vorhandenen Banken unterstützen**

**Unterstützte Banken (10):**
- [x] Commerzbank
- [x] DKB
- [x] ING (2 Varianten: normal + mit Saldo)
- [x] PayPal
- [x] Sparkasse LZO (3 Varianten: CAMT v2, CAMT v8, MT940)
- [x] Sparda-Bank West eG
- [x] Targobank Düsseldorf (+ Variation)
- [x] VR-Teilhaberbank

**Zusätzliche Formate:**
- [x] QIF-Import (targobank-duesseldorf.qif)
- [x] Excel/XLSX-Import (targobank-duesseldorf.xlsx)
- [x] MT940-Format (vr-teilhaberbank.mta)

**Fehlende Bank:**
- [x] Link zu GitHub Issue-Template → Nutzer kann Format beitragen

---

**Frage 5.2: CSV-Mapping** ✅ GEKLÄRT

**Entscheidung: Automatische Format-Erkennung**

- [x] **Automatisch:** Format wird anhand Header/Struktur erkannt
- [x] **Kein manuelles Mapping:** Nutzer muss NICHT Spalten zuordnen
- [x] **Template-System:** Für jede Bank ein Erkennungs-Template
- [x] **Fallback:** Wenn Format unbekannt → Hinweis + Issue-Template-Link

**Frage 5.3: Mehrkonten-Verwaltung** ✅ GEKLÄRT

**Entscheidung: Mehrere Konten mit automatischer Trennung**

**5.3.1: Anzahl Konten**
- [x] **Mehrere Konten** (flache Struktur, unbegrenzt)
- [x] Jedes Konto hat: Name, Bank, IBAN, Typ (Geschäftlich/Gemischt/Privat)
- [x] Beispiel: Sparkasse Geschäftskonto, ING Privat, PayPal

**5.3.2: Betrieblich vs. Privat - Trennung**
- [x] **Automatisch + Korrektur-Möglichkeit**
- [x] Bei Konto-Einrichtung: Typ wählen (Nur Geschäftlich / Gemischt / Nur Privat)
- [x] Bei "Gemischt": Standard = alle geschäftlich, einzelne als "privat" markierbar
- [x] Filter in Transaktionsliste: [✓] Geschäftlich [ ] Privat

**5.3.3: Import-Handling**
- [x] **Jedes Konto = separate CSV**
- [x] Konto auswählen → CSV hochladen → wird diesem Konto zugeordnet
- [x] Keine Mehrkonten-CSVs (zu komplex für v1.0)

**5.3.4: Kontenübergreifende Auswertung**
- [x] Gesamt-Saldo über alle Konten
- [x] Dashboard: "Einnahmen gesamt (alle Konten)"
- [x] EÜR/UStVA: Automatisch alle geschäftlichen Konten zusammenfassen

**Frage 5.4: Matching-Logik (Rechnung → Zahlung)** ✅ GEKLÄRT

**Entscheidung: Intelligentes Matching mit Vorschlagsliste**

**5.4.1: Matching-Kriterien (Kombiniert)**
- [x] **Priorität 1:** Betrag + Datum (±7 Tage) + Rechnungsnummer (RegEx im Verwendungszweck)
- [x] **Priorität 2 (Fallback):** Betrag + Datum (±7 Tage) + Lieferanten-Name (Fuzzy-Matching)
- [x] **Datums-Toleranz:** ±7 Tage (Rechnung → Zahlung kann verzögert sein)
- [x] **Fuzzy-Matching:** "REWE" ≈ "REWE GmbH & Co KG" (ähnlichkeitsbasiert)
- [x] **IBAN-Abgleich:** NICHT verwenden (zu unsicher, Lieferanten haben oft mehrere)

**5.4.2: Mehrere mögliche Matches**
- [x] **Vorschlagsliste zeigen** (Nutzer entscheidet)
- [x] Liste mit allen Kandidaten, Nutzer wählt den richtigen
- [x] Option "Keine davon" → bleibt ungematched

**5.4.3: Ungematche Zahlungen**
- [x] **Als "ungematched" markieren** (Tab/Badge: "Nicht zugeordnet: 5")
- [x] Nichts geht verloren, Nutzer kann später zuordnen
- [x] KEINE automatische Rechnungs-Erstellung (zu riskant)

**5.4.4: Manuelles Matching**
- [x] Nutzer kann jederzeit manuell Zahlung ↔ Rechnung zuordnen
- [x] Suchfeld/Liste bei "Nicht zugeordneten Zahlungen"
- [x] Auch bei automatisch gematchten: Zuordnung änderbar

**Frage 5.5: Import-Details & Duplikaterkennung** ✅ GEKLÄRT

**Entscheidung: Hybrid-Duplikaterkennung mit Schutz vor Doppelbuchung**

**Duplikat-Erkennung:**
- [x] **Strategie Hybrid:**
  1. Bank-ID vorhanden (z.B. Sparkasse CAMT `<TxId>`)? → Nutze diese
  2. Keine Bank-ID? → Hash verwenden: `SHA256(Betrag + Datum + Uhrzeit + Verwendungszweck + IBAN)`
- [x] **Uhrzeit einbeziehen** (wenn in CSV vorhanden) → verhindert doppelte Einkäufe am selben Tag

**Verhalten bei Duplikaten:**
- [x] **Automatisch überspringen** (keine Nutzer-Nachfrage bei jedem Duplikat)
- [x] **Log anzeigen:** "125 neue, 25 Duplikate übersprungen" + [Log anzeigen]-Button
- [x] **Bei 100% Duplikaten:** Warnung "Scheint bereits importiert, fortfahren?"

**Schutz vor Doppelbuchung:**
- [x] **Rechnung bereits "bezahlt"?** → Status kann nicht nochmal geändert werden
- [x] **Status-Prüfung** vor Zahlungsabgleich

**Weitere Import-Details:**
- [ ] Zeitraum-Filter beim Import? (nur neue Buchungen ab Datum X)
- [ ] Saldo-Prüfung? (stimmt Endstand mit CSV überein?)

---

## **📋 Kategorie 6: Umsatzsteuervoranmeldung (UStVA)** ✅ GEKLÄRT

**Frage 6.1: Umfang** ✅ GEKLÄRT

**Entscheidung: CSV/XML-Export + PDF-Vorschau (keine Direktanbindung in v1.0)**

- [x] **CSV/XML-Export für ELSTER:** Datei zum Upload in ELSTER-Portal
- [x] **PDF-Vorschau generieren:** Formular-Ansicht zum Prüfen/Archivieren
- [x] **Keine ELSTER-Direktanbindung** in v1.0 (zu komplex, später in v1.1+)
- [x] **Automatisch Kennziffern befüllen** aus Buchungen

---

**Frage 6.2: Sonderfälle** ✅ GEKLÄRT

**Entscheidung: Kleinunternehmer-Support + Warnungen für komplexe Fälle**

**Kleinunternehmer (§19 UStG):**
- [x] **Must-Have:** Checkbox bei Ersteinrichtung
- [x] Warnung: "Du musst keine UStVA abgeben" (nur Jahreserklärung)
- [x] Keine Umsatzsteuer auf Ausgangsrechnungen

**Reverse-Charge (§13b UStG):**
- [x] **v1.0:** Warnung anzeigen bei EU-IBAN
- [x] Hinweis: "Evtl. Reverse-Charge prüfen! Siehe Hilfe"
- [x] **v1.1:** Vollständige Unterstützung (Checkbox, automatische Kennziffern)

**Innergemeinschaftlicher Erwerb:**
- [x] **v1.0:** Warnung bei EU-Lieferanten
- [x] **v1.1:** Vollständige Unterstützung

**Ist-Versteuerung vs. Soll-Versteuerung:**
- [x] **Ist-Versteuerung** als Standard (wichtiger für Selbstständige)
- [x] Nur bezahlte Rechnungen zählen zur UStVA
- [x] **Soll-Versteuerung:** Später (v1.1) falls Bedarf

---

**Frage 6.3: Zeiträume** ✅ GEKLÄRT

**Entscheidung: Alle drei Modi + Dauerfristverlängerung**

- [x] **Monatlich:** Für Umsatz > 7.500€
- [x] **Quartalsweise:** Für Umsatz < 7.500€ (Q1, Q2, Q3, Q4)
- [x] **Jährlich:** Für Kleinunternehmer (§19 UStG)
- [x] **Dauerfristverlängerung:** Checkbox (1 Monat mehr Zeit)
- [x] **Nutzer wählt** bei Ersteinrichtung (keine automatische Erkennung)

---

**Frage 6.4: Voranmeldungsdaten & Berechnung** ✅ GEKLÄRT

**Entscheidung: Vollautomatische Berechnung aller Kennziffern**

**Wichtigste Kennziffern:**
- [x] **Kz. 81:** Umsätze 19% (aus Ausgangsrechnungen)
- [x] **Kz. 86:** Umsätze 7% (aus Ausgangsrechnungen)
- [x] **Kz. 35:** Umsätze 0% (z.B. EU-Lieferungen)
- [x] **Kz. 66:** Vorsteuer (aus Eingangsrechnungen)
- [x] **Kz. 83:** Umsatzsteuer 19% (automatisch: Kz. 81 × 0,19)
- [x] **Kz. 89:** Zahllast/Erstattung (automatisch berechnet)

**Zusätzliche Features:**
- [x] **Plausibilitätsprüfung:** Warnungen bei ungewöhnlichen Werten
- [x] **Vorjahresvergleich:** Optional anzeigen (v1.1)

---

## **📋 Kategorie 7: Einnahmenüberschussrechnung (EÜR)** ✅ GEKLÄRT

**Frage 7.1: EÜR-Umfang** ✅ GEKLÄRT

**Entscheidung: Vollständige Anlage EÜR mit ELSTER-Export**

- [x] **Vollständige Anlage EÜR:** ~30-40 relevante Zeilen befüllen
- [x] **CSV/XML-Export für ELSTER:** Datei zum Upload
- [x] **PDF-Vorschau generieren:** Zum Prüfen/Archivieren
- [x] **Nicht alle 100 Zeilen:** Nur relevante Zeilen für Selbstständige

**Wichtigste EÜR-Zeilen:**
- [x] Zeile 11-14: Betriebseinnahmen (19%, 7%, steuerfrei)
- [x] Zeile 15-60: Betriebsausgaben (kategorisiert)
- [x] Zeile 29: Abschreibungen (AfA)
- [x] Zeile 90-95: Gewinn/Verlust-Berechnung

---

**Frage 7.2: Betriebsausgaben-Kategorien** ✅ GEKLÄRT

**Entscheidung: Master-Kategorien-System (integriert mit EKS, DATEV, EÜR)**

**Konzept: Ein Kategoriensystem für ALLES**
- [x] **~25-30 Kategorien** (basierend auf claude.md Master-Tabelle)
- [x] **Gruppiert** für bessere Übersicht (Menschen, nicht KIs 😉)
- [x] **Automatisches Mapping:** 1x kategorisieren → automatisch korrekt für EÜR, EKS, DATEV, UStVA

**Zwei Modi (wählbar in Einstellungen):**

**Standard-Modus (empfohlen):**
- [x] Einfache Kategorien-Liste mit 🏷️-Markierung
- [x] Bei 🏷️ + Betrag > 1.000€ → Automatischer Dialog "Anlage?"
- [x] Für Einsteiger & die meisten Nutzer

**Experten-Modus:**
- [x] Separate Anlagen-Kategorien sichtbar
- [x] Keine Dialoge, direkte Auswahl
- [x] Für Power-User

**Kategorien-Gruppen:**
```
📦 Wareneinkauf & Material
👥 Personal
🏢 Raumkosten
🚗 Fahrzeugkosten (mit 🏷️ Kfz-Anschaffung)
💻 IT & Büro (mit 🏷️ Computer/IT, 🏷️ Büromöbel)
🔧 Werkzeuge & Maschinen (mit 🏷️ Werkzeuge/Maschinen)
✈️ Reisen & Werbung
📚 Beratung & Fortbildung
💰 Sonstiges
🏗️ Anlagen (separate Gruppe für Experten-Modus)
```

**Prüfung während Entwicklung:**
- [x] Kategorien-Vollständigkeit kontinuierlich prüfen (Phase 5: EÜR-Export)
- [x] Testen mit realen Daten
- [x] Beta-Feedback einholen

---

**Frage 7.3: Anlagenverwaltung** ✅ GEKLÄRT

**Entscheidung: Vollständiger AfA-Rechner mit zweistufigem Ansatz**

**GWG-Grenze:**
- [x] **Aktuell: 1.000€** (netto)
- [x] **Updatefähig:** Nicht hardcoded, in Datenbank
- [x] **In Einstellungen konfigurierbar**
- [x] **Automatische Updates** bei Gesetzesänderung
- [x] **Historische Werte** bleiben erhalten (Zeitstempel)

**AfA-Rechner:**
- [x] **Anlagenverzeichnis führen** (Name, Wert, Kaufdatum, AfA-Dauer)
- [x] **Automatische AfA-Berechnung** (jährlich)
- [x] **Integration in EÜR** (Zeile 29: Abschreibungen)
- [x] **AfA-Dauer vorschlagen** (Computer 3J, Möbel 13J, KFZ 6J)

**Zweistufiger Ansatz (Ansatz 4):**
- [x] **Schritt 1:** Kategorie mit 🏷️-Markierung (z.B. "💻 Computer/IT 🏷️")
- [x] **Schritt 2:** Bei > 1.000€ → Dialog: "Sofort absetzen (GWG)" oder "Als Anlage (AfA)"
- [x] **Nur bei relevanten Kategorien** (nicht nervig)
- [x] **Nutzer wird geführt** zur richtigen Wahl

**EKS-Besonderheit (Jobcenter-Genehmigung):**
- [x] **Warnung beim EKS-Export** (einmalig): "Anschaffungen müssen vorher genehmigt sein"
- [x] **Ausführlich im Handbuch** (Rechtshinweise, Genehmigungspflicht)
- [x] **Optional: Tooltip bei Erfassung** (wenn EKS aktiviert)

**EKS-Mapping:**
- [x] **Anlagen:** EKS Tabelle B8 (Investitionen)
- [x] **Abschreibungen:** EKS Tabelle C (C1-C6: Absetzungen)
- [x] **GWG:** Normale Betriebsausgaben (z.B. B9 Büromaterial)

---

**Frage 7.4: Zufluss-/Abflussprinzip** ✅ GEKLÄRT

**Entscheidung: Automatisch nach Zahlungsdatum mit Warnungen**

- [x] **Automatisch nach Zahlungsdatum buchen** (nicht Rechnungsdatum)
- [x] **Zufluss-/Abflussprinzip:** Nur Geldflüsse zählen für EÜR
- [x] **Warnung bei Jahreswechsel:**
  ```
  ⚠️ Rechnung 2024, Zahlung 2025
     "Diese Rechnung zählt zur EÜR 2025, nicht 2024!"
  ```
- [x] **Datum der Zahlung entscheidend** (aus Bank-Import)

---

## **📋 Kategorie 8: Stammdaten-Erfassung (Ersteinrichtung)** ✅ GEKLÄRT

**Frage 8.1: Unternehmerdaten - welche Felder?** ✅ GEKLÄRT

**Entscheidung: Optimierte Stammdaten-Erfassung**

**Pflichtfelder (ohne geht's nicht):**

**Grunddaten:**
- [x] **Name des Unternehmens** * (Pflicht)
- [x] **Rechtsform** * (Dropdown: Einzelunternehmer, GbR, UG, GmbH, AG, e.K., Freiberufler, Eingetragener Verein (e.V.), Sonstige)
- [x] **Straße** * (Pflicht)
- [x] **Hausnummer** * (Pflicht)
- [x] **PLZ** * (Pflicht)
- [x] **Stadt** * (Pflicht)

**Ansprechpartner:**
- [x] **Vorname** * (Pflicht)
- [x] **Nachname** * (Pflicht)
- [x] **E-Mail** * (Pflicht - wichtig für Kommunikation, Updates)

**Steuer:**
- [x] **Umsatzsteuer-Status** * (Dropdown: Regelbesteuerung / Kleinunternehmer §19 UStG / Befreit)
- [x] **Steuernummer** * (Pflicht - vom Finanzamt)
  - Validierung: Altes Format (bundesland-spezifisch, z.B. 123/456/78901) UND neues Format (13-stellig einheitlich, z.B. 2893081508152)
  - Software muss BEIDE Formate akzeptieren und validieren
- [x] **Zuständiges Finanzamt** * (Dropdown oder PLZ-basierte Auswahl)

---

**Optionale Felder (können später ergänzt werden):**

**Kontakt:**
- [x] Telefonnummer (optional)
- [x] Webseite (optional)

**Steuer (optional):**
- [x] **USt-ID** (nur bei EU-Geschäften erforderlich)

**Weitere:**
- [x] **Handelsregisternummer** (nur bei GmbH, UG, AG - Pflicht bei diesen Rechtsformen)
- [x] **Branche** (optional, evtl. für EKS-Export hilfreich)

**Bank:**
- [x] **IBAN** (optional, aber sinnvoll für Bank-CSV-Zuordnung)
- [x] **BIC** (optional)

---

**Weglassen (nicht erforderlich):**
- [x] ❌ **Faxnummer** (veraltet, 2024 kaum noch relevant)
- [x] ❌ **Unternehmensbeschreibung** (unklar wofür, kein konkreter Nutzen)

---

**Rechtsform-abhängige Felder:**
```
Bei Auswahl von GmbH, UG, AG:
→ Handelsregisternummer wird Pflichtfeld

Bei Auswahl von Einzelunternehmer, Freiberufler:
→ Handelsregisternummer ausgeblendet
```

---

**Wichtige Klarstellung:**
- [x] ⚠️ **KEIN Z-Bon beim Speichern der USt-ID!**
  - Z-Bon = Tagesabschluss bei Kassensystemen (nicht relevant für RechnungsFee v1.0)
  - USt-ID wird einfach als Text gespeichert
  - Keine TSE/Kassensystem-Funktionen in v1.0

**Frage 8.2: Steuerliche Einstellungen** ✅ GEKLÄRT

Diese Einstellungen werden bei der **Ersteinrichtung** festgelegt und beeinflussen UStVA, EÜR und alle Buchungen.

**⚠️ WICHTIG:** Alle Einstellungen können später in den Einstellungen geändert werden!

---

### **1. Umsatzsteuer-Status**

**Radio-Button:**
- [x] **Kleinunternehmer (§19 UStG)** - keine Umsatzsteuer
  - Umsatz < 25.000€/Jahr (ab 2025, vorher 22.000€) → keine USt ausweisen, keine Vorsteuer abziehen
  - **Warnung bei Auswahl:**
    ```
    ⚠️ Als Kleinunternehmer:
    - Du kannst keine Vorsteuer geltend machen
    - Du kannst keine Rechnung mit Mehrwertsteuer schreiben
    - Du musst auf Rechnungen den §19 UStG-Hinweis angeben
    ```
- [x] **Regelbesteuerung (19%)** - mit Umsatzsteuer
  - Standard für die meisten Unternehmen → USt ausweisen, Vorsteuer abziehen
- [x] **Gemeinnützig (ermäßigt 7%)** - für Vereine
  - Für gemeinnützige, kirchliche oder mildtätige Vereine (e.V.)
  - Ermäßigter Steuersatz 7% für Zweckbetrieb
  - Ideeller Bereich und Vermögensverwaltung USt-frei
  - **Hinweis bei Auswahl:**
    ```
    ℹ️ Als gemeinnütziger Verein:
    - Mitgliedsbeiträge & Spenden: USt-frei (ideeller Bereich)
    - Gemeinnützige Tätigkeiten (Zweckbetrieb): 7% USt
    - Wirtschaftlicher Geschäftsbetrieb: 19% USt
    - Kleinunternehmerregelung (§19) kann zusätzlich gewählt werden
    ```
  - **Nur sichtbar wenn:** Rechtsform "Eingetragener Verein (e.V.)" gewählt

**Hilfetext:** Link zur IHK/Steuerberater-Info für Erklärung

**Auswirkungen:**
- Kleinunternehmer: Alle Rechnungen ohne USt, keine UStVA-Pflicht (aber möglich für EU-Geschäfte!)
- Regelbesteuerung: UStVA Pflicht, Vorsteurabzug möglich
- Gemeinnützig: UStVA Pflicht (je nach Sphären), Vorsteurabzug möglich, ermäßigter Steuersatz 7% für Zweckbetrieb

**Änderbar:** Jährlich (wenn Umsatzgrenze überschritten/unterschritten) bzw. bei Verlust/Erhalt Gemeinnützigkeit

---

### **2. Voranmeldungszeitraum** (nur bei Regelbesteuerung + Gemeinnützig)

**Dropdown:**
- [x] Monatlich (Pflicht in ersten 2 Jahren + wenn Vorauszahlung >7.500€/Jahr)
- [x] Vierteljährlich (Ab 3. Jahr + wenn Vorauszahlung ≤7.500€/Jahr)
- [x] Jährlich (Nur für Kleinunternehmer, kleine Vereine oder bei Dauerfristverlängerung + geringer Last)

**Smart Default:**
- Unternehmen: "Monatlich" (sicher für Neugründer)
- Vereine: "Vierteljährlich" (typisch für kleine gemeinnützige Vereine)

**Hilfetext:**
- Unternehmen: "Im ersten und zweiten Jahr meist monatlich, danach vierteljährlich möglich"
- Vereine: "Kleine Vereine können vierteljährlich oder jährlich melden (abhängig von Umsätzen)"

**Nur sichtbar wenn:** "Regelbesteuerung" oder "Gemeinnützig" gewählt

**Änderbar:** Jederzeit in Einstellungen

---

### **3. Versteuerungsart** (nur bei Regelbesteuerung + Gemeinnützig)

**Radio-Button:**
- [x] **Ist-Versteuerung (DEFAULT)** - USt wird fällig bei **Zahlungseingang**
  - Für Freiberufler, Kleinunternehmer und Vereine <800.000€ Umsatz
  - Vorteil: Liquidität (USt erst zahlen wenn Kunde bezahlt hat)
  - Empfohlen für Vereine (typisch bei Mitgliedsbeiträgen, Kursgebühren)
- [x] **Soll-Versteuerung** - USt wird fällig bei **Rechnungsstellung**
  - Standard für GmbH, UG (Pflicht!)
  - Nachteil: USt zahlen auch wenn Kunde noch nicht bezahlt hat

**Intelligente Vorauswahl basierend auf Rechtsform (8.1):**
- Freiberufler → Default: **Ist-Versteuerung** ✅
- Einzelunternehmer → Default: **Ist-Versteuerung** ✅
- Eingetragener Verein (e.V.) → Default: **Ist-Versteuerung** ✅
- GmbH, UG, AG → Default: Soll-Versteuerung (dann gesperrt/Pflicht)

**Hinweis bei Ist-Versteuerung:**
```
ℹ️ Bei Ist-Versteuerung:
- UStVA rechnet nur bezahlte Rechnungen
- Liquiditätsvorteil
- Nur für Freiberufler/Kleinunternehmer <800.000€
```

**Wichtig für RechnungsFee:**
- Bei Ist-Versteuerung: UStVA berücksichtigt nur bezahlte Rechnungen
- Bei Soll-Versteuerung: UStVA berücksichtigt alle gestellten Rechnungen

**Änderbar:** Mit Zustimmung Finanzamt (meist nur zu Jahresbeginn)

---

### **4. Dauerfristverlängerung** (nur bei Regelbesteuerung)

**Checkbox:**
- [x] ☐ Dauerfristverlängerung beantragt

**Bedeutung:**
- +1 Monat mehr Zeit für UStVA
- Frist: vom 10. des Folgemonats → 10. des übernächsten Monats
- Kostet: Sondervorauszahlung (1/11 der Vorjahres-USt-Last)
- Muss beim Finanzamt beantragt werden

**Hilfetext:** "Gibt dir 1 Monat mehr Zeit für die UStVA. Muss beim Finanzamt beantragt werden."

**Hinweis bei Aktivierung:**
```
⚠️ Beachte bei Dauerfristverlängerung:
- Frist verlängert sich von 10. auf 10. des Folgemonats
- Sondervorauszahlung fällig (wird im Dezember verrechnet)
- Gilt für das gesamte Kalenderjahr
- Antrag muss beim Finanzamt gestellt werden
```

**Änderbar:** Zum Jahresbeginn (mit Antrag beim Finanzamt)

---

### **UI-Vorschlag für Ersteinrichtung:**

```
┌─ Steuerliche Einstellungen ───────────────────────┐
│                                                    │
│ Umsatzsteuer-Status:                               │
│ ○ Kleinunternehmer (§19 UStG)                      │
│   → Keine Umsatzsteuer, kein Vorsteuerabzug        │
│                                                    │
│ ● Regelbesteuerung                                 │
│   → Mit Umsatzsteuer und Vorsteuerabzug            │
│                                                    │
│ ┌─────────────────────────────────────────────┐   │
│ │ Voranmeldungszeitraum: [Monatlich      ▼]  │   │
│ │ ℹ️ Im 1.+2. Jahr meist monatlich           │   │
│ │                                             │   │
│ │ Versteuerungsart:                           │   │
│ │ ● Ist-Versteuerung (bei Zahlungseingang)   │   │
│ │ ○ Soll-Versteuerung (bei Rechnungsstellung)│   │
│ │ ℹ️ Ist-Versteuerung empfohlen (Liquidität) │   │
│ │                                             │   │
│ │ ☐ Dauerfristverlängerung beantragt         │   │
│ │ ℹ️ +1 Monat Zeit, Sondervorauszahlung      │   │
│ └─────────────────────────────────────────────┘   │
│                                                    │
│ ⚙️ Hinweis: Alle Einstellungen können später      │
│   in den Einstellungen geändert werden.           │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

### **Warnung bei Kleinunternehmer-Auswahl:**

```
┌─ ⚠️ Wichtiger Hinweis ────────────────────────────┐
│                                                    │
│ Als Kleinunternehmer (§19 UStG) beachte:          │
│                                                    │
│ ❌ Du kannst KEINE Vorsteuer geltend machen       │
│ ❌ Du kannst KEINE Rechnung mit Mehrwertsteuer    │
│    schreiben                                       │
│ ℹ️ Du musst auf Rechnungen den §19 UStG-Hinweis  │
│    angeben                                         │
│                                                    │
│ ✅ Vorteil: Vereinfachte Buchhaltung              │
│ ✅ Vorteil: Keine UStVA (außer bei EU-Geschäften) │
│                                                    │
│ Mehr Infos: [Link zur IHK/Steuerberater-Info]     │
│                                                    │
│         [Zurück]    [Trotzdem wählen]             │
└────────────────────────────────────────────────────┘
```

**Frage 8.3: Kontenrahmen** ✅ GEKLÄRT

**Entscheidung: Intelligente Defaults basierend auf Rechtsform**

- [x] **Automatische Auswahl basierend auf Rechtsform (aus 8.1):**
  - **Freiberufler** → SKR04 (Standard-Kontenrahmen für Freiberufler)
  - **Eingetragener Verein (e.V.)** → SKR49 (Standard-Kontenrahmen für Vereine)
  - **Einzelunternehmer, GbR, UG, GmbH, AG, e.K., Sonstige** → SKR03 (Standard-Kontenrahmen für Gewerbetreibende)
- [x] **Nachträglich änderbar** in Einstellungen
- [x] **Keine Auswahl bei Einrichtung nötig** - Vereinfacht Setup für Laien
- [x] **Keine Erklärung erforderlich** - System wählt automatisch den richtigen

**Vorteil:** Nutzer braucht kein Wissen über Kontenrahmen - das System entscheidet basierend auf der bereits erfassten Rechtsform.

**SKR49 für Vereine:**
- Speziell für gemeinnützige Vereine entwickelt
- Bildet die 4 Sphären der Vereinstätigkeit ab (ideeller Bereich, Vermögensverwaltung, Zweckbetrieb, wirtschaftlicher Geschäftsbetrieb)
- Vereinfachte Trennung für Steuererklärung und Gemeinnützigkeitsnachweis

**Frage 8.4: Geschäftsjahr** ✅ GEKLÄRT

**Entscheidung: Kalenderjahr als Standard, abweichendes Wirtschaftsjahr optional**

- [x] **Standard: Kalenderjahr** (01.01. - 31.12.)
  - Für die meisten Selbstständigen und Freiberufler
  - Automatisch voreingestellt
- [x] **Abweichendes Wirtschaftsjahr möglich**
  - Bei Einstellung Dauerfristverlängerung aktivierbar
  - Wichtig für EÜR und Jahresabschluss
- [x] **Nachträglich änderbar** in Einstellungen
  - Kann jederzeit angepasst werden

**Auswirkungen:**
- Bestimmt den Zeitraum für EÜR-Export
- Relevant für Jahresabschluss und Steuererklärung
- Bei abweichendem Wirtschaftsjahr: Besondere Berücksichtigung bei UStVA

**Frage 8.5: Bank-/Konteneinrichtung** ✅ GEKLÄRT

**Entscheidung: Mindestens ein Konto bei Ersteinrichtung erforderlich**

**Begründung:**
- ❌ Ohne Konto: Exporte nicht möglich (UStVA, EÜR, DATEV)
- ❌ Ohne Konto: Kontoabgleich nicht möglich
- ❌ Ohne Konto: Bank-CSV-Import nicht zuordenbar
- ✅ **Mindestens eine Bankverbindung = Pflicht**

---

### **Pflichtfelder pro Konto:**

- [x] **Kontoinhaber** (Pflicht)
  - Muss **exakt** wie bei der Bank hinterlegt sein
  - Wichtig für SEPA-Mandate und Abgleich
  - Beispiel: "Max Mustermann" oder "Mustermann GmbH"
- [x] **Bankname** (Pflicht)
  - z.B. "Sparkasse Musterstadt", "GLS Bank", "ING"
  - Für Übersichtlichkeit und Zuordnung
- [x] **IBAN** (Pflicht)
  - Validierung: DE + 20 Zeichen (oder andere Länder-Formate)
  - Eindeutig identifizierbar
- [x] **Kontotyp** (Pflicht - Dropdown)
  - **Geschäftskonto** - nur geschäftliche Transaktionen
  - **Mischkonto** - privat + geschäftlich gemischt (Filter beim Import)
  - **Privatkonto** - nur private Transaktionen (nicht importierbar)
  - Wichtig für SEPA-Mandate-Zuordnung und Transaktionsfilterung

---

### **Optionale Felder:**

- [x] **BIC** (optional)
  - Für internationale Überweisungen
  - Oft automatisch aus IBAN ableitbar
- [x] **Kontoname** (optional)
  - Interne Bezeichnung, z.B. "Hauptgeschäftskonto", "PayPal Business"
  - Für bessere Übersicht bei mehreren Konten

---

### **Workflow bei Ersteinrichtung:**

```
Schritt 7: Bankverbindung einrichten

⚠️ Mindestens ein Konto erforderlich

┌─────────────────────────────────────────────┐
│ Kontoinhaber: [Max Mustermann e.K.    ]   │
│ Bankname:     [Sparkasse Musterstadt  ]   │
│ IBAN:         [DE89370400440532013000 ]   │
│ BIC:          [COBADEFFXXX            ]   │ (optional)
│                                             │
│ Kontotyp:     [Geschäftskonto       ▼]    │
│               ○ Geschäftskonto              │
│               ○ Mischkonto (privat+geschäft)│
│               ○ Privatkonto                 │
│                                             │
│ Kontoname:    [Hauptkonto             ]   │ (optional)
│                                             │
│ [ + Weiteres Konto hinzufügen ]            │
│                                             │
│         [Zurück]    [Weiter]               │
└─────────────────────────────────────────────┘
```

---

### **Mehrere Konten möglich:**

- [x] Nutzer kann mehrere Konten anlegen (z.B. Sparkasse + PayPal)
- [x] Button "Weiteres Konto hinzufügen" verfügbar
- [x] Aber: **Mindestens eines ist Pflicht**
- [x] Weitere Konten können später in Einstellungen hinzugefügt werden

---

### **Verwendung der Kontotypen:**

**Geschäftskonto:**
- Alle Transaktionen werden als geschäftlich importiert
- Keine Filter-Dialoge beim Import
- Standard für Selbstständige

**Mischkonto:**
- Bei CSV-Import: Dialog zur Auswahl geschäftlich/privat
- System lernt aus Entscheidungen (Smart Filter)
- Für Selbstständige mit gemischter Kontonutzung

**Privatkonto:**
- Kann nicht für Bank-CSV-Import verwendet werden
- Nur für Übersicht/spätere Nutzung
- Warnung: "Privatkonten können nicht importiert werden"

---

**Wichtig für SEPA-Mandate:**
- Kontoinhaber muss exakt mit SEPA-Mandaten übereinstimmen
- Bei Abweichung: Fehlgeschlagene Lastschriften möglich
- System warnt bei Abweichungen

**Frage 8.6: Kundenstammdaten - Felder:** ✅ GEKLÄRT

**Punkt 1: Pflichtfelder** ✅
- **Privatkunde:**
  - Vorname, Nachname (Pflicht)
  - E-Mail (Pflicht)
  - Straße, Hausnummer, PLZ, Ort, Land (Pflicht)
  - Telefon (Optional)
- **Geschäftskunde (B2B):**
  - Firma (Pflicht)
  - E-Mail (Pflicht)
  - Straße, Hausnummer, PLZ, Ort, Land (Pflicht)
  - Ansprechpartner (ALLE optional):
    - Vorname, Nachname
    - Telefon, E-Mail
    - Messenger-Kontakt (z.B. WhatsApp, Signal, Telegram)

**Punkt 2: Kundennummer** ✅
- **v1.0:** Automatisch (Format: KD-00001, KD-00002, KD-00003...)
- **v1.1+:** Format konfigurierbar (z.B. KD-{YYYY}-{###})

**Punkt 3: Kundentyp** ✅
- **Entscheidung:** Option A - Explizite Unterscheidung
- Auswahlfeld: "Privatkunde" / "Geschäftskunde"
- Bestimmt Pflichtfelder im Formular

**Punkt 3a: Steuernummer/UID bei B2B** ✅
- Bei **Geschäftskunden (B2B):** Mindestens **EINES** ist Pflicht:
  - Steuernummer (national) ODER
  - USt-IdNr. (EU-weit)
- Begründung: Distributoren/Großhändler benötigen diese für Rechnungsstellung
- **Validierung Steuernummer:**
  - Altes Format: Bundesland-spezifisch (z.B. 123/456/78901)
  - Neues Format: 13-stellig einheitlich (z.B. 2893081508152)
  - Software muss BEIDE Formate akzeptieren und validieren

**Punkt 3b: Zweite Adresse (Privatadresse)** ✅
- **v1.0:** Einfaches Zusatzfeld-Set (ALLE optional):
  - Privat-Straße
  - Privat-Hausnummer
  - Privat-PLZ
  - Privat-Ort
  - Privat-Land
- **v1.1+:** Tab-basierte Adressverwaltung:
  - Lieferadresse
  - Rechnungsadresse
  - Mehrere Ansprechpartner mit eigenen Adressen

**Punkt 4: Zahlungsziel** ✅
- Feld: "Zahlungsziel (Tage)" - Integer
- Default: 14 Tage
- Wird bei Ausgangsrechnungen als Vorschlag übernommen
- Kann pro Rechnung überschrieben werden
- Skonto-Regelung → **v1.1+** (zu komplex für v1.0)

**Punkt 5: Kategorisierung Inland/EU/Drittland** ✅
- **Entscheidung:** Option A - Automatische Erkennung
- Basierend auf Feld "Land" (Dropdown ISO-Codes: DE, AT, FR, CH, US...)
- Software erkennt automatisch:
  - Land = DE → **Inland** (Standard-USt 19%/7%)
  - Land in EU-Liste (27 Länder) → **EU**
    - B2B + gültige UID → Reverse-Charge (§13b UStG, 0% USt)
    - B2C ohne UID → wie Inland (19%/7%)
  - Land nicht in EU → **Drittland** (Exportumsatz §4 Nr. 1a UStG, 0% USt)
- Automatische Plausibilitätsprüfung und Hinweise

**Punkt 6: USt-IdNr.-Prüfung über EU-API** ✅
- **Entscheidung:** Option B - Manuelle Prüfung on-demand
- Button "UID prüfen" im Formular
- API: VIES (VAT Information Exchange System)
- Endpunkt: `https://ec.europa.eu/taxation_customs/vies/rest-api/`
- Ergebnis wird gespeichert (✅ Gültig / ❌ Ungültig + Zeitstempel)
- Nutzer entscheidet, wann geprüft wird (keine automatische Wartezeit)

**Punkt 7: Notizen/Bemerkungsfeld** ✅
- Freitextfeld "Notizen" (optional, unbegrenzt)
- Einfaches aufziehbares Textfeld (Textarea)
- Nur intern sichtbar (erscheint nicht auf Rechnungen)
- Verwendung: Interne Vermerke (z.B. "Kunde zahlt immer pünktlich", "Preisabsprache vom...")

**Punkt 8: Aktiv/Inaktiv Status** ✅
- Checkbox "Aktiv" (Standard: ✅ aktiviert)
- Inaktive Kunden:
  - Werden in Dropdown-Listen ausgegraut oder ausgeblendet
  - Bleiben in Historie sichtbar (GoBD!)
  - Können jederzeit reaktiviert werden
- Filter-Option: "Nur aktive Kunden anzeigen"
- **Wichtig:** Keine Löschung (GoBD-Konformität)

**Punkt 9: Erstellungs-/Änderungsdatum (Metadaten)** ✅
- `created_at` - Zeitpunkt des Anlegens (automatisch)
- `updated_at` - Letzte Änderung (automatisch)
- Nicht editierbar, nur Anzeige
- **Unbedingt erforderlich** für GoBD-Konformität und Nachvollziehbarkeit

**Frage 8.7: Lieferantenstammdaten** ✅ GEKLÄRT

**Struktur: Ähnlich wie Kundenstamm, aber einfacher (keine B2B/B2C-Unterscheidung)**

### **Pflichtfelder (minimal):**
- [x] **Firma** (Pflicht)
- [x] **Adresse:**
  - Straße + Hausnummer (Pflicht)
  - PLZ (Pflicht)
  - Ort (Pflicht)
  - Land (Pflicht - Default: DE)
- [x] **E-Mail** (Pflicht - für Kommunikation)

### **Automatische Felder:**
- [x] **Lieferantennummer** - automatisch (LF-00001, LF-00002, LF-00003...)
  - Format wie Kundennummer
  - v1.1+: Konfigurierbar (z.B. LF-{YYYY}-{###})

### **Optionale Felder:**

**Kontakt:**
- [x] Telefon
- [x] Webseite (URL)
- [x] Webshop (URL)

**Geschäftsbeziehung:**
- [x] Lieferanten-Kundennummer (unsere Kundennummer beim Lieferanten)
  - Beispiel: "KD-123456" bei Amazon Business

**Steuerliche Daten:**
- [x] Steuernummer (national)
  - Validierung: Altes Format (bundesland-spezifisch) UND neues Format (13-stellig)
- [x] **USt-ID** (Umsatzsteuer-Identifikationsnummer, EU-weit)
  - VIES-API-Prüfung: Manueller Button "UID prüfen" (wie bei Kunden)
  - Ergebnis wird mit Zeitstempel gespeichert
- [x] Handelsregisternummer (optional)

**Ansprechpartner (ALLE optional):**
- [x] Kontaktperson (Name)
- [x] Kontaktperson Telefon
- [x] Kontaktperson E-Mail

**Sonstiges:**
- [x] Beschreibung/Notizen (Textarea, unbegrenzt)
  - Nur intern sichtbar
  - Beispiel: "Zahlungsziel 30 Tage", "Liefert nur dienstags", etc.

### **Status & Kategorisierung:**
- [x] **Aktiv/Inaktiv** - Checkbox (Standard: ✅ aktiviert)
  - Inaktive Lieferanten ausblenden, nicht löschen (GoBD!)
- [x] **Inland/EU/Drittland** - automatische Erkennung basierend auf Land-Feld
  - Land = DE → Inland
  - Land in EU → EU
  - Land außerhalb EU → Drittland
  - Wichtig für Reverse-Charge bei Rechnungen von EU-Lieferanten

### **Metadaten (GoBD):**
- [x] `created_at` - Zeitpunkt des Anlegens (automatisch)
- [x] `updated_at` - Letzte Änderung (automatisch)
- [x] Nicht editierbar, nur Anzeige
- [x] **Unbedingt erforderlich** für GoBD-Konformität

---

**Unterschiede zu Kundenstammdaten:**
- ❌ Keine B2B/B2C-Unterscheidung (alle Lieferanten = B2B)
- ❌ Keine Privatadresse (nur Geschäftsadresse)
- ❌ Kein Zahlungsziel (wir bekommen Rechnungen mit vorgegebenem Zahlungsziel)
- ✅ Zusatzfelder: Webshop, Lieferanten-Kundennummer
- ✅ Einfacher und schlanker

**Frage 8.8: Artikel- & Dienstleistungsstammdaten** ✅ GEKLÄRT

**Entscheidung: Gemeinsamer Stamm mit Typ-Unterscheidung (Option A)**

Ein gemeinsamer Stamm für Produkte UND Dienstleistungen mit intelligenter Typ-Unterscheidung.

Bereits in v1.0 vollständig implementiert für:
- Ausgangsrechnungen erfassen (Should-Have v1.0)
- Vorbereitung für Rechnungsschreib-Modul (v1.1+)
- Nachbestellung und Rechnungssuche
- Scanlisten (EAN-Erfassung auch bei Dienstleistungen!)

---

### **Typ-Auswahl (bestimmt verfügbare Felder):**

**1. Produkt** (physische Ware)
- Alle Felder verfügbar
- Mit Hersteller, Artikelcode, Lieferant, EAN

**2. Dienstleistung - Eigenleistung** (selbst erbracht)
- Nur VK (Verkaufspreis) relevant
- Kein EK (Einkaufspreis)
- Kein Lieferant/Hersteller
- EAN möglich (für Scanlisten!)

**3. Dienstleistung - Fremdleistung** (eingekauft, weitergegeben)
- EK + VK relevant (Marge berechnen)
- Lieferant = Dienstleister (Subunternehmer)
- **Artikelnummer = Artikelnummer des Dienstleisters!**
- Wichtig für Reverse-Charge bei ausländischen Dienstleistern

---

### **Pflichtfelder (für ALLE Typen):**
- [x] **Typ** (Dropdown: Produkt / Dienstleistung)
  - Bei "Dienstleistung": Zusatzauswahl "Eigenleistung / Fremdleistung"
- [x] **Bezeichnung** (z.B. "Beratungsstunde", "Bürostuhl Modell X", "SEO-Optimierung")
- [x] **Artikelnummer** (Freitext, frei wählbar!)
  - Bei Produkt: Eigene Artikelnummer (z.B. "BER-001", "STUHL-MX-500")
  - Bei Dienstleistung Eigenleistung: Eigene Nr. (z.B. "DL-WEB-001")
  - Bei Dienstleistung Fremdleistung: **Artikelnummer des Dienstleisters!**
  - Eindeutig (Duplikat-Prüfung)
- [x] **Steuersatz** (Dropdown: 19%, 7%, 0%)
- [x] **VK brutto** (Verkaufspreis brutto - PRIMÄRE EINGABE)
  - VK netto wird automatisch berechnet: `netto = brutto / (1 + steuersatz)`
  - Beispiel: 119,00 € brutto bei 19% → 100,00 € netto
- [x] **Einheit** (Freitext!)
  - Produkte: Stück, kg, m, m², Liter, Paket, Palette, etc.
  - Dienstleistungen: Stunden, Tag, Monat, Pauschal, Projekt, etc.
  - Nutzer kann beliebige Einheit eingeben

---

### **Optionale Felder (verfügbar je nach Typ):**

**Kategorisierung (ALLE Typen):**
- [x] **Kategorie** (Freitext, für Gruppierung)
  - Beispiel: "Dienstleistung", "Bürobedarf", "IT-Hardware", "Marketing"
  - Später (v1.1+): Dropdown mit vordefinierten Kategorien

**Einkaufspreise (NUR bei: Produkt + Dienstleistung Fremdleistung):**
- [x] **EK netto** (Einkaufspreis netto - PRIMÄRE EINGABE)
  - EK brutto wird automatisch berechnet: `brutto = netto * (1 + steuersatz)`
  - Bei Produkt: Wareneinkaufspreis
  - Bei Fremdleistung: Einkaufspreis vom Dienstleister/Subunternehmer
- [x] **EK brutto** (automatisch berechnet, nicht editierbar)

**Verkaufspreise (ALLE Typen):**
- [x] **VK netto** (automatisch berechnet aus VK brutto, nicht editierbar)

**Lieferanten-Information (NUR bei: Produkt + Dienstleistung Fremdleistung):**
- [x] **Lieferant** (Dropdown aus Lieferantenstamm)
  - Bei Produkt: Warenlieferant
  - Bei Fremdleistung: Dienstleister/Subunternehmer
- [x] **Lieferanten-Artikelnummer** (wichtig!)
  - Die Artikelnummer beim Lieferanten/Dienstleister
  - Beispiel Produkt: Bei Amazon Business = ASIN, bei Conrad = Bestellnummer
  - Beispiel Fremdleistung: Service-ID des Subunternehmers
  - **Verwendung:** Rechnungssuche, Nachbestellung

**Hersteller-Information (NUR bei: Produkt):**
- [x] **Hersteller** (Freitext)
  - Beispiel: "Logitech", "HP", "Microsoft"
  - Nicht bei Dienstleistungen
- [x] **Artikelcode** (Hersteller-Artikelbezeichnung, wichtig!)
  - Die originale Artikelbezeichnung des Herstellers
  - Beispiel: "MX-500-BLK", "LaserJet Pro M404dn", "Win11-Pro-OEM"
  - **Verwendung:** Rechnungssuche, technische Dokumentation
  - Nicht bei Dienstleistungen

**Identifikation (ALLE Typen):**
- [x] **EAN** (European Article Number - Barcode)
  - 13-stellig (EAN-13) oder 8-stellig (EAN-8)
  - Validierung: Prüfziffer
  - Bei Produkten: Standard-Barcode
  - Bei Dienstleistungen: **Für Scanlisten!** (z.B. beim Erfassen von Standard-Dienstleistungspaketen)

**Beschreibung (ALLE Typen):**
- [x] **Beschreibung** (Textarea, unbegrenzt)
  - Ausführliche Beschreibung für Rechnungstext
  - Beispiel Produkt: "Ergonomischer Bürostuhl mit Lordosenstütze, höhenverstellbar, Belastbarkeit bis 120kg"
  - Beispiel Dienstleistung: "Umfassende SEO-Optimierung inkl. Keyword-Recherche, On-Page-Optimierung und monatlichem Reporting"
  - Kann bei Ausgangsrechnung als Positionstext übernommen werden

---

### **Automatische Felder:**
- [x] **Aktiv/Inaktiv** - Checkbox (Standard: ✅ aktiviert)
  - Inaktive Artikel ausblenden (z.B. ausgelaufene Produkte)
  - Nicht löschen (GoBD - Historie behalten!)
- [x] **created_at** - Zeitpunkt des Anlegens (automatisch)
- [x] **updated_at** - Letzte Änderung (automatisch)
- [x] **Unbedingt erforderlich** für GoBD-Konformität

---

### **Berechnungslogik:**

**VK brutto → VK netto:**
```
VK netto = VK brutto / (1 + Steuersatz)

Beispiele:
119,00 € (brutto, 19%) → 100,00 € (netto)
107,00 € (brutto, 7%) → 100,00 € (netto)
100,00 € (brutto, 0%) → 100,00 € (netto)
```

**EK netto → EK brutto:**
```
EK brutto = EK netto × (1 + Steuersatz)

Beispiele:
50,00 € (netto, 19%) → 59,50 € (brutto)
80,00 € (netto, 7%) → 85,60 € (brutto)
```

---

### **Wichtige Hinweise:**

**Unterschied Artikelcode vs. Lieferanten-Artikelnummer:**
- **Artikelcode:** Hersteller-Bezeichnung (z.B. Logitech "MX-500-BLK")
- **Lieferanten-Artikelnummer:** Bestellnummer beim Lieferanten (z.B. Conrad "2347891", Amazon "B08XYZ123")
- **Beide wichtig für:**
  - Rechnungssuche (Eingangsrechnungen finden)
  - Nachbestellung (korrekte Artikel identifizieren)
  - Wareneingangsprüfung

**Use Cases:**

**1. Dienstleistung - Eigenleistung erfassen:**
   - **Typ:** Dienstleistung - Eigenleistung
   - Bezeichnung: "SEO-Optimierung Paket Basic"
   - Artikelnummer: "DL-SEO-001" (eigene Nummer)
   - VK brutto: 595,00 € → VK netto: 500,00 €
   - Steuersatz: 19%
   - Einheit: Pauschal
   - Kategorie: "Marketing"
   - EAN: "4012345678901" (für Scanliste!)
   - Beschreibung: "Umfassende SEO-Optimierung inkl. Keyword-Recherche..."
   - EK/Lieferant/Hersteller: leer (selbst erbracht)

**2. Dienstleistung - Fremdleistung erfassen:**
   - **Typ:** Dienstleistung - Fremdleistung
   - Bezeichnung: "Webdesign durch Subunternehmer XY"
   - Artikelnummer: **"WEB-SUB-2024-42"** (Artikelnummer des Dienstleisters!)
   - Lieferant: "Webdesign GmbH" (Subunternehmer)
   - Lieferanten-Artikelnummer: "WEB-SUB-2024-42"
   - EK netto: 800,00 € → EK brutto: 952,00 €
   - VK brutto: 1.190,00 € → VK netto: 1.000,00 €
   - Steuersatz: 19%
   - Einheit: Pauschal
   - Kategorie: "IT-Dienstleistung"
   - Beschreibung: "Responsive Webdesign, 5 Unterseiten, CMS-Integration"
   - Hersteller/Artikelcode: leer

**3. Produkt erfassen (für Wiederverkauf):**
   - **Typ:** Produkt
   - Bezeichnung: "Logitech MX Master 3S Maus"
   - Artikelnummer: "MAUS-001" (eigene Nummer)
   - Hersteller: "Logitech"
   - Artikelcode: "MX-MASTER-3S-BLK" (Hersteller-Bezeichnung)
   - Lieferant: "Conrad Electronic"
   - Lieferanten-Artikelnummer: "2347891" (Conrad Bestellnummer)
   - EAN: "5099206098596"
   - EK netto: 70,00 € → EK brutto: 83,30 €
   - VK brutto: 119,00 € → VK netto: 100,00 €
   - Steuersatz: 19%
   - Einheit: Stück
   - Kategorie: "IT-Hardware"

---

**Vorbereitung für v1.1+ (Rechnungsschreib-Modul):**
- Artikel & Dienstleistungen können direkt in Ausgangsrechnungen eingefügt werden
- Beschreibung → Positionstext
- VK brutto/netto → automatische Berechnung
- Einheit → Mengenangabe (z.B. "3 Stück", "12,5 Stunden", "1 Pauschal")

---

### **Feldverfügbarkeit-Matrix:**

| Feld | Produkt | DL Eigen | DL Fremd | Pflicht/Optional |
|------|---------|----------|----------|------------------|
| **Typ** | ✅ | ✅ | ✅ | Pflicht |
| **Bezeichnung** | ✅ | ✅ | ✅ | Pflicht |
| **Artikelnummer** | ✅ (eigene) | ✅ (eigene) | ✅ (vom Dienstleister!) | Pflicht |
| **Steuersatz** | ✅ | ✅ | ✅ | Pflicht |
| **VK brutto** | ✅ | ✅ | ✅ | Pflicht |
| **VK netto** | ✅ (auto) | ✅ (auto) | ✅ (auto) | Automatisch |
| **Einheit** | ✅ | ✅ | ✅ | Pflicht |
| **Kategorie** | ✅ | ✅ | ✅ | Optional |
| **EK netto** | ✅ | ❌ | ✅ | Optional |
| **EK brutto** | ✅ (auto) | ❌ | ✅ (auto) | Automatisch |
| **Lieferant** | ✅ | ❌ | ✅ | Optional |
| **Lieferanten-ArtNr** | ✅ | ❌ | ✅ | Optional |
| **Hersteller** | ✅ | ❌ | ❌ | Optional |
| **Artikelcode** | ✅ | ❌ | ❌ | Optional |
| **EAN** | ✅ | ✅ | ✅ | Optional |
| **Beschreibung** | ✅ | ✅ | ✅ | Optional |
| **Aktiv/Inaktiv** | ✅ | ✅ | ✅ | Automatisch |
| **created_at/updated_at** | ✅ | ✅ | ✅ | Automatisch (GoBD) |

**Legende:**
- ✅ = Feld verfügbar
- ❌ = Feld nicht verfügbar/ausgeblendet
- (auto) = Automatisch berechnet
- DL = Dienstleistung

---

**Frage 8.9: Vereins-Buchhaltung (4 Sphären)** ✅ GEKLÄRT (für v1.1+)

**Entscheidung: Vereins-spezifische Buchhaltung mit 4 Sphären**

Für gemeinnützige Vereine (e.V.) ist eine **Trennung nach Sphären** steuerlich erforderlich. Dies wird in **v1.1+** implementiert.

### **Die 4 Sphären der Vereinstätigkeit:**

#### **1. Ideeller Bereich** (steuerlich privilegiert)
- [x] **Einnahmen:** Mitgliedsbeiträge, Spenden, Zuschüsse von öffentlicher Hand
- [x] **Ausgaben:** Kosten für satzungsgemäße Vereinsarbeit (ohne wirtschaftlichen Bezug)
- [x] **USt-Status:** Steuerfrei (keine USt, keine Vorsteuer)
- [x] **Körperschaftsteuer:** Steuerfrei
- [x] **Gewerbesteuer:** Steuerfrei

**Beispiele:**
- Mitgliedsbeiträge eines Sportvereins
- Spenden für gemeinnützige Projekte
- Zuschüsse vom Land/Kommune

#### **2. Vermögensverwaltung** (steuerlich privilegiert)
- [x] **Einnahmen:** Zinsen, Dividenden, Vermietung/Verpachtung
- [x] **Ausgaben:** Verwaltungskosten für Vermögen
- [x] **USt-Status:** Meist steuerfrei (abhängig von Art der Vermögensverwaltung)
- [x] **Körperschaftsteuer:** Steuerfrei (bei gemeinnützigen Vereinen)
- [x] **Gewerbesteuer:** Steuerfrei

**Beispiele:**
- Vermietung Vereinsheim an Mitglieder
- Zinserträge aus Rücklagen
- Dividenden aus Wertpapieren

#### **3. Zweckbetrieb** (steuerlich begünstigt)
- [x] **Einnahmen:** Tätigkeiten, die direkt dem satzungsgemäßen Zweck dienen
- [x] **Ausgaben:** Kosten für Zweckbetrieb
- [x] **USt-Status:** **Ermäßigt 7%** (statt 19%)
- [x] **Körperschaftsteuer:** Steuerfrei (bei Erfüllung Gemeinnützigkeit)
- [x] **Gewerbesteuer:** Steuerfrei (bei Erfüllung Gemeinnützigkeit)

**Beispiele:**
- Sportkurse eines Sportvereins (für Mitglieder + Externe)
- Kulturveranstaltungen eines Kulturvereins
- Bildungsangebote einer gemeinnützigen Organisation

**Wichtig:** Zweckbetrieb muss **unentbehrlich** für satzungsgemäßen Zweck sein!

#### **4. Wirtschaftlicher Geschäftsbetrieb** (steuerpflichtig)
- [x] **Einnahmen:** Kommerzielle Tätigkeiten ohne direkten gemeinnützigen Bezug
- [x] **Ausgaben:** Kosten für wirtschaftlichen Geschäftsbetrieb
- [x] **USt-Status:** **Regelsteuersatz 19%**
- [x] **Körperschaftsteuer:** Steuerpflichtig (wenn >45.000€/Jahr, ab 2026: >50.000€/Jahr)
- [x] **Gewerbesteuer:** Steuerpflichtig (wenn >45.000€/Jahr, ab 2026: >50.000€/Jahr)

**Beispiele:**
- Vereinsgaststätte (offen für Öffentlichkeit)
- Merchandise-Verkauf (T-Shirts, Tassen)
- Werbung in Vereinszeitschrift
- Bandenwerbung im Stadion

**Freibetrag:** Bis 45.000€ (ab 2026: 50.000€) Einnahmen keine Körperschaftsteuer/Gewerbesteuer, aber trotzdem **USt-pflichtig!**

---

### **Warum ist diese Trennung wichtig?**

1. **Steuerliche Korrektheit:**
   - Finanzamt verlangt Trennung für Gemeinnützigkeitsprüfung
   - Fehlende Trennung = Risiko Gemeinnützigkeitsverlust!

2. **Unterschiedliche Steuersätze:**
   - Ideell: 0% USt
   - Zweckbetrieb: 7% USt
   - Wirtschaftlich: 19% USt

3. **Freibeträge nutzen:**
   - Wirtschaftlicher GB: Freibetrag 45.000€ (ab 2026: 50.000€)
   - Nur wenn korrekt getrennt, kann Freibetrag genutzt werden

4. **UStVA korrekt erstellen:**
   - Verschiedene Sphären haben verschiedene Behandlung
   - Nur mit Trennung ist UStVA GoBD-konform

---

### **Implementation in RechnungsFee (v1.1+):**

**Workflow:**
1. Bei Buchung/Rechnung: Feld "Sphäre" (Dropdown)
   - Ideeller Bereich (USt-frei)
   - Vermögensverwaltung (USt-frei)
   - Zweckbetrieb (7% USt)
   - Wirtschaftlicher GB (19% USt)

2. Automatische Zuordnung:
   - System schlägt basierend auf Kontierung (SKR49) Sphäre vor
   - User kann korrigieren

3. Auswertungen nach Sphären:
   - Separate Gewinn/Verlust-Rechnung pro Sphäre
   - Freibetrags-Kontrolle (wirtschaftlicher GB)
   - UStVA mit korrekter Trennung

4. Steuererklärung:
   - Export für Steuerberater mit Sphären-Trennung
   - Gemeinnützigkeitsnachweis (Anlage zur Körperschaftsteuererklärung)

---

### **UI-Konzept (v1.1+):**

```
Buchung erfassen:

┌─────────────────────────────────────────────┐
│ Einnahme erfassen                           │
├─────────────────────────────────────────────┤
│ Betrag: [100,00 €]                          │
│ Datum:  [22.01.2025]                        │
│                                             │
│ Sphäre: [Zweckbetrieb            ▼]        │
│         ○ Ideeller Bereich (USt-frei)       │
│         ● Zweckbetrieb (7% USt)             │
│         ○ Vermögensverwaltung (USt-frei)    │
│         ○ Wirtschaftlicher GB (19% USt)     │
│                                             │
│ USt:    [6,54 €] (7%)                       │
│                                             │
│ ℹ️ Zweckbetrieb: Ermäßigter Steuersatz     │
│   für gemeinnützige Tätigkeiten             │
│                                             │
│         [Abbrechen]    [Speichern]         │
└─────────────────────────────────────────────┘
```

---

### **Auswertung nach Sphären (v1.1+):**

```
Vereinsbuchhaltung 2025

┌──────────────────────────────────────────────────────────┐
│ Übersicht nach Sphären                                   │
├──────────────────────────────────────────────────────────┤
│ 1. Ideeller Bereich:                                     │
│    Einnahmen:  25.000 € (Mitgliedsbeiträge, Spenden)    │
│    Ausgaben:   12.000 € (Vereinsarbeit)                 │
│    Ergebnis:  +13.000 € ✅ Steuerfrei                    │
│                                                          │
│ 2. Vermögensverwaltung:                                  │
│    Einnahmen:   2.500 € (Zinsen, Vermietung)            │
│    Ausgaben:      800 € (Verwaltung)                    │
│    Ergebnis:   +1.700 € ✅ Steuerfrei                    │
│                                                          │
│ 3. Zweckbetrieb:                                         │
│    Einnahmen:  18.000 € (Sportkurse)                    │
│    USt (7%):    1.178 € → An Finanzamt                  │
│    Ausgaben:   10.000 € (Trainer, Material)            │
│    Vorsteuer:     950 € → Von Finanzamt zurück          │
│    Ergebnis:   +7.772 € ✅ Steuerfrei (gemeinnützig)    │
│                                                          │
│ 4. Wirtschaftlicher Geschäftsbetrieb:                    │
│    Einnahmen:  32.000 € (Gaststätte, Merchandise)       │
│    USt (19%):   5.109 € → An Finanzamt                  │
│    Ausgaben:   28.000 € (Waren, Personal)               │
│    Vorsteuer:   4.200 € → Von Finanzamt zurück          │
│    Ergebnis:   -1.109 € ⚠️ Unter Freibetrag (45k)       │
│                        ✅ Keine KSt/GewSt                │
│                                                          │
│ Gesamt-USt-Zahllast: 1.178 + 5.109 - 950 - 4.200       │
│                    = 1.137 € (quartalsweise abführen)   │
└──────────────────────────────────────────────────────────┘
```

---

### **Wichtig für v1.0 (Minimal-Version für Vereine):**

Auch ohne 4-Sphären-Trennung können Vereine RechnungsFee nutzen:
- [x] Rechtsform "e.V." auswählbar
- [x] USt-Status "Gemeinnützig (7%)" verfügbar
- [x] SKR49 (Vereins-Kontenrahmen) automatisch gewählt
- [x] Ist-Versteuerung als Default
- [x] Vierteljährliche UStVA

**Für vollständige Vereins-Compliance (4 Sphären) → v1.1+**

---

## **📋 Kategorie 9: Import-Schnittstellen & Rechnungsmodul** ✅ GEKLÄRT

---

### **Grundsatzentscheidung: Zwei Arten von Import** ✅ GEKLÄRT

- [x] **Import zur Verarbeitung** = Eingangsrechnungen (ZUGFeRD/PDF) empfangen und buchen → bereits durch **Kategorie 2** abgedeckt
- [x] **Import als Übernahme** = Datenmigration aus anderen Programmen (hellocash, Fakturama etc.) → **erst ab v1.1**
- [x] **Keine direkte API-Anbindung in v1.0** – kein REST-API-Zugriff, kein direkter DB-Zugriff
- [x] Kategorie 9 ist für **v1.0 vollständig durch Kategorien 2 + 5 gelöst**

---

### **Frage 9.1: Priorität der direkten Schnittstellen** ✅ GEKLÄRT

- [x] **v1.0:** Keine direkten Schnittstellen zu Dritt-Programmen
- [x] **v1.1 (Priorität 1):** hellocash → REST-API (JSON)
- [x] **v1.1 (Priorität 2):** Rechnungsassistent + Fakturama → ZUGFeRD/PDF-Export (universeller Weg, kein direkter DB-Zugriff)
- [x] Alle drei Programme + weitere können ZUGFeRD und PDF exportieren → universeller Importweg

---

### **Fragen 9.2–9.4: Daten-Formate je Programm** ✅ GEKLÄRT

| Programm | v1.0 | v1.1+ |
|----------|------|-------|
| **hellocash** | ZUGFeRD/PDF (universell) | REST-API (JSON) |
| **Rechnungsassistent** | ZUGFeRD/PDF (universell) | ZUGFeRD/PDF reicht |
| **Fakturama** | ZUGFeRD/PDF (universell) | ZUGFeRD/PDF reicht |
| **Alle anderen** | ZUGFeRD/PDF (universell) | ZUGFeRD/PDF reicht |

---

### **Fragen 9.5–9.6: Import-Umfang & Duplikat-Erkennung** ⏸️ ZURÜCKGESTELLT (v1.1)

Erst relevant wenn das eigene Rechnungsmodul (v1.1) existiert und eine vollständige Datenmigration sinnvoll ist.

---

### **Scope-Entscheidung: Rechnungsmodul** ✅ GEKLÄRT

**v1.0 – Kein eigenes Rechnungsmodul:**
- [x] RechnungsFee generiert eine **vorausgefüllte LibreOffice-ODT-Vorlage**
  - Kundendaten, Positionen, Steuersätze, Gesamtbeträge automatisch eingetragen
  - User öffnet Datei in LibreOffice Writer
  - User passt nach Bedarf an (Logo, Layout, Freitext)
  - User exportiert als PDF und versendet
- [x] **Vorteil:** Schlankes v1.0, keine komplexe PDF-Engine nötig
- [x] **Vorteil:** User hat volle Kontrolle über Layout und Inhalt
- [x] Ausgangsrechnungen werden als Einnahmen manuell im Kassenbuch erfasst

**v1.1 – Eigenes Rechnungsmodul:**
- [ ] Rechnungen direkt in RechnungsFee erstellen
- [ ] PDF-Export direkt aus der Anwendung
- [ ] ZUGFeRD-Einbettung in ausgehende Rechnungen
- [ ] Anbindung an Buchhaltung (automatische Buchung bei Zahlungseingang)

---

## **📋 Kategorie 10: Backup & Update** ✅ GEKLÄRT

**Frage 10.1: Backup-Speicherort** ✅ GEKLÄRT

**Entscheidung: Lokales Backup Pflicht, mehrere Ziele möglich**

### **Minimum (v1.0):**
- [x] **Lokales Backup IMMER** (Pflicht)
  - Automatisch bei Programmende
  - Standard-Pfad: `~/.rechnungsfee/backups/` (Linux/macOS) oder `%APPDATA%/RechnungsFee/backups/` (Windows)
  - Mindestens 3 Versionen aufbewahren
  - **Kann nicht deaktiviert werden** (Datensicherheit!)

### **Zusätzliche Backup-Ziele (v1.0 - optional):**
- [x] **USB-Stick** (optional konfigurierbar)
  - Nutzer wählt Laufwerk/Pfad
  - Backup wird auch dorthin kopiert (zusätzlich zu lokal)
  - Warnung wenn USB nicht verfügbar
- [x] **Netzlaufwerk** (optional konfigurierbar)
  - SMB/NFS-Share
  - UNC-Pfad (Windows) oder Mount-Point (Linux/macOS)
  - Warnung wenn Netzwerk nicht erreichbar

### **Mehrere Backup-Ziele parallel:**
- [x] **Local + USB + Netzlaufwerk** gleichzeitig möglich
- [x] Jedes Ziel kann einzeln aktiviert/deaktiviert werden
- [x] **Außer lokales Backup** - das ist immer aktiv

### **Später ausbaubar (v1.1+):**
- [ ] Nextcloud/WebDAV
- [ ] Cloud-Storage (Dropbox, Google Drive, OneDrive)
- [ ] SFTP/SSH
- [ ] Git-basiertes Backup

---

### **Backup-Verhalten:**

```
Beim Programmende:
1. Lokales Backup erstellen (IMMER)
   ✅ ~/.rechnungspilot/backups/backup-2025-01-15-14-30-00.db

2. Wenn USB konfiguriert:
   - USB verfügbar? → Backup kopieren ✅
   - USB nicht verfügbar? → Warnung anzeigen ⚠️

3. Wenn Netzlaufwerk konfiguriert:
   - Netzwerk erreichbar? → Backup kopieren ✅
   - Netzwerk nicht erreichbar? → Warnung anzeigen ⚠️

4. Programm beenden
```

---

### **UI-Einstellungen:**

```
Einstellungen → Backup & Wiederherstellung

┌─────────────────────────────────────────────┐
│ Backup-Ziele                                │
├─────────────────────────────────────────────┤
│ ☑ Lokal (Pflicht, nicht deaktivierbar)     │
│   Pfad: ~/.rechnungfee/backups/         │
│   Versionen: [3 ▼]                          │
│                                             │
│ ☐ USB-Stick                                 │
│   Pfad: [/media/usb/backups/        ]      │
│   [ Durchsuchen ]                           │
│                                             │
│ ☐ Netzlaufwerk                              │
│   Pfad: [\\server\backups\          ]      │
│   [ Durchsuchen ]                           │
│                                             │
│ [ Jetzt sichern ]  [ Wiederherstellen ]    │
└─────────────────────────────────────────────┘
```

---

**Vorteile dieser Lösung:**
- ✅ **Sicherheit:** Lokales Backup kann nicht deaktiviert werden
- ✅ **Flexibilität:** Zusätzliche Ziele nach Bedarf
- ✅ **Einfachheit:** Standard-Setup funktioniert out-of-the-box
- ✅ **Erweiterbar:** Weitere Backup-Ziele in späteren Versionen

**Frage 10.2: Backup-Verschlüsselung** ✅ GEKLÄRT

**Entscheidung: Backups immer verschlüsselt, flexible Passwortverwaltung**

### **Verschlüsselung:**
- [x] **Backups IMMER verschlüsselt** (Pflicht, nicht deaktivierbar)
  - AES-256 Verschlüsselung
  - Datenschutz-konform (DSGVO)
  - Schutz sensibler Buchhaltungsdaten
  - **Kann nicht deaktiviert werden**

### **Passwort-Verwaltung (User wählt Methode):**

#### **Option 1: Passwort manuell (Default)** ⭐ Standard
- [x] **Passwort bei Ersteinrichtung festlegen**
  - Min. 8 Zeichen, empfohlen: 12+ Zeichen
  - Passwort-Stärke-Anzeige
  - Bestätigung (zweimal eingeben)
- [x] **Passwort wird bei jedem Backup/Restore abgefragt**
  - Sicherste Methode
  - Nutzer behält volle Kontrolle
  - Nachteil: Muss bei jedem Programmende eingegeben werden

#### **Option 2: System-Keyring** 🔐 Empfohlen
- [x] **Integration mit System-Keychain/-Keyring**
  - **macOS:** Keychain
  - **Linux:** GNOME Keyring / KWallet (KDE) / Secret Service API
  - **Windows:** Windows Credential Manager
- [x] **Passwort einmal eingeben, danach automatisch**
  - Bei Ersteinrichtung: Passwort festlegen + "Im Keyring speichern"
  - System verschlüsselt und speichert Passwort sicher
  - Bei Backup/Restore: Automatisch aus Keyring abrufen
- [x] **Vorteile:**
  - Komfort: Kein ständiges Passwort-Eingeben
  - Sicherheit: System-Level-Verschlüsselung
  - Standard bei modernen Betriebssystemen

#### **Option 3: Passwortmanager-Integration** 🔑 Für Power-User
- [x] **Integration mit gängigen Passwortmanagern (v1.0 oder v1.1)**
  - KeePass / KeePassXC
  - Bitwarden
  - 1Password
  - Andere (über CLI/API)
- [x] **Workflow:**
  - Passwort in Passwortmanager speichern
  - RechnungsFee ruft Passwort via CLI/API ab
  - Beispiel KeePassXC: `keepassxc-cli show database.kdbx "RechnungsFee Backup"`
- [x] **Für Nutzer mit bestehendem Passwort-Management-Workflow**

---

### **Backup-Passwort vs. Master-Passwort:**

**Entscheidung: Separates Backup-Passwort**

- [x] **Backup-Passwort ≠ Programm-Login** (falls es ein Programm-Login gibt)
- [x] **Begründung:**
  - Backup kann extern wiederhergestellt werden (z.B. auf anderem Rechner)
  - User kann Backup-Passwort anderen geben (z.B. Steuerberater) ohne Programm-Zugriff
  - Flexibilität: Verschiedene Sicherheitsstufen

---

### **UI-Einstellungen:**

```
Einstellungen → Backup & Wiederherstellung → Verschlüsselung

┌─────────────────────────────────────────────┐
│ Backup-Verschlüsselung                      │
├─────────────────────────────────────────────┤
│ ☑ Backups verschlüsseln (Pflicht)          │
│   Methode: AES-256                          │
│                                             │
│ Passwort-Verwaltung:                        │
│ ○ Manuell eingeben (bei jedem Backup)      │
│ ● System-Keyring (empfohlen)               │
│ ○ Passwortmanager-Integration              │
│                                             │
│ Aktuelles Passwort: ••••••••                │
│ [ Passwort ändern ]                         │
│                                             │
│ ℹ️ Bei System-Keyring: Passwort wird       │
│   sicher im System-Schlüsselbund gespeichert│
└─────────────────────────────────────────────┘
```

---

### **Ersteinrichtung (Setup-Assistent):**

```
Schritt 8: Backup-Verschlüsselung einrichten

┌─────────────────────────────────────────────┐
│ Backup-Passwort festlegen                   │
├─────────────────────────────────────────────┤
│ Deine Backups werden verschlüsselt (AES-256)│
│ zum Schutz sensibler Daten.                 │
│                                             │
│ Neues Passwort:                             │
│ [________________________]                  │
│ Stärke: ████████░░ Stark                    │
│                                             │
│ Passwort bestätigen:                        │
│ [________________________]                  │
│                                             │
│ ☑ Im System-Keyring speichern (empfohlen)  │
│   → Kein erneutes Eingeben nötig            │
│                                             │
│ ⚠️ Wichtig: Passwort gut aufbewahren!      │
│   Ohne Passwort sind Backups nicht nutzbar. │
│                                             │
│         [Zurück]    [Weiter]               │
└─────────────────────────────────────────────┘
```

---

### **Backup bei Programmende (mit Keyring):**

```
Benutzer klickt "Beenden"
↓
1. Änderungen vorhanden?
   ├─ Nein → Programm beenden
   └─ Ja → Backup erstellen

2. Passwort benötigt
   ├─ Keyring aktiviert?
   │  ├─ Ja → Passwort aus Keyring abrufen ✅
   │  └─ Nein → Passwort-Dialog anzeigen
   └─ Passwort erhalten

3. Backup erstellen (verschlüsselt mit Passwort)
   ✅ backup-2025-01-15-14-30-00.db.enc

4. Programm beenden
```

---

### **Wiederherstellung:**

```
Backup wiederherstellen
↓
1. Backup-Datei auswählen
   backup-2025-01-15-14-30-00.db.enc

2. Passwort benötigt
   ├─ Keyring aktiviert?
   │  ├─ Ja → Passwort aus Keyring abrufen
   │  └─ Nein → Passwort abfragen
   └─ Passwort korrekt?
      ├─ Ja → Entschlüsseln & Wiederherstellen ✅
      └─ Nein → Fehler "Falsches Passwort" ❌
```

---

### **Passwort vergessen?**

**Wichtiger Hinweis für Nutzer:**

```
⚠️ Backup-Passwort vergessen?

Leider gibt es KEINE Möglichkeit, verschlüsselte
Backups ohne Passwort wiederherzustellen.

Bitte bewahre dein Passwort sicher auf:
- Passwortmanager
- Notizzettel im Safe
- Vertrauenswürdiger Ort

Ohne Passwort sind alle Backups unbrauchbar!
```

---

### **Technische Details:**

**Verschlüsselung:**
- Algorithmus: AES-256-GCM (Galois/Counter Mode)
- Key Derivation: PBKDF2 (100.000+ Iterationen)
- Salt: Zufällig generiert pro Backup
- Dateiformat: `.db.enc` (verschlüsselte SQLite)

**Keyring-Bibliotheken:**
- Rust: `keyring` crate
- Cross-Platform-Support (Windows, macOS, Linux)
- Fallback: Wenn Keyring nicht verfügbar → manuelle Eingabe

---

**Vorteile dieser Lösung:**
- ✅ **Sicherheit:** Immer verschlüsselt, DSGVO-konform
- ✅ **Komfort:** Keyring vermeidet ständige Passwort-Eingabe
- ✅ **Flexibilität:** User wählt bevorzugte Methode
- ✅ **Standard-konform:** System-Keyring ist moderne Best Practice

**Frage 10.3: Backup-Versionen** ✅ GEKLÄRT

**Entscheidung: 7 Versionen als Standard, konfigurierbar**

### **Anzahl der Versionen:**
- [x] **Standard: 7 Versionen** (1 Woche Puffer)
  - Guter Kompromiss zwischen Sicherheit und Speicherplatz
  - Ermöglicht Zeitreise bis zu 7 Tage zurück
  - Für die meisten Nutzer ausreichend

### **Konfigurierbar:**
- [x] **Nutzer kann Anzahl ändern** (in Einstellungen)
  - Minimum: 3 Versionen (nicht weniger - Datensicherheit!)
  - Empfohlen: 7 Versionen ⭐
  - Maximum: 30 Versionen (für Power-User)
  - Dropdown-Werte: 3, 5, 7, 10, 14, 30

### **Automatische Rotation:**
- [x] **Älteste Backups automatisch löschen** (Pflicht)
  - Wenn Maximum erreicht → ältestes Backup wird gelöscht
  - Neues Backup wird erstellt
  - Anzahl bleibt konstant (z.B. immer genau 7)
  - **Kann nicht deaktiviert werden** (verhindert Speicher-Überlauf)

### **Zeitstempel im Dateinamen:**
- [x] **Format: `backup-YYYY-MM-DD-HH-MM-SS.db.enc`**
  - Beispiel: `backup-2025-01-22-14-30-45.db.enc`
  - Eindeutig identifizierbar
  - Sortierbar (chronologisch)
  - Nutzer sieht auf einen Blick, wann Backup erstellt wurde

---

### **Speicherplatz-Berechnung:**

**Annahme:** Datenbank-Größe ≈ 50 MB (typisch für Kleinunternehmer)

| Versionen | Gesamt-Speicherplatz | Rücksprung-Zeitraum |
|-----------|---------------------|---------------------|
| 3 | ~150 MB | 2-3 Tage |
| **7** ⭐ | **~350 MB** | **1 Woche** |
| 30 | ~1,5 GB | 1 Monat |

**Bei größeren Datenbanken (z.B. 200 MB):**
- 7 Versionen = ~1,4 GB

---

### **Rotation-Beispiel (7 Versionen):**

```
Tag 1-7: Backups werden aufgebaut
backup-2025-01-16.db.enc  (ältestes)
backup-2025-01-17.db.enc
backup-2025-01-18.db.enc
backup-2025-01-19.db.enc
backup-2025-01-20.db.enc
backup-2025-01-21.db.enc
backup-2025-01-22.db.enc  (neuestes)

Tag 8: Neues Backup erstellt
→ backup-2025-01-16.db.enc wird GELÖSCHT ❌
→ backup-2025-01-23.db.enc wird ERSTELLT ✅

Ergebnis:
backup-2025-01-17.db.enc  (jetzt ältestes)
backup-2025-01-18.db.enc
backup-2025-01-19.db.enc
backup-2025-01-20.db.enc
backup-2025-01-21.db.enc
backup-2025-01-22.db.enc
backup-2025-01-23.db.enc  (neuestes)
```

**→ Immer genau 7 Versionen vorhanden**

---

### **UI-Einstellungen:**

```
Einstellungen → Backup & Wiederherstellung → Versionen

┌─────────────────────────────────────────────┐
│ Backup-Versionen                            │
├─────────────────────────────────────────────┤
│ Anzahl aufzubewahrender Versionen:          │
│ [7 ▼]                                       │
│ (Dropdown: 3, 5, 7, 10, 14, 30)            │
│                                             │
│ ☑ Älteste Backups automatisch löschen      │
│   (Rotation - nicht deaktivierbar)          │
│                                             │
│ ℹ️ Speicherplatz pro Version: ~50 MB       │
│    Gesamt benötigt: ~350 MB (7 Versionen)  │
│                                             │
│ Vorhandene Backups (7):                     │
│ ┌───────────────────────────────────────┐  │
│ │ ○ 2025-01-22 14:30 (50 MB) ← Neuestes│  │
│ │ ○ 2025-01-21 16:45 (49 MB)           │  │
│ │ ○ 2025-01-20 10:15 (48 MB)           │  │
│ │ ○ 2025-01-19 18:20 (50 MB)           │  │
│ │ ○ 2025-01-18 12:00 (47 MB)           │  │
│ │ ○ 2025-01-17 15:30 (49 MB)           │  │
│ │ ○ 2025-01-16 09:45 (48 MB) ← Ältestes│  │
│ └───────────────────────────────────────┘  │
│                                             │
│ [ Ausgewähltes wiederherstellen ]          │
│ [ Ausgewähltes manuell löschen ]           │
└─────────────────────────────────────────────┘
```

---

### **Vorteile 7 Versionen:**
- ✅ **Sicherheit:** 1 Woche Puffer für Fehler-Erkennung
- ✅ **Speicherplatz:** Moderat (nicht zu viel, nicht zu wenig)
- ✅ **Praktisch:** Wochenzyklus passt zu Arbeitsrhythmus
- ✅ **Flexibel:** Nutzer kann bei Bedarf anpassen

---

### **Schutz-Szenarien abgedeckt:**

**Versehentliche Löschung innerhalb 7 Tagen:**
- ✅ Wiederherstellbar

**Daten-Korruption erkannt innerhalb 7 Tagen:**
- ✅ Auf älteres Backup zurückgreifen

**Falsche Buchungen über mehrere Tage:**
- ✅ Bis zu 1 Woche zurückspringen

**Zeitreise für Vergleiche:**
- ✅ "Wie sah Kontostand vor 5 Tagen aus?"

---

**Zusammenfassung:**
- Standard: 7 Versionen (empfohlen)
- Konfigurierbar: 3-30 Versionen
- Automatische Rotation: Ja (Pflicht)
- Zeitstempel-Format: `YYYY-MM-DD-HH-MM-SS`
- Dateiendung: `.db.enc` (verschlüsselt)

**Frage 10.4: Backup bei Programmende** ✅ GEKLÄRT

**Entscheidung: Automatisch bei Änderungen mit Fortschritt und intelligenter Fehlerbehandlung**

### **Wann wird Backup erstellt?**
- [x] **Nur wenn Änderungen vorhanden** (smart)
  - System prüft: Wurden Daten geändert seit letztem Backup?
  - Keine Änderungen → Kein Backup nötig → Programm schließt sofort
  - Änderungen vorhanden → Backup wird erstellt
- [x] **Automatisch beim Beenden** (kein Nutzer-Eingriff nötig)
  - User klickt "Beenden" → System entscheidet automatisch

### **Fortschrittsanzeige:**
- [x] **Sichtbare Fortschrittsanzeige** (nicht im Hintergrund)
  - Dialog mit Fortschrittsbalken
  - Verhindert versehentliches Herunterfahren während Backup
  - User sieht: "Backup läuft, bitte warten"
  - Geschätzte Dauer anzeigen (bei großen DBs)

### **Fehlerbehandlung:**
- [x] **Bei Backup-Fehler: Warnung mit Optionen**
  - Option 1: "Backup wiederholen" (empfohlen)
  - Option 2: "Trotzdem beenden" (Warnung wird gespeichert)
  - **Kein erzwungenes Schließen** - User entscheidet

### **Warnung beim nächsten Start:**
- [x] **Falls trotz Fehler geschlossen wurde**
  - Beim nächsten Programmstart: Warnung anzeigen
  - "Letztes Backup fehlgeschlagen - jetzt nachholen?"
  - Option: Backup nachholen oder ignorieren
  - Warnung bleibt, bis Backup erfolgreich

---

### **Workflow: Normaler Programmende (mit Änderungen)**

```
1. User klickt "Beenden" (X, Menü, Strg+Q)
   ↓
2. System prüft: Änderungen seit letztem Backup?
   ├─ Nein → Programm schließen sofort ✅
   └─ Ja → Weiter zu Schritt 3

3. Fortschritts-Dialog anzeigen:
   ┌─────────────────────────────────────┐
   │ Backup wird erstellt...             │
   ├─────────────────────────────────────┤
   │ ████████████████░░░░░░░░ 65%       │
   │                                     │
   │ Verschlüssele Daten...              │
   │ Geschätzte Zeit: 5 Sekunden         │
   │                                     │
   │ [ Abbrechen ] (nur in Notfällen)   │
   └─────────────────────────────────────┘

4. Backup erfolgreich
   ↓
5. Programm schließen ✅
```

---

### **Workflow: Backup-Fehler beim Beenden**

```
1. User klickt "Beenden"
   ↓
2. Änderungen vorhanden → Backup starten
   ↓
3. ❌ FEHLER tritt auf (z.B. Festplatte voll, USB nicht erreichbar)
   ↓
4. Fehler-Dialog anzeigen:

   ┌─────────────────────────────────────────┐
   │ ⚠️ Backup fehlgeschlagen                │
   ├─────────────────────────────────────────┤
   │ Das Backup konnte nicht erstellt werden:│
   │                                         │
   │ Fehler: Nicht genügend Speicherplatz    │
   │ Pfad: ~/.rechnungsfee/backups/         │
   │                                         │
   │ Deine Änderungen sind NICHT gesichert!  │
   │                                         │
   │ Was möchtest du tun?                    │
   │                                         │
   │ [ 🔄 Backup wiederholen ]  ← Empfohlen │
   │ [ ⚠️ Trotzdem beenden ]                │
   │ [ ↩️ Abbrechen ]                        │
   └─────────────────────────────────────────┘

5a. User wählt "Backup wiederholen"
    → Zurück zu Schritt 3 (erneuter Versuch)

5b. User wählt "Trotzdem beenden"
    → Warnung speichern (für nächsten Start)
    → Programm schließen ⚠️

5c. User wählt "Abbrechen"
    → Zurück ins Programm (nicht beenden)
```

---

### **Workflow: Warnung beim nächsten Programmstart**

```
Programm startet
↓
System prüft: Letztes Backup fehlgeschlagen?
├─ Nein → Normal starten
└─ Ja → Warnung anzeigen

┌─────────────────────────────────────────────┐
│ ⚠️ Backup-Warnung                           │
├─────────────────────────────────────────────┤
│ Das letzte Backup ist fehlgeschlagen!       │
│                                             │
│ Zeitpunkt: 2025-01-22 16:45                │
│ Fehler: Nicht genügend Speicherplatz        │
│                                             │
│ Deine Daten vom letzten Mal sind NICHT     │
│ gesichert. Möchtest du jetzt ein Backup    │
│ erstellen?                                  │
│                                             │
│ [ 🔄 Jetzt Backup erstellen ] ← Empfohlen  │
│ [ ⏭️ Später (bei Programmende) ]           │
│ [ ❌ Ignorieren (nicht empfohlen) ]        │
└─────────────────────────────────────────────┘

User wählt "Jetzt Backup erstellen":
→ Backup wird sofort erstellt
→ Bei Erfolg: Warnung verschwindet ✅
→ Bei Fehler: Warnung bleibt, erneuter Versuch später

User wählt "Später":
→ Warnung bleibt gespeichert
→ Wird bei nächstem Programmende erneut versucht

User wählt "Ignorieren":
→ Bestätigungs-Dialog:
  "Wirklich ignorieren? Daten sind ungesichert!"
  [Ja, ignorieren] [Abbrechen]
→ Warnung wird gelöscht (auf eigenes Risiko)
```

---

### **Fehler-Typen und Behandlung:**

| Fehler-Typ | Ursache | Automatische Behandlung | User-Aktion |
|------------|---------|------------------------|-------------|
| **Speicherplatz voll** | Festplatte voll | Warnung anzeigen | Speicher freigeben, wiederholen |
| **USB nicht erreichbar** | USB-Stick abgezogen | Lokales Backup trotzdem erstellen ✅, USB-Warnung | USB einstecken, später sync |
| **Netzwerk nicht erreichbar** | Netzlaufwerk offline | Lokales Backup trotzdem erstellen ✅, Netzwerk-Warnung | Netzwerk prüfen, später sync |
| **Passwort falsch** | Keyring-Fehler | Passwort-Dialog anzeigen | Passwort eingeben |
| **Datei gesperrt** | Antivirus blockiert | Warnung anzeigen | Antivirus-Ausnahme hinzufügen |
| **Schreibrechte fehlen** | Permissions-Problem | Warnung anzeigen | Rechte prüfen, ggf. Admin |

---

### **Spezialfall: USB/Netzwerk-Fehler**

**Wichtig:** Lokales Backup hat Priorität!

```
Backup-Prozess:
1. Lokales Backup erstellen
   ├─ Erfolgreich ✅ → Weiter zu Schritt 2
   └─ Fehlgeschlagen ❌ → Fehler-Dialog (wie oben)

2. USB-Backup erstellen (falls konfiguriert)
   ├─ Erfolgreich ✅ → Weiter zu Schritt 3
   └─ Fehlgeschlagen ⚠️ → Warnung (aber Programm kann beenden)
                          "USB-Backup fehlgeschlagen, lokales Backup OK"

3. Netzwerk-Backup erstellen (falls konfiguriert)
   ├─ Erfolgreich ✅ → Alles gut, Programm beenden
   └─ Fehlgeschlagen ⚠️ → Warnung (aber Programm kann beenden)
                          "Netzwerk-Backup fehlgeschlagen, lokales Backup OK"
```

**→ Lokales Backup MUSS erfolgreich sein, zusätzliche Ziele sind optional!**

---

### **UI-Einstellungen:**

```
Einstellungen → Backup & Wiederherstellung → Programmende

┌─────────────────────────────────────────────┐
│ Backup bei Programmende                     │
├─────────────────────────────────────────────┤
│ ☑ Automatisch Backup erstellen (Pflicht)   │
│   Nur wenn Änderungen vorhanden             │
│                                             │
│ ☑ Fortschrittsanzeige anzeigen             │
│   (nicht deaktivierbar)                     │
│                                             │
│ Bei Backup-Fehler:                          │
│ ☑ Warnung beim nächsten Start anzeigen     │
│ ☑ Option zum Wiederholen anbieten           │
│                                             │
│ Zusätzliche Backup-Ziele (optional):        │
│ ☐ USB-Backup als kritisch markieren        │
│   (Programm nur beenden wenn erfolgreich)   │
│ ☐ Netzwerk-Backup als kritisch markieren   │
│                                             │
│ ℹ️ Lokales Backup ist immer kritisch       │
└─────────────────────────────────────────────┘
```

---

### **Abbrechen-Button im Fortschritts-Dialog:**

**Wichtiger Hinweis:** "Abbrechen" sollte nur in Notfällen verwendet werden!

```
User klickt "Abbrechen" während Backup läuft
↓
Bestätigungs-Dialog:
┌─────────────────────────────────────────┐
│ ⚠️ Backup wirklich abbrechen?           │
├─────────────────────────────────────────┤
│ Das Backup ist noch nicht fertig!       │
│                                         │
│ Wenn du jetzt abbrichst:                │
│ • Änderungen sind NICHT gesichert       │
│ • Backup-Datei ist unvollständig        │
│ • Daten könnten verloren gehen          │
│                                         │
│ Wirklich abbrechen?                     │
│                                         │
│ [ ↩️ Zurück zum Backup ] ← Empfohlen   │
│ [ ⚠️ Ja, abbrechen ]                   │
└─────────────────────────────────────────┘

Falls "Ja, abbrechen":
→ Unvollständiges Backup löschen
→ Warnung für nächsten Start speichern
→ Zurück ins Programm (nicht beenden)
```

---

### **Technische Implementation:**

**Änderungs-Erkennung:**
```rust
struct BackupTracker {
    last_backup_hash: String,  // SHA256 der DB
    last_backup_time: DateTime,
}

fn needs_backup() -> bool {
    let current_hash = calculate_db_hash();
    let last_hash = load_last_backup_hash();

    current_hash != last_hash  // true = Änderungen vorhanden
}
```

**Fehler-Warnung speichern:**
```rust
struct BackupWarning {
    failed_at: DateTime,
    error_message: String,
    retry_count: u32,
}

// In Config-Datei speichern:
~/.rechnungsfee/backup_warning.json
```

---

### **Vorteile dieser Lösung:**
- ✅ **Intelligent:** Nur Backup wenn nötig (spart Zeit)
- ✅ **Transparent:** User sieht Fortschritt
- ✅ **Sicher:** Fehler werden nicht ignoriert
- ✅ **Flexibel:** User kann bei Fehler entscheiden
- ✅ **Persistent:** Warnungen bleiben bis behoben
- ✅ **Prioritäten:** Lokales Backup ist kritisch, Rest optional

**Frage 10.5: Manuelles Backup** ✅ GEKLÄRT

**Entscheidung: Menü "Jetzt sichern" mit freier Zielwahl und Log-Viewer**

### **Zugriff:**
- [x] **Menü: Datei → Jetzt sichern** (oder Tastenkürzel Strg+B)
- [x] **Toolbar-Button** (optional, konfigurierbar)
- [x] **Einstellungen → Backup-Button** "Jetzt sichern"

### **Zielwahl:**
- [x] **Keine Vorgabe - User wählt frei:**
  - Nur lokal
  - Nur USB
  - Nur Netzwerk
  - Alle konfigurierten Ziele
  - Oder beliebige Kombination
- [x] **Zusätzlich: Ad-hoc-Ziel wählen**
  - "An anderem Ort sichern..." → Datei-Browser
  - Für Einmal-Backups (z.B. vor großen Änderungen)

### **Backup-Protokoll/Log-Viewer:**
- [x] **Vollständige Backup-Historie einsehbar**
  - Alle automatischen Backups
  - Alle manuellen Backups
  - Erfolge und Fehler
  - Zeitstempel, Größe, Ziel
- [x] **Zugriff:** Menü → Backup & Wiederherstellung → Backup-Protokoll
- [x] **Funktionen:**
  - Filtern (nach Datum, Status, Ziel)
  - Sortieren
  - Details anzeigen
  - Backup direkt wiederherstellen aus Log

---

### **UI: Manuelles Backup-Dialog**

```
Menü: Datei → Jetzt sichern (Strg+B)
↓

┌─────────────────────────────────────────────┐
│ Manuelles Backup erstellen                  │
├─────────────────────────────────────────────┤
│ Wohin möchtest du sichern?                  │
│                                             │
│ ☑ Lokal                                     │
│   ~/.rechnungsfee/backups/                 │
│   Letztes Backup: vor 2 Stunden            │
│                                             │
│ ☑ USB-Stick                                 │
│   /media/usb/backups/                      │
│   Letztes Backup: vor 1 Tag                │
│                                             │
│ ☐ Netzlaufwerk (nicht konfiguriert)        │
│   [ Konfigurieren... ]                     │
│                                             │
│ ─────────────────────────────────────────  │
│                                             │
│ ☐ An anderem Ort sichern...                │
│   [ Durchsuchen... ]                       │
│   Für Einmal-Backup (z.B. externe Festpl.) │
│                                             │
│ ─────────────────────────────────────────  │
│                                             │
│ Dateiname (optional):                       │
│ [backup-vor-steuerexport.db.enc      ]     │
│ (Standard: backup-YYYY-MM-DD-HH-MM-SS.db.enc)│
│                                             │
│ ☑ Vorhandene Versionen beibehalten         │
│   (zählt nicht zur Auto-Rotation)          │
│                                             │
│ [ ✅ Backup jetzt erstellen ]              │
│ [ Abbrechen ]      [ 📋 Protokoll ]        │
└─────────────────────────────────────────────┘
```

---

### **Workflow: Manuelles Backup erstellen**

```
1. User: Menü → "Jetzt sichern" (Strg+B)
   ↓
2. Backup-Dialog öffnet sich (siehe UI oben)
   ↓
3. User wählt Ziele (z.B. Lokal + USB)
   ↓
4. Optional: Eigenen Dateinamen eingeben
   ↓
5. "Backup jetzt erstellen" klicken
   ↓
6. Fortschritts-Dialog (wie bei Programmende)
   ┌─────────────────────────────────────┐
   │ Backup wird erstellt...             │
   ├─────────────────────────────────────┤
   │ ████████████████░░░░░░░░ 65%       │
   │                                     │
   │ Aktuell: USB-Stick (2/2)           │
   │ Geschätzte Zeit: 3 Sekunden         │
   └─────────────────────────────────────┘
   ↓
7. Erfolgs-Meldung:
   ┌─────────────────────────────────────┐
   │ ✅ Backup erfolgreich erstellt      │
   ├─────────────────────────────────────┤
   │ Gesichert nach:                     │
   │ • Lokal (50 MB)                    │
   │ • USB-Stick (50 MB)                │
   │                                     │
   │ [ OK ]  [ Protokoll anzeigen ]     │
   └─────────────────────────────────────┘
```

---

### **Use Cases für manuelles Backup:**

**1. Vor großen Änderungen**
```
User denkt: "Ich mache jetzt große Änderungen (z.B. viele Löschungen)"
→ Manuelles Backup erstellen mit eigenem Namen:
  "backup-vor-loeschung-2025-01-22.db.enc"
→ Falls etwas schiefgeht: Dieses Backup wiederherstellen
```

**2. Vor Steuerberater-Termin**
```
User: "Ich gebe Daten an Steuerberater weiter"
→ Manuelles Backup auf USB-Stick
→ USB-Stick dem Steuerberater geben
→ Steuerberater kann selbst wiederherstellen
```

**3. Regelmäßiges USB-Backup (Offline-Sicherung)**
```
User: "Jeden Freitag sichere ich auf USB"
→ Manuell: USB-Stick auswählen
→ Unabhängig von automatischem Backup
→ Zusätzliche Sicherheit (3-2-1-Backup-Regel)
```

**4. Ad-hoc externe Festplatte**
```
User: "Ich habe gerade externe Festplatte angeschlossen"
→ "An anderem Ort sichern" wählen
→ Externe Festplatte auswählen
→ Einmal-Backup (wird nicht automatisch wiederholt)
```

---

### **Backup-Protokoll/Log-Viewer**

```
Menü: Backup & Wiederherstellung → Backup-Protokoll
↓

┌─────────────────────────────────────────────────────────────┐
│ Backup-Protokoll                                  [ ✕ ]     │
├─────────────────────────────────────────────────────────────┤
│ Filter: [Alle ▼] Zeitraum: [Letzte 30 Tage ▼] [Aktualis.] │
│                                                             │
│ Datum/Zeit        │ Typ        │ Ziel      │ Größe │ Status│
├───────────────────┼────────────┼───────────┼───────┼───────┤
│ 2025-01-22 16:45 │ Automatisch│ Lokal     │ 50 MB │ ✅    │
│ 2025-01-22 16:45 │ Automatisch│ USB       │ 50 MB │ ⚠️ X │
│ 2025-01-22 14:30 │ Manuell    │ USB       │ 50 MB │ ✅    │
│ 2025-01-22 10:15 │ Automatisch│ Lokal     │ 49 MB │ ✅    │
│ 2025-01-21 18:20 │ Automatisch│ Lokal     │ 49 MB │ ✅    │
│ 2025-01-21 18:20 │ Automatisch│ Netzwerk  │ 49 MB │ ❌    │
│ 2025-01-21 12:00 │ Manuell    │ Alle      │150 MB │ ✅    │
│ 2025-01-20 16:45 │ Automatisch│ Lokal     │ 48 MB │ ✅    │
│ ...                                                         │
├─────────────────────────────────────────────────────────────┤
│ ℹ️ Legende:                                                │
│ ✅ Erfolgreich  ⚠️ Teilweise (lokal OK, USB Fehler)       │
│ ❌ Fehlgeschlagen                                          │
│                                                             │
│ [ Details ]  [ Wiederherstellen ]  [ Exportieren (CSV) ]  │
└─────────────────────────────────────────────────────────────┘
```

---

### **Detailansicht (Doppelklick auf Eintrag):**

```
┌─────────────────────────────────────────────┐
│ Backup-Details: 2025-01-22 16:45           │
├─────────────────────────────────────────────┤
│ Typ: Automatisch (Programmende)            │
│ Zeitpunkt: 22.01.2025 16:45:32            │
│ Dauer: 4,2 Sekunden                        │
│                                             │
│ Ziele:                                      │
│ ✅ Lokal                                    │
│    Pfad: ~/.rechnungsfee/backups/         │
│    Datei: backup-2025-01-22-16-45-32.db.enc│
│    Größe: 50,3 MB                          │
│    Hash: a3f5c89d...                       │
│                                             │
│ ⚠️ USB-Stick (Fehler)                      │
│    Pfad: /media/usb/backups/               │
│    Fehler: Gerät nicht gefunden            │
│    Wiederholungen: 3                       │
│                                             │
│ Datenbank-Info:                             │
│ Rechnungen: 245                            │
│ Transaktionen: 1.832                       │
│ Kunden: 42                                 │
│ Lieferanten: 18                            │
│                                             │
│ [ Dieses Backup wiederherstellen ]         │
│ [ Backup-Datei im Explorer anzeigen ]      │
│ [ Schließen ]                              │
└─────────────────────────────────────────────┘
```

---

### **Log-Einträge:**

**Jeder Log-Eintrag enthält:**
- Zeitstempel (Datum + Uhrzeit)
- Typ (Automatisch / Manuell)
- Ziel(e) (Lokal, USB, Netzwerk, Extern)
- Größe (in MB)
- Status (Erfolgreich ✅ / Teilweise ⚠️ / Fehlgeschlagen ❌)
- Bei Fehler: Fehlermeldung
- Hash (zur Integritätsprüfung)
- Datenbank-Statistiken (Anzahl Rechnungen, etc.)

---

### **Filter & Suche:**

```
Filter-Optionen:
┌─────────────────────────────────────────┐
│ Status: [Alle ▼]                       │
│ • Alle                                  │
│ • Nur erfolgreiche                     │
│ • Nur fehlgeschlagene                  │
│ • Nur teilweise                        │
│                                         │
│ Typ: [Alle ▼]                          │
│ • Alle                                  │
│ • Nur automatische                     │
│ • Nur manuelle                         │
│                                         │
│ Ziel: [Alle ▼]                         │
│ • Alle                                  │
│ • Nur lokal                            │
│ • Nur USB                              │
│ • Nur Netzwerk                         │
│                                         │
│ Zeitraum: [Letzte 30 Tage ▼]          │
│ • Heute                                 │
│ • Letzte 7 Tage                        │
│ • Letzte 30 Tage                       │
│ • Dieses Jahr                          │
│ • Benutzerdefiniert...                 │
└─────────────────────────────────────────┘
```

---

### **Export-Funktion:**

**CSV-Export des Protokolls:**
```csv
Zeitstempel,Typ,Ziel,Größe_MB,Status,Fehler,Pfad
2025-01-22 16:45:32,Automatisch,Lokal,50.3,Erfolgreich,,~/.rechnungsfee/backups/backup-2025-01-22-16-45-32.db.enc
2025-01-22 16:45:32,Automatisch,USB,0,Fehlgeschlagen,Gerät nicht gefunden,
2025-01-22 14:30:15,Manuell,USB,50.1,Erfolgreich,,/media/usb/backups/backup-2025-01-22-14-30-15.db.enc
...
```

**Nützlich für:**
- Dokumentation (Steuerberater, Wirtschaftsprüfer)
- Nachweis regelmäßiger Backups (GoBD)
- Fehleranalyse bei Support-Anfragen

---

### **Tastenkürzel:**

| Aktion | Tastenkürzel |
|--------|--------------|
| Manuelles Backup | **Strg+B** |
| Backup-Protokoll öffnen | **Strg+Shift+B** |
| Letzte Wiederherstellung | **Strg+R** |

---

### **Einstellungen: Protokoll-Aufbewahrung**

```
Einstellungen → Backup & Wiederherstellung → Protokoll

┌─────────────────────────────────────────────┐
│ Backup-Protokoll                            │
├─────────────────────────────────────────────┤
│ Protokoll-Einträge aufbewahren:             │
│ [90 Tage ▼]                                 │
│ (Dropdown: 30, 60, 90, 180, 365, Unbegrenzt)│
│                                             │
│ ☑ Erfolgreiche Backups im Protokoll        │
│ ☑ Fehlgeschlagene Backups im Protokoll     │
│ ☑ Warnungen im Protokoll                   │
│                                             │
│ Protokoll-Speicherort:                      │
│ ~/.rechnungsfee/backup_log.db              │
│                                             │
│ Aktuelle Größe: 2,4 MB (1.245 Einträge)   │
│                                             │
│ [ Protokoll bereinigen ]                   │
│ [ Protokoll exportieren (CSV) ]            │
└─────────────────────────────────────────────┘
```

---

### **Technische Implementation:**

**Log-Datenbank:**
```sql
CREATE TABLE backup_log (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    type TEXT NOT NULL,  -- 'auto', 'manual'
    target TEXT NOT NULL,  -- 'local', 'usb', 'network', 'custom'
    file_path TEXT,
    file_size_bytes INTEGER,
    status TEXT NOT NULL,  -- 'success', 'partial', 'failed'
    error_message TEXT,
    duration_seconds REAL,
    db_hash TEXT,

    -- Statistiken
    db_rechnungen_count INTEGER,
    db_transaktionen_count INTEGER,
    db_kunden_count INTEGER,
    db_lieferanten_count INTEGER,

    -- Metadaten
    triggered_by TEXT,  -- 'user', 'program_exit', 'scheduled'
    retry_count INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### **Vorteile dieser Lösung:**
- ✅ **Flexibilität:** User wählt Ziel(e) frei
- ✅ **Transparenz:** Vollständiges Protokoll aller Backups
- ✅ **Kontrolle:** Jederzeit manuell sichern möglich
- ✅ **Nachvollziehbarkeit:** Log-Export für Dokumentation
- ✅ **Komfort:** Tastenkürzel für Power-User
- ✅ **GoBD-konform:** Nachweis regelmäßiger Sicherungen

**Frage 10.6: Wiederherstellung:** ✅ GEKLÄRT

**Entscheidung: Hybrid-Ansatz (Automatisch mit manuellem Fallback)**

#### **Workflow:**

**1. Automatischer Wiederherstellungsversuch:**
- [x] Bei Programmstart: DB-Integritätsprüfung (SQLite PRAGMA integrity_check)
- [x] Bei Korruption: Automatischer Versuch mit **letztem erfolgreichen Backup**
- [x] Fortschrittsanzeige: "Datenbank wird wiederhergestellt..."
- [x] **Erfolg:** Normaler Programmstart mit Info-Meldung
  ```
  ℹ️ Datenbank wurde automatisch wiederhergestellt
  Backup vom: 2025-12-22, 18:45 Uhr
  ```

**2. Fallback bei Scheitern:**
- [x] **Wenn automatische Wiederherstellung fehlschlägt:**
  - Backup-Liste öffnen (Dialog)
  - User wählt manuell eine Version
  - Vorschau pro Backup:
    - **Datum/Uhrzeit** (z.B. "22.12.2025, 18:45 Uhr")
    - **Dateigröße** (z.B. "4,2 MB")
    - **DB-Statistiken:**
      - Anzahl Rechnungen
      - Anzahl Transaktionen
      - Anzahl Kunden
      - Anzahl Lieferanten
    - **Status:** ✓ Erfolgreich, ⚠️ Partiell, ✗ Fehlgeschlagen

#### **UI: Backup-Auswahl-Dialog**

```
┌─────────────────────────────────────────────────────────────┐
│ 🔄 Wiederherstellung erforderlich                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ⚠️ Automatische Wiederherstellung fehlgeschlagen            │
│ Bitte wählen Sie ein Backup zur manuellen Wiederherstellung │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ○ 22.12.2025, 18:45 Uhr  │  4,2 MB  │  ✓  │ 142 Rg.    │ │
│ │   └─ 1.284 Transaktionen, 45 Kunden, 12 Lieferanten     │ │
│ │                                                          │ │
│ │ ○ 22.12.2025, 12:30 Uhr  │  4,1 MB  │  ✓  │ 138 Rg.    │ │
│ │   └─ 1.201 Transaktionen, 44 Kunden, 12 Lieferanten     │ │
│ │                                                          │ │
│ │ ○ 21.12.2025, 19:15 Uhr  │  4,0 MB  │  ✓  │ 135 Rg.    │ │
│ │   └─ 1.156 Transaktionen, 43 Kunden, 11 Lieferanten     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ 📂 Speicherort: ~/.rechnungsfee/backups/                    │
│                                                              │
│         [ Vorschau ]  [ Wiederherstellen ]  [ Abbrechen ]   │
└─────────────────────────────────────────────────────────────┘
```

#### **Zusatzfunktionen:**

- [x] **Vorschau-Button:** Zeigt detaillierte Backup-Metadaten
  - Verschlüsselungsstatus
  - DB-Hash (zur Verifizierung)
  - Wiederherstellungszeit-Schätzung
  - Letzte 5 Buchungen (Preview)

- [x] **Alternative Quelle:**
  - "Anderes Backup wählen..." → Datei-Dialog
  - USB-Stick, Netzlaufwerk, anderer Ordner

- [x] **Notfall-Neuanlage:**
  - Falls keine Backups verfügbar
  - "Neue Datenbank erstellen" (Daten verloren)
  - ⚠️ Warnung mit Bestätigung

#### **Technische Details:**

**Integritätsprüfung:**
```rust
fn check_db_integrity(db_path: &Path) -> Result<bool, Error> {
    let conn = Connection::open(db_path)?;
    let result: String = conn.query_row(
        "PRAGMA integrity_check",
        [],
        |row| row.get(0)
    )?;

    Ok(result == "ok")
}
```

**Wiederherstellungs-Workflow:**
```rust
fn restore_database() -> Result<(), Error> {
    // 1. Integritätsprüfung
    if !check_db_integrity(&DB_PATH)? {
        // 2. Automatischer Versuch
        match try_auto_restore() {
            Ok(_) => {
                show_info("DB erfolgreich wiederhergestellt");
                return Ok(());
            }
            Err(e) => {
                // 3. Fallback: Manuelle Auswahl
                let selected = show_backup_list()?;
                restore_from_backup(&selected)?;
            }
        }
    }
    Ok(())
}

fn try_auto_restore() -> Result<(), Error> {
    let latest = get_latest_successful_backup()?;
    decrypt_and_restore(&latest)?;

    // Verifizierung nach Wiederherstellung
    if !check_db_integrity(&DB_PATH)? {
        return Err(Error::RestoreFailed);
    }

    Ok(())
}
```

---

### **Vorteile dieser Lösung:**
- ✅ **Komfort:** Automatische Wiederherstellung ohne User-Interaktion (Normalfall)
- ✅ **Sicherheit:** Fallback bei Problemen (robuster Workflow)
- ✅ **Transparenz:** User sieht Backup-Details bei manueller Auswahl
- ✅ **Flexibilität:** Alternative Quellen (USB, Netzwerk) möglich
- ✅ **Datenrettung:** Notfall-Neuanlage verhindert Programmblockade
- ✅ **Verifizierung:** Integritätsprüfung nach Wiederherstellung
- ✅ **Informiert:** Info-Meldung bei automatischer Wiederherstellung

---

**Frage 10.7: Auto-Update** ✅ GEKLÄRT

**Entscheidung: Update-Pflicht mit Frist-System (nach Lexware-Modell)**

### **Kernprinzip:**

- [x] **Update-Pflicht** - nicht deaktivierbar
  - Begründung: GoBD-Konformität, Steuerrecht, Sicherheit
  - Kritische Updates MÜSSEN installiert werden
- [x] **Frist-basiert** - User hat Zeit (7-30 Tage je nach Update-Typ)
  - User kann Zeitpunkt innerhalb der Frist wählen
  - Keine überraschenden Updates während der Arbeit
- [x] **Transparenz** - Begründung wird angezeigt
  - Warum ist das Update wichtig?
  - Was ändert sich?
  - Welche rechtlichen Gründe gibt es?

---

### **Update-Kategorien mit Fristen:**

| Update-Typ | Frist | Beispiel | Zwang |
|------------|-------|----------|-------|
| **🔒 Kritisches Sicherheitsupdate** | 7 Tage | Verschlüsselungslücke, SQL-Injection, Datenleck | ✅ Pflicht |
| **⚖️ Rechtliche Pflicht** | 14 Tage | E-Rechnung-Pflicht, neue UStVA-Formulare, Steuersatz-Änderungen | ✅ Pflicht |
| **📋 Wichtiges Update (GoBD/Compliance)** | 30 Tage | GoBD-Änderungen, DATEV-Format-Update, neue Features mit Compliance | ✅ Pflicht |
| **✨ Optionales Feature-Update** | Unbegrenzt | Neue UI, Komfort-Features, Performance-Verbesserungen | ❌ Optional |

---

### **Workflow: Update-Ankündigung (beim Programmstart)**

#### **Phase 1: Erste Ankündigung (Tag 1-7)**

```
┌─────────────────────────────────────────────────────────┐
│ 🔔 Neues Update verfügbar                               │
├─────────────────────────────────────────────────────────┤
│ Version 1.2.0 ist verfügbar                             │
│ Aktuelle Version: 1.1.5                                 │
│                                                         │
│ 🔴 Wichtige Änderungen:                                 │
│ ⚖️ Neue UStVA-Formulare 2025 (Pflicht)                 │
│ ⚖️ E-Rechnungspflicht (§14 UStG, ab 01.01.2025)        │
│ 🔒 Sicherheitsupdate: Verschlüsselung verbessert        │
│ ✨ Vereins-Buchhaltung (4 Sphären)                      │
│                                                         │
│ ⚠️ Dieses Update muss bis 05.01.2025 installiert       │
│    werden (noch 12 Tage).                               │
│                                                         │
│ Begründung:                                             │
│ • Gesetzliche Pflicht: E-Rechnung ab 2025              │
│ • GoBD-Konformität: Neue Anforderungen                  │
│ • Sicherheit: Kritisches Verschlüsselungs-Update        │
│                                                         │
│ [ Jetzt installieren ]  [ Später (erinnere mich) ]     │
│ [ Changelog anzeigen ]                                  │
│                                                         │
│ ℹ️ Update dauert ca. 2 Minuten                          │
│ ℹ️ Automatisches Backup wird erstellt                   │
└─────────────────────────────────────────────────────────┘
```

**User-Aktion:**
- "Jetzt installieren" → Update startet sofort
- "Später" → Dialog schließt sich, Erinnerung beim nächsten Start
- "Changelog anzeigen" → Detaillierte Änderungsliste

---

#### **Phase 2: Dringliche Erinnerung (Tag 8-13)**

```
┌─────────────────────────────────────────────────────────┐
│ ⚠️ Wichtiges Update muss bald installiert werden        │
├─────────────────────────────────────────────────────────┤
│ Version 1.2.0 ist verfügbar                             │
│                                                         │
│ ⏰ Noch 5 Tage Zeit bis 05.01.2025                      │
│                                                         │
│ Danach kann RechnungsFee nicht mehr gestartet werden,  │
│ bis das Update installiert ist.                         │
│                                                         │
│ Gründe für Pflicht-Update:                              │
│ ⚖️ Rechtlich: E-Rechnungspflicht ab 2025               │
│ 🔒 Sicherheit: Kritische Lücke geschlossen              │
│ 📋 GoBD: Neue Anforderungen umgesetzt                   │
│                                                         │
│ [ Jetzt installieren ]  [ Morgen erinnern ]            │
│                                                         │
│ ⚠️ Bitte installiere das Update rechtzeitig!            │
└─────────────────────────────────────────────────────────┘
```

**Zusätzlich:**
- Auch beim **Programmende** wird Erinnerung angezeigt
- Icon in der Statusleiste (permanent sichtbar)

---

#### **Phase 3: Letzte Warnung (Tag 14, letzter Tag)**

```
┌─────────────────────────────────────────────────────────┐
│ 🛑 LETZTER TAG: Update MUSS heute installiert werden!  │
├─────────────────────────────────────────────────────────┤
│ Version 1.2.0                                           │
│                                                         │
│ ⏰ Frist läuft HEUTE ab (05.01.2025, 23:59 Uhr)        │
│                                                         │
│ Ab morgen kann RechnungsFee NICHT MEHR gestartet       │
│ werden, bis das Update installiert ist!                │
│                                                         │
│ ⚠️ Pflichtgründe:                                       │
│ • E-Rechnungspflicht (gesetzlich ab 01.01.2025)        │
│ • GoBD-Konformität gefährdet ohne Update                │
│ • Sicherheitslücken in alter Version                    │
│                                                         │
│ Bitte installiere JETZT das Update!                    │
│                                                         │
│ [ Jetzt installieren ]  [ Programm beenden ]           │
│                                                         │
│ ℹ️ Backup wird automatisch erstellt                     │
│ ℹ️ Bei Fehler: Automatischer Rollback                   │
└─────────────────────────────────────────────────────────┘
```

**User-Aktion:**
- "Jetzt installieren" → Update startet
- "Programm beenden" → Programm schließt sich (ohne Update)

**Kein "Später"-Button mehr!**

---

#### **Phase 4: Frist abgelaufen (nach Tag 14)**

```
┌─────────────────────────────────────────────────────────┐
│ ⛔ Update erforderlich - Programm gesperrt              │
├─────────────────────────────────────────────────────────┤
│ RechnungsFee kann nicht gestartet werden.               │
│                                                         │
│ Die Frist für Update 1.2.0 ist abgelaufen.             │
│ (Fristende: 05.01.2025)                                │
│                                                         │
│ Gründe:                                                 │
│ ⚖️ Gesetzliche Änderungen (E-Rechnung-Pflicht)          │
│ 📋 GoBD-Konformität gefährdet                            │
│ 🔒 Sicherheitslücken in alter Version                   │
│                                                         │
│ Das Update wird jetzt automatisch installiert.          │
│ Danach kannst du RechnungsFee wieder verwenden.        │
│                                                         │
│         [ Update installieren und starten ]            │
│                                                         │
│ ℹ️ Deine Daten bleiben sicher (automatisches Backup)   │
│ ℹ️ Update dauert ca. 2 Minuten                          │
└─────────────────────────────────────────────────────────┘
```

**Kein Ausweichen mehr möglich!**
- Einzige Option: Update installieren
- Programm startet erst nach erfolgreichem Update

---

### **Update-Installation (Workflow)**

```
┌─────────────────────────────────────────────────────────┐
│ 🔄 Update wird installiert...                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Schritt 1/5: Backup erstellen                          │
│ ████████████████████████████████████░░░░░░░ 85%        │
│ backup-2025-01-05-14-30-00.db.enc                      │
│                                                         │
│ ℹ️ Deine Daten werden gesichert...                      │
│                                                         │
│ Geschätzte Zeit: 30 Sekunden                            │
└─────────────────────────────────────────────────────────┘
```

**Ablauf:**

1. **Backup erstellen** (automatisch, verschlüsselt)
   - Vollständiges DB-Backup
   - Mit Zeitstempel
   - Verifizierung (Hash-Check)

2. **Update herunterladen**
   - Von offiziellem Server (HTTPS)
   - Signaturprüfung (GPG)
   - Fortschrittsanzeige

3. **Update installieren**
   - Neue Version extrahieren
   - Alte Version archivieren (für Rollback)
   - Permissions prüfen

4. **Datenbank-Migration** (falls nötig)
   - Schema-Updates
   - Daten konvertieren
   - Integritätsprüfung

5. **Programm neu starten**
   - Automatischer Neustart
   - Verifizierung (funktioniert alles?)
   - Bei Fehler: **Automatischer Rollback**

---

### **Changelog transparent machen**

```
┌─────────────────────────────────────────────────────────┐
│ 📋 Was ist neu in Version 1.2.0?                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ ⚖️ Rechtlich erforderlich (PFLICHT):                    │
│ • E-Rechnungspflicht (§14 UStG, ab 01.01.2025)         │
│   → B2B-Rechnungen müssen elektronisch sein            │
│ • Neue UStVA-Formulare 2025                             │
│   → Finanzamt akzeptiert alte Formulare nicht mehr     │
│                                                         │
│ 🔒 Sicherheit (KRITISCH):                               │
│ • CVE-2025-1234: AES-Verschlüsselung verbessert        │
│ • Backup-Passwort-Hashing (PBKDF2, 200.000 Iterationen)│
│ • SQL-Injection-Schutz verbessert                       │
│                                                         │
│ 📋 GoBD/Compliance:                                     │
│ • Neue Anforderungen BMF-Schreiben 2025                │
│ • Revisionssichere Archivierung erweitert               │
│                                                         │
│ ✨ Neue Features (OPTIONAL):                            │
│ • Vereins-Buchhaltung (4 Sphären, SKR49)                │
│ • GLS Bank CSV-Import                                   │
│ • Verbesserte Fehlerbehandlung                          │
│ • Performance-Optimierungen (30% schneller)             │
│                                                         │
│ 🐛 Bugfixes:                                            │
│ • #123: UStVA Zeile 67 Rundungsfehler behoben          │
│ • #145: DATEV-Export Sonderzeichen-Problem             │
│ • 10 weitere Bugfixes                                   │
│                                                         │
│ [ Vollständigen Changelog auf GitHub anzeigen ]        │
└─────────────────────────────────────────────────────────┘
```

**Kategorisierung:**
- ⚖️ **Rechtlich erforderlich** - User versteht: "Muss sein, Gesetz!"
- 🔒 **Sicherheit** - User versteht: "Wichtig für Datenschutz!"
- 📋 **GoBD/Compliance** - User versteht: "Finanzamt-relevant!"
- ✨ **Neue Features** - User versteht: "Bonus, aber nicht zwingend"
- 🐛 **Bugfixes** - User versteht: "Verbesserungen"

---

### **Automatischer Rollback bei Fehler**

Falls Update fehlschlägt:

```
┌─────────────────────────────────────────────────────────┐
│ ⚠️ Update fehlgeschlagen                                │
├─────────────────────────────────────────────────────────┤
│ Das Update konnte nicht installiert werden.             │
│                                                         │
│ Fehler: Datenbank-Migration fehlgeschlagen (Schritt 4) │
│                                                         │
│ RechnungsFee wird jetzt auf die vorherige Version      │
│ zurückgesetzt (Rollback).                               │
│                                                         │
│ 🔄 Rollback läuft...                                    │
│ ████████████████████████████████████░░░░░░░ 85%        │
│                                                         │
│ Deine Daten sind sicher und bleiben unverändert.       │
│                                                         │
│ [ Bitte warten... ]                                     │
└─────────────────────────────────────────────────────────┘

Nach Rollback:

┌─────────────────────────────────────────────────────────┐
│ ✅ Rollback erfolgreich                                 │
├─────────────────────────────────────────────────────────┤
│ RechnungsFee läuft wieder auf Version 1.1.5             │
│                                                         │
│ Das Update wird in Kürze erneut versucht.              │
│                                                         │
│ Fehlerprotokoll wurde an Entwickler gesendet.          │
│                                                         │
│ [ Programm neu starten ]                                │
└─────────────────────────────────────────────────────────┘
```

**Automatischer Rollback:**
- Backup wird wiederhergestellt
- Alte Version wird aktiviert
- Fehlerprotokoll wird erstellt (optional an Entwickler senden)
- User kann weiterarbeiten

---

### **Antworten auf die 4 Fragen:**

#### **1. Zwingend oder optional?**
**✅ Entscheidung: Zwingend (mit Frist)**

- **Pflicht-Updates:** Sicherheit, Rechtliches, GoBD
  - Nicht deaktivierbar
  - Frist: 7-30 Tage je nach Typ
- **Optionale Updates:** Neue Features ohne Compliance-Relevanz
  - Benachrichtigung, aber kein Zwang
  - User kann ignorieren

**Begründung:**
- GoBD-Konformität: Veraltete Versionen gefährden Compliance
- Steuerrecht: Neue Formulare, Steuersätze müssen aktuell sein
- Sicherheit: Verschlüsselung, Datenschutz
- Support: Einheitliche Versionen erleichtern Support

---

#### **2. Silent-Update oder mit Nachfrage?**
**✅ Entscheidung: Mit Nachfrage (während Frist)**

- **Während Frist:** User wird gefragt, kann Zeitpunkt wählen
  - Vorteil: User kann planen (nicht mitten in Steuererklärung)
  - User behält Kontrolle
- **Nach Frist:** Automatisch (blockierend)
  - Programm startet nicht mehr ohne Update
  - Keine Ausweichmöglichkeit

**KEIN Silent-Update im Hintergrund:**
- Zu riskant (DB-Migration könnte schiefgehen)
- User soll bewusst Update durchführen
- Backup-Erstellung sichtbar machen

---

#### **3. Update-Kanal?**
**✅ Entscheidung: Nur Stable (für v1.0)**

- **Stable-Kanal:** Alle Nutzer (Standard)
  - Nur stabile, getestete Releases
  - Keine Beta/Alpha-Features
- **Beta/Nightly:** Erst ab v1.1+ (für Entwickler/Tester)
  - Optional aktivierbar in Einstellungen
  - Mit Warnung: "Nur für Entwickler!"

**Begründung:**
- v1.0: Einfachheit, keine Verwirrung
- Buchhaltungssoftware = stabil sein muss
- Beta/Nightly nur für Power-User

---

#### **4. Update-Benachrichtigung bei deaktiviertem Auto-Update?**
**✅ Entscheidung: Nicht relevant (Auto-Update nicht deaktivierbar)**

- Pflicht-Updates können nicht deaktiviert werden
- Optionale Feature-Updates:
  - Benachrichtigung: Ja
  - Zwang: Nein
  - User kann ignorieren

---

### **Technische Details:**

**Update-Server:**
```
https://updates.rechnungsfee.de/stable/latest.json

{
  "version": "1.2.0",
  "release_date": "2025-01-01",
  "mandatory": true,
  "deadline": "2025-01-15",
  "deadline_days": 14,
  "category": "legal",
  "download_url": "https://updates.rechnungsfee.de/stable/1.2.0/rechnungsfee-1.2.0.tar.gz",
  "signature": "https://updates.rechnungsfee.de/stable/1.2.0/rechnungsfee-1.2.0.tar.gz.sig",
  "changelog_url": "https://github.com/nicolettas-muggelbude/RechnungsFee/releases/tag/v1.2.0",
  "min_version": "1.0.0",
  "reasons": [
    "E-Rechnungspflicht (§14 UStG)",
    "Kritisches Sicherheitsupdate (CVE-2025-1234)",
    "GoBD-Konformität"
  ]
}
```

**Update-Prüfung:**
- Beim Programmstart (täglich)
- Optional: Stündlich im Hintergrund (wenn Programm läuft)
- Signaturprüfung (GPG) vor Installation

**Rollback-Mechanismus:**
```rust
fn update_with_rollback() -> Result<(), Error> {
    // 1. Backup erstellen
    let backup_path = create_backup()?;

    // 2. Alte Version archivieren
    let old_version = archive_current_version()?;

    // 3. Update installieren
    match install_update() {
        Ok(_) => {
            // 4. Verifizierung
            if verify_installation()? {
                Ok(())
            } else {
                // Rollback
                restore_from_backup(&backup_path)?;
                restore_old_version(&old_version)?;
                Err(Error::VerificationFailed)
            }
        }
        Err(e) => {
            // Rollback
            restore_from_backup(&backup_path)?;
            restore_old_version(&old_version)?;
            Err(e)
        }
    }
}
```

---

### **Vorteile dieser Lösung:**

- ✅ **User-freundlich:** Frist statt sofortigem Zwang
- ✅ **Sicher:** Alle Nutzer auf aktuellem Stand
- ✅ **Rechtlich sauber:** GoBD, Steuerrecht, E-Rechnung
- ✅ **Transparent:** Begründung, Changelog, Kategorisierung
- ✅ **Flexibel:** User wählt Zeitpunkt (innerhalb Frist)
- ✅ **Robust:** Automatischer Rollback bei Fehler
- ✅ **Support-freundlich:** Einheitliche Versionen

---

**Frage 10.8: Rollback** ✅ GEKLÄRT

**Entscheidung: Kein manueller Rollback - nur automatischer bei Update-Fehler**

### **Kernprinzip:**

- [x] **KEIN manueller Rollback** nach erfolgreichem Update
  - User kann nicht auf alte Version zurück
  - Alle User bleiben auf aktueller Version
  - Sicherheit, Compliance, Support
- [x] **Automatischer Rollback bei Update-Fehler**
  - Bereits in 10.7 dokumentiert
  - Funktioniert während Update-Installation
  - User kann weiterarbeiten mit alter Version
- [x] **Automatisches Backup vor Update** (immer!)
  - Bereits in 10.7 dokumentiert
  - Verschlüsselt, verifiziert, mit Zeitstempel
- [x] **Nur letzte Version archiviert** (1 Version zurück)
  - Reicht für automatischen Rollback
  - Wenig Speicherplatz (~100-200 MB)

---

### **1. KEIN manueller Rollback**

**Begründung:**

#### **Sicherheit:**
- Alle User müssen auf aktueller Version sein
- Veraltete Versionen = Sicherheitslücken
- Update-Pflicht mit Frist-System (10.7) greift

#### **Compliance (GoBD, Steuerrecht):**
- Veraltete Versionen gefährden GoBD-Konformität
- Finanzamt erkennt alte Exporte evtl. nicht an
- E-Rechnung-Pflicht ab 2025 erfordert aktuelle Version

#### **Datenbank-Migration:**
- **Vorwärts-Migration:** Einfach (von v1.1 → v1.2)
- **Rückwärts-Migration:** Komplex und fehleranfällig!
  - Neue Spalten müssen gelöscht werden
  - Neue Features hinterlassen evtl. Daten
  - Risiko von Datenverlust

#### **Support:**
- Nur eine Version im Umlauf
- Bug-Reports eindeutig zuordenbar
- Einfachere Fehlersuche

---

### **2. Was wenn User NACH erfolgreichem Update Probleme hat?**

**Szenarien und Lösungen:**

#### **Szenario A: Funktionaler Bug nach Update**

```
Beispiel: "Seit Update v1.2.0 kann ich keine Rechnungen mehr als PDF exportieren"
```

**Workflow:**

1. **User meldet Bug** (GitHub Issue oder Support)
   ```
   Titel: [Bug] PDF-Export funktioniert nicht nach Update v1.2.0
   Beschreibung: Beim Klick auf "Als PDF exportieren" passiert nichts.
   Version: 1.2.0
   Fehlermeldung: [Screenshot]
   ```

2. **Entwickler verifiziert Bug**
   - Bug wird bestätigt
   - Priorität: Kritisch (Kernfunktion betroffen)

3. **Hotfix wird entwickelt** (v1.2.1)
   - Bug-Fix innerhalb 24-48h (kritisch)
   - Release als Pflicht-Update (7 Tage Frist)

4. **User installiert Hotfix**
   - Automatische Benachrichtigung
   - "Wichtiger Bugfix verfügbar"

**KEIN Rollback auf v1.1.5** → stattdessen Fix in v1.2.1

---

#### **Szenario B: Performance-Problem nach Update**

```
Beispiel: "Seit Update v1.2.0 ist das Programm deutlich langsamer"
```

**Workflow:**

1. **User meldet Performance-Problem**
   ```
   Titel: [Performance] Programm langsamer seit v1.2.0
   Beschreibung: Laden dauert jetzt 10 Sekunden statt 2 Sekunden
   Version: 1.2.0
   Datenbank-Größe: 150 MB
   ```

2. **Entwickler analysiert Problem**
   - Profiling, Performance-Tests
   - Ursache identifiziert (z.B. fehlender DB-Index)

3. **Performance-Hotfix** (v1.2.1)
   - Optimierung wird entwickelt
   - Getestet mit großen Datenbanken
   - Release als wichtiges Update (14 Tage Frist)

**KEIN Rollback** → Performance-Fix in nächstem Update

---

#### **Szenario C: UI-Änderung gefällt User nicht**

```
Beispiel: "Die neue Oberfläche in v1.2.0 gefällt mir nicht, ich will die alte zurück"
```

**Antwort:**

```
┌─────────────────────────────────────────────────────────┐
│ UI-Feedback                                             │
├─────────────────────────────────────────────────────────┤
│ Danke für dein Feedback zur neuen Oberfläche!           │
│                                                         │
│ Ein Rollback auf die alte Version ist leider nicht     │
│ möglich, da:                                            │
│ • Sicherheitsupdates in v1.2.0 enthalten sind          │
│ • GoBD-konforme Anforderungen erfüllt werden müssen     │
│                                                         │
│ Wir nehmen dein Feedback ernst:                         │
│ • Bitte erstelle ein GitHub Issue mit konkreten        │
│   Verbesserungsvorschlägen                              │
│ • Wir prüfen UI-Anpassungen für v1.3.0                  │
│ • Optional: Altes Theme als Option (in v1.3.0)         │
│                                                         │
│ [ Issue erstellen ]  [ Schließen ]                     │
└─────────────────────────────────────────────────────────┘
```

**Lösungsansatz:**
- UI-Feedback sammeln
- Optional: "Klassisches Theme" in späterem Update (v1.3.0)
- KEIN Rollback auf alte Version

---

### **3. Automatisches Backup vor Update** ✅

**Bereits in 10.7 vollständig dokumentiert:**

- ✅ Automatisch bei JEDEM Update
- ✅ Verschlüsselt (AES-256-GCM)
- ✅ Mit Zeitstempel
- ✅ Verifizierung (Hash-Check)
- ✅ Wird für automatischen Rollback verwendet (bei Update-Fehler)

**Beispiel:**
```
~/.rechnungsfee/backups/
  ├─ backup-2025-01-05-14-30-00.db.enc  (vor Update v1.2.0)
  ├─ backup-2025-01-12-10-15-30.db.enc  (regulär, 7 Versionen)
  └─ ...
```

**Wichtig:**
- Update-Backup ist **zusätzlich** zu regulären Backups (10.1-10.5)
- Wird verwendet für automatischen Rollback bei Update-Fehler
- NICHT für manuellen Rollback (User kann nicht darauf zugreifen)

---

### **4. Wie viele Versionen archivieren?** ✅

**Entscheidung: Nur letzte Version (1 Version zurück)**

**Archiv-Struktur:**
```
~/.rechnungsfee/archive/
  └─ rechnungsfee-1.1.5/        (alte Version)
      ├─ bin/                   (Binaries)
      ├─ lib/                   (Libraries)
      └─ version.txt            (Version-Info)
```

**Ablauf bei Update von v1.1.5 → v1.2.0:**

1. **Vor Update:**
   - Aktuelle Version: v1.1.5 (aktiv)
   - Archiv: v1.1.4 (alte Version)

2. **Update-Prozess:**
   - v1.1.5 wird ins Archiv verschoben
   - v1.1.4 wird gelöscht (nicht mehr benötigt)
   - v1.2.0 wird installiert (neue aktive Version)

3. **Nach Update:**
   - Aktuelle Version: v1.2.0 (aktiv)
   - Archiv: v1.1.5 (für automatischen Rollback)

**Speicherplatz:**
- Pro Version: ~100-200 MB
- Nur 1 alte Version: Minimal (~200 MB)
- Bei 3 Versionen: ~600 MB (unnötig, da kein manueller Rollback)

---

### **5. Automatischer Rollback bei Update-Fehler** ✅

**Bereits in 10.7 vollständig dokumentiert:**

Wenn Update **während Installation** fehlschlägt:

```rust
fn update_with_rollback() -> Result<(), Error> {
    let backup_path = create_backup()?;
    let old_version = archive_current_version()?;

    match install_update() {
        Ok(_) => {
            if verify_installation()? {
                Ok(())
            } else {
                // Rollback
                restore_from_backup(&backup_path)?;
                restore_old_version(&old_version)?;
                Err(Error::VerificationFailed)
            }
        }
        Err(e) => {
            // Rollback
            restore_from_backup(&backup_path)?;
            restore_old_version(&old_version)?;
            Err(e)
        }
    }
}
```

**Fehler-Szenarien mit automatischem Rollback:**
- ❌ Download fehlgeschlagen → Rollback
- ❌ Signatur ungültig → Rollback
- ❌ Installation fehlgeschlagen → Rollback
- ❌ Datenbank-Migration fehlgeschlagen → Rollback
- ❌ Verifizierung fehlgeschlagen → Rollback

**User sieht:**
```
┌─────────────────────────────────────────────────────────┐
│ ⚠️ Update fehlgeschlagen                                │
├─────────────────────────────────────────────────────────┤
│ Das Update konnte nicht installiert werden.             │
│ Fehler: Datenbank-Migration fehlgeschlagen (Schritt 4) │
│                                                         │
│ RechnungsFee wird auf vorherige Version zurückgesetzt.  │
│                                                         │
│ 🔄 Rollback läuft...                                    │
│ ████████████████████████████████████████░░░ 90%        │
│                                                         │
│ Deine Daten sind sicher und bleiben unverändert.       │
└─────────────────────────────────────────────────────────┘

Nach Rollback:

┌─────────────────────────────────────────────────────────┐
│ ✅ Rollback erfolgreich                                 │
├─────────────────────────────────────────────────────────┤
│ RechnungsFee läuft wieder auf Version 1.1.5             │
│                                                         │
│ Das Update wird in Kürze erneut versucht.              │
│ Fehlerprotokoll wurde an Entwickler gesendet.          │
│                                                         │
│ Du kannst jetzt normal weiterarbeiten.                 │
│                                                         │
│ [ Programm neu starten ]                                │
└─────────────────────────────────────────────────────────┘
```

---

### **6. Notfall-Szenario: Datenbank-Korruption nach Update**

**Extrem seltener Fall:** Update erfolgreich, aber später stellt sich heraus: DB korrupt

**Lösung:** Kategorie 10.6 (Wiederherstellung) greift!

1. **Beim nächsten Programmstart:**
   - DB-Integritätsprüfung (PRAGMA integrity_check)
   - Korruption erkannt

2. **Automatische Wiederherstellung:**
   - Versuch: Letztes Backup wiederherstellen
   - Backup von VOR dem Update existiert

3. **Bei Scheitern:**
   - Backup-Liste anzeigen (10.6)
   - User wählt älteres Backup (vor Update)

**Wichtig:**
- Wiederherstellung betrifft nur **Datenbank**
- Programm-Version bleibt **v1.2.0** (neue Version)
- User kann weiterarbeiten mit Daten von vor dem Update

---

### **UI-Konzept: Kein Rollback-Button**

**Alte Versionen (wenn manueller Rollback erlaubt wäre):**
```
Einstellungen → Updates
[ Auf Version 1.1.5 zurücksetzen ]  ← NICHT vorhanden!
```

**Neue Version (kein manueller Rollback):**
```
Einstellungen → Updates

┌─────────────────────────────────────────────┐
│ Updates                                     │
├─────────────────────────────────────────────┤
│ Aktuelle Version: 1.2.0                     │
│ Veröffentlicht: 01.01.2025                  │
│                                             │
│ ✅ Alle Updates installiert                 │
│                                             │
│ Nächste Update-Prüfung: In 6 Stunden       │
│                                             │
│ [ Jetzt nach Updates suchen ]              │
│ [ Update-Verlauf anzeigen ]                 │
│                                             │
│ ℹ️ Updates werden automatisch überprüft.   │
│   Bei wichtigen Updates wirst du           │
│   benachrichtigt.                           │
└─────────────────────────────────────────────┘

Update-Verlauf:
┌─────────────────────────────────────────────┐
│ v1.2.0  01.01.2025  Installiert ✅          │
│ v1.1.5  15.12.2024  Installiert ✅          │
│ v1.1.0  01.12.2024  Installiert ✅          │
└─────────────────────────────────────────────┘
```

**Kein "Auf alte Version zurücksetzen"-Button!**

---

### **Zusammenfassung der 3 Fragen:**

#### **1. Rollback bei Problemen nach Update?**
**✅ Entscheidung: NEIN (kein manueller Rollback)**

- Nur automatischer Rollback bei Update-Fehler (während Installation)
- Nach erfolgreichem Update: Kein Zurück
- Bei Problemen: Bug-Report → Hotfix in neuem Update

**Begründung:**
- Sicherheit (alle User aktuell)
- Compliance (GoBD, Steuerrecht)
- Einfachheit (keine Rückwärts-Migration)
- Support (einheitliche Versionen)

---

#### **2. Automatisches Backup vor Update?**
**✅ Entscheidung: JA (automatisch, immer)**

- Bereits in 10.7 dokumentiert
- Verschlüsselt, verifiziert
- Wird für automatischen Rollback verwendet

---

#### **3. Wie viele Versionen zurück möglich?**
**✅ Entscheidung: Nur letzte Version (1 Version zurück)**

- Reicht für automatischen Rollback
- Wenig Speicherplatz
- Alte Version wird bei jedem Update überschrieben

---

### **Vorteile dieser Lösung:**

- ✅ **Sicher:** Alle User auf aktueller Version, keine veralteten Versionen
- ✅ **Compliance:** GoBD, Steuerrecht, E-Rechnung garantiert
- ✅ **Einfach:** Keine komplexe Rückwärts-Migration
- ✅ **Support-freundlich:** Nur eine Version im Umlauf
- ✅ **Robust:** Automatischer Rollback bei Update-Fehler
- ✅ **Transparent:** Update-Verlauf einsehbar
- ✅ **Speicher-effizient:** Nur 1 alte Version archiviert (~200 MB)

---

### **Wichtige Klarstellung:**

**Unterschied zwischen:**

| Was | Wann | Automatisch? | Funktion |
|-----|------|--------------|----------|
| **Automatischer Rollback** | Bei Update-FEHLER (während Installation) | ✅ Ja | Zurück zu alter Version, User kann weiterarbeiten |
| **Manueller Rollback** | Nach erfolgreichem Update | ❌ NEIN (nicht vorhanden) | - |
| **Wiederherstellung (10.6)** | Bei DB-Korruption | ✅ Ja (mit Fallback) | Datenbank wiederherstellen, Version bleibt aktuell |

---

---

## **📋 Kategorie 11: Verschiedene Steuersätze** ✅ GEKLÄRT

**Detaildokumentation:** `docs/10-steuersaetze.md`

---

**Frage 11.1: Welche Steuersätze konkret?** ✅ GEKLÄRT

- [x] **19%** – Regelsteuersatz (Standard für Waren & Dienstleistungen, seit 01.01.2007)
- [x] **7%** – Ermäßigt: Bücher, Zeitungen, Lebensmittel, ÖPNV, Kulturveranstaltungen, Beherbergung (nur Übernachtung), künstlerische/schriftstellerische Leistungen (§12 Abs. 2 Nr. 7 UStG)
- [x] **0% Kleinunternehmer** (§19 UStG) – kein Vorsteuerabzug, Pflichthinweis auf Rechnung
- [x] **0% Reverse-Charge** (§13b UStG) – Bauleistungen, Gebäudereinigung, Altmetall, TK, Gas/Strom, CO2-Zertifikate
- [x] **0% Innergemeinschaftliche Lieferung** (§4 Nr. 1b UStG) – Warenlieferung EU, gültige USt-IdNr. erforderlich
- [x] **0% Ausfuhrlieferung/Export** (§4 Nr. 1a UStG) – Drittland, Ausfuhrnachweis erforderlich
- [x] **0% Sonstige** – Vermietung (§4 Nr. 12), Bildungsleistungen, Gesundheitsleistungen
- [x] **Historische Sätze** (Corona 01.07.–31.12.2020): 16% / 5% – automatische Erkennung anhand Rechnungsdatum
- [x] **Sondersätze Land-/Forstwirtschaft** (§24 UStG: 10,7% / 5,5%) → ⏸️ nicht in v1.0, erst v2.0

---

**Frage 11.2: Buchungslogik** ✅ GEKLÄRT

- [x] **Standard-Eingabemodus konfigurierbar:** B2C → Brutto, B2B → Netto (in Einstellungen wählbar)
- [x] **In jeder Maske umschaltbar** – flexibles Arbeiten je nach Beleg
- [x] **Automatische USt-Berechnung** in beide Richtungen:
  - Brutto eingeben → Netto & USt werden berechnet
  - Netto eingeben → USt & Brutto werden berechnet
- [x] **Kaufmännische Rundung** auf 2 Nachkommastellen (ROUND_HALF_UP)

---

**Frage 11.3: Mischrechnung** ✅ GEKLÄRT

- [x] Mehrere Positionen mit **verschiedenen Steuersätzen** pro Beleg möglich
- [x] **Automatische Summierung nach Steuersatz** (Netto 7%, Netto 19% etc. getrennt ausgewiesen)
- [x] Gesamtsummen (Netto, USt, Brutto) werden automatisch berechnet
- [x] DB-Schema: Tabelle `rechnungspositionen` mit `ust_satz` pro Position + Trigger für Summierung

---

**Frage 11.4: Vorsteuerabzug** ✅ GEKLÄRT

- [x] **Automatische Berechnung** bei Eingangsrechnungen (Checkbox "Vorsteuerabzug berechtigt")
- [x] **Bewirtungskosten** (§4 Abs. 5 Nr. 2 UStG): automatisch nur 70% abzugsfähig
- [x] **PKW gemischte Nutzung**: prozentuale Eingabe des geschäftlichen Anteils, Vorsteuer anteilig
- [x] **Kategorie-basierte Regeln**: Vorsteuer-% je Kategorie hinterlegt (100%, 70%, 0%)
- [x] **Kleinunternehmer**: kein Vorsteuerabzug (automatisch gesperrt)

---

**Versionsplanung:**
- **v1.0:** Alle Standard-Steuersätze, Brutto/Netto-Umschaltung, Mischrechnung, Vorsteuer mit Teilabzug ✅
- **v1.1:** Branchenvorlagen für Steuersätze, erweiterter Vorsteuer-Import historischer Rechnungen
- **v2.0:** §24 UStG Land-/Forstwirtschaft, Differenzbesteuerung (§25a), Margenbesteuerung

---

## **📋 Kategorie 12: Hilfe-System** ✅ GEKLÄRT

**Frage 12.1: Umfang der Hilfe:**
- Tooltips auf jeder Eingabemaske (Fragezeichen-Icon).
- Kontextsensitive Hilfe-Texte (abhängig von aktueller Seite).
- Video-Tutorials (eingebettet oder YouTube-Links) - später
- PDF-Handbuch zum Download.
- Interaktive Touren (z.B. bei Erstnutzung) mit Option nicht wieder anzeigen / Einstellungen: erneut aktivieren
- evt. mardown Wiki

**Frage 12.2: Hilfe-Inhalte:**
- Technische Hilfe (wie bediene ich das Programm).
- Fachliche Hilfe (was ist eine EÜR, was bedeutet §19 UStG).
- kombiniert

**Frage 12.3: Steuerberatung:**
- Disclaimer dass keine Steuerberatung gegeben wird.
- Links zu offiziellen Quellen (BMF, ELSTER, Bundesagentur).
- Empfehlung "Bei Unsicherheit Steuerberater konsultieren.

**Frage 12.4: Community/Support:**
- Community-Forum für Austausch zwischen Nutzern.
- FAQ-Bereich
- GitHub Issues für Bug-Reports.
- Kein E-Mail-Support.

**Frage 12.5: Sprache:**
- Deutsch und Englisch
- Mehrsprachigkeit später erweiterbar.

---

## **📋 Kategorie 13: Scope & Priorisierung** ✅ GEKLÄRT

**Frage 13.1: MVP-Definition (Version 1.0)** ✅ GEKLÄRT
**Entscheidung: Komfortables MVP** (Must-Have + wichtigste Should-Haves)

---

### **🎯 Must-Have (Prio 1) - MUSS in v1.0**

**Kern-Buchhaltung:**
- [x] Stammdaten-Verwaltung (Unternehmen, Kunden, Lieferanten)
- [x] Eingangsrechnungen erfassen (manuell)
- [x] Eingangsrechnungen verwalten (Liste, Filter, Suche)
- [x] Kassenbuch führen (mit GoBD-Konformität)
- [x] Backup-Funktion (manuell + Exit-Backup)

**Bank-Integration:**
- [x] Bank-CSV-Import (Format-Erkennung für 10+ Banken)
- [x] Zahlungsabgleich (Bank → Rechnungen)

**Steuer-Exporte (Grundlagen):**
- [x] EÜR-Export (Einnahmen-Überschuss-Rechnung für ELSTER)
- [x] UStVA-Daten-Export (für ELSTER oder Steuerberater)
- [x] Anlage EKS-Export (Agentur für Arbeit)

**Grundlegende UI:**
- [x] Dashboard (Übersicht, wichtigste KPIs)
- [x] Hilfe-System (Tooltips, kontextsensitive Hilfe)
- [x] Onboarding / Ersteinrichtungs-Assistent

---

### **💡 Should-Have (Prio 2) - In v1.0 inkludiert (Komfortables MVP)**

**Wichtigste Should-Haves für v1.0:**
- [x] ZUGFeRD/XRechnung-Import (E-Rechnungen werden Pflicht!)
- [x] DATEV-Export (SKR03/04, CSV-Format)
- [x] UStVA-Vorschau-PDF (zum Ausdrucken/Prüfen vor ELSTER)
- [x] Ausgangsrechnungen erfassen (für UStVA-Umsätze, Read-Only!)

**Weitere Should-Haves (können in v1.0 oder v1.1):**
- [ ] PDF-Import (einfacher Upload, OHNE OCR vorerst)
- [ ] Anlagenverwaltung (AfA-Berechnung für EÜR)
- [ ] Wiederkehrende Rechnungen (z.B. monatliche Miete)
- [ ] Ausgangsrechnungen-Liste (Verwaltung)

---

### **🔮 Could-Have (Prio 3) - Für v1.1/1.2**

**Erweiterte Importe:**
- [ ] Import aus hellocash
- [ ] Import aus Fakturama
- [ ] Import aus Rechnungsassistent
- [ ] PDF-Import mit OCR (Tesseract, KI-gestützt)

**Zusätzliche Exporte:**
- [ ] AGENDA-Export (für DATEV-Alternative)
- [ ] Erweiterte Excel-Berichte

**UX-Verbesserungen:**
- [ ] Dashboard mit interaktiven Charts
- [ ] Erweiterte Filter & Suchfunktionen
- [ ] Massenoperationen (mehrere Rechnungen gleichzeitig)
- [ ] Tags/Labels für Rechnungen

**Mobile & Progressive:**
- [ ] Mobile PWA (Responsive Design)
- [ ] Offline-Modus

**Automatisierung:**
- [ ] Automatische Kategorisierung (KI-basiert)
- [ ] Regel-basierte Buchungen

---

### **❌ Won't-Have in v1.0 - Explizit NICHT in v1.0**

**Rechnungsstellung:**
- [x] Rechnungsschreiben (Ausgangsrechnungen erstellen/drucken)
- [x] Angebote erstellen
- [x] Mahnwesen

**Hardware-Integration:**
- [x] POS-Kassenbuch mit TSE (Technische Sicherheitseinrichtung)
- [x] Bondrucker-Anbindung
- [x] Kartenleser-Integration

**Live-Anbindungen:**
- [x] ELSTER-Direktanbindung (API-Integration)
- [x] Bank-API (Live-Zugriff, PSD2)
- [x] PayPal/Stripe-Integration

**Enterprise-Features:**
- [x] Multi-User / Mehrbenutzerbetrieb
- [x] Mandantenfähigkeit (mehrere Firmen)
- [x] Rechteverwaltung / Rollen

**Erweiterte Funktionen:**
- [x] Lohnbuchhaltung
- [x] Warenwirtschaft / Lagerverwaltung
- [x] CRM (Kundenbeziehungsmanagement)
- [x] Projekt-Zeiterfassung
- [x] Reisekostenabrechnung
- [x] Multi-Währung (nur EUR in v1.0)

---

**📊 Zusammenfassung v1.0 (Komfortables MVP):**
- **13 Must-Have Features** (Kern-Funktionalität)
- **4 Should-Have Features** (für vollständigen Anwendungsfall)
- **= 17 Features gesamt in v1.0**
- Geschätzte Entwicklungszeit: 4-6 Monate

---

**Frage 13.2: Reihenfolge der Entwicklung** ✅ GEKLÄRT

**Entscheidung: Phasenweise Entwicklung, Stabilität vor Geschwindigkeit**

### **Phase 1: Fundament (Wochen 1-4) 🏗️**
- [x] Projekt-Setup (Tauri + DB + Basis-UI)
- [x] Stammdaten-Verwaltung (Unternehmen, Kunden, Lieferanten)
- [x] **✅ Meilenstein 1:** Stammdaten erfassbar → Test-Version 0.1

### **Phase 2: Kern-Buchhaltung (Wochen 5-10) 📊**
- [x] Eingangsrechnungen erfassen & verwalten
- [x] Kassenbuch (mit GoBD-Konformität)
- [x] **✅ Meilenstein 2:** Erste nutzbare Version → Test-Version 0.2

### **Phase 3: Bank-Integration (Wochen 11-14) 🏦**
- [x] Bank-CSV-Import (Format-Erkennung)
- [x] Zahlungsabgleich (automatisch + manuell)
- [x] **✅ Meilenstein 3:** Hauptarbeit automatisiert → Test-Version 0.3

### **Phase 4: Dashboard & Backup (Wochen 15-16) 📈**
- [x] Dashboard (KPIs, Übersicht)
- [x] Backup-Funktion (manuell + Exit-Backup)
- [x] **✅ Meilenstein 4:** Produktiv nutzbar → Test-Version 0.4

### **Phase 5: Steuer-Exporte (Wochen 17-22) 💰**
- [x] EÜR-Export (CSV für ELSTER)
- [x] UStVA-Export (CSV/XML)
- [x] UStVA-Vorschau-PDF
- [x] Anlage EKS-Export
- [x] **✅ Meilenstein 5:** Steuerlich vollständig → Test-Version 0.5

### **Phase 6: Erweiterte Features (Wochen 23-26) ⭐**
- [x] DATEV-Export (SKR03/04)
- [x] ZUGFeRD/XRechnung-Import
- [x] Ausgangsrechnungen erfassen (Read-Only)
- [x] **✅ Meilenstein 6:** Alle 17 Features fertig → Test-Version 0.6

### **Phase 7: UX & Hilfe (Wochen 27-28) 🎨**
- [x] Hilfe-System (Tooltips, Kontexthilfe)
- [x] Onboarding & Setup-Assistent
- [x] **✅ Meilenstein 7:** Benutzerfreundlich → Test-Version 0.7

### **Phase 8: Polishing & Testing (Wochen 29-32) 🔧**
- [x] Unit- & Integration-Tests
- [x] Bug-Fixing & Performance-Optimierung
- [x] PDF-Handbuch schreiben
- [x] **✅ Meilenstein 8:** Stabil & dokumentiert → Test-Version 0.8

### **Phase 9: Beta & Release (Wochen 33-36) 🚀**
- [x] Private Beta (5-10 Tester)
- [x] Desktop-Installer (Windows, macOS, Linux)
- [x] Release Preparation
- [x] **✅ Meilenstein 9:** v1.0 Release! 🎉

**📊 Gesamt:** 9 Phasen, 9 Meilensteine, 9 Test-Versionen, ~36 Wochen (realistisch)

**⚠️ Wichtig:** Stabilität hat Priorität! Jede Phase wird gründlich getestet.

---

**Frage 13.3: Zeitrahmen** ✅ GEKLÄRT
- [x] **Flexibel, aber realistisch:** 4-6 Monate (Best Case) bis 9 Monate (realistisch mit Stabilität)
- [x] **Stabilität vor Geschwindigkeit:** Lieber länger entwickeln, dafür stabil

**Frage 13.4: Meilensteine & Testing** ✅ GEKLÄRT
- [x] **Test-Versionen:** Nach jedem Meilenstein (0.1 bis 0.8, dann v1.0)
- [x] **Arbeitsweise:** Phasenweise (nicht agil/Sprints)
- [x] **Fokus:** Gründliches Testen jeder Phase vor Weitergehen

---

## **📋 GitHub Community Issues** ✅ ANALYSIERT

---

### **Issue #14: Rechnung AN gemeinnützigen Verein (§4 Nr. 21 UStG)** ✅ ANALYSIERT

**Datum:** 2026-02-22
**Issue:** https://github.com/nicolettas-muggelbude/RechnungsFee/issues/14
**User:** @Feedesiree
**Priorität (User):** Sehr wichtig
**Bereich:** Rechnungen, Steuer, Kundenstamm

---

#### **Szenario**

Ein Selbstständiger (Dozent/Lehrer/Kursanbieter) mit USt-Pflicht stellt Rechnungen **an** einen gemeinnützigen Verein für **Bildungsleistungen** (Unterricht, Kurse, Seminare). Unter bestimmten Voraussetzungen kann die Rechnung ohne Umsatzsteuer ausgestellt werden.

**Wichtig:** Dies ist das **umgekehrte Szenario** zu Kategorie 8.9 (Verein als RechnungsFee-Nutzer). Hier ist der Verein der **Kunde**, nicht der Nutzer.

---

#### **Rechtliche Entscheidungslogik (§4 Nr. 21 UStG)**

```
Bist du Kleinunternehmer (§19 UStG)?
  → Ja: Keine USt auf der Rechnung (unabhängig vom Verein) ✅

  → Nein (du weist USt aus):
     Hat der Verein eine Bescheinigung nach §4 Nr. 21 Buchst. b) bb) UStG?
       → Ja: Handelt es sich um eine Bildungsleistung (Unterricht, Kurs, Seminar)?
              → Ja: Rechnung OHNE USt möglich ✅ (Steuerbefreiung greift)
              → Nein: Rechnung MIT USt (z.B. reine Verwaltungsleistung)
       → Nein: Rechnung MIT USt (du bist USt-pflichtig)
```

**Die Bescheinigung nach §4 Nr. 21 Buchst. b) bb) UStG:**
- Amtliche Bescheinigung der zuständigen Landesbehörde
- Bestätigt: Verein ist eine allgemein- oder berufsbildende Einrichtung
- Der Verein muss sie dem Rechnungssteller vorlegen
- Aufbewahrungspflicht: 10 Jahre (Nachweis für Finanzamt)

---

#### **Geplante Umsetzung in RechnungsFee**

**v1.0 (MVP) – bereits eingeplant:**
- [x] Steuerbefreiungsgrund manuell eintragbar (z.B. "§4 Nr. 21 UStG")
- [x] 0% USt auswählbar mit Pflichtangabe des Grundes
- [x] Rechnung enthält automatisch den korrekten Hinweistext

**v1.1 – Kundenstamm-Erweiterung:**
- [ ] Verein-Flag im Kundenstamm: Checkbox "Gemeinnütziger Verein"
- [ ] Bescheinigungsfelder: Nummer, ausstellende Behörde, Gültigkeitsdatum
- [ ] Automatische Warnung bei fehlender oder abgelaufener Bescheinigung

**v1.2 – Geführter Steuer-Assistent:**
- [ ] Assistent bei Rechnungserstellung für Vereinskunden:
  1. "Ist dies ein gemeinnütziger Verein?"
  2. "Liegt eine Bescheinigung nach §4 Nr. 21 Buchst. b) bb) UStG vor?"
  3. "Handelt es sich um eine Bildungsleistung?"
  → Automatische USt-Auswahl (0% oder 19%)
  → Automatischer Textbaustein auf der Rechnung

---

#### **Antwort gepostet**

GitHub-Kommentar gepostet am 2026-02-22:
https://github.com/nicolettas-muggelbude/RechnungsFee/issues/14#issuecomment-3940487903

Rückfragen an User offen:
- Liegt die Bescheinigung immer schriftlich vor?
- Nur Bildungsleistungen oder auch andere Leistungen?
- Wie viele Vereins-Kunden ca.?

---

## **Nächste Schritte:**

Bitte beantworte die Kategorien 2-13 wann du Zeit hast. Du kannst:
- Alle auf einmal beantworten
- Schrittweise (z.B. täglich 2-3 Kategorien)
- Direkt in dieser Datei ergänzen
- Oder separate Antwort-Datei erstellen

**Ich warte auf deine Antworten und erstelle dann:**
1. Detaillierte Projektarchitektur
2. Datenbank-Schema
3. API-Spezifikation
4. Priorisierte Roadmap
5. Technology-Stack-Empfehlung
