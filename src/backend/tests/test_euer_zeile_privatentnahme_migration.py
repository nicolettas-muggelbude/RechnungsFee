"""
Regressionstest für Issue #341-Folgefund (Migration 147).

Bug: Die sechs "Absetzungen vom Einkommen"-Privatkategorien (Einkommensteuer-
Vorauszahlung, Krankenversicherung (Pflicht), Pflegeversicherung (Pflicht),
Rentenversicherung (freiwillig), Riester-Beiträge, Sonstige Absetzungen) hatten
euer_zeile=NULL. Wirtschaftlich sind es Privatentnahmen (Zeile 106) - ohne gesetzte
euer_zeile erschienen sie im Buchungsformular (nach dem #341-Fix) fälschlich sowohl
unter "Einnahme" als auch "Ausgabe", da Privat-Kategorien ohne euer_zeile 106/107
dort bewusst in beiden Gruppen angezeigt werden statt gar nicht.
"""
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from database.connection import Base
from database.models import Kategorie

BETROFFENE_KATEGORIEN = [
    "Einkommensteuer-Vorauszahlung", "Krankenversicherung (Pflicht)",
    "Pflegeversicherung (Pflicht)", "Rentenversicherung (freiwillig)",
    "Riester-Beiträge", "Sonstige Absetzungen",
]


def make_engine(db_path: Path):
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


def get_euer_zeile(db_path: Path, name: str):
    con = sqlite3.connect(str(db_path))
    row = con.execute("SELECT euer_zeile FROM kategorien WHERE name = ?", (name,)).fetchone()
    con.close()
    return row[0] if row else None


class TestEuerZeilePrivatentnahmeMigration:

    def test_bestehende_db_mit_euer_zeile_null_wird_auf_106_korrigiert(self, tmp_path, monkeypatch):
        db_path = tmp_path / "alt.db"
        eng = make_engine(db_path)
        monkeypatch.setattr(main, "engine", eng)
        monkeypatch.setattr(main, "DB_PATH", db_path)

        Base.metadata.create_all(bind=eng)
        Session = sessionmaker(bind=eng)
        session = Session()
        session.add_all([
            Kategorie(name=name, kontenart="Privat", konto_skr03="1890", konto_skr04="2100",
                      euer_zeile=None, vorsteuer_prozent=0, ust_satz_standard=0)
            for name in BETROFFENE_KATEGORIEN
        ])
        session.commit()
        session.close()
        con = sqlite3.connect(str(db_path))
        con.execute("PRAGMA user_version = 146")
        con.commit()
        con.close()

        main._run_migrations()

        for name in BETROFFENE_KATEGORIEN:
            assert get_euer_zeile(db_path, name) == 106

    def test_manuell_abweichende_euer_zeile_bleibt_unangetastet(self, tmp_path, monkeypatch):
        db_path = tmp_path / "manuell.db"
        eng = make_engine(db_path)
        monkeypatch.setattr(main, "engine", eng)
        monkeypatch.setattr(main, "DB_PATH", db_path)

        Base.metadata.create_all(bind=eng)
        Session = sessionmaker(bind=eng)
        session = Session()
        session.add(Kategorie(name="Riester-Beiträge", kontenart="Privat",
                               konto_skr03="1890", konto_skr04="2100",
                               euer_zeile=107, vorsteuer_prozent=0, ust_satz_standard=0))
        session.commit()
        session.close()
        con = sqlite3.connect(str(db_path))
        con.execute("PRAGMA user_version = 146")
        con.commit()
        con.close()

        main._run_migrations()

        assert get_euer_zeile(db_path, "Riester-Beiträge") == 107

    def test_frische_db_erhaelt_euer_zeile_106_ueber_seed(self, tmp_path, monkeypatch):
        db_path = tmp_path / "fresh.db"
        eng = make_engine(db_path)
        monkeypatch.setattr(main, "engine", eng)
        monkeypatch.setattr(main, "DB_PATH", db_path)

        Base.metadata.create_all(bind=eng)
        main._run_migrations()

        Session = sessionmaker(bind=eng)
        session = Session()
        from database.seed import run_all_seeds
        run_all_seeds(session)
        session.close()

        for name in BETROFFENE_KATEGORIEN:
            assert get_euer_zeile(db_path, name) == 106
