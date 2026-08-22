"""
Tests für Issue #366, Mahnwesen-Teil: offene Kundengutschriften werden beim Anlegen einer
Mahnung automatisch mit den mahnrelevanten Rechnungen verrechnet (Nutzer-Vorgabe "automatisch
mindern"), BEVOR der Mahnbetrag berechnet wird. /vorschau bleibt dabei side-effect-frei (keine
Buchung) und zeigt den Effekt nur informativ über das neue Feld gutschrift_verrechnung.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.mahnwesen import erstellen, vorschau
from api.rechnungen import create_gutschrift, finalisiere_rechnung
from api.schemas import MahnungErstellenRequest, MahnungVorschauRequest
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Kunde, Mahnstufe, Rechnung, Rechnungsposition, Unternehmen


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
    session.add(Mahnstufe(stufe=1, bezeichnung="Zahlungserinnerung", mahngebuehr_aktiv=False))
    session.add(Kunde(firmenname="Musterkunde GmbH"))
    session.commit()
    yield session
    session.close()


def _offene_ausgangsrechnung(db, kunde_id, nr, betrag_netto="200.00", satz="19", faellig_vor_tagen=30) -> Rechnung:
    netto = Decimal(betrag_netto)
    ust = (netto * Decimal(satz) / 100).quantize(Decimal("0.01"))
    rechnung = Rechnung(
        typ="ausgang", rechnungsnummer=nr, datum=date.today() - timedelta(days=faellig_vor_tagen + 14),
        faellig_am=date.today() - timedelta(days=faellig_vor_tagen), kunde_id=kunde_id,
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


def test_vorschau_zeigt_gutschrift_verrechnung_ohne_zu_buchen(db):
    kunde = db.query(Kunde).first()
    original = _offene_ausgangsrechnung(db, kunde.id, "RE-2026-1", betrag_netto="100.00")
    gs_resp = create_gutschrift(original.id, db)
    finalisiere_rechnung(gs_resp.id, db)
    gutschrift = db.query(Rechnung).filter(Rechnung.id == gs_resp.id).first()
    ziel = _offene_ausgangsrechnung(db, kunde.id, "RE-2026-2", betrag_netto="300.00")

    result = vorschau(MahnungVorschauRequest(rechnung_ids=[ziel.id], stufe=1), db)

    # 300*1.19=357.00 Rechnung, Gutschrift -119.00 -> 119.00 automatisch verrechnet
    assert result.gutschrift_verrechnung == Decimal("119.00")
    assert result.offener_betrag_gesamt == Decimal("238.00")

    # Side-effect-frei: keine Buchung, kein zahlungsstatus-Wechsel durch /vorschau
    assert db.query(Journaleintrag).count() == 0
    db.refresh(ziel)
    db.refresh(gutschrift)
    assert ziel.zahlungsstatus == "offen"
    assert gutschrift.zahlungsstatus == "offen"


def test_erstellen_verrechnet_offene_gutschrift_automatisch(db):
    kunde = db.query(Kunde).first()
    original = _offene_ausgangsrechnung(db, kunde.id, "RE-2026-1", betrag_netto="100.00")
    gutschrift = create_gutschrift(original.id, db)
    finalisiere_rechnung(gutschrift.id, db)
    ziel = _offene_ausgangsrechnung(db, kunde.id, "RE-2026-2", betrag_netto="300.00")

    mahnung = erstellen(MahnungErstellenRequest(rechnung_ids=[ziel.id], stufe=1), db)

    assert mahnung.offener_betrag_gesamt == Decimal("238.00")

    db.refresh(ziel)
    gs = db.query(Rechnung).filter(Rechnung.id == gutschrift.id).first()
    assert gs.zahlungsstatus == "bezahlt"
    assert ziel.zahlungsstatus == "teilweise"
    assert ziel.bezahlt_betrag == Decimal("119.00")
