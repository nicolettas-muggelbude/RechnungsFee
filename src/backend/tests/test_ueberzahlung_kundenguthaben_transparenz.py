"""
Regressionstest (Issue #419-Fortsetzung, Nutzer-Feedback): Eine Überzahlung bei einer
Ausgangsrechnung wird buchhalterisch korrekt behandelt - die Journalbuchung wird auf den
Restbetrag gekappt, der Überschuss separat als Kundenguthaben-Forderung erfasst. Aber weder
die API-Antwort (BarZahlungResult) noch der Zahlungsdialog haben das jemals gezeigt: Nutzerinnen
verglichen den echten Geldeingang (z.B. 100,50 €) mit dem Journal (100,00 €), fanden die
0,50 € nirgends wieder und hielten die Zahlung für falsch gebucht (bis hin zum vorschnellen
Storno der Rechnung).

Fix: BarZahlungResult weist die Aufteilung aus, die das Backend intern bereits trifft
(mahngebuehr_verrechnet + kundenguthaben_betrag), und der Zahlungsdialog zeigt sie live,
bevor gebucht wird.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import create_rechnung, zahlung_bar_erstellen
from api.schemas_rechnungen import BarZahlungCreate, RechnungCreate, RechnungspositionCreate
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


def _rechnung_100(db, kunde_id):
    """Steuerfreie 100,00-€-Rechnung - exemplarischer Fall aus dem Nutzer-Feedback."""
    resp = create_rechnung(RechnungCreate(
        typ="ausgang", dokument_typ="Rechnung", datum=date(2026, 8, 10), ist_entwurf=False,
        kunde_id=kunde_id,
        positionen=[RechnungspositionCreate(
            beschreibung="Testleistung", menge=Decimal("1"), netto=Decimal("100.00"), ust_satz=Decimal("0"),
        )],
    ), db)
    return db.query(Rechnung).filter(Rechnung.id == resp.id).first()


def test_ueberzahlung_weist_kundenguthaben_in_der_antwort_aus(db):
    session, kunde_id = db
    rechnung = _rechnung_100(session, kunde_id)

    result = zahlung_bar_erstellen(rechnung.id, BarZahlungCreate(
        datum=date(2026, 8, 11), zahlungsart="Bank", betrag=Decimal("100.50"),
    ), session)

    # Die Aufteilung, die bisher nur intern stattfand, ist jetzt Teil der Antwort:
    assert result.kundenguthaben_betrag == Decimal("0.50")
    assert result.mahngebuehr_verrechnet == Decimal("0")

    # Journal bleibt auf den Rechnungsbetrag gekappt; die Spitze ist die separat erfasste Forderung.
    eintrag = session.query(Journaleintrag).filter(Journaleintrag.rechnung_id == rechnung.id).one()
    assert eintrag.brutto_betrag == Decimal("100.00")
    forderung = session.query(Forderung).filter(Forderung.typ == "kundenguthaben").one()
    assert forderung.betrag == Decimal("0.50")
    assert forderung.journal_id == eintrag.id
    assert "Testkunde GmbH" in forderung.notiz
    assert result.rechnung.bezahlt_betrag == Decimal("100.00")


def test_normale_zahlung_weist_kein_guthaben_aus(db):
    session, kunde_id = db
    rechnung = _rechnung_100(session, kunde_id)

    result = zahlung_bar_erstellen(rechnung.id, BarZahlungCreate(
        datum=date(2026, 8, 11), zahlungsart="Bank", betrag=Decimal("100.00"),
    ), session)

    assert result.kundenguthaben_betrag == Decimal("0")
    assert result.mahngebuehr_verrechnet == Decimal("0")
    assert session.query(Forderung).filter(Forderung.typ == "kundenguthaben").count() == 0
