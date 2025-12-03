## **📅 Projektplan: RechnungsPilot (Version 1.0)**
**Ziel:** Eine plattformunabhängige, Open-Source-Lösung für Rechnungserfassung, -verwaltung und Steuerdokumentengenerierung (EAR, EKS) mit Fokus auf §19 UStG und EKS-Kategorisierung.

---

### **📌 Phase 1: Vorbereitung (Woche 1–2)**
**Ziel:** Klare Anforderungen, Technologie-Stack und Entwicklungsumgebung festlegen.

| Aufgabe                                      | Verantwortlich | Technologie/Tools                     | Ergebnis                                  |
|----------------------------------------------|----------------|---------------------------------------|--------------------------------------------|
| **Anforderungsdokument finalisieren**        | Nicoletta      | Markdown/Confluence                   | Dokument mit User Stories und Akzeptanzkriterien |
| **Technologie-Stack auswählen**              | Nicoletta      | Recherche                            | Entscheidung: React (Frontend), FastAPI (Backend), SQLite (DB) |
| **Entwicklungsumgebung einrichten**         | Nicoletta      | Docker, VS Code, GitHub               | Lokale Dev-Umgebung mit Hot-Reload         |
| **Steuerformular-Templates recherchieren**  | Nicoletta      | ELSTER, GoBD, Anlage EKS (BA)         | Vorlagen für EAR-XML und EKS-CSV           |
| **OCR-Bibliothek evaluieren**               | Nicoletta      | Tesseract.js vs. EasyOCR              | Entscheidung: Tesseract.js (lokal, Open Source) |

---

### **📌 Phase 2: Prototyp (Woche 3–6)**
**Ziel:** Ein funktionierender Prototyp mit Kernfunktionen: Rechnungserfassung, EKS-Kategorisierung, EAR/EKS-Export.

#### **🔧 Frontend (React PWA)**
| Aufgabe                                      | Technologie                     | Ergebnis                                  |
|----------------------------------------------|---------------------------------|--------------------------------------------|
| **UI-Konzept & Design**                      | Figma, React                    | Mockups für Rechnungserfassung & Übersicht |
| **Rechnungserfassungsformular**              | React Hooks, Formik             | Formular mit Pflichtfeldern & EKS-Kategorien |
| **Drag & Drop für PDFs**                      | react-dropzone                  | Upload & Vorschau von Rechnungen           |
| **OCR-Integration (Tesseract.js)**           | Tesseract.js                    | Extraktion von Rechnungsdaten (Nummer, Betrag, USt-IdNr.) |
| **EKS-Kategorisierung**                      | React Select                    | Dropdown für EKS-Kategorien (Anlage EKS)   |
| **Rechnungsübersicht (Tabelle)**            | React Table                     | Filterbare Liste mit Status, Datum, Kunde  |

#### **🔧 Backend (FastAPI)**
| Aufgabe                                      | Technologie                     | Ergebnis                                  |
|----------------------------------------------|---------------------------------|--------------------------------------------|
| **API für Rechnungsspeicherung**             | FastAPI, SQLite                 | CRUD-Endpoints für Rechnungen              |
| **EAR-XML-Generierung**                      | xml.etree (Python)              | GoBD-konforme XML-Datei                   |
| **EKS-CSV-Export**                           | Python CSV                      | Vorlage für Anlage EKS (BA)                |
| **§19 UStG-Plausi-Check**                    | Python (RegEx/Validierung)      | Warnung bei Überschreitung der Umsatzgrenze |

#### **🗄️ Datenbank (SQLite)**
| Aufgabe                                      | Technologie                     | Ergebnis                                  |
|----------------------------------------------|---------------------------------|--------------------------------------------|
| **Datenbankschema entwerfen**                | SQLite                          | Tabellen: Rechnungen, Kunden, EKS-Kategorien |
| **Verschlüsselung implementieren**           | SQLCipher                       | AES-256-Verschlüsselung der DB             |

