## **Kategorie 7: Einnahmen-Überschuss-Rechnung (EÜR)**

### **7.1 Was ist die EÜR?**

Die **Einnahmen-Überschuss-Rechnung (EÜR)** ist eine vereinfachte Form der Gewinnermittlung:

**Grundformel:**
```
Gewinn = Betriebseinnahmen - Betriebsausgaben
```

**Rechtliche Grundlage:**
- § 4 Abs. 3 EStG (Einkommensteuergesetz)
- **Anlage EÜR** zur Einkommensteuererklärung
- Nur für nicht-buchführungspflichtige Unternehmen

**Wer muss EÜR erstellen?**

✅ **Pflicht für:**
- Freiberufler (§ 18 EStG) - Ärzte, Anwälte, Künstler, IT-Berater, etc.
- Kleingewerbetreibende mit:
  - Gewinn < 60.000 € pro Jahr UND
  - Umsatz < 600.000 € pro Jahr
- Land- und Forstwirte (unter bestimmten Grenzen)

❌ **NICHT für:**
- Kapitalgesellschaften (GmbH, AG, UG) → Bilanzierung Pflicht
- Personengesellschaften über Grenzen (OHG, KG) → Bilanzierung Pflicht
- Kleinunternehmer (§ 19 UStG) → EÜR optional, aber empfohlen

**Abgabefrist:**
- Mit Einkommensteuererklärung
- Ohne Steuerberater: 31. Juli des Folgejahres (für 2025 → 31.07.2026)
- Mit Steuerberater: 28. Februar übernächstes Jahr (für 2025 → 28.02.2027)

---

### **7.2 Zufluss-/Abfluss-Prinzip**

**Entscheidend ist WANN das Geld geflossen ist, nicht das Rechnungsdatum!**

#### **Beispiel Einnahmen:**

| Rechnung geschrieben | Zahlung erhalten | EÜR-Jahr |
|---------------------|------------------|----------|
| 15.12.2025 | 10.01.2026 | **2026** (Zufluss) |
| 20.11.2025 | 28.12.2025 | **2025** (Zufluss) |

#### **Beispiel Ausgaben:**

| Rechnung erhalten | Zahlung geleistet | EÜR-Jahr |
|-------------------|-------------------|----------|
| 05.12.2025 | 15.01.2026 | **2026** (Abfluss) |
| 10.12.2025 | 20.12.2025 | **2025** (Abfluss) |

**Wichtig:**
- ✅ Zufluss-/Abfluss-Prinzip = **Ist-Versteuerung** (identisch!)
- ✅ SGBII-konform (siehe Kategorie 6.5)
- ✅ Einfacher für Einsteiger (nur bezahlte Rechnungen zählen)

**Ausnahmen:**
- **Regelmäßige Zahlungen** (z.B. Miete, Versicherungen) → 10-Tage-Regel:
  - Zahlung zwischen 22.12.-10.01. → User wählt Jahr
- **Abschreibungen (AfA):** Nicht nach Zahlung, sondern nach Nutzungsdauer

---

### **7.2.1 Automatische Zuordnung & Warnungen (Frage 7.4)**

#### **Automatische Buchung nach Zahlungsdatum**

**Antwort: Ja, RechnungsFee bucht automatisch nach Zahlungsdatum (nicht Rechnungsdatum).**

**Technische Umsetzung:**

```python
def calculate_euer_jahr(rechnung):
    """
    Bestimmt EÜR-Jahr basierend auf Zahlungsdatum (Zufluss-/Abfluss-Prinzip)
    """
    if rechnung.zahlungsdatum:
        # Zufluss-/Abfluss-Prinzip: Zahlungsdatum zählt
        return rechnung.zahlungsdatum.year
    else:
        # Rechnung noch nicht bezahlt → Kein EÜR-Jahr
        return None


# Beispiel:
rechnung = Rechnung(
    rechnungsdatum='2025-12-15',
    zahlungsdatum='2026-01-10',  # Zahlung im neuen Jahr
    betrag=1000.00
)

euer_jahr = calculate_euer_jahr(rechnung)  # → 2026 (nicht 2025!)
```

**UI-Verhalten:**

```
┌──────────────────────────────────────────┐
│ Ausgangsrechnung                         │
├──────────────────────────────────────────┤
│                                          │
│ Rechnungsdatum: [15.12.2025]            │
│ Zahlungsdatum:  [10.01.2026]            │
│                                          │
│ ℹ️ EÜR-Jahr: 2026                        │
│    (Zufluss-Prinzip: Zahlungsdatum zählt)│
│                                          │
│ Betrag: 1.000,00 €                       │
│                                          │
│    [ Speichern ]                         │
└──────────────────────────────────────────┘
```

**Filter in EÜR-Berechnung:**

```python
def get_ausgangsrechnungen_fuer_euer(jahr):
    """
    Holt Ausgangsrechnungen für EÜR (nach Zahlungsdatum!)
    """
    return db.query(Ausgangsrechnung).filter(
        Ausgangsrechnung.zahlungsdatum >= f'{jahr}-01-01',
        Ausgangsrechnung.zahlungsdatum <= f'{jahr}-12-31',
        Ausgangsrechnung.status == 'bezahlt'  # Nur bezahlte!
    ).all()

# NICHT nach Rechnungsdatum filtern!
# ❌ FALSCH: Ausgangsrechnung.rechnungsdatum
# ✅ RICHTIG: Ausgangsrechnung.zahlungsdatum
```

---

#### **Hinweise bei Jahresübergang (Rechnung & Zahlung in verschiedenen Jahren)**

**Antwort: Ja, RechnungsFee warnt proaktiv bei Jahresübergang.**

**Wann wird gewarnt?**

| Rechnungsdatum | Zahlungsdatum | Warnung? | Grund |
|----------------|---------------|----------|-------|
| 15.11.2025 | 28.11.2025 | ❌ Nein | Beide im selben Jahr |
| 15.12.2025 | 10.01.2026 | ✅ Ja | Jahresübergang → EÜR-Jahr ändert sich |
| 20.12.2025 | 28.12.2025 | ⚠️ Optional | Jahresende-Warnung (siehe unten) |

**Warnung bei Jahresübergang:**

```
┌──────────────────────────────────────────┐
│ ⚠️ Jahresübergang: EÜR-Jahr beachten!    │
├──────────────────────────────────────────┤
│                                          │
│ Ausgangsrechnung: RE-2025-042            │
│ Rechnungsdatum: 15.12.2025               │
│ Zahlungsdatum:  10.01.2026               │
│                                          │
│ ⚠️ Rechnung wurde 2025 geschrieben,      │
│    aber Zahlung erfolgt 2026.            │
│                                          │
│ Zufluss-Prinzip (EÜR):                   │
│ → Einnahme zählt für EÜR 2026 (nicht 2025)│
│                                          │
│ Das ist steuerlich korrekt!              │
│ Nur zur Info, falls unerwartet.          │
│                                          │
│              [ Verstanden ]              │
└──────────────────────────────────────────┘
```

**Warnung direkt beim Zahlungseingabe:**

```
┌──────────────────────────────────────────┐
│ Zahlung erfassen                         │
├──────────────────────────────────────────┤
│                                          │
│ Rechnung: RE-2025-042                    │
│ Rechnungsdatum: 15.12.2025               │
│                                          │
│ Zahlungsdatum: [10.01.2026____]          │
│                                          │
│ ⚠️ Achtung: Zahlung im neuen Jahr!       │
│    → EÜR-Jahr: 2026 (nicht 2025)        │
│                                          │
│ Betrag: [1.000,00___] €                  │
│                                          │
│    [Abbrechen]  [ Speichern ]            │
└──────────────────────────────────────────┘
```

---

#### **Jahresende-Warnung (Dezember-Zahlungen)**

**Problem:** User könnte vergessen, Dezember-Zahlungen rechtzeitig zu erfassen.

**Lösung:** Automatische Erinnerung im Januar.

