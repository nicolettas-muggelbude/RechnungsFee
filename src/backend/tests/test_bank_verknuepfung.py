"""
Regressionstests für die Bank-Verknüpfung bei Storno/Korrektur (Issue #322).

Bug: BankTransaktion.journal_id blieb nach Storno/Korrektur einer verknüpften
Buchung dauerhaft an der toten (stornierten) Buchung hängen - weder wanderte
die Verknüpfung automatisch mit, noch ließ sie sich über die API umhängen.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.bank_import import journal_verknuepfen, JournalVerknuepfenRequest
from api.journal import update_eintrag
from api.schemas import JournalEintragCreate
from database.connection import Base
from database.models import BankImport, BankTemplate, BankTransaktion, Journaleintrag, Konto


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _konto_und_import_id(db) -> tuple[int, int]:
    """Minimales Konto + BankTemplate + BankImport - nur als Pflicht-FKs fuer BankTransaktion."""
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


def _eintrag(db, **kwargs) -> Journaleintrag:
    defaults = dict(
        datum=date(2026, 1, 10), belegnr="J-1", beschreibung="Testbuchung",
        zahlungsart="Bank", art="Ausgabe",
        netto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        brutto_betrag=Decimal("119.00"), vorsteuerabzug=True, immutable=True,
    )
    defaults.update(kwargs)
    e = Journaleintrag(**defaults)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def test_put_korrektur_verschiebt_bank_verknuepfung_auf_neubuchung(db):
    """Der haeufigste Fall (Issue #322, Vorschlag 1): PUT nach Ablauf des
    Korrekturfensters erzeugt Storno + Neubuchung - die Bank-Verknuepfung muss
    automatisch auf die Neubuchung wandern statt an der stornierten haengen zu bleiben."""
    konto_id, import_id = _konto_und_import_id(db)
    original = _eintrag(db, belegnr="J-1", immutable=True)
    tx = BankTransaktion(
        konto_id=konto_id, import_id=import_id, datum=date(2026, 1, 10), betrag=Decimal("-119.00"),
        verwendungszweck="Test", journal_id=original.id,
    )
    db.add(tx)
    db.commit()

    data = JournalEintragCreate(
        datum=date(2026, 1, 10), beschreibung="Korrigierte Buchung",
        zahlungsart="Bank", art="Ausgabe", brutto_betrag=Decimal("119.00"),
        ust_satz=Decimal("19"), vorsteuerabzug=True,
    )
    neu = update_eintrag(original.id, data, db)

    db.refresh(tx)
    assert tx.journal_id == neu.id


def test_journal_verknuepfen_blockiert_wenn_alte_buchung_noch_gueltig(db):
    konto_id, import_id = _konto_und_import_id(db)
    original = _eintrag(db, belegnr="J-2")
    andere = _eintrag(db, belegnr="J-3")
    tx = BankTransaktion(
        konto_id=konto_id, import_id=import_id, datum=date(2026, 1, 10), betrag=Decimal("-119.00"),
        verwendungszweck="Test", journal_id=original.id,
    )
    db.add(tx)
    db.commit()

    with pytest.raises(Exception) as exc_info:
        journal_verknuepfen(tx.id, JournalVerknuepfenRequest(journal_id=andere.id), db)
    assert "bereits_verknuepft" in str(exc_info.value)


def test_journal_verknuepfen_erlaubt_umhaengen_wenn_alte_buchung_storniert(db):
    """Issue #322, Vorschlag 2: storno_eintrag()/storno_rechnung() erzeugen keine
    automatische Nachfolgebuchung - hier muss sich die Verknuepfung manuell umhaengen
    lassen, sobald die aktuell verknuepfte Buchung storniert ist."""
    konto_id, import_id = _konto_und_import_id(db)
    original = _eintrag(db, belegnr="J-4")
    neu = _eintrag(db, belegnr="J-5")
    _eintrag(
        db, belegnr="J-6", beschreibung="STORNO J-4: Testkorrektur",
        art="Einnahme", gruppe_id=original.id,
    )
    tx = BankTransaktion(
        konto_id=konto_id, import_id=import_id, datum=date(2026, 1, 10), betrag=Decimal("-119.00"),
        verwendungszweck="Test", journal_id=original.id,
    )
    db.add(tx)
    db.commit()

    ergebnis = journal_verknuepfen(tx.id, JournalVerknuepfenRequest(journal_id=neu.id), db)

    assert ergebnis.journal_id == neu.id
