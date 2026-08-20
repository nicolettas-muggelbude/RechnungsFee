"""Regressionstest für Migration 149 (Issue #358): ust_idnr_validiert/-datum für Lieferanten
neu, ust_idnr_validierung_datum für Kunden nachgerüstet (Spalte fehlte bislang komplett)."""
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine

import main
from database.connection import Base


def make_engine(db_path: Path):
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


def test_bestehende_db_erhaelt_ust_idnr_validiert_spalten(tmp_path, monkeypatch):
    db_path = tmp_path / "alt.db"
    eng = make_engine(db_path)
    monkeypatch.setattr(main, "engine", eng)
    monkeypatch.setattr(main, "DB_PATH", db_path)

    Base.metadata.create_all(bind=eng)
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA user_version = 148")
    con.commit()
    con.close()

    main._run_migrations()

    con = sqlite3.connect(str(db_path))
    kunden_cols = {r[1] for r in con.execute("PRAGMA table_info(kunden)").fetchall()}
    lieferanten_cols = {r[1] for r in con.execute("PRAGMA table_info(lieferanten)").fetchall()}
    con.close()
    assert "ust_idnr_validierung_datum" in kunden_cols
    assert "ust_idnr_validiert" in lieferanten_cols
    assert "ust_idnr_validierung_datum" in lieferanten_cols
    assert main.SCHEMA_VERSION >= 149
