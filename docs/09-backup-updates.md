## **Kategorie 10.1: Backup-Strategie**

### **🎯 Anforderungen**

**Kernanforderungen:**
- ✅ **Lokale Backups** (keine Cloud-Abhängigkeit)
- ✅ **Mehrere Backup-Ziele parallel** (3-2-1-Regel)
- ✅ **Automatische & manuelle Backups**
- ✅ **Verschlüsselung optional** (AES-256)
- ✅ **GoBD-konform** (Unveränderbarkeit, Vollständigkeit)
- ⏸️ **Cloud-Backup** (v2.0 - zurückgestellt)

---

### **📂 Backup-Ziele**

#### **1. Lokales Verzeichnis**
```
Beispiel: /backup/rechnungspilot/
         C:\Backups\RechnungsFee\
```
**Eigenschaften:**
- ✅ Einfachste Variante
- ✅ Schnell
- ⚠️ Gleiche Festplatte → bei HDD-Ausfall verloren
- **Use Case:** Schnelle Wiederherstellung, Test-Backups

#### **2. Externe Festplatte / USB-Stick**
```
Beispiel: /media/usb-backup/
         D:\  (Windows - Wechseldatenträger)
```
**Eigenschaften:**
- ✅ Physisch getrennt (Fire/Theft Protection)
- ✅ Offline (Ransomware-Schutz)
- ⚠️ Manuelles Anschließen erforderlich
- **Use Case:** Tägliches Backup vor Feierabend

#### **3. Netzlaufwerk / NAS**
```
SMB/CIFS-Share:
  smb://nas.local/backups/rechnungspilot
  \\NAS\Backups\RechnungsFee

NFS:
  nfs://192.168.1.100/backups
```
**Eigenschaften:**
- ✅ Immer verfügbar (automatische Backups)
- ✅ Zentrale Verwaltung
- ✅ Meist RAID-geschützt
- ✅ Mehrere Geräte können zugreifen
- **Use Case:** Automatische nächtliche Backups

**Gängige NAS-Systeme:**
- Synology DiskStation
- QNAP
- TrueNAS
- Eigener Linux-Server (Samba)

#### **4. Lokale Freigabe (anderer PC im Netzwerk)**
```
Windows-Freigabe:
  \\DESKTOP-PC\Freigaben\Backups

Linux Samba-Share:
  smb://192.168.1.50/shared/backups
```
**Eigenschaften:**
- ✅ Keine zusätzliche Hardware nötig
- ⚠️ Abhängig von anderem PC (muss laufen)
- **Use Case:** Kleine Büros, Heimnetzwerk

---

### **🔄 3-2-1-Backup-Regel**

**Empfehlung für RechnungsFee:**

```
3 Kopien der Daten:
  1. Original (Produktiv-Datenbank)
  2. Lokales Backup (externe HDD)
  3. Netzwerk-Backup (NAS)

2 verschiedene Medien:
  - SSD/HDD (Produktiv)
  - Externe HDD (Backup 1)
  - NAS (anderes Medium - Backup 2)

1 Kopie offsite:
  - Optional: USB-HDD im Bankschließfach
  - Optional: Cloud (v2.0)
```

**Konfiguration in RechnungsFee:**
```
┌─────────────────────────────────────────────────────────┐
│ ⚙️ Backup-Konfiguration                                 │
├─────────────────────────────────────────────────────────┤
│ Backup-Ziel 1 (Primär):                                │
│ ┌─────────────────────────────────────────────────┐     │
│ │ ● Netzlaufwerk (NAS)                            │     │
│ │   Pfad: smb://nas.local/backups/rechnungspilot  │     │
│ │   Benutzer: [backup_user]                       │     │
│ │   Passwort: [***********]                       │     │
│ │   [Verbindung testen] ✅ Verbunden              │     │
│ │                                                 │     │
│ │   Zeitplan:                                     │     │
│ │   ☑ Täglich um 02:00 Uhr                        │     │
│ │   ☑ Verschlüsselung aktiviert (AES-256)        │     │
│ └─────────────────────────────────────────────────┘     │
│                                                         │
│ Backup-Ziel 2 (Sekundär):                              │
│ ┌─────────────────────────────────────────────────┐     │
│ │ ● Externe Festplatte                            │     │
│ │   Pfad: /media/usb-backup/rechnungspilot        │     │
│ │   [Pfad wählen...]                              │     │
│ │                                                 │     │
│ │   Zeitplan:                                     │     │
│ │   ○ Automatisch (wenn angeschlossen)            │     │
│ │   ● Nur manuell                                 │     │
│ │   ☑ Verschlüsselung aktiviert (AES-256)        │     │
│ └─────────────────────────────────────────────────┘     │
│                                                         │
│ Backup-Ziel 3 (Optional):                              │
│ ┌─────────────────────────────────────────────────┐     │
│ │ ○ Deaktiviert                                   │     │
│ │   [+ Weiteres Ziel hinzufügen]                  │     │
│ └─────────────────────────────────────────────────┘     │
│                                                         │
│ [Jetzt Backup durchführen]      [Speichern]            │
└─────────────────────────────────────────────────────────┘
```

---

### **💾 Backup-Strategien**

#### **1. Vollbackup (Full Backup)**

**Beschreibung:** Komplette Kopie aller Daten

**Vorteile:**
- ✅ Einfachste Wiederherstellung (nur ein Backup nötig)
- ✅ Unabhängig von vorherigen Backups

**Nachteile:**
- ❌ Viel Speicherplatz
- ❌ Langsam (bei großen Datenmengen)

**Empfehlung für RechnungsFee:**
- **Wöchentlich:** Vollbackup (z.B. Sonntag Nacht)
- **Aufbewahrung:** 4 Wochen (4 Vollbackups)

**Dateistruktur:**
```
/backup/rechnungspilot/
├── full_2025-12-09_020000.tar.gz.enc
├── full_2025-12-02_020000.tar.gz.enc
├── full_2025-11-25_020000.tar.gz.enc
└── full_2025-11-18_020000.tar.gz.enc
```

#### **2. Inkrementelles Backup**

