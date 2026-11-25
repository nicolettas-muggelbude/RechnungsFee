"""
Issue #594: Leistungsdatum je Position (Sammelrechnung). rechnungspositionen.leistungsdatum,
Schalter unternehmen.pdf_positionsdatum (Migration 199). Die Spalten „Pos.“ und „Datum“ hängen in
beiden Vorlagen an den Schaltern; Snapshots von vor #594 behalten das alte Bild.
"""
import json
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from pypdf import PdfReader
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import main
from api.rechnungen import (
    _absender_snapshot, _kopiere_positionen, create_rechnung, rechnung_als_pdf, update_rechnung,
)
from api.schemas_rechnungen import RechnungCreate, RechnungUpdate, RechnungspositionCreate
from database.connection import Base
from database.models import Kunde, Rechnung, Unternehmen
from utils.zugferd import generate_zugferd_xml

TAGE = [date(2026, 11, 3), date(2026, 11, 17), None]


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345",
                            ort="Testort", ist_kleinunternehmer=False))
    session.add(Kunde(firmenname="Kunde AG", strasse="Weg", hausnummer="2", plz="54321", ort="Stadt"))
    session.commit()
    yield session
    session.close()


def _positionen(tage=TAGE):
    return [RechnungspositionCreate(beschreibung=f"Einsatz {i}", netto=Decimal("100"), ust_satz=Decimal("19"),
                                    leistungsdatum=t)
            for i, t in enumerate(tage, start=1)]


def _rechnung(db, **kw):
    return create_rechnung(RechnungCreate(
        typ="ausgang", datum=date(2026, 11, 20), kunde_id=db.query(Kunde).one().id,
        positionen=_positionen(), **kw,
    ), db)


def _schalter(db, pos: bool, datum: bool):
    u = db.query(Unternehmen).one()
    u.pdf_positionsnummern, u.pdf_positionsdatum = pos, datum
    db.commit()


def _text(db, rechnung_id: int, vorlage: int) -> str:
    pdf = rechnung_als_pdf(rechnung_id, vorlage=vorlage, nur_ansehen=True, db=db).body
    return "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)


def _tabelle(t: str) -> tuple[str, list[str]]:
    """Kopfzeile der Positionstabelle und die Positionszeilen (ohne Leistungszeitraum im Kopf)."""
    zeilen = t.splitlines()
    kopf = next(z for z in zeilen if "Beschreibung" in z)
    return kopf, [z for z in zeilen if "Einsatz" in z]


# --- Speichern und Leistungszeitraum ----------------------------------------

def test_positionsdatum_gespeichert_und_zeitraum_vorgeschlagen(db):
    r = _rechnung(db)
    assert [p.leistungsdatum for p in r.positionen] == TAGE
    assert (r.leistung_von, r.leistung_bis) == (date(2026, 11, 3), date(2026, 11, 17))


def test_eingetragener_zeitraum_bleibt(db):
    r = _rechnung(db, leistung_von=date(2026, 11, 1), leistung_bis=date(2026, 11, 30))
    assert (r.leistung_von, r.leistung_bis) == (date(2026, 11, 1), date(2026, 11, 30))


def test_ein_tag_ergibt_leistungsdatum_ohne_ende(db):
    r = create_rechnung(RechnungCreate(
        typ="ausgang", datum=date(2026, 11, 20), kunde_id=db.query(Kunde).one().id,
        positionen=_positionen([date(2026, 11, 5), None]),
    ), db)
    assert (r.leistung_von, r.leistung_bis) == (date(2026, 11, 5), None)


def test_aendern_uebernimmt_datum(db):
    r = _rechnung(db)
    neu = update_rechnung(r.id, RechnungUpdate(positionen=_positionen([date(2026, 11, 20)])), db)
    assert [p.leistungsdatum for p in neu.positionen] == [date(2026, 11, 20)]


def test_umwandlung_kopiert_datum(db):
    quelle = db.query(Rechnung).filter(Rechnung.id == _rechnung(db).id).one()
    ziel = Rechnung(typ="ausgang", datum=date(2026, 12, 1), dokument_typ="Rechnung",
                    netto_gesamt=0, ust_gesamt=0, brutto_gesamt=0)
    db.add(ziel)
    db.flush()
    _kopiere_positionen(quelle, ziel, db)
    db.flush()
    db.refresh(ziel)
    assert [p.leistungsdatum for p in sorted(ziel.positionen, key=lambda p: p.position_nr)] == TAGE


# --- PDF -------------------------------------------------------------------

