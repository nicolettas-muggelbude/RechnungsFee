"""
Issue #566 (v0.7.14): DATEV-Spalte 48 (Kreditoren-/Debitorennummer).
- direkte Ausgabe mit Lieferant → Kreditor des Lieferanten (vorher leer)
- Zahlung auf eine Ausgangsrechnung → Debitor über die Rechnung (vorher leer, Rechnungszahlungen
  tragen kein kunde_id)
- Zahlung auf eine Eingangsrechnung → Kreditor über die Rechnung (unverändert), auch bei einer
  Erstattung (art=Einnahme)
- Storno ohne eigenen Partner → Personenkonto der Originalbuchung (gruppe_id)
- Buchung ohne Partner → leer (unverändert)
"""
import asyncio
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.datev import datev_buchungsstapel
from database.connection import Base
from database.models import Journaleintrag, Kunde, Lieferant, Rechnung, Unternehmen

FELD_48 = 47


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    s.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O", kontenrahmen="SKR03",
                      geschaeftsjahr_beginn=1, datev_beraternummer="1001", datev_mandantennummer="1",
                      datev_konto_bank="1200"))
    s.add_all([Kunde(firmenname="Kunde", debitor_nr="10001"), Lieferant(firmenname="Lieferant", kreditor_nr="70001")])
    s.commit()
    yield s
    s.close()


def _buchung(db, nr, art, **kw) -> Journaleintrag:
    e = Journaleintrag(datum=date(2026, 6, 1), belegnr=nr, beschreibung=nr, zahlungsart="Bank", art=art,
                       netto_betrag=Decimal("100"), ust_satz=Decimal("0"), ust_betrag=Decimal("0"),
                       brutto_betrag=Decimal("100"), konto_skr03="4980" if art == "Ausgabe" else "8400",
                       immutable=True, **kw)
    db.add(e)
    db.commit()
    return e


def _rechnung(db, typ) -> Rechnung:
    k, lf = db.query(Kunde).one(), db.query(Lieferant).one()
    r = Rechnung(typ=typ, rechnungsnummer=f"R-{typ}", datum=date(2026, 5, 1), netto_gesamt=Decimal("100"),
                 ust_gesamt=Decimal("0"), brutto_gesamt=Decimal("100"), ist_entwurf=False,
                 kunde_id=k.id if typ == "ausgang" else None, lieferant_id=lf.id if typ == "eingang" else None)
    db.add(r)
    db.commit()
    return r


def _feld48(db) -> dict[str, str]:
    response = datev_buchungsstapel(von=date(2026, 6, 1), bis=date(2026, 6, 30), mit_belegen=False, db=db)
    data = asyncio.run(_body(response))
    zeilen = data.decode("utf-8-sig").splitlines()[2:]
    return {f[10]: f[FELD_48] for f in (z.split(";") for z in zeilen)}


async def _body(response) -> bytes:
    return b"".join([chunk async for chunk in response.body_iterator])


def test_personenkonten(db):
    k, lf = db.query(Kunde).one(), db.query(Lieferant).one()
    direkt = _buchung(db, "J-AUS", "Ausgabe", lieferant_id=lf.id)
    _buchung(db, "J-EIN", "Einnahme", kunde_id=k.id)
    _buchung(db, "J-RA", "Einnahme", rechnung_id=_rechnung(db, "ausgang").id)
    re_ein = _rechnung(db, "eingang")
    _buchung(db, "J-RE", "Ausgabe", rechnung_id=re_ein.id)
    _buchung(db, "J-ERST", "Einnahme", rechnung_id=re_ein.id)   # Erstattung vom Lieferanten
    _buchung(db, "J-STORNO", "Einnahme", gruppe_id=direkt.id)   # Storno ohne eigenen Lieferanten
    _buchung(db, "J-OHNE", "Ausgabe")

    assert _feld48(db) == {
        "J-AUS": "70001", "J-EIN": "10001", "J-RA": "10001", "J-RE": "70001",
        "J-ERST": "70001", "J-STORNO": "70001", "J-OHNE": "",
    }


def test_storno_im_zeitraum_original_davor(db):
    """Original liegt vor dem Exportzeitraum - das Storno bekommt trotzdem dessen Kreditor."""
    lf = db.query(Lieferant).one()
    original = _buchung(db, "J-ALT", "Ausgabe", lieferant_id=lf.id)
    original.datum = date(2026, 5, 15)
    db.commit()
    _buchung(db, "J-STORNO", "Einnahme", gruppe_id=original.id)
    assert _feld48(db) == {"J-STORNO": "70001"}


def test_journal_filter_lieferant(db):
    """Reiter „Ausgaben“ beim Lieferanten: nur seine direkt gebuchten Ausgaben."""
    from api.journal import list_eintraege
    lf = db.query(Lieferant).one()
    _buchung(db, "J-MIT", "Ausgabe", lieferant_id=lf.id)
    _buchung(db, "J-OHNE", "Ausgabe")
    treffer = list_eintraege(monat=None, datum_von=None, datum_bis=None, kategorie_id=None, art=None,
                             zahlungsart_typ=None, gruppe_id=None, lieferant_id=lf.id, db=db)
    assert [e.belegnr for e in treffer] == ["J-MIT"]
