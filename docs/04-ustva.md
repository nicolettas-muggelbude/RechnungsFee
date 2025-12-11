## **Kategorie 6: Umsatzsteuer-Voranmeldung (UStVA)**

### **6.1 Strategie: Hybrid-Ansatz** ✅

**Entscheidung:** Stufenweise Entwicklung

#### **Version 1.0 (MVP): Zahlen vorbereiten** 📊

**Funktionsweise:**
- Software berechnet alle UStVA-Kennziffern aus Buchungen
- Zeigt Übersicht mit allen Werten
- User trägt Zahlen manuell ins ELSTER-Portal ein
- Kein ELSTER-Zertifikat erforderlich

**Vorteile für MVP:**
- ✅ Schnell entwickelbar (nur Berechnung, kein ELSTER-API)
- ✅ Kein rechtlicher Overhead (User submits selbst)
- ✅ Kein Zertifikats-Management
- ✅ User behält Kontrolle über Übermittlung
- ✅ Weniger Komplexität für Version 1.0

**Ausgabe:**
```
┌─────────────────────────────────────────────────┐
│ Umsatzsteuer-Voranmeldung Dezember 2025        │
├─────────────────────────────────────────────────┤
│                                                 │
│ Zeitraum: Dezember 2025 (monatlich)           │
│ Steuernummer: 12/345/67890                     │
│                                                 │
│ UMSÄTZE                                         │
│ ├─ Kz. 81  Umsätze 19% USt      15.890,00 €   │
│ ├─ Kz. 83  → Umsatzsteuer 19%    3.019,10 €   │
│ ├─ Kz. 86  Umsätze 7% USt        2.140,00 €   │
│ ├─ Kz. 88  → Umsatzsteuer 7%       149,80 €   │
│ └─ Kz. 35  § 13b UStG (Rev.Ch.)        0,00 € │
│                                                 │
│ VORSTEUER                                       │
│ ├─ Kz. 66  Vorsteuer abzugsfähig 1.284,50 €   │
│ └─ Kz. 61  § 13b UStG Vorsteuer        0,00 € │
│                                                 │
│ ─────────────────────────────────────────────── │
│ Umsatzsteuer-Vorauszahlung (Soll):             │
│                                   2.884,40 €   │
│ ─────────────────────────────────────────────── │
│                                                 │
│ [ PDF drucken ]  [ In ELSTER eintragen ]       │
└─────────────────────────────────────────────────┘
```

**User-Workflow:**
```
1. RechnungsFee öffnen
   → Menü: "UStVA erstellen"

2. Zeitraum wählen
   → Dezember 2025

3. Berechnung prüfen
   → Alle Kennziffern werden automatisch aus Buchungen berechnet
   → Preview zeigt Aufschlüsselung

4. PDF drucken/speichern
   → Zum Nachschlagen/Dokumentation

5. ELSTER-Portal öffnen
   → https://www.elster.de einloggen

6. Zahlen manuell eintragen
   → Kz. 81: 15890,00
   → Kz. 83: 3019,10
   → etc.

7. In ELSTER abschicken
   → User übernimmt Verantwortung
```

---

#### **Version 2.0 (später): ELSTER-Integration** 🤖

**Funktionsweise:**
- Software erstellt ELSTER-XML
- Direkte Übermittlung ans Finanzamt
- ELSTER-Zertifikat erforderlich

**Zusätzliche Features:**
- ✅ Ein-Klick-Übermittlung
- ✅ Automatische XML-Generierung
- ✅ ELSTER-Empfangsbestätigung
- ✅ Status-Tracking (eingereicht, bestätigt, abgelehnt)

**Workflow:**
```
1. RechnungsFee öffnen
   → UStVA erstellen

2. Zeitraum wählen
   → Dezember 2025

3. Berechnung prüfen
   → Preview

4. [ An ELSTER übermitteln ]  ← Ein Klick!
   → ELSTER-Zertifikat eingeben
   → XML generieren + senden
   → Fertig!
```

**Anforderungen für v2.0:**
- ELSTER-API-Integration (ERiC SDK)
- Zertifikats-Management
- XML-Generierung (ELSTER-Format)
- Fehlerbehandlung (Ablehnung, Nachforderung)

---

### **6.2 Berechnung der Kennziffern**

**Wichtigste UStVA-Kennziffern:**

#### **Umsätze (steuerpflichtig):**

| Kz. | Beschreibung | Quelle | Berechnung |
|-----|--------------|--------|------------|
| **81** | Umsätze 19% USt | Ausgangsrechnungen (Inland) | Summe Netto (USt-Satz 19%) |
| **83** | Umsatzsteuer 19% | Auto-berechnet | Kz. 81 × 0,19 |
| **86** | Umsätze 7% USt | Ausgangsrechnungen (Inland) | Summe Netto (USt-Satz 7%) |
| **88** | Umsatzsteuer 7% | Auto-berechnet | Kz. 86 × 0,07 |
| **41** | Innergemeinschaftliche Lieferungen | Ausgangsrechnungen (EU) | Summe Netto (0% USt, § 4 Nr. 1b UStG) |

#### **Innergemeinschaftlicher Erwerb (EU-Einkäufe):**

| Kz. | Beschreibung | Quelle | Berechnung |
|-----|--------------|--------|------------|
| **89** | Innergemeinschaftlicher Erwerb | Eingangsrechnungen (EU) | Summe Netto (0% von EU-Lieferant) |
| **93** | Umsatzsteuer aus ig. Erwerb | Auto-berechnet | Kz. 89 × 0,19 (Reverse Charge) |
| **61** | Vorsteuer aus ig. Erwerb | Auto-berechnet | = Kz. 93 (abzugsfähig) |

**Wichtig:** Kz. 93 und Kz. 61 gleichen sich aus (zahlen + abziehen) → Netto-Effekt: 0 €

#### **Vorsteuer (abzugsfähig):**

| Kz. | Beschreibung | Quelle | Berechnung |
|-----|--------------|--------|------------|
| **66** | Vorsteuer Inland | Eingangsrechnungen (DE) | Summe USt-Betrag (abzugsfähig) |
| **61** | Vorsteuer aus ig. Erwerb | Eingangsrechnungen (EU) | = Kz. 93 (siehe oben) |

#### **Zahllast/Erstattung:**

| Kz. | Beschreibung | Berechnung |
|-----|--------------|------------|
| **83** | Summe Umsatzsteuer | Kz. 83 + Kz. 88 + ... |
| **66** | Summe Vorsteuer | Kz. 66 + Kz. 61 |
| **Zahllast** | **Vorauszahlung (Soll)** | **Kz. 83 + Kz. 93 - Kz. 66 - Kz. 61** |

---

### **6.2.1 Innergemeinschaftlicher Handel (EU)** 🇪🇺

**Entscheidung:** Im MVP enthalten (wichtig für EU-Geschäft)

---

#### **Was ist innergemeinschaftlicher Handel?**

**Handel zwischen EU-Mitgliedsstaaten**, z.B.:
- Deutschland ↔ Belgien
- Deutschland ↔ Frankreich
- Deutschland ↔ Niederlande
- etc. (alle 27 EU-Länder)

**Besonderheit:** Reverse-Charge-Verfahren (§ 13b UStG, § 4 Nr. 1b UStG)

---

#### **Szenario 1: Einkauf aus EU-Land (Innergemeinschaftlicher Erwerb)**

**Beispiel: Du kaufst Ware aus Belgien (1.000 €)**

```
Belgischer Lieferant               Du (Deutschland)
───────────────────                ────────────────
Rechnung: 1.000 €
+ 0% MwSt (!)                      Du MUSST deutsche USt berechnen:
= 1.000 € Brutto
                                   Kz. 89: 1.000 € (Erwerb)
Lieferant berechnet 0%,            Kz. 93: 190 € (19% USt darauf)
weil du deutsche                   Kz. 61: 190 € (Vorsteuer abziehbar)
USt-IdNr. hast
                                   Netto-Effekt: 0 € (93 - 61 = 0)
```

**Voraussetzungen:**
1. ✅ Du hast gültige **deutsche USt-IdNr.** (DE123456789)
2. ✅ Lieferant hat gültige **belgische USt-IdNr.** (BE0123456789)
3. ✅ Ware wird physisch nach Deutschland geliefert
4. ❌ Du bist **nicht** Kleinunternehmer (§19 UStG)

**Grenzwert:**
- **Unter 12.500 € pro Jahr:** Optional (kannst auch belgische MwSt zahlen)
- **Über 12.500 € pro Jahr:** Pflicht zum Reverse Charge

**UStVA:**
- Kz. 89: 1.000 € (Bemessungsgrundlage)
- Kz. 93: 190 € (Steuer zahlen)
- Kz. 61: 190 € (Vorsteuer abziehen)
- Zahllast: +190 € - 190 € = **0 €** ✅

---

#### **Szenario 2: Verkauf in EU-Land (Innergemeinschaftliche Lieferung)**

**Fall A: B2B - Kunde ist Unternehmer (mit USt-IdNr.)**

**Beispiel: Du verkaufst an belgischen Kunden (1.000 €)**

