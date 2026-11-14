"""
Unbehandelte Ausnahmen als lesbare JSON-Antwort statt „Failed to fetch“ (Issue #537).

Ohne diese Schicht beantwortet Starlettes äußerste ServerErrorMiddleware eine nicht abgefangene
Ausnahme mit einer 500 OHNE CORS-Header – der Browser verwirft die Antwort und das Frontend sieht
nur „Failed to fetch“. Uvicorn schreibt den Traceback zudem nur auf stderr (eigene Logger mit
propagate=False), in backend.log stand also nichts.

Muss INNERHALB der CORSMiddleware liegen (vor ihr per add_middleware registriert), damit die
Fehlerantwort die CORS-Header bekommt. Reine ASGI-Middleware, damit Streaming-Antworten
unverändert durchlaufen.
"""
import json
import logging

logger = logging.getLogger("rechnungsfee.fehler")


class FehlerMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        antwort_gestartet = False

        async def send_merken(message):
            nonlocal antwort_gestartet
            if message["type"] == "http.response.start":
                antwort_gestartet = True
            await send(message)

        try:
            await self.app(scope, receive, send_merken)
        except Exception as e:
            logger.exception("Unbehandelter Fehler bei %s %s", scope.get("method"), scope.get("path"))
            if antwort_gestartet:
                raise
            text = str(e).strip()
            detail = (
                f"Interner Fehler im Backend ({type(e).__name__}{': ' + text[:300] if text else ''}). "
                "Details stehen in der Protokolldatei backend.log."
            )
            body = json.dumps({"detail": detail}, ensure_ascii=False).encode("utf-8")
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [
                    (b"content-type", b"application/json; charset=utf-8"),
                    (b"content-length", str(len(body)).encode()),
                ],
            })
            await send({"type": "http.response.body", "body": body})