```
┌──────────────────────────────────────────┐
│ ℹ️ Jahresabschluss 2025: Offene Rechnungen│
├──────────────────────────────────────────┤
│                                          │
│ Es gibt 3 unbezahlte Rechnungen aus 2025:│
│                                          │
│ • RE-2025-038 (15.11.25) - 500 €        │
│ • RE-2025-040 (01.12.25) - 750 €        │
│ • RE-2025-042 (15.12.25) - 1.000 €      │
│                                          │
│ Fragen:                                  │
│ 1. Wurden diese in 2025 bezahlt?         │
│    → Zahlungsdatum nachtragen            │
│                                          │
│ 2. Wurden diese in 2026 bezahlt?         │
│    → EÜR 2026 (Zufluss-Prinzip)         │
│                                          │
│ 💡 Tipp: Prüfe Kontoauszüge Dez 2025!    │
│                                          │
│    [Später]  [ Rechnungen prüfen ]       │
└──────────────────────────────────────────┘
```

**Zeitpunkt der Warnung:**

- ✅ Anfang Januar (z.B. ab 05.01.2026)
- ✅ Vor EÜR-Export für Vorjahr
- ✅ Bei EÜR-Berechnung für Vorjahr

---

#### **10-Tage-Regel für regelmäßige Zahlungen**

**Rechtslage:** Regelmäßige Zahlungen (Miete, Versicherung, Abos) zwischen 22.12. und 10.01. können dem alten oder neuen Jahr zugeordnet werden.

**UI-Dialog:**

```
┌──────────────────────────────────────────┐
│ 10-Tage-Regel: Jahr wählen               │
├──────────────────────────────────────────┤
│                                          │
│ Eingangsrechnung: Büromiete Januar 2026  │
│ Zahlungsdatum: 28.12.2025                │
│ Betrag: 500,00 €                         │
│                                          │
│ ℹ️ Regelmäßige Zahlung im Zeitraum       │
│    22.12. - 10.01. → Wahlrecht           │
│                                          │
│ EÜR-Jahr:                                │
│ ○ 2025 (Zahlung vor Jahreswechsel)      │
│ ● 2026 (wirtschaftlich zu Januar gehörig)│
│                                          │
│ 💡 Empfehlung: 2026 (Miete für Januar)   │
│                                          │
│    [Abbrechen]  [ Speichern ]            │
└──────────────────────────────────────────┘
```

**Automatische Erkennung:**

```python
def ist_10_tage_regel_anwendbar(rechnung):
    """
    Prüft ob 10-Tage-Regel anwendbar (22.12. - 10.01.)
    """
    # 1. Regelmäßige Zahlung? (Miete, Versicherung, Abo)
    ist_regelmaessig = rechnung.kategorie in [
        'Raumkosten (Miete)',
        'Versicherungen (betr.)',
        'Telefon, Internet',
        'Software, Lizenzen'  # Wenn monatlich
    ]

    if not ist_regelmaessig:
        return False

    # 2. Zahlungsdatum zwischen 22.12. und 10.01.?
    datum = rechnung.zahlungsdatum
    jahr = datum.year

    # 22.12. - 31.12. (altes Jahr)
    if datum >= date(jahr, 12, 22) and datum <= date(jahr, 12, 31):
        return True

    # 01.01. - 10.01. (neues Jahr)
    if datum >= date(jahr, 1, 1) and datum <= date(jahr, 1, 10):
        return True

    return False
```

---

#### **Übersicht: EÜR-Jahr vs. Rechnungsjahr**

**Dashboard-Widget:**

```
┌──────────────────────────────────────────┐
│ EÜR-Jahresübergang (2025 → 2026)        │
├──────────────────────────────────────────┤
│                                          │
│ Rechnungen 2025, bezahlt in 2026:       │
│   3 Rechnungen, 2.500 € → EÜR 2026      │
│                                          │
│ Rechnungen 2026, bezahlt in 2025:       │
│   0 Rechnungen, 0 € → Keine             │
│                                          │
│ ℹ️ EÜR 2025 niedriger als erwartet?      │
│    Prüfe, ob Dezember-Rechnungen in 2026 │
│    bezahlt wurden.                       │
│                                          │
│    [ Details anzeigen ]                  │
└──────────────────────────────────────────┘
```

**Detail-Ansicht:**

```
┌─────────────────────────────────────────────────────────────┐
│ Jahresübergang: Rechnungen mit abweichendem EÜR-Jahr       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Filter: [2025 ▼]  Typ: [Alle ▼]                             │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Rechnung        │ Rechnungsdatum │ Zahlungsdatum │ EÜR │
│ ├─────────────────┼────────────────┼───────────────┼─────┤
│ │ RE-2025-038     │ 15.11.2025     │ 05.01.2026    │ 2026│
│ │ RE-2025-040     │ 01.12.2025     │ 08.01.2026    │ 2026│
│ │ RE-2025-042     │ 15.12.2025     │ 10.01.2026    │ 2026│
│ └─────────────────┴────────────────┴───────────────┴─────┘   │
│                                                             │
│ 💡 Diese Rechnungen wurden 2025 geschrieben, aber zählen   │
│    für EÜR 2026 (Zufluss-Prinzip).                         │
│                                                             │
│    [CSV exportieren]  [PDF drucken]                         │
└─────────────────────────────────────────────────────────────┘
```

---

#### **Zusammenfassung Frage 7.4**

| Aspekt | Antwort |
|--------|---------|
| **Automatisch nach Zahlungsdatum buchen?** | ✅ Ja, EÜR-Jahr = Zahlungsjahr (nicht Rechnungsjahr) |
| **Hinweise bei Jahresübergang?** | ✅ Ja, proaktive Warnungen bei Zahlungseingabe und Jahresabschluss |
| **10-Tage-Regel?** | ✅ Ja, automatische Erkennung + Wahlrecht für regelmäßige Zahlungen |
| **Dashboard-Widget?** | ✅ Ja, Übersicht Jahresübergang mit abweichenden EÜR-Jahren |

---

### **7.3 Betriebseinnahmen**

**Was gehört rein?**

✅ **Alle betrieblichen Einnahmen:**
- Umsätze aus Verkauf (Waren, Dienstleistungen)
- Honorare, Provisionen
- Erstattungen (z.B. von Versicherung)
- Skonti, Rabatte (erhalten)
- Private Kfz-Nutzung (bei Betriebsfahrzeug)
- Entnahmen (z.B. Waren für Eigenverbrauch)

❌ **NICHT:**
- Privatentnahmen (Geld vom Geschäftskonto auf privat)
- Darlehen/Kredite (keine Einnahmen, nur Fremdkapital)
- Umsatzsteuer (wird separat erfasst)

**EÜR-Zeilen (Anlage EÜR):**
- **Zeile 11:** Umsätze 19% USt
- **Zeile 12:** Umsätze 7% USt
- **Zeile 13:** Steuerfreie Umsätze (§ 4 Nr. 1-28 UStG)
- **Zeile 14:** Umsätze Kleinunternehmer (§ 19 UStG)
- **Zeile 15:** Innergemeinschaftliche Lieferungen (0% USt, EU)
- **Zeile 21:** Vereinnahmte Umsatzsteuer

**RechnungsFee-Datenquellen:**
```python
def calculate_betriebseinnahmen(jahr):
    """
    Berechnet Betriebseinnahmen für EÜR
    """
    # 1. Ausgangsrechnungen (bezahlt!)
    ausgangsrechnungen = get_ausgangsrechnungen(
        jahr=jahr,
        status='bezahlt',  # Nur bezahlte (Zufluss-Prinzip!)
        zahlungsdatum_jahr=jahr  # Zahlung im Jahr (nicht Rechnungsdatum!)
    )

    # Aufschlüsselung nach USt-Satz
    umsatz_19 = sum(
        r.netto_betrag for r in ausgangsrechnungen
        if r.umsatzsteuer_satz == 19.0
    )

    umsatz_7 = sum(
        r.netto_betrag for r in ausgangsrechnungen
        if r.umsatzsteuer_satz == 7.0
    )

    umsatz_0_eu = sum(
        r.netto_betrag for r in ausgangsrechnungen
        if r.umsatzsteuer_satz == 0.0 and r.ist_eu_lieferung
    )

    umsatz_kleinunternehmer = sum(
        r.brutto_betrag for r in ausgangsrechnungen
        if user.ist_kleinunternehmer
    )

    # 2. Bareinnahmen (Kassenbuch)
    bareinnahmen = get_kassenbuch_einnahmen(
        jahr=jahr,
        art='Einnahme'
    )

    bar_umsatz_19 = sum(
        e.netto_betrag for e in bareinnahmen
        if e.ust_satz == 19.0
    )

    bar_umsatz_7 = sum(
        e.netto_betrag for e in bareinnahmen
        if e.ust_satz == 7.0
    )

    # SUMMEN
    return {
        'zeile_11_umsatz_19': umsatz_19 + bar_umsatz_19,
        'zeile_12_umsatz_7': umsatz_7 + bar_umsatz_7,
        'zeile_15_eu_lieferungen': umsatz_0_eu,
        'zeile_14_kleinunternehmer': umsatz_kleinunternehmer,
        'zeile_21_ust_gesamt': (umsatz_19 + bar_umsatz_19) * 0.19 + (umsatz_7 + bar_umsatz_7) * 0.07
    }
```

