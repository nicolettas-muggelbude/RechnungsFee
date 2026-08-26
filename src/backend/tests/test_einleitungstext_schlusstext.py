"""
Tests für Issue #368 (Einleitungs-/Schlusstext je Dokumenttyp):
- Migration 151 legt alle neuen Spalten an (unternehmen: schlusstext + 4x Einleitung/Schluss
  je optionalem Dokumenttyp, rechnungen: schlusstext).
- Bestandsfehler behoben: einleitungstext wurde beim Bearbeiten eines Entwurfs bisher nie
  gespeichert (RechnungUpdate-Schema/update_rechnung() kannten das Feld nicht).
- schlusstext ist von Anfang an korrekt verdrahtet (Anlegen, Bearbeiten inkl. bewusstem
  Leeren, Auftrag-Sonderpfad).
- _standardtext() löst pro Dokumenttyp das richtige Unternehmen-Feld auf, ohne
  Cross-Fallback auf den Rechnung-Text.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import main
from api.rechnungen import auftrag_erstellen, create_rechnung, update_rechnung
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate, RechnungUpdate
from database.connection import Base
from database.models import Rechnung, Unternehmen
from utils.pdf_rechnung_base import _standardtext


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    session.commit()
    yield session
    session.close()


def _position(netto="100.00", satz="19"):
    return RechnungspositionCreate(beschreibung="Beratung", menge=Decimal("1"), einheit="Stk.", netto=netto, ust_satz=satz)


def test_migration_151_ergaenzt_alle_neuen_spalten(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("PRAGMA user_version = 150"))

    monkeypatch.setattr(main, "engine", engine)
    main._run_migrations()

    with engine.connect() as conn:
        cols_unt = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
        cols_re = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
        version = conn.execute(text("PRAGMA user_version")).scalar()

    assert version == main.SCHEMA_VERSION
    for spalte in (
        "schlusstext", "einleitungstext_angebot", "schlusstext_angebot",
        "einleitungstext_auftrag", "schlusstext_auftrag",
        "einleitungstext_proforma", "schlusstext_proforma",
        "einleitungstext_lieferschein", "schlusstext_lieferschein",
    ):
        assert spalte in cols_unt, f"unternehmen.{spalte} fehlt"
    assert "schlusstext" in cols_re


def test_create_rechnung_speichert_einleitungs_und_schlusstext(db):
    payload = RechnungCreate(
        typ="ausgang", datum=date(2026, 1, 5), partner_freitext="Testkunde",
        einleitungstext="Hallo Einleitung", schlusstext="Tschüss Schluss",
        positionen=[_position()],
    )
    resp = create_rechnung(payload, db)
    assert resp.einleitungstext == "Hallo Einleitung"
    assert resp.schlusstext == "Tschüss Schluss"


def test_update_rechnung_speichert_geaenderten_einleitungstext(db):
    """Bugfix-Nachweis: vorher wurde ein bearbeiteter Einleitungstext an einem bestehenden
    Entwurf nie gespeichert."""
    payload = RechnungCreate(
        typ="ausgang", datum=date(2026, 1, 5), partner_freitext="Testkunde",
        einleitungstext="Alt", positionen=[_position()],
    )
    resp = create_rechnung(payload, db)

    update_rechnung(resp.id, RechnungUpdate(einleitungstext="Neu"), db)

    rechnung = db.query(Rechnung).filter(Rechnung.id == resp.id).first()
    assert rechnung.einleitungstext == "Neu"


def test_update_rechnung_kann_einleitungstext_bewusst_leeren(db):
    payload = RechnungCreate(
        typ="ausgang", datum=date(2026, 1, 5), partner_freitext="Testkunde",
        einleitungstext="Text da", schlusstext="Auch da", positionen=[_position()],
    )
    resp = create_rechnung(payload, db)

    update_rechnung(resp.id, RechnungUpdate(einleitungstext=None, schlusstext=None), db)

    rechnung = db.query(Rechnung).filter(Rechnung.id == resp.id).first()
    assert rechnung.einleitungstext is None
    assert rechnung.schlusstext is None


def test_update_rechnung_ohne_feld_im_request_laesst_text_unangetastet(db):
    """model_fields_set-Logik: ein Update OHNE einleitungstext/schlusstext im Request darf
    einen bestehenden Text nicht versehentlich löschen."""
    payload = RechnungCreate(
        typ="ausgang", datum=date(2026, 1, 5), partner_freitext="Testkunde",
        einleitungstext="Bleibt stehen", positionen=[_position()],
    )
    resp = create_rechnung(payload, db)

    update_rechnung(resp.id, RechnungUpdate(notizen="Nur Notizen geändert"), db)

    rechnung = db.query(Rechnung).filter(Rechnung.id == resp.id).first()
    assert rechnung.einleitungstext == "Bleibt stehen"


def test_auftrag_erstellen_uebernimmt_einleitungs_und_schlusstext(db):
    """Bugfix-Nachweis: auftrag_erstellen() hat einleitungstext bisher komplett ignoriert -
    schlusstext ist von Anfang an korrekt verdrahtet."""
    payload = RechnungCreate(
        typ="ausgang", datum=date(2026, 1, 5), partner_freitext="Testkunde",
        einleitungstext="Auftrags-Einleitung", schlusstext="Auftrags-Schluss",
        positionen=[_position()],
    )
    resp = auftrag_erstellen(payload, db)

    assert resp.einleitungstext == "Auftrags-Einleitung"
    assert resp.schlusstext == "Auftrags-Schluss"
    assert resp.dokument_typ == "Auftrag"


class TestStandardtext:
    def test_rechnung_nutzt_unpraefigiertes_feld(self):
        unt = {"einleitungstext": "Rechnungstext", "einleitungstext_angebot": "Angebotstext"}
        assert _standardtext(unt, "einleitungstext", "Rechnung") == "Rechnungstext"
        assert _standardtext(unt, "einleitungstext", "Gutschrift") == "Rechnungstext"

    def test_angebot_nutzt_eigenes_feld(self):
        unt = {"einleitungstext": "Rechnungstext", "einleitungstext_angebot": "Angebotstext"}
        assert _standardtext(unt, "einleitungstext", "Angebot") == "Angebotstext"

    def test_kein_cross_fallback_wenn_typspezifisches_feld_leer(self):
        """Kernpunkt aus Issue #368: ein leeres Angebot-Feld darf NICHT den Rechnungstext
        übernehmen, sonst wäre das Problem nicht gelöst."""
        unt = {"einleitungstext": "Rechnungstext", "einleitungstext_angebot": None}
        assert _standardtext(unt, "einleitungstext", "Angebot") == ""

    def test_schlusstext_funktioniert_identisch(self):
        unt = {"schlusstext": "R", "schlusstext_lieferschein": "L"}
        assert _standardtext(unt, "schlusstext", "Lieferschein") == "L"
        assert _standardtext(unt, "schlusstext", "Rechnung") == "R"
