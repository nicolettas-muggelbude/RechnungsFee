"""Python-Gast für RechnungsFees Wasm-Schnittstelle (kein Backend-Import)."""
from componentize_py_types import Err
from wit_world import exports

from pruefung import pruefe_kunde


class EventHandler(exports.EventHandler):
    def on_before_change(self, ctx, payload_json: str) -> str:
        try:
            return pruefe_kunde(payload_json)
        except ValueError as exc:
            # WIT result<string, string>: Err bricht den Speichervorgang ab.
            raise Err(str(exc))

    def on_after_change(self, ctx, payload_json: str) -> None:
        # Kein Dateisystem/Netzwerk, keine Aufgaben- oder sonstigen Schreibzugriffe.
        pass
