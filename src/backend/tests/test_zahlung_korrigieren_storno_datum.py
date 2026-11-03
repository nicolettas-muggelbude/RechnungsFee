"""
Regressionstest für das Storno-Datum bei „Zahlung korrigieren“ (Folgefund zu Issue #320).

storno_eintrag(), die Journal-Korrektur und storno_rechnung() buchen die Gegenbuchung seit
#320 auf das Datum der Originalbuchung. zahlung_korrigieren() buchte sie weiter auf das
heutige Datum: Wird eine Zahlung aus dem Vorjahr (oder einem früheren UStVA-Zeitraum)
korrigiert, bleibt der alte Betrag im Ursprungszeitraum stehen und der laufende Zeitraum
wird um ihn gemindert.
"""
import calendar
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import ZahlungKorrigieren, zahlung_korrigieren
from api.ustva import _berechne_kz
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


def _bezahlte_rechnung(db) -> tuple[Rechnung, Journaleintrag]:
    rechnung = Rechnung(
        typ="ausgang", rechnungsnummer="RE-250001", datum=date(2025, 12, 1),
        netto_gesamt=Decimal("1000.00"), ust_gesamt=Decimal("190.00"),
        brutto_gesamt=Decimal("1190.00"), bezahlt=True, bezahlt_betrag=Decimal("1190.00"),
        zahlungsstatus="bezahlt", ist_entwurf=False, immutable=True,
    )
    db.add(rechnung)
    db.flush()
    zahlung = Journaleintrag(
        datum=date(2025, 12, 20), belegnr="J-2025-1", beschreibung="Zahlung RE-250001",
        zahlungsart="Bank", art="Einnahme", konto_ust_skr03="1776", konto_ust_skr04="3806",
        netto_betrag=Decimal("1000.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("190.00"),
        vorsteuer_betrag=Decimal("0.00"), brutto_betrag=Decimal("1190.00"), vorsteuerabzug=False,
        rechnung_id=rechnung.id, immutable=True,
    )
    db.add(zahlung)
    db.commit()
    return rechnung, zahlung


def test_korrektur_storno_uebernimmt_datum_der_zahlung(db):
    rechnung, zahlung = _bezahlte_rechnung(db)

    # Tatsächlich gingen nur 595,00 € ein - am selben Tag
    zahlung_korrigieren(
        rechnung.id, zahlung.id,
        ZahlungKorrigieren(neues_datum=date(2025, 12, 20), neuer_betrag=Decimal("595.00")), db,
    )

    storno = db.query(Journaleintrag).filter(Journaleintrag.beschreibung.like("STORNO %")).one()
    assert storno.datum == date(2025, 12, 20)

    # UStVA Dezember 2025: nur die korrigierte Zahlung, nicht Original + Korrektur
    kz, _ = _berechne_kz(date(2025, 12, 1), date(2025, 12, 31), db)
    assert kz["kz_81"] == Decimal("500.00")
    assert kz["kz_83"] == Decimal("95.00")


def test_korrektur_mit_neuem_datum_in_anderem_monat(db):
    rechnung, zahlung = _bezahlte_rechnung(db)

    # Geld kam erst am 05.01.2026 und nur zu 595,00 €
    zahlung_korrigieren(
        rechnung.id, zahlung.id,
        ZahlungKorrigieren(neues_datum=date(2026, 1, 5), neuer_betrag=Decimal("595.00")), db,
    )

    storno = db.query(Journaleintrag).filter(Journaleintrag.beschreibung.like("STORNO %")).one()
    neu = db.query(Journaleintrag).filter(
        Journaleintrag.id.notin_([zahlung.id, storno.id]),
    ).one()
    assert storno.datum == date(2025, 12, 20)
    assert neu.datum == date(2026, 1, 5)
    assert neu.brutto_betrag == Decimal("595.00")

    kz_dez, _ = _berechne_kz(date(2025, 12, 1), date(2025, 12, 31), db)
    assert kz_dez["kz_81"] == Decimal("0.00")
    kz_jan, _ = _berechne_kz(date(2026, 1, 1), date(2026, 1, 31), db)
    assert kz_jan["kz_81"] == Decimal("500.00")
    assert kz_jan["kz_83"] == Decimal("95.00")

    # Monat der Korrektur (heute) bleibt unberührt
    heute = date.today()
    letzter_tag = calendar.monthrange(heute.year, heute.month)[1]
    kz_heute, _ = _berechne_kz(date(heute.year, heute.month, 1), date(heute.year, heute.month, letzter_tag), db)
    assert kz_heute["kz_81"] == Decimal("0.00")
    assert kz_heute["kz_83"] == Decimal("0.00")