---

### **7.4 Betriebsausgaben**

**Was gehört rein?**

✅ **Alle betrieblichen Ausgaben:**
- Wareneinkauf, Material
- Bürobedarf, Software
- Miete (Büro, Lager)
- Versicherungen (betrieblich)
- Telefon, Internet
- Fahrtkosten, Reisekosten
- Fortbildungen
- Steuerberatungskosten
- Abschreibungen (AfA)
- Zinsen für Betriebskredite

❌ **NICHT:**
- Private Ausgaben
- Einkommensteuer, Lohnsteuer (nicht abzugsfähig)
- Geldstrafen, Bußgelder
- Repräsentationsaufwand (nur teilweise)

**EÜR-Zeilen (Anlage EÜR):**
- **Zeile 25:** Wareneinkauf
- **Zeile 26:** Löhne, Gehälter
- **Zeile 28:** Raumkosten (Miete, Nebenkosten)
- **Zeile 32:** Fahrtkosten (Kfz)
- **Zeile 34:** Werbekosten
- **Zeile 36:** Bürobedarf
- **Zeile 40:** Fortbildungskosten
- **Zeile 41:** Versicherungen
- **Zeile 43:** Sonstige unbeschränkt abziehbare Betriebsausgaben
- **Zeile 45:** Abschreibungen (AfA)
- **Zeile 60:** Vorsteuer (abziehbar)

**RechnungsFee-Datenquellen:**
```python
def calculate_betriebsausgaben(jahr):
    """
    Berechnet Betriebsausgaben für EÜR
    """
    # 1. Eingangsrechnungen (bezahlt!)
    eingangsrechnungen = get_eingangsrechnungen(
        jahr=jahr,
        status='bezahlt',  # Nur bezahlte (Abfluss-Prinzip!)
        zahlungsdatum_jahr=jahr
    )

    # Kategorisierung nach EÜR-Zeilen
    ausgaben_kategorisiert = {}

    for kategorie in EÜR_KATEGORIEN:
        ausgaben_kategorisiert[kategorie.zeile] = sum(
            r.netto_betrag for r in eingangsrechnungen
            if r.kategorie == kategorie.name
        )

    # 2. Barausgaben (Kassenbuch)
    barausgaben = get_kassenbuch_ausgaben(
        jahr=jahr,
        art='Ausgabe'
    )

    for kategorie in EÜR_KATEGORIEN:
        ausgaben_kategorisiert[kategorie.zeile] += sum(
            a.netto_betrag for a in barausgaben
            if a.kategorie == kategorie.name
        )

    # 3. Vorsteuer (abziehbar)
    vorsteuer = sum(
        r.umsatzsteuer_betrag for r in eingangsrechnungen
        if r.vorsteuerabzug  # Nur wenn abziehbar!
    )

    vorsteuer += sum(
        a.ust_betrag for a in barausgaben
        if a.vorsteuerabzug
    )

    return {
        **ausgaben_kategorisiert,
        'zeile_60_vorsteuer': vorsteuer
    }
```

**Kategorie-Mapping (Beispiel):**
```python
EÜR_KATEGORIEN = [
    {'zeile': 25, 'name': 'Wareneinkauf'},
    {'zeile': 26, 'name': 'Löhne & Gehälter'},  # Auch für Einzelunternehmer mit Mitarbeitern!
    {'zeile': 28, 'name': 'Raumkosten'},
    {'zeile': 32, 'name': 'Fahrtkosten'},
    {'zeile': 34, 'name': 'Werbekosten'},
    {'zeile': 36, 'name': 'Bürobedarf'},
    {'zeile': 40, 'name': 'Fortbildung'},
    {'zeile': 41, 'name': 'Versicherungen'},
    {'zeile': 43, 'name': 'Sonstige'},
]
```

---

### **7.4.1 Betriebsausgaben-Kategorien (Frage 7.2)**

**Konzept:**

RechnungsFee bietet ein **zweistufiges Kategorien-System**:

1. **Vordefinierte Standard-Kategorien** (nach Anlage EÜR)
2. **Frei erweiterbare User-Kategorien** (optional)

---

#### **Standard-Kategorien**

**Anzahl:** 15 vordefinierte Ausgaben-Kategorien

**Basis:** Anlage EÜR Zeilen 25-60 + DATEV-Kontenrahmen

**Vollständige Liste:**

```python
AUSGABEN_KATEGORIEN = [
    # ID | Name                    | EÜR-Zeile | DATEV SKR03 | DATEV SKR04

    # Zeile 25: Wareneinkauf
    {'id': 10, 'name': 'Wareneinkauf', 'euer_zeile': 25, 'skr03': 3400, 'skr04': 5400},

    # Zeile 26: Löhne & Gehälter (auch für Einzelunternehmer mit Mitarbeitern!)
    {'id': 11, 'name': 'Löhne & Gehälter', 'euer_zeile': 26, 'skr03': 4120, 'skr04': 6020},

    # Zeile 28: Raumkosten
    {'id': 12, 'name': 'Raumkosten (Miete)', 'euer_zeile': 28, 'skr03': 4210, 'skr04': 6300},
    {'id': 13, 'name': 'Strom, Gas, Wasser', 'euer_zeile': 28, 'skr03': 4240, 'skr04': 6325},
    {'id': 14, 'name': 'Telefon, Internet', 'euer_zeile': 28, 'skr03': 4910, 'skr04': 6805},

    # Zeile 32: Fahrtkosten
    {'id': 15, 'name': 'KFZ-Kosten (Benzin)', 'euer_zeile': 32, 'skr03': 4530, 'skr04': 6530},
    {'id': 16, 'name': 'KFZ-Versicherung', 'euer_zeile': 32, 'skr03': 4570, 'skr04': 6560},
    {'id': 17, 'name': 'Fahrtkosten (ÖPNV)', 'euer_zeile': 32, 'skr03': 4670, 'skr04': 6670},

    # Zeile 34: Werbekosten
    {'id': 18, 'name': 'Werbekosten', 'euer_zeile': 34, 'skr03': 4600, 'skr04': 6600},

    # Zeile 36: Bürobedarf
    {'id': 19, 'name': 'Bürobedarf', 'euer_zeile': 36, 'skr03': 4910, 'skr04': 6815},
    {'id': 20, 'name': 'Software, Lizenzen', 'euer_zeile': 36, 'skr03': 4940, 'skr04': 6825},

    # Zeile 40: Fortbildung
    {'id': 21, 'name': 'Fortbildung', 'euer_zeile': 40, 'skr03': 4945, 'skr04': 6820},

    # Zeile 41: Versicherungen
    {'id': 22, 'name': 'Versicherungen (betr.)', 'euer_zeile': 41, 'skr03': 4360, 'skr04': 6540},

    # Zeile 43: Sonstige unbeschränkt abziehbare Betriebsausgaben
    {'id': 23, 'name': 'Steuerberatung', 'euer_zeile': 43, 'skr03': 4970, 'skr04': 6837},
    {'id': 24, 'name': 'Sonstige Ausgaben', 'euer_zeile': 43, 'skr03': 4980, 'skr04': 6855},
]
```

