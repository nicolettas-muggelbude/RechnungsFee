"""
Regressionstest für das Storno-Datum bei Rechnungs-Storno (Issue #320).

Gleicher Bug wie bei der Journal-Storno (siehe test_journal_storno.py), aber
im Ausgangsrechnungs-Pfad: storno_rechnung() buchte die Gegenbuchung bisher
immer auf das heutige Datum statt auf das Datum der jeweiligen Original-
Zahlung - bei der EÜR (Zuflussprinzip) verfälscht das sowohl das
Ursprungsjahr (bleibt unkorrigiert) als auch das laufende Jahr.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import storno_rechnung
from api.schemas import StornoRequest
from api.schemas_rechnungen import RechnungResponse
from database.connection import Base
from database.models import Journaleintrag, Rechnung


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_storno_rechnung_uebernimmt_datum_der_zahlung(db):
    rechnung = Rechnung(
        typ="ausgang", rechnungsnummer="RE-2021-1", datum=date(2021, 5, 1),
        brutto_gesamt=Decimal("1190.00"), bezahlt=True, bezahlt_betrag=Decimal("1190.00"),
        zahlungsstatus="bezahlt", ist_entwurf=False, immutable=True,
    )
    db.add(rechnung)
    db.flush()

    zahlung = Journaleintrag(
        datum=date(2021, 5, 3), belegnr="J-2021-1", beschreibung="Zahlung RE-2021-1",
        zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("1000.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("190.00"),
        brutto_betrag=Decimal("1190.00"), vorsteuerabzug=False,
        rechnung_id=rechnung.id, immutable=True,
    )
    db.add(zahlung)
    db.commit()

    response = storno_rechnung(rechnung.id, StornoRequest(grund="falsche Kategorie"), db)

    gegenbuchung = db.query(Journaleintrag).filter(
        Journaleintrag.beschreibung.like("STORNO %")
    ).first()
    assert gegenbuchung is not None
    assert gegenbuchung.datum == date(2021, 5, 3)
    # rechnung.storno_datum (wann tatsaechlich storniert wurde) bleibt bewusst "heute"
    assert response.storno_datum == date.today()


def test_zahlungen_kette_zeigt_storno_status(db):
    """Issue #321-Fortsetzung: ZahlungKompakt (rechnung.zahlungen_kette) muss denselben
    Storno-Status liefern wie JournalEintragResponse, statt dass das Frontend die
    Beschreibung auf 'STORNO ' prueft."""
    rechnung = Rechnung(
        typ="ausgang", rechnungsnummer="RE-2026-1", datum=date(2026, 1, 1),
        brutto_gesamt=Decimal("119.00"), bezahlt=True, bezahlt_betrag=Decimal("119.00"),
        zahlungsstatus="bezahlt", ist_entwurf=False, immutable=True,
    )
    db.add(rechnung)
    db.flush()

    zahlung = Journaleintrag(
        datum=date(2026, 1, 2), belegnr="J-2026-1", beschreibung="Zahlung RE-2026-1",
        zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        brutto_betrag=Decimal("119.00"), vorsteuerabzug=False,
        rechnung_id=rechnung.id, immutable=True,
    )
    db.add(zahlung)
    db.commit()

    storno_rechnung(rechnung.id, StornoRequest(grund="Testkorrektur"), db)
    db.refresh(rechnung)

    response = RechnungResponse.from_orm_extended(rechnung)
    kette = {z.belegnr: z for z in response.zahlungen_kette}

    assert kette["J-2026-1"].storniert is True
    assert kette["J-2026-1"].ist_storno is False
    gegenbuchung = next(z for z in response.zahlungen_kette if z.belegnr != "J-2026-1")
    assert gegenbuchung.ist_storno is True
    assert gegenbuchung.storniert is False
