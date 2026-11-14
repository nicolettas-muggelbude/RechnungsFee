"""
Issue #526: Datenauskunft (Art. 15 DSGVO) per Mail – SMTP-Versand hängt dieselbe PDF an,
die auch „Datenauskunft (PDF)" anzeigt, für Kunden und Lieferanten.
"""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api.mail as mail_mod
from api.kunden import dsgvo_export_pdf as kunde_pdf_endpunkt
from database.connection import Base
from database.models import Kunde, Lieferant, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Testfirma", strasse="Weg", hausnummer="1", plz="12345", ort="Ort",
                            smtp_aktiv=True, smtp_host="localhost",
                            smtp_user="test@example.org", smtp_passwort="x"))
    session.commit()
    yield session
    session.close()


@pytest.fixture
def gesendet(monkeypatch):
    nachrichten = []
    monkeypatch.setattr(mail_mod, "_sende", lambda u, msg, empf, db: nachrichten.append((msg, empf)))
    return nachrichten


def _anhaenge(msg):
    return {
        teil.get_filename(): teil.get_payload(decode=True)
        for teil in msg.walk()
        if teil.get_content_disposition() == "attachment"
    }


def test_kunde_auskunft_als_anhang(db, gesendet):
    k = Kunde(vorname="Erika", nachname="Muster", email="erika@example.org")
    db.add(k)
    db.commit()

    mail_mod.mail_senden(mail_mod.MailSendenRequest(
        an="erika@example.org", betreff="Auskunft", text="Hallo", dsgvo_kunde_id=k.id), db)

    msg, empfaenger = gesendet[0]
    assert empfaenger == ["erika@example.org"]
    anhaenge = _anhaenge(msg)
    assert len(anhaenge) == 1
    name, inhalt = next(iter(anhaenge.items()))
    assert name.startswith("dsgvo-Erika-Muster-") and name.endswith(".pdf")
    assert inhalt.startswith(b"%PDF")


def test_lieferant_auskunft_als_anhang(db, gesendet):
    lf = Lieferant(firmenname="Lieferant GmbH", email="info@example.org")
    db.add(lf)
    db.commit()

    mail_mod.mail_senden(mail_mod.MailSendenRequest(
        an="info@example.org", betreff="Auskunft", text="Hallo", dsgvo_lieferant_id=lf.id), db)

    anhaenge = _anhaenge(gesendet[0][0])
    assert len(anhaenge) == 1
    assert next(iter(anhaenge)).startswith("dsgvo-Lieferant-GmbH-")


def test_unbekannter_kunde_404_ohne_versand(db, gesendet):
    with pytest.raises(HTTPException) as e:
        mail_mod.mail_senden(mail_mod.MailSendenRequest(
            an="x@example.org", betreff="b", text="t", dsgvo_kunde_id=999), db)
    assert e.value.status_code == 404
    assert gesendet == []


def test_pdf_endpunkt_unveraendert_inline(db):
    k = Kunde(firmenname="Firma A")
    db.add(k)
    db.commit()
    antwort = kunde_pdf_endpunkt(k.id, db)
    assert antwort.media_type == "application/pdf"
    assert antwort.headers["content-disposition"].startswith("inline;")
