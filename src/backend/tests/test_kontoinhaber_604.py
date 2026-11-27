"""
Issue #604: Kontoinhaber je Konto (Einstellungen → Konten) als Empfänger im QR-Code und in der
E-Rechnung (BT-85). Hintergrund ist die Empfängerüberprüfung der Banken: Ein Einzelunternehmer mit
Firmenname, dessen Konto auf seinen eigenen Namen läuft, bekam bisher immer den Firmennamen in den
QR-Code. Leer = bisheriges Verhalten (Firmenname, sonst Vor- und Nachname).
"""
import json
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import main
import utils.pdf_mahnung as pdf_mahnung_mod
import utils.pdf_rechnung as pdf_rechnung_mod
import utils.pdf_rechnung_vorlage1 as pdf_vorlage1_mod
from api.konten import update_konto
from api.rechnungen import create_rechnung, finalisiere_rechnung
from api.schemas import KontoCreate, KontoUpdate
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate
from database.connection import Base
from database.models import Konto, Kunde, Rechnung, Unternehmen
from utils.kontoinhaber import (
    abweichender_kontoinhaber, kontoinhaber_fuer_iban, zahlungsempfaenger,
)
from utils.zugferd import generate_zugferd_xml

IBAN = "DE89370400440532013000"


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(
        firmenname="Schmidt Webdesign", vorname="André", nachname="Schmidt",
        strasse="Weg", hausnummer="1", plz="12345", ort="Ort", ist_kleinunternehmer=True,
        iban="DE89 3704 0044 0532 0130 00", bic="COBADEFFXXX",
        qr_zahlung_aktiv=True, zahlungshinweis_aktiv=True,
    ))
    session.commit()
    yield session
    session.close()


def _konto(db, inhaber=None):
    k = Konto(name="Giro", anbieter="Bank", kontoart="bank", iban=IBAN, kontoinhaber=inhaber)
    db.add(k)
    db.commit()
    return k


def _finale_rechnung(db) -> Rechnung:
    kunde = Kunde(firmenname="Kunde GmbH", strasse="S", hausnummer="2", plz="10115", ort="Berlin",
                  land="DE", kundennummer="K-1")
    db.add(kunde)
    db.commit()
    r = create_rechnung(RechnungCreate(
        typ="ausgang", datum=date(2026, 11, 27), kunde_id=kunde.id,
        positionen=[RechnungspositionCreate(beschreibung="Webseite", netto=Decimal("500"), ust_satz=Decimal("0"))],
    ), db)
    finalisiere_rechnung(r.id, db)
    return db.query(Rechnung).filter(Rechnung.id == r.id).one()


# ── Helfer ──────────────────────────────────────────────────────────────────

def test_empfaenger_standard_und_gepflegt():
    unt = {"firmenname": "Schmidt Webdesign", "vorname": "André", "nachname": "Schmidt"}
    assert zahlungsempfaenger(unt) == "Schmidt Webdesign"                       # ohne Schlüssel (Alt-Snapshot)
    assert zahlungsempfaenger({**unt, "kontoinhaber": ""}) == "Schmidt Webdesign"
    assert zahlungsempfaenger({**unt, "kontoinhaber": "André Schmidt"}) == "André Schmidt"
    assert zahlungsempfaenger({"vorname": "André", "nachname": "Schmidt"}) == "André Schmidt"
    assert abweichender_kontoinhaber({**unt, "kontoinhaber": "André Schmidt"}) == "André Schmidt"
    assert abweichender_kontoinhaber({**unt, "kontoinhaber": "Schmidt Webdesign"}) == ""


def test_konto_per_iban_auch_mit_leerzeichen(db):
    _konto(db, "André Schmidt")
    assert kontoinhaber_fuer_iban(db, "de89 3704 0044 0532 0130 00") == "André Schmidt"
    assert kontoinhaber_fuer_iban(db, "DE02120300000000202051") == ""


def test_konto_ohne_inhaber_liefert_standard(db):
    _konto(db)
    assert kontoinhaber_fuer_iban(db, IBAN) == ""


# ── Konten-API ──────────────────────────────────────────────────────────────

