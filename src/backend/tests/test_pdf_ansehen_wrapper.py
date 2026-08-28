"""
Issue #371 (Community-Report, WebKitGTK/Linux): Die "Ansehen"-Ansicht öffnete sich in
einem separaten nativen WebviewWindow als weiße Seite. Ursache: das Frontend lud das PDF
per fetch() im Hauptfenster, erzeugte daraus eine blob:-URL und übergab die an ein neues
Fenster - blob:-URLs sind an das erzeugende Dokument gebunden und können von einem
separaten Fenster/Prozess nicht aufgelöst werden. Der neue Endpunkt liefert stattdessen
eine echte HTML-Seite, die das neue Fenster eigenständig laden kann; der iframe darin
bettet den unveränderten bestehenden PDF-Endpunkt ein.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import rechnung_pdf_ansehen_wrapper
from database.connection import Base
from database.models import Rechnung, Unternehmen
from fastapi import HTTPException


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    session.commit()
    yield session
    session.close()


def _rechnung(db) -> Rechnung:
    r = Rechnung(
        typ="ausgang", rechnungsnummer="RE-2026-42", datum=date(2026, 1, 5),
        dokument_typ="Rechnung", brutto_gesamt=Decimal("119.00"),
        netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("19.00"),
        ist_entwurf=False, zahlungsstatus="offen", bezahlt_betrag=Decimal("0.00"),
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def test_wrapper_enthaelt_rechnungsnummer_und_iframe_auf_pdf_endpunkt(db):
    r = _rechnung(db)

    resp = rechnung_pdf_ansehen_wrapper(r.id, db)

    body = resp.body.decode("utf-8")
    assert "RE-2026-42" in body
    assert f'src="/api/rechnungen/{r.id}/pdf?nur_ansehen=true"' in body
    assert resp.media_type == "text/html"


def test_wrapper_blockiert_strg_p_und_strg_s(db):
    """Kernfunktion des Nur-Ansehen-Wrappers muss beim Serverseitig-Rendern erhalten
    bleiben - Drucken/Speichern per Tastenkürzel wird per JS abgefangen."""
    r = _rechnung(db)

    resp = rechnung_pdf_ansehen_wrapper(r.id, db)

    body = resp.body.decode("utf-8")
    assert "e.key === 'p'" in body
    assert "e.key === 's'" in body
    assert "window.print = function" in body


def test_unbekannte_rechnung_404(db):
    with pytest.raises(HTTPException) as exc_info:
        rechnung_pdf_ansehen_wrapper(999999, db)
    assert exc_info.value.status_code == 404
