"""
Issue #480: Betriebseinnahmen in der richtigen EÜR-Zeile.

1. Einnahme-Kategorien ohne EÜR-Zeile (Sonstige Einnahmen, Mahngebühren, Verzugszinsen,
   Zuwendungen von Dritten) fielen komplett aus der EÜR → Zeile 16 (Migration 181).
2. Status je Buchung: Kleinunternehmer-Einnahmen (Steuerbefreiungsgrund „§19 UStG“) → Zeile 12,
   0-%-Einnahmen Regelbesteuerter → Zeile 16 statt 12. Stornos übernehmen den Status ihres
   Originals, ein Wechsel im Laufe des Jahres wird richtig aufgeteilt.
3. Rechnungen von Kleinunternehmern buchen auf „Betriebseinnahmen (Kleinunternehmer)“ (8192/4184).
"""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

import main
from api.euer import _berechne_euer, _berechne_euer_kategorien
from api.rechnungen import _erloes_kategorie
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Rechnung, Rechnungsposition, Unternehmen
from database.seed import STANDARD_KATEGORIEN

D = Decimal


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Test", strasse="X", hausnummer="1", plz="12345", ort="Y",
                            ist_kleinunternehmer=False))
    for name in ("Betriebseinnahmen", "Betriebseinnahmen (0%)", "Betriebseinnahmen (Kleinunternehmer)",
                 "Sonstige Einnahmen", "Mahngebühren"):
        d = next(k for k in STANDARD_KATEGORIEN if k["name"] == name)
        session.add(Kategorie(**d))
    session.commit()
    yield session
    session.close()


def _kat(db, name) -> Kategorie:
    return db.query(Kategorie).filter_by(name=name).one()


