"""
Regressionstests für Issue #384 (GoBD-Integritätsnachweis):

1. Eine Signatur, die beim frischen Anlegen einer Buchung aus rohen, ungeskalierten
   Decimal-Werten berechnet wird (z.B. Decimal("19") aus dem Request), muss identisch
   sein zur Signatur, die aus demselben, frisch aus SQLite geladenen Datensatz berechnet
   wird (Decimal("19.00"), durch die Numeric(5,2)-Spaltenskala) - sonst meldet ein
   sauberer GoBD-Export "ungueltige Signatur" fuer voellig unveraenderte Buchungen.
2. _migrate_signaturen() darf für eine unveränderte, direkt als immutable=True angelegte
   Buchung (Split-Buchung/Rechnungs-Zahlungspfade) keine Signatur mehr überschreiben.
3. Schlägt _migrate_signaturen() fehl, muss _setup_gobd_triggers() trotzdem laufen -
   sonst bleibt die DB bis zum nächsten erfolgreichen Start ungeschützt.
"""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import main
from database.connection import Base
from database.models import Journaleintrag
from utils.signatur import signatur_journaleintrag


def make_engine(db_path: Path):
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _immutable_eintrag(db, **kwargs) -> Journaleintrag:
    """Baut einen Journaleintrag exakt wie create_split_buchung()/die Rechnungs-Zahlungspfade:
    immutable=True direkt bei der Erstellung, Signatur VOR dem ersten commit()/refresh() aus
    den noch rohen (nicht DB-skalierten) Werten berechnet - das ist der Pfad, der laut Issue
    #384 beim allerersten GoBD-Export als "ungueltig" auffiel, weil er (anders als Storno, das
    Werte aus einem bereits geladenen Original kopiert) nie durch eine erneute Signierung
    lief, bevor er exportiert/geprueft wurde."""
    defaults = dict(
        datum=date(2026, 8, 12), belegnr="J-1", beschreibung="Testausgabe",
        zahlungsart="Bank", art="Ausgabe",
        netto_betrag=Decimal("100"), ust_satz=Decimal("19"), ust_betrag=Decimal("19"),
        brutto_betrag=Decimal("119"), vorsteuerabzug=True, immutable=True,
    )
    defaults.update(kwargs)
    e = Journaleintrag(**defaults)
    e.signatur = signatur_journaleintrag(e)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def test_frische_signatur_uebersteht_db_roundtrip(db):
    """Kernfehler aus Issue #384: str(Decimal("19")) != str(Decimal("19.00"))."""
    eintrag = _immutable_eintrag(db)
    gespeicherte_signatur = eintrag.signatur

    db.expire_all()
    frisch_geladen = db.query(Journaleintrag).filter(Journaleintrag.id == eintrag.id).first()

    assert signatur_journaleintrag(frisch_geladen) == gespeicherte_signatur


def test_migrate_signaturen_lässt_unveränderte_buchung_in_ruhe(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    eng = make_engine(db_path)
    monkeypatch.setattr(main, "engine", eng)
    monkeypatch.setattr(main, "DB_PATH", db_path)
    monkeypatch.setattr(main, "SessionLocal", sessionmaker(bind=eng))

    Base.metadata.create_all(bind=eng)
    Session = sessionmaker(bind=eng)
    db = Session()

    eintrag = _immutable_eintrag(db)
    eintrag_id = eintrag.id
    signatur_vor_migration = eintrag.signatur
    db.close()

    main._migrate_signaturen()

    db2 = Session()
    nachher = db2.query(Journaleintrag).filter(Journaleintrag.id == eintrag_id).first()
    assert nachher.signatur == signatur_vor_migration
    db2.close()


def test_trigger_werden_trotz_fehlgeschlagener_signatur_migration_neu_gesetzt(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    eng = make_engine(db_path)
    monkeypatch.setattr(main, "engine", eng)
    monkeypatch.setattr(main, "DB_PATH", db_path)
    Base.metadata.create_all(bind=eng)

    def _kaputte_migration():
        raise RuntimeError("simulierter Fehler")

    monkeypatch.setattr(main, "_migrate_signaturen", _kaputte_migration)

    main._migrate_signaturen_sicher()

    with eng.connect() as con:
        trigger = con.execute(
            text("SELECT name FROM sqlite_master WHERE type='trigger' AND name='protect_journal_update'")
        ).fetchone()
    assert trigger is not None
