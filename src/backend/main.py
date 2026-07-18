import logging
import logging.handlers
import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database.connection import Base, engine, SessionLocal, DB_PATH, APP_DATA_DIR

# ── Backend-Datei-Logging ─────────────────────────────────────────────────────
# Logs landen neben der DB unter APP_DATA_DIR/logs/backend.log (max. 5 MB × 3)
# so dass sie auch im gebündelten PyInstaller-Build auf Windows auffindbar sind.
_log_dir = APP_DATA_DIR / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)
_log_handler = logging.handlers.RotatingFileHandler(
    _log_dir / "backend.log",
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)
_log_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))
logging.root.setLevel(logging.INFO)
logging.root.addHandler(_log_handler)
# ─────────────────────────────────────────────────────────────────────────────
from database.seed import run_all_seeds
from api import unternehmen, konten, kategorien, setup, journal, kunden, lieferanten, tagesabschluss, nummernkreise, export, rechnungen, backup, artikel, artikel_gruppen, ust_saetze, pdf_vorlagen, eks, system, ustva, zm, euer, dokumentenpakete, mail, wiederkehrend, buchungsvorlagen, anlageverzeichnis, datev, anlage_s, anlage_g, fristen_api, guv, bank_templates, bank_import, auto_filter, forderungen, cockpit, datenmigration

SCHEMA_VERSION = 119

app = FastAPI(title="RechnungsFee API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "tauri://localhost", "http://tauri.localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "Content-Disposition",
        "X-Datev-Eintraege",
        "X-Datev-Uebersprungen",
        "X-Buchhalter-Eintraege",
        "X-GoBD-Buchungen",
        "X-GoBD-Belege",
    ],
)

app.include_router(setup.router)
app.include_router(unternehmen.router)
app.include_router(konten.router)
app.include_router(kategorien.router)
app.include_router(journal.router)
app.include_router(kunden.router)
app.include_router(lieferanten.router)
app.include_router(tagesabschluss.router)
app.include_router(nummernkreise.router)
app.include_router(export.router)
app.include_router(rechnungen.router)
app.include_router(backup.router)
app.include_router(artikel.router)
app.include_router(artikel_gruppen.router)
app.include_router(ust_saetze.router)
app.include_router(pdf_vorlagen.router)
app.include_router(eks.router)
app.include_router(ustva.router)
app.include_router(zm.router)
app.include_router(euer.router)
app.include_router(system.router)
app.include_router(dokumentenpakete.router)
app.include_router(mail.router)
app.include_router(wiederkehrend.router)
app.include_router(buchungsvorlagen.router)
app.include_router(anlageverzeichnis.router)
app.include_router(datev.router)
app.include_router(anlage_s.router)
app.include_router(anlage_g.router)
app.include_router(fristen_api.router)
app.include_router(guv.router)
app.include_router(bank_templates.router)
app.include_router(bank_import.router)
app.include_router(auto_filter.router)
app.include_router(forderungen.router)
app.include_router(cockpit.router)
app.include_router(datenmigration.router)


@app.post("/api/shutdown")
def shutdown():
    """Graceful Shutdown – Tauri ruft diesen Endpoint vor dem Update-Installer auf."""
    def _exit():
        import time
        time.sleep(0.15)   # Antwort zuerst senden, dann beenden
        os._exit(0)
    threading.Thread(target=_exit, daemon=True).start()
    return {"ok": True}


def _decrypt_bytes(data: bytes, passwort: str) -> bytes:
    """Entschlüsselt AES-256-GCM. Format: salt(16)+nonce(12)+ciphertext+tag."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes

    salt  = data[:16]
    nonce = data[16:28]
    ct    = data[28:]
    kdf   = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100_000)
    key   = kdf.derive(passwort.encode())
    return AESGCM(key).decrypt(nonce, ct, None)


def _encrypt_bytes(data: bytes, passwort: str) -> bytes:
    """AES-256-GCM mit PBKDF2-SHA256 (100k Iterationen). Rückgabe: salt(16)+nonce(12)+ciphertext+tag."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    import os as _os

    salt  = _os.urandom(16)
    nonce = _os.urandom(12)
    kdf   = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100_000)
    key   = kdf.derive(passwort.encode())
    return salt + nonce + AESGCM(key).encrypt(nonce, data, None)


def _erstelle_vollbackup_zip() -> bytes:
    """ZIP mit WAL-sicherem DB-Snapshot + Uploads-Ordner (Belege, PDFs)."""
    import io
    import zipfile
    import tempfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # DB: WAL-sicherer Snapshot über sqlite3.backup()
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

        # Uploads: Belege, PDFs, OCR-Dateien
        uploads_dir = APP_DATA_DIR / "uploads"
        if uploads_dir.exists():
            for f in sorted(uploads_dir.rglob("*")):
                if f.is_file():
                    zf.write(f, f"uploads/{f.relative_to(uploads_dir)}")

    return buf.getvalue()


def _backup_smb(smb_url: str, dateiname: str, daten: bytes,
                benutzer: str | None, passwort: str | None) -> None:
    """Schreibt Backup-Bytes direkt per SMB-Protokoll auf eine Netzwerkfreigabe.

    smb_url-Format: smb://server/share/optionaler/pfad
    Erfordert smbprotocol (pip install smbprotocol).
    """
    try:
        import smbclient  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "smbprotocol ist nicht installiert. "
            "Bitte 'pip install smbprotocol' ausführen."
        ) from exc

    # smb://server/share/pfad → server, share, pfad
    ohne_schema = smb_url[6:]  # entfernt "smb://"
    teile = ohne_schema.split("/", 2)
    server = teile[0]
    share  = teile[1] if len(teile) > 1 else ""
    unterordner = teile[2] if len(teile) > 2 else ""

    if not server or not share:
        raise ValueError(f"Ungültige SMB-URL: {smb_url!r} – Format: smb://server/share/pfad")

    smbclient.register_session(server, username=benutzer or "", password=passwort or "")

    # Zielordner sicherstellen (rekursiv)
    unc_basis = f"\\\\{server}\\{share}"
    if unterordner:
        teile_ordner = unterordner.strip("/").split("/")
        aktuell = unc_basis
        for teil in teile_ordner:
            aktuell = f"{aktuell}\\{teil}"
            try:
                smbclient.mkdir(aktuell)
            except Exception:
                pass  # existiert bereits

    unc_ziel = f"{unc_basis}\\{unterordner.replace('/', '\\')}\\{dateiname}".replace("\\\\", "\\").replace("\\", "\\")
    # saubereres UNC aufbauen
    pfad_teile = [p for p in [unterordner.strip("/").replace("/", "\\"), dateiname] if p]
    unc_datei = f"\\\\{server}\\{share}\\" + "\\".join(pfad_teile)

    with smbclient.open_file(unc_datei, mode="wb") as f:
        f.write(daten)


@app.post("/api/backup/erstellen")
def backup_erstellen():
    """Backup bei App-Ende – WAL-sicher lokal (max. 5), optional AES-256-GCM auf externen Pfaden."""
    try:
        _backup_datenbank()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    backup_dir = DB_PATH.parent / "backups"
    backups = sorted(backup_dir.glob("rechnungsfee_*.db"))
    if not backups:
        return {"ok": True}
    neuestes = backups[-1]

    try:
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT backup_extern_pfad_1, backup_extern_pfad_2, backup_extern_passwort, "
                "backup_smb_benutzer, backup_smb_passwort "
                "FROM unternehmen WHERE id=1"
            )).fetchone()
    except Exception:
        return {"ok": True}

    if not row:
        return {"ok": True}

    pfad1, pfad2, passwort, smb_benutzer, smb_passwort = row
    extern_konfiguriert = bool(passwort and (pfad1 or pfad2))
    if not extern_konfiguriert:
        print("[Backup] Externe Ziele übersprungen: kein Verschlüsselungs-Passwort gesetzt")
        return {"ok": True, "extern_konfiguriert": False}

    # Vollbackup (DB + Uploads) als ZIP erstellen und verschlüsseln
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dateiname = f"rechnungsfee_{ts}.zip.enc"
    try:
        zip_bytes = _erstelle_vollbackup_zip()
        enc_bytes = _encrypt_bytes(zip_bytes, passwort)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup-ZIP-Erstellung fehlgeschlagen: {e}")

    fehler = []
    uebersprungen = []
    for pfad in filter(None, [pfad1, pfad2]):
        if _ist_systemlaufwerk(pfad):
            uebersprungen.append(pfad)
            print(f"[Backup] Systemlaufwerk übersprungen: {pfad}")
            continue
        try:
            if pfad.startswith("smb://"):
                _backup_smb(pfad, dateiname, enc_bytes, smb_benutzer, smb_passwort)
            else:
                ziel_dir = Path(pfad)
                ziel_dir.mkdir(parents=True, exist_ok=True)
                (ziel_dir / dateiname).write_bytes(enc_bytes)
            print(f"[Backup] Extern gesichert: {pfad}/{dateiname}")
        except Exception as e:
            fehler.append(f"{pfad}: {e}")
            print(f"[Backup] Externer Backup-Fehler ({pfad}): {e}")

    return {"ok": True, "extern_konfiguriert": True, "fehler": fehler or None, "uebersprungen": uebersprungen or None}


@app.post("/api/backup/wiederherstellen")
async def backup_wiederherstellen(
    datei: UploadFile = File(...),
    passwort: str = Form(default=""),
):
    """Nimmt .zip (unverschlüsselt) oder .zip.enc (AES-256) entgegen, validiert und speichert als Pending-Marker."""
    import io
    import zipfile
    filename = datei.filename or ""
    content  = await datei.read()

    if filename.endswith(".zip.enc"):
        if not passwort:
            raise HTTPException(status_code=400, detail="Verschlüsseltes Backup (.zip.enc) erfordert ein Passwort")
        try:
            content = _decrypt_bytes(content, passwort)
        except Exception:
            raise HTTPException(status_code=400, detail="Entschlüsselung fehlgeschlagen – falsches Passwort?")
    elif not filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Nur .zip oder .zip.enc Dateien werden akzeptiert")

    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            if "rechnungsfee.db" not in zf.namelist():
                raise HTTPException(status_code=400, detail="Ungültiges Backup: rechnungsfee.db nicht gefunden")
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Ungültige ZIP-Datei (oder falsches Passwort)")

    RESTORE_MARKER.write_bytes(content)
    return {"ok": True, "neustart_erforderlich": True}


def _ist_systemlaufwerk(pfad: str) -> bool:
    """Gibt True zurück wenn pfad auf einem Systemlaufwerk liegt (kein sinnvoller Backup-Ort)."""
    if pfad.startswith("smb://"):
        return False
    p = pfad.replace("\\", "/").lower().rstrip("/")
    # Windows: nur C: blockieren, andere Laufwerksbuchstaben (D:, E: …) sind OK
    if p == "c:" or p.startswith("c:/"):
        return True
    # Linux/macOS: alles unter / blockieren außer bekannte externe Einhängepunkte
    if p.startswith("/"):
        erlaubt = ("/mnt/", "/media/", "/run/media/", "/volumes/")
        return not any(p.startswith(e) for e in erlaubt)
    return False


def _backup_datenbank() -> None:
    """Erstellt ein WAL-sicheres Backup der DB vor Migrationen (max. 5 Backups)."""
    backup_dir = DB_PATH.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"rechnungsfee_{ts}.db"

    src = sqlite3.connect(str(DB_PATH))
    dst = sqlite3.connect(str(backup_path))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    print(f"[Migration] DB-Backup: {backup_path.name}")

    # Rotation: max. 5 Backups behalten, älteste löschen
    backups = sorted(backup_dir.glob("rechnungsfee_*.db"))
    for old in backups[:-5]:
        old.unlink()
        print(f"[Migration] Altes Backup gelöscht: {old.name}")


RESTORE_MARKER_ZIP = APP_DATA_DIR / "restore_pending.zip"
RESTORE_MARKER_DB  = APP_DATA_DIR / "restore_pending.db"


def _prüfe_wiederherstellung() -> None:
    """Stellt Backup wieder her wenn ein Pending-Marker existiert (vor DB-Öffnung).

    restore_pending.zip  → vollständiges Backup (DB + Uploads) aus ZIP
    restore_pending.db   → lokaler DB-Snapshot (nur Datenbank, Uploads bleiben)
    """
    marker_zip = RESTORE_MARKER_ZIP
    marker_db  = RESTORE_MARKER_DB
    if not marker_zip.exists() and not marker_db.exists():
        return

    import io
    import shutil
    import zipfile
    print("[Wiederherstellung] Pending-Marker gefunden – stelle wieder her …")
    try:
        _backup_datenbank()  # Sicherheitsbackup der aktuellen DB

        if marker_zip.exists():
            with zipfile.ZipFile(marker_zip, "r") as zf:
                names = zf.namelist()
                if "rechnungsfee.db" in names:
                    zf.extract("rechnungsfee.db", APP_DATA_DIR)
                    print("[Wiederherstellung] Datenbank (ZIP) wiederhergestellt")
                upload_entries = [n for n in names if n.startswith("uploads/") and not n.endswith("/")]
                if upload_entries:
                    uploads_dir = APP_DATA_DIR / "uploads"
                    if uploads_dir.exists():
                        shutil.rmtree(uploads_dir)
                    for name in upload_entries:
                        zf.extract(name, APP_DATA_DIR)
                    print(f"[Wiederherstellung] {len(upload_entries)} Belege wiederhergestellt")
            marker_zip.unlink()

        elif marker_db.exists():
            shutil.copy2(str(marker_db), str(DB_PATH))
            marker_db.unlink()
            print("[Wiederherstellung] Datenbank (lokales Backup) wiederhergestellt")

        print("[Wiederherstellung] Abgeschlossen")
    except Exception as e:
        print(f"[Wiederherstellung] Fehler: {e}")
        marker_zip.unlink(missing_ok=True)
        marker_db.unlink(missing_ok=True)


