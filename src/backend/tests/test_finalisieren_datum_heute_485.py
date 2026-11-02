"""
Issue #485: Rechnungsdatum eines älteren Entwurfs beim Finalisieren auf heute setzen.

Nur auf ausdrücklichen Wunsch (datum_heute=True, Nachfrage im Frontend) und nur für eigene
Ausgangsrechnungen; die Fälligkeit verschiebt sich um dieselben Tage.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import finalisiere_rechnung
from database.connection import Base
from database.models import Rechnung, Unternehmen

HEUTE = date.today()
ALT = HEUTE - timedelta(days=24)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Test", strasse="X", hausnummer="1", plz="12345", ort="Y"))
    session.commit()
    yield session
    session.close()


def _entwurf(db, typ="ausgang", import_quelle=None, faellig=True) -> Rechnung:
    r = Rechnung(
        typ=typ, rechnungsnummer=f"RE-{typ}-{import_quelle}", datum=ALT,
        faellig_am=ALT + timedelta(days=14) if faellig else None,
        netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("19.00"), brutto_gesamt=Decimal("119.00"),
        ist_entwurf=True, import_quelle=import_quelle,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def test_datum_heute_setzt_datum_und_verschiebt_faelligkeit(db):
    r = _entwurf(db)
    finalisiere_rechnung(r.id, datum_heute=True, db=db)
    db.refresh(r)
    assert r.datum == HEUTE
    assert r.faellig_am == HEUTE + timedelta(days=14)
    assert r.ist_entwurf is False


def test_ohne_wunsch_bleibt_datum(db):
    r = _entwurf(db)
    finalisiere_rechnung(r.id, datum_heute=False, db=db)
    db.refresh(r)
    assert r.datum == ALT
    assert r.faellig_am == ALT + timedelta(days=14)


def test_ohne_faelligkeit(db):
    r = _entwurf(db, faellig=False)
    finalisiere_rechnung(r.id, datum_heute=True, db=db)
    db.refresh(r)
    assert r.datum == HEUTE
    assert r.faellig_am is None


def test_extern_erstellte_rechnung_behaelt_datum(db):
    r = _entwurf(db, import_quelle="extern")
    finalisiere_rechnung(r.id, datum_heute=True, db=db)
    db.refresh(r)
    assert r.datum == ALT


def test_lieferschein_behaelt_datum(db):
    r = _entwurf(db)
    r.dokument_typ = "Lieferschein"
    db.commit()
    finalisiere_rechnung(r.id, datum_heute=True, db=db)
    db.refresh(r)
    assert r.datum == ALT


def test_positionsaufruf_ohne_datum_heute(db):
    """Bestehende Aufrufe finalisiere_rechnung(id, db) bleiben gültig."""
    r = _entwurf(db)
    finalisiere_rechnung(r.id, db)
    db.refresh(r)
    assert r.datum == ALT