**Beschreibung:** Nur geänderte Dateien seit dem letzten Backup (egal ob Full oder Inkrementell)

**Vorteile:**
- ✅ Sehr schnell
- ✅ Wenig Speicherplatz

**Nachteile:**
- ❌ Wiederherstellung komplex (braucht Full + alle inkrementellen Backups)
- ❌ Bei Verlust eines inkrementellen Backups → Kette unterbrochen

**Empfehlung für RechnungsFee:**
- **Täglich:** Inkrementelles Backup
- **Aufbewahrung:** 30 Tage

**Dateistruktur:**
```
/backup/rechnungspilot/
├── full_2025-12-09_020000.tar.gz.enc          # Vollbackup (Sonntag)
├── incr_2025-12-10_020000.tar.gz.enc          # +Montag
├── incr_2025-12-11_020000.tar.gz.enc          # +Dienstag
├── incr_2025-12-12_020000.tar.gz.enc          # +Mittwoch
├── incr_2025-12-13_020000.tar.gz.enc          # +Donnerstag
├── incr_2025-12-14_020000.tar.gz.enc          # +Freitag
└── incr_2025-12-15_020000.tar.gz.enc          # +Samstag
```

#### **3. Differentielles Backup**

**Beschreibung:** Nur geänderte Dateien seit dem letzten Vollbackup

**Vorteile:**
- ✅ Schneller als Vollbackup
- ✅ Einfachere Wiederherstellung als inkrementell (nur Full + letztes Diff)

**Nachteile:**
- ⚠️ Wächst im Laufe der Woche (alle Änderungen seit Full)

**Empfehlung für RechnungsFee:**
- Alternative zu inkrementell
- Einfacher für Einsteiger

**Dateistruktur:**
```
/backup/rechnungspilot/
├── full_2025-12-09_020000.tar.gz.enc          # Vollbackup (Sonntag)
├── diff_2025-12-10_020000.tar.gz.enc          # Änderungen seit Sonntag
├── diff_2025-12-11_020000.tar.gz.enc          # Änderungen seit Sonntag
├── diff_2025-12-12_020000.tar.gz.enc          # Änderungen seit Sonntag
└── diff_2025-12-13_020000.tar.gz.enc          # Änderungen seit Sonntag
```

---

### **📦 Backup-Inhalte**

**Was wird gesichert?**

```
rechnungspilot-backup/
├── database/
│   └── rechnungspilot.db              # SQLite-Datenbank (Hauptdaten)
│
├── documents/
│   ├── belege/                        # Eingangsrechnungen (PDFs)
│   ├── rechnungen/                    # Ausgangsrechnungen (PDFs)
│   ├── agb/                           # AGB-Versionen
│   └── widerrufsbelehrung/            # Widerrufsbelehrungen
│
├── imports/
│   ├── 2025/12/09/                    # Import-Archive (Bank-CSV, etc.)
│   │   ├── sparkasse_20251209.csv
│   │   └── paypal_20251209.csv
│   └── ...
│
├── config/
│   ├── settings.json                  # Benutzer-Einstellungen
│   ├── templates/                     # Bank-CSV-Templates (User)
│   └── firma.json                     # Firmenstammdaten
│
└── metadata.json                      # Backup-Metadaten (Timestamp, Version, Hash)
```

**Größenabschätzung:**
```
Startgröße (frische Installation):   ~50 MB
Nach 1 Jahr (100 Rechnungen/Monat):  ~2 GB
  - Datenbank: 100 MB
  - Belege (PDFs): 1,5 GB (avg. 150 KB/PDF × 1200 PDFs)
  - Imports: 200 MB
  - Config: 10 MB
```

---

### **🔐 Verschlüsselung**

**⭐ STANDARDMÄSSIG AKTIVIERT** (Privacy by Default - DSGVO Art. 25)

**Warum Verschlüsselung als Standard?**

1. ✅ **DSGVO Art. 32** fordert Verschlüsselung explizit
2. ✅ **DSGVO Art. 34 Abs. 3 lit. a:** Bei Verschlüsselung **KEINE Meldepflicht** bei Verlust/Diebstahl!
3. ✅ **Schutz vor physischem Zugriff:** USB-Stick verloren? Kein Problem!
4. ✅ **Geschäftsgeheimnisse geschützt:** Umsätze, Preise, Kundenbeziehungen
5. ✅ **Kein Bußgeld-Risiko** bei Datenverlust

**Was passiert OHNE Verschlüsselung bei Verlust?**
```
❌ Meldepflicht an Datenschutzbehörde (72h)
❌ Benachrichtigung ALLER Kunden
❌ Bußgeld bis 20 Mio. € oder 4% Jahresumsatz
❌ Reputationsschaden
```

**Mit Verschlüsselung:**
```
✅ Keine Meldepflicht (Art. 34 Abs. 3 DSGVO)
✅ Keine Kundenbenachrichtigung nötig
✅ Daten bleiben geschützt
✅ Kein Bußgeld-Risiko
```

**Deaktivierung möglich:** User kann Verschlüsselung deaktivieren (opt-out), aber nur mit expliziter Risiko-Warnung.

**Algorithmus:** AES-256 (industry standard)

**Implementierung:**
```python
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

def encrypt_backup(backup_file: str, password: str) -> str:
    """
    Verschlüsselt Backup-Datei mit AES-256.
    """
    # 1. Passwort → Schlüssel (PBKDF2)
    salt = os.urandom(16)
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bit
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = kdf.derive(password.encode())

    # 2. Initialisierungsvektor (IV)
    iv = os.urandom(16)

    # 3. Datei verschlüsseln
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    with open(backup_file, 'rb') as f_in:
        plaintext = f_in.read()

    # Padding (AES benötigt Vielfaches von 16 Bytes)
    padding_length = 16 - (len(plaintext) % 16)
    plaintext += bytes([padding_length]) * padding_length

    ciphertext = encryptor.update(plaintext) + encryptor.finalize()

    # 4. Salt + IV + Ciphertext speichern
    encrypted_file = backup_file + '.enc'
    with open(encrypted_file, 'wb') as f_out:
        f_out.write(salt)       # 16 Bytes
        f_out.write(iv)         # 16 Bytes
        f_out.write(ciphertext) # Rest

    # Original-Datei löschen (sicher)
    os.remove(backup_file)

    return encrypted_file
```

