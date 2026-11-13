"""
Issue #522: Eine einmal gespeicherte Notiz an Angebot/Auftrag/Proforma/Rechnung ließ sich
nicht mehr entfernen. Das Formular schickte eine leere Notiz als undefined (Feld fehlt im
Request), update_rechnung() übernahm notizen nur bei "is not None" - die alte Notiz blieb.
Jetzt: Frontend schickt null, Backend wertet notizen über model_fields_set aus.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import create_rechnung, update_rechnung
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate, RechnungUpdate
from database.connection import Base
from database.models import Rechnung, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    session.commit()
    yield session
    session.close()


def _entwurf(db, notizen="Alte Notiz"):
    payload = RechnungCreate(
        typ="ausgang", datum=date(2026, 11, 8), partner_freitext="Testkunde",
        notizen=notizen, ist_entwurf=True,
        positionen=[RechnungspositionCreate(
            beschreibung="Beratung", menge=Decimal("1"), einheit="Stk.", netto="100.00", ust_satz="19",
        )],
    )
    return create_rechnung(payload, db).id


def _notiz(db, rid):
    return db.query(Rechnung).filter(Rechnung.id == rid).first().notizen


def test_notiz_laesst_sich_entfernen(db):
    rid = _entwurf(db)
    update_rechnung(rid, RechnungUpdate(notizen=None), db)
    assert _notiz(db, rid) is None


def test_nur_leerzeichen_entfernt_notiz(db):
    rid = _entwurf(db)
    update_rechnung(rid, RechnungUpdate(notizen="   "), db)
    assert _notiz(db, rid) is None


def test_notiz_aendern(db):
    rid = _entwurf(db)
    update_rechnung(rid, RechnungUpdate(notizen="Neue Notiz"), db)
    assert _notiz(db, rid) == "Neue Notiz"


def test_update_ohne_notizen_laesst_notiz_stehen(db):
    rid = _entwurf(db)
    update_rechnung(rid, RechnungUpdate(einleitungstext="Hallo"), db)
    assert _notiz(db, rid) == "Alte Notiz"
