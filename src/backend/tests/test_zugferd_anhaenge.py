"""
Regressionstests für Issue #383: ZUGFeRD-Anhänge (rechnungsbegleitende Dokumente).

Deckt ab:
- Upload nur möglich wenn unternehmen.zugferd_anhaenge_aktiv gesetzt ist.
- Upload/Löschen nur bei Entwürfen möglich (eingefroren nach Finalisierung).
- Der Anhang landet als AdditionalReferencedDocument mit Base64-Inhalt im ZUGFeRD-XML.
- Ohne Anhänge bleibt das XML wie zuvor unverändert (kein leeres/kaputtes Element).
"""
import asyncio
import base64
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api.rechnungen as rechnungen_mod
import utils.zugferd as zugferd_mod
from api.rechnungen import delete_zugferd_anhang, list_zugferd_anhaenge, upload_zugferd_anhang
from database.connection import Base
from database.models import Beleg, Rechnung, Rechnungsposition, RechnungZugferdAnhang, Unternehmen
from utils.zugferd import generate_zugferd_xml

UNTERNEHMEN_DICT = {
    "firmenname": "Testfirma GmbH",
    "strasse": "Teststraße", "hausnummer": "1", "plz": "12345", "ort": "Teststadt",
    "land": "DE", "steuernummer": "12/345/67890", "ust_idnr": "",
    "ist_kleinunternehmer": False,
}


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(rechnungen_mod, "BELEG_DIR", tmp_path / "uploads" / "belege")
    monkeypatch.setattr(rechnungen_mod, "APP_DATA_DIR", tmp_path)
    monkeypatch.setattr(zugferd_mod, "APP_DATA_DIR", tmp_path)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _rechnung(db, ist_entwurf=True) -> Rechnung:
    r = Rechnung(
        typ="ausgang", rechnungsnummer="RE-1", datum=date(2026, 7, 1), partner_freitext="Testkunde",
        netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("19.00"), brutto_gesamt=Decimal("119.00"),
        ist_entwurf=ist_entwurf,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def _upload_file(inhalt: bytes = b"%PDF-1.4 Testinhalt") -> UploadFile:
    return UploadFile(
        file=BytesIO(inhalt), filename="stundennachweis.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )


def _upload(db, rechnung_id):
    coro = upload_zugferd_anhang(rechnung_id, datei=_upload_file(), bezeichnung="Stundennachweis", db=db)
    return asyncio.run(coro)


def test_upload_ohne_aktivierte_funktion_wird_abgelehnt(db):
    db.add(Unternehmen(firmenname="Testfirma GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    db.commit()
    rechnung = _rechnung(db)

    with pytest.raises(HTTPException) as exc_info:
        _upload(db, rechnung.id)
    assert exc_info.value.status_code == 409
    assert "nicht aktiviert" in exc_info.value.detail


def test_upload_bei_finalisierter_rechnung_wird_abgelehnt(db):
    db.add(Unternehmen(
        firmenname="Testfirma GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort",
        zugferd_anhaenge_aktiv=True,
    ))
    db.commit()
    rechnung = _rechnung(db, ist_entwurf=False)

    with pytest.raises(HTTPException) as exc_info:
        _upload(db, rechnung.id)
    assert exc_info.value.status_code == 409
    assert "Entwürfen" in exc_info.value.detail


def test_upload_liste_und_loeschen(db):
    db.add(Unternehmen(
        firmenname="Testfirma GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort",
        zugferd_anhaenge_aktiv=True,
    ))
    db.commit()
    rechnung = _rechnung(db)

    anhang = _upload(db, rechnung.id)
    assert anhang.bezeichnung == "Stundennachweis"

    liste = list_zugferd_anhaenge(rechnung.id, db)
    assert len(liste) == 1

    delete_zugferd_anhang(rechnung.id, anhang.id, db)
    assert list_zugferd_anhaenge(rechnung.id, db) == []
    assert db.query(Beleg).count() == 0


def test_zugferd_xml_enthaelt_anhang_als_additional_referenced_document(db):
    rechnung = _rechnung(db, ist_entwurf=False)
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Beratung",
        menge=Decimal("1"), netto=Decimal("100.00"), ust_satz=Decimal("19"), brutto=Decimal("119.00"),
    ))
    beleg = Beleg(dateiname="belege/test.pdf", original_name="stundennachweis.pdf", mime_type="application/pdf", dateigroesse=10)
    db.add(beleg)
    db.flush()
    inhalt = b"%PDF-1.4 Testinhalt"
    ziel = zugferd_mod.APP_DATA_DIR / "uploads" / "belege" / "test.pdf"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_bytes(inhalt)

    db.add(RechnungZugferdAnhang(rechnung_id=rechnung.id, beleg_id=beleg.id, bezeichnung="Stundennachweis Juli"))
    db.commit()
    db.refresh(rechnung)

    xml = generate_zugferd_xml(rechnung, UNTERNEHMEN_DICT).decode("utf-8")

    assert "<ram:AdditionalReferencedDocument>" in xml
    assert "<ram:TypeCode>916</ram:TypeCode>" in xml
    assert base64.b64encode(inhalt).decode("ascii") in xml


def _rechnung_mit_anhaengen(db, *namen):
    """Finalisierte Rechnung mit je einem Anhang pro Originalnamen (gleiche Namen erlaubt)."""
    rechnung = _rechnung(db, ist_entwurf=False)
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Beratung",
        menge=Decimal("1"), netto=Decimal("100.00"), ust_satz=Decimal("19"), brutto=Decimal("119.00"),
    ))
    for i, name in enumerate(namen):
        ziel = zugferd_mod.APP_DATA_DIR / "uploads" / "belege" / f"datei{i}.pdf"
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_bytes(f"%PDF-1.4 Inhalt {i}".encode())
        beleg = Beleg(dateiname=f"belege/datei{i}.pdf", original_name=name, mime_type="application/pdf", dateigroesse=10)
        db.add(beleg)
        db.flush()
        db.add(RechnungZugferdAnhang(rechnung_id=rechnung.id, beleg_id=beleg.id, bezeichnung=f"Nachweis {i}"))
    db.commit()
    db.refresh(rechnung)
    return rechnung


