"""
Regressionstest für Migration 154 (Issue #147): unternehmen.thunderbird_aktiv.
"""
from pathlib import Path

from sqlalchemy import create_engine, text

import main
from database.connection import Base


def make_engine(db_path: Path):
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


def test_bestehende_db_erhaelt_thunderbird_aktiv_spalte(tmp_path, monkeypatch):
    db_path = tmp_path / "alt.db"
    eng = make_engine(db_path)
    monkeypatch.setattr(main, "engine", eng)
    monkeypatch.setattr(main, "DB_PATH", db_path)

    Base.metadata.create_all(bind=eng)
    with eng.connect() as con:
        con.execute(text("PRAGMA user_version = 153"))
        con.commit()

    main._run_migrations()

    with eng.connect() as con:
        info = {r[1]: r for r in con.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}

    assert "thunderbird_aktiv" in info
    assert info["thunderbird_aktiv"][3] == 1  # notnull
    assert str(info["thunderbird_aktiv"][4]).strip("'") == "0"  # dflt_value
    assert main.SCHEMA_VERSION >= 154
