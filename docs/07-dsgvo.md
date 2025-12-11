## 1. Verantwortlicher
[Dein Name/Firma]
[Adresse]
[E-Mail]

## 2. Welche Daten speichern wir?

### Kundendaten:
- Name, Adresse, Kontaktdaten
- Rechnungsinformationen
- Zahlungsinformationen

### Lieferantendaten:
- Name, Adresse, Kontaktdaten
- Vertragsinformationen

## 3. Rechtsgrundlage

- **Art. 6 Abs. 1 lit. b DSGVO**: Vertragserfüllung (Rechnungsstellung)
- **Art. 6 Abs. 1 lit. c DSGVO**: Rechtliche Verpflichtung (§147 AO, §257 HGB)

## 4. Speicherdauer

- **Während Geschäftsbeziehung**: Aktive Speicherung
- **Nach letzter Rechnung**: 10 Jahre (§147 AO)
- **Nach 10 Jahren**: Automatische Löschung

## 5. Ihre Rechte (Art. 15-21 DSGVO)

- **Auskunft**: Sie können jederzeit Auskunft über Ihre gespeicherten Daten erhalten
- **Berichtigung**: Fehlerhafte Daten werden korrigiert
- **Löschung**: Nach Ablauf der Aufbewahrungsfrist werden Daten gelöscht
- **Einschränkung**: Sie können die Verarbeitung einschränken lassen
- **Datenportabilität**: Sie erhalten Ihre Daten in maschinenlesbarem Format

**Kontakt für Betroffenenrechte:**
[E-Mail für DSGVO-Anfragen]

## 6. Datensicherheit

- Datenbank verschlüsselt (SQLCipher)
- Backups verschlüsselt
- Zugriffskontrolle
- Audit-Logging

## 7. Keine Weitergabe an Dritte

Ihre Daten werden NICHT an Dritte weitergegeben (außer gesetzlich verpflichtet, z.B. Finanzamt bei Prüfung).
```

---

**Status:** ✅ **DSGVO-Compliance dokumentiert**

**Wichtigste Punkte:**
1. ✅ Aufbewahrungspflicht (10 Jahre) hat Vorrang vor Löschpflicht
2. ✅ Sperrung statt Löschung während Aufbewahrungsfrist
3. ✅ Automatische Löschung nach Ablauf
4. ✅ Betroffenenrechte (Auskunft, Löschung, Export) implementiert
5. ✅ Verschlüsselung & Audit-Logging
6. ✅ Datenschutzerklärung-Vorlage

---

### **8.12 Wiederkehrende Rechnungen** 🔄 (für v2.0 vorgemerkt)

**Status:** 📋 **Für v2.0 geplant** (NICHT in MVP v1.0)

**Zweck:**
- Automatische Verwaltung von wiederkehrenden Ausgaben
- Erinnerungen für fällige Zahlungen
- Historische Nachverfolgung von Abonnements

---

#### **💡 Anwendungsfälle**

**Typische wiederkehrende Rechnungen:**

```
┌─────────────────────────────────────────────────┐
│ 🔄 WIEDERKEHRENDE AUSGABEN                      │
├─────────────────────────────────────────────────┤
│                                                 │
│ 📅 MONATLICH:                                   │
│   - Software-Abos (Adobe, Microsoft 365, etc.) │
│   - SaaS-Tools (Hosting, Cloud-Dienste)        │
│   - Miete (Büro, Lager)                         │
│   - Versicherungen (monatliche Zahlung)        │
│   - Leasingraten                                │
│                                                 │
│ 📅 JÄHRLICH:                                    │
│   - Domain-Renewals (example.com)              │
│   - Software-Lizenzen (jährliche Verlängerung) │
│   - Versicherungen (Jahresprämie)              │
│   - Mitgliedschaften (IHK, Verbände)           │
│   - Zertifikate (SSL, Code Signing)            │
│                                                 │
│ 📅 QUARTALSWEISE:                               │
│   - Steuervorauszahlungen                       │
│   - Quartalsberichte (Abonnements)             │
│                                                 │
│ 📅 WÖCHENTLICH:                                 │
│   - Reinigungsdienst                            │
│   - Wartungsverträge                            │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

#### **🎯 Geplante Features**

**Kernfunktionen:**

1. **Intervalle:**
   - Täglich, Wöchentlich, Monatlich, Quartalsweise, Halbjährlich, Jährlich
   - Benutzerdefinierte Intervalle (z.B. "alle 3 Monate", "alle 2 Jahre")

2. **Automatische Erstellung:**
   - Rechnung wird automatisch importiert/erstellt
   - E-Mail-Benachrichtigung bei Fälligkeit
   - Optional: Automatische Zahlung (z.B. via SEPA-Lastschrift)

3. **Vorlagen:**
   - Wiederkehrende Rechnung basiert auf Vorlage
   - Betrag, Lieferant, Kategorie vordefiniert
   - Automatische Anpassung (z.B. Preiserhöhungen)

4. **Benachrichtigungen:**
   - X Tage vor Fälligkeit (z.B. 7 Tage vorher)
   - Bei überfälligen Rechnungen
   - Bei automatischer Verlängerung

5. **Start-/Enddatum:**
   - Startdatum: Wann beginnt das Abo?
   - Enddatum: Optional (z.B. Vertrag läuft 2 Jahre)
   - Automatische Verlängerung (mit Kündigungsfrist)

6. **Preisverlauf:**
   - Historische Preise tracken
   - Erkennung von Preiserhöhungen
   - Vergleich Jahr-zu-Jahr

---

#### **📊 Datenbank-Schema**

```sql
CREATE TABLE wiederkehrende_rechnungen (
    id INTEGER PRIMARY KEY,

    -- Stammdaten
    bezeichnung TEXT NOT NULL,  -- "Adobe Creative Cloud Abo"
    beschreibung TEXT,

    -- Lieferant (optional, wenn aus Stammdaten)
    lieferant_id INTEGER,
    lieferant_name TEXT,  -- Falls nicht im Stamm

    -- Kategorie
    kategorie_id INTEGER NOT NULL,

    -- Betrag
    betrag_netto DECIMAL(10,2) NOT NULL,
    betrag_brutto DECIMAL(10,2) NOT NULL,
    umsatzsteuer_satz DECIMAL(5,2) DEFAULT 19.0,

    -- Intervall
    intervall_typ TEXT NOT NULL,  -- 'taeglich', 'woechentlich', 'monatlich', 'quartalsweise', 'halbjaehrlich', 'jaehrlich', 'benutzerdefiniert'
    intervall_anzahl INTEGER DEFAULT 1,  -- z.B. 3 für "alle 3 Monate"
    intervall_einheit TEXT,  -- 'tage', 'wochen', 'monate', 'jahre' (bei benutzerdefiniert)

    -- Start-/Enddatum
    start_datum DATE NOT NULL,
    ende_datum DATE,  -- NULL = unbegrenzt
    kuendigungsfrist_tage INTEGER,  -- z.B. 30 Tage

    -- Verlängerung
    automatische_verlaengerung BOOLEAN DEFAULT 1,
    verlaengerung_intervall_monate INTEGER DEFAULT 12,  -- z.B. 12 Monate Verlängerung

    -- Benachrichtigungen
    benachrichtigung_tage_vorher INTEGER DEFAULT 7,  -- 7 Tage vor Fälligkeit
    benachrichtigung_email TEXT,

    -- Status
    ist_aktiv BOOLEAN DEFAULT 1,
    ist_pausiert BOOLEAN DEFAULT 0,

    -- Letzte Erstellung
    letzte_rechnung_datum DATE,
    naechste_rechnung_datum DATE,  -- Berechnet

    -- Metadaten
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    aktualisiert_am TIMESTAMP,

    -- Foreign Keys
    FOREIGN KEY (lieferant_id) REFERENCES lieferanten(id),
    FOREIGN KEY (kategorie_id) REFERENCES kategorien(id),

    -- Constraints
    CHECK (intervall_typ IN ('taeglich', 'woechentlich', 'monatlich', 'quartalsweise', 'halbjaehrlich', 'jaehrlich', 'benutzerdefiniert'))
);

-- Historie der generierten Rechnungen
CREATE TABLE wiederkehrende_rechnungen_historie (
    id INTEGER PRIMARY KEY,
    wiederkehrende_rechnung_id INTEGER NOT NULL,
    rechnung_id INTEGER,  -- Verknüpfung zur eigentlichen Rechnung
    faelligkeit_datum DATE NOT NULL,
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    betrag_netto DECIMAL(10,2),
    betrag_brutto DECIMAL(10,2),
    status TEXT,  -- 'erstellt', 'bezahlt', 'ueberfaellig', 'storniert'

    FOREIGN KEY (wiederkehrende_rechnung_id) REFERENCES wiederkehrende_rechnungen(id),
    FOREIGN KEY (rechnung_id) REFERENCES rechnungen(id)
);

-- Index für schnelle Abfragen
CREATE INDEX idx_wiederkehrend_naechste ON wiederkehrende_rechnungen(naechste_rechnung_datum);
CREATE INDEX idx_wiederkehrend_aktiv ON wiederkehrende_rechnungen(ist_aktiv);
```

---

#### **💻 Code-Implementierung (Konzept)**

```python
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

@dataclass
class WiederkehrendeRechnung:
    id: Optional[int] = None
    bezeichnung: str = ''  # "Adobe Creative Cloud Abo"
    beschreibung: Optional[str] = None

    # Lieferant
    lieferant_id: Optional[int] = None
    lieferant_name: Optional[str] = None

    # Kategorie
    kategorie_id: int = 0

    # Betrag
    betrag_netto: Decimal = Decimal('0.00')
    betrag_brutto: Decimal = Decimal('0.00')
    umsatzsteuer_satz: Decimal = Decimal('19.0')

    # Intervall
    intervall_typ: str = 'monatlich'  # 'taeglich', 'woechentlich', 'monatlich', etc.
    intervall_anzahl: int = 1
    intervall_einheit: Optional[str] = None

    # Start-/Enddatum
    start_datum: date = date.today()
    ende_datum: Optional[date] = None
    kuendigungsfrist_tage: Optional[int] = None

    # Verlängerung
    automatische_verlaengerung: bool = True
    verlaengerung_intervall_monate: int = 12

    # Benachrichtigungen
    benachrichtigung_tage_vorher: int = 7
    benachrichtigung_email: Optional[str] = None

    # Status
    ist_aktiv: bool = True
    ist_pausiert: bool = False

    # Letzte Erstellung
    letzte_rechnung_datum: Optional[date] = None
    naechste_rechnung_datum: Optional[date] = None

    def berechne_naechstes_datum(self) -> date:
        """
        Berechnet nächstes Fälligkeitsdatum

        Returns:
            Nächstes Datum
        """
        if not self.letzte_rechnung_datum:
            # Erste Rechnung
            return self.start_datum

        # Intervall berechnen
        if self.intervall_typ == 'taeglich':
            delta = timedelta(days=self.intervall_anzahl)
        elif self.intervall_typ == 'woechentlich':
            delta = timedelta(weeks=self.intervall_anzahl)
        elif self.intervall_typ == 'monatlich':
            # Monatlich ist komplexer (unterschiedliche Monatslängen)
            naechstes = self.letzte_rechnung_datum
            for _ in range(self.intervall_anzahl):
                naechstes = self._add_month(naechstes)
            return naechstes
        elif self.intervall_typ == 'quartalsweise':
            naechstes = self.letzte_rechnung_datum
            for _ in range(3 * self.intervall_anzahl):
                naechstes = self._add_month(naechstes)
            return naechstes
        elif self.intervall_typ == 'halbjaehrlich':
            naechstes = self.letzte_rechnung_datum
            for _ in range(6 * self.intervall_anzahl):
                naechstes = self._add_month(naechstes)
            return naechstes
        elif self.intervall_typ == 'jaehrlich':
            naechstes = self.letzte_rechnung_datum
            for _ in range(12 * self.intervall_anzahl):
                naechstes = self._add_month(naechstes)
            return naechstes
        elif self.intervall_typ == 'benutzerdefiniert':
            if self.intervall_einheit == 'tage':
                delta = timedelta(days=self.intervall_anzahl)
            elif self.intervall_einheit == 'wochen':
                delta = timedelta(weeks=self.intervall_anzahl)
            elif self.intervall_einheit == 'monate':
                naechstes = self.letzte_rechnung_datum
                for _ in range(self.intervall_anzahl):
                    naechstes = self._add_month(naechstes)
                return naechstes
            elif self.intervall_einheit == 'jahre':
                naechstes = self.letzte_rechnung_datum
                for _ in range(12 * self.intervall_anzahl):
                    naechstes = self._add_month(naechstes)
                return naechstes
        else:
            raise ValueError(f"Ungültiger Intervall-Typ: {self.intervall_typ}")

        return self.letzte_rechnung_datum + delta

    def _add_month(self, datum: date) -> date:
        """
        Fügt einen Monat zu einem Datum hinzu

        Args:
            datum: Ausgangsdatum

        Returns:
            Datum + 1 Monat
        """
        month = datum.month
        year = datum.year

        if month == 12:
            month = 1
            year += 1
        else:
            month += 1

        # Tag anpassen (z.B. 31.01. + 1 Monat = 28./29.02.)
        day = min(datum.day, self._days_in_month(year, month))

        return date(year, month, day)

    def _days_in_month(self, year: int, month: int) -> int:
        """Gibt Anzahl Tage im Monat zurück"""
        if month in [1, 3, 5, 7, 8, 10, 12]:
            return 31
        elif month in [4, 6, 9, 11]:
            return 30
        else:  # Februar
            # Schaltjahr?
            if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
                return 29
            else:
                return 28

    def ist_faellig(self) -> bool:
        """
        Prüft, ob Rechnung fällig ist

        Returns:
            True, wenn heute >= naechste_rechnung_datum
        """
        if not self.ist_aktiv or self.ist_pausiert:
            return False

        if not self.naechste_rechnung_datum:
            self.naechste_rechnung_datum = self.berechne_naechstes_datum()

        return date.today() >= self.naechste_rechnung_datum

    def ist_ende_erreicht(self) -> bool:
        """
        Prüft, ob Enddatum erreicht ist

        Returns:
            True, wenn ende_datum erreicht
        """
        if not self.ende_datum:
            return False  # Unbegrenzt

        return date.today() >= self.ende_datum


# Cron-Job: Täglich ausführen
def erstelle_faellige_rechnungen():
    """
    Erstellt automatisch fällige wiederkehrende Rechnungen

    Wird täglich ausgeführt (z.B. 06:00 Uhr morgens)
    """
    heute = date.today()

    # Alle aktiven wiederkehrenden Rechnungen finden
    wiederkehrend = db.execute("""
        SELECT * FROM wiederkehrende_rechnungen
        WHERE ist_aktiv = 1
          AND ist_pausiert = 0
          AND naechste_rechnung_datum <= ?
          AND (ende_datum IS NULL OR ende_datum >= ?)
    """, (heute, heute)).fetchall()

    for wr in wiederkehrend:
        # Rechnung erstellen
        rechnung = erstelle_rechnung_aus_vorlage(wr)

        # Historie speichern
        db.execute("""
            INSERT INTO wiederkehrende_rechnungen_historie
            (wiederkehrende_rechnung_id, rechnung_id, faelligkeit_datum, betrag_netto, betrag_brutto, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (wr.id, rechnung.id, heute, wr.betrag_netto, wr.betrag_brutto, 'erstellt'))

        # Nächstes Datum berechnen
        wr.letzte_rechnung_datum = heute
        wr.naechste_rechnung_datum = wr.berechne_naechstes_datum()
        db.save(wr)

        # Benachrichtigung senden
        if wr.benachrichtigung_email:
            sende_benachrichtigung(wr, rechnung)

        print(f"✅ Wiederkehrende Rechnung erstellt: {wr.bezeichnung} ({rechnung.rechnungsnummer})")


def sende_erinnerungen():
    """
    Sendet Erinnerungen X Tage vor Fälligkeit

    Wird täglich ausgeführt
    """
    heute = date.today()

    wiederkehrend = db.execute("""
        SELECT * FROM wiederkehrende_rechnungen
        WHERE ist_aktiv = 1
          AND ist_pausiert = 0
          AND benachrichtigung_email IS NOT NULL
    """).fetchall()

    for wr in wiederkehrend:
        tage_bis_faelligkeit = (wr.naechste_rechnung_datum - heute).days

        if tage_bis_faelligkeit == wr.benachrichtigung_tage_vorher:
            # Erinnerung senden
            sende_erinnerungs_email(wr)
            print(f"📧 Erinnerung gesendet: {wr.bezeichnung} (fällig in {tage_bis_faelligkeit} Tagen)")
```

