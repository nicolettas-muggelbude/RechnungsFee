"""
Issue #492: steuerfreie Leistungen nach § 4 UStG (Heilberufe Nr. 14, Unterricht Nr. 21).

Kennzeichen „steuerfrei_4“ je Rechnung: Positionen 0 %, Pflichthinweis auf der Rechnung, Zahlung
auf „Betriebseinnahmen (0%)“ (EÜR-Basis Zeile 16, bei Kleinunternehmern Zeile 12 + nachrichtlich
13 und nicht im Gesamtumsatz), UStVA Kz 48 bei Regelbesteuerung, E-Rechnung Kategorie E.
"""
import re
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from pydantic import ValidationError
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.euer import _berechne_euer, kleinunternehmer_gesamtumsatz
from api.rechnungen import (
    _absender_snapshot, create_rechnung, finalisiere_rechnung, rechnung_aus_angebot, storno_rechnung,
    zahlung_bar_erstellen,
)
from api.schemas import StornoRequest
from api.schemas_rechnungen import BarZahlungCreate, RechnungCreate, RechnungspositionCreate
from api.ustva import _berechne_kz, jahresumsatzsteuer
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Kunde, Nummernkreis, Rechnung, Unternehmen
from utils.elster import build_ustva_xml
from utils.pdf_rechnung import generate_rechnung_pdf
from utils.pdf_rechnung_vorlage1 import generate_rechnung_pdf_vorlage1
from utils.zugferd import generate_zugferd_xml

import json


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Praxis Muster", strasse="Weg", hausnummer="1", plz="12345", ort="Ort",
                            ist_kleinunternehmer=False, steuerbefreiung_4="4_nr_14", angebote_aktiv=True,
                            steuernummer="12/345/67890"))
    for typ, fmt in [("rechnung_ausgang", "RE-YY####"), ("angebot", "ANG-YY####"),
                     ("journal", "YY####"), ("stornorechnung", "STORNO-YY####")]:
        session.add(Nummernkreis(bezeichnung=typ, typ=typ, format=fmt, naechste_nr=1, reset_jaehrlich=True, aktiv=True))
    session.add_all([
        Kategorie(name="Betriebseinnahmen", kontenart="Erlös", euer_zeile=15, konto_skr03="8400", konto_skr04="4400",
                  ust_satz_standard=19),
        Kategorie(name="Betriebseinnahmen (0%)", kontenart="Erlös", euer_zeile=16, konto_skr03="8100",
                  konto_skr04="4100", ust_satz_standard=0),
        Kategorie(name="Betriebseinnahmen (Kleinunternehmer)", kontenart="Erlös", euer_zeile=12,
                  konto_skr03="8192", konto_skr04="4184", ust_satz_standard=0),
        Kunde(firmenname="Patientin", strasse="Str", hausnummer="2", plz="12345", ort="Ort", kundennummer="K-1"),
    ])
    session.commit()
    yield session
    session.close()


def _kunde(db) -> Kunde:
    return db.query(Kunde).one()


def _rechnung(db, satz="19", steuerfrei=True, dokument_typ="Rechnung"):
    return create_rechnung(RechnungCreate(
        typ="ausgang", dokument_typ=dokument_typ, datum=date(2026, 3, 10), kunde_id=_kunde(db).id,
        steuerfrei_4=steuerfrei,
        positionen=[RechnungspositionCreate(beschreibung="Behandlung", netto=Decimal("100"), ust_satz=Decimal(satz))],
    ), db)


def _bezahlt(db, r) -> Rechnung:
    finalisiere_rechnung(r.id, db)
    zahlung_bar_erstellen(r.id, BarZahlungCreate(datum=date(2026, 3, 20), zahlungsart="Bank"), db)
    return db.query(Rechnung).filter(Rechnung.id == r.id).one()


def _pdf_text(pdf: bytes) -> str:
    return "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)


# --- Rechnung -----------------------------------------------------------------------------------

def test_positionen_werden_auf_null_prozent_gesetzt(db):
    r = _rechnung(db, satz="19")
    assert r.steuerfrei_4 is True
    assert r.ust_gesamt == Decimal("0.00")
    assert r.brutto_gesamt == Decimal("100.00")
    assert all(p.ust_satz == 0 for p in r.positionen)


def test_schliesst_andere_sonderfaelle_aus():
    with pytest.raises(ValidationError):
        RechnungCreate(typ="ausgang", datum=date(2026, 3, 10), steuerfrei_4=True, ist_reverse_charge=True,
                       positionen=[RechnungspositionCreate(beschreibung="x", netto=Decimal("1"), ust_satz=Decimal("0"))])


def test_snapshot_friert_befreiungsgrund_ein(db):
    assert json.loads(_absender_snapshot(db))["steuerbefreiung_4"] == "4_nr_14"


# --- Buchung, EÜR, UStVA ------------------------------------------------------------------------

def test_zahlung_regelbesteuert_zeile_16_und_kz_48(db):
    r = _bezahlt(db, _rechnung(db))
    e = db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == r.id).one()
    assert e.kategorie.name == "Betriebseinnahmen (0%)"
    assert e.ust_betrag == Decimal("0.00")

    euer = _berechne_euer(2026, db)
    assert euer["zeilen"].get(16) == Decimal("100.00")
    assert 15 not in euer["zeilen"]

    kz, _ = _berechne_kz(date(2026, 3, 1), date(2026, 3, 31), db)
    assert kz["kz_48"] == Decimal("100.00")
    assert kz["kz_81"] == Decimal("0")


