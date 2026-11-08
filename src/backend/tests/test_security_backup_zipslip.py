"""
Regressionstests Security-Audit F1 (ZIP-Slip im Backup-Restore).

Bug: _prüfe_wiederherstellung() schrieb jeden Eintrag unter „uploads/“ nach
uploads_dir / rel, ohne den Pfad zu prüfen. Ein präpariertes Backup mit
„uploads/../../.config/autostart/x.desktop“ oder „uploads//absoluter/pfad“ legte beim
nächsten Start Dateien außerhalb des Datenordners ab (z. B. Autostart → Codeausführung).
Jetzt prüfen Upload und Entpacken jeden Zielpfad; ein unzulässiger Eintrag lehnt das
ganze Backup ab, bevor Datenbank oder Uploads ersetzt werden.
"""
import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException

import main
from tests.test_backup_wiederherstellen import _upload_file, _zip_bytes

BOESE_EINTRAEGE = [
    "uploads/../../../../../../.config/autostart/pwned.desktop",
    "uploads/..\\..\\..\\pwned.txt",
    "uploads//tmp/pwned_absolut.txt",
    "uploads/belege/../../pwned.txt",
]


@pytest.mark.parametrize("name", BOESE_EINTRAEGE)
def test_upload_lehnt_pfad_ausserhalb_ab(tmp_path, monkeypatch, name):
    marker_zip = tmp_path / "restore_pending.zip"
    monkeypatch.setattr(main, "RESTORE_MARKER_ZIP", marker_zip)
    monkeypatch.setattr(main, "APP_DATA_DIR", tmp_path / "daten")

    datei = _upload_file("backup.zip", _zip_bytes(eintraege={"uploads/ok.pdf": b"%PDF", name: b"boese"}))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.backup_wiederherstellen(datei=datei, passwort=""))
    assert exc.value.status_code == 400
    assert "unzulässiger Pfad" in exc.value.detail
    assert not marker_zip.exists()


def test_upload_lehnt_kaputte_datenbank_ab(tmp_path, monkeypatch):
    marker_zip = tmp_path / "restore_pending.zip"
    monkeypatch.setattr(main, "RESTORE_MARKER_ZIP", marker_zip)
    monkeypatch.setattr(main, "APP_DATA_DIR", tmp_path / "daten")

    datei = _upload_file("backup.zip", _zip_bytes(db=b"keine-sqlite-datei" * 100))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.backup_wiederherstellen(datei=datei, passwort=""))
    assert exc.value.status_code == 400
    assert not marker_zip.exists()


@pytest.mark.parametrize("name", BOESE_EINTRAEGE)
def test_restore_schreibt_nichts_ausserhalb_und_ersetzt_nichts(tmp_path, monkeypatch, name):
    """Auch ein nachträglich ausgetauschter Marker darf nichts außerhalb schreiben."""
    daten = tmp_path / "home" / "daten"
    uploads = daten / "uploads"
    uploads.mkdir(parents=True)
    (uploads / "bestand.pdf").write_bytes(b"bleibt")
    (daten / "rechnungsfee.db").write_bytes(b"alte-db")

    marker_zip = daten / "restore_pending.zip"
    marker_zip.write_bytes(_zip_bytes(eintraege={name: b"boese"}))
    monkeypatch.setattr(main, "APP_DATA_DIR", daten)
    monkeypatch.setattr(main, "RESTORE_MARKER_ZIP", marker_zip)
    monkeypatch.setattr(main, "RESTORE_MARKER_DB", daten / "restore_pending.db")
    monkeypatch.setattr(main, "_backup_datenbank", lambda: None)

    main._prüfe_wiederherstellung()

    geschrieben = [p for p in tmp_path.rglob("*") if p.is_file() and "pwned" in p.name]
    assert geschrieben == []
    assert not Path("/tmp/pwned_absolut.txt").exists()
    assert (uploads / "bestand.pdf").read_bytes() == b"bleibt"   # Uploads nicht gelöscht
    assert (daten / "rechnungsfee.db").read_bytes() == b"alte-db"  # DB nicht ersetzt
    assert not marker_zip.exists()


def test_restore_mit_unterordnern_und_backslash_funktioniert(tmp_path, monkeypatch):
    daten = tmp_path / "daten"
    daten.mkdir()
    marker_zip = daten / "restore_pending.zip"
    marker_zip.write_bytes(_zip_bytes(eintraege={
        "uploads/2026/beleg.pdf": b"a",
        "uploads/postfach\\anhang.xml": b"b",   # Windows-Backup mit Backslash
    }))
    monkeypatch.setattr(main, "APP_DATA_DIR", daten)
    monkeypatch.setattr(main, "RESTORE_MARKER_ZIP", marker_zip)
    monkeypatch.setattr(main, "RESTORE_MARKER_DB", daten / "restore_pending.db")
    monkeypatch.setattr(main, "_backup_datenbank", lambda: None)

    main._prüfe_wiederherstellung()

    assert (daten / "uploads" / "2026" / "beleg.pdf").read_bytes() == b"a"
    assert (daten / "uploads" / "postfach" / "anhang.xml").read_bytes() == b"b"
    assert (daten / "rechnungsfee.db").read_bytes().startswith(b"SQLite format 3")
    assert not marker_zip.exists()
