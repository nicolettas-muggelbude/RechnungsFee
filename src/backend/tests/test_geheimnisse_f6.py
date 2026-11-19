"""
Security-Audit F6: Passwörter im Klartext in API, Datenbank und Backups.

GET /api/unternehmen gab SMTP-, IMAP-, SMB- und Backup-Passwort im Klartext zurück, und in der
SQLite-Datei (samt Snapshots und Backup-Download) standen sie ebenso. Jetzt: Response nur
`<feld>_gesetzt`, Spalte nur Marker, Passwort im Schlüsselbund bzw. verschlüsselt mit einer
Schlüsseldatei außerhalb der Datenbank.
"""
import asyncio
import io
import sqlite3
import zipfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from api import backup as backup_api
from api.schemas import UnternehmenResponse, UnternehmenUpdate
from api.unternehmen import get_unternehmen, update_unternehmen
from database.connection import Base
from database.models import Unternehmen
from utils import geheimnisse

PASSWOERTER = {
    "smtp_passwort": "smtp-geheim-1",
    "imap_passwort": "imap-geheim-2",
    "backup_extern_passwort": "backup-geheim-3",
    "backup_smb_passwort": "smb-geheim-4",
}


@pytest.fixture
def db_setup(tmp_path, monkeypatch):
    db_path = tmp_path / "rechnungsfee.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "DB_PATH", db_path)
    monkeypatch.setattr(main, "APP_DATA_DIR", tmp_path)
    monkeypatch.setattr(backup_api, "DB_PATH", db_path)
    monkeypatch.setattr(backup_api, "APP_DATA_DIR", tmp_path)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1",
                            plz="12345", ort="Testort"))
    session.commit()
    yield session, db_path
    session.close()
    engine.dispose()


def _roh(db_path) -> bytes:
    return db_path.read_bytes() + (db_path.with_name(db_path.name + "-wal").read_bytes()
                                   if db_path.with_name(db_path.name + "-wal").exists() else b"")


def _alle_setzen(db):
    return update_unternehmen(UnternehmenUpdate(**PASSWOERTER), db)


def test_response_enthaelt_keine_passwoerter(db_setup):
    db, _ = db_setup
    _alle_setzen(db)
    antwort = UnternehmenResponse.model_validate(get_unternehmen(db)).model_dump(mode="json")
    for feld, wert in PASSWOERTER.items():
        assert feld not in antwort
        assert antwort[f"{feld}_gesetzt"] is True
        assert wert not in str(antwort)


def test_datenbank_enthaelt_keinen_klartext(db_setup, schluesselbund):
    db, db_path = db_setup
    _alle_setzen(db)
    u = db.query(Unternehmen).first()
    for feld, wert in PASSWOERTER.items():
        assert getattr(u, feld) == geheimnisse.MARKER_KEYRING
        assert geheimnisse.passwort(u, feld) == wert
        assert wert.encode() not in _roh(db_path)
    assert len(schluesselbund.eintraege) == 4


def test_leer_oder_null_heisst_unveraendert(db_setup):
    db, _ = db_setup
    _alle_setzen(db)
    update_unternehmen(UnternehmenUpdate(smtp_passwort="", imap_passwort=None, smtp_host="mail.x"), db)
    u = db.query(Unternehmen).first()
    assert geheimnisse.passwort(u, "smtp_passwort") == "smtp-geheim-1"
    assert geheimnisse.passwort(u, "imap_passwort") == "imap-geheim-2"


def test_neuer_wert_ersetzt_und_entfernen_loescht(db_setup, schluesselbund):
    db, _ = db_setup
    _alle_setzen(db)
    update_unternehmen(UnternehmenUpdate(smtp_passwort="neu", imap_passwort_entfernen=True), db)
    u = db.query(Unternehmen).first()
    assert geheimnisse.passwort(u, "smtp_passwort") == "neu"
    assert u.imap_passwort is None
    assert not any(k[1].endswith(":imap_passwort") for k in schluesselbund.eintraege)
    antwort = UnternehmenResponse.model_validate(u)
    assert antwort.imap_passwort_gesetzt is False


