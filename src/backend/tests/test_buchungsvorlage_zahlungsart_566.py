"""
Issue #566: Buchungsvorlagen übernehmen beim Buchen das gewählte Konto (bisher ignoriert →
falsches DATEV-Gegenkonto), eine eigene Zahlungsart (bisher fest „Bank“) und bei Einnahmen den
Kunden. Bar-Ausgaben prüfen den Kassenbestand wie das Journal. Migration 191.
"""
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import main
from api.buchungsvorlagen import (
    BuchenRequest, BuchungsvorlageCreate, BuchungsvorlageUpdate, aktualisiere_vorlage, buche_vorlage,
    erstelle_vorlage,
)
from database.connection import Base
from database.models import Journaleintrag, Konto, Kunde


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Konto(name="Giro", anbieter="Bank", kontoart="bank"))
    session.add(Kunde(firmenname="Verein e. V.", strasse="Str", hausnummer="1", plz="12345", ort="Ort"))
    session.commit()
    yield session
    session.close()


def _anlegen(db, **kw):
    daten = dict(bezeichnung="Honorar", betrag=Decimal("300"), naechstes_datum=date(2026, 11, 1),
                 art="Einnahme", modus="direkt")
    daten.update(kw)
    return erstelle_vorlage(BuchungsvorlageCreate(**daten), db)


def _buchen(db, v) -> Journaleintrag:
    buche_vorlage(v.id, data=BuchenRequest(), db=db)
    return db.query(Journaleintrag).filter(Journaleintrag.buchungsvorlage_id == v.id).order_by(
        Journaleintrag.id.desc()).first()


def test_konto_und_kunde_werden_uebernommen(db):
    konto = db.query(Konto).one()
    kunde = db.query(Kunde).one()
    v = _anlegen(db, konto_id=konto.id, kunde_id=kunde.id)
    assert v.zahlungsart == "Bank" and v.kunde_name == "Verein e. V."
    e = _buchen(db, v)
    assert (e.zahlungsart, e.konto_id, e.kunde_id) == ("Bank", konto.id, kunde.id)


def test_zahlungsart_paypal(db):
    v = _anlegen(db, zahlungsart="PayPal")
    assert _buchen(db, v).zahlungsart == "PayPal"


def test_bar_ohne_konto(db):
    konto = db.query(Konto).one()
    v = _anlegen(db, zahlungsart="Bar", konto_id=konto.id)
    e = _buchen(db, v)
    assert (e.zahlungsart, e.konto_id) == ("Bar", None)


def test_bar_ausgabe_braucht_kassenbestand(db):
    v = _anlegen(db, art="Ausgabe", zahlungsart="Bar", bezeichnung="Reinigung")
    with pytest.raises(HTTPException) as exc:
        buche_vorlage(v.id, data=BuchenRequest(), db=db)
    assert exc.value.status_code == 409
    # mit Bar-Einnahme im Kassenbuch klappt es
    _buchen(db, _anlegen(db, zahlungsart="Bar", betrag=Decimal("500")))
    assert _buchen(db, v).zahlungsart == "Bar"


def test_kunde_nur_bei_einnahme(db):
    kunde = db.query(Kunde).one()
    with pytest.raises(HTTPException):
        _anlegen(db, art="Ausgabe", kunde_id=kunde.id)
    v = _anlegen(db, kunde_id=kunde.id)
    v2 = aktualisiere_vorlage(v.id, BuchungsvorlageUpdate(art="Ausgabe"), db)
    assert v2.kunde_id is None


def test_ungueltige_zahlungsart(db):
    with pytest.raises(HTTPException):
        _anlegen(db, zahlungsart="Scheck")


def test_migration_191(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        # Alte Tabelle ohne die neuen Spalten (DROP COLUMN geht bei FK-Spalten in SQLite nicht)
        conn.execute(text("DROP TABLE buchungsvorlagen"))
        conn.execute(text(
            "CREATE TABLE buchungsvorlagen (id INTEGER PRIMARY KEY, bezeichnung VARCHAR(200) NOT NULL, "
            "konto_id INTEGER, betrag NUMERIC(12,2) NOT NULL, art VARCHAR(20) NOT NULL DEFAULT 'Ausgabe')"))
        conn.execute(text("INSERT INTO buchungsvorlagen (bezeichnung, betrag) VALUES ('Miete', 500)"))
        conn.execute(text("PRAGMA user_version = 190"))
    monkeypatch.setattr(main, "engine", engine)
    main._run_migrations()
    with engine.begin() as conn:
        assert conn.execute(text("SELECT zahlungsart, kunde_id FROM buchungsvorlagen")).one() == ("Bank", None)
        assert conn.execute(text("PRAGMA user_version")).scalar() == main.SCHEMA_VERSION
        conn.execute(text("PRAGMA user_version = 190"))
    main._run_migrations()  # zweiter Lauf ohne Fehler
