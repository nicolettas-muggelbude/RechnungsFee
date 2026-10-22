import sqlite3

import main
from database.connection import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_fresh_schema_contains_import_mapping_vorlagen(tmp_path, monkeypatch):
    db_path = tmp_path / "fresh.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "DB_PATH", db_path)

    main._run_migrations()

    with sqlite3.connect(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert "import_mapping_vorlagen" in tables
    assert version == main.SCHEMA_VERSION
    from api.datenmigration import mapping_vorlagen_liste
    with sessionmaker(bind=engine)() as session:
        assert mapping_vorlagen_liste(db=session) == []


def test_migration_173_creates_import_mapping_vorlagen_for_version_172(tmp_path, monkeypatch):
    db_path = tmp_path / "version_172.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE rechnungen (id INTEGER PRIMARY KEY)")
        conn.execute("PRAGMA user_version = 172")

    engine = create_engine(f"sqlite:///{db_path}")
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "DB_PATH", db_path)

    main._run_migrations()

    with sqlite3.connect(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert "import_mapping_vorlagen" in tables
    assert version == main.SCHEMA_VERSION
    from api.datenmigration import mapping_vorlagen_liste
    with sessionmaker(bind=engine)() as session:
        assert mapping_vorlagen_liste(db=session) == []
