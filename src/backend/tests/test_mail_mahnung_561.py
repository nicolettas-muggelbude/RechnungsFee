"""
Issue #561: eigene Mailvorlage für Mahnungen - unternehmen.mail_betreff_mahnung/mail_text_mahnung
(Migration 194). Speichern über die Stammdaten-API (UnternehmenBase) und Migration.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import main
from api.schemas import UnternehmenBase
from database.connection import Base
from database.models import Unternehmen


def test_felder_im_schema_und_modell():
    felder = UnternehmenBase.model_fields
    assert "mail_betreff_mahnung" in felder and "mail_text_mahnung" in felder
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="1", ort="O",
                       mail_betreff_mahnung="{bezeichnung} {rechnungsnummer}", mail_text_mahnung="Hallo {kunde}"))
    db.commit()
    u = db.query(Unternehmen).one()
    assert (u.mail_betreff_mahnung, u.mail_text_mahnung) == ("{bezeichnung} {rechnungsnummer}", "Hallo {kunde}")


def test_migration_194(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE unternehmen DROP COLUMN mail_betreff_mahnung"))
        conn.execute(text("ALTER TABLE unternehmen DROP COLUMN mail_text_mahnung"))
        conn.execute(text("PRAGMA user_version = 193"))
    monkeypatch.setattr(main, "engine", engine)
    main._run_migrations()
    with engine.begin() as conn:
        spalten = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)"))}
        assert {"mail_betreff_mahnung", "mail_text_mahnung"} <= spalten
        assert conn.execute(text("PRAGMA user_version")).scalar() == main.SCHEMA_VERSION
        conn.execute(text("PRAGMA user_version = 193"))
    main._run_migrations()
