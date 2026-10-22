"""
Issue #466: Bank-Vorlage bunq (CSV-Export „Umsätze“).

bunq schreibt die letzte Spalte (Description) doppelt gequotet - ohne Reparatur hing am
Verwendungszweck `""`, und Kommas im Text schnitten ihn ab.
"""
import csv
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import BankTemplate
from database.seed import seed_bank_templates
from utils.bank_csv_parser import find_best_template, parse_csv_mit_template

BUNQ_CSV = (
    '"Date","Interest Date","Amount","Account","Counterparty","Name","Description"\n'
    '"2026-10-01","2026-10-01","3.000,00","DE89370400440532013000","AE611904300234573201","Firma1 LLC",""Rechnung September 2026""\n'
    '"2026-10-01","2026-10-01","-478,99","DE89370400440532013000","DE89370400440532013001","Mustermann, Max",""AutoVAT""\n'
    '"2026-10-02","2026-11-01","-124,55","DE89370400440532013000","","ABCDEFG.COM",""ABCDEFG.COM DUBAI, AE 139.00 USD, 1 USD = 0.89604 EUR""\n'
    '"2026-10-03","2026-10-03","-12,00","DE89370400440532013000","NL28BUNQ2058737261","bunq BV",""\n'
).encode("utf-8")


@pytest.fixture
def templates():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    seed_bank_templates(db)
    yield db.query(BankTemplate).all()
    db.close()


def test_bunq_wird_automatisch_erkannt(templates):
    header = next(csv.reader([BUNQ_CSV.decode().splitlines()[0]]))
    assert find_best_template(header, templates).id == "bunq"


def test_bunq_buchungen_vollstaendig_und_sauber(templates):
    vorlage = next(t for t in templates if t.id == "bunq")
    txs, _ = parse_csv_mit_template(BUNQ_CSV, vorlage)
    assert len(txs) == 4
    assert txs[0]["datum"] == date(2026, 10, 1)
    assert txs[0]["betrag"] == Decimal("3000.00")
    assert txs[0]["partner_iban"] == "AE611904300234573201"
    assert txs[0]["verwendungszweck"] == "Rechnung September 2026"  # ohne angehängtes ""
    assert txs[1]["partner_name"] == "Mustermann, Max"
    assert txs[1]["betrag"] == Decimal("-478.99")
    # Komma im Verwendungszweck schneidet nicht mehr ab, Valuta getrennt vom Buchungsdatum
    assert txs[2]["verwendungszweck"] == "ABCDEFG.COM DUBAI, AE 139.00 USD, 1 USD = 0.89604 EUR"
    assert txs[2]["valuta"] == date(2026, 11, 1)
    assert txs[2]["partner_iban"] is None
    assert txs[3]["verwendungszweck"] is None  # leere Description bleibt leer
