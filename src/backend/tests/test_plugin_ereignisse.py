"""
Plugin-System Phase 4 + 5 (docs/plan-plugin-system.md): DTOs, lesende Host-API und die
Event-Pipeline an echten ORM-Commits.

Test-Plugin-Stichworte (quelle/testplugin.c): "abbrechen", "unveraendert", "plugin-notiz"
(setzt notizen = "geprueft durch Plugin"), sonst Payload in {"geprueft", "original"} verpackt.
"""
import json
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import Artikel, Kunde, PluginProtokoll, Rechnung, Rechnungsposition
from plugins import dto, ereignisse, laufzeit, registry
from plugins.host_api import HostApiFehler, LeseZugriff

FIXTURES = Path(__file__).parent / "fixtures" / "plugins"
ID = "de.test.pruefer"

MANIFEST = f"""
[plugin]
id = "{ID}"
name = "Prüfer"
version = "1.0.0"
author = "Test"
description = "Test"
api_version = "0.1.0"

[permissions]
entities = [
    {{ type = "customer", actions = ["read"] }},
    {{ type = "invoice", actions = ["read"] }},
    {{ type = "task", actions = ["create"] }}
]
hooks = [
    "customer:create:before", "customer:update:before", "customer:create:after",
    "invoice:create:before", "invoice:update:before", "invoice:delete:before",
]
"""


@pytest.fixture
def sf(tmp_path, monkeypatch):
    plugin_dir = tmp_path / "plugins"
    (plugin_dir / ID).mkdir(parents=True)
    (plugin_dir / ID / "plugin.toml").write_text(MANIFEST, encoding="utf-8")
    shutil.copy(FIXTURES / "testplugin.wasm", plugin_dir / ID / "plugin.wasm")
    monkeypatch.setenv("RECHNUNGSFEE_PLUGIN_DIR", str(plugin_dir))
    monkeypatch.delenv("RECHNUNGSFEE_PLUGINS", raising=False)

    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    ereignisse.registrieren(factory)
    laufzeit.konfiguriere(factory)
    registry.status_geaendert()

    db = factory()
    z = registry.zustand(db, ID)
    registry.aktivieren(db, ID, z.gefunden.wasm_sha256, z.gefunden.manifest.rechte_snapshot())
    registry.global_setzen(db, True)
    db.close()
    yield factory
    laufzeit.warte_auf_hintergrund()
    laufzeit.konfiguriere(None)
    engine.dispose()


@pytest.fixture
def spion(monkeypatch):
    """Zeichnet auf, was die Pipeline an die Laufzeit übergibt (Plugin läuft trotzdem)."""
    vor, nach = [], []
    original_vor, original_nach = laufzeit.vor_aenderung, laufzeit.nach_aenderung

    def vor_aenderung(entity, action, payload, **kw):
        vor.append((entity, action, payload))
        return original_vor(entity, action, payload, **kw)

    def nach_aenderung(entity, action, payload, **kw):
        nach.append((entity, action, payload))
        return original_nach(entity, action, payload, **kw)

    monkeypatch.setattr(laufzeit, "vor_aenderung", vor_aenderung)
    monkeypatch.setattr(laufzeit, "nach_aenderung", nach_aenderung)
    return vor, nach


def kunde(**kw):
    return Kunde(nachname=kw.pop("nachname", "Muster"), land="DE", **kw)


def rechnung(**kw):
    return Rechnung(typ="ausgang", datum=date(2026, 10, 28), **kw)


def position(nr=1, beschreibung="Beratung", netto="100.00"):
    return Rechnungsposition(position_nr=nr, beschreibung=beschreibung, menge=Decimal("1"),
                             netto=Decimal(netto), ust_satz=Decimal("19"),
                             ust_betrag=Decimal(netto) * Decimal("0.19"), brutto=Decimal(netto) * Decimal("1.19"))


def pipeline_protokoll(factory):
    laufzeit.warte_auf_hintergrund()
    db = factory()
    try:
        return [(p.hook, p.meldung) for p in db.query(PluginProtokoll).filter_by(plugin_id="rechnungsfee.pipeline")]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------

