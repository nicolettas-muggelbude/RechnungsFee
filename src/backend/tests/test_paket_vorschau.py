"""
Issue #477 Punkt 2: Vorschau „Paket ansehen" – alle Dateien eines Dokumentenpakets
(PDF und Bilder) in Paket-Reihenfolge zu einem einzigen PDF zusammengefügt.
"""
import io

import fitz
import pytest
from fastapi import HTTPException
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api.dokumentenpakete as dp
from database.connection import Base
from database.models import Beleg, DokumentenPaket, DokumentenPaketBeleg


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(dp, "APP_DATA_DIR", tmp_path)
    (tmp_path / "uploads").mkdir()
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _pdf(seiten: int, text: str) -> bytes:
    doc = fitz.open()
    for i in range(seiten):
        doc.new_page().insert_text((72, 72), f"{text} {i + 1}")
    daten = doc.tobytes()
    doc.close()
    return daten


def _png() -> bytes:
    puffer = io.BytesIO()
    Image.new("RGB", (200, 100), "red").save(puffer, format="PNG")
    return puffer.getvalue()


def _datei(db, tmp_path, paket, name, inhalt, mime, sort):
    (tmp_path / "uploads" / name).write_bytes(inhalt)
    beleg = Beleg(dateiname=name, original_name=name, mime_type=mime, dateigroesse=len(inhalt), sha256=name)
    db.add(beleg)
    db.flush()
    db.add(DokumentenPaketBeleg(paket_id=paket.id, beleg_id=beleg.id, sort_order=sort))


def test_pdfs_und_bild_in_paketreihenfolge(db, tmp_path):
    paket = DokumentenPaket(name="B2B")
    db.add(paket)
    db.flush()
    # Reihenfolge absichtlich anders als die Anlage-Reihenfolge
    _datei(db, tmp_path, paket, "agb.pdf", _pdf(2, "AGB"), "application/pdf", 1)
    _datei(db, tmp_path, paket, "dse.pdf", _pdf(1, "DSE"), "application/pdf", 0)
    _datei(db, tmp_path, paket, "plan.png", _png(), "image/png", 2)
    db.commit()
    db.refresh(paket)

    with fitz.open("pdf", dp.paket_als_pdf(paket)) as erg:
        assert erg.page_count == 4
        assert "DSE 1" in erg[0].get_text()
        assert "AGB 1" in erg[1].get_text()
        assert "AGB 2" in erg[2].get_text()
        assert erg[3].get_images()  # Bildseite


def test_fehlende_datei_wird_uebersprungen(db, tmp_path):
    paket = DokumentenPaket(name="Rest")
    db.add(paket)
    db.flush()
    _datei(db, tmp_path, paket, "da.pdf", _pdf(1, "Da"), "application/pdf", 0)
    db.add(Beleg(dateiname="weg.pdf", original_name="weg.pdf", mime_type="application/pdf", sha256="x"))
    db.flush()
    weg = db.query(Beleg).filter(Beleg.dateiname == "weg.pdf").one()
    db.add(DokumentenPaketBeleg(paket_id=paket.id, beleg_id=weg.id, sort_order=1))
    db.commit()
    db.refresh(paket)

    with fitz.open("pdf", dp.paket_als_pdf(paket)) as erg:
        assert erg.page_count == 1


def test_leeres_paket_404(db):
    paket = DokumentenPaket(name="Leer")
    db.add(paket)
    db.commit()
    with pytest.raises(HTTPException) as e:
        dp.paket_als_pdf(paket)
    assert e.value.status_code == 404


def test_endpunkt_inline_mit_dateiname(db, tmp_path):
    paket = DokumentenPaket(name="Privat & Co")
    db.add(paket)
    db.flush()
    _datei(db, tmp_path, paket, "a.pdf", _pdf(1, "A"), "application/pdf", 0)
    db.commit()

    antwort = dp.paket_vorschau(paket.id, db)
    assert antwort.media_type == "application/pdf"
    cd = antwort.headers["content-disposition"]
    assert cd.startswith("inline;")
    assert "Dokumentenpaket_Privat" in cd