**UI - Standard-Einrichtung:**
```
┌─────────────────────────────────────────────────────────┐
│ 🔐 Backup-Verschlüsselung (DSGVO-konform)               │
├─────────────────────────────────────────────────────────┤
│ ☑ Backups verschlüsseln (empfohlen, DSGVO Art. 32)     │
│                                                         │
│ ℹ️ Warum Verschlüsselung wichtig ist:                   │
│ • Schutz bei Diebstahl/Verlust (Art. 32 DSGVO)         │
│ • Keine Meldepflicht bei Datenverlust (Art. 34 DSGVO)  │
│ • Geschäftsgeheimnisse geschützt                       │
│ • Kundendaten bleiben vertraulich                      │
│                                                         │
│ Verschlüsselungs-Passwort:                              │
│ ┌─────────────────────────────────────────────────┐     │
│ │ [●●●●●●●●●●●●●●●●●●●●]  [Generieren]           │     │
│ └─────────────────────────────────────────────────┘     │
│ Stärke: ████████████████░░░░ Stark                      │
│                                                         │
│ Passwort wiederholen:                                   │
│ ┌─────────────────────────────────────────────────┐     │
│ │ [●●●●●●●●●●●●●●●●●●●●]                          │     │
│ └─────────────────────────────────────────────────┘     │
│                                                         │
│ ☑ Passwort in System-Keychain speichern (empfohlen)    │
│   (Automatische Wiederherstellung ohne Passwort-Eingabe)│
│                                                         │
│ ⚠️ WICHTIG: Passwort zusätzlich sicher aufbewahren!    │
│    (z.B. Passwort-Manager, Notiz im Safe)              │
│    Ohne Passwort ist Backup nicht wiederherstellbar!   │
│                                                         │
│ [Erweiterte Optionen...]                [Speichern]     │
└─────────────────────────────────────────────────────────┘
```

**UI - Erweiterte Optionen (Deaktivierung mit Warnung):**
```
┌─────────────────────────────────────────────────────────┐
│ ⚙️ Erweiterte Backup-Optionen                           │
├─────────────────────────────────────────────────────────┤
│ Verschlüsselung:                                        │
│ ☐ Verschlüsselung deaktivieren (NICHT empfohlen!)      │
│                                                         │
│ ⚠️ WARNUNG - Datenschutzrisiko!                        │
│ ┌─────────────────────────────────────────────────┐     │
│ │ Unverschlüsselte Backups sind ein Risiko:      │     │
│ │                                                 │     │
│ │ Bei Diebstahl/Verlust musst du:                │     │
│ │ • Datenschutzbehörde informieren (Art. 33)     │     │
│ │ • ALLE Kunden benachrichtigen (Art. 34)        │     │
│ │ • Mit Bußgeldern rechnen (bis 20 Mio. €)      │     │
│ │                                                 │     │
│ │ Nur deaktivieren wenn:                          │     │
│ │ • Backup-Medium physisch gesichert (Safe)       │     │
│ │ • Kein Transport (bleibt im verschl. Raum)     │     │
│ │ • Sie das Risiko verstehen und akzeptieren     │     │
│ └─────────────────────────────────────────────────┘     │
│                                                         │
│ ☐ Ich verstehe das Risiko und verzichte auf            │
│   Verschlüsselung (Haftung liegt bei mir)              │
│                                                         │
│ [Abbrechen]                              [Speichern]    │
└─────────────────────────────────────────────────────────┘
```

---

### **⏰ Backup-Zeitplan**

**Automatische Backups:**

```python
# Beispiel: Backup-Schedule
backup_schedule = {
    'vollbackup': {
        'frequenz': 'wöchentlich',
        'wochentag': 'Sonntag',
        'uhrzeit': '02:00',
        'aufbewahrung': 4  # 4 Wochen
    },
    'inkrementell': {
        'frequenz': 'täglich',
        'uhrzeit': '02:00',
        'aufbewahrung': 30  # 30 Tage
    },
    'vor_update': {
        'trigger': 'auto',  # Automatisch vor jedem Update
        'typ': 'vollbackup',
        'aufbewahrung': 'permanent'  # Nicht automatisch löschen
    }
}
```

**UI:**
```
┌─────────────────────────────────────────────────────────┐
│ ⏰ Backup-Zeitplan                                      │
├─────────────────────────────────────────────────────────┤
│ Vollbackup:                                             │
│ ☑ Automatisch                                           │
│   Wöchentlich, jeden [Sonntag ▼] um [02:00]            │
│   Aufbewahrung: [4] Wochen                              │
│                                                         │
│ Inkrementelles Backup:                                  │
│ ☑ Automatisch                                           │
│   Täglich um [02:00]                                    │
│   Aufbewahrung: [30] Tage                               │
│                                                         │
│ Sonder-Backups:                                         │
│ ☑ Vor Software-Updates (automatisch)                   │
│ ☑ Vor DATEV-Export (optional)                          │
│ ☑ Vor Jahresabschluss (Erinnerung)                     │
│                                                         │
│ ⭐ Backup beim Beenden:                                 │
│ ☑ Automatisches Backup beim Beenden (wenn Änderungen)  │
│   (Greift nur, wenn KEIN automatischer Zeitplan aktiv) │
│                                                         │
│ Nächstes geplantes Backup:                             │
│ 📅 Sonntag, 15.12.2025 um 02:00 Uhr (Vollbackup)       │
│                                                         │
│ [Backup jetzt durchführen]              [Speichern]    │
└─────────────────────────────────────────────────────────┘
```

---

### **💾 Backup beim Beenden (Exit-Backup)**

**Problem:** User vergessen oft manuelle Backups!

**Lösung:** Automatisches Backup beim Beenden der Anwendung, wenn:
1. ✅ **KEINE** automatische Zeitplanung aktiv ist (weder täglich noch wöchentlich)
2. ✅ Es **Änderungen** seit dem letzten Backup gab
3. ✅ Die Option aktiviert ist (Standard: AN)