**Vorteile:**
- ✅ Sofort einsatzbereit (kein Setup nötig)
- ✅ Korrekte EÜR-Zuordnung garantiert
- ✅ DATEV-Export funktioniert automatisch
- ✅ Für 90% der Einzelunternehmer ausreichend

---

#### **Benutzerdefinierte Kategorien**

**User kann eigene Kategorien hinzufügen:**

```python
class BenutzerKategorie:
    """
    Benutzerdefinierte Ausgaben-Kategorie
    """
    id: int  # 100+ (User-Kategorien starten bei ID 100)
    name: str  # z.B. "Hosting & Domain-Kosten"
    euer_zeile: int  # User wählt aus Dropdown: 25, 28, 32, 34, 36, 40, 41, 43
    datev_konto_skr03: int  # Optional: User kann DATEV-Konto angeben
    datev_konto_skr04: int  # Optional
    parent_kategorie_id: int  # Optional: Verknüpfung zu Standard-Kategorie
```

**UI zum Anlegen:**

```
┌──────────────────────────────────────────┐
│ Neue Kategorie erstellen                 │
├──────────────────────────────────────────┤
│                                          │
│  Name:  [Hosting & Domain-Kosten___]    │
│                                          │
│  Zuordnung:                              │
│  ● Basierend auf Standard-Kategorie:    │
│    [Bürobedarf ▼]                        │
│    → EÜR-Zeile 36                        │
│    → DATEV SKR03: 4910                   │
│                                          │
│  ○ Manuelle Zuordnung:                   │
│    EÜR-Zeile: [Zeile 36 ▼]              │
│    DATEV SKR03: [4910_______]           │
│    DATEV SKR04: [6815_______]           │
│                                          │
│    [Abbrechen]  [ Speichern ]            │
└──────────────────────────────────────────┘
```

**Beispiel-Workflow:**

1. User benötigt Kategorie "Hosting & Domain-Kosten"
2. Wählt Basis-Kategorie "Bürobedarf" (Zeile 36, DATEV 4910)
3. Neue Unterkategorie wird erstellt
4. Bei Eingangsrechnung: User wählt "Hosting & Domain-Kosten"
5. EÜR: Wird automatisch zu Zeile 36 addiert
6. DATEV-Export: Wird mit Konto 4910 exportiert

**Vorteile:**
- ✅ Flexibel für spezielle Branchen (z.B. Fotografen: "Model-Honorare")
- ✅ Detailliertere Auswertungen möglich
- ✅ EÜR-Konformität bleibt erhalten (durch Basis-Kategorie)
- ✅ DATEV-Export funktioniert (durch geerbtes Konto)

---

#### **DATEV-Kontenrahmen: SKR03 vs. SKR04**

**Warum zwei Kontenrahmen?**

| Kontenrahmen | Zielgruppe | Struktur |
|--------------|-----------|----------|
| **SKR03** | Gewerbetreibende, Handwerker, Handel | Prozessgliederung (Umsatzprozess) |
| **SKR04** | Freiberufler, Dienstleister | Abschlussgliederung (GuV-Schema) |

**User wählt bei Ersteinrichtung (Kategorie 8.6):**

```
Kontenrahmen wählen:

○ SKR03 - Gewerbetreibende
  Für: Handel, Handwerk, Produktion

● SKR04 - Freiberufler
  Für: IT-Berater, Ärzte, Anwälte, Kreative
```

**Automatisches Mapping:**

```python
def get_datev_konto(kategorie, kontenrahmen):
    """
    Gibt DATEV-Konto je nach Kontenrahmen zurück
    """
    if kontenrahmen == 'SKR03':
        return kategorie.skr03
    else:
        return kategorie.skr04

# Beispiel:
kategorie = AUSGABEN_KATEGORIEN[0]  # Wareneinkauf
get_datev_konto(kategorie, 'SKR03')  # → 3400
get_datev_konto(kategorie, 'SKR04')  # → 5400
```

**Kontenrahmen wechseln:**

⚠️ **Hinweis:** Wechsel nur möglich, wenn:
- Noch keine Buchungen vorhanden ODER
- User akzeptiert Neu-Mapping aller Buchungen

```
┌──────────────────────────────────────────┐
│ ⚠️ Kontenrahmen wechseln?                │
├──────────────────────────────────────────┤
│                                          │
│ Aktuell:  SKR03 (Gewerbetreibende)      │
│ Neu:      SKR04 (Freiberufler)          │
│                                          │
│ Auswirkungen:                            │
│ • 234 Buchungen werden neu zugeordnet   │
│ • DATEV-Export ändert sich              │
│ • Bisherige Exporte bleiben unverändert │
│                                          │
│ ⚠️ Dieser Vorgang kann nicht rückgängig │
│    gemacht werden!                       │
│                                          │
│    [Abbrechen]  [ Kontenrahmen wechseln ]│
└──────────────────────────────────────────┘
```

---

#### **Namenskonventionen**

**Regeln für Kategorienamen:**

1. **Kurz & prägnant:** Max. 30 Zeichen
2. **Selbsterklärend:** "Bürobedarf" statt "BB" oder "Diverses"
3. **Eindeutig:** "Telefon, Internet" statt nur "Telefon"
4. **Hierarchie optional:** "KFZ-Kosten (Benzin)" vs. einfach "Benzin"

**Beispiele:**

| ✅ Gut | ❌ Schlecht |
|-------|-----------|
| Wareneinkauf | Waren |
| Löhne & Gehälter | Löhne |
| Strom, Gas, Wasser | Energie |
| Telefon, Internet | Telekommunikation (zu lang) |
| KFZ-Kosten (Benzin) | Sprit |
| Software, Lizenzen | SW |

**User-Kategorien:** Können frei benannt werden, aber RechnungsFee schlägt vor:
- "Hosting & Domain-Kosten" (Unterkategorie von "Bürobedarf")
- "Model-Honorare" (Unterkategorie von "Löhne & Gehälter")
- "Werbe-Flyer" (Unterkategorie von "Werbekosten")

---

#### **Standard-Kategorien bearbeiten/löschen?**

**Nein!** Standard-Kategorien sind **schreibgeschützt**.

**Begründung:**
- ✅ Garantiert korrekte EÜR-Zuordnung
- ✅ Verhindert Fehler (z.B. "Wareneinkauf" versehentlich gelöscht)
- ✅ DATEV-Export bleibt kompatibel

**Workaround:**
- User kann Standard-Kategorie **ausblenden** (wenn ungenutzt)
- User kann **eigene Kategorie** mit anderem Namen erstellen

---

#### **Zusammenfassung Frage 7.2**

| Aspekt | Antwort |
|--------|---------|
| **Vordefinierte Liste nach Anlage EÜR?** | ✅ Ja, 15 Standard-Kategorien |
| **Frei konfigurierbar/erweiterbar?** | ✅ Ja, User-Kategorien mit EÜR-Zuordnung |
| **Anlehnung an DATEV-Konten?** | ✅ Beide: Eigene Namen + DATEV-Mapping (SKR03/SKR04) |
| **Wie viele Standard-Kategorien?** | **15 Ausgaben** + 5 Einnahmen |

---

### **7.5 Abschreibungen (AfA)**

**Was ist AfA?**
- **AfA** = Absetzung für Abnutzung
- Verteilung der Anschaffungskosten über die Nutzungsdauer
- Beispiel: Laptop 1.200 € → 3 Jahre Nutzung → 400 €/Jahr AfA

**Wann muss abgeschrieben werden?**

| Anschaffungskosten (netto) | Behandlung |
|----------------------------|------------|
| **< 800 €** | Sofortabzug (volle Kosten im Jahr der Anschaffung) |
| **800 € - 1.000 €** | Poolabschreibung (5 Jahre, je 20%) oder Sofortabzug |
| **> 1.000 €** | Abschreibung über Nutzungsdauer (AfA-Tabelle) |

**AfA-Tabelle (Beispiele):**

| Anlagegut | Nutzungsdauer | AfA/Jahr |
|-----------|---------------|----------|
| Computer, Laptop | 3 Jahre | 33,33% |
| Drucker | 3 Jahre | 33,33% |
| Büromöbel | 13 Jahre | 7,69% |
| Pkw | 6 Jahre | 16,67% |
| Software | 3 Jahre | 33,33% |
| Gebäude | 33-50 Jahre | 2-3% |