---

#### **🎨 UI-Mockups**

**Übersicht Wiederkehrende Rechnungen:**

```
┌─────────────────────────────────────────────────────────────────────┐
│ Wiederkehrende Rechnungen                                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ [ + Neue wiederkehrende Rechnung ]            [🔍 Suchen: ___]     │
│                                                                     │
│ Filter: [Alle ▼] [Aktiv ▼] [Fällig ▼]                             │
│                                                                     │
│ Bezeichnung              │ Lieferant       │ Intervall │ Nächste  │
│─────────────────────────┼─────────────────┼───────────┼──────────│
│ 📦 Adobe Creative Cloud │ Adobe Systems   │ Monatlich │ 01.01.26 │
│                          │ 52,99 € brutto  │           │ in 7 Tg  │
│─────────────────────────┼─────────────────┼───────────┼──────────│
│ 🌐 Domain example.com   │ STRATO          │ Jährlich  │ 15.03.26 │
│                          │ 12,00 € brutto  │           │ in 3 Mon │
│─────────────────────────┼─────────────────┼───────────┼──────────│
│ 💼 Microsoft 365        │ Microsoft       │ Monatlich │ 05.01.26 │
│                          │ 12,50 € brutto  │           │ ⚠️ in 1 T│
│─────────────────────────┼─────────────────┼───────────┼──────────│
│ 🏢 Büromiete             │ Hausverwaltung  │ Monatlich │ 01.01.26 │
│                          │ 500,00 € brutto │           │ in 7 Tg  │
│                                                                     │
│ Gesamt: 4 Abos │ Monatliche Kosten: ~565,49 € │ ⚠️ 1 fällig       │
└─────────────────────────────────────────────────────────────────────┘
```

**Neue Wiederkehrende Rechnung anlegen:**

```
┌──────────────────────────────────────────────────────────┐
│ Neue wiederkehrende Rechnung                             │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ STAMMDATEN:                                              │
│                                                          │
│ Bezeichnung *:  [Adobe Creative Cloud Abo___________]   │
│ Beschreibung:   [Foto & Video Plan___________________]  │
│                                                          │
│ Lieferant:      [Adobe Systems ▼]                       │
│ Kategorie *:    [Software & Lizenzen ▼]                 │
│                                                          │
│ BETRAG:                                                  │
│                                                          │
│ Netto:          [44,53] €                               │
│ USt-Satz:       [19] %                                  │
│ Brutto:         52,99 € (berechnet)                     │
│                                                          │
│ INTERVALL:                                               │
│                                                          │
│ Typ:            ● Monatlich                             │
│                 ○ Quartalsweise                         │
│                 ○ Halbjährlich                          │
│                 ○ Jährlich                              │
│                 ○ Benutzerdefiniert: [__] [Monate ▼]   │
│                                                          │
│ LAUFZEIT:                                                │
│                                                          │
│ Startdatum *:   [01.01.2024]                            │
│ Enddatum:       [ ] Unbegrenzt                          │
│                 [ ] Bis: [__________]                   │
│                                                          │
│ ☑ Automatische Verlängerung (12 Monate)                │
│ Kündigungsfrist: [30] Tage                              │
│                                                          │
│ BENACHRICHTIGUNGEN:                                      │
│                                                          │
│ ☑ Erinnerung senden [7] Tage vor Fälligkeit            │
│ E-Mail:         [admin@beispiel.de___________________]  │
│                                                          │
│ [Abbrechen]                             [Speichern]     │
└──────────────────────────────────────────────────────────┘
```

**Dashboard-Widget:**

```
┌────────────────────────────────────────┐
│ 🔄 Wiederkehrende Rechnungen           │
├────────────────────────────────────────┤
│                                        │
│ ⚠️ FÄLLIG HEUTE (1):                  │
│ - Microsoft 365 (12,50 €)             │
│   [Rechnung erstellen]                 │
│                                        │
│ 📅 FÄLLIG DIESE WOCHE (2):            │
│ - Adobe Creative Cloud (52,99 €)      │
│ - Büromiete (500,00 €)                │
│                                        │
│ 📊 STATISTIKEN:                        │
│ - Aktive Abos: 4                       │
│ - Monatlich: ~565 €                    │
│ - Jährlich: ~6.785 €                   │
│                                        │
│ [Alle anzeigen →]                      │
└────────────────────────────────────────┘
```

---

#### **📋 Workflow-Beispiele**

**Workflow 1: Domain-Renewal**

```
1. SETUP (einmalig):
   ┌──────────────────────────────────┐
   │ Bezeichnung: Domain example.com  │
   │ Lieferant: STRATO                │
   │ Kategorie: Domains & Hosting     │
   │ Betrag: 12,00 € (brutto)         │
   │ Intervall: Jährlich              │
   │ Start: 15.03.2024                │
   │ Erinnerung: 30 Tage vorher       │
   └──────────────────────────────────┘

2. AUTOMATISCH (14.02.2025):
   📧 E-Mail: "Domain example.com läuft in 30 Tagen ab (15.03.2025)"

3. AUTOMATISCH (15.03.2025):
   ✅ Rechnung automatisch erstellt (RE-2025-042)
   📧 E-Mail: "Rechnung für Domain example.com erstellt"

4. MANUELL (User):
   - Rechnung prüfen
   - Zahlung buchen
   - Fertig!
```

**Workflow 2: Software-Abo mit Preisänderung**

```
1. SETUP (einmalig):
   Bezeichnung: Adobe Creative Cloud
   Betrag: 44,53 € netto (52,99 € brutto)
   Intervall: Monatlich

2. MONAT 1-12:
   ✅ Automatische Rechnungserstellung
   ✅ Betrag: 52,99 €

3. MONAT 13 (Preiserhöhung):
   ⚠️ User erhält Rechnung: 59,99 € (statt 52,99 €)

4. USER-AKTION:
   ┌──────────────────────────────────┐
   │ ⚠️ PREISÄNDERUNG ERKANNT         │
   ├──────────────────────────────────┤
   │ Alt: 52,99 €                     │
   │ Neu: 59,99 €                     │
   │ Änderung: +7,00 € (+13,2%)       │
   │                                  │
   │ Möchtest du die wiederkehrende   │
   │ Rechnung aktualisieren?          │
   │                                  │
   │ [Nein] [Ja, aktualisieren]       │
   └──────────────────────────────────┘
```

---

#### **✅ Vorteile**

1. ✅ **Keine vergessenen Zahlungen**: Automatische Erinnerungen
2. ✅ **Budgetplanung**: Monatliche/jährliche Kosten im Blick
3. ✅ **Historische Daten**: Preisentwicklung nachvollziehbar
4. ✅ **Zeitersparnis**: Keine manuelle Erfassung jedes Mal
5. ✅ **Kündigungsfristen**: Rechtzeitige Erinnerung vor Verlängerung
6. ✅ **Kostenoptimierung**: Erkennung ungenutzter Abos

---

#### **🎯 MVP-Entscheidung**

**NICHT in v1.0:**
- v1.0 fokussiert auf Import & Verwaltung bestehender Rechnungen
- Wiederkehrende Rechnungen erfordern Automatisierung (Cron-Jobs, E-Mail)
- Komplex, aber nicht essentiell für Basis-Buchhaltung

**Für v2.0 geplant:**
- Nach v1.0 Release
- User-Feedback abwarten (Bedarf?)
- Integration mit Benachrichtigungs-System

---

#### **📝 Zusammenfassung**

**Feature:** Wiederkehrende Rechnungen für Abos, Domains, Lizenzen, Miete, etc.

**Kernfunktionen:**
- Intervalle (täglich, monatlich, jährlich, benutzerdefiniert)
- Automatische Erstellung
- Benachrichtigungen (X Tage vorher)
- Start-/Enddatum mit Kündigungsfrist
- Preisverlauf & Historie

**Status:** 🔜 **Für v2.0 vorgemerkt**

**Anwendungsfälle:**
- Software-Abos (Adobe, Microsoft, etc.)
- Domains & Hosting
- Miete & Versicherungen
- Lizenzen & Zertifikate
- Mitgliedschaften

---

### **8.9 Produktstammdaten ✅ GEKLÄRT**

**Status:** ✅ **Entscheidung getroffen**

**Entscheidung:** **Hybrid-Lösung** (wie Kundenstamm) mit Templates für verschiedene Produkttypen

---

#### **🎯 Implementierung: Hybrid-Lösung**

**Wie beim Kundenstamm:**
```
┌─────────────────────────────────────────────────┐
│ ⚙️ Einstellungen > Produktstamm                │
├─────────────────────────────────────────────────┤
│                                                 │
│ Beim Erstellen von Rechnungspositionen:       │
│                                                 │
│ ○ Artikel automatisch speichern               │
│   (Alle neuen Artikel werden ohne Nachfrage    │
│    im Produktstamm gespeichert)                │
│                                                 │
│ ● Auf Nachfrage speichern (Standard) ⭐        │
│   (Du wirst gefragt, ob der Artikel gespeichert│
│    werden soll)                                │
│                                                 │
│ ○ Artikel nicht speichern                      │
│   (Artikel werden nur in der Rechnung erfasst, │
│    kein Produktstamm)                          │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Datenbank-Einstellung:**
```sql
-- In der `user` Tabelle:
ALTER TABLE user ADD COLUMN produktstamm_modus TEXT DEFAULT 'nachfrage';
-- Werte: 'automatisch', 'nachfrage', 'nie'
```

---

#### **📊 Datenbank-Schema**

**Haupttabelle `produkte`:**

```sql
CREATE TABLE produkte (
    id INTEGER PRIMARY KEY,

    -- Stammdaten
    artikelnummer TEXT UNIQUE,  -- "ART-001" (manuell oder automatisch)
    name TEXT NOT NULL,  -- ⭐ PFLICHT: "Beratungsstunde", "Laptop Dell XPS 13"
    beschreibung TEXT,  -- Längerer Text für Rechnung

    -- Typ
    typ TEXT NOT NULL DEFAULT 'produkt',  -- 'produkt', 'dienstleistung'

    -- ═══════════════════════════════════════════════════
    -- STANDARD-FELDER (für beide Typen)
    -- ═══════════════════════════════════════════════════

    -- USt-Satz (PFLICHT)
    umsatzsteuer_satz DECIMAL(5,2) NOT NULL DEFAULT 19.0,  -- ⭐ PFLICHT

    -- Verkaufspreis (PFLICHT)
    verkaufspreis_netto DECIMAL(10,2) NOT NULL,  -- ⭐ PFLICHT
    verkaufspreis_brutto DECIMAL(10,2) GENERATED ALWAYS AS (
        verkaufspreis_netto * (1 + umsatzsteuer_satz / 100.0)
    ) STORED,

    -- ═══════════════════════════════════════════════════
    -- NUR FÜR PRODUKTE (typ='produkt')
    -- ═══════════════════════════════════════════════════

    -- Einkaufspreis (PFLICHT bei Produkten)
    einkaufspreis_netto DECIMAL(10,2),  -- ⭐ PFLICHT (bei typ='produkt')
    einkaufspreis_brutto DECIMAL(10,2) GENERATED ALWAYS AS (
        CASE
            WHEN einkaufspreis_netto IS NOT NULL
            THEN einkaufspreis_netto * (1 + umsatzsteuer_satz / 100.0)
            ELSE NULL
        END
    ) STORED,

    -- Erweiterte Felder (Produkte)
    lieferant_id INTEGER,  -- ⭐ Zuordnung zum Lieferanten
    hersteller TEXT,  -- ⭐ z.B. "Dell", "Bosch", etc.

    -- ⭐⭐ EAN-Code Support (WICHTIG!) ⭐⭐
    ean_code TEXT,  -- ⭐ EAN-13 (13-stellig) oder EAN-8 (8-stellig)
    ean_typ TEXT,  -- 'EAN-13', 'EAN-8', 'UPC', 'ISBN'

    artikelcode TEXT,  -- ⭐ Interner Code / SKU
    einheit TEXT DEFAULT 'Stück',  -- ⭐ 'Stück', 'kg', 'l', 'm', etc.

    -- Lagerbestand (erweitert)
    lagerbestand DECIMAL(10,2) DEFAULT 0.00,  -- ⭐ Aktueller Bestand
    lagerbestand_negativ_erlaubt BOOLEAN DEFAULT 0,  -- ⭐ Negativer Bestand?
    mindestbestand DECIMAL(10,2) DEFAULT 0.00,  -- ⭐ Warnung bei Unterschreitung

    -- ═══════════════════════════════════════════════════
    -- KATEGORIE (evt. später - optional für v1.0)
    -- ═══════════════════════════════════════════════════

    kategorie_id INTEGER,  -- Zuordnung zu Einnahmen-Kategorie (später)

    -- ═══════════════════════════════════════════════════
    -- METADATEN
    -- ═══════════════════════════════════════════════════

    ist_aktiv BOOLEAN DEFAULT 1,
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    aktualisiert_am TIMESTAMP,

    -- Foreign Keys
    FOREIGN KEY (lieferant_id) REFERENCES lieferanten(id),
    FOREIGN KEY (kategorie_id) REFERENCES kategorien(id)  -- Optional für später

    -- Constraints
    CHECK (typ IN ('produkt', 'dienstleistung')),
    CHECK (
        -- Bei Produkten: Einkaufspreis PFLICHT
        (typ = 'produkt' AND einkaufspreis_netto IS NOT NULL) OR
        (typ = 'dienstleistung')
    ),
    CHECK (
        -- Bei Dienstleistungen: Lagerfelder NULL
        (typ = 'produkt') OR
        (typ = 'dienstleistung' AND lagerbestand IS NULL AND mindestbestand IS NULL)
    )
);

