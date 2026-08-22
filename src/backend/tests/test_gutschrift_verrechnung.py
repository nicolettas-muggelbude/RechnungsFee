"""
Tests für Issue #366 (Gutschrift mit Kunden-/Lieferantenrechnung verrechnen). Deckt beide
Richtungen ab: Kundengutschrift <-> Ausgangsrechnung, Lieferantengutschrift <-> Eingangsrechnung
(analog zur bestehenden Spiegelung test_gutschrift_ausgang_bestandsschutz.py /
test_gutschrift_eingang.py).
"""
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import (
    create_gutschrift, finalisiere_rechnung, gutschrift_verrechnen, GutschriftVerrechnenRequest,
)
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Kunde, Lieferant, Rechnung, Rechnungsposition, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    session.add(Kategorie(
        name="Betriebseinnahmen", kontenart="Erlös", konto_skr03="8400", konto_skr04="4400",
        vorsteuer_prozent=0, ust_satz_standard=19,
    ))
    session.add(Kategorie(
        name="Bürobedarf", kontenart="Aufwand", konto_skr03="4930", konto_skr04="6815",
        vorsteuer_prozent=100, ust_satz_standard=19,
    ))
    session.add(Kunde(firmenname="Musterkunde GmbH"))
    session.add(Kunde(firmenname="Anderer Kunde"))
    session.add(Lieferant(firmenname="Musterlieferant GmbH"))
    session.commit()
    yield session
    session.close()


def _ausgangsrechnung(db, kunde_id, nr, betrag_netto="200.00", satz="19") -> Rechnung:
    netto = Decimal(betrag_netto)
    ust = (netto * Decimal(satz) / 100).quantize(Decimal("0.01"))
    rechnung = Rechnung(
        typ="ausgang", rechnungsnummer=nr, datum=date(2026, 6, 1), kunde_id=kunde_id,
        brutto_gesamt=netto + ust, netto_gesamt=netto, ust_gesamt=ust,
        ist_entwurf=False, zahlungsstatus="offen", bezahlt_betrag=Decimal("0.00"),
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Beratung", menge=Decimal("1"),
        einheit="Stk.", netto=netto, ust_satz=Decimal(satz), ust_betrag=ust, brutto=netto + ust,
        kategorie_id=None,
    ))
    db.commit()
    db.refresh(rechnung)
    return rechnung


def _eingangsrechnung(db, lieferant_id, nr, betrag_netto="200.00", satz="19") -> Rechnung:
    kat = db.query(Kategorie).filter(Kategorie.name == "Bürobedarf").first()
    netto = Decimal(betrag_netto)
    ust = (netto * Decimal(satz) / 100).quantize(Decimal("0.01"))
    rechnung = Rechnung(
        typ="eingang", rechnungsnummer=nr, datum=date(2026, 6, 1), lieferant_id=lieferant_id,
        brutto_gesamt=netto + ust, netto_gesamt=netto, ust_gesamt=ust,
        ist_entwurf=False, zahlungsstatus="offen", bezahlt_betrag=Decimal("0.00"),
        kategorie_id=kat.id,
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Büromaterial", menge=Decimal("1"),
        einheit="Stk.", netto=netto, ust_satz=Decimal(satz), ust_betrag=ust, brutto=netto + ust,
        kategorie_id=kat.id,
    ))
    db.commit()
    db.refresh(rechnung)
    return rechnung


def _finalisierte_gutschrift(db, original: Rechnung) -> Rechnung:
    resp = create_gutschrift(original.id, db)
    finalisiere_rechnung(resp.id, db)
    return db.query(Rechnung).filter(Rechnung.id == resp.id).first()


