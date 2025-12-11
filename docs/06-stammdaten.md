## **Kategorie 8: Stammdaten-Erfassung**

### **8.1 Übersicht**

Stammdaten sind **grundlegende Informationen**, die wiederholt verwendet werden:

**Arten von Stammdaten in RechnungsFee:**

1. **User-/Firmen-Stammdaten** (Pflicht)
   - Eigene Firma/Freiberufler-Daten
   - Finanzamt, Steuernummer, USt-IdNr.
   - Bank-Verbindungen

2. **Kategorien** (Pflicht)
   - Einnahmen-Kategorien
   - Ausgaben-Kategorien
   - EÜR-Zuordnung

3. **EU-Länder** (für EU-Handel)
   - Ländercodes, MwSt-Sätze
   - USt-IdNr.-Formate

4. **Bankkonten** (für Bank-Integration)
   - IBAN, BIC, Bankname
   - CSV-Format-Zuordnung

5. **Kundenstamm** (📋 **OFFEN** - Community-Entscheidung)
   - Siehe `discussion-kundenstamm.md`
   - Option A: Mit Kundenstamm (v1.0)
   - Option B: Ohne Kundenstamm (v1.0)
   - Option C: Hybrid (optional)

---

### **8.2 User-/Firmen-Stammdaten**

**Zweck:**
- Identifikation der Firma/Freiberufler
- Für Rechnungsvorlagen (Absender)
- Für DATEV/AGENDA-Export
- Für UStVA/EÜR (eigene USt-IdNr., Finanzamt)

**Felder:**

#### **Basis-Informationen:**
```python
class UserStammdaten:
    # Firma/Person
    firmenname: str  # "Musterfirma GmbH" oder "Max Mustermann"
    rechtsform: str  # "Einzelunternehmen", "GbR", "GmbH", "Freiberufler"
    inhaber_name: str  # Bei Einzelunternehmen/Freiberufler

    # Adresse
    strasse: str
    hausnummer: str
    plz: str
    ort: str
    land: str  # ISO 3166-1 Alpha-2, default 'DE'

    # Kontakt
    telefon: str
    email: str
    website: str

    # Steuerliche Daten
    steuernummer: str  # "12/345/67890" (altes Format) oder "2123450678901" (neues 13-stelliges Format nach Umschlüsselung)
    ust_idnr: str  # "DE123456789"
    finanzamt_name: str  # "Finanzamt Oldenburg"
    finanzamt_nummer: str  # "2360"

    # Bank
    iban: str
    bic: str
    bankname: str

    # Steuerliche Einordnung
    ist_kleinunternehmer: bool  # § 19 UStG
    versteuerungsart: str  # 'ist' oder 'soll'
    bezieht_transferleistungen: bool  # ALG II/Bürgergeld → Ist-Versteuerung Pflicht!

    # E-Rechnung
    leitweg_id: str  # Für Rechnungen an öffentliche Auftraggeber (optional)
```

**Validierung:**

```python
def validate_user_stammdaten():
    """
    Prüft Pflichtfelder und Plausibilität
    """
    errors = []

    # 1. Pflichtfelder
    required = ['firmenname', 'strasse', 'plz', 'ort', 'email']
    for field in required:
        if not getattr(user, field):
            errors.append({
                'field': field,
                'message': f'{field} ist Pflichtfeld'
            })

    # 2. Steuernummer oder USt-IdNr. (mindestens eines)
    if not user.steuernummer and not user.ust_idnr:
        errors.append({
            'field': 'steuernummer',
            'message': 'Steuernummer ODER USt-IdNr. erforderlich'
        })

    # 3. USt-IdNr.-Format (wenn vorhanden)
    if user.ust_idnr:
        if not re.match(r'^DE[0-9]{9}$', user.ust_idnr):
            errors.append({
                'field': 'ust_idnr',
                'message': 'USt-IdNr. muss Format "DE123456789" haben'
            })

    # 4. Kleinunternehmer: Keine USt-IdNr. nötig
    if user.ist_kleinunternehmer and user.ust_idnr:
        # Warnung, kein Fehler (kann beides haben)
        warnings.append({
            'field': 'ist_kleinunternehmer',
            'message': 'Kleinunternehmer haben meist keine USt-IdNr.'
        })

    # 5. Transferleistungen → Ist-Versteuerung Pflicht
    if user.bezieht_transferleistungen and user.versteuerungsart == 'soll':
        errors.append({
            'field': 'versteuerungsart',
            'message': 'Bei Bezug von Transferleistungen ist Ist-Versteuerung Pflicht (SGBII § 11)'
        })

    # 6. IBAN-Format (wenn vorhanden)
    if user.iban:
        if not validate_iban(user.iban):
            errors.append({
                'field': 'iban',
                'message': 'IBAN hat ungültiges Format'
            })

    return {
        'errors': errors,
        'valid': len(errors) == 0
    }
```

**UI - Einrichtungs-Assistent (Setup-Wizard):**

```
┌─────────────────────────────────────────────────┐
│ RechnungsFee - Ersteinrichtung (Schritt 1/4) │
├─────────────────────────────────────────────────┤
│                                                 │
│ FIRMA / FREIBERUFLER                            │
│                                                 │
│  Firmenname:  [___________________________]    │
│  Rechtsform:  [Freiberufler ▼]                 │
│               □ Einzelunternehmer               │
│               □ GbR                             │
│               ● Freiberufler                    │
│                                                 │
│  ℹ️ RechnungsFee unterstützt nur            │
│     EÜR-berechtigte Rechtsformen.              │
│     Bilanzpflichtige Gesellschaften (GmbH,     │
│     UG, OHG, KG) werden nicht unterstützt.     │
│                                                 │
│  Inhaber:     [Max Mustermann____________]     │
│                                                 │
│ ADRESSE                                         │
│                                                 │
│  Straße:      [Musterstraße______________]     │
│  Hausnummer:  [42__]                            │
│  PLZ:         [26121]  Ort: [Oldenburg____]    │
│  Land:        [Deutschland ▼]                   │
│                                                 │
│ KONTAKT                                         │
│                                                 │
│  E-Mail:      [max@example.com___________]     │
│  Telefon:     [0441 12345678_____________]     │
│  Website:     [www.example.com___________]     │
│                                                 │
│              [Zurück]        [Weiter →]         │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ RechnungsFee - Ersteinrichtung (Schritt 2/4) │
├─────────────────────────────────────────────────┤
│                                                 │
│ STEUERLICHE DATEN                               │
│                                                 │
│  Steuernummer:    [12/345/67890__________]     │
│  USt-IdNr.:       [DE123456789___________]     │
│                   [ Validieren ]  ✅ Gültig     │
│                                                 │
│  Finanzamt:       [Finanzamt Oldenburg___]     │
│  FA-Nummer:       [2360]                        │
│                                                 │
│ STEUERLICHE EINORDNUNG                          │
│                                                 │
│  ☑ Kleinunternehmer (§ 19 UStG)                │
│    → Keine Umsatzsteuer auf Rechnungen         │
│    → Kein Vorsteuerabzug                        │
│                                                 │
│  Versteuerungsart:                              │
│    ● Ist-Versteuerung (Zufluss-Prinzip)        │
│    ○ Soll-Versteuerung (Rechnungsdatum)        │
│                                                 │
│  ⚠️  WICHTIG:                                   │
│  ☑ Ich beziehe Transferleistungen (ALG II)     │
│    → Ist-Versteuerung ist PFLICHT (SGBII § 11) │
│                                                 │
│ EU-HANDEL                                       │
│                                                 │
│  ☑ Ich plane EU-Geschäft                       │
│    → USt-IdNr. erforderlich                     │
│    → Siehe Kategorie 6.2 (EU-Handel)           │
│                                                 │
│              [← Zurück]      [Weiter →]         │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ RechnungsFee - Ersteinrichtung (Schritt 3/4) │
├─────────────────────────────────────────────────┤
│                                                 │
│ BANKVERBINDUNG                                  │
│                                                 │
│  IBAN:      [DE89370400440532013000______]     │
│             ✅ Gültig                           │
│  BIC:       [COBADEFFXXX_________________]     │
│  Bankname:  [Commerzbank_________________]     │
│                                                 │
│  💡 Diese Daten erscheinen auf Rechnungen      │
│                                                 │
│              [← Zurück]      [Weiter →]         │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ RechnungsFee - Ersteinrichtung (Schritt 4/4) │
├─────────────────────────────────────────────────┤
│                                                 │
│ ZUSAMMENFASSUNG                                 │
│                                                 │
│ ✅ Firma:        Max Mustermann (Freiberufler) │
│ ✅ Adresse:      Musterstraße 42, 26121 OL     │
│ ✅ Steuernr.:    12/345/67890                   │
│ ✅ USt-IdNr.:    DE123456789 (validiert)        │
│ ✅ Finanzamt:    Finanzamt Oldenburg (2360)     │
│ ✅ Bank:         DE89...3000 (Commerzbank)      │
│                                                 │
│ EINSTELLUNGEN:                                  │
│ ✅ Kleinunternehmer (§ 19 UStG)                │
│ ✅ Ist-Versteuerung (Pflicht wegen ALG II)     │
│ ✅ EU-Geschäft geplant                         │
│                                                 │
│              [← Zurück]    [Abschließen]        │
└─────────────────────────────────────────────────┘
```

---

### **8.2.1 Unterstützte Rechtsformen**

**RechnungsFee unterstützt nur EÜR-berechtigte Rechtsformen:**

✅ **Unterstützt:**
- **Einzelunternehmer** - Gewerbetreibende ohne besondere Rechtsform
- **Freiberufler** - § 18 EStG (Ärzte, Anwälte, IT-Berater, Künstler, etc.)
- **GbR (Gesellschaft bürgerlichen Rechts)** - Personengesellschaft unter Grenzen (Gewinn < 60k€, Umsatz < 600k€)

❌ **NICHT unterstützt (bilanzpflichtig):**
- **GmbH** - Kapitalgesellschaft → Bilanzierung Pflicht nach HGB
- **UG (haftungsbeschränkt)** - Kleine Kapitalgesellschaft → Bilanzierung Pflicht
- **OHG (Offene Handelsgesellschaft)** - Personengesellschaft → Bilanzierung Pflicht
- **KG (Kommanditgesellschaft)** - Personengesellschaft → Bilanzierung Pflicht

**UI-Verhalten:**

```
Rechtsform wählen:

○ Einzelunternehmer
○ Freiberufler
● GbR

──────────────────────────────────────

ℹ️ Hinweis: RechnungsFee unterstützt nur
   EÜR-berechtigte Rechtsformen.

   Bilanzpflichtige Gesellschaften (GmbH,
   UG, OHG, KG) können nicht verwendet
   werden, da sie zur doppelten
   Buchführung verpflichtet sind.
```

**Begründung:**

| Rechtsform | EÜR | Bilanz | RechnungsFee |
|------------|-----|--------|----------------|
| Einzelunternehmer | ✅ | ❌ | ✅ Unterstützt |
| Freiberufler | ✅ | ❌ | ✅ Unterstützt |
| GbR (unter Grenzen) | ✅ | ❌ | ✅ Unterstützt |
| GbR (über Grenzen) | ❌ | ✅ | ❌ Nicht unterstützt |
| GmbH, UG | ❌ | ✅ | ❌ Nicht unterstützt |
| OHG, KG | ❌ | ✅ | ❌ Nicht unterstützt |

**Grenzen für GbR:**
- Gewinn < 60.000 € pro Jahr UND
- Umsatz < 600.000 € pro Jahr

