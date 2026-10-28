"""
Event-Pipeline: verbindet Speichervorgänge der App mit den Plugin-Hooks
(docs/plan-plugin-system.md, Phase 5).

Zentral über SQLAlchemy-Session-Events auf `SessionLocal` - die bestehenden Endpunkte bleiben
unverändert.

Ablauf je Transaktion:
1. `before_flush`  - zu löschende Kunden/Rechnungen/Artikel als DTO sichern (danach sind sie weg).
2. `after_flush`   - neue/geänderte Objekte merken (IDs sind jetzt vergeben). Geänderte
                     Rechnungspositionen zählen als Änderung ihrer Rechnung. Endpunkte flushen oft
                     mehrfach (erst Rechnung für die ID, dann Positionen) - deshalb nur sammeln.
3. `before_commit` - Pre-Hooks mit dem VOLLSTÄNDIGEN Stand ausführen. Geänderte Felder (nur die
                     erlaubten, siehe plugins/dto.py) zurückschreiben. `PluginAbbruch` verhindert den
                     Commit; der Endpunkt antwortet mit 422 (Exception-Handler in main.py).
4. `after_commit`  - Post-Hooks im Hintergrund anstoßen.
5. `after_rollback`/`after_soft_rollback` - Gesammeltes verwerfen.

Bewusste Lücken: Massen-Updates per `query.update()/delete()` und rohes SQL (`text(...)`) laufen
an den ORM-Events vorbei. Für Kunden/Rechnungen/Artikel betrifft das nur Migrationen und
Datenkorrekturen - genau dort sollen Plugins auch nicht eingreifen.
"""
from __future__ import annotations

import contextlib
import contextvars
import logging
import time

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from database.models import Rechnung, Rechnungsposition

from . import dto, laufzeit
from .schreiben import DatenZugriff

log = logging.getLogger("rechnungsfee.plugins")

_SCHLUESSEL = "_plugin_ereignisse"     # session.info: {(entity, id): {"action", "vorher"}}
_POST = "_plugin_post"                  # session.info: [(entity, action, dto)]
_IN_ARBEIT = "_plugin_in_arbeit"
_DATEIEN = "_plugin_dateien_nach_commit"
_ZIELE = "_plugin_gepruefte_ziele"
_BUDGET_ENDE = "_plugin_budget_ende"

_unterdrueckt: contextvars.ContextVar[bool] = contextvars.ContextVar("plugins_unterdrueckt", default=False)


@contextlib.contextmanager
def ohne_plugins():
    """Plugins für einen Block abschalten - App-Start, Datenübernahme/Massenimport. Dort sollen
    weder Prüf-Plugins einzelne Zeilen abweisen noch Post-Hooks pro Zeile feuern."""
    token = _unterdrueckt.set(True)
    try:
        yield
    finally:
        _unterdrueckt.reset(token)


def plugins_aus(fn):
    """Dekorator-Variante von ohne_plugins() für Endpunkte (sync und async)."""
    import functools
    import inspect as _inspect

    if _inspect.iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def asynchron(*args, **kwargs):
            with ohne_plugins():
                return await fn(*args, **kwargs)
        return asynchron

    @functools.wraps(fn)
    def synchron(*args, **kwargs):
        with ohne_plugins():
            return fn(*args, **kwargs)
    return synchron


def _aktiv(session: Session) -> bool:
    return not _unterdrueckt.get() and not session.info.get(_IN_ARBEIT)


def _merke(session: Session, entity: str, obj_id, action: str, vorher: dict | None = None) -> None:
    ereignisse = session.info.setdefault(_SCHLUESSEL, {})
    schluessel = (entity, obj_id)
    bisher = ereignisse.get(schluessel)
    if bisher is None:
        ereignisse[schluessel] = {"action": action, "vorher": vorher}
    elif action == "delete":
        if bisher["action"] == "create":
            del ereignisse[schluessel]          # in derselben Transaktion angelegt und gelöscht
        else:
            ereignisse[schluessel] = {"action": "delete", "vorher": vorher}
    # create bleibt create, update bleibt update


def _before_flush(session: Session, _ctx, _instanzen) -> None:
    if not _aktiv(session) or not session.deleted or not laufzeit.irgendein_plugin():
        return
    for obj in session.deleted:
        d = dto.NACH_MODELL.get(type(obj))
        if d is None or obj.id is None:
            continue
        if _relevant(d.name, "delete"):
            _merke(session, d.name, obj.id, "delete", dto.als_dto(obj))