**Berechnung:**
```
AfA linear = Anschaffungskosten / Nutzungsdauer
```

**Beispiel:**
```
Laptop gekauft: 15.03.2025, 1.200 € (netto)
Nutzungsdauer: 3 Jahre
AfA/Jahr: 1.200 € / 3 = 400 €
AfA 2025 (März-Dez): 400 € × 10/12 = 333,33 € (monatsgenau!)
AfA 2026-2027: je 400 €
AfA 2028 (Jan-Feb): 400 € × 2/12 = 66,67 €
```

**RechnungsFee-Implementierung:**
```python
class Anlagegut:
    """
    Anlagegut mit Abschreibung
    """
    id: int
    bezeichnung: str  # "Laptop Dell XPS 13"
    anschaffungsdatum: date  # 15.03.2025
    anschaffungskosten: Decimal  # 1200.00 (netto)
    nutzungsdauer_jahre: int  # 3
    afa_methode: str  # 'linear', 'degressiv', 'pool'
    restbuchwert: Decimal  # 1200.00 → 800.00 → 400.00 → 0.00
    rechnung_id: int  # Verknüpfung zur Eingangsrechnung


def calculate_afa(anlagegut, jahr):
    """
    Berechnet AfA für ein Jahr
    """
    # 1. Volle AfA pro Jahr
    afa_pro_jahr = anlagegut.anschaffungskosten / anlagegut.nutzungsdauer_jahre

    # 2. Monatsgenau (nur im ersten und letzten Jahr)
    start_jahr = anlagegut.anschaffungsdatum.year
    ende_jahr = start_jahr + anlagegut.nutzungsdauer_jahre

    if jahr == start_jahr:
        # Erstes Jahr: Nur Monate ab Anschaffung
        monate = 13 - anlagegut.anschaffungsdatum.month  # März → 10 Monate
        return afa_pro_jahr * (monate / 12)

    elif jahr >= start_jahr and jahr < ende_jahr:
        # Volle Jahre dazwischen
        return afa_pro_jahr

    elif jahr == ende_jahr:
        # Letztes Jahr: Nur Monate bis Jahresende
        monate = anlagegut.anschaffungsdatum.month - 1  # März → 2 Monate
        return afa_pro_jahr * (monate / 12)

    else:
        # Außerhalb Nutzungsdauer
        return 0


def get_afa_for_euer(jahr):
    """
    Summiert alle AfA für EÜR Zeile 45
    """
    anlagegueter = get_anlagegueter()

    afa_gesamt = sum(
        calculate_afa(a, jahr) for a in anlagegueter
    )

    return {
        'zeile_45_afa': afa_gesamt
    }
```

**Geringwertige Wirtschaftsgüter (GWG):**
```python
def handle_gwg(rechnung):
    """
    Prüft ob GWG-Regelung anwendbar
    """
    netto = rechnung.netto_betrag

    if netto < 800:
        # Sofortabzug
        return {
            'typ': 'sofortabzug',
            'zeile_43': netto,  # Sonstige Ausgaben
            'afa_notwendig': False
        }

    elif netto >= 800 and netto <= 1000:
        # User wählt: Sofortabzug oder Pool
        return {
            'typ': 'wahlrecht',
            'optionen': ['sofortabzug', 'pool_5_jahre']
        }

    else:
        # Abschreibung Pflicht
        return {
            'typ': 'afa_pflicht',
            'afa_notwendig': True
        }
```

---

### **7.5.1 Anlagenverwaltung (Frage 7.3)**

#### **Umfang der Anlagenverwaltung in RechnungsFee**

**RechnungsFee bietet vollständige Anlagenverwaltung mit:**

1. ✅ **GWG-Automatik** (Sofortabzug < 800 €, Poolabschreibung 800-1000 €)
2. ✅ **AfA-Rechner** (automatische Abschreibungsberechnung)
3. ✅ **Anlagenverzeichnis** (Übersicht aller Wirtschaftsgüter)
4. ✅ **Monatsgenauer AfA-Berechnung** (anteilig im ersten/letzten Jahr)

---

#### **GWG-Grenzwerte: 800€ vs. 1000€**

**Drei Schwellenwerte:**

| Anschaffungskosten (netto) | Regelung | RechnungsFee-Verhalten |
|----------------------------|----------|--------------------------|
| **< 800 €** | Sofortabzug Pflicht | Automatisch zu Zeile 43 (Sonstige Ausgaben) |
| **800 € - 1.000 €** | Wahlrecht: Sofortabzug ODER Poolabschreibung | User wird gefragt (siehe Dialog unten) |
| **> 1.000 €** | AfA-Pflicht | Anlage wird erstellt, AfA über Nutzungsdauer |

**UI-Dialog bei 800-1000€:**

```
┌──────────────────────────────────────────┐
│ GWG-Behandlung wählen                    │
├──────────────────────────────────────────┤
│                                          │
│ Eingangsrechnung: Laptop HP ProBook     │
│ Netto: 899,00 €                          │
│                                          │
│ Anschaffungskosten zwischen 800-1000 €   │
│ → Wahlrecht nach § 6 Abs. 2a EStG       │
│                                          │
│ Optionen:                                │
│                                          │
│ ● Sofortabzug (empfohlen)                │
│   Volle 899 € im Jahr 2025 abziehbar    │
│   → EÜR Zeile 43                         │
│                                          │
│ ○ Poolabschreibung (5 Jahre)            │
│   179,80 € pro Jahr (2025-2029)         │
│   → EÜR Zeile 45 (AfA)                   │
│                                          │
│ 💡 Sofortabzug maximiert Steuerersparnis│
│    in 2025. Poolabschreibung verteilt   │
│    über 5 Jahre.                         │
│                                          │
│    [Abbrechen]  [ Auswählen ]            │
└──────────────────────────────────────────┘
```

**Empfehlung:**

RechnungsFee empfiehlt **Sofortabzug** (wenn User nicht sicher ist), da:
- ✅ Steuerersparnis früher (im Jahr der Anschaffung)
- ✅ Weniger Verwaltungsaufwand (keine 5-Jahres-Buchführung)
- ✅ Einfacher zu verstehen

---

#### **AfA-Rechner**

**Funktionen:**

1. **Automatische Nutzungsdauer-Vorschläge** (basierend auf amtlicher AfA-Tabelle)
2. **Monatsgenauer AfA-Berechnung** (anteilig im ersten/letzten Jahr)
3. **Restbuchwert-Tracking** (für Verkauf/Entnahme)

**UI beim Anlagegut anlegen:**

```
┌──────────────────────────────────────────┐
│ Anlagegut erfassen                       │
├──────────────────────────────────────────┤
│                                          │
│ Bezeichnung: [Laptop Dell XPS 13_____]  │
│                                          │
│ Anschaffung:                             │
│   Datum:   [15.03.2025]                  │
│   Kosten:  [1.200,00] € (netto)         │
│                                          │
│ Abschreibung:                            │
│   Kategorie: [Computer/Laptop ▼]         │
│   Nutzungsdauer: [3] Jahre               │
│              💡 Vorschlag aus AfA-Tabelle│
│                                          │
│ AfA-Berechnung (Vorschau):               │
│   2025 (Mär-Dez): 333,33 € (10/12)      │
│   2026-2027:      400,00 € (je Jahr)     │
│   2028 (Jan-Feb):  66,67 € (2/12)       │
│   ────────────────────────────────       │
│   Gesamt:       1.200,00 €               │
│                                          │
│ Verknüpfung:                             │
│   Eingangsrechnung: [RE-2025-001 ▼]     │
│                                          │
│    [Abbrechen]  [ Speichern ]            │
└──────────────────────────────────────────┘
```

**AfA-Tabelle (integriert):**

RechnungsFee enthält die wichtigsten Einträge der amtlichen AfA-Tabelle:

```python
AFA_TABELLE = {
    'Computer/Laptop': 3,
    'Drucker': 3,
    'Monitor': 3,
    'Smartphone': 5,
    'Software': 3,
    'Büromöbel': 13,
    'PKW': 6,
    'Kamera (professionell)': 7,
    'Werkzeuge': 10,
    'Maschinen (allgemein)': 10,
    'Gebäude (Büro)': 33,
}
```

**User kann abweichen:**

- ⚠️ Warnung wenn Nutzungsdauer < AfA-Tabelle
- ℹ️ Hinweis: "Finanzamt erkennt ggf. nicht an"

---

#### **Anlagenverzeichnis**

**Übersicht aller Anlagegüter:**

```
┌─────────────────────────────────────────────────────────────┐
│ Anlagenverzeichnis                           [+ Neu]        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Filter: [Alle ▼]  Suche: [____________]                     │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Bezeichnung            │ Anschaffung │ Restbuchwert  │   │
│ ├────────────────────────┼─────────────┼───────────────┤   │
│ │ Laptop Dell XPS 13     │ 15.03.2025  │   800,00 €   │   │
│ │   1.200,00 € (3 Jahre) │ AfA 2025: 333,33 €         │   │
│ ├────────────────────────┼─────────────┼───────────────┤   │
│ │ Drucker HP LaserJet    │ 02.01.2024  │   199,80 €   │   │
│ │   Pool (5 Jahre)       │ AfA 2025: 99,90 €          │   │
│ ├────────────────────────┼─────────────┼───────────────┤   │
│ │ Bürostuhl Herman M.    │ 12.05.2023  │   384,62 €   │   │
│ │   500,00 € (13 Jahre)  │ AfA 2025: 38,46 €          │   │
│ └────────────────────────┴─────────────┴───────────────┘   │
│                                                             │
│ AfA 2025 gesamt: 471,69 € → EÜR Zeile 45                   │
│                                                             │
│ Aktionen: [AfA-Plan drucken]  [CSV exportieren]             │
└─────────────────────────────────────────────────────────────┘
```

**Funktionen:**

- ✅ Sortieren nach: Bezeichnung, Anschaffungsdatum, Restbuchwert
- ✅ Filtern nach: Aktiv, Vollständig abgeschrieben, Verkauft
- ✅ Suche nach Bezeichnung
- ✅ Detailansicht (mit AfA-Plan für alle Jahre)
- ✅ Export: CSV, PDF

**Detailansicht (Klick auf Anlagegut):**

```
┌──────────────────────────────────────────┐
│ Anlagegut: Laptop Dell XPS 13            │
├──────────────────────────────────────────┤
│                                          │
│ STAMMDATEN:                              │
│   Anschaffung:  15.03.2025               │
│   Kosten:       1.200,00 € (netto)      │
│   Nutzungsdauer: 3 Jahre (Computer)      │
│   Verknüpfung:  RE-2025-001              │
│                                          │
│ ABSCHREIBUNGSPLAN:                       │
│ ┌──────────────────────────────────┐     │
│ │ Jahr │ AfA      │ Restbuchwert  │     │
│ ├──────┼──────────┼───────────────┤     │
│ │ 2025 │  333,33  │   866,67 €   │     │
│ │ 2026 │  400,00  │   466,67 €   │     │
│ │ 2027 │  400,00  │    66,67 €   │     │
│ │ 2028 │   66,67  │     0,00 €   │     │
│ └──────┴──────────┴───────────────┘     │
│                                          │
│ AKTIONEN:                                │
│ [ Bearbeiten ]  [ Verkaufen/Entnahme ]   │
│ [ AfA-Plan drucken ]  [ Löschen ]        │
└──────────────────────────────────────────┘
```

---

#### **Verkauf/Entnahme von Anlagegütern**

**Was passiert beim Verkauf?**

```
┌──────────────────────────────────────────┐
│ Anlagegut verkaufen/entnehmen            │
├──────────────────────────────────────────┤
│                                          │
│ Anlagegut: Laptop Dell XPS 13            │
│ Restbuchwert: 466,67 € (Stand 31.12.2026)│
│                                          │
│ Verkaufsdatum: [15.06.2027__]            │
│ Verkaufspreis: [300,00___] € (netto)    │
│                                          │
│ Berechnung:                              │
│   AfA 2027 (Jan-Mai):  166,67 € (5/12)  │
│   Restbuchwert danach: 300,00 €          │
│   Verkaufspreis:       300,00 €          │
│   ────────────────────────────────       │
│   Gewinn/Verlust:        0,00 €          │
│                                          │
│ ℹ️ Kein Buchgewinn/-verlust              │
│                                          │
│    [Abbrechen]  [ Verkauf buchen ]       │
└──────────────────────────────────────────┘
```

**Buchhaltung:**

- ✅ AfA wird anteilig bis Verkaufsdatum berechnet
- ✅ Buchgewinn/-verlust wird berechnet (Verkaufspreis - Restbuchwert)
- ✅ Buchgewinn → EÜR Zeile 11 (Betriebseinnahmen)
- ✅ Buchverlust → EÜR Zeile 43 (Sonstige Ausgaben)

---

#### **Einfache Erfassung vs. vollständige Abschreibungslogik**

**Entscheidung:** RechnungsFee bietet **vollständige Abschreibungslogik**.

**Begründung:**

| Aspekt | Einfache Erfassung | Vollständige AfA-Logik | Entscheidung |
|--------|-------------------|------------------------|--------------|
| **Aufwand für User** | Niedrig (nur Betrag eingeben) | Mittel (Anlagegut anlegen) | ✅ Mittel akzeptabel |
| **Korrektheit EÜR** | Manuell fehleranfällig | Garantiert korrekt | ✅ Wichtig! |
| **Mehrjahresplanung** | Nicht möglich | Automatisch | ✅ Sehr hilfreich |
| **Verkauf/Entnahme** | Kompliziert manuell | Automatisch berechnet | ✅ Wichtig! |
| **Steuerprüfung** | Anlagenverzeichnis fehlt | Vorhanden | ✅ Pflicht ab 60k € Gewinn |

**Kompromiss:** Automatische GWG-Erkennung

- < 800 €: Sofortabzug (User muss kein Anlagegut anlegen)
- \> 800 €: RechnungsFee **schlägt vor**, Anlagegut anzulegen (kann übersprungen werden)

**Workflow:**

```
Eingangsrechnung erfasst: Laptop 1.200 €

┌──────────────────────────────────────────┐
│ ℹ️ Anlagegut anlegen?                    │
├──────────────────────────────────────────┤
│                                          │
│ Die Rechnung "Laptop Dell XPS 13" ist    │
│ über 800 € und könnte ein Anlagegut sein.│
│                                          │
│ Empfehlung: Als Anlagegut anlegen        │
│ → AfA über 3 Jahre (Computer)            │
│                                          │
│ ○ Als Anlagegut anlegen (empfohlen)     │
│   → AfA-Rechner öffnen                   │
│                                          │
│ ○ Als Betriebsausgabe buchen             │
│   → Sofortabzug (nicht korrekt!)        │
│                                          │
│ [Überspringen]  [ Auswählen ]            │
└──────────────────────────────────────────┘
```

**Wichtig:** User kann überspringen, aber RechnungsFee warnt:

⚠️ "Achtung: Anschaffungskosten > 1.000 € müssen lt. EStG abgeschrieben werden. Sofortabzug kann vom Finanzamt abgelehnt werden."

---

#### **Zusammenfassung Frage 7.3**

| Aspekt | Antwort |
|--------|---------|
| **GWG bis 800€/1000€?** | ✅ Ja, automatische Erkennung + Wahlrecht 800-1000€ |
| **AfA-Rechner?** | ✅ Ja, vollständiger AfA-Rechner mit Nutzungsdauer-Vorschlägen |
| **Einfache Erfassung oder Abschreibungslogik?** | ✅ **Vollständige Abschreibungslogik** (mit GWG-Automatik < 800 €) |
| **Anlagenverzeichnis?** | ✅ Ja, mit AfA-Plan, Restbuchwert, Verkauf/Entnahme |

---

### **7.6 MVP-Implementierung (Hybrid-Ansatz)**

Analog zu UStVA (Kategorie 6.1) nutzen wir einen **Hybrid-Ansatz:**

#### **Version 1.0 (MVP):**