⚠️ **Warnung bei Überschreitung:** RechnungsFee warnt, wenn GbR diese Grenzen überschreitet.

---

### **8.2.2 Steuernummer-Formate**

**Deutschland hat zwei Steuernummer-Formate:**

#### **Altes Format (Bundesland-spezifisch):**

**Format:** `FF/BBB/UUUUP`

- **FF** = Finanzamtsnummer (2-stellig)
- **BBB** = Bezirksnummer (3-stellig)
- **UUUUP** = Persönliche Nummer + Prüfziffer (5-stellig)

**Beispiel:** `12/345/67890`

**Varianten je Bundesland:**
- Bayern: `123/456/78901` (3/3/5)
- NRW: `123/4567/8901` (3/4/4)
- Baden-Württemberg: `12345/67890` (5/5)

#### **Neues Format (Bundeseinheitlich nach Umschlüsselung):**

**Format:** `BBFFUUUUUUUUP` (13-stellig, ohne Schrägstriche)

- **BB** = Bundesland-Kennziffer (2-stellig)
- **FF** = Finanzamtsnummer (2-stellig)
- **UUUUUUUU** = Persönliche Nummer (8-stellig)
- **P** = Prüfziffer (1-stellig)

**Beispiel:** `2123450678901`

**Bundesland-Kennziffern:**
- 21 = Niedersachsen
- 93 = Bayern
- 51 = Nordrhein-Westfalen
- 28 = Baden-Württemberg
- etc.

**RechnungsFee unterstützt beide Formate:**

```python
def validate_steuernummer(stnr: str) -> bool:
    """
    Validiert Steuernummer (altes oder neues Format)
    """
    # Schrägstriche entfernen für Verarbeitung
    stnr_clean = stnr.replace('/', '').replace(' ', '')

    # Neues Format: 13-stellig, nur Ziffern
    if len(stnr_clean) == 13 and stnr_clean.isdigit():
        return validate_bundeseinheitlich(stnr_clean)

    # Altes Format: 10-11 Ziffern (ohne Schrägstriche)
    if len(stnr_clean) >= 10 and len(stnr_clean) <= 11:
        return validate_alt(stnr, stnr_clean)

    return False
```

**UI-Eingabe:**

```
┌──────────────────────────────────────────┐
│ Steuernummer                             │
├──────────────────────────────────────────┤
│                                          │
│  Format: [Auto-Erkennung ▼]              │
│          ● Automatisch erkennen          │
│          ○ Alt (z.B. 12/345/67890)      │
│          ○ Neu (13-stellig)             │
│                                          │
│  Steuernummer: [_________________]       │
│                                          │
│  ✅ Gültig (neues Format erkannt)        │
│     2123450678901                        │
│                                          │
│    [ Abbrechen ]  [ Speichern ]          │
└──────────────────────────────────────────┘
```

**Automatische Erkennung:**
- Eingabe mit Schrägstrichen (`/`) → Altes Format
- Eingabe 13-stellig ohne Schrägstriche → Neues Format
- Validierung nach erkanntem Format

**Speicherung:**
- Intern: Immer normalisiert (ohne Schrägstriche)
- Anzeige: Mit ursprünglicher Formatierung
- Export: Je nach Ziel-System (ELSTER akzeptiert beide)

---

### **8.2.3 Berufsrechtliche Pflichtangaben**

**Bestimmte Berufe haben Pflichtangaben auf Rechnungen:**

#### **Kammerberufe:**

| Beruf | Pflichtangabe | Beispiel |
|-------|--------------|----------|
| **Handwerker** | Handwerkskammer + Handwerksrollennummer | "Eingetragen bei Handwerkskammer Oldenburg, Nr. HWK-123456" |
| **Arzt** | Ärztekammer + Approbationsnummer (optional) | "Mitglied der Ärztekammer Niedersachsen" |
| **Rechtsanwalt** | Rechtsanwaltskammer + Zulassung | "Zugelassen bei Rechtsanwaltskammer Oldenburg" |
| **Steuerberater** | Steuerberaterkammer + Berufsbezeichnung | "Mitglied der Steuerberaterkammer Niedersachsen" |
| **Architekt** | Architektenkammer + Berufsbezeichnung | "Mitglied der Architektenkammer Niedersachsen" |
| **Ingenieur** | Ingenieurkammer (je nach Bundesland) | "Mitglied der Ingenieurkammer Niedersachsen" |

#### **IHK-Mitglieder:**

**Gewerbetreibende (IHK-pflichtig):**
- IHK + Registernummer (optional, aber empfohlen)
- Beispiel: "IHK Oldenburg, Registernummer IHK-789012"

#### **Datenmodell:**

```python
class User:
    # ... (bestehende Felder)

    # Berufsrechtliche Angaben (optional, je nach Beruf)
    kammer_typ: str  # 'handwerk', 'aerzte', 'rechtsanwaelte', 'steuerberater', 'architekten', 'ingenieure', 'ihk', 'keine'
    kammer_name: str  # "Handwerkskammer Oldenburg"
    kammer_nummer: str  # "HWK-123456" oder "IHK-789012"

    # Zusätzliche Angaben (je nach Beruf)
    berufsbezeichnung: str  # "Rechtsanwalt", "Steuerberater", "Architekt"
    approbation: str  # Nur für Ärzte/Apotheker
```

#### **UI-Eingabe im Setup-Wizard:**

```
┌─────────────────────────────────────────────────┐
│ RechnungsFee - Ersteinrichtung (Schritt 1/4) │
├─────────────────────────────────────────────────┤
│                                                 │
│ BERUFSRECHTLICHE ANGABEN                        │
│                                                 │
│ Bist du Mitglied einer Kammer/eines            │
│ Berufsverbandes?                                │
│                                                 │
│ ○ Nein                                          │
│ ● Ja                                            │
│                                                 │
│   Kammer/Verband: [Handwerkskammer ▼]          │
│                   □ Keine                       │
│                   ● Handwerkskammer             │
│                   □ Ärztekammer                 │
│                   □ Rechtsanwaltskammer         │
│                   □ Steuerberaterkammer         │
│                   □ Architektenkammer           │
│                   □ Ingenieurkammer             │
│                   □ IHK                         │
│                                                 │
│   Name:   [Handwerkskammer Oldenburg____]      │
│   Nummer: [HWK-123456___________________]      │
│                                                 │
│   ℹ️ Diese Angaben erscheinen auf Rechnungen   │
│      (gesetzliche Pflicht bei Kammerberufen)   │
│                                                 │
│              [← Zurück]      [Weiter →]         │
└─────────────────────────────────────────────────┘
```

#### **Rechtliche Grundlagen:**

**§ 14 Abs. 4 UStG - Pflichtangaben auf Rechnungen:**

Für Kammerberufe zusätzlich erforderlich:
- Berufsbezeichnung
- Zuständige Kammer
- Kammernummer (je nach Kammer)

**Beispiele auf Rechnung:**

**1. Handwerker:**
```
Max Mustermann
Elektroinstallateur
Musterstraße 42, 26121 Oldenburg

Eingetragen bei der Handwerkskammer Oldenburg
Handwerksrollennummer: HWK-123456
```

**2. Rechtsanwalt:**
```
Dr. Erika Musterfrau
Rechtsanwältin
Musterstraße 42, 26121 Oldenburg

Zugelassen bei der Rechtsanwaltskammer Oldenburg
```

**3. Arzt:**
```
Dr. med. Max Mustermann
Facharzt für Allgemeinmedizin
Musterstraße 42, 26121 Oldenburg

Mitglied der Ärztekammer Niedersachsen
```

**4. IHK-Mitglied:**
```
Musterfirma GmbH
Geschäftsführer: Max Mustermann
Musterstraße 42, 26121 Oldenburg

IHK Oldenburg, Registernummer: IHK-789012
```

#### **Automatische Angabe auf Rechnungen:**

```python
def generate_rechnung_kopf(user, kunde):
    """
    Generiert Rechnungskopf mit Pflichtangaben
    """
    kopf = f"{user.firmenname or f'{user.vorname} {user.nachname}'}\n"

    # Berufsbezeichnung (wenn vorhanden)
    if user.berufsbezeichnung:
        kopf += f"{user.berufsbezeichnung}\n"

    kopf += f"{user.strasse}, {user.plz} {user.ort}\n\n"

    # Kammer-Angaben (Pflicht bei Kammerberufen)
    if user.kammer_typ != 'keine':
        if user.kammer_typ == 'handwerk':
            kopf += f"Eingetragen bei der {user.kammer_name}\n"
            kopf += f"Handwerksrollennummer: {user.kammer_nummer}\n\n"

        elif user.kammer_typ == 'rechtsanwaelte':
            kopf += f"Zugelassen bei der {user.kammer_name}\n\n"

        elif user.kammer_typ == 'aerzte':
            kopf += f"Mitglied der {user.kammer_name}\n"
            if user.approbation:
                kopf += f"Approbation: {user.approbation}\n"
            kopf += "\n"

        elif user.kammer_typ == 'ihk':
            kopf += f"{user.kammer_name}"
            if user.kammer_nummer:
                kopf += f", Registernummer: {user.kammer_nummer}"
            kopf += "\n\n"

        else:
            # Generisch: Steuerberater, Architekten, Ingenieure
            kopf += f"Mitglied der {user.kammer_name}\n\n"

    return kopf
```

#### **Validierung:**

```python
def validate_kammerangaben(user):
    """
    Prüft ob Kammer-Angaben vollständig sind
    """
    errors = []

    if user.kammer_typ != 'keine':
        if not user.kammer_name:
            errors.append({
                'field': 'kammer_name',
                'message': 'Kammer-Name ist Pflicht bei Kammerberufen'
            })

        # Handwerker: Nummer ist Pflicht
        if user.kammer_typ == 'handwerk' and not user.kammer_nummer:
            errors.append({
                'field': 'kammer_nummer',
                'message': 'Handwerksrollennummer ist Pflicht für Handwerker'
            })

    return errors
```

#### **Hinweis für User:**

⚠️ **Wichtig:**
- Bei Kammerberufen sind diese Angaben **gesetzlich verpflichtend** auf Rechnungen
- Fehlende Angaben können zu Abmahnungen führen
- RechnungsFee fügt diese automatisch in Rechnungsvorlagen ein

💡 **Tipp:**
- Falls unsicher: Auf der Website Ihrer Kammer nachsehen
- Bei IHK: Pflicht zur Mitgliedschaft, Angabe auf Rechnung empfohlen

---

### **8.3 Kategorien (Einnahmen/Ausgaben)**

**Zweck:**
- Einnahmen/Ausgaben kategorisieren
- Automatische EÜR-Zeilen-Zuordnung
- DATEV-Konten-Mapping
- Auswertungen (Kostenstellen)

**Standardkategorien (vordefiniert):**

#### **Einnahmen-Kategorien:**
```python
EINNAHMEN_KATEGORIEN = [
    {'id': 1, 'name': 'Warenverkauf', 'euer_zeile': 11, 'datev_konto': 8400},
    {'id': 2, 'name': 'Dienstleistungen', 'euer_zeile': 11, 'datev_konto': 8400},
    {'id': 3, 'name': 'Provisionen', 'euer_zeile': 11, 'datev_konto': 8500},
    {'id': 4, 'name': 'Erstattungen', 'euer_zeile': 11, 'datev_konto': 8900},
    {'id': 5, 'name': 'Sonstige Einnahmen', 'euer_zeile': 11, 'datev_konto': 8900},
]
```

