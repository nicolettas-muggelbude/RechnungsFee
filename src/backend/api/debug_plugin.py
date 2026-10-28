"""API des immer mitgelieferten Diagnose-Plugins; unabhängig vom Wasm-Hauptschalter."""
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from plugins.debug_plugin import DebugEinstellungen, Kategorie, PLUGIN_ID, PREFIX, instanz

router = APIRouter(prefix=PREFIX, tags=["Debug-Plugin"])


class UiEreignis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kategorie: Literal["ui", "navigation", "fehler"]
    aktion: Literal["klick", "aenderung", "absenden", "seitenwechsel", "javascript", "promise"]
    # Nur statische Seiten-/Elementkennungen; niemals Texte, Feldwerte oder Fehlertexte.
    seite: str = Field(max_length=80, pattern=r"^/[a-z-]*$")
    element: Literal["button", "a", "input", "select", "textarea", "form", "sonstiges"] | None = None
    element_id: str | None = Field(default=None, max_length=80, pattern=r"^[a-zA-Z0-9_.:-]+$")


class UiStapel(BaseModel):
    ereignisse: list[UiEreignis] = Field(max_length=50)


@router.get("/einstellungen")
def einstellungen():
    p = instanz()
    return {**p.einstellungen.model_dump(), "plugin_id": PLUGIN_ID, "mitgeliefert": True,
            "logdatei": str(p.pfad), "max_bytes": p.MAX_BYTES, "sicherungen": p.BACKUPS,
            "schreibfehler": p.schreibfehler}


@router.put("/einstellungen")
def konfigurieren(daten: DebugEinstellungen):
    try:
        instanz().konfigurieren(daten)
    except OSError:
        raise HTTPException(500, "Debug-Einstellungen konnten nicht gespeichert werden.")
    return einstellungen()


@router.post("/ereignisse", status_code=204)
def ui_ereignisse(daten: UiStapel):
    for e in daten.ereignisse:
        if e.kategorie == "fehler":
            instanz().schreiben("fehler", quelle="frontend", typ=e.aktion)
        else:
            instanz().schreiben(e.kategorie, **e.model_dump(exclude={"kategorie"}, exclude_none=True))


@router.get("/protokoll")
def protokoll(limit: int = Query(200, ge=1, le=500), kategorie: Kategorie | None = None):
    return instanz().lesen(limit, kategorie)


@router.get("/download")
def download():
    p = instanz()
    with p.lock:
        # Archivdateien mit exportieren, in zeitlicher Reihenfolge; maximal 4 × 2 MB.
        daten = b"".join(datei.read_bytes() for datei in reversed(p.dateien()) if datei.exists())
    return Response(daten, media_type="application/x-ndjson",
                    headers={"Content-Disposition": 'attachment; filename="rechnungsfee-debug.jsonl"'})
