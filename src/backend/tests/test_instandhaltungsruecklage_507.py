"""
Issue #507: Systemkategorie „Instandhaltungsrücklage (WEG)“ – Rücklagen-Anteil des Hausgelds ist
beim Bezahlen keine Betriebsausgabe (Vermögen bei der WEG), wird aber gebucht und im DATEV-Export
auf „Sonstige Vermögensgegenstände“ (SKR03 1500 / SKR04 1300) ausgewiesen.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from api.datev import _sachkonto
from api.euer import _berechne_euer
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Unternehmen
from database.seed import seed_kategorien

NAME = "Instandhaltungsrücklage (WEG)"


def _db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)()


def test_neuinstallation_legt_kategorie_an():
    _, db = _db()
    seed_kategorien(db)
    kat = db.query(Kategorie).filter(Kategorie.name == NAME).one()
    assert (kat.kontenart, kat.konto_skr03, kat.konto_skr04, kat.euer_zeile) == ("Aufwand", "1500", "1300", None)
    assert kat.vorsteuer_prozent == 0
    assert "Jahresabrechnung" in kat.beschreibung


def test_bestehende_db_bekommt_kategorie_ueber_migrate_kategorien(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.db'}")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "SessionLocal", sessionmaker(bind=engine))
    main._migrate_kategorien()
    with sessionmaker(bind=engine)() as db:
        assert db.query(Kategorie).filter(Kategorie.name == NAME).count() == 1
    main._migrate_kategorien()  # idempotent
    with sessionmaker(bind=engine)() as db:
        assert db.query(Kategorie).filter(Kategorie.name == NAME).count() == 1


def test_ruecklage_ohne_wirkung_auf_euer_und_datev_konto():
    _, db = _db()
    db.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O", kontenrahmen="SKR03"))
    seed_kategorien(db)
    kat = db.query(Kategorie).filter(Kategorie.name == NAME).one()
    e = Journaleintrag(
        datum=date(2026, 3, 1), belegnr="J-1", beschreibung="Hausgeld März – Rücklage", kategorie_id=kat.id,
        konto_skr03=kat.konto_skr03, konto_skr04=kat.konto_skr04, zahlungsart="Bank", art="Ausgabe",
        netto_betrag=Decimal("80.00"), ust_satz=Decimal("0"), ust_betrag=Decimal("0"),
        vorsteuer_betrag=Decimal("0"), brutto_betrag=Decimal("80.00"),
    )
    db.add(e)
    db.commit()
    euer = _berechne_euer(2026, db)
    assert euer["summe_ausgaben"] == Decimal("0.00")
    assert euer["nicht_zugeordnet"] == []
    assert _sachkonto(e, "SKR03", db) == "1500"