-- Index für EAN-Code (WICHTIG für schnelle Suche!)
CREATE INDEX idx_produkte_ean ON produkte(ean_code);
CREATE INDEX idx_produkte_artikelcode ON produkte(artikelcode);
CREATE INDEX idx_produkte_name ON produkte(name);
CREATE INDEX idx_produkte_typ ON produkte(typ);
```

---

#### **🏷️ EAN-Code Support (WICHTIG!)**

**EAN-Code Typen:**

| Typ | Länge | Verwendung | Beispiel |
|-----|-------|------------|----------|
| **EAN-13** | 13 Ziffern | Standard für Retail | `4012345678901` |
| **EAN-8** | 8 Ziffern | Kleine Artikel | `12345670` |
| **UPC** | 12 Ziffern | USA/Kanada | `012345678905` |
| **ISBN** | 13 Ziffern | Bücher (seit 2007) | `978-3-16-148410-0` |

**EAN-Validierung (Prüfziffer):**

```python
def validate_ean13(ean: str) -> bool:
    """
    Validiert EAN-13 Code (Prüfziffer)

    Args:
        ean: 13-stelliger EAN-Code

    Returns:
        True, wenn gültig
    """
    if not ean or len(ean) != 13 or not ean.isdigit():
        return False

    # Prüfziffer berechnen
    checksum = 0
    for i, digit in enumerate(ean[:12]):  # Erste 12 Ziffern
        if i % 2 == 0:
            checksum += int(digit)  # Ungerade Positionen (1, 3, 5, ...) → ×1
        else:
            checksum += int(digit) * 3  # Gerade Positionen (2, 4, 6, ...) → ×3

    # Prüfziffer = (10 - (Summe mod 10)) mod 10
    check_digit = (10 - (checksum % 10)) % 10

    return int(ean[12]) == check_digit


def validate_ean8(ean: str) -> bool:
    """
    Validiert EAN-8 Code (Prüfziffer)
    """
    if not ean or len(ean) != 8 or not ean.isdigit():
        return False

    checksum = 0
    for i, digit in enumerate(ean[:7]):  # Erste 7 Ziffern
        if i % 2 == 0:
            checksum += int(digit) * 3  # Ungerade Positionen → ×3
        else:
            checksum += int(digit)  # Gerade Positionen → ×1

    check_digit = (10 - (checksum % 10)) % 10
    return int(ean[7]) == check_digit


def validate_ean(ean: str, ean_typ: str = None) -> tuple[bool, str]:
    """
    Validiert EAN-Code (auto-detect oder spezifisch)

    Args:
        ean: EAN-Code
        ean_typ: 'EAN-13', 'EAN-8', 'UPC', 'ISBN' (optional)

    Returns:
        (gültig, erkannter_typ)
    """
    if not ean:
        return False, None

    # Nur Ziffern und Bindestriche erlauben
    ean_clean = ean.replace('-', '').replace(' ', '')

    if ean_typ == 'EAN-13' or (ean_typ is None and len(ean_clean) == 13):
        if validate_ean13(ean_clean):
            return True, 'EAN-13'

    if ean_typ == 'EAN-8' or (ean_typ is None and len(ean_clean) == 8):
        if validate_ean8(ean_clean):
            return True, 'EAN-8'

    if ean_typ == 'UPC' or (ean_typ is None and len(ean_clean) == 12):
        # UPC → EAN-13 (Präfix '0' hinzufügen)
        ean13 = '0' + ean_clean
        if validate_ean13(ean13):
            return True, 'UPC'

    if ean_typ == 'ISBN' or (ean_typ is None and (ean_clean.startswith('978') or ean_clean.startswith('979'))):
        # ISBN-13 ist EAN-13
        if len(ean_clean) == 13 and validate_ean13(ean_clean):
            return True, 'ISBN'

    return False, None
```

**EAN-Scanner Integration:**

```python
def import_produkt_from_ean(ean_code: str):
    """
    Importiert Produkt aus externer Datenbank via EAN

    Quellen:
    - OpenEAN (https://openean.kaufland.de) - Kostenlos
    - EAN-Search.org API
    - GS1 API (kostenpflichtig)
    """
    # 1. Validierung
    valid, typ = validate_ean(ean_code)
    if not valid:
        raise ValueError(f"Ungültiger EAN-Code: {ean_code}")

    # 2. Suche in externer Datenbank
    produkt_info = fetch_ean_info(ean_code)  # API-Call

    # 3. Produkt anlegen
    produkt = Produkt(
        ean_code=ean_code,
        ean_typ=typ,
        name=produkt_info.get('name'),
        hersteller=produkt_info.get('brand'),
        beschreibung=produkt_info.get('description'),
        # Preise manuell ergänzen
    )

    return produkt
```

**UI - EAN-Scanner:**

```
┌────────────────────────────────────────────┐
│ Neues Produkt anlegen                      │
├────────────────────────────────────────────┤
│                                            │
│ ┌──────────────────────────────────────┐  │
│ │ 📷 EAN-Scanner                        │  │
│ ├──────────────────────────────────────┤  │
│ │                                      │  │
│ │ EAN-Code: [____________] [Scannen]   │  │
│ │                                      │  │
│ │ ℹ️ Scanne Barcode oder gib EAN ein  │  │
│ └──────────────────────────────────────┘  │
│                                            │
│ ─── ODER MANUELL EINGEBEN ───              │
│                                            │
│ Name *: [_________________________]        │
│ Hersteller: [____________________]         │
│ EAN-Code: [_______________] ✅ Gültig     │
│ Artikelcode: [_______________]             │
│                                            │
│ ...                                        │
│                                            │
│ [Abbrechen]             [Speichern]        │
└────────────────────────────────────────────┘
```

---

#### **📋 Templates für verschiedene Produkttypen**

**Template-System (für v2.0):**

```python
PRODUKT_TEMPLATES = {
    'dienstleistung_beratung': {
        'name': 'Dienstleistung (Beratung)',
        'beschreibung': 'Für Berater, Coaches, Freiberufler',
        'typ': 'dienstleistung',
        'felder': [
            'name',  # z.B. "Beratungsstunde"
            'beschreibung',
            'umsatzsteuer_satz',
            'verkaufspreis_netto',
            'einheit'  # 'Stunde', 'Tag', 'Projekt'
        ],
        'pflicht': ['name', 'umsatzsteuer_satz', 'verkaufspreis_netto'],
        'defaults': {
            'einheit': 'Stunde',
            'umsatzsteuer_satz': 19.0
        },
        'felder_ausblenden': [
            'einkaufspreis_netto',
            'lieferant_id',
            'hersteller',
            'ean_code',
            'lagerbestand',
            'mindestbestand'
        ]
    },

    'dienstleistung_handwerk': {
        'name': 'Dienstleistung (Handwerk)',
        'beschreibung': 'Für Handwerker (Arbeitsstunden)',
        'typ': 'dienstleistung',
        'felder': [
            'name',  # z.B. "Elektriker Arbeitsstunde"
            'beschreibung',
            'umsatzsteuer_satz',
            'verkaufspreis_netto',
            'einheit'
        ],
        'pflicht': ['name', 'umsatzsteuer_satz', 'verkaufspreis_netto'],
        'defaults': {
            'einheit': 'Stunde',
            'umsatzsteuer_satz': 19.0
        },
        'felder_ausblenden': [
            'einkaufspreis_netto',
            'lieferant_id',
            'hersteller',
            'ean_code',
            'lagerbestand',
            'mindestbestand'
        ]
    },

    'produkt_handelsware': {
        'name': 'Produkt (Handelsware)',
        'beschreibung': 'Für Händler (Einkauf & Verkauf)',
        'typ': 'produkt',
        'felder': [
            'name',
            'beschreibung',
            'hersteller',
            'ean_code',  # ⭐ WICHTIG!
            'artikelcode',
            'einheit',
            'umsatzsteuer_satz',
            'einkaufspreis_netto',  # PFLICHT
            'verkaufspreis_netto',  # PFLICHT
            'lieferant_id',
            'lagerbestand',
            'mindestbestand'
        ],
        'pflicht': ['name', 'umsatzsteuer_satz', 'einkaufspreis_netto', 'verkaufspreis_netto'],
        'defaults': {
            'einheit': 'Stück',
            'umsatzsteuer_satz': 19.0,
            'lagerbestand': 0.00,
            'mindestbestand': 5.00
        },
        'besonderheiten': [
            'EAN-Code empfohlen (für Barcode-Scanner)',
            'Lieferant zuordnen für Nachbestellung',
            'Mindestbestand für Warnung bei niedrigem Lagerstand'
        ]
    },

    'produkt_eigenproduktion': {
        'name': 'Produkt (Eigenproduktion)',
        'beschreibung': 'Für selbst hergestellte Produkte',
        'typ': 'produkt',
        'felder': [
            'name',
            'beschreibung',
            'artikelcode',
            'einheit',
            'umsatzsteuer_satz',
            'einkaufspreis_netto',  # Materialkosten
            'verkaufspreis_netto',
            'lagerbestand',
            'mindestbestand'
        ],
        'pflicht': ['name', 'umsatzsteuer_satz', 'einkaufspreis_netto', 'verkaufspreis_netto'],
        'defaults': {
            'einheit': 'Stück',
            'umsatzsteuer_satz': 19.0,
            'lagerbestand': 0.00
        },
        'felder_ausblenden': [
            'ean_code',  # Keine EAN für Eigenproduktion
            'lieferant_id'  # Kein Lieferant
        ],
        'besonderheiten': [
            'Einkaufspreis = Materialkosten',
            '⚠️ Kalkulations-Modul für v2.0 geplant! (Materialkosten + Arbeitszeit)'
        ]
    },

    'produkt_download': {
        'name': 'Digitales Produkt (Download)',
        'beschreibung': 'Für E-Books, Software, etc.',
        'typ': 'produkt',
        'felder': [
            'name',
            'beschreibung',
            'umsatzsteuer_satz',
            'verkaufspreis_netto'
        ],
        'pflicht': ['name', 'umsatzsteuer_satz', 'verkaufspreis_netto'],
        'defaults': {
            'einheit': 'Lizenz',
            'umsatzsteuer_satz': 19.0,
            'einkaufspreis_netto': 0.00  # Keine Materialkosten
        },
        'felder_ausblenden': [
            'ean_code',
            'lieferant_id',
            'hersteller',
            'lagerbestand',  # Kein Lager bei Downloads
            'mindestbestand'
        ]
    },

    'standard': {
        'name': 'Standard (Universal)',
        'beschreibung': 'Alle Felder verfügbar',
        'typ': None,  # User wählt
        'felder': 'alle',
        'pflicht': ['name', 'typ', 'umsatzsteuer_satz', 'verkaufspreis_netto'],
        'defaults': {
            'einheit': 'Stück',
            'umsatzsteuer_satz': 19.0
        }
    }
}
```

---

#### **💰 Kalkulations-Modul (für v2.0 vorgemerkt)**

**Zweck:**
- Automatische Berechnung von Verkaufspreisen
- Berücksichtigung von Materialkosten, Arbeitszeit, Gemeinkosten
- Gewinnmarge-Kalkulation

**Geplante Funktionen:**

```python
# ⚠️ FÜR v2.0 GEPLANT - NICHT IN v1.0!

def berechne_verkaufspreis(
    materialkosten: Decimal,  # Einkaufspreis
    arbeitszeit_stunden: Decimal,
    stundensatz: Decimal,
    gemeinkostenzuschlag: Decimal = Decimal('0.15'),  # 15%
    gewinnmarge: Decimal = Decimal('0.20')  # 20%
) -> Decimal:
    """
    Kalkuliert Verkaufspreis für selbst hergestellte Produkte

    Beispiel:
    - Materialkosten: 50,00 €
    - Arbeitszeit: 2 Stunden
    - Stundensatz: 40,00 €
    - Gemeinkosten: 15%
    - Gewinnmarge: 20%

    Rechnung:
    - Materialkosten: 50,00 €
    - Arbeitskosten: 2h × 40 €/h = 80,00 €
    - Herstellkosten: 130,00 €
    - + Gemeinkosten (15%): 19,50 €
    - Selbstkosten: 149,50 €
    - + Gewinnmarge (20%): 29,90 €
    - = Verkaufspreis (netto): 179,40 €
    """
    arbeitskosten = arbeitszeit_stunden * stundensatz
    herstellkosten = materialkosten + arbeitskosten
    gemeinkosten = herstellkosten * gemeinkostenzuschlag
    selbstkosten = herstellkosten + gemeinkosten
    gewinn = selbstkosten * gewinnmarge
    verkaufspreis = selbstkosten + gewinn

    return verkaufspreis.quantize(Decimal('0.01'))


# Datenbank-Schema-Erweiterung für v2.0:
"""
ALTER TABLE produkte ADD COLUMN kalkulation_aktiv BOOLEAN DEFAULT 0;
ALTER TABLE produkte ADD COLUMN kalkulation_arbeitszeit_stunden DECIMAL(10,2);
ALTER TABLE produkte ADD COLUMN kalkulation_stundensatz DECIMAL(10,2);
ALTER TABLE produkte ADD COLUMN kalkulation_gemeinkostenzuschlag DECIMAL(5,2) DEFAULT 15.0;
ALTER TABLE produkte ADD COLUMN kalkulation_gewinnmarge DECIMAL(5,2) DEFAULT 20.0;
"""
```

**UI - Kalkulations-Assistent (v2.0):**

```
┌───────────────────────────────────────────────┐
│ 🧮 Kalkulations-Assistent                    │
├───────────────────────────────────────────────┤
│                                               │
│ Produkt: Handgemachter Holztisch             │
│                                               │
│ 1️⃣ MATERIALKOSTEN:                           │
│    Holz, Schrauben, Lack: 50,00 €            │
│                                               │
│ 2️⃣ ARBEITSZEIT:                               │
│    Stunden: [__2,0__]                         │
│    Stundensatz: [_40,00_] €/h                │
│    → Arbeitskosten: 80,00 €                   │
│                                               │
│ 3️⃣ GEMEINKOSTEN:                              │
│    Zuschlag: [_15_] %                         │
│    → Gemeinkosten: 19,50 €                    │
│                                               │
│ 4️⃣ GEWINNMARGE:                               │
│    Marge: [_20_] %                            │
│    → Gewinn: 29,90 €                          │
│                                               │
│ ═══════════════════════════════════════       │
│ VERKAUFSPREIS (netto): 179,40 €               │
│ + USt 19%:              34,09 €               │
│ ─────────────────────────────────             │
│ VERKAUFSPREIS (brutto): 213,49 €              │
│ ═══════════════════════════════════════       │
│                                               │
│ [Abbrechen]    [Übernehmen]                   │
└───────────────────────────────────────────────┘
```

**Status:** 🔜 **Für v2.0 geplant**

---

#### **💻 Code-Implementierung**

```python
# models.py
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