def test_komplette_get_antwort_zurueckschicken_aendert_nichts(db_setup):
    """BackupPage schickte früher `...data` zurück – die Antwort enthält jetzt keine Passwörter,
    also darf ein Rücksenden sie auch nicht löschen."""
    db, _ = db_setup
    _alle_setzen(db)
    antwort = UnternehmenResponse.model_validate(get_unternehmen(db)).model_dump(mode="json")
    update_unternehmen(UnternehmenUpdate(**antwort), db)
    u = db.query(Unternehmen).first()
    for feld, wert in PASSWOERTER.items():
        assert geheimnisse.passwort(u, feld) == wert


def test_ohne_schluesselbund_verschluesselte_datei(db_setup, monkeypatch, tmp_path):
    monkeypatch.setenv("RECHNUNGSFEE_KEIN_SCHLUESSELBUND", "1")
    db, db_path = db_setup
    _alle_setzen(db)
    u = db.query(Unternehmen).first()
    for feld, wert in PASSWOERTER.items():
        assert getattr(u, feld).startswith(geheimnisse.PRAEFIX_DATEI)
        assert geheimnisse.passwort(u, feld) == wert
        assert wert.encode() not in _roh(db_path)
    schluessel = geheimnisse.DATEN_DIR / "geheimnis.key"
    assert schluessel.exists()
    assert schluessel.stat().st_mode & 0o077 == 0


def test_verschluesselter_wert_an_feld_gebunden(monkeypatch):
    monkeypatch.setenv("RECHNUNGSFEE_KEIN_SCHLUESSELBUND", "1")
    marker = geheimnisse.speichern("smtp_passwort", "x")
    with pytest.raises(geheimnisse.GeheimnisFehlt):
        geheimnisse.lesen("imap_passwort", marker)


def test_fehlender_schluesselbund_eintrag(schluesselbund):
    """Marker vorhanden, Eintrag weg (z. B. Wiederherstellung auf anderem Rechner)."""
    with pytest.raises(geheimnisse.GeheimnisFehlt):
        geheimnisse.lesen("smtp_passwort", geheimnisse.MARKER_KEYRING)


def test_migration_zieht_klartext_um_und_bereinigt_snapshots(db_setup, schluesselbund):
    db, db_path = db_setup
    # Stand vor F6: Klartext direkt in der Spalte
    db.query(Unternehmen).update({feld: wert for feld, wert in PASSWOERTER.items()})
    db.commit()
    backups = db_path.parent / "backups"
    backups.mkdir()
    snap_gleich = backups / "rechnungsfee_20260101_120000.db"
    snap_alt = backups / "rechnungsfee_20250101_120000.db"
    for snap in (snap_gleich, snap_alt):
        src, dst = sqlite3.connect(str(db_path)), sqlite3.connect(str(snap))
        src.backup(dst)
        src.close(); dst.close()
    con = sqlite3.connect(str(snap_alt))
    con.execute("UPDATE unternehmen SET smtp_passwort = 'aelteres-passwort'")
    con.commit(); con.close()

    main._migrate_geheimnisse()
    db.expire_all()

    u = db.query(Unternehmen).first()
    for feld, wert in PASSWOERTER.items():
        assert getattr(u, feld) == geheimnisse.MARKER_KEYRING
        assert geheimnisse.passwort(u, feld) == wert
        assert wert.encode() not in _roh(db_path)
        assert wert.encode() not in snap_gleich.read_bytes()
    assert b"aelteres-passwort" not in snap_alt.read_bytes()

    con = sqlite3.connect(str(snap_gleich))
    assert con.execute("SELECT smtp_passwort FROM unternehmen").fetchone()[0] == geheimnisse.MARKER_KEYRING
    con.close()
    con = sqlite3.connect(str(snap_alt))
    # abweichender Alt-Klartext → NULL, gleicher → Marker
    assert con.execute("SELECT smtp_passwort, imap_passwort FROM unternehmen").fetchone() == (
        None, geheimnisse.MARKER_KEYRING)
    con.close()

    # zweiter Lauf: nichts mehr zu tun
    vorher = dict(schluesselbund.eintraege)
    main._migrate_geheimnisse()
    assert schluesselbund.eintraege == vorher


