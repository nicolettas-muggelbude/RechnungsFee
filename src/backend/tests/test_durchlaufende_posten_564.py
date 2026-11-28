"""
Issue #564: Systemkategorie „Durchlaufende Posten“ (SKR03 1590 / SKR04 1370, Kontenart Neutral) -
bei Einnahme und Ausgabe wählbar, z. B. für eine doppelt erhaltene und zurücküberwiesene Zahlung.
Zählt weder in der EÜR noch in der UStVA (auch nicht in KZ 48 bei Kleinunternehmern).
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from api.euer import _berechne_euer
from api.journal import _felder_aus_data
from api.schemas import JournalEintragCreate
from api.ustva import _berechne_ku_kz48, _berechne_kz
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Unternehmen
from database.seed import seed_kategorien

NAME = "Durchlaufende Posten"


def _db(ku=False):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O",
                       kontenrahmen="SKR03", ist_kleinunternehmer=ku))
    seed_kategorien(db)
    db.commit()
    return db


def _buche(db, art, nr, ust_satz="19"):
    kat = db.query(Kategorie).filter(Kategorie.name == NAME).one()
    data = JournalEintragCreate(datum=date(2026, 11, 10), beschreibung="Doppelzahlung", kategorie_id=kat.id,
                                zahlungsart="Bank", art=art, brutto_betrag=Decimal("119.00"),
                                ust_satz=Decimal(ust_satz), vorsteuerabzug=True)
    e = Journaleintrag(belegnr=f"J-{nr}", **_felder_aus_data(data, db))
    db.add(e)
    db.commit()
    return e


def test_neuinstallation_legt_kategorie_an():
    db = _db()
    kat = db.query(Kategorie).filter(Kategorie.name == NAME).one()
    assert (kat.kontenart, kat.konto_skr03, kat.konto_skr04, kat.euer_zeile) == ("Neutral", "1590", "1370", None)
    assert kat.ust_satz_standard == 0 and kat.vorsteuer_prozent == 0


def test_bestehende_db_bekommt_kategorie(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.db'}")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "SessionLocal", sessionmaker(bind=engine))
    main._migrate_kategorien()
    main._migrate_kategorien()  # idempotent
    with sessionmaker(bind=engine)() as db:
        assert db.query(Kategorie).filter(Kategorie.name == NAME).count() == 1


def test_buchung_ohne_ust_und_ohne_wirkung_auf_euer_und_ustva():
    db = _db()
    ein = _buche(db, "Einnahme", 1)
    aus = _buche(db, "Ausgabe", 2)
    for e in (ein, aus):
        assert e.ust_satz == 0 and e.ust_betrag == 0 and e.vorsteuer_betrag == 0
        assert e.netto_betrag == Decimal("119.00")
    euer = _berechne_euer(2026, db)
    assert euer["summe_einnahmen"] == Decimal("0.00")
    assert euer["summe_ausgaben"] == Decimal("0.00")
    assert euer["nicht_zugeordnet"] == []
    kz, _ = _berechne_kz(date(2026, 11, 1), date(2026, 11, 30), db)
    assert all(v == 0 for v in kz.values())


def test_kleinunternehmer_kz48_ohne_durchlaufende_posten():
    db = _db(ku=True)
    _buche(db, "Einnahme", 1, ust_satz="0")
    assert _berechne_ku_kz48(date(2026, 1, 1), date(2026, 12, 31), db) == Decimal("0.00")
