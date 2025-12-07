# 📋 Umfrage: Kundenstamm in Version 1.0 - Ja oder Nein?

Hallo Community! 👋

Ich brauche euer Feedback für eine wichtige **Architektur-Entscheidung** in RechnungsPilot:

**Soll Version 1.0 bereits einen Kundenstamm haben?**

---

## 🤔 Hintergrund

**So funktioniert's:**
- RechnungsPilot öffnet LibreOffice/HTML-Vorlagen
- Du erstellst Rechnungen (mit Kundendaten)
- RechnungsPilot importiert die Rechnung (PDF/XRechnung)
- Bei Export (UStVA, ZM, DATEV) werden Daten validiert

**Die Frage:**
- Sollen Kundendaten **separat gespeichert** werden (Kundenstamm)?
- Oder sollen sie nur **direkt in der Rechnung** erfasst werden?

---

## ✅ **Option A: MIT Kundenstamm**

### **Workflow:**

```
1. Kunde EINMALIG anlegen:
   ├─ Name: Belgischer Kunde GmbH
   ├─ Adresse: Rue de Example 123, 1000 Brüssel
   ├─ Land: Belgien
   └─ USt-IdNr: BE0123456789
       [ Validieren ] ✅ Gültig!

2. Rechnung erstellen:
   ├─ Kunde auswählen: [Belgischer Kunde ▼]
   └─ Daten automatisch übernommen ✅

3. Zweite Rechnung:
   ├─ Kunde auswählen: [Belgischer Kunde ▼]
   └─ Fertig! (keine erneute Eingabe)
```

### **Vorteile:**

✅ **Weniger Tipparbeit** - Kunde 1× anlegen, danach nur auswählen
✅ **Datenqualität höher** - Keine Tippfehler bei wiederholter Eingabe
✅ **Autocomplete** - Kunde schnell finden (tippe "Bel..." → Belgischer Kunde)
✅ **Validierung VORHER** - USt-IdNr. wird sofort beim Anlegen geprüft (nicht erst beim Export)
✅ **Statistiken möglich** - Umsatz pro Kunde, offene Posten, etc.
✅ **EU-Handel einfacher** - USt-IdNr. einmal validiert, immer korrekt

### **Nachteile:**

❌ **Länger bis Release** - ca. +2-3 Wochen Entwicklungszeit
❌ **Mehr Lernkurve** - User muss erst Kunde anlegen, dann Rechnung erstellen
❌ **Overhead bei Einmalkunden** - Privatkunde für eine Rechnung → unnötig im Stamm
❌ **DSGVO-Komplex** - Kundendaten gespeichert → Löschpflicht, Auskunftspflicht

---

## ✅ **Option B: OHNE Kundenstamm**

### **Workflow:**

```
1. Rechnung erstellen:
   ├─ Template öffnet sich
   ├─ Kundendaten MANUELL eingeben:
   │  ├─ Name: Belgischer Kunde GmbH
   │  ├─ Adresse: Rue de Example 123, 1000 Brüssel
   │  ├─ Land: Belgien
   │  └─ USt-IdNr: BE0123456789 (keine Validierung!)
   ├─ Artikelpositionen
   └─ Speichern

2. Zweite Rechnung an denselben Kunden:
   └─ Alles erneut eingeben ❌
```

### **Vorteile:**

✅ **Schneller Release** - 2-3 Wochen gespart → früher nutzbar
✅ **Einfacherer Scope** - Konzentration auf Kernfunktionen (Rechnung, UStVA, Export)
✅ **Flexibler** - Kein Zwang, erst Kunde anzulegen
✅ **DSGVO einfacher** - Kundendaten nur in Rechnungen, nicht separat gespeichert

### **Nachteile:**

❌ **Wiederholte Eingabe** - 10 Rechnungen → 10× dieselben Daten eingeben 😤
❌ **Tippfehler-Gefahr** - "Belgischer Kunde" vs. "Belgischer Kunbe" → Inkonsistenzen
❌ **Validierung erst beim Export** - Fehler in USt-IdNr. erst nach Wochen entdeckt
❌ **Keine Statistiken** - "Welcher Kunde bringt meisten Umsatz?" → nicht beantwortbar
❌ **Migration später nötig** - Wenn Version 2.0 Kundenstamm einführt → komplexe Datenmigration

