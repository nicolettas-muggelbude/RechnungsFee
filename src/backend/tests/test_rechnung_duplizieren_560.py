"""
Issue #560: Rechnung duplizieren - neuer Entwurf nach dem Muster einer bestehenden Ausgangsrechnung.
Datum heute, neue Nummer; Kunde, Texte, Erfassungsmodus übernommen, Positionen auf Wunsch.
"""
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import create_rechnung, finalisiere_rechnung, rechnung_duplizieren
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate
from database.connection import Base
from database.models import Kunde, Nummernkreis, Rechnung, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O",
                            standard_zahlungsziel=14))
    for typ, fmt in [("rechnung_ausgang", "RE-YY####"), ("rechnung_eingang", "ER-YY####")]:
        session.add(Nummernkreis(bezeichnung=typ, typ=typ, format=fmt, naechste_nr=1, reset_jaehrlich=True, aktiv=True))
    session.add(Kunde(firmenname="Stammkunde GmbH", strasse="Str", hausnummer="2", plz="12345", ort="Ort"))
    session.commit()
    yield session
    session.close()


def _vorlage(db) -> Rechnung:
    r = create_rechnung(RechnungCreate(
        typ="ausgang", datum=date(2026, 3, 1), kunde_id=db.query(Kunde).one().id, eingabemodus="brutto",
        einleitungstext="Für die Wartung berechne ich:", schlusstext="Danke!", kunden_bestellnummer="PO-1",
        positionen=[RechnungspositionCreate(beschreibung="Wartung", menge=Decimal("2"), einheit="Std",
                                            netto=Decimal("119"), ust_satz=Decimal("19"))],
    ), db)
    finalisiere_rechnung(r.id, db)
    return db.query(Rechnung).filter(Rechnung.id == r.id).one()


def test_mit_positionen(db):
    alt = _vorlage(db)
    neu = rechnung_duplizieren(alt.id, mit_positionen=True, db=db)
    assert neu.id != alt.id and neu.ist_entwurf
    assert neu.rechnungsnummer != alt.rechnungsnummer
    assert neu.datum == date.today()
    assert (neu.kunde_id, neu.einleitungstext, neu.schlusstext, neu.eingabemodus) == (
        alt.kunde_id, alt.einleitungstext, alt.schlusstext, "brutto")
    assert neu.kunden_bestellnummer is None
    assert len(neu.positionen) == 1
    assert Decimal(str(neu.brutto_gesamt)) == Decimal(str(alt.brutto_gesamt))


def test_ohne_positionen(db):
    neu = rechnung_duplizieren(_vorlage(db).id, mit_positionen=False, db=db)
    assert neu.kunde_id is not None
    assert len(neu.positionen) == 1 and neu.positionen[0].beschreibung == ""
    assert Decimal(str(neu.brutto_gesamt)) == Decimal("0")


def test_nur_ausgangsrechnungen(db):
    eingang = Rechnung(typ="eingang", datum=date(2026, 3, 1))
    db.add(eingang)
    db.commit()
    with pytest.raises(HTTPException) as exc:
        rechnung_duplizieren(eingang.id, mit_positionen=True, db=db)
    assert exc.value.status_code == 422