def _run_migrations() -> None:
    """Versionierte DB-Migrationen für SQLite (ohne Alembic)."""
    with engine.connect() as conn:
        version = conn.execute(text("PRAGMA user_version")).scalar()

    if version >= SCHEMA_VERSION:
        return  # Fast-Path: DB ist aktuell

    # Frische DB: create_all hat bereits das aktuelle Schema angelegt (journal, nicht kassenbuch).
    # user_version ist noch 0, aber die ALTER-Migrationen wären falsch → direkt auf SCHEMA_VERSION.
    with engine.connect() as conn:
        hat_kassenbuch = conn.execute(text(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='kassenbuch'"
        )).scalar()
    if version == 0 and not hat_kassenbuch:
        _backup_datenbank()
        with engine.connect() as conn:
            conn.execute(text(f"PRAGMA user_version = {SCHEMA_VERSION}"))
            conn.commit()
        return

    _backup_datenbank()

    with engine.connect() as conn:
        if version < 1:
            # journal/kassenbuch – 1× PRAGMA für alle Spalten (Tabelle heißt noch kassenbuch bei version < 1)
            cols = {row[1] for row in conn.execute(text("PRAGMA table_info(kassenbuch)"))}
            for col_name, ddl in [
                ("kunde_id",        "INTEGER REFERENCES kunden(id)"),
                ("rechnung_id",     "INTEGER REFERENCES rechnungen(id)"),
                ("externe_belegnr", "VARCHAR(100)"),
                ("signatur",        "VARCHAR(64)"),
            ]:
                if col_name not in cols:
                    conn.execute(text(f"ALTER TABLE kassenbuch ADD COLUMN {col_name} {ddl}"))

            # rechnungen – 1× PRAGMA für alle Spalten
            cols = {row[1] for row in conn.execute(text("PRAGMA table_info(rechnungen)"))}
            for col_name, ddl in [
                ("bezahlt_betrag",  "NUMERIC(12,2) NOT NULL DEFAULT 0"),
                ("zahlungsstatus",  "VARCHAR(20) NOT NULL DEFAULT 'offen'"),
                ("leistungsdatum",  "DATE"),
                ("ist_entwurf",     "BOOLEAN NOT NULL DEFAULT 0"),
                ("storniert",       "BOOLEAN NOT NULL DEFAULT 0"),
                ("ausgegeben",      "BOOLEAN NOT NULL DEFAULT 0"),
            ]:
                if col_name not in cols:
                    conn.execute(text(f"ALTER TABLE rechnungen ADD COLUMN {col_name} {ddl}"))

            # tagesabschluesse – 1× PRAGMA für alle Spalten
            cols = {row[1] for row in conn.execute(text("PRAGMA table_info(tagesabschluesse)"))}
            for col_name, ddl in [
                ("zaehlung_json", "TEXT"),
                ("signatur",      "VARCHAR(64)"),
            ]:
                if col_name not in cols:
                    conn.execute(text(f"ALTER TABLE tagesabschluesse ADD COLUMN {col_name} {ddl}"))

            # unternehmen – 1× PRAGMA für alle Spalten
            cols = {row[1] for row in conn.execute(text("PRAGMA table_info(unternehmen)"))}
            for col_name, ddl in [
                ("handelsregister_nr",      "VARCHAR(100)"),
                ("handelsregister_gericht", "VARCHAR(100)"),
                ("logo_pfad",               "VARCHAR(500)"),
                ("mail_betreff_vorlage",    "VARCHAR(500)"),
                ("mail_text_vorlage",       "TEXT"),
                ("mail_signatur",           "TEXT"),
            ]:
                if col_name not in cols:
                    conn.execute(text(f"ALTER TABLE unternehmen ADD COLUMN {col_name} {ddl}"))

            # kategorien – konto_skr03/04 waren von Anfang an im Modell, fehlen aber in sehr alten DBs
            cols = {row[1] for row in conn.execute(text("PRAGMA table_info(kategorien)"))}
            for col_name, ddl in [
                ("konto_skr03", "TEXT"),
                ("konto_skr04", "TEXT"),
                ("konto_skr49", "TEXT"),
                ("euer_zeile",  "INTEGER"),
                ("eks_kategorie", "TEXT"),
                ("vorsteuer_prozent", "NUMERIC(5,2) NOT NULL DEFAULT 100"),
                ("ist_system",  "BOOLEAN NOT NULL DEFAULT 0"),
                ("aktiv",       "BOOLEAN NOT NULL DEFAULT 1"),
            ]:
                if col_name not in cols:
                    conn.execute(text(f"ALTER TABLE kategorien ADD COLUMN {col_name} {ddl}"))

            # kategorien.ust_satz_standard
            cols = {row[1] for row in conn.execute(text("PRAGMA table_info(kategorien)"))}
            if "ust_satz_standard" not in cols:
                conn.execute(text(
                    "ALTER TABLE kategorien ADD COLUMN ust_satz_standard INTEGER NOT NULL DEFAULT 0"
                ))
                for name, satz in [
                    ("Betriebseinnahmen", 19), ("Betriebseinnahmen (7%)", 7),
                    ("Büromaterial", 19), ("Büroausstattung", 19), ("Porto & Versand", 19),
                    ("Telefon & Internet", 19), ("Software & Abonnements", 19),
                    ("Steuerberatung", 19), ("Rechts- & Beratungskosten", 19),
                    ("Buchführungskosten", 19), ("Miete Büro", 19), ("Nebenkosten Büro", 19),
                    ("KFZ-Kosten", 19), ("Reisekosten", 19), ("Fremdleistungen", 19),
                    ("Werbung & Marketing", 19), ("Bewirtungskosten", 19),
                    ("Fortbildung & Fachliteratur", 19), ("Sonstige Betriebsausgaben", 19),
                    ("Anlagevermögen (Kauf)", 19),
                    ("Geringwertige Wirtschaftsgüter (GWG)", 19),
                ]:
                    conn.execute(
                        text("UPDATE kategorien SET ust_satz_standard = :s WHERE name = :n"),
                        {"s": satz, "n": name},
                    )

            # ist_entwurf-Korrektur (wurde früher versehentlich mit DEFAULT 1 angelegt)
            conn.execute(text("UPDATE rechnungen SET ist_entwurf = 0 WHERE ist_entwurf = 1"))

            conn.execute(text("PRAGMA user_version = 1"))
            conn.commit()
            print("[Migration] Schema auf Version 1 gebracht")

        if version < 2:
            conn.execute(text("PRAGMA user_version = 2"))
            conn.commit()
            print("[Migration] Schema auf Version 2 gebracht")

        if version < 3:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "berufsbezeichnung" not in cols:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN berufsbezeichnung VARCHAR(100)"))
            if "kammer_mitgliedschaft" not in cols:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN kammer_mitgliedschaft VARCHAR(200)"))
            conn.execute(text("PRAGMA user_version = 3"))
            conn.commit()
            print("[Migration] Schema auf Version 3 gebracht (berufsbezeichnung, kammer_mitgliedschaft)")

        if version < 4:
            # Artikelstamm-Tabelle anlegen
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS artikel (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    artikelnummer VARCHAR(50) UNIQUE NOT NULL,
                    typ VARCHAR(20) NOT NULL,
                    bezeichnung VARCHAR(200) NOT NULL,
                    einheit VARCHAR(50) NOT NULL DEFAULT 'Stück',
                    steuersatz NUMERIC(5,2) NOT NULL DEFAULT 19,
                    vk_brutto NUMERIC(12,2) NOT NULL,
                    vk_netto NUMERIC(12,2) NOT NULL,
                    ek_netto NUMERIC(12,2),
                    ek_brutto NUMERIC(12,2),
                    lieferant_id INTEGER REFERENCES lieferanten(id),
                    lieferanten_artikelnr VARCHAR(100),
                    hersteller VARCHAR(100),
                    artikelcode VARCHAR(100),
                    beschreibung TEXT,
                    kategorie VARCHAR(100),
                    aktiv BOOLEAN NOT NULL DEFAULT 1,
                    erstellt_am DATETIME DEFAULT CURRENT_TIMESTAMP,
                    aktualisiert_am DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            # artikel_id zu rechnungspositionen hinzufügen
            pos_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungspositionen)")).fetchall()}
            if "artikel_id" not in pos_cols:
                conn.execute(text("ALTER TABLE rechnungspositionen ADD COLUMN artikel_id INTEGER REFERENCES artikel(id)"))
            conn.execute(text("PRAGMA user_version = 4"))
            conn.commit()
            print("[Migration] Schema auf Version 4 gebracht (Artikelstamm)")

        if version < 5:
            # Typ-Umbenennung: eigenleistung → artikel
            conn.execute(text("UPDATE artikel SET typ = 'artikel' WHERE typ = 'eigenleistung'"))
            conn.execute(text("PRAGMA user_version = 5"))
            conn.commit()
            print("[Migration] Schema auf Version 5 gebracht (eigenleistung → artikel)")

        if version < 6:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "zahlungshinweis_aktiv" not in cols:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN zahlungshinweis_aktiv INTEGER NOT NULL DEFAULT 1"))
            conn.execute(text("PRAGMA user_version = 6"))
            conn.commit()
            print("[Migration] Schema auf Version 6 gebracht (unternehmen.zahlungshinweis_aktiv)")

        if version < 7:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ust_saetze (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    satz NUMERIC(5,2) NOT NULL UNIQUE,
                    bezeichnung VARCHAR(100),
                    ist_aktiv INTEGER NOT NULL DEFAULT 1,
                    ist_default INTEGER NOT NULL DEFAULT 0,
                    ist_standard INTEGER NOT NULL DEFAULT 0
                )
            """))
            # Standard-Sätze eintragen (nur wenn noch nicht vorhanden)
            for satz, bezeichnung, ist_default in [
                ("0.00", "Steuerfrei", 0),
                ("7.00", "Ermäßigt", 0),
                ("19.00", "Standard", 1),
            ]:
                existing = conn.execute(
                    text("SELECT id FROM ust_saetze WHERE satz = :s"), {"s": satz}
                ).fetchone()
                if not existing:
                    conn.execute(text(
                        "INSERT INTO ust_saetze (satz, bezeichnung, ist_aktiv, ist_default, ist_standard) "
                        "VALUES (:satz, :bez, 1, :def, 1)"
                    ), {"satz": satz, "bez": bezeichnung, "def": ist_default})
            conn.execute(text("PRAGMA user_version = 7"))
            conn.commit()
            print("[Migration] Schema auf Version 7 gebracht (ust_saetze)")

        if version < 8:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "pdf_vorlage" not in cols:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN pdf_vorlage INTEGER NOT NULL DEFAULT 0"))
            conn.execute(text("PRAGMA user_version = 8"))
            conn.commit()
            print("[Migration] Schema auf Version 8 gebracht (unternehmen.pdf_vorlage)")

        if version < 9:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "externe_belegnr" not in cols:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN externe_belegnr VARCHAR(100)"))
            conn.execute(text("PRAGMA user_version = 9"))
            conn.commit()
            print("[Migration] Schema auf Version 9 gebracht (rechnungen.externe_belegnr)")

        if version < 10:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungspositionen)")).fetchall()}
            if "kategorie_id" not in cols:
                conn.execute(text("ALTER TABLE rechnungspositionen ADD COLUMN kategorie_id INTEGER REFERENCES kategorien(id)"))
            conn.execute(text("PRAGMA user_version = 10"))
            conn.commit()
            print("[Migration] Schema auf Version 10 gebracht (rechnungspositionen.kategorie_id)")

        if version < 11:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "unterschrift_bild" not in cols:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN unterschrift_bild TEXT"))
            conn.execute(text("PRAGMA user_version = 11"))
            conn.commit()
            print("[Migration] Schema auf Version 11 gebracht (unternehmen.unterschrift_bild)")

        if version < 12:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "unterschrift_auf_rechnung" not in cols:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN unterschrift_auf_rechnung INTEGER NOT NULL DEFAULT 0"))
            conn.execute(text("PRAGMA user_version = 12"))
            conn.commit()
            print("[Migration] Schema auf Version 12 gebracht (unternehmen.unterschrift_auf_rechnung)")

        if version < 13:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "standard_zahlungsziel" not in cols:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN standard_zahlungsziel INTEGER NOT NULL DEFAULT 14"))
            conn.execute(text("PRAGMA user_version = 13"))
            conn.commit()
            print("[Migration] Schema auf Version 13 gebracht (unternehmen.standard_zahlungsziel)")

        if version < 14:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "qr_zahlung_aktiv" not in cols:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN qr_zahlung_aktiv INTEGER NOT NULL DEFAULT 0"))
            conn.execute(text("PRAGMA user_version = 14"))
            conn.commit()
            print("[Migration] Schema auf Version 14 gebracht (unternehmen.qr_zahlung_aktiv)")

        if version < 15:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(kunden)")).fetchall()}
            if "zugferd_aktiv" not in cols:
                conn.execute(text("ALTER TABLE kunden ADD COLUMN zugferd_aktiv INTEGER NOT NULL DEFAULT 0"))
            conn.execute(text("PRAGMA user_version = 15"))
            conn.commit()
            print("[Migration] Schema auf Version 15 gebracht (kunden.zugferd_aktiv)")

        if version < 16:
            kunden_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(kunden)")).fetchall()}
            if "z_hd" not in kunden_cols:
                conn.execute(text("ALTER TABLE kunden ADD COLUMN z_hd VARCHAR(200)"))
            lief_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(lieferanten)")).fetchall()}
            if "z_hd" not in lief_cols:
                conn.execute(text("ALTER TABLE lieferanten ADD COLUMN z_hd VARCHAR(200)"))
            conn.execute(text("PRAGMA user_version = 16"))
            conn.commit()
            print("[Migration] Schema auf Version 16 gebracht (kunden.z_hd, lieferanten.z_hd)")

        if version < 17:
            # Tabelle kassenbuch → journal umbenennen.
            # create_all() legt 'journal' bereits leer an (neues Model) – diese leere
            # Tabelle muss zuerst weg, bevor die alte 'kassenbuch' umbenannt werden kann.
            vorhandene = {r[0] for r in conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ))}
            conn.execute(text("DROP TRIGGER IF EXISTS protect_kassenbuch_update"))
            conn.execute(text("DROP TRIGGER IF EXISTS protect_kassenbuch_delete"))
            if 'kassenbuch' in vorhandene:
                if 'journal' in vorhandene:
                    conn.execute(text("DROP TABLE journal"))
                conn.execute(text("ALTER TABLE kassenbuch RENAME TO journal"))
            conn.execute(text("PRAGMA user_version = 17"))
            conn.commit()
            print("[Migration] Schema auf Version 17 gebracht (kassenbuch → journal)")

        if version < 18:
            # Nummernkreis-Typ und -Bezeichnung umbenennen
            conn.execute(text(
                "UPDATE nummernkreise SET typ='journal', bezeichnung='Journal' WHERE typ='kassenbuch'"
            ))
            conn.execute(text("PRAGMA user_version = 18"))
            conn.commit()
            print("[Migration] Schema auf Version 18 gebracht (nummernkreise: kassenbuch → journal)")

        if version < 19:
            # Partielle Unique-Indizes: doppelte Kunden-/Lieferantennummern verhindern.
            # WHERE NOT NULL erlaubt mehrere Datensätze ohne Nummer (NULL).
            try:
                conn.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uix_kunden_kundennummer "
                    "ON kunden(kundennummer) WHERE kundennummer IS NOT NULL"
                ))
                conn.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uix_lieferanten_lieferantennummer "
                    "ON lieferanten(lieferantennummer) WHERE lieferantennummer IS NOT NULL"
                ))
            except Exception as e:
                print(f"[Migration] Warnung: Unique-Index konnte nicht angelegt werden (Duplikate vorhanden?): {e}")
            conn.execute(text("PRAGMA user_version = 19"))
            conn.commit()
            print("[Migration] Schema auf Version 19 gebracht (unique Kunden-/Lieferantennummern)")

        if version < 20:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            for col_name, ddl in [
                ("geburtsdatum",  "DATE"),
                ("bg_nummer",     "VARCHAR(50)"),
                ("jobcenter_name","VARCHAR(200)"),
            ]:
                if col_name not in cols:
                    conn.execute(text(f"ALTER TABLE unternehmen ADD COLUMN {col_name} {ddl}"))
            conn.execute(text("PRAGMA user_version = 20"))
            conn.commit()
            print("[Migration] Schema auf Version 20 gebracht (unternehmen: geburtsdatum, bg_nummer, jobcenter_name)")

        if version < 21:
            tables = {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()}
            if "eks_einstellungen" not in tables:
                conn.execute(text(
                    "CREATE TABLE eks_einstellungen ("
                    "id INTEGER PRIMARY KEY,"
                    "taetigkeitsart_text VARCHAR(200),"
                    "taetigkeitsbeginn VARCHAR(7),"
                    "taetigkeitsende VARCHAR(7),"
                    "wohnung_gewerblich BOOLEAN NOT NULL DEFAULT 0,"
                    "gewerbliche_raeume VARCHAR(10),"
                    "gewerbliche_flaeche VARCHAR(20),"
                    "produkte_kostenfrei BOOLEAN NOT NULL DEFAULT 0,"
                    "personal_beschaeftigt BOOLEAN NOT NULL DEFAULT 0,"
                    "anzahl_beschaeftigte VARCHAR(10),"
                    "weiteres_personal BOOLEAN NOT NULL DEFAULT 0,"
                    "anzahl_weiteres_personal VARCHAR(10),"
                    "personal_ab VARCHAR(10),"
                    "umsatzsteuerpflichtig BOOLEAN NOT NULL DEFAULT 0,"
                    "zuschuss_erhalten BOOLEAN NOT NULL DEFAULT 0,"
                    "zuschuss_beantragt BOOLEAN NOT NULL DEFAULT 0,"
                    "darlehen BOOLEAN NOT NULL DEFAULT 0,"
                    "darlehen_hoehe VARCHAR(20),"
                    "darlehen_eingang VARCHAR(10),"
                    "darlehen_rueckzahlung_ab VARCHAR(10),"
                    "darlehen_tilgung VARCHAR(20),"
                    "darlehen_ausgaben_art VARCHAR(200),"
                    "darlehen_ausgaben_hoehe VARCHAR(20),"
                    "kind_ausserhalb BOOLEAN NOT NULL DEFAULT 0,"
                    "unterhalt BOOLEAN NOT NULL DEFAULT 0,"
                    "fahrten_betriebsstaette BOOLEAN NOT NULL DEFAULT 0,"
                    "km_einfach VARCHAR(10),"
                    "arbeitstage_pro_woche VARCHAR(5),"
                    "mehraufwand_verpflegung BOOLEAN NOT NULL DEFAULT 0,"
                    "arbeitstage_verpflegung VARCHAR(5),"
                    "aktualisiert_am DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
                ))
            conn.execute(text("PRAGMA user_version = 21"))
            conn.commit()
            print("[Migration] Schema auf Version 21 gebracht (eks_einstellungen)")

        if version < 22:
            # konten-Tabelle neu aufbauen: kontoart + kennung ergänzen, IBAN nullable,
            # Spalte bank → anbieter umbenennen, privat aus kontotyp entfernen
            tables = {r[0] for r in conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )).fetchall()}
            konten_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(konten)")).fetchall()} \
                if "konten" in tables else set()
            if "bank" in konten_cols:
                # Alte Schema-Version: bank → anbieter, kontoart + kennung ergänzen
                conn.execute(text("""
                    CREATE TABLE konten_new (
                        id          INTEGER PRIMARY KEY,
                        name        VARCHAR(100) NOT NULL,
                        anbieter    VARCHAR(100) NOT NULL,
                        kontoart    VARCHAR(30)  NOT NULL DEFAULT 'bank',
                        iban        VARCHAR(34),
                        bic         VARCHAR(11),
                        kennung     VARCHAR(200),
                        kontotyp    VARCHAR(20)  NOT NULL DEFAULT 'geschaeftlich',
                        ist_standard BOOLEAN     NOT NULL DEFAULT 0,
                        aktiv       BOOLEAN      NOT NULL DEFAULT 1,
                        erstellt_am DATETIME     DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now'))
                    )
                """))
                conn.execute(text("""
                    INSERT INTO konten_new (id, name, anbieter, kontoart, iban, bic, kontotyp, ist_standard, aktiv, erstellt_am)
                    SELECT id, name, bank, 'bank', iban, bic,
                        CASE WHEN kontotyp = 'privat' THEN 'mischkonto' ELSE kontotyp END,
                        ist_standard, aktiv, erstellt_am
                    FROM konten
                """))
                conn.execute(text("DROP TABLE konten"))
                conn.execute(text("ALTER TABLE konten_new RENAME TO konten"))
            elif "konten" not in tables:
                # Ganz alte DB ohne konten-Tabelle: frisch anlegen
                conn.execute(text("""
                    CREATE TABLE konten (
                        id          INTEGER PRIMARY KEY,
                        name        VARCHAR(100) NOT NULL,
                        anbieter    VARCHAR(100) NOT NULL,
                        kontoart    VARCHAR(30)  NOT NULL DEFAULT 'bank',
                        iban        VARCHAR(34),
                        bic         VARCHAR(11),
                        kennung     VARCHAR(200),
                        kontotyp    VARCHAR(20)  NOT NULL DEFAULT 'geschaeftlich',
                        ist_standard BOOLEAN     NOT NULL DEFAULT 0,
                        aktiv       BOOLEAN      NOT NULL DEFAULT 1,
                        erstellt_am DATETIME     DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now'))
                    )
                """))
            # else: Tabelle existiert bereits mit neuem Schema (create_all) → nur Index + Version
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uix_konten_iban ON konten(iban) WHERE iban IS NOT NULL"
            ))
            conn.execute(text("PRAGMA user_version = 22"))
            conn.commit()
            print("[Migration] Schema auf Version 22 gebracht (konten: kontoart, kennung, IBAN nullable)")

        if version < 23:
            # belege-Tabelle anlegen, beleg_id-FK zu rechnungen und journal
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS belege (
                    id           INTEGER PRIMARY KEY,
                    dateiname    VARCHAR(500) NOT NULL,
                    original_name VARCHAR(255) NOT NULL,
                    mime_type    VARCHAR(100),
                    dateigroesse INTEGER,
                    sha256       VARCHAR(64),
                    hochgeladen_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            rechnungen_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "beleg_id" not in rechnungen_cols:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN beleg_id INTEGER REFERENCES belege(id)"))
            journal_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(journal)")).fetchall()}
            if "beleg_id" not in journal_cols:
                conn.execute(text("ALTER TABLE journal ADD COLUMN beleg_id INTEGER REFERENCES belege(id)"))
            conn.execute(text("PRAGMA user_version = 23"))
            conn.commit()
            print("[Migration] Schema auf Version 23 gebracht (belege-Tabelle, beleg_id in rechnungen + journal)")

        if version < 24:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(kategorien)")).fetchall()}
            if "aktiv" not in cols:
                conn.execute(text("ALTER TABLE kategorien ADD COLUMN aktiv BOOLEAN NOT NULL DEFAULT 1"))
            conn.execute(text("PRAGMA user_version = 24"))
            conn.commit()
            print("[Migration] Schema auf Version 24 gebracht (kategorien.aktiv)")

        if version < 25:
            # Kontonummern SKR03/SKR04 auf DATEV-Kontenrahmen 2026 korrigieren
            korrekturen = [
                # SKR03-Korrekturen
                ("AG-Anteil Sozialversicherung",        "konto_skr03", "4130"),
                ("Minijob / geringfügige Beschäftigung","konto_skr03", "4120"),
                ("Nebenkosten Büro",                    "konto_skr03", "4228"),
                ("Miete Einrichtung",                   "konto_skr03", "4200"),
                ("Betriebliche Abfallbeseitigung",       "konto_skr03", "4969"),
                ("Reparatur Anlagevermögen",             "konto_skr03", "4260"),
                ("Geringwertige Wirtschaftsgüter (GWG)","konto_skr03", "4855"),
                ("Telefon & Internet",                  "konto_skr03", "4920"),
                ("Büromaterial",                        "konto_skr03", "4930"),
                ("Porto & Versand",                     "konto_skr03", "4910"),
                ("Büroausstattung",                     "konto_skr03", "4985"),
                ("Steuerberatung",                      "konto_skr03", "4950"),
                ("Rechts- & Beratungskosten",           "konto_skr03", "4950"),
                ("Buchführungskosten",                  "konto_skr03", "4955"),
                ("Zinsen & Darlehenskosten",            "konto_skr03", "2140"),
                # SKR04-Korrekturen
                ("Berufsgenossenschaft",                "konto_skr04", "6120"),
                ("Betriebsversicherungen",              "konto_skr04", "6400"),
                ("Nebenkosten Büro",                    "konto_skr04", "6318"),
                ("Arbeitszimmer (anteilig)",             "konto_skr04", "6348"),
                ("Miete Einrichtung",                   "konto_skr04", "6318"),
                ("KFZ-Versicherung",                    "konto_skr04", "6520"),
                ("KFZ-Kosten",                          "konto_skr04", "6530"),
                ("KFZ-Reparatur",                       "konto_skr04", "6450"),
                ("Bewirtungskosten",                    "konto_skr04", "6640"),
                ("Reisekosten – Nebenkosten",           "konto_skr04", "6644"),
                ("Telefon & Internet",                  "konto_skr04", "6805"),
                ("Porto & Versand",                     "konto_skr04", "6800"),
                ("Büroausstattung",                     "konto_skr04", "6845"),
                ("Software & Abonnements",              "konto_skr04", "6820"),
                ("Fortbildung & Fachliteratur",          "konto_skr04", "6821"),
                ("Steuerberatung",                      "konto_skr04", "6825"),
                ("Rechts- & Beratungskosten",           "konto_skr04", "6825"),
                ("Buchführungskosten",                  "konto_skr04", "6830"),
                ("Reparatur Anlagevermögen",             "konto_skr04", "6335"),
                ("Betriebliche Abfallbeseitigung",       "konto_skr04", "6859"),
                ("Geringwertige Wirtschaftsgüter (GWG)","konto_skr04", "6845"),
                ("Sonstige Betriebsausgaben",           "konto_skr04", "6850"),
                ("Zinsen & Darlehenskosten",            "konto_skr04", "7330"),
                ("Personalkosten Familienangehörige",   "konto_skr04", "6050"),
            ]
            for name, spalte, wert in korrekturen:
                conn.execute(
                    text(f"UPDATE kategorien SET {spalte} = :w WHERE name = :n"),
                    {"w": wert, "n": name},
                )
            conn.execute(text("PRAGMA user_version = 25"))
            conn.commit()
            print("[Migration] Schema auf Version 25 gebracht (Kontonummern SKR03/SKR04 auf DATEV 2026 korrigiert)")

        if version < 26:
            # EÜR-Zeilennummern auf Anlage EÜR 2025 korrigieren
            euer_korrekturen = [
                ("Betriebseinnahmen",                      12),
                ("Betriebseinnahmen (0%)",                 12),
                ("Wareneinkauf",                           27),
                ("Wareneinkauf (7%)",                      27),
                ("Wareneinkauf EU",                        27),
                ("Wareneinkauf Nicht-EU",                  27),
                ("Löhne & Gehälter",                      30),
                ("Löhne & Gehälter Teilzeit",            30),
                ("AG-Anteil Sozialversicherung",          30),
                ("Minijob / geringfügige Beschäftigung",  30),
                ("Personalkosten Familienangehörige",      30),
                ("Fremdleistungen",                        29),
                ("Miete Büro (19%)",                       39),
                ("Miete Büro (0%)",                        39),
                ("Nebenkosten Büro",                       41),
                ("Arbeitszimmer (anteilig)",               65),
                ("Betriebsversicherungen",                 49),
                ("Berufsgenossenschaft",                   49),
                ("Werbung & Marketing",                    54),
                ("KFZ-Steuer",                             69),
                ("KFZ-Versicherung",                       69),
                ("KFZ-Kosten",                             70),
                ("KFZ-Leasing",                            68),
                ("KFZ-Reparatur",                          70),
                ("Reparatur Anlagevermögen",               48),
                ("Miete Einrichtung",                      47),
                ("Betriebliche Abfallbeseitigung",         52),
                ("Reisekosten – Übernachtung",            44),
                ("Reisekosten – Nebenkosten",             44),
                ("Reisekosten – ÖPNV",                   70),
                ("Büromaterial",                           51),
                ("Büroausstattung",                        51),
                ("Porto & Versand",                        51),
                ("Geringwertige Wirtschaftsgüter (GWG)",  36),
                ("Telefon & Internet",                     43),
                ("Steuerberatung",                         46),
                ("Rechts- & Beratungskosten",             46),
                ("Buchführungskosten",                     46),
                ("Fortbildung & Fachliteratur",            45),
                ("Bankgebühren",                           60),
                ("Bewirtungskosten",                       63),
                ("Sonstige Betriebsausgaben",              60),
                ("Zinsen & Darlehenskosten",               56),
                ("Umsatzsteuer-Zahlung FA",                58),
            ]
            for name, zeile in euer_korrekturen:
                conn.execute(
                    text("UPDATE kategorien SET euer_zeile = :z WHERE name = :n"),
                    {"z": zeile, "n": name},
                )
            conn.execute(text("PRAGMA user_version = 26"))
            conn.commit()
            print("[Migration] Schema auf Version 26 gebracht (EÜR-Zeilennummern auf Anlage EÜR 2025 korrigiert)")

        if version < 27:
            # kategorien: Default-Spalten + user_modified-Flags
            cols_kat = {r[1] for r in conn.execute(text("PRAGMA table_info(kategorien)")).fetchall()}
            for col, ddl in [
                ("konto_skr03_default",  "ALTER TABLE kategorien ADD COLUMN konto_skr03_default TEXT"),
                ("konto_skr04_default",  "ALTER TABLE kategorien ADD COLUMN konto_skr04_default TEXT"),
                ("user_modified_skr03",  "ALTER TABLE kategorien ADD COLUMN user_modified_skr03 INTEGER NOT NULL DEFAULT 0"),
                ("user_modified_skr04",  "ALTER TABLE kategorien ADD COLUMN user_modified_skr04 INTEGER NOT NULL DEFAULT 0"),
            ]:
                if col not in cols_kat:
                    conn.execute(text(ddl))
            # Aktuelle Werte als Default einfrieren (einmalig)
            conn.execute(text("UPDATE kategorien SET konto_skr03_default = konto_skr03 WHERE konto_skr03_default IS NULL"))
            conn.execute(text("UPDATE kategorien SET konto_skr04_default = konto_skr04 WHERE konto_skr04_default IS NULL"))
            # journal: Kontonummer-Snapshot-Spalten
            cols_j = {r[1] for r in conn.execute(text("PRAGMA table_info(journal)")).fetchall()}
            for col, ddl in [
                ("konto_skr03", "ALTER TABLE journal ADD COLUMN konto_skr03 TEXT"),
                ("konto_skr04", "ALTER TABLE journal ADD COLUMN konto_skr04 TEXT"),
            ]:
                if col not in cols_j:
                    conn.execute(text(ddl))
            conn.execute(text("PRAGMA user_version = 27"))
            conn.commit()
            print("[Migration] Schema auf Version 27 gebracht (kategorien: Default-Konten + user_modified; journal: konto-Snapshot)")

        if version < 28:
            # journal: USt-Gegenkonten-Snapshot
            cols_j = {r[1] for r in conn.execute(text("PRAGMA table_info(journal)")).fetchall()}
            for col, ddl in [
                ("konto_ust_skr03", "ALTER TABLE journal ADD COLUMN konto_ust_skr03 TEXT"),
                ("konto_ust_skr04", "ALTER TABLE journal ADD COLUMN konto_ust_skr04 TEXT"),
            ]:
                if col not in cols_j:
                    conn.execute(text(ddl))
            conn.execute(text("PRAGMA user_version = 28"))
            conn.commit()
            print("[Migration] Schema auf Version 28 gebracht (journal: USt-Gegenkonto-Snapshot)")

        if version < 29:
            # konten: stray 'bank'-Spalte entfernen falls Migration 22 sie nicht bereinigt hat
            konten_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(konten)")).fetchall()}
            if "bank" in konten_cols:
                conn.execute(text("""
                    CREATE TABLE konten_new (
                        id           INTEGER PRIMARY KEY,
                        name         VARCHAR(100) NOT NULL,
                        anbieter     VARCHAR(100) NOT NULL,
                        kontoart     VARCHAR(30)  NOT NULL DEFAULT 'bank',
                        iban         VARCHAR(34),
                        bic          VARCHAR(11),
                        kennung      VARCHAR(200),
                        kontotyp     VARCHAR(20)  NOT NULL DEFAULT 'geschaeftlich',
                        ist_standard BOOLEAN      NOT NULL DEFAULT 0,
                        aktiv        BOOLEAN      NOT NULL DEFAULT 1,
                        erstellt_am  DATETIME     DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now'))
                    )
                """))
                anbieter_src = "anbieter" if "anbieter" in konten_cols else "bank"
                conn.execute(text(f"""
                    INSERT INTO konten_new (id, name, anbieter, kontoart, iban, bic, kennung, kontotyp, ist_standard, aktiv, erstellt_am)
                    SELECT id, name, {anbieter_src}, kontoart, iban, bic, kennung, kontotyp, ist_standard, aktiv, erstellt_am
                    FROM konten
                """))
                conn.execute(text("DROP TABLE konten"))
                conn.execute(text("ALTER TABLE konten_new RENAME TO konten"))
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uix_konten_iban ON konten(iban) WHERE iban IS NOT NULL"))
                print("[Migration] konten: stray 'bank'-Spalte entfernt")
            conn.execute(text("PRAGMA user_version = 29"))
            conn.commit()
            print("[Migration] Schema auf Version 29 gebracht (konten: bank-Spalte bereinigt)")

        if version < 30:
            # rechnungen: leistungsdatum → leistung_von umbenennen + leistung_bis hinzufügen
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "leistungsdatum" in cols and "leistung_von" not in cols:
                conn.execute(text("ALTER TABLE rechnungen RENAME COLUMN leistungsdatum TO leistung_von"))
            if "leistung_bis" not in cols:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN leistung_bis DATE"))
            conn.execute(text("PRAGMA user_version = 30"))
            conn.commit()
            print("[Migration] Schema auf Version 30 gebracht (leistungsdatum → leistung_von + leistung_bis)")

        if version < 31:
            # Skonto: unternehmen (Standard), kunden (kundenspezifisch), rechnungen (je Rechnung)
            cols_unt = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            for col, ddl in [
                ("standard_skonto_prozent", "ALTER TABLE unternehmen ADD COLUMN standard_skonto_prozent NUMERIC(5,2)"),
                ("standard_skonto_tage",    "ALTER TABLE unternehmen ADD COLUMN standard_skonto_tage INTEGER"),
            ]:
                if col not in cols_unt:
                    conn.execute(text(ddl))
            cols_kun = {r[1] for r in conn.execute(text("PRAGMA table_info(kunden)")).fetchall()}
            for col, ddl in [
                ("skonto_prozent", "ALTER TABLE kunden ADD COLUMN skonto_prozent NUMERIC(5,2)"),
                ("skonto_tage",    "ALTER TABLE kunden ADD COLUMN skonto_tage INTEGER"),
            ]:
                if col not in cols_kun:
                    conn.execute(text(ddl))
            cols_rec = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            for col, ddl in [
                ("skonto_prozent", "ALTER TABLE rechnungen ADD COLUMN skonto_prozent NUMERIC(5,2)"),
                ("skonto_tage",    "ALTER TABLE rechnungen ADD COLUMN skonto_tage INTEGER"),
            ]:
                if col not in cols_rec:
                    conn.execute(text(ddl))
            conn.execute(text("PRAGMA user_version = 31"))
            conn.commit()
            print("[Migration] Schema auf Version 31 gebracht (Skonto: unternehmen + kunden + rechnungen)")

        if version < 32:
            # artikel: kategorie → gruppe umbenennen
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(artikel)")).fetchall()}
            if "kategorie" in cols and "gruppe" not in cols:
                conn.execute(text("ALTER TABLE artikel RENAME COLUMN kategorie TO gruppe"))
            conn.execute(text("PRAGMA user_version = 32"))
            conn.commit()
            print("[Migration] Schema auf Version 32 gebracht (artikel: kategorie → gruppe)")

        if version < 33:
            # Neue Tabelle artikel_gruppen
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS artikel_gruppen (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    typ TEXT NOT NULL,
                    name TEXT NOT NULL,
                    aktiv BOOLEAN NOT NULL DEFAULT 1,
                    erstellt_am DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(typ, name)
                )
            """))
            # FK-Spalte gruppe_id zu artikel hinzufügen
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(artikel)")).fetchall()}
            if "gruppe_id" not in cols:
                conn.execute(text("ALTER TABLE artikel ADD COLUMN gruppe_id INTEGER REFERENCES artikel_gruppen(id)"))
            # Bestehende Text-Werte in artikel_gruppen migrieren
            if "gruppe" in cols:
                rows = conn.execute(text(
                    "SELECT DISTINCT typ, gruppe FROM artikel WHERE gruppe IS NOT NULL AND gruppe != ''"
                )).fetchall()
                for typ, name in rows:
                    conn.execute(text(
                        "INSERT OR IGNORE INTO artikel_gruppen (typ, name) VALUES (:typ, :name)"
                    ), {"typ": typ, "name": name})
                conn.execute(text("""
                    UPDATE artikel SET gruppe_id = (
                        SELECT id FROM artikel_gruppen
                        WHERE artikel_gruppen.typ = artikel.typ
                        AND artikel_gruppen.name = artikel.gruppe
                    )
                    WHERE gruppe IS NOT NULL AND gruppe != ''
                """))
                conn.execute(text("ALTER TABLE artikel DROP COLUMN gruppe"))
            conn.execute(text("PRAGMA user_version = 33"))
            conn.commit()
            print("[Migration] Schema auf Version 33 gebracht (artikel_gruppen + artikel.gruppe_id FK)")

        if version < 34:
            # rechnungen: storno_grund hinzufügen
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "storno_grund" not in cols:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN storno_grund VARCHAR(500)"))
            conn.execute(text("PRAGMA user_version = 34"))
            conn.commit()
            print("[Migration] Schema auf Version 34 gebracht (rechnungen.storno_grund)")

        if version < 35:
            # kategorien: beschreibung hinzufügen + Default-Beispiele für Standardkategorien
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(kategorien)")).fetchall()}
            if "beschreibung" not in cols:
                conn.execute(text("ALTER TABLE kategorien ADD COLUMN beschreibung TEXT"))
            # Default-Beschreibungen für Standardkategorien (nur setzen wenn noch leer)
            defaults = {
                "Betriebseinnahmen (19%)":        "z. B. Honorare, Rechnungen an Kunden mit 19 % USt (Regelbesteuerung)",
                "Betriebseinnahmen (7%)":         "z. B. Einnahmen mit 7 % USt (Lebensmittel, Bücher, Zeitschriften)",
                "Betriebseinnahmen (0%)":         "z. B. Einnahmen als Kleinunternehmer (§ 19 UStG) oder steuerfreie Umsätze",
                "Sonstige Einnahmen":             "z. B. Entschädigungen, Schadensersatz, einmalige Nebeneinnahmen",
                "Zuwendungen von Dritten":        "z. B. Fördermittel, Zuschüsse, Transferleistungen",
                "Umsatzsteuer-Erstattung FA":     "Erstattung vom Finanzamt nach USt-Voranmeldung (Überschuss der Vorsteuer)",
                "Vorsteuererstattung FA":         "Erstattung vom Finanzamt nach Voranmeldung",
                "Eigenverbrauch von Waren (19%)": "Entnahme von Waren für private Zwecke (19 % USt auf Einkaufspreis)",
                "Eigenverbrauch von Waren (7%)":  "Entnahme von Waren für private Zwecke (7 % USt auf Einkaufspreis)",
                "Wareneinkauf":                   "z. B. Waren für den Wiederverkauf (19 % USt)",
                "Wareneinkauf (7%)":              "z. B. Waren für den Wiederverkauf mit 7 % USt",
                "Wareneinkauf EU":                "z. B. Waren von EU-Lieferanten (innergemeinschaftlicher Erwerb); Käufer muss gültige USt-IdNr haben",
                "Innergemeinschaftliche Lieferungen": "Lieferung an Unternehmen mit USt-IdNr in einem anderen EU-Mitgliedstaat (§4 Nr. 1b UStG); 0 % USt; UStVA KZ 41; Zusammenfassende Meldung erforderlich",
                "EU-Dienstleistungen (§13b Abs. 1)":  "Bezug von Dienstleistungen eines im EU-Ausland ansässigen Unternehmers (z.B. Google Ads, AWS, Beratung). Reverse Charge: Du schuldest die USt (KZ 46/47) und kannst sie als Vorsteuer (KZ 67) abziehen. Rechnungsbetrag = Nettobetrag.",
                "Bauleistungen / §13b Abs. 2":         "Bauleistungen, Gebäudereinigung, Sicherheitsdienstleistungen, Metallieferungen – auch von inländischen Unternehmen. Reverse Charge: Leistungsempfänger schuldet die USt (KZ 84/85), Vorsteuer KZ 67. Rechnungsbetrag = Nettobetrag.",
                "Wareneinkauf Nicht-EU":          "z. B. Importe aus Drittländern (Einfuhrumsatzsteuer beachten)",
                "Löhne & Gehälter":              "z. B. Bruttogehalt Vollzeitkräfte inkl. Sozialversicherungsabgaben",
                "Löhne & Gehälter Teilzeit":     "z. B. Bruttogehalt Teilzeitkräfte inkl. Sozialversicherungsabgaben",
                "Minijob / geringfügige Beschäftigung": "z. B. Aushilfen bis 556 €/Monat (pauschale Abgaben)",
                "Personalkosten Familienangehörige": "z. B. Arbeitsvertrag mit Ehepartner oder Kindern (Fremdvergleich beachten)",
                "AG-Anteil Sozialversicherung":  "z. B. Arbeitgeberanteil Renten-, Kranken-, Pflege-, Arbeitslosenversicherung",
                "Fremdleistungen":               "z. B. Subunternehmer, externe Dienstleister, Honorare Dritter",
                "Miete Büro (19%)":              "z. B. Büromiete mit 19 % USt (gewerbliche Vermietung)",
                "Miete Büro (0%)":               "z. B. Büromiete ohne USt (private Vermietung)",
                "Nebenkosten Büro":              "z. B. Strom, Wasser, Heizung, Reinigung für Büroräume",
                "Arbeitszimmer (anteilig)":      "z. B. anteiliger Abzug bei Homeoffice: Fläche des Arbeitszimmers ÷ Gesamtfläche × Jahresmiete",
                "Büromaterial":                  "z. B. Stifte, Papier, Druckerpatronen, Ordner, Heftklammern, Briefumschläge",
                "Büroausstattung":               "z. B. Schreibtisch, Bürostühle, Regale, Lampen (über GWG-Grenze: Abschreibung nötig)",
                "Porto & Versand":               "z. B. Briefmarken, Paketversand, Kurierdienste",
                "Geringwertige Wirtschaftsgüter (GWG)": "z. B. Technik und Einrichtung bis 800 € netto – sofort abschreibbar im Kaufjahr",
                "Telefon & Internet":            "z. B. Mobilfunkvertrag, DSL/Glasfaser, VOIP, Videokonferenz-Abo",
                "Werbung & Marketing":           "z. B. Anzeigen, Flyer, Visitenkarten, Website, Social-Media-Werbung, Messen",
                "KFZ-Kosten":                    "z. B. Kraftstoff (Benzin/Diesel/Strom), Motoröl für betriebliche Fahrten",
                "KFZ-Steuer":                    "z. B. jährliche Kfz-Steuer für betrieblich genutzte Fahrzeuge",
                "KFZ-Versicherung":              "z. B. Haftpflicht- und Kaskoversicherung für betriebliche Fahrzeuge",
                "KFZ-Leasing":                   "z. B. monatliche Leasingraten für betrieblich genutzte Fahrzeuge",
                "KFZ-Reparatur":                 "z. B. Werkstattrechnung, TÜV/HU, Reifenwechsel, Reifenkauf",
                "Fahrtkosten Privat-PKW (0,10 €/km)": "z. B. betriebliche Fahrten mit privatem PKW – 0,10 €/km Pauschale (Fahrtenbuch nötig)",
                "Reisekosten – Übernachtung":   "z. B. Hotel, Pension, Ferienwohnung auf Dienstreisen",
                "Reisekosten – Nebenkosten":    "z. B. Taxi, Mietwagen, Gepäckgebühren, Reiseversicherung auf Dienstreisen",
                "Reisekosten – ÖPNV":           "z. B. Bahn, Bus, U-Bahn, Straßenbahn für betriebliche Fahrten",
                "Verpflegungsmehraufwand":      "z. B. Tagespauschalen auf Dienstreisen: 8 € (bis 8 Std.), 14 € (ab 8 Std.), 28 € (ganztägig)",
                "Bewirtungskosten":             "z. B. Geschäftsessen mit Kunden oder Partnern; ertragsteuerlich 70 % abziehbar (§ 4 Abs. 5 Nr. 2 EStG), Vorsteuer zu 100 % abzugsfähig; Anlass und Teilnehmer auf dem Beleg notieren",
                "Bewirtungskosten (nicht abzugsfähig)": "Der ertragsteuerlich nicht abziehbare 30 %-Anteil von Bewirtungskosten (§ 4 Abs. 5 Nr. 2 EStG); Vorsteuer trotzdem zu 100 % abzugsfähig",
                "Steuerberatung":               "z. B. Steuerberater-Honorar, Jahresabschluss, Lohnbuchhaltung",
                "Rechts- & Beratungskosten":   "z. B. Anwaltskosten, Unternehmensberatung, Notargebühren",
                "Buchführungskosten":           "z. B. Buchhaltungssoftware-Abo, externe Buchführung",
                "Betriebsversicherungen":       "z. B. Betriebshaftpflicht, Inhaltsversicherung, Cyberversicherung, Rechtsschutz",
                "Berufsgenossenschaft":         "z. B. gesetzliche Unfallversicherung (Beiträge zur Berufsgenossenschaft)",
                "Fortbildung & Fachliteratur":  "z. B. Kurse, Seminare, Webinare, Fachbücher, Fachjournale, Online-Lernplattformen",
                "Software & Abonnements":       "z. B. Office-Lizenzen, Cloud-Dienste, SaaS-Tools, App-Abos",
                "Bankgebühren":                 "z. B. Kontoführungsgebühren, Überweisungsgebühren, EC-Terminal-Kosten",
                "Zinsen & Darlehenskosten":    "z. B. Bankzinsen auf Betriebskredit, Kreditgebühren, Finanzierungskosten",
                "Kredittilgung":               "z. B. monatliche Tilgungsraten – kein Betriebsaufwand, nur Geldabfluss",
                "Umsatzsteuer-Zahlung FA":     "z. B. monatliche oder quartalsweise USt-Vorauszahlung ans Finanzamt",
                "Sonstige Betriebsausgaben":   "z. B. Kleinbeträge ohne eigene Kategorie – bei wachsenden Beträgen eigene Kategorie anlegen",
                "Reparatur Anlagevermögen":    "z. B. Reparatur von Maschinen, Geräten, IT-Ausstattung, Gebäudeteilen",
                "Miete Einrichtung":           "z. B. Miete oder Leasing von Büroausstattung, Maschinen oder Geräten",
                "Betriebliche Abfallbeseitigung": "z. B. Entsorgungskosten, Containerdienst, Sonderabfall-Entsorgung",
                "Mitgliedsbeiträge":           "z. B. IHK-Beitrag, Berufsverbände, Wirtschaftsvereinigungen, Fachverbände",
                "Spenden (betrieblich)":       "Betrieblich veranlasste Spenden (z. B. über Berufsverband). Achtung: Private Spenden sind keine Betriebsausgaben und gehören nicht hierher – sie werden in der Einkommensteuererklärung als Sonderausgaben abgesetzt.",
                "Gewerbesteuer":               "z. B. vierteljährliche Gewerbesteuer-Vorauszahlungen oder Jahresausgleich",
                "Anlagevermögen (Kauf)":       "z. B. Computer, Maschinen, Geräte über 800 € netto – für Fahrzeuge bitte 'KFZ (Kauf)' verwenden (Anlage AVEÜR)",
                "KFZ (Kauf)":                  "Kauf eines Kraftfahrzeugs über 800 € netto (Anlage AVEÜR: Kategorie Kraftfahrzeuge) – laufende KFZ-Kosten separat unter KFZ-Kosten / KFZ-Versicherung etc. buchen",
                "EDV / Software (Sofortabschreibung)": "Hardware (PC, Laptop, Tablet, Smartphone, Drucker) und Software. Zweistufig buchen: 1. Kauf hier als Anlage (SKR03 0490), 2. im selben Jahr volle AfA über 'Abschreibungen (AfA)'. Wahlrecht auf Nutzungsdauer 1 Jahr nach BMF 26.02.2021 (§ 7 Abs. 1 EStG) – muss ins Bestandsverzeichnis, KEIN GWG!",
                "Forderungsausfall":           "Uneinbringliche Forderungen (Kundeninsolvenz, endgültige Zahlungsverweigerung). Nur für USt-Pflichtige: Korrekturbuchung nach §17 UStG wird automatisch erstellt.",
                "Abschreibungen (AfA)":        "z. B. Jahres-AfA für Wirtschaftsgüter des Anlagevermögens (vom Steuerberater berechnet)",
                "Investition aus Zuwendung Dritter": "z. B. Anschaffungen die aus Fördergeldern oder Zuschüssen finanziert wurden",
                "Gewährte Skonti":             "Skonto den du Kunden gewährst – wird automatisch beim Buchen einer Zahlung mit Skonto zugewiesen (Erlösschmälerung)",
                "Erhaltene Skonti":            "Skonto den du von Lieferanten erhältst – wird automatisch beim Buchen einer Eingangsrechnung mit Skonto zugewiesen (Aufwandsminderung)",
                "Privatentnahme":              "z. B. Bargeld-Entnahme für private Zwecke – kein Betriebsaufwand",
                "Privateinlage":               "z. B. Einzahlung eigener privater Mittel ins Unternehmen",
                "Einkommensteuer-Vorauszahlung": "vierteljährliche Vorauszahlungen ans Finanzamt (fällig: 10. März, 10. Juni, 10. September, 10. Dezember)",
                "Krankenversicherung (Pflicht)": "z. B. Beiträge zur gesetzlichen oder privaten Krankenversicherung",
                "Pflegeversicherung (Pflicht)": "z. B. Beiträge zur gesetzlichen oder privaten Pflegeversicherung",
                "Rentenversicherung (freiwillig)": "z. B. freiwillige Beiträge zur gesetzlichen Rentenversicherung",
                "Riester-Beiträge":            "z. B. Beiträge zur Riester-Rente (staatlich gefördert, Zulageantrag nötig)",
                "Sonstige Absetzungen":        "z. B. weitere abzugsfähige Versicherungen oder Vorsorgeaufwendungen",
                "Umsatzsteuer (vereinnahmt)":  "Korrekturbuchung für vereinnahmte Umsatzsteuer, die ans Finanzamt abgeführt wird",
                "USt auf Eigenverbrauch":      "Korrekturbuchung für Umsatzsteuer auf Eigenverbrauch von Waren",
            }
            for name, beschreibung in defaults.items():
                conn.execute(text(
                    "UPDATE kategorien SET beschreibung = :b WHERE name = :n AND (beschreibung IS NULL OR beschreibung = '')"
                ), {"n": name, "b": beschreibung})
            conn.execute(text("PRAGMA user_version = 35"))
            conn.commit()
            print(f"[Migration] Schema auf Version 35 gebracht (kategorien.beschreibung + {len(defaults)} Default-Beschreibungen)")

        if version < 36:
            # Fehlende Beschreibungen für Kategorien mit abweichendem Namen nachrüsten
            name_fixes = {
                "Betriebseinnahmen":        "z. B. Honorare, Rechnungen an Kunden (Regelbesteuerung)",
                "Fahrtkosten (km-Pauschale)": "z. B. betriebliche Fahrten mit privatem PKW – 0,30 €/km Pauschale (Fahrtenbuch oder Aufzeichnung nötig)",
            }
            for name, beschreibung in name_fixes.items():
                conn.execute(text(
                    "UPDATE kategorien SET beschreibung = :b WHERE name = :n AND (beschreibung IS NULL OR beschreibung = '')"
                ), {"n": name, "b": beschreibung})
            conn.execute(text("PRAGMA user_version = 36"))
            conn.commit()
            print("[Migration] Schema auf Version 36 gebracht (fehlende Kategorie-Beschreibungen ergänzt)")

        if version < 37:
            # Gutschrift: dokument_typ + gutschrift_zu_rechnung_id
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "dokument_typ" not in cols:
                conn.execute(text(
                    "ALTER TABLE rechnungen ADD COLUMN dokument_typ VARCHAR(20) NOT NULL DEFAULT 'Rechnung'"
                ))
            if "gutschrift_zu_rechnung_id" not in cols:
                conn.execute(text(
                    "ALTER TABLE rechnungen ADD COLUMN gutschrift_zu_rechnung_id INTEGER REFERENCES rechnungen(id)"
                ))
            conn.execute(text("PRAGMA user_version = 37"))
            conn.commit()
            print("[Migration] Schema auf Version 37 gebracht (rechnungen: dokument_typ + gutschrift_zu_rechnung_id)")

        if version < 38:
            # Differenzbesteuerung §25a UStG: Flag auf Artikel und Rechnungspositionen
            cols_a = {r[1] for r in conn.execute(text("PRAGMA table_info(artikel)")).fetchall()}
            if "differenzbesteuerung" not in cols_a:
                conn.execute(text(
                    "ALTER TABLE artikel ADD COLUMN differenzbesteuerung BOOLEAN NOT NULL DEFAULT 0"
                ))
            cols_p = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungspositionen)")).fetchall()}
            if "differenzbesteuerung" not in cols_p:
                conn.execute(text(
                    "ALTER TABLE rechnungspositionen ADD COLUMN differenzbesteuerung BOOLEAN NOT NULL DEFAULT 0"
                ))
            conn.execute(text("PRAGMA user_version = 38"))
            conn.commit()
            print("[Migration] Schema auf Version 38 gebracht (differenzbesteuerung §25a UStG)")

        if version < 39:
            # 'Bewirtungskosten (nicht abzugsfähig)': eks_kategorie war fälschlicherweise 'B14_5'.
            # Der steuerlich nicht abziehbare Anteil ist beim Jobcenter keine notwendige Betriebsausgabe
            # und darf die EKS-Einkommensberechnung nicht mindern.
            conn.execute(text("""
                UPDATE kategorien
                SET eks_kategorie = NULL
                WHERE name = 'Bewirtungskosten (nicht abzugsfähig)'
                  AND eks_kategorie = 'B14_5'
            """))
            conn.execute(text("PRAGMA user_version = 39"))
            conn.commit()
            print("[Migration] Schema auf Version 39 gebracht (Bewirtungskosten nicht abzugsfähig: eks_kategorie → NULL)")

        if version < 40:
            # journal.vorsteuer_betrag: tatsächlich abziehbarer Vorsteuer-Anteil
            # Berücksichtigt vorsteuer_prozent der Kategorie (z.B. 70% bei Bewirtungskosten).
            # Für ältere Einträge bleibt der Wert 0 – korrekte Werte ab diesem Release.
            cols_j = {r[1] for r in conn.execute(text("PRAGMA table_info(journal)")).fetchall()}
            if "vorsteuer_betrag" not in cols_j:
                conn.execute(text(
                    "ALTER TABLE journal ADD COLUMN vorsteuer_betrag NUMERIC(12,2) NOT NULL DEFAULT 0"
                ))
            conn.execute(text("PRAGMA user_version = 40"))
            conn.commit()
            print("[Migration] Schema auf Version 40 gebracht (journal.vorsteuer_betrag)")

        if version < 41:
            # Privatentnahme / Privateinlage: euer_zeile war None, muss 106/107 sein.
            # Anlage EÜR 2025 Zeile 106 = Entnahmen, Zeile 107 = Einlagen (Hinweiszeilen,
            # fließen nicht in den Gewinn ein, müssen aber ausgewiesen werden).
            conn.execute(text(
                "UPDATE kategorien SET euer_zeile = 106 WHERE name = 'Privatentnahme' AND euer_zeile IS NULL"
            ))
            conn.execute(text(
                "UPDATE kategorien SET euer_zeile = 107 WHERE name = 'Privateinlage' AND euer_zeile IS NULL"
            ))
            conn.execute(text("PRAGMA user_version = 41"))
            conn.commit()
            print("[Migration] Schema auf Version 41 (Privatentnahme Z106 / Privateinlage Z107)")

        if version < 42:
            # EDV / Software (Sofortabschreibung): war fälschlicherweise kontenart=Aufwand.
            # BMF-Schreiben 26.02.2021 gewährt Wahlrecht auf Nutzungsdauer 1 Jahr (§ 7 Abs. 1 EStG),
            # ist aber KEIN GWG (§ 6 Abs. 2 EStG). Wirtschaftsgut muss ins Bestandsverzeichnis,
            # Buchung läuft über Anlagekonto + separate AfA im selben Jahr.
            # → kontenart Anlage, SKR03 0650 (fehlerhaft, v44 korrigiert auf 0490), SKR04 0490 (fehlerhaft, v44 korrigiert auf 0650).
            conn.execute(text("""
                UPDATE kategorien
                SET kontenart = 'Anlage',
                    konto_skr03_default = '0650',
                    konto_skr04_default = '0490',
                    konto_skr03 = CASE WHEN user_modified_skr03 = 0 THEN '0650' ELSE konto_skr03 END,
                    konto_skr04 = CASE WHEN user_modified_skr04 = 0 THEN '0490' ELSE konto_skr04 END,
                    eks_kategorie = 'B8',
                    euer_zeile = NULL
                WHERE name = 'EDV / Software (Sofortabschreibung)' AND ist_system = 1
            """))
            conn.execute(text("PRAGMA user_version = 42"))
            conn.commit()
            print("[Migration] Schema auf Version 42 (EDV/Software: Aufwand→Anlage, B10→B8)")

        if version < 43:
            # journal.km_anzahl: Kilometeranzahl für km-Pauschale-Buchungen (Fahrtkosten Privat-PKW).
            # Optional – nur bei Fahrtkosten relevant. EÜR rechnet km × 0,30 €, EKS km × 0,10 €.
            # Ohne Eintrag: EKS-Berechnung fällt auf brutto_betrag zurück (Rückwärtskompatibilität).
            cols_j = {r[1] for r in conn.execute(text("PRAGMA table_info(journal)")).fetchall()}
            if "km_anzahl" not in cols_j:
                conn.execute(text("ALTER TABLE journal ADD COLUMN km_anzahl NUMERIC(10,1)"))
            conn.execute(text("PRAGMA user_version = 43"))
            conn.commit()
            print("[Migration] Schema auf Version 43 (journal.km_anzahl fuer Fahrtkosten/EKS B6_5)")

        if version < 44:
            # EDV / Software (Sofortabschreibung): SKR03 war fälschlicherweise 0650
            # (= Verbindlichkeiten gegenüber Kreditinstituten, Passivkonto!), SKR04 war 0490
            # (existiert im SKR04 als Anlagenkonto nicht).
            # Korrekt: SKR03 0490 (Sonstige Betriebs- und Geschäftsausstattung),
            #          SKR04 0650 (Büroeinrichtung).
            conn.execute(text("""
                UPDATE kategorien
                SET konto_skr03_default = '0490',
                    konto_skr04_default = '0650',
                    konto_skr03 = CASE WHEN user_modified_skr03 = 0 THEN '0490' ELSE konto_skr03 END,
                    konto_skr04 = CASE WHEN user_modified_skr04 = 0 THEN '0650' ELSE konto_skr04 END
                WHERE name = 'EDV / Software (Sofortabschreibung)' AND ist_system = 1
            """))
            conn.execute(text("PRAGMA user_version = 44"))
            conn.commit()
            print("[Migration] Schema auf Version 44 (EDV/Software: SKR03 0490, SKR04 0650 korrigiert)")

        if version < 45:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(belege)")).fetchall()}
            if "beleg_pdfa_pfad" not in cols:
                conn.execute(text("ALTER TABLE belege ADD COLUMN beleg_pdfa_pfad VARCHAR(500)"))
            conn.execute(text("PRAGMA user_version = 45"))
            conn.commit()
            print("[Migration] Schema auf Version 45 (belege.beleg_pdfa_pfad – PDF/A-3 GoBD-Archivpfad)")

        if version < 46:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "w_idnr" not in cols:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN w_idnr VARCHAR(20)"))
            if "voranmeldungsrhythmus" not in cols:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN voranmeldungsrhythmus VARCHAR(12) NOT NULL DEFAULT 'quartal'"))
            conn.execute(text("PRAGMA user_version = 46"))
            conn.commit()
            print("[Migration] Schema auf Version 46 (unternehmen: w_idnr, voranmeldungsrhythmus)")

        if version < 47:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(journal)")).fetchall()}
            if "ist_ig_erwerb" not in cols:
                conn.execute(text("ALTER TABLE journal ADD COLUMN ist_ig_erwerb INTEGER NOT NULL DEFAULT 0"))
            conn.execute(text("PRAGMA user_version = 47"))
            conn.commit()
            print("[Migration] Schema auf Version 47 (journal.ist_ig_erwerb – innergemeinschaftlicher Erwerb)")

        if version < 48:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(journal)")).fetchall()}
            if "ust_sonderfall" not in cols:
                conn.execute(text("ALTER TABLE journal ADD COLUMN ust_sonderfall VARCHAR(20)"))
            # ist_ig_erwerb=1 → ust_sonderfall='ig_erwerb'
            conn.execute(text(
                "UPDATE journal SET ust_sonderfall = 'ig_erwerb' "
                "WHERE ist_ig_erwerb = 1 AND (ust_sonderfall IS NULL OR ust_sonderfall = '')"
            ))
            conn.execute(text("PRAGMA user_version = 48"))
            conn.commit()
            print("[Migration] Schema auf Version 48 (journal.ust_sonderfall: ig_erwerb|13b_abs1|13b_abs2)")

        if version < 49:
            cols_rp = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungspositionen)")).fetchall()}
            if "ek_netto_25a" not in cols_rp:
                conn.execute(text("ALTER TABLE rechnungspositionen ADD COLUMN ek_netto_25a NUMERIC(12,2)"))
            cols_j = {r[1] for r in conn.execute(text("PRAGMA table_info(journal)")).fetchall()}
            if "marge_25a_brutto" not in cols_j:
                conn.execute(text("ALTER TABLE journal ADD COLUMN marge_25a_brutto NUMERIC(12,2)"))
            conn.execute(text("PRAGMA user_version = 49"))
            conn.commit()
            print("[Migration] Schema auf Version 49 (§25a: rechnungspositionen.ek_netto_25a, journal.marge_25a_brutto)")

        if version < 50:
            cols_rp = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungspositionen)")).fetchall()}
            if "ust_satz_25a" not in cols_rp:
                conn.execute(text("ALTER TABLE rechnungspositionen ADD COLUMN ust_satz_25a NUMERIC(5,2)"))
            conn.execute(text("PRAGMA user_version = 50"))
            conn.commit()
            print("[Migration] Schema auf Version 50 (rechnungspositionen.ust_satz_25a: nominaler USt-Satz für §25a-Margensteuer)")

        if version < 51:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS kunden_lieferadressen (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kunde_id INTEGER NOT NULL REFERENCES kunden(id) ON DELETE CASCADE,
                    bezeichnung VARCHAR(100),
                    z_hd VARCHAR(200),
                    strasse VARCHAR(200),
                    hausnummer VARCHAR(20),
                    plz VARCHAR(10),
                    ort VARCHAR(100),
                    land VARCHAR(2) NOT NULL DEFAULT 'DE',
                    ist_standard BOOLEAN NOT NULL DEFAULT 0,
                    erstellt_am DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_kunden_lieferadressen_kunde_id ON kunden_lieferadressen(kunde_id)"))
            conn.execute(text("PRAGMA user_version = 51"))
            conn.commit()
            print("[Migration] Schema auf Version 51 (kunden_lieferadressen: separate Lieferadressen pro Kunde)")

        if version < 52:
            unt52 = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            re52  = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "lieferschein_aktiv" not in unt52:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN lieferschein_aktiv BOOLEAN NOT NULL DEFAULT 0"))
            if "lieferschein_zu_rechnung_id" not in re52:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN lieferschein_zu_rechnung_id INTEGER REFERENCES rechnungen(id)"))
            conn.execute(text("PRAGMA user_version = 52"))
            conn.commit()
            print("[Migration] Schema auf Version 52 (Lieferschein: lieferschein_aktiv + lieferschein_zu_rechnung_id)")

        if version < 53:
            re53 = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "lieferadresse_id" not in re53:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN lieferadresse_id INTEGER REFERENCES kunden_lieferadressen(id)"))
            conn.execute(text("PRAGMA user_version = 53"))
            conn.commit()
            print("[Migration] Schema auf Version 53 (rechnungen.lieferadresse_id: Lieferadresse auf Lieferschein)")

        if version < 55:
            unt55 = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            re55  = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "angebote_aktiv" not in unt55:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN angebote_aktiv BOOLEAN NOT NULL DEFAULT 0"))
            for col, ddl in [
                ("angebot_status",        "VARCHAR(20) DEFAULT 'offen'"),
                ("gueltig_bis",           "DATE"),
                ("dokumentenpaket_id",    "INTEGER REFERENCES dokumentenpakete(id)"),
                ("rechnung_zu_angebot_id","INTEGER REFERENCES rechnungen(id)"),
            ]:
                if col not in re55:
                    conn.execute(text(f"ALTER TABLE rechnungen ADD COLUMN {col} {ddl}"))
            conn.execute(text("""
                INSERT OR IGNORE INTO nummernkreise (typ, bezeichnung, format, naechste_nr, reset_jaehrlich, letztes_jahr)
                VALUES ('angebot', 'Angebote', 'ANG-JJNNNN', 1, 1, NULL)
            """))
            conn.execute(text("PRAGMA user_version = 55"))
            conn.commit()
            print("[Migration] Schema auf Version 55 (Angebote: angebote_aktiv + angebot_status + gueltig_bis + dokumentenpaket_id + Nummernkreis)")

        if version < 54:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS dokumentenpakete (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(200) NOT NULL,
                    beschreibung TEXT,
                    aktiv BOOLEAN NOT NULL DEFAULT 1,
                    erstellt_am DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS dokumentenpaket_belege (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paket_id INTEGER NOT NULL REFERENCES dokumentenpakete(id) ON DELETE CASCADE,
                    beleg_id INTEGER NOT NULL REFERENCES belege(id) ON DELETE CASCADE,
                    bezeichnung VARCHAR(200),
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(paket_id, beleg_id)
                )
            """))
            conn.execute(text("PRAGMA user_version = 54"))
            conn.commit()
            print("[Migration] Schema auf Version 54 (dokumentenpakete + dokumentenpaket_belege)")

        if version < 56:
            rechnungen_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "lieferschein_zu_angebot_id" not in rechnungen_cols:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN lieferschein_zu_angebot_id INTEGER REFERENCES rechnungen(id)"))
                rechnungen_cols.add("lieferschein_zu_angebot_id")
            # Bestehende Links aus Notizen "Zu Angebot XXX" rekonstruieren (nur wenn notizen-Spalte existiert)
            ls_rows = []
            if "notizen" in rechnungen_cols and "dokument_typ" in rechnungen_cols:
                ls_rows = conn.execute(text(
                    "SELECT id, notizen FROM rechnungen WHERE dokument_typ='Lieferschein' AND notizen LIKE 'Zu Angebot %'"
                )).fetchall()
            for ls_id, notiz in ls_rows:
                ang_nr = notiz.replace("Zu Angebot ", "").strip()
                ang = conn.execute(text(
                    "SELECT id FROM rechnungen WHERE rechnungsnummer=:nr AND dokument_typ='Angebot'"
                ), {"nr": ang_nr}).fetchone()
                if ang:
                    conn.execute(text(
                        "UPDATE rechnungen SET lieferschein_zu_angebot_id=:ls_id WHERE id=:ang_id"
                    ), {"ls_id": ls_id, "ang_id": ang[0]})
            conn.execute(text("PRAGMA user_version = 56"))
            conn.commit()
            print("[Migration] Schema auf Version 56 (rechnungen.lieferschein_zu_angebot_id: Rückverlinkung Angebot→Lieferschein)")

        if version < 57:
            unt57 = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "leistungsbescheid_monat" not in unt57:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN leistungsbescheid_monat VARCHAR(7)"))
            conn.execute(text("PRAGMA user_version = 57"))
            conn.commit()
            print("[Migration] Schema auf Version 57 (unternehmen.leistungsbescheid_monat: Beginn Abrechnungszeitraum Jobcenter)")

        if version < 58:
            # EÜR-Zeilennummern auf Anlage EÜR 2025 (Issue #132):
            # Vereinnahmte USt: 15 → 17, FA-erstattete USt: 16 → 18
            # Abziehbare Vorsteuer: 48 → 57 (hardcoded in euer.py)
            # Gewährte Skonti: 15 → 12 (Erlösminderung, nicht Vereinnahmte USt)
            # Reparatur Anlagevermögen + Bauleistungen §13b: 48 → 60 (Sonstige BA, nicht Vorsteuer)
            conn.execute(text("UPDATE kategorien SET euer_zeile = 17 WHERE euer_zeile = 15 AND name != 'Gewährte Skonti'"))
            conn.execute(text("UPDATE kategorien SET euer_zeile = 18 WHERE euer_zeile = 16"))
            conn.execute(text("UPDATE kategorien SET euer_zeile = 12 WHERE name = 'Gewährte Skonti'"))
            conn.execute(text("UPDATE kategorien SET euer_zeile = 60 WHERE euer_zeile = 48"))
            conn.execute(text("PRAGMA user_version = 58"))
            conn.commit()
            print("[Migration] Schema auf Version 58 (EÜR-Zeilennummern Anlage EÜR 2025: 15→17, 16→18, 48→57/60, Skonti→12)")

        if version < 59:
            unt59 = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            re59  = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "proforma_aktiv" not in unt59:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN proforma_aktiv BOOLEAN NOT NULL DEFAULT 0"))
            if "proforma_zu_angebot_id" not in re59:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN proforma_zu_angebot_id INTEGER REFERENCES rechnungen(id)"))
            if "rechnung_zu_proforma_id" not in re59:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN rechnung_zu_proforma_id INTEGER REFERENCES rechnungen(id)"))
            conn.execute(text("""
                INSERT OR IGNORE INTO nummernkreise (typ, bezeichnung, format, naechste_nr, reset_jaehrlich, letztes_jahr)
                VALUES ('proforma', 'Proforma-Rechnungen', 'PRF-JJNNNN', 1, 1, NULL)
            """))
            conn.execute(text("PRAGMA user_version = 59"))
            conn.commit()
            print("[Migration] Schema auf Version 59 (Proforma-Rechnungen: proforma_aktiv + FK-Felder + Nummernkreis)")

        if version < 60:
            unt60 = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            re60  = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "auftraege_aktiv" not in unt60:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN auftraege_aktiv BOOLEAN NOT NULL DEFAULT 0"))
            if "auftrag_status" not in re60:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN auftrag_status VARCHAR(20)"))
            if "auftrag_zu_angebot_id" not in re60:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN auftrag_zu_angebot_id INTEGER REFERENCES rechnungen(id)"))
            if "rechnung_zu_auftrag_id" not in re60:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN rechnung_zu_auftrag_id INTEGER REFERENCES rechnungen(id)"))
            if "lieferschein_zu_auftrag_id" not in re60:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN lieferschein_zu_auftrag_id INTEGER REFERENCES rechnungen(id)"))
            if "proforma_zu_auftrag_id" not in re60:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN proforma_zu_auftrag_id INTEGER REFERENCES rechnungen(id)"))
            conn.execute(text("""
                INSERT OR IGNORE INTO nummernkreise (typ, bezeichnung, format, naechste_nr, reset_jaehrlich, letztes_jahr)
                VALUES ('auftrag', 'Aufträge', 'AU-JJNNNN', 1, 1, NULL)
            """))
            conn.execute(text("PRAGMA user_version = 60"))
            conn.commit()
            print("[Migration] Schema auf Version 60 (Aufträge: auftraege_aktiv + FK-Felder + Nummernkreis AU-JJNNNN)")

        if version < 61:
            # Auftrag-Statuskorrektur: in_bearbeitung → abgeschlossen wenn verknüpfte Rechnung bezahlt
            # Pfad 1: Rechnung direkt aus Auftrag (rechnung_zu_auftrag_id)
            # Pfad 2: Proforma aus Auftrag → Rechnung aus Proforma (proforma_zu_auftrag_id + rechnung_zu_proforma_id)
            conn.execute(text("""
                UPDATE rechnungen SET auftrag_status = 'abgeschlossen'
                WHERE dokument_typ = 'Auftrag'
                AND auftrag_status = 'in_bearbeitung'
                AND (
                    EXISTS (
                        SELECT 1 FROM rechnungen r
                        WHERE r.id = rechnungen.rechnung_zu_auftrag_id
                        AND r.zahlungsstatus = 'bezahlt'
                    )
                    OR EXISTS (
                        SELECT 1 FROM rechnungen p
                        WHERE p.id = rechnungen.proforma_zu_auftrag_id
                        AND EXISTS (
                            SELECT 1 FROM rechnungen r2
                            WHERE r2.id = p.rechnung_zu_proforma_id
                            AND r2.zahlungsstatus = 'bezahlt'
                        )
                    )
                )
            """))
            conn.execute(text("PRAGMA user_version = 61"))
            conn.commit()
            print("[Migration] Schema auf Version 61 (Auftrag-Status: in_bearbeitung → abgeschlossen bei bezahlter Rechnung)")

        if version < 62:
            # Pfad 3 nachkorrigieren: Auftrag → Lieferschein → Rechnung bezahlt
            conn.execute(text("""
                UPDATE rechnungen SET auftrag_status = 'abgeschlossen'
                WHERE dokument_typ = 'Auftrag'
                AND auftrag_status = 'in_bearbeitung'
                AND EXISTS (
                    SELECT 1 FROM rechnungen ls
                    WHERE ls.id = rechnungen.lieferschein_zu_auftrag_id
                    AND EXISTS (
                        SELECT 1 FROM rechnungen r
                        WHERE r.id = ls.lieferschein_zu_rechnung_id
                        AND r.zahlungsstatus = 'bezahlt'
                    )
                )
            """))
            conn.execute(text("PRAGMA user_version = 62"))
            conn.commit()
            print("[Migration] Schema auf Version 62 (Auftrag-Status: Lieferschein-Pfad nachkorrigiert)")

        if version < 63:
            # Verwaiste Auftrag-FKs bereinigen: verlinktes Dokument existiert nicht mehr
            conn.execute(text("""
                UPDATE rechnungen SET proforma_zu_auftrag_id = NULL
                WHERE dokument_typ = 'Auftrag'
                AND proforma_zu_auftrag_id IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM rechnungen p WHERE p.id = rechnungen.proforma_zu_auftrag_id)
            """))
            conn.execute(text("""
                UPDATE rechnungen SET rechnung_zu_auftrag_id = NULL
                WHERE dokument_typ = 'Auftrag'
                AND rechnung_zu_auftrag_id IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM rechnungen r WHERE r.id = rechnungen.rechnung_zu_auftrag_id)
            """))
            conn.execute(text("""
                UPDATE rechnungen SET lieferschein_zu_auftrag_id = NULL
                WHERE dokument_typ = 'Auftrag'
                AND lieferschein_zu_auftrag_id IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM rechnungen ls WHERE ls.id = rechnungen.lieferschein_zu_auftrag_id)
            """))
            # Status auf offen zurücksetzen wenn keine Dokumente mehr verlinkt
            conn.execute(text("""
                UPDATE rechnungen SET auftrag_status = 'offen'
                WHERE dokument_typ = 'Auftrag'
                AND auftrag_status = 'in_bearbeitung'
                AND rechnung_zu_auftrag_id IS NULL
                AND lieferschein_zu_auftrag_id IS NULL
                AND proforma_zu_auftrag_id IS NULL
            """))
            conn.execute(text("PRAGMA user_version = 63"))
            conn.commit()
            print("[Migration] Schema auf Version 63 (Auftrag: verwaiste FKs bereinigt, Status zurückgesetzt)")

        if version < 64:
            # Verwaiste auftrag_zu_angebot_id auf Angeboten bereinigen
            conn.execute(text("""
                UPDATE rechnungen SET auftrag_zu_angebot_id = NULL
                WHERE dokument_typ = 'Angebot'
                AND auftrag_zu_angebot_id IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM rechnungen a WHERE a.id = rechnungen.auftrag_zu_angebot_id)
            """))
            conn.execute(text("PRAGMA user_version = 64"))
            conn.commit()
            print("[Migration] Schema auf Version 64 (Angebot: verwaiste auftrag_zu_angebot_id bereinigt)")

        if version < 65:
            # Neuer Status rechnung_gestellt: Aufträge mit finalisierter, noch offener Rechnung
            conn.execute(text("""
                UPDATE rechnungen SET auftrag_status = 'rechnung_gestellt'
                WHERE dokument_typ = 'Auftrag'
                AND auftrag_status = 'in_bearbeitung'
                AND rechnung_zu_auftrag_id IS NOT NULL
                AND EXISTS (
                    SELECT 1 FROM rechnungen r
                    WHERE r.id = rechnungen.rechnung_zu_auftrag_id
                    AND r.ist_entwurf = 0
                    AND r.zahlungsstatus != 'bezahlt'
                    AND (r.storniert IS NULL OR r.storniert = 0)
                )
            """))
            conn.execute(text("PRAGMA user_version = 65"))
            conn.commit()
            print("[Migration] Schema auf Version 65 (Auftrag: neuer Status rechnung_gestellt)")

        if version < 66:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            new_cols = {
                "smtp_aktiv":        "BOOLEAN NOT NULL DEFAULT 0",
                "smtp_host":         "VARCHAR(200)",
                "smtp_port":         "INTEGER NOT NULL DEFAULT 587",
                "smtp_ssl":          "BOOLEAN NOT NULL DEFAULT 0",
                "smtp_user":         "VARCHAR(200)",
                "smtp_passwort":     "VARCHAR(500)",
                "smtp_von_adresse":  "VARCHAR(200)",
                "mail_betreff_angebot":  "VARCHAR(500)",
                "mail_text_angebot":     "TEXT",
                "mail_betreff_proforma": "VARCHAR(500)",
                "mail_text_proforma":    "TEXT",
                "mail_betreff_auftrag":  "VARCHAR(500)",
                "mail_text_auftrag":     "TEXT",
            }
            for col, typ in new_cols.items():
                if col not in cols:
                    conn.execute(text(f"ALTER TABLE unternehmen ADD COLUMN {col} {typ}"))
            conn.execute(text("PRAGMA user_version = 66"))
            conn.commit()
            print("[Migration] Schema auf Version 66 (SMTP + Mail-Templates pro Dokumenttyp)")

        if version < 67:
            # Datenfix Issue #132: 'Betriebseinnahmen (7%)' fehlte in Migration 26 →
            # euer_zeile war NULL → 7%-Umsätze aus Rechnungs-Zahlungen wurden nicht in EÜR gezeigt.
            conn.execute(text(
                "UPDATE kategorien SET euer_zeile = 12 WHERE name = 'Betriebseinnahmen (7%)' AND euer_zeile IS NOT 12"
            ))
            conn.execute(text("PRAGMA user_version = 67"))
            conn.commit()
            print("[Migration] Schema auf Version 67 (Datenfix: Betriebseinnahmen (7%) euer_zeile=12)")

        if version < 68:
            cols68 = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "wiederkehrend_aktiv" not in cols68:
                conn.execute(text(
                    "ALTER TABLE unternehmen ADD COLUMN wiederkehrend_aktiv BOOLEAN NOT NULL DEFAULT 0"
                ))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS rechnungsvorlagen (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bezeichnung VARCHAR(200) NOT NULL,
                    intervall VARCHAR(20) NOT NULL,
                    naechstes_datum DATE NOT NULL,
                    aktiv BOOLEAN NOT NULL DEFAULT 1,
                    kunde_id INTEGER REFERENCES kunden(id) ON DELETE SET NULL,
                    zahlungsziel_tage INTEGER,
                    notizen TEXT,
                    positionen_json TEXT NOT NULL DEFAULT '[]',
                    letzte_erstellung DATE,
                    erstellte_rechnungen INTEGER NOT NULL DEFAULT 0,
                    erstellt_am DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("PRAGMA user_version = 68"))
            conn.commit()
            print("[Migration] Schema auf Version 68 (wiederkehrende Rechnungen: wiederkehrend_aktiv + rechnungsvorlagen)")

        if version < 69:
            # Datenfix Issue #132: Kategorie "Betriebseinnahmen (19%)" → "Betriebseinnahmen"
            # In älteren Installationen hieß die Kategorie noch mit (19%)-Suffix.
            # _erloes_kategorie() suchte nach "Betriebseinnahmen" → fand nichts → kategorie_id=NULL
            # → Einnahmen fehlten komplett in EÜR Zeile 12.
            conn.execute(text(
                "UPDATE kategorien SET name='Betriebseinnahmen', euer_zeile=12 "
                "WHERE name='Betriebseinnahmen (19%)'"
            ))
            # Sicherheitsnetz: euer_zeile=12 für alle Betriebseinnahmen-Varianten erzwingen
            conn.execute(text(
                "UPDATE kategorien SET euer_zeile=12 "
                "WHERE name IN ('Betriebseinnahmen', 'Betriebseinnahmen (0%)') "
                "AND (euer_zeile IS NULL OR euer_zeile != 12)"
            ))
            conn.execute(text("PRAGMA user_version = 69"))
            conn.commit()
            print("[Migration] Schema auf Version 69 (Datenfix #132: 'Betriebseinnahmen (19%)' → 'Betriebseinnahmen', euer_zeile=12 gesichert)")

        if version < 70:
            cols70 = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungsvorlagen)")).fetchall()}
            if "auftrag_id" not in cols70:
                conn.execute(text(
                    "ALTER TABLE rechnungsvorlagen ADD COLUMN auftrag_id INTEGER REFERENCES rechnungen(id) ON DELETE SET NULL"
                ))
            if "beleg_id" not in cols70:
                conn.execute(text(
                    "ALTER TABLE rechnungsvorlagen ADD COLUMN beleg_id INTEGER REFERENCES belege(id) ON DELETE SET NULL"
                ))
            conn.execute(text("PRAGMA user_version = 70"))
            conn.commit()
            print("[Migration] Schema auf Version 70 (rechnungsvorlagen: auftrag_id + beleg_id für Auftrag-Verknüpfung und Vertrags-Upload)")

        if version < 71:
            cols71 = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "vorlage_id" not in cols71:
                conn.execute(text(
                    "ALTER TABLE rechnungen ADD COLUMN vorlage_id INTEGER REFERENCES rechnungsvorlagen(id) ON DELETE SET NULL"
                ))
            conn.execute(text("PRAGMA user_version = 71"))
            conn.commit()
            print("[Migration] Schema auf Version 71 (rechnungen.vorlage_id: Verknüpfung zu wiederkehrender Vorlage)")

        if version < 72:
            cols72 = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungsvorlagen)")).fetchall()}
            if "beendet" not in cols72:
                conn.execute(text(
                    "ALTER TABLE rechnungsvorlagen ADD COLUMN beendet BOOLEAN NOT NULL DEFAULT 0"
                ))
            conn.execute(text("PRAGMA user_version = 72"))
            conn.commit()
            print("[Migration] Schema auf Version 72 (rechnungsvorlagen.beendet: Vorlage dauerhaft beenden)")

        if version < 73:
            # EÜR-Doppelabzug bei Skonti: Zahlung enthält per Zuflussprinzip bereits den
            # korrekten Betrag (z.B. 98 € bei 2 % Skonto auf 100 €). Ein zusätzlicher
            # Skonto-Eintrag mit euer_zeile=12/27 subtrahiert nochmals → 96 € statt 98 €.
            # Lösung: Skonto-Kategorien brauchen keine eigene EÜR-Zeile.
            # Zeile 17 (vereinnahmte USt) wird über konto_ust_skr03/04 korrekt berechnet.
            conn.execute(text("UPDATE kategorien SET euer_zeile = NULL WHERE name = 'Gewährte Skonti'"))
            conn.execute(text("UPDATE kategorien SET euer_zeile = NULL WHERE name = 'Erhaltene Skonti'"))
            conn.execute(text("PRAGMA user_version = 73"))
            conn.commit()
            print("[Migration] Schema auf Version 73 (Skonto-Kategorien: euer_zeile→NULL, kein Doppelabzug in EÜR)")

        if version < 74:
            # Wiederkehrende Buchungen: Vorlagen für Fixkosten (Miete, Leasing, Abo)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS buchungsvorlagen (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bezeichnung VARCHAR(200) NOT NULL,
                    lieferant_id INTEGER REFERENCES lieferanten(id) ON DELETE SET NULL,
                    kategorie_id INTEGER REFERENCES kategorien(id) ON DELETE SET NULL,
                    konto_id INTEGER REFERENCES konten(id) ON DELETE SET NULL,
                    betrag NUMERIC(12,2) NOT NULL,
                    ist_brutto BOOLEAN NOT NULL DEFAULT 1,
                    ust_satz NUMERIC(5,2) NOT NULL DEFAULT 0,
                    intervall VARCHAR(20) NOT NULL DEFAULT 'monatlich',
                    naechstes_datum DATE NOT NULL,
                    aktiv BOOLEAN NOT NULL DEFAULT 1,
                    modus VARCHAR(20) NOT NULL DEFAULT 'direkt',
                    notizen TEXT,
                    beleg_id INTEGER REFERENCES belege(id) ON DELETE SET NULL,
                    letzte_buchung DATE,
                    erstellte_buchungen INTEGER NOT NULL DEFAULT 0,
                    erstellt_am DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            cols74_j = {r[1] for r in conn.execute(text("PRAGMA table_info(journal)")).fetchall()}
            if "buchungsvorlage_id" not in cols74_j:
                conn.execute(text("ALTER TABLE journal ADD COLUMN buchungsvorlage_id INTEGER REFERENCES buchungsvorlagen(id) ON DELETE SET NULL"))
            cols74_r = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "buchungsvorlage_id" not in cols74_r:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN buchungsvorlage_id INTEGER REFERENCES buchungsvorlagen(id) ON DELETE SET NULL"))
            cols74_u = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "buchungsvorlagen_aktiv" not in cols74_u:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN buchungsvorlagen_aktiv BOOLEAN NOT NULL DEFAULT 0"))
            conn.execute(text("PRAGMA user_version = 74"))
            conn.commit()
            print("[Migration] Schema auf Version 74 (buchungsvorlagen: Wiederkehrende Buchungen für Fixkosten)")

        if version < 75:
            # Datenfix Issue #132: 'Betriebseinnahmen (19%)' und 'Betriebseinnahmen (7%)' bekamen
            # in manchen älteren DBs euer_zeile=NULL. Migration 69 hatte nur 'Betriebseinnahmen'
            # und 'Betriebseinnahmen (0%)' gesichert; wenn die Umbenennung (19%)→Basis nicht
            # griff (Kategorie existierte bereits mit anderem Namen), blieb euer_zeile NULL →
            # Rechnungseinnahmen fehlten in der EÜR trotz korrekter UStVA.
            conn.execute(text(
                "UPDATE kategorien SET euer_zeile=12 "
                "WHERE name IN ('Betriebseinnahmen (19%)', 'Betriebseinnahmen (7%)') "
                "AND (euer_zeile IS NULL OR euer_zeile != 12)"
            ))
            conn.execute(text("PRAGMA user_version = 75"))
            conn.commit()
            print("[Migration] Schema auf Version 75 (Datenfix #132: Betriebseinnahmen-Varianten euer_zeile=12)")

        if version < 76:
            cols76 = {c[1] for c in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            for col, typ in [
                ("backup_extern_pfad_1",  "TEXT"),
                ("backup_extern_pfad_2",  "TEXT"),
                ("backup_extern_passwort", "TEXT"),
            ]:
                if col not in cols76:
                    conn.execute(text(f"ALTER TABLE unternehmen ADD COLUMN {col} {typ}"))
            conn.execute(text("PRAGMA user_version = 76"))
            conn.commit()
            print("[Migration] Schema auf Version 76 (Backup: externe Pfade + AES-Passwort)")

        if version < 77:
            cols77 = {c[1] for c in conn.execute(text("PRAGMA table_info(buchungsvorlagen)")).fetchall()}
            if "art" not in cols77:
                conn.execute(text("ALTER TABLE buchungsvorlagen ADD COLUMN art TEXT NOT NULL DEFAULT 'Ausgabe'"))
            conn.execute(text("PRAGMA user_version = 77"))
            conn.commit()
            print("[Migration] Schema auf Version 77 (buchungsvorlagen.art: Einnahme/Ausgabe)")

        if version < 78:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS anlageverzeichnis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bezeichnung TEXT NOT NULL,
                    typ TEXT NOT NULL DEFAULT 'sonstig',
                    kaufdatum DATE NOT NULL,
                    kaufpreis_netto NUMERIC(12,2) NOT NULL,
                    nutzungsdauer_jahre INTEGER NOT NULL,
                    afa_methode TEXT NOT NULL DEFAULT 'linear',
                    kennzeichen TEXT,
                    privat_anteil_prozent NUMERIC(5,2) NOT NULL DEFAULT 0,
                    verkauft_am DATE,
                    notizen TEXT,
                    aktiv BOOLEAN NOT NULL DEFAULT 1,
                    erstellt_am DATETIME DEFAULT CURRENT_TIMESTAMP,
                    aktualisiert_am DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("PRAGMA user_version = 78"))
            conn.commit()
            print("[Migration] Schema auf Version 78 (anlageverzeichnis: Anlage AVEÜR)")

        if version < 79:
            cols79 = {c[1] for c in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            for col, typ in [
                ("datev_beraternummer",  "TEXT"),
                ("datev_mandantennummer", "TEXT"),
                ("datev_konto_bar",      "TEXT"),
                ("datev_konto_bank",     "TEXT"),
                ("datev_konto_karte",    "TEXT"),
                ("datev_konto_paypal",   "TEXT"),
            ]:
                if col not in cols79:
                    conn.execute(text(f"ALTER TABLE unternehmen ADD COLUMN {col} {typ}"))
            conn.execute(text("PRAGMA user_version = 79"))
            conn.commit()
            print("[Migration] Schema auf Version 79 (DATEV-Konfiguration in unternehmen)")

        if version < 80:
            cols_pos = {c[1] for c in conn.execute(text("PRAGMA table_info(rechnungspositionen)")).fetchall()}
            if "rabatt_prozent" not in cols_pos:
                conn.execute(text("ALTER TABLE rechnungspositionen ADD COLUMN rabatt_prozent NUMERIC(5,2) NOT NULL DEFAULT 0"))
            cols_re = {c[1] for c in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "rabatt_prozent" not in cols_re:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN rabatt_prozent NUMERIC(5,2) NOT NULL DEFAULT 0"))
            conn.execute(text("PRAGMA user_version = 80"))
            conn.commit()
            print("[Migration] Schema auf Version 80 (Rabatt auf Positionen und Rechnung)")

        if version < 81:
            cols_unt = {c[1] for c in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "einleitungstext" not in cols_unt:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN einleitungstext TEXT"))
            cols_re = {c[1] for c in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "einleitungstext" not in cols_re:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN einleitungstext TEXT"))
            conn.execute(text("PRAGMA user_version = 81"))
            conn.commit()
            print("[Migration] Schema auf Version 81 (Einleitungstext auf Rechnung)")

        if version < 82:
            # GWG-Kontonummern korrigieren: SKR03 4855→0480, SKR04 6845→0670
            # Quelle: DATEV Kontenrahmen SKR03/04 (offiziell, bestätigt Issue #165)
            conn.execute(text("""
                UPDATE kategorien
                SET konto_skr03_default = '0480',
                    konto_skr03 = CASE WHEN user_modified_skr03 = 0 THEN '0480' ELSE konto_skr03 END
                WHERE name = 'Geringwertige Wirtschaftsgüter (GWG)'
            """))
            conn.execute(text("""
                UPDATE kategorien
                SET konto_skr04_default = '0670',
                    konto_skr04 = CASE WHEN user_modified_skr04 = 0 THEN '0670' ELSE konto_skr04 END
                WHERE name = 'Geringwertige Wirtschaftsgüter (GWG)'
            """))
            conn.execute(text("PRAGMA user_version = 82"))
            conn.commit()
            print("[Migration] Schema auf Version 82 (GWG-Konten korrigiert: SKR03 0480, SKR04 0670)")

        if version < 83:
            cols_re = {c[1] for c in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "original_pdf_pfad" not in cols_re:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN original_pdf_pfad VARCHAR(500)"))
            conn.execute(text("PRAGMA user_version = 83"))
            conn.commit()
            print("[Migration] Schema auf Version 83 (rechnungen.original_pdf_pfad für Original-PDF-Archivierung)")

        if version < 84:
            cols_re = {c[1] for c in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "ausgegeben_am" not in cols_re:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN ausgegeben_am DATETIME"))
            conn.execute(text("PRAGMA user_version = 84"))
            conn.commit()
            print("[Migration] Schema auf Version 84 (rechnungen.ausgegeben_am – Zeitstempel erstes Drucken/Mailen)")

        if version < 85:
            cols_re = {c[1] for c in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "rabatt_betrag" not in cols_re:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN rabatt_betrag NUMERIC(12,2)"))
            conn.execute(text("PRAGMA user_version = 85"))
            conn.commit()
            print("[Migration] Schema auf Version 85 (rechnungen.rabatt_betrag – Festbetrag-Rabatt als Alternative zu rabatt_prozent)")

        if version < 86:
            cols_unt = {c[1] for c in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "lagerführung_aktiv" not in cols_unt:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN lagerführung_aktiv BOOLEAN DEFAULT 0"))
            cols_art = {c[1] for c in conn.execute(text("PRAGMA table_info(artikel)")).fetchall()}
            for col, typ in [
                ("lager_aktiv",          "BOOLEAN DEFAULT 0"),
                ("bestand_aktuell",      "NUMERIC(10,3) DEFAULT 0"),
                ("mindestbestand",       "NUMERIC(10,3) DEFAULT 0"),
                ("minusbestand_erlaubt", "BOOLEAN DEFAULT 0"),
            ]:
                if col not in cols_art:
                    conn.execute(text(f"ALTER TABLE artikel ADD COLUMN {col} {typ}"))
            conn.execute(text("PRAGMA user_version = 86"))
            conn.commit()
            print("[Migration] Schema auf Version 86 (Lagerführung-Light: unternehmen.lagerführung_aktiv, artikel: lager_aktiv/bestand_aktuell/mindestbestand/minusbestand_erlaubt)")

        if version < 87:
            # Datenfix: minusbestand_erlaubt war fälschlich DEFAULT 1 – auf 0 korrigieren
            conn.execute(text("UPDATE artikel SET minusbestand_erlaubt = 0 WHERE minusbestand_erlaubt = 1"))
            conn.execute(text("PRAGMA user_version = 87"))
            conn.commit()
            print("[Migration] Schema auf Version 87 (Datenfix: minusbestand_erlaubt DEFAULT 0)")

        if version < 88:
            cols88 = {c[1] for c in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            for col in ("backup_smb_benutzer", "backup_smb_passwort"):
                if col not in cols88:
                    conn.execute(text(f"ALTER TABLE unternehmen ADD COLUMN {col} TEXT"))
            conn.execute(text("PRAGMA user_version = 88"))
            conn.commit()
            print("[Migration] Schema auf Version 88 (Backup: SMB-Zugangsdaten)")

        if version < 89:
            cols89 = {c[1] for c in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "storno_datum" not in cols89:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN storno_datum DATE"))
            conn.execute(text("PRAGMA user_version = 89"))
            conn.commit()
            print("[Migration] Schema auf Version 89 (rechnungen.storno_datum)")

        if version < 90:
            cols90 = {c[1] for c in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "storno_rechnungsnummer" not in cols90:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN storno_rechnungsnummer VARCHAR(50)"))
            conn.execute(text("""
                INSERT OR IGNORE INTO nummernkreise (typ, bezeichnung, format, naechste_nr, reset_jaehrlich, letztes_jahr)
                VALUES ('stornorechnung', 'Stornorechnungen', 'STORNO-JJNNNN', 1, 1, NULL)
            """))
            conn.execute(text("PRAGMA user_version = 90"))
            conn.commit()
            print("[Migration] Schema auf Version 90 (storno_rechnungsnummer + Nummernkreis Stornorechnungen)")

        if version < 91:
            # Gutschrift-Nummernkreis: naechste_nr aus vorhandenen Gutschriften ableiten
            existing_gs = conn.execute(text(
                "SELECT COUNT(*) FROM rechnungen WHERE dokument_typ='Gutschrift'"
            )).scalar() or 0
            conn.execute(text("""
                INSERT OR IGNORE INTO nummernkreise (typ, bezeichnung, format, naechste_nr, reset_jaehrlich, letztes_jahr)
                VALUES ('gutschrift', 'Gutschriften', 'GS-YY####', :nr, 1, NULL)
            """), {"nr": existing_gs + 1})
            conn.execute(text("PRAGMA user_version = 91"))
            conn.commit()
            print("[Migration] Schema auf Version 91 (Nummernkreis Gutschriften)")

        if version < 92:
            cols92 = {c[1] for c in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "absender_snapshot" not in cols92:
                conn.execute(text("ALTER TABLE rechnungen ADD COLUMN absender_snapshot TEXT"))
            conn.execute(text("PRAGMA user_version = 92"))
            conn.commit()
            print("[Migration] Schema auf Version 92 (rechnungen.absender_snapshot – GoBD-Snapshot Absenderdaten)")

        if version < 93:
            import json as _json
            unt93 = conn.execute(text("SELECT * FROM unternehmen WHERE id=1")).mappings().first()
            if unt93:
                snap93 = _json.dumps({
                    "firmenname":              unt93.get("firmenname") or "",
                    "vorname":                 unt93.get("vorname") or "",
                    "nachname":                unt93.get("nachname") or "",
                    "strasse":                 unt93.get("strasse") or "",
                    "hausnummer":              unt93.get("hausnummer") or "",
                    "plz":                     unt93.get("plz") or "",
                    "ort":                     unt93.get("ort") or "",
                    "land":                    unt93.get("land") or "DE",
                    "steuernummer":            unt93.get("steuernummer") or "",
                    "ust_idnr":                unt93.get("ust_idnr") or "",
                    "finanzamt":               unt93.get("finanzamt") or "",
                    "handelsregister_nr":      unt93.get("handelsregister_nr") or "",
                    "handelsregister_gericht": unt93.get("handelsregister_gericht") or "",
                    "telefon":                 unt93.get("telefon") or "",
                    "email":                   unt93.get("email") or "",
                    "webseite":                unt93.get("webseite") or "",
                    "iban":                    unt93.get("iban") or "",
                    "bic":                     unt93.get("bic") or "",
                    "bank_name":               unt93.get("bank_name") or "",
                    "logo_pfad":               unt93.get("logo_pfad") or "",
                    "berufsbezeichnung":       unt93.get("berufsbezeichnung") or "",
                    "kammer_mitgliedschaft":   unt93.get("kammer_mitgliedschaft") or "",
                    "ist_kleinunternehmer":    bool(unt93.get("ist_kleinunternehmer")),
                    "zahlungshinweis_aktiv":   bool(unt93.get("zahlungshinweis_aktiv", True)),
                    "pdf_vorlage":             int(unt93.get("pdf_vorlage") or 0),
                    "unterschrift_bild":       unt93.get("unterschrift_bild") or "",
                    "unterschrift_auf_rechnung": bool(unt93.get("unterschrift_auf_rechnung")),
                    "qr_zahlung_aktiv":        bool(unt93.get("qr_zahlung_aktiv")),
                    "einleitungstext":         unt93.get("einleitungstext") or "",
                }, ensure_ascii=False)
                result = conn.execute(text(
                    "UPDATE rechnungen SET absender_snapshot = :snap "
                    "WHERE ist_entwurf = 0 AND (absender_snapshot IS NULL OR absender_snapshot = '')"
                ), {"snap": snap93})
                print(f"[Migration] {result.rowcount} finalisierte Dokumente mit Absender-Snapshot befüllt")
            conn.execute(text("PRAGMA user_version = 93"))
            conn.commit()
            print("[Migration] Schema auf Version 93 (rechnungen.absender_snapshot Backfill für Bestandsdokumente)")

        if version < 94:
            cols94 = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "bezeichnung_des_gewerbes" not in cols94:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN bezeichnung_des_gewerbes VARCHAR(200)"))
            conn.execute(text("PRAGMA user_version = 94"))
            conn.commit()
            print("[Migration] Schema auf Version 94 (unternehmen.bezeichnung_des_gewerbes – genaue Bezeichnung des Gewerbes für Anlage G Z.4)")

        if version < 95:
            # EÜR-Zeilenzuordnung korrigieren (Issue #185, Anlage EÜR 2025 BMF):
            # Zeile 12  = Kleinunternehmer §19 Abs. 1 UStG
            # Zeile 15  = Umsatzsteuerpflichtige BE (19% und 7% gemeinsam)
            # Zeile 16  = Steuerfreie / nicht steuerbare BE (§4 UStG)
            # 19%-Einnahmen lagen fälschlich in Zeile 12 (Kleinunternehmer-Zeile)
            conn.execute(text(
                "UPDATE kategorien SET euer_zeile=15 "
                "WHERE name IN ('Betriebseinnahmen', 'Betriebseinnahmen (19%)') "
                "AND (euer_zeile IS NULL OR euer_zeile != 15)"
            ))
            conn.execute(text(
                "UPDATE kategorien SET euer_zeile=15 "
                "WHERE name='Betriebseinnahmen (7%)' "
                "AND (euer_zeile IS NULL OR euer_zeile != 15)"
            ))
            # 0%-Einnahmen = Kleinunternehmer → Zeile 12
            conn.execute(text(
                "UPDATE kategorien SET euer_zeile=12 "
                "WHERE name='Betriebseinnahmen (0%)' "
                "AND (euer_zeile IS NULL OR euer_zeile != 12)"
            ))
            conn.execute(text("PRAGMA user_version = 95"))
            conn.commit()
            print("[Migration] Schema auf Version 95 (EÜR: BE 19%/7% → Zeile 15, BE 0% → Zeile 12 Kleinunternehmer)")

        if version < 96:
            # SKR03-Kontonummer Gewerbesteuer korrigieren: 7600 → 4320
            # Im SKR03 gibt es kein Konto 7600; Gewerbesteuer = 4320 (Issue #186)
            # SKR04 7610 war bereits korrekt (SKR04 7600 = Körperschaftsteuer)
            conn.execute(text(
                "UPDATE kategorien SET konto_skr03='4320' "
                "WHERE name='Gewerbesteuer' AND (konto_skr03 IS NULL OR konto_skr03 != '4320')"
            ))
            conn.execute(text("PRAGMA user_version = 96"))
            conn.commit()
            print("[Migration] Schema auf Version 96 (Gewerbesteuer SKR03: 7600 → 4320)")

        if version < 97:
            # SKR-Kontonummern Spenden (betrieblich) korrigieren (Issue #186)
            # SKR03 4730 = Ausgangsfrachten → korrekt: 1840 (Zuwendungen, Spenden, Einzelunternehmen)
            # SKR04 6580 = Mautgebühren    → korrekt: 2250 (Zuwendungen, Spenden, Einzelunternehmen)
            conn.execute(text(
                "UPDATE kategorien SET konto_skr03='1840', konto_skr04='2250' "
                "WHERE name='Spenden (betrieblich)' "
                "AND (konto_skr03='4730' OR konto_skr04='6580')"
            ))
            conn.execute(text("PRAGMA user_version = 97"))
            conn.commit()
            print("[Migration] Schema auf Version 97 (Spenden SKR03: 4730→1840, SKR04: 6580→2250)")

        if version < 98:
            # Adressfelder für Einmalkunden (ohne Stammdatensatz) in rechnungen (Issue #188)
            for col, typ in [
                ("partner_strasse",    "VARCHAR(200)"),
                ("partner_hausnummer", "VARCHAR(20)"),
                ("partner_plz",        "VARCHAR(20)"),
                ("partner_ort",        "VARCHAR(200)"),
                ("partner_land",       "VARCHAR(2)"),
            ]:
                try:
                    conn.execute(text(f"ALTER TABLE rechnungen ADD COLUMN {col} {typ}"))
                except Exception:
                    pass
            conn.execute(text("PRAGMA user_version = 98"))
            conn.commit()
            print("[Migration] Schema auf Version 98 (Einmalkunden-Adressfelder: partner_strasse/hausnummer/plz/ort/land)")

        if version < 99:
            # Dokumente im Kundenstamm (Verträge, Bescheinigungen etc.)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS kunden_belege (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kunde_id INTEGER NOT NULL REFERENCES kunden(id) ON DELETE CASCADE,
                    beleg_id INTEGER NOT NULL REFERENCES belege(id) ON DELETE CASCADE,
                    bezeichnung VARCHAR(200),
                    erstellt_am DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
                )
            """))
            conn.execute(text("PRAGMA user_version = 99"))
            conn.commit()
            print("[Migration] Schema auf Version 99 (kunden_belege: Dokumente im Kundenstamm)")

        if version < 100:
            try:
                conn.execute(text("ALTER TABLE kunden_belege ADD COLUMN loeschdatum DATE"))
            except Exception:
                pass
            conn.execute(text("PRAGMA user_version = 100"))
            conn.commit()
            print("[Migration] Schema auf Version 100 (kunden_belege.loeschdatum: DSGVO-Löschdatum pro Dokument)")

        if version < 101:
            # Issue #195: Falsche SKR-Konten und fehlende EÜR-Zeilen bei Erlös-Kategorien
            # USt-Erstattung FA: 1779 = "USt aus ig. Erwerb ohne VoSt-Abzug" → korrekt: 1790/3841 (Umsatzsteuerverbindlichkeiten Vorjahr)
            conn.execute(text("""
                UPDATE kategorien SET
                    konto_skr03_default = '1790',
                    konto_skr03 = CASE WHEN user_modified_skr03 = 0 THEN '1790' ELSE konto_skr03 END,
                    konto_skr04_default = '3841',
                    konto_skr04 = CASE WHEN user_modified_skr04 = 0 THEN '3841' ELSE konto_skr04 END,
                    euer_zeile = 18
                WHERE name = 'Umsatzsteuer-Erstattung FA'
            """))
            # VoSt-Erstattung FA: 1570 = "Abziehbare Vorsteuer" (Asset-Konto, kein Erstattungskonto); 1570 existiert in SKR04 nicht
            conn.execute(text("""
                UPDATE kategorien SET
                    konto_skr03_default = '1790',
                    konto_skr03 = CASE WHEN user_modified_skr03 = 0 THEN '1790' ELSE konto_skr03 END,
                    konto_skr04_default = '3841',
                    konto_skr04 = CASE WHEN user_modified_skr04 = 0 THEN '3841' ELSE konto_skr04 END,
                    euer_zeile = 18
                WHERE name = 'Vorsteuererstattung FA'
            """))
            # Zuwendungen von Dritten: 8910 = "Entnahmen (Waren) 19%" und 4910 = "Erträge aus Zuschreibungen" → korrekt: 2747/4982 (Sonstige steuerfreie BE)
            conn.execute(text("""
                UPDATE kategorien SET
                    konto_skr03_default = '2747',
                    konto_skr03 = CASE WHEN user_modified_skr03 = 0 THEN '2747' ELSE konto_skr03 END,
                    konto_skr04_default = '4982',
                    konto_skr04 = CASE WHEN user_modified_skr04 = 0 THEN '4982' ELSE konto_skr04 END
                WHERE name = 'Zuwendungen von Dritten'
                  AND (konto_skr03 = '8910' OR konto_skr04 = '4910')
            """))
            # Eigenverbrauch (7%): 8911+4641 liegen im 19%-Kontenbereich (8910-8913 / 4640-4644) → korrekt: 8915/4610
            conn.execute(text("""
                UPDATE kategorien SET
                    konto_skr03_default = '8915',
                    konto_skr03 = CASE WHEN user_modified_skr03 = 0 THEN '8915' ELSE konto_skr03 END,
                    konto_skr04_default = '4610',
                    konto_skr04 = CASE WHEN user_modified_skr04 = 0 THEN '4610' ELSE konto_skr04 END,
                    euer_zeile = 21
                WHERE name = 'Eigenverbrauch von Waren (7%)'
            """))
            # Eigenverbrauch (19%): SKR-Konten korrekt, EÜR-Zeile 21 fehlte
            conn.execute(text(
                "UPDATE kategorien SET euer_zeile = 21 "
                "WHERE name = 'Eigenverbrauch von Waren (19%)' AND euer_zeile IS NULL"
            ))
            conn.execute(text("PRAGMA user_version = 101"))
            conn.commit()
            print("[Migration] Schema auf Version 101 (Issue #195: SKR-Konten Erlöse korrigiert, EÜR-Zeilen ergänzt)")

        if version < 102:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "bundesland" not in cols:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN bundesland VARCHAR(2)"))
            if "dauerfristverlaengerung_ust" not in cols:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN dauerfristverlaengerung_ust INTEGER NOT NULL DEFAULT 0"))
            if "est_vorauszahlungen_aktiv" not in cols:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN est_vorauszahlungen_aktiv INTEGER NOT NULL DEFAULT 0"))
            if "gewst_vorauszahlungen_aktiv" not in cols:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN gewst_vorauszahlungen_aktiv INTEGER NOT NULL DEFAULT 0"))
            conn.execute(text("PRAGMA user_version = 102"))
            conn.commit()
            print("[Migration] Schema auf Version 102 (unternehmen: bundesland, Steuer-Fristenliste-Felder)")

        if version < 103:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "guv_aktiv" not in cols:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN guv_aktiv INTEGER NOT NULL DEFAULT 0"))
            conn.execute(text("PRAGMA user_version = 103"))
            conn.commit()
            print("[Migration] Schema auf Version 103 (unternehmen: guv_aktiv – GuV / §141 AO Buchführungspflicht)")

        if version < 104:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS bank_imports (
                    id INTEGER PRIMARY KEY,
                    konto_id INTEGER NOT NULL REFERENCES konten(id),
                    template_id TEXT NOT NULL REFERENCES bank_templates(id),
                    dateiname VARCHAR(200) NOT NULL,
                    anzahl_zeilen INTEGER NOT NULL DEFAULT 0,
                    erfolg INTEGER NOT NULL DEFAULT 0,
                    fehler INTEGER NOT NULL DEFAULT 0,
                    duplikate INTEGER NOT NULL DEFAULT 0,
                    importiert_am DATETIME DEFAULT (datetime('now'))
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS bank_transaktionen (
                    id INTEGER PRIMARY KEY,
                    konto_id INTEGER NOT NULL REFERENCES konten(id),
                    import_id INTEGER NOT NULL REFERENCES bank_imports(id),
                    datum DATE NOT NULL,
                    valuta DATE,
                    buchungstext VARCHAR(500),
                    verwendungszweck TEXT,
                    partner_name VARCHAR(200),
                    partner_iban VARCHAR(34),
                    betrag NUMERIC(12,2) NOT NULL,
                    waehrung VARCHAR(3) NOT NULL DEFAULT 'EUR',
                    saldo NUMERIC(12,2),
                    ist_geschaeftlich BOOLEAN NOT NULL DEFAULT 1,
                    ist_privatentnahme BOOLEAN NOT NULL DEFAULT 0,
                    ist_einlage BOOLEAN NOT NULL DEFAULT 0,
                    ist_rueckerstattung BOOLEAN NOT NULL DEFAULT 0,
                    auto_vorschlag VARCHAR(20),
                    user_ueberschrieben BOOLEAN NOT NULL DEFAULT 0,
                    dedupe_hash VARCHAR(64),
                    kategorie_id INTEGER REFERENCES kategorien(id),
                    rechnung_id INTEGER REFERENCES rechnungen(id),
                    journal_id INTEGER REFERENCES journal(id) ON DELETE SET NULL,
                    erstellt_am DATETIME DEFAULT (datetime('now'))
                )
            """))
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(bank_transaktionen)")).fetchall()}
            if "dedupe_hash" not in cols:
                conn.execute(text("ALTER TABLE bank_transaktionen ADD COLUMN dedupe_hash TEXT"))
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uix_bank_tx_hash "
                "ON bank_transaktionen (konto_id, dedupe_hash) WHERE dedupe_hash IS NOT NULL"
            ))
            conn.execute(text("PRAGMA user_version = 104"))
            conn.commit()
            print("[Migration] Schema auf Version 104 (bank_transaktionen: dedupe_hash + UNIQUE Index)")

        if version < 105:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "bank_import_aktiv" not in cols:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN bank_import_aktiv INTEGER NOT NULL DEFAULT 0"))
            conn.execute(text("PRAGMA user_version = 105"))
            conn.commit()
            print("[Migration] Schema auf Version 105 (unternehmen: bank_import_aktiv – Bank CSV-Import)")

        if version < 106:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(bank_transaktionen)")).fetchall()}
            if "journal_id" not in cols:
                conn.execute(text(
                    "ALTER TABLE bank_transaktionen ADD COLUMN journal_id INTEGER REFERENCES journal(id) ON DELETE SET NULL"
                ))
            conn.execute(text("PRAGMA user_version = 106"))
            conn.commit()
            print("[Migration] Schema auf Version 106 (bank_transaktionen: journal_id – Halbautomatik Journal-Buchung)")

        if version < 107:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)")).fetchall()}
            if "ueberzahlung_anerkannt" not in cols:
                conn.execute(text(
                    "ALTER TABLE rechnungen ADD COLUMN ueberzahlung_anerkannt INTEGER NOT NULL DEFAULT 0"
                ))
            conn.execute(text("PRAGMA user_version = 107"))
            conn.commit()
            print("[Migration] Schema auf Version 107 (rechnungen: ueberzahlung_anerkannt – Überzahlungsprotokoll)")

        if version < 108:
            tables = {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()}
            if "forderungen" not in tables:
                conn.execute(text("""
                    CREATE TABLE forderungen (
                        id INTEGER PRIMARY KEY,
                        typ TEXT NOT NULL DEFAULT 'lieferantenguthaben',
                        status TEXT NOT NULL DEFAULT 'offen',
                        betrag NUMERIC(12,2) NOT NULL,
                        waehrung TEXT NOT NULL DEFAULT 'EUR',
                        faellig_am DATE,
                        partner_typ TEXT,
                        partner_id INTEGER,
                        rechnung_id INTEGER REFERENCES rechnungen(id) ON DELETE SET NULL,
                        journal_id INTEGER REFERENCES journal(id) ON DELETE SET NULL,
                        ausgleich_journal_id INTEGER REFERENCES journal(id) ON DELETE SET NULL,
                        notiz TEXT,
                        erstellt_am DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            conn.execute(text("PRAGMA user_version = 108"))
            conn.commit()
            print("[Migration] Schema auf Version 108 (forderungen – Offene Verrechnungsposten / Forderungsmanagement-Fundament)")

        if version < 109:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "bank_import_manuell" not in cols:
                conn.execute(text(
                    "ALTER TABLE unternehmen ADD COLUMN bank_import_manuell INTEGER NOT NULL DEFAULT 0"
                ))
            conn.execute(text("PRAGMA user_version = 109"))
            conn.commit()
            print("[Migration] Schema auf Version 109 (unternehmen: bank_import_manuell – Halbautomatik/Manuell-Modus)")

        if version < 110:
            konten_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(konten)")).fetchall()}
            if "datev_kontonummer" not in konten_cols:
                conn.execute(text("ALTER TABLE konten ADD COLUMN datev_kontonummer TEXT"))
            journal_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(journal)")).fetchall()}
            if "konto_id" not in journal_cols:
                conn.execute(text(
                    "ALTER TABLE journal ADD COLUMN konto_id INTEGER REFERENCES konten(id) ON DELETE SET NULL"
                ))
            conn.execute(text("PRAGMA user_version = 110"))
            conn.commit()
            print("[Migration] Schema auf Version 110 (konten: datev_kontonummer; journal: konto_id – DATEV Gegenkonto pro Bankkonto)")

        if version < 111:
            tx_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(bank_transaktionen)")).fetchall()}
            if "ist_rueckerstattung" not in tx_cols:
                conn.execute(text("ALTER TABLE bank_transaktionen ADD COLUMN ist_rueckerstattung BOOLEAN DEFAULT 0"))
            conn.execute(text("PRAGMA user_version = 111"))
            conn.commit()
            print("[Migration] Schema auf Version 111 (bank_transaktionen: ist_rueckerstattung)")

        if version < 112:
            # Fix: Bewirtungskosten vorsteuer_prozent korrigiert (Issue #214)
            # Per §15 UStG ist Vorsteuer auf Bewirtungskosten zu 100 % abzugsfähig.
            # Der 70 %-Abzug gilt nur ertragsteuerlich (§ 4 Abs. 5 Nr. 2 EStG).
            conn.execute(text("""
                UPDATE kategorien SET
                    vorsteuer_prozent = 100,
                    beschreibung = 'z. B. Geschäftsessen mit Kunden oder Partnern; ertragsteuerlich 70 % abziehbar (§ 4 Abs. 5 Nr. 2 EStG), Vorsteuer zu 100 % abzugsfähig; Anlass und Teilnehmer auf dem Beleg notieren'
                WHERE name = 'Bewirtungskosten'
            """))
            conn.execute(text("""
                UPDATE kategorien SET
                    vorsteuer_prozent = 100,
                    beschreibung = 'Der ertragsteuerlich nicht abziehbare 30 %-Anteil von Bewirtungskosten (§ 4 Abs. 5 Nr. 2 EStG); Vorsteuer trotzdem zu 100 % abzugsfähig'
                WHERE name = 'Bewirtungskosten (nicht abzugsfähig)'
            """))
            conn.execute(text("PRAGMA user_version = 112"))
            conn.commit()
            print("[Migration] Schema auf Version 112 (Bewirtungskosten: vorsteuer_prozent 70/0 → 100, Beschreibungen korrigiert)")

        if version < 113:
            cols_u113 = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "dashboard_config" not in cols_u113:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN dashboard_config TEXT"))
            conn.execute(text("PRAGMA user_version = 113"))
            conn.commit()
            print("[Migration] Schema auf Version 113 (unternehmen.dashboard_config – konfigurierbares Dashboard)")

        if version < 114:
            tables = {r[0] for r in conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )).fetchall()}
            if 'bank_templates' in tables:
                conn.execute(text("""
                    INSERT OR IGNORE INTO bank_templates
                        (id, name, bank, format, delimiter, encoding, decimal_separator, date_format, skip_rows, column_mapping, ist_system)
                    VALUES
                        ('CAMT_XML', 'CAMT / ISO 20022 (automatisch erkannt)', 'CAMT', 'CAMT', ';', 'UTF-8', '.', 'ISO', 0, '{}', 1)
                """))
            conn.execute(text("PRAGMA user_version = 114"))
            conn.commit()
            print("[Migration] Schema auf Version 114 (bank_templates: CAMT_XML-System-Eintrag – FK-Fix für CAMT-Import)")

        if version < 115:
            cols_k = {r[1] for r in conn.execute(text("PRAGMA table_info(kunden)")).fetchall()}
            if "debitor_nr" not in cols_k:
                conn.execute(text("ALTER TABLE kunden ADD COLUMN debitor_nr VARCHAR(20)"))
                conn.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uix_kunden_debitor_nr "
                    "ON kunden (debitor_nr) WHERE debitor_nr IS NOT NULL"
                ))
            cols_l = {r[1] for r in conn.execute(text("PRAGMA table_info(lieferanten)")).fetchall()}
            if "kreditor_nr" not in cols_l:
                conn.execute(text("ALTER TABLE lieferanten ADD COLUMN kreditor_nr VARCHAR(20)"))
                conn.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uix_lieferanten_kreditor_nr "
                    "ON lieferanten (kreditor_nr) WHERE kreditor_nr IS NOT NULL"
                ))
            # aktiv-Spalte in nummernkreise nachrüsten falls fehlend (war nur im Modell, nie migriert)
            cols_nk = {r[1] for r in conn.execute(text("PRAGMA table_info(nummernkreise)")).fetchall()}
            if "aktiv" not in cols_nk:
                conn.execute(text("ALTER TABLE nummernkreise ADD COLUMN aktiv BOOLEAN NOT NULL DEFAULT 1"))
            # Nummernkreise für Debitoren/Kreditoren
            conn.execute(text("""
                INSERT OR IGNORE INTO nummernkreise (typ, bezeichnung, format, naechste_nr, reset_jaehrlich, aktiv)
                VALUES ('debitor', 'Debitorennummern', '1####', 1, 0, 1)
            """))
            conn.execute(text("""
                INSERT OR IGNORE INTO nummernkreise (typ, bezeichnung, format, naechste_nr, reset_jaehrlich, aktiv)
                VALUES ('kreditor', 'Kreditorennummern', '7####', 1, 0, 1)
            """))
            conn.execute(text("PRAGMA user_version = 115"))
            conn.commit()
            print("[Migration] Schema auf Version 115 (kunden.debitor_nr, lieferanten.kreditor_nr – Kontokorrent Grundlage)")

        if version < 116:
            cols_u = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "datenmigration_aktiv" not in cols_u:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN datenmigration_aktiv BOOLEAN DEFAULT 0"))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS import_mapping_vorlagen (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL,
                    typ VARCHAR(20) NOT NULL,
                    hat_header BOOLEAN DEFAULT 1,
                    mapping_json TEXT NOT NULL,
                    typ_erkennung_aktiv BOOLEAN DEFAULT 0,
                    erstellt_am DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("PRAGMA user_version = 116"))
            conn.commit()
            print("[Migration] Schema auf Version 116 (datenmigration_aktiv, import_mapping_vorlagen)")

        if version < 117:
            tables_117 = {r[0] for r in conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )).fetchall()}
            if 'bank_templates' in tables_117:
                conn.execute(text("""
                    UPDATE bank_templates
                    SET column_mapping = '{"__erkennungs__": ["Datum", "Uhrzeit", "Beschreibung", "Brutto", "Währung", "Transaktionscode"], "Datum": "datum", "Uhrzeit": "uhrzeit", "Beschreibung": "buchungstext", "Name": "partner_name", "Brutto": "betrag", "Währung": "waehrung", "Transaktionscode": "referenz"}'
                    WHERE id = 'paypal'
                """))
            conn.execute(text("PRAGMA user_version = 117"))
            conn.commit()
            print("[Migration] Schema auf Version 117 (PayPal-Template: Spalte 'Beschreibung' statt 'Typ'/'Betreff' – Issue #248)")

        if version < 118:
            tables_118 = {r[0] for r in conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )).fetchall()}
            if 'bank_templates' in tables_118:
                conn.execute(text("""
                    INSERT OR IGNORE INTO bank_templates
                        (id, name, bank, format, delimiter, encoding, decimal_separator, date_format, skip_rows, column_mapping, ist_system)
                    VALUES
                        ('vivid', 'Vivid', 'Vivid', 'Standard', ',', 'UTF-8', '.', '%d.%m.%Y', 0,
                        '{"__erkennungs__": ["Completed date", "Counterparty name", "Reference", "Payment amount", "Payment currency"], "Completed date": "datum", "Counterparty name": "partner_name", "Reference": "verwendungszweck", "Payment amount": "betrag", "Payment currency": "waehrung"}',
                        1)
                """))
            conn.execute(text("PRAGMA user_version = 118"))
            conn.commit()
            print("[Migration] Schema auf Version 118 (bank_templates: Vivid-Template ergänzt, Issue #248)")

        if version < 119:
            cols_u119 = {r[1] for r in conn.execute(text("PRAGMA table_info(unternehmen)")).fetchall()}
            if "kontenuebersicht_aktiv" not in cols_u119:
                conn.execute(text("ALTER TABLE unternehmen ADD COLUMN kontenuebersicht_aktiv INTEGER NOT NULL DEFAULT 0"))
            conn.execute(text("PRAGMA user_version = 119"))
            conn.commit()
            print("[Migration] Schema auf Version 119 (unternehmen: kontenuebersicht_aktiv – Kategorien-Summenliste, Issue #255)")