```
Du (Deutschland)                   Belgischer Kunde (Unternehmer)
────────────────                   ─────────────────────────────
Rechnung: 1.000 €
+ 0% USt (!)                       Kunde MUSS belgische MwSt berechnen:
= 1.000 € Brutto                   → 1.000 € × 21% = 210 € (BE-MwSt)
                                   → Gleichzeitig 210 € Vorsteuer
Steuerfreie Lieferung
§ 4 Nr. 1b UStG                    Netto-Effekt beim Kunden: 0 €
```

**Voraussetzungen (KRITISCH!):**

1. ✅ **Kunde hat gültige belgische USt-IdNr.** (BE0123456789)
2. ✅ **USt-IdNr. validiert** über BZSt-Webservice
3. ✅ **Ware wird physisch nach Belgien geliefert**
4. ✅ **Gelangensbestätigung** vorhanden (Nachweis!)

**OHNE gültige USt-IdNr.:**
- ❌ Keine steuerfreie Lieferung!
- ✅ Deutsche USt berechnen (19%)

**UStVA:**
- Kz. 41: 1.000 € (innergemeinschaftliche Lieferung)
- Keine Umsatzsteuer (0%)

**Grenzwert:**
- ❌ **Kein Grenzwert** für B2B-Verkäufe
- Immer 0% bei gültiger USt-IdNr.

---

**Fall B: B2C - Kunde ist Privatperson (ohne USt-IdNr.)**

```
Du (Deutschland)                   Belgischer Privatkunde
────────────────                   ──────────────────────

Bis 10.000 € Jahresumsatz (EU):
→ Deutsche USt (19%)

Ab 10.000 € Jahresumsatz (EU):
→ Belgische MwSt (21%)             Du musst dich in Belgien
→ Registrierung in BE nötig!       registrieren!
```

**Grenzwerte (B2C):**
- **Unter 10.000 € EU-weit pro Jahr:** Deutsche USt
- **Über 10.000 € EU-weit:** Zielland-MwSt + Registrierung
- **Alternative:** OSS-Verfahren (One-Stop-Shop)

---

#### **Pflichten bei EU-Handel**

**1. USt-IdNr.-Validierung (PFLICHT vor jeder Lieferung!)**

```python
def validate_ust_idnr(ust_idnr, land):
    """
    Validiert USt-IdNr. über BZSt-Webservice

    API: https://evatr.bff-online.de/eVatR/xmlrpc/
    """
    # 1. Format prüfen
    if not re.match(r'^BE[0-9]{10}$', ust_idnr):
        return False, "Ungültiges Format"

    # 2. BZSt-API anfragen
    response = bzst_api.validate(
        ust_idnr=ust_idnr,
        eigene_ust_idnr='DE123456789',
        firmenname='Musterfirma',
        ort='Musterstadt'
    )

    # 3. Ergebnis speichern (Nachweispflicht!)
    save_validation_result(
        ust_idnr=ust_idnr,
        datum=heute(),
        ergebnis=response.gueltig,
        fehlercode=response.fehlercode
    )

    return response.gueltig, response.fehlercode
```

**UI-Workflow:**
```
Ausgangsrechnung erstellen
│
├─ Land: [Belgien ▼]
├─ Kunde: Belgischer Kunde GmbH
├─ USt-IdNr: [BE0123456789]  [ Validieren ]
│                             ↓
│                          ✅ Gültig! (BZSt bestätigt)
│                          → 0% USt wird berechnet
│
└─ Rechnung speichern
```

**WICHTIG:** Validation-Ergebnis **muss gespeichert** werden (Nachweispflicht bei Betriebsprüfung!)

---

**2. Gelangensbestätigung (Nachweis der Lieferung)**

**Was ist das?**
- Nachweis, dass Ware tatsächlich ins EU-Ausland geliefert wurde
- Ohne Nachweis: Finanzamt kann 0% USt ablehnen!

**Mögliche Nachweise:**
1. Spediteur-Bescheinigung (CMR-Frachtbrief)
2. Unterschriebener Lieferschein
3. Tracking-Nummer (DHL, UPS, FedEx)
4. Empfangsbestätigung des Kunden

**RechnungsFee:**
```
Rechnung bearbeiten
│
├─ Status: Versendet
├─ Lieferdatum: 15.12.2025
├─ Nachweis: [📎 CMR-Frachtbrief.pdf]
│            [📎 Tracking-DHL-123456.pdf]
│
└─ Speichern
```

---

**3. Zusammenfassende Meldung (ZM)**

**Was ist das?**
- Meldung an BZSt (Bundeszentralamt für Steuern)
- Alle innergemeinschaftlichen Lieferungen
- **Pflicht** bei jeder ig. Lieferung!

**Fristen:**
- **Monatlich:** Bei > 50.000 € ig. Lieferungen pro Jahr
- **Quartalsweise:** Bei < 50.000 €
- **Frist:** 25. des Folgemonats

**Inhalt:**

```xml
<!-- ZM Januar 2026 -->
<ZM>
  <Meldezeitraum>2026-01</Meldezeitraum>
  <Lieferungen>
    <Lieferung>
      <Land>BE</Land>
      <UStIdNr>BE0123456789</UStIdNr>
      <Betrag>1000.00</Betrag>  <!-- Netto -->
    </Lieferung>
    <Lieferung>
      <Land>FR</Land>
      <UStIdNr>FR12345678901</UStIdNr>
      <Betrag>2500.00</Betrag>
    </Lieferung>
  </Lieferungen>
</ZM>
```

**RechnungsFee-Export:**
```python
def export_zm(zeitraum):
    """
    Erstellt Zusammenfassende Meldung (XML)
    """
    lieferungen = get_ig_lieferungen(zeitraum)

    # Nach Land + USt-IdNr gruppieren
    grouped = group_by(lieferungen, ['land', 'ust_idnr'])

    xml = create_zm_xml(
        zeitraum=zeitraum,
        lieferungen=grouped
    )

    return xml  # Hochladen auf ELSTER-Portal
```

**UI:**
```
┌─────────────────────────────────────────┐
│ Zusammenfassende Meldung (ZM)          │
├─────────────────────────────────────────┤
│ Zeitraum: Januar 2026                  │
│                                         │
│ Belgien (BE):                           │
│ └─ BE0123456789: 1.000,00 €            │
│                                         │
│ Frankreich (FR):                        │
│ └─ FR12345678901: 2.500,00 €           │
│                                         │
│ Gesamt: 3.500,00 €                     │
│                                         │
│ [ XML exportieren ]  [ An BZSt ]       │
└─────────────────────────────────────────┘
```

---

#### **Datenbank-Erweiterungen**

```sql
-- Rechnungen (erweitert für EU)
CREATE TABLE rechnungen (
    id INTEGER PRIMARY KEY,
    typ TEXT,  -- 'eingangsrechnung', 'ausgangsrechnung'

    -- NEU: EU-Felder
    land TEXT DEFAULT 'DE',  -- ISO 3166-1 Alpha-2
    ist_eu_lieferung BOOLEAN DEFAULT 0,
    ist_eu_erwerb BOOLEAN DEFAULT 0,
    kunde_ust_idnr TEXT,  -- z.B. BE0123456789

    -- NEU: Validierung
    ust_idnr_validiert BOOLEAN DEFAULT 0,
    ust_idnr_validierung_datum DATE,
    ust_idnr_validierung_ergebnis TEXT,

    -- NEU: Gelangensbestätigung
    gelangensbestaetigung_vorhanden BOOLEAN DEFAULT 0,
    gelangensbestaetigung_datei TEXT,  -- Pfad zu PDF/Scan

    netto_betrag DECIMAL,
    umsatzsteuer_satz DECIMAL,
    umsatzsteuer_betrag DECIMAL,
    brutto_betrag DECIMAL
);

-- ZM-Meldungen
CREATE TABLE zm_meldungen (
    id INTEGER PRIMARY KEY,
    zeitraum TEXT NOT NULL,  -- '2026-01'
    erstellungsdatum TIMESTAMP,
    status TEXT,  -- 'entwurf', 'gesendet', 'bestätigt'
    xml_datei TEXT
);

-- EU-Länder-Stammdaten
CREATE TABLE eu_laender (
    code TEXT PRIMARY KEY,  -- 'BE'
    name TEXT,  -- 'Belgien'
    mwst_satz_standard DECIMAL,  -- 21.0
    mwst_satz_reduziert DECIMAL,  -- 6.0
    ust_idnr_format TEXT  -- '^BE[0-9]{10}$'
);
```

---

#### **Kleinunternehmer (§19 UStG) - Einschränkungen**

**Problem:** Kleinunternehmer haben **keine USt-IdNr.**

**Folgen:**

```
Einkauf aus EU:
❌ Kein Reverse Charge möglich
✅ Lieferant berechnet EU-MwSt (21% BE)
❌ Keine Vorsteuer abziehbar

Verkauf in EU:
❌ Kein 0% USt möglich (keine USt-IdNr.)
✅ Wie Inlandsverkauf (0% nach §19 UStG)
⚠️ Kunde muss ggf. Import-MwSt zahlen
```

**RechnungsFee-Verhalten:**
- EU-Felder ausgegraut bei Kleinunternehmer
- Warnung: "Als Kleinunternehmer kein Reverse Charge möglich"

---

#### **MVP-Umfang EU-Handel**

