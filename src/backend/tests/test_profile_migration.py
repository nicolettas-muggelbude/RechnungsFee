"""
Tests für den Profilmanager (docs/ROADMAP.md): _ermittle_aktives_profil_verzeichnis()
migriert eine bestehende flache Installation (rechnungsfee.db direkt in APP_DATA_DIR)
beim ersten Start nach diesem Update einmalig nach profile/Standard/. Stil analog zu
test_app_data_dir_macos.py - reine Funktionstests mit tmp_path, unabhängig vom Modul-
Importzeitpunkt.
"""
import sqlite3

from database.connection import (
    _ermittle_aktives_profil_verzeichnis,
    ist_gueltiger_profilname,
)


def _schreibe_flache_installation(base_dir, wal=False):
    """Simuliert eine Bestandsinstallation mit echten Daten direkt in base_dir.
    Bei wal=True bleibt eine zweite Verbindung offen, damit SQLite die WAL-Datei
    NICHT automatisch beim Schliessen der ersten Verbindung zurueckfaltet (SQLite
    checkpointet automatisch, sobald die LETZTE Verbindung geschlossen wird) -
    simuliert so einen Absturz/unsauberes Beenden mit noch offener WAL-Datei.
    Gibt die offene Zweitverbindung zurueck, die der Aufrufer nach den Assertions
    schliessen muss."""
    conn = sqlite3.connect(str(base_dir / "rechnungsfee.db"))
    conn.execute("PRAGMA journal_mode=WAL")
    haltekonn = sqlite3.connect(str(base_dir / "rechnungsfee.db")) if wal else None
    conn.execute("CREATE TABLE t (v TEXT)")
    conn.execute("INSERT INTO t VALUES ('echte-daten')")
    conn.commit()
    if not wal:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()

    uploads = base_dir / "uploads"
    uploads.mkdir()
    (uploads / "beleg.pdf").write_bytes(b"pdf-inhalt")
    backups = base_dir / "backups"
    backups.mkdir()
    (backups / "alt.db").write_bytes(b"altes-backup")

    return haltekonn


def _lies_wert(db_pfad):
    conn = sqlite3.connect(str(db_pfad))
    wert = conn.execute("SELECT v FROM t").fetchone()[0]
    conn.close()
    return wert


def test_neuinstallation_ohne_bestehende_daten(tmp_path):
    ziel = _ermittle_aktives_profil_verzeichnis(tmp_path)

    assert ziel == tmp_path / "profile" / "Standard"
    assert (tmp_path / "profile.json").read_text(encoding="utf-8") == '{"active": "Standard"}'
    # Zielordner selbst wird bewusst nicht angelegt (macht der Aufrufer via mkdir),
    # analog zu _resolve_app_data_dir.
    assert not ziel.exists()


def test_migriert_bestehende_flache_installation(tmp_path):
    _schreibe_flache_installation(tmp_path)

    ziel = _ermittle_aktives_profil_verzeichnis(tmp_path)

    assert ziel == tmp_path / "profile" / "Standard"
    assert _lies_wert(ziel / "rechnungsfee.db") == "echte-daten"
    assert (ziel / "uploads" / "beleg.pdf").read_bytes() == b"pdf-inhalt"
    assert (ziel / "backups" / "alt.db").read_bytes() == b"altes-backup"
    # Alte Top-Level-Dateien sind weg
    assert not (tmp_path / "rechnungsfee.db").exists()
    assert not (tmp_path / "uploads").exists()
    # Sicherheitskopie existiert
    assert (tmp_path / "pre_profile_migration_backup" / "rechnungsfee.db").exists()


