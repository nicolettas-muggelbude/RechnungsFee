"""
Issue #592: Rechnungspostfach regelmäßig im Hintergrund abrufen (unternehmen.imap_intervall_minuten,
Migration 198; 0 = aus, sonst 15/30/60). Der Abruf selbst läuft im Frontend, hier Schema und Migration.
"""
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, text

import main
from api.schemas import UnternehmenBase
from database.connection import Base

PFLICHT = {"firmenname": "T", "strasse": "S", "hausnummer": "1", "plz": "12345", "ort": "O"}


def _unt(**kw):
    return UnternehmenBase.model_validate({**PFLICHT, **kw})


@pytest.mark.parametrize("minuten", [0, 15, 30, 60])
def test_erlaubte_intervalle(minuten):
    assert _unt(imap_intervall_minuten=minuten).imap_intervall_minuten == minuten


@pytest.mark.parametrize("minuten", [-1, 1, 5, 45, 120])
def test_andere_intervalle_abgelehnt(minuten):
    with pytest.raises(ValidationError):
        _unt(imap_intervall_minuten=minuten)


def test_standard_aus():
    assert _unt().imap_intervall_minuten == 0


def test_migration_198(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE unternehmen DROP COLUMN imap_intervall_minuten"))
        conn.execute(text("PRAGMA user_version = 197"))
    monkeypatch.setattr(main, "engine", engine)
    main._run_migrations()
    with engine.begin() as conn:
        spalten = {r[1]: r for r in conn.execute(text("PRAGMA table_info(unternehmen)"))}
        assert spalten["imap_intervall_minuten"][4] == "0"  # DB-Default
        assert conn.execute(text("PRAGMA user_version")).scalar() == main.SCHEMA_VERSION
        conn.execute(text("PRAGMA user_version = 197"))
    main._run_migrations()  # zweiter Lauf ändert nichts
