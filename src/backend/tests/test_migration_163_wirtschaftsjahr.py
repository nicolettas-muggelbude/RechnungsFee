"""
Regressionstest für Migration 163 (Issue #404): unternehmen.wirtschaftsjahr_abweichend_aktiv
neu, Default 0 - reiner Opt-in-Schalter, ändert am bestehenden Verhalten nichts, solange er
nicht aktiv gesetzt wird.
"""
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import main
from database.connection import Base
from database.models import Unternehmen


def make_engine(db_path: Path):
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


def test_neue_spalte_wird_mit_default_0_angelegt(tmp_path, monkeypatch):
    db_path = tmp_path / "alt.db"
    eng = make_engine(db_path)
    monkeypatch.setattr(main, "engine", eng)
    monkeypatch.setattr(main, "DB_PATH", db_path)

    Base.metadata.create_all(bind=eng)
    Session = sessionmaker(bind=eng)
    session = Session()
    session.add(Unternehmen(firmenname="Testbetrieb", strasse="Musterweg", hausnummer="1", plz="12345", ort="Musterstadt"))
    session.commit()
    session.close()
    with eng.connect() as con:
        con.execute(text("PRAGMA user_version = 162"))
        con.commit()

    main._run_migrations()

    with eng.connect() as con:
        cols = {r[1] for r in con.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
        wert = con.execute(text("SELECT wirtschaftsjahr_abweichend_aktiv FROM unternehmen")).scalar()

    assert "wirtschaftsjahr_abweichend_aktiv" in cols
    assert wert == 0
    assert main.SCHEMA_VERSION >= 163


def test_leere_datenbank_migriert_fehlerfrei(tmp_path, monkeypatch):
    """Frische Installation ohne unternehmen-Zeile darf nicht crashen (Setup-Wizard-Pflicht
    check, CLAUDE.md)."""
    db_path = tmp_path / "leer.db"
    eng = make_engine(db_path)
    monkeypatch.setattr(main, "engine", eng)
    monkeypatch.setattr(main, "DB_PATH", db_path)

    Base.metadata.create_all(bind=eng)
    with eng.connect() as con:
        con.execute(text("PRAGMA user_version = 0"))
        con.commit()

    main._run_migrations()  # darf nicht raisen

    with eng.connect() as con:
        cols = {r[1] for r in con.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
    assert "wirtschaftsjahr_abweichend_aktiv" in cols
