"""
Regressionstests für Issue #387: Bestellnummer des Kunden (BT-13).

Deckt ab:
- Direktes Anlegen/Ändern einer Ausgangsrechnung mit Bestellnummer.
- Propagation durch die Dokumentenkette (Angebot -> Rechnung, Angebot -> Auftrag -> Rechnung).
- ZUGFeRD-Mapping auf BT-13 (BuyerOrderReferencedDocument), inkl. "kein Platzhalter wenn leer".
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import (
    auftrag_aus_angebot,
    create_rechnung,
    rechnung_aus_angebot,
    rechnung_aus_auftrag,
    update_rechnung,
)
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate, RechnungUpdate
from database.connection import Base
from database.models import Rechnung, Unternehmen
from utils.zugferd import generate_zugferd_xml

UNTERNEHMEN = {
    "firmenname": "Testfirma GmbH",
    "strasse": "Teststraße", "hausnummer": "1", "plz": "12345", "ort": "Teststadt",
    "land": "DE", "steuernummer": "12/345/67890", "ust_idnr": "",
    "ist_kleinunternehmer": False,
}


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(
        firmenname="Testfirma GmbH", strasse="Teststraße", hausnummer="1",
        plz="12345", ort="Teststadt", steuernummer="12/345/67890",
    ))
    session.commit()
    yield session
    session.close()


def _angebot_daten(**kwargs) -> RechnungCreate:
    defaults = dict(
        typ="ausgang", dokument_typ="Angebot", datum=date(2026, 8, 1), ist_entwurf=False,
        partner_freitext="Testkunde GmbH",
        kunden_bestellnummer="PO-12345",
        positionen=[RechnungspositionCreate(beschreibung="Beratung", menge=Decimal("1"), netto=Decimal("100.00"), ust_satz=Decimal("19"))],
    )
    defaults.update(kwargs)
    return RechnungCreate(**defaults)


def test_direktes_anlegen_und_aendern(db):
    resp = create_rechnung(_angebot_daten(dokument_typ="Rechnung", ist_entwurf=True), db)
    assert resp.kunden_bestellnummer == "PO-12345"

    aktualisiert = update_rechnung(resp.id, RechnungUpdate(kunden_bestellnummer="PO-99999"), db)
    assert aktualisiert.kunden_bestellnummer == "PO-99999"


def test_propagation_angebot_zu_rechnung(db):
    angebot = create_rechnung(_angebot_daten(), db)
    rechnung = rechnung_aus_angebot(angebot.id, db)
    assert rechnung.kunden_bestellnummer == "PO-12345"


def test_propagation_angebot_auftrag_rechnung_kette(db):
    angebot = create_rechnung(_angebot_daten(), db)
    auftrag = auftrag_aus_angebot(angebot.id, db)
    assert auftrag.kunden_bestellnummer == "PO-12345"

    rechnung = rechnung_aus_auftrag(auftrag.id, db)
    assert rechnung.kunden_bestellnummer == "PO-12345"


def test_zugferd_bt13_wird_gesetzt_wenn_vorhanden(db):
    resp = create_rechnung(_angebot_daten(dokument_typ="Rechnung"), db)
    rechnung = db.query(Rechnung).filter(Rechnung.id == resp.id).first()

    xml = generate_zugferd_xml(rechnung, UNTERNEHMEN).decode("utf-8")

    assert "<ram:BuyerOrderReferencedDocument>" in xml
    assert "<ram:IssuerAssignedID>PO-12345</ram:IssuerAssignedID>" in xml


def test_zugferd_kein_platzhalter_wenn_keine_bestellnummer(db):
    resp = create_rechnung(_angebot_daten(dokument_typ="Rechnung", kunden_bestellnummer=None), db)
    rechnung = db.query(Rechnung).filter(Rechnung.id == resp.id).first()

    xml = generate_zugferd_xml(rechnung, UNTERNEHMEN).decode("utf-8")

    assert "BuyerOrderReferencedDocument" not in xml
