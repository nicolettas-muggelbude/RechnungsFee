import sqlite3

import main
from sqlalchemy import create_engine


def test_migration_172_adds_import_quelle_to_existing_database(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE rechnungen (id INTEGER PRIMARY KEY, typ TEXT NOT NULL)")
        conn.execute("PRAGMA user_version = 171")

    engine = create_engine(f"sqlite:///{db_path}")
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "DB_PATH", db_path)

    main._run_migrations()

    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(rechnungen)")}
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert "import_quelle" in columns
    assert version == main.SCHEMA_VERSION
