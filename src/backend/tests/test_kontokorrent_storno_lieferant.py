"""
Issue #533: Stornierte Eingangsrechnung blieb im Lieferanten-Kontokorrent als offene
Verbindlichkeit stehen - kontokorrent_lieferant()/_kontokorrent_bewegungen_lieferant()
kannten (anders als die Kunden-Seite) keine Storno-Gegenzeile.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.kontokorrent import kontokorrent_uebersicht
from api.lieferanten import _kontokorrent_bewegungen_lieferant, kontokorrent_lieferant
from database.connection import Base
from database.models import Journaleintrag, Lieferant, Rechnung, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    session.commit()
    yield session
    session.close()


def _lieferant(db) -> Lieferant:
    l = Lieferant(firmenname="Musterlieferant GmbH")
    db.add(l)
    db.commit()
    db.refresh(l)
    return l


def _eingang(db, lieferant, brutto="20.00", **kw) -> Rechnung:
    r = Rechnung(
        typ="eingang", lieferant_id=lieferant.id, rechnungsnummer="ER-260009",
        datum=date(2026, 11, 2), dokument_typ=kw.pop("dokument_typ", "Rechnung"),
        brutto_gesamt=Decimal(brutto), netto_gesamt=Decimal(brutto), ust_gesamt=Decimal("0"),
        ist_entwurf=False, **kw,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def _stornieren(db, r):
    r.storniert = True
    r.storno_grund = "Falsch erfasst"
    r.storno_datum = date(2026, 11, 10)
    r.storno_rechnungsnummer = "STORNO-260001"
    db.commit()


def test_unbezahlte_stornierte_eingangsrechnung_ist_ausgeglichen(db):
    l = _lieferant(db)
    r = _eingang(db, l)
    assert kontokorrent_lieferant(l.id, db)[-1].saldo == 20.0

    _stornieren(db, r)
    bewegungen = kontokorrent_lieferant(l.id, db)
    assert [b.typ for b in bewegungen] == ["rechnung", "storno"]
    assert bewegungen[-1].saldo == 0.0
    assert all(p.partner_id != l.id for p in kontokorrent_uebersicht(db))


def test_bezahlte_stornierte_eingangsrechnung_zeigt_guthaben(db):
    l = _lieferant(db)
    r = _eingang(db, l, zahlungsstatus="bezahlt", bezahlt_betrag=Decimal("20.00"))
    db.add(Journaleintrag(
        datum=date(2026, 11, 3), belegnr="Z-1", beschreibung="Zahlung", zahlungsart="Bank",
        art="Ausgabe", netto_betrag=Decimal("20.00"), brutto_betrag=Decimal("20.00"), rechnung_id=r.id,
    ))
    db.commit()
    _stornieren(db, r)
    # Storno-Gegenbuchung der Zahlung (art=Einnahme) zählt nicht → Guthaben beim Lieferanten
    db.add(Journaleintrag(
        datum=date(2026, 11, 3), belegnr="Z-2", beschreibung="STORNO Z-1: ER-260009", zahlungsart="Bank",
        art="Einnahme", netto_betrag=Decimal("20.00"), brutto_betrag=Decimal("20.00"), rechnung_id=r.id,
    ))
    db.commit()
    assert kontokorrent_lieferant(l.id, db)[-1].saldo == -20.0


def test_stornierte_lieferantengutschrift_hebt_sich_auf(db):
    l = _lieferant(db)
    _eingang(db, l, brutto="50.00")
    gs = _eingang(db, l, brutto="-10.00", dokument_typ="Gutschrift")
    assert kontokorrent_lieferant(l.id, db)[-1].saldo == 40.0
    _stornieren(db, gs)
    assert kontokorrent_lieferant(l.id, db)[-1].saldo == 50.0


def test_zeitraum_storno_nach_eigenem_datum(db):
    l = _lieferant(db)
    r = _eingang(db, l)
    _stornieren(db, r)
    # Zeitraum nur bis vor dem Stornodatum: Storno-Zeile fehlt noch
    bew, _ = _kontokorrent_bewegungen_lieferant(l.id, date(2026, 11, 1), date(2026, 11, 5), db)
    assert [b["typ"] for b in bew] == ["rechnung"]
    # Zeitraum nur mit Stornodatum: nur die Storno-Zeile
    bew, _ = _kontokorrent_bewegungen_lieferant(l.id, date(2026, 11, 6), date(2026, 11, 30), db)
    assert [b["typ"] for b in bew] == ["storno"]
    bew, _ = _kontokorrent_bewegungen_lieferant(l.id, date(2026, 11, 1), date(2026, 11, 30), db)
    assert round(sum(b["betrag"] for b in bew), 2) == 0.0
