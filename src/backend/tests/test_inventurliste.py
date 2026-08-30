"""
Inventurliste (§240 HGB, schlanke Variante): Bestandsliste zum Stichtag für Artikel mit
aktiver Lagerführung. Prüft die zentrale Filterlogik (nur lager_aktiv+aktiv, konsistent zu
api/artikel.py::get_lagerwarnung) und die Wertberechnung (Bestand × EK-Preis).
"""
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.inventurliste import _inventur_zeilen
from database.connection import Base
from database.models import Artikel, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    session.commit()
    yield session
    session.close()


def _artikel(db, **kwargs) -> Artikel:
    defaults = dict(
        artikelnummer="ART-0001", typ="artikel", bezeichnung="Testartikel",
        einheit="Stück", vk_brutto=Decimal("11.90"), vk_netto=Decimal("10.00"),
        lager_aktiv=True, aktiv=True, bestand_aktuell=Decimal("5"),
    )
    defaults.update(kwargs)
    a = Artikel(**defaults)
    db.add(a)
    db.commit()
    return a


def test_nur_lagerartikel_erscheinen(db):
    _artikel(db, artikelnummer="ART-0001", ek_netto=Decimal("4.00"), bestand_aktuell=Decimal("5"))
    _artikel(db, artikelnummer="ART-0002", lager_aktiv=False, bezeichnung="Dienstleistung ohne Lager")
    _artikel(db, artikelnummer="ART-0003", aktiv=False, bezeichnung="Archivierter Lagerartikel")

    zeilen = _inventur_zeilen(db)

    assert len(zeilen) == 1
    assert zeilen[0].artikelnummer == "ART-0001"


def test_wert_ist_bestand_mal_ek(db):
    _artikel(db, ek_netto=Decimal("4.50"), bestand_aktuell=Decimal("3"))

    zeilen = _inventur_zeilen(db)

    assert zeilen[0].wert == "13.50"


def test_ohne_ek_preis_ist_wert_none(db):
    _artikel(db, ek_netto=None, bestand_aktuell=Decimal("3"))

    zeilen = _inventur_zeilen(db)

    assert zeilen[0].ek_netto is None
    assert zeilen[0].wert is None
