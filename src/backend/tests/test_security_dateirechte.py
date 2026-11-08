"""
Regressionstest Security-Audit F11 (Datenordner für andere Benutzer lesbar).

Unter Linux/macOS entstanden rechnungsfee.db, WAL, Snapshots und Uploads mit umask 022
als 0644/0755. database/connection.py setzt jetzt umask 077 und den Basisordner auf 0700.
"""
import os
import stat

import pytest

from database import connection

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Unix-Dateirechte")


def test_umask_nur_eigener_benutzer(tmp_path):
    neu = tmp_path / "neu.db"
    neu.write_bytes(b"x")
    assert stat.S_IMODE(neu.stat().st_mode) & 0o077 == 0
    ordner = tmp_path / "ordner"
    ordner.mkdir()
    assert stat.S_IMODE(ordner.stat().st_mode) & 0o077 == 0


def test_basisordner_0700():
    assert stat.S_IMODE(connection.BASE_DIR.stat().st_mode) == 0o700
