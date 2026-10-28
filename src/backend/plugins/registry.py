"""
Plugin-Registry: findet Plugins im Plugin-Ordner, verknüpft sie mit dem pro Profil gespeicherten
Status und setzt Nutzerentscheidungen (aktivieren, deaktivieren, Hooks abschalten) um.

Ablaufplan: docs/plan-plugin-system.md, Phase 1 + 2.

Ordnerstruktur (global, für alle Profile gleich):

    BASE_DIR/plugins/<beliebiger-ordner>/plugin.toml
                                        /plugin.wasm

Grundsätze:
- Ein neu gefundenes Plugin läuft nie, bevor der Nutzer seine Rechte bestätigt hat (Status „neu“).
- Bestätigt wird ein konkreter Stand: SHA-256 der plugin.wasm + Rechte-Snapshot. Fordert ein
  Update mehr Rechte an, steht das Plugin auf „rechte_erweitert“ und läuft erst nach erneuter
  Bestätigung. Ein Update ohne neue Rechte läuft weiter („aktualisiert“, Hinweis in der UI).
- Ungültige Plugins werden mit Grund angezeigt statt verschwiegen.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import shutil
import threading
import tomllib
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath

from sqlalchemy.orm import Session

from database.connection import BASE_DIR
from database.models import PluginEinstellungen, PluginProtokoll, PluginStatus

from .manifest import (
    MANIFEST_NAME, WASM_NAME, PluginManifest, parse_manifest, pruefe_manifest, rechte_erweitert,
)
from . import wasm_pruefung


def plugin_verzeichnis() -> Path:
    """Plugin-Ordner. RECHNUNGSFEE_PLUGIN_DIR überschreibt ihn (Tests, Entwicklung)."""
    ueberschrieben = os.environ.get("RECHNUNGSFEE_PLUGIN_DIR")
    return Path(ueberschrieben) if ueberschrieben else BASE_DIR / "plugins"


def abgesicherter_modus() -> bool:
    """RECHNUNGSFEE_PLUGINS=0 startet ohne Plugins - Notbremse, falls ein Plugin die App
    unbedienbar macht. Plugins bleiben sichtbar und verwaltbar, laufen aber nicht."""
    return os.environ.get("RECHNUNGSFEE_PLUGINS", "").strip() in ("0", "false", "aus", "off")


MAX_WASM_BYTES = 20 * 1024 * 1024
MAX_PAKET_BYTES = 25 * 1024 * 1024
# Dateien, die ein .rfplugin-Paket enthalten darf (alles andere wird abgelehnt)
ERLAUBTE_PAKETDATEIEN = {MANIFEST_NAME, WASM_NAME, "README.md", "LICENSE", "LICENSE.txt", "CHANGELOG.md"}

# Statuswerte (siehe Tabelle in docs/plan-plugin-system.md, Phase 1)
NEU = "neu"
AKTIV = "aktiv"
DEAKTIVIERT = "deaktiviert"
AKTUALISIERT = "aktualisiert"
RECHTE_ERWEITERT = "rechte_erweitert"
FEHLERHAFT = "fehlerhaft"
AUTOMATISCH_DEAKTIVIERT = "automatisch_deaktiviert"
FEHLT = "fehlt"   # Status-Eintrag vorhanden, Plugin-Dateien aber nicht mehr im Ordner

LAUFENDE_STATUS = (AKTIV, AKTUALISIERT)

_sperre = threading.Lock()

# Wird bei jeder Statusänderung erhöht (aktivieren, deaktivieren, Hooks, Hauptschalter, Installation,
# Entfernen, automatische Abschaltung) - laufende_plugins() verwirft dann seinen Cache.
_generation = 0
_generation_sperre = threading.Lock()


def status_geaendert() -> None:
    global _generation
    with _generation_sperre:
        _generation += 1


class PluginFehler(Exception):
    """Fachlicher Fehler bei einer Plugin-Aktion - Text ist für die Anzeige gedacht."""

    def __init__(self, meldung: str, details: list[str] | None = None, status_code: int = 400):
        super().__init__(meldung)
        self.meldung = meldung
        self.details = details or []
        self.status_code = status_code


@dataclass
class GefundenesPlugin:
    plugin_id: str
    verzeichnis: Path
    manifest: PluginManifest | None
    fehler: list[str] = field(default_factory=list)
    warnungen: list[str] = field(default_factory=list)
    wasm_sha256: str | None = None
    wasm_bytes: int | None = None


@dataclass
class PluginZustand:
    """Gefundenes Plugin + gespeicherter Status = das, was die Einstellungsseite anzeigt."""
    plugin_id: str
    gefunden: GefundenesPlugin | None
    status_zeile: PluginStatus | None
    status: str
    laeuft: bool


# ---------------------------------------------------------------------------
# Ordner scannen
# ---------------------------------------------------------------------------

def _sha256_datei(pfad: Path) -> str:
    h = hashlib.sha256()
    with pfad.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _datei_signatur(pfad: Path) -> tuple[int, int] | None:
    try:
        st = pfad.stat()
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


# Ordner -> (Signatur von plugin.toml + plugin.wasm, Ergebnis). Hook-Aufrufe lesen die Registry bei
# jedem Speichervorgang - ohne Cache würde jedes Mal die plugin.wasm gehasht und geprüft.
_ordner_cache: dict[Path, tuple[tuple, "GefundenesPlugin"]] = {}
_ordner_cache_sperre = threading.Lock()


def _lies_plugin_ordner(ordner: Path) -> GefundenesPlugin:
    signatur = (_datei_signatur(ordner / MANIFEST_NAME), _datei_signatur(ordner / WASM_NAME))
    with _ordner_cache_sperre:
        treffer = _ordner_cache.get(ordner)
    if treffer and treffer[0] == signatur:
        return copy.deepcopy(treffer[1])
    g = _lies_plugin_ordner_ungecacht(ordner)
    with _ordner_cache_sperre:
        _ordner_cache[ordner] = (signatur, copy.deepcopy(g))
    return g


def _lies_plugin_ordner_ungecacht(ordner: Path) -> GefundenesPlugin:
    ergebnis = parse_manifest(ordner / MANIFEST_NAME)
    g = GefundenesPlugin(
        plugin_id=ergebnis.manifest.id if ergebnis.manifest else ordner.name,
        verzeichnis=ordner,
        manifest=ergebnis.manifest,
        fehler=list(ergebnis.fehler),
        warnungen=list(ergebnis.warnungen),
    )
    wasm = ordner / WASM_NAME
    if not wasm.is_file():
        g.fehler.append(f"{WASM_NAME} fehlt")
        return g
    g.wasm_bytes = wasm.stat().st_size
    if g.wasm_bytes > MAX_WASM_BYTES:
        g.fehler.append(f"{WASM_NAME} ist größer als {MAX_WASM_BYTES // (1024 * 1024)} MB")
        return g
    g.wasm_sha256 = _sha256_datei(wasm)
    g.fehler.extend(wasm_pruefung.pruefe_component(wasm, g.wasm_sha256))
    return g


def plugins_scannen(verzeichnis: Path | None = None) -> list[GefundenesPlugin]:
    """Alle Unterordner mit plugin.toml oder plugin.wasm. Ordner, die mit „.“ beginnen, sind
    interne Arbeitsordner (Installation) und werden übersprungen."""
    basis = verzeichnis or plugin_verzeichnis()
    if not basis.is_dir():
        return []
    gefunden: list[GefundenesPlugin] = []
    for ordner in sorted(basis.iterdir(), key=lambda p: p.name.lower()):
        if not ordner.is_dir() or ordner.name.startswith("."):
            continue
        if not (ordner / MANIFEST_NAME).exists() and not (ordner / WASM_NAME).exists():
            continue
        gefunden.append(_lies_plugin_ordner(ordner))

    # Doppelte IDs: das erste (alphabetisch nach Ordnername) gewinnt, alle weiteren sind fehlerhaft -
    # sonst wäre unklar, welche plugin.wasm zum bestätigten Status gehört.
    gesehen: dict[str, Path] = {}
    for g in gefunden:
        if g.manifest is None:
            continue
        if g.plugin_id in gesehen:
            g.fehler.append(
                f"Die Plugin-ID ist bereits im Ordner „{gesehen[g.plugin_id].name}“ vorhanden"
            )
            g.manifest = None
            g.plugin_id = f"{g.plugin_id}#{g.verzeichnis.name}"
        else:
            gesehen[g.plugin_id] = g.verzeichnis
    return gefunden


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def einstellungen(db: Session) -> PluginEinstellungen:
    e = db.get(PluginEinstellungen, 1)
    if e is None:
        e = PluginEinstellungen(id=1, plugins_aktiv=False)
        db.add(e)
        db.flush()
    return e


def genehmigte_rechte(zeile: PluginStatus | None) -> dict | None:
    if zeile is None or not zeile.genehmigte_rechte_json:
        return None
    try:
        return json.loads(zeile.genehmigte_rechte_json)
    except json.JSONDecodeError:
        return None


def deaktivierte_hooks(zeile: PluginStatus | None) -> list[str]:
    if zeile is None or not zeile.deaktivierte_hooks_json:
        return []
    try:
        werte = json.loads(zeile.deaktivierte_hooks_json)
        return [w for w in werte if isinstance(w, str)]
    except json.JSONDecodeError:
        return []


def ermittle_status(g: GefundenesPlugin | None, zeile: PluginStatus | None) -> str:
    if g is None:
        return FEHLT
    if g.manifest is None or g.fehler:
        return FEHLERHAFT
    if zeile is None:
        return NEU
    if zeile.automatisch_deaktiviert:
        return AUTOMATISCH_DEAKTIVIERT
    if not zeile.aktiv:
        return DEAKTIVIERT
    if rechte_erweitert(genehmigte_rechte(zeile), g.manifest.rechte_snapshot()):
        return RECHTE_ERWEITERT
    if zeile.wasm_sha256 != g.wasm_sha256:
        return AKTUALISIERT
    return AKTIV


def alle_zustaende(db: Session, verzeichnis: Path | None = None) -> list[PluginZustand]:
    # Nur lesen (kein einstellungen(): das legt den Singleton notfalls per Flush an). Diese Funktion
    # läuft auch über laufende_plugins() mit einer zweiten Verbindung, während der Aufrufer eine
    # Schreib-Transaktion offen hat - ein Schreibversuch hier würde auf dessen Lock warten.
    e = db.get(PluginEinstellungen, 1)
    global_aktiv = bool(e and e.plugins_aktiv) and not abgesicherter_modus()
    zeilen = {z.plugin_id: z for z in db.query(PluginStatus).all()}
    zustaende: list[PluginZustand] = []
    for g in plugins_scannen(verzeichnis):
        # Auch fehlerhafte Plugins übernehmen ihre Zeile (ID = Ordnername), damit ein vorher
        # aktives Plugin mit kaputtem Update nicht doppelt („fehlt“ + „fehlerhaft“) erscheint.
        zeile = zeilen.pop(g.plugin_id, None)
        status = ermittle_status(g, zeile)
        zustaende.append(PluginZustand(g.plugin_id, g, zeile, status, global_aktiv and status in LAUFENDE_STATUS))
    for plugin_id, zeile in sorted(zeilen.items()):
        zustaende.append(PluginZustand(plugin_id, None, zeile, FEHLT, False))
    return zustaende


def zustand(db: Session, plugin_id: str) -> PluginZustand:
    for z in alle_zustaende(db):
        if z.plugin_id == plugin_id:
            return z
    raise PluginFehler("Plugin nicht gefunden", status_code=404)


def ausfuehrbare_plugins(db: Session) -> list[tuple[GefundenesPlugin, PluginStatus]]:
    """Plugins, die laufen dürfen - Einstiegspunkt für die Laufzeit (Phase 3)."""
    return [(z.gefunden, z.status_zeile) for z in alle_zustaende(db) if z.laeuft]


# ---------------------------------------------------------------------------
# Aktionen
# ---------------------------------------------------------------------------

def protokolliere(db: Session, plugin_id: str, hook: str, ergebnis: str, meldung: str | None = None, **kw) -> None:
    db.add(PluginProtokoll(plugin_id=plugin_id, hook=hook, ergebnis=ergebnis, meldung=meldung, **kw))


def aktivieren(db: Session, plugin_id: str, wasm_sha256: str, rechte: dict) -> PluginZustand:
    """Aktiviert bzw. bestätigt ein Plugin. `wasm_sha256` und `rechte` sind der Stand, den der
    Nutzer im Dialog gesehen hat - weicht der aktuelle Stand davon ab (Datei zwischendurch
    ausgetauscht), wird abgelehnt statt etwas anderes freizugeben als bestätigt wurde."""
    z = zustand(db, plugin_id)
    if z.status == FEHLT:
        raise PluginFehler("Die Plugin-Dateien sind nicht mehr vorhanden", status_code=404)
    if z.status == FEHLERHAFT:
        raise PluginFehler("Das Plugin ist fehlerhaft und kann nicht aktiviert werden", z.gefunden.fehler, 422)
    g = z.gefunden
    aktuell = g.manifest.rechte_snapshot()
    if wasm_sha256 != g.wasm_sha256 or _normalisiere(rechte) != aktuell:
        raise PluginFehler(
            "Das Plugin hat sich geändert, seit die Seite geladen wurde. Bitte prüfe die Rechte erneut.",
            status_code=409,
        )
    zeile = z.status_zeile or PluginStatus(plugin_id=plugin_id)
    zeile.aktiv = True
    zeile.automatisch_deaktiviert = False
    zeile.fehler_in_folge = 0
    zeile.wasm_sha256 = g.wasm_sha256
    zeile.genehmigte_rechte_json = json.dumps(aktuell, ensure_ascii=False)
    zeile.aktiviert_am = datetime.now()
    # Abgeschaltete Hooks, die es im Plugin nicht mehr gibt, nicht mitschleppen
    zeile.deaktivierte_hooks_json = json.dumps([h for h in deaktivierte_hooks(zeile) if h in g.manifest.hooks])
    db.add(zeile)
    protokolliere(db, plugin_id, "verwaltung", "aktiviert",
                  f"Version {g.manifest.version}, SHA-256 {g.wasm_sha256}, Rechte {json.dumps(aktuell, ensure_ascii=False)}")
    db.commit()
    status_geaendert()
    return zustand(db, plugin_id)


def deaktivieren(db: Session, plugin_id: str) -> PluginZustand:
    z = zustand(db, plugin_id)
    zeile = z.status_zeile
    if zeile is None:
        # „neu“ ist bereits aus - trotzdem Zeile anlegen, damit das Plugin als bewusst
        # deaktiviert gilt und nicht dauerhaft als „neu“ markiert bleibt.
        zeile = PluginStatus(plugin_id=plugin_id)
        db.add(zeile)
    zeile.aktiv = False
    zeile.automatisch_deaktiviert = False
    protokolliere(db, plugin_id, "verwaltung", "deaktiviert")
    db.commit()
    status_geaendert()
    return zustand(db, plugin_id)


def hooks_setzen(db: Session, plugin_id: str, abgeschaltet: list[str]) -> PluginZustand:
    z = zustand(db, plugin_id)
    if z.gefunden is None or z.gefunden.manifest is None:
        raise PluginFehler("Für dieses Plugin können keine Hooks eingestellt werden", status_code=422)
    unbekannt = sorted(set(abgeschaltet) - set(z.gefunden.manifest.hooks))
    if unbekannt:
        raise PluginFehler(f"Unbekannte Hooks: {', '.join(unbekannt)}", status_code=422)
    zeile = z.status_zeile
    if zeile is None:
        zeile = PluginStatus(plugin_id=plugin_id, aktiv=False)
        db.add(zeile)
    zeile.deaktivierte_hooks_json = json.dumps(sorted(set(abgeschaltet)))
    protokolliere(db, plugin_id, "verwaltung", "hooks", "Abgeschaltet: " + (", ".join(sorted(set(abgeschaltet))) or "keine"))
    db.commit()
    status_geaendert()
    return zustand(db, plugin_id)


def global_setzen(db: Session, aktiv: bool) -> None:
    einstellungen(db).plugins_aktiv = aktiv
    db.commit()
    status_geaendert()


def entfernen(db: Session, plugin_id: str) -> None:
    """Löscht den Plugin-Ordner und den Status-Eintrag. Das Protokoll bleibt erhalten
    (Nachvollziehbarkeit). Eine spätere Neuinstallation gilt wieder als „neu“."""
    with _sperre:
        z = zustand(db, plugin_id)
        if z.gefunden is not None:
            ordner = z.gefunden.verzeichnis.resolve()
            basis = plugin_verzeichnis().resolve()
            if ordner.parent != basis:
                raise PluginFehler("Plugin-Ordner liegt außerhalb des Plugin-Verzeichnisses", status_code=400)
            shutil.rmtree(ordner)
        if z.status_zeile is not None:
            db.delete(z.status_zeile)
        protokolliere(db, plugin_id, "verwaltung", "entfernt")
        db.commit()
        status_geaendert()


def _normalisiere(rechte: dict) -> dict:
    entities = rechte.get("entities") or {}
    return {
        "entities": {e: list(a) for e, a in sorted(entities.items())},
        "hooks": list(rechte.get("hooks") or []),
    }


# ---------------------------------------------------------------------------
# Installation aus .rfplugin (ZIP)
# ---------------------------------------------------------------------------

def installiere_paket(daten: bytes) -> GefundenesPlugin:
    """Entpackt ein .rfplugin-Paket (ZIP mit plugin.toml + plugin.wasm, optional in genau einem
    Unterordner) nach BASE_DIR/plugins/<plugin-id>/. Ersetzt ein vorhandenes Plugin mit derselben
    ID (Update) - ob es danach weiterläuft, entscheidet ermittle_status()."""
    if len(daten) > MAX_PAKET_BYTES:
        raise PluginFehler(f"Das Paket ist größer als {MAX_PAKET_BYTES // (1024 * 1024)} MB", status_code=413)
    if daten.startswith(b"\0asm"):
        raise PluginFehler(
            "Du hast eine einzelne Wasm-Datei ausgewählt. Bitte wähle das .rfplugin-Paket "
            "(z. B. python-kundenpruefung.rfplugin), das plugin.toml und plugin.wasm enthält. "
            "Nur die Dateiendung zu ändern reicht nicht.",
            status_code=422,
        )
    try:
        zf = zipfile.ZipFile(io.BytesIO(daten))
    except zipfile.BadZipFile:
        raise PluginFehler("Die Datei ist kein gültiges Plugin-Paket (.rfplugin/.zip)", status_code=422)

    dateien = _paket_dateien(zf)
    if MANIFEST_NAME not in dateien or WASM_NAME not in dateien:
        raise PluginFehler(f"Das Paket muss {MANIFEST_NAME} und {WASM_NAME} enthalten", status_code=422)

    try:
        roh = tomllib.loads(dateien[MANIFEST_NAME].decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as e:
        raise PluginFehler(f"{MANIFEST_NAME} ist ungültig: {e}", status_code=422)
    ergebnis = pruefe_manifest(roh)
    if ergebnis.manifest is None:
        raise PluginFehler("Das Manifest des Plugins ist ungültig", ergebnis.fehler, 422)
    if len(dateien[WASM_NAME]) > MAX_WASM_BYTES:
        raise PluginFehler(f"{WASM_NAME} ist größer als {MAX_WASM_BYTES // (1024 * 1024)} MB", status_code=413)
    wasm_fehler = wasm_pruefung.pruefe_component_bytes(dateien[WASM_NAME])
    if wasm_fehler:
        raise PluginFehler("Die Plugin-Datei ist nicht mit RechnungsFee kompatibel", wasm_fehler, 422)

    plugin_id = ergebnis.manifest.id
    basis = plugin_verzeichnis()
    with _sperre:
        basis.mkdir(parents=True, exist_ok=True)
        ziel = basis / plugin_id
        for g in plugins_scannen(basis):
            if g.manifest and g.plugin_id == plugin_id and g.verzeichnis.name != plugin_id:
                raise PluginFehler(
                    f"Ein Plugin mit dieser ID liegt bereits im Ordner „{g.verzeichnis.name}“. "
                    "Entferne es zuerst oder ersetze die Dateien dort von Hand.",
                    status_code=409,
                )
        temp = basis / f".install-{uuid.uuid4().hex}"
        alt = basis / f".alt-{uuid.uuid4().hex}"
        temp.mkdir()
        try:
            for name, inhalt in dateien.items():
                (temp / name).write_bytes(inhalt)
            if ziel.exists():
                ziel.rename(alt)
            temp.rename(ziel)
        except OSError as e:
            if alt.exists() and not ziel.exists():
                alt.rename(ziel)
            raise PluginFehler(f"Das Plugin konnte nicht gespeichert werden: {e}", status_code=500)
        finally:
            shutil.rmtree(temp, ignore_errors=True)
            shutil.rmtree(alt, ignore_errors=True)
    status_geaendert()
    return _lies_plugin_ordner(ziel)


def _paket_dateien(zf: zipfile.ZipFile) -> dict[str, bytes]:
    eintraege = [i for i in zf.infolist() if not i.is_dir()]
    if not eintraege:
        raise PluginFehler("Das Paket ist leer", status_code=422)
    pfade = []
    for i in eintraege:
        p = PurePosixPath(i.filename.replace("\\", "/"))
        if p.is_absolute() or ".." in p.parts:
            raise PluginFehler("Das Paket enthält ungültige Pfade", status_code=422)
        if p.parts and p.parts[0] in ("__MACOSX",):
            continue
        pfade.append((i, p))
    # Ein gemeinsamer oberster Ordner (Ordner gezippt statt Inhalt) wird abgeschnitten
    oberste = {p.parts[0] for _, p in pfade if len(p.parts) > 1}
    alle_in_ordner = all(len(p.parts) > 1 for _, p in pfade)
    praefix = len(oberste) == 1 and alle_in_ordner
    dateien: dict[str, bytes] = {}
    gesamt = 0
    for info, p in pfade:
        teile = p.parts[1:] if praefix else p.parts
        if len(teile) != 1:
            raise PluginFehler("Das Paket darf keine Unterordner enthalten", status_code=422)
        name = teile[0]
        if name.startswith("."):
            continue
        if name not in ERLAUBTE_PAKETDATEIEN:
            raise PluginFehler(
                f"Unerwartete Datei im Paket: {name} (erlaubt: {', '.join(sorted(ERLAUBTE_PAKETDATEIEN))})",
                status_code=422,
            )
        gesamt += info.file_size
        if gesamt > MAX_PAKET_BYTES:
            raise PluginFehler("Das entpackte Paket ist zu groß", status_code=413)
        dateien[name] = zf.read(info)
    return dateien


# ---------------------------------------------------------------------------
# Sicht der Laufzeit (Phase 3)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LaufendesPlugin:
    """Unveränderliche Momentaufnahme eines Plugins, das laufen darf - das, was die Laufzeit braucht."""
    plugin_id: str
    name: str
    wasm_pfad: Path
    wasm_sha256: str
    # Vom Nutzer BESTÄTIGTE Rechte (nicht das aktuelle Manifest): entity -> frozenset(actions)
    rechte: dict[str, frozenset[str]]
    # Aktive Hooks = bestätigt ∩ im Manifest ∩ nicht einzeln abgeschaltet
    hooks: frozenset[str]
    fehler_in_folge: int


_laufend_cache: tuple[tuple, list[LaufendesPlugin]] | None = None
_laufend_sperre = threading.Lock()


def _ordner_signatur(basis: Path) -> tuple:
    if not basis.is_dir():
        return ()
    eintraege = []
    for ordner in sorted(basis.iterdir()):
        if ordner.is_dir() and not ordner.name.startswith("."):
            eintraege.append((ordner.name, _datei_signatur(ordner / MANIFEST_NAME), _datei_signatur(ordner / WASM_NAME)))
    return tuple(eintraege)


def laufende_plugins(session_factory=None) -> list[LaufendesPlugin]:
    """Alle Plugins, die gerade laufen dürfen, sortiert nach Plugin-ID (feste Aufrufreihenfolge).

    Liest mit einer EIGENEN Session: Aufrufer ist typischerweise ein Speichervorgang mitten in
    seiner Transaktion (Phase 5) - dessen Session darf hier nicht benutzt werden. Im WAL-Modus
    blockiert dieses Lesen nicht. Ergebnis wird gecacht, bis sich Status oder Dateien ändern."""
    global _laufend_cache
    if abgesicherter_modus():
        return []
    basis = plugin_verzeichnis()
    with _generation_sperre:
        generation = _generation
    schluessel = (generation, str(basis), _ordner_signatur(basis))
    with _laufend_sperre:
        if _laufend_cache and _laufend_cache[0] == schluessel:
            return list(_laufend_cache[1])

    if session_factory is None:
        from database.connection import SessionLocal as session_factory
    db = session_factory()
    try:
        ergebnis = []
        for z in alle_zustaende(db, basis):
            if not z.laeuft:
                continue
            g, zeile = z.gefunden, z.status_zeile
            bestaetigt = genehmigte_rechte(zeile) or {}
            hooks = (set(bestaetigt.get("hooks") or []) & set(g.manifest.hooks)) - set(deaktivierte_hooks(zeile))
            ergebnis.append(LaufendesPlugin(
                plugin_id=g.plugin_id,
                name=g.manifest.name,
                wasm_pfad=g.verzeichnis / WASM_NAME,
                wasm_sha256=g.wasm_sha256,
                rechte={e: frozenset(a) for e, a in (bestaetigt.get("entities") or {}).items()},
                hooks=frozenset(hooks),
                fehler_in_folge=zeile.fehler_in_folge,
            ))
        db.rollback()
    finally:
        db.close()
    ergebnis.sort(key=lambda p: p.plugin_id)
    with _laufend_sperre:
        _laufend_cache = (schluessel, ergebnis)
    return list(ergebnis)
