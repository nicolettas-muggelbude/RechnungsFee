"""
Regressionstest für Issue #380: JournalEintragResponse.rechnung_datum.

Journaleinträge mit Rechnungsbezug liefern jetzt zusätzlich zum Buchungsdatum
(datum, spiegelt bei Zahlungsbuchungen das Zahlungsdatum) das Rechnungsdatum der
verknüpften Rechnung - Grundlage für die Belegdatum-Spalte im Journal. Freie
Buchungen ohne Rechnungsbezug haben kein Belegdatum (None).
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.schemas import JournalEintragResponse
from database.connection import Base
from database.models import Journaleintrag, Rechnung


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_rechnung_datum_wird_aus_verknuepfter_rechnung_uebernommen():
    db = _db()
    rechnung = Rechnung(
        typ="eingang", datum=date(2026, 3, 5), rechnungsnummer="ER-1",
        brutto_gesamt=Decimal("119.00"), netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("19.00"),
        ist_entwurf=False, zahlungsstatus="bezahlt", bezahlt=True, bezahlt_betrag=Decimal("119.00"),
    )
    db.add(rechnung)
    db.flush()

    e = Journaleintrag(
        datum=date(2026, 8, 12), belegnr="J-1", beschreibung="Zahlung ER-1",
        zahlungsart="Bank", art="Ausgabe",
        netto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        brutto_betrag=Decimal("119.00"), vorsteuerabzug=True, immutable=True,
        rechnung_id=rechnung.id,
    )
    db.add(e)
    db.commit()
    db.refresh(e)

    resp = JournalEintragResponse.from_orm_with_kunde(e)

    assert resp.rechnung_datum == date(2026, 3, 5)
    assert resp.datum == date(2026, 8, 12)


def test_freie_buchung_ohne_rechnung_hat_kein_belegdatum():
    db = _db()
    e = Journaleintrag(
        datum=date(2026, 8, 12), belegnr="J-2", beschreibung="Bürobedarf",
        zahlungsart="Bar", art="Ausgabe",
        netto_betrag=Decimal("50.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("9.50"),
        brutto_betrag=Decimal("59.50"), vorsteuerabzug=True, immutable=True,
    )
    db.add(e)
    db.commit()
    db.refresh(e)

    resp = JournalEintragResponse.from_orm_with_kunde(e)

    assert resp.rechnung_datum is None
