"""
Regressionstest für Issue #344.

Bug: Storno einer Buchung mit steuerlichem Sonderfall (§13b, ig. Erwerb) verdoppelte
Bemessungsgrundlage und Steuer in der UStVA statt sie aufzuheben. Der Storno-Endpunkt legt
sein Vorzeichen nur in `art` ab (invertiert) und in `vorsteuer_betrag` (direkt negiert) -
`netto_betrag`/`ust_betrag` bleiben auf der Gegenbuchung beide positiv. Der Sonderfall-Zweig
in `_addiere_sonderfall_kz()`/`_berechne_kz()` fragte `art` bisher nicht ab und addierte
Original und Storno, statt das Vorzeichen aus `art` abzuleiten wie der reguläre Zweig.
Nur `vorsteuer_betrag` (KZ 67/61) hob sich korrekt auf, da es sein eigenes Vorzeichen trägt.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.journal import storno_eintrag, create_eintrag
from api.schemas import JournalEintragCreate, StornoRequest
from api.ustva import _berechne_kz
from database.connection import Base
from database.models import Journaleintrag, Kategorie


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_13b_abs1_storno_hebt_kz_46_47_67_vollstaendig_auf(db):
    """Exakter Repro-Fall aus Issue #344: 128,38 €, 19%, §13b Abs. 1, Vorsteuerabzug."""
    kat = Kategorie(
        name="EU-Dienstleistungen (§13b Abs. 1)", kontenart="Aufwand",
        konto_skr03="3123", konto_skr04="5923", vorsteuer_prozent=100, ust_satz_standard=19,
    )
    db.add(kat)
    db.commit()

    eintrag = create_eintrag(
        JournalEintragCreate(
            datum=date(2026, 1, 5), beschreibung="Finom Kontoführung",
            kategorie_id=kat.id, art="Ausgabe", brutto_betrag=Decimal("128.38"),
            ust_satz=Decimal("19"), vorsteuerabzug=True, ust_sonderfall="13b_abs1",
            zahlungsart="Bank",
        ),
        db,
    )

    kz_vor_storno, _ = _berechne_kz(date(2026, 1, 1), date(2026, 1, 31), db)
    assert kz_vor_storno["kz_46"] == Decimal("128.38")
    assert kz_vor_storno["kz_47"] == Decimal("24.39")
    assert kz_vor_storno["kz_67"] == Decimal("24.39")
    assert kz_vor_storno["zahllast"] == Decimal("0.00")

    storno_eintrag(eintrag.id, StornoRequest(grund="Testkorrektur"), db)

    kz_nach_storno, _ = _berechne_kz(date(2026, 1, 1), date(2026, 1, 31), db)
    assert kz_nach_storno["kz_46"] == Decimal("0.00")
    assert kz_nach_storno["kz_47"] == Decimal("0.00")
    assert kz_nach_storno["kz_67"] == Decimal("0.00")
    assert kz_nach_storno["zahllast"] == Decimal("0.00")


def test_13b_abs2_storno_hebt_kz_84_85_auf(db):
    kat = Kategorie(
        name="Bauleistungen / §13b Abs. 2", kontenart="Aufwand",
        konto_skr03="3120", konto_skr04="5920", vorsteuer_prozent=100, ust_satz_standard=19,
    )
    db.add(kat)
    db.commit()

    eintrag = create_eintrag(
        JournalEintragCreate(
            datum=date(2026, 2, 5), beschreibung="Bauleistung",
            kategorie_id=kat.id, art="Ausgabe", brutto_betrag=Decimal("500.00"),
            ust_satz=Decimal("19"), vorsteuerabzug=True, ust_sonderfall="13b_abs2",
            zahlungsart="Bank",
        ),
        db,
    )
    storno_eintrag(eintrag.id, StornoRequest(grund="Testkorrektur"), db)

    kz, _ = _berechne_kz(date(2026, 2, 1), date(2026, 2, 28), db)
    assert kz["kz_84"] == Decimal("0.00")
    assert kz["kz_85"] == Decimal("0.00")
    assert kz["kz_67"] == Decimal("0.00")
    assert kz["zahllast"] == Decimal("0.00")


def test_ig_erwerb_storno_hebt_kz_89_und_kz_61_auf(db):
    kat = Kategorie(
        name="Wareneinkauf EU", kontenart="Aufwand",
        konto_skr03="3425", konto_skr04="5425", vorsteuer_prozent=100, ust_satz_standard=19,
    )
    db.add(kat)
    db.commit()

    eintrag = create_eintrag(
        JournalEintragCreate(
            datum=date(2026, 3, 5), beschreibung="ig. Erwerb",
            kategorie_id=kat.id, art="Ausgabe", brutto_betrag=Decimal("300.00"),
            ust_satz=Decimal("19"), vorsteuerabzug=True, ust_sonderfall="ig_erwerb",
            zahlungsart="Bank",
        ),
        db,
    )
    storno_eintrag(eintrag.id, StornoRequest(grund="Testkorrektur"), db)

    kz, _ = _berechne_kz(date(2026, 3, 1), date(2026, 3, 31), db)
    assert kz["kz_89"] == Decimal("0.00")
    assert kz["kz_61"] == Decimal("0.00")
    assert kz["zahllast"] == Decimal("0.00")


def test_zwei_sonderfall_buchungen_nur_eine_storniert(db):
    """Regression: nur die stornierte Buchung darf verschwinden, die andere bleibt stehen."""
    kat = Kategorie(
        name="EU-Dienstleistungen (§13b Abs. 1)", kontenart="Aufwand",
        konto_skr03="3123", konto_skr04="5923", vorsteuer_prozent=100, ust_satz_standard=19,
    )
    db.add(kat)
    db.commit()

    eintrag1 = create_eintrag(
        JournalEintragCreate(
            datum=date(2026, 4, 5), beschreibung="Buchung 1",
            kategorie_id=kat.id, art="Ausgabe", brutto_betrag=Decimal("100.00"),
            ust_satz=Decimal("19"), vorsteuerabzug=True, ust_sonderfall="13b_abs1",
            zahlungsart="Bank",
        ),
        db,
    )
    create_eintrag(
        JournalEintragCreate(
            datum=date(2026, 4, 6), beschreibung="Buchung 2",
            kategorie_id=kat.id, art="Ausgabe", brutto_betrag=Decimal("50.00"),
            ust_satz=Decimal("19"), vorsteuerabzug=True, ust_sonderfall="13b_abs1",
            zahlungsart="Bank",
        ),
        db,
    )
    storno_eintrag(eintrag1.id, StornoRequest(grund="Testkorrektur"), db)

    kz, _ = _berechne_kz(date(2026, 4, 1), date(2026, 4, 30), db)
    assert kz["kz_46"] == Decimal("50.00")
    assert kz["kz_47"] == Decimal("9.50")
    assert kz["kz_67"] == Decimal("9.50")