**Was im MVP enthalten ist:**

✅ **Rechnungen:**
- Länder-Auswahl (27 EU-Länder)
- USt-IdNr.-Feld für Kunden/Lieferanten
- 0% USt bei ig. Lieferung/Erwerb
- Reverse-Charge-Vermerk auf Rechnung

✅ **USt-IdNr.-Validierung:**
- BZSt-API-Integration
- Validation-Ergebnis speichern
- UI-Feedback (gültig/ungültig)

✅ **UStVA:**
- Kz. 41: Innergemeinschaftliche Lieferungen
- Kz. 89: Innergemeinschaftlicher Erwerb
- Kz. 93: USt aus ig. Erwerb
- Kz. 61: Vorsteuer aus ig. Erwerb

✅ **ZM-Export:**
- XML-Generierung
- Nach Land/USt-IdNr gruppiert
- Export für ELSTER-Portal

✅ **Gelangensbestätigung:**
- Datei-Upload (PDF/Scan)
- Tracking-Nummer speichern

**Nicht im MVP (später):**
- ❌ OSS-Verfahren (B2C > 10.000 €)
- ❌ Automatische ELSTER-Übermittlung (ZM)
- ❌ Drittlands-Handel (Schweiz, UK, etc.)

---

#### **Validierung & Abhängigkeiten** ⚠️ **KRITISCH**

**Problem:** EU-Handel hat viele Voraussetzungen - ohne Validierung → Fehler bei Betriebsprüfung!

---

##### **Abhängigkeiten-Checkliste:**

**1. Voraussetzung: Eigene USt-IdNr. vorhanden**

```
Ohne eigene USt-IdNr.:
❌ Kein EU-Handel möglich
❌ Kein Reverse Charge
❌ Keine innergemeinschaftliche Lieferung

Konsequenz:
→ EU-Funktionen müssen gesperrt sein
→ Setup-Wizard muss abfragen
```

**Validierung:**
```python
def can_use_eu_trade():
    """
    Prüft, ob User EU-Handel nutzen kann
    """
    user = get_user_settings()

    # 1. Hat User eigene USt-IdNr.?
    if not user.ust_idnr:
        return False, "Keine USt-IdNr. hinterlegt"

    # 2. Format validieren (DE + 9 Ziffern)
    if not re.match(r'^DE[0-9]{9}$', user.ust_idnr):
        return False, "USt-IdNr. hat ungültiges Format"

    # 3. Kleinunternehmer?
    if user.ist_kleinunternehmer:
        return False, "Kleinunternehmer können keinen EU-Handel nutzen"

    # 4. USt-IdNr. bei BZSt bestätigt?
    if not user.ust_idnr_bestaetigt:
        return False, "USt-IdNr. noch nicht vom BZSt bestätigt"

    return True, "OK"
```

**UI-Verhalten:**
```
Wenn can_use_eu_trade() == False:
┌─────────────────────────────────────────┐
│ Ausgangsrechnung erstellen             │
├─────────────────────────────────────────┤
│ Kunde: [Max Mustermann ▼]             │
│ Land:  [Deutschland ▼]                 │
│        [Belgien] (ausgegraut)          │
│                                         │
│ ⚠️ EU-Länder nicht verfügbar            │
│    Grund: Keine USt-IdNr. hinterlegt   │
│    → Einstellungen > Stammdaten         │
└─────────────────────────────────────────┘
```

---

**2. Voraussetzung: Kunden-USt-IdNr. validiert**

```
Vor jeder ig. Lieferung MUSS geprüft werden:
✅ Kunde hat USt-IdNr. angegeben
✅ Format ist korrekt (z.B. BE0123456789)
✅ BZSt-Bestätigung liegt vor (validiert!)
✅ Nicht älter als 1 Jahr (Empfehlung)
```

**Validierung beim Rechnung-Erstellen:**
```python
def validate_eu_invoice(rechnung):
    """
    Prüft Rechnung vor dem Speichern
    """
    errors = []

    if rechnung.land != 'DE':
        # 1. USt-IdNr. vorhanden?
        if not rechnung.kunde_ust_idnr:
            errors.append(
                "Für EU-Lieferungen ist die USt-IdNr. des Kunden PFLICHT. "
                "Ohne gültige USt-IdNr. muss deutsche USt berechnet werden."
            )

        # 2. USt-IdNr. validiert?
        if rechnung.kunde_ust_idnr and not rechnung.ust_idnr_validiert:
            errors.append(
                "USt-IdNr. muss über BZSt validiert werden. "
                "Klicken Sie auf 'Validieren'."
            )

        # 3. Validation nicht älter als 1 Jahr?
        if rechnung.ust_idnr_validierung_datum:
            age = heute() - rechnung.ust_idnr_validierung_datum
            if age.days > 365:
                errors.append(
                    "USt-IdNr.-Validierung ist älter als 1 Jahr. "
                    "Bitte neu validieren."
                )

        # 4. Wenn 0% USt → Validierung PFLICHT
        if rechnung.umsatzsteuer_satz == 0 and not rechnung.ust_idnr_validiert:
            errors.append(
                "0% USt (steuerfreie ig. Lieferung) nur mit validierter USt-IdNr.!"
            )

    return errors
```

**UI-Blockierung:**
```
[ Rechnung speichern ]
        ↓
      FEHLER!

┌─────────────────────────────────────────┐
│ ❌ Rechnung kann nicht gespeichert      │
│    werden                               │
├─────────────────────────────────────────┤
│ • USt-IdNr. des Kunden fehlt            │
│ • USt-IdNr. nicht validiert             │
│                                         │
│ Bitte ergänze die USt-IdNr. und        │
│ validiere diese über BZSt.             │
│                                         │
│ [ Stammdaten öffnen ]  [ Abbrechen ]   │
└─────────────────────────────────────────┘
```

---

**3. Voraussetzung: Gelangensbestätigung (empfohlen)**

```
Ohne Gelangensbestätigung:
⚠️ Finanzamt kann 0% USt ablehnen
⚠️ Nachzahlung + Zinsen möglich
```

**Validierung (Warnung, nicht Fehler):**
```python
def warn_missing_gelangensbestaetigung(rechnung):
    """
    Warnt bei fehlender Gelangensbestätigung
    """
    if rechnung.ist_eu_lieferung and not rechnung.gelangensbestaetigung_vorhanden:
        return Warning(
            "Gelangensbestätigung fehlt! "
            "Laden Sie einen Nachweis hoch (CMR, Tracking, Lieferschein). "
            "Ohne Nachweis kann das Finanzamt die steuerfreie Lieferung ablehnen."
        )
```

**UI-Warnung:**
```
[ Rechnung speichern ]
        ↓

┌─────────────────────────────────────────┐
│ ⚠️ Gelangensbestätigung fehlt            │
├─────────────────────────────────────────┤
│ Diese Rechnung ist eine innergemein-    │
│ schaftliche Lieferung (0% USt).         │
│                                         │
│ WICHTIG: Laden Sie einen Nachweis hoch, │
│ dass die Ware nach Belgien geliefert    │
│ wurde (CMR, DHL-Tracking, etc.).        │
│                                         │
│ Ohne Nachweis:                          │
│ → Finanzamt kann 0% USt ablehnen        │
│ → Nachzahlung 19% USt + Zinsen          │
│                                         │
│ [ Jetzt hochladen ]  [ Später ]         │
└─────────────────────────────────────────┘
```

---

##### **Integration im Setup-Wizard** 🧙

**Schritt 1: Grunddaten (erweitert)**

```
┌─────────────────────────────────────────┐
│ RechnungsFee - Ersteinrichtung       │
│ Schritt 1/5: Grunddaten                │
├─────────────────────────────────────────┤
│                                         │
│ Firmenname:  [Musterfirma GmbH]        │
│ Straße:      [Musterstr. 1]            │
│ PLZ/Ort:     [12345] [Musterstadt]     │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Umsatzsteuer                        │ │
│ ├─────────────────────────────────────┤ │
│ │ ○ Kleinunternehmer (§19 UStG)       │ │
│ │   → Keine USt, kein EU-Handel       │ │
│ │                                     │ │
│ │ ● Regelbesteuert                    │ │
│ │   USt-IdNr: [DE123456789]          │ │
│ │   [ BZSt validieren ] ✅ Gültig     │ │
│ │                                     │ │
│ │   ☑ Ich plane EU-Handel             │ │
│ │     (innergemeinschaftliche         │ │
│ │      Lieferungen/Erwerbe)           │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ [ Zurück ]              [ Weiter ]     │
└─────────────────────────────────────────┘
```

**Logik:**
```python
def setup_wizard_step1_validate(data):
    if data.ist_kleinunternehmer:
        # Kleinunternehmer: EU-Handel deaktivieren
        data.eu_handel_aktiv = False
        return True

    if data.plant_eu_handel:
        # Regelbesteuert + EU-Handel:
        if not data.ust_idnr:
            return Error("Für EU-Handel ist USt-IdNr. Pflicht")

        if not validate_ust_idnr_format(data.ust_idnr):
            return Error("USt-IdNr. hat ungültiges Format (DE + 9 Ziffern)")

        # BZSt-Validierung durchführen
        result = bzst_validate(data.ust_idnr)
        if not result.gueltig:
            return Error(f"USt-IdNr. ungültig: {result.fehler}")

    return True
```