**✅ RechnungsFee berechnet:**
- Betriebseinnahmen (nach EÜR-Zeilen sortiert)
- Betriebsausgaben (nach EÜR-Zeilen sortiert)
- AfA für Anlagegüter
- Gewinn = Einnahmen - Ausgaben

**✅ Export-Formate:**
- **CSV/Excel** - Für manuelle Übertragung in ELSTER
- **PDF-Report** - Übersichtliche Darstellung

**❌ NICHT in MVP:**
- ELSTER-XML-Generierung
- Direkte Übermittlung ans Finanzamt

**User-Workflow:**
```
1. RechnungsFee: "EÜR erstellen" → Zeitraum wählen (2025)
2. RechnungsFee berechnet alle Werte
3. Export als CSV/Excel/PDF
4. User öffnet ELSTER-Portal
5. User trägt Werte MANUELL aus CSV in Anlage EÜR ein
6. User sendet über ELSTER
```

#### **Version 2.0 (Zukunft):**

**✅ Vollautomatisch:**
- ELSTER-XML-Generierung (Anlage EÜR)
- Validierung gegen ELSTER-Schema
- Direkte Übermittlung mit ELSTER-Zertifikat

**User-Workflow:**
```
1. RechnungsFee: "EÜR erstellen und senden"
2. RechnungsFee generiert ELSTER-XML
3. RechnungsFee sendet direkt ans Finanzamt
4. Bestätigung erhalten → Fertig!
```

---

### **7.7 EÜR-Berechnung (Implementierung)**

**Hauptfunktion:**
```python
def calculate_euer(jahr):
    """
    Berechnet vollständige EÜR für ein Jahr
    """
    # 1. Betriebseinnahmen
    einnahmen = calculate_betriebseinnahmen(jahr)

    # 2. Betriebsausgaben
    ausgaben = calculate_betriebsausgaben(jahr)

    # 3. AfA
    afa = get_afa_for_euer(jahr)

    # 4. Gewinn
    gewinn = (
        einnahmen['zeile_11_umsatz_19'] +
        einnahmen['zeile_12_umsatz_7'] +
        einnahmen['zeile_13_steuerfrei'] +
        einnahmen['zeile_14_kleinunternehmer'] +
        einnahmen['zeile_15_eu_lieferungen']
        -
        sum(ausgaben.values())
        -
        afa['zeile_45_afa']
    )

    return {
        'jahr': jahr,
        'einnahmen': einnahmen,
        'ausgaben': ausgaben,
        'afa': afa,
        'gewinn': gewinn,
        'erstellt_am': datetime.now()
    }
```

**Export-Varianten:**

RechnungsFee bietet **zwei EÜR-Export-Varianten**:

1. **Amtliche Anlage EÜR** - Für ELSTER/Finanzamt (alle Zeilen, zu denen Daten verfügbar sind)
2. **Vereinfachte EÜR** - Für User/Jobcenter (übersichtlich, nur Einnahmen - Ausgaben = Gewinn)

**Export 1: Amtliche Anlage EÜR (vollständig)**
```python
def export_euer_amtlich(euer_data):
    """
    Exportiert vollständige Anlage EÜR für ELSTER

    Befüllt ALLE Zeilen, zu denen Daten verfügbar sind
    """
    csv_data = [
        ['Anlage EÜR', euer_data['jahr']],
        ['', ''],
        ['BETRIEBSEINNAHMEN', ''],
        ['Zeile 11: Umsätze 19% USt', format_euro(euer_data['einnahmen']['zeile_11_umsatz_19'])],
        ['Zeile 12: Umsätze 7% USt', format_euro(euer_data['einnahmen']['zeile_12_umsatz_7'])],
        ['Zeile 14: Kleinunternehmer (§19 UStG)', format_euro(euer_data['einnahmen']['zeile_14_kleinunternehmer'])],
        ['Zeile 15: Innergemeinschaftl. Lieferungen', format_euro(euer_data['einnahmen']['zeile_15_eu_lieferungen'])],
        ['Zeile 21: Vereinnahmte USt', format_euro(euer_data['einnahmen']['zeile_21_ust_gesamt'])],
        ['', ''],
        ['BETRIEBSAUSGABEN', ''],
        ['Zeile 25: Wareneinkauf', format_euro(euer_data['ausgaben'].get(25, 0))],
        ['Zeile 26: Löhne & Gehälter', format_euro(euer_data['ausgaben'].get(26, 0))],  # Neu!
        ['Zeile 28: Raumkosten', format_euro(euer_data['ausgaben'].get(28, 0))],
        ['Zeile 32: Fahrtkosten', format_euro(euer_data['ausgaben'].get(32, 0))],
        ['Zeile 34: Werbekosten', format_euro(euer_data['ausgaben'].get(34, 0))],
        ['Zeile 36: Bürobedarf', format_euro(euer_data['ausgaben'].get(36, 0))],
        ['Zeile 40: Fortbildung', format_euro(euer_data['ausgaben'].get(40, 0))],
        ['Zeile 41: Versicherungen', format_euro(euer_data['ausgaben'].get(41, 0))],
        ['Zeile 43: Sonstige Ausgaben', format_euro(euer_data['ausgaben'].get(43, 0))],
        ['Zeile 45: AfA', format_euro(euer_data['afa']['zeile_45_afa'])],
        ['Zeile 60: Vorsteuer', format_euro(euer_data['ausgaben'].get(60, 0))],
        ['', ''],
        ['GEWINN', format_euro(euer_data['gewinn'])],
    ]

    return csv_data


def export_euer_vereinfacht(euer_data):
    """
    Exportiert vereinfachte EÜR für User/Jobcenter

    Übersichtlich: Nur Einnahmen - Ausgaben = Gewinn
    Keine detaillierte Zeilen-Aufschlüsselung
    """
    # Summen berechnen
    einnahmen_gesamt = sum(euer_data['einnahmen'].values())
    ausgaben_gesamt = sum(euer_data['ausgaben'].values()) + euer_data['afa']['zeile_45_afa']

    csv_data = [
        ['Einnahmen-Überschuss-Rechnung (vereinfacht)', euer_data['jahr']],
        ['', ''],
        ['EINNAHMEN', ''],
        ['Betriebseinnahmen gesamt', format_euro(einnahmen_gesamt)],
        ['', ''],
        ['AUSGABEN', ''],
        ['Betriebsausgaben gesamt', format_euro(ausgaben_gesamt)],
        ['  davon: Wareneinkauf', format_euro(euer_data['ausgaben'].get(25, 0))],
        ['  davon: Löhne & Gehälter', format_euro(euer_data['ausgaben'].get(26, 0))],
        ['  davon: Raumkosten', format_euro(euer_data['ausgaben'].get(28, 0))],
        ['  davon: Fahrtkosten', format_euro(euer_data['ausgaben'].get(32, 0))],
        ['  davon: Sonstige', format_euro(sum(euer_data['ausgaben'].values()) - euer_data['ausgaben'].get(25, 0) - euer_data['ausgaben'].get(26, 0) - euer_data['ausgaben'].get(28, 0) - euer_data['ausgaben'].get(32, 0))],
        ['  davon: AfA (Abschreibungen)', format_euro(euer_data['afa']['zeile_45_afa'])],
        ['', ''],
        ['════════════════════════════════════════', ''],
        ['GEWINN', format_euro(euer_data['gewinn'])],
        ['════════════════════════════════════════', ''],
    ]

    return csv_data
```

---

### **7.8 UI/UX**

**Navigation:**
```
Dashboard → Steuern → EÜR erstellen
```

**Formular:**
```
┌──────────────────────────────────────────────┐
│ Einnahmen-Überschuss-Rechnung (EÜR)         │
├──────────────────────────────────────────────┤
│                                              │
│  Jahr: [2025 ▼]                              │
│                                              │
│  ☑ Alle bezahlten Rechnungen einbeziehen    │
│  ☑ Kassenbuch-Einträge einbeziehen           │
│  ☑ AfA automatisch berechnen                 │
│                                              │
│  [ Berechnen ]                               │
│                                              │
├──────────────────────────────────────────────┤
│ ERGEBNIS:                                    │
│                                              │
│  Betriebseinnahmen:      45.890,00 €        │
│  Betriebsausgaben:      -23.450,00 €        │
│  AfA:                      -400,00 €        │
│  ────────────────────────────────────        │
│  GEWINN:                 22.040,00 €        │
│                                              │
│  EXPORT:                                     │
│  [ Amtliche EÜR (ELSTER) ]                   │
│  [ Vereinfachte EÜR (Jobcenter) ]            │
│  [ Detailansicht ]                           │
└──────────────────────────────────────────────┘
```

