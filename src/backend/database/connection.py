import os
import platform
import shutil
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


# Plattformübergreifender Datenpfad
APP_DATA_DIR = _resolve_app_data_dir(platform.system(), Path.home())
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