@dataclass
class Produkt:
    id: Optional[int] = None

    # Stammdaten
    artikelnummer: Optional[str] = None
    name: str = ''  # PFLICHT
    beschreibung: Optional[str] = None
    typ: str = 'produkt'  # 'produkt' | 'dienstleistung'

    # USt-Satz (PFLICHT)
    umsatzsteuer_satz: Decimal = Decimal('19.0')

    # Verkaufspreis (PFLICHT)
    verkaufspreis_netto: Decimal = Decimal('0.00')

    # Einkaufspreis (PFLICHT bei Produkten)
    einkaufspreis_netto: Optional[Decimal] = None

    # Erweiterte Felder
    lieferant_id: Optional[int] = None
    hersteller: Optional[str] = None

    # EAN-Code
    ean_code: Optional[str] = None
    ean_typ: Optional[str] = None  # 'EAN-13', 'EAN-8', 'UPC', 'ISBN'

    artikelcode: Optional[str] = None
    einheit: str = 'Stück'

    # Lager
    lagerbestand: Decimal = Decimal('0.00')
    lagerbestand_negativ_erlaubt: bool = False
    mindestbestand: Decimal = Decimal('0.00')

    # Kategorie (optional)
    kategorie_id: Optional[int] = None

    # Metadaten
    ist_aktiv: bool = True
    erstellt_am: Optional[datetime] = None
    aktualisiert_am: Optional[datetime] = None

    @property
    def verkaufspreis_brutto(self) -> Decimal:
        """Berechnet Brutto-Verkaufspreis"""
        return (self.verkaufspreis_netto * (1 + self.umsatzsteuer_satz / 100)).quantize(Decimal('0.01'))

    @property
    def einkaufspreis_brutto(self) -> Optional[Decimal]:
        """Berechnet Brutto-Einkaufspreis"""
        if self.einkaufspreis_netto is None:
            return None
        return (self.einkaufspreis_netto * (1 + self.umsatzsteuer_satz / 100)).quantize(Decimal('0.01'))

    @property
    def gewinnmarge_prozent(self) -> Optional[Decimal]:
        """Berechnet Gewinnmarge in Prozent"""
        if self.einkaufspreis_netto is None or self.einkaufspreis_netto == 0:
            return None
        gewinn = self.verkaufspreis_netto - self.einkaufspreis_netto
        marge = (gewinn / self.einkaufspreis_netto) * 100
        return marge.quantize(Decimal('0.01'))

    @property
    def gewinn_pro_stueck(self) -> Optional[Decimal]:
        """Berechnet Gewinn pro Stück (netto)"""
        if self.einkaufspreis_netto is None:
            return None
        return (self.verkaufspreis_netto - self.einkaufspreis_netto).quantize(Decimal('0.01'))

    @property
    def lagerbestand_kritisch(self) -> bool:
        """Prüft, ob Lagerbestand unter Mindestbestand"""
        return self.lagerbestand < self.mindestbestand

    def validate(self) -> list[str]:
        """Validiert Pflichtfelder"""
        errors = []

        if not self.name:
            errors.append("Name ist Pflichtfeld")

        if not self.typ or self.typ not in ['produkt', 'dienstleistung']:
            errors.append("Typ muss 'produkt' oder 'dienstleistung' sein")

        if self.umsatzsteuer_satz is None:
            errors.append("USt-Satz ist Pflichtfeld")

        if self.verkaufspreis_netto is None or self.verkaufspreis_netto <= 0:
            errors.append("Verkaufspreis (netto) ist Pflichtfeld und muss > 0 sein")

        # Bei Produkten: Einkaufspreis PFLICHT
        if self.typ == 'produkt':
            if self.einkaufspreis_netto is None:
                errors.append("Einkaufspreis ist bei Produkten Pflichtfeld")

        # EAN-Validierung
        if self.ean_code:
            valid, detected_typ = validate_ean(self.ean_code, self.ean_typ)
            if not valid:
                errors.append(f"EAN-Code ungültig: {self.ean_code}")
            elif detected_typ != self.ean_typ and self.ean_typ:
                errors.append(f"EAN-Typ stimmt nicht überein: erwartet {self.ean_typ}, erkannt {detected_typ}")

        return errors


# services/produktstamm.py
from models import Produkt

def create_produkt_from_template(template_name: str, **kwargs) -> Produkt:
    """
    Erstellt Produkt aus Template

    Args:
        template_name: 'dienstleistung_beratung', 'produkt_handelsware', etc.
        **kwargs: Überschreibt Template-Defaults

    Returns:
        Produkt-Objekt mit Template-Defaults
    """
    template = PRODUKT_TEMPLATES.get(template_name, PRODUKT_TEMPLATES['standard'])

    produkt_data = {
        'typ': template.get('typ'),
        **template.get('defaults', {}),
        **kwargs
    }

    return Produkt(**produkt_data)
