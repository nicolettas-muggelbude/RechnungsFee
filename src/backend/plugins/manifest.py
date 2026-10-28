"""
Plugin-Manifest (plugin.toml) einlesen und prüfen.

Lastenheft: docs/plugin-system.md, Abschnitt 6. Ablaufplan: docs/plan-plugin-system.md, Phase 1.

Ein ungültiges Manifest wird nicht stillschweigend verworfen: parse_manifest() liefert immer eine
Fehlerliste zurück, damit die Einstellungsseite das Plugin trotzdem anzeigen und erklären kann,
warum es nicht aktivierbar ist.
"""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

MANIFEST_NAME = "plugin.toml"
WASM_NAME = "plugin.wasm"

# Version des WIT-Pakets rechnungsfee:plugin, die dieser Host implementiert
# (plugins/wit/rechnungsfee.wit). Ein Plugin muss eine davon in api_version angeben.
UNTERSTUETZTE_API_VERSIONEN = ("0.1.0",)

ENTITAETEN = ("customer", "invoice", "voucher", "article", "task")
AKTIONEN = ("create", "read", "update", "delete")
# Lese-Hooks sind bewusst nicht vorgesehen (jede Liste würde sonst durch Plugins laufen),
# siehe plan-plugin-system.md, Abschnitt 4 Punkt 8.
HOOK_AKTIONEN = ("create", "update", "delete")
HOOK_PHASEN = ("before", "after")

ENTITAET_BEZEICHNUNG = {
    "customer": ("Kunden", "Kunde"),
    "invoice": ("Rechnungen", "Rechnung"),
    "voucher": ("Belege", "Beleg"),
    "article": ("Artikel", "Artikel"),
    "task": ("Aufgaben", "Aufgabe"),
}

_ID_MUSTER = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*(?:\.[a-z0-9]+(?:-[a-z0-9]+)*)+$")
_SEMVER_MUSTER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
_HOOK_MUSTER = re.compile(r"^([a-z]+):([a-z]+):([a-z]+)$")

MAX_TEXTLAENGE = {"id": 200, "name": 100, "version": 50, "author": 200, "description": 1000, "homepage": 300}


@dataclass(frozen=True)
class PluginManifest:
    id: str
    name: str
    version: str
    author: str
    description: str
    api_version: str
    min_app_version: str | None
    homepage: str | None
    # entitaet -> sortiertes Tupel der erlaubten Aktionen
    rechte: dict[str, tuple[str, ...]]
    # sortiertes Tupel "entity:action:phase"
    hooks: tuple[str, ...]

    def rechte_snapshot(self) -> dict:
        """Normalisierte, vergleichbare Form der angeforderten Rechte + Hooks. Wird bei der
        Aktivierung als vom Nutzer bestätigter Stand in plugin_status gespeichert."""
        return {
            "entities": {e: list(a) for e, a in sorted(self.rechte.items())},
            "hooks": list(self.hooks),
        }


@dataclass
class ManifestErgebnis:
    manifest: PluginManifest | None
    fehler: list[str] = field(default_factory=list)
    warnungen: list[str] = field(default_factory=list)


def rechte_erweitert(bestaetigt: dict | None, aktuell: dict) -> bool:
    """True, wenn `aktuell` irgendein Recht oder einen Hook enthält, der in `bestaetigt` fehlt.
    Weniger Rechte als bestätigt sind unkritisch (kein erneutes Nachfragen)."""
    if not bestaetigt:
        return True
    alt_e = {e: set(a) for e, a in (bestaetigt.get("entities") or {}).items()}
    for entitaet, aktionen in (aktuell.get("entities") or {}).items():
        if not set(aktionen) <= alt_e.get(entitaet, set()):
            return True
    return not set(aktuell.get("hooks") or []) <= set(bestaetigt.get("hooks") or [])


