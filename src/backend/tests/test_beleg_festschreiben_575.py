"""
Issue #575: Der Beleg einer finalisierten Rechnung ist der archivierte Originalbeleg (GoBD) -
weder löschen noch ersetzen. Entwürfe bleiben korrigierbar, ein fehlender Beleg darf nachgereicht
werden, Angebot/Auftrag/Proforma sind nicht betroffen. Geteilte Belege bleiben beim Entfernen erhalten.
"""
import asyncio
import io
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import Headers

import api.rechnungen as ar
from database.connection import Base
from database.models import Beleg, Journaleintrag, Rechnung


class _OhneThread:
    def __init__(self, *a, **k):
        pass

    def start(self):
        pass


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(ar, "APP_DATA_DIR", tmp_path)
    monkeypatch.setattr(ar, "BELEG_DIR", tmp_path / "uploads" / "belege")
    monkeypatch.setattr("threading.Thread", _OhneThread)  # keine PDF/A-Konvertierung im Test
    (tmp_path / "uploads").mkdir()
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _rechnung(db, entwurf=False, dokument_typ="Rechnung"):
    r = Rechnung(typ="eingang", rechnungsnummer=f"ER-{dokument_typ}-{entwurf}", datum=date(2026, 11, 1),
                 partner_freitext="Lieferant", netto_gesamt=Decimal("10"), ust_gesamt=Decimal("0"),
                 brutto_gesamt=Decimal("10"), ist_entwurf=entwurf, dokument_typ=dokument_typ)
    db.add(r)
    db.commit()
    return r


def _hochladen(db, rid, name="beleg.png"):
    datei = UploadFile(file=io.BytesIO(b"\x89PNG " + name.encode()), filename=name,
                       headers=Headers({"content-type": "image/png"}))
    return asyncio.run(ar.upload_beleg(rid, datei, db))


def test_finalisiert_nachreichen_ja_loeschen_und_ersetzen_nein(db):
    r = _rechnung(db)
    _hochladen(db, r.id)  # fehlender Beleg darf nachgereicht werden
    db.refresh(r)
    assert r.beleg_id and ar.beleg_festgeschrieben(r)
    with pytest.raises(HTTPException) as e:
        ar.delete_beleg(r.id, db)
    assert e.value.status_code == 409
    with pytest.raises(HTTPException) as e:
        _hochladen(db, r.id, "anderer.png")
    assert e.value.status_code == 409
    assert db.query(Beleg).count() == 1


def test_entwurf_bleibt_korrigierbar(db, tmp_path):
    r = _rechnung(db, entwurf=True)
    _hochladen(db, r.id, "falsch.png")
    _hochladen(db, r.id, "richtig.png")
    db.refresh(r)
    assert r.beleg.original_name == "richtig.png"
    assert db.query(Beleg).count() == 1  # der ersetzte Beleg ist samt Datei weg
    assert [p.name.split("_")[0] for p in (tmp_path / "uploads" / "belege").rglob("*.png")] == ["richtig"]
    ar.delete_beleg(r.id, db)
    assert db.query(Beleg).count() == 0


@pytest.mark.parametrize("typ", ["Angebot", "Auftrag", "Proforma"])
def test_angebot_auftrag_proforma_nicht_betroffen(db, typ):
    r = _rechnung(db, dokument_typ=typ)
    _hochladen(db, r.id)
    _hochladen(db, r.id, "neu.png")
    ar.delete_beleg(r.id, db)


def test_geteilter_beleg_bleibt_erhalten(db):
    r = _rechnung(db, entwurf=True)
    _hochladen(db, r.id)
    db.refresh(r)
    db.add(Journaleintrag(datum=date(2026, 11, 1), belegnr="J-1", beschreibung="x", zahlungsart="Bar",
                          art="Ausgabe", netto_betrag=Decimal("10"), ust_satz=Decimal("0"),
                          ust_betrag=Decimal("0"), brutto_betrag=Decimal("10"), beleg_id=r.beleg_id))
    db.commit()
    ar.delete_beleg(r.id, db)
    assert db.query(Beleg).count() == 1
