"""
Issue #548: Ein Rechnungsentwurf, auf den ein anderes Dokument zurückverweist, ließ sich nicht
löschen – „IntegrityError: FOREIGN KEY constraint failed“ (PRAGMA foreign_keys=ON).

- Ersatzrechnung (Entwurf) nach Storno: das Original trägt ersatzrechnung_id
- Rechnung (Entwurf) aus einem Angebot: das Angebot trägt rechnung_zu_angebot_id

Nach dem Löschen muss das Ausgangsdokument wieder frei sein (neue Ersatzrechnung bzw. neue
Rechnung aus dem Angebot möglich).
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from api.rechnungen import (
    create_rechnung, delete_rechnung, ersatzrechnung_erstellen, finalisiere_rechnung, rechnung_aus_angebot,
    storno_rechnung,
)
from api.schemas import StornoRequest
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate
from database.connection import Base
from database.models import Kunde, Nummernkreis, Rechnung, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O",
                            angebote_aktiv=True))
    for typ, fmt in [("rechnung_ausgang", "RE-YY####"), ("angebot", "ANG-YY####"),
                     ("stornorechnung", "STORNO-YY####"), ("journal", "YY####")]:
        session.add(Nummernkreis(bezeichnung=typ, typ=typ, format=fmt, naechste_nr=1, reset_jaehrlich=True, aktiv=True))
    session.add(Kunde(firmenname="JWD GmbH", strasse="Str", hausnummer="2", plz="12345", ort="Ort"))
    session.commit()
    yield session
    session.close()


def _daten(db, **extra) -> RechnungCreate:
    return RechnungCreate(
        typ="ausgang", datum=date(2026, 11, 15), kunde_id=db.query(Kunde).one().id,
        positionen=[RechnungspositionCreate(beschreibung="Reinigung", netto=Decimal("500"), ust_satz=Decimal("19"))],
        **extra,
    )


def test_ersatzrechnung_entwurf_loeschbar(db):
    original = create_rechnung(_daten(db), db)
    finalisiere_rechnung(original.id, db)
    storno_rechnung(original.id, StornoRequest(grund="Fehler"), db)
    ersatz = ersatzrechnung_erstellen(original.id, db)

    delete_rechnung(ersatz.id, db)

    assert db.query(Rechnung).filter(Rechnung.id == ersatz.id).first() is None
    orig = db.query(Rechnung).filter(Rechnung.id == original.id).one()
    assert orig.ersatzrechnung_id is None
    # Original ist wieder frei für eine neue Ersatzrechnung
    assert ersatzrechnung_erstellen(original.id, db).ersatz_fuer_rechnung_id == original.id


def test_rechnung_aus_angebot_entwurf_loeschbar(db):
    angebot = create_rechnung(_daten(db, dokument_typ="Angebot", ist_entwurf=False), db)
    rechnung = rechnung_aus_angebot(angebot.id, db)

    delete_rechnung(rechnung.id, db)

    ang = db.query(Rechnung).filter(Rechnung.id == angebot.id).one()
    assert ang.rechnung_zu_angebot_id is None
    assert rechnung_aus_angebot(angebot.id, db).id
