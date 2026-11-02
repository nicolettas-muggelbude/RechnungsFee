"""
Migration 178 (Issue #470, Folgemeldung): Reise-/Fahrtkostenkonten auf "Reisekosten Unternehmer"
bzw. Privat-Fahrzeug (DATEV 2026), ÖPNV mit Vorsteuer, Privat-PKW auf EÜR-Zeile 71 (Nutzungseinlage).
Eigene Kontoanpassungen und eine selbst geänderte EÜR-Zeile bleiben erhalten.
"""
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import main
from database.connection import Base
from database.models import Kategorie


def _kat(name, s03, s04, zeile, vst=100, ust=19, mod04=False):
    return Kategorie(name=name, kontenart="Aufwand", euer_zeile=zeile,
                     konto_skr03=s03, konto_skr04="9999" if mod04 else s04,
                     konto_skr03_default=s03, konto_skr04_default=s04,
                     user_modified_skr03=False, user_modified_skr04=mod04,
                     vorsteuer_prozent=vst, ust_satz_standard=ust)


def _db(tmp_path: Path, monkeypatch, kategorien):
    db_path = tmp_path / "alt.db"
    eng = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(main, "engine", eng)
    monkeypatch.setattr(main, "DB_PATH", db_path)
    Base.metadata.create_all(bind=eng)
    with eng.connect() as con:
        s = Session(bind=con)
        s.add_all(kategorien)
        s.commit()
        s.close()
        con.execute(text("PRAGMA user_version = 177"))
        con.commit()
    return eng


def _zeilen(eng):
    with eng.connect() as con:
        return {r[0]: tuple(r[1:]) for r in con.execute(text(
            "SELECT name, konto_skr03, konto_skr04, euer_zeile, vorsteuer_prozent, ust_satz_standard FROM kategorien"
        ))}


def test_migration_178(tmp_path, monkeypatch):
    eng = _db(tmp_path, monkeypatch, [
        _kat("Reisekosten – Übernachtung", "4660", "6640", 44, ust=7),
        _kat("Reisekosten – Nebenkosten", "4663", "6644", 44, mod04=True),
        _kat("Reisekosten – ÖPNV", "4664", "6644", 70, vst=0, ust=0),
        _kat("Verpflegungsmehraufwand", "4661", "6645", 64, vst=0, ust=0),
        _kat("Fahrtkosten Privat-PKW (0,10 €/km)", "4560", "6530", 70, vst=0, ust=0),
    ])
    main._run_migrations()
    z = _zeilen(eng)
    assert z["Reisekosten – Übernachtung"][:3] == ("4676", "6680", 44)
    assert z["Reisekosten – Nebenkosten"][:2] == ("4676", "9999")   # eigene Anpassung bleibt
    assert z["Reisekosten – ÖPNV"] == ("4673", "6673", 70, 100, 7)
    assert z["Verpflegungsmehraufwand"][:3] == ("4674", "6674", 64)
    assert z["Fahrtkosten Privat-PKW (0,10 €/km)"][:3] == ("4590", "6590", 71)


def test_selbst_geaenderte_zeile_bleibt(tmp_path, monkeypatch):
    eng = _db(tmp_path, monkeypatch, [
        _kat("Fahrtkosten Privat-PKW (0,10 €/km)", "4560", "6530", 60, vst=0, ust=0),
    ])
    main._run_migrations()
    assert _zeilen(eng)["Fahrtkosten Privat-PKW (0,10 €/km)"][2] == 60
