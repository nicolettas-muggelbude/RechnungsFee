"""Issue #565: Jahresauswahl in Journal und Bank-Import zeigt nur Jahre mit Buchungen."""
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.bank_import import transaktionsjahre
from api.journal import buchungsjahre
from database.connection import Base
from database.models import BankImport, BankTemplate, BankTransaktion, Journaleintrag, Konto


def test_jahre_nur_mit_buchungen():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    assert buchungsjahre(db) == []
    for i, d in enumerate([date(2024, 3, 1), date(2026, 1, 5), date(2024, 12, 31)]):
        db.add(Journaleintrag(datum=d, belegnr=f"J-{i}", beschreibung="x", zahlungsart="Bar", art="Einnahme",
                              netto_betrag=Decimal("1"), ust_satz=Decimal("0"), ust_betrag=Decimal("0"),
                              brutto_betrag=Decimal("1")))
    k1, k2 = Konto(name="A", anbieter="Bank A", kontoart="giro"), Konto(name="B", anbieter="Bank B", kontoart="giro")
    db.add_all([k1, k2])
    db.flush()
    imp = BankImport(konto_id=k1.id, template_id="CAMT_XML", dateiname="x.csv")
    db.add_all([BankTemplate(id="CAMT_XML", name="CAMT", bank="x", format="CAMT", column_mapping="{}"), imp])
    db.flush()
    db.add_all([
        BankTransaktion(konto_id=k1.id, import_id=imp.id, datum=date(2025, 6, 1), betrag=Decimal("5")),
        BankTransaktion(konto_id=k2.id, import_id=imp.id, datum=date(2023, 6, 1), betrag=Decimal("5")),
    ])
    db.commit()
    assert buchungsjahre(db) == [2026, 2024]
    assert transaktionsjahre(k1.id, db) == [2025]
