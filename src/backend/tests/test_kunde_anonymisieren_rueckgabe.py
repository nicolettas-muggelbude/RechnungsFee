"""
Nebenfund Issue #495: Seit den Lieferadressen (#25) stand der Rückgabe-Block der
Kunden-Anonymisierung (DSGVO Art. 17) versehentlich in delete_lieferadresse(). Die
Anonymisierung lieferte null – im Kundenstamm erschien weder die Bestätigung noch der Hinweis
auf nicht änderbare (GoBD) Buchungen.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.kunden import anonymisiere_kunde
from database.connection import Base
from database.models import Kunde


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_anonymisierung_liefert_ergebnis(db):
    k = Kunde(firmenname="Weg AG")
    db.add(k)
    db.commit()
    ergebnis = anonymisiere_kunde(k.id, db)
    assert ergebnis == {
        "anonymisierte_buchungen": 0,
        "anonymisierte_rechnungen": 0,
        "unveraenderlich_verblieben": 0,
        "hinweis": "",
    }
    assert db.query(Kunde).count() == 0
