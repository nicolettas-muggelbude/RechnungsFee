from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database.connection import Base, engine, SessionLocal
from database.seed import run_all_seeds
from api import unternehmen, konten, kategorien, setup, kassenbuch, kunden, lieferanten, tagesabschluss, nummernkreise, export, rechnungen

app = FastAPI(title="RechnungsFee API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "tauri://localhost"],
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


def _run_migrations() -> None:
    """Einfache Spalten-Migrationen für SQLite (ohne Alembic)."""
    with engine.connect() as conn:
        # kassenbuch.kunde_id
        result = conn.execute(text("PRAGMA table_info(kassenbuch)"))
        columns = {row[1] for row in result}
        if "kunde_id" not in columns:
            conn.execute(text(
                "ALTER TABLE kassenbuch ADD COLUMN kunde_id INTEGER REFERENCES kunden(id)"
            ))
            conn.commit()

        # kassenbuch.rechnung_id
        result = conn.execute(text("PRAGMA table_info(kassenbuch)"))
        columns = {row[1] for row in result}
        if "rechnung_id" not in columns:
            conn.execute(text(
                "ALTER TABLE kassenbuch ADD COLUMN rechnung_id INTEGER REFERENCES rechnungen(id)"
            ))
            conn.commit()

        # rechnungen.bezahlt_betrag
        result = conn.execute(text("PRAGMA table_info(rechnungen)"))
        columns = {row[1] for row in result}
        if "bezahlt_betrag" not in columns:
            conn.execute(text(
                "ALTER TABLE rechnungen ADD COLUMN bezahlt_betrag NUMERIC(12,2) NOT NULL DEFAULT 0"
            ))
            conn.commit()

        # rechnungen.zahlungsstatus
        result = conn.execute(text("PRAGMA table_info(rechnungen)"))
        columns = {row[1] for row in result}
        if "zahlungsstatus" not in columns:
            conn.execute(text(
                "ALTER TABLE rechnungen ADD COLUMN zahlungsstatus VARCHAR(20) NOT NULL DEFAULT 'offen'"
            ))
            conn.commit()

        # kassenbuch.externe_belegnr
        result = conn.execute(text("PRAGMA table_info(kassenbuch)"))
        columns = {row[1] for row in result}
        if "externe_belegnr" not in columns:
            conn.execute(text(
                "ALTER TABLE kassenbuch ADD COLUMN externe_belegnr VARCHAR(100)"
            ))
            conn.commit()

        # kassenbuch.signatur
        result = conn.execute(text("PRAGMA table_info(kassenbuch)"))
        columns = {row[1] for row in result}
        if "signatur" not in columns:
            conn.execute(text(
                "ALTER TABLE kassenbuch ADD COLUMN signatur VARCHAR(64)"
            ))
            conn.commit()

        # rechnungen.leistungsdatum
        result = conn.execute(text("PRAGMA table_info(rechnungen)"))
        columns = {row[1] for row in result}
        if "leistungsdatum" not in columns:
            conn.execute(text("ALTER TABLE rechnungen ADD COLUMN leistungsdatum DATE"))
            conn.commit()

        # rechnungen.ist_entwurf (DEFAULT 1 = alle bestehenden Rechnungen werden Entwürfe)
        result = conn.execute(text("PRAGMA table_info(rechnungen)"))
        columns = {row[1] for row in result}
        if "ist_entwurf" not in columns:
            conn.execute(text(
                "ALTER TABLE rechnungen ADD COLUMN ist_entwurf BOOLEAN NOT NULL DEFAULT 1"
            ))
            conn.commit()

        # rechnungen.storniert
        result = conn.execute(text("PRAGMA table_info(rechnungen)"))
        columns = {row[1] for row in result}
        if "storniert" not in columns:
            conn.execute(text(
                "ALTER TABLE rechnungen ADD COLUMN storniert BOOLEAN NOT NULL DEFAULT 0"
            ))
            conn.commit()

        # tagesabschluesse.zaehlung_json
        result = conn.execute(text("PRAGMA table_info(tagesabschluesse)"))
        columns = {row[1] for row in result}
        if "zaehlung_json" not in columns:
            conn.execute(text(
                "ALTER TABLE tagesabschluesse ADD COLUMN zaehlung_json TEXT"
            ))
            conn.commit()

        # tagesabschluesse.signatur
        result = conn.execute(text("PRAGMA table_info(tagesabschluesse)"))
        columns = {row[1] for row in result}
        if "signatur" not in columns:
            conn.execute(text(
                "ALTER TABLE tagesabschluesse ADD COLUMN signatur VARCHAR(64)"
            ))
            conn.commit()

        # kategorien.ust_satz_standard
        result = conn.execute(text("PRAGMA table_info(kategorien)"))
        columns = {row[1] for row in result}
        if "ust_satz_standard" not in columns:
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
            conn.commit()


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
    GoBD-Sicherheit: Rückwirkend SHA-256-Signaturen für bestehende immutable
    Einträge ohne Signatur berechnen.

    Ablauf:
    1. Bestehende Schutz-Trigger temporär entfernen (damit UPDATE möglich ist).
    2. Signaturen über ORM-Session berechnen und setzen.
    3. Trigger werden danach durch _setup_gobd_triggers() neu erstellt.
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

    # Signaturen via ORM setzen (konsistent mit signatur_*-Funktionen)
    db = SessionLocal()
    try:
        eintraege = (
            db.query(Kassenbucheintrag)
            .filter(Kassenbucheintrag.immutable == True, Kassenbucheintrag.signatur.is_(None))
            .all()
        )
        for e in eintraege:
            e.signatur = signatur_kassenbucheintrag(e)

        abschluesse = (
            db.query(Tagesabschluss)
            .filter(Tagesabschluss.immutable == True, Tagesabschluss.signatur.is_(None))
            .all()
        )
        for a in abschluesse:
            a.signatur = signatur_tagesabschluss(a)

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
