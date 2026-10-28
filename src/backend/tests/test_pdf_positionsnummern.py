"""
Issue #475: optionale Spalte "Pos." in der Standard-Vorlage (Vorlage 0).

Vorlage 1 zeigt Positionsnummern schon immer, in Vorlage 0 sind sie jetzt per
unternehmen.pdf_positionsnummern zuschaltbar (Standard: aus). Die Breite geht von der
Beschreibung ab - Beträge und Summenblock bleiben an ihrer Stelle.
"""
import json
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import _absender_snapshot, create_rechnung, rechnung_als_pdf
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate
from database.connection import Base
from database.models import Artikel, Kunde, Rechnung, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345",
                            ort="Testort", ist_kleinunternehmer=False))
    session.add(Kunde(firmenname="Kunde AG", strasse="Weg", hausnummer="2", plz="54321", ort="Stadt"))
    session.add(Artikel(artikelnummer="ART-0001", typ="artikel", bezeichnung="Ölfilter", einheit="Stück",
                        artikelcode="AW5010KS", vk_brutto=119, vk_netto=100, steuersatz=19, aktiv=True))
    session.commit()
    yield session
    session.close()


def _rechnung(db, mit_artikel: bool = False):
    art_id = db.query(Artikel).one().id if mit_artikel else None
    return create_rechnung(RechnungCreate(
        typ="ausgang", datum=date(2026, 10, 28), kunde_id=db.query(Kunde).one().id,
        positionen=[RechnungspositionCreate(beschreibung=f"Leistung {i}", netto=Decimal("100"),
                                            ust_satz=Decimal("19"), artikel_id=art_id)
                    for i in range(1, 4)],
    ), db)


def _text(db, rechnung_id: int) -> str:
    pdf = rechnung_als_pdf(rechnung_id, vorlage=0, nur_ansehen=True, db=db).body
    return "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)


def _schalten(db, an: bool):
    db.query(Unternehmen).one().pdf_positionsnummern = an
    db.commit()


def test_standard_ohne_positionsnummern(db):
    text = _text(db, _rechnung(db).id)
    assert "Pos." not in text
    assert "Gesamtbetrag 357,00 €" in text


@pytest.mark.parametrize("mit_artikel", [False, True])
def test_positionsnummern_eingeschaltet(db, mit_artikel):
    _schalten(db, True)
    text = _text(db, _rechnung(db, mit_artikel).id)
    assert "Pos." in text
    for i in range(1, 4):
        assert f"{i} Leistung {i}" in text or f"{i}\nLeistung {i}" in text or f"{i} AW5010KS" in text
    if mit_artikel:
        assert text.count("AW5010KS") == 3
    assert "Gesamtbetrag 357,00 €" in text


def test_lieferschein_mit_positionsnummern(db):
    _schalten(db, True)
    r = _rechnung(db, mit_artikel=True)
    db.query(Rechnung).filter(Rechnung.id == r.id).one().dokument_typ = "Lieferschein"
    db.commit()
    text = _text(db, r.id)
    assert "Pos." in text and text.count("AW5010KS") == 3
    assert "100,00" not in text  # Lieferschein ohne Preise


def test_snapshot_friert_einstellung_ein(db):
    _schalten(db, True)
    assert json.loads(_absender_snapshot(db))["pdf_positionsnummern"] is True
    # vor Issue #475 finalisierte Dokumente haben den Schlüssel nicht -> keine Spalte
    r = _rechnung(db)
    alt = json.loads(_absender_snapshot(db))
    del alt["pdf_positionsnummern"]
    db.query(Rechnung).filter(Rechnung.id == r.id).one().absender_snapshot = json.dumps(alt)
    db.commit()
    assert "Pos." not in _text(db, r.id)
