"""Host-CRUD: gemeinsame Core-Regeln, Savepoints, Audit und Hook-/Commit-Grenzen."""
import json
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import Artikel, Beleg, Kunde, Nummernkreis, PluginProtokoll, Rechnung, UstSatz
from plugins import debug_plugin, ereignisse, laufzeit, registry
from plugins.host_api import HostApiFehler
from plugins.schreiben import DatenZugriff

ID = 'de.test.schreiber'


@pytest.fixture
def sf(tmp_path, monkeypatch):
    monkeypatch.setenv('RECHNUNGSFEE_PLUGIN_DIR', str(tmp_path / 'plugins'))
    monkeypatch.setattr(debug_plugin, '_instanz', debug_plugin.DebugPlugin(tmp_path))
    engine = create_engine(f'sqlite:///{tmp_path / "test.db"}', connect_args={'check_same_thread': False})
    @event.listens_for(engine, 'connect')
    def fk(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    ereignisse.registrieren(factory)
    laufzeit.konfiguriere(factory)
    registry.status_geaendert()
    with factory() as db:
        db.add_all([UstSatz(satz=Decimal('19'), bezeichnung='19%', ist_aktiv=True),
                    Nummernkreis(typ='kunde', bezeichnung='Kunden', format='KD-####', naechste_nr=1),
                    Nummernkreis(typ='debitor', bezeichnung='Debitor', format='####', naechste_nr=10000),
                    Nummernkreis(typ='artikel', bezeichnung='Artikel', format='ART-####', naechste_nr=1),
                    Nummernkreis(typ='rechnung_ausgang', bezeichnung='Rechnung', format='RE-####', naechste_nr=1)])
        db.commit()
    yield factory
    laufzeit.warte_auf_hintergrund()
    laufzeit.konfiguriere(None)
    engine.dispose()


def host(sf):
    return DatenZugriff(session_factory=sf)


def kunde(h, **werte):
    return json.loads(h.create(ID, 'customer', json.dumps({'nachname': 'Test', **werte})))


def artikel(h, **werte):
    return json.loads(h.create(ID, 'article', json.dumps({
        'typ': 'artikel', 'bezeichnung': 'Testartikel', 'vk_brutto': '119.00', **werte})))


def rechnung(h, **werte):
    return json.loads(h.create(ID, 'invoice', json.dumps({
        'typ': 'ausgang', 'partner_freitext': 'Test', 'datum': '2026-10-28',
        'positionen': [{'beschreibung': 'Leistung', 'netto': '100.00', 'ust_satz': '19'}], **werte})))


def test_kunde_crud_core_nummern_partial_update_und_audit(sf):
    h = host(sf)
    k = kunde(h, land='AT', ist_verein=True)
    assert k['kundennummer'] == 'KD-0001'
    neu = json.loads(h.update(ID, 'customer', str(k['id']), '{"ort":"Wien"}'))
    assert neu['ort'] == 'Wien' and neu['land'] == 'AT' and neu['ist_verein'] is True
    h.delete(ID, 'customer', str(k['id']))
    with sf() as db:
        assert db.get(Kunde, k['id']) is None
        assert [p.hook for p in db.query(PluginProtokoll).order_by(PluginProtokoll.id)] == [
            'host:customer:create', 'host:customer:update', 'host:customer:delete']


def test_artikel_core_preise_und_loeschsperre(sf):
    h = host(sf)
    a = artikel(h)
    assert Decimal(a['vk_netto']) == Decimal('100')
    neu = json.loads(h.update(ID, 'article', str(a['id']), '{"vk_brutto":"238.00"}'))
    assert Decimal(neu['vk_netto']) == Decimal('200')
    h.delete(ID, 'article', str(a['id']))
    a = artikel(h, lager_aktiv=True, bestand_aktuell='2')
    with pytest.raises(HostApiFehler, match='Lagerbestand'):
        h.delete(ID, 'article', str(a['id']))
    with sf() as db:
        assert db.get(Artikel, a['id']).bestand_aktuell == 2


def test_rechnung_crud_berechnete_summen_und_core_nummern(sf):
    h = host(sf)
    r = rechnung(h)
    assert r['rechnungsnummer'] == 'RE-0001'
    assert r['ist_entwurf'] and Decimal(r['brutto_gesamt']) == Decimal('119')
    neu = json.loads(h.update(ID, 'invoice', str(r['id']), json.dumps({
        'positionen': [{'beschreibung': 'Neu', 'netto': '50', 'menge': '2', 'ust_satz': '19'}]})))
    assert Decimal(neu['brutto_gesamt']) == Decimal('119')
    h.delete(ID, 'invoice', str(r['id']))
    with sf() as db:
        assert db.get(Rechnung, r['id']) is None


@pytest.mark.parametrize('flag', ['ist_entwurf', 'immutable', 'ausgegeben', 'storniert'])
def test_gobd_sperrt_update_und_delete(sf, flag):
    h = host(sf)
    r = rechnung(h)
    with sf() as db:
        setattr(db.get(Rechnung, r['id']), flag, False if flag == 'ist_entwurf' else True)
        db.commit()
    for aktion in [lambda: h.update(ID, 'invoice', str(r['id']), '{"notizen":"Nein"}'),
                   lambda: h.delete(ID, 'invoice', str(r['id']))]:
        with pytest.raises(HostApiFehler, match='unveränderlich'):
            aktion()


@pytest.mark.parametrize('entity,payload', [
    ('customer', '{"kundennummer":"fremd"}'), ('customer', '{"id":42}'),
    ('customer', '{"_schema":"customer@99"}'), ('customer', '[]'), ('customer', '{defekt'),
    ('article', '{"vk_brutto":"NaN"}'), ('invoice', '{"ist_entwurf":false}'),
    ('invoice', '{"ist_entwurf":0}'), ('invoice', '{"brutto_gesamt":"1"}'),
    ('invoice', '{"positionen":[{"netto":"1","ust_betrag":"0"}]}'),
    ('invoice', '{"netto_gesamt_override":"0"}'), ('invoice', '{"rechnungsnummer":"RE-MANUELL"}'),
])
def test_ungueltige_und_geschuetzte_payloads(sf, entity, payload):
    with pytest.raises(HostApiFehler) as exc:
        host(sf).create(ID, entity, payload)
    assert exc.value.art == 'validation-error'
    with sf() as db:
        assert db.query(PluginProtokoll).count() == 0


def test_fehlende_ids_referenzen_und_schreibgeschuetzte_entitaeten(sf):
    h = host(sf)
    for id in ['0', '-1', 'abc', '1.5', '9' * 5000, '9999999999999999999']:
        with pytest.raises(HostApiFehler) as exc:
            h.delete(ID, 'customer', id)
        assert exc.value.art == 'validation-error'
    with pytest.raises(HostApiFehler) as exc:
        h.delete(ID, 'customer', '999')
    assert exc.value.art == 'not-found'
    with pytest.raises(HostApiFehler) as exc:
        rechnung(h, kunde_id=999)
    assert exc.value.art == 'not-found'
    with pytest.raises(HostApiFehler, match='schreibgeschützt'):
        h.delete(ID, 'voucher', '1')
    with pytest.raises(HostApiFehler, match='noch nicht'):
        h.create(ID, 'task', '{}')


def test_kunde_mit_rechnung_kann_nicht_geloescht_werden(sf):
    h = host(sf)
    k = kunde(h)
    rechnung(h, kunde_id=k['id'])
    with pytest.raises(HostApiFehler, match='verknüpfte'):
        h.delete(ID, 'customer', str(k['id']))


def test_pre_host_schreiben_bleibt_bis_outer_commit_und_rollback_nimmt_nummer_zurueck(sf):
    with sf() as db:
        h = DatenZugriff(session=db)
        k = kunde(h)
        with sf() as andere:
            assert andere.query(Kunde).count() == 0
        db.rollback()
    with sf() as db:
        assert db.query(Kunde).count() == 0
        assert db.query(PluginProtokoll).count() == 0
        assert db.query(Nummernkreis).filter_by(typ='kunde').one().naechste_nr == 1
    assert kunde(host(sf))['kundennummer'] == k['kundennummer']


def test_fehler_in_host_aufruf_rollt_nur_savepoint_zurueck(sf, monkeypatch):
    from api import kunden
    original = kunden._create_kunde
    def kaputt(data, db, **kw):
        original(data, db, **kw)
        raise HostApiFehler('validation-error', 'Nach dem Flush abgewiesen')
    with sf() as db:
        h = DatenZugriff(session=db)
        erstes = kunde(h, nachname='Erstes')
        with monkeypatch.context() as m:
            m.setattr(kunden, '_create_kunde', kaputt)
            with pytest.raises(HostApiFehler):
                kunde(h, nachname='Verwerfen')
        zweites = kunde(h, nachname='Zweites')
        assert zweites['kundennummer'] == 'KD-0002'
        db.commit()
    with sf() as db:
        assert [k.nachname for k in db.query(Kunde).order_by(Kunde.id)] == ['Erstes', 'Zweites']
        assert db.query(PluginProtokoll).count() == 2


def test_host_rechte_werden_vor_schreiben_geprueft(sf):
    from wasmtime.component import Variant
    h = host(sf)
    token = laufzeit._kontext.set((laufzeit._Kontext(ID, {'customer': frozenset(['read'])}, h),))
    try:
        ergebnis = laufzeit._host_aufruf('create', 'customer', '{"nachname":"Nein"}')
        assert isinstance(ergebnis, Variant) and ergebnis.tag == 'unauthorized'
    finally:
        laufzeit._kontext.reset(token)
    with sf() as db:
        assert db.query(Kunde).count() == 0


def test_rekursionslimit_und_aktives_ziel(sf):
    h = host(sf)
    token = laufzeit._kontext.set(tuple(laufzeit._Kontext(ID, {}, h) for _ in range(laufzeit.MAX_VERSCHACHTELUNG)))
    try:
        with pytest.raises(HostApiFehler, match='Verschachtelung'):
            kunde(h)
    finally:
        laufzeit._kontext.reset(token)
    with sf() as db:
        k = kunde(DatenZugriff(session=db))
        db.info[ereignisse._ZIELE] = {('customer', k['id'])}
        with pytest.raises(HostApiFehler, match='gerade geprüft'):
            DatenZugriff(session=db).delete(ID, 'customer', str(k['id']))


def test_post_hooks_erst_nach_root_commit_und_mit_ausloeser(sf, monkeypatch):
    aufrufe = []
    monkeypatch.setattr(laufzeit, 'nach_aenderung', lambda *args, **kw: aufrufe.append((args, laufzeit._kontext.get())))
    with sf() as db:
        h = DatenZugriff(session=db)
        token = laufzeit._kontext.set((laufzeit._Kontext(ID, {}, h),))
        try:
            kunde(h)
        finally:
            laufzeit._kontext.reset(token)
        assert aufrufe == []
        db.commit()
    assert len(aufrufe) == 1 and aufrufe[0][1][0].plugin_id == ID
    aufrufe.clear()
    with sf() as db:
        kunde(DatenZugriff(session=db))
        db.rollback()
    assert aufrufe == []


def test_andere_pre_hooks_duerfen_host_schreiben_abweisen(sf, monkeypatch):
    def ablehnen(*args, **kw):
        raise laufzeit.PluginAbbruch('de.test.pruefer', 'Prüfer', 'Abgewiesen')
    monkeypatch.setattr(laufzeit, 'vor_aenderung', ablehnen)
    with pytest.raises(HostApiFehler, match='Abgewiesen'):
        kunde(host(sf))
    with sf() as db:
        assert db.query(Kunde).count() == 0 and db.query(PluginProtokoll).count() == 0


def test_loeschen_entfernt_dateien_erst_nach_commit(sf, tmp_path, monkeypatch):
    from api import rechnungen as api
    monkeypatch.setattr(api, 'APP_DATA_DIR', tmp_path)
    pfad = tmp_path / 'uploads/test.pdf'
    pfad.parent.mkdir()
    pfad.write_bytes(b'%PDF')
    with sf() as db:
        b = Beleg(dateiname='test.pdf', original_name='test.pdf', sha256='test')
        db.add(b)
        db.flush()
        r = Rechnung(typ='eingang', datum=date(2026, 10, 28), ist_entwurf=True, beleg_id=b.id)
        db.add(r)
        db.commit()
        rid = r.id
    with sf() as db:
        DatenZugriff(session=db).delete(ID, 'invoice', str(rid))
        assert pfad.exists()
        db.rollback()
    assert pfad.exists()
    with sf() as db:
        assert db.get(Rechnung, rid) is not None
        DatenZugriff(session=db).delete(ID, 'invoice', str(rid))
        assert pfad.exists()
        db.commit()
    assert not pfad.exists()


def test_pre_pipeline_schreibt_in_selber_transaktion_und_outer_abbruch_rollt_alles_zurueck(sf, monkeypatch):
    monkeypatch.setattr(laufzeit, 'irgendein_plugin', lambda: True)
    monkeypatch.setattr(laufzeit, 'hat_hooks', lambda *args: True)
    post = []
    monkeypatch.setattr(laufzeit, 'nach_aenderung', lambda *args, **kw: post.append(args))
    def pruefen(entity, action, payload, host, **kw):
        if entity == 'customer':
            artikel(host)
            if payload.get('notizen') == 'abbrechen':
                raise laufzeit.PluginAbbruch(ID, 'Test', 'Abbruch nach Host-Schreiben')
        return payload
    monkeypatch.setattr(laufzeit, 'vor_aenderung', pruefen)
    with sf() as db:
        db.add(Kunde(nachname='Verwerfen', notizen='abbrechen'))
        with pytest.raises(laufzeit.PluginAbbruch):
            db.commit()
        db.rollback()
    assert post == []
    with sf() as db:
        assert db.query(Artikel).count() == 0
        assert db.query(Kunde).count() == 0
        assert db.query(PluginProtokoll).count() == 0
        assert db.query(Nummernkreis).filter_by(typ='artikel').one().naechste_nr == 1
        db.add(Kunde(nachname='Behalten'))
        db.commit()
    assert [(e[0], e[1]) for e in post] == [('article', 'create'), ('customer', 'create')]
    with sf() as db:
        assert db.query(Artikel).count() == db.query(Kunde).count() == 1


def test_threadwechsel_erhaelt_plugin_vorfahren(sf):
    gesehen = []
    h = host(sf)
    token = laufzeit._kontext.set((laufzeit._Kontext(ID, {}, h),))
    try:
        laufzeit._hintergrund.auftrag(lambda: gesehen.append([k.plugin_id for k in laufzeit._kontext.get()]))
    finally:
        laufzeit._kontext.reset(token)
    laufzeit.warte_auf_hintergrund()
    assert gesehen == [[ID]]


def test_integrity_error_zerstoert_nicht_aeussere_transaktion(sf, monkeypatch):
    from api import kunden
    original = kunden._create_kunde
    with sf() as db:
        h = DatenZugriff(session=db)
        kunde(h, nachname='Erster')
        def doppelt(data, db, **kw):
            obj = original(data, db, **kw)
            obj.debitor_nr = db.query(Kunde).filter_by(nachname='Erster').one().debitor_nr
            db.flush()
        with monkeypatch.context() as m:
            m.setattr(kunden, '_create_kunde', doppelt)
            with pytest.raises(HostApiFehler, match='Datenbankregel'):
                kunde(h, nachname='Doppelt')
        kunde(h, nachname='Zweiter')
        db.commit()
    with sf() as db:
        assert [k.nachname for k in db.query(Kunde).order_by(Kunde.id)] == ['Erster', 'Zweiter']
        assert db.query(PluginProtokoll).count() == 2
