"""
Regressionstests für Drittland-Dienstleistungen (§3a Abs. 2 UStG, Issue #315).

Analog zur ig. Lieferung (Issue #316): _erloes_kategorie() muss bei
rechnung.ist_drittland_leistung die eigene Kategorie "Nicht steuerbare
Auslandsumsätze (Drittland)" (Konto 8338/4338) liefern statt der generischen
0%-Kategorie "Betriebseinnahmen (0%)", sonst landet der Umsatz auf dem
falschen Konto und in der falschen EÜR-Zeile.
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


def _kategorie_drittland(db) -> Kategorie:
    kat = Kategorie(
        name="Nicht steuerbare Auslandsumsätze (Drittland)", kontenart="Erlös",
        konto_skr03="8338", konto_skr04="4338", euer_zeile=16,
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
        ist_entwurf=False, ist_drittland_leistung=True,
    )
    defaults.update(kwargs)
    rechnung = Rechnung(**defaults)
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Beratungsleistung",
        menge=Decimal("1"), netto=Decimal("500.00"), ust_satz=Decimal("0"), brutto=Decimal("500.00"),
    ))
    db.commit()
    db.refresh(rechnung)
    return rechnung


def test_erloes_kategorie_liefert_drittland_kategorie(db):
    kat_drittland = _kategorie_drittland(db)
    rechnung = _rechnung_mit_position(db)

    kat_id, kat = _erloes_kategorie(db, rechnung)

    assert kat_id == kat_drittland.id
    assert kat.konto_skr03 == "8338"


def test_zahlung_bucht_auf_drittland_konto(db):
    _kategorie_drittland(db)
    rechnung = _rechnung_mit_position(db)
    db.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    db.commit()

    zahlung_bar_erstellen(rechnung.id, BarZahlungCreate(datum=date(2026, 1, 5), zahlungsart="Bank"), db)

    eintrag = db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == rechnung.id).first()
    assert eintrag is not None
    assert eintrag.konto_skr03 == "8338"
    assert eintrag.konto_skr04 == "4338"
    assert eintrag.ust_satz == 0
