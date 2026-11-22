"""
Issue #568 Stufe 2: mehrere Belege je Journalbuchung (Tabelle journal_anhaenge, Migration 197).
- im Korrekturfenster anhängen und einzeln entfernen, danach gesperrt (API + GoBD-Trigger)
- Buchungsvorlage: eigener Beleg UND Vertrag
- Split-Buchung: alle vorab hochgeladenen Belege an jeder Position
- Korrektur per Storno/Neubuchung: alle Belege wandern mit
- DATEV: mehrere Belege → ein zusammengeführtes PDF
- Migration 197 übernimmt beleg_id als ersten Anhang
"""
import asyncio
import io
import zipfile
from datetime import date, datetime, timedelta
from decimal import Decimal

import fitz
import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import Headers

import api.buchungsvorlagen as bv_mod
import api.datev as datev_mod
import api.journal as journal_mod
import api.rechnungen as rechnungen_mod
import main
from api.buchungsvorlagen import BuchenRequest, buche_vorlage
from api.journal import delete_einzelanhang, update_eintrag, upload_anhang
from api.schemas import JournalEintragCreate, JournalEintragResponse
from database.connection import Base
from database.models import Beleg, Buchungsvorlage, Journaleintrag, JournalAnhang, Unternehmen


def _pdf(text_: str) -> bytes:
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), text_)
    daten = doc.tobytes()
    doc.close()
    return daten


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    belege = tmp_path / "uploads" / "belege"
    for mod in (bv_mod, journal_mod, rechnungen_mod, datev_mod):
        monkeypatch.setattr(mod, "BELEG_DIR", belege, raising=False)
        monkeypatch.setattr(mod, "APP_DATA_DIR", tmp_path, raising=False)
    monkeypatch.setattr(journal_mod, "konvertiere_zu_pdfa", lambda *a, **k: None)
    monkeypatch.setattr("threading.Thread", type("T", (), {"__init__": lambda s, *a, **k: None, "start": lambda s: None}))
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    main_engine = main.engine
    main.engine = engine
    main._setup_gobd_triggers()
    main.engine = main_engine
    db = sessionmaker(bind=engine)()
    db.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O", kontenrahmen="SKR03",
                       geschaeftsjahr_beginn=1, datev_beraternummer="1", datev_mandantennummer="1",
                       datev_konto_bank="1200"))
    db.commit()
    yield db, tmp_path
    db.close()


def _hochladen(db, eintrag_id, name):
    datei = UploadFile(file=io.BytesIO(_pdf(name)), filename=name, headers=Headers({"content-type": "application/pdf"}))
    return asyncio.run(upload_anhang(eintrag_id, datei, db))


def _buchung(db, **kw) -> Journaleintrag:
    e = Journaleintrag(datum=date(2026, 11, 1), belegnr=kw.pop("belegnr", "J-1"), beschreibung="Miete",
                       zahlungsart="Bank", art="Ausgabe", netto_betrag=Decimal("100"), ust_satz=Decimal("0"),
                       ust_betrag=Decimal("0"), brutto_betrag=Decimal("100"), konto_skr03="4210", **kw)
    db.add(e)
    db.commit()
    return e


def test_mehrere_anhaengen_einzeln_entfernen_dann_gesperrt(umgebung):
    db, _ = umgebung
    e = _buchung(db, immutable=False)
    b1 = _hochladen(db, e.id, "vertrag.pdf")
    _hochladen(db, e.id, "abrechnung.pdf")
    db.refresh(e)
    resp = JournalEintragResponse.from_orm_with_kunde(e)
    assert [a.original_name for a in resp.belege_anhaenge] == ["vertrag.pdf", "abrechnung.pdf"]
    assert e.beleg_id == b1.id

    delete_einzelanhang(e.id, resp.belege_anhaenge[0].anhang_id, db)
    db.refresh(e)
    assert [a.beleg.original_name for a in e.anhaenge] == ["abrechnung.pdf"]
    assert e.beleg.original_name == "abrechnung.pdf"   # Hauptbeleg rückt nach

    e.immutable = True
    db.commit()
    with pytest.raises(HTTPException) as exc:
        _hochladen(db, e.id, "spaet.pdf")
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException):
        delete_einzelanhang(e.id, e.anhaenge[0].id, db)
    # GoBD-Trigger auch direkt auf Datenbankebene
    with pytest.raises(Exception):
        db.execute(text("DELETE FROM journal_anhaenge WHERE journal_id = :i"), {"i": e.id})
        db.commit()
    db.rollback()


