"""
Regressionstest für Migration 155 (Issue #379): bank_transaktionen.ignoriert.
"""
from pathlib import Path

from sqlalchemy import create_engine, text

import main
from database.connection import Base


def make_engine(db_path: Path):
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


def test_bestehende_db_erhaelt_ignoriert_spalte(tmp_path, monkeypatch):
    db_path = tmp_path / "alt.db"
    eng = make_engine(db_path)
    monkeypatch.setattr(main, "engine", eng)
    monkeypatch.setattr(main, "DB_PATH", db_path)

    Base.metadata.create_all(bind=eng)
    with eng.connect() as con:
        con.execute(text("PRAGMA user_version = 154"))
        con.commit()

    main._run_migrations()

    with eng.connect() as con:
        info = {r[1]: r for r in con.execute(text("PRAGMA table_info(bank_transaktionen)")).fetchall()}

    assert "ignoriert" in info
    assert info["ignoriert"][3] == 1  # notnull
    assert main.SCHEMA_VERSION >= 155
