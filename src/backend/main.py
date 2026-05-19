import logging
import logging.handlers
import os
import sqlite3
import threading
from datetime import datetime

from fastapi import FastAPI
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
from api import unternehmen, konten, kategorien, setup, journal, kunden, lieferanten, tagesabschluss, nummernkreise, export, rechnungen, backup, artikel, ust_saetze, pdf_vorlagen, eks

SCHEMA_VERSION = 23

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
app.include_router(journal.router)
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
app.include_router(eks.router)


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


def _migrate_kategorien() -> None:
    """EKS-Zuordnungen auf offizielles Formular (04/2025) bringen und fehlende Kategorien eintragen."""
    from database.models import Kategorie

    db = SessionLocal()
    try:
        # ── Korrekturen: alte Codes → neue Codes (offizielles Formular) ──────
        korrekturen = [
            # Tabelle A
            ("Privatentnahme",               "A2"),    # war NULL
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
        ]
        for name, eks in korrekturen:
            kat = db.query(Kategorie).filter(Kategorie.name == name).first()
            if kat and kat.eks_kategorie != eks:
                kat.eks_kategorie = eks

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
            {"name": "Wareneinkauf",                         "kontenart": "Aufwand", "konto_skr03": "3000", "konto_skr04": "5000", "eks_kategorie": "B1",    "euer_zeile": 26,   "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            {"name": "Wareneinkauf (7%)",                    "kontenart": "Aufwand", "konto_skr03": "3000", "konto_skr04": "5000", "eks_kategorie": "B1",    "euer_zeile": 26,   "vorsteuer_prozent": 100, "ust_satz_standard": 7},
            {"name": "Wareneinkauf EU",                      "kontenart": "Aufwand", "konto_skr03": "3400", "konto_skr04": "5400", "eks_kategorie": "B1",    "euer_zeile": 26,   "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            {"name": "Wareneinkauf Nicht-EU",                "kontenart": "Aufwand", "konto_skr03": "3500", "konto_skr04": "5500", "eks_kategorie": "B1",    "euer_zeile": 26,   "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            {"name": "Sonstige Einnahmen",                   "kontenart": "Erlös",   "konto_skr03": "8900", "konto_skr04": "4900", "eks_kategorie": "A3",    "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Zuwendungen von Dritten",              "kontenart": "Erlös",   "konto_skr03": "8910", "konto_skr04": "4910", "eks_kategorie": "A4",    "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Umsatzsteuer (vereinnahmt)",           "kontenart": "Aufwand", "konto_skr03": "1776", "konto_skr04": "1776", "eks_kategorie": "A5_1",  "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Umsatzsteuer-Erstattung FA",           "kontenart": "Erlös",   "konto_skr03": "1779", "konto_skr04": "1779", "eks_kategorie": "A5_3",  "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Minijob / geringfügige Beschäftigung", "kontenart": "Aufwand", "konto_skr03": "4130", "konto_skr04": "6030", "eks_kategorie": "B2_3",  "euer_zeile": 44,   "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Rechts- & Beratungskosten",           "kontenart": "Aufwand", "konto_skr03": "4970", "konto_skr04": "6840", "eks_kategorie": "B12",   "euer_zeile": 50,   "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            {"name": "Buchführungskosten",                   "kontenart": "Aufwand", "konto_skr03": "4975", "konto_skr04": "6845", "eks_kategorie": "B12",   "euer_zeile": 50,   "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            {"name": "KFZ-Steuer",                           "kontenart": "Aufwand", "konto_skr03": "4510", "konto_skr04": "6500", "eks_kategorie": "B6_1",  "euer_zeile": 48,   "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Zinsen & Darlehenskosten",             "kontenart": "Aufwand", "konto_skr03": "4315", "konto_skr04": "7310", "eks_kategorie": "B15",   "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Kredittilgung",                        "kontenart": "Aufwand", "konto_skr03": "2100", "konto_skr04": "3150", "eks_kategorie": "B16",   "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Umsatzsteuer-Zahlung FA",              "kontenart": "Aufwand", "konto_skr03": "1780", "konto_skr04": "1780", "eks_kategorie": "B18",   "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Anlagevermögen (Kauf)",                "kontenart": "Anlage",  "konto_skr03": "0400", "konto_skr04": "0400", "eks_kategorie": "B8",    "euer_zeile": None, "vorsteuer_prozent": 100, "ust_satz_standard": 19},
            {"name": "Einkommensteuer-Vorauszahlung",        "kontenart": "Privat",  "konto_skr03": "1890", "konto_skr04": "2100", "eks_kategorie": "C1",    "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Gewerbesteuer",                        "kontenart": "Aufwand", "konto_skr03": "7600", "konto_skr04": "7610", "eks_kategorie": "C1",    "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Krankenversicherung (Pflicht)",        "kontenart": "Privat",  "konto_skr03": "1890", "konto_skr04": "2100", "eks_kategorie": "C2",    "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Pflegeversicherung (Pflicht)",         "kontenart": "Privat",  "konto_skr03": "1890", "konto_skr04": "2100", "eks_kategorie": "C2",    "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Rentenversicherung (freiwillig)",      "kontenart": "Privat",  "konto_skr03": "1890", "konto_skr04": "2100", "eks_kategorie": "C4",    "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Riester-Beiträge",                     "kontenart": "Privat",  "konto_skr03": "1890", "konto_skr04": "2100", "eks_kategorie": "C9",    "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
            {"name": "Sonstige Absetzungen",                 "kontenart": "Privat",  "konto_skr03": "1890", "konto_skr04": "2100", "eks_kategorie": "C10",   "euer_zeile": None, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
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
    parser.add_argument("--port", type=int, default=8002)
    args = parser.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port)
