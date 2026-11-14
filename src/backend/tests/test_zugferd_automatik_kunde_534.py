"""
Issue #534-Folgefund: Die ZUGFeRD-Automatik (Firmenname + USt-IdNr./Steuernummer → E-Rechnung an)
galt nur im Kundenformular. Per CSV-Datenübernahme angelegte Kunden bekamen zugferd_aktiv=0.
Jetzt setzt das Backend den Schalter beim Anlegen, Ändern und Importieren; Migration 186 zieht
Bestandskunden nach.
"""
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import main
from api.datenmigration import _kunde_anlegen
from api.kunden import create_kunde, update_kunde
from api.schemas import KundeCreate, KundeUpdate
from database.connection import Base
from database.models import Kunde


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_anlegen_mit_firma_und_steuernummer_schaltet_ein(db):
    k = create_kunde(KundeCreate(firmenname="Muster GmbH", ust_idnr="DE123456789"), db)
    assert k.zugferd_aktiv is True


def test_privatkunde_bleibt_aus_und_manuell_waehlbar(db):
    k = create_kunde(KundeCreate(vorname="Erika", nachname="Muster"), db)
    assert k.zugferd_aktiv is False
    k2 = create_kunde(KundeCreate(firmenname="Ohne Nummer GmbH", zugferd_aktiv=True), db)
    assert k2.zugferd_aktiv is True
    k3 = update_kunde(k2.id, KundeUpdate(zugferd_aktiv=False), db)
    assert k3.zugferd_aktiv is False


def test_aendern_schaltet_ein_und_laesst_sich_nicht_abschalten(db):
    k = create_kunde(KundeCreate(firmenname="Muster GmbH"), db)
    assert k.zugferd_aktiv is False
    k = update_kunde(k.id, KundeUpdate(ust_idnr="12/345/67890"), db)
    assert k.zugferd_aktiv is True
    k = update_kunde(k.id, KundeUpdate(zugferd_aktiv=False), db)
    assert k.zugferd_aktiv is True


def test_csv_import_neu_und_ueberschreiben(db):
    _kunde_anlegen(db, {"firmenname": "Import GmbH", "ust_idnr": "DE123456789"})
    _kunde_anlegen(db, {"vorname": "Max", "nachname": "Privat"})
    db.commit()
    assert db.query(Kunde).filter_by(firmenname="Import GmbH").one().zugferd_aktiv is True
    privat = db.query(Kunde).filter_by(nachname="Privat").one()
    assert privat.zugferd_aktiv is False

    # Überschreiben: einschalten wenn Daten passen, manuell gesetzten Schalter nie abschalten
    privat.zugferd_aktiv = True
    db.commit()
    _kunde_anlegen(db, {"vorname": "Max", "nachname": "Privat"}, ueberschreiben_id=privat.id)
    db.commit()
    db.refresh(privat)
    assert privat.zugferd_aktiv is True


def test_migration_186_zieht_bestandskunden_nach(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "alt.db"
    eng = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(main, "engine", eng)
    monkeypatch.setattr(main, "DB_PATH", db_path)
    Base.metadata.create_all(bind=eng)
    with eng.connect() as con:
        con.execute(text(
            "INSERT INTO kunden (firmenname, ust_idnr, zugferd_aktiv, aktiv, land) VALUES "
            "('Firma GmbH', 'DE123456789', 0, 1, 'DE'), "
            "('Ohne Nummer GmbH', NULL, 0, 1, 'DE'), "
            "(NULL, 'DE999999999', 0, 1, 'DE')"
        ))
        con.execute(text("PRAGMA user_version = 185"))
        con.commit()

    main._run_migrations()

    with eng.connect() as con:
        werte = con.execute(text("SELECT zugferd_aktiv FROM kunden ORDER BY id")).scalars().all()
    assert werte == [1, 0, 0]
