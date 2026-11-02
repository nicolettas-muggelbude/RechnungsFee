"""
Issue #476: Dateiname als letztes URL-Segment hinter einem PDF-Endpunkt.

Der eingebaute PDF-Viewer von WebKitGTK (Tauri unter Linux) ignoriert beim Speichern den
Dateinamen aus Content-Disposition und nimmt den letzten Teil der URL - bei
`/rechnungen/12/pdf` wurde daraus „document.pdf“. Das Frontend hängt deshalb den
gewünschten Namen hinter einem Marker an (`/rechnungen/12/pdf/_datei/Rechnung_RE-260035.pdf`,
`mitDateiname()` in client.ts), und diese Middleware entfernt ihn vor dem Routing wieder.
So gilt es für jeden Endpunkt, ohne Routen doppelt anzulegen.
"""
import re

_DATEI_MARKER_RE = re.compile(r"^(.+)/_datei/[^/]+$")


class PdfDateinameMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            m = _DATEI_MARKER_RE.match(scope["path"])
            if m:
                pfad = m.group(1)
                scope = dict(scope, path=pfad, raw_path=pfad.encode("utf-8"))
        await self.app(scope, receive, send)
