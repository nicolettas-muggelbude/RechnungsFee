"""
Integrations-Tests für _run_migrations() in main.py.

Szenarien:
  1. Frische DB (kein Schema, user_version=0) → vollständige Migration → version=2
  2. Alte DB (fehlende Spalten, user_version=0) → Spalten ergänzt, Backup, version=2
  3. DB auf version=1 → nur Bump auf 2, Backup vorhanden
  4. DB auf version=2 → Early-Return, kein Backup erstellt
  5. Backup-Rotation: max. 5 Backups werden behalten
  6. Idempotenz: zweiter Aufruf erstellt kein zweites Backup
"""

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine

import main


# ---------------------------------------------------------------------------
# Minimales altes Schema (vor den Spalten-Migrationen von version 0 → 1)
# ---------------------------------------------------------------------------

OLD_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS kunden (
    id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL
);
CREATE TABLE IF NOT EXISTS rechnungen (
    id INTEGER PRIMARY KEY,
    rechnungsnummer VARCHAR(50) NOT NULL,
    typ VARCHAR(10) NOT NULL,
    gesamtbetrag NUMERIC(12,2) NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS kassenbuch (
    id INTEGER PRIMARY KEY,
    buchungsdatum DATE NOT NULL,
    betrag NUMERIC(12,2) NOT NULL,
    beschreibung VARCHAR(500) NOT NULL,
    art VARCHAR(10) NOT NULL,
    immutable BOOLEAN NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS tagesabschluesse (
    id INTEGER PRIMARY KEY,
    datum DATE NOT NULL,
    immutable BOOLEAN NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS unternehmen (
    id INTEGER PRIMARY KEY,
    firmenname VARCHAR(200) NOT NULL,
    strasse VARCHAR(200) NOT NULL,
    hausnummer VARCHAR(20) NOT NULL,
    plz VARCHAR(10) NOT NULL,
    ort VARCHAR(100) NOT NULL
);
CREATE TABLE IF NOT EXISTS kategorien (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    kontenart VARCHAR(20) NOT NULL
);
"""


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def get_columns(db_path: Path, table: str) -> set[str]:
    con = sqlite3.connect(str(db_path))
    cols = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
    con.close()
    return cols


def get_user_version(db_path: Path) -> int:
    con = sqlite3.connect(str(db_path))
    v = con.execute("PRAGMA user_version").fetchone()[0]
    con.close()
    return v


def make_engine(db_path: Path):
    return create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )


def setup_old_db(db_path: Path, version: int = 0) -> None:
    """Legt eine DB mit altem Schema (vor Migrationen) und gegebener user_version an."""
    con = sqlite3.connect(str(db_path))
    con.executescript(OLD_SCHEMA_SQL)
    con.execute(f"PRAGMA user_version = {version}")
    con.commit()
    con.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMigrationen:

    def test_frische_db(self, tmp_path, monkeypatch):
        """Frische DB: create_all legt vollständiges Schema an, Migration bringt auf version=2."""
        db_path = tmp_path / "fresh.db"
        backup_dir = tmp_path / "backups"

        eng = make_engine(db_path)
        monkeypatch.setattr(main, "engine", eng)
        monkeypatch.setattr(main, "DB_PATH", db_path)

        # Wie beim echten Start: erst create_all, dann migrate
        from database.connection import Base
        Base.metadata.create_all(bind=eng)

        main._run_migrations()

        assert get_user_version(db_path) == 2
        assert backup_dir.exists()
        assert len(list(backup_dir.glob("rechnungsfee_*.db"))) == 1

    def test_alte_db_version_0_spalten_ergaenzt(self, tmp_path, monkeypatch):
        """Alte DB (version=0, fehlende Spalten) → alle Spalten ergänzt, Backup erstellt, version=2."""
        db_path = tmp_path / "old.db"
        backup_dir = tmp_path / "backups"

        setup_old_db(db_path, version=0)

        eng = make_engine(db_path)
        monkeypatch.setattr(main, "engine", eng)
        monkeypatch.setattr(main, "DB_PATH", db_path)

        main._run_migrations()

        assert get_user_version(db_path) == 2
        assert len(list(backup_dir.glob("rechnungsfee_*.db"))) == 1

        # kassenbuch
        assert {"kunde_id", "rechnung_id", "externe_belegnr", "signatur"} <= get_columns(db_path, "kassenbuch")
        # rechnungen
        assert {"bezahlt_betrag", "zahlungsstatus", "leistungsdatum",
                "ist_entwurf", "storniert", "ausgegeben"} <= get_columns(db_path, "rechnungen")
        # tagesabschluesse
        assert {"zaehlung_json", "signatur"} <= get_columns(db_path, "tagesabschluesse")
        # unternehmen
        assert {"handelsregister_nr", "handelsregister_gericht", "logo_pfad",
                "mail_betreff_vorlage", "mail_text_vorlage",
                "mail_signatur"} <= get_columns(db_path, "unternehmen")
        # kategorien
        assert "ust_satz_standard" in get_columns(db_path, "kategorien")

    def test_version_1_nur_bump(self, tmp_path, monkeypatch):
        """DB auf version=1 → nur Bump auf 2, Backup vorhanden."""
        db_path = tmp_path / "v1.db"
        backup_dir = tmp_path / "backups"

        from database.connection import Base
        eng = make_engine(db_path)
        Base.metadata.create_all(bind=eng)

        con = sqlite3.connect(str(db_path))
        con.execute("PRAGMA user_version = 1")
        con.commit()
        con.close()

        monkeypatch.setattr(main, "engine", eng)
        monkeypatch.setattr(main, "DB_PATH", db_path)

        main._run_migrations()

        assert get_user_version(db_path) == 2
        assert len(list(backup_dir.glob("rechnungsfee_*.db"))) == 1

    def test_aktuelle_db_early_return_kein_backup(self, tmp_path, monkeypatch):
        """DB auf version=2 → Early-Return, kein Backup erstellt."""
        db_path = tmp_path / "current.db"
        backup_dir = tmp_path / "backups"

        con = sqlite3.connect(str(db_path))
        con.execute("PRAGMA user_version = 2")
        con.commit()
        con.close()

        eng = make_engine(db_path)
        monkeypatch.setattr(main, "engine", eng)
        monkeypatch.setattr(main, "DB_PATH", db_path)

        main._run_migrations()

        assert get_user_version(db_path) == 2
        assert not backup_dir.exists() or not any(backup_dir.glob("rechnungsfee_*.db"))

    def test_backup_rotation_max_5(self, tmp_path, monkeypatch):
        """Bei 6 vorhandenen Backups wird das älteste gelöscht – max. 5 behalten."""
        db_path = tmp_path / "rot.db"
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        # 6 bestehende Fake-Backups (Datum weit in der Vergangenheit → werden sortiert zuerst)
        for i in range(6):
            (backup_dir / f"rechnungsfee_20260101_00000{i}.db").touch()

        setup_old_db(db_path, version=0)

        eng = make_engine(db_path)
        monkeypatch.setattr(main, "engine", eng)
        monkeypatch.setattr(main, "DB_PATH", db_path)

        main._run_migrations()

        # 6 alt + 1 neu = 7, Rotation → 5 übrig
        backups = list(backup_dir.glob("rechnungsfee_*.db"))
        assert len(backups) == 5

    def test_idempotent_zweiter_aufruf_kein_backup(self, tmp_path, monkeypatch):
        """Zweimaliger Aufruf: zweites Mal Early-Return, kein zweites Backup."""
        db_path = tmp_path / "idempotent.db"
        backup_dir = tmp_path / "backups"

        setup_old_db(db_path, version=0)

        eng = make_engine(db_path)
        monkeypatch.setattr(main, "engine", eng)
        monkeypatch.setattr(main, "DB_PATH", db_path)

        main._run_migrations()           # Erster Aufruf: Migration + Backup
        main._run_migrations()           # Zweiter Aufruf: Early-Return

        assert get_user_version(db_path) == 2
        assert len(list(backup_dir.glob("rechnungsfee_*.db"))) == 1
