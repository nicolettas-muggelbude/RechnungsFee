"""
Regressionstest für Issue #424.

Ein Kleinunternehmer (§19 UStG) darf die beim Einkauf gezahlte Vorsteuer nicht abziehen - der
reale USt-Satz des Lieferanten bleibt dabei erhalten (Issue #397), nur vorsteuerabzug wird
serverseitig hart auf False erzwungen (journal.py::_felder_aus_data()). Dadurch ist
journal.netto_betrag (100 €) bei einer 119-€-Ausgabe kleiner als der tatsächliche wirtschaftliche
Aufwand - die nicht erstattungsfähigen 19 € USt sind für den Kleinunternehmer ein echter,
dauerhafter Kostenbestandteil und keine durchlaufende Vorsteuerforderung.

_berechne_euer() (api/euer.py) und _ausgabe_netto() (api/cockpit.py) summierten Ausgaben-Zeilen
aber bisher ausschließlich über netto_betrag - die 19 € verschwanden komplett aus EÜR, GuV und
Dashboard-Gewinnberechnung (zeile 57 "abziehbare Vorsteuer" bleibt korrekt 0, da gar kein
Vorsteuerabzug stattfindet - aber nirgendwo sonst wird der Betrag nachgetragen). Der ausgewiesene
Gewinn war dadurch um genau den nicht abzugsfähigen USt-Anteil zu hoch.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.cockpit import _ausgabe_netto
from api.euer import _berechne_euer, _berechne_euer_kategorien
from database.connection import Base
from database.models import Journaleintrag, Kategorie


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _kleinunternehmer_ausgabe(db, kat_id: int) -> Journaleintrag:
    """Exaktes Szenario aus Issue #424: Büromaterial 119 € brutto, Kleinunternehmer -
    kein Vorsteuerabzug (journal.py::_felder_aus_data() erzwingt das serverseitig)."""
    e = Journaleintrag(
        datum=date(2025, 3, 1), belegnr="B1", beschreibung="Büromaterial",
        kategorie_id=kat_id, zahlungsart="Bank", art="Ausgabe",
        netto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        vorsteuerabzug=False, vorsteuer_betrag=Decimal("0.00"), brutto_betrag=Decimal("119.00"),
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def test_euer_zeile_zeigt_vollen_bruttobetrag_ohne_vorsteuerabzug(db):
    kat = Kategorie(name="Bürobedarf", kontenart="Aufwand", euer_zeile=51, vorsteuer_prozent=100)
    db.add(kat)
    db.commit()
    _kleinunternehmer_ausgabe(db, kat.id)

    erg = _berechne_euer(2025, db)
    assert erg["zeilen"][51] == Decimal("119.00")
    assert erg["summe_ausgaben"] == Decimal("119.00")
    assert erg["zeilen"].get(57, Decimal("0.00")) == Decimal("0.00")


def test_euer_kategorien_zeigt_vollen_bruttobetrag_ohne_vorsteuerabzug(db):
    kat = Kategorie(name="Bürobedarf", kontenart="Aufwand", euer_zeile=51, vorsteuer_prozent=100)
    db.add(kat)
    db.commit()
    _kleinunternehmer_ausgabe(db, kat.id)

    erg = _berechne_euer_kategorien(2025, db)
    assert erg[51]["Bürobedarf"] == Decimal("119.00")


def test_cockpit_ausgabe_netto_zeigt_vollen_bruttobetrag_ohne_vorsteuerabzug(db):
    kat = Kategorie(name="Bürobedarf", kontenart="Aufwand", euer_zeile=51, vorsteuer_prozent=100)
    db.add(kat)
    db.commit()
    e = _kleinunternehmer_ausgabe(db, kat.id)

    assert _ausgabe_netto(e, kat) == Decimal("119.00")


def test_voller_vorsteuerabzug_bleibt_unveraendert_bei_netto(db):
    """Regressionsschutz: eine normale (nicht Kleinunternehmer-)Ausgabe mit vollem
    Vorsteuerabzug darf weiterhin nur mit dem Nettobetrag in die EÜR einfließen."""
    kat = Kategorie(name="Bürobedarf", kontenart="Aufwand", euer_zeile=51, vorsteuer_prozent=100)
    db.add(kat)
    db.commit()
    e = Journaleintrag(
        datum=date(2025, 3, 1), belegnr="B1", beschreibung="Büromaterial",
        kategorie_id=kat.id, zahlungsart="Bank", art="Ausgabe",
        netto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        vorsteuerabzug=True, vorsteuer_betrag=Decimal("19.00"), brutto_betrag=Decimal("119.00"),
    )
    db.add(e)
    db.commit()

    erg = _berechne_euer(2025, db)
    assert erg["zeilen"][51] == Decimal("100.00")
    assert erg["zeilen"].get(57) == Decimal("19.00")


def test_storno_einer_kleinunternehmer_ausgabe_hebt_sich_vollstaendig_auf(db):
    """Die Storno-Gegenbuchung (art gespiegelt, vorsteuer_betrag negiert) muss die
    Original-Ausgabe exakt auf 0 zurückführen, nicht nur um den Netto-Anteil."""
    kat = Kategorie(name="Bürobedarf", kontenart="Aufwand", euer_zeile=51, vorsteuer_prozent=100)
    db.add(kat)
    db.commit()
    _kleinunternehmer_ausgabe(db, kat.id)
    storno = Journaleintrag(
        datum=date(2025, 3, 2), belegnr="B2", beschreibung="STORNO B1: Testkorrektur",
        kategorie_id=kat.id, zahlungsart="Bank", art="Einnahme",
        netto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        vorsteuerabzug=False, vorsteuer_betrag=Decimal("0.00"), brutto_betrag=Decimal("119.00"),
    )
    db.add(storno)
    db.commit()

    erg = _berechne_euer(2025, db)
    assert erg["zeilen"].get(51, Decimal("0.00")) == Decimal("0.00")
