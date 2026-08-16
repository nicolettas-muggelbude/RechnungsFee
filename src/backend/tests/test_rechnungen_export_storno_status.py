"""
Regressionstest für Issue #352.

Bug: Im Rechnungslisten-Export (PDF und CSV, "Offene-Posten-Liste") wurden stornierte
Rechnungen weiterhin als "offen" gelistet, inkl. eines offenen Betrags. Ursache: storniert ist
ein eigenes Flag (Rechnung.storniert) und keine Ausprägung von zahlungsstatus - der Export las
aber nur zahlungsstatus, das nach einem Storno unverändert auf dem Stand von vorher stehen
bleibt (z.B. weiterhin "offen"). Gleiches Problem betraf Entwürfe.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import _offen_betrag, _status_anzeige, rechnungen_export
from api.schemas_rechnungen import RechnungResponse
from database.connection import Base
from database.models import Rechnung


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _rechnung(db, nr: str, zahlungsstatus: str, ist_entwurf=False, storniert=False) -> Rechnung:
    r = Rechnung(
        typ="ausgang", rechnungsnummer=nr, datum=date(2026, 1, 15),
        brutto_gesamt=Decimal("119.00"), netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("19.00"),
        bezahlt_betrag=Decimal("0.00"),
        zahlungsstatus=zahlungsstatus, ist_entwurf=ist_entwurf, storniert=storniert,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def test_stornierte_rechnung_zeigt_status_storniert_statt_zahlungsstatus(db):
    r = _rechnung(db, "RE-1", "offen", storniert=True)
    resp = RechnungResponse.from_orm_extended(r)
    assert _status_anzeige(resp) == "storniert"


def test_stornierte_rechnung_hat_keinen_offenen_betrag(db):
    r = _rechnung(db, "RE-1", "offen", storniert=True)
    resp = RechnungResponse.from_orm_extended(r)
    assert _offen_betrag(resp) == Decimal("0")


def test_entwurf_zeigt_status_entwurf(db):
    r = _rechnung(db, "RE-2", "offen", ist_entwurf=True)
    resp = RechnungResponse.from_orm_extended(r)
    assert _status_anzeige(resp) == "entwurf"
    assert _offen_betrag(resp) == Decimal("0")


def test_normale_offene_rechnung_unveraendert(db):
    r = _rechnung(db, "RE-3", "offen")
    resp = RechnungResponse.from_orm_extended(r)
    assert _status_anzeige(resp) == "offen"
    assert _offen_betrag(resp) == Decimal("119.00")


def test_csv_export_zeigt_storniert_nicht_offen(db):
    _rechnung(db, "RE-4", "offen", storniert=True)
    response = rechnungen_export(
        typ=None, zahlungsstatus=None, monat=None, datum_von=None, datum_bis=None,
        kunde_id=None, lieferant_id=None, dokument_typ=None, format="csv", db=db,
    )
    inhalt = response.body.decode("utf-8-sig")
    assert "storniert" in inhalt
    zeile = [z for z in inhalt.splitlines() if z.startswith("RE-4")][0]
    assert ";storniert;" in zeile
    assert ";0,00" in zeile.split(";storniert;")[1]