def test_registrieren_ist_idempotent_und_pro_factory(tmp_path):
    """Neue Factories bekommen oft die id() freigegebener alter - trotzdem muss jede neue Factory
    registriert werden (und jede genau einmal)."""
    gefeuert = []
    for _ in range(20):
        engine = create_engine("sqlite://")
        f = sessionmaker(bind=engine)
        ereignisse.registrieren(f)
        ereignisse.registrieren(f)
        db = f()
        zaehler = []
        from sqlalchemy import event as sa_event
        sa_event.listen(db, "before_commit", lambda _s: zaehler.append(1))
        db.commit()
        db.close()
        gefeuert.append(getattr(f, ereignisse._MARKIERUNG, False))
        del f, db
        engine.dispose()
    assert all(gefeuert)


def test_dto_rechnung_mit_positionen(sf):
    db = sf()
    with ereignisse.ohne_plugins():
        r = rechnung(rechnungsnummer="RE-1", netto_gesamt=Decimal("150.00"))
        r.positionen = [position(2, "Zwei", "50.00"), position(1, "Eins", "100.00")]
        db.add(r)
        db.commit()
    d = dto.als_dto(r)
    assert d["_schema"] == "invoice@1"
    assert d["netto_gesamt"] == "150.00" and d["datum"] == "2026-10-28"
    assert [p["beschreibung"] for p in d["positionen"]] == ["Eins", "Zwei"]
    assert "absender_snapshot" not in d and "original_pdf_pfad" not in d
    json.dumps(d)   # vollständig serialisierbar
    db.close()


def test_uebernehme_nur_erlaubte_felder():
    k = kunde(notizen="alt", kundennummer="K-1")
    k.id = 1
    vorher = dto.als_dto(k)
    nachher = {**vorher, "notizen": "neu", "kundennummer": "K-999", "email": 42, "plz": "1" * 20}
    erg = dto.uebernehme(k, vorher, nachher)
    assert erg.geaendert == ["notizen"]
    assert erg.ignoriert == ["kundennummer"]
    assert len(erg.ungueltig) == 2
    assert k.notizen == "neu" and k.kundennummer == "K-1" and k.email is None


def test_uebernehme_finalisierte_rechnung_gobd():
    r = rechnung(ist_entwurf=False, notizen="alt")
    r.id = 1
    vorher = dto.als_dto(r)
    erg = dto.uebernehme(r, vorher, {**vorher, "notizen": "neu"})
    assert erg.geaendert == [] and "GoBD" in erg.ignoriert[0]
    assert r.notizen == "alt"


# ---------------------------------------------------------------------------
# Host-API (lesend)
# ---------------------------------------------------------------------------

def test_lesezugriff(sf):
    db = sf()
    with ereignisse.ohne_plugins():
        db.add_all([kunde(nachname="A", ort="Berlin"), kunde(nachname="B", ort="Hamburg"), kunde(nachname="C", ort="Berlin")])
        db.commit()
    host = LeseZugriff(session=db)
    assert json.loads(host.get(ID, "customer", "1"))["nachname"] == "A"
    berlin = json.loads(host.list(ID, "customer", '{"ort": "Berlin"}'))
    assert [k["nachname"] for k in berlin] == ["A", "C"]
    assert len(json.loads(host.list(ID, "customer", '{"limit": 1, "offset": 1}'))) == 1
    assert len(json.loads(host.list(ID, "customer", None))) == 3

    for aufruf, art, text in [
        (lambda: host.get(ID, "customer", "99"), "not-found", "nicht gefunden"),
        (lambda: host.get(ID, "customer", "abc"), "validation-error", "Ungültige ID"),
        (lambda: host.list(ID, "customer", '{"passwort": 1}'), "validation-error", "Unbekanntes Filterfeld"),
        (lambda: host.list(ID, "customer", '{"limit": 1000}'), "validation-error", "limit"),
        (lambda: host.get(ID, "voucher", "1"), "not-found", "nicht gefunden"),
        (lambda: host.get(ID, "task", "1"), "validation-error", "noch nicht"),
        (lambda: host.create(ID, "customer", "{}"), "validation-error", "nur lesend"),
        (lambda: host.delete(ID, "invoice", "1"), "validation-error", "nur lesend"),
    ]:
        with pytest.raises(HostApiFehler) as e:
            aufruf()
        assert e.value.art == art and text in e.value.meldung, e.value.meldung
    db.close()


