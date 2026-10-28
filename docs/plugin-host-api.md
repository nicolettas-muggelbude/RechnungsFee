# Host-API für Plugin-Entwickler

Stand: Plugin-API **0.1.0**, DTO-Version **1**. Die WIT-Funktionen `get`, `list`,
`create`, `update` und `delete` sind implementiert. Schreibzugriffe verwenden
dieselben Core-Funktionen wie die App, einschließlich Nummernvergabe, Preis- und
Summenberechnung sowie Löschsperren.

## Unterstützte Operationen

| Entität | Lesen | Anlegen / Ändern / Löschen |
| --- | --- | --- |
| `customer` | Ja | Ja; Kunden mit Rechnungen oder Journalverknüpfungen sind nicht löschbar |
| `article` | Ja | Ja; verwendete Artikel und Artikel mit Lagerbestand sind nicht löschbar |
| `invoice` | Ja | Ja, ausschließlich Entwürfe; auch ausgegebene, unveränderliche oder stornierte Dokumente sind gesperrt |
| `voucher` | Nur Metadaten | Nein; Belege über den Belegimport der App verwalten |
| `task` | Nein | Nein; Aufgaben sind noch nicht implementiert |

`invoice` umfasst auch andere Dokumenttypen aus der Rechnungstabelle. Für deren
zusätzliche fachliche Regeln gelten weiterhin die gemeinsamen Core-Funktionen.
Finalisieren, Stornieren, Zahlungen oder der direkte Zugriff auf Journal und
Nummernkreise sind keine Host-CRUD-Operationen.

## Rechte und Rückgabewerte

Im Manifest sind die benötigten Operationen ausdrücklich zu deklarieren:

```toml
[permissions]
entities = [
    { type = "customer", actions = ["create", "update", "delete"] }
]
hooks = ["invoice:create:after"]
```

Die Laufzeit prüft **jede** Operation gegen den vom Nutzer bestätigten
Rechte-Snapshot. Eine Änderung nur der Manifest-Datei gewährt keine neuen Rechte.
Das Lesen per `get` oder `list` benötigt zusätzlich `read`.

```text
create(entity, payload_json)       → vollständiger DTO-JSON-Text
update(entity, id, payload_json)   → vollständiger DTO-JSON-Text
delete(entity, id)                 → kein Rückgabewert
```

IDs werden als positive Ganzzahlen in einem String übergeben. Die Rückgabe von
`create`/`update` enthält `_schema`, die vergebene ID und die vom Core berechneten
Werte. Sie erfordert kein zusätzliches Leserecht für das gerade geschriebene Objekt.
Die bestehenden [DTO-Definitionen](../src/backend/plugins/dto.py) gelten weiter.

## Schreib-Payloads

Der Payload ist ein JSON-Objekt mit den Eingabefeldern der jeweiligen API-Schemas:

- Kunden: `KundeCreate` / `KundeUpdate` in [schemas.py](../src/backend/api/schemas.py).
- Artikel: `ArtikelCreate` / `ArtikelUpdate` in [schemas_artikel.py](../src/backend/api/schemas_artikel.py).
- Rechnungen: `RechnungCreate` / `RechnungUpdate` und `RechnungspositionCreate` in
  [schemas_rechnungen.py](../src/backend/api/schemas_rechnungen.py).

Bei `update` nur die gewünschten Felder übergeben. Nicht übergebene Felder bleiben
erhalten. Das Leeren per `null` folgt dem jeweiligen API-Schema und Core-Verhalten;
beispielsweise ignoriert die Kunden-API `null`, während Rechnungseinleitungs- und
-schlusstexte damit ausdrücklich geleert werden können.

**Zusätzlich geschützt:** `id`, Nummern, Buchungs-/Zahlungs-/Abschlusszustände,
Validierungsstempel und Import-Overrides. Kundennummer, Debitorennummer und
Rechnungsnummer vergibt der Core. `ist_entwurf` darf nur `true` sein und wird beim
Anlegen einer Rechnung automatisch gesetzt. Unbekannte Felder werden abgewiesen,
auch innerhalb von Positionen. Ein optionales `_schema` muss genau zur Entität
passen, z. B. `customer@1`. Der gesamte DTO aus `get` ist deshalb **kein**
unverändert zurückschreibbarer Update-Payload.

Geldwerte als Dezimalstrings und Datumswerte als `JJJJ-MM-TT` übergeben. Beispiel:

```json
{
  "typ": "ausgang",
  "datum": "2026-10-28",
  "partner_freitext": "Beispielkunde",
  "positionen": [
    {"beschreibung": "Beratung", "menge": "2", "netto": "100.00", "ust_satz": "19"}
  ]
}
```

`invoice.create` erzeugt daraus einen Entwurf mit automatisch vergebener Nummer und
berechneten Summen. Gesamtbeträge und Steuerbeträge nicht selbst setzen.
Der maximale Schreib-Payload beträgt 1 MB. Fremdschlüssel müssen auf vorhandene
Datensätze zeigen; Textlängen werden gegen die Datenbankspalten geprüft.

