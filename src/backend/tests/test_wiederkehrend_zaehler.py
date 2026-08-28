"""
Community-Issue #370: Der "Erstellt"-Zähler einer Rechnungsvorlage
(erstellte_rechnungen) wurde bei jeder Entwurfserstellung hochgezählt, aber nie
wieder heruntergezählt, wenn dieser Entwurf ohne Finalisierung wieder gelöscht
wurde - der Zähler blieb "3x erstellt" stehen, obwohl real keine Rechnung mehr
existierte. Das blockierte auch dauerhaft das Löschen der Vorlage (Guard in
loesche_vorlage() prüfte denselben veralteten Zähler). Fix: erstellte_rechnungen
wird nicht mehr aus der Spalte gelesen, sondern live aus der Anzahl tatsächlich
noch vorhandener Rechnungen mit dieser vorlage_id gezählt - damit korrigiert
sich der Zähler von selbst, sobald ein Entwurf gelöscht wird.
"""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.wiederkehrend import entwurf_jetzt, get_vorlage, loesche_vorlage
from database.connection import Base
from database.models import Rechnung, Rechnungsvorlage, Unternehmen


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


def _vorlage(db) -> Rechnungsvorlage:
    v = Rechnungsvorlage(
        bezeichnung="Monatliche Wartung", intervall="monatlich",
        naechstes_datum=date(2026, 1, 1), positionen_json="[]",
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def test_zaehler_zaehlt_tatsaechlich_vorhandene_rechnungen(db):
    v = _vorlage(db)
    entwurf_jetzt(v.id, db)
    entwurf_jetzt(v.id, db)

    resp = get_vorlage(v.id, db)
    assert resp.erstellte_rechnungen == 2


def test_zaehler_sinkt_wenn_entwurf_geloescht_wird(db):
    """Kernfehler aus Issue #370: gelöschter Entwurf muss den Zähler senken."""
    v = _vorlage(db)
    entwurf_jetzt(v.id, db)
    entwurf_jetzt(v.id, db)

    rechnung = db.query(Rechnung).filter(Rechnung.vorlage_id == v.id).first()
    db.delete(rechnung)
    db.commit()

    resp = get_vorlage(v.id, db)
    assert resp.erstellte_rechnungen == 1


def test_vorlage_ohne_verbleibende_rechnungen_ist_loeschbar(db):
    """Vorher blockierte der veraltete Zähler das Löschen dauerhaft, selbst wenn
    der einzige jemals erstellte Entwurf längst gelöscht war."""
    v = _vorlage(db)
    entwurf_jetzt(v.id, db)

    rechnung = db.query(Rechnung).filter(Rechnung.vorlage_id == v.id).first()
    db.delete(rechnung)
    db.commit()

    loesche_vorlage(v.id, db)  # darf keine HTTPException werfen

    assert db.query(Rechnungsvorlage).filter(Rechnungsvorlage.id == v.id).first() is None
