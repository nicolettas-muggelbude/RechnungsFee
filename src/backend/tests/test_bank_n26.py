"""N26-CSV: automatische Erkennung und EUR-Beträge mit synthetischen Daten."""
import csv
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.connection import Base
from database.models import BankTemplate
from database.seed import run_all_seeds, seed_bank_templates
from utils.bank_csv_parser import find_best_template, parse_csv_mit_template


N26_CSV = (
    'Booking Date,Value Date,Partner Name,Partner Iban,Type,Payment Reference,'
    'Account Name,Amount (EUR),Original Amount,Original Currency,Exchange Rate\n'
    '2026-01-02,2026-01-03,"Testkunde, Süd",DE00000000000000000000,'
    'Incoming Transfer,"Testleistung, Januar",Testkonto,+100.50,100.50,EUR,1\n'
    '2026-01-04,2026-01-05,Online-Anbieter,,Card Payment,'
    'Testausgabe,Testkonto,-20.25,-25.00,USD,0.81\n'
).encode('utf-8')


@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_n26_wird_automatisch_erkannt(db):
    seed_bank_templates(db)
    header = next(csv.reader(N26_CSV.decode('utf-8').splitlines()))
    template = find_best_template(header, db.query(BankTemplate).all())
    assert template is not None
    assert template.id == 'n26'


def test_n26_buchungen_mit_unicode_kommas_und_eur_betrag(db):
    seed_bank_templates(db)
    template = db.get(BankTemplate, 'n26')
    assert template is not None
    rows, _ = parse_csv_mit_template(N26_CSV, template)
    assert len(rows) == 2
    assert rows[0]['datum'] == date(2026, 1, 2)
    assert rows[0]['valuta'] == date(2026, 1, 3)
    assert rows[0]['partner_name'] == 'Testkunde, Süd'
    assert rows[0]['partner_iban'] == 'DE00000000000000000000'
    assert rows[0]['buchungstext'] == 'Incoming Transfer'
    assert rows[0]['verwendungszweck'] == 'Testleistung, Januar'
    assert rows[0]['betrag'] == Decimal('100.50')
    assert rows[1]['datum'] == date(2026, 1, 4)
    assert rows[1]['valuta'] == date(2026, 1, 5)
    assert rows[1]['partner_name'] == 'Online-Anbieter'
    assert rows[1]['partner_iban'] is None
    assert rows[1]['buchungstext'] == 'Card Payment'
    assert rows[1]['verwendungszweck'] == 'Testausgabe'
    assert rows[1]['betrag'] == Decimal('-20.25')
    assert all(row['waehrung'] == 'EUR' for row in rows)
    assert all('Original Amount' not in row and 'Account Name' not in row for row in rows)


def test_n26_bei_neuinstallation_durch_startup_seeds(db):
    run_all_seeds(db)
    template = db.get(BankTemplate, 'n26')
    assert template is not None
    assert template.ist_system is True
    rows, _ = parse_csv_mit_template(N26_CSV, template)
    assert rows[1]['betrag'] == Decimal('-20.25')


def test_n26_wird_bestehender_datenbank_idempotent_hinzugefuegt(db):
    seed_bank_templates(db)
    # Vorherigen Installationsstand ohne die neue Vorlage nachbilden.
    db.query(BankTemplate).filter(BankTemplate.id == 'n26').delete()
    existing = db.query(BankTemplate).first()
    existing.name = 'Individuelle Bezeichnung'
    existing_id = existing.id
    db.commit()
    previous_count = db.query(BankTemplate).count()

    run_all_seeds(db)
    assert db.get(BankTemplate, 'n26') is not None
    assert db.query(BankTemplate).count() == previous_count + 1
    run_all_seeds(db)
    assert db.query(BankTemplate).count() == previous_count + 1
    assert db.get(BankTemplate, existing_id).name == 'Individuelle Bezeichnung'