**Vorteil:**
- Backups werden niemals vergessen
- Beenden ist ein natürlicher Zeitpunkt (Arbeitstag abgeschlossen)
- Nur wenn wirklich etwas geändert wurde

#### **Change-Tracking (Änderungserkennung)**

**RechnungsFee trackt automatisch alle Änderungen:**

```sql
-- Change Tracking Tabelle
CREATE TABLE change_log (
    id INTEGER PRIMARY KEY,
    tabelle TEXT NOT NULL,         -- 'rechnungen', 'belege', 'kunden', etc.
    aktion TEXT NOT NULL,           -- 'insert', 'update', 'delete'
    datensatz_id INTEGER,
    geaendert_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger bei jeder Änderung (Beispiel: Rechnungen)
CREATE TRIGGER rechnung_changed
AFTER INSERT ON rechnungen
BEGIN
    INSERT INTO change_log (tabelle, aktion, datensatz_id)
    VALUES ('rechnungen', 'insert', NEW.id);
END;

CREATE TRIGGER rechnung_updated
AFTER UPDATE ON rechnungen
BEGIN
    INSERT INTO change_log (tabelle, aktion, datensatz_id)
    VALUES ('rechnungen', 'update', NEW.id);
END;

-- Funktion: Hat sich was geändert?
CREATE VIEW hat_aenderungen AS
SELECT
    COUNT(*) AS anzahl_aenderungen,
    MAX(geaendert_am) AS letzte_aenderung
FROM change_log
WHERE geaendert_am > (
    SELECT MAX(erstellt_am) FROM backups WHERE status = 'erfolgreich'
);
```

#### **UI: Beenden-Dialog mit Backup**

**Fall 1: Änderungen vorhanden, Exit-Backup aktiv**

```
┌─────────────────────────────────────────────────────────┐
│ 💾 Backup vor dem Beenden                               │
├─────────────────────────────────────────────────────────┤
│ Seit dem letzten Backup hast du einiges geändert:      │
│                                                         │
│ • 3 neue Rechnungen                                     │
│ • 2 neue Belege                                         │
│ • 1 Kunde aktualisiert                                  │
│                                                         │
│ Letzte Änderung: Heute, 17:42 Uhr                      │
│ Letztes Backup:  Gestern, 02:00 Uhr                    │
│                                                         │
│ ☑ Backup jetzt durchführen (empfohlen)                 │
│                                                         │
│ Backup-Ziel: Netzlaufwerk (NAS)                        │
│ Geschätzte Dauer: ~30 Sekunden                         │
│                                                         │
│ [Ohne Backup beenden]          [Backup & Beenden ✅]    │
└─────────────────────────────────────────────────────────┘
```

**Backup läuft:**

```
┌─────────────────────────────────────────────────────────┐
│ 💾 Backup wird erstellt...                              │
├─────────────────────────────────────────────────────────┤
│ ████████████████████░░░░░░ 75%                          │
│                                                         │
│ Verschlüssele Daten...                                  │
│                                                         │
│ Bitte warte, RechnungsFee wird nach dem              │
│ Backup automatisch geschlossen.                        │
│                                                         │
│ [Im Hintergrund beenden] ❌ Nicht empfohlen             │
└─────────────────────────────────────────────────────────┘
```

**Backup erfolgreich:**

```
┌─────────────────────────────────────────────────────────┐
│ ✅ Backup erfolgreich!                                  │
├─────────────────────────────────────────────────────────┤
│ Backup wurde erfolgreich erstellt:                     │
│                                                         │
│ 📁 Datei: full_2025-12-09_174530.tar.gz.enc            │
│ 📊 Größe: 2,3 MB                                        │
│ 🔐 Verschlüsselt: Ja (AES-256)                         │
│ 📍 Ziel: smb://nas.local/backups/rechnungspilot        │
│                                                         │
│ RechnungsFee wird jetzt geschlossen.                 │
│                                                         │
│ [Schließen ✓]                                           │
└─────────────────────────────────────────────────────────┘
```

**Fall 2: KEINE Änderungen → Kein Backup nötig**

```
┌─────────────────────────────────────────────────────────┐
│ 👋 Auf Wiedersehen!                                     │
├─────────────────────────────────────────────────────────┤
│ Seit dem letzten Backup gab es keine Änderungen.       │
│                                                         │
│ Letztes Backup:  Heute, 02:00 Uhr                      │
│                                                         │
│ [Beenden ✓]                                             │
└─────────────────────────────────────────────────────────┘
```

**Fall 3: Automatischer Zeitplan aktiv → Exit-Backup deaktiviert**

```
Beenden ohne Rückfrage, da:
- Automatisches Backup ist konfiguriert (täglich 02:00 Uhr)
- Exit-Backup daher nicht nötig
```

#### **Logik-Flussdiagramm**

```
User klickt "Beenden"
    │
    ├─→ Automatischer Zeitplan aktiv?
    │   ├─→ JA: Sofort beenden (keine Rückfrage)
    │   └─→ NEIN: Weiter
    │
    ├─→ Exit-Backup aktiviert?
    │   ├─→ NEIN: Sofort beenden
    │   └─→ JA: Weiter
    │
    ├─→ Änderungen seit letztem Backup?
    │   ├─→ NEIN: Beenden (kurze Info: "Keine Änderungen")
    │   └─→ JA: Backup-Dialog anzeigen
    │
    └─→ Backup-Dialog
        ├─→ User wählt "Backup & Beenden"
        │   ├─→ Backup durchführen
        │   ├─→ Erfolgsmeldung
        │   └─→ Beenden
        │
        └─→ User wählt "Ohne Backup beenden"
            └─→ Sofort beenden (Risiko auf eigene Verantwortung)
```

#### **Implementierung**

