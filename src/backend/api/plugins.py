"""
Plugin-Verwaltung für die Einstellungsseite (docs/plan-plugin-system.md, Phase 2).

Zeigt alle gefundenen Plugins (auch fehlerhafte), schaltet sie einzeln an/aus, bestätigt
Rechte, installiert/entfernt .rfplugin-Pakete. Ausgeführt werden Plugins hier noch nicht -
das kommt mit der Laufzeit (Phase 3).
"""
from __future__ import annotations

import json
import platform
import subprocess
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import PluginProtokoll
from plugins import laufzeit, registry
from plugins.manifest import UNTERSTUETZTE_API_VERSIONEN, hook_klartext, rechte_klartext
from plugins.registry import PluginFehler, PluginZustand

router = APIRouter(prefix="/api/plugins", tags=["Plugins"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PluginHook(BaseModel):
    hook: str
    beschreibung: str
    abgeschaltet: bool
    vor_dem_speichern: bool


class PluginRechte(BaseModel):
    entities: dict[str, list[str]]
    hooks: list[str]


class PluginEintrag(BaseModel):
    plugin_id: str
    ordner: str | None
    status: str
    laeuft: bool
    name: str
    version: str | None
    author: str | None
    description: str | None
    homepage: str | None
    api_version: str | None
    wasm_sha256: str | None
    wasm_bytes: int | None
    rechte: PluginRechte | None
    rechte_klartext: list[str]
    hooks: list[PluginHook]
    # Bei Status rechte_erweitert: was gegenüber der letzten Bestätigung neu hinzukommt
    neue_rechte_klartext: list[str]
    neue_hooks_klartext: list[str]
    fehler: list[str]
    warnungen: list[str]
    aktiviert_am: datetime | None
    fehler_in_folge: int
    letzter_fehler: str | None
    letzter_fehler_am: datetime | None


class PluginUebersicht(BaseModel):
    plugins_aktiv: bool
    abgesicherter_modus: bool
    verzeichnis: str
    api_versionen: list[str]
    plugins: list[PluginEintrag]


class GlobalRequest(BaseModel):
    plugins_aktiv: bool


class AktivierenRequest(BaseModel):
    wasm_sha256: str
    rechte: PluginRechte


class HooksRequest(BaseModel):
    abgeschaltet: list[str]


class TestlaufRequest(BaseModel):
    hook: str
    payload_json: str = "{}"


class TestlaufAntwort(BaseModel):
    ergebnis: str            # ok | geaendert | abgebrochen | fehler | timeout
    payload_json: str | None
    meldung: str | None
    dauer_ms: float


class ProtokollEintrag(BaseModel):
    id: int
    hook: str
    entitaet: str | None
    datensatz_id: int | None
    ergebnis: str
    dauer_ms: int | None
    meldung: str | None
    erstellt_am: datetime


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _fehler(e: PluginFehler) -> HTTPException:
    detail = e.meldung
    if e.details:
        detail += ": " + " · ".join(e.details)
    return HTTPException(status_code=e.status_code, detail=detail)


def _eintrag(z: PluginZustand) -> PluginEintrag:
    g = z.gefunden
    m = g.manifest if g else None
    zeile = z.status_zeile
    abgeschaltet = set(registry.deaktivierte_hooks(zeile))

    neue_rechte: list[str] = []
    neue_hooks: list[str] = []
    if m is not None and z.status == registry.RECHTE_ERWEITERT:
        alt = registry.genehmigte_rechte(zeile) or {}
        alt_e = {e: set(a) for e, a in (alt.get("entities") or {}).items()}
        differenz = {
            e: tuple(a for a in aktionen if a not in alt_e.get(e, set()))
            for e, aktionen in m.rechte.items()
        }
        neue_rechte = rechte_klartext({e: a for e, a in differenz.items() if a})
        neue_hooks = [hook_klartext(h) for h in m.hooks if h not in set(alt.get("hooks") or [])]

    return PluginEintrag(
        plugin_id=z.plugin_id,
        ordner=g.verzeichnis.name if g else None,
        status=z.status,
        laeuft=z.laeuft,
        name=m.name if m else (g.verzeichnis.name if g else z.plugin_id),
        version=m.version if m else None,
        author=m.author if m else None,
        description=m.description if m else None,
        homepage=m.homepage if m else None,
        api_version=m.api_version if m else None,
        wasm_sha256=g.wasm_sha256 if g else None,
        wasm_bytes=g.wasm_bytes if g else None,
        rechte=PluginRechte(**m.rechte_snapshot()) if m else None,
        rechte_klartext=rechte_klartext(m.rechte) if m else [],
        hooks=[
            PluginHook(
                hook=h,
                beschreibung=hook_klartext(h),
                abgeschaltet=h in abgeschaltet,
                vor_dem_speichern=h.endswith(":before"),
            )
            for h in (m.hooks if m else ())
        ],
        neue_rechte_klartext=neue_rechte,
        neue_hooks_klartext=neue_hooks,
        fehler=g.fehler if g else ["Die Plugin-Dateien wurden aus dem Plugin-Ordner entfernt."],
        warnungen=g.warnungen if g else [],
        aktiviert_am=zeile.aktiviert_am if zeile else None,
        fehler_in_folge=zeile.fehler_in_folge if zeile else 0,
        letzter_fehler=zeile.letzter_fehler if zeile else None,
        letzter_fehler_am=zeile.letzter_fehler_am if zeile else None,
    )


def _einzeln(db: Session, plugin_id: str) -> PluginEintrag:
    try:
        return _eintrag(registry.zustand(db, plugin_id))
    except PluginFehler as e:
        raise _fehler(e)


# ---------------------------------------------------------------------------
# Endpunkte
# ---------------------------------------------------------------------------

@router.get("", response_model=PluginUebersicht)
def liste(db: Session = Depends(get_db)):
    zustaende = registry.alle_zustaende(db)
    db.commit()   # legt ggf. den Singleton plugin_einstellungen an
    return PluginUebersicht(
        plugins_aktiv=registry.einstellungen(db).plugins_aktiv,
        abgesicherter_modus=registry.abgesicherter_modus(),
        verzeichnis=str(registry.plugin_verzeichnis()),
        api_versionen=list(UNTERSTUETZTE_API_VERSIONEN),
        plugins=[_eintrag(z) for z in zustaende],
    )


@router.put("/einstellungen", response_model=PluginUebersicht)
def global_setzen(data: GlobalRequest, db: Session = Depends(get_db)):
    registry.global_setzen(db, data.plugins_aktiv)
    return liste(db)


@router.post("/{plugin_id}/aktivieren", response_model=PluginEintrag)
def aktivieren(plugin_id: str, data: AktivierenRequest, db: Session = Depends(get_db)):
    try:
        return _eintrag(registry.aktivieren(db, plugin_id, data.wasm_sha256, data.rechte.model_dump()))
    except PluginFehler as e:
        raise _fehler(e)


@router.post("/{plugin_id}/deaktivieren", response_model=PluginEintrag)
def deaktivieren(plugin_id: str, db: Session = Depends(get_db)):
    try:
        return _eintrag(registry.deaktivieren(db, plugin_id))
    except PluginFehler as e:
        raise _fehler(e)


@router.put("/{plugin_id}/hooks", response_model=PluginEintrag)
def hooks_setzen(plugin_id: str, data: HooksRequest, db: Session = Depends(get_db)):
    try:
        return _eintrag(registry.hooks_setzen(db, plugin_id, data.abgeschaltet))
    except PluginFehler as e:
        raise _fehler(e)


@router.post("/{plugin_id}/testen", response_model=TestlaufAntwort)
def testen(plugin_id: str, data: TestlaufRequest, db: Session = Depends(get_db)):
    """Ruft einen Hook des Plugins zur Probe mit einem eigenen Payload auf - auch wenn es nicht
    aktiv ist. Ohne Zugriff auf echte Daten, ohne Einfluss auf den Fehlerzähler."""
    try:
        z = registry.zustand(db, plugin_id)
    except PluginFehler as e:
        raise _fehler(e)
    if z.gefunden is None or z.gefunden.manifest is None or z.gefunden.fehler:
        raise HTTPException(status_code=422, detail="Fehlerhafte Plugins können nicht getestet werden")
    if data.hook not in z.gefunden.manifest.hooks:
        raise HTTPException(status_code=422, detail=f"Das Plugin abonniert den Hook „{data.hook}“ nicht")
    try:
        objekt = json.loads(data.payload_json)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Der Test-Payload ist kein gültiges JSON: {e.msg} (Zeile {e.lineno})")
    if not isinstance(objekt, dict):
        raise HTTPException(status_code=422, detail="Der Test-Payload muss ein JSON-Objekt sein ({ ... })")
    e = laufzeit.testlauf(z.gefunden, data.hook, json.dumps(objekt, ensure_ascii=False))
    return TestlaufAntwort(ergebnis=e.ergebnis, payload_json=e.payload_json, meldung=e.meldung,
                           dauer_ms=round(e.dauer_ms, 2))


@router.get("/{plugin_id}/protokoll", response_model=list[ProtokollEintrag])
def protokoll(
    plugin_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    zeilen = (
        db.query(PluginProtokoll)
        .filter(PluginProtokoll.plugin_id == plugin_id)
        .order_by(PluginProtokoll.id.desc())
        .offset(offset).limit(limit).all()
    )
    return [
        ProtokollEintrag(
            id=z.id, hook=z.hook, entitaet=z.entitaet, datensatz_id=z.datensatz_id, ergebnis=z.ergebnis,
            dauer_ms=z.dauer_ms, meldung=z.meldung, erstellt_am=z.erstellt_am,
        )
        for z in zeilen
    ]


@router.post("/installieren", response_model=PluginEintrag, status_code=201)
async def installieren(datei: UploadFile = File(...), db: Session = Depends(get_db)):
    daten = await datei.read(registry.MAX_PAKET_BYTES + 1)
    try:
        g = registry.installiere_paket(daten)
    except PluginFehler as e:
        raise _fehler(e)
    registry.protokolliere(db, g.plugin_id, "verwaltung", "installiert",
                           f"Version {g.manifest.version if g.manifest else '?'}, SHA-256 {g.wasm_sha256}")
    db.commit()
    return _einzeln(db, g.plugin_id)


@router.delete("/{plugin_id}", status_code=204)
def entfernen(plugin_id: str, db: Session = Depends(get_db)):
    try:
        registry.entfernen(db, plugin_id)
    except PluginFehler as e:
        raise _fehler(e)


@router.post("/ordner-oeffnen", status_code=204)
def ordner_oeffnen():
    """Öffnet den Plugin-Ordner im Dateimanager. Backend und Oberfläche laufen auf demselben
    Rechner (Desktop-App), daher genügt ein Aufruf des System-Openers von hier aus."""
    ordner = registry.plugin_verzeichnis()
    ordner.mkdir(parents=True, exist_ok=True)
    system = platform.system()
    befehl = {"Windows": ["explorer", str(ordner)], "Darwin": ["open", str(ordner)]}.get(system, ["xdg-open", str(ordner)])
    try:
        subprocess.Popen(befehl, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Der Ordner konnte nicht geöffnet werden: {e}")
