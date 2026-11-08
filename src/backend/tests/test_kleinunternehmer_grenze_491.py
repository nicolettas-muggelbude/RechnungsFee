"""
Issue #491: Kleinunternehmer-Warnung nach § 19 UStG (seit 2025).

Gesamtumsatz aus der EÜR-Zuordnung je Buchung (Journal, Zahlungsdatum, netto), ohne nicht
steuerbare Einnahmen (Zeile 13) und ohne Anlagevermögen, je Kalenderjahr, zuzüglich Umsatz vor
RechnungsFee. Grenzen: Vorjahr 25.000 €, laufendes Jahr 100.000 €, Gründungsjahr 25.000 €.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.euer import kleinunternehmer_gesamtumsatz
from api.setup import kleinunternehmer_umsatz
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Unternehmen

HEUTE = date(2026, 11, 7)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O",
                            ist_kleinunternehmer=True))
    session.add_all([
        Kategorie(name="Betriebseinnahmen (Kleinunternehmer)", kontenart="Erlös", euer_zeile=12,
                  konto_skr03="8192", konto_skr04="4184"),
        Kategorie(name="Mahngebühren", kontenart="Erlös", euer_zeile=16, konto_skr03="8800", konto_skr04="4800"),
        Kategorie(name="Betriebseinnahmen", kontenart="Erlös", euer_zeile=15, konto_skr03="8400", konto_skr04="4400"),
        Kategorie(name="KFZ (Kauf)", kontenart="Anlage", konto_skr03="0320", konto_skr04="0540"),
    ])
    session.commit()
    yield session
    session.close()


_nr = iter(range(1, 10_000))


def _buche(db, kategorie: str, betrag: str, datum: date, art="Einnahme", grund="§19 UStG", ust="0", **extra):
    kat = db.query(Kategorie).filter(Kategorie.name == kategorie).one()
    b = Decimal(betrag)
    u = Decimal(ust)
    e = Journaleintrag(
        datum=datum, belegnr=f"J-{next(_nr)}", beschreibung=extra.pop("beschreibung", "Test"),
        kategorie_id=kat.id, zahlungsart="Bank", art=art,
        netto_betrag=b - u, ust_satz=Decimal("19") if u else Decimal("0"), ust_betrag=u,
        vorsteuer_betrag=Decimal("0"), brutto_betrag=b, steuerbefreiung_grund=grund, **extra,
    )
    db.add(e)
    db.commit()
    return e


def _unt(db) -> Unternehmen:
    return db.query(Unternehmen).one()


def test_gesamtumsatz_aus_journal_ohne_nicht_steuerbare_und_anlage(db):
    _buche(db, "Betriebseinnahmen (Kleinunternehmer)", "10000.00", date(2026, 3, 1))
    _buche(db, "Betriebseinnahmen (Kleinunternehmer)", "2500.00", date(2026, 6, 1))
    _buche(db, "Mahngebühren", "40.00", date(2026, 7, 1))            # nicht steuerbar → Zeile 13
    _buche(db, "KFZ (Kauf)", "5000.00", date(2026, 8, 1))            # Anlagevermögen zählt nicht
    _buche(db, "Betriebseinnahmen (Kleinunternehmer)", "999.00", date(2025, 12, 31))  # Vorjahr
    assert kleinunternehmer_gesamtumsatz(2026, db) == Decimal("12500.00")
    assert kleinunternehmer_gesamtumsatz(2025, db) == Decimal("999.00")


def test_storno_mindert_den_umsatz(db):
    original = _buche(db, "Betriebseinnahmen (Kleinunternehmer)", "1000.00", date(2026, 3, 1))
    _buche(db, "Betriebseinnahmen (Kleinunternehmer)", "1000.00", date(2026, 3, 1), art="Ausgabe",
           grund=None, gruppe_id=original.id, beschreibung=f"STORNO {original.belegnr}: Korrektur")
    assert kleinunternehmer_gesamtumsatz(2026, db) == Decimal("0.00")


def test_regelbesteuerte_buchungen_im_wechseljahr_zaehlen_netto(db):
    _buche(db, "Betriebseinnahmen", "1190.00", date(2026, 2, 1), grund=None, ust="190.00")
    _buche(db, "Betriebseinnahmen (Kleinunternehmer)", "500.00", date(2026, 9, 1))
    assert kleinunternehmer_gesamtumsatz(2026, db) == Decimal("1500.00")


def test_kalenderjahr_auch_bei_abweichendem_wirtschaftsjahr(db):
    u = _unt(db)
    u.wirtschaftsjahr_abweichend_aktiv = True
    u.geschaeftsjahr_beginn = 7
    db.commit()
    _buche(db, "Betriebseinnahmen (Kleinunternehmer)", "100.00", date(2026, 1, 15))
    _buche(db, "Betriebseinnahmen (Kleinunternehmer)", "200.00", date(2026, 12, 15))
    assert kleinunternehmer_gesamtumsatz(2026, db) == Decimal("300.00")


def test_laufendes_jahr_grenze_100000(db):
    _buche(db, "Betriebseinnahmen (Kleinunternehmer)", "85000.00", date(2026, 5, 1))
    r = kleinunternehmer_umsatz(db, heute=HEUTE)
    assert r["grenze_kritisch"] == 100000.0
    assert r["grenze_warnung"] == 80000.0
    assert r["umsatz_netto"] == 85000.0
    assert r["ist_gruendungsjahr"] is False


def test_gruendungsjahr_grenze_25000(db):
    _unt(db).taetigkeit_beginn = date(2026, 4, 1)
    db.commit()
    _buche(db, "Betriebseinnahmen (Kleinunternehmer)", "21000.00", date(2026, 9, 1))
    r = kleinunternehmer_umsatz(db, heute=HEUTE)
    assert r["ist_gruendungsjahr"] is True
    assert r["grenze_kritisch"] == 25000.0
    assert r["grenze_warnung"] == 20000.0
    assert r["vorjahr_ueberschritten"] is False


def test_vorjahr_ueber_25000(db):
    _unt(db).taetigkeit_beginn = date(2024, 1, 1)
    db.commit()
    _buche(db, "Betriebseinnahmen (Kleinunternehmer)", "26000.00", date(2025, 6, 1))
    r = kleinunternehmer_umsatz(db, heute=HEUTE)
    assert r["vorjahr"] == 2025
    assert r["umsatz_vorjahr"] == 26000.0
    assert r["vorjahr_ueberschritten"] is True


def test_vorjahr_genau_25000_ist_noch_erlaubt(db):
    _buche(db, "Betriebseinnahmen (Kleinunternehmer)", "25000.00", date(2025, 6, 1))
    assert kleinunternehmer_umsatz(db, heute=HEUTE)["vorjahr_ueberschritten"] is False


def test_beginn_im_laufenden_jahr_kein_vorjahr(db):
    _unt(db).taetigkeit_beginn = date(2026, 2, 1)
    db.commit()
    _buche(db, "Betriebseinnahmen (Kleinunternehmer)", "30000.00", date(2025, 6, 1))  # z. B. Testbuchung
    r = kleinunternehmer_umsatz(db, heute=HEUTE)
    assert r["umsatz_vorjahr"] == 0.0
    assert r["vorjahr_ueberschritten"] is False


def test_umsatz_vor_rechnungsfee(db):
    u = _unt(db)
    u.umsatz_extern_jahr = 2026
    u.umsatz_extern_startjahr = Decimal("70000")
    u.umsatz_extern_vorjahr = Decimal("26000")
    db.commit()
    _buche(db, "Betriebseinnahmen (Kleinunternehmer)", "15000.00", date(2026, 10, 1))
    r = kleinunternehmer_umsatz(db, heute=HEUTE)
    assert r["umsatz_netto"] == 85000.0
    assert r["umsatz_extern"] == 70000.0
    assert r["umsatz_vorjahr"] == 26000.0
    assert r["vorjahr_ueberschritten"] is True


def test_umsatz_vor_rechnungsfee_gilt_nicht_fuer_spaetere_jahre(db):
    u = _unt(db)
    u.umsatz_extern_jahr = 2024
    u.umsatz_extern_startjahr = Decimal("50000")
    db.commit()
    r = kleinunternehmer_umsatz(db, heute=HEUTE)
    assert r["umsatz_netto"] == 0.0
    assert r["umsatz_vorjahr"] == 0.0
