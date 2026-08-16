"""Regressionstest für Migration 148 (Issue #348): neue Spalten backup_extern_pfad_1/2_lokal_ok."""
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine

import main
from database.connection import Base


def make_engine(db_path: Path):
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


def test_bestehende_db_erhaelt_lokal_ok_spalten(tmp_path, monkeypatch):
    db_path = tmp_path / "alt.db"
    eng = make_engine(db_path)
    monkeypatch.setattr(main, "engine", eng)
    monkeypatch.setattr(main, "DB_PATH", db_path)

    Base.metadata.create_all(bind=eng)
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA user_version = 147")
    con.commit()
    con.close()

    main._run_migrations()

    con = sqlite3.connect(str(db_path))
    cols = {r[1] for r in con.execute("PRAGMA table_info(unternehmen)").fetchall()}
    con.close()
    assert "backup_extern_pfad_1_lokal_ok" in cols
    assert "backup_extern_pfad_2_lokal_ok" in cols
    assert main.SCHEMA_VERSION >= 148
