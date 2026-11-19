"""
Regressionstests für Issue #546: Bank-Abgleich mit einer Eingangsrechnung, deren Positionen
keine Kategorie haben (vor dem Kategorie-Stichtag finalisiert).

1. Ohne Kategorie bleibt es beim Fehler `keine_kategorie` (Frontend fragt dann nach).
2. Mit im Abgleich gewählter Kategorie wird gebucht und die Kategorie als Hauptkategorie an
   die Rechnung zurückgeschrieben (wie im Dialog „Zahlung buchen“).
3. Eine Hauptkategorie der Rechnung wird auch ohne Positionskategorie genutzt (vorher ignoriert).
4. Die Automatik lässt solche Transaktionen offen statt abzubrechen und alle Buchungen des
   Laufs zurückzurollen.
"""
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.bank_import import _buche_pfad_a, auto_buchen
from database.connection import Base
from database.models import (
    BankImport, BankTemplate, BankTransaktion, Kategorie, Konto, Rechnung, Rechnungsposition,
    Unternehmen,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    konto = Konto(name="Testkonto", anbieter="Testbank")
    session.add(konto)
    session.flush()
    tmpl = BankTemplate(id="test-tmpl", name="Test", bank="Testbank", format="Standard", column_mapping="{}")
    session.add(tmpl)
    session.flush()
    imp = BankImport(konto_id=konto.id, template_id=tmpl.id, dateiname="test.csv")
    session.add(imp)
    session.add(Kategorie(
        name="Bürobedarf", kontenart="Aufwand", konto_skr03="4930", konto_skr04="6815",
        vorsteuer_prozent=100, ust_satz_standard=19,
    ))
    session.commit()
    session.konto_id = konto.id
    session.import_id = imp.id
    yield session
    session.close()


def _kat(db) -> Kategorie:
    return db.query(Kategorie).filter(Kategorie.name == "Bürobedarf").first()


def _rechnung(db, kategorie_id=None) -> Rechnung:
    r = Rechnung(
        typ="eingang", rechnungsnummer="ER-260001", externe_belegnr="L-4711", datum=date(2026, 3, 1),
        brutto_gesamt=Decimal("119.00"), netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("19.00"),
        ist_entwurf=False, zahlungsstatus="offen", bezahlt_betrag=Decimal("0.00"), kategorie_id=kategorie_id,
    )
    db.add(r)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=r.id, position_nr=1, beschreibung="Papier", menge=Decimal("1"), einheit="Stk.",
        netto=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"), brutto=Decimal("119.00"),
    ))
    db.commit()
    db.refresh(r)
    return r


def _tx(db) -> BankTransaktion:
    tx = BankTransaktion(
        konto_id=db.konto_id, import_id=db.import_id, datum=date(2026, 3, 5), betrag=Decimal("-119.00"),
        verwendungszweck="ER-260001 L-4711",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def test_ohne_kategorie_bleibt_fehler(db):
    r = _rechnung(db)
    with pytest.raises(HTTPException) as exc:
        _buche_pfad_a(db, _tx(db), r)
    assert exc.value.detail == "keine_kategorie"


def test_gewaehlte_kategorie_wird_gebucht_und_gespeichert(db):
    r = _rechnung(db)
    kat = _kat(db)
    eintrag, _ = _buche_pfad_a(db, _tx(db), r, kategorie_id=kat.id)
    db.commit()
    db.refresh(eintrag)
    db.refresh(r)
    assert eintrag.kategorie_id == kat.id
    assert eintrag.vorsteuer_betrag == Decimal("19.00")
    assert r.kategorie_id == kat.id
    assert r.zahlungsstatus == "bezahlt"


def test_unbekannte_kategorie_404(db):
    r = _rechnung(db)
    with pytest.raises(HTTPException) as exc:
        _buche_pfad_a(db, _tx(db), r, kategorie_id=99999)
    assert exc.value.status_code == 404


def test_hauptkategorie_der_rechnung_wird_genutzt(db):
    kat = _kat(db)
    r = _rechnung(db, kategorie_id=kat.id)
    eintrag, _ = _buche_pfad_a(db, _tx(db), r)
    db.commit()
    db.refresh(eintrag)
    assert eintrag.kategorie_id == kat.id


def test_automatik_laesst_rechnung_ohne_kategorie_offen(db):
    r = _rechnung(db)
    tx = _tx(db)
    ergebnis = auto_buchen(db.konto_id, db.import_id, db)
    db.refresh(tx)
    db.refresh(r)
    assert tx.journal_id is None
    assert r.zahlungsstatus == "offen"
    assert ergebnis.fehler == 0
