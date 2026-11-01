"""
Aufschlüsselung der EÜR: Einzelposten je Kategorie mit Rechnungs- und Zahlungsnummer.

Die Kategorie-Aufschlüsselung (/euer/kategorien) liefert je Kategorie die zugrunde liegenden
Journalbuchungen - mit Rechnungsnummer + rechnung_id (Link auf die Rechnung) und Belegnr der
Zahlungsbuchung (Link auf den Zahlungsbeleg). Die EÜR ist nach Ist-Versteuerung berechnet:
die "Zahlungsnummer" ist die Belegnummer der Journalbuchung (Zahlungsdatum).
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.euer import _berechne_euer_kategorien, euer_kategorien
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Rechnung, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Test", strasse="X", hausnummer="1", plz="12345", ort="Y",
                            ist_kleinunternehmer=False))
    session.add(Kategorie(name="Warenverkauf", kontenart="Erlös", konto_skr03="8400",
                          konto_skr04="4400", euer_zeile=15, ust_satz_standard=19))
    session.add(Kategorie(name="Bürobedarf", kontenart="Aufwand", konto_skr03="4925",
                          konto_skr04="6820", euer_zeile=51, ust_satz_standard=19))
    session.commit()
    yield session
    session.close()


def _rechnung(db, nummer: str) -> Rechnung:
    r = Rechnung(typ="ausgang", rechnungsnummer=nummer, datum=date(2025, 2, 1),
                 netto_gesamt=Decimal("0.00"), ust_gesamt=Decimal("0.00"),
                 brutto_gesamt=Decimal("0.00"), ist_entwurf=False)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def test_kategorie_buchungen_mit_rechnungs_und_zahlungsnummer(db):
    """Einnahme mit Rechnungsverknüpfung: Einzelposten zeigt Belegnr. (Zahlung) und Rechnungsnummer."""
    rechnung = _rechnung(db, "RE-2025-0001")
    kat = db.query(Kategorie).filter_by(name="Warenverkauf").one()
    db.add(Journaleintrag(
        datum=date(2025, 2, 10), belegnr="2500010", beschreibung="Zahlung RE-2025-0001",
        kategorie_id=kat.id, zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("1000.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("190.00"),
        brutto_betrag=Decimal("1190.00"), rechnung_id=rechnung.id,
    ))
    db.commit()

    detail = euer_kategorien(2025, db=db)
    zeile15 = next(z for z in detail.zeilen if z.zeile == 15)
    kat_summe = zeile15.kategorien[0]

    assert kat_summe.betrag == Decimal("1000.00")
    assert len(kat_summe.buchungen) == 1
    b = kat_summe.buchungen[0]
    assert b.belegnr == "2500010"                    # Zahlungsnummer (Journalbuchung)
    assert b.rechnungsnummer == "RE-2025-0001"       # Rechnungsnummer
    assert b.rechnung_id == rechnung.id              # Link-Ziel
    assert b.betrag == Decimal("1000.00")


def test_kategorie_buchungen_sortiert_und_ohne_link_ohne_rechnung(db):
    """Ohne Rechnungsverknüpfung bleibt rechnungsnummer leer; Sortierung nach Datum/Belegnr."""
    kat = db.query(Kategorie).filter_by(name="Warenverkauf").one()
    db.add(Journaleintrag(
        datum=date(2025, 3, 5), belegnr="2500020", beschreibung="Bar-Zahlung",
        kategorie_id=kat.id, zahlungsart="Bar", art="Einnahme",
        netto_betrag=Decimal("200.00"), brutto_betrag=Decimal("200.00"),
    ))
    db.add(Journaleintrag(
        datum=date(2025, 1, 15), belegnr="2500005", beschreibung="Anzahlung",
        kategorie_id=kat.id, zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("300.00"), brutto_betrag=Decimal("300.00"),
    ))
    db.commit()

    detail = euer_kategorien(2025, db=db)
    kat_summe = next(z for z in detail.zeilen if z.zeile == 15).kategorien[0]

    assert [(b.belegnr, b.rechnungsnummer) for b in kat_summe.buchungen] == [
        ("2500005", None), ("2500020", None),
    ]
    # Summe der Einzelposten = Kategorie-Summe
    assert sum(b.betrag for b in kat_summe.buchungen) == kat_summe.betrag


def test_vorsteuer_getrennt_je_buchung(db):
    """Ausgabe mit Vorsteuer: Netto-Anteil unter der Kategorie, Vorsteuer-Anteil unter Zeile 57 -
    beide Einzelposten tragen dieselbe Zahlungsnummer (Belegnr)."""
    kat = db.query(Kategorie).filter_by(name="Bürobedarf").one()
    db.add(Journaleintrag(
        datum=date(2025, 4, 2), belegnr="2500030", beschreibung="Büromaterial",
        kategorie_id=kat.id, zahlungsart="Karte", art="Ausgabe",
        netto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        vorsteuerabzug=True, vorsteuer_betrag=Decimal("19.00"), brutto_betrag=Decimal("119.00"),
    ))
    db.commit()

    detail = euer_kategorien(2025, db=db)
    zeile51 = next(z for z in detail.zeilen if z.zeile == 51)
    zeile57 = next(z for z in detail.zeilen if z.zeile == 57)

    assert zeile51.kategorien[0].betrag == Decimal("100.00")
    assert zeile51.kategorien[0].buchungen[0].belegnr == "2500030"
    assert zeile57.kategorien[0].name == "Vorsteuer"
    assert zeile57.kategorien[0].betrag == Decimal("19.00")
    assert zeile57.kategorien[0].buchungen[0].belegnr == "2500030"


def test_kategorie_summen_ohne_beitraege_unverändert(db):
    """Regression: _berechne_euer_kategorien liefert weiterhin nur die Summen (bestehende Tests)."""
    kat = db.query(Kategorie).filter_by(name="Warenverkauf").one()
    rechnung = _rechnung(db, "RE-2025-0002")
    db.add(Journaleintrag(
        datum=date(2025, 5, 1), belegnr="2500040", beschreibung="Zahlung RE-2025-0002",
        kategorie_id=kat.id, zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("500.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("95.00"),
        brutto_betrag=Decimal("595.00"), rechnung_id=rechnung.id,
    ))
    db.commit()

    erg = _berechne_euer_kategorien(2025, db)
    assert erg[15]["Warenverkauf"] == Decimal("500.00")
    # USt des Zahlungseingangs zusätzlich in Zeile 17
    assert erg[17]["Umsatzsteuer"] == Decimal("95.00")
