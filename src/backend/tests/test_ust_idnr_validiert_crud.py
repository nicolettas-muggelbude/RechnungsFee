"""
Regressionstest für Issue #358.

Die "über BZSt bestätigt"-Markierung (ust_idnr_validiert + ust_idnr_validierung_datum) muss
über die normalen Kunden-/Lieferanten-Endpunkte lesbar und schreibbar sein - beide Felder waren
vorher entweder gar nicht vorhanden (Lieferant) oder nur read-only in der Response, aber nicht
im Create/Update-Schema (Kunde).
"""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.kunden import create_kunde, update_kunde
from api.lieferanten import create_lieferant, update_lieferant
from api.schemas import KundeCreate, KundeUpdate, LieferantCreate, LieferantUpdate
from database.connection import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_kunde_ust_idnr_validiert_roundtrip(db):
    kunde = create_kunde(KundeCreate(firmenname="Muster GmbH", land="NL", ust_idnr="NL123456789B01"), db)
    assert kunde.ust_idnr_validiert is False
    assert kunde.ust_idnr_validierung_datum is None

    heute = date(2026, 8, 17)
    aktualisiert = update_kunde(
        kunde.id,
        KundeUpdate(ust_idnr_validiert=True, ust_idnr_validierung_datum=heute),
        db,
    )
    assert aktualisiert.ust_idnr_validiert is True
    assert aktualisiert.ust_idnr_validierung_datum == heute


def test_lieferant_ust_idnr_validiert_roundtrip(db):
    lieferant = create_lieferant(LieferantCreate(firmenname="Supplier BV", land="NL", ust_idnr="NL123456789B01"), db)
    assert lieferant.ust_idnr_validiert is False
    assert lieferant.ust_idnr_validierung_datum is None

    heute = date(2026, 8, 17)
    aktualisiert = update_lieferant(
        lieferant.id,
        LieferantUpdate(ust_idnr_validiert=True, ust_idnr_validierung_datum=heute),
        db,
    )
    assert aktualisiert.ust_idnr_validiert is True
    assert aktualisiert.ust_idnr_validierung_datum == heute
