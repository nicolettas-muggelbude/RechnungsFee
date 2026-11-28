"""
Issue #470: Zahlungsart „Privat bezahlt“ - Betriebsausgabe aus privaten Mitteln (Einlage).
- Betriebsausgabe und Vorsteuer wie gebucht, zusätzlich brutto als Einlage in Hinweiszeile 107
  (Vordruck 2026: 108); Storno hebt die Einlage wieder auf
- DATEV-Gegenkonto = Konto der Kategorie „Privateinlage“ (SKR03 1890 / SKR04 2180)
- Kassenbestand unberührt
- nur bei Ausgaben bzw. beim Bezahlen einer Eingangsrechnung
"""
import asyncio
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from api.datev import _gegenkonto, datev_buchungsstapel
from api.euer import _berechne_euer
from api.journal import create_eintrag, storno_eintrag
from api.schemas import StornoRequest
from api.rechnungen import zahlung_bar_erstellen
from api.schemas import JournalEintragCreate
from api.schemas_rechnungen import BarZahlungCreate
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Rechnung, Rechnungsposition, Unternehmen
from database.seed import seed_kategorien


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    s.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O", kontenrahmen="SKR03",
                      geschaeftsjahr_beginn=1, datev_beraternummer="1", datev_mandantennummer="1",
                      datev_konto_bank="1200"))
    seed_kategorien(s)
    s.commit()
    yield s
    s.close()


def _kat(db, name):
    return db.query(Kategorie).filter(Kategorie.name == name).one()


def _ausgabe(db, zahlungsart="Privat", art="Ausgabe"):
    return create_eintrag(JournalEintragCreate(
        datum=date(2026, 3, 1), beschreibung="Fachbuch privat bezahlt", art=art, zahlungsart=zahlungsart,
        kategorie_id=_kat(db, "Sonstige Betriebsausgaben").id, brutto_betrag=Decimal("119.00"),
        ust_satz=Decimal("19"), vorsteuerabzug=True), db)


def test_euer_einlage_und_betriebsausgabe(db):
    _ausgabe(db)
    euer = _berechne_euer(2026, db)
    assert euer["summe_ausgaben"] == Decimal("119.00")      # 100 netto (60) + 19 Vorsteuer (57)
    assert euer["zeilen"][107] == Decimal("119.00")          # Einlage brutto


def test_storno_hebt_einlage_auf(db):
    e = _ausgabe(db)
    storno_eintrag(e.id, StornoRequest(grund="Test"), db)
    euer = _berechne_euer(2026, db)
    assert euer["zeilen"].get(107, Decimal("0")) == Decimal("0")


def test_datev_gegenkonto_privateinlage_und_kasse_unberuehrt(db):
    e = _ausgabe(db)
    j = db.query(Journaleintrag).get(e.id)
    unt = db.query(Unternehmen).one()
    assert _gegenkonto(j, unt, db) == _kat(db, "Privateinlage").konto_skr03
    bar = db.query(func.count(Journaleintrag.id)).filter(Journaleintrag.zahlungsart == "Bar").scalar()
    assert bar == 0


def test_nur_bei_ausgaben(db):
    with pytest.raises(HTTPException) as exc:
        _ausgabe(db, art="Einnahme")
    assert exc.value.status_code == 422


def test_eingangsrechnung_privat_bezahlen(db):
    kat = _kat(db, "Sonstige Betriebsausgaben")
    r = Rechnung(typ="eingang", rechnungsnummer="ER-1", datum=date(2026, 3, 1), partner_freitext="Händler",
                 netto_gesamt=Decimal("100"), ust_gesamt=Decimal("19"), brutto_gesamt=Decimal("119"),
                 ist_entwurf=False, kategorie_id=kat.id)
    db.add(r)
    db.flush()
    db.add(Rechnungsposition(rechnung_id=r.id, position_nr=1, beschreibung="Buch", menge=Decimal("1"),
                             netto=Decimal("100"), ust_satz=Decimal("19"), brutto=Decimal("119"), kategorie_id=kat.id))
    db.commit()
    zahlung_bar_erstellen(r.id, BarZahlungCreate(datum=date(2026, 3, 2), zahlungsart="Privat", kategorie_id=kat.id), db)
    db.refresh(r)
    assert r.zahlungsstatus == "bezahlt"
    assert _berechne_euer(2026, db)["zeilen"][107] == Decimal("119.00")

    aus = Rechnung(typ="ausgang", rechnungsnummer="RE-1", datum=date(2026, 3, 1), partner_freitext="Kunde",
                   netto_gesamt=Decimal("10"), ust_gesamt=Decimal("0"), brutto_gesamt=Decimal("10"), ist_entwurf=False)
    db.add(aus)
    db.commit()
    with pytest.raises(HTTPException) as exc:
        zahlung_bar_erstellen(aus.id, BarZahlungCreate(datum=date(2026, 3, 2), zahlungsart="Privat"), db)
    assert exc.value.status_code == 422
