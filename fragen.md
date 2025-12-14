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
- ✅ Kategorie 8.6 (Kundenstammdaten) vollständig geklärt - 9 Punkte inkl. VIES-API, Inland/EU/Drittland
- ✅ Kategorie 8.7 (Lieferantenstammdaten) geklärt - Ähnlich Kunden, einfacher, VIES-API
- ✅ Kategorie 8.8 (Artikel & Dienstleistungen) geklärt - Gemeinsamer Stamm, 3 Typen, EAN auch bei DL
- ✅ Kategorie 12 (Hilfe-System) geklärt
- ✅ Kategorie 13 (Scope & Priorisierung) vollständig geklärt - Komfortables MVP, 9 Phasen

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

## **📋 Kategorie 8: Stammdaten-Erfassung (Ersteinrichtung)** ⏳ TEILWEISE GEKLÄRT

**Frage 8.1: Unternehmerdaten - welche Felder?** ✅ GEKLÄRT

**Entscheidung: Optimierte Stammdaten-Erfassung**

**Pflichtfelder (ohne geht's nicht):**

**Grunddaten:**
- [x] **Name des Unternehmens** * (Pflicht)
- [x] **Rechtsform** * (Dropdown: Einzelunternehmer, GbR, UG, GmbH, AG, e.K., Freiberufler, Sonstige)
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

**Frage 8.2: Steuerliche Einstellungen:**
- §19 UStG (Kleinunternehmer) oder Regelbesteuerung - Radio-Button?
- Bei Regelbesteuerung: Voranmeldungszeitraum (monatlich/quartalsweise)?
- Ist-Versteuerung oder Soll-Versteuerung?
- Dauerfristverlängerung ja/nein?

**Frage 8.3: Kontenrahmen:**
- SKR03 oder SKR04 bei Einrichtung wählen?
- Erklärung für Laien (wann welcher Rahmen)?
- Kann später gewechselt werden?

**Frage 8.4: Geschäftsjahr:**
- Standard: Kalenderjahr (01.01. - 31.12.)?
- Abweichendes Wirtschaftsjahr möglich?
- Wichtig für EÜR und Jahresabschluss

**Frage 8.5: Bank-/Konteneinrichtung:**
- Konten direkt bei Ersteinrichtung anlegen?
- Oder später separat?
- Welche Infos: Bankname, IBAN, Typ (Geschäftskonto/Privat)?

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

## **📋 Kategorie 9: Import-Schnittstellen (hellocash, Rechnungsassistent, Fakturama)**

**Frage 9.1: Priorität:**
- Welches Tool zuerst? Hellocash, Rechnungsassistent oder Fakturama?
- Oder alle drei parallel?

**Frage 9.2: hellocash - Daten-Formate:**
- Welche Formate exportiert hellocash?
- CSV, JSON, XML, direkte DB-Anbindung?
- Hast du Beispiel-Exporte?

**Frage 9.3: Rechnungsassistent - Daten-Formate:**
- Welche Formate?
- Struktur bekannt?

**Frage 9.4: Fakturama - Daten-Formate:**
- Fakturama nutzt H2-Datenbank - direkter DB-Import?
- Oder CSV-Export aus Fakturama?

**Frage 9.5: Import-Umfang:**
- Nur Rechnungen (Eingang/Ausgang)?
- Auch Kundenstammdaten?
- Auch Produktstammdaten?
- Historische Daten komplett migrieren oder nur ab Stichtag?

**Frage 9.6: Duplikat-Erkennung:**
- Was wenn Daten mehrfach importiert werden?
- Automatische Deduplizierung anhand Rechnungsnummer?
- Warnung bei Duplikaten?
- Überschreiben oder überspringen?

---

## **📋 Kategorie 10: Backup & Update**

**Frage 10.1: Backup-Speicherort:**
- Nur Nextcloud oder auch lokal/USB-Stick/Netzlaufwerk?
- Mehrere Backup-Ziele parallel möglich?
- Cloud-Backup optional (manche wollen nur lokal)?

**Frage 10.2: Backup-Verschlüsselung:**
- Verschlüsselt oder unverschlüsselt?
- Wenn verschlüsselt: Mit Master-Passwort oder separatem Backup-Passwort?
- Verschlüsselung optional oder Pflicht?

**Frage 10.3: Backup-Versionen:**
- Wie viele Backup-Versionen aufbewahren (3, 7, 30)?
- Automatische Rotation (älteste löschen)?
- Zeitstempel im Dateinamen?

**Frage 10.4: Backup bei Programmende:**
- Immer automatisch oder nur wenn Änderungen?
- Fortschrittsanzeige oder im Hintergrund?
- Was bei Backup-Fehler? Programm trotzdem beenden?

**Frage 10.5: Manuelles Backup:**
- Über Menü "Jetzt sichern"?
- Ziel wählbar oder nur Standard-Ziel?
- Backup-Protokoll/Log einsehbar?

**Frage 10.6: Wiederherstellung:**
- Automatische Wiederherstellung bei Programmstart (wenn DB korrupt)?
- Manuell aus Backup-Liste wählen?
- Vorschau welche Backup-Version (Datum, Größe)?

**Frage 10.7: Auto-Update:**
- Zwingend oder optional (Einstellung)?
- Silent-Update (automatisch im Hintergrund) oder mit Nachfrage?
- Update-Kanal: Stable, Beta, Nightly?
- Update-Benachrichtigung auch wenn Auto-Update aus?

**Frage 10.8: Rollback:**
- Rollback bei Problemen nach Update?
- Automatisches Backup vor Update?
- Wie viele Versionen zurück möglich?

---

## **📋 Kategorie 11: Verschiedene Steuersätze**

**Frage 11.1: Welche Steuersätze konkret?**
- 19% (Regelsteuersatz)
- 7% (ermäßigt - Bücher, Lebensmittel, etc.)
- 0% (steuerbefreit):
  - Kleinunternehmer (§19 UStG)
  - Reverse-Charge (§13b UStG)
  - Innergemeinschaftliche Lieferung
  - Ausfuhrlieferung (Export)
- Historische Sätze (z.B. 16%/5% aus Corona-Zeit für alte Rechnungen)?
- Sondersätze (z.B. Künstler/Schriftsteller)?

**Frage 11.2: Buchungslogik:**
- Eingabe Brutto oder Netto?
- Umschaltbar (mal so, mal so)?
- Automatische Umsatzsteuer-Berechnung beim Erfassen?

**Frage 11.3: Mischrechnung:**
- Verschiedene Steuersätze pro Position auf einer Rechnung?
- Z.B. Position 1: Buch 7%, Position 2: Beratung 19%
- Automatische Summierung nach Steuersatz?

**Frage 11.4: Vorsteuerabzug:**
- Bei Eingangsrechnungen: Vorsteuer automatisch berechnen?
- Nicht abzugsfähige Vorsteuer (z.B. Bewirtung 30%, PKW)?
- Vorsteueraufteilung bei gemischter Nutzung?

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
