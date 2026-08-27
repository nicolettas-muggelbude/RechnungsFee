"""
Tests für die Kontokorrent-Übersicht (docs/ROADMAP.md: "alle Partner mit offenem
Saldo auf einen Blick"): GET /api/kontokorrent/uebersicht muss Kunden/Lieferanten
mit offener Forderung/Verbindlichkeit als "offen", mit Überzahlung als "guthaben"
und ausgeglichene Partner gar nicht auflisten. Nutzt bewusst dieselbe
Bewegungslogik wie die bestehende Einzelansicht (kontokorrent_kunde/
kontokorrent_lieferant) - hier wird nur die Aggregation über alle Partner geprüft.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.kontokorrent import kontokorrent_uebersicht
from database.connection import Base
from database.models import Journaleintrag, Kunde, Lieferant, Rechnung, Unternehmen


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


def _ausgangsrechnung(db, kunde_id, brutto="119.00") -> Rechnung:
    r = Rechnung(
        typ="ausgang", kunde_id=kunde_id, rechnungsnummer=f"RE-{kunde_id}",
        datum=date(2026, 1, 5), dokument_typ="Rechnung",
        brutto_gesamt=Decimal(brutto), netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("19.00"),
        ist_entwurf=False, zahlungsstatus="offen", bezahlt_betrag=Decimal("0.00"),
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def _eingangsrechnung(db, lieferant_id, brutto="238.00") -> Rechnung:
    r = Rechnung(
        typ="eingang", lieferant_id=lieferant_id, rechnungsnummer=f"ER-{lieferant_id}",
        datum=date(2026, 1, 5), dokument_typ="Rechnung",
        brutto_gesamt=Decimal(brutto), netto_gesamt=Decimal("200.00"), ust_gesamt=Decimal("38.00"),
        ist_entwurf=False, zahlungsstatus="offen", bezahlt_betrag=Decimal("0.00"),
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def _zahlung(db, rechnung_id, betrag, belegnr, art="Einnahme"):
    db.add(Journaleintrag(
        datum=date(2026, 1, 10), belegnr=belegnr, beschreibung="Zahlung", zahlungsart="Bank",
        art=art, netto_betrag=Decimal(betrag), brutto_betrag=Decimal(betrag),
        rechnung_id=rechnung_id,
    ))
    db.commit()


def test_kunde_mit_offener_rechnung_erscheint_als_offen(db):
    kunde = Kunde(firmenname="Offene Kunde GmbH")
    db.add(kunde)
    db.commit()
    db.refresh(kunde)
    _ausgangsrechnung(db, kunde.id)

    ergebnis = kontokorrent_uebersicht(db)

    treffer = [p for p in ergebnis if p.partner_typ == "kunde" and p.partner_id == kunde.id]
    assert len(treffer) == 1
    assert treffer[0].status == "offen"
    assert treffer[0].saldo == 119.0


def test_ausgeglichener_kunde_erscheint_nicht(db):
    kunde = Kunde(firmenname="Ausgeglichene Kunde GmbH")
    db.add(kunde)
    db.commit()
    db.refresh(kunde)
    r = _ausgangsrechnung(db, kunde.id)
    _zahlung(db, r.id, "119.00", "Z-1")

    ergebnis = kontokorrent_uebersicht(db)

    assert not any(p.partner_typ == "kunde" and p.partner_id == kunde.id for p in ergebnis)


def test_ueberzahlter_kunde_erscheint_als_guthaben(db):
    kunde = Kunde(firmenname="Guthaben Kunde GmbH")
    db.add(kunde)
    db.commit()
    db.refresh(kunde)
    r = _ausgangsrechnung(db, kunde.id)
    _zahlung(db, r.id, "150.00", "Z-2")  # mehr als die 119,00 Rechnung

    ergebnis = kontokorrent_uebersicht(db)

    treffer = [p for p in ergebnis if p.partner_typ == "kunde" and p.partner_id == kunde.id]
    assert len(treffer) == 1
    assert treffer[0].status == "guthaben"
    assert treffer[0].saldo == -31.0


def test_lieferant_mit_offener_rechnung_erscheint_als_offen(db):
    lieferant = Lieferant(firmenname="Offener Lieferant GmbH")
    db.add(lieferant)
    db.commit()
    db.refresh(lieferant)
    _eingangsrechnung(db, lieferant.id)

    ergebnis = kontokorrent_uebersicht(db)

    treffer = [p for p in ergebnis if p.partner_typ == "lieferant" and p.partner_id == lieferant.id]
    assert len(treffer) == 1
    assert treffer[0].status == "offen"
    assert treffer[0].saldo == 238.0


def test_ueberzahlter_lieferant_erscheint_als_guthaben(db):
    lieferant = Lieferant(firmenname="Guthaben Lieferant GmbH")
    db.add(lieferant)
    db.commit()
    db.refresh(lieferant)
    r = _eingangsrechnung(db, lieferant.id)
    _zahlung(db, r.id, "300.00", "Z-3", art="Ausgabe")  # mehr als die 238,00 Rechnung

    ergebnis = kontokorrent_uebersicht(db)

    treffer = [p for p in ergebnis if p.partner_typ == "lieferant" and p.partner_id == lieferant.id]
    assert len(treffer) == 1
    assert treffer[0].status == "guthaben"
    assert treffer[0].saldo == -62.0


def test_sortiert_nach_betrag_absteigend(db):
    klein = Kunde(firmenname="Klein GmbH")
    gross = Kunde(firmenname="Groß GmbH")
    db.add_all([klein, gross])
    db.commit()
    db.refresh(klein)
    db.refresh(gross)
    _ausgangsrechnung(db, klein.id, brutto="50.00")
    _ausgangsrechnung(db, gross.id, brutto="500.00")

    ergebnis = kontokorrent_uebersicht(db)

    namen = [p.name for p in ergebnis]
    assert namen.index("Groß GmbH") < namen.index("Klein GmbH")
