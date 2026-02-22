from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.connection import Base, engine, SessionLocal
from database.seed import run_all_seeds
from api import unternehmen, konten, kategorien, setup, kassenbuch, kunden, lieferanten, tagesabschluss

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


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        run_all_seeds(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
