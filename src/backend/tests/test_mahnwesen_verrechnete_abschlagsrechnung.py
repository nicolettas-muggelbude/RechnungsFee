"""
Regressionstest für Issue #419 Phase 2b (Nutzer-Report): eine überfällige Abschlagsrechnung
blieb in der Mahnwesen-Übersicht (GET /faellig) sichtbar, obwohl sie längst in einer
Schlussrechnung verrechnet wurde - die anderen vier Mahnwesen-Abfragen hatten den
verrechnet_in_rechnung_id-Filter bereits, diese fünfte Stelle (faellig_liste()) war beim
ursprünglichen Phase-2b-Umbau übersehen worden.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.mahnwesen import faellig_liste
from database.connection import Base
from database.models import Kunde, Mahnstufe, Rechnung, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(firmenname="Testfirma GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    session.add(Mahnstufe(stufe=1, bezeichnung="Zahlungserinnerung", mahngebuehr_aktiv=False))
    kunde = Kunde(firmenname="Testkunde GmbH")
    session.add(kunde)
    session.commit()
    session.refresh(kunde)
    yield session, kunde.id
    session.close()


def _ueberfaellige_abschlagsrechnung(db, kunde_id, verrechnet_in_rechnung_id=None) -> Rechnung:
    r = Rechnung(
        typ="ausgang", kunde_id=kunde_id, rechnungsnummer="AR-26-0001", dokument_typ="Abschlagsrechnung",
        datum=date.today() - timedelta(days=30), faellig_am=date.today() - timedelta(days=14),
        brutto_gesamt=Decimal("119.00"), netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("19.00"),
        ist_entwurf=False, zahlungsstatus="offen", bezahlt_betrag=Decimal("0.00"),
        verrechnet_in_rechnung_id=verrechnet_in_rechnung_id,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def test_ueberfaellige_abschlagsrechnung_erscheint_in_faellig_liste(db):
    session, kunde_id = db
    _ueberfaellige_abschlagsrechnung(session, kunde_id)

    ergebnis = faellig_liste(db=session)

    assert len(ergebnis) == 1


def test_verrechnete_ueberfaellige_abschlagsrechnung_erscheint_nicht_mehr(db):
    session, kunde_id = db
    _ueberfaellige_abschlagsrechnung(session, kunde_id, verrechnet_in_rechnung_id=999)

    ergebnis = faellig_liste(db=session)

    assert ergebnis == []