---

**Schritt 2: EU-Handel-Konfiguration (nur wenn aktiviert)**

```
┌─────────────────────────────────────────┐
│ RechnungsFee - Ersteinrichtung       │
│ Schritt 2/5: EU-Handel                 │
├─────────────────────────────────────────┤
│                                         │
│ Du hast EU-Handel aktiviert.           │
│ Bitte lies folgende Hinweise:          │
│                                         │
│ ✅ Voraussetzungen:                     │
│ • Gültige USt-IdNr. (DE123456789) ✅    │
│ • Regelbesteuerung (kein §19) ✅        │
│                                         │
│ ⚠️ Pflichten bei EU-Geschäften:         │
│ • Kunden-USt-IdNr. MUSS validiert sein │
│ • Gelangensbestätigung hochladen       │
│ • Zusammenfassende Meldung (ZM)        │
│   monatlich/quartalsweise an BZSt      │
│                                         │
│ 📋 In welchen Ländern handelst du?     │
│ (optional - nur zur Vorbereitung)      │
│                                         │
│ ☑ Belgien                               │
│ ☑ Niederlande                           │
│ ☐ Frankreich                            │
│ ☐ Österreich                            │
│ ☐ Weitere... [27 EU-Länder]            │
│                                         │
│ [ Zurück ]              [ Weiter ]     │
└─────────────────────────────────────────┘
```

---

##### **Integration in Stammdaten (Kategorie 8)** 📋

**Kunden-Stammdaten (erweitert):**

```
Kunde bearbeiten: Belgischer Kunde GmbH
┌─────────────────────────────────────────┐
│ Grunddaten                              │
├─────────────────────────────────────────┤
│ Firmenname: [Belgischer Kunde GmbH]    │
│ Straße:     [Rue de Example 123]       │
│ PLZ/Ort:    [1000] [Brüssel]           │
│                                         │
│ Land:       [Belgien ▼]  🇧🇪             │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Umsatzsteuer-ID (EU)                │ │
│ ├─────────────────────────────────────┤ │
│ │ USt-IdNr: [BE0123456789]            │ │
│ │           [ Validieren ]            │ │
│ │                                     │ │
│ │ Status: ✅ Gültig                    │ │
│ │ Validiert: 05.12.2025 (vor 2 Tagen)│ │
│ │ BZSt-Ergebnis: A (qualifiziert)    │ │
│ │                                     │ │
│ │ ⚠️ Wichtig:                          │ │
│ │ Ohne validierte USt-IdNr. wird      │ │
│ │ deutsche USt (19%) berechnet!       │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ [ Speichern ]  [ Abbrechen ]           │
└─────────────────────────────────────────┘
```

**Validierung beim Speichern:**
```python
def validate_kunde(kunde):
    errors = []

    if kunde.land != 'DE':
        # EU-Land: Prüfen ob USt-IdNr. nötig
        if not kunde.ust_idnr:
            errors.append({
                'feld': 'ust_idnr',
                'typ': 'warning',
                'nachricht':
                    'Für EU-Kunden empfehlen wir die Angabe der USt-IdNr. '
                    'Ohne USt-IdNr. wird deutsche USt (19%) berechnet.'
            })
        elif not kunde.ust_idnr_validiert:
            errors.append({
                'feld': 'ust_idnr',
                'typ': 'error',
                'nachricht':
                    'USt-IdNr. muss validiert werden (BZSt-Abfrage). '
                    'Klicken Sie auf "Validieren".'
            })

    return errors
```

---

##### **Validierungs-Matrix**

**Übersicht: Was muss wann geprüft werden?**

| Zeitpunkt | Prüfung | Fehler-Typ | Aktion |
|-----------|---------|------------|--------|
| **Setup-Wizard** | Eigene USt-IdNr. vorhanden | ❌ Fehler | Weiter blockiert |
| **Setup-Wizard** | USt-IdNr. Format korrekt | ❌ Fehler | Korrektur nötig |
| **Setup-Wizard** | BZSt-Validierung erfolgreich | ❌ Fehler | Eingabe prüfen |
| **Kunde speichern** | Kunden-USt-IdNr. vorhanden | ⚠️ Warnung | Weiter möglich |
| **Kunde speichern** | Kunden-USt-IdNr. validiert | ❌ Fehler | Validierung nötig |
| **Rechnung erstellen** | Kunde hat validierte USt-IdNr. | ❌ Fehler | Stammdaten öffnen |
| **Rechnung erstellen** | Gelangensbestätigung vorhanden | ⚠️ Warnung | Später hochladen |
| **Rechnung speichern** | 0% USt nur mit USt-IdNr. | ❌ Fehler | Speichern blockiert |
| **UStVA erstellen** | Kz. 41: Alle Rechnungen validiert | ⚠️ Warnung | Prüfung empfohlen |
| **ZM erstellen** | Alle Lieferungen haben USt-IdNr. | ❌ Fehler | Export blockiert |

---

##### **Fehlerbehandlung & User-Guidance**

**Szenario 1: User will EU-Rechnung erstellen, aber keine eigene USt-IdNr.**

```
User: Rechnung erstellen > Land: Belgien
       ↓
System: STOP!

┌─────────────────────────────────────────┐
│ ⚠️ EU-Handel nicht möglich               │
├─────────────────────────────────────────┤
│ Für Geschäfte mit EU-Ländern benötigen │
│ du eine gültige deutsche USt-IdNr.     │
│                                         │
│ Du bist aktuell als Kleinunternehmer   │
│ (§19 UStG) registriert.                │
│                                         │
│ Optionen:                               │
│ • Beim Finanzamt USt-IdNr. beantragen   │
│ • Auf Regelbesteuerung umstellen        │
│                                         │
│ [ Stammdaten ändern ]  [ Abbrechen ]   │
└─────────────────────────────────────────┘
```

**Szenario 2: Kunde ohne USt-IdNr., User will 0% USt**

```
User: USt-Satz: 0% (ig. Lieferung)
       ↓
System: STOP!

┌─────────────────────────────────────────┐
│ ❌ 0% USt nicht möglich                  │
├─────────────────────────────────────────┤
│ Für steuerfreie innergemeinschaftliche │
│ Lieferungen (0% USt) ist eine validierte│
│ USt-IdNr. des Kunden PFLICHT.          │
│                                         │
│ Kunde: Belgischer Kunde GmbH           │
│ USt-IdNr: [fehlt]                      │
│                                         │
│ Optionen:                               │
│ 1. USt-IdNr. erfragen und validieren    │
│ 2. Deutsche USt (19%) berechnen         │
│                                         │
│ [ Stammdaten öffnen ]                  │
│ [ 19% USt verwenden ]  [ Abbrechen ]   │
└─────────────────────────────────────────┘
```

---

##### **Dokumentation für User** 📖

**Hilfe-Seite: "EU-Handel - Checkliste"**

```markdown
# EU-Handel: Was du benötigst

## ✅ Voraussetzungen

1. **Eigene USt-IdNr.**
   - Beim Finanzamt beantragen
   - Format: DE + 9 Ziffern (z.B. DE123456789)
   - In RechnungsFee: Einstellungen > Stammdaten

2. **Regelbesteuerung**
   - Kleinunternehmer (§19 UStG) können keinen EU-Handel nutzen
   - Umstellung beim Finanzamt beantragen

3. **Kunden-USt-IdNr.**
   - Für jeden EU-Kunden erforderlich
   - MUSS über BZSt validiert werden
   - In RechnungsFee: Kunde bearbeiten > "Validieren"

4. **Gelangensbestätigung**
   - Nachweis, dass Ware ins EU-Ausland geliefert wurde
   - CMR-Frachtbrief, DHL-Tracking, Lieferschein
   - In RechnungsFee: Rechnung > "Nachweis hochladen"

## ⚠️ Häufige Fehler

❌ "USt-IdNr. nicht validiert"
→ Lösung: Kunde öffnen > USt-IdNr. eingeben > "Validieren" klicken

❌ "0% USt nicht möglich"
→ Lösung: Kunde muss gültige USt-IdNr. haben

❌ "Gelangensbestätigung fehlt"
→ Lösung: CMR/Tracking hochladen (empfohlen, nicht Pflicht)

## 📋 Monatliche Aufgaben

- Zusammenfassende Meldung (ZM) an BZSt senden
- RechnungsFee: Berichte > ZM erstellen > XML exportieren
```

---

##### **⚠️ KRITISCHE KORREKTUR: Export-Zeit-Validierung**

**Problem mit obigem Konzept:**

```
RechnungsFee MVP hat KEINEN Kundenstamm!
────────────────────────────────────────────

User erstellt Rechnungen:
• LibreOffice-Vorlagen
• HTML-Vorlagen
• PDF/XRechnung-Import

→ KEINE Eingabemasken in RechnungsFee
→ KEINE Validierung bei Erfassung möglich
→ User könnte fehlerhafte Rechnungen erstellen
```

**Konsequenz:**
- Stammdaten-Validierung (oben) gilt erst für **Version 2.0** (mit Rechnungseditor)
- Setup-Wizard-Validierung bleibt (eigene USt-IdNr. MUSS vorhanden sein)
- **Alle anderen Validierungen müssen beim EXPORT erfolgen!**