def test_beleg_als_voucher(sf):
    from database.models import Beleg

    db = sf()
    with ereignisse.ohne_plugins():
        b = Beleg(dateiname="2026/10/geheim/pfad.pdf", original_name="Quittung.pdf",
                  mime_type="application/pdf", dateigroesse=1234, sha256="ab" * 32)
        db.add(b)
        db.flush()
        db.add(rechnung(beleg_id=b.id))
        db.commit()
    host = LeseZugriff(session=db)
    beleg = json.loads(host.get(ID, "voucher", str(b.id)))
    assert beleg["_schema"] == "voucher@1" and beleg["original_name"] == "Quittung.pdf"
    assert "dateiname" not in beleg and "beleg_pdfa_pfad" not in beleg   # keine internen Pfade
    assert json.loads(host.list(ID, "invoice", None))[0]["beleg_id"] == b.id
    vorher = dto.als_dto(b)
    erg = dto.uebernehme(b, vorher, {**vorher, "original_name": "anders.pdf"})
    assert erg.geaendert == [] and b.original_name == "Quittung.pdf"
    db.close()


def test_lesezugriff_mit_eigener_session(sf):
    db = sf()
    with ereignisse.ohne_plugins():
        db.add(kunde(nachname="Hintergrund"))
        db.commit()
    db.close()
    host = LeseZugriff(session_factory=sf)
    assert json.loads(host.get(ID, "customer", "1"))["nachname"] == "Hintergrund"


# ---------------------------------------------------------------------------
# Pipeline: Kunden
# ---------------------------------------------------------------------------

def test_kunde_anlegen_plugin_aendert_erlaubtes_feld(sf):
    db = sf()
    db.add(kunde(notizen="bitte plugin-notiz"))
    db.commit()
    assert db.query(Kunde).one().notizen == "geprueft durch Plugin"
    db.close()


def test_kunde_anlegen_unveraendert(sf, spion):
    vor, _ = spion
    db = sf()
    db.add(kunde(notizen="unveraendert"))
    db.commit()
    assert db.query(Kunde).one().notizen == "unveraendert"
    assert [(e, a) for e, a, _ in vor] == [("customer", "create")]
    assert vor[0][2]["id"] == 1 and vor[0][2]["_schema"] == "customer@1"
    assert pipeline_protokoll(sf) == []
    db.close()


def test_plugin_kann_speichern_verhindern(sf):
    db = sf()
    db.add(kunde(notizen="abbrechen"))
    with pytest.raises(laufzeit.PluginAbbruch) as e:
        db.commit()
    assert e.value.anzeige == "Plugin „Prüfer“: Pflichtfeld fehlt"
    db.rollback()
    db.close()
    db = sf()
    assert db.query(Kunde).count() == 0     # nichts gespeichert
    db.close()


def test_kunde_aendern_loest_update_aus(sf, spion):
    vor, _ = spion
    db = sf()
    db.add(kunde(notizen="unveraendert"))
    db.commit()
    k = db.query(Kunde).one()
    k.ort = "Leipzig"
    db.commit()
    assert [(e, a) for e, a, _ in vor] == [("customer", "create"), ("customer", "update")]
    assert vor[1][2]["ort"] == "Leipzig"
    db.close()


def test_verpackte_antwort_wird_ignoriert_und_protokolliert(sf):
    """Das Test-Plugin liefert ohne Stichwort ein ganz anderes Objekt - kein Feld darf
    dadurch verändert oder gelöscht werden."""
    db = sf()
    db.add(kunde(nachname="Bleibt", ort="Bonn"))
    db.commit()
    k = db.query(Kunde).one()
    assert (k.nachname, k.ort) == ("Bleibt", "Bonn")
    eintraege = pipeline_protokoll(sf)
    assert len(eintraege) == 1 and eintraege[0][0] == "customer:create:before"
    assert "ignoriert:" in eintraege[0][1]
    db.close()