def test_storno_mindert_kz_48(db):
    r = _bezahlt(db, _rechnung(db))
    storno_rechnung(r.id, StornoRequest(grund="Fehler"), db)
    kz, _ = _berechne_kz(date(2026, 1, 1), date(2026, 12, 31), db)
    assert kz["kz_48"] == Decimal("0.00")


def test_jahres_ust_uebernimmt_kz_48(db):
    _bezahlt(db, _rechnung(db))
    assert jahresumsatzsteuer(jahr=2026, db=db).kz_48 == Decimal("100.00")


def test_elster_xml_enthaelt_kz_48():
    xml = build_ustva_xml(
        zeitraum="2026-03", steuernummer13="5133081508159",
        unternehmen=type("U", (), {"firmenname": "Praxis", "vorname": None, "nachname": None, "strasse": "Weg",
                                   "hausnummer": "1", "plz": "12345", "ort": "Ort", "telefon": None, "email": None})(),
        kz_werte={"48": Decimal("100.40")},
    ).decode("iso-8859-15")
    assert "<Kz48>100</Kz48>" in xml


def test_kleinunternehmer_zeile_12_und_13_nicht_im_gesamtumsatz(db):
    unt = db.query(Unternehmen).one()
    unt.ist_kleinunternehmer = True
    db.commit()
    r = _bezahlt(db, _rechnung(db, satz="0"))
    e = db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == r.id).one()
    assert e.kategorie.name == "Betriebseinnahmen (0%)"  # nicht die Kleinunternehmer-Kategorie

    euer = _berechne_euer(2026, db)
    assert euer["zeilen"].get(12) == Decimal("100.00")
    assert euer["zeilen"].get(13) == Decimal("100.00")
    assert kleinunternehmer_gesamtumsatz(2026, db) == Decimal("0.00")
    kz, _ = _berechne_kz(date(2026, 3, 1), date(2026, 3, 31), db)
    assert kz.get("kz_48", Decimal("0")) == Decimal("0")


# --- PDF und E-Rechnung ---------------------------------------------------------------------------

def _unt_dict(db) -> dict:
    return json.loads(_absender_snapshot(db))


@pytest.mark.parametrize("erzeuge", [generate_rechnung_pdf, generate_rechnung_pdf_vorlage1])
def test_pdf_hinweis_statt_paragraf_19(db, erzeuge):
    unt = db.query(Unternehmen).one()
    unt.ist_kleinunternehmer = True
    db.commit()
    r = _rechnung(db, satz="0")
    finalisiere_rechnung(r.id, db)
    text = _pdf_text(erzeuge(db.query(Rechnung).filter(Rechnung.id == r.id).one(), _unt_dict(db)))
    assert "Steuerfreie Leistung nach § 4 Nr. 14 UStG." in text
    assert "§ 19 UStG" not in text


def test_pdf_ohne_kennzeichen_unveraendert(db):
    r = _rechnung(db, steuerfrei=False)
    finalisiere_rechnung(r.id, db)
    text = _pdf_text(generate_rechnung_pdf(db.query(Rechnung).filter(Rechnung.id == r.id).one(), _unt_dict(db)))
    assert "Steuerfreie Leistung" not in text


def test_e_rechnung_kategorie_e_mit_befreiungsgrund(db):
    r = _rechnung(db)
    finalisiere_rechnung(r.id, db)
    unt = {**_unt_dict(db), "email": "praxis@test.example", "telefon": "0123", "iban": "DE89370400440532013000",
           "bic": "COBADEFFXXX", "ust_idnr": "DE123456789"}
    xml = generate_zugferd_xml(db.query(Rechnung).filter(Rechnung.id == r.id).one(), unt).decode("utf-8")
    assert set(re.findall(r"<ram:CategoryCode>([A-Z]+)<", xml)) == {"E"}
    assert "<ram:ExemptionReason>Steuerfreie Leistung nach § 4 Nr. 14 UStG</ram:ExemptionReason>" in xml
    assert "ExemptionReasonCode" not in xml


# --- Umwandlungen ---------------------------------------------------------------------------------

def _angebot_zu_rechnung(db, satz: str) -> Rechnung:
    angebot = _rechnung(db, satz=satz, steuerfrei=False, dokument_typ="Angebot")
    a = db.query(Rechnung).filter(Rechnung.id == angebot.id).one()
    a.angebot_status = "akzeptiert"
    db.commit()
    r = rechnung_aus_angebot(angebot.id, db)
    return db.query(Rechnung).filter(Rechnung.id == r.id).one()


def test_rechnung_aus_angebot_mit_null_prozent_wird_steuerfrei(db):
    assert _angebot_zu_rechnung(db, "0").steuerfrei_4 is True


def test_rechnung_aus_angebot_mit_steuerpflichtigen_positionen_nicht(db):
    assert _angebot_zu_rechnung(db, "19").steuerfrei_4 is False


def test_ohne_befreiungsgrund_in_stammdaten_nicht(db):
    db.query(Unternehmen).one().steuerbefreiung_4 = None
    db.commit()
    assert _angebot_zu_rechnung(db, "0").steuerfrei_4 is False