def _relevant(entity: str, action: str) -> bool:
    return laufzeit.hat_hooks(entity, action, "before") or laufzeit.hat_hooks(entity, action, "after")


def _after_flush(session: Session, _ctx) -> None:
    if not _aktiv(session):
        return
    if not (session.new or session.dirty or session.deleted) or not laufzeit.irgendein_plugin():
        return   # schneller Ausstieg: ohne laufende Plugins kostet die Pipeline praktisch nichts
    for obj in session.new:
        d = dto.NACH_MODELL.get(type(obj))
        if d is not None:
            _merke(session, d.name, obj.id, "create")
        elif isinstance(obj, Rechnungsposition) and obj.rechnung_id:
            _merke(session, "invoice", obj.rechnung_id, "update")
    for obj in session.dirty:
        d = dto.NACH_MODELL.get(type(obj))
        if d is not None:
            if session.is_modified(obj, include_collections=False):
                _merke(session, d.name, obj.id, "update")
        elif isinstance(obj, Rechnungsposition) and obj.rechnung_id \
                and session.is_modified(obj, include_collections=False):
            _merke(session, "invoice", obj.rechnung_id, "update")
    for obj in session.deleted:
        if isinstance(obj, Rechnungsposition) and obj.rechnung_id:
            _merke(session, "invoice", obj.rechnung_id, "update")


def _before_commit(session: Session) -> None:
    if not _aktiv(session) or session.in_nested_transaction():
        return
    if session.new or session.dirty or session.deleted:
        session.flush()   # noch Ausstehendes erfassen (after_flush sammelt)
    ereignisse = session.info.pop(_SCHLUESSEL, None)
    if not ereignisse:
        return

    session.info[_IN_ARBEIT] = True
    try:
        session.info.setdefault(_POST, [])
        host = DatenZugriff(session=session)
        start = time.perf_counter()
        session.info[_BUDGET_ENDE] = start + laufzeit.PRE_HOOK_BUDGET_MS / 1000
        for (entity, obj_id), e in list(ereignisse.items()):
            action = e["action"]
            # Gemeinsames Budget für die ganze Transaktion (NFA-3)
            rest = laufzeit.PRE_HOOK_BUDGET_MS - (time.perf_counter() - start) * 1000

            if action == "delete":
                vorher = e["vorher"]
                if vorher is None:
                    continue
                if laufzeit.hat_hooks(entity, "delete", "before"):
                    session.info.setdefault(_ZIELE, set()).add((entity, obj_id))
                    try:
                        laufzeit.vor_aenderung(entity, "delete", vorher, host=host, budget_ms=max(rest, 0.001))
                    finally:
                        session.info[_ZIELE].discard((entity, obj_id))
                merke_post(session, entity, "delete", vorher)
                continue

            if not _relevant(entity, action):
                continue
            obj = session.get(dto.ENTITAETEN[entity].modell, obj_id)
            if obj is None or inspect(obj).deleted:
                continue
            vorher = dto.als_dto(obj)
            nachher = vorher
            if laufzeit.hat_hooks(entity, action, "before"):
                session.info.setdefault(_ZIELE, set()).add((entity, obj_id))
                try:
                    nachher = laufzeit.vor_aenderung(entity, action, vorher, host=host, budget_ms=max(rest, 0.001))
                finally:
                    session.info[_ZIELE].discard((entity, obj_id))
            if nachher != vorher:
                _uebernehme(entity, action, obj, vorher, nachher)
            merke_post(session, entity, action, dto.als_dto(obj) if nachher != vorher else vorher)
        session.flush()   # vom Plugin übernommene Änderungen schreiben, solange _IN_ARBEIT gilt
    except BaseException:
        session.info.pop(_POST, None)
        raise
    finally:
        session.info.pop(_IN_ARBEIT, None)
        session.info.pop(_BUDGET_ENDE, None)
        session.info.pop(_ZIELE, None)


def merke_post(session, entity, action, payload):
    # Vorfahren des auslösenden Plugins über die Commit-/Thread-Grenze mitnehmen.
    session.info.setdefault(_POST, []).append((entity, action, payload, laufzeit._kontext.get()))