@pytest.mark.parametrize("vorlage", [0, 1])
def test_schalter_aus_keine_spalten(db, vorlage):
    _schalter(db, False, False)
    kopf, zeilen = _tabelle(_text(db, _rechnung(db).id, vorlage))
    assert "Pos." not in kopf and "Datum" not in kopf
    assert not any(".11.2026" in z for z in zeilen)


@pytest.mark.parametrize("vorlage", [0, 1])
def test_datum_je_position(db, vorlage):
    _schalter(db, True, True)
    t = _text(db, _rechnung(db).id, vorlage)
    kopf, zeilen = _tabelle(t)
    assert "Pos." in kopf and "Datum" in kopf
    assert "03.11.2026" in zeilen[0] and "17.11.2026" in zeilen[1]
    # Position ohne eigenes Datum: Leistungsbeginn der Rechnung (hier aus den Positionen)
    assert "03.11.2026" in zeilen[2]
    assert "357,00" in t


@pytest.mark.parametrize("vorlage", [0, 1])
def test_nur_datum_ohne_pos(db, vorlage):
    _schalter(db, False, True)
    kopf, zeilen = _tabelle(_text(db, _rechnung(db).id, vorlage))
    assert "Pos." not in kopf and "Datum" in kopf and "17.11.2026" in zeilen[1]


@pytest.mark.parametrize("vorlage", [0, 1])
def test_alter_snapshot_behaelt_bild(db, vorlage):
    """Vor #594 finalisiert: Sandra grün zeigt Pos. und Datum immer, die Standardvorlage kein Datum."""
    _schalter(db, False, False)
    r = _rechnung(db, ist_entwurf=False)
    alt = json.loads(_absender_snapshot(db))
    del alt["pdf_positionsdatum"]
    db.query(Rechnung).filter(Rechnung.id == r.id).one().absender_snapshot = json.dumps(alt)
    _schalter(db, True, True)  # aktuelle Stammdaten dürfen das alte Dokument nicht ändern
    kopf, zeilen = _tabelle(_text(db, r.id, vorlage))
    if vorlage == 1:
        assert "Pos." in kopf and "Datum" in kopf and len(zeilen) == 3
    else:
        assert "Pos." not in kopf and "Datum" not in kopf


def test_snapshot_friert_schalter_ein(db):
    _schalter(db, False, True)
    assert json.loads(_absender_snapshot(db))["pdf_positionsdatum"] is True


# --- E-Rechnung ------------------------------------------------------------

UNT = {"firmenname": "Test GmbH", "strasse": "Teststr.", "hausnummer": "1", "plz": "12345", "ort": "Testort",
       "land": "DE", "steuernummer": "12/345/67890", "ust_idnr": "", "ist_kleinunternehmer": False}


def test_xml_zeilenzeitraum(db):
    r = db.query(Rechnung).filter(Rechnung.id == _rechnung(db).id).one()
    xml = generate_zugferd_xml(r, UNT).decode("utf-8")
    zeilen = xml.split("<ram:IncludedSupplyChainTradeLineItem>")[1:]
    assert len(zeilen) == 3
    assert zeilen[0].count("20261103") == 2 and "BillingSpecifiedPeriod" in zeilen[0]
    assert zeilen[1].count("20261117") == 2
    assert "BillingSpecifiedPeriod" not in zeilen[2].split("</ram:IncludedSupplyChainTradeLineItem>")[0]
    from facturx import xml_check_xsd
    assert xml_check_xsd(xml.encode("utf-8"), flavor="factur-x", level="extended")


# --- Migration -------------------------------------------------------------

@pytest.mark.parametrize("vorlage,erwartet", [(0, (0, 0)), (1, (1, 1))])
def test_migration_199(tmp_path, monkeypatch, vorlage, erwartet):
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.db'}")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as s:
        s.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O",
                          pdf_vorlage=vorlage))
        s.commit()
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE rechnungspositionen DROP COLUMN leistungsdatum"))
        conn.execute(text("ALTER TABLE unternehmen DROP COLUMN pdf_positionsdatum"))
        conn.execute(text("PRAGMA user_version = 198"))
    monkeypatch.setattr(main, "engine", engine)
    main._run_migrations()
    with engine.begin() as conn:
        assert "leistungsdatum" in {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungspositionen)"))}
        assert tuple(conn.execute(text(
            "SELECT pdf_positionsnummern, pdf_positionsdatum FROM unternehmen")).one()) == erwartet
        assert conn.execute(text("PRAGMA user_version")).scalar() == main.SCHEMA_VERSION
        conn.execute(text("PRAGMA user_version = 198"))
    main._run_migrations()  # zweiter Lauf ändert nichts
