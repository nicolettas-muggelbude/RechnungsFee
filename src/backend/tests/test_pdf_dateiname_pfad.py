"""
Issue #476: angehängter Dateiname hinter ".../pdf" (für den PDF-Viewer von WebKitGTK/Linux,
der beim Speichern den Namen aus der URL nimmt) wird vor dem Routing entfernt.
"""
import asyncio

import pytest

from main import app
from utils.pdf_dateiname_pfad import PdfDateinameMiddleware


def _pfad_nach_middleware(pfad: str) -> tuple[str, bytes]:
    gesehen = {}

    async def innen(scope, receive, send):
        gesehen.update(scope)

    scope = {"type": "http", "path": pfad, "raw_path": pfad.encode(), "query_string": b"vorlage=1"}
    asyncio.run(PdfDateinameMiddleware(innen)(scope, None, None))
    assert gesehen["query_string"] == b"vorlage=1"  # Query bleibt erhalten
    return gesehen["path"], gesehen["raw_path"]


@pytest.mark.parametrize("pfad, erwartet", [
    ("/api/rechnungen/12/pdf", "/api/rechnungen/12/pdf"),
    ("/api/rechnungen/12/pdf/_datei/Rechnung_RE-260035.pdf", "/api/rechnungen/12/pdf"),
    ("/api/rechnungen/7/pdf/_datei/Angebot_Müller GmbH.pdf", "/api/rechnungen/7/pdf"),
    ("/api/euer/pdf/_datei/EÜR_2026.pdf", "/api/euer/pdf"),
    ("/api/journal/export/_datei/Journal_2026-10.pdf", "/api/journal/export"),
    ("/api/kunden/3/dsgvo-export-pdf/_datei/dsgvo.pdf", "/api/kunden/3/dsgvo-export-pdf"),
    ("/api/rechnungen/12/pdf/irgendwas.pdf", "/api/rechnungen/12/pdf/irgendwas.pdf"),
    ("/api/rechnungen/12/pdf-ansehen", "/api/rechnungen/12/pdf-ansehen"),
])
def test_dateiname_wird_entfernt(pfad, erwartet):
    path, raw = _pfad_nach_middleware(pfad)
    assert path == erwartet
    assert raw == erwartet.encode()


def test_middleware_in_app_eingebunden():
    assert any(m.cls is PdfDateinameMiddleware for m in app.user_middleware)
