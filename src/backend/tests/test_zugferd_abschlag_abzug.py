"""
Regressionstest für Issue #419 Phase 2: Eine Schlussrechnung mit einer negierten
Abzugsposition (Abschlagsrechnung-Verrechnung) ist der erste Fall im gesamten Code, bei dem
dokument_typ="Rechnung" automatisch per ZUGFeRD exportiert wird UND gemischte Vorzeichen
innerhalb der Positionen hat (Gutschriften haben zwar seit Jahren negative Positionen, lösen
aber selbst nie den automatischen ZUGFeRD-Trigger aus - ungetestetes Terrain laut Plan-Agent).

Prüft: Kopfsummen (Netto/USt/Brutto) ergeben sich korrekt als Summe aus positiver und
negativer Positionszeile, die negierte Zeile erscheint mit negativem Vorzeichen (nicht
etwa abs()-bereinigt oder weggelassen), kein Crash bei negativer BilledQuantity.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import Rechnung, Rechnungsposition
from utils.zugferd import generate_zugferd_xml

UNTERNEHMEN = {
    "firmenname": "Testfirma GmbH",
    "strasse": "Teststraße", "hausnummer": "1", "plz": "12345", "ort": "Teststadt",
    "land": "DE", "steuernummer": "12/345/67890", "ust_idnr": "",
    "ist_kleinunternehmer": False,
}


def _schlussrechnung_mit_abzug() -> Rechnung:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    r = Rechnung(
        typ="ausgang", dokument_typ="Rechnung", rechnungsnummer="RE-1", datum=date(2026, 2, 1),
        netto_gesamt=Decimal("1000.00"), ust_gesamt=Decimal("190.00"), brutto_gesamt=Decimal("1190.00"),
        ist_entwurf=False,
    )
    db.add(r)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=r.id, position_nr=1, beschreibung="Gesamtleistung", menge=Decimal("1"),
        einheit="Stück", netto=Decimal("2000.00"), ust_satz=Decimal("19"),
        ust_betrag=Decimal("380.00"), brutto=Decimal("2380.00"),
    ))
    db.add(Rechnungsposition(
        rechnung_id=r.id, position_nr=2, beschreibung="Abzgl. Abschlagsrechnung AR-26-0001",
        menge=Decimal("-1"), einheit="Stück", netto=Decimal("1000.00"), ust_satz=Decimal("19"),
        ust_betrag=Decimal("-190.00"), brutto=Decimal("-1190.00"), abschlag_rechnung_id=None,
    ))
    db.commit()
    db.refresh(r)
    return r


def test_kopfsummen_mit_negierter_abzugsposition():
    rechnung = _schlussrechnung_mit_abzug()

    xml = generate_zugferd_xml(rechnung, UNTERNEHMEN).decode("utf-8")

    assert "<ram:LineTotalAmount>1000.00</ram:LineTotalAmount>" in xml
    assert "<ram:TaxBasisTotalAmount>1000.00</ram:TaxBasisTotalAmount>" in xml
    assert "<ram:GrandTotalAmount>1190.00</ram:GrandTotalAmount>" in xml
    assert "<ram:DuePayableAmount>1190.00</ram:DuePayableAmount>" in xml


def test_abzugsposition_erscheint_mit_negativem_vorzeichen_nicht_als_absolutwert():
    rechnung = _schlussrechnung_mit_abzug()

    xml = generate_zugferd_xml(rechnung, UNTERNEHMEN).decode("utf-8")

    # Die negierte Positionssumme (BT-131) der Abzugszeile muss negativ im XML stehen -
    # würde sie faelschlich als abs() auftauchen, ergäbe die Summe aller Line-Totals
    # 3000.00 statt der korrekten 1000.00 (bereits oben geprüft), hier zusätzlich direkt
    # auf das Vorzeichen der Zeile selbst geprüft.
    assert "<ram:LineTotalAmount>-1000.00</ram:LineTotalAmount>" in xml


def test_kein_crash_bei_negativer_billed_quantity():
    rechnung = _schlussrechnung_mit_abzug()

    # Darf keine Exception werfen (z.B. durch eine abs()/Validierung, die eine negative
    # Menge für unmöglich hält).
    xml_bytes = generate_zugferd_xml(rechnung, UNTERNEHMEN)
    assert len(xml_bytes) > 0