```

---

#### **🎨 UI-Mockups**

**Produktverwaltung (Übersicht):**

```
┌─────────────────────────────────────────────────────────────────────┐
│ Stammdaten → Produkte / Dienstleistungen                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ [ + Neues Produkt ] [ + Neue Dienstleistung ]    [🔍 Suchen: ___] │
│                                                                     │
│ Filter: [Alle ▼] [Aktiv ▼] [Typ ▼]                                │
│                                                                     │
│ Art.-Nr. │ Name                  │ Typ    │ Preis (netto) │ Lager │
│──────────┼───────────────────────┼────────┼───────────────┼───────│
│ DL-001   │ Beratungsstunde       │ DL     │    80,00 €    │   -   │
│ ART-001  │ Laptop Dell XPS 13    │ Prod   │ 1.000,00 €    │  15   │
│ ART-002  │ Schrauben M8 (100St.) │ Prod   │     5,00 €    │ ⚠️ 3  │
│ DL-002   │ Elektriker Arbeit     │ DL     │    50,00 €    │   -   │
│                                                                     │
│ Gesamt: 4 Artikel │ Lagerwert: 15.015,00 € │ ⚠️ 1 Artikel kritisch│
└─────────────────────────────────────────────────────────────────────┘
```

**Neues Produkt anlegen (Template-Auswahl):**

```
┌────────────────────────────────────────────┐
│ Neues Produkt / Dienstleistung anlegen     │
├────────────────────────────────────────────┤
│                                            │
│ Wähle eine Vorlage:                        │
│                                            │
│ ○ Dienstleistung (Beratung)                │
│   Für Berater, Coaches, Freiberufler      │
│                                            │
│ ○ Dienstleistung (Handwerk)                │
│   Für Handwerker (Arbeitsstunden)         │
│                                            │
│ ○ Produkt (Handelsware)                    │
│   Für Händler (Einkauf & Verkauf)         │
│                                            │
│ ○ Produkt (Eigenproduktion)                │
│   Für selbst hergestellte Produkte        │
│                                            │
│ ○ Digitales Produkt (Download)             │
│   Für E-Books, Software, etc.             │
│                                            │
│ ○ Standard (Universal)                     │
│   Alle Felder verfügbar                   │
│                                            │
│ [Abbrechen]                    [Weiter]    │
└────────────────────────────────────────────┘
```

**Produkt bearbeiten (Produkt Handelsware):**

```
┌──────────────────────────────────────────────────────────┐
│ Produkt bearbeiten: Laptop Dell XPS 13                   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ STAMMDATEN:                                              │
│                                                          │
│ Name *:        [Laptop Dell XPS 13___________________]  │
│ Artikelnummer: [ART-001] (automatisch)                  │
│ Hersteller:    [Dell_______________________________]    │
│ Beschreibung:  [13" Ultrabook, 16GB RAM, 512GB SSD]     │
│                [________________________________]         │
│                                                          │
│ EAN-CODE: ⭐                                             │
│ EAN-Code:      [4012345678901] ✅ EAN-13 gültig         │
│ Artikelcode:   [DELL-XPS13-2024__________________]      │
│                                                          │
│ PREISE:                                                  │
│                                                          │
│ USt-Satz *:    [19,0] %                                 │
│                                                          │
│ Einkaufspreis *:                                         │
│   Netto:       [1.000,00] €                             │
│   Brutto:      1.190,00 € (berechnet)                   │
│                                                          │
│ Verkaufspreis *:                                         │
│   Netto:       [1.200,00] €                             │
│   Brutto:      1.428,00 € (berechnet)                   │
│   Gewinnmarge: 20,00 % (200,00 € Gewinn/Stück)         │
│                                                          │
│ LAGER:                                                   │
│                                                          │
│ Einheit:       [Stück ▼]                                │
│ Lagerbestand:  [15,00] Stück                            │
│ Mindestbestand:[5,00] Stück (⚠️ Warnung bei <5)        │
│ ☐ Negativer Lagerbestand erlaubt                        │
│                                                          │
│ ZUORDNUNG:                                               │
│                                                          │
│ Lieferant:     [Tech-Großhandel GmbH ▼]                │
│ Kategorie:     [Computer & Elektronik ▼] (optional)    │
│                                                          │
│ ☑ Artikel ist aktiv                                     │
│                                                          │
│ [Löschen]   [Abbrechen]              [Speichern]        │
└──────────────────────────────────────────────────────────┘
```

**Dienstleistung bearbeiten (Beratung):**

```
┌──────────────────────────────────────────────────────────┐
│ Dienstleistung bearbeiten: Beratungsstunde               │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ STAMMDATEN:                                              │
│                                                          │
│ Name *:        [Beratungsstunde____________________]    │
│ Artikelnummer: [DL-001] (automatisch)                   │
│ Beschreibung:  [Strategieberatung für mittelständische] │
│                [Unternehmen_________________________]   │
│                                                          │
│ PREISE:                                                  │
│                                                          │
│ USt-Satz *:    [19,0] %                                 │
│                                                          │
│ Verkaufspreis *:                                         │
│   Netto:       [80,00] €                                │
│   Brutto:      95,20 € (berechnet)                      │
│                                                          │
│ Einheit:       [Stunde ▼]                               │
│                                                          │
│ ZUORDNUNG:                                               │
│                                                          │
│ Kategorie:     [Beratungsleistungen ▼] (optional)      │
│                                                          │
│ ☑ Dienstleistung ist aktiv                              │
│                                                          │
│ [Löschen]   [Abbrechen]              [Speichern]        │
└──────────────────────────────────────────────────────────┘
```

---

#### **💰 Anschaffungskosten & Anschaffungsnebenkosten** ⚖️ **WICHTIG**

**Problem:**
- Einkaufspreis (netto) vom Lieferanten: z.B. 1.000 €
- + Frachtkosten: 50 €
- + Versicherung: 10 €
- + Mautgebühren: 5 €
- + CO2-Abgabe: 15 €
- **= Was ist der "echte" Netto-EK?**

**Frage:** Gehören Nebenkosten zum Einkaufspreis? Wie steuerlich behandeln?

---

##### **Rechtsgrundlage: §255 HGB - Anschaffungskosten**

**§255 Abs. 1 HGB:**

```
Anschaffungskosten sind die Aufwendungen, die geleistet werden,
um einen Vermögensgegenstand zu erwerben und ihn in einen
betriebsbereiten Zustand zu versetzen, soweit sie dem
Vermögensgegenstand einzeln zugeordnet werden können.

Zu den Anschaffungskosten gehören auch die Nebenkosten sowie
die nachträglichen Anschaffungskosten.

Anschaffungskostenminderungen sind abzusetzen.
```

**Bedeutung:**
- Anschaffungskosten = **Einkaufspreis + Nebenkosten - Minderungen**
- NICHT nur der Preis auf der Lieferantenrechnung!

---

##### **Was gehört zu den Anschaffungskosten?**

**Formel:**

```
┌────────────────────────────────────────────────────────┐
│ ANSCHAFFUNGSKOSTEN (= "echter" Netto-EK)              │
├────────────────────────────────────────────────────────┤
│                                                        │
│ + Anschaffungspreis (netto vom Lieferanten)           │
│   Beispiel: 1.000,00 €                                │
│                                                        │
│ + ANSCHAFFUNGSNEBENKOSTEN:                            │
│   ├─ Frachtkosten / Transportkosten     + 50,00 €    │
│   ├─ Versicherung (während Transport)   + 10,00 €    │
│   ├─ Zölle, Einfuhrabgaben               +  0,00 €    │
│   ├─ Verpackung (nicht rückgabefähig)    +  5,00 €    │
│   ├─ Montagekosten                       +  0,00 €    │
│   ├─ CO2-Abgaben (beim Import)           + 15,00 €    │
│   ├─ Mautgebühren (zuordenbar)           +  5,00 €    │
│   └─ Lagerkosten (bis Inbetriebnahme)    +  0,00 €    │
│                                              ─────────  │
│                                       Summe:  85,00 €  │
│                                                        │
│ - ANSCHAFFUNGSPREISMINDERUNGEN:                       │
│   ├─ Rabatte / Preisnachlässe            -  0,00 €    │
│   ├─ Skonto (z.B. 2% bei Zahlung 10 Tg) - 20,00 €    │
│   └─ Boni / Rückvergütungen              -  0,00 €    │
│                                              ─────────  │
│                                       Summe: -20,00 €  │
│                                                        │
│ ═══════════════════════════════════════════════════    │
│ = ANSCHAFFUNGSKOSTEN (netto):        1.065,00 €       │
│ ═══════════════════════════════════════════════════    │
│                                                        │
│ + Umsatzsteuer (19%):                    202,35 €     │
│ ─────────────────────────────────────────────────      │
│ = ANSCHAFFUNGSKOSTEN (brutto):       1.267,35 €       │
└────────────────────────────────────────────────────────┘
```

---

##### **Welche Nebenkosten gehören DAZU?**

**✅ IMMER Anschaffungsnebenkosten:**

| Nebenkosten | Zuordnung | Beispiel |
|-------------|-----------|----------|
| **Frachtkosten** | ✅ JA | Transport vom Lieferanten zum Lager |
| **Transportversicherung** | ✅ JA | Versicherung während Transport |
| **Zölle, Einfuhrabgaben** | ✅ JA | Import aus Nicht-EU |
| **Verpackung (nicht rückgabefähig)** | ✅ JA | Einwegpaletten, Kisten |
| **Montagekosten** | ✅ JA | Zusammenbau vor Inbetriebnahme |
| **CO2-Abgaben** | ✅ JA | CO2-Steuer beim Import |
| **Prüfkosten** | ✅ JA | Qualitätsprüfung vor Nutzung |

**❌ KEINE Anschaffungsnebenkosten:**

| Nebenkosten | Zuordnung | Begründung |
|-------------|-----------|------------|
| **Lagerkosten (laufend)** | ❌ NEIN | Betriebsausgabe (nicht Anschaffung) |
| **Verwaltungskosten** | ❌ NEIN | Gemeinkosten (nicht zuordenbar) |
| **Finanzierungskosten** | ❌ NEIN | Keine Anschaffungskosten (§255 Abs. 3 HGB) |
| **Mautgebühren (allgemein)** | ⚠️ TEILS | Nur wenn dem Artikel zuordenbar |
| **Verpackung (rückgabefähig)** | ❌ NEIN | Wird zurückgegeben (z.B. Europaletten) |

---

##### **Unterschied: Anlagevermögen vs. Umlaufvermögen**

**Bei ANLAGEVERMÖGEN (Maschinen, Fahrzeuge, etc.):**

```
Beispiel: Maschine kaufen

Anschaffungspreis:       10.000,00 € (netto)
+ Frachtkosten:             500,00 €
+ Montagekosten:          1.000,00 €
─────────────────────────────────────
= Anschaffungskosten:    11.500,00 € (netto)

⚠️ PFLICHT: Nebenkosten MÜSSEN hinzugerechnet werden!

Abschreibung:
AfA linear (10 Jahre) = 11.500 € / 10 = 1.150 € pro Jahr
```

**Warum PFLICHT?**
- §255 HGB zwingt dazu
- Abschreibung erfolgt über **gesamte** Anschaffungskosten
- Finanzamt akzeptiert keine separate Verbuchung

---

**Bei UMLAUFVERMÖGEN (Waren, Material):**

```
Beispiel: Waren kaufen (für Wiederverkauf)

Einkaufspreis:            1.000,00 € (netto)
+ Frachtkosten:              50,00 €
─────────────────────────────────────
= Anschaffungskosten:     1.050,00 € (netto)

⚠️ SOLLTE hinzugerechnet werden (§255 HGB)
✅ ABER: Praktische Vereinfachung möglich!
```

**Praktische Vereinfachung (für Kleinunternehmer):**

```
Variante 1 (KORREKT nach §255 HGB):
- Ware: 1.050,00 € Einkaufspreis (inkl. Fracht)
- Lagerwert: 1.050,00 €
- Bei Verkauf: Wareneinsatz 1.050,00 €

Variante 2 (VEREINFACHT - toleriert vom Finanzamt):
- Ware: 1.000,00 € Einkaufspreis
- Fracht: 50,00 € Betriebsausgabe (separate Kategorie)
- Lagerwert: 1.000,00 €
- Bei Verkauf: Wareneinsatz 1.000,00 € + Fracht 50,00 €
```

**Wann Variante 2 erlaubt?**
- ✅ Bei geringem Warenwert
- ✅ Bei häufigen kleinen Bestellungen
- ✅ Wenn Zuordnung zu einzelnem Artikel schwierig
- ❌ NICHT bei großen Anschaffungen (z.B. Container-Import)

---

##### **Steuerliche Behandlung**

**Umsatzsteuer:**

```
Anschaffungspreis (netto):    1.000,00 €
+ Frachtkosten (netto):          50,00 €
─────────────────────────────────────────
= Anschaffungskosten (netto): 1.050,00 €
+ Umsatzsteuer 19%:             199,50 €
─────────────────────────────────────────
= Anschaffungskosten (brutto):1.249,50 €

Vorsteuerabzug: 199,50 € (wenn berechtigt)
```

**Wichtig:**
- Fracht, Spesen etc. unterliegen der Umsatzsteuer (meist 19%)
- Vorsteuerabzug möglich (wenn nicht Kleinunternehmer §19 UStG)

---

**Einkommensteuer / Körperschaftsteuer:**

**Anlagevermögen:**
- Anschaffungskosten werden über Nutzungsdauer abgeschrieben
- Abschreibung = Betriebsausgabe (steuermindernd)

**Umlaufvermögen:**
- Wareneinsatz = Betriebsausgabe (steuermindernd)
- Berechnung: Anfangsbestand + Einkäufe - Endbestand

---

##### **Implementierung in RechnungsFee**

**Erweiterung Datenbank-Schema (Produktstammdaten):**

```sql
ALTER TABLE produkte ADD COLUMN einkaufspreis_anschaffungskosten DECIMAL(10,2);
ALTER TABLE produkte ADD COLUMN einkaufspreis_nebenkosten DECIMAL(10,2) DEFAULT 0.00;
ALTER TABLE produkte ADD COLUMN einkaufspreis_minderungen DECIMAL(10,2) DEFAULT 0.00;

-- Berechnung der Anschaffungskosten
ALTER TABLE produkte ADD COLUMN einkaufspreis_gesamt DECIMAL(10,2) GENERATED ALWAYS AS (
    einkaufspreis_netto + einkaufspreis_nebenkosten - einkaufspreis_minderungen
) STORED;
```

**Detaillierte Nebenkosten-Erfassung:**

```sql
CREATE TABLE produkt_anschaffungsnebenkosten (
    id INTEGER PRIMARY KEY,
    produkt_id INTEGER NOT NULL,
    typ TEXT NOT NULL,  -- 'fracht', 'versicherung', 'zoll', 'montage', 'co2', 'maut', etc.
    bezeichnung TEXT,
    betrag_netto DECIMAL(10,2) NOT NULL,
    betrag_brutto DECIMAL(10,2),
    datum DATE,
    belegt_durch TEXT,  -- Verweis auf Rechnung/Beleg

    FOREIGN KEY (produkt_id) REFERENCES produkte(id),
    CHECK (typ IN ('fracht', 'versicherung', 'zoll', 'montage', 'co2', 'maut', 'verpackung', 'pruefung', 'sonstige'))
);
```

---

##### **UI-Konzept (erweitert)**

**Produkt bearbeiten - Erweiterte Ansicht:**

```
┌──────────────────────────────────────────────────────────┐
│ Produkt bearbeiten: Laptop Dell XPS 13                   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ PREISE:                                                  │
│                                                          │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ EINKAUFSPREIS (detailliert):                        │ │
│ ├─────────────────────────────────────────────────────┤ │
│ │                                                     │ │
│ │ Anschaffungspreis (netto): [1.000,00] €             │ │
│ │                                                     │ │
│ │ + ANSCHAFFUNGSNEBENKOSTEN:                          │ │
│ │   Frachtkosten:              [  50,00] €            │ │
│ │   Versicherung:              [  10,00] €            │ │
│ │   Zölle:                     [   0,00] €            │ │
│ │   CO2-Abgaben:               [  15,00] €            │ │
│ │   Sonstige:                  [   0,00] €            │ │
│ │                              ─────────               │ │
│ │   Summe Nebenkosten:            75,00 €             │ │
│ │                                                     │ │
│ │ - ANSCHAFFUNGSPREISMINDERUNGEN:                     │ │
│ │   Skonto (2%):               [  20,00] €            │ │
│ │   Rabatt:                    [   0,00] €            │ │
│ │                              ─────────               │ │
│ │   Summe Minderungen:           -20,00 €             │ │
│ │                                                     │ │
│ │ ═══════════════════════════════════════             │ │
│ │ ANSCHAFFUNGSKOSTEN (netto):  1.055,00 €             │ │
│ │ + USt 19%:                     200,45 €             │ │
│ │ ─────────────────────────────────────               │ │
│ │ ANSCHAFFUNGSKOSTEN (brutto): 1.255,45 €             │ │
│ │ ═══════════════════════════════════════             │ │
│ │                                                     │ │
│ │ ℹ️ Gemäß §255 HGB müssen Nebenkosten zu den        │ │
│ │    Anschaffungskosten gerechnet werden.            │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                          │
│ Verkaufspreis (netto):     [1.200,00] €                 │
│ Gewinnmarge:               145,00 € (13,74%)            │
│                                                          │
│ [Abbrechen]                             [Speichern]     │
└──────────────────────────────────────────────────────────┘
```

---

##### **Workflow-Beispiel: Warenimport**

```
SZENARIO: Import von 100 Laptops aus China

1. EINKAUF:
   ┌─────────────────────────────────────────┐
   │ Lieferantenrechnung:                    │
   │ - 100 Laptops × 1.000 € = 100.000 €    │
   │ - Fracht (Container):       2.000 €    │
   │ - Versicherung:               500 €    │
   │ - Zoll (EU-Import):         3.000 €    │
   │ - CO2-Abgabe:                 500 €    │
   │                           ─────────    │
   │ Summe (netto):           106.000 €    │
   │ + USt 19%:                20.140 €    │
   │                           ─────────    │
   │ Summe (brutto):          126.140 €    │
   └─────────────────────────────────────────┘

2. BUCHUNG (§255 HGB - KORREKT):
   ┌─────────────────────────────────────────┐
   │ Ware (100 Laptops):                     │
   │ - Anschaffungskosten: 106.000 € (netto)│
   │ - Pro Laptop: 1.060 € (netto)          │
   │                                         │
   │ Lagerwert: 106.000 €                   │
   │                                         │
   │ Bei Verkauf (1 Laptop):                │
   │ - Wareneinsatz: 1.060 € (nicht 1.000 €)│
   └─────────────────────────────────────────┘

3. VEREINFACHT (toleriert bei Kleinunternehmer):
   ┌─────────────────────────────────────────┐
   │ Ware (100 Laptops): 100.000 € (netto)  │
   │ Fracht: 2.000 € (Betriebsausgabe)      │
   │ Versicherung: 500 € (Betriebsausgabe)  │
   │ Zoll: 3.000 € (Betriebsausgabe)        │
   │ CO2: 500 € (Betriebsausgabe)           │
   │                                         │
   │ Lagerwert: 100.000 €                   │
   │                                         │
   │ Bei Verkauf (1 Laptop):                │
   │ - Wareneinsatz: 1.000 €                │
   │ - Nebenkosten: 60 € (anteilig)         │
   └─────────────────────────────────────────┘
```

---

##### **Best Practices für RechnungsFee**

**Empfehlung:**

1. **Anlagevermögen (Maschinen, Fahrzeuge):**
   - ✅ **IMMER** Nebenkosten zu Anschaffungskosten rechnen
   - ✅ §255 HGB zwingend
   - ✅ Abschreibung über Gesamtkosten

2. **Umlaufvermögen (Waren):**
   - ✅ **Standard**: Nebenkosten zu Anschaffungskosten (§255 HGB)
   - ⚠️ **Vereinfachung**: Separate Verbuchung (bei kleinen Beträgen toleriert)
   - 💡 **RechnungsFee**: Beide Methoden unterstützen, User wählt

3. **Einstellung in RechnungsFee:**
   ```
   ┌──────────────────────────────────────────────┐
   │ ⚙️ Einstellungen > Warenwirtschaft          │
   ├──────────────────────────────────────────────┤
   │                                              │
   │ Anschaffungsnebenkosten behandeln als:      │
   │                                              │
   │ ● Teil der Anschaffungskosten (§255 HGB)    │
   │   Empfohlen, korrekt nach Handelsrecht      │
   │                                              │
   │ ○ Separate Betriebsausgaben                 │
   │   Vereinfachung (nur bei kleinen Beträgen)  │
   └──────────────────────────────────────────────┘
   ```

---

##### **Zusammenfassung: Anschaffungskosten**

**Problem:**
Einkaufspreis ≠ Anschaffungskosten

**Lösung:**
```
Anschaffungskosten = Einkaufspreis + Nebenkosten - Minderungen
```

**Nebenkosten (gehören DAZU):**
- ✅ Fracht, Versicherung, Zölle, CO2, Montage, Verpackung (nicht rückgabefähig)

**Nebenkosten (gehören NICHT dazu):**
- ❌ Lagerkosten (laufend), Verwaltung, Finanzierung

**Steuerlich:**
- **Anlagevermögen**: Nebenkosten PFLICHT hinzurechnen (§255 HGB)
- **Umlaufvermögen**: Sollte hinzugerechnet werden, Vereinfachung toleriert

**RechnungsFee:**
- Datenbank-Erweiterung für detaillierte Nebenkosten
- UI für Erfassung
- Einstellung: §255 HGB vs. Vereinfachung

**Status:** 📋 **Für v2.0 vorgemerkt** (komplexe Warenwirtschaft)

---

#### **📝 Zusammenfassung: Produktstammdaten**

**Entscheidung:**
- ✅ **Hybrid-Lösung** (wie Kundenstamm)
  - Automatisch / Auf Nachfrage (Standard) / Nie
- ✅ **Templates** für verschiedene Produkttypen
  - Dienstleistung (Beratung, Handwerk)
  - Produkt (Handelsware, Eigenproduktion, Digital)
  - Standard (Universal)

**Felder:**

**Für ALLE Typen:**
- Name * (Pflicht)
- USt-Satz * (Pflicht)
- Verkaufspreis * (Netto, Brutto berechnet) (Pflicht)
- Beschreibung
- Kategorie (optional, später)

**Zusätzlich für PRODUKTE:**
- Einkaufspreis * (Netto, Brutto berechnet) (Pflicht)
- Lieferant
- Hersteller
- **EAN-Code** ⭐ (mit Validierung!)
- Artikelcode
- Einheit
- Lagerbestand
- Negativer Lagerbestand (erlaubt/nicht erlaubt)
- Mindestbestand

**Besondere Features:**
- ⭐ **EAN-Code Support** mit Validierung (EAN-13, EAN-8, UPC, ISBN)
- 📊 **Gewinnmarge-Berechnung** (Verkaufspreis - Einkaufspreis)
- ⚠️ **Lagerbestand-Warnung** (bei Unterschreitung Mindestbestand)
- 🧮 **Kalkulations-Modul** (für v2.0 vorgemerkt)
- 💰 **Anschaffungskosten** (§255 HGB) (für v2.0 vorgemerkt)

**Status:** 📋 **Für v2.0 geplant** (NICHT in MVP v1.0)

**Begründung:**
- MVP v1.0: Nur Rechnungen VERWALTEN (nicht erstellen)
- Rechnungsschreiben über LibreOffice/HTML-Vorlagen
- Produktstamm wird erst relevant, wenn internes Rechnungsschreib-Tool kommt

---

### **8.10 Kundenstamm ✅ GEKLÄRT**

**Status:** ✅ **Entscheidung getroffen**

**Entscheidung:** **Hybrid-Lösung (Option C)** mit konfigurierbarem Standard-Verhalten

---

#### **🎯 Implementierung: Hybrid mit Einstellungen**

**User kann in Grundeinstellungen wählen:**

```
┌─────────────────────────────────────────────────┐
│ ⚙️ Einstellungen > Kundenstamm                 │
├─────────────────────────────────────────────────┤
│                                                 │
│ Beim Erstellen von Rechnungen:                 │
│                                                 │
│ ○ Kunden automatisch speichern                 │
│   (Alle neuen Kunden werden ohne Nachfrage     │
│    im Kundenstamm gespeichert)                 │
│                                                 │
│ ● Auf Nachfrage speichern (Standard) ⭐        │
│   (Du wirst gefragt, ob der Kunde gespeichert │
│    werden soll)                                │
│                                                 │
│ ○ Kunden nicht speichern                       │
│   (Kundendaten werden nur in der Rechnung      │
│    erfasst, kein Kundenstamm)                  │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Datenbank-Einstellung:**
```sql
-- In der `user` Tabelle:
ALTER TABLE user ADD COLUMN kundenstamm_modus TEXT DEFAULT 'nachfrage';
-- Werte: 'automatisch', 'nachfrage', 'nie'
```

---

#### **📊 Datenbank-Schema**

```sql
CREATE TABLE kunden (
    id INTEGER PRIMARY KEY,

    -- Stammdaten
    kundennummer TEXT UNIQUE,  -- "K-001" (automatisch generiert)
    typ TEXT,  -- 'privat', 'firma'

    -- Person
    anrede TEXT,  -- 'Herr', 'Frau', 'Divers', NULL
    vorname TEXT,
    nachname TEXT,

    -- Firma (nur wenn typ='firma')
    firmenname TEXT,
    rechtsform TEXT,  -- "GmbH", "AG", "e.K.", etc.
    ansprechpartner TEXT,  -- ⭐ NEU: Kontaktperson bei Firmen

    -- Adresse (Pflichtfelder)
    strasse TEXT NOT NULL,
    hausnummer TEXT,
    plz TEXT NOT NULL,
    ort TEXT NOT NULL,
    land TEXT DEFAULT 'DE' NOT NULL,

    -- Automatisch abgeleitete Kategorisierung
    land_kategorie TEXT GENERATED ALWAYS AS (
        CASE
            WHEN land = 'DE' THEN 'inland'
            WHEN land IN ('AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','GR','HU','IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK','SI','ES','SE') THEN 'eu'
            ELSE 'drittland'
        END
    ) STORED,  -- ⭐ NEU: Automatische Kategorisierung

    -- Kontakt (Optional)
    email TEXT,
    telefon_mobil TEXT,  -- ⭐ NEU: Mobiltelefon (getrennt)
    telefon_festnetz TEXT,  -- ⭐ NEU: Festnetz (getrennt)
    website TEXT,

    -- Persönliche Daten (nur bei typ='privat')
    geburtstag DATE,  -- ⭐ NEU: Für Privatpersonen

    -- Geschäftsbedingungen
    zahlungsziel INTEGER DEFAULT 14,  -- Tage (Standard 14)
    zahlungsziel_individuell BOOLEAN DEFAULT 0,  -- Abweichend vom User-Standard?

    -- Steuerliche Daten
    steuernummer TEXT,  -- ⭐ NEU: Steuernummer (bei Firma validiert)
    steuer_id TEXT,  -- ⭐ NEU: Steueridentifikationsnummer (11-stellig)
    steuer_id_validiert BOOLEAN DEFAULT 0,  -- ⭐ NEU

    -- EU-Handel
    ust_idnr TEXT,  -- z.B. "BE0123456789"
    ust_idnr_validiert BOOLEAN DEFAULT 0,
    ust_idnr_validierung_datum DATE,
    ust_idnr_validierung_ergebnis TEXT,  -- BZSt-API Ergebnis (JSON)

    -- Metadaten
    notizen TEXT,  -- Anmerkungen / Bemerkungen
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    aktualisiert_am TIMESTAMP,

    -- Statistiken (automatisch aktualisiert)
    anzahl_rechnungen INTEGER DEFAULT 0,
    umsatz_gesamt DECIMAL(10,2) DEFAULT 0.00,
    letzte_rechnung_datum DATE
);

-- Index für schnelle Suche
CREATE INDEX idx_kunden_nummer ON kunden(kundennummer);
CREATE INDEX idx_kunden_name ON kunden(nachname, vorname, firmenname);
CREATE INDEX idx_kunden_land_kategorie ON kunden(land_kategorie);
```

---

#### **🖥️ UI: Rechnung erstellen (Modus "nachfrage")**

```
┌──────────────────────────────────────────────────┐
│ 📄 Neue Rechnung erstellen                       │
├──────────────────────────────────────────────────┤
│                                                  │
│ Kunde:                                           │
│ ┌──────────────────────────────────────────────┐ │
│ │ 🔍 Kunde suchen oder neu eingeben...        │ │
│ │ [Bel________________________]               │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ ✓ Belgischer Kunde GmbH (K-042)  ← Aus Stamm   │
│ ✓ Beratung Belgien GmbH (K-015)                │
│ ─────────────────────────────────               │
│ ➕ Neuen Kunden eingeben                        │
│                                                  │
└──────────────────────────────────────────────────┘

[User wählt "Neuen Kunden eingeben"]

┌──────────────────────────────────────────────────┐
│ ➕ Neuer Kunde                                   │
├──────────────────────────────────────────────────┤
│                                                  │
│ Typ:  ● Firma  ○ Privatperson                   │
│                                                  │
│ Firmenname: *                                    │
│ [Neue Firma GmbH_________________]               │
│                                                  │
│ Ansprechpartner:                                 │
│ [Max Mustermann__________________]               │
│                                                  │
│ Straße: *          Hausnr.:                      │
│ [Musterstraße___]  [123__]                       │
│                                                  │
│ PLZ: *      Ort: *                               │
│ [12345___]  [Musterstadt__________]              │
│                                                  │
│ Land: *                      (→ Kategorie: EU)   │
│ [Belgien ▼]                                      │
│                                                  │
│ E-Mail:                                          │
│ [info@neue-firma.be______________]               │
│                                                  │
│ Telefon (Mobil): ⭐ NEU                          │
│ [📱 +49 170 1234567_____]  [📞 Anrufen]         │
│                                                  │
│ Telefon (Festnetz): ⭐ NEU                       │
│ [📞 +49 441 12345___]  [📞 Anrufen]              │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ Steuerliche Daten                          │  │
│ ├────────────────────────────────────────────┤  │
│ │                                            │  │
│ │ Steuernummer (bei Firma): ⭐ NEU          │  │
│ │ [26/123/12345___________]                  │  │
│ │ ⚠️ Empfohlen bei Firmen                   │  │
│ │                                            │  │
│ │ Steuer-ID: ⭐ NEU                          │  │
│ │ [12345678901_____]  [Validieren ✓]        │  │
│ │ ℹ️ 11-stellig (für DE-Kunden)             │  │
│ │                                            │  │
│ │ USt-IdNr. (für EU-Kunden):                 │  │
│ │ [BE0123456789____]  [Validieren ✓]        │  │
│ │ ✅ Gültig (geprüft am 08.12.2025)          │  │
│ │                                            │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ Zahlungsziel:                                    │
│ [14__] Tage  ☑ Abweichend vom Standard (14 T.)  │
│                                                  │
│ Anmerkungen: ⭐ NEU                              │
│ [____________________________________________]   │
│ [____________________________________________]   │
│                                                  │
├──────────────────────────────────────────────────┤
│                                                  │
│ ⚠️ Soll dieser Kunde im Kundenstamm gespeichert │
│    werden?                                       │
│                                                  │
│ ✅ Vorteile:                                     │
│ • Nächste Rechnung: Kunde einfach auswählen     │
│ • USt-IdNr. bereits validiert                   │
│ • Statistiken & Umsatzübersicht möglich         │
│                                                  │
│ [Ja, speichern]  [Nein, nur für diese Rechnung] │
│                                                  │
│ ☑ Immer speichern (Einstellung ändern)          │
│ ☐ Nie mehr fragen (Einstellung ändern)          │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

#### **🖥️ UI: Rechnung erstellen (Modus "automatisch")**

```
[Gleiche Maske wie oben, ABER:]

├──────────────────────────────────────────────────┤
│                                                  │
│ ℹ️ Dieser Kunde wird automatisch im Kundenstamm │
│    gespeichert (Kundennummer: K-089).           │
│                                                  │
│    Einstellung ändern: ⚙️ Einstellungen > Kundenstamm
│                                                  │
└──────────────────────────────────────────────────┘
```

---

#### **🖥️ UI: Rechnung erstellen (Modus "nie")**

```
[Keine Nachfrage, kein Hinweis - Kunde wird NICHT gespeichert]

[Aber: Kundenstamm-Suche trotzdem verfügbar falls manuell angelegt]
```

---

#### **🖥️ UI: Privatperson (mit Geburtstag)** ⭐ NEU

```
┌──────────────────────────────────────────────────┐
│ ➕ Neuer Kunde                                   │
├──────────────────────────────────────────────────┤
│                                                  │
│ Typ:  ○ Firma  ● Privatperson ⭐                │
│                                                  │
│ Anrede:                                          │
│ [Frau ▼]                                         │
│                                                  │
│ Vorname:         Nachname: *                     │
│ [Erika____]      [Musterfrau__________]          │
│                                                  │
│ Geburtstag: ⭐ NEU                               │
│ [01.01.1980__]  📅                               │
│ ℹ️ Optional (z.B. für Glückwünsche)             │
│                                                  │
│ Straße: *          Hausnr.:                      │
│ [Musterstraße___]  [42__]                        │
│                                                  │
│ PLZ: *      Ort: *                               │
│ [26123__]   [Oldenburg____________]              │
│                                                  │
│ Land: *                      (→ Kategorie: Inland)
│ [Deutschland ▼]                                  │
│                                                  │
│ E-Mail:                                          │
│ [erika@beispiel.de_______________]               │
│                                                  │
│ Telefon (Mobil): ⭐                              │
│ [📱 +49 170 9876543_____]  [📞 Anrufen]         │
│                                                  │
│ Telefon (Festnetz): ⭐                           │
│ [📞 0441 987654_____]  [📞 Anrufen]              │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ Steuerliche Daten (optional)               │  │
│ ├────────────────────────────────────────────┤  │
│ │                                            │  │
│ │ Steuer-ID: ⭐                              │  │
│ │ [12345678901_____]                         │  │
│ │ ℹ️ 11-stellig (nur bei Bedarf)            │  │
│ │                                            │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ Zahlungsziel:                                    │
│ [14__] Tage                                      │
│                                                  │
│ Anmerkungen: ⭐                                  │
│ [Stammkundin seit 2020, bevorzugt E-Mail____]   │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

#### **📞 Click-to-Call Funktion** ⭐ NEU

**Linkfeld bei Telefonnummern:**

```python
# ui/kunde_detail.py
def render_telefon_feld(telefon: str, typ: str) -> str:
    """
    Rendert Telefon-Feld mit Click-to-Call Link

    Args:
        telefon: Telefonnummer (z.B. "+49 170 1234567")
        typ: 'mobil' oder 'festnetz'

    Returns:
        HTML mit klickbarem Link für Smartphones
    """
    if not telefon:
        return ""

    icon = "📱" if typ == "mobil" else "📞"

    # Link für Smartphones/Click-to-Call
    # Format: tel:+491701234567 (ohne Leerzeichen)
    tel_link = telefon.replace(' ', '').replace('-', '')

    html = f"""
    <div class="telefon-feld">
        <span class="icon">{icon}</span>
        <a href="tel:{tel_link}" class="telefon-link">
            {telefon}
        </a>
        <button class="btn-call" onclick="call('{tel_link}')">
            📞 Anrufen
        </button>
    </div>
    """

    return html


# JavaScript für Desktop (optional: Integration mit Softphone)
def get_telefon_javascript():
    return """
    <script>
    function call(nummer) {
        // Option 1: Browser-Native (Smartphones)
        window.location.href = 'tel:' + nummer;

        // Option 2: Integration mit Softphone (z.B. 3CX, Asterisk)
        // fetch('/api/softphone/call', {
        //     method: 'POST',
        //     body: JSON.stringify({nummer: nummer})
        // });
    }
    </script>
    """
```

**Verhalten:**
- **Smartphone/Tablet**: Öffnet native Telefon-App
- **Desktop**:
  - Link öffnet Standard-Telefonie-App (Skype, Teams, etc.)
  - Optional: Integration mit Softphone (3CX, Asterisk, sipgate)
- **Button "Anrufen"**: Gleiche Funktion wie Link, aber prominenter

---

#### **📋 Templates für Kundenstamm** ⭐ NEU (für später)

**Konzept:**
Branchenspezifische Vorlagen für Kundenstamm-Felder

**Branchen-Templates:**

```python
# templates/kunden_templates.py
KUNDEN_TEMPLATES = {
    'standard': {
        'name': 'Standard (Universal)',
        'felder': [
            'kundennummer', 'typ', 'firmenname', 'vorname', 'nachname',
            'strasse', 'plz', 'ort', 'land',
            'email', 'telefon_mobil', 'telefon_festnetz',
            'steuernummer', 'steuer_id', 'ust_idnr',
            'zahlungsziel', 'notizen'
        ],
        'pflicht': ['nachname|firmenname', 'strasse', 'plz', 'ort', 'land']
    },

    'handwerk': {
        'name': 'Handwerk (Privatkunden)',
        'beschreibung': 'Für Handwerker mit vielen Privatkunden',
        'felder': [
            'kundennummer', 'typ',
            'anrede', 'vorname', 'nachname',  # Privat im Fokus
            'strasse', 'hausnummer', 'plz', 'ort',  # Hausnummer wichtig!
            'email', 'telefon_mobil', 'telefon_festnetz',  # Beide Nummern
            'geburtstag',  # Für Glückwünsche
            'zahlungsziel',
            'notizen'  # "Wünscht Anruf vorab", "Hat Hund"
        ],
        'pflicht': ['nachname', 'strasse', 'hausnummer', 'plz', 'ort', 'telefon_mobil'],
        'besonderheiten': [
            'Hausnummer Pflichtfeld (für Anfahrt)',
            'Mindestens eine Telefonnummer Pflicht',
            'Geburtstag optional (für Kundenbindung)'
        ]
    },

    'b2b_eu': {
        'name': 'B2B EU-Handel',
        'beschreibung': 'Für Unternehmen mit vielen EU-Geschäftskunden',
        'felder': [
            'kundennummer', 'typ',
            'firmenname', 'rechtsform', 'ansprechpartner',  # Firma im Fokus
            'strasse', 'plz', 'ort', 'land',
            'email', 'telefon_mobil', 'telefon_festnetz',
            'steuernummer', 'ust_idnr',  # USt-IdNr. kritisch!
            'zahlungsziel',
            'notizen'
        ],
        'pflicht': ['firmenname', 'strasse', 'plz', 'ort', 'land', 'ust_idnr'],
        'validierung_scharf': [
            'ust_idnr',  # MUSS validiert werden
            'land'  # MUSS EU-Land sein
        ],
        'besonderheiten': [
            'USt-IdNr. Pflichtfeld (für ig. Lieferung)',
            'Automatische BZSt-Validierung beim Speichern',
            'Warnung bei fehlendem Ansprechpartner'
        ]
    },

    'freiberufler_beratung': {
        'name': 'Freiberufler/Beratung',
        'beschreibung': 'Für Berater, Coaches, Dienstleister',
        'felder': [
            'kundennummer', 'typ',
            'anrede', 'vorname', 'nachname',  # Oft persönliche Beziehung
            'firmenname', 'ansprechpartner',  # Aber auch Firmen
            'strasse', 'plz', 'ort', 'land',
            'email', 'telefon_mobil', 'website',  # Website wichtig
            'zahlungsziel',
            'notizen'  # "Interessiert an Coaching", "Kontakt über LinkedIn"
        ],
        'pflicht': ['nachname|firmenname', 'email'],
        'besonderheiten': [
            'E-Mail Pflichtfeld (Haupt-Kommunikationskanal)',
            'Website optional (für Recherche)',
            'Telefon optional (E-Mail-Kommunikation dominiert)'
        ]
    },

    'einzelhandel': {
        'name': 'Einzelhandel (Laufkundschaft)',
        'beschreibung': 'Für Shops mit vielen Einmalkunden',
        'felder': [
            'kundennummer', 'typ',
            'vorname', 'nachname',
            'email', 'telefon_mobil',
            'geburtstag',  # Für Geburtstags-Rabatte
            'notizen'
        ],
        'pflicht': ['nachname', 'email|telefon_mobil'],  # Minimal!
        'besonderheiten': [
            'Minimales Schema (viele Einmalkunden)',
            'E-Mail ODER Telefon reicht',
            'Adresse optional (Abholung im Shop)',
            'Geburtstag für Marketing'
        ]
    },

    'vermietung': {
        'name': 'Vermietung/Verleih',
        'beschreibung': 'Für Vermieter, Verleiher',
        'felder': [
            'kundennummer', 'typ',
            'anrede', 'vorname', 'nachname',
            'geburtstag',  # Für Altersverifikation
            'strasse', 'hausnummer', 'plz', 'ort',
            'email', 'telefon_mobil', 'telefon_festnetz',
            'steuer_id',  # Für Schufa/Bonität
            'notizen'  # "Kaution hinterlegt", "Vertrag bis 31.12."
        ],
        'pflicht': ['nachname', 'geburtstag', 'strasse', 'plz', 'ort', 'telefon_mobil'],
        'besonderheiten': [
            'Geburtstag Pflicht (Altersverifikation)',
            'Vollständige Adresse Pflicht',
            'Beide Telefonnummern empfohlen (Erreichbarkeit)'
        ]
    }
}


def get_template(branche: str) -> dict:
    """
    Gibt Template für Branche zurück

    Args:
        branche: 'standard', 'handwerk', 'b2b_eu', etc.

    Returns:
        Template-Dict mit Feldern, Pflichtfeldern, Besonderheiten
    """
    return KUNDEN_TEMPLATES.get(branche, KUNDEN_TEMPLATES['standard'])


def apply_template(branche: str):
    """
    Wendet Template an: Passt UI-Formular und Validierung an
    """
    template = get_template(branche)

    # UI nur relevante Felder anzeigen
    # Validierung auf template['pflicht'] anpassen
    # Besonderheiten als Tooltips/Hinweise anzeigen

    pass  # Implementierung später
```

**UI - Template-Auswahl im Setup-Wizard:**

```
┌──────────────────────────────────────────────────┐
│ Setup-Wizard - Schritt 1: Branche               │
├──────────────────────────────────────────────────┤
│                                                  │
│ Welche Branche passt am besten zu dir?          │
│                                                  │
│ ○ Standard (Universal)                           │
│   Für alle Branchen geeignet                     │
│                                                  │
│ ○ Handwerk (Privatkunden)                        │
│   Viele Privatkunden, Anfahrt wichtig            │
│                                                  │
│ ○ B2B EU-Handel                                  │
│   Geschäftskunden, USt-IdNr. wichtig             │
│                                                  │
│ ○ Freiberufler/Beratung                          │
│   Dienstleister, E-Mail-Kommunikation            │
│                                                  │
│ ○ Einzelhandel (Laufkundschaft)                  │
│   Viele Einmalkunden, minimale Daten             │
│                                                  │
│ ○ Vermietung/Verleih                             │
│   Verträge, Altersverifikation wichtig           │
│                                                  │
│ ℹ️ Du kannst die Felder später anpassen!        │
│                                                  │
│ [Zurück]                         [Weiter]        │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Vorteile:**
- ✅ **Fokussiert**: Nur relevante Felder für Branche
- ✅ **Geführt**: Pflichtfelder an Branche angepasst
- ✅ **Lernkurve**: Weniger Verwirrung (weniger Felder)
- ✅ **Flexibel**: Kann später auf "Standard" umstellen

**Status:** 🔜 **Für v2.0 geplant** (v1.0 nutzt "Standard"-Template)

---

#### **💻 Code-Implementierung**

```python
# models.py
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

@dataclass
class Kunde:
    id: Optional[int] = None

    # Stammdaten
    kundennummer: Optional[str] = None  # "K-001" (auto)
    typ: str = 'privat'  # 'privat' | 'firma'

    # Person
    anrede: Optional[str] = None
    vorname: Optional[str] = None
    nachname: Optional[str] = None

    # Firma
    firmenname: Optional[str] = None
    rechtsform: Optional[str] = None
    ansprechpartner: Optional[str] = None  # ⭐ NEU

    # Adresse (Pflicht)
    strasse: str = ''
    hausnummer: Optional[str] = None
    plz: str = ''
    ort: str = ''
    land: str = 'DE'

    # Kontakt
    email: Optional[str] = None
    telefon_mobil: Optional[str] = None  # ⭐ NEU
    telefon_festnetz: Optional[str] = None  # ⭐ NEU
    website: Optional[str] = None

    # Persönliche Daten
    geburtstag: Optional[date] = None  # ⭐ NEU (nur bei typ='privat')

    # Geschäftsbedingungen
    zahlungsziel: int = 14  # Tage
    zahlungsziel_individuell: bool = False

    # Steuerliche Daten
    steuernummer: Optional[str] = None  # ⭐ NEU (bei Firma)
    steuer_id: Optional[str] = None  # ⭐ NEU (11-stellig)
    steuer_id_validiert: bool = False  # ⭐ NEU

    # EU-Handel
    ust_idnr: Optional[str] = None
    ust_idnr_validiert: bool = False
    ust_idnr_validierung_datum: Optional[date] = None
    ust_idnr_validierung_ergebnis: Optional[str] = None

    # Metadaten
    notizen: Optional[str] = None
    erstellt_am: Optional[datetime] = None
    aktualisiert_am: Optional[datetime] = None

    # Statistiken
    anzahl_rechnungen: int = 0
    umsatz_gesamt: Decimal = Decimal('0.00')
    letzte_rechnung_datum: Optional[date] = None

    @property
    def land_kategorie(self) -> str:
        """
        Automatische Kategorisierung: inland / eu / drittland
        """
        if self.land == 'DE':
            return 'inland'
        elif self.land in EU_LAENDER:  # Liste aus Sektion 8.6
            return 'eu'
        else:
            return 'drittland'

    @property
    def display_name(self) -> str:
        """
        Anzeigename für UI
        """
        if self.typ == 'firma' and self.firmenname:
            return self.firmenname
        elif self.vorname and self.nachname:
            return f"{self.vorname} {self.nachname}"
        elif self.nachname:
            return self.nachname
        else:
            return "Unbenannter Kunde"

    def validate(self) -> list[str]:
        """
        Validiert Pflichtfelder
        """
        errors = []

        if self.typ == 'privat':
            if not self.nachname:
                errors.append("Nachname ist Pflichtfeld")
        elif self.typ == 'firma':
            if not self.firmenname:
                errors.append("Firmenname ist Pflichtfeld")

        if not self.strasse:
            errors.append("Straße ist Pflichtfeld")
        if not self.plz:
            errors.append("PLZ ist Pflichtfeld")
        if not self.ort:
            errors.append("Ort ist Pflichtfeld")
        if not self.land:
            errors.append("Land ist Pflichtfeld")

        # Steuerliche Validierungen ⭐ NEU
        if self.typ == 'firma' and self.firmenname:
            # Bei Firma: Steuernummer empfohlen
            if not self.steuernummer:
                errors.append("Warnung: Steuernummer bei Firma empfohlen")

        # Steuer-ID Validierung (wenn gefüllt)
        if self.steuer_id:
            if self.land == 'DE':
                # Deutsche Steuer-ID: 11-stellig
                if not self._validate_steuer_id_de(self.steuer_id):
                    errors.append("Steuer-ID ungültig (muss 11-stellig sein)")
            else:
                # Andere Länder: Steuer-ID sollte validiert werden
                if not self.steuer_id_validiert:
                    errors.append("Warnung: Steuer-ID sollte validiert werden")

        # USt-IdNr. bei EU-Kunden empfohlen
        if self.land_kategorie == 'eu' and not self.ust_idnr:
            errors.append("Warnung: USt-IdNr. bei EU-Kunden empfohlen (für ig. Lieferung)")

        return errors

    def _validate_steuer_id_de(self, steuer_id: str) -> bool:
        """
        Validiert deutsche Steuer-ID (11-stellig)

        Format: XXXXXXXXXXX (11 Ziffern)
        - Ziffer 1-10: Beliebig (aber Prüfziffer-Logik)
        - Ziffer 11: Prüfziffer
        """
        import re

        # Leerzeichen entfernen
        steuer_id_clean = steuer_id.replace(' ', '')

        # Muss 11 Ziffern sein
        if not re.match(r'^\d{11}$', steuer_id_clean):
            return False

        # Erweiterte Validierung (Prüfziffer) hier möglich
        # Für MVP: Nur Längen-Check
        return True


# kunde_service.py
class KundenService:
    def __init__(self, db, user_settings):
        self.db = db
        self.user_settings = user_settings

    def sollte_kunde_speichern(self, kunde: Kunde, user_entscheidung: Optional[bool] = None) -> bool:
        """
        Bestimmt ob Kunde gespeichert werden soll basierend auf Einstellung

        Args:
            kunde: Kundendaten
            user_entscheidung: Explizite User-Entscheidung (überschreibt Einstellung)

        Returns:
            True wenn Kunde gespeichert werden soll
        """
        if user_entscheidung is not None:
            return user_entscheidung

        modus = self.user_settings.kundenstamm_modus

        if modus == 'automatisch':
            return True
        elif modus == 'nie':
            return False
        else:  # 'nachfrage'
            # UI muss Dialog anzeigen
            return None  # Signalisiert: UI-Dialog erforderlich

    def generiere_kundennummer(self) -> str:
        """
        Generiert nächste Kundennummer: K-001, K-002, ...
        """
        cursor = self.db.execute(
            "SELECT MAX(CAST(SUBSTR(kundennummer, 3) AS INTEGER)) FROM kunden WHERE kundennummer LIKE 'K-%'"
        )
        max_nr = cursor.fetchone()[0] or 0
        return f"K-{max_nr + 1:03d}"

    def speichere_kunde(self, kunde: Kunde) -> Kunde:
        """
        Speichert Kunde in Datenbank
        """
        # Validierung
        errors = kunde.validate()
        if errors:
            raise ValueError(f"Validierungsfehler: {', '.join(errors)}")

        # Kundennummer generieren
        if not kunde.kundennummer:
            kunde.kundennummer = self.generiere_kundennummer()

        # Standard-Zahlungsziel vom User übernehmen
        if kunde.zahlungsziel == 14 and not kunde.zahlungsziel_individuell:
            kunde.zahlungsziel = self.user_settings.zahlungsziel_standard or 14

        # USt-IdNr. validieren (falls vorhanden und EU)
        if kunde.ust_idnr and kunde.land_kategorie == 'eu':
            if not kunde.ust_idnr_validiert:
                self.validiere_ust_idnr(kunde)

        # Speichern
        cursor = self.db.execute("""
            INSERT INTO kunden (
                kundennummer, typ,
                anrede, vorname, nachname,
                firmenname, rechtsform, ansprechpartner,
                strasse, hausnummer, plz, ort, land,
                email, telefon, website,
                zahlungsziel, zahlungsziel_individuell,
                ust_idnr, ust_idnr_validiert, ust_idnr_validierung_datum, ust_idnr_validierung_ergebnis,
                notizen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            kunde.kundennummer, kunde.typ,
            kunde.anrede, kunde.vorname, kunde.nachname,
            kunde.firmenname, kunde.rechtsform, kunde.ansprechpartner,
            kunde.strasse, kunde.hausnummer, kunde.plz, kunde.ort, kunde.land,
            kunde.email, kunde.telefon, kunde.website,
            kunde.zahlungsziel, kunde.zahlungsziel_individuell,
            kunde.ust_idnr, kunde.ust_idnr_validiert, kunde.ust_idnr_validierung_datum, kunde.ust_idnr_validierung_ergebnis,
            kunde.notizen
        ))

        kunde.id = cursor.lastrowid
        self.db.commit()

        return kunde

    def suche_kunden(self, suchbegriff: str, limit: int = 10) -> list[Kunde]:
        """
        Sucht Kunden für Autocomplete
        """
        cursor = self.db.execute("""
            SELECT * FROM kunden
            WHERE
                firmenname LIKE ? OR
                nachname LIKE ? OR
                vorname LIKE ? OR
                kundennummer LIKE ?
            ORDER BY
                anzahl_rechnungen DESC,  -- Häufigste zuerst
                letzte_rechnung_datum DESC,
                kundennummer ASC
            LIMIT ?
        """, (f"%{suchbegriff}%",) * 4 + (limit,))

        return [self._row_to_kunde(row) for row in cursor.fetchall()]

    def validiere_ust_idnr(self, kunde: Kunde) -> bool:
        """
        Validiert USt-IdNr. über BZSt-API (siehe Sektion 5.8)
        """
        from ust_idnr_service import UStIdNrService

        service = UStIdNrService(
            eigene_ust_idnr=self.user_settings.ust_idnr,
            firmenname=self.user_settings.firmenname or f"{self.user_settings.vorname} {self.user_settings.nachname}",
            ort=self.user_settings.ort,
            plz=self.user_settings.plz,
            strasse=self.user_settings.strasse
        )

        result = service.qualifizierte_abfrage(
            partner_ust_idnr=kunde.ust_idnr,
            partner_firmenname=kunde.firmenname or f"{kunde.vorname} {kunde.nachname}",
            partner_ort=kunde.ort,
            partner_plz=kunde.plz,
            partner_strasse=kunde.strasse
        )

        kunde.ust_idnr_validiert = result['gueltig']
        kunde.ust_idnr_validierung_datum = date.today()
        kunde.ust_idnr_validierung_ergebnis = json.dumps(result)

        return result['gueltig']
```

---

#### **📝 Workflow-Beispiele**

**Beispiel 1: User mit Modus "nachfrage" (Standard)**

```
1. User klickt "Neue Rechnung"
2. UI zeigt Kundensuche + "Neuen Kunden eingeben"
3. User gibt neuen Kunden ein (z.B. "Belgischer Kunde GmbH")
4. User klickt "Weiter"
5. Dialog erscheint: "Soll dieser Kunde im Kundenstamm gespeichert werden?"
6. User wählt "Ja, speichern"
7. Kunde wird gespeichert (K-089)
8. Rechnung wird erstellt mit kunde_id=89
```

**Beispiel 2: User mit Modus "automatisch"**

```
1. User klickt "Neue Rechnung"
2. UI zeigt Kundensuche + "Neuen Kunden eingeben"
3. User gibt neuen Kunden ein
4. User klickt "Weiter"
5. Hinweis erscheint kurz: "Kunde wurde als K-090 gespeichert"
6. Rechnung wird erstellt mit kunde_id=90
```

**Beispiel 3: User mit Modus "nie"**

```
1. User klickt "Neue Rechnung"
2. UI zeigt Kundensuche (falls manuell angelegte Kunden existieren) + "Neuen Kunden eingeben"
3. User gibt neuen Kunden ein
4. User klickt "Weiter"
5. Kunde wird NICHT gespeichert (kunde_id=NULL in Rechnung)
6. Kundendaten werden in `rechnungen.kunde_json` gespeichert (Fallback)
```

---

#### **✅ Vorteile der Hybrid-Lösung**

1. **Maximale Flexibilität**: User entscheidet selbst (einmalig in Einstellungen)
2. **Kein Overhead bei Einmalkunden**: Modus "nie" spart DSGVO-Aufwand
3. **Komfort bei Stammkunden**: Modus "automatisch" spart Klicks
4. **Lernkurve sanft**: Standard "nachfrage" erklärt Feature beim ersten Mal
5. **Jederzeit änderbar**: User kann Modus später umschalten
6. **Keine Datenverluste**: Auch bei Modus "nie" können Kunden manuell angelegt werden

---

#### **🔍 Zusätzliche Features**

**Kundennummer automatisch generiert:**
- K-001, K-002, K-003, ...
- Fortlaufend, keine Lücken

**Zahlungsziel:**
- Standard: 14 Tage (vom User-Setting übernommen)
- Pro Kunde individuell änderbar (Checkbox "Abweichend vom Standard")

**Ansprechpartner:**
- Für Firmen: Kontaktperson erfassen
- Bei Rechnung wird Ansprechpartner angezeigt: "z.Hd. Max Mustermann"

**Inland/EU/Drittland automatisch:**
- Wird aus `land` abgeleitet (Generated Column in SQLite)
- Keine manuelle Eingabe nötig
- Wichtig für USt-Behandlung in UStVA/ZM

---

**Status:** ✅ **Kategorie 8.10 vollständig geklärt** - Hybrid-Lösung mit konfigurierbarem Modus (automatisch / auf Nachfrage / nie). Alle Felder spezifiziert: Kundennummer (automatisch), Ansprechpartner, Zahlungsziel, Inland/EU/Drittland-Automatik, USt-IdNr.-Validierung (BZSt-API).

---

### **8.10.1 Rechtliche Dokumente (B2B vs. B2C)** ⚖️ WICHTIG

**Problem:** Unterschiedliche Pflichten bei Geschäftskunden (B2B) vs. Privatkunden (B2C)

---

#### **⚠️ RECHTLICHER HINWEIS - BITTE LESEN!**

```
┌──────────────────────────────────────────────────┐
│ ⚠️ WICHTIG: Keine Rechtsberatung!               │
├──────────────────────────────────────────────────┤
│                                                  │
│ Diese Dokumentation stellt KEINE Rechtsberatung │
│ dar!                                             │
│                                                  │
│ Widerrufsfristen können sich ändern!            │
│                                                  │
│ ✅ BITTE VOR EINSATZ PRÜFEN:                    │
│                                                  │
│ 1. Aktuelle Widerrufsfrist in Deutschland:      │
│    → §355 BGB, §312g BGB                        │
│    → Stand dieser Doku: 14 Tage (Januar 2025)  │
│                                                  │
│ 2. Quellen zur Prüfung:                          │
│    → https://www.gesetze-im-internet.de/bgb/    │
│    → Verbraucherzentrale                        │
│    → Rechtsanwalt konsultieren!                 │
│                                                  │
│ 3. Bei Änderung:                                 │
│    → Konstante WIDERRUFSFRIST_TAGE anpassen     │
│    → Siehe config.py                            │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

#### **📋 B2B vs. B2C Anforderungen**

```
┌──────────────────────────────────────────────────┐
│ Rechtliche Dokumente - Übersicht                │
├──────────────────────────────────────────────────┤
│                                                  │
│ B2B (Geschäftskunde):                            │
│ ✅ AGBs MÜSSEN aktiv mitgegeben werden          │
│    (§305 Abs. 2 BGB)                             │
│ ❌ Widerrufsbelehrung NICHT erforderlich        │
│ ℹ️ Datenschutzerklärung auf Anfrage             │
│                                                  │
│ B2C (Privatkunde):                               │
│ ✅ AGBs zur Verfügung stellen                   │
│ ✅ Widerrufsbelehrung bei Fernabsatz (PFLICHT!) │
│    (§312g BGB, BGB-InfoV)                        │
│ ✅ Informationspflichten nach BGB-InfoV         │
│ ✅ Datenschutzerklärung (DSGVO)                 │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Wichtig:**
- **B2B:** AGBs müssen **aktiv einbezogen** werden (z.B. als PDF-Anhang)
- **B2C:** AGBs + Widerrufsbelehrung + Informationspflichten
- **Erkennung:** Über `kunde.typ` ('firma' = B2B, 'privat' = B2C)

---

#### **📄 Welche Dokumente?**

**1. AGBs (Allgemeine Geschäftsbedingungen)**

**B2B:**
- ✅ **PFLICHT:** Aktiv mitgeben (§305 Abs. 2 BGB)
- **Wie:** PDF-Anhang an Rechnung ODER Link in Rechnung
- **Wann:** Bei jeder Rechnung (sofern nicht bereits übermittelt)

**B2C:**
- ✅ **PFLICHT:** Zur Verfügung stellen
- **Wie:** Link in Rechnung oder auf Website
- **Wann:** Vor Vertragsschluss

---

**2. Widerrufsbelehrung**

**B2B:**
- ❌ **NICHT erforderlich** (nur für Verbraucher)

**B2C:**
- ✅ **PFLICHT bei Fernabsatzverträgen** (§312g BGB)
- **Wie:** PDF-Anhang oder in Rechnung integriert
- **Wann:** Bei jeder Rechnung (Fernabsatz)
- **Frist:** **14 Tage** ab Vertragsschluss (§355 BGB) ⚠️ **BITTE PRÜFEN!**
  - Stand: Januar 2025
  - Konfigurierbar in `config.py` → `WIDERRUFSFRIST_TAGE`
  - **Bei Gesetzesänderung:** Konstante anpassen!

**Ausnahmen (keine Widerrufsbelehrung erforderlich):**
- Dienstleistungen vollständig erbracht
- Individuell angefertigte Produkte
- Verderbliche Waren

---

**3. Informationspflichten (BGB-InfoV)**

**B2C:**
- ✅ Identität des Unternehmers
- ✅ Wesentliche Eigenschaften der Ware/Dienstleistung
- ✅ Gesamtpreis inkl. USt
- ✅ Lieferkosten
- ✅ Zahlungsbedingungen
- ✅ Lieferbedingungen

**B2B:**
- ℹ️ Teilweise erforderlich (je nach Vertrag)

---

#### **💻 Implementierung in RechnungsFee**

**Datenbank-Schema:**

```sql
-- Rechtliche Dokumente
CREATE TABLE rechtliche_dokumente (
    id INTEGER PRIMARY KEY,

    -- Art des Dokuments
    typ TEXT NOT NULL,  -- 'agb', 'widerruf', 'datenschutz', 'impressum'

    -- Für wen gilt es?
    gueltig_fuer TEXT NOT NULL,  -- 'b2b', 'b2c', 'beide'

    -- Dokument
    titel TEXT NOT NULL,  -- "AGBs Stand 2024"
    datei_pfad TEXT,  -- "dokumente/agb_2024.pdf"
    datei_hash TEXT,  -- SHA256 für Versionierung

    -- Version
    version TEXT,  -- "1.0", "2.0"
    gueltig_ab DATE NOT NULL,
    gueltig_bis DATE,  -- NULL = aktuell gültig

    -- Metadaten
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    erstellt_von TEXT,

    -- Aktiv?
    aktiv BOOLEAN DEFAULT 1
);

-- Zuordnung: Welche Dokumente wurden mit Rechnung versendet?
CREATE TABLE rechnung_dokumente (
    id INTEGER PRIMARY KEY,

    rechnung_id INTEGER NOT NULL,
    dokument_id INTEGER NOT NULL,

    -- Nachweis
    versendet_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    versand_methode TEXT,  -- 'pdf_anhang', 'link', 'integriert'

    FOREIGN KEY (rechnung_id) REFERENCES rechnungen(id),
    FOREIGN KEY (dokument_id) REFERENCES rechtliche_dokumente(id)
);
```

---

#### **🔄 Workflow: Rechnung erstellen**

```python
def erstelle_rechnung(kunde_id: int, positionen: list) -> Rechnung:
    """
    Erstellt Rechnung mit automatischer Anhängung rechtlicher Dokumente
    """
    kunde = db.get_kunde(kunde_id)
    rechnung = create_rechnung(kunde, positionen)

    # Rechtliche Dokumente bestimmen
    dokumente = []

    if kunde.typ == 'firma':  # B2B
        # AGBs PFLICHT
        agb = get_aktives_dokument('agb', 'b2b')
        if agb:
            dokumente.append(agb)
        else:
            raise ValueError("AGBs für B2B fehlen! Bitte in Einstellungen hochladen.")

    elif kunde.typ == 'privat':  # B2C
        # AGBs + Widerrufsbelehrung
        agb = get_aktives_dokument('agb', 'b2c')
        widerruf = get_aktives_dokument('widerruf', 'b2c')

        if agb:
            dokumente.append(agb)
        if widerruf and ist_fernabsatz(rechnung):
            dokumente.append(widerruf)

    # Dokumente anhängen
    for dok in dokumente:
        haenge_dokument_an(rechnung, dok)

    return rechnung


def haenge_dokument_an(rechnung: Rechnung, dokument: RechtlichesDokument):
    """
    Hängt rechtliches Dokument an Rechnung an
    """
    # Methode 1: PDF-Anhang (Standard)
    if dokument.datei_pfad:
        rechnung.anhaenge.append(dokument.datei_pfad)
        versand_methode = 'pdf_anhang'

    # Methode 2: Link in Rechnung (alternativ)
    else:
        link = f"https://example.com/rechtliches/{dokument.typ}.pdf"
        rechnung.fusszeile += f"\n{dokument.titel}: {link}"
        versand_methode = 'link'

    # Nachweis protokollieren
    db.execute("""
        INSERT INTO rechnung_dokumente (rechnung_id, dokument_id, versand_methode)
        VALUES (?, ?, ?)
    """, (rechnung.id, dokument.id, versand_methode))

    db.commit()


def ist_fernabsatz(rechnung: Rechnung) -> bool:
    """
    Prüft ob Fernabsatzvertrag (Widerrufsbelehrung erforderlich)

    Fernabsatz = Vertrag ohne gleichzeitige Anwesenheit
    (z.B. Online-Shop, E-Mail, Telefon)
    """
    # Vereinfachung: Immer True bei B2C
    # Erweiterte Logik: Prüfung Vertriebsweg
    return True
```

---

#### **🖥️ UI: Rechtliche Dokumente verwalten**

```
┌──────────────────────────────────────────────────┐
│ ⚙️ Einstellungen > Rechtliche Dokumente         │
├──────────────────────────────────────────────────┤
│                                                  │
│ [ + Neues Dokument hochladen ]                   │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ 📄 AGBs (B2B) - Stand 2024               │  │
│ ├────────────────────────────────────────────┤  │
│ │ Typ: AGBs                                  │  │
│ │ Gültig für: B2B (Geschäftskunden)          │  │
│ │ Version: 1.0                               │  │
│ │ Gültig ab: 01.01.2024                      │  │
│ │ Datei: agb_b2b_2024.pdf (142 KB)           │  │
│ │                                            │  │
│ │ ✅ Aktiv (wird automatisch angehängt)     │  │
│ │                                            │  │
│ │ [Bearbeiten] [Deaktivieren] [Löschen]     │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ 📄 AGBs (B2C) - Stand 2024               │  │
│ ├────────────────────────────────────────────┤  │
│ │ Typ: AGBs                                  │  │
│ │ Gültig für: B2C (Privatkunden)             │  │
│ │ Version: 1.0                               │  │
│ │ Gültig ab: 01.01.2024                      │  │
│ │ Datei: agb_b2c_2024.pdf (156 KB)           │  │
│ │                                            │  │
│ │ ✅ Aktiv                                   │  │
│ │                                            │  │
│ │ [Bearbeiten] [Deaktivieren] [Löschen]     │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ ┌────────────────────────────────────────────┐  │
│ │ 📄 Widerrufsbelehrung (B2C)              │  │
│ ├────────────────────────────────────────────┤  │
│ │ Typ: Widerrufsbelehrung                    │  │
│ │ Gültig für: B2C (Privatkunden)             │  │
│ │ Version: 1.0                               │  │
│ │ Gültig ab: 01.01.2024                      │  │
│ │ Datei: widerruf_2024.pdf (89 KB)           │  │
│ │                                            │  │
│ │ ✅ Aktiv (bei Fernabsatz)                 │  │
│ │                                            │  │
│ │ [Bearbeiten] [Deaktivieren] [Löschen]     │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ ⚠️ Hinweis:                                     │
│ Bei B2B-Kunden werden AGBs automatisch als      │
│ PDF-Anhang mitgesendet (§305 Abs. 2 BGB).       │
│                                                  │
│ Bei B2C-Kunden werden AGBs + Widerrufsbelehrung │
│ mitgesendet (§312g BGB, BGB-InfoV).              │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

#### **📧 E-Mail-Versand mit Anhängen**

```python
def versende_rechnung_email(rechnung_id: int):
    """
    Versendet Rechnung per E-Mail mit rechtlichen Dokumenten
    """
    rechnung = db.get_rechnung(rechnung_id)
    kunde = rechnung.kunde

    # PDF generieren
    rechnung_pdf = generate_rechnung_pdf(rechnung)

    # Anhänge sammeln
    anhaenge = [rechnung_pdf]

    # Rechtliche Dokumente hinzufügen
    dokumente = db.execute("""
        SELECT d.* FROM rechnung_dokumente rd
        JOIN rechtliche_dokumente d ON rd.dokument_id = d.id
        WHERE rd.rechnung_id = ?
        AND rd.versand_methode = 'pdf_anhang'
    """, (rechnung_id,)).fetchall()

    for dok in dokumente:
        anhaenge.append(dok.datei_pfad)

    # E-Mail zusammenstellen
    betreff = f"Rechnung {rechnung.rechnungsnummer}"

    if kunde.typ == 'firma':  # B2B
        text = f"""
        Sehr geehrte Damen und Herren,

        anbei erhalten Sie die Rechnung {rechnung.rechnungsnummer}.

        Im Anhang finden Sie:
        - Rechnung {rechnung.rechnungsnummer}.pdf
        - AGBs.pdf

        Mit freundlichen Grüßen
        """
    else:  # B2C
        text = f"""
        Sehr geehrte/r {kunde.anrede} {kunde.nachname},

        anbei erhalten Sie die Rechnung {rechnung.rechnungsnummer}.

        Im Anhang finden Sie:
        - Rechnung {rechnung.rechnungsnummer}.pdf
        - AGBs.pdf
        - Widerrufsbelehrung.pdf

        Sie haben ein Widerrufsrecht von 14 Tagen ab Erhalt dieser E-Mail.

        Mit freundlichen Grüßen
        """

    # E-Mail versenden
    send_email(
        to=kunde.email,
        betreff=betreff,
        text=text,
        anhaenge=anhaenge
    )
```

---

#### **⚠️ Wichtige Hinweise**

**1. Versionierung:**
- Bei Änderung der AGBs: Neue Version anlegen
- Alte Version bleibt aktiv für bestehende Verträge
- Neue Rechnungen nutzen neue Version

**2. Nachweis:**
- Alle versendeten Dokumente werden in `rechnung_dokumente` protokolliert
- Wichtig bei Streitigkeiten: Nachweis dass AGBs übermittelt wurden

**3. Sprache:**
- Bei ausländischen Kunden: AGBs in Landessprache?
- Mindestens: Deutsche Version

**4. Individueller Vertrag:**
- Wenn individueller Vertrag existiert: AGBs optional
- Aber: Empfohlen für Standard-Klauseln

---

#### **📋 Checkliste: Setup**

```
┌──────────────────────────────────────────────────┐
│ ✅ Rechtliche Dokumente - Checkliste            │
├──────────────────────────────────────────────────┤
│                                                  │
│ ☑ AGBs für B2B erstellt und hochgeladen         │
│   → Pflicht nach §305 Abs. 2 BGB                │
│                                                  │
│ ☑ AGBs für B2C erstellt und hochgeladen         │
│   → Empfohlen                                    │
│                                                  │
│ ☑ Widerrufsbelehrung für B2C erstellt           │
│   → Pflicht bei Fernabsatz (§312g BGB)          │
│                                                  │
│ ☑ Datenschutzerklärung erstellt                 │
│   → DSGVO-Pflicht                                │
│                                                  │
│ ☑ Automatische Anhängung aktiviert              │
│   → In Einstellungen konfiguriert               │
│                                                  │
│ ☑ Test-Rechnung erstellt (B2B)                  │
│   → Prüfen: AGBs angehängt?                     │
│                                                  │
│ ☑ Test-Rechnung erstellt (B2C)                  │
│   → Prüfen: AGBs + Widerruf angehängt?          │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

#### **🎓 Beispiel: Musterdokumente**

**AGBs (B2B) - Kurzversion:**

```
ALLGEMEINE GESCHÄFTSBEDINGUNGEN

1. Geltungsbereich
Diese AGBs gelten für alle Geschäftsbeziehungen mit Unternehmern.

2. Vertragsschluss
Der Vertrag kommt mit Annahme des Angebots zustande.

3. Zahlungsbedingungen
Zahlungsziel: 14 Tage netto.

4. Gewährleistung
Es gelten die gesetzlichen Gewährleistungsrechte.

5. Haftung
[...]
```

**Widerrufsbelehrung (B2C) - Muster:**

```
WIDERRUFSBELEHRUNG

Widerrufsrecht:
Sie haben das Recht, binnen vierzehn Tagen ohne Angabe von Gründen
diesen Vertrag zu widerrufen.

Die Widerrufsfrist beträgt vierzehn Tage ab dem Tag [...]

Um Ihr Widerrufsrecht auszuüben, müssen Sie uns mittels einer
eindeutigen Erklärung (z.B. per Post oder E-Mail) über Ihren
Entschluss informieren.

Kontakt für Widerruf:
[Name]
[Adresse]
[E-Mail]
```

---

**Status:** ✅ **B2B vs. B2C Anforderungen dokumentiert**

**Wichtigste Punkte:**
1. ✅ **B2B:** AGBs PFLICHT als Anhang (§305 Abs. 2 BGB)
2. ✅ **B2C:** AGBs + Widerrufsbelehrung bei Fernabsatz (§312g BGB)
3. ✅ **Automatische Erkennung** über `kunde.typ`
4. ✅ **Nachweis** in `rechnung_dokumente` Tabelle
5. ✅ **Versionierung** für rechtssichere Nachweisbarkeit

---

