// Test-Plugin fuer den Phase-0-Spike und die Backend-Tests (docs/plan-plugin-system.md).
// Verhalten wird ueber Stichworte im Payload gesteuert:
//   "abbrechen" -> err("Pflichtfeld fehlt")      (Pre-Hook bricht ab)
//   "host-get"  -> ruft host-api.get(invoice,"42") und liefert dessen Ergebnis als ok(...)
//   "endlos"    -> Endlosschleife                  (Timeout/Epoch-Test)
//   "trap"      -> Trap                            (Absturz-Test)
//   "speicher"  -> allokiert immer weiter          (Speicherlimit-Test)
//   "unveraendert" -> ok(<payload>)                (lässt durch, ohne zu ändern)
//   "plugin-notiz" -> ok(<payload> + "notizen":"geprueft durch Plugin")
//                     (hängt das Feld hinten an; bei doppelten Schlüsseln gewinnt in JSON-Parsern
//                     üblicherweise der letzte - reicht für die Ende-zu-Ende-Tests)
//   sonst       -> ok({"geprueft":true,"original":<payload>})
// on-after-change ruft host-api.create(task, payload).
#include "gen/plugin_world.h"
#include <stdlib.h>
#include <string.h>

static int enthaelt(const plugin_world_string_t *s, const char *wort) {
    size_t n = strlen(wort);
    if (s->len < n) return 0;
    for (size_t i = 0; i + n <= s->len; i++) {
        size_t j = 0;
        while (j < n && s->ptr[i + j] == (uint8_t)wort[j]) j++;
        if (j == n) return 1;
    }
    return 0;
}

static void verbinde(plugin_world_string_t *ret, const char *a, const plugin_world_string_t *mitte, const char *b) {
    size_t la = strlen(a), lb = strlen(b);
    size_t n = la + mitte->len + lb;
    uint8_t *p = malloc(n);
    memcpy(p, a, la);
    memcpy(p + la, mitte->ptr, mitte->len);
    memcpy(p + la + mitte->len, b, lb);
    ret->ptr = p;
    ret->len = n;
}

bool exports_rechnungsfee_plugin_event_handler_on_before_change(
    exports_rechnungsfee_plugin_event_handler_event_context_t *ctx,
    plugin_world_string_t *payload, plugin_world_string_t *ret, plugin_world_string_t *err) {
    (void)ctx;
    if (enthaelt(payload, "abbrechen")) {
        plugin_world_string_dup(err, "Pflichtfeld fehlt");
        return false;
    }
    if (enthaelt(payload, "endlos")) {
        volatile int x = 0;
        for (;;) x++;
    }
    if (enthaelt(payload, "trap")) {
        __builtin_trap();
    }
    if (enthaelt(payload, "speicher")) {
        for (;;) { volatile char *p = malloc(1024 * 1024); p[0] = 1; }
    }
    if (enthaelt(payload, "host-get")) {
        plugin_world_string_t id;
        plugin_world_string_dup(&id, "42");
        rechnungsfee_plugin_host_api_api_error_t fehler;
        if (rechnungsfee_plugin_host_api_get(RECHNUNGSFEE_PLUGIN_TYPES_ENTITY_TYPE_INVOICE, &id, ret, &fehler)) {
            return true;
        }
        verbinde(err, "host-api.get fehlgeschlagen: ", &fehler.val.unauthorized, "");
        return false;
    }
    if (enthaelt(payload, "unveraendert")) {
        plugin_world_string_dup_n(ret, (const char *)payload->ptr, payload->len);
        return true;
    }
    if (enthaelt(payload, "plugin-notiz") && payload->len > 1 && payload->ptr[payload->len - 1] == '}') {
        plugin_world_string_t ohne_klammer = { payload->ptr, payload->len - 1 };
        verbinde(ret, "", &ohne_klammer, ",\"notizen\":\"geprueft durch Plugin\"}");
        return true;
    }
    verbinde(ret, "{\"geprueft\":true,\"original\":", payload, "}");
    return true;
}

void exports_rechnungsfee_plugin_event_handler_on_after_change(
    exports_rechnungsfee_plugin_event_handler_event_context_t *ctx, plugin_world_string_t *payload) {
    (void)ctx;
    plugin_world_string_t ergebnis;
    rechnungsfee_plugin_host_api_api_error_t fehler;
    rechnungsfee_plugin_host_api_create(RECHNUNGSFEE_PLUGIN_TYPES_ENTITY_TYPE_TASK, payload, &ergebnis, &fehler);
}