def test_xml_verweist_per_uriid_auf_eingebettete_datei(db):
    """Issue #527: URIID #ef=<Dateiname>, doppelte Namen eindeutig gemacht."""
    rechnung = _rechnung_mit_anhaengen(db, "nachweis.pdf", "nachweis.pdf")
    xml = generate_zugferd_xml(rechnung, UNTERNEHMEN_DICT).decode("utf-8")
    assert "<ram:URIID>#ef=nachweis.pdf</ram:URIID>" in xml
    assert "<ram:URIID>#ef=nachweis-2.pdf</ram:URIID>" in xml
    # Base64-Kopie bleibt für Empfänger, die nur die XML lesen
    assert base64.b64encode(b"%PDF-1.4 Inhalt 0").decode("ascii") in xml


def test_pdf_container_enthaelt_anhaenge_als_dateien(db):
    """Issue #527: Anhänge zusätzlich als eigene Dateien im PDF/A-3 (Büroklammer im Viewer)."""
    from pypdf import PdfReader
    rechnung = _rechnung_mit_anhaengen(db, "nachweis.pdf", "nachweis.pdf", "xrechnung.xml")
    pdf = PdfReader(BytesIO(zugferd_mod.generate_zugferd_pdf(rechnung, UNTERNEHMEN_DICT)))
    anhaenge = pdf.attachments
    assert set(anhaenge) == {"xrechnung.xml", "nachweis.pdf", "nachweis-2.pdf", "xrechnung-2.xml"}
    assert anhaenge["nachweis-2.pdf"][0] == b"%PDF-1.4 Inhalt 1"
    assert b"Inhalt 2" not in anhaenge["xrechnung.xml"][0]


def test_pdf_ohne_anhaenge_nur_xml(db):
    from pypdf import PdfReader
    rechnung = _rechnung_mit_anhaengen(db)
    pdf = PdfReader(BytesIO(zugferd_mod.generate_zugferd_pdf(rechnung, UNTERNEHMEN_DICT)))
    assert set(pdf.attachments) == {"xrechnung.xml"}


def test_zugferd_xml_ohne_anhang_bleibt_unveraendert(db):
    rechnung = _rechnung(db, ist_entwurf=False)
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Beratung",
        menge=Decimal("1"), netto=Decimal("100.00"), ust_satz=Decimal("19"), brutto=Decimal("119.00"),
    ))
    db.commit()
    db.refresh(rechnung)

    xml = generate_zugferd_xml(rechnung, UNTERNEHMEN_DICT).decode("utf-8")

    assert "AdditionalReferencedDocument" not in xml
