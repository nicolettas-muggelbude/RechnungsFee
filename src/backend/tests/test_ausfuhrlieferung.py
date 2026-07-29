"""
Regressionstests für Ausfuhrlieferung (§4 Nr. 1a i.V.m. §6 UStG, Issue #323).

Analog zur ig. Lieferung/Drittland-Dienstleistung: _erloes_kategorie() muss bei
rechnung.ist_ausfuhrlieferung die eigene Kategorie "Steuerfreie Ausfuhrlieferungen
(Drittland)" (Konto 8120/4120) liefern statt der generischen 0%-Kategorie
"Betriebseinnahmen (0%)".
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import _erloes_kategorie, zahlung_bar_erstellen
from api.schemas_rechnungen import BarZahlungCreate
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Rechnung, Rechnungsposition, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _kategorie_ausfuhr(db) -> Kategorie:
    kat = Kategorie(
        name="Steuerfreie Ausfuhrlieferungen (Drittland)", kontenart="Erlös",
        konto_skr03="8120", konto_skr04="4120", euer_zeile=16,
        vorsteuer_prozent=0, ust_satz_standard=0,
    )
    db.add(kat)
    db.commit()
    db.refresh(kat)
    return kat


def _rechnung_mit_position(db, **kwargs) -> Rechnung:
    defaults = dict(
        typ="ausgang", rechnungsnummer="RE-1", datum=date(2026, 1, 1),
        brutto_gesamt=Decimal("500.00"), netto_gesamt=Decimal("500.00"),
        ist_entwurf=False, ist_ausfuhrlieferung=True,
    )
    defaults.update(kwargs)
    rechnung = Rechnung(**defaults)
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Handelsware",
        menge=Decimal("1"), netto=Decimal("500.00"), ust_satz=Decimal("0"), brutto=Decimal("500.00"),
    ))
    db.commit()
    db.refresh(rechnung)
    return rechnung


def test_erloes_kategorie_liefert_ausfuhr_kategorie(db):
    kat_ausfuhr = _kategorie_ausfuhr(db)
    rechnung = _rechnung_mit_position(db)

    kat_id, kat = _erloes_kategorie(db, rechnung)

    assert kat_id == kat_ausfuhr.id
    assert kat.konto_skr03 == "8120"


def test_zahlung_bucht_auf_ausfuhr_konto(db):
    _kategorie_ausfuhr(db)
    rechnung = _rechnung_mit_position(db)
    db.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    db.commit()

    zahlung_bar_erstellen(rechnung.id, BarZahlungCreate(datum=date(2026, 1, 5), zahlungsart="Bank"), db)

    eintrag = db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == rechnung.id).first()
    assert eintrag is not None
    assert eintrag.konto_skr03 == "8120"
    assert eintrag.konto_skr04 == "4120"
    assert eintrag.ust_satz == 0