---

##### **Export-Zeit-Validierung (MVP-Ansatz)** ✅

**Wann wird validiert?**

1. **Vor UStVA-Erstellung**
2. **Vor ZM-Erstellung**
3. **Vor DATEV-Export**

**Was passiert bei Fehlern?**
- Export wird NICHT blockiert
- Aber: **Validierungs-Report** mit Warnungen
- User muss Fehler bestätigen oder korrigieren

---

**1. UStVA-Validierung**

```python
def validate_ustva_before_export(zeitraum):
    """
    Prüft alle Rechnungen VOR UStVA-Export
    """
    warnings = []
    errors = []

    # Alle Rechnungen mit 0% USt (ig. Lieferung)
    eu_lieferungen = get_ausgangsrechnungen(
        zeitraum=zeitraum,
        umsatzsteuer_satz=0,
        land_not='DE'
    )

    for rechnung in eu_lieferungen:
        # 1. Land ist EU-Mitglied?
        if rechnung.land not in EU_LAENDER:
            errors.append({
                'rechnung': rechnung.nummer,
                'fehler': f"Land '{rechnung.land}' ist kein EU-Mitglied",
                'loesung': "0% USt nur für EU-Länder zulässig. Bitte prüfen."
            })

        # 2. Kunden-USt-IdNr. vorhanden?
        if not rechnung.kunde_ust_idnr:
            warnings.append({
                'rechnung': rechnung.nummer,
                'warnung': "Keine Kunden-USt-IdNr. auf Rechnung",
                'risiko': "Finanzamt könnte 0% USt ablehnen → 19% nachzahlen",
                'loesung': "Rechnung nachträglich korrigieren und USt-IdNr. ergänzen"
            })

        # 3. USt-IdNr.-Format plausibel?
        if rechnung.kunde_ust_idnr:
            if not validate_ust_idnr_format(rechnung.kunde_ust_idnr, rechnung.land):
                warnings.append({
                    'rechnung': rechnung.nummer,
                    'warnung': f"USt-IdNr. '{rechnung.kunde_ust_idnr}' hat ungültiges Format",
                    'format': get_expected_format(rechnung.land),
                    'loesung': "Bitte prüfen und ggf. BZSt-Validierung durchführen"
                })

        # 4. BZSt-Validierung vorhanden?
        if rechnung.kunde_ust_idnr and not rechnung.ust_idnr_validiert:
            warnings.append({
                'rechnung': rechnung.nummer,
                'warnung': "USt-IdNr. nicht über BZSt validiert",
                'risiko': "Bei Betriebsprüfung: Nachweis der Validierung erforderlich",
                'loesung': "Jetzt validieren: [USt-IdNr. prüfen]"
            })

    # Zusammenfassung
    return {
        'errors': errors,  # Kritische Fehler
        'warnings': warnings,  # Warnungen
        'kann_exportieren': len(errors) == 0
    }
```

**UI vor UStVA-Export:**

```
[ UStVA Dezember 2025 erstellen ]
        ↓
    Validierung läuft...
        ↓

┌─────────────────────────────────────────────┐
│ ⚠️ UStVA-Validierung: 5 Warnungen gefunden  │
├─────────────────────────────────────────────┤
│                                             │
│ Rechnung RE-2025-123:                       │
│ └─ ⚠️ Keine Kunden-USt-IdNr.                │
│    Risiko: Finanzamt könnte 0% USt ablehnen│
│    → Nachzahlung 19% + Zinsen              │
│    [ Rechnung korrigieren ]                │
│                                             │
│ Rechnung RE-2025-145:                       │
│ └─ ⚠️ USt-IdNr. nicht validiert             │
│    BE0123456789 (nicht geprüft)            │
│    [ Jetzt validieren ]                    │
│                                             │
│ Rechnung RE-2025-167:                       │
│ └─ ⚠️ Format ungültig                       │
│    "BE012345" (zu kurz, erwartet: 10 Ziff.)│
│    [ Rechnung korrigieren ]                │
│                                             │
│ ───────────────────────────────────────────│
│                                             │
│ ✅ Kritische Fehler: 0                      │
│ ⚠️ Warnungen: 5                             │
│                                             │
│ UStVA kann erstellt werden, aber Warnungen │
│ sollten vor Übermittlung ans Finanzamt     │
│ behoben werden.                            │
│                                             │
│ [ Warnungen ignorieren & fortfahren ]      │
│ [ Alle Rechnungen prüfen ]                 │
│ [ Abbrechen ]                              │
└─────────────────────────────────────────────┘
```

---

**2. ZM-Validierung**

```python
def validate_zm_before_export(zeitraum):
    """
    Prüft Zusammenfassende Meldung VOR Export
    """
    errors = []
    warnings = []

    # Alle innergemeinschaftlichen Lieferungen
    ig_lieferungen = get_ig_lieferungen(zeitraum)

    for lieferung in ig_lieferungen:
        # 1. USt-IdNr. MUSS vorhanden sein (ZM-Pflicht!)
        if not lieferung.kunde_ust_idnr:
            errors.append({
                'rechnung': lieferung.nummer,
                'fehler': "Keine USt-IdNr. - ZM-Export nicht möglich",
                'pflicht': "Für ZM ist USt-IdNr. PFLICHT (§18a UStG)",
                'loesung': "Rechnung korrigieren und USt-IdNr. ergänzen"
            })

        # 2. Format-Validierung
        if lieferung.kunde_ust_idnr:
            if not validate_ust_idnr_format(lieferung.kunde_ust_idnr, lieferung.land):
                errors.append({
                    'rechnung': lieferung.nummer,
                    'fehler': f"USt-IdNr. '{lieferung.kunde_ust_idnr}' ungültig",
                    'loesung': "Format prüfen und korrigieren"
                })

        # 3. BZSt-Validierung empfohlen
        if lieferung.kunde_ust_idnr and not lieferung.ust_idnr_validiert:
            warnings.append({
                'rechnung': lieferung.nummer,
                'warnung': "USt-IdNr. nicht validiert",
                'empfehlung': "Vor ZM-Übermittlung validieren"
            })

    return {
        'errors': errors,
        'warnings': warnings,
        'kann_exportieren': len(errors) == 0
    }
```

**UI vor ZM-Export:**

```
[ ZM Januar 2026 erstellen ]
        ↓

┌─────────────────────────────────────────────┐
│ ❌ ZM-Export nicht möglich                   │
├─────────────────────────────────────────────┤
│ 2 kritische Fehler gefunden:                │
│                                             │
│ Rechnung RE-2025-234:                       │
│ └─ ❌ Keine USt-IdNr. vorhanden              │
│    Ohne USt-IdNr. kann diese Lieferung     │
│    nicht in der ZM gemeldet werden.        │
│    → Rechnung aus ZM ausschließen?         │
│    [ Rechnung korrigieren ]                │
│    [ Aus ZM ausschließen ]                 │
│                                             │
│ Rechnung RE-2025-256:                       │
│ └─ ❌ USt-IdNr. ungültig: "BE012"           │
│    Format: BE + 10 Ziffern erwartet        │
│    [ Rechnung korrigieren ]                │
│                                             │
│ ───────────────────────────────────────────│
│                                             │
│ Export BLOCKIERT bis Fehler behoben sind.  │
│                                             │
│ [ Alle Fehler prüfen ]  [ Abbrechen ]      │
└─────────────────────────────────────────────┘
```

---

**3. DATEV-Export-Validierung**

```python
def validate_datev_export(zeitraum):
    """
    Prüft DATEV-Export auf Plausibilität
    """
    warnings = []

    buchungen = get_all_buchungen(zeitraum)

    for buchung in buchungen:
        # 1. Konto 8400 (ig. Lieferung) ohne USt-IdNr.?
        if buchung.konto_skr03 == '8400':  # ig. Lieferung
            if not buchung.kunde_ust_idnr:
                warnings.append({
                    'buchung': buchung.id,
                    'warnung': "Konto 8400 (ig. Lieferung) ohne USt-IdNr.",
                    'risiko': "DATEV-Berater könnte nachfragen",
                    'empfehlung': "Rechnung ergänzen oder Konto korrigieren"
                })

        # 2. 0% USt ohne Begründung?
        if buchung.umsatzsteuer_betrag == 0 and buchung.netto_betrag > 0:
            if not buchung.steuerbefreiung_grund:  # z.B. "§4 Nr. 1b UStG"
                warnings.append({
                    'buchung': buchung.id,
                    'warnung': "0% USt ohne Begründung",
                    'empfehlung': "Steuerbefreiungsgrund angeben"
                })

    return warnings
```

---

##### **Workflow: Nachträgliche Korrektur**

**Szenario: User findet Fehler nach UStVA-Validierung**

