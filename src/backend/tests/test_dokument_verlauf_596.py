"""
Issue #596: Dokumentverlauf – was wann mit einem Dokument passiert ist (Druck/PDF, SMTP-Versand,
Übergabe an Thunderbird/Mailprogramm, Mahnungen), sichtbar in Liste, Detail und Partnerstamm.
"""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import api.mail as mail_modul
import main
from api.kunden import anonymisiere_kunde
from api.mail import MailSendenRequest, mail_senden
from api.schemas_rechnungen import RechnungResponse
from api.verlauf import VerlaufMeldung, kunden_verlauf, melde_mahnung, melde_rechnung
from database.connection import Base
from database.models import (
    DokumentVerlauf, Kunde, Mahnung, MahnungRechnung, Rechnung, Rechnungsposition, Unternehmen,
)


@pytest.fixture
def db(tmp_path, monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    monkeypatch.setattr(mail_modul, "APP_DATA_DIR", tmp_path)
    s.add(Unternehmen(firmenname="Test GmbH", strasse="S", hausnummer="1", plz="12345", ort="O",
                      smtp_aktiv=True, smtp_host="smtp.example.com", smtp_port=587,
                      smtp_user="test@example.com", smtp_passwort="geheim"))
    s.add(Kunde(firmenname="Kunde AG", strasse="W", hausnummer="2", plz="54321", ort="X", email="k@example.com"))
    s.commit()
    yield s
    s.close()


def _rechnung(db, nr="RE-1", entwurf=False):
    k = db.query(Kunde).one()
    r = Rechnung(typ="ausgang", rechnungsnummer=nr, datum=date(2026, 11, 1), kunde_id=k.id,
                 netto_gesamt=Decimal("100"), ust_gesamt=Decimal("19"), brutto_gesamt=Decimal("119"),
                 ist_entwurf=entwurf, dokument_typ="Rechnung")
    db.add(r)
    db.flush()
    db.add(Rechnungsposition(rechnung_id=r.id, position_nr=1, beschreibung="B", menge=Decimal("1"),
                             einheit="Stk.", netto=Decimal("100"), ust_satz=Decimal("19"),
                             ust_betrag=Decimal("19"), brutto=Decimal("119")))
    db.commit()
    return r


def _sende(db, **kw):
    with patch("smtplib.SMTP"):
        mail_senden(MailSendenRequest(an="k@example.com", betreff="Rechnung RE-1", text="Anbei", **kw), db=db)


def test_smtp_versand_original_dann_kopie(db):
    r = _rechnung(db)
    _sende(db, rechnung_id=r.id)
    _sende(db, rechnung_id=r.id)
    db.refresh(r)
    v = r.verlauf
    assert [(e.art, e.kanal, e.kopie) for e in v] == [
        ("mail_gesendet", "smtp", False), ("mail_gesendet", "smtp", True)]
    assert v[0].empfaenger == "k@example.com" and v[0].betreff == "Rechnung RE-1"
    assert v[0].kunde_id == r.kunde_id


def test_fehlgeschlagener_versand_steht_nicht_im_verlauf(db):
    import smtplib
    r = _rechnung(db)
    with patch("smtplib.SMTP") as smtp:
        smtp.return_value.__enter__.side_effect = smtplib.SMTPConnectError(421, "x")
        with pytest.raises(HTTPException):
            mail_senden(MailSendenRequest(an="k@example.com", betreff="B", text="T", rechnung_id=r.id), db=db)
    assert db.query(DokumentVerlauf).count() == 0


def test_frontend_meldungen(db):
    r = _rechnung(db)
    melde_rechnung(r.id, VerlaufMeldung(art="gedruckt", kanal="druck"), db)
    melde_rechnung(r.id, VerlaufMeldung(art="mail_uebergeben", kanal="thunderbird", kopie=True,
                                        empfaenger="k@example.com"), db)
    db.refresh(r)
    resp = RechnungResponse.from_orm_extended(r)
    assert [e.art for e in resp.verlauf] == ["gedruckt", "mail_uebergeben"]
    assert resp.letzter_versand.kanal == "thunderbird" and resp.letzter_versand.kopie is True


@pytest.mark.parametrize("art,kanal", [
    ("mail_gesendet", "smtp"),          # SMTP nur über api/mail.py
    ("gedruckt", "thunderbird"),
    ("mahnung_gesendet", "smtp"),
    ("quatsch", "druck"),
])
def test_frontend_darf_nicht_alles_melden(db, art, kanal):
    r = _rechnung(db)
    with pytest.raises(HTTPException) as exc:
        melde_rechnung(r.id, VerlaufMeldung(art=art, kanal=kanal), db)
    assert exc.value.status_code == 422


def test_entwurf_hat_keinen_verlauf(db):
    r = _rechnung(db, entwurf=True)
    with pytest.raises(HTTPException) as exc:
        melde_rechnung(r.id, VerlaufMeldung(art="gedruckt", kanal="druck"), db)
    assert exc.value.status_code == 409


def _mahnung(db, *rechnungen):
    m = Mahnung(mahnnummer="M-1", kunde_id=rechnungen[0].kunde_id, stufe=1, status="versendet",
                versendet_am=datetime(2026, 11, 20, 9, 0))
    db.add(m)
    db.flush()
    for r in rechnungen:
        db.add(MahnungRechnung(mahnung_id=m.id, rechnung_id=r.id, offener_betrag=Decimal("119")))
    db.commit()
    return m


def test_mahnung_erscheint_bei_jeder_rechnung_aber_nicht_als_versand(db):
    r1, r2 = _rechnung(db, "RE-1"), _rechnung(db, "RE-2")
    m = _mahnung(db, r1, r2)
    melde_mahnung(m.id, VerlaufMeldung(art="mahnung_uebergeben", kanal="mailprogramm"), db)
    for r in (r1, r2):
        db.refresh(r)
        resp = RechnungResponse.from_orm_extended(r)
        assert [e.art for e in resp.verlauf] == ["mahnung_uebergeben"]
        assert resp.letzter_versand is None


def test_kundenverlauf_mit_nummern_neueste_zuerst(db):
    r = _rechnung(db)
    melde_rechnung(r.id, VerlaufMeldung(art="pdf", kanal="druck"), db)
    m = _mahnung(db, r)
    melde_mahnung(m.id, VerlaufMeldung(art="mahnung_gedruckt", kanal="druck"), db)
    v = kunden_verlauf(r.kunde_id, db)
    assert [e.art for e in v] == ["mahnung_gedruckt", "pdf"]
    assert v[0].mahnnummer == "M-1" and v[0].rechnungsnummer == "RE-1"
    assert v[1].dokument_typ == "Rechnung"


def test_anonymisieren_entfernt_mailadresse_ereignis_bleibt(db):
    r = _rechnung(db)
    _sende(db, rechnung_id=r.id)
    anonymisiere_kunde(r.kunde_id, db)
    db.commit()
    e = db.query(DokumentVerlauf).one()
    assert e.empfaenger is None and e.betreff is None and e.kunde_id is None
    assert e.rechnung_id == r.id and e.art == "mail_gesendet"


def test_migration_200(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.db'}")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as s:
        s.add(Kunde(firmenname="K", strasse="W", hausnummer="1", plz="1", ort="O"))
        s.flush()
        kid = s.query(Kunde).one().id
        s.add_all([
            Rechnung(typ="ausgang", rechnungsnummer="A", datum=date(2026, 1, 1), kunde_id=kid,
                     netto_gesamt=0, ust_gesamt=0, brutto_gesamt=0, ist_entwurf=False,
                     ausgegeben=True, ausgegeben_am=datetime(2026, 1, 2, 10, 0)),
            Rechnung(typ="ausgang", rechnungsnummer="B", datum=date(2026, 1, 1), kunde_id=kid,
                     netto_gesamt=0, ust_gesamt=0, brutto_gesamt=0, ist_entwurf=False),
        ])
        s.flush()
        a = s.query(Rechnung).filter_by(rechnungsnummer="A").one()
        m = Mahnung(mahnnummer="M", kunde_id=kid, stufe=1, status="versendet",
                    versendet_am=datetime(2026, 2, 1, 8, 0))
        s.add(m)
        s.flush()
        s.add(MahnungRechnung(mahnung_id=m.id, rechnung_id=a.id, offener_betrag=0))
        s.commit()
    with engine.begin() as conn:
        conn.execute(text("PRAGMA user_version = 199"))
    monkeypatch.setattr(main, "engine", engine)
    main._run_migrations()
    with engine.begin() as conn:
        zeilen = conn.execute(text(
            "SELECT art, kanal, zeitpunkt FROM dokument_verlauf ORDER BY zeitpunkt")).all()
        assert [(z[0], z[1]) for z in zeilen] == [("ausgegeben", "unbekannt"), ("mahnung_gesendet", "unbekannt")]
        assert str(zeilen[0][2]).startswith("2026-01-02 10:00")
        conn.execute(text("PRAGMA user_version = 199"))
    main._run_migrations()  # zweiter Lauf legt nichts doppelt an
    with engine.begin() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM dokument_verlauf")).scalar() == 2