#### **📱 Mobile Version (PWA)**
| Aufgabe                                      | Technologie                     | Ergebnis                                  |
|----------------------------------------------|---------------------------------|--------------------------------------------|
| **Kamera-Integration für Scannen**           | React Camera, Tesseract.js      | Scannen von Rechnungen per Handy          |
| **Offline-Fähigkeit testen**                 | Service Worker                  | Rechnungen erfassen ohne Internet          |

---

### **📌 Phase 3: Test & Feedback (Woche 7–8)**
**Ziel:** Prototyp mit 5–10 Freiberuflern testen und Feedback einarbeiten.

| Aufgabe                                      | Verantwortlich | Technologie                     | Ergebnis                                  |
|----------------------------------------------|----------------|---------------------------------|--------------------------------------------|
| **Testumgebung bereitstellen**               | Nicoletta      | Docker, GitHub Pages            | Demo-Instanz für Tester                    |
| **Usability-Tests durchführen**             | Tester          | Hotjar, Feedback-Formular       | Liste mit Bugs & Verbesserungsvorschlägen |
| **OCR-Genauigkeit evaluieren**               | Nicoletta      | Manuelle Prüfung               | Fehlerquote < 5%                          |
| **EAR/EKS-Exporte prüfen**                   | Steuerberater  | ELSTER, Excel                   | Korrekte Übertragung der Daten            |

---

### **📌 Phase 4: Finalisierung (Woche 9–10)**
**Ziel:** Bugfixes, Dokumentation und Veröffentlichung der Version 1.0.

| Aufgabe                                      | Verantwortlich | Technologie                     | Ergebnis                                  |
|----------------------------------------------|----------------|---------------------------------|--------------------------------------------|
| **Bugfixes umsetzen**                        | Nicoletta      | GitHub Issues                   | Stabiler Prototyp                         |
| **Dokumentation erstellen**                  | Nicoletta      | MkDocs                          | Anleitung für Installation & Nutzung      |
| **Open-Source veröffentlichen**              | Nicoletta      | GitHub                          | Repository mit AGPL-3.0-Lizenz            |
| **Backup-Funktion implementieren**          | Nicoletta      | Python (shutil), Nextcloud API  | Automatische Sicherung nach Nextcloud      |

---

### **📌 Phase 5: Erweiterungen (ab Woche 11)**
**Ziel:** Optionale Features für spätere Versionen.

| Feature                              | Priorität | Technologie                     |
|--------------------------------------|-----------|---------------------------------|
| **ELSTER-Schnittstelle**             | Mittel    | ELSTER API                      |
| **Electron-App für lokale Nutzung**  | Niedrig   | Electron                        |
| **Mandantenfähigkeit**               | Niedrig   | PostgreSQL, Auth0               |
| **Mehrsprachigkeit**                 | Niedrig   | i18n (React)                    |

---

## **📊 Meilensteine & Zeitplan**
| Meilenstein                          | Zieldatum       | Verantwortlich |
|--------------------------------------|-----------------|-----------------|
| **Anforderungsdokument finalisiert** | Ende Woche 2    | Nicoletta       |
| **Prototyp (Frontend + Backend)**    | Ende Woche 6    | Nicoletta       |
| **Testphase abgeschlossen**          | Ende Woche 8    | Tester           |
| **Version 1.0 veröffentlicht**      | Ende Woche 10   | Nicoletta       |

---

## **🔧 Technologie-Stack im Detail**
| Bereich               | Technologie                     | Begründung                                  |
|-----------------------|---------------------------------|---------------------------------------------|
| **Frontend**          | React (PWA)                     | Plattformunabhängig, gute Community         |
| **Backend**           | FastAPI (Python)                | Schnell, einfach, gute Dokumentation       |
| **Datenbank**         | SQLite (SQLCipher)              | Lokal, verschlüsselt, keine Serverkosten   |
| **OCR**               | Tesseract.js                    | Open Source, lokal, keine Cloud-Abhängigkeit |
| **Steuerformulare**   | ELSTER/XRechnung                | Konform mit deutschen Vorschriften          |
| **Backup**            | Nextcloud API                   | Nutzerfreundlich, sicher                    |
| **Verschlüsselung**  | AES-256 (SQLCipher)             | Hohe Sicherheit, bewährt                   |

---
