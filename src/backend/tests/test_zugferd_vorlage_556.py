"""
Issue #556: Mit ZUGFeRD wechselte eine Rechnung in der Vorlage „Sandra grün – Nur für
Kleinunternehmer“ (pdf_vorlage=1) beim Finalisieren ins Standardlayout, weil
generate_zugferd_pdf() fest die Standard-Vorlage nutzte. Jetzt gilt die gewählte Vorlage,
die XML bleibt eingebettet.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import utils.pdf_rechnung as standard_mod
import utils.pdf_rechnung_vorlage1 as vorlage1_mod
import utils.zugferd as zugferd_mod
from database.connection import Base
from database.models import Rechnung, Rechnungsposition

UNT = {
    "firmenname": "Testfirma", "strasse": "Teststraße", "hausnummer": "1", "plz": "12345",
    "ort": "Teststadt", "land": "DE", "steuernummer": "12/345/67890", "ust_idnr": "",
    "ist_kleinunternehmer": True, "iban": "DE02120300000000202051",
}


@pytest.fixture
def rechnung(tmp_path, monkeypatch):
    monkeypatch.setattr(zugferd_mod, "APP_DATA_DIR", tmp_path)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    r = Rechnung(
        typ="ausgang", rechnungsnummer="RE-260001", datum=date(2026, 11, 16), partner_freitext="Kunde",
        netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("0"), brutto_gesamt=Decimal("100.00"),
        ist_entwurf=False, eingabemodus="brutto",
    )
    db.add(r)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=r.id, position_nr=1, beschreibung="Beratung",
        menge=Decimal("1"), netto=Decimal("100.00"), ust_satz=Decimal("0"), brutto=Decimal("100.00"),
    ))
    db.commit()
    db.refresh(r)
    yield r
    db.close()


def _spione(monkeypatch):
    aufrufe = []
    for mod, name in [(standard_mod, "generate_rechnung_pdf"), (vorlage1_mod, "generate_rechnung_pdf_vorlage1")]:
        echt = getattr(mod, name)

        def spion(*a, _echt=echt, _name=name, **kw):
            aufrufe.append((_name, kw.get("mit_output_intent")))
            return _echt(*a, **kw)
        monkeypatch.setattr(mod, name, spion)
    return aufrufe


@pytest.mark.parametrize("vorlage,erwartet", [
    (1, "generate_rechnung_pdf_vorlage1"),
    (0, "generate_rechnung_pdf"),
])
def test_zugferd_nutzt_gewaehlte_vorlage(rechnung, monkeypatch, vorlage, erwartet):
    aufrufe = _spione(monkeypatch)
    pdf = zugferd_mod.generate_zugferd_pdf(rechnung, {**UNT, "pdf_vorlage": vorlage}, ist_netto=False)
    assert aufrufe == [(erwartet, True)]
    assert "xrechnung.xml" in PdfReader(BytesIO(pdf)).attachments


def test_vorlage_parameter_geht_vor(rechnung, monkeypatch):
    aufrufe = _spione(monkeypatch)
    zugferd_mod.generate_zugferd_pdf(rechnung, {**UNT, "pdf_vorlage": 0}, ist_netto=False, vorlage=1)
    assert aufrufe == [("generate_rechnung_pdf_vorlage1", True)]
