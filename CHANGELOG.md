# Changelog

Alle wesentlichen Änderungen an RechnungsFee werden hier dokumentiert.

Das Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/).  
Versionen werden durch Git-Tags gesetzt – `git tag v0.x.y && git push --tags`.

---

## [v0.3.28] – Juni 2026

### 🐛 Behoben
- Lagerführung: Direkt finalisierte Rechnungen (kein Entwurf-Zwischenschritt) haben den Artikelbestand nicht abgebucht – Session hat `autoflush=False`, Positionen waren beim Lager-Buchen noch nicht in der DB; `db.flush()` + `db.expire()` vor `_lager_buchen()` behebt das (Issue #173)

---

## [v0.3.27] – Juni 2026

### 🐛 Behoben
- DATEV-Export: Stornobuchungen, die vor v0.3.24 erstellt wurden, haben den BU-Schlüssel jetzt wieder korrekt (z. B. BU 9 für VoSt 19 %); Regression durch vorherigen Fix – alter Code speicherte `vorsteuerabzug=False` auf Stornos, neuer Algorithmus schlug deshalb fälschlich BU="" nach (Issue #163)
- Anlage G: Beschriftung Z. 52 im UI war noch nicht aktualisiert – zeigt jetzt korrekt „Gewerbesteuer-Vorauszahlungen lt. Journal" statt „Tatsächlich zu zahlende Gewerbesteuer (lt. Journal)"; PDF-Beschriftung war bereits korrekt (Issue #183)
- Anlage G: Anrechnungsfaktor §35 EStG im UI war noch 3,8 – zeigt und rechnet jetzt korrekt mit 4,0 (gilt seit VZ 2020, JStG 2019); PDF war bereits korrekt (Issue #182)
- Anlage G: PDF-Export schlug mit „Failed to fetch" fehl wenn ein Hebesatz eingetragen war und Gewerbesteuer-Buchungen im Journal vorhanden waren – Python TypeError (float ÷ Decimal) im Hebesatz-Rückrechnungs-Code behoben (Issue #187)

### 🔧 Verbessert
- Anlage G: Gewerbesteuer-Messbetrag (Z. 51) wird automatisch aus dem Jahresgewinn geschätzt und als Vorschlagswert vorbelegt – mit echtem Wert aus GewSt-Festsetzungsbescheid überschreiben; Hebesatz-Eingabe in den GewSt-Abschnitt verschoben; §35 EStG Deckelung korrekt implementiert: anrechenbarer Betrag = Messbetrag × min(4,0; Hebesatz%) (Issue #182)

---

## [v0.3.26] – Juni 2026

### 🐛 Behoben
- Anlage G: Gewerbeertrag wird jetzt vor der Messbetrag-Schätzung auf volle 100 € abgerundet (§11 Abs. 1 GewStG); Anrechnungsfaktor §35 EStG von 3,8 auf 4,0 korrigiert (gilt seit VZ 2020); Z. 52 umbenannt von „Tatsächlich zu zahlende Gewerbesteuer" in „Gewerbesteuer-Vorauszahlungen lt. Journal" (Issue #183)
- EÜR: Betriebseinnahmen (19 % und 7 %) wurden fälschlich in Zeile 12 eingetragen – laut Anlage EÜR 2025 (BMF) ist Zeile 12 nur für Kleinunternehmer (§19 UStG); umsatzsteuerpflichtige Einnahmen (7 % und 19 % gemeinsam) gehören in Zeile 15, steuerfreie in Zeile 16; Betriebseinnahmen (0 %) = Kleinunternehmer korrekt auf Zeile 12 (Issue #185)
- Anlage G: Stammdaten-Feld „Bezeichnung des Gewerbes" (Z. 4) ließ sich nicht speichern – Feld fehlte im API-Schema; eigenes Feld statt Berufsbezeichnung, erscheint in Stammdaten bei gewerblicher/gemischter Tätigkeit
- DATEV-Export: Buchungen ohne Sachkonto (z. B. Kassenanfangsbestand) wurden fälschlich als „übersprungen" gezählt obwohl sie exportiert wurden; jetzt eigene amber-Meldung „ohne Sachkonto – im DATEV-Programm ergänzen" statt irreführender Übersprungen-Warnung (Issue #163)
- Kategorien: Gewerbesteuer hatte im SKR03 das falsche Konto 7600 – im SKR03 gibt es kein Konto 7600; korrekt ist 4320 (Gewerbesteuer); SKR04 7610 war bereits korrekt (SKR04 7600 = Körperschaftsteuer) (Issue #186)

### 🔧 Verbessert
- Kategorien: Im Bearbeitungsmodus können jetzt auch Systemkategorien ihre EÜR-Zeile inline anpassen – kleines Zahlenfeld direkt in der Tabellenspalte, leer = kein EÜR-Eintrag; SKR03/04-Konten und Verwendungsbeispiele waren für Systemkategorien bereits editierbar (Issue #186)

### ✨ Neu
- Journal: Buchungen können innerhalb von 5 Minuten nach der Erstellung direkt bearbeitet werden – Bearbeiten-Button erscheint im Detailbereich; nach Ablauf des Fensters wird automatisch storniert und neu gebucht (GoBD-konform) (Issue #184)

---

## [v0.3.25] – Juni 2026

### 🔧 Verbessert
- GoBD: Absender-Snapshot bei Finalisierung – Stammdatenänderungen verändern nicht mehr die Absenderadresse und IBAN auf bereits finalisierten Dokumenten (Rechnungen, Lieferscheine, Angebote, Aufträge, Proforma, Gutschriften)
- Anlage G: ELSTER-KZ-Badges (KZ 10 Gewinn / KZ 11 Verlust) für laufende Einkünfte ergänzt; Z. 51 (Messbetrag), Z. 52 (gezahlte Gewerbesteuer) und Hebesatz nur bei Gewerbesteuerpflicht sichtbar
- Anlage S: ELSTER-KZ-Badge (KZ 100) für Gewinn/Verlust aus freiberuflicher Tätigkeit ergänzt; Anlage S hat kein separates Verlust-KZ – Gewinn und Verlust werden im selben Feld (KZ 100) eingetragen

---

## [v0.3.24] – Juni 2026

### ✨ Neu
- Anlage G – Einkünfte aus Gewerbebetrieb (§15 EStG): neue Auswertung für Gewerbetreibende und gemischte Tätigkeiten; zeigt Gewinn/Verlust aus der EÜR mit ELSTER-KZ-Badges (KZ 10/11); gezahlte Gewerbesteuer (Z. 52) wird automatisch aus dem Journal gezogen; Hebesatz-Eingabe berechnet den Messbetrag (Z. 51) und §35-Anrechnungsbetrag automatisch; PDF-Export

### 🔧 Verbessert
- Anlage S/G: Sichtbarkeitssteuerung nach Tätigkeitsart – Anlage S erscheint nur bei Freiberuflich/Gemischt, Anlage G nur bei Gewerblich/Gemischt; bei Gemischt erscheint jeweils ein Hinweis auf die andere Anlage (Issue #180)
- Detail-Panel (stornierte Rechnungen): Stornodatum und Stornorechnung-Nr. werden jetzt angezeigt; „Fällig am" wird ausgeblendet (Issue #178)

### 🐛 Behoben
- Buchungsvorlagen: Badge mit fälligen Buchungen im Navigationsmenü wurde nach dem Buchen nicht sofort aktualisiert – Query-Cache wird jetzt direkt invalidiert (Issue #181)
- Anlage S/G PDF: schwarzes Fenster in Tauri – Content-Disposition war auf attachment gesetzt, WebView2 versuchte Download statt Anzeige; auf inline geändert (Issue #179)

---

## [v0.3.22] – Juni 2026

### ✨ Neu
- Backup: SMB-Unterstützung – Backup-Ziel kann jetzt ein SMB-Netzwerkpfad sein (smb://server/freigabe/pfad); Benutzername und Passwort werden separat gespeichert; kein System-Mount nötig (Issue #176)
- Stornorechnung: eigener Nummernkreis STORNO-JJNNNN – jede Stornierung bekommt eine eindeutige Stornorechnung-Nummer, sichtbar im PDF-Titel und Kopfzeile; Format über Einstellungen → Nummernkreise anpassbar (Issue #178)
- Gutschrift: eigener Nummernkreis GS-YY#### – Gutschriften haben jetzt einen separaten Zähler statt den Ausgangsrechnungs-Zähler zu teilen; Format über Einstellungen → Nummernkreise anpassbar

### 🔧 Verbessert
- Backup: Pfade auf Systemlaufwerken (C:\\, /home, /root, /Users, …) werden beim automatischen Backup übersprungen – ein Backup auf derselben Platte schützt nicht vor Festplattenausfall; das Formular zeigt einen Hinweis beim Eintippen
- Stornierte Rechnungen: Ansehen zeigt die Original-Rechnung (vor dem Storno); neuer Button „Stornorechnung drucken" für das Stornorechnung-PDF; Mail-Versand als „Stornorechnung senden" jetzt verfügbar (Issue #178)
- Berechnungen: Zwischenergebnisse (Positionsrabatt, USt pro Position, Summierung) werden jetzt auf 4 Dezimalstellen gerundet statt 2 – reduziert Rundungsfehler bei vielen Positionen; in der DB gespeicherte Endwerte bleiben 2-stellig

### 🐛 Behoben
- Nummernkreis-Format: einzelne Buchstaben N in Präfixen (z. B. STORNO) wurden fälschlich als Nummern-Platzhalter interpretiert – Ausgabe war STOR10 statt STORNO-260001
- Lagerführung: Bestand wurde nicht reduziert wenn aus dem Formular finalisiert wurde (Entwurf bearbeiten → Speichern & Finalisieren); SQLAlchemy lieferte nach dem Positions-Neuladen eine leere Liste an _lager_buchen (Issue #173)
- Lagerführung: Finalisieren direkt aus dem Formular (neuer Entwurf → Finalisieren ohne Umweg über Detail-Panel) buchte den Bestand nicht ab (Issue #173)

---

## [v0.3.21] – Juni 2026

### ✨ Neu
- Anlage S – Einkünfte aus selbstständiger Arbeit: Anzeigehilfe für die Einkommensteuererklärung (§18 EStG); zeigt Gewinn/Verlust aus der EÜR, Berufsbezeichnung, Steuernummer und Finanzamt mit den zugehörigen ELSTER-Zeilen; KFZ-Hinweis wenn Anlagegüter mit Privatanteil vorhanden; PDF-Export
- „Ansehen"-Button für finalisierte Rechnungen: öffnet das aktuelle PDF in einem eigenen Fenster ohne Druckdialog und ohne Statusänderung – setzt weder ausgegeben noch speichert es ein Original

### 🔧 Verbessert
- Anlage S: Oberfläche im gleichen Stil wie EÜR und Jahres-USt (blaue Zeilen-Badges, grauer Abschnittsheader, PDF-Button in der Jahresauswahlleiste)
- Art.-Nr.-Spalte im Rechnungs-PDF: Automatischer Zeilenumbruch bei langen Artikelcodes (SKU/EAN) – vorher wurde Text abgeschnitten; gilt für beide PDF-Vorlagen und den Lieferschein
- Lagerführung: Bestandshinweis jetzt auch im Auftragsformular – gelbe Warnung wenn die bestellte Menge den verfügbaren Bestand übersteigt (ohne Blockierung, da der Bestand erst beim Rechnungs-Finalisieren gebucht wird) (Issue #177)

### 🐛 Behoben
- DATEV-Export: Stornobuchungen hatten einen falschen BU-Schlüssel – Storno einer Ausgabe (z. B. Miete VoSt 19%) bekam BU 3 (USt) statt BU 9 (VoSt); jetzt korrekt: Storno übernimmt immer den BU-Schlüssel der Originalbuchung (Issue #163)
- DATEV-Export: Buchungen ohne Sachkonto (z. B. Kassenanfangsbestand) wurden lautlos übersprungen; jetzt werden sie mit leerem Konto exportiert – DATEV zeigt einen Importfehler den der Steuerberater sieht und korrigieren kann (Issue #163)
- Rechnungsrabatt: Formular zeigte Festbetrag (€) fälschlich als Prozentwert an; PDF berechnete die USt auf den Bruttobetrag vor Rabatt statt nach Rabatt (Issue #170)
- Artikel: Beschreibung löschen wurde nicht gespeichert; Beschreibung wurde beim Einfügen in eine Rechnungsposition nicht übernommen (Issue #172)
- Lagerführung: Bestand wurde nicht reduziert wenn direkt aus dem Formular finalisiert wurde (nur der Entwurf→Finalisieren-Weg buchte korrekt); Storno erhöhte den Bestand dadurch fälschlich (Issue #173)
- Lagerführung: Finalisierungssperre bei Bestandsunterschreitung wirkte nur im Entwurf→Finalisieren-Pfad, nicht beim direkten Finalisieren aus dem Formular (Issue #173)

---

## [v0.3.20] – Juni 2026

### ✨ Neu
- Lagerführung-Light (Issue #173): Bestandsführung für Artikel – global aktivierbar (Einstellungen → Unternehmen → Artikel), dann pro Artikel einschalten; Anfangsbestand, Mindestbestand und „Minusbestand erlaubt"-Schalter im Artikelformular
- Automatische Bestandsbuchung: Finalisieren einer Rechnung reduziert den Bestand aller Positionen mit Lager-Artikel; Storno bucht den vollen Bestand zurück; Gutschriften (negative Menge) erhöhen den Bestand automatisch
- Lagerwarnung-Widget auf dem Dashboard: listet alle Artikel bei denen der Bestand den Schwellwert (Mindestbestand) erreicht oder unterschritten hat – mit direktem Link zur Artikelseite
- Bestandswarnung im Rechnungsformular: roter Hinweisbalken wenn die eingetragene Menge den verfügbaren Lagerbestand übersteigt und Minusbestand für den Artikel nicht erlaubt ist
- Artikelcode (SKU/EAN) auf Rechnungs-PDF: Wenn Artikel einen Artikelcode hinterlegt haben, erscheint auf dem PDF automatisch eine eigene „Art.-Nr."-Spalte ganz links in der Positionstabelle – für beide PDF-Vorlagen und im Lieferschein; im Detail-Panel wird der Code unter der Positionsbeschreibung angezeigt

### 🔧 Verbessert
- Artikel-Detailpanel: Lagerinformationen als drei Karten nebeneinander (Bestand / Schwellwert / Minusbestand) – gleiche Optik wie die Preiskarten; Bestand und Schwellwert inline bearbeitbar (✎ direkt in der Karte, keine Seite öffnen nötig)
- Positionsbeschreibung im Rechnungsformular: Textarea wächst automatisch mit – Zeilenumbrüche (Enter) werden im Eingabefeld direkt sichtbar und erscheinen auch im PDF (beide Vorlagen, Lieferschein, Angebot, Auftrag, Proforma)
- PDF: Zeilenabstand in mehrzeiligen Positionsbeschreibungen deutlich reduziert – kompaktere Darstellung bei mehreren Zeilen pro Position

### 🐛 Behoben
- Fehlermeldung bei unzureichendem Bestand: Einheit wird jetzt aus dem Artikel ausgelesen (nicht immer „Stück"); Mengenangabe als ganze Zahl (5 statt 5.000) oder mit deutschem Komma als Dezimaltrennzeichen
- „Minusbestand erlaubt" ist jetzt standardmäßig deaktiviert (war fälschlicherweise beim Anlegen neuer Artikel aktiviert)
- DATEV-Export: Zahlungseingänge für Ausgangsrechnungen fehlten wenn die Erlös-Kategorie kein SKR-Konto hinterlegt hatte (z. B. selbst angelegte „Erlöse 19%"-Kategorie); Export ermittelt jetzt das Konto über die Rechnungspositionen als Fallback (Issue #167)
- DATEV-Export: Skonto-Einträge (zahlungsart = „Skonto") wurden übersprungen weil kein Gegenkonto bekannt war; Skonto wird jetzt als Bank-Buchung exportiert (Issue #167)
- DATEV-Export: Eigenverbrauch-Konten 8920–8925 (SKR03) sind AM-Automatikkonten – BU-Schlüssel wurde fälschlich gesetzt und führte zu DATEV-Importfehler REW00306; jetzt korrekt kein BU-Schlüssel (Issue #165)

---

## [v0.3.19] – Juni 2026

### ✨ Neu
- Rechnungsrabatt als Festbetrag (€): Im Formular per Toggle zwischen % und € wählen – der Festbetrag ist immer ein Bruttobetrag und reduziert den Gesamtbetrag um exakt den eingegebenen Wert; PDF zeigt „Abzug" statt „Rabatt X %"

### 🔧 Verbessert
- PDF-Versand: Original wird beim ersten Drucken oder Mailen gespeichert; alle weiteren Ausgaben sind Kopien des Originals (gleicher Inhalt + KOPIE-Wasserzeichen) – kein wechselnder Status mehr auf Kopien
- Entwurf: Vorschau-Button bleibt; nach Finalisierung nur noch „Drucken" und „Mail senden" – verhindert versehentliche Mehrfach-Ausgabe als Original
- Detail-Panel: Buttons zeigen nach erstem Versand „Kopie drucken" bzw. „Kopie senden"
- Detail-Panel: Zeigt Datum und Uhrzeit des ersten Versands unter „Original versandt" – praktisch als Nachweis wenn ein Kunde behauptet, die Rechnung nicht erhalten zu haben

### 🐛 Behoben
- Detail-Panel: Summenblock zeigte Netto-Layout (Einzelpreis/Gesamt als Netto) auch bei Privatkundenrechnungen und Eingangsrechnungen – jetzt korrekt Brutto für B2C/Eingang, Netto nur für B2B mit ZUGFeRD
- Detail-Panel: Zwischensumme bei Rechnungsrabatt war zu hoch wenn Positionen selbst einen Positionsrabatt hatten (berechnete netto vor statt nach Positionsrabatt)
- DATEV-Export: BU-Schlüssel wurde fälschlicherweise auch auf Automatikkonten (AM) gesetzt – führte zu Fehler REW00305/REW00306 in DATEV; Erlöskonten 8100/8300/8400/8736/8850 (SKR03) und 4100/4300/4400/4736 (SKR04) bleiben jetzt ohne BU
- DATEV-Export: Skonti-Konten 8736 (SKR03) und 4736 (SKR04) wurden nicht als Automatikkonten erkannt und erhielten fälschlicherweise einen BU-Schlüssel (Hinweis von Peter1061, Issue #165)
- DATEV-Export: Konto fehlte bei älteren Journaleinträgen ohne Snapshot – Export verwendete jetzt korrekt das aktuelle Kategorie-Konto als Fallback
- DATEV-Export: Downloads funktionierten nicht wenn der Browser keine benutzerdefinierten Response-Header lesen durfte (CORS); Hinweis auf Download-Schaltfläche ergänzt

---

## [v0.3.18] – Juni 2026

### ✨ Neu
- Einleitungstext auf Rechnungen: Freitext vor der Positionstabelle – global für alle Rechnungen (Einstellungen → Unternehmen) oder individuell pro Rechnung überschreibbar; Markdown-Formatierung: **fett** und *kursiv*
- Rabatt auf Positionsebene und Rechnungsebene (je als %): Positionsrabatt zieht direkt vom Einzelpreis ab und erscheint als Unterzeile im PDF; Rechnungsrabatt auf die Gesamtsumme mit Zwischensumme im Summenblock

### 🔧 Verbessert
- Rechnungsdetail-Panel: Spaltenstruktur überarbeitet – „Stückpreis" → „Einzelpreis"; Positionstabelle zeigt Menge × Einzelpreis = Zeilengesamt; Panel breiter (28 rem)
- Rechnungsdetail-Panel: Summenblock zeigt korrekt Netto, USt und Gesamt (Brutto) – bei Netto-Rechnungen (§19 UStG) entfällt die USt-Zeile
- Beenden-Dialog: Externer Backup-Status direkt sichtbar; Hinweis auf Soll-Versteuerung entfernt (war irreführend für Kleinunternehmer und EÜR-Nutzer)

### 🐛 Behoben
- DATEV-Export: Verwaltungssatz auf korrektes 31-Felder-Format gebracht; BU-Schlüssel für 7 % Vorsteuer (Eingangsrechnungen) von 2 auf 8 korrigiert; PayPal-Standardkonto SKR03 auf 1361 geändert (1360 ist ein internes Transitkonto)
- GWG-Kontonummern korrigiert: SKR03 4855 → 0480, SKR04 6845 → 0670 (laut offiziellem DATEV-Kontenrahmen; Hinweis von Peter1061 via Issue #165)
- EÜR Zeile 17 (vereinnahmte USt): §25a-Margensteuer und ig. Erwerb werden nicht mehr doppelt gezählt; Gutschriften reduzieren Z17 jetzt korrekt
- Jahres-USt: PDF-Export schlug fehl wenn keine UStVA-Voranmeldungen gespeichert waren
- §25a Storno: marge_25a_brutto wird korrekt subtrahiert (war: netto_betrag)
- Gutschrift: Bezug zur Originalrechnung im Detail-Panel sichtbar
- §25a, Belegnr-Kollision und Kategorie-Vorausfüllung im Zahlungsdialog korrigiert

---

## [v0.3.17] – Juni 2026

### ✨ Neu
- Jahresumsatzsteuererklärung (USt 2A): Anzeigehilfe unter Auswertungen → Jahres-USt – berechnet alle KZ-Werte (81/83/86/88/41/89/93/66/61/67 etc.) direkt aus den Journalbuchungen des gesamten Wirtschaftsjahres; Kleinunternehmer erhalten KZ 48 (§19 Gesamtumsatz); Vorauszahlungsanrechnung aus gespeicherten Voranmeldungen (KZ 76); Hinweis wenn Anlage UR ausgefüllt werden muss (ig. Umsätze); PDF-Export

### 🔧 Verbessert
- Exporte-Seite: drei Tabs GoBD-Export / DATEV-Export / Buchhalter-CSV – übersichtlichere Navigation statt langer Scrollseite

---

## [v0.3.16] – Juni 2026

### ✨ Neu
- DATEV-Export: Buchungsstapel im DATEV EXTF-Format (v700/9) für den Steuerberater – Quartal, Halbjahr, Jahr oder freier Zeitraum; BU-Schlüssel für 19 %/7 %, ig. Erwerb (§1a), §13b und §25a Differenzbesteuerung; Gegenkonto-Konfiguration (Bar/Bank/Karte/PayPal) direkt auf der Exporte-Seite
- Buchhalter-CSV: einfacher Journal-Export für Excel / LibreOffice / andere Buchhaltungsprogramme ohne DATEV – Datum, Belegnr, Beschreibung, Kategorie, Zahlungsart, Netto/USt/Brutto; gleiche Zeitraumauswahl wie DATEV

### 🔧 Verbessert
- Anlage AVEÜR: korrekte amtliche Schreibweise durchgehend (war: AVEUR); Navigation, PDF-Titel und Handbuch angepasst
- Anlage AVEÜR: Privatanteil-Feld erklärt Nettomethode und grenzt die 1%-Regelung ab – bei 1%-Regelung Feld auf 0 % lassen, private Nutzung monatlich als Einnahme im Journal buchen

### 🐛 Behoben
- App beenden: Backup läuft jetzt vollständig im Hintergrund – Backup-Fenster erscheint nicht mehr kurz und verschwindet sofort, sondern öffnet sich nur noch bei einem tatsächlichen Fehler beim externen Backup

---

## [v0.3.15] – Juni 2026

### ✨ Neu
- Journal: Toggle „Nur bebuchte" neben dem Kategorie-Dropdown – zeigt nur Kategorien mit mindestens einer Buchung; erleichtert Prüf- und Abstimmarbeiten vor UStVA und EÜR

### 🐛 Behoben
- EÜR: Seite konnte nicht geladen werden wenn kein Anlagenverzeichnis vorhanden ist (Fehler trat bei allen Nutzern ohne AVEÜR-Einträge auf)

---

## [v0.3.14] – Juni 2026

### ✨ Neu
- Anlage AVEÜR – Anlagenverzeichnis: Wirtschaftsgüter (KFZ, EDV, Sonstiges) erfassen; lineare AfA mit Monatsprinzip im Kaufjahr; Privatanteil für KFZ; Abschreibungsplan je Gut; PDF-Export als Anlage AVEÜR
- Buchungsvorlagen: Vorlagen können jetzt auch als Einnahme angelegt werden (z. B. Eigenverbrauch Telefon, Sachentnahmen) – Art-Umschalter im Formular, Kategorienliste zeigt passende Erlös-Kategorien (Issue #157)
- Backup – Ebene 1: Beim Beenden der App wird automatisch ein lokaler WAL-sicherer DB-Snapshot erstellt (max. 5 Kopien, älteste werden automatisch gelöscht)
- Backup – Ebene 2: Externes Backup auf NAS, USB oder Netzlaufwerk beim App-Ende – immer AES-256-GCM-verschlüsselt (DSGVO Art. 32); bis zu 2 Ziele konfigurierbar; enthält Datenbank und alle hochgeladenen Belege
- Backup – Retry-Dialog: Wenn das externe Backup beim Beenden fehlschlägt, kann das Laufwerk angesteckt oder das NAS gestartet werden und direkt erneut versucht werden
- Backup – Manuelles ZIP: Manuelles Backup jetzt als vollständiges ZIP-Archiv (Datenbank + alle Belege) statt nur als .db-Datei; Hinweis auf fehlende Verschlüsselung
- Wiederherstellung – Lokale Snapshots: Aus dem automatisch erstellten lokalen DB-Snapshot direkt über die Backup-Seite wiederherstellen – Backup auswählen, bestätigen, Neustart; kein manuelles Dateikopieren nötig
- Wiederherstellung – ZIP-Upload: Manuelles Backup (.zip) oder verschlüsseltes externes Backup (.zip.enc) hochladen; Passwortfeld erscheint automatisch bei .zip.enc; Datenbank und Belege werden beim Neustart vollständig wiederhergestellt

### 🔧 Verbessert
- EÜR: AfA aus dem Anlagenverzeichnis fließt automatisch in Zeile 36 ein – kein manueller Journaleintrag mehr nötig; blaue Info-Box zeigt den übernommenen Betrag; amber-Hinweis wenn Anlagezugänge existieren aber kein Gut im Anlagenverzeichnis erfasst ist
- Backup-Seite: zwei Karteireiter „Backup" und „Wiederherstellung" mit klarer Trennung der drei Backup-Ebenen (Lokal-Snapshot, Manuell-ZIP, Extern-verschlüsselt)
- Beenden: kein Bestätigungsdialog mehr – App schließt sich direkt; nur wenn das externe Backup fehlschlägt erscheint ein Retry-Dialog
- Buchungsvorlagen: Warndialog wenn „Jetzt buchen" für einen Zeitraum ausgelöst wird der noch nicht fällig ist – verhindert versehentliche Doppelbuchungen (Issue #158)

### 🐛 Behoben
- EÜR: Bei Neuinstallation fehlten die Kategorien „Betriebseinnahmen" (19%/7%/0%) – Rechnungszahlungen wurden ohne Kategorie gebucht und erschienen nicht in der EÜR; bestehende Buchungen werden beim nächsten Start automatisch repariert (Issue #155)
- Journal: Nach CSV-Export erscheint jetzt eine Erfolgsmeldung mit Hinweis dass die Datei in Downloads gespeichert wurde (Issue #136)
- Buchungsvorlagen: Bestätigungsdialog beim Buchen wurde in Tauri/Windows nicht angezeigt (window.confirm() funktioniert in WebView nicht) – ersetzt durch React-Modal mit Abbrechen/Buchen; Warnhinweis bei nicht fälliger Vorlage jetzt sichtbar (Issue #158)
- Windows: Beim App-Ende erscheint kein Konsolen-Fenster mehr kurz auf dem Bildschirm (CREATE_NO_WINDOW für curl.exe + taskkill)
- Kategorien: Fehlermeldung beim Löschen einer belegten Kategorie wird jetzt inline angezeigt statt als nativer alert()-Dialog (Issue #156)

---

## [v0.3.12] – Juni 2026

### ✨ Neu
- Wiederkehrende Buchungen (Fixkosten): Vorlagen für Daueraufträge und monatliche Eingangsrechnungen – Modus „Direkt" erstellt sofort einen Journal-Eintrag, Modus „Warte auf Beleg" füllt das Eingangsrechnungsformular mit Lieferant, Betrag und USt-Satz vor; optional aktivierbar unter Einstellungen → Unternehmen
- Buchungsvorlagen – Beleg-Modus: PDF der Eingangsrechnung direkt im Detailpanel hochladen; OCR extrahiert Belegnummer, Betrag und Fälligkeit automatisch; nach dem Speichern rückt das nächste Fälligkeitsdatum automatisch um ein Intervall vor
- Buchungsvorlagen: Fälligkeits-Badge im Menü – bei überfälligen Vorlagen erscheint ein oranger Punkt neben „Buchungsvorlagen" und neben „Buchhaltung"; Fälligkeiten werden alle 5 Minuten aktualisiert
- Buchungsvorlagen: Vertragsdokument (PDF/Bild) direkt an einer Vorlage hinterlegen; Suche nach Bezeichnung, Lieferant oder Kategorie; Filter nach aktiv/inaktiv und Modus
- Logo-Upload: SVG-Dateien werden jetzt akzeptiert – bei Upload automatisch in hochauflösendes PNG (300 DPI) umgewandelt, inkl. Gradienten, Transparenz und komplexen Vektorformen (Issue #153)

### 🔧 Verbessert
- Buchungsvorlagen – Übersicht: Karten im Wiederkehrend-Stil (2-spaltig, Nächste Fälligkeit zuerst, Erstellt×-Datum, Modus-Badge mit Border, Aktionsbutton direkt in der Karte)
- SMTP-Einstellungen: Testmail-Button jetzt unterhalb des Speichern-Buttons mit Hinweistext – macht deutlich, dass erst gespeichert werden muss, bevor der Test sinnvoll ist (Issue #148)

### 🐛 Behoben
- EÜR: Betriebseinnahmen mit 19 % und 7 % USt fehlten in Zeile 12 wenn die Kategorie in der Datenbank noch als „Betriebseinnahmen (19%)" bzw. „Betriebseinnahmen (7%)" gespeichert war – wird beim App-Start automatisch repariert (Issue #132)

---

## [v0.3.11] – Juni 2026

### ✨ Neu
- EÜR Aufschlüsselung: Schaltfläche „🔍 Aufschlüsselung" zeigt je EÜR-Zeile die enthaltenen Kategorien mit Einzelbeträgen – für Steuerberater und eigene Kontrolle
- Wiederkehrende Ausgangsrechnungen: Vorlagen mit Intervall (monatlich, quartalsweise, jährlich) – Entwürfe werden beim App-Start automatisch angelegt; Preisabgleich mit Artikelstamm meldet Änderungen; optional aktivierbar unter Einstellungen → Unternehmen
- Wiederkehrende Rechnungen – Detail-Panel: Klick auf eine Vorlage zeigt alle daraus generierten Rechnungen mit Datum, Nummer, Brutto und Zahlungsstatus; Gesamtumsatz-Kachel; Klick auf Zeile öffnet Rechnung direkt
- Aufträge: Schaltfläche „🔁 Wiederkehrend" öffnet das Wiederkehrend-Formular mit vorausgefüllten Auftragsdaten (Kunde, Positionen, Auftrag bereits verknüpft)
- Wiederkehrende Rechnungen: Vorlage kann dauerhaft beendet werden – Datensatz und alle bisherigen Rechnungen bleiben erhalten, Auftrag wechselt auf „Abgeschlossen"; Unterschied zu Pausieren: beendete Vorlagen werden standardmäßig im Filter ausgeblendet
- Aufträge: neuer Status „Laufend" (teal) für Aufträge mit aktiver wiederkehrender Vorlage – im Filter und Zähler-Kachel zusammen mit „In Bearbeitung" sichtbar
- Wiederkehrende Rechnungen: Vorlage kann einem Auftrag verknüpft werden – der Auftrag wechselt automatisch auf Status „Laufend" solange die Vorlage aktiv ist, und zurück auf „In Bearbeitung" wenn sie deaktiviert wird
- Wiederkehrende Rechnungen: Vertragsdokument (PDF/Bild) direkt an einer Vorlage hinterlegen – erscheint als Badge auf der Karte und kann jederzeit ersetzt oder entfernt werden

### 🔧 Verbessert
- Mail-Signatur: Vorschau rendert jetzt Markdown als HTML (Fett, Links, Bilder) statt Rohtext – Markdown-Hilfe mit Cheatsheet einblendbar (Issue #150)
- Buchungsanzeige: Kategorie-Dropdowns können optional die SKR03- oder SKR04-Kontonummer hinter der Bezeichnung anzeigen (z. B. „Büromaterial [4930]") – einstellbar unter Einstellungen → Unternehmen → Rechnungen
- Wiederkehrende Rechnungen – Formular: Artikel-Schnellsuche mit Dropdown wie im Rechnungsformular; USt-Satz als Auswahl aus konfigurierten Steuersätzen; Brutto/Netto-Toggle; automatischer Wechsel auf Netto bei Gewerbekunden
- Wiederkehrende Rechnungen – Übersicht: Suchfeld (Bezeichnung/Kunde), Intervall-Filter und Aktiv/Inaktiv-Filter
- GoBD-Export (Journal-CSV): neue Spalte „Vorsteuer-Betrag" zeigt den tatsächlich abziehbaren Vorsteueranteil; USt-Betrag bei normalen Ausgaben korrekt auf 0 gesetzt; Sonderfall (ig_erwerb/§13b) als eigene Spalte
- Wiederkehrende Rechnungen – Statusfilter: Optionen „Nur aktive", „Nur pausierte" und „Beendete" – beendete Vorlagen sind standardmäßig ausgeblendet
- Wiederkehrende Rechnungen – Löschen: nur noch möglich wenn keine Rechnungen erstellt wurden und keine Auftrag- oder Vertrag-Verknüpfung vorhanden; sonst muss „Beenden" verwendet werden

### 🐛 Behoben
- KDE: Dateiauswahl-Dialog erschien im falschen Theme – install.sh setzt nun GTK_THEME automatisch aus den KDE-Einstellungen im Desktop-Starter (Issue #151)
- EÜR: Betriebseinnahmen aus Ausgangsrechnungen (19 % USt) fehlten in Zeile 12, wenn die Datenbank aus einer sehr alten Version stammte – Kategorie hieß damals „Betriebseinnahmen (19%)" und wurde nicht gefunden; bestehende kategorielose Buchungen werden beim App-Start automatisch repariert (Issue #132)
- Wiederkehrende Rechnungen – Detail-Panel: Rechnungsstatus (Entwurf → Offen → Bezahlt) wird jetzt sofort aktualisiert wenn eine Rechnung in der Rechnungsübersicht finalisiert oder bezahlt wird
- Aufträge: Status blieb nach „Vorlage beenden" auf „Laufend" – fehlender DB-Flush vor der Auftrag-Status-Abfrage im Backend
- EÜR: Skonto-Doppelabzug in Zeile 12 – beim Zuflussprinzip enthält die Zahlungsbuchung bereits den tatsächlich vereinnahmten Betrag (z. B. 98 € bei 2 % Skonto); ein separater Skonto-Eintrag mit EÜR-Zeile darf die Einnahme nicht nochmals mindern; EÜR-Zeile für „Gewährte Skonti" und „Erhaltene Skonti" wird bei bestehenden Installationen automatisch korrigiert (Issue #132)

---

## [v0.3.10] – Juni 2026

### ✨ Neu
- SMTP-Mailversand: Rechnungen, Angebote, Proforma-Rechnungen und Auftragsbestätigungen direkt aus RechnungsFee versenden – PDF und Dokumentenpakete werden automatisch angehängt (Einstellungen → Unternehmen → E-Mail → SMTP)
- Mail-Vorlagen je Dokumenttyp: eigene Betreff- und Text-Vorlage für Rechnung, Angebot, Proforma und Auftrag – mit Platzhaltern wie {rechnungsnummer}, {betrag}, {faellig_am}
- Markdown-Signatur: die Mail-Signatur wird als HTML gerendert (Fett, Links, Zeilenumbrüche) mit plain-text-Fallback für ältere Mailprogramme

### 🔧 Verbessert
- Beim Fallback auf den OS-Mailclient erscheint ein Hinweis-Toast mit Link zur SMTP-Einrichtung – Dokumentenpakete können per mailto nicht als Anhang mitgesendet werden

### 🐛 Behoben
- Dokumentenpaket-Anhang: Dateiname wurde fälschlicherweise auf dem Paket-Eintrag gesucht statt auf dem verknüpften Beleg – Anhänge haben jetzt den korrekten Originalnamen
- EÜR: Betriebseinnahmen aus Rechnungen mit 7 % USt wurden nicht angezeigt – die Kategorie „Betriebseinnahmen (7%)" fehlte in Migration 26 und hatte kein EÜR-Zeilen-Mapping (Issue #132)
- EÜR und UStVA: Storno-Gegenbuchungen wurden nicht korrekt verrechnet – Einnahme-Storni wurden addiert statt subtrahiert; Vorsteuer-Storni wurden ignoriert

---

## [v0.3.9] – Juni 2026

### ✨ Neu
- Aufträge: neuer Status „Rechnung" (violett) – Auftrag wechselt automatisch auf diesen Status sobald die verknüpfte Rechnung finalisiert wird; erst nach Zahlungseingang folgt „Abgeschlossen" (Issue #145)

### 🔧 Verbessert
- Aufträge: Auftragsliste und Kennzahlen aktualisieren sich sofort wenn eine verknüpfte Rechnung finalisiert oder gelöscht wird – kein manuelles Refresh mehr nötig
- Neues Rechnungsformular: wechselt automatisch auf Netto-Eingabe wenn ein Firmenkunde gewählt wird (solange noch keine Preise eingetragen wurden)
- ZUGFeRD-Badge im Rechnungsdetail: bei Ausgangsrechnungen für ZUGFeRD-Kunden wird „ZUGFeRD ✓" in der Metadaten-Leiste angezeigt

### 🐛 Behoben
- Lieferschein-PDF zeigte Preisspalten (Vorlage 0 – Standard); Lieferscheine zeigen jetzt nur noch Beschreibung, Menge und Einheit (Issue #144)

---

## [v0.3.8] – Juni 2026

### ✨ Neu
- Aufträge-Modul (aktivierbar unter Einstellungen → Unternehmen): verbindliche Auftragsbestätigungen direkt oder aus einem Angebot heraus; → Rechnung, → Lieferschein, → Proforma; Status-Workflow Offen → In Bearbeitung → Abgeschlossen; Auftrag wechselt automatisch auf „Abgeschlossen" sobald eine verknüpfte Rechnung bezahlt ist
- Tastaturkürzel Strg+Shift+E springt direkt zur Eingangsrechnungen-Ansicht – funktioniert von jeder Seite aus

### 🔧 Verbessert
- Alle Dokumentlisten (Angebote, Aufträge, Proforma, Lieferscheine) haben jetzt einen einheitlichen Filterkopf mit Suche, Statusfilter und Kennzahlen; bleibt beim Scrollen stehen
- Spaltenreihenfolge vereinheitlicht: Datum steht jetzt überall vor der Nummer (wie bei Rechnungen und Lieferscheinen)
- Herkunftsbezug in der Liste: Lieferscheine, Proformas, Aufträge und Rechnungen zeigen hinter der Nummer ein kleines Badge mit dem Vordokument (z. B. „aus ANG-260001")
- Angebote: Bearbeiten und alle Folgedokument-Erstellen-Buttons werden gesperrt sobald ein Folgedokument (Auftrag, Rechnung, Lieferschein oder Proforma) existiert
- Aufträge: Bearbeiten und Löschen werden gesperrt sobald ein Folgedokument (Rechnung, Lieferschein oder Proforma) existiert
- Proforma: Bearbeiten und Löschen werden gesperrt sobald eine Rechnung aus der Proforma erstellt wurde

### 🐛 Behoben
- Backup-Button im Einstellungen-Tab war nach einem Refactor defekt; Dialog öffnet jetzt nativ „Speichern unter" statt immer in den Download-Ordner zu schreiben (Issue #141)
- Eingangsrechnungen-Tab ist beim Öffnen der Rechnungsübersicht wieder der Standard-Tab (Issue #142)
- Artikelsuche reagiert schon ab 2 Zeichen (vorher 3)
- Proforma-Rechnungen erschienen fälschlicherweise in der Rechnungs-Übersicht und wurden dort als leere Zeilen angezeigt (Issue #139)
- CSV-Export öffnete in Tauri ein schwarzes leeres Fenster statt die Datei zu speichern (Issue #139)

---

## [v0.3.7] – Juni 2026

### ✨ Neu
- Proforma-Rechnungen (aktivierbar unter Einstellungen → Unternehmen): Vorkasse-Aufforderung mit Zahlungsblock und Zahlungsziel; direkt oder aus einem Angebot heraus erstellen
- Proforma: „Zahlung eingegangen" – Zahlungsart und Datum wählen, Journaleintrag wird automatisch gebucht, Ausgangsrechnung als Entwurf (bezahlt) wird erstellt
- Proforma-Übersicht: Alterswarnung bei mehr als 14 Tage offenen Proformas (amber-Markierung in der Liste); Navigation aus Angebot filtert die Liste direkt auf das verknüpfte Dokument
- Proforma-PDF: vollständiger Zahlungsblock mit IBAN, Betrag und Zahlungsziel; kein Skonto, keine Unterschrift; nie ZUGFeRD (die erzeugte Rechnung bekommt ZUGFeRD wenn der Kunde es aktiviert hat)
- Proforma: Entwurf-Modus – speichern ohne Nummer, Finalisieren vergibt die PRF-Nummer und schaltet Drucken, PDF und E-Mail frei

### 🔧 Verbessert
- Angebote: → Rechnung und → Lieferschein sind gesperrt wenn eine Proforma zu diesem Angebot existiert; Löschen ist deaktiviert sobald Rechnung, Lieferschein oder Proforma verknüpft sind
- Nummernkreis-Format JJNNNN (deutsch) wird jetzt korrekt aufgelöst – ANG-260001, PRF-260001 statt unverändertem Platzhalter

### 🐛 Behoben
- Angebot löschen schlug still fehl wenn das Angebot finalisiert war (Backend 409, kein Fehlerhinweis) – betrifft alle Plattformen; Issue #135
- Rechnung aus Angebot / Proforma: Positionen wurden mit falschen Feldnamen kopiert (einzelpreis statt netto) und erzeugten einen 500-Fehler
- Rechnung finalisieren: Detail-Panel zeigte nach dem Finalisieren weiterhin den Entwurf-Zustand wenn die Rechnung über ?id= Navigation geöffnet wurde
- Proforma-Rechnungen aktivieren: Toggle wurde nach dem Speichern nicht persistiert (fehlte im Pydantic-Schema)

---

## [v0.3.6] – Juni 2026

### ✨ Neu
- Journal: Export als PDF oder CSV – Buttons immer sichtbar; alle aktiven Filter (Zeitraum, Art, Kategorie, Zahlungsart) werden übernommen und im Dokument dokumentiert

### 🐛 Behoben
- EÜR: Zeilennummern auf Anlage EÜR 2025 korrigiert – Vereinnahmte USt Zeile 17, FA-erstattete USt Zeile 18, Vorsteuer Zeile 57; Gewährte Skonti Zeile 12; Reparatur/Bauleistungen §13b Zeile 60
- Zahlungsdialog: Schaltfläche „Überw." heißt jetzt einheitlich „Bank"
- Gutschriften: Journalbuchungen fehlten in der Anlage EKS – Buchungskategorie wird jetzt korrekt von der Originalrechnung übernommen wenn die Position keine eigene Kategorie hat
- OCR-Import: Summenzeile aktualisiert sich korrekt nach Positionsänderungen beim Import (Issue #119)

---

## [v0.3.5] – Juni 2026

### ✨ Neu
- Angebote: Entwurf-Modus – „Entwurf speichern" legt ein Angebot ohne Nummer an; Entwürfe sind in der Liste mit einem gelben Badge markiert und können jederzeit bearbeitet werden
- Angebote: Finalisieren-Button im Entwurf-Banner vergibt die Angebotsnummer und schaltet alle Aktionen (Drucken, PDF, E-Mail, Rechnung, Lieferschein) frei
- Dashboard – Zufluss-Monitor: Toggle „Monat / Leistungszeitraum" erscheint wenn ein Abrechnungszeitraum hinterlegt ist; zeigt §11b-Berechnung wahlweise für den aktuellen Monat oder den gesamten 6-Monats-Zeitraum
- Stammdaten → Unternehmen: neues Feld „Abrechnungszeitraum Beginn" im Abschnitt Transferleistungen – Startmonat des 6-Monats-Zeitraums aus dem Leistungsbescheid; RechnungsFee berechnet den aktuell laufenden Zeitraum automatisch weiter

### 🐛 Behoben
- Zufluss-Monitor: Berechnung verwendet Brutto-Einnahmen und Brutto-Ausgaben (Zuflussprinzip §3 Alg II-V) – Storni heben sich korrekt auf, Ergebnis stimmt mit dem Journal-Saldo überein

---

## [v0.3.4] – Juni 2026

### ✨ Neu
- Angebote: Lieferschein direkt aus dem Angebot erstellen (nur bei Status „Bestätigt"); Angebot-Zeile zeigt danach einen Link zum erstellten Lieferschein
- Angebote: Rechnung aus Angebot ebenfalls nur bei Status „Bestätigt" möglich; Button ausgegraut solange ein Lieferschein zu diesem Angebot existiert
- Angebote: Rückverlinkung Angebot → Lieferschein (Schema 56); bestehende Links werden beim Update automatisch aus den Notizen rekonstruiert

### 🔧 Verbessert
- Angebote: Preismodus wechselt automatisch auf Netto bei Firmenkunden (B2B) – kein manueller Toggle mehr nötig
- Angebote: direkt aus dem Kundenstamm heraus erstellen (Kunden-Detailansicht → „→ Angebot")
- Angebote: USt-Satz beim neuen Angebot aus dem konfigurierten Standard-Steuersatz vorbelegt
- Navigation zu verlinktem Dokument (Rechnung, Lieferschein) aus Angebot filtert die Übersicht automatisch auf genau dieses Dokument
- Bestätigungsabfragen beim Erstellen von Rechnung oder Lieferschein aus Angebot entfernt – kein überflüssiger Klick mehr
- Unternehmensseite in 5 Tabs aufgeteilt: Firma / Steuer / Rechnungen / E-Mail / Unterschrift
- GoBD-Export unter Auswertungen eingeordnet statt als eigenständiger Menüpunkt

### 🐛 Behoben
- Buttons mit disabled-Attribut (ausgegraut) waren optisch nicht als deaktiviert erkennbar; disabled:opacity-50 + cursor-not-allowed jetzt einheitlich in allen Aktionsleisten
- Angebote: Brutto/Netto-Toggle und Submit-Payload korrigiert – Preise wurden beim Speichern falsch berechnet
- Angebote: bleiben auch ohne Entwurf-Status editierbar bis ein Folgedokument erstellt wird

---

## [v0.3.3] – Juni 2026

### ✨ Neu
- Lieferadressen (#25): Kunden können beliebig viele Lieferadressen verwalten (Bezeichnung, z. Hd., Anschrift); Standard-Adresse wird beim Lieferschein automatisch vorgeschlagen
- Lieferscheine (#25): neuer Dokument-Typ; PDF ohne Preisangaben, mit gewählter Lieferadresse und Felder für Empfangsbestätigung (Datum/Ort + Unterschrift Warenempfänger)
- Lieferschein → Rechnung: Ein-Klick aus dem Lieferschein-Detail erstellt eine Ausgangsrechnung mit allen Positionen (Preise werden im Entwurf ergänzt)
- Sammelrechnung: mehrere Lieferscheine desselben Kunden per Checkbox markieren und zu einer einzigen Rechnung zusammenfassen; Leistungszeitraum wird aus frühestem/spätestem Lieferschein-Datum vorbelegt
- Lieferschein aus Rechnung (Vorkasse-Workflow): finalisierte Ausgangsrechnung → „→ Lieferschein erstellen" legt Lieferschein mit allen Positionen an; max. ein Lieferschein pro Rechnung
- Bidirektionale Navigation: Lieferschein-Detail zeigt verknüpfte Rechnung; Rechnungs-Detail zeigt Lieferschein(e) – Klick öffnet Lieferschein-Übersicht mit Filter auf genau diese Lieferscheine

### 🔧 Verbessert
- Lieferschein-Übersicht: Spalten „Fällig am" und „Brutto" entfernt; neue Spalte „Rechnung" zeigt verknüpfte Rechnungsnummer; Suche findet jetzt auch nach Rechnungsnummer
- Nummernkreise: Lieferschein-Eintrag wird ausgeblendet wenn Lieferschein-Funktion nicht aktiviert ist
- Lieferschein-Status unterscheidet jetzt zwischen „Rechnungsentwurf" (Rechnung angelegt, noch nicht finalisiert) und „Abgerechnet" (Rechnung finalisiert)
- Navigation: ZM (Zusammenfassende Meldung) nur sichtbar wenn eine USt-IdNr. hinterlegt ist und innergemeinschaftliche Buchungen existieren

### 🐛 Behoben
- FK-Konflikt beim Löschen oder Storno einer aus einem Lieferschein erstellten Rechnung
- Sammelrechnung-Dialog schließt nach dem Erstellen automatisch
- Preisvalidierung für Lieferschein-Positionen deaktiviert (Lieferscheine haben keine Preise)

---

## [v0.3.2] – Juni 2026

### ✨ Neu
- EÜR – Einnahmen-Überschuss-Rechnung: Berechnung nach Anlage EÜR 2025 aus Journalbuchungen (Ist-Versteuerung); Zeilen A (Einnahmen), B (Ausgaben), Gewinn/Verlust; PDF-Anzeigehilfe für ELSTER oder Steuerberater
- EÜR: Zeile 15 (vereinnahmte USt) und Zeile 48 (abziehbare Vorsteuer) werden automatisch aus den Journal-USt-Feldern berechnet – kein manueller Eintrag nötig
- EÜR: Hinweis auf Anlage AVEÜR wenn Anlagezugänge (KFZ, EDV etc.) im Journal vorhanden sind
- UStVA-Anzeigehilfe: Berechnung startet automatisch beim Öffnen der Seite und bei jedem Zeitraumwechsel – kein separater „Berechnen"-Klick mehr nötig
- Rechnungsimport (#119): Button „∑ Nach Steuersatz zusammenfassen" – reduziert OCR-erkannte Einzelpositionen auf eine Zeile je Steuersatz (z.B. alle 7%-Positionen → „Waren (7%)")

---

## [v0.3.1] – Juni 2026

### ✨ Neu
- Zusammenfassende Meldung (ZM) §18a UStG: Dashboard-Hinweis wenn eine Meldung fällig ist, ZM-Seite mit Berechnung nach USt-IdNr./Land, Kennzeichen L (Lieferung) und D (§13b Dienstleistung) – für §19 Kleinunternehmer ausgeblendet
- Unterschrift (#129): Datei-Upload als Alternative zum Zeichnen (JPG, PNG, WebP) – für eingescannte Unterschriften und Tablet-Nutzer; Zeichenfläche größer (220px)
- Unterschrift (#129): „⬇ Speichern"-Button lädt die hinterlegte Unterschrift als PNG herunter – Backup für Neuinstallation auf anderem Rechner
- §25a: Neue Kategorie „Wareneinkauf §25a (privat)" – 0% USt, kein Vorsteuerabzug (Ankauf von Privatpersonen für Differenzbesteuerungshandel)

### 🐛 Behoben
- §25a Differenzbesteuerung: Margensteuer wird jetzt korrekt nur auf die Brutto-Marge (VK − EK) berechnet und in KZ 81/83 der UStVA ausgewiesen – Journalbuchungen vor v0.3.1 müssen einmalig neu gebucht werden
- Steuersätze (#128): 0%, 7% und 19% werden bei Neuinstallation jetzt automatisch angelegt; Bezeichnung „MwSt-Sätze" in Navigation und Seite zu „Steuersätze" umbenannt
- Rechnungsliste (#125): Tastaturfokus (Pfeiltasten) jetzt deutlich sichtbar – ausgewählte Zeile mit blauem Hintergrund und blauem Balken links

---

## [v0.3] – Juni 2026

### ✨ Neu
- UStVA-Anzeigehilfe: Alle Voranmeldungs-Kennziffern (KZ 81/83/86/88/41/89/93/61/35/36) werden automatisch aus dem Journal berechnet und als PDF-Übersicht für die manuelle Eingabe in ELSTER aufbereitet
- §25a Differenzbesteuerung – Journalbuchung: USt wird korrekt nur auf die Brutto-Marge (VK − EK) berechnet, nicht auf den vollen Verkaufspreis; Marge wird als eigenes Feld gespeichert und fließt direkt in KZ 81/83 der UStVA ein
- Innergemeinschaftlicher Erwerb (§1a UStG): KZ 89/93 (USt) und KZ 61 (Vorsteuer) werden vollautomatisch aus dem Journal befüllt – kein manueller Eintrag nötig
- Reverse Charge §13b (EU-Dienstleistungen und Bauleistungen): KZ 35/36 automatisch aus Journal-Sonderfall befüllt
- Voranmeldungsrhythmus (monatlich / quartalsweise) in den Stammdaten konfigurierbar

### 🔧 Verbessert
- UStVA-PDF: KZ-Tabelle übersichtlicher – Sub-Zeilen (USt-Betrag) visuell eingerückt, Farbe und Schriftgröße differenzieren Haupt- und Steuerzeile

---

## [v0.2.21] – Juni 2026

### ✨ Neu
- Rechnungsliste: Büroklammer-Icon zeigt auf einen Blick ob eine Eingangsrechnung einen Beleg hat (#123)
- Rechnungsliste: Keyboard-Navigation vollständig – Pfeiltasten scrollen durch die Liste, Tab springt direkt zu einer Zeile (fokus-visible Ring nur beim Tabben) (#125)
- Journal: Summenzeile unterhalb der Liste – Einnahmen, Ausgaben und Saldo des aktuellen Filters auf einen Blick (#122)
- Formulare: Kategorie, Lieferant, Kunde und Artikel lassen sich direkt im Erfassungsformular neu anlegen – ohne Seitenwechsel (#120)

### 🔧 Verbessert
- Beleg-Anhang und -Spalte werden nur noch bei Eingangsrechnungen angezeigt – bei Ausgangsrechnungen generiert die App das PDF selbst
- Zahlungsart „Überweisung" heißt jetzt überall „Bank"

### 🐛 Behoben
- OCR-Import: Vodafone- und Telekommunikationsrechnungen – Lieferantenname, Adressteil-Trimming und Positionen werden jetzt korrekt erkannt (#119)
- GoBD-Export: Belege-Ordner war leer wenn Beleg nur an der Rechnung (nicht am Journal-Eintrag) hing – Fallback via rechnung.beleg_id ergänzt (#124)
- Storno-Buchung einer Eingangsrechnung: Vorsteuer-Betrag wird jetzt korrekt angezeigt (#113)

---

## [v0.2.20] – Juni 2026

### ✨ Neu
- GoBD-Export: Belegdateien jetzt im ZIP enthalten – belege.csv (SHA256-Manifest) + belege/-Ordner mit den tatsächlichen Dateien (PDF/A bevorzugt, sonst Original)
- PDF/A-3-Archivierung: Belege werden nach dem Upload automatisch im Hintergrund zu PDF/A-3 konvertiert (erfordert Ghostscript); ZUGFeRD/XRechnung sofort als PDF/A-3 markiert (sind es per Norm)
- Beleg-Detailansicht: „✓ PDF/A-3 (GoBD-Archiv)"-Link erscheint sobald die Archivversion bereit ist

---

## [v0.2.19] – Juni 2026

### 🔧 Verbessert
- OCR-Import: Belegtyp-Erkennung – Kassenbons und Tankquittungen werden strukturbasiert erkannt (A/B-Steuercode, Liter+Literpreis) und immer im Brutto-Modus verarbeitet; keine Markennamen nötig

### 🐛 Behoben
- OCR-Import: Kassenbons – 19% USt wird auch dann korrekt zugeordnet wenn Tesseract das Steuerklassen-Kürzel „A" als „fz" fehlgelesen hat; DE-Standard A=19%/B=7% als Voreinstellung
- OCR-Import: Tankquittung – Produktname (z.B. „Super 95"), Literanzahl und Brutto-Preis werden jetzt korrekt extrahiert; USt-Satz 19% wird aus dem Brutto/Netto-Verhältnis abgeleitet wenn kein Steuercode auf der Zeile steht
- OCR-Import: Lieferant-Matching – der Backend-Vorschlag wird direkt übernommen statt nochmals im Frontend verglichen zu werden; verhindert „Kein Treffer" bei OCR-verzerrten Firmennamen (z.B. „GimbH" statt „GmbH")
- OCR-Import: „Preis Netto", „Gesamtpreis Netto", „Einzelpreis" und vergleichbare Summenzeilen werden nicht mehr als Positionen importiert
- OCR-Import: Leerzeichen in Geldbeträgen (Tesseract-Artefakt „25, 95" → „25,95") werden vor der Auswertung entfernt
- OCR-Import: USt-Aufschlüsselungs-Tabellenzeilen (z.B. „fz 19,0% 4,12 6,78 4,90") werden nicht mehr als Positionen importiert
- ZUGFeRD/XRechnung-Import: PDF wird jetzt automatisch zur Kontrolle geöffnet (bisher nur bei Plain-PDF)

---

## [v0.2.18] – Juni 2026

### 🐛 Behoben
- OCR-Import: Positionen aus Tankquittungen erkannt – Produktname (z.B. „Super 95") und Menge (z.B. 32,69 l) werden jetzt korrekt extrahiert, auch wenn sie auf getrennten Zeilen oder in einem Einzeiler stehen
- OCR-Import: Sternchen (*) aus OCR-Text entfernt – verhinderte Fehlinterpretationen bei Kassenbons die * um Produktnamen oder Preise verwenden
- OCR-Import: „SUMME EUR 30,85" wird als Rechnungsbetrag erkannt (nicht als Position) – Währungssymbol zwischen Label und Betrag wird jetzt korrekt ignoriert

---

## [v0.2.17] – Juni 2026

### ✨ Neu
- Tesseract-Assistent: benutzerfreundlicher Einrichtungsdialog für OCR – Ein-Klick-Installation ohne Terminal, plattformspezifisch (Windows: winget, Linux: pkexec + apt/dnf/pacman, macOS: Anleitung)

### 🐛 Behoben
- Windows-Installer: Tesseract-Installation wird jetzt per Dialog angeboten statt still im Hintergrund zu laufen (Issue #115)
- Tesseract nach Installation nicht erkannt: zusätzlich bekannte Installationspfade prüfen wenn PATH noch nicht aktualisiert wurde (Windows: Program Files/Tesseract-OCR, macOS: /opt/homebrew, Linux: /usr/bin)

---

## [v0.2.16] – Juni 2026

### ✨ Neu
- OCR für gescannte Eingangsrechnungen & Kassenbons – pdfplumber für maschinenlesbare PDFs, pytesseract + pymupdf für Scans/Fotos; graceful fallback mit Installationshinweis wenn Tesseract nicht vorhanden (Stufe 4)
- Tesseract OCR-Installation: Windows-Installer richtet es automatisch per winget ein; Linux-Installationsskript (install-linux.sh) bietet es interaktiv an; macOS-Hinweis im Import-Dialog
- PDFs öffnen in eigenem OS-Fenster (Tauri): Rechnung, Beleganhang, Exporte öffnen sich in einem eigenen Fenster statt im App-internen Viewer
- Journal: Rechnungsnummer-Badge ist jetzt ein Link – Klick springt direkt zur zugehörigen Rechnung in der Rechnungsübersicht

### 🔧 Verbessert
- Belegnummer kopieren im Journal: Clipboard-Icon zeigt an dass der Button kopiert
- Journal: redundantes Rechnungsnummer-Badge im Detailbereich entfernt (steht bereits im Tabellenkopf als Link)

### 🐛 Behoben
- EDV / Software (Sofortabschreibung): SKR03-Konto korrigiert auf 0490 (SKR03 0650 ist ein Verbindlichkeitenkonto, Issue #111)
- Forderungsausfall: USt-Zeile im Journal zeigte „Vorsteuer" statt „Umsatzsteuer" – Erkennung jetzt per Kontonummer (1776/1771 = Umsatzsteuer, Issue #113)
- Windows / WebView2: Datumsfelder mit leerem Wert verursachten schwarzes Fenster – leere onChange-Events werden jetzt abgefangen (Issue #114)

---

## [v0.2.15] – Mai 2026

### ✨ Neu
- Buchungen ohne Geldfluss – neue Checkbox „Kein Geldfluss" im Buchungsformular für AfA, Sachentnahmen, Eigenverbrauch; kein Kassenstand-Einfluss, kein Tagesabschluss (Issue #55)
- Forderungsausfall – Rechnungen als uneinbringlich ausbuchen: Status-Badge, Filter, eigener Eintrag im Journal; für USt-Pflichtige automatisch §17-UStG-Korrekturbuchung (Issue #61)
- Neue Kategorie „KFZ (Kauf)" SKR03 0320 / SKR04 0540 – separates Anlagekonto für Fahrzeuge, fließt korrekt in Anlage AVEÜR ein
- Neue Kategorie „EDV / Software (Sofortabschreibung)" SKR03 0490 / SKR04 0650 – Anlagekonto nach BMF 26.02.2021 (Nutzungsdauer 1 Jahr, § 7 Abs. 1 EStG); zweistufiger Buchungsweg mit separater AfA erklärt
- Neue Kategorie „Bewirtungskosten (nicht abzugsfähig)" SKR03 4654 – für den steuerlich nicht abziehbaren 30 %-Anteil nach § 4 Abs. 5 Nr. 2 EStG
- Neue Kategorien „Gewährte Skonti" (SKR03 8736) und „Erhaltene Skonti" (SKR03 3736) – werden bei Skonto-Zahlung automatisch zugewiesen und ermöglichen spätere EÜR-Auswertung
- Fahrtkosten Privat-PKW: km-Eingabe im Buchungsformular – Betrag wird automatisch auf 0,30 €/km (EÜR) berechnet, gespeicherte km-Anzahl ermöglicht korrekten EKS-Ansatz (0,10 €/km); EKS-Formular: neues Abzugsfeld B6.4 für privat gefahrene km mit Betriebs-KFZ

### 🔧 Verbessert
- Journal: vorsteuer_betrag-Snapshot – tatsächlich abziehbarer Vorsteuer-Anteil wird je Buchung gespeichert (berücksichtigt z. B. 70 % bei Bewirtungskosten)
- Privatentnahme / Privateinlage: EÜR-Zeilennummern korrigiert auf Zeile 106 / 107 (Anlage EÜR 2025 Hinweiszeilen)
- Kategorien-Seite: EKS-Felder (EKS-Kategorie, EÜR-Zeile) nur noch eingeblendet wenn „Bezieht Transferleistungen" aktiviert – weniger Rauschen für reguläre Nutzer

### 🐛 Behoben
- EDV / Software (Sofortabschreibung): Kategorie war fälschlicherweise als Aufwand angelegt – korrekt ist Anlage (SKR03 0490 / SKR04 0650); BMF 2021 ist kein GWG
- Einkommensteuer-Vorauszahlung: Fälligkeitsmonate in der Beschreibung korrigiert (März / Juni / September / Dezember)
- Bewirtungskosten (nicht abzugsfähig): EKS-Kategorie korrigiert (war B14_5, jetzt leer – kein anerkannter Aufwand beim Jobcenter)

---

## [v0.2.14] – Mai 2026

### 🐛 Behoben
- Linux: Backend startet nicht mehr (PIL/_avif.so Extraktionsfehler) – AVIF- und WebP-Codec aus dem Bundle ausgeschlossen (Issue #110)
- Linux AppImage: Ghost-Backends vom letzten Absturz werden beim Start jetzt korrekt beendet – Pfad-Erkennung für AppImage-Modus korrigiert (vorher: nur Dev-Modus erkannt)

---

## [v0.2.13] – Mai 2026

### ✨ Neu
- Differenzbesteuerung §25a UStG: Artikel als §25a kennzeichnen – kein USt-Ausweis auf der Rechnung, Ankaufspreis hinterlegen, Margenberechnung (VK − EK) live im Formular und Detailpanel
- §25a auf Rechnungen: gemischte Positionen möglich (Regelbesteuerung + §25a); USt-Spalte zeigt „§25a"; Pflichthinweis wird automatisch unter den Summenblock gedruckt

### 🔧 Verbessert
- Artikelsuche in Rechnungen: §25a-Artikel tragen orangenen Badge; VK-Brutto wird als Positionspreis übernommen (kein Netto/Brutto-Umrechnen)
- Scroll-Layout: Seitenheader und rechte Detailspalte bleiben beim Scrollen stehen – gilt für Rechnungen, Journal, Kunden, Lieferanten und Artikel

### 🐛 Behoben
- Storno-Buchungen: Betrag ist jetzt immer positiv; Art (Einnahme/Ausgabe) richtet sich nach dem Originalbeleg – Gutschrift-Storno erscheint korrekt als Einnahme
- Gutschrift: Betragslimit wird auch beim Speichern eines Entwurfs geprüft – nicht erst beim Finalisieren

---

## [v0.2.12] – Mai 2026

### ✨ Neu
- Gutschriften: Aus jeder abgeschlossenen Ausgangsrechnung lässt sich per Klick eine Gutschrift erstellen – mit GS-Nummer, Bezug auf Originalrechnung und negierten Positionen
- Gutschrift-Buchung: Rückerstattung buchen erzeugt negative Einnahme-Buchungen mit denselben Kategorien und USt-Konten wie die Originalrechnung (EÜR-korrekte Aufhebung)

### 🔧 Verbessert
- Gutschrift-Badge in der Rechnungsliste; Gutschrift-Formular öffnet sich direkt nach Erstellung; PDF zeigt korrekten Rückerstattungstext statt Zahlungshinweis
- Entwürfe zeigen nur noch „Vorschau" – Drucken, PDF öffnen und Mail senden sind für nicht finalisierte Dokumente ausgeblendet

### 🐛 Behoben
- Gutschrift-Positionen: Betrag wurde beim Bearbeiten doppelt negiert; Gesamt-Betrag in der Positionsspalte zeigte den richtigen Wert

---

## [v0.2.11] – Mai 2026

### ✨ Neu
- Buchungskategorien: Verwendungsbeispiele und Beschreibungen – vorbefüllt, frei editierbar, als Hinweis im Buchungsformular sichtbar; Export als PDF-Nachschlageblatt
- Storno-Begründung Pflichtfeld: Schnellauswahl (Doppelt ausgestellt / Falsche Adresse / Kundenwiderspruch / Sonstiges) – Begründung wird im Journal dokumentiert

### 🐛 Behoben
- Backend-Start nach Update: Wartezeit auf 60 Sekunden verlängert – verhindert „Backend nicht erreichbar" nach Windows-Update (Defender-Scan, PyInstaller-Extraktion)

---

## [v0.2.10] – Mai 2026

### ✨ Neu
- Artikelgruppen-Verwaltung: Warengruppen, Servicegruppen und Fremdleistungsgruppen anlegen, umbenennen und deaktivieren – direkt über „Gruppen"-Button auf der Artikelseite

### 🔧 Verbessert
- Artikelstamm: Feld „Kategorie" heißt jetzt Warengruppe / Servicegruppe / Fremdleistungsgruppe (je nach Typ); Auswahl über Dropdown statt Freitext
- Info-Seite: Handbuch, Links und „Über RechnungsFee" stehen jetzt oben – der Changelog ist ans Ende gewandert

### 🐛 Behoben
- Ausgangsrechnungen mit mehreren Steuersätzen: Zahlung erzeugt jetzt je USt-Satz einen eigenen Journaleintrag statt eines einzigen mit dominantem Satz (Issue #109)

---

## [v0.2.9] – Mai 2026

### ✨ Neu
- Skonto: Standard im Unternehmensprofil, Kunden-spezifisch und je Rechnung konfigurierbar; ZahlungsDialog zeigt grüne Hinweis-Box wenn Skonto-Frist noch offen (Issue #73)
- Giro-Code mit Skonto: zwei QR-Codes nebeneinander auf der Rechnung – links Skonto-Betrag mit Frist-Label, rechts Vollbetrag (Vorlage 0 + 1)

### 🔧 Verbessert
- Journal: Rechnungsnummer in Buchungseinträgen sichtbar; Rechnungszahlungen können nicht mehr storniert, gedruckt oder per Mail versendet werden

### 🐛 Behoben
- POS-Kassenbelege (Thermaldrucker-Format): Belegnr., Lieferant, Positionen und USt-Tabelle werden jetzt korrekt erkannt und importiert
- PDF-Import: Fälligkeitsdatum wird beim Import nicht mehr automatisch berechnet (verhindert falsche Werte bei unbekanntem Zahlungsziel)
- PDF-Import: Rechnungen mit mehreren Positionen öffnen automatisch den aufgeschlüsselten Eingabemodus (XML + PDF)

---

## [v0.2.8] – Mai 2026

### ✨ Neu
- Leistungszeitraum: statt einem Datum kann jetzt ein Von–Bis-Zeitraum angegeben werden – ideal für Monats- oder Projektabrechnungen (Issue #107)
- Kategorie-Zuweisung bei Eingangsrechnungen jetzt beim Bezahlen statt beim Anlegen – Split-Zahlung mit mehreren Kategorien möglich

### 🐛 Behoben
- PDF-Import: Rechnungen im Amazon-/bilingualen Format (DE/EN-Spaltenüberschriften) werden korrekt erkannt
- PDF-Import: Beträge ohne Leerzeichen vor EUR (z. B. „37,73 EUR44,90") werden jetzt korrekt geparst
- Linux Mint Cinnamon: Mausrad-Scrollen im Setup-Wizard funktioniert jetzt (React-onWheel-Handler durch globalen WebKitGTK-Workaround ersetzt)

---

## [v0.2.7] – Mai 2026

### 🔧 Verbessert
- PDF-Vorlagen: Gemeinsame Logik in Basisklasse extrahiert – einfachere Pflege bei neuen Vorlagen

### 🐛 Behoben
- PDF: Negative Mengen (Gutschriften) korrekt dargestellt – Einzelpreis bleibt positiv, Nettospalte zeigt Positionssumme, USt-Aufschlüsselung und Vorzeichen stimmen
- Kategorien: Löschen schlug still fehl wenn Kategorie in Rechnung, Banktransaktion oder Automatikregel verwendet – Fehlermeldung wird jetzt angezeigt (Issue #96)
- Linux Mint Cinnamon: Mausrad-Scrollen in der Hauptapp funktioniert jetzt (WebKitGTK-Workaround)
- Kategorien: 5 fehlende Einträge ergänzt (AfA, Fahrtkosten Privat-PKW, Verpflegungsmehraufwand, Mitgliedsbeiträge, Spenden betrieblich) mit korrekter EKS- und EÜR-Zuordnung (Issue #106)

---

## [v0.2.6] – Mai 2026

### 🐛 Behoben
- Rechnungs-PDF: USt-Aufschlüsselung pro Steuersatz (§14 UStG) bei gemischten Sätzen; B2B-Kunden (ZUGFeRD) erhalten Netto-, B2C-Kunden Bruttorechnung (Issue #101)
- Ausgangsrechnung: Kategorie-Feld entfernt – Erlöskategorie wird automatisch ermittelt (Issue #100)
- CachyOS/Arch: Sidecar-Absturz beim Start (Exit 3) durch entferntes imghdr-Modul behoben – Magic-Bytes-Erkennung als Ersatz (Issue #92)
- Setup-Wizard: Mausrad-Scrollen unter Mint Cinnamon / GTK-Desktops funktioniert jetzt
- Migration: Sehr alte Datenbanken (v0.1.x) werden beim Start vollständig migriert ohne Fehler

---

## [v0.2.5] – Mai 2026

### ✨ Neu
- Journal: Netto- und USt-Betrag werden als separate Zeilen angezeigt – vollautomatisch anhand des USt-Satzes aufgeteilt
- Benutzerkategorien können jetzt vollständig bearbeitet werden (Name, Konten, alle Felder)

### 🐛 Behoben
- XRechnung-Import: Lieferantenname und Fälligkeitsdatum wurden bei UBL-Format nicht erkannt (Issue #98)
- PDF-Import öffnet jetzt den systemseitig eingestellten PDF-Viewer statt des eingebetteten Viewers (Issue #99)
- Kategorie löschen: Bestätigungs-Dialog zeigte fälschlich "tauri.localhost" (Issue #96)
- Mausrad-Scrollen im Setup-Wizard unter Linux Cinnamon/Muffin funktioniert jetzt

---

## [v0.2.4] – Mai 2026

### ✨ Neu
- Eingangsrechnungen importieren – ZUGFeRD/XRechnung werden automatisch erkannt und Felder vorausgefüllt
- Eingangsrechnung-Import: plain PDF öffnet sich automatisch zum Abschreiben, Originaldatei wird als Beleganhang gespeichert
- Kategorien: SKR03/SKR04-Kontonummern im Bearbeitungsmodus editierbar, Reset auf Standardwert möglich
- Kategorien: eigene Kategorien anlegen und nicht verwendete löschen

### 🔧 Verbessert
- EÜR-Zeilennummern auf Anlage EÜR 2025 aktualisiert (44 Korrekturen)
- SKR03/SKR04-Kontonummern auf DATEV-Kontenrahmen 2026 korrigiert (39 Korrekturen)

### 🐛 Behoben
- Mausrad-Scrollen im Setup-Wizard unter Linux Mint Cinnamon (WebKit2GTK)
- Reset-Button in Kategorien aktualisiert den angezeigten Wert sofort

---

## [v0.2.3] – Mai 2026

### 🐛 Behoben
- Setup-Wizard scrollbar in Tauri – langer Inhalt war abgeschnitten, Wizard ist jetzt vollständig scrollbar

---

## [v0.2.2] – Mai 2026

### ✨ Neu
- Kategorien ein-/ausblenden – einzelne Buchungskategorien können deaktiviert werden und erscheinen dann nicht mehr in Buchungsformularen
- EKS-Zuordnung automatisch: USt-Betrag aus Einnahmen wird automatisch A5_1 (vereinnahmt) und A5_2 (Eigenverbrauch) zugeordnet – kein manueller Eintrag mehr nötig
- Reisekosten in drei EKS-Unterkategorien aufgeteilt: B7_1 Übernachtung, B7_2 Nebenkosten, B7_3 ÖPNV
- Neue Buchungskategorien: KFZ-Reparatur (B6_4), Investition aus Zuwendung Dritter (B9), Personalkosten Familienangehörige (B2_4), Löhne & Gehälter Teilzeit (B2_2), AG-Anteil Sozialversicherung, Eigenverbrauch von Waren (19%/7%), Wareneinkauf EU/Nicht-EU, Miete Büro (0%), KFZ-Leasing
- Buchungskategorie „Reparatur Anlagevermögen" (B14.1) – Reparatur- und Instandhaltungskosten für Betriebsanlagen und Maschinen (außer KFZ); SKR03 4855 / SKR04 6805
- Buchungskategorie „Miete Einrichtung" (B14.2) – Mietkosten für bewegliche Wirtschaftsgüter und Einrichtungsgegenstände; SKR03 4240 / SKR04 6830
- Buchungskategorie „Betriebliche Abfallbeseitigung" (B14.4) – Entsorgungskosten; SKR03 4830 / SKR04 6810

### 🔧 Verbessert
- Scrollen: Sidebar und Hauptinhalt scrollen jetzt unabhängig voneinander – die Navigation bleibt beim Scrollen langer Listen immer sichtbar
- Kategorien-Tabelle: erste Spalte bleibt beim horizontalen Scrollen sichtbar (sticky)

### 🐛 Behoben
- Build-Fehler behoben – TypeScript-Fehler in der Journal-Kategorienauswahl verhinderte den Release-Build

---

## [v0.2.1] – Mai 2026

### ✨ Neu
- Beleganhang für Eingangsrechnungen – PDF, JPG oder PNG direkt an eine Eingangsrechnung anhängen, im eingebetteten Viewer öffnen und bei Bedarf löschen; SHA256-Hash wird für die GoBD-Nachweisbarkeit gespeichert

### 🐛 Behoben
- PDF-Doppelöffnung behoben – auf Windows öffnete ein Klick auf eine lokale Datei gleichzeitig den Systembrowser und Acrobat; lokale Dokumente werden jetzt plattformübergreifend (Windows, Linux, macOS) im eingebetteten Viewer angezeigt

---

## [v0.1.67] – Mai 2026

### ✨ Neu
- Bankkonten-Verwaltung in Stammdaten – Konten anlegen, bearbeiten und löschen; Unterscheidung zwischen Bankkonto und Zahlungsdienstleister (PayPal, Stripe usw.) mit IBAN, BIC, Kontoinhaber und Notizfeld
- Kontoart-Unterscheidung – Bankkonto (IBAN Pflicht) vs. Zahlungsdienstleister (Kennung statt IBAN); Partial Unique Index verhindert doppelte Einträge
- Kategorien-Übersicht in Stammdaten – alle Buchungskategorien auf einen Blick mit EÜR-Zuordnung, USt-Satz und EKS-Kategorie; Inline-Bearbeitung direkt in der Tabelle

---

## [v0.1.65] – Mai 2026

### 🔧 Verbessert
- Anlage EKS: vollständiger 9-seitiger Formular-Nachbau nach offiziellem Jobcenter-Formular 04/2025 – Tabellen A/B/C, Abschnitte D/F/Seite 9, Übertrag zwischen Tabellenteilen, Textumbrüche in Zellen

### ✨ Neu
- EKS: Persistente Formularfelder (Abschnitte D, F 23–41, Seite 9 52–58) per Modal – Eingaben bleiben über Sitzungen hinweg gespeichert

### 🐛 Behoben
- EKS: Auto/Manuell-Badge bei vorläufiger EKS korrekt gesetzt; EKS-PDF öffnet sich zuverlässig im Inline-Viewer

---

## [v0.1.64] – Mai 2026

### ✨ Neu
- Anlage EKS – Einkommenserklärung für Selbstständige (Jobcenter / Bürgergeld): abschließend (summiert Journalbuchungen nach EKS-Kategorie) und vorläufig (Halbjahres-Prognose aus Vorjahresdaten); PDF-Export; nur sichtbar wenn Transferleistungen aktiviert
- DSGVO-Datenauskunft als PDF-Export – strukturierter Bericht mit allen gespeicherten Daten zu einem Kunden oder Lieferanten (Art. 15 DSGVO)

### 🐛 Behoben
- Tagesabschluss-Saldo berücksichtigt jetzt alle Buchungen seit dem letzten Abschluss (nicht nur den aktuellen Tag)
- Dashboard-Statistik schließt Privateinlagen und -entnahmen aus – nur betriebliche Buchungen fließen in Einnahmen/Ausgaben ein
- Benutzerdefinierte USt-Sätze werden bei Rechnungen und Journal-Buchungen jetzt akzeptiert
- Journal-Filter: Highlighting und Reset-Button; Zahlungsart als Select mit farbiger Markierung wenn aktiv

---

## [v0.1.63] – Mai 2026

### 🐛 Behoben
- Unternehmensdaten: Logo verschwindet nicht mehr nach dem Speichern – logo_pfad wird beim Speichern der Firmendaten nie überschrieben, da er ausschließlich über den Logo-Upload/-Löschen-Endpunkt verwaltet wird (Issue #85)

---

## [v0.1.62] – Mai 2026

### ✨ Neu
- Journal: Filter für Bar- und Unbar-Zahlungen (Karte, Bank, PayPal)
- Journal-Detailansicht: Belegnummer per Klick in die Zwischenablage kopieren
- macOS-Build: DMG für Apple Silicon (M1–M4) und Intel in GitHub Actions

### 🔧 Verbessert
- Kassenbuch wurde in Journal umbenannt – der Begriff Kassenbuch bleibt für eine spätere Funktion frei

### 🐛 Behoben
- GoBD-Export auf Linux: weißes Fenster behoben – ZIP wird jetzt direkt heruntergeladen mit Erfolgsmeldung
- Nummernkreis: Nächste Nummer kann nicht mehr verringert werden – verhindert doppelte Belegnummern
- Kunden- und Lieferantennummern: Doppelvergabe wird jetzt auf API- und Datenbankebene verhindert
- Artikel: benutzerdefinierte MwSt.-Sätze (z.B. 7,8 % Landwirtschaft) wurden beim Anlegen und Bearbeiten fälschlich abgelehnt – Prüfung erfolgt jetzt gegen die hinterlegten aktiven Steuersätze
- Dashboard Zufluss-Monitor: Bürgergeld-Berechnung korrigiert – § 11b SGB II verwendet eine dreistufige Freibetragsregelung (0–100 € frei, 100–1.000 € 20 % frei, 1.000–1.200 € 10 % frei), nicht eine Pauschal-Grenze bei 520 €

---

## [v0.1.60] – April 2026

### 🔧 Verbessert
- Rechnungs-PDF: Positionsbeschreibungen brechen jetzt automatisch um – kein Abschneiden bei langen Texten mehr; manuelle Zeilenumbrüche im Beschreibungsfeld werden übernommen (Issue #76)
- Kunden/Lieferanten: Firmenname und Vorname+Nachname erscheinen jetzt auf getrennten Zeilen im Rechnungs-PDF; neues Feld „z.Hd. von" für Ansprechpartner/Abteilung (Issue #79)

### 🐛 Behoben
- ZUGFeRD: Decimal-Division erzeugte bei bestimmten Beträgen wissenschaftliche Notation (1E+2 statt 100.00) – xs:decimal-Validierungsfehler auf Windows (Issue #71)
- ZUGFeRD: Vorname+Nachname wird als Firmenname verwendet wenn kein Firmenname eingetragen ist (Freiberufler)
- ZUGFeRD: Hausnummer und weitere Felder gegen None-Werte abgesichert
- Update-Hinweis: App startet nach dem Update automatisch neu – kein manueller Neustart nötig (Issue #75)
- GiroCode-Tooltip in Unternehmenseinstellungen öffnet sich jetzt nach links – war am rechten Fensterrand abgeschnitten (Issue #77)

---

## [v0.1.59] – April 2026

### 🔧 Verbessert
- Unternehmensdaten & Setup-Wizard: Pflichtfeld-Validierung überarbeitet – Firmenname oder Vor-/Nachname (beides möglich), Steuernummer oder USt-IdNr., IBAN sowie Adressfelder sind jetzt Pflicht; länderspezifische PLZ-Prüfung (DE/AT/CH/NL/LI), ZUGFeRD-Zeichensatz-Prüfung
- Setup-Wizard: IBAN aus StepKonto wird jetzt automatisch in die Unternehmensdaten übernommen – Bankverbindung erscheint sofort auf Rechnungen
- Backend-Logging: FastAPI/uvicorn schreibt Fehler jetzt in eine Datei (APP_DATA_DIR/logs/backend.log, max. 5 MB × 3) – auf Windows waren Backend-Fehler bisher unsichtbar
- Kunden: Zeile anklicken klappt alle Stammdaten direkt in der Tabelle auf (Akkordeon) – Vorname/Nachname, Adresse, E-Mail, Telefon, USt-IdNr., Kundennr., Badges, Notizen; alle weiteren Zeilen schieben sich nach unten

### 🐛 Behoben
- ZUGFeRD: fehlende Unternehmenspflichtfelder erzeugen jetzt eine klare Fehlermeldung im Log; Seller-Name nutzt Firmenname oder Vor-/Nachname als Fallback

---

## [v0.1.57] – April 2026

### 🐛 Behoben
- ZUGFeRD: Pflichtfeld-Validierung im Kundenstamm – Firmenname, Straße, PLZ und Ort werden bei manuell aktiviertem ZUGFeRD als Pflichtfelder geprüft; Amber-Hinweis wenn keine USt-IdNr. vorhanden
- ZUGFeRD: utils.zugferd und saxonche fehlten im PyInstaller-Build – ZUGFeRD-PDF wurde im AppImage/MSI lautlos durch normales PDF ersetzt
- InfoTooltip bei „Kopie öffnen" wurde über den rechten Rand hinausgeschoben – öffnet sich jetzt nach links (Issue #74)

---

## [v0.1.54] – April 2026

### ✨ Neu
- ZUGFeRD / E-Rechnung: Ausgangsrechnungen an Firmenkunden werden automatisch als PDF/A-3 mit eingebettetem FacturX-XML (EN 16931 Comfort) ausgegeben wenn im Kundenstamm ZUGFeRD aktiviert ist – erfüllt die B2B-E-Rechnungspflicht (Issue #62)

### 🐛 Behoben
- Logo-Upload: Dateien werden jetzt anhand des Dateiinhalts erkannt – Upload schlug fehl wenn die WebView einen falschen MIME-Typ übermittelte (Linux AppImage, Windows)
- Bürgergeld/Transferleistungen: Checkbox jetzt auch in Stammdaten → Unternehmen → Steuer & Rechtsform – war bisher nur im Setup-Wizard erreichbar (Issue #64)
- Zombie-Backend: Beim App-Start werden jetzt eventuell noch laufende Backend-Prozesse vom letzten Absturz beendet – verhindert DB-Sperren und "Failed to Fetch" nach einem Absturz (Issue #67)
- GiroCode-Tooltip: InfoTooltip war halb transparent wenn keine IBAN hinterlegt war – opacity-50 vererbte sich auf alle Kind-Elemente (Issue #65)
- Linux: install-linux.sh prüft und installiert libfuse2 automatisch (Ubuntu 22.04–26.04) – App-Icon eingebettet, kein curl/wget mehr nötig (Issue #69)
- Linux: Ubuntu 26.04 / webkit2gtk 2.52 – WEBKIT_DISABLE_COMPOSITING_MODE=1 verhindert Segfault beim Start (Issue #70)

---

## [v0.1.52] – April 2026

### ✨ Neu
- GiroCode (QR) auf Ausgangsrechnungen – EPC-QR-Code wird neben dem Zahlungshinweis eingebettet; Kunden können per Banking-App mit vorausgefüllten Daten direkt überweisen (aktivierbar in Unternehmenseinstellungen → Zahlungseinstellungen)

### 🔧 Verbessert
- GiroCode-Aktivierung gesperrt wenn keine IBAN hinterlegt ist – Tooltip erklärt warum

### 🐛 Behoben
- Dark-Mode: Alle Formular-Felder (select, input, textarea) auf allen Seiten korrekt dunkel – Browser-Default war weiß
- Kassenbuch: Eigene MwSt-Sätze aus den Einstellungen erscheinen jetzt im USt-Dropdown (nicht mehr nur 0/7/19 %)
- USt-Dropdown in Rechnungen und Kassenbuch: Bezeichnung nicht mehr abgeschnitten – zeigt nur die Prozentzahl

---

## [v0.1.44] – April 2026

### ✨ Neu
- GiroCode (EPC-QR) auf Ausgangsrechnungen – aktivierbar in den Unternehmenseinstellungen; Kunden können per Banking-App überweisen, IBAN, Betrag und Rechnungsnummer werden vorausgefüllt (Issue #53)
- Digitale Unterschrift – einmal hinterlegen, optional auf Ausgangsrechnungen und Tagesabschlüssen ausgeben (Issue #58)
- Fälligkeiten-Dashboard – neue Kachel zeigt fällige und überfällige Rechnungen; zusätzliche „Fällig am"-Spalte in der Rechnungsliste mit Sortierung (Issue #59)
- Standard-Zahlungsziel – einstellbar in den Unternehmenseinstellungen (Standard: 14 Tage); neue Rechnungen erhalten automatisch das korrekte Fälligkeitsdatum
- Gutschriften – negative Menge (z. B. −1) und negative Beträge in Rechnungspositionen jetzt möglich

### 🐛 Behoben
- PDF-Original statt Kopie: Race-Condition behoben, bei der das erste PDF fälschlicherweise als Kopie gestempelt wurde (Issue #57)
- Vorlage Sandra grün: Unterschrift kollidierte mit dem Überweisungsblock – Cursor-Position korrigiert
- Rechnungsformular: Summenanzeige zeigt jetzt auch negative Beträge korrekt an

---

## [v0.1.40] – April 2026

### ✨ Neu
- Eingangsrechnungen: Belegnummer des Lieferanten kann optional erfasst werden – wird im Detail-Panel angezeigt und ist über die Suchfunktion durchsuchbar (Issue #52)
- Eingangsrechnungen: Schnelleingabe-Modus – statt Positionstabelle nur Betrag, USt-Satz und Beschreibung eingeben; mit einem Klick auf „Positionen aufschlüsseln" wechseln (Issue #42)
- Eingangsrechnungen: Im Positionsmodus kann jeder Zeile ein eigenes Konto (Kategorie) zugewiesen werden – überschreibt die Hauptkategorie der Rechnung (Issue #42)

### 🐛 Behoben
- Rechnungsentwurf: Preis änderte sich jedes Mal beim erneuten Öffnen und Speichern – Brutto-Eingabemodus wurde fälschlich als Netto interpretiert (Issue #50)
- Stückzahl „10" wurde als „10.000" (Zehntausend) angezeigt – Python Decimal-Trailing-Zeros werden jetzt beim Laden normalisiert

---

## [v0.1.38] – April 2026

### ✨ Neu
- Lieferanten: Suchfeld hinzugefügt – Suche nach Firmenname, E-Mail, Lieferantennummer und Ort
- Artikelstamm: VK und EK können jetzt wahlweise als Netto oder Brutto eingegeben werden – der jeweils andere Wert wird automatisch anhand des Steuersatzes berechnet (Issue #38)
- Rechnungen: Suchfeld nach Rechnungsnummer und Partnername – Volltextsuche mit Teiltreffern, kombinierbar mit dem Status-Filter (Issue #49)

### 🔧 Verbessert
- Split-Screen-Layout: Beim Öffnen des Formulars kollabiert die Liste auf ¼ Breite, das Formular bekommt ¾ – einheitlich für Rechnungen, Kunden, Lieferanten und Artikelstamm (Issue #39)
- Kunden, Lieferanten und Artikelstamm: permanentes Detail-Panel rechts (wie Rechnungsdetails) – zeigt beim Anklicken einer Zeile Details, verschwindet beim Bearbeiten (Issue #36)
- Artikelstamm Detail-Panel: strukturierter Aufbau mit Header, Sections (Preise, Details, Beschreibung, Verknüpfte Rechnungen) und Footer – analog Rechnungsdetails (Issue #46)
- Lieferanten Detail-Panel: Header mit Name, Sections für Adresse, Kontakt, Steuer und Notizen
- Kunden, Lieferanten, Artikelstamm: einheitliches Design – p-6 Header, text-2xl Titel, rounded-xl Buttons, Tabelle/Liste in Card-Wrapper (Issue #36)
- Infotexte präzisiert: Handelsregister erklärt jetzt Abteilung A (HRA) und B (HRB), Ist-Versteuerung weist auf einmaligen Antrag beim Finanzamt hin (Issue #37)

### 🐛 Behoben
- Background-Inkonsistenz behoben: Kunden, Lieferanten, Rechnungen und Artikelstamm hatten einen anderen Hintergrund als der Rest der App
- Fenstertitel zeigte „RechnungsFee Testing" statt „RechnungsFee" (Issue #43)
- Tagesabschluss-PDF auf Windows: Interner Fehler 500 behoben – DejaVu-Fonts wurden im PyInstaller-Bundle nicht gefunden (Issue #47)
- GoBD-Export-PDF: gleicher Font-Suchpfad-Fix wie Tagesabschluss (Issue #47)
- Zahlungsdialog: Zukunftsdaten werden jetzt abgelehnt – Datumsauswahl ist auf heute begrenzt, Fehlermeldung bei manuellem Eintrag eines zukünftigen Datums (Issue #44)
- Rechnungsübersicht: Entwürfe werden jetzt korrekt als „Entwurf" angezeigt statt als „Offen" – in der Liste und im Detailpanel (Issue #45)
- Rechnungsübersicht: Filter-Dropdown um „Entwurf" und „Storniert" erweitert (Issue #45)
- Rechnungsübersicht: Saldo „Offen" und Kachel „Gesamt" berücksichtigen jetzt nur echte Rechnungen – Entwürfe und stornierte Rechnungen werden nicht mehr eingerechnet (Issue #45)

---

## [v0.1.34] – April 2026

### ✨ Neu
- Rechnungsvorlagen: Community-Vorlage „Sandra grün" für Kleinunternehmer – Tabelle mit Pos./Datum/Beschreibung/Saldo, grünes Design, persönliche Anrede, Überweisungsblock mit IBAN (Issue #33, Dank an @trinity2701)
- Rechnungsvorlagen-Auswahl: unter Stammdaten → Rechnungsvorlagen kann die Standard-Vorlage für alle Ausgangsrechnungen gewählt werden – mit Vorschau-Funktion
- Dark Mode: folgt automatisch dem System-Theme (prefers-color-scheme) – kein manueller Toggle (Issue #29)
- Kleinunternehmer-Umsatzwarnung: Dashboard zeigt ab 80.000 € Netto-Jahresumsatz ein Warn-Banner, ab 100.000 € eine kritische Warnung mit Handlungsaufforderung (Issue #30)

### 🔧 Verbessert
- Kleinunternehmer-Infotext in Stammdaten auf neue Grenzen ab 2025 aktualisiert: Vorjahresumsatz ≤ 25.000 € netto, laufendes Jahr unter 100.000 € netto (Issue #30)

### 🐛 Behoben
- Info-Tooltips werden nicht mehr am linken Bildschirmrand abgeschnitten – öffnen sich jetzt linksbündig statt zentriert (Issue #31)
- USt-IdNr. wird jetzt auf gültiges Format geprüft: deutsche IdNr. muss DE + 9 Ziffern sein (Issue #31)
- Stammdaten: Partial-Updates (z.B. Vorlagenauswahl) überschreiben keine anderen gespeicherten Felder mehr

---

## [v0.1.33] – März 2026

### ✨ Neu
- Neues App-Icon von @Adler_real (LinuxGuidesDECommunity) – herzlichen Dank!
- MwSt.-Sätze konfigurierbar: eigene Sätze hinzufügen (z.B. 5,5 %), Sätze aktivieren/deaktivieren und einen Standard-Satz festlegen – gilt für Rechnungsformular und Artikelstamm (Issue #23)
- Rechnungs-PDF: Standard-Zahlungshinweis (IBAN-Überweisungstext) kann in Unternehmen → Rechnungs-PDF deaktiviert werden – Notizfeld bleibt immer zusätzlich sichtbar (Issue #24)

### 🔧 Verbessert
- Kundenstamm: Split-View mit Suchleiste, vollständiger Tabelle, Stammdaten-Karte bei Klick und schmalem Rechnungspanel rechts

### 🐛 Behoben
- Kundenstamm: Artikel-Typ-Badge in Rechnungspositionen zeigt jetzt korrekt „Artikel", „Dienstl." oder „Fremdl." statt immer „Artikel"
- Kassenbuch: Bar-Ausgabe die den Kassenstand ins Minus treibt wird jetzt abgelehnt – rotes Banner und gesperrter Speichern-Button (gilt nur für Barkasse, nicht für Karte/Bank/PayPal)

---

## [v0.1.32] – März 2026

### ✨ Neu
- Artikelstamm: Artikel und Dienstleistungen zentral verwalten (Eigenleistung, Dienstleistung, Fremdleistung) mit Artikelnummer, Preisen, Steuersatz, Lieferant und mehr
- Rechnungen: Artikel-Autocomplete in Positionen – ab 3 Zeichen werden passende Artikel aus dem Stamm vorgeschlagen und füllen Beschreibung, Einheit, Preis und USt automatisch
- Kundenstamm: „Rechnungen"-Button pro Kunde zeigt alle Ausgangsrechnungen mit aufklappbaren Positionen (Artikel-Badge wenn aus Artikelstamm)

---

## [v0.1.23] – März 2026

### ✨ Neu
- Berufsbezeichnung & Kammermitgliedschaft: 12 Berufskarten im Setup-Assistenten, Kammerberufe (Rechtsanwalt, Steuerberater, Architekt, Arzt) werden automatisch vorausgefüllt – erscheinen auf PDF-Rechnungen

### 🐛 Behoben
- Mail-Versand funktioniert jetzt auf Linux (kein "URL can't be shown" mehr) und Windows (PDF wird korrekt erstellt)
- AppImage behält nach einem Update jetzt seinen Dateinamen – kein manuelles Umbenennen mehr nötig
- Linux: RechnungsFee erscheint jetzt mit eigenem Icon im Anwendungsmenü (nach einmaligem Ausführen von install-linux.sh)
- Setup-Assistent: Schrittanzeige ist jetzt auf Windows und Linux korrekt ausgerichtet

---

## [v0.1.1] – März 2026

### ✨ Neu
- Kassenbuch mit GoBD-konformen unveränderlichen Einträgen und SHA-256-Signaturen (§146 AO)
- Rechnungen (Eingang & Ausgang) mit Zahlungsverfolgung, Teilzahlungen und PDF nach DIN 5008
- Kunden & Lieferanten mit DSGVO-Funktionen (Auskunft Art. 15, Löschung Art. 17)
- Tagesabschlüsse mit SHA-256-Integritätsprüfung und PDF-Export
- GoBD-Export für Betriebsprüfungen (Z3-Datenträgerüberlassung, 8 Dateien als ZIP)
- Backup-Funktion: manueller Download + automatisches Backup vor DB-Updates
- Kontext-Hilfe mit ℹ-Tooltips für GoBD-Konzepte, Steuerfelder und Rechnungslogik
- Setup-Assistent für den ersten Start (Unternehmen, Konto, Anfangsbestand)
- Nummernkreise frei konfigurierbar (Kassenbuch KB, Rechnung RE, Kunden KD, Lieferanten LI)
- Logo-Upload + Mail-Vorlagen in den Unternehmensstammdaten
- Kleinunternehmer §19 UStG vollständig unterstützt (USt automatisch 0 %, kein Vorsteuerabzug)
