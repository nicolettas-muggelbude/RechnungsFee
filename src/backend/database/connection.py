import json
import os
import platform
import re
import shutil
import sqlite3
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase


def _resolve_app_data_dir(system: str, home: Path) -> Path:
    """Plattformübergreifender Datenpfad. Reine Funktion (kein I/O außer der macOS-
    Einmalmigration) - so lässt sie sich unabhängig vom Modul-Importzeitpunkt testen."""
    if system == "Windows":
        return Path(os.environ.get("APPDATA", str(home))) / "RechnungsFee"
    if system == "Darwin":
        ziel = home / "Library" / "Application Support" / "RechnungsFee"
        # Einmalige Migration (Issue #348): frühere Versionen nutzten fälschlich den
        # Linux-XDG-Pfad auch unter macOS ("else"-Zweig fing Darwin mit auf). Bestehende
        # Installationen würden ihre Daten sonst beim Update scheinbar verlieren - alter
        # Ordner wird nur verschoben, wenn er echte Daten enthält und am neuen Ort noch
        # keine DB liegt (kein Überschreiben eines bereits migrierten/neuen Ordners).
        alter_pfad = home / ".local" / "share" / "RechnungsFee"
        if (alter_pfad / "rechnungsfee.db").exists() and not (ziel / "rechnungsfee.db").exists():
            ziel.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(alter_pfad), str(ziel))
            print(f"[Migration] macOS-Datenordner verschoben: {alter_pfad} -> {ziel}")
        return ziel
    return home / ".local" / "share" / "RechnungsFee"


# ---------------------------------------------------------------------------
# Profilmanager (docs/ROADMAP.md): mehrere Firmenprofile pro Installation.
# APP_DATA_DIR zeigt nicht mehr direkt auf den Basisordner, sondern eine Ebene
# tiefer auf das jeweils AKTIVE Profil (BASE_DIR/profile/<name>/). Dadurch
# erben alle bestehenden, APP_DATA_DIR-relativen Pfade (uploads/, backups/,
# logs/ usw. in main.py und den api/*-Modulen) die Profiltrennung automatisch,
# ohne dass diese Module selbst geändert werden müssen.
# ---------------------------------------------------------------------------

_PROFILE_POINTER_NAME = "profile.json"
_PROFILE_ROOT_NAME = "profile"
_STANDARD_PROFIL = "Standard"
_MIGRATION_TEMP_PREFIX = ".migrating_"

_PROFILNAME_PATTERN = re.compile(r"^[A-Za-z0-9 _-]{1,50}$")

# Alles was zu einer flachen Alt-Installation gehören kann und beim ersten Start
# nach diesem Update einmalig ins Standard-Profil verschoben werden muss.
_MIGRIERBARE_ELEMENTE = (
    "rechnungsfee.db", "rechnungsfee.db-wal", "rechnungsfee.db-shm",
    "uploads", "backups", "logs",
    "restore_pending.zip", "restore_pending.db",
)


def ist_gueltiger_profilname(name: str) -> bool:
    """Nur alphanumerisch + Leerzeichen/Bindestrich/Unterstrich, max. 50 Zeichen -
    verhindert Path-Traversal (../, /, \\) sowohl beim Anlegen als auch defensiv
    beim Lesen eines (potenziell manuell manipulierten) Profil-Zeigers."""
    return bool(_PROFILNAME_PATTERN.match(name))


