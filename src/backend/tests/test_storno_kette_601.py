"""
Issue #601: Nach einer Korrektur (Storno + Neubuchung) erschien die Neubuchung ebenfalls als
„storniert“ (Journal, UStVA, EÜR) und liess sich nicht erneut korrigieren.

Ursache: Original, Storno und Neubuchung teilen dieselbe gruppe_id; jedes Storno der Gruppe
markierte alle Nicht-Storno-Buchungen als storniert. Jetzt zaehlt nur das Glied, dessen
Belegnummer die Gegenbuchung nennt („STORNO <Belegnr>: …“).
"""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.journal import StornoRequest, _storno_infos, storno_eintrag, update_eintrag
from api.schemas import JournalEintragCreate
from database.connection import Base
from database.models import Journaleintrag
from utils.storno_kette import storno_bezug, stornos_je_glied


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _original(db) -> Journaleintrag:
    e = Journaleintrag(
        datum=date(2026, 11, 2), belegnr="J-1", beschreibung="Büromaterial",
        zahlungsart="Bank", art="Ausgabe",
        netto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        brutto_betrag=Decimal("119.00"), vorsteuerabzug=True, immutable=True,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def _korrektur(tag: int) -> JournalEintragCreate:
    return JournalEintragCreate(
        datum=date(2026, 11, tag), beschreibung="Büromaterial",
        zahlungsart="Bank", art="Ausgabe", brutto_betrag=Decimal("119.00"),
        ust_satz=Decimal("19"), vorsteuerabzug=True,
    )


def _alle(db):
    return db.query(Journaleintrag).order_by(Journaleintrag.id).all()


def _neueste_neubuchung(db) -> Journaleintrag:
    return [e for e in _alle(db) if not e.beschreibung.startswith("STORNO ")][-1]


def test_neubuchung_nach_datumskorrektur_nicht_storniert(db):
    original = _original(db)
    update_eintrag(original.id, _korrektur(5), db)
    eintraege = _alle(db)
    infos = _storno_infos(db, eintraege)
    storno = next(e for e in eintraege if e.beschreibung.startswith("STORNO "))
    neu = _neueste_neubuchung(db)

    assert infos[original.id]["storniert"] is True
    assert infos[original.id]["storno_belegnr"] == storno.belegnr
    assert infos[storno.id]["ist_storno"] is True
    assert infos[storno.id]["storno_von_belegnr"] == "J-1"
    assert neu.id != original.id and neu.gruppe_id == original.id
    assert infos[neu.id]["storniert"] is False
    assert infos[neu.id]["ist_storno"] is False


def test_neubuchung_laesst_sich_erneut_korrigieren(db):
    original = _original(db)
    update_eintrag(original.id, _korrektur(5), db)
    erste_neu = _neueste_neubuchung(db)
    update_eintrag(erste_neu.id, _korrektur(7), db)  # vorher 409 „bereits storniert“

    eintraege = _alle(db)
    infos = _storno_infos(db, eintraege)
    zweite_neu = _neueste_neubuchung(db)
    stornos = [e for e in eintraege if e.beschreibung.startswith("STORNO ")]

    assert len(stornos) == 2
    assert infos[original.id]["storniert"] and infos[erste_neu.id]["storniert"]
    assert infos[zweite_neu.id]["storniert"] is False
    assert zweite_neu.datum == date(2026, 11, 7)
    # Storno der ersten Neubuchung nennt diese, nicht die Wurzel
    assert sorted(infos[s.id]["storno_von_belegnr"] for s in stornos) == sorted(["J-1", erste_neu.belegnr])


def test_stornierte_buchung_bleibt_gesperrt(db):
    original = _original(db)
    update_eintrag(original.id, _korrektur(5), db)
    with pytest.raises(HTTPException) as e:
        update_eintrag(original.id, _korrektur(9), db)
    assert e.value.status_code == 409
    with pytest.raises(HTTPException) as e:
        storno_eintrag(original.id, StornoRequest(grund="doppelt"), db)
    assert e.value.status_code == 409


def test_neubuchung_einzeln_stornierbar(db):
    original = _original(db)
    update_eintrag(original.id, _korrektur(5), db)
    neu = _neueste_neubuchung(db)
    storno_eintrag(neu.id, StornoRequest(grund="Fehlbuchung"), db)
    infos = _storno_infos(db, _alle(db))
    assert infos[neu.id]["storniert"] is True
    with pytest.raises(HTTPException):
        storno_eintrag(neu.id, StornoRequest(grund="nochmal"), db)


def test_eigene_buchung_mit_storno_text_ohne_gruppe_kein_storno(db):
    e = _original(db)
    e2 = Journaleintrag(
        datum=date(2026, 11, 3), belegnr="J-2", beschreibung="STORNO J-1: selbst getippt",
        zahlungsart="Bank", art="Einnahme", netto_betrag=Decimal("1"), ust_satz=Decimal("0"),
        ust_betrag=Decimal("0"), brutto_betrag=Decimal("1"), immutable=True,
    )
    db.add(e2)
    db.commit()
    infos = _storno_infos(db, _alle(db))
    assert infos[e.id]["storniert"] is False
    assert infos[e2.id]["ist_storno"] is False


def test_zahlungskette_ersatzrechnung():
    """Zahlungen einer Ersatzrechnung erben die gruppe_id der Vorgänger-Zahlung – nur die
    stornierte Zahlung zählt als storniert (Logik aus schemas_rechnungen.py)."""
    z1 = SimpleNamespace(id=1, gruppe_id=None, belegnr="J-1", beschreibung="Zahlung RE-1")
    s1 = SimpleNamespace(id=2, gruppe_id=1, belegnr="J-2", beschreibung="STORNO J-1: RE-1 – falsch")
    z2 = SimpleNamespace(id=3, gruppe_id=1, belegnr="J-3", beschreibung="Zahlung RE-2")
    je_glied = stornos_je_glied([z1, s1, z2])
    assert (1, "J-1") in je_glied
    assert (1, "J-3") not in je_glied


@pytest.mark.parametrize("text,bezug", [
    ("STORNO J-1: Korrektur", "J-1"),
    ("STORNO 2026-0007: RE-26001 – Doppelt", "2026-0007"),
    ("STORNO J-1 : alt", "J-1"),
    ("Zahlung", None),
    (None, None),
])
def test_storno_bezug(text, bezug):
    assert storno_bezug(text) == bezug