def test_ausgang_gutschrift_voll_verrechnet_gegen_gleich_hohe_rechnung(db):
    kunde = db.query(Kunde).filter(Kunde.firmenname == "Musterkunde GmbH").first()
    original = _ausgangsrechnung(db, kunde.id, "RE-2026-1")
    gutschrift = _finalisierte_gutschrift(db, original)
    ziel = _ausgangsrechnung(db, kunde.id, "RE-2026-2")

    ergebnis = gutschrift_verrechnen(gutschrift.id, GutschriftVerrechnenRequest(rechnung_id=ziel.id), db)

    assert ergebnis.betrag == Decimal("238.00")
    assert ergebnis.gutschrift.zahlungsstatus == "bezahlt"
    assert ergebnis.rechnung.zahlungsstatus == "bezahlt"

    gs_eintrag = db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == gutschrift.id).one()
    assert gs_eintrag.brutto_betrag == Decimal("-238.00")
    assert gs_eintrag.art == "Einnahme"
    assert gs_eintrag.zahlungsart == "Verrechnung"
    assert gs_eintrag.kategorie_id is not None
    kat = db.query(Kategorie).filter(Kategorie.id == gs_eintrag.kategorie_id).first()
    assert kat.name == "Betriebseinnahmen"

    re_eintrag = db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == ziel.id).one()
    assert re_eintrag.brutto_betrag == Decimal("238.00")
    assert re_eintrag.art == "Einnahme"
    assert re_eintrag.zahlungsart == "Verrechnung"


def test_eingang_gutschrift_teilweise_verrechnet(db):
    lieferant = db.query(Lieferant).first()
    original = _eingangsrechnung(db, lieferant.id, "ER-2026-1", betrag_netto="100.00")
    gutschrift = _finalisierte_gutschrift(db, original)  # -119.00
    ziel = _eingangsrechnung(db, lieferant.id, "ER-2026-2", betrag_netto="200.00")  # 238.00

    ergebnis = gutschrift_verrechnen(gutschrift.id, GutschriftVerrechnenRequest(rechnung_id=ziel.id), db)

    assert ergebnis.betrag == Decimal("119.00")
    assert ergebnis.gutschrift.zahlungsstatus == "bezahlt"
    assert ergebnis.rechnung.zahlungsstatus == "teilweise"
    assert ergebnis.rechnung.bezahlt_betrag == Decimal("119.00")

    gs_eintrag = db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == gutschrift.id).one()
    assert gs_eintrag.brutto_betrag == Decimal("-119.00")
    assert gs_eintrag.art == "Ausgabe"
    re_eintrag = db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == ziel.id).one()
    assert re_eintrag.brutto_betrag == Decimal("119.00")
    assert re_eintrag.art == "Ausgabe"
    assert re_eintrag.kategorie_id == ziel.kategorie_id


def test_verrechnung_scheitert_bei_unterschiedlichem_kunden(db):
    kunde_a = db.query(Kunde).filter(Kunde.firmenname == "Musterkunde GmbH").first()
    kunde_b = db.query(Kunde).filter(Kunde.firmenname == "Anderer Kunde").first()
    original = _ausgangsrechnung(db, kunde_a.id, "RE-2026-1")
    gutschrift = _finalisierte_gutschrift(db, original)
    ziel = _ausgangsrechnung(db, kunde_b.id, "RE-2026-2")

    with pytest.raises(HTTPException) as exc:
        gutschrift_verrechnen(gutschrift.id, GutschriftVerrechnenRequest(rechnung_id=ziel.id), db)
    assert exc.value.status_code == 400


def test_verrechnung_scheitert_bei_unterschiedlicher_richtung(db):
    kunde = db.query(Kunde).filter(Kunde.firmenname == "Musterkunde GmbH").first()
    lieferant = db.query(Lieferant).first()
    original = _ausgangsrechnung(db, kunde.id, "RE-2026-1")
    gutschrift = _finalisierte_gutschrift(db, original)
    ziel = _eingangsrechnung(db, lieferant.id, "ER-2026-1")

    with pytest.raises(HTTPException) as exc:
        gutschrift_verrechnen(gutschrift.id, GutschriftVerrechnenRequest(rechnung_id=ziel.id), db)
    assert exc.value.status_code == 400


def test_verrechnung_scheitert_gegen_weitere_gutschrift(db):
    kunde = db.query(Kunde).filter(Kunde.firmenname == "Musterkunde GmbH").first()
    original1 = _ausgangsrechnung(db, kunde.id, "RE-2026-1")
    gutschrift1 = _finalisierte_gutschrift(db, original1)
    original2 = _ausgangsrechnung(db, kunde.id, "RE-2026-2")
    gutschrift2 = _finalisierte_gutschrift(db, original2)

    with pytest.raises(HTTPException) as exc:
        gutschrift_verrechnen(gutschrift1.id, GutschriftVerrechnenRequest(rechnung_id=gutschrift2.id), db)
    assert exc.value.status_code == 400
