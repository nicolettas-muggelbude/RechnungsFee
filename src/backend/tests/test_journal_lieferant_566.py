"""
Issue #566: Lieferant bei direkt gebuchten Ausgaben (Journal, Split, Buchungsvorlage).

- journal.lieferant_id ohne DB-Fremdschlüssel (Migration 192), nur bei Ausgaben gesetzt
- Signatur: Buchungen ohne Lieferant behalten exakt ihre bisherige Signatur
- DSGVO beim Lieferanten: Auskunft listet die Buchungen, Anonymisieren löscht den Stammsatz
  auch dann, wenn versiegelte Buchungen auf ihn verweisen
"""
import json
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

import main
from api.buchungsvorlagen import BuchenRequest, BuchungsvorlageCreate, buche_vorlage, erstelle_vorlage
from api.journal import create_eintrag, create_split_buchung
from api.lieferanten import anonymisiere_lieferant, dsgvo_export
from api.schemas import JournalEintragCreate, JournalEintragResponse, SplitBuchungCreate, SplitPosition
from database.connection import Base
from database.models import Journaleintrag, Lieferant
from utils.signatur import berechne_signatur, signatur_journaleintrag


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Lieferant(firmenname="Reinigung Blitz", strasse="Weg", hausnummer="1", plz="12345", ort="Ort"))
    session.commit()
    yield session
    session.close()


def _lid(db) -> int:
    return db.query(Lieferant).one().id


def _ausgabe(db, **kw):
    daten = dict(datum=date(2026, 11, 20), beschreibung="Reinigung Büro", art="Ausgabe",
                 brutto_betrag=Decimal("119"), ust_satz=Decimal("19"), zahlungsart="Bank")
    daten.update(kw)
    return create_eintrag(JournalEintragCreate(**daten), db)


def test_ausgabe_mit_lieferant(db):
    resp = _ausgabe(db, lieferant_id=_lid(db))
    assert (resp.lieferant_id, resp.lieferant_name) == (_lid(db), "Reinigung Blitz")


def test_einnahme_ignoriert_lieferant(db):
    resp = _ausgabe(db, art="Einnahme", lieferant_id=_lid(db))
    assert resp.lieferant_id is None


def test_signatur_altbestand_unveraendert(db):
    """Ohne Lieferant entspricht die Signatur exakt der bisherigen Feldliste."""
    e = db.query(Journaleintrag).filter(Journaleintrag.id == _ausgabe(db).id).one()
    alt = berechne_signatur({
        "art": str(e.art), "belegnr": str(e.belegnr), "beschreibung": str(e.beschreibung),
        "brutto_betrag": "119.00", "datum": str(e.datum), "externe_belegnr": "",
        "kategorie_id": "", "kunde_id": "", "netto_betrag": "100.00", "steuerbefreiung_grund": "",
        "ust_betrag": "19.00", "ust_satz": "19.00", "vorsteuerabzug": bool(e.vorsteuerabzug),
        "zahlungsart": "Bank", "km_anzahl": "",
    })
    assert signatur_journaleintrag(e) == alt == e.signatur


def test_signatur_mit_lieferant_anders(db):
    e = db.query(Journaleintrag).filter(Journaleintrag.id == _ausgabe(db, lieferant_id=_lid(db)).id).one()
    assert e.signatur == signatur_journaleintrag(e)
    ohne = signatur_journaleintrag(e)
    e.lieferant_id = None
    assert signatur_journaleintrag(e) != ohne


def test_split_mit_lieferant(db):
    eintraege = create_split_buchung(SplitBuchungCreate(
        datum=date(2026, 11, 20), art="Ausgabe", zahlungsart="Bank", lieferant_id=_lid(db),
        positionen=[SplitPosition(beschreibung="A", brutto_betrag=Decimal("50")),
                    SplitPosition(beschreibung="B", brutto_betrag=Decimal("70"))],
    ), db)
    ids = [e.id for e in eintraege]
    assert {e.lieferant_id for e in db.query(Journaleintrag).filter(Journaleintrag.id.in_(ids))} == {_lid(db)}


def test_vorlage_uebergibt_lieferant(db):
    v = erstelle_vorlage(BuchungsvorlageCreate(
        bezeichnung="Reinigung", lieferant_id=_lid(db), betrag=Decimal("119"), ust_satz=Decimal("19"),
        naechstes_datum=date(2026, 11, 1), art="Ausgabe", modus="direkt",
    ), db)
    buche_vorlage(v.id, data=BuchenRequest(), db=db)
    e = db.query(Journaleintrag).filter(Journaleintrag.buchungsvorlage_id == v.id).one()
    assert e.lieferant_id == _lid(db)
    assert JournalEintragResponse.from_orm_with_kunde(e).lieferant_name == "Reinigung Blitz"


def test_dsgvo_auskunft_und_anonymisieren(db):
    lid = _lid(db)
    _ausgabe(db, lieferant_id=lid)
    db.query(Journaleintrag).update({Journaleintrag.immutable: True})
    db.commit()
    auskunft = json.loads(dsgvo_export(lid, db).body)
    assert len(auskunft["journal"]) == 1
    erg = anonymisiere_lieferant(lid, db)
    assert erg["unveraenderlich_verblieben"] == 1
    assert db.query(Lieferant).count() == 0
    e = db.query(Journaleintrag).one()
    assert e.lieferant_id == lid and JournalEintragResponse.from_orm_with_kunde(e).lieferant_name is None


def test_migration_192(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE journal DROP COLUMN lieferant_id"))
        conn.execute(text("PRAGMA user_version = 191"))
    monkeypatch.setattr(main, "engine", engine)
    main._run_migrations()
    with engine.begin() as conn:
        assert "lieferant_id" in {r[1] for r in conn.execute(text("PRAGMA table_info(journal)"))}
        assert conn.execute(text("PRAGMA user_version")).scalar() == main.SCHEMA_VERSION
        conn.execute(text("PRAGMA user_version = 191"))
    main._run_migrations()
