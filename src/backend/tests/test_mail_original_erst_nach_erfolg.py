"""
Regressionstest für Issue #410: Eine Rechnung wurde bereits beim VORBEREITEN des
Mail-Anhangs als "ausgegeben" markiert (original_pdf_pfad gesetzt, ausgegeben_am gesetzt,
committet) - noch bevor der eigentliche SMTP-Versand überhaupt versucht wurde. Scheiterte
der erste Sendeversuch (z.B. SMTP-Rate-Limit "zu viele Mails pro Minute"), blieb die
Markierung trotzdem bestehen. Ein zweiter, diesmal erfolgreicher Versandversuch bekam dadurch
fälschlich den KOPIE-Stempel statt des echten Originals, weil _pdf_bytes_fuer() beim zweiten
Aufruf schon ein original_pdf_pfad vorfand.

Fix: Die DB-Markierung erfolgt jetzt erst in mail_senden(), NACH erfolgreichem _sende() -
_sende() wirft bei jedem Fehler eine HTTPException, die Markierung wird dann nie erreicht.
"""
from datetime import date
from decimal import Decimal
from unittest.mock import patch
import smtplib

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import Kunde, Rechnung, Rechnungsposition, Unternehmen
import api.mail as mail_modul
from api.mail import mail_senden, MailSendenRequest


@pytest.fixture
def db(tmp_path, monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    monkeypatch.setattr(mail_modul, "APP_DATA_DIR", tmp_path)

    unt = Unternehmen(
        firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort",
        smtp_aktiv=True, smtp_host="smtp.example.com", smtp_port=587,
        smtp_user="test@example.com", smtp_passwort="geheim",
    )
    session.add(unt)

    kunde = Kunde(firmenname="Kunde GmbH", strasse="Kundenweg", hausnummer="1", plz="54321", ort="Kundenstadt")
    session.add(kunde)
    session.flush()

    rechnung = Rechnung(
        typ="ausgang", rechnungsnummer="RE-2026-1", datum=date(2026, 10, 1),
        kunde_id=kunde.id, netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("19.00"),
        brutto_gesamt=Decimal("119.00"), ist_entwurf=False, dokument_typ="Rechnung",
    )
    session.add(rechnung)
    session.flush()
    session.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Beratung", menge=Decimal("1"),
        einheit="Stk.", netto=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        brutto=Decimal("119.00"),
    ))
    session.commit()
    session.refresh(rechnung)

    yield session, rechnung.id
    session.close()


def _request(rechnung_id: int) -> MailSendenRequest:
    return MailSendenRequest(an="empfaenger@example.com", betreff="Rechnung", text="Anbei die Rechnung.", rechnung_id=rechnung_id)


def test_fehlgeschlagener_versand_markiert_rechnung_nicht_als_ausgegeben(db):
    session, rechnung_id = db

    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp.return_value.__enter__.side_effect = smtplib.SMTPConnectError(421, "Too many messages per minute")
        with pytest.raises(HTTPException):
            mail_senden(_request(rechnung_id), db=session)

    rechnung = session.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    assert rechnung.ausgegeben is False
    assert rechnung.original_pdf_pfad is None


def test_erfolgreicher_versand_nach_fehlschlag_bekommt_original_nicht_kopie(db):
    """Kernszenario aus Issue #410: erster Versuch scheitert (Rate-Limit), zweiter klappt -
    die zweite, tatsächlich zugestellte Mail muss das echte Original enthalten, nicht die
    Kopie mit KOPIE-Stempel."""
    session, rechnung_id = db

    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp.return_value.__enter__.side_effect = smtplib.SMTPConnectError(421, "Too many messages per minute")
        with pytest.raises(HTTPException):
            mail_senden(_request(rechnung_id), db=session)

    with patch("smtplib.SMTP") as mock_smtp:
        srv = mock_smtp.return_value.__enter__.return_value
        mail_senden(_request(rechnung_id), db=session)
        assert srv.sendmail.called

    rechnung = session.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    assert rechnung.ausgegeben is True
    assert rechnung.original_pdf_pfad is not None
