"""
Issue #554: Eine von Hand eingegebene Rechnungsnummer wurde ohne Widerspruch übernommen, auch
wenn das System sie schon vergeben hatte. Jetzt 409 – beim Anlegen und beim Ändern eines
Entwurfs, je Richtung (ausgang/eingang).
"""
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import create_rechnung, update_rechnung
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate, RechnungUpdate
from database.connection import Base
from database.models import Kunde, Lieferant, Nummernkreis, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O"))
    for typ, fmt in [("rechnung_ausgang", "RE-YY####"), ("rechnung_eingang", "ER-YY####")]:
        session.add(Nummernkreis(bezeichnung=typ, typ=typ, format=fmt, naechste_nr=1, reset_jaehrlich=True, aktiv=True))
    session.add(Kunde(firmenname="JWD GmbH", strasse="Str", hausnummer="2", plz="12345", ort="Ort"))
    session.add(Lieferant(firmenname="Lief GmbH", strasse="Str", hausnummer="3", plz="12345", ort="Ort"))
    session.commit()
    yield session
    session.close()


def _daten(db, **extra) -> RechnungCreate:
    return RechnungCreate(
        typ="ausgang", datum=date(2026, 11, 15), kunde_id=db.query(Kunde).one().id,
        positionen=[RechnungspositionCreate(beschreibung="Reinigung", netto=Decimal("500"), ust_satz=Decimal("19"))],
        **extra,
    )


def test_manuelle_nummer_doppelt_abgelehnt(db):
    erste = create_rechnung(_daten(db), db)
    assert erste.rechnungsnummer == "RE-260001"
    with pytest.raises(HTTPException) as e:
        create_rechnung(_daten(db, rechnungsnummer=" RE-260001 "), db)
    assert e.value.status_code == 409


def test_freie_manuelle_nummer_erlaubt(db):
    create_rechnung(_daten(db), db)
    r = create_rechnung(_daten(db, rechnungsnummer="RE-260005"), db)
    assert r.rechnungsnummer == "RE-260005"


def test_gleiche_nummer_in_anderer_richtung_erlaubt(db):
    create_rechnung(_daten(db, rechnungsnummer="4711"), db)
    eingang = create_rechnung(RechnungCreate(
        typ="eingang", datum=date(2026, 11, 15), lieferant_id=db.query(Lieferant).one().id,
        rechnungsnummer="4711",
        positionen=[RechnungspositionCreate(beschreibung="Material", netto=Decimal("100"), ust_satz=Decimal("19"))],
    ), db)
    assert eingang.rechnungsnummer == "4711"


def test_aendern_auf_vergebene_nummer_abgelehnt(db):
    create_rechnung(_daten(db), db)
    zweite = create_rechnung(_daten(db), db)
    with pytest.raises(HTTPException) as e:
        update_rechnung(zweite.id, RechnungUpdate(rechnungsnummer="RE-260001"), db)
    assert e.value.status_code == 409
    # eigene Nummer unverändert speichern geht weiterhin
    assert update_rechnung(zweite.id, RechnungUpdate(rechnungsnummer=zweite.rechnungsnummer), db).id == zweite.id
