"""
Issue #563: Skonto und Zahlungsziel aus den Einstellungen wurden bei Rechnungen aus Angebot,
Auftrag und Lieferschein nicht übernommen (nur das Rechnungsformular belegte sie vor).

- Angebot/Auftrag → Rechnung: Skonto vom Kunden, sonst aus den Einstellungen
- Lieferschein → Rechnung (auch Sammelrechnung): zusätzlich Fälligkeit aus dem Zahlungsziel
- Zahlungsziel 0 = keine Fälligkeit (wie Issue #411)
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import (
    auftrag_aus_angebot, create_rechnung, rechnung_aus_angebot, rechnung_aus_auftrag, rechnung_aus_lieferschein,
)
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate
from database.connection import Base
from database.models import Kunde, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(
        firmenname="Testfirma", strasse="Weg", hausnummer="1", plz="12345", ort="Ort", steuernummer="12/345/67890",
        standard_zahlungsziel=30, standard_skonto_prozent=Decimal("2"), standard_skonto_tage=10,
    ))
    session.add(Kunde(firmenname="Kunde GmbH", strasse="Str", hausnummer="2", plz="12345", ort="Ort"))
    session.commit()
    yield session
    session.close()


def _dok(db, dokument_typ, **kw) -> RechnungCreate:
    return RechnungCreate(
        typ="ausgang", dokument_typ=dokument_typ, datum=date(2026, 11, 17), ist_entwurf=False,
        kunde_id=db.query(Kunde).one().id,
        positionen=[RechnungspositionCreate(beschreibung="Beratung", menge=Decimal("1"), netto=Decimal("100"),
                                            ust_satz=Decimal("19"))],
        **kw,
    )


def _skonto(r):
    return (Decimal(str(r.skonto_prozent)) if r.skonto_prozent is not None else None, r.skonto_tage)


def test_angebot_zu_rechnung_skonto_aus_einstellungen(db):
    rechnung = rechnung_aus_angebot(create_rechnung(_dok(db, "Angebot"), db).id, db)
    assert _skonto(rechnung) == (Decimal("2"), 10)
    assert rechnung.faellig_am == date.today() + timedelta(days=30)


def test_kunde_hat_vorrang(db):
    k = db.query(Kunde).one()
    k.skonto_prozent, k.skonto_tage = Decimal("3"), 7
    db.commit()
    rechnung = rechnung_aus_angebot(create_rechnung(_dok(db, "Angebot"), db).id, db)
    assert _skonto(rechnung) == (Decimal("3"), 7)


def test_auftrag_zu_rechnung(db):
    angebot = create_rechnung(_dok(db, "Angebot"), db)
    rechnung = rechnung_aus_auftrag(auftrag_aus_angebot(angebot.id, db).id, db)
    assert _skonto(rechnung) == (Decimal("2"), 10)


def test_lieferschein_zu_rechnung_faelligkeit_und_skonto(db):
    ls = create_rechnung(_dok(db, "Lieferschein"), db)
    rechnung = rechnung_aus_lieferschein(ls.id, db)
    assert rechnung.faellig_am == date.today() + timedelta(days=30)
    assert _skonto(rechnung) == (Decimal("2"), 10)


def test_ohne_vorgaben_bleibt_leer(db):
    u = db.query(Unternehmen).one()
    u.standard_zahlungsziel, u.standard_skonto_prozent, u.standard_skonto_tage = 0, None, None
    db.commit()
    rechnung = rechnung_aus_lieferschein(create_rechnung(_dok(db, "Lieferschein"), db).id, db)
    assert rechnung.faellig_am is None
    assert _skonto(rechnung) == (None, None)
