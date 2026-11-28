"""
Issue #595 (Markus, Community):
- stornierte Ausgangsrechnung: „Ansehen“ zeigt weiter das Original, mit stornorechnung=true die
  Stornorechnung selbst (ohne Archiv, ohne Status-Änderung)
- stornierte Eingangsrechnung: korrigierte Rechnung als Entwurf erfassen (Lieferant, Positionen,
  Kategorie übernommen, Lieferanten-Nr. leer), beidseitig verknüpft wie die Ersatzrechnung
- Erfassungsblatt zeigt Stornodatum und Grund
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from fastapi import HTTPException
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import ersatzrechnung_erstellen, rechnung_als_pdf, rechnung_pdf_ansehen_wrapper
from database.connection import Base
from database.models import Kategorie, Lieferant, Rechnung, Rechnungsposition, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    s.add(Unternehmen(firmenname="Meine Firma", strasse="Hauptstr.", hausnummer="1", plz="12345", ort="Musterstadt"))
    s.commit()
    yield s
    s.close()


def _rechnung(db, typ, **kw) -> Rechnung:
    r = Rechnung(typ=typ, rechnungsnummer=f"R-{typ}", datum=date(2026, 11, 2), partner_freitext="Partner",
                 netto_gesamt=Decimal("100"), ust_gesamt=Decimal("19"), brutto_gesamt=Decimal("119"),
                 ist_entwurf=False, eingabemodus="netto", storniert=True, storno_datum=date(2026, 11, 20),
                 storno_rechnungsnummer="STORNO-260001", storno_grund="Falscher Betrag", **kw)
    db.add(r)
    db.flush()
    db.add(Rechnungsposition(rechnung_id=r.id, position_nr=1, beschreibung="Bretter", menge=Decimal("1"),
                             netto=Decimal("100"), ust_satz=Decimal("19"), ust_betrag=Decimal("19"),
                             brutto=Decimal("119"), kategorie_id=kw.get("kategorie_id")))
    db.commit()
    return r


def _text(resp) -> str:
    return "\n".join(p.extract_text() for p in PdfReader(BytesIO(resp.body)).pages)


def test_ausgang_original_und_stornorechnung_ansehen(db):
    r = _rechnung(db, "ausgang")
    original = _text(rechnung_als_pdf(r.id, nur_ansehen=True, db=db))
    db.rollback()   # wie Request-Ende: Ansehen setzt storniert nur im Speicher zurück
    storno = _text(rechnung_als_pdf(r.id, nur_ansehen=True, stornorechnung=True, db=db))
    assert "STORNO-260001" not in original
    assert "Stornorechnung" in storno and "STORNO-260001" in storno
    db.refresh(r)
    assert r.storniert and not r.ausgegeben and not r.original_pdf_pfad


def test_ansicht_huelle_stornorechnung(db):
    r = _rechnung(db, "ausgang")
    html = rechnung_pdf_ansehen_wrapper(r.id, stornorechnung=True, db=db).body.decode()
    assert "STORNO-260001" in html and "stornorechnung=true" in html
    assert "stornorechnung" not in rechnung_pdf_ansehen_wrapper(r.id, db=db).body.decode().split("<iframe")[1]


def test_eingang_korrigierte_rechnung(db):
    lf = Lieferant(firmenname="Holz Müller GmbH")
    kat = Kategorie(name="Wareneinkauf", kontenart="Aufwand")
    db.add_all([lf, kat])
    db.flush()
    r = _rechnung(db, "eingang", lieferant_id=lf.id, externe_belegnr="HM-4711", kategorie_id=kat.id)

    neu = ersatzrechnung_erstellen(r.id, db=db)
    e = db.get(Rechnung, neu.id)
    assert e.typ == "eingang" and e.ist_entwurf and e.rechnungsnummer is None
    assert e.lieferant_id == lf.id and e.kategorie_id == kat.id and e.externe_belegnr is None
    assert [p.beschreibung for p in e.positionen] == ["Bretter"] and e.positionen[0].kategorie_id == kat.id
    assert e.ersatz_fuer_rechnung_id == r.id
    db.refresh(r)
    assert r.ersatzrechnung_id == e.id
    assert [g.id for g in neu.rechnungs_kette] == [r.id, e.id]

    with pytest.raises(HTTPException) as exc:      # nur einmal
        ersatzrechnung_erstellen(r.id, db=db)
    assert exc.value.status_code == 409


def test_eingang_nicht_storniert_abgelehnt(db):
    r = _rechnung(db, "eingang")
    r.storniert = False
    db.commit()
    with pytest.raises(HTTPException):
        ersatzrechnung_erstellen(r.id, db=db)


def test_erfassungsblatt_mit_storno(db):
    r = _rechnung(db, "eingang")
    text = _text(rechnung_als_pdf(r.id, db=db))
    assert "Storniert am 20.11.2026" in text and "Falscher Betrag" in text
