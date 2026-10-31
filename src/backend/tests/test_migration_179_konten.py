"""
Migration 179 (Issue #470-Folgeprüfung): Systemkategorien am DATEV-Kontenrahmen 2026 korrigiert.
Eigene Kontoanpassungen bleiben erhalten; die Erkennung der ig. Lieferung kennt alte (3125) und
neue (4125) SKR04-Nummer, weil gebuchte Einträge ihren Konto-Snapshot behalten.
"""
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import main
from api.rechnungen import _skonto_konto
from database.connection import Base
from database.models import Kategorie
from database.seed import STANDARD_KATEGORIEN
from utils.konten import ist_ig_lieferung_konto

ERWARTET = {
    "Privatentnahme": ("1800", "2100"),
    "Privateinlage": ("1890", "2180"),
    "Einkommensteuer-Vorauszahlung": ("1810", "2150"),
    "Krankenversicherung (Pflicht)": ("1820", "2200"),
    "Sonstige Absetzungen": ("1800", "2100"),
    "Gewährte Skonti": ("8736", "4736"),
    "Erhaltene Skonti": ("3736", "5736"),
    "Forderungsausfall": ("2400", "6930"),
    "Sonstige Einnahmen": ("8603", "4830"),
    "Wareneinkauf Nicht-EU": ("3200", "5200"),
    "Kredittilgung": ("0630", "3150"),
    "KFZ-Reparatur": ("4540", "6540"),
    "KFZ-Steuer": ("4510", "7685"),
    "KFZ (Kauf)": ("0320", "0520"),
    "Anlagevermögen (Kauf)": ("0400", "0630"),
    "Mitgliedsbeiträge": ("4380", "6420"),
    "Berufsgenossenschaft": ("4138", "6120"),
    "Arbeitszimmer (anteilig)": ("4288", "6348"),
    "Miete Einrichtung": ("4960", "6835"),
    "Minijob / geringfügige Beschäftigung": ("4195", "6035"),
    "Personalkosten Familienangehörige": ("4125", "6050"),
    "Löhne & Gehälter": ("4120", "6020"),
    "Eigenverbrauch von Waren (19%)": ("8910", "4620"),
    "EDV / Software (Sofortabschreibung)": ("0490", "0650"),
    "Gewerbesteuer": ("4320", "7610"),
}


def test_seed_konten():
    kat = {k["name"]: (k["konto_skr03"], k["konto_skr04"]) for k in STANDARD_KATEGORIEN}
    for name, konten in ERWARTET.items():
        assert kat[name] == konten, name


def _db(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "alt.db"
    eng = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(main, "engine", eng)
    monkeypatch.setattr(main, "DB_PATH", db_path)
    Base.metadata.create_all(bind=eng)
    with eng.connect() as con:
        s = Session(bind=con)
        for name, s03, s04, mod04 in [
            ("Privateinlage", "1890", "2100", False),
            ("Innergemeinschaftliche Lieferungen", "8125", "3125", False),
            ("Erhaltene Skonti", "2401", "3401", True),   # SKR04 selbst angepasst
        ]:
            s.add(Kategorie(name=name, kontenart="Aufwand", konto_skr03=s03,
                            konto_skr04="9999" if mod04 else s04,
                            konto_skr03_default=s03, konto_skr04_default=s04,
                            user_modified_skr03=False, user_modified_skr04=mod04))
        s.commit()
        s.close()
        con.execute(text("PRAGMA user_version = 178"))
        con.commit()
    return eng


def test_migration_179(tmp_path, monkeypatch):
    eng = _db(tmp_path, monkeypatch)
    main._run_migrations()
    with eng.connect() as con:
        z = {r[0]: tuple(r[1:]) for r in con.execute(text(
            "SELECT name, konto_skr03, konto_skr04, konto_skr04_default FROM kategorien"))}
    assert z["Privateinlage"] == ("1890", "2180", "2180")
    assert z["Innergemeinschaftliche Lieferungen"] == ("8125", "4125", "4125")
    assert z["Erhaltene Skonti"] == ("3736", "9999", "5736")   # eigene Anpassung bleibt


@pytest.mark.parametrize("typ,satz,konten", [
    ("ausgang", 19, ("8736", "4736")), ("ausgang", 7, ("8731", "4731")), ("ausgang", 0, ("8734", "4734")),
    ("eingang", 19, ("3736", "5736")), ("eingang", 7, ("3731", "5731")), ("eingang", 0, ("3730", "5730")),
])
def test_skonto_konten(typ, satz, konten):
    assert _skonto_konto(typ, Decimal(satz)) == konten


def test_ig_lieferung_erkennung_alt_und_neu():
    assert ist_ig_lieferung_konto("8125", "4125")
    assert ist_ig_lieferung_konto(None, "4125")
    assert ist_ig_lieferung_konto(None, "3125")      # alter Konto-Snapshot
    assert not ist_ig_lieferung_konto("3125", "5925")  # Drittland-DL (§13b Abs. 2), SKR03 3125
