"""
Issue #578: EDV/Software mit Nutzungsdauer 1 Jahr - voller Abzug im Anschaffungsjahr (BMF-Schreiben
Computerhardware/Software) statt monatsgenauer Verteilung auf Kauf- und Folgejahr. Opt-in je
Anlagegut (afa_sofort, Migration 193), bestehende Einträge rechnen unverändert.
"""
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, text

import main
from api.anlageverzeichnis import AnlagegutCreate, _afa_fuer_jahr
from database.connection import Base
from database.models import Anlagegut


def _gut(**kw) -> Anlagegut:
    daten = dict(bezeichnung="Laptop", typ="edv", kaufdatum=date(2026, 5, 10),
                 kaufpreis_netto=Decimal("3000"), nutzungsdauer_jahre=1, afa_methode="linear",
                 privat_anteil_prozent=Decimal("0"), afa_sofort=True)
    daten.update(kw)
    return Anlagegut(**daten)


def test_voller_abzug_im_anschaffungsjahr():
    g = _gut()
    assert _afa_fuer_jahr(g, 2026) == Decimal("3000.00")
    assert _afa_fuer_jahr(g, 2027) == Decimal("0")


def test_ohne_haekchen_monatsgenau_wie_bisher():
    g = _gut(afa_sofort=False)
    assert _afa_fuer_jahr(g, 2026) == Decimal("2000.00")  # Mai–Dezember: 8/12
    assert _afa_fuer_jahr(g, 2027) == Decimal("1000.00")


def test_privatanteil_wird_beruecksichtigt():
    assert _afa_fuer_jahr(_gut(privat_anteil_prozent=Decimal("20")), 2026) == Decimal("2400.00")


@pytest.mark.parametrize("kw", [dict(typ="sonstig"), dict(nutzungsdauer_jahre=3)])
def test_nur_edv_mit_einem_jahr(kw):
    daten = dict(bezeichnung="X", typ="edv", kaufdatum=date(2026, 5, 10), kaufpreis_netto=Decimal("3000"),
                 nutzungsdauer_jahre=1, afa_sofort=True)
    daten.update(kw)
    with pytest.raises(ValidationError):
        AnlagegutCreate(**daten)


def test_migration_193(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE anlageverzeichnis DROP COLUMN afa_sofort"))
        conn.execute(text("PRAGMA user_version = 192"))
    monkeypatch.setattr(main, "engine", engine)
    main._run_migrations()
    with engine.begin() as conn:
        assert "afa_sofort" in {r[1] for r in conn.execute(text("PRAGMA table_info(anlageverzeichnis)"))}
        assert conn.execute(text("PRAGMA user_version")).scalar() == main.SCHEMA_VERSION
        conn.execute(text("PRAGMA user_version = 192"))
    main._run_migrations()
