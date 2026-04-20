import os
import platform
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Plattformübergreifender Datenpfad
# RECHNUNGSFEE_DATA_DIR kann per Umgebungsvariable überschrieben werden (z.B. Testing-Build)
_data_dir_override = os.environ.get("RECHNUNGSFEE_DATA_DIR")
if _data_dir_override:
    APP_DATA_DIR = Path(_data_dir_override)
elif platform.system() == "Windows":
    APP_DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "RechnungsFee"
else:
    APP_DATA_DIR = Path.home() / ".local" / "share" / "RechnungsFee"
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
