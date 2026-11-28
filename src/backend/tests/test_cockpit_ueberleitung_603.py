"""
Issue #603: Überleitung Dashboard-Kacheln (brutto, alle Zahlungen) → Cockpit (netto, EÜR-relevant).

Die Summen der Überleitung müssen exakt den Kacheln (Dashboard.tsx: brutto, ohne Privat/Neutral)
und den Cockpit-KPIs für denselben Zeitraum entsprechen, und jede Kategorie bekommt einen
verständlichen Grund für die Abweichung.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.cockpit import get_cockpit, get_ueberleitung
from database.connection import Base
from database.models import Journaleintrag, Kategorie

D = Decimal


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _kat(db, name, kontenart, zeile):
    k = Kategorie(name=name, kontenart=kontenart, euer_zeile=zeile, vorsteuer_prozent=100)
    db.add(k)
    db.commit()
    return k


def _buchung(db, nr, kat, art, netto, ust, brutto, vorsteuer=D("0"), beschreibung="Test", tag=10):
    e = Journaleintrag(
        datum=date(2026, 3, tag), belegnr=nr, beschreibung=beschreibung, kategorie_id=kat.id,
        zahlungsart="Bank", art=art, netto_betrag=netto, ust_satz=D("19") if ust else D("0"),
        ust_betrag=ust, vorsteuerabzug=bool(vorsteuer), vorsteuer_betrag=vorsteuer, brutto_betrag=brutto,
    )
    db.add(e)
    db.commit()
    return e


@pytest.fixture
def szenario(db):
    erloes = _kat(db, "Betriebseinnahmen", "Erlös", 15)
    buero = _kat(db, "Bürobedarf", "Aufwand", 51)
    anlage = _kat(db, "Büroeinrichtung (Anlage)", "Anlage", None)
    ohne_zeile = _kat(db, "Eigene Kategorie", "Aufwand", None)
    erstattung = _kat(db, "USt-Erstattung FA", "Erlös", 18)
    privat = _kat(db, "Privatentnahme", "Privat", 106)

    _buchung(db, "B1", erloes, "Einnahme", D("100.00"), D("19.00"), D("119.00"))
    original = _buchung(db, "B2", buero, "Ausgabe", D("100.00"), D("19.00"), D("119.00"), D("19.00"))
    _buchung(db, "B3", anlage, "Ausgabe", D("1000.00"), D("190.00"), D("1190.00"), D("190.00"))
    _buchung(db, "B4", ohne_zeile, "Ausgabe", D("50.00"), D("0"), D("50.00"))
    _buchung(db, "B5", erstattung, "Einnahme", D("50.00"), D("0"), D("50.00"))
    _buchung(db, "B6", privat, "Ausgabe", D("300.00"), D("0"), D("300.00"))
    # Storno der Büro-Ausgabe: art=Einnahme, Vorsteuer gespiegelt (negativ)
    storno = _buchung(db, "B7", buero, "Einnahme", D("100.00"), D("19.00"), D("119.00"), D("-19.00"),
                      beschreibung="STORNO B2: Test", tag=11)
    storno.gruppe_id = original.id
    db.commit()
    return db


def test_summen_entsprechen_kacheln_und_cockpit(szenario):
    db = szenario
    erg = get_ueberleitung(von=date(2026, 3, 1), bis=date(2026, 3, 31), db=db)
    s = erg["summen"]
    # Kacheln: brutto je Buchungsrichtung, Privat nicht mitgezählt
    assert s["kachel_eingaenge"] == 119.0 + 50.0 + 119.0
    assert s["kachel_ausgaenge"] == 119.0 + 1190.0 + 50.0
    # Cockpit für denselben Zeitraum
    cockpit = get_cockpit(zeitraum="monat", wert="2026-03", db=db)["kpis"]
    assert s["cockpit_einnahmen"] == cockpit["einnahmen"] == 100.0
    assert s["cockpit_ausgaben"] == cockpit["ausgaben"] == 0.0


def test_gruende_je_kategorie(szenario):
    erg = get_ueberleitung(von=date(2026, 3, 1), bis=date(2026, 3, 31), db=szenario)
    ein = {x["kategorie"]: x for x in erg["eingaenge"]}
    aus = {x["kategorie"]: x for x in erg["ausgaenge"]}

    assert "netto" in ein["Betriebseinnahmen"]["grund"]
    assert ein["Betriebseinnahmen"]["cockpit_einnahmen"] == 100.0
    assert "Zeile 18" in ein["USt-Erstattung FA"]["grund"]
    # Storno einer Ausgabe steht bei den Eingängen und mindert die Cockpit-Ausgaben
    assert ein["Bürobedarf"]["cockpit_ausgaben"] == -100.0
    assert "Anlagekauf" in aus["Büroeinrichtung (Anlage)"]["grund"]
    assert "ohne EÜR-Zeile" in aus["Eigene Kategorie"]["grund"]
    assert aus["Bürobedarf"]["cockpit_ausgaben"] == 100.0
    # Privatbuchungen zählen in keiner der beiden Sichten
    assert "Privatentnahme" not in aus and not erg["nicht_in_kacheln"]


def test_zeitraum_grenzen(szenario):
    erg = get_ueberleitung(von=date(2026, 3, 11), bis=date(2026, 3, 31), db=szenario)
    assert erg["summen"]["kachel_eingaenge"] == 119.0  # nur das Storno
    assert erg["summen"]["kachel_ausgaenge"] == 0.0
