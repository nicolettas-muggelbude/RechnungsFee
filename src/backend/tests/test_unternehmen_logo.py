"""
Regressionstest: unternehmen.logo_pfad wurde als ABSOLUTER Pfad gespeichert (Altfehler,
anders als der Rest der Codebase - original_pdf_pfad/beleg_pdfa_pfad sind bereits relativ
zu APP_DATA_DIR). Nach einem Datenordner-Umzug (Profilmanager-Migration, macOS-Alt-Pfad-
Migration) existiert die Datei nicht mehr am gespeicherten Pfad, obwohl sie unter demselben
Dateinamen im aktuellen UPLOAD_DIR liegt - get_logo() muss sich selbst heilen statt 404 zu
liefern (vom Nutzer beobachtet: /api/unternehmen/logo spammt 404 nach Profil-Migration).
"""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api.unternehmen as unternehmen_modul
from api.unternehmen import get_logo
from database.connection import Base
from database.models import Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_logo_heilt_sich_selbst_nach_verschobenem_datenordner(db, tmp_path, monkeypatch):
    altes_upload_dir = tmp_path / "alt" / "uploads"
    neues_upload_dir = tmp_path / "neu" / "uploads"
    neues_upload_dir.mkdir(parents=True)
    (neues_upload_dir / "logo.png").write_bytes(b"echte-logo-bytes")

    monkeypatch.setattr(unternehmen_modul, "UPLOAD_DIR", neues_upload_dir)

    db.add(Unternehmen(
        firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort",
        logo_pfad=str(altes_upload_dir / "logo.png"),
    ))
    db.commit()

    response = get_logo(db)

    assert response.path == str(neues_upload_dir / "logo.png")
    # Korrigierter Pfad wird dauerhaft in der DB gespeichert, damit der Fallback nur
    # einmal greifen muss.
    unternehmen = db.query(Unternehmen).first()
    assert unternehmen.logo_pfad == str(neues_upload_dir / "logo.png")


def test_logo_ohne_datei_an_altem_oder_neuem_ort_gibt_404(db, tmp_path, monkeypatch):
    monkeypatch.setattr(unternehmen_modul, "UPLOAD_DIR", tmp_path / "neu" / "uploads")

    db.add(Unternehmen(
        firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort",
        logo_pfad=str(tmp_path / "alt" / "uploads" / "logo.png"),
    ))
    db.commit()

    with pytest.raises(HTTPException) as exc:
        get_logo(db)
    assert exc.value.status_code == 404


def test_logo_am_gespeicherten_pfad_vorhanden_kein_selbstheil_noetig(db, tmp_path, monkeypatch):
    monkeypatch.setattr(unternehmen_modul, "UPLOAD_DIR", tmp_path / "uploads")
    logo_pfad = tmp_path / "uploads"
    logo_pfad.mkdir()
    (logo_pfad / "logo.png").write_bytes(b"logo-bytes")

    db.add(Unternehmen(
        firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort",
        logo_pfad=str(logo_pfad / "logo.png"),
    ))
    db.commit()

    response = get_logo(db)
    assert response.path == str(logo_pfad / "logo.png")