def test_wal_und_shm_dateien_wandern_mit_auch_wenn_checkpoint_fehlschlaegt(tmp_path, monkeypatch):
    """Der WAL-Checkpoint vor dem Verschieben ist best-effort (siehe Kommentar in
    _verschiebe_flache_installation_in_temp) - schlägt er fehl, dürfen -wal/-shm
    trotzdem nicht zurückgelassen werden, sonst könnten committete Transaktionen
    verloren gehen. Simuliert den Fehlerfall direkt statt zu versuchen, einen echten
    SQLite-WAL-Restzustand nachzubauen (SQLites eigenes Checkpoint-on-close-Verhalten
    lässt sich über die Python-API nicht zuverlässig umgehen)."""
    _schreibe_flache_installation(tmp_path)
    (tmp_path / "rechnungsfee.db-wal").write_bytes(b"wal-inhalt")
    (tmp_path / "rechnungsfee.db-shm").write_bytes(b"shm-inhalt")

    # Nur der Checkpoint-Connect auf die ALTE (flache) DB soll fehlschlagen - ein
    # blanket-Patch von sqlite3.connect wuerde auch _lies_wert() unten treffen, da
    # beide denselben Modul-Namen "sqlite3" referenzieren.
    import database.connection as connection_modul
    echter_connect = connection_modul.sqlite3.connect

    def teilweise_kaputter_connect(pfad, *args, **kwargs):
        if str(pfad) == str(tmp_path / "rechnungsfee.db"):
            raise sqlite3.OperationalError("simulierter Checkpoint-Fehler")
        return echter_connect(pfad, *args, **kwargs)
    monkeypatch.setattr(connection_modul.sqlite3, "connect", teilweise_kaputter_connect)

    ziel = _ermittle_aktives_profil_verzeichnis(tmp_path)

    # Reihenfolge wichtig: erst die rohen Bytes pruefen, BEVOR _lies_wert() eine echte
    # SQLite-Verbindung zur db oeffnet - unsere -wal/-shm-Dateien sind absichtlich nur
    # Fake-Inhalt (kein echtes WAL-Format), SQLite wuerde sie beim Oeffnen als defekt
    # erkennen und automatisch bereinigen, was den eigentlichen Test (wurden die
    # Dateien beim VERSCHIEBEN nicht zurückgelassen?) verfälschen würde.
    assert (ziel / "rechnungsfee.db-wal").read_bytes() == b"wal-inhalt"
    assert (ziel / "rechnungsfee.db-shm").read_bytes() == b"shm-inhalt"
    assert _lies_wert(ziel / "rechnungsfee.db") == "echte-daten"


def test_zeiger_existiert_bereits_keine_erneute_migration(tmp_path):
    (tmp_path / "profile.json").write_text('{"active": "Standard"}', encoding="utf-8")
    (tmp_path / "rechnungsfee.db").write_bytes(b"sollte-ignoriert-werden")

    ziel = _ermittle_aktives_profil_verzeichnis(tmp_path)

    assert ziel == tmp_path / "profile" / "Standard"
    # Die "neue" Alt-DB wurde NICHT migriert, da bereits ein Profil aktiv ist
    assert (tmp_path / "rechnungsfee.db").exists()
    assert not (ziel / "rechnungsfee.db").exists()


def test_aufruf_ist_idempotent(tmp_path):
    _schreibe_flache_installation(tmp_path)

    erster_aufruf = _ermittle_aktives_profil_verzeichnis(tmp_path)
    zweiter_aufruf = _ermittle_aktives_profil_verzeichnis(tmp_path)

    assert erster_aufruf == zweiter_aufruf
    assert _lies_wert(erster_aufruf / "rechnungsfee.db") == "echte-daten"


def test_setzt_migration_nach_simuliertem_absturz_fort(tmp_path):
    """Absturz zwischen Verschieben und finalem Rename: .migrating_Standard/ liegt
    bereits (teilweise befüllt) vor, profile.json fehlt noch."""
    _schreibe_flache_installation(tmp_path)

    # Absturz simulieren: DB wurde schon verschoben, uploads/backups noch nicht,
    # kein finaler Rename, kein Zeiger.
    temp = tmp_path / "profile" / ".migrating_Standard"
    temp.mkdir(parents=True)
    (tmp_path / "rechnungsfee.db").rename(temp / "rechnungsfee.db")

    ziel = _ermittle_aktives_profil_verzeichnis(tmp_path)

    assert ziel == tmp_path / "profile" / "Standard"
    assert _lies_wert(ziel / "rechnungsfee.db") == "echte-daten"
    assert (ziel / "uploads" / "beleg.pdf").read_bytes() == b"pdf-inhalt"
    assert (ziel / "backups" / "alt.db").read_bytes() == b"altes-backup"
    assert not temp.exists()


def test_zeiger_mit_ungueltigem_profilnamen_faellt_auf_standard_zurueck(tmp_path):
    (tmp_path / "profile.json").write_text('{"active": "../../etc"}', encoding="utf-8")

    ziel = _ermittle_aktives_profil_verzeichnis(tmp_path)

    assert ziel == tmp_path / "profile" / "Standard"


def test_defektes_zeiger_json_faellt_auf_standard_zurueck(tmp_path):
    (tmp_path / "profile.json").write_text("{kaputt", encoding="utf-8")

    ziel = _ermittle_aktives_profil_verzeichnis(tmp_path)

    assert ziel == tmp_path / "profile" / "Standard"


def test_ist_gueltiger_profilname():
    assert ist_gueltiger_profilname("Standard")
    assert ist_gueltiger_profilname("Freiberuflich 2026")
    assert ist_gueltiger_profilname("Firma-B_2")
    assert not ist_gueltiger_profilname("")
    assert not ist_gueltiger_profilname("../etc")
    assert not ist_gueltiger_profilname("a/b")
    assert not ist_gueltiger_profilname("a\\b")
    assert not ist_gueltiger_profilname("a" * 51)
