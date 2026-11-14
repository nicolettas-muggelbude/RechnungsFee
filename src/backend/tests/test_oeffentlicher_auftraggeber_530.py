"""
Issue #530: Rechnungen an öffentliche Auftraggeber (XRechnung mit Leitweg-ID).

- Leitweg-ID: Format + Prüfziffer (Modulo 97-10)
- Kunde mit Schalter: Leitweg-ID und E-Mail Pflicht, ZUGFeRD automatisch an
- XML: Leitweg-ID als BuyerReference (BT-10) statt Kundennummer
- Finalisieren meldet fehlende Pflichtangaben (Telefon/E-Mail/IBAN Verkäufer, E-Mail Kunde)
- XRechnung-XML als eigene Datei, beim ersten Abruf archiviert (GoBD), danach unverändert
- PDF ist reine Sichtkopie (keine eingebettete XML), Mail hängt XML + PDF an
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from fastapi import HTTPException
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api.mail as mail_mod
import api.rechnungen as rechnungen_mod
import utils.zugferd as zugferd_mod
from api.kunden import create_kunde, update_kunde
from api.rechnungen import finalisiere_rechnung, rechnung_als_pdf, rechnung_als_xrechnung
from api.schemas import KundeCreate, KundeUpdate
from database.connection import Base
from database.models import Kunde, Rechnung, Rechnungsposition, Unternehmen
from utils.leitweg_id import leitweg_id_fehler

LEITWEG = "991-33333TEST-33"


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(rechnungen_mod, "APP_DATA_DIR", tmp_path)
    monkeypatch.setattr(zugferd_mod, "APP_DATA_DIR", tmp_path)
    monkeypatch.setattr(mail_mod, "APP_DATA_DIR", tmp_path)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(
        firmenname="Testfirma GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort",
        steuernummer="12/345/67890", telefon="0123 456", email="info@testfirma.example",
        iban="DE02120300000000202051", oeffentliche_auftraggeber_aktiv=True,
        smtp_aktiv=True, smtp_host="localhost", smtp_user="u", smtp_passwort="p",
    ))
    session.commit()
    yield session
    session.close()


def _rechnung(db, *, oeffentlich=True, leitweg=LEITWEG, email="rechnung@amt.example", entwurf=False):
    kunde = Kunde(firmenname="Stadtverwaltung Musterstadt", strasse="Rathausplatz", hausnummer="1",
                  plz="54321", ort="Musterstadt", kundennummer="KD-0007", email=email,
                  zugferd_aktiv=True, oeffentlicher_auftraggeber=oeffentlich, leitweg_id=leitweg)
    db.add(kunde)
    db.commit()
    r = Rechnung(
        typ="ausgang", kunde_id=kunde.id, rechnungsnummer="RE-260001", datum=date(2026, 11, 1),
        dokument_typ="Rechnung", eingabemodus="netto", ist_entwurf=entwurf,
        netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("19.00"), brutto_gesamt=Decimal("119.00"),
    )
    db.add(r)
    db.commit()
    db.add(Rechnungsposition(
        rechnung_id=r.id, position_nr=1, beschreibung="Beratung", menge=Decimal("1"), einheit="Std",
        netto=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"), brutto=Decimal("119.00"),
    ))
    db.commit()
    db.refresh(r)
    return r


# ── Leitweg-ID ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("lid", ["991-33333TEST-33", "992-90009-96", "04011000-1234512345-06", " 991-33333test-33 "])
def test_leitweg_id_gueltig(lid):
    assert leitweg_id_fehler(lid) is None


@pytest.mark.parametrize("lid,teil", [
    ("991-33333TEST-34", "Prüfziffer"),
    ("991_33333TEST_33", "Format"),
    ("1-33333-33", "Format"),
    ("", "fehlt"),
])
def test_leitweg_id_ungueltig(lid, teil):
    assert teil in leitweg_id_fehler(lid)


# ── Kundenstamm ───────────────────────────────────────────────────────────────

def test_kunde_oeffentlich_braucht_leitweg_und_email(db):
    with pytest.raises(HTTPException) as e:
        create_kunde(KundeCreate(firmenname="Amt", oeffentlicher_auftraggeber=True), db)
    assert e.value.status_code == 422
    assert "Leitweg-ID" in e.value.detail and "E-Mail" in e.value.detail


def test_kunde_oeffentlich_normalisiert_und_zugferd_an(db):
    k = create_kunde(KundeCreate(firmenname="Amt", oeffentlicher_auftraggeber=True,
                                 leitweg_id=" 991-33333test-33", email="a@amt.example"), db)
    assert k.leitweg_id == LEITWEG
    assert k.zugferd_aktiv is True


def test_kunde_ohne_schalter_unveraendert(db):
    k = create_kunde(KundeCreate(firmenname="Privat"), db)
    assert k.zugferd_aktiv is False and k.leitweg_id is None


def test_update_ungueltige_leitweg_id_abgewiesen(db):
    k = create_kunde(KundeCreate(firmenname="Amt", oeffentlicher_auftraggeber=True,
                                 leitweg_id=LEITWEG, email="a@amt.example"), db)
    with pytest.raises(HTTPException):
        update_kunde(k.id, KundeUpdate(firmenname="Amt", oeffentlicher_auftraggeber=True,
                                       leitweg_id="991-33333TEST-34", email="a@amt.example"), db)
    assert db.get(Kunde,k.id).leitweg_id == LEITWEG


# ── XML / Finalisieren ────────────────────────────────────────────────────────

def test_xml_leitweg_id_als_buyer_reference(db):
    r = _rechnung(db)
    xml = zugferd_mod.generate_zugferd_xml(r, {
        "firmenname": "Testfirma GmbH", "strasse": "Teststr.", "plz": "12345", "ort": "Testort",
        "steuernummer": "12/345/67890"}).decode()
    assert f"<ram:BuyerReference>{LEITWEG}</ram:BuyerReference>" in xml


def test_xml_ohne_schalter_weiter_kundennummer(db):
    r = _rechnung(db, oeffentlich=False)
    xml = zugferd_mod.generate_zugferd_xml(r, {
        "firmenname": "Testfirma GmbH", "strasse": "Teststr.", "plz": "12345", "ort": "Testort",
        "steuernummer": "12/345/67890"}).decode()
    assert "<ram:BuyerReference>KD-0007</ram:BuyerReference>" in xml


def test_finalisieren_meldet_fehlende_pflichtangaben(db):
    u = db.query(Unternehmen).first()
    u.telefon = ""
    u.iban = None
    db.commit()
    r = _rechnung(db, email=None, entwurf=True)
    with pytest.raises(HTTPException) as e:
        finalisiere_rechnung(r.id, db)
    assert e.value.status_code == 422
    for teil in ("Telefon", "IBAN", "E-Mail-Adresse beim Kunden"):
        assert teil in e.value.detail
    assert db.get(Rechnung,r.id).ist_entwurf is True


def test_finalisieren_ohne_schalter_ohne_pflichtpruefung(db):
    u = db.query(Unternehmen).first()
    u.telefon = ""
    db.commit()
    r = _rechnung(db, oeffentlich=False, entwurf=True)
    assert finalisiere_rechnung(r.id, db).ist_entwurf is False


# ── Ausgabe ───────────────────────────────────────────────────────────────────

def test_xrechnung_download_archiviert_original(db, tmp_path):
    r = _rechnung(db)
    erste = rechnung_als_xrechnung(r.id, db)
    assert erste.media_type == "application/xml"
    assert erste.headers["content-disposition"].startswith("attachment;")
    r = db.get(Rechnung,r.id)
    assert r.original_xml_pfad and (tmp_path / r.original_xml_pfad).is_file()
    assert r.ausgegeben is True

    # Stammdaten ändern: das archivierte Original bleibt maßgeblich
    k = r.kunde
    k.leitweg_id = "992-90009-96"
    db.commit()
    zweite = rechnung_als_xrechnung(r.id, db)
    assert zweite.body == erste.body
    assert LEITWEG.encode() in zweite.body


def test_xrechnung_entwurf_abgewiesen(db):
    r = _rechnung(db, entwurf=True)
    with pytest.raises(HTTPException) as e:
        rechnung_als_xrechnung(r.id, db)
    assert e.value.status_code == 400


def test_pdf_ist_sichtkopie_ohne_xml(db):
    r = _rechnung(db)
    pdf = PdfReader(BytesIO(rechnung_als_pdf(r.id, nur_ansehen=True, db=db).body))
    assert "xrechnung.xml" not in pdf.attachments


def test_mail_haengt_xml_und_pdf_an(db, monkeypatch):
    gesendet = []
    monkeypatch.setattr(mail_mod, "_sende", lambda u, msg, empf, db: gesendet.append(msg))
    r = _rechnung(db)
    mail_mod.mail_senden(mail_mod.MailSendenRequest(
        an="rechnung@amt.example", betreff="Rechnung", text="Anbei", rechnung_id=r.id), db)
    namen = [t.get_filename() for t in gesendet[0].walk() if t.get_content_disposition() == "attachment"]
    assert namen[0] == "XRechnung_RE-260001.xml"
    assert namen[1].endswith(".pdf")
    assert db.get(Rechnung,r.id).original_xml_pfad
