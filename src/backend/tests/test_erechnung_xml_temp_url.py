"""
Regressionstest für Issue #384 Punkt 4: E-Rechnungs-Import per Drag&Drop einer reinen
XML-Datei (kein PDF) erzeugte nie eine temp_url - im Frontend blieb "datei" dadurch
dauerhaft null und der Button "Rechnung erstellen" tat wirkungslos nichts, ohne jede
Fehlermeldung. Ursache: _temp_dateiendung() (vorher inline "if dateiname.endswith('.pdf')")
kannte nur PDF.
"""
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api.rechnungen as rechnungen_mod
from api.rechnungen import (
    AnalysierePfadRequest,
    _temp_dateiendung,
    analysiere_rechnung_pfad,
    get_temp_pdf,
)
from database.connection import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_temp_dateiendung_erkennt_pdf_und_xml():
    assert _temp_dateiendung("rechnung.pdf", None) == ".pdf"
    assert _temp_dateiendung("rechnung.PDF", None) == ".pdf"
    assert _temp_dateiendung("rechnung.xml", None) == ".xml"
    assert _temp_dateiendung("beliebig", "application/pdf") == ".pdf"
    assert _temp_dateiendung("rechnung.docx", None) is None


def test_analysiere_pfad_xml_erzeugt_temp_url(tmp_path, monkeypatch, db):
    monkeypatch.setattr(rechnungen_mod, "TEMP_DIR", tmp_path / "tmp-uploads")

    minimal_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100">
</rsm:CrossIndustryInvoice>"""
    xml_datei = tmp_path / "eingang.xml"
    xml_datei.write_bytes(minimal_xml)

    ergebnis = analysiere_rechnung_pfad(AnalysierePfadRequest(pfad=str(xml_datei)), db)

    assert ergebnis.temp_url is not None
    assert ergebnis.temp_url.startswith("/rechnungen/temp/")

    token = ergebnis.temp_url.rsplit("/", 1)[-1]
    resp = get_temp_pdf(token)
    assert resp.media_type == "application/xml"


def test_temp_datei_ohne_erkanntes_format_bleibt_ohne_url(tmp_path, monkeypatch, db):
    monkeypatch.setattr(rechnungen_mod, "TEMP_DIR", tmp_path / "tmp-uploads")

    datei = tmp_path / "notiz.txt"
    datei.write_bytes(b"kein Rechnungsformat")

    ergebnis = analysiere_rechnung_pfad(AnalysierePfadRequest(pfad=str(datei)), db)

    assert ergebnis.temp_url is None


def test_get_temp_pdf_liefert_404_fuer_unbekannten_token(tmp_path, monkeypatch):
    monkeypatch.setattr(rechnungen_mod, "TEMP_DIR", tmp_path / "tmp-uploads")
    with pytest.raises(HTTPException) as exc_info:
        get_temp_pdf("00000000-0000-0000-0000-000000000000")
    assert exc_info.value.status_code == 404