```
1. UStVA-Validierung zeigt Warnung
   "Rechnung RE-2025-123: Keine USt-IdNr."

2. User öffnet Rechnung
   → Datei: rechnung-2025-123.xml (XRechnung)
   → Oder: rechnung-2025-123.pdf + metadata.json

3. Zwei Optionen:

   Option A: In RechnungsFee korrigieren
   ┌────────────────────────────────────┐
   │ Rechnung RE-2025-123 bearbeiten   │
   ├────────────────────────────────────┤
   │ Kunde: Belgischer Kunde GmbH      │
   │ Betrag: 1.000,00 € (Netto)        │
   │ USt: 0% (ig. Lieferung)           │
   │                                    │
   │ ⚠️ USt-IdNr. fehlt!                 │
   │                                    │
   │ Nachträglich ergänzen:             │
   │ USt-IdNr: [BE0123456789]          │
   │           [ Validieren ]           │
   │                                    │
   │ [ Speichern ]                      │
   └────────────────────────────────────┘

   Option B: Original-Rechnung neu erstellen
   → LibreOffice/HTML-Vorlage anpassen
   → Neu hochladen/importieren
   → Alte Version ersetzen

4. Nach Korrektur: UStVA neu erstellen
   → Validierung erneut durchlaufen
   → Diesmal ohne Warnung ✅
```

---

##### **Validierungs-Report (Export-Zusammenfassung)**

**Vor jedem Export: Übersicht aller Probleme**

```
┌───────────────────────────────────────────────────┐
│ Validierungs-Report: Dezember 2025               │
├───────────────────────────────────────────────────┤
│                                                   │
│ ✅ Geprüfte Rechnungen: 47                        │
│ ✅ Ohne Probleme: 42                              │
│ ⚠️ Mit Warnungen: 5                               │
│ ❌ Mit Fehlern: 0                                 │
│                                                   │
│ ───────────────────────────────────────────────── │
│                                                   │
│ Warnungen (sollten behoben werden):              │
│                                                   │
│ 1. RE-2025-123 (Belgien, 1.000 €)                │
│    └─ ⚠️ Keine USt-IdNr.                          │
│       [ Korrigieren ] [ Details ]                │
│                                                   │
│ 2. RE-2025-145 (Frankreich, 2.500 €)             │
│    └─ ⚠️ USt-IdNr. nicht validiert                │
│       [ Validieren ] [ Details ]                 │
│                                                   │
│ 3. RE-2025-167 (Niederlande, 800 €)              │
│    └─ ⚠️ Gelangensbestätigung fehlt               │
│       [ Hochladen ] [ Details ]                  │
│                                                   │
│ 4. RE-2025-189 (Österreich, 450 €)               │
│    └─ ⚠️ USt-IdNr.-Format unklar                  │
│       [ Prüfen ] [ Details ]                     │
│                                                   │
│ 5. RE-2025-201 (Italien, 1.200 €)                │
│    └─ ⚠️ Validierung älter als 1 Jahr             │
│       [ Neu validieren ] [ Details ]             │
│                                                   │
│ ───────────────────────────────────────────────── │
│                                                   │
│ Empfehlung:                                      │
│ Behebe die Warnungen vor UStVA-Abgabe,          │
│ um Probleme bei Betriebsprüfung zu vermeiden.   │
│                                                   │
│ [ Alle korrigieren ]  [ Report drucken ]         │
│ [ Warnungen ignorieren & exportieren ]           │
└───────────────────────────────────────────────────┘
```

---

##### **Unterschied: Fehler vs. Warnung**

| | Fehler ❌ | Warnung ⚠️ |
|---|---|---|
| **Export** | Blockiert | Möglich |
| **Risiko** | Hoch (rechtlich falsch) | Mittel (Betriebsprüfung) |
| **Beispiel** | ZM ohne USt-IdNr. | UStVA mit unvalidierter USt-IdNr. |
| **User-Aktion** | MUSS behoben werden | SOLLTE behoben werden |
| **UI** | Export-Button gesperrt | Export mit Bestätigung |

---

**Status:** ✅ Export-Zeit-Validierung definiert - UStVA, ZM, DATEV mit Validierungs-Report und nachträglicher Korrektur

**Status (alt):** ~~Stammdaten-Validierung~~ → Verschoben auf Version 2.0 (mit Rechnungseditor)

---

### **6.3 Implementierung (MVP)**

**Datenquellen:**

```python
def calculate_ustva(zeitraum):
    """
    Berechnet UStVA-Kennziffern aus Buchungen

    Zeitraum: 'monat' oder 'quartal'
    """
    # 1. Ausgangsrechnungen (Umsätze)
    ausgangsrechnungen = get_ausgangsrechnungen(
        zeitraum=zeitraum,
        status='bezahlt'  # Nur bezahlte (Ist-Versteuerung)
    )

    kz_81 = sum(
        r.netto_betrag for r in ausgangsrechnungen
        if r.umsatzsteuer_satz == 19.0
    )
    kz_83 = kz_81 * 0.19

    kz_86 = sum(
        r.netto_betrag for r in ausgangsrechnungen
        if r.umsatzsteuer_satz == 7.0
    )
    kz_88 = kz_86 * 0.07

    # 2. Eingangsrechnungen (Vorsteuer)
    eingangsrechnungen = get_eingangsrechnungen(
        zeitraum=zeitraum,
        vorsteuer_abzugsfaehig=True
    )

    kz_66 = sum(r.umsatzsteuer_betrag for r in eingangsrechnungen)

    # 3. Kassenbuch-Einnahmen (falls Bar)
    kassenbuch_einnahmen = get_kassenbuch(
        zeitraum=zeitraum,
        art='einnahme'
    )

    kz_81 += sum(
        k.netto_betrag for k in kassenbuch_einnahmen
        if k.ust_satz == 19.0
    )
    # ... analog für 7%

    # 4. Zahllast berechnen
    umsatzsteuer_gesamt = kz_83 + kz_88
    vorsteuer_gesamt = kz_66
    zahllast = umsatzsteuer_gesamt - vorsteuer_gesamt

    return {
        'kz_81': kz_81,
        'kz_83': kz_83,
        'kz_86': kz_86,
        'kz_88': kz_88,
        'kz_66': kz_66,
        'zahllast': zahllast,
        'zeitraum': zeitraum
    }
```

**PDF-Export:**

```python
def export_ustva_pdf(ustva_data):
    """
    Erstellt PDF-Übersicht der UStVA

    Zum Ausdrucken/Dokumentieren
    """
    pdf = create_pdf('UStVA_' + ustva_data['zeitraum'] + '.pdf')

    pdf.add_header("Umsatzsteuer-Voranmeldung")
    pdf.add_text(f"Zeitraum: {ustva_data['zeitraum']}")

    pdf.add_table([
        ['Kz. 81', 'Umsätze 19%', format_currency(ustva_data['kz_81'])],
        ['Kz. 83', 'USt 19%', format_currency(ustva_data['kz_83'])],
        ['Kz. 86', 'Umsätze 7%', format_currency(ustva_data['kz_86'])],
        ['Kz. 88', 'USt 7%', format_currency(ustva_data['kz_88'])],
        ['Kz. 66', 'Vorsteuer', format_currency(ustva_data['kz_66'])],
        ['', 'Zahllast', format_currency(ustva_data['zahllast'])],
    ])

    return pdf
```

---

### **6.4 Kleinunternehmer (§19 UStG)**

**Besonderheit:** Keine UStVA erforderlich!

**Verhalten:**
- RechnungsFee erkennt: User ist Kleinunternehmer
- UStVA-Menü wird ausgeblendet/deaktiviert
- Hinweis: "Als Kleinunternehmer (§19 UStG) musst du keine UStVA abgeben"

**Optional:**
- Umsatzgrenze-Tracker:
  - Warnung bei 22.000 € Jahresumsatz
  - "Achtung: Nächstes Jahr keine Kleinunternehmerregelung mehr!"

---

### **6.5 Soll- vs. Ist-Versteuerung**

**Unterschied:**

| | Soll-Versteuerung | Ist-Versteuerung |
|---|---|---|
| **Wann USt fällig?** | Bei Rechnungsstellung | Bei Zahlungseingang |
| **Für wen?** | Alle (Standardfall) | Freiberufler, kleine Unternehmen |
| **RechnungsFee** | Alle Ausgangsrechnungen | Nur bezahlte Rechnungen |

---

#### **⚠️ WICHTIG: Ist-Versteuerung PFLICHT bei Transferleistungen**

**Grund: SGBII-Konformität**

Wenn der User **Transferleistungen** bezieht (ALG II / Bürgergeld), ist **Ist-Versteuerung zwingend erforderlich**!

**Warum?**
- **SGBII § 11:** "Einnahmen = Zufluss" (nur tatsächlich erhaltenes Geld)
- **Soll-Versteuerung** würde Rechnungsdatum zählen → Einnahme "zu früh" gemeldet
- **Ist-Versteuerung** zählt Zahlungseingang → Passt zu SGBII-Definition

**Beispiel:**

```
Szenario:
- Rechnung gestellt: 15.12.2025 (1.000 €)
- Zahlung erhalten: 10.01.2026 (1.000 €)

Soll-Versteuerung (FALSCH bei ALG II):
→ Einnahme in Dezember 2025 (Rechnungsdatum)
→ SGBII rechnet 1.000 € im Dezember an
→ Aber: Kein Geld auf dem Konto!
→ Kürzung der Leistung obwohl kein Geld da ist ❌

Ist-Versteuerung (RICHTIG bei ALG II):
→ Einnahme in Januar 2026 (Zahlungseingang)
→ SGBII rechnet 1.000 € im Januar an
→ Geld ist tatsächlich auf dem Konto
→ Korrekte Anrechnung ✅
```

