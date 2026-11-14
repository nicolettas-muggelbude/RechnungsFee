"""
Issue #534: ZUGFeRD hing seit #332 versehentlich am Erfassungsmodus (eingabemodus == "netto")
statt am Kunden-Schalter kunde.zugferd_aktiv. Eine Brutto-Rechnung an einen ZUGFeRD-Kunden
zeigte in der Detailansicht "ZUGFeRD ✓", das PDF enthielt aber keine XML.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api.rechnungen as rechnungen_mod
import utils.zugferd as zugferd_mod
from api.rechnungen import rechnung_als_pdf
from database.connection import Base
from database.models import Kunde, Rechnung, Rechnungsposition, Unternehmen


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(rechnungen_mod, "APP_DATA_DIR", tmp_path)
    monkeypatch.setattr(zugferd_mod, "APP_DATA_DIR", tmp_path)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(
        firmenname="Testfirma GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort",
        steuernummer="12/345/67890",
    ))
    session.commit()
    yield session
    session.close()


def _rechnung(db, *, zugferd_kunde: bool, eingabemodus: str) -> Rechnung:
    kunde = Kunde(firmenname="Musterkunde GmbH", strasse="Kundenweg", hausnummer="2", plz="54321",
                  ort="Kundenstadt", zugferd_aktiv=zugferd_kunde)
    db.add(kunde)
    db.commit()
    # Ein Artikel zu 3,50 € brutto (19 %): Einzelpreis im jeweiligen Erfassungsmodus
    einzelpreis = Decimal("3.50") if eingabemodus == "brutto" else Decimal("2.94")
    r = Rechnung(
        typ="ausgang", kunde_id=kunde.id, rechnungsnummer="RE-260001", datum=date(2026, 11, 1),
        dokument_typ="Rechnung", eingabemodus=eingabemodus, ist_entwurf=False,
        netto_gesamt=Decimal("2.94"), ust_gesamt=Decimal("0.56"), brutto_gesamt=Decimal("3.50"),
    )
    db.add(r)
    db.commit()
    db.add(Rechnungsposition(
        rechnung_id=r.id, position_nr=1, beschreibung="Testartikel", menge=Decimal("1"), einheit="Stück",
        netto=einzelpreis, ust_satz=Decimal("19"), ust_betrag=Decimal("0.56"), brutto=Decimal("3.50"),
    ))
    db.commit()
    db.refresh(r)
    return r


def _pdf(db, r) -> PdfReader:
    resp = rechnung_als_pdf(r.id, nur_ansehen=True, db=db)
    return PdfReader(BytesIO(resp.body))


def _text(reader: PdfReader) -> str:
    return "\n".join(p.extract_text() or "" for p in reader.pages)


def test_brutto_rechnung_an_zugferd_kunden_enthaelt_xml(db):
    reader = _pdf(db, _rechnung(db, zugferd_kunde=True, eingabemodus="brutto"))
    assert "xrechnung.xml" in reader.attachments
    # Sichtbares PDF liest den Brutto-Einzelpreis nicht als Netto (sonst 4,17 €)
    text = _text(reader)
    assert "3,50" in text
    assert "4,17" not in text


def test_netto_rechnung_an_zugferd_kunden_enthaelt_xml(db):
    reader = _pdf(db, _rechnung(db, zugferd_kunde=True, eingabemodus="netto"))
    assert "xrechnung.xml" in reader.attachments


def test_kunde_ohne_zugferd_bekommt_keine_xml(db):
    reader = _pdf(db, _rechnung(db, zugferd_kunde=False, eingabemodus="netto"))
    assert "xrechnung.xml" not in reader.attachments
