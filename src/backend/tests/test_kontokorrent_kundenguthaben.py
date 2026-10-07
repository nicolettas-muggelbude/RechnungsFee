"""
Regressionstest für Issue #419 Phase 2b (Nutzer-Feedback): Das Kontokorrent zeigte bei einer
Überzahlung nur den auf die Rechnung GEKAPPTEN Zahlungsbetrag (zahlung_bar_erstellen() kappt
bewusst auf brutto_gesamt, der Überschuss landet separat als Forderung(typ="kundenguthaben"))
- der tatsächlich gezahlte Betrag war im Kontokorrent dadurch unsichtbar.

Jetzt: eine offene Kundenguthaben-Forderung erscheint als eigene "guthaben"-Zeile zum
Zeitpunkt ihrer Entstehung. Einmal verrechnet (status != "offen") verschwindet sie wieder,
ohne den Saldo doppelt zu belasten - der Betrag ist dann bereits über die verrechnende
Buchung bzw. die reduzierte Schlussrechnungssumme abgedeckt.
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


def test_offene_ueberzahlung_erscheint_als_guthaben_zeile(db):
    session, kunde_id = db
    abschlag = Rechnung(
        typ="ausgang", kunde_id=kunde_id, rechnungsnummer="AR-26-0001", dokument_typ="Abschlagsrechnung",
        datum=date(2026, 1, 5), brutto_gesamt=Decimal("2.00"), netto_gesamt=Decimal("2.00"), ust_gesamt=Decimal("0"),
        ist_entwurf=False, zahlungsstatus="bezahlt", bezahlt_betrag=Decimal("2.00"),
    )
    session.add(abschlag)
    session.commit()
    session.refresh(abschlag)
    session.add(Journaleintrag(
        datum=date(2026, 1, 10), belegnr="Z-1", beschreibung="Zahlung AR-26-0001", zahlungsart="Bank",
        art="Einnahme", netto_betrag=Decimal("2.00"), brutto_betrag=Decimal("2.00"), rechnung_id=abschlag.id,
    ))
    guthaben = Forderung(
        typ="kundenguthaben", betrag=Decimal("3.00"), status="offen",
        partner_typ="kunde", partner_id=kunde_id, rechnung_id=abschlag.id,
        notiz="Überzahlung: Testkunde GmbH · 3.00 €", erstellt_am=datetime(2026, 1, 10),
    )
    session.add(guthaben)
    session.commit()

    bewegungen = kontokorrent_kunde(kunde_id, db=session)

    guthaben_zeilen = [b for b in bewegungen if b.typ == "guthaben"]
    assert len(guthaben_zeilen) == 1
    assert guthaben_zeilen[0].betrag == -3.0
    # Rechnung (+2) - Zahlung (-2) - offenes Guthaben (-3) = tatsächlicher Netto-Saldo -3
    assert round(bewegungen[-1].saldo, 2) == -3.0


def test_verrechnetes_guthaben_verschwindet_ohne_doppelzaehlung(db):
    session, kunde_id = db
    abschlag = Rechnung(
        typ="ausgang", kunde_id=kunde_id, rechnungsnummer="AR-26-0001", dokument_typ="Abschlagsrechnung",
        datum=date(2026, 1, 5), brutto_gesamt=Decimal("2.00"), netto_gesamt=Decimal("2.00"), ust_gesamt=Decimal("0"),
        ist_entwurf=False, zahlungsstatus="bezahlt", bezahlt_betrag=Decimal("2.00"),
    )
    session.add(abschlag)
    session.commit()
    session.refresh(abschlag)
    session.add(Journaleintrag(
        datum=date(2026, 1, 10), belegnr="Z-1", beschreibung="Zahlung AR-26-0001", zahlungsart="Bank",
        art="Einnahme", netto_betrag=Decimal("2.00"), brutto_betrag=Decimal("2.00"), rechnung_id=abschlag.id,
    ))
    guthaben = Forderung(
        typ="kundenguthaben", betrag=Decimal("3.00"), status="ausgeglichen",
        partner_typ="kunde", partner_id=kunde_id, rechnung_id=abschlag.id,
        notiz="Überzahlung: Testkunde GmbH · 3.00 €", erstellt_am=datetime(2026, 1, 10),
    )
    session.add(guthaben)
    session.commit()

    bewegungen = kontokorrent_kunde(kunde_id, db=session)

    assert not any(b.typ == "guthaben" for b in bewegungen)
    # Rechnung (+2) - Zahlung (-2) = 0 - die 3€ sind bereits anderswo verrechnet (eigene Buchung
    # oder reduzierte Schlussrechnungssumme), tauchen hier bewusst nicht mehr auf.
    assert round(bewegungen[-1].saldo, 2) == 0.0