def _migrate_kategorien() -> None:
    """EKS-Zuordnungen auf offizielles Formular (04/2025) bringen und fehlende Kategorien eintragen."""
    from database.models import Kategorie

    db = SessionLocal()
    try:
        # ── Korrekturen: alte Codes → neue Codes (offizielles Formular) ──────
        korrekturen = [
            # Tabelle A
            ("Privatentnahme",               None),    # Bargeld-Entnahme ist kein EKS-Feld; war fälschlich A2
            ("Privateinlage",                None),    # nicht im EKS-Formular
            ("Umsatzsteuer-Erstattung FA",   "A5_3"),  # war A5_2
            ("Vorsteuererstattung FA",       "A5_3"),  # war B17 – ist Einnahme
            # Tabelle B – Personalkostenumbenennungen
            ("Löhne & Gehälter",            "B2_1"),  # war B3
            ("Fremdleistungen",              "B14_5"), # war B4
            # Raumkosten
            ("Miete Büro",                   "B3"),    # war B5
            ("Nebenkosten Büro",             "B3"),    # war B5
            ("Arbeitszimmer (anteilig)",      "B3"),    # war B5
            # Versicherungen aufgeteilt
            ("Betriebsversicherungen",       "B4"),    # war B6
            ("Berufsgenossenschaft",         "B4"),    # war B6
            ("KFZ-Versicherung",             "B6_2"),  # war B7
            ("KFZ-Kosten",                   "B6_3"),  # war B7
            # Reise
            ("Reisekosten",                  "B7_1"),  # war B8
            # Büro / Sonstiges
            ("Büromaterial",                 "B10"),   # war B9
            ("Büroausstattung",              "B10"),   # war B9
            ("Porto & Versand",              "B10"),   # war B9
            ("Geringwertige Wirtschaftsgüter (GWG)", "B10"),  # war B9
            ("Werbung & Marketing",          "B5"),    # war B9
            ("Bewirtungskosten",             "B14_5"), # war B9
            ("Bankgebühren",                 "B14_3"), # war B9
            ("Software & Abonnements",       "B14_5"), # war B9
            ("Telefon & Internet",           "B11"),   # war B10
            ("Steuerberatung",               "B12"),   # war B11
            ("Rechts- & Beratungskosten",   "B12"),   # war B11
            ("Buchführungskosten",           "B12"),   # war B11
            ("Fortbildung & Fachliteratur",  "B13"),   # war B12
            ("Zinsen & Darlehenskosten",     "B15"),   # war B14
            ("Kredittilgung",                "B16"),   # war B15
            ("Umsatzsteuer-Zahlung FA",      "B18"),   # war B16
            ("Sonstige Betriebsausgaben",    "B14_5"), # war B18
            ("Anlagevermögen (Kauf)",        "B8"),    # war B18/C1
            # Tabelle C
            ("Pflegeversicherung (Pflicht)", "C2"),    # war C3 – im Formular mit KV zusammen
            ("Riester-Beiträge",             "C9"),    # war C5
            ("Sonstige Absetzungen",         "C10"),   # war C6
            ("Fahrtkosten (km-Pauschale)",   "B6_5"),  # war B6_3
            ("Mitgliedsbeiträge",            "B14_5"), # war B12
        ]
        for name, eks in korrekturen:
            kat = db.query(Kategorie).filter(Kategorie.name == name).first()
            if kat and kat.eks_kategorie != eks:
                kat.eks_kategorie = eks

        # SKR03-Kontonummer-Korrekturen (Issue #186)
        skr03_korrekturen = [
            ("Gewerbesteuer", "4320"),  # SKR03 hat kein 7600; Gewerbesteuer = 4320
        ]
        for name, konto in skr03_korrekturen:
            kat = db.query(Kategorie).filter(Kategorie.name == name).first()
            if kat and kat.konto_skr03 != konto:
                kat.konto_skr03 = konto

        # EÜR-Zeilen-Korrekturen
        euer_korrekturen = [
            ("Mitgliedsbeiträge", 60),          # war 46 (Beratungskosten) – Issue #106
            ("Betriebseinnahmen", 15),           # Issue #185: umsatzsteuerpflichtige BE → Zeile 15
            ("Betriebseinnahmen (19%)", 15),     # Datenfix #132: ältere DBs + Issue #185
            ("Betriebseinnahmen (7%)", 15),      # Issue #185: 7% gemeinsam mit 19% in Zeile 15
            ("Betriebseinnahmen (0%)", 12),      # Issue #185: Kleinunternehmer §19 → Zeile 12
            # Gewährte Skonti: euer_zeile → NULL (Issue #132, Migration 73 – kein Doppelabzug)
        ]
        for name, zeile in euer_korrekturen:
            kat = db.query(Kategorie).filter(Kategorie.name == name).first()
            if kat and kat.euer_zeile != zeile:
                kat.euer_zeile = zeile

        # ── Umbenennungen ─────────────────────────────────────────────────────
        umbenennungen = [
            ("Miete Büro", "Miete Büro (19%)"),
            ("Reisekosten", "Reisekosten – Übernachtung"),
            ("Fahrtkosten (km-Pauschale)", "Fahrtkosten Privat-PKW (0,10 €/km)"),
            # Issue #132: ältere Installs hatten Kategorie noch mit (19%)-Suffix
            ("Betriebseinnahmen (19%)", "Betriebseinnahmen"),
        ]
        for alt, neu in umbenennungen:
            kat = db.query(Kategorie).filter(Kategorie.name == alt).first()
            if kat and not db.query(Kategorie).filter(Kategorie.name == neu).first():
                kat.name = neu

        # ── Duplikat "Kleinunternehmer-Einnahmen" entfernen ───────────────────
        ku = db.query(Kategorie).filter(Kategorie.name == "Kleinunternehmer-Einnahmen").first()
        if ku:
            from database.models import Journaleintrag, Rechnungsposition
            in_use = (
                db.query(Journaleintrag).filter(Journaleintrag.kategorie_id == ku.id).first() or
                db.query(Rechnungsposition).filter(Rechnungsposition.kategorie_id == ku.id).first()
            )
            if not in_use:
                db.delete(ku)
                print("[Kategorien] 'Kleinunternehmer-Einnahmen' entfernt (Duplikat von 'Betriebseinnahmen (0%)')")

        # ── Fehlende Kategorien eintragen ─────────────────────────────────────
        neue = [
            # Betriebseinnahmen: müssen VOR _migrate_signaturen() existieren (Datenfix kategorie_id=NULL)
            {"name": "Betriebseinnahmen",     "kontenart": "Erlös",  "konto_skr03": "8400", "konto_skr04": "4400", "eks_kategorie": "A1", "euer_zeile": 15, "vorsteuer_prozent": 0, "ust_satz_standard": 19},
            {"name": "Betriebseinnahmen (7%)", "kontenart": "Erlös", "konto_skr03": "8300", "konto_skr04": "4300", "eks_kategorie": "A1", "euer_zeile": 15, "vorsteuer_prozent": 0, "ust_satz_standard": 7},
            {"name": "Betriebseinnahmen (0%)", "kontenart": "Erlös", "konto_skr03": "8100", "konto_skr04": "4100", "eks_kategorie": "A1", "euer_zeile": 12, "vorsteuer_prozent": 0, "ust_satz_standard": 0},
            {"name": "Wareneinkauf",                         "kontenart": "Aufwand", "konto_skr03": "3000", "konto_skr04": "5000", "eks_kategorie": "B1",    "euer_zeile": 27,   "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            {"name": "Wareneinkauf (7%)",                    "kontenart": "Aufwand", "konto_skr03": "3000", "konto_skr04": "5000", "eks_kategorie": "B1",    "euer_zeile": 27,   "vorsteuer_prozent": 100, "ust_satz_standard": 7},
            {"name": "Wareneinkauf EU",                      "kontenart": "Aufwand", "konto_skr03": "3400", "konto_skr04": "5400", "eks_kategorie": "B1",    "euer_zeile": 27,   "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            {"name": "Wareneinkauf Nicht-EU",                "kontenart": "Aufwand", "konto_skr03": "3500", "konto_skr04": "5500", "eks_kategorie": "B1",    "euer_zeile": 27,   "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            {"name": "Miete Büro (0%)",                      "kontenart": "Aufwand", "konto_skr03": "4210", "konto_skr04": "6310", "eks_kategorie": "B3",    "euer_zeile": 39,   "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "KFZ-Leasing",                          "kontenart": "Aufwand", "konto_skr03": "4570", "konto_skr04": "6560", "eks_kategorie": "B6_3",  "euer_zeile": 68,   "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            {"name": "Eigenverbrauch von Waren (19%)",       "kontenart": "Erlös",   "konto_skr03": "8910", "konto_skr04": "4640", "eks_kategorie": "A2",    "euer_zeile": 21,   "vorsteuer_prozent": 0,   "ust_satz_standard": 19},
            {"name": "Eigenverbrauch von Waren (7%)",        "kontenart": "Erlös",   "konto_skr03": "8915", "konto_skr04": "4610", "eks_kategorie": "A2",    "euer_zeile": 21,   "vorsteuer_prozent": 0,   "ust_satz_standard": 7},
            {"name": "USt auf Eigenverbrauch",               "kontenart": "Aufwand", "konto_skr03": "1776", "konto_skr04": "1776", "eks_kategorie": "A5_2",  "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Sonstige Einnahmen",                   "kontenart": "Erlös",   "konto_skr03": "8900", "konto_skr04": "4900", "eks_kategorie": "A3",    "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Zuwendungen von Dritten",              "kontenart": "Erlös",   "konto_skr03": "2747", "konto_skr04": "4982", "eks_kategorie": "A4",    "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Umsatzsteuer (vereinnahmt)",           "kontenart": "Aufwand", "konto_skr03": "1776", "konto_skr04": "1776", "eks_kategorie": "A5_1",  "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Umsatzsteuer-Erstattung FA",           "kontenart": "Erlös",   "konto_skr03": "1790", "konto_skr04": "3841", "eks_kategorie": "A5_3",  "euer_zeile": 18,   "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Löhne & Gehälter Teilzeit",           "kontenart": "Aufwand", "konto_skr03": "4120", "konto_skr04": "6010", "eks_kategorie": "B2_2",  "euer_zeile": 30,   "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "AG-Anteil Sozialversicherung",        "kontenart": "Aufwand", "konto_skr03": "4130", "konto_skr04": "6110", "eks_kategorie": "B2_1",  "euer_zeile": 30,   "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Minijob / geringfügige Beschäftigung", "kontenart": "Aufwand", "konto_skr03": "4120", "konto_skr04": "6030", "eks_kategorie": "B2_3",  "euer_zeile": 30,   "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Personalkosten Familienangehörige",  "kontenart": "Aufwand", "konto_skr03": "4120", "konto_skr04": "6050", "eks_kategorie": "B2_4",  "euer_zeile": 30,   "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Rechts- & Beratungskosten",           "kontenart": "Aufwand", "konto_skr03": "4950", "konto_skr04": "6825", "eks_kategorie": "B12",   "euer_zeile": 46,   "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            {"name": "Buchführungskosten",                   "kontenart": "Aufwand", "konto_skr03": "4955", "konto_skr04": "6830", "eks_kategorie": "B12",   "euer_zeile": 46,   "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            {"name": "KFZ-Steuer",                           "kontenart": "Aufwand", "konto_skr03": "4510", "konto_skr04": "6500", "eks_kategorie": "B6_1",  "euer_zeile": 69,   "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "KFZ-Reparatur",                        "kontenart": "Aufwand", "konto_skr03": "4540", "konto_skr04": "6450", "eks_kategorie": "B6_4",  "euer_zeile": 70,   "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            {"name": "Reparatur Anlagevermögen",              "kontenart": "Aufwand", "konto_skr03": "4260", "konto_skr04": "6335", "eks_kategorie": "B14_1", "euer_zeile": 60,   "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            {"name": "Miete Einrichtung",                     "kontenart": "Aufwand", "konto_skr03": "4200", "konto_skr04": "6318", "eks_kategorie": "B14_2", "euer_zeile": 47,   "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            {"name": "Betriebliche Abfallbeseitigung",        "kontenart": "Aufwand", "konto_skr03": "4969", "konto_skr04": "6859", "eks_kategorie": "B14_4", "euer_zeile": 52,   "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            {"name": "Reisekosten – Nebenkosten",            "kontenart": "Aufwand", "konto_skr03": "4663", "konto_skr04": "6644", "eks_kategorie": "B7_2",  "euer_zeile": 44,   "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            {"name": "Reisekosten – ÖPNV",                  "kontenart": "Aufwand", "konto_skr03": "4664", "konto_skr04": "6644", "eks_kategorie": "B7_3",  "euer_zeile": 70,   "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Zinsen & Darlehenskosten",             "kontenart": "Aufwand", "konto_skr03": "2140", "konto_skr04": "7330", "eks_kategorie": "B15",   "euer_zeile": 56,   "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Kredittilgung",                        "kontenart": "Aufwand", "konto_skr03": "2100", "konto_skr04": "3150", "eks_kategorie": "B16",   "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Umsatzsteuer-Zahlung FA",              "kontenart": "Aufwand", "konto_skr03": "1780", "konto_skr04": "1780", "eks_kategorie": "B18",   "euer_zeile": 58,   "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Anlagevermögen (Kauf)",                "kontenart": "Anlage",  "konto_skr03": "0400", "konto_skr04": "0400", "eks_kategorie": "B8",    "euer_zeile": None, "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            {"name": "Investition aus Zuwendung Dritter",   "kontenart": "Anlage",  "konto_skr03": "0435", "konto_skr04": "0435", "eks_kategorie": "B9",    "euer_zeile": None, "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            {"name": "Einkommensteuer-Vorauszahlung",        "kontenart": "Privat",  "konto_skr03": "1890", "konto_skr04": "2100", "eks_kategorie": "C1",    "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Gewerbesteuer",                        "kontenart": "Aufwand", "konto_skr03": "7600", "konto_skr04": "7610", "eks_kategorie": "C1",    "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Krankenversicherung (Pflicht)",        "kontenart": "Privat",  "konto_skr03": "1890", "konto_skr04": "2100", "eks_kategorie": "C2",    "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Pflegeversicherung (Pflicht)",         "kontenart": "Privat",  "konto_skr03": "1890", "konto_skr04": "2100", "eks_kategorie": "C2",    "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Rentenversicherung (freiwillig)",      "kontenart": "Privat",  "konto_skr03": "1890", "konto_skr04": "2100", "eks_kategorie": "C4",    "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Riester-Beiträge",                     "kontenart": "Privat",  "konto_skr03": "1890", "konto_skr04": "2100", "eks_kategorie": "C9",    "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Sonstige Absetzungen",                 "kontenart": "Privat",  "konto_skr03": "1890", "konto_skr04": "2100", "eks_kategorie": "C10",   "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            # Issue #61 – Forderungsausfall
            {"name": "Forderungsausfall",                "kontenart": "Aufwand", "konto_skr03": "4803", "konto_skr04": "6403", "eks_kategorie": None,    "euer_zeile": 60,   "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            # Issue #106 – fehlende EÜR-Zeilen
            {"name": "Abschreibungen (AfA)",             "kontenart": "Aufwand", "konto_skr03": "4830", "konto_skr04": "6220", "eks_kategorie": None,    "euer_zeile": 36,   "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Fahrtkosten Privat-PKW (0,10 €/km)", "kontenart": "Aufwand", "konto_skr03": "4560", "konto_skr04": "6530", "eks_kategorie": "B6_5",  "euer_zeile": 70,   "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Verpflegungsmehraufwand",          "kontenart": "Aufwand", "konto_skr03": "4661", "konto_skr04": "6645", "eks_kategorie": "B7_2",  "euer_zeile": 44,   "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Mitgliedsbeiträge",               "kontenart": "Aufwand", "konto_skr03": "4390", "konto_skr04": "6405", "eks_kategorie": "B14_5", "euer_zeile": 60,   "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Spenden (betrieblich)",            "kontenart": "Aufwand", "konto_skr03": "1840", "konto_skr04": "2250", "eks_kategorie": "B14_5", "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            # Skonti
            {"name": "Gewährte Skonti",                  "kontenart": "Erlös",   "konto_skr03": "8736", "konto_skr04": "4310", "eks_kategorie": "A1",    "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 19},
            {"name": "Erhaltene Skonti",                 "kontenart": "Aufwand", "konto_skr03": "2401", "konto_skr04": "3401", "eks_kategorie": "B1",    "euer_zeile": None, "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            # Bewirtungskosten nicht abzugsfähiger Anteil
            {"name": "Bewirtungskosten (nicht abzugsfähig)", "kontenart": "Aufwand", "konto_skr03": "4654", "konto_skr04": "6644", "eks_kategorie": None,    "euer_zeile": 63, "vorsteuer_prozent": 100, "ust_satz_standard": 0},
            # Anlagevermögen KFZ (Anlage AVEÜR: eigene Kategorie „Kraftfahrzeuge")
            {"name": "KFZ (Kauf)",                           "kontenart": "Anlage",  "konto_skr03": "0320", "konto_skr04": "0540", "eks_kategorie": "B8",    "euer_zeile": None, "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            # Digitale Wirtschaftsgüter: Wahlrecht Nutzungsdauer 1 Jahr (BMF 26.02.2021, § 7 Abs. 1 EStG)
            # KEIN GWG – muss ins Bestandsverzeichnis! Buchung: 1. Kauf hier (Anlage 0650), 2. volle AfA
            {"name": "EDV / Software (Sofortabschreibung)",  "kontenart": "Anlage",  "konto_skr03": "0490", "konto_skr04": "0650", "eks_kategorie": "B8",    "euer_zeile": None, "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            # EU-Handel – innergemeinschaftliche Lieferungen (§4 Nr. 1b UStG)
            # Käufer muss gültige USt-IdNr haben; UStVA KZ 41; Zusammenfassende Meldung (ZM) nötig
            {"name": "Innergemeinschaftliche Lieferungen",   "kontenart": "Erlös",   "konto_skr03": "8125", "konto_skr04": "3125", "eks_kategorie": "A1",    "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            # §13b Abs. 1 – EU-Dienstleistungen (Google, AWS, Beratung aus EU etc.)
            # Reverse Charge: Empfänger schuldet USt (KZ 46/47); Vorsteuer KZ 67; Rechnungsbetrag = Netto
            {"name": "EU-Dienstleistungen (§13b Abs. 1)",    "kontenart": "Aufwand", "konto_skr03": "3300", "konto_skr04": "5300", "eks_kategorie": "B1",    "euer_zeile": 27,   "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            # §13b Abs. 2 – Bauleistungen, Gebäudereinigung, Sicherheit, Metallieferungen aus Inland/EU
            # Reverse Charge: Empfänger schuldet USt (KZ 84/85); Vorsteuer KZ 67; Rechnungsbetrag = Netto
            {"name": "Bauleistungen / §13b Abs. 2",          "kontenart": "Aufwand", "konto_skr03": "3610", "konto_skr04": "5600", "eks_kategorie": "B14_1", "euer_zeile": 60,   "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            # §25a Differenzbesteuerung – Ankauf von Privatpersonen oder anderen ohne USt-Ausweis
            # Keine Vorsteuer abziehbar; EK-Preis ist Basis für Margenberechnung (VK − EK)
            {"name": "Wareneinkauf §25a (privat)",            "kontenart": "Aufwand", "konto_skr03": "3000", "konto_skr04": "5000", "eks_kategorie": "B1",    "euer_zeile": 27,   "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
        ]
        for data in neue:
            if not db.query(Kategorie).filter(Kategorie.name == data["name"]).first():
                db.add(Kategorie(**data))
        db.commit()
    finally:
        db.close()


def _migrate_signaturen() -> None:
    """
    GoBD-Sicherheit: SHA-256-Signaturen für alle immutable Einträge auf den
    aktuellen Stand der Signaturformel bringen.

    Behandelt zwei Fälle:
    - Keine Signatur (Altdaten vor GoBD-Feature)
    - Veraltete Signatur (Signaturformel durch Software-Update erweitert,
      z.B. neue Felder wie externe_belegnr oder kunde_id hinzugekommen)

    In beiden Fällen werden keine Buchungsdaten geändert – nur der Hash
    wird neu aus den unveränderlichen Buchungsdaten berechnet.

    Ablauf:
    1. Bestehende Schutz-Trigger temporär entfernen (damit UPDATE möglich ist).
    2. Alle immutable Einträge laden, Signatur neu berechnen.
    3. Nur tatsächlich abweichende Einträge aktualisieren.
    4. Trigger werden danach durch _setup_gobd_triggers() neu erstellt.
    """
    from utils.signatur import signatur_journaleintrag, signatur_tagesabschluss
    from database.models import Journaleintrag, Tagesabschluss

    # Trigger temporär entfernen
    with engine.connect() as conn:
        for trigger in [
            "protect_journal_update",
            "protect_journal_delete",
            "protect_tagesabschluesse_update",
            "protect_tagesabschluesse_delete",
        ]:
            conn.execute(text(f"DROP TRIGGER IF EXISTS {trigger}"))
        conn.commit()

    # Signaturen via ORM prüfen und bei Abweichung aktualisieren
    db = SessionLocal()
    try:
        # Issue #132: kategorielose Einnahme-Buchungen aus Ausgangsrechnungen reparieren.
        # Ursache: _erloes_kategorie() fand "Betriebseinnahmen" nicht (Kategorie hieß früher
        # "Betriebseinnahmen (19%)") → kategorie_id=NULL → EÜR Zeile 12 fehlte.
        # Kategorien sind jetzt durch Migration 69 / _migrate_kategorien() korrekt benannt.
        from database.models import Kategorie as _Kat
        _kat19 = db.query(_Kat).filter(_Kat.name == "Betriebseinnahmen").first()
        _kat7  = db.query(_Kat).filter(_Kat.name == "Betriebseinnahmen (7%)").first()
        _kat0  = db.query(_Kat).filter(_Kat.name == "Betriebseinnahmen (0%)").first()
        if _kat19:
            _ohne_kat = (
                db.query(Journaleintrag)
                .filter(
                    Journaleintrag.immutable == True,
                    Journaleintrag.art == "Einnahme",
                    Journaleintrag.rechnung_id.isnot(None),
                    Journaleintrag.kategorie_id.is_(None),
                )
                .all()
            )
            for _e in _ohne_kat:
                _satz = int(_e.ust_satz)
                if _satz == 19 and _kat19:
                    _e.kategorie_id = _kat19.id
                elif _satz == 7 and _kat7:
                    _e.kategorie_id = _kat7.id
                elif _kat0:
                    _e.kategorie_id = _kat0.id
            if _ohne_kat:
                print(f"[Signaturen] {len(_ohne_kat)} kategorielose Einnahme-Buchung(en) repariert (Issue #132)")

        # Noch offene Einträge (immutable=False) die älter als 5 Min. sind versiegeln
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        offene = (
            db.query(Journaleintrag)
            .filter(
                Journaleintrag.immutable == False,  # noqa: E712
                Journaleintrag.erstellt_am < cutoff,
            )
            .all()
        )
        for e in offene:
            e.immutable = True
            e.signatur = signatur_journaleintrag(e)
        if offene:
            print(f"[Signaturen] {len(offene)} offene Journal-Eintrag/Einträge versiegelt (Korrekturfenster abgelaufen)")

        eintraege = (
            db.query(Journaleintrag)
            .filter(Journaleintrag.immutable == True)
            .all()
        )
        for e in eintraege:
            neu = signatur_journaleintrag(e)
            if e.signatur != neu:
                e.signatur = neu

        abschluesse = (
            db.query(Tagesabschluss)
            .filter(Tagesabschluss.immutable == True)
            .all()
        )
        for a in abschluesse:
            neu = signatur_tagesabschluss(a)
            if a.signatur != neu:
                a.signatur = neu

        db.commit()
    finally:
        db.close()


def _setup_gobd_triggers() -> None:
    """
    SQLite-Trigger erstellen, die UPDATE und DELETE auf immutable Einträge
    auf Datenbankebene blockieren (GoBD-Konformität).

    WHEN OLD.immutable = 1 → greift nur auf bereits festgeschriebene Einträge.
    Neue Einträge (INSERT) sind nicht betroffen.
    """
    triggers = [
        """
        CREATE TRIGGER IF NOT EXISTS protect_journal_update
        BEFORE UPDATE ON journal
        WHEN OLD.immutable = 1
        BEGIN
            SELECT RAISE(ABORT,
                'GoBD-Verstoß: Journaleinträge sind unveränderbar (immutable=1).');
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS protect_journal_delete
        BEFORE DELETE ON journal
        WHEN OLD.immutable = 1
        BEGIN
            SELECT RAISE(ABORT,
                'GoBD-Verstoß: Journaleinträge können nicht gelöscht werden (immutable=1).');
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS protect_tagesabschluesse_update
        BEFORE UPDATE ON tagesabschluesse
        WHEN OLD.immutable = 1
        BEGIN
            SELECT RAISE(ABORT,
                'GoBD-Verstoß: Tagesabschlüsse sind unveränderbar (immutable=1).');
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS protect_tagesabschluesse_delete
        BEFORE DELETE ON tagesabschluesse
        WHEN OLD.immutable = 1
        BEGIN
            SELECT RAISE(ABORT,
                'GoBD-Verstoß: Tagesabschlüsse können nicht gelöscht werden (immutable=1).');
        END
        """,
    ]
    with engine.connect() as conn:
        for trigger_sql in triggers:
            conn.execute(text(trigger_sql))
        conn.commit()


@app.on_event("startup")
def startup():
    _prüfe_wiederherstellung()   # Vor create_all – DB muss ggf. erst ersetzt werden
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    _migrate_kategorien()   # Fehlende Kategorien nachträglich eintragen
    _migrate_signaturen()   # Erst Signaturen nachholen (Trigger noch nicht aktiv)
    _setup_gobd_triggers()  # Dann Trigger scharf schalten
    db = SessionLocal()
    try:
        run_all_seeds(db)
        # Fällige Rechnungsvorlagen als Entwürfe anlegen (blockiert Startup nie)
        try:
            from api.wiederkehrend import pruefen_intern as _wi
            _wi(db)
        except Exception as _e:
            logging.getLogger(__name__).warning("Wiederkehrende Rechnungen: %s", _e)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="RechnungsFee Backend")
    parser.add_argument("--port", type=int, default=8002)
    args = parser.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port)
