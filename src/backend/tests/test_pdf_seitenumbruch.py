"""
Issue #462: Positionen mit mehrzeiliger Beschreibung am Seitenende.

Die Beträge einer Position wurden auf die alte Seite gezeichnet, erst die Beschreibung löste den
Seitenumbruch aus - je nach Lage stand eine Position über bis zu drei Seiten verteilt (Beträge,
Nummer, Beschreibung), in Vorlage 1 zusätzlich mit einem verrutschten Tabellenrahmen und
zerrissenem Zahlungsblock. Jetzt bleibt jede Position (und der Zahlungsblock) zusammen, der
Tabellenkopf wird auf jeder Folgeseite wiederholt.
"""
import re
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import create_rechnung, rechnung_als_pdf
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate
from database.connection import Base
from database.models import Kunde, Unternehmen

BETRAG = re.compile(r"(?<![0-9.])100,00")


def _seiten(vorlage: int, zeilen: int, anzahl: int) -> list[str]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort",
                       ist_kleinunternehmer=False))
    db.add(Kunde(firmenname="Kunde AG", strasse="Weg", hausnummer="2", plz="54321", ort="Stadt"))
    db.commit()
    text = "\n".join(f"Produktbeschreibung Zeile {i} mit etwas mehr Text damit es realistisch ist"
                     for i in range(1, zeilen + 1))
    r = create_rechnung(RechnungCreate(
        typ="ausgang", datum=date(2026, 10, 20), kunde_id=db.query(Kunde).one().id,
        positionen=[RechnungspositionCreate(beschreibung=text, netto=Decimal("100"), ust_satz=Decimal("19"))
                    for _ in range(anzahl)],
    ), db)
    pdf = rechnung_als_pdf(r.id, vorlage=vorlage, nur_ansehen=True, db=db).body
    return [p.extract_text() for p in PdfReader(BytesIO(pdf)).pages]


@pytest.mark.parametrize("vorlage", [0, 1])
@pytest.mark.parametrize("zeilen,anzahl", [(4, 6), (7, 8), (5, 3), (2, 11)])
def test_jede_position_vollstaendig_auf_einer_seite(vorlage, zeilen, anzahl):
    seiten = _seiten(vorlage, zeilen, anzahl)
    letzte_zeile = f"Zeile {zeilen} "
    # je Position genau einmal Einzelpreis + Gesamt - nichts doppelt, nichts verloren
    assert sum(len(BETRAG.findall(s)) for s in seiten) == 2 * anzahl
    for s in seiten:
        # Beträge und vollständige Beschreibung stehen auf derselben Seite
        assert len(BETRAG.findall(s)) == 2 * s.count(letzte_zeile)
        # Zahlungsblock (Vorlage 1) nicht zerrissen
        assert ("Empfänger" in s) == ("Verwendungszweck" in s)
    # Tabellenkopf auf jeder Seite mit Positionen
    kopf = "Einzelpreis"
    assert all(kopf in s for s in seiten if BETRAG.search(s))
    # Summe stimmt
    assert any(f"Gesamtbetrag {anzahl * 119},00 €".replace("1309,00", "1.309,00") in s for s in seiten)
