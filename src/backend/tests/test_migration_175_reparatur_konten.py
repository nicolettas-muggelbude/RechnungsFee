"""
Migration 175 (Issue #470): "Reparatur Anlagevermögen" von 4260/6335 (Instandhaltung betrieblicher
Räume) auf 4805/6470 (Reparatur andere Anlagen und BGA) - eigene Kontoanpassungen bleiben erhalten.
"""
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import main
from database.connection import Base
from database.models import Kategorie


def _db(tmp_path: Path, monkeypatch, user_modified_skr04: bool):
    db_path = tmp_path / "alt.db"
    eng = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(main, "engine", eng)
    monkeypatch.setattr(main, "DB_PATH", db_path)
    Base.metadata.create_all(bind=eng)
    with eng.connect() as con:
        s = Session(bind=con)
        s.add(Kategorie(name="Reparatur Anlagevermögen", kontenart="Aufwand", euer_zeile=60,
                        konto_skr03="4260", konto_skr04="9999" if user_modified_skr04 else "6335",
                        konto_skr03_default="4260", konto_skr04_default="6335",
                        user_modified_skr03=False, user_modified_skr04=user_modified_skr04))
        s.commit()
        s.close()
        con.execute(text("PRAGMA user_version = 174"))
        con.commit()
    return eng


def _konten(eng):
    with eng.connect() as con:
        return con.execute(text(
            "SELECT konto_skr03, konto_skr04, konto_skr03_default, konto_skr04_default FROM kategorien"
        )).one()


def test_konten_korrigiert(tmp_path, monkeypatch):
    eng = _db(tmp_path, monkeypatch, user_modified_skr04=False)
    main._run_migrations()
    assert tuple(_konten(eng)) == ("4805", "6470", "4805", "6470")


def test_eigene_anpassung_bleibt(tmp_path, monkeypatch):
    eng = _db(tmp_path, monkeypatch, user_modified_skr04=True)
    main._run_migrations()
    assert tuple(_konten(eng)) == ("4805", "9999", "4805", "6470")