def parse_manifest(pfad: Path) -> ManifestErgebnis:
    """Liest und validiert eine plugin.toml. Wirft nie - Fehler landen in .fehler."""
    try:
        roh = tomllib.loads(pfad.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ManifestErgebnis(None, [f"{MANIFEST_NAME} fehlt"])
    except UnicodeDecodeError:
        return ManifestErgebnis(None, [f"{MANIFEST_NAME} ist nicht UTF-8-kodiert"])
    except tomllib.TOMLDecodeError as e:
        return ManifestErgebnis(None, [f"{MANIFEST_NAME} ist kein gültiges TOML: {e}"])
    except OSError as e:
        return ManifestErgebnis(None, [f"{MANIFEST_NAME} kann nicht gelesen werden: {e}"])
    return pruefe_manifest(roh)


def pruefe_manifest(roh: dict) -> ManifestErgebnis:
    fehler: list[str] = []
    warnungen: list[str] = []

    plugin = roh.get("plugin")
    if not isinstance(plugin, dict):
        return ManifestErgebnis(None, ["Abschnitt [plugin] fehlt"])

    def text(schluessel: str, pflicht: bool = True) -> str | None:
        wert = plugin.get(schluessel)
        if wert is None:
            if pflicht:
                fehler.append(f"[plugin].{schluessel} fehlt")
            return None
        if not isinstance(wert, str) or not wert.strip():
            fehler.append(f"[plugin].{schluessel} muss ein nicht-leerer Text sein")
            return None
        wert = wert.strip()
        grenze = MAX_TEXTLAENGE.get(schluessel)
        if grenze and len(wert) > grenze:
            fehler.append(f"[plugin].{schluessel} ist länger als {grenze} Zeichen")
            return None
        return wert

    plugin_id = text("id")
    name = text("name")
    version = text("version")
    author = text("author")
    description = text("description")
    homepage = text("homepage", pflicht=False)
    min_app_version = text("min_app_version", pflicht=False)
    api_version = text("api_version", pflicht=False)

    if plugin_id and not _ID_MUSTER.match(plugin_id):
        fehler.append(
            "[plugin].id muss im Reverse-DNS-Format sein, nur Kleinbuchstaben, Ziffern, Punkt und "
            "Bindestrich (z. B. „org.rechnungsfee.task-automation“)"
        )
    if version and not _SEMVER_MUSTER.match(version):
        fehler.append("[plugin].version muss eine SemVer-Version sein (z. B. „1.2.0“)")
    if min_app_version and not _SEMVER_MUSTER.match(min_app_version):
        fehler.append("[plugin].min_app_version muss eine SemVer-Version sein")
    if homepage and not homepage.startswith(("https://", "http://")):
        warnungen.append("[plugin].homepage ist keine http(s)-Adresse und wird nicht verlinkt")
        homepage = None

    if api_version is None and "api_version" not in plugin:
        # Lastenheft-Beispiel kennt das Feld noch nicht - kein harter Fehler, solange es
        # nur eine API-Version gibt.
        api_version = UNTERSTUETZTE_API_VERSIONEN[0]
        warnungen.append(
            f"[plugin].api_version fehlt, angenommen wird {api_version}"
        )
    elif api_version and api_version not in UNTERSTUETZTE_API_VERSIONEN:
        fehler.append(
            f"Plugin-Schnittstelle {api_version} wird von dieser RechnungsFee-Version nicht "
            f"unterstützt (unterstützt: {', '.join(UNTERSTUETZTE_API_VERSIONEN)})"
        )

    rechte, hooks = _pruefe_berechtigungen(roh.get("permissions"), fehler, warnungen)

    if fehler:
        return ManifestErgebnis(None, fehler, warnungen)
    return ManifestErgebnis(
        PluginManifest(
            id=plugin_id, name=name, version=version, author=author, description=description,
            api_version=api_version, min_app_version=min_app_version, homepage=homepage,
            rechte=rechte, hooks=hooks,
        ),
        fehler,
        warnungen,
    )


def _pruefe_berechtigungen(
    perm, fehler: list[str], warnungen: list[str]
) -> tuple[dict[str, tuple[str, ...]], tuple[str, ...]]:
    if perm is None:
        warnungen.append("Abschnitt [permissions] fehlt - das Plugin kann nichts tun")
        return {}, ()
    if not isinstance(perm, dict):
        fehler.append("[permissions] muss ein Abschnitt sein")
        return {}, ()

    unbekannt = set(perm) - {"entities", "hooks"}
    for s in sorted(unbekannt):
        warnungen.append(f"[permissions].{s} ist unbekannt und wird ignoriert")

    rechte: dict[str, set[str]] = {}
    eintraege = perm.get("entities", [])
    if not isinstance(eintraege, list):
        fehler.append("[permissions].entities muss eine Liste sein")
        eintraege = []
    for i, eintrag in enumerate(eintraege, start=1):
        if not isinstance(eintrag, dict):
            fehler.append(f"[permissions].entities[{i}] muss eine Tabelle {{ type, actions }} sein")
            continue
        typ = eintrag.get("type")
        aktionen = eintrag.get("actions")
        if typ not in ENTITAETEN:
            fehler.append(f"[permissions].entities[{i}]: unbekannte Entität „{typ}“ (erlaubt: {', '.join(ENTITAETEN)})")
            continue
        if not isinstance(aktionen, list) or not aktionen:
            fehler.append(f"[permissions].entities[{i}] ({typ}): actions muss eine nicht-leere Liste sein")
            continue
        for a in aktionen:
            if a not in AKTIONEN:
                fehler.append(f"[permissions].entities[{i}] ({typ}): unbekannte Aktion „{a}“ (erlaubt: {', '.join(AKTIONEN)})")
            else:
                rechte.setdefault(typ, set()).add(a)

    hooks: set[str] = set()
    hook_liste = perm.get("hooks", [])
    if not isinstance(hook_liste, list):
        fehler.append("[permissions].hooks muss eine Liste sein")
        hook_liste = []
    for h in hook_liste:
        m = _HOOK_MUSTER.match(h) if isinstance(h, str) else None
        if not m:
            fehler.append(f"Hook „{h}“ hat nicht das Format entity:action:before|after")
            continue
        entitaet, aktion, phase = m.groups()
        if entitaet not in ENTITAETEN:
            fehler.append(f"Hook „{h}“: unbekannte Entität „{entitaet}“")
        elif aktion not in HOOK_AKTIONEN:
            fehler.append(f"Hook „{h}“: Aktion „{aktion}“ wird nicht unterstützt (erlaubt: {', '.join(HOOK_AKTIONEN)})")
        elif phase not in HOOK_PHASEN:
            fehler.append(f"Hook „{h}“: Phase „{phase}“ muss before oder after sein")
        else:
            hooks.add(h)

    return (
        {e: tuple(sorted(a, key=AKTIONEN.index)) for e, a in sorted(rechte.items())},
        tuple(sorted(hooks)),
    )


# ---------------------------------------------------------------------------
# Klartext für die Einstellungsseite
# ---------------------------------------------------------------------------

_AKTION_VERB = {"create": "anlegen", "read": "lesen", "update": "ändern", "delete": "löschen"}


def rechte_klartext(rechte: dict[str, tuple[str, ...]] | dict[str, list[str]]) -> list[str]:
    """{"task": ("create","read")} -> ["Darf Aufgaben lesen und anlegen"]"""
    zeilen = []
    for entitaet in ENTITAETEN:
        aktionen = rechte.get(entitaet)
        if not aktionen:
            continue
        # Reihenfolge: lesen zuerst, dann schreibende Aktionen
        reihenfolge = ["read", "create", "update", "delete"]
        verben = [_AKTION_VERB[a] for a in reihenfolge if a in aktionen]
        if len(verben) > 1:
            verb_text = ", ".join(verben[:-1]) + " und " + verben[-1]
        else:
            verb_text = verben[0]
        zeilen.append(f"Darf {ENTITAET_BEZEICHNUNG[entitaet][0]} {verb_text}")
    return zeilen


_HOOK_TEXT = {
    ("create", "before"): "Prüft oder verändert neue {sg_akk} vor dem Speichern",
    ("update", "before"): "Prüft oder verändert {pl} vor dem Speichern einer Änderung",
    ("delete", "before"): "Kann das Löschen von {pl} verhindern",
    ("create", "after"): "Reagiert, nachdem {art_nom} {sg} angelegt wurde",
    ("update", "after"): "Reagiert, nachdem {art_nom} {sg} geändert wurde",
    ("delete", "after"): "Reagiert, nachdem {art_nom} {sg} gelöscht wurde",
}
_ARTIKEL = {"customer": "ein", "invoice": "eine", "voucher": "ein", "article": "ein", "task": "eine"}
_SG_AKK = {"customer": "Kunden", "invoice": "Rechnungen", "voucher": "Belege", "article": "Artikel", "task": "Aufgaben"}


def hook_klartext(hook: str) -> str:
    entitaet, aktion, phase = hook.split(":")
    vorlage = _HOOK_TEXT[(aktion, phase)]
    return vorlage.format(
        pl=ENTITAET_BEZEICHNUNG[entitaet][0],
        sg=ENTITAET_BEZEICHNUNG[entitaet][1],
        sg_akk=_SG_AKK[entitaet],
        art_nom=_ARTIKEL[entitaet],
    )