```python
def on_exit():
    """
    Wird beim Beenden der Anwendung aufgerufen.
    """
    # 1. Prüfe: Automatischer Zeitplan aktiv?
    zeitplan_aktiv = db.execute("""
        SELECT COUNT(*) FROM backup_ziele
        WHERE zeitplan_aktiv = 1
    """).fetchone()[0] > 0

    if zeitplan_aktiv:
        # Automatisches Backup läuft → Exit-Backup nicht nötig
        sys.exit(0)

    # 2. Prüfe: Exit-Backup aktiviert?
    exit_backup_aktiv = db.execute("""
        SELECT backup_beim_beenden FROM einstellungen
    """).fetchone()[0]

    if not exit_backup_aktiv:
        # Exit-Backup deaktiviert → Beenden
        sys.exit(0)

    # 3. Prüfe: Änderungen seit letztem Backup?
    letztes_backup = db.execute("""
        SELECT MAX(erstellt_am) FROM backups
        WHERE status = 'erfolgreich'
    """).fetchone()[0]

    aenderungen = db.execute("""
        SELECT COUNT(*) FROM change_log
        WHERE geaendert_am > ?
    """, (letztes_backup,)).fetchone()[0]

    if aenderungen == 0:
        # Keine Änderungen → Beenden (mit kurzer Info)
        show_info_dialog("Keine Änderungen seit letztem Backup.")
        sys.exit(0)

    # 4. Änderungen vorhanden → Backup-Dialog anzeigen
    dialog = ExitBackupDialog(aenderungen_details={
        'anzahl_rechnungen': count_changes('rechnungen'),
        'anzahl_belege': count_changes('belege'),
        'anzahl_kunden': count_changes('kunden'),
        'letzte_aenderung': get_last_change_time(),
        'letztes_backup': letztes_backup
    })

    if dialog.show() == 'BACKUP':
        # User will Backup
        if perform_backup():
            show_success_dialog("Backup erfolgreich!")
            sys.exit(0)
        else:
            show_error_dialog("Backup fehlgeschlagen!")
            # User entscheiden lassen: trotzdem beenden?
            if show_question("Trotzdem beenden?"):
                sys.exit(0)
    else:
        # User will ohne Backup beenden
        sys.exit(0)
```

#### **Einstellungen: Exit-Backup konfigurieren**

```
┌─────────────────────────────────────────────────────────┐
│ ⚙️ Einstellungen → Backup                               │
├─────────────────────────────────────────────────────────┤
│ 💾 Backup beim Beenden                                  │
│                                                         │
│ ☑ Automatisches Backup beim Beenden (wenn Änderungen)  │
│                                                         │
│ ℹ️ Diese Option ist nur aktiv, wenn KEIN automatischer │
│    Zeitplan konfiguriert ist.                          │
│                                                         │
│ Vorteile:                                              │
│ • Sie vergessen nie ein Backup                         │
│ • Backup nur bei echten Änderungen                     │
│ • Beenden ist natürlicher Zeitpunkt                    │
│                                                         │
│ Nachteile:                                             │
│ • Beenden dauert etwas länger (~30 Sekunden)           │
│ • Bei großen Datenmengen kann es nerven                │
│                                                         │
│ Empfehlung:                                            │
│ Aktivieren Sie entweder:                               │
│ • Automatischen Zeitplan (täglich/wöchentlich) ODER    │
│ • Exit-Backup                                          │
│                                                         │
│ [Speichern]                                            │
└─────────────────────────────────────────────────────────┘
```

---

### **🔄 Restore (Wiederherstellung)**

#### **1. Vollständige Wiederherstellung**

**Szenario:** Festplatte defekt, Neuinstallation nötig

**Workflow:**
```
1. RechnungsFee neu installieren
2. Backup auswählen:
   ┌─────────────────────────────────────────────────────────┐
   │ 📥 Backup wiederherstellen                              │
   ├─────────────────────────────────────────────────────────┤
   │ Backup-Quelle:                                          │
   │ ● Externe Festplatte: /media/usb-backup                │
   │ ○ Netzlaufwerk: smb://nas.local/backups                │
   │ ○ Anderer Pfad: [Durchsuchen...]                       │
   │                                                         │
   │ Verfügbare Backups:                                     │
   │ ┌─────────────────────────────────────────────────┐     │
   │ │ ● 15.12.2025 02:00 - Vollbackup (2,3 GB)       │     │
   │ │ ○ 14.12.2025 02:00 - Inkrementell (15 MB)      │     │
   │ │ ○ 13.12.2025 02:00 - Inkrementell (22 MB)      │     │
   │ │ ○ 08.12.2025 02:00 - Vollbackup (2,2 GB)       │     │
   │ └─────────────────────────────────────────────────┘     │
   │                                                         │
   │ ⚠️ Warnung: Alle aktuellen Daten werden überschrieben! │
   │                                                         │
   │ [Abbrechen]                   [Wiederherstellen →]      │
   └─────────────────────────────────────────────────────────┘

3. Bei verschlüsseltem Backup: Passwort eingeben
4. Wiederherstellung (Fortschrittsbalken)
5. Fertig! RechnungsFee neu starten
```

#### **2. Einzelne Datei/Beleg wiederherstellen**

**Szenario:** Versehentlich gelöschtes PDF

**Workflow:**
```
1. Backup durchsuchen:
   ┌─────────────────────────────────────────────────────────┐
   │ 🔍 Backup durchsuchen                                   │
   ├─────────────────────────────────────────────────────────┤
   │ Suche nach:                                             │
   │ [Rechnung RE-2025-001]                    [Suchen]      │
   │                                                         │
   │ Gefunden in Backup vom 08.12.2025:                      │
   │ ┌─────────────────────────────────────────────────┐     │
   │ │ ☑ RE-2025-001.pdf (145 KB)                      │     │
   │ │ ☑ RE-2025-001.xrechnung.xml (12 KB)            │     │
   │ └─────────────────────────────────────────────────┘     │
   │                                                         │
   │ [Abbrechen]          [Exportieren...]  [Wiederherstellen│
   └─────────────────────────────────────────────────────────┘

2. Datei wiederherstellen oder an anderem Ort speichern
```

#### **3. Point-in-Time Recovery**

**Szenario:** "Wie sah meine Datenbank am 01.12. aus?"

**Workflow:**
```
1. Backup vom gewünschten Datum auswählen
2. In temporäres Verzeichnis entpacken
3. Datenbank im Read-Only-Modus öffnen
4. Daten prüfen/exportieren
5. Optional: Bestimmte Datensätze in aktuelle DB kopieren
```