def _verschiebe_flache_installation_in_temp(base_dir: Path, temp_ziel: Path) -> None:
    """Verschiebt eine bestehende flache Installation (rechnungsfee.db, uploads/, ...)
    in einen deterministischen Temp-Ordner. Jeder Schritt ist einzeln idempotent (nur
    wenn Quelle existiert und Ziel noch nicht) - exakt das bestehende Muster der macOS-
    Migration oben, nur auf mehrere Objekte statt einem einzelnen Ordner angewandt.
    Dadurch ist ein Absturz mittendrin beim nächsten Start sicher fortsetzbar, ohne
    bereits verschobene Daten zu duplizieren oder zu verlieren."""
    alte_db = base_dir / "rechnungsfee.db"
    if alte_db.exists():
        # WAL-Checkpoint erzwingen BEVOR irgendetwas verschoben wird - sonst könnten
        # bereits committete, aber noch nicht in die Hauptdatei zurückgeschriebene
        # Transaktionen in der WAL-Datei zurückbleiben bzw. beim Verschieben getrennt
        # werden. Eigenständige sqlite3-Verbindung, da die SQLAlchemy-Engine an dieser
        # Stelle (Modul-Importzeit, vor DB_PATH/engine) noch gar nicht existiert.
        try:
            conn = sqlite3.connect(str(alte_db))
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.close()
        except sqlite3.Error as e:
            print(f"[Profilmigration] WAL-Checkpoint fehlgeschlagen (nicht kritisch, "
                  f"-wal/-shm werden trotzdem mitverschoben): {e}")

        # Sicherheitskopie der Haupt-DB - wird nie automatisch gelöscht, dient nur als
        # manueller Notanker für Support-Fälle. Explizit VOR dem Verschieben, damit sie
        # auch bei einem Absturz mitten in der Migration bereits vorhanden ist.
        sicherung_dir = base_dir / "pre_profile_migration_backup"
        sicherung_dir.mkdir(exist_ok=True)
        sicherung_ziel = sicherung_dir / "rechnungsfee.db"
        if not sicherung_ziel.exists():
            shutil.copy2(str(alte_db), str(sicherung_ziel))

    temp_ziel.mkdir(parents=True, exist_ok=True)
    for name in _MIGRIERBARE_ELEMENTE:
        quelle = base_dir / name
        ziel = temp_ziel / name
        if quelle.exists() and not ziel.exists():
            shutil.move(str(quelle), str(ziel))


def _ermittle_aktives_profil_verzeichnis(base_dir: Path) -> Path:
    """Liefert das Datenverzeichnis des aktiven Profils. Migriert eine bestehende
    flache Installation (Daten direkt in base_dir) beim ersten Start nach diesem
    Update einmalig nach profile/Standard/ - ohne das würde es für Bestandsnutzer wie
    Datenverlust wirken (docs/ROADMAP.md, Profilmanager-Plan). Reine, unabhängig vom
    Modul-Importzeitpunkt testbare Funktion, analog zu _resolve_app_data_dir oben.
    Legt das Zielverzeichnis selbst NICHT an (macht der Aufrufer via mkdir), außer dem
    Zwischenschritt-Rename bei einer laufenden Migration."""
    zeiger_pfad = base_dir / _PROFILE_POINTER_NAME
    profile_root = base_dir / _PROFILE_ROOT_NAME

    if zeiger_pfad.exists():
        aktiv = _STANDARD_PROFIL
        try:
            zeiger = json.loads(zeiger_pfad.read_text(encoding="utf-8"))
            kandidat = zeiger.get("active", _STANDARD_PROFIL)
            if ist_gueltiger_profilname(kandidat):
                aktiv = kandidat
        except (json.JSONDecodeError, OSError):
            pass
        return profile_root / aktiv

    ziel = profile_root / _STANDARD_PROFIL
    temp = profile_root / f"{_MIGRATION_TEMP_PREFIX}{_STANDARD_PROFIL}"

    if not ziel.exists() and (temp.exists() or (base_dir / "rechnungsfee.db").exists()):
        _verschiebe_flache_installation_in_temp(base_dir, temp)
        # Atomarer Abschluss: ein einzelner Verzeichnis-Rename ist sowohl unter POSIX
        # als auch unter Windows atomar (anders als die mehreren Einzel-Moves oben).
        os.rename(str(temp), str(ziel))

    zeiger_pfad.write_text(json.dumps({"active": _STANDARD_PROFIL}), encoding="utf-8")
    return ziel


# Plattformübergreifender Basis-Datenpfad (unverändert wie bisher)
_BASE_DIR_ROH = _resolve_app_data_dir(platform.system(), Path.home())
_BASE_DIR_ROH.mkdir(parents=True, exist_ok=True)

# Öffentlich, wird von api/profile.py gebraucht um Geschwister-Profile aufzulisten.
BASE_DIR = _BASE_DIR_ROH

# Datenpfad des AKTIVEN Profils - das ist der eigentliche "Arbeitsordner" der App.
APP_DATA_DIR = _ermittle_aktives_profil_verzeichnis(BASE_DIR)
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = APP_DATA_DIR / "rechnungsfee.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


# WAL-Modus für bessere Parallelität und GoBD-Sicherheit
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