def host_vor_aenderung(session, entity, action, obj, host):
    vorher = dto.als_dto(obj)
    ziel = (entity, obj.id)
    ziele = session.info.setdefault(_ZIELE, set())
    ziele.add(ziel)
    eigenes_budget = _BUDGET_ENDE not in session.info
    if eigenes_budget:
        session.info[_BUDGET_ENDE] = time.perf_counter() + laufzeit.PRE_HOOK_BUDGET_MS / 1000
    try:
        rest = (session.info[_BUDGET_ENDE] - time.perf_counter()) * 1000
        nachher = laufzeit.vor_aenderung(entity, action, vorher, host=host, budget_ms=max(rest, 0.001))
        if action != "delete" and nachher != vorher:
            _uebernehme(entity, action, obj, vorher, nachher)
    finally:
        ziele.discard(ziel)
        if eigenes_budget:
            session.info.pop(_BUDGET_ENDE, None)


def _uebernehme(entity: str, action: str, obj, vorher: dict, nachher: dict) -> None:
    erg = dto.uebernehme(obj, vorher, nachher)
    hook = f"{entity}:{action}:before"
    if erg.ignoriert or erg.ungueltig:
        teile = []
        if erg.ignoriert:
            teile.append("ignoriert: " + ", ".join(erg.ignoriert))
        if erg.ungueltig:
            teile.append("ungültig: " + "; ".join(erg.ungueltig))
        # welchem Plugin das gehört, weiß hier niemand mehr genau (Kette) - deshalb als Hinweis
        # unter dem Pseudo-Plugin der Pipeline protokollieren
        laufzeit._protokolliere("rechnungsfee.pipeline", hook, "teilweise",
                                f"{entity} {obj.id}: " + " | ".join(teile), entitaet=entity)
        log.info("Plugin-Änderung an %s %s teilweise übernommen: %s", entity, obj.id, teile)


def _after_commit(session: Session) -> None:
    if session.in_nested_transaction():
        return  # RELEASE SAVEPOINT ist noch kein dauerhafter Commit.
    dateien = session.info.pop(_DATEIEN, [])
    if dateien:
        from api.rechnungen import _dateien_entfernen
        _dateien_entfernen(dateien)
    post = session.info.pop(_POST, None)
    if not post or _unterdrueckt.get():
        return
    for entity, action, payload, kontext in post:
        token = laufzeit._kontext.set(kontext)
        try:
            laufzeit.nach_aenderung(entity, action, payload,
                host_factory=lambda: DatenZugriff(session_factory=laufzeit._sessions()))
        finally:
            laufzeit._kontext.reset(token)


def _after_rollback(session: Session, transaction=None) -> None:
    if session.in_nested_transaction() or (transaction is not None and transaction.parent is not None):
        return  # Einen gescheiterten Host-Aufruf stellt dessen Savepoint-Guard wieder her.
    for key in (_SCHLUESSEL, _POST, _IN_ARBEIT, _DATEIEN, _ZIELE, _BUDGET_ENDE):
        session.info.pop(key, None)


def registrieren_session(session):
    if _before_commit not in list(session.dispatch.before_commit):
        registrieren(session)


_MARKIERUNG = "_rechnungsfee_plugin_pipeline"


def registrieren(ziel) -> None:
    """Hängt die Pipeline an eine Session-Factory (sessionmaker) oder Session-Klasse.
    Mehrfachaufruf für dasselbe Ziel ist harmlos.

    Markierung direkt am Ziel-Objekt statt id(ziel) in einem Set oder event.contains(): Python
    vergibt die id() einer freigegebenen Factory neu, und SQLAlchemys contains()-Buchhaltung hängt
    ebenfalls an id(). Eine neue Factory hielt sich dadurch zufällig für bereits registriert und
    lief ohne Plugins (aufgefallen als wackelige Tests)."""
    if getattr(ziel, _MARKIERUNG, False):
        return
    setattr(ziel, _MARKIERUNG, True)
    event.listen(ziel, "before_flush", _before_flush)
    event.listen(ziel, "after_flush", _after_flush)
    event.listen(ziel, "before_commit", _before_commit)
    event.listen(ziel, "after_commit", _after_commit)
    event.listen(ziel, "after_rollback", _after_rollback)
    event.listen(ziel, "after_soft_rollback", _after_rollback)


__all__ = ["registrieren", "ohne_plugins", "plugins_aus", "Rechnung"]
