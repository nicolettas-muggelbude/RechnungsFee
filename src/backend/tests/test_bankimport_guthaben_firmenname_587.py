"""
Regressionstest für Issue #587: auto_buchen crasht im Kundenguthaben-/Lieferantenguthaben-
Matching mit AttributeError, weil `kunde.firma`/`lieferant.firma` gelesen wird, das Modell
aber `firmenname` heißt. Dadurch rollt auto_buchen den ganzen Lauf zurück und die
Rückerstattung wird nie gebucht.

Wichtig: Kunde und Lieferant werden hier als PRIVATPERSON angelegt (nur vorname/nachname,
firmenname=None) - genau der Fall, der in Produktiv-DBs mit echten Kundinnen passiert und
bisher nie getestet war.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.bank_import import auto_buchen
from api.rechnungen import create_rechnung, finalisiere_rechnung, zahlung_bar_erstellen
from database.connection import Base
from database.models import (
    BankImport, BankTemplate, BankTransaktion, Forderung, Kunde, Lieferant, Kategorie, Konto,
    Rechnung, Rechnungsposition, Unternehmen,
)
from api.schemas_rechnungen import BarZahlungCreate, RechnungspositionCreate, RechnungCreate


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    konto = Konto(name="Testkonto", anbieter="Testbank")
    session.add(konto)
    session.flush()
    tmpl = BankTemplate(id="test-tmpl", name="Test", bank="Testbank", format="Standard", column_mapping="{}")
    session.add(tmpl)
    session.flush()
    imp = BankImport(konto_id=konto.id, template_id=tmpl.id, dateiname="test.csv")
    session.add(imp)
    session.commit()
    session.konto_id = konto.id
    session.import_id = imp.id
    yield session
    session.close()


def _privatkunde(db) -> Kunde:
    # PRIVATPERSON: firmenname=None - genau der Produktiv-Fall aus Issue #587
    kunde = Kunde(vorname="Erika", nachname="Muster")
    db.add(kunde)
    db.commit()
    return kunde


def _ausgangsrechnung_mit_guthaben(db, kunde_id: int) -> Rechnung:
    kat = Kategorie(name="Dienstleistung", kontenart="Erlös", konto_skr03="8400", konto_skr04="4000")
    db.add(kat)
    db.commit()
    rechnung = create_rechnung(RechnungCreate(
        typ="ausgang", dokument_typ="Rechnung", datum=date(2026, 3, 1), ist_entwurf=True,
        kunde_id=kunde_id, kategorie_id=kat.id,
        positionen=[RechnungspositionCreate(
            beschreibung="Testleistung", menge=Decimal("1"), netto=Decimal("100.00"), ust_satz=Decimal("0"),
        )],
    ), db)
    finalisiere_rechnung(rechnung.id, db)
    # Überzahlung: 100,50 statt 100,00 -> 0,50 Kundenguthaben
    zahlung_bar_erstellen(rechnung.id, BarZahlungCreate(
        datum=date(2026, 3, 2), zahlungsart="Bar", betrag=Decimal("100.50"),
    ), db)
    db.commit()
    return rechnung


def test_kundenguthaben_matching_privatperson_kein_crash(db):
    """Issue #587: Kunde ohne firmenname darf auto_buchen nicht crashen; die ausgehende
    Transaktion muss als Rückerstattung erkannt und das Guthaben ausgeglichen werden."""
    kunde = _privatkunde(db)
    rechnung = _ausgangsrechnung_mit_guthaben(db, kunde.id)

    guthaben = db.query(Forderung).filter(Forderung.typ == "kundenguthaben").one()
    assert guthaben.status == "offen"
    assert guthaben.betrag == Decimal("0.50")

    tx = BankTransaktion(
        konto_id=db.konto_id, import_id=db.import_id, datum=date(2026, 3, 10),
        betrag=Decimal("-0.50"), partner_name="Erika Muster",
        verwendungszweck="Rücküberweisung",
    )
    db.add(tx)
    db.commit()

    result = auto_buchen(db.konto_id, db.import_id, db)

    db.refresh(tx)
    db.refresh(guthaben)
    assert result.fehler == 0, "auto_buchen darf nicht fehlschlagen (kein Rollback)"
    assert tx.ist_rueckerstattung is True
    assert guthaben.status == "ausgeglichen"


def test_kundenguthaben_matching_keyword_fallback(db):
    """Fallback-Pfad: Keyword im Verwendungszweck reicht ohne Namens-Match."""
    kunde = _privatkunde(db)
    _ausgangsrechnung_mit_guthaben(db, kunde.id)
    guthaben = db.query(Forderung).filter(Forderung.typ == "kundenguthaben").one()

    tx = BankTransaktion(
        konto_id=db.konto_id, import_id=db.import_id, datum=date(2026, 3, 10),
        betrag=Decimal("-0.50"), partner_name=None, verwendungszweck="Rückerstattung",
    )
    db.add(tx)
    db.commit()

    result = auto_buchen(db.konto_id, db.import_id, db)
    db.refresh(tx)
    db.refresh(guthaben)
    assert result.fehler == 0
    assert tx.ist_rueckerstattung is True
    assert guthaben.status == "ausgeglichen"
