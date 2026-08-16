"""
Regressionstest für Issue #348.

Feature: "Backup beim Beenden" lehnte externe Pfade 1/2 pauschal ab, sobald sie auf dem
Systemlaufwerk lagen (_ist_systemlaufwerk()) - auch wenn der Ordner in Wirklichkeit per
Sync-Client (Dropbox/Proton Drive/...) extern gesichert wird. Neue Bestätigungs-Flags
backup_extern_pfad_1/2_lokal_ok überspringen die Systemlaufwerk-Prüfung gezielt für den
jeweils bestätigten Pfad - Default bleibt sicher (Prüfung greift weiterhin).
"""
from pathlib import Path

import pytest
from sqlalchemy import create_engine

import main
from database.connection import Base
from database.models import Unternehmen


@pytest.fixture
def db_setup(tmp_path, monkeypatch):
    db_path = tmp_path / "rechnungsfee.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "DB_PATH", db_path)
    monkeypatch.setattr(main, "APP_DATA_DIR", tmp_path)

    return engine


def _unternehmen(engine, ziel: Path, lokal_ok: bool) -> None:
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(
        firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort",
        backup_extern_pfad_1=str(ziel), backup_extern_passwort="test-passwort-123",
        backup_extern_pfad_1_lokal_ok=lokal_ok,
    ))
    session.commit()
    session.close()


def test_lokal_ok_bestaetigt_ueberspringt_systemlaufwerk_pruefung(db_setup, tmp_path):
    # Pfad liegt unter tmp_path, NICHT unter /mnt//media//run/media//Volumes -> gilt als
    # "Systemlaufwerk" fuer _ist_systemlaufwerk(), genau der vom Issue beschriebene Fall
    # (z.B. ein lokal per Sync-Client gespiegelter Ordner).
    ziel = tmp_path / "sync-ordner"
    _unternehmen(db_setup, ziel, lokal_ok=True)

    ergebnis = main.backup_erstellen()

    assert ergebnis["extern_konfiguriert"] is True
    assert not ergebnis.get("fehler")
    dateien = list(ziel.glob("*.zip.enc"))
    assert len(dateien) == 1


def test_ohne_bestaetigung_bleibt_systemlaufwerk_gesperrt(db_setup, tmp_path):
    ziel = tmp_path / "sync-ordner-unbestaetigt"
    _unternehmen(db_setup, ziel, lokal_ok=False)

    ergebnis = main.backup_erstellen()

    assert ergebnis["extern_konfiguriert"] is True
    assert not ziel.exists() or not list(ziel.glob("*.zip.enc"))
