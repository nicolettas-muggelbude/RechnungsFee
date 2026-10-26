"""Issue #471: Artikelsuche findet auch den eigenen Artikelcode und die Lieferanten-Artikelnummer."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.artikel import suche_artikel
from database.connection import Base
from database.models import Artikel


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Artikel(artikelnummer="ART-0001", typ="dienstleistung", bezeichnung="Ölwechsel",
                        einheit="Stück", artikelcode="AW5010KS", vk_brutto=50, vk_netto=42, steuersatz=19, aktiv=True))
    session.add(Artikel(artikelnummer="ART-0002", typ="artikel", bezeichnung="Ölfilter",
                        einheit="Stück", lieferanten_artikelnr="MANN-W712", vk_brutto=12, vk_netto=10, steuersatz=19, aktiv=True))
    session.commit()
    yield session
    session.close()


@pytest.mark.parametrize("q,erwartet", [
    ("AW5010", "Ölwechsel"),      # eigener Artikelcode
    ("aw5010ks", "Ölwechsel"),    # unabhängig von Groß-/Kleinschreibung
    ("W712", "Ölfilter"),         # Lieferanten-Artikelnummer
    ("ART-0002", "Ölfilter"),     # interne Nummer wie bisher
])
def test_suche(db, q, erwartet):
    assert [t.bezeichnung for t in suche_artikel(q, db=db)] == [erwartet]
