"""
Regressionstest für Migration 152 (Nutzer-Feedback): Die Nummernkreise für Angebot,
Auftrag, Proforma und Stornorechnung wurden seit ihrer Einführung mit dem Format
"...-JJNNNN" angelegt - Platzhalter, die _belegnr_aus_format() nie erkannt hat (nur
YYYY/YY/MM/TT/# werden unterstützt). Diese vier Dokumenttypen bekamen dadurch buchstäblich
die unveränderte Formatvorlage als "Nummer" statt einer echten Nummer. Migration 152
korrigiert das Format für bereits bestehende Installationen; database/seed.py und die
ursprünglichen main.py-Migrationen (55/59/60/90) wurden ebenfalls korrigiert (Neuinstallation).
"""
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine

import main
from database.connection import Base


def make_engine(db_path: Path):
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


def test_bestehende_jjnnnn_formate_werden_korrigiert(tmp_path, monkeypatch):
    db_path = tmp_path / "alt.db"
    eng = make_engine(db_path)
    monkeypatch.setattr(main, "engine", eng)
    monkeypatch.setattr(main, "DB_PATH", db_path)

    Base.metadata.create_all(bind=eng)
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA user_version = 151")
    con.executemany(
        "INSERT INTO nummernkreise (typ, bezeichnung, format, naechste_nr, reset_jaehrlich, aktiv) VALUES (?, ?, ?, 7, 1, 1)",
        [
            ("angebot", "Angebote", "ANG-JJNNNN"),
            ("auftrag", "Aufträge", "AU-JJNNNN"),
            ("proforma", "Proforma-Rechnungen", "PRF-JJNNNN"),
            ("stornorechnung", "Stornorechnungen", "STORNO-JJNNNN"),
            # unveraendertes, individuell abweichendes Format bleibt unangetastet
            ("rechnung_ausgang", "Ausgangsrechnungen", "YY####"),
        ],
    )
    con.commit()
    con.close()

    main._run_migrations()

    con = sqlite3.connect(str(db_path))
    formate = dict(con.execute("SELECT typ, format FROM nummernkreise").fetchall())
    con.close()

    assert formate["angebot"] == "ANG-YY####"
    assert formate["auftrag"] == "AU-YY####"
    assert formate["proforma"] == "PRF-YY####"
    assert formate["stornorechnung"] == "STORNO-YY####"
    assert formate["rechnung_ausgang"] == "YY####"
    assert main.SCHEMA_VERSION >= 152


def test_neuinstallation_seed_nutzt_korrektes_format():
    """database/seed.py darf bei einer frischen Installation nicht erneut JJNNNN aussäen."""
    from database.seed import seed_nummernkreise
    from database.models import Nummernkreis
    from sqlalchemy.orm import sessionmaker

    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    db = Session()

    seed_nummernkreise(db)

    formate = {nk.typ: nk.format for nk in db.query(Nummernkreis).all()}
    assert formate.get("proforma") == "PRF-YY####"
    assert "JJNNNN" not in "".join(formate.values())


def test_angebot_und_auftrag_werden_ueber_seed_abgesichert():
    """Zusatzfund: nummernkreise.aktiv ist NOT NULL ohne DB-seitigen Default (nur im
    SQLAlchemy-Modell). Auf einer brandneuen DB (create_all() legt die Spalte sofort im
    Vollschema an) schlägt die rohe INSERT-Migration für 'angebot'/'auftrag' dadurch still
    fehl (INSERT OR IGNORE), da sie "aktiv" nicht mit angibt - ohne dieses ORM-basierte
    Sicherheitsnetz hätten neue Installationen dadurch gar keinen Angebot-/Auftrag-
    Nummernkreis und naechste_nummer() würde dauerhaft None liefern."""
    from database.seed import seed_nummernkreise
    from database.models import Nummernkreis
    from sqlalchemy.orm import sessionmaker

    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    db = Session()

    seed_nummernkreise(db)

    formate = {nk.typ: nk.format for nk in db.query(Nummernkreis).all()}
    assert formate.get("angebot") == "ANG-YY####"
    assert formate.get("auftrag") == "AU-YY####"
