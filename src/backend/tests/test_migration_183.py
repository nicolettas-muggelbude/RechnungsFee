"""
Migration 183 (Issue #497): rechnungen.ausfall_datum für den Forderungsausfall nach §17 Abs. 2 Nr. 1
UStG. Bereits ausgebuchte Rechnungen bleiben ohne Datum.
"""
from datetime import date

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import main
from database.connection import Base
from database.models import Rechnung


def _alte_db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.db'}")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        session.add(Rechnung(typ="ausgang", datum=date(2026, 3, 1), zahlungsstatus="uneinbringlich"))
        session.commit()
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE rechnungen DROP COLUMN ausfall_datum"))
        conn.execute(text("PRAGMA user_version = 182"))
    monkeypatch.setattr(main, "engine", engine)
    return engine


def test_migration_183_legt_ausfall_datum_an(tmp_path, monkeypatch):
    engine = _alte_db(tmp_path, monkeypatch)
    main._run_migrations()
    with engine.connect() as conn:
        spalten = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)"))}
        version = conn.execute(text("PRAGMA user_version")).scalar()
        alt = conn.execute(text("SELECT zahlungsstatus, ausfall_datum FROM rechnungen")).one()
    assert version == main.SCHEMA_VERSION
    assert "ausfall_datum" in spalten
    assert tuple(alt) == ("uneinbringlich", None)


def test_migration_183_zweiter_lauf_ohne_fehler(tmp_path, monkeypatch):
    engine = _alte_db(tmp_path, monkeypatch)
    main._run_migrations()
    with engine.begin() as conn:
        conn.execute(text("PRAGMA user_version = 182"))
    main._run_migrations()
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA user_version")).scalar() == main.SCHEMA_VERSION
