import os
import sqlite3
import tempfile
from datetime import date

from fastapi import APIRouter
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from database.connection import DB_PATH

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.get("/download")
def backup_download():
    """WAL-sicheres DB-Backup erstellen und als Download bereitstellen."""
    datum = date.today().strftime("%Y-%m-%d")
    filename = f"RechnungsFee-Backup-{datum}.db"

    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    src = sqlite3.connect(str(DB_PATH))
    dst = sqlite3.connect(tmp_path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

    return FileResponse(
        path=tmp_path,
        filename=filename,
        media_type="application/octet-stream",
        background=BackgroundTask(os.unlink, tmp_path),
    )
