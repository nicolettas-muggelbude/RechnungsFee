"""
Regressionstest: ust_sonderfall wurde bei Eingangsrechnungen nie gesetzt (Nebenfund
beim Prüfen des umgekehrten Falls zu Issue #315/#316 - Eingangsrechnungen von
Auslands-Lieferanten).

Bug: journal.py leitet ust_sonderfall (ig_erwerb/13b_abs1/13b_abs2) korrekt aus dem
Konto der gewählten Kategorie ab. rechnungen.py._erstelle_eintrag() (Zahlungsbuchung
für Rechnungen) tat das nicht - dort wurde ust_sonderfall nur aus rechnung.
ist_reverse_charge abgeleitet, ein Flag das bei Eingangsrechnungen nie gesetzt wird.
Ergebnis: Eine Eingangsrechnung, bezahlt mit der Kategorie "EU-Dienstleistungen
(§13b Abs. 1)" (oder "Bauleistungen / §13b Abs. 2", "Wareneinkauf EU"), bekam nie
ihren Sonderfall markiert - weder das USt-Sonderkonto (1787/1780 statt normalem
Vorsteuerkonto) noch die UStVA-Zuordnung griffen.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import zahlung_bar_erstellen
from api.schemas_rechnungen import BarZahlungCreate
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Rechnung, Rechnungsposition, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _eingangsrechnung(db) -> Rechnung:
    rechnung = Rechnung(
        typ="eingang", rechnungsnummer="ER-1", datum=date(2026, 1, 1),
        brutto_gesamt=Decimal("119.00"), netto_gesamt=Decimal("100.00"),
        ist_entwurf=False,
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Beratung Schweizer Consultant",
        menge=Decimal("1"), netto=Decimal("100.00"), ust_satz=Decimal("19"), brutto=Decimal("119.00"),
    ))
    db.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    db.commit()
    db.refresh(rechnung)
    return rechnung


def test_13b_abs1_kategorie_setzt_ust_sonderfall_und_sonderkonto(db):
    kat = Kategorie(
        name="EU-Dienstleistungen (§13b Abs. 1)", kontenart="Aufwand",
        konto_skr03="3123", konto_skr04="5923", vorsteuer_prozent=100, ust_satz_standard=19,
    )
    db.add(kat)
    db.commit()
    rechnung = _eingangsrechnung(db)

    zahlung_bar_erstellen(
        rechnung.id,
        BarZahlungCreate(datum=date(2026, 1, 5), zahlungsart="Bank", kategorie_id=kat.id),
        db,
    )

    eintrag = db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == rechnung.id).first()
    assert eintrag is not None
    assert eintrag.ust_sonderfall == "13b_abs1"
    assert eintrag.konto_ust_skr03 == "1787"
    assert eintrag.konto_ust_skr04 == "3803"


def test_ig_erwerb_kategorie_setzt_ust_sonderfall_und_ist_ig_erwerb_flag(db):
    kat = Kategorie(
        name="Wareneinkauf EU", kontenart="Aufwand",
        konto_skr03="3425", konto_skr04="5425", vorsteuer_prozent=100, ust_satz_standard=19,
    )
    db.add(kat)
    db.commit()
    rechnung = _eingangsrechnung(db)

    zahlung_bar_erstellen(
        rechnung.id,
        BarZahlungCreate(datum=date(2026, 1, 5), zahlungsart="Bank", kategorie_id=kat.id),
        db,
    )

    eintrag = db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == rechnung.id).first()
    assert eintrag is not None
    assert eintrag.ust_sonderfall == "ig_erwerb"
    assert eintrag.ist_ig_erwerb is True
    assert eintrag.konto_ust_skr03 == "1780"
    assert eintrag.konto_ust_skr04 == "3802"


def test_normale_kategorie_bleibt_ohne_sonderfall(db):
    kat = Kategorie(
        name="Bürobedarf", kontenart="Aufwand",
        konto_skr03="4930", konto_skr04="6815", vorsteuer_prozent=100, ust_satz_standard=19,
    )
    db.add(kat)
    db.commit()
    rechnung = _eingangsrechnung(db)

    zahlung_bar_erstellen(
        rechnung.id,
        BarZahlungCreate(datum=date(2026, 1, 5), zahlungsart="Bank", kategorie_id=kat.id),
        db,
    )

    eintrag = db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == rechnung.id).first()
    assert eintrag is not None
    assert eintrag.ust_sonderfall is None
    assert eintrag.konto_ust_skr03 == "1575"