---

### **🗄️ Datenbank-Schema für Backups**

```sql
-- Backup-Historie
CREATE TABLE backups (
    id INTEGER PRIMARY KEY,
    typ TEXT NOT NULL, -- 'full', 'incremental', 'differential'
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ziel TEXT NOT NULL, -- '/media/usb-backup', 'smb://nas.local/backups'
    ziel_typ TEXT NOT NULL, -- 'lokal', 'usb', 'netzwerk'

    -- Backup-Datei
    dateiname TEXT NOT NULL, -- 'full_2025-12-09_020000.tar.gz.enc'
    dateipfad TEXT NOT NULL, -- Vollständiger Pfad
    dateigroesse INTEGER, -- Bytes
    hash_sha256 TEXT, -- Integritätsprüfung

    -- Verschlüsselung (standardmäßig aktiviert!)
    verschluesselt BOOLEAN DEFAULT 1, -- Privacy by Default (DSGVO Art. 25)
    verschluesselungs_algorithmus TEXT DEFAULT 'AES-256-CBC',

    -- Metadaten
    software_version TEXT, -- RechnungsFee-Version
    datenbank_version INTEGER, -- Schema-Version
    anzahl_rechnungen INTEGER,
    anzahl_belege INTEGER,
    anzahl_kunden INTEGER,

    -- Status
    status TEXT DEFAULT 'erfolgreich', -- 'erfolgreich', 'fehler', 'abgebrochen'
    fehlermeldung TEXT,
    dauer_sekunden INTEGER,

    -- Aufbewahrung
    aufbewahren_bis DATE, -- NULL = permanent
    automatisch_geloescht BOOLEAN DEFAULT 0,

    -- Abhängigkeiten (für inkrementelle Backups)
    basiert_auf_backup_id INTEGER, -- NULL bei Vollbackup

    -- Exit-Backup
    exit_backup BOOLEAN DEFAULT 0, -- Wurde beim Beenden erstellt?

    CHECK (typ IN ('full', 'incremental', 'differential')),
    CHECK (ziel_typ IN ('lokal', 'usb', 'netzwerk', 'nas')),
    FOREIGN KEY (basiert_auf_backup_id) REFERENCES backups(id)
);

CREATE INDEX idx_backups_typ ON backups(typ);
CREATE INDEX idx_backups_datum ON backups(erstellt_am);
CREATE INDEX idx_backups_ziel ON backups(ziel_typ);

-- Backup-Ziele (mehrere möglich)
CREATE TABLE backup_ziele (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL, -- 'Primäres NAS', 'USB-Backup', etc.
    typ TEXT NOT NULL, -- 'lokal', 'usb', 'netzwerk', 'nas'
    pfad TEXT NOT NULL, -- '/media/usb-backup' oder 'smb://nas.local/backups'

    -- Authentifizierung (für Netzwerk)
    benutzer TEXT,
    passwort_keychain_id TEXT, -- Referenz zu System-Keychain

    -- Zeitplan
    zeitplan_aktiv BOOLEAN DEFAULT 0,
    zeitplan_typ TEXT, -- 'täglich', 'wöchentlich', 'monatlich'
    zeitplan_uhrzeit TEXT, -- '02:00'
    zeitplan_wochentag INTEGER, -- 0=Sonntag, 1=Montag, etc. (nur bei wöchentlich)

    -- Backup-Typ
    backup_typ TEXT DEFAULT 'full', -- 'full', 'incremental', 'differential'

    -- Verschlüsselung
    verschluesselt BOOLEAN DEFAULT 1,
    passwort_keychain_id_backup TEXT, -- Backup-Verschlüsselungspasswort

    -- Status
    aktiv BOOLEAN DEFAULT 1,
    letztes_backup TIMESTAMP,
    letzter_fehler TEXT,

    CHECK (typ IN ('lokal', 'usb', 'netzwerk', 'nas')),
    CHECK (backup_typ IN ('full', 'incremental', 'differential'))
);

-- Change Tracking (für Exit-Backup)
CREATE TABLE change_log (
    id INTEGER PRIMARY KEY,
    tabelle TEXT NOT NULL, -- 'rechnungen', 'belege', 'kunden', etc.
    aktion TEXT NOT NULL, -- 'insert', 'update', 'delete'
    datensatz_id INTEGER,
    geaendert_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CHECK (aktion IN ('insert', 'update', 'delete'))
);

CREATE INDEX idx_change_log_datum ON change_log(geaendert_am);
CREATE INDEX idx_change_log_tabelle ON change_log(tabelle);

-- View: Änderungen seit letztem Backup
CREATE VIEW hat_aenderungen AS
SELECT
    COUNT(*) AS anzahl_aenderungen,
    MAX(geaendert_am) AS letzte_aenderung
FROM change_log
WHERE geaendert_am > (
    SELECT COALESCE(MAX(erstellt_am), '1970-01-01')
    FROM backups
    WHERE status = 'erfolgreich'
);

-- Einstellungen (Erweiterung)
-- ALTER TABLE einstellungen ADD COLUMN backup_beim_beenden BOOLEAN DEFAULT 1;
-- (Diese Spalte wird zur bestehenden einstellungen-Tabelle hinzugefügt)
```

---

### **📋 MVP-Umfang für Kategorie 10.1 (Backup)**

#### **Phase 1 (v1.0 - MVP):**

**Backup-Ziele:**
- ✅ Lokales Verzeichnis
- ✅ Externe Festplatte / USB
- ✅ Netzlaufwerk (SMB/CIFS)
- ✅ Mehrere Ziele parallel (bis zu 3)

**Backup-Strategien:**
- ✅ Vollbackup
- ⏸️ Inkrementelles Backup - optional (v1.1, wenn Zeit)
- ❌ Differentielles Backup - v1.1

**Features:**
- ✅ Manuelles Backup (On-Demand)
- ✅ Automatisches Backup (Zeitplan)
- ✅ **Exit-Backup** (Backup beim Beenden, wenn Änderungen) ⭐ NEU
- ✅ **Change-Tracking** (automatische Änderungserkennung) ⭐ NEU
- ✅ **Verschlüsselung STANDARD** (AES-256, opt-out mit Warnung) ⭐
- ✅ Passwort in System-Keychain (automatisch)
- ✅ Passwort-Generator (sichere Passwörter)
- ✅ Backup vor Software-Update (automatisch, Pflicht)
- ✅ Vollständige Wiederherstellung
- ⏸️ Einzeldatei-Wiederherstellung - optional (v1.1)

