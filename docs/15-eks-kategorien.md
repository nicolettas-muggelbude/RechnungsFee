# Anlage EKS – Journal-Kategorien-Verknüpfung

Alle 28 EKS-Felder (Tabellen A, B, C) sind mit Journal-Kategorien und DATEV-Konten verknüpft.
Jede Buchung in einer der unten aufgeführten Kategorien fließt automatisch in das entsprechende EKS-Feld.

---

## Tabelle A – Einnahmen

| EKS-Feld | Bezeichnung (EKS) | Kategorie(n) | SKR03 | SKR04 | Kontenart |
|----------|-------------------|--------------|-------|-------|-----------|
| A1 | Betriebseinnahmen (brutto) | Betriebseinnahmen | 8400 | 4400 | Erlös |
| | | Betriebseinnahmen (7%) | 8300 | 4300 | Erlös |
| | | Betriebseinnahmen (0%) | 8100 | 4100 | Erlös |
| | | Kleinunternehmer-Einnahmen | 8100 | 4100 | Erlös |
| A2 | Privatentnahmen | Privatentnahme | 1800 | 2010 | Privat |
| A3 | Sonstige Einnahmen | Sonstige Einnahmen | 8900 | 4900 | Erlös |
| A4 | Privateinlagen | Privateinlage | 1890 | 2100 | Privat |
| A5_1 | Vereinnahmte Umsatzsteuer | Umsatzsteuer (vereinnahmt) | 1776 | 1776 | Aufwand |
| A5_2 | USt-Erstattung Finanzamt | Umsatzsteuer-Erstattung FA | 1779 | 1779 | Erlös |

---

## Tabelle B – Betriebsausgaben

| EKS-Feld | Bezeichnung (EKS) | Kategorie(n) | SKR03 | SKR04 | Kontenart |
|----------|-------------------|--------------|-------|-------|-----------|
| B1 | Waren, Roh-/Hilfsstoffe | Wareneinkauf | 3000 | 5000 | Aufwand |
| | | Wareneinkauf (7%) | 3000 | 5000 | Aufwand |
| B3 | Löhne und Gehälter | Löhne & Gehälter | 4120 | 6010 | Aufwand |
| B4 | Fremdleistungen | Fremdleistungen | 3100 | 5900 | Aufwand |
| B5 | Miete, Nebenkosten, Arbeitszimmer | Miete Büro | 4210 | 6310 | Aufwand |
| | | Nebenkosten Büro | 4230 | 6320 | Aufwand |
| | | Arbeitszimmer (anteilig) | 4215 | 6315 | Aufwand |
| B6 | Versicherungen, Beiträge | Betriebsversicherungen | 4360 | 6430 | Aufwand |
| | | Berufsgenossenschaft | 4380 | 6450 | Aufwand |
| B7 | KFZ-Kosten | KFZ-Kosten | 4530 | 6520 | Aufwand |
| | | KFZ-Versicherung | 4360 | 6430 | Aufwand |
| B8 | Reisekosten | Reisekosten | 4660 | 6640 | Aufwand |
| B9 | Büro, Werbung, Sonstiges | Büromaterial | 4910 | 6815 | Aufwand |
| | | Büroausstattung | 4920 | 6820 | Aufwand |
| | | Porto & Versand | 4930 | 6825 | Aufwand |
| | | Software & Abonnements | 4940 | 6831 | Aufwand |
| | | Werbung & Marketing | 4600 | 6600 | Aufwand |
| | | Bewirtungskosten | 4650 | 6620 | Aufwand |
| | | Bankgebühren | 4970 | 6855 | Aufwand |
| | | Geringwertige Wirtschaftsgüter (GWG) | 0480 | 0680 | Aufwand |
| B10 | Telefon und Internet | Telefon & Internet | 4920 | 6820 | Aufwand |
| B11 | Steuer-, Rechts- und Beratungskosten | Steuerberatung | 4960 | 6835 | Aufwand |
| | | Rechts- & Beratungskosten | 4970 | 6840 | Aufwand |
| | | Buchführungskosten | 4975 | 6845 | Aufwand |
| B12 | Aus- und Fortbildung | Fortbildung & Fachliteratur | 4945 | 6820 | Aufwand |
| B14 | Zinsen und Finanzierungskosten | Zinsen & Darlehenskosten | 4315 | 7310 | Aufwand |
| B15 | Tilgungsleistungen | Kredittilgung | 2100 | 3150 | Aufwand |
| B16 | Gezahlte Umsatzsteuer | Umsatzsteuer-Zahlung FA | 1780 | 1780 | Aufwand |
| B17 | Vorsteuererstattung | Vorsteuererstattung FA | 1570 | 1570 | Erlös |
| B18 | Sonstige Betriebsausgaben, Investitionen | Sonstige Betriebsausgaben | 4980 | 6880 | Aufwand |
| | | Anlagevermögen (Kauf) | 0400 | 0400 | Anlage |

---

## Tabelle C – Absetzungsbeträge (persönliche Abzüge)

| EKS-Feld | Bezeichnung (EKS) | Kategorie(n) | SKR03 | SKR04 | Kontenart |
|----------|-------------------|--------------|-------|-------|-----------|
| C1 | Steuern vom Einkommen | Einkommensteuer-Vorauszahlung | 1890 | 2100 | Privat |
| | | Gewerbesteuer | 7600 | 7610 | Aufwand |
| C2 | Krankenversicherung | Krankenversicherung (Pflicht) | 1890 | 2100 | Privat |
| C3 | Pflegeversicherung | Pflegeversicherung (Pflicht) | 1890 | 2100 | Privat |
| C4 | Rentenversicherung | Rentenversicherung (freiwillig) | 1890 | 2100 | Privat |
| C5 | Riester-Rente | Riester-Beiträge | 1890 | 2100 | Privat |
| C6 | Sonstige Absetzungen | Sonstige Absetzungen | 1890 | 2100 | Privat |

---

## Hinweise

**Fehlende Felder B2 und B13:**
- B2 (Wareneinsatz ohne Vorsteuer) – nicht separat abgebildet; wird ggf. über B1 gedeckt
- B13 (Abschreibungen) – werden im EÜR berechnet, nicht direkt als Buchungsposition gebucht

**Kontenart „Privat":**
Tabelle-C-Kategorien und Privatentnahme/-einlage verwenden SKR03 1890 / SKR04 2100 als
Sammelkonto für private Zahlungen, die über das Geschäftskonto laufen. Die genaue Zuordnung
wird durch den Kategorie-Namen und das `eks_kategorie`-Feld gesteuert.

**Mehrere Kategorien pro EKS-Feld:**
Alle Buchungen mit identischem `eks_kategorie`-Wert werden für das jeweilige Feld aufsummiert.
Neue benutzerdefinierte Kategorien können ebenfalls mit einem `eks_kategorie`-Wert versehen werden.
