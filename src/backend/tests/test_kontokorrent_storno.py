"""
Regressionstest: Stornierte, bereits bezahlte Ausgangsrechnung/Abschlagsrechnung wurde im
Kontokorrent nicht wieder gutgeschrieben (Nutzer-Feedback bei Issue #419 Phase 1).

Ursache: "Stornorechnung" als dokument_typ existiert in der Praxis nicht - storniert ist ein
Flag auf dem Original-Dokument (siehe Migration 89/90) - der dafür vorgesehene Zweig in
kontokorrent_kunde()/_kontokorrent_bewegungen() griff deshalb nie. Die Forderungs-Zeile blieb
nach Storno unverändert positiv stehen, die bereits gebuchte Zahlung reduzierte den Saldo
weiterhin - zusammen ergab das fälschlich einen ausgeglichenen statt einen Guthaben-Saldo.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.kunden import kontokorrent_kunde
from database.connection import Base
from database.models import Journaleintrag, Kunde, Rechnung, Unternehmen


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


def _kunde(db) -> Kunde:
    kunde = Kunde(firmenname="Testkunde GmbH")
    db.add(kunde)
    db.commit()
    db.refresh(kunde)
    return kunde


@pytest.mark.parametrize("dokument_typ", ["Rechnung", "Abschlagsrechnung"])
def test_stornierte_bezahlte_rechnung_zeigt_guthaben(db, dokument_typ):
    kunde = _kunde(db)
    r = Rechnung(
        typ="ausgang", kunde_id=kunde.id, rechnungsnummer="AR-26-0001" if dokument_typ == "Abschlagsrechnung" else "RE-26-0001",
        datum=date(2026, 1, 5), dokument_typ=dokument_typ,
        brutto_gesamt=Decimal("1190.00"), netto_gesamt=Decimal("1000.00"), ust_gesamt=Decimal("190.00"),
        ist_entwurf=False, zahlungsstatus="bezahlt", bezahlt_betrag=Decimal("1190.00"),
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    db.add(Journaleintrag(
        datum=date(2026, 1, 10), belegnr="Z-1", beschreibung="Zahlung", zahlungsart="Bank",
        art="Einnahme", netto_betrag=Decimal("1000.00"), brutto_betrag=Decimal("1190.00"),
        rechnung_id=r.id,
    ))
    db.commit()

    # Vor dem Storno: ausgeglichen (Forderung 1190 - Zahlung 1190 = 0)
    bewegungen = kontokorrent_kunde(kunde.id, db)
    assert round(bewegungen[-1].saldo, 2) == 0.0

    r.storniert = True
    r.storno_grund = "Projekt abgebrochen"
    r.storno_datum = date(2026, 1, 20)
    db.commit()

    bewegungen = kontokorrent_kunde(kunde.id, db)
    storno_zeilen = [b for b in bewegungen if b.typ == "storno"]
    assert len(storno_zeilen) == 1
    assert storno_zeilen[0].betrag == -1190.0
    # Nach dem Storno: Guthaben in Höhe der bereits gezahlten, jetzt nicht mehr
    # geschuldeten Summe (negativer Saldo = Guthaben).
    assert round(bewegungen[-1].saldo, 2) == -1190.0
