Hier ist das vollständige, konsolidierte Lastenheft im Markdown-Format.

---

# Lastenheft: Wasm-basiertes Plugin-System für RechnungsFee

**Projekt:** RechnungsFee Extension Framework

**Spezifikationsversion:** 1.0.0

**Status:** Entwurf / Bereits zur Umsetzung

**Architektur-Typ:** WebAssembly Component Model (Host/Guest Isolation)

---

Ein baubares Python-Beispiel mit Tests und Installationsanleitung findest du unter
[examples/plugins/python-kundenpruefung](../examples/plugins/python-kundenpruefung/README.md).
Schreibzugriffe, Rechte und Transaktionen beschreibt die [Host-API-Anleitung](plugin-host-api.md).
Der aktuelle Implementierungsstand und die Einschränkungen stehen im
[Umsetzungsplan](plan-plugin-system.md).

## 1. Zielsetzung & Gesamtsystem

Das Ziel dieses Vorhabens ist die Entwicklung einer modularen Plugin-Schnittstelle für RechnungsFee auf Basis von **WebAssembly (Wasm)**.

Das Plugin-System ermöglicht es Drittentwicklern, das Kernsystem um eigene Funktionen und Automatisierungen zu erweitern, ohne den Core-Quellcode zu modifizieren. Plugins laufen in einer isolierten Sandbox und kommunizieren ausschließlich über eine klar definierte WIT-Schnittstelle (*WebAssembly Interface Type*).

---

## 2. Systemarchitektur & Laufzeitumgebung

```
+-------------------------------------------------------------------------------+
|                            RechnungsFee Core (Rust)                           |
|                                                                               |
|  +------------------------+                    +---------------------------+  |
|  | Data Access Layer (DAL) | <--- DB Guard ---  |   Wasm Host (Wasmtime)    |  |
|  +-----------+------------+   (Permissions)    +-------------+-------------+  |
|              |                                               |                |
|              | Events                                        | WIT Calls      |
|              v                                               v                |
|  +------------------------+                    +---------------------------+  |
|  |     Event Dispatcher   | -----------------> |  WASM Guest (Component)   |  |
|  +------------------------+  on-before / after +---------------------------+  |
|                                                                               |
+-------------------------------------------------------------------------------+

```

* **Host Runtime:** `wasmtime` mit aktivierter Component-Model-Unterstützung im Rust-Backend der Desktop-App.
* **Sandbox-Prinzip:** Plugins besitzen standardmäßig keinerlei Systemrechte (kein freier Dateisystem- oder Netzwerkzugriff).
* **Kommunikation:** Sämtliche Interaktionen zwischen Core und Plugin erfolgen strikt typisiert über das Wasm Component Model (`.wit`).

---

## 3. Funktionale Anforderungen (FA)

### FA-1: Plugin-Lifecycle & Manifest-Verwaltung

* **FA-1.1:** Das System lädt `.wasm`-Plugins aus dem lokalen Verzeichnis `/plugins`.
* **FA-1.2:** Jedes Plugin muss ein Manifest (`plugin.toml`) enthalten, das Metadaten und angeforderte Berechtigungen deklariert.
* **FA-1.3:** Der Host validiert die angeforderten Berechtigungen des Manifests vor dem Laden gegen die tatsächlich ausgeführten Host-API-Aufrufe.

### FA-2: Event-Pipeline & CRUD-Hooks

Das System stellt eine zweistufige Pipeline für Datenbank-Ereignisse auf Kern-Entitäten (`customer`, `invoice`, `voucher`, `article`, `task`) bereit:

* **FA-2.1: Pre-Hooks (`on-before-change`)**
* **Ausführung:** Synchron (blocking) innerhalb der aktiven Datenbank-Transaktion.
* **Fähigkeiten:** Kann die Daten-Payload vor dem Schreiben modifizieren (Return `ok(modified_payload)`) oder die Transaktion mit einer Fehlermeldung abbrechen (Return `err(reason)` führt zu atomarem DB-Rollback).


* **FA-2.2: Post-Hooks (`on-after-change`)**
* **Ausführung:** Asynchron (non-blocking) in einem separaten Thread/Task.
* **Fähigkeiten:** Reagiert auf bereits gespeicherte Ereignisse, um Folgeaktionen auszulösen (z. B. Aufgaben-Erstellung, Audit-Logging, Benachrichtigungen).



### FA-3: Host-API (Kontrollierter Datenzugriff)

