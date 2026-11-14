"""
Issue #524: Reihenfolge der Dokumente in einem Dokumentenpaket.

- neue Dokumente landen immer am Ende (vorher len(dateien) → nach einem Löschen doppelte Position)
- bei doppelter Position (Altbestand) entscheidet die Anlage-Reihenfolge
- Reihenfolge per Endpunkt änderbar
"""
import asyncio
import io

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import Headers

import api.dokumentenpakete as dp
from database.connection import Base
from database.models import Beleg, DokumentenPaket, DokumentenPaketBeleg


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(dp, "APP_DATA_DIR", tmp_path)
    monkeypatch.setattr(dp, "BELEG_DIR", tmp_path / "uploads" / "belege")
    (tmp_path / "uploads").mkdir()
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _paket(db):
    p = DokumentenPaket(name="B2B")
    db.add(p)
    db.commit()
    return p


def _hochladen(db, paket_id, name):
    datei = UploadFile(
        file=io.BytesIO(b"%PDF-1.4 " + name.encode()),
        filename=name,
        headers=Headers({"content-type": "application/pdf"}),
    )
    return asyncio.run(dp.upload_datei(paket_id, None, datei, db))


def _namen(antwort):
    return [d.original_name for d in antwort.dateien]


def test_neues_dokument_nach_loeschen_am_ende(db):
    p = _paket(db)
    for n in ("a.pdf", "b.pdf", "c.pdf"):
        antwort = _hochladen(db, p.id, n)
    b = next(d for d in antwort.dateien if d.original_name == "b.pdf")
    dp.delete_datei(p.id, b.id, db)

    antwort = _hochladen(db, p.id, "neu.pdf")
    assert _namen(antwort) == ["a.pdf", "c.pdf", "neu.pdf"]
    assert len({d.sort_order for d in antwort.dateien}) == 3


def test_doppelte_position_altbestand_nach_anlage(db):
    p = _paket(db)
    for name, sort in (("erst.pdf", 1), ("null.pdf", 0), ("zweit.pdf", 1)):
        beleg = Beleg(dateiname=name, original_name=name, mime_type="application/pdf", sha256=name)
        db.add(beleg)
        db.flush()
        db.add(DokumentenPaketBeleg(paket_id=p.id, beleg_id=beleg.id, sort_order=sort))
    db.commit()

    assert _namen(dp.get_paket(p.id, db)) == ["null.pdf", "erst.pdf", "zweit.pdf"]


def test_reihenfolge_aendern(db):
    p = _paket(db)
    for n in ("a.pdf", "b.pdf", "c.pdf"):
        antwort = _hochladen(db, p.id, n)
    ids = [d.id for d in antwort.dateien]

    antwort = dp.update_reihenfolge(p.id, dp.ReihenfolgeUpdate(eintrag_ids=[ids[2], ids[0], ids[1]]), db)
    assert _namen(antwort) == ["c.pdf", "a.pdf", "b.pdf"]
    assert [d.sort_order for d in antwort.dateien] == [0, 1, 2]
    # neues Dokument danach weiterhin am Ende
    assert _namen(_hochladen(db, p.id, "d.pdf"))[-1] == "d.pdf"


def test_reihenfolge_unvollstaendig_abgewiesen(db):
    p = _paket(db)
    for n in ("a.pdf", "b.pdf"):
        antwort = _hochladen(db, p.id, n)
    ids = [d.id for d in antwort.dateien]

    for falsch in ([ids[0]], [ids[0], ids[0]], [ids[0], ids[1], 999]):
        with pytest.raises(HTTPException) as e:
            dp.update_reihenfolge(p.id, dp.ReihenfolgeUpdate(eintrag_ids=falsch), db)
        assert e.value.status_code == 422