**Export-Dialog:**
```
┌──────────────────────────────────────────┐
│ EÜR exportieren                          │
├──────────────────────────────────────────┤
│                                          │
│ Variante:                                │
│ ● Amtliche Anlage EÜR                   │
│   Für: ELSTER / Finanzamt                │
│   Enthält: Alle EÜR-Zeilen mit Daten     │
│                                          │
│ ○ Vereinfachte EÜR                      │
│   Für: Eigene Übersicht / Jobcenter      │
│   Enthält: Einnahmen - Ausgaben = Gewinn │
│                                          │
│ Format:                                  │
│ ● CSV  ○ PDF  ○ Excel                    │
│                                          │
│    [Abbrechen]  [ Exportieren ]          │
└──────────────────────────────────────────┘
```

**Detailansicht:**
```
┌──────────────────────────────────────────────┐
│ EÜR 2025 - Detailansicht                     │
├──────────────────────────────────────────────┤
│                                              │
│ BETRIEBSEINNAHMEN                            │
│ ├─ Zeile 11: Umsätze 19% USt    38.500,00 € │
│ ├─ Zeile 12: Umsätze 7% USt      7.390,00 € │
│ └─ SUMME                         45.890,00 € │
│                                              │
│ BETRIEBSAUSGABEN                             │
│ ├─ Zeile 25: Wareneinkauf       12.300,00 € │
│ ├─ Zeile 28: Raumkosten          4.800,00 € │
│ ├─ Zeile 32: Fahrtkosten         2.150,00 € │
│ ├─ Zeile 36: Bürobedarf            890,00 € │
│ ├─ Zeile 40: Fortbildung           450,00 € │
│ ├─ Zeile 41: Versicherungen      1.260,00 € │
│ ├─ Zeile 43: Sonstige            1.600,00 € │
│ └─ SUMME                         23.450,00 € │
│                                              │
│ ABSCHREIBUNGEN (AfA)                         │
│ └─ Zeile 45: AfA                   400,00 € │
│    ├─ Laptop Dell XPS (03/2025)   400,00 € │
│                                              │
│ VORSTEUER                                    │
│ └─ Zeile 60: Vorsteuer           4.455,50 € │
│                                              │
│ ════════════════════════════════════════════ │
│ GEWINN                           22.040,00 € │
└──────────────────────────────────────────────┘
```

---

### **7.9 Validierung & Plausibilitätsprüfung**

**Vor Export:**
```python
def validate_euer(euer_data):
    """
    Prüft EÜR auf Plausibilität
    """
    warnings = []
    errors = []

    # 1. Gewinn plausibel?
    if euer_data['gewinn'] < 0:
        warnings.append({
            'typ': 'negativer_gewinn',
            'message': 'Verlust im Jahr - bitte prüfen',
            'betrag': euer_data['gewinn']
        })

    # 2. Alle Rechnungen bezahlt?
    unbezahlte = get_unbezahlte_rechnungen(euer_data['jahr'])
    if unbezahlte:
        warnings.append({
            'typ': 'unbezahlte_rechnungen',
            'message': f'{len(unbezahlte)} unbezahlte Rechnungen gefunden',
            'hinweis': 'Diese werden in der EÜR NICHT berücksichtigt (Zufluss-Prinzip)'
        })

    # 3. AfA vollständig?
    anlagegueter_ohne_afa = get_anlagegueter(
        jahr=euer_data['jahr'],
        anschaffungskosten__gt=1000,
        afa_angelegt=False
    )
    if anlagegueter_ohne_afa:
        errors.append({
            'typ': 'fehlende_afa',
            'message': f'{len(anlagegueter_ohne_afa)} Anlagegüter ohne AfA-Berechnung',
            'anlagegueter': [a.bezeichnung for a in anlagegueter_ohne_afa]
        })

    # 4. Kleinunternehmer: Keine Vorsteuer
    if user.ist_kleinunternehmer and euer_data['ausgaben'].get(60, 0) > 0:
        errors.append({
            'typ': 'kleinunternehmer_vorsteuer',
            'message': 'Kleinunternehmer können keine Vorsteuer abziehen',
            'betrag': euer_data['ausgaben'][60]
        })

    # 5. Umsatz > 600.000 € → Bilanzierungspflicht
    umsatz_gesamt = sum(euer_data['einnahmen'].values())
    if umsatz_gesamt > 600000:
        warnings.append({
            'typ': 'bilanzierungspflicht',
            'message': 'Umsatz > 600.000 € → Bilanzierungspflicht ab nächstem Jahr!',
            'umsatz': umsatz_gesamt
        })

    return {
        'errors': errors,
        'warnings': warnings,
        'kann_exportieren': len(errors) == 0
    }
```

---

### **7.10 Datenbank-Schema (Erweiterung)**

**Neue Tabelle: Anlagegüter**
```sql
CREATE TABLE anlagegueter (
    id INTEGER PRIMARY KEY,

    -- Stammdaten
    bezeichnung TEXT NOT NULL,  -- "Laptop Dell XPS 13"
    anschaffungsdatum DATE NOT NULL,
    anschaffungskosten DECIMAL(10,2) NOT NULL,  -- Netto

    -- AfA
    nutzungsdauer_jahre INTEGER NOT NULL,
    afa_methode TEXT DEFAULT 'linear',  -- 'linear', 'degressiv', 'pool'
    restbuchwert DECIMAL(10,2),

    -- Verknüpfung
    rechnung_id INTEGER,  -- Verknüpfung zur Eingangsrechnung

    -- Metadaten
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (rechnung_id) REFERENCES eingangsrechnungen(id)
);
```

**Neue Tabelle: EÜR-Export-Historie**
```sql
CREATE TABLE euer_exporte (
    id INTEGER PRIMARY KEY,
    jahr INTEGER NOT NULL,

    -- Berechnete Werte
    einnahmen_gesamt DECIMAL(10,2),
    ausgaben_gesamt DECIMAL(10,2),
    afa_gesamt DECIMAL(10,2),
    gewinn DECIMAL(10,2),

    -- Export
    export_format TEXT,  -- 'csv', 'pdf', 'elster_xml'
    export_datei TEXT,

    -- Metadaten
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### **7.11 Zusammenhang mit anderen Kategorien**

**Kategorie 1 (Kassenbuch):**
- Bareinnahmen/-ausgaben fließen in EÜR ein
- Zufluss-/Abfluss-Prinzip identisch

**Kategorie 2 (Rechnungen):**
- Ausgangsrechnungen (bezahlt!) → Betriebseinnahmen
- Eingangsrechnungen (bezahlt!) → Betriebsausgaben

**Kategorie 5 (Bank-Integration):**
- Zahlungsdaten → Zuordnung Rechnungen (bezahlt/unbezahlt)
- Automatischer Zahlungsabgleich essentiell für EÜR

**Kategorie 6 (UStVA):**
- **Gleiche Datengrundlage** (Ist-Versteuerung = Zufluss-Prinzip)
- Vorsteuer aus UStVA → EÜR Zeile 60

**Kategorie 4 (DATEV-Export):**
- EÜR-Daten können als DATEV-CSV exportiert werden
- Steuerberater nutzt für Jahresabschluss

---

**Status:** ✅ Kategorie 7 definiert - EÜR-Berechnung (Hybrid-Ansatz: MVP berechnet Werte, Export als CSV/PDF für manuelle ELSTER-Eingabe; v2.0: ELSTER-XML mit direkter Übermittlung), Zufluss-/Abfluss-Prinzip, Betriebseinnahmen/-ausgaben, AfA-Verwaltung, GWG-Regelung, Validierung, Datenbank-Schema.

---