#### **Ausgaben-Kategorien:**
```python
AUSGABEN_KATEGORIEN = [
    {'id': 10, 'name': 'Wareneinkauf', 'euer_zeile': 25, 'datev_konto': 3400},
    {'id': 11, 'name': 'Löhne & Gehälter', 'euer_zeile': 26, 'datev_konto': 4120},  # Auch für Einzelunternehmer!
    {'id': 12, 'name': 'Raumkosten (Miete)', 'euer_zeile': 28, 'datev_konto': 4210},
    {'id': 13, 'name': 'Strom, Gas, Wasser', 'euer_zeile': 28, 'datev_konto': 4240},
    {'id': 14, 'name': 'Telefon, Internet', 'euer_zeile': 28, 'datev_konto': 4910},
    {'id': 15, 'name': 'KFZ-Kosten (Benzin)', 'euer_zeile': 32, 'datev_konto': 4530},
    {'id': 16, 'name': 'KFZ-Versicherung', 'euer_zeile': 32, 'datev_konto': 4570},
    {'id': 17, 'name': 'Fahrtkosten (ÖPNV)', 'euer_zeile': 32, 'datev_konto': 4670},
    {'id': 18, 'name': 'Werbekosten', 'euer_zeile': 34, 'datev_konto': 4600},
    {'id': 19, 'name': 'Bürobedarf', 'euer_zeile': 36, 'datev_konto': 4910},
    {'id': 20, 'name': 'Software, Lizenzen', 'euer_zeile': 36, 'datev_konto': 4940},
    {'id': 21, 'name': 'Fortbildung', 'euer_zeile': 40, 'datev_konto': 4945},
    {'id': 22, 'name': 'Versicherungen (betr.)', 'euer_zeile': 41, 'datev_konto': 4360},
    {'id': 23, 'name': 'Steuerberatung', 'euer_zeile': 43, 'datev_konto': 4970},
    {'id': 24, 'name': 'Sonstige Ausgaben', 'euer_zeile': 43, 'datev_konto': 4980},
]
```

**User kann eigene Kategorien hinzufügen:**

```python
class Kategorie:
    id: int
    name: str  # "Marketing-Flyer"
    typ: str  # 'einnahme' oder 'ausgabe'
    euer_zeile: int  # 34 (Werbekosten)
    datev_konto: int  # 4600 (Werbekosten)
    ist_standard: bool  # False (custom)
    erstellt_am: datetime
```

**UI - Kategorien verwalten:**

```
┌──────────────────────────────────────────────┐
│ Einstellungen → Kategorien                   │
├──────────────────────────────────────────────┤
│                                              │
│ EINNAHMEN-KATEGORIEN                         │
│                                              │
│ ID │ Name                 │ EÜR │ DATEV     │
│────┼──────────────────────┼─────┼──────────│
│  1 │ Warenverkauf         │  11 │ 8400  🔒 │
│  2 │ Dienstleistungen     │  11 │ 8400  🔒 │
│  3 │ Provisionen          │  11 │ 8500  🔒 │
│  4 │ Erstattungen         │  11 │ 8900  🔒 │
│  5 │ Sonstige Einnahmen   │  11 │ 8900  🔒 │
│────┼──────────────────────┼─────┼──────────│
│  6 │ Online-Kurse         │  11 │ 8400  ✏️ │
│                                              │
│ [ + Neue Kategorie ]                         │
│                                              │
│ AUSGABEN-KATEGORIEN                          │
│                                              │
│ ID │ Name                 │ EÜR │ DATEV     │
│────┼──────────────────────┼─────┼──────────│
│ 10 │ Wareneinkauf         │  25 │ 3400  🔒 │
│ 11 │ Raumkosten (Miete)   │  28 │ 4210  🔒 │
│ 12 │ Strom, Gas, Wasser   │  28 │ 4240  🔒 │
│ ...│ ...                  │ ... │ ...   🔒 │
│ 23 │ Sonstige Ausgaben    │  43 │ 4980  🔒 │
│────┼──────────────────────┼─────┼──────────│
│ 30 │ Hosting-Kosten       │  43 │ 4980  ✏️ │
│ 31 │ Bücher (Fachliteratur)│ 40 │ 4945  ✏️ │
│                                              │
│ [ + Neue Kategorie ]                         │
│                                              │
│ 🔒 = Standard (nicht editierbar)             │
│ ✏️  = Custom (editierbar/löschbar)           │
└──────────────────────────────────────────────┘
```

---

### **8.4 EU-Länder-Stammdaten**

**Zweck:**
- EU-Handel (Kategorie 6.2)
- Validierung USt-IdNr.-Format
- MwSt-Sätze für Reverse Charge

**Datenbank:**
```sql
CREATE TABLE eu_laender (
    code TEXT PRIMARY KEY,  -- 'BE' (ISO 3166-1 Alpha-2)
    name_de TEXT,  -- 'Belgien'
    name_en TEXT,  -- 'Belgium'

    -- MwSt-Sätze
    mwst_satz_standard DECIMAL(5,2),  -- 21.0
    mwst_satz_reduziert DECIMAL(5,2),  -- 6.0

    -- USt-IdNr.-Format
    ust_idnr_prefix TEXT,  -- 'BE'
    ust_idnr_regex TEXT,  -- '^BE[0-9]{10}$'
    ust_idnr_beispiel TEXT,  -- 'BE0123456789'

    -- EU-Mitglied seit
    eu_beitritt_jahr INTEGER,  -- 1957

    -- Aktiv
    ist_eu_mitglied BOOLEAN DEFAULT 1,  -- True (falls Land austritt)

    -- Metadaten
    aktualisiert_am TIMESTAMP
);
```

**Vorbefüllung (Beispiel):**
```python
EU_LAENDER_INITIAL = [
    {
        'code': 'AT', 'name_de': 'Österreich', 'name_en': 'Austria',
        'mwst_satz_standard': 20.0, 'mwst_satz_reduziert': 10.0,
        'ust_idnr_prefix': 'AT', 'ust_idnr_regex': r'^ATU[0-9]{8}$',
        'ust_idnr_beispiel': 'ATU12345678', 'eu_beitritt_jahr': 1995
    },
    {
        'code': 'BE', 'name_de': 'Belgien', 'name_en': 'Belgium',
        'mwst_satz_standard': 21.0, 'mwst_satz_reduziert': 6.0,
        'ust_idnr_prefix': 'BE', 'ust_idnr_regex': r'^BE[0-9]{10}$',
        'ust_idnr_beispiel': 'BE0123456789', 'eu_beitritt_jahr': 1957
    },
    {
        'code': 'FR', 'name_de': 'Frankreich', 'name_en': 'France',
        'mwst_satz_standard': 20.0, 'mwst_satz_reduziert': 5.5,
        'ust_idnr_prefix': 'FR', 'ust_idnr_regex': r'^FR[0-9A-Z]{2}[0-9]{9}$',
        'ust_idnr_beispiel': 'FR12345678901', 'eu_beitritt_jahr': 1957
    },
    # ... weitere 24 EU-Länder
]
```

**Verwendung:**
```python
def validate_ust_idnr_format(ust_idnr, land_code):
    """
    Prüft USt-IdNr. gegen Länder-Format
    """
    land = get_eu_land(land_code)

    if not land:
        return False, f"Land {land_code} nicht in EU-Stammdaten"

    if not re.match(land.ust_idnr_regex, ust_idnr):
        return False, f"Format ungültig. Erwartet: {land.ust_idnr_beispiel}"

    return True, "Format OK"


def get_reverse_charge_mwst(land_code):
    """
    Holt MwSt-Satz des Lieferlands für Reverse Charge
    """
    land = get_eu_land(land_code)
    return land.mwst_satz_standard  # Z.B. 21% für Belgien
```

---

### **8.5 Bankkonten-Stammdaten**

**Zweck:**
- Bank-CSV-Import (Kategorie 5)
- Zuordnung CSV-Format → Parser
- Mehrere Konten verwalten

**Datenbank:**
```sql
CREATE TABLE bankkonten (
    id INTEGER PRIMARY KEY,

    -- Kontodaten
    kontoname TEXT NOT NULL,  -- "Geschäftskonto Commerzbank"
    iban TEXT NOT NULL UNIQUE,
    bic TEXT,
    bankname TEXT,

    -- CSV-Import
    bank_typ TEXT,  -- 'commerzbank', 'sparkasse', 'dkb', 'paypal'
    csv_format TEXT,  -- 'mt940', 'camt_v8', 'standard'
    csv_delimiter TEXT DEFAULT ';',  -- ';', ',', '\t'
    csv_encoding TEXT DEFAULT 'ISO-8859-1',  -- 'UTF-8', 'ISO-8859-1'

    -- Status
    ist_hauptkonto BOOLEAN DEFAULT 0,
    ist_aktiv BOOLEAN DEFAULT 1,

    -- Saldo
    aktueller_saldo DECIMAL(10,2),
    saldo_datum DATE,

    -- Metadaten
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**UI - Bankkonten verwalten:**

```
┌─────────────────────────────────────────────────┐
│ Einstellungen → Bankkonten                      │
├─────────────────────────────────────────────────┤
│                                                 │
│ GESCHÄFTSKONTEN                                 │
│                                                 │
│ ┌─────────────────────────────────────────────┐ │
│ │ ⭐ Hauptkonto: Commerzbank                   │ │
│ │                                             │ │
│ │ IBAN:     DE89 3704 0044 0532 0130 00      │ │
│ │ BIC:      COBADEFFXXX                       │ │
│ │ Bank:     Commerzbank                       │ │
│ │                                             │ │
│ │ CSV-Import:                                 │ │
│ │ - Format:    Commerzbank Standard           │ │
│ │ - Delimiter: ; (Semikolon)                  │ │
│ │ - Encoding:  ISO-8859-1                     │ │
│ │                                             │ │
│ │ Saldo:       8.450,23 € (Stand: 06.12.25)  │ │
│ │                                             │ │
│ │ [ Bearbeiten ]  [ CSV importieren ]         │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ ┌─────────────────────────────────────────────┐ │
│ │ PayPal Geschäftskonto                       │ │
│ │                                             │ │
│ │ E-Mail:   fibu@musterfirma.de               │ │
│ │ Typ:      PayPal                            │ │
│ │                                             │ │
│ │ CSV-Import:                                 │ │
│ │ - Format:    PayPal Aktivitätsbericht       │ │
│ │ - Delimiter: , (Komma)                      │ │
│ │ - Encoding:  UTF-8                          │ │
│ │                                             │ │
│ │ Saldo:       234,56 € (Stand: 06.12.25)    │ │
│ │                                             │ │
│ │ [ Bearbeiten ]  [ CSV importieren ]         │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ [ + Bankkonto hinzufügen ]                      │
└─────────────────────────────────────────────────┘
```

**Hinzufügen-Dialog:**

```
┌─────────────────────────────────────────┐
│ Neues Bankkonto hinzufügen              │
├─────────────────────────────────────────┤
│                                         │
│ Kontoname:  [Geschäftskonto_________]  │
│                                         │
│ IBAN:       [DE89________________]     │
│             [ Validieren ] ✅ Gültig   │
│ BIC:        [COBADEFFXXX_________]     │
│ Bankname:   [Commerzbank_________]     │
│                                         │
│ CSV-IMPORT-EINSTELLUNGEN                │
│                                         │
│ Bank/Typ:   [Commerzbank ▼]            │
│             - Commerzbank               │
│             - Sparkasse (MT940)         │
│             - Sparkasse (CAMT V8)       │
│             - DKB                       │
│             - PayPal                    │
│             - Andere...                 │
│                                         │
│ Format:     [Standard ▼]               │
│ Delimiter:  [; (Semikolon) ▼]          │
│ Encoding:   [ISO-8859-1 ▼]             │
│                                         │
│ ☑ Als Hauptkonto festlegen             │
│                                         │
│        [Abbrechen]  [ Speichern ]      │
└─────────────────────────────────────────┘
```

---

### **8.6 Kontenrahmen (SKR03 / SKR04)**

**Zweck:**
- DATEV-Export korrekt zuordnen
- Buchungskonten für Einnahmen/Ausgaben
- Unterschied zwischen Gewerbetreibenden und Freiberuflern

**Was ist der Kontenrahmen?**
- Standardisierte Nummernstruktur für Buchhaltungskonten
- In Deutschland: SKR03 oder SKR04 (DATEV-Standard)

**Unterschied:**

| Aspekt | SKR03 | SKR04 |
|--------|-------|-------|
| **Zielgruppe** | Gewerbetreibende, Handwerk, Handel | Freiberufler, Dienstleister |
| **Struktur** | Prozessgliederung (nach Ablauf) | Abschlussgliederung (nach Bilanz) |
| **Beispiel** | Konto 8400: Erlöse 19% USt | Konto 4400: Erlöse 19% USt |
| **Verbreitung** | Häufiger | Seltener |

**Auswahl im Setup-Wizard:**

```
┌─────────────────────────────────────────┐
│ Kontenrahmen auswählen                  │
├─────────────────────────────────────────┤
│                                         │
│ Welchen Kontenrahmen nutzt du?         │
│                                         │
│ ● SKR03 (Prozessgliederung)            │
│   Empfohlen für:                        │
│   - Gewerbetreibende                    │
│   - Handel, Handwerk                    │
│   - Produktion                          │
│                                         │
│ ○ SKR04 (Abschlussgliederung)          │
│   Empfohlen für:                        │
│   - Freiberufler                        │
│   - Dienstleister                       │
│   - Beratung, IT, Kreative              │
│                                         │
│ 💡 Diese Einstellung kann später        │
│    geändert werden.                     │
│                                         │
│          [Zurück]  [Weiter →]           │
└─────────────────────────────────────────┘
```

**Datenbank:**
```sql
ALTER TABLE user_settings ADD COLUMN kontenrahmen TEXT DEFAULT 'SKR03';
-- 'SKR03' oder 'SKR04'
```

**Implementierung:**
```python
def get_datev_konto(kategorie_name, kontenrahmen='SKR03'):
    """
    Gibt DATEV-Konto für Kategorie zurück
    """
    mapping = {
        'Warenverkauf': {
            'SKR03': 8400,
            'SKR04': 4400
        },
        'Bürobedarf': {
            'SKR03': 4910,
            'SKR04': 6815
        },
        # ... weitere Kategorien
    }

    return mapping[kategorie_name][kontenrahmen]