**RechnungsFee-Verhalten:**

1. **Beim Ersteinrichtung:**
   ```
   Beziehst du Transferleistungen?
   (ALG II, Bürgergeld, Grundsicherung)

   ○ Nein
   ● Ja  ← User wählt "Ja"

   → Automatisch: Ist-Versteuerung wird gesetzt
   → Soll-Versteuerung wird deaktiviert/ausgegraut
   ```

2. **In Einstellungen:**
   ```
   Einstellungen > Steuern
   ┌──────────────────────────────────┐
   │ Versteuerungsart:                │
   │ ○ Soll-Versteuerung (gesperrt)  │
   │ ● Ist-Versteuerung               │
   │                                  │
   │ ⚠️ Ist-Versteuerung ist Pflicht  │
   │    bei Bezug von                 │
   │    Transferleistungen (SGBII)    │
   └──────────────────────────────────┘
   ```

3. **EKS-Export:**
   - EKS nutzt automatisch Ist-Versteuerung
   - Alle Einnahmen/Ausgaben nach Zufluss-Datum
   - Konsistent mit UStVA

**Zusammenhang mit EKS (Kategorie 3):**
- EKS = Einkommensnachweis fürs Jobcenter
- Verwendet "Zufluss-Prinzip" (= Ist-Versteuerung)
- UStVA muss dasselbe Prinzip verwenden!
- Sonst: Widersprüchliche Zahlen zwischen EKS und Steuererklärung

---

#### **Implementierung:**

```python
def get_versteuerungsart():
    """
    Ermittelt die Versteuerungsart unter Berücksichtigung von Transferleistungen
    """
    user_settings = get_user_settings()

    # ZWANG: Transferleistungen → Ist-Versteuerung
    if user_settings.bezieht_transferleistungen:
        return 'ist'  # Keine Wahl!

    # Sonst: User-Einstellung
    return user_settings.versteuerungsart  # 'ist' oder 'soll'


def get_ausgangsrechnungen_fuer_ustva(zeitraum):
    """
    Holt Ausgangsrechnungen je nach Versteuerungsart
    """
    versteuerungsart = get_versteuerungsart()

    if versteuerungsart == 'ist':
        # Ist-Versteuerung: Nur bezahlte Rechnungen
        # WICHTIG bei Transferleistungen (SGBII § 11: Zufluss-Prinzip)
        return get_ausgangsrechnungen(
            zeitraum=zeitraum,
            bezahlt=True,
            zahlungsdatum_in_zeitraum=True  # Nach Zahlungseingang!
        )
    else:
        # Soll-Versteuerung: Alle Rechnungen
        return get_ausgangsrechnungen(
            zeitraum=zeitraum,
            rechnungsdatum_in_zeitraum=True  # Nach Rechnungsdatum
        )


def validate_settings_change(field, new_value):
    """
    Verhindert ungültige Einstellungen
    """
    if field == 'versteuerungsart' and new_value == 'soll':
        user = get_user_settings()

        if user.bezieht_transferleistungen:
            raise ValidationError(
                "Soll-Versteuerung nicht möglich bei Bezug von Transferleistungen. "
                "SGBII § 11 erfordert Ist-Versteuerung (Zufluss-Prinzip)."
            )
```

**User-Einstellung (normal):**
```
Einstellungen > Steuern
┌────────────────────────────┐
│ Versteuerungsart:          │
│ ○ Soll-Versteuerung        │
│ ● Ist-Versteuerung         │
└────────────────────────────┘
```

**User-Einstellung (bei Transferleistungen):**
```
Einstellungen > Steuern
┌──────────────────────────────────────┐
│ Versteuerungsart:                    │
│ ○ Soll-Versteuerung (nicht möglich) │
│ ● Ist-Versteuerung (Pflicht)        │
│                                      │
│ ⚠️ Bei Bezug von Transferleistungen  │
│    ist Ist-Versteuerung              │
│    gesetzlich vorgeschrieben         │
│    (SGBII § 11 Zufluss-Prinzip)      │
└──────────────────────────────────────┘
```

---

### **6.6 Bürgergeld-Freibeträge (Einkommensanrechnung)**

**Für erwerbstätige Bürgergeld-Empfänger gibt es Einkommensfreibeträge:**

#### **Grundfreibetrag: 100 € brutto anrechnungsfrei**

**Zusammensetzung des Grundfreibetrags (100 €):**

1. **Versicherungsbeiträge:**
   - Kranken- und Pflegeversicherung (für nicht gesetzlich Versicherte)
   - Altersvorsorge (für Personen ohne Versicherungspflicht in gesetzlicher Rentenversicherung)

2. **Geförderte Altersvorsorge:**
   - Riester-Beiträge nach § 82 EStG
   - Bis Mindesteigenbeitrag nach § 86 EStG

3. **Werbungskosten:**
   - Mit Erzielung des Einkommens verbundene notwendige Ausgaben
   - Fahrtkosten: 0,20 €/km (bei Einkommen > 400 €, wenn Summe > 100 €)

#### **Gestaffelte Anrechnung über 100 €:**

| Bruttoeinkommen | Anrechnung | Anrechnungsfrei | Beispiel (brutto) | Anrechnungsfrei (konkret) |
|-----------------|------------|-----------------|-------------------|---------------------------|
| **0-100 €** | 0% | 100% | 80 € | 80 € |
| **101-520 €** | 80% | **20%** | 500 € | 100 € + (400 € × 20%) = **180 €** |
| **521-1000 €** | 70% | **30%** ⭐ | 800 € | 100 € + (400 € × 20%) + (280 € × 30%) = **264 €** |
| **1001-1200 €** | 90% | **10%** | 1.150 € | 100 € + (400 € × 20%) + (480 € × 30%) + (150 € × 10%) = **339 €** |
| **1001-1500 €** (mit Kind) | 90% | **10%** | 1.400 € | 100 € + (400 € × 20%) + (480 € × 30%) + (400 € × 10%) = **364 €** |
| **Über 1200/1500 €** | 100% | 0% | 1.300 € | 339 € (keine weitere Anrechnung) |

⭐ **NEU seit 2023:** Stufe 521-1000 € mit 30% anrechnungsfrei (vorher 20%)

**Grenzen:**
- **Ohne Kind:** 1.200 € Brutto
- **Mit Kind:** 1.500 € Brutto

#### **Berechnungsbeispiele:**

**Beispiel 1: Einkommen 400 €**
```
Brutto:                400,00 €
- Grundfreibetrag:    -100,00 €
- Anrechnungsfrei 20%:  -60,00 € (300 € × 20%)
= Angerechnet:         240,00 €
→ Bürgergeld wird um 240 € gekürzt
```

**Beispiel 2: Einkommen 750 € (NEU: 30% ab 521 €)**
```
Brutto:                750,00 €
- Grundfreibetrag:    -100,00 €
Verbleibend:           650,00 €

Staffelung:
  101-520 €: 420 € × 20% = 84,00 € anrechnungsfrei
  521-750 €: 230 € × 30% = 69,00 € anrechnungsfrei (NEU!)

Gesamt anrechnungsfrei: 100 + 84 + 69 = 253,00 €
= Angerechnet:                          497,00 €
→ Bürgergeld wird um 497 € gekürzt
```

**Beispiel 3: Einkommen 1.100 € (ohne Kind)**
```
Brutto:                1.100,00 €
- Grundfreibetrag:      -100,00 €
Verbleibend:          1.000,00 €

Staffelung:
  101-520 €: 420 € × 20% =  84,00 € anrechnungsfrei
  521-1000 €: 480 € × 30% = 144,00 € anrechnungsfrei (NEU!)
  1001-1100 €: 100 € × 10% =  10,00 € anrechnungsfrei

Gesamt anrechnungsfrei: 100 + 84 + 144 + 10 = 338,00 €
= Angerechnet:                                762,00 €
→ Bürgergeld wird um 762 € gekürzt
```

#### **RechnungsFee-Implementierung:**

