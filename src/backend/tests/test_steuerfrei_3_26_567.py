"""
Issue #567 (Folgemeldung Markus): Übungsleiter-Einnahmen (§ 3 Nr. 26 EStG) werden in der
Anlage S getrennt ausgewiesen und mindern den Gewinn bis zum Freibetrag.

- Kategorie bekommt steuerfrei_paragraf (3_26 | 3_26a), Migration 190
- EÜR: Einnahmen bleiben Betriebseinnahmen, Abzug in der Gewinnermittlung (Zeile 78, 2026: 79)
- Freibetrag 3.000 € (bis 2025) / 3.300 € (ab 2026), Ehrenamt 840 € / 960 €
- Anlage S Zeile 57: Gesamtbetrag (Kz 191) und davon steuerfrei (Kz 192)
"""
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text

import main
from api.anlage_s import anlage_s_berechnen
from api.euer import _berechne_euer, formular_zeile, freibetrag_3
from api.kategorien import create_kategorie
from api.schemas import KategorieCreate
from database.connection import Base
from database.models import Kategorie
from tests.test_ausgang_positionskategorie_567 import _kat, _ku, _pos, _rechnung, _zahlen, db  # noqa: F401


def _ul(db, paragraf="3_26") -> Kategorie:
    k = _kat(db, "Übungsleiter § 3 Nr. 26")
    k.steuerfrei_paragraf = paragraf
    db.commit()
    return k


def test_freibetraege_je_jahr():
    assert freibetrag_3("3_26", 2025) == Decimal("3000")
    assert freibetrag_3("3_26", 2026) == Decimal("3300")
    assert freibetrag_3("3_26a", 2025) == Decimal("840")
    assert freibetrag_3("3_26a", 2026) == Decimal("960")


def test_zeile_gewinnermittlung_2026_verschoben():
    assert formular_zeile(78, 2025) == 78
    assert formular_zeile(78, 2026) == 79


def test_euer_unter_freibetrag_ganz_steuerfrei(db):
    _ku(db)
    ul = _ul(db)
    r = _rechnung(db, [_pos("Training", "1200", "0", ul), _pos("Fotos", "500", "0")])
    _zahlen(db, r)
    euer = _berechne_euer(2026, db)
    assert euer["summe_einnahmen"] == Decimal("1700.00")  # Einnahmen bleiben Betriebseinnahmen
    assert euer["ueberschuss"] == Decimal("1700.00")
    assert euer["abzug_steuerfrei"] == Decimal("1200.00")
    assert euer["gewinn_verlust"] == Decimal("500.00")


def test_euer_ueber_freibetrag_gekappt(db):
    _ku(db)
    ul = _ul(db)
    r = _rechnung(db, [_pos("Training", "4000", "0", ul)])
    _zahlen(db, r)
    euer = _berechne_euer(2026, db)
    assert euer["abzug_steuerfrei"] == Decimal("3300.00")
    assert euer["gewinn_verlust"] == Decimal("700.00")
    t = euer["steuerfrei_taetigkeiten"][0]
    assert (t["einnahmen"], t["steuerfrei"]) == (Decimal("4000.00"), Decimal("3300.00"))


def test_ohne_kennzeichen_unveraendert(db):
    _ku(db)
    ul = _kat(db, "Übungsleiter § 3 Nr. 26")
    r = _rechnung(db, [_pos("Training", "1200", "0", ul)])
    _zahlen(db, r)
    euer = _berechne_euer(2026, db)
    assert euer["abzug_steuerfrei"] == Decimal("0")
    assert euer["gewinn_verlust"] == euer["ueberschuss"] == Decimal("1200.00")


def test_anlage_s_zeile_57(db):
    from database.models import Unternehmen
    db.query(Unternehmen).one().vorname = "Markus"
    _ku(db)
    ul = _ul(db)
    r = _rechnung(db, [_pos("Training", "1200", "0", ul), _pos("Fotos", "500", "0")])
    _zahlen(db, r)
    erg = anlage_s_berechnen(jahr=2026, db=db)
    assert erg.gewinn_verlust == Decimal("500.00")
    assert len(erg.nebentaetigkeiten) == 1
    n = erg.nebentaetigkeiten[0]
    assert (n.zeile, n.taetigkeit, n.einnahmen, n.steuerfrei) == (
        57, "Übungsleiter § 3 Nr. 26", Decimal("1200.00"), Decimal("1200.00"))


def test_pdfs_mit_abschnitt(db):
    from api.anlage_s import _generate_anlage_s_pdf
    from api.euer import _generate_pdf
    from database.models import Unternehmen
    _ku(db)
    ul = _ul(db)
    r = _rechnung(db, [_pos("Training", "1200", "0", ul), _pos("Fotos", "500", "0")])
    _zahlen(db, r)
    assert _generate_anlage_s_pdf(anlage_s_berechnen(jahr=2026, db=db))[:4] == b"%PDF"
    assert _generate_pdf(_berechne_euer(2026, db), db.query(Unternehmen).one())[:4] == b"%PDF"


def test_kennzeichen_nur_bei_erloes(db):
    with pytest.raises(HTTPException) as exc:
        create_kategorie(KategorieCreate(name="Material", kontenart="Aufwand", steuerfrei_paragraf="3_26"), db)
    assert exc.value.status_code == 422
    k = create_kategorie(KategorieCreate(name="Ehrenamt Verein", kontenart="Erlös", euer_zeile=12,
                                         steuerfrei_paragraf="3_26a"), db)
    assert k.steuerfrei_paragraf == "3_26a"


def test_migration_190(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE kategorien DROP COLUMN steuerfrei_paragraf"))
        conn.execute(text("PRAGMA user_version = 189"))
    monkeypatch.setattr(main, "engine", engine)
    main._run_migrations()
    with engine.begin() as conn:
        assert "steuerfrei_paragraf" in {r[1] for r in conn.execute(text("PRAGMA table_info(kategorien)"))}
        assert conn.execute(text("PRAGMA user_version")).scalar() == main.SCHEMA_VERSION
        conn.execute(text("PRAGMA user_version = 189"))
    main._run_migrations()  # zweiter Lauf ohne Fehler