def test_leerer_inhaber_setzt_zurueck(db):
    k = _konto(db, "André Schmidt")
    update_konto(k.id, KontoUpdate(kontoinhaber=""), db)
    assert db.get(Konto, k.id).kontoinhaber is None


def test_update_ohne_feld_laesst_inhaber_stehen(db):
    k = _konto(db, "André Schmidt")
    update_konto(k.id, KontoUpdate(name="Neu"), db)
    assert db.get(Konto, k.id).kontoinhaber == "André Schmidt"


def test_hoechstens_70_zeichen():
    with pytest.raises(ValueError):
        KontoCreate(name="G", anbieter="B", iban=IBAN, kontoinhaber="x" * 71)


# ── Rechnung: Snapshot, QR-Code, E-Rechnung ─────────────────────────────────

def test_snapshot_friert_inhaber_ein(db):
    k = _konto(db, "André Schmidt")
    r = _finale_rechnung(db)
    assert json.loads(r.absender_snapshot)["kontoinhaber"] == "André Schmidt"
    k.kontoinhaber = "Jemand anders"
    db.commit()
    db.refresh(r)
    assert json.loads(r.absender_snapshot)["kontoinhaber"] == "André Schmidt"


@pytest.mark.parametrize("modul,erzeuge", [
    (pdf_rechnung_mod, "generate_rechnung_pdf"),
    (pdf_vorlage1_mod, "generate_rechnung_pdf_vorlage1"),
])
@pytest.mark.parametrize("inhaber,erwartet", [
    ("André Schmidt", "André Schmidt"),
    (None, "Schmidt Webdesign"),
])
def test_qr_code_empfaenger(db, monkeypatch, modul, erzeuge, inhaber, erwartet):
    _konto(db, inhaber)
    r = _finale_rechnung(db)
    namen = []
    monkeypatch.setattr(modul, "epc_qr_bytes", lambda iban, bic, empf, *a, **kw: namen.append(empf) or None)
    getattr(modul, erzeuge)(r, json.loads(r.absender_snapshot))
    assert namen and set(namen) == {erwartet}


def test_mahnung_qr_code_empfaenger(monkeypatch):
    namen = []
    monkeypatch.setattr(pdf_mahnung_mod, "epc_qr_bytes", lambda iban, bic, empf, *a, **kw: namen.append(empf) or None)
    unt = {"firmenname": "Schmidt Webdesign", "kontoinhaber": "André Schmidt", "iban": IBAN, "qr_zahlung_aktiv": True}
    # nur die Empfängerermittlung des Mahnungs-PDFs: gleiche Funktion wie im Modul
    assert pdf_mahnung_mod.zahlungsempfaenger(unt) == "André Schmidt"


def test_e_rechnung_kontoinhaber_bt85(db):
    _konto(db, "André Schmidt")
    r = _finale_rechnung(db)
    xml = generate_zugferd_xml(r, json.loads(r.absender_snapshot) | {
        "land": "DE", "email": "a@b.de", "telefon": "1", "steuernummer": "12/345/67890"}).decode("utf-8")
    assert "<ram:AccountName>André Schmidt</ram:AccountName>" in xml


def test_e_rechnung_ohne_inhaber_unveraendert(db):
    _konto(db)
    r = _finale_rechnung(db)
    xml = generate_zugferd_xml(r, json.loads(r.absender_snapshot) | {
        "land": "DE", "email": "a@b.de", "telefon": "1", "steuernummer": "12/345/67890"}).decode("utf-8")
    assert "AccountName" not in xml


# ── Migration ───────────────────────────────────────────────────────────────

def test_migration_203(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE konten DROP COLUMN kontoinhaber"))
        conn.execute(text("PRAGMA user_version = 202"))
    monkeypatch.setattr(main, "engine", engine)
    main._run_migrations()
    with engine.begin() as conn:
        spalten = {r[1] for r in conn.execute(text("PRAGMA table_info(konten)"))}
        assert "kontoinhaber" in spalten
        assert conn.execute(text("PRAGMA user_version")).scalar() == main.SCHEMA_VERSION
        conn.execute(text("PRAGMA user_version = 202"))
    main._run_migrations()  # zweiter Lauf ändert nichts
