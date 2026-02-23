from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database.connection import Base, engine, SessionLocal
from database.seed import run_all_seeds
from api import unternehmen, konten, kategorien, setup, kassenbuch, kunden, lieferanten, tagesabschluss, nummernkreise

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


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    db = SessionLocal()
    try:
        run_all_seeds(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
