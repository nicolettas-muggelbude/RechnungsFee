"""
Issue #591: Eingangsrechnung - kein Rechnungs-PDF mit eigener Firma als Absender und eigenen
Bankdaten, sondern ein internes Erfassungsblatt (Lieferant = Rechnungssteller, eigene Firma =
Empfänger). Ohne Archivierung/„ausgegeben“, kein Mailversand.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from fastapi import HTTPException
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.mail import _pdf_bytes_fuer
from api.rechnungen import rechnung_als_pdf
from database.connection import Base
from database.models import Lieferant, Rechnung, Rechnungsposition, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    s.add(Unternehmen(firmenname="Meine Firma", strasse="Hauptstr.", hausnummer="1", plz="12345", ort="Musterstadt",
                      iban="DE02120300000000202051"))
    lf = Lieferant(firmenname="Holz Müller GmbH", strasse="Waldweg", hausnummer="7", plz="54321", ort="Forst")
    s.add(lf)
    s.flush()
    r = Rechnung(typ="eingang", rechnungsnummer="ER-260001", externe_belegnr="HM-4711", datum=date(2026, 11, 2),
                 lieferant_id=lf.id, netto_gesamt=Decimal("100"), ust_gesamt=Decimal("19"),
                 brutto_gesamt=Decimal("119"), ist_entwurf=False, eingabemodus="netto")
    s.add(r)
    s.flush()
    s.add(Rechnungsposition(rechnung_id=r.id, position_nr=1, beschreibung="Bretter", menge=Decimal("1"),
                            netto=Decimal("100"), ust_satz=Decimal("19"), ust_betrag=Decimal("19"), brutto=Decimal("119")))
    s.commit()
    yield s
    s.close()


def test_erfassungsblatt_statt_rechnungsvorlage(db):
    r = db.query(Rechnung).one()
    resp = rechnung_als_pdf(r.id, db=db)
    text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(resp.body)).pages)
    assert "Erfassungsblatt" in text
    assert text.index("Holz Müller GmbH") < text.index("Meine Firma")   # Lieferant links als Rechnungssteller
    assert "HM-4711" in text and "Bretter" in text and "119,00" in text
    assert "DE02" not in text and "IBAN" not in text                    # keine eigenen Bankdaten
    db.refresh(r)
    assert not r.ausgegeben and not r.original_pdf_pfad                 # nichts archiviert
    assert "inline" in resp.headers["content-disposition"]


def test_kein_mailversand(db):
    with pytest.raises(HTTPException) as exc:
        _pdf_bytes_fuer(db.query(Rechnung).one().id, db)
    assert exc.value.status_code == 409