Plugins erhalten keinen direkten Datenbankzugriff. Der Host stellt für zugelassene Lese- und Schreiboperationen eine API-Schnittstelle bereit:

* `get(entity, id)`: Liest eine spezifische Entität anhand ihrer ID.
* `list(entity, filter_json)`: Gibt eine gefilterte Liste von Entitäten zurück.
* `create(entity, payload_json)`: Erstellt eine neue Entität.
* `update(entity, id, payload_json)`: Aktualisiert eine bestehende Entität.
* `delete(entity, id)`: Löscht eine Entität.

---

## 4. Nicht-funktionale Anforderungen (NFA)

* **NFA-1 (Sicherheit):** Ein Plugin darf niemals unautorisiert auf Daten zugreifen oder Systemressourcen blockieren.
* **NFA-2 (Stabilität):** Abstürze, Panics oder Endlosschleifen innerhalb eines Wasm-Plugins dürfen nicht zum Absturz der RechnungsFee-Hauptanwendung führen (*Graceful Error Handling*).
* **NFA-3 (Performance):** Die Ausführungszeit von synchronen Pre-Hooks darf 50ms pro DB-Transaktion nicht überschreiten. Post-Hooks müssen vollständig im Hintergrund laufen.

---

## 5. Technische Schnittstellendefinition (`rechnungsfee.wit`)

```wit
package rechnungsfee:plugin@0.1.0;

interface types {
    enum entity-type {
        customer,
        invoice,
        voucher,
        article,
        task,
    }

    enum crud-action {
        create,
        read,
        update,
        delete,
    }

    record event-context {
        event-id: string,
        timestamp: string,
        entity: entity-type,
        action: crud-action,
    }

    variant api-error {
        unauthorized(string),
        not-found(string),
        validation-error(string),
        internal-error(string),
    }
}

/// Vom Hauptsystem bereitgestellte Funktionen für Plugins
interface host-api {
    use types.{entity-type, api-error};

    get: func(entity: entity-type, id: string) -> result<string, api-error>;
    list: func(entity: entity-type, filter-json: option<string>) -> result<string, api-error>;
    create: func(entity: entity-type, payload-json: string) -> result<string, api-error>;
    update: func(entity: entity-type, id: string, payload-json: string) -> result<string, api-error>;
    delete: func(entity: entity-type, id: string) -> result<(), api-error>;
}

/// Vom Wasm-Plugin zu implementierende Events
interface event-handler {
    use types.{event-context};

    /// Synchroner Pre-Hook: Modifiziert Daten oder bricht DB-Transaktion ab
    on-before-change: func(ctx: event-context, payload-json: string) -> result<string, string>;

    /// Asynchroner Post-Hook für Folgeaktionen nach erfolgreichem DB-Zugriff
    on-after-change: func(ctx: event-context, payload-json: string);
}

world plugin-world {
    import host-api;
    export event-handler;
}

```

---

## 6. Spezifikation des Manifests (`plugin.toml`)

Jedes Plugin muss eine `plugin.toml` im Root-Verzeichnis mitführen:

```toml
[plugin]
id = "org.rechnungsfee.task-automation"
name = "Task Automation & Audit Logger"
version = "0.1.0"
author = "Stefan Lindecke"
description = "Erstellt automatisch Folge-Aufgaben bei Rechnungs-Events und sichert Logdaten."

[permissions]
# Deklarative Rechtevergabe für die Host-API
entities = [
    { type = "invoice", actions = ["read"] },
    { type = "task", actions = ["create", "read", "update"] }
]

# Abonnierte Event-Hooks
hooks = [
    "invoice:create:before",
    "invoice:create:after"
]

```

---

## 7. Referenz-Szenario: Initiales Task-Automation Plugin

1. **Pre-Hook (`Invoice.CREATE`):** Das Plugin prüft die Rechnungsdaten auf Gültigkeit (z. B. das Vorhandensein von Pflichtfeldern). Ist die Prüfung fehlerhaft, wird der Vorgang mit einer Fehlermeldung abgebrochen.
2. **Post-Hook (`Invoice.CREATE`):** Nach dem erfolgreichen Speichern liest das Plugin die Zahlungsbedingungen der Rechnung aus und ruft die Host-API `create(entity::task, ...)` auf, um automatisch eine Wiedervorlage-Aufgabe zur Fälligkeitsüberwachung in der Datenbank anzulegen.