```

**Wechsel später möglich:**
```python
def switch_kontenrahmen(alt, neu):
    """
    Wechselt Kontenrahmen für alle Kategorien
    """
    kategorien = get_all_kategorien()

    for kat in kategorien:
        kat.datev_konto = get_datev_konto(kat.name, neu)
        kat.save()

    user_settings.kontenrahmen = neu
    user_settings.save()

    return f"Kontenrahmen gewechselt: {alt} → {neu}"
```

---

### **8.7 Geschäftsjahr**

**Zweck:**
- Zeiträume für EÜR, UStVA, Auswertungen
- Standard: Kalenderjahr (01.01. - 31.12.)
- Abweichendes Wirtschaftsjahr möglich (z.B. Landwirtschaft)

**Standard: Kalenderjahr**
```python
class UserSettings:
    geschaeftsjahr_start: str = '01-01'  # MM-DD
    geschaeftsjahr_ende: str = '12-31'   # MM-DD
```

**Abweichendes Wirtschaftsjahr (Beispiel):**
```
Landwirtschaft: 01.07. - 30.06.
→ geschaeftsjahr_start = '07-01'
→ geschaeftsjahr_ende = '06-30'
```

**UI - Setup-Wizard:**
```
┌─────────────────────────────────────────┐
│ Geschäftsjahr festlegen                 │
├─────────────────────────────────────────┤
│                                         │
│ ● Kalenderjahr (01.01. - 31.12.)       │
│   Standard für die meisten Unternehmen │
│                                         │
│ ○ Abweichendes Wirtschaftsjahr         │
│   Beginn: [01] . [07] (TT.MM)          │
│   Ende:   [30] . [06] (TT.MM)          │
│                                         │
│   Beispiel: Landwirtschaft (01.07.-30.06.)│
│                                         │
│ 💡 Wichtig für EÜR und Jahresabschluss │
│                                         │
│          [Zurück]  [Weiter →]           │
└─────────────────────────────────────────┘
```

**Verwendung:**
```python
def get_geschaeftsjahr(jahr):
    """
    Gibt Start- und End-Datum des Geschäftsjahres zurück
    """
    user = get_user_settings()

    if user.geschaeftsjahr_start == '01-01':
        # Kalenderjahr
        return (
            date(jahr, 1, 1),
            date(jahr, 12, 31)
        )
    else:
        # Abweichendes Wirtschaftsjahr
        start_month, start_day = user.geschaeftsjahr_start.split('-')
        ende_month, ende_day = user.geschaeftsjahr_ende.split('-')

        start = date(jahr, int(start_month), int(start_day))

        # Ende kann im Folgejahr sein
        if int(ende_month) < int(start_month):
            ende = date(jahr + 1, int(ende_month), int(ende_day))
        else:
            ende = date(jahr, int(ende_month), int(ende_day))

        return (start, ende)


def calculate_euer(jahr):
    """
    Berechnet EÜR für Geschäftsjahr
    """
    start, ende = get_geschaeftsjahr(jahr)

    rechnungen = get_rechnungen(
        zahlungsdatum__gte=start,
        zahlungsdatum__lte=ende
    )
    # ... Berechnung
```

---

### **8.8 Lieferantenstammdaten**

**Zweck:**
- Wiederholte Lieferanten (z.B. Vermieter, Telefon, Strom, Material)
- Autocomplete bei Eingangsrechnungen
- Detaillierte Kontaktdaten für Bestellungen

**Datenbank:**
```sql
CREATE TABLE lieferanten (
    id INTEGER PRIMARY KEY,

    -- Stammdaten
    lieferantennummer TEXT UNIQUE,  -- "L-001" (automatisch)
    name TEXT NOT NULL,  -- "Deutsche Telekom AG" (Pflichtfeld) ⭐

    -- Adresse ⭐
    strasse TEXT,
    hausnummer TEXT,
    plz TEXT,
    ort TEXT,
    land TEXT DEFAULT 'DE',

    -- Kontakt (Firma) ⭐
    telefon TEXT,
    email TEXT,
    website TEXT,

    -- Kontaktperson ⭐ NEU
    kontaktperson_name TEXT,  -- z.B. "Max Mustermann"
    kontaktperson_telefon TEXT,
    kontaktperson_email TEXT,

    -- Unternehmensdetails ⭐ NEU
    handelsregisternummer TEXT,  -- z.B. "HRB 12345"
    steuernummer TEXT,

    -- Steuerlich
    ust_idnr TEXT,  -- Bei EU-Lieferanten wichtig (Reverse Charge)

    -- Standard-Kategorie (optional)
    standard_kategorie_id INTEGER,  -- z.B. "Telefon/Internet" für Telekom

    -- Metadaten ⭐
    beschreibung TEXT,  -- Beschreibung / Notizen
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    aktualisiert_am TIMESTAMP,

    -- Statistiken
    anzahl_rechnungen INTEGER DEFAULT 0,
    ausgaben_gesamt DECIMAL(10,2) DEFAULT 0.00,
    letzte_rechnung_datum DATE,

    FOREIGN KEY (standard_kategorie_id) REFERENCES kategorien(id)
);

-- Index für schnelle Suche
CREATE INDEX idx_lieferanten_nummer ON lieferanten(lieferantennummer);
CREATE INDEX idx_lieferanten_name ON lieferanten(name);
```

**UI - Lieferanten verwalten:**
```
┌────────────────────────────────────────────┐
│ Stammdaten → Lieferanten                   │
├────────────────────────────────────────────┤
│                                            │
│ [ + Neuer Lieferant ]        [🔍 Suchen]  │
│                                            │
│ Nr.  │ Name                │ Kategorie     │
│──────┼─────────────────────┼──────────────│
│ L-001│ Vermieter Müller    │ Raumkosten   │
│ L-002│ Deutsche Telekom AG │ Telefon      │
│ L-003│ Amazon Business     │ Bürobedarf   │
│ L-004│ Shell Tankstelle    │ Fahrtkosten  │
│ L-005│ Lieferant BE GmbH   │ Wareneinkauf │
│      │ (BE0123456789)      │ [EU]         │
│                                            │
│ Gesamt: 5 Lieferanten                      │
└────────────────────────────────────────────┘
```

**Verknüpfung mit Eingangsrechnungen:**
```python
class Eingangsrechnung:
    id: int
    lieferant_id: int  # OPTIONAL - Verknüpfung zu Lieferant
    lieferant_name: str  # Immer ausgefüllt (auch ohne Stammdaten)
    # ... andere Felder
