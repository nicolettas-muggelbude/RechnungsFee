"""
Issue #474: eigene Bemerkung für die E-Rechnung (BT-22).

Opt-in über unternehmen.bt22_bemerkung_aktiv. Ist rechnungen.bemerkung_erechnung gefüllt,
steht nur dieser Text in BT-22 und die Notizen bleiben reiner PDF-Fußtext; ist es leer,
gehen wie bisher die Notizen in BT-22. Der Text steht auch im PDF und wandert bei jeder
Dokumentumwandlung mit.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfReader
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import main
from api.rechnungen import (
    auftrag_aus_angebot,
    create_rechnung,
    rechnung_als_pdf,
    rechnung_aus_auftrag,
    update_rechnung,
)
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate, RechnungUpdate
from database.connection import Base
from database.models import Rechnung, Unternehmen
from utils.zugferd import generate_zugferd_xml

UNTERNEHMEN = {
    "firmenname": "Testfirma GmbH",
    "strasse": "Teststraße", "hausnummer": "1", "plz": "12345", "ort": "Teststadt",
    "land": "DE", "steuernummer": "12/345/67890", "ust_idnr": "",
    "ist_kleinunternehmer": False,
}


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(
        firmenname="Testfirma GmbH", strasse="Teststraße", hausnummer="1",
        plz="12345", ort="Teststadt", steuernummer="12/345/67890",
    ))
    session.commit()
    yield session
    session.close()


def _daten(**kwargs) -> RechnungCreate:
    defaults = dict(
        typ="ausgang", dokument_typ="Rechnung", datum=date(2026, 10, 29), ist_entwurf=True,
        partner_freitext="Testkunde GmbH",
        notizen="Vielen Dank für den Auftrag!",
        bemerkung_erechnung="Projekt 4711 / Kostenstelle 12",
        positionen=[RechnungspositionCreate(beschreibung="Beratung", menge=Decimal("1"),
                                            netto=Decimal("100.00"), ust_satz=Decimal("19"))],
    )
    defaults.update(kwargs)
    return RechnungCreate(**defaults)


def _xml(db, rechnung_id: int) -> str:
    r = db.query(Rechnung).filter(Rechnung.id == rechnung_id).one()
    return generate_zugferd_xml(r, UNTERNEHMEN).decode("utf-8")


def test_standard_aus():
    assert Unternehmen().bt22_bemerkung_aktiv in (None, False)


def test_bemerkung_hat_vorrang_vor_notizen(db):
    xml = _xml(db, create_rechnung(_daten(), db).id)
    assert "Projekt 4711 / Kostenstelle 12" in xml
    assert "Vielen Dank für den Auftrag!" not in xml
    assert xml.count("<ram:IncludedNote>") == 1


def test_ohne_bemerkung_bisheriges_verhalten(db):
    xml = _xml(db, create_rechnung(_daten(bemerkung_erechnung=None), db).id)
    assert "Vielen Dank für den Auftrag!" in xml


def test_nur_leerzeichen_zaehlt_als_leer(db):
    resp = create_rechnung(_daten(bemerkung_erechnung="   "), db)
    assert resp.bemerkung_erechnung is None
    assert "Vielen Dank für den Auftrag!" in _xml(db, resp.id)


def test_aendern_und_wieder_leeren(db):
    resp = create_rechnung(_daten(), db)
    assert update_rechnung(resp.id, RechnungUpdate(bemerkung_erechnung="Neu"), db).bemerkung_erechnung == "Neu"
    # explizit null -> geleert; weggelassen -> unverändert
    assert update_rechnung(resp.id, RechnungUpdate(bemerkung_erechnung=None), db).bemerkung_erechnung is None
    update_rechnung(resp.id, RechnungUpdate(bemerkung_erechnung="Wieder da"), db)
    assert update_rechnung(resp.id, RechnungUpdate(notizen="x"), db).bemerkung_erechnung == "Wieder da"


def test_wandert_angebot_auftrag_rechnung(db):
    angebot = create_rechnung(_daten(dokument_typ="Angebot", ist_entwurf=False), db)
    auftrag = auftrag_aus_angebot(angebot.id, db)
    assert auftrag.bemerkung_erechnung == "Projekt 4711 / Kostenstelle 12"
    assert rechnung_aus_auftrag(auftrag.id, db).bemerkung_erechnung == "Projekt 4711 / Kostenstelle 12"


@pytest.mark.parametrize("vorlage", [0, 1])
def test_steht_im_pdf(db, vorlage):
    resp = create_rechnung(_daten(), db)
    pdf = rechnung_als_pdf(resp.id, vorlage=vorlage, nur_ansehen=True, db=db).body
    inhalt = "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
    assert "Projekt 4711 / Kostenstelle 12" in inhalt
    assert "Vielen Dank für den Auftrag!" in inhalt  # Notizen bleiben Fußtext


def test_migration_177_bestehende_db(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "alt.db"
    eng = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(main, "engine", eng)
    monkeypatch.setattr(main, "DB_PATH", db_path)
    Base.metadata.create_all(bind=eng)
    with eng.connect() as con:
        con.execute(text("ALTER TABLE unternehmen DROP COLUMN bt22_bemerkung_aktiv"))
        con.execute(text("ALTER TABLE rechnungen DROP COLUMN bemerkung_erechnung"))
        con.execute(text("PRAGMA user_version = 176"))
        con.commit()

    main._run_migrations()

    with eng.connect() as con:
        u = {r[1] for r in con.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
        r = {r[1] for r in con.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
        assert con.execute(text("PRAGMA user_version")).scalar() >= 177
    assert "bt22_bemerkung_aktiv" in u
    assert "bemerkung_erechnung" in r
