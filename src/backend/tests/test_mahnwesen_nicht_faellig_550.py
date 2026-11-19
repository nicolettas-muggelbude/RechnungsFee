"""
Issue #550 (Markus): Ab der zusammenfassenden Mahnstufe (konsolidiert_ab_stufe) nahm die Mahnung
ALLE offenen Rechnungen des Kunden auf - auch eine, deren Zahlungsziel noch in der Zukunft lag.
Mitgemahnt werden nur bereits überfällige Rechnungen.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.mahnwesen import _get_or_create_einstellungen, erstellen
from api.schemas import MahnungErstellenRequest
from database.connection import Base
from database.models import Kunde, Mahnstufe, Nummernkreis, Rechnung, Unternehmen

HEUTE = date.today()


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O"))
    session.add(Nummernkreis(bezeichnung="mahnung", typ="mahnung", format="MA-YY####", naechste_nr=1,
                             reset_jaehrlich=True, aktiv=True))
    session.add_all([
        Mahnstufe(stufe=1, bezeichnung="Zahlungserinnerung", mahngebuehr_aktiv=False),
        Mahnstufe(stufe=2, bezeichnung="1. Mahnung", mahngebuehr_aktiv=False),
    ])
    session.add(Kunde(firmenname="Kunde GmbH"))
    session.commit()
    yield session
    session.close()


def _rechnung(db, nr, faellig_am, **extra) -> Rechnung:
    r = Rechnung(
        typ="ausgang", kunde_id=db.query(Kunde).one().id, rechnungsnummer=nr, dokument_typ="Rechnung",
        datum=faellig_am - timedelta(days=14), faellig_am=faellig_am,
        brutto_gesamt=Decimal("119.00"), netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("19.00"),
        ist_entwurf=False, zahlungsstatus="offen", bezahlt_betrag=Decimal("0.00"), **extra,
    )
    db.add(r)
    db.commit()
    return r


def test_noch_nicht_faellige_rechnung_wird_nicht_mitgemahnt(db):
    _get_or_create_einstellungen(db)
    ueberfaellig = _rechnung(db, "RE-1", HEUTE - timedelta(days=2))
    zukunft = _rechnung(db, "RE-2", HEUTE + timedelta(days=13))
    weitere_ueberfaellig = _rechnung(db, "RE-3", HEUTE - timedelta(days=20))

    mahnung = erstellen(MahnungErstellenRequest(rechnung_ids=[ueberfaellig.id], stufe=2), db)

    assert set(mahnung.rechnung_ids) == {ueberfaellig.id, weitere_ueberfaellig.id}
    db.refresh(zukunft)
    assert zukunft.mahnstufe_aktuell == 0


def test_heute_faellige_rechnung_wird_nicht_mitgemahnt(db):
    _get_or_create_einstellungen(db)
    ueberfaellig = _rechnung(db, "RE-1", HEUTE - timedelta(days=2))
    _rechnung(db, "RE-2", HEUTE)

    mahnung = erstellen(MahnungErstellenRequest(rechnung_ids=[ueberfaellig.id], stufe=2), db)

    assert mahnung.rechnung_ids == [ueberfaellig.id]


def test_importierte_rechnung_wird_nicht_mitgemahnt(db):
    _get_or_create_einstellungen(db)
    ueberfaellig = _rechnung(db, "RE-1", HEUTE - timedelta(days=2))
    _rechnung(db, "ALT-1", HEUTE - timedelta(days=30), import_quelle="papierkram")

    mahnung = erstellen(MahnungErstellenRequest(rechnung_ids=[ueberfaellig.id], stufe=2), db)

    assert mahnung.rechnung_ids == [ueberfaellig.id]
