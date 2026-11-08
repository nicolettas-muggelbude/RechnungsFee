"""
Regressionstest für Issue #347.

Bug: backup_wiederherstellen() (main.py) referenzierte die nie definierte Variable
RESTORE_MARKER statt RESTORE_MARKER_ZIP - jeder Wiederherstellungsversuch crashte
mit NameError: name 'RESTORE_MARKER' is not defined ("Failed to fetch" im Frontend,
500 Internal Server Error im Backend). Kritisch, da Backup-Wiederherstellung komplett
unbenutzbar war.
"""
import asyncio
import io
import sqlite3
import tempfile
import zipfile
from pathlib import Path

import pytest

import main


def _db_bytes() -> bytes:
    """Kleine, gültige SQLite-Datenbank (der Upload prüft PRAGMA integrity_check)."""
    with tempfile.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "x.db"
        con = sqlite3.connect(str(pfad))
        con.execute("CREATE TABLE t (id INTEGER)")
        con.commit()
        con.close()
        return pfad.read_bytes()


def _zip_bytes(mit_db: bool = True, eintraege: dict[str, bytes] | None = None, db: bytes | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        if mit_db:
            zf.writestr("rechnungsfee.db", db if db is not None else _db_bytes())
        for name, inhalt in (eintraege or {"uploads/dummy.txt": b"x"}).items():
            zf.writestr(name, inhalt)
    return buf.getvalue()


def _upload_file(filename: str, content: bytes):
    from fastapi import UploadFile
    return UploadFile(filename=filename, file=io.BytesIO(content))


def test_backup_wiederherstellen_schreibt_restore_marker_zip(tmp_path, monkeypatch):
    marker_zip = tmp_path / "restore_pending.zip"
    monkeypatch.setattr(main, "RESTORE_MARKER_ZIP", marker_zip)

    inhalt = _zip_bytes()
    datei = _upload_file("backup.zip", inhalt)

    ergebnis = asyncio.run(main.backup_wiederherstellen(datei=datei, passwort=""))

    assert ergebnis == {"ok": True, "neustart_erforderlich": True}
    assert marker_zip.exists()
    assert marker_zip.read_bytes() == inhalt


def test_backup_wiederherstellen_ohne_db_in_zip_wird_abgelehnt(tmp_path, monkeypatch):
    marker_zip = tmp_path / "restore_pending.zip"
    monkeypatch.setattr(main, "RESTORE_MARKER_ZIP", marker_zip)

    datei = _upload_file("backup.zip", _zip_bytes(mit_db=False))

    with pytest.raises(Exception) as exc_info:
        asyncio.run(main.backup_wiederherstellen(datei=datei, passwort=""))
    assert "400" in str(exc_info.value) or "rechnungsfee.db" in str(exc_info.value)
    assert not marker_zip.exists()
