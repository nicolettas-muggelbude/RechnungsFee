"""
Ohne IBAN im Export (PayPal) wird die eigene E-Mail-Adresse gegen die Kennung
der Zahlungsdienstleister gehalten. Ein Treffer wählt das Konto, mehrere Treffer
bleiben eine Auswahlliste. Das Bankkonto fällt nicht darüber.
"""
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.bank_import import _vorschau_fuer_bytes
from database.connection import Base
from database.models import BankTemplate, Konto
from database.seed import SYSTEM_BANK_TEMPLATES


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _paypal_template(db) -> None:
    tpl = next(t for t in SYSTEM_BANK_TEMPLATES if t["id"] == "paypal")
    mapping = {"__erkennungs__": tpl["erkennungs_spalten"], **tpl["column_mapping"]}
    db.add(BankTemplate(
        id=tpl["id"],
        name=tpl["name"],
        bank=tpl["bank"],
        format=tpl["format"],
        delimiter=tpl["delimiter"],
        encoding=tpl["encoding"],
        decimal_separator=tpl["decimal_separator"],
        date_format=tpl["date_format"],
        skip_rows=tpl["skip_rows"],
        column_mapping=json.dumps(mapping, ensure_ascii=False),
    ))


def _bank(db) -> Konto:
    bank = Konto(
        name="Giro",
        anbieter="Sparkasse",
        kontoart="bank",
        iban="DE89370400440532013000",
        ist_standard=True,
        kennung="fibu@musterfirma.de",
    )
    db.add(bank)
    return bank


def _dienstleister(db, name: str, kennung: str) -> Konto:
    konto = Konto(
        name=name,
        anbieter="PayPal",
        kontoart="zahlungsdienstleister",
        kennung=kennung,
    )
    db.add(konto)
    return konto


def _csv(absender_spalte: str, empfaenger_spalte: str) -> bytes:
    # Eigene Adresse steht in jeder Zeile, die Gegenstelle nur in einer.
    text = (
        f"Datum,Uhrzeit,Beschreibung,Name,Brutto,Währung,Transaktionscode,{absender_spalte},{empfaenger_spalte}\n"
        '18.06.2025,07:47:30,Aufladung,PayPal Inc.,"100,00",EUR,CODE1,viban_TopUp@paypal.com,fibu@musterfirma.de\n'
        '21.06.2025,12:29:40,Zahlung,Deutsche Post AG,"-6,19",EUR,CODE2,fibu@musterfirma.de,service@beispiel.de\n'
    )
    return text.encode("utf-8")


def test_eine_kennung_waehlt_dienstleister_nicht_bank(db):
    _paypal_template(db)
    bank = _bank(db)
    paypal = _dienstleister(db, "PayPal Geschäft", "fibu@musterfirma.de")
    db.commit()

    result = _vorschau_fuer_bytes(_csv('"Absender E-Mail-Adresse"', '"Empfänger E-Mail-Adresse"'), None, None, db)

    assert result.erkannte_email == "fibu@musterfirma.de"
    assert result.erkanntes_konto_id == paypal.id
    assert result.email_konto_ids == [paypal.id]
    assert bank.id not in result.email_konto_ids
    assert len(result.transaktionen) == 2

    # Manuell gewähltes Konto hat Vorrang vor der E-Mail.
    manuell = _vorschau_fuer_bytes(
        _csv('"Absender E-Mail-Adresse"', '"Empfänger E-Mail-Adresse"'), bank.id, None, db,
    )
    assert manuell.erkanntes_konto_id == bank.id
    assert manuell.erkannte_email is None
    assert manuell.email_konto_ids == []


def test_bindestrich_im_spaltennamen_trifft_dieselbe_adresse(db):
    _paypal_template(db)
    paypal = _dienstleister(db, "PayPal Geschäft", "Fibu@Musterfirma.de")
    db.commit()

    result = _vorschau_fuer_bytes(
        _csv("Absender-E-Mail-Adresse", "Empfänger-E-Mail-Adresse"), None, None, db,
    )

    assert result.erkannte_email == "fibu@musterfirma.de"
    assert result.erkanntes_konto_id == paypal.id


def test_zwei_dienstleister_liefern_auswahlliste_ohne_bank(db):
    _paypal_template(db)
    bank = _bank(db)
    erster = _dienstleister(db, "PayPal Geschäft", "Fibu@Musterfirma.de")
    zweiter = _dienstleister(db, "PayPal Privatanteil", " fibu@musterfirma.de ")
    db.commit()

    result = _vorschau_fuer_bytes(_csv('"Absender E-Mail-Adresse"', '"Empfänger E-Mail-Adresse"'), None, None, db)

    assert result.erkanntes_konto_id is None
    assert result.erkannte_email == "fibu@musterfirma.de"
    assert set(result.email_konto_ids) == {erster.id, zweiter.id}
    assert bank.id not in result.email_konto_ids
