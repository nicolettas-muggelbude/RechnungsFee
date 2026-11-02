"""
Issue #477 Punkt 3: Dokumentenpakete auch für Rechnungen und Proforma-Rechnungen
(bisher nur Angebot/Auftrag). Dazu: ein gewähltes Paket lässt sich wieder abwählen -
das alte "val is not None"-Muster in update_rechnung() ignorierte ein explizites null.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import auftrag_erstellen, create_rechnung, update_rechnung
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate, RechnungUpdate
from database.connection import Base
from database.models import DokumentenPaket, Kunde, Lieferant, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    session.add(Kunde(firmenname="Kunde AG", strasse="Weg", hausnummer="2", plz="54321", ort="Stadt"))
    session.add(Lieferant(firmenname="Lieferant KG"))
    session.add(DokumentenPaket(name="B2B"))
    session.commit()
    yield session
    session.close()


def _pos():
    return [RechnungspositionCreate(beschreibung="Leistung", netto=Decimal("100"), ust_satz=Decimal("19"))]


@pytest.mark.parametrize("dokument_typ", ["Rechnung", "Proforma", "Angebot", "Auftrag"])
def test_paket_setzen_und_abwaehlen(db, dokument_typ):
    kunde_id = db.query(Kunde).one().id
    paket_id = db.query(DokumentenPaket).one().id
    anlegen = auftrag_erstellen if dokument_typ == "Auftrag" else create_rechnung
    dok = anlegen(RechnungCreate(typ="ausgang", dokument_typ=dokument_typ, datum=date(2026, 10, 30),
                                 kunde_id=kunde_id, dokumentenpaket_id=paket_id, positionen=_pos()), db)
    assert dok.dokumentenpaket_id == paket_id

    # Teil-Update ohne das Feld lässt das Paket stehen
    assert update_rechnung(dok.id, RechnungUpdate(notizen="x"), db).dokumentenpaket_id == paket_id
    # explizites null wählt es ab
    assert update_rechnung(dok.id, RechnungUpdate(dokumentenpaket_id=None), db).dokumentenpaket_id is None
    assert update_rechnung(dok.id, RechnungUpdate(dokumentenpaket_id=paket_id), db).dokumentenpaket_id == paket_id


def test_kein_paket_bei_lieferschein_und_eingang(db):
    kunde_id = db.query(Kunde).one().id
    lief_id = db.query(Lieferant).one().id
    paket_id = db.query(DokumentenPaket).one().id
    ls = create_rechnung(RechnungCreate(typ="ausgang", dokument_typ="Lieferschein", datum=date(2026, 10, 30),
                                        kunde_id=kunde_id, dokumentenpaket_id=paket_id, positionen=_pos()), db)
    assert ls.dokumentenpaket_id is None

    er = create_rechnung(RechnungCreate(typ="eingang", datum=date(2026, 10, 30), lieferant_id=lief_id,
                                        dokumentenpaket_id=paket_id, positionen=_pos()), db)
    assert er.dokumentenpaket_id is None
    assert update_rechnung(er.id, RechnungUpdate(dokumentenpaket_id=paket_id), db).dokumentenpaket_id is None


@pytest.mark.parametrize('umwandlung', ['auftrag_aus_angebot', 'proforma_aus_angebot', 'rechnung_aus_angebot'])
def test_paket_wandert_nicht_mit(db, umwandlung):
    # Pakete gehen in der Regel nur einmal an den Kunden - das Folgedokument startet ohne
    import api.rechnungen as r
    from database.models import Rechnung
    kunde_id = db.query(Kunde).one().id
    paket_id = db.query(DokumentenPaket).one().id
    ang = create_rechnung(RechnungCreate(typ='ausgang', dokument_typ='Angebot', datum=date(2026, 10, 30),
                                         kunde_id=kunde_id, dokumentenpaket_id=paket_id, ist_entwurf=False,
                                         positionen=_pos()), db)
    db.query(Rechnung).filter(Rechnung.id == ang.id).update({Rechnung.angebot_status: 'akzeptiert'})
    db.commit()
    folge = getattr(r, umwandlung)(ang.id, db)
    assert folge.dokumentenpaket_id is None