def _einnahme(db, kat_name, netto, datum=date(2026, 3, 1), grund=None, ust=D("0"), **kw) -> Journaleintrag:
    e = Journaleintrag(
        datum=datum, belegnr=f"B{db.query(Journaleintrag).count() + 1}", beschreibung=kw.pop("beschreibung", "Einnahme"),
        kategorie_id=_kat(db, kat_name).id, zahlungsart="Bank", art=kw.pop("art", "Einnahme"),
        netto_betrag=D(netto), ust_satz=D("19") if ust else D("0"), ust_betrag=ust,
        brutto_betrag=D(netto) + ust, steuerbefreiung_grund=grund, **kw,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def _ku(db, an: bool):
    db.query(Unternehmen).one().ist_kleinunternehmer = an
    db.commit()


def test_seed_zeilen():
    z = {k["name"]: k["euer_zeile"] for k in STANDARD_KATEGORIEN}
    for name in ("Sonstige Einnahmen", "Mahngebühren", "Verzugszinsen (Einnahme)", "Zuwendungen von Dritten",
                 "Betriebseinnahmen (0%)"):
        assert z[name] == 16, name
    ku = next(k for k in STANDARD_KATEGORIEN if k["name"] == "Betriebseinnahmen (Kleinunternehmer)")
    assert (ku["konto_skr03"], ku["konto_skr04"], ku["euer_zeile"]) == ("8192", "4184", 12)


def test_regelbesteuert_0_prozent_und_sonstige_in_zeile_16(db):
    _einnahme(db, "Betriebseinnahmen (0%)", "100.00")
    _einnahme(db, "Sonstige Einnahmen", "40.00")
    _einnahme(db, "Betriebseinnahmen", "200.00", ust=D("38.00"))
    z = _berechne_euer(2026, db)["zeilen"]
    assert z.get(12, D("0")) == D("0")
    assert z[16] == D("140.00")
    assert z[15] == D("200.00")


def test_kleinunternehmer_alles_in_zeile_12(db):
    _ku(db, True)
    _einnahme(db, "Betriebseinnahmen (Kleinunternehmer)", "100.00", grund="§19 UStG")
    _einnahme(db, "Mahngebühren", "5.00", grund="§19 UStG")
    _einnahme(db, "Betriebseinnahmen", "50.00", grund="§19 UStG")   # versehentlich 19-%-Kategorie
    z = _berechne_euer(2026, db)["zeilen"]
    assert z[12] == D("155.00")
    assert z.get(15, D("0")) == D("0") and z.get(16, D("0")) == D("0")
    assert _berechne_euer_kategorien(2026, db)[12]["Mahngebühren"] == D("5.00")


def test_wechsel_im_jahr_wird_je_buchung_aufgeteilt(db):
    """Bis Juni Kleinunternehmer, danach regelbesteuert (aktuelle Einstellung: regelbesteuert)."""
    _einnahme(db, "Betriebseinnahmen (Kleinunternehmer)", "1000.00", datum=date(2026, 3, 1), grund="§19 UStG")
    _einnahme(db, "Sonstige Einnahmen", "20.00", datum=date(2026, 4, 1), grund="§19 UStG")
    _einnahme(db, "Betriebseinnahmen", "500.00", datum=date(2026, 8, 1), ust=D("95.00"))
    _einnahme(db, "Sonstige Einnahmen", "30.00", datum=date(2026, 9, 1))
    z = _berechne_euer(2026, db)["zeilen"]
    assert z[12] == D("1020.00")
    assert z[15] == D("500.00")
    assert z[16] == D("30.00")


def test_storno_uebernimmt_status_des_originals(db):
    """Die Storno-Gegenbuchung trägt keinen Steuerbefreiungsgrund - sie muss trotzdem in Zeile 12
    abziehen, sonst bliebe Zeile 12 zu hoch und Zeile 16 negativ."""
    original = _einnahme(db, "Betriebseinnahmen (Kleinunternehmer)", "100.00", grund="§19 UStG")
    _einnahme(db, "Betriebseinnahmen (Kleinunternehmer)", "100.00", art="Ausgabe",
              beschreibung=f"STORNO {original.belegnr}: Korrektur", gruppe_id=original.id)
    z = _berechne_euer(2026, db)["zeilen"]
    assert z.get(12, D("0")) == D("0")
    assert z.get(16, D("0")) == D("0")


def test_altbuchung_ohne_grund_bei_kleinunternehmer(db):
    _ku(db, True)
    _einnahme(db, "Betriebseinnahmen (0%)", "80.00")     # vor Einführung des Steuerbefreiungsgrunds
    z = _berechne_euer(2026, db)["zeilen"]
    assert z[12] == D("80.00")
    assert z.get(16, D("0")) == D("0")


def _rechnung(db) -> Rechnung:
    r = Rechnung(typ="ausgang", rechnungsnummer="RE-1", datum=date(2026, 3, 1), netto_gesamt=D("100"),
                 ust_gesamt=D("0"), brutto_gesamt=D("100"), ist_entwurf=False)
    db.add(r)
    db.flush()
    db.add(Rechnungsposition(rechnung_id=r.id, position_nr=1, beschreibung="Leistung", menge=D("1"),
                             einheit="Stk.", netto=D("100"), ust_satz=D("0"), ust_betrag=D("0"), brutto=D("100")))
    db.commit()
    db.refresh(r)
    return r


def test_erloeskategorie_kleinunternehmer(db):
    _ku(db, True)
    _, kat = _erloes_kategorie(db, _rechnung(db))
    assert kat.name == "Betriebseinnahmen (Kleinunternehmer)"


def test_erloeskategorie_regelbesteuert_0_prozent(db):
    _, kat = _erloes_kategorie(db, _rechnung(db))
    assert kat.name == "Betriebseinnahmen (0%)"


def test_migration_181(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "alt.db"
    eng = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(main, "engine", eng)
    monkeypatch.setattr(main, "DB_PATH", db_path)
    Base.metadata.create_all(bind=eng)
    with eng.connect() as con:
        s = Session(bind=con)
        s.add(Kategorie(name="Sonstige Einnahmen", kontenart="Erlös", euer_zeile=None))
        s.add(Kategorie(name="Mahngebühren", kontenart="Erlös", euer_zeile=60))   # eigene Zuordnung bleibt
        s.add(Kategorie(name="Zuwendungen von Dritten", kontenart="Erlös", euer_zeile=None,
                        beschreibung="z. B. Fördermittel, Zuschüsse, Transferleistungen"))
        s.commit()
        s.close()
        con.execute(text("PRAGMA user_version = 180"))
        con.commit()
    main._run_migrations()
    with eng.connect() as con:
        z = {r[0]: (r[1], r[2]) for r in con.execute(text("SELECT name, euer_zeile, beschreibung FROM kategorien"))}
    assert z["Sonstige Einnahmen"][0] == 16
    assert z["Mahngebühren"][0] == 60
    assert z["Zuwendungen von Dritten"][0] == 16
    assert "Gründungszuschuss" in z["Zuwendungen von Dritten"][1]


def test_zeile_13_nachrichtlich_nicht_in_summe(db):
    """Kleinunternehmer: nicht steuerbare Einnahmen zusätzlich als Davon-Betrag in Zeile 13."""
    _ku(db, True)
    _einnahme(db, "Betriebseinnahmen (Kleinunternehmer)", "1000.00", grund="§19 UStG")
    _einnahme(db, "Mahngebühren", "5.00", grund="§19 UStG")
    _einnahme(db, "Sonstige Einnahmen", "20.00", grund="§19 UStG")
    erg = _berechne_euer(2026, db)
    assert erg["zeilen"][12] == D("1025.00")
    assert erg["zeilen"][13] == D("25.00")
    assert erg["summe_einnahmen"] == D("1025.00")      # Zeile 13 nicht doppelt gezählt
    assert _berechne_euer_kategorien(2026, db)[13] == {"Mahngebühren": D("5.00"), "Sonstige Einnahmen": D("20.00")}


def test_zeile_13_leer_bei_regelbesteuerung(db):
    _einnahme(db, "Mahngebühren", "5.00")
    z = _berechne_euer(2026, db)["zeilen"]
    assert z[16] == D("5.00")
    assert z.get(13, D("0")) == D("0")


def test_zeile_13_storno_hebt_auf(db):
    original = _einnahme(db, "Mahngebühren", "5.00", grund="§19 UStG")
    _einnahme(db, "Mahngebühren", "5.00", art="Ausgabe",
              beschreibung=f"STORNO {original.belegnr}: Korrektur", gruppe_id=original.id)
    assert _berechne_euer(2026, db)["zeilen"].get(13, D("0")) == D("0")


def test_zeile_13_nicht_als_kategorie_zeile_waehlbar():
    from fastapi import HTTPException
    from api.euer import euer_zeilen_auswahl
    from api.kategorien import _pruefe_euer_zeile
    assert 13 not in {z["zeile"] for z in euer_zeilen_auswahl()}
    with pytest.raises(HTTPException):
        _pruefe_euer_zeile(13)