def test_post_hook_nach_commit_nicht_nach_rollback(sf, spion):
    _, nach = spion
    db = sf()
    db.add(kunde(notizen="unveraendert"))
    db.flush()
    db.rollback()
    assert nach == []
    db.add(kunde(notizen="unveraendert"))
    db.commit()
    assert [(e, a) for e, a, _ in nach] == [("customer", "create")]
    db.close()


def test_ohne_plugins_und_hauptschalter(sf):
    db = sf()
    with ereignisse.ohne_plugins():
        db.add(kunde(notizen="abbrechen"))
        db.commit()
    registry.global_setzen(db, False)
    db.add(kunde(notizen="abbrechen"))
    db.commit()
    assert db.query(Kunde).count() == 2
    db.close()


def test_artikel_ohne_hook_kein_aufruf(sf, spion):
    vor, nach = spion
    db = sf()
    db.add(Artikel(artikelnummer="A-1", typ="artikel", bezeichnung="abbrechen",
                   vk_brutto=Decimal("1.19"), vk_netto=Decimal("1.00")))
    db.commit()
    assert vor == [] and nach == []
    db.close()


# ---------------------------------------------------------------------------
# Pipeline: Rechnungen
# ---------------------------------------------------------------------------

def test_rechnung_mit_mehrfachem_flush_sieht_vollstaendigen_stand(sf, spion):
    """Wie die Endpunkte: erst Rechnung flushen (ID), dann Positionen, dann commit."""
    vor, _ = spion
    db = sf()
    r = rechnung(notizen="unveraendert")
    db.add(r)
    db.flush()
    db.add_all([position(1, "Eins"), position(2, "Zwei")])
    for p in db.new:
        if isinstance(p, Rechnungsposition):
            p.rechnung_id = r.id
    db.commit()
    assert len(vor) == 1
    entity, action, payload = vor[0]
    assert (entity, action) == ("invoice", "create")
    assert [p["beschreibung"] for p in payload["positionen"]] == ["Eins", "Zwei"]
    db.close()


def test_entwurf_wird_geaendert_finalisierte_nicht(sf):
    db = sf()
    db.add(rechnung(notizen="plugin-notiz"))
    db.commit()
    r = db.query(Rechnung).one()
    assert r.notizen == "geprueft durch Plugin"

    with ereignisse.ohne_plugins():
        r.ist_entwurf = False
        r.notizen = "fest"
        db.commit()
    r.notizen = "fest, plugin-notiz"
    db.commit()
    assert r.notizen == "fest, plugin-notiz"     # GoBD: Plugin-Änderung ignoriert
    assert any("GoBD" in m for _, m in pipeline_protokoll(sf))
    db.close()


def test_positionsaenderung_ist_rechnungs_update(sf, spion):
    vor, _ = spion
    db = sf()
    r = rechnung(notizen="unveraendert")
    r.positionen = [position()]
    db.add(r)
    db.commit()
    vor.clear()
    r.positionen[0].beschreibung = "Beratung (korrigiert)"
    db.commit()
    assert [(e, a) for e, a, _ in vor] == [("invoice", "update")]
    assert vor[0][2]["positionen"][0]["beschreibung"] == "Beratung (korrigiert)"
    db.close()


def test_loeschen_kann_verhindert_werden(sf):
    db = sf()
    with ereignisse.ohne_plugins():
        db.add(rechnung(notizen="abbrechen"))
        db.commit()
    r = db.query(Rechnung).one()
    db.delete(r)
    with pytest.raises(laufzeit.PluginAbbruch):
        db.commit()
    db.rollback()
    assert db.query(Rechnung).count() == 1
    db.close()


def test_anlegen_und_loeschen_in_einer_transaktion(sf, spion):
    vor, nach = spion
    db = sf()
    k = kunde(notizen="unveraendert")
    db.add(k)
    db.flush()
    db.delete(k)
    db.commit()
    assert vor == [] and nach == []
    db.close()