```python
def calculate_buergergeld_anrechnung(brutto_einkommen: Decimal, hat_kind: bool = False) -> dict:
    """
    Berechnet Bürgergeld-Einkommensanrechnung (Stand 2023)

    Returns:
        {
            'brutto': Decimal,
            'grundfreibetrag': Decimal,
            'anrechnungsfrei_gesamt': Decimal,
            'angerechnet': Decimal,
            'staffelung': list  # Details der Berechnung
        }
    """
    grundfreibetrag = Decimal('100.00')

    if brutto_einkommen <= grundfreibetrag:
        return {
            'brutto': brutto_einkommen,
            'grundfreibetrag': brutto_einkommen,
            'anrechnungsfrei_gesamt': brutto_einkommen,
            'angerechnet': Decimal('0.00'),
            'staffelung': []
        }

    verbleibend = brutto_einkommen - grundfreibetrag
    anrechnungsfrei = grundfreibetrag
    staffelung = []

    # Stufe 1: 101-520 € (20% anrechnungsfrei)
    if verbleibend > 0:
        stufe1_max = Decimal('420.00')  # 520 - 100
        stufe1_betrag = min(verbleibend, stufe1_max)
        stufe1_frei = stufe1_betrag * Decimal('0.20')
        anrechnungsfrei += stufe1_frei
        staffelung.append({
            'bereich': '101-520 €',
            'betrag': stufe1_betrag,
            'prozent': 20,
            'anrechnungsfrei': stufe1_frei
        })
        verbleibend -= stufe1_betrag

    # Stufe 2: 521-1000 € (30% anrechnungsfrei) ⭐ NEU!
    if verbleibend > 0:
        stufe2_max = Decimal('480.00')  # 1000 - 520
        stufe2_betrag = min(verbleibend, stufe2_max)
        stufe2_frei = stufe2_betrag * Decimal('0.30')  # NEU: 30% statt 20%
        anrechnungsfrei += stufe2_frei
        staffelung.append({
            'bereich': '521-1000 €',
            'betrag': stufe2_betrag,
            'prozent': 30,
            'anrechnungsfrei': stufe2_frei
        })
        verbleibend -= stufe2_betrag

    # Stufe 3: 1001-1200 € bzw. 1001-1500 € (mit Kind) (10% anrechnungsfrei)
    if verbleibend > 0:
        stufe3_max = Decimal('300.00') if not hat_kind else Decimal('600.00')  # 1500 - 1000 mit Kind
        stufe3_betrag = min(verbleibend, stufe3_max)
        stufe3_frei = stufe3_betrag * Decimal('0.10')
        anrechnungsfrei += stufe3_frei
        staffelung.append({
            'bereich': f'1001-{1200 if not hat_kind else 1500} €',
            'betrag': stufe3_betrag,
            'prozent': 10,
            'anrechnungsfrei': stufe3_frei
        })
        verbleibend -= stufe3_betrag

    # Alles darüber: 100% angerechnet (0% frei)
    if verbleibend > 0:
        staffelung.append({
            'bereich': f'Über {1200 if not hat_kind else 1500} €',
            'betrag': verbleibend,
            'prozent': 0,
            'anrechnungsfrei': Decimal('0.00')
        })

    angerechnet = brutto_einkommen - anrechnungsfrei

    return {
        'brutto': brutto_einkommen,
        'grundfreibetrag': grundfreibetrag,
        'anrechnungsfrei_gesamt': anrechnungsfrei,
        'angerechnet': angerechnet,
        'staffelung': staffelung
    }
```

#### **UI-Ansicht (EKS-Export / Einkommensübersicht):**

```
┌──────────────────────────────────────────────────────────┐
│ Einkommensberechnung für Bürgergeld (Bewilligungszeitraum)│
├──────────────────────────────────────────────────────────┤
│                                                          │
│ Zeitraum: Januar - Juni 2025 (6 Monate)                 │
│                                                          │
│ EINNAHMEN:                                               │
│   Betriebseinnahmen:          4.200,00 € (monatl. Ø 700 €)│
│                                                          │
│ AUSGABEN:                                                │
│   Betriebsausgaben:          -1.800,00 €                 │
│   ────────────────────────────────────────               │
│   Gewinn/Monat (Ø):             400,00 €                 │
│                                                          │
│ ANRECHNUNG (pro Monat):                                  │
│   Bruttoeinkommen:              400,00 €                 │
│   - Grundfreibetrag:          - 100,00 €                 │
│   - Anrechnungsfrei (20%):    -  60,00 € (300 € × 20%)  │
│   ──────────────────────────────────────                 │
│   Angerechnetes Einkommen:      240,00 €                 │
│                                                          │
│ 💡 Ihr Bürgergeld wird um ca. 240 € pro Monat gekürzt   │
│                                                          │
│    [EKS-Formular exportieren]  [Details anzeigen]        │
└──────────────────────────────────────────────────────────┘
```

**Detail-Ansicht:**

```
┌──────────────────────────────────────────┐
│ Staffelung Einkommensanrechnung          │
├──────────────────────────────────────────┤
│                                          │
│ Bruttoeinkommen:      400,00 €           │
│                                          │
│ 1. Grundfreibetrag:                      │
│    0-100 €            100,00 € (100%)    │
│                                          │
│ 2. Staffelung:                           │
│    101-400 €          300,00 €           │
│    Anrechnungsfrei:    60,00 € (20%)     │
│    Angerechnet:       240,00 € (80%)     │
│                                          │
│ ────────────────────────────────────     │
│                                          │
│ Gesamt anrechnungsfrei:  160,00 €        │
│ Gesamt angerechnet:      240,00 €        │
│                                          │
│              [ Schließen ]               │
└──────────────────────────────────────────┘
```

#### **Hinweise für User:**

⚠️ **Wichtig:**
- Anrechnung erfolgt auf **Brutto-Einkommen** (Einnahmen - Ausgaben)
- Werbungskosten sind bereits im Grundfreibetrag (100 €) enthalten
- Fahrtkosten können zusätzlich abgesetzt werden (0,20 €/km bei Einkommen > 400 €)
- Bei schwankendem Einkommen: Durchschnitt des Bewilligungszeitraums

💡 **Tipp:**
- Einkommen unter 100 €/Monat: Keine Anrechnung
- Einkommen 100-520 €: 20% anrechnungsfrei zusätzlich
- Einkommen 521-1000 €: **30% anrechnungsfrei** (NEU seit 2023!)
- Mit Kind: Höhere Grenze (1.500 € statt 1.200 €)

---

**Status:** ✅ Kategorie 6.1-6.6 definiert - Hybrid-Ansatz (MVP: Zahlen vorbereiten, v2.0: ELSTER-Integration), Berechnung, Kleinunternehmer, Ist/Soll-Versteuerung, SGBII-Konformität (Ist-Versteuerung Pflicht bei Transferleistungen).

---

## **🔍 Export-Anforderungen für Steuerberater-Software**

### **AGENDA - Export-Kompatibilität**

**Was AGENDA importieren kann (= was RechnungsFee exportieren muss):**

1. **DATEV-Format**
   - AGENDA kann DATEV-Daten importieren
   - ✅ RechnungsFee hat bereits DATEV-Export (Kategorie 2)

2. **Belegbilder-Export (PDF + XML)**
   - **AGENDA-Anforderung:** PDF und XML müssen denselben Dateinamen haben
   - **Format:** `rechnung-123.pdf` + `rechnung-123.xml`
   - **Bulk-Export:** Gezippte Belegbilder
   - **Workflow:** RechnungsFee erstellt ZIP → AGENDA importiert → Matcht PDF+XML automatisch

**RechnungsFee-Export für AGENDA:**

```python
def export_belege_fuer_agenda(zeitraum):
    """
    Exportiert alle Belege im AGENDA-kompatiblen Format

    Output:
    belege_2025-Q4.zip
    ├── rechnung-001.pdf  (Beleg-Scan/PDF)
    ├── rechnung-001.xml  (XRechnung-Daten)
    ├── rechnung-002.pdf
    ├── rechnung-002.xml
    └── ...
    """
    rechnungen = get_rechnungen(zeitraum)
    zip_file = create_zip(f"belege_{zeitraum}.zip")

    for rechnung in rechnungen:
        filename_base = f"rechnung-{rechnung.id:03d}"

        # 1. PDF-Beleg
        pdf_path = f"{filename_base}.pdf"
        zip_file.add(rechnung.beleg_pdf, pdf_path)

        # 2. XML-Daten (XRechnung/ZUGFeRD)
        xml_data = generate_xrechnung(rechnung)
        xml_path = f"{filename_base}.xml"
        zip_file.add_text(xml_data, xml_path)

    return zip_file


def export_to_agenda(zeitraum):
    """
    Vollständiger AGENDA-Export
    """
    # 1. DATEV-CSV (Buchungsdaten)
    datev_csv = export_datev(zeitraum)

    # 2. Belegbilder (ZIP mit PDF+XML)
    belege_zip = export_belege_fuer_agenda(zeitraum)

    return {
        'datev': datev_csv,
        'belege': belege_zip
    }
```

**Export-UI:**

```
┌─────────────────────────────────────────┐
│ Export für Steuerberater (AGENDA)      │
├─────────────────────────────────────────┤
│                                         │
│  Zeitraum: [Q4 2025 ▼]                 │
│                                         │
│  ☑ DATEV-Buchungsdaten (CSV)           │
│  ☑ Belegbilder (ZIP mit PDF+XML)       │
│                                         │
│  Dateinamen-Format:                     │
│  ● rechnung-NNN.pdf + .xml              │
│  ○ Rechnungsnummer als Dateiname       │
│                                         │
│  [ Exportieren ]                        │
│                                         │
│  → belege_2025-Q4.zip (12,4 MB)        │
│  → datev_2025-Q4.csv (124 KB)          │
└─────────────────────────────────────────┘
```

**Anforderungen:**
- ✅ **Gleicher Dateiname:** PDF und XML müssen identisch heißen (außer Endung)
- ✅ **ZIP-Format:** Für Massen-Export aller Belege
- ✅ **XRechnung/ZUGFeRD:** XML muss valide sein
- ✅ **DATEV-CSV:** Buchungsdaten parallel exportieren

**Status:** 📋 Für AGENDA-Export-Funktion vorgemerkt (Erweiterung von Kategorie 2: DATEV-Export)

---

