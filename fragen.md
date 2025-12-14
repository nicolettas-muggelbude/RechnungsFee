# Offene Fragen zu RechnungsFee

## Status:
- ✅ Kategorie 1 (Kassenbuch) geklärt
- ✅ Kategorie 2 (PDF/E-Rechnungs-Import) geklärt
- ✅ Kategorie 3 (Anlage EKS) geklärt
- ✅ Kategorie 4 (DATEV-Export) geklärt
- ✅ Kategorie 5 (Bank-Integration) vollständig geklärt - 9 Banken, Auto-Erkennung, Matching
- ✅ Kategorie 6 (UStVA) vollständig geklärt - CSV/XML-Export, Kleinunternehmer, Zeiträume
- ✅ Kategorie 7 (EÜR) vollständig geklärt - Master-Kategorien, AfA-Rechner, Anlagenverwaltung
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

**Unterstützte Banken (9):**
- [x] Commerzbank
- [x] DKB
- [x] ING (2 Varianten: normal + mit Saldo)
- [x] PayPal
- [x] Sparkasse LZO (3 Varianten: CAMT v2, CAMT v8, MT940)
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

## **📋 Kategorie 8: Stammdaten-Erfassung (Ersteinrichtung)**

**Frage 8.1: Unternehmerdaten - welche Felder?**
- Name (Vor- und Nachname / Firmenname)
- Rechtsform (Einzelunternehmer, GbR, UG, GmbH, etc.)
- Anschrift (Straße, PLZ, Ort)
- Kontaktdaten (E-Mail, Telefon, Website?)
- Steuernummer
- USt-IdNr. (falls vorhanden)
- Finanzamt (zuständiges FA)
- Steuer-Identifikationsnummer (persönliche)
- Bankverbindung (für Ausgangsrechnungen)

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

**Frage 8.6: Kundenstammdaten - Felder:**
- Pflichtfelder: Name, Anschrift
- Optional: E-Mail, Telefon, Website, Ansprechpartner
- USt-IdNr. (bei Geschäftskunden)
- Kundennummer (automatisch oder manuell)?
- Zahlungsziel (Standard z.B. 14 Tage, individuell änderbar?)
- Kategorisierung:
  - Privat/Geschäftskunde
  - Inland/EU/Drittland (wichtig für USt)
- Automatische USt-IdNr.-Prüfung über EU-API?

**Frage 8.7: Lieferantenstammdaten:**
- Ähnliche Felder wie Kunden?
- Oder minimalistischer (nur Name, Anschrift, USt-IdNr.)?
- Lieferantennummer?

**Frage 8.8: Produktstammdaten (für späteres Rechnungsschreib-Modul):**
- Schon in Ersteinrichtung erfassen oder erst später wenn Modul aktiv?
- Falls jetzt: Artikel/Dienstleistungen mit Bezeichnung, Preis, Steuersatz?
- Artikelnummern?
- Einheiten (Stück, Stunden, Pauschal)?

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
