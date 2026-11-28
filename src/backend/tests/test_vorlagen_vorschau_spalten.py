"""
Vorschau unter Einstellungen → Rechnungsvorlagen: Die Spalten „Art.-Nr.“ (#562), „Pos.“ (#475) und
„Datum“ (#594) erscheinen in beiden Vorlagen, sobald der jeweilige Schalter an ist. Die
Musterrechnung hatte keine Artikel, dadurch fehlte „Art.-Nr.“ in der Vorschau.
"""
from io import BytesIO

import pytest
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.pdf_vorlagen import demo_pdf
from database.connection import Base
from database.models import Unternehmen


def _kopf(db, vorlage: int) -> tuple[str, str]:
    pdf = demo_pdf(vorlage=vorlage, db=db).body
    text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
    return next(z for z in text.splitlines() if "Beschreibung" in z), text


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    s.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O", ist_kleinunternehmer=False))
    s.commit()
    yield s
    s.close()


@pytest.mark.parametrize("vorlage", [0, 1])
def test_alle_schalter_an(db, vorlage):
    u = db.query(Unternehmen).one()
    u.pdf_artikelnummer = u.pdf_positionsnummern = u.pdf_positionsdatum = True
    db.commit()
    kopf, text = _kopf(db, vorlage)
    assert "Art.-Nr." in kopf and "Pos." in kopf and "Datum" in kopf
    assert "WEB-START" in text and "ART-0007" in text
    assert "04.03.2024" in text and "28.03.2024" in text


@pytest.mark.parametrize("vorlage", [0, 1])
def test_alle_schalter_aus(db, vorlage):
    kopf, text = _kopf(db, vorlage)
    assert "Art.-Nr." not in kopf and "Pos." not in kopf and "Datum" not in kopf
    assert "WEB-START" not in text