def test_backup_download_ohne_klartext(db_setup):
    db, db_path = db_setup
    _alle_setzen(db)
    antwort = backup_api.backup_download()

    async def _lesen():
        return b"".join([teil async for teil in antwort.body_iterator])

    inhalt = asyncio.run(_lesen())
    with zipfile.ZipFile(io.BytesIO(inhalt)) as zf:
        db_bytes = zf.read("rechnungsfee.db")
        namen = zf.namelist()
    for wert in PASSWOERTER.values():
        assert wert.encode() not in db_bytes
    assert not any("geheimnis" in n for n in namen)


def test_externes_backup_nutzt_passwort_aus_schluesselbund(db_setup, tmp_path):
    db, _ = db_setup
    ziel = tmp_path / "nas"
    update_unternehmen(UnternehmenUpdate(
        backup_extern_pfad_1=str(ziel), backup_extern_pfad_1_lokal_ok=True,
        backup_extern_passwort="backup-geheim-3",
    ), db)
    ergebnis = main.backup_erstellen()
    assert ergebnis["extern_konfiguriert"] is True and not ergebnis.get("fehler")
    datei = next(ziel.glob("rechnungsfee_*.zip.enc"))
    klartext = main._decrypt_bytes(datei.read_bytes(), "backup-geheim-3")
    with zipfile.ZipFile(io.BytesIO(klartext)) as zf:
        assert b"backup-geheim-3" not in zf.read("rechnungsfee.db")


def test_externes_backup_meldet_fehlendes_passwort(db_setup, tmp_path, schluesselbund):
    db, _ = db_setup
    update_unternehmen(UnternehmenUpdate(
        backup_extern_pfad_1=str(tmp_path / "nas"), backup_extern_pfad_1_lokal_ok=True,
        backup_extern_passwort="backup-geheim-3",
    ), db)
    schluesselbund.eintraege.clear()
    ergebnis = main.backup_erstellen()
    assert ergebnis["fehler"] and "Backup-Passwort nicht gefunden" in ergebnis["fehler"][0]


def test_profil_loeschen_entfernt_schluesselbund_eintraege(schluesselbund, tmp_path):
    ordner = tmp_path / "AltesProfil"
    ordner.mkdir()
    for feld in geheimnisse.FELDER:
        geheimnisse.speichern(feld, "x", daten_dir=ordner)
    geheimnisse.speichern("smtp_passwort", "bleibt")   # anderes (aktives) Profil
    geheimnisse.profil_entfernen(ordner)
    assert list(schluesselbund.eintraege.values()) == ["bleibt"]


def test_mail_und_postfach_lesen_aus_schluesselbund(db_setup, schluesselbund):
    from fastapi import HTTPException
    from api.mail import _smtp_passwort
    from api.postfach import _imap_passwort
    db, _ = db_setup
    _alle_setzen(db)
    u = db.query(Unternehmen).first()
    assert _smtp_passwort(u) == "smtp-geheim-1"
    assert _imap_passwort(u) == "imap-geheim-2"
    schluesselbund.eintraege.clear()
    for funktion in (_smtp_passwort, _imap_passwort):
        with pytest.raises(HTTPException) as e:
            funktion(u)
        assert e.value.status_code == 400 and "neu eingeben" in e.value.detail


def test_setup_wizard_leere_datenbank(tmp_path):
    """Pflicht laut CLAUDE.md bei Änderungen an `unternehmen`: Erstanlage ohne Passwörter."""
    from api.schemas import UnternehmenCreate
    from api.unternehmen import create_unternehmen
    engine = create_engine(f"sqlite:///{tmp_path / 'leer.db'}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        u = create_unternehmen(UnternehmenCreate(
            firmenname="Neu", strasse="Weg", hausnummer="1", plz="12345", ort="Ort", land="DE",
        ), db)
        antwort = UnternehmenResponse.model_validate(u)
        assert not any(getattr(antwort, f"{f}_gesetzt") for f in geheimnisse.FELDER)
    finally:
        db.close()
        engine.dispose()
