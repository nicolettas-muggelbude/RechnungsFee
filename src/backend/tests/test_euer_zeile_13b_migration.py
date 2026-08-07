"""
Regressionstest für Issue #340 (Migration 146).

Bug: "EU-Dienstleistungen (§13b Abs. 1)" und "Drittland-Dienstleistungen (§13b Abs. 1)"
lagen mit euer_zeile=27 (Waren, Rohstoffe, Hilfsstoffe) auf der falschen EÜR-Zeile -
beide erfassen sonstige Leistungen, keine Waren. Korrekt ist Zeile 60 (Sonstige
Betriebsausgaben), wie bei der dritten Reverse-Charge-Kategorie "Bauleistungen / §13b
Abs. 2" bereits der Fall.
"""
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from database.connection import Base
from database.models import Kategorie


def make_engine(db_path: Path):
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


def get_euer_zeile(db_path: Path, name: str) -> int | None:
    con = sqlite3.connect(str(db_path))
    row = con.execute("SELECT euer_zeile FROM kategorien WHERE name = ?", (name,)).fetchone()
    con.close()
    return row[0] if row else None


class TestEuerZeile13bMigration:

    def test_bestehende_db_mit_euer_zeile_27_wird_auf_60_korrigiert(self, tmp_path, monkeypatch):
        db_path = tmp_path / "alt.db"
        eng = make_engine(db_path)
        monkeypatch.setattr(main, "engine", eng)
        monkeypatch.setattr(main, "DB_PATH", db_path)

        Base.metadata.create_all(bind=eng)
        Session = sessionmaker(bind=eng)
        session = Session()
        session.add_all([
            Kategorie(name="EU-Dienstleistungen (§13b Abs. 1)", kontenart="Aufwand",
                      konto_skr03="3123", konto_skr04="5923", euer_zeile=27,
                      vorsteuer_prozent=100, ust_satz_standard=19),
            Kategorie(name="Drittland-Dienstleistungen (§13b Abs. 1)", kontenart="Aufwand",
                      konto_skr03="3125", konto_skr04="5925", euer_zeile=27,
                      vorsteuer_prozent=100, ust_satz_standard=19),
        ])
        session.commit()
        session.close()
        con = sqlite3.connect(str(db_path))
        con.execute("PRAGMA user_version = 145")
        con.commit()
        con.close()

        main._run_migrations()

        assert get_euer_zeile(db_path, "EU-Dienstleistungen (§13b Abs. 1)") == 60
        assert get_euer_zeile(db_path, "Drittland-Dienstleistungen (§13b Abs. 1)") == 60

    def test_manuell_abweichende_euer_zeile_bleibt_unangetastet(self, tmp_path, monkeypatch):
        """Guard "WHERE euer_zeile = 27": eine bereits manuell auf einen anderen Wert
        gesetzte Zeile darf durch die Korrektur nicht überschrieben werden - es gibt
        kein user_modified-Flag für euer_zeile (anders als bei konto_skr03/04)."""
        db_path = tmp_path / "manuell.db"
        eng = make_engine(db_path)
        monkeypatch.setattr(main, "engine", eng)
        monkeypatch.setattr(main, "DB_PATH", db_path)

        Base.metadata.create_all(bind=eng)
        Session = sessionmaker(bind=eng)
        session = Session()
        session.add(Kategorie(name="EU-Dienstleistungen (§13b Abs. 1)", kontenart="Aufwand",
                               konto_skr03="3123", konto_skr04="5923", euer_zeile=30,
                               vorsteuer_prozent=100, ust_satz_standard=19))
        session.commit()
        session.close()
        con = sqlite3.connect(str(db_path))
        con.execute("PRAGMA user_version = 145")
        con.commit()
        con.close()

        main._run_migrations()

        assert get_euer_zeile(db_path, "EU-Dienstleistungen (§13b Abs. 1)") == 30

    def test_frische_db_erhaelt_euer_zeile_60_ueber_migrate_kategorien(self, tmp_path, monkeypatch):
        """Neuinstallation: _migrate_kategorien() legt beide Kategorien direkt mit euer_zeile=60 an."""
        db_path = tmp_path / "fresh.db"
        eng = make_engine(db_path)
        monkeypatch.setattr(main, "engine", eng)
        monkeypatch.setattr(main, "DB_PATH", db_path)
        monkeypatch.setattr(main, "SessionLocal", main.SessionLocal.__class__(bind=eng))

        Base.metadata.create_all(bind=eng)
        main._run_migrations()
        main._migrate_kategorien()

        assert get_euer_zeile(db_path, "EU-Dienstleistungen (§13b Abs. 1)") == 60
        assert get_euer_zeile(db_path, "Drittland-Dienstleistungen (§13b Abs. 1)") == 60