def test_vorlage_haengt_eigenen_beleg_und_vertrag_an(umgebung):
    db, tmp_path = umgebung
    belege = tmp_path / "uploads" / "belege"
    belege.mkdir(parents=True, exist_ok=True)
    (belege / "vertrag.pdf").write_bytes(_pdf("Vertrag"))
    vertrag = Beleg(dateiname="vertrag.pdf", original_name="Vertrag.pdf", mime_type="application/pdf", dateigroesse=1)
    eigen = Beleg(dateiname="belege/eigen.pdf", original_name="Abrechnung.pdf", mime_type="application/pdf", dateigroesse=1)
    db.add_all([vertrag, eigen])
    db.flush()
    v = Buchungsvorlage(bezeichnung="Miete", betrag=Decimal("100"), ist_brutto=True, ust_satz=Decimal("0"),
                        intervall="monatlich", naechstes_datum=date(2026, 11, 1), modus="direkt", art="Ausgabe",
                        beleg_id=vertrag.id)
    db.add(v)
    db.commit()
    resp = buche_vorlage(v.id, data=BuchenRequest(beleg_ids=[eigen.id]), db=db)
    assert [a.original_name for a in resp.belege_anhaenge] == ["Abrechnung.pdf", "Vertrag.pdf"]
    assert resp.beleg_id == eigen.id


def test_korrektur_uebernimmt_alle_belege(umgebung):
    db, _ = umgebung
    e = _buchung(db, immutable=False)
    _hochladen(db, e.id, "a.pdf")
    _hochladen(db, e.id, "b.pdf")
    e.erstellt_am = datetime.utcnow() - timedelta(minutes=10)
    db.commit()
    data = JournalEintragCreate(datum=e.datum, beschreibung="Miete korrigiert", zahlungsart="Bank", art="Ausgabe",
                                brutto_betrag=Decimal("110"))
    neu = update_eintrag(e.id, data, db)
    assert [a.original_name for a in neu.belege_anhaenge] == ["a.pdf", "b.pdf"]


def test_datev_fuehrt_mehrere_belege_zu_einem_pdf_zusammen(umgebung):
    db, _ = umgebung
    e = _buchung(db, immutable=False)
    _hochladen(db, e.id, "a.pdf")
    _hochladen(db, e.id, "b.pdf")
    resp = datev_mod.datev_buchungsstapel(von=date(2026, 11, 1), bis=date(2026, 11, 30), mit_belegen=True, db=db)
    body = asyncio.run(_body(resp))
    with zipfile.ZipFile(io.BytesIO(body)) as zf:
        assert "J-1.pdf" in zf.namelist()
        with fitz.open("pdf", zf.read("J-1.pdf")) as doc:
            assert doc.page_count == 2


async def _body(response) -> bytes:
    return b"".join([c async for c in response.body_iterator])


def test_migration_197_uebernimmt_beleg_id(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.db'}")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as s:
        b = Beleg(dateiname="x.pdf", original_name="x.pdf", mime_type="application/pdf", dateigroesse=1)
        s.add(b)
        s.flush()
        s.add(Journaleintrag(datum=date(2026, 1, 1), belegnr="J-1", beschreibung="x", zahlungsart="Bar", art="Ausgabe",
                             netto_betrag=Decimal("1"), brutto_betrag=Decimal("1"), beleg_id=b.id, immutable=True))
        s.commit()
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE journal_anhaenge"))
        conn.execute(text("PRAGMA user_version = 196"))
    monkeypatch.setattr(main, "engine", engine)
    main._run_migrations()
    main._run_migrations()  # idempotent
    with engine.begin() as conn:
        assert conn.execute(text("SELECT journal_id, beleg_id FROM journal_anhaenge")).fetchall() == [(1, 1)]
