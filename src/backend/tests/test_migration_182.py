"""
Migration 182 (Issue #491/#492): Felder für die Kleinunternehmergrenze und steuerfreie Umsätze.
"""
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import main
from api.schemas import UnternehmenUpdate
from database.connection import Base
from database.models import EksEinstellungen, Unternehmen


def _alte_db(tmp_path, monkeypatch, eks_beginn=None):
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.db'}")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        session.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O"))
        if eks_beginn:
            session.add(EksEinstellungen(id=1, taetigkeitsbeginn=eks_beginn))
        session.commit()
    with engine.begin() as conn:
        for spalte in ("taetigkeit_beginn", "umsatz_extern_jahr", "umsatz_extern_vorjahr",
                       "umsatz_extern_startjahr", "steuerbefreiung_4"):
            conn.execute(text(f"ALTER TABLE unternehmen DROP COLUMN {spalte}"))
        conn.execute(text("ALTER TABLE rechnungen DROP COLUMN steuerfrei_4"))
        conn.execute(text("PRAGMA user_version = 181"))
    monkeypatch.setattr(main, "engine", engine)
    return engine


def test_migration_182_legt_spalten_an(tmp_path, monkeypatch):
    engine = _alte_db(tmp_path, monkeypatch)
    main._run_migrations()
    with engine.connect() as conn:
        u = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)"))}
        r = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)"))}
        version = conn.execute(text("PRAGMA user_version")).scalar()
    assert version == main.SCHEMA_VERSION
    assert {"taetigkeit_beginn", "umsatz_extern_jahr", "umsatz_extern_vorjahr",
            "umsatz_extern_startjahr", "steuerbefreiung_4"} <= u
    assert "steuerfrei_4" in r


def test_migration_182_uebernimmt_taetigkeitsbeginn_aus_eks(tmp_path, monkeypatch):
    engine = _alte_db(tmp_path, monkeypatch, eks_beginn="2025-04")
    main._run_migrations()
    with engine.connect() as conn:
        beginn = conn.execute(text("SELECT taetigkeit_beginn FROM unternehmen")).scalar()
    assert beginn == "2025-04-01"


def test_migration_182_ohne_eks_eintrag(tmp_path, monkeypatch):
    engine = _alte_db(tmp_path, monkeypatch)
    main._run_migrations()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT taetigkeit_beginn FROM unternehmen")).scalar() is None


def test_schema_steuerbefreiung_nur_bekannte_werte():
    assert UnternehmenUpdate(steuerbefreiung_4="4_nr_14").steuerbefreiung_4 == "4_nr_14"
    assert UnternehmenUpdate(steuerbefreiung_4="").steuerbefreiung_4 is None
    with pytest.raises(ValidationError):
        UnternehmenUpdate(steuerbefreiung_4="4_nr_99")


def test_schema_umsatz_extern_nicht_negativ():
    u = UnternehmenUpdate(taetigkeit_beginn=date(2026, 3, 1), umsatz_extern_vorjahr=Decimal("12000"))
    assert u.umsatz_extern_vorjahr == Decimal("12000")
    with pytest.raises(ValidationError):
        UnternehmenUpdate(umsatz_extern_startjahr=Decimal("-1"))
