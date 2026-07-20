import io
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import date, datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from database.connection import DB_PATH, APP_DATA_DIR

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.get("/download")
def backup_download():
    """Vollständiges Backup als ZIP: WAL-sicherer DB-Snapshot + Uploads-Ordner."""
    datum = date.today().strftime("%Y-%m-%d")
    filename = f"RechnungsFee-Backup-{datum}.zip"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # DB: WAL-sicherer Snapshot
        fd, tmp = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            src = sqlite3.connect(str(DB_PATH))
            dst = sqlite3.connect(tmp)
            try:
                src.backup(dst)
            finally:
                dst.close()
                src.close()
            zf.write(tmp, "rechnungsfee.db")
        finally:
            os.unlink(tmp)

        # Uploads: Belege, PDFs, Scans
        uploads_dir = APP_DATA_DIR / "uploads"
        if uploads_dir.exists():
            for f in sorted(uploads_dir.rglob("*")):
                if f.is_file():
                    zf.write(f, f"uploads/{f.relative_to(uploads_dir).as_posix()}")

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/liste")
def backup_liste():
    """Lokale automatische Backups auflisten (neuste zuerst)."""
    backups_dir = APP_DATA_DIR / "backups"
    if not backups_dir.exists():
        return []
    eintraege = []
    for f in backups_dir.glob("rechnungsfee_*.db"):
        try:
            teile = f.stem.split("_")  # rechnungsfee_20260613_143022
            ts = datetime.strptime(f"{teile[1]}_{teile[2]}", "%Y%m%d_%H%M%S").isoformat() if len(teile) >= 3 else None
        except (ValueError, IndexError):
            ts = None
        eintraege.append({"dateiname": f.name, "timestamp": ts, "groesse": f.stat().st_size})
    eintraege.sort(key=lambda x: x["dateiname"], reverse=True)
    return eintraege


class LokalWiederherstellenBody(BaseModel):
    dateiname: str


@router.post("/wiederherstellen-lokal")
def backup_wiederherstellen_lokal(body: LokalWiederherstellenBody):
    """Kopiert einen lokalen DB-Snapshot als restore_pending.db – wird beim Neustart eingespielt."""
    if not body.dateiname.startswith("rechnungsfee_") or not body.dateiname.endswith(".db"):
        raise HTTPException(400, "Ungültiger Dateiname")
    backup_pfad = APP_DATA_DIR / "backups" / body.dateiname
    if not backup_pfad.exists():
        raise HTTPException(404, "Backup nicht gefunden")
    shutil.copy2(str(backup_pfad), str(APP_DATA_DIR / "restore_pending.db"))
    return {"ok": True, "neustart_erforderlich": True}
