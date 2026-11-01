"""
Issue #486-Folgefund: Split-Zahlung einer Eingangsrechnung rechnete jede Zeile mit dem
Standardsatz ihrer KATEGORIE statt mit dem Satz ihrer POSITION. Eine 0-%-Position auf
„Wareneinkauf Nicht-EU“ (Standard 19 %) bekam dadurch 19 % Vorsteuer herausgerechnet
(20 € brutto → 16,81 € netto + 3,19 € Vorsteuer, obwohl keine USt angefallen war).
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import zahlung_bar_erstellen
from api.schemas_rechnungen import BarZahlungCreate, ZahlungSplitPosition
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Rechnung, Rechnungsposition, Unternehmen

D = Decimal


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Test", strasse="X", hausnummer="1", plz="12345", ort="Y"))
    session.add(Kategorie(name="Wareneinkauf Nicht-EU", kontenart="Aufwand", konto_skr03="3200",
                          konto_skr04="5200", euer_zeile=27, vorsteuer_prozent=100, ust_satz_standard=19))
    session.commit()
    yield session
    session.close()


def _rechnung(db) -> tuple[Rechnung, Kategorie]:
    """Exakt der Fall aus dem Screenshot: ER-250005 mit einer 19-%- und einer 0-%-Position."""
    kat = db.query(Kategorie).one()
    r = Rechnung(
        typ="eingang", rechnungsnummer="ER-250005", datum=date(2025, 11, 1),
        netto_gesamt=D("28.40"), ust_gesamt=D("1.60"), brutto_gesamt=D("30.00"),
        ist_entwurf=False, zahlungsstatus="offen", bezahlt_betrag=D("0.00"),
    )
    db.add(r)
    db.flush()
    for nr, (text, satz, netto, ust) in enumerate(
        [("Wareneinkauf Nicht EU 19%", "19", "8.40", "1.60"), ("Wareneinkauf Nicht EU 0%", "0", "20.00", "0.00")],
        start=1,
    ):
        db.add(Rechnungsposition(
            rechnung_id=r.id, position_nr=nr, beschreibung=text, menge=D("1"), einheit="Stk.",
            netto=D(netto), ust_satz=D(satz), ust_betrag=D(ust), brutto=D(netto) + D(ust), kategorie_id=kat.id,
        ))
    db.commit()
    db.refresh(r)
    return r, kat


def _split_zahlung(db, r, kat, mit_position=True):
    p19, p0 = sorted(r.positionen, key=lambda p: p.position_nr)
    split = [
        ZahlungSplitPosition(kategorie_id=kat.id, betrag=D("10.00"), beschreibung=p19.beschreibung,
                             position_id=p19.id if mit_position else None),
        ZahlungSplitPosition(kategorie_id=kat.id, betrag=D("20.00"), beschreibung=p0.beschreibung,
                             position_id=p0.id if mit_position else None),
    ]
    zahlung_bar_erstellen(r.id, BarZahlungCreate(datum=date(2025, 11, 1), zahlungsart="Bank", split=split), db)
    return {e.beschreibung: e for e in db.query(Journaleintrag).all()}


def test_split_nutzt_ust_satz_der_position(db):
    r, kat = _rechnung(db)
    e = _split_zahlung(db, r, kat)

    null = e["Wareneinkauf Nicht EU 0%"]
    assert null.ust_satz == D("0")
    assert null.netto_betrag == D("20.00")
    assert null.ust_betrag == D("0.00")
    assert null.vorsteuer_betrag == D("0.00")

    neunzehn = e["Wareneinkauf Nicht EU 19%"]
    assert neunzehn.ust_satz == D("19")
    assert neunzehn.netto_betrag == D("8.40")
    assert neunzehn.vorsteuer_betrag == D("1.60")


def test_ohne_position_id_bleibt_kategorie_standardsatz(db):
    """Ältere Clients ohne position_id: unverändertes Verhalten (Kategorie-Standardsatz)."""
    r, kat = _rechnung(db)
    e = _split_zahlung(db, r, kat, mit_position=False)
    assert e["Wareneinkauf Nicht EU 0%"].ust_satz == D("19")
