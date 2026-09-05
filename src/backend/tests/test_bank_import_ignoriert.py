"""
Regressionstests für Issue #379: bank_transaktionen.ignoriert.

Eine als "ignoriert" markierte Transaktion (z.B. interne Umbuchung zwischen
eigenen Konten bei einem Mischkonto) darf weder von auto_buchen() automatisch
gebucht noch über buche_transaktion() manuell gebucht werden können.
"""
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.bank_import import (
    BuchungsRequest,
    TransaktionKlassifizierung,
    auto_buchen,
    buche_transaktion,
    klassifiziere_transaktion,
)
from database.connection import Base
from database.models import BankImport, BankTemplate, BankTransaktion, Konto


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _konto_und_import_id(db) -> tuple[int, int]:
    k = Konto(name="Testkonto", anbieter="Testbank")
    db.add(k)
    db.flush()
    tmpl = BankTemplate(id="test-tmpl", name="Test", bank="Testbank", format="Standard", column_mapping="{}")
    db.add(tmpl)
    db.flush()
    imp = BankImport(konto_id=k.id, template_id=tmpl.id, dateiname="test.csv")
    db.add(imp)
    db.commit()
    db.refresh(imp)
    return k.id, imp.id


def test_klassifiziere_transaktion_setzt_ignoriert(db):
    konto_id, import_id = _konto_und_import_id(db)
    tx = BankTransaktion(
        konto_id=konto_id, import_id=import_id, datum=date(2026, 1, 10),
        betrag=Decimal("-50.00"), verwendungszweck="Umbuchung Tagesgeld",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    resp = klassifiziere_transaktion(
        tx.id, TransaktionKlassifizierung(ignoriert=True), db,
    )

    assert resp.ignoriert is True
    db.refresh(tx)
    assert tx.ignoriert is True


def test_auto_buchen_ignoriert_ignorierte_transaktion(db):
    konto_id, import_id = _konto_und_import_id(db)
    tx = BankTransaktion(
        konto_id=konto_id, import_id=import_id, datum=date(2026, 1, 10),
        betrag=Decimal("-50.00"), verwendungszweck="Umbuchung Tagesgeld", ignoriert=True,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    ergebnis = auto_buchen(konto_id, import_id=None, db=db)

    assert ergebnis.gebucht == 0
    assert ergebnis.offen == 0
    db.refresh(tx)
    assert tx.journal_id is None


def test_buche_transaktion_lehnt_ignorierte_transaktion_ab(db):
    konto_id, import_id = _konto_und_import_id(db)
    tx = BankTransaktion(
        konto_id=konto_id, import_id=import_id, datum=date(2026, 1, 10),
        betrag=Decimal("-50.00"), verwendungszweck="Umbuchung Tagesgeld", ignoriert=True,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    with pytest.raises(HTTPException) as exc_info:
        buche_transaktion(tx.id, BuchungsRequest(), db)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "ignoriert"
