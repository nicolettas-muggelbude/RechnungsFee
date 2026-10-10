"""
Regressionstest für Migration 166 (Issue #426, Datenfix-Teil):
naechste_nummer() (api/nummernkreise.py) erkannte einen Jahreswechsel bisher über
"letztes_jahr != bezug.year" - griff auch RÜCKWÄRTS, wenn eine ältere Eingangsrechnung erst
nachträglich erfasst wurde (Papierbelege werden selten chronologisch nach Rechnungsdatum
eingegeben). Dadurch konnten mehrere unterschiedliche Rechnungen dieselbe interne Nummer
bekommen (real gemeldet: vier Lieferanten mit "ER-260009"). Migration 166 disambiguiert
bestehende Dubletten einmalig, die reine Zählerlogik ist separat (Phase 1, ohne Schema-Änderung)
bereits vorwärts-only gefixt.
"""
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import main
from database.connection import Base
from database.models import Rechnung


def make_engine(db_path: Path):
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


def test_doppelte_rechnungsnummern_werden_disambiguiert(tmp_path, monkeypatch):
    db_path = tmp_path / "alt.db"
    eng = make_engine(db_path)
    monkeypatch.setattr(main, "engine", eng)
    monkeypatch.setattr(main, "DB_PATH", db_path)

    Base.metadata.create_all(bind=eng)

    with eng.connect() as con:
        s = Session(bind=con)
        # Exaktes Szenario aus Issue #426: vier verschiedene Eingangsrechnungen mit "ER-260009".
        r1 = Rechnung(typ="eingang", rechnungsnummer="ER-260009", datum=date(2026, 4, 30), partner_freitext="Drillisch Online GmbH")
        r2 = Rechnung(typ="eingang", rechnungsnummer="ER-260009", datum=date(2026, 8, 8), partner_freitext="Amazon", storniert=True)
        r3 = Rechnung(typ="eingang", rechnungsnummer="ER-260009", datum=date(2026, 8, 17), partner_freitext="Zakelijk Rijden BV", storniert=True)
        r4 = Rechnung(typ="eingang", rechnungsnummer="ER-260009", datum=date(2026, 8, 25), partner_freitext="SUNO")
        # Kontrolle: eine eindeutige Nummer darf nicht angefasst werden.
        r5 = Rechnung(typ="eingang", rechnungsnummer="ER-260001", datum=date(2026, 1, 5), partner_freitext="Eindeutig")
        s.add_all([r1, r2, r3, r4, r5])
        s.commit()
        ids = [r1.id, r2.id, r3.id, r4.id, r5.id]
        s.close()

        con.execute(text("PRAGMA user_version = 165"))
        con.commit()

    main._run_migrations()

    with eng.connect() as con:
        def _nr(id_):
            return con.execute(text("SELECT rechnungsnummer FROM rechnungen WHERE id = :id"), {"id": id_}).scalar()

        nummern = [_nr(i) for i in ids]
        protokoll_count = con.execute(
            text("SELECT COUNT(*) FROM aenderungsprotokoll WHERE migration_version = 166")
        ).scalar()
        user_version = con.execute(text("PRAGMA user_version")).scalar()

    # Älteste (kleinste id) behält ihre Original-Nummer, alle weiteren werden eindeutig gemacht.
    assert nummern[0] == "ER-260009"
    assert nummern[1] == "ER-260009-2"
    assert nummern[2] == "ER-260009-3"
    assert nummern[3] == "ER-260009-4"
    assert len(set(nummern)) == 5  # inkl. der unangetasteten r5
    assert nummern[4] == "ER-260001"  # unangetastet
    assert protokoll_count == 3  # nur die drei disambiguierten Zeilen, nicht die aelteste
    assert user_version == 166
