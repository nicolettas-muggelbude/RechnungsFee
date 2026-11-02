"""
Issue #478: Empfänger eines Entwurfs von einem Stammdaten-Kunden auf einen frei eingetippten
Empfänger (Einmalkunde) umstellen - bisher blieb die alte kunde_id stehen, und weil kunde_name
überall Vorrang hat, war der neue Empfänger nach dem Speichern wieder weg.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import create_rechnung, update_rechnung
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate, RechnungUpdate
from database.connection import Base
from database.models import Kunde, Lieferant, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    session.add(Kunde(firmenname="Stammkunde AG", strasse="Weg", hausnummer="2", plz="54321", ort="Stadt"))
    session.add(Lieferant(firmenname="Stammlieferant KG"))
    session.commit()
    yield session
    session.close()


def _pos():
    return [RechnungspositionCreate(beschreibung="Leistung", netto=Decimal("100"), ust_satz=Decimal("19"))]


@pytest.mark.parametrize("dokument_typ", ["Angebot", "Auftrag", "Proforma", "Rechnung"])
def test_kunde_zu_einmalkunde(db, dokument_typ):
    kunde_id = db.query(Kunde).one().id
    dok = create_rechnung(RechnungCreate(typ="ausgang", dokument_typ=dokument_typ, datum=date(2026, 10, 30),
                                         kunde_id=kunde_id, positionen=_pos()), db)
    assert dok.kunde_id == kunde_id

    neu = update_rechnung(dok.id, RechnungUpdate(
        partner_freitext="Gerti Einmalig", partner_strasse="Gasse", partner_plz="11111", partner_ort="Dorf",
        positionen=_pos(),
    ), db)
    assert neu.kunde_id is None
    assert neu.kunde_name is None
    assert neu.partner_freitext == "Gerti Einmalig"


def test_einmalkunde_zu_kunde(db):
    kunde_id = db.query(Kunde).one().id
    dok = create_rechnung(RechnungCreate(typ="ausgang", dokument_typ="Angebot", datum=date(2026, 10, 30),
                                         partner_freitext="Gerti Einmalig", positionen=_pos()), db)
    neu = update_rechnung(dok.id, RechnungUpdate(kunde_id=kunde_id, positionen=_pos()), db)
    assert neu.kunde_id == kunde_id


def test_eingangsrechnung_lieferant_zu_freitext(db):
    lief_id = db.query(Lieferant).one().id
    dok = create_rechnung(RechnungCreate(typ="eingang", datum=date(2026, 10, 30), lieferant_id=lief_id,
                                         positionen=_pos()), db)
    neu = update_rechnung(dok.id, RechnungUpdate(partner_freitext="Baumarkt um die Ecke", positionen=_pos()), db)
    assert neu.lieferant_id is None
    assert neu.partner_freitext == "Baumarkt um die Ecke"


def test_teil_update_laesst_kunde_stehen(db):
    kunde_id = db.query(Kunde).one().id
    dok = create_rechnung(RechnungCreate(typ="ausgang", dokument_typ="Angebot", datum=date(2026, 10, 30),
                                         kunde_id=kunde_id, positionen=_pos()), db)
    assert update_rechnung(dok.id, RechnungUpdate(notizen="nur Notiz"), db).kunde_id == kunde_id