## Python-Aufrufe im Wasm-Gast

Die Python-Bindings werden wie im [Python-Beispiel](../examples/plugins/python-kundenpruefung/README.md)
aus der WIT-Datei generiert. Ein Ausschnitt für einen Hook mit den oben gezeigten
Kundenrechten:

```python
import json
from componentize_py_types import Err
from wit_world.imports import host_api
from wit_world.imports.types import EntityType


def beispiel():
    try:
        kunde = json.loads(host_api.create(
            EntityType.CUSTOMER,
            json.dumps({"firmenname": "Plugin-Testkunde", "land": "DE"}),
        ))
        kunde_id = str(kunde["id"])
        geaendert = host_api.update(
            EntityType.CUSTOMER, kunde_id,
            json.dumps({"notizen": "Vom Plugin ergänzt"}),
        )
        host_api.delete(EntityType.CUSTOMER, kunde_id)
        return geaendert
    except Err as fehler:
        # fehler.value ist die generierte ApiError-Variante mit einer Meldung.
        # Der aufrufende Hook entscheidet, ob er den Fehler behandelt oder abbricht.
        raise
```

Dieser Ausschnitt zeigt alle drei Operationen und entfernt den Testkunden wieder.
Er gehört in einen kompilierten Wasm-Gast; er läuft nicht als natives Python-Skript
im Backend. In der UI-Funktion „Testlauf“ bleiben alle Host-Zugriffe gesperrt, damit
Testläufe keine echten Daten verändern.

## Transaktionen, Hooks und Protokollierung

**Pre-Hooks:** Schreibzugriffe gehören zur noch offenen Transaktion des auslösenden
Speichervorgangs. Ein späterer Abbruch, Trap oder Timeout rollt auch deren
Datenänderungen, Nummernkreisfortschritte und erfolgreiche Audit-Einträge zurück.
Jeder Host-Aufruf besitzt zusätzlich einen Savepoint: Ein vom Plugin behandelter
Fehler verwirft nur diesen Aufruf; vorherige erfolgreiche Aufrufe bleiben Teil der
äußeren Transaktion. Andere Pre-Hooks dürfen auch Host-Schreibvorgänge abweisen.

**Post-Hooks:** Jeder schreibende Host-Aufruf besitzt eine eigene Transaktion und
wird vor seiner Rückgabe committed. Mehrere Aufrufe desselben Post-Hooks bilden
keine gemeinsame atomare Transaktion. Scheitert ein späterer Aufruf oder der
Post-Hook selbst, werden frühere erfolgreiche Aufrufe nicht rückgängig gemacht.

Erfolgreiche CRUD-Aufrufe erzeugen `plugin_protokoll`-Einträge mit Plugin-ID,
`host:<entity>:<action>`, Datensatz-ID und Ergebnis `geschrieben`, in derselben
Transaktion wie die Datenänderung. Die Anzeige findet sich in den Plugin-Details.
Das optionale Debug-Protokoll erfasst zusätzlich technische Host-Aufrufmetadaten.

Durch Host-Schreibzugriffe entstehen neue Pre-/Post-Hooks. Das auslösende Plugin
und seine Vorfahren werden dabei ausgeschlossen. Diese Herkunft bleibt auch über
Commit und Hintergrund-Thread hinweg erhalten. Die maximale Verschachtelung ist
zwei Plugin-Kontexte; tiefere Schreibaufrufe werden abgewiesen. Der gerade von
einem Pre-Hook geprüfte Datensatz kann nicht rekursiv über die Host-API
überschrieben oder gelöscht werden. Pre-Hooks teilen weiterhin das gemeinsame
50-ms-Budget der Transaktion.

Post-Hooks werden erst nach dem tatsächlichen äußeren Commit gestartet, nicht beim
Freigeben eines Savepoints. Physische Dateien gelöschter Rechnungsentwürfe werden
ebenfalls erst nach erfolgreichem Commit entfernt und bleiben bei Rollback erhalten.

## Fehler und Tests

WIT liefert `unauthorized`, `not-found`, `validation-error` oder `internal-error`.
Dazu gehören fehlende Rechte, fehlende IDs/Referenzen, ungültige Payloads,
GoBD-/Löschsperren und abgewiesene verschachtelte Hooks. Datenbankfehler werden
nicht als rohe SQL-Fehlermeldungen an das Plugin weitergereicht.

```bash
make test-backend PYTEST_ARGS="-q -k plugin_schreiben"
```

Die Tests verwenden temporäre Datenbanken und prüfen CRUD, Berechnungen, Rechte,
GoBD-Sperren, Savepoints, äußeren Rollback, Nummernkreise, Audit, Hook-Verkettung und
Dateibereinigung. Für die Desktop-Auslieferung nehmen beide Sidecar-Buildskripte
`plugins.schreiben` explizit mit auf; bestehende Desktop-Pakete müssen neu gebaut werden.
