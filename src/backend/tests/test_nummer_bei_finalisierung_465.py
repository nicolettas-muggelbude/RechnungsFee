"""
Issue #465 / #551: Rechnungsnummer erst beim Finalisieren.
- Entwürfe von Rechnung, Abschlagsrechnung und Gutschrift bekommen keine Nummer (außer von Hand)
- Vergabe beim Finalisieren aus dem passenden Kreis zum Rechnungsdatum - gelöschte Entwürfe
  hinterlassen keine Lücke, die Reihenfolge folgt der Finalisierung
- direkt finalisiert angelegte Rechnungen wie bisher sofort
- wiederkehrende Rechnung: eigener Kreis, falls aktiv
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import create_rechnung, delete_rechnung, finalisiere_rechnung, update_rechnung
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate, RechnungUpdate
from database.connection import Base
from database.models import Kunde, Nummernkreis, Rechnung, Rechnungsvorlage, Unternehmen

HEUTE = date.today()


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    s.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O"))
    for typ, fmt, aktiv in [("rechnung_ausgang", "RE-####", True), ("rechnung_eingang", "ER-####", True),
                            ("gutschrift", "GS-####", True), ("abschlagsrechnung", "AR-####", True),
                            ("rechnung_wiederkehrend", "WR-####", True)]:
        s.add(Nummernkreis(bezeichnung=typ, typ=typ, format=fmt, naechste_nr=1, reset_jaehrlich=False, aktiv=aktiv))
    s.add(Kunde(firmenname="Kunde GmbH", strasse="Str", hausnummer="2", plz="12345", ort="Ort"))
    s.commit()
    yield s
    s.close()


def _neu(db, **extra):
    daten = dict(typ="ausgang", datum=HEUTE, kunde_id=db.query(Kunde).one().id,
                 positionen=[RechnungspositionCreate(beschreibung="Leistung", netto=Decimal("100"), ust_satz=Decimal("19"))])
    daten.update(extra)
    return create_rechnung(RechnungCreate(**daten), db)


def test_entwurf_ohne_nummer_vergabe_beim_finalisieren(db):
    a = _neu(db)
    b = _neu(db)
    c = _neu(db)
    assert (a.rechnungsnummer, b.rechnungsnummer, c.rechnungsnummer) == (None, None, None)
    delete_rechnung(b.id, db)                       # gelöschter Entwurf: keine Lücke
    assert finalisiere_rechnung(c.id, db).rechnungsnummer == "RE-0001"  # Reihenfolge der Finalisierung
    assert finalisiere_rechnung(a.id, db).rechnungsnummer == "RE-0002"


def test_direkt_finalisiert_und_manuelle_nummer(db):
    assert _neu(db, ist_entwurf=False).rechnungsnummer == "RE-0001"
    manuell = _neu(db, rechnungsnummer="ALT-7")
    assert manuell.rechnungsnummer == "ALT-7"
    assert finalisiere_rechnung(manuell.id, db).rechnungsnummer == "ALT-7"


def test_finalisieren_ueber_update(db):
    r = _neu(db)
    assert update_rechnung(r.id, RechnungUpdate(ist_entwurf=False), db).rechnungsnummer == "RE-0001"


def test_abschlag_und_wiederkehrend_aus_eigenem_kreis(db):
    ab = _neu(db, dokument_typ="Abschlagsrechnung")
    assert ab.rechnungsnummer is None
    assert finalisiere_rechnung(ab.id, db).rechnungsnummer == "AR-0001"

    v = Rechnungsvorlage(bezeichnung="Abo", kunde_id=db.query(Kunde).one().id, intervall="monatlich",
                         naechstes_datum=HEUTE, positionen_json="[]")
    db.add(v)
    db.commit()
    w = _neu(db)
    db.query(Rechnung).filter(Rechnung.id == w.id).update({"vorlage_id": v.id})
    db.commit()
    assert finalisiere_rechnung(w.id, db).rechnungsnummer == "WR-0001"


def test_gutschrift_entwurf_ohne_nummer(db):
    from api.rechnungen import create_gutschrift
    original = _neu(db, ist_entwurf=False, datum=HEUTE - timedelta(days=3))
    gs = create_gutschrift(original.id, db=db)
    assert gs.rechnungsnummer is None
    assert finalisiere_rechnung(gs.id, db).rechnungsnummer == "GS-0001"


def test_angebot_behaelt_nummer_ab_anlage(db):
    db.add(Nummernkreis(bezeichnung="angebot", typ="angebot", format="ANG-####", naechste_nr=1,
                        reset_jaehrlich=False, aktiv=True))
    db.commit()
    assert _neu(db, dokument_typ="Angebot").rechnungsnummer == "ANG-0001"
