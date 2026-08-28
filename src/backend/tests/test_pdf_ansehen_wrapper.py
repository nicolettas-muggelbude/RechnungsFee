"""
Issue #371 (Community-Report, WebKitGTK/Linux): Die "Ansehen"-Ansicht öffnete sich in
einem separaten nativen WebviewWindow als weiße Seite. Ursache: das Frontend lud das PDF
per fetch() im Hauptfenster, erzeugte daraus eine blob:-URL und übergab die an ein neues
Fenster - blob:-URLs sind an das erzeugende Dokument gebunden und können von einem
separaten Fenster/Prozess nicht aufgelöst werden. Der neue Endpunkt liefert stattdessen
eine echte HTML-Seite, die das neue Fenster eigenständig laden kann; der iframe darin
bettet den unveränderten bestehenden PDF-Endpunkt ein.

Nutzer-Folgefund nach dem #371-Fix: "Ansehen" einer bereits archivierten Rechnung zeigte
eine andere Vorlage/kein QR-Code, obwohl das tatsächlich archivierte Original mit QR-Code
erzeugt worden war - weil nur_ansehen=True bislang IMMER frisch aus aktuellen Einstellungen/
Snapshot neu gerendert hat (Ausnahme nur für stornierte Rechnungen), statt das echte
archivierte Original zu zeigen. Getestet in test_ansehen_zeigt_echtes_original_...
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import rechnung_als_pdf, rechnung_pdf_ansehen_wrapper, _absender_snapshot, create_rechnung
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate
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


def test_ansehen_zeigt_echtes_original_auch_nach_geaenderten_einstellungen(db):
    """Kernfehler aus dem Nutzer-Feedback: Ansehen darf nach dem Archivieren nie eine
    andere Vorlage/andere Einstellungen zeigen als beim ursprünglichen Drucken - auch
    dann nicht, wenn die Unternehmenseinstellungen sich seitdem geändert haben."""
    unt = db.query(Unternehmen).first()
    unt.pdf_vorlage = 1
    unt.qr_zahlung_aktiv = True
    unt.iban = "DE02120300000000202051"
    db.commit()

    payload = RechnungCreate(
        typ="ausgang", datum=date(2026, 1, 5), partner_freitext="Testkunde",
        positionen=[RechnungspositionCreate(beschreibung="Beratung", menge=Decimal("1"), einheit="Stk.", netto="100.00", ust_satz="19")],
    )
    resp = create_rechnung(payload, db)
    rechnung = db.query(Rechnung).filter(Rechnung.id == resp.id).first()
    rechnung.ist_entwurf = False
    rechnung.absender_snapshot = _absender_snapshot(db)
    db.commit()

    original = rechnung_als_pdf(rechnung.id, db=db)  # archiviert original_pdf_pfad

    # Einstellungen jetzt ändern - simuliert einen späteren Wechsel auf Standard-Vorlage/kein QR
    unt.pdf_vorlage = 0
    unt.qr_zahlung_aktiv = False
    db.commit()

    ansehen = rechnung_als_pdf(rechnung.id, nur_ansehen=True, db=db)

    assert ansehen.body == original.body