**Cloud-Backup:**
- ❌ **NICHT in v1.0** - zurückgestellt auf v2.0

#### **Phase 2 (v1.1):**
- Inkrementelles/Differentielles Backup
- Einzeldatei-Wiederherstellung (Backup-Browser)
- Backup-Verifizierung (Hash-Check)
- Backup-Rotation automatisch
- Backup-Benachrichtigungen (E-Mail bei Fehler)

#### **Phase 3 (v2.0):**
- Cloud-Backup (S3-kompatibel: AWS, Backblaze B2, Wasabi)
- WebDAV (Nextcloud, ownCloud)
- SFTP/SCP
- Backup-Verschlüsselung mit GPG (zusätzlich zu AES)
- Deduplizierung (nur geänderte Blöcke speichern)

---

### **✅ Status: Kategorie 10.1 - Backup vollständig geklärt**

**Wichtigste Entscheidungen:**

1. ✅ **Lokale Backups für v1.0** (keine Cloud-Abhängigkeit)
2. ✅ **Mehrere Backup-Ziele parallel** (3-2-1-Regel)
3. ✅ **Vollbackup + optional Inkrementell** (v1.0/v1.1)
4. ✅ **Verschlüsselung STANDARDMÄSSIG AKTIVIERT** ⭐
   - AES-256 mit PBKDF2 (100.000 Iterationen)
   - Privacy by Default (DSGVO Art. 25)
   - Deaktivierung möglich (opt-out mit Warnung)
   - Passwort in System-Keychain
5. ✅ **Automatischer Backup-Zeitplan** (täglich/wöchentlich)
6. ✅ **Exit-Backup beim Beenden** (wenn keine Zeitplanung aktiv) ⭐ NEU
   - Nur wenn Änderungen seit letztem Backup
   - Change-Tracking mit automatischen Triggers
   - Benutzerfreundliche Backup-Dialoge
   - Kann deaktiviert werden
7. ✅ **Backup vor Update** (Pflicht, automatisch)
8. ⏸️ **Cloud-Backup** → v2.0

**Backup-Ziele:**
- Lokales Verzeichnis
- Externe Festplatte
- NAS/Netzlaufwerk (SMB/CIFS)
- Lokale Freigaben (anderer PC)

**DSGVO-Konformität:** ⭐
- **Art. 32 DSGVO:** Verschlüsselung als technische Schutzmaßnahme
- **Art. 34 Abs. 3 DSGVO:** Bei Verschlüsselung KEINE Meldepflicht bei Verlust
- **Art. 25 DSGVO:** Privacy by Default (Verschlüsselung standardmäßig aktiv)
- SHA256-Hash für Integrität
- Unveränderbare Backups
- Vollständige Aufzeichnung (Metadaten)

---

## **Kategorie 10.2: Software-Updates**

### **Update-Strategie**

**Grundprinzip:** Sicher, automatisch, mit Backup-Absicherung

### **🔄 Update-Mechanismen**

#### **1. Auto-Update (Standard)** ✅ Implementiert (v0.1.1)

**Desktop-App (Tauri):**
- `tauri-plugin-updater` – prüft beim Start auf neue Versionen
- Endpoint: GitHub Releases `latest.json`
- Signing-Key: `~/.tauri/rechnungsfee.key` (Public Key in `tauri.conf.json`)
- Frontend: `useUpdateCheck`-Hook + grünes Banner in `InfoPage`
- `downloadAndInstall()` → App startet automatisch neu

**Workflow:**
```
1. RechnungsFee startet
   ↓
2. Prüft: Neue Version verfügbar?
   ↓ JA
3. 🔔 "Update verfügbar: v1.2.0 → v1.3.0"
   ┌─────────────────────────────────────────┐
   │ 🎉 Update verfügbar!                    │
   ├─────────────────────────────────────────┤
   │ Version 1.3.0 ist verfügbar.           │
   │                                         │
   │ Neue Features:                          │
   │ • Verbesserte UStVA-Prüfung             │
   │ • Schnellerer DATEV-Export              │
   │ • Bugfixes für Kassenbuch               │
   │                                         │
   │ Größe: 45 MB                            │
   │                                         │
   │ ☑ Automatisch beim Beenden installieren│
   │                                         │
   │ [Später]  [Jetzt herunterladen]         │
   └─────────────────────────────────────────┘
   ↓
4. Download im Hintergrund (Progress-Bar)
   ↓
5. User beendet RechnungsFee
   ↓
6. **AUTOMATISCHES BACKUP VOR UPDATE** ⭐
   ┌─────────────────────────────────────────┐
   │ 💾 Backup vor Update (Pflicht)          │
   ├─────────────────────────────────────────┤
   │ Vor dem Update wird automatisch ein    │
   │ Backup erstellt. Dies ist verpflichtend│
   │ und kann nicht übersprungen werden.    │
   │                                         │
   │ ████████████████████░░░░ 80%            │
   │                                         │
   │ Erstelle Backup...                      │
   └─────────────────────────────────────────┘
   ↓
7. Update installieren
   ↓
8. RechnungsFee automatisch neu starten
   ↓
9. ✅ Update erfolgreich!
   "Willkommen bei RechnungsFee v1.3.0!"
```

#### **2. Manuelle Updates**

**Für Power-User / Docker:**
```bash
# Docker
docker pull rechnungspilot/rechnungspilot:latest
docker-compose down
docker-compose up -d

# AppImage
wget https://github.com/rechnungspilot/releases/latest/RechnungsFee.AppImage
chmod +x RechnungsFee.AppImage
./RechnungsFee.AppImage
```

#### **3. Update-Kanäle**

**Verfügbare Kanäle:**

