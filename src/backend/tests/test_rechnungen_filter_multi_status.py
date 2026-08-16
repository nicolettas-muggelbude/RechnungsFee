"""
Regressionstest für Issue #351 (Filter verbessern).

Der Status-Filter für die Rechnungsliste (list_rechnungen/export) erlaubte bisher nur einen
einzelnen zahlungsstatus-Wert gleichzeitig - "Offen" und "Teilweise bezahlt" ließen sich nicht
kombiniert anzeigen, obwohl das Konzept "hat noch eine offene Restforderung" (istOffen) an
anderer Stelle im Code bereits beide Status zusammenfasst. _rechnungen_gefiltert() akzeptiert
zahlungsstatus jetzt als Liste; entwurf/storniert sind eigene Flags (nicht Teil der
zahlungsstatus-Spalte) und werden deshalb weiterhin separat behandelt, aber per OR mit den
echten Status-Werten verknüpft.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import _rechnungen_gefiltert
from database.connection import Base
from database.models import Rechnung


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def _rechnung(nr: str, zahlungsstatus: str, ist_entwurf=False, storniert=False) -> Rechnung:
        r = Rechnung(
            typ="ausgang", rechnungsnummer=nr, datum=date(2026, 1, 15),
            brutto_gesamt=Decimal("119.00"), netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("19.00"),
            zahlungsstatus=zahlungsstatus, ist_entwurf=ist_entwurf, storniert=storniert,
        )
        session.add(r)
        return r

    _rechnung("RE-1", "offen")
    _rechnung("RE-2", "teilweise")
    _rechnung("RE-3", "bezahlt")
    _rechnung("RE-4", "uneinbringlich")
    _rechnung("RE-5", "offen", ist_entwurf=True)
    _rechnung("RE-6", "offen", storniert=True)
    session.commit()
    yield session
    session.close()


def test_ohne_filter_alle_ausser_entwurf_storniert_sichtbar(db):
    # Kein zahlungsstatus-Filter -> keine Einschränkung auf ist_entwurf/storniert
    ergebnis = _rechnungen_gefiltert(db, zahlungsstatus=None)
    assert {r.rechnungsnummer for r in ergebnis} == {"RE-1", "RE-2", "RE-3", "RE-4", "RE-5", "RE-6"}


def test_einzelner_status_wie_bisher(db):
    ergebnis = _rechnungen_gefiltert(db, zahlungsstatus=["offen"])
    assert {r.rechnungsnummer for r in ergebnis} == {"RE-1"}


def test_offen_und_teilweise_kombiniert(db):
    ergebnis = _rechnungen_gefiltert(db, zahlungsstatus=["offen", "teilweise"])
    assert {r.rechnungsnummer for r in ergebnis} == {"RE-1", "RE-2"}


def test_echte_status_schliessen_entwurf_und_storniert_weiterhin_aus(db):
    # RE-5 (Entwurf) und RE-6 (storniert) haben ebenfalls zahlungsstatus="offen", dürfen aber
    # ohne explizite entwurf/storniert-Auswahl nicht auftauchen (galt schon vor #351).
    ergebnis = _rechnungen_gefiltert(db, zahlungsstatus=["offen"])
    nummern = {r.rechnungsnummer for r in ergebnis}
    assert "RE-5" not in nummern
    assert "RE-6" not in nummern


def test_entwurf_und_offen_kombiniert(db):
    ergebnis = _rechnungen_gefiltert(db, zahlungsstatus=["offen", "entwurf"])
    assert {r.rechnungsnummer for r in ergebnis} == {"RE-1", "RE-5"}


def test_storniert_allein(db):
    ergebnis = _rechnungen_gefiltert(db, zahlungsstatus=["storniert"])
    assert {r.rechnungsnummer for r in ergebnis} == {"RE-6"}


def test_alle_status_gleichzeitig(db):
    ergebnis = _rechnungen_gefiltert(
        db, zahlungsstatus=["offen", "teilweise", "bezahlt", "uneinbringlich", "entwurf", "storniert"]
    )
    assert {r.rechnungsnummer for r in ergebnis} == {"RE-1", "RE-2", "RE-3", "RE-4", "RE-5", "RE-6"}
