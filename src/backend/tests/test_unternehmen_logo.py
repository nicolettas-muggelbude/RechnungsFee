"""
Regressionstests Firmenlogo-Pfad.

unternehmen.logo_pfad wurde früher als ABSOLUTER Pfad gespeichert - auch im eingefrorenen
absender_snapshot finalisierter Dokumente. Nach einem Datenordner-Umzug (Profilmanager-,
macOS-Migration) oder einem Backup-Import auf einem anderen System (Issue #454: Windows → macOS)
existiert die Datei nicht mehr am gespeicherten Pfad, liegt aber unter demselben Namen im
aktuellen uploads/. get_logo() und die PDF-Erzeugung müssen sie trotzdem finden - auch bei einem
Windows-Pfad, dessen "\\" unter macOS/Linux kein Pfadtrenner ist. Neu gespeichert wird relativ.
"""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api.unternehmen as unternehmen_modul
import utils.logo as logo_modul
from api.unternehmen import get_logo
from database.connection import Base
from database.models import Unternehmen
from utils.logo import logo_datei


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def datenordner(tmp_path, monkeypatch):
    """Aktueller Datenordner mit uploads/logo.png."""
    basis = tmp_path / "neu"
    (basis / "uploads").mkdir(parents=True)
    (basis / "uploads" / "logo.png").write_bytes(b"echte-logo-bytes")
    monkeypatch.setattr(unternehmen_modul, "UPLOAD_DIR", basis / "uploads")
    monkeypatch.setattr(logo_modul, "APP_DATA_DIR", basis)
    return basis


def _unternehmen(db, logo_pfad):
    db.add(Unternehmen(
        firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort",
        logo_pfad=logo_pfad,
    ))
    db.commit()


def test_logo_heilt_sich_selbst_nach_verschobenem_datenordner(db, tmp_path, datenordner):
    _unternehmen(db, str(tmp_path / "alt" / "uploads" / "logo.png"))

    response = get_logo(db)

    assert response.path == str(datenordner / "uploads" / "logo.png")
    # einmalig auf die relative Speicherform umgestellt
    assert db.query(Unternehmen).first().logo_pfad == "uploads/logo.png"


def test_windows_pfad_nach_backup_import_auf_macos_linux(db, datenordner):
    # Issue #454: Backup von Windows, wiederhergestellt auf macOS/Linux
    _unternehmen(db, r"C:\Users\Max\AppData\Roaming\RechnungsFee\profile\Standard\uploads\logo.png")

    response = get_logo(db)

    assert response.path == str(datenordner / "uploads" / "logo.png")
    assert db.query(Unternehmen).first().logo_pfad == "uploads/logo.png"


def test_relativer_pfad(db, datenordner):
    _unternehmen(db, "uploads/logo.png")
    assert get_logo(db).path == str(datenordner / "uploads" / "logo.png")


def test_logo_ohne_datei_gibt_404(db, tmp_path, datenordner):
    (datenordner / "uploads" / "logo.png").unlink()
    _unternehmen(db, str(tmp_path / "alt" / "uploads" / "logo.png"))
    with pytest.raises(HTTPException) as exc:
        get_logo(db)
    assert exc.value.status_code == 404


def test_logo_datei_fuer_snapshot_pfade(datenordner):
    erwartet = datenordner / "uploads" / "logo.png"
    assert logo_datei("/Users/max/Library/Application Support/RechnungsFee/uploads/logo.png") == erwartet
    assert logo_datei(r"C:\x\uploads\logo.png") == erwartet
    assert logo_datei("uploads/logo.png") == erwartet
    assert logo_datei("") is None and logo_datei(None) is None
    assert logo_datei(r"C:\x\uploads\anderes.png") is None


def test_pdf_zeigt_logo_aus_altem_snapshot_pfad(datenordner, monkeypatch):
    """Finalisierte Dokumente haben den alten absoluten Pfad im absender_snapshot eingefroren."""
    from PIL import Image
    Image.new("RGB", (200, 80), "red").save(datenordner / "uploads" / "logo.png")

    from api.pdf_vorlagen import _demo_rechnung, _unt_dict
    from utils.pdf_rechnung import generate_rechnung_pdf
    import utils.pdf_rechnung_base as base

    eingebunden = []
    original_image = base.RechnungPDFBase.image
    monkeypatch.setattr(base.RechnungPDFBase, "image",
                        lambda self, name, *a, **kw: (eingebunden.append(str(name)), original_image(self, name, *a, **kw))[1])

    unt = _unt_dict(None)
    unt["logo_pfad"] = r"C:\Users\Max\AppData\Roaming\RechnungsFee\uploads\logo.png"
    generate_rechnung_pdf(_demo_rechnung(unt), unt)

    assert str(datenordner / "uploads" / "logo.png") in eingebunden
