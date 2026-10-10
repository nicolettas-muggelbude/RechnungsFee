"""
Regressionstest für Issue #426.

Eine Eingangsrechnung wird oft nicht chronologisch nach Rechnungsdatum erfasst, sondern wie
der Papierbeleg gerade zur Hand ist. naechste_nummer() (api/nummernkreise.py) erkannte einen
Jahreswechsel bisher über "letztes_jahr != bezug.year" - das greift auch RÜCKWÄRTS: wird nach
einer 2026er-Eingangsrechnung eine ältere, noch nicht erfasste 2025er-Rechnung nachgetragen,
wurde das fälschlich als Rollover in ein "neues" Jahr gewertet und naechste_nr auf 1
zurückgesetzt. Die nächste echte 2026er-Rechnung erhielt dadurch exakt dieselbe Nummer wie
eine bereits vergebene (konkret aus dem Issue: ER-260009 an vier verschiedenen Lieferanten).

Reale GitHub-Rückmeldung (UweKoslowski): vier unterschiedliche Eingangsrechnungen
(SUNO, Zakelijk Rijden BV, Amazon, Drillisch Online GmbH) zeigten alle "ER-260009".
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.nummernkreise import naechste_nummer
from api.rechnungen import create_rechnung
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate
from database.connection import Base
from database.models import Nummernkreis, Rechnung, Unternehmen


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


def test_aeltere_nacherfasste_rechnung_setzt_zaehler_nicht_zurueck(db):
    """Kernszenario: 2026-Rechnung, dann eine nachgetragene 2025-Rechnung, dann weitere
    2026-Rechnungen - der Zähler darf NICHT auf 1 zurückfallen."""
    db.add(Nummernkreis(bezeichnung="Eingangsrechnungen", typ="rechnung_eingang", format="ER-YY####", naechste_nr=1, reset_jaehrlich=True))
    db.commit()

    nr1 = naechste_nummer("rechnung_eingang", db, date(2026, 4, 30))
    db.commit()
    nr2 = naechste_nummer("rechnung_eingang", db, date(2025, 12, 15))  # nachgetragen
    db.commit()
    nr3 = naechste_nummer("rechnung_eingang", db, date(2026, 8, 8))
    db.commit()

    assert nr1 == "ER-260001"
    assert nr3 != nr1  # der eigentliche Bug: nr3 wäre ohne Fix wieder "ER-260001" gewesen
    assert len({nr1, nr2, nr3}) == 3  # alle drei eindeutig


def test_echter_jahreswechsel_setzt_weiterhin_korrekt_zurueck(db):
    """Regressionsschutz: ein tatsächlicher Rollover in ein neues (höheres) Jahr muss
    weiterhin bei 1 starten - nur die rückwärtige Erkennung war der Bug."""
    db.add(Nummernkreis(bezeichnung="Eingangsrechnungen", typ="rechnung_eingang", format="ER-YY####", naechste_nr=5, reset_jaehrlich=True, letztes_jahr=2026))
    db.commit()

    nr = naechste_nummer("rechnung_eingang", db, date(2027, 1, 10))

    assert nr == "ER-270001"


def test_kollisionsschutz_greift_auch_wenn_zaehler_bereits_korrupt_ist(db):
    """Verteidigung in der Tiefe: existiert die vom Zähler vorgeschlagene Nummer bereits
    (z.B. aus Altdaten vor diesem Fix), wird übersprungen statt eine Dublette anzulegen."""
    db.add(Nummernkreis(bezeichnung="Eingangsrechnungen", typ="rechnung_eingang", format="ER-YY####", naechste_nr=1, reset_jaehrlich=True, letztes_jahr=2026))
    db.add(Rechnung(typ="eingang", rechnungsnummer="ER-260001", datum=date(2026, 1, 1), partner_freitext="Altbeleg"))
    db.commit()

    nr = naechste_nummer("rechnung_eingang", db, date(2026, 2, 1))

    assert nr == "ER-260002"


def _position() -> RechnungspositionCreate:
    return RechnungspositionCreate(beschreibung="Büromaterial", menge=Decimal("1"), netto=Decimal("100.00"), ust_satz=Decimal("19"))


def test_end_to_end_ueber_create_rechnung_keine_dublette(db):
    """Exaktes Szenario aus dem Issue end-to-end über den echten Erstellungs-Endpunkt."""
    db.add(Nummernkreis(bezeichnung="Eingangsrechnungen", typ="rechnung_eingang", format="ER-YY####", naechste_nr=1, reset_jaehrlich=True))
    db.commit()

    reihenfolge = [date(2026, 4, 30), date(2025, 12, 15), date(2026, 8, 8), date(2026, 8, 17), date(2026, 8, 25)]
    nummern = []
    for d in reihenfolge:
        data = RechnungCreate(typ="eingang", datum=d, ist_entwurf=False, partner_freitext="Testlieferant", positionen=[_position()])
        ergebnis = create_rechnung(data, db)
        nummern.append(ergebnis.rechnungsnummer)

    assert len(nummern) == len(set(nummern)), f"Doppelte Rechnungsnummern vergeben: {nummern}"