```

**Autocomplete beim Erfassen:**
```
┌────────────────────────────────────────┐
│ Eingangsrechnung erfassen              │
├────────────────────────────────────────┤
│                                        │
│ Lieferant: [Deut____________]         │
│            ┌──────────────────────┐   │
│            │ Deutsche Telekom AG  │   │
│            │ (L-002)              │   │
│            │ Kategorie: Telefon   │   │
│            └──────────────────────┘   │
│                                        │
│ [✓] = Enter drücken übernimmt          │
└────────────────────────────────────────┘
```

**Hybrid-Ansatz (wie Kundenstamm):**
- Optional: Lieferant aus Stamm wählen
- Oder: Manuell Name eingeben
- Bei wiederholtem Lieferanten: "Als Lieferant speichern?" anbieten

---

#### **🖥️ UI: Neuen Lieferanten anlegen** ⭐ NEU

```
┌──────────────────────────────────────────────────┐
│ ➕ Neuer Lieferant                               │
├──────────────────────────────────────────────────┤
│                                                  │
│ Name: * ⭐                                       │
│ [Deutsche Telekom AG_________________]           │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ Adresse ⭐                                 │  │
│ ├────────────────────────────────────────────┤  │
│ │                                            │  │
│ │ Straße:          Hausnr.:                  │  │
│ │ [Musterstraße__] [42__]                    │  │
│ │                                            │  │
│ │ PLZ:       Ort:                            │  │
│ │ [53111__]  [Bonn_______________]           │  │
│ │                                            │  │
│ │ Land:                                      │  │
│ │ [Deutschland ▼]                            │  │
│ │                                            │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ Kontakt (Firma) ⭐                         │  │
│ ├────────────────────────────────────────────┤  │
│ │                                            │  │
│ │ Telefon:                                   │  │
│ │ [📞 0228 181-0___________]                 │  │
│ │                                            │  │
│ │ E-Mail:                                    │  │
│ │ [info@telekom.de_____________]             │  │
│ │                                            │  │
│ │ Website:                                   │  │
│ │ [https://www.telekom.de__]                 │  │
│ │                                            │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ Kontaktperson ⭐ NEU                       │  │
│ ├────────────────────────────────────────────┤  │
│ │                                            │  │
│ │ Name:                                      │  │
│ │ [Max Mustermann______________]             │  │
│ │                                            │  │
│ │ Telefon (direkt):                          │  │
│ │ [📞 0228 181-1234________]                 │  │
│ │                                            │  │
│ │ E-Mail (direkt):                           │  │
│ │ [max.mustermann@telekom.de___]             │  │
│ │                                            │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ Unternehmensdetails ⭐ NEU                 │  │
│ ├────────────────────────────────────────────┤  │
│ │                                            │  │
│ │ Handelsregisternummer:                     │  │
│ │ [HRB 12345_______________]                 │  │
│ │ ℹ️ z.B. "HRB 12345" (Amtsgericht XY)      │  │
│ │                                            │  │
│ │ Steuernummer:                              │  │
│ │ [26/123/12345____________]                 │  │
│ │                                            │  │
│ │ USt-IdNr. (bei EU-Lieferanten):            │  │
│ │ [DE123456789_____]  [Validieren ✓]        │  │
│ │ ℹ️ Wichtig für Reverse Charge             │  │
│ │                                            │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ Standard-Kategorie:                              │
│ [Telefon/Internet ▼]                             │
│ ℹ️ Wird bei Eingangsrechnungen vorgeschlagen    │
│                                                  │
│ Beschreibung / Anmerkungen: ⭐                   │
│ [____________________________________________]   │
│ [Hauptlieferant für Telefonanlage____________]   │
│ [Vertragsnummer: 123456789___________________]   │
│                                                  │
│ [Abbrechen]                    [Speichern]       │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

#### **📋 Templates für Lieferanten** ⭐ NEU (für später)

**Konzept:**
Branchenspezifische Vorlagen für Lieferanten-Felder

**Lieferanten-Templates:**

```python
# templates/lieferanten_templates.py
LIEFERANTEN_TEMPLATES = {
    'standard': {
        'name': 'Standard (Universal)',
        'felder': [
            'lieferantennummer', 'name',
            'strasse', 'plz', 'ort', 'land',
            'telefon', 'email', 'website',
            'kontaktperson_name', 'kontaktperson_telefon', 'kontaktperson_email',
            'handelsregisternummer', 'steuernummer', 'ust_idnr',
            'standard_kategorie_id', 'beschreibung'
        ],
        'pflicht': ['name']
    },

    'handwerk_material': {
        'name': 'Handwerk - Material-Lieferanten',
        'beschreibung': 'Für Handwerker: Baustoff, Werkzeug, Material',
        'felder': [
            'lieferantennummer', 'name',
            'strasse', 'hausnummer', 'plz', 'ort',  # Adresse wichtig (Abholung)
            'telefon', 'email', 'website',
            'kontaktperson_name', 'kontaktperson_telefon',  # Für Bestellungen
            'standard_kategorie_id',  # "Wareneinkauf"
            'beschreibung'  # "Lieferzeit 2-3 Tage", "Rabatt 5%"
        ],
        'pflicht': ['name', 'telefon'],
        'besonderheiten': [
            'Telefon Pflicht (für schnelle Bestellungen)',
            'Adresse wichtig (für Abholung)',
            'Kontaktperson für Bestellabwicklung'
        ]
    },

    'it_software': {
        'name': 'IT/Software - SaaS & Lizenzen',
        'beschreibung': 'Für Software-Abos, Cloud-Dienste, Lizenzen',
        'felder': [
            'lieferantennummer', 'name',
            'email', 'website',  # Nur Online-Kontakt
            'kontaktperson_name', 'kontaktperson_email',  # Support-Kontakt
            'ust_idnr',  # Oft EU-Anbieter
            'standard_kategorie_id',  # "Software/SaaS"
            'beschreibung'  # "Abo-Nr: 123456", "Kündigungsfrist: 3 Monate"
        ],
        'pflicht': ['name', 'email'],
        'besonderheiten': [
            'Adresse optional (nur Online)',
            'E-Mail Pflicht (Hauptkommunikation)',
            'Website wichtig (für Login/Support)',
            'Beschreibung für Abo-Details'
        ]
    },

    'buero_verbrauch': {
        'name': 'Bürobedarf & Verbrauchsmaterial',
        'beschreibung': 'Für Büromaterial, Druckerpatronen, etc.',
        'felder': [
            'lieferantennummer', 'name',
            'telefon', 'email', 'website',
            'kontaktperson_name', 'kontaktperson_telefon', 'kontaktperson_email',
            'standard_kategorie_id',  # "Bürobedarf"
            'beschreibung'  # "Kundennummer: K123456", "Lieferung ab 50€ frei"
        ],
        'pflicht': ['name', 'telefon'],
        'besonderheiten': [
            'Telefon/E-Mail für Bestellungen',
            'Adresse optional (Lieferung)',
            'Kontaktperson für Auftragsabwicklung'
        ]
    },

    'dienstleister_fixkosten': {
        'name': 'Dienstleister - Fixkosten',
        'beschreibung': 'Für Miete, Strom, Telefon, Versicherungen',
        'felder': [
            'lieferantennummer', 'name',
            'strasse', 'plz', 'ort',  # Für Schriftverkehr
            'telefon', 'email', 'website',
            'kontaktperson_name', 'kontaktperson_telefon',  # Ansprechpartner
            'ust_idnr',
            'standard_kategorie_id',  # "Raumkosten", "Telefon", etc.
            'beschreibung'  # "Vertragsnummer: 123456", "Kündigungsfrist: 31.12."
        ],
        'pflicht': ['name', 'standard_kategorie_id'],
        'besonderheiten': [
            'Standard-Kategorie Pflicht (für AutoBooking)',
            'Beschreibung für Vertragsdaten',
            'Kontaktperson für Vertragsanpassungen'
        ]
    },

    'wareneinkauf_grosshandel': {
        'name': 'Wareneinkauf - Großhändler',
        'beschreibung': 'Für Wiederverkäufer, Produzenten, Importeure',
        'felder': [
            'lieferantennummer', 'name',
            'strasse', 'hausnummer', 'plz', 'ort', 'land',
            'telefon', 'email', 'website',
            'kontaktperson_name', 'kontaktperson_telefon', 'kontaktperson_email',
            'handelsregisternummer',  # ⚠️ Wichtig für Verträge
            'steuernummer', 'ust_idnr',  # ⚠️ Wichtig für Vorsteuerabzug
            'standard_kategorie_id',  # "Wareneinkauf"
            'beschreibung'  # "Zahlungsziel: 30 Tage", "Mindestbestellwert: 500€"
        ],
        'pflicht': ['name', 'strasse', 'plz', 'ort', 'steuernummer'],
        'besonderheiten': [
            'Vollständige Adresse Pflicht',
            'Steuernummer Pflicht (für Vorsteuerabzug)',
            'Handelsregisternummer empfohlen',
            'USt-IdNr. bei EU-Lieferanten Pflicht (Reverse Charge)'
        ]
    },

    'freiberufler_subunternehmer': {
        'name': 'Freiberufler - Subunternehmer',
        'beschreibung': 'Für Freie Mitarbeiter, Subunternehmer, Dienstleister',
        'felder': [
            'lieferantennummer', 'name',
            'telefon', 'email',
            'kontaktperson_name',  # = Name (bei Einzelperson)
            'steuernummer',  # ⚠️ Wichtig für § 13b UStG
            'ust_idnr',
            'standard_kategorie_id',
            'beschreibung'  # "Stundensatz: 80€", "Spezialisierung: PHP"
        ],
        'pflicht': ['name', 'telefon', 'email', 'steuernummer'],
        'besonderheiten': [
            'Steuernummer Pflicht (für § 13b UStG - Reverse Charge Bau)',
            'Telefon/E-Mail für Abstimmung',
            'Beschreibung für Stundensatz/Konditionen'
        ]
    }
}


def get_lieferanten_template(branche: str) -> dict:
    """
    Gibt Template für Branche zurück

    Args:
        branche: 'standard', 'handwerk_material', 'it_software', etc.

    Returns:
        Template-Dict mit Feldern, Pflichtfeldern, Besonderheiten
    """
    return LIEFERANTEN_TEMPLATES.get(branche, LIEFERANTEN_TEMPLATES['standard'])
```

**UI - Template-Auswahl (Setup-Wizard):**

```
┌──────────────────────────────────────────────────┐
│ Setup-Wizard: Lieferanten-Arten                  │
├──────────────────────────────────────────────────┤
│                                                  │
│ Welche Art von Lieferanten hast du hauptsächlich?│
│ (Du kannst mehrere wählen)                       │
│                                                  │
│ ☑ Material-Lieferanten (Handwerk)                │
│   Baustoff, Werkzeug, Material                   │
│                                                  │
│ ☑ IT/Software (SaaS & Lizenzen)                  │
│   Software-Abos, Cloud-Dienste                   │
│                                                  │
│ ☐ Bürobedarf & Verbrauchsmaterial                │
│   Büromaterial, Druckerpatronen                  │
│                                                  │
│ ☑ Dienstleister - Fixkosten                      │
│   Miete, Strom, Telefon, Versicherungen          │
│                                                  │
│ ☐ Wareneinkauf - Großhändler                     │
│   Wiederverkäufer, Produzenten                   │
│                                                  │
│ ☐ Freiberufler - Subunternehmer                  │
│   Freie Mitarbeiter, Dienstleister               │
│                                                  │
│ ℹ️ Template passt Felder an deine Anforderungen!│
│                                                  │
│ [Zurück]                         [Weiter]        │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Vorteile:**
- ✅ **Fokussiert**: Nur relevante Felder für Lieferanten-Art
- ✅ **Geführt**: Pflichtfelder an Branche angepasst
- ✅ **Compliance**: § 13b UStG (Reverse Charge) bei Subunternehmern
- ✅ **Flexibel**: Mehrere Templates gleichzeitig nutzbar

**Status:** 🔜 **Für v2.0 geplant** (v1.0 nutzt "Standard"-Template)

---

#### **💻 Python-Modell** ⭐ NEU

```python
# models.py
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

@dataclass
class Lieferant:
    id: Optional[int] = None

    # Stammdaten
    lieferantennummer: Optional[str] = None  # "L-001" (auto)
    name: str = ''  # Pflichtfeld ⭐

    # Adresse
    strasse: Optional[str] = None
    hausnummer: Optional[str] = None
    plz: Optional[str] = None
    ort: Optional[str] = None
    land: str = 'DE'

    # Kontakt (Firma)
    telefon: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None

    # Kontaktperson ⭐ NEU
    kontaktperson_name: Optional[str] = None
    kontaktperson_telefon: Optional[str] = None
    kontaktperson_email: Optional[str] = None

    # Unternehmensdetails ⭐ NEU
    handelsregisternummer: Optional[str] = None
    steuernummer: Optional[str] = None

    # Steuerlich
    ust_idnr: Optional[str] = None

    # Standard-Kategorie
    standard_kategorie_id: Optional[int] = None

    # Metadaten
    beschreibung: Optional[str] = None  # ⭐ NEU
    erstellt_am: Optional[datetime] = None
    aktualisiert_am: Optional[datetime] = None

    # Statistiken
    anzahl_rechnungen: int = 0
    ausgaben_gesamt: Decimal = Decimal('0.00')
    letzte_rechnung_datum: Optional[date] = None

    @property
    def display_name(self) -> str:
        """
        Anzeigename für UI
        """
        if self.kontaktperson_name:
            return f"{self.name} ({self.kontaktperson_name})"
        return self.name

    def validate(self) -> list[str]:
        """
        Validiert Pflichtfelder
        """
        errors = []

        if not self.name:
            errors.append("Name ist Pflichtfeld")

        # USt-IdNr. bei EU-Lieferanten empfohlen (Reverse Charge)
        if self.land != 'DE' and self.land in EU_LAENDER and not self.ust_idnr:
            errors.append("Warnung: USt-IdNr. bei EU-Lieferanten empfohlen (für Reverse Charge)")

        # Steuernummer bei Subunternehmern Pflicht (§ 13b UStG)
        if self.standard_kategorie_id and self._ist_bau_dienstleistung():
            if not self.steuernummer:
                errors.append("Warnung: Steuernummer bei Bau-Dienstleistern Pflicht (§ 13b UStG)")

        return errors

    def _ist_bau_dienstleistung(self) -> bool:
        """
        Prüft ob Kategorie = Bau-Dienstleistung (für § 13b UStG)
        """
        # Implementierung hängt von Kategorien ab
        return False  # Placeholder
```

---

### **8.11 DSGVO-Compliance für Stammdaten** ⚠️ WICHTIG

**Gilt für:** Kundenstamm UND Lieferantenstamm

---

#### **🔐 Rechtsgrundlagen für Speicherung**

**Art. 6 Abs. 1 DSGVO - Rechtmäßigkeit der Verarbeitung:**

```
┌─────────────────────────────────────────────────┐
│ Warum dürfen wir Kundendaten speichern?        │
├─────────────────────────────────────────────────┤
│                                                 │
│ ✅ Art. 6 Abs. 1 lit. b DSGVO                  │
│    "Vertragserfüllung"                          │
│    → Rechnungsstellung erfordert Kundendaten   │
│                                                 │
│ ✅ Art. 6 Abs. 1 lit. c DSGVO                  │
│    "Rechtliche Verpflichtung"                   │
│    → §147 AO: Aufbewahrungspflicht 10 Jahre    │
│    → §257 HGB: Aufbewahrungspflicht 10 Jahre   │
│                                                 │
│ ✅ Art. 6 Abs. 1 lit. f DSGVO                  │
│    "Berechtigtes Interesse"                     │
│    → Kundenverwaltung für Geschäftszwecke      │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Wichtig:**
- **Keine Einwilligung erforderlich** (Art. 6 Abs. 1 lit. a) für Geschäftskunden
- **Aufbewahrungspflicht überwiegt Löschpflicht** während 10 Jahren
- **Danach: Löschpflicht** (Art. 17 DSGVO)

---

#### **⏰ Aufbewahrungsfristen & Löschkonzept**

**§147 AO & §257 HGB:**

```python
# Aufbewahrungsfristen
AUFBEWAHRUNGSFRISTEN = {
    'rechnungen': 10,  # Jahre (§147 Abs. 1 Nr. 1 AO)
    'belege': 10,      # Jahre (§147 Abs. 1 Nr. 4 AO)
    'buchhaltung': 10, # Jahre (§147 Abs. 1 Nr. 1 AO)
}

def berechne_aufbewahrung_bis(letzte_rechnung_datum: date) -> date:
    """
    Berechnet Ende der Aufbewahrungsfrist

    Regel: 10 Jahre ab Ende des Kalenderjahres der letzten Rechnung

    Beispiel:
    - Letzte Rechnung: 15.03.2024
    - Ende Kalenderjahr: 31.12.2024
    - Aufbewahrung bis: 31.12.2034 (10 Jahre später)
    """
    jahr_letzte_rechnung = letzte_rechnung_datum.year
    ende_kalenderjahr = date(jahr_letzte_rechnung, 12, 31)
    aufbewahrung_bis = date(jahr_letzte_rechnung + 10, 12, 31)

    return aufbewahrung_bis
```

**Konflikt: Aufbewahrungspflicht vs. Löschpflicht:**

```
Zeitstrahl:

2024        2025        ...        2034        2035
│           │                      │           │
│           │                      │           │
Rechnung    │                      │           Löschung
erstellt    │                      │           erlaubt!
            │                      │
            │<──── 10 Jahre ──────>│
            Aufbewahrungspflicht
```

**Lösung:**
1. **Während Aufbewahrungsfrist (10 Jahre):**
   - Daten NICHT löschen (§147 AO hat Vorrang)
   - Aber: **Zugriff einschränken** ("Sperrung")
   - Nur für Finanzamt/Prüfung zugänglich

2. **Nach Ablauf (nach 10 Jahren):**
   - **Automatische Löschung** (DSGVO Art. 17)
   - Oder: Anonymisierung

---

#### **📊 Datenbank-Schema mit DSGVO-Feldern**

```sql
-- Erweitert: kunden & lieferanten Tabellen
ALTER TABLE kunden ADD COLUMN gesperrt BOOLEAN DEFAULT 0;
ALTER TABLE kunden ADD COLUMN gesperrt_grund TEXT;  -- "Aufbewahrungspflicht", "Nutzer-Wunsch"
ALTER TABLE kunden ADD COLUMN gesperrt_am DATE;
ALTER TABLE kunden ADD COLUMN loesch_datum DATE;  -- Geplantes Löschdatum
ALTER TABLE kunden ADD COLUMN aufbewahrung_bis DATE;  -- Ende Aufbewahrungsfrist

ALTER TABLE lieferanten ADD COLUMN gesperrt BOOLEAN DEFAULT 0;
ALTER TABLE lieferanten ADD COLUMN gesperrt_grund TEXT;
ALTER TABLE lieferanten ADD COLUMN gesperrt_am DATE;
ALTER TABLE lieferanten ADD COLUMN loesch_datum DATE;
ALTER TABLE lieferanten ADD COLUMN aufbewahrung_bis DATE;

-- Audit-Log für DSGVO-Aktionen
CREATE TABLE dsgvo_log (
    id INTEGER PRIMARY KEY,

    -- Betroffene Person
    tabelle TEXT NOT NULL,  -- 'kunden' oder 'lieferanten'
    datensatz_id INTEGER NOT NULL,
    person_name TEXT,  -- Snapshot für Log

    -- Aktion
    aktion TEXT NOT NULL,  -- 'auskunft', 'berichtigung', 'loeschung', 'sperrung', 'export'
    durchgefuehrt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Details
    details TEXT,  -- JSON mit Details

    -- User (falls Multi-User in Zukunft)
    user_id INTEGER
);
```

---

#### **👤 Betroffenenrechte implementieren**

**Art. 15 DSGVO - Auskunftsrecht:**

```python
def dsgvo_auskunft(kunde_id: int) -> dict:
    """
    Gibt alle gespeicherten Daten über einen Kunden aus

    Returns:
        Dict mit allen Daten + Rechnungen
    """
    kunde = db.get_kunde(kunde_id)
    rechnungen = db.get_rechnungen_by_kunde(kunde_id)

    auskunft = {
        'stammdaten': {
            'kundennummer': kunde.kundennummer,
            'name': f"{kunde.vorname} {kunde.nachname}",
            'adresse': f"{kunde.strasse}, {kunde.plz} {kunde.ort}",
            'email': kunde.email,
            'telefon_mobil': kunde.telefon_mobil,
            'telefon_festnetz': kunde.telefon_festnetz,
            # ... alle Felder
        },
        'rechnungen': [
            {
                'rechnungsnummer': r.rechnungsnummer,
                'datum': r.datum,
                'betrag': r.betrag_brutto,
                'status': r.status
            }
            for r in rechnungen
        ],
        'statistiken': {
            'anzahl_rechnungen': kunde.anzahl_rechnungen,
            'umsatz_gesamt': kunde.umsatz_gesamt,
            'kunde_seit': kunde.erstellt_am,
        },
        'rechtsgrundlage': 'Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung)',
        'speicherdauer': f'Bis {kunde.aufbewahrung_bis} (§147 AO)',
    }

    # Audit-Log
    log_dsgvo_aktion('kunden', kunde_id, 'auskunft', auskunft)

    return auskunft
```

**UI - Auskunft generieren:**

```
┌──────────────────────────────────────────────────┐
│ 📄 DSGVO-Auskunft für Kunde                     │
├──────────────────────────────────────────────────┤
│                                                  │
│ Kunde: [Musterfrau, Erika ▼]                    │
│                                                  │
│ [Auskunft erstellen (PDF)]                      │
│                                                  │
│ ℹ️ Enthält alle gespeicherten Daten gemäß      │
│    Art. 15 DSGVO                                │
│                                                  │
└──────────────────────────────────────────────────┘

[Generiert PDF mit:]
- Stammdaten
- Rechnungen (Liste)
- Speicherzweck
- Rechtsgrundlage
- Speicherdauer
```

---

**Art. 16 DSGVO - Berichtigungsrecht:**

```python
def dsgvo_berichtigung(kunde_id: int, korrekturen: dict):
    """
    Korrigiert Kundendaten auf Wunsch

    Args:
        korrekturen: {'email': 'neu@beispiel.de', 'strasse': 'Neue Str. 1'}
    """
    kunde = db.get_kunde(kunde_id)

    # Alte Daten für Log speichern
    alte_daten = {k: getattr(kunde, k) for k in korrekturen.keys()}

    # Aktualisieren
    for feld, wert in korrekturen.items():
        setattr(kunde, feld, wert)

    kunde.aktualisiert_am = datetime.now()
    db.save(kunde)

    # Audit-Log
    log_dsgvo_aktion('kunden', kunde_id, 'berichtigung', {
        'alt': alte_daten,
        'neu': korrekturen
    })
```

---

**Art. 17 DSGVO - Recht auf Löschung:**

```python
def dsgvo_loeschung(kunde_id: int, grund: str = 'nutzer_wunsch'):
    """
    Löscht Kundendaten (mit Aufbewahrungspflicht-Check)

    Args:
        grund: 'nutzer_wunsch', 'frist_abgelaufen'
    """
    kunde = db.get_kunde(kunde_id)

    # Prüfung: Aufbewahrungspflicht?
    heute = date.today()
    if kunde.aufbewahrung_bis and kunde.aufbewahrung_bis > heute:
        # Noch in Aufbewahrungsfrist → NICHT löschen!
        raise ValueError(
            f"Löschung nicht möglich: Aufbewahrungspflicht bis {kunde.aufbewahrung_bis} "
            f"(§147 AO). Kunde wird stattdessen gesperrt."
        )

    # Löschung durchführen
    if grund == 'nutzer_wunsch':
        # Nutzer will Löschung → Sperrung statt Löschung
        kunde.gesperrt = True
        kunde.gesperrt_grund = 'Nutzer-Wunsch (DSGVO Art. 17)'
        kunde.gesperrt_am = heute
        kunde.loesch_datum = kunde.aufbewahrung_bis  # Löschung nach Frist
        db.save(kunde)

        log_dsgvo_aktion('kunden', kunde_id, 'sperrung', {
            'grund': grund,
            'loesch_datum': kunde.loesch_datum
        })

        return f"Kunde gesperrt. Automatische Löschung am {kunde.loesch_datum}."

    elif grund == 'frist_abgelaufen':
        # Frist abgelaufen → Endgültige Löschung

        # Option 1: Vollständige Löschung
        db.delete_kunde(kunde_id)

        # Option 2: Anonymisierung (besser für Statistiken)
        # kunde.vorname = 'GELÖSCHT'
        # kunde.nachname = 'GELÖSCHT'
        # kunde.email = None
        # kunde.telefon_mobil = None
        # ...
        # db.save(kunde)

        log_dsgvo_aktion('kunden', kunde_id, 'loeschung', {
            'grund': grund
        })

        return "Kunde gelöscht."
```

**UI - Löschung beantragen:**

```
┌──────────────────────────────────────────────────┐
│ 🗑️ Kundendaten löschen                          │
├──────────────────────────────────────────────────┤
│                                                  │
│ Kunde: Erika Musterfrau (K-042)                 │
│                                                  │
│ ⚠️ WARNUNG:                                     │
│ Dieser Kunde hat noch Rechnungen!               │
│                                                  │
│ Letzte Rechnung: 15.03.2024 (RE-2024-123)       │
│ Aufbewahrungspflicht bis: 31.12.2034            │
│                                                  │
│ ❌ Löschung NICHT möglich (§147 AO)             │
│                                                  │
│ ✅ Stattdessen: Kunde sperren                   │
│    → Nicht mehr in Suche/Auswahl sichtbar       │
│    → Automatische Löschung am 31.12.2034        │
│                                                  │
│ [Abbrechen]          [Kunde sperren]            │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

**Art. 20 DSGVO - Datenportabilität:**

```python
def dsgvo_export(kunde_id: int) -> str:
    """
    Exportiert Kundendaten in maschinenlesbarem Format

    Returns:
        JSON-String mit allen Daten
    """
    kunde = db.get_kunde(kunde_id)
    rechnungen = db.get_rechnungen_by_kunde(kunde_id)

    export_data = {
        'stammdaten': {
            'kundennummer': kunde.kundennummer,
            'typ': kunde.typ,
            'vorname': kunde.vorname,
            'nachname': kunde.nachname,
            # ... alle Felder
        },
        'rechnungen': [
            {
                'rechnungsnummer': r.rechnungsnummer,
                'datum': r.datum.isoformat(),
                'betrag_netto': str(r.betrag_netto),
                'betrag_brutto': str(r.betrag_brutto),
                # ... alle Felder
            }
            for r in rechnungen
        ],
        'export_datum': datetime.now().isoformat(),
        'format_version': '1.0'
    }

    json_export = json.dumps(export_data, indent=2, ensure_ascii=False)

    log_dsgvo_aktion('kunden', kunde_id, 'export', {'format': 'JSON'})

    return json_export
```

---

#### **🔗 Löschstrategie für verknüpfte Daten (Rechnungen)** ⚠️ **KRITISCH**

**Problem:**
- Kunde verlangt Löschung seiner Daten (Art. 17 DSGVO)
- ABER: Rechnungen müssen 10 Jahre aufbewahrt werden (§147 AO)
- **Konflikt:** Kundendaten sind in Rechnungen enthalten!

**Frage:** Was passiert mit den Kundendaten in Rechnungen, wenn der Kunde gelöscht wird?

---

##### **Rechtsgrundlage: Ausnahme vom Löschrecht**

**Art. 17 Abs. 3 lit. b DSGVO:**

```
Das Recht auf Löschung besteht NICHT, soweit die Verarbeitung
erforderlich ist zur Erfüllung einer rechtlichen Verpflichtung.
```

**§147 AO & §257 HGB:**
- 10-jährige Aufbewahrungspflicht für Rechnungen
- Rechnung muss **vollständig nachvollziehbar** sein
- Kundendaten (Name, Adresse, etc.) sind **Teil der Rechnung**

**Ergebnis:**
- ✅ **Kundendaten in Rechnungen DÜRFEN gespeichert bleiben** (auch nach Löschantrag)
- ❌ **Kundenstammdaten MÜSSEN gesperrt werden** (bis Frist abläuft)

---

##### **Lösung: Denormalisierung der Kundendaten**

**Strategie:**
1. **Rechnungen enthalten KOPIE der Kundendaten** (nicht Foreign Key)
2. **Kundenstamm wird gesperrt/pseudonymisiert** (bei Löschantrag)
3. **Rechnungen bleiben unverändert** (Aufbewahrungspflicht)

**Datenbank-Design:**

```sql
-- ❌ FALSCH: Foreign Key (führt zu Problemen bei Löschung)
CREATE TABLE rechnungen (
    id INTEGER PRIMARY KEY,
    kunde_id INTEGER,  -- ❌ Foreign Key → Kunde kann nicht gelöscht werden!
    FOREIGN KEY (kunde_id) REFERENCES kunden(id)
);

-- ✅ RICHTIG: Denormalisierte Kundendaten
CREATE TABLE rechnungen (
    id INTEGER PRIMARY KEY,
    rechnungsnummer TEXT UNIQUE,
    datum DATE,

    -- ═══════════════════════════════════════════════════
    -- KUNDENDATEN (KOPIE ZUM ZEITPUNKT DER RECHNUNG)
    -- ═══════════════════════════════════════════════════

    -- Optional: Referenz auf Kundenstamm (für Statistiken)
    -- Wird NULL gesetzt, wenn Kunde gelöscht wird
    kunde_id INTEGER,  -- Optional, kann NULL sein

    -- Kundendaten (denormalisiert, immer gespeichert)
    kunde_typ TEXT,  -- 'privat', 'firma'

    -- Person
    kunde_anrede TEXT,
    kunde_vorname TEXT,
    kunde_nachname TEXT,

    -- Firma
    kunde_firmenname TEXT,
    kunde_rechtsform TEXT,

    -- Adresse (PFLICHT für Rechnung)
    kunde_strasse TEXT NOT NULL,
    kunde_hausnummer TEXT,
    kunde_plz TEXT NOT NULL,
    kunde_ort TEXT NOT NULL,
    kunde_land TEXT DEFAULT 'DE',

    -- Kontakt
    kunde_email TEXT,
    kunde_telefon TEXT,
    kunde_website TEXT,

    -- Steuerlich
    kunde_steuernummer TEXT,
    kunde_ust_idnr TEXT,

    -- ═══════════════════════════════════════════════════
    -- RECHNUNGSDATEN
    -- ═══════════════════════════════════════════════════

    betrag_netto DECIMAL(10,2),
    betrag_brutto DECIMAL(10,2),
    -- ... weitere Felder

    -- Foreign Key (optional, kann NULL sein)
    FOREIGN KEY (kunde_id) REFERENCES kunden(id) ON DELETE SET NULL
    --                                              ^^^^^^^^^^^^^^^^^
    --                                              Bei Löschung: kunde_id → NULL
    --                                              Kundendaten bleiben erhalten!
);
```

**Wichtig:**
- `kunde_id` ist **OPTIONAL** (nur für Statistiken, Verknüpfung mit Kundenstamm)
- `kunde_*` Felder sind **DENORMALISIERT** (immer ausgefüllt, auch wenn `kunde_id` NULL)
- Bei Löschung: `kunde_id` wird `NULL`, aber `kunde_name`, `kunde_adresse` etc. bleiben!

---

##### **Workflow: Kunde will Löschung**

**Szenario:**
1. Kunde "Erika Musterfrau" (ID 42) verlangt Löschung (Art. 17 DSGVO)
2. Letzte Rechnung: 15.03.2024 (RE-2024-123)
3. Aufbewahrungspflicht bis: 31.12.2034

**Schritt 1: Prüfung**

```python
def kunde_loeschen(kunde_id: int):
    kunde = db.get_kunde(kunde_id)
    rechnungen = db.get_rechnungen_by_kunde(kunde_id)

    # Prüfung: Hat Kunde Rechnungen?
    if rechnungen:
        letzte_rechnung = max(rechnungen, key=lambda r: r.datum)
        aufbewahrung_bis = berechne_aufbewahrung_bis(letzte_rechnung.datum)

        if aufbewahrung_bis > date.today():
            # Aufbewahrungspflicht noch aktiv
            raise ValueError(
                f"Löschung nicht möglich: Aufbewahrungspflicht bis {aufbewahrung_bis} (§147 AO)\n"
                f"Kunde wird stattdessen gesperrt."
            )
```

**Schritt 2: Sperrung im Kundenstamm**

```python
    # Kundenstamm sperren
    kunde.gesperrt = True
    kunde.gesperrt_grund = 'DSGVO Art. 17 - Löschantrag vom ' + str(date.today())
    kunde.gesperrt_am = date.today()
    kunde.loesch_datum = aufbewahrung_bis

    # Optional: Pseudonymisierung für zusätzlichen Schutz
    kunde.email = None
    kunde.telefon_mobil = None
    kunde.telefon_festnetz = None
    kunde.website = None
    kunde.notizen = '[GESPERRT - DSGVO]'

    db.save(kunde)

    log_dsgvo_aktion('kunden', kunde_id, 'sperrung', {
        'grund': 'Löschantrag',
        'loesch_datum': aufbewahrung_bis,
        'anzahl_rechnungen': len(rechnungen)
    })
```

**Schritt 3: Rechnungen bleiben unverändert**

```python
    # Rechnungen NICHT ändern!
    # - kunde_id bleibt erhalten (oder wird NULL gesetzt, je nach Design)
    # - kunde_name, kunde_adresse etc. bleiben IMMER erhalten (denormalisiert)

    # Optional: kunde_id auf NULL setzen (Verknüpfung trennen)
    db.execute("""
        UPDATE rechnungen
        SET kunde_id = NULL
        WHERE kunde_id = ?
    """, (kunde_id,))

    # WICHTIG: Kundendaten (kunde_name, kunde_adresse etc.) bleiben!
```

**Ergebnis:**
- ✅ **Kundenstamm**: Gesperrt, nicht mehr sichtbar, optional pseudonymisiert
- ✅ **Rechnungen**: Unverändert, alle Kundendaten erhalten
- ✅ **Compliance**: Aufbewahrungspflicht erfüllt, Löschrecht respektiert

---

##### **Alternative Strategien**

**Strategie 1: Vollständige Denormalisierung (empfohlen)**

```sql
-- Rechnungen enthalten ALLE Kundendaten (keine kunde_id)
CREATE TABLE rechnungen (
    id INTEGER PRIMARY KEY,
    -- Kundendaten (vollständig denormalisiert)
    kunde_typ TEXT,
    kunde_name TEXT,
    kunde_adresse TEXT,
    -- ... alle relevanten Felder
    -- KEIN kunde_id Foreign Key!
);
```

**Vorteile:**
- ✅ Keine Abhängigkeit zum Kundenstamm
- ✅ Kunde kann vollständig gelöscht werden (nach Frist)
- ✅ Rechnung bleibt immer nachvollziehbar

**Nachteile:**
- ❌ Keine Statistiken pro Kunde möglich (nach Löschung)
- ❌ Mehr Speicherplatz

---

**Strategie 2: Foreign Key mit ON DELETE SET NULL (hybrid)**

```sql
CREATE TABLE rechnungen (
    id INTEGER PRIMARY KEY,
    kunde_id INTEGER,  -- Optional (für Statistiken)
    -- Kundendaten (denormalisiert, immer ausgefüllt)
    kunde_name TEXT NOT NULL,
    kunde_adresse TEXT NOT NULL,
    -- ...
    FOREIGN KEY (kunde_id) REFERENCES kunden(id) ON DELETE SET NULL
);
```

**Vorteile:**
- ✅ Statistiken pro Kunde möglich (solange Kunde existiert)
- ✅ Rechnung bleibt nachvollziehbar (auch nach Löschung)
- ✅ kunde_id optional, Kundendaten immer da

**Nachteile:**
- ⚠️ Komplexer (zwei Datenquellen: kunde_id + denormalisierte Felder)

---

**Strategie 3: Pseudonymisierung (NICHT empfohlen für Rechnungen!)**

```python
# ❌ NICHT empfohlen für Rechnungen!
def pseudonymisiere_kunde(kunde_id: int):
    kunde = db.get_kunde(kunde_id)
    kunde.vorname = f"KUNDE-{kunde_id}"
    kunde.nachname = "GELÖSCHT"
    kunde.email = f"geloescht-{kunde_id}@example.com"
    kunde.telefon_mobil = None
    # ...
    db.save(kunde)
```

**Problem:**
- ❌ Rechnung nicht mehr nachvollziehbar (Name geändert)
- ❌ Finanzamt könnte Bedenken haben (Manipulation?)
- ❌ Nicht GoBD-konform (Unveränderbarkeit)

**Nur verwenden für:**
- ✅ Kundenstamm (nach Sperrung)
- ❌ NICHT für Rechnungen!

---

##### **Empfohlene Implementierung**

**Datenbank-Schema:**

```sql
-- Strategie 2: Hybrid (Foreign Key + Denormalisierung)

CREATE TABLE rechnungen (
    id INTEGER PRIMARY KEY,
    rechnungsnummer TEXT UNIQUE,
    datum DATE,

    -- OPTIONAL: Referenz auf Kundenstamm (für Statistiken, kann NULL werden)
    kunde_id INTEGER,

    -- PFLICHT: Denormalisierte Kundendaten (immer ausgefüllt)
    kunde_typ TEXT NOT NULL,
    kunde_anrede TEXT,
    kunde_vorname TEXT,
    kunde_nachname TEXT,
    kunde_firmenname TEXT,
    kunde_strasse TEXT NOT NULL,
    kunde_hausnummer TEXT,
    kunde_plz TEXT NOT NULL,
    kunde_ort TEXT NOT NULL,
    kunde_land TEXT DEFAULT 'DE',
    kunde_email TEXT,
    kunde_telefon TEXT,
    kunde_ust_idnr TEXT,

    -- ... Rechnungsdaten

    FOREIGN KEY (kunde_id) REFERENCES kunden(id) ON DELETE SET NULL
);
```

**Rechnung erstellen:**

```python
def erstelle_rechnung(kunde_id: int, positionen: list):
    kunde = db.get_kunde(kunde_id)

    # Kundendaten KOPIEREN (denormalisieren)
    rechnung = Rechnung(
        kunde_id=kunde_id,  # Optional, für Statistiken

        # Kundendaten zum Zeitpunkt der Rechnungserstellung
        kunde_typ=kunde.typ,
        kunde_anrede=kunde.anrede,
        kunde_vorname=kunde.vorname,
        kunde_nachname=kunde.nachname,
        kunde_firmenname=kunde.firmenname,
        kunde_strasse=kunde.strasse,
        kunde_hausnummer=kunde.hausnummer,
        kunde_plz=kunde.plz,
        kunde_ort=kunde.ort,
        kunde_land=kunde.land,
        kunde_email=kunde.email,
        kunde_telefon=kunde.telefon_mobil or kunde.telefon_festnetz,
        kunde_ust_idnr=kunde.ust_idnr,

        # ... Rechnungspositionen
    )

    db.save(rechnung)
    return rechnung
```

**Kunde löschen (nach Frist):**

```python
def loesche_kunde_nach_frist(kunde_id: int):
    # Prüfung: Frist abgelaufen?
    kunde = db.get_kunde(kunde_id)
    if kunde.aufbewahrung_bis > date.today():
        raise ValueError("Aufbewahrungsfrist noch nicht abgelaufen!")

    # 1. kunde_id in Rechnungen auf NULL setzen
    db.execute("UPDATE rechnungen SET kunde_id = NULL WHERE kunde_id = ?", (kunde_id,))

    # 2. Kundenstamm löschen
    db.delete_kunde(kunde_id)

    # 3. Audit-Log
    log_dsgvo_aktion('kunden', kunde_id, 'loeschung', {
        'grund': 'Aufbewahrungsfrist abgelaufen'
    })

    # WICHTIG: Kundendaten in Rechnungen bleiben erhalten!
    # (kunde_typ, kunde_name, kunde_adresse etc. sind denormalisiert)
```

---

##### **UI: Löschantrag mit Warnung**

```
┌──────────────────────────────────────────────────────────────┐
│ 🗑️ Kundendaten löschen - DSGVO Art. 17                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Kunde: Erika Musterfrau (K-042)                             │
│                                                              │
│ ⚠️ WICHTIG: Dieser Kunde hat Rechnungen!                   │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ 📋 VERKNÜPFTE DATEN                                  │   │
│ ├──────────────────────────────────────────────────────┤   │
│ │ Anzahl Rechnungen: 15                                │   │
│ │ Letzte Rechnung: 15.03.2024 (RE-2024-123)           │   │
│ │ Aufbewahrungspflicht bis: 31.12.2034                │   │
│ │                                                      │   │
│ │ ℹ️ Was passiert mit den Rechnungen?                 │   │
│ │                                                      │   │
│ │ ✅ Rechnungen bleiben erhalten (§147 AO)            │   │
│ │    - Kundendaten in Rechnung: UNVERÄNDERT           │   │
│ │    - Name, Adresse bleiben gespeichert              │   │
│ │                                                      │   │
│ │ ⚠️ Kundenstamm wird gesperrt:                       │   │
│ │    - Nicht mehr in Suche sichtbar                   │   │
│ │    - Kann nicht mehr bearbeitet werden              │   │
│ │    - E-Mail/Telefon werden gelöscht (optional)      │   │
│ │    - Automatische Löschung: 31.12.2034              │   │
│ │                                                      │   │
│ │ 📋 Rechtsgrundlage:                                  │   │
│ │ Art. 17 Abs. 3 lit. b DSGVO - Ausnahme vom          │   │
│ │ Löschrecht bei rechtlicher Aufbewahrungspflicht     │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                              │
│ Optionen:                                                    │
│                                                              │
│ ○ Kundenstamm sperren (empfohlen)                          │
│   Daten werden gesperrt, aber nicht gelöscht.              │
│   Automatische Löschung nach Fristablauf.                  │
│                                                              │
│ ○ Kundenstamm sperren + E-Mail/Telefon löschen             │
│   Zusätzlicher Schutz durch Pseudonymisierung.             │
│   Rechnungen bleiben vollständig erhalten.                 │
│                                                              │
│ ☐ Kunde über Sperrung informieren (E-Mail)                 │
│                                                              │
│ [Abbrechen]                         [Kunde sperren]         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

##### **Zusammenfassung**

**Problem:**
Kunde will Löschung, aber Rechnungen müssen 10 Jahre aufbewahrt werden.

**Lösung:**
1. ✅ **Denormalisierung**: Kundendaten werden in Rechnung kopiert
2. ✅ **Sperrung**: Kundenstamm wird gesperrt (nicht gelöscht)
3. ✅ **Rechtsgrundlage**: Art. 17 Abs. 3 lit. b DSGVO (Ausnahme vom Löschrecht)
4. ✅ **Automatische Löschung**: Nach Ablauf der 10-Jahres-Frist

**Datenbank-Design:**
- `rechnungen.kunde_id` → `ON DELETE SET NULL` (optional, für Statistiken)
- `rechnungen.kunde_*` → Denormalisierte Kundendaten (immer ausgefüllt)

**Compliance:**
- ✅ DSGVO Art. 17 (Löschrecht) → Kundenstamm gesperrt
- ✅ §147 AO (Aufbewahrungspflicht) → Rechnungen bleiben erhalten
- ✅ GoBD (Unveränderbarkeit) → Rechnungen werden nicht geändert

---

#### **🤖 Automatische Löschung (Cron-Job)**

```python
# tasks/dsgvo_cleanup.py
def automatische_loeschung():
    """
    Wird täglich ausgeführt (Cron-Job)

    Löscht Kunden/Lieferanten deren Aufbewahrungsfrist abgelaufen ist
    """
    heute = date.today()

    # Kunden mit abgelaufener Frist finden
    zu_loeschen = db.execute("""
        SELECT id, name FROM kunden
        WHERE loesch_datum IS NOT NULL
        AND loesch_datum <= ?
        AND gesperrt = 1
    """, (heute,)).fetchall()

    for kunde_id, name in zu_loeschen:
        print(f"Lösche Kunde {name} (ID: {kunde_id})...")

        try:
            dsgvo_loeschung(kunde_id, grund='frist_abgelaufen')
            print(f"✅ Gelöscht: {name}")
        except Exception as e:
            print(f"❌ Fehler bei {name}: {e}")

    # Gleiches für Lieferanten
    # ...

    print(f"Automatische Löschung abgeschlossen: {len(zu_loeschen)} Datensätze gelöscht")


# Cron-Eintrag (täglich 02:00 Uhr)
# 0 2 * * * cd /pfad/zu/rechnungspilot && python tasks/dsgvo_cleanup.py
```

---

#### **🔒 Technische & Organisatorische Maßnahmen (TOM)**

**Verschlüsselung:**

```python
# config.py
DATENBANK_VERSCHLUESSELUNG = True  # SQLCipher aktivieren

# Bei SQLite-Verbindung:
import sqlcipher3
conn = sqlcipher3.connect('rechnungspilot.db')
conn.execute(f"PRAGMA key = '{MASTER_PASSWORD}'")
```

**Zugriffskontrolle:**

```python
# Nur gesperrte Kunden für Finanzamt sichtbar
def get_kunden_fuer_anzeige(include_gesperrt: bool = False):
    """
    Gibt Kunden zurück (ohne gesperrte, außer explizit gewünscht)
    """
    query = "SELECT * FROM kunden"
    if not include_gesperrt:
        query += " WHERE gesperrt = 0"

    return db.execute(query).fetchall()


# UI zeigt gesperrte Kunden NICHT in Autocomplete
```

**Audit-Logging:**

```python
def log_dsgvo_aktion(tabelle: str, datensatz_id: int, aktion: str, details: dict):
    """
    Loggt DSGVO-relevante Aktionen
    """
    db.execute("""
        INSERT INTO dsgvo_log (tabelle, datensatz_id, aktion, details)
        VALUES (?, ?, ?, ?)
    """, (tabelle, datensatz_id, aktion, json.dumps(details)))

    db.commit()
```

---

#### **📋 DSGVO-Checkliste für Setup**

```
┌──────────────────────────────────────────────────┐
│ ✅ DSGVO-Checkliste                             │
├──────────────────────────────────────────────────┤
│                                                  │
│ ☑ Datenschutzerklärung erstellt                 │
│   (siehe datenschutz.md)                         │
│                                                  │
│ ☑ Verarbeitungsverzeichnis geführt              │
│   (Art. 30 DSGVO)                                │
│                                                  │
│ ☑ Aufbewahrungsfristen implementiert            │
│   (§147 AO: 10 Jahre)                            │
│                                                  │
│ ☑ Automatische Löschung konfiguriert            │
│   (Cron-Job täglich 02:00 Uhr)                   │
│                                                  │
│ ☑ Datenbank verschlüsselt                       │
│   (SQLCipher aktiviert)                          │
│                                                  │
│ ☑ Backup verschlüsselt                          │
│   (Nextcloud mit Verschlüsselung)                │
│                                                  │
│ ☑ Audit-Logging aktiviert                       │
│   (dsgvo_log Tabelle)                            │
│                                                  │
│ ☐ Datenschutz-Folgenabschätzung (DSFA)          │
│   (Bei > 250 Mitarbeitern oder sensiblen Daten) │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

#### **📄 Datenschutzerklärung (Vorlage)**

```markdown
# Datenschutzerklärung - RechnungsFee