| Kanal | Beschreibung | Zielgruppe | Stabilität |
|-------|--------------|------------|------------|
| **Stable** | Produktiv-Release | Alle User | ⭐⭐⭐⭐⭐ |
| **Beta** | Vorab-Test | Early Adopters | ⭐⭐⭐⭐ |
| **Nightly** | Tägliche Builds | Entwickler | ⭐⭐ |

**Einstellung:**
```
┌─────────────────────────────────────────┐
│ ⚙️ Einstellungen → Updates              │
├─────────────────────────────────────────┤
│ Update-Kanal:                           │
│ ● Stable (empfohlen)                    │
│ ○ Beta (für Early Adopters)             │
│ ○ Nightly (nur für Entwickler)          │
│                                         │
│ ☑ Automatisch nach Updates suchen      │
│ ☑ Updates automatisch herunterladen    │
│ ☑ Backup vor Update (Pflicht) ✅        │
│                                         │
│ Letzte Prüfung: Heute, 10:30 Uhr       │
│ Installierte Version: 1.2.5             │
│                                         │
│ [Jetzt nach Updates suchen]             │
└─────────────────────────────────────────┘
```

### **🛡️ Update-Sicherheit**

#### **1. Backup vor Update (PFLICHT)**

**Siehe Kategorie 10.1 - Backup:**
- Automatisches Backup IMMER vor Update
- Kann NICHT übersprungen werden
- Bei Backup-Fehler → Update wird abgebrochen
- Backup-Typ: Vollbackup (nicht inkrementell)

```python
def perform_update():
    """
    Update-Prozess mit obligatorischem Backup.
    """
    # 1. Backup erzwingen
    backup_erfolg = create_mandatory_backup(typ='vor_update')

    if not backup_erfolg:
        show_error("Update abgebrochen: Backup fehlgeschlagen!")
        return False

    # 2. Datenbank-Migration (falls nötig)
    if needs_migration():
        migrate_database()

    # 3. Update installieren
    install_update()

    # 4. Verifizierung
    if verify_update():
        return True
    else:
        # Rollback auf Backup
        restore_backup(backup_id=last_backup_before_update)
        return False
```

#### **2. Signierte Updates**

**Code Signing:**
- Alle Updates digital signiert
- Verhindert Man-in-the-Middle-Attacks
- Electron Auto-Updater prüft Signatur automatisch

```javascript
// electron-updater Konfiguration
{
  "publish": {
    "provider": "github",
    "owner": "rechnungspilot",
    "repo": "rechnungspilot"
  },
  "verifyUpdateCodeSignature": true  // ✅ Signaturprüfung
}
```

#### **3. Rollback-Funktion**

**Falls Update fehlschlägt:**

```
┌─────────────────────────────────────────┐
│ ⚠️ Update fehlgeschlagen                │
├─────────────────────────────────────────┤
│ Das Update konnte nicht installiert     │
│ werden.                                  │
│                                         │
│ Möchtest du auf die vorherige Version  │
│ zurückkehren? (Backup vom 09.12.2025)  │
│                                         │
│ [Abbrechen]  [Auf v1.2.5 zurückkehren] │
└─────────────────────────────────────────┘
```

### **📋 MVP-Umfang für Kategorie 10.2 (Update)**

#### **Phase 1 (v1.0):**
- ✅ **Auto-Update** (Electron/Tauri built-in)
- ✅ **Backup vor Update** (Pflicht, automatisch) - bereits in 10.1 geklärt
- ✅ **Update-Benachrichtigung** (beim Start)
- ✅ **Signierte Updates** (Code Signing)
- ✅ **Stable-Kanal** (Produktiv-Releases)
- ✅ **Changelog anzeigen** (Was ist neu?)
- ✅ **Manuelle Update-Prüfung** (Button in Einstellungen)

#### **Phase 2 (v1.1):**
- Beta-Kanal (Early Access)
- Rollback-UI (zurück zur vorherigen Version)
- Update-Historie (welche Versionen wurden wann installiert)

#### **Phase 3 (v2.0):**
- Nightly-Kanal (tägliche Builds)
- Delta-Updates (nur Änderungen herunterladen, spart Bandbreite)
- Offline-Updates (Update-Paket manuell importieren)

### **🗄️ Datenbank-Schema für Updates**

```sql
-- Update-Historie
CREATE TABLE update_log (
    id INTEGER PRIMARY KEY,
    version_alt TEXT NOT NULL,        -- '1.2.5'
    version_neu TEXT NOT NULL,        -- '1.3.0'
    update_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Backup-Referenz
    backup_id INTEGER NOT NULL,       -- Backup vor Update

    -- Status
    status TEXT DEFAULT 'erfolgreich', -- 'erfolgreich', 'fehler', 'rollback'
    fehlermeldung TEXT,

    -- Metadaten
    update_kanal TEXT DEFAULT 'stable', -- 'stable', 'beta', 'nightly'
    groesse_mb REAL,
    dauer_sekunden INTEGER,

    CHECK (status IN ('erfolgreich', 'fehler', 'rollback')),
    CHECK (update_kanal IN ('stable', 'beta', 'nightly')),
    FOREIGN KEY (backup_id) REFERENCES backups(id)
);

CREATE INDEX idx_update_log_datum ON update_log(update_am);
```

### **✅ Status: Kategorie 10.2 - Update vollständig geklärt**

**Wichtigste Entscheidungen:**

1. ✅ **Auto-Update als Standard** (Electron/Tauri built-in)
2. ✅ **Backup vor Update PFLICHT** (siehe Kategorie 10.1) ⭐
3. ✅ **Signierte Updates** (Code Signing für Sicherheit)
4. ✅ **Stable-Kanal für v1.0** (Beta/Nightly später)
5. ✅ **Rollback-Funktion** (bei fehlgeschlagenem Update)
6. ✅ **Changelog-Anzeige** (Transparenz über Änderungen)

**Technische Umsetzung:**
- Desktop: `electron-updater` oder `tauri-plugin-updater`
- Docker: Docker Hub / GitHub Container Registry
- AppImage: GitHub Releases mit Auto-Updater

**Sicherheit:**
- Obligatorisches Backup vor jedem Update
- Code Signing (verhindert manipulierte Updates)
- Automatischer Rollback bei Fehler

---

