"""
Regressionstest für Issue #355.

Direkt gebuchte Buchungsvorlagen (Modus "direkt", z.B. Dauerauftrag/SEPA) erzeugten bisher
einen Journal-Eintrag komplett ohne Möglichkeit, einen Beleg anzuhängen - obwohl
journal.beleg_id als Feld längst existiert und beim manuellen Buchen (BuchungForm.tsx) auch
genutzt wird. POST /{vorlage_id}/buchen akzeptiert jetzt optional {"beleg_id": ...} - der Beleg
wird analog zur Split-Buchung (Issue #310) vorab über POST /journal/anhang-vorab hochgeladen,
da der Journal-Eintrag ab Erstellung immutable ist.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.buchungsvorlagen import BuchenRequest, buche_vorlage
from database.connection import Base
from database.models import Beleg, Buchungsvorlage, Journaleintrag


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _vorlage(db) -> Buchungsvorlage:
    v = Buchungsvorlage(
        bezeichnung="Büromiete", betrag=Decimal("500.00"), ist_brutto=True, ust_satz=Decimal("19"),
        intervall="monatlich", naechstes_datum=date(2026, 1, 1), modus="direkt", art="Ausgabe",
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def test_buchen_ohne_beleg_unveraendert(db):
    v = _vorlage(db)
    buche_vorlage(v.id, data=BuchenRequest(), db=db)
    eintrag = db.query(Journaleintrag).filter(Journaleintrag.buchungsvorlage_id == v.id).first()
    assert eintrag is not None
    assert eintrag.beleg_id is None


def test_buchen_mit_beleg_verknuepft_journal_eintrag(db):
    v = _vorlage(db)
    beleg = Beleg(dateiname="x.pdf", original_name="Kontoauszug.pdf", mime_type="application/pdf", dateigroesse=100, sha256="abc")
    db.add(beleg)
    db.commit()
    db.refresh(beleg)

    buche_vorlage(v.id, data=BuchenRequest(beleg_id=beleg.id), db=db)

    eintrag = db.query(Journaleintrag).filter(Journaleintrag.buchungsvorlage_id == v.id).first()
    assert eintrag is not None
    assert eintrag.beleg_id == beleg.id


def test_buchen_default_request_entspricht_keinem_beleg(db):
    v = _vorlage(db)
    # So wie es ankommt, wenn das Frontend keinen Body mitschickt bzw. beleg_id weglässt.
    buche_vorlage(v.id, data=BuchenRequest(), db=db)
    eintrag = db.query(Journaleintrag).filter(Journaleintrag.buchungsvorlage_id == v.id).first()
    assert eintrag.beleg_id is None
