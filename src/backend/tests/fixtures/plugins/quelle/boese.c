// Test-Fixture: Plugin, das eine nicht erlaubte Schnittstelle (Netzwerk) importiert.
#include "genb/boese_world.h"
bool exports_rechnungsfee_plugin_event_handler_on_before_change(
    exports_rechnungsfee_plugin_event_handler_event_context_t *ctx,
    boese_world_string_t *payload, boese_world_string_t *ret, boese_world_string_t *err) {
    (void)ctx; (void)err;
    rechnungsfee_plugin_netz_senden(payload, ret);
    return true;
}
void exports_rechnungsfee_plugin_event_handler_on_after_change(
    exports_rechnungsfee_plugin_event_handler_event_context_t *ctx, boese_world_string_t *payload) {
    (void)ctx; (void)payload;
}
