"""
Regressionstest für Issue #419 Phase 2b (Nutzer-Feedback): Das Kontokorrent zeigte bei einer
Überzahlung nur den auf die Rechnung GEKAPPTEN Zahlungsbetrag (zahlung_bar_erstellen() kappt
bewusst auf brutto_gesamt, der Überschuss landet separat als Forderung(typ="kundenguthaben"))
- der tatsächlich gezahlte Betrag war im Kontokorrent dadurch unsichtbar.

Nutzer-Vorgabe: Die Zahlungs-Zeile selbst muss immer den tatsächlich gezahlten Betrag zeigen,
unabhängig vom Rechnungsbetrag - keine eigene "Guthaben"-Zeile. Das Guthaben ergibt sich
automatisch aus der Saldo-Summe (Rechnung + tatsächliche Zahlung).

Solange die Überzahlung noch offen ist (status="offen"), wird sie der ursprünglichen
Zahlungs-Zeile zugerechnet. Einmal verrechnet (status != "offen") zählt sie stattdessen bei der
verrechnenden Buchung bzw. der reduzierten Schlussrechnungssumme - sonst würde sie doppelt
auftauchen.
"""
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.kunden import kontokorrent_kunde
from database.connection import Base
from database.models import Forderung, Journaleintrag, Kunde, Rechnung, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(firmenname="Testfirma GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    kunde = Kunde(firmenname="Testkunde GmbH")
    session.add(kunde)
    session.commit()
    session.refresh(kunde)
    yield session, kunde.id
    session.close()


def _abschlag_mit_zahlung(db, kunde_id) -> tuple[Rechnung, Journaleintrag]:
    abschlag = Rechnung(
        typ="ausgang", kunde_id=kunde_id, rechnungsnummer="AR-26-0001", dokument_typ="Abschlagsrechnung",
        datum=date(2026, 1, 5), brutto_gesamt=Decimal("2.00"), netto_gesamt=Decimal("2.00"), ust_gesamt=Decimal("0"),
        ist_entwurf=False, zahlungsstatus="bezahlt", bezahlt_betrag=Decimal("2.00"),
    )
    db.add(abschlag)
    db.commit()
    db.refresh(abschlag)
    eintrag = Journaleintrag(
        datum=date(2026, 1, 10), belegnr="Z-1", beschreibung="Zahlung AR-26-0001", zahlungsart="Bank",
        art="Einnahme", netto_betrag=Decimal("2.00"), brutto_betrag=Decimal("2.00"), rechnung_id=abschlag.id,
    )
    db.add(eintrag)
    db.commit()
    db.refresh(eintrag)
    return abschlag, eintrag


def test_zahlung_zeigt_tatsaechlich_gezahlten_betrag_bei_offener_ueberzahlung(db):
    session, kunde_id = db
    abschlag, eintrag = _abschlag_mit_zahlung(session, kunde_id)
    session.add(Forderung(
        typ="kundenguthaben", betrag=Decimal("3.00"), status="offen",
        partner_typ="kunde", partner_id=kunde_id, rechnung_id=abschlag.id, journal_id=eintrag.id,
        notiz="Überzahlung: Testkunde GmbH · 3.00 €", erstellt_am=datetime(2026, 1, 10),
    ))
    session.commit()

    bewegungen = kontokorrent_kunde(kunde_id, db=session)

    assert not any(b.typ == "guthaben" for b in bewegungen)
    zahlung_zeilen = [b for b in bewegungen if b.typ == "zahlung"]
    assert len(zahlung_zeilen) == 1
    assert zahlung_zeilen[0].betrag == -5.0
    # Rechnung (+2) - tatsächliche Zahlung (-5) = Saldo -3 (Guthaben ergibt sich aus der Summe)
    assert round(bewegungen[-1].saldo, 2) == -3.0


def test_verrechnete_ueberzahlung_zaehlt_nicht_mehr_bei_der_zahlung(db):
    session, kunde_id = db
    abschlag, eintrag = _abschlag_mit_zahlung(session, kunde_id)
    session.add(Forderung(
        typ="kundenguthaben", betrag=Decimal("3.00"), status="ausgeglichen",
        partner_typ="kunde", partner_id=kunde_id, rechnung_id=abschlag.id, journal_id=eintrag.id,
        notiz="Überzahlung: Testkunde GmbH · 3.00 €", erstellt_am=datetime(2026, 1, 10),
    ))
    session.commit()

    bewegungen = kontokorrent_kunde(kunde_id, db=session)

    zahlung_zeilen = [b for b in bewegungen if b.typ == "zahlung"]
    assert len(zahlung_zeilen) == 1
    assert zahlung_zeilen[0].betrag == -2.0
    # Die 3€ sind bereits anderswo verrechnet (eigene Buchung oder reduzierte
    # Schlussrechnungssumme) - hier bewusst nicht noch einmal gezählt.
    assert round(bewegungen[-1].saldo, 2) == 0.0
