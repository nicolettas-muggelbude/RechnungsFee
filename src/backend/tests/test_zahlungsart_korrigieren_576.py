"""
Issue #576: Zahlungsart einer Rechnungszahlung korrigieren. Das Storno läuft mit der alten,
die Neubuchung mit der neuen Zahlungsart - eine versehentlich als Bar gebuchte Kartenzahlung
berichtigt dadurch automatisch die Kasse. Wechsel auf eine Bar-Ausgabe prüft den Kassenbestand.
"""
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from api.rechnungen import ZahlungKorrigieren, zahlung_korrigieren
from database.connection import Base
from database.models import BankImport, BankTemplate, BankTransaktion, Journaleintrag, Konto, Rechnung


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _kasse(db) -> Decimal:
    def summe(art):
        return db.query(func.sum(Journaleintrag.brutto_betrag)).filter(
            Journaleintrag.art == art, Journaleintrag.zahlungsart == "Bar").scalar() or Decimal("0")
    return Decimal(str(summe("Einnahme"))) - Decimal(str(summe("Ausgabe")))


def _zahlung(db, typ, art, zahlungsart, nr="1", konto_id=None):
    r = Rechnung(typ=typ, rechnungsnummer=f"R-{nr}", datum=date(2026, 11, 1), netto_gesamt=Decimal("50"),
                 ust_gesamt=Decimal("0"), brutto_gesamt=Decimal("50"), bezahlt=True,
                 bezahlt_betrag=Decimal("50"), zahlungsstatus="bezahlt", ist_entwurf=False)
    db.add(r)
    db.flush()
    z = Journaleintrag(datum=date(2026, 11, 2), belegnr=f"J-{nr}", beschreibung="Zahlung", zahlungsart=zahlungsart,
                       art=art, netto_betrag=Decimal("50"), ust_satz=Decimal("0"), ust_betrag=Decimal("0"),
                       vorsteuer_betrag=Decimal("0"), brutto_betrag=Decimal("50"), rechnung_id=r.id,
                       immutable=True, konto_id=konto_id)
    db.add(z)
    db.commit()
    return r, z


def _kassenanfang(db, betrag):
    db.add(Journaleintrag(datum=date(2026, 1, 1), belegnr=f"J-0-{betrag}", beschreibung="Kassenanfangsbestand",
                          zahlungsart="Bar", art="Einnahme", netto_betrag=betrag, ust_satz=Decimal("0"),
                          ust_betrag=Decimal("0"), brutto_betrag=betrag, immutable=True))
    db.commit()


def _korrigiere(db, r, z, art):
    zahlung_korrigieren(r.id, z.id, ZahlungKorrigieren(neues_datum=z.datum, neue_zahlungsart=art), db)
    return db.query(Journaleintrag).filter(Journaleintrag.gruppe_id == z.id,
                                           ~Journaleintrag.beschreibung.like("STORNO %")).one()


def test_karte_statt_bar_einnahme_nimmt_betrag_aus_der_kasse(db):
    _kassenanfang(db, Decimal("100"))
    r, z = _zahlung(db, "ausgang", "Einnahme", "Bar")
    assert _kasse(db) == Decimal("150")
    neu = _korrigiere(db, r, z, "Karte")
    assert neu.zahlungsart == "Karte"
    assert _kasse(db) == Decimal("100")
    db.refresh(r)
    assert r.bezahlt_betrag == Decimal("50")


def test_karte_statt_bar_ausgabe_gibt_betrag_an_die_kasse_zurueck(db):
    _kassenanfang(db, Decimal("100"))
    r, z = _zahlung(db, "eingang", "Ausgabe", "Bar")
    assert _kasse(db) == Decimal("50")
    _korrigiere(db, r, z, "Karte")
    assert _kasse(db) == Decimal("100")


def test_wechsel_auf_bar_ausgabe_prueft_kassenbestand(db):
    _kassenanfang(db, Decimal("20"))
    r, z = _zahlung(db, "eingang", "Ausgabe", "Bank")
    with pytest.raises(HTTPException) as e:
        _korrigiere(db, r, z, "Bar")
    assert e.value.status_code == 409 and "Kassenstand" in e.value.detail
    _kassenanfang(db, Decimal("40"))
    _korrigiere(db, r, z, "Bar")
    assert _kasse(db) == Decimal("10")


def test_zahlung_aus_bank_import_zahlungsart_gesperrt_konto_bleibt(db):
    k = Konto(name="Giro", anbieter="Bank", kontoart="giro")
    db.add_all([k, BankTemplate(id="CAMT_XML", name="CAMT", bank="x", format="CAMT", column_mapping="{}")])
    db.flush()
    r, z = _zahlung(db, "ausgang", "Einnahme", "Bank", konto_id=k.id)
    imp = BankImport(konto_id=k.id, template_id="CAMT_XML", dateiname="x.csv")
    db.add(imp)
    db.flush()
    tx = BankTransaktion(konto_id=k.id, import_id=imp.id, datum=z.datum, betrag=Decimal("50"), journal_id=z.id)
    db.add(tx)
    db.commit()
    with pytest.raises(HTTPException) as e:
        _korrigiere(db, r, z, "Bar")
    assert e.value.status_code == 409
    # Datum korrigieren geht weiter - Konto und Bank-Verknüpfung wandern mit
    zahlung_korrigieren(r.id, z.id, ZahlungKorrigieren(neues_datum=date(2026, 11, 3)), db)
    neu = db.query(Journaleintrag).filter(Journaleintrag.datum == date(2026, 11, 3)).one()
    assert neu.konto_id == k.id
    db.refresh(tx)
    assert tx.journal_id == neu.id
