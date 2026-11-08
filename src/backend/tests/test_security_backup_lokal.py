"""
Regressionstest Security-Audit F8 (Pfad-Traversal in der lokalen DB-Wiederherstellung).

Bug: backup_wiederherstellen_lokal() prüfte nur Präfix „rechnungsfee_“ und Endung „.db“.
„rechnungsfee_\\..\\..\\Users\\Public\\Downloads\\x.db“ erfüllte beides; unter Windows wurde
damit eine beliebige (z. B. heruntergeladene, präparierte) Datenbank beim nächsten Start
als Firmendatenbank eingespielt.
"""
import pytest
from fastapi import HTTPException

from api import backup
from api.backup import LokalWiederherstellenBody, backup_wiederherstellen_lokal


@pytest.fixture
def daten(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "APP_DATA_DIR", tmp_path)
    (tmp_path / "backups").mkdir()
    return tmp_path


def test_gueltiger_snapshot_wird_vorgemerkt(daten):
    (daten / "backups" / "rechnungsfee_20261108_120000.db").write_bytes(b"db")
    ergebnis = backup_wiederherstellen_lokal(LokalWiederherstellenBody(dateiname="rechnungsfee_20261108_120000.db"))
    assert ergebnis["ok"] is True
    assert (daten / "restore_pending.db").read_bytes() == b"db"


@pytest.mark.parametrize("name", [
    "rechnungsfee_\\..\\..\\..\\Users\\Public\\Downloads\\x.db",
    "rechnungsfee_/../../x.db",
    "rechnungsfee_x/../../../x.db",
    "rechnungsfee_20261108_120000.db/../x.db",
    "rechnungsfee_boese.db",
    "/tmp/rechnungsfee_20261108_120000.db",
])
def test_unzulaessiger_name_abgewiesen(daten, name):
    # Ziel außerhalb existiert tatsächlich – der Test soll nicht am „nicht gefunden“ scheitern
    (daten / "x.db").write_bytes(b"fremd")
    (daten / "backups" / "rechnungsfee_x").mkdir()
    with pytest.raises(HTTPException) as exc:
        backup_wiederherstellen_lokal(LokalWiederherstellenBody(dateiname=name))
    assert exc.value.status_code == 400
    assert not (daten / "restore_pending.db").exists()