---

## 🎯 **Option C: Hybrid (Kompromiss)**

### **Workflow:**

```
Rechnung erstellen:
┌────────────────────────────┐
│ Kunde:                     │
│ ○ Aus Kundenstamm:        │
│   [Belgischer Kunde ▼]    │
│                            │
│ ● Manuell eingeben:       │
│   Name: [_____________]    │
│   Land: [Belgien ▼]       │
│   USt-IdNr: [_________]   │
│   ☑ Als Kunde speichern   │ ← Optional!
└────────────────────────────┘
```

### **Vorteile:**

✅ **Flexibel** - User entscheidet: Stamm oder manuell
✅ **Wiederholte Kunden** - Aus Stamm wählen (schnell)
✅ **Einmalige Kunden** - Direkt eingeben (kein Overhead)
✅ **Moderater Aufwand** - ca. +1 Woche Entwicklungszeit

### **Nachteile:**

⚠️ **Zwei Wege** - Könnte User verwirren
⚠️ **Etwas mehr Code** - Beide Workflows implementieren

---

## 📊 **Umfrage: Was ist dir wichtiger?**

### **Frage 1: Wie viele wiederkehrende Kunden hast du?**

- [ ] **Wenige (< 5 wiederkehrend)**
  - Meist Einmalkunden, selten wiederkehrend
  - → Kundenstamm bringt wenig Nutzen

- [ ] **Mittel (5-20 wiederkehrend)**
  - Mix aus Stamm- und Einmalkunden
  - → Kundenstamm spart Zeit bei Stammkunden

- [ ] **Viele (> 20 wiederkehrend)**
  - Hauptsächlich Stammkunden, viele Rechnungen pro Kunde
  - → Kundenstamm essentiell!

---

### **Frage 2: Wie wichtig ist dir schneller Release vs. Komfort?**

- [ ] **Schnell am Markt (Option B: Ohne Stamm)**
  - Ich will RechnungsPilot so schnell wie möglich nutzen
  - Komfort kann später kommen (Version 2.0)

- [ ] **Komfort wichtiger (Option A: Mit Stamm)**
  - Ich warte lieber 2-3 Wochen länger
  - Dafür bessere UX von Anfang an

- [ ] **Kompromiss (Option C: Hybrid)**
  - 1 Woche länger für optionalen Kundenstamm ist OK
  - Flexibilität ist wichtig

---

### **Frage 3: Machst du viel EU-Geschäft?**

- [ ] **Ja, regelmäßig**
  - Validierung der USt-IdNr. ist kritisch
  - → Kundenstamm hilft (Validierung beim Anlegen)

- [ ] **Gelegentlich**
  - Paar EU-Rechnungen pro Jahr
  - → Validierung beim Export reicht

- [ ] **Nein, nur Inland**
  - Keine EU-Rechnungen
  - → USt-IdNr.-Validierung unwichtig

---

## 💬 **Deine Meinung?**

**Kommentiere gerne:**
- Welche Option bevorzugst du? (A, B, C)
- Warum?
- Habe ich einen Aspekt vergessen?
- Nutzt du bereits andere Buchhaltungs-Software? Wie macht die das?

**Beispiel-Kommentar:**

> Ich bevorzuge **Option A (mit Kundenstamm)**.
>
> Grund: Ich habe 15 Stammkunden, für die ich monatlich Rechnungen schreibe. Jedes Mal alles neu einzutippen wäre nervig. Die 2-3 Wochen Wartezeit nehme ich in Kauf für besseren Komfort.

---

## 📈 **Bisheriges Ergebnis** (wird laufend aktualisiert)

| Option | Stimmen | Prozent |
|--------|---------|---------|
| A: Mit Kundenstamm | 0 | 0% |
| B: Ohne Kundenstamm | 0 | 0% |
| C: Hybrid | 0 | 0% |

---

**Danke für dein Feedback!** 🙏

Diese Entscheidung prägt das Design von RechnungsPilot maßgeblich - daher ist eure Meinung als potenzielle User extrem wichtig!
