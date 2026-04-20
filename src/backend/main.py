import os
import sqlite3
import threading
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database.connection import Base, engine, SessionLocal, DB_PATH
from database.seed import run_all_seeds
from api import unternehmen, konten, kategorien, setup, kassenbuch, kunden, lieferanten, tagesabschluss, nummernkreise, export, rechnungen, backup, artikel, ust_saetze, pdf_vorlagen

SCHEMA_VERSION = 14

app = FastAPI(title="RechnungsFee API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "tauri://localhost", "http://tauri.localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(setup.router)
app.include_router(unternehmen.router)
app.include_router(konten.router)
app.include_router(kategorien.router)
app.include_router(kassenbuch.router)
app.include_router(kunden.router)
app.include_router(lieferanten.router)
app.include_router(tagesabschluss.router)
app.include_router(nummernkreise.router)
app.include_router(export.router)
app.include_router(rechnungen.router)
app.include_router(backup.router)
app.include_router(artikel.router)
app.include_router(ust_saetze.router)
app.include_router(pdf_vorlagen.router)


@app.get("/api/debug/qr")
def debug_qr():
    """Debug: segno-Import und QR-Generierung testen (nur Testing-Build)."""
    result = {}
    try:
        import segno
        result["segno_version"] = segno.__version__
        result["segno_import"] = "ok"
    except Exception as e:
        result["segno_import"] = f"FEHLER: {e}"
        return result

    try:
        from io import BytesIO
        qr = segno.make("BCD\n002\n2\nSCT\nCOBADEFFXXX\nTest GmbH\nDE89370400440532013000\nEUR42.00\n\n\nRE-TEST", error="m")
        buf = BytesIO()
        qr.save(buf, kind="png", scale=10, border=1)
        png_bytes = buf.getvalue()
        result["qr_generierung"] = "ok"
        result["png_bytes"] = len(png_bytes)
        result["png_header"] = png_bytes[:4].hex()
    except Exception as e:
        result["qr_generierung"] = f"FEHLER: {e}"

    return result


@app.get("/api/debug/qr.png")
def debug_qr_png():
    """Debug: QR-Code direkt als PNG zurückgeben."""
    from fastapi.responses import Response
    from io import BytesIO
    try:
        import segno
        qr = segno.make("BCD\n002\n2\nSCT\nCOBADEFFXXX\nTest GmbH\nDE89370400440532013000\nEUR42.00\n\n\nRE-TEST", error="m")
        buf = BytesIO()
        qr.save(buf, kind="png", scale=10, border=1)
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as e:
        return Response(content=f"Fehler: {e}", media_type="text/plain", status_code=500)


@app.post("/api/shutdown")
def shutdown():
    """Graceful Shutdown – Tauri ruft diesen Endpoint vor dem Update-Installer auf."""
    def _exit():
        import time
        time.sleep(0.15)   # Antwort zuerst senden, dann beenden
        os._exit(0)
    threading.Thread(target=_exit, daemon=True).start()
    return {"ok": True}


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


def _run_migrations() -> None:
    """Versionierte DB-Migrationen für SQLite (ohne Alembic)."""
    with engine.connect() as conn:
        version = conn.execute(text("PRAGMA user_version")).scalar()

    if version >= SCHEMA_VERSION:
        return  # Fast-Path: DB ist aktuell

    _backup_datenbank()

    with engine.connect() as conn:
        if version < 1:
            # kassenbuch – 1× PRAGMA für alle Spalten
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


def _migrate_kategorien() -> None:
    """Fehlende Kategorien in bestehende Datenbanken eintragen."""
    from database.models import Kategorie

    neue = [
        {
            "name": "Wareneinkauf",
            "kontenart": "Aufwand",
            "konto_skr03": "3000", "konto_skr04": "5000",
            "eks_kategorie": "B1", "euer_zeile": 26,
            "vorsteuer_prozent": 100, "ust_satz_standard": 19,
            "ist_system": True,
        },
        {
            "name": "Wareneinkauf (7%)",
            "kontenart": "Aufwand",
            "konto_skr03": "3000", "konto_skr04": "5000",
            "eks_kategorie": "B1", "euer_zeile": 26,
            "vorsteuer_prozent": 100, "ust_satz_standard": 7,
            "ist_system": True,
        },
    ]
    db = SessionLocal()
    try:
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
    from utils.signatur import signatur_kassenbucheintrag, signatur_tagesabschluss
    from database.models import Kassenbucheintrag, Tagesabschluss

    # Trigger temporär entfernen
    with engine.connect() as conn:
        for trigger in [
            "protect_kassenbuch_update",
            "protect_kassenbuch_delete",
            "protect_tagesabschluesse_update",
            "protect_tagesabschluesse_delete",
        ]:
            conn.execute(text(f"DROP TRIGGER IF EXISTS {trigger}"))
        conn.commit()

    # Signaturen via ORM prüfen und bei Abweichung aktualisieren
    db = SessionLocal()
    try:
        eintraege = (
            db.query(Kassenbucheintrag)
            .filter(Kassenbucheintrag.immutable == True)
            .all()
        )
        for e in eintraege:
            neu = signatur_kassenbucheintrag(e)
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
        CREATE TRIGGER IF NOT EXISTS protect_kassenbuch_update
        BEFORE UPDATE ON kassenbuch
        WHEN OLD.immutable = 1
        BEGIN
            SELECT RAISE(ABORT,
                'GoBD-Verstoß: Kassenbucheinträge sind unveränderbar (immutable=1).');
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS protect_kassenbuch_delete
        BEFORE DELETE ON kassenbuch
        WHEN OLD.immutable = 1
        BEGIN
            SELECT RAISE(ABORT,
                'GoBD-Verstoß: Kassenbucheinträge können nicht gelöscht werden (immutable=1).');
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
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    _migrate_kategorien()   # Fehlende Kategorien nachträglich eintragen
    _migrate_signaturen()   # Erst Signaturen nachholen (Trigger noch nicht aktiv)
    _setup_gobd_triggers()  # Dann Trigger scharf schalten
    db = SessionLocal()
    try:
        run_all_seeds(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="RechnungsFee Backend")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port)
